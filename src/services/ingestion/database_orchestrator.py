#!/usr/bin/env python3
"""PAKE System - Phase 5 Database-Aware Cached Orchestrator
Extends the Redis cached orchestrator with PostgreSQL integration for comprehensive data persistence.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..database.postgresql_service import (
    DatabaseConfig,
    PostgreSQLService,
)

# Import base orchestrators
from .cached_orchestrator import (
    CachedIngestionConfig,
    CachedIngestionOrchestrator,
    IngestionPlan,
    IngestionResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseIngestionConfig(CachedIngestionConfig):
    """Extended configuration with database integration"""

    # Database settings
    enable_database: bool = True
    save_search_history: bool = True
    save_system_metrics: bool = True
    database_config: DatabaseConfig | None = None

    # Analytics settings
    track_user_searches: bool = True
    enable_search_analytics: bool = True
    metrics_save_interval: int = 300  # 5 minutes


class DatabaseIngestionOrchestrator(CachedIngestionOrchestrator):
    """Enterprise-grade orchestrator with full persistence stack.

    Features:
    - All Redis caching capabilities from Phase 4
    - PostgreSQL persistence for user data and search history
    - Comprehensive search analytics and metrics
    - User-specific search tracking
    - System performance monitoring
    - Search history and saved searches support
    """

    def __init__(self, config: DatabaseIngestionConfig, **kwargs):
        # Initialize parent cached orchestrator
        super().__init__(config, **kwargs)

        self.database_config = config
        self.database_service: PostgreSQLService | None = None

        # Database metrics tracking
        self.database_metrics = {
            "searches_saved": 0,
            "metrics_saved": 0,
            "database_errors": 0,
            "last_database_save": None,
        }

        logger.info("DatabaseIngestionOrchestrator initialized with PostgreSQL support")

    async def initialize_database(self) -> None:
        """Initialize PostgreSQL database service"""
        if self.database_config.enable_database:
            try:
                # Use provided config or default
                db_config = self.database_config.database_config or DatabaseConfig()

                # Initialize database service
                self.database_service = PostgreSQLService(db_config)
                await self.database_service.initialize()

                logger.info("✅ PostgreSQL database service initialized successfully")

            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to initialize PostgreSQL, continuing without database: {e}",
                )
                self.database_service = None

    async def initialize_cache(self) -> None:
        """Initialize both cache and database"""
        # Initialize Redis cache from parent
        await super().initialize_cache()

        # Initialize PostgreSQL database
        await self.initialize_database()

    async def close(self) -> None:
        """Clean up both cache and database services"""
        # Close parent cache service
        await super().close()

        # Close database service
        if self.database_service:
            await self.database_service.close()

    async def execute_ingestion_plan(
        self,
        plan: IngestionPlan,
        user_id: str | None = None,
    ) -> IngestionResult:
        """Execute ingestion plan with full persistence tracking"""
        start_time = time.time()

        # Execute plan using parent cached orchestrator
        result = await super().execute_ingestion_plan(plan)

        # Save search history to database if enabled
        if (
            self.database_service
            and self.database_config.save_search_history
            and result.success
        ):
            try:
                await self._save_search_history(
                    plan=plan,
                    result=result,
                    user_id=user_id,
                )
                self.database_metrics["searches_saved"] += 1
                self.database_metrics["last_database_save"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"Failed to save search history: {e}")
                self.database_metrics["database_errors"] += 1

        # Save system metrics if enabled
        if self.database_service and self.database_config.save_system_metrics:
            try:
                await self._save_performance_metrics(result)
                self.database_metrics["metrics_saved"] += 1

            except Exception as e:
                logger.error(f"Failed to save system metrics: {e}")
                self.database_metrics["database_errors"] += 1

        return result

    async def _save_search_history(
        self,
        plan: IngestionPlan,
        result: IngestionResult,
        user_id: str | None = None,
    ) -> None:
        """Save search execution to history"""
        if not self.database_service:
            return

        # Extract cache hit information from metrics
        cache_hit = (
            result.metrics.get("plan_cache_hits", 0) > 0
            or result.metrics.get("search_cache_hits", 0) > 0
        )

        # Calculate average quality score
        avg_quality = result.metrics.get("average_quality_score", 0.0)

        # Prepare metadata
        metadata = {
            "plan_id": plan.plan_id,
            "sources_attempted": result.sources_attempted,
            "sources_completed": result.sources_completed,
            "sources_failed": result.sources_failed,
            "cache_metrics": {
                "plan_cache_hits": result.metrics.get("plan_cache_hits", 0),
                "search_cache_hits": result.metrics.get("search_cache_hits", 0),
                "cache_time_saved_ms": result.metrics.get("cache_time_saved_ms", 0),
            },
        }

        # Extract source types from plan
        source_types = [source.source_type for source in plan.sources]

        await self.database_service.save_search_history(
            query=plan.topic,
            sources=source_types,
            results_count=len(result.content_items),
            execution_time_ms=result.execution_time * 1000,  # Convert to milliseconds
            user_id=user_id,
            cache_hit=cache_hit,
            quality_score=avg_quality,
            metadata=metadata,
        )

        logger.debug(f"Saved search history for query: {plan.topic}")

    async def _save_performance_metrics(self, result: IngestionResult) -> None:
        """Save system performance metrics"""
        if not self.database_service:
            return

        # Combine cache metrics with execution metrics
        performance_data = {
            "execution_time_ms": result.execution_time * 1000,
            "sources_attempted": result.sources_attempted,
            "sources_completed": result.sources_completed,
            "sources_failed": result.sources_failed,
            "content_items_retrieved": len(result.content_items),
            "average_quality_score": result.metrics.get("average_quality_score", 0.0),
            **self.cache_metrics,  # Include cache performance metrics
            **self.database_metrics,  # Include database metrics
        }

        await self.database_service.save_system_metrics(
            metric_type="search_performance",
            metric_data=performance_data,
        )

        logger.debug("Saved system performance metrics")

    # User-specific search methods

    async def save_user_search(
        self,
        user_id: str,
        name: str,
        query: str,
        sources: list[str],
        filters: dict[str, Any] | None = None,
        is_public: bool = False,
        tags: list[str] | None = None,
    ) -> str | None:
        """Save a user's search query for later use"""
        if not self.database_service:
            logger.warning("Database service not available for saving search")
            return None

        try:
            search_id = await self.database_service.save_search(
                user_id=user_id,
                name=name,
                query=query,
                sources=sources,
                filters=filters,
                is_public=is_public,
                tags=tags,
            )

            logger.info(f"Saved user search: {name} for user {user_id}")
            return search_id

        except Exception as e:
            logger.error(f"Failed to save user search: {e}")
            return None

    async def get_user_search_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get user's search history"""
        if not self.database_service:
            return []

        try:
            return await self.database_service.get_user_search_history(
                user_id=user_id,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(f"Failed to get user search history: {e}")
            return []

    async def get_user_saved_searches(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's saved searches"""
        if not self.database_service:
            return []

        try:
            return await self.database_service.get_user_saved_searches(user_id)
        except Exception as e:
            logger.error(f"Failed to get user saved searches: {e}")
            return []

    # Analytics methods

    async def get_search_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get comprehensive search analytics"""
        if not self.database_service:
            return {"error": "Database service not available"}

        try:
            analytics = await self.database_service.get_search_analytics(days)

            # Add cache statistics from Redis
            if hasattr(self, "get_cache_statistics"):
                cache_stats = await self.get_cache_statistics()
                analytics["current_cache_stats"] = cache_stats

            return analytics

        except Exception as e:
            logger.error(f"Failed to get search analytics: {e}")
            return {"error": str(e)}

    async def get_popular_searches(
        self,
        limit: int = 10,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get most popular search queries"""
        if not self.database_service:
            return []

        try:
            return await self.database_service.get_popular_searches(limit, days)
        except Exception as e:
            logger.error(f"Failed to get popular searches: {e}")
            return []

    async def get_comprehensive_statistics(self) -> dict[str, Any]:
        """Get comprehensive system statistics combining cache and database"""
        stats = {}

        # Get execution metrics from parent
        execution_metrics = await self.get_execution_metrics()
        stats["execution"] = execution_metrics

        # Get cache statistics if available
        if hasattr(self, "get_cache_statistics"):
            cache_stats = await self.get_cache_statistics()
            stats["cache"] = cache_stats

        # Get database metrics
        stats["database"] = self.database_metrics.copy()

        # Get database health if available
        if self.database_service:
            try:
                db_health = await self.database_service.health_check()
                stats["database"]["health"] = db_health
            except Exception as e:
                stats["database"]["health"] = {"status": "error", "error": str(e)}

        # Get recent analytics if available
        if self.database_service:
            try:
                analytics = await self.get_search_analytics(days=1)  # Last 24 hours
                stats["recent_analytics"] = analytics
            except Exception as e:
                stats["recent_analytics"] = {"error": str(e)}

        return stats


# Factory function for easy instantiation


async def create_database_orchestrator(
    database_config: DatabaseConfig | None = None,
    **config_kwargs,
) -> DatabaseIngestionOrchestrator:
    """Create and initialize a database-aware orchestrator"""
    # Prepare configuration
    config_dict = {
        "enable_database": True,
        "save_search_history": True,
        "save_system_metrics": True,
        "database_config": database_config,
        **config_kwargs,
    }

    config = DatabaseIngestionConfig(**config_dict)
    orchestrator = DatabaseIngestionOrchestrator(config)

    # Initialize both cache and database
    await orchestrator.initialize_cache()

    return orchestrator


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        # Create database-aware orchestrator
        orchestrator = await create_database_orchestrator()

        try:
            # Test plan creation (will be cached)
            plan = await orchestrator.create_ingestion_plan("artificial intelligence")
            print(f"Created plan with {len(plan.sources)} sources")

            # Execute plan (will be saved to database)
            result = await orchestrator.execute_ingestion_plan(
                plan,
                user_id="test-user-123",
            )
            print(f"Retrieved {len(result.content_items)} items")

            # Get comprehensive statistics
            stats = await orchestrator.get_comprehensive_statistics()
            print(f"System stats: {stats}")

            # Get analytics
            analytics = await orchestrator.get_search_analytics(days=1)
            print(f"Analytics: {analytics}")

        finally:
            await orchestrator.close()

    asyncio.run(main())
