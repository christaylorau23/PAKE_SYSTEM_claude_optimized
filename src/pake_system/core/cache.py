"""
Enterprise caching system for PAKE System
Multi-level caching with optional Redis integration
"""

import asyncio
import json
import pickle
from typing import Any, Optional, Union, Dict
from datetime import datetime, timedelta

# Optional Redis import
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None


class CacheService:
    """Enterprise caching service with optional Redis backend."""
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._redis: Optional[Redis] = None
        self._local_cache: Dict[str, Any] = {}
    
    async def connect(self) -> None:
        """Connect to Redis if available."""
        if REDIS_AVAILABLE and self.redis_url and not self._redis:
            try:
                self._redis = redis.from_url(self.redis_url)
                await self._redis.ping()
            except Exception:
                self._redis = None
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            # Try local cache first
            if key in self._local_cache:
                return self._local_cache[key]
            
            # Try Redis cache if available
            if self._redis:
                value = await self._redis.get(key)
                if value:
                    try:
                        # Try to deserialize as JSON first
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        # Fall back to pickle
                        return pickle.loads(value)
            
            return None
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.default_ttl
            
            # Store in local cache
            self._local_cache[key] = value
            
            # Store in Redis cache if available
            if self._redis:
                try:
                    # Try to serialize as JSON first
                    serialized = json.dumps(value)
                except (TypeError, ValueError):
                    # Fall back to pickle
                    serialized = pickle.dumps(value)
                
                await self._redis.setex(key, ttl, serialized)
            
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            # Remove from local cache
            self._local_cache.pop(key, None)
            
            # Remove from Redis cache if available
            if self._redis:
                await self._redis.delete(key)
            
            return True
        except Exception:
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            # Clear local cache
            self._local_cache.clear()
            
            # Clear Redis cache if available
            if self._redis:
                await self._redis.flushdb()
            
            return True
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            # Check local cache
            if key in self._local_cache:
                return True
            
            # Check Redis cache if available
            if self._redis:
                return await self._redis.exists(key) > 0
            
            return False
        except Exception:
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            stats = {
                'local_cache_size': len(self._local_cache),
                'redis_available': REDIS_AVAILABLE,
                'redis_connected': self._redis is not None
            }
            
            if self._redis:
                info = await self._redis.info()
                stats.update({
                    'redis_memory_used': info.get('used_memory_human', 'N/A'),
                    'redis_keys': info.get('db0', {}).get('keys', 0),
                    'redis_hits': info.get('keyspace_hits', 0),
                    'redis_misses': info.get('keyspace_misses', 0)
                })
            
            return stats
        except Exception:
            return {'error': 'Failed to get cache stats'}


# Global cache instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service
    if not _cache_service:
        from .config import get_settings
        settings = get_settings()
        _cache_service = CacheService(settings.REDIS_URL, settings.CACHE_TTL)
        await _cache_service.connect()
    return _cache_service


async def cache_key(key: str, ttl: Optional[int] = None):
    """Decorator for caching function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = await get_cache_service()
            
            # Create cache key from function name and arguments
            cache_key_str = f"{func.__name__}:{key}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key_str, result, ttl)
            
            return result
        return wrapper
    return decorator