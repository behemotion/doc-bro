"""Contract tests for CLI shelf creation commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.cli.commands.shelf import ShelfCommands
from src.models.shelf import Shelf
from src.services.shelf_service import ShelfService


class TestShelfCreateContract:
    """Contract tests for shelf creation CLI commands."""

    @pytest.fixture
    def mock_shelf_service(self):
        """Mock shelf service."""
        service = MagicMock(spec=ShelfService)
        service.create_shelf = AsyncMock()
        service.get_shelf = AsyncMock()
        service.list_shelfs = AsyncMock()
        return service

    @pytest.fixture
    def shelf_commands(self, mock_shelf_service):
        """Shelf commands instance with mocked service."""
        return ShelfCommands(shelf_service=mock_shelf_service)

    @pytest.mark.asyncio
    async def test_shelf_create_basic_contract(self, shelf_commands, mock_shelf_service):
        """Test basic shelf creation command contract."""
        # Arrange
        shelf_name = "documentation"
        expected_shelf = Shelf(
            id="test-shelf-id",
            name=shelf_name,
            baskets=[]
        )
        mock_shelf_service.create_shelf.return_value = expected_shelf
        mock_shelf_service.get_shelf.return_value = expected_shelf

        # Act - simulate: docbro shelf --new documentation
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=None,
            set_current=False,
            force=False
        )

        # Assert
        assert result["success"] is True
        assert result["shelf_name"] == shelf_name
        assert "created successfully" in result["message"].lower()

        # Verify service was called correctly
        mock_shelf_service.create_shelf.assert_called_once_with(
            name=shelf_name,
            description=None,
            set_current=False,
            force=False
        )

    @pytest.mark.asyncio
    async def test_shelf_create_with_description_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf creation with description contract."""
        # Arrange
        shelf_name = "API Documentation"
        description = "Complete API docs collection"
        expected_shelf = Shelf(
            id="test-shelf-id",
            name=shelf_name,
            metadata={"description": description},
            baskets=[]
        )
        mock_shelf_service.create_shelf.return_value = expected_shelf

        # Act - simulate: docbro shelf --new "API Documentation" --description "Complete API docs collection"
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=description,
            set_current=False,
            force=False
        )

        # Assert
        assert result["success"] is True
        assert result["shelf_name"] == shelf_name
        assert result.get("description") == description

        mock_shelf_service.create_shelf.assert_called_once_with(
            name=shelf_name,
            description=description,
            set_current=False,
            force=False
        )

    @pytest.mark.asyncio
    async def test_shelf_create_set_current_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf creation with set-current flag contract."""
        # Arrange
        shelf_name = "documentation"
        expected_shelf = Shelf(
            id="test-shelf-id",
            name=shelf_name,
            is_current=True,
            baskets=[]
        )
        mock_shelf_service.create_shelf.return_value = expected_shelf

        # Act - simulate: docbro shelf --new documentation --set-current
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=None,
            set_current=True,
            force=False
        )

        # Assert
        assert result["success"] is True
        assert result["shelf_name"] == shelf_name
        assert result.get("is_current") is True

        mock_shelf_service.create_shelf.assert_called_once_with(
            name=shelf_name,
            description=None,
            set_current=True,
            force=False
        )

    @pytest.mark.asyncio
    async def test_shelf_create_force_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf creation with force flag contract."""
        # Arrange
        shelf_name = "documentation"
        expected_shelf = Shelf(
            id="test-shelf-id",
            name=shelf_name,
            baskets=[]
        )
        mock_shelf_service.create_shelf.return_value = expected_shelf

        # Act - simulate: docbro shelf --new documentation --force
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=None,
            set_current=False,
            force=True
        )

        # Assert
        assert result["success"] is True
        assert result["shelf_name"] == shelf_name

        mock_shelf_service.create_shelf.assert_called_once_with(
            name=shelf_name,
            description=None,
            set_current=False,
            force=True
        )

    @pytest.mark.asyncio
    async def test_shelf_create_already_exists_error_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf creation error when shelf already exists."""
        # Arrange
        shelf_name = "documentation"
        from src.services.shelf_service import ShelfExistsError
        mock_shelf_service.create_shelf.side_effect = ShelfExistsError(
            f"Shelf '{shelf_name}' already exists"
        )

        # Act - simulate: docbro shelf --new documentation (when it already exists)
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=None,
            set_current=False,
            force=False
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "shelf_exists"
        assert shelf_name in result["message"]
        assert "already exists" in result["message"].lower()
        assert "use --force" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_shelf_create_invalid_name_error_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf creation error for invalid shelf name."""
        # Arrange
        invalid_name = "invalid/shelf*name"
        from src.models.shelf import ShelfValidationError
        mock_shelf_service.create_shelf.side_effect = ShelfValidationError(
            "Shelf name can only contain letters, numbers, hyphens, underscores, and spaces"
        )

        # Act - simulate: docbro shelf --new "invalid/shelf*name"
        result = await shelf_commands.create_shelf(
            name=invalid_name,
            description=None,
            set_current=False,
            force=False
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "invalid_shelf_name"
        assert "invalid shelf name" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_shelf_create_output_format_contract(self, shelf_commands, mock_shelf_service):
        """Test the expected output format of shelf creation."""
        # Arrange
        shelf_name = "documentation"
        expected_shelf = Shelf(
            id="test-shelf-id",
            name=shelf_name,
            baskets=[]
        )
        mock_shelf_service.create_shelf.return_value = expected_shelf

        # Act
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=None,
            set_current=False,
            force=False
        )

        # Assert expected output structure
        assert isinstance(result, dict)
        required_fields = ["success", "shelf_name", "message", "details"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Check details structure
        details = result["details"]
        assert isinstance(details, dict)
        detail_fields = ["shelf_id", "created_at", "is_current", "default_basket_created"]
        for field in detail_fields:
            assert field in details, f"Missing detail field: {field}"

    @pytest.mark.asyncio
    async def test_shelf_create_default_basket_created_contract(self, shelf_commands, mock_shelf_service):
        """Test that default basket is created with new shelf."""
        # Arrange
        shelf_name = "documentation"
        expected_shelf = Shelf(
            id="test-shelf-id",
            name=shelf_name,
            baskets=[]  # Service handles default basket creation internally
        )
        mock_shelf_service.create_shelf.return_value = expected_shelf

        # Act
        result = await shelf_commands.create_shelf(
            name=shelf_name,
            description=None,
            set_current=False,
            force=False
        )

        # Assert
        assert result["success"] is True
        assert result["details"]["default_basket_created"] is True
        assert "default basket created" in result["message"].lower()