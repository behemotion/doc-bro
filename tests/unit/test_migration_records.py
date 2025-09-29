"""Unit tests for migration record creation and tracking validation."""

import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from src.models.migration_record import ProjectMigrationRecord, MigrationOperation


class TestMigrationOperation:
    """Test MigrationOperation enum functionality."""

    def test_migration_operation_values(self):
        """Test that migration operations have correct values."""
        assert MigrationOperation.RECREATION.value == "recreation"
        assert MigrationOperation.UPGRADE.value == "upgrade"
        assert MigrationOperation.VALIDATION.value == "validation"

    def test_migration_operation_string_representation(self):
        """Test string representation of migration operations."""
        assert str(MigrationOperation.RECREATION) == "recreation"
        assert str(MigrationOperation.UPGRADE) == "upgrade"
        assert str(MigrationOperation.VALIDATION) == "validation"

    def test_migration_operation_enum_members(self):
        """Test that all expected enum members exist."""
        operations = list(MigrationOperation)
        assert len(operations) == 3
        assert MigrationOperation.RECREATION in operations
        assert MigrationOperation.UPGRADE in operations
        assert MigrationOperation.VALIDATION in operations


class TestProjectMigrationRecordModel:
    """Test ProjectMigrationRecord model functionality."""

    def test_minimal_migration_record_creation(self):
        """Test creating a migration record with minimal required fields."""
        record = ProjectMigrationRecord(
            project_id="test-project-id",
            project_name="test-project",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3
        )

        assert record.project_id == "test-project-id"
        assert record.project_name == "test-project"
        assert record.operation == MigrationOperation.RECREATION
        assert record.from_schema_version == 1
        assert record.to_schema_version == 3
        assert isinstance(record.id, str)
        assert len(record.id) == 36  # UUID format
        assert isinstance(record.started_at, datetime)
        assert record.completed_at is None
        assert record.success is False
        assert record.error_message is None
        assert record.preserved_settings == {}
        assert record.preserved_metadata == {}
        assert record.data_size_bytes == 0
        assert record.user_initiated is True
        assert record.initiated_by_command == "unknown"

    def test_complete_migration_record_creation(self):
        """Test creating a migration record with all fields."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        completion_time = datetime(2023, 1, 1, 12, 0, 30)

        record = ProjectMigrationRecord(
            project_id="full-test-id",
            project_name="full-test-project",
            operation=MigrationOperation.UPGRADE,
            from_schema_version=2,
            to_schema_version=3,
            started_at=custom_time,
            completed_at=completion_time,
            success=True,
            error_message=None,
            preserved_settings={"setting1": "value1", "setting2": 42},
            preserved_metadata={"meta1": "data1", "description": "test"},
            data_size_bytes=1048576,
            user_initiated=False,
            initiated_by_command="automated migration"
        )

        assert record.started_at == custom_time
        assert record.completed_at == completion_time
        assert record.success is True
        assert record.preserved_settings == {"setting1": "value1", "setting2": 42}
        assert record.preserved_metadata == {"meta1": "data1", "description": "test"}
        assert record.data_size_bytes == 1048576
        assert record.user_initiated is False
        assert record.initiated_by_command == "automated migration"

    def test_field_validation_project_name(self):
        """Test project name validation."""
        # Valid names
        valid_names = ["test", "a", "project-name", "project_with_underscores", "Project 123"]
        for name in valid_names:
            record = ProjectMigrationRecord(
                project_id="test-id",
                project_name=name,
                operation=MigrationOperation.RECREATION,
                from_schema_version=1,
                to_schema_version=3
            )
            assert record.project_name == name

        # Invalid names
        invalid_names = ["", "   "]
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ProjectMigrationRecord(
                    project_id="test-id",
                    project_name=name,
                    operation=MigrationOperation.RECREATION,
                    from_schema_version=1,
                    to_schema_version=3
                )
            assert "at least 1 characters" in str(exc_info.value)

    def test_field_validation_schema_versions(self):
        """Test schema version validation."""
        # Valid versions
        valid_versions = [1, 2, 3, 10, 100]
        for version in valid_versions:
            record = ProjectMigrationRecord(
                project_id="test-id",
                project_name="test",
                operation=MigrationOperation.RECREATION,
                from_schema_version=version,
                to_schema_version=version
            )
            assert record.from_schema_version == version
            assert record.to_schema_version == version

        # Invalid versions
        invalid_versions = [0, -1, -10]
        for version in invalid_versions:
            with pytest.raises(ValidationError) as exc_info:
                ProjectMigrationRecord(
                    project_id="test-id",
                    project_name="test",
                    operation=MigrationOperation.RECREATION,
                    from_schema_version=version,
                    to_schema_version=3
                )
            assert "greater than or equal to 1" in str(exc_info.value)

            with pytest.raises(ValidationError) as exc_info:
                ProjectMigrationRecord(
                    project_id="test-id",
                    project_name="test",
                    operation=MigrationOperation.RECREATION,
                    from_schema_version=1,
                    to_schema_version=version
                )
            assert "greater than or equal to 1" in str(exc_info.value)

    def test_field_validation_data_size(self):
        """Test data size validation."""
        # Valid sizes
        valid_sizes = [0, 1, 1024, 1048576, 1073741824]
        for size in valid_sizes:
            record = ProjectMigrationRecord(
                project_id="test-id",
                project_name="test",
                operation=MigrationOperation.RECREATION,
                from_schema_version=1,
                to_schema_version=3,
                data_size_bytes=size
            )
            assert record.data_size_bytes == size

        # Invalid sizes
        invalid_sizes = [-1, -100, -1024]
        for size in invalid_sizes:
            with pytest.raises(ValidationError) as exc_info:
                ProjectMigrationRecord(
                    project_id="test-id",
                    project_name="test",
                    operation=MigrationOperation.RECREATION,
                    from_schema_version=1,
                    to_schema_version=3,
                    data_size_bytes=size
                )
            assert "greater than or equal to 0" in str(exc_info.value)


class TestProjectMigrationRecordMethods:
    """Test ProjectMigrationRecord instance methods."""

    @pytest.fixture
    def sample_record(self):
        """Create a sample migration record for testing."""
        return ProjectMigrationRecord(
            project_id="sample-id",
            project_name="sample-project",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3,
            preserved_settings={"setting1": "value1"},
            preserved_metadata={"meta1": "data1"}
        )

    def test_mark_completed_success(self, sample_record):
        """Test marking migration as completed successfully."""
        assert sample_record.completed_at is None
        assert sample_record.success is False
        assert sample_record.error_message is None

        sample_record.mark_completed(success=True)

        assert sample_record.completed_at is not None
        assert isinstance(sample_record.completed_at, datetime)
        assert sample_record.success is True
        assert sample_record.error_message is None

    def test_mark_completed_with_error(self, sample_record):
        """Test marking migration as completed with error."""
        error_msg = "Migration failed due to validation error"

        sample_record.mark_completed(success=False, error=error_msg)

        assert sample_record.completed_at is not None
        assert sample_record.success is False
        assert sample_record.error_message == error_msg

    def test_mark_failed(self, sample_record):
        """Test marking migration as failed."""
        error_msg = "Critical migration failure"

        sample_record.mark_failed(error_msg)

        assert sample_record.completed_at is not None
        assert sample_record.success is False
        assert sample_record.error_message == error_msg

    def test_is_completed_property(self, sample_record):
        """Test is_completed property."""
        # Initially not completed
        assert sample_record.is_completed is False

        # After marking as completed
        sample_record.mark_completed()
        assert sample_record.is_completed is True

    def test_is_in_progress_property(self, sample_record):
        """Test is_in_progress property."""
        # Initially in progress
        assert sample_record.is_in_progress is True

        # After completion
        sample_record.mark_completed()
        assert sample_record.is_in_progress is False

    def test_duration_seconds_property(self, sample_record):
        """Test duration_seconds property."""
        # Initially no duration (not completed)
        assert sample_record.duration_seconds is None

        # Set specific start time for predictable duration calculation
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        sample_record.started_at = start_time

        # Mark as completed after known duration
        completion_time = start_time + timedelta(seconds=30)
        sample_record.completed_at = completion_time

        # Should calculate correct duration
        assert sample_record.duration_seconds == 30.0

    def test_schema_version_properties(self):
        """Test schema version analysis properties."""
        # Schema upgrade (1 -> 3)
        upgrade_record = ProjectMigrationRecord(
            project_id="upgrade-test",
            project_name="upgrade-test",
            operation=MigrationOperation.UPGRADE,
            from_schema_version=1,
            to_schema_version=3
        )

        assert upgrade_record.is_schema_upgrade is True
        assert upgrade_record.is_schema_downgrade is False
        assert upgrade_record.schema_version_change == 2

        # Schema downgrade (3 -> 1)
        downgrade_record = ProjectMigrationRecord(
            project_id="downgrade-test",
            project_name="downgrade-test",
            operation=MigrationOperation.RECREATION,
            from_schema_version=3,
            to_schema_version=1
        )

        assert downgrade_record.is_schema_upgrade is False
        assert downgrade_record.is_schema_downgrade is True
        assert downgrade_record.schema_version_change == -2

        # Same version (validation)
        same_version_record = ProjectMigrationRecord(
            project_id="same-test",
            project_name="same-test",
            operation=MigrationOperation.VALIDATION,
            from_schema_version=2,
            to_schema_version=2
        )

        assert same_version_record.is_schema_upgrade is False
        assert same_version_record.is_schema_downgrade is False
        assert same_version_record.schema_version_change == 0

    def test_to_summary(self, sample_record):
        """Test summary generation."""
        # Test summary for incomplete migration
        summary = sample_record.to_summary()

        assert summary["id"] == sample_record.id
        assert summary["project_id"] == "sample-id"
        assert summary["project_name"] == "sample-project"
        assert summary["operation"] == "recreation"
        assert summary["schema_change"] == "v1 → v3"
        assert isinstance(summary["started_at"], str)
        assert summary["completed_at"] is None
        assert summary["duration_seconds"] is None
        assert summary["success"] is False
        assert summary["error_message"] is None
        assert summary["data_size_mb"] == 0
        assert summary["user_initiated"] is True
        assert summary["initiated_by_command"] == "unknown"

        # Complete the migration and test summary again
        sample_record.data_size_bytes = 2097152  # 2 MB
        sample_record.mark_completed(success=True)

        completed_summary = sample_record.to_summary()

        assert completed_summary["completed_at"] is not None
        assert isinstance(completed_summary["duration_seconds"], float)
        assert completed_summary["success"] is True
        assert completed_summary["data_size_mb"] == 2.0


class TestProjectMigrationRecordFactoryMethods:
    """Test ProjectMigrationRecord factory methods."""

    def test_create_recreation_record_minimal(self):
        """Test creating recreation record with minimal parameters."""
        record = ProjectMigrationRecord.create_recreation_record(
            project_id="recreation-test-id",
            project_name="recreation-test",
            from_version=1,
            to_version=3
        )

        assert record.project_id == "recreation-test-id"
        assert record.project_name == "recreation-test"
        assert record.operation == MigrationOperation.RECREATION
        assert record.from_schema_version == 1
        assert record.to_schema_version == 3
        assert record.preserved_settings == {}
        assert record.preserved_metadata == {}
        assert record.initiated_by_command == "docbro project --recreate"

    def test_create_recreation_record_complete(self):
        """Test creating recreation record with all parameters."""
        settings = {"crawl_depth": 3, "rate_limit": 1.0}
        metadata = {"description": "Test project", "category": "demo"}
        command = "docbro project --recreate test-project --confirm"

        record = ProjectMigrationRecord.create_recreation_record(
            project_id="complete-recreation-id",
            project_name="complete-recreation",
            from_version=2,
            to_version=3,
            preserved_settings=settings,
            preserved_metadata=metadata,
            initiated_by_command=command
        )

        assert record.operation == MigrationOperation.RECREATION
        assert record.from_schema_version == 2
        assert record.to_schema_version == 3
        assert record.preserved_settings == settings
        assert record.preserved_metadata == metadata
        assert record.initiated_by_command == command

    def test_create_validation_record(self):
        """Test creating validation record."""
        record = ProjectMigrationRecord.create_validation_record(
            project_id="validation-test-id",
            project_name="validation-test",
            schema_version=3
        )

        assert record.project_id == "validation-test-id"
        assert record.project_name == "validation-test"
        assert record.operation == MigrationOperation.VALIDATION
        assert record.from_schema_version == 3
        assert record.to_schema_version == 3  # Same for validation
        assert record.initiated_by_command == "docbro project --check-compatibility"

    def test_create_validation_record_custom_command(self):
        """Test creating validation record with custom command."""
        custom_command = "docbro health --compatibility-check"

        record = ProjectMigrationRecord.create_validation_record(
            project_id="custom-validation-id",
            project_name="custom-validation",
            schema_version=2,
            initiated_by_command=custom_command
        )

        assert record.operation == MigrationOperation.VALIDATION
        assert record.from_schema_version == 2
        assert record.to_schema_version == 2
        assert record.initiated_by_command == custom_command


class TestProjectMigrationRecordEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_preserved_data(self):
        """Test handling of very large preserved data."""
        large_settings = {f"setting_{i}": f"value_{i}" * 100 for i in range(100)}
        large_metadata = {f"meta_{i}": {"nested": f"data_{i}" * 50} for i in range(50)}

        record = ProjectMigrationRecord(
            project_id="large-data-test",
            project_name="large-data-test",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3,
            preserved_settings=large_settings,
            preserved_metadata=large_metadata,
            data_size_bytes=1073741824  # 1 GB
        )

        assert len(record.preserved_settings) == 100
        assert len(record.preserved_metadata) == 50
        assert record.data_size_bytes == 1073741824

        # Should handle large data in summary
        summary = record.to_summary()
        assert summary["data_size_mb"] == 1024.0

    def test_unicode_in_fields(self):
        """Test handling of unicode characters in text fields."""
        unicode_record = ProjectMigrationRecord(
            project_id="unicode-test-项目-🚀",
            project_name="项目测试-émojis-🎯",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3,
            error_message="Error with unicode: 错误信息 🐛",
            initiated_by_command="docbro projet --recréer 项目-🚀",
            preserved_settings={"设置": "值", "emoji_setting": "🎯"},
            preserved_metadata={"描述": "测试项目", "émoji_meta": "🚀"}
        )

        # Should handle unicode gracefully
        assert "项目" in unicode_record.project_name
        assert "🎯" in unicode_record.project_name
        assert "错误信息" in unicode_record.error_message
        assert "🐛" in unicode_record.error_message
        assert unicode_record.preserved_settings["设置"] == "值"
        assert unicode_record.preserved_metadata["émoji_meta"] == "🚀"

        # Summary should preserve unicode
        summary = unicode_record.to_summary()
        assert "项目" in summary["project_name"]
        assert "🎯" in summary["project_name"]

    def test_extreme_timestamps(self):
        """Test handling of extreme timestamp values."""
        # Far past
        past_time = datetime(1970, 1, 1, 0, 0, 0)
        record = ProjectMigrationRecord(
            project_id="past-test",
            project_name="past-test",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3,
            started_at=past_time
        )

        assert record.started_at == past_time

        # Complete after very long duration
        future_completion = past_time + timedelta(days=365 * 50)  # 50 years later
        record.completed_at = future_completion

        # Should calculate duration correctly even for extreme values
        duration = record.duration_seconds
        assert duration is not None
        assert duration > 0
        assert duration == (365 * 50 * 24 * 3600)  # 50 years in seconds

    def test_concurrent_modification_safety(self):
        """Test that record modifications are safe under concurrent-like access."""
        record = ProjectMigrationRecord(
            project_id="concurrent-test",
            project_name="concurrent-test",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3
        )

        # Simulate rapid state changes
        initial_state = record.is_in_progress

        record.mark_completed(success=True)
        completed_state = record.is_completed

        record.mark_failed("Rollback after completion")
        failed_state = record.success

        # Verify state transitions are consistent
        assert initial_state is True
        assert completed_state is True
        assert failed_state is False  # Last state should persist

    def test_enum_serialization_in_summary(self):
        """Test that enums are properly serialized in summaries."""
        for operation in MigrationOperation:
            record = ProjectMigrationRecord(
                project_id=f"enum-test-{operation.value}",
                project_name=f"enum-test-{operation.value}",
                operation=operation,
                from_schema_version=1,
                to_schema_version=3
            )

            summary = record.to_summary()
            assert summary["operation"] == operation.value
            assert isinstance(summary["operation"], str)

    def test_data_size_conversion_accuracy(self):
        """Test accuracy of data size conversion to MB."""
        test_cases = [
            (0, 0),                    # 0 bytes = 0 MB
            (1024, 0),                 # 1 KB = 0.00 MB (rounded)
            (1048576, 1.0),           # 1 MB = 1.00 MB
            (1572864, 1.5),           # 1.5 MB = 1.50 MB
            (2097152, 2.0),           # 2 MB = 2.00 MB
            (1073741824, 1024.0),     # 1 GB = 1024.00 MB
            (1048577, 1.0),           # 1 MB + 1 byte = 1.00 MB (rounded)
        ]

        for bytes_size, expected_mb in test_cases:
            record = ProjectMigrationRecord(
                project_id=f"size-test-{bytes_size}",
                project_name=f"size-test-{bytes_size}",
                operation=MigrationOperation.RECREATION,
                from_schema_version=1,
                to_schema_version=3,
                data_size_bytes=bytes_size
            )

            summary = record.to_summary()
            assert summary["data_size_mb"] == expected_mb

    def test_property_consistency(self):
        """Test that properties remain consistent across different states."""
        record = ProjectMigrationRecord(
            project_id="consistency-test",
            project_name="consistency-test",
            operation=MigrationOperation.UPGRADE,
            from_schema_version=1,
            to_schema_version=3
        )

        # Properties should be consistent before completion
        assert record.is_in_progress is True
        assert record.is_completed is False
        assert record.duration_seconds is None
        assert record.is_schema_upgrade is True
        assert record.schema_version_change == 2

        # Complete the record
        record.mark_completed(success=True)

        # Properties should be consistent after completion
        assert record.is_in_progress is False
        assert record.is_completed is True
        assert record.duration_seconds is not None
        assert record.duration_seconds >= 0
        assert record.is_schema_upgrade is True  # Should not change
        assert record.schema_version_change == 2  # Should not change