"""Contract tests for CLI shelf management commands.

Tests the CLI command contracts defined in specs/017-projects-as-collections/contracts/cli-shelf-commands.md.
These tests will initially FAIL as the shelf command implementation does not exist yet.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

pytestmark = [pytest.mark.contract, pytest.mark.async_test]


@pytest.fixture
def mock_shelf_service():
    """Mock shelf service for CLI tests."""
    with patch('src.services.shelf_service.ShelfService') as mock:
        service_instance = AsyncMock()
        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_basket_service():
    """Mock basket service for CLI tests."""
    with patch('src.services.basket_service.BasketService') as mock:
        service_instance = AsyncMock()
        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_context_service():
    """Mock current shelf context service."""
    with patch('src.services.current_shelf_context_service.CurrentShelfContextService') as mock:
        service_instance = AsyncMock()
        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


class TestShelfCommandExists:
    """Test that the shelf command group exists and is properly registered."""

    def test_shelf_command_exists(self, cli_runner):
        """Test that the shelf command is registered with the main CLI."""
        # This will fail until the shelf command is implemented
        from src.cli.main import main

        result = cli_runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'shelf' in result.output

    def test_shelf_command_structure(self, cli_runner):
        """Test that the shelf command has the expected structure."""
        # This will fail until the shelf command is implemented
        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--help'])
        assert result.exit_code == 0
        assert 'Manage documentation shelves' in result.output


class TestShelfCreateCommand:
    """Contract tests for shelf creation commands."""

    def test_shelf_create_basic(self, cli_runner, mock_shelf_service):
        """Test basic shelf creation with --new flag."""
        # Mock successful shelf creation
        mock_shelf_service.create_shelf.return_value = {
            'id': 'test-shelf-id',
            'name': 'test-shelf',
            'created_at': '2025-09-29T10:30:15Z',
            'is_current': False,
            'baskets': []
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--new', 'test-shelf'])

        # Should succeed when implementation exists
        assert result.exit_code == 0
        assert "Shelf 'test-shelf' created successfully" in result.output
        mock_shelf_service.create_shelf.assert_called_once()

    def test_shelf_create_with_description(self, cli_runner, mock_shelf_service):
        """Test shelf creation with description."""
        mock_shelf_service.create_shelf.return_value = {
            'id': 'docs-shelf-id',
            'name': 'documentation',
            'created_at': '2025-09-29T10:30:15Z',
            'is_current': False,
            'baskets': []
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', '--new', 'documentation',
            '--description', 'Main documentation collection'
        ])

        assert result.exit_code == 0
        assert "Shelf 'documentation' created successfully" in result.output

    def test_shelf_create_set_current(self, cli_runner, mock_shelf_service, mock_context_service):
        """Test shelf creation with --set-current flag."""
        mock_shelf_service.create_shelf.return_value = {
            'id': 'current-shelf-id',
            'name': 'current-docs',
            'created_at': '2025-09-29T10:30:15Z',
            'is_current': True,
            'baskets': []
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', '--new', 'current-docs', '--set-current'
        ])

        assert result.exit_code == 0
        assert "Status: Current shelf" in result.output
        mock_context_service.set_current_shelf.assert_called_once_with('current-docs')

    def test_shelf_create_force_overwrite(self, cli_runner, mock_shelf_service):
        """Test shelf creation with --force to overwrite existing."""
        mock_shelf_service.create_shelf.return_value = {
            'id': 'overwritten-shelf-id',
            'name': 'existing-shelf',
            'created_at': '2025-09-29T10:30:15Z',
            'is_current': False,
            'baskets': []
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', '--new', 'existing-shelf', '--force'
        ])

        assert result.exit_code == 0

    def test_shelf_create_duplicate_error(self, cli_runner, mock_shelf_service):
        """Test error when creating duplicate shelf without --force."""
        from src.services.shelf_service import ShelfExistsError
        mock_shelf_service.create_shelf.side_effect = ShelfExistsError("Shelf 'duplicate' already exists")

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--new', 'duplicate'])

        assert result.exit_code != 0
        assert "already exists" in result.output
        assert "Use --force to overwrite" in result.output

    def test_shelf_create_invalid_name(self, cli_runner, mock_shelf_service):
        """Test error for invalid shelf name."""
        from src.services.shelf_service import InvalidShelfNameError
        mock_shelf_service.create_shelf.side_effect = InvalidShelfNameError("Invalid shelf name format")

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--new', 'invalid/name'])

        assert result.exit_code != 0
        assert "Invalid shelf name" in result.output


class TestShelfListCommand:
    """Contract tests for shelf listing commands."""

    def test_shelf_list_basic(self, cli_runner, mock_shelf_service):
        """Test basic shelf listing."""
        mock_shelf_service.list_shelfs.return_value = [
            {
                'name': 'documentation',
                'basket_count': 3,
                'is_current': True,
                'created_at': '2025-09-28T10:00:00Z'
            },
            {
                'name': 'examples',
                'basket_count': 2,
                'is_current': False,
                'created_at': '2025-09-29T15:00:00Z'
            }
        ]

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--list'])

        assert result.exit_code == 0
        assert 'documentation' in result.output
        assert 'examples' in result.output
        assert '3' in result.output  # basket count
        assert '2' in result.output  # basket count

    def test_shelf_list_verbose(self, cli_runner, mock_shelf_service):
        """Test verbose shelf listing."""
        mock_shelf_service.list_shelfs.return_value = [
            {
                'name': 'documentation',
                'basket_count': 3,
                'is_current': True,
                'created_at': '2025-09-28T10:00:00Z',
                'total_files': 65,
                'total_size_bytes': 2458634
            }
        ]

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--list', '--verbose'])

        assert result.exit_code == 0
        assert 'Total files: 65' in result.output or '65' in result.output

    def test_shelf_list_current_only(self, cli_runner, mock_shelf_service):
        """Test listing only current shelf."""
        mock_shelf_service.list_shelfs.return_value = [
            {
                'name': 'documentation',
                'basket_count': 3,
                'is_current': True,
                'created_at': '2025-09-28T10:00:00Z'
            }
        ]

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--list', '--current-only'])

        assert result.exit_code == 0
        assert 'documentation' in result.output

    def test_shelf_list_empty(self, cli_runner, mock_shelf_service):
        """Test listing when no shelfs exist."""
        mock_shelf_service.list_shelfs.return_value = []

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--list'])

        assert result.exit_code == 0
        assert 'No shelfs found' in result.output


class TestShelfShowCommand:
    """Contract tests for shelf show/details commands."""

    def test_shelf_show_implicit(self, cli_runner, mock_shelf_service):
        """Test showing shelf details with implicit syntax (shelf name only)."""
        mock_shelf_service.get_shelf_by_name.return_value = {
            'name': 'documentation',
            'created_at': '2025-09-28T10:00:00Z',
            'updated_at': '2025-09-29T14:30:00Z',
            'is_current': True,
            'baskets': [
                {'name': 'api-docs', 'type': 'crawling', 'status': 'ready', 'files': 45},
                {'name': 'user-guides', 'type': 'data', 'status': 'active', 'files': 12}
            ]
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'documentation'])

        assert result.exit_code == 0
        assert 'Shelf: documentation' in result.output
        assert 'api-docs' in result.output
        assert 'user-guides' in result.output

    def test_shelf_show_explicit(self, cli_runner, mock_shelf_service):
        """Test showing shelf details with explicit --show flag."""
        mock_shelf_service.get_shelf_by_name.return_value = {
            'name': 'examples',
            'created_at': '2025-09-29T15:00:00Z',
            'updated_at': '2025-09-29T15:30:00Z',
            'is_current': False,
            'baskets': []
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--show', 'examples'])

        assert result.exit_code == 0
        assert 'Shelf: examples' in result.output

    def test_shelf_show_detailed(self, cli_runner, mock_shelf_service):
        """Test detailed shelf view."""
        mock_shelf_service.get_shelf_by_name.return_value = {
            'name': 'documentation',
            'created_at': '2025-09-28T10:00:00Z',
            'updated_at': '2025-09-29T14:30:00Z',
            'is_current': True,
            'baskets': [
                {
                    'name': 'api-docs',
                    'type': 'crawling',
                    'status': 'ready',
                    'files': 45,
                    'size_bytes': 1834567,
                    'last_updated': '2025-09-29T12:15:00Z'
                }
            ]
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--show', 'documentation', '--detailed'])

        assert result.exit_code == 0
        assert '1834567' in result.output or '1.8' in result.output  # Size information

    def test_shelf_show_not_found(self, cli_runner, mock_shelf_service):
        """Test error when shelf doesn't exist."""
        from src.services.shelf_service import ShelfNotFoundError
        mock_shelf_service.get_shelf_by_name.side_effect = ShelfNotFoundError("Shelf 'nonexistent' not found")

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'nonexistent'])

        assert result.exit_code != 0
        assert "not found" in result.output


class TestBasketManagementCommands:
    """Contract tests for basket management within shelfs."""

    def test_add_basket_to_shelf(self, cli_runner, mock_basket_service, mock_context_service):
        """Test adding basket to specific shelf."""
        mock_basket_service.create_basket.return_value = {
            'id': 'new-basket-id',
            'name': 'api-docs',
            'shelf_id': 'docs-shelf-id',
            'type': 'crawling',
            'status': 'created'
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', 'documentation', '--basket', 'api-docs', '--type', 'crawling'
        ])

        assert result.exit_code == 0
        assert "Basket 'api-docs' added to shelf 'documentation'" in result.output

    def test_add_basket_short_form(self, cli_runner, mock_basket_service):
        """Test adding basket with short form flags."""
        mock_basket_service.create_basket.return_value = {
            'id': 'guides-basket-id',
            'name': 'user-guides',
            'shelf_id': 'docs-shelf-id',
            'type': 'data',
            'status': 'created'
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', 'documentation', '-b', 'user-guides', '--type', 'data'
        ])

        assert result.exit_code == 0

    def test_add_basket_global_short_form(self, cli_runner, mock_basket_service, mock_context_service):
        """Test adding basket with global short form to current shelf."""
        # Mock current shelf context
        mock_context_service.get_current_shelf.return_value = 'documentation'

        mock_basket_service.create_basket.return_value = {
            'id': 'tutorials-basket-id',
            'name': 'tutorials',
            'shelf_id': 'docs-shelf-id',
            'type': 'storage',
            'status': 'created'
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['-s', 'documentation', '-b', 'tutorials', '--type', 'storage'])

        assert result.exit_code == 0

    def test_add_basket_default_type(self, cli_runner, mock_basket_service):
        """Test adding basket with default type (data)."""
        mock_basket_service.create_basket.return_value = {
            'id': 'default-basket-id',
            'name': 'default-basket',
            'shelf_id': 'docs-shelf-id',
            'type': 'data',  # Default type
            'status': 'created'
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', 'documentation', '--basket', 'default-basket'
        ])

        assert result.exit_code == 0

    def test_remove_basket_from_shelf(self, cli_runner, mock_basket_service):
        """Test removing basket from shelf."""
        mock_basket_service.delete_basket.return_value = True

        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', 'documentation', '--remove-basket', 'old-docs', '--confirm'
        ])

        assert result.exit_code == 0


class TestShelfContextCommands:
    """Contract tests for shelf context management."""

    def test_set_current_shelf(self, cli_runner, mock_context_service, mock_shelf_service):
        """Test setting current shelf."""
        mock_shelf_service.get_shelf_by_name.return_value = {
            'name': 'examples',
            'basket_count': 2
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', 'examples', '--set-current'])

        assert result.exit_code == 0
        assert "Current shelf set to 'examples'" in result.output
        mock_context_service.set_current_shelf.assert_called_once_with('examples')

    def test_set_current_alternative_syntax(self, cli_runner, mock_context_service, mock_shelf_service):
        """Test alternative syntax for setting current shelf."""
        mock_shelf_service.get_shelf_by_name.return_value = {
            'name': 'documentation',
            'basket_count': 3
        }

        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--current', 'documentation'])

        assert result.exit_code == 0


class TestShelfRemovalCommands:
    """Contract tests for shelf removal (with security restrictions)."""

    def test_remove_shelf_requires_force(self, cli_runner, mock_shelf_service):
        """Test that shelf removal requires --force flag."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--remove', 'old-shelf'])

        # Should fail without --force flag
        assert result.exit_code != 0
        assert "--force" in result.output

    def test_remove_shelf_with_confirmation(self, cli_runner, mock_shelf_service):
        """Test shelf removal with proper confirmation."""
        mock_shelf_service.get_shelf_by_name.return_value = {
            'name': 'old-shelf',
            'baskets': [
                {'name': 'basket1', 'files': 10},
                {'name': 'basket2', 'files': 5}
            ]
        }
        mock_shelf_service.delete_shelf.return_value = True

        from src.cli.main import main

        # This would require user input confirmation in practice
        result = cli_runner.invoke(main, [
            'shelf', '--remove', 'old-shelf', '--force', '--confirm'
        ])

        assert result.exit_code == 0


class TestInteractiveShelfMenu:
    """Contract tests for interactive shelf management menu."""

    def test_interactive_menu_launch(self, cli_runner, mock_shelf_service):
        """Test that interactive menu launches when no arguments provided."""
        mock_shelf_service.list_shelfs.return_value = []

        from src.cli.main import main

        # This would launch interactive menu - test that it doesn't crash
        # In practice, this would require mocking user input
        result = cli_runner.invoke(main, ['shelf'], input='5\n')  # Select exit option

        # Should not crash (exact behavior depends on implementation)
        assert "DocBro Shelf Management" in result.output or result.exit_code in [0, 1]


class TestShelfCommandValidation:
    """Contract tests for command validation and error handling."""

    def test_multiple_action_flags_error(self, cli_runner):
        """Test error when multiple action flags are provided."""
        from src.cli.main import main

        result = cli_runner.invoke(main, [
            'shelf', '--new', 'test', '--list'
        ])

        assert result.exit_code != 0
        assert "Only one action flag" in result.output

    def test_missing_required_parameters(self, cli_runner):
        """Test error when required parameters are missing."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--new'])

        assert result.exit_code != 0

    def test_invalid_shelf_name_validation(self, cli_runner):
        """Test validation of shelf name format."""
        from src.cli.main import main

        result = cli_runner.invoke(main, ['shelf', '--new', 'invalid/shelf*name'])

        assert result.exit_code != 0


# NOTE: All these tests will initially FAIL because:
# 1. The shelf command group doesn't exist yet
# 2. The shelf/basket services don't exist yet
# 3. The CLI command routing for shelf operations isn't implemented
# 4. The interactive menu system for shelfs isn't built
#
# These tests serve as the contract specification that the implementation must satisfy.