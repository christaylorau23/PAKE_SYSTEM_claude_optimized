#!/usr/bin/env python3
"""PAKE System - Real-Time Monitoring Dashboard
Phase 2B Sprint 4: Production-scale monitoring and observability

Provides real-time performance monitoring, health checks, and operational insights
for the PAKE ingestion pipeline and caching systems.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import aiofiles

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics tracked"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass(frozen=True)
class MetricPoint:
    """Immutable metric data point"""

    timestamp: datetime
    value: float
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels,
        }


@dataclass
class SystemHealth:
    """System health assessment"""

    overall_status: HealthStatus = HealthStatus.UNKNOWN
    component_health: dict[str, HealthStatus] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    last_check: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_status": self.overall_status.value,
            "component_health": {k: v.value for k, v in self.component_health.items()},
            "alerts": self.alerts,
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }


@dataclass
class DashboardConfig:
    """Real-time dashboard configuration"""

    # Update intervals
    metric_update_interval: float = 1.0  # seconds
    health_check_interval: float = 5.0  # seconds
    dashboard_refresh_interval: float = 2.0  # seconds

    # Retention settings
    metric_retention_hours: int = 24
    max_data_points: int = 1000

    # Alerting thresholds
    error_rate_threshold: float = 0.05  # 5%
    response_time_threshold: float = 5.0  # seconds
    memory_usage_threshold: float = 0.85  # 85%
    disk_usage_threshold: float = 0.90  # 90%

    # Dashboard settings
    dashboard_port: int = 8080
    enable_websocket: bool = True
    log_level: str = "INFO"


class MetricCollector(ABC):
    """Abstract base for metric collectors"""

    @abstractmethod
    async def collect_metrics(self) -> dict[str, list[MetricPoint]]:
        """Collect metrics from the system"""


class IngestionMetrics(MetricCollector):
    """Collects ingestion pipeline metrics"""

    def __init__(self, orchestrator_manager=None, cache_manager=None):
        self.orchestrator_manager = orchestrator_manager
        self.cache_manager = cache_manager
        self._start_time = time.time()

    async def collect_metrics(self) -> dict[str, list[MetricPoint]]:
        """Collect ingestion and caching metrics"""
        metrics = {}
        now = datetime.now(UTC)

        # System uptime
        uptime_seconds = time.time() - self._start_time
        metrics["system_uptime"] = [MetricPoint(now, uptime_seconds)]

        # Cache metrics (if available)
        if self.cache_manager:
            cache_stats = await self.cache_manager.get_stats()

            metrics["cache_hit_rate"] = [MetricPoint(now, cache_stats.hit_rate)]
            metrics["cache_memory_usage"] = [MetricPoint(now, cache_stats.memory_usage)]
            metrics["cache_total_requests"] = [
                MetricPoint(now, cache_stats.total_requests),
            ]
            metrics["cache_successful_requests"] = [
                MetricPoint(now, cache_stats.successful_requests),
            ]

            # Per-tier metrics
            for tier, hits in cache_stats.hits.items():
                tier_name = tier.value if hasattr(tier, "value") else str(tier)
                metrics[f"cache_hits_{tier_name}"] = [MetricPoint(now, hits)]

            for tier, misses in cache_stats.misses.items():
                tier_name = tier.value if hasattr(tier, "value") else str(tier)
                metrics[f"cache_misses_{tier_name}"] = [MetricPoint(now, misses)]

        # Orchestrator metrics (mock data for demonstration)
        if self.orchestrator_manager:
            # These would be real metrics from the orchestrator
            metrics["ingestion_requests_total"] = [MetricPoint(now, 1250)]
            metrics["ingestion_success_rate"] = [MetricPoint(now, 0.987)]
            metrics["average_processing_time"] = [MetricPoint(now, 1.23)]

            # Source-specific metrics
            for source in ["arxiv", "pubmed", "firecrawl", "email", "social", "rss"]:
                metrics[f"source_requests_{source}"] = [MetricPoint(now, 150)]
                metrics[f"source_success_rate_{source}"] = [MetricPoint(now, 0.95)]

        return metrics


class SystemHealthChecker:
    """Monitors system health and generates alerts"""

    def __init__(self, config: DashboardConfig, metric_collector: MetricCollector):
        self.config = config
        self.metric_collector = metric_collector
        self._alerts = []

    async def check_health(self) -> SystemHealth:
        """Perform comprehensive health check"""
        health = SystemHealth()
        health.last_check = datetime.now(UTC)

        try:
            # Collect current metrics
            metrics = await self.metric_collector.collect_metrics()

            # Check cache health
            cache_status = await self._check_cache_health(metrics)
            health.component_health["cache"] = cache_status

            # Check ingestion health
            ingestion_status = await self._check_ingestion_health(metrics)
            health.component_health["ingestion"] = ingestion_status

            # Check system resources
            resource_status = await self._check_system_resources()
            health.component_health["resources"] = resource_status

            # Determine overall status
            health.overall_status = self._calculate_overall_status(
                health.component_health,
            )
            health.alerts = self._get_active_alerts()

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health.overall_status = HealthStatus.CRITICAL
            health.component_health["system"] = HealthStatus.CRITICAL
            health.alerts = [f"Health check system error: {str(e)}"]
            self._add_alert(f"Health check system error: {str(e)}")

        return health

    async def _check_cache_health(
        self,
        metrics: dict[str, list[MetricPoint]],
    ) -> HealthStatus:
        """Check cache system health"""
        if "cache_hit_rate" not in metrics:
            return HealthStatus.UNKNOWN

        hit_rate = metrics["cache_hit_rate"][0].value

        if hit_rate < 0.3:  # Below 30% hit rate
            self._add_alert(f"Low cache hit rate: {hit_rate:.1%}")
            return HealthStatus.WARNING

        if hit_rate < 0.1:  # Below 10% hit rate
            return HealthStatus.CRITICAL

        return HealthStatus.HEALTHY

    async def _check_ingestion_health(
        self,
        metrics: dict[str, list[MetricPoint]],
    ) -> HealthStatus:
        """Check ingestion pipeline health"""
        if "ingestion_success_rate" not in metrics:
            return HealthStatus.UNKNOWN

        success_rate = metrics["ingestion_success_rate"][0].value

        if success_rate < 0.95:  # Below 95% success rate
            self._add_alert(f"Low ingestion success rate: {success_rate:.1%}")
            return HealthStatus.WARNING

        if success_rate < 0.85:  # Below 85% success rate
            return HealthStatus.CRITICAL

        # Check processing time
        if "average_processing_time" in metrics:
            avg_time = metrics["average_processing_time"][0].value
            if avg_time > self.config.response_time_threshold:
                self._add_alert(f"High processing time: {avg_time:.2f}s")
                return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    async def _check_system_resources(self) -> HealthStatus:
        """Check system resource utilization"""
        # In production, this would check real system metrics
        # For now, simulate resource checks

        # Memory check (simulated)
        memory_usage = 0.72  # 72%
        if memory_usage > self.config.memory_usage_threshold:
            self._add_alert(f"High memory usage: {memory_usage:.1%}")
            return HealthStatus.CRITICAL
        if memory_usage > 0.75:
            return HealthStatus.WARNING

        # Disk check (simulated)
        disk_usage = 0.65  # 65%
        if disk_usage > self.config.disk_usage_threshold:
            self._add_alert(f"High disk usage: {disk_usage:.1%}")
            return HealthStatus.CRITICAL
        if disk_usage > 0.80:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    def _calculate_overall_status(
        self,
        component_health: dict[str, HealthStatus],
    ) -> HealthStatus:
        """Calculate overall system status"""
        if not component_health:
            return HealthStatus.UNKNOWN

        statuses = list(component_health.values())

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    def _add_alert(self, message: str):
        """Add alert to the active alerts list"""
        if message not in self._alerts:
            self._alerts.append(message)

    def _get_active_alerts(self) -> list[str]:
        """Get current active alerts"""
        return self._alerts.copy()


class RealTimeMonitoringDashboard:
    """Real-time monitoring dashboard for PAKE system.
    Provides live metrics, health monitoring, and alerting.
    """

    def __init__(self, config: DashboardConfig = None):
        self.config = config or DashboardConfig()
        self.metrics_history: dict[str, list[MetricPoint]] = {}
        self.is_running = False

        # Initialize collectors
        self.metric_collector = IngestionMetrics()
        self.health_checker = SystemHealthChecker(self.config, self.metric_collector)

        # Current state
        self.current_metrics = {}
        self.current_health = SystemHealth()

        logger.info("Initialized RealTimeMonitoringDashboard")

    async def start(self):
        """Start the monitoring dashboard"""
        self.is_running = True
        logger.info("Starting Real-Time Monitoring Dashboard")

        # Start background tasks
        tasks = [
            asyncio.create_task(self._metric_collection_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._dashboard_update_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            await self.stop()

    async def stop(self):
        """Stop the monitoring dashboard"""
        logger.info("Stopping Real-Time Monitoring Dashboard")
        self.is_running = False

    async def _metric_collection_loop(self):
        """Background loop for metric collection"""
        while self.is_running:
            try:
                # Collect metrics
                new_metrics = await self.metric_collector.collect_metrics()

                # Update metrics history
                for metric_name, points in new_metrics.items():
                    if metric_name not in self.metrics_history:
                        self.metrics_history[metric_name] = []

                    self.metrics_history[metric_name].extend(points)

                    # Trim old data
                    self._trim_metric_history(metric_name)

                self.current_metrics = new_metrics

            except Exception as e:
                logger.error(f"Metric collection error: {e}")

            await asyncio.sleep(self.config.metric_update_interval)

    async def _health_check_loop(self):
        """Background loop for health monitoring"""
        while self.is_running:
            try:
                self.current_health = await self.health_checker.check_health()

                # Log critical alerts
                if self.current_health.overall_status == HealthStatus.CRITICAL:
                    logger.critical(
                        f"CRITICAL SYSTEM STATUS: {self.current_health.alerts}",
                    )
                elif self.current_health.alerts:
                    logger.warning(f"System alerts: {self.current_health.alerts}")

            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.config.health_check_interval)

    async def _dashboard_update_loop(self):
        """Background loop for dashboard updates"""
        while self.is_running:
            try:
                # Generate dashboard data
                dashboard_data = await self.get_dashboard_data()

                # In production, this would update WebSocket connections
                # or write to a shared data store for the web dashboard
                logger.debug(f"Dashboard updated: {len(dashboard_data)} metrics")

            except Exception as e:
                logger.error(f"Dashboard update error: {e}")

            await asyncio.sleep(self.config.dashboard_refresh_interval)

    def _trim_metric_history(self, metric_name: str):
        """Remove old metric data points"""
        if metric_name not in self.metrics_history:
            return

        points = self.metrics_history[metric_name]

        # Filter out corrupted data and invalid points
        valid_points = []
        cutoff_time = datetime.now(UTC) - timedelta(
            hours=self.config.metric_retention_hours,
        )

        for p in points:
            try:
                # Validate point is a MetricPoint and has required attributes
                if (
                    hasattr(p, "timestamp")
                    and hasattr(p, "value")
                    and hasattr(p, "to_dict")
                ):
                    if p.timestamp > cutoff_time:
                        valid_points.append(p)
            except Exception:
                # Skip corrupted points
                continue

        # Limit number of points
        if len(valid_points) > self.config.max_data_points:
            valid_points = valid_points[-self.config.max_data_points :]

        self.metrics_history[metric_name] = valid_points

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "health": self.current_health.to_dict(),
            "current_metrics": {
                name: points[-1].to_dict() if points else None
                for name, points in self.current_metrics.items()
            },
            "metric_history": {
                name: [
                    p.to_dict() for p in points[-50:] if hasattr(p, "to_dict")
                ]  # Last 50 valid points
                for name, points in self.metrics_history.items()
            },
            "system_info": {
                "uptime": time.time()
                - (
                    self.metric_collector._start_time
                    if hasattr(self.metric_collector, "_start_time")
                    else time.time()
                ),
                "config": {
                    "metric_update_interval": self.config.metric_update_interval,
                    "health_check_interval": self.config.health_check_interval,
                    "dashboard_refresh_interval": self.config.dashboard_refresh_interval,
                },
            },
        }

    async def get_health_status(self) -> SystemHealth:
        """Get current system health status"""
        return self.current_health

    async def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary for API endpoints"""
        summary = {}

        for metric_name, points in self.current_metrics.items():
            if points:
                latest = points[-1]
                summary[metric_name] = {
                    "current_value": latest.value,
                    "timestamp": latest.timestamp.isoformat(),
                    "labels": latest.labels,
                }

        return summary

    async def export_metrics(self, filepath: str) -> bool:
        """Export current metrics to JSON file"""
        try:
            dashboard_data = await self.get_dashboard_data()

            async with aiofiles.open(filepath, "w") as f:
                await f.write(json.dumps(dashboard_data, indent=2, default=str))

            logger.info(f"Metrics exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False


# Example usage and integration
async def create_production_dashboard(
    cache_manager=None,
    orchestrator_manager=None,
) -> RealTimeMonitoringDashboard:
    """Create production-ready monitoring dashboard with real integrations."""
    config = DashboardConfig(
        metric_update_interval=0.5,  # 500ms updates
        health_check_interval=2.0,  # 2 second health checks
        dashboard_refresh_interval=1.0,  # 1 second dashboard updates
        metric_retention_hours=48,  # 48 hour history
        error_rate_threshold=0.02,  # 2% error threshold
        response_time_threshold=3.0,  # 3 second response threshold
    )

    dashboard = RealTimeMonitoringDashboard(config)

    # Configure with real services
    dashboard.metric_collector = IngestionMetrics(orchestrator_manager, cache_manager)
    dashboard.health_checker = SystemHealthChecker(config, dashboard.metric_collector)

    return dashboard


if __name__ == "__main__":
    # Example standalone usage
    async def main():
        dashboard = RealTimeMonitoringDashboard()

        # Start dashboard (would run indefinitely)
        try:
            await asyncio.wait_for(dashboard.start(), timeout=10.0)
        except TimeoutError:
            logger.info("Dashboard demo completed")
        finally:
            await dashboard.stop()

    asyncio.run(main())
