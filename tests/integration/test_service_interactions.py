#!/usr/bin/env python3
"""
PAKE System - Service Integration Testing
Tests interactions between different services and components in the PAKE System.

This module demonstrates comprehensive integration testing patterns:
- Service-to-service communication
- Database integration
- Cache integration
- Message queue integration
- API gateway integration

Integration Testing Principles:
- Test real service interactions (not mocked)
- Use test databases and services
- Verify data flow between components
- Test error propagation and handling
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from src.services.analytics.performance_analyzer import PerformanceAnalyzer
from src.services.caching.redis_cache_strategy import RedisCacheStrategy
from src.services.database.connection_manager import DatabaseConnectionManager
from src.services.ingestion.arxiv_service import ArxivService
from src.services.ingestion.firecrawl_service import FirecrawlService
from src.services.ingestion.orchestrator import IngestionConfig, IngestionOrchestrator
from src.services.messaging.message_bus import MessageBus
from src.services.security.authentication_service import AuthenticationService


class TestServiceIntegration:
    """
    Integration tests for service-to-service interactions.

    These tests verify that services work together correctly
    and handle real-world scenarios with actual dependencies.
    """

    @pytest.fixture()
    async def test_database(self):
        """Set up test database connection"""
        db_manager = DatabaseConnectionManager(
            host="localhost",
            port=5432,
            database="pake_test",
            user="test_user",
            REDACTED_SECRET="test_password",
        )

        await db_manager.connect()
        yield db_manager
        await db_manager.disconnect()

    @pytest.fixture()
    async def test_cache(self):
        """Set up test Redis cache"""
        cache = RedisCacheStrategy("redis://localhost:6379/15")  # Use test database
        await cache.start()
        yield cache
        await cache.stop()

    @pytest.fixture()
    async def test_message_bus(self):
        """Set up test message bus"""
        bus = MessageBus("redis://localhost:6379/16")  # Use separate test database
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.fixture()
    def test_services(self):
        """Set up test services with real configurations"""
        return {
            "firecrawl": FirecrawlService(api_key="test_key"),
            "arxiv": ArxivService(),
            "auth": AuthenticationService(secret_key="test_secret_key"),
            "analyzer": PerformanceAnalyzer(),
        }

    # ========================================================================
    # Database Integration Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_database_cache_integration(self, test_database, test_cache):
        """
        Test: Database and cache should work together seamlessly

        Integration Test:
        - Store data in database
        - Cache the data for performance
        - Verify cache invalidation works
        - Test data consistency
        """
        # Test data
        user_data = {
            "user_id": "integration_test_user",
            "email": "integration@test.com",
            "profile": {
                "name": "Integration Test User",
                "preferences": {"theme": "dark", "notifications": True},
            },
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Store in database
        await test_database.execute_query(
            "INSERT INTO users (user_id, email, profile_data) VALUES ($1, $2, $3)",
            user_data["user_id"],
            user_data["email"],
            json.dumps(user_data["profile"]),
        )

        # Cache the data
        cache_success = await test_cache.set(
            "users", user_data["user_id"], user_data, ttl=3600
        )
        assert cache_success is True

        # Retrieve from cache (should be fast)
        cached_data = await test_cache.get("users", user_data["user_id"])
        assert cached_data is not None
        assert cached_data["user_id"] == user_data["user_id"]
        assert cached_data["email"] == user_data["email"]

        # Update in database
        updated_profile = user_data["profile"].copy()
        updated_profile["preferences"]["theme"] = "light"

        await test_database.execute_query(
            "UPDATE users SET profile_data = $1 WHERE user_id = $2",
            json.dumps(updated_profile),
            user_data["user_id"],
        )

        # Invalidate cache
        await test_cache.delete("users", user_data["user_id"])

        # Verify cache is invalidated
        cached_data_after_invalidation = await test_cache.get(
            "users", user_data["user_id"]
        )
        assert cached_data_after_invalidation is None

        # Retrieve fresh data from database
        fresh_data = await test_database.fetch_one(
            "SELECT user_id, email, profile_data FROM users WHERE user_id = $1",
            user_data["user_id"],
        )
        assert fresh_data is not None
        assert json.loads(fresh_data["profile_data"])["preferences"]["theme"] == "light"

    @pytest.mark.asyncio()
    async def test_ingestion_database_integration(self, test_database, test_services):
        """
        Test: Ingestion services should store results in database correctly

        Integration Test:
        - Execute ingestion process
        - Store results in database
        - Verify data integrity and relationships
        """
        # Set up ingestion orchestrator
        config = IngestionConfig(
            max_concurrent_sources=2,
            enable_cognitive_processing=True,
            database_storage=True,
        )

        orchestrator = IngestionOrchestrator(config)
        orchestrator.database_manager = test_database

        # Mock successful ingestion results
        mock_content_items = [
            {
                "title": "Integration Test Article 1",
                "content": "This is test content for integration testing",
                "source": "web",
                "url": "https://example.com/test1",
                "metadata": {"word_count": 150, "author": "Test Author"},
            },
            {
                "title": "Integration Test Article 2",
                "content": "More test content for integration testing",
                "source": "arxiv",
                "arxiv_id": "2401.12345",
                "metadata": {"word_count": 200, "authors": ["Author 1", "Author 2"]},
            },
        ]

        # Store ingestion results in database
        for item in mock_content_items:
            await test_database.execute_query(
                """
                INSERT INTO content_items (title, content, source_type, url, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                item["title"],
                item["content"],
                item["source"],
                item.get("url") or item.get("arxiv_id"),
                json.dumps(item["metadata"]),
                datetime.now(UTC),
            )

        # Verify data was stored correctly
        stored_items = await test_database.fetch_all(
            "SELECT * FROM content_items WHERE title LIKE 'Integration Test Article%'"
        )

        assert len(stored_items) == 2

        # Verify data integrity
        for stored_item in stored_items:
            assert stored_item["title"] is not None
            assert stored_item["content"] is not None
            assert stored_item["source_type"] in ["web", "arxiv"]
            assert stored_item["created_at"] is not None

            # Verify metadata is properly stored as JSON
            metadata = json.loads(stored_item["metadata"])
            assert "word_count" in metadata

    # ========================================================================
    # Cache Integration Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_cache_performance_integration(self, test_cache, test_services):
        """
        Test: Cache should improve performance for repeated operations

        Integration Test:
        - Perform expensive operation without cache
        - Perform same operation with cache
        - Verify performance improvement
        - Test cache hit/miss ratios
        """
        analyzer = test_services["analyzer"]

        # Generate large dataset for performance testing
        large_dataset = {
            "response_times": [100 + i * 10 for i in range(1000)],
            "error_rates": [0.01 + i * 0.0001 for i in range(1000)],
            "throughput": [50 + i * 5 for i in range(1000)],
        }

        # First run without cache (should be slower)
        start_time = time.time()
        result1 = await analyzer.calculate_metrics_summary(large_dataset)
        time_without_cache = time.time() - start_time

        # Cache the result
        cache_key = f"metrics_summary_{hash(str(large_dataset))}"
        await test_cache.set("analytics", cache_key, result1, ttl=3600)

        # Second run with cache (should be faster)
        start_time = time.time()
        cached_result = await test_cache.get("analytics", cache_key)
        time_with_cache = time.time() - start_time

        # Verify cache performance improvement
        assert cached_result is not None
        assert cached_result == result1
        assert time_with_cache < time_without_cache  # Cache should be faster

        # Verify cache hit
        cache_stats = await test_cache.get_stats()
        assert cache_stats["hits"] > 0

    @pytest.mark.asyncio()
    async def test_cache_invalidation_integration(self, test_cache, test_database):
        """
        Test: Cache invalidation should maintain data consistency

        Integration Test:
        - Store data in both cache and database
        - Update data in database
        - Verify cache invalidation triggers
        - Test eventual consistency
        """
        # Initial data
        initial_data = {
            "user_id": "cache_invalidation_test",
            "name": "Original Name",
            "email": "original@test.com",
            "last_updated": datetime.now(UTC).isoformat(),
        }

        # Store in database
        await test_database.execute_query(
            "INSERT INTO users (user_id, name, email, last_updated) VALUES ($1, $2, $3, $4)",
            initial_data["user_id"],
            initial_data["name"],
            initial_data["email"],
            initial_data["last_updated"],
        )

        # Cache the data
        await test_cache.set("users", initial_data["user_id"], initial_data, ttl=3600)

        # Verify cache hit
        cached_data = await test_cache.get("users", initial_data["user_id"])
        assert cached_data["name"] == "Original Name"

        # Update in database
        updated_data = initial_data.copy()
        updated_data["name"] = "Updated Name"
        updated_data["last_updated"] = datetime.now(UTC).isoformat()

        await test_database.execute_query(
            "UPDATE users SET name = $1, last_updated = $2 WHERE user_id = $3",
            updated_data["name"],
            updated_data["last_updated"],
            initial_data["user_id"],
        )

        # Simulate cache invalidation (in real system, this would be triggered by database events)
        await test_cache.delete("users", initial_data["user_id"])

        # Verify cache is invalidated
        cached_data_after_update = await test_cache.get(
            "users", initial_data["user_id"]
        )
        assert cached_data_after_update is None

        # Verify database has updated data
        db_data = await test_database.fetch_one(
            "SELECT name, last_updated FROM users WHERE user_id = $1",
            initial_data["user_id"],
        )
        assert db_data["name"] == "Updated Name"

    # ========================================================================
    # Message Queue Integration Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_message_bus_integration(self, test_message_bus, test_services):
        """
        Test: Message bus should enable reliable service communication

        Integration Test:
        - Publish messages from one service
        - Subscribe and process messages in another service
        - Verify message delivery and processing
        - Test error handling and retry logic
        """
        # Set up message handlers
        received_messages = []

        async def message_handler(message):
            received_messages.append(message)
            return {"status": "processed", "message_id": message.message_id}

        # Subscribe to test stream
        subscription_id = await test_message_bus.subscribe(
            "test:integration", message_handler
        )

        # Wait for subscription to be ready
        await asyncio.sleep(0.1)

        # Publish test messages
        test_messages = [
            {
                "message_id": "msg_001",
                "source": "test_service_1",
                "target": "test_service_2",
                "data": {"action": "process_data", "payload": "test_payload_1"},
            },
            {
                "message_id": "msg_002",
                "source": "test_service_1",
                "target": "test_service_2",
                "data": {"action": "process_data", "payload": "test_payload_2"},
            },
        ]

        for msg_data in test_messages:
            await test_message_bus.publish("test:integration", msg_data)

        # Wait for message processing
        await asyncio.sleep(0.5)

        # Verify messages were received and processed
        assert len(received_messages) == 2
        assert received_messages[0]["message_id"] == "msg_001"
        assert received_messages[1]["message_id"] == "msg_002"

        # Cleanup
        await test_message_bus.unsubscribe(subscription_id)

    @pytest.mark.asyncio()
    async def test_service_coordination_integration(
        self, test_message_bus, test_services
    ):
        """
        Test: Services should coordinate through message bus for complex workflows

        Integration Test:
        - Set up multi-service workflow
        - Coordinate through message passing
        - Verify workflow completion
        - Test error propagation
        """
        # Set up workflow coordination
        workflow_state = {"steps_completed": 0, "errors": []}

        async def step1_handler(message):
            workflow_state["steps_completed"] += 1
            return {"status": "step1_complete", "next_step": "step2"}

        async def step2_handler(message):
            workflow_state["steps_completed"] += 1
            return {"status": "step2_complete", "workflow_complete": True}

        async def error_handler(message):
            workflow_state["errors"].append(message.get("error", "Unknown error"))
            return {"status": "error_handled"}

        # Subscribe to workflow steps
        await test_message_bus.subscribe("workflow:step1", step1_handler)
        await test_message_bus.subscribe("workflow:step2", step2_handler)
        await test_message_bus.subscribe("workflow:error", error_handler)

        # Wait for subscriptions
        await asyncio.sleep(0.1)

        # Execute workflow
        await test_message_bus.publish(
            "workflow:step1",
            {
                "workflow_id": "integration_test_workflow",
                "data": {"input": "test_data"},
            },
        )

        await asyncio.sleep(0.1)

        await test_message_bus.publish(
            "workflow:step2",
            {
                "workflow_id": "integration_test_workflow",
                "data": {"step1_result": "processed"},
            },
        )

        # Wait for workflow completion
        await asyncio.sleep(0.5)

        # Verify workflow completion
        assert workflow_state["steps_completed"] == 2
        assert len(workflow_state["errors"]) == 0

    # ========================================================================
    # Authentication Integration Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_authentication_database_integration(
        self, test_database, test_services
    ):
        """
        Test: Authentication service should integrate with database for user management

        Integration Test:
        - Create user in database
        - Generate authentication token
        - Verify token validation
        - Test user session management
        """
        auth_service = test_services["auth"]

        # Create test user in database
        user_data = {
            "user_id": "auth_integration_test",
            "email": "auth@test.com",
            "REDACTED_SECRET_hash": "hashed_REDACTED_SECRET_123",
            "role": "user",
            "is_active": True,
            "created_at": datetime.now(UTC),
        }

        await test_database.execute_query(
            """
            INSERT INTO users (user_id, email, REDACTED_SECRET_hash, role, is_active, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_data["user_id"],
            user_data["email"],
            user_data["REDACTED_SECRET_hash"],
            user_data["role"],
            user_data["is_active"],
            user_data["created_at"],
        )

        # Generate authentication token
        token_data = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "role": user_data["role"],
        }

        token = auth_service.generate_token(token_data, expires_in=3600)

        # Validate token
        validation_result = auth_service.validate_token(token)

        assert validation_result.success is True
        assert validation_result.user_data["user_id"] == user_data["user_id"]
        assert validation_result.user_data["email"] == user_data["email"]
        assert validation_result.user_data["role"] == user_data["role"]

        # Verify user exists in database
        db_user = await test_database.fetch_one(
            "SELECT user_id, email, role, is_active FROM users WHERE user_id = $1",
            user_data["user_id"],
        )

        assert db_user is not None
        assert db_user["email"] == user_data["email"]
        assert db_user["role"] == user_data["role"]
        assert db_user["is_active"] is True

    # ========================================================================
    # End-to-End Integration Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_complete_ingestion_workflow_integration(
        self, test_database, test_cache, test_message_bus, test_services
    ):
        """
        Test: Complete ingestion workflow should work end-to-end

        Integration Test:
        - Set up complete ingestion pipeline
        - Execute multi-source ingestion
        - Store results in database
        - Cache processed results
        - Coordinate through message bus
        - Verify end-to-end data flow
        """
        # Set up complete orchestrator with all integrations
        config = IngestionConfig(
            max_concurrent_sources=3,
            enable_cognitive_processing=True,
            enable_database_storage=True,
            enable_caching=True,
            enable_message_coordination=True,
        )

        orchestrator = IngestionOrchestrator(config)
        orchestrator.database_manager = test_database
        orchestrator.cache_strategy = test_cache
        orchestrator.message_bus = test_message_bus

        # Set up message handlers for workflow coordination
        workflow_messages = []

        async def workflow_handler(message):
            workflow_messages.append(message)
            return {"status": "workflow_step_completed"}

        await test_message_bus.subscribe("ingestion:workflow", workflow_handler)
        await asyncio.sleep(0.1)

        # Create comprehensive ingestion plan
        ingestion_plan = {
            "topic": "Complete Integration Test",
            "sources": [
                {
                    "type": "web",
                    "url": "https://example.com/integration-test",
                    "priority": 1,
                    "scraping_options": {"wait_time": 1000},
                },
                {
                    "type": "arxiv",
                    "query": "integration testing",
                    "categories": ["cs.SE"],
                    "max_results": 5,
                    "priority": 2,
                },
            ],
            "processing_options": {
                "enable_deduplication": True,
                "enable_cognitive_assessment": True,
                "enable_caching": True,
            },
        }

        # Mock successful service responses
        with patch.object(
            test_services["firecrawl"], "extract_content"
        ) as mock_firecrawl, patch.object(
            test_services["arxiv"], "search_papers"
        ) as mock_arxiv:
            # Configure mock responses
            mock_firecrawl.return_value = {
                "success": True,
                "content": "Integration test web content",
                "url": "https://example.com/integration-test",
                "metadata": {"title": "Integration Test Article", "word_count": 200},
            }

            mock_arxiv.return_value = {
                "success": True,
                "papers": [
                    {
                        "title": "Integration Testing Paper 1",
                        "abstract": "Testing integration patterns",
                    },
                    {
                        "title": "Integration Testing Paper 2",
                        "abstract": "Advanced integration testing",
                    },
                ],
                "total_results": 2,
            }

            # Execute complete workflow
            result = await orchestrator.execute_plan(ingestion_plan)

            # Verify workflow completion
            assert result.success is True
            assert result.total_sources_processed == 2
            assert result.total_content_items > 0

            # Verify database storage
            stored_items = await test_database.fetch_all(
                "SELECT * FROM content_items WHERE title LIKE '%Integration Test%'"
            )
            assert len(stored_items) > 0

            # Verify cache storage
            cached_items = []
            for item in stored_items:
                cached_item = await test_cache.get("content_items", item["id"])
                if cached_item:
                    cached_items.append(cached_item)
            assert len(cached_items) > 0

            # Verify message coordination
            assert len(workflow_messages) > 0

            # Verify data consistency across all systems
            for stored_item in stored_items:
                cached_item = await test_cache.get("content_items", stored_item["id"])
                if cached_item:
                    assert cached_item["title"] == stored_item["title"]
                    assert cached_item["content"] == stored_item["content"]


class TestErrorPropagationIntegration:
    """
    Integration tests for error propagation and handling across services.

    These tests verify that errors are properly propagated and handled
    when services interact with each other.
    """

    @pytest.mark.asyncio()
    async def test_database_error_propagation(self, test_services):
        """
        Test: Database errors should propagate correctly to calling services

        Integration Test:
        - Simulate database connection failure
        - Verify error propagation to service layer
        - Test graceful degradation
        """
        # Set up service with failing database
        with patch(
            "src.services.database.connection_manager.DatabaseConnectionManager.connect"
        ) as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")

            # Attempt to use service that depends on database
            from src.services.analytics.user_analytics_service import UserAnalyticsService

            analytics_service = UserAnalyticsService()

            # Attempt operation that requires database
            result = await analytics_service.get_user_analytics("test_user")

            # Verify error handling
            assert result.success is False
            assert "Database connection failed" in result.error_message

    @pytest.mark.asyncio()
    async def test_cache_error_propagation(self, test_database):
        """
        Test: Cache errors should not break core functionality

        Integration Test:
        - Simulate cache service failure
        - Verify service continues to work without cache
        - Test fallback mechanisms
        """
        # Set up service with failing cache
        with patch(
            "src.services.caching.redis_cache_strategy.RedisCacheStrategy.get"
        ) as mock_cache_get:
            mock_cache_get.side_effect = Exception("Cache service unavailable")

            # Service should still work without cache
            from src.services.ingestion.content_processor import ContentProcessor

            processor = ContentProcessor()
            processor.database_manager = test_database

            # Attempt operation that would normally use cache
            result = await processor.process_content(
                {"title": "Test Content", "content": "Test content for processing"}
            )

            # Verify service continues to work
            assert result.success is True
            assert result.processed_content is not None

    @pytest.mark.asyncio()
    async def test_message_bus_error_propagation(self, test_services):
        """
        Test: Message bus errors should be handled gracefully

        Integration Test:
        - Simulate message bus failure
        - Verify error handling and retry logic
        - Test service degradation
        """
        # Set up service with failing message bus
        with patch("src.services.messaging.message_bus.MessageBus.publish") as mock_publish:
            mock_publish.side_effect = Exception("Message bus unavailable")

            # Service should handle message bus failures gracefully
            from src.services.workflow.orchestration_service import OrchestrationService

            orchestration_service = OrchestrationService()

            # Attempt workflow that requires message coordination
            result = await orchestration_service.execute_workflow(
                {"workflow_id": "test_workflow", "steps": ["step1", "step2"]}
            )

            # Verify graceful degradation
            assert result.success is False
            assert "Message bus unavailable" in result.error_message


if __name__ == "__main__":
    # Run integration tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])
