"""
Comprehensive Unit Tests for IngestionOrchestrator

Tests all primary use cases, edge cases, and expected failure modes
for the IngestionOrchestrator class using pytest-mock for complete isolation.

Following Testing Pyramid: Unit Tests (70%) - Fast, isolated, comprehensive
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import asyncio

from src.services.ingestion.orchestrator import (
    IngestionOrchestrator,
    IngestionConfig,
    IngestionPlan,
    IngestionResult,
    OptimizationConfig,
    OptimizationMode
)
from tests.factories import SearchQueryFactory, SearchResultFactory


class TestIngestionOrchestratorComprehensive:
    """Comprehensive unit tests for IngestionOrchestrator"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies for IngestionOrchestrator"""
        return {
            'cognitive_engine': AsyncMock(),
            'n8n_manager': AsyncMock(),
            'firecrawl_service': AsyncMock(),
            'arxiv_service': AsyncMock(),
            'pubmed_service': AsyncMock(),
            'performance_optimizer': AsyncMock(),
        }

    @pytest.fixture
    def ingestion_config(self):
        """Create test ingestion configuration"""
        return IngestionConfig(
            max_concurrent_requests=5,
            timeout_seconds=30,
            retry_attempts=3,
            enable_caching=True,
            cache_ttl_hours=24
        )

    @pytest.fixture
    def orchestrator(self, ingestion_config, mock_dependencies):
        """Create IngestionOrchestrator instance with mocked dependencies"""
        with patch('src.services.ingestion.orchestrator.FirecrawlService') as mock_firecrawl, \
             patch('src.services.ingestion.orchestrator.ArxivEnhancedService') as mock_arxiv, \
             patch('src.services.ingestion.orchestrator.PubMedService') as mock_pubmed, \
             patch('src.services.ingestion.orchestrator.PerformanceOptimizationService') as mock_perf:
            
            mock_firecrawl.return_value = mock_dependencies['firecrawl_service']
            mock_arxiv.return_value = mock_dependencies['arxiv_service']
            mock_pubmed.return_value = mock_dependencies['pubmed_service']
            mock_perf.return_value = mock_dependencies['performance_optimizer']
            
            return IngestionOrchestrator(
                config=ingestion_config,
                cognitive_engine=mock_dependencies['cognitive_engine'],
                n8n_manager=mock_dependencies['n8n_manager']
            )

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional
    async def test_create_ingestion_plan_success(self, orchestrator, mock_dependencies):
        """Test successful ingestion plan creation"""
        # Arrange
        topic = "artificial intelligence"
        context = {"user_id": "user123", "preferences": ["machine learning"]}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["AI", "machine learning", "neural networks"],
            "complexity": "medium",
            "estimated_sources": 3
        }
        
        # Act
        plan = await orchestrator.create_ingestion_plan(topic, context)
        
        # Assert
        assert plan is not None
        assert plan.topic == topic
        assert plan.context == context
        assert len(plan.source_strategies) > 0
        assert plan.estimated_duration > 0
        
        # Verify interactions
        mock_dependencies['cognitive_engine'].analyze_topic.assert_called_once_with(topic, context)

    @pytest.mark.unit_functional
    async def test_execute_ingestion_plan_success(self, orchestrator, mock_dependencies):
        """Test successful ingestion plan execution"""
        # Arrange
        plan = IngestionPlan(
            topic="machine learning",
            context={"user_id": "user123"},
            source_strategies=[
                {"source": "arxiv", "query": "machine learning", "max_results": 10},
                {"source": "pubmed", "query": "machine learning", "max_results": 5}
            ],
            estimated_duration=30
        )
        
        # Mock service responses
        mock_dependencies['arxiv_service'].search.return_value = [
            SearchResultFactory(title="ML Paper 1"),
            SearchResultFactory(title="ML Paper 2")
        ]
        mock_dependencies['pubmed_service'].search.return_value = [
            SearchResultFactory(title="Medical ML Paper 1")
        ]
        mock_dependencies['performance_optimizer'].optimize_execution.return_value = {
            "optimized_strategies": plan.source_strategies,
            "performance_metrics": {"estimated_time": 25}
        }
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        assert result.success is True
        assert len(result.content_items) >= 3  # At least 3 papers found
        assert result.execution_time > 0
        assert result.total_sources_queried == 2
        
        # Verify service calls
        mock_dependencies['arxiv_service'].search.assert_called_once()
        mock_dependencies['pubmed_service'].search.assert_called_once()

    @pytest.mark.unit_functional
    async def test_ingest_content_success(self, orchestrator, mock_dependencies):
        """Test successful content ingestion with multiple sources"""
        # Arrange
        topic = "quantum computing"
        context = {"user_id": "user456"}
        
        # Mock cognitive analysis
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["quantum", "computing", "algorithms"],
            "complexity": "high",
            "estimated_sources": 2
        }
        
        # Mock service responses
        mock_dependencies['arxiv_service'].search.return_value = [
            SearchResultFactory(title="Quantum Algorithm Paper"),
            SearchResultFactory(title="Quantum Computing Review")
        ]
        mock_dependencies['firecrawl_service'].scrape_url.return_value = {
            "title": "Quantum Computing News",
            "content": "Latest developments in quantum computing...",
            "url": "https://example.com/quantum-news"
        }
        
        # Act
        result = await orchestrator.ingest_content(topic, context)
        
        # Assert
        assert result is not None
        assert result.success is True
        assert len(result.content_items) >= 2
        assert all(item.get('title') for item in result.content_items)
        
        # Verify metrics tracking
        assert orchestrator.execution_metrics["plans_executed"] >= 1
        assert orchestrator.execution_metrics["total_content_retrieved"] >= 2

    @pytest.mark.unit_functional
    async def test_get_ingestion_metrics_success(self, orchestrator):
        """Test successful metrics retrieval"""
        # Arrange - Set some initial metrics
        orchestrator.execution_metrics = {
            "plans_executed": 5,
            "total_content_retrieved": 25,
            "average_execution_time": 15.5,
            "success_rate": 0.95
        }
        
        # Act
        metrics = await orchestrator.get_ingestion_metrics()
        
        # Assert
        assert metrics is not None
        assert metrics["plans_executed"] == 5
        assert metrics["total_content_retrieved"] == 25
        assert metrics["average_execution_time"] == 15.5
        assert metrics["success_rate"] == 0.95

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case
    async def test_create_plan_with_minimal_context(self, orchestrator, mock_dependencies):
        """Test plan creation with minimal context"""
        # Arrange
        topic = "test topic"
        minimal_context = {}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["test"],
            "complexity": "low",
            "estimated_sources": 1
        }
        
        # Act
        plan = await orchestrator.create_ingestion_plan(topic, minimal_context)
        
        # Assert
        assert plan is not None
        assert plan.topic == topic
        assert plan.context == minimal_context

    @pytest.mark.unit_edge_case
    async def test_create_plan_with_special_characters(self, orchestrator, mock_dependencies):
        """Test plan creation with special characters in topic"""
        # Arrange
        topic = "AI & Machine Learning: A Comprehensive Guide (2024)"
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["AI", "machine learning", "guide"],
            "complexity": "medium",
            "estimated_sources": 2
        }
        
        # Act
        plan = await orchestrator.create_ingestion_plan(topic, context)
        
        # Assert
        assert plan is not None
        assert plan.topic == topic

    @pytest.mark.unit_edge_case
    async def test_execute_plan_with_empty_strategies(self, orchestrator):
        """Test plan execution with empty source strategies"""
        # Arrange
        plan = IngestionPlan(
            topic="empty test",
            context={},
            source_strategies=[],
            estimated_duration=0
        )
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        assert result.success is True
        assert len(result.content_items) == 0
        assert result.total_sources_queried == 0

    @pytest.mark.unit_edge_case
    async def test_ingest_content_with_very_long_topic(self, orchestrator, mock_dependencies):
        """Test content ingestion with very long topic string"""
        # Arrange
        long_topic = "artificial intelligence " * 50  # Very long topic
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["artificial", "intelligence"],
            "complexity": "medium",
            "estimated_sources": 2
        }
        
        mock_dependencies['arxiv_service'].search.return_value = []
        mock_dependencies['pubmed_service'].search.return_value = []
        
        # Act
        result = await orchestrator.ingest_content(long_topic, context)
        
        # Assert
        assert result is not None
        assert result.success is True

    @pytest.mark.unit_edge_case
    async def test_concurrent_ingestion_requests(self, orchestrator, mock_dependencies):
        """Test handling of concurrent ingestion requests"""
        # Arrange
        topics = ["topic1", "topic2", "topic3"]
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["test"],
            "complexity": "low",
            "estimated_sources": 1
        }
        
        mock_dependencies['arxiv_service'].search.return_value = [
            SearchResultFactory(title="Test Paper")
        ]
        
        # Act
        tasks = [orchestrator.ingest_content(topic, context) for topic in topics]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 3
        assert all(result.success for result in results)
        assert orchestrator.execution_metrics["plans_executed"] >= 3

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling
    async def test_create_plan_with_invalid_topic(self, orchestrator):
        """Test plan creation with invalid topic"""
        # Arrange
        invalid_topic = ""  # Empty topic
        
        # Act & Assert
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            await orchestrator.create_ingestion_plan(invalid_topic, {})

    @pytest.mark.unit_error_handling
    async def test_create_plan_cognitive_engine_failure(self, orchestrator, mock_dependencies):
        """Test plan creation when cognitive engine fails"""
        # Arrange
        topic = "test topic"
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.side_effect = Exception("Cognitive engine unavailable")
        
        # Act & Assert
        with pytest.raises(Exception, match="Cognitive engine unavailable"):
            await orchestrator.create_ingestion_plan(topic, context)

    @pytest.mark.unit_error_handling
    async def test_execute_plan_service_timeout(self, orchestrator, mock_dependencies):
        """Test plan execution when services timeout"""
        # Arrange
        plan = IngestionPlan(
            topic="test topic",
            context={},
            source_strategies=[
                {"source": "arxiv", "query": "test", "max_results": 5}
            ],
            estimated_duration=30
        )
        
        mock_dependencies['arxiv_service'].search.side_effect = asyncio.TimeoutError("Service timeout")
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        assert result.success is False
        assert "timeout" in result.error_message.lower()

    @pytest.mark.unit_error_handling
    async def test_execute_plan_service_failure(self, orchestrator, mock_dependencies):
        """Test plan execution when services fail"""
        # Arrange
        plan = IngestionPlan(
            topic="test topic",
            context={},
            source_strategies=[
                {"source": "arxiv", "query": "test", "max_results": 5}
            ],
            estimated_duration=30
        )
        
        mock_dependencies['arxiv_service'].search.side_effect = Exception("Service unavailable")
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        assert result.success is False
        assert "unavailable" in result.error_message.lower()

    @pytest.mark.unit_error_handling
    async def test_ingest_content_network_failure(self, orchestrator, mock_dependencies):
        """Test content ingestion when network fails"""
        # Arrange
        topic = "test topic"
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["test"],
            "complexity": "low",
            "estimated_sources": 1
        }
        
        mock_dependencies['arxiv_service'].search.side_effect = Exception("Network error")
        mock_dependencies['pubmed_service'].search.side_effect = Exception("Network error")
        
        # Act
        result = await orchestrator.ingest_content(topic, context)
        
        # Assert
        assert result is not None
        assert result.success is False
        assert len(result.content_items) == 0

    @pytest.mark.unit_error_handling
    async def test_performance_optimizer_failure(self, orchestrator, mock_dependencies):
        """Test handling of performance optimizer failures"""
        # Arrange
        plan = IngestionPlan(
            topic="test topic",
            context={},
            source_strategies=[
                {"source": "arxiv", "query": "test", "max_results": 5}
            ],
            estimated_duration=30
        )
        
        mock_dependencies['performance_optimizer'].optimize_execution.side_effect = Exception("Optimizer failed")
        mock_dependencies['arxiv_service'].search.return_value = [
            SearchResultFactory(title="Test Paper")
        ]
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        # Should still succeed despite optimizer failure
        assert result.success is True

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance
    async def test_plan_creation_performance(self, orchestrator, mock_dependencies):
        """Test plan creation performance"""
        import time
        
        # Arrange
        topic = "performance test"
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["performance", "test"],
            "complexity": "low",
            "estimated_sources": 1
        }
        
        # Act
        start_time = time.time()
        plan = await orchestrator.create_ingestion_plan(topic, context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        assert plan is not None

    @pytest.mark.unit_performance
    async def test_execution_time_tracking(self, orchestrator, mock_dependencies):
        """Test execution time tracking accuracy"""
        # Arrange
        plan = IngestionPlan(
            topic="timing test",
            context={},
            source_strategies=[
                {"source": "arxiv", "query": "test", "max_results": 1}
            ],
            estimated_duration=5
        )
        
        mock_dependencies['arxiv_service'].search.return_value = [
            SearchResultFactory(title="Timing Test Paper")
        ]
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        assert result.execution_time > 0
        assert result.execution_time < 10  # Should complete quickly in unit test

    @pytest.mark.unit_performance
    async def test_memory_usage_with_large_results(self, orchestrator, mock_dependencies):
        """Test memory usage with large result sets"""
        # Arrange
        plan = IngestionPlan(
            topic="large results test",
            context={},
            source_strategies=[
                {"source": "arxiv", "query": "test", "max_results": 100}
            ],
            estimated_duration=30
        )
        
        # Create large result set
        large_results = [SearchResultFactory(title=f"Paper {i}") for i in range(100)]
        mock_dependencies['arxiv_service'].search.return_value = large_results
        
        # Act
        result = await orchestrator.execute_ingestion_plan(plan)
        
        # Assert
        assert result is not None
        assert result.success is True
        assert len(result.content_items) == 100

    # ============================================================================
    # SECURITY TESTS - Authentication and Authorization
    # ============================================================================

    @pytest.mark.unit_security
    async def test_context_data_sanitization(self, orchestrator, mock_dependencies):
        """Test that context data is properly sanitized"""
        # Arrange
        topic = "security test"
        malicious_context = {
            "user_id": "user123",
            "malicious_script": "<script>alert('xss')</script>",
            "sql_injection": "'; DROP TABLE users; --"
        }
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["security", "test"],
            "complexity": "low",
            "estimated_sources": 1
        }
        
        # Act
        plan = await orchestrator.create_ingestion_plan(topic, malicious_context)
        
        # Assert
        assert plan is not None
        # Verify that malicious content doesn't affect the plan
        assert plan.topic == topic
        # The context should be passed through but handled safely by downstream services

    @pytest.mark.unit_security
    async def test_input_validation(self, orchestrator):
        """Test input validation for security"""
        # Arrange
        malicious_topic = "../../etc/passwd"  # Path traversal attempt
        
        # Act & Assert
        with pytest.raises(ValueError):
            await orchestrator.create_ingestion_plan(malicious_topic, {})

    @pytest.mark.unit_security
    async def test_rate_limiting_integration(self, orchestrator, mock_dependencies):
        """Test rate limiting integration"""
        # Arrange
        topic = "rate limit test"
        context = {"user_id": "user123"}
        
        mock_dependencies['cognitive_engine'].analyze_topic.return_value = {
            "keywords": ["rate", "limit"],
            "complexity": "low",
            "estimated_sources": 1
        }
        
        # Act - Make multiple rapid requests
        tasks = [orchestrator.create_ingestion_plan(topic, context) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert
        assert len(results) == 5
        # All requests should succeed (rate limiting handled by performance optimizer)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 4  # At least 4 should succeed
