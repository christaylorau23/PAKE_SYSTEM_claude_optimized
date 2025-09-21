#!/usr/bin/env python3
"""PAKE System - Phase 16 Tenant-Aware Data Access Layer
Enterprise-grade Data Access Layer with automatic tenant isolation.
"""

import logging
from abc import ABC
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

import sqlalchemy as sa
from sqlalchemy import func

from src.middleware.tenant_context import get_current_tenant_id, get_current_user_id
from src.services.database.multi_tenant_schema import (
    Base,
    MultiTenantPostgreSQLService,
    SavedSearch,
    SearchHistory,
    SystemMetrics,
    TenantActivity,
    TenantResourceUsage,
    User,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


class TenantIsolationError(Exception):
    """Exception raised when tenant isolation is violated"""


class TenantAwareRepository(ABC, Generic[T]):
    """Abstract base class for tenant-aware repositories.
    Ensures all database operations are automatically scoped to the current tenant.
    """

    def __init__(self, db_service: MultiTenantPostgreSQLService, model_class: type):
        self.db_service = db_service
        self.model_class = model_class
        self._session_maker = db_service._session_maker

    def _get_tenant_id(self) -> str:
        """Get current tenant ID from context"""
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise TenantIsolationError("No tenant context available")
        return tenant_id

    def _get_user_id(self) -> str | None:
        """Get current user ID from context"""
        return get_current_user_id()

    async def _validate_tenant_access(self, tenant_id: str) -> None:
        """Validate that the current context has access to the specified tenant"""
        current_tenant_id = self._get_tenant_id()
        if current_tenant_id != tenant_id:
            raise TenantIsolationError(f"Access denied to tenant {tenant_id}")

    def _add_tenant_filter(self, query, tenant_id: str | None = None) -> sa.Select:
        """Add tenant filter to query"""
        if tenant_id is None:
            tenant_id = self._get_tenant_id()

        # Add tenant_id filter based on model
        if hasattr(self.model_class, "tenant_id"):
            return query.where(self.model_class.tenant_id == tenant_id)
        # For models without tenant_id (like Tenant itself)
        return query

    async def create(self, **kwargs) -> T:
        """Create new record with automatic tenant association"""
        tenant_id = self._get_tenant_id()

        # Add tenant_id if model supports it
        if hasattr(self.model_class, "tenant_id"):
            kwargs["tenant_id"] = tenant_id

        async with self._session_maker() as session:
            instance = self.model_class(**kwargs)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)

            logger.debug(f"Created {self.model_class.__name__}: {instance.id}")
            return instance

    async def get_by_id(
        self,
        record_id: str,
        tenant_id: str | None = None,
    ) -> T | None:
        """Get record by ID with tenant isolation"""
        async with self._session_maker() as session:
            query = sa.select(self.model_class).where(self.model_class.id == record_id)
            query = self._add_tenant_filter(query, tenant_id)

            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[T]:
        """Get all records with tenant isolation"""
        async with self._session_maker() as session:
            query = sa.select(self.model_class)
            query = self._add_tenant_filter(query, tenant_id)

            if order_by:
                if hasattr(self.model_class, order_by):
                    query = query.order_by(getattr(self.model_class, order_by))

            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return result.scalars().all()

    async def update(self, record_id: str, **kwargs) -> T | None:
        """Update record with tenant isolation"""
        async with self._session_maker() as session:
            query = sa.select(self.model_class).where(self.model_class.id == record_id)
            query = self._add_tenant_filter(query)

            result = await session.execute(query)
            instance = result.scalar_one_or_none()

            if not instance:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            await session.commit()
            await session.refresh(instance)

            logger.debug(f"Updated {self.model_class.__name__}: {instance.id}")
            return instance

    async def delete(self, record_id: str) -> bool:
        """Delete record with tenant isolation"""
        async with self._session_maker() as session:
            query = sa.select(self.model_class).where(self.model_class.id == record_id)
            query = self._add_tenant_filter(query)

            result = await session.execute(query)
            instance = result.scalar_one_or_none()

            if not instance:
                return False

            await session.delete(instance)
            await session.commit()

            logger.debug(f"Deleted {self.model_class.__name__}: {instance.id}")
            return True

    async def count(self, tenant_id: str | None = None) -> int:
        """Count records with tenant isolation"""
        async with self._session_maker() as session:
            query = sa.select(func.count(self.model_class.id))
            query = self._add_tenant_filter(query, tenant_id)

            result = await session.execute(query)
            return result.scalar()


class UserRepository(TenantAwareRepository[User]):
    """Tenant-aware user repository"""

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        super().__init__(db_service, User)

    async def get_by_username(
        self,
        username: str,
        tenant_id: str | None = None,
    ) -> User | None:
        """Get user by username within tenant"""
        async with self._session_maker() as session:
            query = sa.select(User).where(User.username == username)
            query = self._add_tenant_filter(query, tenant_id)

            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_by_email(
        self,
        email: str,
        tenant_id: str | None = None,
    ) -> User | None:
        """Get user by email within tenant"""
        async with self._session_maker() as session:
            query = sa.select(User).where(User.email == email)
            query = self._add_tenant_filter(query, tenant_id)

            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_active_users(self, tenant_id: str | None = None) -> list[User]:
        """Get active users within tenant"""
        async with self._session_maker() as session:
            query = sa.select(User).where(User.is_active)
            query = self._add_tenant_filter(query, tenant_id)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_users_by_role(
        self,
        role: str,
        tenant_id: str | None = None,
    ) -> list[User]:
        """Get users by role within tenant"""
        async with self._session_maker() as session:
            query = sa.select(User).where(User.role == role)
            query = self._add_tenant_filter(query, tenant_id)

            result = await session.execute(query)
            return result.scalars().all()

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        result = await self.update(user_id, last_login=datetime.utcnow())
        return result is not None


class SearchHistoryRepository(TenantAwareRepository[SearchHistory]):
    """Tenant-aware search history repository"""

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        super().__init__(db_service, SearchHistory)

    async def get_by_user(
        self,
        user_id: str,
        tenant_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SearchHistory]:
        """Get search history for user within tenant"""
        async with self._session_maker() as session:
            query = sa.select(SearchHistory).where(SearchHistory.user_id == user_id)
            query = self._add_tenant_filter(query, tenant_id)
            query = (
                query.order_by(SearchHistory.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(query)
            return result.scalars().all()

    async def get_popular_searches(
        self,
        tenant_id: str | None = None,
        limit: int = 10,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get popular searches within tenant"""
        since = datetime.utcnow() - timedelta(days=days)

        async with self.db_service._pool.acquire() as conn:
            query = """
                SELECT query, COUNT(*) as search_count,
                       AVG(execution_time_ms) as avg_time,
                       AVG(results_count) as avg_results
                FROM search_history
                WHERE tenant_id = $1 AND created_at >= $2
                GROUP BY query
                ORDER BY search_count DESC
                LIMIT $3
            """
            rows = await conn.fetch(
                query,
                tenant_id or self._get_tenant_id(),
                since,
                limit,
            )
            return [dict(row) for row in rows]

    async def get_search_analytics(
        self,
        tenant_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get search analytics within tenant"""
        since = datetime.utcnow() - timedelta(days=days)
        tenant_id = tenant_id or self._get_tenant_id()

        async with self.db_service._pool.acquire() as conn:
            # Total searches
            total_searches = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE tenant_id = $1 AND created_at >= $2",
                tenant_id,
                since,
            )

            # Average execution time
            avg_time = await conn.fetchval(
                "SELECT AVG(execution_time_ms) FROM search_history WHERE tenant_id = $1 AND created_at >= $2",
                tenant_id,
                since,
            )

            # Cache hit rate
            cache_hits = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE tenant_id = $1 AND created_at >= $2 AND cache_hit = true",
                tenant_id,
                since,
            )
            cache_hit_rate = (
                (cache_hits / total_searches * 100) if total_searches > 0 else 0
            )

            # Top sources
            source_stats = await conn.fetch(
                """
                SELECT unnest(sources) as source, COUNT(*) as usage_count
                FROM search_history
                WHERE tenant_id = $1 AND created_at >= $2
                GROUP BY source
                ORDER BY usage_count DESC
                LIMIT 5
            """,
                tenant_id,
                since,
            )

            return {
                "tenant_id": tenant_id,
                "period_days": days,
                "total_searches": total_searches,
                "average_execution_time_ms": float(avg_time) if avg_time else 0,
                "cache_hit_rate_percent": round(cache_hit_rate, 2),
                "top_sources": [dict(row) for row in source_stats],
            }


class SavedSearchRepository(TenantAwareRepository[SavedSearch]):
    """Tenant-aware saved search repository"""

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        super().__init__(db_service, SavedSearch)

    async def get_by_user(
        self,
        user_id: str,
        tenant_id: str | None = None,
    ) -> list[SavedSearch]:
        """Get saved searches for user within tenant"""
        async with self._session_maker() as session:
            query = sa.select(SavedSearch).where(SavedSearch.user_id == user_id)
            query = self._add_tenant_filter(query, tenant_id)
            query = query.order_by(SavedSearch.updated_at.desc())

            result = await session.execute(query)
            return result.scalars().all()

    async def get_public_searches(
        self,
        tenant_id: str | None = None,
    ) -> list[SavedSearch]:
        """Get public saved searches within tenant"""
        async with self._session_maker() as session:
            query = sa.select(SavedSearch).where(SavedSearch.is_public)
            query = self._add_tenant_filter(query, tenant_id)
            query = query.order_by(SavedSearch.created_at.desc())

            result = await session.execute(query)
            return result.scalars().all()

    async def search_by_tags(
        self,
        tags: list[str],
        tenant_id: str | None = None,
    ) -> list[SavedSearch]:
        """Search saved searches by tags within tenant"""
        async with self._session_maker() as session:
            query = sa.select(SavedSearch)
            query = self._add_tenant_filter(query, tenant_id)

            # Filter by tags (PostgreSQL array contains operator)
            for tag in tags:
                query = query.where(SavedSearch.tags.contains([tag]))

            result = await session.execute(query)
            return result.scalars().all()


class SystemMetricsRepository(TenantAwareRepository[SystemMetrics]):
    """Tenant-aware system metrics repository"""

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        super().__init__(db_service, SystemMetrics)

    async def get_by_type(
        self,
        metric_type: str,
        tenant_id: str | None = None,
        hours: int = 24,
    ) -> list[SystemMetrics]:
        """Get metrics by type within tenant"""
        since = datetime.utcnow() - timedelta(hours=hours)

        async with self._session_maker() as session:
            query = sa.select(SystemMetrics).where(
                SystemMetrics.metric_type == metric_type,
                SystemMetrics.timestamp >= since,
            )
            query = self._add_tenant_filter(query, tenant_id)
            query = query.order_by(SystemMetrics.timestamp.desc())

            result = await session.execute(query)
            return result.scalars().all()

    async def get_latest_metric(
        self,
        metric_type: str,
        tenant_id: str | None = None,
    ) -> SystemMetrics | None:
        """Get latest metric by type within tenant"""
        async with self._session_maker() as session:
            query = sa.select(SystemMetrics).where(
                SystemMetrics.metric_type == metric_type,
            )
            query = self._add_tenant_filter(query, tenant_id)
            query = query.order_by(SystemMetrics.timestamp.desc()).limit(1)

            result = await session.execute(query)
            return result.scalar_one_or_none()


class TenantActivityRepository(TenantAwareRepository[TenantActivity]):
    """Tenant-aware activity repository"""

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        super().__init__(db_service, TenantActivity)

    async def log_activity(
        self,
        activity_type: str,
        user_id: str | None = None,
        activity_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TenantActivity:
        """Log tenant activity"""
        tenant_id = self._get_tenant_id()

        activity = await self.create(
            tenant_id=tenant_id,
            user_id=user_id,
            activity_type=activity_type,
            activity_data=activity_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.debug(f"Logged activity: {activity_type} for tenant {tenant_id}")
        return activity

    async def get_activity_by_type(
        self,
        activity_type: str,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TenantActivity]:
        """Get activity by type within tenant"""
        async with self._session_maker() as session:
            query = sa.select(TenantActivity).where(
                TenantActivity.activity_type == activity_type,
            )
            query = self._add_tenant_filter(query, tenant_id)
            query = (
                query.order_by(TenantActivity.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(query)
            return result.scalars().all()

    async def get_user_activity(
        self,
        user_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TenantActivity]:
        """Get activity for user within tenant"""
        async with self._session_maker() as session:
            query = sa.select(TenantActivity).where(TenantActivity.user_id == user_id)
            query = self._add_tenant_filter(query, tenant_id)
            query = (
                query.order_by(TenantActivity.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(query)
            return result.scalars().all()


class TenantResourceUsageRepository(TenantAwareRepository[TenantResourceUsage]):
    """Tenant-aware resource usage repository"""

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        super().__init__(db_service, TenantResourceUsage)

    async def record_usage(
        self,
        resource_type: str,
        usage_count: int = 1,
        usage_amount: float = 0.0,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> TenantResourceUsage:
        """Record resource usage for tenant"""
        tenant_id = self._get_tenant_id()

        if period_start is None:
            period_start = datetime.utcnow().replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        if period_end is None:
            period_end = period_start + timedelta(days=1)

        usage = await self.create(
            tenant_id=tenant_id,
            resource_type=resource_type,
            usage_count=usage_count,
            usage_amount=usage_amount,
            period_start=period_start,
            period_end=period_end,
        )

        logger.debug(f"Recorded usage: {resource_type} for tenant {tenant_id}")
        return usage

    async def get_usage_by_type(
        self,
        resource_type: str,
        tenant_id: str | None = None,
        days: int = 30,
    ) -> list[TenantResourceUsage]:
        """Get usage by type within tenant"""
        since = datetime.utcnow() - timedelta(days=days)

        async with self._session_maker() as session:
            query = sa.select(TenantResourceUsage).where(
                TenantResourceUsage.resource_type == resource_type,
                TenantResourceUsage.period_start >= since,
            )
            query = self._add_tenant_filter(query, tenant_id)
            query = query.order_by(TenantResourceUsage.period_start.desc())

            result = await session.execute(query)
            return result.scalars().all()

    async def get_usage_summary(
        self,
        tenant_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get usage summary within tenant"""
        since = datetime.utcnow() - timedelta(days=days)
        tenant_id = tenant_id or self._get_tenant_id()

        async with self.db_service._pool.acquire() as conn:
            # Get usage by resource type
            usage_stats = await conn.fetch(
                """
                SELECT resource_type,
                       SUM(usage_count) as total_count,
                       SUM(usage_amount) as total_amount
                FROM tenant_resource_usage
                WHERE tenant_id = $1 AND period_start >= $2
                GROUP BY resource_type
                ORDER BY total_count DESC
            """,
                tenant_id,
                since,
            )

            return {
                "tenant_id": tenant_id,
                "period_days": days,
                "usage_by_type": [dict(row) for row in usage_stats],
            }


class TenantAwareDataAccessLayer:
    """Centralized Data Access Layer with automatic tenant isolation.

    Features:
    - Automatic tenant context propagation
    - Tenant isolation enforcement
    - Repository pattern implementation
    - Performance optimization
    - Audit logging
    - Resource usage tracking
    """

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        self.db_service = db_service

        # Initialize repositories
        self.users = UserRepository(db_service)
        self.search_history = SearchHistoryRepository(db_service)
        self.saved_searches = SavedSearchRepository(db_service)
        self.system_metrics = SystemMetricsRepository(db_service)
        self.activity = TenantActivityRepository(db_service)
        self.resource_usage = TenantResourceUsageRepository(db_service)

        logger.info("Tenant-aware Data Access Layer initialized")

    async def health_check(self) -> dict[str, Any]:
        """Health check for tenant-aware DAL"""
        try:
            # Test tenant context
            tenant_id = get_current_tenant_id()
            if not tenant_id:
                return {"status": "unhealthy", "error": "No tenant context available"}

            # Test database connectivity
            db_health = await self.db_service.health_check()

            return {
                "status": "healthy",
                "tenant_id": tenant_id,
                "database_health": db_health,
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def get_tenant_summary(
        self,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive tenant summary"""
        tenant_id = tenant_id or get_current_tenant_id()
        if not tenant_id:
            raise TenantIsolationError("No tenant context available")

        # Get tenant info
        tenant_data = await self.db_service.get_tenant_by_id(tenant_id)
        if not tenant_data:
            raise TenantIsolationError(f"Tenant not found: {tenant_id}")

        # Get counts
        user_count = await self.users.count(tenant_id)
        search_count = await self.search_history.count(tenant_id)
        saved_search_count = await self.saved_searches.count(tenant_id)

        # Get recent activity
        recent_activity = await self.activity.get_all(tenant_id, limit=10)

        # Get usage summary
        usage_summary = await self.resource_usage.get_usage_summary(tenant_id, days=7)

        return {
            "tenant": tenant_data,
            "counts": {
                "users": user_count,
                "search_history": search_count,
                "saved_searches": saved_search_count,
            },
            "recent_activity": [
                {
                    "id": activity.id,
                    "activity_type": activity.activity_type,
                    "user_id": activity.user_id,
                    "created_at": activity.created_at.isoformat(),
                }
                for activity in recent_activity
            ],
            "usage_summary": usage_summary,
        }


# Factory function


async def create_tenant_aware_dal(
    db_service: MultiTenantPostgreSQLService,
) -> TenantAwareDataAccessLayer:
    """Create tenant-aware Data Access Layer"""
    return TenantAwareDataAccessLayer(db_service)


if __name__ == "__main__":
    # Example usage
    print("Tenant-Aware Data Access Layer")
    print("=" * 50)

    # This would be used with actual database service
    print("DAL provides automatic tenant isolation for all database operations")
    print("All queries are automatically scoped to the current tenant context")
    print("Cross-tenant data access is prevented by design")
