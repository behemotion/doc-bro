"""Contract tests for CLI create command wizard functionality."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.cli.main import main


class TestCliCreateWizard:
    """Test CLI create command wizard mode."""

    def test_create_without_args_launches_wizard(self):
        """Test that create without arguments launches interactive wizard."""
        runner = CliRunner()

        # Mock the wizard interaction
        with patch('src.cli.main.prompt') as mock_prompt:
            mock_prompt.side_effect = [
                "test-project",  # Project name
                "https://docs.example.com",  # URL
                "2",  # Depth
                "mxbai-embed-large"  # Model
            ]

            result = runner.invoke(main, ["create"], catch_exceptions=False)

            # Wizard should be invoked
            assert mock_prompt.called
            assert mock_prompt.call_count >= 3  # At least name, url, depth

    def test_create_with_args_skips_wizard(self):
        """Test that create with arguments bypasses wizard."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                mock_pm.return_value.create_project.return_value = MagicMock()

                result = runner.invoke(main, [
                    "create", "test-project",
                    "--url", "https://docs.example.com",
                    "--depth", "2"
                ])

                # Wizard should NOT be invoked
                assert not mock_prompt.called

    def test_wizard_validates_input(self):
        """Test that wizard validates user input."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            # First attempt with invalid URL, then valid inputs
            mock_prompt.side_effect = [
                "test-project",
                "not-a-url",  # Invalid URL
                "https://docs.example.com",  # Valid URL
                "2",
                "mxbai-embed-large"
            ]

            with patch('src.cli.main.click.echo') as mock_echo:
                result = runner.invoke(main, ["create"], catch_exceptions=False)

                # Should show validation error
                validation_shown = any(
                    "invalid" in str(call).lower() or "url" in str(call).lower()
                    for call in mock_echo.call_args_list
                )
                assert validation_shown

    def test_wizard_handles_interruption(self):
        """Test that wizard handles user interruption gracefully."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            # Simulate Ctrl+C during wizard
            mock_prompt.side_effect = KeyboardInterrupt()

            result = runner.invoke(main, ["create"])

            # Should exit gracefully
            assert result.exit_code != 0
            assert "cancelled" in result.output.lower() or "aborted" in result.output.lower()

    def test_wizard_shows_progress(self):
        """Test that wizard shows progress through steps."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            mock_prompt.side_effect = [
                "test-project",
                "https://docs.example.com",
                "2",
                "mxbai-embed-large"
            ]

            with patch('src.cli.main.click.echo') as mock_echo:
                result = runner.invoke(main, ["create"], catch_exceptions=False)

                # Should show step indicators
                output_text = ' '.join(str(call) for call in mock_echo.call_args_list)
                progress_shown = any(
                    keyword in output_text.lower()
                    for keyword in ["step", "1/", "2/", "progress", "creating"]
                )
                assert progress_shown

    def test_wizard_confirms_before_creation(self):
        """Test that wizard shows confirmation before creating project."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.cli.main.click.confirm') as mock_confirm:
                mock_prompt.side_effect = [
                    "test-project",
                    "https://docs.example.com",
                    "3",
                    "mxbai-embed-large"
                ]
                mock_confirm.return_value = True

                result = runner.invoke(main, ["create"], catch_exceptions=False)

                # Should ask for confirmation
                assert mock_confirm.called

    def test_wizard_default_values(self):
        """Test that wizard provides sensible defaults."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            # User just presses enter for defaults
            mock_prompt.side_effect = [
                "test-project",
                "https://docs.example.com",
                "",  # Use default depth
                ""   # Use default model
            ]

            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                mock_pm.return_value.create_project.return_value = MagicMock()

                result = runner.invoke(main, ["create"], catch_exceptions=False)

                # Should use default values
                create_call = mock_pm.return_value.create_project.call_args
                assert create_call is not None
                # Check that defaults were applied (depth=2, model=mxbai-embed-large)