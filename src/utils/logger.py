#!/usr/bin/env python3
"""Structured Logger for PAKE System
Structlog-based JSON logger with timestamp, level, service name, and correlation IDs
"""

import logging
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import LoggerFactory

# Add configs to path for configuration access
sys.path.insert(0, str(Path(__file__).parent.parent / "configs"))

try:
    from service_config import get_config

    config = get_config()
    logging_config = config.logging
except ImportError:
    # Fallback configuration if service_config is not available
    class LoggingConfig:
        default_level = "INFO"
        json_formatting = True
        file_logging_enabled = False
        file_path = "pake_system.log"
        max_file_size = "10MB"
        backup_count = 5

    logging_config = LoggingConfig()


class TimestampProcessor:
    """Add ISO8601 timestamp to log entries"""

    def __call__(self, logger, method_name, event_dict):
        event_dict["timestamp"] = datetime.now(UTC).isoformat()
        return event_dict


class ServiceInfoProcessor:
    """Add service information to log entries"""

    def __init__(self, service_name: str = "pake-system"):
        self.service_name = service_name
        self.version = os.getenv("PAKE_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.hostname = platform.node()
        self.pid = os.getpid()

    def __call__(self, logger, method_name, event_dict):
        event_dict.update(
            {
                "service": self.service_name,
                "version": self.version,
                "environment": self.environment,
                "hostname": self.hostname,
                "pid": self.pid,
            },
        )
        return event_dict


class LevelNormalizer:
    """Normalize log level to uppercase"""

    def __call__(self, logger, method_name, event_dict):
        if "level" in event_dict:
            event_dict["level"] = event_dict["level"].upper()
        else:
            # Map method names to levels
            level_mapping = {
                "debug": "DEBUG",
                "info": "INFO",
                "warning": "WARN",
                "warn": "WARN",
                "error": "ERROR",
                "critical": "CRITICAL",
                "exception": "ERROR",
            }
            event_dict["level"] = level_mapping.get(method_name, "INFO")
        return event_dict


class ErrorProcessor:
    """Process exception information"""

    def __call__(self, logger, method_name, event_dict):
        exc_info = event_dict.pop("exc_info", None)
        if exc_info:
            if exc_info is True:
                exc_info = sys.exc_info()

            if exc_info and exc_info[0] is not None:
                import traceback

                event_dict["error"] = {
                    "type": exc_info[0].__name__,
                    "message": str(exc_info[1]),
                    "traceback": "".join(traceback.format_exception(*exc_info)),
                }
        return event_dict


def setup_structured_logging(
    service_name: str = "pake-system",
    level: str = None,
    json_format: bool = None,
    file_logging: bool = None,
) -> structlog.BoundLogger:
    """Setup structured logging with consistent format

    Args:
        service_name: Name of the service
        level: Log level (DEBUG, INFO, WARN, ERROR)
        json_format: Whether to use JSON formatting
        file_logging: Whether to enable file logging

    Returns:
        Configured structlog logger
    """
    # Use configuration values with overrides
    log_level = level or getattr(logging_config, "default_level", "INFO")
    use_json = (
        json_format
        if json_format is not None
        else getattr(logging_config, "json_formatting", True)
    )
    use_file = (
        file_logging
        if file_logging is not None
        else getattr(logging_config, "file_logging_enabled", False)
    )

    # Configure processors
    processors = [
        structlog.stdlib.filter_by_level,
        TimestampProcessor(),
        ServiceInfoProcessor(service_name),
        LevelNormalizer(),
        ErrorProcessor(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if use_json:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[],
    )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logging.getLogger().addHandler(console_handler)

    # Add file handler if enabled
    if use_file:
        try:
            from logging.handlers import RotatingFileHandler

            file_path = getattr(logging_config, "file_path", "pake_system.log")
            max_size = _parse_size(getattr(logging_config, "max_file_size", "10MB"))
            backup_count = getattr(logging_config, "backup_count", 5)

            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=max_size,
                backupCount=backup_count,
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging: {e}", file=sys.stderr)

    return structlog.get_logger(service_name)


def _parse_size(size_str: str) -> int:
    """Parse file size string (e.g., '10MB', '1GB')"""
    units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
    size_str = size_str.upper().strip()

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            return int(size_str[: -len(unit)]) * multiplier

    # Default to MB if no unit specified
    try:
        return int(size_str) * 1024**2
    except ValueError:
        return 10 * 1024**2  # Default 10MB


class StructuredLogger:
    """Enhanced logger with context support and structured methods"""

    def __init__(
        self,
        logger: structlog.BoundLogger = None,
        service_name: str = "pake-system",
    ):
        self.logger = logger or setup_structured_logging(service_name)
        self.context = {}

    def bind(self, **kwargs) -> "StructuredLogger":
        """Create child logger with additional context"""
        bound_logger = self.logger.bind(**kwargs)
        child = StructuredLogger(bound_logger)
        child.context = {**self.context, **kwargs}
        return child

    def with_correlation_id(self, correlation_id: str) -> "StructuredLogger":
        """Add correlation ID for request tracking"""
        return self.bind(correlation_id=correlation_id)

    def with_user(self, user_id: str, username: str = None) -> "StructuredLogger":
        """Add user context for audit logging"""
        context = {"user_id": user_id}
        if username:
            context["username"] = username
        return self.bind(**context)

    def with_request(
        self,
        request_id: str = None,
        method: str = None,
        path: str = None,
        ip: str = None,
        user_agent: str = None,
    ) -> "StructuredLogger":
        """Add request context for API logging"""
        context = {}
        if request_id:
            context["request_id"] = request_id
        if method:
            context["method"] = method
        if path:
            context["path"] = path
        if ip:
            context["ip"] = ip
        if user_agent:
            context["user_agent"] = user_agent
        return self.bind(**context)

    # Basic logging methods
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)

    def warn(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message (alias)"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with optional exception"""
        if error:
            kwargs["exc_info"] = error
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, **kwargs)

    # Structured logging methods for specific use cases
    def http(
        self,
        message: str,
        method: str = None,
        path: str = None,
        status_code: int = None,
        duration: float = None,
        user_id: str = None,
        error: Exception = None,
        **kwargs,
    ):
        """Log HTTP request/response"""
        level = self._get_http_log_level(status_code, error)

        http_data = {
            "http": {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration,
            },
        }
        if user_id:
            http_data["user_id"] = user_id
        if error:
            http_data["exc_info"] = error

        getattr(self.logger, level)(message, **http_data, **kwargs)

    def database(
        self,
        message: str,
        operation: str = None,
        table: str = None,
        duration: float = None,
        row_count: int = None,
        error: Exception = None,
        **kwargs,
    ):
        """Log database operations"""
        level = "error" if error else "debug"

        db_data = {
            "database": {
                "operation": operation,
                "table": table,
                "duration_ms": duration,
                "row_count": row_count,
            },
        }
        if error:
            db_data["exc_info"] = error

        getattr(self.logger, level)(message, **db_data, **kwargs)

    def security(
        self,
        message: str,
        event: str = None,
        user_id: str = None,
        ip: str = None,
        user_agent: str = None,
        success: bool = None,
        reason: str = None,
        **kwargs,
    ):
        """Log security events"""
        level = "info" if success else "warning"

        security_data = {
            "security": {"event": event, "success": success, "reason": reason},
        }
        if user_id:
            security_data["user_id"] = user_id
        if ip:
            security_data["ip"] = ip
        if user_agent:
            security_data["user_agent"] = user_agent

        getattr(self.logger, level)(message, **security_data, **kwargs)

    def business(
        self,
        message: str,
        event: str = None,
        user_id: str = None,
        entity_type: str = None,
        entity_id: str = None,
        action: str = None,
        metadata: dict = None,
        **kwargs,
    ):
        """Log business events"""
        business_data = {
            "business": {
                "event": event,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "metadata": metadata,
            },
        }
        if user_id:
            business_data["user_id"] = user_id

        self.logger.info(message, **business_data, **kwargs)

    def performance(
        self,
        message: str,
        operation: str = None,
        duration: float = None,
        memory_mb: float = None,
        cpu_percent: float = None,
        **kwargs,
    ):
        """Log performance metrics"""
        perf_data = {
            "performance": {
                "operation": operation,
                "duration_ms": duration,
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
            },
        }

        self.logger.info(message, **perf_data, **kwargs)

    def _get_http_log_level(self, status_code: int, error: Exception) -> str:
        """Get appropriate log level for HTTP status codes"""
        if error:
            return "error"
        if status_code and status_code >= 500:
            return "error"
        if status_code and status_code >= 400:
            return "warning"
        return "info"

    def timer(self, operation: str = None):
        """Context manager for timing operations"""
        return TimerContext(self, operation)


class TimerContext:
    """Context manager for timing operations"""

    def __init__(self, logger: StructuredLogger, operation: str = None):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        if self.operation:
            self.logger.debug(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.time() - self.start_time) * 1000  # Convert to milliseconds

            if exc_type:
                self.logger.error(
                    f"Operation {self.operation or 'timer'} failed",
                    error=exc_val,
                    duration_ms=duration,
                )
            else:
                self.logger.info(
                    f"Completed {self.operation or 'timer'}",
                    duration_ms=duration,
                )


# Create default logger instance
_default_logger = None


def get_logger(service_name: str = "pake-system") -> StructuredLogger:
    """Get or create default logger instance"""
    global _default_logger
    if _default_logger is None:
        _default_logger = StructuredLogger(service_name=service_name)
    return _default_logger


# Convenience function for quick access
logger = get_logger()

# FastAPI/Starlette middleware integration


def setup_request_logging():
    """Setup request logging for web frameworks"""
    try:
        import uuid

        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class LoggingMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, logger: StructuredLogger = None):
                super().__init__(app)
                self.logger = logger or get_logger()

            async def dispatch(self, request: Request, call_next):
                start_time = time.time()
                request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

                # Add request context
                request_logger = self.logger.with_request(
                    request_id=request_id,
                    method=request.method,
                    path=str(request.url.path),
                    ip=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                )

                # Log request start
                request_logger.info("HTTP Request started")

                try:
                    response = await call_next(request)
                    duration = (time.time() - start_time) * 1000

                    # Log response
                    request_logger.http(
                        "HTTP Request completed",
                        method=request.method,
                        path=str(request.url.path),
                        status_code=response.status_code,
                        duration=duration,
                    )

                    # Add request ID to response headers
                    response.headers["x-request-id"] = request_id

                    return response

                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    request_logger.http(
                        "HTTP Request failed",
                        method=request.method,
                        path=str(request.url.path),
                        duration=duration,
                        error=e,
                    )
                    raise

        return LoggingMiddleware

    except ImportError:
        # Return a no-op class if starlette is not available
        class NoOpMiddleware:
            def __init__(self, app, logger=None):
                pass

        return NoOpMiddleware


if __name__ == "__main__":
    # Example usage
    logger = get_logger("test-service")

    logger.info("Service started", version="1.0.0")
    logger.debug("Debug message", extra_data={"key": "value"})

    # Context logging
    user_logger = logger.with_user("user123", "john_doe")
    user_logger.info("User action", action="login")

    # HTTP logging
    logger.http(
        "API request processed",
        method="POST",
        path="/api/v1/tasks",
        status_code=201,
        duration=150.5,
    )

    # Database logging
    logger.database(
        "Query executed",
        operation="SELECT",
        table="tasks",
        duration=25.3,
        row_count=10,
    )

    # Timer usage
    with logger.timer("expensive_operation"):
        time.sleep(0.1)  # Simulate work
