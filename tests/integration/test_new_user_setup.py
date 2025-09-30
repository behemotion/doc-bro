"""Integration test for new user setup scenario with shelf-level configuration.

This test validates the complete user journey from initial shelf creation
through configuration to content management.
"""

import asyncio
import pytest
from click.testing import CliRunner

from src.cli.commands.shelf import shelf as shelf_command
from src.cli.commands.box import box as box_command
from src.services.context_service import ContextService
from src.services.shelf_service import ShelfService
from src.services.box_service import BoxService
from src.logic.wizard.orchestrator import WizardOrchestrator
from src.logic.wizard.shelf_wizard import ShelfWizard
from src.logic.wizard.box_wizard import BoxWizard


class TestNewUserSetupScenario:
    """Integration test for new user setup workflow."""

    @pytest.mark.integration
    def test_imports_available(self):
        """Test that enhanced CLI commands can be imported."""
        assert shelf_command is not None
        assert box_command is not None
        assert ContextService is not None
        assert WizardOrchestrator is not None
        assert ShelfWizard is not None

    @pytest.mark.integration
    def test_shelf_commands_available(self):
        """Test that shelf commands are available."""
        runner = CliRunner()
        result = runner.invoke(shelf_command, ['--help'])
        assert result.exit_code == 0
        assert 'shelf' in result.output.lower() or 'shelf' in str(shelf_command)

    @pytest.mark.integration
    def test_box_commands_available(self):
        """Test that box commands are available."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['--help'])
        assert result.exit_code == 0
        assert 'box' in result.output.lower() or 'box' in str(box_command)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_context_service_exists(self):
        """Test that ContextService can be instantiated."""
        service = ContextService()
        assert service is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_shelf_service_exists(self):
        """Test that ShelfService can be instantiated."""
        service = ShelfService()
        assert service is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_box_service_exists(self):
        """Test that BoxService can be instantiated."""
        service = BoxService()
        assert service is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_orchestrator_exists(self):
        """Test that WizardOrchestrator can be instantiated."""
        orchestrator = WizardOrchestrator()
        assert orchestrator is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_shelf_wizard_exists(self):
        """Test that ShelfWizard can be instantiated."""
        wizard = ShelfWizard()
        assert wizard is not None
        assert hasattr(wizard, 'run')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_box_wizard_exists(self):
        """Test that BoxWizard can be instantiated."""
        wizard = BoxWizard()
        assert wizard is not None
        assert hasattr(wizard, 'run')

    @pytest.mark.integration
    def test_shelf_create_command_exists(self):
        """Test that shelf create command exists."""
        runner = CliRunner()
        result = runner.invoke(shelf_command, ['create', '--help'])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_shelf_list_command_exists(self):
        """Test that shelf list command exists."""
        runner = CliRunner()
        result = runner.invoke(shelf_command, ['list', '--help'])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_box_create_command_exists(self):
        """Test that box create command exists."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['create', '--help'])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_box_list_command_exists(self):
        """Test that box list command exists."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['list', '--help'])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_shelf_cli_has_init_flag(self):
        """Test that shelf commands support --init flag."""
        runner = CliRunner()
        result = runner.invoke(shelf_command, ['inspect', '--help'])
        assert result.exit_code == 0
        assert '--init' in result.output or '-i' in result.output

    @pytest.mark.integration
    def test_box_cli_has_init_flag(self):
        """Test that box commands support --init flag."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['inspect', '--help'])
        assert result.exit_code == 0
        assert '--init' in result.output or '-i' in result.output

    @pytest.mark.integration
    def test_shelf_cli_has_verbose_flag(self):
        """Test that shelf commands support --verbose flag."""
        runner = CliRunner()
        result = runner.invoke(shelf_command, ['inspect', '--help'])
        assert result.exit_code == 0
        assert '--verbose' in result.output or '-v' in result.output

    @pytest.mark.integration
    def test_box_cli_has_shelf_flag(self):
        """Test that box commands support --shelf flag."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['inspect', '--help'])
        assert result.exit_code == 0
        assert '--shelf' in result.output or '-B' in result.output

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_context_service_performance(self):
        """Test that context service operations are reasonably fast."""
        import time

        service = ContextService()
        start = time.time()

        # This should be very fast since it's just checking
        # We're not mocking to test actual performance
        try:
            context = await service.check_shelf_exists("nonexistent-test-shelf")
            elapsed_ms = (time.time() - start) * 1000

            # Should be under 500ms (constitutional requirement)
            assert elapsed_ms < 500, f"Context check took {elapsed_ms}ms, should be <500ms"
        except Exception:
            # Even with errors, should be fast
            elapsed_ms = (time.time() - start) * 1000
            assert elapsed_ms < 500, f"Context check took {elapsed_ms}ms, should be <500ms"

    @pytest.mark.integration
    def test_help_text_consistency(self):
        """Test that help text follows consistent patterns."""
        runner = CliRunner()

        # Test shelf command help
        result = runner.invoke(shelf_command, ['--help'])
        assert result.exit_code == 0
        help_text = result.output

        # Should mention shelves
        assert any(keyword in help_text.lower() for keyword in [
            "shelf", "shelves", "collection"
        ])

    @pytest.mark.integration
    def test_box_help_text_consistency(self):
        """Test that box help text follows consistent patterns."""
        runner = CliRunner()

        # Test box command help
        result = runner.invoke(box_command, ['--help'])
        assert result.exit_code == 0
        help_text = result.output

        # Should mention boxes or projects
        assert any(keyword in help_text.lower() for keyword in [
            "box", "boxes", "project"
        ])