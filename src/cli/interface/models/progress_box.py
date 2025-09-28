"""
ProgressBox model for CLI progress display
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ProgressBox(BaseModel):
    """Visual container for operation progress with borders and metrics"""

    title: str = Field(..., min_length=1, description="Operation title")
    project_name: str = Field(..., min_length=1, description="Target project identifier")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Dynamic progress metrics")
    current_operation: str = Field(default="", description="Current activity description")
    border_style: str = Field(default="rounded", description="Box border styling")
    width: int = Field(default=80, ge=40, description="Box width in characters")

    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v):
        """Validate project name contains only valid characters"""
        if not all(c.isalnum() or c in '-_.' for c in v):
            raise ValueError("Project name must contain only alphanumeric characters, hyphens, underscores, and dots")
        return v

    @field_validator('metrics')
    @classmethod
    def validate_metrics_serializable(cls, v):
        """Ensure all metric values are JSON serializable"""
        try:
            import json
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Metrics must be JSON serializable: {e}")
        return v

    def truncate_current_operation(self, max_length: int) -> str:
        """Truncate current operation text to fit available width"""
        if len(self.current_operation) <= max_length:
            return self.current_operation

        if max_length <= 3:
            return "..."

        # Use middle truncation to preserve start and end
        start_len = (max_length - 3) // 2
        end_len = max_length - 3 - start_len

        return f"{self.current_operation[:start_len]}...{self.current_operation[-end_len:]}"

    model_config = ConfigDict(validate_assignment=True)