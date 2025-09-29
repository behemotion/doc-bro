"""Unit tests for upload source parsers."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional
import tempfile
from urllib.parse import urlparse

from src.logic.projects.models.upload import UploadSource, UploadSourceType
from src.logic.projects.upload.sources.local_source import LocalSource
from src.logic.projects.upload.sources.ftp_source import FTPSource
from src.logic.projects.upload.sources.sftp_source import SFTPSource
from src.logic.projects.upload.sources.smb_source import SMBSource
from src.logic.projects.upload.sources.http_source import HTTPSource


class TestUploadSourceParsing:
    """Test parsing of different upload source formats."""

    def test_parse_local_path(self):
        """Test parsing local file paths."""
        test_cases = [
            ("/absolute/path/to/file.txt", "local", "/absolute/path/to/file.txt"),
            ("./relative/path/file.txt", "local", "./relative/path/file.txt"),
            ("~/user/path/file.txt", "local", "~/user/path/file.txt"),
            ("C:\\Windows\\path\\file.txt", "local", "C:\\Windows\\path\\file.txt"),
        ]

        for source_str, expected_type, expected_path in test_cases:
            source = UploadSource.parse(source_str)
            assert source.type == UploadSourceType(expected_type)
            assert source.location == expected_path

    def test_parse_ftp_url(self):
        """Test parsing FTP URLs."""
        test_cases = [
            (
                "ftp://user:pass@server.com/path/file.txt",
                {
                    "type": "ftp",
                    "host": "server.com",
                    "path": "/path/file.txt",
                    "username": "user",
                    "password": "pass",
                    "port": 21,
                }
            ),
            (
                "ftp://server.com/path/",
                {
                    "type": "ftp",
                    "host": "server.com",
                    "path": "/path/",
                    "username": None,
                    "password": None,
                    "port": 21,
                }
            ),
            (
                "ftp://server.com:2121/custom/port/",
                {
                    "type": "ftp",
                    "host": "server.com",
                    "path": "/custom/port/",
                    "port": 2121,
                }
            ),
        ]

        for url, expected in test_cases:
            source = UploadSource.parse(url)
            assert source.type == UploadSourceType(expected["type"])

            parsed = urlparse(source.location)
            assert parsed.hostname == expected["host"]
            assert parsed.path == expected["path"]

            if expected.get("username"):
                assert source.credentials["username"] == expected["username"]
            if expected.get("password"):
                assert source.credentials["password"] == expected["password"]

    def test_parse_sftp_url(self):
        """Test parsing SFTP URLs."""
        test_cases = [
            (
                "sftp://user@server.com/path/file.txt",
                {
                    "type": "sftp",
                    "host": "server.com",
                    "path": "/path/file.txt",
                    "username": "user",
                    "port": 22,
                }
            ),
            (
                "sftp://user:pass@server.com:2222/path/",
                {
                    "type": "sftp",
                    "host": "server.com",
                    "path": "/path/",
                    "username": "user",
                    "password": "pass",
                    "port": 2222,
                }
            ),
            (
                "ssh://user@server.com/path/",  # SSH alias for SFTP
                {
                    "type": "sftp",
                    "host": "server.com",
                    "path": "/path/",
                    "username": "user",
                    "port": 22,
                }
            ),
        ]

        for url, expected in test_cases:
            source = UploadSource.parse(url)
            assert source.type == UploadSourceType("sftp")

            parsed = urlparse(source.location)
            assert parsed.hostname == expected["host"]
            assert parsed.path == expected["path"]

            if expected.get("username"):
                assert source.credentials["username"] == expected["username"]

    def test_parse_smb_url(self):
        """Test parsing SMB/CIFS URLs."""
        test_cases = [
            (
                "smb://server/share/path/file.txt",
                {
                    "type": "smb",
                    "host": "server",
                    "share": "share",
                    "path": "/path/file.txt",
                    "port": 445,
                }
            ),
            (
                "smb://user:pass@server/share/",
                {
                    "type": "smb",
                    "host": "server",
                    "share": "share",
                    "path": "/",
                    "username": "user",
                    "password": "pass",
                    "port": 445,
                }
            ),
            (
                "\\\\server\\share\\path\\file.txt",  # UNC path
                {
                    "type": "smb",
                    "host": "server",
                    "share": "share",
                    "path": "\\path\\file.txt",
                }
            ),
        ]

        for url, expected in test_cases:
            source = UploadSource.parse(url)
            assert source.type == UploadSourceType("smb")

            # Parse SMB-specific components
            if url.startswith("smb://"):
                parsed = urlparse(source.location)
                assert parsed.hostname == expected["host"]

    def test_parse_http_url(self):
        """Test parsing HTTP/HTTPS URLs."""
        test_cases = [
            (
                "http://example.com/file.pdf",
                {
                    "type": "http",
                    "host": "example.com",
                    "path": "/file.pdf",
                    "scheme": "http",
                }
            ),
            (
                "https://secure.example.com/path/to/file.zip",
                {
                    "type": "https",
                    "host": "secure.example.com",
                    "path": "/path/to/file.zip",
                    "scheme": "https",
                }
            ),
            (
                "https://user:pass@api.example.com/download",
                {
                    "type": "https",
                    "host": "api.example.com",
                    "path": "/download",
                    "username": "user",
                    "password": "pass",
                }
            ),
        ]

        for url, expected in test_cases:
            source = UploadSource.parse(url)
            assert source.type == UploadSourceType(expected["type"])

            parsed = urlparse(source.location)
            assert parsed.hostname == expected["host"]
            assert parsed.path == expected["path"]
            assert parsed.scheme == expected["scheme"]

    def test_invalid_source_parsing(self):
        """Test that invalid sources raise appropriate errors."""
        invalid_sources = [
            "",  # Empty string
            "invalid://protocol/path",  # Unknown protocol
            "ftp://",  # Incomplete URL
            "://missing/scheme",  # Missing scheme
            "not_a_url_or_path",  # Ambiguous input
        ]

        for source in invalid_sources:
            with pytest.raises(ValueError) as exc_info:
                UploadSource.parse(source)
            assert "invalid" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()


class TestLocalSourceHandler:
    """Test local file source handler."""

    @pytest.fixture
    def local_source(self):
        """Create LocalSource handler."""
        return LocalSource()

    @pytest.fixture
    def temp_files(self):
        """Create temporary test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create test directory structure
            (base_path / "docs").mkdir()
            (base_path / "docs" / "readme.txt").write_text("readme content")
            (base_path / "docs" / "guide.pdf").write_bytes(b"PDF content")

            (base_path / "images").mkdir()
            (base_path / "images" / "logo.png").write_bytes(b"PNG content")
            (base_path / "images" / "banner.jpg").write_bytes(b"JPG content")

            (base_path / "file.txt").write_text("root file")

            yield base_path

    async def test_list_local_files(self, local_source, temp_files):
        """Test listing files from local directory."""
        # List all files
        files = await local_source.list_files(str(temp_files))
        assert len(files) == 5

        # List with pattern
        files = await local_source.list_files(str(temp_files), pattern="*.txt")
        assert len(files) == 2
        assert all(f.endswith(".txt") for f in files)

        # List recursive
        files = await local_source.list_files(
            str(temp_files / "docs"),
            recursive=False
        )
        assert len(files) == 2

    async def test_validate_local_source(self, local_source, temp_files):
        """Test validation of local source paths."""
        # Valid directory
        result = await local_source.validate(str(temp_files))
        assert result["valid"] is True
        assert result["accessible"] is True

        # Valid file
        result = await local_source.validate(str(temp_files / "file.txt"))
        assert result["valid"] is True
        assert result["is_file"] is True

        # Non-existent path
        result = await local_source.validate("/non/existent/path")
        assert result["valid"] is False
        assert "not found" in result["error"].lower()

        # No read permissions (simulate)
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_readable", return_value=False):
                result = await local_source.validate("/restricted/path")
                assert result["valid"] is False
                assert "permission" in result["error"].lower()

    async def test_download_local_files(self, local_source, temp_files):
        """Test 'downloading' (copying) local files."""
        destination = Path(tempfile.mkdtemp())

        try:
            # Download single file
            result = await local_source.download(
                str(temp_files / "file.txt"),
                str(destination)
            )
            assert result["success"] is True
            assert (destination / "file.txt").exists()
            assert (destination / "file.txt").read_text() == "root file"

            # Download directory
            result = await local_source.download(
                str(temp_files / "docs"),
                str(destination),
                recursive=True
            )
            assert result["success"] is True
            assert (destination / "docs" / "readme.txt").exists()
            assert (destination / "docs" / "guide.pdf").exists()

        finally:
            import shutil
            shutil.rmtree(destination)


class TestFTPSourceHandler:
    """Test FTP source handler."""

    @pytest.fixture
    def ftp_source(self):
        """Create FTPSource handler."""
        return FTPSource()

    @patch("ftplib.FTP")
    async def test_connect_ftp(self, mock_ftp_class, ftp_source):
        """Test FTP connection establishment."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        credentials = {
            "host": "ftp.example.com",
            "port": 21,
            "username": "user",
            "password": "pass"
        }

        connection = await ftp_source.connect(credentials)

        mock_ftp_class.assert_called_once()
        mock_ftp.connect.assert_called_with("ftp.example.com", 21)
        mock_ftp.login.assert_called_with("user", "pass")

        assert connection == mock_ftp

    @patch("ftplib.FTP")
    async def test_list_ftp_files(self, mock_ftp_class, ftp_source):
        """Test listing files from FTP server."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        # Simulate FTP listing
        mock_ftp.nlst.return_value = [
            "file1.txt",
            "file2.pdf",
            "directory/file3.doc"
        ]

        files = await ftp_source.list_files(
            mock_ftp,
            "/path/to/files"
        )

        assert len(files) == 3
        assert "file1.txt" in files
        mock_ftp.cwd.assert_called_with("/path/to/files")
        mock_ftp.nlst.assert_called_once()

    @patch("ftplib.FTP")
    async def test_download_ftp_file(self, mock_ftp_class, ftp_source):
        """Test downloading files from FTP server."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        # Setup mock responses
        file_content = b"File content from FTP"
        mock_ftp.retrbinary.side_effect = lambda cmd, callback: callback(file_content)

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir)

            result = await ftp_source.download_file(
                mock_ftp,
                "/remote/file.txt",
                destination / "file.txt"
            )

            assert result["success"] is True
            assert (destination / "file.txt").exists()
            assert (destination / "file.txt").read_bytes() == file_content

            mock_ftp.retrbinary.assert_called()


class TestSFTPSourceHandler:
    """Test SFTP source handler."""

    @pytest.fixture
    def sftp_source(self):
        """Create SFTPSource handler."""
        return SFTPSource()

    @patch("paramiko.SSHClient")
    async def test_connect_sftp(self, mock_ssh_class, sftp_source):
        """Test SFTP connection establishment."""
        mock_ssh = MagicMock()
        mock_sftp = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        mock_ssh.open_sftp.return_value = mock_sftp

        credentials = {
            "host": "sftp.example.com",
            "port": 22,
            "username": "user",
            "password": "pass"
        }

        connection = await sftp_source.connect(credentials)

        mock_ssh.connect.assert_called_with(
            hostname="sftp.example.com",
            port=22,
            username="user",
            password="pass"
        )
        mock_ssh.open_sftp.assert_called_once()
        assert connection == mock_sftp

    @patch("paramiko.SSHClient")
    async def test_list_sftp_files(self, mock_ssh_class, sftp_source):
        """Test listing files from SFTP server."""
        mock_sftp = MagicMock()

        # Simulate SFTP listing
        mock_file1 = MagicMock()
        mock_file1.filename = "file1.txt"
        mock_file1.st_mode = 0o100644  # Regular file

        mock_file2 = MagicMock()
        mock_file2.filename = "file2.pdf"
        mock_file2.st_mode = 0o100644

        mock_dir = MagicMock()
        mock_dir.filename = "subdir"
        mock_dir.st_mode = 0o040755  # Directory

        mock_sftp.listdir_attr.return_value = [mock_file1, mock_file2, mock_dir]

        files = await sftp_source.list_files(
            mock_sftp,
            "/remote/path",
            include_dirs=False
        )

        assert len(files) == 2
        assert "file1.txt" in files
        assert "file2.pdf" in files
        assert "subdir" not in files

    @patch("paramiko.SSHClient")
    async def test_download_sftp_file(self, mock_ssh_class, sftp_source):
        """Test downloading files from SFTP server."""
        mock_sftp = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir)
            local_path = destination / "downloaded.txt"

            result = await sftp_source.download_file(
                mock_sftp,
                "/remote/file.txt",
                local_path
            )

            mock_sftp.get.assert_called_with(
                "/remote/file.txt",
                str(local_path)
            )


class TestHTTPSourceHandler:
    """Test HTTP/HTTPS source handler."""

    @pytest.fixture
    def http_source(self):
        """Create HTTPSource handler."""
        return HTTPSource()

    @patch("httpx.AsyncClient.head")
    async def test_validate_http_url(self, mock_head, http_source):
        """Test validation of HTTP URLs."""
        # Valid URL
        mock_head.return_value = MagicMock(
            status_code=200,
            headers={"content-length": "1024", "content-type": "application/pdf"}
        )

        result = await http_source.validate("https://example.com/file.pdf")
        assert result["valid"] is True
        assert result["size"] == 1024
        assert result["mime_type"] == "application/pdf"

        # 404 Not Found
        mock_head.return_value = MagicMock(status_code=404)
        result = await http_source.validate("https://example.com/notfound.pdf")
        assert result["valid"] is False
        assert "404" in result["error"]

    @patch("httpx.AsyncClient.get")
    async def test_download_http_file(self, mock_get, http_source):
        """Test downloading files via HTTP."""
        file_content = b"Downloaded content"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = file_content
        mock_response.headers = {"content-length": str(len(file_content))}
        mock_response.iter_bytes = lambda chunk_size: [file_content]
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "downloaded.pdf"

            result = await http_source.download(
                "https://example.com/file.pdf",
                destination
            )

            assert result["success"] is True
            assert destination.exists()
            assert destination.read_bytes() == file_content

    @patch("httpx.AsyncClient.get")
    async def test_download_http_with_retry(self, mock_get, http_source):
        """Test HTTP download with retry logic."""
        # First two attempts fail, third succeeds
        mock_get.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection reset"),
            MagicMock(
                status_code=200,
                content=b"Success",
                headers={"content-length": "7"}
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "file.txt"

            result = await http_source.download_with_retry(
                "https://example.com/file.txt",
                destination,
                max_retries=3
            )

            assert result["success"] is True
            assert result["attempts"] == 3
            assert destination.exists()

    @patch("httpx.AsyncClient.get")
    async def test_download_http_with_progress(self, mock_get, http_source):
        """Test HTTP download with progress callback."""
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        total_size = sum(len(c) for c in chunks)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": str(total_size)}
        mock_response.iter_bytes = lambda chunk_size: chunks
        mock_get.return_value = mock_response

        progress_updates = []

        def progress_callback(downloaded, total):
            progress_updates.append((downloaded, total))

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "file.bin"

            result = await http_source.download(
                "https://example.com/file.bin",
                destination,
                progress_callback=progress_callback
            )

            assert result["success"] is True
            assert len(progress_updates) == 3
            assert progress_updates[-1] == (total_size, total_size)


class TestUploadSourceTypeDetection:
    """Test automatic detection of source types."""

    def test_detect_source_type_from_string(self):
        """Test detecting source type from various input strings."""
        test_cases = [
            ("/local/path/file.txt", UploadSourceType.LOCAL),
            ("./relative/path/", UploadSourceType.LOCAL),
            ("~/home/user/file", UploadSourceType.LOCAL),
            ("ftp://server.com/file", UploadSourceType.FTP),
            ("sftp://server.com/file", UploadSourceType.SFTP),
            ("smb://server/share/file", UploadSourceType.SMB),
            ("http://example.com/file", UploadSourceType.HTTP),
            ("https://example.com/file", UploadSourceType.HTTPS),
            ("\\\\server\\share\\file", UploadSourceType.SMB),  # UNC path
        ]

        for source_str, expected_type in test_cases:
            detected_type = UploadSource.detect_type(source_str)
            assert detected_type == expected_type, (
                f"Failed to detect {expected_type} from '{source_str}'"
            )

    def test_ambiguous_source_detection(self):
        """Test handling of ambiguous source strings."""
        ambiguous = [
            "server.com/file",  # Could be local path or missing protocol
            "file.txt",  # Could be local or needs full path
            "192.168.1.1/share",  # IP without protocol
        ]

        for source in ambiguous:
            # Should default to local or require explicit type
            detected = UploadSource.detect_type(source, default=UploadSourceType.LOCAL)
            assert detected == UploadSourceType.LOCAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])