"""Contract tests for docbro status --install enhancement."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock

from src.cli.main import cli


class TestStatusInstallCommand:
    """Contract tests for the docbro status --install command enhancement."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_status_command_exists(self):
        """Test that status command is available in CLI."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_status_install_option_exists(self):
        """Test that status command has --install option."""
        result = self.runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "--install" in result.output

    @patch('src.services.config.ConfigService')
    def test_status_install_output_format(self, mock_config_service):
        """Test that status --install has proper output format."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should have installation status section
        assert "Installation Status" in result.output
        assert "Method:" in result.output
        assert "Version:" in result.output

    @patch('src.services.config.ConfigService')
    def test_status_install_shows_method(self, mock_config_service):
        """Test that status --install shows installation method."""
        methods = ["uvx", "manual", "development"]

        for method in methods:
            mock_config = Mock()
            mock_config.load_installation_context.return_value = Mock(
                install_method=method,
                version="1.0.0",
                install_date="2025-01-25 10:30:00",
                is_global=True,
                config_dir="/home/user/.config/docbro",
                user_data_dir="/home/user/.local/share/docbro"
            )
            mock_config_service.return_value = mock_config

            result = self.runner.invoke(cli, ["status", "--install"])
            assert result.exit_code == 0

            # Should show the installation method
            assert method in result.output

    @patch('src.services.config.ConfigService')
    def test_status_install_shows_paths(self, mock_config_service):
        """Test that status --install shows installation paths."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro",
            cache_dir="/home/user/.cache/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should show directory paths
        assert "Config Dir:" in result.output
        assert "Data Dir:" in result.output
        assert "/home/user/.config/docbro" in result.output
        assert "/home/user/.local/share/docbro" in result.output

    @patch('src.services.config.ConfigService')
    def test_status_install_shows_version_info(self, mock_config_service):
        """Test that status --install shows version information."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            python_version="3.13.1",
            uv_version="0.4.0",
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should show version information
        assert "Version: 1.0.0" in result.output
        assert "2025-01-25" in result.output  # Install date

    @patch('src.services.config.ConfigService')
    def test_status_install_global_vs_local_indication(self, mock_config_service):
        """Test that status --install indicates global vs local installation."""
        # Test global installation
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            is_global=True,
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should indicate global installation
        assert "global" in result.output.lower()

        # Test local installation
        mock_config.load_installation_context.return_value.is_global = False

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should not indicate global (may show local or project-local)
        output_lower = result.output.lower()
        assert "local" in output_lower or "project" in output_lower

    def test_status_without_install_flag(self):
        """Test that status without --install flag doesn't show installation info."""
        result = self.runner.invoke(cli, ["status"])

        # May or may not exist yet, but should not crash
        if result.exit_code == 0:
            # Should not show detailed installation info
            assert "Installation Status" not in result.output

    def test_status_install_error_handling(self):
        """Test status --install error handling when config unavailable."""
        # When no installation context is available
        result = self.runner.invoke(cli, ["status", "--install"])

        # Should not crash but may show error or default message
        # Exact behavior to be defined in implementation

    @patch('src.services.config.ConfigService')
    def test_status_install_with_missing_optional_fields(self, mock_config_service):
        """Test status --install with missing optional fields."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="manual",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            uv_version=None,  # Optional field missing
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should handle missing optional fields gracefully
        assert "Method: manual" in result.output
        assert "Version: 1.0.0" in result.output

    @patch('src.services.config.ConfigService')
    def test_status_install_formatted_output(self, mock_config_service):
        """Test that status --install has well-formatted output."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            is_global=True,
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro",
            cache_dir="/home/user/.cache/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        output_lines = result.output.split('\n')

        # Should have proper formatting with indentation
        install_section_found = False
        for line in output_lines:
            if "Installation Status:" in line:
                install_section_found = True
            elif install_section_found and line.strip():
                # Lines in installation status section should be indented
                if "Method:" in line or "Version:" in line or "Config Dir:" in line:
                    assert line.startswith(" ") or line.startswith("\t")

    @patch('src.services.config.ConfigService')
    def test_status_install_integration_with_existing_status(self, mock_config_service):
        """Test that status --install integrates with existing status output."""
        mock_config = Mock()
        mock_config.load_installation_context.return_value = Mock(
            install_method="uvx",
            version="1.0.0",
            install_date="2025-01-25 10:30:00",
            config_dir="/home/user/.config/docbro",
            user_data_dir="/home/user/.local/share/docbro"
        )
        mock_config_service.return_value = mock_config

        result = self.runner.invoke(cli, ["status", "--install"])
        assert result.exit_code == 0

        # Should include both regular status info and installation info
        # (Regular status functionality should still work)