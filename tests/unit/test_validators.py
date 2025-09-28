"""
Unit tests for settings validators.
"""

import pytest
from pydantic import ValidationError
from src.models.settings import GlobalSettings, ProjectSettings


class TestGlobalSettingsValidators:
    """Test validators for GlobalSettings model."""

    def test_valid_embedding_model(self):
        """Test valid embedding model choices."""
        valid_models = ["mxbai-embed-large", "nomic-embed-text", "all-minilm", "bge-small-en"]

        for model in valid_models:
            settings = GlobalSettings(embedding_model=model)
            assert settings.embedding_model == model

    def test_invalid_embedding_model_raises_error(self):
        """Test invalid embedding model raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GlobalSettings(embedding_model="invalid-model")

        errors = exc_info.value.errors()
        assert any("embedding_model" in str(e) for e in errors)

    def test_crawl_depth_range_validation(self):
        """Test crawl depth range validation."""
        # Valid range
        for depth in [1, 5, 10]:
            settings = GlobalSettings(crawl_depth=depth)
            assert settings.crawl_depth == depth

        # Below minimum
        with pytest.raises(ValidationError):
            GlobalSettings(crawl_depth=0)

        # Above maximum
        with pytest.raises(ValidationError):
            GlobalSettings(crawl_depth=11)

    def test_chunk_size_range_validation(self):
        """Test chunk size range validation."""
        # Valid range
        for size in [100, 1500, 10000]:
            settings = GlobalSettings(chunk_size=size)
            assert settings.chunk_size == size

        # Below minimum
        with pytest.raises(ValidationError):
            GlobalSettings(chunk_size=99)

        # Above maximum
        with pytest.raises(ValidationError):
            GlobalSettings(chunk_size=10001)

    def test_rag_temperature_range_validation(self):
        """Test RAG temperature range validation."""
        # Valid range
        for temp in [0.0, 0.5, 1.0]:
            settings = GlobalSettings(rag_temperature=temp)
            assert settings.rag_temperature == temp

        # Below minimum
        with pytest.raises(ValidationError):
            GlobalSettings(rag_temperature=-0.1)

        # Above maximum
        with pytest.raises(ValidationError):
            GlobalSettings(rag_temperature=1.1)

    def test_storage_path_expansion(self):
        """Test storage path expands user directory."""
        settings = GlobalSettings(vector_storage="~/test/path")
        assert "~" not in settings.vector_storage
        assert "/test/path" in settings.vector_storage


class TestProjectSettingsValidators:
    """Test validators for ProjectSettings model."""

    def test_optional_fields_can_be_none(self):
        """Test all ProjectSettings fields are optional."""
        settings = ProjectSettings()
        assert settings.embedding_model is None
        assert settings.crawl_depth is None
        assert settings.chunk_size is None

    def test_modified_fields_tracking(self):
        """Test modified fields are tracked correctly."""
        settings = ProjectSettings()
        assert len(settings._modified_fields) == 0

        settings.set_field("crawl_depth", 5)
        assert settings.crawl_depth == 5
        assert settings.is_modified("crawl_depth")
        assert not settings.is_modified("chunk_size")

    def test_project_settings_validation(self):
        """Test ProjectSettings validates same as GlobalSettings."""
        # Valid values
        settings = ProjectSettings(
            crawl_depth=5,
            chunk_size=2000,
            rag_temperature=0.7
        )
        assert settings.crawl_depth == 5

        # Invalid values should still raise errors
        with pytest.raises(ValidationError):
            ProjectSettings(crawl_depth=20)  # Exceeds max

        with pytest.raises(ValidationError):
            ProjectSettings(chunk_size=50)  # Below min


class TestEffectiveSettingsMerging:
    """Test EffectiveSettings merging logic."""

    def test_merge_with_no_overrides(self):
        """Test merging with no project overrides uses global defaults."""
        from src.models.settings import EffectiveSettings

        global_settings = GlobalSettings(crawl_depth=3, chunk_size=1500)
        effective = EffectiveSettings.from_configs(global_settings, None)

        assert effective.crawl_depth == 3
        assert effective.chunk_size == 1500

    def test_merge_with_partial_overrides(self):
        """Test partial overrides merge correctly."""
        from src.models.settings import EffectiveSettings

        global_settings = GlobalSettings(
            crawl_depth=3,
            chunk_size=1500,
            rag_temperature=0.7
        )

        project_settings = ProjectSettings(crawl_depth=7)
        effective = EffectiveSettings.from_configs(global_settings, project_settings)

        assert effective.crawl_depth == 7  # Overridden
        assert effective.chunk_size == 1500  # Inherited
        assert effective.rag_temperature == 0.7  # Inherited

    def test_non_overridable_fields_preserved(self):
        """Test non-overridable fields are not changed."""
        from src.models.settings import EffectiveSettings, NON_OVERRIDABLE_FIELDS
        from pathlib import Path

        global_settings = GlobalSettings()
        project_settings = ProjectSettings()

        # Even if project had these fields, they shouldn't change
        effective = EffectiveSettings.from_configs(global_settings, project_settings)

        for field in NON_OVERRIDABLE_FIELDS:
            global_value = getattr(global_settings, field)
            effective_value = getattr(effective, field)

            # For path fields, compare expanded paths
            if field == "vector_storage" and "~" in str(global_value):
                assert Path(effective_value).expanduser() == Path(global_value).expanduser()
            else:
                assert effective_value == global_value