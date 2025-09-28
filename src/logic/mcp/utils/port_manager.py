"""Port manager for port allocation and conflict detection."""

import socket
import logging
from typing import List, Set, Optional, Tuple
from contextlib import closing

from src.logic.mcp.models.config import McpServerConfig
from src.logic.mcp.models.server_type import McpServerType

logger = logging.getLogger(__name__)


class PortManager:
    """Manager for port allocation and conflict detection."""

    def __init__(self):
        """Initialize port manager."""
        self._allocated_ports: Set[int] = set()

    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is available on the given host."""
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                # Set socket option to reuse address
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                # Try to bind to the port
                result = sock.connect_ex((host, port))

                # If connection succeeds, port is in use
                return result != 0

        except Exception as e:
            logger.error(f"Error checking port {port} on {host}: {e}")
            return False

    def find_available_port(
        self,
        preferred_port: int,
        host: str = "localhost",
        port_range: Tuple[int, int] = (1024, 65535)
    ) -> Optional[int]:
        """Find an available port, starting with the preferred port."""
        # First try the preferred port
        if self.is_port_available(preferred_port, host):
            return preferred_port

        # Search for available port in range
        start_range, end_range = port_range

        # Search near the preferred port first
        search_radius = 100
        search_start = max(start_range, preferred_port - search_radius)
        search_end = min(end_range, preferred_port + search_radius)

        for port in range(search_start, search_end + 1):
            if port != preferred_port and self.is_port_available(port, host):
                return port

        # If not found in nearby range, search the full range
        for port in range(start_range, end_range + 1):
            if port not in range(search_start, search_end + 1):
                if self.is_port_available(port, host):
                    return port

        return None

    def allocate_port(self, port: int) -> bool:
        """Allocate a port for use."""
        if port in self._allocated_ports:
            return False

        self._allocated_ports.add(port)
        return True

    def release_port(self, port: int) -> bool:
        """Release an allocated port."""
        if port in self._allocated_ports:
            self._allocated_ports.remove(port)
            return True
        return False

    def check_port_conflicts(self, configs: List[McpServerConfig]) -> List[str]:
        """Check for port conflicts between server configurations."""
        conflicts = []
        port_usage = {}

        for config in configs:
            if not config.enabled:
                continue

            port = config.port
            if port in port_usage:
                existing_config = port_usage[port]
                conflicts.append(
                    f"Port {port} conflict: {config.server_type.value} server "
                    f"conflicts with {existing_config.server_type.value} server"
                )
            else:
                port_usage[port] = config

        return conflicts

    def validate_server_configs(self, configs: List[McpServerConfig]) -> Tuple[bool, List[str]]:
        """Validate server configurations for port availability and conflicts."""
        errors = []

        # Check for internal conflicts
        conflicts = self.check_port_conflicts(configs)
        errors.extend(conflicts)

        # Check port availability
        for config in configs:
            if not config.enabled:
                continue

            if not self.is_port_available(config.port, config.host):
                errors.append(
                    f"Port {config.port} is not available on {config.host} "
                    f"for {config.server_type.value} server"
                )

        return len(errors) == 0, errors

    def suggest_port_fixes(
        self,
        configs: List[McpServerConfig]
    ) -> List[Tuple[McpServerConfig, int]]:
        """Suggest alternative ports for conflicting configurations."""
        suggestions = []

        # Find configs with port issues
        _, errors = self.validate_server_configs(configs)

        for config in configs:
            if not config.enabled:
                continue

            # Check if this config has issues
            needs_fix = any(
                str(config.port) in error and config.server_type.value in error
                for error in errors
            )

            if needs_fix:
                # Find alternative port
                alternative_port = self.find_available_port(
                    config.port,
                    config.host
                )

                if alternative_port:
                    suggestions.append((config, alternative_port))

        return suggestions

    def get_default_configs(self) -> List[McpServerConfig]:
        """Get default configurations for both server types."""
        configs = []

        for server_type in [McpServerType.READ_ONLY, McpServerType.ADMIN]:
            config = McpServerConfig(
                server_type=server_type,
                host=server_type.default_host,
                port=server_type.default_port,
                enabled=True
            )
            configs.append(config)

        return configs

    def get_port_status_report(self) -> dict:
        """Get a report of port usage and availability."""
        report = {
            "allocated_ports": list(self._allocated_ports),
            "default_ports": {
                "read_only": McpServerType.READ_ONLY.default_port,
                "admin": McpServerType.ADMIN.default_port
            },
            "port_availability": {}
        }

        # Check availability of default ports
        for server_type in [McpServerType.READ_ONLY, McpServerType.ADMIN]:
            port = server_type.default_port
            host = server_type.default_host

            report["port_availability"][f"{server_type.value}_{port}"] = {
                "port": port,
                "host": host,
                "available": self.is_port_available(port, host)
            }

        return report