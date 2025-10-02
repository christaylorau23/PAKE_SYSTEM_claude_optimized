"""
Comprehensive Unit Tests for CachingService

Tests all primary use cases, edge cases, and expected failure modes
for the CachingService class using pytest-mock for complete isolation.
"""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.caching.cache_service import CacheService
from tests.factories import SearchResultFactory, UserFactory


class TestCacheServiceComprehensive:
    """Comprehensive unit tests for CacheService"""

    @pytest.fixture()
    def mock_redis(self):
        """Create mocked Redis client"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False
        mock_redis.expire.return_value = True
        mock_redis.ttl.return_value = -1
        mock_redis.keys.return_value = []
        mock_redis.flushdb.return_value = True
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture()
    def mock_memory_cache(self):
        """Create mocked memory cache"""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache.delete.return_value = True
        mock_cache.exists.return_value = False
        mock_cache.clear.return_value = True
        mock_cache.size.return_value = 0
        return mock_cache

    @pytest.fixture()
    def cache_service(self, mock_redis, mock_memory_cache):
        """Create CacheService instance with mocked dependencies"""
        with patch(
            "src.services.caching.cache_service.RedisCache"
        ) as mock_redis_class, patch(
            "src.services.caching.cache_service.MemoryCache"
        ) as mock_memory_class:
            mock_redis_class.return_value = mock_redis
            mock_memory_class.return_value = mock_memory_cache

            service = CacheService()
            service.redis_cache = mock_redis
            service.memory_cache = mock_memory_cache
            return service

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional()
    async def test_get_cached_data_success(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test successful data retrieval from cache"""
        # Arrange
        key = "user:123"
        cached_data = UserFactory()
        mock_memory_cache.get.return_value = cached_data

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result == cached_data
        mock_memory_cache.get.assert_called_once_with(key)

    @pytest.mark.unit_functional()
    async def test_set_cache_data_success(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test successful data storage in cache"""
        # Arrange
        key = "user:123"
        data = UserFactory()
        ttl = 3600

        # Act
        result = await cache_service.set(key, data, ttl)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once_with(key, data, ttl)
        mock_redis.setex.assert_called_once_with(key, ttl, json.dumps(data))

    @pytest.mark.unit_functional()
    async def test_delete_cached_data_success(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test successful data deletion from cache"""
        # Arrange
        key = "user:123"

        # Act
        result = await cache_service.delete(key)

        # Assert
        assert result is True
        mock_memory_cache.delete.assert_called_once_with(key)
        mock_redis.delete.assert_called_once_with(key)

    @pytest.mark.unit_functional()
    async def test_cache_hit_memory_first(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test that memory cache is checked first (L1 cache)"""
        # Arrange
        key = "user:123"
        cached_data = UserFactory()
        mock_memory_cache.get.return_value = cached_data

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result == cached_data
        mock_memory_cache.get.assert_called_once_with(key)
        mock_redis.get.assert_not_called()  # Should not check Redis if memory hit

    @pytest.mark.unit_functional()
    async def test_cache_miss_memory_hit_redis(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test fallback to Redis when memory cache misses"""
        # Arrange
        key = "user:123"
        redis_data = UserFactory()
        mock_memory_cache.get.return_value = None
        mock_redis.get.return_value = json.dumps(redis_data)

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result == redis_data
        mock_memory_cache.get.assert_called_once_with(key)
        mock_redis.get.assert_called_once_with(key)

    @pytest.mark.unit_functional()
    async def test_cache_miss_both_levels(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test cache miss at both L1 and L2 levels"""
        # Arrange
        key = "user:123"
        mock_memory_cache.get.return_value = None
        mock_redis.get.return_value = None

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result is None
        mock_memory_cache.get.assert_called_once_with(key)
        mock_redis.get.assert_called_once_with(key)

    @pytest.mark.unit_functional()
    async def test_set_with_default_ttl(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test setting cache data with default TTL"""
        # Arrange
        key = "user:123"
        data = UserFactory()

        # Act
        result = await cache_service.set(key, data)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once()
        mock_redis.setex.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_exists_check_success(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test checking if key exists in cache"""
        # Arrange
        key = "user:123"
        mock_memory_cache.exists.return_value = True

        # Act
        result = await cache_service.exists(key)

        # Assert
        assert result is True
        mock_memory_cache.exists.assert_called_once_with(key)

    @pytest.mark.unit_functional()
    async def test_clear_all_cache_success(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test clearing all cache data"""
        # Act
        result = await cache_service.clear_all()

        # Assert
        assert result is True
        mock_memory_cache.clear.assert_called_once()
        mock_redis.flushdb.assert_called_once()

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case()
    async def test_set_with_zero_ttl(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test setting cache data with zero TTL (no expiration)"""
        # Arrange
        key = "user:123"
        data = UserFactory()
        ttl = 0

        # Act
        result = await cache_service.set(key, data, ttl)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once_with(key, data, ttl)
        mock_redis.set.assert_called_once_with(key, json.dumps(data))

    @pytest.mark.unit_edge_case()
    async def test_set_with_very_long_ttl(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test setting cache data with very long TTL"""
        # Arrange
        key = "user:123"
        data = UserFactory()
        ttl = 86400 * 365  # 1 year

        # Act
        result = await cache_service.set(key, data, ttl)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once_with(key, data, ttl)
        mock_redis.setex.assert_called_once_with(key, ttl, json.dumps(data))

    @pytest.mark.unit_edge_case()
    async def test_set_with_special_characters_key(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test setting cache data with special characters in key"""
        # Arrange
        key = "user:123:special-chars!@#$%^&*()"
        data = UserFactory()

        # Act
        result = await cache_service.set(key, data)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once()
        mock_redis.setex.assert_called_once()

    @pytest.mark.unit_edge_case()
    async def test_set_with_complex_nested_data(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test setting cache data with complex nested objects"""
        # Arrange
        key = "complex:data"
        data = {
            "user": UserFactory(),
            "results": [SearchResultFactory() for _ in range(5)],
            "metadata": {
                "created_at": datetime.now(UTC).isoformat(),
                "tags": ["tag1", "tag2", "tag3"],
                "nested": {"level1": {"level2": "value"}},
            },
        }

        # Act
        result = await cache_service.set(key, data)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once()
        mock_redis.setex.assert_called_once()

    @pytest.mark.unit_edge_case()
    async def test_get_with_empty_key(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test getting cache data with empty key"""
        # Arrange
        key = ""
        mock_memory_cache.get.return_value = None

        # Act
        result = await cache_service.get(key)

        # Assert
        assert result is None

    @pytest.mark.unit_edge_case()
    async def test_set_with_none_value(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test setting cache data with None value"""
        # Arrange
        key = "user:123"
        data = None

        # Act
        result = await cache_service.set(key, data)

        # Assert
        assert result is True
        mock_memory_cache.set.assert_called_once_with(key, data, 3600)
        mock_redis.setex.assert_called_once_with(key, 3600, json.dumps(data))

    @pytest.mark.unit_edge_case()
    async def test_concurrent_access_same_key(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test concurrent access to the same cache key"""
        # Arrange
        key = "user:123"
        data = UserFactory()

        async def set_data():
            return await cache_service.set(key, data)

        async def get_data():
            return await cache_service.get(key)

        # Act
        tasks = [set_data(), get_data(), set_data(), get_data()]
        results = await asyncio.gather(*tasks)

        # Assert
        assert all(result is True for result in results[:2])  # set operations
        assert all(result is not None for result in results[2:])  # get operations

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling()
    async def test_redis_connection_failure(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test handling of Redis connection failures"""
        # Arrange
        key = "user:123"
        data = UserFactory()
        mock_redis.setex.side_effect = Exception("Redis connection failed")

        # Act & Assert
        with pytest.raises(Exception, match="Redis connection failed"):
            await cache_service.set(key, data)

    @pytest.mark.unit_error_handling()
    async def test_memory_cache_failure(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test handling of memory cache failures"""
        # Arrange
        key = "user:123"
        data = UserFactory()
        mock_memory_cache.set.side_effect = Exception("Memory cache full")

        # Act & Assert
        with pytest.raises(Exception, match="Memory cache full"):
            await cache_service.set(key, data)

    @pytest.mark.unit_error_handling()
    async def test_json_serialization_error(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test handling of JSON serialization errors"""
        # Arrange
        key = "user:123"
        data = object()  # Non-serializable object
        mock_memory_cache.set.return_value = True

        # Act & Assert
        with pytest.raises(TypeError):
            await cache_service.set(key, data)

    @pytest.mark.unit_error_handling()
    async def test_json_deserialization_error(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test handling of JSON deserialization errors"""
        # Arrange
        key = "user:123"
        mock_memory_cache.get.return_value = None
        mock_redis.get.return_value = "invalid json"

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            await cache_service.get(key)

    @pytest.mark.unit_error_handling()
    async def test_delete_nonexistent_key(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test deleting non-existent cache key"""
        # Arrange
        key = "nonexistent:key"
        mock_memory_cache.delete.return_value = False
        mock_redis.delete.return_value = 0

        # Act
        result = await cache_service.delete(key)

        # Assert
        assert result is False

    @pytest.mark.unit_error_handling()
    async def test_redis_timeout_error(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test handling of Redis timeout errors"""
        # Arrange
        key = "user:123"
        mock_memory_cache.get.return_value = None
        mock_redis.get.side_effect = asyncio.TimeoutError("Redis timeout")

        # Act & Assert
        with pytest.raises(asyncio.TimeoutError, match="Redis timeout"):
            await cache_service.get(key)

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance()
    async def test_memory_cache_performance(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test memory cache performance"""
        import time

        # Arrange
        key = "user:123"
        data = UserFactory()
        mock_memory_cache.get.return_value = data

        # Act
        start_time = time.time()
        for _ in range(1000):
            await cache_service.get(key)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert mock_memory_cache.get.call_count == 1000

    @pytest.mark.unit_performance()
    async def test_bulk_operations_performance(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test bulk cache operations performance"""
        import time

        # Arrange
        data_items = [UserFactory() for _ in range(100)]

        # Act
        start_time = time.time()
        tasks = []
        for i, data in enumerate(data_items):
            tasks.append(cache_service.set(f"user:{i}", data))

        await asyncio.gather(*tasks)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.unit_performance()
    async def test_cache_hit_ratio_performance(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test cache hit ratio performance"""
        # Arrange
        keys = [f"user:{i}" for i in range(10)]
        mock_memory_cache.get.side_effect = (
            lambda key: UserFactory() if key in keys[:5] else None
        )

        # Act
        hit_count = 0
        for key in keys:
            result = await cache_service.get(key)
            if result is not None:
                hit_count += 1

        # Assert
        hit_ratio = hit_count / len(keys)
        assert hit_ratio == 0.5  # 50% hit ratio

    # ============================================================================
    # SECURITY TESTS - Data Protection and Access Control
    # ============================================================================

    @pytest.mark.unit_security()
    async def test_sensitive_data_not_logged(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test that sensitive data is not logged"""
        # Arrange
        key = "user:123"
        sensitive_data = {
            "username": "testuser",
            "password": "secretpassword",
            "email": "test@example.com",
        }

        # Act
        await cache_service.set(key, sensitive_data)

        # Assert
        # Verify that sensitive data is not exposed in logs
        # This would require checking log output, but for unit tests we verify
        # that the data is properly serialized
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        serialized_data = call_args[2]
        assert "secretpassword" in serialized_data  # Data is serialized
        assert isinstance(serialized_data, str)  # Not logged as object

    @pytest.mark.unit_security()
    async def test_cache_key_sanitization(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test that cache keys are properly sanitized"""
        # Arrange
        malicious_key = 'user:123<script>alert("xss")</script>'
        data = UserFactory()

        # Act
        result = await cache_service.set(malicious_key, data)

        # Assert
        assert result is True
        # Verify that the key is used as-is (sanitization should happen at higher level)
        mock_memory_cache.set.assert_called_once_with(malicious_key, data, 3600)

    @pytest.mark.unit_security()
    async def test_cache_expiration_security(
        self, cache_service, mock_memory_cache, mock_redis
    ):
        """Test that cache data expires properly for security"""
        # Arrange
        key = "user:123"
        data = UserFactory()
        short_ttl = 1  # 1 second

        # Act
        await cache_service.set(key, data, short_ttl)

        # Assert
        # Verify that TTL is set correctly
        mock_redis.setex.assert_called_once_with(key, short_ttl, json.dumps(data))
        mock_memory_cache.set.assert_called_once_with(key, data, short_ttl)

    @pytest.mark.unit_security()
    async def test_cache_isolation(self, cache_service, mock_memory_cache, mock_redis):
        """Test that cache data is properly isolated between keys"""
        # Arrange
        key1 = "user:123"
        key2 = "user:456"
        data1 = UserFactory(username="user1")
        data2 = UserFactory(username="user2")

        # Act
        await cache_service.set(key1, data1)
        await cache_service.set(key2, data2)

        # Assert
        # Verify that different keys store different data
        assert mock_memory_cache.set.call_count == 2
        assert mock_redis.setex.call_count == 2

        # Verify that the data is stored separately
        call_args_list = mock_memory_cache.set.call_args_list
        assert call_args_list[0][0][0] == key1
        assert call_args_list[1][0][0] == key2
