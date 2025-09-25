"""ProgressTracker model with ProgressStep and StepStatus for setup wizard."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class StepStatus(Enum):
    PENDING = "pending"      # ⏳
    RUNNING = "running"      # ⚠
    COMPLETED = "completed"  # ✓
    FAILED = "failed"        # ✗
    RETRYING = "retrying"    # 🔄


class ProgressStep(BaseModel):
    """Individual progress step in setup wizard"""
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    status: StepStatus = Field(..., description="Current step status")
    start_time: Optional[datetime] = Field(None, description="Step start time")
    end_time: Optional[datetime] = Field(None, description="Step completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    def get_duration_seconds(self) -> float:
        """Get step duration in seconds"""
        if not self.start_time:
            return 0.0
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()


class ProgressTracker(BaseModel):
    """Real-time progress tracking with step-by-step status"""
    model_config = ConfigDict(str_strip_whitespace=True)

    steps: List[ProgressStep] = Field(default_factory=list, description="List of progress steps")
    total_steps: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(default=0, description="Number of completed steps")
    current_step: Optional[str] = Field(None, description="Current step ID")
    start_time: datetime = Field(default_factory=datetime.now, description="Overall start time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

    def add_step(self, step_id: str, name: str) -> None:
        """Add a new progress step"""
        step = ProgressStep(id=step_id, name=name, status=StepStatus.PENDING)
        self.steps.append(step)

    def start_step(self, step_id: str) -> None:
        """Start a specific step"""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.RUNNING
                step.start_time = datetime.now()
                self.current_step = step_id
                break

    def complete_step(self, step_id: str) -> None:
        """Mark step as completed"""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                step.end_time = datetime.now()
                self.completed_steps += 1
                break

    def fail_step(self, step_id: str, error_message: str) -> None:
        """Mark step as failed"""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.FAILED
                step.error_message = error_message
                step.end_time = datetime.now()
                break