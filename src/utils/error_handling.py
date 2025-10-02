#!/usr/bin/env python3
"""PAKE+ Enhanced Error Handling Patterns
Comprehensive error handling, retry mechanisms, and resilience patterns
"""

import asyncio
import functools
import json
import time
import traceback
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from utils.logger import get_logger
from utils.metrics import MetricsStore

logger = get_logger(service_name="pake-error-handler")
metrics = MetricsStore(service_name="pake-error-handler")


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categorization for better handling"""

    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"


@dataclass
class ErrorContext:
    """Enhanced error context for structured logging"""

    error_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service_name: str = ""
    operation: str = ""
    correlation_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    additional_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """Retry policy configuration"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()


class PAKEException(Exception):
    """Base exception class for the PAKE system.

    This exception class provides a standardized way to handle errors across the
    PAKE system. It includes severity levels, error categorization, and rich context
    information for better error tracking and debugging.

    Attributes:
        message: The primary error message describing what went wrong.
        severity: The severity level of the error (LOW, MEDIUM, HIGH, CRITICAL).
        category: The category of error for better classification and handling.
        context: Additional context information including timestamps, service names,
            and correlation IDs for debugging.
        original_exception: The original exception that caused this error, if any.
        user_message: A user-friendly error message for display to end users.

    Example:
        >>> try:
        ...     risky_operation()
        ... except ValueError as e:
        ...     raise PAKEException(
        ...         message="Invalid input provided",
        ...         severity=ErrorSeverity.MEDIUM,
        ...         category=ErrorCategory.VALIDATION,
        ...         original_exception=e,
        ...         user_message="Please check your input and try again"
        ...     )
    """

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: ErrorContext | None = None,
        original_exception: Exception | None = None,
        user_message: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        self.user_message = user_message or "An error occurred. Please try again."

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            "error_id": self.context.error_id,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.context.timestamp.isoformat(),
            "service_name": self.context.service_name,
            "operation": self.context.operation,
            "correlation_id": self.context.correlation_id,
            "user_message": self.user_message,
            "original_exception": (
                str(self.original_exception) if self.original_exception else None
            ),
            "traceback": traceback.format_exc() if self.original_exception else None,
            "additional_data": self.context.additional_data,
        }


class NetworkError(PAKEException):
    """Network-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class DatabaseError(PAKEException):
    """Database-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATABASE, **kwargs)


class ValidationError(PAKEException):
    """Validation-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


class ExternalAPIError(PAKEException):
    """External API-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.EXTERNAL_API, **kwargs)


class ErrorHandler:
    """Enhanced error handler with comprehensive logging and metrics.

    This class provides centralized error handling for the PAKE system, including
    automatic exception conversion, structured logging, and metrics collection.
    It ensures consistent error handling patterns across all services.

    Attributes:
        service_name: The name of the service using this error handler.
        logger: Logger instance for error logging and tracking.
        metrics: Metrics store for error statistics and monitoring.

    Example:
        >>> error_handler = ErrorHandler("my-service")
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     pake_error = error_handler.handle_exception(e)
        ...     # Error is logged and metrics are updated
    """

    def __init__(self, service_name: str = "pake-system"):
        self.service_name = service_name
        self.logger = get_logger(service_name=service_name)
        self.metrics = MetricsStore(service_name=service_name)

    def handle_exception(
        self,
        exception: Exception,
        context: ErrorContext | None = None,
        severity: ErrorSeverity | None = None,
    ) -> PAKEException:
        """Handle and transform exceptions into PAKE exceptions"""
        if isinstance(exception, PAKEException):
            pake_error = exception
        else:
            # Determine error category and severity
            category = self._categorize_exception(exception)
            severity = severity or self._determine_severity(exception, category)

            # Create PAKE exception
            pake_error = PAKEException(
                message=str(exception),
                severity=severity,
                category=category,
                context=context or ErrorContext(service_name=self.service_name),
                original_exception=exception,
            )

        # Log the error
        self._log_error(pake_error)

        # Update metrics
        self._update_metrics(pake_error)

        return pake_error

    def _categorize_exception(self, exception: Exception) -> ErrorCategory:
        """Categorize exception based on type and message"""
        exception_name = exception.__class__.__name__.lower()
        exception_message = str(exception).lower()

        # Network-related errors
        if any(
            term in exception_name
            for term in ["connection", "network", "timeout", "http"]
        ):
            return ErrorCategory.NETWORK

        # Database-related errors
        if any(
            term in exception_name for term in ["database", "sql", "postgres", "redis"]
        ):
            return ErrorCategory.DATABASE

        # Authentication/Authorization
        if any(
            term in exception_name for term in ["auth", "permission", "unauthorized"]
        ):
            return ErrorCategory.AUTHENTICATION

        # Validation errors
        if any(term in exception_name for term in ["validation", "invalid", "schema"]):
            return ErrorCategory.VALIDATION

        # External API errors
        if any(term in exception_message for term in ["api", "openai", "context7"]):
            return ErrorCategory.EXTERNAL_API

        return ErrorCategory.SYSTEM

    def _determine_severity(
        self,
        exception: Exception,
        category: ErrorCategory,
    ) -> ErrorSeverity:
        """Determine error severity based on exception and category"""
        exception_name = exception.__class__.__name__.lower()

        # Critical errors
        if any(term in exception_name for term in ["system", "memory", "disk"]):
            return ErrorSeverity.CRITICAL

        # High severity
        if category in [ErrorCategory.DATABASE, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.HIGH

        # Medium severity
        if category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_API]:
            return ErrorSeverity.MEDIUM

        return ErrorSeverity.LOW

    def _log_error(self, error: PAKEException):
        """Log error with structured logging"""
        log_data = error.to_dict()

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error occurred", extra=log_data)
        else:
            self.logger.info("Low severity error occurred", extra=log_data)

    def _update_metrics(self, error: PAKEException):
        """Update error metrics"""
        tags = {
            "service": self.service_name,
            "severity": error.severity.value,
            "category": error.category.value,
            "operation": error.context.operation or "unknown",
        }

        self.metrics.increment_counter("errors_total", labels=tags)
        self.metrics.set_gauge("last_error_timestamp", time.time(), labels=tags)


def with_error_handling(
    operation_name: str,
    severity: ErrorSeverity | None = None,
    category: ErrorCategory | None = None,
    reraise: bool = True,
):
    """Decorator for automatic error handling.

    This decorator wraps functions with automatic error handling, converting
    standard exceptions to PAKEException subclasses and providing structured
    logging and metrics collection.

    Args:
        operation_name: The name of the operation for logging and metrics.
        severity: Optional severity level override for errors.
        category: Optional error category override for errors.
        reraise: Whether to re-raise exceptions after handling.

    Returns:
        Decorated function with automatic error handling.

    Example:
        >>> @with_error_handling("database_query", severity=ErrorSeverity.HIGH)
        ... async def query_database(query: str):
        ...     # Function implementation
        ...     pass
        >>>
        >>> # Any exception will be automatically converted to PAKEException
        >>> # and logged with the operation name "database_query"
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            context = ErrorContext(
                service_name=func.__module__,
                operation=operation_name,
            )

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                pake_error = error_handler.handle_exception(e, context, severity)
                if reraise:
                    raise pake_error
                return None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            context = ErrorContext(
                service_name=func.__module__,
                operation=operation_name,
            )

            try:
                return func(*args, **kwargs)
            except Exception as e:
                pake_error = error_handler.handle_exception(e, context, severity)
                if reraise:
                    raise pake_error
                return None

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def with_retry(policy: RetryPolicy | None = None):
    """Decorator for automatic retry with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        retry_policy = policy or RetryPolicy()

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_policy.non_retryable_exceptions:
                    raise  # Don't retry these exceptions
                except retry_policy.retryable_exceptions as e:
                    last_exception = e

                    if attempt == retry_policy.max_attempts - 1:
                        break  # Last attempt failed

                    # Calculate delay
                    delay = min(
                        retry_policy.base_delay
                        * (retry_policy.exponential_base**attempt),
                        retry_policy.max_delay,
                    )

                    # Add jitter
                    if retry_policy.jitter:
                        import random

                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{retry_policy.max_attempts} "
                        f"for {func.__name__} after {delay:.2f}s delay",
                        extra={
                            "attempt": attempt + 1,
                            "delay": delay,
                            "exception": str(e),
                        },
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_policy.max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_policy.non_retryable_exceptions:
                    raise  # Don't retry these exceptions
                except retry_policy.retryable_exceptions as e:
                    last_exception = e

                    if attempt == retry_policy.max_attempts - 1:
                        break  # Last attempt failed

                    # Calculate delay
                    delay = min(
                        retry_policy.base_delay
                        * (retry_policy.exponential_base**attempt),
                        retry_policy.max_delay,
                    )

                    # Add jitter
                    if retry_policy.jitter:
                        import random

                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{retry_policy.max_attempts} "
                        f"for {func.__name__} after {delay:.2f}s delay",
                        extra={
                            "attempt": attempt + 1,
                            "delay": delay,
                            "exception": str(e),
                        },
                    )

                    time.sleep(delay)

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


@asynccontextmanager
async def error_boundary(
    operation_name: str,
    reraise: bool = True,
    fallback_value: Any = None,
):
    """Async context manager for error boundaries"""
    error_handler = ErrorHandler()
    context = ErrorContext(operation=operation_name)

    try:
        yield
    except Exception as e:
        pake_error = error_handler.handle_exception(e, context)
        if reraise:
            raise pake_error
        # Note: Cannot return from async context manager, fallback handled by caller


class HealthChecker:
    """System health monitoring and error detection"""

    def __init__(self):
        self.logger = get_logger(service_name="health-checker")
        self.metrics = MetricsStore(service_name="health-checker")
        self.checks = []

    async def add_health_check(self, name: str, check_func: Callable):
        """Add a health check function"""
        self.checks.append((name, check_func))

    async def run_health_checks(self) -> dict[str, Any]:
        """Run all health checks and return results"""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {},
        }

        failed_checks = 0

        for name, check_func in self.checks:
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time

                results["checks"][name] = {
                    "status": "healthy",
                    "duration_ms": round(duration * 1000, 2),
                    "details": (
                        result if isinstance(result, dict) else {"message": str(result)}
                    ),
                }

                self.metrics.record_histogram(
                    "health_check_duration",
                    duration,
                    labels={"check": name, "status": "healthy"},
                )

            except Exception as e:
                failed_checks += 1
                duration = time.time() - start_time

                results["checks"][name] = {
                    "status": "unhealthy",
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                }

                self.metrics.record_histogram(
                    "health_check_duration",
                    duration,
                    labels={"check": name, "status": "unhealthy"},
                )
                self.logger.error(
                    f"Health check {name} failed",
                    extra={"error": str(e), "duration": duration},
                )

        # Determine overall status
        if failed_checks == 0:
            results["overall_status"] = "healthy"
        elif failed_checks < len(self.checks) / 2:
            results["overall_status"] = "degraded"
        else:
            results["overall_status"] = "unhealthy"

        self.metrics.set_gauge(
            "health_status",
            1 if results["overall_status"] == "healthy" else 0,
        )

        return results


# Example usage and testing functions
if __name__ == "__main__":
    import asyncio

    @with_error_handling("test_operation", severity=ErrorSeverity.HIGH)
    @with_retry(RetryPolicy(max_attempts=3, base_delay=0.5))
    async def test_function():
        """Test function for error handling"""
        import random

        if random.random() < 0.7:  # 70% chance of failure
            raise NetworkError("Simulated network failure")
        return "Success!"

    async def test_health_check():
        """Test health check"""
        return {"cpu_usage": 45.2, "memory_usage": 62.1}

    async def main():
        # Test error handling
        try:
            result = await test_function()
            print(f"Function result: {result}")
        except PAKEException as e:
            print(f"Caught PAKE exception: {e.message}")

        # Test health checks
        health_checker = HealthChecker()
        await health_checker.add_health_check("system", test_health_check)
        health_result = await health_checker.run_health_checks()
        print(f"Health check result: {json.dumps(health_result, indent=2)}")

    asyncio.run(main())
