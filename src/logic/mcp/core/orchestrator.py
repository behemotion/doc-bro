"""Server orchestrator for dual server management."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from src.logic.mcp.models.config import McpServerConfig
from src.logic.mcp.models.server_type import McpServerType
from src.logic.mcp.utils.port_manager import PortManager

logger = logging.getLogger(__name__)


class ServerOrchestrator:
    """Orchestrates multiple MCP servers."""

    def __init__(self, port_manager: PortManager):
        """Initialize orchestrator."""
        self.port_manager = port_manager
        self.running_servers: Dict[McpServerType, Any] = {}
        self.server_tasks: Dict[McpServerType, asyncio.Task] = {}

    async def start_servers(self, configs: List[McpServerConfig]) -> bool:
        """Start multiple servers based on configurations."""
        try:
            # Validate configurations
            is_valid, errors = self.port_manager.validate_server_configs(configs)
            if not is_valid:
                logger.error(f"Server configuration validation failed: {errors}")
                return False

            # Start each enabled server
            for config in configs:
                if config.enabled:
                    success = await self.start_single_server(config)
                    if not success:
                        logger.error(f"Failed to start {config.server_type.value} server")
                        await self.stop_all_servers()
                        return False

            return True

        except Exception as e:
            logger.error(f"Error starting servers: {e}")
            await self.stop_all_servers()
            return False

    async def start_single_server(self, config: McpServerConfig) -> bool:
        """Start a single server."""
        try:
            if config.server_type == McpServerType.READ_ONLY:
                from src.logic.mcp.core.read_only_server import app
                server_app = app
            elif config.server_type == McpServerType.ADMIN:
                from src.logic.mcp.core.admin_server import app
                server_app = app
            else:
                logger.error(f"Unknown server type: {config.server_type}")
                return False

            # Start server in background task
            task = asyncio.create_task(
                self._run_server(server_app, config)
            )

            self.server_tasks[config.server_type] = task
            logger.info(f"Started {config.server_type.value} server on {config.url}")

            return True

        except Exception as e:
            logger.error(f"Error starting {config.server_type.value} server: {e}")
            return False

    async def _run_server(self, app: Any, config: McpServerConfig):
        """Run a server with uvicorn."""
        import uvicorn

        uvicorn_config = uvicorn.Config(
            app=app,
            host=config.host,
            port=config.port,
            log_level="info"
        )

        server = uvicorn.Server(uvicorn_config)
        await server.serve()

    async def stop_all_servers(self):
        """Stop all running servers."""
        for server_type, task in self.server_tasks.items():
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping {server_type.value} server: {e}")

        self.server_tasks.clear()
        self.running_servers.clear()

    def get_server_status(self) -> Dict[str, Any]:
        """Get status of all servers."""
        status = {}

        for server_type in [McpServerType.READ_ONLY, McpServerType.ADMIN]:
            is_running = server_type in self.server_tasks
            status[server_type.value] = {
                "running": is_running,
                "port": server_type.default_port,
                "host": server_type.default_host
            }

        return status

    @asynccontextmanager
    async def server_context(self, configs: List[McpServerConfig]):
        """Context manager for server lifecycle."""
        try:
            success = await self.start_servers(configs)
            if not success:
                raise RuntimeError("Failed to start servers")
            yield self
        finally:
            await self.stop_all_servers()