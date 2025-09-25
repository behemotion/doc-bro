"""
Settings migration support for version upgrades.
"""

from typing import Dict, Any, Optional, Callable
from packaging import version
from pathlib import Path
import yaml

from src.lib.yaml_utils import load_yaml_file, save_yaml_file, create_backup


class SettingsMigrator:
    """Handle settings version migrations."""

    # Migration functions registry
    migrations: Dict[str, Callable[[Dict], Dict]] = {}

    @classmethod
    def register_migration(cls, from_version: str, to_version: str):
        """Decorator to register a migration function."""
        def decorator(func: Callable):
            key = f"{from_version}->{to_version}"
            cls.migrations[key] = func
            return func
        return decorator

    @classmethod
    def migrate(cls, data: Dict, from_version: str, to_version: str) -> Dict:
        """Apply migrations between versions."""
        current_ver = version.parse(from_version)
        target_ver = version.parse(to_version)

        if current_ver >= target_ver:
            # No migration needed
            return data

        result = data.copy()

        # Find and apply migrations in sequence
        for key, migration_func in cls.migrations.items():
            if "->" in key:
                from_v, to_v = key.split("->")
                from_v = version.parse(from_v)
                to_v = version.parse(to_v)

                if from_v >= current_ver and to_v <= target_ver:
                    result = migration_func(result)
                    result["version"] = str(to_v)

        return result

    @classmethod
    def detect_version(cls, data: Dict) -> str:
        """Detect settings file version."""
        return data.get("version", "0.0.0")

    @classmethod
    def migrate_file(cls, file_path: Path, target_version: str) -> bool:
        """Migrate a settings file to target version."""
        data = load_yaml_file(file_path)
        if not data:
            return False

        current_version = cls.detect_version(data)

        if current_version == target_version:
            # Already at target version
            return True

        # Create backup before migration
        backup_path = create_backup(file_path, f"pre-migration-{current_version}")
        if not backup_path:
            print(f"Warning: Could not create backup before migration")

        # Migrate
        migrated_data = cls.migrate(data, current_version, target_version)

        # Save migrated data
        return save_yaml_file(file_path, migrated_data)


# Example migrations (to be implemented as needed)

@SettingsMigrator.register_migration("0.9.0", "1.0.0")
def migrate_090_to_100(data: Dict) -> Dict:
    """Migrate from 0.9.0 to 1.0.0."""
    result = data.copy()

    # Example: Rename old field to new field
    if "settings" in result:
        settings = result["settings"]

        # Example: chunk_length -> chunk_size
        if "chunk_length" in settings:
            settings["chunk_size"] = settings.pop("chunk_length")

        # Example: Add new required fields with defaults
        if "rag_top_k" not in settings:
            settings["rag_top_k"] = 5

        if "rag_temperature" not in settings:
            settings["rag_temperature"] = 0.7

    # Update version
    result["version"] = "1.0.0"

    return result


@SettingsMigrator.register_migration("1.0.0", "1.1.0")
def migrate_100_to_110(data: Dict) -> Dict:
    """Migrate from 1.0.0 to 1.1.0 (future migration example)."""
    result = data.copy()

    # Future migration logic would go here
    # For now, just update version
    result["version"] = "1.1.0"

    return result


def check_and_migrate_settings(file_path: Path, target_version: str = "1.0.0") -> bool:
    """Check settings file and migrate if needed."""
    if not file_path.exists():
        # No file to migrate
        return True

    data = load_yaml_file(file_path)
    if not data:
        # Invalid file
        return False

    current_version = SettingsMigrator.detect_version(data)

    if current_version != target_version:
        print(f"Migrating settings from v{current_version} to v{target_version}")
        return SettingsMigrator.migrate_file(file_path, target_version)

    return True