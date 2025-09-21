"""Advanced Analytics Services Package

Provides predictive analytics, trend analysis, correlation analysis,
and AI-powered insights for the PAKE System.
"""

from .correlation_engine import CorrelationEngine, get_correlation_engine
from .insight_generation_service import (
    InsightGenerationService,
    get_insight_generation_service,
)
from .predictive_analytics_service import (
    PredictiveAnalyticsService,
    get_predictive_analytics_service,
)
from .trend_analysis_service import TrendAnalysisService, get_trend_analysis_service

__all__ = [
    "PredictiveAnalyticsService",
    "get_predictive_analytics_service",
    "CorrelationEngine",
    "get_correlation_engine",
    "TrendAnalysisService",
    "get_trend_analysis_service",
    "InsightGenerationService",
    "get_insight_generation_service",
]
