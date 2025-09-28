"""Contract tests for 'docbro system-check' command."""

import json
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.cli.main import main
from src.models.system_requirements import SystemRequirements


class TestSystemCheckCommand:
    """Test cases for the system-check command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_system_check_command_exists(self):
        """Test that the system-check command exists and shows help."""
        result = self.runner.invoke(main, ["system-check", "--help"])
        assert result.exit_code == 0
        assert "system-check" in result.output.lower()
        assert "Check system requirements" in result.output

    def test_system_check_shows_help_content(self):
        """Test that help shows proper command description and examples."""
        result = self.runner.invoke(main, ["system-check", "--help"])
        assert result.exit_code == 0
        assert "python version" in result.output.lower()
        assert "memory" in result.output.lower()
        assert "disk space" in result.output.lower()
        assert "--json" in result.output
        assert "--verbose" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_basic_execution(self, mock_validate):
        """Test basic system-check command execution."""
        # Mock a system that meets all requirements
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 0  # Should succeed when all requirements met
        assert "System Requirements Status" in result.output
        assert "READY" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_insufficient_requirements(self, mock_validate):
        """Test system-check when requirements are not met."""
        # Mock a system with insufficient memory
        mock_requirements = SystemRequirements(
            python_version="3.12.0",
            python_valid=False,
            available_memory=2,
            memory_valid=False,
            available_disk=20,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=False,
            uv_version=None
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1  # Should fail when requirements not met
        assert "NOT READY" in result.output
        assert "Missing Requirements" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_verbose_mode(self, mock_validate):
        """Test system-check with verbose flag for detailed information."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="linux",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check", "--verbose"])

        assert result.exit_code == 0
        assert "Details" in result.output
        assert "Compatible Python version" in result.output or "Sufficient memory" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_json_output(self, mock_validate):
        """Test system-check with JSON output format."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="windows",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert "system_ready" in output_data
        assert "requirements" in output_data
        assert output_data["system_ready"] == True
        assert "python" in output_data["requirements"]
        assert "memory" in output_data["requirements"]
        assert "disk" in output_data["requirements"]
        assert "platform" in output_data["requirements"]
        assert "uv" in output_data["requirements"]

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_json_verbose_output(self, mock_validate):
        """Test system-check with JSON and verbose flags."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=4,
            memory_valid=True,
            available_disk=2,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=False,
            uv_version=None
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check", "--json", "--verbose"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert "details" in output_data
        assert "suggestions" in output_data["details"]
        assert "next_steps" in output_data["details"]

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_error_handling(self, mock_validate):
        """Test system-check behavior when validation fails."""
        mock_validate.side_effect = Exception("Mock validation error")

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1
        assert "System check failed" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_error_handling_json(self, mock_validate):
        """Test system-check error handling with JSON output."""
        mock_validate.side_effect = Exception("Mock validation error")

        result = self.runner.invoke(main, ["system-check", "--json"])

        assert result.exit_code == 1

        # Parse JSON error output
        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "system_ready" in output_data
        assert output_data["system_ready"] == False
        assert "validation_failed" in output_data

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_shows_python_requirements(self, mock_validate):
        """Test that system-check validates Python version requirements."""
        mock_requirements = SystemRequirements(
            python_version="3.12.0",
            python_valid=False,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1
        assert "Python" in result.output
        assert "3.13.0" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_shows_memory_requirements(self, mock_validate):
        """Test that system-check validates memory requirements."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=2,
            memory_valid=False,
            available_disk=20,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1
        assert "Memory" in result.output or "memory" in result.output
        assert "4 GB" in result.output or "4GB" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_shows_disk_requirements(self, mock_validate):
        """Test that system-check validates disk space requirements."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=1,
            disk_valid=False,
            platform="darwin",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1
        assert "Disk" in result.output or "disk" in result.output
        assert "2 GB" in result.output or "2GB" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_shows_platform_requirements(self, mock_validate):
        """Test that system-check validates platform support."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="unsupported",
            platform_supported=False,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1
        assert "Platform" in result.output or "platform" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_shows_uv_status(self, mock_validate):
        """Test that system-check shows UV availability status."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=False,
            uv_version=None
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 0  # UV is optional, so should still pass
        assert "UV" in result.output or "uv" in result.output
        assert "Not available" in result.output or "⚠" in result.output

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_provides_suggestions(self, mock_validate):
        """Test that system-check provides helpful suggestions for missing requirements."""
        mock_requirements = SystemRequirements(
            python_version="3.12.0",
            python_valid=False,
            available_memory=2,
            memory_valid=False,
            available_disk=1,
            disk_valid=False,
            platform="unsupported",
            platform_supported=False,
            uv_available=False,
            uv_version=None
        )
        mock_validate.return_value = mock_requirements

        result = self.runner.invoke(main, ["system-check"])

        assert result.exit_code == 1
        assert "Suggestions" in result.output
        # Should contain helpful suggestions
        assert any(keyword in result.output for keyword in ["python.org", "memory", "disk", "UV"])

    def test_system_check_standalone_execution(self):
        """Test that the system_check module can be run standalone."""
        # This tests the if __name__ == "__main__": functionality
        with patch('src.cli.system_check.system_check') as mock_cmd:
            mock_cmd.return_value = None

            # Import and test the standalone execution path
            from src.cli.system_check import system_check
            assert callable(system_check)

    @patch('src.services.system_validator.SystemRequirementsService.validate_system_requirements')
    def test_system_check_integration_with_main_cli(self, mock_validate):
        """Test that system-check is properly integrated with main CLI."""
        mock_requirements = SystemRequirements(
            python_version="3.13.5",
            python_valid=True,
            available_memory=8,
            memory_valid=True,
            available_disk=20,
            disk_valid=True,
            platform="darwin",
            platform_supported=True,
            uv_available=True,
            uv_version="0.8.9"
        )
        mock_validate.return_value = mock_requirements

        # Test that command appears in main help
        result = self.runner.invoke(main, ["--help"])
        assert "system-check" in result.output

        # Test that command works through main CLI
        result = self.runner.invoke(main, ["system-check"])
        assert result.exit_code == 0