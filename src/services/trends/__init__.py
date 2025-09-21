"""Live Trend Data Feed System

This module provides real-time trend intelligence from multiple platforms
for investment analysis and opportunity detection.

Components:
- streaming: Platform-specific data ingestion services
- aggregation: Time-based and geographic trend aggregation
- intelligence: Trend analysis and prediction services
- apis: External API management and rate limiting
- models: Core data models and validation
"""

__version__ = "1.0.0"
__author__ = "PAKE System"

from .models import (
    GeographicTrendData,
    InvestmentOpportunity,
    TrendCorrelation,
    TrendSignal,
)

__all__ = [
    "TrendSignal",
    "TrendCorrelation",
    "InvestmentOpportunity",
    "GeographicTrendData",
]
