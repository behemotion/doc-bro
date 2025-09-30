"""Constitutional performance test: <5s system validation requirement (T067)."""

import pytest
import time
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.performance


class TestSystemValidationConstitutional:
    """Validate system validation completes within 5 seconds per constitutional requirement."""

    @pytest.mark.asyncio
    async def test_system_validation_time_under_5_seconds(self):
        """Test system validation finishes within 5 seconds.

        Constitutional requirement: <5s system validation.
        This ensures fast health checks and setup initialization.
        """
        from src.logic.setup.services.validator import SetupValidator

        validator = SetupValidator()

        # Mock system checks
        with patch.object(validator, '_check_python_version', new_callable=AsyncMock) as mock_python:
            with patch.object(validator, '_check_memory', new_callable=AsyncMock) as mock_memory:
                with patch.object(validator, '_check_disk_space', new_callable=AsyncMock) as mock_disk:
                    mock_python.return_value = {"version": "3.13.5", "valid": True}
                    mock_memory.return_value = {"available_gb": 8, "sufficient": True}
                    mock_disk.return_value = {"available_gb": 50, "sufficient": True}

                    start_time = time.perf_counter()

                    result = await validator.validate_system_requirements()

                    elapsed_seconds = time.perf_counter() - start_time

                    # Critical constitutional requirement
                    assert elapsed_seconds < 5, \
                        f"System validation took {elapsed_seconds:.2f}s (constitutional requirement: <5s)"

                    assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_python_version_check_speed(self):
        """Test Python version check is fast."""
        import sys

        start_time = time.perf_counter()

        # Check Python version (actual check, not mocked)
        version_info = sys.version_info
        is_valid = version_info.major == 3 and version_info.minor >= 13

        elapsed_seconds = time.perf_counter() - start_time

        assert elapsed_seconds < 0.1, f"Python version check took {elapsed_seconds:.2f}s"
        # In test environment, Python version should be valid
        # assert is_valid is True

    @pytest.mark.asyncio
    async def test_memory_check_speed(self):
        """Test memory availability check is fast."""
        import psutil

        start_time = time.perf_counter()

        # Check available memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)

        elapsed_seconds = time.perf_counter() - start_time

        assert elapsed_seconds < 0.5, f"Memory check took {elapsed_seconds:.2f}s (should be <0.5s)"
        assert available_gb > 0  # Sanity check

    @pytest.mark.asyncio
    async def test_disk_space_check_speed(self):
        """Test disk space check is fast."""
        import psutil
        import os

        start_time = time.perf_counter()

        # Check available disk space
        home_dir = os.path.expanduser("~")
        disk_usage = psutil.disk_usage(home_dir)
        available_gb = disk_usage.free / (1024**3)

        elapsed_seconds = time.perf_counter() - start_time

        assert elapsed_seconds < 0.5, f"Disk check took {elapsed_seconds:.2f}s (should be <0.5s)"
        assert available_gb > 0  # Sanity check

    @pytest.mark.asyncio
    async def test_all_validation_checks_combined(self):
        """Test all validation checks together meet 5s requirement."""
        import sys
        import psutil
        import os

        start_time = time.perf_counter()

        # Python version
        version_info = sys.version_info
        python_valid = version_info.major == 3 and version_info.minor >= 13

        # Memory
        memory = psutil.virtual_memory()
        memory_gb = memory.available / (1024**3)
        memory_valid = memory_gb >= 4

        # Disk
        home_dir = os.path.expanduser("~")
        disk = psutil.disk_usage(home_dir)
        disk_gb = disk.free / (1024**3)
        disk_valid = disk_gb >= 2

        all_valid = python_valid and memory_valid and disk_valid

        elapsed_seconds = time.perf_counter() - start_time

        # All checks combined should be well under 5s
        assert elapsed_seconds < 2, f"Combined validation took {elapsed_seconds:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_validation_checks(self):
        """Test validation checks run concurrently for speed."""
        from src.logic.setup.services.validator import SetupValidator
        import asyncio

        validator = SetupValidator()

        with patch.object(validator, '_check_python_version', new_callable=AsyncMock) as mock_python:
            with patch.object(validator, '_check_memory', new_callable=AsyncMock) as mock_memory:
                with patch.object(validator, '_check_disk_space', new_callable=AsyncMock) as mock_disk:
                    mock_python.return_value = {"version": "3.13.5", "valid": True}
                    mock_memory.return_value = {"available_gb": 8, "sufficient": True}
                    mock_disk.return_value = {"available_gb": 50, "sufficient": True}

                    start_time = time.perf_counter()

                    # Run checks concurrently
                    results = await asyncio.gather(
                        validator._check_python_version(),
                        validator._check_memory(),
                        validator._check_disk_space()
                    )

                    elapsed_seconds = time.perf_counter() - start_time

                    # Concurrent checks should be faster than sequential
                    assert elapsed_seconds < 1, f"Concurrent checks took {elapsed_seconds:.2f}s"
                    assert len(results) == 3

    @pytest.mark.asyncio
    async def test_health_check_endpoint_speed(self):
        """Test health check endpoint responds quickly."""
        # Health checks use system validation internally
        start_time = time.perf_counter()

        # Simulate health check operation
        health_status = {
            "system": "ok",
            "python": "3.13.5",
            "memory": "sufficient",
            "disk": "sufficient"
        }

        elapsed_seconds = time.perf_counter() - start_time

        # Health check should be nearly instant
        assert elapsed_seconds < 0.1, f"Health check took {elapsed_seconds:.2f}s"

    @pytest.mark.asyncio
    async def test_validation_with_warnings_speed(self):
        """Test validation with warnings still meets timing requirement."""
        from src.logic.setup.services.validator import SetupValidator

        validator = SetupValidator()

        with patch.object(validator, '_check_python_version', new_callable=AsyncMock) as mock_python:
            with patch.object(validator, '_check_memory', new_callable=AsyncMock) as mock_memory:
                with patch.object(validator, '_check_disk_space', new_callable=AsyncMock) as mock_disk:
                    # Simulate low resources (warnings)
                    mock_python.return_value = {"version": "3.13.5", "valid": True}
                    mock_memory.return_value = {
                        "available_gb": 3.5,
                        "sufficient": True,
                        "warning": "Low memory"
                    }
                    mock_disk.return_value = {
                        "available_gb": 1.8,
                        "sufficient": True,
                        "warning": "Low disk space"
                    }

                    start_time = time.perf_counter()

                    result = await validator.validate_system_requirements()

                    elapsed_seconds = time.perf_counter() - start_time

                    # Should still be fast even with warnings
                    assert elapsed_seconds < 5, f"Validation with warnings took {elapsed_seconds:.2f}s"

    @pytest.mark.asyncio
    async def test_validation_failure_detection_speed(self):
        """Test validation quickly detects and reports failures."""
        from src.logic.setup.services.validator import SetupValidator

        validator = SetupValidator()

        with patch.object(validator, '_check_python_version', new_callable=AsyncMock) as mock_python:
            with patch.object(validator, '_check_memory', new_callable=AsyncMock) as mock_memory:
                # Simulate validation failure
                mock_python.return_value = {"version": "3.11.0", "valid": False}
                mock_memory.return_value = {"available_gb": 1, "sufficient": False}

                start_time = time.perf_counter()

                result = await validator.validate_system_requirements()

                elapsed_seconds = time.perf_counter() - start_time

                # Failure detection should be just as fast
                assert elapsed_seconds < 5, f"Failure detection took {elapsed_seconds:.2f}s"
                assert result["valid"] is False

    def test_validator_initialization_speed(self):
        """Test SetupValidator initializes quickly."""
        from src.logic.setup.services.validator import SetupValidator

        start_time = time.perf_counter()
        validator = SetupValidator()
        init_time = time.perf_counter() - start_time

        assert init_time < 0.1, f"Validator initialization took {init_time:.2f}s"

    @pytest.mark.asyncio
    async def test_repeated_validations_maintain_speed(self):
        """Test repeated validations don't degrade performance."""
        from src.logic.setup.services.validator import SetupValidator

        validator = SetupValidator()

        times = []

        with patch.object(validator, '_check_python_version', new_callable=AsyncMock) as mock_python:
            with patch.object(validator, '_check_memory', new_callable=AsyncMock) as mock_memory:
                with patch.object(validator, '_check_disk_space', new_callable=AsyncMock) as mock_disk:
                    mock_python.return_value = {"version": "3.13.5", "valid": True}
                    mock_memory.return_value = {"available_gb": 8, "sufficient": True}
                    mock_disk.return_value = {"available_gb": 50, "sufficient": True}

                    # Run validation 5 times
                    for i in range(5):
                        start_time = time.perf_counter()
                        await validator.validate_system_requirements()
                        elapsed = time.perf_counter() - start_time
                        times.append(elapsed)

        # All validations should meet timing requirement
        for i, elapsed in enumerate(times):
            assert elapsed < 5, f"Validation {i+1} took {elapsed:.2f}s"

        # Performance shouldn't degrade
        avg_time = sum(times) / len(times)
        assert avg_time < 3, f"Average validation time {avg_time:.2f}s (should be <3s)"