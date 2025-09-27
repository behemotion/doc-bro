"""Setup uninstaller service."""

import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import tarfile
from src.logic.setup.models.uninstall_manifest import UninstallManifest
from src.lib.logging import get_logger

logger = get_logger(__name__)


class SetupUninstaller:
    """Service for uninstalling DocBro."""

    def __init__(self, home_dir: Optional[Path] = None):
        """Initialize the uninstaller.

        Args:
            home_dir: Optional home directory for testing
        """
        self.home_dir = home_dir or Path.home()
        self.config_dir = self.home_dir / ".config" / "docbro"
        self.data_dir = self.home_dir / ".local" / "share" / "docbro"
        self.cache_dir = self.home_dir / ".cache" / "docbro"

    def generate_manifest(self, preserve_data: bool = False) -> UninstallManifest:
        """Generate uninstall manifest.

        Args:
            preserve_data: Whether to preserve user data

        Returns:
            UninstallManifest with items to remove
        """
        manifest = UninstallManifest()

        # Add directories
        if self.config_dir.exists():
            manifest.add_directory(self.config_dir)

        if self.cache_dir.exists():
            manifest.add_directory(self.cache_dir)

        if self.data_dir.exists():
            if preserve_data:
                # Only remove non-project directories
                for item in self.data_dir.iterdir():
                    if item.name != "projects":
                        if item.is_dir():
                            manifest.add_directory(item)
                        else:
                            manifest.add_file(item)
            else:
                manifest.add_directory(self.data_dir)

        # Add specific files if they exist
        potential_files = [
            self.home_dir / ".docbro",  # Legacy config file
            Path("/usr/local/bin/docbro"),  # Symlink if exists
        ]

        for file_path in potential_files:
            if file_path.exists():
                manifest.add_file(file_path)

        # Add config entries to clear
        manifest.add_config_entry("DOCBRO_HOME")
        manifest.add_config_entry("DOCBRO_CONFIG")

        return manifest

    def create_backup(self, manifest: UninstallManifest) -> Path:
        """Create backup of items to be removed.

        Args:
            manifest: Items to backup

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.home_dir / ".local" / "share" / "docbro_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"docbro_backup_{timestamp}.tar.gz"

        with tarfile.open(backup_path, "w:gz") as tar:
            for directory in manifest.directories:
                if directory.exists():
                    tar.add(directory, arcname=directory.name)

            for file_path in manifest.files:
                if file_path.exists():
                    tar.add(file_path, arcname=file_path.name)

        logger.info(f"Created backup at {backup_path}")
        manifest.backup_location = backup_path
        return backup_path

    def execute(
        self,
        manifest: Optional[UninstallManifest] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Execute uninstallation.

        Args:
            manifest: Optional manifest, generates if not provided
            force: Force removal without checks

        Returns:
            Uninstall results
        """
        if not manifest:
            manifest = self.generate_manifest()

        results = {
            "removed": [],
            "failed": [],
            "status": "completed"
        }

        # Remove directories
        for directory in manifest.directories:
            if directory.exists():
                try:
                    shutil.rmtree(directory)
                    results["removed"].append(str(directory))
                    logger.debug(f"Removed directory: {directory}")
                except Exception as e:
                    logger.error(f"Failed to remove {directory}: {e}")
                    results["failed"].append(str(directory))
                    if not force:
                        results["status"] = "partial"

        # Remove files
        for file_path in manifest.files:
            if file_path.exists():
                try:
                    file_path.unlink()
                    results["removed"].append(str(file_path))
                    logger.debug(f"Removed file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to remove {file_path}: {e}")
                    results["failed"].append(str(file_path))
                    if not force:
                        results["status"] = "partial"

        logger.info(f"Uninstall completed: {len(results['removed'])} items removed")
        return results