"""Configuration management for DocBro."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, Field
try:
    from pydantic_settings import BaseSettings as PydanticBaseSettings
except ImportError:
    from pydantic import ConfigDict, BaseSettings as PydanticBaseSettings


class ServiceDeployment(str, Enum):
    """Service deployment types."""
    DOCKER = "docker"
    LOCAL = "local"
    AUTO = "auto"


class DocBroConfig(PydanticBaseSettings):
    """DocBro configuration with environment variable support."""

    # Application settings
    debug: bool = Field(default=False, env="DOCBRO_DEBUG")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".docbro")

    # Service deployment configuration
    qdrant_deployment: ServiceDeployment = Field(default=ServiceDeployment.DOCKER, env="DOCBRO_QDRANT_DEPLOYMENT")
    # Redis removed - no longer supported
    ollama_deployment: ServiceDeployment = Field(default=ServiceDeployment.LOCAL, env="DOCBRO_OLLAMA_DEPLOYMENT")

    # Qdrant configuration
    qdrant_url: str = Field(default="http://localhost:6333", env="DOCBRO_QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="DOCBRO_QDRANT_API_KEY")

    # Redis removed - configuration no longer supported

    # Ollama configuration
    ollama_url: str = Field(default="http://localhost:11434", env="DOCBRO_OLLAMA_URL")
    ollama_timeout: int = Field(default=300, env="DOCBRO_OLLAMA_TIMEOUT")

    # Crawling configuration
    default_crawl_depth: int = Field(default=3, env="DOCBRO_DEFAULT_CRAWL_DEPTH")
    default_rate_limit: float = Field(default=1.0, env="DOCBRO_DEFAULT_RATE_LIMIT")
    max_page_size_mb: float = Field(default=10.0, env="DOCBRO_MAX_PAGE_SIZE_MB")
    outdated_days: int = Field(default=60, env="DOCBRO_OUTDATED_DAYS")

    # Embedding configuration
    default_embedding_model: str = Field(default="mxbai-embed-large", env="DOCBRO_DEFAULT_EMBEDDING_MODEL")
    embedding_model: str = Field(default="mxbai-embed-large", env="DOCBRO_EMBEDDING_MODEL")  # Alias for compatibility
    chunk_size: int = Field(default=500, env="DOCBRO_CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="DOCBRO_CHUNK_OVERLAP")

    # MCP Server configuration
    mcp_host: str = Field(default="localhost", env="DOCBRO_MCP_HOST")
    mcp_port: int = Field(default=9382, env="DOCBRO_MCP_PORT")
    mcp_auth_token: Optional[str] = Field(default=None, env="DOCBRO_MCP_AUTH_TOKEN")

    # Database configuration
    database_url: str = Field(
        default_factory=lambda: f"sqlite+aiosqlite:///{Path.home() / '.docbro' / 'docbro.db'}",
        env="DOCBRO_DATABASE_URL"
    )

    # Logging configuration
    log_level: str = Field(default="INFO", env="DOCBRO_LOG_LEVEL")
    log_file: Optional[Path] = Field(default=None, env="DOCBRO_LOG_FILE")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        """Initialize configuration and create data directory."""
        super().__init__(**kwargs)

        # Check for Redis configuration and reject it
        if os.getenv("DOCBRO_REDIS_URL") or os.getenv("DOCBRO_REDIS_PASSWORD"):
            raise ValueError("Redis configuration detected but no longer supported")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "cache").mkdir(exist_ok=True)
        (self.data_dir / "exports").mkdir(exist_ok=True)

    @property
    def database_path(self) -> Path:
        """Get database file path."""
        return self.data_dir / "docbro.db"

    @property
    def cache_dir(self) -> Path:
        """Get cache directory."""
        return self.data_dir / "cache"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        return self.data_dir / "logs"

    @property
    def exports_dir(self) -> Path:
        """Get exports directory."""
        return self.data_dir / "exports"

    def detect_service_availability(self) -> dict[str, bool]:
        """Auto-detect which services are available."""
        availability = {}

        # Check Qdrant
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=self.qdrant_url)
            client.get_collections()
            availability["qdrant"] = True
        except Exception:
            availability["qdrant"] = False

        # Redis removed - no longer checking for Redis availability

        # Check Ollama
        try:
            import httpx
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=5.0)
            availability["ollama"] = response.status_code == 200
        except Exception:
            availability["ollama"] = False

        # Check Docker
        try:
            import docker
            client = docker.from_env()
            client.ping()
            availability["docker"] = True
        except Exception:
            availability["docker"] = False

        return availability

    def get_effective_deployment_strategy(self) -> dict[str, ServiceDeployment]:
        """Get the effective deployment strategy after auto-detection."""
        if all(
            dep != ServiceDeployment.AUTO
            for dep in [self.qdrant_deployment, self.ollama_deployment]
        ):
            return {
                "qdrant": self.qdrant_deployment,
                # Redis removed - no longer part of deployment strategy
                "ollama": self.ollama_deployment,
            }

        # Auto-detection required
        availability = self.detect_service_availability()

        strategy = {}

        # Qdrant strategy
        if self.qdrant_deployment == ServiceDeployment.AUTO:
            if availability.get("docker", False):
                strategy["qdrant"] = ServiceDeployment.DOCKER
            elif availability.get("qdrant", False):
                strategy["qdrant"] = ServiceDeployment.LOCAL
            else:
                strategy["qdrant"] = ServiceDeployment.DOCKER  # Default fallback
        else:
            strategy["qdrant"] = self.qdrant_deployment

        # Redis removed - no longer part of deployment strategy

        # Ollama strategy (prefer local for better performance)
        if self.ollama_deployment == ServiceDeployment.AUTO:
            if availability.get("ollama", False):
                strategy["ollama"] = ServiceDeployment.LOCAL
            else:
                strategy["ollama"] = ServiceDeployment.LOCAL  # Default fallback
        else:
            strategy["ollama"] = self.ollama_deployment

        return strategy


# Global configuration instance
config = DocBroConfig()


def get_config() -> DocBroConfig:
    """Get the global configuration instance."""
    return config


def reload_config() -> DocBroConfig:
    """Reload configuration from environment and files."""
    global config
    config = DocBroConfig()
    return config