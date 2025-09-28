#!/usr/bin/env python3
"""Quick runner for UV compliance validation."""

import sys
import asyncio
from pathlib import Path

# Add the project root to the path so we can import the compliance validator
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.uv_compliance import main

if __name__ == "__main__":
    asyncio.run(main())