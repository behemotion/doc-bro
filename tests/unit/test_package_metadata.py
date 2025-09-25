"""Unit tests for PackageMetadata model."""

import pytest
from typing import Dict, List
from pydantic import ValidationError

from src.models.installation import PackageMetadata


class TestPackageMetadata:
    """Test cases for PackageMetadata model validation and behavior."""

    def test_valid_package_metadata_creation(self):
        """Test creating a valid PackageMetadata instance."""
        metadata = PackageMetadata(
            name="docbro",
            version="1.0.0",
            description="Documentation crawler and search tool",
            homepage="https://github.com/user/local-doc-bro",
            repository_url="https://github.com/user/local-doc-bro",
            entry_points={"console_scripts": "docbro = src.cli.main:cli"},
            dependencies=["click>=8.1", "pydantic>=2.0"],
            python_requires=">=3.13",
            install_source="git+https://github.com/user/local-doc-bro"
        )

        assert metadata.name == "docbro"
        assert metadata.version == "1.0.0"
        assert metadata.python_requires == ">=3.13"

    def test_name_immutability(self):
        """Test that name is always 'docbro' and cannot be changed."""
        # Default name should be 'docbro'
        metadata = PackageMetadata(
            version="1.0.0",
            description="Test description",
            homepage="https://example.com",
            repository_url="https://github.com/test/repo",
            entry_points={},
            dependencies=[],
            install_source="test"
        )

        assert metadata.name == "docbro"

        # Trying to set different name should be rejected
        with pytest.raises(ValidationError):
            PackageMetadata(
                name="different-name",
                version="1.0.0",
                description="Test description",
                homepage="https://example.com",
                repository_url="https://github.com/test/repo",
                entry_points={},
                dependencies=[],
                install_source="test"
            )

    def test_version_semver_validation(self):
        """Test that version follows semantic versioning."""
        valid_versions = ["1.0.0", "2.1.3", "0.1.0", "10.20.30"]

        for version in valid_versions:
            metadata = PackageMetadata(
                version=version,
                description="Test description",
                homepage="https://example.com",
                repository_url="https://github.com/test/repo",
                entry_points={},
                dependencies=[],
                install_source="test"
            )
            assert metadata.version == version

        # Test invalid version formats
        invalid_versions = ["1.0", "v1.0.0", "1.0.0-alpha", "invalid"]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                PackageMetadata(
                    version=version,
                    description="Test description",
                    homepage="https://example.com",
                    repository_url="https://github.com/test/repo",
                    entry_points={},
                    dependencies=[],
                    install_source="test"
                )

    def test_url_validation(self):
        """Test that URLs are valid HTTP/HTTPS."""
        valid_urls = [
            "https://github.com/user/repo",
            "http://example.com",
            "https://docs.example.com/path"
        ]

        for url in valid_urls:
            metadata = PackageMetadata(
                version="1.0.0",
                description="Test description",
                homepage=url,
                repository_url=url,
                entry_points={},
                dependencies=[],
                install_source=url
            )
            assert metadata.homepage == url
            assert metadata.repository_url == url

        # Test invalid URLs
        invalid_urls = ["ftp://example.com", "not-a-url", ""]
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                PackageMetadata(
                    version="1.0.0",
                    description="Test description",
                    homepage=url,
                    repository_url="https://github.com/test/repo",
                    entry_points={},
                    dependencies=[],
                    install_source="https://github.com/test/repo"
                )

    def test_python_requires_validation(self):
        """Test that python_requires matches supported version."""
        # Default should be >=3.13
        metadata = PackageMetadata(
            version="1.0.0",
            description="Test description",
            homepage="https://example.com",
            repository_url="https://github.com/test/repo",
            entry_points={},
            dependencies=[],
            install_source="test"
        )

        assert metadata.python_requires == ">=3.13"

        # Should accept valid version specifiers
        valid_requires = [">=3.13", ">=3.13.0", "==3.13.*"]
        for req in valid_requires:
            metadata = PackageMetadata(
                version="1.0.0",
                description="Test description",
                homepage="https://example.com",
                repository_url="https://github.com/test/repo",
                entry_points={},
                dependencies=[],
                python_requires=req,
                install_source="test"
            )
            assert metadata.python_requires == req

    def test_entry_points_dict(self):
        """Test entry_points dictionary structure."""
        entry_points = {
            "console_scripts": "docbro = src.cli.main:cli",
            "gui_scripts": "docbro-gui = src.gui.main:main"
        }

        metadata = PackageMetadata(
            version="1.0.0",
            description="Test description",
            homepage="https://example.com",
            repository_url="https://github.com/test/repo",
            entry_points=entry_points,
            dependencies=[],
            install_source="test"
        )

        assert metadata.entry_points == entry_points
        assert "console_scripts" in metadata.entry_points

    def test_dependencies_list(self):
        """Test dependencies list validation."""
        dependencies = [
            "click>=8.1.0",
            "pydantic>=2.0.0,<3.0.0",
            "httpx~=0.24.0"
        ]

        metadata = PackageMetadata(
            version="1.0.0",
            description="Test description",
            homepage="https://example.com",
            repository_url="https://github.com/test/repo",
            entry_points={},
            dependencies=dependencies,
            install_source="test"
        )

        assert metadata.dependencies == dependencies
        assert len(metadata.dependencies) == 3

    def test_install_source_formats(self):
        """Test various install source formats."""
        valid_sources = [
            "git+https://github.com/user/repo",
            "https://github.com/user/repo/archive/main.zip",
            "/local/path/to/package",
            "."
        ]

        for source in valid_sources:
            metadata = PackageMetadata(
                version="1.0.0",
                description="Test description",
                homepage="https://example.com",
                repository_url="https://github.com/test/repo",
                entry_points={},
                dependencies=[],
                install_source=source
            )
            assert metadata.install_source == source

    def test_json_serialization(self):
        """Test that PackageMetadata can be serialized to/from JSON."""
        original = PackageMetadata(
            name="docbro",
            version="1.0.0",
            description="Documentation crawler and search tool",
            homepage="https://github.com/user/local-doc-bro",
            repository_url="https://github.com/user/local-doc-bro",
            entry_points={"console_scripts": "docbro = src.cli.main:cli"},
            dependencies=["click>=8.1", "pydantic>=2.0"],
            python_requires=">=3.13",
            install_source="git+https://github.com/user/local-doc-bro"
        )

        # Serialize to JSON
        json_data = original.model_dump(mode='json')
        assert isinstance(json_data, dict)
        assert json_data["name"] == "docbro"
        assert json_data["version"] == "1.0.0"
        assert json_data["python_requires"] == ">=3.13"

        # Deserialize from JSON
        restored = PackageMetadata.model_validate(json_data)
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.dependencies == original.dependencies

    def test_from_pyproject_toml_data(self):
        """Test creating PackageMetadata from pyproject.toml data structure."""
        pyproject_data = {
            "name": "docbro",
            "version": "1.0.0",
            "description": "Documentation crawler and search tool",
            "homepage": "https://github.com/user/local-doc-bro",
            "repository_url": "https://github.com/user/local-doc-bro",
            "dependencies": ["click>=8.1.0", "pydantic>=2.0.0"],
            "scripts": {"docbro": "src.cli.main:cli"}
        }

        # Transform scripts to entry_points format
        entry_points = {"console_scripts": f"docbro = {pyproject_data['scripts']['docbro']}"}

        metadata = PackageMetadata(
            name=pyproject_data["name"],
            version=pyproject_data["version"],
            description=pyproject_data["description"],
            homepage=pyproject_data["homepage"],
            repository_url=pyproject_data["repository_url"],
            entry_points=entry_points,
            dependencies=pyproject_data["dependencies"],
            install_source="git+https://github.com/user/local-doc-bro"
        )

        assert metadata.name == "docbro"
        assert len(metadata.dependencies) == 2

    def test_empty_optional_fields(self):
        """Test handling of empty optional fields."""
        metadata = PackageMetadata(
            version="1.0.0",
            description="Minimal package",
            homepage="https://example.com",
            repository_url="https://github.com/test/repo",
            entry_points={},  # Empty dict
            dependencies=[],  # Empty list
            install_source="test"
        )

        assert len(metadata.entry_points) == 0
        assert len(metadata.dependencies) == 0