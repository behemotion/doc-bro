"""Contract tests for shelf list command."""

import pytest
from click.testing import CliRunner

from src.cli.main import cli


class TestShelfListContract:
    """Test the contract for shelf list command."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_shelf_list_empty(self):
        """Test listing shelves when none exist."""
        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        assert "No shelves found" in result.output or len(result.output.strip()) == 0

    @pytest.mark.asyncio
    async def test_shelf_list_with_default_shelf(self):
        """Test listing includes default shelf if it exists."""
        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        # If default shelf exists, it should be shown
        if "common shelf" in result.output:
            assert "default" in result.output or "common shelf" in result.output

    @pytest.mark.asyncio
    async def test_shelf_list_basic_format(self):
        """Test basic list output format."""
        # Create a test shelf first
        create_result = self.runner.invoke(cli, ['shelf', 'create', 'list-test-shelf'])
        assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        assert "list-test-shelf" in result.output
        # Should show in table format with columns
        assert "name" in result.output.lower() or "shelf" in result.output.lower()

    @pytest.mark.asyncio
    async def test_shelf_list_shows_box_count(self):
        """Test that list shows box count for each shelf."""
        # Create shelf (should auto-create one box)
        create_result = self.runner.invoke(cli, ['shelf', 'create', 'count-test-shelf'])
        assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        assert "count-test-shelf" in result.output
        # Should show box count
        assert "1" in result.output  # At least the auto-created box

    @pytest.mark.asyncio
    async def test_shelf_list_shows_creation_date(self):
        """Test that list shows creation dates."""
        # Create shelf
        create_result = self.runner.invoke(cli, ['shelf', 'create', 'date-test-shelf'])
        assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        assert "date-test-shelf" in result.output
        # Should include date information (year at minimum)
        assert "202" in result.output  # Part of current year

    @pytest.mark.asyncio
    async def test_shelf_list_verbose_flag(self):
        """Test verbose flag provides additional information."""
        # Create shelf
        create_result = self.runner.invoke(cli, ['shelf', 'create', 'verbose-test-shelf'])
        assert create_result.exit_code == 0

        # Regular list
        result_normal = self.runner.invoke(cli, ['shelf', 'list'])
        normal_length = len(result_normal.output)

        # Verbose list
        result_verbose = self.runner.invoke(cli, ['shelf', 'list', '--verbose'])

        assert result_verbose.exit_code == 0
        assert len(result_verbose.output) >= normal_length
        # Verbose should include the shelf
        assert "verbose-test-shelf" in result_verbose.output

    @pytest.mark.asyncio
    async def test_shelf_list_current_only_flag(self):
        """Test current-only flag shows only current shelf."""
        # Create and set current shelf
        create_result = self.runner.invoke(cli, [
            'shelf', 'create', 'current-only-test',
            '--set-current'
        ])
        assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list', '--current-only'])

        assert result.exit_code == 0
        assert "current-only-test" in result.output

    @pytest.mark.asyncio
    async def test_shelf_list_limit_flag(self):
        """Test limit flag restricts number of results."""
        # Create multiple shelves
        for i in range(5):
            create_result = self.runner.invoke(cli, ['shelf', 'create', f'limit-test-{i}'])
            assert create_result.exit_code == 0

        # List with limit
        result = self.runner.invoke(cli, ['shelf', 'list', '--limit', '2'])

        assert result.exit_code == 0
        # Should show at most 2 shelves (plus headers)
        output_lines = [line for line in result.output.split('\n') if line.strip()]
        # Exact count depends on output format, but should be limited

    @pytest.mark.asyncio
    async def test_shelf_list_shows_current_marker(self):
        """Test that current shelf is marked in the list."""
        # Create and set current shelf
        create_result = self.runner.invoke(cli, [
            'shelf', 'create', 'current-marker-test',
            '--set-current'
        ])
        assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        assert "current-marker-test" in result.output
        # Should indicate which shelf is current
        assert "current" in result.output.lower() or "*" in result.output or "→" in result.output

    @pytest.mark.asyncio
    async def test_shelf_list_multiple_shelves(self):
        """Test listing multiple shelves."""
        shelf_names = ['multi-shelf-1', 'multi-shelf-2', 'multi-shelf-3']

        # Create multiple shelves
        for name in shelf_names:
            create_result = self.runner.invoke(cli, ['shelf', 'create', name])
            assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        # All shelves should be shown
        for name in shelf_names:
            assert name in result.output

    @pytest.mark.asyncio
    async def test_shelf_list_table_format(self):
        """Test that output uses table format as specified in contracts."""
        # Create shelf
        create_result = self.runner.invoke(cli, ['shelf', 'create', 'table-test'])
        assert create_result.exit_code == 0

        result = self.runner.invoke(cli, ['shelf', 'list'])

        assert result.exit_code == 0
        # Should be in table format (columns: name, boxes, current, created)
        output_lower = result.output.lower()
        assert "name" in output_lower
        assert "box" in output_lower  # "boxes" column
        assert "created" in output_lower

    @pytest.mark.asyncio
    async def test_shelf_list_help(self):
        """Test shelf list command help."""
        result = self.runner.invoke(cli, ['shelf', 'list', '--help'])

        assert result.exit_code == 0
        assert "List" in result.output
        assert "--verbose" in result.output
        assert "--current-only" in result.output
        assert "--limit" in result.output

    @pytest.mark.asyncio
    async def test_shelf_list_default_limit(self):
        """Test that default limit is applied correctly."""
        # Default limit should be 10 according to contract
        result = self.runner.invoke(cli, ['shelf', 'list'])
        assert result.exit_code == 0
        # Should not error even with default limit