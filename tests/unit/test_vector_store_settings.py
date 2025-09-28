"""Contract tests for VectorStoreSettings model with SQLite-vec support."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from src.models.vector_store_types import VectorStoreProvider
from src.models.settings import VectorStoreSettings
from src.models.sqlite_vec_config import SQLiteVecConfiguration


class TestVectorStoreSettings:
    """Test VectorStoreSettings model with SQLite-vec integration."""

    def test_create_with_qdrant_provider(self):
        """Test creating settings with Qdrant provider."""
        settings = VectorStoreSettings(
            provider=VectorStoreProvider.QDRANT,
            qdrant_config={
                "url": "http://localhost:6333",
                "api_key": None
            }
        )

        assert settings.provider == VectorStoreProvider.QDRANT
        assert settings.qdrant_config is not None
        assert settings.sqlite_vec_config is None

    def test_create_with_sqlite_vec_provider(self, tmp_path):
        """Test creating settings with SQLite-vec provider."""
        settings = VectorStoreSettings(
            provider=VectorStoreProvider.SQLITE_VEC,
            sqlite_vec_config={
                "enabled": True,
                "database_path": str(tmp_path / "vectors.db")
            }
        )

        assert settings.provider == VectorStoreProvider.SQLITE_VEC
        assert settings.sqlite_vec_config is not None
        assert settings.qdrant_config is None

    def test_provider_config_validation(self, tmp_path):
        """Test that provider must match the non-null configuration."""
        # Invalid: Qdrant provider with SQLite config
        with pytest.raises(ValidationError) as exc_info:
            VectorStoreSettings(
                provider=VectorStoreProvider.QDRANT,
                sqlite_vec_config={
                    "enabled": True,
                    "database_path": str(tmp_path / "vectors.db")
                }
            )
        assert "provider mismatch" in str(exc_info.value).lower()

        # Invalid: SQLite provider with Qdrant config
        with pytest.raises(ValidationError) as exc_info:
            VectorStoreSettings(
                provider=VectorStoreProvider.SQLITE_VEC,
                qdrant_config={
                    "url": "http://localhost:6333"
                }
            )
        assert "provider mismatch" in str(exc_info.value).lower()

    def test_exactly_one_config_required(self):
        """Test that exactly one configuration must be provided."""
        # Invalid: No configuration
        with pytest.raises(ValidationError) as exc_info:
            VectorStoreSettings(
                provider=VectorStoreProvider.SQLITE_VEC
            )
        assert "configuration required" in str(exc_info.value).lower()

        # Invalid: Both configurations
        with pytest.raises(ValidationError) as exc_info:
            VectorStoreSettings(
                provider=VectorStoreProvider.SQLITE_VEC,
                qdrant_config={"url": "http://localhost:6333"},
                sqlite_vec_config={"enabled": True, "database_path": "/tmp/vectors.db"}
            )
        assert "only one configuration" in str(exc_info.value).lower()

    def test_switch_provider(self, tmp_path):
        """Test switching from one provider to another."""
        # Start with Qdrant
        settings = VectorStoreSettings(
            provider=VectorStoreProvider.QDRANT,
            qdrant_config={"url": "http://localhost:6333"}
        )
        assert settings.provider == VectorStoreProvider.QDRANT

        # Switch to SQLite-vec
        settings_dict = settings.model_dump()
        settings_dict["provider"] = VectorStoreProvider.SQLITE_VEC
        settings_dict["qdrant_config"] = None
        settings_dict["sqlite_vec_config"] = {
            "enabled": True,
            "database_path": str(tmp_path / "vectors.db")
        }

        new_settings = VectorStoreSettings(**settings_dict)
        assert new_settings.provider == VectorStoreProvider.SQLITE_VEC
        assert new_settings.sqlite_vec_config is not None
        assert new_settings.qdrant_config is None

    def test_get_active_config(self, tmp_path):
        """Test getting the active configuration based on provider."""
        # Qdrant settings
        qdrant_settings = VectorStoreSettings(
            provider=VectorStoreProvider.QDRANT,
            qdrant_config={"url": "http://localhost:6333"}
        )
        active = qdrant_settings.get_active_config()
        assert active == qdrant_settings.qdrant_config

        # SQLite-vec settings
        sqlite_settings = VectorStoreSettings(
            provider=VectorStoreProvider.SQLITE_VEC,
            sqlite_vec_config={
                "enabled": True,
                "database_path": str(tmp_path / "vectors.db")
            }
        )
        active = sqlite_settings.get_active_config()
        assert active == sqlite_settings.sqlite_vec_config

    def test_serialization_with_sqlite_vec(self, tmp_path):
        """Test settings serialization with SQLite-vec configuration."""
        settings = VectorStoreSettings(
            provider=VectorStoreProvider.SQLITE_VEC,
            sqlite_vec_config={
                "enabled": True,
                "database_path": str(tmp_path / "vectors.db"),
                "vector_dimensions": 768,
                "batch_size": 200
            }
        )

        # Serialize
        settings_dict = settings.model_dump()
        assert settings_dict["provider"] == "sqlite_vec"
        assert settings_dict["sqlite_vec_config"]["vector_dimensions"] == 768
        assert settings_dict["sqlite_vec_config"]["batch_size"] == 200

        # Deserialize
        settings2 = VectorStoreSettings(**settings_dict)
        assert settings2.provider == VectorStoreProvider.SQLITE_VEC
        assert settings2.sqlite_vec_config.vector_dimensions == 768