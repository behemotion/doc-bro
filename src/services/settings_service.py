"""
Settings service for managing global and project configurations.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import yaml

from src.lib.paths import (
    get_global_settings_path,
    get_project_settings_path,
    ensure_directory
)
from src.models.settings import (
    GlobalSettings,
    ProjectSettings,
    EffectiveSettings,
    SettingsMetadata,
    NON_OVERRIDABLE_FIELDS
)


class SettingsService:
    """Service for managing DocBro settings."""

    def __init__(self):
        """Initialize settings service."""
        self.global_settings_path = get_global_settings_path()
        self.settings_version = "1.0.0"

    def get_global_settings(self) -> GlobalSettings:
        """Load global settings from file or create defaults."""
        if self.global_settings_path.exists():
            try:
                with open(self.global_settings_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data and 'settings' in data:
                        settings_data = data['settings']

                        # Convert string back to VectorStoreProvider enum
                        if 'vector_store_provider' in settings_data and isinstance(settings_data['vector_store_provider'], str):
                            from src.models.vector_store_types import VectorStoreProvider
                            settings_data['vector_store_provider'] = VectorStoreProvider.from_string(settings_data['vector_store_provider'])

                        return GlobalSettings(**settings_data)
            except Exception as e:
                print(f"Warning: Failed to load global settings: {e}")

        # Return defaults if file doesn't exist or is invalid
        return GlobalSettings()

    def save_global_settings(self, settings: GlobalSettings) -> None:
        """Save global settings to file."""
        ensure_directory(self.global_settings_path.parent)

        metadata = SettingsMetadata(
            version=self.settings_version,
            updated_at=datetime.now()
        )

        # Convert settings to dict with proper enum serialization
        settings_dict = settings.model_dump()

        # Convert VectorStoreProvider enum to string value
        if 'vector_store_provider' in settings_dict:
            settings_dict['vector_store_provider'] = settings_dict['vector_store_provider'].value

        data = {
            'version': self.settings_version,
            'settings': settings_dict,
            'metadata': {
                'created_at': metadata.created_at.isoformat(),
                'updated_at': metadata.updated_at.isoformat(),
                'reset_count': metadata.reset_count
            }
        }

        with open(self.global_settings_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_project_settings(self, project_path: Optional[Path] = None) -> Optional[ProjectSettings]:
        """Load project-specific settings."""
        settings_path = get_project_settings_path(project_path)

        if not settings_path.exists():
            return None

        try:
            with open(settings_path, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'settings' in data:
                    project_settings = ProjectSettings(**data['settings'])
                    # Restore modified fields tracking
                    if 'modified_fields' in data:
                        for field in data['modified_fields']:
                            project_settings._modified_fields.add(field)
                    return project_settings
        except Exception as e:
            print(f"Warning: Failed to load project settings: {e}")

        return None

    def save_project_settings(
        self,
        settings: ProjectSettings,
        project_path: Optional[Path] = None
    ) -> None:
        """Save project-specific settings."""
        settings_path = get_project_settings_path(project_path)
        ensure_directory(settings_path.parent)

        data = {
            'version': self.settings_version,
            'settings': settings.model_dump(exclude_unset=True),
            'modified_fields': list(settings._modified_fields)
        }

        with open(settings_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_effective_settings(
        self,
        project_path: Optional[Path] = None
    ) -> EffectiveSettings:
        """Get effective settings after applying overrides."""
        global_settings = self.get_global_settings()
        project_settings = self.get_project_settings(project_path)

        return EffectiveSettings.from_configs(global_settings, project_settings)

    def validate_settings(
        self,
        settings: Dict,
        is_project: bool = False
    ) -> tuple[bool, list[str]]:
        """Validate settings dictionary."""
        errors = []

        try:
            if is_project:
                # Check for non-overridable fields
                for field in NON_OVERRIDABLE_FIELDS:
                    if field in settings:
                        errors.append(
                            f"Field '{field}' cannot be overridden at project level"
                        )

                # Validate as ProjectSettings
                ProjectSettings(**settings)
            else:
                # Validate as GlobalSettings
                GlobalSettings(**settings)

        except Exception as e:
            errors.append(str(e))

        return len(errors) == 0, errors

    def reset_to_factory_defaults(self, backup: bool = True) -> Path:
        """Reset global settings to factory defaults."""
        if backup and self.global_settings_path.exists():
            # Create backup
            backup_path = self.global_settings_path.with_suffix(
                f'.yaml.backup.{datetime.now().strftime("%Y%m%d-%H%M%S")}'
            )
            shutil.copy2(self.global_settings_path, backup_path)
        else:
            backup_path = None

        # Save factory defaults
        default_settings = GlobalSettings()
        self.save_global_settings(default_settings)

        return backup_path

    def migrate_settings(self, from_version: str, to_version: str) -> bool:
        """Migrate settings between versions."""
        # Placeholder for future migration logic
        # Currently no migrations needed for v1.0.0
        return True