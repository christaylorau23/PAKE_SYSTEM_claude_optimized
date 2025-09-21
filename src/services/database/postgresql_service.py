#!/usr/bin/env python3
"""PAKE System - Phase 5 PostgreSQL Database Service
Enterprise-grade database service for persistent data storage and user management.
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
from sqlalchemy import JSON, UUID, Boolean, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

logger = logging.getLogger(__name__)

# SQLAlchemy Models
Base = declarative_base()


class User(Base):
    """User account model"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    REDACTED_SECRET_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime)


class SearchHistory(Base):
    """Search history tracking model"""

    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
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


class SavedSearch(Base):
    """Saved search queries model"""

    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
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


class SystemMetrics(Base):
    """System performance metrics model"""

    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    # 'search_performance', 'cache_stats', etc.
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


@dataclass
class DatabaseConfig:
    """Database configuration"""

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


class PostgreSQLService:
    """Enterprise PostgreSQL database service with async support.

    Features:
    - Connection pooling for high performance
    - Automatic migrations with Alembic
    - User management and authentication data
    - Search history and analytics
    - Saved searches functionality
    - System metrics storage
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Pool | None = None
        self._engine = None
        self._session_maker = None

        # Build connection strings
        self._async_url = f"postgresql+asyncpg://{config.username}:{config.REDACTED_SECRET}@{
            config.host
        }:{config.port}/{config.database}"
        self._sync_url = f"postgresql://{config.username}:{config.REDACTED_SECRET}@{
            config.host
        }:{config.port}/{config.database}"

        logger.info("PostgreSQL service initialized")

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

            logger.info("✅ PostgreSQL service initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL service: {e}")
            raise

    async def close(self) -> None:
        """Close database connections"""
        if self._pool:
            await self._pool.close()
        if self._engine:
            await self._engine.dispose()
        logger.info("PostgreSQL service closed")

    async def _run_migrations(self) -> None:
        """Run Alembic migrations"""
        try:
            # Create tables if they don't exist
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database migrations completed successfully")
        except Exception as e:
            logger.error(f"Migration error: {e}")
            raise

    # User Management Methods

    async def create_user(
        self,
        username: str,
        email: str,
        REDACTED_SECRET_hash: str,
        full_name: str | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        """Create a new user"""
        async with self._session_maker() as session:
            user = User(
                username=username,
                email=email,
                REDACTED_SECRET_hash=REDACTED_SECRET_hash,
                full_name=full_name,
                is_admin=is_admin,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(f"Created user: {username}")
            return self._user_to_dict(user)

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user by username"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(User).where(User.username == username),
            )
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID"""
        async with self._session_maker() as session:
            result = await session.execute(sa.select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def update_user_login(self, user_id: str) -> None:
        """Update user last login timestamp"""
        async with self._session_maker() as session:
            await session.execute(
                sa.update(User)
                .where(User.id == user_id)
                .values(last_login=datetime.utcnow()),
            )
            await session.commit()

    # Search History Methods

    async def save_search_history(
        self,
        query: str,
        sources: list[str],
        results_count: int,
        execution_time_ms: float,
        user_id: str | None = None,
        cache_hit: bool = False,
        quality_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save search to history"""
        async with self._session_maker() as session:
            search = SearchHistory(
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

            logger.debug(f"Saved search history: {search.id}")
            return search.id

    async def get_user_search_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get user's search history"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(SearchHistory)
                .where(SearchHistory.user_id == user_id)
                .order_by(SearchHistory.created_at.desc())
                .limit(limit)
                .offset(offset),
            )
            searches = result.scalars().all()
            return [self._search_history_to_dict(search) for search in searches]

    async def get_popular_searches(
        self,
        limit: int = 10,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get most popular search queries"""
        since = datetime.utcnow() - timedelta(days=days)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT query, COUNT(*) as search_count,
                       AVG(execution_time_ms) as avg_time,
                       AVG(results_count) as avg_results
                FROM search_history
                WHERE created_at >= $1
                GROUP BY query
                ORDER BY search_count DESC
                LIMIT $2
            """,
                since,
                limit,
            )

            return [dict(row) for row in rows]

    # Saved Searches Methods

    async def save_search(
        self,
        user_id: str,
        name: str,
        query: str,
        sources: list[str],
        filters: dict[str, Any] | None = None,
        is_public: bool = False,
        tags: list[str] | None = None,
    ) -> str:
        """Save a search query"""
        async with self._session_maker() as session:
            saved_search = SavedSearch(
                user_id=user_id,
                name=name,
                query=query,
                sources=sources,
                filters=filters,
                is_public=is_public,
                tags=tags or [],
            )
            session.add(saved_search)
            await session.commit()
            await session.refresh(saved_search)

            logger.info(f"Saved search: {name} for user {user_id}")
            return saved_search.id

    async def get_user_saved_searches(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's saved searches"""
        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(SavedSearch)
                .where(SavedSearch.user_id == user_id)
                .order_by(SavedSearch.updated_at.desc()),
            )
            searches = result.scalars().all()
            return [self._saved_search_to_dict(search) for search in searches]

    # System Metrics Methods

    async def save_system_metrics(
        self,
        metric_type: str,
        metric_data: dict[str, Any],
    ) -> None:
        """Save system performance metrics"""
        async with self._session_maker() as session:
            metrics = SystemMetrics(metric_type=metric_type, metric_data=metric_data)
            session.add(metrics)
            await session.commit()

    async def get_system_metrics(
        self,
        metric_type: str,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Get system metrics for analysis"""
        since = datetime.utcnow() - timedelta(hours=hours)

        async with self._session_maker() as session:
            result = await session.execute(
                sa.select(SystemMetrics)
                .where(SystemMetrics.metric_type == metric_type)
                .where(SystemMetrics.timestamp >= since)
                .order_by(SystemMetrics.timestamp.desc()),
            )
            metrics = result.scalars().all()
            return [self._system_metrics_to_dict(metric) for metric in metrics]

    # Analytics Methods

    async def get_search_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get comprehensive search analytics"""
        since = datetime.utcnow() - timedelta(days=days)

        async with self._pool.acquire() as conn:
            # Total searches
            total_searches = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE created_at >= $1",
                since,
            )

            # Average execution time
            avg_time = await conn.fetchval(
                "SELECT AVG(execution_time_ms) FROM search_history WHERE created_at >= $1",
                since,
            )

            # Cache hit rate
            cache_hits = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE created_at >= $1 AND cache_hit = true",
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
                WHERE created_at >= $1
                GROUP BY source
                ORDER BY usage_count DESC
                LIMIT 5
            """,
                since,
            )

            return {
                "period_days": days,
                "total_searches": total_searches,
                "average_execution_time_ms": float(avg_time) if avg_time else 0,
                "cache_hit_rate_percent": round(cache_hit_rate, 2),
                "top_sources": [dict(row) for row in source_stats],
            }

    # User Authentication Methods

    async def create_user(
        self,
        username: str,
        email: str,
        REDACTED_SECRET_hash: str,
        full_name: str | None = None,
    ) -> str | None:
        """Create new user account"""
        try:
            async with self._pool.acquire() as conn:
                user_id = await conn.fetchval(
                    """
                    INSERT INTO users (username, email, REDACTED_SECRET_hash, full_name)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """,
                    username,
                    email,
                    REDACTED_SECRET_hash,
                    full_name,
                )
                return user_id
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user by username"""
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, username, email, REDACTED_SECRET_hash, full_name,
                           is_active, is_admin, preferences, created_at, updated_at, last_login
                    FROM users WHERE username = $1
                """,
                    username,
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user by username: {e}")
            return None

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email"""
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, username, email, REDACTED_SECRET_hash, full_name,
                           is_active, is_admin, preferences, created_at, updated_at, last_login
                    FROM users WHERE email = $1
                """,
                    email,
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID"""
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, username, email, REDACTED_SECRET_hash, full_name,
                           is_active, is_admin, preferences, created_at, updated_at, last_login
                    FROM users WHERE id = $1
                """,
                    user_id,
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None

    async def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE users
                    SET last_login = NOW(), updated_at = NOW()
                    WHERE id = $1
                """,
                    user_id,
                )
                return result != "UPDATE 0"
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False

    async def update_user_REDACTED_SECRET(self, user_id: str, REDACTED_SECRET_hash: str) -> bool:
        """Update user REDACTED_SECRET"""
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE users
                    SET REDACTED_SECRET_hash = $2, updated_at = NOW()
                    WHERE id = $1
                """,
                    user_id,
                    REDACTED_SECRET_hash,
                )
                return result != "UPDATE 0"
        except Exception as e:
            logger.error(f"Failed to update REDACTED_SECRET: {e}")
            return False

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE users
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE id = $1
                """,
                    user_id,
                )
                return result != "UPDATE 0"
        except Exception as e:
            logger.error(f"Failed to deactivate user: {e}")
            return False

    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE users
                    SET is_active = TRUE, updated_at = NOW()
                    WHERE id = $1
                """,
                    user_id,
                )
                return result != "UPDATE 0"
        except Exception as e:
            logger.error(f"Failed to activate user: {e}")
            return False

    # Health Check

    async def health_check(self) -> dict[str, Any]:
        """Database health check"""
        try:
            async with self._pool.acquire() as conn:
                # Test basic connectivity
                version = await conn.fetchval("SELECT version()")

                # Check table counts
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                search_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM search_history",
                )
                saved_count = await conn.fetchval("SELECT COUNT(*) FROM saved_searches")

                return {
                    "status": "healthy",
                    "postgresql_version": version,
                    "pool_size": self._pool.get_size(),
                    "pool_idle": self._pool.get_idle_size(),
                    "tables": {
                        "users": user_count,
                        "search_history": search_count,
                        "saved_searches": saved_count,
                    },
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # Helper Methods

    def _user_to_dict(self, user: User) -> dict[str, Any]:
        """Convert User model to dictionary"""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "preferences": user.preferences,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

    def _search_history_to_dict(self, search: SearchHistory) -> dict[str, Any]:
        """Convert SearchHistory model to dictionary"""
        return {
            "id": search.id,
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

    def _saved_search_to_dict(self, search: SavedSearch) -> dict[str, Any]:
        """Convert SavedSearch model to dictionary"""
        return {
            "id": search.id,
            "user_id": search.user_id,
            "name": search.name,
            "query": search.query,
            "sources": search.sources,
            "filters": search.filters,
            "is_public": search.is_public,
            "tags": search.tags,
            "created_at": search.created_at.isoformat(),
            "updated_at": search.updated_at.isoformat(),
        }

    def _system_metrics_to_dict(self, metrics: SystemMetrics) -> dict[str, Any]:
        """Convert SystemMetrics model to dictionary"""
        return {
            "id": metrics.id,
            "metric_type": metrics.metric_type,
            "metric_data": metrics.metric_data,
            "timestamp": metrics.timestamp.isoformat(),
        }


# Factory Functions


async def create_database_service(
    config: DatabaseConfig | None = None,
) -> PostgreSQLService:
    """Create and initialize database service"""
    if config is None:
        config = DatabaseConfig()

    service = PostgreSQLService(config)
    await service.initialize()
    return service


@asynccontextmanager
async def get_database_service(config: DatabaseConfig | None = None):
    """Context manager for database service"""
    service = await create_database_service(config)
    try:
        yield service
    finally:
        await service.close()


# Singleton instance
_db_service: PostgreSQLService | None = None


async def get_database() -> PostgreSQLService:
    """Get global database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = await create_database_service()
    return _db_service


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        async with get_database_service() as db:
            # Health check
            health = await db.health_check()
            print(f"Database health: {health}")

            # Create a test user
            user = await db.create_user(
                username="testuser",
                email="test@example.com",
                REDACTED_SECRET_hash="hashed_REDACTED_SECRET_here",
                full_name="Test User",
            )
            print(f"Created user: {user['username']}")

            # Save a search
            search_id = await db.save_search_history(
                query="machine learning",
                sources=["web", "arxiv"],
                results_count=15,
                execution_time_ms=250.5,
                user_id=user["id"],
            )
            print(f"Saved search: {search_id}")

            # Get analytics
            analytics = await db.get_search_analytics(days=1)
            print(f"Analytics: {analytics}")

    asyncio.run(main())
