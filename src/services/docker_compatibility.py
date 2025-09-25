"""Docker API compatibility layer for handling different Docker versions."""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List, Tuple
from packaging import version

try:
    import docker
    from docker.models.containers import Container
    from docker.errors import DockerException, NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    Container = None
    DockerException = Exception
    NotFound = Exception
    APIError = Exception
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)


class DockerAPICompatibility:
    """Handles Docker API version compatibility across different Docker versions."""

    # Known API versions and their Docker engine versions
    API_VERSION_MAP = {
        "1.24": "1.12.0",  # Minimum supported
        "1.25": "1.13.0",
        "1.26": "1.13.1",
        "1.27": "17.03.0",
        "1.28": "17.04.0",
        "1.29": "17.05.0",
        "1.30": "17.06.0",
        "1.31": "17.07.0",
        "1.32": "17.09.0",
        "1.33": "17.10.0",
        "1.34": "17.11.0",
        "1.35": "17.12.0",
        "1.36": "18.02.0",
        "1.37": "18.03.0",
        "1.38": "18.06.0",
        "1.39": "18.09.0",
        "1.40": "19.03.0",
        "1.41": "20.10.0",
        "1.42": "20.10.7",
        "1.43": "21.xx",
        "1.44": "24.0",
        "1.45": "25.0",
        "1.46": "26.0",
        "1.47": "27.0",
        "1.48": "27.1",
        "1.49": "27.2",
        "1.50": "27.3",
        "1.51": "28.0",
    }

    def __init__(self):
        """Initialize compatibility layer."""
        self.client: Optional[Any] = None
        self.server_version: Optional[str] = None
        self.api_version: Optional[str] = None
        self.negotiated_version: Optional[str] = None

    async def create_client(self, max_retries: int = 3) -> Optional[Any]:
        """Create Docker client with automatic version negotiation.

        Args:
            max_retries: Maximum number of retries for version negotiation

        Returns:
            Docker client or None if connection failed
        """
        if not DOCKER_AVAILABLE:
            logger.error("Docker package not installed")
            return None

        # Try different connection methods
        connection_methods = [
            self._try_auto_version,
            self._try_from_env,
            self._try_explicit_versions,
            self._try_minimum_version
        ]

        for method in connection_methods:
            try:
                client = await method()
                if client and await self._validate_client(client):
                    self.client = client
                    logger.info(f"Docker client created with API version: {self.negotiated_version}")
                    return client
            except Exception as e:
                logger.debug(f"Connection method {method.__name__} failed: {e}")
                continue

        logger.error("Failed to create Docker client with any method")
        return None

    async def _try_auto_version(self) -> Optional[Any]:
        """Try creating client with automatic version negotiation."""
        try:
            # Let docker-py negotiate the version
            client = docker.from_env(version='auto')
            self.negotiated_version = client.api._version
            return client
        except Exception as e:
            logger.debug(f"Auto version negotiation failed: {e}")
            return None

    async def _try_from_env(self) -> Optional[Any]:
        """Try creating client from environment."""
        try:
            client = docker.from_env()
            # Get the negotiated version
            info = client.version()
            self.server_version = info.get('Version')
            self.api_version = info.get('ApiVersion')
            self.negotiated_version = client.api._version
            return client
        except Exception as e:
            logger.debug(f"from_env failed: {e}")
            return None

    async def _try_explicit_versions(self) -> Optional[Any]:
        """Try explicit API versions from newest to oldest."""
        # Sort versions in descending order
        versions_to_try = sorted(self.API_VERSION_MAP.keys(),
                                key=lambda x: float(x),
                                reverse=True)

        for api_ver in versions_to_try:
            try:
                # Try with environment variable first
                os.environ['DOCKER_API_VERSION'] = api_ver
                client = docker.from_env()

                # Test the connection
                client.ping()
                self.negotiated_version = api_ver
                return client
            except Exception:
                continue
            finally:
                # Clean up environment variable
                os.environ.pop('DOCKER_API_VERSION', None)

        return None

    async def _try_minimum_version(self) -> Optional[Any]:
        """Try with minimum supported version."""
        try:
            # Use minimum API version for maximum compatibility
            client = docker.DockerClient(
                base_url='unix://var/run/docker.sock',
                version='1.24'  # Minimum version
            )
            client.ping()
            self.negotiated_version = '1.24'
            return client
        except Exception as e:
            logger.debug(f"Minimum version failed: {e}")
            return None

    async def _validate_client(self, client: Any) -> bool:
        """Validate that the client works."""
        try:
            # Try a simple operation
            client.ping()

            # Try to get version info
            version_info = client.version()
            self.server_version = version_info.get('Version', 'unknown')
            self.api_version = version_info.get('ApiVersion', 'unknown')

            logger.debug(f"Docker server version: {self.server_version}, API: {self.api_version}")
            return True
        except Exception as e:
            logger.debug(f"Client validation failed: {e}")
            return False

    def get_compatible_features(self) -> Dict[str, bool]:
        """Get list of features compatible with current Docker version."""
        if not self.negotiated_version:
            return {}

        api_ver = float(self.negotiated_version)

        return {
            'health_check': api_ver >= 1.25,
            'init_process': api_ver >= 1.25,
            'runtime_selection': api_ver >= 1.30,
            'device_requests': api_ver >= 1.40,  # GPU support
            'platform_selection': api_ver >= 1.32,
            'secrets': api_ver >= 1.25,
            'configs': api_ver >= 1.30,
            'rollback': api_ver >= 1.28,
            'isolation': api_ver >= 1.24,
        }

    async def safe_container_operation(self, operation: str, *args, **kwargs) -> Any:
        """Execute container operation with version compatibility handling."""
        if not self.client:
            raise DockerException("Docker client not initialized")

        # Remove unsupported parameters based on API version
        features = self.get_compatible_features()

        if operation == 'run' and 'init' in kwargs and not features.get('init_process'):
            kwargs.pop('init', None)

        if operation == 'run' and 'runtime' in kwargs and not features.get('runtime_selection'):
            kwargs.pop('runtime', None)

        if operation == 'run' and 'device_requests' in kwargs and not features.get('device_requests'):
            kwargs.pop('device_requests', None)

        try:
            method = getattr(self.client.containers, operation)
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: method(*args, **kwargs)
            )
        except APIError as e:
            # Handle version-specific errors
            if 'client version' in str(e).lower() or 'api version' in str(e).lower():
                logger.error(f"API version mismatch for operation {operation}: {e}")
                # Try to downgrade the request
                return await self._retry_with_downgrade(operation, args, kwargs)
            raise

    async def _retry_with_downgrade(self, operation: str, args: tuple, kwargs: dict) -> Any:
        """Retry operation with downgraded parameters."""
        # Remove newer features
        downgrade_params = ['init', 'runtime', 'device_requests', 'platform',
                          'isolation', 'storage_opt', 'sysctls', 'userns_mode']

        for param in downgrade_params:
            kwargs.pop(param, None)

        try:
            method = getattr(self.client.containers, operation)
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: method(*args, **kwargs)
            )
        except Exception as e:
            logger.error(f"Downgraded operation {operation} still failed: {e}")
            raise


class DockerManagerCompatible:
    """Docker manager with built-in compatibility handling."""

    def __init__(self):
        """Initialize compatible Docker manager."""
        self.compat = DockerAPICompatibility()
        self.client: Optional[Any] = None
        self._connected = False

    async def connect(self, timeout: float = 10.0) -> bool:
        """Connect to Docker with automatic version negotiation.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully
        """
        try:
            # Use compatibility layer to create client
            self.client = await asyncio.wait_for(
                self.compat.create_client(),
                timeout=timeout
            )

            if self.client:
                self._connected = True
                logger.info(f"Connected to Docker (API: {self.compat.negotiated_version})")
                return True
            else:
                logger.error("Failed to create Docker client")
                return False

        except asyncio.TimeoutError:
            logger.error(f"Docker connection timed out after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Docker connection failed: {e}")
            return False

    async def get_version_info(self) -> Dict[str, Any]:
        """Get Docker version and compatibility information."""
        if not self._connected:
            await self.connect()

        if not self.client:
            return {
                'connected': False,
                'error': 'Not connected to Docker'
            }

        return {
            'connected': True,
            'server_version': self.compat.server_version,
            'api_version': self.compat.api_version,
            'negotiated_version': self.compat.negotiated_version,
            'features': self.compat.get_compatible_features()
        }

    async def list_containers(self, all: bool = True) -> List[Container]:
        """List containers with compatibility handling."""
        if not self._connected:
            await self.connect()

        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.containers.list(all=all)
            )
        except APIError as e:
            if 'api version' in str(e).lower():
                logger.warning("API version issue, retrying with basic parameters")
                # Try without any parameters
                return await asyncio.get_event_loop().run_in_executor(
                    None, self.client.containers.list
                )
            raise

    async def create_container(self, image: str, name: str, **kwargs) -> Container:
        """Create container with compatibility handling."""
        if not self._connected:
            await self.connect()

        # Use compatibility layer for container creation
        return await self.compat.safe_container_operation(
            'run', image=image, name=name, detach=True, **kwargs
        )

    async def get_container(self, name: str) -> Optional[Container]:
        """Get container by name with compatibility handling."""
        if not self._connected:
            await self.connect()

        try:
            containers = await self.list_containers(all=True)
            for container in containers:
                if container.name == name or name in container.name:
                    return container
            return None
        except Exception as e:
            logger.error(f"Failed to get container {name}: {e}")
            return None

    async def check_health(self) -> Dict[str, Any]:
        """Check Docker health with version information."""
        try:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return {
                        'healthy': False,
                        'error': 'Cannot connect to Docker',
                        'version_info': None
                    }

            # Get version info
            version_info = await self.get_version_info()

            # Try a simple operation
            await self.list_containers()

            return {
                'healthy': True,
                'version_info': version_info,
                'compatibility': self.compat.get_compatible_features()
            }

        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'version_info': await self.get_version_info()
            }

    async def disconnect(self):
        """Disconnect from Docker."""
        if self.client:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.client.close
                )
            except Exception as e:
                logger.warning(f"Error closing Docker client: {e}")
            finally:
                self.client = None
                self._connected = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()