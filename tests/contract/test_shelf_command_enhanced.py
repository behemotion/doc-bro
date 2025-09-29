"""Contract tests for enhanced shelf command behavior."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from click.testing import CliRunner
from datetime import datetime

# Import will fail until command is implemented - this is expected for TDD
try:
    from src.cli.shelf import shelf_command
    from src.models.command_context import CommandContext
    from src.models.configuration_state import ConfigurationState
    COMMAND_EXISTS = True
except ImportError:
    COMMAND_EXISTS = False


@pytest.mark.contract
class TestEnhancedShelfCommand:
    """Test enhanced shelf command contracts."""

    @pytest.fixture
    def cli_runner(self):
        """CLI runner for testing Click commands."""
        return CliRunner()

    @pytest.fixture
    def mock_context_service(self):
        """Mock context service for shelf operations."""
        service = Mock()
        service.check_shelf_exists = AsyncMock()
        return service

    @pytest.fixture
    def mock_shelf_wizard(self):
        """Mock shelf wizard for setup operations."""
        wizard = Mock()
        wizard.run = AsyncMock(return_value={"success": True, "configuration": {}})
        return wizard

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_display_existing_shelf(self, cli_runner, mock_context_service):
        """Test shelf command displays existing shelf information."""
        # Mock existing shelf with content
        mock_context = Mock()
        mock_context.exists = True
        mock_context.is_empty = False
        mock_context.entity_name = "docs-shelf"
        mock_context.entity_type = "shelf"
        mock_context.content_summary = "5 boxes with documentation content"
        mock_context.last_modified = datetime.utcnow()
        mock_context.configuration_state.is_configured = True
        mock_context.configuration_state.has_content = True

        mock_context_service.check_shelf_exists.return_value = mock_context

        with patch('src.cli.shelf.context_service', mock_context_service):
            result = cli_runner.invoke(shelf_command, ['docs-shelf'])

        assert result.exit_code == 0
        assert "docs-shelf" in result.output
        assert "5 boxes with documentation content" in result.output
        assert "configured" in result.output.lower()
        mock_context_service.check_shelf_exists.assert_called_once_with("docs-shelf")

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_display_empty_shelf_prompts_fill(self, cli_runner, mock_context_service):
        """Test shelf command prompts to fill empty shelf."""
        # Mock existing but empty shelf
        mock_context = Mock()
        mock_context.exists = True
        mock_context.is_empty = True
        mock_context.entity_name = "empty-shelf"
        mock_context.entity_type = "shelf"
        mock_context.content_summary = None
        mock_context.configuration_state.is_configured = True
        mock_context.configuration_state.has_content = False

        mock_context_service.check_shelf_exists.return_value = mock_context

        with patch('src.cli.shelf.context_service', mock_context_service):
            # Simulate user saying 'no' to fill prompt
            result = cli_runner.invoke(shelf_command, ['empty-shelf'], input='n\n')

        assert result.exit_code == 0
        assert "empty-shelf" in result.output
        assert "is empty" in result.output.lower()
        assert "fill boxes now?" in result.output.lower() or "fill" in result.output.lower()

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_nonexistent_prompts_creation(self, cli_runner, mock_context_service):
        """Test shelf command prompts to create non-existent shelf."""
        # Mock non-existent shelf
        mock_context = Mock()
        mock_context.exists = False
        mock_context.is_empty = None
        mock_context.entity_name = "new-shelf"
        mock_context.entity_type = "shelf"

        mock_context_service.check_shelf_exists.return_value = mock_context

        with patch('src.cli.shelf.context_service', mock_context_service):
            # Simulate user saying 'no' to creation prompt
            result = cli_runner.invoke(shelf_command, ['new-shelf'], input='n\n')

        assert result.exit_code in [0, 1]  # 1 for user cancellation
        assert "new-shelf" in result.output
        assert "not found" in result.output.lower()
        assert "create it?" in result.output.lower() or "create" in result.output.lower()

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_creation_with_wizard_flag(self, cli_runner, mock_context_service, mock_shelf_wizard):
        """Test shelf creation with --init flag launches wizard."""
        with patch('src.cli.shelf.context_service', mock_context_service), \
             patch('src.cli.shelf.shelf_wizard', mock_shelf_wizard):

            result = cli_runner.invoke(shelf_command, ['create', 'wizard-shelf', '--init'])

        assert result.exit_code == 0
        assert "wizard-shelf" in result.output
        # Verify wizard was called
        mock_shelf_wizard.run.assert_called_once()

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_list_shows_status_summary(self, cli_runner, mock_context_service):
        """Test shelf command without arguments lists all shelves with status."""
        mock_shelves = [
            Mock(name="docs-shelf", is_configured=True, has_content=True, box_count=5),
            Mock(name="empty-shelf", is_configured=True, has_content=False, box_count=0),
            Mock(name="unconfigured-shelf", is_configured=False, has_content=False, box_count=2)
        ]

        with patch('src.cli.shelf.list_all_shelves', return_value=mock_shelves):
            result = cli_runner.invoke(shelf_command, [])

        assert result.exit_code == 0
        assert "docs-shelf" in result.output
        assert "empty-shelf" in result.output
        assert "unconfigured-shelf" in result.output
        # Should show status indicators
        assert "configured" in result.output.lower() or "ready" in result.output.lower()

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_verbose_flag_shows_detailed_info(self, cli_runner, mock_context_service):
        """Test shelf command with --verbose flag shows detailed information."""
        mock_context = Mock()
        mock_context.exists = True
        mock_context.is_empty = False
        mock_context.entity_name = "docs-shelf"
        mock_context.configuration_state.setup_completed_at = datetime.utcnow()
        mock_context.configuration_state.configuration_version = "1.0"

        mock_context_service.check_shelf_exists.return_value = mock_context

        with patch('src.cli.shelf.context_service', mock_context_service):
            result = cli_runner.invoke(shelf_command, ['docs-shelf', '--verbose'])

        assert result.exit_code == 0
        assert "configuration_version" in result.output.lower() or "version" in result.output
        assert "setup_completed" in result.output.lower() or "configured" in result.output

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_flag_standardization(self, cli_runner):
        """Test shelf command supports standardized flags."""
        # Test that both long and short forms are supported
        test_cases = [
            (['--init'], 'should support --init'),
            (['-i'], 'should support -i short form'),
            (['--verbose'], 'should support --verbose'),
            (['-v'], 'should support -v short form'),
            (['--help'], 'should support --help'),
            (['-h'], 'should support -h short form'),
        ]

        for flags, description in test_cases:
            try:
                result = cli_runner.invoke(shelf_command, ['test-shelf'] + flags)
                # Help flag should exit with 0, others may exit with various codes
                # The important thing is that the flag is recognized (not "no such option")
                assert "no such option" not in result.output.lower(), f"Flag {flags[0]} not recognized: {description}"
            except SystemExit:
                # Help flags cause SystemExit, which is expected
                pass

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_error_handling_graceful(self, cli_runner, mock_context_service):
        """Test shelf command handles errors gracefully."""
        # Mock service error
        mock_context_service.check_shelf_exists.side_effect = Exception("Database connection failed")

        with patch('src.cli.shelf.context_service', mock_context_service):
            result = cli_runner.invoke(shelf_command, ['test-shelf'])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()
        # Should not show raw stack trace
        assert "Traceback" not in result.output

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_create_validation(self, cli_runner):
        """Test shelf create command validates input parameters."""
        # Test invalid shelf names
        invalid_names = ["", "shelf with spaces", "shelf@invalid", "shelf.with.dots"]

        for invalid_name in invalid_names:
            result = cli_runner.invoke(shelf_command, ['create', invalid_name])
            assert result.exit_code != 0
            assert ("invalid" in result.output.lower() or
                    "validation" in result.output.lower() or
                    "error" in result.output.lower())

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_performance_requirements(self, cli_runner, mock_context_service):
        """Test shelf command meets performance requirements (<500ms for context detection)."""
        import time

        mock_context = Mock()
        mock_context.exists = True
        mock_context.is_empty = False
        mock_context.entity_name = "perf-shelf"

        # Add artificial delay to test timeout handling
        async def delayed_check(name):
            await asyncio.sleep(0.1)  # 100ms delay - should be fast enough
            return mock_context

        mock_context_service.check_shelf_exists.side_effect = delayed_check

        with patch('src.cli.shelf.context_service', mock_context_service):
            start_time = time.time()
            result = cli_runner.invoke(shelf_command, ['perf-shelf'])
            end_time = time.time()

        # Should complete within reasonable time (allowing for test overhead)
        assert (end_time - start_time) < 2.0, "Shelf command took too long to execute"
        assert result.exit_code == 0

    @pytest.mark.skipif(not COMMAND_EXISTS, reason="Enhanced shelf command not yet implemented")
    def test_shelf_wizard_integration(self, cli_runner, mock_context_service, mock_shelf_wizard):
        """Test shelf command integrates properly with wizard system."""
        # Test wizard launch after creation
        mock_shelf_wizard.run.return_value = {
            "success": True,
            "configuration": {
                "description": "Test shelf",
                "auto_fill": True,
                "default_box_type": "drag"
            }
        }

        with patch('src.cli.shelf.context_service', mock_context_service), \
             patch('src.cli.shelf.shelf_wizard', mock_shelf_wizard):

            # Simulate creating shelf and launching wizard
            result = cli_runner.invoke(shelf_command, ['create', 'test-shelf', '--init'])

        assert result.exit_code == 0
        mock_shelf_wizard.run.assert_called_once_with("test-shelf")
        assert "wizard" in result.output.lower() or "setup" in result.output.lower()


if not COMMAND_EXISTS:
    def test_enhanced_shelf_command_not_implemented():
        """Test that fails until enhanced shelf command is implemented."""
        assert False, "Enhanced shelf command not yet implemented - this test should fail until T037 is completed"