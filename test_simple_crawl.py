#!/usr/bin/env python3
"""Simple test to verify basic crawling works."""

import asyncio
import httpx

async def test_fetch():
    """Test basic fetching."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        print("Fetching https://example.com...")
        response = await client.get("https://example.com")
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        print(f"First 100 chars: {response.text[:100]}")

if __name__ == "__main__":
    asyncio.run(test_fetch())