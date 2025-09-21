"""Comprehensive Monitoring and Analytics Platform for PAKE System
Enterprise-grade observability, insights, and performance analytics.
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemComponent(Enum):
    """System components being monitored"""

    API_GATEWAY = "api_gateway"
    COGNITIVE_ENGINE = "cognitive_engine"
    SEMANTIC_SEARCH = "semantic_search"
    QUERY_EXPANSION = "query_expansion"
    REALTIME_PIPELINE = "realtime_pipeline"
    ADAPTIVE_LEARNING = "adaptive_learning"
    CONTENT_ROUTING = "content_routing"
    EXTERNAL_APIS = "external_apis"
    DATABASE = "database"
    CACHE = "cache"


class AnalyticsTimeframe(Enum):
    """Analytics time frames"""

    REAL_TIME = "real_time"
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


@dataclass(frozen=True)
class MetricPoint:
    """Immutable metric data point"""

    metric_name: str
    metric_type: MetricType
    value: float | int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    labels: dict[str, str] = field(default_factory=dict)
    component: SystemComponent = SystemComponent.API_GATEWAY
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AlertRule:
    """Immutable alert rule definition"""

    rule_id: str
    name: str
    metric_name: str
    component: SystemComponent
    condition: str  # e.g., "> 0.8", "< 100", "== 0"
    threshold: float
    severity: AlertSeverity
    cooldown_minutes: int = 5
    is_active: bool = True
    notification_channels: list[str] = field(default_factory=list)
    description: str = ""
    created_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class Alert:
    """Immutable alert instance"""

    alert_id: str
    rule_id: str
    component: SystemComponent
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    triggered_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    resolved_timestamp: datetime | None = None
    is_resolved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PerformanceReport:
    """Immutable performance analytics report"""

    report_id: str
    component: SystemComponent
    timeframe: AnalyticsTimeframe
    start_time: datetime
    end_time: datetime
    metrics_summary: dict[str, Any] = field(default_factory=dict)
    performance_insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    trends: dict[str, Any] = field(default_factory=dict)
    generated_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class SystemHealthStatus:
    """Immutable system health status"""

    overall_status: str  # healthy, degraded, critical, down
    component_statuses: dict[SystemComponent, str] = field(default_factory=dict)
    active_alerts: list[Alert] = field(default_factory=list)
    performance_score: float = 1.0  # 0.0 to 1.0
    uptime_percentage: float = 100.0
    last_incident: datetime | None = None
    health_check_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metrics_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsPlatformConfig:
    """Configuration for analytics platform"""

    enable_real_time_monitoring: bool = True
    enable_alerting: bool = True
    enable_performance_analytics: bool = True
    enable_predictive_insights: bool = True
    metric_retention_days: int = 30
    high_frequency_metrics_retention_hours: int = 24
    alert_cooldown_minutes: int = 5
    health_check_interval_seconds: int = 30
    analytics_computation_interval_minutes: int = 5
    max_metrics_per_minute: int = 10000
    enable_metric_aggregation: bool = True
    aggregation_window_minutes: int = 1
    enable_anomaly_detection: bool = True
    anomaly_sensitivity: float = 0.8
    notification_channels: list[str] = field(default_factory=lambda: ["email", "slack"])
    enable_dashboard: bool = True
    dashboard_refresh_seconds: int = 10


class MetricsCollector:
    """High-performance metrics collection and storage"""

    def __init__(self, config: AnalyticsPlatformConfig):
        self.config = config
        self.metrics_buffer: deque = deque(maxlen=100000)  # High-performance buffer
        self.aggregated_metrics: dict[str, dict] = defaultdict(dict)
        self.metric_schemas: dict[str, MetricType] = {}
        self.collection_stats = {
            "total_metrics_collected": 0,
            "metrics_per_second": 0.0,
            "buffer_utilization": 0.0,
            "last_collection_time": datetime.now(UTC),
        }

        # Time-series storage for different retention periods
        self.real_time_metrics: deque = deque(maxlen=3600)  # Last hour at 1s resolution
        self.hourly_metrics: dict[str, list] = defaultdict(list)  # Last day
        self.daily_metrics: dict[str, list] = defaultdict(list)  # Last month

    async def collect_metric(self, metric: MetricPoint) -> bool:
        """Collect a single metric point"""
        try:
            # Add to high-performance buffer
            self.metrics_buffer.append(metric)

            # Track metric schema
            self.metric_schemas[metric.metric_name] = metric.metric_type

            # Add to real-time storage
            self.real_time_metrics.append(metric)

            # Update collection stats
            self.collection_stats["total_metrics_collected"] += 1
            self.collection_stats["buffer_utilization"] = (
                len(self.metrics_buffer) / self.metrics_buffer.maxlen
            )

            # Trigger aggregation if enabled
            if self.config.enable_metric_aggregation:
                await self._aggregate_metric(metric)

            return True

        except Exception as e:
            logger.error(f"Failed to collect metric {metric.metric_name}: {e}")
            return False

    async def collect_batch_metrics(self, metrics: list[MetricPoint]) -> int:
        """Collect multiple metrics efficiently"""
        successful_count = 0

        for metric in metrics:
            if await self.collect_metric(metric):
                successful_count += 1

        # Update metrics per second calculation
        now = datetime.now(UTC)
        time_diff = (
            now - self.collection_stats["last_collection_time"]
        ).total_seconds()
        if time_diff > 0:
            self.collection_stats["metrics_per_second"] = successful_count / time_diff
        self.collection_stats["last_collection_time"] = now

        return successful_count

    async def _aggregate_metric(self, metric: MetricPoint):
        """Aggregate metric for efficient storage and querying"""
        window_key = self._get_aggregation_window_key(metric.timestamp)
        metric_key = f"{metric.component.value}_{metric.metric_name}"

        if metric_key not in self.aggregated_metrics[window_key]:
            self.aggregated_metrics[window_key][metric_key] = {
                "count": 0,
                "sum": 0.0,
                "min": float("inf"),
                "max": float("-inf"),
                "values": [],
            }

        agg = self.aggregated_metrics[window_key][metric_key]
        agg["count"] += 1
        agg["sum"] += metric.value
        agg["min"] = min(agg["min"], metric.value)
        agg["max"] = max(agg["max"], metric.value)
        agg["values"].append(metric.value)

        # Keep only recent values for percentile calculations
        if len(agg["values"]) > 1000:
            agg["values"] = agg["values"][-1000:]

    def _get_aggregation_window_key(self, timestamp: datetime) -> str:
        """Get aggregation window key for timestamp"""
        window_minutes = self.config.aggregation_window_minutes
        window_start = timestamp.replace(second=0, microsecond=0)
        window_start = window_start.replace(
            minute=(window_start.minute // window_minutes) * window_minutes,
        )
        return window_start.isoformat()

    def get_metrics(
        self,
        component: SystemComponent,
        metric_name: str,
        timeframe: AnalyticsTimeframe,
    ) -> list[MetricPoint]:
        """Get metrics for specific component and timeframe"""
        end_time = datetime.now(UTC)

        if timeframe == AnalyticsTimeframe.REAL_TIME:
            start_time = end_time - timedelta(minutes=5)
        elif timeframe == AnalyticsTimeframe.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
        elif timeframe == AnalyticsTimeframe.LAST_DAY:
            start_time = end_time - timedelta(days=1)
        elif timeframe == AnalyticsTimeframe.LAST_WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif timeframe == AnalyticsTimeframe.LAST_MONTH:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=1)  # Default

        # Filter metrics from real-time storage
        filtered_metrics = []
        for metric in self.real_time_metrics:
            if (
                metric.component == component
                and metric.metric_name == metric_name
                and start_time <= metric.timestamp <= end_time
            ):
                filtered_metrics.append(metric)

        return sorted(filtered_metrics, key=lambda m: m.timestamp)

    def get_aggregated_metrics(self, window_key: str) -> dict[str, Any]:
        """Get aggregated metrics for specific window"""
        return self.aggregated_metrics.get(window_key, {})

    def get_collection_stats(self) -> dict[str, Any]:
        """Get metrics collection statistics"""
        return {
            **self.collection_stats,
            "buffer_size": len(self.metrics_buffer),
            "buffer_max_size": self.metrics_buffer.maxlen,
            "real_time_metrics_count": len(self.real_time_metrics),
            "aggregated_windows": len(self.aggregated_metrics),
            "metric_types_tracked": len(self.metric_schemas),
        }


class AlertManager:
    """Intelligent alerting and notification management"""

    def __init__(self, config: AnalyticsPlatformConfig):
        self.config = config
        self.alert_rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.resolved_alerts: deque = deque(maxlen=10000)
        self.alert_cooldowns: dict[str, datetime] = {}
        self.notification_queue: deque = deque()

        # Alert statistics
        self.alert_stats = {
            "total_alerts_triggered": 0,
            "alerts_resolved": 0,
            "avg_resolution_time_minutes": 0.0,
            "false_positive_rate": 0.0,
            "critical_alerts_count": 0,
        }

        self._setup_default_alert_rules()

    def _setup_default_alert_rules(self):
        """Setup default alert rules for system monitoring"""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                metric_name="error_rate",
                component=SystemComponent.API_GATEWAY,
                condition="> 0.05",
                threshold=0.05,
                severity=AlertSeverity.WARNING,
                cooldown_minutes=5,
                description="API error rate exceeds 5%",
            ),
            AlertRule(
                rule_id="critical_error_rate",
                name="Critical Error Rate",
                metric_name="error_rate",
                component=SystemComponent.API_GATEWAY,
                condition="> 0.15",
                threshold=0.15,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=2,
                description="API error rate exceeds 15%",
            ),
            AlertRule(
                rule_id="high_response_time",
                name="High Response Time",
                metric_name="average_response_time_ms",
                component=SystemComponent.API_GATEWAY,
                condition="> 2000",
                threshold=2000,
                severity=AlertSeverity.WARNING,
                cooldown_minutes=10,
                description="API response time exceeds 2 seconds",
            ),
            AlertRule(
                rule_id="low_system_health",
                name="Low System Health",
                metric_name="health_score",
                component=SystemComponent.API_GATEWAY,
                condition="< 0.7",
                threshold=0.7,
                severity=AlertSeverity.ERROR,
                cooldown_minutes=3,
                description="System health score below 70%",
            ),
            AlertRule(
                rule_id="processing_pipeline_failure",
                name="Processing Pipeline Failure",
                metric_name="success_rate",
                component=SystemComponent.REALTIME_PIPELINE,
                condition="< 0.9",
                threshold=0.9,
                severity=AlertSeverity.ERROR,
                cooldown_minutes=5,
                description="Processing pipeline success rate below 90%",
            ),
        ]

        for rule in default_rules:
            self.add_alert_rule(rule)

    def add_alert_rule(self, rule: AlertRule):
        """Add new alert rule"""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name} ({rule.rule_id})")

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False

    async def evaluate_metrics(self, metrics: list[MetricPoint]) -> list[Alert]:
        """Evaluate metrics against alert rules"""
        triggered_alerts = []

        if not self.config.enable_alerting:
            return triggered_alerts

        for metric in metrics:
            for rule in self.alert_rules.values():
                if not rule.is_active:
                    continue

                if (
                    rule.component == metric.component
                    and rule.metric_name == metric.metric_name
                ):
                    alert = await self._evaluate_rule(rule, metric)
                    if alert:
                        triggered_alerts.append(alert)

        return triggered_alerts

    async def _evaluate_rule(
        self,
        rule: AlertRule,
        metric: MetricPoint,
    ) -> Alert | None:
        """Evaluate single rule against metric"""
        # Check cooldown
        if rule.rule_id in self.alert_cooldowns:
            cooldown_end = self.alert_cooldowns[rule.rule_id] + timedelta(
                minutes=rule.cooldown_minutes,
            )
            if datetime.now(UTC) < cooldown_end:
                return None

        # Evaluate condition
        condition_met = self._evaluate_condition(
            rule.condition,
            rule.threshold,
            metric.value,
        )

        if condition_met:
            alert_id = f"{rule.rule_id}_{int(time.time())}"

            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                component=rule.component,
                severity=rule.severity,
                message=f"{rule.name}: {rule.description} (Current: {
                    metric.value
                }, Threshold: {rule.threshold})",
                metric_value=metric.value,
                threshold=rule.threshold,
                metadata={"metric_labels": metric.labels},
            )

            # Add to active alerts
            self.active_alerts[alert_id] = alert

            # Set cooldown
            self.alert_cooldowns[rule.rule_id] = datetime.now(UTC)

            # Update statistics
            self.alert_stats["total_alerts_triggered"] += 1
            if alert.severity == AlertSeverity.CRITICAL:
                self.alert_stats["critical_alerts_count"] += 1

            # Queue for notification
            self.notification_queue.append(alert)

            logger.warning(f"Alert triggered: {alert.message}")
            return alert

        return None

    def _evaluate_condition(
        self,
        condition: str,
        threshold: float,
        value: float,
    ) -> bool:
        """Evaluate alert condition"""
        try:
            if condition.startswith(">"):
                return value > threshold
            if condition.startswith("<"):
                return value < threshold
            if condition.startswith("=="):
                return abs(value - threshold) < 0.001  # Float comparison
            if condition.startswith("!="):
                return abs(value - threshold) >= 0.001
            if condition.startswith(">="):
                return value >= threshold
            if condition.startswith("<="):
                return value <= threshold
            return False
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            resolved_alert = Alert(
                alert_id=alert.alert_id,
                rule_id=alert.rule_id,
                component=alert.component,
                severity=alert.severity,
                message=alert.message,
                metric_value=alert.metric_value,
                threshold=alert.threshold,
                triggered_timestamp=alert.triggered_timestamp,
                resolved_timestamp=datetime.now(UTC),
                is_resolved=True,
                metadata=alert.metadata,
            )

            # Move to resolved alerts
            self.resolved_alerts.append(resolved_alert)
            del self.active_alerts[alert_id]

            # Update statistics
            self.alert_stats["alerts_resolved"] += 1
            resolution_time = (
                resolved_alert.resolved_timestamp - alert.triggered_timestamp
            ).total_seconds() / 60
            current_avg = self.alert_stats["avg_resolution_time_minutes"]
            total_resolved = self.alert_stats["alerts_resolved"]
            self.alert_stats["avg_resolution_time_minutes"] = (
                (current_avg * (total_resolved - 1)) + resolution_time
            ) / total_resolved

            logger.info(f"Alert resolved: {alert_id}")
            return True

        return False

    def get_active_alerts(
        self,
        severity: AlertSeverity | None = None,
    ) -> list[Alert]:
        """Get active alerts, optionally filtered by severity"""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return sorted(alerts, key=lambda a: a.triggered_timestamp, reverse=True)

    def get_alert_stats(self) -> dict[str, Any]:
        """Get alerting statistics"""
        return {
            **self.alert_stats,
            "active_alerts_count": len(self.active_alerts),
            "alert_rules_count": len(self.alert_rules),
            "pending_notifications": len(self.notification_queue),
            "cooldowns_active": len(self.alert_cooldowns),
        }


class PerformanceAnalyzer:
    """Advanced performance analytics and insights generation"""

    def __init__(self, config: AnalyticsPlatformConfig):
        self.config = config
        self.analysis_cache: dict[str, tuple[Any, datetime]] = {}
        self.trend_detectors: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1440),
        )  # 24h of minutes
        self.anomaly_detectors: dict[str, dict] = defaultdict(dict)

        # Performance baselines
        self.performance_baselines: dict[SystemComponent, dict[str, float]] = {
            SystemComponent.API_GATEWAY: {
                "response_time_ms": 200.0,
                "success_rate": 0.99,
                "throughput_rps": 100.0,
            },
            SystemComponent.REALTIME_PIPELINE: {
                "processing_time_ms": 500.0,
                "success_rate": 0.95,
                "throughput_items_per_second": 50.0,
            },
        }

    async def generate_performance_report(
        self,
        component: SystemComponent,
        timeframe: AnalyticsTimeframe,
        metrics_collector: MetricsCollector,
    ) -> PerformanceReport:
        """Generate comprehensive performance report"""
        report_id = (
            f"perf_report_{component.value}_{timeframe.value}_{int(time.time())}"
        )

        # Determine time range
        end_time = datetime.now(UTC)
        if timeframe == AnalyticsTimeframe.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
        elif timeframe == AnalyticsTimeframe.LAST_DAY:
            start_time = end_time - timedelta(days=1)
        elif timeframe == AnalyticsTimeframe.LAST_WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif timeframe == AnalyticsTimeframe.LAST_MONTH:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=1)

        # Collect metrics for analysis
        key_metrics = ["response_time_ms", "success_rate", "error_rate", "throughput"]
        metrics_data = {}

        for metric_name in key_metrics:
            metrics = metrics_collector.get_metrics(component, metric_name, timeframe)
            if metrics:
                values = [m.value for m in metrics]
                metrics_data[metric_name] = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values),
                    "p95": self._calculate_percentile(values, 95),
                    "p99": self._calculate_percentile(values, 99),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
                }

        # Generate insights and recommendations
        insights = await self._generate_performance_insights(component, metrics_data)
        recommendations = await self._generate_recommendations(component, metrics_data)
        trends = await self._analyze_trends(component, metrics_data, timeframe)

        return PerformanceReport(
            report_id=report_id,
            component=component,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            metrics_summary=metrics_data,
            performance_insights=insights,
            recommendations=recommendations,
            trends=trends,
        )

    async def _generate_performance_insights(
        self,
        component: SystemComponent,
        metrics_data: dict[str, Any],
    ) -> list[str]:
        """Generate performance insights from metrics data"""
        insights = []
        baselines = self.performance_baselines.get(component, {})

        for metric_name, data in metrics_data.items():
            if not data:
                continue

            baseline = baselines.get(metric_name)
            if baseline:
                avg_value = data["avg"]
                deviation = abs(avg_value - baseline) / baseline

                if deviation > 0.2:  # >20% deviation
                    direction = "higher" if avg_value > baseline else "lower"
                    insights.append(
                        f"{metric_name} is {deviation:.1%} {direction} than baseline ({
                            avg_value:.2f} vs {baseline:.2f})",
                    )

                if data["p95"] > baseline * 1.5:
                    insights.append(
                        f"{metric_name} P95 ({data['p95']:.2f}) indicates performance degradation",
                    )

                if data["std_dev"] > baseline * 0.3:
                    insights.append(
                        f"{metric_name} shows high variability (std dev: {data['std_dev']:.2f})",
                    )

        # Detect anomalies
        anomalies = await self._detect_anomalies(component, metrics_data)
        insights.extend(anomalies)

        return insights

    async def _generate_recommendations(
        self,
        component: SystemComponent,
        metrics_data: dict[str, Any],
    ) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Response time recommendations
        if "response_time_ms" in metrics_data:
            rt_data = metrics_data["response_time_ms"]
            if rt_data["p95"] > 1000:  # >1s P95
                recommendations.append(
                    "Consider implementing response caching to reduce P95 latency",
                )
                recommendations.append(
                    "Review database query performance and add indexes if needed",
                )

            if rt_data["std_dev"] > rt_data["avg"] * 0.5:
                recommendations.append(
                    "High response time variability detected - investigate inconsistent performance",
                )

        # Error rate recommendations
        if "error_rate" in metrics_data:
            er_data = metrics_data["error_rate"]
            if er_data["avg"] > 0.05:  # >5% error rate
                recommendations.append(
                    "Error rate exceeds acceptable threshold - implement better error handling",
                )
                recommendations.append(
                    "Enable circuit breaker patterns for external dependencies",
                )

        # Success rate recommendations
        if "success_rate" in metrics_data:
            sr_data = metrics_data["success_rate"]
            if sr_data["avg"] < 0.95:  # <95% success rate
                recommendations.append(
                    "Success rate below target - review failure modes and add retry logic",
                )

        # Throughput recommendations
        if "throughput" in metrics_data:
            th_data = metrics_data["throughput"]
            baseline_throughput = self.performance_baselines.get(component, {}).get(
                "throughput_rps",
                100,
            )
            if th_data["max"] > baseline_throughput * 0.8:
                recommendations.append(
                    "Approaching throughput capacity - consider scaling horizontally",
                )

        return recommendations

    async def _analyze_trends(
        self,
        component: SystemComponent,
        metrics_data: dict[str, Any],
        timeframe: AnalyticsTimeframe,
    ) -> dict[str, Any]:
        """Analyze performance trends"""
        trends = {}

        for metric_name, data in metrics_data.items():
            if not data or data["count"] < 10:
                continue

            # Simple trend analysis (would be more sophisticated in production)
            recent_avg = data["avg"]
            trend_key = f"{component.value}_{metric_name}"

            if trend_key in self.trend_detectors:
                historical_values = list(self.trend_detectors[trend_key])
                if len(historical_values) >= 10:
                    historical_avg = statistics.mean(historical_values[-10:])
                    trend_direction = (
                        "increasing" if recent_avg > historical_avg else "decreasing"
                    )
                    trend_magnitude = abs(recent_avg - historical_avg) / historical_avg

                    trends[metric_name] = {
                        "direction": trend_direction,
                        "magnitude": trend_magnitude,
                        "significance": "high" if trend_magnitude > 0.1 else "low",
                    }

            # Update trend detector
            self.trend_detectors[trend_key].append(recent_avg)

        return trends

    async def _detect_anomalies(
        self,
        component: SystemComponent,
        metrics_data: dict[str, Any],
    ) -> list[str]:
        """Detect performance anomalies using statistical methods"""
        anomalies = []

        if not self.config.enable_anomaly_detection:
            return anomalies

        for metric_name, data in metrics_data.items():
            if not data or data["count"] < 30:  # Need sufficient data points
                continue

            # Simple anomaly detection using z-score
            mean_val = data["avg"]
            std_val = data["std_dev"]

            if std_val > 0:
                # Check if P99 is an anomaly
                z_score = abs((data["p99"] - mean_val) / std_val)
                if z_score > 2.0:  # 2 standard deviations
                    anomalies.append(
                        f"Anomaly detected in {metric_name}: P99 value ({
                            data['p99']:.2f}) is {
                            z_score:.1f} standard deviations from mean",
                    )

                # Check for unusual distribution
                if data["max"] > mean_val + (3 * std_val):
                    anomalies.append(
                        f"Outlier detected in {metric_name}: max value ({data['max']:.2f}) significantly exceeds normal range",
                    )

        return anomalies

    def _calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)

        if lower_index == upper_index:
            return sorted_values[lower_index]

        # Linear interpolation
        weight = index - lower_index
        return (
            sorted_values[lower_index] * (1 - weight)
            + sorted_values[upper_index] * weight
        )

    def clear_analysis_cache(self):
        """Clear analysis cache to free memory"""
        self.analysis_cache.clear()
        logger.info("Performance analysis cache cleared")


class ComprehensiveAnalyticsPlatform:
    """Main analytics platform integrating all monitoring capabilities.
    Provides enterprise-grade observability and insights.
    """

    def __init__(self, config: AnalyticsPlatformConfig = None):
        self.config = config or AnalyticsPlatformConfig()
        self.metrics_collector = MetricsCollector(self.config)
        self.alert_manager = AlertManager(self.config)
        self.performance_analyzer = PerformanceAnalyzer(self.config)

        # Platform state
        self.is_running = False
        self.background_tasks: list[asyncio.Task] = []
        self.system_start_time = datetime.now(UTC)

        # Dashboard and reporting
        self.dashboard_data: dict[str, Any] = {}
        self.scheduled_reports: dict[str, dict] = {}

        # Integration points
        self.system_components: dict[SystemComponent, dict[str, Any]] = {}

        logger.info("Comprehensive Analytics Platform initialized")

    async def start(self):
        """Start the analytics platform"""
        if self.is_running:
            logger.warning("Analytics platform is already running")
            return

        self.is_running = True

        # Start background tasks
        if self.config.enable_real_time_monitoring:
            self.background_tasks.append(
                asyncio.create_task(self._real_time_monitoring_loop()),
            )

        if self.config.enable_alerting:
            self.background_tasks.append(
                asyncio.create_task(self._alert_processing_loop()),
            )

        if self.config.enable_performance_analytics:
            self.background_tasks.append(
                asyncio.create_task(self._analytics_computation_loop()),
            )

        if self.config.enable_dashboard:
            self.background_tasks.append(
                asyncio.create_task(self._dashboard_update_loop()),
            )

        logger.info("Analytics platform started successfully")

    async def stop(self):
        """Stop the analytics platform"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        self.background_tasks.clear()
        logger.info("Analytics platform stopped")

    async def record_metric(self, metric: MetricPoint) -> bool:
        """Record a single metric"""
        return await self.metrics_collector.collect_metric(metric)

    async def record_metrics_batch(self, metrics: list[MetricPoint]) -> int:
        """Record multiple metrics efficiently"""
        return await self.metrics_collector.collect_batch_metrics(metrics)

    async def get_system_health(self) -> SystemHealthStatus:
        """Get comprehensive system health status"""
        # Collect component statuses
        component_statuses = {}
        active_alerts = self.alert_manager.get_active_alerts()

        # Calculate overall health
        critical_alerts = [
            a for a in active_alerts if a.severity == AlertSeverity.CRITICAL
        ]
        error_alerts = [a for a in active_alerts if a.severity == AlertSeverity.ERROR]

        if critical_alerts:
            overall_status = "critical"
            performance_score = 0.3
        elif error_alerts:
            overall_status = "degraded"
            performance_score = 0.6
        elif len(active_alerts) > 5:
            overall_status = "degraded"
            performance_score = 0.8
        else:
            overall_status = "healthy"
            performance_score = 1.0

        # Calculate uptime
        uptime_seconds = (datetime.now(UTC) - self.system_start_time).total_seconds()
        # Simplified calculation
        uptime_percentage = min(100.0, (uptime_seconds / (24 * 3600)) * 100)

        # Get metrics summary
        metrics_summary = {
            "total_metrics_collected": self.metrics_collector.collection_stats[
                "total_metrics_collected"
            ],
            "metrics_per_second": self.metrics_collector.collection_stats[
                "metrics_per_second"
            ],
            "active_alerts": len(active_alerts),
            "system_components": len(self.system_components),
        }

        return SystemHealthStatus(
            overall_status=overall_status,
            component_statuses=component_statuses,
            active_alerts=active_alerts,
            performance_score=performance_score,
            uptime_percentage=uptime_percentage,
            metrics_summary=metrics_summary,
        )

    async def generate_performance_report(
        self,
        component: SystemComponent,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_HOUR,
    ) -> PerformanceReport:
        """Generate performance report for component"""
        return await self.performance_analyzer.generate_performance_report(
            component,
            timeframe,
            self.metrics_collector,
        )

    async def _real_time_monitoring_loop(self):
        """Background loop for real-time monitoring"""
        while self.is_running:
            try:
                # Process any pending metrics evaluations
                recent_metrics = list(self.metrics_collector.real_time_metrics)[
                    -100:
                ]  # Last 100 metrics

                if recent_metrics:
                    # Evaluate against alert rules
                    alerts = await self.alert_manager.evaluate_metrics(recent_metrics)

                    # Log any new alerts
                    for alert in alerts:
                        logger.warning(f"Real-time alert: {alert.message}")

                await asyncio.sleep(self.config.health_check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in real-time monitoring loop: {e}")
                await asyncio.sleep(30)  # Back off on error

    async def _alert_processing_loop(self):
        """Background loop for alert processing and notifications"""
        while self.is_running:
            try:
                # Process notification queue
                while self.alert_manager.notification_queue:
                    alert = self.alert_manager.notification_queue.popleft()
                    await self._send_notification(alert)

                # Auto-resolve stale alerts (implementation would depend on
                # requirements)
                await self._check_stale_alerts()

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                await asyncio.sleep(30)

    async def _analytics_computation_loop(self):
        """Background loop for analytics computation"""
        while self.is_running:
            try:
                # Generate performance insights for key components
                key_components = [
                    SystemComponent.API_GATEWAY,
                    SystemComponent.REALTIME_PIPELINE,
                ]

                for component in key_components:
                    if component in self.system_components:
                        # Generate quick performance summary
                        report = await self.generate_performance_report(
                            component,
                            AnalyticsTimeframe.LAST_HOUR,
                        )

                        # Store in dashboard data
                        self.dashboard_data[f"{component.value}_performance"] = {
                            "last_updated": datetime.now(UTC).isoformat(),
                            "summary": report.metrics_summary,
                            # Top 3 insights
                            "insights": report.performance_insights[:3],
                            "health_score": report.trends.get("health_score", {}),
                        }

                await asyncio.sleep(
                    self.config.analytics_computation_interval_minutes * 60,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics computation loop: {e}")
                await asyncio.sleep(300)  # 5 minute back off

    async def _dashboard_update_loop(self):
        """Background loop for dashboard data updates"""
        while self.is_running:
            try:
                # Update dashboard with latest system health
                health_status = await self.get_system_health()

                self.dashboard_data.update(
                    {
                        "system_health": {
                            "status": health_status.overall_status,
                            "performance_score": health_status.performance_score,
                            "uptime_percentage": health_status.uptime_percentage,
                            "active_alerts_count": len(health_status.active_alerts),
                            "last_updated": datetime.now(UTC).isoformat(),
                        },
                        "metrics_overview": self.metrics_collector.get_collection_stats(),
                        "alert_stats": self.alert_manager.get_alert_stats(),
                    },
                )

                await asyncio.sleep(self.config.dashboard_refresh_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dashboard update loop: {e}")
                await asyncio.sleep(60)

    async def _send_notification(self, alert: Alert):
        """Send alert notification (mock implementation)"""
        # In production, this would integrate with actual notification systems
        logger.info(f"NOTIFICATION: {alert.severity.value.upper()} - {alert.message}")

        # Mock different notification channels
        for channel in self.config.notification_channels:
            if channel == "email":
                logger.info(f"Email notification sent for alert: {alert.alert_id}")
            elif channel == "slack":
                logger.info(f"Slack notification sent for alert: {alert.alert_id}")
            elif channel == "webhook":
                logger.info(f"Webhook notification sent for alert: {alert.alert_id}")

    async def _check_stale_alerts(self):
        """Check for stale alerts that should be auto-resolved"""
        now = datetime.now(UTC)
        stale_threshold = timedelta(hours=1)  # Auto-resolve alerts older than 1 hour

        stale_alerts = []
        for alert_id, alert in self.alert_manager.active_alerts.items():
            age = now - alert.triggered_timestamp
            if age > stale_threshold:
                stale_alerts.append(alert_id)

        for alert_id in stale_alerts:
            await self.alert_manager.resolve_alert(alert_id)
            logger.info(f"Auto-resolved stale alert: {alert_id}")

    def register_system_component(
        self,
        component: SystemComponent,
        metadata: dict[str, Any],
    ):
        """Register a system component for monitoring"""
        self.system_components[component] = {
            "registered_at": datetime.now(UTC),
            "metadata": metadata,
            "health_status": "unknown",
        }
        logger.info(f"Registered system component: {component.value}")

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get current dashboard data"""
        return {
            "platform_status": {
                "is_running": self.is_running,
                "uptime_seconds": (
                    datetime.now(UTC) - self.system_start_time
                ).total_seconds(),
                "background_tasks": len(self.background_tasks),
                "system_components": len(self.system_components),
            },
            **self.dashboard_data,
        }

    def get_comprehensive_metrics(self) -> dict[str, Any]:
        """Get comprehensive platform metrics"""
        return {
            "metrics_collection": self.metrics_collector.get_collection_stats(),
            "alerting": self.alert_manager.get_alert_stats(),
            "system_health": {
                "registered_components": len(self.system_components),
                "platform_uptime": (
                    datetime.now(UTC) - self.system_start_time
                ).total_seconds(),
            },
        }


def create_production_analytics_platform() -> ComprehensiveAnalyticsPlatform:
    """Factory function to create production-ready analytics platform"""
    config = AnalyticsPlatformConfig(
        enable_real_time_monitoring=True,
        enable_alerting=True,
        enable_performance_analytics=True,
        enable_predictive_insights=True,
        metric_retention_days=90,  # Longer retention for production
        high_frequency_metrics_retention_hours=72,  # 3 days of high-freq metrics
        alert_cooldown_minutes=3,  # Shorter cooldown for production
        health_check_interval_seconds=15,  # More frequent health checks
        analytics_computation_interval_minutes=2,  # More frequent analytics
        max_metrics_per_minute=50000,  # Higher throughput
        enable_metric_aggregation=True,
        aggregation_window_minutes=1,
        enable_anomaly_detection=True,
        anomaly_sensitivity=0.85,  # Slightly more sensitive
        notification_channels=["email", "slack", "webhook"],
        enable_dashboard=True,
        dashboard_refresh_seconds=5,  # Faster dashboard updates
    )

    return ComprehensiveAnalyticsPlatform(config)
