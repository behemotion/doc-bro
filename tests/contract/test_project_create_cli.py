"""
Contract tests for project create CLI command.

These tests verify the CLI interface contract for creating projects
according to the specification in contracts/cli-interface.py.
"""

import pytest
from click.testing import CliRunner
from src.cli.main import main


class TestProjectCreateCLIContract:
    """Test the project create CLI command contract."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_project_create_with_long_options(self):
        """Test project create with long option names."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-docs',
            '--type', 'data'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-docs' in result.output
        assert 'data' in result.output

    def test_project_create_with_short_options(self):
        """Test project create with short option names."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '-n', 'test-storage',
            '-t', 'storage'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-storage' in result.output
        assert 'storage' in result.output

    def test_project_create_with_description(self):
        """Test project create with description option."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-crawl',
            '--type', 'crawling',
            '--description', 'Test crawling project'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-crawl' in result.output
        assert 'crawling' in result.output
        assert 'Test crawling project' in result.output

    def test_project_create_with_short_description(self):
        """Test project create with short description option."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '-n', 'test-desc',
            '-t', 'data',
            '-d', 'Short description'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-desc' in result.output
        assert 'Short description' in result.output

    def test_project_create_with_settings(self):
        """Test project create with JSON settings override."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-settings',
            '--type', 'data',
            '--settings', '{"max_file_size": 52428800}'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-settings' in result.output

    def test_project_create_with_short_settings(self):
        """Test project create with short settings option."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '-n', 'test-settings-short',
            '-t', 'storage',
            '-s', '{"enable_compression": true}'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-settings-short' in result.output

    def test_project_create_with_force(self):
        """Test project create with force overwrite."""
        # First create a project
        self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-force',
            '--type', 'data'
        ])

        # Then try to create it again with force
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-force',
            '--type', 'data',
            '--force'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_create_missing_name(self):
        """Test project create without required name parameter."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--type', 'data'
        ])

        # Should fail with error code 2 (invalid arguments)
        assert result.exit_code == 2
        assert 'name' in result.output.lower()

    def test_project_create_missing_type(self):
        """Test project create without required type parameter."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-no-type'
        ])

        # Should fail with error code 2 (invalid arguments)
        assert result.exit_code == 2
        assert 'type' in result.output.lower()

    def test_project_create_invalid_type(self):
        """Test project create with invalid project type."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-invalid',
            '--type', 'invalid-type'
        ])

        # Should fail with error code 6 (validation error)
        assert result.exit_code == 6
        assert 'Invalid project type' in result.output

    def test_project_create_duplicate_name(self):
        """Test project create with duplicate project name."""
        # First create a project
        self.runner.invoke(main, [
            'project', 'create',
            '--name', 'duplicate-test',
            '--type', 'data'
        ])

        # Then try to create another with same name
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'duplicate-test',
            '--type', 'storage'
        ])

        # Should fail and suggest using --force
        assert result.exit_code != 0
        assert 'already exists' in result.output
        assert '--force' in result.output

    def test_project_create_invalid_json_settings(self):
        """Test project create with malformed JSON settings."""
        result = self.runner.invoke(main, [
            'project', 'create',
            '--name', 'test-bad-json',
            '--type', 'data',
            '--settings', 'invalid-json'
        ])

        # Should fail with validation error
        assert result.exit_code == 6
        assert 'JSON' in result.output or 'settings' in result.output

    def test_project_create_all_project_types(self):
        """Test project create with all valid project types."""
        project_types = ['crawling', 'data', 'storage']

        for project_type in project_types:
            result = self.runner.invoke(main, [
                'project', 'create',
                '--name', f'test-{project_type}',
                '--type', project_type
            ])

            # Should succeed for all valid types (will fail until implementation exists)
            assert result.exit_code == 0, f"Failed for project type: {project_type}"
            assert project_type in result.output

    def test_project_create_help(self):
        """Test project create help message."""
        result = self.runner.invoke(main, [
            'project', 'create', '--help'
        ])

        # Should show help with all options
        assert result.exit_code == 0
        assert '--name' in result.output
        assert '--type' in result.output
        assert '--description' in result.output
        assert '--settings' in result.output
        assert '--force' in result.output

        # Should show short options
        assert '-n' in result.output
        assert '-t' in result.output
        assert '-d' in result.output
        assert '-s' in result.output
        assert '-f' in result.output

    def test_short_key_uniqueness(self):
        """Test that short keys are unique and don't conflict."""
        # This test verifies the CLI_SHORT_KEYS contract
        result = self.runner.invoke(main, [
            'project', 'create', '--help'
        ])

        assert result.exit_code == 0

        # Check that short keys match the contract specification
        help_text = result.output
        assert '-n, --name' in help_text
        assert '-t, --type' in help_text
        assert '-d, --description' in help_text
        assert '-s, --settings' in help_text
        assert '-f, --force' in help_text