"""Documentation crawler service using httpx and BeautifulSoup."""

import asyncio
import hashlib
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import logging

import httpx
from bs4 import BeautifulSoup
from bs4.element import Comment

from src.models import Project, CrawlStatus, PageStatus
from ..models.session import CrawlSession
from ..models.page import Page
from src.services.database import DatabaseManager
from src.core.config import DocBroConfig
from src.core.lib_logger import get_component_logger


class CrawlerError(Exception):
    """Crawler operation error."""
    pass


class DocumentationCrawler:
    """Asynchronous documentation crawler with rate limiting and robots.txt support."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: Optional[DocBroConfig] = None
    ):
        """Initialize documentation crawler."""
        self.db_manager = db_manager
        self.config = config or DocBroConfig()
        self.logger = get_component_logger("crawler")

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        # Crawl state
        self._crawl_queue: asyncio.Queue = asyncio.Queue()
        self._visited_urls: Set[str] = set()
        self._content_hashes: Set[str] = set()
        self._domain_last_access: Dict[str, float] = {}

        # Robots.txt cache
        self._robots_cache: Dict[str, RobotFileParser] = {}

        # Session state
        self._current_session: Optional[CrawlSession] = None
        self._is_running = False
        self._stop_requested = False
        self._crawl_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize crawler."""
        if self._client:
            self.logger.debug("Client already initialized, skipping")
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        self.logger.debug("Crawler initialized")

    async def cleanup(self) -> None:
        """Clean up crawler resources."""
        # Cancel crawl task if running
        if self._crawl_task and not self._crawl_task.done():
            self._crawl_task.cancel()
            try:
                await self._crawl_task
            except asyncio.CancelledError:
                pass
            self._crawl_task = None

        if self._client:
            await self._client.aclose()
            self._client = None

        # Clear state but don't recreate queue (it will be recreated in start_crawl)
        while not self._crawl_queue.empty():
            try:
                self._crawl_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._visited_urls.clear()
        self._content_hashes.clear()
        self._domain_last_access.clear()
        self._robots_cache.clear()

        self.logger.debug("Crawler cleaned up")

    async def start_crawl(
        self,
        project_id: str,
        user_agent: Optional[str] = None,
        rate_limit: float = 1.0,
        max_pages: Optional[int] = None,
        progress_display: Optional[Any] = None,
        error_reporter: Optional[Any] = None
    ) -> CrawlSession:
        """Start a new crawl session for a project."""
        if self._is_running:
            raise CrawlerError("Crawler is already running")

        # Get project
        project = await self.db_manager.get_project(project_id)
        if not project:
            raise CrawlerError(f"Project {project_id} not found")

        # Create crawl session
        session = await self.db_manager.create_crawl_session(
            project_id=project_id,
            crawl_depth=project.crawl_depth,
            user_agent=user_agent or "DocBro/1.0",
            rate_limit=rate_limit
        )

        self._current_session = session
        self._is_running = True
        self._stop_requested = False

        # Initialize crawler
        await self.initialize()

        # Set user agent
        self._client.headers["User-Agent"] = session.user_agent

        # Clear state and create fresh queue
        self._visited_urls.clear()
        self._content_hashes.clear()
        self._domain_last_access.clear()
        self._robots_cache.clear()
        self._crawl_queue = asyncio.Queue()

        # Add initial URL to queue BEFORE creating the task
        await self._crawl_queue.put((project.source_url, 0, None))
        self.logger.debug(f"Added initial URL to queue: {project.source_url}, queue size: {self._crawl_queue.qsize()}")

        # Update session status
        session.start_session()
        await self.db_manager.update_crawl_session(session)

        # Now start crawl worker task AFTER queue is set up
        self._crawl_task = asyncio.create_task(self._crawl_worker(
            project, session, max_pages, progress_display, error_reporter
        ))

        self.logger.debug("Crawl started", extra={
            "project_id": project_id,
            "session_id": session.id,
            "source_url": project.source_url
        })

        return session

    async def _crawl_worker(
        self,
        project: Project,
        session: CrawlSession,
        max_pages: Optional[int] = None,
        progress_display: Optional[Any] = None,
        error_reporter: Optional[Any] = None
    ) -> None:
        """Main crawl worker loop."""
        try:
            pages_crawled = 0
            pages_errors = 0
            current_depth = 0
            self.logger.info(f"Starting crawl worker loop, initial queue size: {self._crawl_queue.qsize()}, max_depth: {project.crawl_depth}")

            while not self._stop_requested:
                if max_pages and pages_crawled >= max_pages:
                    self.logger.info(f"Maximum pages reached: {pages_crawled} >= {max_pages}")
                    break

                try:
                    self.logger.debug(f"Attempting to get from queue, current size: {self._crawl_queue.qsize()}")
                    # Get next URL from queue with timeout
                    # Use a longer timeout to ensure we wait for pages to be processed
                    # This prevents premature stopping when pages are still being fetched
                    timeout_seconds = 60.0 if current_depth < project.crawl_depth else 30.0

                    url, depth, parent_url = await asyncio.wait_for(
                        self._crawl_queue.get(),
                        timeout=timeout_seconds
                    )
                    self.logger.debug(f"Got URL from queue: {url}, depth: {depth}")

                    # Update progress with current depth and counts
                    if depth != current_depth:
                        current_depth = depth

                    # Update progress display if available
                    if progress_display:
                        progress_display.update(
                            depth=depth,
                            pages=pages_crawled,
                            errors=pages_errors,
                            queue=self._crawl_queue.qsize(),
                            url=url
                        )
                except asyncio.TimeoutError:
                    # Check if we should really stop
                    # If we haven't exceeded max depth and we have crawled pages, we might still be processing
                    if current_depth < project.crawl_depth and pages_crawled > 0:
                        # Give it more time - pages might still be processing
                        self.logger.info(f"Queue empty but still at depth {current_depth}/{project.crawl_depth}, waiting for more URLs...")
                        await asyncio.sleep(10.0)  # Wait longer for pages to be processed
                        # Check queue again
                        if self._crawl_queue.qsize() > 0:
                            self.logger.info(f"Queue refilled with {self._crawl_queue.qsize()} URLs, continuing...")
                            continue

                    # No more URLs to process
                    self.logger.info(f"Queue timeout - stopping crawl. Final depth: {current_depth}, Queue size: {self._crawl_queue.qsize()}")
                    break

                # Skip if already visited
                if url in self._visited_urls:
                    self.logger.debug(f"Skipping already visited URL: {url}")
                    continue

                # Skip if depth exceeded
                if depth > project.crawl_depth:
                    self.logger.info(f"Skipping URL due to depth {depth} > {project.crawl_depth}: {url}")
                    continue

                # Mark as visited
                self._visited_urls.add(url)
                self.logger.debug(f"Marked URL as visited: {url}")

                # Check robots.txt
                self.logger.debug(f"Checking robots.txt for URL: {url}")
                robots_allowed = await self.check_robots_allowed(url, session.user_agent)
                self.logger.debug(f"Robots.txt check result for {url}: {robots_allowed}")
                if not robots_allowed:
                    self.logger.debug(f"Robots.txt disallows URL: {url}")
                    continue
                self.logger.debug(f"Robots.txt allows URL: {url}")

                # Apply rate limiting
                await self._apply_rate_limit(url, session.rate_limit)

                # Create page record
                page = await self.db_manager.create_page(
                    project_id=project.id,
                    session_id=session.id,
                    url=url,
                    crawl_depth=depth,
                    parent_url=parent_url
                )

                # Crawl the page
                crawl_result = await self.crawl_page(url)

                if crawl_result and not crawl_result.get("error"):
                    # Update page with content
                    page.update_content(
                        title=crawl_result.get("title"),
                        content_html=crawl_result.get("content_html"),
                        content_text=crawl_result.get("content_text"),
                        mime_type=crawl_result.get("mime_type", "text/html"),
                        charset=crawl_result.get("charset", "utf-8")
                    )

                    # Check for duplicate content
                    if page.content_hash in self._content_hashes:
                        page.mark_skipped("Duplicate content")
                    else:
                        self._content_hashes.add(page.content_hash)
                        page.mark_crawled(
                            response_code=crawl_result.get("status_code", 200),
                            response_time_ms=crawl_result.get("response_time_ms", 0)
                        )

                        # Extract and queue links
                        links = crawl_result.get("links", [])
                        page.outbound_links = links
                        page.categorize_links(urlparse(project.source_url).netloc)

                        # Queue internal links
                        self.logger.info(f"Found {len(page.internal_links)} internal links on {url} (current depth: {depth})")
                        queued_count = 0
                        for link in page.internal_links:
                            if link not in self._visited_urls:
                                new_depth = depth + 1
                                if new_depth <= project.crawl_depth:
                                    self.logger.debug(f"Queueing link: {link} at depth {new_depth}")
                                    await self._crawl_queue.put((link, new_depth, url))
                                    queued_count += 1
                                else:
                                    self.logger.debug(f"Skipping link (would be depth {new_depth} > {project.crawl_depth}): {link}")
                            else:
                                self.logger.debug(f"Skipping already visited link: {link}")

                        self.logger.info(f"Queued {queued_count} new links from {url}")

                        pages_crawled += 1

                        # Update progress display after successful crawl
                        if progress_display:
                            progress_display.update(
                                depth=depth,
                                pages=pages_crawled,
                                errors=pages_errors,
                                queue=self._crawl_queue.qsize(),
                                url=url
                            )
                else:
                    # Handle crawl error
                    error_msg = crawl_result.get("error") if crawl_result else "Unknown error"
                    page.mark_failed(error_msg)
                    pages_errors += 1

                    if error_reporter:
                        error_reporter.add_error(url, error_msg, depth)

                    if session.increment_error_count():
                        self.logger.debug("Max errors reached, stopping crawl", extra={
                            "session_id": session.id,
                            "error_count": session.error_count
                        })
                        break

                # Update page in database
                await self.db_manager.update_page(page)

                # Update session progress
                session.update_progress(
                    pages_discovered=len(self._visited_urls),
                    pages_crawled=pages_crawled,
                    pages_failed=session.error_count
                )
                await self.db_manager.update_crawl_session(session)

            # Complete session
            session.complete_session()
            await self.db_manager.update_crawl_session(session)

            self.logger.debug("Crawl completed", extra={
                "session_id": session.id,
                "pages_crawled": pages_crawled,
                "pages_discovered": len(self._visited_urls)
            })

        except Exception as e:
            self.logger.debug("Crawl worker error", extra={
                "session_id": session.id,
                "error": str(e)
            })
            session.fail_session(str(e))
            await self.db_manager.update_crawl_session(session)

        finally:
            self._is_running = False
            self._current_session = None

    async def crawl_page(self, url: str) -> Dict[str, Any]:
        """Crawl a single page and extract content."""
        try:
            start_time = time.time()

            # Make HTTP request
            response = await self._client.get(url)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return {
                    "url": url,
                    "error": f"Unsupported content type: {content_type}"
                }

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string or ""

            # Extract text content
            text_content = self._extract_text(soup)

            # Extract links
            links = self.extract_links(response.text, url)

            # Calculate content hash
            content_hash = hashlib.sha256(text_content.encode()).hexdigest()

            return {
                "url": url,
                "title": title.strip(),
                "content_html": response.text,
                "content_text": text_content,
                "content_hash": content_hash,
                "links": links,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "mime_type": "text/html",
                "charset": response.encoding or "utf-8"
            }

        except httpx.TimeoutException:
            return {"url": url, "error": "Request timeout"}
        except httpx.RequestError as e:
            return {"url": url, "error": f"Request error: {str(e)}"}
        except Exception as e:
            self.logger.debug("Failed to crawl page", extra={
                "url": url,
                "error": str(e)
            })
            return {"url": url, "error": str(e)}

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML."""
        # Remove script and style elements
        for element in soup(["script", "style", "meta", "link", "noscript"]):
            element.decompose()

        # Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Get text
        text = soup.get_text(separator=" ")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return text

    def extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract all links from HTML content."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            links = []

            for tag in soup.find_all(["a", "link"]):
                href = tag.get("href")
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)

                    # Parse and clean URL
                    parsed = urlparse(absolute_url)

                    # Skip non-HTTP(S) URLs
                    if parsed.scheme not in ["http", "https"]:
                        continue

                    # Remove fragment
                    clean_url = urlunparse(
                        (parsed.scheme, parsed.netloc, parsed.path,
                         parsed.params, parsed.query, "")
                    )

                    links.append(clean_url)

            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)

            return unique_links

        except Exception as e:
            self.logger.debug("Failed to extract links", extra={
                "base_url": base_url,
                "error": str(e)
            })
            return []

    async def check_robots_allowed(self, url: str, user_agent: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            # Check cache
            if robots_url not in self._robots_cache:
                # Fetch and parse robots.txt
                rp = RobotFileParser()
                rp.set_url(robots_url)

                try:
                    response = await self._client.get(robots_url, timeout=5.0)
                    if response.status_code == 200:
                        # Check if it's actually a robots.txt file (text/plain)
                        content_type = response.headers.get("content-type", "").lower()
                        if "text/plain" in content_type or response.text.startswith("User-agent:") or response.text.startswith("user-agent:"):
                            # Parse robots.txt content
                            rp.parse(response.text.splitlines())
                        else:
                            # Not a robots.txt file (probably HTML 404 page), allow all
                            self.logger.debug(f"Response is not robots.txt (content-type: {content_type}), allowing all")
                    elif response.status_code == 404:
                        # No robots.txt exists, allow all
                        self.logger.debug("No robots.txt found (404), allowing all")
                    else:
                        # Other status codes, be conservative and check
                        self.logger.debug(f"Robots.txt returned status {response.status_code}, allowing all")
                except Exception as e:
                    # If robots.txt cannot be fetched, assume allowed
                    self.logger.debug(f"Failed to fetch robots.txt from {robots_url}: {e}")
                    pass  # RobotFileParser allows all by default when empty

                self._robots_cache[robots_url] = rp

            # Check if URL is allowed
            rp = self._robots_cache[robots_url]
            # If no rules were parsed (empty robots or non-robots content), allow all
            if not rp.entries:
                return True
            return rp.can_fetch(user_agent, url)

        except Exception as e:
            self.logger.debug("Failed to check robots.txt", extra={
                "url": url,
                "error": str(e)
            })
            # Default to allowing if check fails
            return True

    async def _apply_rate_limit(self, url: str, rate_limit: float) -> None:
        """Apply rate limiting per domain."""
        domain = urlparse(url).netloc

        if domain in self._domain_last_access:
            elapsed = time.time() - self._domain_last_access[domain]
            wait_time = (1.0 / rate_limit) - elapsed

            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self._domain_last_access[domain] = time.time()

    async def stop_crawl(self, session_id: str) -> bool:
        """Stop an active crawl session."""
        if self._current_session and self._current_session.id == session_id:
            self._stop_requested = True
            self.logger.info("Stop requested for crawl", extra={
                "session_id": session_id
            })
            return True
        return False

    async def pause_crawl(self, session_id: str) -> bool:
        """Pause an active crawl session."""
        if self._current_session and self._current_session.id == session_id:
            self._current_session.pause_session()
            await self.db_manager.update_crawl_session(self._current_session)
            self._stop_requested = True
            return True
        return False

    async def resume_crawl(self, session_id: str) -> CrawlSession:
        """Resume a paused crawl session."""
        session = await self.db_manager.get_crawl_session(session_id)
        if not session:
            raise CrawlerError(f"Session {session_id} not found")

        if session.status != CrawlStatus.PAUSED:
            raise CrawlerError(f"Session is not paused: {session.status}")

        # TODO: Implement resume logic
        # This would need to reconstruct the crawl state from the database
        raise NotImplementedError("Resume crawl not fully implemented yet")

    async def complete_crawl(self, session_id: str) -> CrawlSession:
        """Mark a crawl session as completed."""
        session = await self.db_manager.get_crawl_session(session_id)
        if not session:
            raise CrawlerError(f"Session {session_id} not found")

        session.complete_session()
        await self.db_manager.update_crawl_session(session)

        return session

    async def get_crawled_pages(self, session_id: str) -> List[Page]:
        """Get all pages crawled in a session."""
        # This would need to be implemented in the database manager
        # For now, return empty list
        return []

    async def get_crawl_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a crawl session."""
        session = await self.db_manager.get_crawl_session(session_id)
        if not session:
            raise CrawlerError(f"Session {session_id} not found")

        return {
            "pages_crawled": session.pages_crawled,
            "pages_failed": session.pages_failed,
            "pages_skipped": session.pages_skipped,
            "total_size": session.total_size_bytes,
            "average_page_size": (
                session.total_size_bytes / session.pages_crawled
                if session.pages_crawled > 0 else 0
            ),
            "crawl_duration": session.get_duration()
        }

    async def wait_for_completion(
        self,
        session_id: str,
        timeout: Optional[float] = None
    ) -> CrawlSession:
        """Wait for a crawl session to complete."""
        start_time = time.time()

        while True:
            session = await self.db_manager.get_crawl_session(session_id)
            if not session:
                raise CrawlerError(f"Session {session_id} not found")

            if session.is_completed():
                return session

            if timeout and (time.time() - start_time) > timeout:
                raise CrawlerError(f"Timeout waiting for session {session_id}")

            await asyncio.sleep(1.0)

    async def mark_crawl_failed(self, session_id: str, error: str) -> CrawlSession:
        """Mark a crawl session as failed."""
        session = await self.db_manager.get_crawl_session(session_id)
        if not session:
            raise CrawlerError(f"Session {session_id} not found")

        session.fail_session(error)
        await self.db_manager.update_crawl_session(session)

        return session

    async def retry_crawl(self, project_id: str) -> CrawlSession:
        """Start a new crawl session for retry."""
        return await self.start_crawl(project_id)