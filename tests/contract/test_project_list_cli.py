"""
Contract tests for project list CLI command.

These tests verify the CLI interface contract for listing projects
according to the specification in contracts/cli-interface.py.
"""

import pytest
from click.testing import CliRunner
from src.cli.main import main


class TestProjectListCLIContract:
    """Test the project list CLI command contract."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_project_list_no_options(self):
        """Test project list without any filters."""
        result = self.runner.invoke(main, ['project', 'list'])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_status_filter_long(self):
        """Test project list with status filter using long option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--status', 'active'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_status_filter_short(self):
        """Test project list with status filter using short option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '-st', 'active'  # Two-char to avoid conflict with --settings
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_type_filter_long(self):
        """Test project list with type filter using long option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--type', 'data'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_type_filter_short(self):
        """Test project list with type filter using short option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '-t', 'storage'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_limit_long(self):
        """Test project list with limit using long option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--limit', '10'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_limit_short(self):
        """Test project list with limit using short option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '-l', '5'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_verbose_long(self):
        """Test project list with verbose output using long option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--verbose'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_verbose_short(self):
        """Test project list with verbose output using short option."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '-v'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_combined_filters(self):
        """Test project list with multiple filters combined."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--status', 'active',
            '--type', 'data',
            '--limit', '3',
            '--verbose'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_with_combined_filters_short(self):
        """Test project list with multiple filters using short options."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '-st', 'error',
            '-t', 'crawling',
            '-l', '2',
            '-v'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_list_invalid_status(self):
        """Test project list with invalid status value."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--status', 'invalid-status'
        ])

        # Should fail with validation error
        assert result.exit_code == 6
        assert 'status' in result.output.lower()

    def test_project_list_invalid_type(self):
        """Test project list with invalid project type."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--type', 'invalid-type'
        ])

        # Should fail with validation error
        assert result.exit_code == 6
        assert 'type' in result.output.lower()

    def test_project_list_invalid_limit(self):
        """Test project list with invalid limit value."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--limit', 'not-a-number'
        ])

        # Should fail with validation error
        assert result.exit_code == 2

    def test_project_list_negative_limit(self):
        """Test project list with negative limit value."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--limit', '-1'
        ])

        # Should fail with validation error
        assert result.exit_code == 6

    def test_project_list_zero_limit(self):
        """Test project list with zero limit value."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--limit', '0'
        ])

        # Should fail with validation error
        assert result.exit_code == 6

    def test_project_list_all_valid_statuses(self):
        """Test project list with all valid status values."""
        valid_statuses = ['active', 'inactive', 'error', 'processing']

        for status in valid_statuses:
            result = self.runner.invoke(main, [
                'project', 'list',
                '--status', status
            ])

            # Should succeed for all valid statuses (will fail until implementation exists)
            assert result.exit_code == 0, f"Failed for status: {status}"

    def test_project_list_all_valid_types(self):
        """Test project list with all valid project types."""
        valid_types = ['crawling', 'data', 'storage']

        for project_type in valid_types:
            result = self.runner.invoke(main, [
                'project', 'list',
                '--type', project_type
            ])

            # Should succeed for all valid types (will fail until implementation exists)
            assert result.exit_code == 0, f"Failed for type: {project_type}"

    def test_project_list_help(self):
        """Test project list help message."""
        result = self.runner.invoke(main, [
            'project', 'list', '--help'
        ])

        # Should show help with all options
        assert result.exit_code == 0
        assert '--status' in result.output
        assert '--type' in result.output
        assert '--limit' in result.output
        assert '--verbose' in result.output

        # Should show short options
        assert '-st' in result.output  # Two-char for status
        assert '-t' in result.output
        assert '-l' in result.output
        assert '-v' in result.output

    def test_project_list_output_format(self):
        """Test that project list output follows expected format."""
        result = self.runner.invoke(main, ['project', 'list'])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

        # When implemented, should include project information
        # This test will validate the output format matches ProjectListItem contract

    def test_project_list_verbose_output_format(self):
        """Test that verbose project list includes additional details."""
        result = self.runner.invoke(main, [
            'project', 'list',
            '--verbose'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

        # When implemented, verbose should include more details than basic list

    def test_short_key_uniqueness(self):
        """Test that short keys are unique and don't conflict."""
        # This test verifies the CLI_SHORT_KEYS contract
        result = self.runner.invoke(main, [
            'project', 'list', '--help'
        ])

        assert result.exit_code == 0

        # Check that short keys match the contract specification
        help_text = result.output
        assert '-st, --status' in help_text  # Two-char to avoid conflict
        assert '-t, --type' in help_text
        assert '-l, --limit' in help_text
        assert '-v, --verbose' in help_text

    def test_project_list_empty_result(self):
        """Test project list when no projects exist."""
        result = self.runner.invoke(main, ['project', 'list'])

        # Should succeed even with no projects (will fail until implementation exists)
        assert result.exit_code == 0