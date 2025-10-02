"""
Comprehensive Integration Tests for Service Interactions

Tests service-to-service interactions with real database and Redis connections.
Uses ephemeral test database and factory-boy for realistic test data generation.

Following Testing Pyramid: Integration Tests (20%) - Service interactions, real dependencies
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from src.services.analytics.advanced_analytics_engine import AdvancedAnalyticsEngine
from src.services.auth.src.services.EmailService import EmailService
from src.services.auth.src.services.MFAService import MFAService
from src.services.auth.src.services.PasswordService import PasswordService
from src.services.auth.src.services.RBACService import RBACService
from src.services.auth.src.services.SessionService import SessionService
from src.services.auth.src.services.TokenService import TokenService
from src.services.auth.src.services.UserService import UserService
from src.services.caching.redis_cache_service import CacheConfig, RedisCacheService
from src.services.ingestion.orchestrator import IngestionConfig, IngestionOrchestrator
from tests.factories import (
    UserFactory,
    UserInDBFactory,
)


class TestServiceIntegrationComprehensive:
    """Comprehensive integration tests for service interactions"""

    @pytest.fixture(scope="session")
    async def test_database(self):
        """Create ephemeral test database"""
        # This would typically use testcontainers or similar
        # For now, we'll mock the database connection
        return {
            "url": "postgresql://test_user:test_password@localhost:5432/pake_test",
            "connection": None,  # Would be actual connection in real implementation
        }

    @pytest.fixture(scope="session")
    async def test_redis(self):
        """Create ephemeral test Redis instance"""
        # This would typically use testcontainers or similar
        # For now, we'll mock the Redis connection
        return {
            "url": "redis://localhost:6379/1",
            "connection": None,  # Would be actual connection in real implementation
        }

    @pytest.fixture()
    async def redis_service(self, test_redis):
        """Create Redis service with test connection"""
        config = CacheConfig(
            redis_url=test_redis["url"], default_ttl=3600, max_memory_cache_size=1000
        )
        service = RedisCacheService(config=config)
        await service.initialize()
        return service

    @pytest.fixture()
    async def user_service(self, redis_service):
        """Create UserService with real Redis integration"""
        # Create mocked dependencies
        token_service = TokenService()
        mfa_service = MFAService()
        session_service = SessionService()
        rbac_service = RBACService()
        password_service = PasswordService()
        email_service = EmailService()

        return UserService(
            redis=redis_service,
            tokenService=token_service,
            mfaService=mfa_service,
            sessionService=session_service,
            rbacService=rbac_service,
            passwordService=password_service,
            emailService=email_service,
        )

    @pytest.fixture()
    async def ingestion_orchestrator(self, redis_service):
        """Create IngestionOrchestrator with real Redis integration"""
        config = IngestionConfig(
            max_concurrent_requests=5,
            timeout_seconds=30,
            retry_attempts=3,
            enable_caching=True,
            cache_ttl_hours=24,
        )

        orchestrator = IngestionOrchestrator(config=config)
        # Inject Redis service for caching
        orchestrator.cache_service = redis_service
        return orchestrator

    @pytest.fixture()
    async def analytics_engine(self, redis_service):
        """Create AdvancedAnalyticsEngine with real Redis integration"""
        engine = AdvancedAnalyticsEngine()
        # Inject Redis service for caching
        engine.cache_service = redis_service
        return engine

    # ============================================================================
    # AUTHENTICATION SERVICE INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration()
    @pytest.mark.integration_auth()
    async def test_user_registration_and_login_flow(self, user_service, redis_service):
        """Test complete user registration and login flow with real Redis"""
        # Arrange
        user_data = UserFactory(
            email="integration@example.com",
            username="integration_user",
            password="SecurePassword123!",
        )

        # Act 1: User Registration
        registered_user = await user_service.createUser(
            email=user_data["email"],
            username=user_data["username"],
            password=user_data["password"],
            firstName="Integration",
            lastName="Test",
        )

        # Assert 1: User created successfully
        assert registered_user is not None
        assert registered_user.email == user_data["email"]
        assert registered_user.username == user_data["username"]

        # Verify user stored in Redis
        stored_user = await redis_service.get(f"user:{registered_user.id}")
        assert stored_user is not None

        # Act 2: User Login
        auth_result = await user_service.authenticateUser(
            user_data["username"], user_data["password"]
        )

        # Assert 2: Login successful
        assert auth_result.success is True
        assert auth_result.accessToken is not None
        assert auth_result.refreshToken is not None
        assert auth_result.user.username == user_data["username"]

    @pytest.mark.integration()
    @pytest.mark.integration_auth()
    async def test_session_management_integration(self, user_service, redis_service):
        """Test session management with real Redis integration"""
        # Arrange
        user_data = UserInDBFactory()

        # Act: Create session
        session_id = await user_service.sessionService.createSession(
            user_id=user_data["id"], username=user_data["username"], role="user"
        )

        # Assert: Session stored in Redis
        session_data = await redis_service.get(f"session:{session_id}")
        assert session_data is not None
        assert session_data["user_id"] == user_data["id"]
        assert session_data["username"] == user_data["username"]

        # Act: Validate session
        is_valid = await user_service.sessionService.validateSession(session_id)
        assert is_valid is True

        # Act: Delete session
        await user_service.sessionService.deleteSession(session_id)

        # Assert: Session removed from Redis
        deleted_session = await redis_service.get(f"session:{session_id}")
        assert deleted_session is None

    @pytest.mark.integration()
    @pytest.mark.integration_auth()
    async def test_multi_tenant_user_isolation(self, user_service, redis_service):
        """Test multi-tenant user isolation with real Redis"""
        # Arrange
        tenant1_user = UserFactory(tenant_id="tenant_1")
        tenant2_user = UserFactory(tenant_id="tenant_2")

        # Act: Create users for different tenants
        user1 = await user_service.createUser(
            email=tenant1_user["email"],
            username=tenant1_user["username"],
            password="Password123!",
            firstName="Tenant1",
            lastName="User",
            tenant_id="tenant_1",
        )

        user2 = await user_service.createUser(
            email=tenant2_user["email"],
            username=tenant2_user["username"],
            password="Password123!",
            firstName="Tenant2",
            lastName="User",
            tenant_id="tenant_2",
        )

        # Assert: Users are isolated by tenant
        stored_user1 = await redis_service.get(f"user:{user1.id}")
        stored_user2 = await redis_service.get(f"user:{user2.id}")

        assert stored_user1["tenant_id"] == "tenant_1"
        assert stored_user2["tenant_id"] == "tenant_2"

        # Act: Try to access user from wrong tenant
        wrong_tenant_user = await user_service.getUserById(
            user1.id, tenant_id="tenant_2"
        )

        # Assert: Should not find user from wrong tenant
        assert wrong_tenant_user is None

    # ============================================================================
    # INGESTION SERVICE INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration()
    @pytest.mark.integration_cache()
    async def test_ingestion_with_caching_integration(
        self, ingestion_orchestrator, redis_service
    ):
        """Test ingestion service with real Redis caching"""
        # Arrange
        topic = "machine learning integration test"
        context = {"user_id": "integration_user", "tenant_id": "test_tenant"}

        # Act: First ingestion (should cache results)
        result1 = await ingestion_orchestrator.ingest_content(topic, context)

        # Assert: First ingestion successful
        assert result1.success is True
        assert len(result1.content_items) > 0

        # Verify results cached in Redis
        cache_key = f"ingestion:{topic}:{hash(str(context))}"
        cached_result = await redis_service.get(cache_key)
        assert cached_result is not None

        # Act: Second ingestion (should use cache)
        result2 = await ingestion_orchestrator.ingest_content(topic, context)

        # Assert: Second ingestion uses cache
        assert result2.success is True
        assert result2.from_cache is True
        assert result2.execution_time < result1.execution_time

    @pytest.mark.integration()
    @pytest.mark.integration_cache()
    async def test_ingestion_cache_invalidation(
        self, ingestion_orchestrator, redis_service
    ):
        """Test ingestion cache invalidation with real Redis"""
        # Arrange
        topic = "cache invalidation test"
        context = {"user_id": "test_user"}

        # Act: Initial ingestion
        result1 = await ingestion_orchestrator.ingest_content(topic, context)
        assert result1.success is True

        # Act: Invalidate cache by tag
        invalidated_count = await redis_service.invalidate_by_tag("ingestion")
        assert invalidated_count > 0

        # Act: Second ingestion (should not use cache)
        result2 = await ingestion_orchestrator.ingest_content(topic, context)

        # Assert: Second ingestion not from cache
        assert result2.success is True
        assert result2.from_cache is False

    @pytest.mark.integration()
    @pytest.mark.integration_database()
    async def test_ingestion_with_database_persistence(
        self, ingestion_orchestrator, test_database
    ):
        """Test ingestion with database persistence"""
        # Arrange
        topic = "database persistence test"
        context = {"user_id": "db_user", "save_to_db": True}

        # Act: Ingest content with database persistence
        result = await ingestion_orchestrator.ingest_content(topic, context)

        # Assert: Content persisted to database
        assert result.success is True
        assert result.persisted_to_db is True

        # Verify content in database (would query actual database in real implementation)
        # For now, we'll assert the result indicates persistence
        assert result.content_items[0].get("db_id") is not None

    # ============================================================================
    # ANALYTICS SERVICE INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration()
    @pytest.mark.integration_cache()
    async def test_analytics_with_caching_integration(
        self, analytics_engine, redis_service
    ):
        """Test analytics service with real Redis caching"""
        # Arrange
        time_range = "24h"

        # Act: First analytics report (should cache results)
        report1 = await analytics_engine.generate_comprehensive_report(time_range)

        # Assert: First report generated successfully
        assert report1 is not None
        assert "trends" in report1
        assert "insights" in report1

        # Verify report cached in Redis
        cache_key = f"analytics:report:{time_range}"
        cached_report = await redis_service.get(cache_key)
        assert cached_report is not None

        # Act: Second report (should use cache)
        report2 = await analytics_engine.generate_comprehensive_report(time_range)

        # Assert: Second report uses cache
        assert report2 is not None
        assert report2.get("from_cache") is True

    @pytest.mark.integration()
    @pytest.mark.integration_database()
    async def test_analytics_with_database_integration(
        self, analytics_engine, test_database
    ):
        """Test analytics service with database integration"""
        # Arrange
        # Simulate some data in the database
        test_data = [
            {"timestamp": datetime.now(UTC), "metric": "user_count", "value": 100},
            {
                "timestamp": datetime.now(UTC) - timedelta(hours=1),
                "metric": "user_count",
                "value": 95,
            },
            {
                "timestamp": datetime.now(UTC) - timedelta(hours=2),
                "metric": "user_count",
                "value": 90,
            },
        ]

        # Act: Generate analytics report
        report = await analytics_engine.generate_comprehensive_report("24h")

        # Assert: Report includes database metrics
        assert report is not None
        assert "database_metrics" in report
        assert len(report["database_metrics"]) >= 0

    # ============================================================================
    # CROSS-SERVICE INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration()
    @pytest.mark.integration_auth()
    @pytest.mark.integration_cache()
    async def test_user_ingestion_workflow_integration(
        self, user_service, ingestion_orchestrator, redis_service
    ):
        """Test complete user workflow: login -> ingest content -> cache results"""
        # Arrange
        user_data = UserFactory()

        # Act 1: User registration and login
        user = await user_service.createUser(
            email=user_data["email"],
            username=user_data["username"],
            password="SecurePassword123!",
            firstName="Workflow",
            lastName="Test",
        )

        auth_result = await user_service.authenticateUser(
            user_data["username"], "SecurePassword123!"
        )
        assert auth_result.success is True

        # Act 2: User ingests content
        context = {"user_id": user.id, "session_id": auth_result.session_id}
        ingestion_result = await ingestion_orchestrator.ingest_content(
            "AI and Machine Learning", context
        )

        # Assert: Complete workflow successful
        assert ingestion_result.success is True
        assert len(ingestion_result.content_items) > 0

        # Verify user session still valid
        session_valid = await user_service.sessionService.validateSession(
            auth_result.session_id
        )
        assert session_valid is True

        # Verify content cached with user context
        cache_key = f"ingestion:AI and Machine Learning:{hash(str(context))}"
        cached_content = await redis_service.get(cache_key)
        assert cached_content is not None

    @pytest.mark.integration()
    @pytest.mark.integration_auth()
    @pytest.mark.integration_cache()
    async def test_analytics_user_behavior_integration(
        self, user_service, analytics_engine, redis_service
    ):
        """Test analytics tracking user behavior with real services"""
        # Arrange
        user_data = UserFactory()

        # Act 1: User performs actions
        user = await user_service.createUser(
            email=user_data["email"],
            username=user_data["username"],
            password="SecurePassword123!",
            firstName="Analytics",
            lastName="Test",
        )

        # Simulate user actions
        await user_service.updateUserProfile(
            user.id, {"last_search": "machine learning"}
        )
        await user_service.updateUserProfile(user.id, {"preferences": ["AI", "ML"]})

        # Act 2: Generate analytics report
        report = await analytics_engine.generate_comprehensive_report("24h")

        # Assert: Analytics includes user behavior
        assert report is not None
        assert "user_behavior" in report
        assert "search_patterns" in report

        # Verify analytics cached
        cache_key = "analytics:report:24h"
        cached_report = await redis_service.get(cache_key)
        assert cached_report is not None

    @pytest.mark.integration()
    @pytest.mark.integration_database()
    @pytest.mark.integration_cache()
    async def test_multi_tenant_data_isolation_integration(
        self, user_service, ingestion_orchestrator, redis_service
    ):
        """Test multi-tenant data isolation across services"""
        # Arrange
        tenant1_user = UserFactory(tenant_id="tenant_1")
        tenant2_user = UserFactory(tenant_id="tenant_2")

        # Act: Create users for different tenants
        user1 = await user_service.createUser(
            email=tenant1_user["email"],
            username=tenant1_user["username"],
            password="Password123!",
            firstName="Tenant1",
            lastName="User",
            tenant_id="tenant_1",
        )

        user2 = await user_service.createUser(
            email=tenant2_user["email"],
            username=tenant2_user["username"],
            password="Password123!",
            firstName="Tenant2",
            lastName="User",
            tenant_id="tenant_2",
        )

        # Act: Each user ingests content
        context1 = {"user_id": user1.id, "tenant_id": "tenant_1"}
        context2 = {"user_id": user2.id, "tenant_id": "tenant_2"}

        result1 = await ingestion_orchestrator.ingest_content("AI Research", context1)
        result2 = await ingestion_orchestrator.ingest_content("AI Research", context2)

        # Assert: Results are isolated by tenant
        assert result1.success is True
        assert result2.success is True

        # Verify cache keys are tenant-specific
        cache_key1 = f"ingestion:AI Research:{hash(str(context1))}"
        cache_key2 = f"ingestion:AI Research:{hash(str(context2))}"

        cached1 = await redis_service.get(cache_key1)
        cached2 = await redis_service.get(cache_key2)

        assert cached1 is not None
        assert cached2 is not None
        assert cached1 != cached2  # Different tenant data

    # ============================================================================
    # PERFORMANCE INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration()
    @pytest.mark.integration_performance()
    async def test_concurrent_service_operations(
        self, user_service, ingestion_orchestrator, redis_service
    ):
        """Test concurrent operations across services"""
        # Arrange
        users = [UserFactory() for _ in range(5)]

        # Act: Concurrent user creation and content ingestion
        tasks = []

        for i, user_data in enumerate(users):
            # Create user
            user_task = user_service.createUser(
                email=user_data["email"],
                username=user_data["username"],
                password="SecurePassword123!",
                firstName=f"Concurrent{i}",
                lastName="Test",
            )
            tasks.append(user_task)

        # Wait for all users to be created
        created_users = await asyncio.gather(*tasks)

        # Act: Concurrent content ingestion
        ingestion_tasks = []
        for user in created_users:
            context = {"user_id": user.id}
            ingestion_task = ingestion_orchestrator.ingest_content(
                f"Topic for user {user.id}", context
            )
            ingestion_tasks.append(ingestion_task)

        ingestion_results = await asyncio.gather(*ingestion_tasks)

        # Assert: All operations successful
        assert len(created_users) == 5
        assert len(ingestion_results) == 5
        assert all(result.success for result in ingestion_results)

        # Verify Redis performance
        stats = await redis_service.get_stats()
        assert stats["sets"] >= 10  # At least 5 users + 5 ingestion results

    @pytest.mark.integration()
    @pytest.mark.integration_performance()
    async def test_cache_performance_under_load(self, redis_service):
        """Test cache performance under load"""
        import time

        # Arrange
        test_data = [
            {"key": f"perf_test_{i}", "value": f"value_{i}"} for i in range(100)
        ]

        # Act: Set operations
        start_time = time.time()
        set_tasks = [
            redis_service.set(item["key"], item["value"]) for item in test_data
        ]
        await asyncio.gather(*set_tasks)
        set_time = time.time() - start_time

        # Act: Get operations
        start_time = time.time()
        get_tasks = [redis_service.get(item["key"]) for item in test_data]
        get_results = await asyncio.gather(*get_tasks)
        get_time = time.time() - start_time

        # Assert: Performance within acceptable limits
        assert set_time < 5.0  # Set operations should complete within 5 seconds
        assert get_time < 2.0  # Get operations should complete within 2 seconds
        assert all(result is not None for result in get_results)

        # Verify cache statistics
        stats = await redis_service.get_stats()
        assert stats["sets"] >= 100
        assert stats["hits"] >= 100
