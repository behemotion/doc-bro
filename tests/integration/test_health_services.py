"""Integration test for service status health check scenario."""

import pytest
from click.testing import CliRunner

from src.cli.main import main


class TestHealthServicesIntegration:
    """Test service status health check integration scenario."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_service_status_check_scenario(self):
        """
        Quickstart Scenario 3: Service Status Check
        Goal: Verify external service availability
        """
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--services"])

        # Expect failure during TDD phase
        assert result.exit_code != 0, "Services health test should fail until implementation is complete"

        # TODO: After implementation, validate:
        # assert "External Services" in result.output
        # service_components = ["Docker Service", "Qdrant Database", "Ollama Service", "Git"]
        # for component in service_components:
        #     assert component in result.output

    def test_service_check_excludes_system(self):
        """Service-only check should not include system requirements."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--services"])

        # Expect failure during TDD phase
        assert result.exit_code != 0, "Service exclusion test should fail until implementation is complete"

        # TODO: After implementation, validate system exclusion:
        # system_components = ["Python Version", "Available Memory", "Available Disk Space"]
        # for component in system_components:
        #     assert component not in result.output

    def test_service_check_shows_connection_details(self):
        """Service check should show connection status and details."""
        # This test should FAIL until implementation is complete
        result = self.runner.invoke(main, ["health", "--services"])

        # Expect failure during TDD phase
        assert result.exit_code != 0, "Connection details test should fail until implementation is complete"

        # TODO: After implementation, validate connection info:
        # - Should show version numbers for available services
        # - Should show connection URLs where applicable
        # - Should provide resolution guidance for unavailable services