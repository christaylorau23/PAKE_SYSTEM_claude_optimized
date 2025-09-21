"""APIHealthMonitor - Monitors API health and performance

Tracks response times, error rates, and availability for all external APIs.
"""

import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    """API health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"


@dataclass
class HealthMetric:
    """Individual health metric data point"""

    timestamp: float
    response_time_ms: float
    success: bool
    error_message: str | None = None
    status_code: int | None = None


@dataclass
class APIHealthSummary:
    """Summary of API health metrics"""

    api_name: str
    status: HealthStatus
    success_rate: float
    average_response_time_ms: float
    p95_response_time_ms: float
    error_count_1h: int
    total_requests_1h: int
    last_success: datetime | None
    last_failure: datetime | None
    uptime_percentage: float
    health_score: float  # 0.0 to 1.0


class APIHealthMonitor:
    """Comprehensive API health monitoring system

    Features:
    - Real-time health tracking
    - Performance metrics collection
    - Automated alerting thresholds
    - Circuit breaker integration
    - Health score calculation
    """

    def __init__(self, max_history_hours: int = 24):
        self.logger = logging.getLogger(__name__)
        self.max_history_hours = max_history_hours
        self.max_history_seconds = max_history_hours * 3600

        # Health metrics storage
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        # Health thresholds
        self.thresholds = {
            "response_time_warning_ms": 5000,
            "response_time_critical_ms": 10000,
            "success_rate_warning": 0.95,
            "success_rate_critical": 0.85,
            "error_rate_warning": 0.05,
            "error_rate_critical": 0.15,
        }

        # Circuit breaker states
        self.circuit_breakers: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure_time": None,
                "recovery_timeout": 60,  # seconds
            },
        )

        # Monitored APIs
        self.apis = ["google_trends", "youtube", "twitter", "tiktok"]

    async def record_request(
        self,
        api_name: str,
        response_time_ms: float,
        success: bool,
        error_message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Record a request result for health monitoring"""
        metric = HealthMetric(
            timestamp=time.time(),
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
            status_code=status_code,
        )

        self.metrics[api_name].append(metric)

        # Update circuit breaker
        await self._update_circuit_breaker(api_name, success)

        # Clean old metrics
        await self._clean_old_metrics(api_name)

        self.logger.debug(
            f"Recorded {api_name} request: {response_time_ms:.1f}ms, success={success}",
        )

    async def _update_circuit_breaker(self, api_name: str, success: bool) -> None:
        """Update circuit breaker state based on request result"""
        breaker = self.circuit_breakers[api_name]

        if success:
            if breaker["state"] == "half_open":
                # Success in half-open state - close circuit
                breaker["state"] = "closed"
                breaker["failure_count"] = 0
                self.logger.info(
                    f"Circuit breaker for {api_name} closed after successful recovery",
                )
            elif breaker["state"] == "closed":
                # Reset failure count on success
                breaker["failure_count"] = 0

        else:
            breaker["failure_count"] += 1
            breaker["last_failure_time"] = time.time()

            if breaker["state"] == "closed" and breaker["failure_count"] >= 5:
                # Open circuit after 5 consecutive failures
                breaker["state"] = "open"
                self.logger.warning(
                    f"Circuit breaker for {api_name} opened after {breaker['failure_count']} failures",
                )

            elif breaker["state"] == "half_open":
                # Failure in half-open state - back to open
                breaker["state"] = "open"
                self.logger.warning(
                    f"Circuit breaker for {api_name} back to open state",
                )

    async def _clean_old_metrics(self, api_name: str) -> None:
        """Remove metrics older than max_history_hours"""
        cutoff_time = time.time() - self.max_history_seconds
        metrics = self.metrics[api_name]

        while metrics and metrics[0].timestamp < cutoff_time:
            metrics.popleft()

    async def get_health_summary(self, api_name: str) -> APIHealthSummary:
        """Get comprehensive health summary for an API"""
        metrics = self.metrics[api_name]

        if not metrics:
            return APIHealthSummary(
                api_name=api_name,
                status=HealthStatus.DOWN,
                success_rate=0.0,
                average_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                error_count_1h=0,
                total_requests_1h=0,
                last_success=None,
                last_failure=None,
                uptime_percentage=0.0,
                health_score=0.0,
            )

        # Calculate time windows
        now = time.time()
        hour_ago = now - 3600

        # Filter metrics for last hour
        recent_metrics = [m for m in metrics if m.timestamp > hour_ago]

        if not recent_metrics:
            # No recent metrics - use all available
            recent_metrics = list(metrics)

        # Calculate success rate
        successful_requests = sum(1 for m in recent_metrics if m.success)
        total_requests = len(recent_metrics)
        success_rate = (
            successful_requests / total_requests if total_requests > 0 else 0.0
        )

        # Calculate response times
        response_times = [m.response_time_ms for m in recent_metrics if m.success]
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        p95_response_time = (
            statistics.quantiles(response_times, n=20)[18]
            if len(response_times) >= 20
            else avg_response_time
        )

        # Count errors
        error_count = sum(1 for m in recent_metrics if not m.success)

        # Find last success/failure
        last_success = None
        last_failure = None

        for metric in reversed(metrics):
            if metric.success and last_success is None:
                last_success = datetime.fromtimestamp(metric.timestamp)
            if not metric.success and last_failure is None:
                last_failure = datetime.fromtimestamp(metric.timestamp)

            if last_success and last_failure:
                break

        # Calculate uptime percentage (last 24 hours)
        day_ago = now - 86400
        day_metrics = [m for m in metrics if m.timestamp > day_ago]
        day_successful = sum(1 for m in day_metrics if m.success)
        uptime_percentage = (
            (day_successful / len(day_metrics)) * 100 if day_metrics else 0.0
        )

        # Determine status and health score
        status, health_score = self._calculate_health_status(
            success_rate,
            avg_response_time,
            error_count,
            total_requests,
        )

        return APIHealthSummary(
            api_name=api_name,
            status=status,
            success_rate=success_rate,
            average_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            error_count_1h=error_count,
            total_requests_1h=total_requests,
            last_success=last_success,
            last_failure=last_failure,
            uptime_percentage=uptime_percentage,
            health_score=health_score,
        )

    def _calculate_health_status(
        self,
        success_rate: float,
        avg_response_time: float,
        error_count: int,
        total_requests: int,
    ) -> tuple[HealthStatus, float]:
        """Calculate health status and score"""
        # Calculate component scores (0.0 to 1.0)
        success_score = success_rate
        response_time_score = max(
            0.0,
            1.0 - (avg_response_time / self.thresholds["response_time_critical_ms"]),
        )
        error_rate = error_count / total_requests if total_requests > 0 else 0.0
        error_score = max(
            0.0,
            1.0 - (error_rate / self.thresholds["error_rate_critical"]),
        )

        # Weighted health score
        health_score = (
            success_score * 0.4 + response_time_score * 0.3 + error_score * 0.3
        )

        # Determine status
        if (
            health_score >= 0.9
            and success_rate >= self.thresholds["success_rate_warning"]
        ):
            status = HealthStatus.HEALTHY
        elif (
            health_score >= 0.7
            and success_rate >= self.thresholds["success_rate_critical"]
        ):
            status = HealthStatus.DEGRADED
        elif health_score >= 0.3:
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.DOWN

        return status, health_score

    async def get_all_health_summaries(self) -> dict[str, APIHealthSummary]:
        """Get health summaries for all monitored APIs"""
        summaries = {}
        for api_name in self.apis:
            summaries[api_name] = await self.get_health_summary(api_name)
        return summaries

    async def check_circuit_breaker(self, api_name: str) -> bool:
        """Check if API is available (circuit breaker closed)"""
        breaker = self.circuit_breakers[api_name]

        if breaker["state"] == "closed":
            return True

        if breaker["state"] == "open":
            # Check if recovery timeout has passed
            if (time.time() - breaker["last_failure_time"]) > breaker[
                "recovery_timeout"
            ]:
                breaker["state"] = "half_open"
                self.logger.info(
                    f"Circuit breaker for {api_name} moved to half-open state",
                )
                return True
            return False

        if breaker["state"] == "half_open":
            return True

        return False

    async def get_circuit_breaker_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers"""
        status = {}
        for api_name in self.apis:
            breaker = self.circuit_breakers[api_name]
            status[api_name] = {
                "state": breaker["state"],
                "failure_count": breaker["failure_count"],
                "last_failure_time": (
                    datetime.fromtimestamp(breaker["last_failure_time"])
                    if breaker["last_failure_time"]
                    else None
                ),
                "is_available": await self.check_circuit_breaker(api_name),
            }
        return status

    async def get_performance_metrics(
        self,
        api_name: str,
        hours: int = 1,
    ) -> dict[str, Any]:
        """Get detailed performance metrics for an API"""
        metrics = self.metrics[api_name]
        cutoff_time = time.time() - (hours * 3600)
        filtered_metrics = [m for m in metrics if m.timestamp > cutoff_time]

        if not filtered_metrics:
            return {"error": "No metrics available for specified time period"}

        # Response time statistics
        response_times = [m.response_time_ms for m in filtered_metrics if m.success]
        error_response_times = [
            m.response_time_ms for m in filtered_metrics if not m.success
        ]

        response_time_stats = {}
        if response_times:
            response_time_stats = {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": (
                    statistics.quantiles(response_times, n=20)[18]
                    if len(response_times) >= 20
                    else max(response_times)
                ),
                "p99": (
                    statistics.quantiles(response_times, n=100)[98]
                    if len(response_times) >= 100
                    else max(response_times)
                ),
            }

        # Error analysis
        errors_by_type = defaultdict(int)
        for metric in filtered_metrics:
            if not metric.success and metric.error_message:
                errors_by_type[metric.error_message] += 1

        # Throughput calculation
        time_span_hours = hours
        throughput_per_hour = len(filtered_metrics) / time_span_hours

        return {
            "time_period_hours": hours,
            "total_requests": len(filtered_metrics),
            "successful_requests": len([m for m in filtered_metrics if m.success]),
            "failed_requests": len([m for m in filtered_metrics if not m.success]),
            "success_rate": len([m for m in filtered_metrics if m.success])
            / len(filtered_metrics),
            "throughput_per_hour": throughput_per_hour,
            "response_time_stats": response_time_stats,
            "error_response_times": {
                "count": len(error_response_times),
                "average": (
                    statistics.mean(error_response_times) if error_response_times else 0
                ),
            },
            "errors_by_type": dict(errors_by_type),
            "health_score": (await self.get_health_summary(api_name)).health_score,
        }

    async def generate_health_report(self) -> str:
        """Generate comprehensive health report"""
        summaries = await self.get_all_health_summaries()
        circuit_status = await self.get_circuit_breaker_status()

        report = "API HEALTH REPORT\n"
        report += "=" * 50 + "\n\n"

        for api_name, summary in summaries.items():
            status_emoji = {
                HealthStatus.HEALTHY: "🟢",
                HealthStatus.DEGRADED: "🟡",
                HealthStatus.UNHEALTHY: "🟠",
                HealthStatus.DOWN: "🔴",
            }

            report += f"{status_emoji[summary.status]} {api_name.upper()}\n"
            report += f"  Status: {summary.status.value}\n"
            report += f"  Health Score: {summary.health_score:.2f}/1.0\n"
            report += f"  Success Rate: {summary.success_rate:.1%}\n"
            report += f"  Avg Response: {summary.average_response_time_ms:.1f}ms\n"
            report += (
                f"  Errors (1h): {summary.error_count_1h}/{summary.total_requests_1h}\n"
            )
            report += f"  Uptime (24h): {summary.uptime_percentage:.1f}%\n"

            # Circuit breaker status
            breaker = circuit_status[api_name]
            report += f"  Circuit Breaker: {breaker['state']}\n"

            if summary.last_failure:
                time_since_failure = datetime.now() - summary.last_failure
                report += f"  Last Failure: {time_since_failure} ago\n"

            report += "\n"

        # Overall system health
        overall_health = statistics.mean([s.health_score for s in summaries.values()])
        report += f"OVERALL SYSTEM HEALTH: {overall_health:.2f}/1.0\n"

        return report

    async def set_thresholds(self, **kwargs) -> None:
        """Update health monitoring thresholds"""
        for key, value in kwargs.items():
            if key in self.thresholds:
                self.thresholds[key] = value
                self.logger.info(f"Updated threshold {key} to {value}")

    async def reset_circuit_breaker(self, api_name: str) -> bool:
        """Manually reset circuit breaker for an API"""
        if api_name in self.circuit_breakers:
            self.circuit_breakers[api_name] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "recovery_timeout": 60,
            }
            self.logger.info(f"Circuit breaker for {api_name} manually reset")
            return True
        return False
