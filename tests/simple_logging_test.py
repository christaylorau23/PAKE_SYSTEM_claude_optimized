#!/usr/bin/env python3
"""Simple test to verify pytest logging configuration
This test demonstrates the enhanced logging capabilities without external dependencies.
"""

import logging
import time

import pytest


class TestSimpleLogging:
    """Simple logging tests to verify configuration"""

    def test_basic_logging_with_capture(self) -> None:
        """Test basic logging with log capture verification"""
        logger = logging.getLogger("test_basic")

        # Log various levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Verify logs were captured
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text

    def test_logging_levels(self) -> None:
        """Test different logging levels"""
        logger = logging.getLogger("test_levels")

        # Test all log levels
        logger.debug("Debug level test")
        logger.info("Info level test")
        logger.warning("Warning level test")
        logger.error("Error level test")
        logger.critical("Critical level test")

    def test_structured_logging_basic(self) -> None:
        """Test basic structured logging"""
        logger = logging.getLogger("test_structured")

        # Log with extra context
        logger.info(
            "Structured message",
            extra={"user_id": "123", "action": "test", "timestamp": time.time()},
        )

    def test_performance_logging(self) -> None:
        """Test performance logging"""
        logger = logging.getLogger("test_performance")

        # Simulate timing
        start_time = time.time()
        time.sleep(0.01)  # 10ms
        duration = time.time() - start_time

        logger.info(
            "Operation completed",
            extra={"operation": "test_operation", "duration_ms": duration * 1000},
        )

    def test_error_logging(self) -> None:
        """Test error logging with exception"""
        logger = logging.getLogger("test_error")

        try:
            # Simulate an error
            msg = "Test error for logging"
            raise ValueError(msg)
        except ValueError as e:
            logger.error(
                "Error occurred",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "context": "test_function",
                },
            )

    def test_logging_with_context(self) -> None:
        """Test logging with various context information"""
        logger = logging.getLogger("test_context")

        # Log with different types of context
        logger.info(
            "User action",
            extra={
                "user_id": "user_123",
                "action": "login",
                "ip": "192.168.1.1",
                "user_agent": "test-agent",
            },
        )

        logger.info(
            "Database operation",
            extra={
                "operation": "SELECT",
                "table": "users",
                "duration_ms": 25.5,
                "row_count": 10,
            },
        )

        logger.info(
            "API call",
            extra={
                "method": "POST",
                "url": "/api/v1/test",
                "status_code": 201,
                "duration_ms": 150.0,
            },
        )


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
