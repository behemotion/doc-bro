"""
Integration test for data project workflow

Tests end-to-end data project operations including:
- Project creation with data type
- Document upload and processing
- Vector storage integration
- Search functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.logic.projects.core.project_manager import ProjectManager
from src.logic.projects.models.project import Project, ProjectType, ProjectStatus
from src.logic.projects.models.config import ProjectConfig
from src.logic.projects.upload.upload_manager import UploadManager
from src.logic.projects.upload.sources.local_source import LocalSource
from src.logic.projects.models.upload import UploadSource, UploadSourceType


@pytest.fixture
async def project_manager():
    """Create project manager for testing"""
    manager = ProjectManager()
    await manager.initialize()
    return manager


@pytest.fixture
async def upload_manager():
    """Create upload manager for testing"""
    manager = UploadManager()
    await manager.initialize()
    return manager


@pytest.fixture
def sample_documents():
    """Create sample documents for testing"""
    temp_dir = tempfile.mkdtemp()

    # Create sample text document
    doc1_path = Path(temp_dir) / "document1.txt"
    doc1_path.write_text("This is a sample document for testing vector storage.")

    # Create sample markdown document
    doc2_path = Path(temp_dir) / "document2.md"
    doc2_path.write_text("# Test Document\n\nThis document tests markdown processing.")

    # Create sample JSON document
    doc3_path = Path(temp_dir) / "data.json"
    doc3_path.write_text('{"title": "Test Data", "content": "JSON document for testing"}')

    return temp_dir


@pytest.mark.asyncio
async def test_data_project_creation(project_manager):
    """Test creating a data project with appropriate settings"""
    project_name = "test-data-project"
    project_type = ProjectType.DATA

    # Create data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=project_type
    )

    assert project is not None
    assert project.name == project_name
    assert project.type == ProjectType.DATA
    assert project.status == ProjectStatus.ACTIVE

    # Verify data-specific settings
    config = await project_manager.get_project_config(project_name)
    assert config is not None
    assert "chunk_size" in config.type_specific_settings
    assert "embedding_model" in config.type_specific_settings
    assert "vector_store_type" in config.type_specific_settings


@pytest.mark.asyncio
async def test_document_upload_workflow(project_manager, upload_manager, sample_documents):
    """Test complete document upload and processing workflow"""
    project_name = "test-doc-upload"

    # Create data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    # Create upload source for local documents
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_documents,
        recursive=True
    )

    # Upload documents
    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is True
    assert result.files_processed > 0
    assert len(result.errors) == 0

    # Verify documents were processed
    stats = await project_manager.get_project_stats(project_name)
    assert stats["document_count"] > 0
    assert stats["chunk_count"] > 0


@pytest.mark.asyncio
async def test_vector_search_functionality(project_manager, upload_manager, sample_documents):
    """Test vector search functionality after document upload"""
    project_name = "test-vector-search"

    # Create and populate data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_documents,
        recursive=True
    )

    await upload_manager.upload_files(project=project, source=upload_source)

    # Get project handler for search operations
    project_handler = await project_manager.get_project_handler(project)

    # Test search functionality
    search_results = await project_handler.search_documents(
        project=project,
        query="sample document",
        limit=5
    )

    assert len(search_results) > 0
    assert all("content" in result for result in search_results)
    assert all("score" in result for result in search_results)


@pytest.mark.asyncio
async def test_data_project_settings_override(project_manager):
    """Test that data project settings properly override global defaults"""
    project_name = "test-settings-override"

    # Create data project with custom settings
    custom_settings = ProjectConfig(
        max_file_size=52428800,  # 50MB override
        allowed_formats=["txt", "md", "pdf"],
        type_specific_settings={
            "chunk_size": 1000,
            "embedding_model": "custom-model",
            "vector_store_type": "qdrant"
        }
    )

    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA,
        config=custom_settings
    )

    # Verify settings were applied
    config = await project_manager.get_project_config(project_name)
    assert config.max_file_size == 52428800
    assert config.type_specific_settings["chunk_size"] == 1000
    assert config.type_specific_settings["embedding_model"] == "custom-model"


@pytest.mark.asyncio
async def test_data_project_format_validation(project_manager, upload_manager):
    """Test that data projects validate document formats correctly"""
    project_name = "test-format-validation"

    # Create data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    # Create temporary file with invalid format
    temp_dir = tempfile.mkdtemp()
    invalid_file = Path(temp_dir) / "invalid.exe"
    invalid_file.write_bytes(b"Invalid binary content")

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=str(invalid_file)
    )

    # Attempt upload - should fail validation
    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is False
    assert len(result.errors) > 0
    assert "unsupported format" in result.errors[0].lower()


@pytest.mark.asyncio
async def test_concurrent_document_processing(project_manager, upload_manager, sample_documents):
    """Test that multiple documents can be processed concurrently"""
    project_name = "test-concurrent-processing"

    # Create data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    # Create multiple document batches
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_documents,
        recursive=True
    )

    # Start upload with progress tracking
    progress_updates = []

    def progress_callback(update):
        progress_updates.append(update)

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source,
        progress_callback=progress_callback
    )

    assert result.success is True
    assert len(progress_updates) > 0
    assert any(update.stage == "processing" for update in progress_updates)


@pytest.mark.asyncio
async def test_data_project_cleanup(project_manager):
    """Test that data project cleanup removes vector data"""
    project_name = "test-cleanup"

    # Create and populate data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    # Verify project exists
    retrieved = await project_manager.get_project(project_name)
    assert retrieved is not None

    # Remove project
    success = await project_manager.remove_project(project_name)
    assert success is True

    # Verify project and vector data removed
    removed = await project_manager.get_project(project_name)
    assert removed is None

    # Verify vector database cleanup occurred
    project_handler = await project_manager.get_project_handler(project)
    cleanup_success = await project_handler.verify_cleanup(project)
    assert cleanup_success is True


@pytest.mark.asyncio
async def test_data_project_error_recovery(project_manager, upload_manager):
    """Test error recovery during document processing"""
    project_name = "test-error-recovery"

    # Create data project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    # Create corrupted document
    temp_dir = tempfile.mkdtemp()
    corrupt_file = Path(temp_dir) / "corrupt.txt"
    corrupt_file.write_bytes(b"\x00\x01\x02\x03Invalid UTF-8")

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=str(corrupt_file)
    )

    # Upload should handle corruption gracefully
    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    # Should have warnings but not complete failure
    assert len(result.warnings) > 0
    assert "encoding error" in result.warnings[0].lower() or "corrupt" in result.warnings[0].lower()

    # Project should remain in valid state
    project_status = await project_manager.get_project(project_name)
    assert project_status.status != ProjectStatus.ERROR