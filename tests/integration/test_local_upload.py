"""
Integration test for local file upload functionality

Tests end-to-end local file upload operations including:
- Single file upload
- Directory upload (recursive and non-recursive)
- File validation and filtering
- Progress tracking
- Error handling
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.logic.projects.core.project_manager import ProjectManager
from src.logic.projects.upload.upload_manager import UploadManager
from src.logic.projects.upload.sources.local_source import LocalSource
from src.logic.projects.models.project import Project, ProjectType, ProjectStatus
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
def test_file_structure():
    """Create comprehensive test file structure"""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)

    # Create directory structure
    (base_path / "documents").mkdir()
    (base_path / "images").mkdir()
    (base_path / "code").mkdir()
    (base_path / "archives").mkdir()
    (base_path / "nested" / "deep").mkdir(parents=True)

    # Create various file types
    files = {
        "documents/readme.txt": "This is a text file for testing.",
        "documents/manual.pdf": b"%PDF-1.4\n",  # PDF header
        "documents/data.json": '{"test": "data", "type": "document"}',
        "images/photo.jpg": b"\xFF\xD8\xFF\xE0\x00\x10JFIF",  # JPEG header
        "images/diagram.png": b"\x89PNG\r\n\x1a\n",  # PNG header
        "code/script.py": "print('Hello, World!')",
        "code/config.yaml": "database:\n  host: localhost\n  port: 5432",
        "archives/backup.zip": b"PK\x03\x04",  # ZIP header
        "archives/data.tar.gz": b"\x1f\x8b\x08",  # GZIP header
        "nested/deep/hidden.txt": "Deep nested file content",
        "large_file.bin": b"x" * 1048576,  # 1MB binary file
        "empty_file.txt": "",
        "special chars file (test).txt": "File with special characters in name"
    }

    for file_path, content in files.items():
        full_path = base_path / file_path
        if isinstance(content, str):
            full_path.write_text(content)
        else:
            full_path.write_bytes(content)

    return str(base_path)


@pytest.mark.asyncio
async def test_single_file_upload(project_manager, upload_manager, test_file_structure):
    """Test uploading a single file"""
    project_name = "test-single-upload"

    # Create data project for document uploads
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA
    )

    # Upload single file
    test_file = Path(test_file_structure) / "documents" / "readme.txt"
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=str(test_file)
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is True
    assert result.files_processed == 1
    assert result.files_total == 1
    assert len(result.errors) == 0

    # Verify file was processed
    stats = await project_manager.get_project_stats(project_name)
    assert stats["document_count"] >= 1


@pytest.mark.asyncio
async def test_directory_upload_non_recursive(project_manager, upload_manager, test_file_structure):
    """Test uploading directory contents without recursion"""
    project_name = "test-dir-non-recursive"

    # Create storage project for file uploads
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Upload documents directory (non-recursive)
    docs_dir = Path(test_file_structure) / "documents"
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=str(docs_dir),
        recursive=False
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is True
    assert result.files_processed == 3  # readme.txt, manual.pdf, data.json
    assert len(result.errors) == 0

    # Verify nested files were not included
    stats = await project_manager.get_project_stats(project_name)
    assert stats["file_count"] == 3


@pytest.mark.asyncio
async def test_directory_upload_recursive(project_manager, upload_manager, test_file_structure):
    """Test uploading directory contents with recursion"""
    project_name = "test-dir-recursive"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Upload entire directory structure (recursive)
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=test_file_structure,
        recursive=True
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is True
    assert result.files_processed > 10  # All files including nested
    assert len(result.errors) == 0

    # Verify nested files were included
    project_handler = await project_manager.get_project_handler(project)
    inventory = await project_handler.get_file_inventory(project)

    nested_files = [f for f in inventory if "nested" in f["filename"]]
    assert len(nested_files) > 0


@pytest.mark.asyncio
async def test_file_filtering_by_extension(project_manager, upload_manager, test_file_structure):
    """Test filtering files by extension during upload"""
    project_name = "test-file-filtering"

    # Create data project with restricted formats
    from src.logic.projects.models.config import ProjectConfig

    config = ProjectConfig(
        allowed_formats=["txt", "md", "py"],
        type_specific_settings={}
    )

    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.DATA,
        config=config
    )

    # Upload entire directory (should filter out non-text files)
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=test_file_structure,
        recursive=True
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    # Should have warnings for filtered files but overall success
    assert result.success is True
    assert len(result.warnings) > 0  # Filtered files should generate warnings

    # Verify only allowed formats were processed
    stats = await project_manager.get_project_stats(project_name)
    assert stats["document_count"] >= 2  # At least readme.txt and script.py


@pytest.mark.asyncio
async def test_file_size_validation(project_manager, upload_manager, test_file_structure):
    """Test file size validation during upload"""
    project_name = "test-size-validation"

    # Create project with small file size limit
    from src.logic.projects.models.config import ProjectConfig

    config = ProjectConfig(
        max_file_size=512000,  # 500KB limit
        type_specific_settings={}
    )

    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE,
        config=config
    )

    # Upload directory including large file
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=test_file_structure,
        recursive=True
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    # Should have errors for oversized files
    assert len(result.errors) > 0
    assert any("too large" in error.lower() or "size limit" in error.lower() for error in result.errors)

    # Smaller files should still be processed
    assert result.files_processed > 0


@pytest.mark.asyncio
async def test_upload_progress_tracking(project_manager, upload_manager, test_file_structure):
    """Test progress tracking during file upload"""
    project_name = "test-upload-progress"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Track progress updates
    progress_updates = []

    def progress_callback(update):
        progress_updates.append(update)

    # Upload files with progress tracking
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=test_file_structure,
        recursive=True
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source,
        progress_callback=progress_callback
    )

    assert result.success is True
    assert len(progress_updates) > 0

    # Verify progress updates have required fields
    for update in progress_updates:
        assert hasattr(update, "files_processed")
        assert hasattr(update, "files_total")
        assert hasattr(update, "bytes_processed")
        assert update.files_processed <= update.files_total


@pytest.mark.asyncio
async def test_upload_with_exclude_patterns(project_manager, upload_manager, test_file_structure):
    """Test excluding files based on patterns during upload"""
    project_name = "test-exclude-patterns"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Upload with exclude patterns
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=test_file_structure,
        recursive=True,
        exclude_patterns=["*.bin", "*.zip", "nested/*"]
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is True

    # Verify excluded files were not processed
    project_handler = await project_manager.get_project_handler(project)
    inventory = await project_handler.get_file_inventory(project)

    excluded_files = [
        f for f in inventory
        if any(pattern in f["filename"] for pattern in ["large_file.bin", "backup.zip", "nested"])
    ]
    assert len(excluded_files) == 0


@pytest.mark.asyncio
async def test_symlink_handling(project_manager, upload_manager):
    """Test handling of symbolic links during upload"""
    project_name = "test-symlinks"

    # Create test structure with symlinks
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)

    # Create real file
    real_file = base_path / "real_file.txt"
    real_file.write_text("Real file content")

    # Create symlink
    symlink_file = base_path / "symlink_file.txt"
    if os.name != 'nt':  # Skip on Windows if symlinks not supported
        try:
            symlink_file.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlinks not supported on this system")

        # Create storage project
        project = await project_manager.create_project(
            name=project_name,
            project_type=ProjectType.STORAGE
        )

        # Upload directory with symlinks
        upload_source = UploadSource(
            type=UploadSourceType.LOCAL,
            location=str(base_path),
            recursive=True,
            follow_symlinks=True
        )

        result = await upload_manager.upload_files(
            project=project,
            source=upload_source
        )

        assert result.success is True
        # Should process both real file and symlink target
        assert result.files_processed >= 1


@pytest.mark.asyncio
async def test_permission_error_handling(project_manager, upload_manager):
    """Test handling of permission errors during upload"""
    project_name = "test-permission-errors"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Attempt to upload non-existent file
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location="/non/existent/path"
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    assert result.success is False
    assert len(result.errors) > 0
    assert any("not found" in error.lower() or "permission" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_empty_directory_upload(project_manager, upload_manager):
    """Test uploading empty directory"""
    project_name = "test-empty-directory"

    # Create empty directory
    temp_dir = tempfile.mkdtemp()
    empty_dir = Path(temp_dir) / "empty"
    empty_dir.mkdir()

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Upload empty directory
    upload_source = UploadSource(
        type=UploadSourceType.LOCAL,
        location=str(empty_dir),
        recursive=True
    )

    result = await upload_manager.upload_files(
        project=project,
        source=upload_source
    )

    # Should succeed but process no files
    assert result.success is True
    assert result.files_processed == 0
    assert result.files_total == 0


@pytest.mark.asyncio
async def test_concurrent_local_uploads(project_manager, upload_manager, test_file_structure):
    """Test concurrent uploads from multiple local sources"""
    project_name = "test-concurrent-uploads"

    # Create storage project
    project = await project_manager.create_project(
        name=project_name,
        project_type=ProjectType.STORAGE
    )

    # Create multiple upload sources
    sources = [
        UploadSource(
            type=UploadSourceType.LOCAL,
            location=str(Path(test_file_structure) / "documents")
        ),
        UploadSource(
            type=UploadSourceType.LOCAL,
            location=str(Path(test_file_structure) / "images")
        ),
        UploadSource(
            type=UploadSourceType.LOCAL,
            location=str(Path(test_file_structure) / "code")
        )
    ]

    # Upload concurrently
    import asyncio
    upload_tasks = [
        upload_manager.upload_files(project=project, source=source)
        for source in sources
    ]

    results = await asyncio.gather(*upload_tasks, return_exceptions=True)

    # All uploads should succeed
    successful_results = [r for r in results if not isinstance(r, Exception) and r.success]
    assert len(successful_results) == 3

    # Total files processed should be sum of all uploads
    total_processed = sum(r.files_processed for r in successful_results)
    assert total_processed > 0