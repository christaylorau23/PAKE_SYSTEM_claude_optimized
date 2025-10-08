#!/usr/bin/env python3
"""PAKE System - Repository Dependency Injection Container
Manages repository dependencies and provides clean separation between
business logic and data access concerns.
"""

import logging
from typing import Any, Dict, TypeVar

import asyncpg
import psycopg2
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from .abstract_repositories import (
    AbstractAPIGatewayRouteRepository,
    AbstractSavedSearchRepository,
    AbstractSearchHistoryRepository,
    AbstractServiceHealthCheckRepository,
    AbstractServiceMetricsRepository,
    AbstractServiceRegistryRepository,
    AbstractSystemAlertRepository,
    AbstractUserRepository,
)
from .sqlalchemy_repositories import (
    SQLAlchemySearchHistoryRepository,
    SQLAlchemyUserRepository,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RepositoryContainer:
    """Dependency injection container for repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._repositories: dict[str, Any] = {}
        self._initialize_repositories()

    def _initialize_repositories(self) -> None:
        """Initialize all repository instances."""
        try:
            # Initialize SQLAlchemy repositories
            self._repositories["user"] = SQLAlchemyUserRepository(self.session)
            self._repositories["search_history"] = SQLAlchemySearchHistoryRepository(
                self.session
            )

            # TODO: Initialize other repositories as they are implemented
            # self._repositories['saved_search'] = SQLAlchemySavedSearchRepository(self.session)
            # self._repositories['service_registry'] = SQLAlchemyServiceRegistryRepository(self.session)
            # self._repositories['service_health_check'] = SQLAlchemyServiceHealthCheckRepository(self.session)
            # self._repositories['service_metrics'] = SQLAlchemyServiceMetricsRepository(self.session)
            # self._repositories['api_gateway_route'] = SQLAlchemyAPIGatewayRouteRepository(self.session)
            # self._repositories['system_alert'] = SQLAlchemySystemAlertRepository(self.session)

            logger.info("Repository container initialized successfully")

        except (sqlalchemy.exc.SQLAlchemyError, psycopg2.Error, asyncpg.Error) as e:
            logger.error("Error initializing repository container: %s", e)
            raise

    def get_user_repository(self) -> AbstractUserRepository:
        """Get user repository instance."""
        return self._repositories["user"]

    def get_search_history_repository(self) -> AbstractSearchHistoryRepository:
        """Get search history repository instance."""
        return self._repositories["search_history"]

    def get_saved_search_repository(self) -> AbstractSavedSearchRepository:
        """Get saved search repository instance."""
        # TODO: Implement when SQLAlchemySavedSearchRepository is created
        msg = "SavedSearch repository not yet implemented"
        raise NotImplementedError(msg)

    def get_service_registry_repository(self) -> AbstractServiceRegistryRepository:
        """Get service registry repository instance."""
        # TODO: Implement when SQLAlchemyServiceRegistryRepository is created
        msg = "ServiceRegistry repository not yet implemented"
        raise NotImplementedError(msg)

    def get_service_health_check_repository(
        self,
    ) -> AbstractServiceHealthCheckRepository:
        """Get service health check repository instance."""
        # TODO: Implement when SQLAlchemyServiceHealthCheckRepository is created
        msg = "ServiceHealthCheck repository not yet implemented"
        raise NotImplementedError(msg)

    def get_service_metrics_repository(self) -> AbstractServiceMetricsRepository:
        """Get service metrics repository instance."""
        # TODO: Implement when SQLAlchemyServiceMetricsRepository is created
        msg = "ServiceMetrics repository not yet implemented"
        raise NotImplementedError(msg)

    def get_api_gateway_route_repository(self) -> AbstractAPIGatewayRouteRepository:
        """Get API gateway route repository instance."""
        # TODO: Implement when SQLAlchemyAPIGatewayRouteRepository is created
        msg = "APIGatewayRoute repository not yet implemented"
        raise NotImplementedError(msg)

    def get_system_alert_repository(self) -> AbstractSystemAlertRepository:
        """Get system alert repository instance."""
        # TODO: Implement when SQLAlchemySystemAlertRepository is created
        msg = "SystemAlert repository not yet implemented"
        raise NotImplementedError(msg)

    def get_repository(self, repository_name: str) -> Any:
        """Get repository by name."""
        if repository_name not in self._repositories:
            msg = f"Repository '{repository_name}' not found"
            raise ValueError(msg)
        return self._repositories[repository_name]

    def register_repository(self, name: str, repository: Any) -> None:
        """Register a custom repository."""
        self._repositories[name] = repository
        logger.info("Registered custom repository: %s", name)

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all repositories."""
        health_status = {
            "status": "healthy",
            "repositories": {},
            "session_active": self.session.is_active
            if hasattr(self.session, "is_active")
            else True,
        }

        # Test each repository
        for name, repository in self._repositories.items():
            try:
                # Simple health check - try to count entities
                if hasattr(repository, "count"):
                    await repository.count()
                    health_status["repositories"][name] = "healthy"
                else:
                    health_status["repositories"][name] = "no_count_method"
            except (ValueError, RuntimeError) as e:
                health_status["repositories"][name] = f"unhealthy: {str(e)}"
                health_status["status"] = "unhealthy"

        return health_status


class RepositoryFactory:
    """Factory for creating repository containers with different configurations."""

    @staticmethod
    def create_container(session: AsyncSession) -> RepositoryContainer:
        """Create a new repository container with the given session."""
        return RepositoryContainer(session)

    @staticmethod
    def create_with_fake_repositories() -> "FakeRepositoryContainer":
        """Create a container with fake repositories for testing."""
        return FakeRepositoryContainer()


class FakeRepositoryContainer:
    """Container with fake repositories for unit testing."""

    def __init__(self) -> None:
        self._repositories: dict[str, Any] = {}
        self._initialize_fake_repositories()

    def _initialize_fake_repositories(self) -> None:
        """Initialize fake repositories for testing."""
        from .fake_repositories import (
            FakeSearchHistoryRepository,
            FakeUserRepository,
        )

        self._repositories["user"] = FakeUserRepository()
        self._repositories["search_history"] = FakeSearchHistoryRepository()

        logger.info("Fake repository container initialized for testing")

    def get_user_repository(self) -> AbstractUserRepository:
        """Get fake user repository instance."""
        return self._repositories["user"]

    def get_search_history_repository(self) -> AbstractSearchHistoryRepository:
        """Get fake search history repository instance."""
        return self._repositories["search_history"]

    def get_repository(self, repository_name: str) -> Any:
        """Get fake repository by name."""
        if repository_name not in self._repositories:
            msg = f"Fake repository '{repository_name}' not found"
            raise ValueError(msg)
        return self._repositories[repository_name]

    async def health_check(self) -> dict[str, Any]:
        """Fake health check always returns healthy."""
        return {
            "status": "healthy",
            "repositories": dict.fromkeys(self._repositories, "healthy"),
            "session_active": True,
            "fake_mode": True,
        }
