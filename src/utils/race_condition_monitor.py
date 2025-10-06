#!/usr/bin/env python3
"""Race Condition Detection and Monitoring Tools for PAKE System
Advanced tools for detecting, monitoring, and preventing race conditions in async code.
"""

import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import functools
import logging
import threading
import time
from typing import Any, Callable
import weakref

logger = logging.getLogger("race_condition_monitor")


@dataclass
class RaceConditionEvent:
    """Represents a detected race condition event."""

    timestamp: float
    event_type: str
    location: str
    details: dict[str, Any]
    severity: str = "medium"  # low, medium, high, critical
    stack_trace: str | None = None
    task_id: str | None = None


@dataclass
class SharedStateAccess:
    """Represents access to shared state."""

    timestamp: float
    operation: str
    state_name: str
    task_id: str
    thread_id: int
    stack_trace: str


@dataclass
class RaceConditionMetrics:
    """Metrics for race condition monitoring."""

    total_events: int = 0
    events_by_type: dict[str, int] = field(default_factory=dict)
    events_by_severity: dict[str, int] = field(default_factory=dict)
    concurrent_access_count: int = 0
    time_window_violations: int = 0
    lock_contention_count: int = 0
    deadlock_detection_count: int = 0


class RaceConditionMonitor:
    """Advanced race condition detection and monitoring system."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {
            "detection_window_ms": 100,  # Time window for concurrent access detection
            "max_concurrent_access": 2,  # Maximum concurrent accesses before flagging
            "enable_stack_trace": True,
            "enable_task_tracking": True,
            "enable_deadlock_detection": True,
            "log_level": "WARNING",
        }

        # State tracking
        self.shared_state_access: dict[str, list[SharedStateAccess]] = defaultdict(list)
        self.active_locks: dict[str, set[str]] = defaultdict(
            set
        )  # lock_name -> task_ids
        self.lock_waiting: dict[str, set[str]] = defaultdict(
            set
        )  # lock_name -> waiting_task_ids
        self.task_dependencies: dict[str, set[str]] = defaultdict(
            set
        )  # task_id -> dependent_task_ids

        # Event tracking
        self.events: deque = deque(maxlen=10000)  # Keep last 10k events
        self.metrics = RaceConditionMetrics()

        # Thread safety
        self._lock = threading.RLock()

        # Weak references to prevent memory leaks
        self._task_refs: weakref.WeakSet = weakref.WeakSet()

        logger.info("Race condition monitor initialized")

    def _get_task_id(self) -> str:
        """Get current task ID."""
        try:
            task = asyncio.current_task()
            if task:
                return f"task_{id(task)}"
        except RuntimeError:
            pass
        return f"thread_{threading.get_ident()}"

    def _get_stack_trace(self) -> str:
        """Get current stack trace."""
        if not self.config["enable_stack_trace"]:
            return ""

        try:
            import traceback

            return "".join(traceback.format_stack()[-5:])  # Last 5 frames
        except Exception:
            return ""

    def track_shared_state_access(self, operation: str, state_name: str) -> None:
        """Track access to shared state."""
        with self._lock:
            access = SharedStateAccess(
                timestamp=time.time(),
                operation=operation,
                state_name=state_name,
                task_id=self._get_task_id(),
                thread_id=threading.get_ident(),
                stack_trace=self._get_stack_trace(),
            )

            self.shared_state_access[state_name].append(access)

            # Clean old accesses (older than detection window)
            cutoff_time = time.time() - (self.config["detection_window_ms"] / 1000.0)
            self.shared_state_access[state_name] = [
                acc
                for acc in self.shared_state_access[state_name]
                if acc.timestamp > cutoff_time
            ]

            # Check for concurrent access
            self._check_concurrent_access(state_name)

    def _check_concurrent_access(self, state_name: str) -> None:
        """Check for concurrent access to shared state."""
        accesses = self.shared_state_access[state_name]

        if len(accesses) > self.config["max_concurrent_access"]:
            # Group by time windows
            time_windows = defaultdict(list)
            window_size = self.config["detection_window_ms"] / 1000.0

            for access in accesses:
                window_start = int(access.timestamp / window_size) * window_size
                time_windows[window_start].append(access)

            # Check each time window for concurrent access
            for window_start, window_accesses in time_windows.items():
                if len(window_accesses) > self.config["max_concurrent_access"]:
                    self._record_race_condition(
                        "concurrent_access",
                        f"Concurrent access to {state_name}",
                        {
                            "state_name": state_name,
                            "access_count": len(window_accesses),
                            "time_window": window_start,
                            "accesses": [
                                {
                                    "task_id": acc.task_id,
                                    "operation": acc.operation,
                                    "timestamp": acc.timestamp,
                                }
                                for acc in window_accesses
                            ],
                        },
                        "high",
                    )
                    self.metrics.concurrent_access_count += 1

    def track_lock_acquisition(self, lock_name: str, task_id: str | None = None) -> None:
        """Track lock acquisition."""
        if task_id is None:
            task_id = self._get_task_id()

        with self._lock:
            # Check for deadlock potential
            if task_id in self.lock_waiting[lock_name]:
                self._record_race_condition(
                    "potential_deadlock",
                    f"Potential deadlock detected for lock {lock_name}",
                    {
                        "lock_name": lock_name,
                        "task_id": task_id,
                        "waiting_tasks": list(self.lock_waiting[lock_name]),
                    },
                    "critical",
                )
                self.metrics.deadlock_detection_count += 1

            # Record lock acquisition
            self.active_locks[lock_name].add(task_id)
            self.lock_waiting[lock_name].discard(task_id)

            # Track lock contention
            if len(self.active_locks[lock_name]) > 1:
                self.metrics.lock_contention_count += 1
                self._record_race_condition(
                    "lock_contention",
                    f"Lock contention detected for {lock_name}",
                    {
                        "lock_name": lock_name,
                        "active_tasks": list(self.active_locks[lock_name]),
                    },
                    "medium",
                )

    def track_lock_waiting(self, lock_name: str, task_id: str | None = None) -> None:
        """Track task waiting for lock."""
        if task_id is None:
            task_id = self._get_task_id()

        with self._lock:
            self.lock_waiting[lock_name].add(task_id)

    def track_lock_release(self, lock_name: str, task_id: str | None = None) -> None:
        """Track lock release."""
        if task_id is None:
            task_id = self._get_task_id()

        with self._lock:
            self.active_locks[lock_name].discard(task_id)

    def _record_race_condition(self, event_type: str, location: str, details: dict[str, Any], severity: str) -> None:
        """Record a race condition event."""
        event = RaceConditionEvent(
            timestamp=time.time(),
            event_type=event_type,
            location=location,
            details=details,
            severity=severity,
            stack_trace=self._get_stack_trace()
            if self.config["enable_stack_trace"]
            else None,
            task_id=self._get_task_id(),
        )

        with self._lock:
            self.events.append(event)
            self.metrics.total_events += 1
            self.metrics.events_by_type[event_type] = (
                self.metrics.events_by_type.get(event_type, 0) + 1
            )
            self.metrics.events_by_severity[severity] = (
                self.metrics.events_by_severity.get(severity, 0) + 1
            )

        # Log the event
        log_level = getattr(logging, self.config["log_level"], logging.WARNING)
        logger.log(log_level, "Race condition detected: %s at %s", event_type, location)

    def get_metrics(self) -> RaceConditionMetrics:
        """Get current race condition metrics."""
        with self._lock:
            return self.metrics

    def get_recent_events(self, limit: int = 100) -> list[RaceConditionEvent]:
        """Get recent race condition events."""
        with self._lock:
            return list(self.events)[-limit:]

    def get_shared_state_summary(self) -> dict[str, Any]:
        """Get summary of shared state access patterns."""
        with self._lock:
            summary = {}
            for state_name, accesses in self.shared_state_access.items():
                if accesses:
                    recent_accesses = [
                        acc for acc in accesses if time.time() - acc.timestamp < 60
                    ]  # Last minute
                    summary[state_name] = {
                        "total_accesses": len(accesses),
                        "recent_accesses": len(recent_accesses),
                        "unique_tasks": len({acc.task_id for acc in accesses}),
                        "operations": list({acc.operation for acc in accesses}),
                    }
            return summary

    def clear_metrics(self) -> None:
        """Clear all metrics and events."""
        with self._lock:
            self.events.clear()
            self.shared_state_access.clear()
            self.active_locks.clear()
            self.lock_waiting.clear()
            self.task_dependencies.clear()
            self.metrics = RaceConditionMetrics()


# Global race condition monitor
_race_monitor = RaceConditionMonitor()


def get_race_monitor() -> RaceConditionMonitor:
    """Get the global race condition monitor."""
    return _race_monitor


class AsyncSafeLock:
    """Async-safe lock with race condition monitoring."""

    def __init__(self, name: str | None = None) -> None:
        self.name = name or f"lock_{id(self)}"
        self._lock = asyncio.Lock()
        self.monitor = get_race_monitor()

    async def __aenter__(self) -> None:
        self.monitor.track_lock_waiting(self.name)
        await self._lock.acquire()
        self.monitor.track_lock_acquisition(self.name)
        return self

    async def __aexit__(self) -> None:
        self.monitor.track_lock_release(self.name)
        self._lock.release()


class AsyncSafeSemaphore:
    """Async-safe semaphore with race condition monitoring."""

    def __init__(self, value: int, name: str | None = None) -> None:
        self.name = name or f"semaphore_{id(self)}"
        self._semaphore = asyncio.Semaphore(value)
        self.monitor = get_race_monitor()
        self.max_value = value

    async def acquire(self) -> None:
        """Acquire semaphore with monitoring."""
        self.monitor.track_lock_waiting(self.name)
        await self._semaphore.acquire()
        self.monitor.track_lock_acquisition(self.name)

    async def release(self) -> None:
        """Release semaphore with monitoring."""
        self.monitor.track_lock_release(self.name)
        self._semaphore.release()

    async def __aenter__(self) -> None:
        await self.acquire()
        return self

    async def __aexit__(self) -> None:
        await self.release()


class RaceConditionDetector:
    """Decorator-based race condition detector."""

    def __init__(self, monitor: RaceConditionMonitor | None = None) -> None:
        self.monitor = monitor or get_race_monitor()

    def track_shared_state(self, state_name: str) -> Callable:
        """Decorator to track shared state access."""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                self.monitor.track_shared_state_access(
                    state_name, f"call_{func.__name__}"
                )
                return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                self.monitor.track_shared_state_access(
                    state_name, f"call_{func.__name__}"
                )
                return func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def with_lock(self, lock_name: str) -> Callable:
        """Decorator to ensure function runs with a lock."""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with AsyncSafeLock(lock_name):
                    return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # For sync functions, we can't use async locks
                # This is a limitation - sync functions should use threading.Lock
                return func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator


# Convenience functions


def track_shared_state_access(state_name: str, operation: str) -> None:
    """Track access to shared state."""
    get_race_monitor().track_shared_state_access(state_name, operation)


def track_lock_acquisition(lock_name: str, task_id: str | None = None) -> None:
    """Track lock acquisition."""
    get_race_monitor().track_lock_acquisition(lock_name, task_id)


def track_lock_waiting(lock_name: str, task_id: str | None = None) -> None:
    """Track task waiting for lock."""
    get_race_monitor().track_lock_waiting(lock_name, task_id)


def track_lock_release(lock_name: str, task_id: str | None = None) -> None:
    """Track lock release."""
    get_race_monitor().track_lock_release(lock_name, task_id)


# Context managers for race condition monitoring


@asynccontextmanager
async def monitored_lock(lock_name: str) -> Any:
    """Context manager for monitored async lock."""
    monitor = get_race_monitor()
    monitor.track_lock_waiting(lock_name)

    try:
        async with asyncio.Lock() as lock:
            await lock.acquire()
            monitor.track_lock_acquisition(lock_name)
            yield lock
    finally:
        monitor.track_lock_release(lock_name)
        lock.release()


@asynccontextmanager
async def monitored_shared_state(state_name: str, operation: str) -> Any:
    """Context manager for monitored shared state access."""
    monitor = get_race_monitor()
    monitor.track_shared_state_access(state_name, operation)
    yield


# Utility functions for race condition analysis


def analyze_race_conditions(events: list[RaceConditionEvent]) -> dict[str, Any]:
    """Analyze race condition events for patterns."""
    analysis = {
        "total_events": len(events),
        "events_by_type": defaultdict(int),
        "events_by_severity": defaultdict(int),
        "time_distribution": defaultdict(int),
        "common_locations": defaultdict(int),
        "recommendations": [],
    }

    for event in events:
        analysis["events_by_type"][event.event_type] += 1
        analysis["events_by_severity"][event.severity] += 1

        # Group by time (hour buckets)
        hour_bucket = int(event.timestamp // 3600)
        analysis["time_distribution"][hour_bucket] += 1

        # Track common locations
        analysis["common_locations"][event.location] += 1

    # Generate recommendations
    if analysis["events_by_type"]["concurrent_access"] > 10:
        analysis["recommendations"].append(
            "Consider using async locks for shared state access"
        )

    if analysis["events_by_type"]["lock_contention"] > 5:
        analysis["recommendations"].append(
            "Review lock granularity - consider finer-grained locking"
        )

    if analysis["events_by_severity"]["critical"] > 0:
        analysis["recommendations"].append(
            "Critical race conditions detected - immediate attention required"
        )

    return analysis


def generate_race_condition_report(monitor: RaceConditionMonitor) -> str:
    """Generate a comprehensive race condition report."""
    metrics = monitor.get_metrics()
    events = monitor.get_recent_events(50)
    shared_state_summary = monitor.get_shared_state_summary()

    report = []
    report.append("=== Race Condition Monitoring Report ===")
    report.append(f"Total Events: {metrics.total_events}")
    report.append(f"Concurrent Access Violations: {metrics.concurrent_access_count}")
    report.append(f"Lock Contention Events: {metrics.lock_contention_count}")
    report.append(f"Deadlock Detection Events: {metrics.deadlock_detection_count}")

    report.append("\n--- Events by Type ---")
    for event_type, count in metrics.events_by_type.items():
        report.append(f"  {event_type}: {count}")

    report.append("\n--- Events by Severity ---")
    for severity, count in metrics.events_by_severity.items():
        report.append(f"  {severity}: {count}")

    report.append("\n--- Shared State Access Summary ---")
    for state_name, summary in shared_state_summary.items():
        report.append(f"  {state_name}:")
        report.append(f"    Total accesses: {summary['total_accesses']}")
        report.append(f"    Recent accesses: {summary['recent_accesses']}")
        report.append(f"    Unique tasks: {summary['unique_tasks']}")
        report.append(f"    Operations: {', '.join(summary['operations'])}")

    if events:
        report.append("\n--- Recent Events ---")
        for event in events[-10:]:  # Last 10 events
            report.append(
                f"  [{event.severity.upper()}] {event.event_type} at {event.location}"
            )
            report.append(f"    Time: {time.ctime(event.timestamp)}")
            if event.details:
                report.append(f"    Details: {event.details}")

    return "\n".join(report)


# Example usage and testing

if __name__ == "__main__":

    async def example_race_condition_detection(self) -> None:
        """Example of race condition detection."""
        print("Race Condition Detection Example")

        # Create a monitor
        monitor = RaceConditionMonitor()

        # Simulate concurrent access to shared state
        shared_counter = {"value": 0}

        async def unsafe_increment(self) -> None:
            # This will trigger race condition detection
            monitor.track_shared_state_access("counter", "read")
            current_value = shared_counter["value"]

            await asyncio.sleep(0.001)  # Simulate context switch

            monitor.track_shared_state_access("counter", "write")
            shared_counter["value"] = current_value + 1

        # Run multiple tasks concurrently
        tasks = [unsafe_increment() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Check results
        print(f"Final counter value: {shared_counter['value']}")

        # Get metrics
        metrics = monitor.get_metrics()
        print(f"Race condition events detected: {metrics.total_events}")
        print(f"Concurrent access violations: {metrics.concurrent_access_count}")

        # Generate report
        report = generate_race_condition_report(monitor)
        print("\nRace Condition Report:")
        print(report)

    # Run the example
    asyncio.run(example_race_condition_detection())
