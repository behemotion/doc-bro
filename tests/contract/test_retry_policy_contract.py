"""
Contract test for RetryPolicyContract interface.
These tests define the interface for retry policy implementation with exponential backoff.
They MUST FAIL initially before implementation is created.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch
from typing import Type, List
from dataclasses import dataclass

# Expected interface contracts that implementation must satisfy
@dataclass
class RetryState:
    attempt_number: int
    next_delay_seconds: float
    last_error: Exception = None
    started_at: float = None

class RetryPolicyContract:
    """Contract interface for retry policy with exponential backoff"""

    def should_retry(self, error: Exception, attempt_number: int) -> bool:
        """Determine if error should be retried based on attempt number"""
        raise NotImplementedError

    def get_delay_seconds(self, attempt_number: int) -> float:
        """Get delay for attempt number (1-based): must be 2s, 4s, 8s"""
        raise NotImplementedError

    def get_max_attempts(self) -> int:
        """Get maximum number of retry attempts (must be 3)"""
        raise NotImplementedError

    def is_retryable_error(self, error: Exception) -> bool:
        """Check if error type should be retried"""
        raise NotImplementedError

class AsyncRetryServiceContract:
    """Contract interface for async retry service implementation"""

    async def retry_with_backoff(
        self,
        operation: callable,
        max_attempts: int = 3,
        *args,
        **kwargs
    ) -> any:
        """Execute operation with exponential backoff retry"""
        raise NotImplementedError

    def create_retry_state(self) -> RetryState:
        """Create new retry state for tracking attempts"""
        raise NotImplementedError

class TestRetryPolicyContract:
    """Contract tests that RetryPolicy implementation must pass"""

    @pytest.fixture
    def retry_policy(self):
        """This will be overridden with actual implementation"""
        try:
            from src.models.retry_policy import RetryPolicy
            return RetryPolicy()
        except ImportError:
            # Should FAIL initially - no implementation exists yet
            pytest.fail("RetryPolicy implementation not found - create src/models/retry_policy.py")

    def test_exponential_backoff_sequence(self, retry_policy):
        """Test FR-012 clarification: exact delay sequence 2s, 4s, 8s"""
        # Must follow EXACT sequence from clarification
        assert retry_policy.get_delay_seconds(1) == 2.0, "First retry delay must be exactly 2.0 seconds"
        assert retry_policy.get_delay_seconds(2) == 4.0, "Second retry delay must be exactly 4.0 seconds"
        assert retry_policy.get_delay_seconds(3) == 8.0, "Third retry delay must be exactly 8.0 seconds"

    def test_max_three_attempts(self, retry_policy):
        """Test clarification: maximum 3 attempts before failing"""
        assert retry_policy.get_max_attempts() == 3, "Must allow exactly 3 attempts maximum"

        # Test attempt-based retry decisions
        test_error = Exception("transient error")

        assert retry_policy.should_retry(test_error, 1) is True, "Should retry on 1st attempt"
        assert retry_policy.should_retry(test_error, 2) is True, "Should retry on 2nd attempt"
        assert retry_policy.should_retry(test_error, 3) is False, "Should NOT retry after 3rd attempt"

    def test_retryable_error_types(self, retry_policy):
        """Test that appropriate error types are retryable"""
        # Network-related errors should be retryable
        network_errors = [
            ConnectionError("Connection failed"),
            TimeoutError("Request timeout"),
            OSError("Network unreachable")
        ]

        for error in network_errors:
            assert retry_policy.is_retryable_error(error) is True, f"{type(error).__name__} should be retryable"

        # Logic errors should NOT be retryable
        logic_errors = [
            ValueError("Invalid configuration"),
            TypeError("Invalid type"),
            KeyError("Missing key")
        ]

        for error in logic_errors:
            assert retry_policy.is_retryable_error(error) is False, f"{type(error).__name__} should NOT be retryable"

    def test_backoff_multiplier_validation(self, retry_policy):
        """Test that backoff follows expected 2x multiplier pattern"""
        delay1 = retry_policy.get_delay_seconds(1)  # 2.0
        delay2 = retry_policy.get_delay_seconds(2)  # 4.0
        delay3 = retry_policy.get_delay_seconds(3)  # 8.0

        # Verify the exponential pattern (base=2, multiplier=2)
        assert delay2 == delay1 * 2, "Second delay should be 2x first delay"
        assert delay3 == delay2 * 2, "Third delay should be 2x second delay"

    def test_attempt_number_bounds(self, retry_policy):
        """Test behavior with out-of-bounds attempt numbers"""
        # Should handle attempt numbers beyond max gracefully
        delay_beyond_max = retry_policy.get_delay_seconds(4)
        assert delay_beyond_max >= 8.0, "Delay beyond max attempts should be at least max delay"

        # Should handle zero or negative attempts
        with pytest.raises((ValueError, IndexError)):
            retry_policy.get_delay_seconds(0)

        with pytest.raises((ValueError, IndexError)):
            retry_policy.get_delay_seconds(-1)

class TestAsyncRetryServiceContract:
    """Contract tests for async retry service implementation"""

    @pytest.fixture
    def retry_service(self):
        """This will be overridden with actual implementation"""
        try:
            from src.services.retry_service import RetryService
            return RetryService()
        except ImportError:
            pytest.fail("RetryService implementation not found - create src/services/retry_service.py")

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_eventually(self, retry_service):
        """Test that retry succeeds when operation eventually succeeds"""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await retry_service.retry_with_backoff(flaky_operation, max_attempts=3)

        assert result == "success"
        assert call_count == 3  # Should have tried 3 times

    @pytest.mark.asyncio
    async def test_retry_with_backoff_fails_after_max_attempts(self, retry_service):
        """Test that retry fails after maximum attempts"""
        call_count = 0

        async def always_failing_operation():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            await retry_service.retry_with_backoff(always_failing_operation, max_attempts=3)

        assert call_count == 3  # Should have tried exactly 3 times

    @pytest.mark.asyncio
    async def test_retry_timing_follows_backoff(self, retry_service):
        """Test that retry timing follows exponential backoff pattern"""
        call_times = []

        async def timing_operation():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Timing test failure")
            return "timed_success"

        start_time = time.time()
        result = await retry_service.retry_with_backoff(timing_operation, max_attempts=3)
        total_time = time.time() - start_time

        assert result == "timed_success"
        assert len(call_times) == 3

        # Check timing intervals (allowing for some variance)
        if len(call_times) >= 2:
            first_interval = call_times[1] - call_times[0]
            assert 1.8 <= first_interval <= 2.2, f"First retry interval should be ~2s, got {first_interval:.2f}s"

        if len(call_times) >= 3:
            second_interval = call_times[2] - call_times[1]
            assert 3.8 <= second_interval <= 4.2, f"Second retry interval should be ~4s, got {second_interval:.2f}s"

    @pytest.mark.asyncio
    async def test_non_retryable_errors_fail_immediately(self, retry_service):
        """Test that non-retryable errors don't trigger retries"""
        call_count = 0

        async def operation_with_logic_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid configuration - non-retryable")

        with pytest.raises(ValueError):
            await retry_service.retry_with_backoff(operation_with_logic_error, max_attempts=3)

        assert call_count == 1  # Should have tried only once

    def test_create_retry_state(self, retry_service):
        """Test retry state creation and tracking"""
        retry_state = retry_service.create_retry_state()

        assert isinstance(retry_state, RetryState)
        assert retry_state.attempt_number == 0  # Initial state
        assert retry_state.next_delay_seconds == 2.0  # First delay
        assert retry_state.last_error is None
        assert retry_state.started_at is not None

class TestRetryPolicyPerformanceContract:
    """Performance contract tests for retry policy"""

    @pytest.fixture
    def retry_service(self):
        try:
            from src.services.retry_service import RetryService
            return RetryService()
        except ImportError:
            pytest.fail("RetryService implementation not found")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_retry_overhead_minimal(self, retry_service):
        """Test that retry logic adds minimal overhead"""
        call_count = 0

        async def fast_success_operation():
            nonlocal call_count
            call_count += 1
            return "immediate_success"

        start_time = time.time()
        result = await retry_service.retry_with_backoff(fast_success_operation, max_attempts=3)
        duration = time.time() - start_time

        assert result == "immediate_success"
        assert call_count == 1  # Should succeed on first try
        assert duration < 0.1, f"Immediate success should take <0.1s, took {duration:.2f}s"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_total_retry_time_reasonable(self, retry_service):
        """Test that total retry time matches expected backoff"""
        async def always_failing_operation():
            raise ConnectionError("Test failure")

        start_time = time.time()
        try:
            await retry_service.retry_with_backoff(always_failing_operation, max_attempts=3)
        except ConnectionError:
            pass  # Expected

        total_time = time.time() - start_time

        # Expected: ~0s + 2s + 4s = ~6s minimum (plus small execution overhead)
        assert 6.0 <= total_time <= 7.0, f"Total retry time should be ~6-7s, got {total_time:.2f}s"

class TestRetryPolicyIntegrationContract:
    """Integration contract requirements"""

    @pytest.fixture
    def retry_policy(self):
        try:
            from src.models.retry_policy import RetryPolicy
            return RetryPolicy()
        except ImportError:
            pytest.fail("RetryPolicy implementation not found")

    def test_setup_wizard_integration_contract(self, retry_policy):
        """Test that retry policy integrates with setup wizard requirements"""
        # Contract ensures retry policy can be used by setup wizard
        # for Docker operations, service connections, etc.

        # Must support the specific error types that setup wizard encounters
        docker_errors = [
            ConnectionError("Docker daemon not running"),
            TimeoutError("Container startup timeout"),
            OSError("Docker socket not available")
        ]

        for error in docker_errors:
            # All these should be retryable in setup context
            assert retry_policy.is_retryable_error(error) is True

        # Must follow the exact timing from clarification
        assert retry_policy.get_delay_seconds(1) == 2.0
        assert retry_policy.get_delay_seconds(2) == 4.0
        assert retry_policy.get_delay_seconds(3) == 8.0

    def test_error_context_preservation(self, retry_policy):
        """Test that error context is preserved across retries"""
        test_error = ConnectionError("Original error message")

        # Policy should be able to examine error details
        assert retry_policy.is_retryable_error(test_error) is True

        # Error information should be preserved for logging/debugging
        assert str(test_error) == "Original error message"