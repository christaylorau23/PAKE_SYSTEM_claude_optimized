#!/usr/bin/env python3
"""PAKE System - Phase 16 Multi-Tenant Database Schema
Enterprise-grade multi-tenant database schema with tenant isolation.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import asyncpg
import sqlalchemy as sa
from asyncpg import Pool
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

logger = logging.getLogger(__name__)

# SQLAlchemy Models - Multi-Tenant Architecture
Base = declarative_base()


class Tenant(Base):
    """Central tenant management model"""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
    )  # For subdomain routing
    # active, suspended, trial, expired
    status: Mapped[str] = mapped_column(String(50), default="active")
    # basic, professional, enterprise
    plan: Mapped[str] = mapped_column(String(50), default="basic")
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
    )  # Tenant-specific settings
    limits: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # Resource limits
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
    )  # For trial/expired tenants

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    search_history: Mapped[list["SearchHistory"]] = relationship(
        "SearchHistory",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    saved_searches: Mapped[list["SavedSearch"]] = relationship(
        "SavedSearch",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    system_metrics: Mapped[list["SystemMetrics"]] = relationship(
        "SystemMetrics",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class User(Base):
    """User account model with tenant association"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    REDACTED_SECRET_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(
        String(50),
        default="user",
    )  # user, admin, super_admin
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    # Composite unique constraint for username within tenant
    __table_args__ = (
        Index("idx_users_tenant_username", "tenant_id", "username", unique=True),
        Index("idx_users_tenant_email", "tenant_id", "email", unique=True),
    )


class SearchHistory(Base):
    """Search history tracking model with tenant association"""

    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )  # Nullable for anonymous searches
    query: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_time_ms: Mapped[float] = mapped_column(sa.Float)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_score: Mapped[float | None] = mapped_column(sa.Float)
    query_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="search_history")


class SavedSearch(Base):
    """Saved search queries model with tenant association"""

    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="saved_searches")


class SystemMetrics(Base):
    """System performance metrics model with tenant association"""

    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 'search_performance', 'cache_stats', etc.
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="system_metrics")


# Additional Multi-Tenant Models


class TenantInvitation(Base):
    """Tenant invitation management"""

    __tablename__ = "tenant_invitations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user")
    invited_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
    )  # User ID who sent invitation
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # pending, accepted, expired, revoked
    status: Mapped[str] = mapped_column(String(50), default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)


class TenantActivity(Base):
    """Tenant activity logging for audit and analytics"""

    __tablename__ = "tenant_activity"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    # 'login', 'search', 'admin_action', etc.
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TenantResourceUsage(Base):
    """Tenant resource usage tracking"""

    __tablename__ = "tenant_resource_usage"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 'api_calls', 'storage', 'compute', etc.
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    # For storage, bandwidth, etc.
    usage_amount: Mapped[float] = mapped_column(sa.Float, default=0.0)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Performance Indexes for Multi-Tenancy


class MultiTenantIndexes:
    """Centralized index definitions for optimal multi-tenant performance"""

    @staticmethod
    def create_indexes():
        """Create all performance indexes for multi-tenant queries"""
        indexes = [
            # Tenant-based indexes for all tables
            Index("idx_users_tenant_id", User.tenant_id),
            Index("idx_search_history_tenant_id", SearchHistory.tenant_id),
            Index("idx_saved_searches_tenant_id", SavedSearch.tenant_id),
            Index("idx_system_metrics_tenant_id", SystemMetrics.tenant_id),
            Index("idx_tenant_invitations_tenant_id", TenantInvitation.tenant_id),
            Index("idx_tenant_activity_tenant_id", TenantActivity.tenant_id),
            Index("idx_tenant_resource_usage_tenant_id", TenantResourceUsage.tenant_id),
            # Composite indexes for common query patterns
            Index(
                "idx_search_history_tenant_user",
                SearchHistory.tenant_id,
                SearchHistory.user_id,
            ),
            Index(
                "idx_search_history_tenant_created",
                SearchHistory.tenant_id,
                SearchHistory.created_at,
            ),
            Index(
                "idx_saved_searches_tenant_user",
                SavedSearch.tenant_id,
                SavedSearch.user_id,
            ),
            Index(
                "idx_system_metrics_tenant_type",
                SystemMetrics.tenant_id,
                SystemMetrics.metric_type,
            ),
            Index(
                "idx_tenant_activity_tenant_type",
                TenantActivity.tenant_id,
                TenantActivity.activity_type,
            ),
            Index(
                "idx_tenant_resource_usage_tenant_type",
                TenantResourceUsage.tenant_id,
                TenantResourceUsage.resource_type,
            ),
            # Time-based indexes for analytics
            Index("idx_search_history_created_at", SearchHistory.created_at),
            Index("idx_system_metrics_timestamp", SystemMetrics.timestamp),
            Index("idx_tenant_activity_created_at", TenantActivity.created_at),
            Index(
                "idx_tenant_resource_usage_period",
                TenantResourceUsage.period_start,
                TenantResourceUsage.period_end,
            ),
            # Tenant status and domain indexes
            Index("idx_tenants_status", Tenant.status),
            Index("idx_tenants_domain", Tenant.domain),
            Index("idx_tenants_plan", Tenant.plan),
        ]
        return indexes


@dataclass
class MultiTenantDatabaseConfig:
    """Multi-tenant database configuration"""

    host: str = "localhost"
    port: int = 5432
    database: str = "pake_system"
    username: str = "pake_user"
    REDACTED_SECRET: str = "secure_REDACTED_SECRET"
    pool_min_size: int = 10
    pool_max_size: int = 20
    pool_max_queries: int = 50000
    pool_max_inactive_connection_lifetime: float = 300.0
    echo: bool = False
    # Multi-tenant specific settings
    max_tenants_per_pool: int = 100
    tenant_isolation_level: str = "strict"  # strict, relaxed
    cross_tenant_analytics: bool = (
        True  # Allow cross-tenant analytics for platform insights
    )


class MultiTenantPostgreSQLService:
    """Enterprise Multi-Tenant PostgreSQL database service.

    Features:
    - Complete tenant isolation at database level
    - Automatic tenant context propagation
    - Performance-optimized indexes for multi-tenant queries
    - Tenant resource usage tracking
    - Activity logging and audit trails
    - Cross-tenant analytics capabilities
    """

    def __init__(self, config: MultiTenantDatabaseConfig):
        self.config = config
        self._pool: Pool | None = None
        self._engine = None
        self._session_maker = None

        # Build connection strings
        self._async_url = f"postgresql+asyncpg://{config.username}:{config.REDACTED_SECRET}@{config.host}:{config.port}/{config.database}"
        self._sync_url = f"postgresql://{config.username}:{config.REDACTED_SECRET}@{config.host}:{config.port}/{config.database}"

        logger.info("Multi-tenant PostgreSQL service initialized")

    async def initialize(self) -> None:
        """Initialize database connections and run migrations"""
        try:
            # Create asyncpg connection pool
            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                REDACTED_SECRET=self.config.REDACTED_SECRET,
                database=self.config.database,
                min_size=self.config.pool_min_size,
                max_size=self.config.pool_max_size,
                max_queries=self.config.pool_max_queries,
                max_inactive_connection_lifetime=self.config.pool_max_inactive_connection_lifetime,
            )

            # Create SQLAlchemy async engine
            self._engine = create_async_engine(
                self._async_url,
                echo=self.config.echo,
                pool_pre_ping=True,
                pool_recycle=300,
            )

            # Create session maker
            self._session_maker = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Run database migrations
            await self._run_migrations()

            logger.info("✅ Multi-tenant PostgreSQL service initialized successfully")

        except Exception as e:
            logger.error(
                f"❌ Failed to initialize multi-tenant PostgreSQL service: {e}",
            )
            raise

    async def close(self) -> None:
        """Close database connections"""
        if self._pool:
            await self._pool.close()
        if self._engine:
            await self._engine.dispose()
        logger.info("Multi-tenant PostgreSQL service closed")

    async def _run_migrations(self) -> None:
        """Run multi-tenant database migrations"""
        try:
            # Create tables if they don't exist
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

                # Create performance indexes
                indexes = MultiTenantIndexes.create_indexes()
                for index in indexes:
                    try:
                        await conn.run_sync(lambda conn: index.create(conn))
                    except Exception as e:
                        logger.warning(f"Index creation warning: {e}")

            logger.info("Multi-tenant database migrations completed successfully")
        except Exception as e:
            logger.error(f"Multi-tenant migration error: {e}")
            raise

    # Tenant Management Methods

    async def create_tenant(
        self,
        name: str,
        display_name: str,
        domain: str | None = None,
        plan: str = "basic",
        settings: dict[str, Any] | None = None,
        limits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new tenant"""
        async with self._session_maker() as session:
            tenant = Tenant(
                name=name,
                display_name=display_name,
                domain=domain,
                plan=plan,
                settings=settings or {},
                limits=limits or {},
            )
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)

            logger.info(f"Created tenant: {name} ({tenant.id})")
            return self._tenant_to_dict(tenant)

    async def get_tenant_by_id(self, tenant_id: str) -> dict[str, Any] | None:
        """Get tenant by ID"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(Tenant).where(Tenant.id == tenant_id),
            )
            tenant = result.scalar_one_or_none()
            return self._tenant_to_dict(tenant) if tenant else None

    async def get_tenant_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Get tenant by domain"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(Tenant).where(Tenant.domain == domain),
            )
            tenant = result.scalar_one_or_none()
            return self._tenant_to_dict(tenant) if tenant else None

    async def get_tenant_by_name(self, name: str) -> dict[str, Any] | None:
        """Get tenant by name"""
        async with self._session_maker() as session:
            result = await session.execute(sa.select(Tenant).where(Tenant.name == name))
            tenant = result.scalar_one_or_none()
            return self._tenant_to_dict(tenant) if tenant else None

    async def update_tenant_status(self, tenant_id: str, status: str) -> bool:
        """Update tenant status"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(status=status, updated_at=datetime.utcnow()),
            )
            await session.commit()
            return result.rowcount > 0

    async def get_all_tenants(
        self,
        status: str | None = None,
        plan: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all tenants with optional filtering"""
        async with self._session_maker() as session:
            query = sa.select(Tenant)

            if status:
                query = query.where(Tenant.status == status)
            if plan:
                query = query.where(Tenant.plan == plan)

            result = await session.execute(query.order_by(Tenant.created_at.desc()))
            tenants = result.scalars().all()
            return [self._tenant_to_dict(tenant) for tenant in tenants]

    # User Management Methods (Tenant-Aware)

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        REDACTED_SECRET_hash: str,
        full_name: str | None = None,
        role: str = "user",
    ) -> dict[str, Any]:
        """Create a new user within a tenant"""
        async with self._session_maker() as session:
            user = User(
                tenant_id=tenant_id,
                username=username,
                email=email,
                REDACTED_SECRET_hash=REDACTED_SECRET_hash,
                full_name=full_name,
                role=role,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(f"Created user: {username} in tenant {tenant_id}")
            return self._user_to_dict(user)

    async def get_user_by_username(
        self,
        tenant_id: str,
        username: str,
    ) -> dict[str, Any] | None:
        """Get user by username within tenant"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(User).where(
                    User.tenant_id == tenant_id,
                    User.username == username,
                ),
            )
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def get_user_by_id(
        self,
        tenant_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Get user by ID within tenant"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(User).where(User.tenant_id == tenant_id, User.id == user_id),
            )
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def get_tenant_users(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all users within a tenant"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(User)
                .where(User.tenant_id == tenant_id)
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset),
            )
            users = result.scalars().all()
            return [self._user_to_dict(user) for user in users]

    # Search History Methods (Tenant-Aware)

    async def save_search_history(
        self,
        tenant_id: str,
        query: str,
        sources: list[str],
        results_count: int,
        execution_time_ms: float,
        user_id: str | None = None,
        cache_hit: bool = False,
        quality_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save search to history within tenant"""
        async with self._session_maker() as session:
            search = SearchHistory(
                tenant_id=tenant_id,
                user_id=user_id,
                query=query,
                sources=sources,
                results_count=results_count,
                execution_time_ms=execution_time_ms,
                cache_hit=cache_hit,
                quality_score=quality_score,
                query_metadata=metadata or {},
            )
            session.add(search)
            await session.commit()
            await session.refresh(search)

            logger.debug(f"Saved search history: {search.id} for tenant {tenant_id}")
            return search.id

    async def get_tenant_search_history(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get search history within tenant"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(SearchHistory)
                .where(SearchHistory.tenant_id == tenant_id)
                .order_by(SearchHistory.created_at.desc())
                .limit(limit)
                .offset(offset),
            )
            searches = result.scalars().all()
            return [self._search_history_to_dict(search) for search in searches]

    async def get_tenant_search_analytics(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get search analytics within tenant"""
        since = datetime.utcnow() - timedelta(days=days)

        async with self._pool.acquire() as conn:
            # Total searches for tenant
            total_searches = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE tenant_id = $1 AND created_at >= $2",
                tenant_id,
                since,
            )

            # Average execution time for tenant
            avg_time = await conn.fetchval(
                "SELECT AVG(execution_time_ms) FROM search_history WHERE tenant_id = $1 AND created_at >= $2",
                tenant_id,
                since,
            )

            # Cache hit rate for tenant
            cache_hits = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE tenant_id = $1 AND created_at >= $2 AND cache_hit = true",
                tenant_id,
                since,
            )
            cache_hit_rate = (
                (cache_hits / total_searches * 100) if total_searches > 0 else 0
            )

            # Top sources for tenant
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

    # Cross-Tenant Analytics (Platform-Level)

    async def get_platform_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get platform-wide analytics across all tenants"""
        if not self.config.cross_tenant_analytics:
            raise ValueError("Cross-tenant analytics is disabled")

        since = datetime.utcnow() - timedelta(days=days)

        async with self._pool.acquire() as conn:
            # Total tenants
            total_tenants = await conn.fetchval("SELECT COUNT(*) FROM tenants")
            active_tenants = await conn.fetchval(
                "SELECT COUNT(*) FROM tenants WHERE status = 'active'",
            )

            # Total searches across all tenants
            total_searches = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE created_at >= $1",
                since,
            )

            # Average execution time across all tenants
            avg_time = await conn.fetchval(
                "SELECT AVG(execution_time_ms) FROM search_history WHERE created_at >= $1",
                since,
            )

            # Top performing tenants by search volume
            tenant_stats = await conn.fetch(
                """
                SELECT t.name, t.display_name, COUNT(sh.id) as search_count,
                       AVG(sh.execution_time_ms) as avg_execution_time,
                       AVG(sh.quality_score) as avg_quality_score
                FROM tenants t
                LEFT JOIN search_history sh ON t.id = sh.tenant_id AND sh.created_at >= $1
                GROUP BY t.id, t.name, t.display_name
                ORDER BY search_count DESC
                LIMIT 10
            """,
                since,
            )

            return {
                "period_days": days,
                "total_tenants": total_tenants,
                "active_tenants": active_tenants,
                "total_searches": total_searches,
                "average_execution_time_ms": float(avg_time) if avg_time else 0,
                "top_tenants_by_usage": [dict(row) for row in tenant_stats],
            }

    # Activity Logging Methods

    async def log_tenant_activity(
        self,
        tenant_id: str,
        activity_type: str,
        user_id: str | None = None,
        activity_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        """Log tenant activity for audit trail"""
        async with self._session_maker() as session:
            activity = TenantActivity(
                tenant_id=tenant_id,
                user_id=user_id,
                activity_type=activity_type,
                activity_data=activity_data,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(activity)
            await session.commit()
            await session.refresh(activity)

            logger.debug(f"Logged activity: {activity_type} for tenant {tenant_id}")
            return activity.id

    async def get_tenant_activity(
        self,
        tenant_id: str,
        activity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get tenant activity log"""
        async with self._session_maker() as session:
            query = sa.select(TenantActivity).where(
                TenantActivity.tenant_id == tenant_id,
            )

            if activity_type:
                query = query.where(TenantActivity.activity_type == activity_type)

            result = await session.execute(
                query.order_by(TenantActivity.created_at.desc())
                .limit(limit)
                .offset(offset),
            )
            activities = result.scalars().all()
            return [self._tenant_activity_to_dict(activity) for activity in activities]

    # Health Check

    async def health_check(self) -> dict[str, Any]:
        """Multi-tenant database health check"""
        try:
            async with self._pool.acquire() as conn:
                # Test basic connectivity
                version = await conn.fetchval("SELECT version()")

                # Check table counts
                tenant_count = await conn.fetchval("SELECT COUNT(*) FROM tenants")
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                search_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM search_history",
                )

                # Check tenant distribution
                tenant_status = await conn.fetch(
                    """
                    SELECT status, COUNT(*) as count
                    FROM tenants
                    GROUP BY status
                """,
                )

                return {
                    "status": "healthy",
                    "postgresql_version": version,
                    "pool_size": self._pool.get_size(),
                    "pool_idle": self._pool.get_idle_size(),
                    "tables": {
                        "tenants": tenant_count,
                        "users": user_count,
                        "search_history": search_count,
                    },
                    "tenant_distribution": [dict(row) for row in tenant_status],
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # Helper Methods

    def _tenant_to_dict(self, tenant: Tenant) -> dict[str, Any]:
        """Convert Tenant model to dictionary"""
        return {
            "id": tenant.id,
            "name": tenant.name,
            "display_name": tenant.display_name,
            "domain": tenant.domain,
            "status": tenant.status,
            "plan": tenant.plan,
            "settings": tenant.settings,
            "limits": tenant.limits,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
            "expires_at": tenant.expires_at.isoformat() if tenant.expires_at else None,
        }

    def _user_to_dict(self, user: User) -> dict[str, Any]:
        """Convert User model to dictionary"""
        return {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "role": user.role,
            "preferences": user.preferences,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

    def _search_history_to_dict(self, search: SearchHistory) -> dict[str, Any]:
        """Convert SearchHistory model to dictionary"""
        return {
            "id": search.id,
            "tenant_id": search.tenant_id,
            "user_id": search.user_id,
            "query": search.query,
            "sources": search.sources,
            "results_count": search.results_count,
            "execution_time_ms": search.execution_time_ms,
            "cache_hit": search.cache_hit,
            "quality_score": search.quality_score,
            "metadata": search.query_metadata,
            "created_at": search.created_at.isoformat(),
        }

    def _tenant_activity_to_dict(self, activity: TenantActivity) -> dict[str, Any]:
        """Convert TenantActivity model to dictionary"""
        return {
            "id": activity.id,
            "tenant_id": activity.tenant_id,
            "user_id": activity.user_id,
            "activity_type": activity.activity_type,
            "activity_data": activity.activity_data,
            "ip_address": activity.ip_address,
            "user_agent": activity.user_agent,
            "created_at": activity.created_at.isoformat(),
        }


# Factory Functions


async def create_multi_tenant_database_service(
    config: MultiTenantDatabaseConfig | None = None,
) -> MultiTenantPostgreSQLService:
    """Create and initialize multi-tenant database service"""
    if config is None:
        config = MultiTenantDatabaseConfig()

    service = MultiTenantPostgreSQLService(config)
    await service.initialize()
    return service


@asynccontextmanager
async def get_multi_tenant_database_service(
    config: MultiTenantDatabaseConfig | None = None,
):
    """Context manager for multi-tenant database service"""
    service = await create_multi_tenant_database_service(config)
    try:
        yield service
    finally:
        await service.close()


# Singleton instance
_multi_tenant_db_service: MultiTenantPostgreSQLService | None = None


async def get_multi_tenant_database() -> MultiTenantPostgreSQLService:
    """Get global multi-tenant database service instance"""
    global _multi_tenant_db_service
    if _multi_tenant_db_service is None:
        _multi_tenant_db_service = await create_multi_tenant_database_service()
    return _multi_tenant_db_service


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        async with get_multi_tenant_database_service() as db:
            # Health check
            health = await db.health_check()
            print(f"Multi-tenant database health: {health}")

            # Create a test tenant
            tenant = await db.create_tenant(
                name="test-tenant",
                display_name="Test Tenant",
                domain="test.pake.com",
                plan="basic",
            )
            print(f"Created tenant: {tenant['name']}")

            # Create a test user
            user = await db.create_user(
                tenant_id=tenant["id"],
                username="testuser",
                email="test@test.pake.com",
                REDACTED_SECRET_hash="hashed_REDACTED_SECRET_here",
                full_name="Test User",
            )
            print(f"Created user: {user['username']}")

            # Save a search
            search_id = await db.save_search_history(
                tenant_id=tenant["id"],
                query="machine learning",
                sources=["web", "arxiv"],
                results_count=15,
                execution_time_ms=250.5,
                user_id=user["id"],
            )
            print(f"Saved search: {search_id}")

            # Get tenant analytics
            analytics = await db.get_tenant_search_analytics(tenant["id"], days=1)
            print(f"Tenant analytics: {analytics}")

            # Get platform analytics
            platform_analytics = await db.get_platform_analytics(days=1)
            print(f"Platform analytics: {platform_analytics}")

    asyncio.run(main())
