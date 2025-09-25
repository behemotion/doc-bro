"""ProjectStatus model for tracking documentation project state."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ProjectState(str, Enum):
    """State of a documentation project."""
    READY = "READY"
    CRAWLING = "CRAWLING"
    ERROR = "ERROR"
    UNINITIALIZED = "UNINITIALIZED"
    UPDATING = "UPDATING"


class ProjectStatus(BaseModel):
    """Current state and statistics of a documentation project."""

    project_name: str = Field(..., min_length=1)
    last_crawl_time: Optional[datetime] = None
    total_documents: int = Field(default=0, ge=0)
    total_embeddings: int = Field(default=0, ge=0)
    index_size_mb: float = Field(default=0.0, ge=0.0)
    status: ProjectState = Field(default=ProjectState.UNINITIALIZED)
    last_error: Optional[str] = None
    crawl_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    url: Optional[str] = None
    crawl_depth: int = Field(default=2, ge=1, le=10)
    model: str = Field(default="mxbai-embed-large")

    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        """Validate project name format."""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Project name must contain only letters, numbers, hyphens, and underscores"
            )
        return v

    @field_validator('last_crawl_time', 'created_at', 'updated_at')
    @classmethod
    def validate_timestamps(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure timestamps are UTC."""
        if v and v.tzinfo is None:
            from datetime import timezone
            return v.replace(tzinfo=timezone.utc)
        return v

    def increment_crawl(self) -> None:
        """Increment crawl count and update timestamp."""
        self.crawl_count += 1
        self.last_crawl_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_crawling(self) -> None:
        """Mark project as currently crawling."""
        self.status = ProjectState.CRAWLING
        self.last_error = None
        self.updated_at = datetime.utcnow()

    def mark_ready(self) -> None:
        """Mark project as ready."""
        self.status = ProjectState.READY
        self.last_error = None
        self.updated_at = datetime.utcnow()

    def mark_error(self, error_message: str) -> None:
        """Mark project as having an error.

        Args:
            error_message: Error description
        """
        self.status = ProjectState.ERROR
        self.last_error = error_message[:500]  # Limit error message length
        self.updated_at = datetime.utcnow()

    def update_statistics(
        self,
        documents: Optional[int] = None,
        embeddings: Optional[int] = None,
        index_size: Optional[float] = None
    ) -> None:
        """Update project statistics.

        Args:
            documents: Total document count
            embeddings: Total embedding count
            index_size: Index size in MB
        """
        if documents is not None:
            self.total_documents = documents
        if embeddings is not None:
            self.total_embeddings = embeddings
        if index_size is not None:
            self.index_size_mb = index_size
        self.updated_at = datetime.utcnow()

    def needs_crawl(self, max_age_hours: int = 24) -> bool:
        """Check if project needs re-crawling.

        Args:
            max_age_hours: Maximum age in hours before re-crawl needed

        Returns:
            True if crawl is needed
        """
        if self.status == ProjectState.UNINITIALIZED:
            return True

        if self.last_crawl_time is None:
            return True

        from datetime import timedelta
        age = datetime.utcnow() - self.last_crawl_time
        return age > timedelta(hours=max_age_hours)

    def get_health_status(self) -> str:
        """Get health status of the project.

        Returns:
            Health status (HEALTHY, WARNING, CRITICAL)
        """
        if self.status == ProjectState.ERROR:
            return "CRITICAL"
        elif self.status == ProjectState.UNINITIALIZED:
            return "WARNING"
        elif self.total_documents == 0:
            return "WARNING"
        elif self.needs_crawl(max_age_hours=7*24):  # Week old
            return "WARNING"
        else:
            return "HEALTHY"

    def to_summary(self) -> dict:
        """Generate summary for display.

        Returns:
            Summary dictionary
        """
        return {
            "name": self.project_name,
            "status": self.status.value,
            "health": self.get_health_status(),
            "documents": self.total_documents,
            "embeddings": self.total_embeddings,
            "last_crawl": self.last_crawl_time.isoformat() if self.last_crawl_time else None,
            "crawl_count": self.crawl_count,
            "index_size_mb": round(self.index_size_mb, 2)
        }

    class Config:
        """Pydantic configuration."""
        use_enum_values = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }