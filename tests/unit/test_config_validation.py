"""Unit tests for configuration hierarchy and validation."""

import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
import yaml
import os

from src.logic.projects.models.config import ProjectConfig
from src.logic.projects.models.project import ProjectType
from src.logic.projects.core.config_manager import ConfigManager


class TestConfigHierarchy:
    """Test configuration hierarchy: global -> project -> effective."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def global_config(self) -> Dict[str, Any]:
        """Sample global configuration."""
        return {
            "project_defaults": {
                "max_file_size": 10485760,  # 10MB
                "chunk_size": 500,
                "chunk_overlap": 50,
                "embedding_model": "mxbai-embed-large",
                "rate_limit": 1.0,
                "allowed_formats": {
                    "documents": ["pdf", "docx", "txt", "md"],
                    "images": ["jpg", "png", "gif"],
                    "archives": ["zip", "tar", "gz"],
                }
            }
        }

    @pytest.fixture
    def project_config(self) -> Dict[str, Any]:
        """Sample project-specific configuration."""
        return {
            "max_file_size": 52428800,  # 50MB override
            "chunk_size": 1000,  # Override
            "allowed_formats": {
                "documents": ["pdf", "txt"],  # Restricted list
            }
        }

    def test_config_hierarchy_merge(self, global_config, project_config):
        """Test that project config correctly overrides global config."""
        config_manager = ConfigManager()

        # Simulate merging configs
        effective_config = config_manager.merge_configs(global_config["project_defaults"], project_config)

        # Check overrides
        assert effective_config["max_file_size"] == 52428800  # Project override
        assert effective_config["chunk_size"] == 1000  # Project override

        # Check inherited values
        assert effective_config["chunk_overlap"] == 50  # From global
        assert effective_config["embedding_model"] == "mxbai-embed-large"  # From global
        assert effective_config["rate_limit"] == 1.0  # From global

        # Check nested merge (allowed_formats)
        assert effective_config["allowed_formats"]["documents"] == ["pdf", "txt"]  # Project override
        assert effective_config["allowed_formats"]["images"] == ["jpg", "png", "gif"]  # From global
        assert effective_config["allowed_formats"]["archives"] == ["zip", "tar", "gz"]  # From global

    def test_environment_variable_override(self, global_config):
        """Test that environment variables override all configs."""
        config_manager = ConfigManager()

        with patch.dict(os.environ, {
            "DOCBRO_CHUNK_SIZE": "2000",
            "DOCBRO_EMBEDDING_MODEL": "custom-model",
            "DOCBRO_DEFAULT_RATE_LIMIT": "2.5",
        }):
            effective_config = config_manager.apply_env_overrides(global_config["project_defaults"])

            assert effective_config["chunk_size"] == 2000
            assert effective_config["embedding_model"] == "custom-model"
            assert effective_config["rate_limit"] == 2.5

    def test_config_validation_for_project_type(self):
        """Test that configs are validated against project type constraints."""
        # Test invalid config for crawling project
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.CRAWLING,
                chunk_size=500,  # Valid for DATA projects only
                enable_compression=True  # Valid for STORAGE projects only
            )
        assert "not valid for CRAWLING project" in str(exc_info.value)

        # Test valid config for data project
        config = ProjectConfig(
            project_type=ProjectType.DATA,
            chunk_size=500,
            embedding_model="mxbai-embed-large",
            vector_store_type="qdrant"
        )
        assert config.chunk_size == 500

        # Test valid config for storage project
        config = ProjectConfig(
            project_type=ProjectType.STORAGE,
            enable_compression=True,
            auto_tagging=True,
            full_text_indexing=False
        )
        assert config.enable_compression is True

    def test_config_file_loading_priority(self, temp_config_dir):
        """Test configuration file loading priority."""
        config_manager = ConfigManager()

        # Create config files in different locations
        global_config_path = temp_config_dir / "global" / "settings.yaml"
        project_config_path = temp_config_dir / "project" / "settings.yaml"

        global_config_path.parent.mkdir(parents=True)
        project_config_path.parent.mkdir(parents=True)

        # Write global config
        with open(global_config_path, 'w') as f:
            yaml.dump({
                "max_file_size": 10485760,
                "chunk_size": 500,
            }, f)

        # Write project config
        with open(project_config_path, 'w') as f:
            yaml.dump({
                "max_file_size": 52428800,
            }, f)

        # Load and merge configs
        configs = config_manager.load_configs([global_config_path, project_config_path])

        assert configs["max_file_size"] == 52428800  # Project override
        assert configs["chunk_size"] == 500  # From global

    def test_invalid_config_values(self):
        """Test validation of invalid configuration values."""
        config_manager = ConfigManager()

        # Test negative file size
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config({"max_file_size": -1})
        assert "must be positive" in str(exc_info.value).lower()

        # Test invalid chunk size
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config({"chunk_size": 0})
        assert "must be positive" in str(exc_info.value).lower()

        # Test invalid rate limit
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config({"rate_limit": -1.0})
        assert "must be positive" in str(exc_info.value).lower()

        # Test invalid embedding model
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config({"embedding_model": ""})
        assert "cannot be empty" in str(exc_info.value).lower()


class TestProjectConfigValidation:
    """Test project-specific configuration validation."""

    def test_crawling_project_config_validation(self):
        """Test validation for crawling project configurations."""
        # Valid crawling config
        config = ProjectConfig(
            project_type=ProjectType.CRAWLING,
            crawl_depth=3,
            rate_limit=1.0,
            user_agent="DocBro/1.0",
            max_file_size=10485760
        )
        assert config.crawl_depth == 3
        assert config.rate_limit == 1.0

        # Test invalid crawl depth
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.CRAWLING,
                crawl_depth=-1
            )
        assert "crawl_depth must be positive" in str(exc_info.value).lower()

        # Test invalid rate limit
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.CRAWLING,
                rate_limit=0
            )
        assert "rate_limit must be positive" in str(exc_info.value).lower()

    def test_data_project_config_validation(self):
        """Test validation for data project configurations."""
        # Valid data config
        config = ProjectConfig(
            project_type=ProjectType.DATA,
            chunk_size=500,
            chunk_overlap=50,
            embedding_model="mxbai-embed-large",
            vector_store_type="qdrant"
        )
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50

        # Test chunk overlap larger than chunk size
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.DATA,
                chunk_size=100,
                chunk_overlap=150
            )
        assert "chunk_overlap cannot exceed chunk_size" in str(exc_info.value).lower()

        # Test invalid vector store type
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.DATA,
                vector_store_type="invalid_store"
            )
        assert "invalid vector store type" in str(exc_info.value).lower()

    def test_storage_project_config_validation(self):
        """Test validation for storage project configurations."""
        # Valid storage config
        config = ProjectConfig(
            project_type=ProjectType.STORAGE,
            enable_compression=True,
            auto_tagging=False,
            full_text_indexing=True,
            max_file_size=104857600  # 100MB
        )
        assert config.enable_compression is True
        assert config.auto_tagging is False

        # Test conflicting settings
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.STORAGE,
                enable_compression=True,
                full_text_indexing=True,  # Can't index compressed files
                compression_level=10  # Invalid level
            )
        assert "cannot enable full_text_indexing with compression" in str(exc_info.value).lower()

    def test_allowed_formats_validation(self):
        """Test validation of allowed file formats."""
        # Test valid formats
        config = ProjectConfig(
            project_type=ProjectType.DATA,
            allowed_formats=["pdf", "docx", "txt", "md"]
        )
        assert "pdf" in config.allowed_formats

        # Test invalid format for project type
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.DATA,
                allowed_formats=["exe", "dll", "bat"]  # Executable formats not allowed
            )
        assert "not allowed for DATA project" in str(exc_info.value).lower()

        # Test empty formats list
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig(
                project_type=ProjectType.STORAGE,
                allowed_formats=[]
            )
        assert "at least one format must be allowed" in str(exc_info.value).lower()


class TestConfigPersistence:
    """Test configuration persistence and retrieval."""

    @pytest.fixture
    def config_manager(self):
        """Create config manager instance."""
        return ConfigManager()

    def test_save_project_config(self, config_manager, temp_config_dir):
        """Test saving project configuration to disk."""
        project_name = "test-project"
        config = ProjectConfig(
            project_type=ProjectType.DATA,
            chunk_size=1000,
            embedding_model="custom-model"
        )

        config_path = temp_config_dir / f"{project_name}.yaml"
        config_manager.save_config(config, config_path)

        # Verify file exists
        assert config_path.exists()

        # Load and verify content
        with open(config_path, 'r') as f:
            saved_config = yaml.safe_load(f)

        assert saved_config["project_type"] == "data"
        assert saved_config["chunk_size"] == 1000
        assert saved_config["embedding_model"] == "custom-model"

    def test_load_project_config(self, config_manager, temp_config_dir):
        """Test loading project configuration from disk."""
        config_path = temp_config_dir / "project.yaml"

        # Write config file
        with open(config_path, 'w') as f:
            yaml.dump({
                "project_type": "storage",
                "enable_compression": True,
                "max_file_size": 52428800
            }, f)

        # Load config
        loaded_config = config_manager.load_project_config(config_path)

        assert loaded_config.project_type == ProjectType.STORAGE
        assert loaded_config.enable_compression is True
        assert loaded_config.max_file_size == 52428800

    def test_config_migration(self, config_manager, temp_config_dir):
        """Test migration of old config format to new format."""
        old_config_path = temp_config_dir / "old.yaml"

        # Write old format config
        with open(old_config_path, 'w') as f:
            yaml.dump({
                "type": "data",  # Old field name
                "max_size": 10485760,  # Old field name
                "chunk": 500  # Old field name
            }, f)

        # Load and migrate
        migrated_config = config_manager.migrate_config(old_config_path)

        assert migrated_config.project_type == ProjectType.DATA
        assert migrated_config.max_file_size == 10485760
        assert migrated_config.chunk_size == 500


class TestConfigDefaults:
    """Test configuration default values."""

    def test_global_defaults(self):
        """Test that global defaults are applied correctly."""
        config_manager = ConfigManager()
        defaults = config_manager.get_global_defaults()

        # Check required defaults exist
        assert "max_file_size" in defaults
        assert "chunk_size" in defaults
        assert "chunk_overlap" in defaults
        assert "embedding_model" in defaults
        assert "rate_limit" in defaults
        assert "allowed_formats" in defaults

        # Check default values
        assert defaults["max_file_size"] == 10485760  # 10MB
        assert defaults["chunk_size"] == 500
        assert defaults["chunk_overlap"] == 50
        assert defaults["embedding_model"] == "mxbai-embed-large"
        assert defaults["rate_limit"] == 1.0

    def test_project_type_defaults(self):
        """Test that each project type has appropriate defaults."""
        config_manager = ConfigManager()

        # Crawling defaults
        crawling_defaults = config_manager.get_project_type_defaults(ProjectType.CRAWLING)
        assert crawling_defaults["crawl_depth"] == 3
        assert crawling_defaults["user_agent"] == "DocBro/1.0"

        # Data defaults
        data_defaults = config_manager.get_project_type_defaults(ProjectType.DATA)
        assert data_defaults["vector_store_type"] == "qdrant"
        assert data_defaults["chunk_size"] == 500

        # Storage defaults
        storage_defaults = config_manager.get_project_type_defaults(ProjectType.STORAGE)
        assert storage_defaults["enable_compression"] is False
        assert storage_defaults["auto_tagging"] is True
        assert storage_defaults["full_text_indexing"] is True

    def test_effective_config_calculation(self):
        """Test calculation of effective configuration."""
        config_manager = ConfigManager()

        global_config = {
            "max_file_size": 10485760,
            "chunk_size": 500,
            "rate_limit": 1.0
        }

        project_config = {
            "max_file_size": 52428800,  # Override
        }

        env_overrides = {
            "DOCBRO_CHUNK_SIZE": "1000"  # Override
        }

        with patch.dict(os.environ, env_overrides):
            effective = config_manager.get_effective_config(
                global_config,
                project_config,
                ProjectType.DATA
            )

            assert effective["max_file_size"] == 52428800  # Project override
            assert effective["chunk_size"] == 1000  # Env override
            assert effective["rate_limit"] == 1.0  # Global default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])