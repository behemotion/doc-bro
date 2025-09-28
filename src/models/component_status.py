"""ComponentStatus model for tracking component removal status."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Type of component to be removed."""
    CONTAINER = "container"
    VOLUME = "volume"
    DIRECTORY = "directory"
    PACKAGE = "package"
    CONFIG = "config"


class RemovalStatus(str, Enum):
    """Status of component removal."""
    PENDING = "pending"
    REMOVING = "removing"
    REMOVED = "removed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ComponentStatus(BaseModel):
    """Tracks the status of each component to be removed."""

    component_type: ComponentType = Field(
        description="Type of component"
    )
    component_name: str = Field(
        description="Identifier for the component"
    )
    component_path: Path | None = Field(
        default=None,
        description="File system path if applicable"
    )
    size_bytes: int | None = Field(
        default=None,
        description="Size of component if known"
    )
    status: RemovalStatus = Field(
        default=RemovalStatus.PENDING,
        description="Current status of the component"
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if failed"
    )
    is_external: bool = Field(
        default=False,
        description="Whether component is external (should preserve)"
    )

    def transition_to(self, new_status: RemovalStatus) -> None:
        """Transition to a new status with validation."""
        valid_transitions = {
            RemovalStatus.PENDING: [
                RemovalStatus.REMOVING,
                RemovalStatus.SKIPPED
            ],
            RemovalStatus.REMOVING: [
                RemovalStatus.REMOVED,
                RemovalStatus.FAILED
            ],
            RemovalStatus.REMOVED: [],  # Terminal state
            RemovalStatus.FAILED: [],    # Terminal state
            RemovalStatus.SKIPPED: []    # Terminal state
        }

        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(
                f"Invalid status transition from {self.status} to {new_status}"
            )

        self.status = new_status

    def mark_as_removing(self) -> None:
        """Mark component as being removed."""
        self.transition_to(RemovalStatus.REMOVING)

    def mark_as_removed(self) -> None:
        """Mark component as successfully removed."""
        self.transition_to(RemovalStatus.REMOVED)

    def mark_as_failed(self, error_message: str) -> None:
        """Mark component as failed with error message."""
        self.transition_to(RemovalStatus.FAILED)
        self.error_message = error_message

    def mark_as_skipped(self, reason: str | None = None) -> None:
        """Mark component as skipped."""
        self.transition_to(RemovalStatus.SKIPPED)
        if reason:
            self.error_message = f"Skipped: {reason}"

    @property
    def is_terminal(self) -> bool:
        """Check if component is in a terminal state."""
        return self.status in [
            RemovalStatus.REMOVED,
            RemovalStatus.FAILED,
            RemovalStatus.SKIPPED
        ]

    @property
    def display_name(self) -> str:
        """Get display name for the component."""
        if self.component_path:
            return str(self.component_path)
        return self.component_name

    @property
    def size_display(self) -> str:
        """Get human-readable size display."""
        if self.size_bytes is None:
            return "unknown size"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.size_bytes < 1024.0:
                return f"{self.size_bytes:.1f} {unit}"
            self.size_bytes /= 1024.0
        return f"{self.size_bytes:.1f} PB"

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        use_enum_values = True
