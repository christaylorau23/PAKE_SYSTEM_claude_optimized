#!/usr/bin/env python3
"""PAKE System - High-Performance Data Ingestion Pipeline
Real-time multi-source data ingestion optimized for personal wealth generation.

Features:
- Real-time market data streaming (stocks, crypto, forex, commodities)
- News and social sentiment data ingestion
- Patent and research paper monitoring
- High-throughput parallel processing
- Intelligent data prioritization and filtering
- Sub-second latency for critical signals
"""

import asyncio
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib
import logging
import time
from typing import Any, Dict, List

import aiohttp
import json
import numpy as np
import orjson  # Fast JSON parsing

# High-performance async libraries
import uvloop  # Ultra-fast event loop
import websockets

# Redis for high-speed caching and pub/sub
try:
    import redis.asyncio as redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    MARKET_DATA = "market_data"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    PATENTS = "patents"
    RESEARCH = "research"
    ECONOMIC_INDICATORS = "economic_indicators"
    INSIDER_TRADING = "insider_trading"
    OPTIONS_FLOW = "options_flow"


class DataPriority(Enum):
    CRITICAL = 0  # Sub-100ms processing required
    HIGH = 1  # Sub-500ms processing required
    MEDIUM = 2  # Sub-2s processing required
    LOW = 3  # Can wait up to 30s


@dataclass
class DataPoint:
    """Individual data point with metadata."""

    source: str
    data_type: DataSourceType
    symbol: str | None
    timestamp: datetime
    data: Dict[str, Any]
    priority: DataPriority = DataPriority.MEDIUM
    hash_key: str | None = None

    def __post_init__(self) -> None:
        if not self.hash_key:
            # Generate unique hash for deduplication
            content = f"{self.source}_{self.symbol}_{self.timestamp.isoformat()}_{
                hash(str(self.data))
            }"
            self.hash_key = hashlib.sha256(content.encode()).hexdigest()


@dataclass
class DataStream:
    """Configuration for a data stream."""

    source_name: str
    data_type: DataSourceType
    endpoint_url: str
    symbols: List[str]
    update_frequency: float  # seconds
    priority: DataPriority
    parser_func: Callable
    is_websocket: bool = False
    api_key: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    active: bool = True


class DataIngestionPipeline:
    """High-performance data ingestion pipeline for wealth generation."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

        # Performance optimization
        self.use_uvloop = config.get("use_uvloop", True)
        if self.use_uvloop:
            try:
                uvloop.install()
                logger.info("🚀 UV Loop installed for maximum performance")
            except (ValueError, RuntimeError) as e:
                logger.warning("Could not install uvloop: %s", e)

        # Redis connection for high-speed caching and pub/sub
        self.redis_client = None
        if HAS_REDIS and config.get("redis_url"):
            self.redis_client = redis.from_url(config["redis_url"])

        # Data streams configuration
        self.data_streams: dict[str, DataStream] = {}
        self.active_connections: Dict[str, Any] = {}

        # High-performance data queues (priority-based)
        self.data_queues: dict[DataPriority, asyncio.Queue] = {
            DataPriority.CRITICAL: asyncio.Queue(maxsize=1000),
            DataPriority.HIGH: asyncio.Queue(maxsize=5000),
            DataPriority.MEDIUM: asyncio.Queue(maxsize=10000),
            DataPriority.LOW: asyncio.Queue(maxsize=20000),
        }

        # Deduplication cache (in-memory for speed)
        self.dedup_cache: dict[str, float] = {}  # hash_key -> timestamp
        self.dedup_cache_size = config.get("dedup_cache_size", 100000)

        # Performance metrics
        self.metrics = {
            "data_points_processed": 0,
            "data_points_deduplicated": 0,
            "processing_latency": deque(maxlen=1000),
            "queue_sizes": defaultdict(list),
            "errors": defaultdict(int),
        }

        # Data subscribers (components that want to receive data)
        self.subscribers: dict[DataSourceType, list[Callable]] = defaultdict(list)

        # Initialize data streams
        self._initialize_data_streams()

        logger.info(
            "DataIngestionPipeline initialized with %s streams",
            len(self.data_streams),
        )

    def _initialize_data_streams(self) -> None:
        """Initialize all data streams based on configuration."""
        # Stock market data streams
        if self.config.get("stock_symbols"):
            # Alpha Vantage real-time quotes
            self.add_data_stream(
                DataStream(
                    source_name="alpha_vantage_quotes",
                    data_type=DataSourceType.MARKET_DATA,
                    endpoint_url="https://www.alphavantage.co/query",
                    symbols=self.config["stock_symbols"],
                    update_frequency=5.0,  # Every 5 seconds
                    priority=DataPriority.HIGH,
                    parser_func=self._parse_alpha_vantage_quote,
                    api_key=self.config.get("alpha_vantage_api_key"),
                ),
            )

            # Yahoo Finance WebSocket (if available)
            if self.config.get("enable_yahoo_websocket", False):
                self.add_data_stream(
                    DataStream(
                        source_name="yahoo_websocket",
                        data_type=DataSourceType.MARKET_DATA,
                        endpoint_url="wss://streamer.finance.yahoo.com/",
                        symbols=self.config["stock_symbols"],
                        update_frequency=0.1,  # Real-time
                        priority=DataPriority.CRITICAL,
                        parser_func=self._parse_yahoo_websocket,
                        is_websocket=True,
                    ),
                )

        # Cryptocurrency data streams
        if self.config.get("crypto_symbols"):
            # Coinbase Pro WebSocket
            self.add_data_stream(
                DataStream(
                    source_name="coinbase_websocket",
                    data_type=DataSourceType.MARKET_DATA,
                    endpoint_url="wss://ws-feed.pro.coinbase.com",
                    symbols=[
                        f"{symbol}-USD" for symbol in self.config["crypto_symbols"]
                    ],
                    update_frequency=0.1,  # Real-time
                    priority=DataPriority.CRITICAL,
                    parser_func=self._parse_coinbase_websocket,
                    is_websocket=True,
                ),
            )

            # CoinGecko API for additional crypto data
            self.add_data_stream(
                DataStream(
                    source_name="coingecko_api",
                    data_type=DataSourceType.MARKET_DATA,
                    endpoint_url="https://api.coingecko.com/api/v3/simple/price",
                    symbols=self.config["crypto_symbols"],
                    update_frequency=10.0,  # Every 10 seconds
                    priority=DataPriority.HIGH,
                    parser_func=self._parse_coingecko_price,
                ),
            )

        # News data streams
        if self.config.get("enable_news_feeds", True):
            # NewsAPI
            if self.config.get("newsapi_key"):
                self.add_data_stream(
                    DataStream(
                        source_name="newsapi",
                        data_type=DataSourceType.NEWS,
                        endpoint_url="https://newsapi.org/v2/everything",
                        symbols=self.config.get(
                            "news_keywords",
                            ["stocks", "crypto", "AI", "technology"],
                        ),
                        update_frequency=60.0,  # Every minute
                        priority=DataPriority.MEDIUM,
                        parser_func=self._parse_news_api,
                        api_key=self.config.get("newsapi_key"),
                    ),
                )

        # Social media sentiment streams
        if self.config.get("enable_social_feeds", True):
            # Reddit API (if available)
            if self.config.get("reddit_client_id"):
                self.add_data_stream(
                    DataStream(
                        source_name="reddit_api",
                        data_type=DataSourceType.SOCIAL_MEDIA,
                        endpoint_url="https://oauth.reddit.com/r/all/new",
                        symbols=self.config.get(
                            "social_keywords",
                            ["stocks", "investing", "crypto"],
                        ),
                        update_frequency=30.0,  # Every 30 seconds
                        priority=DataPriority.LOW,
                        parser_func=self._parse_reddit_posts,
                    ),
                )

        # Economic indicators
        if self.config.get("enable_economic_data", True):
            # FRED Economic Data
            self.add_data_stream(
                DataStream(
                    source_name="fred_api",
                    data_type=DataSourceType.ECONOMIC_INDICATORS,
                    endpoint_url="https://api.stlouisfed.org/fred/series/observations",
                    symbols=["GDP", "UNRATE", "CPIAUCSL", "FEDFUNDS"],
                    # Key economic indicators
                    update_frequency=3600.0,  # Every hour
                    priority=DataPriority.LOW,
                    parser_func=self._parse_fred_data,
                    api_key=self.config.get("fred_api_key"),
                ),
            )

    def add_data_stream(self, stream: DataStream) -> None:
        """Add a new data stream to the pipeline."""
        self.data_streams[stream.source_name] = stream
        logger.info(
            "Added data stream: %s (%s)",
            stream.source_name,
            stream.data_type.value,
        )

    async def start(self) -> None:
        """Start the data ingestion pipeline."""
        logger.info("🚀 Starting high-performance data ingestion pipeline...")

        # Start Redis connection if available
        if self.redis_client:
            try:
                await self.redis_client.ping()
                logger.info("✅ Redis connection established")
            except (ValueError, RuntimeError) as e:
                logger.warning("Redis connection failed: %s", e)
                self.redis_client = None

        # Start all data processors
        tasks = []

        # Start data stream tasks
        for stream_name, stream in self.data_streams.items():
            if stream.active:
                if stream.is_websocket:
                    task = asyncio.create_task(self._websocket_stream_handler(stream))
                else:
                    task = asyncio.create_task(self._http_stream_handler(stream))
                tasks.append(task)
                logger.info("Started stream: %s", stream_name)

        # Start data processing tasks (priority-based)
        for priority in DataPriority:
            task = asyncio.create_task(self._data_processor(priority))
            tasks.append(task)

        # Start metrics and cleanup tasks
        tasks.extend(
            [
                asyncio.create_task(self._metrics_reporter()),
                asyncio.create_task(self._cleanup_task()),
                asyncio.create_task(self._health_monitor()),
            ],
        )

        logger.info("✅ Pipeline started with %s concurrent tasks", len(tasks))

        # Wait for all tasks to complete (they should run indefinitely)
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down data ingestion pipeline...")
            for task in tasks:
                task.cancel()

    async def _websocket_stream_handler(self, stream: DataStream) -> None:
        """Handle WebSocket data streams."""
        while stream.active:
            try:
                logger.info("🔗 Connecting to WebSocket: %s", stream.source_name)

                async with websockets.connect(
                    stream.endpoint_url,
                    extra_headers=stream.headers,
                    ping_interval=20,
                    ping_timeout=10,
                ) as websocket:
                    # Send subscription message if needed
                    if stream.source_name == "coinbase_websocket":
                        subscribe_msg = {
                            "type": "subscribe",
                            "product_ids": stream.symbols,
                            "channels": ["ticker", "heartbeat"],
                        }
                        await websocket.send(orjson.dumps(subscribe_msg).decode())

                    # Store active connection
                    self.active_connections[stream.source_name] = websocket

                    # Process incoming messages
                    async for message in websocket:
                        try:
                            data = orjson.loads(message)

                            # Parse and queue data point
                            data_point = stream.parser_func(data, stream)
                            if data_point:
                                await self._queue_data_point(data_point)

                        except (ValueError, RuntimeError) as e:
                            self.metrics["errors"][stream.source_name] += 1
                            logger.error(
                                "Error processing WebSocket message from %s: %s",
                                stream.source_name,
                                e,
                            )

            except (ImportError, ModuleNotFoundError) as e:
                self.metrics["errors"][stream.source_name] += 1
                logger.error(
                    "WebSocket connection error for %s: %s",
                    stream.source_name,
                    e,
                )

                # Remove from active connections
                self.active_connections.pop(stream.source_name, None)

                # Exponential backoff retry
                retry_delay = min(60, 2 ** self.metrics["errors"][stream.source_name])
                logger.info("Retrying WebSocket connection in %ss...", retry_delay)
                await asyncio.sleep(retry_delay)

    async def _http_stream_handler(self, stream: DataStream) -> None:
        """Handle HTTP API data streams."""
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=stream.headers,
        )

        try:
            while stream.active:
                try:
                    start_time = time.time()

                    # Make API request
                    params = self._build_api_params(stream)
                    async with session.get(
                        stream.endpoint_url,
                        params=params,
                    ) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Parse and queue data points
                            data_points = stream.parser_func(data, stream)
                            if data_points:
                                if isinstance(data_points, list):
                                    for data_point in data_points:
                                        await self._queue_data_point(data_point)
                                else:
                                    await self._queue_data_point(data_points)

                            # Reset error count on success
                            self.metrics["errors"][stream.source_name] = 0

                        else:
                            logger.warning(
                                "API error for %s: %s",
                                stream.source_name,
                                response.status,
                            )
                            self.metrics["errors"][stream.source_name] += 1

                    # Calculate processing time
                    processing_time = time.time() - start_time
                    self.metrics["processing_latency"].append(processing_time)

                    # Wait for next update
                    await asyncio.sleep(stream.update_frequency)

                except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
                    self.metrics["errors"][stream.source_name] += 1
                    logger.error("HTTP stream error for %s: %s", stream.source_name, e)

                    # Exponential backoff
                    retry_delay = min(
                        60,
                        stream.update_frequency
                        * (2 ** min(5, self.metrics["errors"][stream.source_name])),
                    )
                    await asyncio.sleep(retry_delay)

        finally:
            await session.close()

    def _build_api_params(self, stream: DataStream) -> Dict[str, Any]:
        """Build API parameters for HTTP requests."""
        params = {}

        if stream.api_key:
            if stream.source_name == "alpha_vantage_quotes":
                params.update(
                    {
                        "function": "GLOBAL_QUOTE",
                        # Single symbol per request
                        "symbol": stream.symbols[0] if stream.symbols else "AAPL",
                        "apikey": stream.api_key,
                    },
                )
            elif stream.source_name == "newsapi":
                params.update(
                    {
                        "q": " OR ".join(stream.symbols),
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": 20,
                        "apiKey": stream.api_key,
                    },
                )
            elif stream.source_name == "fred_api":
                params.update(
                    {
                        "series_id": stream.symbols[0] if stream.symbols else "GDP",
                        "api_key": stream.api_key,
                        "file_type": "json",
                        "limit": 1,
                    },
                )

        elif stream.source_name == "coingecko_api":
            params.update(
                {
                    "ids": ",".join([s.lower() for s in stream.symbols]),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_last_updated_at": "true",
                },
            )

        return params

    async def _queue_data_point(self, data_point: DataPoint) -> None:
        """Queue a data point for processing."""
        try:
            # Check for duplicates
            if self._is_duplicate(data_point):
                self.metrics["data_points_deduplicated"] += 1
                return

            # Add to appropriate priority queue
            queue = self.data_queues[data_point.priority]

            try:
                queue.put_nowait(data_point)

                # Update cache
                self.dedup_cache[data_point.hash_key] = time.time()

                # Track queue sizes
                self.metrics["queue_sizes"][data_point.priority].append(queue.qsize())

            except asyncio.QueueFull:
                logger.warning(
                    "Queue full for priority %s, dropping data point",
                    data_point.priority.name,
                )

        except (ValueError, RuntimeError) as e:
            logger.error("Error queuing data point: %s", e)

    def _is_duplicate(self, data_point: DataPoint) -> bool:
        """Check if data point is a duplicate."""
        if data_point.hash_key in self.dedup_cache:
            # Check if it's a recent duplicate (within last 5 minutes)
            last_seen = self.dedup_cache[data_point.hash_key]
            if time.time() - last_seen < 300:  # 5 minutes
                return True

        return False

    async def _data_processor(self, priority: DataPriority) -> None:
        """Process data points from priority queue."""
        queue = self.data_queues[priority]

        while True:
            try:
                # Get data point from queue
                data_point = await queue.get()

                # Process data point
                start_time = time.time()
                await self._process_data_point(data_point)
                processing_time = time.time() - start_time

                # Track metrics
                self.metrics["data_points_processed"] += 1
                self.metrics["processing_latency"].append(processing_time)

                # Mark task as done
                queue.task_done()

                # Performance check for critical data
                if priority == DataPriority.CRITICAL and processing_time > 0.1:
                    logger.warning(
                        "Critical data processing took %ss (target: <0.1s)",
                        f"{processing_time:.3f}",
                    )

            except (ValueError, RuntimeError) as e:
                logger.error("Error in data processor for %s: %s", priority.name, e)
                await asyncio.sleep(0.1)  # Brief pause before retry

    async def _process_data_point(self, data_point: DataPoint) -> None:
        """Process individual data point."""
        try:
            # Publish to Redis if available (for real-time subscribers)
            if self.redis_client:
                channel = f"data:{data_point.data_type.value}"
                message = {
                    "source": data_point.source,
                    "symbol": data_point.symbol,
                    "timestamp": data_point.timestamp.isoformat(),
                    "data": data_point.data,
                    "priority": data_point.priority.name,
                }
                await self.redis_client.publish(channel, orjson.dumps(message).decode())

            # Notify local subscribers
            subscribers = self.subscribers.get(data_point.data_type, [])
            for subscriber in subscribers:
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        await subscriber(data_point)
                    else:
                        subscriber(data_point)
                except (ValueError, RuntimeError) as e:
                    logger.error("Error notifying subscriber: %s", e)

        except (ValueError, RuntimeError) as e:
            logger.error("Error processing data point: %s", e)

    def subscribe(self, data_type: DataSourceType, callback: Callable) -> None:
        """Subscribe to data points of a specific type."""
        self.subscribers[data_type].append(callback)
        logger.info("Added subscriber for %s", data_type.value)

    def unsubscribe(self, data_type: DataSourceType, callback: Callable) -> None:
        """Unsubscribe from data points."""
        if callback in self.subscribers[data_type]:
            self.subscribers[data_type].remove(callback)

    async def _metrics_reporter(self) -> None:
        """Report performance metrics periodically."""
        while True:
            try:
                await asyncio.sleep(60)  # Report every minute

                # Calculate metrics
                if self.metrics["processing_latency"]:
                    avg_latency = np.mean(self.metrics["processing_latency"])
                    p95_latency = np.percentile(self.metrics["processing_latency"], 95)
                else:
                    avg_latency = p95_latency = 0

                # Queue size metrics
                queue_sizes = {
                    priority.name: queue.qsize()
                    for priority, queue in self.data_queues.items()
                }

                # Connection status
                active_connections = len(self.active_connections)

                metrics_report = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data_points_processed": self.metrics["data_points_processed"],
                    "data_points_deduplicated": self.metrics[
                        "data_points_deduplicated"
                    ],
                    "avg_processing_latency_ms": avg_latency * 1000,
                    "p95_processing_latency_ms": p95_latency * 1000,
                    "queue_sizes": queue_sizes,
                    "active_connections": active_connections,
                    "total_errors": sum(self.metrics["errors"].values()),
                }

                logger.info(
                    "📊 Pipeline metrics: %s",
                    orjson.dumps(metrics_report).decode(),
                )

                # Publish metrics to Redis if available
                if self.redis_client:
                    await self.redis_client.publish(
                        "metrics:pipeline",
                        orjson.dumps(metrics_report).decode(),
                    )

            except (json.JSONDecodeError, ValueError) as e:
                logger.error("Error reporting metrics: %s", e)

    async def _cleanup_task(self) -> None:
        """Periodic cleanup of caches and old data."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                # Clean up deduplication cache
                current_time = time.time()
                expired_keys = [
                    key
                    for key, timestamp in self.dedup_cache.items()
                    if current_time - timestamp > 300  # 5 minutes
                ]

                for key in expired_keys:
                    del self.dedup_cache[key]

                # Limit cache size
                if len(self.dedup_cache) > self.dedup_cache_size:
                    # Remove oldest entries
                    sorted_items = sorted(self.dedup_cache.items(), key=lambda x: x[1])
                    items_to_remove = len(sorted_items) - self.dedup_cache_size
                    for key, _ in sorted_items[:items_to_remove]:
                        del self.dedup_cache[key]

                logger.debug("Cleaned up %s expired cache entries", len(expired_keys))

            except (ValueError, RuntimeError) as e:
                logger.error("Error in cleanup task: %s", e)

    async def _health_monitor(self) -> None:
        """Monitor pipeline health and restart failed streams."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check for failed streams
                for stream_name, stream in self.data_streams.items():
                    if stream.active and stream.is_websocket:
                        if stream_name not in self.active_connections:
                            logger.warning(
                                "WebSocket stream %s appears disconnected",
                                stream_name,
                            )
                            # The websocket handler should automatically retry

                    # Check error rates
                    error_count = self.metrics["errors"].get(stream_name, 0)
                    if error_count > 10:  # High error rate
                        logger.warning(
                            "High error rate for %s: %s errors",
                            stream_name,
                            error_count,
                        )

            except (ValueError, RuntimeError) as e:
                logger.error("Error in health monitor: %s", e)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current pipeline metrics."""
        return {
            "data_points_processed": self.metrics["data_points_processed"],
            "data_points_deduplicated": self.metrics["data_points_deduplicated"],
            "queue_sizes": {p.name: q.qsize() for p, q in self.data_queues.items()},
            "active_connections": len(self.active_connections),
            "cache_size": len(self.dedup_cache),
            "error_counts": dict(self.metrics["errors"]),
        }

    # Data parser functions

    def _parse_alpha_vantage_quote(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> DataPoint | None:
        """Parse Alpha Vantage quote data."""
        try:
            if "Global Quote" in data:
                quote = data["Global Quote"]
                symbol = quote.get("01. symbol", "")

                return DataPoint(
                    source=stream.source_name,
                    data_type=stream.data_type,
                    symbol=symbol,
                    timestamp=datetime.now(UTC),
                    data={
                        "price": float(quote.get("05. price", 0)),
                        "change": float(quote.get("09. change", 0)),
                        "change_percent": quote.get("10. change percent", "0%").strip(
                            "%",
                        ),
                        "volume": int(quote.get("06. volume", 0)),
                        "high": float(quote.get("03. high", 0)),
                        "low": float(quote.get("04. low", 0)),
                        "open": float(quote.get("02. open", 0)),
                    },
                    priority=stream.priority,
                )
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing Alpha Vantage data: %s", e)
        return None

    def _parse_yahoo_websocket(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> DataPoint | None:
        """Parse Yahoo Finance WebSocket data."""
        try:
            # Yahoo WebSocket format varies - this is a placeholder
            if "id" in data and "price" in data:
                return DataPoint(
                    source=stream.source_name,
                    data_type=stream.data_type,
                    symbol=data.get("id", ""),
                    timestamp=datetime.now(UTC),
                    data={
                        "price": data.get("price", 0),
                        "volume": data.get("volume", 0),
                        "change": data.get("change", 0),
                    },
                    priority=stream.priority,
                )
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing Yahoo WebSocket data: %s", e)
        return None

    def _parse_coinbase_websocket(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> DataPoint | None:
        """Parse Coinbase Pro WebSocket data."""
        try:
            if data.get("type") == "ticker":
                return DataPoint(
                    source=stream.source_name,
                    data_type=stream.data_type,
                    symbol=data.get("product_id", ""),
                    timestamp=datetime.now(UTC),
                    data={
                        "price": float(data.get("price", 0)),
                        "volume_24h": float(data.get("volume_24h", 0)),
                        "high_24h": float(data.get("high_24h", 0)),
                        "low_24h": float(data.get("low_24h", 0)),
                        "best_bid": float(data.get("best_bid", 0)),
                        "best_ask": float(data.get("best_ask", 0)),
                    },
                    priority=stream.priority,
                )
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing Coinbase WebSocket data: %s", e)
        return None

    def _parse_coingecko_price(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> list[DataPoint]:
        """Parse CoinGecko price data."""
        data_points = []
        try:
            for symbol_id, price_data in data.items():
                if isinstance(price_data, dict) and "usd" in price_data:
                    data_point = DataPoint(
                        source=stream.source_name,
                        data_type=stream.data_type,
                        symbol=symbol_id.upper(),
                        timestamp=datetime.now(UTC),
                        data={
                            "price": price_data.get("usd", 0),
                            "change_24h": price_data.get("usd_24h_change", 0),
                            "volume_24h": price_data.get("usd_24h_vol", 0),
                            "last_updated": price_data.get("last_updated_at", 0),
                        },
                        priority=stream.priority,
                    )
                    data_points.append(data_point)
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing CoinGecko data: %s", e)

        return data_points

    def _parse_news_api(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> list[DataPoint]:
        """Parse NewsAPI data."""
        data_points = []
        try:
            for article in data.get("articles", []):
                data_point = DataPoint(
                    source=stream.source_name,
                    data_type=stream.data_type,
                    symbol=None,  # News is not symbol-specific
                    timestamp=datetime.now(UTC),
                    data={
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "content": article.get("content", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "published_at": article.get("publishedAt", ""),
                        "author": article.get("author", ""),
                    },
                    priority=stream.priority,
                )
                data_points.append(data_point)
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing NewsAPI data: %s", e)

        return data_points

    def _parse_reddit_posts(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> list[DataPoint]:
        """Parse Reddit API data."""
        data_points = []
        try:
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                data_point = DataPoint(
                    source=stream.source_name,
                    data_type=stream.data_type,
                    symbol=None,
                    timestamp=datetime.now(UTC),
                    data={
                        "title": post_data.get("title", ""),
                        "selftext": post_data.get("selftext", ""),
                        "subreddit": post_data.get("subreddit", ""),
                        "score": post_data.get("score", 0),
                        "num_comments": post_data.get("num_comments", 0),
                        "created_utc": post_data.get("created_utc", 0),
                        "url": post_data.get("url", ""),
                        "author": post_data.get("author", ""),
                    },
                    priority=stream.priority,
                )
                data_points.append(data_point)
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing Reddit data: %s", e)

        return data_points

    def _parse_fred_data(
        self,
        data: Dict[str, Any],
        stream: DataStream,
    ) -> DataPoint | None:
        """Parse FRED economic data."""
        try:
            observations = data.get("observations", [])
            if observations:
                latest = observations[-1]  # Get most recent observation

                return DataPoint(
                    source=stream.source_name,
                    data_type=stream.data_type,
                    symbol=latest.get("series_id", ""),
                    timestamp=datetime.now(UTC),
                    data={
                        "value": (
                            float(latest.get("value", 0))
                            if latest.get("value") != "."
                            else 0
                        ),
                        "date": latest.get("date", ""),
                        "series_id": latest.get("series_id", ""),
                    },
                    priority=stream.priority,
                )
        except (ValueError, RuntimeError) as e:
            logger.error("Error parsing FRED data: %s", e)

        return None


# Example usage and configuration


async def main_pipeline_demo() -> None:
    """Demo of the data ingestion pipeline."""
    config = {
        "use_uvloop": True,
        "redis_url": "redis://localhost:6379",  # Optional
        "stock_symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        "crypto_symbols": ["bitcoin", "ethereum", "solana"],
        "alpha_vantage_api_key": "demo",  # Replace with real API key
        "newsapi_key": None,  # Add NewsAPI key if available
        "enable_yahoo_websocket": False,  # Requires proper WebSocket URL
        "enable_news_feeds": True,
        "enable_social_feeds": False,  # Requires Reddit API credentials
        "enable_economic_data": True,
        "dedup_cache_size": 50000,
    }

    # Initialize pipeline
    pipeline = DataIngestionPipeline(config)

    # Add data subscribers
    def print_market_data(data_point: DataPoint) -> None:
        if data_point.symbol:
            print(f"📈 {data_point.symbol}: ${data_point.data.get('price', 0):.4f}")

    def print_news(data_point: DataPoint) -> None:
        title = data_point.data.get("title", "Unknown")[:50]
        print(f"📰 News: {title}...")

    pipeline.subscribe(DataSourceType.MARKET_DATA, print_market_data)
    pipeline.subscribe(DataSourceType.NEWS, print_news)

    # Start pipeline
    try:
        await pipeline.start()
    except KeyboardInterrupt:
        print("🛑 Pipeline stopped")


if __name__ == "__main__":
    asyncio.run(main_pipeline_demo())