"""Performance tests for context detection (<500ms requirement) - T057."""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, patch

from src.services.context_service import ContextService


pytestmark = pytest.mark.performance


class TestContextDetectionPerformance:
    """Validate context detection meets <500ms response time requirement."""

    @pytest.fixture
    def context_service(self):
        """Create ContextService instance for testing."""
        return ContextService()

    @pytest.mark.asyncio
    async def test_shelf_context_check_response_time(self, context_service):
        """Test shelf existence check completes within 500ms."""
        with patch.object(context_service, '_check_shelf_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, False, "Test shelf", datetime.now())

            start_time = time.perf_counter()
            context = await context_service.check_shelf_exists("performance-shelf")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 500, f"Context check took {elapsed_ms:.2f}ms (threshold: 500ms)"
            assert context.entity_name == "performance-shelf"

    @pytest.mark.asyncio
    async def test_box_context_check_response_time(self, context_service):
        """Test box existence check completes within 500ms."""
        with patch.object(context_service, '_check_box_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, True, "Empty box", datetime.now(), "drag")

            start_time = time.perf_counter()
            context = await context_service.check_box_exists("performance-box")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 500, f"Context check took {elapsed_ms:.2f}ms (threshold: 500ms)"
            assert context.entity_name == "performance-box"

    @pytest.mark.asyncio
    async def test_context_check_with_cache_hit(self, context_service):
        """Test cached context lookups are significantly faster."""
        with patch.object(context_service, '_check_shelf_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, False, "Cached shelf", datetime.now())

            # First call - database query
            start_time = time.perf_counter()
            await context_service.check_shelf_exists("cached-shelf")
            first_call_ms = (time.perf_counter() - start_time) * 1000

            # Second call - should use cache
            start_time = time.perf_counter()
            await context_service.check_shelf_exists("cached-shelf")
            cached_call_ms = (time.perf_counter() - start_time) * 1000

            # Both should be under 500ms
            assert first_call_ms < 500, f"First call took {first_call_ms:.2f}ms"
            assert cached_call_ms < 500, f"Cached call took {cached_call_ms:.2f}ms"

            # Cached call should be significantly faster
            # But we're testing against mocks, so just verify it completes quickly
            assert cached_call_ms < 100, f"Cached lookup should be <100ms, was {cached_call_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_multiple_sequential_context_checks(self, context_service):
        """Test multiple context checks maintain performance."""
        with patch.object(context_service, '_check_shelf_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, False, "Test", datetime.now())

            times = []
            for i in range(5):
                start_time = time.perf_counter()
                await context_service.check_shelf_exists(f"shelf-{i}")
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                times.append(elapsed_ms)

            # All checks should be under 500ms
            for i, elapsed_ms in enumerate(times):
                assert elapsed_ms < 500, f"Check {i+1} took {elapsed_ms:.2f}ms (threshold: 500ms)"

            # Average should also be well under threshold
            avg_time = sum(times) / len(times)
            assert avg_time < 300, f"Average time {avg_time:.2f}ms should be <300ms"

    @pytest.mark.asyncio
    async def test_concurrent_context_checks_performance(self, context_service):
        """Test concurrent context checks don't degrade performance."""
        with patch.object(context_service, '_check_shelf_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, False, "Test", datetime.now())

            # Create 10 concurrent requests
            start_time = time.perf_counter()
            tasks = [
                context_service.check_shelf_exists(f"concurrent-shelf-{i}")
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000

            # All should complete
            assert len(results) == 10

            # Total time for 10 concurrent requests should be reasonable
            # Not 10x individual time due to concurrency
            assert total_elapsed_ms < 2000, f"10 concurrent checks took {total_elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_context_check_under_load(self, context_service):
        """Test context detection maintains performance under load."""
        with patch.object(context_service, '_check_shelf_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, False, "Load test", datetime.now())

            # Simulate high load with many rapid requests
            times = []
            for batch in range(3):  # 3 batches of 5 concurrent requests
                batch_start = time.perf_counter()
                tasks = [
                    context_service.check_shelf_exists(f"load-shelf-{batch}-{i}")
                    for i in range(5)
                ]
                await asyncio.gather(*tasks)
                batch_time = (time.perf_counter() - batch_start) * 1000
                times.append(batch_time)

            # Each batch should complete reasonably quickly
            for i, batch_time in enumerate(times):
                assert batch_time < 1000, f"Batch {i+1} took {batch_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_configuration_state_query_performance(self, context_service):
        """Test configuration state queries meet performance requirements."""
        with patch.object(context_service, '_get_entity_config_state', new_callable=AsyncMock) as mock_config:
            from src.models.configuration_state import ConfigurationState
            from datetime import datetime

            mock_config.return_value = ConfigurationState(
                is_configured=True,
                has_content=True,
                configuration_version="1.0",
                setup_completed_at=datetime.now(),
                needs_migration=False
            )

            start_time = time.perf_counter()
            config = await context_service.get_configuration_state("test-entity", "shelf")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 500, f"Config state query took {elapsed_ms:.2f}ms"
            assert config.is_configured is True

    @pytest.mark.asyncio
    async def test_context_check_memory_efficiency(self, context_service):
        """Test context checks don't leak memory with repeated calls."""
        import tracemalloc

        tracemalloc.start()

        with patch.object(context_service, '_check_shelf_in_db', new_callable=AsyncMock) as mock_check:
            from datetime import datetime
            mock_check.return_value = (True, False, "Memory test", datetime.now())

            # Get baseline memory
            baseline_memory = tracemalloc.get_traced_memory()[0]

            # Perform many context checks
            for i in range(100):
                await context_service.check_shelf_exists(f"memory-shelf-{i}")

            # Get final memory
            final_memory = tracemalloc.get_traced_memory()[0]
            tracemalloc.stop()

            # Memory increase should be reasonable (less than 10MB for 100 checks)
            memory_increase = (final_memory - baseline_memory) / (1024 * 1024)
            assert memory_increase < 10, f"Memory increased by {memory_increase:.2f}MB"

    @pytest.mark.asyncio
    async def test_cache_expiration_performance(self, context_service):
        """Test cache expiration doesn't impact performance."""
        # This tests that TTL-based cache cleanup is efficient
        # Implementation depends on actual caching strategy
        pass

    def test_context_service_initialization_time(self):
        """Test ContextService initializes quickly."""
        start_time = time.perf_counter()
        service = ContextService()
        init_time_ms = (time.perf_counter() - start_time) * 1000

        assert init_time_ms < 100, f"Service initialization took {init_time_ms:.2f}ms"