#!/usr/bin/env python3
"""PAKE System - Base Service Classes
Provides common functionality and patterns for all PAKE services
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.utils.exceptions import (
    ConfigurationException,
    ServiceException,
    ServiceInitializationException,
)


class ServiceStatus(Enum):
    """Service status enumeration"""

    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    ERROR = "error"


class HealthStatus(Enum):
    """Health check status"""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ServiceMetrics:
    """Service performance metrics"""

    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    average_response_time: float = 0.0
    last_request_time: datetime | None = None
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.requests_total == 0:
            return 0.0
        return (self.requests_successful / self.requests_total) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage"""
        if self.requests_total == 0:
            return 0.0
        return (self.requests_failed / self.requests_total) * 100


@dataclass
class HealthCheck:
    """Health check result"""

    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceConfig:
    """Base service configuration"""

    name: str
    version: str = "1.0.0"
    description: str = ""
    enabled: bool = True
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    metrics_enabled: bool = True
    health_check_interval: float = 60.0
    log_level: str = "INFO"
    environment: str = "development"

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors"""
        errors = []

        if not self.name:
            errors.append("Service name is required")

        if self.timeout_seconds <= 0:
            errors.append("Timeout must be positive")

        if self.retry_attempts < 0:
            errors.append("Retry attempts cannot be negative")

        if self.retry_delay_seconds < 0:
            errors.append("Retry delay cannot be negative")

        if self.health_check_interval <= 0:
            errors.append("Health check interval must be positive")

        return errors


class BaseService(ABC):
    """Base class for all PAKE services

    Provides common functionality:
    - Configuration management
    - Logging setup
    - Health checks
    - Metrics collection
    - Error handling
    - Lifecycle management
    """

    def __init__(self, config: ServiceConfig):
        """Initialize base service

        Args:
            config: Service configuration
        """
        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            raise ConfigurationException(
                f"Invalid service configuration: {', '.join(config_errors)}",
            )

        self.config = config
        self.status = ServiceStatus.INITIALIZING
        self.metrics = ServiceMetrics()
        self._start_time = time.time()
        self._health_checks: dict[str, Callable[[], HealthCheck]] = {}

        # Setup logging
        self.logger = logging.getLogger(f"{self.config.name}.{self.__class__.__name__}")
        self.logger.setLevel(
            getattr(logging, self.config.log_level.upper(), logging.INFO),
        )

        # Initialize service
        try:
            self._initialize()
            self.status = ServiceStatus.HEALTHY
            self.logger.info(f"Service {self.config.name} initialized successfully")
        except Exception as e:
            self.status = ServiceStatus.ERROR
            error_msg = f"Failed to initialize service {self.config.name}: {str(e)}"
            self.logger.error(error_msg)
            raise ServiceInitializationException(
                self.config.name,
                str(e),
                original_exception=e,
            )

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize service-specific components"""

    @abstractmethod
    def health_check(self) -> HealthCheck:
        """Perform health check"""

    def get_status(self) -> ServiceStatus:
        """Get current service status"""
        return self.status

    def get_metrics(self) -> ServiceMetrics:
        """Get current service metrics"""
        self.metrics.uptime_seconds = time.time() - self._start_time
        return self.metrics

    def add_health_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheck],
    ) -> None:
        """Add a custom health check"""
        self._health_checks[name] = check_func

    def run_health_checks(self) -> list[HealthCheck]:
        """Run all health checks"""
        results = [self.health_check()]

        for name, check_func in self._health_checks.items():
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                results.append(
                    HealthCheck(
                        name=name,
                        status=HealthStatus.FAIL,
                        message=f"Health check failed: {str(e)}",
                    ),
                )

        return results

    def _record_request(self, success: bool, duration: float) -> None:
        """Record request metrics"""
        if not self.config.metrics_enabled:
            return

        self.metrics.requests_total += 1
        self.metrics.last_request_time = datetime.now(UTC)

        if success:
            self.metrics.requests_successful += 1
        else:
            self.metrics.requests_failed += 1

        # Update average response time
        if self.metrics.requests_total == 1:
            self.metrics.average_response_time = duration
        else:
            # Running average
            total_time = self.metrics.average_response_time * (
                self.metrics.requests_total - 1
            )
            self.metrics.average_response_time = (
                total_time + duration
            ) / self.metrics.requests_total

    def execute_with_metrics(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with automatic metrics recording"""
        start_time = time.time()
        success = False

        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            self.logger.error(f"Error executing {func.__name__}: {str(e)}")
            raise
        finally:
            duration = time.time() - start_time
            self._record_request(success, duration)

    def shutdown(self) -> None:
        """Shutdown the service gracefully"""
        try:
            self._cleanup()
            self.status = ServiceStatus.STOPPED
            self.logger.info(f"Service {self.config.name} shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during service shutdown: {str(e)}")
            self.status = ServiceStatus.ERROR

    def _cleanup(self) -> None:
        """Cleanup service resources (override in subclasses)"""


class AsyncBaseService(BaseService):
    """Async base class for PAKE services

    Extends BaseService with async capabilities
    """

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self._shutdown_event = asyncio.Event()
        self._background_tasks: list[asyncio.Task] = []

    @abstractmethod
    async def _async_initialize(self) -> None:
        """Async initialization (override in subclasses)"""

    @abstractmethod
    async def async_health_check(self) -> HealthCheck:
        """Async health check"""

    async def start(self) -> None:
        """Start the async service"""
        try:
            await self._async_initialize()
            self.status = ServiceStatus.HEALTHY
            self.logger.info(f"Async service {self.config.name} started successfully")
        except Exception as e:
            self.status = ServiceStatus.ERROR
            error_msg = f"Failed to start async service {self.config.name}: {str(e)}"
            self.logger.error(error_msg)
            raise ServiceInitializationException(
                self.config.name,
                str(e),
                original_exception=e,
            )

    async def stop(self) -> None:
        """Stop the async service gracefully"""
        self._shutdown_event.set()

        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        await self._async_cleanup()
        self.status = ServiceStatus.STOPPED
        self.logger.info(f"Async service {self.config.name} stopped")

    async def _async_cleanup(self) -> None:
        """Async cleanup (override in subclasses)"""

    def add_background_task(self, coro: Awaitable) -> asyncio.Task:
        """Add a background task"""
        task = asyncio.create_task(coro)
        self._background_tasks.append(task)
        return task

    async def execute_async_with_metrics(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with automatic metrics recording"""
        start_time = time.time()
        success = False

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            self.logger.error(f"Error executing async {func.__name__}: {str(e)}")
            raise
        finally:
            duration = time.time() - start_time
            self._record_request(success, duration)

    @asynccontextmanager
    async def timeout_context(self, timeout: float | None = None):
        """Context manager for timeout handling"""
        timeout = timeout or self.config.timeout_seconds

        try:
            async with asyncio.timeout(timeout):
                yield
        except TimeoutError:
            self.logger.warning(f"Operation timed out after {timeout}s")
            raise ServiceException(
                f"Operation timed out after {timeout}s",
                service_name=self.config.name,
            )

    async def retry_async(
        self,
        func: Callable,
        *args,
        max_attempts: int | None = None,
        delay: float | None = None,
        **kwargs,
    ) -> Any:
        """Retry async function with exponential backoff"""
        max_attempts = max_attempts or self.config.retry_attempts
        delay = delay or self.config.retry_delay_seconds

        last_exception = None

        for attempt in range(max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == max_attempts - 1:
                    break

                wait_time = delay * (2**attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}",
                )
                await asyncio.sleep(wait_time)

        # All attempts failed
        raise ServiceException(
            f"All {max_attempts} attempts failed",
            service_name=self.config.name,
            original_exception=last_exception,
        )

    async def run_async_health_checks(self) -> list[HealthCheck]:
        """Run all async health checks"""
        results = [await self.async_health_check()]

        for name, check_func in self._health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                results.append(result)
            except Exception as e:
                results.append(
                    HealthCheck(
                        name=name,
                        status=HealthStatus.FAIL,
                        message=f"Async health check failed: {str(e)}",
                    ),
                )

        return results

    @property
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        return self._shutdown_event.is_set()

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal"""
        await self._shutdown_event.wait()


# Utility functions for service management
def create_service_config(name: str, **kwargs) -> ServiceConfig:
    """Create a service configuration with defaults"""
    return ServiceConfig(name=name, **kwargs)


def validate_service_dependencies(
    dependencies: list[str],
    logger: logging.Logger | None = None,
) -> list[str]:
    """Validate that required service dependencies are available

    Args:
        dependencies: List of module names to check
        logger: Optional logger for warnings

    Returns:
        List of missing dependencies
    """
    missing = []

    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
            if logger:
                logger.warning(f"Missing dependency: {dep}")

    return missing
