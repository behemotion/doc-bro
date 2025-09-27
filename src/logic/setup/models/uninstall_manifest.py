"""Uninstall manifest model."""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class UninstallManifest(BaseModel):
    """Items to be removed during uninstallation."""

    directories: List[Path] = Field(
        default_factory=list,
        description="Directories to remove"
    )
    files: List[Path] = Field(
        default_factory=list,
        description="Individual files to remove"
    )
    config_entries: List[str] = Field(
        default_factory=list,
        description="Configuration keys to clear"
    )
    total_size_bytes: int = Field(
        default=0,
        description="Total disk space to recover in bytes"
    )
    backup_location: Optional[Path] = Field(
        default=None,
        description="Where backup will be or was stored"
    )

    @field_validator("directories", "files")
    @classmethod
    def validate_paths_exist(cls, v: List[Path]) -> List[Path]:
        """Validate that paths exist (warning only, not error)."""
        existing = []
        for path in v:
            if path.exists():
                existing.append(path)
            # We don't raise error for non-existing paths
            # as they might have been already removed
        return v

    @field_validator("total_size_bytes")
    @classmethod
    def validate_size_non_negative(cls, v: int) -> int:
        """Validate that size is non-negative."""
        if v < 0:
            raise ValueError(f"Total size cannot be negative: {v}")
        return v

    @field_validator("backup_location")
    @classmethod
    def validate_backup_location(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate backup location is writable if specified."""
        if v is None:
            return v

        # Check parent directory is writable
        parent = v.parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create backup directory {parent}: {e}")

        if not parent.is_dir():
            raise ValueError(f"Backup location parent is not a directory: {parent}")

        return v

    def add_directory(self, path: Path, calculate_size: bool = True) -> None:
        """Add a directory to the manifest."""
        if path not in self.directories:
            self.directories.append(path)

            if calculate_size and path.exists():
                self.total_size_bytes += self._calculate_directory_size(path)

    def add_file(self, path: Path, calculate_size: bool = True) -> None:
        """Add a file to the manifest."""
        if path not in self.files:
            self.files.append(path)

            if calculate_size and path.exists() and path.is_file():
                self.total_size_bytes += path.stat().st_size

    def add_config_entry(self, key: str) -> None:
        """Add a configuration key to clear."""
        if key not in self.config_entries:
            self.config_entries.append(key)

    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of a directory recursively."""
        total = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        except (OSError, PermissionError):
            # Ignore errors accessing files
            pass
        return total

    def recalculate_size(self) -> None:
        """Recalculate total size based on current paths."""
        self.total_size_bytes = 0

        for directory in self.directories:
            if directory.exists():
                self.total_size_bytes += self._calculate_directory_size(directory)

        for file in self.files:
            if file.exists() and file.is_file():
                self.total_size_bytes += file.stat().st_size

    def get_size_mb(self) -> float:
        """Get total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    def get_size_display(self) -> str:
        """Get human-readable size display."""
        size_bytes = self.total_size_bytes

        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

        return f"{size_bytes:.2f} TB"

    def is_empty(self) -> bool:
        """Check if manifest is empty."""
        return not (self.directories or self.files or self.config_entries)

    def get_item_count(self) -> int:
        """Get total number of items to remove."""
        return len(self.directories) + len(self.files) + len(self.config_entries)

    def to_display_list(self) -> List[str]:
        """Convert to user-friendly display list."""
        items = []

        if self.directories:
            items.append("Directories to remove:")
            for dir_path in sorted(self.directories):
                items.append(f"  • {dir_path}")

        if self.files:
            items.append("Files to remove:")
            for file_path in sorted(self.files):
                items.append(f"  • {file_path}")

        if self.config_entries:
            items.append("Configuration entries to clear:")
            for entry in sorted(self.config_entries):
                items.append(f"  • {entry}")

        items.append(f"\nTotal space to recover: {self.get_size_display()}")

        if self.backup_location:
            items.append(f"Backup will be created at: {self.backup_location}")

        return items

    def filter_existing(self) -> "UninstallManifest":
        """Return a new manifest with only existing items."""
        return UninstallManifest(
            directories=[d for d in self.directories if d.exists()],
            files=[f for f in self.files if f.exists()],
            config_entries=self.config_entries.copy(),
            total_size_bytes=self.total_size_bytes,
            backup_location=self.backup_location
        )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
        json_encoders = {
            Path: str
        }