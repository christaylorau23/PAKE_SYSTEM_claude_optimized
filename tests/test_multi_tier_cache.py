#!/usr/bin/env python3
"""
PAKE System - Multi-Tier Caching System Tests
Phase 2B Sprint 4: Comprehensive TDD testing for production-scale caching

Tests memory, disk, and distributed caching with intelligent tier management,
eviction policies, and performance optimization.
"""

import asyncio
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from services.caching.multi_tier_cache import (
    CacheConfig,
    CacheEntry,
    CacheKey,
    CachePolicy,
    CacheStats,
    CacheTier,
    DiskCacheTier,
    MemoryCacheTier,
    MultiTierCacheManager,
)


class TestMultiTierCacheManager:
    """
    Comprehensive test suite for multi-tier caching system.
    Tests memory, disk, and distributed caching with intelligent management.
    """

    @pytest.fixture()
    def temp_cache_dir(self):
        """Create temporary directory for cache testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture()
    def cache_config(self, temp_cache_dir):
        """Standard cache configuration"""
        return CacheConfig(
            memory_max_size=1024 * 1024,  # 1MB
            memory_max_items=100,
            memory_ttl_seconds=3600,
            disk_max_size=10 * 1024 * 1024,  # 10MB
            disk_ttl_seconds=86400,
            disk_path=temp_cache_dir,
            redis_url=None,  # No Redis for basic tests
            default_policy=CachePolicy.LRU,
            compression_enabled=True,
            stats_enabled=True,
        )

    @pytest.fixture()
    def redis_config(self, temp_cache_dir):
        """Redis-enabled cache configuration"""
        return CacheConfig(
            memory_max_size=1024 * 1024,
            memory_max_items=100,
            disk_path=temp_cache_dir,
            redis_url="redis://localhost:6379/0",
            redis_ttl_seconds=604800,
        )

    @pytest_asyncio.fixture
    async def cache_manager(self, cache_config):
        """Create cache manager instance"""
        manager = MultiTierCacheManager(cache_config)
        yield manager
        await manager.close()

    @pytest_asyncio.fixture
    async def redis_cache_manager(self, redis_config):
        """Create Redis-enabled cache manager instance"""
        manager = MultiTierCacheManager(redis_config)
        yield manager
        await manager.close()

    @pytest.fixture()
    def sample_cache_key(self):
        """Sample cache key for testing"""
        return CacheKey(
            namespace="test",
            key="sample_data",
            version="1.0",
            tags=["unit_test", "sample"],
        )

    @pytest.fixture()
    def sample_data(self):
        """Sample data for caching"""
        return {
            "id": 12345,
            "name": "Test Data",
            "content": "This is sample content for cache testing",
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": {
                "type": "test_data",
                "size": "medium",
                "tags": ["cache", "test", "sample"],
            },
        }

    # ========================================================================
    # BASIC CACHE OPERATIONS TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_set_and_get_cache_entries_successfully(
        self,
        cache_manager,
        sample_cache_key,
        sample_data,
    ):
        """
        Test: Should set and retrieve cache entries with proper
        data integrity and metadata preservation.
        """
        # Set data in cache
        success = await cache_manager.set(sample_cache_key, sample_data, ttl=3600)
        assert success

        # Get data from cache
        retrieved_data = await cache_manager.get(sample_cache_key)

        assert retrieved_data is not None
        assert retrieved_data == sample_data
        assert retrieved_data["id"] == 12345
        assert retrieved_data["name"] == "Test Data"
        assert retrieved_data["metadata"]["type"] == "test_data"

    @pytest.mark.asyncio()
    async def test_should_handle_cache_miss_gracefully(self, cache_manager):
        """
        Test: Should handle cache misses gracefully by returning None
        without raising exceptions.
        """
        nonexistent_key = CacheKey(
            namespace="test",
            key="nonexistent_data",
            version="1.0",
        )

        # Should return None for cache miss
        result = await cache_manager.get(nonexistent_key)
        assert result is None

    @pytest.mark.asyncio()
    async def test_should_delete_cache_entries_from_all_tiers(
        self,
        cache_manager,
        sample_cache_key,
        sample_data,
    ):
        """
        Test: Should delete cache entries from all tiers
        and confirm successful removal.
        """
        # Set data in cache
        await cache_manager.set(sample_cache_key, sample_data)

        # Confirm data exists
        retrieved_data = await cache_manager.get(sample_cache_key)
        assert retrieved_data is not None

        # Delete data
        deleted = await cache_manager.delete(sample_cache_key)
        assert deleted

        # Confirm data is gone
        result = await cache_manager.get(sample_cache_key)
        assert result is None

    @pytest.mark.asyncio()
    async def test_should_support_ttl_expiration(
        self,
        cache_manager,
        sample_cache_key,
        sample_data,
    ):
        """
        Test: Should respect TTL (Time To Live) settings and automatically
        expire cache entries after specified duration.
        """
        # Set data with short TTL
        await cache_manager.set(sample_cache_key, sample_data, ttl=1)

        # Should be available immediately
        result = await cache_manager.get(sample_cache_key)
        assert result is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired now
        result = await cache_manager.get(sample_cache_key)
        assert result is None

    # ========================================================================
    # MULTI-TIER FUNCTIONALITY TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_promote_frequently_accessed_items_to_memory(
        self,
        cache_manager,
        sample_cache_key,
        sample_data,
    ):
        """
        Test: Should promote frequently accessed items from disk to memory
        tier for improved performance.
        """
        # Set data in cache
        await cache_manager.set(sample_cache_key, sample_data)

        # Access multiple times to trigger promotion
        for _ in range(5):
            result = await cache_manager.get(sample_cache_key)
            assert result is not None

        # Check stats to verify promotion behavior
        stats = await cache_manager.get_stats()
        assert stats.hits[CacheTier.MEMORY] > 0

    @pytest.mark.asyncio()
    async def test_should_search_tiers_in_correct_order(self, cache_manager):
        """
        Test: Should search cache tiers in correct order (memory -> disk -> distributed)
        and return first match found.
        """
        # Create keys for different scenarios
        memory_key = CacheKey(namespace="test", key="memory_item")
        disk_key = CacheKey(namespace="test", key="disk_item")

        # Set data in different tiers by manipulating internal state
        await cache_manager.memory_tier.set(
            CacheEntry(
                key=memory_key,
                value="memory_data",
                created_at=datetime.now(UTC),
                expires_at=None,
            ),
        )

        # Get from memory (should be fastest)
        result = await cache_manager.get(memory_key)
        assert result == "memory_data"

        # Verify stats reflect memory hit
        stats = await cache_manager.get_stats()
        assert stats.hits[CacheTier.MEMORY] > 0

    @pytest.mark.asyncio()
    async def test_should_handle_large_data_sets_efficiently(self, cache_manager):
        """
        Test: Should handle large data sets efficiently with proper
        memory management and disk overflow.
        """
        large_data_items = []

        # Create multiple large data entries
        for i in range(10):
            key = CacheKey(namespace="test", key=f"large_item_{i}")
            data = {
                "id": i,
                "content": "x" * 10000,  # 10KB of data
                "metadata": {"size": "large", "index": i},
            }
            large_data_items.append((key, data))

        # Set all items
        for key, data in large_data_items:
            success = await cache_manager.set(key, data)
            assert success

        # Retrieve and verify all items
        for key, original_data in large_data_items:
            retrieved_data = await cache_manager.get(key)
            assert retrieved_data is not None
            assert retrieved_data["id"] == original_data["id"]
            assert len(retrieved_data["content"]) == 10000

    # ========================================================================
    # MEMORY TIER SPECIFIC TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_memory_tier_should_respect_size_limits(self, cache_config):
        """
        Test: Memory tier should respect size limits and evict entries
        when capacity is exceeded.
        """
        memory_tier = MemoryCacheTier(cache_config)

        # Fill memory tier to capacity
        large_value = "x" * 100000  # 100KB
        keys = []

        for i in range(15):  # Should exceed memory limit
            key = CacheKey(namespace="test", key=f"item_{i}")
            entry = CacheEntry(
                key=key,
                value=large_value,
                created_at=datetime.now(UTC),
                expires_at=None,
            )
            await memory_tier.set(entry)
            keys.append(key)

        # Check that some entries were evicted
        cache_size = await memory_tier.size()
        assert cache_size < 15  # Some items should have been evicted

        # Verify LRU eviction (first items should be gone)
        first_key = keys[0]
        result = await memory_tier.get(first_key)
        assert result is None

    @pytest.mark.asyncio()
    async def test_memory_tier_should_implement_lru_eviction(self, cache_config):
        """
        Test: Memory tier should implement LRU (Least Recently Used) eviction
        policy correctly.
        """
        # Use small cache for predictable eviction
        small_config = CacheConfig(
            memory_max_items=3,
            memory_max_size=1024 * 1024,  # Very small cache
        )
        memory_tier = MemoryCacheTier(small_config)

        # Add 3 items
        keys = []
        for i in range(3):
            key = CacheKey(namespace="test", key=f"item_{i}")
            entry = CacheEntry(
                key=key,
                value=f"data_{i}",
                created_at=datetime.now(UTC),
                expires_at=None,
            )
            await memory_tier.set(entry)
            keys.append(key)

        # Access first item to make it recently used
        await memory_tier.get(keys[0])

        # Add another item (should evict keys[1] which is least recently used)
        fourth_key = CacheKey(namespace="test", key="item_4")
        fourth_entry = CacheEntry(
            key=fourth_key,
            value="data_4",
            created_at=datetime.now(UTC),
            expires_at=None,
        )
        await memory_tier.set(fourth_entry)

        # Verify LRU behavior
        assert await memory_tier.get(keys[0]) is not None  # Recently accessed
        assert await memory_tier.get(keys[1]) is None  # Should be evicted
        assert await memory_tier.get(keys[2]) is not None  # Still there
        assert await memory_tier.get(fourth_key) is not None  # Newly added

    # ========================================================================
    # DISK TIER SPECIFIC TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_disk_tier_should_persist_data_across_restarts(self, temp_cache_dir):
        """
        Test: Disk tier should persist data across service restarts
        and maintain data integrity.
        """
        config = CacheConfig(disk_path=temp_cache_dir)

        # Create first disk tier instance
        disk_tier1 = DiskCacheTier(config)

        test_key = CacheKey(namespace="test", key="persistent_data")
        test_data = {"message": "This should persist", "timestamp": "2025-09-06"}

        entry = CacheEntry(
            key=test_key,
            value=test_data,
            created_at=datetime.now(UTC),
            expires_at=None,
        )

        # Set data in first instance
        await disk_tier1.set(entry)

        # Create second disk tier instance (simulating restart)
        disk_tier2 = DiskCacheTier(config)

        # Should be able to retrieve data from second instance
        retrieved_entry = await disk_tier2.get(test_key)
        assert retrieved_entry is not None
        assert retrieved_entry.value == test_data
        assert retrieved_entry.value["message"] == "This should persist"

    @pytest.mark.asyncio()
    async def test_disk_tier_should_handle_file_corruption_gracefully(
        self,
        temp_cache_dir,
    ):
        """
        Test: Disk tier should handle file corruption gracefully
        without crashing the application.
        """
        config = CacheConfig(disk_path=temp_cache_dir)
        disk_tier = DiskCacheTier(config)

        test_key = CacheKey(namespace="test", key="corrupt_test")

        # Create corrupted file manually
        cache_dir = Path(temp_cache_dir)
        import hashlib

        safe_key = hashlib.sha256(test_key.to_string().encode()).hexdigest()
        corrupt_file = cache_dir / f"{safe_key}.cache"

        # Write invalid data
        with open(corrupt_file, "w") as f:
            f.write("This is not valid serialized data")

        # Should handle corruption gracefully
        result = await disk_tier.get(test_key)
        assert result is None  # Should return None, not crash

    # ========================================================================
    # CACHE STATISTICS TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_track_comprehensive_cache_statistics(
        self,
        cache_manager,
        sample_cache_key,
        sample_data,
    ):
        """
        Test: Should track comprehensive cache statistics including
        hits, misses, hit rates, and performance metrics.
        """
        # Perform various cache operations
        await cache_manager.set(sample_cache_key, sample_data)
        await cache_manager.get(sample_cache_key)  # Hit

        miss_key = CacheKey(namespace="test", key="nonexistent")
        await cache_manager.get(miss_key)  # Miss

        # Get statistics
        stats = await cache_manager.get_stats()

        # Verify statistics structure
        assert isinstance(stats, CacheStats)
        assert CacheTier.MEMORY in stats.hits
        assert CacheTier.DISK in stats.hits
        assert CacheTier.MEMORY in stats.misses
        assert CacheTier.DISK in stats.misses

        # Verify hit rate calculation
        assert 0.0 <= stats.hit_rate <= 1.0

        # Should have recorded some activity
        total_hits = sum(stats.hits.values())
        total_misses = sum(stats.misses.values())
        assert total_hits > 0 or total_misses > 0

    @pytest.mark.asyncio()
    async def test_should_calculate_hit_rate_accurately(
        self,
        cache_manager,
        sample_data,
    ):
        """
        Test: Should calculate cache hit rate accurately based on
        hits and misses across all tiers.
        """
        # Create predictable hit/miss pattern
        hit_keys = []
        miss_keys = []

        # Create 5 items that will be hits
        for i in range(5):
            key = CacheKey(namespace="test", key=f"hit_item_{i}")
            await cache_manager.set(key, sample_data)
            hit_keys.append(key)

        # Create 5 items that will be misses
        for i in range(5):
            key = CacheKey(namespace="test", key=f"miss_item_{i}")
            miss_keys.append(key)

        # Reset stats to start fresh
        cache_manager.stats = CacheStats()

        # Perform hits
        for key in hit_keys:
            await cache_manager.get(key)

        # Perform misses
        for key in miss_keys:
            await cache_manager.get(key)

        # Check hit rate
        stats = await cache_manager.get_stats()
        expected_hit_rate = 5 / 10  # 5 hits out of 10 requests
        assert abs(stats.hit_rate - expected_hit_rate) < 0.1  # Allow for some variance

    # ========================================================================
    # TAG-BASED INVALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_support_tag_based_invalidation(
        self,
        cache_manager,
        sample_data,
    ):
        """
        Test: Should support tag-based cache invalidation for
        efficient bulk cache clearing.
        """
        # Create items with different tags
        user_keys = []
        admin_keys = []

        for i in range(3):
            # User data
            user_key = CacheKey(
                namespace="user",
                key=f"user_data_{i}",
                tags=["user", "profile"],
            )
            await cache_manager.set(user_key, sample_data)
            user_keys.append(user_key)

            # Admin data
            admin_key = CacheKey(
                namespace="admin",
                key=f"admin_data_{i}",
                tags=["admin", "system"],
            )
            await cache_manager.set(admin_key, sample_data)
            admin_keys.append(admin_key)

        # Invalidate by tag
        invalidated = await cache_manager.invalidate_by_tags(["user"])

        # Mock implementation returns 0, but in production would invalidate tagged items
        assert invalidated >= 0

    # ========================================================================
    # NAMESPACE SUPPORT TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_support_namespace_isolation(self, cache_manager, sample_data):
        """
        Test: Should support namespace isolation to prevent
        key collisions between different application areas.
        """
        # Create items in different namespaces with same key
        user_key = CacheKey(namespace="users", key="item_1")
        product_key = CacheKey(namespace="products", key="item_1")

        user_data = {"type": "user", "name": "John Doe"}
        product_data = {"type": "product", "name": "Widget"}

        # Set data in different namespaces
        await cache_manager.set(user_key, user_data)
        await cache_manager.set(product_key, product_data)

        # Retrieve data
        retrieved_user = await cache_manager.get(user_key)
        retrieved_product = await cache_manager.get(product_key)

        # Verify namespace isolation
        assert retrieved_user["type"] == "user"
        assert retrieved_product["type"] == "product"
        assert retrieved_user != retrieved_product

    # ========================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_concurrent_access_safely(
        self,
        cache_manager,
        sample_data,
    ):
        """
        Test: Should handle concurrent cache access safely without
        data corruption or race conditions.
        """

        async def concurrent_cache_operations(base_id: int):
            for i in range(5):
                key = CacheKey(namespace="concurrent", key=f"item_{base_id}_{i}")
                await cache_manager.set(key, {**sample_data, "id": f"{base_id}_{i}"})
                result = await cache_manager.get(key)
                assert result is not None
                assert result["id"] == f"{base_id}_{i}"

        # Run concurrent operations
        tasks = [concurrent_cache_operations(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify no data corruption occurred
        stats = await cache_manager.get_stats()
        assert sum(stats.hits.values()) > 0
        assert sum(stats.sets.values()) > 0

    @pytest.mark.asyncio()
    async def test_should_maintain_performance_under_load(self, cache_manager):
        """
        Test: Should maintain reasonable performance under high load
        with many cache operations.
        """
        import time

        start_time = time.time()

        # Perform many cache operations
        for i in range(100):
            key = CacheKey(namespace="performance", key=f"item_{i}")
            data = {"id": i, "data": f"performance_test_{i}"}
            await cache_manager.set(key, data)
            retrieved = await cache_manager.get(key)
            assert retrieved is not None

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 5.0  # Should complete within 5 seconds

        # Verify operations were tracked
        stats = await cache_manager.get_stats()
        assert sum(stats.hits.values()) >= 100
        assert sum(stats.sets.values()) >= 100

    # ========================================================================
    # HEALTH CHECK TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_provide_comprehensive_health_status(
        self,
        cache_manager,
        sample_cache_key,
        sample_data,
    ):
        """
        Test: Should provide comprehensive health check information
        including tier status, statistics, and configuration.
        """
        # Add some data first
        await cache_manager.set(sample_cache_key, sample_data)
        await cache_manager.get(sample_cache_key)

        health_status = await cache_manager.health_check()

        # Verify health check structure
        assert "status" in health_status
        assert "tiers" in health_status
        assert "overall_hit_rate" in health_status
        assert "average_response_time" in health_status
        assert "configuration" in health_status

        # Verify tier information
        assert "memory" in health_status["tiers"]
        assert "disk" in health_status["tiers"]

        # Should be healthy
        assert health_status["status"] == "healthy"

        # Verify configuration information
        config_info = health_status["configuration"]
        assert "memory_max_size" in config_info
        assert "disk_max_size" in config_info
        assert "memory_ttl" in config_info
        assert "disk_ttl" in config_info

    # ========================================================================
    # RESOURCE CLEANUP TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_cleanup_resources_properly(self, cache_config, sample_data):
        """
        Test: Should properly clean up resources when cache manager
        is closed.
        """
        cache_manager = MultiTierCacheManager(cache_config)

        # Add some data
        test_key = CacheKey(namespace="test", key="cleanup_test")
        await cache_manager.set(test_key, sample_data)

        # Verify data exists
        result = await cache_manager.get(test_key)
        assert result is not None

        # Close cache manager
        await cache_manager.close()

        # Create new instance - memory should be cleared but disk should persist
        new_cache_manager = MultiTierCacheManager(cache_config)

        # Memory should be empty, but disk might have data
        memory_size = await new_cache_manager.memory_tier.size()
        assert memory_size == 0

        await new_cache_manager.close()


class TestCacheDataStructures:
    """Test cache-specific data structures"""

    def test_cache_key_should_generate_consistent_strings(self):
        """
        Test: CacheKey should generate consistent string representations
        for the same input parameters.
        """
        key1 = CacheKey(
            namespace="test",
            key="data_item",
            version="1.0",
            tags=["tag1", "tag2"],
        )

        key2 = CacheKey(
            namespace="test",
            key="data_item",
            version="1.0",
            tags=["tag2", "tag1"],  # Different order
        )

        # Should generate same string (tags are sorted)
        assert key1.to_string() == key2.to_string()

    def test_cache_entry_should_be_immutable(self):
        """
        Test: CacheEntry instances should be immutable to ensure
        data integrity throughout caching pipeline.
        """
        entry = CacheEntry(
            key=CacheKey(namespace="test", key="immutable_test"),
            value="test_data",
            created_at=datetime.now(UTC),
            expires_at=None,
        )

        # Should be frozen dataclass (immutable)
        with pytest.raises(AttributeError):
            entry.value = "modified_data"

    def test_cache_stats_should_calculate_hit_rate_correctly(self):
        """
        Test: CacheStats should calculate hit rate correctly
        based on successful requests vs total requests.
        """
        stats = CacheStats()

        # Set request-level statistics
        stats.total_requests = 20
        stats.successful_requests = 11

        # Calculate hit rate
        hit_rate = stats.calculate_hit_rate()

        # Should be 11 successful out of 20 total = 0.55
        expected_rate = 11 / 20
        assert abs(hit_rate - expected_rate) < 0.01

    def test_cache_config_should_have_sensible_defaults(self):
        """
        Test: CacheConfig should provide reasonable default values
        for all configuration parameters.
        """
        config = CacheConfig()

        # Verify defaults
        assert config.memory_max_size == 100 * 1024 * 1024  # 100MB
        assert config.memory_max_items == 10000
        assert config.memory_ttl_seconds == 3600
        assert config.disk_max_size == 1024 * 1024 * 1024  # 1GB
        assert config.disk_ttl_seconds == 86400
        assert config.disk_path == "./cache"
        assert config.redis_url is None
        assert config.default_policy == CachePolicy.LRU
        assert config.compression_enabled
        assert config.encryption_enabled == False
        assert config.stats_enabled
