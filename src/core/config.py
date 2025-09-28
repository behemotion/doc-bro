"""Unified configuration management for DocBro."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import SettingsConfigDict
try:
    from pydantic_settings import BaseSettings as PydanticBaseSettings
except ImportError:
    from pydantic import BaseSettings as PydanticBaseSettings

from src.models.vector_store_types import VectorStoreProvider


class ServiceDeployment(str, Enum):
    """Service deployment types."""
    DOCKER = "docker"
    LOCAL = "local"
    AUTO = "auto"
    SQLITE_VEC = "sqlite_vec"  # SQLite-vec vector store option


class DocBroConfig(PydanticBaseSettings):
    """DocBro unified configuration with environment variable support."""

    # Application settings
    debug: bool = Field(default=False)
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".docbro")

    # Service deployment configuration
    qdrant_deployment: ServiceDeployment = Field(default=ServiceDeployment.DOCKER)
    ollama_deployment: ServiceDeployment = Field(default=ServiceDeployment.LOCAL)

    # Vector store configuration
    vector_store_provider: VectorStoreProvider = Field(
        default=VectorStoreProvider.SQLITE_VEC
    )
    vector_storage: str = Field(
        default="~/.local/share/docbro/vectors"
    )

    # Service URLs
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: Optional[str] = Field(default=None)
    ollama_url: str = Field(default="http://localhost:11434")
    ollama_timeout: int = Field(default=300)

    # Crawling configuration
    crawl_depth: int = Field(default=2, ge=1, le=10)
    rate_limit: float = Field(default=2.0, ge=0.1, le=10.0)
    max_page_size_mb: float = Field(default=10.0)
    outdated_days: int = Field(default=60)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=30, ge=5, le=300)

    # Embedding configuration
    embedding_model: str = Field(default="mxbai-embed-large")
    chunk_size: int = Field(default=1000, ge=100, le=10000)  # Changed from 1500 to 1000
    chunk_overlap: int = Field(default=100, ge=0, le=1000)

    # RAG Configuration
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    # MCP Server configuration
    mcp_host: str = Field(default="localhost")
    mcp_port: int = Field(default=9382)
    mcp_auth_token: Optional[str] = Field(default=None)

    # Database configuration
    database_url: str = Field(
        default_factory=lambda: f"sqlite+aiosqlite:///{Path.home() / '.docbro' / 'docbro.db'}"
    )

    # Logging configuration
    log_level: str = Field(default="WARNING")
    log_file: Optional[Path] = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="DOCBRO_",
        validate_assignment=True
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

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name."""
        allowed_models = {
            "mxbai-embed-large",
            "nomic-embed-text",
            "all-minilm",
            "bge-small-en"
        }
        if v not in allowed_models:
            raise ValueError(f"Model must be one of: {allowed_models}")
        return v

    @field_validator("vector_storage")
    @classmethod
    def validate_storage_path(cls, v: str) -> str:
        """Validate and expand storage path."""
        path = Path(v).expanduser()
        return str(path)

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