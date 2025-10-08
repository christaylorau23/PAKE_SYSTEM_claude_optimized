#!/usr/bin/env python3
"""Async Debugging Utilities and Test Helpers for PAKE System
Comprehensive tools for debugging asynchronous code, race conditions, and flaky tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import functools
import logging
import os
import time
from typing import Any, Dict, List, Optional

import pytest

# Configure logging for async debugging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("PYTHONASYNCIODEBUG") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("async_debug")


@dataclass
class AsyncDebugConfig:
    """Configuration for async debugging utilities."""

    enable_debug_mode: bool = field(
        default_factory=lambda: bool(os.getenv("PYTHONASYNCIODEBUG"))
    )
    log_slow_operations: bool = True
    slow_operation_threshold: float = 0.1  # seconds
    log_race_conditions: bool = True
    log_unawaited_coroutines: bool = True
    log_context_switches: bool = False
    max_concurrent_tasks: int = 100
    timeout_warning_threshold: float = 5.0  # seconds
    enable_performance_profiling: bool = False


@dataclass
class AsyncOperationMetrics:
    """Metrics for async operations."""

    operation_name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    success: bool = True
    error: str | None = None
    context_switches: int = 0
    concurrent_tasks: int = 0
    memory_usage: float | None = None


class AsyncDebugCollector:
    """Collects and analyzes async debugging information."""

    def __init__(self, config: AsyncDebugConfig | None = None) -> None:
        self.config = config or AsyncDebugConfig()
        self.operations: list[AsyncOperationMetrics] = []
        self.race_conditions: list[dict[str, Any]] = []
        self.unawaited_coroutines: list[str] = []
        self.slow_operations: list[AsyncOperationMetrics] = []
        self._lock = asyncio.Lock()

    async def record_operation(self, operation: AsyncOperationMetrics) -> None:
        """Record an async operation."""
        async with self._lock:
            self.operations.append(operation)

            # Check for slow operations
            if (
                operation.duration
                and operation.duration > self.config.slow_operation_threshold
            ):
                self.slow_operations.append(operation)
                if self.config.log_slow_operations:
                    logger.warning(
                        "Slow async operation detected: %s took %.3fs",
                        operation.operation_name,
                        operation.duration,
                    )

    async def record_race_condition(self, details: dict[str, Any]) -> None:
        """Record a potential race condition."""
        async with self._lock:
            self.race_conditions.append(details)
            if self.config.log_race_conditions:
                logger.warning("Potential race condition detected: %s", details)

    async def record_unawaited_coroutine(self, coroutine_name: str) -> None:
        """Record an unawaited coroutine."""
        async with self._lock:
            self.unawaited_coroutines.append(coroutine_name)
            if self.config.log_unawaited_coroutines:
                logger.warning("Unawaited coroutine detected: %s", coroutine_name)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of async debugging information."""
        return {
            "total_operations": len(self.operations),
            "slow_operations": len(self.slow_operations),
            "race_conditions": len(self.race_conditions),
            "unawaited_coroutines": len(self.unawaited_coroutines),
            "average_duration": (
                sum(op.duration for op in self.operations if op.duration)
                / len(self.operations)
                if self.operations
                else 0
            ),
            "max_duration": (
                max(op.duration for op in self.operations if op.duration)
                if self.operations
                else 0
            ),
            "error_rate": (
                sum(1 for op in self.operations if not op.success)
                / len(self.operations)
                if self.operations
                else 0
            ),
        }


# Global debug collector
_debug_collector = AsyncDebugCollector()


def get_debug_collector() -> AsyncDebugCollector:
    """Get the global debug collector."""
    return _debug_collector


class AsyncDebugContext:
    """Context manager for async debugging."""

    def __init__(
        self, operation_name: str, config: AsyncDebugConfig | None = None
    ) -> None:
        self.operation_name = operation_name
        self.config = config or AsyncDebugConfig()
        self.start_time: float | None = None
        self.metrics: AsyncOperationMetrics | None = None

    async def __aenter__(self) -> "AsyncDebugContext":
        self.start_time = time.time()
        self.metrics = AsyncOperationMetrics(
            operation_name=self.operation_name, start_time=self.start_time
        )
        return self

    async def __aexit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None
    ) -> None:
        if self.metrics:
            self.metrics.end_time = time.time()
            self.metrics.duration = self.metrics.end_time - self.metrics.start_time
            self.metrics.success = exc_type is None

            if exc_type:
                self.metrics.error = str(exc_val)

            await _debug_collector.record_operation(self.metrics)


def async_debug(operation_name: str | None = None) -> Callable:
    """Decorator for async debugging."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = operation_name or f"{func.__name__}"
            async with AsyncDebugContext(name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


class RaceConditionDetector:
    """Detects potential race conditions in async code."""

    def __init__(self) -> None:
        self.shared_state_access: dict[str, list[dict[str, Any]]] = {}
        self.concurrent_access_count = 0
        self._lock = asyncio.Lock()

    async def track_shared_state_access(self, state_name: str, operation: str) -> None:
        """Track access to shared state."""
        async with self._lock:
            if state_name not in self.shared_state_access:
                self.shared_state_access[state_name] = []

            self.shared_state_access[state_name].append(
                {
                    "operation": operation,
                    "timestamp": time.time(),
                    "task": asyncio.current_task(),
                }
            )

            # Check for concurrent access
            recent_accesses = [
                access
                for access in self.shared_state_access[state_name]
                if time.time() - access["timestamp"] < 0.1  # Within 100ms
            ]

            if len(recent_accesses) > 1:
                self.concurrent_access_count += 1
                await _debug_collector.record_race_condition(
                    {
                        "state_name": state_name,
                        "concurrent_accesses": len(recent_accesses),
                        "operations": [
                            access["operation"] for access in recent_accesses
                        ],
                    }
                )


# Global race condition detector
_race_detector = RaceConditionDetector()


def get_race_detector() -> RaceConditionDetector:
    """Get the global race condition detector."""
    return _race_detector


class AsyncSafeCounter:
    """Async-safe counter with race condition protection."""

    def __init__(self, initial_value: int = 0) -> None:
        self._value = initial_value
        self._lock = asyncio.Lock()

    async def increment(self, value: int = 1) -> int:
        """Increment counter safely."""
        async with self._lock:
            self._value += value
            await _race_detector.track_shared_state_access("counter", "increment")
            return self._value

    async def decrement(self, value: int = 1) -> int:
        """Decrement counter safely."""
        async with self._lock:
            self._value -= value
            await _race_detector.track_shared_state_access("counter", "decrement")
            return self._value

    async def get_value(self) -> int:
        """Get current value safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("counter", "read")
            return self._value

    async def reset(self) -> int:
        """Reset counter safely."""
        async with self._lock:
            old_value = self._value
            self._value = 0
            await _race_detector.track_shared_state_access("counter", "reset")
            return old_value


class AsyncSafeDict:
    """Async-safe dictionary with race condition protection."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("dict", "get")
            return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Set value safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("dict", "set")
            self._data[key] = value

    async def delete(self, key: str) -> Any:
        """Delete value safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("dict", "delete")
            return self._data.pop(key, None)

    async def keys(self) -> list[str]:
        """Get all keys safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("dict", "keys")
            return list(self._data.keys())

    async def values(self) -> list[Any]:
        """Get all values safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("dict", "values")
            return list(self._data.values())

    async def items(self) -> list[tuple[str, Any]]:
        """Get all items safely."""
        async with self._lock:
            await _race_detector.track_shared_state_access("dict", "items")
            return list(self._data.items())


@asynccontextmanager
async def async_timeout_context(
    timeout: float, operation_name: str
) -> AsyncGenerator[None, None]:
    """Context manager for async timeout with debugging."""
    start_time = time.time()

    try:
        async with asyncio.timeout(timeout):
            yield
    except TimeoutError:
        duration = time.time() - start_time
        logger.error(
            "Timeout in %.3f after %ss (limit: %ss)", operation_name, duration, timeout
        )
        raise
    finally:
        duration = time.time() - start_time
        if duration > _debug_collector.config.timeout_warning_threshold:
            logger.warning(
                "Slow operation: %.3f%% took %.3f%%s", operation_name, duration
            )


class AsyncTestHelper:
    """Helper utilities for async testing."""

    @staticmethod
    async def run_concurrent_tasks(
        tasks: list[Callable], max_concurrent: int = 10, timeout: float = 30.0
    ) -> list[Any]:
        """Run multiple async tasks concurrently with debugging."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(task_func: Callable) -> Any:
            async with semaphore:
                async with AsyncDebugContext(f"concurrent_task_{task_func.__name__}"):
                    return await task_func()

        try:
            async with async_timeout_context(timeout, "concurrent_tasks"):
                return await asyncio.gather(
                    *[run_with_semaphore(task) for task in tasks],
                    return_exceptions=True,
                )
        except (ValueError, RuntimeError) as e:
            logger.error("Error in concurrent task execution: %s", e)
            raise

    @staticmethod
    async def simulate_race_condition(
        shared_state_accessor: Callable,
        num_tasks: int = 10,
        delay_range: tuple = (0.001, 0.01),
    ) -> list[Any]:
        """Simulate race conditions for testing."""
        import secrets

        async def competing_task(task_id: int) -> None:
            delay = (
                secrets.randbelow(int((delay_range[1] - delay_range[0]) * 1000)) / 1000
                + delay_range[0]
            )
            await asyncio.sleep(delay)
            return await shared_state_accessor(task_id)

        tasks = [competing_task(i) for i in range(num_tasks)]
        return await AsyncTestHelper.run_concurrent_tasks(tasks)

    @staticmethod
    async def test_async_lock_protection(
        protected_operation: Callable,
        unprotected_operation: Callable,
        num_iterations: int = 100,
    ) -> dict[str, Any]:
        """Test that async locks protect against race conditions."""
        results = {
            "protected_results": [],
            "unprotected_results": [],
            "protected_race_conditions": 0,
            "unprotected_race_conditions": 0,
        }

        # Test protected operation
        for _ in range(num_iterations):
            result = await protected_operation()
            results["protected_results"].append(result)

        # Test unprotected operation
        for _ in range(num_iterations):
            result = await unprotected_operation()
            results["unprotected_results"].append(result)

        # Analyze results for race conditions
        protected_unique = len(set(results["protected_results"]))
        unprotected_unique = len(set(results["unprotected_results"]))

        results["protected_race_conditions"] = num_iterations - protected_unique
        results["unprotected_race_conditions"] = num_iterations - unprotected_unique

        return results


# Pytest fixtures for async debugging


@pytest.fixture()
async def async_debug_context(self) -> None:
    """Fixture providing async debug context."""
    collector = get_debug_collector()
    yield collector
    # Cleanup after test
    collector.operations.clear()
    collector.race_conditions.clear()
    collector.unawaited_coroutines.clear()
    collector.slow_operations.clear()


@pytest.fixture()
async def race_condition_detector(self) -> None:
    """Fixture providing race condition detector."""
    detector = get_race_detector()
    yield detector
    # Cleanup after test
    detector.shared_state_access.clear()
    detector.concurrent_access_count = 0


@pytest.fixture()
async def async_safe_counter(self) -> None:
    """Fixture providing async-safe counter."""
    return AsyncSafeCounter()


@pytest.fixture()
async def async_safe_dict(self) -> None:
    """Fixture providing async-safe dictionary."""
    return AsyncSafeDict()


@pytest.fixture()
async def async_test_helper(self) -> None:
    """Fixture providing async test helper."""
    return AsyncTestHelper()


# Pytest markers for async debugging


def pytest_configure(config) -> None:
    """Configure pytest with async debugging markers."""
    config.addinivalue_line(
        "markers", "async_debug: mark test as requiring async debugging"
    )
    config.addinivalue_line(
        "markers", "race_condition: mark test as potentially exposing race conditions"
    )
    config.addinivalue_line(
        "markers", "slow_async: mark test as having slow async operations"
    )
    config.addinivalue_line(
        "markers", "concurrent_tasks: mark test as using concurrent async tasks"
    )


# Utility functions for async debugging


async def log_async_state(self) -> None:
    """Log current async state for debugging."""
    current_task = asyncio.current_task()
    all_tasks = asyncio.all_tasks()

    logger.debug("Current task: %s", current_task)
    logger.debug("Total tasks: %s", len(all_tasks))
    logger.debug("Event loop: %s", asyncio.get_running_loop())

    # Log task details
    for task in all_tasks:
        if not task.done():
            logger.debug("Active task: %s", task.get_name())


async def detect_unawaited_coroutines(self) -> None:
    """Detect and log unawaited coroutines."""
    loop = asyncio.get_running_loop()

    # This is a simplified detection - in practice, you'd need more sophisticated monitoring
    pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]

    if len(pending_tasks) > 10:  # Arbitrary threshold
        logger.warning("High number of pending tasks: %s", len(pending_tasks))
        for task in pending_tasks[:5]:  # Log first 5
            logger.warning("Pending task: %s", task.get_name())


def enable_asyncio_debug_mode(self) -> None:
    """Enable asyncio debug mode programmatically."""
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    logger.info("Asyncio debug mode enabled")


# Example usage and test cases


async def example_race_condition_test(self) -> None:
    """Example of testing for race conditions."""
    counter = AsyncSafeCounter()

    async def increment_task(self) -> None:
        return await counter.increment()

    # Run multiple tasks concurrently
    results = await AsyncTestHelper.run_concurrent_tasks(
        [increment_task for _ in range(10)]
    )

    # Check final value
    final_value = await counter.get_value()
    assert final_value == 10, f"Expected 10, got {final_value}"

    return results


async def example_slow_operation_test(self) -> None:
    """Example of testing slow operations."""
    async with AsyncDebugContext("slow_operation_test"):
        await asyncio.sleep(0.2)  # Simulate slow operation

        # This should be detected as slow
        collector = get_debug_collector()
        summary = collector.get_summary()

        assert summary["slow_operations"] > 0
        return summary


if __name__ == "__main__":
    # Example usage
    async def main(self) -> None:
        print("Async Debugging Utilities Example")

        # Test race condition detection
        print("\nTesting race condition detection...")
        results = await example_race_condition_test()
        print(f"Race condition test results: {len(results)} tasks completed")

        # Test slow operation detection
        print("\nTesting slow operation detection...")
        summary = await example_slow_operation_test()
        print(f"Slow operation summary: {summary}")

        # Test async-safe data structures
        print("\nTesting async-safe data structures...")
        counter = AsyncSafeCounter()
        safe_dict = AsyncSafeDict()

        await counter.increment(5)
        await safe_dict.set("test_key", "test_value")

        counter_value = await counter.get_value()
        dict_value = await safe_dict.get("test_key")

        print(f"Counter value: {counter_value}")
        print(f"Dict value: {dict_value}")

        # Get debug summary
        collector = get_debug_collector()
        debug_summary = collector.get_summary()
        print(f"\nDebug summary: {debug_summary}")

    # Run example
    asyncio.run(main())
