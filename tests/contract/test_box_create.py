"""Contract tests for box create command.

Tests the actual box CLI implementation in src/cli/commands/box.py.
Uses mocks to avoid database dependencies while validating command structure.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

from src.models.box import Box, BoxExistsError, BoxValidationError, BoxNotFoundError
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
    box.id = "test-box-id"
    box.name = "test-drag-box"
    box.type = BoxType.DRAG
    box.created_at = datetime.now()
    box.updated_at = datetime.now()
    box.get_type_description.return_value = "Website crawler"
    return box


@pytest.fixture
def mock_rag_box():
    """Create a mock rag box."""
    box = MagicMock(spec=Box)
    box.id = "test-box-id"
    box.name = "test-rag-box"
    box.type = BoxType.RAG
    box.created_at = datetime.now()
    box.updated_at = datetime.now()
    box.get_type_description.return_value = "Document storage"
    return box


@pytest.fixture
def mock_bag_box():
    """Create a mock bag box."""
    box = MagicMock(spec=Box)
    box.id = "test-box-id"
    box.name = "test-bag-box"
    box.type = BoxType.BAG
    box.created_at = datetime.now()
    box.updated_at = datetime.now()
    box.get_type_description.return_value = "File storage"
    return box


class TestBoxCreateContract:
    """Test the contract for box create command."""

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_drag_type_success(self, mock_box_service_class, mock_shelf_service_class, cli_runner, mock_drag_box):
        """Test creating a drag (crawling) box."""
        # Mock services
        mock_box_service = AsyncMock()
        mock_box_service.create_box.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'test-drag-box',
            '--type', 'drag'
        ])

        assert result.exit_code == 0
        assert 'created' in result.output.lower() and 'drag' in result.output.lower()
        mock_box_service.create_box.assert_called_once()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_rag_type_success(self, mock_box_service_class, mock_shelf_service_class, cli_runner, mock_rag_box):
        """Test creating a rag (document) box."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.return_value = mock_rag_box
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'test-rag-box',
            '--type', 'rag'
        ])

        assert result.exit_code == 0
        assert 'created' in result.output.lower() and 'rag' in result.output.lower()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_bag_type_success(self, mock_box_service_class, mock_shelf_service_class, cli_runner, mock_bag_box):
        """Test creating a bag (storage) box."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.return_value = mock_bag_box
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'test-bag-box',
            '--type', 'bag'
        ])

        assert result.exit_code == 0
        assert 'created' in result.output.lower() and 'bag' in result.output.lower()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_with_shelf(self, mock_box_service_class, mock_shelf_service_class, cli_runner, mock_rag_box):
        """Test creating box and adding to specific shelf."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.return_value = mock_rag_box
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'shelf-box',
            '--type', 'rag',
            '--shelf', 'test-target-shelf'
        ])

        assert result.exit_code == 0
        call_args = mock_box_service.create_box.call_args
        assert call_args.kwargs.get('shelf_name') == 'test-target-shelf'

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_with_description(self, mock_box_service_class, mock_shelf_service_class, cli_runner, mock_bag_box):
        """Test creating box with description."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.return_value = mock_bag_box
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'described-box',
            '--type', 'bag',
            '--box-description', 'A test box for storage'
        ])

        assert result.exit_code == 0
        call_args = mock_box_service.create_box.call_args
        assert call_args.kwargs.get('description') == 'A test box for storage'

    def test_box_create_missing_type_fails(self, cli_runner):
        """Test that missing type parameter fails."""
        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'no-type-box'
        ])

        assert result.exit_code != 0
        assert 'type' in result.output.lower() or 'required' in result.output.lower()

    def test_box_create_invalid_type_fails(self, cli_runner):
        """Test that invalid type fails."""
        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'invalid-type-box',
            '--type', 'invalid'
        ])

        assert result.exit_code != 0
        assert 'invalid' in result.output.lower() or 'choice' in result.output.lower()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_duplicate_name_fails(self, mock_box_service_class, mock_shelf_service_class, cli_runner):
        """Test that duplicate box name fails."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.side_effect = BoxExistsError("Box already exists")
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'duplicate',
            '--type', 'drag'
        ])

        assert result.exit_code == 1
        assert 'error' in result.output.lower() or 'exists' in result.output.lower()

    def test_box_create_empty_name_fails(self, cli_runner):
        """Test that empty name fails."""
        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', '',
            '--type', 'drag'
        ])

        assert result.exit_code != 0

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_reserved_name_fails(self, mock_box_service_class, mock_shelf_service_class, cli_runner):
        """Test that reserved names fail."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.side_effect = BoxValidationError("Reserved name")
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'system',
            '--type', 'drag'
        ])

        assert result.exit_code == 1
        assert 'invalid' in result.output.lower() or 'error' in result.output.lower()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_with_nonexistent_shelf_fails(self, mock_box_service_class, mock_shelf_service_class, cli_runner):
        """Test creating box with non-existent shelf fails."""
        mock_box_service = AsyncMock()
        from src.services.database import DatabaseError
        mock_box_service.create_box.side_effect = DatabaseError("Shelf not found")
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'orphan-box',
            '--type', 'drag',
            '--shelf', 'nonexistent'
        ])

        assert result.exit_code == 1
        assert 'not found' in result.output.lower() or 'error' in result.output.lower()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_valid_special_characters(self, mock_box_service_class, mock_shelf_service_class, cli_runner, mock_drag_box):
        """Test that valid special characters are accepted."""
        mock_box_service = AsyncMock()
        mock_drag_box.name = "my-test_box"
        mock_box_service.create_box.return_value = mock_drag_box
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'my-test_box',
            '--type', 'drag'
        ])

        assert result.exit_code == 0

    def test_box_create_type_choices_validation(self, cli_runner):
        """Test that type choices are validated."""
        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'test-box',
            '--type', 'invalid-type'
        ])

        assert result.exit_code != 0
        # Should show available choices
        assert 'drag' in result.output or 'rag' in result.output or 'bag' in result.output

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_shows_globally_unique_constraint(self, mock_box_service_class, mock_shelf_service_class, cli_runner):
        """Test that global uniqueness is enforced."""
        mock_box_service = AsyncMock()
        mock_box_service.create_box.side_effect = BoxExistsError("Box 'test-box' already exists globally")
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "shelf1"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', 'test-box',
            '--type', 'drag',
            '--shelf', 'shelf2'
        ])

        assert result.exit_code == 1
        assert 'exists' in result.output.lower()

    def test_box_create_help(self, cli_runner):
        """Test box create help text."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['box', 'create', '--help'])

        assert result.exit_code == 0
        assert 'type' in result.output.lower()
        assert 'drag' in result.output or 'rag' in result.output
        assert 'shelf' in result.output.lower()

    @patch('src.cli.commands.box.ShelfService')
    @patch('src.cli.commands.box.BoxService')
    def test_box_create_long_name_limit(self, mock_box_service_class, mock_shelf_service_class, cli_runner):
        """Test that long names are handled."""
        long_name = "a" * 150
        mock_box_service = AsyncMock()
        mock_box_service.create_box.side_effect = BoxValidationError("Name too long")
        mock_box_service_class.return_value = mock_box_service

        mock_shelf_service = AsyncMock()
        mock_shelf = MagicMock()
        mock_shelf.name = "default-shelf"
        mock_shelf_service.get_current_shelf.return_value = mock_shelf
        mock_shelf_service_class.return_value = mock_shelf_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'box', 'create', long_name,
            '--type', 'drag'
        ])

        assert result.exit_code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])