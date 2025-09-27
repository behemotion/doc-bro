"""
Settings models for DocBro global configuration layer.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set
from pydantic import BaseModel, Field, PrivateAttr, field_validator
from .vector_store_types import VectorStoreProvider

# Non-overridable fields at project level
NON_OVERRIDABLE_FIELDS = {
    "vector_storage",
    "vector_store_provider",
    "qdrant_url",
    "ollama_url"
}

class GlobalSettings(BaseModel):
    """Global default settings for DocBro."""

    # Embedding Configuration
    embedding_model: str = Field(
        default="mxbai-embed-large",
        description="Default embedding model for vector operations"
    )

    # Vector Storage Configuration
    vector_store_provider: VectorStoreProvider = Field(
        default=VectorStoreProvider.SQLITE_VEC,
        description="Vector store backend provider (non-overridable)"
    )

    vector_storage: str = Field(
        default="~/.local/share/docbro/vectors",
        description="Default vector storage location (non-overridable)"
    )

    # Crawling Configuration
    crawl_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default crawling depth (1-10 levels)"
    )

    # Text Processing Configuration
    chunk_size: int = Field(
        default=1500,
        ge=100,
        le=10000,
        description="Default text chunk size (100-10000 characters)"
    )

    # Service Endpoints (non-overridable)
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant service endpoint (non-overridable)"
    )

    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama service endpoint (non-overridable)"
    )

    # RAG Configuration
    rag_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of context chunks for RAG"
    )

    rag_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="RAG generation temperature"
    )

    # Advanced Settings
    rate_limit: float = Field(
        default=2.0,
        ge=0.1,
        le=10.0,
        description="Requests per second for crawling"
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests"
    )

    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds"
    )

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

    class Config:
        json_schema_extra = {
            "example": {
                "embedding_model": "mxbai-embed-large",
                "vector_store_provider": "sqlite_vec",
                "vector_storage": "~/.local/share/docbro/vectors",
                "crawl_depth": 3,
                "chunk_size": 1500,
                "rag_top_k": 5,
                "rag_temperature": 0.7
            }
        }


class ProjectSettings(BaseModel):
    """Project-specific settings that override global defaults."""

    # Only overridable settings
    embedding_model: Optional[str] = None
    crawl_depth: Optional[int] = Field(None, ge=1, le=10)
    chunk_size: Optional[int] = Field(None, ge=100, le=10000)
    rag_top_k: Optional[int] = Field(None, ge=1, le=20)
    rag_temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    rate_limit: Optional[float] = Field(None, ge=0.1, le=10.0)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout: Optional[int] = Field(None, ge=5, le=300)

    # Track which settings have been explicitly set
    _modified_fields: Set[str] = PrivateAttr(default_factory=set)

    def set_field(self, field: str, value: Any):
        """Set a field and track it as modified."""
        setattr(self, field, value)
        self._modified_fields.add(field)

    def is_modified(self, field: str) -> bool:
        """Check if a field has been explicitly modified."""
        return field in self._modified_fields


class EffectiveSettings(GlobalSettings):
    """Effective settings after applying project overrides."""

    @classmethod
    def from_configs(
        cls,
        global_settings: GlobalSettings,
        project_settings: Optional[ProjectSettings] = None
    ) -> "EffectiveSettings":
        """Create effective settings by merging global and project configs."""
        data = global_settings.model_dump()

        if project_settings:
            # Apply only modified project settings
            for field, value in project_settings.model_dump(exclude_unset=True).items():
                if value is not None and field in cls.model_fields:
                    # Check if field is overridable
                    if field not in NON_OVERRIDABLE_FIELDS:
                        data[field] = value

        return cls(**data)


class SettingsMetadata(BaseModel):
    """Metadata about settings configuration."""

    version: str = Field(..., description="Settings schema version")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When settings were created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update time"
    )
    reset_count: int = Field(
        default=0,
        description="Number of factory resets"
    )
    last_reset: Optional[datetime] = Field(
        None,
        description="Last factory reset time"
    )