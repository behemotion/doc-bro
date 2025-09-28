"""
Integration test for storage project workflow

Tests end-to-end storage project operations including:
- Project creation with storage type
- File upload and inventory management
- File search and tagging
- Retrieval operations
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
def sample_files():
    """Create sample files for storage testing"""
    temp_dir = tempfile.mkdtemp()

    # Create various file types
    files = {
        "image1.jpg": b"\xFF\xD8\xFF\xE0\x00\x10JFIF",  # JPEG header
        "image2.png": b"\x89PNG\r\n\x1a\n",  # PNG header
        "document.pdf": b"%PDF-1.4",  # PDF header
        "archive.zip": b"PK\x03\x04",  # ZIP header
        "text.txt": b"Sample text content",
        "data.json": b'{"test": "data"}',
        "code.py": b"print('Hello World')"
    }

    for filename, content in files.items():
        file_path = Path(temp_dir) / filename
        file_path.write_bytes(content)

    return temp_dir


@pytest.mark.asyncio
async def test_storage_project_creation(project_manager):
    """Test creating a storage project with appropriate settings"""
    project_name = "test-storage-project"
    project_type = ProjectType.STORAGE

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=project_type
    )

    assert project is not None
    assert project.name == project_name
    assert project.type == ProjectType.STORAGE
    assert project.status == ProjectStatus.ACTIVE

    # Verify storage-specific settings
    config = await project_manager.get_project_config(project_name)
    assert config is not None
    assert "enable_compression" in config.type_specific_settings
    assert "auto_tagging" in config.type_specific_settings
    assert "full_text_indexing" in config.type_specific_settings


@pytest.mark.asyncio
async def test_file_upload_and_inventory(project_manager, upload_manager, sample_files):
    """Test file upload and inventory creation workflow"""
    project_name = "test-file-upload"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Create upload source for sample files
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_files,
        recursive=True
    )

    # Upload files
    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is True
    assert result.files_processed > 0
    assert len(result.errors) == 0

    # Verify inventory was created
    stats = await project_manager.get_project_stats(project_name)
    assert stats["file_count"] > 0
    assert stats["total_size"] > 0


@pytest.mark.asyncio
async def test_file_tagging_functionality(project_manager, upload_manager, sample_files):
    """Test file tagging and tag-based search"""
    project_name = "test-file-tagging"

    # Create and populate storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_files,
        recursive=True
    )

    await upload_manager.upload_files(project=project, source=upload_source)

    # Get project handler for file operations
    project_handler = await project_manager.get_project_handler(project)

    # Get file inventory
    inventory = await project_handler.get_file_inventory(project)
    assert len(inventory) > 0

    # Tag first file
    first_file = inventory[0]
    tags = ["important", "test-file", "sample"]

    success = await project_handler.tag_file(
        project=project,
        file_id=first_file["id"],
        tags=tags
    )
    assert success is True

    # Search files by tag
    search_results = await project_handler.search_files(
        project=project,
        query="important",
        filters={"search_type": "tag"}
    )

    assert len(search_results) > 0
    assert any(first_file["id"] == result["id"] for result in search_results)


@pytest.mark.asyncio
async def test_file_retrieval_workflow(project_manager, upload_manager, sample_files):
    """Test file storage and retrieval workflow"""
    project_name = "test-file-retrieval"

    # Create and populate storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_files,
        recursive=True
    )

    await upload_manager.upload_files(project=project, source=upload_source)

    # Get project handler
    project_handler = await project_manager.get_project_handler(project)

    # Get file inventory
    inventory = await project_handler.get_file_inventory(project)
    test_file = inventory[0]

    # Retrieve file to temporary location
    temp_output = tempfile.mkdtemp()
    output_path = Path(temp_output) / "retrieved_file"

    success = await project_handler.retrieve_file(
        project=project,
        file_id=test_file["id"],
        output_path=str(output_path)
    )

    assert success is True
    assert output_path.exists()

    # Verify file integrity
    original_size = test_file["file_size"]
    retrieved_size = output_path.stat().st_size
    assert retrieved_size == original_size


@pytest.mark.asyncio
async def test_storage_project_search_functionality(project_manager, upload_manager, sample_files):
    """Test comprehensive file search functionality"""
    project_name = "test-storage-search"

    # Create and populate storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_files,
        recursive=True
    )

    await upload_manager.upload_files(project=project, source=upload_source)

    # Get project handler
    project_handler = await project_manager.get_project_handler(project)

    # Test filename search
    search_results = await project_handler.search_files(
        project=project,
        query="image",
        filters={"search_type": "filename"}
    )

    image_files = [f for f in search_results if "image" in f["filename"].lower()]
    assert len(image_files) > 0

    # Test MIME type filtering
    search_results = await project_handler.search_files(
        project=project,
        query="*",
        filters={"mime_type": "image/*"}
    )

    assert all("image" in result["mime_type"] for result in search_results)

    # Test size filtering
    search_results = await project_handler.search_files(
        project=project,
        query="*",
        filters={"min_size": 0, "max_size": 1000}
    )

    assert all(result["file_size"] <= 1000 for result in search_results)


@pytest.mark.asyncio
async def test_storage_project_settings_override(project_manager):
    """Test that storage project settings properly override global defaults"""
    project_name = "test-storage-settings"

    # Create storage project with custom settings
    custom_settings = ProjectConfig(
        max_file_size=104857600,  # 100MB override
        allowed_formats=["jpg", "png", "pdf", "zip", "txt"],
        type_specific_settings={
            "enable_compression": True,
            "auto_tagging": True,
            "full_text_indexing": True
        }
    )

    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE,
        config=custom_settings
    )

    # Verify settings were applied
    config = await project_manager.get_project_config(project_name)
    assert config.max_file_size == 104857600
    assert config.type_specific_settings["enable_compression"] is True
    assert config.type_specific_settings["auto_tagging"] is True


@pytest.mark.asyncio
async def test_storage_project_format_validation(project_manager, upload_manager):
    """Test that storage projects validate file formats correctly"""
    project_name = "test-storage-validation"

    # Create storage project with restricted formats
    custom_settings = ProjectConfig(
        allowed_formats=["txt", "pdf"],
        type_specific_settings={}
    )

    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE,
        config=custom_settings
    )

    # Create temporary file with disallowed format
    temp_dir = tempfile.mkdtemp()
    invalid_file = Path(temp_dir) / "test.exe"
    invalid_file.write_bytes(b"Executable content")

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
async def test_concurrent_file_operations(project_manager, upload_manager, sample_files):
    """Test concurrent file upload and processing"""
    project_name = "test-concurrent-storage"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Upload files with progress tracking
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_files,
        recursive=True
    )

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
async def test_storage_project_cleanup(project_manager, upload_manager, sample_files):
    """Test that storage project cleanup removes all stored files"""
    project_name = "test-storage-cleanup"

    # Create and populate storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=sample_files,
        recursive=True
    )

    await upload_manager.upload_files(project=project, source=upload_source)

    # Verify files were stored
    stats = await project_manager.get_project_stats(project_name)
    assert stats["file_count"] > 0

    # Remove project
    success = await project_manager.remove_project(project_name)
    assert success is True

    # Verify project and stored files removed
    removed = await project_manager.get_project(project_name)
    assert removed is None

    # Verify file storage cleanup occurred
    project_handler = await project_manager.get_project_handler(project)
    cleanup_success = await project_handler.verify_cleanup(project)
    assert cleanup_success is True


@pytest.mark.asyncio
async def test_file_conflict_resolution(project_manager, upload_manager):
    """Test file conflict detection and resolution"""
    project_name = "test-file-conflicts"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Create file and upload it
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "conflict_test.txt"
    test_file.write_text("Original content")

    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=str(test_file)
    )

    # First upload
    result1 = await upload_manager.upload_files(project=project, source=upload_source)
    assert result1.success is True

    # Modify file and upload again (should detect conflict)
    test_file.write_text("Modified content")

    result2 = await upload_manager.upload_files(
        project=project,
        source=upload_source,
        conflict_resolution="rename"
    )

    assert result2.success is True

    # Verify both versions exist
    project_handler = await project_manager.get_project_handler(project)
    inventory = await project_handler.get_file_inventory(project)

    conflict_files = [f for f in inventory if "conflict_test" in f["filename"]]
    assert len(conflict_files) >= 2  # Original and renamed version