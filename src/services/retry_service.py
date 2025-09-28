"""
RetryService with exponential backoff (2s, 4s, 8s) implementation.
Provides async retry functionality for setup wizard operations.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.models.retry_policy import RetryPolicy, RetryState

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryService:
    """Async retry service with exponential backoff for setup wizard"""

    def __init__(self, retry_policy: RetryPolicy = None):
        """Initialize retry service with policy"""
        self.retry_policy = retry_policy or RetryPolicy()

    async def retry_with_backoff(
        self,
        operation: Callable[[], Awaitable[T]],
        max_attempts: int = 3,
        *args,
        **kwargs
    ) -> T:
        """Execute operation with exponential backoff retry"""
        retry_state = self.create_retry_state()
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"Attempting operation (attempt {attempt}/{max_attempts})")
                result = await operation(*args, **kwargs)
                logger.debug(f"Operation succeeded on attempt {attempt}")
                return result

            except Exception as error:
                last_error = error
                retry_state.last_error = error
                retry_state.attempt_number = attempt

                # Check if we should retry
                if not self.retry_policy.should_retry(error, attempt):
                    logger.debug(f"Not retrying error {type(error).__name__} on attempt {attempt}")
                    break

                if attempt < max_attempts:
                    delay = self.retry_policy.get_delay_seconds(attempt)
                    retry_state.next_delay_seconds = delay

                    logger.info(
                        f"Operation failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay}s: {error}"
                    )

                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {max_attempts} attempts: {error}")
                    break

        # If we get here, all attempts failed
        if last_error:
            raise last_error
        else:
            raise RuntimeError("Operation failed without specific error")

    def create_retry_state(self) -> RetryState:
        """Create new retry state for tracking attempts"""
        return RetryState(
            attempt_number=0,
            next_delay_seconds=2.0,  # First delay
            started_at=time.time()
        )

    async def retry_docker_operation(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Retry Docker-specific operations with appropriate error handling"""
        return await self.retry_with_backoff(operation, max_attempts=3)

    async def retry_network_operation(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Retry network operations with backoff"""
        return await self.retry_with_backoff(operation, max_attempts=3)

    async def retry_service_connection(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Retry service connection attempts"""
        return await self.retry_with_backoff(operation, max_attempts=3)
