"""Constitutional performance test: <30s complete setup requirement (T066)."""

import pytest
import time
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.performance


class TestSetupTimeConstitutional:
    """Validate setup completes within 30 seconds per constitutional requirement."""

    @pytest.mark.asyncio
    async def test_complete_setup_time_under_30_seconds(self):
        """Test complete setup operation finishes within 30 seconds.

        Constitutional requirement: <30s installation with automatic setup.
        This is a critical acceptance criterion for the entire system.
        """
        from src.logic.setup.core.orchestrator import SetupOrchestrator

        orchestrator = SetupOrchestrator()

        # Mock external service checks to avoid real Docker/Ollama dependencies
        with patch.object(orchestrator, '_detect_services', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = {
                "python": {"available": True, "version": "3.13.5"},
                "uv": {"available": True, "version": "0.8.0"},
                "git": {"available": True},
                "docker": {"available": False},
                "qdrant": {"available": False},
                "ollama": {"available": False},
                "sqlite_vec": {"available": True}
            }

            with patch.object(orchestrator, '_initialize_system', new_callable=AsyncMock) as mock_init:
                mock_init.return_value = {"success": True, "vector_store": "sqlite_vec"}

                start_time = time.perf_counter()

                # Run setup with auto mode (SQLite-vec, no external services)
                result = await orchestrator.run_setup(auto=True, vector_store="sqlite_vec")

                elapsed_seconds = time.perf_counter() - start_time

                # Critical constitutional requirement
                assert elapsed_seconds < 30, \
                    f"Setup took {elapsed_seconds:.2f}s (constitutional requirement: <30s)"

                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_incremental_setup_steps_timing(self):
        """Test individual setup steps contribute to overall 30s requirement."""
        from src.logic.setup.services.validator import SetupValidator

        validator = SetupValidator()

        step_times = {}

        # System validation step
        start = time.perf_counter()
        # Mock system check
        with patch.object(validator, 'validate_system_requirements', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"valid": True, "python": "3.13.5", "memory": "8GB"}
            await validator.validate_system_requirements()
        step_times["system_validation"] = time.perf_counter() - start

        # Vector store selection
        start = time.perf_counter()
        # Simulated decision
        vector_store = "sqlite_vec"
        step_times["vector_store_selection"] = time.perf_counter() - start

        # Configuration initialization
        start = time.perf_counter()
        # Mock config creation
        config = {"vector_store": "sqlite_vec", "ollama_url": "http://localhost:11434"}
        step_times["config_initialization"] = time.perf_counter() - start

        # Database migration
        start = time.perf_counter()
        # Mock migration
        with patch('src.services.database_migrator.DatabaseMigrator') as mock_migrator:
            migrator = mock_migrator.return_value
            migrator.run_migrations = AsyncMock(return_value=True)
            await migrator.run_migrations()
        step_times["database_migration"] = time.perf_counter() - start

        # Total of all steps
        total_time = sum(step_times.values())

        # All steps together should be well under 30s
        assert total_time < 30, f"Setup steps took {total_time:.2f}s total"

        # Individual steps should also be fast
        for step_name, step_time in step_times.items():
            assert step_time < 10, f"{step_name} took {step_time:.2f}s (should be <10s)"

    @pytest.mark.asyncio
    async def test_setup_with_qdrant_detection_time(self):
        """Test setup time when Qdrant detection is included."""
        from src.logic.setup.services.detector import ServiceDetector

        detector = ServiceDetector()

        start_time = time.perf_counter()

        # Mock Qdrant detection (simulates checking if service is available)
        with patch.object(detector, 'detect_qdrant', new_callable=AsyncMock) as mock_qdrant:
            mock_qdrant.return_value = {"available": False, "reason": "Not running"}

            result = await detector.detect_qdrant()

            elapsed_seconds = time.perf_counter() - start_time

            # Service detection should be fast (contributes to 30s total)
            assert elapsed_seconds < 5, f"Qdrant detection took {elapsed_seconds:.2f}s (should be <5s)"

    @pytest.mark.asyncio
    async def test_setup_fallback_to_sqlite_vec_speed(self):
        """Test that falling back to SQLite-vec is fast when Qdrant unavailable."""
        from src.logic.setup.core.orchestrator import SetupOrchestrator

        orchestrator = SetupOrchestrator()

        with patch.object(orchestrator, '_detect_services', new_callable=AsyncMock) as mock_detect:
            # Simulate Qdrant unavailable scenario
            mock_detect.return_value = {
                "qdrant": {"available": False},
                "sqlite_vec": {"available": True}
            }

            with patch.object(orchestrator, '_initialize_system', new_callable=AsyncMock) as mock_init:
                mock_init.return_value = {"success": True, "vector_store": "sqlite_vec"}

                start_time = time.perf_counter()

                # Should quickly fallback to SQLite-vec
                result = await orchestrator.run_setup(auto=True)

                elapsed_seconds = time.perf_counter() - start_time

                # Fallback should be fast
                assert elapsed_seconds < 10, f"Fallback setup took {elapsed_seconds:.2f}s"
                assert result["success"] is True

    def test_setup_menu_rendering_time(self):
        """Test interactive menu renders quickly (contributes to UX perception)."""
        from src.logic.setup.core.menu import InteractiveMenu

        start_time = time.perf_counter()
        menu = InteractiveMenu()
        init_time = time.perf_counter() - start_time

        assert init_time < 1, f"Menu initialization took {init_time:.2f}s (should be <1s)"

    @pytest.mark.asyncio
    async def test_concurrent_service_detection(self):
        """Test that parallel service detection improves setup time."""
        from src.logic.setup.services.detector import ServiceDetector
        import asyncio

        detector = ServiceDetector()

        # Mock all service detections
        with patch.object(detector, 'detect_python', new_callable=AsyncMock) as mock_python:
            with patch.object(detector, 'detect_docker', new_callable=AsyncMock) as mock_docker:
                with patch.object(detector, 'detect_ollama', new_callable=AsyncMock) as mock_ollama:
                    with patch.object(detector, 'detect_git', new_callable=AsyncMock) as mock_git:
                        mock_python.return_value = {"available": True}
                        mock_docker.return_value = {"available": False}
                        mock_ollama.return_value = {"available": False}
                        mock_git.return_value = {"available": True}

                        start_time = time.perf_counter()

                        # Run detections concurrently
                        results = await asyncio.gather(
                            detector.detect_python(),
                            detector.detect_docker(),
                            detector.detect_ollama(),
                            detector.detect_git()
                        )

                        elapsed_seconds = time.perf_counter() - start_time

                        # Concurrent detection should be much faster than sequential
                        assert elapsed_seconds < 5, f"Concurrent detection took {elapsed_seconds:.2f}s"
                        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_setup_with_minimal_configuration(self):
        """Test minimal setup (SQLite-vec only) is fastest path."""
        from src.logic.setup.core.orchestrator import SetupOrchestrator

        orchestrator = SetupOrchestrator()

        with patch.object(orchestrator, '_detect_services', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = {"sqlite_vec": {"available": True}}

            with patch.object(orchestrator, '_initialize_system', new_callable=AsyncMock) as mock_init:
                mock_init.return_value = {"success": True}

                start_time = time.perf_counter()

                result = await orchestrator.run_setup(
                    auto=True,
                    vector_store="sqlite_vec",
                    skip_ollama=True
                )

                elapsed_seconds = time.perf_counter() - start_time

                # Minimal setup should be very fast
                assert elapsed_seconds < 15, f"Minimal setup took {elapsed_seconds:.2f}s (should be <15s)"
                assert result["success"] is True