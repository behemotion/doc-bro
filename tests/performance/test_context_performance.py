"""Performance tests for context detection (<500ms requirement) - T057."""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.services.context_service import ContextService
from src.models.command_context import CommandContext
from src.models.configuration_state import ConfigurationState


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
        # Mock the database manager's get_connection method
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call checks cache (returns None - cache miss)
        # Second call gets shelf data
        # Third call gets box count
        mock_cursor.fetchone = AsyncMock(side_effect=[
            None,  # Cache miss
            (1, "performance-shelf", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),  # Shelf data
            (0,)  # Box count
        ])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
            start_time = time.perf_counter()
            context = await context_service.check_shelf_exists("performance-shelf")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 500, f"Context check took {elapsed_ms:.2f}ms (threshold: 500ms)"
            assert context.entity_name == "performance-shelf"

    @pytest.mark.asyncio
    async def test_box_context_check_response_time(self, context_service):
        """Test box existence check completes within 500ms."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call checks cache (returns None - cache miss)
        # Second call gets box data
        mock_cursor.fetchone = AsyncMock(side_effect=[
            None,  # Cache miss
            (1, "performance-box", "drag", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())  # Box data
        ])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
            start_time = time.perf_counter()
            context = await context_service.check_box_exists("performance-box")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 500, f"Context check took {elapsed_ms:.2f}ms (threshold: 500ms)"
            assert context.entity_name == "performance-box"

    @pytest.mark.asyncio
    async def test_context_check_with_cache_hit(self, context_service):
        """Test cached context lookups are significantly faster."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # First call returns data from database (cache miss)
        # Second call returns data from cache (cache hit)
        config_state = ConfigurationState(
            is_configured=True,
            has_content=False,
            configuration_version="1.0",
            setup_completed_at=datetime.now(timezone.utc),
            needs_migration=False
        )
        cache_row = ("cached-shelf", "shelf", True, True, config_state.model_dump_json(), datetime.now(timezone.utc).isoformat(), "0 boxes", (datetime.now(timezone.utc)).isoformat())

        mock_cursor.fetchone = AsyncMock(side_effect=[
            None,  # No cache on first call
            (1, "cached-shelf", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),  # DB query
            (0,),  # box count
            cache_row  # Cache hit on second call
        ])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
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
            assert cached_call_ms < 100, f"Cached lookup should be <100ms, was {cached_call_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_multiple_sequential_context_checks(self, context_service):
        """Test multiple context checks maintain performance."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock responses for 5 different shelves
        responses = []
        for i in range(5):
            responses.append(None)  # Cache miss
            responses.append((i+1, f"shelf-{i}", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
            responses.append((0,))  # box count

        mock_cursor.fetchone = AsyncMock(side_effect=responses)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
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
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock responses for 10 concurrent shelves
        responses = []
        for i in range(10):
            responses.append(None)  # Cache miss
            responses.append((i+1, f"concurrent-shelf-{i}", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
            responses.append((0,))  # box count

        mock_cursor.fetchone = AsyncMock(side_effect=responses)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
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
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock responses for 15 shelves (3 batches of 5)
        responses = []
        for batch in range(3):
            for i in range(5):
                responses.append(None)  # Cache miss
                responses.append((batch*5+i+1, f"load-shelf-{batch}-{i}", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
                responses.append((0,))  # box count

        mock_cursor.fetchone = AsyncMock(side_effect=responses)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
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
    async def test_context_check_memory_efficiency(self, context_service):
        """Test context checks don't leak memory with repeated calls."""
        import tracemalloc

        tracemalloc.start()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock responses for 100 shelves
        responses = []
        for i in range(100):
            responses.append(None)  # Cache miss
            responses.append((i+1, f"memory-shelf-{i}", None, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
            responses.append((0,))  # box count

        mock_cursor.fetchone = AsyncMock(side_effect=responses)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch.object(context_service.db_manager, 'get_connection', return_value=mock_conn):
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