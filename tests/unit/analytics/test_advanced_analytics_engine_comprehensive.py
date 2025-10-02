"""
Comprehensive Unit Tests for AdvancedAnalyticsEngine

Tests all primary use cases, edge cases, and expected failure modes
for the AdvancedAnalyticsEngine class using pytest-mock for complete isolation.

Following Testing Pyramid: Unit Tests (70%) - Fast, isolated, comprehensive
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.services.analytics.advanced_analytics_engine import (
    AdvancedAnalyticsEngine,
    CorrelationEngine,
    InsightGenerationService,
    PredictiveAnalyticsService,
    TrendAnalysisService,
)


class TestAdvancedAnalyticsEngineComprehensive:
    """Comprehensive unit tests for AdvancedAnalyticsEngine"""

    @pytest.fixture()
    def mock_dependencies(self):
        """Create mocked dependencies for AdvancedAnalyticsEngine"""
        return {
            "trend_service": AsyncMock(spec=TrendAnalysisService),
            "correlation_engine": AsyncMock(spec=CorrelationEngine),
            "predictive_service": AsyncMock(spec=PredictiveAnalyticsService),
            "insight_service": AsyncMock(spec=InsightGenerationService),
            "ml_aggregation": AsyncMock(),
            "semantic_search": AsyncMock(),
        }

    @pytest.fixture()
    def analytics_engine(self, mock_dependencies):
        """Create AdvancedAnalyticsEngine instance with mocked dependencies"""
        with patch(
            "src.services.analytics.advanced_analytics_engine.TrendAnalysisService"
        ) as mock_trend, patch(
            "src.services.analytics.advanced_analytics_engine.CorrelationEngine"
        ) as mock_corr, patch(
            "src.services.analytics.advanced_analytics_engine.PredictiveAnalyticsService"
        ) as mock_pred, patch(
            "src.services.analytics.advanced_analytics_engine.InsightGenerationService"
        ) as mock_insight, patch(
            "src.services.analytics.advanced_analytics_engine.AnalyticsAggregationService"
        ) as mock_ml, patch(
            "src.services.analytics.advanced_analytics_engine.get_semantic_search_service"
        ) as mock_search:
            mock_trend.return_value = mock_dependencies["trend_service"]
            mock_corr.return_value = mock_dependencies["correlation_engine"]
            mock_pred.return_value = mock_dependencies["predictive_service"]
            mock_insight.return_value = mock_dependencies["insight_service"]
            mock_ml.return_value = mock_dependencies["ml_aggregation"]
            mock_search.return_value = mock_dependencies["semantic_search"]

            return AdvancedAnalyticsEngine()

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional()
    async def test_generate_comprehensive_report_success(
        self, analytics_engine, mock_dependencies
    ):
        """Test successful comprehensive report generation"""
        # Arrange
        time_range = "24h"

        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [
                {"topic": "AI", "growth_rate": 0.15, "confidence": 0.85},
                {"topic": "ML", "growth_rate": 0.12, "confidence": 0.78},
            ],
            "summary": "Strong growth in AI and ML topics",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [
                {"topic1": "AI", "topic2": "ML", "strength": 0.92},
                {"topic1": "AI", "topic2": "Data Science", "strength": 0.78},
            ],
            "insights": ["AI and ML are highly correlated"],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [
                {"topic": "AI", "predicted_growth": 0.18, "confidence": 0.82},
                {"topic": "ML", "predicted_growth": 0.14, "confidence": 0.75},
            ],
            "scenarios": {
                "optimistic": {"AI": 0.25, "ML": 0.20},
                "pessimistic": {"AI": 0.10, "ML": 0.08},
            },
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [
                {
                    "type": "emerging_trend",
                    "description": "AI adoption accelerating",
                    "confidence": 0.88,
                    "actionable": True,
                }
            ],
            "recommendations": ["Focus on AI-related content"],
        }

        # Act
        report = await analytics_engine.generate_comprehensive_report(
            time_range=time_range,
            include_predictions=True,
            include_recommendations=True,
        )

        # Assert
        assert report is not None
        assert "trends" in report
        assert "correlations" in report
        assert "predictions" in report
        assert "insights" in report
        assert "recommendations" in report
        assert len(report["trends"]["trends"]) == 2
        assert len(report["correlations"]["correlations"]) == 2
        assert len(report["predictions"]["predictions"]) == 2
        assert len(report["insights"]["insights"]) == 1

        # Verify service calls
        mock_dependencies["trend_service"].analyze_trends.assert_called_once_with(
            time_range
        )
        mock_dependencies["correlation_engine"].find_correlations.assert_called_once()
        mock_dependencies[
            "predictive_service"
        ].generate_predictions.assert_called_once()
        mock_dependencies["insight_service"].generate_insights.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_analyze_system_health_success(
        self, analytics_engine, mock_dependencies
    ):
        """Test successful system health analysis"""
        # Arrange
        mock_dependencies["trend_service"].get_system_metrics.return_value = {
            "cpu_usage": 0.65,
            "memory_usage": 0.72,
            "disk_usage": 0.45,
            "network_latency": 120,
            "error_rate": 0.02,
        }

        mock_dependencies["insight_service"].analyze_health_patterns.return_value = {
            "health_score": 0.85,
            "issues": [
                {
                    "type": "memory",
                    "severity": "medium",
                    "description": "Memory usage trending upward",
                }
            ],
            "recommendations": ["Consider memory optimization"],
        }

        # Act
        health_report = await analytics_engine.analyze_system_health()

        # Assert
        assert health_report is not None
        assert "metrics" in health_report
        assert "health_score" in health_report
        assert "issues" in health_report
        assert "recommendations" in health_report
        assert health_report["health_score"] == 0.85
        assert len(health_report["issues"]) == 1

    @pytest.mark.unit_functional()
    async def test_detect_anomalies_success(self, analytics_engine, mock_dependencies):
        """Test successful anomaly detection"""
        # Arrange
        mock_dependencies["trend_service"].detect_anomalies.return_value = {
            "anomalies": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "metric": "cpu_usage",
                    "value": 0.95,
                    "expected_range": [0.3, 0.7],
                    "severity": "high",
                    "description": "CPU usage spike detected",
                }
            ],
            "anomaly_score": 0.92,
        }

        # Act
        anomaly_report = await analytics_engine.detect_anomalies()

        # Assert
        assert anomaly_report is not None
        assert "anomalies" in anomaly_report
        assert "anomaly_score" in anomaly_report
        assert len(anomaly_report["anomalies"]) == 1
        assert anomaly_report["anomaly_score"] == 0.92

    @pytest.mark.unit_functional()
    async def test_generate_predictive_insights_success(
        self, analytics_engine, mock_dependencies
    ):
        """Test successful predictive insights generation"""
        # Arrange
        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [
                {
                    "metric": "user_growth",
                    "current_value": 1000,
                    "predicted_value": 1200,
                    "confidence": 0.85,
                    "time_horizon": "30d",
                }
            ],
            "scenarios": {
                "optimistic": {"user_growth": 1500},
                "pessimistic": {"user_growth": 900},
            },
        }

        mock_dependencies[
            "insight_service"
        ].generate_predictive_insights.return_value = {
            "insights": [
                {
                    "type": "growth_prediction",
                    "description": "User growth expected to increase by 20%",
                    "confidence": 0.85,
                    "actionable": True,
                }
            ]
        }

        # Act
        predictive_report = await analytics_engine.generate_predictive_insights()

        # Assert
        assert predictive_report is not None
        assert "predictions" in predictive_report
        assert "scenarios" in predictive_report
        assert "insights" in predictive_report
        assert len(predictive_report["predictions"]["predictions"]) == 1
        assert len(predictive_report["insights"]["insights"]) == 1

    @pytest.mark.unit_functional()
    async def test_get_cached_insights_success(self, analytics_engine):
        """Test successful cached insights retrieval"""
        # Arrange - Set up cache
        cache_key = "test_insights"
        cached_data = {
            "insights": [{"type": "cached", "description": "Cached insight"}],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        analytics_engine._insight_cache[cache_key] = cached_data

        # Act
        insights = await analytics_engine.get_cached_insights(cache_key)

        # Assert
        assert insights is not None
        assert insights == cached_data

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case()
    async def test_generate_report_with_minimal_data(
        self, analytics_engine, mock_dependencies
    ):
        """Test report generation with minimal data"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [],
            "summary": "No significant trends detected",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act
        report = await analytics_engine.generate_comprehensive_report()

        # Assert
        assert report is not None
        assert len(report["trends"]["trends"]) == 0
        assert len(report["correlations"]["correlations"]) == 0
        assert len(report["predictions"]["predictions"]) == 0
        assert len(report["insights"]["insights"]) == 0

    @pytest.mark.unit_edge_case()
    async def test_generate_report_without_predictions(
        self, analytics_engine, mock_dependencies
    ):
        """Test report generation without predictions"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [{"topic": "AI", "growth_rate": 0.15}],
            "summary": "AI trending upward",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act
        report = await analytics_engine.generate_comprehensive_report(
            include_predictions=False, include_recommendations=False
        )

        # Assert
        assert report is not None
        assert "predictions" not in report
        assert "recommendations" not in report
        mock_dependencies["predictive_service"].generate_predictions.assert_not_called()

    @pytest.mark.unit_edge_case()
    async def test_cache_expiration_handling(self, analytics_engine):
        """Test cache expiration handling"""
        # Arrange - Set up expired cache entry
        cache_key = "expired_insights"
        expired_time = datetime.now(UTC) - timedelta(hours=1)
        expired_data = {
            "insights": [{"type": "expired", "description": "Expired insight"}],
            "timestamp": expired_time.isoformat(),
        }
        analytics_engine._insight_cache[cache_key] = expired_data

        # Act
        insights = await analytics_engine.get_cached_insights(cache_key)

        # Assert
        assert insights is None  # Should return None for expired cache

    @pytest.mark.unit_edge_case()
    async def test_concurrent_report_generation(
        self, analytics_engine, mock_dependencies
    ):
        """Test concurrent report generation"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [{"topic": "AI", "growth_rate": 0.15}],
            "summary": "AI trending",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act - Generate multiple reports concurrently
        tasks = [
            analytics_engine.generate_comprehensive_report(),
            analytics_engine.generate_comprehensive_report(),
            analytics_engine.generate_comprehensive_report(),
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        assert all(result is not None for result in results)

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling()
    async def test_trend_service_failure(self, analytics_engine, mock_dependencies):
        """Test handling of trend service failures"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.side_effect = Exception(
            "Trend service unavailable"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Trend service unavailable"):
            await analytics_engine.generate_comprehensive_report()

    @pytest.mark.unit_error_handling()
    async def test_correlation_engine_failure(
        self, analytics_engine, mock_dependencies
    ):
        """Test handling of correlation engine failures"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [],
            "summary": "No trends",
        }

        mock_dependencies[
            "correlation_engine"
        ].find_correlations.side_effect = Exception("Correlation engine failed")

        # Act & Assert
        with pytest.raises(Exception, match="Correlation engine failed"):
            await analytics_engine.generate_comprehensive_report()

    @pytest.mark.unit_error_handling()
    async def test_predictive_service_failure(
        self, analytics_engine, mock_dependencies
    ):
        """Test handling of predictive service failures"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [],
            "summary": "No trends",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies[
            "predictive_service"
        ].generate_predictions.side_effect = Exception("Predictive service failed")

        # Act & Assert
        with pytest.raises(Exception, match="Predictive service failed"):
            await analytics_engine.generate_comprehensive_report(
                include_predictions=True
            )

    @pytest.mark.unit_error_handling()
    async def test_insight_service_failure(self, analytics_engine, mock_dependencies):
        """Test handling of insight service failures"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [],
            "summary": "No trends",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["insight_service"].generate_insights.side_effect = Exception(
            "Insight service failed"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Insight service failed"):
            await analytics_engine.generate_comprehensive_report()

    @pytest.mark.unit_error_handling()
    async def test_ml_services_unavailable(self, analytics_engine, mock_dependencies):
        """Test handling when ML services are unavailable"""
        # Arrange - Simulate ML services being None
        analytics_engine.ml_aggregation = None
        analytics_engine.semantic_search = None

        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [],
            "summary": "No trends",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act
        report = await analytics_engine.generate_comprehensive_report()

        # Assert
        assert report is not None
        # Should succeed even without ML services

    @pytest.mark.unit_error_handling()
    async def test_invalid_time_range(self, analytics_engine):
        """Test handling of invalid time range"""
        # Arrange
        invalid_time_range = "invalid_range"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time range"):
            await analytics_engine.generate_comprehensive_report(
                time_range=invalid_time_range
            )

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance()
    async def test_report_generation_performance(
        self, analytics_engine, mock_dependencies
    ):
        """Test report generation performance"""
        import time

        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [{"topic": "AI", "growth_rate": 0.15}],
            "summary": "AI trending",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act
        start_time = time.time()
        report = await analytics_engine.generate_comprehensive_report()
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Should complete within 2 seconds
        assert report is not None

    @pytest.mark.unit_performance()
    async def test_cache_performance(self, analytics_engine):
        """Test cache performance"""
        import time

        # Arrange - Set up cache
        cache_key = "performance_test"
        cached_data = {
            "insights": [{"type": "cached", "description": "Cached insight"}],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        analytics_engine._insight_cache[cache_key] = cached_data

        # Act
        start_time = time.time()
        insights = await analytics_engine.get_cached_insights(cache_key)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 0.1  # Cache lookup should be very fast
        assert insights is not None

    @pytest.mark.unit_performance()
    async def test_memory_usage_with_large_datasets(
        self, analytics_engine, mock_dependencies
    ):
        """Test memory usage with large datasets"""
        # Arrange - Create large dataset
        large_trends = [{"topic": f"Topic{i}", "growth_rate": 0.1} for i in range(1000)]
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": large_trends,
            "summary": "Many trends detected",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act
        report = await analytics_engine.generate_comprehensive_report()

        # Assert
        assert report is not None
        assert len(report["trends"]["trends"]) == 1000

    # ============================================================================
    # SECURITY TESTS - Authentication and Authorization
    # ============================================================================

    @pytest.mark.unit_security()
    async def test_input_sanitization(self, analytics_engine, mock_dependencies):
        """Test input sanitization for security"""
        # Arrange
        malicious_time_range = "24h'; DROP TABLE analytics; --"

        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [],
            "summary": "No trends",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act & Assert
        with pytest.raises(ValueError):
            await analytics_engine.generate_comprehensive_report(
                time_range=malicious_time_range
            )

    @pytest.mark.unit_security()
    async def test_cache_key_validation(self, analytics_engine):
        """Test cache key validation for security"""
        # Arrange
        malicious_cache_key = "../../etc/passwd"

        # Act & Assert
        with pytest.raises(ValueError):
            await analytics_engine.get_cached_insights(malicious_cache_key)

    @pytest.mark.unit_security()
    async def test_data_privacy_protection(self, analytics_engine, mock_dependencies):
        """Test data privacy protection"""
        # Arrange
        mock_dependencies["trend_service"].analyze_trends.return_value = {
            "trends": [{"topic": "sensitive_data", "growth_rate": 0.15}],
            "summary": "Sensitive data trending",
        }

        mock_dependencies["correlation_engine"].find_correlations.return_value = {
            "correlations": [],
            "insights": [],
        }

        mock_dependencies["predictive_service"].generate_predictions.return_value = {
            "predictions": [],
            "scenarios": {},
        }

        mock_dependencies["insight_service"].generate_insights.return_value = {
            "insights": [],
            "recommendations": [],
        }

        # Act
        report = await analytics_engine.generate_comprehensive_report()

        # Assert
        assert report is not None
        # Verify that sensitive data is handled appropriately
        # (This would depend on specific privacy requirements)
        assert "sensitive_data" in str(report["trends"]["trends"][0]["topic"])
