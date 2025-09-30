"""Box model for the Shelf-Box Rhyme System."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

from src.models.box_type import BoxType


class BoxValidationError(Exception):
    """Raised when box validation fails."""
    pass


class BoxExistsError(Exception):
    """Raised when attempting to create a box that already exists."""
    pass


class BoxNotFoundError(Exception):
    """Raised when a box is not found."""
    pass


class Box(BaseModel):
    """
    Box model representing a documentation storage unit.

    Boxes are the fundamental unit of documentation storage, replacing the
    concept of "projects". Each box has a type (drag/rag/bag) that determines
    how the fill command operates on it.
    """

    # Core fields
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    type: BoxType = Field(..., description="Box type (drag/rag/bag)")
    is_deletable: bool = Field(default=True, description="Whether this box can be deleted")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Type-specific fields (for drag boxes - website crawling)
    url: Optional[str] = Field(None, description="Source URL for drag boxes")
    max_pages: Optional[int] = Field(None, ge=1, description="Maximum pages to crawl")
    rate_limit: Optional[float] = Field(None, gt=0, description="Requests per second")
    crawl_depth: Optional[int] = Field(None, ge=1, description="Maximum crawl depth")

    # Configuration and settings
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Box-specific settings")

    # Constants
    MAX_NAME_LENGTH: ClassVar[int] = 100
    RESERVED_NAMES: ClassVar[set[str]] = {"default", "system", "temp", "tmp", "test"}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate box name."""
        if not v or not v.strip():
            raise BoxValidationError("Box name cannot be empty")

        v = v.strip()

        # Check length
        if len(v) > cls.MAX_NAME_LENGTH:
            raise BoxValidationError(f"Box name cannot exceed {cls.MAX_NAME_LENGTH} characters")

        # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_]*$', v):
            raise BoxValidationError(
                "Box name must start with alphanumeric and contain only letters, numbers, hyphens, underscores, and spaces"
            )

        # Check for reserved names
        if v.lower() in cls.RESERVED_NAMES:
            raise BoxValidationError(f"'{v}' is a reserved box name")

        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Basic URL validation
        if not (v.startswith("http://") or v.startswith("https://")):
            raise BoxValidationError("URL must start with http:// or https://")

        return v

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> Self:
        """Validate fields based on box type."""
        if self.type == BoxType.DRAG:
            # Drag boxes should have URL for crawling
            if not self.url:
                raise BoxValidationError("Drag boxes require a URL")

        # Update timestamp
        if self.updated_at < self.created_at:
            self.updated_at = self.created_at

        return self

    def to_dict(self, include_type_fields: bool = True) -> Dict[str, Any]:
        """Convert box to dictionary representation."""
        # Note: self.type is already a string due to use_enum_values=True
        box_type = self.type if isinstance(self.type, str) else self.type.value
        data = {
            "id": self.id,
            "name": self.name,
            "type": box_type,
            "is_deletable": self.is_deletable,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if include_type_fields:
            # Include type-specific fields
            if self.url:
                data["url"] = self.url
            if self.max_pages:
                data["max_pages"] = self.max_pages
            if self.rate_limit:
                data["rate_limit"] = self.rate_limit
            if self.crawl_depth:
                data["crawl_depth"] = self.crawl_depth
            if self.settings:
                data["settings"] = self.settings

        return data

    def to_summary(self) -> Dict[str, Any]:
        """Get a brief summary of the box."""
        box_type = self.type if isinstance(self.type, str) else self.type.value
        return {
            "name": self.name,
            "type": box_type,
            "is_deletable": self.is_deletable,
            "created_at": self.created_at.isoformat()
        }

    def get_type_description(self) -> str:
        """Get human-readable description of the box type."""
        # Handle both string and enum types
        if isinstance(self.type, str):
            box_type_enum = BoxType(self.type)
        else:
            box_type_enum = self.type
        return box_type_enum.get_description()

    def is_drag_box(self) -> bool:
        """Check if this is a drag (crawling) box."""
        return self.type == BoxType.DRAG.value or self.type == BoxType.DRAG

    def is_rag_box(self) -> bool:
        """Check if this is a rag (document import) box."""
        return self.type == BoxType.RAG.value or self.type == BoxType.RAG

    def is_bag_box(self) -> bool:
        """Check if this is a bag (storage) box."""
        return self.type == BoxType.BAG.value or self.type == BoxType.BAG

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update box settings and timestamp."""
        if not self.settings:
            self.settings = {}
        self.settings.update(settings)
        self.updated_at = datetime.now(timezone.utc)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        if not self.settings:
            return default
        return self.settings.get(key, default)

    def __str__(self) -> str:
        """String representation."""
        box_type = self.type if isinstance(self.type, str) else self.type.value
        protected = "" if self.is_deletable else " (protected)"
        url_info = f" -> {self.url}" if self.url else ""
        return f"Box: {self.name} ({box_type}){protected}{url_info}"

    def __repr__(self) -> str:
        """Developer representation."""
        box_type = self.type if isinstance(self.type, str) else self.type.value
        return f"Box(id='{self.id}', name='{self.name}', type='{box_type}', is_deletable={self.is_deletable})"

    model_config = {
        "from_attributes": True,
        "use_enum_values": True
    }