"""Shelf model for organizing baskets (projects) into collections."""

from datetime import datetime
from typing import Optional, ClassVar
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class ShelfValidationError(Exception):
    """Raised when shelf validation fails."""
    pass


class ShelfExistsError(Exception):
    """Raised when attempting to create a shelf that already exists."""
    pass


class ShelfNotFoundError(Exception):
    """Raised when a shelf is not found."""
    pass


class Shelf(BaseModel):
    """Shelf model representing a collection of baskets."""

    # Core fields
    id: str = Field(default_factory=lambda: f"shelf-{uuid4().hex[:12]}")
    name: str = Field(..., min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Status fields
    is_current: bool = Field(default=False, description="Whether this is the current active shelf")

    # Metadata
    metadata: dict = Field(default_factory=dict, description="Additional shelf metadata")

    # Related data (populated when needed)
    baskets: list = Field(default_factory=list, description="List of baskets in this shelf")
    basket_count: int = Field(default=0, description="Number of baskets in this shelf")

    # Constants
    MAX_NAME_LENGTH: ClassVar[int] = 100
    RESERVED_NAMES: ClassVar[set[str]] = {"default", "system", "temp", "tmp", "test"}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate shelf name."""
        if not v or not v.strip():
            raise ShelfValidationError("Shelf name cannot be empty")

        v = v.strip()

        # Check length
        if len(v) > cls.MAX_NAME_LENGTH:
            raise ShelfValidationError(f"Shelf name cannot exceed {cls.MAX_NAME_LENGTH} characters")

        # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ShelfValidationError(
                "Shelf name can only contain letters, numbers, hyphens, underscores, and spaces"
            )

        # Check for reserved names
        if v.lower() in cls.RESERVED_NAMES:
            raise ShelfValidationError(f"'{v}' is a reserved shelf name")

        return v

    @model_validator(mode="after")
    def update_timestamps(self) -> Self:
        """Ensure updated_at is always current or newer than created_at."""
        if self.updated_at < self.created_at:
            self.updated_at = self.created_at
        return self

    def to_dict(self, include_baskets: bool = False) -> dict:
        """Convert shelf to dictionary representation."""
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_current": self.is_current,
            "basket_count": self.basket_count,
            "metadata": self.metadata
        }

        if include_baskets:
            data["baskets"] = self.baskets

        return data

    def to_summary(self) -> dict:
        """Get a brief summary of the shelf."""
        return {
            "name": self.name,
            "is_current": self.is_current,
            "basket_count": self.basket_count,
            "created_at": self.created_at.isoformat()
        }

    def add_metadata(self, key: str, value: any) -> None:
        """Add or update metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def get_metadata(self, key: str, default: any = None) -> any:
        """Get metadata value."""
        return self.metadata.get(key, default)

    def set_current(self) -> None:
        """Mark this shelf as current."""
        self.is_current = True
        self.updated_at = datetime.utcnow()

    def unset_current(self) -> None:
        """Unmark this shelf as current."""
        self.is_current = False
        self.updated_at = datetime.utcnow()

    def __str__(self) -> str:
        """String representation."""
        current = " (current)" if self.is_current else ""
        return f"Shelf: {self.name}{current} [{self.basket_count} baskets]"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Shelf(id='{self.id}', name='{self.name}', is_current={self.is_current}, basket_count={self.basket_count})"