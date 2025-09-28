"""MCP configuration loading and validation utilities."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.logic.mcp.models.config import McpServerConfig
from src.logic.mcp.models.server_type import McpServerType
from src.models.settings import GlobalSettings

logger = logging.getLogger(__name__)


class McpConfigLoader:
    """Loads and validates MCP server configurations."""

    def __init__(self, settings: GlobalSettings):
        """Initialize config loader.

        Args:
            settings: Global settings instance containing MCP configuration
        """
        self.settings = settings

    def load_all_server_configs(self) -> List[McpServerConfig]:
        """Load all MCP server configurations from settings.

        Returns:
            List of validated McpServerConfig instances
        """
        configs = []

        # Load from structured configuration first
        if hasattr(self.settings, 'mcp_server_configs') and self.settings.mcp_server_configs:
            for server_name, config_data in self.settings.mcp_server_configs.items():
                try:
                    config = self._create_config_from_dict(config_data)
                    configs.append(config)
                    logger.debug(f"Loaded MCP config for {server_name}: {config.url}")
                except Exception as e:
                    logger.error(f"Failed to load MCP config for {server_name}: {e}")
        else:
            # Fallback to individual configuration fields for backward compatibility
            configs = self._load_from_individual_fields()

        # Validate all configurations
        validated_configs = []
        for config in configs:
            if self._validate_config(config):
                validated_configs.append(config)
            else:
                logger.warning(f"Skipping invalid MCP config: {config.server_type.value}")

        return validated_configs

    def load_enabled_server_configs(self) -> List[McpServerConfig]:
        """Load only enabled MCP server configurations.

        Returns:
            List of enabled McpServerConfig instances
        """
        all_configs = self.load_all_server_configs()
        return [config for config in all_configs if config.enabled]

    def load_server_config(self, server_type: McpServerType) -> Optional[McpServerConfig]:
        """Load configuration for a specific server type.

        Args:
            server_type: Type of server to load configuration for

        Returns:
            McpServerConfig instance or None if not found/invalid
        """
        all_configs = self.load_all_server_configs()
        for config in all_configs:
            if config.server_type == server_type:
                return config
        return None

    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> McpServerConfig:
        """Create McpServerConfig from dictionary data.

        Args:
            config_data: Configuration dictionary

        Returns:
            Validated McpServerConfig instance
        """
        # Map string server type to enum
        server_type_str = config_data.get("server_type")
        if server_type_str == "read-only":
            server_type = McpServerType.READ_ONLY
        elif server_type_str == "admin":
            server_type = McpServerType.ADMIN
        else:
            raise ValueError(f"Unknown server type: {server_type_str}")

        # Create configuration with validation
        return McpServerConfig(
            server_type=server_type,
            host=config_data.get("host", ""),
            port=config_data.get("port", 0),
            enabled=config_data.get("enabled", True)
        )

    def _load_from_individual_fields(self) -> List[McpServerConfig]:
        """Load configurations from individual settings fields (backward compatibility).

        Returns:
            List of McpServerConfig instances
        """
        configs = []

        # Load read-only server config
        try:
            read_only_config = McpServerConfig(
                server_type=McpServerType.READ_ONLY,
                host=getattr(self.settings, 'mcp_read_only_host', '0.0.0.0'),
                port=getattr(self.settings, 'mcp_read_only_port', 9383),
                enabled=getattr(self.settings, 'mcp_read_only_enabled', True)
            )
            configs.append(read_only_config)
            logger.debug("Loaded read-only MCP config from individual fields")
        except Exception as e:
            logger.error(f"Failed to load read-only MCP config from individual fields: {e}")

        # Load admin server config
        try:
            admin_config = McpServerConfig(
                server_type=McpServerType.ADMIN,
                host=getattr(self.settings, 'mcp_admin_host', '127.0.0.1'),
                port=getattr(self.settings, 'mcp_admin_port', 9384),
                enabled=getattr(self.settings, 'mcp_admin_enabled', True)
            )
            configs.append(admin_config)
            logger.debug("Loaded admin MCP config from individual fields")
        except Exception as e:
            logger.error(f"Failed to load admin MCP config from individual fields: {e}")

        return configs

    def _validate_config(self, config: McpServerConfig) -> bool:
        """Validate an MCP server configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid
        """
        try:
            # Port range validation
            if not (1024 <= config.port <= 65535):
                logger.error(f"Invalid port for {config.server_type.value} server: {config.port}")
                return False

            # Admin server security validation
            if config.server_type == McpServerType.ADMIN:
                if config.host not in ["127.0.0.1", "localhost"]:
                    logger.error(f"Admin server must be bound to localhost, got: {config.host}")
                    return False

            # Host format validation
            if not config.host or not isinstance(config.host, str):
                logger.error(f"Invalid host for {config.server_type.value} server: {config.host}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating {config.server_type.value} server config: {e}")
            return False

    def validate_port_conflicts(self) -> bool:
        """Check for port conflicts between enabled servers.

        Returns:
            True if no port conflicts exist
        """
        enabled_configs = self.load_enabled_server_configs()
        ports = [config.port for config in enabled_configs]

        # Check for duplicates
        if len(ports) != len(set(ports)):
            conflicting_ports = [port for port in set(ports) if ports.count(port) > 1]
            logger.error(f"Port conflicts detected: {conflicting_ports}")
            return False

        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current MCP configuration.

        Returns:
            Configuration summary dictionary
        """
        all_configs = self.load_all_server_configs()
        enabled_configs = [config for config in all_configs if config.enabled]

        return {
            "total_servers": len(all_configs),
            "enabled_servers": len(enabled_configs),
            "server_types": [config.server_type.value for config in all_configs],
            "enabled_types": [config.server_type.value for config in enabled_configs],
            "ports_in_use": [config.port for config in enabled_configs],
            "port_conflicts": not self.validate_port_conflicts(),
            "servers": [
                {
                    "type": config.server_type.value,
                    "host": config.host,
                    "port": config.port,
                    "enabled": config.enabled,
                    "url": config.url,
                    "localhost_only": config.is_localhost_only()
                }
                for config in all_configs
            ]
        }

    def export_config_to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Export current configuration as dictionary for persistence.

        Returns:
            Configuration dictionary suitable for settings storage
        """
        all_configs = self.load_all_server_configs()
        config_dict = {}

        for config in all_configs:
            server_name = config.server_type.value
            config_dict[server_name] = {
                "server_type": config.server_type.value,
                "host": config.host,
                "port": config.port,
                "enabled": config.enabled
            }

        return config_dict

    def update_server_config(
        self,
        server_type: McpServerType,
        host: Optional[str] = None,
        port: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """Update configuration for a specific server type.

        Args:
            server_type: Type of server to update
            host: New host (optional)
            port: New port (optional)
            enabled: New enabled status (optional)

        Returns:
            True if update was successful
        """
        try:
            # Load current config
            current_config = self.load_server_config(server_type)
            if not current_config:
                logger.error(f"No existing configuration found for {server_type.value}")
                return False

            # Create updated config
            updated_config = McpServerConfig(
                server_type=server_type,
                host=host if host is not None else current_config.host,
                port=port if port is not None else current_config.port,
                enabled=enabled if enabled is not None else current_config.enabled
            )

            # Validate updated config
            if not self._validate_config(updated_config):
                logger.error(f"Updated configuration for {server_type.value} is invalid")
                return False

            # Update in settings
            server_name = server_type.value
            if hasattr(self.settings, 'mcp_server_configs'):
                self.settings.mcp_server_configs[server_name] = {
                    "server_type": updated_config.server_type.value,
                    "host": updated_config.host,
                    "port": updated_config.port,
                    "enabled": updated_config.enabled
                }
                logger.info(f"Updated MCP configuration for {server_type.value}")
                return True
            else:
                logger.error("Settings does not support structured MCP configuration")
                return False

        except Exception as e:
            logger.error(f"Failed to update configuration for {server_type.value}: {e}")
            return False