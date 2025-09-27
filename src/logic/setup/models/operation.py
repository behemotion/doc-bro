"""Setup operation model and related enums."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Set
from pydantic import BaseModel, Field, field_validator


class OperationType(str, Enum):
    """Types of setup operations."""

    INIT = "init"
    SETUP = "setup"
    UNINSTALL = "uninstall"
    RESET = "reset"
    MENU = "menu"


class OperationStatus(str, Enum):
    """Status of a setup operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SetupOperation(BaseModel):
    """Represents a specific setup action that can be performed."""

    operation_type: OperationType = Field(
        description="Type of operation being performed"
    )
    flags: Set[str] = Field(
        default_factory=set,
        description="Command line flags provided"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When operation started (UTC)"
    )
    status: OperationStatus = Field(
        default=OperationStatus.PENDING,
        description="Current status of the operation"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if operation failed"
    )
    user_selections: Dict[str, Any] = Field(
        default_factory=dict,
        description="Choices made during operation"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_utc_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is UTC."""
        if v.tzinfo is not None and v.tzinfo.utcoffset(None) is not None:
            # Convert to UTC if timezone aware
            return v.astimezone(tz=None).replace(tzinfo=None)
        return v

    @field_validator("flags")
    @classmethod
    def validate_flag_conflicts(cls, v: Set[str], info) -> Set[str]:
        """Validate that conflicting flags are not present."""
        operation_flags = {"init", "uninstall", "reset"}
        present_ops = v & operation_flags

        if len(present_ops) > 1:
            raise ValueError(
                f"Conflicting operation flags: {', '.join(present_ops)}. "
                "Only one operation flag can be specified."
            )

        # Validate flag dependencies
        if "vector-store" in v and "init" not in v:
            raise ValueError("--vector-store requires --init flag")

        if "auto" in v and not (present_ops or "menu" in v):
            raise ValueError("--auto requires an operation flag")

        if "non-interactive" in v and not present_ops:
            raise ValueError("--non-interactive requires an operation flag")

        return v

    def transition_to(self, new_status: OperationStatus, error: Optional[str] = None) -> None:
        """Transition to a new status with validation."""
        # Define valid transitions
        valid_transitions = {
            OperationStatus.PENDING: [
                OperationStatus.IN_PROGRESS,
                OperationStatus.CANCELLED
            ],
            OperationStatus.IN_PROGRESS: [
                OperationStatus.COMPLETED,
                OperationStatus.FAILED,
                OperationStatus.CANCELLED
            ],
            OperationStatus.COMPLETED: [],  # Terminal state
            OperationStatus.FAILED: [],  # Terminal state
            OperationStatus.CANCELLED: [],  # Terminal state
        }

        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(
                f"Invalid transition from {self.status} to {new_status}"
            )

        self.status = new_status

        if new_status == OperationStatus.FAILED and error:
            self.error_message = error

    def is_terminal(self) -> bool:
        """Check if operation is in a terminal state."""
        return self.status in [
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED
        ]

    def add_selection(self, key: str, value: Any) -> None:
        """Add a user selection to the operation."""
        self.user_selections[key] = value

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }