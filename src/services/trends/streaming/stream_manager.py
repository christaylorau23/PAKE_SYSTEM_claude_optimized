"""StreamManager - Central coordinator for all trend streaming services

Manages multiple platform streams with Redis Streams integration and performance monitoring.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from ..apis.api_health_monitor import APIHealthMonitor
from ..apis.rate_limit_controller import RateLimitController
from ..models.trend_signal import Platform, TrendSignal


@dataclass
class StreamConfig:
    """Configuration for individual stream"""

    platform: Platform
    enabled: bool = True
    poll_interval_seconds: int = 60
    max_keywords: int = 100
    priority: int = 1  # 1=highest, 5=lowest
    rate_limit_per_hour: int = 1000


@dataclass
class StreamStatus:
    """Status information for a stream"""

    platform: Platform
    is_running: bool
    last_update: datetime | None
    trends_processed: int
    errors_count: int
    average_latency_ms: float
    health_score: float  # 0.0 to 1.0


class StreamManager:
    """Central manager for all trend streaming services

    Capabilities:
    - Manages multiple platform streams
    - Redis Streams integration for real-time processing
    - Rate limiting and health monitoring
    - Performance metrics and alerting
    - Graceful error handling and recovery
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.logger = logging.getLogger(__name__)

        # Stream management
        self.active_streams: dict[Platform, asyncio.Task] = {}
        self.stream_configs: dict[Platform, StreamConfig] = {}
        self.stream_status: dict[Platform, StreamStatus] = {}

        # Performance tracking
        self.max_throughput = 10.0  # trends per second (for contract testing)
        self.trends_processed_total = 0
        self.start_time = datetime.now()

        # Components
        self.rate_controller = RateLimitController()
        self.health_monitor = APIHealthMonitor()

        # Redis stream names
        self.trend_stream_name = "trends:stream"
        self.consumer_group = "trend_processors"

        self._initialize_default_configs()

    def _initialize_default_configs(self):
        """Initialize default configurations for all platforms"""
        self.stream_configs = {
            Platform.GOOGLE_TRENDS: StreamConfig(
                platform=Platform.GOOGLE_TRENDS,
                poll_interval_seconds=300,  # 5 minutes
                max_keywords=50,
                priority=1,
                rate_limit_per_hour=500,
            ),
            Platform.YOUTUBE: StreamConfig(
                platform=Platform.YOUTUBE,
                poll_interval_seconds=600,  # 10 minutes
                max_keywords=100,
                priority=2,
                rate_limit_per_hour=1000,
            ),
            Platform.TWITTER: StreamConfig(
                platform=Platform.TWITTER,
                poll_interval_seconds=60,  # 1 minute
                max_keywords=200,
                priority=1,
                rate_limit_per_hour=2000,
            ),
            Platform.TIKTOK: StreamConfig(
                platform=Platform.TIKTOK,
                poll_interval_seconds=600,  # 10 minutes
                max_keywords=75,
                priority=2,
                rate_limit_per_hour=800,
            ),
        }

    async def initialize(self) -> bool:
        """Initialize Redis connection and stream infrastructure"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()

            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create(
                    self.trend_stream_name,
                    self.consumer_group,
                    id="0",
                    mkstream=True,
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

            self.logger.info("StreamManager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize StreamManager: {e}")
            return False

    async def start_stream(
        self,
        platform: Platform,
        keywords: list[str] = None,
    ) -> bool:
        """Start streaming for a specific platform"""
        if platform in self.active_streams:
            self.logger.warning(f"Stream for {platform.value} already running")
            return False

        config = self.stream_configs.get(platform)
        if not config or not config.enabled:
            self.logger.warning(f"Stream for {platform.value} is disabled")
            return False

        try:
            # Create stream task
            task = asyncio.create_task(
                self._run_platform_stream(platform, keywords or []),
            )
            self.active_streams[platform] = task

            # Initialize status
            self.stream_status[platform] = StreamStatus(
                platform=platform,
                is_running=True,
                last_update=None,
                trends_processed=0,
                errors_count=0,
                average_latency_ms=0.0,
                health_score=1.0,
            )

            self.logger.info(f"Started stream for {platform.value}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start stream for {platform.value}: {e}")
            return False

    async def stop_stream(self, platform: Platform) -> bool:
        """Stop streaming for a specific platform"""
        if platform not in self.active_streams:
            self.logger.warning(f"No active stream for {platform.value}")
            return False

        try:
            task = self.active_streams[platform]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self.active_streams[platform]

            # Update status
            if platform in self.stream_status:
                status = self.stream_status[platform]
                self.stream_status[platform] = StreamStatus(
                    platform=status.platform,
                    is_running=False,
                    last_update=status.last_update,
                    trends_processed=status.trends_processed,
                    errors_count=status.errors_count,
                    average_latency_ms=status.average_latency_ms,
                    health_score=status.health_score,
                )

            self.logger.info(f"Stopped stream for {platform.value}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop stream for {platform.value}: {e}")
            return False

    async def start_all_streams(
        self,
        keywords: list[str] = None,
    ) -> dict[Platform, bool]:
        """Start all enabled streams"""
        results = {}
        for platform in Platform:
            if self.stream_configs[platform].enabled:
                results[platform] = await self.start_stream(platform, keywords)
        return results

    async def stop_all_streams(self) -> dict[Platform, bool]:
        """Stop all active streams"""
        results = {}
        for platform in list(self.active_streams.keys()):
            results[platform] = await self.stop_stream(platform)
        return results

    async def get_status(self, platform: Platform = None) -> dict[str, Any]:
        """Get status for specific platform or all platforms"""
        if platform:
            status = self.stream_status.get(platform)
            return status.__dict__ if status else {"error": "Platform not found"}

        return {
            "active_streams": len(self.active_streams),
            "total_trends_processed": self.trends_processed_total,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "average_throughput": self._calculate_average_throughput(),
            "platforms": {
                platform.value: status.__dict__
                for platform, status in self.stream_status.items()
            },
        }

    def _calculate_average_throughput(self) -> float:
        """Calculate average trends per second"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return self.trends_processed_total / uptime if uptime > 0 else 0.0

    async def _run_platform_stream(self, platform: Platform, keywords: list[str]):
        """Run the streaming loop for a specific platform"""
        config = self.stream_configs[platform]

        while True:
            try:
                start_time = datetime.now()

                # Check rate limits
                if not await self.rate_controller.can_make_request(platform.value):
                    await asyncio.sleep(60)  # Wait before retrying
                    continue

                # Get trends from platform (placeholder - would integrate with actual
                # APIs)
                trends = await self._fetch_platform_trends(platform, keywords)

                # Process and publish trends
                for trend in trends:
                    await self._publish_trend(trend)
                    self.trends_processed_total += 1

                    # Update status
                    if platform in self.stream_status:
                        status = self.stream_status[platform]
                        self.stream_status[platform] = StreamStatus(
                            platform=status.platform,
                            is_running=True,
                            last_update=datetime.now(),
                            trends_processed=status.trends_processed + 1,
                            errors_count=status.errors_count,
                            average_latency_ms=status.average_latency_ms,
                            health_score=status.health_score,
                        )

                # Calculate latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                await self._update_latency_metrics(platform, latency_ms)

                # Wait for next poll
                await asyncio.sleep(config.poll_interval_seconds)

            except Exception as e:
                self.logger.error(f"Error in {platform.value} stream: {e}")
                await self._handle_stream_error(platform, e)
                await asyncio.sleep(60)  # Error backoff

    async def _fetch_platform_trends(
        self,
        platform: Platform,
        keywords: list[str],
    ) -> list[TrendSignal]:
        """Fetch trends from platform API (placeholder implementation)"""
        # This is a placeholder - real implementation would use actual API clients
        from ..models.trend_signal import TrendLifecycle

        trends = []
        for i, keyword in enumerate(keywords[:5]):  # Limit for demo
            trend = TrendSignal(
                platform=platform,
                keyword=f"{keyword}_trend_{i}",
                momentum=0.7 + (i * 0.05),
                timestamp=datetime.now(),
                confidence=0.8 + (i * 0.02),
                volume=1000 + (i * 500),
                lifecycle_stage=TrendLifecycle.EMERGING,
                geographic_scope=["US", "CA", "GB"],
                related_keywords=[f"related_{keyword}_{i}"],
            )
            trends.append(trend)

        return trends

    async def _publish_trend(self, trend: TrendSignal):
        """Publish trend to Redis stream"""
        if not self.redis_client:
            return

        try:
            trend_data = {
                "trend_json": trend.to_json(),
                "platform": trend.platform.value,
                "keyword": trend.keyword,
                "timestamp": trend.timestamp.isoformat(),
                "momentum": trend.momentum,
            }

            await self.redis_client.xadd(self.trend_stream_name, trend_data)

        except Exception as e:
            self.logger.error(f"Failed to publish trend: {e}")

    async def _update_latency_metrics(self, platform: Platform, latency_ms: float):
        """Update latency metrics for platform"""
        if platform in self.stream_status:
            status = self.stream_status[platform]
            # Simple moving average
            new_avg = (status.average_latency_ms + latency_ms) / 2

            self.stream_status[platform] = StreamStatus(
                platform=status.platform,
                is_running=status.is_running,
                last_update=status.last_update,
                trends_processed=status.trends_processed,
                errors_count=status.errors_count,
                average_latency_ms=new_avg,
                health_score=status.health_score,
            )

    async def _handle_stream_error(self, platform: Platform, error: Exception):
        """Handle stream errors and update health metrics"""
        if platform in self.stream_status:
            status = self.stream_status[platform]
            new_health = max(0.1, status.health_score - 0.1)  # Decrease health

            self.stream_status[platform] = StreamStatus(
                platform=status.platform,
                is_running=status.is_running,
                last_update=status.last_update,
                trends_processed=status.trends_processed,
                errors_count=status.errors_count + 1,
                average_latency_ms=status.average_latency_ms,
                health_score=new_health,
            )

    async def get_consumer_stream(
        self,
        consumer_name: str = "default",
    ) -> AsyncGenerator[TrendSignal, None]:
        """Get async generator for consuming trends from Redis stream"""
        if not self.redis_client:
            return

        while True:
            try:
                # Read from stream
                streams = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    consumer_name,
                    {self.trend_stream_name: ">"},
                    count=10,
                    block=1000,
                )

                for stream_name, messages in streams:
                    for message_id, fields in messages:
                        try:
                            trend_json = fields.get(b"trend_json", b"{}").decode()
                            trend = TrendSignal.from_json(trend_json)
                            yield trend

                            # Acknowledge message
                            await self.redis_client.xack(
                                self.trend_stream_name,
                                self.consumer_group,
                                message_id,
                            )

                        except Exception as e:
                            self.logger.error(
                                f"Failed to process message {message_id}: {e}",
                            )

            except Exception as e:
                self.logger.error(f"Error reading from stream: {e}")
                await asyncio.sleep(5)

    async def shutdown(self):
        """Gracefully shutdown all streams and cleanup"""
        self.logger.info("Shutting down StreamManager...")

        # Stop all streams
        await self.stop_all_streams()

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()

        self.logger.info("StreamManager shutdown complete")
