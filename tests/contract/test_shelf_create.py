"""Contract tests for shelf create command."""

import pytest
from click.testing import CliRunner

from src.cli.main import cli


class TestShelfCreateContract:
    """Test the contract for shelf create command."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_shelf_create_basic_success(self):
        """Test basic shelf creation succeeds."""
        result = self.runner.invoke(cli, ['shelf', 'create', 'test-shelf'])

        assert result.exit_code == 0
        assert "Created shelf 'test-shelf'" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_with_description(self):
        """Test shelf creation with description."""
        result = self.runner.invoke(cli, [
            'shelf', 'create', 'documented-shelf',
            '--description', 'A shelf for testing'
        ])

        assert result.exit_code == 0
        assert "Created shelf 'documented-shelf'" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_set_current(self):
        """Test shelf creation with set-current flag."""
        result = self.runner.invoke(cli, [
            'shelf', 'create', 'current-shelf',
            '--set-current'
        ])

        assert result.exit_code == 0
        assert "Created shelf 'current-shelf'" in result.output
        assert "Set as current shelf" in result.output or "current" in result.output.lower()

    @pytest.mark.asyncio
    async def test_shelf_create_duplicate_name(self):
        """Test that creating shelf with duplicate name fails."""
        # Create first shelf
        result1 = self.runner.invoke(cli, ['shelf', 'create', 'duplicate-shelf'])
        assert result1.exit_code == 0

        # Try to create with same name
        result2 = self.runner.invoke(cli, ['shelf', 'create', 'duplicate-shelf'])
        assert result2.exit_code != 0
        assert "already exists" in result2.output

    @pytest.mark.asyncio
    async def test_shelf_create_invalid_name_empty(self):
        """Test that empty shelf name fails."""
        result = self.runner.invoke(cli, ['shelf', 'create', ''])
        assert result2.exit_code != 0

    @pytest.mark.asyncio
    async def test_shelf_create_invalid_name_reserved(self):
        """Test that reserved shelf names fail."""
        reserved_names = ['default', 'system', 'temp']

        for name in reserved_names:
            result = self.runner.invoke(cli, ['shelf', 'create', name])
            assert result.exit_code != 0
            assert "reserved" in result.output or "invalid" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_auto_creates_default_box(self):
        """Test that creating shelf auto-creates a default box."""
        result = self.runner.invoke(cli, ['shelf', 'create', 'auto-box-shelf'])

        assert result.exit_code == 0
        assert "Created shelf 'auto-box-shelf'" in result.output
        # Should mention the auto-created box
        assert "auto-box-shelf_box" in result.output or "default box" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_shows_box_count(self):
        """Test that create command shows initial box count."""
        result = self.runner.invoke(cli, ['shelf', 'create', 'counted-shelf'])

        assert result.exit_code == 0
        # Should indicate the shelf has 1 box (the auto-created one)
        assert "1" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_help(self):
        """Test shelf create command help."""
        result = self.runner.invoke(cli, ['shelf', 'create', '--help'])

        assert result.exit_code == 0
        assert "Create a new shelf" in result.output
        assert "--description" in result.output
        assert "--set-current" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_verbose_output(self):
        """Test that create command provides adequate information."""
        result = self.runner.invoke(cli, ['shelf', 'create', 'verbose-shelf'])

        assert result.exit_code == 0
        assert "verbose-shelf" in result.output
        # Should provide some details about what was created
        assert len(result.output.strip()) > 50  # More than just success message

    @pytest.mark.asyncio
    async def test_shelf_create_with_special_characters(self):
        """Test shelf creation with valid special characters."""
        valid_names = ['shelf-with-hyphens', 'shelf_with_underscores', 'shelf with spaces']

        for name in valid_names:
            result = self.runner.invoke(cli, ['shelf', 'create', name])
            assert result.exit_code == 0
            assert f"Created shelf '{name}'" in result.output

    @pytest.mark.asyncio
    async def test_shelf_create_long_name_limit(self):
        """Test shelf creation with name at character limit."""
        # Test max length name (100 chars)
        max_name = 'a' * 100
        result = self.runner.invoke(cli, ['shelf', 'create', max_name])
        assert result.exit_code == 0

        # Test over limit
        over_limit_name = 'a' * 101
        result2 = self.runner.invoke(cli, ['shelf', 'create', over_limit_name])
        assert result2.exit_code != 0
        assert "100 characters" in result2.output or "too long" in result2.output