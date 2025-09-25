"""MCP client detection service for DocBro setup logic.

This service handles detection of MCP clients like Claude Code across different platforms.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import platform

from ..models.setup_types import ComponentType, HealthStatus
from ..models.component_availability import ComponentAvailability


logger = logging.getLogger(__name__)


class MCPDetector:
    """Detects and manages MCP client integrations."""

    def __init__(self):
        """Initialize MCP detector."""
        self.platform = platform.system().lower()

    async def detect_all_mcp_clients(self) -> List[ComponentAvailability]:
        """Detect all available MCP clients."""
        clients = []

        # Detect Claude Code
        claude_code = await self.detect_claude_code()
        clients.append(claude_code)

        return clients

    async def detect_claude_code(self) -> ComponentAvailability:
        """Detect Claude Code installation."""
        try:
            if self.platform == "darwin":  # macOS
                return await self._detect_claude_code_macos()
            elif self.platform == "linux":
                return await self._detect_claude_code_linux()
            elif self.platform == "windows":
                return await self._detect_claude_code_windows()
            else:
                return ComponentAvailability.create_unavailable(
                    ComponentType.MCP_CLIENT,
                    "claude-code",
                    f"Unsupported platform: {self.platform}"
                )

        except Exception as e:
            logger.error(f"Error detecting Claude Code: {e}")
            return ComponentAvailability.create_unavailable(
                ComponentType.MCP_CLIENT,
                "claude-code",
                f"Detection failed: {e}"
            )

    async def _detect_claude_code_macos(self) -> ComponentAvailability:
        """Detect Claude Code on macOS."""
        app_path = Path("/Applications/Claude Code.app")
        config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"

        if not app_path.exists():
            return ComponentAvailability.create_unavailable(
                ComponentType.MCP_CLIENT,
                "claude-code",
                "Claude Code not found in /Applications"
            )

        # Try to get version from Info.plist
        version = self._get_macos_app_version(app_path)

        return ComponentAvailability.create_available(
            ComponentType.MCP_CLIENT,
            "claude-code",
            version=version,
            installation_path=app_path,
            configuration_path=config_path if config_path.exists() else None,
            capabilities={
                "platform": "macos",
                "config_format": "json",
                "supports_server_config": True
            }
        )

    async def _detect_claude_code_linux(self) -> ComponentAvailability:
        """Detect Claude Code on Linux."""
        # Common Linux installation paths
        possible_paths = [
            Path.home() / ".local/bin/claude-code",
            Path("/usr/local/bin/claude-code"),
            Path("/usr/bin/claude-code"),
            Path.home() / "Applications/Claude Code"
        ]

        config_path = Path.home() / ".config/Claude/claude_desktop_config.json"

        for path in possible_paths:
            if path.exists():
                return ComponentAvailability.create_available(
                    ComponentType.MCP_CLIENT,
                    "claude-code",
                    installation_path=path,
                    configuration_path=config_path if config_path.exists() else None,
                    capabilities={
                        "platform": "linux",
                        "config_format": "json",
                        "supports_server_config": True
                    }
                )

        return ComponentAvailability.create_unavailable(
            ComponentType.MCP_CLIENT,
            "claude-code",
            "Claude Code not found in common Linux installation paths"
        )

    async def _detect_claude_code_windows(self) -> ComponentAvailability:
        """Detect Claude Code on Windows."""
        # Common Windows installation paths
        possible_paths = [
            Path.home() / "AppData/Local/Programs/Claude Code/Claude Code.exe",
            Path("C:/Program Files/Claude Code/Claude Code.exe"),
            Path("C:/Program Files (x86)/Claude Code/Claude Code.exe")
        ]

        config_path = Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"

        for path in possible_paths:
            if path.exists():
                return ComponentAvailability.create_available(
                    ComponentType.MCP_CLIENT,
                    "claude-code",
                    installation_path=path,
                    configuration_path=config_path if config_path.exists() else None,
                    capabilities={
                        "platform": "windows",
                        "config_format": "json",
                        "supports_server_config": True
                    }
                )

        return ComponentAvailability.create_unavailable(
            ComponentType.MCP_CLIENT,
            "claude-code",
            "Claude Code not found in common Windows installation paths"
        )

    def _get_macos_app_version(self, app_path: Path) -> Optional[str]:
        """Get version from macOS app Info.plist."""
        try:
            import plistlib
            info_plist = app_path / "Contents/Info.plist"
            if info_plist.exists():
                with open(info_plist, 'rb') as f:
                    plist = plistlib.load(f)
                    return plist.get('CFBundleShortVersionString', 'unknown')
        except Exception as e:
            logger.debug(f"Could not read version from {app_path}: {e}")

        return None

    async def configure_mcp_client(
        self,
        client_availability: ComponentAvailability,
        server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure MCP client with DocBro server."""
        if not client_availability.available:
            raise ValueError(f"Cannot configure unavailable client: {client_availability.component_name}")

        config_path = client_availability.configuration_path
        if not config_path:
            raise ValueError(f"No configuration path found for {client_availability.component_name}")

        try:
            # Load existing configuration
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"mcpServers": {}}

            # Ensure mcpServers exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Add DocBro server configuration
            config["mcpServers"]["docbro"] = {
                "command": server_config.get("command", "docbro"),
                "args": server_config.get("args", ["serve", "--port", "9382"]),
                "env": server_config.get("env", {})
            }

            # Create directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write configuration
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Updated MCP configuration: {config_path}")

            return {
                "status": "success",
                "config_path": str(config_path),
                "client_name": client_availability.component_name,
                "server_added": "docbro"
            }

        except Exception as e:
            logger.error(f"Failed to configure MCP client: {e}")
            raise ValueError(f"Configuration failed: {e}")

    async def check_mcp_health(self) -> Dict[str, Any]:
        """Check overall MCP client ecosystem health."""
        clients = await self.detect_all_mcp_clients()

        available_clients = [c for c in clients if c.available]
        configured_clients = [c for c in available_clients if c.configuration_path and c.configuration_path.exists()]

        return {
            "total_clients_detected": len(clients),
            "available_clients": len(available_clients),
            "configured_clients": len(configured_clients),
            "clients": [c.get_status_details() for c in clients]
        }