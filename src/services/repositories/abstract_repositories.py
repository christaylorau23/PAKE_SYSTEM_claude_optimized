#!/usr/bin/env python3
"""PAKE System - Abstract Repository Interfaces
Repository Pattern implementation for clean separation of data access and business logic.

This module defines abstract repository interfaces (ports) that define contracts
for data access operations without specifying implementation details.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Generic, TypeVar
from uuid import UUID

# Generic type for domain entities
T = TypeVar('T')


class AbstractRepository(ABC, Generic[T]):
    """Abstract base repository interface for all domain entities"""
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """Get all entities with optional filtering and pagination"""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity"""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, **kwargs) -> Optional[T]:
        """Update entity by ID"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching filters"""
        pass


class AbstractUserRepository(AbstractRepository):
    """Abstract repository interface for User domain entity"""
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[T]:
        """Get user by email address"""
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[T]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def get_active_users(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all active users"""
        pass
    
    @abstractmethod
    async def update_last_login(self, user_id: str, login_time: datetime) -> bool:
        """Update user's last login time"""
        pass
    
    @abstractmethod
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        pass
    
    @abstractmethod
    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        pass


class AbstractSearchHistoryRepository(AbstractRepository):
    """Abstract repository interface for SearchHistory domain entity"""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get search history for a specific user"""
        pass
    
    @abstractmethod
    async def get_anonymous_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get anonymous search history"""
        pass
    
    @abstractmethod
    async def get_by_query_pattern(
        self,
        pattern: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get searches matching query pattern"""
        pass
    
    @abstractmethod
    async def get_recent_searches(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[T]:
        """Get recent searches within specified hours"""
        pass
    
    @abstractmethod
    async def get_cached_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get searches that resulted in cache hits"""
        pass
    
    @abstractmethod
    async def delete_old_searches(self, days: int = 30) -> int:
        """Delete searches older than specified days"""
        pass


class AbstractSavedSearchRepository(AbstractRepository):
    """Abstract repository interface for SavedSearch domain entity"""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get saved searches for a specific user"""
        pass
    
    @abstractmethod
    async def get_public_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get public saved searches"""
        pass
    
    @abstractmethod
    async def get_by_tags(
        self,
        tags: List[str],
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get saved searches by tags"""
        pass
    
    @abstractmethod
    async def search_by_name(
        self,
        name_pattern: str,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Search saved searches by name pattern"""
        pass
    
    @abstractmethod
    async def get_most_popular(
        self,
        limit: int = 10,
    ) -> List[T]:
        """Get most popular saved searches"""
        pass


class AbstractServiceRegistryRepository(AbstractRepository):
    """Abstract repository interface for ServiceRegistry domain entity"""
    
    @abstractmethod
    async def get_by_name(self, service_name: str) -> Optional[T]:
        """Get service by name"""
        pass
    
    @abstractmethod
    async def get_by_type(
        self,
        service_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get services by type"""
        pass
    
    @abstractmethod
    async def get_by_environment(
        self,
        environment: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get services by environment"""
        pass
    
    @abstractmethod
    async def get_healthy_services(self) -> List[T]:
        """Get all healthy services"""
        pass
    
    @abstractmethod
    async def get_unhealthy_services(self) -> List[T]:
        """Get all unhealthy services"""
        pass
    
    @abstractmethod
    async def update_service_status(
        self,
        service_id: str,
        status: str,
    ) -> bool:
        """Update service health status"""
        pass


class AbstractServiceHealthCheckRepository(AbstractRepository):
    """Abstract repository interface for ServiceHealthCheck domain entity"""
    
    @abstractmethod
    async def get_by_service_id(
        self,
        service_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get health checks for a specific service"""
        pass
    
    @abstractmethod
    async def get_recent_checks(
        self,
        service_id: str,
        hours: int = 24,
        limit: int = 100,
    ) -> List[T]:
        """Get recent health checks for a service"""
        pass
    
    @abstractmethod
    async def get_failed_checks(
        self,
        service_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get failed health checks"""
        pass
    
    @abstractmethod
    async def get_average_response_time(
        self,
        service_id: str,
        hours: int = 24,
    ) -> Optional[float]:
        """Get average response time for a service"""
        pass


class AbstractServiceMetricsRepository(AbstractRepository):
    """Abstract repository interface for ServiceMetrics domain entity"""
    
    @abstractmethod
    async def get_by_service_id(
        self,
        service_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get metrics for a specific service"""
        pass
    
    @abstractmethod
    async def get_by_metric_name(
        self,
        metric_name: str,
        service_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get metrics by metric name"""
        pass
    
    @abstractmethod
    async def get_recent_metrics(
        self,
        service_id: str,
        hours: int = 24,
        limit: int = 100,
    ) -> List[T]:
        """Get recent metrics for a service"""
        pass
    
    @abstractmethod
    async def get_metric_average(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 24,
    ) -> Optional[float]:
        """Get average value for a specific metric"""
        pass
    
    @abstractmethod
    async def get_metric_trend(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get metric trend data"""
        pass


class AbstractAPIGatewayRouteRepository(AbstractRepository):
    """Abstract repository interface for APIGatewayRoute domain entity"""
    
    @abstractmethod
    async def get_by_path_and_method(
        self,
        path: str,
        method: str,
    ) -> Optional[T]:
        """Get route by path and HTTP method"""
        pass
    
    @abstractmethod
    async def get_by_target_service(
        self,
        target_service: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get routes by target service"""
        pass
    
    @abstractmethod
    async def get_active_routes(self) -> List[T]:
        """Get all active routes"""
        pass
    
    @abstractmethod
    async def get_routes_requiring_auth(self) -> List[T]:
        """Get routes that require authentication"""
        pass
    
    @abstractmethod
    async def activate_route(self, route_id: str) -> bool:
        """Activate a route"""
        pass
    
    @abstractmethod
    async def deactivate_route(self, route_id: str) -> bool:
        """Deactivate a route"""
        pass


class AbstractSystemAlertRepository(AbstractRepository):
    """Abstract repository interface for SystemAlert domain entity"""
    
    @abstractmethod
    async def get_by_severity(
        self,
        severity: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get alerts by severity level"""
        pass
    
    @abstractmethod
    async def get_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get alerts by status"""
        pass
    
    @abstractmethod
    async def get_by_service(
        self,
        service_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get alerts by service name"""
        pass
    
    @abstractmethod
    async def get_active_alerts(self) -> List[T]:
        """Get all active alerts"""
        pass
    
    @abstractmethod
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> bool:
        """Acknowledge an alert"""
        pass
    
    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        pass
    
    @abstractmethod
    async def get_critical_alerts(self) -> List[T]:
        """Get all critical alerts"""
        pass
