"""Health summary aggregation model."""

from typing import List
from pydantic import BaseModel, Field, computed_field

from .health_check import HealthCheck
from .status import HealthStatus


class HealthSummary(BaseModel):
    """Statistical summary of health check results."""

    total_checks: int = Field(..., ge=0, description="Total number of health checks performed")
    healthy_count: int = Field(..., ge=0, description="Number of HEALTHY checks")
    warning_count: int = Field(..., ge=0, description="Number of WARNING checks")
    error_count: int = Field(..., ge=0, description="Number of ERROR checks")
    unavailable_count: int = Field(..., ge=0, description="Number of UNAVAILABLE checks")

    @computed_field
    @property
    def success_rate(self) -> float:
        """Percentage of HEALTHY checks."""
        if self.total_checks == 0:
            return 0.0
        return (self.healthy_count / self.total_checks) * 100

    @computed_field
    @property
    def issue_rate(self) -> float:
        """Percentage of WARNING + ERROR checks."""
        if self.total_checks == 0:
            return 0.0
        return ((self.warning_count + self.error_count) / self.total_checks) * 100

    @classmethod
    def from_health_checks(cls, checks: List[HealthCheck]) -> 'HealthSummary':
        """Create summary from list of health checks."""
        total = len(checks)
        healthy = sum(1 for check in checks if check.status == HealthStatus.HEALTHY)
        warning = sum(1 for check in checks if check.status == HealthStatus.WARNING)
        error = sum(1 for check in checks if check.status == HealthStatus.ERROR)
        unavailable = sum(1 for check in checks if check.status == HealthStatus.UNAVAILABLE)

        return cls(
            total_checks=total,
            healthy_count=healthy,
            warning_count=warning,
            error_count=error,
            unavailable_count=unavailable
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_checks": self.total_checks,
            "healthy_count": self.healthy_count,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "unavailable_count": self.unavailable_count,
            "success_rate": self.success_rate,
            "issue_rate": self.issue_rate
        }