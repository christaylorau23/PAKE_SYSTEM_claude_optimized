#!/usr/bin/env python3
"""Example test demonstrating enhanced logging capabilities
This test shows how to use the enhanced logging system for comprehensive test debugging.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.logging_example,
]


class TestEnhancedLoggingExample:
    """Example test class demonstrating enhanced logging features"""

    def test_basic_logging_with_capture(self) -> None:
        """Test basic logging with log capture verification"""
        import logging

        logger = logging.getLogger("test_basic")

        # Log various levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Verify logs were captured
        assert self.capture_logs.has_info("Info message")
        assert self.capture_logs.has_warning("Warning message")
        assert self.capture_logs.has_error("Error message")

    def test_structured_logging_with_context(self) -> None:
        """Test structured logging with context and metadata"""
        # Log with structured data
        self.structured_logger.info(
            "User action performed",
            user_id="12345",
            action="login",
            timestamp="2024-01-01T00:00:00Z",
            metadata={"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"},
        )

        # Log database operation
        self.structured_logger.log_database(
            "User query executed",
            operation="SELECT",
            table="users",
            duration=0.05,
            row_count=1,
        )

        # Log API call
        self.structured_logger.log_api_call(
            "API request processed",
            method="POST",
            url="/api/v1/users",
            status_code=201,
            duration=0.15,
        )

    def test_performance_logging(self) -> None:
        """Test performance logging and timing"""
        # Simulate some work
        start_time = time.time()

        # Simulate database operation
        time.sleep(0.01)  # 10ms
        self.test_logger.log_performance("database_query", time.time() - start_time)

        # Simulate API call
        start_time = time.time()
        time.sleep(0.02)  # 20ms
        self.test_logger.log_performance("api_call", time.time() - start_time)

        # Log memory usage (simulated)
        self.test_logger.info(
            "Memory usage tracked", memory_mb=128.5, operation="test_operation"
        )

    def test_error_logging_with_context(self) -> None:
        """Test error logging with detailed context"""
        try:
            # Simulate an error
            msg = "Test error for logging demonstration"
            raise ValueError(msg)
        except ValueError as e:
            self.structured_logger.error(
                "Test error occurred",
                error=e,
                context="test_error_logging",
                operation="simulate_error",
                user_id="test_user",
            )

    @pytest.mark.asyncio()
    async def test_async_operation_logging(self) -> None:
        """Test logging in async operations"""
        self.structured_logger.info("Starting async operation")

        # Simulate async database operation
        async def mock_db_operation(self) -> None:
            await asyncio.sleep(0.01)
            return {"id": 1, "name": "test"}

        start_time = time.time()
        result = await mock_db_operation()
        duration = time.time() - start_time

        self.structured_logger.log_database(
            "Async database operation completed",
            operation="SELECT",
            table="test_table",
            duration=duration,
            row_count=1,
        )

        assert result["id"] == 1

    def test_business_event_logging(self) -> None:
        """Test business event logging"""
        # Log user registration
        self.structured_logger.business(
            "User registered successfully",
            event="user_registration",
            user_id="new_user_123",
            entity_type="user",
            entity_id="new_user_123",
            action="create",
            metadata={
                "registration_method": "email",
                "source": "web",
                "campaign": "winter_2024",
            },
        )

        # Log order creation
        self.structured_logger.business(
            "Order created",
            event="order_creation",
            user_id="user_123",
            entity_type="order",
            entity_id="order_456",
            action="create",
            metadata={"order_value": 99.99, "currency": "USD", "items_count": 3},
        )

    def test_security_event_logging(self) -> None:
        """Test security event logging"""
        # Log successful login
        self.structured_logger.security(
            "User login successful",
            event="login",
            user_id="user_123",
            ip="192.168.1.100",
            user_agent="Mozilla/5.0",
            success=True,
        )

        # Log failed login attempt
        self.structured_logger.security(
            "Failed login attempt",
            event="login",
            user_id="unknown_user",
            ip="192.168.1.200",
            user_agent="curl/7.68.0",
            success=False,
            reason="invalid_credentials",
        )

    def test_timer_context_manager(self) -> None:
        """Test timer context manager for automatic timing"""
        with self.structured_logger.timer("expensive_operation"):
            # Simulate expensive operation
            time.sleep(0.05)

            # Simulate some work
            data = list(range(1000))
            result = sum(data)

            assert result == 499500

    def test_correlation_id_tracking(self) -> None:
        """Test correlation ID for request tracking"""
        # Create logger with correlation ID
        request_logger = self.structured_logger.with_correlation_id("req_12345")

        request_logger.info("Request started")

        # Simulate request processing
        request_logger.log_database(
            "User data retrieved", operation="SELECT", table="users", duration=0.02
        )

        request_logger.log_api_call(
            "External API called",
            method="GET",
            url="/api/external/data",
            status_code=200,
            duration=0.1,
        )

        request_logger.info("Request completed")

    def test_user_context_logging(self) -> None:
        """Test user context logging for audit trails"""
        # Create logger with user context
        user_logger = self.structured_logger.with_user("user_123", "john_doe")

        user_logger.info("User action performed", action="view_profile")
        user_logger.business(
            "Profile updated",
            event="profile_update",
            entity_type="user_profile",
            entity_id="user_123",
            action="update",
        )

    def test_request_context_logging(self) -> None:
        """Test request context logging for API requests"""
        # Create logger with request context
        request_logger = self.structured_logger.with_request(
            request_id="req_67890",
            method="POST",
            path="/api/v1/tasks",
            ip="192.168.1.50",
            user_agent="PostmanRuntime/7.28.0",
        )

        request_logger.info("API request received")
        request_logger.log_database(
            "Task created", operation="INSERT", table="tasks", duration=0.03
        )
        request_logger.info("API request processed")

    def test_comprehensive_workflow_logging(self) -> None:
        """Test comprehensive workflow with all logging types"""
        # Start workflow
        self.structured_logger.info("Starting comprehensive workflow")

        # User authentication
        self.structured_logger.security(
            "User authenticated",
            event="authentication",
            user_id="user_456",
            success=True,
        )

        # Database operations
        self.structured_logger.log_database(
            "User data retrieved", operation="SELECT", table="users", duration=0.01
        )

        self.structured_logger.log_database(
            "User preferences updated",
            operation="UPDATE",
            table="user_preferences",
            duration=0.02,
        )

        # External API calls
        self.structured_logger.log_api_call(
            "External service called",
            method="GET",
            url="/api/external/user-data",
            status_code=200,
            duration=0.15,
        )

        # Business events
        self.structured_logger.business(
            "User session started",
            event="session_start",
            user_id="user_456",
            entity_type="session",
            action="create",
        )

        # Performance metrics
        self.structured_logger.performance(
            "Workflow completed",
            operation="comprehensive_workflow",
            duration=0.18,
            memory_mb=64.2,
            cpu_percent=15.5,
        )

        self.structured_logger.info("Comprehensive workflow completed successfully")

    def test_error_handling_with_logging(self) -> None:
        """Test error handling with comprehensive logging"""
        try:
            # Simulate an operation that might fail
            result = 10 / 0
        except ZeroDivisionError as e:
            self.structured_logger.error(
                "Division by zero error",
                error=e,
                context="mathematical_operation",
                operation="division",
                operands={"dividend": 10, "divisor": 0},
            )

            # Log recovery action
            self.structured_logger.info(
                "Error recovery attempted",
                recovery_action="use_default_value",
                default_value=0,
            )

    def test_logging_with_mocked_services(self) -> None:
        """Test logging with mocked external services"""
        # Mock external service
        mock_service = MagicMock()
        mock_service.get_data.return_value = {"status": "success", "data": "test"}

        # Log service call
        self.structured_logger.info("Calling external service")

        # Simulate service call
        result = mock_service.get_data()

        self.structured_logger.log_api_call(
            "External service response",
            method="GET",
            url="/api/external",
            status_code=200,
            duration=0.05,
        )

        assert result["status"] == "success"

    @pytest.mark.slow()
    def test_slow_operation_logging(self) -> None:
        """Test logging for slow operations (marked as slow test)"""
        self.structured_logger.info("Starting slow operation")

        # Simulate slow operation
        start_time = time.time()
        time.sleep(0.1)  # 100ms - should trigger slow test warning
        duration = time.time() - start_time

        self.structured_logger.performance(
            "Slow operation completed",
            operation="slow_test_operation",
            duration=duration,
        )

        self.structured_logger.info("Slow operation completed")


class TestLoggingIntegration:
    """Test integration between different logging components"""

    def test_pytest_logging_integration(self) -> None:
        """Test integration with pytest's caplog fixture"""
        import logging

        logger = logging.getLogger("integration_test")
        logger.info("Integration test message")

        # Verify message was captured
        assert "Integration test message" in self.caplog.text

    def test_structured_and_standard_logging_mix(self) -> None:
        """Test mixing structured and standard logging"""
        import logging

        # Standard logging
        std_logger = logging.getLogger("mixed_test")
        std_logger.info("Standard log message")

        # Structured logging
        self.structured_logger.info(
            "Structured log message", test_type="mixed_logging", standard_logged=True
        )

    def test_logging_levels_and_filtering(self) -> None:
        """Test different logging levels and filtering"""
        # Test all log levels
        self.structured_logger.debug("Debug message", level="debug")
        self.structured_logger.info("Info message", level="info")
        self.structured_logger.warning("Warning message", level="warning")
        self.structured_logger.error("Error message", level="error")
        self.structured_logger.critical("Critical message", level="critical")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
