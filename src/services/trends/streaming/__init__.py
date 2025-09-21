"""Trend Streaming Services

Real-time data ingestion from multiple platforms:
- Google Trends API integration
- YouTube Data API v3 trending analysis
- Twitter/X API v2 trend detection
- TikTok Research API viral content tracking
- Redis Streams event processing
"""

from .stream_manager import StreamManager

__all__ = ["StreamManager"]
