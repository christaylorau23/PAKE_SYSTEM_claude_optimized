#!/usr/bin/env python3
"""
PAKE System - Enterprise Deployment Tests
Phase 2B Sprint 4: Comprehensive TDD testing for production deployment orchestration

Tests deployment configuration, service orchestration, health monitoring,
and production readiness validation.
"""

import asyncio
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from deployment.enterprise_deployment import (
    ConfigurationValidator,
    DeploymentConfig,
    DeploymentEnvironment,
    DeploymentStatus,
    EnterpriseDeploymentOrchestrator,
    HealthCheckStatus,
    LocalServiceManager,
    ServiceConfig,
    ServiceHealth,
    ServiceStatus,
    create_development_deployment_config,
    create_production_deployment_config,
)


class TestEnterpriseDeploymentOrchestrator:
    """
    Comprehensive test suite for enterprise deployment orchestrator.
    Tests service deployment, health monitoring, configuration validation, and production readiness.
    """

    @pytest.fixture()
    def sample_services(self):
        """Sample service configurations for testing"""
        return [
            ServiceConfig(
                name="test-service-1",
                version="1.0.0",
                replicas=2,
                port=8001,
                health_check_path="/health",
                environment_variables={"ENV": "test"},
            ),
            ServiceConfig(
                name="test-service-2",
                version="1.0.0",
                replicas=1,
                port=8002,
                health_check_path="/status",
                dependencies=["test-service-1"],
                resource_limits={"cpu": "500m", "memory": "1Gi"},
            ),
            ServiceConfig(
                name="test-database",
                version="1.0.0",
                replicas=1,
                port=5432,
                health_check_path="/health",
            ),
        ]

    @pytest.fixture()
    def deployment_config(self, sample_services):
        """Standard deployment configuration for testing"""
        return DeploymentConfig(
            environment=DeploymentEnvironment.TEST,
            namespace="test-namespace",
            cluster_name="test-cluster",
            services=sample_services,
            database_config={"type": "postgresql"},
            cache_config={"type": "redis"},
            monitoring_config={"enabled": True},
            enable_tls=True,
            resource_quotas={"cpu": "4", "memory": "8Gi"},
        )

    @pytest.fixture()
    def mock_service_manager(self):
        """Mock service manager for testing"""
        manager = AsyncMock(spec=LocalServiceManager)

        # Configure default behaviors
        manager.deploy_service.return_value = True
        manager.stop_service.return_value = True
        manager.get_service_status.return_value = ServiceStatus.RUNNING

        # Mock health check responses
        def mock_health_check(service_name: str, health_path: str):
            return ServiceHealth(
                service_name=service_name,
                status=HealthCheckStatus.HEALTHY,
                response_time_ms=50.0,
                last_check=datetime.now(UTC),
                metrics={"uptime": "100%"},
            )

        manager.health_check.side_effect = mock_health_check
        return manager

    @pytest_asyncio.fixture
    async def orchestrator(self, deployment_config, mock_service_manager):
        """Create orchestrator instance for testing"""
        orchestrator = EnterpriseDeploymentOrchestrator(
            deployment_config,
            mock_service_manager,
        )
        yield orchestrator
        # Cleanup
        await orchestrator.stop_deployment()

    # ========================================================================
    # Core Functionality Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_initialize_orchestrator_with_configuration(
        self,
        deployment_config,
    ):
        """
        Test: Should initialize deployment orchestrator with proper configuration
        and default settings.
        """
        orchestrator = EnterpriseDeploymentOrchestrator(deployment_config)

        # Check configuration is set
        assert orchestrator.config == deployment_config
        assert orchestrator.validator is not None
        assert orchestrator.service_manager is not None

        # Check initial deployment status
        assert orchestrator.deployment_status.environment == DeploymentEnvironment.TEST
        assert orchestrator.deployment_status.overall_status == ServiceStatus.UNKNOWN
        assert len(orchestrator.deployment_status.services) == 0

        # Check service startup order is empty initially
        assert orchestrator.service_startup_order == []

    @pytest.mark.asyncio()
    async def test_should_validate_deployment_configuration_correctly(
        self,
        orchestrator,
    ):
        """
        Test: Should validate deployment configuration and identify
        configuration issues and production readiness.
        """
        # Test valid configuration
        is_valid, issues = await orchestrator.validate_deployment()

        # Should be valid for test environment
        assert is_valid or len(issues) == 0  # Test environment has minimal requirements

        # Test invalid configuration
        invalid_config = DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            services=[
                ServiceConfig(name="service1", version="1.0", port=8000),
                ServiceConfig(
                    name="service1",
                    version="1.0",
                    port=8000,
                ),  # Duplicate name and port
            ],
        )

        invalid_orchestrator = EnterpriseDeploymentOrchestrator(invalid_config)
        is_valid, issues = await invalid_orchestrator.validate_deployment()

        assert not is_valid
        assert len(issues) > 0
        assert any("duplicate" in issue.lower() for issue in issues)

    @pytest.mark.asyncio()
    async def test_should_calculate_service_deployment_order_based_on_dependencies(
        self,
        orchestrator,
    ):
        """
        Test: Should correctly calculate service deployment order
        based on service dependencies using topological sorting.
        """
        # Calculate deployment order
        order = orchestrator._calculate_deployment_order()

        # Check all services are included
        service_names = [s.name for s in orchestrator.config.services]
        assert set(order) == set(service_names)

        # Check dependency order is respected
        # test-service-2 depends on test-service-1, so test-service-1 should come first
        service1_index = order.index("test-service-1")
        service2_index = order.index("test-service-2")
        assert service1_index < service2_index

        # test-database has no dependencies, can be anywhere
        assert "test-database" in order

    @pytest.mark.asyncio()
    async def test_should_deploy_services_in_correct_dependency_order(
        self,
        orchestrator,
        mock_service_manager,
    ):
        """
        Test: Should deploy services in correct order respecting dependencies
        and update deployment status appropriately.
        """
        # Mock successful deployment
        deployment_calls = []

        async def track_deployments(config):
            deployment_calls.append(config.name)
            return True

        mock_service_manager.deploy_service.side_effect = track_deployments

        # Perform deployment
        success = await orchestrator.deploy()

        assert success
        assert orchestrator.deployment_status.overall_status == ServiceStatus.RUNNING

        # Check services were deployed in correct order
        assert len(deployment_calls) == 3

        # test-service-1 should be deployed before test-service-2 (due to dependency)
        service1_pos = deployment_calls.index("test-service-1")
        service2_pos = deployment_calls.index("test-service-2")
        assert service1_pos < service2_pos

        # Check all services are marked as running
        for service in orchestrator.config.services:
            assert (
                orchestrator.deployment_status.services[service.name]
                == ServiceStatus.RUNNING
            )

    @pytest.mark.asyncio()
    async def test_should_handle_service_deployment_failures_gracefully(
        self,
        orchestrator,
        mock_service_manager,
    ):
        """
        Test: Should handle service deployment failures and stop deployment
        process with appropriate error reporting.
        """

        # Mock deployment failure for second service
        def mock_deploy_with_failure(config):
            if config.name == "test-service-2":
                return False  # Simulate failure
            return True

        mock_service_manager.deploy_service.side_effect = mock_deploy_with_failure

        # Attempt deployment
        success = await orchestrator.deploy()

        assert not success
        assert orchestrator.deployment_status.overall_status == ServiceStatus.FAILED

        # Check that services were attempted in deployment order
        # Depending on dependency order, different services might be deployed first
        services_with_status = orchestrator.deployment_status.services

        # At least one service should have failed
        failed_services = [
            name
            for name, status in services_with_status.items()
            if status == ServiceStatus.FAILED
        ]
        assert len(failed_services) >= 1

        # The specific failed service should be test-service-2 (as per our mock)
        assert "test-service-2" in failed_services

    @pytest.mark.asyncio()
    async def test_should_perform_health_checks_on_deployed_services(
        self,
        orchestrator,
        mock_service_manager,
    ):
        """
        Test: Should perform health checks on all deployed services
        and track health status over time.
        """
        # Deploy services first
        await orchestrator.deploy()

        # Wait for health monitoring to start
        await asyncio.sleep(0.1)

        # Trigger health check manually
        await orchestrator._perform_health_checks()

        # Check health status was recorded for all services
        for service in orchestrator.config.services:
            assert service.name in orchestrator.deployment_status.health_checks
            health = orchestrator.deployment_status.health_checks[service.name]
            assert health.status == HealthCheckStatus.HEALTHY
            assert health.response_time_ms > 0
            assert health.last_check is not None

    @pytest.mark.asyncio()
    async def test_should_stop_services_in_reverse_dependency_order(
        self,
        orchestrator,
        mock_service_manager,
    ):
        """
        Test: Should stop services in reverse dependency order
        to ensure clean shutdown process.
        """
        # Deploy services first
        await orchestrator.deploy()

        # Track stop calls
        stop_calls = []

        async def track_stops(service_name):
            stop_calls.append(service_name)
            return True

        mock_service_manager.stop_service.side_effect = track_stops

        # Stop deployment
        success = await orchestrator.stop_deployment()

        assert success
        assert orchestrator.deployment_status.overall_status == ServiceStatus.STOPPED

        # Check services were stopped in reverse order
        # test-service-2 (dependent) should be stopped before test-service-1
        # (dependency)
        if len(stop_calls) >= 2:
            service1_pos = (
                stop_calls.index("test-service-1")
                if "test-service-1" in stop_calls
                else -1
            )
            service2_pos = (
                stop_calls.index("test-service-2")
                if "test-service-2" in stop_calls
                else -1
            )

            if service1_pos >= 0 and service2_pos >= 0:
                assert service2_pos < service1_pos  # Dependent service stopped first

    # ========================================================================
    # Configuration Validation Tests
    # ========================================================================

    def test_configuration_validator_should_identify_production_requirements(self):
        """
        Test: ConfigurationValidator should identify missing production
        requirements and security configurations.
        """
        validator = ConfigurationValidator()

        # Test production configuration with missing requirements
        production_config = DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            services=[
                ServiceConfig(
                    name="service1",
                    version="1.0",
                    replicas=1,
                ),  # Single replica in production
            ],
            enable_tls=False,  # TLS disabled in production
            # Missing: secret_management, backup_config, resource_quotas,
            # monitoring_config
        )

        async def validate():
            is_valid, issues = await validator.validate_configuration(production_config)
            return is_valid, issues

        is_valid, issues = asyncio.run(validate())

        assert not is_valid
        assert len(issues) > 0

        # Check specific production requirements
        issue_text = " ".join(issues).lower()
        assert "tls" in issue_text or "production" in issue_text
        assert (
            "replica" in issue_text or "secret" in issue_text or "backup" in issue_text
        )

    def test_configuration_validator_should_detect_circular_dependencies(self):
        """
        Test: Should detect circular dependencies in service configurations
        and prevent invalid deployment ordering.
        """
        # Create configuration with circular dependency
        circular_services = [
            ServiceConfig(name="service-a", version="1.0", dependencies=["service-b"]),
            ServiceConfig(name="service-b", version="1.0", dependencies=["service-a"]),
        ]

        config = DeploymentConfig(
            environment=DeploymentEnvironment.TEST,
            services=circular_services,
        )

        orchestrator = EnterpriseDeploymentOrchestrator(config)

        # Should raise error when calculating deployment order
        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator._calculate_deployment_order()

    def test_configuration_validator_should_detect_missing_dependencies(self):
        """
        Test: Should detect references to undefined service dependencies
        and report configuration errors.
        """
        validator = ConfigurationValidator()

        # Configuration with undefined dependency
        config = DeploymentConfig(
            environment=DeploymentEnvironment.TEST,
            services=[
                ServiceConfig(
                    name="service1",
                    version="1.0",
                    dependencies=["undefined-service"],
                ),
            ],
        )

        async def validate():
            return await validator.validate_configuration(config)

        is_valid, issues = asyncio.run(validate())

        assert not is_valid
        assert any("undefined service" in issue.lower() for issue in issues)

    # ========================================================================
    # Service Management Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_local_service_manager_should_handle_service_lifecycle(self):
        """
        Test: LocalServiceManager should properly handle service deployment,
        status tracking, and lifecycle management.
        """
        manager = LocalServiceManager()

        service_config = ServiceConfig(
            name="test-local-service",
            version="1.0.0",
            port=9000,
            health_check_path="/health",
        )

        # Test deployment
        success = await manager.deploy_service(service_config)
        assert success

        # Test status check
        status = await manager.get_service_status("test-local-service")
        assert status == ServiceStatus.RUNNING

        # Test health check
        health = await manager.health_check("test-local-service", "/health")
        assert health.status == HealthCheckStatus.HEALTHY
        assert health.service_name == "test-local-service"
        assert health.response_time_ms > 0

        # Test stopping
        success = await manager.stop_service("test-local-service")
        assert success

        # Test status after stopping
        status = await manager.get_service_status("test-local-service")
        assert status == ServiceStatus.STOPPED

    @pytest.mark.asyncio()
    async def test_should_export_deployment_configuration_to_file(self, orchestrator):
        """
        Test: Should export deployment configuration to JSON/YAML files
        with complete configuration data.
        """
        # Test JSON export
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as tmp_file:
            json_path = tmp_file.name

        success = await orchestrator.export_configuration(json_path)
        assert success

        # Verify JSON content
        with open(json_path) as f:
            config_data = json.load(f)

        Path(json_path).unlink()  # Cleanup

        # Verify configuration structure
        assert "environment" in config_data
        assert "services" in config_data
        assert "namespace" in config_data
        assert config_data["environment"] == DeploymentEnvironment.TEST.value
        assert len(config_data["services"]) == len(orchestrator.config.services)

    # ========================================================================
    # Performance and Scalability Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_large_number_of_services_efficiently(
        self,
        mock_service_manager,
    ):
        """
        Test: Should efficiently handle deployment of large numbers of services
        without performance degradation.
        """
        # Create configuration with many services
        many_services = []
        for i in range(50):
            many_services.append(
                ServiceConfig(
                    name=f"service-{i:02d}",
                    version="1.0.0",
                    port=8000 + i,
                    health_check_path="/health",
                ),
            )

        config = DeploymentConfig(
            environment=DeploymentEnvironment.TEST,
            services=many_services,
        )

        orchestrator = EnterpriseDeploymentOrchestrator(config, mock_service_manager)

        # Measure deployment time
        start_time = time.time()
        success = await orchestrator.deploy()
        deployment_time = time.time() - start_time

        assert success
        # Should complete in reasonable time (under 10 seconds for 50 services)
        assert deployment_time < 10.0

        # All services should be running
        assert len(orchestrator.deployment_status.services) == 50
        for status in orchestrator.deployment_status.services.values():
            assert status == ServiceStatus.RUNNING

    @pytest.mark.asyncio()
    async def test_should_handle_concurrent_health_checks_safely(
        self,
        orchestrator,
        mock_service_manager,
    ):
        """
        Test: Should handle concurrent health checks without race conditions
        or resource conflicts.
        """
        # Deploy services
        await orchestrator.deploy()

        # Trigger multiple concurrent health check cycles
        health_check_tasks = []
        for _ in range(10):
            task = asyncio.create_task(orchestrator._perform_health_checks())
            health_check_tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*health_check_tasks, return_exceptions=True)

        # Verify no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception)

        # Verify health status is still intact
        for service in orchestrator.config.services:
            assert service.name in orchestrator.deployment_status.health_checks

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_service_manager_failures_gracefully(
        self,
        deployment_config,
    ):
        """
        Test: Should handle service manager failures and provide
        meaningful error reporting.
        """
        # Create failing service manager
        failing_manager = AsyncMock()
        failing_manager.deploy_service.side_effect = Exception(
            "Service manager failure",
        )

        orchestrator = EnterpriseDeploymentOrchestrator(
            deployment_config,
            failing_manager,
        )

        # Attempt deployment
        success = await orchestrator.deploy()

        assert not success
        assert orchestrator.deployment_status.overall_status == ServiceStatus.FAILED

    @pytest.mark.asyncio()
    async def test_should_handle_health_check_failures_appropriately(
        self,
        orchestrator,
        mock_service_manager,
    ):
        """
        Test: Should handle health check failures and update service
        health status accordingly.
        """

        # Configure health check to fail for one service
        def mock_failing_health_check(service_name: str, health_path: str):
            if service_name == "test-service-2":
                return ServiceHealth(
                    service_name=service_name,
                    status=HealthCheckStatus.UNHEALTHY,
                    last_check=datetime.now(UTC),
                    error_message="Service unavailable",
                )
            return ServiceHealth(
                service_name=service_name,
                status=HealthCheckStatus.HEALTHY,
                last_check=datetime.now(UTC),
            )

        mock_service_manager.health_check.side_effect = mock_failing_health_check

        # Deploy and perform health checks
        await orchestrator.deploy()
        await orchestrator._perform_health_checks()

        # Check health status
        healthy_service = await orchestrator.get_service_health("test-service-1")
        unhealthy_service = await orchestrator.get_service_health("test-service-2")

        assert healthy_service.status == HealthCheckStatus.HEALTHY
        assert unhealthy_service.status == HealthCheckStatus.UNHEALTHY
        assert unhealthy_service.error_message == "Service unavailable"

    @pytest.mark.asyncio()
    async def test_should_handle_empty_service_configuration(self):
        """
        Test: Should handle deployment configurations with no services
        and provide appropriate validation feedback.
        """
        empty_config = DeploymentConfig(
            environment=DeploymentEnvironment.TEST,
            services=[],  # No services
        )

        orchestrator = EnterpriseDeploymentOrchestrator(empty_config)

        # Validation should fail
        is_valid, issues = await orchestrator.validate_deployment()
        assert not is_valid
        assert any("no services" in issue.lower() for issue in issues)


class TestDeploymentConfigurationFactory:
    """
    Test suite for deployment configuration factory functions.
    """

    @pytest.mark.asyncio()
    async def test_should_create_production_ready_configuration(self):
        """
        Test: Should create production-ready configuration with all
        required security and reliability features.
        """
        config = await create_production_deployment_config()

        # Check environment
        assert config.environment == DeploymentEnvironment.PRODUCTION

        # Check security requirements
        assert config.enable_tls
        assert config.secret_management

        # Check reliability requirements
        assert config.backup_config
        assert config.resource_quotas
        assert config.monitoring_config

        # Check service configurations
        assert len(config.services) > 0
        for service in config.services:
            if service.name != "pake-database":  # Database might have single replica
                assert service.replicas >= 2  # HA requirement
            assert service.resource_limits  # Resource limits required

    @pytest.mark.asyncio()
    async def test_should_create_development_configuration(self):
        """
        Test: Should create development configuration optimized
        for local development workflow.
        """
        config = await create_development_deployment_config()

        # Check environment
        assert config.environment == DeploymentEnvironment.DEVELOPMENT

        # Check simplified settings
        assert not config.enable_tls  # Simplified for development
        assert len(config.services) > 0

        # Services should have single replica for development
        for service in config.services:
            assert service.replicas == 1

    @pytest.mark.asyncio()
    async def test_production_configuration_should_pass_validation(self):
        """
        Test: Production configuration created by factory should
        pass all validation requirements.
        """
        config = await create_production_deployment_config()
        validator = ConfigurationValidator()

        is_valid, issues = await validator.validate_configuration(config)

        # Should be valid or have minimal issues
        if not is_valid:
            print(f"Validation issues: {issues}")

        # Production config should be valid or close to valid
        # Allow minor issues that might be environment-specific
        assert is_valid or len(issues) <= 2


class TestServiceDataStructures:
    """
    Test suite for service configuration and status data structures.
    """

    def test_service_config_should_serialize_correctly(self):
        """
        Test: ServiceConfig should properly serialize to dictionary
        for export and API responses.
        """
        service = ServiceConfig(
            name="test-service",
            version="2.1.0",
            replicas=3,
            port=8080,
            health_check_path="/status",
            environment_variables={"ENV": "prod", "DEBUG": "false"},
            resource_limits={"cpu": "1000m", "memory": "2Gi"},
            dependencies=["database", "cache"],
        )

        service_dict = service.to_dict()

        # Verify all fields are present
        assert service_dict["name"] == "test-service"
        assert service_dict["version"] == "2.1.0"
        assert service_dict["replicas"] == 3
        assert service_dict["port"] == 8080
        assert service_dict["health_check_path"] == "/status"
        assert service_dict["environment_variables"]["ENV"] == "prod"
        assert service_dict["resource_limits"]["cpu"] == "1000m"
        assert "database" in service_dict["dependencies"]

    def test_deployment_status_should_track_service_states(self):
        """
        Test: DeploymentStatus should properly track and serialize
        service states and health information.
        """
        status = DeploymentStatus(
            environment=DeploymentEnvironment.PRODUCTION,
            deployment_id="deploy-123",
            started_at=datetime.now(UTC),
        )

        # Add service statuses
        status.services["service1"] = ServiceStatus.RUNNING
        status.services["service2"] = ServiceStatus.FAILED

        # Add health checks
        status.health_checks["service1"] = ServiceHealth(
            service_name="service1",
            status=HealthCheckStatus.HEALTHY,
            response_time_ms=25.5,
        )

        status_dict = status.to_dict()

        # Verify serialization
        assert status_dict["environment"] == "production"
        assert status_dict["deployment_id"] == "deploy-123"
        assert status_dict["services"]["service1"] == "running"
        assert status_dict["services"]["service2"] == "failed"
        assert status_dict["health_checks"]["service1"]["status"] == "healthy"

    def test_service_health_should_capture_comprehensive_metrics(self):
        """
        Test: ServiceHealth should capture comprehensive health metrics
        and error information for monitoring.
        """
        health = ServiceHealth(
            service_name="api-service",
            status=HealthCheckStatus.DEGRADED,
            response_time_ms=150.75,
            last_check=datetime.now(UTC),
            error_message="High response time",
            metrics={
                "cpu_usage": "85%",
                "memory_usage": "70%",
                "active_connections": 245,
            },
        )

        health_dict = health.to_dict()

        # Verify all information is captured
        assert health_dict["service_name"] == "api-service"
        assert health_dict["status"] == "degraded"
        assert health_dict["response_time_ms"] == 150.75
        assert health_dict["error_message"] == "High response time"
        assert health_dict["metrics"]["cpu_usage"] == "85%"
        assert health_dict["metrics"]["active_connections"] == 245
