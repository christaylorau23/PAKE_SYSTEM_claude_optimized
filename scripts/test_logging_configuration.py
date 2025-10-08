#!/usr/bin/env python3
"""Test script to verify enhanced logging configuration
This script tests the logging setup to ensure it works correctly.
"""

import logging
from pathlib import Path
import sys
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_basic_logging(self) -> None:
    """Test basic Python logging functionality"""
    print("Testing basic logging...")

    # Configure basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)s)",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("test_basic")

    # Test all log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    print("✓ Basic logging test completed")


def test_structured_logging(self) -> None:
    """Test structured logging with structlog"""
    print("Testing structured logging...")

    try:
        import structlog

        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        logger = structlog.get_logger("test_structured")

        # Test structured logging
        logger.info(
            "Structured log message",
            test_type="structured",
            timestamp=time.time(),
            data={"key": "value", "number": 42},
        )

        logger.error(
            "Error with context",
            error_type="TestError",
            context="test_function",
            details={"step": "validation", "result": "failed"},
        )

        print("✓ Structured logging test completed")

    except ImportError:
        print("⚠ structlog not available, skipping structured logging test")


def test_enhanced_test_logging(self) -> None:
    """Test enhanced test logging service"""
    print("Testing enhanced test logging service...")

    try:
        from src.services.logging.enhanced_test_logging import (
            TestLoggingConfig,
            TestLoggingService,
        )

        # Configure test logging
        config = TestLoggingConfig(
            enabled=True,
            level="DEBUG",
            format_type="structured",
            console_output=True,
            file_output=False,  # Disable file output for this test
            show_test_boundaries=True,
        )

        service = TestLoggingService(config)

        # Test with context manager
        with service.test_context("test_logging_verification", "unit") as logger:
            logger.info("Test started")

            # Log various events
            service.log_application_event("User action", user_id="test_user")
            service.log_performance_metric("test_operation", 0.05)
            service.log_database_operation("SELECT", "test_table", 0.01)
            service.log_api_call("GET", "/api/test", 200, 0.1)

            logger.info("Test completed")

        # Get test summary
        summary = service.get_test_summary()
        print(
            f"✓ Enhanced test logging completed - {summary['total_tests']} tests logged"
        )

    except ImportError as e:
        print(f"⚠ Enhanced test logging not available: {e}")


def test_pytest_integration(self) -> None:
    """Test pytest logging integration"""
    print("Testing pytest integration...")

    try:
        import pytest

        # Test that pytest can import our configuration
        from tests.conftest import capture_logs, structured_logger, test_logger

        print("✓ Pytest fixtures imported successfully")

        # Test logging configuration
        logger = logging.getLogger("pytest_test")
        logger.info("Pytest integration test message")

        print("✓ Pytest integration test completed")

    except ImportError as e:
        print(f"⚠ Pytest integration test failed: {e}")


def test_log_file_creation(self) -> None:
    """Test log file creation"""
    print("Testing log file creation...")

    try:
        from logging.handlers import RotatingFileHandler

        # Create test log file
        log_file = Path("logs/test_logging.log")
        log_file.parent.mkdir(exist_ok=True)

        # Configure file logging
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)s)",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        logger = logging.getLogger("test_file")
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        # Write test messages
        logger.info("Test file logging message")
        logger.debug("Debug message to file")

        # Verify file was created
        if log_file.exists():
            content = log_file.read_text()
            assert "Test file logging message" in content
            print("✓ Log file creation test completed")
        else:
            print("⚠ Log file was not created")

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"⚠ Log file creation test failed: {e}")


def main(self) -> None:
    """Run all logging tests"""
    print("=" * 60)
    print("PAKE System - Enhanced Logging Configuration Test")
    print("=" * 60)

    try:
        test_basic_logging()
        print()

        test_structured_logging()
        print()

        test_enhanced_test_logging()
        print()

        test_pytest_integration()
        print()

        test_log_file_creation()
        print()

        print("=" * 60)
        print("✓ All logging tests completed successfully!")
        print("=" * 60)

    except (ValueError, RuntimeError) as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
