#!/usr/bin/env python3
"""PAKE System - SRP Refactoring Validation
Simple validation of Single Responsibility Principle implementation
"""

from unittest.mock import MagicMock

import pytest


class TestSRPValidation:
    """Test Single Responsibility Principle compliance"""

    def test_plan_builder_srp_compliance(self):
        """Test IngestionPlanBuilder follows SRP"""
        # Import only the class we need
        from src.services.ingestion.managers.IngestionPlanBuilder import (
            IngestionPlanBuilder,
        )

        builder = IngestionPlanBuilder()

        # Should only handle plan building
        assert hasattr(builder, "build_plan")
        assert hasattr(builder, "optimize_plan")
        assert hasattr(builder, "_validate_plan")

        # Should not handle execution, caching, etc.
        assert not hasattr(builder, "execute_source")
        assert not hasattr(builder, "cache_result")
        assert not hasattr(builder, "handle_error")
        assert not hasattr(builder, "monitor_performance")

    def test_source_executor_srp_compliance(self):
        """Test SourceExecutor follows SRP"""
        from src.services.ingestion.managers.SourceExecutor import SourceExecutor

        executor = SourceExecutor()

        # Should only handle source execution
        assert hasattr(executor, "execute_source")
        assert hasattr(executor, "get_source_cache_key")
        assert hasattr(executor, "_execute_web_source")
        assert hasattr(executor, "_execute_arxiv_source")
        assert hasattr(executor, "_execute_pubmed_source")

        # Should not handle plan building, orchestration, etc.
        assert not hasattr(executor, "build_plan")
        assert not hasattr(executor, "orchestrate_execution")
        assert not hasattr(executor, "handle_errors")
        assert not hasattr(executor, "collect_metrics")

    def test_orchestrator_srp_compliance(self):
        """Test IngestionOrchestratorRefactored follows SRP"""
        from src.services.ingestion.IngestionOrchestratorRefactored import (
            IngestionOrchestratorRefactored,
        )

        orchestrator = IngestionOrchestratorRefactored()

        # Should only handle orchestration
        assert hasattr(orchestrator, "execute_ingestion_plan")
        assert hasattr(orchestrator, "get_statistics")
        assert hasattr(orchestrator, "health_check")
        assert hasattr(orchestrator, "create_plan_from_config")
        assert hasattr(orchestrator, "optimize_plan")

        # Should delegate specific responsibilities to managers
        assert hasattr(orchestrator, "plan_builder")
        assert hasattr(orchestrator, "source_executor")

        # Should not implement specific source execution logic
        assert not hasattr(orchestrator, "_execute_web_source")
        assert not hasattr(orchestrator, "_execute_arxiv_source")
        assert not hasattr(orchestrator, "_execute_pubmed_source")

    def test_dependency_injection_pattern(self):
        """Test that services use dependency injection"""
        from src.services.ingestion.IngestionOrchestratorRefactored import (
            IngestionOrchestratorRefactored,
        )

        orchestrator = IngestionOrchestratorRefactored()

        # Should have injected dependencies
        assert orchestrator.plan_builder is not None
        assert orchestrator.source_executor is not None

        # Dependencies should be separate instances
        assert orchestrator.plan_builder != orchestrator.source_executor

    def test_single_responsibility_principle(self):
        """Test that each class has exactly one reason to change"""

        # PlanBuilder: Changes when plan building logic changes
        from src.services.ingestion.managers.IngestionPlanBuilder import (
            IngestionPlanBuilder,
        )

        plan_builder = IngestionPlanBuilder()

        # Should only have plan-related methods
        plan_methods = [
            method
            for method in dir(plan_builder)
            if not method.startswith("_") and callable(getattr(plan_builder, method))
        ]

        # All methods should be related to plan building
        for method in plan_methods:
            method_name = method.lower()
            assert any(
                keyword in method_name
                for keyword in ["plan", "build", "validate", "optimize", "config"]
            )

        # SourceExecutor: Changes when source execution logic changes
        from src.services.ingestion.managers.SourceExecutor import SourceExecutor

        source_executor = SourceExecutor()

        # Should only have execution-related methods
        execution_methods = [
            method
            for method in dir(source_executor)
            if not method.startswith("_") and callable(getattr(source_executor, method))
        ]

        # All methods should be related to source execution
        for method in execution_methods:
            method_name = method.lower()
            assert any(
                keyword in method_name
                for keyword in ["execute", "source", "cache", "web", "arxiv", "pubmed"]
            )


class TestArchitecturalBenefits:
    """Test architectural benefits of SRP refactoring"""

    def test_separation_of_concerns(self):
        """Test that concerns are properly separated"""

        # Plan building is separate from execution
        from src.services.ingestion.managers.IngestionPlanBuilder import (
            IngestionPlanBuilder,
        )
        from src.services.ingestion.managers.SourceExecutor import SourceExecutor

        plan_builder = IngestionPlanBuilder()
        source_executor = SourceExecutor()

        # They should be independent
        assert plan_builder != source_executor
        assert not hasattr(plan_builder, "source_executor")
        assert not hasattr(source_executor, "plan_builder")

    def test_testability_improvement(self):
        """Test that refactored services are more testable"""

        # Each service can be tested in isolation
        from src.services.ingestion.managers.IngestionPlanBuilder import (
            IngestionPlanBuilder,
        )

        builder = IngestionPlanBuilder()

        # Can test plan building without dependencies
        assert builder.build_plan is not None
        assert builder.optimize_plan is not None

        # Can mock dependencies easily
        mock_config = MagicMock()
        builder.config = mock_config
        assert builder.config == mock_config

    def test_maintainability_improvement(self):
        """Test that refactored services are more maintainable"""

        # Changes to plan building don't affect execution
        from src.services.ingestion.managers.IngestionPlanBuilder import (
            IngestionPlanBuilder,
        )
        from src.services.ingestion.managers.SourceExecutor import SourceExecutor

        plan_builder = IngestionPlanBuilder()
        source_executor = SourceExecutor()

        # They have different responsibilities
        plan_responsibilities = ["build_plan", "optimize_plan", "_validate_plan"]
        execution_responsibilities = ["execute_source", "get_source_cache_key"]

        for resp in plan_responsibilities:
            assert hasattr(plan_builder, resp)
            assert not hasattr(source_executor, resp)

        for resp in execution_responsibilities:
            assert hasattr(source_executor, resp)
            assert not hasattr(plan_builder, resp)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
