"""Unit tests for FileAccessController logic."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch

from src.logic.mcp.services.file_access import FileAccessController
from src.logic.mcp.models.file_access import FileAccessRequest, ProjectType, FileAccessType


class TestFileAccessController:
    """Test cases for FileAccessController logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.controller = FileAccessController()

    def test_validate_access_storage_project(self):
        """Test access validation for storage projects."""
        # Storage projects should allow all access types
        request_metadata = FileAccessRequest(
            project_name="test-storage",
            access_type=FileAccessType.METADATA
        )
        request_content = FileAccessRequest(
            project_name="test-storage",
            access_type=FileAccessType.CONTENT
        )
        request_download = FileAccessRequest(
            project_name="test-storage",
            access_type=FileAccessType.DOWNLOAD
        )

        assert self.controller.validate_access(request_metadata, ProjectType.STORAGE) is True
        assert self.controller.validate_access(request_content, ProjectType.STORAGE) is True
        assert self.controller.validate_access(request_download, ProjectType.STORAGE) is True

    def test_validate_access_crawling_project(self):
        """Test access validation for crawling projects."""
        # Crawling projects should only allow metadata access
        request_metadata = FileAccessRequest(
            project_name="test-crawling",
            access_type=FileAccessType.METADATA
        )
        request_content = FileAccessRequest(
            project_name="test-crawling",
            access_type=FileAccessType.CONTENT
        )
        request_download = FileAccessRequest(
            project_name="test-crawling",
            access_type=FileAccessType.DOWNLOAD
        )

        assert self.controller.validate_access(request_metadata, ProjectType.CRAWLING) is True
        assert self.controller.validate_access(request_content, ProjectType.CRAWLING) is False
        assert self.controller.validate_access(request_download, ProjectType.CRAWLING) is False

    def test_validate_access_data_project(self):
        """Test access validation for data projects."""
        # Data projects should only allow metadata access
        request_metadata = FileAccessRequest(
            project_name="test-data",
            access_type=FileAccessType.METADATA
        )
        request_content = FileAccessRequest(
            project_name="test-data",
            access_type=FileAccessType.CONTENT
        )
        request_download = FileAccessRequest(
            project_name="test-data",
            access_type=FileAccessType.DOWNLOAD
        )

        assert self.controller.validate_access(request_metadata, ProjectType.DATA) is True
        assert self.controller.validate_access(request_content, ProjectType.DATA) is False
        assert self.controller.validate_access(request_download, ProjectType.DATA) is False

    def test_get_allowed_access_level(self):
        """Test getting allowed access level per project type."""
        assert self.controller.get_allowed_access_level(ProjectType.STORAGE) == FileAccessType.DOWNLOAD
        assert self.controller.get_allowed_access_level(ProjectType.CRAWLING) == FileAccessType.METADATA
        assert self.controller.get_allowed_access_level(ProjectType.DATA) == FileAccessType.METADATA

    @pytest.mark.asyncio
    async def test_get_file_metadata_single_file(self):
        """Test getting metadata for a single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"
            test_file.write_text("Hello, world!")

            # Get metadata for single file
            metadata_list = await self.controller.get_file_metadata(project_root, "test.txt")

            assert len(metadata_list) == 1
            metadata = metadata_list[0]
            assert metadata["path"] == "test.txt"
            assert metadata["size"] == 13  # "Hello, world!" length
            assert metadata["content_type"] == "text/plain"
            assert "modified_at" in metadata

    @pytest.mark.asyncio
    async def test_get_file_metadata_all_files(self):
        """Test getting metadata for all files in project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create multiple test files
            (project_root / "test1.txt").write_text("File 1")
            (project_root / "test2.md").write_text("# File 2")
            (project_root / "subdir").mkdir()
            (project_root / "subdir" / "test3.json").write_text('{"key": "value"}')

            # Get metadata for all files
            metadata_list = await self.controller.get_file_metadata(project_root)

            assert len(metadata_list) == 3

            # Check that all files are included
            file_paths = {meta["path"] for meta in metadata_list}
            expected_paths = {"test1.txt", "test2.md", "subdir/test3.json"}
            assert file_paths == expected_paths

    @pytest.mark.asyncio
    async def test_get_file_metadata_nonexistent_file(self):
        """Test getting metadata for nonexistent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Try to get metadata for nonexistent file
            metadata_list = await self.controller.get_file_metadata(project_root, "nonexistent.txt")

            assert len(metadata_list) == 0

    @pytest.mark.asyncio
    async def test_get_file_content_storage_project(self):
        """Test getting file content for storage project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"
            test_content = "Hello, world!"
            test_file.write_text(test_content)

            # Should allow content access for storage projects
            content = await self.controller.get_file_content(
                project_root, "test.txt", ProjectType.STORAGE
            )

            assert content == test_content

    @pytest.mark.asyncio
    async def test_get_file_content_crawling_project_denied(self):
        """Test getting file content denied for crawling project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"
            test_file.write_text("Hello, world!")

            # Should deny content access for crawling projects
            content = await self.controller.get_file_content(
                project_root, "test.txt", ProjectType.CRAWLING
            )

            assert content is None

    @pytest.mark.asyncio
    async def test_get_file_content_data_project_denied(self):
        """Test getting file content denied for data project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"
            test_file.write_text("Hello, world!")

            # Should deny content access for data projects
            content = await self.controller.get_file_content(
                project_root, "test.txt", ProjectType.DATA
            )

            assert content is None

    @pytest.mark.asyncio
    async def test_get_file_content_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create a file outside the project root
            outside_file = Path(temp_dir).parent / "outside.txt"
            outside_file.write_text("Secret content")

            # Try to access file outside project boundaries
            content = await self.controller.get_file_content(
                project_root, "../outside.txt", ProjectType.STORAGE
            )

            assert content is None

    @pytest.mark.asyncio
    async def test_get_file_content_nonexistent_file(self):
        """Test getting content for nonexistent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            content = await self.controller.get_file_content(
                project_root, "nonexistent.txt", ProjectType.STORAGE
            )

            assert content is None

    def test_get_content_type(self):
        """Test content type detection based on file extension."""
        test_cases = [
            ("test.txt", "text/plain"),
            ("README.md", "text/markdown"),
            ("index.html", "text/html"),
            ("style.css", "text/css"),
            ("script.js", "application/javascript"),
            ("data.json", "application/json"),
            ("config.xml", "application/xml"),
            ("document.pdf", "application/pdf"),
            ("image.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("picture.jpeg", "image/jpeg"),
            ("animation.gif", "image/gif"),
            ("unknown.xyz", "application/octet-stream"),
        ]

        for filename, expected_type in test_cases:
            file_path = Path(filename)
            content_type = self.controller._get_content_type(file_path)
            assert content_type == expected_type

    def test_is_safe_file_path_valid_paths(self):
        """Test safe file path validation for valid paths."""
        valid_paths = [
            "test.txt",
            "docs/readme.md",
            "src/main.py",
            "images/logo.png",
            "data/files/config.json",
        ]

        for path in valid_paths:
            assert self.controller.is_safe_file_path(path) is True

    def test_is_safe_file_path_dangerous_paths(self):
        """Test safe file path validation rejects dangerous paths."""
        dangerous_paths = [
            "../../../etc/passwd",
            "../../config.ini",
            "/etc/passwd",
            "/absolute/path.txt",
            "folder/../../../outside.txt",
        ]

        for path in dangerous_paths:
            assert self.controller.is_safe_file_path(path) is False

    def test_is_safe_file_path_hidden_files(self):
        """Test safe file path validation rejects hidden files."""
        hidden_paths = [
            ".env",
            ".secrets.json",
            "folder/.hidden",
            ".config/settings.yaml",
            "src/.private/data.txt",
        ]

        for path in hidden_paths:
            assert self.controller.is_safe_file_path(path) is False

    @pytest.mark.asyncio
    async def test_list_accessible_files(self):
        """Test listing accessible files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create test files
            (project_root / "public.txt").write_text("Public file")
            (project_root / "docs").mkdir()
            (project_root / "docs" / "readme.md").write_text("# README")
            (project_root / ".hidden.txt").write_text("Hidden file")
            (project_root / "subdir").mkdir()
            (project_root / "subdir" / "file.py").write_text("# Python code")

            # List accessible files (excluding hidden)
            files = await self.controller.list_accessible_files(
                project_root, ProjectType.STORAGE, include_hidden=False
            )

            expected_files = {"public.txt", "docs/readme.md", "subdir/file.py"}
            assert set(files) == expected_files

    @pytest.mark.asyncio
    async def test_list_accessible_files_include_hidden(self):
        """Test listing accessible files including hidden files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create test files including hidden ones
            (project_root / "public.txt").write_text("Public file")
            (project_root / ".hidden.txt").write_text("Hidden file")

            # List accessible files (including hidden)
            files = await self.controller.list_accessible_files(
                project_root, ProjectType.STORAGE, include_hidden=True
            )

            expected_files = {"public.txt", ".hidden.txt"}
            assert set(files) == expected_files

    @pytest.mark.asyncio
    async def test_list_accessible_files_nonexistent_directory(self):
        """Test listing files in nonexistent directory."""
        nonexistent_path = Path("/nonexistent/directory")

        files = await self.controller.list_accessible_files(
            nonexistent_path, ProjectType.STORAGE
        )

        assert files == []

    @pytest.mark.asyncio
    async def test_get_single_file_metadata_error_handling(self):
        """Test error handling in _get_single_file_metadata."""
        # Test with a path that will cause permission error
        with patch('pathlib.Path.stat', side_effect=PermissionError("Access denied")):
            metadata = await self.controller._get_single_file_metadata(
                Path("test.txt"), "test.txt"
            )
            assert metadata is None

    @pytest.mark.asyncio
    async def test_get_file_metadata_error_handling(self):
        """Test error handling in get_file_metadata."""
        # Test with invalid path
        with patch('pathlib.Path.exists', side_effect=Exception("Filesystem error")):
            metadata_list = await self.controller.get_file_metadata(
                Path("/invalid"), "test.txt"
            )
            assert metadata_list == []

    @pytest.mark.asyncio
    async def test_get_file_content_encoding_error_handling(self):
        """Test file content reading with encoding errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "binary.bin"

            # Write binary data that might cause encoding issues
            test_file.write_bytes(b'\x80\x81\x82\x83')

            # Should handle encoding errors gracefully
            content = await self.controller.get_file_content(
                project_root, "binary.bin", ProjectType.STORAGE
            )

            # Content should be read (with errors='ignore')
            assert content is not None

    @pytest.mark.asyncio
    async def test_list_accessible_files_error_handling(self):
        """Test error handling in list_accessible_files."""
        # Test with permission error
        with patch('pathlib.Path.rglob', side_effect=PermissionError("Access denied")):
            files = await self.controller.list_accessible_files(
                Path("/restricted"), ProjectType.STORAGE
            )
            assert files == []