"""Unit tests for SchemaVersion tracking."""

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from src.models.schema_version import SchemaVersion


class TestSchemaVersionModel:
    """Test SchemaVersion model functionality."""

    def test_schema_version_creation(self):
        """Test creating a SchemaVersion instance."""
        version = SchemaVersion(
            version=1,
            name="Test Version",
            description="A test schema version"
        )

        assert version.version == 1
        assert version.name == "Test Version"
        assert version.description == "A test schema version"
        assert isinstance(version.introduced_at, datetime)
        assert version.fields_added == []
        assert version.fields_removed == []
        assert version.fields_changed == []

    def test_schema_version_with_field_changes(self):
        """Test creating a SchemaVersion with field changes."""
        version = SchemaVersion(
            version=2,
            name="Updated Version",
            description="Version with field changes",
            fields_added=["new_field1", "new_field2"],
            fields_removed=["old_field"],
            fields_changed=["modified_field"]
        )

        assert version.fields_added == ["new_field1", "new_field2"]
        assert version.fields_removed == ["old_field"]
        assert version.fields_changed == ["modified_field"]

    def test_schema_version_validation_positive_version(self):
        """Test that version must be positive."""
        # Valid positive versions
        for valid_version in [1, 2, 10, 100]:
            version = SchemaVersion(
                version=valid_version,
                name="Test",
                description="Test"
            )
            assert version.version == valid_version

        # Invalid non-positive versions
        for invalid_version in [0, -1, -10]:
            with pytest.raises(ValidationError) as exc_info:
                SchemaVersion(
                    version=invalid_version,
                    name="Test",
                    description="Test"
                )
            assert "greater than or equal to 1" in str(exc_info.value)

    def test_schema_version_validation_name(self):
        """Test name validation."""
        # Valid names
        valid_names = ["Version 1", "v", "A" * 100, "Test-Version_1"]
        for name in valid_names:
            version = SchemaVersion(version=1, name=name, description="Test")
            assert version.name == name

        # Invalid names
        invalid_names = ["", "   "]
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                SchemaVersion(version=1, name=name, description="Test")
            assert "at least 1 characters" in str(exc_info.value)

    def test_custom_timestamp(self):
        """Test setting a custom introduced_at timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        version = SchemaVersion(
            version=1,
            name="Custom Time",
            description="Version with custom timestamp",
            introduced_at=custom_time
        )

        assert version.introduced_at == custom_time

    def test_to_summary(self):
        """Test the to_summary method."""
        version = SchemaVersion(
            version=3,
            name="Current Version",
            description="The current unified schema",
            fields_added=["schema_version", "compatibility_status"],
            fields_removed=["old_field"],
            fields_changed=["settings"]
        )

        summary = version.to_summary()

        assert summary["version"] == 3
        assert summary["name"] == "Current Version"
        assert summary["description"] == "The current unified schema"
        assert isinstance(summary["introduced_at"], str)
        assert summary["is_current"] == (version.version == SchemaVersion.CURRENT_VERSION)
        assert summary["changes"]["added"] == ["schema_version", "compatibility_status"]
        assert summary["changes"]["removed"] == ["old_field"]
        assert summary["changes"]["changed"] == ["settings"]


class TestSchemaVersionClassMethods:
    """Test SchemaVersion class methods."""

    def test_get_current_version(self):
        """Test getting the current version."""
        current = SchemaVersion.get_current_version()
        assert isinstance(current, int)
        assert current > 0
        assert current == SchemaVersion.CURRENT_VERSION

    def test_current_version_constant(self):
        """Test the CURRENT_VERSION constant."""
        assert hasattr(SchemaVersion, 'CURRENT_VERSION')
        assert isinstance(SchemaVersion.CURRENT_VERSION, int)
        assert SchemaVersion.CURRENT_VERSION == 3  # Current unified schema version

    def test_get_version_history(self):
        """Test getting the complete version history."""
        history = SchemaVersion.get_version_history()

        # Should have at least the three known versions
        assert len(history) >= 3

        # Should be instances of SchemaVersion
        for version in history:
            assert isinstance(version, SchemaVersion)

        # Should be ordered by version number
        versions = [v.version for v in history]
        assert versions == sorted(versions)

        # Should start from version 1
        assert history[0].version == 1

        # Should include current version
        current_versions = [v for v in history if v.version == SchemaVersion.CURRENT_VERSION]
        assert len(current_versions) == 1

    def test_version_history_content(self):
        """Test the content of version history."""
        history = SchemaVersion.get_version_history()
        history_by_version = {v.version: v for v in history}

        # Version 1 - Original crawler schema
        v1 = history_by_version[1]
        assert v1.name == "Original Crawler Schema"
        assert "crawler-focused" in v1.description.lower()
        assert "total_pages" in v1.fields_added
        assert "crawl_depth" in v1.fields_added
        assert len(v1.fields_removed) == 0  # First version has no removed fields

        # Version 2 - Project logic schema
        v2 = history_by_version[2]
        assert v2.name == "Project Logic Schema"
        assert "type-based" in v2.description.lower()
        assert "type" in v2.fields_added
        assert "settings" in v2.fields_added
        assert "total_pages" in v2.fields_removed

        # Version 3 - Unified schema
        v3 = history_by_version[3]
        assert v3.name == "Unified Schema"
        assert "unified" in v3.description.lower()
        assert "schema_version" in v3.fields_added
        assert "compatibility_status" in v3.fields_added
        assert "statistics" in v3.fields_added

    def test_get_version_info_valid(self):
        """Test getting info for valid version numbers."""
        # Test getting info for each version in history
        history = SchemaVersion.get_version_history()
        for expected_version in history:
            retrieved = SchemaVersion.get_version_info(expected_version.version)
            assert retrieved is not None
            assert retrieved.version == expected_version.version
            assert retrieved.name == expected_version.name
            assert retrieved.description == expected_version.description

    def test_get_version_info_invalid(self):
        """Test getting info for invalid version numbers."""
        invalid_versions = [0, -1, 99, 100, 1000]
        for version in invalid_versions:
            info = SchemaVersion.get_version_info(version)
            assert info is None

    def test_is_current_version(self):
        """Test checking if a version is the current version."""
        # Current version should return True
        assert SchemaVersion.is_current_version(SchemaVersion.CURRENT_VERSION) is True

        # Other versions should return False
        other_versions = [1, 2, 4, 5, 10]
        for version in other_versions:
            if version != SchemaVersion.CURRENT_VERSION:
                assert SchemaVersion.is_current_version(version) is False

    def test_is_compatible_version(self):
        """Test checking version compatibility."""
        # Only current version should be compatible
        assert SchemaVersion.is_compatible_version(SchemaVersion.CURRENT_VERSION) is True

        # All other versions should be incompatible
        incompatible_versions = [1, 2, 4, 5, 10]
        for version in incompatible_versions:
            if version != SchemaVersion.CURRENT_VERSION:
                assert SchemaVersion.is_compatible_version(version) is False

    def test_can_migrate_from(self):
        """Test migration possibility checking."""
        # Currently, no automatic migration is supported
        test_versions = [1, 2, 3, 4, 5]
        for version in test_versions:
            assert SchemaVersion.can_migrate_from(version) is False

    def test_requires_recreation(self):
        """Test recreation requirement checking."""
        # Current version should not require recreation
        assert SchemaVersion.requires_recreation(SchemaVersion.CURRENT_VERSION) is False

        # All other versions should require recreation
        other_versions = [1, 2, 4, 5, 10]
        for version in other_versions:
            if version != SchemaVersion.CURRENT_VERSION:
                assert SchemaVersion.requires_recreation(version) is True


class TestSchemaVersionIntegration:
    """Test SchemaVersion integration scenarios."""

    def test_version_comparison_logic(self):
        """Test various version comparison scenarios."""
        current = SchemaVersion.CURRENT_VERSION

        # Test with versions from history
        history = SchemaVersion.get_version_history()
        for version_info in history:
            version = version_info.version

            # Test all comparison methods for consistency
            is_current = SchemaVersion.is_current_version(version)
            is_compatible = SchemaVersion.is_compatible_version(version)
            requires_recreation = SchemaVersion.requires_recreation(version)

            if version == current:
                assert is_current is True
                assert is_compatible is True
                assert requires_recreation is False
            else:
                assert is_current is False
                assert is_compatible is False
                assert requires_recreation is True

    def test_version_history_completeness(self):
        """Test that version history includes all expected versions."""
        history = SchemaVersion.get_version_history()
        versions = [v.version for v in history]

        # Should include versions 1, 2, and current (3)
        assert 1 in versions
        assert 2 in versions
        assert SchemaVersion.CURRENT_VERSION in versions

        # Should not have gaps in version sequence
        sorted_versions = sorted(versions)
        for i in range(1, len(sorted_versions)):
            # Allow for non-consecutive versions in the future
            assert sorted_versions[i] > sorted_versions[i-1]

    def test_version_history_immutability(self):
        """Test that version history is consistent across calls."""
        history1 = SchemaVersion.get_version_history()
        history2 = SchemaVersion.get_version_history()

        # Should return identical data
        assert len(history1) == len(history2)

        for i in range(len(history1)):
            v1, v2 = history1[i], history2[i]
            assert v1.version == v2.version
            assert v1.name == v2.name
            assert v1.description == v2.description
            assert v1.fields_added == v2.fields_added
            assert v1.fields_removed == v2.fields_removed
            assert v1.fields_changed == v2.fields_changed

    def test_summary_includes_current_flag(self):
        """Test that summary correctly identifies current version."""
        history = SchemaVersion.get_version_history()

        current_count = 0
        for version_info in history:
            summary = version_info.to_summary()
            is_current = summary["is_current"]

            if version_info.version == SchemaVersion.CURRENT_VERSION:
                assert is_current is True
                current_count += 1
            else:
                assert is_current is False

        # Should have exactly one current version
        assert current_count == 1

    def test_field_change_tracking(self):
        """Test that field changes are properly tracked across versions."""
        history = SchemaVersion.get_version_history()
        history_by_version = {v.version: v for v in history}

        # Check specific field evolution
        # total_pages: added in v1, removed in v2, re-added in v3 (via statistics)
        v1 = history_by_version[1]
        v2 = history_by_version[2]

        assert "total_pages" in v1.fields_added
        assert "total_pages" in v2.fields_removed

        # settings: added in v2, changed in v3
        assert "settings" in v2.fields_added
        if 3 in history_by_version:
            v3 = history_by_version[3]
            assert "settings" in v3.fields_changed

    def test_version_naming_convention(self):
        """Test that version names follow expected conventions."""
        history = SchemaVersion.get_version_history()

        for version_info in history:
            # Names should be meaningful and non-empty
            assert len(version_info.name) > 0
            assert not version_info.name.isspace()

            # Names should contain version-related terms
            name_lower = version_info.name.lower()
            version_terms = ['schema', 'version', 'crawler', 'logic', 'unified']
            assert any(term in name_lower for term in version_terms)

    def test_description_completeness(self):
        """Test that version descriptions are complete and informative."""
        history = SchemaVersion.get_version_history()

        for version_info in history:
            # Descriptions should be meaningful
            assert len(version_info.description) > 10
            assert not version_info.description.isspace()

            # Should describe what the version contains or changes
            description_lower = version_info.description.lower()
            descriptive_terms = ['schema', 'project', 'support', 'operation', 'field', 'change']
            assert any(term in description_lower for term in descriptive_terms)


class TestSchemaVersionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extreme_version_numbers(self):
        """Test behavior with extreme version numbers."""
        extreme_versions = [0, -1, 1000000, -1000000]

        for version in extreme_versions:
            # These should not be in history
            assert SchemaVersion.get_version_info(version) is None

            # These should follow consistent logic
            is_current = SchemaVersion.is_current_version(version)
            is_compatible = SchemaVersion.is_compatible_version(version)
            requires_recreation = SchemaVersion.requires_recreation(version)
            can_migrate = SchemaVersion.can_migrate_from(version)

            if version == SchemaVersion.CURRENT_VERSION:
                assert is_current is True
                assert is_compatible is True
                assert requires_recreation is False
            else:
                assert is_current is False
                assert is_compatible is False
                assert requires_recreation is True

            # Migration is currently not supported for any version
            assert can_migrate is False

    def test_version_info_consistency(self):
        """Test consistency between version info and class methods."""
        history = SchemaVersion.get_version_history()

        for version_info in history:
            version = version_info.version

            # get_version_info should return identical data
            retrieved = SchemaVersion.get_version_info(version)
            assert retrieved is not None
            assert retrieved.version == version_info.version
            assert retrieved.name == version_info.name

            # Summary should be consistent with version info
            summary = version_info.to_summary()
            assert summary["version"] == version
            assert summary["name"] == version_info.name

    def test_empty_field_lists(self):
        """Test handling of empty field change lists."""
        # Create a version with empty field lists
        version = SchemaVersion(
            version=10,
            name="Empty Changes",
            description="Version with no field changes",
            fields_added=[],
            fields_removed=[],
            fields_changed=[]
        )

        summary = version.to_summary()
        assert summary["changes"]["added"] == []
        assert summary["changes"]["removed"] == []
        assert summary["changes"]["changed"] == []

    def test_large_field_lists(self):
        """Test handling of large field change lists."""
        large_list = [f"field_{i}" for i in range(100)]

        version = SchemaVersion(
            version=20,
            name="Many Changes",
            description="Version with many field changes",
            fields_added=large_list,
            fields_removed=large_list[:50],
            fields_changed=large_list[50:]
        )

        assert len(version.fields_added) == 100
        assert len(version.fields_removed) == 50
        assert len(version.fields_changed) == 50

        summary = version.to_summary()
        assert len(summary["changes"]["added"]) == 100
        assert len(summary["changes"]["removed"]) == 50
        assert len(summary["changes"]["changed"]) == 50

    def test_unicode_in_names_and_descriptions(self):
        """Test handling of unicode characters in names and descriptions."""
        unicode_version = SchemaVersion(
            version=30,
            name="Version avec caractères spéciaux 中文",
            description="Description with émojis 🚀 and unicode 测试",
            fields_added=["field_with_émoji_🎯"]
        )

        # Should handle unicode gracefully
        assert "avec" in unicode_version.name
        assert "🚀" in unicode_version.description
        assert "🎯" in unicode_version.fields_added[0]

        # Summary should preserve unicode
        summary = unicode_version.to_summary()
        assert "🚀" in summary["description"]
        assert "🎯" in summary["changes"]["added"][0]