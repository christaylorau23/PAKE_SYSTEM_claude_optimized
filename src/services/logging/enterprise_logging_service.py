#!/usr/bin/env python3
"""PAKE System - Enterprise Logging Service
Comprehensive logging service implementing enterprise best practices for:
- Structured JSON logging
- Security-aware logging (no secrets)
- Correlation IDs and context
- Performance monitoring
- Audit trails
- Compliance logging
"""

import asyncio
import logging
import os
import re
import sys
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field, validator

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from configs.service_config import get_config
    from src.utils.logger import StructuredLogger, get_logger
except ImportError:
    # Fallback imports
    StructuredLogger = None
    get_logger = None


class LogLevel(Enum):
    """Standard log levels with numeric values for filtering"""

    DEBUG = (10, "DEBUG")
    INFO = (20, "INFO")
    WARNING = (30, "WARNING")
    ERROR = (40, "ERROR")
    CRITICAL = (50, "CRITICAL")

    def __init__(self, level: int, name: str):
        self.level = level
        self.name = name


class LogCategory(Enum):
    """Log categories for better organization"""

    APPLICATION = "application"
    SECURITY = "security"
    AUDIT = "audit"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL = "external"


class SecurityLevel(Enum):
    """Security classification levels"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class LoggingConfig:
    """Centralized logging configuration"""

    # Basic settings
    service_name: str = "pake-system"
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    log_level: LogLevel = LogLevel.INFO
    json_format: bool = True

    # Output destinations
    console_enabled: bool = True
    file_enabled: bool = True
    syslog_enabled: bool = False
    external_enabled: bool = False

    # File settings
    log_directory: str = "logs"
    max_file_size_mb: int = 100
    backup_count: int = 10
    rotation_frequency: str = "daily"  # daily, weekly, monthly

    # Security settings
    mask_sensitive_data: bool = True
    security_level: SecurityLevel = SecurityLevel.INTERNAL
    audit_retention_days: int = 2555  # 7 years for compliance

    # Performance settings
    async_logging: bool = True
    buffer_size: int = 1000
    flush_interval_seconds: int = 5

    # Monitoring settings
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    alerting_enabled: bool = True

    def __post_init__(self):
        """Validate configuration"""
        if self.log_level not in LogLevel:
            raise ValueError(f"Invalid log level: {self.log_level}")

        if self.max_file_size_mb <= 0:
            raise ValueError("Max file size must be positive")

        if self.backup_count < 0:
            raise ValueError("Backup count cannot be negative")


class SensitiveDataMasker:
    """Utility class to mask sensitive data in logs"""

    # Common patterns for sensitive data
    SENSITIVE_PATTERNS = {
        "REDACTED_SECRET": r'(?i)(REDACTED_SECRET|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        "token": r'(?i)(token|access_token|refresh_token|bearer)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        "api_key": r'(?i)(api_key|apikey|key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        "secret": r'(?i)(secret|secret_key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    }

    @classmethod
    def mask_string(cls, text: str, mask_char: str = "*") -> str:
        """Mask sensitive data in a string"""
        if not isinstance(text, str):
            return text

        masked_text = text

        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if pattern_name in ["email", "phone"]:
                # For emails and phones, mask partially
                masked_text = re.sub(
                    pattern,
                    lambda m: cls._partial_mask(m.group(), mask_char),
                    masked_text,
                )
            else:
                # For other patterns, mask completely
                masked_text = re.sub(
                    pattern, lambda m: f"{m.group(1)}={mask_char * 8}", masked_text
                )

        return masked_text

    @classmethod
    def _partial_mask(cls, text: str, mask_char: str) -> str:
        """Partially mask text (show first and last characters)"""
        if len(text) <= 4:
            return mask_char * len(text)
        return text[0] + mask_char * (len(text) - 2) + text[-1]

    @classmethod
    def mask_dict(cls, data: dict[str, Any], mask_char: str = "*") -> dict[str, Any]:
        """Recursively mask sensitive data in a dictionary"""
        if not isinstance(data, dict):
            return data

        masked_data = {}
        sensitive_keys = {
            "REDACTED_SECRET",
            "token",
            "secret",
            "key",
            "api_key",
            "access_token",
            "refresh_token",
        }

        for key, value in data.items():
            key_lower = key.lower()

            if key_lower in sensitive_keys:
                masked_data[key] = mask_char * 8
            elif isinstance(value, str):
                masked_data[key] = cls.mask_string(value, mask_char)
            elif isinstance(value, dict):
                masked_data[key] = cls.mask_dict(value, mask_char)
            elif isinstance(value, list):
                masked_data[key] = [
                    cls.mask_dict(item, mask_char) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked_data[key] = value

        return masked_data


class LogContext:
    """Context manager for adding contextual information to logs"""

    def __init__(self, logger: "EnterpriseLoggingService", **context):
        self.logger = logger
        self.context = context
        self.previous_context = {}

    def __enter__(self):
        # Store previous context
        self.previous_context = self.logger.context.copy()
        # Add new context
        self.logger.context.update(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        self.logger.context = self.previous_context


class LogEntry(BaseModel):
    """Structured log entry model"""

    # Core fields
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    level: str = Field(..., description="Log level")
    category: str = Field(
        default=LogCategory.APPLICATION.value, description="Log category"
    )
    message: str = Field(..., description="Log message")

    # Service identification
    service_name: str = Field(default="pake-system", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")

    # Request/Correlation tracking
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for request tracing"
    )
    request_id: Optional[str] = Field(None, description="Request ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")

    # System information
    hostname: Optional[str] = Field(None, description="Hostname")
    process_id: Optional[int] = Field(None, description="Process ID")
    thread_id: Optional[str] = Field(None, description="Thread ID")

    # Performance metrics
    duration_ms: Optional[float] = Field(
        None, description="Operation duration in milliseconds"
    )
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")

    # Error information
    error_code: Optional[str] = Field(None, description="Error code")
    error_type: Optional[str] = Field(None, description="Error type")
    stack_trace: Optional[str] = Field(None, description="Stack trace")

    # Security information
    security_level: str = Field(
        default=SecurityLevel.INTERNAL.value, description="Security classification"
    )
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent")

    # Additional context
    extra_data: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured data"
    )

    @validator("extra_data")
    def validate_extra_data(cls, v):
        """Ensure extra_data doesn't contain sensitive information"""
        if isinstance(v, dict):
            return SensitiveDataMasker.mask_dict(v)
        return v


class EnterpriseLoggingService:
    """Enterprise-grade logging service implementing all best practices:
    - Structured JSON logging
    - Security-aware logging (no secrets)
    - Correlation IDs and context
    - Performance monitoring
    - Audit trails
    - Compliance logging
    """

    def __init__(self, config: LoggingConfig = None):
        self.config = config or LoggingConfig()
        self.context: dict[str, Any] = {}
        self.loggers: dict[str, logging.Logger] = {}
        self.metrics_buffer: list[dict[str, Any]] = []
        self.audit_logs: list[LogEntry] = []

        # Initialize logging infrastructure
        self._setup_logging()
        self._setup_file_handlers()
        self._setup_console_handler()

        # Start background tasks
        if self.config.async_logging:
            self._start_background_tasks()

    def _setup_logging(self):
        """Setup structured logging with structlog"""
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
        ]

        if self.config.json_format:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _setup_file_handlers(self):
        """Setup file handlers for different log categories"""
        if not self.config.file_enabled:
            return

        # Create log directory
        log_dir = Path(self.config.log_directory)
        log_dir.mkdir(exist_ok=True)

        # Setup handlers for different categories
        categories = [
            LogCategory.APPLICATION.value,
            LogCategory.SECURITY.value,
            LogCategory.AUDIT.value,
            LogCategory.PERFORMANCE.value,
            LogCategory.API.value,
            LogCategory.DATABASE.value,
        ]

        for category in categories:
            self._create_file_handler(log_dir, category)

    def _create_file_handler(self, log_dir: Path, category: str):
        """Create a file handler for a specific category"""
        try:
            from logging.handlers import RotatingFileHandler

            log_file = log_dir / f"{category}.log"
            max_bytes = self.config.max_file_size_mb * 1024 * 1024

            handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )

            handler.setLevel(self.config.log_level.level)

            # Create logger for this category
            logger = logging.getLogger(f"{self.config.service_name}.{category}")
            logger.addHandler(handler)
            logger.setLevel(self.config.log_level.level)

            self.loggers[category] = logger

        except Exception as e:
            print(f"Failed to create file handler for {category}: {e}", file=sys.stderr)

    def _setup_console_handler(self):
        """Setup console handler"""
        if not self.config.console_enabled:
            return

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.config.log_level.level)

        # Colored formatter for development
        if self.config.environment == "development":
            formatter = logging.Formatter(
                "\033[92m%(asctime)s\033[0m - \033[94m%(name)s\033[0m - "
                "\033[93m%(levelname)s\033[0m - %(message)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        console_handler.setFormatter(formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.setLevel(self.config.log_level.level)

    def _start_background_tasks(self):
        """Start background tasks for async logging"""
        # This would be implemented with asyncio tasks in a real application

    # ========================================================================
    # Context Management
    # ========================================================================

    def with_context(self, **context) -> LogContext:
        """Create a context manager for adding contextual information"""
        return LogContext(self, **context)

    def with_correlation_id(self, correlation_id: str = None) -> LogContext:
        """Add correlation ID for request tracing"""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        return self.with_context(correlation_id=correlation_id)

    def with_user(self, user_id: str, username: str = None) -> LogContext:
        """Add user context for audit logging"""
        context = {"user_id": user_id}
        if username:
            context["username"] = username
        return self.with_context(**context)

    def with_request(
        self,
        request_id: str = None,
        method: str = None,
        path: str = None,
        ip: str = None,
        user_agent: str = None,
    ) -> LogContext:
        """Add request context for API logging"""
        context = {}
        if request_id:
            context["request_id"] = request_id
        if method:
            context["method"] = method
        if path:
            context["path"] = path
        if ip:
            context["ip_address"] = ip
        if user_agent:
            context["user_agent"] = user_agent
        return self.with_context(**context)

    # ========================================================================
    # Core Logging Methods
    # ========================================================================

    def _create_log_entry(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.APPLICATION,
        **kwargs,
    ) -> LogEntry:
        """Create a structured log entry"""
        # Merge context and kwargs
        log_data = {**self.context, **kwargs}

        # Mask sensitive data if enabled
        if self.config.mask_sensitive_data:
            log_data = SensitiveDataMasker.mask_dict(log_data)

        # Create log entry
        entry = LogEntry(
            level=level.name,
            category=category.value,
            message=message,
            service_name=self.config.service_name,
            environment=self.config.environment,
            security_level=self.config.security_level.value,
            extra_data=log_data,
        )

        # Add system information
        entry.hostname = os.getenv("HOSTNAME", "unknown")
        entry.process_id = os.getpid()

        return entry

    def _log_entry(self, entry: LogEntry):
        """Log a structured entry"""
        # Get appropriate logger
        logger_name = f"{self.config.service_name}.{entry.category}"
        logger = logging.getLogger(logger_name)

        # Convert to dict for JSON logging
        log_dict = entry.dict()

        # Log with appropriate level
        if entry.level == LogLevel.DEBUG.name:
            logger.debug(entry.message, extra=log_dict)
        elif entry.level == LogLevel.INFO.name:
            logger.info(entry.message, extra=log_dict)
        elif entry.level == LogLevel.WARNING.name:
            logger.warning(entry.message, extra=log_dict)
        elif entry.level == LogLevel.ERROR.name:
            logger.error(entry.message, extra=log_dict)
        elif entry.level == LogLevel.CRITICAL.name:
            logger.critical(entry.message, extra=log_dict)

    def debug(
        self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs
    ):
        """Log debug message"""
        entry = self._create_log_entry(LogLevel.DEBUG, message, category, **kwargs)
        self._log_entry(entry)

    def info(
        self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs
    ):
        """Log info message"""
        entry = self._create_log_entry(LogLevel.INFO, message, category, **kwargs)
        self._log_entry(entry)

    def warning(
        self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs
    ):
        """Log warning message"""
        entry = self._create_log_entry(LogLevel.WARNING, message, category, **kwargs)
        self._log_entry(entry)

    def error(
        self,
        message: str,
        category: LogCategory = LogCategory.APPLICATION,
        error: Exception = None,
        **kwargs,
    ):
        """Log error message with optional exception"""
        if error:
            kwargs.update(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "stack_trace": str(error.__traceback__)
                    if hasattr(error, "__traceback__")
                    else None,
                }
            )

        entry = self._create_log_entry(LogLevel.ERROR, message, category, **kwargs)
        self._log_entry(entry)

    def critical(
        self, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs
    ):
        """Log critical message"""
        entry = self._create_log_entry(LogLevel.CRITICAL, message, category, **kwargs)
        self._log_entry(entry)

    # ========================================================================
    # Specialized Logging Methods
    # ========================================================================

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
        security_data = {
            "event": event,
            "success": success,
            "reason": reason,
            "ip_address": ip,
            "user_agent": user_agent,
            **kwargs,
        }
        if user_id:
            security_data["user_id"] = user_id

        level = LogLevel.INFO if success else LogLevel.WARNING
        entry = self._create_log_entry(
            level, message, LogCategory.SECURITY, **security_data
        )
        self._log_entry(entry)

    def audit(
        self,
        message: str,
        event_type: str,
        action: str,
        result: str,
        user_id: str = None,
        resource: str = None,
        **kwargs,
    ):
        """Log audit events for compliance"""
        audit_data = {
            "event_type": event_type,
            "action": action,
            "result": result,
            "resource": resource,
            **kwargs,
        }
        if user_id:
            audit_data["user_id"] = user_id

        entry = self._create_log_entry(
            LogLevel.INFO, message, LogCategory.AUDIT, **audit_data
        )
        self._log_entry(entry)

        # Store in audit logs for compliance
        self.audit_logs.append(entry)

    def performance(
        self,
        message: str,
        operation: str = None,
        duration_ms: float = None,
        memory_mb: float = None,
        cpu_percent: float = None,
        **kwargs,
    ):
        """Log performance metrics"""
        perf_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            "memory_usage_mb": memory_mb,
            "cpu_usage_percent": cpu_percent,
            **kwargs,
        }

        entry = self._create_log_entry(
            LogLevel.INFO, message, LogCategory.PERFORMANCE, **perf_data
        )
        self._log_entry(entry)

    def api(
        self,
        message: str,
        method: str = None,
        path: str = None,
        status_code: int = None,
        duration_ms: float = None,
        user_id: str = None,
        error: Exception = None,
        **kwargs,
    ):
        """Log API requests/responses"""
        api_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **kwargs,
        }
        if user_id:
            api_data["user_id"] = user_id
        if error:
            api_data.update(
                {"error_type": type(error).__name__, "error_message": str(error)}
            )

        # Determine log level based on status code
        if error or (status_code and status_code >= 500):
            level = LogLevel.ERROR
        elif status_code and status_code >= 400:
            level = LogLevel.WARNING
        else:
            level = LogLevel.INFO

        entry = self._create_log_entry(level, message, LogCategory.API, **api_data)
        self._log_entry(entry)

    def database(
        self,
        message: str,
        operation: str = None,
        table: str = None,
        duration_ms: float = None,
        row_count: int = None,
        error: Exception = None,
        **kwargs,
    ):
        """Log database operations"""
        db_data = {
            "operation": operation,
            "table": table,
            "duration_ms": duration_ms,
            "row_count": row_count,
            **kwargs,
        }
        if error:
            db_data.update(
                {"error_type": type(error).__name__, "error_message": str(error)}
            )

        level = LogLevel.ERROR if error else LogLevel.DEBUG
        entry = self._create_log_entry(level, message, LogCategory.DATABASE, **db_data)
        self._log_entry(entry)

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
            "event": event,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "metadata": metadata or {},
            **kwargs,
        }
        if user_id:
            business_data["user_id"] = user_id

        entry = self._create_log_entry(
            LogLevel.INFO, message, LogCategory.BUSINESS, **business_data
        )
        self._log_entry(entry)

    # ========================================================================
    # Context Managers and Decorators
    # ========================================================================

    @asynccontextmanager
    async def timer(self, operation: str = None) -> AsyncGenerator[None, None]:
        """Context manager for timing operations"""
        start_time = time.time()
        if operation:
            self.debug(
                f"Starting {operation}",
                category=LogCategory.PERFORMANCE,
                operation=operation,
            )

        try:
            yield
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.error(
                f"Operation {operation or 'timer'} failed",
                category=LogCategory.PERFORMANCE,
                error=e,
                operation=operation,
                duration_ms=duration_ms,
            )
            raise
        else:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Completed {operation or 'timer'}",
                category=LogCategory.PERFORMANCE,
                operation=operation,
                duration_ms=duration_ms,
            )

    def trace_operation(self, operation_name: str):
        """Decorator to trace an operation"""

        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                async with self.timer(operation_name):
                    return await func(*args, **kwargs)

            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    self.info(
                        f"Completed {operation_name}",
                        category=LogCategory.PERFORMANCE,
                        operation=operation_name,
                        duration_ms=duration_ms,
                    )
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.error(
                        f"Operation {operation_name} failed",
                        category=LogCategory.PERFORMANCE,
                        error=e,
                        operation=operation_name,
                        duration_ms=duration_ms,
                    )
                    raise

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    # ========================================================================
    # Analysis and Reporting
    # ========================================================================

    def get_audit_logs(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: str = None,
        user_id: str = None,
    ) -> list[LogEntry]:
        """Get filtered audit logs"""
        filtered_logs = self.audit_logs

        if start_date:
            filtered_logs = [
                log for log in filtered_logs if log.timestamp >= start_date
            ]

        if end_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]

        if event_type:
            filtered_logs = [
                log
                for log in filtered_logs
                if log.extra_data.get("event_type") == event_type
            ]

        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]

        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

    def generate_compliance_report(self, days: int = 30) -> dict[str, Any]:
        """Generate compliance report for audit logs"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        audit_logs = self.get_audit_logs(start_date, end_date)

        # Calculate statistics
        event_counts = {}
        user_activity = {}
        resource_access = {}

        for log in audit_logs:
            event_type = log.extra_data.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            if log.user_id:
                user_activity[log.user_id] = user_activity.get(log.user_id, 0) + 1

            resource = log.extra_data.get("resource")
            if resource:
                resource_access[resource] = resource_access.get(resource, 0) + 1

        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "summary": {
                "total_audit_events": len(audit_logs),
                "unique_users": len(user_activity),
                "unique_resources": len(resource_access),
            },
            "event_breakdown": event_counts,
            "top_users": dict(
                sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "top_resources": dict(
                sorted(resource_access.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }


# ========================================================================
# Global Logger Instance
# ========================================================================

# Create global logger instance
_global_logger: Optional[EnterpriseLoggingService] = None


def get_enterprise_logger(config: LoggingConfig = None) -> EnterpriseLoggingService:
    """Get or create global enterprise logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = EnterpriseLoggingService(config)
    return _global_logger


# Convenience function for quick access
def get_logger() -> EnterpriseLoggingService:
    """Get the global enterprise logger"""
    return get_enterprise_logger()


# ========================================================================
# Example Usage
# ========================================================================

if __name__ == "__main__":
    # Example usage
    logger = get_logger()

    # Basic logging
    logger.info("Service started", version="1.0.0")
    logger.debug("Debug message", extra_data={"key": "value"})

    # Context logging
    with logger.with_correlation_id("req-123"):
        logger.info("Processing request")

        with logger.with_user("user123", "john_doe"):
            logger.info("User action", action="login")

    # Security logging
    logger.security(
        "User login attempt",
        event="login",
        user_id="user123",
        ip="192.168.1.100",
        success=True,
    )

    # Audit logging
    logger.audit(
        "User accessed resource",
        event_type="resource_access",
        action="read",
        result="success",
        user_id="user123",
        resource="/api/documents/123",
    )

    # Performance logging
    logger.performance(
        "Database query completed",
        operation="SELECT",
        duration_ms=150.5,
        memory_mb=25.3,
    )

    # API logging
    logger.api(
        "API request processed",
        method="POST",
        path="/api/v1/tasks",
        status_code=201,
        duration_ms=250.0,
        user_id="user123",
    )

    # Timer usage
    import asyncio

    async def example_async_operation():
        async with logger.timer("expensive_operation"):
            await asyncio.sleep(0.1)  # Simulate work

    # Decorator usage
    @logger.trace_operation("data_processing")
    def process_data():
        time.sleep(0.05)  # Simulate work
        return "processed"

    # Generate compliance report
    report = logger.generate_compliance_report(days=7)
    print(f"Compliance report: {report['summary']}")
