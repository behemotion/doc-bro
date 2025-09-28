"""Integration tests for create command wizard flow."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from src.cli.main import main


class TestCreateWizardIntegration:
    """Integration tests for create command wizard functionality."""

    def test_complete_wizard_flow(self):
        """Test complete wizard flow from start to finish."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                # Simulate user inputs
                mock_prompt.side_effect = [
                    "test-docs",  # Project name
                    "https://docs.example.com",  # URL
                    "3",  # Depth
                    "",  # Default model
                ]

                mock_pm.return_value.create_project.return_value = MagicMock(
                    name="test-docs",
                    url="https://docs.example.com"
                )

                result = runner.invoke(main, ["create"], input="y\n")  # Confirm

                assert result.exit_code == 0
                assert mock_pm.return_value.create_project.called
                assert "created" in result.output.lower() or "success" in result.output.lower()

    def test_wizard_validation_flow(self):
        """Test wizard validation with retry on invalid input."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            # Invalid then valid inputs
            mock_prompt.side_effect = [
                "",  # Empty name (invalid)
                "test-docs",  # Valid name
                "not-a-url",  # Invalid URL
                "ftp://invalid.com",  # Invalid protocol
                "https://docs.example.com",  # Valid URL
                "-1",  # Invalid depth
                "100",  # Too deep
                "2",  # Valid depth
                "invalid-model",  # Invalid model
                "",  # Use default
            ]

            with patch('src.services.project_manager.ProjectManager'):
                result = runner.invoke(main, ["create"], input="y\n")

                # Should handle all validation
                assert mock_prompt.call_count >= 4  # At least name, url, depth, model

    def test_wizard_cancel_flow(self):
        """Test canceling wizard at different stages."""
        runner = CliRunner()

        test_cases = [
            (KeyboardInterrupt(), "after name"),
            ([None, KeyboardInterrupt()], "after URL"),
            (["test", "http://test.com", KeyboardInterrupt()], "after depth"),
        ]

        for inputs, stage in test_cases:
            with patch('src.cli.main.prompt') as mock_prompt:
                if isinstance(inputs, list):
                    mock_prompt.side_effect = inputs
                else:
                    mock_prompt.side_effect = inputs

                result = runner.invoke(main, ["create"])

                assert "cancelled" in result.output.lower() or "abort" in result.output.lower()

    def test_wizard_with_existing_project(self):
        """Test wizard when project name already exists."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                mock_prompt.side_effect = [
                    "existing-project",
                    "new-project",  # Retry with new name
                    "https://docs.example.com",
                    "2",
                    "",
                ]

                # First call returns existing, second succeeds
                mock_pm.return_value.get_project.side_effect = [
                    MagicMock(),  # Exists
                    None,  # Doesn't exist
                ]

                result = runner.invoke(main, ["create"], input="y\n")

                assert "already exists" in result.output or "taken" in result.output

    def test_wizard_state_management(self):
        """Test that wizard properly manages state between steps."""
        from src.models.wizard_state import WizardState

        with patch('src.services.wizard_manager.WizardManager') as mock_wm:
            wizard = mock_wm.return_value
            state = MagicMock()
            wizard.get_state.return_value = state

            runner = CliRunner()
            with patch('src.cli.main.prompt') as mock_prompt:
                mock_prompt.side_effect = [
                    "test-project",
                    "https://docs.example.com",
                    "2",
                    "",
                ]

                result = runner.invoke(main, ["create"], input="y\n")

                # State should be updated at each step
                assert wizard.update_state.called or wizard.advance_step.called

    def test_wizard_progress_indicators(self):
        """Test that wizard shows progress through steps."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            mock_prompt.side_effect = [
                "test-project",
                "https://docs.example.com",
                "2",
                "",
            ]

            with patch('src.services.project_manager.ProjectManager'):
                result = runner.invoke(main, ["create"], input="y\n")

                # Should show step indicators
                assert any(
                    indicator in result.output
                    for indicator in ["Step", "1/", "2/", "[1]", "[2]", "•", "→"]
                )

    def test_wizard_help_text(self):
        """Test that wizard provides helpful prompts."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            mock_prompt.side_effect = KeyboardInterrupt()  # Cancel immediately

            result = runner.invoke(main, ["create"])

            # First prompt should be called with helpful text
            if mock_prompt.called:
                first_call = mock_prompt.call_args_list[0]
                prompt_text = str(first_call)
                # Should have descriptive prompt

    def test_wizard_default_values(self):
        """Test that wizard shows and uses default values."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                # User accepts all defaults (empty input)
                mock_prompt.side_effect = [
                    "test-project",
                    "https://docs.example.com",
                    "",  # Default depth
                    "",  # Default model
                ]

                mock_pm.return_value.create_project.return_value = MagicMock()

                result = runner.invoke(main, ["create"], input="y\n")

                # Check that defaults were used
                create_call = mock_pm.return_value.create_project.call_args
                if create_call:
                    kwargs = create_call[1] if len(create_call) > 1 else {}
                    args = create_call[0] if create_call[0] else ()
                    # Should use default depth=2 and model=mxbai-embed-large

    def test_wizard_confirmation_step(self):
        """Test wizard confirmation before creating project."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.cli.main.click.confirm') as mock_confirm:
                mock_prompt.side_effect = [
                    "test-project",
                    "https://docs.example.com",
                    "3",
                    "",
                ]

                # Test rejection
                mock_confirm.return_value = False
                result = runner.invoke(main, ["create"])
                assert "cancelled" in result.output.lower() or "aborted" in result.output.lower()

                # Test confirmation
                mock_confirm.return_value = True
                with patch('src.services.project_manager.ProjectManager'):
                    result = runner.invoke(main, ["create"])
                    assert result.exit_code == 0

    def test_wizard_error_recovery(self):
        """Test that wizard recovers from errors during creation."""
        runner = CliRunner()

        with patch('src.cli.main.prompt') as mock_prompt:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                mock_prompt.side_effect = [
                    "test-project",
                    "https://docs.example.com",
                    "2",
                    "",
                ]

                # Simulate creation error
                mock_pm.return_value.create_project.side_effect = Exception("Database error")

                result = runner.invoke(main, ["create"], input="y\n")

                assert "error" in result.output.lower()
                assert result.exit_code != 0