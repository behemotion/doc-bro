"""
Settings models for backward compatibility with test suite.

This module provides compatibility models that wrap the unified DocBroConfig
from src.core.config to maintain existing test contracts.
"""

from pydantic import BaseModel, Field

from src.core.config import DocBroConfig
from src.models.vector_store_types import VectorStoreProvider


class GlobalSettings(BaseModel):
    """Global settings model for backward compatibility."""

    # Crawling configuration
    crawl_depth: int = Field(default=3, ge=1, le=10)
    rate_limit: float = Field(default=2.0, ge=0.1, le=10.0)
    max_page_size_mb: float = Field(default=10.0)
    outdated_days: int = Field(default=60)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=30, ge=5, le=300)

    # Embedding configuration
    embedding_model: str = Field(default="mxbai-embed-large")
    chunk_size: int = Field(default=1500, ge=100, le=10000)  # Test expects 1500
    chunk_overlap: int = Field(default=100, ge=0, le=1000)

    # RAG Configuration
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    # Vector store configuration
    vector_store_provider: VectorStoreProvider = Field(default=VectorStoreProvider.SQLITE_VEC)
    vector_storage: str = Field(default="~/.local/share/docbro/vectors")

    # Service URLs
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str | None = Field(default=None)
    ollama_url: str = Field(default="http://localhost:11434")
    ollama_timeout: int = Field(default=300)

    # MCP Server configuration
    mcp_host: str = Field(default="localhost")
    mcp_port: int = Field(default=9382)
    mcp_auth_token: str | None = Field(default=None)

    # Logging configuration
    log_level: str = Field(default="WARNING")

    @classmethod
    def from_config(cls, config: DocBroConfig) -> "GlobalSettings":
        """Create GlobalSettings from DocBroConfig."""
        # Create with defaults first, then override with config values
        data = {}
        for field_name in cls.model_fields:
            if hasattr(config, field_name):
                data[field_name] = getattr(config, field_name)

        return cls(**data)


class ProjectSettings(BaseModel):
    """Project-specific settings that can override global settings."""

    # Only overridable fields
    crawl_depth: int | None = Field(default=None, ge=1, le=10)
    rate_limit: float | None = Field(default=None, ge=0.1, le=10.0)
    max_page_size_mb: float | None = Field(default=None)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    timeout: int | None = Field(default=None, ge=5, le=300)
    embedding_model: str | None = Field(default=None)
    chunk_size: int | None = Field(default=None, ge=100, le=10000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000)
    rag_top_k: int | None = Field(default=None, ge=1, le=20)
    rag_temperature: float | None = Field(default=None, ge=0.0, le=1.0)

    # Track which fields have been explicitly set
    modified_fields: set[str] = Field(default_factory=set, exclude=True)


class EffectiveSettings(BaseModel):
    """Effective settings after applying project overrides to global settings."""

    # All fields from GlobalSettings
    crawl_depth: int = Field(ge=1, le=10)
    rate_limit: float = Field(ge=0.1, le=10.0)
    max_page_size_mb: float
    outdated_days: int
    max_retries: int = Field(ge=0, le=10)
    timeout: int = Field(ge=5, le=300)
    embedding_model: str
    chunk_size: int = Field(ge=100, le=10000)
    chunk_overlap: int = Field(ge=0, le=1000)
    rag_top_k: int = Field(ge=1, le=20)
    rag_temperature: float = Field(ge=0.0, le=1.0)
    vector_store_provider: VectorStoreProvider
    vector_storage: str
    qdrant_url: str
    qdrant_api_key: str | None
    ollama_url: str
    ollama_timeout: int
    mcp_host: str
    mcp_port: int
    mcp_auth_token: str | None
    log_level: str

    @classmethod
    def from_configs(
        cls,
        global_settings: GlobalSettings,
        project_settings: ProjectSettings | None = None
    ) -> "EffectiveSettings":
        """Create effective settings by merging global and project settings."""
        # Start with global settings
        data = global_settings.model_dump()

        # Apply project overrides for overridable fields only
        if project_settings:
            overridable_fields = {
                'crawl_depth', 'rate_limit', 'max_page_size_mb', 'max_retries',
                'timeout', 'embedding_model', 'chunk_size', 'chunk_overlap',
                'rag_top_k', 'rag_temperature'
            }

            for field in overridable_fields:
                project_value = getattr(project_settings, field, None)
                if project_value is not None and field in getattr(project_settings, 'modified_fields', set()):
                    data[field] = project_value

        return cls(**data)
