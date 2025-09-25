"""Contract tests for docbro setup command."""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, Mock

from src.cli.main import cli


class TestSetupCommand:
    """Contract tests for the docbro setup command interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_setup_command_exists(self):
        """Test that setup command is available in CLI."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "setup" in result.output.lower()

    def test_setup_command_help(self):
        """Test that setup command has proper help text."""
        result = self.runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.output.lower()
        assert "wizard" in result.output.lower()

    def test_setup_command_options(self):
        """Test that setup command has required options."""
        result = self.runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0

        # Check for required options
        assert "--force" in result.output
        assert "--skip-services" in result.output
        assert "--non-interactive" in result.output

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_basic_execution(self, mock_setup_service):
        """Test basic setup command execution."""
        # Mock the setup service
        mock_service = Mock()
        mock_service.run_setup.return_value = True
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup"])

        # Should not crash and should call setup service
        mock_service.run_setup.assert_called_once()

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_with_force_flag(self, mock_setup_service):
        """Test setup command with --force flag."""
        mock_service = Mock()
        mock_service.run_setup.return_value = True
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup", "--force"])

        # Should call setup with force=True
        mock_service.run_setup.assert_called_once_with(force=True)

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_with_skip_services(self, mock_setup_service):
        """Test setup command with --skip-services flag."""
        mock_service = Mock()
        mock_service.run_setup.return_value = True
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup", "--skip-services"])

        # Should call setup with skip_services=True
        mock_service.run_setup.assert_called_once_with(skip_services=True)

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_with_non_interactive(self, mock_setup_service):
        """Test setup command with --non-interactive flag."""
        mock_service = Mock()
        mock_service.run_setup.return_value = True
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup", "--non-interactive"])

        # Should call setup with interactive=False
        mock_service.run_setup.assert_called_once_with(interactive=False)

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_exit_codes(self, mock_setup_service):
        """Test setup command exit codes."""
        mock_service = Mock()
        mock_setup_service.return_value = mock_service

        # Test successful completion
        mock_service.run_setup.return_value = True
        result = self.runner.invoke(cli, ["setup"])
        assert result.exit_code == 0

        # Test setup failure
        mock_service.run_setup.return_value = False
        result = self.runner.invoke(cli, ["setup"])
        assert result.exit_code == 1

        # Test setup already completed
        mock_service.run_setup.side_effect = Exception("Setup already completed")
        result = self.runner.invoke(cli, ["setup"])
        assert result.exit_code == 3

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_output_format(self, mock_setup_service):
        """Test setup command output format and messages."""
        mock_service = Mock()
        mock_service.run_setup.return_value = True
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup"])

        # Should have structured output
        assert "DocBro Setup Wizard" in result.output
        assert "Checking installation" in result.output

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_service_detection_output(self, mock_setup_service):
        """Test that setup command shows service detection results."""
        mock_service = Mock()
        mock_service.get_service_status.return_value = {
            "docker": {"available": False, "version": None},
            "ollama": {"available": True, "version": "0.1.17"}
        }
        mock_service.run_setup.return_value = True
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup"])

        # Should show service status
        assert "Checking services" in result.output
        assert "Docker" in result.output or "docker" in result.output
        assert "Ollama" in result.output or "ollama" in result.output

    @patch('src.services.setup.SetupWizardService')
    def test_setup_command_user_cancellation(self, mock_setup_service):
        """Test setup command when user cancels."""
        mock_service = Mock()
        mock_service.run_setup.side_effect = KeyboardInterrupt()
        mock_setup_service.return_value = mock_service

        result = self.runner.invoke(cli, ["setup"])

        # Should exit with code 2 for user cancellation
        assert result.exit_code == 2

    @patch('src.services.setup.SetupWizardService')
    @patch('src.services.config.ConfigService')
    def test_setup_command_config_interaction(self, mock_config_service, mock_setup_service):
        """Test that setup command interacts with configuration service."""
        mock_setup = Mock()
        mock_config = Mock()

        mock_setup_service.return_value = mock_setup
        mock_config_service.return_value = mock_config

        mock_setup.run_setup.return_value = True

        result = self.runner.invoke(cli, ["setup"])

        # Should interact with config service
        assert result.exit_code == 0

    def test_setup_command_combined_flags(self):
        """Test setup command with multiple flags combined."""
        result = self.runner.invoke(cli, ["setup", "--force", "--skip-services", "--non-interactive"])

        # Should not fail with argument parsing
        # (Implementation details will be tested when command exists)
        # For now, just ensure the command can be called with all flags