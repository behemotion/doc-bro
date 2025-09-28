#!/usr/bin/env python
"""Test crawl directly with debug output."""

import asyncio
import logging
from src.services.database import DatabaseManager
from src.logic.crawler.core.crawler import DocumentationCrawler
from src.core.config import DocBroConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

async def test_crawl():
    config = DocBroConfig()
    config.log_level = "DEBUG"

    db = DatabaseManager(config)
    await db.initialize()

    crawler = DocumentationCrawler(db, config)
    # Enable debug logging
    crawler.logger.setLevel(logging.DEBUG)
    await crawler.initialize()

    try:
        # Get the project
        project = await db.get_project_by_name('google-adk')
        if not project:
            print("Project 'google-adk' not found")
            return

        print(f"Starting crawl for project: {project.name}")
        print(f"  crawl_depth: {project.crawl_depth}")
        print(f"  source_url: {project.source_url}")

        # Start crawl
        session = await crawler.start_crawl(
            project_id=project.id,
            rate_limit=1.0,
            max_pages=None  # No limit to see what happens
        )

        print(f"Crawl session started: {session.id}")

        # Monitor crawl for 30 seconds
        for i in range(15):
            await asyncio.sleep(2)

            session = await db.get_crawl_session(session.id)
            if not session:
                print("Session disappeared!")
                break

            print(f"Progress: Pages={session.pages_crawled}, Queue={crawler._crawl_queue.qsize()}, Visited={len(crawler._visited_urls)}")

            if session.is_completed():
                print(f"\nCrawl completed!")
                break

        print(f"\nFinal stats:")
        print(f"  Pages crawled: {session.pages_crawled}")
        print(f"  Pages failed: {session.pages_failed}")
        print(f"  Queue remaining: {crawler._crawl_queue.qsize()}")
        print(f"  URLs visited: {len(crawler._visited_urls)}")

    finally:
        await crawler.cleanup()
        await db.cleanup()

if __name__ == "__main__":
    asyncio.run(test_crawl())