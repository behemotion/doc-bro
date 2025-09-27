"""SQLite-vec configuration model."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SQLiteVecConfiguration(BaseModel):
    """Configuration for SQLite-vec vector store."""

    enabled: bool = Field(default=True, description="Whether SQLite-vec is enabled")
    database_path: Path = Field(description="Path to SQLite database file")
    vector_dimensions: int = Field(
        default=1024,
        description="Vector dimensions (must match embedding model)",
        ge=1,
        le=4096,
    )
    batch_size: int = Field(
        default=100,
        description="Batch size for vector operations",
        ge=1,
        le=1000,
    )
    max_connections: int = Field(
        default=5,
        description="Maximum number of connections",
        ge=1,
        le=10,
    )
    wal_mode: bool = Field(
        default=True,
        description="Enable WAL mode for better concurrency"
    )
    busy_timeout: int = Field(
        default=5000,
        description="Busy timeout in milliseconds",
        ge=100,
        le=30000,
    )
    data_directory: Optional[Path] = Field(
        default=None,
        description="Base data directory for validation"
    )

    @field_validator("vector_dimensions")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        """Validate vector dimensions."""
        if v <= 0:
            raise ValueError("Vector dimensions must be greater than 0")
        if v > 4096:
            raise ValueError("Vector dimensions must be less than or equal to 4096")
        return v

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size."""
        if v < 1:
            raise ValueError("Batch size must be at least 1")
        if v > 1000:
            raise ValueError("Batch size must be at most 1000")
        return v

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """Validate max connections."""
        if v < 1:
            raise ValueError("Max connections must be at least 1")
        if v > 10:
            raise ValueError("Max connections must be at most 10")
        return v

    @model_validator(mode="after")
    def validate_database_path(self) -> "SQLiteVecConfiguration":
        """Validate database path is within data directory if specified."""
        if self.data_directory:
            try:
                # Resolve paths for comparison
                db_path = self.database_path.resolve()
                data_dir = self.data_directory.resolve()

                # Check if database path is within data directory
                db_path.relative_to(data_dir)
            except (ValueError, RuntimeError):
                raise ValueError(
                    f"Database path must be within data directory: {self.data_directory}"
                )
        return self

    def get_connection_string(self) -> str:
        """Generate SQLite connection string with parameters."""
        params = []

        if self.wal_mode:
            params.append("mode=wal")

        if self.busy_timeout:
            # Convert milliseconds to seconds for some SQLite interfaces
            params.append(f"timeout={self.busy_timeout/1000:.1f}")

        conn_str = str(self.database_path)
        if params:
            conn_str += "?" + "&".join(params)

        return conn_str

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            Path: str
        }