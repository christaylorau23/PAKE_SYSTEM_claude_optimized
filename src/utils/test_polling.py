#!/usr/bin/env python3
"""PAKE System - Robust Test Polling Utilities
Enterprise-grade polling mechanisms for reliable test execution.

This module provides robust polling mechanisms to replace fixed delays
in tests, making them resilient to timing variations in CI environments.

Key Features:
- Configurable timeout and interval settings
- Exponential backoff for better performance
- Comprehensive error handling and logging
- Type-safe async/await patterns
- Circuit breaker patterns for failing services
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PollingConfig:
    """Configuration for polling operations."""

    timeout_seconds: float = 30.0
    interval_seconds: float = 0.1
    max_interval_seconds: float = 2.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 1.5
    max_retries: int | None = None
    log_attempts: bool = True


@dataclass(frozen=True)
class PollingResult:
    """Result of a polling operation."""

    success: bool
    value: Any | None = None
    attempts: int = 0
    total_time: float = 0.0
    error: str | None = None


class RobustPoller:
    """Robust polling utility for test operations.

    Provides reliable polling mechanisms that adapt to different
    execution environments and service response times.
    """

    def __init__(self) -> None:
        self.config = config or PollingConfig()
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60.0
        self._circuit_breaker_state = {}

    async def poll_condition(
        self,
        condition_func: Callable[[], Awaitable[bool]],
        config: PollingConfig | None = None,
        operation_name: str = "poll_condition",
    ) -> PollingResult:
        """Poll until a condition becomes true.

        Args:
            condition_func: Async function that returns True when condition is met
            config: Polling configuration (uses instance config if None)
            operation_name: Name for logging purposes

        Returns:
            PollingResult with success status and metadata
        """
        config = config or self.config
        start_time = time.time()
        attempts = 0
        current_interval = config.interval_seconds

        logger.debug("Starting polling for %s", operation_name)

        while True:
            attempts += 1

            try:
                # Check circuit breaker
                if self._is_circuit_open(operation_name):
                    return PollingResult(
                        success=False,
                        attempts=attempts,
                        total_time=time.time() - start_time,
                        error="Circuit breaker is open",
                    )

                # Execute condition check
                result = await condition_func()

                if result:
                    total_time = time.time() - start_time
                    logger.debug(
                        "Polling succeeded for %s after %s attempts in %ss", operation_name, attempts, f"{total_time:.2f}"
                    )

                    return PollingResult(
                        success=True,
                        value=result,
                        attempts=attempts,
                        total_time=total_time,
                    )

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= config.timeout_seconds:
                    return PollingResult(
                        success=False,
                        attempts=attempts,
                        total_time=elapsed,
                        error=f"Timeout after {config.timeout_seconds}s",
                    )

                # Check max retries
                if config.max_retries and attempts >= config.max_retries:
                    return PollingResult(
                        success=False,
                        attempts=attempts,
                        total_time=elapsed,
                        error=f"Max retries ({config.max_retries}) exceeded",
                    )

                # Log attempt if enabled
                if config.log_attempts and attempts % 10 == 0:
                    logger.debug(
                        "Polling attempt %s for %s (elapsed: %ss)", attempts, operation_name, elapsed:.2f
                    )

                # Wait before next attempt
                await asyncio.sleep(current_interval)

                # Update interval with exponential backoff
                if config.exponential_backoff:
                    current_interval = min(
                        current_interval * config.backoff_multiplier,
                        config.max_interval_seconds,
                    )

            except (ValueError, RuntimeError) as e:
                logger.warning(
                    "Polling attempt %s failed for %s: %s", attempts, operation_name, e
                )

                # Record failure for circuit breaker
                self._record_failure(operation_name)

                # Check if we should continue
                elapsed = time.time() - start_time
                if elapsed >= config.timeout_seconds:
                    return PollingResult(
                        success=False,
                        attempts=attempts,
                        total_time=elapsed,
                        error=f"Exception during polling: {str(e)}",
                    )

                # Wait before retry
                await asyncio.sleep(current_interval)

    async def poll_value(
        self,
        value_func: Callable[[], Awaitable[Any]],
        expected_value: Any,
        config: PollingConfig | None = None,
        operation_name: str = "poll_value",
    ) -> PollingResult:
        """Poll until a function returns an expected value.

        Args:
            value_func: Async function that returns a value
            expected_value: The value we're waiting for
            config: Polling configuration
            operation_name: Name for logging purposes

        Returns:
            PollingResult with success status and actual value
        """

        async def condition(self) -> None:
            value = await value_func()
            return value == expected_value

        result = await self.poll_condition(condition, config, operation_name)

        if result.success:
            # Get the actual value for the result
            actual_value = await value_func()
            return PollingResult(
                success=True,
                value=actual_value,
                attempts=result.attempts,
                total_time=result.total_time,
            )

        return result

    async def poll_database_record(
        self,
        db_manager,
        query: str,
        params: tuple,
        expected_count: int = 1,
        config: PollingConfig | None = None,
        operation_name: str = "poll_database_record",
    ) -> PollingResult:
        """Poll until database query returns expected number of records.

        Args:
            db_manager: Database connection manager
            query: SQL query to execute
            params: Query parameters
            expected_count: Expected number of records
            config: Polling configuration
            operation_name: Name for logging purposes

        Returns:
            PollingResult with success status and records
        """

        async def check_records(self) -> None:
            records = await db_manager.fetch_all(query, *params)
            return len(records) >= expected_count

        result = await self.poll_condition(check_records, config, operation_name)

        if result.success:
            records = await db_manager.fetch_all(query, *params)
            return PollingResult(
                success=True,
                value=records,
                attempts=result.attempts,
                total_time=result.total_time,
            )

        return result

    async def poll_cache_value(
        self,
        cache_manager,
        namespace: str,
        key: str,
        expected_value: Any | None = None,
        config: PollingConfig | None = None,
        operation_name: str = "poll_cache_value",
    ) -> PollingResult:
        """Poll until cache contains expected value.

        Args:
            cache_manager: Cache manager instance
            namespace: Cache namespace
            key: Cache key
            expected_value: Expected value (None means any non-None value)
            config: Polling configuration
            operation_name: Name for logging purposes

        Returns:
            PollingResult with success status and cached value
        """

        async def check_cache(self) -> None:
            value = await cache_manager.get(namespace, key)
            if expected_value is None:
                return value is not None
            return value == expected_value

        result = await self.poll_condition(check_cache, config, operation_name)

        if result.success:
            value = await cache_manager.get(namespace, key)
            return PollingResult(
                success=True,
                value=value,
                attempts=result.attempts,
                total_time=result.total_time,
            )

        return result

    async def poll_message_received(
        self,
        message_bus,
        expected_count: int,
        received_messages: list,
        config: PollingConfig | None = None,
        operation_name: str = "poll_message_received",
    ) -> PollingResult:
        """Poll until expected number of messages are received.

        Args:
            message_bus: Message bus instance
            expected_count: Expected number of messages
            received_messages: List to check for received messages
            config: Polling configuration
            operation_name: Name for logging purposes

        Returns:
            PollingResult with success status and message count
        """

        async def check_messages(self) -> None:
            return len(received_messages) >= expected_count

        result = await self.poll_condition(check_messages, config, operation_name)

        if result.success:
            return PollingResult(
                success=True,
                value=len(received_messages),
                attempts=result.attempts,
                total_time=result.total_time,
            )

        return result

    def _is_circuit_open(self, operation_name: str) -> bool:
        """Check if circuit breaker is open for an operation."""
        if operation_name not in self._circuit_breaker_state:
            return False

        state = self._circuit_breaker_state[operation_name]
        if state["failures"] < self._circuit_breaker_threshold:
            return False

        # Check if timeout has passed
        if time.time() - state["last_failure"] > self._circuit_breaker_timeout:
            # Reset circuit breaker
            del self._circuit_breaker_state[operation_name]
            return False

        return True

    def _record_failure(self) -> None:
        """Record a failure for circuit breaker."""
        if operation_name not in self._circuit_breaker_state:
            self._circuit_breaker_state[operation_name] = {
                "failures": 0,
                "last_failure": 0,
            }

        state = self._circuit_breaker_state[operation_name]
        state["failures"] += 1
        state["last_failure"] = time.time()


# Convenience functions for common polling patterns
async def poll_until_true(
    condition_func: Callable[[], Awaitable[bool]],
    timeout: float = 30.0,
    interval: float = 0.1,
    operation_name: str = "poll_until_true",
) -> bool:
    """Convenience function to poll until condition is true.

    Returns:
        True if condition became true, False if timeout
    """
    config = PollingConfig(timeout_seconds=timeout, interval_seconds=interval)

    poller = RobustPoller(config)
    result = await poller.poll_condition(condition_func, operation_name=operation_name)
    return result.success


async def poll_until_equal(
    value_func: Callable[[], Awaitable[Any]],
    expected_value: Any,
    timeout: float = 30.0,
    interval: float = 0.1,
    operation_name: str = "poll_until_equal",
) -> Any | None:
    """Convenience function to poll until value equals expected.

    Returns:
        Actual value if successful, None if timeout
    """
    config = PollingConfig(timeout_seconds=timeout, interval_seconds=interval)

    poller = RobustPoller(config)
    result = await poller.poll_value(
        value_func, expected_value, operation_name=operation_name
    )
    return result.value if result.success else None


async def poll_database_ready(
    db_manager, timeout: float = 30.0, operation_name: str = "poll_database_ready"
) -> bool:
    """Convenience function to poll until database is ready.

    Returns:
        True if database is ready, False if timeout
    """

    async def check_db(self) -> None:
        try:
            await db_manager.execute_query("SELECT 1")
            return True
        except Exception:
            return False

    return await poll_until_true(check_db, timeout, operation_name=operation_name)


async def poll_cache_ready(
    cache_manager, timeout: float = 30.0, operation_name: str = "poll_cache_ready"
) -> bool:
    """Convenience function to poll until cache is ready.

    Returns:
        True if cache is ready, False if timeout
    """

    async def check_cache(self) -> None:
        try:
            await cache_manager.set("test", "ready", "true", ttl=1)
            await cache_manager.delete("test", "ready")
            return True
        except Exception:
            return False

    return await poll_until_true(check_cache, timeout, operation_name=operation_name)


# Pytest fixtures for common polling scenarios
@pytest.fixture()
def robust_poller(self) -> None:
    """Pytest fixture providing a RobustPoller instance."""
    return RobustPoller()


@pytest.fixture()
def fast_poller(self) -> None:
    """Pytest fixture providing a fast-polling RobustPoller instance."""
    config = PollingConfig(
        timeout_seconds=5.0, interval_seconds=0.05, max_interval_seconds=0.5
    )
    return RobustPoller(config)


@pytest.fixture()
def slow_poller(self) -> None:
    """Pytest fixture providing a slow-polling RobustPoller instance."""
    config = PollingConfig(
        timeout_seconds=60.0, interval_seconds=1.0, max_interval_seconds=5.0
    )
    return RobustPoller(config)


# Example usage and testing
if __name__ == "__main__":

    async def example_usage(self) -> None:
        """Example demonstrating robust polling usage."""
        # Create poller with custom configuration
        config = PollingConfig(
            timeout_seconds=10.0, interval_seconds=0.1, exponential_backoff=True
        )
        poller = RobustPoller(config)

        # Example 1: Poll until condition is true
        counter = 0

        async def increment_counter(self) -> None:
            nonlocal counter
            counter += 1
            return counter >= 5

        result = await poller.poll_condition(
            increment_counter, operation_name="counter_example"
        )
        print(f"Counter polling: {result}")

        # Example 2: Poll until value equals expected
        async def get_value(self) -> None:
            return counter

        result = await poller.poll_value(get_value, 5, operation_name="value_example")
        print(f"Value polling: {result}")

        # Example 3: Using convenience functions
        success = await poll_until_true(increment_counter, timeout=5.0)
        print(f"Convenience polling: {success}")

    # Run example
    asyncio.run(example_usage())