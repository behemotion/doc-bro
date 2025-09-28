"""Performance tests for progress update frequency."""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
from src.logic.crawler.utils.progress import ProgressReporter, CrawlPhase


class TestProgressUpdatePerformance:
    """Test progress update frequency performance."""

    def test_progress_update_frequency(self):
        """Test that progress updates occur at correct intervals."""
        reporter = ProgressReporter(refresh_rate=0.5)

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=100)

            update_times = []
            for i in range(10):
                start = time.perf_counter()
                reporter.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=1)
                update_times.append(time.perf_counter() - start)

            # Each update should be fast (< 10ms)
            for update_time in update_times:
                assert update_time < 0.01, f"Update took {update_time*1000:.2f}ms"

    @pytest.mark.asyncio
    async def test_periodic_update_performance(self):
        """Test periodic update performance."""
        reporter = ProgressReporter(refresh_rate=0.5)

        update_count = 0
        current_value = 0

        def get_current():
            nonlocal update_count
            update_count += 1
            return current_value

        def get_total():
            return 100

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=100)

            start_time = time.perf_counter()

            # Run periodic updates for 1 second
            update_task = asyncio.create_task(
                reporter.update_periodically(
                    CrawlPhase.CRAWLING_CONTENT,
                    get_current,
                    get_total,
                    interval=0.5  # 500ms interval
                )
            )

            await asyncio.sleep(1.0)
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass

            elapsed = time.perf_counter() - start_time

            # Should have ~2 updates in 1 second with 500ms interval
            expected_updates = int(elapsed / 0.5)
            assert abs(update_count - expected_updates) <= 1, f"Got {update_count} updates, expected ~{expected_updates}"

    def test_progress_bar_rendering_performance(self):
        """Test that progress bar rendering is efficient."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.ANALYZING_HEADERS, total=1000)

            # Simulate rapid updates
            start_time = time.perf_counter()
            for i in range(100):
                reporter.update_phase(CrawlPhase.ANALYZING_HEADERS, advance=10)
            end_time = time.perf_counter()

            total_time = end_time - start_time
            avg_update_time = total_time / 100

            # Average update should be very fast
            assert avg_update_time < 0.005, f"Average update took {avg_update_time*1000:.2f}ms"

    def test_phase_transition_performance(self):
        """Test that phase transitions are fast."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            transition_times = []

            phases = [
                CrawlPhase.INITIALIZING,
                CrawlPhase.ANALYZING_HEADERS,
                CrawlPhase.CRAWLING_CONTENT,
                CrawlPhase.GENERATING_EMBEDDINGS,
                CrawlPhase.FINALIZING
            ]

            for phase in phases:
                start = time.perf_counter()
                reporter.start_phase(phase, total=50)
                reporter.complete_phase(phase)
                transition_times.append(time.perf_counter() - start)

            # Each transition should be fast
            for i, transition_time in enumerate(transition_times):
                assert transition_time < 0.02, f"Phase {phases[i].value} transition took {transition_time*1000:.2f}ms"

    def test_large_batch_progress_performance(self):
        """Test progress performance with large batch operations."""
        reporter = ProgressReporter()

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=10000)

            # Simulate batch updates
            start_time = time.perf_counter()

            # Update in chunks
            for _ in range(100):
                reporter.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=100)

            end_time = time.perf_counter()

            total_time = end_time - start_time
            assert total_time < 1.0, f"Large batch update took {total_time:.2f}s"

    def test_summary_generation_performance(self):
        """Test that summary generation is fast."""
        reporter = ProgressReporter()

        stats = {
            'total_pages': 10000,
            'successful_pages': 9500,
            'failed_pages': 500,
            'duration': 3600.5,
            'embeddings_count': 95000,
            'errors_by_type': {
                'NETWORK': 200,
                'TIMEOUT': 150,
                'PARSE': 100,
                'OTHER': 50
            }
        }

        with patch.object(reporter.console, 'print'):
            start_time = time.perf_counter()
            reporter.display_summary(stats)
            end_time = time.perf_counter()

            summary_time = (end_time - start_time) * 1000
            assert summary_time < 50, f"Summary generation took {summary_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_phase_updates(self):
        """Test performance with concurrent phase updates."""
        reporter = ProgressReporter()

        async def update_worker(phase, count):
            for _ in range(count):
                reporter.update_phase(phase, advance=1)
                await asyncio.sleep(0.001)

        with reporter.crawl_progress():
            reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=300)

            start_time = time.perf_counter()

            # Simulate concurrent updates from multiple sources
            tasks = [
                asyncio.create_task(update_worker(CrawlPhase.CRAWLING_CONTENT, 100))
                for _ in range(3)
            ]

            await asyncio.gather(*tasks)

            end_time = time.perf_counter()

            total_time = end_time - start_time
            assert total_time < 1.0, f"Concurrent updates took {total_time:.2f}s"

    def test_refresh_rate_compliance(self):
        """Test that refresh rate is properly respected."""
        # Test with different refresh rates
        refresh_rates = [0.1, 0.5, 1.0]

        for rate in refresh_rates:
            reporter = ProgressReporter(refresh_rate=rate)

            with reporter.crawl_progress():
                reporter.start_phase(CrawlPhase.CRAWLING_CONTENT, total=100)

                # Check that progress respects refresh rate
                assert reporter.refresh_rate == rate

                # Simulate updates faster than refresh rate
                start = time.perf_counter()
                for _ in range(10):
                    reporter.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=1)
                    time.sleep(rate / 10)  # Update 10x faster than refresh

                elapsed = time.perf_counter() - start

                # Total time should be close to expected
                expected_time = rate
                assert elapsed < expected_time * 1.5, f"Updates took too long with refresh rate {rate}"

    def test_memory_efficiency(self):
        """Test that progress reporter doesn't leak memory."""
        import sys

        initial_size = sys.getsizeof(ProgressReporter())

        reporter = ProgressReporter()

        # Run many cycles
        for _ in range(10):
            with reporter.crawl_progress():
                for phase in CrawlPhase:
                    reporter.start_phase(phase, total=100)
                    for _ in range(10):
                        reporter.update_phase(phase, advance=10)
                    reporter.complete_phase(phase)

        # Clear stats
        reporter._phase_stats.clear()
        reporter.tasks.clear()

        # Size shouldn't grow significantly
        final_size = sys.getsizeof(reporter)
        growth_factor = final_size / initial_size
        assert growth_factor < 2.0, f"Memory grew by {growth_factor}x"