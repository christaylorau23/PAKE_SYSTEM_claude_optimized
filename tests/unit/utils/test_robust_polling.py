#!/usr/bin/env python3
"""
PAKE System - Robust Polling Utility Tests
Comprehensive test suite for the robust polling mechanisms

This module tests the robust polling utilities that replace fixed delays
in tests, ensuring they work correctly in various scenarios.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest

from src.utils.test_polling import (
    PollingConfig,
    PollingResult,
    RobustPoller,
    poll_cache_ready,
    poll_database_ready,
    poll_until_equal,
    poll_until_true,
)


class TestPollingConfig:
    """Test cases for PollingConfig dataclass"""

    def test_default_config(self) -> None:
        """Test default configuration values"""
        config = PollingConfig()

        assert config.timeout_seconds == 30.0
        assert config.interval_seconds == 0.1
        assert config.max_interval_seconds == 2.0
        assert config.exponential_backoff is True
        assert config.backoff_multiplier == 1.5
        assert config.max_retries is None
        assert config.log_attempts is True

    def test_custom_config(self) -> None:
        """Test custom configuration values"""
        config = PollingConfig(
            timeout_seconds=10.0,
            interval_seconds=0.5,
            max_interval_seconds=5.0,
            exponential_backoff=False,
            backoff_multiplier=2.0,
            max_retries=5,
            log_attempts=False,
        )

        assert config.timeout_seconds == 10.0
        assert config.interval_seconds == 0.5
        assert config.max_interval_seconds == 5.0
        assert config.exponential_backoff is False
        assert config.backoff_multiplier == 2.0
        assert config.max_retries == 5
        assert config.log_attempts is False


class TestRobustPoller:
    """Test cases for RobustPoller class"""

    @pytest.fixture
    def poller(self) -> RobustPoller:
        """Create a RobustPoller instance for testing"""
        return RobustPoller()

    @pytest.fixture
    def fast_poller(self) -> RobustPoller:
        """Create a fast-polling RobustPoller for testing"""
        config = PollingConfig(
            timeout_seconds=2.0, interval_seconds=0.01, max_interval_seconds=0.1
        )
        return RobustPoller(config)

    @pytest.fixture
    def robust_poller(self) -> RobustPoller:
        """Create a robust_poller fixture (alias for poller)"""
        return RobustPoller()

    @pytest.fixture
    def slow_poller(self) -> RobustPoller:
        """Create a slow-polling RobustPoller for testing"""
        config = PollingConfig(
            timeout_seconds=60.0, interval_seconds=1.0, max_interval_seconds=5.0
        )
        return RobustPoller(config)

    @pytest.mark.asyncio
    async def test_poll_condition_success(self, fast_poller: RobustPoller) -> None:
        """Test successful condition polling"""
        counter = 0

        async def condition() -> bool:
            nonlocal counter
            counter += 1
            return counter >= 3

        result = await fast_poller.poll_condition(
            condition, operation_name="test_condition"
        )

        assert result.success is True
        assert result.value is True
        assert result.attempts == 3
        assert result.total_time > 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_poll_condition_timeout(self, fast_poller: RobustPoller) -> None:
        """Test condition polling timeout"""

        async def never_true() -> bool:
            return False

        result = await fast_poller.poll_condition(
            never_true, operation_name="test_timeout"
        )

        assert result.success is False
        assert result.value is None
        assert result.attempts > 0
        assert result.total_time >= 2.0
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_poll_condition_max_retries(self, fast_poller: RobustPoller) -> None:
        """Test condition polling with max retries"""
        config = PollingConfig(
            timeout_seconds=10.0, interval_seconds=0.01, max_retries=3
        )

        async def never_true() -> bool:
            return False

        result = await fast_poller.poll_condition(
            never_true, config, operation_name="test_max_retries"
        )

        assert result.success is False
        assert result.attempts == 3
        assert "Max retries" in result.error

    @pytest.mark.asyncio
    async def test_poll_condition_exception(self, fast_poller: RobustPoller) -> None:
        """Test condition polling with exceptions"""

        async def failing_condition() -> bool:
            msg = "Test exception"
            raise ValueError(msg)

        result = await fast_poller.poll_condition(
            failing_condition, operation_name="test_exception"
        )

        assert result.success is False
        assert "Exception during polling" in result.error

    @pytest.mark.asyncio
    async def test_poll_value_success(self, fast_poller) -> None:
        """Test successful value polling"""
        counter = 0

        async def value_func() -> None:
            nonlocal counter
            counter += 1
            return counter

        result = await fast_poller.poll_value(
            value_func, 3, operation_name="test_value"
        )

        assert result.success is True
        assert result.value == 3
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_poll_value_timeout(self, fast_poller) -> None:
        """Test value polling timeout"""

        async def always_zero() -> None:
            return 0

        result = await fast_poller.poll_value(
            always_zero, 1, operation_name="test_value_timeout"
        )

        assert result.success is False
        assert result.value is None

    @pytest.mark.asyncio
    async def test_poll_database_record_success(self, fast_poller) -> None:
        """Test successful database record polling"""
        # Mock database manager
        db_manager = AsyncMock()
        db_manager.fetch_all.return_value = [{"id": 1}, {"id": 2}]

        result = await fast_poller.poll_database_record(
            db_manager,
            "SELECT * FROM test_table",
            (),
            expected_count=2,
            operation_name="test_db_record",
        )

        assert result.success is True
        assert len(result.value) == 2

    @pytest.mark.asyncio
    async def test_poll_cache_value_success(self, fast_poller) -> None:
        """Test successful cache value polling"""
        # Mock cache manager
        cache_manager = AsyncMock()
        cache_manager.get.return_value = "cached_value"

        result = await fast_poller.poll_cache_value(
            cache_manager,
            "test_namespace",
            "test_key",
            expected_value="cached_value",
            operation_name="test_cache_value",
        )

        assert result.success is True
        assert result.value == "cached_value"

    @pytest.mark.asyncio
    async def test_poll_message_received_success(self, fast_poller) -> None:
        """Test successful message received polling"""
        # Mock message bus
        message_bus = AsyncMock()
        received_messages = [{"id": 1}, {"id": 2}]

        result = await fast_poller.poll_message_received(
            message_bus,
            expected_count=2,
            received_messages=received_messages,
            operation_name="test_message_received",
        )

        assert result.success is True
        assert result.value == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, poller) -> None:
        """Test exponential backoff behavior"""
        config = PollingConfig(
            timeout_seconds=1.0,
            interval_seconds=0.01,
            exponential_backoff=True,
            backoff_multiplier=2.0,
        )

        start_time = time.time()
        attempt_times = []

        async def condition() -> None:
            attempt_times.append(time.time())
            return False  # Never succeed

        result = await poller.poll_condition(
            condition, config, operation_name="test_backoff"
        )

        assert result.success is False

        # Check that intervals increased (at least first few attempts)
        if len(attempt_times) >= 3:
            interval1 = attempt_times[1] - attempt_times[0]
            interval2 = attempt_times[2] - attempt_times[1]
            assert interval2 > interval1

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, fast_poller) -> None:
        """Test circuit breaker functionality"""

        async def failing_condition() -> None:
            msg = "Service unavailable"
            raise ConnectionError(msg)

        # First few attempts should fail and record failures
        result1 = await fast_poller.poll_condition(
            failing_condition, operation_name="test_circuit"
        )
        assert result1.success is False

        # Circuit should be open after threshold failures
        result2 = await fast_poller.poll_condition(
            failing_condition, operation_name="test_circuit"
        )
        assert result2.success is False
        assert "Circuit breaker is open" in result2.error


class TestConvenienceFunctions:
    """Test cases for convenience polling functions"""

    @pytest.mark.asyncio
    async def test_poll_until_true_success(self) -> None:
        """Test successful poll_until_true"""
        counter = 0

        async def condition() -> None:
            nonlocal counter
            counter += 1
            return counter >= 2

        result = await poll_until_true(
            condition, timeout=5.0, operation_name="test_convenience"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_poll_until_true_timeout(self) -> None:
        """Test poll_until_true timeout"""

        async def never_true() -> None:
            return False

        result = await poll_until_true(
            never_true, timeout=0.1, operation_name="test_timeout"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_poll_until_equal_success(self) -> None:
        """Test successful poll_until_equal"""
        counter = 0

        async def value_func() -> None:
            nonlocal counter
            counter += 1
            return counter

        result = await poll_until_equal(
            value_func, 2, timeout=5.0, operation_name="test_equal"
        )
        assert result == 2

    @pytest.mark.asyncio
    async def test_poll_until_equal_timeout(self) -> None:
        """Test poll_until_equal timeout"""

        async def always_zero() -> None:
            return 0

        result = await poll_until_equal(
            always_zero, 1, timeout=0.1, operation_name="test_equal_timeout"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_poll_database_ready_success(self) -> None:
        """Test successful poll_database_ready"""
        db_manager = AsyncMock()
        db_manager.execute_query.return_value = None

        result = await poll_database_ready(
            db_manager, timeout=5.0, operation_name="test_db_ready"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_poll_database_ready_failure(self) -> None:
        """Test poll_database_ready failure"""
        db_manager = AsyncMock()
        db_manager.execute_query.side_effect = ConnectionError("Database unavailable")

        result = await poll_database_ready(
            db_manager, timeout=0.1, operation_name="test_db_failure"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_poll_cache_ready_success(self) -> None:
        """Test successful poll_cache_ready"""
        cache_manager = AsyncMock()
        cache_manager.set.return_value = True
        cache_manager.delete.return_value = True

        result = await poll_cache_ready(
            cache_manager, timeout=5.0, operation_name="test_cache_ready"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_poll_cache_ready_failure(self) -> None:
        """Test poll_cache_ready failure"""
        cache_manager = AsyncMock()
        cache_manager.set.side_effect = ConnectionError("Cache unavailable")

        result = await poll_cache_ready(
            cache_manager, timeout=0.1, operation_name="test_cache_failure"
        )
        assert result is False


class TestPytestFixtures:
    """Test cases for pytest fixtures"""

    @pytest.mark.asyncio
    async def test_robust_poller_fixture(self, robust_poller) -> None:
        """Test robust_poller fixture"""
        assert isinstance(robust_poller, RobustPoller)

        counter = 0

        async def condition() -> None:
            nonlocal counter
            counter += 1
            return counter >= 2

        result = await robust_poller.poll_condition(
            condition, operation_name="test_fixture"
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fast_poller_fixture(self, fast_poller) -> None:
        """Test fast_poller fixture"""
        assert isinstance(fast_poller, RobustPoller)
        assert fast_poller.config.timeout_seconds == 2.0
        assert fast_poller.config.interval_seconds == 0.01

    @pytest.mark.asyncio
    async def test_slow_poller_fixture(self, slow_poller) -> None:
        """Test slow_poller fixture"""
        assert isinstance(slow_poller, RobustPoller)
        assert slow_poller.config.timeout_seconds == 60.0
        assert slow_poller.config.interval_seconds == 1.0


class TestPollingResult:
    """Test cases for PollingResult dataclass"""

    def test_successful_result(self) -> None:
        """Test successful polling result"""
        result = PollingResult(
            success=True, value="test_value", attempts=5, total_time=1.5
        )

        assert result.success is True
        assert result.value == "test_value"
        assert result.attempts == 5
        assert result.total_time == 1.5
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test failed polling result"""
        result = PollingResult(
            success=False, attempts=10, total_time=5.0, error="Timeout occurred"
        )

        assert result.success is False
        assert result.value is None
        assert result.attempts == 10
        assert result.total_time == 5.0
        assert result.error == "Timeout occurred"


class TestIntegrationScenarios:
    """Integration test scenarios for robust polling"""

    @pytest.mark.asyncio
    async def test_database_workflow_polling(self, fast_poller) -> None:
        """Test polling in a database workflow scenario"""
        # Mock database manager
        db_manager = AsyncMock()

        # Simulate database becoming ready
        call_count = 0

        async def mock_execute_query() -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "Database not ready"
                raise ConnectionError(msg)
            return

        db_manager.execute_query.side_effect = mock_execute_query

        # Test database readiness polling
        result = await poll_database_ready(
            db_manager, timeout=5.0, operation_name="integration_db"
        )
        assert result is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_cache_workflow_polling(self, fast_poller) -> None:
        """Test polling in a cache workflow scenario"""
        # Mock cache manager
        cache_manager = AsyncMock()

        # Simulate cache becoming ready
        call_count = 0

        async def mock_set() -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                msg = "Cache not ready"
                raise ConnectionError(msg)
            return True

        cache_manager.set.side_effect = mock_set
        cache_manager.delete.return_value = True

        # Test cache readiness polling
        result = await poll_cache_ready(
            cache_manager, timeout=5.0, operation_name="integration_cache"
        )
        assert result is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_message_bus_workflow_polling(self, fast_poller) -> None:
        """Test polling in a message bus workflow scenario"""
        # Mock message bus and received messages
        message_bus = AsyncMock()
        received_messages = []

        # Simulate messages being received over time
        async def simulate_message_reception() -> None:
            await asyncio.sleep(0.1)
            received_messages.append({"id": len(received_messages) + 1})

        # Start message reception simulation
        asyncio.create_task(simulate_message_reception())
        asyncio.create_task(simulate_message_reception())

        # Test message reception polling
        result = await fast_poller.poll_message_received(
            message_bus,
            expected_count=2,
            received_messages=received_messages,
            operation_name="integration_messages",
        )

        assert result.success is True
        assert len(received_messages) == 2


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])
