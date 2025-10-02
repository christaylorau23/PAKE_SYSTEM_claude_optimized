"""
TDD Monitoring Integration Tests
Test-Driven Development for Prometheus, Grafana, and Jaeger integration
"""

import json
from pathlib import Path

import pytest
import yaml


class TestMonitoringIntegrationTDD:
    """Test-Driven Development for monitoring components"""

    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.monitoring_dir = self.project_root / "monitoring"
        self.prometheus_dir = self.monitoring_dir / "prometheus"
        self.grafana_dir = self.monitoring_dir / "grafana"
        self.jaeger_dir = self.monitoring_dir / "jaeger"

    def test_prometheus_configuration_structure(self):
        """TDD: Test Prometheus configuration has proper structure"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act & Assert
        assert (
            prometheus_config_path.exists()
        ), "Should have prometheus.yml configuration"

        with open(prometheus_config_path) as f:
            content = f.read()

        assert len(content) > 1000, "Prometheus config should be comprehensive"

    def test_prometheus_global_configuration(self):
        """TDD: Test Prometheus global configuration"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act
        with open(prometheus_config_path) as f:
            content = f.read()

        # Assert
        assert "global:" in content, "Should have global configuration"
        assert "scrape_interval:" in content, "Should define scrape interval"
        assert "evaluation_interval:" in content, "Should define evaluation interval"
        assert "external_labels:" in content, "Should have external labels"

    def test_prometheus_scrape_configs(self):
        """TDD: Test Prometheus scrape configurations"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act
        with open(prometheus_config_path) as f:
            content = f.read()

        # Assert
        assert "scrape_configs:" in content, "Should have scrape configurations"

        # Check for key job configurations
        required_jobs = [
            "job_name: 'prometheus'",
            "job_name: 'pake-system'",
            "job_name: 'kubernetes-apiservers'",
            "job_name: 'kubernetes-nodes'",
            "job_name: 'kubernetes-cadvisor'",
            "job_name: 'postgresql'",
            "job_name: 'redis'",
        ]

        for job in required_jobs:
            assert job in content, f"Should have {job} configuration"

    def test_prometheus_kubernetes_integration(self):
        """TDD: Test Prometheus Kubernetes integration"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act
        with open(prometheus_config_path) as f:
            content = f.read()

        # Assert
        assert (
            "kubernetes_sd_configs:" in content
        ), "Should have Kubernetes service discovery"
        assert "role: endpoints" in content, "Should discover endpoints"
        assert "role: node" in content, "Should discover nodes"
        assert "relabel_configs:" in content, "Should have relabeling configuration"

    def test_prometheus_alerting_configuration(self):
        """TDD: Test Prometheus alerting configuration"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act
        with open(prometheus_config_path) as f:
            content = f.read()

        # Assert
        assert "alerting:" in content, "Should have alerting configuration"
        assert "alertmanagers:" in content, "Should configure Alertmanager"
        assert "rule_files:" in content, "Should have rule files configuration"

    def test_prometheus_alerting_rules(self):
        """TDD: Test Prometheus alerting rules"""
        # Arrange
        rules_dir = self.prometheus_dir / "rules"
        pake_rules_path = rules_dir / "pake-system.yml"

        # Act & Assert
        assert rules_dir.exists(), "Should have rules directory"
        assert pake_rules_path.exists(), "Should have PAKE system rules"

        with open(pake_rules_path) as f:
            rules_content = f.read()

        assert "groups:" in rules_content, "Should have rule groups"
        assert (
            "pake-system.rules" in rules_content
        ), "Should have PAKE system rules group"
        assert (
            "alert: PAKESystemHighErrorRate" in rules_content
        ), "Should have error rate alert"
        assert (
            "alert: PAKESystemHighResponseTime" in rules_content
        ), "Should have response time alert"
        assert "alert: PAKESystemPodDown" in rules_content, "Should have pod down alert"

    def test_grafana_dashboard_structure(self):
        """TDD: Test Grafana dashboard structure"""
        # Arrange
        dashboards_dir = self.grafana_dir / "dashboards"
        overview_dashboard_path = dashboards_dir / "pake-system-overview.json"

        # Act & Assert
        assert dashboards_dir.exists(), "Should have dashboards directory"
        assert overview_dashboard_path.exists(), "Should have overview dashboard"

        with open(overview_dashboard_path) as f:
            dashboard_data = json.load(f)

        assert "dashboard" in dashboard_data, "Should have dashboard structure"

    def test_grafana_dashboard_metadata(self):
        """TDD: Test Grafana dashboard metadata"""
        # Arrange
        overview_dashboard_path = (
            self.grafana_dir / "dashboards" / "pake-system-overview.json"
        )

        # Act
        with open(overview_dashboard_path) as f:
            dashboard_data = json.load(f)

        # Assert
        dashboard = dashboard_data["dashboard"]

        assert dashboard["title"] == "PAKE System Overview", "Should have correct title"
        assert "pake-system" in dashboard["tags"], "Should have correct tags"
        assert dashboard["style"] == "dark", "Should use dark theme"

    def test_grafana_dashboard_panels(self):
        """TDD: Test Grafana dashboard panels"""
        # Arrange
        overview_dashboard_path = (
            self.grafana_dir / "dashboards" / "pake-system-overview.json"
        )

        # Act
        with open(overview_dashboard_path) as f:
            dashboard_data = json.load(f)

        # Assert
        panels = dashboard_data["dashboard"]["panels"]
        assert len(panels) > 5, "Should have multiple panels"

        # Check for key metric panels
        panel_titles = [panel.get("title", "") for panel in panels]

        required_panels = [
            "Request Rate",
            "Response Time",
            "Error Rate",
            "CPU Usage",
            "Memory Usage",
        ]

        for panel_title in required_panels:
            assert any(
                panel_title in title for title in panel_titles
            ), f"Should have {panel_title} panel"

    def test_grafana_dashboard_queries(self):
        """TDD: Test Grafana dashboard queries"""
        # Arrange
        overview_dashboard_path = (
            self.grafana_dir / "dashboards" / "pake-system-overview.json"
        )

        # Act
        with open(overview_dashboard_path) as f:
            dashboard_data = json.load(f)

        # Assert
        panels = dashboard_data["dashboard"]["panels"]

        # Check for Prometheus queries
        has_prometheus_queries = False
        for panel in panels:
            if "targets" in panel:
                for target in panel["targets"]:
                    if "expr" in target and "rate(" in target["expr"]:
                        has_prometheus_queries = True
                        break

        assert has_prometheus_queries, "Should have Prometheus queries"

    def test_jaeger_configuration_structure(self):
        """TDD: Test Jaeger configuration structure"""
        # Arrange
        jaeger_config_path = self.jaeger_dir / "jaeger-config.yaml"

        # Act & Assert
        assert jaeger_config_path.exists(), "Should have Jaeger configuration"

        with open(jaeger_config_path) as f:
            jaeger_data = yaml.safe_load(f)

        assert "apiVersion" in jaeger_data, "Should be Kubernetes ConfigMap"
        assert jaeger_data["kind"] == "ConfigMap", "Should be ConfigMap resource"
        assert "data" in jaeger_data, "Should have data section"

    def test_jaeger_yaml_configuration(self):
        """TDD: Test Jaeger YAML configuration"""
        # Arrange
        jaeger_config_path = self.jaeger_dir / "jaeger-config.yaml"

        # Act
        with open(jaeger_config_path) as f:
            jaeger_data = yaml.safe_load(f)

        # Assert
        jaeger_yaml = jaeger_data["data"]["jaeger.yaml"]

        assert "service:" in jaeger_yaml, "Should have service configuration"
        assert "sampling:" in jaeger_yaml, "Should have sampling configuration"
        assert "storage:" in jaeger_yaml, "Should have storage configuration"
        assert "query:" in jaeger_yaml, "Should have query configuration"

    def test_jaeger_storage_configuration(self):
        """TDD: Test Jaeger storage configuration"""
        # Arrange
        jaeger_config_path = self.jaeger_dir / "jaeger-config.yaml"

        # Act
        with open(jaeger_config_path) as f:
            jaeger_data = yaml.safe_load(f)

        # Assert
        jaeger_yaml = jaeger_data["data"]["jaeger.yaml"]

        assert "type: elasticsearch" in jaeger_yaml, "Should use Elasticsearch storage"
        assert (
            "elasticsearch:" in jaeger_yaml
        ), "Should have Elasticsearch configuration"
        assert "serverURLs:" in jaeger_yaml, "Should have server URLs"

    def test_jaeger_sampling_configuration(self):
        """TDD: Test Jaeger sampling configuration"""
        # Arrange
        jaeger_config_path = self.jaeger_dir / "jaeger-config.yaml"

        # Act
        with open(jaeger_config_path) as f:
            jaeger_data = yaml.safe_load(f)

        # Assert
        jaeger_yaml = jaeger_data["data"]["jaeger.yaml"]

        assert "type: const" in jaeger_yaml, "Should use constant sampling"
        assert "param: 1" in jaeger_yaml, "Should sample 100% of traces"

    def test_monitoring_integration_completeness(self):
        """TDD: Test monitoring integration completeness"""
        # Arrange
        required_files = [
            "prometheus/prometheus.yml",
            "prometheus/rules/pake-system.yml",
            "grafana/dashboards/pake-system-overview.json",
            "jaeger/jaeger-config.yaml",
        ]

        # Act & Assert
        for file_path in required_files:
            full_path = self.monitoring_dir / file_path
            assert full_path.exists(), f"Should have {file_path}"

            # Check file is not empty
            assert (
                full_path.stat().st_size > 100
            ), f"{file_path} should have substantial content"

    def test_monitoring_kubernetes_integration(self):
        """TDD: Test monitoring Kubernetes integration"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act
        with open(prometheus_config_path) as f:
            content = f.read()

        # Assert
        # Check for Kubernetes-specific configurations
        kubernetes_configs = [
            "kubernetes_sd_configs",
            "kubernetes-apiservers",
            "kubernetes-nodes",
            "kubernetes-cadvisor",
            "kubernetes-service-endpoints",
        ]

        for config in kubernetes_configs:
            assert config in content, f"Should have {config} configuration"

    def test_monitoring_application_integration(self):
        """TDD: Test monitoring application integration"""
        # Arrange
        prometheus_config_path = self.prometheus_dir / "prometheus.yml"

        # Act
        with open(prometheus_config_path) as f:
            content = f.read()

        # Assert
        # Check for application-specific configurations
        app_configs = [
            "job_name: 'pake-system'",
            "http_requests_total",
            "http_request_duration_seconds",
            "database_connections_active",
            "redis_hits_total",
        ]

        for config in app_configs:
            assert config in content, f"Should have {config} configuration"

    def test_monitoring_alerting_integration(self):
        """TDD: Test monitoring alerting integration"""
        # Arrange
        rules_path = self.prometheus_dir / "rules" / "pake-system.yml"

        # Act
        with open(rules_path) as f:
            content = f.read()

        # Assert
        # Check for comprehensive alerting rules
        alert_categories = [
            "PAKESystemHighErrorRate",
            "PAKESystemHighResponseTime",
            "PAKESystemHighCPUUsage",
            "PAKESystemHighMemoryUsage",
            "PAKESystemPodDown",
            "PAKESystemDatabaseConnectionIssues",
            "PAKESystemRedisConnectionIssues",
            "PAKESystemSLABreach",
        ]

        for alert in alert_categories:
            assert f"alert: {alert}" in content, f"Should have {alert} alert"

    def test_monitoring_dashboard_integration(self):
        """TDD: Test monitoring dashboard integration"""
        # Arrange
        dashboard_path = self.grafana_dir / "dashboards" / "pake-system-overview.json"

        # Act
        with open(dashboard_path) as f:
            dashboard_data = json.load(f)

        # Assert
        panels = dashboard_data["dashboard"]["panels"]

        # Check for comprehensive monitoring coverage
        monitoring_metrics = [
            "http_requests_total",
            "http_request_duration_seconds",
            "container_cpu_usage_seconds_total",
            "container_memory_usage_bytes",
            "database_connections_active",
            "redis_hits_total",
        ]

        dashboard_content = json.dumps(dashboard_data)
        for metric in monitoring_metrics:
            assert metric in dashboard_content, f"Dashboard should include {metric}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
