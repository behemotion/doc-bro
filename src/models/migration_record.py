"""Project migration record model for audit trail."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MigrationOperation(Enum):
    """Types of migration operations."""

    RECREATION = "recreation"  # Complete project recreation
    UPGRADE = "upgrade"        # Schema upgrade (future use)
    VALIDATION = "validation"  # Compatibility validation check

    def __str__(self) -> str:
        """String representation using the enum value."""
        return self.value


class ProjectMigrationRecord(BaseModel):
    """Record of project migration/recreation operations."""

    # Identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Migration record ID")
    project_id: str = Field(..., description="Target project ID")
    project_name: str = Field(..., min_length=1, description="Project name for reference")
    operation: MigrationOperation = Field(..., description="Type of migration operation")

    # Schema information
    from_schema_version: int = Field(..., ge=1, description="Original schema version")
    to_schema_version: int = Field(..., ge=1, description="Target schema version")

    # Operation timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Migration start time")
    completed_at: Optional[datetime] = Field(default=None, description="Migration completion time")
    success: bool = Field(default=False, description="Whether migration succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    # Data preservation
    preserved_settings: dict[str, Any] = Field(default_factory=dict, description="Settings preserved during migration")
    preserved_metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata preserved during migration")
    data_size_bytes: int = Field(default=0, ge=0, description="Size of preserved data")

    # User context
    user_initiated: bool = Field(default=True, description="Whether migration was user-initiated")
    initiated_by_command: str = Field(default="unknown", description="Command that initiated migration")

    def mark_completed(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark migration as completed."""
        self.completed_at = datetime.utcnow()
        self.success = success
        self.error_message = error

    def mark_failed(self, error: str) -> None:
        """Mark migration as failed with error message."""
        self.mark_completed(success=False, error=error)

    @property
    def is_completed(self) -> bool:
        """Whether the migration has completed."""
        return self.completed_at is not None

    @property
    def is_in_progress(self) -> bool:
        """Whether the migration is currently in progress."""
        return self.completed_at is None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Migration duration in seconds if completed."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def is_schema_upgrade(self) -> bool:
        """Whether this is a schema version upgrade."""
        return self.to_schema_version > self.from_schema_version

    @property
    def is_schema_downgrade(self) -> bool:
        """Whether this is a schema version downgrade."""
        return self.to_schema_version < self.from_schema_version

    @property
    def schema_version_change(self) -> int:
        """The change in schema version (positive for upgrade, negative for downgrade)."""
        return self.to_schema_version - self.from_schema_version

    def to_summary(self) -> dict[str, Any]:
        """Get a summary of this migration record."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "operation": self.operation.value,
            "schema_change": f"v{self.from_schema_version} → v{self.to_schema_version}",
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_message": self.error_message,
            "data_size_mb": round(self.data_size_bytes / (1024 * 1024), 2) if self.data_size_bytes > 0 else 0,
            "user_initiated": self.user_initiated,
            "initiated_by_command": self.initiated_by_command
        }

    @classmethod
    def create_recreation_record(
        cls,
        project_id: str,
        project_name: str,
        from_version: int,
        to_version: int,
        preserved_settings: dict[str, Any] = None,
        preserved_metadata: dict[str, Any] = None,
        initiated_by_command: str = "docbro project --recreate"
    ) -> "ProjectMigrationRecord":
        """Create a new recreation record."""
        return cls(
            project_id=project_id,
            project_name=project_name,
            operation=MigrationOperation.RECREATION,
            from_schema_version=from_version,
            to_schema_version=to_version,
            preserved_settings=preserved_settings or {},
            preserved_metadata=preserved_metadata or {},
            initiated_by_command=initiated_by_command
        )

    @classmethod
    def create_validation_record(
        cls,
        project_id: str,
        project_name: str,
        schema_version: int,
        initiated_by_command: str = "docbro project --check-compatibility"
    ) -> "ProjectMigrationRecord":
        """Create a new validation record."""
        return cls(
            project_id=project_id,
            project_name=project_name,
            operation=MigrationOperation.VALIDATION,
            from_schema_version=schema_version,
            to_schema_version=schema_version,  # Same version for validation
            initiated_by_command=initiated_by_command
        )