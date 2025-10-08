#!/usr/bin/env python3
"""
PAKE System - Flaky Test Management Tests
Comprehensive test suite for flaky test tracking and resolution

This module tests the flaky test management system to ensure it properly
tracks, analyzes, and helps resolve flaky tests according to enterprise policy.
"""

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch

import pytest

from src.utils.flaky_test_management import (
    FailureMode,
    FlakyTestRecord,
    FlakyTestStatus,
    FlakyTestTracker,
    analyze_race_condition,
    create_mock_for_flaky_test,
    flaky_test,
    get_flaky_tracker,
)


class TestFlakyTestRecord:
    """Test cases for FlakyTestRecord"""

    def test_record_creation(self) -> None:
        """Test creating a flaky test record"""
        record = FlakyTestRecord(
            test_id="test_example",
            test_name="test_example",
            test_file="tests/test_example.py",
            failure_mode=FailureMode.RACE_CONDITION,
            failure_rate=0.3,
            first_detected=datetime.now(UTC),
            last_failure=datetime.now(UTC),
            total_failures=3,
            total_runs=10,
            retry_count=2,
            resolution_status=FlakyTestStatus.IDENTIFIED,
        )

        assert record.test_id == "test_example"
        assert record.failure_mode == FailureMode.RACE_CONDITION
        assert record.failure_rate == 0.3
        assert record.resolution_status == FlakyTestStatus.IDENTIFIED


class TestFlakyTestTracker:
    """Test cases for FlakyTestTracker"""

    @pytest.fixture
    def temp_tracker(self) -> None:
        """Create FlakyTestTracker with temporary storage"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        tracker = FlakyTestTracker(storage_path=temp_path)
        yield tracker

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

def test_tracker_initialization(self, temp_tracker: Any = None) -> None:
        """Test tracker initialization"""
        assert isinstance(temp_tracker, FlakyTestTracker)
        assert len(self.temp_tracker.flaky_tests) == 0

    def test_record_test_failure(self) -> None:
        """Test recording a test failure"""
        test_id = "test_example_failure"
        test_name = "test_example_failure"
        test_file = "tests/test_example.py"
        error_message = "Test failed due to race condition"

        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_name,
            test_file=test_file,
            error_message=error_message,
            failure_mode=FailureMode.RACE_CONDITION,
        )

        assert test_id in self.temp_tracker.flaky_tests
        record = self.temp_tracker.flaky_tests[test_id]
        assert record.test_name == test_name
        assert record.failure_mode == FailureMode.RACE_CONDITION
        assert record.failure_rate == 1.0  # First failure = 100%
        assert record.resolution_status == FlakyTestStatus.IDENTIFIED

    def test_record_test_success(self) -> None:
        """Test recording a test success"""
        test_id = "test_example_success"

        # First record a failure
        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_id,
            test_file="tests/test_example.py",
            error_message="Test failed",
            failure_mode=FailureMode.UNKNOWN,
        )

        # Then record a success
        self.temp_tracker.record_test_success(test_id)

        record = self.temp_tracker.flaky_tests[test_id]
        assert record.total_runs == 2
        assert record.total_failures == 1
        assert record.failure_rate == 0.5  # 1 failure out of 2 runs

    def test_record_retry_attempt(self) -> None:
        """Test recording retry attempts"""
        test_id = "test_example_retry"

        self.temp_tracker.record_retry_attempt(test_id)
        self.temp_tracker.record_retry_attempt(test_id)

        assert self.temp_tracker.retry_attempts[test_id] == 2

    def test_should_retry_test(self) -> None:
        """Test retry decision logic"""
        test_id = "test_example_retry_decision"

        # Unknown test should be retryable
        assert self.temp_tracker.should_retry_test(test_id) is True

        # Record some failures
        for _ in range(3):
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message="Test failed",
                failure_mode=FailureMode.UNKNOWN,
            )

        # Should still be retryable (failure rate above threshold)
        assert self.temp_tracker.should_retry_test(test_id) is True

        # Record many retry attempts
        for _ in range(5):
            self.temp_tracker.record_retry_attempt(test_id)

        # Should not be retryable (too many retries)
        assert self.temp_tracker.should_retry_test(test_id) is False

    def test_create_issue_ticket(self) -> None:
        """Test creating issue tickets"""
        test_id = "test_example_ticket"

        # First record a failure
        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_id,
            test_file="tests/test_example.py",
            error_message="Test failed",
            failure_mode=FailureMode.RACE_CONDITION,
        )

        # Create issue ticket
        ticket_id = self.temp_tracker.create_issue_ticket(test_id)

        assert ticket_id.startswith("FLAKY-")
        assert test_id.upper() in ticket_id

        record = self.temp_tracker.flaky_tests[test_id]
        assert record.issue_ticket == ticket_id
        assert record.resolution_status == FlakyTestStatus.INVESTIGATING

    def test_update_resolution_status(self) -> None:
        """Test updating resolution status"""
        test_id = "test_example_resolution"

        # Record failure and create ticket
        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_id,
            test_file="tests/test_example.py",
            error_message="Test failed",
            failure_mode=FailureMode.RACE_CONDITION,
        )

        self.temp_tracker.create_issue_ticket(test_id)

        # Update resolution status
        self.temp_tracker.update_resolution_status(
            test_id=test_id,
            status=FlakyTestStatus.RESOLVED,
            notes="Fixed race condition with proper locking",
            refactoring_notes="Added asyncio.Lock to protect shared state",
        )

        record = self.temp_tracker.flaky_tests[test_id]
        assert record.resolution_status == FlakyTestStatus.RESOLVED
        assert "Fixed race condition" in record.resolution_notes
        assert "Added asyncio.Lock" in record.refactoring_notes

    def test_get_tests_by_status(self) -> None:
        """Test getting tests by status"""
        # Create tests with different statuses
        test_ids = ["test_identified", "test_investigating", "test_resolved"]
        statuses = [
            FlakyTestStatus.IDENTIFIED,
            FlakyTestStatus.INVESTIGATING,
            FlakyTestStatus.RESOLVED,
        ]

        for test_id, status in zip(test_ids, statuses, strict=False):
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message="Test failed",
                failure_mode=FailureMode.UNKNOWN,
            )

            if status != FlakyTestStatus.IDENTIFIED:
                self.temp_tracker.update_resolution_status(test_id, status)

        # Test getting by status
        identified_tests = self.temp_tracker.get_flaky_tests_by_status(
            FlakyTestStatus.IDENTIFIED
        )
        investigating_tests = self.temp_tracker.get_flaky_tests_by_status(
            FlakyTestStatus.INVESTIGATING
        )
        resolved_tests = self.temp_tracker.get_flaky_tests_by_status(
            FlakyTestStatus.RESOLVED
        )

        assert len(identified_tests) == 1
        assert len(investigating_tests) == 1
        assert len(resolved_tests) == 1

    def test_get_tests_by_failure_mode(self) -> None:
        """Test getting tests by failure mode"""
        # Create tests with different failure modes
        test_ids = ["test_race", "test_timeout", "test_api"]
        failure_modes = [
            FailureMode.RACE_CONDITION,
            FailureMode.TIMING_DEPENDENT,
            FailureMode.EXTERNAL_API,
        ]

        for test_id, failure_mode in zip(test_ids, failure_modes, strict=False):
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message="Test failed",
                failure_mode=failure_mode,
            )

        # Test getting by failure mode
        race_tests = self.temp_tracker.get_flaky_tests_by_failure_mode(
            FailureMode.RACE_CONDITION
        )
        timeout_tests = self.temp_tracker.get_flaky_tests_by_failure_mode(
            FailureMode.TIMING_DEPENDENT
        )
        api_tests = self.temp_tracker.get_flaky_tests_by_failure_mode(
            FailureMode.EXTERNAL_API
        )

        assert len(race_tests) == 1
        assert len(timeout_tests) == 1
        assert len(api_tests) == 1

    def test_get_metrics(self) -> None:
        """Test metrics calculation"""
        # Create some test records
        test_ids = ["test1", "test2", "test3"]

        for i, test_id in enumerate(test_ids):
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message="Test failed",
                failure_mode=FailureMode.RACE_CONDITION,
            )

            # Record some successes
            for _ in range(i + 1):
                self.temp_tracker.record_test_success(test_id)

            # Update status for some tests
            if i == 0:
                self.temp_tracker.update_resolution_status(test_id, FlakyTestStatus.RESOLVED)
            elif i == 1:
                self.temp_tracker.update_resolution_status(test_id, FlakyTestStatus.ACCEPTED)

        metrics = self.temp_tracker.get_metrics()

        assert metrics.total_flaky_tests == 3
        assert metrics.resolved_tests == 1
        assert metrics.accepted_tests == 1
        assert metrics.active_investigations == 1
        assert metrics.retry_success_rate >= 0
        assert metrics.mock_coverage_rate >= 0

    def test_generate_report(self) -> None:
        """Test report generation"""
        # Create some test records
        test_ids = ["test_report1", "test_report2"]

        for test_id in test_ids:
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message="Test failed",
                failure_mode=FailureMode.RACE_CONDITION,
            )

            # Create tickets
            self.temp_tracker.create_issue_ticket(test_id)

        report = self.temp_tracker.generate_report()

        assert "summary" in report
        assert "by_status" in report
        assert "by_failure_mode" in report
        assert "top_flaky_tests" in report
        assert "recommendations" in report

        assert report["summary"]["total_flaky_tests"] == 2
        assert report["summary"]["active_investigations"] == 2

    def test_data_persistence(self) -> None:
        """Test data persistence to file"""
        test_id = "test_persistence"

        # Record a failure
        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_id,
            test_file="tests/test_example.py",
            error_message="Test failed",
            failure_mode=FailureMode.RACE_CONDITION,
        )

        # Create a new tracker with the same storage path
        new_tracker = FlakyTestTracker(storage_path=self.temp_tracker.storage_path)

        # Should load the existing data
        assert test_id in new_tracker.flaky_tests
        assert (
            new_tracker.flaky_tests[test_id].failure_mode == FailureMode.RACE_CONDITION
        )


class TestFlakyTestDecorator:
    """Test cases for flaky test decorator"""

    def test_flaky_test_decorator(self) -> None:
        """Test flaky test decorator"""

        @flaky_test(failure_mode=FailureMode.RACE_CONDITION, max_retries=3)
        def test_example(self) -> None:
            return "test_result"

        # Check that decorator added metadata
        assert hasattr(test_example, "_flaky_metadata")
        assert (
            test_example._flaky_metadata["failure_mode"] == FailureMode.RACE_CONDITION
        )
        assert test_example._flaky_metadata["max_retries"] == 3

        # Check that pytest markers were added
        assert hasattr(test_example, "pytestmark")

    def test_flaky_test_decorator_with_ticket(self) -> None:
        """Test flaky test decorator with issue ticket"""

        @flaky_test(failure_mode=FailureMode.EXTERNAL_API, issue_ticket="TICKET-123")
        def test_example_with_ticket(self) -> None:
            return "test_result"

        metadata = test_example_with_ticket._flaky_metadata
        assert metadata["failure_mode"] == FailureMode.EXTERNAL_API
        assert metadata["issue_ticket"] == "TICKET-123"


class TestUtilityFunctions:
    """Test cases for utility functions"""

    def test_create_mock_for_flaky_test(self) -> None:
        """Test mock creation utility"""
        mock_code = create_mock_for_flaky_test(
            test_name="test_api_call", external_dependency="ExternalAPI"
        )

        assert "test_api_call" in mock_code
        assert "ExternalAPI" in mock_code
        assert "MockExternalAPI" in mock_code
        assert "unittest.mock" in mock_code

    def test_analyze_race_condition(self) -> None:
        """Test race condition analysis utility"""
        analysis = analyze_race_condition(
            test_name="test_concurrent_counter",
            shared_state_vars=["counter", "shared_dict", "global_state"],
        )

        assert "test_concurrent_counter" in analysis
        assert "counter" in analysis
        assert "shared_dict" in analysis
        assert "global_state" in analysis
        assert "asyncio.Lock" in analysis
        assert "threading.Lock" in analysis
        assert "AsyncSafeDict" in analysis


class TestPytestIntegration:
    """Test cases for pytest integration"""

    def test_pytest_runtest_setup_hook(self) -> None:
        """Test pytest setup hook"""
        # This would be tested in integration with actual pytest runs
        # For now, we just verify the function exists and can be called
        from src.utils.flaky_test_management import pytest_runtest_setup

        # Create a mock item
        mock_item = Mock()
        mock_item.nodeid = "test_example"

        # Should not raise an exception
        pytest_runtest_setup(mock_item)

    def test_pytest_runtest_logreport_hook(self) -> None:
        """Test pytest logreport hook"""
        from src.utils.flaky_test_management import pytest_runtest_logreport

        # Create a mock report
        mock_report = Mock()
        mock_report.when = "call"
        mock_report.nodeid = "test_example"
        mock_report.failed = False
        mock_report.passed = True
        mock_report.longrepr = None

        # Should not raise an exception
        pytest_runtest_logreport(mock_report)


class TestIntegrationScenarios:
    """Integration test scenarios"""

    def test_comprehensive_flaky_test_workflow(self) -> None:
        """Test comprehensive flaky test workflow"""
        test_id = "test_comprehensive_workflow"

        # Step 1: Record initial failure
        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_id,
            test_file="tests/test_example.py",
            error_message="Race condition in shared counter",
            failure_mode=FailureMode.RACE_CONDITION,
        )

        # Step 2: Record retry attempts
        for _ in range(2):
            self.temp_tracker.record_retry_attempt(test_id)

        # Step 3: Create issue ticket
        ticket_id = self.temp_tracker.create_issue_ticket(test_id)

        # Step 4: Record more failures during investigation
        for _ in range(2):
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message="Still failing",
                failure_mode=FailureMode.RACE_CONDITION,
            )

        # Step 5: Update resolution status
        self.temp_tracker.update_resolution_status(
            test_id=test_id,
            status=FlakyTestStatus.RESOLVED,
            notes="Fixed with proper synchronization",
            refactoring_notes="Added AsyncSafeCounter",
        )

        # Step 6: Record successful runs
        for _ in range(5):
            self.temp_tracker.record_test_success(test_id)

        # Verify final state
        record = self.temp_tracker.flaky_tests[test_id]
        assert record.resolution_status == FlakyTestStatus.RESOLVED
        assert record.issue_ticket == ticket_id
        assert record.total_failures == 3
        assert record.total_runs == 8
        assert record.failure_rate == 3 / 8

        # Generate report
        report = self.temp_tracker.generate_report()
        assert report["summary"]["resolved_tests"] == 1

    def test_multiple_failure_modes_tracking(self) -> None:
        """Test tracking tests with different failure modes"""
        test_cases = [
            ("test_race", FailureMode.RACE_CONDITION),
            ("test_timeout", FailureMode.TIMING_DEPENDENT),
            ("test_api", FailureMode.EXTERNAL_API),
            ("test_network", FailureMode.NETWORK_TIMEOUT),
            ("test_db", FailureMode.DATABASE_CONNECTION),
        ]

        for test_id, failure_mode in test_cases:
            self.temp_tracker.record_test_failure(
                test_id=test_id,
                test_name=test_id,
                test_file="tests/test_example.py",
                error_message=f"Failed due to {failure_mode.value}",
                failure_mode=failure_mode,
            )

        # Verify all failure modes are tracked
        for failure_mode in FailureMode:
            if failure_mode != FailureMode.UNKNOWN:
                tests = self.temp_tracker.get_flaky_tests_by_failure_mode(failure_mode)
                assert len(tests) == 1

        # Generate report
        report = self.temp_tracker.generate_report()
        assert report["summary"]["total_flaky_tests"] == 5

        # Check recommendations
        recommendations = report["recommendations"]
        assert any("race condition" in rec.lower() for rec in recommendations)

    def test_retry_policy_compliance(self) -> None:
        """Test retry policy compliance"""
        test_id = "test_retry_policy"

        # Record initial failure
        self.temp_tracker.record_test_failure(
            test_id=test_id,
            test_name=test_id,
            test_file="tests/test_example.py",
            error_message="Test failed",
            failure_mode=FailureMode.UNKNOWN,
        )

        # Should be retryable initially
        assert self.temp_tracker.should_retry_test(test_id) is True

        # Record retry attempts up to limit
        for _ in range(3):
            self.temp_tracker.record_retry_attempt(test_id)

        # Should not be retryable after max retries
        assert self.temp_tracker.should_retry_test(test_id) is False

        # Create ticket (mandatory per policy)
        ticket_id = self.temp_tracker.create_issue_ticket(test_id)
        assert ticket_id is not None

        # Update status to resolved
        self.temp_tracker.update_resolution_status(
            test_id=test_id,
            status=FlakyTestStatus.RESOLVED,
            notes="Fixed the underlying issue",
        )

        # Should not be retryable when resolved
        assert self.temp_tracker.should_retry_test(test_id) is False


# Pytest fixtures
@pytest.fixture
def flaky_tracker(self) -> None:
    """Fixture providing FlakyTestTracker"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name

    tracker = FlakyTestTracker(storage_path=temp_path)
    yield tracker

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
