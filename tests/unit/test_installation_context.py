"""Unit tests for InstallationContext model."""

import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError

from src.models.installation import InstallationContext


class TestInstallationContext:
    """Test cases for InstallationContext model validation and behavior."""

    def test_valid_installation_context_creation(self):
        """Test creating a valid InstallationContext instance."""
        context = InstallationContext(
            install_method="uvx",
            install_date=datetime.now(),
            version="1.0.0",
            python_version="3.13.1",
            uv_version="0.4.0",
            install_path=Path("/usr/local/bin/docbro"),
            is_global=True,
            user_data_dir=Path.home() / ".local" / "share" / "docbro",
            config_dir=Path.home() / ".config" / "docbro",
            cache_dir=Path.home() / ".cache" / "docbro"
        )

        assert context.install_method == "uvx"
        assert context.version == "1.0.0"
        assert context.python_version == "3.13.1"
        assert context.is_global is True
        assert isinstance(context.install_path, Path)

    def test_install_method_validation(self):
        """Test that install_method must be one of allowed values."""
        valid_methods = ["uvx", "manual", "development"]

        for method in valid_methods:
            context = InstallationContext(
                install_method=method,
                install_date=datetime.now(),
                version="1.0.0",
                python_version="3.13.1",
                install_path=Path("/usr/local/bin/docbro"),
                is_global=True,
                user_data_dir=Path.home() / ".local" / "share" / "docbro",
                config_dir=Path.home() / ".config" / "docbro",
                cache_dir=Path.home() / ".cache" / "docbro"
            )
            assert context.install_method == method

        # Test invalid method
        with pytest.raises(ValidationError):
            InstallationContext(
                install_method="invalid",
                install_date=datetime.now(),
                version="1.0.0",
                python_version="3.13.1",
                install_path=Path("/usr/local/bin/docbro"),
                is_global=True,
                user_data_dir=Path.home() / ".local" / "share" / "docbro",
                config_dir=Path.home() / ".config" / "docbro",
                cache_dir=Path.home() / ".cache" / "docbro"
            )

    def test_version_format_validation(self):
        """Test that version must follow semantic versioning."""
        valid_versions = ["1.0.0", "2.1.3", "0.1.0", "10.20.30"]

        for version in valid_versions:
            context = InstallationContext(
                install_method="uvx",
                install_date=datetime.now(),
                version=version,
                python_version="3.13.1",
                install_path=Path("/usr/local/bin/docbro"),
                is_global=True,
                user_data_dir=Path.home() / ".local" / "share" / "docbro",
                config_dir=Path.home() / ".config" / "docbro",
                cache_dir=Path.home() / ".cache" / "docbro"
            )
            assert context.version == version

        # Test invalid version formats
        invalid_versions = ["1.0", "v1.0.0", "1.0.0-alpha", "invalid"]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                InstallationContext(
                    install_method="uvx",
                    install_date=datetime.now(),
                    version=version,
                    python_version="3.13.1",
                    install_path=Path("/usr/local/bin/docbro"),
                    is_global=True,
                    user_data_dir=Path.home() / ".local" / "share" / "docbro",
                    config_dir=Path.home() / ".config" / "docbro",
                    cache_dir=Path.home() / ".cache" / "docbro"
                )

    def test_python_version_validation(self):
        """Test that python_version must be 3.13.x."""
        valid_versions = ["3.13.0", "3.13.1", "3.13.10"]

        for py_version in valid_versions:
            context = InstallationContext(
                install_method="uvx",
                install_date=datetime.now(),
                version="1.0.0",
                python_version=py_version,
                install_path=Path("/usr/local/bin/docbro"),
                is_global=True,
                user_data_dir=Path.home() / ".local" / "share" / "docbro",
                config_dir=Path.home() / ".config" / "docbro",
                cache_dir=Path.home() / ".cache" / "docbro"
            )
            assert context.python_version == py_version

        # Test invalid Python versions
        invalid_versions = ["3.12.0", "3.11.5", "3.14.0", "python3.13"]
        for py_version in invalid_versions:
            with pytest.raises(ValidationError):
                InstallationContext(
                    install_method="uvx",
                    install_date=datetime.now(),
                    version="1.0.0",
                    python_version=py_version,
                    install_path=Path("/usr/local/bin/docbro"),
                    is_global=True,
                    user_data_dir=Path.home() / ".local" / "share" / "docbro",
                    config_dir=Path.home() / ".config" / "docbro",
                    cache_dir=Path.home() / ".cache" / "docbro"
                )

    def test_path_validation(self):
        """Test that paths must be absolute and accessible."""
        # Test with absolute paths (valid)
        context = InstallationContext(
            install_method="uvx",
            install_date=datetime.now(),
            version="1.0.0",
            python_version="3.13.1",
            install_path=Path("/usr/local/bin/docbro").absolute(),
            is_global=True,
            user_data_dir=Path.home().absolute() / "data",
            config_dir=Path.home().absolute() / "config",
            cache_dir=Path.home().absolute() / "cache"
        )

        assert context.install_path.is_absolute()
        assert context.user_data_dir.is_absolute()
        assert context.config_dir.is_absolute()
        assert context.cache_dir.is_absolute()

    def test_json_serialization(self):
        """Test that InstallationContext can be serialized to/from JSON."""
        original = InstallationContext(
            install_method="uvx",
            install_date=datetime(2025, 1, 25, 10, 30, 0),
            version="1.0.0",
            python_version="3.13.1",
            uv_version="0.4.0",
            install_path=Path("/usr/local/bin/docbro"),
            is_global=True,
            user_data_dir=Path.home() / ".local" / "share" / "docbro",
            config_dir=Path.home() / ".config" / "docbro",
            cache_dir=Path.home() / ".cache" / "docbro"
        )

        # Serialize to JSON
        json_data = original.model_dump(mode='json')
        assert isinstance(json_data, dict)
        assert json_data["install_method"] == "uvx"
        assert json_data["version"] == "1.0.0"

        # Deserialize from JSON
        restored = InstallationContext.model_validate(json_data)
        assert restored.install_method == original.install_method
        assert restored.version == original.version
        assert restored.python_version == original.python_version

    def test_optional_uv_version(self):
        """Test that uv_version can be None."""
        context = InstallationContext(
            install_method="manual",
            install_date=datetime.now(),
            version="1.0.0",
            python_version="3.13.1",
            uv_version=None,  # Should be allowed
            install_path=Path("/usr/local/bin/docbro"),
            is_global=True,
            user_data_dir=Path.home() / ".local" / "share" / "docbro",
            config_dir=Path.home() / ".config" / "docbro",
            cache_dir=Path.home() / ".cache" / "docbro"
        )

        assert context.uv_version is None