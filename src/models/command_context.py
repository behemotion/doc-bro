"""Command context model for shelf/box command state tracking."""

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .configuration_state import ConfigurationState


class CommandContext(BaseModel):
    """Represents the current state and metadata for shelf/box commands."""

    entity_name: str = Field(
        description="Name of the shelf or box being accessed"
    )
    entity_type: Literal["shelf", "box"] = Field(
        description="Type of entity"
    )
    entity_exists: bool = Field(
        description="Whether the entity exists in the database"
    )
    is_empty: Optional[bool] = Field(
        default=None,
        description="Whether the entity has no content (only applicable if exists=True)"
    )
    configuration_state: ConfigurationState = Field(
        description="Current setup/configuration status"
    )
    last_modified: datetime = Field(
        description="When the entity was last updated"
    )
    content_summary: Optional[str] = Field(
        default=None,
        description="Brief description of current content"
    )

    @model_validator(mode='after')
    def validate_command_context(self) -> 'CommandContext':
        """Validate command context logic."""
        # Validate entity name format
        if not self._is_valid_entity_name(self.entity_name):
            raise ValueError("entity_name must be valid identifier (alphanumeric + underscores + hyphens)")

        # Validate is_empty logic
        if not self.entity_exists and self.is_empty is not None:
            raise ValueError("is_empty only meaningful when entity_exists=True")

        return self

    def _is_valid_entity_name(self, name: str) -> bool:
        """Check if entity name follows valid identifier format."""
        if not name:
            return False

        # Allow alphanumeric characters, underscores, and hyphens
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name))

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }