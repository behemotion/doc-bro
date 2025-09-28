"""Health report entity model."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, validator

from .health_check import HealthCheck
from .health_summary import HealthSummary
from .status import HealthStatus


class HealthReport(BaseModel):
    """Overall health state combining all individual health check results."""

    timestamp: datetime = Field(..., description="When the health report was generated")
    overall_status: HealthStatus = Field(..., description="Aggregated status across all checks")
    checks: List[HealthCheck] = Field(..., min_items=1, description="List of individual health check results")
    total_execution_time: float = Field(..., le=15.0, description="Total time for all health checks")
    timeout_occurred: bool = Field(..., description="Whether any checks timed out")
    summary: HealthSummary = Field(..., description="Aggregated count statistics")

    @validator('checks')
    def validate_checks_not_empty(cls, v):
        """Validate checks list is not empty."""
        if not v:
            raise ValueError("Health report must contain at least one health check")
        return v

    @validator('total_execution_time')
    def validate_execution_time_limit(cls, v):
        """Validate total execution time does not exceed 15 seconds."""
        if v > 15.0:
            raise ValueError("Total execution time must not exceed 15 seconds")
        return v

    @validator('overall_status')
    def validate_overall_status_derivation(cls, v, values):
        """Validate overall status is correctly derived from individual checks."""
        checks = values.get('checks', [])
        if not checks:
            return v

        # Find the worst status among all checks
        worst_status = HealthStatus.HEALTHY
        for check in checks:
            if check.status > worst_status:
                worst_status = check.status

        if v != worst_status:
            raise ValueError("Overall status must be derived from worst individual check status")

        return v

    @validator('summary')
    def validate_summary_matches_checks(cls, v, values):
        """Validate summary counts match the actual checks."""
        checks = values.get('checks', [])
        if not checks:
            return v

        expected_summary = HealthSummary.from_health_checks(checks)

        if (v.total_checks != expected_summary.total_checks or
            v.healthy_count != expected_summary.healthy_count or
            v.warning_count != expected_summary.warning_count or
            v.error_count != expected_summary.error_count or
            v.unavailable_count != expected_summary.unavailable_count):
            raise ValueError("Summary statistics must match actual health check counts")

        return v

    @classmethod
    def create_from_checks(cls, checks: List[HealthCheck], execution_time: float,
                          timeout_occurred: bool = False) -> 'HealthReport':
        """Create health report from list of health checks."""
        if not checks:
            raise ValueError("Cannot create health report without checks")

        # Calculate overall status (worst status among all checks)
        overall_status = HealthStatus.HEALTHY
        for check in checks:
            if check.status > overall_status:
                overall_status = check.status

        # Generate summary
        summary = HealthSummary.from_health_checks(checks)

        return cls(
            timestamp=datetime.now(),
            overall_status=overall_status,
            checks=checks,
            total_execution_time=execution_time,
            timeout_occurred=timeout_occurred,
            summary=summary
        )

    @property
    def exit_code(self) -> int:
        """Get CLI exit code based on overall status."""
        return self.overall_status.exit_code

    @property
    def has_issues(self) -> bool:
        """Check if this report indicates any issues."""
        return self.overall_status != HealthStatus.HEALTHY

    @property
    def is_healthy(self) -> bool:
        """Check if this report indicates healthy state."""
        return self.overall_status == HealthStatus.HEALTHY

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "execution_time": self.total_execution_time,
            "timeout_occurred": self.timeout_occurred,
            "summary": self.summary.to_dict(),
            "checks": [check.to_dict() for check in self.checks]
        }

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HealthStatus: lambda v: v.value,
        }