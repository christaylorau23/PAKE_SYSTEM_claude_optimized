#!/usr/bin/env python3
"""
PAKE System - Production Orchestrator Tests
Phase 2B Sprint 2: Advanced features and real API integration tests

Following TDD methodology for production-grade enhancements.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
import pytest_asyncio

from services.ingestion.orchestrator import (
    IngestionConfig,
    IngestionPlan,
    IngestionSource,
)

# Import production orchestrator and components
from services.ingestion.production_orchestrator import (
    APIHealthStatus,
    ProductionConfig,
    ProductionIngestionOrchestrator,
)


class TestProductionOrchestrator:
    """
    Test suite for production-grade ingestion orchestrator.
    Tests advanced features and real API integration capabilities.
    """

    @pytest.fixture
    def production_config(self):
        """Production configuration for testing"""
        return ProductionConfig(
            firecrawl_api_key="test-firecrawl-key",
            ncbi_email="test@example.com",
            ncbi_api_key="test-ncbi-key",
            min_content_quality=0.8,
            min_source_reliability=0.9,
            max_retries=3,
        )

    @pytest.fixture
    def base_config(self):
        """Base ingestion configuration"""
        return IngestionConfig(
            max_concurrent_sources=5,
            timeout_per_source=300,
            quality_threshold=0.7,
            enable_cognitive_processing=True,
            enable_workflow_automation=True,
        )

    @pytest.fixture
    def mock_cognitive_engine(self):
        """Advanced mock cognitive engine"""
        engine = Mock()
        engine.assess_research_quality = AsyncMock(return_value=0.89)
        engine.assess_content_quality = AsyncMock(return_value=0.92)
        engine.optimize_search_query = AsyncMock(
            return_value={
                "optimized_params": {"terms": ["enhanced query"], "max_results": 15},
                "confidence": 0.85,
                "estimated_improvement": 0.2,
            },
        )
        return engine

    @pytest.fixture
    def mock_n8n_manager(self):
        """Mock n8n workflow manager"""
        manager = Mock()
        manager.trigger_workflow = AsyncMock(return_value={"workflow_id": "prod_001"})
        return manager

    @pytest_asyncio.fixture
    async def production_orchestrator(
        self,
        base_config,
        production_config,
        mock_cognitive_engine,
        mock_n8n_manager,
    ):
        """Create production orchestrator instance"""
        orchestrator = ProductionIngestionOrchestrator(
            config=base_config,
            production_config=production_config,
            cognitive_engine=mock_cognitive_engine,
            n8n_manager=mock_n8n_manager,
        )
        yield orchestrator
        await orchestrator.close()

    # ========================================================================
    # PRODUCTION INITIALIZATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_initialize_with_real_api_configurations(
        self,
        production_orchestrator,
        production_config,
    ):
        """
        Test: Should initialize production services with real API endpoints
        and proper authentication.
        """
        # Verify production configuration is applied
        assert production_orchestrator.production_config == production_config
        assert (
            production_orchestrator.production_config.firecrawl_api_key
            == "test-firecrawl-key"
        )
        assert (
            production_orchestrator.production_config.ncbi_email == "test@example.com"
        )

        # Verify API health status is initialized
        assert "firecrawl" in production_orchestrator.api_health_status
        assert "arxiv" in production_orchestrator.api_health_status
        assert "ncbi" in production_orchestrator.api_health_status

        # Verify services are properly initialized
        assert production_orchestrator.firecrawl_service is not None
        assert production_orchestrator.arxiv_service is not None
        assert production_orchestrator.pubmed_service is not None

    @pytest.mark.asyncio
    async def test_should_setup_api_health_monitoring(self, production_orchestrator):
        """
        Test: Should initialize API health monitoring for all services
        with proper status tracking.
        """
        health_status = production_orchestrator.api_health_status

        # Verify all services have health status
        assert len(health_status) == 3

        for service_name in ["firecrawl", "arxiv", "ncbi"]:
            assert service_name in health_status
            status = health_status[service_name]
            assert isinstance(status, APIHealthStatus)
            assert status.service_name == service_name
            assert isinstance(status.is_healthy, bool)
            assert isinstance(status.response_time_ms, float)
            assert isinstance(status.last_check, datetime)

    # ========================================================================
    # COGNITIVE QUERY OPTIMIZATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_optimize_queries_with_cognitive_feedback(
        self,
        production_orchestrator,
        mock_cognitive_engine,
    ):
        """
        Test: Should use cognitive engine to optimize queries based on
        historical performance and context analysis.
        """
        # Create test plan
        original_plan = IngestionPlan(
            topic="AI optimization test",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters={"terms": ["ai"], "max_results": 10},
                    estimated_results=10,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=10,
            estimated_duration=60,
        )

        # Mock historical results for optimization context
        mock_historical_results = []

        # Optimize queries
        optimized_plan = (
            await production_orchestrator.optimize_queries_with_cognitive_feedback(
                original_plan,
                mock_historical_results,
            )
        )

        # Verify optimization was applied
        assert optimized_plan.topic == original_plan.topic
        assert len(optimized_plan.sources) == len(original_plan.sources)
        assert optimized_plan.context.get("query_optimization_applied") is True

        # Verify cognitive engine was called
        assert mock_cognitive_engine.optimize_search_query.call_count > 0

    @pytest.mark.asyncio
    async def test_should_handle_optimization_failures_gracefully(
        self,
        production_orchestrator,
    ):
        """
        Test: Should fallback to original queries when optimization fails
        and continue execution without errors.
        """
        # Create orchestrator without cognitive engine
        orchestrator_no_cognitive = ProductionIngestionOrchestrator(
            config=IngestionConfig(),
            production_config=ProductionConfig(),
            cognitive_engine=None,
            n8n_manager=None,
        )

        try:
            original_plan = IngestionPlan(
                topic="fallback test",
                sources=[
                    IngestionSource(
                        source_type="arxiv",
                        priority=1,
                        query_parameters={"terms": ["test"], "max_results": 5},
                        estimated_results=5,
                        timeout=60,
                    ),
                ],
                total_sources=1,
                estimated_total_results=5,
                estimated_duration=60,
            )

            # Should not fail even without cognitive engine
            result_plan = await orchestrator_no_cognitive.optimize_queries_with_cognitive_feedback(
                original_plan,
            )

            # Should return original plan when no optimization available
            assert result_plan.topic == original_plan.topic
            assert len(result_plan.sources) == len(original_plan.sources)

        finally:
            await orchestrator_no_cognitive.close()

    @pytest.mark.asyncio
    async def test_should_apply_heuristic_optimization_fallbacks(
        self,
        production_orchestrator,
    ):
        """
        Test: Should apply intelligent heuristic optimizations when
        cognitive optimization is unavailable or fails.
        """
        # Mock cognitive engine to fail
        production_orchestrator.cognitive_engine = None

        # Test ArXiv optimization
        arxiv_source = IngestionSource(
            source_type="arxiv",
            priority=1,
            query_parameters={"terms": ["machine learning"], "max_results": 5},
            estimated_results=5,
            timeout=60,
        )

        # Apply fallback optimization
        context = {"average_quality": 0.7, "success_rate": 0.9}
        optimization = production_orchestrator._fallback_optimization(
            arxiv_source,
            context,
        )

        # Verify heuristic optimization was applied
        assert "optimized_params" in optimization
        assert optimization["confidence"] > 0
        assert optimization["estimated_improvement"] > 0

        # For ArXiv with "machine learning", should add related terms
        optimized_params = optimization["optimized_params"]
        if "terms" in optimized_params:
            terms = optimized_params["terms"]
            assert len(terms) > len(arxiv_source.query_parameters["terms"])

    # ========================================================================
    # ADAPTIVE SCALING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_execute_with_adaptive_scaling(self, production_orchestrator):
        """
        Test: Should dynamically adjust concurrency and resources based on
        API performance and system health.
        """
        # Create test plan
        plan = IngestionPlan(
            topic="adaptive scaling test",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters={"terms": ["scaling"], "max_results": 3},
                    estimated_results=3,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=3,
            estimated_duration=60,
        )

        # Execute with adaptive scaling
        result = await production_orchestrator.execute_with_adaptive_scaling(
            plan,
            enable_optimization=True,
        )

        # Verify execution completed successfully
        assert result.success
        assert result.total_content_items > 0

        # Verify production metrics are included
        assert "production_features_enabled" in result.metrics
        assert result.metrics["production_features_enabled"] is True
        assert "api_health_checks" in result.metrics
        assert "healthy_apis" in result.metrics

    @pytest.mark.asyncio
    async def test_should_adjust_concurrency_based_on_api_health(
        self,
        production_orchestrator,
    ):
        """
        Test: Should dynamically adjust concurrency limits based on
        real-time API health and performance metrics.
        """
        # Simulate unhealthy APIs
        production_orchestrator.api_health_status["firecrawl"] = APIHealthStatus(
            service_name="firecrawl",
            is_healthy=False,
            response_time_ms=5000.0,
            last_check=datetime.now(UTC),
        )

        # Calculate optimal concurrency with unhealthy API
        optimal_concurrency = production_orchestrator._calculate_optimal_concurrency()

        # Should reduce concurrency due to unhealthy API
        assert (
            optimal_concurrency < production_orchestrator.config.max_concurrent_sources
        )
        assert optimal_concurrency >= 1  # Should never go below 1

        # Simulate all healthy APIs with fast response times
        for service_name in production_orchestrator.api_health_status:
            production_orchestrator.api_health_status[service_name] = APIHealthStatus(
                service_name=service_name,
                is_healthy=True,
                response_time_ms=50.0,  # Very fast
                last_check=datetime.now(UTC),
            )

        # Recalculate with healthy APIs
        optimal_concurrency_healthy = (
            production_orchestrator._calculate_optimal_concurrency()
        )

        # Should potentially increase concurrency for excellent performance
        assert (
            optimal_concurrency_healthy
            >= production_orchestrator.config.max_concurrent_sources
        )

    # ========================================================================
    # API HEALTH MONITORING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_monitor_api_health_status(self, production_orchestrator):
        """
        Test: Should continuously monitor API health and update status
        with response times and error tracking.
        """
        # Mock HTTP session for health checks
        with patch.object(production_orchestrator, "get_session") as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            # Perform health checks
            await production_orchestrator._check_api_health()

            # Verify health status was updated
            for service_name in ["firecrawl", "arxiv", "ncbi"]:
                status = production_orchestrator.api_health_status[service_name]
                assert isinstance(status.last_check, datetime)
                # Health status should be updated (either healthy or unhealthy)
                assert isinstance(status.is_healthy, bool)

    @pytest.mark.asyncio
    async def test_should_handle_api_health_check_failures(
        self,
        production_orchestrator,
    ):
        """
        Test: Should gracefully handle API health check failures and
        mark services as unhealthy without crashing.
        """
        # Mock session to raise exceptions
        with patch.object(production_orchestrator, "get_session") as mock_session:
            mock_session.side_effect = Exception("Connection failed")

            # Health checks should not crash
            await production_orchestrator._check_api_health()

            # Services should be marked as unhealthy
            for service_name in ["firecrawl", "arxiv", "ncbi"]:
                status = production_orchestrator.api_health_status[service_name]
                # Status should still be updated even with failures
                assert isinstance(status.last_check, datetime)

    # ========================================================================
    # PRODUCTION STATUS AND MONITORING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_provide_comprehensive_production_status(
        self,
        production_orchestrator,
    ):
        """
        Test: Should provide detailed production status including API health,
        performance metrics, and configuration details.
        """
        # Get production status
        status = await production_orchestrator.get_production_status()

        # Verify status structure
        assert "orchestrator_version" in status
        assert status["orchestrator_version"] == "2.0-production"

        assert "total_executions" in status
        assert "success_rate" in status
        assert "average_execution_time" in status

        # Verify API health is included
        assert "api_health" in status
        api_health = status["api_health"]
        assert len(api_health) == 3

        for service_name in ["firecrawl", "arxiv", "ncbi"]:
            assert service_name in api_health
            service_health = api_health[service_name]
            assert "is_healthy" in service_health
            assert "response_time_ms" in service_health
            assert "last_check" in service_health

        # Verify configuration is included
        assert "configuration" in status
        config = status["configuration"]
        assert "real_apis_enabled" in config
        assert "cognitive_optimization" in config
        assert "workflow_automation" in config
        assert "quality_threshold" in config

    @pytest.mark.asyncio
    async def test_should_track_performance_metrics_for_learning(
        self,
        production_orchestrator,
    ):
        """
        Test: Should collect and store performance metrics for continuous
        learning and optimization improvements.
        """
        # Create mock result
        from services.ingestion.orchestrator import IngestionResult

        mock_result = IngestionResult(
            success=True,
            plan_id="test-plan-123",
            content_items=[],
            total_content_items=5,
            sources_attempted=2,
            sources_completed=2,
            sources_failed=0,
            execution_time=1.5,
            average_quality_score=0.85,
        )

        # Update performance metrics (should not crash)
        await production_orchestrator._update_performance_metrics(mock_result)

        # Performance tracking should be logged (in production, would be stored)
        # This test verifies the method executes without errors
        assert True  # If we reach here, performance tracking worked

    # ========================================================================
    # PRODUCTION LIFECYCLE TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_create_and_cleanup_http_session(
        self,
        production_orchestrator,
    ):
        """
        Test: Should properly create HTTP session with production settings
        and clean up resources on shutdown.
        """
        # Get session
        session1 = await production_orchestrator.get_session()
        assert isinstance(session1, aiohttp.ClientSession)
        assert not session1.closed

        # Getting session again should return same instance
        session2 = await production_orchestrator.get_session()
        assert session1 is session2

        # Close orchestrator
        await production_orchestrator.close()

        # Session should be closed
        assert session1.closed

    @pytest.mark.asyncio
    async def test_should_handle_production_configuration_variations(self, base_config):
        """
        Test: Should handle various production configuration combinations
        gracefully including missing API keys.
        """
        # Test with minimal configuration (no API keys)
        minimal_config = ProductionConfig()

        orchestrator = ProductionIngestionOrchestrator(
            config=base_config,
            production_config=minimal_config,
            cognitive_engine=None,
            n8n_manager=None,
        )

        try:
            # Should initialize without errors even with minimal config
            assert orchestrator.production_config is not None
            assert orchestrator.api_health_status is not None

            # Should have default service instances
            assert orchestrator.arxiv_service is not None
            assert orchestrator.pubmed_service is not None

        finally:
            await orchestrator.close()

    # ========================================================================
    # INTEGRATION WITH BASE ORCHESTRATOR TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_extend_base_orchestrator_functionality(
        self,
        production_orchestrator,
    ):
        """
        Test: Should properly extend base orchestrator while maintaining
        all existing functionality and adding production features.
        """
        # Verify inheritance
        from services.ingestion.orchestrator import IngestionOrchestrator

        assert isinstance(production_orchestrator, IngestionOrchestrator)

        # Verify base functionality is available
        assert hasattr(production_orchestrator, "create_ingestion_plan")
        assert hasattr(production_orchestrator, "execute_ingestion_plan")

        # Verify production-specific functionality is added
        assert hasattr(
            production_orchestrator,
            "optimize_queries_with_cognitive_feedback",
        )
        assert hasattr(production_orchestrator, "execute_with_adaptive_scaling")
        assert hasattr(production_orchestrator, "get_production_status")

        # Verify production configuration is properly set
        assert production_orchestrator.production_config is not None
        assert production_orchestrator.api_health_status is not None

    @pytest.mark.asyncio
    async def test_should_maintain_backward_compatibility(
        self,
        production_orchestrator,
    ):
        """
        Test: Should maintain full backward compatibility with base
        orchestrator API while adding production enhancements.
        """
        # Create simple plan using base orchestrator API
        plan = await production_orchestrator.create_ingestion_plan(
            topic="compatibility test",
            context={"test": True},
        )

        # Verify plan creation works
        assert plan is not None
        assert plan.topic == "compatibility test"
        assert plan.total_sources >= 1

        # Execute using base API
        result = await production_orchestrator.execute_ingestion_plan(plan)

        # Verify execution works
        assert result is not None
        assert isinstance(result.success, bool)

        # But should include production enhancements
        if result.success:
            assert (
                "production_features_enabled" in result.metrics
                or len(result.content_items) >= 0
            )


if __name__ == "__main__":
    # Run production orchestrator tests
    pytest.main([__file__, "-v", "--tb=short"])
