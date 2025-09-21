#!/usr/bin/env python3
"""
PAKE System - Enterprise Logging & Observability Framework
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
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, UTC, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

import aiofiles
import structlog
from datadog import initialize, statsd
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from pydantic import BaseModel, Field


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogOutput(Enum):
    """Log output destinations"""
    CONSOLE = "console"
    FILE = "file"
    JSON = "json"
    SYSLOG = "syslog"
    DATADOG = "datadog"
    ELASTICSEARCH = "elasticsearch"
    SPLUNK = "splunk"


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class LogEntry(BaseModel):
    """Structured log entry model"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    level: LogLevel = Field(..., description="Log level")
    logger_name: str = Field(..., description="Logger name")
    message: str = Field(..., description="Log message")
    module: Optional[str] = Field(None, description="Module name")
    function: Optional[str] = Field(None, description="Function name")
    line_number: Optional[int] = Field(None, description="Line number")
    thread_id: Optional[str] = Field(None, description="Thread ID")
    process_id: Optional[int] = Field(None, description="Process ID")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    service_name: str = Field(default="pake-system", description="Service name")
    environment: str = Field(default="development", description="Environment")
    hostname: Optional[str] = Field(None, description="Hostname")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    duration_ms: Optional[float] = Field(None, description="Operation duration in milliseconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    error_code: Optional[str] = Field(None, description="Error code")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class MetricEntry(BaseModel):
    """Metric entry model"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metric_name: str = Field(..., description="Metric name")
    metric_type: MetricType = Field(..., description="Metric type")
    value: Union[int, float] = Field(..., description="Metric value")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    service_name: str = Field(default="pake-system", description="Service name")
    environment: str = Field(default="development", description="Environment")


class AuditEntry(BaseModel):
    """Audit log entry model"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str = Field(..., description="Event type")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    resource: Optional[str] = Field(None, description="Resource accessed")
    action: str = Field(..., description="Action performed")
    result: str = Field(..., description="Result (success/failure)")
    source_ip: Optional[str] = Field(None, description="Source IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    request_id: Optional[str] = Field(None, description="Request ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class LoggingFramework:
    """
    Enterprise Logging & Observability Framework
    
    Provides comprehensive logging, monitoring, and observability capabilities
    for enterprise applications with support for multiple outputs and formats.
    """
    
    def __init__(
        self,
        service_name: str = "pake-system",
        environment: str = "development",
        log_level: LogLevel = LogLevel.INFO,
        outputs: List[LogOutput] = None
    ):
        self.service_name = service_name
        self.environment = environment
        self.log_level = log_level
        self.outputs = outputs or [LogOutput.CONSOLE, LogOutput.FILE]
        
        # Initialize components
        self.loggers: Dict[str, logging.Logger] = {}
        self.metrics_buffer: List[MetricEntry] = []
        self.audit_logs: List[AuditEntry] = []
        self.tracer = None
        
        # Setup logging
        self._setup_structured_logging()
        self._setup_outputs()
        self._setup_tracing()
        self._setup_metrics()
        
        # Performance tracking
        self.performance_metrics: Dict[str, List[float]] = {}
        
    def _setup_structured_logging(self):
        """Setup structured logging with structlog"""
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
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Create main logger
        self.main_logger = structlog.get_logger(self.service_name)
    
    def _setup_outputs(self):
        """Setup log outputs"""
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
    
    def _setup_file_handlers(self):
        """Setup file handlers for different log types"""
        # Application logs
        app_handler = logging.FileHandler(
            self.logs_dir / "application.log",
            encoding='utf-8'
        )
        app_handler.setLevel(logging.DEBUG)
        
        # Error logs
        error_handler = logging.FileHandler(
            self.logs_dir / "errors.log",
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # Audit logs
        audit_handler = logging.FileHandler(
            self.logs_dir / "audit.log",
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        
        # Performance logs
        perf_handler = logging.FileHandler(
            self.logs_dir / "performance.log",
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        
        # Configure formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    
    def _setup_console_handler(self):
        """Setup console handler with colored output"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level.value)
        
        # Colored formatter for development
        if self.environment == "development":
            formatter = logging.Formatter(
                '\033[92m%(asctime)s\033[0m - \033[94m%(name)s\033[0m - '
                '\033[93m%(levelname)s\033[0m - %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
    
    def _setup_datadog(self):
        """Setup Datadog integration"""
        try:
            initialize(
                api_key=os.getenv('DATADOG_API_KEY'),
                app_key=os.getenv('DATADOG_APP_KEY')
            )
            self.datadog_enabled = True
        except Exception as e:
            print(f"Failed to initialize Datadog: {e}")
            self.datadog_enabled = False
    
    def _setup_tracing(self):
        """Setup distributed tracing"""
        try:
            # Create tracer provider
            trace.set_tracer_provider(TracerProvider())
            tracer_provider = trace.get_tracer_provider()
            
            # Setup Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv('JAEGER_AGENT_HOST', 'localhost'),
                agent_port=int(os.getenv('JAEGER_AGENT_PORT', '14268')),
            )
            
            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
        except Exception as e:
            print(f"Failed to setup tracing: {e}")
            self.tracer = None
    
    def _setup_metrics(self):
        """Setup metrics collection"""
        self.metrics_enabled = LogOutput.DATADOG in self.outputs
    
    # ========================================================================
    # Logging Methods
    # ========================================================================
    
    def get_logger(self, name: str) -> structlog.BoundLogger:
        """Get a structured logger"""
        return structlog.get_logger(name)
    
    async def log_structured(
        self,
        level: LogLevel,
        message: str,
        logger_name: str = None,
        **kwargs
    ):
        """Log structured message"""
        logger_name = logger_name or self.service_name
        
        # Create log entry
        log_entry = LogEntry(
            level=level,
            logger_name=logger_name,
            message=message,
            service_name=self.service_name,
            environment=self.environment,
            extra_data=kwargs
        )
        
        # Add system information
        log_entry.hostname = os.getenv('HOSTNAME')
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
        exception: Exception = None,
        logger_name: str = None,
        **kwargs
    ):
        """Log error with exception details"""
        extra_data = kwargs.copy()
        
        if exception:
            extra_data.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'stack_trace': traceback.format_exc()
            })
        
        await self.log_structured(
            LogLevel.ERROR,
            message,
            logger_name,
            **extra_data
        )
    
    async def log_performance(
        self,
        operation: str,
        duration_ms: float,
        logger_name: str = None,
        **kwargs
    ):
        """Log performance metrics"""
        # Store performance metric
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = []
        
        self.performance_metrics[operation].append(duration_ms)
        
        # Keep only last 1000 measurements
        if len(self.performance_metrics[operation]) > 1000:
            self.performance_metrics[operation] = self.performance_metrics[operation][-1000:]
        
        await self.log_structured(
            LogLevel.INFO,
            f"Performance: {operation}",
            logger_name,
            operation=operation,
            duration_ms=duration_ms,
            **kwargs
        )
        
        # Send metric to Datadog
        if self.metrics_enabled:
            await self._send_metric(
                f"performance.{operation}",
                MetricType.TIMER,
                duration_ms,
                tags={"operation": operation}
            )
    
    async def log_audit(
        self,
        event_type: str,
        action: str,
        result: str,
        user_id: str = None,
        resource: str = None,
        **kwargs
    ):
        """Log audit event"""
        audit_entry = AuditEntry(
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            details=kwargs
        )
        
        self.audit_logs.append(audit_entry)
        
        # Log to audit logger
        audit_logger = self.get_logger("audit")
        audit_logger.info(
            f"Audit: {event_type} - {action} - {result}",
            event_type=event_type,
            action=action,
            result=result,
            user_id=user_id,
            resource=resource,
            **kwargs
        )
    
    # ========================================================================
    # Metrics Methods
    # ========================================================================
    
    async def _send_metric(
        self,
        metric_name: str,
        metric_type: MetricType,
        value: Union[int, float],
        tags: Dict[str, str] = None
    ):
        """Send metric to external service"""
        if not self.metrics_enabled:
            return
        
        try:
            metric_tags = tags or {}
            metric_tags.update({
                'service': self.service_name,
                'environment': self.environment
            })
            
            if metric_type == MetricType.COUNTER:
                statsd.increment(metric_name, value, tags=list(metric_tags.items()))
            elif metric_type == MetricType.GAUGE:
                statsd.gauge(metric_name, value, tags=list(metric_tags.items()))
            elif metric_type == MetricType.HISTOGRAM:
                statsd.histogram(metric_name, value, tags=list(metric_tags.items()))
            elif metric_type == MetricType.TIMER:
                statsd.timing(metric_name, value, tags=list(metric_tags.items()))
                
        except Exception as e:
            print(f"Failed to send metric: {e}")
    
    async def increment_counter(
        self,
        metric_name: str,
        value: int = 1,
        tags: Dict[str, str] = None
    ):
        """Increment a counter metric"""
        await self._send_metric(metric_name, MetricType.COUNTER, value, tags)
    
    async def set_gauge(
        self,
        metric_name: str,
        value: Union[int, float],
        tags: Dict[str, str] = None
    ):
        """Set a gauge metric"""
        await self._send_metric(metric_name, MetricType.GAUGE, value, tags)
    
    async def record_histogram(
        self,
        metric_name: str,
        value: Union[int, float],
        tags: Dict[str, str] = None
    ):
        """Record a histogram metric"""
        await self._send_metric(metric_name, MetricType.HISTOGRAM, value, tags)
    
    async def record_timing(
        self,
        metric_name: str,
        duration_ms: float,
        tags: Dict[str, str] = None
    ):
        """Record a timing metric"""
        await self._send_metric(metric_name, MetricType.TIMER, duration_ms, tags)
    
    # ========================================================================
    # Tracing Methods
    # ========================================================================
    
    def start_span(self, name: str, **kwargs):
        """Start a new span"""
        if self.tracer:
            return self.tracer.start_span(name, **kwargs)
        return None
    
    def add_span_attribute(self, span, key: str, value: Any):
        """Add attribute to span"""
        if span:
            span.set_attribute(key, value)
    
    def add_span_event(self, span, name: str, attributes: Dict[str, Any] = None):
        """Add event to span"""
        if span:
            span.add_event(name, attributes or {})
    
    # ========================================================================
    # Context Managers and Decorators
    # ========================================================================
    
    def trace_operation(self, operation_name: str):
        """Decorator to trace an operation"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
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
                    
                except Exception as e:
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
    
    async def _send_to_datadog(self, log_entry: LogEntry):
        """Send log entry to Datadog"""
        if not self.datadog_enabled:
            return
        
        try:
            # Convert log entry to Datadog format
            datadog_log = {
                'timestamp': log_entry.timestamp.isoformat(),
                'level': log_entry.level.value,
                'message': log_entry.message,
                'service': log_entry.service_name,
                'env': log_entry.environment,
                'logger': log_entry.logger_name,
                'hostname': log_entry.hostname,
                'process_id': log_entry.process_id,
                'thread_id': log_entry.thread_id,
                'request_id': log_entry.request_id,
                'user_id': log_entry.user_id,
                'session_id': log_entry.session_id,
                'correlation_id': log_entry.correlation_id,
                'duration_ms': log_entry.duration_ms,
                'memory_usage_mb': log_entry.memory_usage_mb,
                'cpu_usage_percent': log_entry.cpu_usage_percent,
                'error_code': log_entry.error_code,
                'stack_trace': log_entry.stack_trace,
                'extra_data': log_entry.extra_data
            }
            
            # Send to Datadog (implementation depends on Datadog client)
            # This is a placeholder - actual implementation would use Datadog client
            
        except Exception as e:
            print(f"Failed to send log to Datadog: {e}")
    
    # ========================================================================
    # Analysis and Reporting
    # ========================================================================
    
    async def get_performance_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if operation:
            if operation not in self.performance_metrics:
                return {}
            
            values = self.performance_metrics[operation]
            return {
                'operation': operation,
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'p50': sorted(values)[len(values) // 2],
                'p95': sorted(values)[int(len(values) * 0.95)],
                'p99': sorted(values)[int(len(values) * 0.99)]
            }
        else:
            # Return stats for all operations
            stats = {}
            for op, values in self.performance_metrics.items():
                stats[op] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'p50': sorted(values)[len(values) // 2],
                    'p95': sorted(values)[int(len(values) * 0.95)],
                    'p99': sorted(values)[int(len(values) * 0.99)]
                }
            return stats
    
    async def get_audit_logs(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: str = None,
        user_id: str = None
    ) -> List[AuditEntry]:
        """Get filtered audit logs"""
        filtered_logs = self.audit_logs
        
        if start_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_date]
        
        if end_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]
        
        if event_type:
            filtered_logs = [log for log in filtered_logs if log.event_type == event_type]
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)
    
    async def generate_log_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive log report"""
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
        
        report = {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {
                'total_audit_events': len(audit_logs),
                'unique_users': len(user_activity),
                'unique_resources': len(resource_access),
                'tracked_operations': len(performance_stats)
            },
            'event_breakdown': event_counts,
            'top_users': dict(sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_resources': dict(sorted(resource_access.items(), key=lambda x: x[1], reverse=True)[:10]),
            'performance_summary': performance_stats
        }
        
        return report


# ========================================================================
# FastAPI Integration
# ========================================================================

class FastAPILoggingMiddleware:
    """FastAPI middleware for request logging"""
    
    def __init__(self, logging_framework: LoggingFramework):
        self.logging_framework = logging_framework
    
    async def __call__(self, request, call_next):
        start_time = time.time()
        
        # Extract request information
        request_id = request.headers.get('X-Request-ID', f"req_{int(time.time())}")
        user_id = getattr(request.state, 'user_id', None)
        
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
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get('User-Agent')
            )
            
            # Add span attributes
            if span:
                self.logging_framework.add_span_attribute(span, "http.method", request.method)
                self.logging_framework.add_span_attribute(span, "http.url", str(request.url))
                self.logging_framework.add_span_attribute(span, "http.user_agent", request.headers.get('User-Agent'))
                self.logging_framework.add_span_attribute(span, "request_id", request_id)
            
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
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else None
            )
            
            # Add span attributes
            if span:
                self.logging_framework.add_span_attribute(span, "http.status_code", response.status_code)
                self.logging_framework.add_span_attribute(span, "duration_ms", duration_ms)
            
            # Record performance metric
            await self.logging_framework.record_timing(
                f"http.request.duration",
                duration_ms,
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            await self.logging_framework.log_error(
                f"Request failed: {request.method} {request.url.path}",
                e,
                logger_name="http",
                request_id=request_id,
                user_id=user_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms
            )
            
            # Add span attributes
            if span:
                self.logging_framework.add_span_attribute(span, "error", str(e))
                self.logging_framework.add_span_attribute(span, "duration_ms", duration_ms)
            
            raise
            
        finally:
            if span:
                span.end()


if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize logging framework
        logging_framework = LoggingFramework(
            service_name="pake-system",
            environment="development",
            outputs=[LogOutput.CONSOLE, LogOutput.FILE]
        )
        
        # Get logger
        logger = logging_framework.get_logger("example")
        
        # Log structured message
        await logging_framework.log_structured(
            LogLevel.INFO,
            "Application started",
            extra_data={"version": "1.0.0", "build": "123"}
        )
        
        # Log performance
        await logging_framework.log_performance("database_query", 150.5)
        
        # Log audit event
        await logging_framework.log_audit(
            "user_login",
            "authenticate",
            "success",
            user_id="user123",
            resource="/api/auth/login"
        )
        
        # Generate report
        report = await logging_framework.generate_log_report()
        print(f"Log report: {report['summary']}")
    
    asyncio.run(main())
