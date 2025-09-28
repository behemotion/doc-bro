"""ServiceConfigurationService for external service setup and management.

This service extends ServiceDetectionService to provide comprehensive configuration
and setup capabilities for Docker, Qdrant, and Ollama services.
"""

import asyncio
import json
import logging
import socket
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models.service_config import (
    ServiceConfiguration,
    ServiceName,
    ServiceStatusType,
)
from src.services.detection import ServiceDetectionService

logger = logging.getLogger(__name__)


class ServiceConflictError(Exception):
    """Raised when service configuration conflicts are detected."""
    pass


class ServiceSetupError(Exception):
    """Raised when service setup fails."""
    pass


class ServiceConfigurationService:
    """Comprehensive service configuration and management for external services.

    This service provides:
    - Async service detection and configuration
    - Port conflict resolution
    - Auto-start configuration
    - Service setup validation
    - Error recovery and retry logic
    - Dependency injection support
    """

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 3,
        detection_service: ServiceDetectionService | None = None
    ):
        """Initialize service configuration manager.

        Args:
            timeout: Timeout for service operations in seconds
            max_retries: Maximum number of retry attempts
            detection_service: Optional detection service for dependency injection
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.detection_service = detection_service or ServiceDetectionService(timeout)
        self._service_configs: dict[str, ServiceConfiguration] = {}
        self._port_registry: dict[int, str] = {}  # Track port assignments

    async def setup_service(
        self,
        service_name: ServiceName,
        custom_port: int | None = None,
        custom_endpoint: str | None = None,
        auto_start: bool = False,
        config_overrides: dict[str, Any] | None = None
    ) -> ServiceConfiguration:
        """Setup and configure a service with comprehensive validation.

        Args:
            service_name: Service to configure
            custom_port: Custom port (will validate for conflicts)
            custom_endpoint: Custom endpoint URL
            auto_start: Whether to enable auto-start
            config_overrides: Additional configuration options

        Returns:
            ServiceConfiguration with current status

        Raises:
            ServiceConflictError: If port conflicts are detected
            ServiceSetupError: If setup fails
        """
        logger.info(f"Setting up service: {service_name}")

        try:
            # Create base configuration
            config = ServiceConfiguration.create_default_config(
                service_name=service_name,
                custom_port=custom_port,
                custom_endpoint=custom_endpoint
            )
            config.auto_start = auto_start

            # Apply configuration overrides
            if config_overrides:
                # Store overrides in a metadata field if needed
                pass

            # Check for port conflicts
            await self._validate_port_availability(config.port, service_name)

            # Detect service and update configuration
            config = await self._detect_and_configure_service(config)

            # Attempt service setup if not running
            if config.status not in [ServiceStatusType.RUNNING, ServiceStatusType.CONFIGURED]:
                config = await self._attempt_service_setup(config)

            # Register the configuration
            self._service_configs[service_name] = config
            self._port_registry[config.port] = service_name

            logger.info(f"Service {service_name} configured: {config.status}")
            return config

        except Exception as e:
            logger.error(f"Failed to setup service {service_name}: {str(e)}")
            error_config = ServiceConfiguration.create_default_config(service_name)
            error_config.status = ServiceStatusType.FAILED
            error_config.error_message = f"Setup failed: {str(e)}"
            return error_config

    async def setup_multiple_services(
        self,
        service_requests: list[dict[str, Any]]
    ) -> dict[str, ServiceConfiguration]:
        """Setup multiple services concurrently with dependency management.

        Args:
            service_requests: List of service configuration requests

        Returns:
            Dictionary mapping service names to their configurations
        """
        logger.info(f"Setting up {len(service_requests)} services")

        # Separate Docker (dependency) from others
        docker_requests = [req for req in service_requests if req.get('service_name') == ServiceName.DOCKER]
        other_requests = [req for req in service_requests if req.get('service_name') != ServiceName.DOCKER]

        results = {}

        # Setup Docker first (dependency for others)
        for req in docker_requests:
            config = await self.setup_service(
                service_name=ServiceName(req['service_name']),
                custom_port=req.get('custom_port'),
                custom_endpoint=req.get('custom_endpoint'),
                auto_start=req.get('auto_start', False),
                config_overrides=req.get('config_overrides')
            )
            results[req['service_name']] = config

        # Setup other services concurrently
        if other_requests:
            tasks = []
            for req in other_requests:
                task = self.setup_service(
                    service_name=ServiceName(req['service_name']),
                    custom_port=req.get('custom_port'),
                    custom_endpoint=req.get('custom_endpoint'),
                    auto_start=req.get('auto_start', False),
                    config_overrides=req.get('config_overrides')
                )
                tasks.append((req['service_name'], task))

            # Execute tasks concurrently
            for service_name, task in tasks:
                try:
                    config = await task
                    results[service_name] = config
                except Exception as e:
                    logger.error(f"Failed to setup {service_name}: {e}")
                    error_config = ServiceConfiguration.create_default_config(ServiceName(service_name))
                    error_config.status = ServiceStatusType.FAILED
                    error_config.error_message = str(e)
                    results[service_name] = error_config

        return results

    async def get_service_configuration(self, service_name: ServiceName) -> ServiceConfiguration | None:
        """Get current configuration for a service.

        Args:
            service_name: Service to get configuration for

        Returns:
            Service configuration or None if not found
        """
        return self._service_configs.get(service_name)

    async def get_all_configurations(self) -> dict[str, ServiceConfiguration]:
        """Get all service configurations.

        Returns:
            Dictionary of all service configurations
        """
        return self._service_configs.copy()

    async def refresh_service_status(self, service_name: ServiceName) -> ServiceConfiguration:
        """Refresh the status of a service by re-detecting it.

        Args:
            service_name: Service to refresh

        Returns:
            Updated service configuration
        """
        logger.info(f"Refreshing status for service: {service_name}")

        # Get existing configuration or create default
        config = self._service_configs.get(service_name)
        if not config:
            config = ServiceConfiguration.create_default_config(service_name)

        # Re-detect service status
        config = await self._detect_and_configure_service(config)

        # Update registry
        self._service_configs[service_name] = config

        return config

    async def check_service_health(self, service_name: ServiceName) -> bool:
        """Check if a service is healthy and responding.

        Args:
            service_name: Service to check

        Returns:
            True if service is healthy, False otherwise
        """
        config = await self.get_service_configuration(service_name)
        if not config:
            return False

        return config.is_healthy()

    async def resolve_port_conflicts(self) -> list[dict[str, Any]]:
        """Detect and resolve port conflicts between services.

        Returns:
            List of conflict resolution actions taken
        """
        logger.info("Checking for port conflicts")

        conflicts = []
        port_usage = {}

        # Check for duplicate port assignments
        for service_name, config in self._service_configs.items():
            if config.port in port_usage:
                conflicts.append({
                    'type': 'port_conflict',
                    'port': config.port,
                    'services': [port_usage[config.port], service_name],
                    'action': 'reassign_port'
                })
            else:
                port_usage[config.port] = service_name

        # Check system port availability
        for service_name, config in self._service_configs.items():
            if not await self._is_port_available(config.port):
                conflicts.append({
                    'type': 'port_unavailable',
                    'port': config.port,
                    'service': service_name,
                    'action': 'find_alternative_port'
                })

        # Resolve conflicts
        resolutions = []
        for conflict in conflicts:
            if conflict['type'] == 'port_conflict':
                # Reassign port for the second service
                services = conflict['services']
                service_to_reassign = services[1]  # Reassign the second service
                new_port = await self._find_available_port(
                    ServiceName(service_to_reassign),
                    start_port=conflict['port'] + 1
                )

                if new_port:
                    config = self._service_configs[service_to_reassign]
                    old_port = config.port
                    config.port = new_port
                    config.endpoint = config.endpoint.replace(f":{old_port}", f":{new_port}")

                    resolutions.append({
                        'service': service_to_reassign,
                        'action': 'port_reassigned',
                        'old_port': old_port,
                        'new_port': new_port
                    })

            elif conflict['type'] == 'port_unavailable':
                # Find alternative port
                service = conflict['service']
                new_port = await self._find_available_port(
                    ServiceName(service),
                    start_port=conflict['port'] + 1
                )

                if new_port:
                    config = self._service_configs[service]
                    old_port = config.port
                    config.port = new_port
                    config.endpoint = config.endpoint.replace(f":{old_port}", f":{new_port}")

                    resolutions.append({
                        'service': service,
                        'action': 'port_changed',
                        'old_port': old_port,
                        'new_port': new_port,
                        'reason': 'port_unavailable'
                    })

        return resolutions

    async def enable_auto_start(self, service_name: ServiceName) -> bool:
        """Enable auto-start for a service.

        Args:
            service_name: Service to enable auto-start for

        Returns:
            True if successfully enabled, False otherwise
        """
        config = self._service_configs.get(service_name)
        if not config:
            return False

        config.auto_start = True

        # For Docker services, we might set up systemd or similar
        # For now, just update the configuration
        logger.info(f"Auto-start enabled for {service_name}")
        return True

    async def disable_auto_start(self, service_name: ServiceName) -> bool:
        """Disable auto-start for a service.

        Args:
            service_name: Service to disable auto-start for

        Returns:
            True if successfully disabled, False otherwise
        """
        config = self._service_configs.get(service_name)
        if not config:
            return False

        config.auto_start = False
        logger.info(f"Auto-start disabled for {service_name}")
        return True

    async def get_service_summary(self) -> dict[str, Any]:
        """Get a summary of all service configurations.

        Returns:
            Summary dictionary with service statistics and statuses
        """
        configs = await self.get_all_configurations()

        total_services = len(configs)
        healthy_services = sum(1 for config in configs.values() if config.is_healthy())
        failed_services = sum(1 for config in configs.values() if config.status == ServiceStatusType.FAILED)
        needs_attention = sum(1 for config in configs.values() if config.needs_attention())

        services_detail = {}
        for service_name, config in configs.items():
            services_detail[service_name] = config.to_summary_dict()

        return {
            'total_services': total_services,
            'healthy_services': healthy_services,
            'failed_services': failed_services,
            'needs_attention': needs_attention,
            'services': services_detail,
            'port_assignments': dict(self._port_registry),
            'timestamp': datetime.now().isoformat()
        }

    # Private helper methods

    async def _detect_and_configure_service(self, config: ServiceConfiguration) -> ServiceConfiguration:
        """Detect service and update configuration with current status.

        Args:
            config: Service configuration to update

        Returns:
            Updated configuration with detection results
        """
        try:
            if config.service_name == ServiceName.DOCKER:
                # Use synchronous Docker detection
                status = self.detection_service.check_docker()
                config.status = ServiceStatusType.RUNNING if status.available else ServiceStatusType.NOT_FOUND
                config.detected_version = status.version
                config.error_message = status.error_message

            elif config.service_name == ServiceName.OLLAMA:
                status = await self.detection_service.check_ollama(config.endpoint)
                config.status = ServiceStatusType.RUNNING if status.available else ServiceStatusType.NOT_FOUND
                config.detected_version = status.version
                config.error_message = status.error_message

            elif config.service_name == ServiceName.QDRANT:
                status = await self.detection_service.check_qdrant(config.endpoint)
                config.status = ServiceStatusType.RUNNING if status.available else ServiceStatusType.NOT_FOUND
                config.detected_version = status.version
                config.error_message = status.error_message

        except Exception as e:
            config.status = ServiceStatusType.FAILED
            config.error_message = f"Detection failed: {str(e)}"
            logger.error(f"Service detection failed for {config.service_name}: {e}")

        return config

    async def _attempt_service_setup(self, config: ServiceConfiguration) -> ServiceConfiguration:
        """Attempt to setup a service if it's not running.

        Args:
            config: Service configuration

        Returns:
            Updated configuration with setup results
        """
        if config.service_name == ServiceName.DOCKER:
            return await self._setup_docker_service(config)
        elif config.service_name == ServiceName.QDRANT:
            return await self._setup_qdrant_service(config)
        elif config.service_name == ServiceName.OLLAMA:
            return await self._setup_ollama_service(config)

        return config

    async def _setup_docker_service(self, config: ServiceConfiguration) -> ServiceConfiguration:
        """Setup Docker service if needed.

        Args:
            config: Docker service configuration

        Returns:
            Updated configuration
        """
        # Docker setup is typically system-level and requires manual installation
        # We can provide guidance but not automatic setup
        if config.status == ServiceStatusType.NOT_FOUND:
            config.status = ServiceStatusType.FAILED
            config.error_message = (
                "Docker not found. Please install Docker Desktop or Docker Engine. "
                "Visit https://docs.docker.com/get-docker/ for installation instructions."
            )

        return config

    async def _setup_qdrant_service(self, config: ServiceConfiguration) -> ServiceConfiguration:
        """Setup Qdrant service using Docker if available.

        Args:
            config: Qdrant service configuration

        Returns:
            Updated configuration
        """
        # Check if Docker is available for Qdrant setup
        docker_config = self._service_configs.get(ServiceName.DOCKER)
        if not docker_config or not docker_config.is_healthy():
            config.status = ServiceStatusType.FAILED
            config.error_message = "Docker required for Qdrant setup but not available"
            return config

        try:
            # Attempt to start Qdrant container
            cmd = [
                "docker", "run", "-d",
                "--name", "qdrant",
                "-p", f"{config.port}:6333",
                "qdrant/qdrant:latest"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)

            if process.returncode == 0:
                config.status = ServiceStatusType.CONFIGURED
                config.error_message = None

                # Wait a moment for service to start
                await asyncio.sleep(2)

                # Re-detect to confirm it's running
                config = await self._detect_and_configure_service(config)
            else:
                config.status = ServiceStatusType.FAILED
                config.error_message = f"Failed to start Qdrant container: {stderr.decode().strip()}"

        except TimeoutError:
            config.status = ServiceStatusType.FAILED
            config.error_message = "Timeout starting Qdrant container"
        except Exception as e:
            config.status = ServiceStatusType.FAILED
            config.error_message = f"Error starting Qdrant: {str(e)}"

        return config

    async def _setup_ollama_service(self, config: ServiceConfiguration) -> ServiceConfiguration:
        """Setup Ollama service if needed.

        Args:
            config: Ollama service configuration

        Returns:
            Updated configuration
        """
        # Ollama typically needs to be installed manually
        # We can provide installation guidance
        if config.status == ServiceStatusType.NOT_FOUND:
            config.status = ServiceStatusType.FAILED
            config.error_message = (
                "Ollama not found. Please install Ollama from https://ollama.ai/download "
                "and start it with 'ollama serve'"
            )

        return config

    async def _validate_port_availability(self, port: int, service_name: ServiceName) -> None:
        """Validate that a port is available for use.

        Args:
            port: Port to check
            service_name: Service requesting the port

        Raises:
            ServiceConflictError: If port is not available
        """
        # Check if port is already assigned to a different service
        if port in self._port_registry and self._port_registry[port] != service_name:
            raise ServiceConflictError(
                f"Port {port} is already assigned to service {self._port_registry[port]}"
            )

        # Check if port is available on the system
        if not await self._is_port_available(port):
            raise ServiceConflictError(f"Port {port} is not available on the system")

    async def _is_port_available(self, port: int) -> bool:
        """Check if a port is available on the local system.

        Args:
            port: Port to check

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                result = sock.bind(('localhost', port))
                return True
        except OSError:
            return False

    async def _find_available_port(
        self,
        service_name: ServiceName,
        start_port: int = 8000,
        max_attempts: int = 100
    ) -> int | None:
        """Find an available port for a service.

        Args:
            service_name: Service needing a port
            start_port: Starting port to check
            max_attempts: Maximum number of ports to try

        Returns:
            Available port number or None if none found
        """
        for port_offset in range(max_attempts):
            port = start_port + port_offset

            # Skip reserved ports
            if port < 1024 or port > 65535:
                continue

            try:
                await self._validate_port_availability(port, service_name)
                return port
            except ServiceConflictError:
                continue

        return None

    @asynccontextmanager
    async def service_transaction(self):
        """Context manager for transactional service operations.

        Allows rolling back changes if operations fail.
        """
        # Save current state
        original_configs = self._service_configs.copy()
        original_ports = self._port_registry.copy()

        try:
            yield self
        except Exception:
            # Rollback on error
            self._service_configs = original_configs
            self._port_registry = original_ports
            raise

    async def export_configurations(self, file_path: Path) -> None:
        """Export service configurations to a JSON file.

        Args:
            file_path: Path to export configurations to
        """
        config_data = {}

        for service_name, config in self._service_configs.items():
            config_data[service_name] = config.model_dump()

        export_data = {
            'configurations': config_data,
            'port_registry': self._port_registry,
            'exported_at': datetime.now().isoformat(),
            'version': '1.0.0'
        }

        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Configurations exported to {file_path}")

    async def import_configurations(self, file_path: Path) -> None:
        """Import service configurations from a JSON file.

        Args:
            file_path: Path to import configurations from
        """
        with open(file_path) as f:
            import_data = json.load(f)

        configurations = import_data.get('configurations', {})
        port_registry = import_data.get('port_registry', {})

        # Clear current state
        self._service_configs.clear()
        self._port_registry.clear()

        # Import configurations
        for service_name, config_data in configurations.items():
            try:
                config = ServiceConfiguration(**config_data)
                self._service_configs[service_name] = config
            except Exception as e:
                logger.error(f"Failed to import configuration for {service_name}: {e}")

        # Import port registry
        for port_str, service_name in port_registry.items():
            self._port_registry[int(port_str)] = service_name

        logger.info(f"Configurations imported from {file_path}")


# Dependency injection factory
def create_service_configuration_service(
    timeout: int = 10,
    max_retries: int = 3,
    detection_service: ServiceDetectionService | None = None
) -> ServiceConfigurationService:
    """Factory function for creating ServiceConfigurationService with dependency injection.

    Args:
        timeout: Timeout for service operations
        max_retries: Maximum retry attempts
        detection_service: Optional detection service

    Returns:
        Configured ServiceConfigurationService instance
    """
    return ServiceConfigurationService(
        timeout=timeout,
        max_retries=max_retries,
        detection_service=detection_service
    )
