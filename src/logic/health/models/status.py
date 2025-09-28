"""Health status enum model."""

from enum import Enum


class HealthStatus(Enum):
    """Status levels for health checks with severity ordering."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"

    def __lt__(self, other):
        """Define ordering for status aggregation (HEALTHY < WARNING < ERROR < UNAVAILABLE)."""
        if not isinstance(other, HealthStatus):
            return NotImplemented

        # Define severity order for aggregation
        order = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 1,
            HealthStatus.ERROR: 2,
            HealthStatus.UNAVAILABLE: 3
        }

        return order[self] < order[other]

    def __le__(self, other):
        """Less than or equal comparison."""
        return self < other or self == other

    def __gt__(self, other):
        """Greater than comparison."""
        return not self <= other

    def __ge__(self, other):
        """Greater than or equal comparison."""
        return not self < other

    @property
    def is_healthy(self) -> bool:
        """Check if status indicates healthy state."""
        return self == HealthStatus.HEALTHY

    @property
    def is_warning(self) -> bool:
        """Check if status indicates warning state."""
        return self == HealthStatus.WARNING

    @property
    def is_error(self) -> bool:
        """Check if status indicates error state."""
        return self == HealthStatus.ERROR

    @property
    def is_unavailable(self) -> bool:
        """Check if status indicates unavailable state."""
        return self == HealthStatus.UNAVAILABLE

    @property
    def exit_code(self) -> int:
        """Get CLI exit code for this status."""
        exit_codes = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 1,
            HealthStatus.ERROR: 2,
            HealthStatus.UNAVAILABLE: 3
        }
        return exit_codes[self]

    @property
    def symbol(self) -> str:
        """Get visual symbol for this status."""
        symbols = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.ERROR: "❌",
            HealthStatus.UNAVAILABLE: "⭕"
        }
        return symbols[self]
