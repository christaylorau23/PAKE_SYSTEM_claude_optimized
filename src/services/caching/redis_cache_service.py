#!/usr/bin/env python3
"""Redis Cache Service - Enterprise-Grade Caching Layer
Provides multi-level caching for search results, API responses, and user data.
"""

import asyncio
import logging

# import pickle  # SECURITY: Replaced with secure serialization
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from ...utils.secure_serialization import deserialize, serialize

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for Redis cache service"""

    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 3600
    max_memory_cache_size: int = 1000
    enable_compression: bool = True


@dataclass
class CacheKey:
    """Structured cache key generator"""

    namespace: str
    identifier: str
    version: str = "v1"

    def __str__(self) -> str:
        return f"pake:{self.namespace}:{self.version}:{self.identifier}"


@dataclass
class CacheMetadata:
    """Cache entry metadata"""

    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime | None = None
    tags: list[str] | None = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class CacheEntry:
    """Wrapper for cached data with metadata"""

    def __init__(self, data: Any, metadata: CacheMetadata):
        self.data = data
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        return {"data": self.data, "metadata": asdict(self.metadata)}

    @classmethod
    def from_dict(cls, cache_dict: dict[str, Any]) -> "CacheEntry":
        metadata_dict = cache_dict["metadata"]
        metadata = CacheMetadata(
            created_at=datetime.fromisoformat(metadata_dict["created_at"]),
            expires_at=datetime.fromisoformat(metadata_dict["expires_at"]),
            access_count=metadata_dict["access_count"],
            last_accessed=(
                datetime.fromisoformat(metadata_dict["last_accessed"])
                if metadata_dict["last_accessed"]
                else None
            ),
            tags=metadata_dict["tags"],
        )
        return cls(cache_dict["data"], metadata)

    def is_expired(self) -> bool:
        return datetime.now() > self.metadata.expires_at

    def access(self):
        """Mark entry as accessed"""
        self.metadata.access_count += 1
        self.metadata.last_accessed = datetime.now()


class RedisCacheService:
    """Enterprise-grade Redis caching service with advanced features:
    - Multi-level caching (L1: in-memory, L2: Redis)
    - Intelligent cache warming
    - Tag-based invalidation
    - Performance metrics
    - Automatic cleanup
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
        max_memory_cache_size: int = 1000,
    ):
        if config:
            self.redis_url = config.redis_url
            self.default_ttl = config.default_ttl
            self.max_memory_cache_size = config.max_memory_cache_size
        else:
            self.redis_url = redis_url
            self.default_ttl = default_ttl
            self.max_memory_cache_size = max_memory_cache_size

        # L1 Cache (in-memory)
        self._memory_cache: dict[str, CacheEntry] = {}
        self._memory_access_order: list[str] = []

        # Redis connection
        self._redis: Redis | None = None

        # Performance metrics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "l1_hits": 0,
            "l2_hits": 0,
        }

        # Background tasks
        self._cleanup_task: asyncio.Task | None = None
        self._metrics_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize Redis connection and background tasks"""
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=False)
            await self._redis.ping()
            logger.info(f"✅ Redis cache service connected: {self.redis_url}")

            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
            self._metrics_task = asyncio.create_task(self._report_metrics())

        except Exception as e:
            logger.warning(f"⚠️ Redis not available, using memory-only cache: {e}")
            self._redis = None

    async def close(self) -> None:
        """Close connections and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()

        if self._redis:
            await self._redis.close()

    async def get(
        self,
        key: str | CacheKey,
        default: Any = None,
        update_access: bool = True,
    ) -> Any:
        """Get value from cache (L1 -> L2 hierarchy)"""
        cache_key = str(key)

        # L1 Cache check
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if not entry.is_expired():
                if update_access:
                    entry.access()
                    self._update_access_order(cache_key)
                self.stats["hits"] += 1
                self.stats["l1_hits"] += 1
                logger.debug(f"L1 cache hit: {cache_key}")
                return entry.data
            # Remove expired entry
            self._remove_from_memory_cache(cache_key)

        # L2 Cache check (Redis)
        if self._redis:
            try:
                cached_data = await self._redis.get(cache_key)
                if cached_data:
                    entry_dict = deserialize(cached_data)
                    entry = CacheEntry.from_dict(entry_dict)

                    if not entry.is_expired():
                        if update_access:
                            entry.access()

                        # Promote to L1 cache
                        self._add_to_memory_cache(cache_key, entry)

                        # Update Redis with access info
                        if update_access:
                            await self._redis.set(
                                cache_key,
                                serialize(entry.to_dict()),
                                ex=int(
                                    (
                                        entry.metadata.expires_at - datetime.now()
                                    ).total_seconds(),
                                ),
                            )

                        self.stats["hits"] += 1
                        self.stats["l2_hits"] += 1
                        logger.debug(f"L2 cache hit: {cache_key}")
                        return entry.data
                    # Remove expired entry
                    await self._redis.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis get error for {cache_key}: {e}")

        # Cache miss
        self.stats["misses"] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return default

    async def set(
        self,
        key: str | CacheKey,
        value: Any,
        ttl: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set value in cache (both L1 and L2)"""
        cache_key = str(key)
        ttl = ttl or self.default_ttl
        tags = tags or []

        # Create cache entry
        metadata = CacheMetadata(
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl),
            tags=tags,
        )
        entry = CacheEntry(value, metadata)

        # Set in L1 cache
        self._add_to_memory_cache(cache_key, entry)

        # Set in L2 cache (Redis)
        if self._redis:
            try:
                await self._redis.set(cache_key, serialize(entry.to_dict()), ex=ttl)

                # Add to tag sets for tag-based invalidation
                for tag in tags:
                    await self._redis.sadd(f"tag:{tag}", cache_key)
                    # Tag expires later
                    await self._redis.expire(f"tag:{tag}", ttl + 3600)

            except Exception as e:
                logger.warning(f"Redis set error for {cache_key}: {e}")

        self.stats["sets"] += 1
        logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s, Tags: {tags})")

    async def delete(self, key: str | CacheKey) -> None:
        """Delete from both cache levels"""
        cache_key = str(key)

        # Remove from L1
        self._remove_from_memory_cache(cache_key)

        # Remove from L2
        if self._redis:
            try:
                await self._redis.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis delete error for {cache_key}: {e}")

        self.stats["deletes"] += 1

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with given tag"""
        if not self._redis:
            return 0

        try:
            # Get all keys with this tag
            keys = await self._redis.smembers(f"tag:{tag}")
            if not keys:
                return 0

            # Delete all keys
            count = 0
            for key in keys:
                await self.delete(key.decode() if isinstance(key, bytes) else key)
                count += 1

            # Clean up tag set
            await self._redis.delete(f"tag:{tag}")

            logger.info(f"Invalidated {count} cache entries with tag: {tag}")
            return count

        except Exception as e:
            logger.error(f"Tag invalidation error for {tag}: {e}")
            return 0

    async def clear_all(self) -> None:
        """Clear all cache data"""
        # Clear L1
        self._memory_cache.clear()
        self._memory_access_order.clear()

        # Clear L2
        if self._redis:
            try:
                await self._redis.flushdb()
                logger.info("All cache data cleared")
            except Exception as e:
                logger.error(f"Redis clear error: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "l1_cache_size": len(self._memory_cache),
            "l1_cache_limit": self.max_memory_cache_size,
        }

    # Cache warming methods
    async def warm_search_cache(self, popular_queries: list[str]) -> None:
        """Pre-warm cache with popular search queries"""
        logger.info(f"Warming cache with {len(popular_queries)} popular queries")

        for query in popular_queries:
            cache_key = CacheKey("search", f"warm:{query}")
            # This would typically call the actual search service
            # await self.set(cache_key, search_results, ttl=7200, tags=["search",
            # "warmed"])

    # Private methods
    def _add_to_memory_cache(self, key: str, entry: CacheEntry) -> None:
        """Add entry to L1 memory cache with LRU eviction"""
        # Remove if exists (to update position)
        if key in self._memory_cache:
            self._memory_access_order.remove(key)

        # Add to cache
        self._memory_cache[key] = entry
        self._memory_access_order.append(key)

        # Evict if over limit
        while len(self._memory_cache) > self.max_memory_cache_size:
            oldest_key = self._memory_access_order.pop(0)
            del self._memory_cache[oldest_key]

    def _remove_from_memory_cache(self, key: str) -> None:
        """Remove entry from L1 memory cache"""
        if key in self._memory_cache:
            del self._memory_cache[key]
            if key in self._memory_access_order:
                self._memory_access_order.remove(key)

    def _update_access_order(self, key: str) -> None:
        """Update LRU access order"""
        if key in self._memory_access_order:
            self._memory_access_order.remove(key)
            self._memory_access_order.append(key)

    async def _cleanup_expired(self) -> None:
        """Background task to cleanup expired cache entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                # Clean L1 cache
                expired_keys = []
                for key, entry in self._memory_cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)

                for key in expired_keys:
                    self._remove_from_memory_cache(key)

                if expired_keys:
                    logger.debug(
                        f"Cleaned {len(expired_keys)} expired L1 cache entries",
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    async def _report_metrics(self) -> None:
        """Background task to report cache metrics"""
        while True:
            try:
                await asyncio.sleep(600)  # Report every 10 minutes
                stats = self.get_stats()
                logger.info(f"Cache metrics: {stats}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics reporting error: {e}")


# Context manager for cache service


@asynccontextmanager
async def get_cache_service(
    redis_url: str = "redis://localhost:6379/0",
) -> RedisCacheService:
    """Context manager for cache service lifecycle"""
    service = RedisCacheService(redis_url=redis_url)
    try:
        await service.initialize()
        yield service
    finally:
        await service.close()


# Singleton instance
_cache_service: RedisCacheService | None = None


async def get_cache() -> RedisCacheService:
    """Get global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = RedisCacheService()
        await _cache_service.initialize()
    return _cache_service


async def create_redis_cache_service(config: CacheConfig) -> RedisCacheService:
    """Factory function to create and initialize Redis cache service"""
    service = RedisCacheService(config=config)
    await service.initialize()
    return service


# Decorators for caching


def cached(ttl: int = 3600, tags: list[str] | None = None):
    """Decorator for caching function results"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = await get_cache()

            # Generate cache key from function name and args
            key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = CacheKey("function", key_data)

            # Try to get from cache
            result = await cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl, tags=tags)

            return result

        return wrapper

    return decorator


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        async with get_cache_service() as cache:
            # Test basic operations
            await cache.set("test:key", {"data": "test"}, ttl=60)
            result = await cache.get("test:key")
            print(f"Cache result: {result}")

            # Test tag-based invalidation
            await cache.set("user:123", {"name": "John"}, tags=["user", "profile"])
            await cache.set("user:456", {"name": "Jane"}, tags=["user", "profile"])

            invalidated = await cache.invalidate_by_tag("user")
            print(f"Invalidated {invalidated} entries")

            # Show stats
            stats = cache.get_stats()
            print(f"Cache stats: {stats}")

    asyncio.run(main())
