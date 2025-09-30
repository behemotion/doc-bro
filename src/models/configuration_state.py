"""Configuration state model for tracking entity setup status."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ConfigurationState(BaseModel):
    """Represents the setup/configuration status of entities."""

    is_configured: bool = Field(
        description="Whether initial setup has been completed"
    )
    has_content: bool = Field(
        description="Whether entity contains any data"
    )
    configuration_version: str = Field(
        description="Version of configuration schema used"
    )
    setup_completed_at: Optional[datetime] = Field(
        default=None,
        description="When initial setup finished"
    )
    needs_migration: bool = Field(
        default=False,
        description="Whether configuration needs updating"
    )

    @model_validator(mode='after')
    def validate_configuration_state(self) -> 'ConfigurationState':
        """Validate configuration state logic."""
        # Validate configuration version format
        if not self._is_valid_version(self.configuration_version):
            raise ValueError("configuration_version must match supported versions")

        # Validate setup_completed_at logic
        if self.is_configured and self.setup_completed_at is None:
            raise ValueError("setup_completed_at only set when is_configured=True")

        if not self.is_configured and self.setup_completed_at is not None:
            raise ValueError("setup_completed_at only set when is_configured=True")

        return self

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string follows valid format."""
        # Support semantic versioning patterns: X.Y, X.Y.Z, X.Y.Z-suffix
        pattern = r'^(\d+\.){1,2}\d+(-[a-zA-Z0-9]+)?$'
        return bool(re.match(pattern, version))

    def is_ready(self) -> bool:
        """Check if entity is fully configured and ready to use."""
        return self.is_configured and not self.needs_migration

    def needs_setup(self) -> bool:
        """Check if entity needs setup or migration."""
        return not self.is_configured or self.needs_migration

    model_config = {}