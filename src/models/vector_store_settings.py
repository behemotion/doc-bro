"""Vector store settings model."""

from typing import Optional
from pydantic import BaseModel, Field, model_validator

from src.models.vector_store_types import VectorStoreProvider
from src.models.sqlite_vec_config import SQLiteVecConfiguration


class QdrantConfiguration(BaseModel):
    """Configuration for Qdrant vector store."""

    url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for authentication"
    )
    collection_name_prefix: str = Field(
        default="docbro_",
        description="Prefix for collection names"
    )


class VectorStoreSettings(BaseModel):
    """Settings for vector store selection and configuration."""

    provider: VectorStoreProvider = Field(
        description="Selected vector store provider"
    )
    qdrant_config: Optional[QdrantConfiguration] = Field(
        default=None,
        description="Configuration for Qdrant (required if provider is QDRANT)"
    )
    sqlite_vec_config: Optional[SQLiteVecConfiguration] = Field(
        default=None,
        description="Configuration for SQLite-vec (required if provider is SQLITE_VEC)"
    )

    @model_validator(mode="after")
    def validate_provider_config(self) -> "VectorStoreSettings":
        """Validate that provider matches configuration."""
        # Check provider has matching configuration
        if self.provider == VectorStoreProvider.QDRANT:
            if not self.qdrant_config:
                raise ValueError("Qdrant configuration required for QDRANT provider")
            if self.sqlite_vec_config:
                raise ValueError("Provider mismatch: QDRANT provider with SQLite config")

        elif self.provider == VectorStoreProvider.SQLITE_VEC:
            if not self.sqlite_vec_config:
                raise ValueError("SQLite-vec configuration required for SQLITE_VEC provider")
            if self.qdrant_config:
                raise ValueError("Provider mismatch: SQLITE_VEC provider with Qdrant config")

        # Ensure exactly one configuration is set
        configs_set = sum([
            self.qdrant_config is not None,
            self.sqlite_vec_config is not None
        ])

        if configs_set == 0:
            raise ValueError("No vector store configuration provided")
        elif configs_set > 1:
            raise ValueError("Only one configuration allowed at a time")

        return self

    def get_active_config(self):
        """Get the active configuration based on provider."""
        if self.provider == VectorStoreProvider.QDRANT:
            return self.qdrant_config
        elif self.provider == VectorStoreProvider.SQLITE_VEC:
            return self.sqlite_vec_config
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def is_local_provider(self) -> bool:
        """Check if using a local provider (SQLite-vec)."""
        return self.provider == VectorStoreProvider.SQLITE_VEC

    def requires_external_service(self) -> bool:
        """Check if provider requires external service."""
        return self.provider == VectorStoreProvider.QDRANT

    class Config:
        """Pydantic configuration."""

        use_enum_values = False  # Keep enums as objects