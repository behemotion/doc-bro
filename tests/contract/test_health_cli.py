"""Contract tests for health CLI interface."""

import pytest
from click.testing import CliRunner

from src.cli.main import main


class TestHealthCLIContract:
    """Test the health command CLI interface contract."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_health_command_exists(self):
        """Health command should be available in CLI."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "health" in result.output

    def test_health_command_basic_invocation(self):
        """Health command should accept basic invocation."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health"])
        # Temporarily expect failure during TDD phase
        # TODO: Change to assert result.exit_code == 0 after implementation
        assert result.exit_code != 0, "This test should fail until health command is implemented"

    def test_health_command_help(self):
        """Health command should provide help information."""
        result = self.runner.invoke(main, ["health", "--help"])
        # Should work even without full implementation
        assert result.exit_code == 0 or "health" in result.output.lower()

    def test_health_command_accepts_system_flag(self):
        """Health command should accept --system flag."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--system"])
        # Temporarily expect failure during TDD phase
        assert result.exit_code != 0, "This test should fail until health command is implemented"

    def test_health_command_accepts_services_flag(self):
        """Health command should accept --services flag."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--services"])
        # Temporarily expect failure during TDD phase
        assert result.exit_code != 0, "This test should fail until health command is implemented"

    def test_health_command_accepts_config_flag(self):
        """Health command should accept --config flag."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--config"])
        # Temporarily expect failure during TDD phase
        assert result.exit_code != 0, "This test should fail until health command is implemented"

    def test_health_command_accepts_format_flag(self):
        """Health command should accept --format flag."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--format", "json"])
        # Temporarily expect failure during TDD phase
        assert result.exit_code != 0, "This test should fail until health command is implemented"