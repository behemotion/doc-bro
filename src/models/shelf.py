"""Shelf model for the Shelf-Box Rhyme System."""

import uuid
from datetime import datetime
from typing import Optional, ClassVar, List, TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

if TYPE_CHECKING:
    from src.models.box import Box


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
    """
    Shelf model representing a collection of boxes.

    Shelves organize boxes (documentation units) into logical collections.
    Each shelf can contain multiple boxes, and boxes can belong to multiple shelves.
    """

    # Core fields
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    is_default: bool = Field(default=False, description="Whether this is the default shelf")
    is_deletable: bool = Field(default=True, description="Whether this shelf can be deleted")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Related data (populated when needed)
    boxes: List['Box'] = Field(default_factory=list, description="List of boxes in this shelf")
    box_count: int = Field(default=0, description="Number of boxes in this shelf")

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

    def to_dict(self, include_boxes: bool = False) -> dict:
        """Convert shelf to dictionary representation."""
        data = {
            "id": self.id,
            "name": self.name,
            "is_default": self.is_default,
            "is_deletable": self.is_deletable,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "box_count": self.box_count
        }

        if include_boxes:
            data["boxes"] = self.boxes

        return data

    def to_summary(self) -> dict:
        """Get a brief summary of the shelf."""
        return {
            "name": self.name,
            "is_default": self.is_default,
            "box_count": self.box_count,
            "created_at": self.created_at.isoformat()
        }

    def __str__(self) -> str:
        """String representation."""
        default_marker = " (default)" if self.is_default else ""
        deletable = "" if self.is_deletable else " (protected)"
        return f"Shelf: {self.name}{default_marker}{deletable} [{self.box_count} boxes]"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Shelf(id='{self.id}', name='{self.name}', is_default={self.is_default}, box_count={self.box_count})"

    model_config = {
        "from_attributes": True
    }