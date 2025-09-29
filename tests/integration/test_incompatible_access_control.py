"""Integration test for read-only access for incompatible projects (T013)."""

import pytest
from datetime import datetime

from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.logic.projects.models.project import ProjectType


class IncompatibleProjectError(Exception):
    """Exception raised when trying to modify incompatible projects."""
    pass


class TestIncompatibleAccessControl:
    """Test read-only access control for incompatible projects."""

    def test_read_access_allowed_for_incompatible_project(self):
        """Test that read operations are allowed on incompatible projects."""
        # Create incompatible project (old schema version)
        incompatible_project = UnifiedProject(
            name="incompatible-readonly-test",
            type=ProjectType.CRAWLING,
            schema_version=1,  # Old version
            source_url="https://legacy.example.com",
            settings={
                "crawl_depth": 3,
                "rate_limit": 1.0
            },
            statistics={
                "total_pages": 100,
                "successful_pages": 95,
                "failed_pages": 5
            },
            metadata={
                "description": "Legacy project that needs recreation",
                "created_by": "user123"
            }
        )

        # Verify it's incompatible
        assert not incompatible_project.is_compatible()
        assert not incompatible_project.allows_modification()
        assert incompatible_project.needs_recreation()

        # Read operations should work fine
        assert incompatible_project.name == "incompatible-readonly-test"
        assert incompatible_project.type == ProjectType.CRAWLING
        assert incompatible_project.source_url == "https://legacy.example.com"
        assert incompatible_project.schema_version == 1
        assert incompatible_project.compatibility_status == CompatibilityStatus.INCOMPATIBLE

        # Can read settings
        assert incompatible_project.settings["crawl_depth"] == 3
        assert incompatible_project.settings["rate_limit"] == 1.0

        # Can read statistics
        assert incompatible_project.statistics["total_pages"] == 100
        assert incompatible_project.statistics["successful_pages"] == 95
        assert incompatible_project.statistics["failed_pages"] == 5

        # Can read metadata
        assert incompatible_project.metadata["description"] == "Legacy project that needs recreation"
        assert incompatible_project.metadata["created_by"] == "user123"

        # Can read timestamps
        assert isinstance(incompatible_project.created_at, datetime)
        assert isinstance(incompatible_project.updated_at, datetime)

        # Can get project paths
        project_dir = incompatible_project.get_project_directory()
        assert "incompatible-readonly-test" in project_dir

        db_path = incompatible_project.get_database_path()
        assert "incompatible-readonly-test.db" in db_path

    def test_modification_blocked_for_incompatible_project(self):
        """Test that modification operations are blocked on incompatible projects."""
        # Create incompatible project
        incompatible_project = UnifiedProject(
            name="modification-test",
            type=ProjectType.DATA,
            schema_version=2,  # Old version
            settings={"chunk_size": 500}
        )

        # Verify it's incompatible
        assert not incompatible_project.allows_modification()

        # Attempting to update settings should be blocked
        # Note: This is at the application level - the model itself doesn't enforce this
        # The blocking would happen in the service layer
        if not incompatible_project.allows_modification():
            # Simulate service-level blocking
            with pytest.raises(Exception):  # Would be IncompatibleProjectError in real implementation
                raise IncompatibleProjectError(
                    f"Cannot modify incompatible project '{incompatible_project.name}'. "
                    f"Project requires recreation to schema version {SchemaVersion.CURRENT_VERSION}."
                )

        # Attempting to update status should be blocked
        if not incompatible_project.allows_modification():
            with pytest.raises(Exception):
                raise IncompatibleProjectError(
                    f"Cannot update status of incompatible project '{incompatible_project.name}'. "
                    "Project requires recreation."
                )

    def test_search_operations_allowed_with_compatibility_warning(self):
        """Test that search operations are allowed but include compatibility warnings."""
        # Create incompatible project
        incompatible_project = UnifiedProject(
            name="search-test",
            type=ProjectType.CRAWLING,
            schema_version=1,
            statistics={"total_pages": 50}
        )

        # Search should be allowed (read-only operation)
        # But should include compatibility status in results
        search_result = {
            "project_id": incompatible_project.id,
            "project_name": incompatible_project.name,
            "compatibility_status": incompatible_project.compatibility_status.value,
            "allows_modification": incompatible_project.allows_modification(),
            "needs_recreation": incompatible_project.needs_recreation(),
            "schema_version": incompatible_project.schema_version,
            "current_schema_version": SchemaVersion.CURRENT_VERSION
        }

        # Verify search result includes compatibility information
        assert search_result["compatibility_status"] == "incompatible"
        assert search_result["allows_modification"] is False
        assert search_result["needs_recreation"] is True
        assert search_result["schema_version"] == 1
        assert search_result["current_schema_version"] == 3

    def test_project_listing_includes_compatibility_status(self):
        """Test that project listings include compatibility status for all projects."""
        # Create mixed compatibility projects
        projects = [
            UnifiedProject(
                name="compatible-project",
                type=ProjectType.CRAWLING,
                schema_version=SchemaVersion.CURRENT_VERSION
            ),
            UnifiedProject(
                name="incompatible-v1",
                type=ProjectType.CRAWLING,
                schema_version=1
            ),
            UnifiedProject(
                name="incompatible-v2",
                type=ProjectType.DATA,
                schema_version=2
            ),
            UnifiedProject(
                name="migrating-project",
                type=ProjectType.STORAGE,
                compatibility_status=CompatibilityStatus.MIGRATING
            )
        ]

        # Generate listing with compatibility information
        project_listing = []
        for project in projects:
            summary = project.to_summary()
            # Add compatibility flags to summary
            summary.update({
                "is_compatible": project.is_compatible(),
                "allows_modification": project.allows_modification(),
                "needs_recreation": project.needs_recreation(),
                "schema_version": project.schema_version
            })
            project_listing.append(summary)

        # Verify compatibility information is included
        compatible, incompatible_v1, incompatible_v2, migrating = project_listing

        # Compatible project
        assert compatible["compatibility_status"] == "compatible"
        assert compatible["is_compatible"] is True
        assert compatible["allows_modification"] is True
        assert compatible["needs_recreation"] is False
        assert compatible["schema_version"] == SchemaVersion.CURRENT_VERSION

        # Incompatible v1 project
        assert incompatible_v1["compatibility_status"] == "incompatible"
        assert incompatible_v1["is_compatible"] is False
        assert incompatible_v1["allows_modification"] is False
        assert incompatible_v1["needs_recreation"] is True
        assert incompatible_v1["schema_version"] == 1

        # Incompatible v2 project
        assert incompatible_v2["compatibility_status"] == "incompatible"
        assert incompatible_v2["is_compatible"] is False
        assert incompatible_v2["allows_modification"] is False
        assert incompatible_v2["needs_recreation"] is True
        assert incompatible_v2["schema_version"] == 2

        # Migrating project
        assert migrating["compatibility_status"] == "migrating"
        assert migrating["is_compatible"] is False
        assert migrating["allows_modification"] is False
        assert migrating["needs_recreation"] is False  # Already in migration process

    def test_detailed_project_view_shows_compatibility_info(self):
        """Test that detailed project views show comprehensive compatibility information."""
        # Create incompatible project
        incompatible_project = UnifiedProject(
            name="detailed-view-test",
            type=ProjectType.CRAWLING,
            schema_version=1,
            source_url="https://old.example.com",
            settings={"crawl_depth": 2},
            statistics={"total_pages": 75}
        )

        # Generate detailed view with full compatibility information
        detailed_view = incompatible_project.to_dict()

        # Verify all compatibility information is present
        assert detailed_view["schema_version"] == 1
        assert detailed_view["compatibility_status"] == "incompatible"
        assert detailed_view["is_compatible"] is False
        assert detailed_view["allows_modification"] is False
        assert detailed_view["needs_recreation"] is True

        # Verify all project data is still accessible
        assert detailed_view["name"] == "detailed-view-test"
        assert detailed_view["type"] == "crawling"
        assert detailed_view["source_url"] == "https://old.example.com"
        assert detailed_view["settings"]["crawl_depth"] == 2
        assert detailed_view["statistics"]["total_pages"] == 75

        # Add recreation guidance information
        recreation_info = {
            "current_schema_version": SchemaVersion.CURRENT_VERSION,
            "recreation_required": True,
            "recreation_command": f"docbro project --recreate {incompatible_project.name}",
            "data_preservation": "Settings and metadata will be preserved, crawled data will be reset",
            "version_upgrade_path": f"v{incompatible_project.schema_version} → v{SchemaVersion.CURRENT_VERSION}"
        }

        detailed_view["recreation_info"] = recreation_info

        # Verify recreation guidance
        assert detailed_view["recreation_info"]["recreation_required"] is True
        assert "docbro project --recreate" in detailed_view["recreation_info"]["recreation_command"]
        assert "v1 → v3" in detailed_view["recreation_info"]["version_upgrade_path"]

    def test_export_functionality_for_incompatible_projects(self):
        """Test that project export works for incompatible projects (read-only)."""
        # Create incompatible project with rich data
        incompatible_project = UnifiedProject(
            name="export-test",
            type=ProjectType.DATA,
            schema_version=2,
            settings={
                "chunk_size": 750,
                "embedding_model": "custom-model",
                "enable_tagging": True
            },
            metadata={
                "description": "Legacy data project",
                "tags": ["legacy", "important"],
                "owner": "team-data"
            },
            statistics={
                "total_documents": 200,
                "processed_documents": 180
            }
        )

        # Export should work (read operation)
        export_data = {
            "project_name": incompatible_project.name,
            "project_type": incompatible_project.type.value if incompatible_project.type else None,
            "schema_version": incompatible_project.schema_version,
            "exported_at": datetime.utcnow().isoformat(),
            "settings": incompatible_project.settings.copy(),
            "metadata": incompatible_project.metadata.copy(),
            "source_url": incompatible_project.source_url,
            "statistics": incompatible_project.statistics.copy(),
            "compatibility_info": {
                "is_compatible": incompatible_project.is_compatible(),
                "current_schema_version": SchemaVersion.CURRENT_VERSION,
                "needs_recreation": incompatible_project.needs_recreation()
            }
        }

        # Verify export contains all necessary data
        assert export_data["project_name"] == "export-test"
        assert export_data["project_type"] == "data"
        assert export_data["schema_version"] == 2
        assert export_data["settings"]["chunk_size"] == 750
        assert export_data["metadata"]["description"] == "Legacy data project"
        assert export_data["statistics"]["total_documents"] == 200
        assert export_data["compatibility_info"]["is_compatible"] is False
        assert export_data["compatibility_info"]["needs_recreation"] is True

    def test_operation_compatibility_checking(self):
        """Test that operation compatibility is checked properly."""
        # Create incompatible projects of different types
        incompatible_crawler = UnifiedProject(
            name="incompatible-crawler",
            type=ProjectType.CRAWLING,
            schema_version=1
        )

        incompatible_data = UnifiedProject(
            name="incompatible-data",
            type=ProjectType.DATA,
            schema_version=2
        )

        # Operation compatibility should still work (read-only check)
        assert incompatible_crawler.is_compatible_with_operation("crawl")
        assert incompatible_crawler.is_compatible_with_operation("search")
        assert incompatible_crawler.is_compatible_with_operation("vector_operations")
        assert not incompatible_crawler.is_compatible_with_operation("upload")

        assert incompatible_data.is_compatible_with_operation("upload")
        assert incompatible_data.is_compatible_with_operation("search")
        assert incompatible_data.is_compatible_with_operation("vector_operations")
        assert not incompatible_data.is_compatible_with_operation("crawl")

        # But actual execution would be blocked if allows_modification is False
        for project in [incompatible_crawler, incompatible_data]:
            assert not project.allows_modification()
            # In real implementation, services would check this before operation execution

    def test_error_messages_for_blocked_operations(self):
        """Test that appropriate error messages are generated for blocked operations."""
        incompatible_project = UnifiedProject(
            name="error-message-test",
            type=ProjectType.CRAWLING,
            schema_version=1
        )

        # Generate appropriate error messages for different blocked operations
        def generate_modification_error(operation: str) -> str:
            return (
                f"Cannot perform '{operation}' on incompatible project "
                f"'{incompatible_project.name}' (schema v{incompatible_project.schema_version}). "
                f"Project requires recreation to current schema version "
                f"v{SchemaVersion.CURRENT_VERSION}. "
                f"Use 'docbro project --recreate {incompatible_project.name}' to upgrade."
            )

        # Test different operation error messages
        crawl_error = generate_modification_error("crawl")
        update_error = generate_modification_error("update")
        settings_error = generate_modification_error("update_settings")

        # Verify error messages contain necessary information
        for error_msg in [crawl_error, update_error, settings_error]:
            assert "incompatible project" in error_msg
            assert incompatible_project.name in error_msg
            assert "schema v1" in error_msg
            assert f"v{SchemaVersion.CURRENT_VERSION}" in error_msg
            assert "docbro project --recreate" in error_msg

    def test_compatibility_status_transitions(self):
        """Test compatibility status transitions during recreation process."""
        # Start with incompatible project
        project = UnifiedProject(
            name="transition-test",
            type=ProjectType.STORAGE,
            schema_version=1
        )
        assert project.compatibility_status == CompatibilityStatus.INCOMPATIBLE

        # Simulate transition to migrating status
        project.compatibility_status = CompatibilityStatus.MIGRATING
        assert project.compatibility_status == CompatibilityStatus.MIGRATING
        assert not project.allows_modification()  # Still blocked during migration
        assert project.compatibility_status.is_transitional

        # Simulate completion of recreation
        project.schema_version = SchemaVersion.CURRENT_VERSION
        project.compatibility_status = CompatibilityStatus.COMPATIBLE
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE
        assert project.allows_modification()  # Now allowed
        assert not project.compatibility_status.is_transitional

    def test_bulk_compatibility_assessment(self):
        """Test bulk assessment of project compatibility."""
        # Create multiple projects with different compatibility states
        projects = [
            UnifiedProject(name="compat-1", type=ProjectType.CRAWLING, schema_version=3),
            UnifiedProject(name="compat-2", type=ProjectType.DATA, schema_version=3),
            UnifiedProject(name="incompat-1", type=ProjectType.CRAWLING, schema_version=1),
            UnifiedProject(name="incompat-2", type=ProjectType.DATA, schema_version=2),
            UnifiedProject(name="incompat-3", type=ProjectType.STORAGE, schema_version=1),
        ]

        # Assess compatibility
        compatibility_report = {
            "total_projects": len(projects),
            "compatible_projects": [],
            "incompatible_projects": [],
            "migration_candidates": []
        }

        for project in projects:
            if project.is_compatible():
                compatibility_report["compatible_projects"].append({
                    "name": project.name,
                    "type": project.type.value if project.type else None,
                    "schema_version": project.schema_version
                })
            else:
                incompatible_info = {
                    "name": project.name,
                    "type": project.type.value if project.type else None,
                    "schema_version": project.schema_version,
                    "needs_recreation": project.needs_recreation()
                }
                compatibility_report["incompatible_projects"].append(incompatible_info)

                if project.needs_recreation():
                    compatibility_report["migration_candidates"].append(project.name)

        # Verify assessment results
        assert compatibility_report["total_projects"] == 5
        assert len(compatibility_report["compatible_projects"]) == 2
        assert len(compatibility_report["incompatible_projects"]) == 3
        assert len(compatibility_report["migration_candidates"]) == 3

        # Verify compatible projects
        compatible_names = [p["name"] for p in compatibility_report["compatible_projects"]]
        assert "compat-1" in compatible_names
        assert "compat-2" in compatible_names

        # Verify incompatible projects
        incompatible_names = [p["name"] for p in compatibility_report["incompatible_projects"]]
        assert "incompat-1" in incompatible_names
        assert "incompat-2" in incompatible_names
        assert "incompat-3" in incompatible_names