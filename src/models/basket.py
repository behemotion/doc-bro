"""Basket model (project within a shelf)."""

from datetime import datetime
from enum import Enum
from typing import Optional, ClassVar
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class BasketType(str, Enum):
    """Types of baskets."""
    DATA = "data"
    CRAWLING = "crawling"
    STORAGE = "storage"


class BasketStatus(str, Enum):
    """Status of a basket."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CRAWLING = "crawling"
    PROCESSING = "processing"
    ERROR = "error"
    COMPLETED = "completed"


class BasketValidationError(Exception):
    """Raised when basket validation fails."""
    pass


class BasketExistsError(Exception):
    """Raised when attempting to create a basket that already exists."""
    pass


class BasketNotFoundError(Exception):
    """Raised when a basket is not found."""
    pass


class Basket(BaseModel):
    """Basket model representing a project within a shelf."""

    # Core fields
    id: str = Field(default_factory=lambda: f"basket-{uuid4().hex[:12]}")
    name: str = Field(..., min_length=1, max_length=100)
    shelf_id: str = Field(..., description="ID of the parent shelf")
    type: BasketType = Field(default=BasketType.DATA)
    status: BasketStatus = Field(default=BasketStatus.ACTIVE)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_operation_at: Optional[datetime] = Field(default=None)

    # Crawling configuration (for crawling type)
    source_url: Optional[str] = Field(default=None)
    crawl_depth: int = Field(default=3, ge=1, le=10)
    rate_limit: float = Field(default=1.0, ge=0.1, le=10.0)
    max_pages: int = Field(default=100, ge=1, le=10000)

    # Processing configuration
    embedding_model: str = Field(default="mxbai-embed-large")
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)

    # Statistics
    total_pages: int = Field(default=0, ge=0)
    total_size_bytes: int = Field(default=0, ge=0)
    successful_pages: int = Field(default=0, ge=0)
    failed_pages: int = Field(default=0, ge=0)

    # Settings and metadata
    settings: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    # Constants
    MAX_NAME_LENGTH: ClassVar[int] = 100
    RESERVED_NAMES: ClassVar[set[str]] = {"default", "system", "temp", "tmp", "test"}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate basket name."""
        if not v or not v.strip():
            raise BasketValidationError("Basket name cannot be empty")

        v = v.strip()

        # Check length
        if len(v) > cls.MAX_NAME_LENGTH:
            raise BasketValidationError(f"Basket name cannot exceed {cls.MAX_NAME_LENGTH} characters")

        # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise BasketValidationError(
                "Basket name can only contain letters, numbers, hyphens, underscores, and spaces"
            )

        # Check for reserved names
        if v.lower() in cls.RESERVED_NAMES:
            raise BasketValidationError(f"'{v}' is a reserved basket name")

        return v

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: Optional[str], values) -> Optional[str]:
        """Validate source URL for crawling baskets."""
        if v and v.strip():
            v = v.strip()
            # Basic URL validation
            if not (v.startswith("http://") or v.startswith("https://")):
                raise BasketValidationError("Source URL must start with http:// or https://")
        return v

    @model_validator(mode="after")
    def validate_crawling_fields(self) -> Self:
        """Ensure crawling fields are set for crawling type baskets."""
        if self.type == BasketType.CRAWLING:
            if not self.source_url:
                raise BasketValidationError("Source URL is required for crawling baskets")
        return self

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> Self:
        """Ensure chunk overlap is less than chunk size."""
        if self.chunk_overlap >= self.chunk_size:
            raise BasketValidationError("Chunk overlap must be less than chunk size")
        return self

    @model_validator(mode="after")
    def update_timestamps(self) -> Self:
        """Ensure updated_at is always current or newer than created_at."""
        if self.updated_at < self.created_at:
            self.updated_at = self.created_at
        return self

    def to_dict(self, include_statistics: bool = True) -> dict:
        """Convert basket to dictionary representation."""
        data = {
            "id": self.id,
            "name": self.name,
            "shelf_id": self.shelf_id,
            "type": self.type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_operation_at": self.last_operation_at.isoformat() if self.last_operation_at else None,
            "source_url": self.source_url,
            "settings": self.settings,
            "metadata": self.metadata
        }

        if include_statistics:
            data.update({
                "total_pages": self.total_pages,
                "total_size_bytes": self.total_size_bytes,
                "successful_pages": self.successful_pages,
                "failed_pages": self.failed_pages
            })

        if self.type == BasketType.CRAWLING:
            data.update({
                "crawl_depth": self.crawl_depth,
                "rate_limit": self.rate_limit,
                "max_pages": self.max_pages
            })

        data.update({
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        })

        return data

    def to_summary(self) -> dict:
        """Get a brief summary of the basket."""
        return {
            "name": self.name,
            "type": self.type.value,
            "status": self.status.value,
            "pages": self.total_pages,
            "created_at": self.created_at.isoformat()
        }

    def update_status(self, status: BasketStatus) -> None:
        """Update basket status."""
        self.status = status
        self.updated_at = datetime.utcnow()
        self.last_operation_at = datetime.utcnow()

    def update_statistics(
        self,
        total_pages: Optional[int] = None,
        total_size_bytes: Optional[int] = None,
        successful_pages: Optional[int] = None,
        failed_pages: Optional[int] = None
    ) -> None:
        """Update basket statistics."""
        if total_pages is not None:
            self.total_pages = total_pages
        if total_size_bytes is not None:
            self.total_size_bytes = total_size_bytes
        if successful_pages is not None:
            self.successful_pages = successful_pages
        if failed_pages is not None:
            self.failed_pages = failed_pages

        self.updated_at = datetime.utcnow()
        self.last_operation_at = datetime.utcnow()

    def add_metadata(self, key: str, value: any) -> None:
        """Add or update metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def get_metadata(self, key: str, default: any = None) -> any:
        """Get metadata value."""
        return self.metadata.get(key, default)

    def add_setting(self, key: str, value: any) -> None:
        """Add or update setting."""
        self.settings[key] = value
        self.updated_at = datetime.utcnow()

    def get_setting(self, key: str, default: any = None) -> any:
        """Get setting value."""
        return self.settings.get(key, default)

    def is_active(self) -> bool:
        """Check if basket is active."""
        return self.status == BasketStatus.ACTIVE

    def is_crawling_type(self) -> bool:
        """Check if basket is of crawling type."""
        return self.type == BasketType.CRAWLING

    def __str__(self) -> str:
        """String representation."""
        return f"Basket: {self.name} ({self.type.value}) [{self.status.value}]"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Basket(id='{self.id}', name='{self.name}', shelf_id='{self.shelf_id}', type={self.type.value}, status={self.status.value})"