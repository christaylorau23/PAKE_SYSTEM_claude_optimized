#!/usr/bin/env python3
"""Async Debugging Test Examples for PAKE System
Comprehensive test cases demonstrating async debugging, race condition detection, and flaky test handling
"""

import asyncio
import time
from typing import Any, Dict, List

import pytest

from src.utils.async_debug_utils import (
    AsyncDebugContext,
    AsyncSafeCounter,
    AsyncSafeDict,
    AsyncTestHelper,
    RaceConditionDetector,
    async_debug,
    async_timeout_context,
    get_debug_collector,
    get_race_detector,
)


class TestAsyncDebugging:
    """Test cases for async debugging utilities"""

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    async def test_async_debug_context(self) -> None:
        """Test async debug context manager"""
        async with AsyncDebugContext("test_operation"):
            # Use minimal delay for testing async behavior
            await asyncio.sleep(0.001)  # Reduced from 0.01 for faster tests

        collector = get_debug_collector()
        assert len(collector.operations) > 0
        assert collector.operations[0].operation_name == "test_operation"
        assert collector.operations[0].success is True

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    async def test_async_debug_decorator(self) -> None:
        """Test async debug decorator"""

        @async_debug("decorated_operation")
        async def test_function(self) -> None:
            # Use minimal delay for testing async behavior
            await asyncio.sleep(0.001)  # Reduced from 0.01 for faster tests
            return "success"

        result = await test_function()
        assert result == "success"

        collector = get_debug_collector()
        assert any(
            op.operation_name == "decorated_operation" for op in collector.operations
        )

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    async def test_slow_operation_detection(self) -> None:
        """Test detection of slow operations"""
        async with AsyncDebugContext("slow_operation"):
            await asyncio.sleep(0.2)  # Simulate slow operation

        collector = get_debug_collector()
        assert len(collector.slow_operations) > 0
        assert collector.slow_operations[0].operation_name == "slow_operation"

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    async def test_timeout_context(self) -> None:
        """Test async timeout context"""
        with pytest.raises(asyncio.TimeoutError):
            async with async_timeout_context(0.1, "timeout_test"):
                await asyncio.sleep(0.2)


class TestRaceConditionDetection:
    """Test cases for race condition detection"""

    @pytest.mark.asyncio
    @pytest.mark.race_condition
    async def test_async_safe_counter(self) -> None:
        """Test async-safe counter prevents race conditions"""
        counter = AsyncSafeCounter()

        async def increment_task(self) -> None:
            return await counter.increment()

        # Run multiple increment tasks concurrently
        tasks = [increment_task() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All tasks should complete successfully
        assert len(results) == 10
        assert all(isinstance(result, int) for result in results)

        # Final counter value should be correct
        final_value = await counter.get_value()
        assert final_value == 10

    @pytest.mark.asyncio
    @pytest.mark.race_condition
    async def test_async_safe_dict(self) -> None:
        """Test async-safe dictionary prevents race conditions"""
        safe_dict = AsyncSafeDict()

        async def set_task(self) -> None:
            await safe_dict.set(key, value)
            return await safe_dict.get(key)

        # Run multiple set operations concurrently
        tasks = [set_task(f"key_{i}", f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All operations should complete successfully
        assert len(results) == 10
        assert all(result is not None for result in results)

        # All keys should be present
        keys = await safe_dict.keys()
        assert len(keys) == 10

    @pytest.mark.asyncio
    @pytest.mark.race_condition
    async def test_concurrent_shared_state_access(self) -> None:
        """Test detection of concurrent shared state access"""
        detector = get_race_detector()

        async def access_shared_state(self) -> None:
            await detector.track_shared_state_access(
                "test_state", f"operation_{task_id}"
            )
            await asyncio.sleep(0.001)  # Small delay to simulate concurrent access

        # Run multiple tasks that access shared state concurrently
        tasks = [access_shared_state(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Should detect some concurrent access
        assert detector.concurrent_access_count > 0

    @pytest.mark.asyncio
    @pytest.mark.race_condition
    async def test_unsafe_counter_race_condition(self) -> None:
        """Test that demonstrates race condition with unsafe counter"""
        # This is intentionally unsafe to demonstrate the problem
        unsafe_counter = {"value": 0}

        async def unsafe_increment(self) -> None:
            # Simulate the race condition
            current_value = unsafe_counter["value"]
            await asyncio.sleep(0.001)  # Yield control
            unsafe_counter["value"] = current_value + 1
            return unsafe_counter["value"]

        # Run multiple increment tasks concurrently
        tasks = [unsafe_increment() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Due to race condition, final value might be less than expected
        final_value = unsafe_counter["value"]
        assert final_value <= 10  # Should be less than or equal to 10
        # This test demonstrates the race condition problem


class TestConcurrentTasks:
    """Test cases for concurrent task execution"""

    @pytest.mark.asyncio
    @pytest.mark.concurrent_tasks
    async def test_run_concurrent_tasks(self) -> None:
        """Test running multiple async tasks concurrently"""

        async def test_task(self) -> None:
            await asyncio.sleep(0.01)
            return f"task_{task_id}_completed"

        tasks = [lambda: test_task(i) for i in range(5)]
        results = await AsyncTestHelper.run_concurrent_tasks(tasks)

        assert len(results) == 5
        assert all("completed" in str(result) for result in results)

    @pytest.mark.asyncio
    @pytest.mark.concurrent_tasks
    async def test_concurrent_tasks_with_semaphore(self) -> None:
        """Test concurrent tasks with semaphore limiting"""

        async def limited_task(self) -> None:
            await asyncio.sleep(0.01)
            return f"limited_task_{task_id}"

        tasks = [lambda: limited_task(i) for i in range(10)]
        results = await AsyncTestHelper.run_concurrent_tasks(tasks, max_concurrent=3)

        assert len(results) == 10
        assert all("limited_task" in str(result) for result in results)

    @pytest.mark.asyncio
    @pytest.mark.concurrent_tasks
    async def test_concurrent_tasks_timeout(self) -> None:
        """Test concurrent tasks with timeout"""

        async def slow_task(self) -> None:
            await asyncio.sleep(0.2)
            return "slow_task_completed"

        tasks = [slow_task for _ in range(3)]

        with pytest.raises(asyncio.TimeoutError):
            await AsyncTestHelper.run_concurrent_tasks(tasks, timeout=0.1)


class TestFlakyTestHandling:
    """Test cases demonstrating flaky test handling"""

    @pytest.mark.asyncio
    @pytest.mark.flaky
    async def test_intermittent_failure(self) -> None:
        """Test that may fail intermittently (demonstrates retry mechanism)"""
        import random

        # Simulate intermittent failure (10% chance)
        if random.random() < 0.1:
            msg = "Intermittent failure"
            raise AssertionError(msg)

        assert True

    @pytest.mark.asyncio
    @pytest.mark.flaky
    async def test_network_timeout_simulation(self) -> None:
        """Test simulating network timeout issues"""
        import random

        # Simulate network timeout (5% chance)
        if random.random() < 0.05:
            msg = "Network timeout"
            raise TimeoutError(msg)

        await asyncio.sleep(0.01)
        assert True

    @pytest.mark.asyncio
    @pytest.mark.flaky
    async def test_resource_contention(self) -> None:
        """Test simulating resource contention issues"""
        import random

        # Simulate resource contention (3% chance)
        if random.random() < 0.03:
            msg = "Resource contention"
            raise ConnectionError(msg)

        await asyncio.sleep(0.01)
        assert True


class TestAsyncPerformance:
    """Test cases for async performance monitoring"""

    @pytest.mark.asyncio
    @pytest.mark.slow_async
    async def test_performance_monitoring(self) -> None:
        """Test async performance monitoring"""
        async with AsyncDebugContext("performance_test"):
            # Simulate some work
            await asyncio.sleep(0.05)

            # Simulate CPU-intensive work
            for _ in range(1000):
                pass

        collector = get_debug_collector()
        summary = collector.get_summary()

        assert summary["total_operations"] > 0
        assert summary["average_duration"] > 0

    @pytest.mark.asyncio
    @pytest.mark.slow_async
    async def test_memory_usage_monitoring(self) -> None:
        """Test memory usage monitoring during async operations"""
        async with AsyncDebugContext("memory_test"):
            # Create some data
            data = list(range(1000))
            await asyncio.sleep(0.01)
            del data

        collector = get_debug_collector()
        assert len(collector.operations) > 0


class TestAsyncErrorHandling:
    """Test cases for async error handling and debugging"""

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    async def test_async_error_capture(self) -> None:
        """Test capturing errors in async operations"""
        async with AsyncDebugContext("error_test"):
            msg = "Test error"
            raise ValueError(msg)

        collector = get_debug_collector()
        error_operations = [op for op in collector.operations if not op.success]
        assert len(error_operations) > 0
        assert error_operations[0].error == "Test error"

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    async def test_nested_async_operations(self) -> None:
        """Test nested async operations"""

        async def inner_operation(self) -> None:
            async with AsyncDebugContext("inner_operation"):
                await asyncio.sleep(0.01)
                return "inner_success"

        async def outer_operation(self) -> None:
            async with AsyncDebugContext("outer_operation"):
                return await inner_operation()

        result = await outer_operation()
        assert result == "inner_success"

        collector = get_debug_collector()
        operation_names = [op.operation_name for op in collector.operations]
        assert "inner_operation" in operation_names
        assert "outer_operation" in operation_names


class TestAsyncDebuggingIntegration:
    """Integration tests for async debugging"""

    @pytest.mark.asyncio
    @pytest.mark.async_debug
    @pytest.mark.race_condition
    async def test_comprehensive_async_debugging(self) -> None:
        """Comprehensive test of async debugging capabilities"""
        # Test async-safe data structures
        counter = AsyncSafeCounter()
        safe_dict = AsyncSafeDict()

        async def complex_operation(self) -> None:
            async with AsyncDebugContext(f"complex_operation_{task_id}"):
                # Increment counter
                await counter.increment()

                # Set dictionary value
                await safe_dict.set(f"key_{task_id}", f"value_{task_id}")

                # Simulate some work
                await asyncio.sleep(0.01)

                # Read values back
                counter_value = await counter.get_value()
                dict_value = await safe_dict.get(f"key_{task_id}")

                return {
                    "task_id": task_id,
                    "counter_value": counter_value,
                    "dict_value": dict_value,
                }

        # Run multiple complex operations concurrently
        tasks = [lambda: complex_operation(i) for i in range(5)]
        results = await AsyncTestHelper.run_concurrent_tasks(tasks)

        # Verify results
        assert len(results) == 5
        assert all(isinstance(result, dict) for result in results)

        # Verify final state
        final_counter_value = await counter.get_value()
        final_keys = await safe_dict.keys()

        assert final_counter_value == 5
        assert len(final_keys) == 5

        # Verify debug information
        collector = get_debug_collector()
        summary = collector.get_summary()

        assert summary["total_operations"] >= 5
        assert summary["error_rate"] == 0  # No errors expected


# Pytest configuration for async debugging tests


@pytest.fixture
async def async_debug_cleanup(self) -> None:
    """Cleanup fixture for async debugging tests"""
    collector = get_debug_collector()
    detector = get_race_detector()

    # Clear state before test
    collector.operations.clear()
    collector.race_conditions.clear()
    collector.unawaited_coroutines.clear()
    collector.slow_operations.clear()
    detector.shared_state_access.clear()
    detector.concurrent_access_count = 0

    yield

    # Cleanup after test
    collector.operations.clear()
    collector.race_conditions.clear()
    collector.unawaited_coroutines.clear()
    collector.slow_operations.clear()
    detector.shared_state_access.clear()
    detector.concurrent_access_count = 0


# Example of how to use these tests in practice

if __name__ == "__main__":
    # Example of running async debugging tests
    async def run_example_tests(self) -> None:
        print("Running Async Debugging Test Examples")

        # Test async-safe counter
        print("\n1. Testing async-safe counter...")
        counter = AsyncSafeCounter()

        async def increment_task(self) -> None:
            return await counter.increment()

        tasks = [increment_task() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        final_value = await counter.get_value()

        print(f"   Results: {len(results)} tasks completed")
        print(f"   Final counter value: {final_value}")

        # Test race condition detection
        print("\n2. Testing race condition detection...")
        detector = get_race_detector()

        async def access_shared_state(self) -> None:
            await detector.track_shared_state_access(
                "test_state", f"operation_{task_id}"
            )
            await asyncio.sleep(0.001)

        tasks = [access_shared_state(i) for i in range(5)]
        await asyncio.gather(*tasks)

        print(f"   Concurrent access count: {detector.concurrent_access_count}")

        # Test debug summary
        print("\n3. Getting debug summary...")
        collector = get_debug_collector()
        summary = collector.get_summary()

        print(f"   Total operations: {summary['total_operations']}")
        print(f"   Slow operations: {summary['slow_operations']}")
        print(f"   Race conditions: {summary['race_conditions']}")
        print(f"   Error rate: {summary['error_rate']:.2%}")

        print("\nAsync debugging test examples completed successfully!")

    # Run the example
    asyncio.run(run_example_tests())
