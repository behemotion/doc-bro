"""Unit tests for CompatibilityChecker logic."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.services.compatibility_checker import CompatibilityChecker, CompatibilityResult
from src.logic.projects.models.project import ProjectType


class TestCompatibilityResult:
    """Test the CompatibilityResult model."""

    def test_compatibility_result_creation(self):
        """Test creating a CompatibilityResult."""
        result = CompatibilityResult(
            is_compatible=True,
            current_version=3,
            project_version=3,
            status=CompatibilityStatus.COMPATIBLE
        )

        assert result.is_compatible is True
        assert result.current_version == 3
        assert result.project_version == 3
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert result.missing_fields == []
        assert result.extra_fields == []
        assert result.issues == []
        assert result.can_be_migrated is False
        assert result.migration_required is False
        assert result.needs_recreation is False

    def test_needs_recreation_property(self):
        """Test needs_recreation property logic."""
        # Compatible project doesn't need recreation
        compatible = CompatibilityResult(
            is_compatible=True,
            current_version=3,
            project_version=3,
            status=CompatibilityStatus.COMPATIBLE
        )
        assert compatible.needs_recreation is False

        # Incompatible but migratable doesn't need recreation
        migratable = CompatibilityResult(
            is_compatible=False,
            current_version=3,
            project_version=2,
            status=CompatibilityStatus.INCOMPATIBLE,
            can_be_migrated=True
        )
        assert migratable.needs_recreation is False

        # Incompatible and not migratable needs recreation
        needs_recreation = CompatibilityResult(
            is_compatible=False,
            current_version=3,
            project_version=1,
            status=CompatibilityStatus.INCOMPATIBLE,
            can_be_migrated=False
        )
        assert needs_recreation.needs_recreation is True

    def test_add_methods(self):
        """Test methods for adding issues and fields."""
        result = CompatibilityResult(
            is_compatible=False,
            current_version=3,
            project_version=2,
            status=CompatibilityStatus.INCOMPATIBLE
        )

        result.add_issue("Test issue")
        result.add_missing_field("missing_field")
        result.add_extra_field("extra_field")

        assert "Test issue" in result.issues
        assert "missing_field" in result.missing_fields
        assert "extra_field" in result.extra_fields

    def test_to_summary(self):
        """Test summary generation."""
        result = CompatibilityResult(
            is_compatible=False,
            current_version=3,
            project_version=2,
            status=CompatibilityStatus.INCOMPATIBLE,
            migration_required=True
        )
        result.add_issue("Version mismatch")
        result.add_missing_field("new_field")

        summary = result.to_summary()

        assert summary["is_compatible"] is False
        assert summary["status"] == "incompatible"
        assert summary["version_info"] == "v2 → v3"
        assert summary["issues_count"] == 1
        assert summary["missing_fields_count"] == 1
        assert summary["extra_fields_count"] == 0
        assert summary["needs_recreation"] is True
        assert summary["migration_required"] is True


class TestCompatibilityChecker:
    """Test the CompatibilityChecker service."""

    @pytest.fixture
    def checker(self):
        """Create a CompatibilityChecker instance."""
        return CompatibilityChecker()

    @pytest.fixture
    def compatible_project(self):
        """Create a compatible project."""
        return UnifiedProject(
            name="compatible-project",
            schema_version=SchemaVersion.CURRENT_VERSION,
            type=ProjectType.CRAWLING,
            status=UnifiedProjectStatus.ACTIVE,
            settings={'crawl_depth': 3, 'rate_limit': 1.0}
        )

    @pytest.fixture
    def incompatible_v1_project(self):
        """Create an incompatible v1 project."""
        return UnifiedProject(
            name="v1-project",
            schema_version=1,
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3},
            statistics={'total_pages': 100, 'successful_pages': 90, 'failed_pages': 10}
        )

    @pytest.fixture
    def incompatible_v2_project(self):
        """Create an incompatible v2 project."""
        return UnifiedProject(
            name="v2-project",
            schema_version=2,
            type=ProjectType.DATA,
            settings={'chunk_size': 500, 'embedding_model': 'test-model'}
        )

    def test_checker_initialization(self, checker):
        """Test CompatibilityChecker initialization."""
        assert checker.current_version == SchemaVersion.CURRENT_VERSION
        assert hasattr(checker, 'logger')

    @pytest.mark.asyncio
    async def test_check_compatible_project(self, checker, compatible_project):
        """Test checking a compatible project."""
        result = await checker.check_project_compatibility(compatible_project)

        assert result.is_compatible is True
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert result.current_version == SchemaVersion.CURRENT_VERSION
        assert result.project_version == SchemaVersion.CURRENT_VERSION
        assert result.migration_required is False
        assert result.needs_recreation is False
        assert len(result.issues) == 0

    @pytest.mark.asyncio
    async def test_check_incompatible_v1_project(self, checker, incompatible_v1_project):
        """Test checking an incompatible v1 project."""
        result = await checker.check_project_compatibility(incompatible_v1_project)

        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert result.project_version == 1
        assert result.migration_required is True
        assert any("older schema version" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_incompatible_v2_project(self, checker, incompatible_v2_project):
        """Test checking an incompatible v2 project."""
        result = await checker.check_project_compatibility(incompatible_v2_project)

        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert result.project_version == 2
        assert result.migration_required is True

    @pytest.mark.asyncio
    async def test_check_future_version_project(self, checker):
        """Test checking a project with future schema version."""
        future_project = UnifiedProject(
            name="future-project",
            schema_version=10,  # Future version
            type=ProjectType.CRAWLING
        )

        result = await checker.check_project_compatibility(future_project)

        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert any("future schema version" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_project_with_invalid_timestamps(self, checker):
        """Test checking a project with invalid timestamp order."""
        now = datetime.utcnow()
        invalid_project = UnifiedProject(
            name="invalid-timestamps",
            created_at=now,
            updated_at=now - timedelta(hours=1),  # Updated before created
            last_crawl_at=now - timedelta(days=2)  # Crawled before created
        )

        result = await checker.check_project_compatibility(invalid_project)

        assert any("Updated timestamp is before created timestamp" in issue for issue in result.issues)
        assert any("Last crawl timestamp is before created timestamp" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_project_with_inconsistent_statistics(self, checker):
        """Test checking a project with inconsistent statistics."""
        invalid_stats_project = UnifiedProject(
            name="invalid-stats",
            statistics={
                'total_pages': 100,
                'successful_pages': 60,
                'failed_pages': 50  # 60 + 50 = 110 > 100
            }
        )

        result = await checker.check_project_compatibility(invalid_stats_project)

        assert any("Sum of successful and failed pages exceeds total pages" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_project_with_invalid_settings(self, checker):
        """Test checking a project with invalid type-specific settings."""
        invalid_settings_project = UnifiedProject(
            name="invalid-settings",
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 15}  # Invalid depth (> 10)
        )

        result = await checker.check_project_compatibility(invalid_settings_project)

        assert any("Invalid settings" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_project_without_type(self, checker):
        """Test checking a project without a specified type."""
        no_type_project = UnifiedProject(name="no-type", type=None)

        result = await checker.check_project_compatibility(no_type_project)

        assert any("Project type is not specified" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_project_with_missing_required_settings(self, checker):
        """Test checking projects with missing required type-specific settings."""
        # Crawling project missing crawl_depth
        crawling_project = UnifiedProject(
            name="incomplete-crawling",
            type=ProjectType.CRAWLING,
            settings={'rate_limit': 1.0}  # Missing crawl_depth
        )

        result = await checker.check_project_compatibility(crawling_project)
        assert any("Missing required setting" in issue and "crawl_depth" in issue for issue in result.issues)

        # Data project missing required settings
        data_project = UnifiedProject(
            name="incomplete-data",
            type=ProjectType.DATA,
            settings={'chunk_size': 500}  # Missing embedding_model
        )

        result = await checker.check_project_compatibility(data_project)
        assert any("Missing required setting" in issue and "embedding_model" in issue for issue in result.issues)

        # Storage project missing required settings
        storage_project = UnifiedProject(
            name="incomplete-storage",
            type=ProjectType.STORAGE,
            settings={}  # Missing enable_compression
        )

        result = await checker.check_project_compatibility(storage_project)
        assert any("Missing required setting" in issue and "enable_compression" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_database_compatibility_current_version(self, checker):
        """Test checking database compatibility for current version."""
        project_data = {
            'id': str(uuid.uuid4()),
            'name': 'test-project',
            'schema_version': SchemaVersion.CURRENT_VERSION,
            'type': 'crawling',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'settings': {'crawl_depth': 3},
            'statistics': {},
            'metadata': {},
            'compatibility_status': 'compatible'
        }

        result = await checker.check_database_compatibility(project_data)

        assert result.is_compatible is True
        assert result.status == CompatibilityStatus.COMPATIBLE

    @pytest.mark.asyncio
    async def test_check_database_compatibility_v1(self, checker):
        """Test checking database compatibility for v1 project."""
        v1_project_data = {
            'id': str(uuid.uuid4()),
            'name': 'v1-project',
            'schema_version': 1,
            'status': 'ready',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'source_url': 'https://example.com',
            'crawl_depth': 3,
            'total_pages': 100
        }

        result = await checker.check_database_compatibility(v1_project_data)

        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert result.migration_required is True
        assert any("Version 1 crawler project requires recreation" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_database_compatibility_v2(self, checker):
        """Test checking database compatibility for v2 project."""
        v2_project_data = {
            'id': str(uuid.uuid4()),
            'name': 'v2-project',
            'schema_version': 2,
            'type': 'data',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'settings': {'chunk_size': 500}
        }

        result = await checker.check_database_compatibility(v2_project_data)

        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert result.migration_required is True
        assert any("Version 2 logic project requires recreation" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_database_compatibility_unknown_version(self, checker):
        """Test checking database compatibility for unknown version."""
        unknown_version_data = {
            'id': str(uuid.uuid4()),
            'name': 'unknown-version',
            'schema_version': 99
        }

        result = await checker.check_database_compatibility(unknown_version_data)

        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert any("Unknown schema version: 99" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_database_compatibility_missing_version(self, checker):
        """Test checking database compatibility without schema_version field."""
        no_version_data = {
            'id': str(uuid.uuid4()),
            'name': 'no-version-project',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        result = await checker.check_database_compatibility(no_version_data)

        # Should default to version 1
        assert result.project_version == 1
        assert result.is_compatible is False

    @pytest.mark.asyncio
    async def test_check_project_compatibility_with_exception(self, checker, compatible_project):
        """Test handling exceptions during compatibility check."""
        with patch.object(checker, '_check_schema_version', side_effect=Exception("Test error")):
            result = await checker.check_project_compatibility(compatible_project)

            assert result.is_compatible is False
            assert result.status == CompatibilityStatus.INCOMPATIBLE
            assert any("Error during compatibility check: Test error" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_multiple_projects(self, checker, compatible_project, incompatible_v1_project):
        """Test checking multiple projects at once."""
        projects = [compatible_project, incompatible_v1_project]

        results = await checker.check_multiple_projects(projects)

        assert len(results) == 2
        assert compatible_project.id in results
        assert incompatible_v1_project.id in results

        # Compatible project result
        compatible_result = results[compatible_project.id]
        assert compatible_result.is_compatible is True

        # Incompatible project result
        incompatible_result = results[incompatible_v1_project.id]
        assert incompatible_result.is_compatible is False

    @pytest.mark.asyncio
    async def test_check_multiple_projects_with_errors(self, checker):
        """Test checking multiple projects when some checks fail."""
        # Create a mock project that will cause an error
        problematic_project = MagicMock()
        problematic_project.id = "error-project"
        problematic_project.schema_version = 3
        problematic_project.name = "error-project"

        # Create a normal project
        normal_project = UnifiedProject(name="normal", schema_version=3)

        projects = [problematic_project, normal_project]

        # Mock the check method to raise an exception for the problematic project
        original_check = checker.check_project_compatibility

        async def mock_check(project):
            if project.id == "error-project":
                raise Exception("Simulated error")
            return await original_check(project)

        with patch.object(checker, 'check_project_compatibility', side_effect=mock_check):
            results = await checker.check_multiple_projects(projects)

            assert len(results) == 2

            # Error project should have error result
            error_result = results["error-project"]
            assert error_result.is_compatible is False
            assert any("Error checking project: Simulated error" in issue for issue in error_result.issues)

            # Normal project should work
            normal_result = results[normal_project.id]
            assert normal_result.is_compatible is True

    def test_get_compatibility_summary(self, checker):
        """Test generating compatibility summary from results."""
        results = {
            'project1': CompatibilityResult(
                is_compatible=True,
                current_version=3,
                project_version=3,
                status=CompatibilityStatus.COMPATIBLE
            ),
            'project2': CompatibilityResult(
                is_compatible=False,
                current_version=3,
                project_version=1,
                status=CompatibilityStatus.INCOMPATIBLE,
                can_be_migrated=False
            ),
            'project3': CompatibilityResult(
                is_compatible=False,
                current_version=3,
                project_version=2,
                status=CompatibilityStatus.INCOMPATIBLE,
                can_be_migrated=True
            )
        }

        summary = checker.get_compatibility_summary(results)

        assert summary["total_projects"] == 3
        assert summary["compatible"] == 1
        assert summary["incompatible"] == 2
        assert summary["needs_recreation"] == 1  # Only project2 needs recreation
        assert summary["can_migrate"] == 1  # Only project3 can migrate
        assert summary["compatibility_rate"] == 33.3
        assert summary["version_distribution"] == {3: 1, 1: 1, 2: 1}

    def test_get_compatibility_summary_empty(self, checker):
        """Test generating compatibility summary with empty results."""
        summary = checker.get_compatibility_summary({})

        assert summary["total_projects"] == 0
        assert summary["compatible"] == 0
        assert summary["incompatible"] == 0
        assert summary["compatibility_rate"] == 0
        assert summary["version_distribution"] == {}

    def test_get_recreation_instructions_compatible(self, checker):
        """Test getting recreation instructions for compatible project."""
        compatible_result = CompatibilityResult(
            is_compatible=True,
            current_version=3,
            project_version=3,
            status=CompatibilityStatus.COMPATIBLE
        )

        instructions = checker.get_recreation_instructions(compatible_result, "test-project")

        assert len(instructions) == 1
        assert "already compatible" in instructions[0]

    def test_get_recreation_instructions_incompatible(self, checker):
        """Test getting recreation instructions for incompatible project."""
        incompatible_result = CompatibilityResult(
            is_compatible=False,
            current_version=3,
            project_version=1,
            status=CompatibilityStatus.INCOMPATIBLE
        )
        incompatible_result.add_issue("Version 1 project detected")
        incompatible_result.add_issue("Missing unified schema fields")

        instructions = checker.get_recreation_instructions(incompatible_result, "old-project")

        # Verify key instruction elements are present
        instructions_text = "\n".join(instructions)
        assert "old-project" in instructions_text
        assert "--export" in instructions_text
        assert "--recreate" in instructions_text
        assert "--confirm" in instructions_text
        assert "Version 1 project detected" in instructions_text
        assert "Missing unified schema fields" in instructions_text

    @pytest.mark.asyncio
    async def test_field_compatibility_check(self, checker):
        """Test field compatibility checking logic."""
        # Create project with all required fields
        complete_project = UnifiedProject(
            name="complete",
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3}
        )

        result = await checker.check_project_compatibility(complete_project)

        # Should not have missing field issues for a properly constructed UnifiedProject
        missing_issues = [issue for issue in result.issues if "Missing required field" in issue]
        assert len(missing_issues) == 0

    @pytest.mark.asyncio
    async def test_determine_final_status_logic(self, checker):
        """Test the final status determination logic."""
        # Test current version with no issues -> compatible
        current_no_issues = UnifiedProject(
            name="current-clean",
            schema_version=SchemaVersion.CURRENT_VERSION,
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3}
        )

        result = await checker.check_project_compatibility(current_no_issues)
        assert result.is_compatible is True
        assert result.status == CompatibilityStatus.COMPATIBLE

        # Test old version -> incompatible but potentially migratable
        old_version = UnifiedProject(
            name="old-version",
            schema_version=1,
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3}
        )

        with patch.object(SchemaVersion, 'can_migrate_from', return_value=True):
            result = await checker.check_project_compatibility(old_version)
            assert result.is_compatible is False
            assert result.status == CompatibilityStatus.INCOMPATIBLE
            assert result.can_be_migrated is True

    def test_version_distribution(self, checker):
        """Test version distribution calculation."""
        results = {
            'p1': CompatibilityResult(is_compatible=True, current_version=3, project_version=3, status=CompatibilityStatus.COMPATIBLE),
            'p2': CompatibilityResult(is_compatible=False, current_version=3, project_version=1, status=CompatibilityStatus.INCOMPATIBLE),
            'p3': CompatibilityResult(is_compatible=False, current_version=3, project_version=1, status=CompatibilityStatus.INCOMPATIBLE),
            'p4': CompatibilityResult(is_compatible=False, current_version=3, project_version=2, status=CompatibilityStatus.INCOMPATIBLE),
        }

        distribution = checker._get_version_distribution(results)

        assert distribution == {3: 1, 1: 2, 2: 1}


class TestCompatibilityCheckerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def checker(self):
        """Create a CompatibilityChecker instance."""
        return CompatibilityChecker()

    @pytest.mark.asyncio
    async def test_malformed_project_data(self, checker):
        """Test handling of malformed project data."""
        malformed_data = {
            'name': 'malformed',
            'schema_version': 'not-a-number',  # Invalid type
            'type': 'invalid-type'  # Invalid enum value
        }

        result = await checker.check_database_compatibility(malformed_data)
        assert result.is_compatible is False
        assert result.status == CompatibilityStatus.INCOMPATIBLE

    @pytest.mark.asyncio
    async def test_empty_project_data(self, checker):
        """Test handling of empty project data."""
        empty_data = {}

        result = await checker.check_database_compatibility(empty_data)
        assert result.is_compatible is False
        assert result.project_version == 1  # Default version

    @pytest.mark.asyncio
    async def test_project_with_null_values(self, checker):
        """Test handling of project with null/None values."""
        project_with_nulls = UnifiedProject(
            name="null-values",
            type=None,  # Null type
            source_url=None,  # Null URL
            last_crawl_at=None  # Null timestamp
        )

        result = await checker.check_project_compatibility(project_with_nulls)

        # Should handle nulls gracefully
        assert result is not None
        assert any("Project type is not specified" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, checker):
        """Test that concurrent checks don't interfere with each other."""
        import asyncio

        projects = [
            UnifiedProject(name=f"concurrent-{i}", schema_version=i % 3 + 1)
            for i in range(10)
        ]

        # Run multiple checks concurrently
        tasks = [checker.check_project_compatibility(project) for project in projects]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert isinstance(result, CompatibilityResult)

    @pytest.mark.asyncio
    async def test_extremely_large_project_data(self, checker):
        """Test handling of projects with extremely large data."""
        large_settings = {f"setting_{i}": f"value_{i}" for i in range(1000)}
        large_statistics = {f"stat_{i}": i for i in range(1000)}
        large_metadata = {f"meta_{i}": f"data_{i}" * 100 for i in range(100)}

        large_project = UnifiedProject(
            name="large-project",
            type=ProjectType.DATA,
            settings=large_settings,
            statistics=large_statistics,
            metadata=large_metadata
        )

        result = await checker.check_project_compatibility(large_project)

        # Should handle large data without errors
        assert result is not None
        assert isinstance(result.is_compatible, bool)

    def test_thread_safety(self, checker):
        """Test that checker methods are thread-safe for read operations."""
        # Test that multiple threads can access the same checker instance
        import threading

        results = []

        def check_summary():
            summary = checker.get_compatibility_summary({})
            results.append(summary)

        threads = [threading.Thread(target=check_summary) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10
        # All results should be identical for empty input
        for result in results:
            assert result == results[0]