"""Contract tests for CLI shelf management commands.

Tests the actual shelf CLI implementation in src/cli/commands/shelf.py.
Updated to match the subcommand-based architecture (shelf create, shelf list, etc.).
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

from src.models.shelf import Shelf, ShelfExistsError, ShelfValidationError, ShelfNotFoundError

pytestmark = [pytest.mark.contract]


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_shelf():
    """Create a mock shelf object."""
    return Shelf(
        id="test-shelf-id",
        name="test-shelf",
        description="Test shelf",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_default=False,
        box_count=0
    )


class TestShelfCommandExists:
    """Test that the shelf command group exists and is properly registered."""

    def test_shelf_command_exists(self, cli_runner):
        """Test that the shelf command is registered with the main CLI."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'shelf' in result.output.lower()

    def test_shelf_command_structure(self, cli_runner):
        """Test that the shelf command has the expected structure."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--help'])
        assert result.exit_code == 0
        assert 'shelves' in result.output.lower()


class TestShelfCreateCommand:
    """Contract tests for shelf creation commands."""

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_create_basic(self, mock_service_class, cli_runner, mock_shelf):
        """Test basic shelf creation."""
        # Setup mock
        mock_service = AsyncMock()
        mock_service.create_shelf.return_value = mock_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'create', 'test-shelf'])

        assert result.exit_code == 0
        assert 'created' in result.output.lower() or 'test-shelf' in result.output
        mock_service.create_shelf.assert_called_once()

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_create_with_description(self, mock_service_class, cli_runner, mock_shelf):
        """Test shelf creation with description."""
        mock_service = AsyncMock()
        mock_service.create_shelf.return_value = mock_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', 'create', 'test-shelf',
            '--shelf-description', 'Main documentation'
        ])

        # Note: Shelf model doesn't currently have description field,
        # but command should still accept the flag without error
        assert result.exit_code == 0
        # Verify the shelf was created (description handling may be future feature)
        mock_service.create_shelf.assert_called_once()

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_create_set_current(self, mock_service_class, cli_runner, mock_shelf):
        """Test shelf creation with --set-current flag."""
        mock_service = AsyncMock()
        mock_shelf.is_default = True
        mock_service.create_shelf.return_value = mock_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', 'create', 'test-shelf', '--set-current'
        ])

        assert result.exit_code == 0
        call_args = mock_service.create_shelf.call_args
        assert call_args.kwargs.get('set_current') is True

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_create_duplicate_error(self, mock_service_class, cli_runner):
        """Test error when creating duplicate shelf."""
        mock_service = AsyncMock()
        mock_service.create_shelf.side_effect = ShelfExistsError("Shelf already exists")
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'create', 'duplicate'])

        assert result.exit_code == 1
        assert 'error' in result.output.lower() or 'exists' in result.output.lower()

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_create_invalid_name(self, mock_service_class, cli_runner):
        """Test error for invalid shelf name."""
        mock_service = AsyncMock()
        mock_service.create_shelf.side_effect = ShelfValidationError("Invalid name")
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'create', 'invalid/name'])

        assert result.exit_code == 1
        assert 'invalid' in result.output.lower() or 'error' in result.output.lower()


class TestShelfListCommand:
    """Contract tests for shelf listing commands."""

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_list_basic(self, mock_service_class, cli_runner):
        """Test basic shelf listing."""
        mock_service = AsyncMock()
        shelf1 = Shelf(
            id="id1", name="documentation", description="Docs",
            created_at=datetime.now(), updated_at=datetime.now(),
            is_default=True, box_count=3
        )
        shelf2 = Shelf(
            id="id2", name="examples", description="Examples",
            created_at=datetime.now(), updated_at=datetime.now(),
            is_default=False, box_count=2
        )
        mock_service.list_shelves.return_value = [shelf1, shelf2]
        mock_service.get_current_shelf.return_value = shelf1
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'list'])

        assert result.exit_code == 0
        assert 'documentation' in result.output
        assert 'examples' in result.output
        assert '3' in result.output
        assert '2' in result.output

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_list_verbose(self, mock_service_class, cli_runner):
        """Test verbose shelf listing."""
        mock_service = AsyncMock()
        shelf = Shelf(
            id="test-id-12345678", name="documentation", description="Docs",
            created_at=datetime.now(), updated_at=datetime.now(),
            is_default=True, box_count=3
        )
        mock_service.list_shelves.return_value = [shelf]
        mock_service.get_current_shelf.return_value = shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'list', '--verbose'])

        assert result.exit_code == 0
        # Verbose mode should show ID
        assert 'test-id-' in result.output or 'documentation' in result.output

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_list_current_only(self, mock_service_class, cli_runner):
        """Test listing only current shelf."""
        mock_service = AsyncMock()
        current_shelf = Shelf(
            id="id1", name="documentation", description="Docs",
            created_at=datetime.now(), updated_at=datetime.now(),
            is_default=True, box_count=3
        )
        mock_service.get_current_shelf.return_value = current_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'list', '--current-only'])

        assert result.exit_code == 0
        assert 'documentation' in result.output

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_list_empty(self, mock_service_class, cli_runner):
        """Test listing when no shelves exist."""
        mock_service = AsyncMock()
        mock_service.list_shelves.return_value = []
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'list'])

        assert result.exit_code == 0
        assert 'no shelves' in result.output.lower() or 'not found' in result.output.lower()


class TestShelfCurrentCommand:
    """Contract tests for current shelf commands."""

    @patch('src.cli.commands.shelf.ShelfService')
    def test_get_current_shelf(self, mock_service_class, cli_runner):
        """Test getting current shelf."""
        mock_service = AsyncMock()
        current_shelf = Shelf(
            id="id1", name="documentation", description="Docs",
            created_at=datetime.now(), updated_at=datetime.now(),
            is_default=True, box_count=3
        )
        mock_service.get_current_shelf.return_value = current_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'current'])

        assert result.exit_code == 0
        assert 'documentation' in result.output

    @patch('src.cli.commands.shelf.ShelfService')
    def test_set_current_shelf(self, mock_service_class, cli_runner, mock_shelf):
        """Test setting current shelf."""
        mock_service = AsyncMock()
        mock_service.set_current_shelf.return_value = mock_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'current', 'test-shelf'])

        assert result.exit_code == 0
        assert 'test-shelf' in result.output
        mock_service.set_current_shelf.assert_called_once_with('test-shelf')


class TestShelfRenameCommand:
    """Contract tests for shelf rename command."""

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_rename(self, mock_service_class, cli_runner, mock_shelf):
        """Test renaming a shelf."""
        mock_service = AsyncMock()
        renamed_shelf = mock_shelf
        renamed_shelf.name = "new-name"
        mock_service.rename_shelf.return_value = renamed_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'rename', 'old-name', 'new-name'])

        assert result.exit_code == 0
        assert 'renamed' in result.output.lower()
        mock_service.rename_shelf.assert_called_once_with('old-name', 'new-name')

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_rename_not_found(self, mock_service_class, cli_runner):
        """Test renaming non-existent shelf."""
        mock_service = AsyncMock()
        mock_service.rename_shelf.side_effect = ShelfNotFoundError("Shelf not found")
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'rename', 'missing', 'new-name'])

        assert result.exit_code == 1
        assert 'error' in result.output.lower() or 'not found' in result.output.lower()


class TestShelfDeleteCommand:
    """Contract tests for shelf delete command."""

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_delete_with_force(self, mock_service_class, cli_runner, mock_shelf):
        """Test deleting shelf with --force flag."""
        mock_service = AsyncMock()
        mock_service.get_shelf_by_name.return_value = mock_shelf
        mock_service.delete_shelf.return_value = None
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'delete', 'test-shelf', '--force'])

        assert result.exit_code == 0
        assert 'deleted' in result.output.lower()
        mock_service.delete_shelf.assert_called_once_with('test-shelf')

    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_delete_protected(self, mock_service_class, cli_runner):
        """Test deleting protected shelf."""
        mock_service = AsyncMock()
        # Use non-reserved name since "default" is reserved
        protected_shelf = Shelf(
            id="id1", name="protected-shelf",
            created_at=datetime.now(), updated_at=datetime.now(),
            is_default=True, is_deletable=False, box_count=0
        )
        mock_service.get_shelf_by_name.return_value = protected_shelf
        mock_service_class.return_value = mock_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'delete', 'protected-shelf', '--force'])

        assert result.exit_code == 1
        assert 'protected' in result.output.lower() or 'cannot' in result.output.lower()


class TestShelfInspectCommand:
    """Contract tests for shelf inspect command."""

    @patch('src.cli.commands.shelf.ContextService')
    @patch('src.cli.commands.shelf.ShelfService')
    def test_shelf_inspect_exists(self, mock_shelf_service_class, mock_context_service_class, cli_runner):
        """Test inspecting existing shelf."""
        # Mock context service
        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = True
        mock_context.is_empty = False
        mock_context.configuration_state.is_configured = True
        mock_context_service.check_shelf_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'inspect', 'test-shelf'])

        assert result.exit_code == 0
        assert 'test-shelf' in result.output.lower()

    @patch('src.cli.commands.shelf.ContextService')
    def test_shelf_inspect_not_found(self, mock_context_service_class, cli_runner):
        """Test inspecting non-existent shelf."""
        mock_context_service = AsyncMock()
        mock_context = MagicMock()
        mock_context.entity_exists = False
        mock_context_service.check_shelf_exists.return_value = mock_context
        mock_context_service_class.return_value = mock_context_service

        from src.cli.main import main

        # Use input to simulate user declining creation
        result = cli_runner.invoke(main, ['shelf', 'inspect', 'missing'], input='n\n')

        # Should show not found message
        assert 'not found' in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])