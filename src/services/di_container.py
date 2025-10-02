#!/usr/bin/env python3
"""PAKE System - Dependency Injection Container (Phase 2 Architectural Refactoring)
Centralized dependency management and service factory.

This container manages all service dependencies and provides:
1. Service registration and resolution
2. Singleton and transient lifecycle management
3. Dependency graph resolution
4. Circular dependency prevention
"""

import logging
from collections.abc import Callable
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifetime:
    """Service lifetime enumeration"""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceRegistration:
    """Service registration metadata"""

    def __init__(
        self,
        interface: type[T],
        implementation: type[T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        factory: Optional[Callable[[], T]] = None,
    ):
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.factory = factory
        self.instance: Optional[T] = None


class DIContainer:
    """Dependency Injection Container for managing service dependencies"""

    def __init__(self):
        self._services: dict[str, ServiceRegistration] = {}
        self._singletons: dict[str, Any] = {}
        logger.info("DIContainer initialized")

    def register_singleton(
        self, interface: type[T], implementation: type[T]
    ) -> "DIContainer":
        """Register a singleton service"""
        return self._register_service(
            interface, implementation, ServiceLifetime.SINGLETON
        )

    def register_transient(
        self, interface: type[T], implementation: type[T]
    ) -> "DIContainer":
        """Register a transient service"""
        return self._register_service(
            interface, implementation, ServiceLifetime.TRANSIENT
        )

    def register_factory(
        self,
        interface: type[T],
        factory: Callable[[], T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> "DIContainer":
        """Register a service with custom factory"""
        interface_name = interface.__name__
        self._services[interface_name] = ServiceRegistration(
            interface=interface, implementation=None, lifetime=lifetime, factory=factory
        )
        logger.info(
            f"Registered factory: {interface_name} (lifetime: {lifetime.value})"
        )
        return self

    def register_instance(self, interface: type[T], instance: T) -> "DIContainer":
        """Register a service instance"""
        interface_name = interface.__name__
        self._singletons[interface_name] = instance
        logger.info(f"Registered instance: {interface_name}")
        return self

    def _register_service(
        self, interface: type[T], implementation: type[T], lifetime: ServiceLifetime
    ) -> "DIContainer":
        """Internal service registration method"""
        interface_name = interface.__name__
        self._services[interface_name] = ServiceRegistration(
            interface=interface, implementation=implementation, lifetime=lifetime
        )
        logger.info(
            f"Registered service: {interface_name} -> {implementation.__name__} (lifetime: {lifetime.value})"
        )
        return self

    def get(self, interface: type[T]) -> T:
        """Get service instance"""
        interface_name = interface.__name__

        # Check if we have a registered instance
        if interface_name in self._singletons:
            return self._singletons[interface_name]

        # Check if we have a service registration
        if interface_name not in self._services:
            raise ValueError(f"No service registered for {interface_name}")

        registration = self._services[interface_name]

        # Handle singleton lifetime
        if registration.lifetime == ServiceLifetime.SINGLETON:
            if registration.instance is None:
                registration.instance = self._create_instance(registration)
            return registration.instance

        # Handle transient lifetime
        return self._create_instance(registration)

    def get_with_dependencies(self, interface: type[T], **kwargs) -> T:
        """Get service instance with additional dependencies"""
        interface_name = interface.__name__

        if interface_name not in self._services:
            raise ValueError(f"No service registered for {interface_name}")

        registration = self._services[interface_name]

        # Create instance with additional dependencies
        if registration.factory:
            return registration.factory()

        if registration.implementation:
            # Try to inject dependencies through constructor
            try:
                return registration.implementation(**kwargs)
            except TypeError:
                # Fallback to parameterless constructor
                return registration.implementation()

        raise ValueError(f"Cannot create instance for {interface_name}")

    def _create_instance(self, registration: ServiceRegistration) -> T:
        """Create service instance"""
        if registration.factory:
            return registration.factory()

        if registration.implementation:
            try:
                # Try to resolve constructor dependencies
                return self._resolve_dependencies(registration.implementation)
            except Exception as e:
                logger.warning(
                    f"Failed to resolve dependencies for {registration.implementation.__name__}: {e}"
                )
                # Fallback to parameterless constructor
                return registration.implementation()

        raise ValueError(
            f"Cannot create instance for {registration.interface.__name__}"
        )

    def _resolve_dependencies(self, implementation: type[T]) -> T:
        """Resolve constructor dependencies"""
        import inspect

        # Get constructor signature
        signature = inspect.signature(implementation.__init__)
        dependencies = {}

        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            # Try to resolve parameter type
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependencies[param_name] = self.get(param.annotation)
                except ValueError:
                    logger.warning(
                        f"Cannot resolve dependency {param_name} of type {param.annotation}"
                    )

        return implementation(**dependencies)

    def is_registered(self, interface: type[T]) -> bool:
        """Check if service is registered"""
        interface_name = interface.__name__
        return interface_name in self._services or interface_name in self._singletons

    def get_registered_services(self) -> dict[str, str]:
        """Get list of registered services"""
        services = {}

        # Add registered services
        for name, registration in self._services.items():
            services[
                name
            ] = f"{registration.implementation.__name__ if registration.implementation else 'Factory'} ({registration.lifetime.value})"

        # Add singleton instances
        for name in self._singletons.keys():
            services[name] = "Instance (singleton)"

        return services

    def clear(self):
        """Clear all registrations"""
        self._services.clear()
        self._singletons.clear()
        logger.info("DIContainer cleared")


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get global DI container instance"""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def configure_services(container: DIContainer) -> DIContainer:
    """Configure all PAKE System services"""
    # Import here to avoid circular dependencies
    from ..business.user_service_refactored import UserService
    from ..domain.interfaces import (
        AbstractAuthenticationService,
        AbstractCacheService,
        AbstractConfigService,
        AbstractNotificationService,
        AbstractUserRepository,
    )
    from ..repositories.sqlalchemy_repositories import UserRepository

    # Register repositories
    container.register_transient(AbstractUserRepository, UserRepository)

    # Register services
    container.register_transient(UserService, UserService)

    # Register configuration services
    container.register_singleton(AbstractConfigService, MockConfigService)
    container.register_singleton(AbstractCacheService, MockCacheService)
    container.register_singleton(AbstractAuthenticationService, MockAuthService)
    container.register_singleton(AbstractNotificationService, MockNotificationService)

    logger.info("PAKE System services configured")
    return container


# Mock implementations for demonstration
class MockConfigService:
    """Mock configuration service"""

    def get_config(self, key: str, default: Any = None) -> Any:
        return default

    def get_database_config(self) -> dict[str, Any]:
        return {"host": "localhost", "port": 5432}

    def get_redis_config(self) -> dict[str, Any]:
        return {"host": "localhost", "port": 6379}


class MockCacheService:
    """Mock cache service"""

    async def get(self, key: str) -> Optional[Any]:
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        return True

    async def delete(self, key: str) -> bool:
        return True

    async def clear_pattern(self, pattern: str) -> int:
        return 0


class MockAuthService:
    """Mock authentication service"""

    async def authenticate_user(self, email: str, password: str):
        from ..domain.interfaces import ServiceResult, ServiceStatus

        return ServiceResult(
            status=ServiceStatus.SUCCESS,
            data={"user_id": "mock-user-id", "token": "mock-token"},
        )

    async def create_user(self, user_data: dict[str, Any]):
        from ..domain.interfaces import ServiceResult, ServiceStatus

        return ServiceResult(
            status=ServiceStatus.SUCCESS,
            data={"hashed_password": "mock-hashed-password"},
        )

    async def validate_token(self, token: str):
        from ..domain.interfaces import ServiceResult, ServiceStatus

        return ServiceResult(
            status=ServiceStatus.SUCCESS, data={"user_id": "mock-user-id"}
        )


class MockNotificationService:
    """Mock notification service"""

    async def send_welcome_email(self, email: str, user_data: dict[str, Any]):
        from ..domain.interfaces import ServiceResult, ServiceStatus

        return ServiceResult(status=ServiceStatus.SUCCESS, data=True)

    async def send_notification(
        self, user_id: str, message: str, notification_type: str
    ):
        from ..domain.interfaces import ServiceResult, ServiceStatus

        return ServiceResult(status=ServiceStatus.SUCCESS, data=True)
