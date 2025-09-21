"""Trend Aggregation Services

Time-based and geographic trend analysis:
- Time-series aggregation (hourly, daily, weekly)
- Geographic trend distribution analysis
- Cross-platform correlation engine
- Statistical validation and confidence scoring
"""

from .correlation_engine import CorrelationEngine
from .geographic_aggregator import GeographicAggregator
from .time_based_aggregator import TimeBasedAggregator

__all__ = ["TimeBasedAggregator", "GeographicAggregator", "CorrelationEngine"]
