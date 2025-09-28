"""
CompletionSummary model for final results display
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import CompletionStatus


class CompletionSummary(BaseModel):
    """Final results display without progress elements"""

    project_name: str = Field(..., min_length=1, description="Completed project identifier")
    operation_type: str = Field(..., min_length=1, description="Type of completed operation")
    duration: float = Field(..., ge=0.0, description="Total operation time in seconds")
    success_metrics: dict[str, Any] = Field(..., description="Final counts and statistics")
    status: CompletionStatus = Field(..., description="Final operation status")

    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v):
        """Validate project name contains only valid characters"""
        if not all(c.isalnum() or c in '-_.' for c in v):
            raise ValueError("Project name must contain only alphanumeric characters, hyphens, underscores, and dots")
        return v

    @field_validator('success_metrics')
    @classmethod
    def validate_success_metrics(cls, v):
        """Ensure metrics contain relevant counts and are serializable"""
        try:
            import json
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Success metrics must be JSON serializable: {e}")

        # Ensure at least some basic metrics are present
        expected_keys = {'pages_crawled', 'pages_failed', 'documents_indexed', 'chunks_created'}
        if not any(key in v for key in expected_keys):
            raise ValueError("Success metrics should contain relevant operation counts")

        return v

    @field_validator('status')
    @classmethod
    def validate_terminal_status(cls, v):
        """Ensure status is a terminal state"""
        # All CompletionStatus values are terminal states by definition
        return v

    def get_success_rate(self) -> float:
        """Calculate success rate from metrics"""
        pages_crawled = self.success_metrics.get('pages_crawled', 0)
        pages_failed = self.success_metrics.get('pages_failed', 0)

        if pages_crawled == 0:
            return 0.0

        return ((pages_crawled - pages_failed) / pages_crawled) * 100.0

    def format_duration(self) -> str:
        """Format duration for display"""
        if self.duration < 60:
            return f"{self.duration:.1f}s"
        elif self.duration < 3600:
            minutes = int(self.duration // 60)
            seconds = self.duration % 60
            return f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(self.duration // 3600)
            minutes = int((self.duration % 3600) // 60)
            return f"{hours}h {minutes}m"

    def get_status_emoji(self) -> str:
        """Get emoji representation of status"""
        emoji_map = {
            CompletionStatus.SUCCESS: "🎉",
            CompletionStatus.PARTIAL_SUCCESS: "⚠️",
            CompletionStatus.FAILURE: "❌"
        }
        return emoji_map.get(self.status, "")

    model_config = ConfigDict(validate_assignment=True)
