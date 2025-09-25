"""Test configuration and fixtures for DocBro."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Test configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_QDRANT_URL = "http://localhost:6333"
TEST_OLLAMA_URL = "http://localhost:11434"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_qdrant_client() -> MagicMock:
    """Mock Qdrant client for testing."""
    mock_client = MagicMock(spec=QdrantClient)
    mock_client.get_collections.return_value = []
    mock_client.create_collection.return_value = True
    mock_client.delete_collection.return_value = True
    mock_client.search.return_value = []
    mock_client.upsert.return_value = True
    return mock_client




@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Import models to create tables
    from src.models import project, page, embedding, crawl_session, query_result, agent_session

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with AsyncSession(engine) as session:
        yield session

    # Clean up
    await engine.dispose()


@pytest.fixture
def mock_ollama_client() -> MagicMock:
    """Mock Ollama client for testing."""
    mock_client = MagicMock()
    mock_client.list.return_value = {"models": [
        {"name": "mxbai-embed-large"},
        {"name": "nomic-embed-text"}
    ]}
    mock_client.embeddings.return_value = {
        "embedding": [0.1, 0.2, 0.3] * 341  # 1024 dimensions
    }
    return mock_client


@pytest.fixture
def sample_html_content() -> str:
    """Sample HTML content for testing crawling."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Documentation</title>
    </head>
    <body>
        <h1>Welcome to Test Docs</h1>
        <p>This is a sample documentation page.</p>
        <a href="/page2">Next Page</a>
        <a href="/api/reference">API Reference</a>
        <div class="content">
            <h2>Section 1</h2>
            <p>Some important information here.</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_project_data() -> dict:
    """Sample project data for testing."""
    return {
        "name": "test-project",
        "source_url": "https://docs.example.com",
        "crawl_depth": 3,
        "embedding_model": "mxbai-embed-large",
        "status": "active"
    }


@pytest.fixture
def docker_available() -> bool:
    """Check if Docker services are available."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def skip_if_no_docker(docker_available: bool) -> None:
    """Skip test if Docker is not available."""
    if not docker_available:
        pytest.skip("Docker is not available")


@pytest.fixture
def qdrant_available() -> bool:
    """Check if Qdrant service is available."""
    try:
        client = QdrantClient(url=TEST_QDRANT_URL)
        client.get_collections()
        return True
    except Exception:
        return False


@pytest.fixture
def skip_if_no_qdrant(qdrant_available: bool) -> None:
    """Skip test if Qdrant is not available."""
    if not qdrant_available:
        pytest.skip("Qdrant is not available")






@pytest.fixture
def ollama_available() -> bool:
    """Check if Ollama service is available."""
    try:
        import httpx
        response = httpx.get(f"{TEST_OLLAMA_URL}/api/tags")
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def skip_if_no_ollama(ollama_available: bool) -> None:
    """Skip test if Ollama is not available."""
    if not ollama_available:
        pytest.skip("Ollama is not available")


# Docker compose fixtures for integration tests
@pytest.fixture(scope="session")
async def docker_services():
    """Start Docker services for integration tests."""
    if not os.getenv("DOCKER_INTEGRATION", "false").lower() == "true":
        pytest.skip("Docker integration tests disabled")

    import subprocess
    import time

    # Start Docker services
    subprocess.run(["docker-compose", "-f", "docker/docker-compose.yml", "up", "-d"],
                  check=True)

    # Wait for services to be ready
    time.sleep(10)

    yield

    # Cleanup
    subprocess.run(["docker-compose", "-f", "docker/docker-compose.yml", "down"],
                  check=True)


@pytest_asyncio.fixture
async def integration_qdrant_client(docker_services):
    """Real Qdrant client for integration tests."""
    client = QdrantClient(url=TEST_QDRANT_URL)
    yield client

    # Cleanup test collections
    collections = client.get_collections()
    for collection in collections.collections:
        if collection.name.startswith("test_"):
            client.delete_collection(collection.name)


