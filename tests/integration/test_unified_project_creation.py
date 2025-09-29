"""Integration test for unified schema project creation (T011)."""

import pytest
from datetime import datetime

from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.logic.projects.models.project import ProjectType


class TestUnifiedProjectCreation:
    """Test unified schema project creation functionality."""

    def test_create_crawling_project_with_unified_schema(self):
        """Test creating a crawling project with unified schema."""
        # Create a new crawling project
        project = UnifiedProject(
            name="test-crawling-project",
            type=ProjectType.CRAWLING,
            source_url="https://example.com/docs",
            settings={
                "crawl_depth": 3,
                "rate_limit": 1.0,
                "max_file_size": 10485760
            },
            metadata={
                "description": "Test crawling project",
                "tags": ["test", "documentation"]
            }
        )

        # Verify unified schema properties
        assert project.schema_version == SchemaVersion.CURRENT_VERSION
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE
        assert project.type == ProjectType.CRAWLING
        assert project.status == UnifiedProjectStatus.ACTIVE
        assert project.source_url == "https://example.com/docs"

        # Verify settings are correctly stored
        assert project.settings["crawl_depth"] == 3
        assert project.settings["rate_limit"] == 1.0
        assert project.settings["max_file_size"] == 10485760

        # Verify metadata
        assert project.metadata["description"] == "Test crawling project"
        assert "test" in project.metadata["tags"]

        # Verify computed properties
        assert project.is_compatible()
        assert project.allows_modification()
        assert not project.needs_recreation()

        # Verify timestamps are set
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)
        assert project.last_crawl_at is None  # Not crawled yet

    def test_create_data_project_with_unified_schema(self):
        """Test creating a data project with unified schema."""
        project = UnifiedProject(
            name="test-data-project",
            type=ProjectType.DATA,
            settings={
                "chunk_size": 500,
                "chunk_overlap": 50,
                "embedding_model": "mxbai-embed-large",
                "vector_store_type": "sqlite_vec"
            },
            metadata={
                "description": "Test data project for document processing"
            }
        )

        # Verify unified schema properties
        assert project.schema_version == SchemaVersion.CURRENT_VERSION
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE
        assert project.type == ProjectType.DATA
        assert project.status == UnifiedProjectStatus.ACTIVE
        assert project.source_url is None  # Data projects don't require source URL

        # Verify data-specific settings
        assert project.settings["chunk_size"] == 500
        assert project.settings["chunk_overlap"] == 50
        assert project.settings["embedding_model"] == "mxbai-embed-large"
        assert project.settings["vector_store_type"] == "sqlite_vec"

        # Verify compatibility
        assert project.is_compatible()
        assert project.allows_modification()

    def test_create_storage_project_with_unified_schema(self):
        """Test creating a storage project with unified schema."""
        project = UnifiedProject(
            name="test-storage-project",
            type=ProjectType.STORAGE,
            settings={
                "enable_compression": True,
                "auto_tagging": True,
                "full_text_indexing": True,
                "max_file_size": 104857600
            },
            metadata={
                "description": "Test storage project for file management"
            }
        )

        # Verify unified schema properties
        assert project.schema_version == SchemaVersion.CURRENT_VERSION
        assert project.compatibility_status == CompatibilityStatus.COMPATIBLE
        assert project.type == ProjectType.STORAGE
        assert project.status == UnifiedProjectStatus.ACTIVE

        # Verify storage-specific settings
        assert project.settings["enable_compression"] is True
        assert project.settings["auto_tagging"] is True
        assert project.settings["full_text_indexing"] is True
        assert project.settings["max_file_size"] == 104857600

    def test_project_name_validation(self):
        """Test project name validation in unified schema."""
        # Valid names should pass
        valid_names = [
            "valid-project",
            "valid_project",
            "Valid Project 123",
            "project123",
            "My-Test_Project"
        ]

        for name in valid_names:
            project = UnifiedProject(
                name=name,
                type=ProjectType.DATA
            )
            assert project.name == name

        # Invalid names should fail
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace only
            "project/with/slash",  # Contains slash
            "project:with:colon",  # Contains colon
            "project*with*asterisk",  # Contains asterisk
            "project?with?question",  # Contains question mark
            "project<with>brackets",  # Contains brackets
            "project|with|pipe",  # Contains pipe
            "project\"with\"quotes",  # Contains quotes
        ]

        for name in invalid_names:
            with pytest.raises(ValueError):
                UnifiedProject(
                    name=name,
                    type=ProjectType.DATA
                )

    def test_settings_validation_by_type(self):
        """Test type-specific settings validation."""
        # Valid crawling settings
        UnifiedProject(
            name="crawling-test",
            type=ProjectType.CRAWLING,
            settings={
                "crawl_depth": 5,
                "rate_limit": 2.0
            }
        )

        # Invalid crawling settings
        with pytest.raises(ValueError, match="crawl_depth must be an integer between 1 and 10"):
            UnifiedProject(
                name="crawling-test-invalid",
                type=ProjectType.CRAWLING,
                settings={
                    "crawl_depth": 15  # Too high
                }
            )

        # Valid data settings
        UnifiedProject(
            name="data-test",
            type=ProjectType.DATA,
            settings={
                "chunk_size": 1000,
                "embedding_model": "test-model"
            }
        )

        # Invalid data settings
        with pytest.raises(ValueError, match="chunk_size must be an integer between 100 and 5000"):
            UnifiedProject(
                name="data-test-invalid",
                type=ProjectType.DATA,
                settings={
                    "chunk_size": 50  # Too small
                }
            )

        # Valid storage settings
        UnifiedProject(
            name="storage-test",
            type=ProjectType.STORAGE,
            settings={
                "enable_compression": True
            }
        )

        # Invalid storage settings
        with pytest.raises(ValueError, match="enable_compression must be a boolean"):
            UnifiedProject(
                name="storage-test-invalid",
                type=ProjectType.STORAGE,
                settings={
                    "enable_compression": "yes"  # Not a boolean
                }
            )

    def test_statistics_consistency_validation(self):
        """Test statistics consistency validation."""
        # Valid statistics
        project = UnifiedProject(
            name="stats-test",
            type=ProjectType.CRAWLING,
            statistics={
                "total_pages": 100,
                "successful_pages": 80,
                "failed_pages": 20
            }
        )
        assert project.statistics["total_pages"] == 100

        # Invalid statistics (sum exceeds total)
        with pytest.raises(ValueError, match="Sum of successful and failed pages cannot exceed total pages"):
            UnifiedProject(
                name="stats-test-invalid",
                type=ProjectType.CRAWLING,
                statistics={
                    "total_pages": 100,
                    "successful_pages": 80,
                    "failed_pages": 30  # 80 + 30 = 110 > 100
                }
            )

    def test_compatibility_status_auto_correction(self):
        """Test compatibility status auto-correction based on schema version."""
        # Create project with mismatched compatibility status
        project = UnifiedProject(
            name="compatibility-test",
            type=ProjectType.DATA,
            schema_version=1,  # Old version
            compatibility_status=CompatibilityStatus.COMPATIBLE  # Wrong status
        )

        # Should auto-correct to INCOMPATIBLE
        assert project.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert not project.is_compatible()
        assert not project.allows_modification()
        assert project.needs_recreation()

    def test_project_operations_compatibility(self):
        """Test project operation compatibility checking."""
        # Crawling project
        crawling_project = UnifiedProject(
            name="crawling-ops-test",
            type=ProjectType.CRAWLING
        )
        assert crawling_project.is_compatible_with_operation("crawl")
        assert crawling_project.is_compatible_with_operation("search")
        assert crawling_project.is_compatible_with_operation("vector_operations")
        assert not crawling_project.is_compatible_with_operation("upload")

        # Data project
        data_project = UnifiedProject(
            name="data-ops-test",
            type=ProjectType.DATA
        )
        assert data_project.is_compatible_with_operation("upload")
        assert data_project.is_compatible_with_operation("search")
        assert data_project.is_compatible_with_operation("vector_operations")
        assert data_project.is_compatible_with_operation("document_processing")
        assert not data_project.is_compatible_with_operation("crawl")

        # Storage project
        storage_project = UnifiedProject(
            name="storage-ops-test",
            type=ProjectType.STORAGE
        )
        assert storage_project.is_compatible_with_operation("upload")
        assert storage_project.is_compatible_with_operation("download")
        assert storage_project.is_compatible_with_operation("file_management")
        assert storage_project.is_compatible_with_operation("tagging")
        assert not storage_project.is_compatible_with_operation("vector_operations")

    def test_update_operations(self):
        """Test project update operations."""
        project = UnifiedProject(
            name="update-test",
            type=ProjectType.CRAWLING,
            settings={"crawl_depth": 3}
        )

        original_updated_at = project.updated_at

        # Test status update
        project.update_status(UnifiedProjectStatus.PROCESSING)
        assert project.status == UnifiedProjectStatus.PROCESSING
        assert project.updated_at > original_updated_at

        # Test settings update
        project.update_settings({"rate_limit": 2.0})
        assert project.settings["crawl_depth"] == 3  # Preserved
        assert project.settings["rate_limit"] == 2.0  # Added

        # Test statistics update
        project.update_statistics(total_pages=50, successful_pages=45)
        assert project.statistics["total_pages"] == 50
        assert project.statistics["successful_pages"] == 45

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        original_project = UnifiedProject(
            name="serialization-test",
            type=ProjectType.CRAWLING,
            source_url="https://example.com",
            settings={"crawl_depth": 3},
            statistics={"total_pages": 10},
            metadata={"description": "test"}
        )

        # Convert to dict
        project_dict = original_project.to_dict()

        # Verify dict contains all expected fields
        assert project_dict["name"] == "serialization-test"
        assert project_dict["type"] == "crawling"
        assert project_dict["schema_version"] == SchemaVersion.CURRENT_VERSION
        assert project_dict["compatibility_status"] == "compatible"
        assert project_dict["source_url"] == "https://example.com"
        assert project_dict["is_compatible"] is True
        assert project_dict["allows_modification"] is True
        assert project_dict["needs_recreation"] is False

        # Convert back to object
        restored_project = UnifiedProject.from_dict(project_dict)

        # Verify restoration
        assert restored_project.name == original_project.name
        assert restored_project.type == original_project.type
        assert restored_project.schema_version == original_project.schema_version
        assert restored_project.compatibility_status == original_project.compatibility_status
        assert restored_project.source_url == original_project.source_url
        assert restored_project.settings == original_project.settings
        assert restored_project.statistics == original_project.statistics
        assert restored_project.metadata == original_project.metadata

    def test_legacy_project_conversion(self):
        """Test conversion from legacy project schemas."""
        # This will be expanded when we implement the conversion methods
        # For now, just test that the conversion methods exist
        assert hasattr(UnifiedProject, 'from_crawler_project')
        assert hasattr(UnifiedProject, 'from_logic_project')

    def test_default_settings_by_type(self):
        """Test default settings retrieval by project type."""
        # Crawling project defaults
        crawling_project = UnifiedProject(name="crawling-defaults", type=ProjectType.CRAWLING)
        defaults = crawling_project.get_default_settings()
        assert "crawl_depth" in defaults
        assert "rate_limit" in defaults
        assert "user_agent" in defaults
        assert defaults["crawl_depth"] == 3
        assert defaults["rate_limit"] == 1.0

        # Data project defaults
        data_project = UnifiedProject(name="data-defaults", type=ProjectType.DATA)
        defaults = data_project.get_default_settings()
        assert "chunk_size" in defaults
        assert "embedding_model" in defaults
        assert "vector_store_type" in defaults
        assert defaults["chunk_size"] == 500
        assert defaults["embedding_model"] == "mxbai-embed-large"

        # Storage project defaults
        storage_project = UnifiedProject(name="storage-defaults", type=ProjectType.STORAGE)
        defaults = storage_project.get_default_settings()
        assert "enable_compression" in defaults
        assert "auto_tagging" in defaults
        assert defaults["enable_compression"] is True
        assert defaults["auto_tagging"] is True

        # Project without type
        typeless_project = UnifiedProject(name="typeless")
        defaults = typeless_project.get_default_settings()
        assert defaults == {}

    def test_project_summary(self):
        """Test project summary generation."""
        project = UnifiedProject(
            name="summary-test",
            type=ProjectType.CRAWLING,
            statistics={"total_pages": 42}
        )

        summary = project.to_summary()
        assert summary["name"] == "summary-test"
        assert summary["type"] == "crawling"
        assert summary["compatibility_status"] == "compatible"
        assert summary["page_count"] == 42
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_string_representations(self):
        """Test string representations of unified project."""
        project = UnifiedProject(
            name="string-test",
            type=ProjectType.DATA
        )

        str_repr = str(project)
        assert "string-test" in str_repr
        assert "data" in str_repr
        assert "active" in str_repr
        assert "compatible" in str_repr

        repr_str = repr(project)
        assert "UnifiedProject" in repr_str
        assert project.id in repr_str
        assert "string-test" in repr_str
        assert "schema_v3" in repr_str