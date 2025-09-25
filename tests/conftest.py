"""Test configuration and fixtures for DocBro."""

import asyncio
import os
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime

import pytest
import pytest_asyncio
from qdrant_client import QdrantClient

# Test configuration
TEST_QDRANT_URL = "http://localhost:6333"
TEST_OLLAMA_URL = "http://localhost:11434"
TEST_UV_VERSION = "0.4.0"
TEST_PYTHON_VERSION = "3.13.1"
TEST_DOCBRO_VERSION = "0.2.1"


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
def mock_installation_environment() -> Generator[Dict[str, Any], None, None]:
    """Mock environment for UV installation testing."""
    mock_env = {
        "mock_uv_available": True,
        "mock_uv_version": TEST_UV_VERSION,
        "mock_python_version": TEST_PYTHON_VERSION,
        "mock_docbro_version": TEST_DOCBRO_VERSION,
        "mock_install_path": "/home/user/.local/bin/docbro",
    }
    yield mock_env


@pytest.fixture
def mock_uv_commands(mock_installation_environment):
    """Mock UV command execution for testing."""
    with patch('subprocess.run') as mock_run, \
         patch('shutil.which') as mock_which:

        # Mock UV installation detection
        mock_which.side_effect = lambda cmd: {
            'uv': '/home/user/.local/bin/uv' if mock_installation_environment['mock_uv_available'] else None,
            'docbro': mock_installation_environment['mock_install_path']
        }.get(cmd)

        # Mock UV version command
        mock_run.return_value = Mock(
            returncode=0,
            stdout=f"uv {mock_installation_environment['mock_uv_version']}",
            stderr=""
        )

        yield {
            'mock_run': mock_run,
            'mock_which': mock_which
        }


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
def mock_temp_directories():
    """Mock temporary directories for installation testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        mock_dirs = {
            "config_dir": temp_path / ".config" / "docbro",
            "data_dir": temp_path / ".local" / "share" / "docbro",
            "cache_dir": temp_path / ".cache" / "docbro"
        }

        # Create directories
        for dir_path in mock_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            # Set permissions (700 - user only)
            dir_path.chmod(0o700)

        yield mock_dirs


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


@pytest.fixture
def mock_installation_context():
    """Mock InstallationContext for testing."""
    from src.models.installation import InstallationContext

    return InstallationContext(
        install_method="uvx",
        install_date=datetime.now(),
        version=TEST_DOCBRO_VERSION,
        python_version=TEST_PYTHON_VERSION,
        uv_version=TEST_UV_VERSION,
        install_path=Path("/home/user/.local/bin/docbro"),
        is_global=True,
        user_data_dir=Path.home() / ".local" / "share" / "docbro",
        config_dir=Path.home() / ".config" / "docbro",
        cache_dir=Path.home() / ".cache" / "docbro"
    )


@pytest.fixture
def mock_service_status():
    """Mock ServiceStatus for testing."""
    from src.models.installation import ServiceStatus

    def _create_status(name: str, available: bool = True, version: str = None):
        return ServiceStatus(
            name=name,
            available=available,
            version=version,
            last_checked=datetime.now(),
            error_message=None if available else f"{name} not available",
            setup_completed=available  # Add the required setup_completed field
        )

    return _create_status


@pytest_asyncio.fixture
async def mock_async_service_detection():
    """Mock async service detection for testing."""
    from src.services.detection import ServiceDetectionService
    from src.models.installation import ServiceStatus

    with patch.object(ServiceDetectionService, 'check_all_services') as mock_check:
        mock_services = {
            "docker": ServiceStatus(
                name="docker",
                available=True,
                version="24.0.0",
                last_checked=datetime.now(),
                error_message=None,
                setup_completed=True
            ),
            "ollama": ServiceStatus(
                name="ollama",
                available=True,
                version="0.1.7",
                last_checked=datetime.now(),
                error_message=None,
                setup_completed=True
            ),
            "qdrant": ServiceStatus(
                name="qdrant",
                available=True,
                version="1.13.0",
                last_checked=datetime.now(),
                error_message=None,
                setup_completed=True
            )
        }

        mock_check.return_value = mock_services
        yield mock_check


@pytest.fixture
def uv_installation_validator():
    """Fixture for UV installation validation testing."""
    class UVInstallationValidator:
        def __init__(self):
            self.validation_results = {
                "uv_available": True,
                "uv_version_valid": True,
                "python_version_valid": True,
                "docbro_installed": True,
                "docbro_version_valid": True,
                "config_directory_exists": True,
                "data_directory_exists": True,
                "cache_directory_exists": True
            }

        def validate_installation(self) -> Dict[str, bool]:
            """Validate UV installation completeness."""
            return self.validation_results.copy()

        def set_validation_failure(self, component: str):
            """Set a specific validation component to fail."""
            if component in self.validation_results:
                self.validation_results[component] = False

        def reset_validations(self):
            """Reset all validations to pass."""
            for key in self.validation_results:
                self.validation_results[key] = True

    return UVInstallationValidator()


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


# Docker container testing fixtures for setup wizard
@pytest.fixture
def mock_docker_client() -> MagicMock:
    """Mock Docker client for container testing."""
    mock_client = MagicMock()

    # Mock container operations
    mock_container = MagicMock()
    mock_container.name = "docbro-memory-qdrant"
    mock_container.status = "running"
    mock_container.ports = {"6333/tcp": [{"HostPort": "6333"}]}
    mock_container.attrs = {"Config": {"Image": "qdrant/qdrant"}}

    # Mock client methods
    mock_client.containers.list.return_value = [mock_container]
    mock_client.containers.get.return_value = mock_container
    mock_client.containers.run.return_value = mock_container
    mock_client.ping.return_value = True
    mock_client.images.pull.return_value = MagicMock()

    return mock_client


@pytest.fixture
def docker_container_test_env(mock_docker_client, temp_dir):
    """Test environment for Docker container operations."""
    return {
        "docker_client": mock_docker_client,
        "temp_dir": temp_dir,
        "container_name": "docbro-memory-qdrant",
        "test_port": 6333,
        "test_image": "qdrant/qdrant:latest"
    }


@pytest.fixture
def mock_progress_callback():
    """Mock progress callback for setup wizard testing."""
    def callback(step_id: str, status: str, message: str = "", duration: float = 0.0):
        """Mock progress callback that captures step updates."""
        pass
    return MagicMock(side_effect=callback)


@pytest.fixture
def setup_wizard_test_context(docker_container_test_env, mock_progress_callback):
    """Complete test context for setup wizard testing."""
    return {
        **docker_container_test_env,
        "progress_callback": mock_progress_callback,
        "retry_policy": {
            "max_attempts": 3,
            "delays": [2.0, 4.0, 8.0]
        }
    }


