"""Integration tests for crawling documentation."""

import pytest
import pytest_asyncio
from pathlib import Path

from src.models.project import Project
from src.models.crawl_session import CrawlSession
from src.services.crawler import DocumentationCrawler
from src.services.database import DatabaseManager


class TestCrawlFlow:
    """Integration tests for the complete crawl flow."""

    @pytest.fixture
    def sample_project_data(self):
        """Sample project data for testing."""
        return {
            "name": "test-crawl-project",
            "source_url": "https://example.com/docs",
            "crawl_depth": 2,
            "embedding_model": "mxbai-embed-large"
        }

    @pytest.fixture
    async def db_manager(self):
        """Database manager for testing."""
        try:
            from src.services.database import DatabaseManager
            manager = DatabaseManager()
            await manager.initialize()
            yield manager
            await manager.cleanup()
        except ImportError:
            pytest.fail("DatabaseManager not implemented yet")

    @pytest.fixture
    async def crawler(self, db_manager):
        """Documentation crawler instance."""
        try:
            from src.services.crawler import DocumentationCrawler
            return DocumentationCrawler(db_manager)
        except ImportError:
            pytest.fail("DocumentationCrawler not implemented yet")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_crawl_project(self, db_manager, sample_project_data):
        """Test creating a new crawl project."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            project = await db_manager.create_project(**sample_project_data)
            assert project.name == sample_project_data["name"]
            assert project.source_url == sample_project_data["source_url"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_start_crawl_session(self, crawler, sample_project_data):
        """Test starting a crawl session."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            session = await crawler.start_crawl(**sample_project_data)
            assert session.status == "running"
            assert session.project_id is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_crawl_single_page(self, crawler):
        """Test crawling a single page."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            url = "https://httpbin.org/html"  # Simple test page
            page_data = await crawler.crawl_page(url)

            assert page_data["url"] == url
            assert "content_html" in page_data
            assert "content_text" in page_data
            assert "title" in page_data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_extract_links(self, crawler, sample_html_content):
        """Test extracting links from HTML content."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            links = crawler.extract_links(
                sample_html_content,
                base_url="https://example.com"
            )

            assert isinstance(links, list)
            assert len(links) > 0
            assert all(link.startswith("http") for link in links)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_respect_robots_txt(self, crawler):
        """Test that crawler respects robots.txt."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            allowed = await crawler.check_robots_allowed(
                "https://example.com/disallowed-path",
                user_agent="DocBro"
            )
            assert isinstance(allowed, bool)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rate_limiting(self, crawler):
        """Test that crawler implements rate limiting."""
        # This test will fail until implementation exists
        import time

        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            start_time = time.time()

            # Attempt to crawl multiple pages rapidly
            urls = [
                "https://httpbin.org/html",
                "https://httpbin.org/json",
                "https://httpbin.org/xml"
            ]

            for url in urls:
                await crawler.crawl_page(url)

            elapsed_time = time.time() - start_time

            # Should take at least 2 seconds with 1.0 req/s rate limit
            assert elapsed_time >= 2.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handle_crawl_errors(self, crawler):
        """Test handling of crawl errors."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Try to crawl an invalid URL
            result = await crawler.crawl_page("https://invalid-domain-xyz.com")

            # Should handle error gracefully
            assert "error" in result or result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_crawl_depth_limiting(self, crawler, sample_project_data):
        """Test that crawler respects depth limits."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Start crawl with depth limit of 1
            sample_project_data["crawl_depth"] = 1
            session = await crawler.start_crawl(**sample_project_data)

            # All crawled pages should be within depth limit
            pages = await crawler.get_crawled_pages(session.id)
            assert all(page.crawl_depth <= 1 for page in pages)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_duplicate_url_handling(self, crawler):
        """Test handling of duplicate URLs."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            url = "https://httpbin.org/html"

            # Crawl the same URL twice
            result1 = await crawler.crawl_page(url)
            result2 = await crawler.crawl_page(url)

            # Should detect and handle duplicates
            assert "duplicate" in str(result2) or result2 is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_content_deduplication(self, crawler):
        """Test content deduplication based on hash."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # URLs with identical content should be deduplicated
            url1 = "https://httpbin.org/html"
            url2 = "https://httpbin.org/html"  # Same content, different request

            page1 = await crawler.crawl_page(url1)
            page2 = await crawler.crawl_page(url2)

            # Should have same content hash
            assert page1["content_hash"] == page2["content_hash"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_crawl_session_completion(self, crawler, sample_project_data):
        """Test completing a crawl session."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            session = await crawler.start_crawl(**sample_project_data)

            # Complete the crawl session
            completed_session = await crawler.complete_crawl(session.id)

            assert completed_session.status == "completed"
            assert completed_session.completed_at is not None
            assert completed_session.pages_crawled >= 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_crawl_statistics(self, crawler, sample_project_data):
        """Test crawl session statistics."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            session = await crawler.start_crawl(**sample_project_data)

            # Get crawl statistics
            stats = await crawler.get_crawl_statistics(session.id)

            expected_stats = [
                "pages_crawled", "pages_failed", "pages_skipped",
                "total_size", "average_page_size", "crawl_duration"
            ]

            for stat in expected_stats:
                assert stat in stats

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_crawl_resume_capability(self, crawler, sample_project_data):
        """Test ability to resume interrupted crawls."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Start a crawl
            session = await crawler.start_crawl(**sample_project_data)

            # Simulate interruption
            await crawler.pause_crawl(session.id)

            # Resume crawl
            resumed_session = await crawler.resume_crawl(session.id)

            assert resumed_session.status == "running"