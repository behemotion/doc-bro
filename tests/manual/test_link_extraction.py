#!/usr/bin/env python
"""Test link extraction and categorization."""

import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

async def test_link_extraction():
    url = "https://google.github.io/adk-docs/"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"Fetched: {url}")
        print(f"Status: {response.status_code}")

        # Extract links
        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        for tag in soup.find_all(["a", "link"]):
            href = tag.get("href")
            if href:
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, href)

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

        # Remove duplicates
        unique_links = list(set(links))

        # Categorize links
        base_domain = urlparse(url).netloc
        internal_links = []
        external_links = []

        for link in unique_links:
            link_domain = urlparse(link).netloc
            if link_domain == base_domain or link_domain == "":
                internal_links.append(link)
            else:
                external_links.append(link)

        print(f"\nFound {len(unique_links)} unique links")
        print(f"  Internal: {len(internal_links)}")
        print(f"  External: {len(external_links)}")

        print("\nInternal links:")
        for link in sorted(internal_links)[:10]:  # Show first 10
            print(f"  - {link}")

        if len(internal_links) > 10:
            print(f"  ... and {len(internal_links) - 10} more")

if __name__ == "__main__":
    asyncio.run(test_link_extraction())