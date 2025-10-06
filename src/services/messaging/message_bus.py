#!/usr/bin/env python3
"""PAKE System - Redis Streams-based Message Bus
Event-driven hierarchical architecture for Phase 2B transformation.

Implements high-performance message bus using Redis Streams for:
- Supervisor-Worker communication
- Real-time event distribution
- Fault-tolerant message processing
- Scalable inter-service communication
"""

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
import logging
from typing import Any, Dict
import uuid

import redis.asyncio as redis
from redis.asyncio import default_backoff
from redis.asyncio.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for event-driven communication."""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_STATUS = "task_status"
    SYSTEM_EVENT = "system_event"
    HEALTH_CHECK = "health_check"
    COGNITIVE_ASSESSMENT = "cognitive_assessment"
    WORKFLOW_TRIGGER = "workflow_trigger"
    ERROR_NOTIFICATION = "error_notification"


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class Message:
    """Immutable message structure for event-driven communication."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK_REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    source: str = "unknown"
    target: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    reply_to: str | None = None
    ttl: int | None = None  # Time to live in seconds
    retries: int = 0
    max_retries: int = 3


@dataclass
class StreamConfig:
    """Configuration for Redis Streams."""

    max_len: int = 10000  # Maximum stream length
    approximate_max_len: bool = True  # Use ~ for approximate trimming
    consumer_group: str = "pake_consumers"
    consumer_name: str = "default"
    block_timeout: int = 1000  # Milliseconds
    count: int = 10  # Messages to read per batch
    auto_ack: bool = True
    dead_letter_stream: str | None = None


class MessageBus:
    """Redis Streams-based message bus for event-driven hierarchical architecture.

    Provides high-performance, fault-tolerant messaging between:
    - Supervisor agent (orchestrator)
    - Worker agents (AI services)
    - System components
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", stream_config: StreamConfig | None = None, max_connections: int = 10) -> None:
        """Initialize message bus with Redis connection pool."""
        self.redis_url = redis_url
        self.config = stream_config or StreamConfig()
        self.max_connections = max_connections

        # Initialize Redis connection pool
        self.redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            retry_on_timeout=True,
            retry=Retry(default_backoff(), 3),
            health_check_interval=30,
        )

        # Message handlers and subscribers
        self._handlers: dict[str, list[Callable]] = {}
        self._subscribers: dict[str, asyncio.Task] = {}
        self._running = False

        # Performance metrics
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "active_streams": 0,
            "active_consumers": 0,
        }

        logger.info(
            "MessageBus initialized with Redis pool (max_connections=%s)",
            max_connections,
        )

    async def start(self) -> None:
        """Start message bus and initialize streams."""
        if self._running:
            return

        self._running = True
        logger.info("Starting Redis Streams message bus...")

        # Test Redis connection
        async with redis.Redis(connection_pool=self.redis_pool) as r:
            await r.ping()
            logger.info("Redis connection established")

        # Initialize core streams
        await self._initialize_streams()

        logger.info("Message bus started successfully")

    async def stop(self) -> None:
        """Stop message bus and cleanup resources."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping message bus...")

        # Stop all subscribers
        for task in self._subscribers.values():
            task.cancel()

        # Wait for subscribers to finish
        if self._subscribers:
            await asyncio.gather(*self._subscribers.values(), return_exceptions=True)

        # Close connection pool
        await self.redis_pool.disconnect()

        logger.info("Message bus stopped")

    async def publish(
        self,
        stream: str,
        message: Message,
        partition_key: str | None = None,
    ) -> str:
        """Publish message to Redis Stream with optional partitioning.

        Returns:
            Message ID assigned by Redis
        """
        try:
            # Serialize message data
            message_data = {
                "id": message.id,
                "type": message.type.value,
                "priority": message.priority.value,
                "source": message.source,
                "target": message.target or "",
                "timestamp": message.timestamp.isoformat(),
                "data": json.dumps(message.data),
                "correlation_id": message.correlation_id or "",
                "reply_to": message.reply_to or "",
                "ttl": message.ttl or 0,
                "retries": message.retries,
                "max_retries": message.max_retries,
            }

            # Add partition key if provided
            if partition_key:
                message_data["partition_key"] = partition_key

            async with redis.Redis(connection_pool=self.redis_pool) as r:
                # Use XADD to add message to stream
                message_id = await r.xadd(
                    stream,
                    message_data,
                    maxlen=self.config.max_len,
                    approximate=self.config.approximate_max_len,
                )

                self._metrics["messages_sent"] += 1
                logger.debug(
                    "Published message %s to stream %s with ID %s",
                    message.id,
                    stream,
                    message_id,
                )
                return message_id

        except (ValueError, RuntimeError) as e:
            self._metrics["messages_failed"] += 1
            logger.error("Failed to publish message to stream %s: %s", stream, e)
            raise

    async def subscribe(
        self,
        stream: str,
        handler: Callable[[Message], None],
        consumer_group: str | None = None,
        consumer_name: str | None = None,
    ) -> str:
        """Subscribe to stream with message handler.

        Returns:
            Subscription ID for tracking
        """
        group = consumer_group or self.config.consumer_group
        consumer = consumer_name or self.config.consumer_name
        subscription_id = f"{stream}:{group}:{consumer}"

        # Create consumer group if it doesn't exist
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as r:
                await r.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        # Start consumer task
        consumer_task = asyncio.create_task(
            self._consumer_loop(stream, group, consumer, handler),
        )
        self._subscribers[subscription_id] = consumer_task

        logger.info(
            "Subscribed to stream %s with group %s, consumer %s",
            stream,
            group,
            consumer,
        )
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from stream."""
        if subscription_id in self._subscribers:
            task = self._subscribers.pop(subscription_id)
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

            logger.info("Unsubscribed from %s", subscription_id)

    async def request_response(
        self,
        stream: str,
        request: Message,
        timeout: float = 30.0,
    ) -> Message:
        """Send request and wait for response with correlation ID.

        Implements request-response pattern over streams.
        """
        # Set up response correlation
        correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id
        response_stream = f"{stream}:responses"

        # Create response future
        response_future = asyncio.Future()

        # Subscribe to response stream temporarily
        async def response_handler(message: Message) -> None:
            if message.correlation_id == correlation_id:
                response_future.set_result(message)

        response_sub_id = await self.subscribe(response_stream, response_handler)

        try:
            # Send request
            await self.publish(stream, request)

            # Wait for response with timeout
            return await asyncio.wait_for(response_future, timeout=timeout)

        finally:
            # Cleanup response subscription
            await self.unsubscribe(response_sub_id)

    async def send_response(self, response: Message, original_message: Message, response_stream: str) -> None:
        """Send response to request with proper correlation."""
        response.correlation_id = original_message.correlation_id
        response.target = original_message.source

        await self.publish(response_stream, response)

    async def get_stream_info(self, stream: str) -> Dict[str, Any]:
        """Get information about stream."""
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as r:
                return await r.xinfo_stream(stream)
        except redis.ResponseError:
            return {}

    async def get_consumer_group_info(
        self,
        stream: str,
        group: str | None = None,
    ) -> list[Dict[str, Any]]:
        """Get consumer group information."""
        group = group or self.config.consumer_group

        try:
            async with redis.Redis(connection_pool=self.redis_pool) as r:
                groups = await r.xinfo_groups(stream)
                return [g for g in groups if g["name"] == group.encode()]
        except redis.ResponseError:
            return []

    async def acknowledge_message(self, stream: str, group: str, message_id: str) -> None:
        """Acknowledge message processing."""
        try:
            async with redis.Redis(connection_pool=self.redis_pool) as r:
                await r.xack(stream, group, message_id)
        except redis.ResponseError as e:
            logger.warning("Failed to ack message %s: %s", message_id, e)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get message bus performance metrics."""
        metrics = self._metrics.copy()
        metrics.update(
            {
                "active_streams": len(
                    {sub.split(":")[0] for sub in self._subscribers},
                ),
                "active_consumers": len(self._subscribers),
                "redis_pool_created_connections": self.redis_pool.created_connections,
                "redis_pool_available_connections": len(
                    self.redis_pool._available_connections,
                ),
            },
        )

        return metrics

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on message bus."""
        health = {
            "status": "healthy",
            "redis_connected": False,
            "streams_active": 0,
            "consumers_active": len(self._subscribers),
            "metrics": await self.get_metrics(),
        }

        try:
            async with redis.Redis(connection_pool=self.redis_pool) as r:
                await r.ping()
                health["redis_connected"] = True

                # Check stream existence
                active_streams = set()
                for sub_id in self._subscribers:
                    stream = sub_id.split(":")[0]
                    try:
                        await r.xinfo_stream(stream)
                        active_streams.add(stream)
                    except redis.ResponseError as e:

                        logger.debug(f"Exception in message_bus.py: {e}")

                        # Continue gracefully

                health["streams_active"] = len(active_streams)

        except (ValueError, RuntimeError) as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)

        return health

    async def _initialize_streams(self) -> None:
        """Initialize core message streams."""
        core_streams = [
            "supervisor:tasks",  # Supervisor -> Workers
            "supervisor:responses",  # Workers -> Supervisor
            "system:events",  # System-wide events
            "health:checks",  # Health monitoring
            "cognitive:assessments",  # Cognitive processing
            "workflows:triggers",  # n8n workflow triggers
        ]

        async with redis.Redis(connection_pool=self.redis_pool) as r:
            for stream in core_streams:
                try:
                    # Create stream if it doesn't exist
                    await r.xadd(stream, {"init": "stream"}, maxlen=1)
                    # Remove init message
                    await r.xtrim(stream, maxlen=0, approximate=True)

                    logger.debug("Initialized stream: %s", stream)

                except (ValueError, RuntimeError) as e:
                    logger.warning("Failed to initialize stream %s: %s", stream, e)

        self._metrics["active_streams"] = len(core_streams)

    async def _consumer_loop(self, stream: str, group: str, consumer: str, handler: Callable[[Message], None]) -> None:
        """Main consumer loop for processing messages."""
        logger.info("Starting consumer loop for %s:%s:%s", stream, group, consumer)

        async with redis.Redis(connection_pool=self.redis_pool) as r:
            while self._running:
                try:
                    # Read messages from stream
                    messages = await r.xreadgroup(
                        group,
                        consumer,
                        {stream: ">"},
                        count=self.config.count,
                        block=self.config.block_timeout,
                    )

                    for stream_messages in messages:
                        stream_name, stream_data = stream_messages

                        for message_id, fields in stream_data:
                            try:
                                # Parse message
                                message = self._parse_message(fields)

                                # Call handler
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(message)
                                else:
                                    handler(message)

                                # Acknowledge if auto-ack enabled
                                if self.config.auto_ack:
                                    await self.acknowledge_message(
                                        stream_name.decode(),
                                        group,
                                        message_id.decode(),
                                    )

                                self._metrics["messages_received"] += 1

                            except (ValueError, RuntimeError) as e:
                                logger.error(
                                    "Error processing message %s: %s",
                                    message_id,
                                    e,
                                )
                                self._metrics["messages_failed"] += 1

                except asyncio.CancelledError:
                    break
                except (ValueError, RuntimeError) as e:
                    logger.error("Consumer loop error: %s", e)
                    await asyncio.sleep(1)  # Brief pause before retry

        logger.info("Consumer loop stopped for %s:%s:%s", stream, group, consumer)

    def _parse_message(self, fields: dict[bytes, bytes]) -> Message:
        """Parse Redis stream message into Message object."""
        # Decode bytes to strings
        decoded_fields = {k.decode(): v.decode() for k, v in fields.items()}

        return Message(
            id=decoded_fields.get("id", ""),
            type=MessageType(decoded_fields.get("type", "task_request")),
            priority=MessagePriority(int(decoded_fields.get("priority", "2"))),
            source=decoded_fields.get("source", "unknown"),
            target=decoded_fields.get("target") or None,
            timestamp=datetime.fromisoformat(
                decoded_fields.get("timestamp", datetime.now(UTC).isoformat()),
            ),
            data=json.loads(decoded_fields.get("data", "{}")),
            correlation_id=decoded_fields.get("correlation_id") or None,
            reply_to=decoded_fields.get("reply_to") or None,
            ttl=int(decoded_fields.get("ttl", "0")) or None,
            retries=int(decoded_fields.get("retries", "0")),
            max_retries=int(decoded_fields.get("max_retries", "3")),
        )


# Convenience functions for common messaging patterns


async def create_message_bus(redis_url: str = None) -> MessageBus:
    """Create and start message bus instance."""
    if redis_url is None:
        # Use environment variable or default
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    bus = MessageBus(redis_url)
    await bus.start()
    return bus


def create_task_message(
    source: str,
    target: str,
    task_type: str,
    task_data: Dict[str, Any],
    priority: MessagePriority = MessagePriority.NORMAL,
) -> Message:
    """Create task request message."""
    return Message(
        type=MessageType.TASK_REQUEST,
        priority=priority,
        source=source,
        target=target,
        data={
            "task_type": task_type,
            "task_data": task_data,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )


def create_response_message(
    source: str,
    target: str,
    result: Any,
    success: bool = True,
    error: str = None,
) -> Message:
    """Create task response message."""
    return Message(
        type=MessageType.TASK_RESPONSE,
        source=source,
        target=target,
        data={
            "result": result,
            "success": success,
            "error": error,
            "completed_at": datetime.now(UTC).isoformat(),
        },
    )


def create_system_event(
    source: str,
    event_type: str,
    event_data: Dict[str, Any],
    priority: MessagePriority = MessagePriority.NORMAL,
) -> Message:
    """Create system event message."""
    return Message(
        type=MessageType.SYSTEM_EVENT,
        priority=priority,
        source=source,
        data={
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )