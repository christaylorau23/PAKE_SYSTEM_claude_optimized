#!/usr/bin/env python3
"""Flaky Test Tracking and Technical Debt Management for PAKE System
Comprehensive system for tracking, analyzing, and managing flaky tests and technical debt.
"""

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

logger = logging.getLogger("flaky_test_tracker")


class TestStatus(Enum):
    """Status of a test."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    FLAKY = "flaky"


class FlakySeverity(Enum):
    """Severity of flaky test."""

    LOW = "low"  # Fails < 5% of the time
    MEDIUM = "medium"  # Fails 5-20% of the time
    HIGH = "high"  # Fails 20-50% of the time
    CRITICAL = "critical"  # Fails > 50% of the time


class TechnicalDebtPriority(Enum):
    """Priority of technical debt."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestExecution:
    """Represents a single test execution."""

    test_id: str
    test_name: str
    status: TestStatus
    execution_time: float
    timestamp: datetime
    retry_count: int = 0
    error_message: str | None = None
    stack_trace: str | None = None
    environment: str = "unknown"
    commit_hash: str | None = None
    branch: str | None = None


@dataclass
class FlakyTestRecord:
    """Record of a flaky test."""

    test_id: str
    test_name: str
    total_executions: int
    failed_executions: int
    flaky_severity: FlakySeverity
    first_detected: datetime
    last_occurrence: datetime
    failure_patterns: list[str] = field(default_factory=list)
    retry_success_rate: float = 0.0
    average_execution_time: float = 0.0
    technical_debt_ticket: str | None = None
    assigned_engineer: str | None = None
    estimated_fix_time: int | None = None  # hours


@dataclass
class TechnicalDebtTicket:
    """Technical debt ticket for flaky tests."""

    ticket_id: str
    title: str
    description: str
    priority: TechnicalDebtPriority
    test_ids: list[str]
    created_date: datetime
    due_date: datetime | None = None
    assigned_engineer: str | None = None
    status: str = "open"
    estimated_hours: int | None = None
    actual_hours: int | None = None
    resolution_notes: str | None = None


class FlakyTestTracker:
    """Comprehensive flaky test tracking and management system."""

    def __init__(self) -> None:
        self.db_path = db_path
        self._init_database()

        # In-memory cache for performance
        self._test_cache: dict[str, FlakyTestRecord] = {}
        self._cache_dirty = False

        logger.info("Flaky test tracker initialized with database: %s", db_path)

    def _init_database(self) -> None:
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Test executions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    stack_trace TEXT,
                    environment TEXT DEFAULT 'unknown',
                    commit_hash TEXT,
                    branch TEXT
                )
            """
            )

            # Flaky tests table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS flaky_tests (
                    test_id TEXT PRIMARY KEY,
                    test_name TEXT NOT NULL,
                    total_executions INTEGER DEFAULT 0,
                    failed_executions INTEGER DEFAULT 0,
                    flaky_severity TEXT NOT NULL,
                    first_detected TEXT NOT NULL,
                    last_occurrence TEXT NOT NULL,
                    failure_patterns TEXT DEFAULT '[]',
                    retry_success_rate REAL DEFAULT 0.0,
                    average_execution_time REAL DEFAULT 0.0,
                    technical_debt_ticket TEXT,
                    assigned_engineer TEXT,
                    estimated_fix_time INTEGER
                )
            """
            )

            # Technical debt tickets table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS technical_debt_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    test_ids TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    due_date TEXT,
                    assigned_engineer TEXT,
                    status TEXT DEFAULT 'open',
                    estimated_hours INTEGER,
                    actual_hours INTEGER,
                    resolution_notes TEXT
                )
            """
            )

            # Create indexes for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_executions_test_id ON test_executions(test_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_executions_timestamp ON test_executions(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_executions_status ON test_executions(status)"
            )

            conn.commit()

    def record_test_execution(self) -> None:
        """Record a test execution."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO test_executions
                (test_id, test_name, status, execution_time, timestamp, retry_count,
                 error_message, stack_trace, environment, commit_hash, branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    execution.test_id,
                    execution.test_name,
                    execution.status.value,
                    execution.execution_time,
                    execution.timestamp.isoformat(),
                    execution.retry_count,
                    execution.error_message,
                    execution.stack_trace,
                    execution.environment,
                    execution.commit_hash,
                    execution.branch,
                ),
            )
            conn.commit()

        # Update cache
        self._update_test_cache(execution)

    def _update_test_cache(self) -> None:
        """Update the in-memory cache for a test."""
        test_id = execution.test_id

        if test_id not in self._test_cache:
            self._test_cache[test_id] = FlakyTestRecord(
                test_id=test_id,
                test_name=execution.test_name,
                total_executions=0,
                failed_executions=0,
                flaky_severity=FlakySeverity.LOW,
                first_detected=execution.timestamp,
                last_occurrence=execution.timestamp,
            )

        record = self._test_cache[test_id]
        record.total_executions += 1

        if execution.status in [TestStatus.FAILED, TestStatus.ERROR]:
            record.failed_executions += 1
            record.last_occurrence = execution.timestamp

            # Update failure patterns
            if execution.error_message:
                pattern = self._extract_failure_pattern(execution.error_message)
                if pattern not in record.failure_patterns:
                    record.failure_patterns.append(pattern)

        # Update flaky severity
        failure_rate = record.failed_executions / record.total_executions
        record.flaky_severity = self._calculate_flaky_severity(failure_rate)

        # Update retry success rate
        if execution.retry_count > 0:
            record.retry_success_rate = self._calculate_retry_success_rate(test_id)

        # Update average execution time
        record.average_execution_time = self._calculate_average_execution_time(test_id)

        self._cache_dirty = True

    def _extract_failure_pattern(self, error_message: str) -> str:
        """Extract a pattern from error message."""
        # Simple pattern extraction - can be enhanced
        if "timeout" in error_message.lower():
            return "timeout"
        if "connection" in error_message.lower():
            return "connection_error"
        if "assertion" in error_message.lower():
            return "assertion_failure"
        if "race" in error_message.lower():
            return "race_condition"
        return "unknown_error"

    def _calculate_flaky_severity(self, failure_rate: float) -> FlakySeverity:
        """Calculate flaky severity based on failure rate."""
        if failure_rate >= 0.5:
            return FlakySeverity.CRITICAL
        if failure_rate >= 0.2:
            return FlakySeverity.HIGH
        if failure_rate >= 0.05:
            return FlakySeverity.MEDIUM
        return FlakySeverity.LOW

    def _calculate_retry_success_rate(self, test_id: str) -> float:
        """Calculate retry success rate for a test."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM test_executions
                WHERE test_id = ? AND retry_count > 0 AND status = ?
            """,
                (test_id, TestStatus.PASSED.value),
            )
            successful_retries = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*) FROM test_executions
                WHERE test_id = ? AND retry_count > 0
            """,
                (test_id,),
            )
            total_retries = cursor.fetchone()[0]

            return successful_retries / total_retries if total_retries > 0 else 0.0

    def _calculate_average_execution_time(self, test_id: str) -> float:
        """Calculate average execution time for a test."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT AVG(execution_time) FROM test_executions
                WHERE test_id = ?
            """,
                (test_id,),
            )
            result = cursor.fetchone()[0]
            return result if result else 0.0

    def get_flaky_tests(self, severity: FlakySeverity = None) -> list[FlakyTestRecord]:
        """Get flaky tests, optionally filtered by severity."""
        self._sync_cache_to_db()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if severity:
                cursor.execute(
                    """
                    SELECT * FROM flaky_tests
                    WHERE flaky_severity = ? AND total_executions >= 5
                    ORDER BY failed_executions DESC
                """,
                    (severity.value,),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM flaky_tests
                    WHERE total_executions >= 5
                    ORDER BY failed_executions DESC
                """
                )

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            tests = []
            for row in rows:
                data = dict(zip(columns, row, strict=False))
                tests.append(
                    FlakyTestRecord(
                        test_id=data["test_id"],
                        test_name=data["test_name"],
                        total_executions=data["total_executions"],
                        failed_executions=data["failed_executions"],
                        flaky_severity=FlakySeverity(data["flaky_severity"]),
                        first_detected=datetime.fromisoformat(data["first_detected"]),
                        last_occurrence=datetime.fromisoformat(data["last_occurrence"]),
                        failure_patterns=json.loads(data["failure_patterns"]),
                        retry_success_rate=data["retry_success_rate"],
                        average_execution_time=data["average_execution_time"],
                        technical_debt_ticket=data["technical_debt_ticket"],
                        assigned_engineer=data["assigned_engineer"],
                        estimated_fix_time=data["estimated_fix_time"],
                    )
                )

            return tests

    def _sync_cache_to_db(self) -> None:
        """Sync cache to database."""
        if not self._cache_dirty:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for _test_id, record in self._test_cache.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO flaky_tests
                    (test_id, test_name, total_executions, failed_executions,
                     flaky_severity, first_detected, last_occurrence, failure_patterns,
                     retry_success_rate, average_execution_time, technical_debt_ticket,
                     assigned_engineer, estimated_fix_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record.test_id,
                        record.test_name,
                        record.total_executions,
                        record.failed_executions,
                        record.flaky_severity.value,
                        record.first_detected.isoformat(),
                        record.last_occurrence.isoformat(),
                        json.dumps(record.failure_patterns),
                        record.retry_success_rate,
                        record.average_execution_time,
                        record.technical_debt_ticket,
                        record.assigned_engineer,
                        record.estimated_fix_time,
                    ),
                )

            conn.commit()
            self._cache_dirty = False

    def create_technical_debt_ticket(self) -> None:
        """Create a technical debt ticket."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO technical_debt_tickets
                (ticket_id, title, description, priority, test_ids, created_date,
                 due_date, assigned_engineer, status, estimated_hours, actual_hours, resolution_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ticket.ticket_id,
                    ticket.title,
                    ticket.description,
                    ticket.priority.value,
                    json.dumps(ticket.test_ids),
                    ticket.created_date.isoformat(),
                    ticket.due_date.isoformat() if ticket.due_date else None,
                    ticket.assigned_engineer,
                    ticket.status,
                    ticket.estimated_hours,
                    ticket.actual_hours,
                    ticket.resolution_notes,
                ),
            )
            conn.commit()

    def get_technical_debt_tickets(
        self, status: str = None
    ) -> list[TechnicalDebtTicket]:
        """Get technical debt tickets."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    """
                    SELECT * FROM technical_debt_tickets
                    WHERE status = ?
                    ORDER BY created_date DESC
                """,
                    (status,),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM technical_debt_tickets
                    ORDER BY created_date DESC
                """
                )

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            tickets = []
            for row in rows:
                data = dict(zip(columns, row, strict=False))
                tickets.append(
                    TechnicalDebtTicket(
                        ticket_id=data["ticket_id"],
                        title=data["title"],
                        description=data["description"],
                        priority=TechnicalDebtPriority(data["priority"]),
                        test_ids=json.loads(data["test_ids"]),
                        created_date=datetime.fromisoformat(data["created_date"]),
                        due_date=datetime.fromisoformat(data["due_date"])
                        if data["due_date"]
                        else None,
                        assigned_engineer=data["assigned_engineer"],
                        status=data["status"],
                        estimated_hours=data["estimated_hours"],
                        actual_hours=data["actual_hours"],
                        resolution_notes=data["resolution_notes"],
                    )
                )

            return tickets

    def generate_flaky_test_report(self) -> str:
        """Generate a comprehensive flaky test report."""
        flaky_tests = self.get_flaky_tests()
        tickets = self.get_technical_debt_tickets()

        report = []
        report.append("=== Flaky Test Report ===")
        report.append(f"Generated: {datetime.now(UTC).isoformat()}")
        report.append(f"Total flaky tests: {len(flaky_tests)}")
        report.append(
            f"Open technical debt tickets: {len([t for t in tickets if t.status == 'open'])}"
        )

        # Group by severity
        by_severity = {}
        for test in flaky_tests:
            severity = test.flaky_severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(test)

        report.append("\n--- Tests by Severity ---")
        for severity in [
            FlakySeverity.CRITICAL,
            FlakySeverity.HIGH,
            FlakySeverity.MEDIUM,
            FlakySeverity.LOW,
        ]:
            tests = by_severity.get(severity.value, [])
            report.append(f"  {severity.value.upper()}: {len(tests)} tests")

            for test in tests[:5]:  # Show top 5
                report.append(f"    - {test.test_name}")
                report.append(
                    f"      Failure rate: {test.failed_executions}/{test.total_executions} ({test.failed_executions / test.total_executions:.1%})"
                )
                report.append(f"      Patterns: {', '.join(test.failure_patterns)}")
                if test.technical_debt_ticket:
                    report.append(f"      Ticket: {test.technical_debt_ticket}")

        # Technical debt summary
        report.append("\n--- Technical Debt Summary ---")
        open_tickets = [t for t in tickets if t.status == "open"]
        if open_tickets:
            report.append(f"Open tickets: {len(open_tickets)}")
            for ticket in open_tickets[:3]:  # Show top 3
                report.append(f"  - {ticket.title} ({ticket.priority.value})")
                report.append(f"    Tests: {len(ticket.test_ids)}")
                if ticket.assigned_engineer:
                    report.append(f"    Assigned to: {ticket.assigned_engineer}")
        else:
            report.append("No open technical debt tickets")

        return "\n".join(report)


# Global flaky test tracker
_flaky_tracker = FlakyTestTracker()


def get_flaky_tracker() -> FlakyTestTracker:
    """Get the global flaky test tracker."""
    return _flaky_tracker


# Pytest integration


class FlakyTestPlugin:
    """Pytest plugin for flaky test tracking."""

    def __init__(self) -> None:
        self.tracker = get_flaky_tracker()
        self.start_times = {}

    def pytest_runtest_setup(self) -> None:
        """Called before each test."""
        self.start_times[item.nodeid] = time.time()

    def pytest_runtest_logreport(self) -> None:
        """Called after each test report."""
        if report.when == "call":  # Only track the actual test call
            test_id = report.nodeid
            test_name = report.nodeid.split("::")[-1]

            execution_time = time.time() - self.start_times.get(test_id, time.time())

            # Determine status
            if report.passed:
                status = TestStatus.PASSED
            elif report.failed:
                status = TestStatus.FAILED
            elif report.skipped:
                status = TestStatus.SKIPPED
            else:
                status = TestStatus.ERROR

            # Create execution record
            execution = TestExecution(
                test_id=test_id,
                test_name=test_name,
                status=status,
                execution_time=execution_time,
                timestamp=datetime.now(UTC),
                retry_count=getattr(report, "retry_count", 0),
                error_message=str(report.longrepr)
                if hasattr(report, "longrepr") and report.longrepr
                else None,
                stack_trace=str(report.longrepr)
                if hasattr(report, "longrepr") and report.longrepr
                else None,
                environment=os.getenv("TEST_ENVIRONMENT", "unknown"),
                commit_hash=os.getenv("GIT_COMMIT", None),
                branch=os.getenv("GIT_BRANCH", None),
            )

            # Record the execution
            self.tracker.record_test_execution(execution)


# Utility functions


def create_technical_debt_ticket_for_flaky_tests(
    test_ids: list[str],
    title: str,
    description: str,
    priority: TechnicalDebtPriority = TechnicalDebtPriority.MEDIUM,
    assigned_engineer: str = None,
    estimated_hours: int = None,
) -> TechnicalDebtTicket:
    """Create a technical debt ticket for flaky tests."""
    ticket_id = f"TD-{int(time.time())}"

    ticket = TechnicalDebtTicket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        priority=priority,
        test_ids=test_ids,
        created_date=datetime.now(UTC),
        assigned_engineer=assigned_engineer,
        estimated_hours=estimated_hours,
    )

    tracker = get_flaky_tracker()
    tracker.create_technical_debt_ticket(ticket)

    # Update flaky test records with ticket reference
    for test_id in test_ids:
        if test_id in tracker._test_cache:
            tracker._test_cache[test_id].technical_debt_ticket = ticket_id
            tracker._test_cache[test_id].assigned_engineer = assigned_engineer
            tracker._test_cache[test_id].estimated_fix_time = estimated_hours
            tracker._cache_dirty = True

    return ticket


def auto_create_technical_debt_tickets(self) -> None:
    """Automatically create technical debt tickets for high-severity flaky tests."""
    tracker = get_flaky_tracker()
    flaky_tests = tracker.get_flaky_tests(FlakySeverity.HIGH)

    # Group tests by failure patterns
    pattern_groups = {}
    for test in flaky_tests:
        if not test.technical_debt_ticket:  # Only create tickets for tests without them
            pattern = test.failure_patterns[0] if test.failure_patterns else "unknown"
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(test)

    created_tickets = []
    for pattern, tests in pattern_groups.items():
        if len(tests) >= 2:  # Only create tickets for patterns with multiple tests
            ticket = create_technical_debt_ticket_for_flaky_tests(
                test_ids=[test.test_id for test in tests],
                title=f"Fix {pattern} flaky tests",
                description=f"Address {len(tests)} flaky tests with {pattern} failure pattern",
                priority=FlakySeverity.CRITICAL
                if any(t.flaky_severity == FlakySeverity.CRITICAL for t in tests)
                else TechnicalDebtPriority.HIGH,
                estimated_hours=len(tests) * 2,  # Estimate 2 hours per test
            )
            created_tickets.append(ticket)

    return created_tickets


# Example usage

if __name__ == "__main__":
    # Example of using the flaky test tracker
    tracker = FlakyTestTracker("example_flaky_tests.db")

    # Simulate some test executions
    test_executions = [
        TestExecution(
            test_id="test_example_1",
            test_name="test_example_1",
            status=TestStatus.PASSED,
            execution_time=0.1,
            timestamp=datetime.now(UTC) - timedelta(days=1),
        ),
        TestExecution(
            test_id="test_example_1",
            test_name="test_example_1",
            status=TestStatus.FAILED,
            execution_time=0.2,
            timestamp=datetime.now(UTC) - timedelta(hours=12),
            error_message="AssertionError: Expected 5, got 4",
        ),
        TestExecution(
            test_id="test_example_1",
            test_name="test_example_1",
            status=TestStatus.PASSED,
            execution_time=0.15,
            timestamp=datetime.now(UTC) - timedelta(hours=6),
            retry_count=1,
        ),
        TestExecution(
            test_id="test_example_2",
            test_name="test_example_2",
            status=TestStatus.FAILED,
            execution_time=0.3,
            timestamp=datetime.now(UTC) - timedelta(hours=3),
            error_message="TimeoutError: Operation timed out",
        ),
    ]

    # Record executions
    for execution in test_executions:
        tracker.record_test_execution(execution)

    # Get flaky tests
    flaky_tests = tracker.get_flaky_tests()
    print(f"Found {len(flaky_tests)} flaky tests")

    # Create a technical debt ticket
    if flaky_tests:
        ticket = create_technical_debt_ticket_for_flaky_tests(
            test_ids=[test.test_id for test in flaky_tests],
            title="Fix flaky tests in example suite",
            description="Address flaky tests that are causing CI instability",
            priority=TechnicalDebtPriority.HIGH,
            estimated_hours=4,
        )
        print(f"Created technical debt ticket: {ticket.ticket_id}")

    # Generate report
    report = tracker.generate_flaky_test_report()
    print("\nFlaky Test Report:")
    print(report)
