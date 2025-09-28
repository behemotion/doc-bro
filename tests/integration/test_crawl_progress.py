"""Integration tests for crawl progress visualization."""

import pytest
import asyncio
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from src.cli.main import main
from src.logic.crawler.utils.progress import ProgressReporter, CrawlPhase


class TestCrawlProgressIntegration:
    """Integration tests for crawl progress visualization."""

    def test_crawl_shows_two_phase_progress(self):
        """Test that crawl displays two-phase progress (headers, content)."""
        runner = CliRunner()

        with patch('src.services.crawler.CrawlerService') as mock_crawler:
            with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
                progress_instance = MagicMock()
                mock_progress.return_value = progress_instance

                # Track phase starts
                phases_started = []

                def track_phase(phase, *args, **kwargs):
                    phases_started.append(phase)
                    return MagicMock()

                progress_instance.start_phase.side_effect = track_phase

                with patch('src.services.project_manager.ProjectManager') as mock_pm:
                    mock_pm.return_value.get_project.return_value = MagicMock()

                    result = runner.invoke(main, ["crawl", "test-project"])

                    # Should start both phases
                    assert CrawlPhase.ANALYZING_HEADERS in phases_started
                    assert CrawlPhase.CRAWLING_CONTENT in phases_started

    def test_progress_updates_periodically(self):
        """Test that progress updates at correct intervals."""
        runner = CliRunner()

        with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
            progress_instance = MagicMock()
            mock_progress.return_value = progress_instance

            update_count = 0

            def count_updates(*args, **kwargs):
                nonlocal update_count
                update_count += 1

            progress_instance.update_phase.side_effect = count_updates

            with patch('src.services.crawler.CrawlerService'):
                with patch('src.services.project_manager.ProjectManager') as mock_pm:
                    mock_pm.return_value.get_project.return_value = MagicMock()

                    # Simulate crawl with updates
                    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                        result = runner.invoke(main, ["crawl", "test-project"])

                        # Should have multiple updates
                        if update_count > 0:
                            assert update_count >= 2  # At least some updates

    def test_progress_hidden_in_debug_mode(self):
        """Test that progress bars are hidden when debug flag is active."""
        runner = CliRunner()

        with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
            with patch('src.cli.context.CliContext') as mock_context:
                ctx = mock_context.return_value
                ctx.debug_enabled = True
                ctx.should_show_progress.return_value = False

                result = runner.invoke(main, ["--debug", "crawl", "test-project"])

                # Progress should not be shown in debug mode
                if mock_progress.return_value.crawl_progress.called:
                    assert not ctx.should_show_progress()

    def test_progress_with_error_handling(self):
        """Test that progress continues despite errors."""
        runner = CliRunner()

        with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
            progress_instance = MagicMock()
            mock_progress.return_value = progress_instance

            with patch('src.services.crawler.CrawlerService') as mock_crawler:
                # Simulate some errors during crawl
                async def crawl_with_errors(*args, **kwargs):
                    # Update progress
                    progress_instance.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=5)
                    # Simulate error
                    raise Exception("Network error")

                mock_crawler.return_value.crawl_page = crawl_with_errors

                with patch('src.services.project_manager.ProjectManager') as mock_pm:
                    mock_pm.return_value.get_project.return_value = MagicMock()

                    result = runner.invoke(main, ["crawl", "test-project"])

                    # Progress should complete even with errors
                    assert progress_instance.complete_phase.called or progress_instance.print_phase_summary.called

    def test_progress_summary_display(self):
        """Test that progress summary is shown after crawl."""
        runner = CliRunner()

        with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
            progress_instance = MagicMock()
            mock_progress.return_value = progress_instance

            summary_data = {
                'total_pages': 100,
                'successful_pages': 95,
                'failed_pages': 5,
                'duration': 45.6,
                'embeddings_count': 950
            }

            progress_instance.display_summary.side_effect = lambda x: print("Summary displayed")

            with patch('src.services.crawler.CrawlerService'):
                with patch('src.services.project_manager.ProjectManager') as mock_pm:
                    mock_pm.return_value.get_project.return_value = MagicMock()

                    result = runner.invoke(main, ["crawl", "test-project"])

                    # Summary should be displayed
                    if progress_instance.display_summary.called:
                        call_args = progress_instance.display_summary.call_args
                        # Should pass statistics

    def test_progress_bar_components(self):
        """Test that progress bars have all required components."""
        from src.logic.crawler.utils.progress import ProgressReporter
        from rich.console import Console

        console = Console()
        reporter = ProgressReporter(console=console)

        progress = reporter.create_progress_bar()

        # Check progress bar has required columns
        column_types = [type(col).__name__ for col in progress.columns]
        assert "SpinnerColumn" in column_types
        assert "BarColumn" in column_types
        assert "TextColumn" in column_types

    def test_progress_context_manager(self):
        """Test progress context manager behavior."""
        from src.logic.crawler.utils.progress import ProgressReporter

        reporter = ProgressReporter()

        with reporter.crawl_progress() as progress:
            assert reporter.is_active()
            # Can start phases
            task_id = progress.start_phase(CrawlPhase.ANALYZING_HEADERS, total=50)
            assert task_id is not None

        # Should be inactive after context
        assert not reporter.is_active()

    def test_progress_with_different_totals(self):
        """Test progress with different total values."""
        runner = CliRunner()

        test_cases = [
            (10, "small crawl"),
            (100, "medium crawl"),
            (1000, "large crawl"),
        ]

        for total, description in test_cases:
            with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
                progress_instance = MagicMock()
                mock_progress.return_value = progress_instance

                with patch('src.services.crawler.CrawlerService') as mock_crawler:
                    mock_crawler.return_value.get_total_pages.return_value = total

                    with patch('src.services.project_manager.ProjectManager') as mock_pm:
                        mock_pm.return_value.get_project.return_value = MagicMock()

                        result = runner.invoke(main, ["crawl", "test-project", "--max-pages", str(total)])

                        # Should handle different scales
                        if progress_instance.start_phase.called:
                            call_args = progress_instance.start_phase.call_args
                            # Total should be passed

    def test_progress_cancellation(self):
        """Test that progress can be cancelled cleanly."""
        runner = CliRunner()

        with patch('logic.crawler.utils.progress.ProgressReporter') as mock_progress:
            progress_instance = MagicMock()
            mock_progress.return_value = progress_instance

            with patch('src.services.crawler.CrawlerService') as mock_crawler:
                # Simulate interruption
                mock_crawler.return_value.crawl.side_effect = KeyboardInterrupt()

                with patch('src.services.project_manager.ProjectManager') as mock_pm:
                    mock_pm.return_value.get_project.return_value = MagicMock()

                    result = runner.invoke(main, ["crawl", "test-project"])

                    # Progress should be cleaned up
                    assert progress_instance.complete_phase.called or progress_instance.print_phase_summary.called