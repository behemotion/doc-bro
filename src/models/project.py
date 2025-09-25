"""Project data model."""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pathlib import Path


class ProjectStatus(str, Enum):
    """Valid project status values."""
    CREATED = "created"
    CRAWLING = "crawling"
    PROCESSING = "processing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class Project(BaseModel):
    """Project model representing a documentation crawling project."""

    id: str = Field(description="Unique project identifier")
    name: str = Field(description="Human-readable project name")
    source_url: str = Field(description="Base URL to start crawling from")
    status: ProjectStatus = Field(default=ProjectStatus.CREATED, description="Current project status")

    # Crawl configuration
    crawl_depth: int = Field(default=2, ge=1, le=10, description="Maximum crawl depth")
    embedding_model: str = Field(default="mxbai-embed-large", description="Embedding model to use")
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Document chunk size")
    chunk_overlap: int = Field(default=100, ge=0, le=500, description="Chunk overlap size")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_crawl_at: Optional[datetime] = Field(default=None)

    # Statistics
    total_pages: int = Field(default=0, ge=0)
    total_size_bytes: int = Field(default=0, ge=0)
    successful_pages: int = Field(default=0, ge=0)
    failed_pages: int = Field(default=0, ge=0)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate project name."""
        if not v.strip():
            raise ValueError("Project name cannot be empty")
        if len(v) > 100:
            raise ValueError("Project name too long")
        # Only allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError("Project name can only contain letters, numbers, hyphens, and underscores")
        return v.strip()

    @field_validator('source_url')
    @classmethod
    def validate_source_url(cls, v):
        """Validate source URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Source URL must be a valid HTTP/HTTPS URL")
        return v

    @field_validator('chunk_overlap')
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        """Validate chunk overlap is less than chunk size."""
        if info.data.get('chunk_size') and v >= info.data['chunk_size']:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v

    def update_status(self, new_status: ProjectStatus) -> None:
        """Update project status and timestamp."""
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def update_statistics(self, **stats) -> None:
        """Update project statistics."""
        for key, value in stats.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

    def is_ready_for_search(self) -> bool:
        """Check if project is ready for search operations."""
        return self.status == ProjectStatus.READY

    def is_outdated(self, max_age_hours: int = 24) -> bool:
        """Check if project data is outdated."""
        if not self.last_crawl_at:
            return True

        age = datetime.utcnow() - self.last_crawl_at
        return age.total_seconds() > (max_age_hours * 3600)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "source_url": self.source_url,
            "status": self.status.value,
            "crawl_depth": self.crawl_depth,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_crawl_at": self.last_crawl_at.isoformat() if self.last_crawl_at else None,
            "total_pages": self.total_pages,
            "total_size_bytes": self.total_size_bytes,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages,
            "metadata": self.metadata,
            "outdated": self.is_outdated()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create Project from dictionary."""
        # Handle datetime fields
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        if 'last_crawl_at' in data and data['last_crawl_at']:
            data['last_crawl_at'] = datetime.fromisoformat(data['last_crawl_at'].replace('Z', '+00:00'))

        # Remove computed fields
        data.pop('outdated', None)

        return cls(**data)