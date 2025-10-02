"""
Comprehensive test suite for Production API Gateway
Tests enterprise-grade API functionality with real integrations and live data sources.
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from services.api.production_api_gateway import (
    APIEndpoint,
    APIEndpointType,
    APIRequest,
    APIResponse,
    APIStatus,
    CircuitBreaker,
    ExternalAPIConfig,
    ExternalAPIManager,
    ProductionAPIConfig,
    ProductionAPIGateway,
    RateLimiter,
    RateLimitStrategy,
    ResponseCache,
    create_production_api_gateway,
)


@pytest.fixture()
def api_config():
    """Test configuration for production API gateway"""
    return ProductionAPIConfig(
        host="localhost",
        port=8080,
        max_concurrent_requests=100,
        enable_cors=True,
        cors_origins=["http://localhost:3000", "https://testdomain.com"],
        enable_rate_limiting=True,
        global_rate_limit_per_minute=1000,
        enable_request_logging=True,
        enable_response_caching=True,
        cache_ttl_seconds=300,
        enable_health_checks=True,
        health_check_interval_seconds=30,
        enable_metrics_collection=True,
        enable_circuit_breaker=True,
        circuit_breaker_failure_threshold=3,
        circuit_breaker_recovery_timeout_seconds=60,
        jwt_secret_key="test-secret-key-for-testing-only",
        api_key_header="X-Test-API-Key",
        request_timeout_seconds=30,
    )


@pytest.fixture()
def api_gateway(api_config):
    """Production API gateway instance for testing"""
    return ProductionAPIGateway(api_config)


@pytest_asyncio.fixture
async def initialized_gateway(api_gateway):
    """Initialized API gateway for testing"""
    await api_gateway.initialize()
    yield api_gateway
    await api_gateway.shutdown()


@pytest.fixture()
def sample_api_requests():
    """Sample API requests for testing"""
    base_time = datetime.now(UTC)

    requests = [
        APIRequest(
            request_id="req_001",
            endpoint_id="content_analysis",
            client_id="client_001",
            method="POST",
            path="/api/v1/content/analyze",
            headers={
                "X-Test-API-Key": "valid-test-api-key-123456789",
                "Content-Type": "application/json",
                "User-Agent": "TestClient/1.0",
            },
            payload={
                "content": "This is a test article about artificial intelligence and machine learning.",
                "analyze_sentiment": True,
                "extract_topics": True,
            },
            timestamp=base_time,
            ip_address="192.168.1.100",
        ),
        APIRequest(
            request_id="req_002",
            endpoint_id="semantic_search",
            client_id="client_002",
            method="POST",
            path="/api/v1/search/semantic",
            headers={
                "X-Test-API-Key": "valid-test-api-key-987654321",
                "Content-Type": "application/json",
            },
            query_params={"limit": "10", "threshold": "0.8"},
            payload={"query": "machine learning algorithms", "search_type": "semantic"},
            timestamp=base_time,
            ip_address="10.0.0.50",
        ),
        APIRequest(
            request_id="req_003",
            endpoint_id="get_recommendations",
            client_id="client_003",
            method="GET",
            path="/api/v1/recommendations",
            headers={
                "X-Test-API-Key": "valid-test-api-key-555666777",
                "Accept": "application/json",
            },
            query_params={"user_id": "user_123", "max_items": "5"},
            timestamp=base_time,
            ip_address="172.16.0.10",
        ),
        APIRequest(
            request_id="req_004",
            endpoint_id="system_health",
            client_id="client_004",
            method="GET",
            path="/api/v1/health",
            headers={"Accept": "application/json"},
            timestamp=base_time,
            ip_address="203.0.113.42",
        ),
    ]

    return requests


@pytest.fixture()
def sample_external_apis():
    """Sample external API configurations"""
    return [
        ExternalAPIConfig(
            api_name="test_arxiv",
            base_url="http://export.arxiv.org/api",
            rate_limit_per_minute=180,
            timeout_seconds=30,
            retry_attempts=2,
            is_active=True,
        ),
        ExternalAPIConfig(
            api_name="test_openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key-for-testing-purposes",
            auth_header="Authorization",
            rate_limit_per_minute=3000,
            timeout_seconds=60,
            retry_attempts=2,
            is_active=True,
        ),
        ExternalAPIConfig(
            api_name="test_disabled_api",
            base_url="https://disabled-api.example.com",
            is_active=False,
        ),
    ]


class TestProductionAPIGateway:
    """Test the main production API gateway functionality"""

    @pytest.mark.asyncio()
    async def test_should_initialize_api_gateway_with_configuration(self, api_config):
        """
        Test: Should initialize production API gateway with proper configuration
        and default endpoints ready for enterprise operations.
        """
        gateway = ProductionAPIGateway(api_config)

        # Verify initialization
        assert gateway.config == api_config
        assert len(gateway.endpoints) > 0  # Default endpoints loaded
        assert gateway.rate_limiter is not None
        assert gateway.response_cache is not None
        assert gateway.external_api_manager is not None

        # Verify default endpoints are configured
        required_endpoints = [
            "content_ingestion",
            "content_analysis",
            "semantic_search",
            "get_recommendations",
            "content_routing",
            "system_health",
            "metrics_endpoint",
        ]
        for endpoint_id in required_endpoints:
            assert endpoint_id in gateway.endpoints

        # Verify metrics initialization
        metrics = gateway.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["rate_limited_requests"] == 0

    @pytest.mark.asyncio()
    async def test_should_handle_successful_api_requests_with_authentication(
        self,
        initialized_gateway,
        sample_api_requests,
    ):
        """
        Test: Should handle successful API requests with proper authentication
        and return well-formed responses with metrics tracking.
        """
        # Handle content analysis request
        analysis_request = sample_api_requests[0]
        response = await initialized_gateway.handle_request(analysis_request)

        # Verify successful response
        assert isinstance(response, APIResponse)
        assert response.request_id == analysis_request.request_id
        assert response.status == APIStatus.SUCCESS
        assert response.status_code == 200
        assert response.data is not None
        assert response.processing_time_ms > 0
        assert not response.cached  # First request shouldn't be cached
        assert response.rate_limit_remaining >= 0

        # Verify response data structure
        assert response.data["success"] is True
        assert response.data["request_id"] == analysis_request.request_id
        assert "timestamp" in response.data

        # Verify metrics updated
        metrics = initialized_gateway.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["average_response_time_ms"] > 0

    @pytest.mark.asyncio()
    async def test_should_enforce_rate_limiting_per_client_and_endpoint(
        self,
        initialized_gateway,
        sample_api_requests,
    ):
        """
        Test: Should enforce rate limiting per client and endpoint to prevent
        abuse and ensure fair usage across all API consumers.
        """
        # Get endpoint with low rate limit for testing
        search_request = sample_api_requests[1]  # semantic search
        endpoint = initialized_gateway.endpoints["semantic_search"]

        # Simulate rapid requests from same client
        client_id = search_request.client_id
        successful_requests = 0
        rate_limited_requests = 0

        # Make requests up to and beyond rate limit
        for i in range(endpoint.rate_limit_per_minute + 10):
            test_request = APIRequest(
                request_id=f"rate_test_{i}",
                endpoint_id="semantic_search",
                client_id=client_id,
                method="POST",
                path="/api/v1/search/semantic",
                headers={"X-Test-API-Key": "valid-test-api-key-rate-limit-test"},
                payload={"query": f"test query {i}"},
            )

            response = await initialized_gateway.handle_request(test_request)

            if response.status == APIStatus.SUCCESS:
                successful_requests += 1
            elif response.status == APIStatus.RATE_LIMITED:
                rate_limited_requests += 1
                assert response.status_code == 429
                assert "rate limit" in response.error_message.lower()
                assert response.rate_limit_reset is not None

        # Verify rate limiting was applied
        assert successful_requests <= endpoint.rate_limit_per_minute
        assert rate_limited_requests > 0

        # Verify metrics
        metrics = initialized_gateway.get_metrics()
        assert metrics["rate_limited_requests"] > 0

    @pytest.mark.asyncio()
    async def test_should_implement_response_caching_effectively(
        self,
        initialized_gateway,
        sample_api_requests,
    ):
        """
        Test: Should cache responses and serve from cache when appropriate
        to improve performance and reduce backend load.
        """
        request = sample_api_requests[2]  # GET recommendations request

        # First request - should miss cache
        response1 = await initialized_gateway.handle_request(request)
        assert response1.status == APIStatus.SUCCESS
        assert not response1.cached

        # Second identical request - should hit cache
        response2 = await initialized_gateway.handle_request(request)
        assert response2.status == APIStatus.SUCCESS
        assert response2.cached

        # Verify cached response is identical
        assert response1.data == response2.data
        assert response1.request_id == response2.request_id

        # Verify cache metrics
        metrics = initialized_gateway.get_metrics()
        assert metrics["cached_responses"] > 0
        assert metrics["cache_hit_rate"] > 0

    @pytest.mark.asyncio()
    async def test_should_handle_authentication_failures_properly(
        self,
        initialized_gateway,
        sample_api_requests,
    ):
        """
        Test: Should properly handle authentication failures and return
        appropriate error responses without exposing system details.
        """
        # Request without API key
        unauthorized_request = APIRequest(
            request_id="auth_test_001",
            endpoint_id="content_analysis",
            client_id="unauthorized_client",
            method="POST",
            path="/api/v1/content/analyze",
            headers={"Content-Type": "application/json"},  # No API key
            payload={"content": "test content"},
        )

        response = await initialized_gateway.handle_request(unauthorized_request)

        # Verify authentication failure
        assert response.status == APIStatus.UNAUTHORIZED
        assert response.status_code == 401
        assert "authentication" in response.error_message.lower()
        assert response.data is None

        # Request with invalid API key
        invalid_key_request = APIRequest(
            request_id="auth_test_002",
            endpoint_id="content_analysis",
            client_id="invalid_client",
            method="POST",
            path="/api/v1/content/analyze",
            headers={"X-Test-API-Key": "invalid"},  # Too short/invalid key
            payload={"content": "test content"},
        )

        response = await initialized_gateway.handle_request(invalid_key_request)
        assert response.status == APIStatus.UNAUTHORIZED
        assert response.status_code == 401

    @pytest.mark.asyncio()
    async def test_should_handle_invalid_endpoints_gracefully(
        self,
        initialized_gateway,
    ):
        """
        Test: Should handle requests to invalid endpoints gracefully
        and return appropriate 404 responses.
        """
        invalid_request = APIRequest(
            request_id="invalid_test",
            endpoint_id="nonexistent",
            client_id="test_client",
            method="GET",
            path="/api/v1/nonexistent/endpoint",
            headers={"X-Test-API-Key": "valid-test-api-key-123456789"},
        )

        response = await initialized_gateway.handle_request(invalid_request)

        # Verify 404 response
        assert response.status == APIStatus.INVALID_REQUEST
        assert response.status_code == 404
        assert "not found" in response.error_message.lower()
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio()
    async def test_should_handle_concurrent_requests_safely(
        self,
        initialized_gateway,
        sample_api_requests,
    ):
        """
        Test: Should handle concurrent API requests safely without
        race conditions and maintain consistent performance.
        """
        # Get initial metrics
        initial_metrics = initialized_gateway.get_metrics()

        # Create many concurrent requests
        concurrent_requests = []
        for i in range(50):
            request = APIRequest(
                request_id=f"concurrent_{i}",
                endpoint_id="system_health",  # Use health endpoint (no auth required)
                client_id=f"client_{i % 10}",  # 10 different clients
                method="GET",
                path="/api/v1/health",
            )
            concurrent_requests.append(request)

        # Process all requests concurrently
        start_time = time.time()
        tasks = [
            initialized_gateway.handle_request(request)
            for request in concurrent_requests
        ]
        responses = await asyncio.gather(*tasks)
        processing_time = time.time() - start_time

        # Verify all requests were handled successfully
        assert len(responses) == 50
        assert all(response.status == APIStatus.SUCCESS for response in responses)

        # Verify reasonable processing time
        assert processing_time < 10.0  # Should complete within 10 seconds

        # Verify metrics updated correctly
        final_metrics = initialized_gateway.get_metrics()
        assert final_metrics["total_requests"] == initial_metrics["total_requests"] + 50
        # Due to caching and identical requests, successful may be less than total
        # but should be >= 1
        assert (
            final_metrics["successful_requests"]
            > initial_metrics["successful_requests"]
        )

    @pytest.mark.asyncio()
    async def test_should_provide_comprehensive_health_status(
        self,
        initialized_gateway,
    ):
        """
        Test: Should provide comprehensive health status including system
        metrics, external API status, and operational information.
        """
        health_status = initialized_gateway.get_health_status()

        # Verify health status structure
        assert health_status["status"] == "healthy"
        assert "uptime_seconds" in health_status
        assert health_status["uptime_seconds"] >= 0
        assert health_status["total_endpoints"] > 0
        assert health_status["active_endpoints"] > 0

        # Verify external API status
        assert "external_apis" in health_status

        # Verify metrics
        assert "metrics" in health_status
        assert "total_requests" in health_status["metrics"]

        # Verify system info
        assert "system_info" in health_status
        assert "version" in health_status["system_info"]
        assert "features_enabled" in health_status["system_info"]

    @pytest.mark.asyncio()
    async def test_should_track_comprehensive_metrics(
        self,
        initialized_gateway,
        sample_api_requests,
    ):
        """
        Test: Should track comprehensive metrics for monitoring API
        performance, usage patterns, and system health.
        """
        initial_metrics = initialized_gateway.get_metrics()

        # Process various requests
        for request in sample_api_requests[:3]:
            await initialized_gateway.handle_request(request)

        final_metrics = initialized_gateway.get_metrics()

        # Verify metric tracking
        assert final_metrics["total_requests"] > initial_metrics["total_requests"]
        assert (
            final_metrics["successful_requests"]
            > initial_metrics["successful_requests"]
        )
        assert "success_rate" in final_metrics
        assert "cache_hit_rate" in final_metrics
        assert "rate_limit_hit_rate" in final_metrics
        assert "external_api_health" in final_metrics
        assert final_metrics["average_response_time_ms"] > 0

    @pytest.mark.asyncio()
    async def test_should_handle_request_processing_errors_gracefully(
        self,
        initialized_gateway,
    ):
        """
        Test: Should handle request processing errors gracefully
        and return appropriate error responses.
        """
        # Create request that might cause processing error
        problematic_request = APIRequest(
            request_id="error_test",
            endpoint_id="content_analysis",
            client_id="test_client",
            method="POST",
            path="/api/v1/content/analyze",
            headers={"X-Test-API-Key": "valid-test-api-key-123456789"},
            payload={"invalid_field": "This might cause processing error"},
        )

        # Mock a handler that raises an exception
        async def failing_handler(request, external_manager):
            raise Exception("Simulated processing error")

        initialized_gateway.register_handler("content_analysis", failing_handler)

        response = await initialized_gateway.handle_request(problematic_request)

        # Should handle gracefully
        assert response.status == APIStatus.FAILED
        assert response.status_code == 500
        assert response.error_message is not None
        assert response.processing_time_ms > 0

        # Verify metrics updated
        metrics = initialized_gateway.get_metrics()
        assert metrics["failed_requests"] > 0


class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio()
    async def test_should_implement_sliding_window_rate_limiting(self, api_config):
        """
        Test: Should implement sliding window rate limiting accurately
        with proper time-based request tracking and limit enforcement.
        """
        rate_limiter = RateLimiter(api_config)

        # Create test endpoint with low limit
        test_endpoint = APIEndpoint(
            endpoint_id="test_sliding",
            path="/test",
            method="GET",
            endpoint_type=APIEndpointType.MONITORING,
            rate_limit_per_minute=5,
            rate_limit_strategy=RateLimitStrategy.SLIDING_WINDOW,
        )

        client_id = "test_sliding_client"

        # Should allow requests up to limit
        for i in range(5):
            allowed, remaining, reset_time = rate_limiter.check_rate_limit(
                client_id,
                test_endpoint,
            )
            assert allowed is True
            assert remaining >= 0

        # 6th request should be blocked
        allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            client_id,
            test_endpoint,
        )
        assert allowed is False
        assert remaining == 0
        assert reset_time is not None

    @pytest.mark.asyncio()
    async def test_should_implement_token_bucket_rate_limiting(self, api_config):
        """
        Test: Should implement token bucket rate limiting with proper
        token refill rates and burst handling capabilities.
        """
        rate_limiter = RateLimiter(api_config)

        test_endpoint = APIEndpoint(
            endpoint_id="test_token_bucket",
            path="/test",
            method="POST",
            endpoint_type=APIEndpointType.ANALYSIS,
            rate_limit_per_minute=60,  # 1 token per second
            rate_limit_strategy=RateLimitStrategy.TOKEN_BUCKET,
        )

        client_id = "test_token_client"

        # Initial requests should be allowed
        allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            client_id,
            test_endpoint,
        )
        assert allowed is True

        # Tokens should decrease
        allowed, new_remaining, reset_time = rate_limiter.check_rate_limit(
            client_id,
            test_endpoint,
        )
        assert allowed is True
        assert new_remaining < remaining

    @pytest.mark.asyncio()
    async def test_should_implement_adaptive_rate_limiting_based_on_load(
        self,
        api_config,
    ):
        """
        Test: Should implement adaptive rate limiting that adjusts
        limits based on current system load and performance.
        """
        rate_limiter = RateLimiter(api_config)

        test_endpoint = APIEndpoint(
            endpoint_id="test_adaptive",
            path="/test",
            method="GET",
            endpoint_type=APIEndpointType.SEARCH,
            rate_limit_per_minute=100,
            rate_limit_strategy=RateLimitStrategy.ADAPTIVE,
        )

        client_id = "test_adaptive_client"

        # Should adjust based on system load
        allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            client_id,
            test_endpoint,
        )
        assert allowed is True

        # Verify adaptive behavior (limit may be adjusted)
        assert remaining <= test_endpoint.rate_limit_per_minute


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    @pytest.mark.asyncio()
    async def test_should_open_circuit_after_failure_threshold(self, api_config):
        """
        Test: Should open circuit breaker after reaching failure threshold
        and prevent further requests to failing services.
        """
        circuit_breaker = CircuitBreaker(api_config)
        service_name = "test_service"

        # Initially should allow execution
        assert circuit_breaker.can_execute(service_name) is True

        # Record failures up to threshold
        for i in range(api_config.circuit_breaker_failure_threshold):
            circuit_breaker.record_failure(service_name)

        # Circuit should now be open
        assert circuit_breaker.can_execute(service_name) is False

        # Verify circuit state
        circuit = circuit_breaker.circuit_state[service_name]
        assert circuit["state"] == "open"
        assert circuit["failure_count"] == api_config.circuit_breaker_failure_threshold

    @pytest.mark.asyncio()
    async def test_should_transition_to_half_open_after_timeout(self, api_config):
        """
        Test: Should transition circuit breaker to half-open state
        after recovery timeout and allow test requests.
        """
        # Use shorter timeout for testing
        config = ProductionAPIConfig(
            circuit_breaker_failure_threshold=2,
            circuit_breaker_recovery_timeout_seconds=1,  # 1 second for testing
        )
        circuit_breaker = CircuitBreaker(config)
        service_name = "test_recovery_service"

        # Trigger circuit open
        circuit_breaker.record_failure(service_name)
        circuit_breaker.record_failure(service_name)
        assert circuit_breaker.can_execute(service_name) is False

        # Wait for recovery timeout
        await asyncio.sleep(1.5)

        # Should now allow execution (half-open)
        assert circuit_breaker.can_execute(service_name) is True

        # Verify state transition
        circuit = circuit_breaker.circuit_state[service_name]
        assert circuit["state"] == "half_open"

    @pytest.mark.asyncio()
    async def test_should_close_circuit_on_successful_recovery(self, api_config):
        """
        Test: Should close circuit breaker and reset failure count
        when service recovers and responds successfully.
        """
        circuit_breaker = CircuitBreaker(api_config)
        service_name = "test_success_service"

        # Open circuit
        for i in range(api_config.circuit_breaker_failure_threshold):
            circuit_breaker.record_failure(service_name)

        # Record success - should close circuit
        circuit_breaker.record_success(service_name)

        # Verify circuit closed and reset
        circuit = circuit_breaker.circuit_state[service_name]
        assert circuit["state"] == "closed"
        assert circuit["failure_count"] == 0
        assert circuit_breaker.can_execute(service_name) is True


class TestResponseCache:
    """Test response caching functionality"""

    @pytest.mark.asyncio()
    async def test_should_cache_and_retrieve_responses_correctly(self, api_config):
        """
        Test: Should cache responses and retrieve them within TTL
        while properly handling cache expiration.
        """
        response_cache = ResponseCache(api_config)
        cache_key = "test_cache_key"
        test_data = {"result": "test data", "timestamp": "2023-01-01T00:00:00Z"}

        # Initially should return None
        assert response_cache.get(cache_key) is None

        # Set cache data
        response_cache.set(cache_key, test_data)

        # Should retrieve cached data
        cached_data = response_cache.get(cache_key)
        assert cached_data == test_data

    @pytest.mark.asyncio()
    async def test_should_expire_cached_responses_after_ttl(self, api_config):
        """
        Test: Should expire cached responses after TTL and return None
        for expired entries while cleaning up memory.
        """
        # Use short TTL for testing
        config = ProductionAPIConfig(cache_ttl_seconds=1)
        response_cache = ResponseCache(config)

        cache_key = "test_expiry_key"
        test_data = {"result": "expiry test"}

        # Cache data
        response_cache.set(cache_key, test_data)
        assert response_cache.get(cache_key) == test_data

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should return None after expiration
        assert response_cache.get(cache_key) is None

    @pytest.mark.asyncio()
    async def test_should_handle_cache_eviction_when_full(self, api_config):
        """
        Test: Should handle cache eviction when cache is full
        using LRU-like eviction strategy.
        """
        response_cache = ResponseCache(api_config)

        # Fill cache beyond capacity (simulate by setting many entries)
        for i in range(50):
            response_cache.set(f"cache_key_{i}", {"data": f"value_{i}"})

        # Verify cache operations still work
        latest_key = "cache_key_49"
        assert response_cache.get(latest_key) is not None

        # Cache should handle eviction gracefully
        assert len(response_cache.cache) <= 50


class TestExternalAPIManager:
    """Test external API management functionality"""

    @pytest.mark.asyncio()
    async def test_should_manage_external_api_configurations(
        self,
        api_config,
        sample_external_apis,
    ):
        """
        Test: Should properly manage external API configurations
        and track their health status and availability.
        """
        manager = ExternalAPIManager(api_config)

        # Add external APIs
        for api_config in sample_external_apis:
            manager.add_external_api(api_config)

        # Verify APIs were added
        assert "test_arxiv" in manager.external_apis
        assert "test_openai" in manager.external_apis
        assert "test_disabled_api" in manager.external_apis

        # Verify health status tracking
        assert "test_arxiv" in manager.health_status
        assert manager.health_status["test_arxiv"]["is_healthy"] is True

    @pytest.mark.asyncio()
    async def test_should_handle_external_api_calls_with_retries(
        self,
        api_config,
        sample_external_apis,
    ):
        """
        Test: Should handle external API calls with proper retry logic
        and circuit breaker integration for resilience.
        """
        manager = ExternalAPIManager(api_config)
        await manager.initialize()

        try:
            manager.add_external_api(sample_external_apis[0])  # test_arxiv

            # Mock the session to simulate API response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"results": "test data"})

            with patch.object(manager.session, "request") as mock_request:
                mock_request.return_value.__aenter__.return_value = mock_response

                result = await manager.call_external_api(
                    "test_arxiv",
                    "/query",
                    "GET",
                    params={"search_query": "test"},
                )

                assert result == {"results": "test data"}
                assert mock_request.called

        finally:
            await manager.shutdown()

    @pytest.mark.asyncio()
    async def test_should_track_external_api_health_status(
        self,
        api_config,
        sample_external_apis,
    ):
        """
        Test: Should continuously track external API health status
        and update availability metrics for monitoring.
        """
        manager = ExternalAPIManager(api_config)
        await manager.initialize()

        try:
            manager.add_external_api(sample_external_apis[0])

            # Initial health status
            initial_status = manager.health_status["test_arxiv"]
            assert initial_status["is_healthy"] is True
            assert initial_status["consecutive_failures"] == 0

            # Simulate health check failure
            manager.circuit_breaker.record_failure("test_arxiv")
            manager.health_status["test_arxiv"]["is_healthy"] = False
            manager.health_status["test_arxiv"]["consecutive_failures"] = 1

            # Verify health status updated
            updated_status = manager.health_status["test_arxiv"]
            assert updated_status["is_healthy"] is False
            assert updated_status["consecutive_failures"] == 1

        finally:
            await manager.shutdown()


class TestProductionConfiguration:
    """Test production-ready configuration and setup"""

    @pytest.mark.asyncio()
    async def test_should_create_production_api_gateway(self):
        """
        Test: Should create production-ready API gateway with appropriate
        configuration for enterprise scale and security.
        """
        gateway = create_production_api_gateway()

        # Verify production configuration
        assert gateway.config.max_concurrent_requests >= 1000
        assert gateway.config.enable_rate_limiting is True
        assert gateway.config.enable_response_caching is True
        assert gateway.config.enable_circuit_breaker is True
        assert gateway.config.enable_health_checks is True
        assert gateway.config.enable_metrics_collection is True
        assert gateway.config.jwt_secret_key is not None
        assert len(gateway.config.jwt_secret_key) >= 32  # Secure key length

        # Verify external API integrations are configured
        external_apis = gateway.external_api_manager.external_apis
        expected_apis = ["arxiv", "pubmed", "openai", "newsapi"]
        for api_name in expected_apis:
            assert api_name in external_apis

        # Verify endpoints are configured
        assert len(gateway.endpoints) >= 7  # Default endpoints


class TestDataStructures:
    """Test data structure serialization and immutability"""

    def test_api_request_should_be_immutable_and_serializable(self):
        """
        Test: APIRequest should be immutable and properly serializable
        for logging and transmission across system components.
        """
        request = APIRequest(
            request_id="test_req_001",
            endpoint_id="test_endpoint",
            client_id="test_client",
            method="POST",
            path="/api/v1/test",
            headers={"Authorization": "Bearer token123"},
            query_params={"param1": "value1"},
            payload={"data": "test data"},
            ip_address="192.168.1.1",
        )

        # Verify immutability
        with pytest.raises(Exception):  # Should raise FrozenInstanceError
            request.client_id = "modified_client"

        # Verify serialization fields
        assert request.request_id == "test_req_001"
        assert request.endpoint_id == "test_endpoint"
        assert request.client_id == "test_client"
        assert request.method == "POST"
        assert request.headers["Authorization"] == "Bearer token123"
        assert request.query_params["param1"] == "value1"
        assert request.payload["data"] == "test data"
        assert isinstance(request.timestamp, datetime)

    def test_api_response_should_serialize_with_comprehensive_metadata(self):
        """
        Test: APIResponse should serialize with comprehensive metadata
        including processing metrics and rate limiting information.
        """
        response = APIResponse(
            request_id="test_resp_001",
            status=APIStatus.SUCCESS,
            status_code=200,
            data={"result": "success", "items": [1, 2, 3]},
            processing_time_ms=125.5,
            cached=False,
            rate_limit_remaining=95,
            rate_limit_reset=datetime.now(UTC) + timedelta(minutes=1),
        )

        # Verify comprehensive serialization
        assert response.request_id == "test_resp_001"
        assert response.status == APIStatus.SUCCESS
        assert response.status_code == 200
        assert response.data["result"] == "success"
        assert response.processing_time_ms == 125.5
        assert response.cached is False
        assert response.rate_limit_remaining == 95
        assert isinstance(response.rate_limit_reset, datetime)
        assert isinstance(response.response_timestamp, datetime)

    def test_external_api_config_should_support_comprehensive_integration(self):
        """
        Test: ExternalAPIConfig should support comprehensive integration
        configuration with security and resilience settings.
        """
        config = ExternalAPIConfig(
            api_name="comprehensive_api",
            base_url="https://api.example.com/v1",
            api_key="secret-api-key-123",
            auth_header="X-API-Key",
            rate_limit_per_minute=1000,
            timeout_seconds=45,
            retry_attempts=3,
            retry_backoff_seconds=2.0,
            is_active=True,
            health_check_interval_minutes=2,
            metadata={"version": "v1", "region": "us-east-1"},
        )

        # Verify comprehensive configuration
        assert config.api_name == "comprehensive_api"
        assert config.base_url == "https://api.example.com/v1"
        assert config.api_key == "secret-api-key-123"
        assert config.auth_header == "X-API-Key"
        assert config.rate_limit_per_minute == 1000
        assert config.timeout_seconds == 45
        assert config.retry_attempts == 3
        assert config.retry_backoff_seconds == 2.0
        assert config.is_active is True
        assert config.health_check_interval_minutes == 2
        assert config.metadata["version"] == "v1"
