"""
Comprehensive Unit Tests for RedisCacheService

Tests all primary use cases, edge cases, and expected failure modes
for the RedisCacheService class using pytest-mock for complete isolation.

Following Testing Pyramid: Unit Tests (70%) - Fast, isolated, comprehensive
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.services.caching.redis_cache_service import (
    CacheConfig,
    CacheEntry,
    CacheMetadata,
    RedisCacheService,
)


class TestRedisCacheServiceComprehensive:
    """Comprehensive unit tests for RedisCacheService"""

    @pytest.fixture
    def mock_redis(self) -> None:
        """Create mocked Redis connection"""
        return AsyncMock()

    @pytest.fixture
    def cache_config(self) -> None:
        """Create test cache configuration"""
        return CacheConfig(
            redis_url="redis://localhost:6379/0",
            default_ttl=3600,
            max_memory_cache_size=1000,
            enable_compression=True,
        )

    @pytest.fixture
    def cache_service(self) -> None:
        """Create RedisCacheService instance with mocked dependencies"""
        with patch(
            "src.services.caching.redis_cache_service.redis.asyncio.from_url"
        ) as mock_from_url:
            mock_from_url.return_value = mock_redis

            service = RedisCacheService(config=cache_config)
            service._redis = mock_redis  # Inject mock directly
            return service

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional
    async def test_initialize_success(self) -> None:
        """Test successful cache service initialization"""
        # Arrange
        self.mock_redis.ping.return_value = True

        # Act
        await self.cache_service.initialize()

        # Assert
        assert self.cache_service._redis is not None
        self.mock_redis.ping.assert_called_once()

    @pytest.mark.unit_functional
    async def test_set_and_get_success(self) -> None:
        """Test successful cache set and get operations"""
        # Arrange
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        ttl = 3600

        self.mock_redis.set.return_value = True
        self.mock_redis.get.return_value = b"serialized_data"

        with (
            patch(
                "src.services.caching.redis_cache_service.serialize"
            ) as mock_serialize,
            patch(
                "src.services.caching.redis_cache_service.deserialize"
            ) as mock_deserialize,
        ):
            mock_serialize.return_value = b"serialized_data"
            mock_deserialize.return_value = {
                "value": value,
                "metadata": {
                    "created_at": datetime.now(UTC).isoformat(),
                    "expires_at": (
                        datetime.now(UTC) + timedelta(seconds=ttl)
                    ).isoformat(),
                    "tags": [],
                    "access_count": 0,
                    "last_accessed": None,
                },
            }

            # Act
            await self.cache_service.set(key, value, ttl=ttl)
            result = await self.cache_service.get(key)

            # Assert
            assert result == value
            self.mock_redis.set.assert_called_once()
            self.mock_redis.get.assert_called_once()

    @pytest.mark.unit_functional
    async def test_get_from_memory_cache_success(self) -> None:
        """Test successful get from L1 memory cache"""
        # Arrange
        key = "memory_test_key"
        value = {"data": "memory_value"}

        # Manually add to memory cache
        metadata = CacheMetadata(
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            tags=[],
        )
        entry = CacheEntry(value, metadata)
        self.cache_service._memory_cache[key] = entry

        # Act
        result = await self.cache_service.get(key)

        # Assert
        assert result == value
        assert self.cache_service.stats["l1_hits"] == 1
        assert self.cache_service.stats["hits"] == 1

    @pytest.mark.unit_functional
    async def test_set_with_tags_success(self) -> None:
        """Test successful cache set with tags"""
        # Arrange
        key = "tagged_key"
        value = {"data": "tagged_value"}
        tags = ["tag1", "tag2"]

        self.mock_redis.set.return_value = True
        self.mock_redis.sadd.return_value = 1
        self.mock_redis.expire.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_data"

            # Act
            await self.cache_service.set(key, value, tags=tags)

            # Assert
            self.mock_redis.set.assert_called_once()
            assert self.mock_redis.sadd.call_count == 2  # One for each tag
            assert self.mock_redis.expire.call_count == 2  # One for each tag

    @pytest.mark.unit_functional
    async def test_delete_success(self) -> None:
        """Test successful cache delete operation"""
        # Arrange
        key = "delete_test_key"

        # Add to memory cache first
        metadata = CacheMetadata(
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            tags=[],
        )
        entry = CacheEntry({"data": "test"}, metadata)
        self.cache_service._memory_cache[key] = entry

        self.mock_redis.delete.return_value = 1

        # Act
        await self.cache_service.delete(key)

        # Assert
        assert key not in self.cache_service._memory_cache
        self.mock_redis.delete.assert_called_once_with(key)
        assert self.cache_service.stats["deletes"] == 1

    @pytest.mark.unit_functional
    async def test_invalidate_by_tag_success(self) -> None:
        """Test successful tag-based invalidation"""
        # Arrange
        tag = "test_tag"
        keys = ["key1", "key2", "key3"]

        self.mock_redis.smembers.return_value = {key.encode() for key in keys}
        self.mock_redis.delete.return_value = len(keys)

        # Act
        invalidated_count = await self.cache_service.invalidate_by_tag(tag)

        # Assert
        assert invalidated_count == len(keys)
        self.mock_redis.smembers.assert_called_once_with(f"tag:{tag}")
        assert self.mock_redis.delete.call_count == len(keys) + 1  # Keys + tag set

    @pytest.mark.unit_functional
    async def test_get_cache_stats_success(self) -> None:
        """Test successful cache statistics retrieval"""
        # Arrange
        self.cache_service.stats = {
            "hits": 10,
            "misses": 5,
            "sets": 8,
            "deletes": 2,
            "l1_hits": 7,
            "l2_hits": 3,
        }

        # Act
        stats = await self.cache_service.get_stats()

        # Assert
        assert stats == self.cache_service.stats
        assert stats["hits"] == 10
        assert stats["misses"] == 5

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case
    async def test_set_with_none_value(self) -> None:
        """Test cache set with None value"""
        # Arrange
        key = "none_key"
        value = None

        self.mock_redis.set.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_none"

            # Act
            await self.cache_service.set(key, value)

            # Assert
            self.mock_redis.set.assert_called_once()

    @pytest.mark.unit_edge_case
    async def test_set_with_empty_string_key(self) -> None:
        """Test cache set with empty string key"""
        # Arrange
        key = ""
        value = {"data": "test"}

        # Act & Assert
        with pytest.raises(ValueError, match="Cache key cannot be empty"):
            await self.cache_service.set(key, value)

    @pytest.mark.unit_edge_case
    async def test_get_with_default_value(self) -> None:
        """Test cache get with default value on miss"""
        # Arrange
        key = "nonexistent_key"
        default_value = {"default": "value"}

        self.mock_redis.get.return_value = None

        # Act
        result = await self.cache_service.get(key, default=default_value)

        # Assert
        assert result == default_value
        assert self.cache_service.stats["misses"] == 1

    @pytest.mark.unit_edge_case
    async def test_set_with_zero_ttl(self) -> None:
        """Test cache set with zero TTL"""
        # Arrange
        key = "zero_ttl_key"
        value = {"data": "test"}
        ttl = 0

        self.mock_redis.set.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_data"

            # Act
            await self.cache_service.set(key, value, ttl=ttl)

            # Assert
            self.mock_redis.set.assert_called_once()

    @pytest.mark.unit_edge_case
    async def test_memory_cache_size_limit(self) -> None:
        """Test memory cache size limit enforcement"""
        # Arrange
        self.cache_service.max_memory_cache_size = 2

        # Act - Add more items than the limit
        for i in range(5):
            key = f"key_{i}"
            value = {"data": f"value_{i}"}
            metadata = CacheMetadata(
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(seconds=3600),
                tags=[],
            )
            entry = CacheEntry(value, metadata)
            self.cache_service._add_to_memory_cache(key, entry)

        # Assert
        assert len(self.self.cache_service._memory_cache) <= self.self.cache_service.max_memory_cache_size

    @pytest.mark.unit_edge_case
    async def test_concurrent_set_operations(self) -> None:
        """Test concurrent set operations"""
        # Arrange
        self.mock_redis.set.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_data"

            # Act
            tasks = []
            for i in range(10):
                key = f"concurrent_key_{i}"
                value = {"data": f"value_{i}"}
                tasks.append(self.cache_service.set(key, value))

            await asyncio.gather(*tasks)

            # Assert
            assert self.mock_redis.set.call_count == 10

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling
    async def test_redis_connection_failure(self) -> None:
        """Test handling of Redis connection failures"""
        # Arrange
        self.cache_service._redis = None

        # Act
        result = await self.cache_service.get("test_key")

        # Assert
        assert result is None
        assert self.cache_service.stats["misses"] == 1

    @pytest.mark.unit_error_handling
    async def test_redis_set_failure(self) -> None:
        """Test handling of Redis set failures"""
        # Arrange
        key = "fail_key"
        value = {"data": "test"}

        self.mock_redis.set.side_effect = Exception("Redis connection failed")

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_data"

            # Act
            await self.cache_service.set(key, value)

            # Assert
            # Should not raise exception, but log warning
            assert key in self.cache_service._memory_cache  # Should still be in L1 cache

    @pytest.mark.unit_error_handling
    async def test_redis_get_failure(self) -> None:
        """Test handling of Redis get failures"""
        # Arrange
        key = "fail_get_key"

        self.mock_redis.get.side_effect = Exception("Redis connection failed")

        # Act
        result = await self.cache_service.get(key)

        # Assert
        assert result is None
        assert self.cache_service.stats["misses"] == 1

    @pytest.mark.unit_error_handling
    async def test_serialization_failure(self) -> None:
        """Test handling of serialization failures"""
        # Arrange
        key = "serialize_fail_key"
        value = {"data": "test"}

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.side_effect = Exception("Serialization failed")

            # Act & Assert
            with pytest.raises(Exception, match="Serialization failed"):
                await self.cache_service.set(key, value)

    @pytest.mark.unit_error_handling
    async def test_deserialization_failure(self) -> None:
        """Test handling of deserialization failures"""
        # Arrange
        key = "deserialize_fail_key"

        self.mock_redis.get.return_value = b"invalid_data"

        with patch(
            "src.services.caching.redis_cache_service.deserialize"
        ) as mock_deserialize:
            mock_deserialize.side_effect = Exception("Deserialization failed")

            # Act
            result = await self.cache_service.get(key)

            # Assert
            assert result is None
            assert self.cache_service.stats["misses"] == 1

    @pytest.mark.unit_error_handling
    async def test_redis_delete_failure(self) -> None:
        """Test handling of Redis delete failures"""
        # Arrange
        key = "delete_fail_key"

        self.mock_redis.delete.side_effect = Exception("Redis delete failed")

        # Act
        await self.cache_service.delete(key)

        # Assert
        # Should not raise exception, but log warning
        assert self.cache_service.stats["deletes"] == 1

    @pytest.mark.unit_error_handling
    async def test_invalid_cache_key_type(self) -> None:
        """Test handling of invalid cache key types"""
        # Arrange
        invalid_key = 123  # Should be string
        value = {"data": "test"}

        # Act & Assert
        with pytest.raises(TypeError):
            await self.cache_service.set(invalid_key, value)

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance
    async def test_memory_cache_performance(self) -> None:
        """Test memory cache performance"""
        import time

        # Arrange
        key = "perf_test_key"
        value = {"data": "performance_test"}

        metadata = CacheMetadata(
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            tags=[],
        )
        entry = CacheEntry(value, metadata)
        self.cache_service._memory_cache[key] = entry

        # Act
        start_time = time.time()
        for _ in range(1000):
            await self.cache_service.get(key)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert self.cache_service.stats["l1_hits"] == 1000

    @pytest.mark.unit_performance
    async def test_set_performance(self) -> None:
        """Test cache set performance"""
        import time

        # Arrange
        self.mock_redis.set.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_data"

            # Act
            start_time = time.time()
            for i in range(100):
                await self.cache_service.set(f"perf_key_{i}", {"data": f"value_{i}"})
            end_time = time.time()

            # Assert
            execution_time = end_time - start_time
            assert execution_time < 2.0  # Should complete within 2 seconds

    @pytest.mark.unit_performance
    async def test_memory_usage_with_large_values(self) -> None:
        """Test memory usage with large values"""
        # Arrange
        large_value = {"data": "x" * 10000}  # Large value

        metadata = CacheMetadata(
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            tags=[],
        )
        entry = CacheEntry(large_value, metadata)

        # Act
        self.cache_service._add_to_memory_cache("large_key", entry)

        # Assert
        assert "large_key" in self.cache_service._memory_cache
        retrieved_value = await self.cache_service.get("large_key")
        assert retrieved_value == large_value

    # ============================================================================
    # SECURITY TESTS - Authentication and Authorization
    # ============================================================================

    @pytest.mark.unit_security
    async def test_cache_key_injection_prevention(self) -> None:
        """Test prevention of cache key injection attacks"""
        # Arrange
        malicious_key = "../../etc/passwd"
        value = {"data": "test"}

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid cache key"):
            await self.cache_service.set(malicious_key, value)

    @pytest.mark.unit_security
    async def test_sensitive_data_handling(self) -> None:
        """Test handling of sensitive data"""
        # Arrange
        key = "sensitive_key"
        sensitive_value = {
            "password": "secret123",
            "api_key": "sk-1234567890",
            "user_data": {"email": "user@example.com"},
        }

        self.mock_redis.set.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_sensitive_data"

            # Act
            await self.cache_service.set(key, sensitive_value)

            # Assert
            # Verify that sensitive data is handled appropriately
            # (This would depend on specific security requirements)
            self.mock_redis.set.assert_called_once()

    @pytest.mark.unit_security
    async def test_cache_entry_access_tracking(self) -> None:
        """Test cache entry access tracking for security monitoring"""
        # Arrange
        key = "access_track_key"
        value = {"data": "test"}

        metadata = CacheMetadata(
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=3600),
            tags=[],
        )
        entry = CacheEntry(value, metadata)
        self.cache_service._memory_cache[key] = entry

        # Act
        await self.cache_service.get(key)
        await self.cache_service.get(key)
        await self.cache_service.get(key)

        # Assert
        assert entry.metadata.access_count == 3
        assert entry.metadata.last_accessed is not None

    @pytest.mark.unit_security
    async def test_tag_based_access_control(self) -> None:
        """Test tag-based access control"""
        # Arrange
        key = "restricted_key"
        value = {"data": "restricted"}
        tags = ["restricted", "admin_only"]

        self.mock_redis.set.return_value = True
        self.mock_redis.sadd.return_value = 1
        self.mock_redis.expire.return_value = True

        with patch(
            "src.services.caching.redis_cache_service.serialize"
        ) as mock_serialize:
            mock_serialize.return_value = b"serialized_data"

            # Act
            await self.cache_service.set(key, value, tags=tags)

            # Assert
            # Verify tags are properly set for access control
            assert self.mock_redis.sadd.call_count == 2  # One for each tag
            assert self.mock_redis.expire.call_count == 2  # One for each tag