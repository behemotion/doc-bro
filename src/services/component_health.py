"""Component health checker service for DocBro setup logic.

This service provides health checking capabilities for all external components.
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from ..models.setup_types import ComponentType, HealthStatus
from ..models.component_availability import ComponentAvailability
from .docker_manager import DockerManager
from .ollama_manager import OllamaManager
from .mcp_detector import MCPDetector


logger = logging.getLogger(__name__)


class ComponentHealthChecker:
    """Checks health of all external components."""

    def __init__(self):
        """Initialize health checker."""
        self.docker_manager = DockerManager()
        self.ollama_manager = OllamaManager()
        self.mcp_detector = MCPDetector()

    async def check_all_components(self) -> List[ComponentAvailability]:
        """Check health of all components."""
        logger.info("Checking health of all components")

        # Run health checks concurrently
        docker_task = asyncio.create_task(self._check_docker_health())
        ollama_task = asyncio.create_task(self._check_ollama_health())
        mcp_task = asyncio.create_task(self._check_mcp_health())

        results = await asyncio.gather(docker_task, ollama_task, mcp_task, return_exceptions=True)

        components = []
        for result in results:
            if isinstance(result, ComponentAvailability):
                components.append(result)
            elif isinstance(result, list):
                components.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Component health check failed: {result}")

        return components

    async def _check_docker_health(self) -> ComponentAvailability:
        """Check Docker health."""
        try:
            health = await self.docker_manager.check_docker_health()

            if health["available"]:
                return ComponentAvailability.create_available(
                    ComponentType.DOCKER,
                    "docker",
                    version=health.get("version"),
                    capabilities={
                        "api_version": health.get("api_version"),
                        "platform": health.get("platform"),
                        "architecture": health.get("architecture")
                    }
                )
            else:
                return ComponentAvailability.create_unavailable(
                    ComponentType.DOCKER,
                    "docker",
                    health.get("error", "Docker not available")
                )

        except Exception as e:
            return ComponentAvailability.create_unavailable(
                ComponentType.DOCKER,
                "docker",
                f"Health check failed: {e}"
            )

    async def _check_ollama_health(self) -> ComponentAvailability:
        """Check Ollama health."""
        try:
            health = await self.ollama_manager.check_ollama_health()

            if health["available"]:
                return ComponentAvailability.create_available(
                    ComponentType.OLLAMA,
                    "ollama",
                    version=health.get("version"),
                    capabilities={
                        "models_count": health.get("models_count", 0),
                        "available_models": health.get("available_models", [])
                    }
                )
            else:
                return ComponentAvailability.create_unavailable(
                    ComponentType.OLLAMA,
                    "ollama",
                    health.get("error", "Ollama not available")
                )

        except Exception as e:
            return ComponentAvailability.create_unavailable(
                ComponentType.OLLAMA,
                "ollama",
                f"Health check failed: {e}"
            )

    async def _check_mcp_health(self) -> List[ComponentAvailability]:
        """Check MCP clients health."""
        try:
            return await self.mcp_detector.detect_all_mcp_clients()
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return [ComponentAvailability.create_unavailable(
                ComponentType.MCP_CLIENT,
                "claude-code",
                f"Health check failed: {e}"
            )]

    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        components = await self.check_all_components()

        summary = {
            "total_components": len(components),
            "healthy_components": len([c for c in components if c.is_healthy()]),
            "available_components": len([c for c in components if c.available]),
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "components": {c.component_name: c.get_status_details() for c in components}
        }

        return summary

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.docker_manager.disconnect()
        await self.ollama_manager.disconnect()