#!/usr/bin/env python3
"""PAKE System - Advanced Performance Optimization Service
Comprehensive performance optimization for ingestion pipeline

Features:
- Intelligent caching with TTL management
- Connection pooling and session reuse
- Batch processing optimization
- Memory management and resource cleanup
- Adaptive rate limiting
- Query optimization and result deduplication
- Concurrent execution optimization
- Performance monitoring and metrics
"""

import asyncio
import hashlib
import json
import logging
import time
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    import aioredis

    REDIS_AVAILABLE = True
except Exception:
    aioredis = None
    REDIS_AVAILABLE = False
import gc
from collections import defaultdict

import psutil

logger = logging.getLogger(__name__)


class OptimizationMode(Enum):
    """Performance optimization modes"""

    SPEED_FIRST = "speed_first"  # Maximize execution speed
    MEMORY_FIRST = "memory_first"  # Minimize memory usage
    BALANCED = "balanced"  # Balance speed and memory
    THROUGHPUT = "throughput"  # Maximize data throughput


@dataclass
class PerformanceMetrics:
    """Performance monitoring metrics"""

    execution_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    network_requests: int = 0
    concurrent_tasks: int = 0
    error_rate: float = 0.0
    throughput_items_per_second: float = 0.0
    resource_pool_size: int = 0


@dataclass
class OptimizationConfig:
    """Advanced performance optimization configuration"""

    mode: OptimizationMode = OptimizationMode.BALANCED

    # Caching configuration
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 10000
    cache_compression_enabled: bool = True

    # Connection pooling
    connection_pool_enabled: bool = True
    max_connections_per_host: int = 20
    connection_timeout: int = 30
    connection_keepalive: int = 300

    # Batch processing
    batch_processing_enabled: bool = True
    optimal_batch_size: int = 50
    max_batch_size: int = 200
    batch_timeout: int = 10

    # Concurrency control
    max_concurrent_tasks: int = 10
    adaptive_concurrency: bool = True
    min_concurrent_tasks: int = 2
    max_concurrent_tasks_limit: int = 50

    # Memory management
    memory_monitoring_enabled: bool = True
    memory_threshold_mb: int = 1000
    garbage_collection_interval: int = 300
    weak_reference_cleanup: bool = True

    # Rate limiting
    adaptive_rate_limiting: bool = True
    base_rate_limit_per_second: float = 10.0
    burst_rate_multiplier: float = 2.0
    rate_limit_window_seconds: int = 60


class IntelligentCache:
    """Advanced caching system with TTL, compression, and LRU eviction"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_times: dict[str, float] = {}
        self._cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._lock = asyncio.Lock()

    def _generate_key(
        self,
        namespace: str,
        identifier: str,
        params: dict[str, Any] = None,
    ) -> str:
        """Generate cache key with namespace and parameter hashing"""
        key_data = f"{namespace}:{identifier}"
        if params:
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
            key_data = f"{key_data}:{param_hash}"
        return key_data

    async def get(
        self,
        namespace: str,
        identifier: str,
        params: dict[str, Any] = None,
    ) -> Any | None:
        """Retrieve item from cache with TTL validation"""
        async with self._lock:
            key = self._generate_key(namespace, identifier, params)

            if key not in self._cache:
                self._cache_stats["misses"] += 1
                return None

            entry = self._cache[key]
            current_time = time.time()

            # Check TTL expiration
            if current_time > entry["expires_at"]:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                self._cache_stats["misses"] += 1
                return None

            # Update access time for LRU
            self._access_times[key] = current_time
            self._cache_stats["hits"] += 1

            return entry["data"]

    async def set(
        self,
        namespace: str,
        identifier: str,
        data: Any,
        params: dict[str, Any] = None,
        ttl_override: int | None = None,
    ) -> None:
        """Store item in cache with TTL and eviction management"""
        async with self._lock:
            key = self._generate_key(namespace, identifier, params)
            current_time = time.time()

            ttl = ttl_override or self.config.cache_ttl_seconds
            expires_at = current_time + ttl

            # Check if cache is full and needs eviction
            if len(self._cache) >= self.config.cache_max_size:
                await self._evict_lru()

            self._cache[key] = {
                "data": data,
                "created_at": current_time,
                "expires_at": expires_at,
                "size_bytes": len(str(data)),  # Approximate size
            }
            self._access_times[key] = current_time

    async def _evict_lru(self) -> None:
        """Evict least recently used items"""
        if not self._access_times:
            return

        # Find oldest accessed key
        oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]

        if oldest_key in self._cache:
            del self._cache[oldest_key]
        del self._access_times[oldest_key]
        self._cache_stats["evictions"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / max(total_requests, 1)

        return {
            "cache_size": len(self._cache),
            "hit_rate": hit_rate,
            "total_hits": self._cache_stats["hits"],
            "total_misses": self._cache_stats["misses"],
            "total_evictions": self._cache_stats["evictions"],
        }


class ConnectionPool:
    """Advanced connection pool with health monitoring"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._pools: dict[str, list[Any]] = defaultdict(list)
        self._pool_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"created": 0, "reused": 0, "closed": 0},
        )
        self._pool_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get_session(
        self,
        service_name: str,
        session_factory: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Get connection from pool or create new one"""
        async with self._pool_locks[service_name]:
            pool = self._pools[service_name]

            # Try to reuse existing connection
            if pool:
                session = pool.pop()
                self._pool_stats[service_name]["reused"] += 1
                return session

            # Create new connection
            session = await session_factory()
            self._pool_stats[service_name]["created"] += 1
            return session

    async def return_session(self, service_name: str, session: Any) -> None:
        """Return connection to pool"""
        async with self._pool_locks[service_name]:
            pool = self._pools[service_name]

            # Only keep up to max_connections_per_host
            if len(pool) < self.config.max_connections_per_host:
                pool.append(session)
            else:
                # Close excess connection
                if hasattr(session, "close"):
                    await session.close()
                self._pool_stats[service_name]["closed"] += 1

    async def cleanup_pools(self) -> None:
        """Clean up all connection pools"""
        for service_name, pool in self._pools.items():
            while pool:
                session = pool.pop()
                if hasattr(session, "close"):
                    await session.close()
                self._pool_stats[service_name]["closed"] += 1

    def get_pool_stats(self) -> dict[str, dict[str, int]]:
        """Get connection pool statistics"""
        return dict(self._pool_stats)


class BatchProcessor:
    """Intelligent batch processing with adaptive sizing"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._batch_stats = defaultdict(
            lambda: {
                "batches_processed": 0,
                "items_processed": 0,
                "avg_batch_time": 0.0,
            },
        )

    async def process_batch(
        self,
        items: list[Any],
        processor: Callable[[list[Any]], Awaitable[list[Any]]],
        batch_key: str = "default",
    ) -> list[Any]:
        """Process items in optimized batches"""
        if not items:
            return []

        if not self.config.batch_processing_enabled:
            return await processor(items)

        results = []
        batch_size = self._calculate_optimal_batch_size(len(items), batch_key)

        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            start_time = time.time()

            try:
                batch_results = await asyncio.wait_for(
                    processor(batch),
                    timeout=self.config.batch_timeout,
                )
                results.extend(batch_results)

                # Update batch statistics
                execution_time = time.time() - start_time
                stats = self._batch_stats[batch_key]
                stats["batches_processed"] += 1
                stats["items_processed"] += len(batch)
                stats["avg_batch_time"] = (stats["avg_batch_time"] + execution_time) / 2

            except TimeoutError:
                logger.warning(
                    f"Batch processing timeout for {batch_key}, batch size: {len(batch)}",
                )
                # Process items individually as fallback
                for item in batch:
                    try:
                        item_result = await processor([item])
                        results.extend(item_result)
                    except Exception as e:
                        logger.error(f"Failed to process individual item: {e}")

        return results

    def _calculate_optimal_batch_size(self, total_items: int, batch_key: str) -> int:
        """Calculate optimal batch size based on historical performance"""
        base_size = min(self.config.optimal_batch_size, total_items)
        max_size = min(self.config.max_batch_size, total_items)

        # Use historical performance to adjust batch size
        stats = self._batch_stats[batch_key]
        if stats["batches_processed"] > 5:  # Have enough data
            avg_time = stats["avg_batch_time"]
            if avg_time > 5.0:  # Slow batches, reduce size
                return max(base_size // 2, 10)
            if avg_time < 1.0:  # Fast batches, increase size
                return min(base_size * 2, max_size)

        return base_size


class AdaptiveRateLimiter:
    """Adaptive rate limiting with burst handling"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._rate_windows: dict[str, list[float]] = defaultdict(list)
        self._error_rates: dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def acquire(self, service_name: str) -> None:
        """Acquire rate limit permit"""
        if not self.config.adaptive_rate_limiting:
            return

        async with self._lock:
            current_time = time.time()
            window = self._rate_windows[service_name]

            # Clean old entries outside the window
            cutoff_time = current_time - self.config.rate_limit_window_seconds
            window[:] = [t for t in window if t > cutoff_time]

            # Calculate current rate
            current_rate = len(window) / self.config.rate_limit_window_seconds
            max_rate = self._calculate_adaptive_rate_limit(service_name)

            # Check if we need to wait
            if current_rate >= max_rate:
                wait_time = self.config.rate_limit_window_seconds / max_rate
                await asyncio.sleep(wait_time)

            # Record this request
            window.append(current_time)

    def _calculate_adaptive_rate_limit(self, service_name: str) -> float:
        """Calculate adaptive rate limit based on error rates"""
        base_rate = self.config.base_rate_limit_per_second
        error_rate = self._error_rates[service_name]

        if error_rate > 0.1:  # High error rate, reduce rate
            return base_rate * 0.5
        if error_rate < 0.01:  # Low error rate, allow burst
            return base_rate * self.config.burst_rate_multiplier

        return base_rate

    def record_error(self, service_name: str) -> None:
        """Record error for adaptive rate calculation"""
        self._error_rates[service_name] = min(
            self._error_rates[service_name] + 0.01,
            1.0,
        )

    def record_success(self, service_name: str) -> None:
        """Record success for adaptive rate calculation"""
        self._error_rates[service_name] = max(
            self._error_rates[service_name] - 0.001,
            0.0,
        )


class MemoryManager:
    """Advanced memory management and monitoring"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._weak_refs: set[weakref.ref] = set()
        self._last_gc_time = time.time()
        self._memory_stats = {"peak_usage_mb": 0.0, "gc_collections": 0}

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self._memory_stats["peak_usage_mb"]:
            self._memory_stats["peak_usage_mb"] = memory_mb

        return memory_mb

    async def check_memory_pressure(self) -> bool:
        """Check if memory usage is high and trigger cleanup if needed"""
        if not self.config.memory_monitoring_enabled:
            return False

        memory_usage = self.get_memory_usage()

        if memory_usage > self.config.memory_threshold_mb:
            logger.info(f"Memory usage high: {memory_usage:.2f}MB, triggering cleanup")
            await self.force_cleanup()
            return True

        # Periodic garbage collection
        current_time = time.time()
        if current_time - self._last_gc_time > self.config.garbage_collection_interval:
            await self.gentle_cleanup()
            self._last_gc_time = current_time

        return False

    async def force_cleanup(self) -> None:
        """Force memory cleanup and garbage collection"""
        # Clean up weak references
        if self.config.weak_reference_cleanup:
            self._cleanup_weak_references()

        # Force garbage collection
        collected = gc.collect()
        self._memory_stats["gc_collections"] += 1

        logger.info(f"Force cleanup completed, collected {collected} objects")

    async def gentle_cleanup(self) -> None:
        """Gentle memory cleanup for periodic maintenance"""
        if self.config.weak_reference_cleanup:
            self._cleanup_weak_references()

        # Gentle garbage collection
        gc.collect(0)  # Only collect generation 0

    def _cleanup_weak_references(self) -> None:
        """Clean up dead weak references"""
        dead_refs = [ref for ref in self._weak_refs if ref() is None]
        for ref in dead_refs:
            self._weak_refs.discard(ref)

    def register_weak_reference(self, obj: Any) -> None:
        """Register object for weak reference cleanup"""
        if self.config.weak_reference_cleanup:
            self._weak_refs.add(weakref.ref(obj))

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory management statistics"""
        return {
            "current_usage_mb": self.get_memory_usage(),
            "peak_usage_mb": self._memory_stats["peak_usage_mb"],
            "gc_collections": self._memory_stats["gc_collections"],
            "weak_refs_count": len(self._weak_refs),
        }


class PerformanceOptimizationService:
    """Advanced performance optimization service for PAKE system"""

    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.cache = IntelligentCache(self.config)
        self.connection_pool = ConnectionPool(self.config)
        self.batch_processor = BatchProcessor(self.config)
        self.rate_limiter = AdaptiveRateLimiter(self.config)
        self.memory_manager = MemoryManager(self.config)

        self._performance_metrics = PerformanceMetrics()
        self._start_time = time.time()

        logger.info(
            f"PerformanceOptimizationService initialized with mode: {self.config.mode}",
        )

    async def optimize_concurrent_execution(
        self,
        tasks: list[Callable[[], Awaitable[Any]]],
        task_names: list[str] = None,
    ) -> list[Any]:
        """Optimize concurrent task execution with adaptive concurrency"""
        if not tasks:
            return []

        task_names = task_names or [f"task_{i}" for i in range(len(tasks))]
        results = []

        # Determine optimal concurrency level
        max_concurrent = self._calculate_optimal_concurrency(len(tasks))
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_task_with_optimization(
            task: Callable[[], Awaitable[Any]],
            task_name: str,
        ):
            async with semaphore:
                await self.rate_limiter.acquire(task_name)

                start_time = time.time()
                try:
                    result = await task()
                    execution_time = time.time() - start_time

                    # Update metrics
                    self._performance_metrics.network_requests += 1
                    self._performance_metrics.execution_time += execution_time

                    self.rate_limiter.record_success(task_name)
                    return result

                except Exception as e:
                    self.rate_limiter.record_error(task_name)
                    logger.error(f"Task {task_name} failed: {e}")
                    raise

        # Execute tasks with optimization
        coroutines = [
            execute_task_with_optimization(task, name)
            for task, name in zip(tasks, task_names, strict=False)
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Update concurrent task metrics
        self._performance_metrics.concurrent_tasks = max_concurrent

        return results

    def _calculate_optimal_concurrency(self, total_tasks: int) -> int:
        """Calculate optimal concurrency level based on system resources and configuration"""
        base_concurrency = min(self.config.max_concurrent_tasks, total_tasks)

        if not self.config.adaptive_concurrency:
            return base_concurrency

        # Adjust based on memory pressure
        memory_usage = self.memory_manager.get_memory_usage()
        if memory_usage > self.config.memory_threshold_mb * 0.8:
            return max(self.config.min_concurrent_tasks, base_concurrency // 2)

        # Adjust based on CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 80:
            return max(self.config.min_concurrent_tasks, base_concurrency // 2)
        if cpu_percent < 50:
            return min(self.config.max_concurrent_tasks_limit, base_concurrency * 2)

        return base_concurrency

    async def optimize_query_deduplication(
        self,
        queries: list[dict[str, Any]],
        service_name: str,
    ) -> list[dict[str, Any]]:
        """Remove duplicate queries and return optimized query list"""
        if not queries:
            return []

        # Generate hash for each query
        unique_queries = {}
        query_mapping = {}

        for i, query in enumerate(queries):
            query_str = json.dumps(query, sort_keys=True)
            query_hash = hashlib.sha256(query_str.encode()).hexdigest()

            if query_hash not in unique_queries:
                unique_queries[query_hash] = query
                query_mapping[query_hash] = [i]
            else:
                query_mapping[query_hash].append(i)

        deduplicated_queries = list(unique_queries.values())

        logger.info(
            f"Query deduplication for {service_name}: {len(queries)} -> {len(deduplicated_queries)} queries",
        )
        return deduplicated_queries

    async def get_comprehensive_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance metrics"""
        current_time = time.time()
        total_runtime = current_time - self._start_time

        # Update current metrics
        self._performance_metrics.memory_usage_mb = (
            self.memory_manager.get_memory_usage()
        )
        self._performance_metrics.cpu_usage_percent = psutil.cpu_percent()

        cache_stats = self.cache.get_stats()
        self._performance_metrics.cache_hits = cache_stats["total_hits"]
        self._performance_metrics.cache_misses = cache_stats["total_misses"]

        # Calculate throughput
        if total_runtime > 0:
            self._performance_metrics.throughput_items_per_second = (
                self._performance_metrics.network_requests / total_runtime
            )

        return {
            "performance_metrics": {
                "execution_time": self._performance_metrics.execution_time,
                "memory_usage_mb": self._performance_metrics.memory_usage_mb,
                "cpu_usage_percent": self._performance_metrics.cpu_usage_percent,
                "cache_hit_rate": cache_stats["hit_rate"],
                "total_network_requests": self._performance_metrics.network_requests,
                "throughput_items_per_second": self._performance_metrics.throughput_items_per_second,
                "concurrent_tasks": self._performance_metrics.concurrent_tasks,
            },
            "cache_statistics": cache_stats,
            "connection_pool_statistics": self.connection_pool.get_pool_stats(),
            "memory_statistics": self.memory_manager.get_memory_stats(),
            "total_runtime_seconds": total_runtime,
            "optimization_mode": self.config.mode.value,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive performance health check"""
        health_status = {"status": "healthy", "checks": {}, "recommendations": []}

        # Check memory usage
        memory_usage = self.memory_manager.get_memory_usage()
        memory_healthy = memory_usage < self.config.memory_threshold_mb
        health_status["checks"]["memory"] = {
            "healthy": memory_healthy,
            "current_usage_mb": memory_usage,
            "threshold_mb": self.config.memory_threshold_mb,
        }

        if not memory_healthy:
            health_status["recommendations"].append(
                "Consider reducing batch sizes or increasing memory threshold",
            )
            health_status["status"] = "warning"

        # Check cache performance
        cache_stats = self.cache.get_stats()
        cache_healthy = cache_stats["hit_rate"] > 0.3  # 30% hit rate minimum
        health_status["checks"]["cache"] = {
            "healthy": cache_healthy,
            "hit_rate": cache_stats["hit_rate"],
            "cache_size": cache_stats["cache_size"],
        }

        if not cache_healthy:
            health_status["recommendations"].append(
                "Consider increasing cache TTL or adjusting cache size",
            )

        # Check CPU usage
        cpu_usage = psutil.cpu_percent()
        cpu_healthy = cpu_usage < 90
        health_status["checks"]["cpu"] = {
            "healthy": cpu_healthy,
            "usage_percent": cpu_usage,
        }

        if not cpu_healthy:
            health_status["recommendations"].append(
                "Consider reducing concurrency or optimizing queries",
            )
            health_status["status"] = "warning"

        return health_status

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance metrics"""
        cache_stats = self.cache.get_stats()
        memory_stats = self.memory_manager.get_memory_stats()

        # Get system memory info
        memory_info = psutil.virtual_memory()

        return {
            "cache_size": cache_stats["cache_size"],
            "cache_hit_rate": cache_stats["hit_rate"],
            "cache_memory_mb": cache_stats.get("memory_usage_mb", 0),
            "memory_usage_mb": memory_stats.get("current_usage_mb", 0),
            "memory_available_mb": int(memory_info.available / 1024 / 1024),
            "gc_collections": memory_stats.get("gc_collections", 0),
            "rate_limit_remaining": getattr(self.rate_limiter, "_tokens", 100),
            "rate_limit_reset": None,  # Would need actual implementation
            "optimization_mode": self.config.mode.value,
            "concurrent_tasks": 0,  # Simplified for now
        }

    async def deduplicate_content(
        self,
        items: list[Any],
        key_extractor: callable,
    ) -> list[Any]:
        """Enhanced content deduplication with performance optimization"""
        logger.info(f"Performing intelligent deduplication on {len(items)} items")

        unique_items = []
        seen_keys = set()

        for item in items:
            # Extract key for comparison
            key = key_extractor(item)
            key_hash = hashlib.sha256(key.encode()).hexdigest()

            if key_hash not in seen_keys:
                unique_items.append(item)
                seen_keys.add(key_hash)

        dedup_ratio = (len(items) - len(unique_items)) / len(items) if items else 0
        logger.info(
            f"Deduplication complete: {len(unique_items)} unique items ({dedup_ratio:.2%} reduction)",
        )

        return unique_items

    async def close(self) -> None:
        """Clean up resources and connections"""
        await self.connection_pool.cleanup_pools()
        await self.memory_manager.force_cleanup()

        logger.info("PerformanceOptimizationService closed successfully")
