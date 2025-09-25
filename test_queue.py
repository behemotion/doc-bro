#!/usr/bin/env python3
"""Test asyncio queue."""

import asyncio

async def test_queue():
    q = asyncio.Queue()

    # Add item
    await q.put(("https://example.com", 0, None))
    print(f"Queue size: {q.qsize()}")

    # Get item with timeout
    try:
        item = await asyncio.wait_for(q.get(), timeout=2.0)
        print(f"Got item: {item}")
    except asyncio.TimeoutError:
        print("Timeout getting from queue")

    print(f"Queue size after get: {q.qsize()}")

if __name__ == "__main__":
    asyncio.run(test_queue())