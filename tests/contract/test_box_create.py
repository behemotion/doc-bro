"""Contract tests for box create command."""

import pytest
from click.testing import CliRunner

from src.cli.main import cli


class TestBoxCreateContract:
    """Test the contract for box create command."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_box_create_drag_type_success(self):
        """Test creating a drag (crawling) box."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'test-drag-box',
            '--type', 'drag'
        ])

        assert result.exit_code == 0
        assert "Created drag box 'test-drag-box'" in result.output

    @pytest.mark.asyncio
    async def test_box_create_rag_type_success(self):
        """Test creating a rag (document) box."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'test-rag-box',
            '--type', 'rag'
        ])

        assert result.exit_code == 0
        assert "Created rag box 'test-rag-box'" in result.output

    @pytest.mark.asyncio
    async def test_box_create_bag_type_success(self):
        """Test creating a bag (storage) box."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'test-bag-box',
            '--type', 'bag'
        ])

        assert result.exit_code == 0
        assert "Created bag box 'test-bag-box'" in result.output

    @pytest.mark.asyncio
    async def test_box_create_with_shelf(self):
        """Test creating box and adding to specific shelf."""
        # First create a shelf
        shelf_result = self.runner.invoke(cli, ['shelf', 'create', 'test-target-shelf'])
        assert shelf_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'box', 'create', 'shelf-box',
            '--type', 'rag',
            '--shelf', 'test-target-shelf'
        ])

        assert result.exit_code == 0
        assert "Created rag box 'shelf-box'" in result.output
        assert "test-target-shelf" in result.output

    @pytest.mark.asyncio
    async def test_box_create_with_description(self):
        """Test creating box with description."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'described-box',
            '--type', 'bag',
            '--description', 'A test box for storage'
        ])

        assert result.exit_code == 0
        assert "Created bag box 'described-box'" in result.output

    @pytest.mark.asyncio
    async def test_box_create_missing_type_fails(self):
        """Test that missing type parameter fails."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'no-type-box'
        ])

        assert result.exit_code != 0
        assert "--type" in result.output or "required" in result.output

    @pytest.mark.asyncio
    async def test_box_create_invalid_type_fails(self):
        """Test that invalid type fails."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'invalid-type-box',
            '--type', 'invalid'
        ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower()

    @pytest.mark.asyncio
    async def test_box_create_duplicate_name_fails(self):
        """Test that duplicate box names fail."""
        # Create first box
        result1 = self.runner.invoke(cli, [
            'box', 'create', 'duplicate-box',
            '--type', 'rag'
        ])
        assert result1.exit_code == 0

        # Try to create with same name
        result2 = self.runner.invoke(cli, [
            'box', 'create', 'duplicate-box',
            '--type', 'bag'
        ])

        assert result2.exit_code != 0
        assert "already exists" in result2.output

    @pytest.mark.asyncio
    async def test_box_create_empty_name_fails(self):
        """Test that empty box name fails."""
        result = self.runner.invoke(cli, [
            'box', 'create', '',
            '--type', 'rag'
        ])

        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_box_create_reserved_name_fails(self):
        """Test that reserved box names fail."""
        reserved_names = ['default', 'system', 'temp']

        for name in reserved_names:
            result = self.runner.invoke(cli, [
                'box', 'create', name,
                '--type', 'rag'
            ])

            assert result.exit_code != 0
            assert "reserved" in result.output or "invalid" in result.output

    @pytest.mark.asyncio
    async def test_box_create_with_nonexistent_shelf_fails(self):
        """Test that specifying nonexistent shelf fails."""
        result = self.runner.invoke(cli, [
            'box', 'create', 'orphan-box',
            '--type', 'rag',
            '--shelf', 'nonexistent-shelf'
        ])

        assert result.exit_code != 0
        assert "not found" in result.output or "nonexistent-shelf" in result.output

    @pytest.mark.asyncio
    async def test_box_create_valid_special_characters(self):
        """Test box creation with valid special characters."""
        valid_names = ['box-with-hyphens', 'box_with_underscores', 'box with spaces']

        for name in valid_names:
            result = self.runner.invoke(cli, [
                'box', 'create', name,
                '--type', 'rag'
            ])

            assert result.exit_code == 0
            assert f"Created rag box '{name}'" in result.output

    @pytest.mark.asyncio
    async def test_box_create_type_choices_validation(self):
        """Test that only valid type choices are accepted."""
        valid_types = ['drag', 'rag', 'bag']

        for box_type in valid_types:
            result = self.runner.invoke(cli, [
                'box', 'create', f'test-{box_type}-box',
                '--type', box_type
            ])

            assert result.exit_code == 0
            assert f"Created {box_type} box" in result.output

    @pytest.mark.asyncio
    async def test_box_create_shows_globally_unique_constraint(self):
        """Test that box names are globally unique across all shelves."""
        # Create box in default context
        result1 = self.runner.invoke(cli, [
            'box', 'create', 'global-unique-box',
            '--type', 'rag'
        ])
        assert result1.exit_code == 0

        # Create shelf
        shelf_result = self.runner.invoke(cli, ['shelf', 'create', 'another-shelf'])
        assert shelf_result.exit_code == 0

        # Try to create box with same name in different shelf
        result2 = self.runner.invoke(cli, [
            'box', 'create', 'global-unique-box',
            '--type', 'bag',
            '--shelf', 'another-shelf'
        ])

        assert result2.exit_code != 0
        assert "already exists" in result2.output

    @pytest.mark.asyncio
    async def test_box_create_help(self):
        """Test box create command help."""
        result = self.runner.invoke(cli, ['box', 'create', '--help'])

        assert result.exit_code == 0
        assert "Create" in result.output
        assert "--type" in result.output
        assert "--shelf" in result.output
        assert "--description" in result.output
        assert "drag" in result.output
        assert "rag" in result.output
        assert "bag" in result.output

    @pytest.mark.asyncio
    async def test_box_create_long_name_limit(self):
        """Test box creation with name at character limit."""
        # Test max length name (100 chars)
        max_name = 'b' * 100
        result = self.runner.invoke(cli, [
            'box', 'create', max_name,
            '--type', 'rag'
        ])
        assert result.exit_code == 0

        # Test over limit
        over_limit_name = 'b' * 101
        result2 = self.runner.invoke(cli, [
            'box', 'create', over_limit_name,
            '--type', 'rag'
        ])
        assert result2.exit_code != 0
        assert "100 characters" in result2.output or "too long" in result2.output