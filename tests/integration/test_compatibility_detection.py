"""Integration test for compatibility detection for old projects (T012)."""

import pytest
from datetime import datetime

from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.models.project import Project as CrawlerProject, ProjectStatus as CrawlerProjectStatus
from src.logic.projects.models.project import Project as LogicProject, ProjectType, ProjectStatus as LogicProjectStatus


class TestCompatibilityDetection:
    """Test compatibility detection for legacy projects."""

    def test_detect_compatible_current_schema_project(self):
        """Test detection of projects with current schema version."""
        # Create project with current schema version
        project = UnifiedProject(
            name="current-schema-project",
            type=ProjectType.CRAWLING,
            schema_version=SchemaVersion.CURRENT_VERSION
        )

        # Should be detected as compatible
        assert project.schema_version == SchemaVersion.CURRENT_VERSION
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE
        assert project.is_compatible()
        assert project.allows_modification()
        assert not project.needs_recreation()

    def test_detect_incompatible_v1_schema_project(self):
        """Test detection of projects with schema version 1 (crawler schema)."""
        # Simulate old crawler schema project
        project = UnifiedProject(
            name="v1-crawler-project",
            type=ProjectType.CRAWLING,
            schema_version=1,  # Old crawler schema version
            source_url="https://example.com",
            settings={
                # Old crawler schema fields mapped to settings
                "crawl_depth": 2,
                "embedding_model": "mxbai-embed-large",
                "chunk_size": 1000,
                "chunk_overlap": 100
            },
            statistics={
                # Old crawler schema statistics
                "total_pages": 50,
                "total_size_bytes": 1024000,
                "successful_pages": 45,
                "failed_pages": 5
            }
        )

        # Should be detected as incompatible
        assert project.schema_version == 1
        assert project.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert not project.is_compatible()
        assert not project.allows_modification()
        assert project.needs_recreation()

        # Should still have read access to data
        assert project.name == "v1-crawler-project"
        assert project.source_url == "https://example.com"
        assert project.settings["crawl_depth"] == 2
        assert project.statistics["total_pages"] == 50

    def test_detect_incompatible_v2_schema_project(self):
        """Test detection of projects with schema version 2 (logic schema)."""
        # Simulate old logic schema project
        project = UnifiedProject(
            name="v2-logic-project",
            type=ProjectType.DATA,
            schema_version=2,  # Old logic schema version
            settings={
                "chunk_size": 500,
                "embedding_model": "mxbai-embed-large",
                "enable_tagging": True
            },
            metadata={
                "description": "Old logic schema project",
                "created_by": "user123"
            }
        )

        # Should be detected as incompatible
        assert project.schema_version == 2
        assert project.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert not project.is_compatible()
        assert not project.allows_modification()
        assert project.needs_recreation()

        # Should still have read access to data
        assert project.name == "v2-logic-project"
        assert project.type == ProjectType.DATA
        assert project.settings["chunk_size"] == 500
        assert project.metadata["description"] == "Old logic schema project"

    def test_detect_future_schema_version(self):
        """Test detection of projects with future schema versions."""
        # Simulate project with future schema version
        project = UnifiedProject(
            name="future-schema-project",
            type=ProjectType.STORAGE,
            schema_version=99  # Future version
        )

        # Should be detected as incompatible (future versions are not supported)
        assert project.schema_version == 99
        assert project.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert not project.is_compatible()
        assert not project.allows_modification()
        assert project.needs_recreation()

    def test_compatibility_status_from_schema_version(self):
        """Test CompatibilityStatus.from_schema_version method."""
        current_version = SchemaVersion.CURRENT_VERSION

        # Current version should be compatible
        status = CompatibilityStatus.from_schema_version(current_version, current_version)
        assert status == CompatibilityStatus.COMPATIBLE

        # Older versions should be incompatible
        status = CompatibilityStatus.from_schema_version(1, current_version)
        assert status == CompatibilityStatus.INCOMPATIBLE

        status = CompatibilityStatus.from_schema_version(2, current_version)
        assert status == CompatibilityStatus.INCOMPATIBLE

        # Future versions should be incompatible
        status = CompatibilityStatus.from_schema_version(99, current_version)
        assert status == CompatibilityStatus.INCOMPATIBLE

    def test_schema_version_validation_methods(self):
        """Test SchemaVersion validation methods."""
        current = SchemaVersion.CURRENT_VERSION

        # Test current version checks
        assert SchemaVersion.is_current_version(current)
        assert not SchemaVersion.is_current_version(1)
        assert not SchemaVersion.is_current_version(2)
        assert not SchemaVersion.is_current_version(99)

        # Test compatibility checks
        assert SchemaVersion.is_compatible_version(current)
        assert not SchemaVersion.is_compatible_version(1)
        assert not SchemaVersion.is_compatible_version(2)
        assert not SchemaVersion.is_compatible_version(99)

        # Test recreation requirements
        assert not SchemaVersion.requires_recreation(current)
        assert SchemaVersion.requires_recreation(1)
        assert SchemaVersion.requires_recreation(2)
        assert SchemaVersion.requires_recreation(99)

        # Test migration capabilities (currently not supported)
        assert not SchemaVersion.can_migrate_from(1)
        assert not SchemaVersion.can_migrate_from(2)
        assert not SchemaVersion.can_migrate_from(99)

    def test_conversion_from_crawler_project(self):
        """Test conversion from crawler schema project."""
        # Create a mock crawler project
        crawler_project = type('MockCrawlerProject', (), {
            'id': 'crawler-123',
            'name': 'test-crawler',
            'source_url': 'https://docs.example.com',
            'status': type('Status', (), {'value': 'ready'})(),
            'crawl_depth': 3,
            'embedding_model': 'mxbai-embed-large',
            'chunk_size': 1000,
            'chunk_overlap': 100,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'last_crawl_at': datetime.now(),
            'total_pages': 25,
            'total_size_bytes': 512000,
            'successful_pages': 23,
            'failed_pages': 2,
            'metadata': {'description': 'Test crawler project'}
        })()

        # Convert to unified project
        unified = UnifiedProject.from_crawler_project(crawler_project)

        # Verify conversion
        assert unified.id == 'crawler-123'
        assert unified.name == 'test-crawler'
        assert unified.schema_version == 1  # Crawler was version 1
        assert unified.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert unified.type == ProjectType.CRAWLING
        assert unified.source_url == 'https://docs.example.com'

        # Verify settings mapping
        assert unified.settings['crawl_depth'] == 3
        assert unified.settings['embedding_model'] == 'mxbai-embed-large'
        assert unified.settings['chunk_size'] == 1000
        assert unified.settings['chunk_overlap'] == 100

        # Verify statistics mapping
        assert unified.statistics['total_pages'] == 25
        assert unified.statistics['total_size_bytes'] == 512000
        assert unified.statistics['successful_pages'] == 23
        assert unified.statistics['failed_pages'] == 2

        # Verify status mapping
        assert unified.status == UnifiedProjectStatus.READY

    def test_conversion_from_logic_project(self):
        """Test conversion from logic schema project."""
        # Create a mock logic project
        logic_project = type('MockLogicProject', (), {
            'id': 'logic-456',
            'name': 'test-logic',
            'type': ProjectType.DATA,
            'status': type('Status', (), {'value': 'active'})(),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'settings': {
                'chunk_size': 500,
                'embedding_model': 'test-model',
                'enable_compression': True
            },
            'metadata': {'description': 'Test logic project', 'version': '1.0'}
        })()

        # Convert to unified project
        unified = UnifiedProject.from_logic_project(logic_project)

        # Verify conversion
        assert unified.id == 'logic-456'
        assert unified.name == 'test-logic'
        assert unified.schema_version == 2  # Logic was version 2
        assert unified.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert unified.type == ProjectType.DATA

        # Verify settings preservation
        assert unified.settings['chunk_size'] == 500
        assert unified.settings['embedding_model'] == 'test-model'
        assert unified.settings['enable_compression'] is True

        # Verify metadata preservation
        assert unified.metadata['description'] == 'Test logic project'
        assert unified.metadata['version'] == '1.0'

        # Verify status mapping
        assert unified.status == UnifiedProjectStatus.ACTIVE

        # Logic projects don't have statistics initially
        assert unified.statistics == {}
        assert unified.source_url is None

    def test_compatibility_properties_behavior(self):
        """Test behavior of compatibility-related properties."""
        # Compatible project
        compatible = UnifiedProject(
            name="compatible-test",
            type=ProjectType.CRAWLING,
            schema_version=SchemaVersion.CURRENT_VERSION
        )

        assert compatible.compatibility_status.allows_modification
        assert not compatible.compatibility_status.needs_recreation
        assert not compatible.compatibility_status.is_transitional

        # Incompatible project
        incompatible = UnifiedProject(
            name="incompatible-test",
            type=ProjectType.CRAWLING,
            schema_version=1
        )

        assert not incompatible.compatibility_status.allows_modification
        assert incompatible.compatibility_status.needs_recreation
        assert not incompatible.compatibility_status.is_transitional

        # Migrating project
        migrating = UnifiedProject(
            name="migrating-test",
            type=ProjectType.CRAWLING,
            compatibility_status=CompatibilityStatus.MIGRATING
        )

        assert not migrating.compatibility_status.allows_modification
        assert not migrating.compatibility_status.needs_recreation
        assert migrating.compatibility_status.is_transitional

    def test_mixed_schema_project_listing(self):
        """Test handling mixed schema versions in project listings."""
        projects = [
            # Current schema project
            UnifiedProject(
                name="current-project",
                type=ProjectType.CRAWLING,
                schema_version=SchemaVersion.CURRENT_VERSION
            ),
            # Legacy crawler project
            UnifiedProject(
                name="legacy-crawler",
                type=ProjectType.CRAWLING,
                schema_version=1
            ),
            # Legacy logic project
            UnifiedProject(
                name="legacy-logic",
                type=ProjectType.DATA,
                schema_version=2
            )
        ]

        # Verify each project's compatibility
        current, crawler, logic = projects

        assert current.is_compatible()
        assert not crawler.is_compatible()
        assert not logic.is_compatible()

        # Count compatible vs incompatible
        compatible_count = sum(1 for p in projects if p.is_compatible())
        incompatible_count = sum(1 for p in projects if not p.is_compatible())

        assert compatible_count == 1
        assert incompatible_count == 2

        # Verify read access for all projects
        for project in projects:
            assert project.name  # Can read name
            assert project.type  # Can read type
            assert isinstance(project.created_at, datetime)  # Can read timestamps

    def test_schema_version_history(self):
        """Test schema version history tracking."""
        history = SchemaVersion.get_version_history()

        # Should have all versions
        assert len(history) == 3
        versions = [v.version for v in history]
        assert 1 in versions  # Crawler schema
        assert 2 in versions  # Logic schema
        assert 3 in versions  # Unified schema

        # Verify version 1 details (crawler schema)
        v1 = SchemaVersion.get_version_info(1)
        assert v1 is not None
        assert v1.name == "Original Crawler Schema"
        assert "total_pages" in v1.fields_added
        assert "crawl_depth" in v1.fields_added

        # Verify version 2 details (logic schema)
        v2 = SchemaVersion.get_version_info(2)
        assert v2 is not None
        assert v2.name == "Project Logic Schema"
        assert "type" in v2.fields_added
        assert "settings" in v2.fields_added

        # Verify version 3 details (unified schema)
        v3 = SchemaVersion.get_version_info(3)
        assert v3 is not None
        assert v3.name == "Unified Schema"
        assert "schema_version" in v3.fields_added
        assert "compatibility_status" in v3.fields_added

    def test_invalid_schema_version_handling(self):
        """Test handling of invalid schema versions."""
        # Non-existent version
        version_info = SchemaVersion.get_version_info(999)
        assert version_info is None

        # Zero or negative version
        with pytest.raises(ValueError):
            UnifiedProject(
                name="invalid-version",
                type=ProjectType.DATA,
                schema_version=0
            )

        with pytest.raises(ValueError):
            UnifiedProject(
                name="negative-version",
                type=ProjectType.DATA,
                schema_version=-1
            )

    def test_compatibility_summary_information(self):
        """Test compatibility summary information."""
        # Compatible project
        compatible = UnifiedProject(
            name="compatible-summary",
            type=ProjectType.CRAWLING
        )
        summary = compatible.to_summary()
        assert summary["compatibility_status"] == "compatible"

        # Incompatible project
        incompatible = UnifiedProject(
            name="incompatible-summary",
            type=ProjectType.CRAWLING,
            schema_version=1
        )
        summary = incompatible.to_summary()
        assert summary["compatibility_status"] == "incompatible"

        # Dict representation includes compatibility flags
        dict_repr = incompatible.to_dict()
        assert dict_repr["is_compatible"] is False
        assert dict_repr["allows_modification"] is False
        assert dict_repr["needs_recreation"] is True