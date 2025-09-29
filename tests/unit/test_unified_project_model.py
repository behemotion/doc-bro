"""Unit tests for UnifiedProject model validation."""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.logic.projects.models.project import ProjectType


class TestUnifiedProjectValidation:
    """Test validation logic for UnifiedProject model."""

    def test_minimal_valid_project_creation(self):
        """Test creating a project with minimal required fields."""
        project = UnifiedProject(name="test-project")

        assert project.name == "test-project"
        assert project.schema_version == SchemaVersion.CURRENT_VERSION
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE
        assert project.status == UnifiedProjectStatus.ACTIVE
        assert isinstance(project.id, str)
        assert len(project.id) == 36  # UUID format
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)
        assert project.settings == {}
        assert project.statistics == {}
        assert project.metadata == {}

    def test_name_validation_success(self):
        """Test valid project name formats."""
        valid_names = [
            "simple-name",
            "Name_With_Underscores",
            "Project 123",
            "a",
            "Multi Word Project",
            "snake_case_name",
            "kebab-case-name",
            "MixedCaseProject",
            "123-numeric-start"
        ]

        for name in valid_names:
            project = UnifiedProject(name=name)
            assert project.name == name.strip()

    def test_name_validation_failure(self):
        """Test invalid project name formats."""
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace only
            "name/with/slashes",
            "name\\with\\backslashes",
            "name:with:colons",
            "name*with*asterisks",
            "name?with?question",
            "name\"with\"quotes",
            "name<with>brackets",
            "name|with|pipes",
            "name@with@special",
            "name#with#hash",
            "name%with%percent",
            "name+with+plus",
            "name=with=equals",
            "name[with]square",
            "name{with}curly",
            "name(with)parens",
            "name.with.dots",
            "name,with,commas"
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                UnifiedProject(name=name)
            assert "name" in str(exc_info.value).lower()

    def test_name_length_validation(self):
        """Test project name length validation."""
        # Valid length range: 1-100 chars
        valid_long_name = "a" * 100
        project = UnifiedProject(name=valid_long_name)
        assert len(project.name) == 100

        # Too long
        too_long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            UnifiedProject(name=too_long_name)
        assert "at most 100 characters" in str(exc_info.value)

    def test_source_url_validation(self):
        """Test source URL validation."""
        valid_urls = [
            "https://example.com",
            "http://localhost:3000",
            "https://subdomain.example.com/path",
            "http://192.168.1.1:8080/docs",
            None  # None is allowed
        ]

        for url in valid_urls:
            project = UnifiedProject(name="test", source_url=url)
            assert project.source_url == url

        invalid_urls = [
            "ftp://example.com",
            "file:///path/to/file",
            "example.com",
            "//example.com",
            "not-a-url"
        ]

        for url in invalid_urls:
            with pytest.raises(ValidationError):
                UnifiedProject(name="test", source_url=url)

    def test_schema_version_validation(self):
        """Test schema version validation."""
        # Valid versions
        valid_versions = [1, 2, 3, 4, 10, 100]
        for version in valid_versions:
            project = UnifiedProject(name="test", schema_version=version)
            assert project.schema_version == version

        # Invalid versions
        invalid_versions = [0, -1, -10]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                UnifiedProject(name="test", schema_version=version)

    def test_type_specific_settings_validation_crawling(self):
        """Test crawling project type settings validation."""
        # Valid crawling settings
        valid_settings = {
            'crawl_depth': 5,
            'rate_limit': 2.5,
            'custom_setting': 'value'  # Custom settings allowed
        }

        project = UnifiedProject(
            name="crawl-test",
            type=ProjectType.CRAWLING,
            settings=valid_settings
        )
        assert project.settings['crawl_depth'] == 5
        assert project.settings['rate_limit'] == 2.5

        # Invalid crawl_depth
        invalid_depth_settings = [
            {'crawl_depth': 0},  # Too low
            {'crawl_depth': 11},  # Too high
            {'crawl_depth': -1},  # Negative
            {'crawl_depth': 'invalid'},  # Wrong type
            {'crawl_depth': 2.5}  # Float not allowed
        ]

        for settings in invalid_depth_settings:
            with pytest.raises(ValidationError):
                UnifiedProject(
                    name="test",
                    type=ProjectType.CRAWLING,
                    settings=settings
                )

        # Invalid rate_limit
        invalid_rate_settings = [
            {'rate_limit': 0},  # Zero
            {'rate_limit': -1},  # Negative
            {'rate_limit': 'invalid'}  # Wrong type
        ]

        for settings in invalid_rate_settings:
            with pytest.raises(ValidationError):
                UnifiedProject(
                    name="test",
                    type=ProjectType.CRAWLING,
                    settings=settings
                )

    def test_type_specific_settings_validation_data(self):
        """Test data project type settings validation."""
        # Valid data settings
        valid_settings = {
            'chunk_size': 1000,
            'embedding_model': 'mxbai-embed-large',
            'custom_setting': 'value'
        }

        project = UnifiedProject(
            name="data-test",
            type=ProjectType.DATA,
            settings=valid_settings
        )
        assert project.settings['chunk_size'] == 1000
        assert project.settings['embedding_model'] == 'mxbai-embed-large'

        # Invalid chunk_size
        invalid_chunk_settings = [
            {'chunk_size': 50},  # Too low
            {'chunk_size': 6000},  # Too high
            {'chunk_size': -100},  # Negative
            {'chunk_size': 'invalid'},  # Wrong type
            {'chunk_size': 500.5}  # Float not allowed
        ]

        for settings in invalid_chunk_settings:
            with pytest.raises(ValidationError):
                UnifiedProject(
                    name="test",
                    type=ProjectType.DATA,
                    settings=settings
                )

        # Invalid embedding_model
        invalid_model_settings = [
            {'embedding_model': ''},  # Empty
            {'embedding_model': '   '},  # Whitespace
            {'embedding_model': 123}  # Wrong type
        ]

        for settings in invalid_model_settings:
            with pytest.raises(ValidationError):
                UnifiedProject(
                    name="test",
                    type=ProjectType.DATA,
                    settings=settings
                )

    def test_type_specific_settings_validation_storage(self):
        """Test storage project type settings validation."""
        # Valid storage settings
        valid_settings = {
            'enable_compression': True,
            'custom_setting': 'value'
        }

        project = UnifiedProject(
            name="storage-test",
            type=ProjectType.STORAGE,
            settings=valid_settings
        )
        assert project.settings['enable_compression'] is True

        # Invalid enable_compression
        invalid_compression_settings = [
            {'enable_compression': 'yes'},  # String instead of bool
            {'enable_compression': 1},  # Integer instead of bool
            {'enable_compression': 'true'}  # String instead of bool
        ]

        for settings in invalid_compression_settings:
            with pytest.raises(ValidationError):
                UnifiedProject(
                    name="test",
                    type=ProjectType.STORAGE,
                    settings=settings
                )

    def test_statistics_consistency_validation(self):
        """Test statistics consistency validation."""
        # Valid consistent statistics
        valid_stats = {
            'total_pages': 100,
            'successful_pages': 80,
            'failed_pages': 20
        }

        project = UnifiedProject(name="test", statistics=valid_stats)
        assert project.statistics == valid_stats

        # Invalid: sum exceeds total
        invalid_stats = [
            {
                'total_pages': 100,
                'successful_pages': 60,
                'failed_pages': 50  # 60 + 50 = 110 > 100
            },
            {
                'total_pages': 50,
                'successful_pages': 30,
                'failed_pages': 25  # 30 + 25 = 55 > 50
            }
        ]

        for stats in invalid_stats:
            with pytest.raises(ValidationError) as exc_info:
                UnifiedProject(name="test", statistics=stats)
            assert "cannot exceed total pages" in str(exc_info.value)

    def test_compatibility_status_auto_correction(self):
        """Test automatic compatibility status correction."""
        # Schema version 3 should be compatible
        project = UnifiedProject(
            name="test",
            schema_version=3,
            compatibility_status=CompatibilityStatus.INCOMPATIBLE  # Wrong status
        )
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE

        # Schema version 1 should be incompatible
        project = UnifiedProject(
            name="test",
            schema_version=1,
            compatibility_status=CompatibilityStatus.COMPATIBLE  # Wrong status
        )
        assert project.compatibility_status == CompatibilityStatus.INCOMPATIBLE

    def test_datetime_field_validation(self):
        """Test datetime field handling."""
        now = datetime.now(timezone.utc)

        project = UnifiedProject(
            name="test",
            created_at=now,
            updated_at=now,
            last_crawl_at=now
        )

        assert project.created_at == now
        assert project.updated_at == now
        assert project.last_crawl_at == now

    def test_enum_field_validation(self):
        """Test enum field validation."""
        # Valid project type
        for project_type in ProjectType:
            project = UnifiedProject(name="test", type=project_type)
            assert project.type == project_type

        # Valid project status
        for status in UnifiedProjectStatus:
            project = UnifiedProject(name="test", status=status)
            assert project.status == status

        # Valid compatibility status
        for compat_status in CompatibilityStatus:
            # Note: this might get auto-corrected based on schema version
            project = UnifiedProject(
                name="test",
                compatibility_status=compat_status,
                schema_version=1 if compat_status == CompatibilityStatus.INCOMPATIBLE else 3
            )
            assert project.compatibility_status == compat_status

    def test_update_methods(self):
        """Test update methods update timestamps correctly."""
        project = UnifiedProject(name="test")
        original_updated_at = project.updated_at

        # Small delay to ensure timestamp change
        import time
        time.sleep(0.001)

        # Test update_status
        project.update_status(UnifiedProjectStatus.PROCESSING)
        assert project.status == UnifiedProjectStatus.PROCESSING
        assert project.updated_at > original_updated_at

        # Test update_settings
        updated_at_after_status = project.updated_at
        time.sleep(0.001)

        project.update_settings({'new_setting': 'value'})
        assert project.settings['new_setting'] == 'value'
        assert project.updated_at > updated_at_after_status

        # Test update_statistics
        updated_at_after_settings = project.updated_at
        time.sleep(0.001)

        project.update_statistics(total_pages=50)
        assert project.statistics['total_pages'] == 50
        assert project.updated_at > updated_at_after_settings

    def test_utility_methods(self):
        """Test utility methods return correct values."""
        # Compatible project
        compatible_project = UnifiedProject(
            name="compatible",
            schema_version=3,
            compatibility_status=CompatibilityStatus.COMPATIBLE,
            status=UnifiedProjectStatus.READY
        )

        assert compatible_project.is_compatible() is True
        assert compatible_project.allows_modification() is True
        assert compatible_project.needs_recreation() is False
        assert compatible_project.is_ready_for_search() is True

        # Incompatible project
        incompatible_project = UnifiedProject(
            name="incompatible",
            schema_version=1,
            compatibility_status=CompatibilityStatus.INCOMPATIBLE,
            status=UnifiedProjectStatus.FAILED
        )

        assert incompatible_project.is_compatible() is False
        assert incompatible_project.allows_modification() is False
        assert incompatible_project.needs_recreation() is True
        assert incompatible_project.is_ready_for_search() is False

    def test_is_outdated_method(self):
        """Test project outdated check."""
        from datetime import timedelta

        # Fresh project (no crawl)
        fresh_project = UnifiedProject(name="fresh")
        assert fresh_project.is_outdated() is True  # No crawl at all

        # Recent crawl
        recent_project = UnifiedProject(
            name="recent",
            last_crawl_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert recent_project.is_outdated() is False

        # Old crawl (default 24 hours)
        old_project = UnifiedProject(
            name="old",
            last_crawl_at=datetime.utcnow() - timedelta(hours=25)
        )
        assert old_project.is_outdated() is True

        # Custom max age
        assert old_project.is_outdated(max_age_hours=48) is False

    def test_operation_compatibility(self):
        """Test operation compatibility checking."""
        crawling_project = UnifiedProject(name="crawl", type=ProjectType.CRAWLING)
        data_project = UnifiedProject(name="data", type=ProjectType.DATA)
        storage_project = UnifiedProject(name="storage", type=ProjectType.STORAGE)

        # Crawling project operations
        assert crawling_project.is_compatible_with_operation('crawl') is True
        assert crawling_project.is_compatible_with_operation('search') is True
        assert crawling_project.is_compatible_with_operation('vector_operations') is True
        assert crawling_project.is_compatible_with_operation('upload') is False

        # Data project operations
        assert data_project.is_compatible_with_operation('upload') is True
        assert data_project.is_compatible_with_operation('search') is True
        assert data_project.is_compatible_with_operation('vector_operations') is True
        assert data_project.is_compatible_with_operation('document_processing') is True
        assert data_project.is_compatible_with_operation('crawl') is False

        # Storage project operations
        assert storage_project.is_compatible_with_operation('upload') is True
        assert storage_project.is_compatible_with_operation('download') is True
        assert storage_project.is_compatible_with_operation('file_management') is True
        assert storage_project.is_compatible_with_operation('tagging') is True
        assert storage_project.is_compatible_with_operation('search') is False

    def test_get_default_settings(self):
        """Test default settings for each project type."""
        crawling_project = UnifiedProject(name="crawl", type=ProjectType.CRAWLING)
        crawling_defaults = crawling_project.get_default_settings()
        assert 'crawl_depth' in crawling_defaults
        assert 'rate_limit' in crawling_defaults
        assert crawling_defaults['crawl_depth'] == 3
        assert crawling_defaults['rate_limit'] == 1.0

        data_project = UnifiedProject(name="data", type=ProjectType.DATA)
        data_defaults = data_project.get_default_settings()
        assert 'chunk_size' in data_defaults
        assert 'embedding_model' in data_defaults
        assert data_defaults['chunk_size'] == 500
        assert data_defaults['embedding_model'] == 'mxbai-embed-large'

        storage_project = UnifiedProject(name="storage", type=ProjectType.STORAGE)
        storage_defaults = storage_project.get_default_settings()
        assert 'enable_compression' in storage_defaults
        assert storage_defaults['enable_compression'] is True

    def test_path_generation(self):
        """Test project path generation."""
        project = UnifiedProject(name="test-paths")

        project_dir = project.get_project_directory()
        assert project_dir.endswith('docbro/projects/test-paths')

        db_path = project.get_database_path()
        assert db_path.endswith('test-paths/test-paths.db')

    def test_serialization_methods(self):
        """Test serialization and deserialization."""
        original = UnifiedProject(
            name="serialize-test",
            type=ProjectType.DATA,
            status=UnifiedProjectStatus.PROCESSING,
            settings={'chunk_size': 1000},
            statistics={'total_pages': 42},
            metadata={'description': 'Test project'}
        )

        # Test to_dict
        data = original.to_dict()
        assert data['name'] == 'serialize-test'
        assert data['type'] == 'data'
        assert data['status'] == 'processing'
        assert data['settings'] == {'chunk_size': 1000}
        assert data['statistics'] == {'total_pages': 42}
        assert data['metadata'] == {'description': 'Test project'}
        assert isinstance(data['created_at'], str)
        assert data['is_compatible'] is True

        # Test from_dict
        reconstructed = UnifiedProject.from_dict(data)
        assert reconstructed.name == original.name
        assert reconstructed.type == original.type
        assert reconstructed.status == original.status
        assert reconstructed.settings == original.settings
        assert reconstructed.statistics == original.statistics
        assert reconstructed.metadata == original.metadata

        # Test to_summary
        summary = original.to_summary()
        assert 'id' in summary
        assert 'name' in summary
        assert 'type' in summary
        assert 'status' in summary
        assert 'compatibility_status' in summary
        assert summary['page_count'] == 42  # From statistics

    def test_legacy_project_conversion(self):
        """Test conversion from legacy project schemas."""
        # Mock crawler project (simplified)
        class MockCrawlerProject:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.name = "crawler-project"
                self.total_pages = 100
                self.total_size_bytes = 1048576
                self.successful_pages = 95
                self.failed_pages = 5
                self.crawl_depth = 3
                self.embedding_model = "test-model"
                self.chunk_size = 500
                self.chunk_overlap = 50
                self.status = type('Status', (), {'value': 'ready'})()
                self.created_at = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                self.last_crawl_at = datetime.utcnow()
                self.source_url = "https://example.com"
                self.metadata = {"test": "data"}

        mock_crawler = MockCrawlerProject()
        unified = UnifiedProject.from_crawler_project(mock_crawler)

        assert unified.name == "crawler-project"
        assert unified.schema_version == 1
        assert unified.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert unified.type == ProjectType.CRAWLING
        assert unified.statistics['total_pages'] == 100
        assert unified.settings['crawl_depth'] == 3

        # Mock logic project (simplified)
        class MockLogicProject:
            def __init__(self):
                self.id = str(uuid.uuid4())
                self.name = "logic-project"
                self.type = ProjectType.DATA
                self.status = type('Status', (), {'value': 'active'})()
                self.created_at = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                self.settings = {"chunk_size": 1000}
                self.metadata = {"type": "data"}

        mock_logic = MockLogicProject()
        unified = UnifiedProject.from_logic_project(mock_logic)

        assert unified.name == "logic-project"
        assert unified.schema_version == 2
        assert unified.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert unified.type == ProjectType.DATA
        assert unified.settings == {"chunk_size": 1000}
        assert unified.statistics == {}  # Logic schema had no statistics

    def test_string_representations(self):
        """Test string representation methods."""
        project = UnifiedProject(
            name="string-test",
            type=ProjectType.CRAWLING,
            status=UnifiedProjectStatus.READY
        )

        str_repr = str(project)
        assert "string-test" in str_repr
        assert "crawling" in str_repr
        assert "ready" in str_repr
        assert "compatible" in str_repr

        repr_str = repr(project)
        assert "UnifiedProject" in repr_str
        assert "string-test" in repr_str
        assert "crawling" in repr_str
        assert "ready" in repr_str
        assert project.id in repr_str

    def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions."""
        # Project with None type
        no_type_project = UnifiedProject(name="no-type")
        assert no_type_project.type is None
        assert no_type_project.get_default_settings() == {}
        assert no_type_project.is_compatible_with_operation('any') is False

        # Project with empty collections
        empty_project = UnifiedProject(
            name="empty",
            settings={},
            statistics={},
            metadata={}
        )
        assert len(empty_project.settings) == 0
        assert len(empty_project.statistics) == 0
        assert len(empty_project.metadata) == 0

        # Project with maximum valid values
        max_project = UnifiedProject(
            name="a" * 100,  # Max name length
            schema_version=1000,  # Large schema version
            settings={'crawl_depth': 10},  # Max crawl depth
            type=ProjectType.CRAWLING
        )
        assert len(max_project.name) == 100
        assert max_project.schema_version == 1000


class TestUnifiedProjectBehaviorValidation:
    """Test behavioral aspects and complex validation scenarios."""

    def test_settings_update_validation_preserves_existing(self):
        """Test that settings updates preserve existing valid settings."""
        project = UnifiedProject(
            name="update-test",
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3, 'rate_limit': 1.0, 'custom': 'value'}
        )

        # Update with new settings
        project.update_settings({'crawl_depth': 5, 'new_setting': 'new_value'})

        # Should merge, not replace
        assert project.settings['crawl_depth'] == 5  # Updated
        assert project.settings['rate_limit'] == 1.0  # Preserved
        assert project.settings['custom'] == 'value'  # Preserved
        assert project.settings['new_setting'] == 'new_value'  # Added

    def test_settings_update_validation_fails_on_invalid(self):
        """Test that invalid settings updates fail validation."""
        project = UnifiedProject(
            name="validation-test",
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3}
        )

        # Should fail validation and not update
        with pytest.raises(ValueError):
            project.update_settings({'crawl_depth': 15})  # Invalid depth

        # Original settings should be unchanged
        assert project.settings['crawl_depth'] == 3

    def test_complex_validation_scenarios(self):
        """Test complex validation scenarios with multiple fields."""
        # Project with type but incompatible settings
        with pytest.raises(ValidationError):
            UnifiedProject(
                name="complex-test",
                type=ProjectType.DATA,
                settings={'crawl_depth': 5}  # Wrong setting for DATA type
            )

        # Project with valid settings for its type
        valid_complex = UnifiedProject(
            name="complex-valid",
            type=ProjectType.DATA,
            settings={
                'chunk_size': 1000,
                'embedding_model': 'test-model',
                'custom_setting': 'allowed'
            },
            statistics={
                'documents_processed': 50,
                'total_chunks': 500
            }
        )

        assert valid_complex.settings['chunk_size'] == 1000
        assert valid_complex.statistics['documents_processed'] == 50

    def test_concurrent_modification_safety(self):
        """Test that the model handles concurrent-like modifications safely."""
        project = UnifiedProject(name="concurrent-test")

        # Simulate rapid updates (testing timestamp ordering)
        original_time = project.updated_at

        project.update_status(UnifiedProjectStatus.PROCESSING)
        first_update = project.updated_at

        project.update_settings({'new': 'setting'})
        second_update = project.updated_at

        project.update_statistics(count=1)
        third_update = project.updated_at

        # Timestamps should be ordered
        assert original_time <= first_update <= second_update <= third_update

    def test_data_integrity_after_operations(self):
        """Test that data integrity is maintained after various operations."""
        project = UnifiedProject(
            name="integrity-test",
            type=ProjectType.CRAWLING,
            settings={'crawl_depth': 3},
            statistics={'total_pages': 100, 'successful_pages': 90, 'failed_pages': 10}
        )

        # Perform various operations
        project.update_status(UnifiedProjectStatus.READY)
        project.update_settings({'rate_limit': 2.0})
        project.update_statistics(processed_pages=90)

        # Verify integrity
        assert project.status == UnifiedProjectStatus.READY
        assert project.settings['crawl_depth'] == 3  # Preserved
        assert project.settings['rate_limit'] == 2.0  # Added
        assert project.statistics['total_pages'] == 100  # Preserved
        assert project.statistics['processed_pages'] == 90  # Added

        # Verify consistency still holds
        assert (project.statistics['successful_pages'] +
                project.statistics['failed_pages']) <= project.statistics['total_pages']