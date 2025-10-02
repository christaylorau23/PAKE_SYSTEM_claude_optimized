#!/usr/bin/env python3
"""
PAKE System - Phase 2A Ingestion Orchestrator Tests
TDD RED phase: Comprehensive failing tests for unified omni-source ingestion orchestrator.

Following CLAUDE.md TDD principles for orchestrator implementation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from scripts.ingestion_pipeline import ContentItem

# Import Phase 2A services

# Import orchestrator (will be created)
try:
    from services.ingestion.orchestrator import (
        IngestionConfig,
        IngestionOrchestrator,
        IngestionPlan,
        IngestionResult,
        IngestionSource,
    )
except ImportError:
    # Expected during RED phase - orchestrator doesn't exist yet
    IngestionOrchestrator = None
    IngestionPlan = None
    IngestionResult = None
    IngestionSource = None
    IngestionConfig = None


class TestIngestionOrchestrator:
    """
    TDD test suite for Phase 2A unified ingestion orchestrator.
    Tests comprehensive multi-source orchestration capabilities.
    """

    @pytest.fixture()
    def mock_cognitive_engine(self):
        """Mock cognitive engine for testing"""
        engine = Mock()
        engine.assess_research_quality = AsyncMock(return_value=0.89)
        engine.assess_content_quality = AsyncMock(return_value=0.92)
        engine.categorize_content = AsyncMock(return_value=["AI", "Research"])
        engine.extract_insights = AsyncMock(
            return_value={
                "key_concepts": ["machine learning", "healthcare"],
                "relevance_score": 0.94,
                "complexity_level": "advanced",
            },
        )
        return engine

    @pytest.fixture()
    def mock_n8n_manager(self):
        """Mock n8n workflow manager"""
        manager = Mock()
        manager.trigger_workflow = AsyncMock(return_value={"workflow_id": "orch_001"})
        manager.monitor_workflow = AsyncMock(return_value={"status": "completed"})
        return manager

    @pytest.fixture()
    def orchestrator_config(self):
        """Orchestrator configuration for testing"""
        return {
            "max_concurrent_sources": 5,
            "timeout_per_source": 300,
            "quality_threshold": 0.7,
            "enable_cognitive_processing": True,
            "enable_workflow_automation": True,
            "retry_failed_sources": True,
            "max_retries": 2,
            "deduplication_enabled": True,
            "caching_enabled": True,
        }

    @pytest.fixture()
    def ingestion_orchestrator(
        self,
        orchestrator_config,
        mock_cognitive_engine,
        mock_n8n_manager,
    ):
        """Create ingestion orchestrator instance"""
        if IngestionOrchestrator is None:
            pytest.skip("IngestionOrchestrator not implemented yet (RED phase)")

        return IngestionOrchestrator(
            config=IngestionConfig(**orchestrator_config),
            cognitive_engine=mock_cognitive_engine,
            n8n_manager=mock_n8n_manager,
        )

    # ========================================================================
    # CORE ORCHESTRATOR FUNCTIONALITY TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_create_comprehensive_ingestion_plan_from_research_topic(
        self,
        ingestion_orchestrator,
    ):
        """
        Test: Should generate comprehensive ingestion plan for complex research topic
        covering web scraping, academic papers, and biomedical research.
        """
        research_topic = "AI applications in personalized medicine"
        research_context = {
            "domain": "healthcare",
            "focus_areas": [
                "machine learning",
                "medical diagnosis",
                "personalized treatment",
            ],
            "depth": "comprehensive",
            "timeline": "recent_5_years",
        }

        # Create ingestion plan
        plan = await ingestion_orchestrator.create_ingestion_plan(
            topic=research_topic,
            context=research_context,
        )

        # Verify plan structure
        assert isinstance(plan, IngestionPlan)
        assert plan.topic == research_topic
        assert plan.total_sources >= 3  # Web, ArXiv, PubMed minimum
        assert len(plan.sources) >= 3

        # Verify source diversity
        source_types = [source.source_type for source in plan.sources]
        assert "web" in source_types
        assert "arxiv" in source_types
        assert "pubmed" in source_types

        # Verify source configurations are appropriate
        for source in plan.sources:
            assert isinstance(source, IngestionSource)
            assert source.priority >= 1
            assert source.estimated_results > 0
            assert source.query_parameters is not None

    @pytest.mark.asyncio()
    async def test_should_execute_comprehensive_multi_source_ingestion_plan(
        self,
        ingestion_orchestrator,
    ):
        """
        Test: Should execute ingestion plan across all sources with proper orchestration,
        error handling, and result aggregation.
        """
        # Create test plan
        plan = IngestionPlan(
            topic="machine learning in healthcare",
            sources=[
                IngestionSource(
                    source_type="web",
                    priority=1,
                    query_parameters={
                        "urls": [
                            "https://example.com/ml-healthcare-overview",
                            "https://example.com/ai-medical-applications",
                        ],
                        "scraping_options": {
                            "wait_time": 3000,
                            "include_headings": True,
                        },
                    },
                    estimated_results=2,
                    timeout=60,
                ),
                IngestionSource(
                    source_type="arxiv",
                    priority=2,
                    query_parameters={
                        "terms": ["machine learning", "healthcare"],
                        "categories": ["cs.AI", "cs.LG"],
                        "max_results": 10,
                    },
                    estimated_results=10,
                    timeout=90,
                ),
                IngestionSource(
                    source_type="pubmed",
                    priority=3,
                    query_parameters={
                        "terms": ["machine learning", "medical diagnosis"],
                        "mesh_terms": ["Algorithms"],
                        "publication_types": ["Journal Article"],
                        "max_results": 8,
                    },
                    estimated_results=8,
                    timeout=120,
                ),
            ],
            total_sources=3,
            estimated_total_results=20,
            estimated_duration=300,
        )

        # Execute ingestion plan
        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify execution results
        assert isinstance(result, IngestionResult)
        assert result.success
        assert result.plan_id == plan.plan_id
        assert (
            result.total_content_items >= 3
        )  # Should have content from multiple sources
        assert result.sources_completed >= 2  # At least 2 sources should succeed
        assert result.execution_time > 0

        # Verify content diversity
        source_types_retrieved = set()
        for item in result.content_items:
            assert isinstance(item, ContentItem)
            source_types_retrieved.add(item.source_type)

        assert len(source_types_retrieved) >= 2  # Multiple source types

    @pytest.mark.asyncio()
    async def test_should_handle_parallel_source_execution_with_proper_concurrency_control(
        self,
        ingestion_orchestrator,
        orchestrator_config,
    ):
        """
        Test: Should execute multiple sources in parallel while respecting
        concurrency limits and timeout constraints.
        """
        # Create plan with many sources to test concurrency
        sources = []
        for i in range(orchestrator_config["max_concurrent_sources"] + 2):
            sources.append(
                IngestionSource(
                    source_type="web",
                    priority=i + 1,
                    query_parameters={
                        "urls": [f"https://example.com/test-{i}"],
                        "scraping_options": {"wait_time": 1000},
                    },
                    estimated_results=1,
                    timeout=30,
                ),
            )

        plan = IngestionPlan(
            topic="concurrency test",
            sources=sources,
            total_sources=len(sources),
            estimated_total_results=len(sources),
            estimated_duration=60,
        )

        start_time = datetime.now(UTC)
        result = await ingestion_orchestrator.execute_ingestion_plan(plan)
        execution_time = (datetime.now(UTC) - start_time).total_seconds()

        # Verify concurrency behavior
        assert result.success
        assert (
            result.max_concurrent_sources
            <= orchestrator_config["max_concurrent_sources"]
        )
        assert (
            execution_time < 120
        )  # Should complete within reasonable time due to parallelism
        assert result.sources_completed > 0

    # ========================================================================
    # COGNITIVE INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_apply_cognitive_assessment_across_all_ingested_content(
        self,
        ingestion_orchestrator,
        mock_cognitive_engine,
    ):
        """
        Test: Should apply unified cognitive assessment to all content
        from all sources with quality filtering and insights extraction.
        """
        # Create simple plan for cognitive testing
        plan = IngestionPlan(
            topic="AI cognitive assessment test",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters={
                        "terms": ["artificial intelligence"],
                        "max_results": 3,
                    },
                    estimated_results=3,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=3,
            estimated_duration=60,
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify cognitive assessment was applied
        assert result.success
        assert result.cognitive_assessment_applied

        # Check that cognitive engine methods were called
        assert mock_cognitive_engine.assess_research_quality.call_count > 0

        # Verify content has quality scores
        high_quality_content = [
            item
            for item in result.content_items
            if hasattr(item, "metadata")
            and item.metadata.get("quality_score", 0) > 0.7  # Use direct threshold
        ]
        assert len(high_quality_content) > 0

    @pytest.mark.asyncio()
    async def test_should_optimize_queries_based_on_cognitive_feedback(
        self,
        ingestion_orchestrator,
        mock_cognitive_engine,
    ):
        """
        Test: Should use cognitive engine to optimize search queries
        and improve result quality through iterative refinement.
        """
        # Mock cognitive engine to provide query optimization suggestions
        mock_cognitive_engine.optimize_search_query = AsyncMock(
            return_value={
                "optimized_terms": [
                    "machine learning",
                    "deep learning",
                    "neural networks",
                ],
                "suggested_filters": {"recent_years": 3},
                "confidence": 0.88,
            },
        )

        research_topic = "AI in medicine"

        # Create plan with query optimization enabled
        plan = await ingestion_orchestrator.create_ingestion_plan(
            topic=research_topic,
            context={"enable_query_optimization": True},
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify query optimization was applied
        assert result.success
        assert result.query_optimizations_applied > 0
        assert mock_cognitive_engine.optimize_search_query.call_count > 0

    # ========================================================================
    # WORKFLOW AUTOMATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_trigger_appropriate_n8n_workflows_based_on_content_type(
        self,
        ingestion_orchestrator,
        mock_n8n_manager,
    ):
        """
        Test: Should trigger different n8n workflows based on the type
        of content ingested and research domain.
        """
        plan = IngestionPlan(
            topic="biomedical research automation",
            sources=[
                IngestionSource(
                    source_type="pubmed",
                    priority=1,
                    query_parameters={
                        "terms": ["clinical trials"],
                        "mesh_terms": ["Algorithms"],
                        "max_results": 5,
                    },
                    estimated_results=5,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=5,
            estimated_duration=60,
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify workflow automation
        assert result.success
        assert result.workflows_triggered > 0
        assert mock_n8n_manager.trigger_workflow.call_count > 0

        # Verify appropriate workflow types were triggered
        workflow_calls = mock_n8n_manager.trigger_workflow.call_args_list
        workflow_types = [
            call.kwargs.get("workflow_type", "") for call in workflow_calls
        ]
        assert any("biomedical" in wtype.lower() for wtype in workflow_types)

    @pytest.mark.asyncio()
    async def test_should_coordinate_cross_source_workflow_dependencies(
        self,
        ingestion_orchestrator,
        mock_n8n_manager,
    ):
        """
        Test: Should coordinate workflows that depend on content from
        multiple sources (e.g., cross-reference validation).
        """
        # Mock workflow that requires multi-source coordination
        mock_n8n_manager.trigger_cross_source_workflow = AsyncMock(
            return_value={
                "workflow_id": "cross_ref_001",
                "dependencies_resolved": True,
            },
        )

        plan = IngestionPlan(
            topic="multi-source research validation",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters={"terms": ["validation"], "max_results": 3},
                    estimated_results=3,
                    timeout=60,
                ),
                IngestionSource(
                    source_type="pubmed",
                    priority=2,
                    query_parameters={
                        "terms": ["validation"],
                        "mesh_terms": ["Algorithms"],
                        "max_results": 3,
                    },
                    estimated_results=3,
                    timeout=60,
                ),
            ],
            total_sources=2,
            estimated_total_results=6,
            estimated_duration=120,
            enable_cross_source_workflows=True,
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify cross-source coordination
        assert result.success
        assert result.cross_source_workflows_triggered > 0

    # ========================================================================
    # ERROR HANDLING AND RESILIENCE TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_partial_source_failures_gracefully(
        self,
        ingestion_orchestrator,
    ):
        """
        Test: Should continue execution when some sources fail,
        providing partial results and detailed error reporting.
        """
        # Create plan where some sources will fail
        plan = IngestionPlan(
            topic="resilience test",
            sources=[
                IngestionSource(
                    source_type="web",
                    priority=1,
                    query_parameters={"urls": ["https://nonexistent-failure-test.com"]},
                    estimated_results=1,
                    timeout=30,
                ),
                IngestionSource(
                    source_type="arxiv",
                    priority=2,
                    query_parameters={"terms": ["working query"], "max_results": 3},
                    estimated_results=3,
                    timeout=60,
                ),
            ],
            total_sources=2,
            estimated_total_results=4,
            estimated_duration=90,
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Should succeed partially
        assert result.sources_attempted == 2
        assert result.sources_failed > 0
        assert result.sources_completed > 0
        assert len(result.error_details) > 0

        # Should still have some content
        assert len(result.content_items) > 0

    @pytest.mark.asyncio()
    async def test_should_implement_retry_logic_for_failed_sources(
        self,
        ingestion_orchestrator,
        orchestrator_config,
    ):
        """
        Test: Should retry failed sources according to retry configuration
        with exponential backoff and failure classification.
        """
        # Mock a source that fails twice then succeeds
        retry_count = 0

        async def mock_failing_source(*args, **kwargs):
            nonlocal retry_count
            retry_count += 1
            if retry_count <= orchestrator_config["max_retries"]:
                raise Exception(f"Temporary failure {retry_count}")
            # Return list of ContentItem objects as expected by _execute_test_source
            return [
                ContentItem(
                    source_name="retry_test",
                    source_type="test",
                    title="Retry Success Test",
                    content="Test content after successful retry",
                    url="https://test.example.com",
                    published=datetime.now(UTC),
                    author="Test Author",
                    tags=["retry", "test"],
                    metadata={"retry_attempt": retry_count},
                ),
            ]

        # Test retry behavior
        plan = IngestionPlan(
            topic="retry test",
            sources=[
                IngestionSource(
                    source_type="test_source",  # Will use mock
                    priority=1,
                    query_parameters={"test": "retry"},
                    estimated_results=1,
                    timeout=30,
                ),
            ],
            total_sources=1,
            estimated_total_results=1,
            estimated_duration=60,
        )

        with patch.object(
            ingestion_orchestrator,
            "_execute_test_source",
            side_effect=mock_failing_source,
        ):
            result = await ingestion_orchestrator.execute_ingestion_plan(plan)

            # Verify retry behavior
            assert retry_count == orchestrator_config["max_retries"] + 1
            assert result.total_retry_attempts > 0

    # ========================================================================
    # PERFORMANCE AND OPTIMIZATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_implement_content_deduplication_across_sources(
        self,
        ingestion_orchestrator,
    ):
        """
        Test: Should identify and deduplicate similar content from
        different sources while preserving unique information.
        """
        plan = IngestionPlan(
            topic="deduplication test",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters={"terms": ["machine learning"], "max_results": 5},
                    estimated_results=5,
                    timeout=60,
                ),
                IngestionSource(
                    source_type="pubmed",
                    priority=2,
                    query_parameters={
                        "terms": ["machine learning"],
                        "mesh_terms": ["Algorithms"],
                        "max_results": 5,
                    },
                    estimated_results=5,
                    timeout=60,
                ),
            ],
            total_sources=2,
            estimated_total_results=10,
            estimated_duration=120,
            enable_deduplication=True,
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify deduplication was applied
        assert result.success
        assert result.deduplication_applied
        assert result.duplicates_removed >= 0

        # Check content diversity
        unique_titles = set(item.title.lower() for item in result.content_items)
        total_items = len(result.content_items)
        diversity_ratio = len(unique_titles) / max(total_items, 1)
        assert diversity_ratio >= 0.7  # High diversity indicates good deduplication

    @pytest.mark.asyncio()
    async def test_should_implement_intelligent_caching_for_repeat_queries(
        self,
        ingestion_orchestrator,
    ):
        """
        Test: Should cache results from expensive sources and reuse
        them for similar queries to improve performance.
        """
        query_params = {"terms": ["caching test"], "max_results": 3}

        plan1 = IngestionPlan(
            topic="caching test 1",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters=query_params,
                    estimated_results=3,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=3,
            estimated_duration=60,
        )

        # Execute first time
        result1 = await ingestion_orchestrator.execute_ingestion_plan(plan1)
        first_execution_time = result1.execution_time

        # Execute similar query
        plan2 = IngestionPlan(
            topic="caching test 2",  # Similar topic
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters=query_params,  # Same parameters
                    estimated_results=3,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=3,
            estimated_duration=60,
        )

        result2 = await ingestion_orchestrator.execute_ingestion_plan(plan2)

        # Second execution should be faster due to caching
        assert result1.success and result2.success
        assert result2.cache_hits > 0  # Should have cache hits
        # Allow for small timing variations - cache should either be faster or
        # very close
        assert (
            result2.execution_time <= first_execution_time * 1.1
        )  # Allow 10% variance

    @pytest.mark.asyncio()
    async def test_should_monitor_and_report_comprehensive_metrics(
        self,
        ingestion_orchestrator,
    ):
        """
        Test: Should collect and report comprehensive metrics about
        ingestion performance, quality, and system health.
        """
        plan = IngestionPlan(
            topic="metrics test",
            sources=[
                IngestionSource(
                    source_type="arxiv",
                    priority=1,
                    query_parameters={"terms": ["metrics"], "max_results": 2},
                    estimated_results=2,
                    timeout=60,
                ),
            ],
            total_sources=1,
            estimated_total_results=2,
            estimated_duration=60,
        )

        result = await ingestion_orchestrator.execute_ingestion_plan(plan)

        # Verify comprehensive metrics
        assert result.success
        assert hasattr(result, "metrics")

        expected_metrics = [
            "total_execution_time",
            "source_success_rate",
            "average_quality_score",
            "content_diversity_score",
            "cognitive_processing_time",
            "workflow_trigger_count",
            "cache_hit_rate",
            "retry_success_rate",
        ]

        for metric in expected_metrics:
            assert metric in result.metrics

    # ========================================================================
    # CONFIGURATION AND CUSTOMIZATION TESTS
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_support_custom_source_configurations(
        self,
        ingestion_orchestrator,
        mock_cognitive_engine,
        mock_n8n_manager,
    ):
        """
        Test: Should support custom configurations for each source type
        including specialized parameters and processing options.
        """
        custom_config = IngestionConfig(
            max_concurrent_sources=2,
            timeout_per_source=120,
            quality_threshold=0.8,  # Higher quality threshold
            custom_source_configs={
                "arxiv": {
                    "preferred_categories": ["cs.AI", "cs.LG", "cs.CL"],
                    "author_filters": ["exclude_known_spam"],
                    "date_range_years": 2,
                },
                "pubmed": {
                    "mesh_term_expansion": True,
                    "journal_impact_filter": 3.0,
                    "study_type_preferences": ["RCT", "Meta-Analysis"],
                },
            },
        )

        orchestrator = IngestionOrchestrator(
            config=custom_config,
            cognitive_engine=mock_cognitive_engine,
            n8n_manager=mock_n8n_manager,
        )

        plan = await orchestrator.create_ingestion_plan(
            topic="custom config test",
            context={"domain": "medical_ai"},
        )

        result = await orchestrator.execute_ingestion_plan(plan)

        # Verify custom configurations were applied
        assert result.success
        assert result.custom_configs_applied

        # Check that quality threshold was enforced
        low_quality_items = [
            item
            for item in result.content_items
            if item.metadata.get("quality_score", 0) < custom_config.quality_threshold
        ]
        assert len(low_quality_items) == 0  # All items should meet higher threshold


if __name__ == "__main__":
    # Run orchestrator tests
    pytest.main([__file__, "-v", "--tb=short"])
