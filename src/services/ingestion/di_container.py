#!/usr/bin/env python3
"""PAKE System - Dependency Injection Container
Manages dependencies and breaks circular imports through proper injection.
"""

import logging
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container"""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}

    def register_singleton(self, interface: type[T], implementation: type[T]) -> None:
        """Register a singleton implementation for an interface"""
        interface_name = interface.__name__
        self._services[interface_name] = implementation
        logger.info(
            f"Registered singleton: {interface_name} -> {implementation.__name__}"
        )

    def register_transient(self, interface: type[T], implementation: type[T]) -> None:
        """Register a transient implementation for an interface"""
        interface_name = interface.__name__
        self._services[interface_name] = implementation
        logger.info(
            f"Registered transient: {interface_name} -> {implementation.__name__}"
        )

    def get(self, interface: type[T]) -> T:
        """Get an instance of the interface"""
        interface_name = interface.__name__

        if interface_name not in self._services:
            raise ValueError(f"No implementation registered for {interface_name}")

        implementation = self._services[interface_name]

        # For singletons, check if we already have an instance
        if interface_name in self._singletons:
            return self._singletons[interface_name]

        # Create new instance
        instance = implementation()

        # Store singleton if it's registered as such
        if interface_name in self._services:
            self._singletons[interface_name] = instance

        return instance

    def get_with_dependencies(self, interface: type[T], **kwargs) -> T:
        """Get an instance with specific dependencies injected"""
        interface_name = interface.__name__

        if interface_name not in self._services:
            raise ValueError(f"No implementation registered for {interface_name}")

        implementation = self._services[interface_name]

        # Create instance with injected dependencies
        instance = implementation(**kwargs)

        return instance


# Global container instance
container = DIContainer()


def register_ingestion_services() -> None:
    """Register all ingestion-related services in the container"""
    from .interfaces import (
        IngestionPlanBuilderInterface,
        SourceExecutorInterface,
    )
    from .managers.IngestionPlanBuilder import IngestionPlanBuilder
    from .managers.SourceExecutor import SourceExecutor

    # Register services as singletons
    container.register_singleton(IngestionPlanBuilderInterface, IngestionPlanBuilder)
    container.register_singleton(SourceExecutorInterface, SourceExecutor)

    logger.info("Ingestion services registered in DI container")


def get_orchestrator_with_injection() -> "IngestionOrchestratorRefactored":
    """Get orchestrator instance with proper dependency injection"""
    from .IngestionOrchestratorRefactored import IngestionOrchestratorRefactored
    from .interfaces import (
        IngestionPlanBuilderInterface,
        SourceExecutorInterface,
    )

    # Get dependencies from container
    plan_builder = container.get(IngestionPlanBuilderInterface)
    source_executor = container.get(SourceExecutorInterface)

    # Create orchestrator with injected dependencies
    return IngestionOrchestratorRefactored(
        plan_builder=plan_builder,
        source_executor=source_executor,
    )


# Initialize services when module is imported
try:
    register_ingestion_services()
except ImportError as e:
    logger.warning(f"Could not register ingestion services: {e}")
