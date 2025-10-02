#!/usr/bin/env python3
"""PAKE System - Multi-Layered Redis Caching Strategy
Advanced caching system for event-driven hierarchical architecture.

Implements:
- L1 Cache: In-memory high-speed cache
- L2 Cache: Redis distributed cache
- L3 Cache: Persistent Redis cache with compression
- Intelligent cache warming and eviction
- Performance optimization and analytics
"""

import asyncio
import logging

# import pickle  # SECURITY: Replaced with secure serialization
import time
import zlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import default_backoff
from redis.asyncio.retry import Retry

from ...utils.secure_serialization import deserialize, serialize

# Configure logging
logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level definitions"""

    L1_MEMORY = "l1_memory"
    L2_DISTRIBUTED = "l2_distributed"
    L3_PERSISTENT = "l3_persistent"


class EvictionPolicy(Enum):
    """Cache eviction policies"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns


class CacheOperation(Enum):
    """Cache operation types"""

    GET = "get"
    SET = "set"
    DELETE = "delete"
    INVALIDATE = "invalidate"
    WARM = "warm"


@dataclass
class CacheConfig:
    """Configuration for cache layers"""

    # L1 Memory Cache
    l1_enabled: bool = True
    l1_max_size: int = 1000
    l1_ttl: int = 300  # 5 minutes
    l1_eviction_policy: EvictionPolicy = EvictionPolicy.LRU

    # L2 Distributed Cache
    l2_enabled: bool = True
    l2_max_size: int = 10000
    l2_ttl: int = 3600  # 1 hour
    l2_eviction_policy: EvictionPolicy = EvictionPolicy.LRU

    # L3 Persistent Cache
    l3_enabled: bool = True
    l3_max_size: int = 100000
    l3_ttl: int = 86400  # 24 hours
    l3_eviction_policy: EvictionPolicy = EvictionPolicy.TTL
    l3_compression: bool = True

    # Global settings
    enable_statistics: bool = True
    enable_warming: bool = True
    enable_prefetching: bool = True
    batch_operations: bool = True
    consistency_level: str = "eventual"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    ttl: int | None = None
    size: int = 0
    compressed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStatistics:
    """Cache performance statistics"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    size: int = 0
    memory_usage: int = 0
    avg_access_time: float = 0.0
    hit_rate: float = 0.0


class CacheLayer(ABC):
    """Abstract base class for cache layers"""

    def __init__(self, level: CacheLevel, config: CacheConfig):
        self.level = level
        self.config = config
        self.statistics = CacheStatistics()
        self.access_times: list[float] = []
        self.max_access_times = 1000

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value from cache"""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""

    @abstractmethod
    async def size(self) -> int:
        """Get cache size"""

    def update_statistics(
        self,
        operation: CacheOperation,
        hit: Optional[bool] = None,
        access_time: Optional[float] = None,
    ) -> None:
        """Update cache statistics"""
        if operation == CacheOperation.GET:
            if hit:
                self.statistics.hits += 1
            else:
                self.statistics.misses += 1
        elif operation == CacheOperation.SET:
            self.statistics.sets += 1
        elif operation == CacheOperation.DELETE:
            self.statistics.deletes += 1

        # Update hit rate
        total_accesses = self.statistics.hits + self.statistics.misses
        if total_accesses > 0:
            self.statistics.hit_rate = self.statistics.hits / total_accesses

        # Update access time
        if access_time is not None:
            self.access_times.append(access_time)
            if len(self.access_times) > self.max_access_times:
                self.access_times = self.access_times[-self.max_access_times :]

            self.statistics.avg_access_time = sum(self.access_times) / len(
                self.access_times,
            )

    def get_statistics(self) -> CacheStatistics:
        """Get cache statistics"""
        return self.statistics


class L1MemoryCache(CacheLayer):
    """Level 1 in-memory cache"""

    def __init__(self, config: CacheConfig):
        super().__init__(CacheLevel.L1_MEMORY, config)
        self.cache: dict[str, CacheEntry] = {}
        self.access_order: list[str] = []  # For LRU
        self.frequency: dict[str, int] = {}  # For LFU

    async def get(self, key: str) -> Any | None:
        """Get value from L1 cache"""
        start_time = time.time()

        try:
            if key in self.cache:
                entry = self.cache[key]

                # Check TTL
                if self._is_expired(entry):
                    await self.delete(key)
                    self.update_statistics(
                        CacheOperation.GET,
                        hit=False,
                        access_time=time.time() - start_time,
                    )
                    return None

                # Update access metadata
                entry.accessed_at = datetime.now(UTC)
                entry.access_count += 1

                # Update access order for LRU
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)

                # Update frequency for LFU
                self.frequency[key] = self.frequency.get(key, 0) + 1

                self.update_statistics(
                    CacheOperation.GET,
                    hit=True,
                    access_time=time.time() - start_time,
                )
                return entry.value

            self.update_statistics(
                CacheOperation.GET,
                hit=False,
                access_time=time.time() - start_time,
            )
            return None

        except Exception as e:
            logger.error(f"L1 cache get error: {e}")
            self.update_statistics(
                CacheOperation.GET,
                hit=False,
                access_time=time.time() - start_time,
            )
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in L1 cache"""
        try:
            # Check if we need to evict
            if len(self.cache) >= self.config.l1_max_size and key not in self.cache:
                await self._evict()

            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl or self.config.l1_ttl,
                size=self._calculate_size(value),
            )

            self.cache[key] = entry

            # Update access tracking
            if key not in self.access_order:
                self.access_order.append(key)

            self.frequency[key] = self.frequency.get(key, 0) + 1

            self.update_statistics(CacheOperation.SET)
            return True

        except Exception as e:
            logger.error(f"L1 cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from L1 cache"""
        try:
            if key in self.cache:
                del self.cache[key]

                if key in self.access_order:
                    self.access_order.remove(key)

                if key in self.frequency:
                    del self.frequency[key]

                self.update_statistics(CacheOperation.DELETE)
                return True

            return False

        except Exception as e:
            logger.error(f"L1 cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in L1 cache"""
        return key in self.cache and not self._is_expired(self.cache[key])

    async def clear(self) -> bool:
        """Clear L1 cache"""
        try:
            self.cache.clear()
            self.access_order.clear()
            self.frequency.clear()
            return True
        except Exception as e:
            logger.error(f"L1 cache clear error: {e}")
            return False

    async def size(self) -> int:
        """Get L1 cache size"""
        return len(self.cache)

    async def _evict(self):
        """Evict entries based on configured policy"""
        if not self.cache:
            return

        if self.config.l1_eviction_policy == EvictionPolicy.LRU:
            # Remove least recently used
            if self.access_order:
                key_to_remove = self.access_order[0]
                await self.delete(key_to_remove)

        elif self.config.l1_eviction_policy == EvictionPolicy.LFU:
            # Remove least frequently used
            if self.frequency:
                key_to_remove = min(
                    self.frequency.keys(),
                    key=lambda k: self.frequency[k],
                )
                await self.delete(key_to_remove)

        elif self.config.l1_eviction_policy == EvictionPolicy.TTL:
            # Remove expired entries first
            expired_keys = [
                key for key, entry in self.cache.items() if self._is_expired(entry)
            ]

            for key in expired_keys:
                await self.delete(key)

        self.statistics.evictions += 1

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        if entry.ttl is None:
            return False

        age = (datetime.now(UTC) - entry.created_at).total_seconds()
        return age > entry.ttl

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of cached value"""
        try:
            return len(serialize(value))
        except BaseException:
            return len(str(value))


class L2DistributedCache(CacheLayer):
    """Level 2 Redis distributed cache"""

    def __init__(self, config: CacheConfig, redis_url: str = "redis://localhost:6379"):
        super().__init__(CacheLevel.L2_DISTRIBUTED, config)
        self.redis_url = redis_url
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.key_prefix = "pake:l2:"

    async def connect(self) -> None:
        """Connect to Redis"""
        if self.redis_pool is None:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                retry=Retry(default_backoff(), 3),
            )

    async def get(self, key: str) -> Any | None:
        """Get value from L2 cache"""
        start_time = time.time()

        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"
                data = await r.get(prefixed_key)

                if data is not None:
                    # Deserialize value
                    value = deserialize(data)

                    # Update access count
                    await r.incr(f"{prefixed_key}:access_count")

                    self.update_statistics(
                        CacheOperation.GET,
                        hit=True,
                        access_time=time.time() - start_time,
                    )
                    return value

                self.update_statistics(
                    CacheOperation.GET,
                    hit=False,
                    access_time=time.time() - start_time,
                )
                return None

        except Exception as e:
            logger.error(f"L2 cache get error: {e}")
            self.update_statistics(
                CacheOperation.GET,
                hit=False,
                access_time=time.time() - start_time,
            )
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in L2 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"
                ttl = ttl or self.config.l2_ttl

                # Serialize value
                data = serialize(value)

                # Set value with TTL
                await r.setex(prefixed_key, ttl, data)

                # Set access metadata
                await r.setex(f"{prefixed_key}:access_count", ttl, 0)
                await r.setex(
                    f"{prefixed_key}:created_at",
                    ttl,
                    datetime.now(UTC).isoformat(),
                )

                self.update_statistics(CacheOperation.SET)
                return True

        except Exception as e:
            logger.error(f"L2 cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from L2 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"

                # Delete main key and metadata
                deleted = await r.delete(
                    prefixed_key,
                    f"{prefixed_key}:access_count",
                    f"{prefixed_key}:created_at",
                )

                if deleted > 0:
                    self.update_statistics(CacheOperation.DELETE)
                    return True

                return False

        except Exception as e:
            logger.error(f"L2 cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in L2 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"
                return await r.exists(prefixed_key)

        except Exception as e:
            logger.error(f"L2 cache exists error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear L2 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                # Find and delete all keys with our prefix
                keys = await r.keys(f"{self.key_prefix}*")
                if keys:
                    await r.delete(*keys)

                return True

        except Exception as e:
            logger.error(f"L2 cache clear error: {e}")
            return False

    async def size(self) -> int:
        """Get L2 cache size"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                keys = await r.keys(f"{self.key_prefix}*")
                return len(
                    [
                        k
                        for k in keys
                        if not k.endswith((b":access_count", b":created_at"))
                    ],
                )

        except Exception as e:
            logger.error(f"L2 cache size error: {e}")
            return 0


class L3PersistentCache(CacheLayer):
    """Level 3 persistent Redis cache with compression"""

    def __init__(self, config: CacheConfig, redis_url: str = "redis://localhost:6379"):
        super().__init__(CacheLevel.L3_PERSISTENT, config)
        self.redis_url = redis_url
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.key_prefix = "pake:l3:"

    async def connect(self) -> None:
        """Connect to Redis"""
        if self.redis_pool is None:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                retry=Retry(default_backoff(), 3),
            )

    async def get(self, key: str) -> Any | None:
        """Get value from L3 cache"""
        start_time = time.time()

        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"
                data = await r.get(prefixed_key)

                if data is not None:
                    # Check if compressed
                    metadata = await r.hgetall(f"{prefixed_key}:meta")
                    compressed = metadata.get(b"compressed", b"false") == b"true"

                    # Decompress if needed
                    if compressed:
                        data = zlib.decompress(data)

                    # Deserialize value
                    value = deserialize(data)

                    # Update access metadata
                    await r.hset(
                        f"{prefixed_key}:meta",
                        "last_access",
                        datetime.now(UTC).isoformat(),
                    )
                    await r.hincrby(f"{prefixed_key}:meta", "access_count", 1)

                    self.update_statistics(
                        CacheOperation.GET,
                        hit=True,
                        access_time=time.time() - start_time,
                    )
                    return value

                self.update_statistics(
                    CacheOperation.GET,
                    hit=False,
                    access_time=time.time() - start_time,
                )
                return None

        except Exception as e:
            logger.error(f"L3 cache get error: {e}")
            self.update_statistics(
                CacheOperation.GET,
                hit=False,
                access_time=time.time() - start_time,
            )
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in L3 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"
                ttl = ttl or self.config.l3_ttl

                # Serialize value
                data = serialize(value)
                original_size = len(data)

                # Compress if enabled
                compressed = False
                if (
                    self.config.l3_compression and original_size > 1024
                ):  # Only compress large objects
                    compressed_data = zlib.compress(data)
                    if (
                        len(compressed_data) < original_size * 0.8
                    ):  # Only use if 20% savings
                        data = compressed_data
                        compressed = True

                # Set value with TTL
                await r.setex(prefixed_key, ttl, data)

                # Set metadata
                metadata = {
                    "created_at": datetime.now(UTC).isoformat(),
                    "original_size": original_size,
                    "stored_size": len(data),
                    "compressed": str(compressed).lower(),
                    "access_count": 0,
                }

                await r.hset(f"{prefixed_key}:meta", mapping=metadata)
                await r.expire(f"{prefixed_key}:meta", ttl)

                self.update_statistics(CacheOperation.SET)
                return True

        except Exception as e:
            logger.error(f"L3 cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from L3 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"

                # Delete main key and metadata
                deleted = await r.delete(prefixed_key, f"{prefixed_key}:meta")

                if deleted > 0:
                    self.update_statistics(CacheOperation.DELETE)
                    return True

                return False

        except Exception as e:
            logger.error(f"L3 cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in L3 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                prefixed_key = f"{self.key_prefix}{key}"
                return await r.exists(prefixed_key)

        except Exception as e:
            logger.error(f"L3 cache exists error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear L3 cache"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                # Find and delete all keys with our prefix
                keys = await r.keys(f"{self.key_prefix}*")
                if keys:
                    await r.delete(*keys)

                return True

        except Exception as e:
            logger.error(f"L3 cache clear error: {e}")
            return False

    async def size(self) -> int:
        """Get L3 cache size"""
        try:
            await self.connect()

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                keys = await r.keys(f"{self.key_prefix}*")
                return len([k for k in keys if not k.endswith(b":meta")])

        except Exception as e:
            logger.error(f"L3 cache size error: {e}")
            return 0


class MultiLayeredCacheStrategy:
    """Multi-layered caching strategy coordinator"""

    def __init__(self, config: CacheConfig, redis_url: str = "redis://localhost:6379"):
        self.config = config
        self.redis_url = redis_url

        # Initialize cache layers
        self.layers: dict[CacheLevel, CacheLayer] = {}

        if config.l1_enabled:
            self.layers[CacheLevel.L1_MEMORY] = L1MemoryCache(config)

        if config.l2_enabled:
            self.layers[CacheLevel.L2_DISTRIBUTED] = L2DistributedCache(
                config,
                redis_url,
            )

        if config.l3_enabled:
            self.layers[CacheLevel.L3_PERSISTENT] = L3PersistentCache(config, redis_url)

        # Cache warming and prefetching
        self.warming_tasks: list[asyncio.Task] = []
        self.prefetch_patterns: dict[str, list[str]] = {}

        logger.info(
            f"MultiLayeredCacheStrategy initialized with {len(self.layers)} layers",
        )

    async def get(self, namespace: str, key: str) -> Any | None:
        """Get value from cache hierarchy"""
        cache_key = f"{namespace}:{key}"

        # Try L1 first (fastest)
        if CacheLevel.L1_MEMORY in self.layers:
            value = await self.layers[CacheLevel.L1_MEMORY].get(cache_key)
            if value is not None:
                return value

        # Try L2 (distributed)
        if CacheLevel.L2_DISTRIBUTED in self.layers:
            value = await self.layers[CacheLevel.L2_DISTRIBUTED].get(cache_key)
            if value is not None:
                # Populate L1 cache
                if CacheLevel.L1_MEMORY in self.layers:
                    await self.layers[CacheLevel.L1_MEMORY].set(cache_key, value)
                return value

        # Try L3 (persistent)
        if CacheLevel.L3_PERSISTENT in self.layers:
            value = await self.layers[CacheLevel.L3_PERSISTENT].get(cache_key)
            if value is not None:
                # Populate L2 and L1 caches
                if CacheLevel.L2_DISTRIBUTED in self.layers:
                    # nosec B608 - This is cache key setting, not SQL execution
                    await self.layers[CacheLevel.L2_DISTRIBUTED].set(cache_key, value)

                if CacheLevel.L1_MEMORY in self.layers:
                    await self.layers[CacheLevel.L1_MEMORY].set(cache_key, value)

                return value

        return None

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_override: Optional[int] = None,
    ) -> bool:
        """Set value in appropriate cache layers"""
        cache_key = f"{namespace}:{key}"
        success = True

        # Set in all enabled layers
        for level, layer in self.layers.items():
            try:
                # Use appropriate TTL for each layer
                ttl = ttl_override
                if ttl is None:
                    if level == CacheLevel.L1_MEMORY:
                        ttl = self.config.l1_ttl
                    elif level == CacheLevel.L2_DISTRIBUTED:
                        ttl = self.config.l2_ttl
                    elif level == CacheLevel.L3_PERSISTENT:
                        ttl = self.config.l3_ttl

                layer_success = await layer.set(cache_key, value, ttl)
                success = success and layer_success

            except Exception as e:
                logger.error(f"Failed to set in {level.value}: {e}")
                success = False

        # Trigger prefetching if enabled
        if self.config.enable_prefetching:
            await self._trigger_prefetching(namespace, key, value)

        return success

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete value from all cache layers"""
        cache_key = f"{namespace}:{key}"
        success = True

        for level, layer in self.layers.items():
            try:
                layer_success = await layer.delete(cache_key)
                success = success and layer_success

            except Exception as e:
                logger.error(f"Failed to delete from {level.value}: {e}")
                success = False

        return success

    async def invalidate_namespace(self, namespace: str) -> bool:
        """Invalidate all keys in a namespace"""
        # This is a simplified implementation
        # In production, you'd want to use Redis patterns or keep a registry
        success = True

        for level, layer in self.layers.items():
            try:
                # For now, we'll clear the entire layer
                # In production, implement namespace-specific clearing
                if hasattr(layer, "clear"):
                    await layer.clear()

            except Exception as e:
                logger.error(f"Failed to invalidate namespace in {level.value}: {e}")
                success = False

        return success

    async def warm_cache(self, namespace: str, keys: list[str], data_loader: Callable):
        """Warm cache with data from data loader"""
        if not self.config.enable_warming:
            return

        warming_task = asyncio.create_task(
            self._warm_cache_async(namespace, keys, data_loader),
        )

        self.warming_tasks.append(warming_task)

    async def _warm_cache_async(
        self,
        namespace: str,
        keys: list[str],
        data_loader: Callable,
    ):
        """Asynchronously warm cache"""
        logger.info(
            f"Starting cache warming for namespace {namespace} with {len(keys)} keys",
        )

        for key in keys:
            try:
                # Check if already cached
                cached_value = await self.get(namespace, key)
                if cached_value is not None:
                    continue

                # Load data and cache it
                if asyncio.iscoroutinefunction(data_loader):
                    value = await data_loader(key)
                else:
                    value = data_loader(key)

                if value is not None:
                    await self.set(namespace, key, value)

                # Add small delay to not overwhelm the system
                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Cache warming error for key {key}: {e}")

        logger.info(f"Cache warming completed for namespace {namespace}")

    async def _trigger_prefetching(self, namespace: str, key: str, value: Any):
        """Trigger predictive prefetching based on patterns"""
        if not self.config.enable_prefetching:
            return

        # Simple pattern-based prefetching
        if namespace in self.prefetch_patterns:
            patterns = self.prefetch_patterns[namespace]

            for pattern in patterns:
                # Generate related keys based on patterns
                related_keys = self._generate_related_keys(key, pattern)

                # Prefetch related keys (simplified implementation)
                for related_key in related_keys[:5]:  # Limit prefetching
                    asyncio.create_task(self._prefetch_key(namespace, related_key))

    def _generate_related_keys(self, base_key: str, pattern: str) -> list[str]:
        """Generate related keys based on patterns"""
        # Simplified pattern matching
        related_keys = []

        if pattern == "sequential":
            # Generate sequential keys
            if base_key.endswith("_0") or base_key.endswith("_1"):
                base = base_key.rsplit("_", 1)[0]
                for i in range(1, 4):
                    related_keys.append(f"{base}_{i}")

        elif pattern == "hierarchical":
            # Generate hierarchical keys
            if ":" in base_key:
                parts = base_key.split(":")
                for i in range(len(parts)):
                    related_keys.append(":".join(parts[: i + 1]))

        return related_keys

    async def _prefetch_key(self, namespace: str, key: str):
        """Prefetch a specific key"""
        try:
            # Check if already cached
            cached_value = await self.get(namespace, key)
            if cached_value is not None:
                return

            # In a real implementation, you'd load the data here
            # For now, we just log the prefetching attempt
            logger.debug(f"Prefetching {namespace}:{key}")

        except Exception as e:
            logger.error(f"Prefetching error for {namespace}:{key}: {e}")

    async def get_statistics(self) -> dict[str, CacheStatistics]:
        """Get statistics for all cache layers"""
        stats = {}

        for level, layer in self.layers.items():
            stats[level.value] = layer.get_statistics()

        return stats

    async def get_health_status(self) -> dict[str, Any]:
        """Get health status of cache system"""
        health = {
            "overall_status": "healthy",
            "layers": {},
            "total_size": 0,
            "total_hit_rate": 0.0,
        }

        total_hits = 0
        total_accesses = 0

        for level, layer in self.layers.items():
            try:
                stats = layer.get_statistics()
                size = await layer.size()

                layer_health = {
                    "status": "healthy",
                    "size": size,
                    "hit_rate": stats.hit_rate,
                    "hits": stats.hits,
                    "misses": stats.misses,
                }

                health["layers"][level.value] = layer_health
                health["total_size"] += size

                total_hits += stats.hits
                total_accesses += stats.hits + stats.misses

            except Exception as e:
                logger.error(f"Health check error for {level.value}: {e}")
                health["layers"][level.value] = {"status": "unhealthy", "error": str(e)}
                health["overall_status"] = "degraded"

        if total_accesses > 0:
            health["total_hit_rate"] = total_hits / total_accesses

        return health

    def add_prefetch_pattern(self, namespace: str, pattern: str):
        """Add prefetch pattern for namespace"""
        if namespace not in self.prefetch_patterns:
            self.prefetch_patterns[namespace] = []

        self.prefetch_patterns[namespace].append(pattern)

    async def cleanup(self):
        """Cleanup cache resources"""
        # Cancel warming tasks
        for task in self.warming_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.warming_tasks:
            await asyncio.gather(*self.warming_tasks, return_exceptions=True)

        # Close Redis connections
        for layer in self.layers.values():
            if hasattr(layer, "redis_pool") and layer.redis_pool:
                await layer.redis_pool.disconnect()

        logger.info("Cache cleanup completed")


# Factory functions
async def create_standard_cache_strategy(
    redis_url: str = "redis://localhost:6379",
) -> MultiLayeredCacheStrategy:
    """Create standard cache strategy"""
    config = CacheConfig(
        l1_enabled=True,
        l1_max_size=1000,
        l1_ttl=300,
        l2_enabled=True,
        l2_max_size=10000,
        l2_ttl=3600,
        l3_enabled=True,
        l3_max_size=100000,
        l3_ttl=86400,
        l3_compression=True,
    )

    return MultiLayeredCacheStrategy(config, redis_url)


async def create_high_performance_cache_strategy(
    redis_url: str = "redis://localhost:6379",
) -> MultiLayeredCacheStrategy:
    """Create high-performance cache strategy"""
    config = CacheConfig(
        l1_enabled=True,
        l1_max_size=5000,
        l1_ttl=600,
        l1_eviction_policy=EvictionPolicy.LRU,
        l2_enabled=True,
        l2_max_size=50000,
        l2_ttl=7200,
        l2_eviction_policy=EvictionPolicy.ADAPTIVE,
        l3_enabled=True,
        l3_max_size=500000,
        l3_ttl=172800,  # 48 hours
        l3_compression=True,
        enable_warming=True,
        enable_prefetching=True,
        batch_operations=True,
    )

    return MultiLayeredCacheStrategy(config, redis_url)
