"""Integration test for content filling by box type with type-aware routing.

This test validates that different box types (drag/rag/bag) receive
appropriate prompts and fill workflows.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

# These imports will fail until the enhanced CLI commands are implemented
try:
    from src.cli.commands.box import box_command
    from src.cli.commands.fill import fill_command
    from src.services.context_service import ContextService
    from src.logic.wizard.box_wizard import BoxWizard
    CLI_ENHANCED = True
except ImportError:
    CLI_ENHANCED = False
    box_command = None
    fill_command = None
    ContextService = None
    BoxWizard = None


class TestContentFillingByType:
    """Integration test for type-aware content filling."""

    @pytest.mark.integration
    def test_imports_available(self):
        """Test that enhanced CLI commands can be imported."""
        assert CLI_ENHANCED, "Enhanced CLI commands not implemented yet"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_drag_box_creation_and_wizard(self):
        """Test creating drag box with wizard for website crawling."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test drag box creation with wizard
        with patch('src.cli.commands.box.create_box') as mock_create:
            mock_create.return_value = True

            with patch('src.logic.wizard.box_wizard.BoxWizard') as mock_wizard_class:
                mock_wizard = AsyncMock()
                mock_wizard_class.return_value = mock_wizard

                # Mock wizard for drag box
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.configuration = {
                    "box_type": "drag",
                    "description": "Website documentation crawler",
                    "auto_process": True,
                    "crawl_depth": 3,
                    "rate_limit": 1.0
                }
                mock_wizard.run.return_value = mock_result

                result = runner.invoke(box_command, [
                    'create', 'website-docs',
                    '--type', 'drag',
                    '--init'
                ])

                # Should create box and run wizard
                mock_create.assert_called_once()
                mock_wizard.run.assert_called_once_with('website-docs')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rag_box_creation_and_wizard(self):
        """Test creating rag box with wizard for document upload."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test rag box creation with wizard
        with patch('src.cli.commands.box.create_box') as mock_create:
            mock_create.return_value = True

            with patch('src.logic.wizard.box_wizard.BoxWizard') as mock_wizard_class:
                mock_wizard = AsyncMock()
                mock_wizard_class.return_value = mock_wizard

                # Mock wizard for rag box
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.configuration = {
                    "box_type": "rag",
                    "description": "Local file document processor",
                    "auto_process": True,
                    "file_patterns": ["*.pdf", "*.md", "*.txt"],
                    "chunk_size": 500,
                    "overlap": 50
                }
                mock_wizard.run.return_value = mock_result

                result = runner.invoke(box_command, [
                    'create', 'local-files',
                    '--type', 'rag',
                    '--init'
                ])

                # Should create box and run wizard
                mock_create.assert_called_once()
                mock_wizard.run.assert_called_once_with('local-files')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bag_box_creation_and_wizard(self):
        """Test creating bag box with wizard for data storage."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test bag box creation with wizard
        with patch('src.cli.commands.box.create_box') as mock_create:
            mock_create.return_value = True

            with patch('src.logic.wizard.box_wizard.BoxWizard') as mock_wizard_class:
                mock_wizard = AsyncMock()
                mock_wizard_class.return_value = mock_wizard

                # Mock wizard for bag box
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.configuration = {
                    "box_type": "bag",
                    "description": "Raw data storage container",
                    "auto_process": False,
                    "storage_format": "json",
                    "compression": True
                }
                mock_wizard.run.return_value = mock_result

                result = runner.invoke(box_command, [
                    'create', 'data-store',
                    '--type', 'bag',
                    '--init'
                ])

                # Should create box and run wizard
                mock_create.assert_called_once()
                mock_wizard.run.assert_called_once_with('data-store')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_drag_box_url_prompt(self):
        """Test that empty drag box prompts for website URL."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock context service to return empty drag box
        with patch('src.cli.commands.box.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Simulate empty drag box
            mock_context = MagicMock()
            mock_context.exists = True
            mock_context.is_empty = True
            mock_context.entity_name = "website-docs"
            mock_context.entity_type = "box"
            mock_context.box_type = "drag"
            mock_service.check_box_exists.return_value = mock_context

            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = True

                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = "https://docs.example.com"

                    with patch('src.cli.commands.fill.fill_drag_box') as mock_fill:
                        result = runner.invoke(box_command, ['website-docs'])

                        # Should prompt for URL
                        mock_confirm.assert_called_once()
                        mock_prompt.assert_called_once()
                        # Should call fill with URL
                        mock_fill.assert_called_once_with("website-docs", "https://docs.example.com")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_rag_box_file_prompt(self):
        """Test that empty rag box prompts for file path."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock context service to return empty rag box
        with patch('src.cli.commands.box.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Simulate empty rag box
            mock_context = MagicMock()
            mock_context.exists = True
            mock_context.is_empty = True
            mock_context.entity_name = "local-files"
            mock_context.entity_type = "box"
            mock_context.box_type = "rag"
            mock_service.check_box_exists.return_value = mock_context

            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = True

                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = "/path/to/documents"

                    with patch('src.cli.commands.fill.fill_rag_box') as mock_fill:
                        result = runner.invoke(box_command, ['local-files'])

                        # Should prompt for file path
                        mock_confirm.assert_called_once()
                        mock_prompt.assert_called_once()
                        # Should call fill with path
                        mock_fill.assert_called_once_with("local-files", "/path/to/documents")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_bag_box_data_prompt(self):
        """Test that empty bag box prompts for content path."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Mock context service to return empty bag box
        with patch('src.cli.commands.box.ContextService') as mock_context_service:
            mock_service = AsyncMock()
            mock_context_service.return_value = mock_service

            # Simulate empty bag box
            mock_context = MagicMock()
            mock_context.exists = True
            mock_context.is_empty = True
            mock_context.entity_name = "data-store"
            mock_context.entity_type = "box"
            mock_context.box_type = "bag"
            mock_service.check_box_exists.return_value = mock_context

            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = True

                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = "/path/to/data"

                    with patch('src.cli.commands.fill.fill_bag_box') as mock_fill:
                        result = runner.invoke(box_command, ['data-store'])

                        # Should prompt for content path
                        mock_confirm.assert_called_once()
                        mock_prompt.assert_called_once()
                        # Should call fill with path
                        mock_fill.assert_called_once_with("data-store", "/path/to/data")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fill_command_type_routing(self):
        """Test that fill command routes correctly based on box type."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test drag box fill routing
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            with patch('src.cli.commands.fill.fill_drag_box') as mock_fill_drag:
                result = runner.invoke(fill_command, [
                    'website-docs',
                    '--source', 'https://example.com'
                ])

                mock_fill_drag.assert_called_once_with('website-docs', 'https://example.com')

        # Test rag box fill routing
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "rag"

            with patch('src.cli.commands.fill.fill_rag_box') as mock_fill_rag:
                result = runner.invoke(fill_command, [
                    'local-files',
                    '--source', '/path/to/docs'
                ])

                mock_fill_rag.assert_called_once_with('local-files', '/path/to/docs')

        # Test bag box fill routing
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "bag"

            with patch('src.cli.commands.fill.fill_bag_box') as mock_fill_bag:
                result = runner.invoke(fill_command, [
                    'data-store',
                    '--source', '/path/to/data'
                ])

                mock_fill_bag.assert_called_once_with('data-store', '/path/to/data')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_drag_box_specific_parameters(self):
        """Test drag box specific parameters are handled correctly."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test drag-specific parameters
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            with patch('src.cli.commands.fill.fill_drag_box') as mock_fill:
                result = runner.invoke(fill_command, [
                    'website-docs',
                    '--source', 'https://example.com',
                    '--max-pages', '100',
                    '--rate-limit', '2.0',
                    '--depth', '3'
                ])

                # Should pass drag-specific parameters
                args, kwargs = mock_fill.call_args
                assert args[0] == 'website-docs'
                assert args[1] == 'https://example.com'
                # Should have drag-specific options in kwargs
                assert 'max_pages' in str(kwargs) or 'max_pages' in str(args)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rag_box_specific_parameters(self):
        """Test rag box specific parameters are handled correctly."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test rag-specific parameters
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "rag"

            with patch('src.cli.commands.fill.fill_rag_box') as mock_fill:
                result = runner.invoke(fill_command, [
                    'local-files',
                    '--source', '/path/to/docs',
                    '--chunk-size', '1000',
                    '--overlap', '100'
                ])

                # Should pass rag-specific parameters
                args, kwargs = mock_fill.call_args
                assert args[0] == 'local-files'
                assert args[1] == '/path/to/docs'
                # Should have rag-specific options
                assert 'chunk_size' in str(kwargs) or 'chunk_size' in str(args)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bag_box_specific_parameters(self):
        """Test bag box specific parameters are handled correctly."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test bag-specific parameters
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "bag"

            with patch('src.cli.commands.fill.fill_bag_box') as mock_fill:
                result = runner.invoke(fill_command, [
                    'data-store',
                    '--source', '/path/to/data',
                    '--recursive',
                    '--pattern', '*.json'
                ])

                # Should pass bag-specific parameters
                args, kwargs = mock_fill.call_args
                assert args[0] == 'data-store'
                assert args[1] == '/path/to/data'
                # Should have bag-specific options
                assert 'recursive' in str(kwargs) or 'pattern' in str(kwargs)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_source_validation_by_type(self):
        """Test that source validation varies by box type."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test drag box URL validation
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            with patch('src.cli.commands.fill.validate_url_source') as mock_validate:
                mock_validate.return_value = True

                with patch('src.cli.commands.fill.fill_drag_box') as mock_fill:
                    result = runner.invoke(fill_command, [
                        'website-docs',
                        '--source', 'https://example.com'
                    ])

                    # Should validate as URL
                    mock_validate.assert_called_once_with('https://example.com')

        # Test rag box file path validation
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "rag"

            with patch('src.cli.commands.fill.validate_file_source') as mock_validate:
                mock_validate.return_value = True

                with patch('src.cli.commands.fill.fill_rag_box') as mock_fill:
                    result = runner.invoke(fill_command, [
                        'local-files',
                        '--source', '/path/to/docs'
                    ])

                    # Should validate as file path
                    mock_validate.assert_called_once_with('/path/to/docs')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_box_content_status_update(self):
        """Test that box content status is updated after filling."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        # Test successful fill updates status
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            with patch('src.cli.commands.fill.fill_drag_box') as mock_fill:
                mock_fill.return_value = {"success": True, "items_added": 50}

                with patch('src.cli.commands.fill.update_box_status') as mock_update:
                    runner = CliRunner()
                    result = runner.invoke(fill_command, [
                        'website-docs',
                        '--source', 'https://example.com'
                    ])

                    # Should update box status after successful fill
                    mock_update.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fill_progress_display(self):
        """Test that fill operations display progress appropriately."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test progress display for drag box
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            with patch('src.cli.commands.fill.CrawlProgressDisplay') as mock_progress:
                with patch('src.cli.commands.fill.fill_drag_box') as mock_fill:
                    result = runner.invoke(fill_command, [
                        'website-docs',
                        '--source', 'https://example.com'
                    ])

                    # Should use progress display
                    mock_progress.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_type_mismatch_error_handling(self):
        """Test error handling when source doesn't match box type."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test file path with drag box (should fail)
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            result = runner.invoke(fill_command, [
                'website-docs',
                '--source', '/path/to/file'
            ])

            # Should show error about type mismatch
            assert result.exit_code != 0
            assert "url" in result.output.lower() or "website" in result.output.lower()

        # Test URL with rag box (should fail)
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "rag"

            result = runner.invoke(fill_command, [
                'local-files',
                '--source', 'https://example.com'
            ])

            # Should show error about type mismatch
            assert result.exit_code != 0
            assert "file" in result.output.lower() or "path" in result.output.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_successful_fill_completion_message(self):
        """Test that successful fills show appropriate completion messages."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced CLI not implemented yet")

        runner = CliRunner()

        # Test drag box completion message
        with patch('src.cli.commands.fill.get_box_type') as mock_get_type:
            mock_get_type.return_value = "drag"

            with patch('src.cli.commands.fill.fill_drag_box') as mock_fill:
                mock_fill.return_value = {
                    "success": True,
                    "pages_crawled": 25,
                    "items_added": 50,
                    "processing_time": 45.2
                }

                result = runner.invoke(fill_command, [
                    'website-docs',
                    '--source', 'https://example.com'
                ])

                # Should show success message with stats
                output = result.output.lower()
                assert "success" in output or "complete" in output
                assert "25" in output  # pages crawled
                assert "50" in output  # items added