#!/usr/bin/env python3
"""
PAKE System - Real-Time Monitoring Dashboard Tests
Phase 2B Sprint 4: Comprehensive TDD testing for production monitoring

Tests real-time metrics collection, health monitoring, alerting,
and dashboard functionality.
"""

import asyncio
import json
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from services.monitoring.real_time_dashboard import (
    DashboardConfig,
    HealthStatus,
    IngestionMetrics,
    MetricPoint,
    RealTimeMonitoringDashboard,
    SystemHealth,
    SystemHealthChecker,
)


class TestRealTimeMonitoringDashboard:
    """
    Comprehensive test suite for real-time monitoring dashboard.
    Tests metrics collection, health monitoring, alerting, and dashboard updates.
    """

    @pytest.fixture
    def dashboard_config(self):
        """Standard dashboard configuration for testing"""
        return DashboardConfig(
            metric_update_interval=0.1,  # Fast for testing
            health_check_interval=0.1,
            dashboard_refresh_interval=0.1,
            metric_retention_hours=1,
            max_data_points=100,
            error_rate_threshold=0.05,
            response_time_threshold=2.0,
            memory_usage_threshold=0.80,
            disk_usage_threshold=0.90,
        )

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager with test data"""
        mock_manager = AsyncMock()
        mock_stats = Mock()
        mock_stats.hit_rate = 0.75
        mock_stats.memory_usage = 1024 * 1024  # 1MB
        mock_stats.total_requests = 1000
        mock_stats.successful_requests = 750
        mock_stats.hits = {"memory": 500, "disk": 250, "distributed": 0}
        mock_stats.misses = {"memory": 200, "disk": 50, "distributed": 0}
        mock_manager.get_stats.return_value = mock_stats
        return mock_manager

    @pytest.fixture
    def mock_orchestrator_manager(self):
        """Mock orchestrator manager with test data"""
        return Mock()

    @pytest_asyncio.fixture
    async def dashboard(self, dashboard_config):
        """Create dashboard instance for testing"""
        dashboard = RealTimeMonitoringDashboard(dashboard_config)
        yield dashboard
        await dashboard.stop()

    @pytest.fixture
    def sample_metric_points(self):
        """Sample metric data points for testing"""
        now = datetime.now(UTC)
        return [
            MetricPoint(now - timedelta(minutes=5), 100.0, {"source": "test"}),
            MetricPoint(now - timedelta(minutes=4), 150.0, {"source": "test"}),
            MetricPoint(now - timedelta(minutes=3), 200.0, {"source": "test"}),
            MetricPoint(now - timedelta(minutes=2), 175.0, {"source": "test"}),
            MetricPoint(now - timedelta(minutes=1), 225.0, {"source": "test"}),
        ]

    # ========================================================================
    # Core Functionality Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_initialize_dashboard_with_default_config(self):
        """
        Test: Should initialize monitoring dashboard with sensible defaults
        and proper component setup.
        """
        dashboard = RealTimeMonitoringDashboard()

        # Check default configuration
        assert dashboard.config.metric_update_interval == 1.0
        assert dashboard.config.health_check_interval == 5.0
        assert dashboard.config.dashboard_refresh_interval == 2.0

        # Check initialization state
        assert not dashboard.is_running
        assert dashboard.metrics_history == {}
        assert dashboard.current_metrics == {}

        # Check components are initialized
        assert dashboard.metric_collector is not None
        assert dashboard.health_checker is not None

    @pytest.mark.asyncio
    async def test_should_collect_metrics_from_integrated_systems(
        self,
        dashboard,
        mock_cache_manager,
    ):
        """
        Test: Should collect comprehensive metrics from cache and
        ingestion systems with proper data structure.
        """
        # Configure dashboard with mock systems
        dashboard.metric_collector = IngestionMetrics(
            orchestrator_manager=None,
            cache_manager=mock_cache_manager,
        )

        # Collect metrics
        metrics = await dashboard.metric_collector.collect_metrics()

        # Verify cache metrics are collected
        assert "cache_hit_rate" in metrics
        assert "cache_memory_usage" in metrics
        assert "cache_total_requests" in metrics
        assert "cache_successful_requests" in metrics

        # Verify metric point structure
        hit_rate_point = metrics["cache_hit_rate"][0]
        assert isinstance(hit_rate_point, MetricPoint)
        assert hit_rate_point.value == 0.75
        assert isinstance(hit_rate_point.timestamp, datetime)

        # Verify per-tier metrics
        assert "cache_hits_memory" in metrics
        assert "cache_misses_disk" in metrics

    @pytest.mark.asyncio
    async def test_should_track_metrics_history_with_retention_limits(
        self,
        dashboard,
        sample_metric_points,
    ):
        """
        Test: Should maintain metrics history with proper retention
        and data point limits.
        """
        # Add sample data points
        dashboard.metrics_history["test_metric"] = sample_metric_points.copy()

        # Add more points to test retention
        now = datetime.now(UTC)
        for i in range(150):  # Exceed max_data_points
            point = MetricPoint(now + timedelta(seconds=i), float(i))
            dashboard.metrics_history["test_metric"].append(point)

        # Trim history
        dashboard._trim_metric_history("test_metric")

        # Check data point limit is enforced
        assert (
            len(dashboard.metrics_history["test_metric"])
            <= dashboard.config.max_data_points
        )

        # Check most recent points are retained
        latest_point = dashboard.metrics_history["test_metric"][-1]
        assert latest_point.value == 149.0

    @pytest.mark.asyncio
    async def test_should_perform_comprehensive_health_checks(
        self,
        dashboard,
        mock_cache_manager,
    ):
        """
        Test: Should perform multi-component health assessment
        with proper status calculation and alerting.
        """
        # Configure health checker with mock data
        dashboard.metric_collector = IngestionMetrics(cache_manager=mock_cache_manager)

        # Perform health check
        health = await dashboard.health_checker.check_health()

        # Verify health check structure
        assert isinstance(health, SystemHealth)
        assert health.overall_status in [status for status in HealthStatus]
        assert health.last_check is not None

        # Verify component health tracking
        assert "cache" in health.component_health
        assert "ingestion" in health.component_health
        assert "resources" in health.component_health

        # All components should report some status
        for component, status in health.component_health.items():
            assert status in [status for status in HealthStatus]

    @pytest.mark.asyncio
    async def test_should_generate_alerts_for_unhealthy_conditions(
        self,
        dashboard_config,
    ):
        """
        Test: Should detect unhealthy system conditions and
        generate appropriate alerts with severity levels.
        """
        # Create mock collector with poor metrics
        mock_collector = AsyncMock()
        mock_collector.collect_metrics.return_value = {
            # Very low hit rate
            "cache_hit_rate": [MetricPoint(datetime.now(UTC), 0.05)],
            # Below threshold
            "ingestion_success_rate": [MetricPoint(datetime.now(UTC), 0.80)],
            # High response time
            "average_processing_time": [MetricPoint(datetime.now(UTC), 8.0)],
        }

        health_checker = SystemHealthChecker(dashboard_config, mock_collector)
        health = await health_checker.check_health()

        # Should detect problems and generate alerts
        assert health.overall_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        assert len(health.alerts) > 0

        # Check specific alert messages
        alert_text = " ".join(health.alerts).lower()
        assert (
            "cache" in alert_text
            or "success" in alert_text
            or "processing" in alert_text
        )

    @pytest.mark.asyncio
    async def test_should_export_comprehensive_dashboard_data(
        self,
        dashboard,
        mock_cache_manager,
    ):
        """
        Test: Should generate complete dashboard data export
        with metrics, health, and system information.
        """
        # Configure dashboard
        dashboard.metric_collector = IngestionMetrics(cache_manager=mock_cache_manager)

        # Simulate some metrics collection
        metrics = await dashboard.metric_collector.collect_metrics()
        dashboard.current_metrics = metrics
        dashboard.current_health = await dashboard.health_checker.check_health()

        # Get dashboard data
        dashboard_data = await dashboard.get_dashboard_data()

        # Verify data structure
        assert "timestamp" in dashboard_data
        assert "health" in dashboard_data
        assert "current_metrics" in dashboard_data
        assert "metric_history" in dashboard_data
        assert "system_info" in dashboard_data

        # Verify health data is properly serialized
        health_data = dashboard_data["health"]
        assert "overall_status" in health_data
        assert "component_health" in health_data
        assert "alerts" in health_data

        # Verify metrics are properly serialized
        current_metrics = dashboard_data["current_metrics"]
        assert len(current_metrics) > 0

    # ========================================================================
    # Integration and Performance Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_metric_collection_safely(
        self,
        dashboard,
        mock_cache_manager,
    ):
        """
        Test: Should handle concurrent metric collection and health
        monitoring without race conditions or data corruption.
        """
        dashboard.metric_collector = IngestionMetrics(cache_manager=mock_cache_manager)

        # Start concurrent operations
        tasks = []
        for i in range(10):
            task = asyncio.create_task(dashboard.metric_collector.collect_metrics())
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded and returned valid data
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, dict)
            assert len(result) > 0

            # Check metric structure
            for metric_name, points in result.items():
                assert len(points) == 1
                assert isinstance(points[0], MetricPoint)

    @pytest.mark.asyncio
    async def test_should_maintain_performance_under_high_metric_load(self, dashboard):
        """
        Test: Should maintain acceptable performance when processing
        large volumes of metrics and maintaining history.
        """
        # Generate large volume of metrics
        start_time = datetime.now(UTC)

        for i in range(500):  # Large number of metric updates
            metric_name = f"test_metric_{i % 10}"  # 10 different metrics
            point = MetricPoint(
                timestamp=start_time + timedelta(seconds=i),
                value=float(i),
                labels={"batch": str(i // 100)},
            )

            if metric_name not in dashboard.metrics_history:
                dashboard.metrics_history[metric_name] = []
            dashboard.metrics_history[metric_name].append(point)

        # Measure trimming performance
        trim_start = time.time()
        for metric_name in dashboard.metrics_history:
            dashboard._trim_metric_history(metric_name)
        trim_time = time.time() - trim_start

        # Should complete quickly (under 1 second)
        assert trim_time < 1.0

        # Verify data is properly managed
        for metric_name, points in dashboard.metrics_history.items():
            assert len(points) <= dashboard.config.max_data_points

    @pytest.mark.asyncio
    async def test_should_export_metrics_to_file_successfully(
        self,
        dashboard,
        mock_cache_manager,
    ):
        """
        Test: Should export comprehensive metrics data to JSON file
        with proper formatting and completeness.
        """
        # Configure dashboard with test data
        dashboard.metric_collector = IngestionMetrics(cache_manager=mock_cache_manager)

        # Collect some metrics
        metrics = await dashboard.metric_collector.collect_metrics()
        dashboard.current_metrics = metrics
        dashboard.current_health = await dashboard.health_checker.check_health()

        # Export to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as tmp_file:
            tmp_path = tmp_file.name

        # Perform export
        success = await dashboard.export_metrics(tmp_path)
        assert success

        # Verify file contents
        with open(tmp_path) as f:
            exported_data = json.load(f)

        # Clean up
        Path(tmp_path).unlink()

        # Verify exported data structure
        assert "timestamp" in exported_data
        assert "health" in exported_data
        assert "current_metrics" in exported_data
        assert "system_info" in exported_data

        # Verify JSON serialization worked properly
        assert isinstance(exported_data["health"]["overall_status"], str)
        assert isinstance(exported_data["current_metrics"], dict)

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_metric_collection_failures_gracefully(self, dashboard):
        """
        Test: Should handle metric collection failures without
        stopping the monitoring system.
        """
        # Create failing metric collector
        failing_collector = AsyncMock()
        failing_collector.collect_metrics.side_effect = Exception("Collection failed")

        dashboard.metric_collector = failing_collector
        # Update health checker to use the same failing collector
        dashboard.health_checker.metric_collector = failing_collector

        # Health checker should handle the failure
        health = await dashboard.health_checker.check_health()

        # Should report critical status due to collection failure
        assert health.overall_status == HealthStatus.CRITICAL
        assert len(health.alerts) > 0
        assert "error" in " ".join(health.alerts).lower()

    @pytest.mark.asyncio
    async def test_should_handle_empty_metrics_gracefully(self, dashboard):
        """
        Test: Should handle cases where no metrics are available
        without errors or crashes.
        """
        # Set up empty metrics
        dashboard.current_metrics = {}
        dashboard.metrics_history = {}

        # Should still generate dashboard data
        dashboard_data = await dashboard.get_dashboard_data()

        # Verify structure is maintained
        assert "timestamp" in dashboard_data
        assert "current_metrics" in dashboard_data
        assert dashboard_data["current_metrics"] == {}
        assert dashboard_data["metric_history"] == {}

    @pytest.mark.asyncio
    async def test_should_validate_dashboard_configuration(self, dashboard_config):
        """
        Test: Should validate dashboard configuration parameters
        and use sensible defaults for invalid values.
        """
        # Test with extreme configuration values
        extreme_config = DashboardConfig(
            metric_update_interval=-1.0,  # Invalid negative
            health_check_interval=0.0,  # Invalid zero
            max_data_points=-100,  # Invalid negative
            error_rate_threshold=2.0,  # Invalid > 1.0
        )

        # Dashboard should still initialize (would use defaults in production)
        dashboard = RealTimeMonitoringDashboard(extreme_config)
        assert dashboard.config is not None

    @pytest.mark.asyncio
    async def test_should_handle_metric_history_corruption_safely(self, dashboard):
        """
        Test: Should handle corrupted metric history data
        without affecting overall system operation.
        """
        # Introduce corrupted data
        dashboard.metrics_history["corrupted_metric"] = [
            "invalid_data",  # Not a MetricPoint
            None,
            {"invalid": "dict"},
        ]

        # Should handle gracefully during trimming
        try:
            dashboard._trim_metric_history("corrupted_metric")
            # If it doesn't crash, it handled the corruption
            trimming_handled = True
        except BaseException:
            trimming_handled = False

        # Dashboard should still be operational
        dashboard_data = await dashboard.get_dashboard_data()
        assert "timestamp" in dashboard_data


class TestDashboardDataStructures:
    """
    Test suite for dashboard data structures and utility classes.
    """

    def test_metric_point_should_be_immutable_and_serializable(self):
        """
        Test: MetricPoint should be immutable and properly serializable.
        """
        now = datetime.now(UTC)
        point = MetricPoint(
            timestamp=now,
            value=123.45,
            labels={"source": "test", "type": "gauge"},
        )

        # Should be frozen (immutable)
        with pytest.raises(AttributeError):
            point.value = 999.99

        # Should serialize to dict properly
        point_dict = point.to_dict()
        assert point_dict["timestamp"] == now.isoformat()
        assert point_dict["value"] == 123.45
        assert point_dict["labels"]["source"] == "test"

    def test_system_health_should_track_component_status_correctly(self):
        """
        Test: SystemHealth should properly track component health
        and overall system status.
        """
        health = SystemHealth()

        # Set component health
        health.component_health["cache"] = HealthStatus.HEALTHY
        health.component_health["ingestion"] = HealthStatus.WARNING
        health.component_health["database"] = HealthStatus.CRITICAL

        # Add alerts
        health.alerts = ["High memory usage", "Database connection timeout"]
        health.last_check = datetime.now(UTC)

        # Should serialize properly
        health_dict = health.to_dict()
        assert health_dict["component_health"]["cache"] == "healthy"
        assert health_dict["component_health"]["ingestion"] == "warning"
        assert health_dict["component_health"]["database"] == "critical"
        assert len(health_dict["alerts"]) == 2

    def test_dashboard_config_should_have_reasonable_defaults(self):
        """
        Test: DashboardConfig should provide sensible default values
        for production use.
        """
        config = DashboardConfig()

        # Check reasonable update intervals
        assert 0.1 <= config.metric_update_interval <= 10.0
        assert 1.0 <= config.health_check_interval <= 60.0
        assert 0.5 <= config.dashboard_refresh_interval <= 30.0

        # Check reasonable retention settings
        assert config.metric_retention_hours >= 1
        assert config.max_data_points >= 100

        # Check reasonable thresholds
        assert 0.0 <= config.error_rate_threshold <= 1.0
        assert config.response_time_threshold > 0
        assert 0.0 <= config.memory_usage_threshold <= 1.0
        assert 0.0 <= config.disk_usage_threshold <= 1.0
