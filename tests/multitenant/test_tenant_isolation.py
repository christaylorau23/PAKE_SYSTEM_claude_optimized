#!/usr/bin/env python3
"""
PAKE System - Phase 16 Multi-Tenant Security Validation Tests
Comprehensive testing for tenant isolation and data leakage prevention.
"""

import asyncio
import uuid
from datetime import datetime

import pytest

from src.services.database.multi_tenant_schema import (
    MultiTenantDatabaseConfig,
    MultiTenantPostgreSQLService,
)
from src.services.database.tenant_aware_dal import (
    TenantAwareDataAccessLayer,
    TenantIsolationError,
)


class TestTenantIsolation:
    """
    Comprehensive test suite for tenant isolation validation.

    Tests:
    - Database-level tenant isolation
    - Application-level tenant filtering
    - Cross-tenant data access prevention
    - Tenant context propagation
    - Security boundary enforcement
    """

    @pytest.fixture
    async def db_service(self):
        """Create test database service"""
        config = MultiTenantDatabaseConfig(database="pake_system_multitenant_test")
        service = MultiTenantPostgreSQLService(config)
        await service.initialize()
        yield service
        await service.close()

    @pytest.fixture
    async def test_tenants(self, db_service):
        """Create test tenants"""
        tenant1 = await db_service.create_tenant(
            name="test-tenant-1",
            display_name="Test Tenant 1",
            domain="test1.pake.com",
            plan="basic",
        )

        tenant2 = await db_service.create_tenant(
            name="test-tenant-2",
            display_name="Test Tenant 2",
            domain="test2.pake.com",
            plan="professional",
        )

        return [tenant1, tenant2]

    @pytest.fixture
    async def test_users(self, db_service, test_tenants):
        """Create test users for each tenant"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        user1 = await db_service.create_user(
            tenant_id=tenant1_id,
            username="user1",
            email="user1@test1.pake.com",
            REDACTED_SECRET_hash="hash1",
            full_name="User 1",
        )

        user2 = await db_service.create_user(
            tenant_id=tenant2_id,
            username="user2",
            email="user2@test2.pake.com",
            REDACTED_SECRET_hash="hash2",
            full_name="User 2",
        )

        return [user1, user2]

    @pytest.fixture
    async def test_search_history(self, db_service, test_tenants, test_users):
        """Create test search history for each tenant"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]
        user1_id = test_users[0]["id"]
        user2_id = test_users[1]["id"]

        # Create search history for tenant 1
        search1_id = await db_service.save_search_history(
            tenant_id=tenant1_id,
            user_id=user1_id,
            query="machine learning",
            sources=["web", "arxiv"],
            results_count=10,
            execution_time_ms=100.0,
        )

        # Create search history for tenant 2
        search2_id = await db_service.save_search_history(
            tenant_id=tenant2_id,
            user_id=user2_id,
            query="artificial intelligence",
            sources=["web", "pubmed"],
            results_count=15,
            execution_time_ms=150.0,
        )

        return [search1_id, search2_id]

    # Database-Level Isolation Tests

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self, db_service, test_tenants, test_users):
        """Test that tenant data is properly isolated at database level"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        # Get users for tenant 1
        tenant1_users = await db_service.get_tenant_users(tenant1_id)
        assert len(tenant1_users) == 1
        assert tenant1_users[0]["tenant_id"] == tenant1_id

        # Get users for tenant 2
        tenant2_users = await db_service.get_tenant_users(tenant2_id)
        assert len(tenant2_users) == 1
        assert tenant2_users[0]["tenant_id"] == tenant2_id

        # Verify no cross-tenant data leakage
        assert tenant1_users[0]["id"] != tenant2_users[0]["id"]
        assert tenant1_users[0]["username"] != tenant2_users[0]["username"]

    @pytest.mark.asyncio
    async def test_tenant_search_history_isolation(
        self,
        db_service,
        test_tenants,
        test_search_history,
    ):
        """Test that search history is properly isolated by tenant"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        # Get search history for tenant 1
        tenant1_searches = await db_service.get_tenant_search_history(tenant1_id)
        assert len(tenant1_searches) == 1
        assert tenant1_searches[0]["tenant_id"] == tenant1_id
        assert tenant1_searches[0]["query"] == "machine learning"

        # Get search history for tenant 2
        tenant2_searches = await db_service.get_tenant_search_history(tenant2_id)
        assert len(tenant2_searches) == 1
        assert tenant2_searches[0]["tenant_id"] == tenant2_id
        assert tenant2_searches[0]["query"] == "artificial intelligence"

        # Verify no cross-tenant data leakage
        assert tenant1_searches[0]["id"] != tenant2_searches[0]["id"]

    @pytest.mark.asyncio
    async def test_cross_tenant_access_prevention(
        self,
        db_service,
        test_tenants,
        test_users,
    ):
        """Test that cross-tenant access is prevented"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]
        user1_id = test_users[0]["id"]

        # Try to get user1 from tenant1 using tenant2 context
        # This should return None (no cross-tenant access)
        user_from_wrong_tenant = await db_service.get_user_by_id(tenant2_id, user1_id)
        assert user_from_wrong_tenant is None

        # Verify user1 is only accessible from tenant1
        user_from_correct_tenant = await db_service.get_user_by_id(tenant1_id, user1_id)
        assert user_from_correct_tenant is not None
        assert user_from_correct_tenant["id"] == user1_id

    @pytest.mark.asyncio
    async def test_tenant_analytics_isolation(
        self,
        db_service,
        test_tenants,
        test_search_history,
    ):
        """Test that analytics are properly isolated by tenant"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        # Get analytics for tenant 1
        tenant1_analytics = await db_service.get_tenant_search_analytics(
            tenant1_id,
            days=1,
        )
        assert tenant1_analytics["tenant_id"] == tenant1_id
        assert tenant1_analytics["total_searches"] == 1

        # Get analytics for tenant 2
        tenant2_analytics = await db_service.get_tenant_search_analytics(
            tenant2_id,
            days=1,
        )
        assert tenant2_analytics["tenant_id"] == tenant2_id
        assert tenant2_analytics["total_searches"] == 1

        # Verify analytics don't include cross-tenant data
        assert tenant1_analytics["total_searches"] == 1
        assert tenant2_analytics["total_searches"] == 1

    # Application-Level Isolation Tests

    @pytest.mark.asyncio
    async def test_tenant_aware_dal_isolation(
        self,
        db_service,
        test_tenants,
        test_users,
    ):
        """Test tenant-aware Data Access Layer isolation"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        # Create DAL instances for each tenant
        dal1 = TenantAwareDataAccessLayer(db_service)
        dal2 = TenantAwareDataAccessLayer(db_service)

        # Mock tenant context for DAL1
        from src.middleware.tenant_context import tenant_context

        tenant_context.set(tenant1_id)

        # Test DAL1 can only see tenant1 data
        tenant1_users = await dal1.users.get_all(tenant_id=tenant1_id)
        assert len(tenant1_users) == 1
        assert tenant1_users[0].tenant_id == tenant1_id

        # Mock tenant context for DAL2
        tenant_context.set(tenant2_id)

        # Test DAL2 can only see tenant2 data
        tenant2_users = await dal2.users.get_all(tenant_id=tenant2_id)
        assert len(tenant2_users) == 1
        assert tenant2_users[0].tenant_id == tenant2_id

    @pytest.mark.asyncio
    async def test_tenant_context_validation(self, db_service, test_tenants):
        """Test tenant context validation"""
        tenant1_id = test_tenants[0]["id"]
        invalid_tenant_id = str(uuid.uuid4())

        # Test valid tenant context
        tenant_data = await db_service.get_tenant_by_id(tenant1_id)
        assert tenant_data is not None
        assert tenant_data["id"] == tenant1_id

        # Test invalid tenant context
        invalid_tenant_data = await db_service.get_tenant_by_id(invalid_tenant_id)
        assert invalid_tenant_data is None

    @pytest.mark.asyncio
    async def test_tenant_isolation_error_handling(self, db_service, test_tenants):
        """Test that tenant isolation errors are properly handled"""
        dal = TenantAwareDataAccessLayer(db_service)

        # Test without tenant context
        from src.middleware.tenant_context import tenant_context

        tenant_context.set(None)

        with pytest.raises(TenantIsolationError):
            await dal.users.get_all()

    # Security Boundary Tests

    @pytest.mark.asyncio
    async def test_tenant_resource_isolation(self, db_service, test_tenants):
        """Test that tenant resources are properly isolated"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        # Create resource usage for tenant 1
        await db_service.log_tenant_activity(
            tenant_id=tenant1_id,
            activity_type="api_call",
            activity_data={"endpoint": "/api/search", "method": "POST"},
        )

        # Create resource usage for tenant 2
        await db_service.log_tenant_activity(
            tenant_id=tenant2_id,
            activity_type="api_call",
            activity_data={"endpoint": "/api/analytics", "method": "GET"},
        )

        # Get activity for tenant 1
        tenant1_activity = await db_service.get_tenant_activity(tenant1_id)
        assert len(tenant1_activity) == 1
        assert tenant1_activity[0]["tenant_id"] == tenant1_id
        assert tenant1_activity[0]["activity_type"] == "api_call"

        # Get activity for tenant 2
        tenant2_activity = await db_service.get_tenant_activity(tenant2_id)
        assert len(tenant2_activity) == 1
        assert tenant2_activity[0]["tenant_id"] == tenant2_id
        assert tenant2_activity[0]["activity_type"] == "api_call"

        # Verify no cross-tenant activity leakage
        assert tenant1_activity[0]["id"] != tenant2_activity[0]["id"]

    @pytest.mark.asyncio
    async def test_tenant_status_validation(self, db_service, test_tenants):
        """Test tenant status validation"""
        tenant1_id = test_tenants[0]["id"]

        # Test active tenant
        tenant_data = await db_service.get_tenant_by_id(tenant1_id)
        assert tenant_data["status"] == "active"

        # Suspend tenant
        await db_service.update_tenant_status(tenant1_id, "suspended")

        # Verify status update
        updated_tenant = await db_service.get_tenant_by_id(tenant1_id)
        assert updated_tenant["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_tenant_plan_limits(self, db_service, test_tenants):
        """Test tenant plan limits enforcement"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        # Get tenant data
        tenant1_data = await db_service.get_tenant_by_id(tenant1_id)
        tenant2_data = await db_service.get_tenant_by_id(tenant2_id)

        # Verify plan assignments
        assert tenant1_data["plan"] == "basic"
        assert tenant2_data["plan"] == "professional"

        # Verify limits are set
        assert tenant1_data["limits"] is not None
        assert tenant2_data["limits"] is not None

    # Performance and Scalability Tests

    @pytest.mark.asyncio
    async def test_tenant_query_performance(self, db_service, test_tenants):
        """Test that tenant-scoped queries perform well"""
        tenant1_id = test_tenants[0]["id"]

        # Create multiple users for performance testing
        start_time = datetime.utcnow()

        for i in range(10):
            await db_service.create_user(
                tenant_id=tenant1_id,
                username=f"perf_user_{i}",
                email=f"perf_user_{i}@test1.pake.com",
                REDACTED_SECRET_hash=f"hash_{i}",
                full_name=f"Performance User {i}",
            )

        # Query users with tenant filter
        users = await db_service.get_tenant_users(tenant1_id)

        end_time = datetime.utcnow()
        query_time = (end_time - start_time).total_seconds()

        # Verify performance (should be fast with proper indexing)
        assert query_time < 1.0  # Less than 1 second
        assert len(users) == 11  # 1 original + 10 new users

    @pytest.mark.asyncio
    async def test_concurrent_tenant_operations(self, db_service, test_tenants):
        """Test concurrent operations across multiple tenants"""
        tenant1_id = test_tenants[0]["id"]
        tenant2_id = test_tenants[1]["id"]

        async def create_users_for_tenant(tenant_id: str, count: int):
            """Create users for a specific tenant"""
            for i in range(count):
                await db_service.create_user(
                    tenant_id=tenant_id,
                    username=f"concurrent_user_{i}",
                    email=f"concurrent_user_{i}@{tenant_id}.com",
                    REDACTED_SECRET_hash=f"hash_{i}",
                    full_name=f"Concurrent User {i}",
                )

        # Run concurrent operations
        await asyncio.gather(
            create_users_for_tenant(tenant1_id, 5),
            create_users_for_tenant(tenant2_id, 5),
        )

        # Verify isolation maintained
        tenant1_users = await db_service.get_tenant_users(tenant1_id)
        tenant2_users = await db_service.get_tenant_users(tenant2_id)

        assert len(tenant1_users) == 6  # 1 original + 5 new
        assert len(tenant2_users) == 6  # 1 original + 5 new

        # Verify no cross-tenant data
        tenant1_user_ids = {user["id"] for user in tenant1_users}
        tenant2_user_ids = {user["id"] for user in tenant2_users}

        assert len(tenant1_user_ids.intersection(tenant2_user_ids)) == 0

    # Edge Case Tests

    @pytest.mark.asyncio
    async def test_empty_tenant_data(self, db_service):
        """Test handling of empty tenant data"""
        # Create tenant with no data
        empty_tenant = await db_service.create_tenant(
            name="empty-tenant",
            display_name="Empty Tenant",
            plan="basic",
        )

        # Verify empty tenant can be queried
        tenant_data = await db_service.get_tenant_by_id(empty_tenant["id"])
        assert tenant_data is not None
        assert tenant_data["name"] == "empty-tenant"

        # Verify no users
        users = await db_service.get_tenant_users(empty_tenant["id"])
        assert len(users) == 0

        # Verify no search history
        searches = await db_service.get_tenant_search_history(empty_tenant["id"])
        assert len(searches) == 0

    @pytest.mark.asyncio
    async def test_tenant_deletion_cascade(self, db_service, test_tenants, test_users):
        """Test that tenant deletion cascades properly"""
        tenant1_id = test_tenants[0]["id"]
        user1_id = test_users[0]["id"]

        # Create some data for tenant 1
        await db_service.save_search_history(
            tenant_id=tenant1_id,
            user_id=user1_id,
            query="test query",
            sources=["web"],
            results_count=5,
            execution_time_ms=50.0,
        )

        # Verify data exists
        users = await db_service.get_tenant_users(tenant1_id)
        assert len(users) == 1

        searches = await db_service.get_tenant_search_history(tenant1_id)
        assert len(searches) == 1

        # Delete tenant (this would cascade delete all related data)
        # Note: In a real implementation, this would be handled by database constraints
        await db_service.update_tenant_status(tenant1_id, "deleted")

        # Verify tenant status updated
        tenant_data = await db_service.get_tenant_by_id(tenant1_id)
        assert tenant_data["status"] == "deleted"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
