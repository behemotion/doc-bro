"""Contract tests for docbro version --detailed command."""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, Mock

from src.cli.main import cli


class TestVersionDetailedCommand:
    """Contract tests for the docbro version --detailed command interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_command_exists(self):
        """Test that version command is available in CLI."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_version_detailed_option_exists(self):
        """Test that version command has --detailed option."""
        result = self.runner.invoke(cli, ["version", "--help"])
        assert result.exit_code == 0
        assert "--detailed" in result.output

    @patch('src.services.config.ConfigService')
    def test_version_detailed_json_output_format(self, mock_config_service):
        """Test that version --detailed returns valid JSON format."""
        # Mock config service to return installation context
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            install_date="2025-01-25T10:30:00Z",
            version="1.0.0",
            python_version="3.13.1",
            uv_version="0.4.0",
            install_path="/usr/local/bin/docbro",
            is_global=True
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["version", "--detailed"])

        assert result.exit_code == 0

        # Output should be valid JSON
        try:
            json_output = json.loads(result.output)
            assert isinstance(json_output, dict)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    @patch('src.services.config.ConfigService')
    def test_version_detailed_required_fields(self, mock_config_service):
        """Test that version --detailed contains all required fields."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            install_date="2025-01-25T10:30:00Z",
            version="1.0.0",
            python_version="3.13.1",
            uv_version="0.4.0",
            install_path="/usr/local/bin/docbro",
            is_global=True,
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro",
            cache_dir="/home/user/.cache/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)

        # Check required fields
        required_fields = [
            "version",
            "install_method",
            "install_date",
            "python_version",
            "install_path",
            "is_global"
        ]

        for field in required_fields:
            assert field in json_output, f"Missing required field: {field}"

    @patch('src.services.config.ConfigService')
    @patch('src.services.detection.ServiceDetectionService')
    def test_version_detailed_services_section(self, mock_detection_service, mock_config_service):
        """Test that version --detailed includes services status."""
        # Mock config service
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            version="1.0.0",
            install_method="uvx",
            install_date="2025-01-25T10:30:00Z",
            python_version="3.13.1",
            is_global=True,
            install_path="/usr/local/bin/docbro"
        )
        mock_config_service.return_value = mock_config

        # Mock service detection
        mock_detection = Mock()
        mock_detection.check_all_services.return_value = {
            "docker": {"available": False, "version": None},
            "ollama": {"available": True, "version": "0.1.17"}
        }
        mock_detection_service.return_value = mock_detection

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)

        # Should have services section
        assert "services" in json_output
        assert isinstance(json_output["services"], dict)

        # Should have expected services
        services = json_output["services"]
        assert "docker" in services
        assert "ollama" in services

        # Service entries should have expected structure
        assert "available" in services["docker"]
        assert "version" in services["docker"]

    @patch('src.services.config.ConfigService')
    def test_version_detailed_path_information(self, mock_config_service):
        """Test that version --detailed includes path information."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            version="1.0.0",
            install_method="uvx",
            install_date="2025-01-25T10:30:00Z",
            python_version="3.13.1",
            is_global=True,
            install_path="/usr/local/bin/docbro",
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro",
            cache_dir="/home/user/.cache/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)

        # Should include path information
        assert "install_path" in json_output
        assert "config_dir" in json_output or "paths" in json_output
        assert "user_data_dir" in json_output or "paths" in json_output

    @patch('src.services.config.ConfigService')
    def test_version_detailed_installation_method_display(self, mock_config_service):
        """Test different installation methods are displayed correctly."""
        methods = ["uvx", "manual", "development"]

        for method in methods:
            mock_config = Mock()
            mock_config.load_installation_context.return_value = Mock(
                version="1.0.0",
                install_method=method,
                install_date="2025-01-25T10:30:00Z",
                python_version="3.13.1",
                is_global=True,
                install_path="/usr/local/bin/docbro"
            )
            mock_config_service.return_value = mock_config

            result = self.runner.invoke(cli, ["version", "--detailed"])
            assert result.exit_code == 0

            json_output = json.loads(result.output)
            assert json_output["install_method"] == method

    def test_version_detailed_error_handling(self):
        """Test version --detailed error handling when config unavailable."""
        # This test will pass once the command handles missing config gracefully
        result = self.runner.invoke(cli, ["version", "--detailed"])

        # Should not crash, but may show error or default values
        # Exact behavior will be defined in implementation

    @patch('src.services.config.ConfigService')
    def test_version_detailed_uv_version_optional(self, mock_config_service):
        """Test that uv_version is optional in output."""
        # Test with uv_version present
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            version="1.0.0",
            install_method="uvx",
            install_date="2025-01-25T10:30:00Z",
            python_version="3.13.1",
            uv_version="0.4.0",
            is_global=True,
            install_path="/usr/local/bin/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)
        assert json_output["uv_version"] == "0.4.0"

        # Test with uv_version None
        mock_config.load_installation_context.return_value.uv_version = None

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)
        assert json_output["uv_version"] is None

    @patch('src.services.config.ConfigService')
    def test_version_detailed_global_vs_local_flag(self, mock_config_service):
        """Test that is_global flag is properly displayed."""
        # Test global installation
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            version="1.0.0",
            install_method="uvx",
            install_date="2025-01-25T10:30:00Z",
            python_version="3.13.1",
            is_global=True,
            install_path="/usr/local/bin/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)
        assert json_output["is_global"] is True

        # Test local installation
        mock_config.load_installation_context.return_value.is_global = False

        result = self.runner.invoke(cli, ["version", "--detailed"])
        assert result.exit_code == 0

        json_output = json.loads(result.output)
        assert json_output["is_global"] is False

    def test_version_basic_vs_detailed_difference(self):
        """Test that basic version and detailed version are different."""
        # Test basic version
        result_basic = self.runner.invoke(cli, ["--version"])

        # Test detailed version
        result_detailed = self.runner.invoke(cli, ["version", "--detailed"])

        # Outputs should be different formats
        # Basic should be simple string, detailed should be JSON
        if result_basic.exit_code == 0 and result_detailed.exit_code == 0:
            try:
                # Detailed should be JSON
                json.loads(result_detailed.output)
                # Basic should not be JSON
                with pytest.raises(json.JSONDecodeError):
                    json.loads(result_basic.output)
            except json.JSONDecodeError:
                pytest.fail("Detailed version should be valid JSON")