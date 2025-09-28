"""Unit tests for file validation logic."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import hashlib
from typing import List, Dict, Any

from src.logic.projects.upload.validators.format_validator import FileValidator
from src.logic.projects.upload.validators.conflict_resolver import ConflictResolver
from src.logic.projects.models.project import ProjectType


class TestFileFormatValidation:
    """Test file format validation logic."""

    @pytest.fixture
    def file_validator(self):
        """Create FileValidator instance."""
        return FileValidator()

    @pytest.fixture
    def temp_files(self):
        """Create temporary test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create test files with different extensions
            test_files = {
                "document.pdf": b"PDF content",
                "text.txt": b"Plain text content",
                "image.jpg": b"\xff\xd8\xff",  # JPEG header
                "archive.zip": b"PK\x03\x04",  # ZIP header
                "executable.exe": b"MZ",  # PE header
                "script.py": b"#!/usr/bin/env python",
                "data.json": b'{"key": "value"}',
                "webpage.html": b"<html><body></body></html>",
            }

            created_files = {}
            for filename, content in test_files.items():
                file_path = base_path / filename
                file_path.write_bytes(content)
                created_files[filename] = file_path

            yield created_files

    def test_validate_allowed_formats_for_project_type(self, file_validator):
        """Test that format validation respects project type constraints."""
        # Crawling project - only web formats
        crawling_formats = file_validator.get_allowed_formats(ProjectType.CRAWLING)
        assert "html" in crawling_formats
        assert "htm" in crawling_formats
        assert "xml" in crawling_formats
        assert "json" in crawling_formats
        assert "pdf" not in crawling_formats

        # Data project - document formats
        data_formats = file_validator.get_allowed_formats(ProjectType.DATA)
        assert "pdf" in data_formats
        assert "docx" in data_formats
        assert "txt" in data_formats
        assert "md" in data_formats
        assert "jpg" not in data_formats

        # Storage project - all formats
        storage_formats = file_validator.get_allowed_formats(ProjectType.STORAGE)
        assert "pdf" in storage_formats
        assert "jpg" in storage_formats
        assert "zip" in storage_formats
        assert "mp3" in storage_formats
        assert "py" in storage_formats

    def test_validate_file_extension(self, file_validator, temp_files):
        """Test file extension validation."""
        # Valid extensions
        assert file_validator.validate_extension(temp_files["document.pdf"], ["pdf"]) is True
        assert file_validator.validate_extension(temp_files["text.txt"], ["txt", "md"]) is True

        # Invalid extensions
        assert file_validator.validate_extension(temp_files["executable.exe"], ["pdf", "txt"]) is False
        assert file_validator.validate_extension(temp_files["script.py"], ["jpg", "png"]) is False

        # Case-insensitive matching
        assert file_validator.validate_extension(temp_files["document.pdf"], ["PDF"]) is True

    def test_validate_mime_type(self, file_validator, temp_files):
        """Test MIME type detection and validation."""
        # Test MIME type detection
        pdf_mime = file_validator.get_mime_type(temp_files["document.pdf"])
        assert pdf_mime == "application/pdf"

        text_mime = file_validator.get_mime_type(temp_files["text.txt"])
        assert text_mime == "text/plain"

        # Test MIME type validation
        assert file_validator.validate_mime_type(
            temp_files["image.jpg"],
            ["image/jpeg", "image/png"]
        ) is True

        assert file_validator.validate_mime_type(
            temp_files["executable.exe"],
            ["image/jpeg", "text/plain"]
        ) is False

    def test_validate_file_size(self, file_validator, temp_files):
        """Test file size validation."""
        max_size = 1024  # 1KB

        # Small files pass
        assert file_validator.validate_size(temp_files["text.txt"], max_size) is True

        # Create large file
        with tempfile.NamedTemporaryFile(delete=False) as large_file:
            large_file.write(b"x" * 2048)  # 2KB
            large_file_path = Path(large_file.name)

        try:
            # Large file fails
            assert file_validator.validate_size(large_file_path, max_size) is False
        finally:
            large_file_path.unlink()

    def test_validate_file_content(self, file_validator, temp_files):
        """Test file content validation."""
        # Test JSON validation
        assert file_validator.validate_json_content(temp_files["data.json"]) is True
        assert file_validator.validate_json_content(temp_files["text.txt"]) is False

        # Test HTML validation
        assert file_validator.validate_html_content(temp_files["webpage.html"]) is True
        assert file_validator.validate_html_content(temp_files["text.txt"]) is False

        # Test binary detection
        assert file_validator.is_binary(temp_files["image.jpg"]) is True
        assert file_validator.is_binary(temp_files["text.txt"]) is False

    def test_comprehensive_file_validation(self, file_validator, temp_files):
        """Test comprehensive file validation with all checks."""
        validation_config = {
            "allowed_formats": ["pdf", "txt", "json"],
            "max_file_size": 10485760,  # 10MB
            "validate_content": True,
            "project_type": ProjectType.DATA
        }

        # Valid file passes all checks
        result = file_validator.validate_file(
            temp_files["document.pdf"],
            validation_config
        )
        assert result["valid"] is True
        assert result["extension"] == "pdf"
        assert result["size"] < validation_config["max_file_size"]

        # Invalid extension fails
        result = file_validator.validate_file(
            temp_files["executable.exe"],
            validation_config
        )
        assert result["valid"] is False
        assert "extension" in result["error"].lower()

        # Corrupt file fails content validation
        corrupt_pdf = Path(tempfile.mktemp(suffix=".pdf"))
        corrupt_pdf.write_bytes(b"not a real pdf")

        try:
            result = file_validator.validate_file(
                corrupt_pdf,
                validation_config
            )
            assert result["valid"] is False
            assert "content" in result["error"].lower() or "format" in result["error"].lower()
        finally:
            corrupt_pdf.unlink()


class TestFileConflictResolution:
    """Test file conflict detection and resolution."""

    @pytest.fixture
    def conflict_resolver(self):
        """Create ConflictResolver instance."""
        return ConflictResolver()

    @pytest.fixture
    def project_files(self):
        """Create mock project file list."""
        return {
            "document.pdf": {
                "checksum": "abc123",
                "size": 1024,
                "path": "/storage/document.pdf"
            },
            "image.jpg": {
                "checksum": "def456",
                "size": 2048,
                "path": "/storage/image.jpg"
            },
            "data.json": {
                "checksum": "ghi789",
                "size": 512,
                "path": "/storage/data.json"
            }
        }

    def test_detect_filename_conflict(self, conflict_resolver, project_files):
        """Test detection of filename conflicts."""
        # Exact filename match
        assert conflict_resolver.check_filename_conflict(
            "document.pdf",
            project_files
        ) is True

        # No conflict
        assert conflict_resolver.check_filename_conflict(
            "newfile.txt",
            project_files
        ) is False

        # Case sensitivity
        assert conflict_resolver.check_filename_conflict(
            "Document.PDF",
            project_files,
            case_sensitive=False
        ) is True

    def test_detect_checksum_conflict(self, conflict_resolver, project_files):
        """Test detection of duplicate files by checksum."""
        # Same checksum = duplicate
        assert conflict_resolver.check_checksum_conflict(
            "abc123",
            project_files
        ) is True

        # Different checksum = unique
        assert conflict_resolver.check_checksum_conflict(
            "xyz999",
            project_files
        ) is False

    def test_resolve_filename_conflict(self, conflict_resolver, project_files):
        """Test filename conflict resolution strategies."""
        # Overwrite strategy
        resolution = conflict_resolver.resolve_conflict(
            "document.pdf",
            project_files,
            strategy="overwrite"
        )
        assert resolution["action"] == "overwrite"
        assert resolution["final_name"] == "document.pdf"

        # Skip strategy
        resolution = conflict_resolver.resolve_conflict(
            "document.pdf",
            project_files,
            strategy="skip"
        )
        assert resolution["action"] == "skip"
        assert resolution["reason"] == "file exists"

        # Rename strategy
        resolution = conflict_resolver.resolve_conflict(
            "document.pdf",
            project_files,
            strategy="rename"
        )
        assert resolution["action"] == "rename"
        assert resolution["final_name"] != "document.pdf"
        assert "document" in resolution["final_name"]
        assert ".pdf" in resolution["final_name"]

    def test_generate_unique_filename(self, conflict_resolver, project_files):
        """Test unique filename generation."""
        # Generate unique name for existing file
        unique_name = conflict_resolver.generate_unique_name(
            "document.pdf",
            project_files
        )
        assert unique_name != "document.pdf"
        assert unique_name not in project_files
        assert unique_name.endswith(".pdf")

        # Pattern variations
        assert "document_1.pdf" in conflict_resolver.generate_unique_name(
            "document.pdf",
            project_files,
            pattern="_{n}"
        )

        assert "document(1).pdf" in conflict_resolver.generate_unique_name(
            "document.pdf",
            project_files,
            pattern="({n})"
        )

    def test_batch_conflict_resolution(self, conflict_resolver, project_files):
        """Test resolving conflicts for multiple files."""
        new_files = [
            {"name": "document.pdf", "checksum": "new123"},
            {"name": "image.jpg", "checksum": "def456"},  # Duplicate checksum
            {"name": "newfile.txt", "checksum": "new456"},
            {"name": "data.json", "checksum": "new789"},
        ]

        resolutions = conflict_resolver.resolve_batch(
            new_files,
            project_files,
            strategy="auto"
        )

        # First file: name conflict, different content -> rename
        assert resolutions[0]["action"] == "rename"

        # Second file: same checksum -> skip duplicate
        assert resolutions[1]["action"] == "skip"
        assert "duplicate" in resolutions[1]["reason"].lower()

        # Third file: no conflict -> add
        assert resolutions[2]["action"] == "add"
        assert resolutions[2]["final_name"] == "newfile.txt"

        # Fourth file: name conflict -> rename
        assert resolutions[3]["action"] == "rename"


class TestFileValidationEdgeCases:
    """Test edge cases in file validation."""

    @pytest.fixture
    def file_validator(self):
        """Create FileValidator instance."""
        return FileValidator()

    def test_validate_empty_file(self, file_validator):
        """Test validation of empty files."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as empty_file:
            empty_path = Path(empty_file.name)

        try:
            result = file_validator.validate_file(
                empty_path,
                {"allowed_formats": ["txt"], "allow_empty": False}
            )
            assert result["valid"] is False
            assert "empty" in result["error"].lower()

            # Allow empty files
            result = file_validator.validate_file(
                empty_path,
                {"allowed_formats": ["txt"], "allow_empty": True}
            )
            assert result["valid"] is True
        finally:
            empty_path.unlink()

    def test_validate_symlink(self, file_validator):
        """Test validation of symbolic links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create real file
            real_file = base_path / "real.txt"
            real_file.write_text("content")

            # Create symlink
            symlink = base_path / "link.txt"
            symlink.symlink_to(real_file)

            # Validate symlink (should follow to real file)
            result = file_validator.validate_file(
                symlink,
                {"allowed_formats": ["txt"], "follow_symlinks": True}
            )
            assert result["valid"] is True

            # Don't follow symlinks
            result = file_validator.validate_file(
                symlink,
                {"allowed_formats": ["txt"], "follow_symlinks": False}
            )
            assert result["valid"] is False
            assert "symlink" in result["error"].lower()

    def test_validate_hidden_files(self, file_validator):
        """Test validation of hidden files."""
        with tempfile.NamedTemporaryFile(prefix=".", suffix=".txt", delete=False) as hidden_file:
            hidden_path = Path(hidden_file.name)
            hidden_path.write_text("hidden content")

        try:
            # Reject hidden files
            result = file_validator.validate_file(
                hidden_path,
                {"allowed_formats": ["txt"], "allow_hidden": False}
            )
            assert result["valid"] is False
            assert "hidden" in result["error"].lower()

            # Allow hidden files
            result = file_validator.validate_file(
                hidden_path,
                {"allowed_formats": ["txt"], "allow_hidden": True}
            )
            assert result["valid"] is True
        finally:
            hidden_path.unlink()

    def test_validate_special_characters_in_filename(self, file_validator):
        """Test validation of filenames with special characters."""
        special_names = [
            "file with spaces.txt",
            "file(with)parens.txt",
            "file[with]brackets.txt",
            "file@with#symbols.txt",
            "file.multiple.dots.txt",
            "文件.txt",  # Unicode characters
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            for name in special_names:
                file_path = base_path / name
                file_path.write_text("content")

                result = file_validator.validate_file(
                    file_path,
                    {"allowed_formats": ["txt"], "strict_naming": False}
                )
                assert result["valid"] is True

                # Strict naming mode
                result = file_validator.validate_file(
                    file_path,
                    {"allowed_formats": ["txt"], "strict_naming": True}
                )
                if any(c in name for c in " ()[]@#"):
                    assert result["valid"] is False
                    assert "naming" in result["error"].lower()


class TestFileValidationPerformance:
    """Test performance aspects of file validation."""

    @pytest.fixture
    def file_validator(self):
        """Create FileValidator instance."""
        return FileValidator()

    def test_validate_large_file_efficiently(self, file_validator):
        """Test that large files are validated efficiently."""
        # Create a 100MB file
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as large_file:
            large_file.write(b"x" * (100 * 1024 * 1024))
            large_path = Path(large_file.name)

        try:
            import time
            start = time.time()

            result = file_validator.validate_file(
                large_path,
                {
                    "allowed_formats": ["bin"],
                    "max_file_size": 200 * 1024 * 1024,  # 200MB limit
                    "quick_validation": True  # Don't read entire content
                }
            )

            elapsed = time.time() - start

            assert result["valid"] is True
            assert elapsed < 1.0  # Should complete in under 1 second
        finally:
            large_path.unlink()

    def test_batch_validation_performance(self, file_validator):
        """Test batch file validation performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create 100 test files
            files = []
            for i in range(100):
                file_path = base_path / f"file_{i}.txt"
                file_path.write_text(f"content {i}")
                files.append(file_path)

            import time
            start = time.time()

            results = file_validator.validate_batch(
                files,
                {"allowed_formats": ["txt"], "parallel": True}
            )

            elapsed = time.time() - start

            assert len(results) == 100
            assert all(r["valid"] for r in results)
            assert elapsed < 5.0  # Should complete in under 5 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])