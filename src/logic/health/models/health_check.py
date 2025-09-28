"""Health check entity model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator

from .status import HealthStatus
from .category import HealthCategory


class HealthCheck(BaseModel):
    """Represents an individual validation operation with status and resolution guidance."""

    id: str = Field(..., description="Unique identifier for the health check")
    category: HealthCategory = Field(..., description="Category of the health check")
    name: str = Field(..., min_length=1, description="Human-readable name of the check")
    status: HealthStatus = Field(..., description="Current status of the check")
    message: str = Field(..., description="Descriptive message about the check result")
    details: Optional[str] = Field(None, description="Additional details or error information")
    resolution: Optional[str] = Field(None, description="Actionable guidance for resolving issues")
    execution_time: float = Field(..., ge=0, description="Time taken to execute the check (seconds)")

    @validator('id')
    def validate_id_format(cls, v):
        """Validate ID format follows category.check_name pattern."""
        if not v or '.' not in v:
            raise ValueError("Health check ID must follow 'category.check_name' format")
        return v

    @validator('name')
    def validate_name_not_empty(cls, v):
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("Health check name cannot be empty")
        return v.strip()

    @validator('resolution')
    def validate_resolution_required_for_issues(cls, v, values):
        """Validate resolution is provided when status indicates issues."""
        status = values.get('status')
        if status and status in [HealthStatus.ERROR, HealthStatus.WARNING] and not v:
            raise ValueError("Resolution guidance required for ERROR or WARNING status")
        return v

    @property
    def has_issues(self) -> bool:
        """Check if this health check has issues."""
        return self.status in [HealthStatus.ERROR, HealthStatus.WARNING, HealthStatus.UNAVAILABLE]

    @property
    def is_successful(self) -> bool:
        """Check if this health check was successful."""
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "category": self.category.value,
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "resolution": self.resolution,
            "execution_time": self.execution_time
        }

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HealthStatus: lambda v: v.value,
            HealthCategory: lambda v: v.value,
        }