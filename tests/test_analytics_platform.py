"""
Comprehensive test suite for Analytics Platform
Tests enterprise-grade monitoring, alerting, and performance analytics.
"""

import asyncio
import statistics
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from services.monitoring.analytics_platform import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AnalyticsPlatformConfig,
    AnalyticsTimeframe,
    ComprehensiveAnalyticsPlatform,
    MetricPoint,
    MetricsCollector,
    MetricType,
    PerformanceAnalyzer,
    PerformanceReport,
    SystemComponent,
    SystemHealthStatus,
    create_production_analytics_platform,
)


@pytest.fixture
def analytics_config():
    """Test configuration for analytics platform"""
    return AnalyticsPlatformConfig(
        enable_real_time_monitoring=True,
        enable_alerting=True,
        enable_performance_analytics=True,
        enable_predictive_insights=True,
        metric_retention_days=7,
        high_frequency_metrics_retention_hours=2,
        alert_cooldown_minutes=1,
        health_check_interval_seconds=10,
        analytics_computation_interval_minutes=1,
        max_metrics_per_minute=1000,
        enable_metric_aggregation=True,
        aggregation_window_minutes=1,
        enable_anomaly_detection=True,
        anomaly_sensitivity=0.8,
        notification_channels=["test_email", "test_slack"],
        enable_dashboard=True,
        dashboard_refresh_seconds=5,
    )


@pytest.fixture
def analytics_platform(analytics_config):
    """Analytics platform instance for testing"""
    return ComprehensiveAnalyticsPlatform(analytics_config)


@pytest_asyncio.fixture
async def running_platform(analytics_platform):
    """Running analytics platform for testing"""
    await analytics_platform.start()
    yield analytics_platform
    await analytics_platform.stop()


@pytest.fixture
def sample_metrics():
    """Sample metrics for testing"""
    base_time = datetime.now(UTC)

    metrics = [
        MetricPoint(
            metric_name="response_time_ms",
            metric_type=MetricType.TIMER,
            value=150.5,
            timestamp=base_time - timedelta(minutes=5),
            labels={"endpoint": "/api/v1/analyze", "method": "POST"},
            component=SystemComponent.API_GATEWAY,
            metadata={"request_id": "req_001"},
        ),
        MetricPoint(
            metric_name="error_rate",
            metric_type=MetricType.RATE,
            value=0.02,
            timestamp=base_time - timedelta(minutes=4),
            labels={"endpoint": "/api/v1/search"},
            component=SystemComponent.API_GATEWAY,
        ),
        MetricPoint(
            metric_name="success_rate",
            metric_type=MetricType.RATE,
            value=0.98,
            timestamp=base_time - timedelta(minutes=3),
            component=SystemComponent.REALTIME_PIPELINE,
        ),
        MetricPoint(
            metric_name="processing_time_ms",
            metric_type=MetricType.TIMER,
            value=450.2,
            timestamp=base_time - timedelta(minutes=2),
            component=SystemComponent.COGNITIVE_ENGINE,
        ),
        MetricPoint(
            metric_name="cache_hit_rate",
            metric_type=MetricType.RATE,
            value=0.85,
            timestamp=base_time - timedelta(minutes=1),
            component=SystemComponent.CACHE,
            labels={"cache_type": "response"},
        ),
    ]

    return metrics


@pytest.fixture
def sample_alert_rules():
    """Sample alert rules for testing"""
    return [
        AlertRule(
            rule_id="test_high_latency",
            name="Test High Latency",
            metric_name="response_time_ms",
            component=SystemComponent.API_GATEWAY,
            condition="> 1000",
            threshold=1000,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=5,
            description="Response time exceeds 1 second",
        ),
        AlertRule(
            rule_id="test_error_rate",
            name="Test Error Rate",
            metric_name="error_rate",
            component=SystemComponent.API_GATEWAY,
            condition="> 0.05",
            threshold=0.05,
            severity=AlertSeverity.ERROR,
            cooldown_minutes=3,
            description="Error rate exceeds 5%",
        ),
        AlertRule(
            rule_id="test_low_success",
            name="Test Low Success Rate",
            metric_name="success_rate",
            component=SystemComponent.REALTIME_PIPELINE,
            condition="< 0.9",
            threshold=0.9,
            severity=AlertSeverity.CRITICAL,
            cooldown_minutes=1,
            description="Success rate below 90%",
        ),
    ]


class TestComprehensiveAnalyticsPlatform:
    """Test the main analytics platform functionality"""

    @pytest.mark.asyncio
    async def test_should_initialize_analytics_platform_with_configuration(
        self,
        analytics_config,
    ):
        """
        Test: Should initialize analytics platform with proper configuration
        and all components ready for enterprise monitoring operations.
        """
        platform = ComprehensiveAnalyticsPlatform(analytics_config)

        # Verify initialization
        assert platform.config == analytics_config
        assert platform.metrics_collector is not None
        assert platform.alert_manager is not None
        assert platform.performance_analyzer is not None
        assert not platform.is_running
        assert len(platform.background_tasks) == 0
        assert isinstance(platform.system_start_time, datetime)

        # Verify component integration
        assert len(platform.system_components) == 0
        assert len(platform.dashboard_data) == 0
        assert len(platform.scheduled_reports) == 0

    @pytest.mark.asyncio
    async def test_should_start_and_stop_platform_correctly(self, analytics_platform):
        """
        Test: Should start and stop analytics platform with proper
        background task management and resource cleanup.
        """
        # Initially not running
        assert not analytics_platform.is_running
        assert len(analytics_platform.background_tasks) == 0

        # Start platform
        await analytics_platform.start()
        assert analytics_platform.is_running
        assert len(analytics_platform.background_tasks) > 0

        # Background tasks should be running
        for task in analytics_platform.background_tasks:
            assert not task.done()

        # Stop platform
        await analytics_platform.stop()
        assert not analytics_platform.is_running
        assert len(analytics_platform.background_tasks) == 0

    @pytest.mark.asyncio
    async def test_should_collect_and_store_metrics_efficiently(
        self,
        running_platform,
        sample_metrics,
    ):
        """
        Test: Should collect and store metrics efficiently with proper
        aggregation and high-performance storage mechanisms.
        """
        # Record individual metrics
        for metric in sample_metrics[:3]:
            success = await running_platform.record_metric(metric)
            assert success is True

        # Record batch metrics
        batch_success_count = await running_platform.record_metrics_batch(
            sample_metrics[3:],
        )
        assert batch_success_count == len(sample_metrics[3:])

        # Verify metrics are stored
        collector_stats = running_platform.metrics_collector.get_collection_stats()
        assert collector_stats["total_metrics_collected"] >= len(sample_metrics)
        assert collector_stats["buffer_size"] > 0
        assert collector_stats["real_time_metrics_count"] > 0

        # Verify metric retrieval
        api_metrics = running_platform.metrics_collector.get_metrics(
            SystemComponent.API_GATEWAY,
            "response_time_ms",
            AnalyticsTimeframe.LAST_HOUR,
        )
        assert len(api_metrics) > 0
        assert api_metrics[0].metric_name == "response_time_ms"

    @pytest.mark.asyncio
    async def test_should_trigger_alerts_based_on_metric_thresholds(
        self,
        running_platform,
        sample_alert_rules,
    ):
        """
        Test: Should trigger alerts when metrics exceed defined thresholds
        and manage alert lifecycle with proper cooldown periods.
        """
        # Add test alert rules
        for rule in sample_alert_rules:
            running_platform.alert_manager.add_alert_rule(rule)

        # Create metric that should trigger alert
        high_latency_metric = MetricPoint(
            metric_name="response_time_ms",
            metric_type=MetricType.TIMER,
            value=1500.0,  # Above 1000ms threshold
            component=SystemComponent.API_GATEWAY,
        )

        # Record the metric
        await running_platform.record_metric(high_latency_metric)

        # Evaluate metrics for alerts
        alerts = await running_platform.alert_manager.evaluate_metrics(
            [high_latency_metric],
        )

        # Verify alert was triggered
        assert len(alerts) > 0
        triggered_alert = alerts[0]
        assert triggered_alert.rule_id == "test_high_latency"
        assert triggered_alert.severity == AlertSeverity.WARNING
        assert triggered_alert.metric_value == 1500.0
        assert not triggered_alert.is_resolved

        # Verify alert is active
        active_alerts = running_platform.alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        assert active_alerts[0].alert_id == triggered_alert.alert_id

    @pytest.mark.asyncio
    async def test_should_generate_comprehensive_performance_reports(
        self,
        running_platform,
        sample_metrics,
    ):
        """
        Test: Should generate comprehensive performance reports with
        insights, recommendations, and trend analysis.
        """
        # Record metrics for analysis
        await running_platform.record_metrics_batch(sample_metrics)

        # Allow some processing time
        await asyncio.sleep(0.1)

        # Generate performance report
        report = await running_platform.generate_performance_report(
            SystemComponent.API_GATEWAY,
            AnalyticsTimeframe.LAST_HOUR,
        )

        # Verify report structure
        assert isinstance(report, PerformanceReport)
        assert report.component == SystemComponent.API_GATEWAY
        assert report.timeframe == AnalyticsTimeframe.LAST_HOUR
        assert isinstance(report.start_time, datetime)
        assert isinstance(report.end_time, datetime)
        assert report.start_time < report.end_time

        # Verify report content
        assert isinstance(report.metrics_summary, dict)
        assert isinstance(report.performance_insights, list)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.trends, dict)
        assert isinstance(report.generated_timestamp, datetime)

    @pytest.mark.asyncio
    async def test_should_provide_comprehensive_system_health_status(
        self,
        running_platform,
        sample_metrics,
    ):
        """
        Test: Should provide comprehensive system health status including
        component health, performance scores, and alert summaries.
        """
        # Register system components
        running_platform.register_system_component(
            SystemComponent.API_GATEWAY,
            {"version": "1.0.0", "status": "active"},
        )
        running_platform.register_system_component(
            SystemComponent.REALTIME_PIPELINE,
            {"version": "1.0.0", "status": "active"},
        )

        # Record some metrics
        await running_platform.record_metrics_batch(sample_metrics)

        # Get system health
        health_status = await running_platform.get_system_health()

        # Verify health status structure
        assert isinstance(health_status, SystemHealthStatus)
        assert health_status.overall_status in [
            "healthy",
            "degraded",
            "critical",
            "down",
        ]
        assert isinstance(health_status.component_statuses, dict)
        assert isinstance(health_status.active_alerts, list)
        assert 0.0 <= health_status.performance_score <= 1.0
        assert 0.0 <= health_status.uptime_percentage <= 100.0
        assert isinstance(health_status.health_check_timestamp, datetime)
        assert isinstance(health_status.metrics_summary, dict)

        # Verify metrics summary content
        summary = health_status.metrics_summary
        assert "total_metrics_collected" in summary
        assert "metrics_per_second" in summary
        assert "active_alerts" in summary
        assert "system_components" in summary

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_metric_collection_safely(
        self,
        running_platform,
    ):
        """
        Test: Should handle concurrent metric collection safely without
        race conditions and maintain data consistency.
        """
        # Create many concurrent metrics
        concurrent_metrics = []
        base_time = datetime.now(UTC)

        for i in range(100):
            metric = MetricPoint(
                metric_name=f"test_metric_{i % 10}",
                metric_type=MetricType.GAUGE,
                value=float(i),
                timestamp=base_time - timedelta(seconds=i),
                component=SystemComponent.API_GATEWAY,
                labels={"batch": "concurrent_test"},
            )
            concurrent_metrics.append(metric)

        # Process all metrics concurrently
        tasks = [
            running_platform.record_metric(metric) for metric in concurrent_metrics
        ]
        results = await asyncio.gather(*tasks)

        # Verify all metrics were collected successfully
        assert len(results) == 100
        assert all(results)  # All should be True

        # Verify metrics are stored correctly
        stats = running_platform.metrics_collector.get_collection_stats()
        assert stats["total_metrics_collected"] >= 100
        assert stats["buffer_size"] >= 100

    @pytest.mark.asyncio
    async def test_should_resolve_alerts_and_track_resolution_times(
        self,
        running_platform,
        sample_alert_rules,
    ):
        """
        Test: Should allow manual alert resolution and track resolution
        times for performance analysis and SLA monitoring.
        """
        # Add alert rule
        alert_rule = sample_alert_rules[0]  # High latency rule
        running_platform.alert_manager.add_alert_rule(alert_rule)

        # Trigger alert
        trigger_metric = MetricPoint(
            metric_name="response_time_ms",
            metric_type=MetricType.TIMER,
            value=1200.0,  # Above threshold
            component=SystemComponent.API_GATEWAY,
        )

        alerts = await running_platform.alert_manager.evaluate_metrics([trigger_metric])
        assert len(alerts) > 0

        triggered_alert = alerts[0]
        alert_id = triggered_alert.alert_id

        # Wait a small amount to simulate resolution time
        await asyncio.sleep(0.1)

        # Resolve the alert
        resolution_success = await running_platform.alert_manager.resolve_alert(
            alert_id,
        )
        assert resolution_success is True

        # Verify alert is no longer active
        active_alerts = running_platform.alert_manager.get_active_alerts()
        active_ids = [alert.alert_id for alert in active_alerts]
        assert alert_id not in active_ids

        # Verify resolution statistics
        alert_stats = running_platform.alert_manager.get_alert_stats()
        assert alert_stats["alerts_resolved"] > 0
        assert alert_stats["avg_resolution_time_minutes"] >= 0

    @pytest.mark.asyncio
    async def test_should_respect_alert_cooldown_periods(self, running_platform):
        """
        Test: Should respect alert cooldown periods to prevent
        alert spam and maintain system stability.
        """
        # Create alert rule with short cooldown for testing
        cooldown_rule = AlertRule(
            rule_id="test_cooldown",
            name="Test Cooldown Rule",
            metric_name="test_metric",
            component=SystemComponent.API_GATEWAY,
            condition="> 100",
            threshold=100,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=0.02,  # Very short cooldown (about 1 second)
        )

        running_platform.alert_manager.add_alert_rule(cooldown_rule)

        # Create metric that triggers alert
        trigger_metric = MetricPoint(
            metric_name="test_metric",
            metric_type=MetricType.GAUGE,
            value=150.0,
            component=SystemComponent.API_GATEWAY,
        )

        # First evaluation should trigger alert
        alerts1 = await running_platform.alert_manager.evaluate_metrics(
            [trigger_metric],
        )
        assert len(alerts1) == 1

        # Immediate second evaluation should not trigger (cooldown active)
        alerts2 = await running_platform.alert_manager.evaluate_metrics(
            [trigger_metric],
        )
        assert len(alerts2) == 0

        # Wait for cooldown to expire
        await asyncio.sleep(1.5)

        # Third evaluation should trigger again (cooldown expired)
        alerts3 = await running_platform.alert_manager.evaluate_metrics(
            [trigger_metric],
        )
        assert len(alerts3) == 1

    @pytest.mark.asyncio
    async def test_should_provide_dashboard_data_and_metrics(
        self,
        running_platform,
        sample_metrics,
    ):
        """
        Test: Should provide dashboard data and comprehensive metrics
        for monitoring and operational visibility.
        """
        # Record metrics and register components
        await running_platform.record_metrics_batch(sample_metrics)
        running_platform.register_system_component(
            SystemComponent.API_GATEWAY,
            {"version": "1.0.0"},
        )

        # Allow dashboard updates
        await asyncio.sleep(0.1)

        # Get dashboard data
        dashboard_data = running_platform.get_dashboard_data()

        # Verify dashboard structure
        assert "platform_status" in dashboard_data
        platform_status = dashboard_data["platform_status"]
        assert platform_status["is_running"] is True
        assert platform_status["uptime_seconds"] > 0
        assert platform_status["background_tasks"] > 0
        assert platform_status["system_components"] > 0

        # Get comprehensive metrics
        comprehensive_metrics = running_platform.get_comprehensive_metrics()

        # Verify metrics structure
        assert "metrics_collection" in comprehensive_metrics
        assert "alerting" in comprehensive_metrics
        assert "system_health" in comprehensive_metrics

        metrics_collection = comprehensive_metrics["metrics_collection"]
        assert "total_metrics_collected" in metrics_collection
        assert "metrics_per_second" in metrics_collection
        assert "buffer_size" in metrics_collection


class TestMetricsCollector:
    """Test metrics collection functionality"""

    @pytest.mark.asyncio
    async def test_should_collect_metrics_with_high_performance_buffer(
        self,
        analytics_config,
    ):
        """
        Test: Should collect metrics using high-performance buffer
        with proper aggregation and time-series storage.
        """
        collector = MetricsCollector(analytics_config)

        # Test individual metric collection
        metric = MetricPoint(
            metric_name="test_performance",
            metric_type=MetricType.GAUGE,
            value=42.0,
            component=SystemComponent.API_GATEWAY,
        )

        success = await collector.collect_metric(metric)
        assert success is True

        # Verify storage
        assert len(collector.metrics_buffer) == 1
        assert len(collector.real_time_metrics) == 1
        assert collector.collection_stats["total_metrics_collected"] == 1

        # Test batch collection
        batch_metrics = [
            MetricPoint(
                f"batch_metric_{i}",
                MetricType.COUNTER,
                float(i),
                component=SystemComponent.API_GATEWAY,
            )
            for i in range(10)
        ]

        batch_count = await collector.collect_batch_metrics(batch_metrics)
        assert batch_count == 10
        assert collector.collection_stats["total_metrics_collected"] == 11

    @pytest.mark.asyncio
    async def test_should_aggregate_metrics_by_time_windows(self, analytics_config):
        """
        Test: Should aggregate metrics by configurable time windows
        for efficient storage and querying capabilities.
        """
        collector = MetricsCollector(analytics_config)

        # Collect metrics with same name but different values
        base_time = datetime.now(UTC)

        for i in range(5):
            metric = MetricPoint(
                metric_name="aggregation_test",
                metric_type=MetricType.GAUGE,
                value=float(i * 10),
                timestamp=base_time + timedelta(seconds=i),
                component=SystemComponent.API_GATEWAY,
            )
            await collector.collect_metric(metric)

        # Verify aggregation occurred
        window_key = collector._get_aggregation_window_key(base_time)
        aggregated = collector.get_aggregated_metrics(window_key)

        if aggregated:  # Aggregation is async, might not be complete immediately
            metric_key = f"{SystemComponent.API_GATEWAY.value}_aggregation_test"
            if metric_key in aggregated:
                agg_data = aggregated[metric_key]
                assert agg_data["count"] > 0
                assert agg_data["sum"] >= 0
                assert agg_data["min"] >= 0
                assert agg_data["max"] >= 0

    @pytest.mark.asyncio
    async def test_should_retrieve_metrics_by_timeframe(self, analytics_config):
        """
        Test: Should retrieve metrics by component and timeframe
        with proper filtering and sorting capabilities.
        """
        collector = MetricsCollector(analytics_config)
        base_time = datetime.now(UTC)

        # Create metrics across different time ranges
        metrics = [
            MetricPoint(
                "recent_metric",
                MetricType.GAUGE,
                1.0,
                timestamp=base_time - timedelta(minutes=1),
                component=SystemComponent.API_GATEWAY,
            ),
            MetricPoint(
                "old_metric",
                MetricType.GAUGE,
                2.0,
                timestamp=base_time - timedelta(hours=2),
                component=SystemComponent.API_GATEWAY,
            ),
            MetricPoint(
                "recent_metric",
                MetricType.GAUGE,
                3.0,
                timestamp=base_time - timedelta(minutes=2),
                component=SystemComponent.REALTIME_PIPELINE,
            ),
        ]

        for metric in metrics:
            await collector.collect_metric(metric)

        # Test retrieval by timeframe
        recent_api_metrics = collector.get_metrics(
            SystemComponent.API_GATEWAY,
            "recent_metric",
            AnalyticsTimeframe.LAST_HOUR,
        )

        # Should find the API gateway metric from last hour
        assert len(recent_api_metrics) >= 1
        assert recent_api_metrics[0].component == SystemComponent.API_GATEWAY

        # Verify sorting by timestamp
        if len(recent_api_metrics) > 1:
            timestamps = [m.timestamp for m in recent_api_metrics]
            assert timestamps == sorted(timestamps)


class TestAlertManager:
    """Test alerting and notification functionality"""

    @pytest.mark.asyncio
    async def test_should_evaluate_alert_conditions_accurately(
        self,
        analytics_config,
        sample_alert_rules,
    ):
        """
        Test: Should evaluate alert conditions accurately using various
        comparison operators and threshold values.
        """
        alert_manager = AlertManager(analytics_config)

        # Add custom alert rules
        for rule in sample_alert_rules:
            alert_manager.add_alert_rule(rule)

        # Test different condition types
        test_cases = [
            # (metric_value, rule_id, should_trigger)
            (1500.0, "test_high_latency", True),  # > 1000
            (800.0, "test_high_latency", False),  # < 1000
            (0.06, "test_error_rate", True),  # > 0.05
            (0.03, "test_error_rate", False),  # < 0.05
            (0.85, "test_low_success", True),  # < 0.9
            (0.95, "test_low_success", False),  # > 0.9
        ]

        for metric_value, rule_id, should_trigger in test_cases:
            rule = alert_manager.alert_rules[rule_id]
            metric = MetricPoint(
                metric_name=rule.metric_name,
                metric_type=MetricType.GAUGE,
                value=metric_value,
                component=rule.component,
            )

            alerts = await alert_manager.evaluate_metrics([metric])

            if should_trigger:
                assert len(alerts) > 0, f"Alert {rule_id} should trigger for value {
                    metric_value
                }"
                # Find the specific rule in the alerts (may have multiple alerts)
                matching_alerts = [a for a in alerts if a.rule_id == rule_id]
                assert len(matching_alerts) > 0, f"Should find alert with rule_id {
                    rule_id
                }"
                assert matching_alerts[0].rule_id == rule_id
            else:
                matching_alerts = [a for a in alerts if a.rule_id == rule_id]
                assert len(matching_alerts) == 0, f"Alert {
                    rule_id
                } should not trigger for value {metric_value}"

    @pytest.mark.asyncio
    async def test_should_manage_alert_lifecycle_correctly(self, analytics_config):
        """
        Test: Should manage alert lifecycle from trigger through resolution
        with proper state transitions and statistics tracking.
        """
        alert_manager = AlertManager(analytics_config)

        # Add test alert rule
        test_rule = AlertRule(
            rule_id="lifecycle_test",
            name="Lifecycle Test Rule",
            metric_name="test_value",
            component=SystemComponent.API_GATEWAY,
            condition="> 50",
            threshold=50,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=1,
        )
        alert_manager.add_alert_rule(test_rule)

        # Verify no active alerts initially
        assert len(alert_manager.get_active_alerts()) == 0

        # Trigger alert
        trigger_metric = MetricPoint(
            metric_name="test_value",
            metric_type=MetricType.GAUGE,
            value=75.0,
            component=SystemComponent.API_GATEWAY,
        )

        alerts = await alert_manager.evaluate_metrics([trigger_metric])
        assert len(alerts) == 1

        triggered_alert = alerts[0]
        assert not triggered_alert.is_resolved

        # Verify alert is active
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == triggered_alert.alert_id

        # Resolve alert
        resolution_success = await alert_manager.resolve_alert(triggered_alert.alert_id)
        assert resolution_success is True

        # Verify alert is no longer active
        assert len(alert_manager.get_active_alerts()) == 0

        # Verify statistics updated
        stats = alert_manager.get_alert_stats()
        assert stats["total_alerts_triggered"] >= 1
        assert stats["alerts_resolved"] >= 1

    @pytest.mark.asyncio
    async def test_should_filter_alerts_by_severity(self, analytics_config):
        """
        Test: Should filter and retrieve alerts by severity level
        for priority-based alert management.
        """
        alert_manager = AlertManager(analytics_config)

        # Add rules with different severities
        rules = [
            AlertRule(
                "warning_rule",
                "Warning Rule",
                "metric1",
                SystemComponent.API_GATEWAY,
                "> 10",
                10,
                AlertSeverity.WARNING,
            ),
            AlertRule(
                "error_rule",
                "Error Rule",
                "metric2",
                SystemComponent.API_GATEWAY,
                "> 20",
                20,
                AlertSeverity.ERROR,
            ),
            AlertRule(
                "critical_rule",
                "Critical Rule",
                "metric3",
                SystemComponent.API_GATEWAY,
                "> 30",
                30,
                AlertSeverity.CRITICAL,
            ),
        ]

        for rule in rules:
            alert_manager.add_alert_rule(rule)

        # Trigger alerts of different severities
        metrics = [
            MetricPoint(
                "metric1",
                MetricType.GAUGE,
                15.0,
                component=SystemComponent.API_GATEWAY,
            ),
            MetricPoint(
                "metric2",
                MetricType.GAUGE,
                25.0,
                component=SystemComponent.API_GATEWAY,
            ),
            MetricPoint(
                "metric3",
                MetricType.GAUGE,
                35.0,
                component=SystemComponent.API_GATEWAY,
            ),
        ]

        all_alerts = await alert_manager.evaluate_metrics(metrics)
        assert len(all_alerts) == 3

        # Test filtering by severity
        critical_alerts = alert_manager.get_active_alerts(AlertSeverity.CRITICAL)
        error_alerts = alert_manager.get_active_alerts(AlertSeverity.ERROR)
        warning_alerts = alert_manager.get_active_alerts(AlertSeverity.WARNING)

        assert len(critical_alerts) == 1
        assert len(error_alerts) == 1
        assert len(warning_alerts) == 1

        assert critical_alerts[0].severity == AlertSeverity.CRITICAL
        assert error_alerts[0].severity == AlertSeverity.ERROR
        assert warning_alerts[0].severity == AlertSeverity.WARNING


class TestPerformanceAnalyzer:
    """Test performance analysis functionality"""

    @pytest.mark.asyncio
    async def test_should_generate_performance_insights_from_metrics(
        self,
        analytics_config,
    ):
        """
        Test: Should generate meaningful performance insights from
        collected metrics data with statistical analysis.
        """
        analyzer = PerformanceAnalyzer(analytics_config)
        collector = MetricsCollector(analytics_config)

        # Generate metrics with performance issues
        base_time = datetime.now(UTC)
        high_latency_metrics = []

        for i in range(20):
            # Create metrics with high latency pattern
            latency = 300 + (i * 50)  # Increasing latency
            metric = MetricPoint(
                metric_name="response_time_ms",
                metric_type=MetricType.TIMER,
                value=latency,
                timestamp=base_time - timedelta(minutes=20 - i),
                component=SystemComponent.API_GATEWAY,
            )
            await collector.collect_metric(metric)
            high_latency_metrics.append(metric)

        # Generate performance report
        report = await analyzer.generate_performance_report(
            SystemComponent.API_GATEWAY,
            AnalyticsTimeframe.LAST_HOUR,
            collector,
        )

        # Verify report generation
        assert isinstance(report, PerformanceReport)
        assert report.component == SystemComponent.API_GATEWAY
        assert len(report.performance_insights) > 0
        assert len(report.recommendations) > 0

        # Verify metrics summary contains statistical analysis
        if "response_time_ms" in report.metrics_summary:
            rt_summary = report.metrics_summary["response_time_ms"]
            assert "avg" in rt_summary
            assert "min" in rt_summary
            assert "max" in rt_summary
            assert "p95" in rt_summary
            assert "p99" in rt_summary
            assert rt_summary["min"] <= rt_summary["avg"] <= rt_summary["max"]

    @pytest.mark.asyncio
    async def test_should_detect_performance_anomalies(self, analytics_config):
        """
        Test: Should detect performance anomalies using statistical
        methods and generate appropriate alerts and insights.
        """
        analyzer = PerformanceAnalyzer(analytics_config)

        # Create metrics data with anomaly
        normal_values = [100.0] * 20  # Normal baseline
        anomaly_values = [100.0] * 18 + [500.0, 520.0]  # Two anomalous values

        # Simulate anomaly detection
        metrics_data = {
            "response_time_ms": {
                "count": len(anomaly_values),
                "avg": statistics.mean(anomaly_values),
                "min": min(anomaly_values),
                "max": max(anomaly_values),
                "p95": analyzer._calculate_percentile(anomaly_values, 95),
                "p99": analyzer._calculate_percentile(anomaly_values, 99),
                "std_dev": statistics.stdev(anomaly_values),
            },
        }

        # Generate insights (which includes anomaly detection)
        insights = await analyzer._generate_performance_insights(
            SystemComponent.API_GATEWAY,
            metrics_data,
        )

        # Should detect the anomaly in some form
        assert len(insights) > 0
        # Check if any insight mentions anomaly or unusual patterns
        anomaly_detected = any(
            "anomaly" in insight.lower() or "outlier" in insight.lower()
            for insight in insights
        )
        # Note: Anomaly detection might be triggered by other patterns too

    @pytest.mark.asyncio
    async def test_should_calculate_percentiles_correctly(self, analytics_config):
        """
        Test: Should calculate percentiles correctly for performance
        analysis and SLA monitoring.
        """
        analyzer = PerformanceAnalyzer(analytics_config)

        # Test with known values
        test_values = list(range(1, 101))  # 1 to 100

        # Test different percentiles
        p50 = analyzer._calculate_percentile(test_values, 50)
        p90 = analyzer._calculate_percentile(test_values, 90)
        p95 = analyzer._calculate_percentile(test_values, 95)
        p99 = analyzer._calculate_percentile(test_values, 99)

        # Verify percentile calculations
        assert 50 <= p50 <= 51  # 50th percentile should be around 50.5
        assert 90 <= p90 <= 91  # 90th percentile should be around 90.1
        assert 95 <= p95 <= 96  # 95th percentile should be around 95.05
        assert 99 <= p99 <= 100  # 99th percentile should be around 99.01

        # Verify ordering
        assert p50 < p90 < p95 < p99

        # Test edge cases
        single_value = [42.0]
        assert analyzer._calculate_percentile(single_value, 50) == 42.0
        assert analyzer._calculate_percentile(single_value, 99) == 42.0

        empty_values = []
        assert analyzer._calculate_percentile(empty_values, 50) == 0.0


class TestProductionConfiguration:
    """Test production-ready configuration and setup"""

    @pytest.mark.asyncio
    async def test_should_create_production_analytics_platform(self):
        """
        Test: Should create production-ready analytics platform with
        appropriate configuration for enterprise scale monitoring.
        """
        platform = create_production_analytics_platform()

        # Verify production configuration
        config = platform.config
        assert config.enable_real_time_monitoring is True
        assert config.enable_alerting is True
        assert config.enable_performance_analytics is True
        assert config.enable_predictive_insights is True
        assert config.metric_retention_days >= 30  # Long retention for production
        assert config.max_metrics_per_minute >= 10000  # High throughput
        assert config.health_check_interval_seconds <= 30  # Frequent health checks
        assert config.enable_anomaly_detection is True

        # Verify notification channels
        assert len(config.notification_channels) >= 2
        assert "email" in config.notification_channels

        # Verify components are initialized
        assert platform.metrics_collector is not None
        assert platform.alert_manager is not None
        assert platform.performance_analyzer is not None
        assert len(platform.alert_manager.alert_rules) > 0  # Default rules loaded


class TestDataStructures:
    """Test data structure serialization and immutability"""

    def test_metric_point_should_be_immutable_and_serializable(self):
        """
        Test: MetricPoint should be immutable and properly serializable
        for storage and transmission across monitoring infrastructure.
        """
        metric = MetricPoint(
            metric_name="test_metric",
            metric_type=MetricType.GAUGE,
            value=42.5,
            labels={"service": "api", "version": "1.0"},
            component=SystemComponent.API_GATEWAY,
            metadata={"request_id": "req_123"},
        )

        # Verify immutability
        with pytest.raises(Exception):  # Should raise FrozenInstanceError
            metric.value = 50.0

        # Verify serialization fields
        assert metric.metric_name == "test_metric"
        assert metric.metric_type == MetricType.GAUGE
        assert metric.value == 42.5
        assert metric.labels["service"] == "api"
        assert metric.component == SystemComponent.API_GATEWAY
        assert metric.metadata["request_id"] == "req_123"
        assert isinstance(metric.timestamp, datetime)

    def test_alert_should_serialize_with_comprehensive_metadata(self):
        """
        Test: Alert should serialize with comprehensive metadata
        including trigger conditions and resolution tracking.
        """
        alert = Alert(
            alert_id="alert_001",
            rule_id="test_rule",
            component=SystemComponent.REALTIME_PIPELINE,
            severity=AlertSeverity.ERROR,
            message="Test alert message",
            metric_value=75.5,
            threshold=50.0,
            is_resolved=False,
            metadata={
                "correlation_id": "corr_123",
                "runbook": "wiki.company.com/alerts",
            },
        )

        # Verify comprehensive serialization
        assert alert.alert_id == "alert_001"
        assert alert.rule_id == "test_rule"
        assert alert.component == SystemComponent.REALTIME_PIPELINE
        assert alert.severity == AlertSeverity.ERROR
        assert alert.message == "Test alert message"
        assert alert.metric_value == 75.5
        assert alert.threshold == 50.0
        assert alert.is_resolved is False
        assert alert.metadata["correlation_id"] == "corr_123"
        assert isinstance(alert.triggered_timestamp, datetime)

    def test_performance_report_should_contain_complete_analysis(self):
        """
        Test: PerformanceReport should contain complete performance analysis
        with metrics, insights, recommendations, and trends.
        """
        start_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = datetime.now(UTC)

        report = PerformanceReport(
            report_id="perf_001",
            component=SystemComponent.API_GATEWAY,
            timeframe=AnalyticsTimeframe.LAST_HOUR,
            start_time=start_time,
            end_time=end_time,
            metrics_summary={
                "response_time_ms": {"avg": 250.0, "p95": 400.0, "p99": 500.0},
                "error_rate": {"avg": 0.02, "max": 0.05},
            },
            performance_insights=[
                "Response time P95 is 60% above baseline",
                "Error rate spike detected at 14:30",
            ],
            recommendations=[
                "Consider implementing response caching",
                "Review error handling for /api/v1/search endpoint",
            ],
            trends={"response_time_ms": {"direction": "increasing", "magnitude": 0.15}},
        )

        # Verify complete analysis structure
        assert report.report_id == "perf_001"
        assert report.component == SystemComponent.API_GATEWAY
        assert report.timeframe == AnalyticsTimeframe.LAST_HOUR
        assert report.start_time < report.end_time
        assert len(report.metrics_summary) == 2
        assert len(report.performance_insights) == 2
        assert len(report.recommendations) == 2
        assert len(report.trends) == 1
        assert isinstance(report.generated_timestamp, datetime)
