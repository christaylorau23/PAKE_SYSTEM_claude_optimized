#!/usr/bin/env python3
"""PAKE System - OpenTelemetry Observability Framework
Comprehensive observability solution for hierarchical event-driven architecture.

Implements:
- Distributed tracing across Supervisor and Worker agents
- Metrics collection and monitoring
- Structured logging with correlation
- Performance analytics and alerting
- Integration with Prometheus and Grafana
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# OpenTelemetry imports
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode

# Configure logging
logger = logging.getLogger(__name__)


class ObservabilityLevel(Enum):
    """Observability detail levels"""

    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"


class MetricType(Enum):
    """Types of metrics"""

    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    UP_DOWN_COUNTER = "up_down_counter"


@dataclass
class TelemetryConfig:
    """Configuration for telemetry system"""

    service_name: str = "pake-system"
    service_version: str = "2.0.0"
    environment: str = "development"

    # Tracing configuration
    enable_tracing: bool = True
    trace_endpoint: str | None = None  # OTLP endpoint
    trace_sampling_ratio: float = 1.0
    enable_console_traces: bool = True

    # Metrics configuration
    enable_metrics: bool = True
    metrics_endpoint: str | None = None  # OTLP endpoint
    prometheus_port: int = 8000
    metrics_interval: float = 30.0
    enable_console_metrics: bool = True

    # Logging configuration
    enable_structured_logging: bool = True
    log_level: str = "INFO"
    enable_trace_correlation: bool = True

    # Feature flags
    observability_level: ObservabilityLevel = ObservabilityLevel.STANDARD
    enable_redis_instrumentation: bool = True
    enable_asyncio_instrumentation: bool = True
    enable_custom_metrics: bool = True


class TelemetrySystem:
    """Centralized telemetry system for PAKE observability"""

    def __init__(self, config: TelemetryConfig = None):
        self.config = config or TelemetryConfig()

        # OpenTelemetry components
        self.tracer_provider = None
        self.meter_provider = None
        self.tracer = None
        self.meter = None

        # Custom metrics
        self.custom_metrics: dict[str, Any] = {}
        self.metric_callbacks: dict[str, Callable] = {}

        # Performance tracking
        self.operation_timings: dict[str, list[float]] = {}
        self.error_counts: dict[str, int] = {}
        self.request_counts: dict[str, int] = {}

        # Background tasks
        self._background_tasks: list[asyncio.Task] = []
        self._running = False

        logger.info(f"TelemetrySystem initialized for {self.config.service_name}")

    async def initialize(self):
        """Initialize telemetry system"""
        if self._running:
            return

        logger.info("Initializing OpenTelemetry observability framework...")

        try:
            # Create resource
            resource = Resource.create(
                {
                    SERVICE_NAME: self.config.service_name,
                    SERVICE_VERSION: self.config.service_version,
                    "environment": self.config.environment,
                    "component": "hierarchical-ai-system",
                },
            )

            # Initialize tracing
            if self.config.enable_tracing:
                try:
                    await self._setup_tracing(resource)
                except Exception as e:
                    logger.warning(
                        f"Failed to setup tracing: {e}. Continuing without tracing.",
                    )

            # Initialize metrics
            if self.config.enable_metrics:
                try:
                    await self._setup_metrics(resource)
                except Exception as e:
                    logger.warning(
                        f"Failed to setup metrics: {e}. Continuing without metrics.",
                    )

            # Setup instrumentation
            try:
                await self._setup_instrumentation()
            except Exception as e:
                logger.warning(
                    f"Failed to setup instrumentation: {e}. Continuing without instrumentation.",
                )

            # Setup structured logging
            if self.config.enable_structured_logging:
                try:
                    await self._setup_structured_logging()
                except Exception as e:
                    logger.warning(
                        f"Failed to setup structured logging: {e}. Continuing without structured logging.",
                    )

            # Start background tasks
            try:
                self._background_tasks = [
                    asyncio.create_task(self._metrics_collection_loop()),
                    asyncio.create_task(self._health_monitoring_loop()),
                ]
            except Exception as e:
                logger.warning(
                    f"Failed to start background tasks: {e}. Continuing without background tasks.",
                )
                self._background_tasks = []

            self._running = True
            logger.info(
                "OpenTelemetry observability framework initialized successfully",
            )

        except Exception as e:
            logger.error(f"Failed to initialize telemetry system: {e}")
            logger.info(
                "Continuing without telemetry - system will operate with reduced observability",
            )
            self._running = False

    async def shutdown(self):
        """Shutdown telemetry system"""
        if not self._running:
            return

        logger.info("Shutting down observability framework...")

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Flush exporters
        if self.tracer_provider:
            self.tracer_provider.force_flush(timeout_millis=5000)

        if self.meter_provider:
            self.meter_provider.force_flush(timeout_millis=5000)

        self._running = False
        logger.info("Observability framework shutdown complete")

    async def _setup_tracing(self, resource: Resource):
        """Setup distributed tracing"""
        self.tracer_provider = TracerProvider(resource=resource)

        # Add exporters
        exporters = []

        if self.config.enable_console_traces:
            exporters.append(ConsoleSpanExporter())

        if self.config.trace_endpoint:
            exporters.append(OTLPSpanExporter(endpoint=self.config.trace_endpoint))

        # Add span processors
        for exporter in exporters:
            processor = BatchSpanProcessor(exporter)
            self.tracer_provider.add_span_processor(processor)

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(__name__, version=self.config.service_version)

        logger.info("Distributed tracing initialized")

    async def _setup_metrics(self, resource: Resource):
        """Setup metrics collection"""
        readers = []

        # Console metrics reader
        if self.config.enable_console_metrics:
            console_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=int(self.config.metrics_interval * 1000),
            )
            readers.append(console_reader)

        # OTLP metrics reader
        if self.config.metrics_endpoint:
            otlp_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=self.config.metrics_endpoint),
                export_interval_millis=int(self.config.metrics_interval * 1000),
            )
            readers.append(otlp_reader)

        # Prometheus metrics reader
        try:
            prometheus_reader = PrometheusMetricReader(port=self.config.prometheus_port)
            readers.append(prometheus_reader)
            logger.info(
                f"Prometheus metrics available at http://localhost:{self.config.prometheus_port}/metrics",
            )
        except Exception as e:
            logger.warning(f"Failed to setup Prometheus reader: {e}")

        # Create meter provider
        self.meter_provider = MeterProvider(resource=resource, metric_readers=readers)

        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)

        # Get meter
        self.meter = metrics.get_meter(__name__, version=self.config.service_version)

        # Initialize custom metrics
        await self._setup_custom_metrics()

        logger.info("Metrics collection initialized")

    async def _setup_custom_metrics(self):
        """Setup custom application metrics"""
        if not self.config.enable_custom_metrics or not self.meter:
            return

        # Task execution metrics
        self.custom_metrics["task_duration"] = self.meter.create_histogram(
            name="pake_task_duration_seconds",
            description="Duration of task execution in seconds",
            unit="s",
        )

        self.custom_metrics["task_counter"] = self.meter.create_counter(
            name="pake_tasks_total",
            description="Total number of tasks processed",
            unit="1",
        )

        self.custom_metrics["error_counter"] = self.meter.create_counter(
            name="pake_errors_total",
            description="Total number of errors encountered",
            unit="1",
        )

        # Agent metrics
        self.custom_metrics["active_agents"] = self.meter.create_up_down_counter(
            name="pake_active_agents",
            description="Number of active agents",
            unit="1",
        )

        self.custom_metrics["message_counter"] = self.meter.create_counter(
            name="pake_messages_total",
            description="Total number of messages processed",
            unit="1",
        )

        # Cache metrics
        self.custom_metrics["cache_hits"] = self.meter.create_counter(
            name="pake_cache_hits_total",
            description="Total cache hits",
            unit="1",
        )

        self.custom_metrics["cache_misses"] = self.meter.create_counter(
            name="pake_cache_misses_total",
            description="Total cache misses",
            unit="1",
        )

        # Quality metrics
        self.custom_metrics["content_quality"] = self.meter.create_histogram(
            name="pake_content_quality_score",
            description="Content quality scores",
            unit="1",
        )

        # System resource metrics (using callbacks)
        self.meter.create_observable_gauge(
            name="pake_system_cpu_usage",
            description="System CPU usage percentage",
            unit="%",
            callbacks=[self._get_cpu_usage],
        )

        self.meter.create_observable_gauge(
            name="pake_system_memory_usage",
            description="System memory usage percentage",
            unit="%",
            callbacks=[self._get_memory_usage],
        )

        logger.info("Custom metrics initialized")

    async def _setup_instrumentation(self):
        """Setup automatic instrumentation"""
        if self.config.enable_redis_instrumentation:
            try:
                RedisInstrumentor().instrument()
                logger.info("Redis instrumentation enabled")
            except Exception as e:
                logger.warning(f"Failed to instrument Redis: {e}")

        if self.config.enable_asyncio_instrumentation:
            try:
                AsyncioInstrumentor().instrument()
                logger.info("Asyncio instrumentation enabled")
            except Exception as e:
                logger.warning(f"Failed to instrument asyncio: {e}")

    async def _setup_structured_logging(self):
        """Setup structured logging with trace correlation"""
        # Configure logging format
        log_format = {
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "service": self.config.service_name,
            "logger": "%(name)s",
            "message": "%(message)s",
        }

        if self.config.enable_trace_correlation:
            # Add trace correlation fields
            log_format.update({"trace_id": "%(trace_id)s", "span_id": "%(span_id)s"})

        # Create custom formatter
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                # Add trace context if available
                if hasattr(record, "trace_id"):
                    span = trace.get_current_span()
                    if span and span.is_recording():
                        span_context = span.get_span_context()
                        record.trace_id = format(span_context.trace_id, "032x")
                        record.span_id = format(span_context.span_id, "016x")
                    else:
                        record.trace_id = ""
                        record.span_id = ""

                # Create structured log entry
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "service": self.config.service_name,
                    "logger": record.name,
                    "message": record.getMessage(),
                }

                if hasattr(record, "trace_id") and record.trace_id:
                    log_entry["trace_id"] = record.trace_id
                    log_entry["span_id"] = record.span_id

                return json.dumps(log_entry)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level))

        # Add structured handler
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(handler)

        logger.info("Structured logging initialized")

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        attributes: dict[str, Any] = None,
        span_kind: SpanKind = SpanKind.INTERNAL,
    ):
        """Context manager for tracing operations"""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            operation_name,
            kind=span_kind,
            attributes=attributes or {},
        ) as span:
            start_time = time.time()

            try:
                yield span

                # Record success
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                # Record error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)

                # Update error metrics
                if "error_counter" in self.custom_metrics:
                    self.custom_metrics["error_counter"].add(
                        1,
                        {"operation": operation_name, "error_type": type(e).__name__},
                    )

                raise

            finally:
                # Record timing
                duration = time.time() - start_time

                if "task_duration" in self.custom_metrics:
                    self.custom_metrics["task_duration"].record(
                        duration,
                        {"operation": operation_name},
                    )

                # Track operation timings
                if operation_name not in self.operation_timings:
                    self.operation_timings[operation_name] = []

                self.operation_timings[operation_name].append(duration)

                # Keep only recent timings
                if len(self.operation_timings[operation_name]) > 1000:
                    self.operation_timings[operation_name] = self.operation_timings[
                        operation_name
                    ][-1000:]

    @asynccontextmanager
    async def trace_async_operation(
        self,
        operation_name: str,
        attributes: dict[str, Any] = None,
        span_kind: SpanKind = SpanKind.INTERNAL,
    ):
        """Async context manager for tracing operations"""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            operation_name,
            kind=span_kind,
            attributes=attributes or {},
        ) as span:
            start_time = time.time()

            try:
                yield span

                # Record success
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                # Record error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)

                # Update error metrics
                if "error_counter" in self.custom_metrics:
                    self.custom_metrics["error_counter"].add(
                        1,
                        {"operation": operation_name, "error_type": type(e).__name__},
                    )

                raise

            finally:
                # Record timing
                duration = time.time() - start_time

                if "task_duration" in self.custom_metrics:
                    self.custom_metrics["task_duration"].record(
                        duration,
                        {"operation": operation_name},
                    )

    def record_metric(
        self,
        metric_name: str,
        value: float,
        attributes: dict[str, str] = None,
        metric_type: MetricType = MetricType.COUNTER,
    ):
        """Record a custom metric"""
        if metric_name not in self.custom_metrics:
            logger.warning(f"Metric {metric_name} not found in custom metrics")
            return

        metric = self.custom_metrics[metric_name]
        attrs = attributes or {}

        if metric_type == MetricType.COUNTER:
            metric.add(value, attrs)
        elif metric_type == MetricType.HISTOGRAM:
            metric.record(value, attrs)
        elif metric_type == MetricType.UP_DOWN_COUNTER:
            metric.add(value, attrs)

    def record_task_execution(
        self,
        task_type: str,
        duration: float,
        success: bool = True,
        agent_id: str = None,
    ):
        """Record task execution metrics"""
        attributes = {"task_type": task_type}
        if agent_id:
            attributes["agent_id"] = agent_id

        # Record duration
        if "task_duration" in self.custom_metrics:
            self.custom_metrics["task_duration"].record(duration, attributes)

        # Record count
        if "task_counter" in self.custom_metrics:
            attributes["status"] = "success" if success else "error"
            self.custom_metrics["task_counter"].add(1, attributes)

        # Record error if failed
        if not success and "error_counter" in self.custom_metrics:
            self.custom_metrics["error_counter"].add(1, attributes)

    def record_message_processing(
        self,
        message_type: str,
        agent_type: str,
        success: bool = True,
    ):
        """Record message processing metrics"""
        if "message_counter" in self.custom_metrics:
            attributes = {
                "message_type": message_type,
                "agent_type": agent_type,
                "status": "success" if success else "error",
            }
            self.custom_metrics["message_counter"].add(1, attributes)

    def record_cache_operation(self, hit: bool, cache_level: str = "unknown"):
        """Record cache operation metrics"""
        attributes = {"cache_level": cache_level}

        if hit and "cache_hits" in self.custom_metrics:
            self.custom_metrics["cache_hits"].add(1, attributes)
        elif not hit and "cache_misses" in self.custom_metrics:
            self.custom_metrics["cache_misses"].add(1, attributes)

    def record_content_quality(
        self,
        quality_score: float,
        source_type: str = "unknown",
    ):
        """Record content quality metrics"""
        if "content_quality" in self.custom_metrics:
            attributes = {"source_type": source_type}
            self.custom_metrics["content_quality"].record(quality_score, attributes)

    def update_active_agents(self, count: int, agent_type: str = "all"):
        """Update active agents count"""
        if "active_agents" in self.custom_metrics:
            attributes = {"agent_type": agent_type}
            # This is a gauge, so we set the absolute value
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.set_attribute("active_agents_count", count)

    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        logger.info("Starting metrics collection loop")

        while self._running:
            try:
                # Collect and emit custom metrics
                await self._collect_performance_metrics()
                await self._collect_system_metrics()

                await asyncio.sleep(self.config.metrics_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(5)

        logger.info("Metrics collection loop stopped")

    async def _health_monitoring_loop(self):
        """Background health monitoring loop"""
        logger.info("Starting health monitoring loop")

        while self._running:
            try:
                # Check system health and emit alerts if needed
                health_status = await self._check_system_health()

                if not health_status["healthy"]:
                    logger.warning(f"System health degraded: {health_status}")

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(10)

        logger.info("Health monitoring loop stopped")

    async def _collect_performance_metrics(self):
        """Collect performance metrics"""
        # Calculate and emit operation timing statistics
        for operation, timings in self.operation_timings.items():
            if timings:
                avg_time = sum(timings) / len(timings)
                max_time = max(timings)
                min_time = min(timings)

                # Log performance statistics
                logger.debug(
                    f"Operation {operation}: avg={avg_time:.3f}s, max={
                        max_time:.3f}s, min={min_time:.3f}s",
                )

    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            import psutil

            # CPU and memory metrics are collected via callbacks
            # Additional system metrics can be added here

        except ImportError:
            logger.warning("psutil not available for system metrics")

    async def _check_system_health(self) -> dict[str, Any]:
        """Check overall system health"""
        health_status = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Check error rates
        total_operations = sum(
            len(timings) for timings in self.operation_timings.values()
        )
        total_errors = sum(self.error_counts.values())

        if total_operations > 0:
            error_rate = total_errors / total_operations
            health_status["checks"]["error_rate"] = {
                "status": "healthy" if error_rate < 0.05 else "unhealthy",
                "value": error_rate,
                "threshold": 0.05,
            }

            if error_rate >= 0.05:
                health_status["healthy"] = False

        # Check response times
        slow_operations = []
        for operation, timings in self.operation_timings.items():
            if timings:
                avg_time = sum(timings[-10:]) / min(len(timings), 10)  # Recent average
                if avg_time > 30.0:  # 30 second threshold
                    slow_operations.append(operation)

        health_status["checks"]["response_times"] = {
            "status": "healthy" if not slow_operations else "unhealthy",
            "slow_operations": slow_operations,
        }

        if slow_operations:
            health_status["healthy"] = False

        return health_status

    def _get_cpu_usage(self, options: CallbackOptions) -> list[Observation]:
        """Callback for CPU usage metric"""
        try:
            import psutil

            cpu_usage = psutil.cpu_percent(interval=None)
            return [Observation(cpu_usage)]
        except ImportError:
            return [Observation(0.0)]

    def _get_memory_usage(self, options: CallbackOptions) -> list[Observation]:
        """Callback for memory usage metric"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            return [Observation(memory.percent)]
        except ImportError:
            return [Observation(0.0)]

    def get_telemetry_summary(self) -> dict[str, Any]:
        """Get telemetry system summary"""
        return {
            "service": self.config.service_name,
            "version": self.config.service_version,
            "environment": self.config.environment,
            "tracing_enabled": self.config.enable_tracing,
            "metrics_enabled": self.config.enable_metrics,
            "custom_metrics_count": len(self.custom_metrics),
            "operations_tracked": len(self.operation_timings),
            "total_operations": sum(
                len(timings) for timings in self.operation_timings.values()
            ),
            "running": self._running,
        }


# Global telemetry instance
_telemetry_instance = None


def get_telemetry() -> TelemetrySystem:
    """Get global telemetry instance"""
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = TelemetrySystem()
    return _telemetry_instance


def initialize_telemetry(config: TelemetryConfig = None) -> TelemetrySystem:
    """Initialize global telemetry system"""
    global _telemetry_instance
    _telemetry_instance = TelemetrySystem(config)
    return _telemetry_instance


async def setup_observability(config: TelemetryConfig = None) -> TelemetrySystem:
    """Setup and initialize observability system"""
    telemetry = initialize_telemetry(config)
    await telemetry.initialize()
    return telemetry


# Convenience decorators
def trace_function(operation_name: str = None, attributes: dict[str, Any] = None):
    """Decorator for tracing functions"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__qualname__}"
            telemetry = get_telemetry()

            async with telemetry.trace_async_operation(name, attributes):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__qualname__}"
            telemetry = get_telemetry()

            with telemetry.trace_operation(name, attributes):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def record_execution_time(
    metric_name: str = "execution_time",
    attributes: dict[str, str] = None,
):
    """Decorator for recording execution time"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                telemetry.record_metric(
                    metric_name,
                    duration,
                    attributes,
                    MetricType.HISTOGRAM,
                )
                return result
            except Exception:
                duration = time.time() - start_time
                error_attrs = {**(attributes or {}), "status": "error"}
                telemetry.record_metric(
                    metric_name,
                    duration,
                    error_attrs,
                    MetricType.HISTOGRAM,
                )
                raise

        def sync_wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                telemetry.record_metric(
                    metric_name,
                    duration,
                    attributes,
                    MetricType.HISTOGRAM,
                )
                return result
            except Exception:
                duration = time.time() - start_time
                error_attrs = {**(attributes or {}), "status": "error"}
                telemetry.record_metric(
                    metric_name,
                    duration,
                    error_attrs,
                    MetricType.HISTOGRAM,
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Configuration presets
def create_development_config() -> TelemetryConfig:
    """Create development telemetry configuration"""
    return TelemetryConfig(
        environment="development",
        observability_level=ObservabilityLevel.DEBUG,
        enable_console_traces=True,
        enable_console_metrics=True,
        trace_sampling_ratio=1.0,
        metrics_interval=10.0,
        log_level="DEBUG",
    )


def create_production_config(
    trace_endpoint: str = None,
    metrics_endpoint: str = None,
) -> TelemetryConfig:
    """Create production telemetry configuration"""
    return TelemetryConfig(
        environment="production",
        observability_level=ObservabilityLevel.STANDARD,
        enable_console_traces=False,
        enable_console_metrics=False,
        trace_endpoint=trace_endpoint,
        metrics_endpoint=metrics_endpoint,
        trace_sampling_ratio=0.1,  # Sample 10% in production
        metrics_interval=60.0,
        log_level="INFO",
    )


def create_testing_config() -> TelemetryConfig:
    """Create testing telemetry configuration"""
    return TelemetryConfig(
        environment="testing",
        observability_level=ObservabilityLevel.MINIMAL,
        enable_console_traces=False,
        enable_console_metrics=False,
        enable_metrics=False,  # Disable metrics in tests
        trace_sampling_ratio=0.0,  # No tracing in tests
        log_level="WARNING",
    )
