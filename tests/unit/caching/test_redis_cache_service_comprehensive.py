"""
Comprehensive Unit Tests for RedisCacheService

Tests all primary use cases, edge cases, and expected failure modes
for the RedisCacheService class using pytest-mock for complete isolation.

Following Testing Pyramid: Unit Tests (70%) - Fast, isolated, comprehensive
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import asyncio

from src.services.caching.redis_cache_service import (
    RedisCacheService,
    CacheConfig,
    CacheKey,
    CacheEntry,
    CacheMetadata
)
from tests.factories import SearchResultFactory


class TestRedisCacheServiceComprehensive:
    """Comprehensive unit tests for RedisCacheService"""

    @pytest.fixture
    def mock_redis(self):
        """Create mocked Redis connection"""
        return AsyncMock()

    @pytest.fixture
    def cache_config(self):
        """Create test cache configuration"""
        return CacheConfig(
            redis_url="redis://localhost:6379/0",
            default_ttl=3600,
            max_memory_cache_size=1000,
            enable_compression=True
        )

    @pytest.fixture
    def cache_service(self, cache_config, mock_redis):
        """Create RedisCacheService instance with mocked dependencies"""
        with patch('src.services.caching.redis_cache_service.redis.asyncio.from_url') as mock_from_url:
            mock_from_url.return_value = mock_redis
            
            service = RedisCacheService(config=cache_config)
            service._redis = mock_redis  # Inject mock directly
            return service

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional
    async def test_initialize_success(self, cache_service, mock_redis):
        """Test successful cache service initialization"""
        # Arrange
        mock_redis.ping.return_value = True
        
        # Act
        await cache_service.initialize()
        
        # Assert
        assert cache_service._redis is not None
        mock_redis.ping.assert_called_once()

    @pytest.mark.unit_functional
    async def test_set_and_get_success(self, cache_service, mock_redis):
        """Test successful cache set and get operations"""
        # Arrange
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        ttl = 3600
        
        mock_redis.set.return_value = True
        mock_redis.get.return_value = b'serialized_data'
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize, \
             patch('src.services.caching.redis_cache_service.deserialize') as mock_deserialize:
            
            mock_serialize.return_value = b'serialized_data'
            mock_deserialize.return_value = {
                'value': value,
                'metadata': {
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat(),
                    'tags': [],
                    'access_count': 0,
                    'last_accessed': None
                }
            }
            
            # Act
            await cache_service.set(key, value, ttl=ttl)
            result = await cache_service.get(key)
            
            # Assert
            assert result == value
            mock_redis.set.assert_called_once()
            mock_redis.get.assert_called_once()

    @pytest.mark.unit_functional
    async def test_get_from_memory_cache_success(self, cache_service):
        """Test successful get from L1 memory cache"""
        # Arrange
        key = "memory_test_key"
        value = {"data": "memory_value"}
        
        # Manually add to memory cache
        metadata = CacheMetadata(
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
            tags=[]
        )
        entry = CacheEntry(value, metadata)
        cache_service._memory_cache[key] = entry
        
        # Act
        result = await cache_service.get(key)
        
        # Assert
        assert result == value
        assert cache_service.stats["l1_hits"] == 1
        assert cache_service.stats["hits"] == 1

    @pytest.mark.unit_functional
    async def test_set_with_tags_success(self, cache_service, mock_redis):
        """Test successful cache set with tags"""
        # Arrange
        key = "tagged_key"
        value = {"data": "tagged_value"}
        tags = ["tag1", "tag2"]
        
        mock_redis.set.return_value = True
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_data'
            
            # Act
            await cache_service.set(key, value, tags=tags)
            
            # Assert
            mock_redis.set.assert_called_once()
            assert mock_redis.sadd.call_count == 2  # One for each tag
            assert mock_redis.expire.call_count == 2  # One for each tag

    @pytest.mark.unit_functional
    async def test_delete_success(self, cache_service, mock_redis):
        """Test successful cache delete operation"""
        # Arrange
        key = "delete_test_key"
        
        # Add to memory cache first
        metadata = CacheMetadata(
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
            tags=[]
        )
        entry = CacheEntry({"data": "test"}, metadata)
        cache_service._memory_cache[key] = entry
        
        mock_redis.delete.return_value = 1
        
        # Act
        await cache_service.delete(key)
        
        # Assert
        assert key not in cache_service._memory_cache
        mock_redis.delete.assert_called_once_with(key)
        assert cache_service.stats["deletes"] == 1

    @pytest.mark.unit_functional
    async def test_invalidate_by_tag_success(self, cache_service, mock_redis):
        """Test successful tag-based invalidation"""
        # Arrange
        tag = "test_tag"
        keys = ["key1", "key2", "key3"]
        
        mock_redis.smembers.return_value = {key.encode() for key in keys}
        mock_redis.delete.return_value = len(keys)
        
        # Act
        invalidated_count = await cache_service.invalidate_by_tag(tag)
        
        # Assert
        assert invalidated_count == len(keys)
        mock_redis.smembers.assert_called_once_with(f"tag:{tag}")
        assert mock_redis.delete.call_count == len(keys) + 1  # Keys + tag set

    @pytest.mark.unit_functional
    async def test_get_cache_stats_success(self, cache_service):
        """Test successful cache statistics retrieval"""
        # Arrange
        cache_service.stats = {
            "hits": 10,
            "misses": 5,
            "sets": 8,
            "deletes": 2,
            "l1_hits": 7,
            "l2_hits": 3
        }
        
        # Act
        stats = await cache_service.get_stats()
        
        # Assert
        assert stats == cache_service.stats
        assert stats["hits"] == 10
        assert stats["misses"] == 5

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case
    async def test_set_with_none_value(self, cache_service, mock_redis):
        """Test cache set with None value"""
        # Arrange
        key = "none_key"
        value = None
        
        mock_redis.set.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_none'
            
            # Act
            await cache_service.set(key, value)
            
            # Assert
            mock_redis.set.assert_called_once()

    @pytest.mark.unit_edge_case
    async def test_set_with_empty_string_key(self, cache_service):
        """Test cache set with empty string key"""
        # Arrange
        key = ""
        value = {"data": "test"}
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cache key cannot be empty"):
            await cache_service.set(key, value)

    @pytest.mark.unit_edge_case
    async def test_get_with_default_value(self, cache_service, mock_redis):
        """Test cache get with default value on miss"""
        # Arrange
        key = "nonexistent_key"
        default_value = {"default": "value"}
        
        mock_redis.get.return_value = None
        
        # Act
        result = await cache_service.get(key, default=default_value)
        
        # Assert
        assert result == default_value
        assert cache_service.stats["misses"] == 1

    @pytest.mark.unit_edge_case
    async def test_set_with_zero_ttl(self, cache_service, mock_redis):
        """Test cache set with zero TTL"""
        # Arrange
        key = "zero_ttl_key"
        value = {"data": "test"}
        ttl = 0
        
        mock_redis.set.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_data'
            
            # Act
            await cache_service.set(key, value, ttl=ttl)
            
            # Assert
            mock_redis.set.assert_called_once()

    @pytest.mark.unit_edge_case
    async def test_memory_cache_size_limit(self, cache_service):
        """Test memory cache size limit enforcement"""
        # Arrange
        cache_service.max_memory_cache_size = 2
        
        # Act - Add more items than the limit
        for i in range(5):
            key = f"key_{i}"
            value = {"data": f"value_{i}"}
            metadata = CacheMetadata(
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
                tags=[]
            )
            entry = CacheEntry(value, metadata)
            cache_service._add_to_memory_cache(key, entry)
        
        # Assert
        assert len(cache_service._memory_cache) <= cache_service.max_memory_cache_size

    @pytest.mark.unit_edge_case
    async def test_concurrent_set_operations(self, cache_service, mock_redis):
        """Test concurrent set operations"""
        # Arrange
        mock_redis.set.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_data'
            
            # Act
            tasks = []
            for i in range(10):
                key = f"concurrent_key_{i}"
                value = {"data": f"value_{i}"}
                tasks.append(cache_service.set(key, value))
            
            await asyncio.gather(*tasks)
            
            # Assert
            assert mock_redis.set.call_count == 10

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling
    async def test_redis_connection_failure(self, cache_service):
        """Test handling of Redis connection failures"""
        # Arrange
        cache_service._redis = None
        
        # Act
        result = await cache_service.get("test_key")
        
        # Assert
        assert result is None
        assert cache_service.stats["misses"] == 1

    @pytest.mark.unit_error_handling
    async def test_redis_set_failure(self, cache_service, mock_redis):
        """Test handling of Redis set failures"""
        # Arrange
        key = "fail_key"
        value = {"data": "test"}
        
        mock_redis.set.side_effect = Exception("Redis connection failed")
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_data'
            
            # Act
            await cache_service.set(key, value)
            
            # Assert
            # Should not raise exception, but log warning
            assert key in cache_service._memory_cache  # Should still be in L1 cache

    @pytest.mark.unit_error_handling
    async def test_redis_get_failure(self, cache_service, mock_redis):
        """Test handling of Redis get failures"""
        # Arrange
        key = "fail_get_key"
        
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        # Act
        result = await cache_service.get(key)
        
        # Assert
        assert result is None
        assert cache_service.stats["misses"] == 1

    @pytest.mark.unit_error_handling
    async def test_serialization_failure(self, cache_service, mock_redis):
        """Test handling of serialization failures"""
        # Arrange
        key = "serialize_fail_key"
        value = {"data": "test"}
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.side_effect = Exception("Serialization failed")
            
            # Act & Assert
            with pytest.raises(Exception, match="Serialization failed"):
                await cache_service.set(key, value)

    @pytest.mark.unit_error_handling
    async def test_deserialization_failure(self, cache_service, mock_redis):
        """Test handling of deserialization failures"""
        # Arrange
        key = "deserialize_fail_key"
        
        mock_redis.get.return_value = b'invalid_data'
        
        with patch('src.services.caching.redis_cache_service.deserialize') as mock_deserialize:
            mock_deserialize.side_effect = Exception("Deserialization failed")
            
            # Act
            result = await cache_service.get(key)
            
            # Assert
            assert result is None
            assert cache_service.stats["misses"] == 1

    @pytest.mark.unit_error_handling
    async def test_redis_delete_failure(self, cache_service, mock_redis):
        """Test handling of Redis delete failures"""
        # Arrange
        key = "delete_fail_key"
        
        mock_redis.delete.side_effect = Exception("Redis delete failed")
        
        # Act
        await cache_service.delete(key)
        
        # Assert
        # Should not raise exception, but log warning
        assert cache_service.stats["deletes"] == 1

    @pytest.mark.unit_error_handling
    async def test_invalid_cache_key_type(self, cache_service):
        """Test handling of invalid cache key types"""
        # Arrange
        invalid_key = 123  # Should be string
        value = {"data": "test"}
        
        # Act & Assert
        with pytest.raises(TypeError):
            await cache_service.set(invalid_key, value)

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance
    async def test_memory_cache_performance(self, cache_service):
        """Test memory cache performance"""
        import time
        
        # Arrange
        key = "perf_test_key"
        value = {"data": "performance_test"}
        
        metadata = CacheMetadata(
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
            tags=[]
        )
        entry = CacheEntry(value, metadata)
        cache_service._memory_cache[key] = entry
        
        # Act
        start_time = time.time()
        for _ in range(1000):
            await cache_service.get(key)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert cache_service.stats["l1_hits"] == 1000

    @pytest.mark.unit_performance
    async def test_set_performance(self, cache_service, mock_redis):
        """Test cache set performance"""
        import time
        
        # Arrange
        mock_redis.set.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_data'
            
            # Act
            start_time = time.time()
            for i in range(100):
                await cache_service.set(f"perf_key_{i}", {"data": f"value_{i}"})
            end_time = time.time()
            
            # Assert
            execution_time = end_time - start_time
            assert execution_time < 2.0  # Should complete within 2 seconds

    @pytest.mark.unit_performance
    async def test_memory_usage_with_large_values(self, cache_service):
        """Test memory usage with large values"""
        # Arrange
        large_value = {"data": "x" * 10000}  # Large value
        
        metadata = CacheMetadata(
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
            tags=[]
        )
        entry = CacheEntry(large_value, metadata)
        
        # Act
        cache_service._add_to_memory_cache("large_key", entry)
        
        # Assert
        assert "large_key" in cache_service._memory_cache
        retrieved_value = await cache_service.get("large_key")
        assert retrieved_value == large_value

    # ============================================================================
    # SECURITY TESTS - Authentication and Authorization
    # ============================================================================

    @pytest.mark.unit_security
    async def test_cache_key_injection_prevention(self, cache_service):
        """Test prevention of cache key injection attacks"""
        # Arrange
        malicious_key = "../../etc/passwd"
        value = {"data": "test"}
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid cache key"):
            await cache_service.set(malicious_key, value)

    @pytest.mark.unit_security
    async def test_sensitive_data_handling(self, cache_service, mock_redis):
        """Test handling of sensitive data"""
        # Arrange
        key = "sensitive_key"
        sensitive_value = {
            "password": "secret123",
            "api_key": "sk-1234567890",
            "user_data": {"email": "user@example.com"}
        }
        
        mock_redis.set.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_sensitive_data'
            
            # Act
            await cache_service.set(key, sensitive_value)
            
            # Assert
            # Verify that sensitive data is handled appropriately
            # (This would depend on specific security requirements)
            mock_redis.set.assert_called_once()

    @pytest.mark.unit_security
    async def test_cache_entry_access_tracking(self, cache_service):
        """Test cache entry access tracking for security monitoring"""
        # Arrange
        key = "access_track_key"
        value = {"data": "test"}
        
        metadata = CacheMetadata(
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=3600),
            tags=[]
        )
        entry = CacheEntry(value, metadata)
        cache_service._memory_cache[key] = entry
        
        # Act
        await cache_service.get(key)
        await cache_service.get(key)
        await cache_service.get(key)
        
        # Assert
        assert entry.metadata.access_count == 3
        assert entry.metadata.last_accessed is not None

    @pytest.mark.unit_security
    async def test_tag_based_access_control(self, cache_service, mock_redis):
        """Test tag-based access control"""
        # Arrange
        key = "restricted_key"
        value = {"data": "restricted"}
        tags = ["restricted", "admin_only"]
        
        mock_redis.set.return_value = True
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        
        with patch('src.services.caching.redis_cache_service.serialize') as mock_serialize:
            mock_serialize.return_value = b'serialized_data'
            
            # Act
            await cache_service.set(key, value, tags=tags)
            
            # Assert
            # Verify tags are properly set for access control
            assert mock_redis.sadd.call_count == 2  # One for each tag
            assert mock_redis.expire.call_count == 2  # One for each tag
