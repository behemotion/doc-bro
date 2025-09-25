#!/usr/bin/env python3
"""Debug script to test crawler directly."""

import asyncio
import logging
from src.services.database import DatabaseManager
from src.services.crawler import DocumentationCrawler
from src.lib.config import DocBroConfig

logging.basicConfig(level=logging.DEBUG)

async def test_crawl():
    config = DocBroConfig()
    config.redis_url = "redis://localhost:6380"

    db_manager = DatabaseManager(config)
    await db_manager.initialize()

    crawler = DocumentationCrawler(db_manager, config)
    await crawler.initialize()

    try:
        # Get test project
        project = await db_manager.get_project_by_name("test-project")
        if not project:
            print("Project not found")
            return

        print(f"Starting crawl for project: {project.name}")
        print(f"URL: {project.source_url}")

        # Start crawl
        session = await crawler.start_crawl(
            project_id=project.id,
            max_pages=1,
            rate_limit=1.0
        )

        print(f"Crawl session started: {session.id}")
        print(f"Status: {session.status}")

        # Wait for the crawl task to complete
        if crawler._crawl_task:
            print("Waiting for crawl task...")
            await crawler._crawl_task
            print("Crawl task completed")

        # Get final session status
        final_session = await db_manager.get_crawl_session(session.id)
        if final_session:
            print(f"Final status: {final_session.status}")
            print(f"Pages crawled: {final_session.pages_crawled}")
            print(f"Pages failed: {final_session.pages_failed}")

    finally:
        await crawler.cleanup()
        await db_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_crawl())