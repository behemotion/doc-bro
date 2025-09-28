"""FileAccessRequest model for project-type-based file access validation."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator


class FileAccessType(str, Enum):
    """Types of file access requests."""

    METADATA = "metadata"
    CONTENT = "content"
    DOWNLOAD = "download"


class ProjectType(str, Enum):
    """Project types with different access levels."""

    CRAWLING = "crawling"
    DATA = "data"
    STORAGE = "storage"


class FileAccessRequest(BaseModel):
    """Request for file access with project-type-based validation.

    Attributes:
        project_name: Name of the target project
        file_path: Requested file path (optional)
        access_type: Type of access requested
    """

    project_name: str = Field(..., min_length=1)
    file_path: Optional[str] = Field(default=None)
    access_type: FileAccessType = Field(default=FileAccessType.METADATA)

    @validator("file_path")
    def validate_file_path_security(cls, v: Optional[str]) -> Optional[str]:
        """Validate file path for security (prevent directory traversal)."""
        if v is None:
            return v

        # Prevent directory traversal attacks
        if ".." in v or v.startswith("/"):
            raise ValueError("File path must be relative and cannot contain '..' sequences")

        # Normalize path separators
        v = v.replace("\\", "/")

        return v

    def is_within_project_boundaries(self, project_root: str) -> bool:
        """Check if the file path is within project boundaries."""
        if self.file_path is None:
            return True

        # Additional boundary validation would go here
        # This is a simplified check
        return not self.file_path.startswith("/") and ".." not in self.file_path

    def get_allowed_access_level(self, project_type: ProjectType) -> FileAccessType:
        """Get the allowed access level based on project type.

        Access matrix from data-model.md:
        | Project Type | Metadata | Content | Files |
        |-------------|----------|---------|-------|
        | crawling    | ✓        | ✗       | ✗     |
        | data        | ✓        | ✗       | ✗     |
        | storage     | ✓        | ✓       | ✓     |
        """
        if project_type == ProjectType.STORAGE:
            return self.access_type  # Storage projects allow all access types
        else:
            return FileAccessType.METADATA  # Crawling and data projects: metadata only

    def is_access_allowed(self, project_type: ProjectType) -> bool:
        """Check if the requested access is allowed for the project type."""
        allowed_level = self.get_allowed_access_level(project_type)

        # Map access types to levels (higher number = more access)
        access_levels = {
            FileAccessType.METADATA: 1,
            FileAccessType.CONTENT: 2,
            FileAccessType.DOWNLOAD: 3,
        }

        requested_level = access_levels[self.access_type]
        allowed_level_num = access_levels[allowed_level]

        return requested_level <= allowed_level_num