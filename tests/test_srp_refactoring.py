#!/usr/bin/env python3
"""PAKE System - SRP Refactoring Test Suite
Comprehensive tests for refactored services following Single Responsibility Principle
"""


import pytest

from src.services.ingestion.IngestionOrchestratorRefactored import (
    IngestionOrchestratorRefactored,
    OrchestratorConfig,
)

# Import refactored Python services
from src.services.ingestion.managers.IngestionPlanBuilder import (
    IngestionPlanBuilder,
    PlanBuilderConfig,
)
from src.services.ingestion.managers.SourceExecutor import SourceExecutor

# Video service tests removed - TypeScript services will be tested separately


class TestIngestionPlanBuilder:
    """Test IngestionPlanBuilder - Single Responsibility: Plan Building"""

    def test_plan_builder_initialization(self):
        """Test plan builder initializes correctly"""
        config = PlanBuilderConfig(max_sources_per_plan=5)
        builder = IngestionPlanBuilder(config)

        assert builder.config.max_sources_per_plan == 5

    def test_plan_building(self):
        """Test plan building functionality"""
        builder = IngestionPlanBuilder()

        topic = "AI Research"
        source_configs = [
            {
                "source_type": "web",
                "query_parameters": {"query": "artificial intelligence"},
                "estimated_results": 10,
                "priority": 5,
            },
            {
                "source_type": "arxiv",
                "query_parameters": {"query": "machine learning"},
                "estimated_results": 15,
                "priority": 7,
            },
        ]

        plan = builder.build_plan(topic, source_configs)

        assert plan.topic == topic
        assert plan.total_sources == 2
        assert plan.estimated_total_results == 25
        assert plan.estimated_duration > 0

    def test_plan_validation(self):
        """Test plan validation"""
        builder = IngestionPlanBuilder()

        # Invalid plan should raise error
        with pytest.raises(ValueError):
            builder.build_plan("", [])

        # Too many sources should raise error
        config = PlanBuilderConfig(max_sources_per_plan=1)
        builder = IngestionPlanBuilder(config)

        with pytest.raises(ValueError):
            builder.build_plan(
                "test",
                [
                    {
                        "source_type": "web",
                        "query_parameters": {},
                        "estimated_results": 10,
                    },
                    {
                        "source_type": "arxiv",
                        "query_parameters": {},
                        "estimated_results": 10,
                    },
                ],
            )


class TestSourceExecutor:
    """Test SourceExecutor - Single Responsibility: Source Execution"""

    def test_source_executor_initialization(self):
        """Test source executor initializes correctly"""
        executor = SourceExecutor()

        assert executor.firecrawl_service is not None
        assert executor.arxiv_service is not None
        assert executor.pubmed_service is not None

    def test_cache_key_generation(self):
        """Test cache key generation"""
        executor = SourceExecutor()

        source = {
            "source_type": "web",
            "query_parameters": {"query": "test"},
            "estimated_results": 10,
        }

        cache_key = executor.get_source_cache_key(source)
        assert cache_key.startswith("web_")
        assert len(cache_key) > 10


class TestIngestionOrchestratorRefactored:
    """Test IngestionOrchestratorRefactored - Single Responsibility: Orchestration"""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly"""
        config = OrchestratorConfig(max_concurrent_sources=3)
        orchestrator = IngestionOrchestratorRefactored(config)

        assert orchestrator.config.max_concurrent_sources == 3
        assert orchestrator.plan_builder is not None
        assert orchestrator.source_executor is not None

    def test_statistics_tracking(self):
        """Test statistics are tracked correctly"""
        orchestrator = IngestionOrchestratorRefactored()

        stats = orchestrator.get_statistics()
        assert "plans_executed" in stats
        assert "sources_processed" in stats
        assert "total_items_retrieved" in stats

    @pytest.mark.asyncio()
    async def test_health_check(self):
        """Test health check functionality"""
        orchestrator = IngestionOrchestratorRefactored()

        health = await orchestrator.health_check()
        assert health["orchestrator"] == "healthy"
        assert health["plan_builder"] == "healthy"
        assert health["source_executor"] == "healthy"
        assert "statistics" in health
        assert "config" in health


class TestSRPCompliance:
    """Test Single Responsibility Principle compliance"""

    def test_ingestion_plan_builder_srp(self):
        """Test IngestionPlanBuilder has single responsibility"""
        builder = IngestionPlanBuilder()

        # Should only handle plan building
        plan = builder.build_plan(
            "test",
            [{"source_type": "web", "query_parameters": {}, "estimated_results": 10}],
        )
        assert plan.topic == "test"

        # Should not handle execution, caching, etc.
        assert not hasattr(builder, "executeSource")
        assert not hasattr(builder, "cacheResult")
        assert not hasattr(builder, "handleError")

    def test_source_executor_srp(self):
        """Test SourceExecutor has single responsibility"""
        executor = SourceExecutor()

        # Should only handle source execution
        assert hasattr(executor, "execute_source")
        assert hasattr(executor, "get_source_cache_key")

        # Should not handle plan building, orchestration, etc.
        assert not hasattr(executor, "build_plan")
        assert not hasattr(executor, "orchestrate_execution")
        assert not hasattr(executor, "handle_errors")

    def test_orchestrator_srp(self):
        """Test IngestionOrchestratorRefactored has single responsibility"""
        orchestrator = IngestionOrchestratorRefactored()

        # Should only handle orchestration
        assert hasattr(orchestrator, "execute_ingestion_plan")
        assert hasattr(orchestrator, "get_statistics")
        assert hasattr(orchestrator, "health_check")

        # Should delegate specific responsibilities to managers
        assert hasattr(orchestrator, "plan_builder")
        assert hasattr(orchestrator, "source_executor")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
