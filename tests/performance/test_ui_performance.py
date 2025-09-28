"""Performance tests for UI rendering (<100ms)"""

import pytest
import time
from unittest.mock import patch

from src.cli.interface.components.full_width_display import FullWidthProgressDisplay
from src.cli.interface.components.compact_display import CompactProgressDisplay
from src.cli.interface.services.progress_coordinator import ProgressDisplayCoordinator
from src.cli.interface.models.enums import ProcessingState, CompletionStatus


@pytest.mark.performance
class TestUIPerformance:
    """Performance tests for UI rendering components"""

    def test_full_width_display_startup_performance(self):
        """Test that full-width display starts up in <100ms"""
        start_time = time.perf_counter()

        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        end_time = time.perf_counter()
        startup_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert startup_time < 100, f"Full-width display startup took {startup_time:.2f}ms (should be <100ms)"

    def test_compact_display_startup_performance(self):
        """Test that compact display starts up in <100ms"""
        start_time = time.perf_counter()

        display = CompactProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        end_time = time.perf_counter()
        startup_time = (end_time - start_time) * 1000

        assert startup_time < 100, f"Compact display startup took {startup_time:.2f}ms (should be <100ms)"

    def test_progress_coordinator_startup_performance(self):
        """Test that progress coordinator starts up in <100ms"""
        start_time = time.perf_counter()

        coordinator = ProgressDisplayCoordinator()
        coordinator.start_operation("Test Operation", "test-project")

        end_time = time.perf_counter()
        startup_time = (end_time - start_time) * 1000

        assert startup_time < 100, f"Progress coordinator startup took {startup_time:.2f}ms (should be <100ms)"

    def test_metrics_update_performance(self):
        """Test that metrics updates complete in <50ms"""
        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        metrics = {
            "depth": "2/2",
            "pages_crawled": 150,
            "errors": 3,
            "queue": 45,
            "success_rate": 98.0
        }

        start_time = time.perf_counter()
        display.update_metrics(metrics)
        end_time = time.perf_counter()

        update_time = (end_time - start_time) * 1000

        assert update_time < 50, f"Metrics update took {update_time:.2f}ms (should be <50ms)"

    def test_current_operation_update_performance(self):
        """Test that current operation updates complete in <50ms"""
        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        long_operation = "Processing https://example.com/very/long/url/path/that/might/need/truncation/file.html"

        start_time = time.perf_counter()
        display.set_current_operation(long_operation)
        end_time = time.perf_counter()

        update_time = (end_time - start_time) * 1000

        assert update_time < 50, f"Current operation update took {update_time:.2f}ms (should be <50ms)"

    def test_embedding_status_update_performance(self):
        """Test that embedding status updates complete in <50ms"""
        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        start_time = time.perf_counter()
        display.show_embedding_status("mxbai-embed-large", "test-project", ProcessingState.PROCESSING)
        end_time = time.perf_counter()

        update_time = (end_time - start_time) * 1000

        assert update_time < 50, f"Embedding status update took {update_time:.2f}ms (should be <50ms)"

    def test_completion_summary_performance(self):
        """Test that completion summary displays in <100ms"""
        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        metrics = {
            "pages_crawled": 150,
            "pages_failed": 3,
            "documents_indexed": 147,
            "chunks_created": 1250,
            "url": "https://example.com"
        }

        start_time = time.perf_counter()
        display.complete_operation(
            "test-project",
            "crawl",
            45.7,
            metrics,
            CompletionStatus.SUCCESS
        )
        end_time = time.perf_counter()

        completion_time = (end_time - start_time) * 1000

        assert completion_time < 100, f"Completion summary took {completion_time:.2f}ms (should be <100ms)"

    def test_layout_switching_performance(self):
        """Test that layout mode switching completes in <50ms"""
        coordinator = ProgressDisplayCoordinator()

        start_time = time.perf_counter()
        coordinator.refresh_layout()
        end_time = time.perf_counter()

        switch_time = (end_time - start_time) * 1000

        assert switch_time < 50, f"Layout switching took {switch_time:.2f}ms (should be <50ms)"

    def test_multiple_rapid_updates_performance(self):
        """Test performance with rapid consecutive updates"""
        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        num_updates = 10
        start_time = time.perf_counter()

        for i in range(num_updates):
            display.update_metrics({
                "pages_crawled": i * 10,
                "errors": i,
                "queue": 100 - i * 10
            })
            display.set_current_operation(f"Processing page {i}")

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        avg_time_per_update = total_time / (num_updates * 2)  # 2 updates per iteration

        assert avg_time_per_update < 25, f"Average update time was {avg_time_per_update:.2f}ms (should be <25ms)"

    @patch('src.cli.interface.services.terminal_adapter.TerminalAdapter.get_terminal_width')
    def test_text_truncation_performance(self, mock_width):
        """Test that text truncation performs well with various terminal widths"""
        mock_width.return_value = 80

        display = FullWidthProgressDisplay()
        display.start_operation("Test Operation", "test-project")

        # Very long text that will need truncation
        very_long_text = "Processing " + "very-long-path/" * 20 + "final-file.html"

        start_time = time.perf_counter()
        display.set_current_operation(very_long_text)
        end_time = time.perf_counter()

        truncation_time = (end_time - start_time) * 1000

        assert truncation_time < 25, f"Text truncation took {truncation_time:.2f}ms (should be <25ms)"

    def test_factory_creation_performance(self):
        """Test that factory creation is fast"""
        from src.cli.interface.factories.progress_factory import ProgressFactory

        start_time = time.perf_counter()
        factory = ProgressFactory()
        coordinator = factory.create_progress_coordinator()
        end_time = time.perf_counter()

        creation_time = (end_time - start_time) * 1000

        assert creation_time < 50, f"Factory creation took {creation_time:.2f}ms (should be <50ms)"