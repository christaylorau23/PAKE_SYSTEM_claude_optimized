#!/usr/bin/env python3
"""Metrics Collection for PAKE System
Prometheus-compatible metrics for observability
"""

import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import psutil

try:
    from .logger import get_logger

    logger = get_logger("metrics")
except ImportError:
    import logging

    logger = logging.getLogger("metrics")


@dataclass
class MetricValue:
    """Container for metric values with metadata"""

    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsStore:
    """Thread-safe metrics storage with Prometheus export capability"""

    def __init__(self, service_name: str = "pake-system"):
        self.service_name = service_name
        self.start_time = time.time()
        self._lock = threading.RLock()

        # Metric collections
        self._counters: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int),
        )
        self._gauges: dict[str, dict[str, float]] = defaultdict(dict)
        self._histograms: dict[str, dict[str, dict]] = defaultdict(
            lambda: defaultdict(
                lambda: {"buckets": defaultdict(int), "sum": 0.0, "count": 0},
            ),
        )

        # HTTP-specific metrics
        self.http_requests = defaultdict(int)  # method:path:status -> count
        self.http_duration = defaultdict(
            lambda: {"sum": 0, "count": 0, "buckets": defaultdict(int)},
        )
        self.http_requests_total = 0
        self.http_errors = 0

        # System metrics cache
        self._last_system_update = 0
        self._system_metrics = {}

        logger.info("Metrics store initialized", service=service_name)

    def _get_label_key(self, labels: dict[str, str]) -> str:
        """Convert labels dict to string key"""
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def increment_counter(
        self,
        name: str,
        labels: dict[str, str] = None,
        value: int = 1,
    ):
        """Increment a counter metric"""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        with self._lock:
            self._counters[name][label_key] += value

        logger.debug("Counter incremented", metric=name, value=value, labels=labels)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] = None):
        """Set a gauge metric value"""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        with self._lock:
            self._gauges[name][label_key] = value

        logger.debug("Gauge set", metric=name, value=value, labels=labels)

    def record_histogram(
        self,
        name: str,
        value: float,
        buckets: list[float] = None,
        labels: dict[str, str] = None,
    ):
        """Record a histogram value"""
        labels = labels or {}
        labels["service"] = self.service_name
        label_key = self._get_label_key(labels)

        # Default histogram buckets (in seconds for duration, adjust as needed)
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

        with self._lock:
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

        logger.debug("Histogram recorded", metric=name, value=value, labels=labels)

    def record_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
    ):
        """Record HTTP request metrics"""
        normalized_path = self._normalize_path(path)
        key = f"{method}:{normalized_path}:{status_code}"
        duration_key = f"{method}:{normalized_path}"

        with self._lock:
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
            "HTTP request recorded",
            method=method,
            path=normalized_path,
            status_code=status_code,
            duration=duration,
        )

    def _normalize_path(self, path: str) -> str:
        """Normalize API paths for metrics (remove IDs, etc.)"""
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
        normalized = re.sub(r"\?.*", "", normalized)
        return normalized

    def update_system_metrics(self):
        """Update system-level metrics"""
        now = time.time()
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

            # Update gauge metrics
            for metric_name, value in self._system_metrics.items():
                self.set_gauge(f"system_{metric_name}", value)

        except Exception as e:
            logger.error("Failed to update system metrics", error=e)

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus format metrics"""
        self.update_system_metrics()
        lines = []

        with self._lock:
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

    def get_json_metrics(self) -> dict[str, Any]:
        """Get metrics in JSON format"""
        self.update_system_metrics()

        with self._lock:
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


# Global metrics store
_metrics_store = None


def get_metrics_store(service_name: str = "pake-system") -> MetricsStore:
    """Get or create global metrics store"""
    global _metrics_store
    if _metrics_store is None:
        _metrics_store = MetricsStore(service_name)
    return _metrics_store


# Convenience functions


def increment_counter(name: str, value: int = 1, labels: dict[str, str] = None):
    """Increment a counter metric"""
    get_metrics_store().increment_counter(name, value, labels)


def set_gauge(name: str, value: float, labels: dict[str, str] = None):
    """Set a gauge metric"""
    get_metrics_store().set_gauge(name, value, labels)


def record_histogram(name: str, value: float, labels: dict[str, str] = None):
    """Record a histogram value"""
    get_metrics_store().record_histogram(name, value, labels=labels)


def record_http_request(method: str, path: str, status_code: int, duration: float):
    """Record HTTP request metrics"""
    get_metrics_store().record_http_request(method, path, status_code, duration)


# Context managers and decorators


class timer:
    """Context manager for timing operations"""

    def __init__(self, metric_name: str, labels: dict[str, str] = None):
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_histogram(self.metric_name, duration, self.labels)


def timed(metric_name: str, labels: dict[str, str] = None):
    """Decorator to time function execution"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with timer(metric_name, labels):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# FastAPI/Starlette middleware


def create_metrics_middleware():
    """Create metrics middleware for FastAPI/Starlette"""
    try:
        import time

        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class MetricsMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, metrics_store: MetricsStore = None):
                super().__init__(app)
                self.metrics_store = metrics_store or get_metrics_store()

            async def dispatch(self, request: Request, call_next):
                start_time = time.time()

                try:
                    response = await call_next(request)
                    duration = time.time() - start_time

                    # Record metrics
                    self.metrics_store.record_http_request(
                        request.method,
                        str(request.url.path),
                        response.status_code,
                        duration,
                    )

                    return response

                except Exception:
                    duration = time.time() - start_time
                    self.metrics_store.record_http_request(
                        request.method,
                        str(request.url.path),
                        500,  # Internal server error
                        duration,
                    )
                    raise

        return MetricsMiddleware

    except ImportError:
        # Return no-op middleware if starlette is not available
        class NoOpMetricsMiddleware:
            def __init__(self, app, metrics_store=None):
                pass

        return NoOpMetricsMiddleware


# Health check function


def get_health_status() -> dict[str, Any]:
    """Get service health status with key metrics"""
    metrics_store = get_metrics_store()
    metrics = metrics_store.get_json_metrics()

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

    # Initialize metrics
    store = get_metrics_store("test-service")

    # Record some example metrics
    increment_counter("test_counter", 5, {"type": "example"})
    set_gauge("test_gauge", 42.0, {"type": "example"})

    with timer("test_operation"):
        time.sleep(0.1)

    # Record HTTP request
    record_http_request("GET", "/api/test", 200, 0.05)

    # Print metrics
    print("Prometheus format:")
    print(store.get_prometheus_metrics())

    print("\nJSON format:")
    import json

    print(json.dumps(store.get_json_metrics(), indent=2))

    print("\nHealth status:")
    print(json.dumps(get_health_status(), indent=2))
