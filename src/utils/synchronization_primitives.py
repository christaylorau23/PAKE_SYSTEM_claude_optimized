#!/usr/bin/env python3
"""PAKE System - Synchronization Primitives
Enterprise-grade synchronization utilities for preventing race conditions.

This module provides comprehensive synchronization primitives to protect
shared mutable state in concurrent environments, following enterprise patterns.
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LockType(Enum):
    """Types of locks available."""

    ASYNC_LOCK = "async_lock"
    THREADING_LOCK = "threading_lock"
    RWLOCK = "rwlock"
    SEMAPHORE = "semaphore"
    CONDITION = "condition"


@dataclass
class LockMetrics:
    """Metrics for lock performance monitoring."""

    total_acquisitions: int = 0
    total_wait_time: float = 0.0
    max_wait_time: float = 0.0
    contention_count: int = 0
    deadlock_detection_count: int = 0
    average_wait_time: float = 0.0


class AsyncLockManager:
    """Advanced async lock manager with deadlock detection and metrics."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_holders: dict[str, set[str]] = defaultdict(
            set
        )  # lock_name -> task_ids
        self._waiting_tasks: dict[str, set[str]] = defaultdict(
            set
        )  # lock_name -> waiting_task_ids
        self._task_locks: dict[str, set[str]] = defaultdict(
            set
        )  # task_id -> lock_names
        self._metrics: dict[str, LockMetrics] = defaultdict(LockMetrics)
        self._enable_deadlock_detection = enable_deadlock_detection
        self._global_lock = asyncio.Lock()

        logger.info("AsyncLockManager initialized with deadlock detection enabled")

    def _get_task_id(self) -> str:
        """Get current task ID."""
        try:
            task = asyncio.current_task()
            if task:
                return f"task_{id(task)}"
        except RuntimeError:
            pass
        return f"thread_{threading.get_ident()}"

    async def acquire_lock(self, lock_name: str, timeout: float | None = None) -> bool:
        """Acquire a named lock with deadlock detection."""
        task_id = self._get_task_id()
        start_time = time.time()

        async with self._global_lock:
            # Check for deadlock
            if self._enable_deadlock_detection and self._would_cause_deadlock(
                task_id, lock_name
            ):
                logger.warning(
                    "Deadlock detected for task %s trying to acquire %s",
                    task_id,
                    lock_name,
                )
                self._metrics[lock_name].deadlock_detection_count += 1
                return False

            # Get or create lock
            if lock_name not in self._locks:
                self._locks[lock_name] = asyncio.Lock()

            # Record waiting task
            self._waiting_tasks[lock_name].add(task_id)

        try:
            # Acquire the actual lock
            if timeout is not None:
                acquired = await asyncio.wait_for(
                    self._locks[lock_name].acquire(), timeout=timeout
                )
            else:
                acquired = await self._locks[lock_name].acquire()

            if acquired:
                async with self._global_lock:
                    # Update tracking
                    self._lock_holders[lock_name].add(task_id)
                    self._task_locks[task_id].add(lock_name)
                    self._waiting_tasks[lock_name].discard(task_id)

                    # Update metrics
                    wait_time = time.time() - start_time
                    metrics = self._metrics[lock_name]
                    metrics.total_acquisitions += 1
                    metrics.total_wait_time += wait_time
                    metrics.max_wait_time = max(metrics.max_wait_time, wait_time)
                    metrics.average_wait_time = (
                        metrics.total_wait_time / metrics.total_acquisitions
                    )

                    if wait_time > 0.001:  # 1ms threshold for contention
                        metrics.contention_count += 1

            return acquired

        except TimeoutError:
            async with self._global_lock:
                self._waiting_tasks[lock_name].discard(task_id)
            logger.warning(
                "Lock acquisition timeout for %s by task %s", lock_name, task_id
            )
            return False

    async def release_lock(self, lock_name: str) -> bool:
        """Release a named lock."""
        task_id = self._get_task_id()

        async with self._global_lock:
            if (
                lock_name not in self._lock_holders
                or task_id not in self._lock_holders[lock_name]
            ):
                logger.warning(
                    "Task %s attempted to release unheld lock %s", task_id, lock_name
                )
                return False

            # Update tracking
            self._lock_holders[lock_name].discard(task_id)
            self._task_locks[task_id].discard(lock_name)

            # Clean up empty sets
            if not self._lock_holders[lock_name]:
                del self._lock_holders[lock_name]
            if not self._task_locks[task_id]:
                del self._task_locks[task_id]

        # Release the actual lock
        self._locks[lock_name].release()
        return True

    def _would_cause_deadlock(self, task_id: str, lock_name: str) -> bool:
        """Check if acquiring lock would cause deadlock."""
        # Build dependency graph
        visited = set()

        def has_cycle(current_task: str, target_lock: str) -> bool:
            if current_task in visited:
                return True
            visited.add(current_task)

            # Check if current task holds locks that others are waiting for
            for held_lock in self._task_locks.get(current_task, set()):
                for waiting_task in self._waiting_tasks.get(held_lock, set()):
                    if waiting_task != current_task:
                        if waiting_task == target_lock or has_cycle(
                            waiting_task, target_lock
                        ):
                            return True

            return False

        return has_cycle(task_id, lock_name)

    def get_metrics(self, lock_name: str) -> LockMetrics | None:
        """Get metrics for a specific lock."""
        return self._metrics.get(lock_name)

    def get_all_metrics(self) -> dict[str, LockMetrics]:
        """Get metrics for all locks."""
        return dict(self._metrics)


class ThreadSafeCounter:
    """Thread-safe counter with atomic operations."""

    def __init__(self) -> None:
        self._value = initial_value
        self._lock = threading.RLock()
        self._metrics = LockMetrics()

    def increment(self, value: int = 1) -> int:
        """Atomically increment counter."""
        with self._lock:
            start_time = time.time()
            self._value += value
            wait_time = time.time() - start_time

            # Update metrics
            self._metrics.total_acquisitions += 1
            self._metrics.total_wait_time += wait_time
            self._metrics.max_wait_time = max(self._metrics.max_wait_time, wait_time)
            self._metrics.average_wait_time = (
                self._metrics.total_wait_time / self._metrics.total_acquisitions
            )

            return self._value

    def decrement(self, value: int = 1) -> int:
        """Atomically decrement counter."""
        with self._lock:
            start_time = time.time()
            self._value -= value
            wait_time = time.time() - start_time

            # Update metrics
            self._metrics.total_acquisitions += 1
            self._metrics.total_wait_time += wait_time
            self._metrics.max_wait_time = max(self._metrics.max_wait_time, wait_time)
            self._metrics.average_wait_time = (
                self._metrics.total_wait_time / self._metrics.total_acquisitions
            )

            return self._value

    def get_value(self) -> int:
        """Get current counter value."""
        with self._lock:
            return self._value

    def reset(self) -> int:
        """Reset counter to zero and return previous value."""
        with self._lock:
            old_value = self._value
            self._value = 0
            return old_value

    def get_metrics(self) -> LockMetrics:
        """Get lock performance metrics."""
        return self._metrics


class AsyncSafeDict:
    """Async-safe dictionary with comprehensive synchronization."""

    def __init__(self) -> None:
        self._data = initial_data or {}
        self._lock = asyncio.Lock()
        self._metrics = LockMetrics()
        self._access_patterns = deque(maxlen=1000)  # Track access patterns

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value with lock protection."""
        async with self._lock:
            start_time = time.time()
            result = self._data.get(key, default)
            wait_time = time.time() - start_time

            # Update metrics and access patterns
            self._update_metrics(wait_time)
            self._access_patterns.append(("get", key, time.time()))

            return result

    async def set(self, key: str, value: Any) -> None:
        """Set value with lock protection."""
        async with self._lock:
            start_time = time.time()
            self._data[key] = value
            wait_time = time.time() - start_time

            # Update metrics and access patterns
            self._update_metrics(wait_time)
            self._access_patterns.append(("set", key, time.time()))

    async def delete(self, key: str) -> Any:
        """Delete key with lock protection."""
        async with self._lock:
            start_time = time.time()
            result = self._data.pop(key, None)
            wait_time = time.time() - start_time

            # Update metrics and access patterns
            self._update_metrics(wait_time)
            self._access_patterns.append(("delete", key, time.time()))

            return result

    async def keys(self) -> list[str]:
        """Get all keys with lock protection."""
        async with self._lock:
            start_time = time.time()
            result = list(self._data.keys())
            wait_time = time.time() - start_time

            self._update_metrics(wait_time)
            self._access_patterns.append(("keys", None, time.time()))

            return result

    async def values(self) -> list[Any]:
        """Get all values with lock protection."""
        async with self._lock:
            start_time = time.time()
            result = list(self._data.values())
            wait_time = time.time() - start_time

            self._update_metrics(wait_time)
            self._access_patterns.append(("values", None, time.time()))

            return result

    async def items(self) -> list[tuple]:
        """Get all items with lock protection."""
        async with self._lock:
            start_time = time.time()
            result = list(self._data.items())
            wait_time = time.time() - start_time

            self._update_metrics(wait_time)
            self._access_patterns.append(("items", None, time.time()))

            return result

    async def size(self) -> int:
        """Get dictionary size with lock protection."""
        async with self._lock:
            return len(self._data)

    def _update_metrics(self) -> None:
        """Update internal metrics."""
        self._metrics.total_acquisitions += 1
        self._metrics.total_wait_time += wait_time
        self._metrics.max_wait_time = max(self._metrics.max_wait_time, wait_time)
        self._metrics.average_wait_time = (
            self._metrics.total_wait_time / self._metrics.total_acquisitions
        )

        if wait_time > 0.001:  # 1ms threshold for contention
            self._metrics.contention_count += 1

    def get_metrics(self) -> LockMetrics:
        """Get lock performance metrics."""
        return self._metrics

    def get_access_patterns(self) -> list[tuple]:
        """Get recent access patterns for analysis."""
        return list(self._access_patterns)


class AsyncSafeQueue:
    """Async-safe queue with priority support and metrics."""

    def __init__(self) -> None:
        self._queue = asyncio.Queue(maxsize=maxsize)
        self._priority_queue = asyncio.PriorityQueue(maxsize=maxsize)
        self._metrics = LockMetrics()
        self._use_priority = False

    async def put(self, item: Any, priority: int = 0) -> None:
        """Put item in queue with optional priority."""
        start_time = time.time()

        if self._use_priority or priority > 0:
            await self._priority_queue.put((priority, time.time(), item))
        else:
            await self._queue.put(item)

        wait_time = time.time() - start_time
        self._update_metrics(wait_time)

    async def get(self) -> Any:
        """Get item from queue."""
        start_time = time.time()

        if self._use_priority and not self._priority_queue.empty():
            priority, timestamp, item = await self._priority_queue.get()
            result = item
        else:
            result = await self._queue.get()

        wait_time = time.time() - start_time
        self._update_metrics(wait_time)

        return result

    async def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize() + self._priority_queue.qsize()

    def _update_metrics(self) -> None:
        """Update internal metrics."""
        self._metrics.total_acquisitions += 1
        self._metrics.total_wait_time += wait_time
        self._metrics.max_wait_time = max(self._metrics.max_wait_time, wait_time)
        self._metrics.average_wait_time = (
            self._metrics.total_wait_time / self._metrics.total_acquisitions
        )

        if wait_time > 0.001:  # 1ms threshold for contention
            self._metrics.contention_count += 1

    def get_metrics(self) -> LockMetrics:
        """Get queue performance metrics."""
        return self._metrics


@asynccontextmanager
async def async_lock_context(self) -> None:
    """Context manager for async lock acquisition/release."""
    acquired = await lock_manager.acquire_lock(lock_name, timeout)
    if not acquired:
        msg = f"Failed to acquire lock {lock_name} within timeout"
        raise TimeoutError(msg)

    try:
        yield
    finally:
        await lock_manager.release_lock(lock_name)


@contextmanager
def thread_lock_context(self) -> None:
    """Context manager for thread lock acquisition/release."""
    acquired = lock.acquire(timeout=timeout)
    if not acquired:
        msg = "Failed to acquire thread lock within timeout"
        raise TimeoutError(msg)

    try:
        yield
    finally:
        lock.release()


class SynchronizationMonitor:
    """Monitor synchronization primitives for performance and deadlock detection."""

    def __init__(self) -> None:
        self._lock_managers: dict[str, AsyncLockManager] = {}
        self._counters: dict[str, ThreadSafeCounter] = {}
        self._async_dicts: dict[str, AsyncSafeDict] = {}
        self._queues: dict[str, AsyncSafeQueue] = {}
        self._global_metrics = LockMetrics()

    def register_lock_manager(self) -> None:
        """Register a lock manager for monitoring."""
        self._lock_managers[name] = manager

    def register_counter(self) -> None:
        """Register a counter for monitoring."""
        self._counters[name] = counter

    def register_async_dict(self) -> None:
        """Register an async dict for monitoring."""
        self._async_dicts[name] = async_dict

    def register_queue(self) -> None:
        """Register a queue for monitoring."""
        self._queues[name] = queue

    def get_system_metrics(self) -> dict[str, Any]:
        """Get comprehensive system synchronization metrics."""
        metrics = {
            "lock_managers": {},
            "counters": {},
            "async_dicts": {},
            "queues": {},
            "summary": {},
        }

        # Collect lock manager metrics
        for name, manager in self._lock_managers.items():
            metrics["lock_managers"][name] = manager.get_all_metrics()

        # Collect counter metrics
        for name, counter in self._counters.items():
            metrics["counters"][name] = counter.get_metrics()

        # Collect async dict metrics
        for name, async_dict in self._async_dicts.items():
            metrics["async_dicts"][name] = async_dict.get_metrics()

        # Collect queue metrics
        for name, queue in self._queues.items():
            metrics["queues"][name] = queue.get_metrics()

        # Calculate summary metrics
        total_acquisitions = sum(
            sum(m.total_acquisitions for m in manager.get_all_metrics().values())
            for manager in self._lock_managers.values()
        )

        total_wait_time = sum(
            sum(m.total_wait_time for m in manager.get_all_metrics().values())
            for manager in self._lock_managers.values()
        )

        metrics["summary"] = {
            "total_acquisitions": total_acquisitions,
            "total_wait_time": total_wait_time,
            "average_wait_time": total_wait_time / max(total_acquisitions, 1),
            "lock_managers_count": len(self._lock_managers),
            "counters_count": len(self._counters),
            "async_dicts_count": len(self._async_dicts),
            "queues_count": len(self._queues),
        }

        return metrics


# Global synchronization monitor instance
_sync_monitor = SynchronizationMonitor()


def get_sync_monitor() -> SynchronizationMonitor:
    """Get the global synchronization monitor."""
    return _sync_monitor


# Convenience functions for common synchronization patterns
async def with_async_lock(self) -> None:
    """Convenience function for async lock context."""
    return async_lock_context(lock_manager, lock_name, timeout)


def with_thread_lock(self) -> None:
    """Convenience function for thread lock context."""
    return thread_lock_context(lock, timeout)


# Example usage and testing utilities
class SynchronizationTestHelper:
    """Helper utilities for testing synchronization primitives."""

    @staticmethod
    async def test_race_condition_protection(
        operation: Callable, num_concurrent: int = 10, iterations: int = 100
    ) -> dict[str, Any]:
        """Test that an operation is protected against race conditions."""
        results = []
        errors = []

        async def concurrent_operation(self) -> None:
            try:
                for _ in range(iterations):
                    result = await operation()
                    results.append(result)
            except Exception as e:
                errors.append(str(e))

        # Run concurrent operations
        tasks = [concurrent_operation() for _ in range(num_concurrent)]
        await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "total_results": len(results),
            "total_errors": len(errors),
            "unique_results": len(set(results)),
            "errors": errors[:10],  # First 10 errors
            "race_condition_detected": len(set(results)) != len(results),
        }

    @staticmethod
    async def benchmark_synchronization_performance(
        operation: Callable, num_operations: int = 1000
    ) -> dict[str, Any]:
        """Benchmark synchronization primitive performance."""
        start_time = time.time()

        tasks = [operation() for _ in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        errors = [r for r in results if isinstance(r, Exception)]

        return {
            "total_operations": num_operations,
            "successful_operations": num_operations - len(errors),
            "failed_operations": len(errors),
            "total_time": total_time,
            "operations_per_second": num_operations / total_time,
            "average_time_per_operation": total_time / num_operations,
            "error_rate": len(errors) / num_operations,
            "errors": [str(e) for e in errors[:5]],  # First 5 errors
        }


if __name__ == "__main__":
    # Example usage
    async def example_usage(self) -> None:
        print("Synchronization Primitives Example")

        # Create lock manager
        lock_manager = AsyncLockManager()

        # Test async-safe counter
        counter = ThreadSafeCounter()

        async def increment_task(self) -> None:
            return counter.increment()

        # Run concurrent increments
        tasks = [increment_task() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        print(f"Counter results: {results}")
        print(f"Final counter value: {counter.get_value()}")
        print(f"Counter metrics: {counter.get_metrics()}")

        # Test async-safe dict
        safe_dict = AsyncSafeDict()

        async def dict_operation(self) -> None:
            await safe_dict.set(key, value)
            return await safe_dict.get(key)

        # Run concurrent dict operations
        tasks = [dict_operation(f"key_{i}", f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)

        print(f"Dict results: {results}")
        print(f"Dict size: {await safe_dict.size()}")
        print(f"Dict metrics: {safe_dict.get_metrics()}")

        # Test lock manager
        async with async_lock_context(lock_manager, "test_lock"):
            print("Acquired test_lock")
            await asyncio.sleep(0.01)

        print(f"Lock manager metrics: {lock_manager.get_all_metrics()}")

        print("Synchronization primitives example completed!")

    # Run example
    asyncio.run(example_usage())
