"""PAKE System - Machine Learning Services
Phase 9B: Practical AI/ML Integration

This module provides lightweight ML functionality focused on semantic search,
content analysis, and practical knowledge management enhancements.
"""

from .analytics_aggregation_service import (
    MLAnalyticsAggregationService,
    get_ml_analytics_service,
)
from .content_summarization_service import (
    ContentSummarizationService,
    get_content_summarization_service,
)
from .feature_engineering import FeatureEngineer, FeatureEngineeringConfig
from .ml_monitoring import MetricType, MLMonitor

# Heavy ML infrastructure - available for testing
from .model_serving import ModelServingConfig, ModelServingService
from .prediction_service import (
    BatchPredictionRequest,
    EnsembleMethod,
    PredictionRequest,
    PredictionService,
)
from .semantic_search_service import SemanticSearchService, get_semantic_search_service
from .training_pipeline import ModelType, TrainingJob, TrainingOrchestrator

__all__ = [
    "SemanticSearchService",
    "get_semantic_search_service",
    "ContentSummarizationService",
    "get_content_summarization_service",
    "MLAnalyticsAggregationService",
    "get_ml_analytics_service",
    # Heavy infrastructure exports:
    "ModelServingService",
    "ModelServingConfig",
    "TrainingOrchestrator",
    "ModelType",
    "TrainingJob",
    "FeatureEngineer",
    "FeatureEngineeringConfig",
    "PredictionService",
    "PredictionRequest",
    "BatchPredictionRequest",
    "EnsembleMethod",
    "MLMonitor",
    "MetricType",
]
