"""RetryPolicy model with exponential backoff logic (2s, 4s, 8s)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Type, List, Optional
from pydantic import BaseModel, Field, ConfigDict


@dataclass
class RetryState:
    """State tracking for retry attempts"""
    attempt_number: int
    next_delay_seconds: float
    last_error: Optional[Exception] = None
    started_at: Optional[float] = None


class RetryPolicy(BaseModel):
    """Retry policy with exponential backoff for setup wizard"""
    model_config = ConfigDict(str_strip_whitespace=True)

    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    base_delay_seconds: float = Field(default=2.0, description="Base delay in seconds")
    max_delay_seconds: float = Field(default=8.0, description="Maximum delay in seconds")
    backoff_multiplier: float = Field(default=2.0, description="Backoff multiplier")
    retryable_errors: List[str] = Field(
        default_factory=lambda: ["ConnectionError", "TimeoutError", "OSError"],
        description="List of retryable error class names"
    )

    def should_retry(self, error: Exception, attempt_number: int) -> bool:
        """Determine if error should be retried based on attempt number"""
        # Don't retry after max attempts
        if attempt_number >= self.max_attempts:
            return False

        # Check if error type is retryable
        return self.is_retryable_error(error)

    def get_delay_seconds(self, attempt_number: int) -> float:
        """Get delay for attempt number (1-based): must be 2s, 4s, 8s"""
        if attempt_number <= 0:
            raise ValueError("attempt_number must be >= 1")

        # FR-012 clarification: exact sequence 2s, 4s, 8s
        delays = [2.0, 4.0, 8.0]

        if attempt_number <= len(delays):
            return delays[attempt_number - 1]
        else:
            # Beyond max, return max delay
            return self.max_delay_seconds

    def get_max_attempts(self) -> int:
        """Get maximum number of retry attempts (must be 3)"""
        return self.max_attempts

    def is_retryable_error(self, error: Exception) -> bool:
        """Check if error type should be retried"""
        error_class_name = type(error).__name__
        return error_class_name in self.retryable_errors