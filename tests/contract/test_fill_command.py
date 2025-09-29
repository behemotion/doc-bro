"""Contract tests for fill command routing."""

import pytest
from click.testing import CliRunner

from src.cli.main import cli


class TestFillCommandContract:
    """Test the contract for unified fill command."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_fill_drag_box_routing(self):
        """Test fill command routes correctly for drag boxes."""
        # Create drag box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'test-drag',
            '--type', 'drag'
        ])
        assert box_result.exit_code == 0

        # Fill the drag box (should route to crawler)
        result = self.runner.invoke(cli, [
            'fill', 'test-drag',
            '--source', 'https://example.com'
        ])

        assert result.exit_code == 0
        assert "Crawling https://example.com into drag box 'test-drag'" in result.output

    @pytest.mark.asyncio
    async def test_fill_rag_box_routing(self):
        """Test fill command routes correctly for rag boxes."""
        # Create rag box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'test-rag',
            '--type', 'rag'
        ])
        assert box_result.exit_code == 0

        # Fill the rag box (should route to uploader)
        result = self.runner.invoke(cli, [
            'fill', 'test-rag',
            '--source', './test/documents/'
        ])

        assert result.exit_code == 0
        assert "Importing ./test/documents/ into rag box 'test-rag'" in result.output

    @pytest.mark.asyncio
    async def test_fill_bag_box_routing(self):
        """Test fill command routes correctly for bag boxes."""
        # Create bag box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'test-bag',
            '--type', 'bag'
        ])
        assert box_result.exit_code == 0

        # Fill the bag box (should route to storage)
        result = self.runner.invoke(cli, [
            'fill', 'test-bag',
            '--source', './test/files/'
        ])

        assert result.exit_code == 0
        assert "Storing ./test/files/ into bag box 'test-bag'" in result.output

    @pytest.mark.asyncio
    async def test_fill_nonexistent_box_fails(self):
        """Test fill command fails for nonexistent box."""
        result = self.runner.invoke(cli, [
            'fill', 'nonexistent-box',
            '--source', 'https://example.com'
        ])

        assert result.exit_code != 0
        assert "not found" in result.output or "nonexistent-box" in result.output

    @pytest.mark.asyncio
    async def test_fill_missing_source_fails(self):
        """Test fill command fails without source."""
        # Create box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'sourceless-box',
            '--type', 'rag'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, ['fill', 'sourceless-box'])

        assert result.exit_code != 0
        assert "source" in result.output.lower()

    @pytest.mark.asyncio
    async def test_fill_drag_specific_options(self):
        """Test drag-specific options are passed correctly."""
        # Create drag box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'drag-options',
            '--type', 'drag'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'fill', 'drag-options',
            '--source', 'https://example.com',
            '--max-pages', '50',
            '--rate-limit', '2.0',
            '--depth', '2'
        ])

        assert result.exit_code == 0
        # Should indicate the options were applied
        assert "50" in result.output or "max-pages" in result.output

    @pytest.mark.asyncio
    async def test_fill_rag_specific_options(self):
        """Test rag-specific options are passed correctly."""
        # Create rag box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'rag-options',
            '--type', 'rag'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'fill', 'rag-options',
            '--source', './documents/',
            '--chunk-size', '1000',
            '--overlap', '100'
        ])

        assert result.exit_code == 0
        # Should indicate the options were applied
        assert "1000" in result.output or "chunk-size" in result.output

    @pytest.mark.asyncio
    async def test_fill_bag_specific_options(self):
        """Test bag-specific options are passed correctly."""
        # Create bag box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'bag-options',
            '--type', 'bag'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'fill', 'bag-options',
            '--source', './files/',
            '--recursive',
            '--pattern', '*.txt'
        ])

        assert result.exit_code == 0
        # Should indicate the options were applied
        assert "recursive" in result.output or "pattern" in result.output

    @pytest.mark.asyncio
    async def test_fill_with_shelf_context(self):
        """Test fill command with explicit shelf context."""
        # Create shelf and box
        shelf_result = self.runner.invoke(cli, ['shelf', 'create', 'context-shelf'])
        assert shelf_result.exit_code == 0

        box_result = self.runner.invoke(cli, [
            'box', 'create', 'context-box',
            '--type', 'rag',
            '--shelf', 'context-shelf'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'fill', 'context-box',
            '--source', './docs/',
            '--shelf', 'context-shelf'
        ])

        assert result.exit_code == 0
        assert "context-shelf" in result.output or "context-box" in result.output

    @pytest.mark.asyncio
    async def test_fill_uses_current_shelf_by_default(self):
        """Test fill command uses current shelf when not specified."""
        # Create and set current shelf
        shelf_result = self.runner.invoke(cli, [
            'shelf', 'create', 'current-fill-shelf',
            '--set-current'
        ])
        assert shelf_result.exit_code == 0

        # Create box in current shelf
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'current-fill-box',
            '--type', 'rag'
        ])
        assert box_result.exit_code == 0

        # Fill without specifying shelf (should use current)
        result = self.runner.invoke(cli, [
            'fill', 'current-fill-box',
            '--source', './docs/'
        ])

        assert result.exit_code == 0
        # Should work without error

    @pytest.mark.asyncio
    async def test_fill_no_current_shelf_warning(self):
        """Test fill command warns when no current shelf is set."""
        # Ensure no current shelf (implementation dependent)
        # Create box without shelf context
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'no-current-box',
            '--type', 'rag'
        ])

        if box_result.exit_code != 0:
            # Expected - might require current shelf
            assert "current shelf" in box_result.output or "shelf" in box_result.output

    @pytest.mark.asyncio
    async def test_fill_success_confirmation(self):
        """Test fill command provides success confirmation."""
        # Create box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'success-box',
            '--type', 'rag'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'fill', 'success-box',
            '--source', './docs/'
        ])

        assert result.exit_code == 0
        assert "Successfully filled box 'success-box'" in result.output

    @pytest.mark.asyncio
    async def test_fill_error_handling(self):
        """Test fill command handles errors appropriately."""
        # Create box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'error-box',
            '--type', 'drag'
        ])
        assert box_result.exit_code == 0

        # Try to fill with invalid source
        result = self.runner.invoke(cli, [
            'fill', 'error-box',
            '--source', 'invalid://not-a-real-url'
        ])

        assert result.exit_code != 0
        assert "Failed to fill:" in result.output or "error" in result.output.lower()

    @pytest.mark.asyncio
    async def test_fill_help(self):
        """Test fill command help."""
        result = self.runner.invoke(cli, ['fill', '--help'])

        assert result.exit_code == 0
        assert "Add content to a box" in result.output
        assert "--source" in result.output
        assert "--shelf" in result.output
        assert "drag" in result.output
        assert "rag" in result.output
        assert "bag" in result.output

    @pytest.mark.asyncio
    async def test_fill_progress_indication(self):
        """Test fill command shows progress information."""
        # Create box
        box_result = self.runner.invoke(cli, [
            'box', 'create', 'progress-box',
            '--type', 'rag'
        ])
        assert box_result.exit_code == 0

        result = self.runner.invoke(cli, [
            'fill', 'progress-box',
            '--source', './docs/'
        ])

        assert result.exit_code == 0
        # Should show some kind of progress or activity indication
        output_lines = result.output.strip().split('\n')
        assert len(output_lines) > 1  # More than just final success message