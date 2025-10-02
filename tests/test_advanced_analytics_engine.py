#!/usr/bin/env python3
"""
PAKE System - Advanced Analytics Engine Tests
Phase 13: Advanced Analytics Deep Dive - TDD Implementation

Comprehensive test suite for the Advanced Analytics Engine following TDD principles
and world-class engineering best practices.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

# Import the advanced analytics engine
from src.services.analytics.advanced_analytics_engine import (
    AdvancedAnalyticsEngine,
    AdvancedInsight,
    PredictiveReport,
    SystemHealthScore,
    get_advanced_analytics_engine,
)


class TestAdvancedAnalyticsEngine:
    """Test suite for AdvancedAnalyticsEngine following TDD principles."""

    @pytest.fixture()
    def analytics_engine(self):
        """Create a fresh analytics engine instance for each test."""
        return AdvancedAnalyticsEngine()

    @pytest.fixture()
    def mock_time_range(self):
        """Standard time range for testing."""
        return "24h"

    @pytest.fixture()
    def sample_health_data(self):
        """Sample health data for testing."""
        return {
            "overall_score": 85.5,
            "component_scores": {
                "api_health": 90.0,
                "database_health": 85.0,
                "cache_health": 95.0,
                "ml_services": 80.0,
                "ingestion_pipeline": 82.0,
            },
            "health_trends": {
                "api_health": "stable",
                "database_health": "improving",
                "cache_health": "stable",
                "ml_services": "declining",
                "ingestion_pipeline": "stable",
            },
            "critical_issues": [],
            "recommendations": ["Monitor ml_services performance"],
        }

    @pytest.fixture()
    def sample_anomaly_data(self):
        """Sample anomaly data for testing."""
        return {
            "anomalies_detected": 2,
            "anomalies": [
                {
                    "type": "performance_spike",
                    "metric": "response_time",
                    "severity": "medium",
                    "timestamp": "2025-09-14T08:00:00Z",
                    "description": "Response time increased by 40%",
                    "confidence": 0.85,
                },
                {
                    "type": "usage_drop",
                    "metric": "query_rate",
                    "severity": "high",
                    "timestamp": "2025-09-14T06:00:00Z",
                    "description": "Query rate dropped by 25%",
                    "confidence": 0.92,
                },
            ],
        }

    # Test 1: Engine Initialization
    def test_analytics_engine_initialization(self, analytics_engine):
        """Test that the analytics engine initializes correctly."""
        assert analytics_engine is not None
        assert analytics_engine.trend_service is not None
        assert analytics_engine.correlation_engine is not None
        assert analytics_engine.predictive_service is not None
        assert analytics_engine.insight_service is not None
        assert analytics_engine._insight_cache is not None
        assert analytics_engine._cache_ttl == timedelta(minutes=5)

    # Test 2: Singleton Pattern
    def test_singleton_pattern(self):
        """Test that get_advanced_analytics_engine returns singleton instance."""
        engine1 = get_advanced_analytics_engine()
        engine2 = get_advanced_analytics_engine()
        assert engine1 is engine2

    # Test 3: Comprehensive Report Generation
    @pytest.mark.asyncio()
    async def test_generate_comprehensive_report_success(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test successful comprehensive report generation."""
        with (
            patch.object(analytics_engine, "_analyze_system_health") as mock_health,
            patch.object(
                analytics_engine,
                "_analyze_performance_trends",
            ) as mock_trends,
            patch.object(analytics_engine, "_analyze_usage_patterns") as mock_usage,
            patch.object(analytics_engine, "_detect_anomalies") as mock_anomalies,
            patch.object(
                analytics_engine,
                "_generate_correlations",
            ) as mock_correlations,
            patch.object(analytics_engine, "_generate_predictions") as mock_predictions,
            patch.object(analytics_engine, "_synthesize_insights") as mock_insights,
            patch.object(
                analytics_engine,
                "_generate_recommendations",
            ) as mock_recommendations,
        ):
            # Mock return values
            mock_health.return_value = SystemHealthScore(
                overall_score=85.5,
                component_scores={"api_health": 90.0},
                health_trends={"api_health": "stable"},
                critical_issues=[],
                recommendations=[],
                timestamp=datetime.now(UTC),
            )
            mock_trends.return_value = {"performance_score": 85.0}
            mock_usage.return_value = {"usage_patterns": {}}
            mock_anomalies.return_value = {"anomalies_detected": 0}
            mock_correlations.return_value = {"correlations": []}
            mock_predictions.return_value = PredictiveReport(
                forecast_horizon="7d",
                predicted_metrics={},
                confidence_intervals={},
                risk_factors=[],
                opportunities=[],
                scenario_analysis={},
            )
            mock_insights.return_value = []
            mock_recommendations.return_value = []

            # Execute test
            report = await analytics_engine.generate_comprehensive_report(
                time_range=mock_time_range,
                include_predictions=True,
                include_recommendations=True,
            )

            # Assertions
            assert report is not None
            assert "report_id" in report
            assert "generated_at" in report
            assert report["time_range"] == mock_time_range
            assert "executive_summary" in report
            assert "system_health" in report
            assert "performance_trends" in report
            assert "usage_patterns" in report
            assert "anomalies" in report
            assert "correlations" in report
            assert "predictions" in report
            assert "key_insights" in report
            assert "recommendations" in report
            assert "metadata" in report

    # Test 4: System Health Analysis
    @pytest.mark.asyncio()
    async def test_analyze_system_health_success(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test successful system health analysis."""
        health_score = await analytics_engine._analyze_system_health(mock_time_range)

        assert isinstance(health_score, SystemHealthScore)
        assert 0 <= health_score.overall_score <= 100
        assert isinstance(health_score.component_scores, dict)
        assert isinstance(health_score.health_trends, dict)
        assert isinstance(health_score.critical_issues, list)
        assert isinstance(health_score.recommendations, list)
        assert isinstance(health_score.timestamp, datetime)

        # Verify component scores are within valid range
        for component, score in health_score.component_scores.items():
            assert 0 <= score <= 100

        # Verify health trends are valid
        valid_trends = ["improving", "declining", "stable"]
        for component, trend in health_score.health_trends.items():
            assert trend in valid_trends

    # Test 5: Performance Trends Analysis
    @pytest.mark.asyncio()
    async def test_analyze_performance_trends_success(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test successful performance trends analysis."""
        with patch.object(
            analytics_engine.trend_service,
            "analyze_trend",
        ) as mock_analyze_trend:
            mock_analyze_trend.return_value = {
                "trend_direction": "up",
                "trend_strength": 0.75,
                "confidence": 0.85,
            }

            trends = await analytics_engine._analyze_performance_trends(mock_time_range)

            assert isinstance(trends, dict)
            assert "performance_score" in trends
            assert "trend_direction" in trends
            assert "metric_trends" in trends
            assert "time_range" in trends
            assert "analysis_timestamp" in trends

            # Verify performance score is within valid range
            assert 0 <= trends["performance_score"] <= 100

    # Test 6: Usage Patterns Analysis
    @pytest.mark.asyncio()
    async def test_analyze_usage_patterns_success(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test successful usage patterns analysis."""
        patterns = await analytics_engine._analyze_usage_patterns(mock_time_range)

        assert isinstance(patterns, dict)
        assert "usage_patterns" in patterns
        assert "time_range" in patterns
        assert "analysis_timestamp" in patterns

        usage_patterns = patterns["usage_patterns"]
        assert "peak_hours" in usage_patterns
        assert "usage_distribution" in usage_patterns
        assert "user_segments" in usage_patterns
        assert "engagement_metrics" in usage_patterns

        # Verify peak hours are valid
        for hour in usage_patterns["peak_hours"]:
            assert 0 <= hour <= 23

    # Test 7: Anomaly Detection
    @pytest.mark.asyncio()
    async def test_detect_anomalies_success(self, analytics_engine, mock_time_range):
        """Test successful anomaly detection."""
        anomalies = await analytics_engine._detect_anomalies(mock_time_range)

        assert isinstance(anomalies, dict)
        assert "anomalies_detected" in anomalies
        assert "anomalies" in anomalies
        assert "detection_methods" in anomalies
        assert "time_range" in anomalies
        assert "analysis_timestamp" in anomalies

        assert isinstance(anomalies["anomalies_detected"], int)
        assert isinstance(anomalies["anomalies"], list)
        assert isinstance(anomalies["detection_methods"], list)

        # Verify anomaly structure if any exist
        for anomaly in anomalies["anomalies"]:
            assert "type" in anomaly
            assert "metric" in anomaly
            assert "severity" in anomaly
            assert "timestamp" in anomaly
            assert "description" in anomaly
            assert "confidence" in anomaly

            # Verify severity is valid
            valid_severities = ["low", "medium", "high", "critical"]
            assert anomaly["severity"] in valid_severities

            # Verify confidence is within valid range
            assert 0 <= anomaly["confidence"] <= 1

    # Test 8: Correlation Analysis
    @pytest.mark.asyncio()
    async def test_generate_correlations_success(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test successful correlation analysis."""
        with patch.object(
            analytics_engine.correlation_engine,
            "analyze_correlations",
        ) as mock_analyze:
            mock_analyze.return_value = {
                "response_time_throughput": {
                    "correlation_coefficient": -0.75,
                    "p_value": 0.001,
                    "significance": "high",
                },
            }

            correlations = await analytics_engine._generate_correlations(
                mock_time_range,
            )

            assert isinstance(correlations, dict)
            assert "correlations" in correlations
            assert "time_range" in correlations
            assert "analysis_timestamp" in correlations

    # Test 9: Predictive Analytics
    @pytest.mark.asyncio()
    async def test_generate_predictions_success(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test successful predictive analytics generation."""
        with patch.object(
            analytics_engine.predictive_service,
            "generate_forecast",
        ) as mock_forecast:
            mock_forecast.return_value = {
                "forecasts": {
                    "response_time": [100, 105, 110, 115],
                    "throughput": [1000, 950, 900, 850],
                },
                "confidence_intervals": {
                    "response_time": [(95, 105), (100, 110), (105, 115), (110, 120)],
                    "throughput": [(950, 1050), (900, 1000), (850, 950), (800, 900)],
                },
            }

            predictions = await analytics_engine._generate_predictions(mock_time_range)

            assert isinstance(predictions, PredictiveReport)
            assert predictions.forecast_horizon == "7d"
            assert isinstance(predictions.predicted_metrics, dict)
            assert isinstance(predictions.confidence_intervals, dict)
            assert isinstance(predictions.risk_factors, list)
            assert isinstance(predictions.opportunities, list)
            assert isinstance(predictions.scenario_analysis, dict)

    # Test 10: Insight Synthesis
    @pytest.mark.asyncio()
    async def test_synthesize_insights_success(
        self,
        analytics_engine,
        sample_health_data,
        sample_anomaly_data,
    ):
        """Test successful insight synthesis."""
        health_analysis = SystemHealthScore(
            overall_score=sample_health_data["overall_score"],
            component_scores=sample_health_data["component_scores"],
            health_trends=sample_health_data["health_trends"],
            critical_issues=sample_health_data["critical_issues"],
            recommendations=sample_health_data["recommendations"],
            timestamp=datetime.now(UTC),
        )

        trend_analysis = {"performance_score": 85.0}
        usage_analysis = {
            "usage_patterns": {"engagement_metrics": {"daily_active_users": 120}},
        }
        anomaly_analysis = sample_anomaly_data
        correlation_analysis = {"correlations": []}
        predictions = PredictiveReport(
            forecast_horizon="7d",
            predicted_metrics={},
            confidence_intervals={},
            risk_factors=[],
            opportunities=[],
            scenario_analysis={},
        )

        insights = await analytics_engine._synthesize_insights(
            health_analysis,
            trend_analysis,
            usage_analysis,
            anomaly_analysis,
            correlation_analysis,
            predictions,
        )

        assert isinstance(insights, list)

        # Verify insight structure
        for insight in insights:
            assert isinstance(insight, AdvancedInsight)
            assert isinstance(insight.insight_id, str)
            assert isinstance(insight.title, str)
            assert isinstance(insight.description, str)
            assert isinstance(insight.category, str)
            assert 0 <= insight.confidence <= 1
            assert insight.priority in ["critical", "high", "medium", "low"]
            assert insight.severity in ["urgent", "warning", "info", "success"]
            assert isinstance(insight.timestamp, datetime)
            assert isinstance(insight.data_sources, list)
            assert isinstance(insight.metrics_involved, list)
            assert isinstance(insight.supporting_evidence, dict)
            assert isinstance(insight.recommended_actions, list)

    # Test 11: Recommendation Generation
    @pytest.mark.asyncio()
    async def test_generate_recommendations_success(self, analytics_engine):
        """Test successful recommendation generation."""
        # Create sample insights
        insights = [
            AdvancedInsight(
                insight_id="test_1",
                title="Critical Issue",
                description="A critical issue has been detected",
                category="performance",
                confidence=0.95,
                priority="critical",
                severity="urgent",
                timestamp=datetime.now(UTC),
                data_sources=["system_monitoring"],
                metrics_involved=["response_time"],
                supporting_evidence={"score": 0.95},
                recommended_actions=["Investigate immediately", "Scale resources"],
            ),
            AdvancedInsight(
                insight_id="test_2",
                title="High Priority Issue",
                description="A high priority issue has been detected",
                category="usage",
                confidence=0.85,
                priority="high",
                severity="warning",
                timestamp=datetime.now(UTC),
                data_sources=["usage_analytics"],
                metrics_involved=["query_rate"],
                supporting_evidence={"score": 0.85},
                recommended_actions=["Monitor closely", "Optimize performance"],
            ),
        ]

        recommendations = await analytics_engine._generate_recommendations(insights)

        assert isinstance(recommendations, list)

        # Verify recommendation structure
        for recommendation in recommendations:
            assert isinstance(recommendation, dict)
            assert "category" in recommendation
            assert "priority" in recommendation
            assert "title" in recommendation
            assert "description" in recommendation
            assert "actions" in recommendation
            assert "timeline" in recommendation
            assert "impact" in recommendation
            assert "effort" in recommendation

            # Verify priority is valid
            valid_priorities = ["critical", "high", "medium", "low"]
            assert recommendation["priority"] in valid_priorities

            # Verify timeline is valid
            valid_timelines = ["immediate", "daily", "weekly", "monthly"]
            assert recommendation["timeline"] in valid_timelines

            # Verify impact is valid
            valid_impacts = ["high", "medium", "low"]
            assert recommendation["impact"] in valid_impacts

            # Verify effort is valid
            valid_efforts = ["high", "medium", "low"]
            assert recommendation["effort"] in valid_efforts

    # Test 12: Executive Summary Creation
    def test_create_executive_summary_success(self, analytics_engine):
        """Test successful executive summary creation."""
        insights = [
            AdvancedInsight(
                insight_id="test_1",
                title="Critical Issue",
                description="A critical issue",
                category="performance",
                confidence=0.95,
                priority="critical",
                severity="urgent",
                timestamp=datetime.now(UTC),
                data_sources=[],
                metrics_involved=[],
                supporting_evidence={},
                recommended_actions=[],
            ),
            AdvancedInsight(
                insight_id="test_2",
                title="High Priority Issue",
                description="A high priority issue",
                category="usage",
                confidence=0.85,
                priority="high",
                severity="warning",
                timestamp=datetime.now(UTC),
                data_sources=[],
                metrics_involved=[],
                supporting_evidence={},
                recommended_actions=[],
            ),
        ]

        summary = analytics_engine._create_executive_summary(insights)

        assert isinstance(summary, dict)
        assert "overall_status" in summary
        assert "key_findings" in summary
        assert "critical_count" in summary
        assert "high_priority_count" in summary
        assert "total_insights" in summary
        assert "recommendations_count" in summary

        # Verify overall status is valid
        valid_statuses = ["healthy", "attention_needed", "critical"]
        assert summary["overall_status"] in valid_statuses

        # Verify counts are correct
        assert summary["critical_count"] == 1
        assert summary["high_priority_count"] == 1
        assert summary["total_insights"] == 2

    # Test 13: Report Confidence Calculation
    def test_calculate_report_confidence_success(self, analytics_engine):
        """Test successful report confidence calculation."""
        insights = [
            AdvancedInsight(
                insight_id="test_1",
                title="Test Insight 1",
                description="Test description",
                category="performance",
                confidence=0.9,
                priority="high",
                severity="warning",
                timestamp=datetime.now(UTC),
                data_sources=[],
                metrics_involved=[],
                supporting_evidence={},
                recommended_actions=[],
            ),
            AdvancedInsight(
                insight_id="test_2",
                title="Test Insight 2",
                description="Test description",
                category="usage",
                confidence=0.8,
                priority="medium",
                severity="info",
                timestamp=datetime.now(UTC),
                data_sources=[],
                metrics_involved=[],
                supporting_evidence={},
                recommended_actions=[],
            ),
        ]

        confidence = analytics_engine._calculate_report_confidence(insights)

        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
        assert confidence == 0.85  # Average of 0.9 and 0.8

    # Test 14: Empty Insights Handling
    def test_create_executive_summary_empty_insights(self, analytics_engine):
        """Test executive summary creation with empty insights."""
        summary = analytics_engine._create_executive_summary([])

        assert isinstance(summary, dict)
        assert summary["overall_status"] == "healthy"
        assert summary["key_findings"] == []
        assert summary["critical_count"] == 0
        assert summary["recommendations_count"] == 0

    # Test 15: Error Handling
    @pytest.mark.asyncio()
    async def test_generate_comprehensive_report_error_handling(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test error handling in comprehensive report generation."""
        with patch.object(analytics_engine, "_analyze_system_health") as mock_health:
            mock_health.side_effect = Exception("Test error")

            report = await analytics_engine.generate_comprehensive_report(
                mock_time_range,
            )

            assert isinstance(report, dict)
            assert "error" in report
            assert "timestamp" in report
            assert report["error"] == "Test error"

    # Test 16: Cache Functionality
    def test_insight_cache_functionality(self, analytics_engine):
        """Test insight cache functionality."""
        # Test cache initialization
        assert analytics_engine._insight_cache == {}
        assert analytics_engine._cache_ttl == timedelta(minutes=5)

        # Test cache key generation
        cache_key = f"test_key_{datetime.now().timestamp()}"
        analytics_engine._insight_cache[cache_key] = {"test": "data"}

        assert cache_key in analytics_engine._insight_cache
        assert analytics_engine._insight_cache[cache_key] == {"test": "data"}

    # Test 17: Data Validation
    @pytest.mark.asyncio()
    async def test_data_validation_in_insights(self, analytics_engine):
        """Test data validation in insight generation."""
        # Test with invalid confidence score
        with pytest.raises(ValueError):
            AdvancedInsight(
                insight_id="test",
                title="Test",
                description="Test",
                category="test",
                confidence=1.5,  # Invalid: > 1
                priority="high",
                severity="warning",
                timestamp=datetime.now(UTC),
                data_sources=[],
                metrics_involved=[],
                supporting_evidence={},
                recommended_actions=[],
            )

    # Test 18: Performance Metrics
    @pytest.mark.asyncio()
    async def test_performance_metrics(self, analytics_engine, mock_time_range):
        """Test performance metrics in analytics generation."""
        import time

        start_time = time.time()
        report = await analytics_engine.generate_comprehensive_report(mock_time_range)
        end_time = time.time()

        processing_time = end_time - start_time

        # Verify report was generated within reasonable time
        assert processing_time < 5.0  # Should complete within 5 seconds

        # Verify report contains performance metadata
        assert "metadata" in report
        assert "total_insights" in report["metadata"]
        assert "confidence_score" in report["metadata"]

    # Test 19: Concurrent Execution
    @pytest.mark.asyncio()
    async def test_concurrent_report_generation(
        self,
        analytics_engine,
        mock_time_range,
    ):
        """Test concurrent report generation."""
        # Generate multiple reports concurrently
        tasks = [
            analytics_engine.generate_comprehensive_report(mock_time_range)
            for _ in range(3)
        ]

        reports = await asyncio.gather(*tasks)

        # Verify all reports were generated
        assert len(reports) == 3
        for report in reports:
            assert isinstance(report, dict)
            assert "report_id" in report
            assert "generated_at" in report

    # Test 20: Integration Test
    @pytest.mark.asyncio()
    async def test_full_integration(self, analytics_engine):
        """Test full integration of all analytics components."""
        # Test with different time ranges
        time_ranges = ["1h", "6h", "24h", "7d"]

        for time_range in time_ranges:
            report = await analytics_engine.generate_comprehensive_report(
                time_range=time_range,
                include_predictions=True,
                include_recommendations=True,
            )

            # Verify report structure
            assert isinstance(report, dict)
            assert report["time_range"] == time_range
            assert "executive_summary" in report
            assert "system_health" in report
            assert "performance_trends" in report
            assert "usage_patterns" in report
            assert "anomalies" in report
            assert "correlations" in report
            assert "predictions" in report
            assert "key_insights" in report
            assert "recommendations" in report


class TestAdvancedInsight:
    """Test suite for AdvancedInsight data class."""

    def test_advanced_insight_creation(self):
        """Test AdvancedInsight creation with valid data."""
        insight = AdvancedInsight(
            insight_id="test_123",
            title="Test Insight",
            description="This is a test insight",
            category="performance",
            confidence=0.85,
            priority="high",
            severity="warning",
            timestamp=datetime.now(UTC),
            data_sources=["system_monitoring"],
            metrics_involved=["response_time"],
            supporting_evidence={"score": 0.85},
            recommended_actions=["Monitor closely"],
            predicted_impact="Medium impact expected",
            time_sensitivity="daily",
        )

        assert insight.insight_id == "test_123"
        assert insight.title == "Test Insight"
        assert insight.description == "This is a test insight"
        assert insight.category == "performance"
        assert insight.confidence == 0.85
        assert insight.priority == "high"
        assert insight.severity == "warning"
        assert isinstance(insight.timestamp, datetime)
        assert insight.data_sources == ["system_monitoring"]
        assert insight.metrics_involved == ["response_time"]
        assert insight.supporting_evidence == {"score": 0.85}
        assert insight.recommended_actions == ["Monitor closely"]
        assert insight.predicted_impact == "Medium impact expected"
        assert insight.time_sensitivity == "daily"

    def test_advanced_insight_default_values(self):
        """Test AdvancedInsight creation with default values."""
        insight = AdvancedInsight(
            insight_id="test_456",
            title="Test Insight",
            description="This is a test insight",
            category="usage",
            confidence=0.75,
            priority="medium",
            severity="info",
            timestamp=datetime.now(UTC),
        )

        assert insight.data_sources == []
        assert insight.metrics_involved == []
        assert insight.supporting_evidence == {}
        assert insight.recommended_actions == []
        assert insight.predicted_impact is None
        assert insight.time_sensitivity is None


class TestSystemHealthScore:
    """Test suite for SystemHealthScore data class."""

    def test_system_health_score_creation(self):
        """Test SystemHealthScore creation with valid data."""
        health_score = SystemHealthScore(
            overall_score=85.5,
            component_scores={
                "api_health": 90.0,
                "database_health": 85.0,
                "cache_health": 95.0,
            },
            health_trends={
                "api_health": "stable",
                "database_health": "improving",
                "cache_health": "stable",
            },
            critical_issues=["Low database performance"],
            recommendations=["Monitor database closely"],
            timestamp=datetime.now(UTC),
        )

        assert health_score.overall_score == 85.5
        assert health_score.component_scores["api_health"] == 90.0
        assert health_score.health_trends["api_health"] == "stable"
        assert health_score.critical_issues == ["Low database performance"]
        assert health_score.recommendations == ["Monitor database closely"]
        assert isinstance(health_score.timestamp, datetime)


class TestPredictiveReport:
    """Test suite for PredictiveReport data class."""

    def test_predictive_report_creation(self):
        """Test PredictiveReport creation with valid data."""
        report = PredictiveReport(
            forecast_horizon="7d",
            predicted_metrics={
                "response_time": [100, 105, 110],
                "throughput": [1000, 950, 900],
            },
            confidence_intervals={
                "response_time": [(95, 105), (100, 110), (105, 115)],
                "throughput": [(950, 1050), (900, 1000), (850, 950)],
            },
            risk_factors=["Increased load", "Seasonal patterns"],
            opportunities=["Cache optimization", "Auto-scaling"],
            scenario_analysis={
                "best_case": {"performance_improvement": "15%"},
                "worst_case": {"performance_degradation": "8%"},
            },
        )

        assert report.forecast_horizon == "7d"
        assert len(report.predicted_metrics["response_time"]) == 3
        assert len(report.confidence_intervals["response_time"]) == 3
        assert len(report.risk_factors) == 2
        assert len(report.opportunities) == 2
        assert "best_case" in report.scenario_analysis
        assert "worst_case" in report.scenario_analysis


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
