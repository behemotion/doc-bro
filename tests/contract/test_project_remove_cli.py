"""
Contract tests for project remove CLI command.

These tests verify the CLI interface contract for removing projects
according to the specification in contracts/cli-interface.py.
"""

import pytest
from click.testing import CliRunner
from src.cli.main import main


class TestProjectRemoveCLIContract:
    """Test the project remove CLI command contract."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_project_remove_with_long_options(self):
        """Test project remove with long option names."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-project'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-project' in result.output

    def test_project_remove_with_short_options(self):
        """Test project remove with short option names."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '-n', 'test-project-short'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0
        assert 'test-project-short' in result.output

    def test_project_remove_with_confirm_long(self):
        """Test project remove with confirm flag using long option."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-confirm',
            '--confirm'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_confirm_short(self):
        """Test project remove with confirm flag using short option."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '-n', 'test-confirm-short',
            '-c'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_backup_long(self):
        """Test project remove with backup option using long option."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-backup',
            '--backup'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_backup_short(self):
        """Test project remove with backup option using short option."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '-n', 'test-backup-short',
            '-b'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_force_long(self):
        """Test project remove with force flag using long option."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-force',
            '--force'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_force_short(self):
        """Test project remove with force flag using short option."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '-n', 'test-force-short',
            '-f'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_all_flags(self):
        """Test project remove with all flags combined."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-all-flags',
            '--confirm',
            '--backup',
            '--force'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_with_all_flags_short(self):
        """Test project remove with all flags using short options."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '-n', 'test-all-short',
            '-c',
            '-b',
            '-f'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_missing_name(self):
        """Test project remove without required name parameter."""
        result = self.runner.invoke(main, [
            'project', 'remove'
        ])

        # Should fail with error code 2 (invalid arguments)
        assert result.exit_code == 2
        assert 'name' in result.output.lower()

    def test_project_remove_nonexistent_project(self):
        """Test project remove for non-existent project."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'nonexistent-project'
        ])

        # Should fail with error code 3 (project not found)
        assert result.exit_code == 3
        assert 'not found' in result.output.lower()

    def test_project_remove_interactive_confirmation(self):
        """Test project remove with interactive confirmation prompt."""
        # Simulate user declining confirmation
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-interactive'
        ], input='n\n')

        # Should be cancelled with operation cancelled exit code
        assert result.exit_code == 7

    def test_project_remove_interactive_confirmation_yes(self):
        """Test project remove with interactive confirmation accepted."""
        # Simulate user accepting confirmation
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-interactive-yes'
        ], input='y\n')

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_force_skips_confirmation(self):
        """Test that force flag skips confirmation prompt."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-force-no-prompt',
            '--force'
        ])

        # Should succeed without any input required (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_confirm_skips_confirmation(self):
        """Test that confirm flag skips confirmation prompt."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-confirm-no-prompt',
            '--confirm'
        ])

        # Should succeed without any input required (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_no_backup(self):
        """Test project remove without backup creation."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-no-backup',
            '--backup', 'false'  # Assuming boolean flag can be disabled
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_type_specific_cleanup(self):
        """Test that remove handles type-specific cleanup correctly."""
        # This will be validated through the actual cleanup behavior
        # For now, just test the command accepts the request
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'test-cleanup',
            '--confirm'
        ])

        # Should succeed (will fail until implementation exists)
        assert result.exit_code == 0

    def test_project_remove_help(self):
        """Test project remove help message."""
        result = self.runner.invoke(main, [
            'project', 'remove', '--help'
        ])

        # Should show help with all options
        assert result.exit_code == 0
        assert '--name' in result.output
        assert '--confirm' in result.output
        assert '--backup' in result.output
        assert '--force' in result.output

        # Should show short options
        assert '-n' in result.output
        assert '-c' in result.output
        assert '-b' in result.output
        assert '-f' in result.output

    def test_short_key_uniqueness(self):
        """Test that short keys are unique and don't conflict."""
        # This test verifies the CLI_SHORT_KEYS contract
        result = self.runner.invoke(main, [
            'project', 'remove', '--help'
        ])

        assert result.exit_code == 0

        # Check that short keys match the contract specification
        help_text = result.output
        assert '-n, --name' in help_text
        assert '-c, --confirm' in help_text
        assert '-b, --backup' in help_text
        assert '-f, --force' in help_text

    def test_project_remove_error_messages(self):
        """Test that error messages follow the CLI_ERROR_MESSAGES contract."""
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'nonexistent-project'
        ])

        # Should fail with project not found error
        assert result.exit_code == 3
        # Error message should be clear and actionable
        assert 'not found' in result.output.lower()

    def test_project_remove_with_dependencies(self):
        """Test project remove when project has dependencies or is in use."""
        # This tests the scenario where a project cannot be removed
        result = self.runner.invoke(main, [
            'project', 'remove',
            '--name', 'project-with-deps'
        ])

        # Behavior depends on implementation - may succeed with warnings
        # or fail with clear explanation (will fail until implementation exists)
        assert result.exit_code in [0, 1, 4]  # Success, general error, or permission denied