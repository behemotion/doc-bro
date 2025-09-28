"""UninstallProgress model for tracking overall uninstall progress."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class UninstallProgress(BaseModel):
    """Tracks overall progress of uninstall operation."""

    total_components: int = Field(
        default=0,
        description="Total number of components to process"
    )
    processed_components: int = Field(
        default=0,
        description="Number of components processed"
    )
    removed_components: int = Field(
        default=0,
        description="Successfully removed"
    )
    failed_components: int = Field(
        default=0,
        description="Failed to remove"
    )
    skipped_components: int = Field(
        default=0,
        description="Skipped (external/not found)"
    )
    start_time: datetime = Field(
        default_factory=datetime.now,
        description="When uninstall started"
    )
    end_time: datetime | None = Field(
        default=None,
        description="When uninstall completed"
    )
    backup_created: bool = Field(
        default=False,
        description="Whether backup was successfully created"
    )
    backup_location: Path | None = Field(
        default=None,
        description="Where backup was saved"
    )

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Check if all components have been processed."""
        return self.processed_components >= self.total_components

    @computed_field
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.processed_components == 0:
            return 0.0
        return (self.removed_components / self.processed_components) * 100

    @computed_field
    @property
    def has_failures(self) -> bool:
        """Check if there were any failures."""
        return self.failed_components > 0

    @computed_field
    @property
    def is_partial_success(self) -> bool:
        """Check if operation was partially successful."""
        return self.removed_components > 0 and self.failed_components > 0

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        """Calculate operation duration in seconds."""
        if self.end_time is None:
            # If still running, calculate from start to now
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    def increment_processed(self) -> None:
        """Increment the processed components counter."""
        self.processed_components += 1

    def increment_removed(self) -> None:
        """Increment the removed components counter."""
        self.removed_components += 1
        self.increment_processed()

    def increment_failed(self) -> None:
        """Increment the failed components counter."""
        self.failed_components += 1
        self.increment_processed()

    def increment_skipped(self) -> None:
        """Increment the skipped components counter."""
        self.skipped_components += 1
        self.increment_processed()

    def mark_complete(self) -> None:
        """Mark the uninstall operation as complete."""
        self.end_time = datetime.now()

    def set_backup_info(self, location: Path) -> None:
        """Set backup creation information."""
        self.backup_created = True
        self.backup_location = location

    def get_summary(self) -> dict:
        """Get a summary of the uninstall progress."""
        return {
            "total": self.total_components,
            "removed": self.removed_components,
            "failed": self.failed_components,
            "skipped": self.skipped_components,
            "success_rate": f"{self.success_rate:.1f}%",
            "duration": f"{self.duration_seconds:.1f}s" if self.duration_seconds else "N/A",
            "backup_created": self.backup_created,
            "backup_location": str(self.backup_location) if self.backup_location else None
        }

    def get_exit_code(self) -> int:
        """Determine appropriate exit code based on progress."""
        if self.total_components == 0:
            return 4  # Nothing to uninstall
        elif self.failed_components == 0 and self.removed_components > 0:
            return 0  # Complete success
        elif self.removed_components > 0 and self.failed_components > 0:
            return 1  # Partial success
        elif self.removed_components == 0 and self.failed_components > 0:
            return 3  # Complete failure
        else:
            return 2  # Aborted or unknown state

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
