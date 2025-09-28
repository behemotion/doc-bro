"""
Base class for upload source handlers

Provides common interface and functionality for all upload source types.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from typing import Any

from src.logic.projects.models.upload import UploadSource
from src.logic.projects.models.validation import ValidationResult


class BaseUploadSource(ABC):
    """Abstract base class for upload source handlers"""

    def __init__(self):
        self.source_type = None

    @abstractmethod
    async def validate_source(self, source: UploadSource) -> ValidationResult:
        """Validate source accessibility and credentials"""
        pass

    @abstractmethod
    async def list_files(
        self,
        source: UploadSource,
        recursive: bool = False
    ) -> AsyncGenerator[str]:
        """List files available from source"""
        pass

    @abstractmethod
    async def download_file(
        self,
        source: UploadSource,
        remote_path: str,
        local_path: str,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> bool:
        """Download single file from source"""
        pass

    @abstractmethod
    async def get_file_info(
        self,
        source: UploadSource,
        remote_path: str
    ) -> dict[str, Any]:
        """Get file metadata (size, type, etc.)"""
        pass

    @abstractmethod
    async def test_connection(self, source: UploadSource) -> bool:
        """Test connection to source"""
        pass

    def supports_resume(self) -> bool:
        """Whether this source supports resuming interrupted downloads"""
        return False

    def requires_authentication(self) -> bool:
        """Whether this source requires authentication"""
        return False

    async def cleanup(self, source: UploadSource) -> None:
        """Cleanup any resources after upload operation"""
        pass
