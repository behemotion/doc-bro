"""SetupSession model for DocBro setup logic.

This model manages the current setup process state, progress tracking, and user interaction context.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import ConfigDict, BaseModel, Field, field_validator, model_validator

from .setup_types import (
    SetupStep,
    SessionStatus,
    SetupStepFailure,
    RollbackPoint,
    get_valid_setup_steps,
    is_step_before
)


class SetupSession(BaseModel):
    """Manages the current setup process state, progress tracking, and user interaction context.

    This model represents an active setup session, tracking progress through individual
    setup steps, handling failures, and maintaining rollback points for error recovery.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique session identifier"
    )
    setup_config_id: UUID = Field(
        description="Reference to SetupConfiguration"
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session start time"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Session completion time"
    )
    current_step: SetupStep = Field(
        default=SetupStep.DETECT_COMPONENTS,
        description="Current step in the setup process"
    )
    total_steps: int = Field(
        default=6,
        description="Total number of steps for progress calculation"
    )
    completed_steps: List[SetupStep] = Field(
        default_factory=list,
        description="Steps that have been completed"
    )
    failed_steps: List[SetupStepFailure] = Field(
        default_factory=list,
        description="Steps that failed with error details"
    )
    user_choices: Dict[str, Any] = Field(
        default_factory=dict,
        description="User selections made during interactive setup"
    )
    progress_percentage: float = Field(
        default=0.0,
        description="Current progress as percentage (0-100)"
    )
    session_status: SessionStatus = Field(
        default=SessionStatus.INITIALIZED,
        description="Overall session status"
    )
    rollback_points: List[RollbackPoint] = Field(
        default_factory=list,
        description="Rollback checkpoints for error recovery"
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: str
        }
    )

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: UUID) -> UUID:
        """Validate session_id is a proper UUID v4."""
        if v.version != 4:
            raise ValueError("session_id must be a UUID v4")
        return v

    @field_validator('setup_config_id')
    @classmethod
    def validate_setup_config_id(cls, v: UUID) -> UUID:
        """Validate setup_config_id is a proper UUID v4."""
        if v.version != 4:
            raise ValueError("setup_config_id must be a UUID v4")
        return v

    @field_validator('progress_percentage')
    @classmethod
    def validate_progress_percentage(cls, v: float) -> float:
        """Validate progress percentage is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("Progress percentage must be between 0 and 100")
        return v

    @field_validator('total_steps')
    @classmethod
    def validate_total_steps(cls, v: int) -> int:
        """Validate total steps is positive."""
        if v <= 0:
            raise ValueError("Total steps must be positive")
        return v

    @model_validator(mode='after')
    def validate_timestamps(self) -> 'SetupSession':
        """Validate timestamp consistency."""
        if self.completed_at is not None:
            if self.started_at > self.completed_at:
                raise ValueError("started_at must be <= completed_at")
        return self

    @model_validator(mode='after')
    def validate_completed_steps_count(self) -> 'SetupSession':
        """Validate completed steps count is reasonable."""
        if len(self.completed_steps) > self.total_steps:
            raise ValueError("Completed steps count cannot exceed total steps")
        return self

    @model_validator(mode='after')
    def validate_session_status(self) -> 'SetupSession':
        """Validate session status transitions are logical."""
        if self.session_status == SessionStatus.COMPLETED and self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)

        if self.session_status == SessionStatus.COMPLETED and len(self.completed_steps) < self.total_steps:
            # Allow completion with fewer steps in case some were skipped
            pass

        return self

    def is_completed(self) -> bool:
        """Check if session is completed."""
        return self.session_status == SessionStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if session has failed."""
        return self.session_status == SessionStatus.FAILED

    def is_running(self) -> bool:
        """Check if session is currently running."""
        return self.session_status == SessionStatus.RUNNING

    def is_paused(self) -> bool:
        """Check if session is paused."""
        return self.session_status == SessionStatus.PAUSED

    def can_be_resumed(self) -> bool:
        """Check if session can be resumed."""
        return self.session_status in {SessionStatus.PAUSED, SessionStatus.INITIALIZED}

    def get_remaining_steps(self) -> List[SetupStep]:
        """Get list of steps that haven't been completed yet."""
        all_steps = get_valid_setup_steps()
        return [step for step in all_steps if step not in self.completed_steps]

    def calculate_progress(self) -> float:
        """Calculate current progress percentage based on completed steps."""
        if self.total_steps == 0:
            return 100.0

        progress = (len(self.completed_steps) / self.total_steps) * 100
        return min(100.0, max(0.0, progress))

    def update_progress(self) -> None:
        """Update progress percentage based on completed steps."""
        self.progress_percentage = self.calculate_progress()

    def start_session(self) -> None:
        """Start the setup session."""
        if self.session_status != SessionStatus.INITIALIZED:
            raise ValueError(f"Cannot start session in status: {self.session_status}")

        self.session_status = SessionStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def pause_session(self) -> None:
        """Pause the setup session."""
        if self.session_status != SessionStatus.RUNNING:
            raise ValueError(f"Cannot pause session in status: {self.session_status}")

        self.session_status = SessionStatus.PAUSED

    def resume_session(self) -> None:
        """Resume the setup session."""
        if not self.can_be_resumed():
            raise ValueError(f"Cannot resume session in status: {self.session_status}")

        self.session_status = SessionStatus.RUNNING

    def complete_session(self) -> None:
        """Mark session as completed."""
        self.session_status = SessionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.progress_percentage = 100.0

    def fail_session(self, error_message: str) -> None:
        """Mark session as failed."""
        self.session_status = SessionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)

        # Add general failure to failed steps if no specific step failure exists
        if not self.failed_steps:
            failure = SetupStepFailure(
                step=self.current_step,
                error_type="general",
                error_message=error_message,
                retry_possible=True
            )
            self.failed_steps.append(failure)

    def cancel_session(self) -> None:
        """Cancel the setup session."""
        self.session_status = SessionStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    def complete_step(self, step: SetupStep) -> None:
        """Mark a step as completed and advance to next step."""
        if step not in self.completed_steps:
            self.completed_steps.append(step)

        # Advance to next step
        remaining_steps = self.get_remaining_steps()
        if remaining_steps:
            self.current_step = remaining_steps[0]

        self.update_progress()

    def fail_step(
        self,
        step: SetupStep,
        error_type: str,
        error_message: str,
        technical_details: Optional[str] = None,
        retry_possible: bool = True,
        suggested_action: Optional[str] = None
    ) -> None:
        """Record a step failure."""
        failure = SetupStepFailure(
            step=step,
            error_type=error_type,
            error_message=error_message,
            technical_details=technical_details,
            retry_possible=retry_possible,
            suggested_action=suggested_action
        )
        self.failed_steps.append(failure)

    def add_rollback_point(
        self,
        step: SetupStep,
        state_data: Dict[str, Any],
        description: str
    ) -> None:
        """Add a rollback checkpoint."""
        rollback_point = RollbackPoint(
            step=step,
            timestamp=datetime.now(timezone.utc),
            state_data=state_data,
            description=description
        )
        self.rollback_points.append(rollback_point)

    def get_latest_rollback_point(self) -> Optional[RollbackPoint]:
        """Get the most recent rollback point."""
        if not self.rollback_points:
            return None
        return max(self.rollback_points, key=lambda rp: rp.timestamp)

    def record_user_choice(self, key: str, value: Any) -> None:
        """Record a user choice made during interactive setup."""
        self.user_choices[key] = value

    def get_user_choice(self, key: str, default: Any = None) -> Any:
        """Get a previously recorded user choice."""
        return self.user_choices.get(key, default)

    def get_failed_step_by_type(self, step: SetupStep) -> Optional[SetupStepFailure]:
        """Get the most recent failure for a specific step."""
        failures_for_step = [f for f in self.failed_steps if f.step == step]
        if not failures_for_step:
            return None
        return failures_for_step[-1]  # Most recent failure

    def has_retryable_failures(self) -> bool:
        """Check if there are any retryable step failures."""
        return any(failure.retry_possible for failure in self.failed_steps)

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the session state."""
        return {
            "session_id": str(self.session_id),
            "setup_config_id": str(self.setup_config_id),
            "status": self.session_status,
            "current_step": self.current_step,
            "progress_percentage": self.progress_percentage,
            "completed_steps_count": len(self.completed_steps),
            "total_steps": self.total_steps,
            "failed_steps_count": len(self.failed_steps),
            "rollback_points_count": len(self.rollback_points),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "has_retryable_failures": self.has_retryable_failures(),
            "can_be_resumed": self.can_be_resumed()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: dict) -> 'SetupSession':
        """Create instance from dictionary."""
        return cls(**data)