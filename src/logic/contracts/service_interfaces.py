"""Service interface contracts for projects logic implementation."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from typing import Any

from ..projects.models.config import ProjectConfig
from ..projects.models.project import Project
from ..projects.models.upload import UploadSource


class ValidationResult:
    """Result of validation operation."""

    def __init__(self, valid: bool, errors: list[str] = None, warnings: list[str] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []


class ProjectHandlerContract(ABC):
    """Base interface for type-specific project operations."""

    @abstractmethod
    async def initialize_project(self, project: Project) -> bool:
        """Initialize project-specific storage and configuration."""
        pass

    @abstractmethod
    async def cleanup_project(self, project: Project) -> bool:
        """Clean up project-specific resources."""
        pass

    @abstractmethod
    async def validate_settings(self, settings: ProjectConfig) -> ValidationResult:
        """Validate settings for this project type."""
        pass

    @abstractmethod
    async def get_default_settings(self) -> ProjectConfig:
        """Get default settings for this project type."""
        pass


class CrawlingProjectContract(ProjectHandlerContract):
    """Crawling project specific operations."""

    @abstractmethod
    async def start_crawl(
        self,
        project: Project,
        url: str,
        depth: int,
        progress_callback: Callable[[dict[str, Any]], None] | None = None
    ) -> dict[str, Any]:
        """Start web crawling operation."""
        pass

    @abstractmethod
    async def get_crawl_status(self, project: Project) -> dict[str, Any]:
        """Get crawling operation status."""
        pass


class DataProjectContract(ProjectHandlerContract):
    """Data project specific operations."""

    @abstractmethod
    async def process_document(
        self,
        project: Project,
        file_path: str
    ) -> bool:
        """Process document for vector storage."""
        pass

    @abstractmethod
    async def search_documents(
        self,
        project: Project,
        query: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search documents in project."""
        pass

    @abstractmethod
    async def get_document_stats(self, project: Project) -> dict[str, Any]:
        """Get document processing statistics."""
        pass


class StorageProjectContract(ProjectHandlerContract):
    """Storage project specific operations."""

    @abstractmethod
    async def store_file(
        self,
        project: Project,
        file_path: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Store file and return file ID."""
        pass

    @abstractmethod
    async def retrieve_file(
        self,
        project: Project,
        file_id: str,
        output_path: str
    ) -> bool:
        """Retrieve stored file."""
        pass

    @abstractmethod
    async def search_files(
        self,
        project: Project,
        query: str,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search files in storage project."""
        pass

    @abstractmethod
    async def tag_file(
        self,
        project: Project,
        file_id: str,
        tags: list[str]
    ) -> bool:
        """Add tags to stored file."""
        pass

    @abstractmethod
    async def get_file_inventory(self, project: Project) -> list[dict[str, Any]]:
        """Get complete file inventory."""
        pass


class UploadSourceContract(ABC):
    """Base interface for upload source handlers."""

    @abstractmethod
    async def validate_source(self, source: UploadSource) -> ValidationResult:
        """Validate source accessibility and credentials."""
        pass

    @abstractmethod
    async def list_files(
        self,
        source: UploadSource,
        recursive: bool = False
    ) -> AsyncGenerator[str]:
        """List files available from source."""
        pass

    @abstractmethod
    async def download_file(
        self,
        source: UploadSource,
        remote_path: str,
        local_path: str,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> bool:
        """Download single file from source."""
        pass

    @abstractmethod
    async def get_file_info(
        self,
        source: UploadSource,
        remote_path: str
    ) -> dict[str, Any]:
        """Get file metadata (size, type, etc.)."""
        pass
