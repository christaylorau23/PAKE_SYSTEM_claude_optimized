#!/usr/bin/env python3
"""Async-Safe Metrics Collection for PAKE System
Thread-safe and async-safe metrics for observability with race condition protection.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
import threading
import time
from typing import Any

import psutil

try:
    from .logger import get_logger

    logger = get_logger("async_metrics")
except ImportError:
    import logging

    logger = logging.getLogger("async_metrics")


@dataclass
class AsyncMetricValue:
    """Container for async metric values with metadata."""

    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AsyncMetricsStore:
    """Async-safe metrics storage with Prometheus export capability and race condition protection."""

    def __init__(self, service_name: str | None = None) -> None:
        self.service_name = service_name
        self.start_time = time.time()

        # Async-safe locks for different operations
        self._async_lock = asyncio.Lock()
        self._thread_lock = threading.RLock()  # For sync operations

        # Metric collections with async-safe access
        self._counters: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int),
        )
        self._gauges: dict[str, dict[str, float]] = defaultdict(dict)
        self._histograms: dict[str, dict[str, dict]] = defaultdict(
            lambda: defaultdict(
                lambda: {"buckets": defaultdict(int), "sum": 0.0, "count": 0},
            ),
        )

        # HTTP-specific metrics with async protection
        self.http_requests = defaultdict(int)  # method:path:status -> count
        self.http_duration = defaultdict(
            lambda: {"sum": 0, "count": 0, "buckets": defaultdict(int)},
        )
        self.http_requests_total = 0
        self.http_errors = 0

        # System metrics cache with async protection
        self._last_system_update = 0
        self._system_metrics = {}
        self._system_update_lock = asyncio.Lock()

        logger.info("Async metrics store initialized for service: %s", service_name)

    def _get_label_key(self, labels: dict[str, str]) -> str:
        """Convert labels dict to string key."""
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    async def increment_counter_async(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric (async-safe)."""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        async with self._async_lock:
            self._counters[name][label_key] += value

        logger.debug(
            "Counter incremented (async): %s = %s, labels: %s", name, value, labels
        )

    def increment_counter_sync(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric (sync-safe)."""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        with self._thread_lock:
            self._counters[name][label_key] += value

        logger.debug(
            "Counter incremented (sync)", metric=name, value=value, labels=labels
        )

    async def set_gauge_async(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric value (async-safe)."""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        async with self._async_lock:
            self._gauges[name][label_key] = value

        logger.debug("Gauge set (async)", metric=name, value=value, labels=labels)

    def set_gauge_sync(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric value (sync-safe)."""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        with self._thread_lock:
            self._gauges[name][label_key] = value

        logger.debug("Gauge set (sync)", metric=name, value=value, labels=labels)

    async def record_histogram_async(self, name: str, value: float, labels: dict[str, str] | None = None, buckets: list[float] | None = None) -> None:
        """Record a histogram value (async-safe)."""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        # Default histogram buckets (in seconds for duration, adjust as needed)
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

        async with self._async_lock:
            hist_data = self._histograms[name][label_key]
            hist_data["sum"] += value
            hist_data["count"] += 1

            # Initialize buckets if not exists
            if not hist_data["buckets"]:
                for bucket in buckets:
                    hist_data["buckets"][bucket] = 0

            # Update buckets
            for bucket in buckets:
                if value <= bucket:
                    hist_data["buckets"][bucket] += 1

        logger.debug(
            "Histogram recorded (async)", metric=name, value=value, labels=labels
        )

    def record_histogram_sync(self, name: str, value: float, labels: dict[str, str] | None = None, buckets: list[float] | None = None) -> None:
        """Record a histogram value (sync-safe)."""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        # Default histogram buckets (in seconds for duration, adjust as needed)
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

        with self._thread_lock:
            hist_data = self._histograms[name][label_key]
            hist_data["sum"] += value
            hist_data["count"] += 1

            # Initialize buckets if not exists
            if not hist_data["buckets"]:
                for bucket in buckets:
                    hist_data["buckets"][bucket] = 0

            # Update buckets
            for bucket in buckets:
                if value <= bucket:
                    hist_data["buckets"][bucket] += 1

        logger.debug(
            "Histogram recorded (sync)", metric=name, value=value, labels=labels
        )

    async def record_http_request_async(self, method: str, path: str, status_code: int, duration: float | None = None) -> None:
        """Record HTTP request metrics (async-safe)."""
        normalized_path = self._normalize_path(path)
        key = f"{method}:{normalized_path}:{status_code}"
        duration_key = f"{method}:{normalized_path}"

        async with self._async_lock:
            self.http_requests[key] += 1
            self.http_requests_total += 1

            if status_code >= 400:
                self.http_errors += 1

            # Record duration histogram
            hist_data = self.http_duration[duration_key]
            hist_data["sum"] += duration
            hist_data["count"] += 1

            # Duration buckets (in seconds)
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            for bucket in buckets:
                if duration <= bucket:
                    hist_data["buckets"][bucket] += 1

        logger.debug(
            "HTTP request recorded (async)",
            method=method,
            path=normalized_path,
            status_code=status_code,
            duration=duration,
        )

    def record_http_request_sync(self, method: str, path: str, status_code: int, duration: float | None = None) -> None:
        """Record HTTP request metrics (sync-safe)."""
        normalized_path = self._normalize_path(path)
        key = f"{method}:{normalized_path}:{status_code}"
        duration_key = f"{method}:{normalized_path}"

        with self._thread_lock:
            self.http_requests[key] += 1
            self.http_requests_total += 1

            if status_code >= 400:
                self.http_errors += 1

            # Record duration histogram
            hist_data = self.http_duration[duration_key]
            hist_data["sum"] += duration
            hist_data["count"] += 1

            # Duration buckets (in seconds)
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            for bucket in buckets:
                if duration <= bucket:
                    hist_data["buckets"][bucket] += 1

        logger.debug(
            "HTTP request recorded (sync)",
            method=method,
            path=normalized_path,
            status_code=status_code,
            duration=duration,
        )

    def _normalize_path(self, path: str) -> str:
        """Normalize API paths for metrics (remove IDs, etc.)."""
        import re

        normalized = path
        # Replace UUIDs
        normalized = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/:uuid",
            normalized,
        )
        # Replace numeric IDs
        normalized = re.sub(r"/\d+", "/:id", normalized)
        # Replace query parameters
        return re.sub(r"\?.*", "", normalized)

    async def update_system_metrics_async(self) -> None:
        """Update system-level metrics (async-safe)."""
        now = time.time()

        # Use async lock to prevent concurrent system metric updates
        async with self._system_update_lock:
            if now - self._last_system_update < 5.0:  # Update every 5 seconds
                return

            try:
                # Process metrics
                process = psutil.Process()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()

                # System metrics
                system_memory = psutil.virtual_memory()
                system_cpu = psutil.cpu_percent()
                disk_usage = psutil.disk_usage("/")

                self._system_metrics = {
                    "process_memory_rss": memory_info.rss,
                    "process_memory_vms": memory_info.vms,
                    "process_cpu_percent": cpu_percent,
                    "system_memory_total": system_memory.total,
                    "system_memory_available": system_memory.available,
                    "system_memory_percent": system_memory.percent,
                    "system_cpu_percent": system_cpu,
                    "disk_usage_total": disk_usage.total,
                    "disk_usage_used": disk_usage.used,
                    "disk_usage_percent": (disk_usage.used / disk_usage.total) * 100,
                    "uptime_seconds": now - self.start_time,
                }

                self._last_system_update = now

                # Update gauge metrics (async-safe)
                for metric_name, value in self._system_metrics.items():
                    await self.set_gauge_async(f"system_{metric_name}", value)

            except (ValueError, RuntimeError) as e:
                logger.error("Failed to update system metrics (async)", error=e)

    def update_system_metrics_sync(self) -> None:
        """Update system-level metrics (sync-safe)."""
        now = time.time()

        with self._thread_lock:
            if now - self._last_system_update < 5.0:  # Update every 5 seconds
                return

            try:
                # Process metrics
                process = psutil.Process()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()

                # System metrics
                system_memory = psutil.virtual_memory()
                system_cpu = psutil.cpu_percent()
                disk_usage = psutil.disk_usage("/")

                self._system_metrics = {
                    "process_memory_rss": memory_info.rss,
                    "process_memory_vms": memory_info.vms,
                    "process_cpu_percent": cpu_percent,
                    "system_memory_total": system_memory.total,
                    "system_memory_available": system_memory.available,
                    "system_memory_percent": system_memory.percent,
                    "system_cpu_percent": system_cpu,
                    "disk_usage_total": disk_usage.total,
                    "disk_usage_used": disk_usage.used,
                    "disk_usage_percent": (disk_usage.used / disk_usage.total) * 100,
                    "uptime_seconds": now - self.start_time,
                }

                self._last_system_update = now

                # Update gauge metrics (sync-safe)
                for metric_name, value in self._system_metrics.items():
                    self.set_gauge_sync(f"system_{metric_name}", value)

            except (ValueError, RuntimeError) as e:
                logger.error("Failed to update system metrics (sync)", error=e)

    async def get_prometheus_metrics_async(self) -> str:
        """Generate Prometheus format metrics (async-safe)."""
        await self.update_system_metrics_async()
        lines = []

        async with self._async_lock:
            # Counters
            for name, label_data in self._counters.items():
                lines.append(f"# HELP {name} Counter metric")
                lines.append(f"# TYPE {name} counter")
                for label_key, value in label_data.items():
                    labels_str = (
                        f"{ {{label_key}} }"
                        if label_key
                        else '{service="' + self.service_name + '"}'
                    )
                    lines.append(f"{name}{labels_str} {value}")
                lines.append("")

            # Gauges
            for name, label_data in self._gauges.items():
                lines.append(f"# HELP {name} Gauge metric")
                lines.append(f"# TYPE {name} gauge")
                for label_key, value in label_data.items():
                    labels_str = (
                        f"{ {{label_key}} }"
                        if label_key
                        else '{service="' + self.service_name + '"}'
                    )
                    lines.append(f"{name}{labels_str} {value}")
                lines.append("")

            # Histograms
            for name, label_data in self._histograms.items():
                lines.append(f"# HELP {name} Histogram metric")
                lines.append(f"# TYPE {name} histogram")
                for label_key, hist_data in label_data.items():
                    base_labels = (
                        label_key if label_key else f'service="{self.service_name}"'
                    )

                    # Buckets
                    for bucket, count in sorted(hist_data["buckets"].items()):
                        bucket_labels = (
                            base_labels + f',le="{bucket}"'
                            if base_labels
                            else f'le="{bucket}",service="{self.service_name}"'
                        )
                        lines.append(f"{name}_bucket{{{bucket_labels}}} {count}")

                    # +Inf bucket
                    inf_labels = (
                        base_labels + ',le="+Inf"'
                        if base_labels
                        else f'le="+Inf",service="{self.service_name}"'
                    )
                    lines.append(f"{name}_bucket{{{inf_labels}}} {hist_data['count']}")

                    # Sum and count
                    sum_labels = (
                        f"{ {{base_labels}} }"
                        if base_labels
                        else '{service="' + self.service_name + '"}'
                    )
                    lines.append(f"{name}_sum{sum_labels} {hist_data['sum']}")
                    lines.append(f"{name}_count{sum_labels} {hist_data['count']}")
                lines.append("")

            # HTTP-specific metrics
            if self.http_requests:
                lines.append("# HELP http_requests_total Total number of HTTP requests")
                lines.append("# TYPE http_requests_total counter")
                for key, count in self.http_requests.items():
                    method, path, status = key.split(":", 2)
                    lines.append(
                        f'http_requests_total{{method="{method}",path="{path}",status="{
                            status
                        }",service="{self.service_name}"}} {count}',
                    )
                lines.append("")

            if self.http_duration:
                lines.append(
                    "# HELP http_request_duration_seconds HTTP request duration in seconds",
                )
                lines.append("# TYPE http_request_duration_seconds histogram")
                for key, data in self.http_duration.items():
                    method, path = key.split(":", 1)
                    base_labels = (
                        f'method="{method}",path="{path}",service="{self.service_name}"'
                    )

                    # Buckets
                    for bucket, count in sorted(data["buckets"].items()):
                        lines.append(
                            f'http_request_duration_seconds_bucket{{{base_labels},le="{bucket}"}} {count}',
                        )

                    # +Inf bucket
                    lines.append(
                        f'http_request_duration_seconds_bucket{{{
                            base_labels
                        },le="+Inf"}} {data["count"]}',
                    )

                    # Sum and count
                    lines.append(
                        f"http_request_duration_seconds_sum{{{base_labels}}} {
                            data['sum']
                        }",
                    )
                    lines.append(
                        f"http_request_duration_seconds_count{{{base_labels}}} {
                            data['count']
                        }",
                    )
                lines.append("")

            # Error rate
            if self.http_requests_total > 0:
                error_rate = self.http_errors / self.http_requests_total
                lines.append("# HELP http_requests_error_rate HTTP request error rate")
                lines.append("# TYPE http_requests_error_rate gauge")
                lines.append(
                    f'http_requests_error_rate{{service="{self.service_name}"}} {
                        error_rate:.4f}',
                )
                lines.append("")

        return "\n".join(lines)

    def get_prometheus_metrics_sync(self) -> str:
        """Generate Prometheus format metrics (sync-safe)."""
        self.update_system_metrics_sync()
        lines = []

        with self._thread_lock:
            # Counters
            for name, label_data in self._counters.items():
                lines.append(f"# HELP {name} Counter metric")
                lines.append(f"# TYPE {name} counter")
                for label_key, value in label_data.items():
                    labels_str = (
                        f"{ {{label_key}} }"
                        if label_key
                        else '{service="' + self.service_name + '"}'
                    )
                    lines.append(f"{name}{labels_str} {value}")
                lines.append("")

            # Gauges
            for name, label_data in self._gauges.items():
                lines.append(f"# HELP {name} Gauge metric")
                lines.append(f"# TYPE {name} gauge")
                for label_key, value in label_data.items():
                    labels_str = (
                        f"{ {{label_key}} }"
                        if label_key
                        else '{service="' + self.service_name + '"}'
                    )
                    lines.append(f"{name}{labels_str} {value}")
                lines.append("")

            # Histograms
            for name, label_data in self._histograms.items():
                lines.append(f"# HELP {name} Histogram metric")
                lines.append(f"# TYPE {name} histogram")
                for label_key, hist_data in label_data.items():
                    base_labels = (
                        label_key if label_key else f'service="{self.service_name}"'
                    )

                    # Buckets
                    for bucket, count in sorted(hist_data["buckets"].items()):
                        bucket_labels = (
                            base_labels + f',le="{bucket}"'
                            if base_labels
                            else f'le="{bucket}",service="{self.service_name}"'
                        )
                        lines.append(f"{name}_bucket{{{bucket_labels}}} {count}")

                    # +Inf bucket
                    inf_labels = (
                        base_labels + ',le="+Inf"'
                        if base_labels
                        else f'le="+Inf",service="{self.service_name}"'
                    )
                    lines.append(f"{name}_bucket{{{inf_labels}}} {hist_data['count']}")

                    # Sum and count
                    sum_labels = (
                        f"{ {{base_labels}} }"
                        if base_labels
                        else '{service="' + self.service_name + '"}'
                    )
                    lines.append(f"{name}_sum{sum_labels} {hist_data['sum']}")
                    lines.append(f"{name}_count{sum_labels} {hist_data['count']}")
                lines.append("")

            # HTTP-specific metrics
            if self.http_requests:
                lines.append("# HELP http_requests_total Total number of HTTP requests")
                lines.append("# TYPE http_requests_total counter")
                for key, count in self.http_requests.items():
                    method, path, status = key.split(":", 2)
                    lines.append(
                        f'http_requests_total{{method="{method}",path="{path}",status="{
                            status
                        }",service="{self.service_name}"}} {count}',
                    )
                lines.append("")

            if self.http_duration:
                lines.append(
                    "# HELP http_request_duration_seconds HTTP request duration in seconds",
                )
                lines.append("# TYPE http_request_duration_seconds histogram")
                for key, data in self.http_duration.items():
                    method, path = key.split(":", 1)
                    base_labels = (
                        f'method="{method}",path="{path}",service="{self.service_name}"'
                    )

                    # Buckets
                    for bucket, count in sorted(data["buckets"].items()):
                        lines.append(
                            f'http_request_duration_seconds_bucket{{{base_labels},le="{bucket}"}} {count}',
                        )

                    # +Inf bucket
                    lines.append(
                        f'http_request_duration_seconds_bucket{{{
                            base_labels
                        },le="+Inf"}} {data["count"]}',
                    )

                    # Sum and count
                    lines.append(
                        f"http_request_duration_seconds_sum{{{base_labels}}} {
                            data['sum']
                        }",
                    )
                    lines.append(
                        f"http_request_duration_seconds_count{{{base_labels}}} {
                            data['count']
                        }",
                    )
                lines.append("")

            # Error rate
            if self.http_requests_total > 0:
                error_rate = self.http_errors / self.http_requests_total
                lines.append("# HELP http_requests_error_rate HTTP request error rate")
                lines.append("# TYPE http_requests_error_rate gauge")
                lines.append(
                    f'http_requests_error_rate{{service="{self.service_name}"}} {
                        error_rate:.4f}',
                )
                lines.append("")

        return "\n".join(lines)

    async def get_json_metrics_async(self) -> dict[str, Any]:
        """Get metrics in JSON format (async-safe)."""
        await self.update_system_metrics_async()

        async with self._async_lock:
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "service": self.service_name,
                "uptime_seconds": time.time() - self.start_time,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": dict(self._histograms),
                "http": {
                    "requests": dict(self.http_requests),
                    "duration": dict(self.http_duration),
                    "total_requests": self.http_requests_total,
                    "total_errors": self.http_errors,
                    "error_rate": (
                        self.http_errors / self.http_requests_total
                        if self.http_requests_total > 0
                        else 0
                    ),
                },
                "system": self._system_metrics,
            }

    def get_json_metrics_sync(self) -> dict[str, Any]:
        """Get metrics in JSON format (sync-safe)."""
        self.update_system_metrics_sync()

        with self._thread_lock:
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "service": self.service_name,
                "uptime_seconds": time.time() - self.start_time,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": dict(self._histograms),
                "http": {
                    "requests": dict(self.http_requests),
                    "duration": dict(self.http_duration),
                    "total_requests": self.http_requests_total,
                    "total_errors": self.http_errors,
                    "error_rate": (
                        self.http_errors / self.http_requests_total
                        if self.http_requests_total > 0
                        else 0
                    ),
                },
                "system": self._system_metrics,
            }


# Global async metrics store
_async_metrics_store = None


def get_async_metrics_store(service_name: str = "pake-system") -> AsyncMetricsStore:
    """Get or create global async metrics store."""
    global _async_metrics_store
    if _async_metrics_store is None:
        _async_metrics_store = AsyncMetricsStore(service_name)
    return _async_metrics_store


# Convenience functions for async operations


async def increment_counter_async(name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
    """Increment a counter metric (async-safe)."""
    await get_async_metrics_store().increment_counter_async(name, value, labels)


def increment_counter_sync(name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
    """Increment a counter metric (sync-safe)."""
    get_async_metrics_store().increment_counter_sync(name, value, labels)


async def set_gauge_async(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Set a gauge metric (async-safe)."""
    await get_async_metrics_store().set_gauge_async(name, value, labels)


def set_gauge_sync(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Set a gauge metric (sync-safe)."""
    get_async_metrics_store().set_gauge_sync(name, value, labels)


async def record_histogram_async(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Record a histogram value (async-safe)."""
    await get_async_metrics_store().record_histogram_async(name, value, labels=labels)


def record_histogram_sync(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Record a histogram value (sync-safe)."""
    get_async_metrics_store().record_histogram_sync(name, value, labels=labels)


async def record_http_request_async(method: str, path: str, status_code: int, duration: float | None = None) -> None:
    """Record HTTP request metrics (async-safe)."""
    await get_async_metrics_store().record_http_request_async(
        method, path, status_code, duration
    )


def record_http_request_sync(method: str, path: str, status_code: int, duration: float | None = None) -> None:
    """Record HTTP request metrics (sync-safe)."""
    get_async_metrics_store().record_http_request_sync(
        method, path, status_code, duration
    )


# Async context managers and decorators


class async_timer:
    """Async context manager for timing operations."""

    def __init__(self, metric_name: str, labels: dict[str, str] | None = None) -> None:
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None

    async def __aenter__(self) -> None:
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time:
            duration = time.time() - self.start_time
            await record_histogram_async(self.metric_name, duration, self.labels)


def async_timed(metric_name: str, labels: dict[str, str] | None = None) -> Callable:
    """Decorator to time async function execution."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with async_timer(metric_name, labels):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


# Health check functions


async def get_health_status_async() -> dict[str, Any]:
    """Get service health status with key metrics (async-safe)."""
    metrics_store = get_async_metrics_store()
    metrics = await metrics_store.get_json_metrics_async()

    # Determine health status
    status = "healthy"
    warnings = []

    # Check memory usage
    if metrics["system"].get("system_memory_percent", 0) > 90:
        status = "degraded"
        warnings.append("High system memory usage")

    if metrics["system"].get("process_cpu_percent", 0) > 80:
        status = "degraded"
        warnings.append("High CPU usage")

    # Check error rate
    error_rate = metrics["http"].get("error_rate", 0)
    if error_rate > 0.1:  # 10% error rate
        status = "degraded"
        warnings.append(f"High error rate: {error_rate:.2%}")

    return {
        "status": status,
        "timestamp": metrics["timestamp"],
        "uptime": metrics["uptime_seconds"],
        "service": metrics["service"],
        "version": os.getenv("PAKE_VERSION", "1.0.0"),
        "warnings": warnings,
        "metrics": {
            "total_requests": metrics["http"]["total_requests"],
            "error_rate": error_rate,
            "memory_usage_mb": round(
                metrics["system"].get("process_memory_rss", 0) / 1024 / 1024,
            ),
            "cpu_percent": round(metrics["system"].get("process_cpu_percent", 0), 2),
        },
    }


def get_health_status_sync() -> dict[str, Any]:
    """Get service health status with key metrics (sync-safe)."""
    metrics_store = get_async_metrics_store()
    metrics = metrics_store.get_json_metrics_sync()

    # Determine health status
    status = "healthy"
    warnings = []

    # Check memory usage
    if metrics["system"].get("system_memory_percent", 0) > 90:
        status = "degraded"
        warnings.append("High system memory usage")

    if metrics["system"].get("process_cpu_percent", 0) > 80:
        status = "degraded"
        warnings.append("High CPU usage")

    # Check error rate
    error_rate = metrics["http"].get("error_rate", 0)
    if error_rate > 0.1:  # 10% error rate
        status = "degraded"
        warnings.append(f"High error rate: {error_rate:.2%}")

    return {
        "status": status,
        "timestamp": metrics["timestamp"],
        "uptime": metrics["uptime_seconds"],
        "service": metrics["service"],
        "version": os.getenv("PAKE_VERSION", "1.0.0"),
        "warnings": warnings,
        "metrics": {
            "total_requests": metrics["http"]["total_requests"],
            "error_rate": error_rate,
            "memory_usage_mb": round(
                metrics["system"].get("process_memory_rss", 0) / 1024 / 1024,
            ),
            "cpu_percent": round(metrics["system"].get("process_cpu_percent", 0), 2),
        },
    }


if __name__ == "__main__":
    # Example usage

    async def example_async_usage() -> None:
        # Initialize async metrics
        store = get_async_metrics_store("test-async-service")

        # Record some example metrics (async-safe)
        await increment_counter_async("test_counter", 5, {"type": "example"})
        await set_gauge_async("test_gauge", 42.0, {"type": "example"})

        async with async_timer("test_async_operation"):
            await asyncio.sleep(0.1)

        # Record HTTP request (async-safe)
        await record_http_request_async("GET", "/api/test", 200, 0.05)

        # Print metrics
        print("Prometheus format (async):")
        print(await store.get_prometheus_metrics_async())

        print("\nJSON format (async):")
        import json

        print(json.dumps(await store.get_json_metrics_async(), indent=2))

        print("\nHealth status (async):")
        print(json.dumps(await get_health_status_async(), indent=2))

    # Run async example
    asyncio.run(example_async_usage())

    # Sync example
    store = get_async_metrics_store("test-sync-service")
    increment_counter_sync("test_counter", 3, {"type": "sync_example"})
    set_gauge_sync("test_gauge", 24.0, {"type": "sync_example"})

    print("\nHealth status (sync):")
    import json

    print(json.dumps(get_health_status_sync(), indent=2))