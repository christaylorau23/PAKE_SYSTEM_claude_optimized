"""Enterprise Caching Service
Task T046-T049 - Phase 18 Production System Integration.

Multi-level caching with Redis for enterprise performance optimization.
Implements cache-aside, write-through, and cache prefetching patterns.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration."""

    def __init__(self) -> None:
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
        self.retry_on_timeout = True
        self.socket_keepalive = True
        self.socket_keepalive_options = {}

        # Cache TTL defaults
        self.default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5 minutes
        self.short_ttl = int(os.getenv("CACHE_SHORT_TTL", "60"))  # 1 minute
        self.long_ttl = int(os.getenv("CACHE_LONG_TTL", "3600"))  # 1 hour


class CacheService:
    """Enterprise Redis caching service."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        self.config = config or CacheConfig()
        self.pool: ConnectionPool | None = None
        self.redis: redis.Redis | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._initialized:
            return

        try:
            self.pool = ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_keepalive=self.config.socket_keepalive,
                socket_keepalive_options=self.config.socket_keepalive_options,
            )

            self.redis = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.redis.ping()
            self._initialized = True
            logger.info("Redis cache service initialized successfully")

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to initialize Redis cache: %s", e)
            raise

    async def close(self) -> None:
        """Close Redis connections."""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
        self._initialized = False
        logger.info("Redis cache service closed")

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self._initialized:
            await self.initialize()

        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value.decode("utf-8") if isinstance(value, bytes) else value

        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Cache get error for key %s: %s", key, e)
            return None

    async def set(
        self, key: str, value: Any, ttl: int | None = None, nx: bool = False
    ) -> bool:
        """Set value in cache."""
        if not self._initialized:
            await self.initialize()

        try:
            # Serialize value
            if isinstance(value, dict | list):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)

            # Set TTL
            ttl = ttl or self.config.default_ttl

            # Set with optional NX (only if not exists)
            if nx:
                result = await self.redis.set(key, serialized_value, ex=ttl, nx=True)
            else:
                result = await self.redis.set(key, serialized_value, ex=ttl)

            return result is not None

        except (ValueError, RuntimeError) as e:
            logger.error("Cache set error for key %s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.delete(key)
            return result > 0
        except (ValueError, RuntimeError) as e:
            logger.error("Cache delete error for key %s: %s", key, e)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._initialized:
            await self.initialize()

        try:
            result = await self.redis.exists(key)
            return result > 0
        except (ValueError, RuntimeError) as e:
            logger.error("Cache exists error for key %s: %s", key, e)
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.redis.expire(key, ttl)
        except (ValueError, RuntimeError) as e:
            logger.error("Cache expire error for key %s: %s", key, e)
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        if not self._initialized:
            await self.initialize()

        try:
            values = await self.redis.mget(keys)
            result = {}

            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = (
                            value.decode("utf-8") if isinstance(value, bytes) else value
                        )

            return result

        except (ValueError, RuntimeError) as e:
            logger.error("Cache get_many error: %s", e)
            return {}

    async def set_many(self, mapping: Dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple values in cache."""
        if not self._initialized:
            await self.initialize()

        try:
            # Serialize values
            serialized_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, dict | list):
                    serialized_mapping[key] = json.dumps(value)
                else:
                    serialized_mapping[key] = str(value)

            # Set TTL
            ttl = ttl or self.config.default_ttl

            # Use pipeline for efficiency
            pipe = self.redis.pipeline()
            for key, value in serialized_mapping.items():
                pipe.setex(key, ttl, value)

            await pipe.execute()
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Cache set_many error: %s", e)
            return False

    async def increment(self, key: str, amount: int = 1) -> int | None:
        """Increment counter in cache."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.redis.incrby(key, amount)
        except (ValueError, RuntimeError) as e:
            logger.error("Cache increment error for key %s: %s", key, e)
            return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            info = await self.redis.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
        except (ValueError, RuntimeError) as e:
            logger.error("Cache stats error: %s", e)
            return {}


class CachePatterns:
    """Enterprise caching patterns."""

    def __init__(self) -> None:
        self.cache = cache_service

    async def cache_aside(
        self, key: str, fetch_func, ttl: int | None = None, *args, **kwargs
    ) -> Any:
        """Cache-aside pattern: Check cache first, fetch from source if miss.

        Args:
            key: Cache key
            fetch_func: Function to fetch data if cache miss
            ttl: Time to live for cached data
            *args, **kwargs: Arguments to pass to fetch_func
        """
        # Try to get from cache
        cached_value = await self.cache.get(key)
        if cached_value is not None:
            return cached_value

        # Cache miss - fetch from source
        try:
            value = (
                await fetch_func(*args, **kwargs)
                if asyncio.iscoroutinefunction(fetch_func)
                else fetch_func(*args, **kwargs)
            )

            # Store in cache
            await self.cache.set(key, value, ttl)
            return value

        except (ValueError, RuntimeError) as e:
            logger.error("Cache-aside fetch error for key %s: %s", key, e)
            raise

    async def write_through(
        self,
        key: str,
        value: Any,
        write_func,
        ttl: int | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """Write-through pattern: Write to cache and source simultaneously.

        Args:
            key: Cache key
            value: Value to cache
            write_func: Function to write to source
            ttl: Time to live for cached data
            *args, **kwargs: Arguments to pass to write_func
        """
        try:
            # Write to source first
            result = (
                await write_func(value, *args, **kwargs)
                if asyncio.iscoroutinefunction(write_func)
                else write_func(value, *args, **kwargs)
            )

            # Then write to cache
            await self.cache.set(key, value, ttl)

            return result

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Write-through error for key %s: %s", key, e)
            raise

    async def cache_prefetch(self, keys_and_fetch_funcs: Dict[str, Any], ttl: int | None = None) -> None:
        """Cache prefetch pattern: Proactively load data into cache.

        Args:
            keys_and_fetch_funcs: Dict mapping cache keys to fetch functions
            ttl: Time to live for cached data
        """
        tasks = []

        for key, fetch_func in keys_and_fetch_funcs.items():
            task = self.cache_aside(key, fetch_func, ttl)
            tasks.append(task)

        try:
            await asyncio.gather(*tasks)
            logger.info(
                "Cache prefetch completed for %s keys", len(keys_and_fetch_funcs)
            )
        except (ValueError, RuntimeError) as e:
            logger.error("Cache prefetch error: %s", e)


# Global cache service instance
cache_service = CacheService()
cache_patterns = CachePatterns(cache_service)