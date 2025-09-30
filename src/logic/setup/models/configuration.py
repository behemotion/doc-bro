"""Setup configuration model."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from src.models.vector_store_types import VectorStoreProvider


class SetupConfiguration(BaseModel):
    """Contains all configuration parameters for setup operations."""

    vector_store_provider: VectorStoreProvider = Field(
        default=VectorStoreProvider.SQLITE_VEC,
        description="Selected vector store provider"
    )
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama service URL"
    )
    embedding_model: str = Field(
        default="mxbai-embed-large",
        description="Model for embeddings"
    )
    directories: dict[str, Path] = Field(
        default_factory=dict,
        description="System directories (config, data, cache)"
    )
    services_detected: dict[str, dict] = Field(
        default_factory=dict,
        description="Available services and their info"
    )
    installation_timestamp: datetime | None = Field(
        default=None,
        description="When first installed (UTC)"
    )
    last_modified: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last configuration change (UTC)"
    )

    @field_validator("ollama_url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL format: {v}")
        return v

    @field_validator("embedding_model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate embedding model is supported."""
        supported_models = [
            "mxbai-embed-large",
            "nomic-embed-text",
            "all-minilm",
            "bge-small",
            "bge-large"
        ]
        if v not in supported_models:
            raise ValueError(
                f"Unsupported embedding model: {v}. "
                f"Supported models: {', '.join(supported_models)}"
            )
        return v

    @field_validator("directories")
    @classmethod
    def validate_paths(cls, v: dict[str, Path]) -> dict[str, Path]:
        """Validate that all paths are absolute."""
        for key, path in v.items():
            if not path.is_absolute():
                raise ValueError(f"Directory path must be absolute: {key}={path}")
        return v

    def update_service_status(self, service: str, info: dict) -> None:
        """Update the status of a detected service."""
        self.services_detected[service] = {
            **info,
            "last_check": datetime.now(datetime.UTC).isoformat()
        }
        self.last_modified = datetime.now(datetime.UTC)

    def is_initialized(self) -> bool:
        """Check if configuration has been initialized."""
        return self.installation_timestamp is not None

    def mark_initialized(self) -> None:
        """Mark configuration as initialized."""
        if not self.installation_timestamp:
            self.installation_timestamp = datetime.now(datetime.UTC)
            self.last_modified = datetime.now(datetime.UTC)

    def to_yaml_dict(self) -> dict:
        """Convert to YAML-serializable dictionary."""
        data = self.model_dump(exclude_none=True)

        # Convert Path objects to strings
        if "directories" in data:
            data["directories"] = {
                k: str(v) for k, v in data["directories"].items()
            }

        # Convert datetime objects to ISO strings
        for field in ["installation_timestamp", "last_modified"]:
            if field in data and data[field]:
                if isinstance(data[field], datetime):
                    data[field] = data[field].isoformat() + "Z"

        # Convert enum to string
        if "vector_store_provider" in data:
            data["vector_store_provider"] = data["vector_store_provider"].value

        return data

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "SetupConfiguration":
        """Create from YAML-loaded dictionary."""
        # Convert string paths back to Path objects
        if "directories" in data:
            data["directories"] = {
                k: Path(v) for k, v in data["directories"].items()
            }

        # Convert ISO strings back to datetime
        for field in ["installation_timestamp", "last_modified"]:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    # Remove 'Z' suffix if present and parse
                    timestamp_str = data[field].rstrip("Z")
                    data[field] = datetime.fromisoformat(timestamp_str)

        # Convert string to enum
        if "vector_store_provider" in data:
            if isinstance(data["vector_store_provider"], str):
                data["vector_store_provider"] = VectorStoreProvider(data["vector_store_provider"])

        return cls(**data)

    model_config = {
        "use_enum_values": False  # Keep enums as enums
    }
