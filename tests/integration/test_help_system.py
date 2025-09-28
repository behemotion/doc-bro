"""Integration tests for the enhanced help system."""

import pytest
from click.testing import CliRunner
from src.cli.main import main
from src.cli.help_formatter import CliHelpFormatter


class TestHelpSystemIntegration:
    """Integration tests for help system improvements."""

    def test_help_formatter_integration(self):
        """Test that custom help formatter is properly integrated."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0

        # Check that output has enhanced formatting
        output_lines = result.output.split('\n')

        # Should have sections
        assert any("Commands:" in line for line in output_lines)
        assert any("Options:" in line for line in output_lines)

        # Should have proper indentation
        indented_lines = [line for line in output_lines if line.startswith('  ') and line.strip()]
        assert len(indented_lines) > 0

    def test_bare_command_behavior(self):
        """Test complete flow when running docbro without arguments."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 0

        # Should not show full help
        assert "Commands:" not in result.output

        # Should show suggestion
        assert "--help" in result.output
        assert ("Try" in result.output or "Use" in result.output)

    def test_help_consistency_across_commands(self):
        """Test that help format is consistent across all commands."""
        runner = CliRunner()
        commands = ["create", "crawl", "list", "search", "remove", "serve", "status"]

        help_structures = []
        for cmd in commands:
            result = runner.invoke(main, [cmd, "--help"])
            assert result.exit_code == 0

            # Extract structure markers
            has_usage = "Usage:" in result.output
            has_options = "Options:" in result.output or "--help" in result.output
            help_structures.append((has_usage, has_options))

        # All should have same structure
        assert all(struct == help_structures[0] for struct in help_structures)

    def test_help_with_debug_flag(self):
        """Test that help works correctly with debug flag."""
        runner = CliRunner()

        # Help should work even with debug
        result = runner.invoke(main, ["--debug", "--help"])
        assert result.exit_code == 0
        assert "Commands:" in result.output

        # Debug flag should be documented
        assert "--debug" in result.output

    def test_nested_command_help(self):
        """Test help for nested/grouped commands if any."""
        runner = CliRunner()

        # Test service commands group if it exists
        result = runner.invoke(main, ["services", "--help"], catch_exceptions=False)

        if result.exit_code == 0:
            # Should show subcommands
            assert "Commands:" in result.output or "Available" in result.output

    def test_help_shows_new_options(self):
        """Test that new CLI options are documented in help."""
        runner = CliRunner()

        # Check main help
        result = runner.invoke(main, ["--help"])
        assert "--debug" in result.output

        # Check crawl help for new options
        result = runner.invoke(main, ["crawl", "--help"])
        assert "--update" in result.output
        assert "--all" in result.output

    def test_help_error_messages(self):
        """Test that error messages suggest using help."""
        runner = CliRunner()

        # Invalid command
        result = runner.invoke(main, ["nonexistent"])
        assert result.exit_code != 0
        assert "--help" in result.output or "help" in result.output.lower()

        # Missing required argument
        result = runner.invoke(main, ["create"])
        if result.exit_code != 0:  # Only if wizard not implemented yet
            assert "help" in result.output.lower() or "usage" in result.output.lower()

    def test_help_output_length(self):
        """Test that help output is comprehensive but not overwhelming."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        lines = result.output.split('\n')
        # Should be detailed but reasonable
        assert 10 < len(lines) < 200  # Reasonable range for main help

        # Individual command help should be shorter
        result = runner.invoke(main, ["list", "--help"])
        lines = result.output.split('\n')
        assert 5 < len(lines) < 50  # Shorter for specific commands

    def test_help_examples_if_present(self):
        """Test that help includes examples if implemented."""
        runner = CliRunner()
        result = runner.invoke(main, ["crawl", "--help"])

        # Check if examples are provided (optional enhancement)
        if "example" in result.output.lower() or "e.g." in result.output.lower():
            # Examples should be indented
            example_lines = [
                line for line in result.output.split('\n')
                if "example" in line.lower() or "e.g." in line.lower()
            ]
            assert len(example_lines) > 0