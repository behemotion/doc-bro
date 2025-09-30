"""CrawlReport model for tracking crawl operation results."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.error import ErrorEntry


class CrawlStatus(str, Enum):
    """Status of a crawl operation."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"


class CrawlReport(BaseModel):
    """Represents a complete crawl operation report for a project."""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    project_name: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: CrawlStatus = Field(default=CrawlStatus.PENDING)
    total_pages: int = Field(default=0, ge=0)
    successful_pages: int = Field(default=0, ge=0)
    failed_pages: int = Field(default=0, ge=0)
    embeddings_count: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    errors: list[ErrorEntry] = Field(default_factory=list)
    report_path: str | None = None

    @field_validator('failed_pages')
    @classmethod
    def validate_failed_pages(cls, v: int, info) -> int:
        """Validate that failed_pages + successful_pages <= total_pages."""
        if 'successful_pages' in info.data and 'total_pages' in info.data:
            if v + info.data['successful_pages'] > info.data['total_pages']:
                raise ValueError(
                    f"Sum of failed ({v}) and successful ({info.data['successful_pages']}) "
                    f"pages cannot exceed total pages ({info.data['total_pages']})"
                )
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            # Assume UTC if no timezone
            return v.replace(tzinfo=UTC)
        return v

    def add_error(self, error: ErrorEntry) -> None:
        """Add an error entry to the report.

        Args:
            error: Error entry to add
        """
        self.errors.append(error)
        self.failed_pages += 1

    def mark_success(self) -> None:
        """Mark a page as successfully processed."""
        self.successful_pages += 1

    def update_status(self) -> None:
        """Update status based on current statistics."""
        if self.failed_pages == 0 and self.successful_pages > 0:
            self.status = CrawlStatus.SUCCESS
        elif self.successful_pages > 0:
            self.status = CrawlStatus.PARTIAL
        elif self.failed_pages > 0 and self.successful_pages == 0:
            self.status = CrawlStatus.FAILED
        else:
            self.status = CrawlStatus.IN_PROGRESS

    def get_success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Success rate (0-100)
        """
        if self.total_pages == 0:
            return 0.0
        return (self.successful_pages / self.total_pages) * 100

    def get_error_summary(self) -> dict:
        """Generate error summary statistics.

        Returns:
            Dictionary with error statistics
        """
        if not self.errors:
            return {"total_errors": 0}

        error_types = {}
        for error in self.errors:
            error_type = error.error_type
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": len(self.errors),
            "by_type": error_types,
            "unique_urls": len(set(e.url for e in self.errors))
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "report_id": self.report_id,
            "project_name": self.project_name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "total_pages": self.total_pages,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages,
            "embeddings_count": self.embeddings_count,
            "duration_seconds": self.duration_seconds,
            "errors": [e.model_dump() for e in self.errors],
            "report_path": self.report_path,
            "success_rate": self.get_success_rate(),
            "error_summary": self.get_error_summary()
        }

    model_config = ConfigDict()
