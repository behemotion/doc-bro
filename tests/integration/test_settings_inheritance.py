"""
Integration tests for settings inheritance.
"""

import pytest
from pathlib import Path
import yaml

from src.services.settings_service import SettingsService
from src.models.settings import GlobalSettings, ProjectSettings, EffectiveSettings


class TestSettingsInheritance:
    """Test settings inheritance between global and project levels."""

    def test_new_project_inherits_global_defaults(self, tmp_path, monkeypatch):
        """Test that new projects inherit global settings."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()

        monkeypatch.setattr("src.services.settings_service.get_global_settings_path",
                          lambda: global_dir / "settings.yaml")

        service = SettingsService()
        service.global_settings_path = global_dir / "settings.yaml"

        # Set custom global settings
        global_settings = GlobalSettings(
            crawl_depth=5,
            chunk_size=2000,
            rag_temperature=0.8
        )
        service.save_global_settings(global_settings)

        # Get effective settings for project (no project settings yet)
        effective = service.get_effective_settings(project_dir)

        # Should inherit all global settings
        assert effective.crawl_depth == 5
        assert effective.chunk_size == 2000
        assert effective.rag_temperature == 0.8

    def test_project_overrides_take_precedence(self, tmp_path, monkeypatch):
        """Test that project settings override global defaults."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()

        monkeypatch.setattr("src.services.settings_service.get_global_settings_path",
                          lambda: global_dir / "settings.yaml")

        service = SettingsService()
        service.global_settings_path = global_dir / "settings.yaml"

        # Set global settings
        global_settings = GlobalSettings(
            crawl_depth=3,
            chunk_size=1500,
            rag_temperature=0.7
        )
        service.save_global_settings(global_settings)

        # Set project overrides
        project_settings = ProjectSettings(
            crawl_depth=7,  # Override
            chunk_size=3000  # Override
            # rag_temperature not set - should inherit
        )
        project_settings._modified_fields = {"crawl_depth", "chunk_size"}
        service.save_project_settings(project_settings, project_dir)

        # Get effective settings
        effective = service.get_effective_settings(project_dir)

        assert effective.crawl_depth == 7  # Project override
        assert effective.chunk_size == 3000  # Project override
        assert effective.rag_temperature == 0.7  # Inherited from global

    def test_global_changes_affect_unmodified_project_fields(self, tmp_path, monkeypatch):
        """Test that global changes propagate to unmodified project fields."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()

        monkeypatch.setattr("src.services.settings_service.get_global_settings_path",
                          lambda: global_dir / "settings.yaml")

        service = SettingsService()
        service.global_settings_path = global_dir / "settings.yaml"

        # Initial global settings
        global_settings = GlobalSettings(
            crawl_depth=3,
            chunk_size=1500
        )
        service.save_global_settings(global_settings)

        # Project with partial override
        project_settings = ProjectSettings(crawl_depth=5)
        project_settings._modified_fields = {"crawl_depth"}
        service.save_project_settings(project_settings, project_dir)

        # Update global settings
        global_settings.chunk_size = 2500  # Change unmodified field
        global_settings.crawl_depth = 8  # This won't affect project
        service.save_global_settings(global_settings)

        # Get effective settings
        effective = service.get_effective_settings(project_dir)

        assert effective.crawl_depth == 5  # Project override preserved
        assert effective.chunk_size == 2500  # Inherited new global value

    def test_multiple_projects_independent_overrides(self, tmp_path, monkeypatch):
        """Test that multiple projects can have independent overrides."""
        global_dir = tmp_path / "global"
        project1_dir = tmp_path / "project1"
        project2_dir = tmp_path / "project2"

        for dir in [global_dir, project1_dir, project2_dir]:
            dir.mkdir()

        monkeypatch.setattr("src.services.settings_service.get_global_settings_path",
                          lambda: global_dir / "settings.yaml")

        service = SettingsService()
        service.global_settings_path = global_dir / "settings.yaml"

        # Global settings
        service.save_global_settings(GlobalSettings(crawl_depth=3))

        # Project 1 settings
        p1_settings = ProjectSettings(crawl_depth=5)
        p1_settings._modified_fields = {"crawl_depth"}
        service.save_project_settings(p1_settings, project1_dir)

        # Project 2 settings
        p2_settings = ProjectSettings(crawl_depth=7)
        p2_settings._modified_fields = {"crawl_depth"}
        service.save_project_settings(p2_settings, project2_dir)

        # Check effective settings are independent
        eff1 = service.get_effective_settings(project1_dir)
        eff2 = service.get_effective_settings(project2_dir)

        assert eff1.crawl_depth == 5
        assert eff2.crawl_depth == 7

    def test_removing_project_override_reverts_to_global(self, tmp_path, monkeypatch):
        """Test that removing a project override reverts to global default."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()

        monkeypatch.setattr("src.services.settings_service.get_global_settings_path",
                          lambda: global_dir / "settings.yaml")

        service = SettingsService()
        service.global_settings_path = global_dir / "settings.yaml"

        # Set global
        service.save_global_settings(GlobalSettings(crawl_depth=3))

        # Set project override
        project_settings = ProjectSettings(crawl_depth=7)
        project_settings._modified_fields = {"crawl_depth"}
        service.save_project_settings(project_settings, project_dir)

        # Verify override works
        effective = service.get_effective_settings(project_dir)
        assert effective.crawl_depth == 7

        # Remove project override
        project_settings = ProjectSettings()  # No overrides
        project_settings._modified_fields = set()
        service.save_project_settings(project_settings, project_dir)

        # Should revert to global
        effective = service.get_effective_settings(project_dir)
        assert effective.crawl_depth == 3