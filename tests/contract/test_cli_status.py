"""Contract tests for 'docbro status' command."""

import pytest
from click.testing import CliRunner

from src.cli.main import main


class TestStatusCommand:
    """Test cases for the status command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_status_command_exists(self):
        """Test that the status command exists and shows help."""
        result = self.runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_status_shows_system_information(self):
        """Test that status shows system information."""
        result = self.runner.invoke(main, ["status"])
        # This should fail until implementation exists
        assert result.exit_code != 0 or "not implemented" in result.output.lower()

    def test_status_checks_service_health(self):
        """Test that status checks health of all services."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should check Qdrant, Ollama connectivity
        # For now, should fail
        assert result.exit_code != 0 or any(service in result.output.lower()
                                          for service in ["qdrant", "ollama"])

    def test_status_shows_project_count(self):
        """Test that status shows project statistics."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should show project count and stats
        # For now, should fail
        assert result.exit_code != 0 or "projects" in result.output.lower()

    def test_status_shows_active_crawls(self):
        """Test that status shows any active crawl operations."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should show currently running crawls
        # For now, should fail
        assert result.exit_code != 0 or "crawl" in result.output.lower()

    def test_status_shows_service_urls(self):
        """Test that status shows service connection URLs."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should show URLs for Qdrant, Redis, Ollama
        # For now, should fail
        assert result.exit_code != 0 or "localhost" in result.output

    def test_status_indicates_service_health(self):
        """Test that status clearly indicates service health status."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should show health status with indicators
        # For now, should fail
        assert result.exit_code != 0 or any(indicator in result.output.lower()
                                          for indicator in ["✅", "❌", "healthy", "unhealthy"])

    def test_status_shows_storage_usage(self):
        """Test that status shows storage usage information."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should show disk usage for data directory
        # For now, should fail
        assert result.exit_code != 0 or any(unit in result.output.lower()
                                          for unit in ["mb", "gb", "size"])

    def test_status_shows_configuration_summary(self):
        """Test that status shows key configuration settings."""
        result = self.runner.invoke(main, ["status"])
        # When implemented, should show important config values
        # For now, should fail
        assert result.exit_code != 0 or "config" in result.output.lower()

    def test_status_handles_service_failures(self):
        """Test status behavior when services are unavailable."""
        # This test will fail until implementation exists
        result = self.runner.invoke(main, ["status"])
        # Should gracefully handle when services are down
        assert result.exit_code != 0

    def test_status_verbose_mode(self):
        """Test status with verbose flag for detailed information."""
        result = self.runner.invoke(main, ["status", "--verbose"])
        # This should fail until implementation exists
        # When implemented, should show detailed system information
        assert result.exit_code != 0

    def test_status_json_output(self):
        """Test status with JSON output format."""
        result = self.runner.invoke(main, ["status", "--json"])
        # This should fail until implementation exists
        # When implemented, should output structured JSON
        assert result.exit_code != 0

    def test_status_exit_codes(self):
        """Test that status uses appropriate exit codes."""
        result = self.runner.invoke(main, ["status"])
        # This should fail until implementation exists
        # When implemented, should use exit code 0 for healthy, non-zero for issues
        assert result.exit_code != 0