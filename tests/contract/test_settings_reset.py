"""
Contract tests for factory reset functionality.
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.services.settings_service import SettingsService
from src.models.settings import GlobalSettings


class TestSettingsReset:
    """Test factory reset contracts."""

    def test_reset_to_factory_defaults(self, tmp_path, monkeypatch):
        """Test resetting settings to factory defaults."""
        settings_file = tmp_path / "settings.yaml"
        monkeypatch.setattr("src.services.settings_service.get_global_settings_path", lambda: settings_file)

        service = SettingsService()
        service.global_settings_path = settings_file

        # Create custom settings
        custom_settings = GlobalSettings(
            crawl_depth=7,
            chunk_size=3000,
            rag_temperature=0.9
        )
        service.save_global_settings(custom_settings)

        # Verify custom settings saved
        loaded = service.get_global_settings()
        assert loaded.crawl_depth == 7

        # Reset to factory defaults
        backup_path = service.reset_to_factory_defaults(backup=True)

        # Verify backup was created
        assert backup_path is not None
        assert backup_path.exists()
        assert "backup" in str(backup_path)

        # Verify settings are reset to defaults
        reset_settings = service.get_global_settings()
        assert reset_settings.crawl_depth == 3  # Default value
        assert reset_settings.chunk_size == 1500  # Default value
        assert reset_settings.rag_temperature == 0.7  # Default value

    def test_reset_without_backup(self, tmp_path, monkeypatch):
        """Test reset without creating backup."""
        settings_file = tmp_path / "settings.yaml"
        monkeypatch.setattr("src.services.settings_service.get_global_settings_path", lambda: settings_file)

        service = SettingsService()
        service.global_settings_path = settings_file

        # Create custom settings
        custom_settings = GlobalSettings(crawl_depth=8)
        service.save_global_settings(custom_settings)

        # Reset without backup
        backup_path = service.reset_to_factory_defaults(backup=False)

        # No backup should be created
        assert backup_path is None

        # Settings should still be reset
        reset_settings = service.get_global_settings()
        assert reset_settings.crawl_depth == 3

    def test_reset_preserves_project_settings(self, tmp_path, monkeypatch):
        """Test that factory reset doesn't affect project settings."""
        # Setup paths
        global_settings_file = tmp_path / "global" / "settings.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        monkeypatch.setattr("src.services.settings_service.get_global_settings_path", lambda: global_settings_file)

        service = SettingsService()
        service.global_settings_path = global_settings_file

        # Create project settings
        from src.models.settings import ProjectSettings
        project_settings = ProjectSettings(crawl_depth=9)
        project_settings._modified_fields = {"crawl_depth"}
        service.save_project_settings(project_settings, project_dir)

        # Reset global settings
        service.reset_to_factory_defaults()

        # Project settings should remain unchanged
        loaded_project = service.get_project_settings(project_dir)
        assert loaded_project is not None
        assert loaded_project.crawl_depth == 9

    def test_reset_creates_timestamped_backup(self, tmp_path, monkeypatch):
        """Test that backup files have timestamp in name."""
        settings_file = tmp_path / "settings.yaml"
        monkeypatch.setattr("src.services.settings_service.get_global_settings_path", lambda: settings_file)

        service = SettingsService()
        service.global_settings_path = settings_file

        # Save some settings
        service.save_global_settings(GlobalSettings())

        # Reset and check backup naming
        backup_path = service.reset_to_factory_defaults(backup=True)

        assert backup_path is not None
        assert "backup" in backup_path.name
        # Check for timestamp pattern (YYYYMMDD-HHMMSS)
        import re
        timestamp_pattern = r'\d{8}-\d{6}'
        assert re.search(timestamp_pattern, backup_path.name) is not None