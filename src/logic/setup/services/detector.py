"""Service detection service."""

import asyncio
import subprocess
import shutil
from typing import Dict, Any, Optional
import httpx
from src.logic.setup.models.service_info import ServiceInfo, ServiceStatus
from src.lib.logging import get_logger

logger = get_logger(__name__)


class ServiceDetector:
    """Service for detecting available external services."""

    def __init__(self):
        """Initialize the service detector."""
        self.timeout = 5.0  # Timeout for service checks

    async def detect_all_async(self) -> Dict[str, Dict[str, Any]]:
        """Detect all services asynchronously for performance.

        Returns:
            Dictionary of service detection results
        """
        tasks = [
            self.check_docker(),
            self.check_qdrant(),
            self.check_ollama(),
            self.check_sqlite_vec(),
            self.check_python(),
            self.check_uv(),
            self.check_git()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        services = {}
        service_names = ["docker", "qdrant", "ollama", "sqlite_vec", "python", "uv", "git"]

        for name, result in zip(service_names, results):
            if isinstance(result, Exception):
                services[name] = {
                    "status": "unavailable",
                    "error": str(result)
                }
            else:
                services[name] = result

        return services

    def detect_all(self) -> Dict[str, Dict[str, Any]]:
        """Synchronous wrapper for detect_all_async.

        Returns:
            Dictionary of service detection results
        """
        return asyncio.run(self.detect_all_async())

    async def check_docker(self) -> Dict[str, Any]:
        """Check if Docker is available.

        Returns:
            Docker status information
        """
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "version", "--format", "{{.Server.Version}}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                version = stdout.decode().strip()
                return {
                    "status": "available",
                    "version": version
                }
            else:
                return {
                    "status": "unavailable",
                    "error": "Docker not running"
                }
        except FileNotFoundError:
            return {
                "status": "unavailable",
                "error": "Docker not installed"
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": str(e)
            }

    async def check_qdrant(self) -> Dict[str, Any]:
        """Check if Qdrant is available.

        Returns:
            Qdrant status information
        """
        url = "http://localhost:6333/health"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "available",
                        "version": data.get("version", "unknown"),
                        "url": "http://localhost:6333"
                    }
                else:
                    return {
                        "status": "unavailable",
                        "error": f"Health check failed: {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": f"Cannot connect to Qdrant: {e}"
            }

    async def check_ollama(self) -> Dict[str, Any]:
        """Check if Ollama is available.

        Returns:
            Ollama status information
        """
        url = "http://localhost:11434/api/version"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "available",
                        "version": data.get("version", "unknown"),
                        "url": "http://localhost:11434"
                    }
                else:
                    return {
                        "status": "unavailable",
                        "error": f"Version check failed: {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": f"Cannot connect to Ollama: {e}"
            }

    async def check_sqlite_vec(self) -> Dict[str, Any]:
        """Check if sqlite-vec is available.

        Returns:
            SQLite-vec status information
        """
        try:
            # Check if sqlite-vec Python package is installed
            import sqlite_vec

            return {
                "status": "available",
                "version": getattr(sqlite_vec, "__version__", "unknown")
            }
        except ImportError:
            return {
                "status": "unavailable",
                "error": "sqlite-vec not installed"
            }

    async def check_python(self) -> Dict[str, Any]:
        """Check Python version.

        Returns:
            Python status information
        """
        import sys

        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        return {
            "status": "available",
            "version": version,
            "path": sys.executable
        }

    async def check_uv(self) -> Dict[str, Any]:
        """Check if UV is installed.

        Returns:
            UV status information
        """
        try:
            result = await asyncio.create_subprocess_exec(
                "uv", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                version_line = stdout.decode().strip()
                # Parse version from output like "uv 0.8.0"
                version = version_line.split()[-1] if version_line else "unknown"
                return {
                    "status": "available",
                    "version": version,
                    "path": shutil.which("uv")
                }
            else:
                return {
                    "status": "unavailable",
                    "error": "UV command failed"
                }
        except FileNotFoundError:
            return {
                "status": "unavailable",
                "error": "UV not installed"
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": str(e)
            }

    async def check_git(self) -> Dict[str, Any]:
        """Check if Git is installed.

        Returns:
            Git status information
        """
        try:
            result = await asyncio.create_subprocess_exec(
                "git", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                version_line = stdout.decode().strip()
                # Parse version from output like "git version 2.40.0"
                parts = version_line.split()
                version = parts[2] if len(parts) > 2 else "unknown"
                return {
                    "status": "available",
                    "version": version,
                    "path": shutil.which("git")
                }
            else:
                return {
                    "status": "unavailable",
                    "error": "Git command failed"
                }
        except FileNotFoundError:
            return {
                "status": "unavailable",
                "error": "Git not installed"
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": str(e)
            }

    def create_service_info(self, name: str, result: Dict[str, Any]) -> ServiceInfo:
        """Convert detection result to ServiceInfo model.

        Args:
            name: Service name
            result: Detection result

        Returns:
            ServiceInfo instance
        """
        info = ServiceInfo(name=name)

        if result.get("status") == "available":
            info.mark_available(version=result.get("version"))
            info.url = result.get("url")
        else:
            info.mark_unavailable(error=result.get("error"))

        return info