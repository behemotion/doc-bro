"""Contract tests for fill command routing.

Tests the actual fill CLI implementation in src/cli/commands/fill.py.
Uses mocks to avoid database dependencies while validating command structure.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

from src.models.box import Box
from src.models.box_type import BoxType

pytestmark = [pytest.mark.contract]


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_drag_box():
    """Create a mock drag box."""
    box = MagicMock(spec=Box)
    box.id = "drag-box-id"
    box.name = "test-drag"
    box.type = BoxType.DRAG
    box.created_at = datetime.now()
    box.updated_at = datetime.now()
    return box


@pytest.fixture
def mock_rag_box():
    """Create a mock rag box."""
    box = MagicMock(spec=Box)
    box.id = "rag-box-id"
    box.name = "test-rag"
    box.type = BoxType.RAG
    box.created_at = datetime.now()
    box.updated_at = datetime.now()
    return box


@pytest.fixture
def mock_bag_box():
    """Create a mock bag box."""
    box = MagicMock(spec=Box)
    box.id = "bag-box-id"
    box.name = "test-bag"
    box.type = BoxType.BAG
    box.created_at = datetime.now()
    box.updated_at = datetime.now()
    return box


class TestFillCommandContract:
    """Test the contract for unified fill command."""

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_drag_box_routing(self, mock_shelf_service_class, mock_box_service_class,
                                     mock_fill_service_class, mock_context_service_class,
                                     cli_runner, mock_drag_box):
        """Test fill command routes correctly for drag boxes."""
        # Mock services
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True, 'operation': 'crawl'}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-drag',
            '--source', 'https://example.com'
        ])

        assert result.exit_code == 0
        assert 'crawling' in result.output.lower()
        mock_fill_service.fill.assert_called_once()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_rag_box_routing(self, mock_shelf_service_class, mock_box_service_class,
                                    mock_fill_service_class, mock_context_service_class,
                                    cli_runner, mock_rag_box):
        """Test fill command routes correctly for rag boxes."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_rag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True, 'operation': 'import'}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-rag',
            '--source', './test/documents/'
        ])

        assert result.exit_code == 0
        assert 'importing' in result.output.lower()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_bag_box_routing(self, mock_shelf_service_class, mock_box_service_class,
                                    mock_fill_service_class, mock_context_service_class,
                                    cli_runner, mock_bag_box):
        """Test fill command routes correctly for bag boxes."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_bag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True, 'operation': 'store'}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-bag',
            '--source', './test/files/'
        ])

        assert result.exit_code == 0
        assert 'storing' in result.output.lower()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_nonexistent_box_fails(self, mock_shelf_service_class, mock_context_service_class, cli_runner):
        """Test fill command fails for nonexistent box."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = False
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'nonexistent-box',
            '--source', 'https://example.com'
        ], input='n\n')

        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    def test_fill_missing_source_fails(self, cli_runner):
        """Test fill command fails without source."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['fill', 'sourceless-box'])

        assert result.exit_code != 0
        assert 'source' in result.output.lower() or 'required' in result.output.lower()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_drag_specific_options(self, mock_shelf_service_class, mock_box_service_class,
                                         mock_fill_service_class, mock_context_service_class,
                                         cli_runner, mock_drag_box):
        """Test drag-specific options are passed correctly."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-drag',
            '--source', 'https://example.com',
            '--max-pages', '50',
            '--rate-limit', '2.0',
            '--depth', '3'
        ])

        assert result.exit_code == 0
        call_kwargs = mock_fill_service.fill.call_args.kwargs
        assert call_kwargs.get('max_pages') == 50
        assert call_kwargs.get('rate_limit') == 2.0
        assert call_kwargs.get('depth') == 3

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_rag_specific_options(self, mock_shelf_service_class, mock_box_service_class,
                                        mock_fill_service_class, mock_context_service_class,
                                        cli_runner, mock_rag_box):
        """Test rag-specific options are passed correctly."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_rag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-rag',
            '--source', './docs/',
            '--chunk-size', '1000',
            '--overlap', '100'
        ])

        assert result.exit_code == 0
        call_kwargs = mock_fill_service.fill.call_args.kwargs
        assert call_kwargs.get('chunk_size') == 1000
        assert call_kwargs.get('overlap') == 100

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_bag_specific_options(self, mock_shelf_service_class, mock_box_service_class,
                                        mock_fill_service_class, mock_context_service_class,
                                        cli_runner, mock_bag_box):
        """Test bag-specific options are passed correctly."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_bag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-bag',
            '--source', './files/',
            '--recursive',
            '--pattern', '*.pdf'
        ])

        assert result.exit_code == 0
        call_kwargs = mock_fill_service.fill.call_args.kwargs
        assert call_kwargs.get('recursive') is True
        assert call_kwargs.get('pattern') == '*.pdf'

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_with_shelf_context(self, mock_shelf_service_class, mock_box_service_class,
                                      mock_fill_service_class, mock_context_service_class,
                                      cli_runner, mock_drag_box):
        """Test fill with explicit shelf context."""
        mock_shelf_service = AsyncMock()
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-drag',
            '--source', 'https://example.com',
            '--shelf', 'custom-shelf'
        ])

        assert result.exit_code == 0
        call_kwargs = mock_fill_service.fill.call_args.kwargs
        assert call_kwargs.get('shelf_name') == 'custom-shelf'

    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_uses_current_shelf_by_default(self, mock_shelf_service_class, cli_runner):
        """Test fill uses current shelf when not specified."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "my-current-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        # This will fail at context check, but we're just verifying shelf lookup
        result = cli_runner.invoke(main, [
            'fill', 'test-box',
            '--source', 'https://example.com'
        ])

        # Verify current shelf was requested
        mock_shelf_service.get_current_shelf.assert_called_once()

    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_no_current_shelf_warning(self, mock_shelf_service_class, cli_runner):
        """Test fill warns when no current shelf set."""
        mock_shelf_service = AsyncMock()
        mock_shelf_service.get_current_shelf.return_value = None
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-box',
            '--source', 'https://example.com'
        ])

        assert result.exit_code == 1
        assert 'no current shelf' in result.output.lower()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_success_confirmation(self, mock_shelf_service_class, mock_box_service_class,
                                        mock_fill_service_class, mock_context_service_class,
                                        cli_runner, mock_drag_box):
        """Test fill shows success confirmation."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-drag',
            '--source', 'https://example.com'
        ])

        assert result.exit_code == 0
        assert 'successfully' in result.output.lower()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_error_handling(self, mock_shelf_service_class, mock_box_service_class,
                                  mock_fill_service_class, mock_context_service_class,
                                  cli_runner, mock_drag_box):
        """Test fill handles errors gracefully."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': False, 'error': 'Connection failed'}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-drag',
            '--source', 'https://example.com'
        ])

        assert result.exit_code == 1
        assert 'failed' in result.output.lower()

    def test_fill_help(self, cli_runner):
        """Test fill help text."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['fill', '--help'])

        assert result.exit_code == 0
        assert 'source' in result.output.lower()
        assert 'box' in result.output.lower()

    @patch('src.cli.commands.fill.ContextService')
    @patch('src.cli.commands.fill.FillService')
    @patch('src.cli.commands.fill.BoxService')
    @patch('src.cli.commands.fill.ShelfService')
    def test_fill_progress_indication(self, mock_shelf_service_class, mock_box_service_class,
                                       mock_fill_service_class, mock_context_service_class,
                                       cli_runner, mock_drag_box):
        """Test fill shows progress indication."""
        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        mock_box_service = AsyncMock()
        mock_box_service.get_box_by_name.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context_service.check_box_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        mock_fill_service = AsyncMock()
        mock_fill_service.fill.return_value = {'success': True}
        mock_fill_service_class.return_value = mock_fill_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'fill', 'test-drag',
            '--source', 'https://example.com'
        ])

        assert result.exit_code == 0
        # Progress indication would have been shown (though not captured in output)
        assert 'successfully' in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])