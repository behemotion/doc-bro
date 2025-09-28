"""RemovalOperation model for queuing removal operations."""

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Type of removal operation."""
    STOP_CONTAINER = "stop_container"
    REMOVE_CONTAINER = "remove_container"
    REMOVE_VOLUME = "remove_volume"
    DELETE_DIRECTORY = "delete_directory"
    UNINSTALL_PACKAGE = "uninstall_package"
    DELETE_CONFIG = "delete_config"


class RemovalOperation(BaseModel):
    """Represents a single removal operation in the queue."""

    operation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier"
    )
    operation_type: OperationType = Field(
        description="Type of removal operation"
    )
    target: str = Field(
        description="What to remove (container ID, path, package name)"
    )
    priority: int = Field(
        description="Execution order (lower = higher priority)"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Other operation IDs that must complete first"
    )
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retries allowed"
    )
    error_message: str | None = Field(
        default=None,
        description="Last error message if failed"
    )

    @classmethod
    def create_stop_container(cls, container_id: str, container_name: str) -> "RemovalOperation":
        """Create operation to stop a container."""
        return cls(
            operation_type=OperationType.STOP_CONTAINER,
            target=container_id,
            priority=10  # Highest priority - stop first
        )

    @classmethod
    def create_remove_container(cls, container_id: str, depends_on: str | None = None) -> "RemovalOperation":
        """Create operation to remove a container."""
        dependencies = [depends_on] if depends_on else []
        return cls(
            operation_type=OperationType.REMOVE_CONTAINER,
            target=container_id,
            priority=20,
            dependencies=dependencies
        )

    @classmethod
    def create_remove_volume(cls, volume_name: str) -> "RemovalOperation":
        """Create operation to remove a volume."""
        return cls(
            operation_type=OperationType.REMOVE_VOLUME,
            target=volume_name,
            priority=30
        )

    @classmethod
    def create_delete_directory(cls, directory_path: str) -> "RemovalOperation":
        """Create operation to delete a directory."""
        return cls(
            operation_type=OperationType.DELETE_DIRECTORY,
            target=directory_path,
            priority=40
        )

    @classmethod
    def create_uninstall_package(cls, package_name: str) -> "RemovalOperation":
        """Create operation to uninstall a package."""
        return cls(
            operation_type=OperationType.UNINSTALL_PACKAGE,
            target=package_name,
            priority=50  # Lowest priority - uninstall last
        )

    @classmethod
    def create_delete_config(cls, config_path: str) -> "RemovalOperation":
        """Create operation to delete a configuration file."""
        return cls(
            operation_type=OperationType.DELETE_CONFIG,
            target=config_path,
            priority=35  # After volumes but before directories
        )

    @property
    def can_retry(self) -> bool:
        """Check if operation can be retried."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1

    def mark_failed(self, error: str) -> None:
        """Mark operation as failed with error."""
        self.error_message = error

    @property
    def is_container_operation(self) -> bool:
        """Check if this is a container-related operation."""
        return self.operation_type in [
            OperationType.STOP_CONTAINER,
            OperationType.REMOVE_CONTAINER
        ]

    @property
    def is_filesystem_operation(self) -> bool:
        """Check if this is a filesystem operation."""
        return self.operation_type in [
            OperationType.DELETE_DIRECTORY,
            OperationType.DELETE_CONFIG
        ]

    @property
    def requires_docker(self) -> bool:
        """Check if operation requires Docker."""
        return self.operation_type in [
            OperationType.STOP_CONTAINER,
            OperationType.REMOVE_CONTAINER,
            OperationType.REMOVE_VOLUME
        ]

    def get_display_name(self) -> str:
        """Get human-readable operation description."""
        type_display = {
            OperationType.STOP_CONTAINER: "Stopping container",
            OperationType.REMOVE_CONTAINER: "Removing container",
            OperationType.REMOVE_VOLUME: "Removing volume",
            OperationType.DELETE_DIRECTORY: "Deleting directory",
            OperationType.UNINSTALL_PACKAGE: "Uninstalling package",
            OperationType.DELETE_CONFIG: "Deleting config file"
        }
        return f"{type_display.get(self.operation_type, 'Unknown operation')}: {self.target}"

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        use_enum_values = True
