config
#!/usr/bin/env python3
"""PAKE System - Enterprise Deployment Configuration
Phase 2B Sprint 4: Production-ready deployment orchestration and configuration.

Provides enterprise-grade deployment configuration, service orchestration,
health monitoring, and production readiness validation.
"""

from abc import ABC, abstractmethod
import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
import logging
import time
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    import subprocess

logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class ServiceStatus(Enum):
    """Service deployment status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


class HealthCheckStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for individual service deployment."""

    name: str
    version: str
    image: str | None = None
    replicas: int = 1
    port: int = 8000
    health_check_path: str = "/health"
    environment_variables: dict[str, str] = field(default_factory=dict)
    resource_limits: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "image": self.image,
            "replicas": self.replicas,
            "port": self.port,
            "health_check_path": self.health_check_path,
            "environment_variables": self.environment_variables,
            "resource_limits": self.resource_limits,
            "dependencies": self.dependencies,
        }


@dataclass
class DeploymentConfig:
    """Enterprise deployment configuration."""

    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    namespace: str = "pake-system"
    cluster_name: str = "pake-cluster"

    # Service configurations
    services: list[ServiceConfig] = field(default_factory=list)

    # Infrastructure settings
    database_config: dict[str, Any] = field(default_factory=dict)
    cache_config: dict[str, Any] = field(default_factory=dict)
    monitoring_config: dict[str, Any] = field(default_factory=dict)

    # Security settings
    enable_tls: bool = True
    secret_management: dict[str, str] = field(default_factory=dict)
    network_policies: list[dict[str, Any]] = field(default_factory=list)

    # Performance settings
    auto_scaling: dict[str, Any] = field(default_factory=dict)
    resource_quotas: dict[str, str] = field(default_factory=dict)

    # Backup and recovery
    backup_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "environment": self.environment.value,
            "namespace": self.namespace,
            "cluster_name": self.cluster_name,
            "services": [service.to_dict() for service in self.services],
            "database_config": self.database_config,
            "cache_config": self.cache_config,
            "monitoring_config": self.monitoring_config,
            "enable_tls": self.enable_tls,
            "secret_management": self.secret_management,
            "network_policies": self.network_policies,
            "auto_scaling": self.auto_scaling,
            "resource_quotas": self.resource_quotas,
            "backup_config": self.backup_config,
        }


@dataclass
class ServiceHealth:
    """Service health status information."""

    service_name: str
    status: HealthCheckStatus
    response_time_ms: float = 0.0
    last_check: datetime | None = None
    error_message: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


@dataclass
class DeploymentStatus:
    """Overall deployment status."""

    environment: DeploymentEnvironment
    deployment_id: str
    started_at: datetime
    services: dict[str, ServiceStatus] = field(default_factory=dict)
    health_checks: dict[str, ServiceHealth] = field(default_factory=dict)
    overall_status: ServiceStatus = ServiceStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "environment": self.environment.value,
            "deployment_id": self.deployment_id,
            "started_at": self.started_at.isoformat(),
            "services": {name: status.value for name, status in self.services.items()},
            "health_checks": {
                name: health.to_dict() for name, health in self.health_checks.items()
            },
            "overall_status": self.overall_status.value,
        }


class ServiceManager(ABC):
    """Abstract base for service management implementations."""

    @abstractmethod
    async def deploy_service(self, config: ServiceConfig) -> bool:
        """Deploy a service with the given configuration."""

    @abstractmethod
    async def stop_service(self, service_name: str) -> bool:
        """Stop a running service."""

    @abstractmethod
    async def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get current status of a service."""

    @abstractmethod
    async def health_check(
        self, service_name: str, health_check_path: str
    ) -> ServiceHealth:
        """Perform health check on a service."""


class LocalServiceManager(ServiceManager):
    """Local development service manager."""

    def __init__(self) -> None:
        self.running_processes: dict[str, subprocess.Popen] = {}
        self.service_ports: dict[str, int] = {}

    async def deploy_service(self, config: ServiceConfig) -> bool:
        """Deploy service locally using subprocess."""
        try:
            if config.name in self.running_processes:
                await self.stop_service(config.name)

            # Simulate service deployment
            logger.info("Deploying %s locally on port %s", config.name, config.port)

            # In a real implementation, this would start the actual service
            # For simulation, we'll just track the configuration
            self.service_ports[config.name] = config.port

            # Simulate process (in real implementation, would be actual subprocess)
            self.running_processes[config.name] = None

            await asyncio.sleep(0.1)  # Simulate startup time
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to deploy %s: %s", config.name, e)
            return False

    async def stop_service(self, service_name: str) -> bool:
        """Stop a locally running service."""
        try:
            if service_name in self.running_processes:
                # In real implementation, would terminate the process
                del self.running_processes[service_name]
                if service_name in self.service_ports:
                    del self.service_ports[service_name]
                logger.info("Stopped %s", service_name)
                return True
            return False
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to stop %s: %s", service_name, e)
            return False

    async def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get status of local service."""
        if service_name in self.running_processes:
            return ServiceStatus.RUNNING
        return ServiceStatus.STOPPED

    async def health_check(
        self, service_name: str, health_check_path: str
    ) -> ServiceHealth:
        """Perform health check on local service."""
        start_time = time.time()

        try:
            if service_name in self.running_processes:
                # Simulate health check
                await asyncio.sleep(0.01)  # Simulate network call

                response_time = (time.time() - start_time) * 1000

                return ServiceHealth(
                    service_name=service_name,
                    status=HealthCheckStatus.HEALTHY,
                    response_time_ms=response_time,
                    last_check=datetime.now(UTC),
                    metrics={"uptime": "simulated"},
                )
            return ServiceHealth(
                service_name=service_name,
                status=HealthCheckStatus.UNHEALTHY,
                last_check=datetime.now(UTC),
                error_message="Service not running",
            )

        except (ValueError, RuntimeError) as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                service_name=service_name,
                status=HealthCheckStatus.UNHEALTHY,
                response_time_ms=response_time,
                last_check=datetime.now(UTC),
                error_message=str(e),
            )


class ConfigurationValidator:
    """Validates deployment configurations for production readiness."""

    def __init__(self) -> None:
        self.validation_rules = {
            DeploymentEnvironment.PRODUCTION: self._production_rules,
            DeploymentEnvironment.STAGING: self._staging_rules,
            DeploymentEnvironment.DEVELOPMENT: self._development_rules,
        }

    async def validate_configuration(
        self, config: DeploymentConfig
    ) -> tuple[bool, list[str]]:
        """Validate deployment configuration.
        Returns: (is_valid, list_of_issues).
        """
        issues = []

        # Get environment-specific validation rules
        validator = self.validation_rules.get(
            config.environment, self._development_rules
        )
        issues.extend(await validator(config))

        # Common validation rules
        issues.extend(await self._validate_common_requirements(config))

        return len(issues) == 0, issues

    async def _validate_common_requirements(
        self, config: DeploymentConfig
    ) -> list[str]:
        """Validate common requirements across all environments."""
        issues = []

        # Check service configurations
        if not config.services:
            issues.append("No services configured for deployment")

        # Check for duplicate service names
        service_names = [s.name for s in config.services]
        if len(service_names) != len(set(service_names)):
            issues.append("Duplicate service names detected")

        # Check for port conflicts
        ports = [s.port for s in config.services]
        if len(ports) != len(set(ports)):
            issues.append("Port conflicts detected between services")

        # Validate service dependencies
        for service in config.services:
            for dep in service.dependencies:
                if dep not in service_names:
                    issues.append(
                        f"Service {service.name} depends on undefined service {dep}"
                    )

        return issues

    async def _production_rules(self, config: DeploymentConfig) -> list[str]:
        """Production-specific validation rules."""
        issues = []

        # Security requirements
        if not config.enable_tls:
            issues.append("TLS must be enabled in production")

        if not config.secret_management:
            issues.append("Secret management configuration required for production")

        # Resource requirements
        if not config.resource_quotas:
            issues.append("Resource quotas must be defined for production")

        # Backup requirements
        if not config.backup_config:
            issues.append("Backup configuration required for production")

        # High availability requirements
        for service in config.services:
            if service.replicas < 2:
                issues.append(
                    f"Service {service.name} should have at least 2 replicas in production"
                )

            if not service.resource_limits:
                issues.append(
                    f"Resource limits must be defined for service {service.name} in production"
                )

        # Monitoring requirements
        if not config.monitoring_config:
            issues.append("Monitoring configuration required for production")

        return issues

    async def _staging_rules(self, config: DeploymentConfig) -> list[str]:
        """Staging-specific validation rules."""
        issues = []

        # Less strict than production but still important
        if not config.monitoring_config:
            issues.append("Monitoring recommended for staging environment")

        return issues

    async def _development_rules(self, config: DeploymentConfig) -> list[str]:
        """Development-specific validation rules."""
        return []

        # Minimal requirements for development


class EnterpriseDeploymentOrchestrator:
    """Enterprise deployment orchestrator for PAKE system.
    Manages service deployment, health monitoring, and configuration validation.
    """

def __init__(self, config: Any = None, service_manager: Any = None, config: Any = None, config: Any = None) -> None:
        self.config = config
        self.service_manager = service_manager or LocalServiceManager()
        self.validator = ConfigurationValidator()

        # Deployment state
        self.deployment_status = DeploymentStatus(
            environment=config.environment,
            deployment_id=f"deployment_{int(time.time())}",
            started_at=datetime.now(UTC),
        )

        # Service orchestration
        self.service_startup_order: list[str] = []
        self.health_check_interval = 30  # seconds
        self.health_monitoring_task: asyncio.Task | None = None

        logger.info(
            "Initialized Enterprise Deployment Orchestrator for %s",
            config.environment.value,
        )

    async def validate_deployment(self) -> tuple[bool, list[str]]:
        """Validate deployment configuration before starting."""
        return await self.validator.validate_configuration(self.config)

    async def deploy(self) -> bool:
        """Deploy all services according to configuration.
        Returns True if deployment successful, False otherwise.
        """
        logger.info("Starting deployment to %s", self.config.environment.value)

        try:
            # Validate configuration first
            is_valid, issues = await self.validate_deployment()
            if not is_valid:
                logger.error("Configuration validation failed: %s", issues)
                return False

            # Calculate service deployment order based on dependencies
            self.service_startup_order = self._calculate_deployment_order()

            # Deploy services in dependency order
            for service_name in self.service_startup_order:
                service_config = self._get_service_config(service_name)
                if not service_config:
                    logger.error("Service configuration not found: %s", service_name)
                    return False

                logger.info("Deploying service: %s", service_name)
                self.deployment_status.services[service_name] = ServiceStatus.STARTING

                success = await self.service_manager.deploy_service(service_config)

                if success:
                    self.deployment_status.services[service_name] = (
                        ServiceStatus.RUNNING
                    )
                    logger.info("Successfully deployed: %s", service_name)
                else:
                    self.deployment_status.services[service_name] = ServiceStatus.FAILED
                    self.deployment_status.overall_status = ServiceStatus.FAILED
                    logger.error("Failed to deploy: %s", service_name)
                    return False

                # Brief pause between service deployments
                await asyncio.sleep(0.01)

            # Start health monitoring
            await self._start_health_monitoring()

            # Update overall status
            self.deployment_status.overall_status = ServiceStatus.RUNNING

            logger.info("Deployment completed successfully")
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Deployment failed: %s", e)
            self.deployment_status.overall_status = ServiceStatus.FAILED
            return False

    async def stop_deployment(self) -> bool:
        """Stop all deployed services."""
        logger.info("Stopping deployment")

        try:
            # Stop health monitoring
            if self.health_monitoring_task:
                self.health_monitoring_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.health_monitoring_task

            # Stop services in reverse order
            for service_name in reversed(self.service_startup_order):
                logger.info("Stopping service: %s", service_name)
                self.deployment_status.services[service_name] = ServiceStatus.STOPPING

                success = await self.service_manager.stop_service(service_name)

                if success:
                    self.deployment_status.services[service_name] = (
                        ServiceStatus.STOPPED
                    )
                else:
                    logger.warning("Failed to cleanly stop: %s", service_name)

                await asyncio.sleep(0.5)

            self.deployment_status.overall_status = ServiceStatus.STOPPED
            logger.info("Deployment stopped")
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Error stopping deployment: %s", e)
            return False

def _calculate_deployment_order(self, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None) -> list[str]:
        """Calculate service deployment order based on dependencies."""
        # Simple topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        order = []

def visit(self, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None, service_name: Any = None) -> None:
            if service_name in temp_visited:
                msg = f"Circular dependency detected involving {service_name}"
                raise ValueError(msg)

            if service_name not in visited:
                temp_visited.add(service_name)

                # Visit dependencies first
                service_config = self._get_service_config(service_name)
                if service_config:
                    for dep in service_config.dependencies:
                        visit(dep)

                temp_visited.remove(service_name)
                visited.add(service_name)
                order.append(service_name)

        # Process all services
        for service in self.config.services:
            if service.name not in visited:
                visit(service.name)

        return order

    def _get_service_config(self, service_name: str) -> ServiceConfig | None:
        """Get service configuration by name."""
        for service in self.config.services:
            if service.name == service_name:
                return service
        return None

    async def _start_health_monitoring(self) -> None:
        """Start continuous health monitoring of deployed services."""
        self.health_monitoring_task = asyncio.create_task(
            self._health_monitoring_loop()
        )

    async def _health_monitoring_loop(self) -> None:
        """Continuous health monitoring loop."""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except (ValueError, RuntimeError) as e:
                logger.error("Health monitoring error: %s", e)
                await asyncio.sleep(5)  # Brief pause before retry

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all services."""
        health_check_tasks = []

        for service_name in self.service_startup_order:
            service_config = self._get_service_config(service_name)
            if (
                service_config
                and self.deployment_status.services.get(service_name)
                == ServiceStatus.RUNNING
            ):
                task = self.service_manager.health_check(
                    service_name, service_config.health_check_path
                )
                health_check_tasks.append((service_name, task))

        # Execute health checks concurrently
        if health_check_tasks:
            results = await asyncio.gather(
                *[task for _, task in health_check_tasks], return_exceptions=True
            )

            for (service_name, _), result in zip(
                health_check_tasks, results, strict=False
            ):
                if isinstance(result, ServiceHealth):
                    self.deployment_status.health_checks[service_name] = result
                else:
                    # Handle exception case
                    self.deployment_status.health_checks[service_name] = ServiceHealth(
                        service_name=service_name,
                        status=HealthCheckStatus.UNHEALTHY,
                        last_check=datetime.now(UTC),
                        error_message=str(result)
                        if isinstance(result, Exception)
                        else "Unknown error",
                    )

    async def get_deployment_status(self) -> DeploymentStatus:
        """Get current deployment status."""
        return self.deployment_status

    async def get_service_health(self, service_name: str) -> ServiceHealth | None:
        """Get health status of a specific service."""
        return self.deployment_status.health_checks.get(service_name)

    async def export_configuration(self, filepath: str) -> bool:
        """Export deployment configuration to file."""
        try:
            config_data = self.config.to_dict()

            if filepath.endswith((".yaml", ".yml")):
                with open(filepath, "w") as f:
                    yaml.dump(config_data, f, default_flow_style=False)
            else:
                with open(filepath, "w") as f:
                    json.dump(config_data, f, indent=2)

            logger.info("Configuration exported to %s", filepath)
            return True

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Failed to export configuration: %s", e)
            return False


# Production-ready configuration factory functions
async def create_production_deployment_config() -> DeploymentConfig:
    """Create production-ready deployment configuration."""
    # Core services
    services = [
        ServiceConfig(
            name="pake-orchestrator",
            version="1.0.0",
            replicas=3,
            port=8000,
            health_check_path="/health",
            environment_variables={"ENVIRONMENT": "production", "LOG_LEVEL": "INFO"},
            resource_limits={"cpu": "1000m", "memory": "2Gi"},
        ),
        ServiceConfig(
            name="pake-cache-service",
            version="1.0.0",
            replicas=2,
            port=6379,
            health_check_path="/health",
            dependencies=["pake-database"],
            resource_limits={"cpu": "500m", "memory": "1Gi"},
        ),
        ServiceConfig(
            name="pake-monitoring-dashboard",
            version="1.0.0",
            replicas=2,
            port=8080,
            health_check_path="/health",
            dependencies=["pake-orchestrator"],
            resource_limits={"cpu": "250m", "memory": "512Mi"},
        ),
        ServiceConfig(
            name="pake-database",
            version="1.0.0",
            replicas=1,
            port=5432,
            health_check_path="/health",
            resource_limits={"cpu": "2000m", "memory": "4Gi"},
        ),
    ]

    return DeploymentConfig(
        environment=DeploymentEnvironment.PRODUCTION,
        namespace="pake-production",
        cluster_name="pake-prod-cluster",
        services=services,
        database_config={
            "type": "postgresql",
            "high_availability": True,
            "backup_retention_days": 30,
        },
        cache_config={"type": "redis", "clustering": True, "persistence": True},
        monitoring_config={
            "metrics_collection": True,
            "alerting": True,
            "log_aggregation": True,
        },
        enable_tls=True,
        secret_management={"provider": "kubernetes-secrets", "encryption": "enabled"},
        auto_scaling={
            "enabled": True,
            "min_replicas": 2,
            "max_replicas": 10,
            "target_cpu_utilization": 70,
        },
        resource_quotas={"cpu": "10", "memory": "20Gi", "storage": "100Gi"},
        backup_config={
            "enabled": True,
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "retention_days": 30,
        },
    )


async def create_development_deployment_config() -> DeploymentConfig:
    """Create development deployment configuration."""
    services = [
        ServiceConfig(
            name="pake-orchestrator",
            version="dev",
            replicas=1,
            port=8000,
            health_check_path="/health",
            environment_variables={"ENVIRONMENT": "development", "LOG_LEVEL": "DEBUG"},
        ),
        ServiceConfig(
            name="pake-cache-service",
            version="dev",
            replicas=1,
            port=6379,
            health_check_path="/health",
        ),
    ]

    return DeploymentConfig(
        environment=DeploymentEnvironment.DEVELOPMENT,
        namespace="pake-dev",
        services=services,
        enable_tls=False,  # Simplified for development
        monitoring_config={"metrics_collection": False, "basic_logging": True},
    )


if __name__ == "__main__":
    # Example usage
    async def main(self) -> None:
        # Create deployment configuration
        config = await create_development_deployment_config()

        # Initialize orchestrator
        orchestrator = EnterpriseDeploymentOrchestrator(config)

        # Validate and deploy
        is_valid, issues = await orchestrator.validate_deployment()
        if is_valid:
            success = await orchestrator.deploy()
            if success:
                print("Deployment successful!")

                # Wait a bit then check status
                await asyncio.sleep(2)
                status = await orchestrator.get_deployment_status()
                print(f"Deployment status: {status.overall_status.value}")

                # Stop deployment
                await orchestrator.stop_deployment()
            else:
                print("Deployment failed!")
        else:
            print(f"Configuration validation failed: {issues}")

    asyncio.run(main())
