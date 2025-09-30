"""ShelfBox junction model for many-to-many relationship between shelves and boxes."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class ShelfBoxValidationError(Exception):
    """Raised when shelf-box relationship validation fails."""
    pass


class ShelfBox(BaseModel):
    """
    Junction model for the many-to-many relationship between shelves and boxes.

    This model represents the association between a shelf and a box,
    including metadata about when the box was added and its position
    within the shelf.
    """

    # Core relationship fields
    shelf_id: str = Field(..., description="ID of the shelf")
    box_id: str = Field(..., description="ID of the box")

    # Relationship metadata
    position: Optional[int] = Field(None, description="Display position within the shelf")
    added_at: datetime = Field(default_factory=datetime.utcnow, description="When box was added to shelf")

    @model_validator(mode="after")
    def validate_relationship(self) -> Self:
        """Validate the shelf-box relationship."""
        if not self.shelf_id or not self.shelf_id.strip():
            raise ShelfBoxValidationError("shelf_id cannot be empty")

        if not self.box_id or not self.box_id.strip():
            raise ShelfBoxValidationError("box_id cannot be empty")

        if self.position is not None and self.position < 0:
            raise ShelfBoxValidationError("position must be non-negative")

        return self

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "shelf_id": self.shelf_id,
            "box_id": self.box_id,
            "position": self.position,
            "added_at": self.added_at.isoformat()
        }

    def __str__(self) -> str:
        """String representation."""
        position_info = f" at position {self.position}" if self.position is not None else ""
        return f"ShelfBox: {self.box_id} in {self.shelf_id}{position_info}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"ShelfBox(shelf_id='{self.shelf_id}', box_id='{self.box_id}', position={self.position})"

    model_config = {
        "from_attributes": True
    }