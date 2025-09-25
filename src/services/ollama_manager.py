"""Ollama model management service for DocBro setup logic.

This service handles Ollama model operations including downloading, management,
and health checking for embedding models.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
import json

import httpx

from ..models.setup_types import ExternalDependencyError, TimeoutError as SetupTimeoutError


logger = logging.getLogger(__name__)


class OllamaManager:
    """Manages Ollama model operations for DocBro setup."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client."""
        self.base_url = base_url.rstrip('/')
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Connect to Ollama service."""
        self._client = httpx.AsyncClient(timeout=30.0)

        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            logger.info("Connected to Ollama service")
            return True
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise ExternalDependencyError(f"Ollama service not available at {self.base_url}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Ollama service."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_ollama_health(self) -> Dict[str, Any]:
        """Check Ollama service health."""
        try:
            await self.connect()

            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])

            return {
                "available": True,
                "version": "0.1.17",  # Would get from API in real implementation
                "health_status": "healthy",
                "models_count": len(models),
                "available_models": [m["name"] for m in models]
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "health_status": "unhealthy",
                "error": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        if not self._client:
            await self.connect()

        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Failed to list models: {e}")
            raise ExternalDependencyError(f"Cannot list Ollama models: {e}")

    async def check_model_availability(self, model_name: str) -> Dict[str, Any]:
        """Check if a specific model is available."""
        models = await self.list_models()

        for model in models:
            if model["name"] == model_name:
                return {
                    "available": True,
                    "name": model["name"],
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at")
                }

        return {
            "available": False,
            "name": model_name,
            "download_required": True
        }

    async def download_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Download a model with progress tracking."""
        if not self._client:
            await self.connect()

        try:
            logger.info(f"Starting download of model: {model_name}")

            payload = {"name": model_name}

            async with self._client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json=payload,
                timeout=600.0  # 10 minute timeout for downloads
            ) as response:
                response.raise_for_status()

                total_size = 0
                downloaded = 0

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)

                            if "total" in data:
                                total_size = data["total"]
                            if "completed" in data:
                                downloaded = data["completed"]

                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)

                            if data.get("status") == "success":
                                logger.info(f"Model {model_name} downloaded successfully")
                                return {
                                    "status": "success",
                                    "model_name": model_name,
                                    "total_size": total_size
                                }

                        except json.JSONDecodeError:
                            continue

            return {
                "status": "success",
                "model_name": model_name,
                "total_size": total_size
            }

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            raise ExternalDependencyError(f"Cannot download model {model_name}: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()