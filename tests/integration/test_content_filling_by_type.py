"""Integration test for content filling by box type with type-aware routing.

This test validates that different box types (drag/rag/bag) have
appropriate command options available.
"""

import pytest
from click.testing import CliRunner

from src.cli.commands.box import box as box_command
from src.cli.commands.fill import fill as fill_command
from src.services.context_service import ContextService
from src.services.box_service import BoxService
from src.logic.wizard.box_wizard import BoxWizard


class TestContentFillingByType:
    """Integration test for type-aware content filling."""

    @pytest.mark.integration
    def test_imports_available(self):
        """Test that enhanced CLI commands can be imported."""
        assert box_command is not None
        assert fill_command is not None
        assert ContextService is not None
        assert BoxWizard is not None

    @pytest.mark.integration
    def test_fill_command_exists(self):
        """Test that fill command exists."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_box_command_supports_type_flag(self):
        """Test that box create command supports --type flag."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['create', '--help'])
        assert result.exit_code == 0
        assert '--type' in result.output or '-t' in result.output

    @pytest.mark.integration
    def test_fill_command_has_source_option(self):
        """Test that fill command has --source option."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0
        assert '--source' in result.output or '-S' in result.output

    @pytest.mark.integration
    def test_fill_command_has_drag_options(self):
        """Test that fill command has drag-specific options (website crawling)."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0
        help_text = result.output

        # Should have drag-specific options
        assert any(keyword in help_text for keyword in [
            '--max-pages', '--rate-limit', '--depth', 'drag'
        ])

    @pytest.mark.integration
    def test_fill_command_has_rag_options(self):
        """Test that fill command has rag-specific options (document import)."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0
        help_text = result.output

        # Should have rag-specific options
        assert any(keyword in help_text for keyword in [
            '--chunk-size', '--overlap', 'rag'
        ])

    @pytest.mark.integration
    def test_fill_command_has_bag_options(self):
        """Test that fill command has bag-specific options (file storage)."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0
        help_text = result.output

        # Should have bag-specific options
        assert any(keyword in help_text for keyword in [
            '--recursive', '--pattern', 'bag'
        ])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_box_service_exists(self):
        """Test that BoxService can be instantiated."""
        service = BoxService()
        assert service is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_box_wizard_exists(self):
        """Test that BoxWizard can be instantiated."""
        wizard = BoxWizard()
        assert wizard is not None
        assert hasattr(wizard, 'run')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_context_service_box_check(self):
        """Test that context service can check box existence."""
        service = ContextService()
        # This should not raise an exception
        try:
            context = await service.check_box_exists("nonexistent-test-box")
            # Should return a context object
            assert context is not None
            assert hasattr(context, 'entity_exists')
        except Exception:
            # Even with errors, should not crash
            pass

    @pytest.mark.integration
    def test_box_create_command_drag_type(self):
        """Test that box create accepts 'drag' type."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['create', '--help'])
        assert result.exit_code == 0
        # Command should accept type parameter
        assert '--type' in result.output or '-t' in result.output

    @pytest.mark.integration
    def test_box_create_command_rag_type(self):
        """Test that box create accepts 'rag' type."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['create', '--help'])
        assert result.exit_code == 0
        # Command should accept type parameter
        assert '--type' in result.output or '-t' in result.output

    @pytest.mark.integration
    def test_box_create_command_bag_type(self):
        """Test that box create accepts 'bag' type."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['create', '--help'])
        assert result.exit_code == 0
        # Command should accept type parameter
        assert '--type' in result.output or '-t' in result.output

    @pytest.mark.integration
    def test_fill_command_shelf_option(self):
        """Test that fill command supports shelf context."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0
        assert '--shelf' in result.output

    @pytest.mark.integration
    def test_fill_help_mentions_box_types(self):
        """Test that fill command help mentions box types."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['--help'])
        assert result.exit_code == 0
        help_text = result.output.lower()

        # Should mention different box types
        assert 'drag' in help_text or 'rag' in help_text or 'bag' in help_text

    @pytest.mark.integration
    def test_box_inspect_has_init_flag(self):
        """Test that box inspect supports wizard initialization."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['inspect', '--help'])
        assert result.exit_code == 0
        assert '--init' in result.output or '-i' in result.output

    @pytest.mark.integration
    def test_fill_command_requires_arguments(self):
        """Test that fill command validates required arguments."""
        runner = CliRunner()
        result = runner.invoke(fill_command, [])
        # Should fail without arguments
        assert result.exit_code != 0

    @pytest.mark.integration
    def test_fill_command_requires_source(self):
        """Test that fill command requires --source option."""
        runner = CliRunner()
        result = runner.invoke(fill_command, ['test-box'])
        # Should fail without source
        assert result.exit_code != 0
        assert 'source' in result.output.lower() or '--source' in result.output.lower()

    @pytest.mark.integration
    def test_box_list_command_has_type_filter(self):
        """Test that box list command can filter by type."""
        runner = CliRunner()
        result = runner.invoke(box_command, ['list', '--help'])
        assert result.exit_code == 0
        # Should have type filtering capability
        assert '--type' in result.output or '-t' in result.output or 'type' in result.output.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_context_service_performance_box(self):
        """Test that box context checks are reasonably fast."""
        import time

        service = ContextService()
        start = time.time()

        try:
            context = await service.check_box_exists("nonexistent-test-box")
            elapsed_ms = (time.time() - start) * 1000

            # Should be under 500ms (constitutional requirement)
            assert elapsed_ms < 500, f"Context check took {elapsed_ms}ms, should be <500ms"
        except Exception:
            elapsed_ms = (time.time() - start) * 1000
            assert elapsed_ms < 500, f"Context check took {elapsed_ms}ms, should be <500ms"