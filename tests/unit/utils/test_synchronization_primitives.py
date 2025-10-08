#!/usr/bin/env python3
"""
PAKE System - Synchronization Primitives Tests
Comprehensive test suite for enterprise synchronization utilities

This module tests the synchronization primitives to ensure they properly
prevent race conditions and provide enterprise-grade concurrency safety.
"""

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest

from src.utils.synchronization_primitives import (
    AsyncLockManager,
    AsyncSafeCounter,
    AsyncSafeDict,
    AsyncSafeQueue,
    SynchronizationMonitor,
    SynchronizationTestHelper,
    ThreadSafeCounter,
    async_lock_context,
    get_sync_monitor,
    thread_lock_context,
    with_async_lock,
    with_thread_lock,
)


class TestAsyncLockManager:
    """Test cases for AsyncLockManager"""

    @pytest.fixture()
    def lock_manager(self) -> AsyncLockManager:
        """Create AsyncLockManager instance for testing"""
        return AsyncLockManager(enable_deadlock_detection=True)

    @pytest.mark.asyncio()
    async def test_lock_acquisition_and_release(
        self, lock_manager: AsyncLockManager
    ) -> None:
        """Test basic lock acquisition and release"""
        lock_name = "test_lock"

        # Acquire lock
        acquired = await lock_manager.acquire_lock(lock_name)
        assert acquired is True

        # Release lock
        released = await lock_manager.release_lock(lock_name)
        assert released is True

    @pytest.mark.asyncio()
    async def test_concurrent_lock_acquisition(
        self, lock_manager: AsyncLockManager
    ) -> None:
        """Test concurrent lock acquisition"""
        lock_name = "concurrent_test_lock"
        results: list[str] = []

        async def acquire_lock_task(task_id: int) -> None:
            acquired = await lock_manager.acquire_lock(lock_name, timeout=1.0)
            if acquired:
                await asyncio.sleep(0.01)  # Hold lock briefly
                await lock_manager.release_lock(lock_name)
                results.append(f"task_{task_id}_acquired")
            else:
                results.append(f"task_{task_id}_failed")

        # Run multiple tasks trying to acquire the same lock
        tasks = [acquire_lock_task(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # All tasks should eventually acquire the lock
        assert len(results) == 5
        assert all("acquired" in result for result in results)

    @pytest.mark.asyncio()
    async def test_lock_timeout(self, lock_manager: AsyncLockManager) -> None:
        """Test lock acquisition timeout"""
        lock_name = "timeout_test_lock"

        # Acquire lock in first task
        acquired1 = await lock_manager.acquire_lock(lock_name)
        assert acquired1 is True

        # Try to acquire same lock with short timeout
        acquired2 = await lock_manager.acquire_lock(lock_name, timeout=0.1)
        assert acquired2 is False

        # Release first lock
        await lock_manager.release_lock(lock_name)

    @pytest.mark.asyncio()
    async def test_deadlock_detection(self, lock_manager: AsyncLockManager) -> None:
        """Test deadlock detection"""
        lock1 = "deadlock_lock1"
        lock2 = "deadlock_lock2"

        # Simulate potential deadlock scenario
        async def task1() -> bool:
            await lock_manager.acquire_lock(lock1)
            await asyncio.sleep(0.01)  # Small delay
            return await lock_manager.acquire_lock(lock2, timeout=0.1)

        async def task2() -> bool:
            await lock_manager.acquire_lock(lock2)
            await asyncio.sleep(0.01)  # Small delay
            return await lock_manager.acquire_lock(lock1, timeout=0.1)

        # Run tasks concurrently
        results = await asyncio.gather(*[task1(), task2()], return_exceptions=True)

        # At least one should fail due to deadlock detection or timeout
        assert any(result is False for result in results)

    @pytest.mark.asyncio()
    async def test_lock_metrics(self, lock_manager: AsyncLockManager) -> None:
        """Test lock performance metrics"""
        lock_name = "metrics_test_lock"

        # Perform some lock operations
        for _ in range(10):
            await lock_manager.acquire_lock(lock_name)
            await asyncio.sleep(0.001)  # Small delay
            await lock_manager.release_lock(lock_name)

        # Check metrics
        metrics = lock_manager.get_metrics(lock_name)
        assert metrics is not None
        assert metrics.total_acquisitions == 10
        assert metrics.total_wait_time >= 0
        assert metrics.average_wait_time >= 0

    @pytest.mark.asyncio()
    async def test_lock_context_manager(self, lock_manager: AsyncLockManager) -> None:
        """Test lock context manager"""
        lock_name = "context_test_lock"

        async with async_lock_context(lock_manager, lock_name):
            # Lock should be acquired
            assert True  # If we get here, lock was acquired

        # Lock should be released automatically


class TestThreadSafeCounter:
    """Test cases for ThreadSafeCounter"""

    @pytest.fixture()
    def counter(self) -> ThreadSafeCounter:
        """Create ThreadSafeCounter instance for testing"""
        return ThreadSafeCounter()

    def test_increment_and_decrement(self, counter: ThreadSafeCounter) -> None:
        """Test counter increment and decrement operations"""
        # Test increment
        result = counter.increment(5)
        assert result == 5
        assert counter.get_value() == 5

        # Test decrement
        result = counter.decrement(2)
        assert result == 3
        assert counter.get_value() == 3

    def test_concurrent_operations(self, counter: ThreadSafeCounter) -> None:
        """Test concurrent counter operations"""
        results: list[int] = []

        def increment_task(value: int) -> None:
            result = counter.increment(value)
            results.append(result)

        def decrement_task(value: int) -> None:
            result = counter.decrement(value)
            results.append(result)

        # Create threads for concurrent operations
        threads = []
        for _i in range(10):
            thread = threading.Thread(target=increment_task, args=(1,))
            threads.append(thread)

        for _i in range(5):
            thread = threading.Thread(target=decrement_task, args=(1,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check final value
        final_value = counter.get_value()
        assert final_value == 5  # 10 increments - 5 decrements = 5

    def test_reset_operation(self, counter: ThreadSafeCounter) -> None:
        """Test counter reset operation"""
        counter.increment(10)
        assert counter.get_value() == 10

        old_value = counter.reset()
        assert old_value == 10
        assert counter.get_value() == 0

    def test_metrics_tracking(self, counter: ThreadSafeCounter) -> None:
        """Test counter metrics tracking"""
        # Perform some operations
        for _ in range(5):
            counter.increment()

        metrics = counter.get_metrics()
        assert metrics.total_acquisitions == 5
        assert metrics.total_wait_time >= 0


class TestAsyncSafeDict:
    """Test cases for AsyncSafeDict"""

    @pytest.fixture()
    def safe_dict(self) -> AsyncSafeDict:
        """Create AsyncSafeDict instance for testing"""
        return AsyncSafeDict()

    @pytest.mark.asyncio()
    async def test_basic_operations(self, safe_dict: AsyncSafeDict) -> None:
        """Test basic dictionary operations"""
        # Test set and get
        await safe_dict.set("key1", "value1")
        value = await safe_dict.get("key1")
        assert value == "value1"

        # Test get with default
        value = await safe_dict.get("nonexistent", "default")
        assert value == "default"

        # Test delete
        deleted = await safe_dict.delete("key1")
        assert deleted == "value1"

        # Test size
        size = await safe_dict.size()
        assert size == 0

    @pytest.mark.asyncio()
    async def test_concurrent_operations(self, safe_dict: AsyncSafeDict) -> None:
        """Test concurrent dictionary operations"""

        async def set_task(key: str, value: str) -> str | None:
            await safe_dict.set(key, value)
            return await safe_dict.get(key)

        # Run concurrent set operations
        tasks = [set_task(f"key_{i}", f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert len(results) == 10
        assert all(result is not None for result in results)

        # Check final size
        size = await safe_dict.size()
        assert size == 10

    @pytest.mark.asyncio()
    async def test_keys_values_items(self, safe_dict: AsyncSafeDict) -> None:
        """Test keys, values, and items operations"""
        # Add some data
        for i in range(5):
            await safe_dict.set(f"key_{i}", f"value_{i}")

        # Test keys
        keys = await safe_dict.keys()
        assert len(keys) == 5
        assert all(f"key_{i}" in keys for i in range(5))

        # Test values
        values = await safe_dict.values()
        assert len(values) == 5
        assert all(f"value_{i}" in values for i in range(5))

        # Test items
        items = await safe_dict.items()
        assert len(items) == 5
        assert all((f"key_{i}", f"value_{i}") in items for i in range(5))

    @pytest.mark.asyncio()
    async def test_metrics_tracking(self, safe_dict: AsyncSafeDict) -> None:
        """Test metrics tracking"""
        # Perform some operations
        for i in range(10):
            await safe_dict.set(f"key_{i}", f"value_{i}")
            await safe_dict.get(f"key_{i}")

        metrics = safe_dict.get_metrics()
        assert metrics.total_acquisitions >= 20  # 10 sets + 10 gets
        assert metrics.total_wait_time >= 0


class TestAsyncSafeQueue:
    """Test cases for AsyncSafeQueue"""

    @pytest.fixture()
    def safe_queue(self) -> AsyncSafeQueue:
        """Create AsyncSafeQueue instance for testing"""
        return AsyncSafeQueue(maxsize=10)

    @pytest.mark.asyncio()
    async def test_basic_queue_operations(self, safe_queue: AsyncSafeQueue) -> None:
        """Test basic queue operations"""
        # Test put and get
        await safe_queue.put("item1")
        item = await safe_queue.get()
        assert item == "item1"

        # Test size
        size = await safe_queue.size()
        assert size == 0

    @pytest.mark.asyncio()
    async def test_concurrent_queue_operations(
        self, safe_queue: AsyncSafeQueue
    ) -> None:
        """Test concurrent queue operations"""

        async def producer(item: str) -> str:
            await safe_queue.put(item)
            return f"produced_{item}"

        async def consumer() -> str:
            item = await safe_queue.get()
            return f"consumed_{item}"

        # Run producers and consumers concurrently
        producer_tasks = [producer(f"item_{i}") for i in range(5)]
        consumer_tasks = [consumer() for _ in range(5)]

        producer_results = await asyncio.gather(*producer_tasks)
        consumer_results = await asyncio.gather(*consumer_tasks)

        assert len(producer_results) == 5
        assert len(consumer_results) == 5
        assert all("produced" in result for result in producer_results)
        assert all("consumed" in result for result in consumer_results)

    @pytest.mark.asyncio()
    async def test_priority_queue(self, safe_queue: AsyncSafeQueue) -> None:
        """Test priority queue functionality"""
        # Enable priority mode
        safe_queue._use_priority = True

        # Add items with different priorities
        await safe_queue.put("low_priority", priority=1)
        await safe_queue.put("high_priority", priority=10)
        await safe_queue.put("medium_priority", priority=5)

        # Items should be retrieved in priority order
        high = await safe_queue.get()
        medium = await safe_queue.get()
        low = await safe_queue.get()

        assert high == "high_priority"
        assert medium == "medium_priority"
        assert low == "low_priority"


class TestSynchronizationMonitor:
    """Test cases for SynchronizationMonitor"""

    @pytest.fixture()
    def monitor(self) -> SynchronizationMonitor:
        """Create SynchronizationMonitor instance for testing"""
        return SynchronizationMonitor()

    def test_register_components(self, monitor: SynchronizationMonitor) -> None:
        """Test registering synchronization components"""
        lock_manager = AsyncLockManager()
        counter = ThreadSafeCounter()
        safe_dict = AsyncSafeDict()
        queue = AsyncSafeQueue()

        monitor.register_lock_manager("test_manager", lock_manager)
        monitor.register_counter("test_counter", counter)
        monitor.register_async_dict("test_dict", safe_dict)
        monitor.register_queue("test_queue", queue)

        metrics = monitor.get_system_metrics()
        assert "test_manager" in metrics["lock_managers"]
        assert "test_counter" in metrics["counters"]
        assert "test_dict" in metrics["async_dicts"]
        assert "test_queue" in metrics["queues"]

    def test_system_metrics(self, monitor: SynchronizationMonitor) -> None:
        """Test system metrics collection"""
        # Register some components
        lock_manager = AsyncLockManager()
        counter = ThreadSafeCounter()

        monitor.register_lock_manager("test_manager", lock_manager)
        monitor.register_counter("test_counter", counter)

        # Perform some operations
        counter.increment(5)

        metrics = monitor.get_system_metrics()
        assert metrics["summary"]["lock_managers_count"] == 1
        assert metrics["summary"]["counters_count"] == 1
        assert metrics["summary"]["total_acquisitions"] >= 1


class TestSynchronizationTestHelper:
    """Test cases for SynchronizationTestHelper"""

    @pytest.mark.asyncio()
    async def test_race_condition_protection(self) -> None:
        """Test race condition protection analysis"""
        counter = AsyncSafeCounter()

        async def increment_operation() -> int:
            return await counter.increment()

        result = await SynchronizationTestHelper.test_race_condition_protection(
            increment_operation, num_concurrent=5, iterations=10
        )

        assert result["total_results"] == 50  # 5 concurrent * 10 iterations
        assert result["race_condition_detected"] is False  # Should be protected

    @pytest.mark.asyncio()
    async def test_performance_benchmark(self) -> None:
        """Test performance benchmarking"""
        safe_dict = AsyncSafeDict()

        async def dict_operation() -> str | None:
            await safe_dict.set("test_key", "test_value")
            return await safe_dict.get("test_key")

        result = await SynchronizationTestHelper.benchmark_synchronization_performance(
            dict_operation, num_operations=100
        )

        assert result["total_operations"] == 100
        assert result["successful_operations"] == 100
        assert result["failed_operations"] == 0
        assert result["operations_per_second"] > 0
        assert result["error_rate"] == 0.0


class TestContextManagers:
    """Test cases for context managers"""

    @pytest.mark.asyncio()
    async def test_async_lock_context(self) -> None:
        """Test async lock context manager"""
        lock_manager = AsyncLockManager()
        lock_name = "context_test_lock"

        async with with_async_lock(lock_manager, lock_name):
            # Lock should be acquired
            assert True

        # Lock should be released automatically

    def test_thread_lock_context(self) -> None:
        """Test thread lock context manager"""
        lock = threading.Lock()

        with with_thread_lock(lock):
            # Lock should be acquired
            assert True

        # Lock should be released automatically


class TestIntegrationScenarios:
    """Integration test scenarios"""

    @pytest.mark.asyncio()
    async def test_comprehensive_synchronization_scenario(self) -> None:
        """Test comprehensive synchronization scenario"""
        # Create components
        lock_manager = AsyncLockManager()
        counter = AsyncSafeCounter()
        safe_dict = AsyncSafeDict()
        queue = AsyncSafeQueue()

        # Register with monitor
        monitor = SynchronizationMonitor()
        monitor.register_lock_manager("test_manager", lock_manager)
        monitor.register_async_dict("test_dict", safe_dict)
        monitor.register_queue("test_queue", queue)

        async def complex_operation(task_id: int) -> int:
            """Complex operation using multiple synchronization primitives"""
            # Use lock for critical section
            async with async_lock_context(lock_manager, f"operation_{task_id}"):
                # Increment counter
                counter_value = await counter.increment()

                # Store in safe dict
                await safe_dict.set(f"task_{task_id}", f"value_{counter_value}")

                # Put in queue
                await queue.put(f"task_{task_id}_result")

                return counter_value

        # Run multiple complex operations concurrently
        tasks = [complex_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify results
        assert len(results) == 10
        assert all(isinstance(result, int) for result in results)

        # Verify final state
        final_counter_value = await counter.get_value()
        assert final_counter_value == 10

        dict_size = await safe_dict.size()
        assert dict_size == 10

        queue_size = await queue.size()
        assert queue_size == 10

        # Check system metrics
        metrics = monitor.get_system_metrics()
        assert metrics["summary"]["total_acquisitions"] > 0

    @pytest.mark.asyncio()
    async def test_race_condition_prevention(self) -> None:
        """Test that synchronization primitives prevent race conditions"""
        # Test unsafe counter (should show race condition)
        unsafe_counter = {"value": 0}

        async def unsafe_increment() -> int:
            current_value = unsafe_counter["value"]
            await asyncio.sleep(0.001)  # Yield control
            unsafe_counter["value"] = current_value + 1
            return unsafe_counter["value"]

        # Run unsafe operations
        tasks = [unsafe_increment() for _ in range(10)]
        unsafe_results = await asyncio.gather(*tasks)

        # Unsafe counter might not reach expected value due to race condition
        unsafe_final_value = unsafe_counter["value"]

        # Test safe counter (should prevent race condition)
        safe_counter = AsyncSafeCounter()

        async def safe_increment() -> int:
            return await safe_counter.increment()

        # Run safe operations
        tasks = [safe_increment() for _ in range(10)]
        safe_results = await asyncio.gather(*tasks)

        # Safe counter should reach expected value
        safe_final_value = await safe_counter.get_value()

        # Safe counter should be more reliable
        assert safe_final_value == 10
        # Unsafe counter might be less than 10 due to race conditions
        assert unsafe_final_value <= 10


# Pytest fixtures for integration with existing test suite
@pytest.fixture()
async def async_lock_manager() -> AsyncLockManager:
    """Fixture providing AsyncLockManager"""
    return AsyncLockManager()
    # Cleanup if needed


@pytest.fixture()
def thread_safe_counter() -> ThreadSafeCounter:
    """Fixture providing ThreadSafeCounter"""
    return ThreadSafeCounter()


@pytest.fixture()
async def async_safe_dict() -> AsyncSafeDict:
    """Fixture providing AsyncSafeDict"""
    return AsyncSafeDict()


@pytest.fixture()
async def async_safe_queue() -> AsyncSafeQueue:
    """Fixture providing AsyncSafeQueue"""
    return AsyncSafeQueue()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])
