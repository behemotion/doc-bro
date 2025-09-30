"""ErrorEntry model for individual crawl errors."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorType(str, Enum):
    """Types of errors that can occur during crawling."""
    NETWORK = "NETWORK"
    PARSE = "PARSE"
    TIMEOUT = "TIMEOUT"
    PERMISSION = "PERMISSION"
    RATE_LIMIT = "RATE_LIMIT"
    VALIDATION = "VALIDATION"
    UNKNOWN = "UNKNOWN"


class ErrorEntry(BaseModel):
    """Individual error record within a crawl report."""

    error_id: str = Field(default_factory=lambda: str(uuid4()))
    url: str = Field(..., min_length=1)
    error_type: ErrorType = Field(default=ErrorType.UNKNOWN)
    error_message: str = Field(..., max_length=500)
    error_code: int | None = Field(default=None, ge=100, le=599)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0, ge=0)
    stacktrace: str | None = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(('http://', 'https://', 'ftp://')):
            raise ValueError(f"Invalid URL format: {v}")
        return v

    @field_validator('error_message')
    @classmethod
    def truncate_message(cls, v: str) -> str:
        """Ensure error message doesn't exceed max length."""
        if len(v) > 500:
            return v[:497] + "..."
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    def is_retryable(self) -> bool:
        """Check if error is retryable.

        Returns:
            True if error type suggests retry might succeed
        """
        retryable_types = {
            ErrorType.NETWORK,
            ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT
        }
        return self.error_type in retryable_types

    def should_retry(self, max_retries: int = 3) -> bool:
        """Check if retry should be attempted.

        Args:
            max_retries: Maximum number of retries allowed

        Returns:
            True if retry should be attempted
        """
        return self.is_retryable() and self.retry_count < max_retries

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1

    def get_severity(self) -> str:
        """Get error severity level.

        Returns:
            Severity level (HIGH, MEDIUM, LOW)
        """
        high_severity = {ErrorType.PERMISSION, ErrorType.VALIDATION}
        medium_severity = {ErrorType.PARSE, ErrorType.RATE_LIMIT}

        if self.error_type in high_severity:
            return "HIGH"
        elif self.error_type in medium_severity:
            return "MEDIUM"
        else:
            return "LOW"

    def to_log_format(self) -> str:
        """Format error for logging.

        Returns:
            Formatted error string
        """
        parts = [
            f"[{self.error_type.value}]",
            f"URL: {self.url}",
            f"Error: {self.error_message}"
        ]

        if self.error_code:
            parts.append(f"Code: {self.error_code}")

        if self.retry_count > 0:
            parts.append(f"Retries: {self.retry_count}")

        return " | ".join(parts)

    model_config = ConfigDict()
