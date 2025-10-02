#!/usr/bin/env python3
"""PAKE System - Abstract Repository Interfaces
Repository Pattern implementation for clean separation of data access and business logic.

This module defines abstract repository interfaces (ports) that define contracts
for data access operations without specifying implementation details.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

# Generic type for domain entities
T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Abstract base repository interface for all domain entities"""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""

    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[T]:
        """Get all entities with optional filtering and pagination"""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity"""

    @abstractmethod
    async def update(self, entity_id: str, **kwargs) -> Optional[T]:
        """Update entity by ID"""

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""

    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""

    @abstractmethod
    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count entities matching filters"""


class AbstractUserRepository(AbstractRepository):
    """Abstract repository interface for User domain entity"""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[T]:
        """Get user by email address"""

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[T]:
        """Get user by username"""

    @abstractmethod
    async def get_active_users(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all active users"""

    @abstractmethod
    async def update_last_login(self, user_id: str, login_time: datetime) -> bool:
        """Update user's last login time"""

    @abstractmethod
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""

    @abstractmethod
    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""


class AbstractSearchHistoryRepository(AbstractRepository):
    """Abstract repository interface for SearchHistory domain entity"""

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get search history for a specific user"""

    @abstractmethod
    async def get_anonymous_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get anonymous search history"""

    @abstractmethod
    async def get_by_query_pattern(
        self,
        pattern: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get searches matching query pattern"""

    @abstractmethod
    async def get_recent_searches(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[T]:
        """Get recent searches within specified hours"""

    @abstractmethod
    async def get_cached_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get searches that resulted in cache hits"""

    @abstractmethod
    async def delete_old_searches(self, days: int = 30) -> int:
        """Delete searches older than specified days"""


class AbstractSavedSearchRepository(AbstractRepository):
    """Abstract repository interface for SavedSearch domain entity"""

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get saved searches for a specific user"""

    @abstractmethod
    async def get_public_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get public saved searches"""

    @abstractmethod
    async def get_by_tags(
        self,
        tags: list[str],
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get saved searches by tags"""

    @abstractmethod
    async def search_by_name(
        self,
        name_pattern: str,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Search saved searches by name pattern"""

    @abstractmethod
    async def get_most_popular(
        self,
        limit: int = 10,
    ) -> list[T]:
        """Get most popular saved searches"""


class AbstractServiceRegistryRepository(AbstractRepository):
    """Abstract repository interface for ServiceRegistry domain entity"""

    @abstractmethod
    async def get_by_name(self, service_name: str) -> Optional[T]:
        """Get service by name"""

    @abstractmethod
    async def get_by_type(
        self,
        service_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get services by type"""

    @abstractmethod
    async def get_by_environment(
        self,
        environment: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get services by environment"""

    @abstractmethod
    async def get_healthy_services(self) -> list[T]:
        """Get all healthy services"""

    @abstractmethod
    async def get_unhealthy_services(self) -> list[T]:
        """Get all unhealthy services"""

    @abstractmethod
    async def update_service_status(
        self,
        service_id: str,
        status: str,
    ) -> bool:
        """Update service health status"""


class AbstractServiceHealthCheckRepository(AbstractRepository):
    """Abstract repository interface for ServiceHealthCheck domain entity"""

    @abstractmethod
    async def get_by_service_id(
        self,
        service_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get health checks for a specific service"""

    @abstractmethod
    async def get_recent_checks(
        self,
        service_id: str,
        hours: int = 24,
        limit: int = 100,
    ) -> list[T]:
        """Get recent health checks for a service"""

    @abstractmethod
    async def get_failed_checks(
        self,
        service_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get failed health checks"""

    @abstractmethod
    async def get_average_response_time(
        self,
        service_id: str,
        hours: int = 24,
    ) -> Optional[float]:
        """Get average response time for a service"""


class AbstractServiceMetricsRepository(AbstractRepository):
    """Abstract repository interface for ServiceMetrics domain entity"""

    @abstractmethod
    async def get_by_service_id(
        self,
        service_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get metrics for a specific service"""

    @abstractmethod
    async def get_by_metric_name(
        self,
        metric_name: str,
        service_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get metrics by metric name"""

    @abstractmethod
    async def get_recent_metrics(
        self,
        service_id: str,
        hours: int = 24,
        limit: int = 100,
    ) -> list[T]:
        """Get recent metrics for a service"""

    @abstractmethod
    async def get_metric_average(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 24,
    ) -> Optional[float]:
        """Get average value for a specific metric"""

    @abstractmethod
    async def get_metric_trend(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Get metric trend data"""


class AbstractAPIGatewayRouteRepository(AbstractRepository):
    """Abstract repository interface for APIGatewayRoute domain entity"""

    @abstractmethod
    async def get_by_path_and_method(
        self,
        path: str,
        method: str,
    ) -> Optional[T]:
        """Get route by path and HTTP method"""

    @abstractmethod
    async def get_by_target_service(
        self,
        target_service: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get routes by target service"""

    @abstractmethod
    async def get_active_routes(self) -> list[T]:
        """Get all active routes"""

    @abstractmethod
    async def get_routes_requiring_auth(self) -> list[T]:
        """Get routes that require authentication"""

    @abstractmethod
    async def activate_route(self, route_id: str) -> bool:
        """Activate a route"""

    @abstractmethod
    async def deactivate_route(self, route_id: str) -> bool:
        """Deactivate a route"""


class AbstractSystemAlertRepository(AbstractRepository):
    """Abstract repository interface for SystemAlert domain entity"""

    @abstractmethod
    async def get_by_severity(
        self,
        severity: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get alerts by severity level"""

    @abstractmethod
    async def get_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get alerts by status"""

    @abstractmethod
    async def get_by_service(
        self,
        service_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get alerts by service name"""

    @abstractmethod
    async def get_active_alerts(self) -> list[T]:
        """Get all active alerts"""

    @abstractmethod
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> bool:
        """Acknowledge an alert"""

    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""

    @abstractmethod
    async def get_critical_alerts(self) -> list[T]:
        """Get all critical alerts"""
