#!/usr/bin/env python
"""Test to understand the depth issue."""

import asyncio
from src.services.database import DatabaseManager
from logic.crawler.core.crawler import DocumentationCrawler
from src.core.config import DocBroConfig

async def test():
    config = DocBroConfig()
    db = DatabaseManager(config)
    await db.initialize()

    try:
        project = await db.get_project_by_name('google-adk')
        print(f"Project crawl_depth: {project.crawl_depth}")

        # Check what pages are in the database
        pages = await db.get_project_pages(project.id)

        depth_count = {}
        for page in pages:
            depth = page.crawl_depth
            depth_count[depth] = depth_count.get(depth, 0) + 1

        print(f"\nPages by depth:")
        for depth in sorted(depth_count.keys()):
            print(f"  Depth {depth}: {depth_count[depth]} pages")

        print(f"\nTotal pages: {len(pages)}")
        print(f"Pages with content: {len([p for p in pages if p.content_text])}")

    finally:
        await db.cleanup()

asyncio.run(test())