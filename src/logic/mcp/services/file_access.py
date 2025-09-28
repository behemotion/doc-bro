"""File access controller for project-type-based access."""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.logic.mcp.models.file_access import FileAccessRequest, ProjectType, FileAccessType

logger = logging.getLogger(__name__)


class FileAccessController:
    """Controller for managing file access based on project type."""

    def __init__(self):
        """Initialize file access controller."""
        pass

    def validate_access(
        self,
        request: FileAccessRequest,
        project_type: ProjectType
    ) -> bool:
        """Validate if the requested access is allowed for the project type."""
        return request.is_access_allowed(project_type)

    def get_allowed_access_level(
        self,
        project_type: ProjectType
    ) -> FileAccessType:
        """Get the maximum allowed access level for a project type."""
        if project_type == ProjectType.STORAGE:
            return FileAccessType.DOWNLOAD  # Highest level
        else:
            return FileAccessType.METADATA  # Metadata only for crawling/data

    async def get_file_metadata(
        self,
        project_root: Path,
        file_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get file metadata from project."""
        try:
            metadata_list = []

            if file_path:
                # Single file metadata
                full_path = project_root / file_path
                if full_path.exists() and full_path.is_file():
                    metadata = await self._get_single_file_metadata(full_path, file_path)
                    if metadata:
                        metadata_list.append(metadata)
            else:
                # All files metadata
                if project_root.exists() and project_root.is_dir():
                    for file_obj in project_root.rglob("*"):
                        if file_obj.is_file():
                            relative_path = str(file_obj.relative_to(project_root))
                            metadata = await self._get_single_file_metadata(file_obj, relative_path)
                            if metadata:
                                metadata_list.append(metadata)

            return metadata_list

        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return []

    async def get_file_content(
        self,
        project_root: Path,
        file_path: str,
        project_type: ProjectType
    ) -> Optional[str]:
        """Get file content if access is allowed."""
        try:
            # Check if content access is allowed for this project type
            if project_type != ProjectType.STORAGE:
                logger.warning(f"Content access denied for {project_type} project")
                return None

            full_path = project_root / file_path

            # Security check - ensure file is within project boundaries
            try:
                full_path.resolve().relative_to(project_root.resolve())
            except ValueError:
                logger.warning(f"File access denied - path outside project: {file_path}")
                return None

            if full_path.exists() and full_path.is_file():
                # Read file content
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return content
            else:
                logger.warning(f"File not found: {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error reading file content: {e}")
            return None

    async def _get_single_file_metadata(
        self,
        file_path: Path,
        relative_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get metadata for a single file."""
        try:
            stat = file_path.stat()

            return {
                "path": relative_path,
                "size": stat.st_size,
                "modified_at": stat.st_mtime,
                "content_type": self._get_content_type(file_path)
            }

        except Exception as e:
            logger.error(f"Error getting metadata for {relative_path}: {e}")
            return None

    def _get_content_type(self, file_path: Path) -> str:
        """Determine content type based on file extension."""
        extension = file_path.suffix.lower()

        content_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
        }

        return content_types.get(extension, 'application/octet-stream')

    def is_safe_file_path(self, file_path: str) -> bool:
        """Check if file path is safe (no directory traversal)."""
        # Check for directory traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            return False

        # Check for hidden files/directories (optional restriction)
        path_parts = Path(file_path).parts
        for part in path_parts:
            if part.startswith('.'):
                return False

        return True

    async def list_accessible_files(
        self,
        project_root: Path,
        project_type: ProjectType,
        include_hidden: bool = False
    ) -> List[str]:
        """List all files accessible for the given project type."""
        try:
            accessible_files = []

            if project_root.exists() and project_root.is_dir():
                for file_obj in project_root.rglob("*"):
                    if file_obj.is_file():
                        relative_path = str(file_obj.relative_to(project_root))

                        # Skip hidden files unless explicitly requested
                        if not include_hidden and any(part.startswith('.') for part in Path(relative_path).parts):
                            continue

                        # For all project types, files are at least listable
                        accessible_files.append(relative_path)

            return accessible_files

        except Exception as e:
            logger.error(f"Error listing accessible files: {e}")
            return []