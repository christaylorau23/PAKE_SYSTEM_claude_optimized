#!/usr/bin/env python3
"""PAKE System - Enterprise Logging & Observability Framework
Comprehensive logging, monitoring, and observability for enterprise applications.

This module provides:
- Structured logging with multiple outputs
- Performance monitoring and metrics
- Error tracking and alerting
- Audit logging for compliance
- Distributed tracing support
- Log aggregation and analysis
"""

import asyncio
from datetime import UTC, datetime, timedelta
from enum import Enum
import logging
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any

from datadog import initialize, statsd
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field
import structlog


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogOutput(Enum):
    """Log output destinations."""

    CONSOLE = "console"
    FILE = "file"
    JSON = "json"
    SYSLOG = "syslog"
    DATADOG = "datadog"
    ELASTICSEARCH = "elasticsearch"
    SPLUNK = "splunk"


class MetricType(Enum):
    """Metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class LogEntry(BaseModel):
    """Structured log entry model."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    level: LogLevel = Field(..., description="Log level")
    logger_name: str = Field(..., description="Logger name")
    message: str = Field(..., description="Log message")
    module: str | None = Field(None, description="Module name")
    function: str | None = Field(None, description="Function name")
    line_number: int | None = Field(None, description="Line number")
    thread_id: str | None = Field(None, description="Thread ID")
    process_id: int | None = Field(None, description="Process ID")
    request_id: str | None = Field(None, description="Request ID for tracing")
    user_id: str | None = Field(None, description="User ID")
    session_id: str | None = Field(None, description="Session ID")
    correlation_id: str | None = Field(None, description="Correlation ID")
    service_name: str = Field(default="pake-system", description="Service name")
    environment: str = Field(default="development", description="Environment")
    hostname: str | None = Field(None, description="Hostname")
    ip_address: str | None = Field(None, description="IP address")
    user_agent: str | None = Field(None, description="User agent")
    duration_ms: float | None = Field(
        None, description="Operation duration in milliseconds"
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")
    error_code: str | None = Field(None, description="Error code")
    stack_trace: str | None = Field(None, description="Stack trace")
    extra_data: dict[str, Any] = Field(
        default_factory=dict, description="Additional data"
    )


class MetricEntry(BaseModel):
    """Metric entry model."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metric_name: str = Field(..., description="Metric name")
    metric_type: MetricType = Field(..., description="Metric type")
    value: int | float = Field(..., description="Metric value")
    tags: dict[str, str] = Field(default_factory=dict, description="Metric tags")
    service_name: str = Field(default="pake-system", description="Service name")
    environment: str = Field(default="development", description="Environment")


class AuditEntry(BaseModel):
    """Audit log entry model."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str = Field(..., description="Event type")
    user_id: str | None = Field(None, description="User ID")
    session_id: str | None = Field(None, description="Session ID")
    resource: str | None = Field(None, description="Resource accessed")
    action: str = Field(..., description="Action performed")
    result: str = Field(..., description="Result (success/failure)")
    source_ip: str | None = Field(None, description="Source IP")
    user_agent: str | None = Field(None, description="User agent")
    request_id: str | None = Field(None, description="Request ID")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional details"
    )


class LoggingFramework:
    """Enterprise Logging & Observability Framework.

    Provides comprehensive logging, monitoring, and observability capabilities
    for enterprise applications with support for multiple outputs and formats.
    """

    def __init__(self, environment: str | None = None, log_level: Any = None, outputs: Any = None, service_name: Any = None) -> None:
        self.service_name = service_name
        self.environment = environment
        self.log_level = log_level
        self.outputs = outputs or [LogOutput.CONSOLE, LogOutput.FILE]

        # Initialize components
        self.loggers: dict[str, logging.Logger] = {}
        self.metrics_buffer: list[MetricEntry] = []
        self.audit_logs: list[AuditEntry] = []
        self.tracer = None

        # Setup logging
        self._setup_structured_logging()
        self._setup_outputs()
        self._setup_tracing()
        self._setup_metrics()

        # Performance tracking
        self.performance_metrics: dict[str, list[float]] = {}

    def _setup_structured_logging(self) -> None:
        """Setup structured logging with structlog."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Create main logger
        self.main_logger = structlog.get_logger(self.service_name)

    def _setup_outputs(self) -> None:
        """Setup log outputs."""
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Setup file handlers
        if LogOutput.FILE in self.outputs:
            self._setup_file_handlers()

        # Setup console handler
        if LogOutput.CONSOLE in self.outputs:
            self._setup_console_handler()

        # Setup external services
        if LogOutput.DATADOG in self.outputs:
            self._setup_datadog()

    def _setup_file_handlers(self) -> None:
        """Setup file handlers for different log types."""
        # Application logs
        app_handler = logging.FileHandler(
            self.logs_dir / "application.log", encoding="utf-8"
        )
        app_handler.setLevel(logging.DEBUG)

        # Error logs
        error_handler = logging.FileHandler(
            self.logs_dir / "errors.log", encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)

        # Audit logs
        audit_handler = logging.FileHandler(
            self.logs_dir / "audit.log", encoding="utf-8"
        )
        audit_handler.setLevel(logging.INFO)

        # Performance logs
        perf_handler = logging.FileHandler(
            self.logs_dir / "performance.log", encoding="utf-8"
        )
        perf_handler.setLevel(logging.INFO)

        # Configure formatters
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        for handler in [app_handler, error_handler, audit_handler, perf_handler]:
            handler.setFormatter(formatter)

        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(audit_handler)
        root_logger.addHandler(perf_handler)
        root_logger.setLevel(logging.DEBUG)

    def _setup_console_handler(self) -> None:
        """Setup console handler with colored output."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level.value)

        # Colored formatter for development
        if self.environment == "development":
            formatter = logging.Formatter(
                "\033[92m%(asctime)s\033[0m - \033[94m%(name)s\033[0m - "
                "\033[93m%(levelname)s\033[0m - %(message)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        console_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)

    def _setup_datadog(self) -> None:
        """Setup Datadog integration."""
        try:
            initialize(
                api_key=os.getenv("DATADOG_API_KEY"),
                app_key=os.getenv("DATADOG_APP_KEY"),
            )
            self.datadog_enabled = True
        except (ValueError, RuntimeError) as e:
            print(f"Failed to initialize Datadog: {e}")
            self.datadog_enabled = False

    def _setup_tracing(self) -> None:
        """Setup distributed tracing."""
        try:
            # Create tracer provider
            trace.set_tracer_provider(TracerProvider())
            tracer_provider = trace.get_tracer_provider()

            # Setup Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_AGENT_PORT", "14268")),
            )

            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

        except (ValueError, RuntimeError) as e:
            print(f"Failed to setup tracing: {e}")
            self.tracer = None

    def _setup_metrics(self) -> None:
        """Setup metrics collection."""
        self.metrics_enabled = LogOutput.DATADOG in self.outputs

    # ========================================================================
    # Logging Methods
    # ========================================================================

    def get_logger(self, name: str) -> structlog.BoundLogger:
        """Get a structured logger."""
        return structlog.get_logger(name)

    async def log_structured(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        logger_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log structured message."""
        logger_name = logger_name or self.service_name

        # Create log entry
        log_entry = LogEntry(
            level=level,
            logger_name=logger_name,
            message=message,
            service_name=self.service_name,
            environment=self.environment,
            extra_data=kwargs,
        )

        # Add system information
        log_entry.hostname = os.getenv("HOSTNAME")
        log_entry.process_id = os.getpid()

        # Get logger and log message
        logger = self.get_logger(logger_name)

        # Log with appropriate level
        if level == LogLevel.DEBUG:
            logger.debug(message, **kwargs)
        elif level == LogLevel.INFO:
            logger.info(message, **kwargs)
        elif level == LogLevel.WARNING:
            logger.warning(message, **kwargs)
        elif level == LogLevel.ERROR:
            logger.error(message, **kwargs)
        elif level == LogLevel.CRITICAL:
            logger.critical(message, **kwargs)

        # Send to external services
        if self.datadog_enabled:
            await self._send_to_datadog(log_entry)

    async def log_error(
        self,
        message: str,
        logger_name: str | None = None,
        exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Log error with exception details."""
        extra_data = kwargs.copy()

        if exception:
            extra_data.update(
                {
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                    "stack_trace": traceback.format_exc(),
                }
            )

        await self.log_structured(
            message, level=LogLevel.ERROR, logger_name=logger_name, **extra_data
        )

async def log_performance(self, operation: str, operation: str, operation: str, duration_ms: float, operation: str, operation: str, operation: str, operation: str, logger_name: str | None = None, operation: str, duration_ms: float, kwargs: Any = None, operation: str, duration_ms: float, operation: str, **kwargs: Any) -> None:
        """Log performance metrics."""
        # Store performance metric
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = []

        self.performance_metrics[operation].append(duration_ms)

        # Keep only last 1000 measurements
        if len(self.performance_metrics[operation]) > 1000:
            self.performance_metrics[operation] = self.performance_metrics[operation][
                -1000:
            ]

        await self.log_structured(
            LogLevel.INFO,
            f"Performance: {operation}",
            logger_name,
            operation=operation,
            duration_ms=duration_ms,
            **kwargs,
        )

        # Send metric to Datadog
        if self.metrics_enabled:
            await self._send_metric(
                f"performance.{operation}",
                MetricType.TIMER,
                duration_ms,
                tags={"operation": operation},
            )

async def log_audit(self, event_type: str, user_id: str, resource: str, action: str, result: str, kwargs: Any = None, event_type: str, action: str, result: str, event_type: str, action: str, result: str, user_id: str, resource: str, kwargs: Any = None, **kwargs: Any) -> None:
        """Log audit event."""
        audit_entry = AuditEntry(
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            details=kwargs,
        )

        self.audit_logs.append(audit_entry)

        # Log to audit logger
        audit_logger = self.get_logger("audit")
        audit_logger.info(
            "Audit: %s - %s - %s",
            event_type,
            action,
            result,
            event_type=event_type,
            action=action,
            result=result,
            user_id=user_id,
            resource=resource,
            **kwargs,
        )

    # ========================================================================
    # Metrics Methods
    # ========================================================================

async def _send_metric(self, tags: dict[str, str] | None = None, metric_type: str, metric_name: str, value: float, metric_type: str, metric_name: str, value: float, metric_type: str, metric_name: str, value: float, metric_type: str, metric_name: str, value: float) -> None:
        """Send metric to external service."""
        if not self.metrics_enabled:
            return

        try:
            metric_tags = tags or {}
            metric_tags.update(
                {"service": self.service_name, "environment": self.environment}
            )

            if metric_type == MetricType.COUNTER:
                statsd.increment(metric_name, value, tags=list(metric_tags.items()))
            elif metric_type == MetricType.GAUGE:
                statsd.gauge(metric_name, value, tags=list(metric_tags.items()))
            elif metric_type == MetricType.HISTOGRAM:
                statsd.histogram(metric_name, value, tags=list(metric_tags.items()))
            elif metric_type == MetricType.TIMER:
                statsd.timing(metric_name, value, tags=list(metric_tags.items()))

        except (ValueError, RuntimeError) as e:
            print(f"Failed to send metric: {e}")

async def increment_counter(self, metric_name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        await self._send_metric(metric_name, MetricType.COUNTER, value, tags)

async def set_gauge(self, metric_name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        await self._send_metric(metric_name, MetricType.GAUGE, value, tags)

async def record_histogram(self, metric_name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a histogram metric."""
        await self._send_metric(metric_name, MetricType.HISTOGRAM, value, tags)

async def record_timing(self, metric_name: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        """Record a timing metric."""
        await self._send_metric(metric_name, MetricType.TIMER, duration_ms, tags)

    # ========================================================================
    # Tracing Methods
    # ========================================================================

def start_span(self, name: str, kwargs: Any = None, **kwargs: Any) -> None:
        """Start a new span."""
        if self.tracer:
            return self.tracer.start_span(name, **kwargs)
        return None

def add_span_attribute(self, span: Any = None, span: Any = None, key: str, value: float) -> None:
        """Add attribute to self.span."""
        if span:
            span.set_attribute(key, value)

def add_span_event(self, span: Any = None, span: Any = None, name: str, attributes: dict[str, Any]) -> None:
        """Add event to self.span."""
        if span:
            span.add_event(name, attributes or {})

    # ========================================================================
    # Context Managers and Decorators
    # ========================================================================

def trace_operation(self, operation_name: str, operation_name: str, func: Callable, func: Callable, args: tuple, kwargs: Any = None, operation_name: str, operation_name: str, **kwargs: Any) -> None:
        """Decorator to trace an operation."""

def decorator(self, operation_name: str, operation_name: str, func: Callable, func: Callable, args: tuple, kwargs: Any = None, operation_name: str, operation_name: str, **kwargs: Any) -> None:
async def wrapper(self, operation_name: str, operation_name: str, func: Callable, func: Callable, args: tuple, kwargs: Any = None, operation_name: str, operation_name: str, **kwargs: Any) -> None:
                start_time = time.time()
                span = self.start_span(operation_name)

                try:
                    if span:
                        self.add_span_attribute(span, "operation", operation_name)
                        self.add_span_attribute(span, "function", func.__name__)

                    result = await func(*args, **kwargs)

                    duration_ms = (time.time() - start_time) * 1000
                    await self.log_performance(operation_name, duration_ms)

                    if span:
                        self.add_span_attribute(span, "duration_ms", duration_ms)
                        self.add_span_attribute(span, "success", True)

                    return result

                except (ValueError, RuntimeError) as e:
                    duration_ms = (time.time() - start_time) * 1000
                    await self.log_error(f"Operation failed: {operation_name}", e)

                    if span:
                        self.add_span_attribute(span, "duration_ms", duration_ms)
                        self.add_span_attribute(span, "success", False)
                        self.add_span_attribute(span, "error", str(e))

                    raise

                finally:
                    if span:
                        span.end()

            return wrapper

        return decorator

    # ========================================================================
    # External Service Integration
    # ========================================================================

async def _send_to_datadog(self, log_entry: Any = None) -> None:
        """Send log entry to Datadog."""
        if not self.datadog_enabled:
            return

        try:
            # Convert log entry to Datadog format
            datadog_log = {
                "timestamp": self.log_entry.timestamp.isoformat(),
                "level": self.log_entry.level.value,
                "message": self.log_entry.message,
                "service": self.log_entry.service_name,
                "env": self.log_entry.environment,
                "logger": self.log_entry.logger_name,
                "hostname": self.log_entry.hostname,
                "process_id": self.log_entry.process_id,
                "thread_id": self.log_entry.thread_id,
                "request_id": self.log_entry.request_id,
                "user_id": self.log_entry.user_id,
                "session_id": self.log_entry.session_id,
                "correlation_id": self.log_entry.correlation_id,
                "duration_ms": self.log_entry.duration_ms,
                "memory_usage_mb": self.log_entry.memory_usage_mb,
                "cpu_usage_percent": self.log_entry.cpu_usage_percent,
                "error_code": self.log_entry.error_code,
                "stack_trace": self.log_entry.stack_trace,
                "extra_data": log_entry.extra_data,
            }

            # Send to Datadog (implementation depends on Datadog client)
            # This is a placeholder - actual implementation would use Datadog client

        except (ValueError, RuntimeError) as e:
            print(f"Failed to send log to Datadog: {e}")

    # ========================================================================
    # Analysis and Reporting
    # ========================================================================

    async def get_performance_stats(self, operation: str = None) -> dict[str, Any]:
        """Get performance statistics."""
        if operation:
            if operation not in self.performance_metrics:
                return {}

            values = self.performance_metrics[operation]
            return {
                "operation": operation,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": sorted(values)[len(values) // 2],
                "p95": sorted(values)[int(len(values) * 0.95)],
                "p99": sorted(values)[int(len(values) * 0.99)],
            }
        # Return stats for all operations
        stats = {}
        for op, values in self.performance_metrics.items():
            stats[op] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": sorted(values)[len(values) // 2],
                "p95": sorted(values)[int(len(values) * 0.95)],
                "p99": sorted(values)[int(len(values) * 0.99)],
            }
        return stats

    async def get_audit_logs(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: str = None,
        user_id: str = None,
    ) -> list[AuditEntry]:
        """Get filtered audit logs."""
        filtered_logs = self.audit_logs

        if start_date:
            filtered_logs = [
                log for log in filtered_logs if log.timestamp >= start_date
            ]

        if end_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]

        if event_type:
            filtered_logs = [
                log for log in filtered_logs if log.event_type == event_type
            ]

        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]

        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

    async def generate_log_report(self, days: int = 7) -> dict[str, Any]:
        """Generate comprehensive log report."""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Get audit logs for period
        audit_logs = await self.get_audit_logs(start_date, end_date)

        # Calculate statistics
        event_counts = {}
        user_activity = {}
        resource_access = {}

        for log in audit_logs:
            # Count events by type
            event_counts[log.event_type] = event_counts.get(log.event_type, 0) + 1

            # Count user activity
            if log.user_id:
                user_activity[log.user_id] = user_activity.get(log.user_id, 0) + 1

            # Count resource access
            if log.resource:
                resource_access[log.resource] = resource_access.get(log.resource, 0) + 1

        # Get performance stats
        performance_stats = await self.get_performance_stats()

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
                "tracked_operations": len(performance_stats),
            },
            "event_breakdown": event_counts,
            "top_users": dict(
                sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "top_resources": dict(
                sorted(resource_access.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "performance_summary": performance_stats,
        }


# ========================================================================
# FastAPI Integration
# ========================================================================


class FastAPILoggingMiddleware:
    """FastAPI middleware for request logging."""

    def __init__(self, call_next: Any = None, logging_framework: Any = None, request: Any = None) -> None:
        self.logging_framework = logging_framework

async def __call__(self, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, call_next: Callable, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request, request: Request) -> None:
        start_time = time.time()

        # Extract request information
        request_id = self.request.headers.get("X-Request-ID", f"req_{int(time.time())}")
        user_id = getattr(request.state, "user_id", None)

        # Start span
        span = self.logging_framework.start_span(f"http_request_{request.method}")

        try:
            # Log request start
            await self.logging_framework.log_structured(
                LogLevel.INFO,
                f"Request started: {request.method} {request.url.path}",
                logger_name="http",
                request_id=request_id,
                user_id=user_id,
                method=self.request.method,
                path=self.request.url.path,
                query_params=dict(self.self.request.query_params),
                client_ip=self.request.client.host if self.request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )

            # Add span attributes
            if span:
                self.logging_framework.add_span_attribute(
                    span, "http.method", request.method
                )
                self.logging_framework.add_span_attribute(
                    span, "http.url", str(request.url)
                )
                self.logging_framework.add_span_attribute(
                    span, "http.user_agent", request.headers.get("User-Agent")
                )
                self.logging_framework.add_span_attribute(
                    span, "request_id", request_id
                )

            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log request completion
            await self.logging_framework.log_structured(
                LogLevel.INFO,
                f"Request completed: {request.method} {request.url.path}",
                logger_name="http",
                request_id=request_id,
                user_id=user_id,
                method=self.request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else None,
            )

            # Add span attributes
            if span:
                self.logging_framework.add_span_attribute(
                    span, "http.status_code", response.status_code
                )
                self.logging_framework.add_span_attribute(
                    span, "duration_ms", duration_ms
                )

            # Record performance metric
            await self.logging_framework.record_timing(
                "http.request.duration",
                duration_ms,
                tags={
                    "method": self.request.method,
                    "path": request.url.path,
                    "status_code": str(response.status_code),
                },
            )

            return response

        except (ValueError, RuntimeError) as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            await self.logging_framework.log_error(
                f"Request failed: {request.method} {request.url.path}",
                e,
                logger_name="http",
                request_id=request_id,
                user_id=user_id,
                method=self.request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )

            # Add span attributes
            if span:
                self.logging_framework.add_span_attribute(span, "error", str(e))
                self.logging_framework.add_span_attribute(
                    span, "duration_ms", duration_ms
                )

            raise

        finally:
            if span:
                span.end()


if __name__ == "__main__":
    # Example usage
    async def main(self) -> None:
        # Initialize logging framework
        logging_framework = LoggingFramework(
            service_name="pake-system",
            environment="development",
            outputs=[LogOutput.CONSOLE, LogOutput.FILE],
        )

        # Get logger
        logger = logging_framework.get_logger("example")

        # Log structured message
        await logging_framework.log_structured(
            LogLevel.INFO,
            "Application started",
            extra_data={"version": "1.0.0", "build": "123"},
        )

        # Log performance
        await logging_framework.log_performance("database_query", 150.5)

        # Log audit event
        await logging_framework.log_audit(
            "user_login",
            "authenticate",
            "success",
            user_id="user123",
            resource="/api/auth/login",
        )

        # Generate report
        report = await logging_framework.generate_log_report()
        print(f"Log report: {report['summary']}")

    asyncio.run(main())
