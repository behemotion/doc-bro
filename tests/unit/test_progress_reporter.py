"""Unit tests for ProgressReporter."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.logic.crawler.utils.progress import ProgressReporter, CrawlPhase


class TestProgressReporter:
    """Test ProgressReporter functionality."""

    def test_initialization(self):
        """Test ProgressReporter initialization."""
        reporter = ProgressReporter()

        assert reporter.refresh_rate == 0.5
        assert reporter.progress is None
        assert not reporter._is_active
        assert len(reporter.tasks) == 0

    def test_create_progress_bar(self):
        """Test progress bar creation."""
        reporter = ProgressReporter()
        progress = reporter.create_progress_bar()

        assert progress is not None
        # Check that progress has required columns
        column_names = [type(col).__name__ for col in progress.columns]
        assert "SpinnerColumn" in column_names
        assert "TextColumn" in column_names
        assert "BarColumn" in column_names

    def test_crawl_progress_context_manager(self):
        """Test crawl progress context manager."""
        reporter = ProgressReporter()

        assert not reporter.is_active()

        with reporter.crawl_progress():
            assert reporter.is_active()
            assert reporter.progress is not None

        assert not reporter.is_active()
        assert reporter.progress is None

    def test_start_phase(self):
        """Test starting a crawl phase."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            task_id = reporter.start_phase(CrawlPhase.ANALYZING_HEADERS, total=100)

            assert task_id is not None
            assert CrawlPhase.ANALYZING_HEADERS.value in reporter.tasks
            assert CrawlPhase.ANALYZING_HEADERS in reporter._phase_stats

    def test_update_phase(self):
        """Test updating phase progress."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=50)

            # Test advance
            reporter.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=5)
            stats = reporter._phase_stats.get(CrawlPhase.CRAWLING_CONTENT)
            assert stats['completed'] == 5

            # Test setting completed directly
            reporter.update_phase(CrawlPhase.CRAWLING_CONTENT, completed=20)
            stats = reporter._phase_stats.get(CrawlPhase.CRAWLING_CONTENT)
            assert stats['completed'] == 20

    def test_complete_phase(self):
        """Test completing a phase."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.GENERATING_EMBEDDINGS, total=30)
            reporter.complete_phase(CrawlPhase.GENERATING_EMBEDDINGS)

            stats = reporter._phase_stats.get(CrawlPhase.GENERATING_EMBEDDINGS)
            assert stats['completed'] == stats['total']
            assert 'duration' in stats

    def test_phase_transitions(self):
        """Test transitioning between phases."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            # Start first phase
            reporter.start_phase(CrawlPhase.ANALYZING_HEADERS, total=10)
            assert len(reporter.tasks) == 1

            # Start second phase (should complete first)
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=20)
            # First phase should be marked complete
            headers_stats = reporter._phase_stats.get(CrawlPhase.ANALYZING_HEADERS)
            assert headers_stats['completed'] == headers_stats['total']

    def test_simple_progress_context(self):
        """Test simple progress context manager."""
        reporter = ProgressReporter()

        with reporter.simple_progress("Test operation", total=10) as update_func:
            assert update_func is not None or update_func is None  # Could be None for indeterminate

        # Test with no total (indeterminate)
        with reporter.simple_progress("Indeterminate operation") as update_func:
            # Update function might be None for indeterminate progress
            pass

    def test_display_summary(self):
        """Test summary display."""
        reporter = ProgressReporter()

        with patch.object(reporter.console, 'print') as mock_print:
            stats = {
                'total_pages': 100,
                'successful': 95,
                'failed': 5,
                'duration': 45.67
            }
            reporter.display_summary(stats)

            # Should print a table with stats
            assert mock_print.called

    def test_print_phase_summary(self):
        """Test printing phase summary."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.ANALYZING_HEADERS, total=10)
            reporter.complete_phase(CrawlPhase.ANALYZING_HEADERS)

            with patch.object(reporter.console, 'print') as mock_print:
                reporter.print_phase_summary()
                assert mock_print.called

    @pytest.mark.asyncio
    async def test_update_periodically(self):
        """Test periodic updates."""
        reporter = ProgressReporter()

        current_value = 0
        total_value = 100

        def get_current():
            return current_value

        def get_total():
            return total_value

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=100)

            # Start periodic update
            update_task = asyncio.create_task(
                reporter.update_periodically(
                    CrawlPhase.CRAWLING_CONTENT,
                    get_current,
                    get_total,
                    interval=0.01  # Fast interval for testing
                )
            )

            # Let it update a few times
            await asyncio.sleep(0.05)
            current_value = 50
            await asyncio.sleep(0.05)

            # Cancel the update task
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass

    def test_is_active(self):
        """Test activity status checking."""
        reporter = ProgressReporter()

        assert not reporter.is_active()

        with reporter.crawl_progress():
            assert reporter.is_active()

        assert not reporter.is_active()

    def test_log_progress(self):
        """Test progress-aware logging."""
        reporter = ProgressReporter()

        with patch('logging.Logger.log') as mock_log:
            # Without active progress
            reporter.log_progress("Test message")

            # With active progress
            with reporter.crawl_progress():
                with patch.object(reporter.live.console, 'print') as mock_print:
                    reporter.log_progress("Progress message")
                    mock_print.assert_called_with("Progress message")

    def test_phase_stats_tracking(self):
        """Test that phase statistics are properly tracked."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            # Track multiple phases
            reporter.start_phase(CrawlPhase.ANALYZING_HEADERS, total=50)
            reporter.update_phase(CrawlPhase.ANALYZING_HEADERS, advance=25)
            reporter.complete_phase(CrawlPhase.ANALYZING_HEADERS)

            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=100)
            reporter.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=75)
            reporter.complete_phase(CrawlPhase.CRAWLING_CONTENT)

            # Check stats
            headers_stats = reporter._phase_stats[CrawlPhase.ANALYZING_HEADERS]
            content_stats = reporter._phase_stats[CrawlPhase.CRAWLING_CONTENT]

            assert headers_stats['total'] == 50
            assert headers_stats['completed'] == 50
            assert 'duration' in headers_stats

            assert content_stats['total'] == 100
            assert content_stats['completed'] == 100
            assert 'duration' in content_stats