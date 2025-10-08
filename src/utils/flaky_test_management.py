#!/usr/bin/env python3
"""PAKE System - Flaky Test Management System
Enterprise-grade flaky test tracking and resolution workflow.

This module implements the tactical retry policy with mandatory issue tracking
as specified in the enterprise testing standards.
"""

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import json
import logging
from pathlib import Path
import time
from typing import Any

import pytest

logger = logging.getLogger(__name__)


class FlakyTestStatus(Enum):
    """Status of flaky test resolution."""

    IDENTIFIED = "identified"
    INVESTIGATING = "investigating"
    REFACTORING = "refactoring"
    MOCKING = "mocking"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"  # Acceptable flakiness with proper documentation


class FailureMode(Enum):
    """Common failure modes for flaky tests."""

    TIMING_DEPENDENT = "timing_dependent"
    RACE_CONDITION = "race_condition"
    EXTERNAL_API = "external_api"
    RESOURCE_CONTENTION = "resource_contention"
    NETWORK_TIMEOUT = "network_timeout"
    DATABASE_CONNECTION = "database_connection"
    CACHE_INCONSISTENCY = "cache_inconsistency"
    CONCURRENT_EXECUTION = "concurrent_execution"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FlakyTestRecord:
    """Immutable record of a flaky test."""

    test_id: str
    test_name: str
    test_file: str
    failure_mode: FailureMode
    failure_rate: float
    first_detected: datetime
    last_failure: datetime
    total_failures: int
    total_runs: int
    retry_count: int
    resolution_status: FlakyTestStatus
    issue_ticket: str | None = None
    resolution_notes: str | None = None
    mock_implementation: str | None = None
    refactoring_notes: str | None = None
    accepted_reason: str | None = None


@dataclass
class FlakyTestMetrics:
    """Metrics for flaky test management."""

    total_flaky_tests: int = 0
    resolved_tests: int = 0
    accepted_tests: int = 0
    active_investigations: int = 0
    average_resolution_time_days: float = 0.0
    failure_rate_threshold: float = 0.1  # 10% failure rate threshold
    retry_success_rate: float = 0.0
    mock_coverage_rate: float = 0.0


class FlakyTestTracker:
    """Enterprise flaky test tracking and management system."""

    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.flaky_tests: dict[str, FlakyTestRecord] = {}
        self.test_failures: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.retry_attempts: dict[str, int] = defaultdict(int)
        self.metrics = FlakyTestMetrics()

        # Load existing data
        self._load_data()

        logger.info(
            "FlakyTestTracker initialized with %s known flaky tests",
            len(self.flaky_tests),
        )

    def _load_data(self) -> None:
        """Load flaky test data from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)

                for test_id, test_data in data.get("flaky_tests", {}).items():
                    # Convert datetime strings back to datetime objects
                    test_data["first_detected"] = datetime.fromisoformat(
                        test_data["first_detected"]
                    )
                    test_data["last_failure"] = datetime.fromisoformat(
                        test_data["last_failure"]
                    )
                    test_data["failure_mode"] = FailureMode(test_data["failure_mode"])
                    test_data["resolution_status"] = FlakyTestStatus(
                        test_data["resolution_status"]
                    )

                    self.flaky_tests[test_id] = FlakyTestRecord(**test_data)

                logger.info("Loaded %s flaky test records", len(self.flaky_tests))
            except (ValueError, RuntimeError) as e:
                logger.error("Failed to load flaky test data: %s", e)

    def _save_data(self) -> None:
        """Save flaky test data to storage."""
        try:
            data = {
                "flaky_tests": {},
                "metadata": {
                    "last_updated": datetime.now(UTC).isoformat(),
                    "version": "1.0",
                },
            }

            for test_id, test_record in self.flaky_tests.items():
                # Convert datetime objects to ISO strings for JSON serialization
                test_data = {
                    "test_id": test_record.test_id,
                    "test_name": test_record.test_name,
                    "test_file": test_record.test_file,
                    "failure_mode": test_record.failure_mode.value,
                    "failure_rate": test_record.failure_rate,
                    "first_detected": test_record.first_detected.isoformat(),
                    "last_failure": test_record.last_failure.isoformat(),
                    "total_failures": test_record.total_failures,
                    "total_runs": test_record.total_runs,
                    "retry_count": test_record.retry_count,
                    "resolution_status": test_record.resolution_status.value,
                    "issue_ticket": test_record.issue_ticket,
                    "resolution_notes": test_record.resolution_notes,
                    "mock_implementation": test_record.mock_implementation,
                    "refactoring_notes": test_record.refactoring_notes,
                    "accepted_reason": test_record.accepted_reason,
                }
                data["flaky_tests"][test_id] = test_data

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Failed to save flaky test data: %s", e)

    def record_test_failure(
        self,
        test_id: str,
        test_name: str,
        test_file: str,
        error_message: str,
        failure_mode: FailureMode = FailureMode.UNKNOWN,
    ) -> None:
        """Record a test failure for flaky test analysis."""
        current_time = datetime.now(UTC)

        # Record failure
        self.test_failures[test_id].append(
            {
                "timestamp": current_time,
                "error_message": error_message,
                "failure_mode": failure_mode,
            }
        )

        # Update or create flaky test record
        if test_id in self.flaky_tests:
            existing_record = self.flaky_tests[test_id]

            # Update existing record
            updated_record = FlakyTestRecord(
                test_id=existing_record.test_id,
                test_name=existing_record.test_name,
                test_file=existing_record.test_file,
                failure_mode=failure_mode
                if failure_mode != FailureMode.UNKNOWN
                else existing_record.failure_mode,
                failure_rate=self._calculate_failure_rate(test_id),
                first_detected=existing_record.first_detected,
                last_failure=current_time,
                total_failures=existing_record.total_failures + 1,
                total_runs=existing_record.total_runs + 1,
                retry_count=self.retry_attempts[test_id],
                resolution_status=existing_record.resolution_status,
                issue_ticket=existing_record.issue_ticket,
                resolution_notes=existing_record.resolution_notes,
                mock_implementation=existing_record.mock_implementation,
                refactoring_notes=existing_record.refactoring_notes,
                accepted_reason=existing_record.accepted_reason,
            )
            self.flaky_tests[test_id] = updated_record
        else:
            # Create new flaky test record
            new_record = FlakyTestRecord(
                test_id=test_id,
                test_name=test_name,
                test_file=test_file,
                failure_mode=failure_mode,
                failure_rate=1.0,  # First failure = 100% failure rate
                first_detected=current_time,
                last_failure=current_time,
                total_failures=1,
                total_runs=1,
                retry_count=self.retry_attempts[test_id],
                resolution_status=FlakyTestStatus.IDENTIFIED,
            )
            self.flaky_tests[test_id] = new_record

            logger.warning("New flaky test identified: %s in %s", test_name, test_file)

        # Save data
        self._save_data()

    def record_test_success(self, test_id: str) -> None:
        """Record a successful test run."""
        if test_id in self.flaky_tests:
            existing_record = self.flaky_tests[test_id]

            updated_record = FlakyTestRecord(
                test_id=existing_record.test_id,
                test_name=existing_record.test_name,
                test_file=existing_record.test_file,
                failure_mode=existing_record.failure_mode,
                failure_rate=self._calculate_failure_rate(test_id),
                first_detected=existing_record.first_detected,
                last_failure=existing_record.last_failure,
                total_failures=existing_record.total_failures,
                total_runs=existing_record.total_runs + 1,
                retry_count=self.retry_attempts[test_id],
                resolution_status=existing_record.resolution_status,
                issue_ticket=existing_record.issue_ticket,
                resolution_notes=existing_record.resolution_notes,
                mock_implementation=existing_record.mock_implementation,
                refactoring_notes=existing_record.refactoring_notes,
                accepted_reason=existing_record.accepted_reason,
            )
            self.flaky_tests[test_id] = updated_record

            self._save_data()

    def record_retry_attempt(self, test_id: str) -> None:
        """Record a retry attempt."""
        self.retry_attempts[test_id] += 1

    def _calculate_failure_rate(self, test_id: str) -> float:
        """Calculate failure rate for a test."""
        failures = len(self.test_failures[test_id])
        total_runs = failures + max(0, self.retry_attempts[test_id])
        return failures / max(total_runs, 1)

    def should_retry_test(self, test_id: str) -> bool:
        """Determine if a test should be retried based on enterprise policy."""
        if test_id not in self.flaky_tests:
            return True  # Unknown test, allow retry

        record = self.flaky_tests[test_id]

        # Don't retry if already resolved or accepted
        if record.resolution_status in [
            FlakyTestStatus.RESOLVED,
            FlakyTestStatus.ACCEPTED,
        ]:
            return False

        # Don't retry if too many retries already attempted
        if record.retry_count >= 3:
            logger.warning("Test %s has exceeded maximum retry attempts", test_id)
            return False

        # Retry if failure rate is above threshold
        return record.failure_rate >= self.metrics.failure_rate_threshold

    def create_issue_ticket(
        self, test_id: str, issue_tracker_url: str | None = None
    ) -> str:
        """Create an issue ticket for a flaky test (mandatory per policy)."""
        if test_id not in self.flaky_tests:
            msg = f"Test {test_id} not found in flaky test records"
            raise ValueError(msg)

        record = self.flaky_tests[test_id]

        # Generate ticket ID (in real implementation, this would call issue tracker API)
        ticket_id = f"FLAKY-{test_id.upper()}-{int(time.time())}"

        # Update record with ticket
        updated_record = FlakyTestRecord(
            test_id=record.test_id,
            test_name=record.test_name,
            test_file=record.test_file,
            failure_mode=record.failure_mode,
            failure_rate=record.failure_rate,
            first_detected=record.first_detected,
            last_failure=record.last_failure,
            total_failures=record.total_failures,
            total_runs=record.total_runs,
            retry_count=record.retry_count,
            resolution_status=FlakyTestStatus.INVESTIGATING,
            issue_ticket=ticket_id,
            resolution_notes=record.resolution_notes,
            mock_implementation=record.mock_implementation,
            refactoring_notes=record.refactoring_notes,
            accepted_reason=record.accepted_reason,
        )
        self.flaky_tests[test_id] = updated_record

        logger.info("Created issue ticket %s for flaky test %s", ticket_id, test_id)
        self._save_data()

        return ticket_id

    def update_resolution_status(
        self,
        test_id: str,
        status: FlakyTestStatus,
        notes: str | None = None,
        mock_implementation: str | None = None,
        refactoring_notes: str | None = None,
        accepted_reason: str | None = None,
    ) -> None:
        """Update the resolution status of a flaky test."""
        if test_id not in self.flaky_tests:
            msg = f"Test {test_id} not found in flaky test records"
            raise ValueError(msg)

        record = self.flaky_tests[test_id]

        updated_record = FlakyTestRecord(
            test_id=record.test_id,
            test_name=record.test_name,
            test_file=record.test_file,
            failure_mode=record.failure_mode,
            failure_rate=record.failure_rate,
            first_detected=record.first_detected,
            last_failure=record.last_failure,
            total_failures=record.total_failures,
            total_runs=record.total_runs,
            retry_count=record.retry_count,
            resolution_status=status,
            issue_ticket=record.issue_ticket,
            resolution_notes=notes or record.resolution_notes,
            mock_implementation=mock_implementation or record.mock_implementation,
            refactoring_notes=refactoring_notes or record.refactoring_notes,
            accepted_reason=accepted_reason or record.accepted_reason,
        )
        self.flaky_tests[test_id] = updated_record

        logger.info("Updated resolution status for %s to %s", test_id, status.value)
        self._save_data()

    def get_flaky_tests_by_status(
        self, status: FlakyTestStatus
    ) -> list[FlakyTestRecord]:
        """Get all flaky tests with a specific status."""
        return [
            record
            for record in self.flaky_tests.values()
            if record.resolution_status == status
        ]

    def get_flaky_tests_by_failure_mode(
        self, failure_mode: FailureMode
    ) -> list[FlakyTestRecord]:
        """Get all flaky tests with a specific failure mode."""
        return [
            record
            for record in self.flaky_tests.values()
            if record.failure_mode == failure_mode
        ]

    def get_metrics(self) -> FlakyTestMetrics:
        """Get current flaky test metrics."""
        total_tests = len(self.flaky_tests)
        resolved_tests = len(self.get_flaky_tests_by_status(FlakyTestStatus.RESOLVED))
        accepted_tests = len(self.get_flaky_tests_by_status(FlakyTestStatus.ACCEPTED))
        investigating_tests = len(
            self.get_flaky_tests_by_status(FlakyTestStatus.INVESTIGATING)
        )

        # Calculate average resolution time
        resolved_records = self.get_flaky_tests_by_status(FlakyTestStatus.RESOLVED)
        if resolved_records:
            resolution_times = [
                (record.last_failure - record.first_detected).total_seconds()
                / 86400  # Convert to days
                for record in resolved_records
            ]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        else:
            avg_resolution_time = 0.0

        # Calculate retry success rate
        total_retries = sum(record.retry_count for record in self.flaky_tests.values())
        successful_retries = sum(
            record.total_runs - record.total_failures
            for record in self.flaky_tests.values()
        )
        retry_success_rate = successful_retries / max(total_retries, 1)

        # Calculate mock coverage rate
        mocked_tests = len(
            [
                record
                for record in self.flaky_tests.values()
                if record.mock_implementation is not None
            ]
        )
        mock_coverage_rate = mocked_tests / max(total_tests, 1)

        return FlakyTestMetrics(
            total_flaky_tests=total_tests,
            resolved_tests=resolved_tests,
            accepted_tests=accepted_tests,
            active_investigations=investigating_tests,
            average_resolution_time_days=avg_resolution_time,
            retry_success_rate=retry_success_rate,
            mock_coverage_rate=mock_coverage_rate,
        )

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive flaky test report."""
        metrics = self.get_metrics()

        report = {
            "summary": {
                "total_flaky_tests": metrics.total_flaky_tests,
                "resolved_tests": metrics.resolved_tests,
                "accepted_tests": metrics.accepted_tests,
                "active_investigations": metrics.active_investigations,
                "resolution_rate": (metrics.resolved_tests + metrics.accepted_tests)
                / max(metrics.total_flaky_tests, 1),
                "average_resolution_time_days": metrics.average_resolution_time_days,
                "retry_success_rate": metrics.retry_success_rate,
                "mock_coverage_rate": metrics.mock_coverage_rate,
            },
            "by_status": {},
            "by_failure_mode": {},
            "top_flaky_tests": [],
            "recommendations": [],
        }

        # Group by status
        for status in FlakyTestStatus:
            tests = self.get_flaky_tests_by_status(status)
            report["by_status"][status.value] = {
                "count": len(tests),
                "tests": [
                    {
                        "test_name": t.test_name,
                        "test_file": t.test_file,
                        "failure_rate": t.failure_rate,
                    }
                    for t in tests
                ],
            }

        # Group by failure mode
        for failure_mode in FailureMode:
            tests = self.get_flaky_tests_by_failure_mode(failure_mode)
            report["by_failure_mode"][failure_mode.value] = {
                "count": len(tests),
                "tests": [
                    {
                        "test_name": t.test_name,
                        "test_file": t.test_file,
                        "failure_rate": t.failure_rate,
                    }
                    for t in tests
                ],
            }

        # Top flaky tests (highest failure rate)
        sorted_tests = sorted(
            self.flaky_tests.values(), key=lambda x: x.failure_rate, reverse=True
        )
        report["top_flaky_tests"] = [
            {
                "test_name": t.test_name,
                "test_file": t.test_file,
                "failure_rate": t.failure_rate,
                "total_failures": t.total_failures,
                "status": t.resolution_status.value,
            }
            for t in sorted_tests[:10]
        ]

        # Generate recommendations
        recommendations = []

        if metrics.mock_coverage_rate < 0.8:
            recommendations.append("Increase mock coverage for external dependencies")

        if metrics.average_resolution_time_days > 7:
            recommendations.append("Improve resolution time for flaky tests")

        if metrics.retry_success_rate < 0.5:
            recommendations.append("Review retry strategy effectiveness")

        race_condition_tests = self.get_flaky_tests_by_failure_mode(
            FailureMode.RACE_CONDITION
        )
        if len(race_condition_tests) > 0:
            recommendations.append(
                f"Address {len(race_condition_tests)} race condition issues"
            )

        report["recommendations"] = recommendations

        return report


# Global flaky test tracker instance
_flaky_tracker = FlakyTestTracker()


def get_flaky_tracker() -> FlakyTestTracker:
    """Get the global flaky test tracker."""
    return _flaky_tracker


# Pytest hooks for automatic flaky test detection
def pytest_runtest_setup(item: Any) -> None:
    """Pytest hook called before each test."""
    test_id = f"{item.nodeid}"
    tracker = get_flaky_tracker()

    # Check if test should be retried
    if not tracker.should_retry_test(test_id):
        pytest.skip(f"Test {test_id} marked as non-retryable due to enterprise policy")


def pytest_runtest_logreport(report: Any) -> None:
    """Pytest hook called after each test report."""
    if report.when == "call":  # Only process actual test execution
        test_id = f"{report.nodeid}"
        tracker = get_flaky_tracker()

        if report.failed:
            # Determine failure mode
            failure_mode = FailureMode.UNKNOWN
            error_message = str(report.longrepr) if report.longrepr else "Unknown error"

            if "timeout" in error_message.lower():
                failure_mode = FailureMode.TIMING_DEPENDENT
            elif (
                "race" in error_message.lower() or "concurrent" in error_message.lower()
            ):
                failure_mode = FailureMode.RACE_CONDITION
            elif (
                "connection" in error_message.lower()
                or "network" in error_message.lower()
            ):
                failure_mode = FailureMode.NETWORK_TIMEOUT
            elif "database" in error_message.lower():
                failure_mode = FailureMode.DATABASE_CONNECTION
            elif "cache" in error_message.lower():
                failure_mode = FailureMode.CACHE_INCONSISTENCY

            # Record failure
            tracker.record_test_failure(
                test_id=test_id,
                test_name=report.nodeid,
                test_file=report.fspath,
                error_message=error_message,
                failure_mode=failure_mode,
            )

            # Record retry attempt
            tracker.record_retry_attempt(test_id)

        elif report.passed:
            # Record success
            tracker.record_test_success(test_id)


# Decorator for marking tests as flaky
def flaky_test(
    failure_mode: FailureMode = FailureMode.UNKNOWN,
    max_retries: int = 3,
    issue_ticket: str | None = None,
) -> Callable:
    """Decorator for marking tests as flaky with enterprise policy compliance."""

    def decorator(func: Callable) -> Callable:
        # Add pytest markers
        func = pytest.mark.flaky(func)
        func = pytest.mark.retry_on_failure(func)

        # Store metadata
        func._flaky_metadata = {
            "failure_mode": failure_mode,
            "max_retries": max_retries,
            "issue_ticket": issue_ticket,
        }

        return func

    return decorator


# Utility functions for test developers
def create_mock_for_flaky_test(test_name: str, external_dependency: str) -> str:
    """Generate mock implementation for external dependencies."""
    return f"""
# Mock implementation for {test_name}
# Replaces external dependency: {external_dependency}

from unittest.mock import AsyncMock, Mock

class Mock{external_dependency}:
    def __init__(self) -> None:
        self.mock_instance = AsyncMock() if 'async' in {external_dependency}.lower() else Mock()

    def __getattr__(self) -> None:
        return getattr(self.mock_instance, name)

# Usage in test:
# mock_dependency = Mock{external_dependency}()
# with patch('module.{external_dependency}', mock_dependency):
#     # Your test code here
"""


def analyze_race_condition(test_name: str, shared_state_vars: list[str]) -> str:
    """Generate analysis and fix for race conditions."""
    return f"""
# Race Condition Analysis for {test_name}

## Identified Shared State Variables:
{chr(10).join(f"- {var}" for var in shared_state_vars)}

## Recommended Fixes:

1. Use asyncio.Lock for async code:
```python
import asyncio
from src.utils.synchronization_primitives import AsyncLockManager

lock_manager = AsyncLockManager()

async def protected_operation(self) -> None:
    async with async_lock_context(lock_manager, "shared_state_lock"):
        # Access shared state here
```

2. Use threading.Lock for thread-based code:
```python
import threading
from src.utils.synchronization_primitives import ThreadSafeCounter

counter = ThreadSafeCounter()

def protected_operation(self) -> None:
    with thread_lock_context(counter._lock):
        # Access shared state here
```

3. Use AsyncSafeDict for async-safe data structures:
```python
from src.utils.synchronization_primitives import AsyncSafeDict

safe_dict = AsyncSafeDict()
await safe_dict.set("key", "value")
value = await safe_dict.get("key")
```
"""


if __name__ == "__main__":
    # Example usage
    tracker = get_flaky_tracker()

    # Simulate some test failures
    tracker.record_test_failure(
        test_id="test_example_race_condition",
        test_name="test_example_race_condition",
        test_file="tests/unit/test_example.py",
        error_message="Race condition detected in shared counter",
        failure_mode=FailureMode.RACE_CONDITION,
    )

    # Create issue ticket
    ticket_id = tracker.create_issue_ticket("test_example_race_condition")
    print(f"Created ticket: {ticket_id}")

    # Generate report
    report = tracker.generate_report()
    print(f"Flaky test report: {json.dumps(report, indent=2)}")

    print("Flaky test management system example completed!")
