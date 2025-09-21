#!/usr/bin/env python3
"""PAKE System - Phase 4 Cached Ingestion Orchestrator
Enhanced orchestrator with Redis caching integration for enterprise-grade performance.
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from scripts.ingestion_pipeline import ContentItem

from ..caching.redis_cache_service import CacheKey, RedisCacheService

# Import base orchestrator and services
from .orchestrator import (
    IngestionConfig,
    IngestionOrchestrator,
    IngestionPlan,
    IngestionResult,
    SourceType,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CachedIngestionConfig(IngestionConfig):
    """Extended configuration with caching parameters"""

    redis_url: str = "redis://localhost:6379/0"
    enable_redis_cache: bool = True
    cache_search_results: bool = True
    search_cache_ttl: int = 3600  # 1 hour
    plan_cache_ttl: int = 1800  # 30 minutes
    warm_cache_enabled: bool = True
    cache_compression: bool = True


class CachedIngestionOrchestrator(IngestionOrchestrator):
    """Enterprise-grade cached orchestrator with Redis integration.

    Features:
    - Multi-level caching (Redis + in-memory)
    - Intelligent cache warming
    - Tag-based cache invalidation
    - Performance metrics and monitoring
    - Async cache operations
    """

    def __init__(self, config: CachedIngestionConfig, **kwargs):
        # Initialize base orchestrator
        super().__init__(config, **kwargs)

        self.cache_config = config
        self.cache_service: RedisCacheService | None = None

        # Cache performance metrics
        self.cache_metrics = {
            "search_cache_hits": 0,
            "search_cache_misses": 0,
            "plan_cache_hits": 0,
            "plan_cache_misses": 0,
            "cache_time_saved_ms": 0,
        }

        logger.info(
            "CachedIngestionOrchestrator initialized with Redis caching support",
        )

    async def initialize_cache(self) -> None:
        """Initialize Redis cache service"""
        if self.cache_config.enable_redis_cache:
            try:
                self.cache_service = RedisCacheService(
                    redis_url=self.cache_config.redis_url,
                    default_ttl=self.cache_config.search_cache_ttl,
                )
                await self.cache_service.initialize()
                logger.info("✅ Redis cache service initialized successfully")

                # Warm cache if enabled
                if self.cache_config.warm_cache_enabled:
                    await self._warm_cache()

            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to initialize Redis cache, using memory-only: {e}",
                )
                self.cache_service = None

    async def close(self) -> None:
        """Clean up cache service"""
        if self.cache_service:
            await self.cache_service.close()

    async def create_ingestion_plan(
        self,
        topic: str,
        context: dict[str, Any] | None = None,
    ) -> IngestionPlan:
        """Create ingestion plan with caching support"""
        # Generate cache key for plan
        context = context or {}
        cache_key_data = f"{topic}:{str(sorted(context.items()))}"
        plan_cache_key = CacheKey(
            "ingestion_plan",
            hashlib.sha256(cache_key_data.encode()).hexdigest(),
        )

        # Try to get plan from cache
        if self.cache_service:
            start_time = datetime.now()
            cached_plan = await self.cache_service.get(plan_cache_key)

            if cached_plan:
                cache_time = (datetime.now() - start_time).total_seconds() * 1000
                self.cache_metrics["plan_cache_hits"] += 1
                self.cache_metrics["cache_time_saved_ms"] += cache_time

                logger.info(
                    f"🚀 Plan cache hit for topic: {topic} (saved {cache_time:.1f}ms)",
                )
                return cached_plan

            self.cache_metrics["plan_cache_misses"] += 1

        # Generate new plan
        plan = await super().create_ingestion_plan(topic, context)

        # Cache the plan
        if self.cache_service:
            tags = ["ingestion_plan", f"topic:{topic}"]
            if context.get("domain"):
                tags.append(f"domain:{context['domain']}")

            await self.cache_service.set(
                plan_cache_key,
                plan,
                ttl=self.cache_config.plan_cache_ttl,
                tags=tags,
            )
            logger.debug(f"Cached ingestion plan for topic: {topic}")

        return plan

    async def execute_ingestion_plan(self, plan: IngestionPlan) -> IngestionResult:
        """Execute ingestion plan with intelligent caching"""
        # Check for cached results of the entire plan
        plan_result_key = CacheKey("plan_result", plan.plan_id)

        if self.cache_service:
            cached_result = await self.cache_service.get(plan_result_key)
            if cached_result:
                logger.info(f"🚀 Full plan result cache hit: {plan.plan_id}")
                return cached_result

        # Execute plan with source-level caching
        start_time = time.time()
        content_items = []
        sources_completed = 0
        sources_failed = 0

        logger.info(f"Executing ingestion plan {plan.plan_id} for topic: {plan.topic}")

        # Execute sources concurrently with individual caching
        source_tasks = []
        for source in plan.sources:
            task = asyncio.create_task(self._execute_cached_source(source, plan.topic))
            source_tasks.append(task)

        # Gather results
        source_results = await asyncio.gather(*source_tasks, return_exceptions=True)

        for i, result in enumerate(source_results):
            source = plan.sources[i]

            if isinstance(result, Exception):
                logger.error(f"Source {source.source_type} failed: {result}")
                sources_failed += 1
                continue

            if result:
                content_items.extend(result)
                sources_completed += 1
                logger.info(
                    f"Successfully retrieved {len(result)} items from {source.source_type}",
                )
            else:
                sources_failed += 1

        # Apply intelligent deduplication
        if content_items and self.config.deduplication_enabled:
            logger.info(
                f"Applying intelligent deduplication to {len(content_items)} items",
            )
            content_items = await self.performance_optimizer.deduplicate_content(
                content_items,
            )
            logger.info(
                f"Intelligent deduplication complete: {len(content_items)} unique items",
            )

        # Create result
        execution_time = time.time() - start_time
        result = IngestionResult(
            plan_id=plan.plan_id,
            success=sources_completed > 0,
            content_items=content_items,
            total_content_items=len(content_items),
            sources_attempted=len(plan.sources),
            sources_completed=sources_completed,
            sources_failed=sources_failed,
            execution_time=execution_time,
            error_details=(
                [{"error": f"All {sources_failed} sources failed"}]
                if sources_completed == 0
                else []
            ),
            metrics={
                "execution_time_seconds": execution_time,
                "sources_attempted": len(plan.sources),
                "content_items_retrieved": len(content_items),
                "average_quality_score": (
                    sum(
                        item.metadata.get("quality_score", 0.7)
                        for item in content_items
                    )
                    / len(content_items)
                    if content_items
                    else 0.0
                ),
                **self.cache_metrics,
            },
        )

        # Cache successful results
        if self.cache_service and result.success:
            cache_tags = ["plan_result", f"topic:{plan.topic}"]
            await self.cache_service.set(
                plan_result_key,
                result,
                ttl=self.cache_config.search_cache_ttl,
                tags=cache_tags,
            )

        # Update execution metrics
        self.execution_metrics["plans_executed"] += 1
        self.execution_metrics["total_content_retrieved"] += len(content_items)

        logger.info(
            f"Completed ingestion plan {plan.plan_id}: {len(content_items)} items from {sources_completed}/{len(plan.sources)} sources in {execution_time:.2f}s",
        )

        return result

    async def _execute_cached_source(self, source, topic: str) -> list[ContentItem]:
        """Execute individual source with caching"""
        # Generate source-specific cache key
        query_str = str(source.query_parameters.get("query", topic))
        source_cache_key = CacheKey(
            "source_result",
            f"{source.source_type}:{hashlib.sha256(f'{topic}:{query_str}'.encode()).hexdigest()}",
        )

        # Check cache first
        if self.cache_service:
            start_time = datetime.now()
            cached_items = await self.cache_service.get(source_cache_key)

            if cached_items:
                cache_time = (datetime.now() - start_time).total_seconds() * 1000
                self.cache_metrics["search_cache_hits"] += 1
                self.cache_metrics["cache_time_saved_ms"] += cache_time

                logger.info(
                    f"🚀 Source cache hit: {source.source_type} (saved {cache_time:.1f}ms)",
                )
                return cached_items

            self.cache_metrics["search_cache_misses"] += 1

        # Execute source
        try:
            if source.source_type == SourceType.WEB:
                items = await self._execute_web_source(source)
            elif source.source_type == SourceType.ARXIV:
                items = await self._execute_arxiv_source(source)
            elif source.source_type == SourceType.PUBMED:
                items = await self._execute_pubmed_source(source)
            else:
                logger.warning(f"Unknown source type: {source.source_type}")
                return []

            # Cache successful results
            if self.cache_service and items:
                cache_tags = [
                    "source_result",
                    f"source:{source.source_type}",
                    f"topic:{topic}",
                ]

                await self.cache_service.set(
                    source_cache_key,
                    items,
                    ttl=self.cache_config.search_cache_ttl,
                    tags=cache_tags,
                )
                logger.debug(f"Cached {len(items)} items from {source.source_type}")

            return items

        except Exception as e:
            logger.error(f"Error executing {source.source_type} source: {e}")
            return []

    async def invalidate_topic_cache(self, topic: str) -> int:
        """Invalidate all cache entries for a specific topic"""
        if not self.cache_service:
            return 0

        count = await self.cache_service.invalidate_by_tag(f"topic:{topic}")
        logger.info(f"Invalidated {count} cache entries for topic: {topic}")
        return count

    async def invalidate_source_cache(self, source_type: SourceType) -> int:
        """Invalidate all cache entries for a specific source"""
        if not self.cache_service:
            return 0

        count = await self.cache_service.invalidate_by_tag(f"source:{source_type}")
        logger.info(f"Invalidated {count} cache entries for source: {source_type}")
        return count

    async def get_cache_statistics(self) -> dict[str, Any]:
        """Get comprehensive cache performance statistics"""
        base_stats = {}
        if self.cache_service:
            base_stats = self.cache_service.get_stats()

        return {
            **base_stats,
            **self.cache_metrics,
            "cache_enabled": self.cache_service is not None,
            "redis_url": self.cache_config.redis_url if self.cache_service else None,
        }

    async def _warm_cache(self) -> None:
        """Warm cache with popular/common queries"""
        popular_queries = [
            "machine learning",
            "artificial intelligence",
            "data science",
            "quantum computing",
            "blockchain technology",
            "climate change",
            "renewable energy",
            "biotechnology",
            "cybersecurity",
            "cloud computing",
        ]

        logger.info(f"🔥 Warming cache with {len(popular_queries)} popular queries")

        warming_tasks = []
        for query in popular_queries:
            task = asyncio.create_task(self._warm_query_cache(query))
            warming_tasks.append(task)

        # Execute warming tasks concurrently but don't wait for all
        # This allows the system to start serving requests while warming continues
        asyncio.create_task(self._complete_cache_warming(warming_tasks))

    async def _warm_query_cache(self, query: str) -> None:
        """Warm cache for a specific query"""
        try:
            context = {"domain": "research", "cache_warming": True}
            plan = await self.create_ingestion_plan(query, context)

            # Don't execute the full plan during warming, just cache the plan
            logger.debug(f"Warmed plan cache for query: {query}")

        except Exception as e:
            logger.debug(f"Cache warming failed for query '{query}': {e}")

    async def _complete_cache_warming(self, warming_tasks: list[asyncio.Task]) -> None:
        """Complete cache warming in background"""
        try:
            await asyncio.gather(*warming_tasks, return_exceptions=True)
            logger.info("🔥 Cache warming completed")
        except Exception as e:
            logger.warning(f"Cache warming partially failed: {e}")


# Factory function for easy instantiation


async def create_cached_orchestrator(
    redis_url: str = "redis://localhost:6379/0",
    **config_kwargs,
) -> CachedIngestionOrchestrator:
    """Create and initialize a cached ingestion orchestrator"""
    config = CachedIngestionConfig(redis_url=redis_url, **config_kwargs)

    orchestrator = CachedIngestionOrchestrator(config)
    await orchestrator.initialize_cache()

    return orchestrator


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        # Create cached orchestrator
        orchestrator = await create_cached_orchestrator()

        try:
            # Test plan creation and caching
            plan1 = await orchestrator.create_ingestion_plan("machine learning")
            # Should be cached
            plan2 = await orchestrator.create_ingestion_plan("machine learning")

            # Execute plan
            result = await orchestrator.execute_ingestion_plan(plan1)
            print(f"Retrieved {len(result.content_items)} items")

            # Get cache statistics
            stats = await orchestrator.get_cache_statistics()
            print(f"Cache stats: {stats}")

        finally:
            await orchestrator.close()

    import time

    asyncio.run(main())
