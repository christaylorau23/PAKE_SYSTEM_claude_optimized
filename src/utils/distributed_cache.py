#!/usr/bin/env python3
"""PAKE+ Distributed Caching with Redis Cluster
High-performance, fault-tolerant caching layer with intelligent failover
"""

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

# Import secure serialization
from .secure_serialization import SerializationFormat, serialize

try:
    import redis.asyncio as redis
    from redis.asyncio.cluster import RedisCluster
    from redis.exceptions import ConnectionError, RedisError, TimeoutError
except ImportError:
    raise ImportError(
        "Please install redis[asyncio]: pip install 'redis[asyncio]>=5.0.0'",
    )

from utils.error_handling import (
    ErrorCategory,
    ErrorSeverity,
    PAKEException,
    RetryPolicy,
    with_error_handling,
    with_retry,
)
from utils.logger import get_logger
from utils.metrics import MetricsStore

logger = get_logger(service_name="pake-distributed-cache")
metrics = MetricsStore(service_name="pake-distributed-cache")

T = TypeVar("T")


class CacheBackend(Enum):
    """Cache backend types"""

    REDIS_SINGLE = "redis_single"
    REDIS_CLUSTER = "redis_cluster"
    REDIS_SENTINEL = "redis_sentinel"


# SerializationFormat is now imported from secure_serialization
# Removed PICKLE format for security


@dataclass
class CacheConfig:
    """Configuration for distributed cache"""

    # Connection settings
    host: str = "localhost"
    port: int = 6379
    REDACTED_SECRET: str | None = None
    cluster_nodes: list[dict[str, str | int]] | None = None
    sentinel_nodes: list[dict[str, str | int]] | None = None

    # Cache settings
    default_ttl: int = 3600  # 1 hour default TTL
    max_connections: int = 20
    connection_timeout: float = 5.0
    socket_timeout: float = 5.0

    # Retry and circuit breaker settings
    max_retries: int = 3
    retry_delay: float = 0.1
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0

    # Serialization
    default_serialization: SerializationFormat = SerializationFormat.JSON
    compression_enabled: bool = True
    compression_threshold: int = 1024  # Compress if larger than 1KB

    # Performance settings
    pipeline_batch_size: int = 100
    enable_key_prefix: bool = True
    key_prefix: str = "pake:"

    # Monitoring
    enable_metrics: bool = True
    log_slow_operations: bool = True
    slow_operation_threshold: float = 0.1  # 100ms


class CacheError(PAKEException):
    """Cache-specific errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SYSTEM, **kwargs)


@dataclass
class CacheStats:
    """Cache statistics"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_operations: int = 0
    average_response_time: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_gets = self.hits + self.misses
        return self.hits / total_gets if total_gets > 0 else 0.0


class DistributedCache:
    """High-performance distributed cache with Redis Cluster support"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.logger = get_logger(service_name="pake-distributed-cache")
        self.metrics = (
            MetricsStore(service_name="pake-distributed-cache")
            if config.enable_metrics
            else None
        )
        self.stats = CacheStats()

        self._client: redis.Redis | RedisCluster | None = None
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0
        self._is_circuit_open = False

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    @with_error_handling("cache_connect", severity=ErrorSeverity.HIGH)
    async def connect(self) -> None:
        """Connect to Redis cache backend"""
        try:
            if self.config.cluster_nodes:
                # Redis Cluster mode
                self._client = RedisCluster(
                    startup_nodes=self.config.cluster_nodes,
                    REDACTED_SECRET=self.config.REDACTED_SECRET,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.connection_timeout,
                    decode_responses=False,  # We handle encoding ourselves
                    skip_full_coverage_check=True,
                    health_check_interval=30,
                )
            else:
                # Single Redis instance
                self._client = redis.Redis(
                    host=self.config.host,
                    port=self.config.port,
                    REDACTED_SECRET=self.config.REDACTED_SECRET,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.connection_timeout,
                    decode_responses=False,
                )

            # Test connection
            await self._client.ping()
            self.logger.info("Successfully connected to Redis cache")

        except Exception as e:
            raise CacheError(
                f"Failed to connect to Redis: {str(e)}",
                original_exception=e,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis cache backend"""
        if self._client:
            try:
                await self._client.aclose()
                self.logger.info("Disconnected from Redis cache")
            except Exception as e:
                self.logger.warning(f"Error during Redis disconnect: {str(e)}")

    def _format_key(self, key: str) -> str:
        """Format cache key with optional prefix"""
        if self.config.enable_key_prefix:
            return f"{self.config.key_prefix}{key}"
        return key

    def _serialize_value(self, value: Any, format: SerializationFormat = None) -> bytes:
        """Serialize value for cache storage using secure serialization"""
        format = format or self.config.default_serialization

        try:
            if format == SerializationFormat.JSON:
                serialized = json.dumps(value).encode("utf-8")
            elif format == SerializationFormat.MSGPACK:
                serialized = serialize(value, SerializationFormat.MSGPACK)
            elif format == SerializationFormat.CBOR:
                serialized = serialize(value, SerializationFormat.CBOR)
            elif format == SerializationFormat.STRING:
                serialized = str(value).encode("utf-8")
            elif format == SerializationFormat.BINARY:
                serialized = value if isinstance(value, bytes) else bytes(value)
            else:
                raise ValueError(f"Unsupported serialization format: {format}")

            # Apply compression if enabled and value is large enough
            if (
                self.config.compression_enabled
                and len(serialized) > self.config.compression_threshold
            ):
                compressed = gzip.compress(serialized)
                # Only use compression if it actually reduces size
                if len(compressed) < len(serialized):
                    return b"GZIP:" + compressed

            return b"RAW:" + serialized

        except Exception as e:
            raise CacheError(
                f"Failed to serialize value: {str(e)}",
                original_exception=e,
            )

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from cache storage"""
        try:
            if data.startswith(b"GZIP:"):
                import gzip

                decompressed = gzip.decompress(data[5:])
                return json.loads(decompressed.decode("utf-8"))
            if data.startswith(b"RAW:"):
                raw_data = data[4:]
                # Try JSON first (most common)
                try:
                    return json.loads(raw_data.decode("utf-8"))
                except json.JSONDecodeError:
                    # Try secure deserialization
                    try:
                        from .secure_serialization import deserialize
                        return deserialize(raw_data)
                    except Exception:
                        # Return as string as last resort
                        return raw_data.decode("utf-8")
            else:
                # Legacy format without prefix
                return json.loads(data.decode("utf-8"))

        except Exception as e:
            raise CacheError(
                f"Failed to deserialize value: {str(e)}",
                original_exception=e,
            )

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker is open"""
        if self._is_circuit_open:
            if (
                time.time() - self._circuit_breaker_last_failure
                > self.config.circuit_breaker_timeout
            ):
                # Reset circuit breaker
                self._is_circuit_open = False
                self._circuit_breaker_failures = 0
                self.logger.info("Circuit breaker reset")
            else:
                raise CacheError(
                    "Circuit breaker is open - cache operations are temporarily disabled",
                )

    def _handle_operation_failure(self) -> None:
        """Handle operation failure for circuit breaker"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()

        if self._circuit_breaker_failures >= self.config.circuit_breaker_threshold:
            self._is_circuit_open = True
            self.logger.warning(
                f"Circuit breaker opened after {self._circuit_breaker_failures} failures",
            )

    async def _execute_operation(self, operation_name: str, operation: Callable) -> Any:
        """Execute cache operation with error handling and metrics"""
        start_time = time.time()

        try:
            self._check_circuit_breaker()

            if not self._client:
                await self.connect()

            result = await operation()

            # Record success metrics
            duration = time.time() - start_time
            self.stats.total_operations += 1

            if self.metrics:
                self.metrics.record_histogram(
                    "cache_operation_duration",
                    duration,
                    labels={"operation": operation_name, "status": "success"},
                )

            if (
                self.config.log_slow_operations
                and duration > self.config.slow_operation_threshold
            ):
                self.logger.warning(
                    f"Slow cache operation: {operation_name} took {duration:.3f}s",
                )

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.stats.errors += 1
            self._handle_operation_failure()

            if self.metrics:
                self.metrics.record_histogram(
                    "cache_operation_duration",
                    duration,
                    labels={"operation": operation_name, "status": "error"},
                )
                self.metrics.increment_counter(
                    "cache_errors",
                    labels={"operation": operation_name, "error": type(e).__name__},
                )

            raise CacheError(
                f"Cache operation {operation_name} failed: {str(e)}",
                original_exception=e,
            )

    @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""

        async def operation():
            formatted_key = self._format_key(key)
            data = await self._client.get(formatted_key)

            if data is None:
                self.stats.misses += 1
                if self.metrics:
                    self.metrics.increment_counter(
                        "cache_misses",
                        labels={"key_prefix": key.split(":")[0]},
                    )
                return default

            self.stats.hits += 1
            if self.metrics:
                self.metrics.increment_counter(
                    "cache_hits",
                    labels={"key_prefix": key.split(":")[0]},
                )

            return self._deserialize_value(data)

        return await self._execute_operation("get", operation)

    @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache"""

        async def operation():
            formatted_key = self._format_key(key)
            serialized_value = self._serialize_value(value)
            ttl_value = ttl or self.config.default_ttl

            result = await self._client.setex(
                formatted_key,
                ttl_value,
                serialized_value,
            )
            self.stats.sets += 1

            if self.metrics:
                self.metrics.increment_counter(
                    "cache_sets",
                    labels={"key_prefix": key.split(":")[0]},
                )
                self.metrics.record_histogram(
                    "cache_value_size",
                    len(serialized_value),
                    labels={"key_prefix": key.split(":")[0]},
                )

            return bool(result)

        return await self._execute_operation("set", operation)

    @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""

        async def operation():
            formatted_key = self._format_key(key)
            result = await self._client.delete(formatted_key)
            self.stats.deletes += 1

            if self.metrics:
                self.metrics.increment_counter(
                    "cache_deletes",
                    labels={"key_prefix": key.split(":")[0]},
                )

            return bool(result)

        return await self._execute_operation("delete", operation)

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from cache"""

        async def operation():
            formatted_keys = [self._format_key(key) for key in keys]
            values = await self._client.mget(formatted_keys)

            result = {}
            for i, (original_key, value) in enumerate(zip(keys, values, strict=False)):
                if value is not None:
                    result[original_key] = self._deserialize_value(value)
                    self.stats.hits += 1
                else:
                    self.stats.misses += 1

            if self.metrics:
                self.metrics.increment_counter("cache_hits", self.stats.hits)
                self.metrics.increment_counter("cache_misses", self.stats.misses)

            return result

        return await self._execute_operation("get_many", operation)

    async def set_many(self, data: dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple values in cache"""

        async def operation():
            ttl_value = ttl or self.config.default_ttl

            # Use pipeline for better performance
            pipeline = self._client.pipeline()

            for key, value in data.items():
                formatted_key = self._format_key(key)
                serialized_value = self._serialize_value(value)
                pipeline.setex(formatted_key, ttl_value, serialized_value)

            results = await pipeline.execute()
            self.stats.sets += len(data)

            if self.metrics:
                self.metrics.increment_counter("cache_sets", len(data))

            return all(results)

        return await self._execute_operation("set_many", operation)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""

        async def operation():
            formatted_key = self._format_key(key)
            result = await self._client.exists(formatted_key)
            return bool(result)

        return await self._execute_operation("exists", operation)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""

        async def operation():
            formatted_key = self._format_key(key)
            result = await self._client.expire(formatted_key, ttl)
            return bool(result)

        return await self._execute_operation("expire", operation)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value"""

        async def operation():
            formatted_key = self._format_key(key)
            result = await self._client.incrby(formatted_key, amount)
            return int(result)

        return await self._execute_operation("increment", operation)

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""

        async def operation():
            formatted_pattern = self._format_key(pattern)

            # Scan for keys to avoid blocking
            keys_to_delete = []
            async for key in self._client.scan_iter(match=formatted_pattern):
                keys_to_delete.append(key)

            if keys_to_delete:
                result = await self._client.delete(*keys_to_delete)
                self.stats.deletes += result
                return int(result)

            return 0

        return await self._execute_operation("clear_pattern", operation)

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_stats": {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "sets": self.stats.sets,
                "deletes": self.stats.deletes,
                "errors": self.stats.errors,
                "total_operations": self.stats.total_operations,
                "hit_rate": self.stats.hit_rate,
                "average_response_time": self.stats.average_response_time,
            },
            "circuit_breaker": {
                "failures": self._circuit_breaker_failures,
                "is_open": self._is_circuit_open,
                "last_failure": self._circuit_breaker_last_failure,
            },
            "connection_info": {
                "backend": "cluster" if self.config.cluster_nodes else "single",
                "connected": self._client is not None,
            },
        }


class CacheManager:
    """High-level cache manager with multiple cache instances"""

    def __init__(self):
        self.caches: dict[str, DistributedCache] = {}
        self.logger = get_logger(service_name="cache-manager")

    def add_cache(self, name: str, config: CacheConfig) -> None:
        """Add a cache instance"""
        self.caches[name] = DistributedCache(config)

    async def get_cache(self, name: str = "default") -> DistributedCache:
        """Get cache instance by name"""
        if name not in self.caches:
            raise CacheError(f"Cache '{name}' not found")

        cache = self.caches[name]
        if cache._client is None:
            await cache.connect()

        return cache

    async def initialize_all(self) -> None:
        """Initialize all cache connections"""
        for name, cache in self.caches.items():
            try:
                await cache.connect()
                self.logger.info(f"Initialized cache: {name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize cache {name}: {str(e)}")

    async def shutdown_all(self) -> None:
        """Shutdown all cache connections"""
        for name, cache in self.caches.items():
            try:
                await cache.disconnect()
                self.logger.info(f"Shutdown cache: {name}")
            except Exception as e:
                self.logger.error(f"Error shutting down cache {name}: {str(e)}")


# Decorators for automatic caching
def cached(cache_key: str, ttl: int | None = None, cache_name: str = "default"):
    """Decorator for automatic function result caching"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            cache = await cache_manager.get_cache(cache_name)

            # Generate cache key
            key_data = {
                "function": f"{func.__module__}.{func.__name__}",
                "args": str(args),
                "kwargs": str(sorted(kwargs.items())),
            }
            key_hash = hashlib.sha256(json.dumps(key_data).encode()).hexdigest()
            final_key = f"{cache_key}:{key_hash}"

            # Try to get from cache
            cached_result = await cache.get(final_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(final_key, result, ttl)

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Example configuration for PAKE system
def create_pake_cache_config(redis_url: str = None) -> CacheConfig:
    """Create optimized cache configuration for PAKE system"""
    import os

    # Parse Redis URL or use defaults
    if redis_url:
        # Simple URL parsing (production should use more robust parsing)
        if redis_url.startswith("redis://"):
            parts = redis_url.replace("redis://", "").split("@")
            if len(parts) == 2:
                auth, host_port = parts
                REDACTED_SECRET = auth.split(":")[1] if ":" in auth else None
                host_port_parts = host_port.split(":")
                host = host_port_parts[0]
                port = int(host_port_parts[1]) if len(host_port_parts) > 1 else 6379
            else:
                host_port_parts = parts[0].split(":")
                host = host_port_parts[0]
                port = int(host_port_parts[1]) if len(host_port_parts) > 1 else 6379
                REDACTED_SECRET = None
        else:
            host = "localhost"
            port = 6379
            REDACTED_SECRET = None
    else:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        REDACTED_SECRET = os.getenv("REDIS_PASSWORD")

    return CacheConfig(
        host=host,
        port=port,
        REDACTED_SECRET=REDACTED_SECRET,
        default_ttl=3600,  # 1 hour
        max_connections=20,
        connection_timeout=5.0,
        socket_timeout=5.0,
        max_retries=3,
        retry_delay=0.1,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60.0,
        compression_enabled=True,
        compression_threshold=1024,
        enable_metrics=True,
        log_slow_operations=True,
        slow_operation_threshold=0.1,
        key_prefix="pake:",
    )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def example_usage():
        # Create cache configuration
        config = create_pake_cache_config()

        # Use cache with context manager
        async with DistributedCache(config) as cache:
            # Basic operations
            await cache.set("test_key", {"message": "Hello, PAKE!"}, ttl=300)
            result = await cache.get("test_key")
            print(f"Cached result: {result}")

            # Batch operations
            data = {
                "key1": "value1",
                "key2": {"nested": "data"},
                "key3": [1, 2, 3, 4, 5],
            }
            await cache.set_many(data, ttl=300)
            retrieved = await cache.get_many(["key1", "key2", "key3"])
            print(f"Batch retrieved: {retrieved}")

            # Statistics
            stats = await cache.get_stats()
            print(f"Cache stats: {json.dumps(stats, indent=2)}")

    asyncio.run(example_usage())
