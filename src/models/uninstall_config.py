"""UninstallConfig model for uninstall operation configuration."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UninstallConfig(BaseModel):
    """Configuration for an uninstall operation."""

    force: bool = Field(
        default=False,
        description="Skip all confirmation prompts"
    )
    backup: bool = Field(
        default=False,
        description="Create backup before removal"
    )
    backup_path: Optional[Path] = Field(
        default=None,
        description="Path where backup will be created"
    )
    verbose: bool = Field(
        default=False,
        description="Show detailed progress information"
    )
    dry_run: bool = Field(
        default=False,
        description="Show what would be removed without removing"
    )

    @field_validator('backup_path')
    def validate_backup_path(cls, v: Optional[Path], values) -> Optional[Path]:
        """Validate backup path if backup is enabled."""
        # Note: In Pydantic v2, we get values as a dict-like object
        if v is not None:
            # Check if parent directory exists and is writable
            parent = v.parent
            if not parent.exists():
                raise ValueError(f"Parent directory does not exist: {parent}")
            if not parent.is_dir():
                raise ValueError(f"Parent path is not a directory: {parent}")
            # Note: Actual write permission check would be done at runtime
            # to avoid side effects during validation
        return v

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        str_strip_whitespace = True