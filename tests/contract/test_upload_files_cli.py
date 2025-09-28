"""
Contract tests for upload files CLI command.

These tests verify the CLI interface contract for uploading files
according to the specification in contracts/cli-interface.py.
"""

import pytest
from click.testing import CliRunner
from src.cli.main import main


class TestUploadFilesCLIContract:
    """Test the upload files CLI command contract."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_upload_files_with_long_options(self):
        """Test upload files with long option names."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--source', '/path/to/files',
            '--type', 'local'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_short_options(self):
        """Test upload files with short option names."""
        result = self.runner.invoke(main, [
            'upload',
            '-p', 'test-project',
            '-sr', '/path/to/files',  # Two-char to avoid conflict with --settings
            '-t', 'local'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_local_source(self):
        """Test upload files from local source."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'data-project',
            '--source', '/home/user/documents',
            '--type', 'local'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_ftp_source(self):
        """Test upload files from FTP source."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'storage-project',
            '--source', 'ftp://server.com/path',
            '--type', 'ftp',
            '--username', 'testuser'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_sftp_source(self):
        """Test upload files from SFTP source."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'data-project',
            '--source', 'sftp://secure-server.com/docs',
            '--type', 'sftp',
            '--username', 'admin'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_smb_source(self):
        """Test upload files from SMB source."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'storage-project',
            '--source', '//server/share/folder',
            '--type', 'smb',
            '--username', 'domain\\user'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_http_source(self):
        """Test upload files from HTTP source."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'data-project',
            '--source', 'http://example.com/file.pdf',
            '--type', 'http'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_https_source(self):
        """Test upload files from HTTPS source."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'data-project',
            '--source', 'https://secure.example.com/document.pdf',
            '--type', 'https'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_recursive(self):
        """Test upload files with recursive flag."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'storage-project',
            '--source', '/path/to/directory',
            '--type', 'local',
            '--recursive'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_recursive_short(self):
        """Test upload files with recursive flag using short option."""
        result = self.runner.invoke(main, [
            'upload',
            '-p', 'storage-project',
            '-sr', '/path/to/directory',
            '-t', 'local',
            '-r'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_exclude_patterns(self):
        """Test upload files with exclude patterns."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'data-project',
            '--source', '/path/to/files',
            '--type', 'local',
            '--exclude', '*.tmp',
            '--exclude', '*.log'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_exclude_patterns_short(self):
        """Test upload files with exclude patterns using short option."""
        result = self.runner.invoke(main, [
            'upload',
            '-p', 'data-project',
            '-sr', '/path/to/files',
            '-t', 'local',
            '-e', '*.tmp',
            '-e', '*.bak'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_dry_run(self):
        """Test upload files with dry run flag."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--source', '/path/to/files',
            '--type', 'local',
            '--dry-run'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_dry_run_short(self):
        """Test upload files with dry run flag using short option."""
        result = self.runner.invoke(main, [
            'upload',
            '-p', 'test-project',
            '-sr', '/path/to/files',
            '-t', 'local',
            '-dr'  # Two-char compound
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_with_overwrite_options(self):
        """Test upload files with different overwrite options."""
        overwrite_options = ['ask', 'skip', 'overwrite']

        for option in overwrite_options:
            result = self.runner.invoke(main, [
                'upload',
                '--project', 'test-project',
                '--source', '/path/to/files',
                '--type', 'local',
                '--overwrite', option
            ])

            # Should succeed for all valid options (will fail until implementation exists)
            assert result.exit_code == 0, f"Failed for overwrite option: {option}"

    def test_upload_files_with_overwrite_short(self):
        """Test upload files with overwrite option using short option."""
        result = self.runner.invoke(main, [
            'upload',
            '-p', 'test-project',
            '-sr', '/path/to/files',
            '-t', 'local',
            '-o', 'overwrite'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_disable_progress(self):
        """Test upload files with progress disabled."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--source', '/path/to/files',
            '--type', 'local',
            '--progress', 'false'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_upload_files_missing_project(self):
        """Test upload files without required project parameter."""
        result = self.runner.invoke(main, [
            'upload',
            '--source', '/path/to/files',
            '--type', 'local'
        ])

        # Should fail with error code 2 (invalid arguments)
        assert result.exit_code == 2
        assert 'project' in result.output.lower()

    def test_upload_files_missing_source(self):
        """Test upload files without required source parameter."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--type', 'local'
        ])

        # Should fail with error code 2 (invalid arguments)
        assert result.exit_code == 2
        assert 'source' in result.output.lower()

    def test_upload_files_missing_type(self):
        """Test upload files without required type parameter."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--source', '/path/to/files'
        ])

        # Should fail with error code 2 (invalid arguments)
        assert result.exit_code == 2
        assert 'type' in result.output.lower()

    def test_upload_files_invalid_project(self):
        """Test upload files with non-existent project."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'nonexistent-project',
            '--source', '/path/to/files',
            '--type', 'local'
        ])

        # Should fail with error code 3 (project not found)
        assert result.exit_code == 3
        assert 'not found' in result.output.lower()

    def test_upload_files_invalid_source_type(self):
        """Test upload files with invalid source type."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--source', '/path/to/files',
            '--type', 'invalid-type'
        ])

        # Should fail with error code 6 (validation error)
        assert result.exit_code == 6
        assert 'Invalid source type' in result.output

    def test_upload_files_invalid_overwrite_option(self):
        """Test upload files with invalid overwrite option."""
        result = self.runner.invoke(main, [
            'upload',
            '--project', 'test-project',
            '--source', '/path/to/files',
            '--type', 'local',
            '--overwrite', 'invalid-option'
        ])

        # Should fail with validation error
        assert result.exit_code == 6

    def test_upload_files_all_source_types(self):
        """Test upload files with all valid source types."""
        source_types = ['local', 'ftp', 'sftp', 'smb', 'http', 'https']

        for source_type in source_types:
            result = self.runner.invoke(main, [
                'upload',
                '--project', 'test-project',
                '--source', f'test-source-{source_type}',
                '--type', source_type
            ])

            # Should succeed for all valid types (will fail until implementation exists)
            assert result.exit_code == 0, f"Failed for source type: {source_type}"

    def test_upload_files_help(self):
        """Test upload files help message."""
        result = self.runner.invoke(main, [
            'upload', '--help'
        ])

        # Should show help with all options
        assert result.exit_code == 0
        assert '--project' in result.output
        assert '--source' in result.output
        assert '--type' in result.output
        assert '--username' in result.output
        assert '--recursive' in result.output
        assert '--exclude' in result.output
        assert '--dry-run' in result.output
        assert '--overwrite' in result.output
        assert '--progress' in result.output

        # Should show short options
        assert '-p' in result.output
        assert '-sr' in result.output  # Two-char for source
        assert '-t' in result.output
        assert '-u' in result.output
        assert '-r' in result.output
        assert '-e' in result.output
        assert '-dr' in result.output  # Two-char compound
        assert '-o' in result.output
        assert '-pr' in result.output  # Two-char compound

    def test_short_key_uniqueness(self):
        """Test that short keys are unique and don't conflict."""
        # This test verifies the CLI_SHORT_KEYS contract
        result = self.runner.invoke(main, [
            'upload', '--help'
        ])

        assert result.exit_code == 0

        # Check that short keys match the contract specification
        help_text = result.output
        assert '-p, --project' in help_text
        assert '-sr, --source' in help_text  # Two-char to avoid conflict
        assert '-t, --type' in help_text
        assert '-u, --username' in help_text
        assert '-r, --recursive' in help_text
        assert '-e, --exclude' in help_text
        assert '-dr, --dry-run' in help_text  # Two-char compound
        assert '-o, --overwrite' in help_text
        assert '-pr, --progress' in help_text  # Two-char compound