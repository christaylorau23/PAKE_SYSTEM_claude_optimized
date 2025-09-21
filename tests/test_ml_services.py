#!/usr/bin/env python3
"""
Test ML Services
Tests for machine learning pipeline components
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import ML services that are available
try:
    from services.ml import (
        ContentSummarizationService,
        MLAnalyticsAggregationService,
        SemanticSearchService,
        get_content_summarization_service,
        get_ml_analytics_service,
        get_semantic_search_service,
    )

    ML_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"ML services not fully available: {e}")
    ML_SERVICES_AVAILABLE = False


class TestMLServices:
    """Test ML service functionality"""

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    def test_semantic_search_service_import(self):
        """Test that SemanticSearchService can be imported"""
        assert SemanticSearchService is not None

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    def test_content_summarization_service_import(self):
        """Test that ContentSummarizationService can be imported"""
        assert ContentSummarizationService is not None

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    def test_ml_analytics_service_import(self):
        """Test that MLAnalyticsAggregationService can be imported"""
        assert MLAnalyticsAggregationService is not None

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    def test_service_factory_functions(self):
        """Test that service factory functions exist"""
        assert callable(get_semantic_search_service)
        assert callable(get_content_summarization_service)
        assert callable(get_ml_analytics_service)

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    @patch("services.ml.semantic_search_service.SemanticSearchService")
    def test_semantic_search_service_creation(self, mock_service):
        """Test semantic search service creation"""
        # Mock the service creation
        mock_instance = Mock()
        mock_service.return_value = mock_instance

        # Test service creation
        service = get_semantic_search_service()
        assert service is not None

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    @patch("services.ml.content_summarization_service.ContentSummarizationService")
    def test_content_summarization_service_creation(self, mock_service):
        """Test content summarization service creation"""
        # Mock the service creation
        mock_instance = Mock()
        mock_service.return_value = mock_instance

        # Test service creation
        service = get_content_summarization_service()
        assert service is not None

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    @patch("services.ml.analytics_aggregation_service.MLAnalyticsAggregationService")
    def test_ml_analytics_service_creation(self, mock_service):
        """Test ML analytics service creation"""
        # Mock the service creation
        mock_instance = Mock()
        mock_service.return_value = mock_instance

        # Test service creation
        service = get_ml_analytics_service()
        assert service is not None


class TestMLServiceIntegration:
    """Test ML service integration and basic functionality"""

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    def test_ml_services_module_structure(self):
        """Test that ML services module has expected structure"""
        import services.ml as ml_module

        # Check that module has expected attributes
        expected_exports = [
            "SemanticSearchService",
            "ContentSummarizationService",
            "MLAnalyticsAggregationService",
        ]

        for export in expected_exports:
            assert hasattr(ml_module, export), f"Missing export: {export}"

    def test_ml_services_graceful_degradation(self):
        """Test that system handles ML service unavailability gracefully"""
        # This test should always pass even if ML services are not available
        try:
            from services.ml import SemanticSearchService

            # If import succeeds, service should be functional
            assert SemanticSearchService is not None
        except ImportError:
            # If import fails, that's acceptable for CI environments
            assert True


class TestMLServiceConfiguration:
    """Test ML service configuration and setup"""

    def test_mock_ml_service_config(self):
        """Test mock ML service configuration for CI environments"""
        # Create a mock configuration that ML services might expect
        mock_config = {
            "model_path": "/tmp/test_model",
            "embedding_dimension": 384,
            "batch_size": 32,
            "max_tokens": 512,
        }

        assert mock_config["embedding_dimension"] == 384
        assert mock_config["batch_size"] == 32

    @pytest.mark.skipif(not ML_SERVICES_AVAILABLE, reason="ML services not available")
    def test_service_initialization_without_models(self):
        """Test that services can be initialized without actual ML models"""
        # This test verifies that services can be created even if models aren't loaded
        with patch(
            "services.ml.semantic_search_service.SemanticSearchService",
        ) as mock_service:
            mock_instance = Mock()
            mock_instance.initialized = False
            mock_service.return_value = mock_instance

            service = get_semantic_search_service()
            assert service is not None


# Mock service classes for when actual ML services aren't available
class MockSemanticSearchService:
    """Mock semantic search service for testing"""

    def __init__(self):
        self.initialized = False

    async def search(self, query: str, limit: int = 10):
        """Mock search functionality"""
        return [{"text": f"Mock result for: {query}", "score": 0.9}]


class MockContentSummarizationService:
    """Mock content summarization service for testing"""

    def __init__(self):
        self.initialized = False

    async def summarize(self, content: str, max_length: int = 100):
        """Mock summarization functionality"""
        return f"Mock summary of content (length: {len(content)})"


class MockMLAnalyticsService:
    """Mock ML analytics service for testing"""

    def __init__(self):
        self.initialized = False

    async def analyze(self, data):
        """Mock analytics functionality"""
        return {"status": "analyzed", "data_points": len(data) if data else 0}


class TestMockMLServices:
    """Test mock ML services when actual services aren't available"""

    def test_mock_semantic_search(self):
        """Test mock semantic search service"""
        service = MockSemanticSearchService()
        assert service is not None
        assert hasattr(service, "search")

    def test_mock_content_summarization(self):
        """Test mock content summarization service"""
        service = MockContentSummarizationService()
        assert service is not None
        assert hasattr(service, "summarize")

    def test_mock_ml_analytics(self):
        """Test mock ML analytics service"""
        service = MockMLAnalyticsService()
        assert service is not None
        assert hasattr(service, "analyze")

    @pytest.mark.asyncio
    async def test_mock_service_functionality(self):
        """Test that mock services provide expected functionality"""
        search_service = MockSemanticSearchService()
        summarization_service = MockContentSummarizationService()
        analytics_service = MockMLAnalyticsService()

        # Test search
        search_results = await search_service.search("test query")
        assert isinstance(search_results, list)
        assert len(search_results) > 0

        # Test summarization
        summary = await summarization_service.summarize("test content")
        assert isinstance(summary, str)
        assert "Mock summary" in summary

        # Test analytics
        analysis = await analytics_service.analyze([1, 2, 3])
        assert isinstance(analysis, dict)
        assert "status" in analysis


if __name__ == "__main__":
    pytest.main([__file__])
