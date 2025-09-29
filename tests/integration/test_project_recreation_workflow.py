"""Integration test for project recreation workflow with settings preservation (T014)."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.models.migration_record import ProjectMigrationRecord, MigrationOperation
from src.logic.projects.models.project import ProjectType


class TestProjectRecreationWorkflow:
    """Test project recreation workflow with settings and metadata preservation."""

    def test_recreation_workflow_end_to_end(self):
        """Test complete recreation workflow from incompatible to compatible."""
        # Step 1: Start with incompatible project (legacy schema)
        original_project = UnifiedProject(
            name="recreation-test-project",
            type=ProjectType.CRAWLING,
            schema_version=1,  # Legacy version
            source_url="https://legacy.example.com/docs",
            settings={
                "crawl_depth": 4,
                "rate_limit": 2.0,
                "user_agent": "DocBro/0.5",
                "max_file_size": 5242880
            },
            statistics={
                "total_pages": 150,
                "successful_pages": 140,
                "failed_pages": 10,
                "total_size_bytes": 15728640
            },
            metadata={
                "description": "Legacy documentation project",
                "tags": ["documentation", "legacy", "important"],
                "owner": "team-docs",
                "priority": "high"
            }
        )

        # Verify original project state
        assert not original_project.is_compatible()
        assert not original_project.allows_modification()
        assert original_project.needs_recreation()

        # Step 2: Create migration record before recreation
        migration_record = ProjectMigrationRecord.create_recreation_record(
            project_id=original_project.id,
            project_name=original_project.name,
            from_version=original_project.schema_version,
            to_version=SchemaVersion.CURRENT_VERSION,
            preserved_settings=original_project.settings.copy(),
            preserved_metadata=original_project.metadata.copy(),
            initiated_by_command="docbro project --recreate recreation-test-project"
        )

        # Verify migration record
        assert migration_record.operation == MigrationOperation.RECREATION
        assert migration_record.from_schema_version == 1
        assert migration_record.to_schema_version == SchemaVersion.CURRENT_VERSION
        assert migration_record.project_name == "recreation-test-project"
        assert migration_record.preserved_settings["crawl_depth"] == 4
        assert migration_record.preserved_metadata["description"] == "Legacy documentation project"
        assert not migration_record.is_completed

        # Step 3: Mark project as migrating
        original_project.compatibility_status = CompatibilityStatus.MIGRATING
        assert original_project.compatibility_status.is_transitional
        assert not original_project.allows_modification()  # Still blocked during migration

        # Step 4: Create recreated project with preserved settings
        recreated_project = UnifiedProject(
            id=original_project.id,  # Keep same ID
            name=original_project.name,  # Keep same name
            type=original_project.type,  # Keep same type
            schema_version=SchemaVersion.CURRENT_VERSION,  # Upgrade to current
            source_url=original_project.source_url,  # Preserve source URL
            settings=migration_record.preserved_settings.copy(),  # Preserve settings
            metadata=migration_record.preserved_metadata.copy(),  # Preserve metadata
            statistics={},  # Reset statistics (clean slate)
            status=UnifiedProjectStatus.ACTIVE  # Reset to active
        )

        # Step 5: Verify recreated project state
        assert recreated_project.is_compatible()
        assert recreated_project.allows_modification()
        assert not recreated_project.needs_recreation()
        assert recreated_project.schema_version == SchemaVersion.CURRENT_VERSION
        assert recreated_project.compatibility_status == CompatibilityStatus.COMPATIBLE

        # Verify preserved data
        assert recreated_project.id == original_project.id
        assert recreated_project.name == original_project.name
        assert recreated_project.type == original_project.type
        assert recreated_project.source_url == original_project.source_url

        # Verify preserved settings
        assert recreated_project.settings["crawl_depth"] == 4
        assert recreated_project.settings["rate_limit"] == 2.0
        assert recreated_project.settings["user_agent"] == "DocBro/0.5"
        assert recreated_project.settings["max_file_size"] == 5242880

        # Verify preserved metadata
        assert recreated_project.metadata["description"] == "Legacy documentation project"
        assert recreated_project.metadata["tags"] == ["documentation", "legacy", "important"]
        assert recreated_project.metadata["owner"] == "team-docs"
        assert recreated_project.metadata["priority"] == "high"

        # Verify reset data
        assert recreated_project.statistics == {}  # Statistics reset
        assert recreated_project.last_crawl_at is None  # No crawl data
        assert recreated_project.status == UnifiedProjectStatus.ACTIVE

        # Step 6: Complete migration record
        migration_record.mark_completed(success=True)
        assert migration_record.is_completed
        assert migration_record.success
        assert migration_record.completed_at is not None
        assert migration_record.duration_seconds is not None

    def test_settings_preservation_and_validation(self):
        """Test that settings are properly preserved and validated during recreation."""
        # Create project with type-specific settings
        original_data_project = UnifiedProject(
            name="settings-preservation-test",
            type=ProjectType.DATA,
            schema_version=2,
            settings={
                "chunk_size": 750,
                "chunk_overlap": 75,
                "embedding_model": "custom-model-v2",
                "vector_store_type": "qdrant",
                "enable_tagging": True,
                "custom_setting": "preserved_value"
            }
        )

        # Simulate recreation with settings preservation
        migration_record = ProjectMigrationRecord.create_recreation_record(
            project_id=original_data_project.id,
            project_name=original_data_project.name,
            from_version=2,
            to_version=3,
            preserved_settings=original_data_project.settings.copy()
        )

        # Create recreated project
        recreated_project = UnifiedProject(
            id=original_data_project.id,
            name=original_data_project.name,
            type=original_data_project.type,
            schema_version=3,
            settings=migration_record.preserved_settings
        )

        # Verify settings validation still works
        assert recreated_project.settings["chunk_size"] == 750
        assert recreated_project.settings["embedding_model"] == "custom-model-v2"
        assert recreated_project.settings["custom_setting"] == "preserved_value"

        # Test that invalid settings are caught during recreation
        invalid_settings = original_data_project.settings.copy()
        invalid_settings["chunk_size"] = 50  # Too small

        with pytest.raises(ValueError, match="chunk_size must be an integer between 100 and 5000"):
            UnifiedProject(
                name="invalid-recreation",
                type=ProjectType.DATA,
                schema_version=3,
                settings=invalid_settings
            )

    def test_metadata_preservation_with_migration_tracking(self):
        """Test metadata preservation with additional migration tracking."""
        original_project = UnifiedProject(
            name="metadata-preservation-test",
            type=ProjectType.STORAGE,
            schema_version=1,
            metadata={
                "description": "Important storage project",
                "tags": ["storage", "critical"],
                "created_by": "admin",
                "last_backup": "2025-01-15",
                "storage_location": "/data/projects/storage"
            }
        )

        # Create migration record with metadata preservation
        migration_record = ProjectMigrationRecord.create_recreation_record(
            project_id=original_project.id,
            project_name=original_project.name,
            from_version=1,
            to_version=3,
            preserved_metadata=original_project.metadata.copy()
        )

        # Add migration tracking to metadata
        enhanced_metadata = migration_record.preserved_metadata.copy()
        enhanced_metadata.update({
            "migration_history": [{
                "migration_id": migration_record.id,
                "from_version": migration_record.from_schema_version,
                "to_version": migration_record.to_schema_version,
                "migrated_at": migration_record.started_at.isoformat(),
                "migration_type": migration_record.operation.value
            }]
        })

        # Create recreated project with enhanced metadata
        recreated_project = UnifiedProject(
            id=original_project.id,
            name=original_project.name,
            type=original_project.type,
            schema_version=3,
            metadata=enhanced_metadata
        )

        # Verify metadata preservation
        assert recreated_project.metadata["description"] == "Important storage project"
        assert recreated_project.metadata["tags"] == ["storage", "critical"]
        assert recreated_project.metadata["created_by"] == "admin"
        assert recreated_project.metadata["last_backup"] == "2025-01-15"
        assert recreated_project.metadata["storage_location"] == "/data/projects/storage"

        # Verify migration tracking
        assert "migration_history" in recreated_project.metadata
        migration_history = recreated_project.metadata["migration_history"]
        assert len(migration_history) == 1
        assert migration_history[0]["from_version"] == 1
        assert migration_history[0]["to_version"] == 3
        assert migration_history[0]["migration_type"] == "recreation"

    def test_recreation_failure_handling(self):
        """Test handling of recreation failures with rollback."""
        original_project = UnifiedProject(
            name="failure-test-project",
            type=ProjectType.CRAWLING,
            schema_version=1,
            settings={"crawl_depth": 3}
        )

        # Create migration record
        migration_record = ProjectMigrationRecord.create_recreation_record(
            project_id=original_project.id,
            project_name=original_project.name,
            from_version=1,
            to_version=3,
            preserved_settings=original_project.settings.copy()
        )

        # Simulate recreation failure
        error_message = "Recreation failed due to invalid configuration"
        migration_record.mark_failed(error_message)

        # Verify failure state
        assert migration_record.is_completed
        assert not migration_record.success
        assert migration_record.error_message == error_message

        # Original project should remain in incompatible state
        assert not original_project.is_compatible()
        assert original_project.compatibility_status == CompatibilityStatus.INCOMPATIBLE

        # Migration record should contain failure details
        summary = migration_record.to_summary()
        assert not summary["success"]
        assert summary["error_message"] == error_message
        assert summary["schema_change"] == "v1 → v3"

    def test_recreation_with_data_size_tracking(self):
        """Test recreation with tracking of data size for preserved content."""
        original_project = UnifiedProject(
            name="data-size-test",
            type=ProjectType.DATA,
            schema_version=2,
            settings={"chunk_size": 1000},
            metadata={"description": "Large project with lots of data"},
            statistics={"total_documents": 5000, "total_size_bytes": 52428800}
        )

        # Calculate preserved data size (settings + metadata as JSON)
        import json
        settings_size = len(json.dumps(original_project.settings).encode('utf-8'))
        metadata_size = len(json.dumps(original_project.metadata).encode('utf-8'))
        preserved_data_size = settings_size + metadata_size

        # Create migration record with data size tracking
        migration_record = ProjectMigrationRecord.create_recreation_record(
            project_id=original_project.id,
            project_name=original_project.name,
            from_version=2,
            to_version=3,
            preserved_settings=original_project.settings.copy(),
            preserved_metadata=original_project.metadata.copy()
        )

        # Set data size
        migration_record.data_size_bytes = preserved_data_size

        # Complete migration
        migration_record.mark_completed(success=True)

        # Verify data size tracking
        assert migration_record.data_size_bytes > 0
        summary = migration_record.to_summary()
        assert summary["data_size_mb"] > 0

    def test_multiple_recreation_attempts(self):
        """Test handling multiple recreation attempts for the same project."""
        project = UnifiedProject(
            name="multiple-attempts-test",
            type=ProjectType.STORAGE,
            schema_version=1
        )

        # First recreation attempt (fails)
        first_attempt = ProjectMigrationRecord.create_recreation_record(
            project_id=project.id,
            project_name=project.name,
            from_version=1,
            to_version=3,
            initiated_by_command="docbro project --recreate multiple-attempts-test"
        )
        first_attempt.mark_failed("Network timeout during recreation")

        # Second recreation attempt (succeeds)
        second_attempt = ProjectMigrationRecord.create_recreation_record(
            project_id=project.id,
            project_name=project.name,
            from_version=1,
            to_version=3,
            initiated_by_command="docbro project --recreate multiple-attempts-test --retry"
        )
        second_attempt.mark_completed(success=True)

        # Verify both attempts are tracked
        assert not first_attempt.success
        assert first_attempt.error_message == "Network timeout during recreation"

        assert second_attempt.success
        assert second_attempt.error_message is None

        # Migration history would track both attempts
        migration_history = [first_attempt, second_attempt]

        # Verify chronological order
        assert first_attempt.started_at < second_attempt.started_at
        assert len([r for r in migration_history if not r.success]) == 1
        assert len([r for r in migration_history if r.success]) == 1

    def test_recreation_command_tracking(self):
        """Test tracking of different recreation commands."""
        project = UnifiedProject(
            name="command-tracking-test",
            type=ProjectType.CRAWLING,
            schema_version=2
        )

        # Test different command variations
        commands = [
            "docbro project --recreate command-tracking-test",
            "docbro project --recreate command-tracking-test --confirm",
            "docbro project --recreate command-tracking-test --preserve-settings",
            "docbro project --recreate command-tracking-test --clean-slate"
        ]

        migration_records = []
        for command in commands:
            record = ProjectMigrationRecord.create_recreation_record(
                project_id=project.id,
                project_name=project.name,
                from_version=2,
                to_version=3,
                initiated_by_command=command
            )
            migration_records.append(record)

        # Verify command tracking
        for i, record in enumerate(migration_records):
            assert record.initiated_by_command == commands[i]
            assert record.user_initiated is True
            assert "docbro project --recreate" in record.initiated_by_command

    def test_recreation_validation_workflow(self):
        """Test validation steps during recreation workflow."""
        original_project = UnifiedProject(
            name="validation-workflow-test",
            type=ProjectType.DATA,
            schema_version=1,
            settings={
                "chunk_size": 500,
                "embedding_model": "old-model"
            }
        )

        # Step 1: Pre-recreation validation
        validation_record = ProjectMigrationRecord.create_validation_record(
            project_id=original_project.id,
            project_name=original_project.name,
            schema_version=original_project.schema_version
        )

        # Verify validation record
        assert validation_record.operation == MigrationOperation.VALIDATION
        assert validation_record.from_schema_version == validation_record.to_schema_version

        # Complete validation successfully
        validation_record.mark_completed(success=True)

        # Step 2: Proceed with recreation after successful validation
        recreation_record = ProjectMigrationRecord.create_recreation_record(
            project_id=original_project.id,
            project_name=original_project.name,
            from_version=1,
            to_version=3,
            preserved_settings=original_project.settings.copy()
        )

        # Step 3: Create recreated project
        recreated_project = UnifiedProject(
            id=original_project.id,
            name=original_project.name,
            type=original_project.type,
            schema_version=3,
            settings=recreation_record.preserved_settings
        )

        # Complete recreation
        recreation_record.mark_completed(success=True)

        # Verify both validation and recreation are tracked
        assert validation_record.success
        assert recreation_record.success
        assert validation_record.started_at <= recreation_record.started_at

    def test_schema_version_upgrade_path(self):
        """Test different schema version upgrade paths."""
        # Test v1 -> v3 upgrade
        v1_project = UnifiedProject(
            name="v1-upgrade",
            type=ProjectType.CRAWLING,
            schema_version=1
        )

        v1_migration = ProjectMigrationRecord.create_recreation_record(
            project_id=v1_project.id,
            project_name=v1_project.name,
            from_version=1,
            to_version=3
        )

        assert v1_migration.schema_version_change == 2
        assert v1_migration.is_schema_upgrade

        # Test v2 -> v3 upgrade
        v2_project = UnifiedProject(
            name="v2-upgrade",
            type=ProjectType.DATA,
            schema_version=2
        )

        v2_migration = ProjectMigrationRecord.create_recreation_record(
            project_id=v2_project.id,
            project_name=v2_project.name,
            from_version=2,
            to_version=3
        )

        assert v2_migration.schema_version_change == 1
        assert v2_migration.is_schema_upgrade

        # Verify upgrade path information
        v1_summary = v1_migration.to_summary()
        v2_summary = v2_migration.to_summary()

        assert v1_summary["schema_change"] == "v1 → v3"
        assert v2_summary["schema_change"] == "v2 → v3"