"""Contract tests for CLI shelf listing commands."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.cli.commands.shelf import ShelfCommands
from src.models.shelf import Shelf
from src.services.shelf_service import ShelfService


class TestShelfListContract:
    """Contract tests for shelf listing CLI commands."""

    @pytest.fixture
    def mock_shelf_service(self):
        """Mock shelf service."""
        service = MagicMock(spec=ShelfService)
        service.list_shelfs = AsyncMock()
        service.get_current_shelf = AsyncMock()
        return service

    @pytest.fixture
    def shelf_commands(self, mock_shelf_service):
        """Shelf commands instance with mocked service."""
        return ShelfCommands(shelf_service=mock_shelf_service)

    @pytest.fixture
    def sample_shelfs(self):
        """Sample shelf data for testing."""
        return [
            Shelf(
                id="shelf-1",
                name="documentation",
                created_at=datetime(2025, 9, 28, 10, 30, 15),
                updated_at=datetime(2025, 9, 29, 14, 20, 33),
                is_current=True,
                baskets=[]
            ),
            Shelf(
                id="shelf-2",
                name="examples",
                created_at=datetime(2025, 9, 29, 8, 15, 20),
                updated_at=datetime(2025, 9, 29, 9, 10, 45),
                is_current=False,
                baskets=[]
            ),
            Shelf(
                id="shelf-3",
                name="archived",
                created_at=datetime(2025, 9, 27, 16, 45, 10),
                updated_at=datetime(2025, 9, 27, 16, 45, 10),
                is_current=False,
                baskets=[]
            )
        ]

    @pytest.mark.asyncio
    async def test_shelf_list_basic_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test basic shelf listing command contract."""
        # Arrange
        mock_shelf_service.list_shelfs.return_value = sample_shelfs
        mock_shelf_service.get_current_shelf.return_value = sample_shelfs[0]  # documentation

        # Act - simulate: docbro shelf --list
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=None
        )

        # Assert
        assert result["success"] is True
        assert len(result["shelfs"]) == 3
        assert result["current_shelf"] == "documentation"
        assert result["total_shelfs"] == 3

        # Verify service was called correctly
        mock_shelf_service.list_shelfs.assert_called_once_with(
            verbose=False,
            current_only=False,
            limit=None
        )

    @pytest.mark.asyncio
    async def test_shelf_list_verbose_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test verbose shelf listing command contract."""
        # Arrange
        mock_shelf_service.list_shelfs.return_value = sample_shelfs
        mock_shelf_service.get_current_shelf.return_value = sample_shelfs[0]

        # Act - simulate: docbro shelf --list --verbose
        result = await shelf_commands.list_shelfs(
            verbose=True,
            current_only=False,
            limit=None
        )

        # Assert
        assert result["success"] is True
        assert result["verbose"] is True

        # Check that verbose data is included
        for shelf_data in result["shelfs"]:
            assert "created_at" in shelf_data
            assert "updated_at" in shelf_data
            assert "basket_count" in shelf_data
            assert "metadata" in shelf_data

        mock_shelf_service.list_shelfs.assert_called_once_with(
            verbose=True,
            current_only=False,
            limit=None
        )

    @pytest.mark.asyncio
    async def test_shelf_list_current_only_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test current shelf only listing command contract."""
        # Arrange
        current_shelf = sample_shelfs[0]  # documentation (is_current=True)
        mock_shelf_service.list_shelfs.return_value = [current_shelf]
        mock_shelf_service.get_current_shelf.return_value = current_shelf

        # Act - simulate: docbro shelf --list --current-only
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=True,
            limit=None
        )

        # Assert
        assert result["success"] is True
        assert len(result["shelfs"]) == 1
        assert result["shelfs"][0]["name"] == "documentation"
        assert result["shelfs"][0]["is_current"] is True
        assert result["current_shelf"] == "documentation"

        mock_shelf_service.list_shelfs.assert_called_once_with(
            verbose=False,
            current_only=True,
            limit=None
        )

    @pytest.mark.asyncio
    async def test_shelf_list_with_limit_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test shelf listing with limit contract."""
        # Arrange
        limited_shelfs = sample_shelfs[:2]  # First 2 shelfs
        mock_shelf_service.list_shelfs.return_value = limited_shelfs
        mock_shelf_service.get_current_shelf.return_value = sample_shelfs[0]

        # Act - simulate: docbro shelf --list --limit 2
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=2
        )

        # Assert
        assert result["success"] is True
        assert len(result["shelfs"]) == 2
        assert result["limit_applied"] == 2

        mock_shelf_service.list_shelfs.assert_called_once_with(
            verbose=False,
            current_only=False,
            limit=2
        )

    @pytest.mark.asyncio
    async def test_shelf_list_empty_result_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf listing when no shelfs exist."""
        # Arrange
        mock_shelf_service.list_shelfs.return_value = []
        mock_shelf_service.get_current_shelf.return_value = None

        # Act - simulate: docbro shelf --list (no shelfs exist)
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=None
        )

        # Assert
        assert result["success"] is True
        assert result["shelfs"] == []
        assert result["total_shelfs"] == 0
        assert result["current_shelf"] is None
        assert "no shelfs found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_shelf_list_output_format_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test the expected output format of shelf listing."""
        # Arrange
        mock_shelf_service.list_shelfs.return_value = sample_shelfs
        mock_shelf_service.get_current_shelf.return_value = sample_shelfs[0]

        # Act
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=None
        )

        # Assert expected output structure
        assert isinstance(result, dict)
        required_fields = ["success", "shelfs", "total_shelfs", "current_shelf", "message"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Check shelf data structure
        for shelf_data in result["shelfs"]:
            assert isinstance(shelf_data, dict)
            required_shelf_fields = ["name", "is_current", "created_at"]
            for field in required_shelf_fields:
                assert field in shelf_data, f"Missing shelf field: {field}"

    @pytest.mark.asyncio
    async def test_shelf_list_table_format_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test shelf listing table format output."""
        # Arrange
        mock_shelf_service.list_shelfs.return_value = sample_shelfs
        mock_shelf_service.get_current_shelf.return_value = sample_shelfs[0]

        # Act
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=None
        )

        # Assert table format structure
        assert "table_format" in result
        table_format = result["table_format"]
        assert isinstance(table_format, dict)
        assert "headers" in table_format
        assert "rows" in table_format

        # Check expected headers
        expected_headers = ["Name", "Baskets", "Current", "Created"]
        assert table_format["headers"] == expected_headers

        # Check row data structure
        assert len(table_format["rows"]) == 3
        for row in table_format["rows"]:
            assert len(row) == len(expected_headers)

    @pytest.mark.asyncio
    async def test_shelf_list_sorting_contract(self, shelf_commands, mock_shelf_service, sample_shelfs):
        """Test shelf listing sorting behavior."""
        # Arrange - shelfs should be sorted by created_at desc by default
        expected_order = [sample_shelfs[1], sample_shelfs[0], sample_shelfs[2]]  # examples, documentation, archived
        mock_shelf_service.list_shelfs.return_value = expected_order
        mock_shelf_service.get_current_shelf.return_value = sample_shelfs[0]

        # Act
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=None
        )

        # Assert sorting
        assert result["success"] is True
        shelf_names = [shelf["name"] for shelf in result["shelfs"]]
        assert shelf_names == ["examples", "documentation", "archived"]

    @pytest.mark.asyncio
    async def test_shelf_list_error_handling_contract(self, shelf_commands, mock_shelf_service):
        """Test shelf listing error handling."""
        # Arrange
        mock_shelf_service.list_shelfs.side_effect = Exception("Database connection failed")

        # Act
        result = await shelf_commands.list_shelfs(
            verbose=False,
            current_only=False,
            limit=None
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "database_error"
        assert "failed to retrieve shelf list" in result["message"].lower()
        assert "database connection failed" in result["details"]["error_message"]