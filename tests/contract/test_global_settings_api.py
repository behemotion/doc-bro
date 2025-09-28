"""
Contract tests for global settings API endpoints.
"""

import pytest
from src.services.settings_service import SettingsService
from src.models.settings import GlobalSettings


class TestGlobalSettingsAPI:
    """Test global settings API contracts."""

    def test_get_global_settings_returns_defaults(self):
        """Test that GET global settings returns default values."""
        service = SettingsService()
        settings = service.get_global_settings()

        assert isinstance(settings, GlobalSettings)
        assert settings.embedding_model == "mxbai-embed-large"
        assert settings.crawl_depth == 3
        assert settings.chunk_size == 1500
        assert settings.rag_temperature == 0.7

    def test_save_and_load_global_settings(self, tmp_path, monkeypatch):
        """Test saving and loading global settings."""
        # Mock the settings path
        settings_file = tmp_path / "settings.yaml"
        monkeypatch.setattr("src.services.settings_service.get_global_settings_path", lambda: settings_file)

        service = SettingsService()
        service.global_settings_path = settings_file

        # Create custom settings
        settings = GlobalSettings(
            crawl_depth=5,
            chunk_size=2000,
            rag_temperature=0.8
        )

        # Save settings
        service.save_global_settings(settings)
        assert settings_file.exists()

        # Load settings
        loaded = service.get_global_settings()
        assert loaded.crawl_depth == 5
        assert loaded.chunk_size == 2000
        assert loaded.rag_temperature == 0.8

    @pytest.mark.xfail(reason="Not yet implemented")
    def test_validate_invalid_settings(self):
        """Test validation of invalid settings."""
        service = SettingsService()

        invalid_settings = {
            "crawl_depth": 20,  # Exceeds max
            "chunk_size": 50,  # Below min
        }

        is_valid, errors = service.validate_settings(invalid_settings)
        assert not is_valid
        assert len(errors) >= 2