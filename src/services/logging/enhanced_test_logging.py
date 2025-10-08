#!/usr/bin/env python3
"""Enhanced Test Logging Service for PAKE System
Provides comprehensive logging integration for pytest with:
- Automatic log capture and display
- Structured logging during tests
- Performance monitoring
- Error tracking and debugging
- Integration with existing enterprise logging.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from pathlib import Path
import sys
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.utils.logger import StructuredLogger, get_logger
except ImportError:
    StructuredLogger = None
    get_logger = None


@dataclass
class TestLoggingConfig:
    """Configuration for test logging."""

    # Basic settings
    enabled: bool = True
    level: str = "DEBUG"
    format_type: str = "structured"  # structured, json, console

    # Output settings
    console_output: bool = True
    file_output: bool = True
    test_log_directory: str = "logs/tests"

    # Test-specific settings
    capture_application_logs: bool = True
    capture_performance_metrics: bool = True
    capture_error_details: bool = True
    show_test_boundaries: bool = True

    # Integration settings
    integrate_with_pytest: bool = True
    auto_setup_loggers: bool = True

    # Performance settings
    log_test_duration: bool = True
    log_memory_usage: bool = True
    log_slow_tests: bool = True
    slow_test_threshold: float = 1.0  # seconds

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            msg = f"Invalid log level: {self.level}"
            raise ValueError(msg)

        if self.format_type not in ["structured", "json", "console"]:
            msg = f"Invalid format type: {self.format_type}"
            raise ValueError(msg)


class TestLoggingService:
    """Enhanced test logging service with comprehensive features."""

    def __init__(self, config: TestLoggingConfig | None = None) -> None:
        self.config = config or TestLoggingConfig()
        self.test_loggers: dict[str, StructuredLogger] = {}
        self.test_metrics: dict[str, dict[str, Any]] = {}
        self.active_tests: list[str] = []

        if self.config.enabled:
            self._setup_logging()
            self._setup_test_directory()

    def _setup_logging(self) -> None:
        """Setup structured logging for tests."""
        if not self.config.enabled:
            return

        # Configure structlog processors
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            self._add_test_context,
        ]

        if self.config.format_type == "json":
            processors.append(structlog.processors.JSONRenderer())
        elif self.config.format_type == "structured":
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure standard library logging
        logging.basicConfig(
            level=getattr(logging, self.config.level),
            format="%(message)s",
            handlers=[],
        )

        # Add console handler
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config.level))
            logging.getLogger().addHandler(console_handler)

    def _setup_test_directory(self) -> None:
        """Create test log directory if needed."""
        if self.config.file_output:
            log_dir = Path(self.config.test_log_directory)
            log_dir.mkdir(parents=True, exist_ok=True)

    def _add_test_context(
        self, event_dict: dict[str, Any], method_name: str
    ) -> dict[str, Any]:
        """Add test context to log entries."""
        if self.active_tests:
            event_dict["active_test"] = self.active_tests[-1]

        event_dict["test_session"] = True
        event_dict["timestamp"] = datetime.now(UTC).isoformat()

        return event_dict

    def get_test_logger(self, test_name: str | None = None) -> StructuredLogger:
        """Get or create logger for specific test."""
        if not test_name:
            test_name = "default_test"

        if test_name not in self.test_loggers:
            logger = structlog.get_logger(f"test.{test_name}")
            self.test_loggers[test_name] = (
                StructuredLogger(logger) if StructuredLogger else logger
            )

        return self.test_loggers[test_name]

    @contextmanager
    def test_context(self, test_name: str, test_type: str = "unit"):
        """Context manager for test execution with logging."""
        if not self.config.enabled:
            yield
            return

        start_time = datetime.now(UTC)
        self.active_tests.append(test_name)

        logger = self.get_test_logger(test_name)

        try:
            if self.config.show_test_boundaries:
                logger.info(
                    "Starting %s test",
                    test_type,
                    test_name=test_name,
                    test_type=test_type,
                    event="test_start",
                )

            # Initialize test metrics
            self.test_metrics[test_name] = {
                "start_time": start_time,
                "test_type": test_type,
                "logs": [],
                "errors": [],
                "performance": {},
            }

            yield logger

        except (ValueError, RuntimeError) as e:
            logger.error(
                "Test %s failed",
                test_name,
                test_name=test_name,
                error=str(e),
                event="test_error",
            )
            raise

        finally:
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Log test completion
            if self.config.show_test_boundaries:
                logger.info(
                    "Completed %s test",
                    test_type,
                    test_name=test_name,
                    test_type=test_type,
                    duration_seconds=duration,
                    event="test_complete",
                )

            # Log slow tests
            if (
                self.config.log_slow_tests
                and duration > self.config.slow_test_threshold
            ):
                logger.warning(
                    "Slow test detected",
                    test_name=test_name,
                    duration_seconds=duration,
                    threshold=self.config.slow_test_threshold,
                    event="slow_test",
                )

            # Update metrics
            if test_name in self.test_metrics:
                self.test_metrics[test_name]["end_time"] = end_time
                self.test_metrics[test_name]["duration"] = duration

            self.active_tests.remove(test_name)

    def log_application_event(self, event: str, **kwargs: Any) -> None:
        """Log application events during tests."""
        if not self.config.capture_application_logs:
            return

        logger = self.get_test_logger()
        logger.info("Application event: %s", event, event_type="application", **kwargs)

    def log_performance_metric(
        self, operation: str, duration: float, **kwargs: Any
    ) -> None:
        """Log performance metrics during tests."""
        if not self.config.capture_performance_metrics:
            return

        logger = self.get_test_logger()
        logger.info(
            "Performance metric: %s",
            operation,
            event_type="performance",
            operation=operation,
            duration_ms=duration * 1000,
            **kwargs,
        )

    def log_error(
        self, error: Exception, context: str | None = None, **kwargs: Any
    ) -> None:
        """Log errors with detailed context."""
        if not self.config.capture_error_details:
            return

        logger = self.get_test_logger()
        logger.error(
            "Error captured: %s",
            context or "Unknown context",
            event_type="error",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            **kwargs,
        )

    def log_database_operation(
        self,
        operation: str,
        table: str | None = None,
        duration: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Log database operations during tests."""
        logger = self.get_test_logger()
        logger.database(
            f"Database operation: {operation}",
            operation=operation,
            table=table,
            duration=duration,
            **kwargs,
        )

    def log_api_call(
        self,
        method: str,
        url: str,
        status_code: int | None = None,
        duration: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Log API calls during tests."""
        logger = self.get_test_logger()
        logger.http(
            f"API call: {method} {url}",
            method=method,
            path=url,
            status_code=status_code,
            duration=duration,
            **kwargs,
        )

    def get_test_summary(self) -> dict[str, Any]:
        """Get summary of all test metrics."""
        return {
            "total_tests": len(self.test_metrics),
            "test_metrics": self.test_metrics,
            "slow_tests": [
                name
                for name, metrics in self.test_metrics.items()
                if metrics.get("duration", 0) > self.config.slow_test_threshold
            ],
            "failed_tests": [
                name
                for name, metrics in self.test_metrics.items()
                if metrics.get("errors")
            ],
        }


# Global test logging service instance
_test_logging_service: TestLoggingService | None = None


def get_test_logging_service() -> TestLoggingService:
    """Get or create global test logging service."""
    global _test_logging_service
    if _test_logging_service is None:
        _test_logging_service = TestLoggingService()
    return _test_logging_service


def setup_test_logging(config: TestLoggingConfig | None = None) -> TestLoggingService:
    """Setup test logging with configuration."""
    global _test_logging_service
    _test_logging_service = TestLoggingService(config)
    return _test_logging_service


# Convenience functions for easy access
def log_test_event(event: str, **kwargs: Any) -> None:
    """Log test event."""
    service = get_test_logging_service()
    service.log_application_event(event, **kwargs)


def log_performance(operation: str, duration: float, **kwargs: Any) -> None:
    """Log performance metric."""
    service = get_test_logging_service()
    service.log_performance_metric(operation, duration, **kwargs)


def log_error(error: Exception, context: str | None = None, **kwargs: Any) -> None:
    """Log error with context."""
    service = get_test_logging_service()
    service.log_error(error, context, **kwargs)


def log_database(
    operation: str,
    table: str | None = None,
    duration: float | None = None,
    **kwargs: Any,
) -> None:
    """Log database operation."""
    service = get_test_logging_service()
    service.log_database_operation(operation, table, duration, **kwargs)


def log_api(
    method: str,
    url: str,
    status_code: int | None = None,
    duration: float | None = None,
    **kwargs: Any,
) -> None:
    """Log API call."""
    service = get_test_logging_service()
    service.log_api_call(method, url, status_code, duration, **kwargs)


# Pytest integration helpers
def pytest_configure_logging() -> TestLoggingService:
    """Configure logging for pytest."""
    return get_test_logging_service()


def pytest_test_logger(test_name: str) -> StructuredLogger:
    """Get logger for specific test."""
    service = get_test_logging_service()
    return service.get_test_logger(test_name)


if __name__ == "__main__":
    # Example usage
    config = TestLoggingConfig(
        level="DEBUG",
        format_type="structured",
        show_test_boundaries=True,
        capture_performance_metrics=True,
    )

    service = TestLoggingService(config)

    # Example test context usage
    with service.test_context("example_test", "unit") as logger:
        logger.info("Test started")

        # Log various events
        service.log_application_event("User login", user_id="123")
        service.log_performance_metric("database_query", 0.05)
        service.log_database_operation("SELECT", "users", 0.05)
        service.log_api_call("GET", "/api/users", 200, 0.1)

        logger.info("Test completed")

    # Get test summary
    summary = service.get_test_summary()
    print(f"Test summary: {summary}")
