"""
File conflict resolution service

Handles detection and resolution of file naming conflicts including:
- Duplicate filename detection
- Interactive conflict resolution
- Automatic rename strategies
- Conflict logging and tracking
"""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.logic.projects.models.project import Project
from src.logic.projects.models.validation import ValidationResult

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy:
    """Enumeration of conflict resolution strategies"""
    ASK = "ask"
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    BACKUP = "backup"


class FileConflict:
    """Represents a file naming conflict"""

    def __init__(self, filename: str, existing_path: str, new_path: str):
        self.filename = filename
        self.existing_path = existing_path
        self.new_path = new_path
        self.resolved = False
        self.resolution = None
        self.resolved_filename = None
        self.timestamp = datetime.now()


class ConflictResolver:
    """Service for resolving file naming conflicts"""

    def __init__(self):
        self.conflicts: list[FileConflict] = []
        self.default_strategy = ConflictResolutionStrategy.ASK
        self.interactive_callback: Callable | None = None

    async def detect_conflicts(
        self,
        project: Project,
        incoming_files: list[str],
        target_directory: str
    ) -> list[FileConflict]:
        """Detect filename conflicts with existing files"""
        conflicts = []
        target_path = Path(target_directory)

        try:
            # Get existing files in target directory
            existing_files = set()
            if target_path.exists():
                for file_path in target_path.rglob("*"):
                    if file_path.is_file():
                        existing_files.add(file_path.name.lower())

            # Check each incoming file for conflicts
            for file_path in incoming_files:
                filename = Path(file_path).name

                if filename.lower() in existing_files:
                    existing_path = target_path / filename
                    conflict = FileConflict(
                        filename=filename,
                        existing_path=str(existing_path),
                        new_path=file_path
                    )
                    conflicts.append(conflict)
                    logger.debug(f"Conflict detected: {filename}")

            self.conflicts.extend(conflicts)
            return conflicts

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []

    async def resolve_conflict(
        self,
        conflict: FileConflict,
        strategy: str | None = None,
        project: Project | None = None
    ) -> str:
        """Resolve single file conflict, return final filename"""
        try:
            resolution_strategy = strategy or self.default_strategy

            if resolution_strategy == ConflictResolutionStrategy.ASK:
                # Use interactive resolution
                if self.interactive_callback:
                    resolution_strategy = await self.interactive_callback(conflict)
                else:
                    # Default to rename if no interactive callback
                    resolution_strategy = ConflictResolutionStrategy.RENAME

            resolved_filename = await self._apply_resolution_strategy(
                conflict, resolution_strategy, project
            )

            # Update conflict record
            conflict.resolved = True
            conflict.resolution = resolution_strategy
            conflict.resolved_filename = resolved_filename

            logger.info(f"Conflict resolved: {conflict.filename} -> {resolved_filename} (strategy: {resolution_strategy})")
            return resolved_filename

        except Exception as e:
            logger.error(f"Error resolving conflict for {conflict.filename}: {e}")
            # Fallback to rename strategy
            return await self.suggest_filename(conflict.filename, project)

    async def resolve_all_conflicts(
        self,
        conflicts: list[FileConflict],
        strategy: str | None = None,
        project: Project | None = None
    ) -> dict[str, str]:
        """Resolve all conflicts and return filename mapping"""
        resolution_map = {}

        for conflict in conflicts:
            resolved_filename = await self.resolve_conflict(conflict, strategy, project)
            resolution_map[conflict.filename] = resolved_filename

        return resolution_map

    async def suggest_filename(
        self,
        original_filename: str,
        project: Project | None = None,
        target_directory: str | None = None
    ) -> str:
        """Suggest non-conflicting filename"""
        try:
            path = Path(original_filename)
            name_part = path.stem
            extension = path.suffix

            # Different naming strategies based on project type
            if project and hasattr(project, 'type'):
                suggestion = await self._get_type_specific_suggestion(
                    name_part, extension, project, target_directory
                )
                if suggestion:
                    return suggestion

            # Default timestamp-based suggestion
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggested_name = f"{name_part}_{timestamp}{extension}"

            # Ensure the suggestion doesn't also conflict
            if target_directory:
                suggested_path = Path(target_directory) / suggested_name
                counter = 1
                while suggested_path.exists():
                    suggested_name = f"{name_part}_{timestamp}_{counter}{extension}"
                    suggested_path = Path(target_directory) / suggested_name
                    counter += 1

            return suggested_name

        except Exception as e:
            logger.error(f"Error suggesting filename for {original_filename}: {e}")
            # Fallback to simple numbered suffix
            return f"{Path(original_filename).stem}_copy{Path(original_filename).suffix}"

    async def _apply_resolution_strategy(
        self,
        conflict: FileConflict,
        strategy: str,
        project: Project | None = None
    ) -> str:
        """Apply specific resolution strategy"""
        if strategy == ConflictResolutionStrategy.SKIP:
            return None  # File will be skipped

        elif strategy == ConflictResolutionStrategy.OVERWRITE:
            return conflict.filename  # Keep original name, will overwrite

        elif strategy == ConflictResolutionStrategy.RENAME:
            target_dir = Path(conflict.existing_path).parent
            return await self.suggest_filename(
                conflict.filename, project, str(target_dir)
            )

        elif strategy == ConflictResolutionStrategy.BACKUP:
            # Create backup of existing file and use original name
            await self._create_backup(conflict.existing_path)
            return conflict.filename

        else:
            # Default to rename
            target_dir = Path(conflict.existing_path).parent
            return await self.suggest_filename(
                conflict.filename, project, str(target_dir)
            )

    async def _get_type_specific_suggestion(
        self,
        name_part: str,
        extension: str,
        project: Project,
        target_directory: str | None = None
    ) -> str | None:
        """Get project type-specific filename suggestion"""
        from src.logic.projects.models.project import ProjectType

        try:
            if project.type == ProjectType.DATA:
                # Data projects: add version number
                version = await self._get_next_version_number(name_part, extension, target_directory)
                return f"{name_part}_v{version}{extension}"

            elif project.type == ProjectType.STORAGE:
                # Storage projects: add date prefix
                date_prefix = datetime.now().strftime("%Y%m%d")
                return f"{date_prefix}_{name_part}{extension}"

            elif project.type == ProjectType.CRAWLING:
                # Crawling projects: add page suffix
                page_num = await self._get_next_page_number(name_part, extension, target_directory)
                return f"{name_part}_page{page_num}{extension}"

        except Exception as e:
            logger.debug(f"Error generating type-specific suggestion: {e}")

        return None

    async def _get_next_version_number(
        self,
        name_part: str,
        extension: str,
        target_directory: str | None = None
    ) -> int:
        """Get next available version number for filename"""
        if not target_directory:
            return 1

        target_path = Path(target_directory)
        if not target_path.exists():
            return 1

        # Find existing versions
        pattern = re.compile(rf"{re.escape(name_part)}_v(\d+){re.escape(extension)}")
        max_version = 0

        for file_path in target_path.iterdir():
            if file_path.is_file():
                match = pattern.match(file_path.name)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)

        return max_version + 1

    async def _get_next_page_number(
        self,
        name_part: str,
        extension: str,
        target_directory: str | None = None
    ) -> int:
        """Get next available page number for filename"""
        if not target_directory:
            return 1

        target_path = Path(target_directory)
        if not target_path.exists():
            return 1

        # Find existing pages
        pattern = re.compile(rf"{re.escape(name_part)}_page(\d+){re.escape(extension)}")
        max_page = 0

        for file_path in target_path.iterdir():
            if file_path.is_file():
                match = pattern.match(file_path.name)
                if match:
                    page = int(match.group(1))
                    max_page = max(max_page, page)

        return max_page + 1

    async def _create_backup(self, file_path: str) -> str:
        """Create backup of existing file"""
        try:
            path = Path(file_path)
            backup_name = f"{path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
            backup_path = path.parent / backup_name

            # Copy file to backup location
            import shutil
            shutil.copy2(str(path), str(backup_path))

            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
            raise

    def set_interactive_callback(self, callback: Callable[[FileConflict], str]):
        """Set callback for interactive conflict resolution"""
        self.interactive_callback = callback

    def set_default_strategy(self, strategy: str):
        """Set default conflict resolution strategy"""
        if strategy in [
            ConflictResolutionStrategy.ASK,
            ConflictResolutionStrategy.SKIP,
            ConflictResolutionStrategy.OVERWRITE,
            ConflictResolutionStrategy.RENAME,
            ConflictResolutionStrategy.BACKUP
        ]:
            self.default_strategy = strategy
        else:
            logger.warning(f"Invalid strategy: {strategy}, keeping default")

    def get_conflict_history(self) -> list[dict[str, Any]]:
        """Get history of resolved conflicts"""
        return [
            {
                "filename": conflict.filename,
                "existing_path": conflict.existing_path,
                "new_path": conflict.new_path,
                "resolved": conflict.resolved,
                "resolution": conflict.resolution,
                "resolved_filename": conflict.resolved_filename,
                "timestamp": conflict.timestamp.isoformat()
            }
            for conflict in self.conflicts
        ]

    def clear_conflict_history(self):
        """Clear conflict history"""
        self.conflicts.clear()
        logger.debug("Conflict history cleared")

    async def validate_resolution(
        self,
        original_filename: str,
        resolved_filename: str,
        target_directory: str
    ) -> ValidationResult:
        """Validate that conflict resolution is appropriate"""
        try:
            warnings = []
            errors = []

            # Check if resolved filename still conflicts
            target_path = Path(target_directory) / resolved_filename
            if target_path.exists():
                errors.append(f"Resolved filename '{resolved_filename}' still conflicts")

            # Check if filename is valid for the filesystem
            if not self._is_valid_filename(resolved_filename):
                errors.append(f"Resolved filename '{resolved_filename}' contains invalid characters")

            # Check for excessive length
            if len(resolved_filename) > 255:
                errors.append("Resolved filename exceeds maximum length (255 characters)")

            # Warn about significant name changes
            original_stem = Path(original_filename).stem
            resolved_stem = Path(resolved_filename).stem
            if len(resolved_stem) > len(original_stem) * 1.5:
                warnings.append("Resolved filename significantly longer than original")

            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Error validating resolution: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Resolution validation error: {str(e)}"],
                warnings=[]
            )

    def _is_valid_filename(self, filename: str) -> bool:
        """Check if filename is valid for most filesystems"""
        # Invalid characters for Windows/Mac/Linux
        invalid_chars = '<>:"/\\|?*'

        # Check for invalid characters
        if any(char in filename for char in invalid_chars):
            return False

        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        name_part = Path(filename).stem.upper()
        if name_part in reserved_names:
            return False

        # Check for control characters
        if any(ord(char) < 32 for char in filename):
            return False

        return True
