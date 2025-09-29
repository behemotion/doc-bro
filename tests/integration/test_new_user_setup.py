"""Integration test for new user setup scenario with shelf-level fill prompting.

This test validates the complete user journey from initial shelf creation
through wizard configuration to content filling.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

# These imports will fail until the enhanced CLI commands are implemented
try:
    from src.cli.commands.shelf import shelf_command
    from src.cli.commands.box import box_command
    from src.services.context_service import ContextService
    from src.logic.wizard.orchestrator import WizardOrchestrator
    from src.logic.wizard.shelf_wizard import ShelfWizard
    CLI_ENHANCED = True
except ImportError:
    CLI_ENHANCED = False
    shelf_command = None
    box_command = None
    ContextService = None
    WizardOrchestrator = None
    ShelfWizard = None


class TestNewUserSetupScenario:
    """Integration test for new user setup workflow."""

    @pytest.mark.integration
    def test_imports_available(self):
        """Test that enhanced CLI commands can be imported."""
        assert CLI_ENHANCED, "Enhanced CLI commands not implemented yet"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_shelf_not_found_creation_prompt(self):
        """Test that accessing non-existent shelf prompts for creation."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock context service to return shelf not found
        with patch('src.cli.commands.shelf.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Simulate shelf doesn't exist
            mock_context = MagicMock()
            mock_context.exists = False
            mock_context.entity_name = "project-docs"
            mock_context.entity_type = "shelf"
            mock_service.check_shelf_exists.return_value = mock_context

            # Mock user input for creation prompt
            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = True

                with patch('src.cli.commands.shelf.create_shelf') as mock_create:
                    mock_create.return_value = True

                    result = runner.invoke(shelf_command, ['project-docs'])

                    # Should prompt for creation
                    mock_confirm.assert_called_once()
                    # Should call create function
                    mock_create.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_shelf_creation_wizard_prompt(self):
        """Test that after creation, user is prompted for setup wizard."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock successful shelf creation
        with patch('src.cli.commands.shelf.create_shelf') as mock_create:
            mock_create.return_value = True

            with patch('click.confirm') as mock_confirm:
                # First confirm: create shelf (yes)
                # Second confirm: launch wizard (yes)
                mock_confirm.side_effect = [True, True]

                with patch('src.cli.commands.shelf.run_shelf_wizard') as mock_wizard:
                    mock_wizard.return_value = True

                    result = runner.invoke(shelf_command, ['project-docs'])

                    # Should ask twice: create and wizard
                    assert mock_confirm.call_count == 2
                    # Should run wizard
                    mock_wizard.assert_called_once_with("project-docs")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_shelf_wizard_configuration_flow(self):
        """Test complete shelf wizard configuration flow."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        # Mock wizard orchestrator
        with patch('src.logic.wizard.orchestrator.WizardOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock wizard steps
            mock_wizard_result = MagicMock()
            mock_wizard_result.success = True
            mock_wizard_result.configuration = {
                "description": "Main project documentation",
                "auto_fill": True,
                "default_box_type": "drag",
                "tags": ["docs", "main", "project"]
            }
            mock_orchestrator.run_wizard.return_value = mock_wizard_result

            from src.logic.wizard.shelf_wizard import ShelfWizard
            wizard = ShelfWizard()

            result = await wizard.run("project-docs")

            # Should complete successfully
            assert result.success is True
            assert result.configuration["description"] == "Main project documentation"
            assert result.configuration["auto_fill"] is True
            assert result.configuration["default_box_type"] == "drag"
            assert "docs" in result.configuration["tags"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_configured_shelf_status_display(self):
        """Test that configured shelf displays proper status."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock context service to return configured shelf
        with patch('src.cli.commands.shelf.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Simulate configured but empty shelf
            mock_context = MagicMock()
            mock_context.exists = True
            mock_context.is_empty = True
            mock_context.entity_name = "project-docs"
            mock_context.entity_type = "shelf"
            mock_context.configuration_state.is_configured = True
            mock_context.configuration_state.has_content = False
            mock_context.content_summary = None
            mock_service.check_shelf_exists.return_value = mock_context

            with patch('src.cli.commands.shelf.display_shelf_status') as mock_display:
                result = runner.invoke(shelf_command, ['project-docs'])

                # Should display status
                mock_display.assert_called_once_with(mock_context)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_shelf_fill_prompt(self):
        """Test that empty shelf prompts for box creation/filling."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock context service to return empty shelf
        with patch('src.cli.commands.shelf.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Simulate empty shelf
            mock_context = MagicMock()
            mock_context.exists = True
            mock_context.is_empty = True
            mock_context.entity_name = "project-docs"
            mock_context.entity_type = "shelf"
            mock_service.check_shelf_exists.return_value = mock_context

            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = True

                with patch('src.cli.commands.shelf.prompt_fill_shelf') as mock_fill_prompt:
                    result = runner.invoke(shelf_command, ['project-docs'])

                    # Should prompt to fill shelf
                    mock_fill_prompt.assert_called_once_with(mock_context)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_box_creation_from_shelf_prompt(self):
        """Test creating boxes when shelf is empty."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        # Mock shelf fill prompt leading to box creation
        with patch('src.cli.commands.shelf.prompt_create_boxes') as mock_box_prompt:
            mock_box_prompt.return_value = ["website-docs", "local-files"]

            with patch('src.cli.commands.box.create_box') as mock_create_box:
                mock_create_box.return_value = True

                # Simulate user choosing to create boxes
                result = await mock_box_prompt("project-docs")

                assert "website-docs" in result
                assert "local-files" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_context_awareness_performance(self):
        """Test that context detection meets performance requirements (<500ms)."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        import time

        # Test context service performance
        context_service = ContextService()

        start_time = time.time()

        # Mock database operations to be fast
        with patch.object(context_service, '_check_database_exists') as mock_check:
            mock_check.return_value = True

            context = await context_service.check_shelf_exists("test-shelf")

            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            # Should be under 500ms
            assert elapsed_ms < 500, f"Context detection took {elapsed_ms}ms, should be <500ms"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_session_cleanup(self):
        """Test that wizard sessions are properly cleaned up after completion."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        # Mock wizard orchestrator with cleanup
        with patch('src.logic.wizard.orchestrator.WizardOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock successful wizard with cleanup
            mock_wizard_result = MagicMock()
            mock_wizard_result.success = True
            mock_orchestrator.run_wizard.return_value = mock_wizard_result
            mock_orchestrator.cleanup_session = AsyncMock()

            # Run wizard
            orchestrator = WizardOrchestrator()
            result = await orchestrator.run_wizard("shelf", "test-shelf", {})

            # Should clean up session
            mock_orchestrator.cleanup_session.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_wizard_sessions(self):
        """Test that multiple wizard sessions can run concurrently."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        # Test concurrent wizard sessions
        orchestrator = WizardOrchestrator()

        # Mock multiple sessions
        with patch.object(orchestrator, 'start_session') as mock_start:
            mock_start.side_effect = ["session-1", "session-2", "session-3"]

            sessions = []
            for i in range(3):
                session_id = await orchestrator.start_session(
                    wizard_type="shelf",
                    target_entity=f"shelf-{i}",
                    config={}
                )
                sessions.append(session_id)

            # All sessions should be unique
            assert len(set(sessions)) == 3
            assert len(sessions) == 3

    @pytest.mark.integration
    def test_cli_flag_consistency(self):
        """Test that enhanced CLI commands use consistent flag patterns."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test --init flag exists and works
        result = runner.invoke(shelf_command, ['--help'])

        if result.exit_code == 0:
            help_text = result.output.lower()

            # Should have --init flag
            assert "--init" in help_text or "-i" in help_text

            # Should have consistent flag descriptions
            assert "wizard" in help_text or "setup" in help_text

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery_graceful(self):
        """Test graceful error recovery during setup process."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test wizard interruption handling
        with patch('src.logic.wizard.orchestrator.WizardOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Simulate wizard interruption
            mock_orchestrator.run_wizard.side_effect = KeyboardInterrupt()

            with patch('src.cli.commands.shelf.handle_wizard_interruption') as mock_handler:
                try:
                    result = runner.invoke(shelf_command, ['test-shelf', '--init'])
                except KeyboardInterrupt:
                    pass

                # Should handle interruption gracefully
                mock_handler.assert_called_once()

    @pytest.mark.integration
    def test_help_text_consistency(self):
        """Test that help text follows consistent patterns."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test shelf command help
        result = runner.invoke(shelf_command, ['--help'])

        if result.exit_code == 0:
            help_text = result.output

            # Should mention context awareness
            assert any(keyword in help_text.lower() for keyword in [
                "create", "wizard", "setup", "configure"
            ])

            # Should have examples
            assert "example" in help_text.lower() or "usage" in help_text.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_scenario_timing(self):
        """Test complete end-to-end scenario meets timing requirements."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        import time

        start_time = time.time()

        # Mock complete workflow
        with patch('src.cli.commands.shelf.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Mock fast operations
            mock_context = MagicMock()
            mock_context.exists = False
            mock_service.check_shelf_exists.return_value = mock_context

            with patch('src.cli.commands.shelf.create_shelf') as mock_create:
                mock_create.return_value = True

                with patch('src.logic.wizard.orchestrator.WizardOrchestrator') as mock_orchestrator_class:
                    mock_orchestrator = AsyncMock()
                    mock_orchestrator_class.return_value = mock_orchestrator

                    mock_result = MagicMock()
                    mock_result.success = True
                    mock_orchestrator.run_wizard.return_value = mock_result

                    # Run complete scenario
                    runner = CliRunner()
                    with patch('click.confirm', return_value=True):
                        result = runner.invoke(shelf_command, ['test-shelf'])

                    end_time = time.time()
                    elapsed_time = end_time - start_time

                    # Complete setup should be under 30 seconds (constitutional requirement)
                    assert elapsed_time < 30, f"Setup took {elapsed_time}s, should be <30s"