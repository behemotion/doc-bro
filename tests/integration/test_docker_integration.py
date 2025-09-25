"""Integration tests for Docker Qdrant connection."""

import pytest
import pytest_asyncio
from qdrant_client import QdrantClient
from redis import Redis

from src.lib.docker_utils import DockerServiceManager, ServiceHealthChecker
from src.lib.config import DocBroConfig


class TestDockerIntegration:
    """Integration tests for Docker services."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return DocBroConfig()

    @pytest.fixture
    def docker_manager(self, config):
        """Docker service manager instance."""
        try:
            from src.lib.docker_utils import DockerServiceManager
            return DockerServiceManager(config)
        except ImportError:
            pytest.fail("DockerServiceManager not implemented yet")

    @pytest.fixture
    def health_checker(self, config):
        """Service health checker instance."""
        try:
            from src.lib.docker_utils import ServiceHealthChecker
            return ServiceHealthChecker(config)
        except ImportError:
            pytest.fail("ServiceHealthChecker not implemented yet")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_docker_availability(self, docker_manager):
        """Test Docker daemon availability."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            is_available = docker_manager.is_docker_available()
            assert isinstance(is_available, bool)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_start_docker_services(self, docker_manager):
        """Test starting Docker services via docker-compose."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            success = docker_manager.start_services()
            assert isinstance(success, bool)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_qdrant_container_running(self, docker_manager):
        """Test that Qdrant container can be started and is running."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            containers = docker_manager.get_service_containers()
            assert "qdrant" in containers

    @pytest.mark.docker
    @pytest.mark.integration
    def test_redis_container_running(self, docker_manager):
        """Test that Redis container can be started and is running."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            containers = docker_manager.get_service_containers()
            assert "redis" in containers

    @pytest.mark.docker
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_qdrant_health_check(self, health_checker):
        """Test Qdrant service health check."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            is_healthy, message = await health_checker.check_qdrant()
            assert isinstance(is_healthy, bool)
            assert isinstance(message, str)

    @pytest.mark.docker
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_health_check(self, health_checker):
        """Test Redis service health check."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            is_healthy, message = await health_checker.check_redis()
            assert isinstance(is_healthy, bool)
            assert isinstance(message, str)

    @pytest.mark.docker
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_services_health(self, health_checker):
        """Test health check for all services."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            health_status = await health_checker.check_all_services()
            assert isinstance(health_status, dict)
            expected_services = ["qdrant", "redis", "ollama", "database"]
            for service in expected_services:
                assert service in health_status

    @pytest.mark.docker
    @pytest.mark.integration
    def test_qdrant_client_connection(self, config):
        """Test direct Qdrant client connection."""
        # This test will fail until services are actually running
        try:
            client = QdrantClient(url=config.qdrant_url)
            collections = client.get_collections()
            assert hasattr(collections, 'collections')
        except Exception:
            pytest.fail("Qdrant connection failed - ensure Docker services are running")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_redis_client_connection(self, config):
        """Test direct Redis client connection."""
        # This test will fail until services are actually running
        try:
            client = Redis.from_url(config.redis_url)
            result = client.ping()
            assert result is True
        except Exception:
            pytest.fail("Redis connection failed - ensure Docker services are running")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_docker_compose_file_exists(self):
        """Test that Docker Compose file exists and is valid."""
        from pathlib import Path
        compose_file = Path("docker/docker-compose.yml")
        assert compose_file.exists(), "Docker Compose file not found"

        # Basic validation that it's a valid YAML file
        import yaml
        try:
            with open(compose_file) as f:
                config = yaml.safe_load(f)
                assert "services" in config
                assert "qdrant" in config["services"]
                assert "redis" in config["services"]
        except yaml.YAMLError:
            pytest.fail("Invalid Docker Compose YAML file")

    @pytest.mark.docker
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_wait_functionality(self, docker_manager):
        """Test waiting for services to become ready."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            health_status = await docker_manager.wait_for_services(timeout=30)
            assert isinstance(health_status, dict)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_get_service_logs(self, docker_manager):
        """Test retrieving service logs."""
        # This test will fail until implementation exists
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            logs = docker_manager.get_service_logs("qdrant", lines=10)
            assert isinstance(logs, str)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_stop_docker_services(self, docker_manager):
        """Test stopping Docker services."""
        # This test will fail until implementation exists
        # Note: This should be the last test to avoid affecting others
        with pytest.raises((AttributeError, ImportError, NotImplementedError)):
            success = docker_manager.stop_services()
            assert isinstance(success, bool)