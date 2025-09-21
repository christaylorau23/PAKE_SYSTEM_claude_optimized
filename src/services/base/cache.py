"""
Enterprise Caching Service
Task T046-T049 - Phase 18 Production System Integration

Multi-level caching with Redis for enterprise performance optimization.
Implements cache-aside, write-through, and cache prefetching patterns.
"""

import os
import json
import asyncio
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import logging

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
        self.retry_on_timeout = True
        self.socket_keepalive = True
        self.socket_keepalive_options = {}
        
        # Cache TTL defaults
        self.default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5 minutes
        self.short_ttl = int(os.getenv("CACHE_SHORT_TTL", "60"))      # 1 minute
        self.long_ttl = int(os.getenv("CACHE_LONG_TTL", "3600"))      # 1 hour


class CacheService:
    """Enterprise Redis caching service"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[redis.Redis] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        if self._initialized:
            return
            
        try:
            self.pool = ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_keepalive=self.config.socket_keepalive,
                socket_keepalive_options=self.config.socket_keepalive_options
            )
            
            self.redis = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.redis.ping()
            self._initialized = True
            logger.info("Redis cache service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
        self._initialized = False
        logger.info("Redis cache service closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
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
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Set value in cache"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
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
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self._initialized:
            await self.initialize()
        
        try:
            values = await self.redis.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value.decode('utf-8') if isinstance(value, bytes) else value
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Serialize values
            serialized_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
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
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.redis.incrby(key, amount)
            return result
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
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
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}


class CachePatterns:
    """Enterprise caching patterns"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
    
    async def cache_aside(
        self, 
        key: str, 
        fetch_func, 
        ttl: Optional[int] = None,
        *args, 
        **kwargs
    ) -> Any:
        """
        Cache-aside pattern: Check cache first, fetch from source if miss
        
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
            value = await fetch_func(*args, **kwargs) if asyncio.iscoroutinefunction(fetch_func) else fetch_func(*args, **kwargs)
            
            # Store in cache
            await self.cache.set(key, value, ttl)
            return value
            
        except Exception as e:
            logger.error(f"Cache-aside fetch error for key {key}: {e}")
            raise
    
    async def write_through(
        self, 
        key: str, 
        value: Any, 
        write_func, 
        ttl: Optional[int] = None,
        *args, 
        **kwargs
    ) -> Any:
        """
        Write-through pattern: Write to cache and source simultaneously
        
        Args:
            key: Cache key
            value: Value to cache
            write_func: Function to write to source
            ttl: Time to live for cached data
            *args, **kwargs: Arguments to pass to write_func
        """
        try:
            # Write to source first
            result = await write_func(value, *args, **kwargs) if asyncio.iscoroutinefunction(write_func) else write_func(value, *args, **kwargs)
            
            # Then write to cache
            await self.cache.set(key, value, ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Write-through error for key {key}: {e}")
            raise
    
    async def cache_prefetch(self, keys_and_fetch_funcs: Dict[str, Any], ttl: Optional[int] = None):
        """
        Cache prefetch pattern: Proactively load data into cache
        
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
            logger.info(f"Cache prefetch completed for {len(keys_and_fetch_funcs)} keys")
        except Exception as e:
            logger.error(f"Cache prefetch error: {e}")


# Global cache service instance
cache_service = CacheService()
cache_patterns = CachePatterns(cache_service)
