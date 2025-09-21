#!/usr/bin/env python3
"""PAKE System - Event-Driven Communication Protocols
Standardized protocols for hierarchical architecture communication.

Defines:
- Communication patterns between Supervisor and Workers
- Event schemas and message formats
- Protocol handlers and middleware
- Error handling and retry mechanisms
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ..messaging.message_bus import Message, MessageBus, MessagePriority, MessageType

# Configure logging
logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """Communication protocol types"""

    REQUEST_RESPONSE = "request_response"
    PUBLISH_SUBSCRIBE = "publish_subscribe"
    COMMAND_QUERY = "command_query"
    EVENT_SOURCING = "event_sourcing"
    TASK_COORDINATION = "task_coordination"


class CommunicationPattern(Enum):
    """Communication patterns between agents"""

    SUPERVISOR_TO_WORKER = "supervisor_to_worker"
    WORKER_TO_SUPERVISOR = "worker_to_supervisor"
    WORKER_TO_WORKER = "worker_to_worker"
    SYSTEM_BROADCAST = "system_broadcast"
    HEALTH_MONITORING = "health_monitoring"


@dataclass(frozen=True)
class ProtocolMessage:
    """Standardized protocol message structure"""

    protocol_version: str = "1.0"
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None
    pattern: CommunicationPattern = CommunicationPattern.SUPERVISOR_TO_WORKER
    sender_id: str = ""
    receiver_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    ttl: int | None = None  # Time to live in seconds
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ProtocolConfig:
    """Configuration for communication protocols"""

    default_timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.5
    enable_compression: bool = False
    enable_encryption: bool = False
    message_ordering: bool = True
    duplicate_detection: bool = True
    dead_letter_handling: bool = True


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers"""

    def __init__(self, protocol_type: ProtocolType, config: ProtocolConfig = None):
        self.protocol_type = protocol_type
        self.config = config or ProtocolConfig()
        self.middleware: list[Callable] = []

    @abstractmethod
    async def handle_message(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle incoming protocol message"""

    def add_middleware(self, middleware: Callable):
        """Add middleware to protocol handler"""
        self.middleware.append(middleware)

    async def process_middleware(self, message: ProtocolMessage) -> ProtocolMessage:
        """Process message through middleware chain"""
        for middleware_func in self.middleware:
            try:
                message = await middleware_func(message)
            except Exception as e:
                logger.warning(f"Middleware processing error: {e}")

        return message


class RequestResponseProtocol(ProtocolHandler):
    """Request-Response communication protocol"""

    def __init__(self, config: ProtocolConfig = None):
        super().__init__(ProtocolType.REQUEST_RESPONSE, config)
        self.pending_requests: dict[str, asyncio.Future] = {}

    async def send_request(
        self,
        message_bus: MessageBus,
        request: ProtocolMessage,
        timeout: float = None,
    ) -> ProtocolMessage:
        """Send request and wait for response"""
        timeout = timeout or self.config.default_timeout
        correlation_id = request.correlation_id or str(uuid.uuid4())

        # Create response future
        response_future = asyncio.Future()
        self.pending_requests[correlation_id] = response_future

        try:
            # Convert protocol message to bus message
            bus_message = self._protocol_to_bus_message(request)
            bus_message.correlation_id = correlation_id

            # Send request
            stream = self._get_stream_for_pattern(request.pattern)
            await message_bus.publish(stream, bus_message)

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response

        except TimeoutError:
            raise TimeoutError(f"Request {correlation_id} timed out after {timeout}s")
        finally:
            # Cleanup
            self.pending_requests.pop(correlation_id, None)

    async def handle_message(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle incoming request or response"""
        # Process through middleware
        message = await self.process_middleware(message)

        # Check if this is a response to pending request
        if message.correlation_id and message.correlation_id in self.pending_requests:
            future = self.pending_requests[message.correlation_id]
            if not future.done():
                future.set_result(message)
            return None

        # This is a new request - subclasses should override
        return await self._handle_request(message)

    async def _handle_request(
        self,
        request: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle incoming request - to be overridden by subclasses"""
        return None

    def _protocol_to_bus_message(self, protocol_msg: ProtocolMessage) -> Message:
        """Convert protocol message to bus message"""
        return Message(
            type=MessageType.TASK_REQUEST,
            priority=MessagePriority.NORMAL,
            source=protocol_msg.sender_id,
            target=protocol_msg.receiver_id,
            data=protocol_msg.payload,
            correlation_id=protocol_msg.correlation_id,
            ttl=protocol_msg.ttl,
        )

    def _get_stream_for_pattern(self, pattern: CommunicationPattern) -> str:
        """Get Redis stream name for communication pattern"""
        if pattern == CommunicationPattern.SUPERVISOR_TO_WORKER:
            return "supervisor:tasks"
        if pattern == CommunicationPattern.WORKER_TO_SUPERVISOR:
            return "supervisor:responses"
        if pattern == CommunicationPattern.SYSTEM_BROADCAST:
            return "system:events"
        if pattern == CommunicationPattern.HEALTH_MONITORING:
            return "health:checks"
        return "general:messages"


class PublishSubscribeProtocol(ProtocolHandler):
    """Publish-Subscribe communication protocol"""

    def __init__(self, config: ProtocolConfig = None):
        super().__init__(ProtocolType.PUBLISH_SUBSCRIBE, config)
        self.subscribers: dict[str, list[Callable]] = {}

    async def publish(
        self,
        message_bus: MessageBus,
        topic: str,
        message: ProtocolMessage,
    ):
        """Publish message to topic"""
        # Process through middleware
        message = await self.process_middleware(message)

        # Convert to bus message
        bus_message = self._protocol_to_bus_message(message)

        # Publish to appropriate stream
        stream = f"pubsub:{topic}"
        await message_bus.publish(stream, bus_message)

    async def subscribe(
        self,
        message_bus: MessageBus,
        topic: str,
        handler: Callable[[ProtocolMessage], None],
    ):
        """Subscribe to topic with handler"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []

        self.subscribers[topic].append(handler)

        # Subscribe to stream
        stream = f"pubsub:{topic}"
        await message_bus.subscribe(stream, self._handle_subscription_message)

    async def handle_message(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle incoming published message"""
        # Process through middleware
        message = await self.process_middleware(message)

        # Notify subscribers
        topic = message.metadata.get("topic", "default")
        if topic in self.subscribers:
            for handler in self.subscribers[topic]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Subscriber handler error: {e}")

        return None

    async def _handle_subscription_message(self, bus_message: Message):
        """Handle message from subscription stream"""
        # Convert bus message to protocol message
        protocol_msg = self._bus_to_protocol_message(bus_message)
        await self.handle_message(protocol_msg)

    def _protocol_to_bus_message(self, protocol_msg: ProtocolMessage) -> Message:
        """Convert protocol message to bus message"""
        return Message(
            type=MessageType.SYSTEM_EVENT,
            priority=MessagePriority.NORMAL,
            source=protocol_msg.sender_id,
            data=protocol_msg.payload,
            correlation_id=protocol_msg.correlation_id,
        )

    def _bus_to_protocol_message(self, bus_msg: Message) -> ProtocolMessage:
        """Convert bus message to protocol message"""
        return ProtocolMessage(
            sender_id=bus_msg.source,
            receiver_id=bus_msg.target,
            correlation_id=bus_msg.correlation_id,
            payload=bus_msg.data,
            timestamp=bus_msg.timestamp,
        )


class TaskCoordinationProtocol(ProtocolHandler):
    """Task coordination protocol for Supervisor-Worker interactions"""

    def __init__(self, config: ProtocolConfig = None):
        super().__init__(ProtocolType.TASK_COORDINATION, config)
        self.active_tasks: dict[str, dict[str, Any]] = {}
        self.worker_status: dict[str, str] = {}

    async def assign_task(
        self,
        message_bus: MessageBus,
        worker_id: str,
        task_data: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """Assign task to worker and return task ID"""
        task_id = str(uuid.uuid4())

        # Create task assignment message
        assignment_msg = ProtocolMessage(
            pattern=CommunicationPattern.SUPERVISOR_TO_WORKER,
            sender_id="supervisor",
            receiver_id=worker_id,
            correlation_id=task_id,
            payload={
                "task_type": "assignment",
                "task_id": task_id,
                "task_data": task_data,
                "assigned_at": datetime.now(UTC).isoformat(),
                "priority": priority.value,
            },
            metadata={"protocol": "task_coordination", "action": "assign_task"},
        )

        # Track active task
        self.active_tasks[task_id] = {
            "worker_id": worker_id,
            "status": "assigned",
            "assigned_at": datetime.now(UTC),
            "task_data": task_data,
        }

        # Send assignment
        await self._send_protocol_message(message_bus, assignment_msg)

        logger.debug(f"Assigned task {task_id} to worker {worker_id}")
        return task_id

    async def report_task_progress(
        self,
        message_bus: MessageBus,
        task_id: str,
        progress: dict[str, Any],
    ):
        """Report task progress from worker"""
        progress_msg = ProtocolMessage(
            pattern=CommunicationPattern.WORKER_TO_SUPERVISOR,
            sender_id=progress.get("worker_id", "unknown"),
            receiver_id="supervisor",
            correlation_id=task_id,
            payload={
                "task_type": "progress",
                "task_id": task_id,
                "progress": progress,
                "reported_at": datetime.now(UTC).isoformat(),
            },
            metadata={"protocol": "task_coordination", "action": "report_progress"},
        )

        await self._send_protocol_message(message_bus, progress_msg)

    async def complete_task(
        self,
        message_bus: MessageBus,
        task_id: str,
        result: dict[str, Any],
        success: bool = True,
    ):
        """Complete task and report result"""
        completion_msg = ProtocolMessage(
            pattern=CommunicationPattern.WORKER_TO_SUPERVISOR,
            sender_id=result.get("worker_id", "unknown"),
            receiver_id="supervisor",
            correlation_id=task_id,
            payload={
                "task_type": "completion",
                "task_id": task_id,
                "result": result,
                "success": success,
                "completed_at": datetime.now(UTC).isoformat(),
            },
            metadata={"protocol": "task_coordination", "action": "complete_task"},
        )

        # Update task status
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "completed" if success else "failed"
            self.active_tasks[task_id]["completed_at"] = datetime.now(UTC)
            self.active_tasks[task_id]["result"] = result

        await self._send_protocol_message(message_bus, completion_msg)
        logger.debug(f"Task {task_id} completed with success={success}")

    async def handle_message(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle task coordination messages"""
        # Process through middleware
        message = await self.process_middleware(message)

        action = message.metadata.get("action")
        task_id = message.correlation_id

        if action == "assign_task":
            return await self._handle_task_assignment(message)
        if action == "report_progress":
            return await self._handle_progress_report(message)
        if action == "complete_task":
            return await self._handle_task_completion(message)
        logger.warning(f"Unknown task coordination action: {action}")
        return None

    async def _handle_task_assignment(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle task assignment (worker perspective)"""
        task_id = message.correlation_id
        task_data = message.payload.get("task_data", {})

        # Acknowledge assignment
        ack_msg = ProtocolMessage(
            pattern=CommunicationPattern.WORKER_TO_SUPERVISOR,
            sender_id=message.receiver_id,
            receiver_id=message.sender_id,
            correlation_id=task_id,
            payload={
                "task_type": "acknowledgment",
                "task_id": task_id,
                "acknowledged_at": datetime.now(UTC).isoformat(),
                "worker_status": "ready",
            },
            metadata={
                "protocol": "task_coordination",
                "action": "acknowledge_assignment",
            },
        )

        return ack_msg

    async def _handle_progress_report(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle progress report (supervisor perspective)"""
        task_id = message.correlation_id
        progress = message.payload.get("progress", {})

        # Update task tracking
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "in_progress"
            self.active_tasks[task_id]["progress"] = progress
            self.active_tasks[task_id]["last_update"] = datetime.now(UTC)

        logger.debug(f"Task {task_id} progress updated: {progress}")
        return None

    async def _handle_task_completion(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle task completion (supervisor perspective)"""
        task_id = message.correlation_id
        result = message.payload.get("result", {})
        success = message.payload.get("success", True)

        # Update task tracking
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "completed" if success else "failed"
            self.active_tasks[task_id]["result"] = result
            self.active_tasks[task_id]["completed_at"] = datetime.now(UTC)

        logger.info(f"Task {task_id} completed with success={success}")
        return None

    async def _send_protocol_message(
        self,
        message_bus: MessageBus,
        message: ProtocolMessage,
    ):
        """Send protocol message via message bus"""
        bus_message = Message(
            type=(
                MessageType.TASK_REQUEST
                if message.pattern == CommunicationPattern.SUPERVISOR_TO_WORKER
                else MessageType.TASK_RESPONSE
            ),
            priority=MessagePriority.NORMAL,
            source=message.sender_id,
            target=message.receiver_id,
            data=message.payload,
            correlation_id=message.correlation_id,
        )

        stream = (
            "supervisor:tasks"
            if message.pattern == CommunicationPattern.SUPERVISOR_TO_WORKER
            else "supervisor:responses"
        )
        await message_bus.publish(stream, bus_message)

    def get_active_tasks(self) -> dict[str, dict[str, Any]]:
        """Get all active tasks"""
        return self.active_tasks.copy()

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get specific task status"""
        return self.active_tasks.get(task_id)


class HealthMonitoringProtocol(ProtocolHandler):
    """Health monitoring protocol for system-wide health checks"""

    def __init__(self, config: ProtocolConfig = None):
        super().__init__(ProtocolType.EVENT_SOURCING, config)
        self.health_status: dict[str, dict[str, Any]] = {}
        self.health_history: list[dict[str, Any]] = []
        self.max_history = 1000

    async def send_heartbeat(
        self,
        message_bus: MessageBus,
        agent_id: str,
        health_data: dict[str, Any],
    ):
        """Send heartbeat with health data"""
        heartbeat_msg = ProtocolMessage(
            pattern=CommunicationPattern.HEALTH_MONITORING,
            sender_id=agent_id,
            payload={
                "heartbeat_type": "status_update",
                "agent_id": agent_id,
                "health_data": health_data,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            metadata={"protocol": "health_monitoring", "action": "heartbeat"},
        )

        await self._send_health_message(message_bus, heartbeat_msg)

    async def request_health_check(
        self,
        message_bus: MessageBus,
        target_agent: str = None,
    ) -> dict[str, Any]:
        """Request health check from agent(s)"""
        check_msg = ProtocolMessage(
            pattern=CommunicationPattern.SYSTEM_BROADCAST,
            sender_id="health_monitor",
            receiver_id=target_agent,
            payload={
                "check_type": "full_health_check",
                "requested_at": datetime.now(UTC).isoformat(),
                "include_metrics": True,
            },
            metadata={
                "protocol": "health_monitoring",
                "action": "health_check_request",
            },
        )

        await self._send_health_message(message_bus, check_msg)

        # Return current health status
        if target_agent:
            return self.health_status.get(target_agent, {})
        return self.health_status.copy()

    async def handle_message(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle health monitoring messages"""
        # Process through middleware
        message = await self.process_middleware(message)

        action = message.metadata.get("action")

        if action == "heartbeat":
            return await self._handle_heartbeat(message)
        if action == "health_check_request":
            return await self._handle_health_check_request(message)
        if action == "health_check_response":
            return await self._handle_health_check_response(message)
        logger.warning(f"Unknown health monitoring action: {action}")
        return None

    async def _handle_heartbeat(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle heartbeat message"""
        agent_id = message.payload.get("agent_id")
        health_data = message.payload.get("health_data", {})

        if agent_id:
            # Update health status
            self.health_status[agent_id] = {
                **health_data,
                "last_heartbeat": datetime.now(UTC),
                "status": "healthy",
            }

            # Add to history
            self.health_history.append(
                {
                    "agent_id": agent_id,
                    "timestamp": datetime.now(UTC),
                    "health_data": health_data,
                    "event_type": "heartbeat",
                },
            )

            # Trim history
            if len(self.health_history) > self.max_history:
                self.health_history = self.health_history[-self.max_history :]

            logger.debug(f"Received heartbeat from {agent_id}")

        return None

    async def _handle_health_check_request(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle health check request"""
        # This would be implemented by individual agents
        # Return health status
        response_msg = ProtocolMessage(
            pattern=CommunicationPattern.HEALTH_MONITORING,
            sender_id=message.receiver_id or "unknown",
            receiver_id=message.sender_id,
            correlation_id=message.correlation_id,
            payload={
                "check_type": "health_check_response",
                "agent_id": message.receiver_id,
                "health_status": self.health_status.get(message.receiver_id or "", {}),
                "responded_at": datetime.now(UTC).isoformat(),
            },
            metadata={
                "protocol": "health_monitoring",
                "action": "health_check_response",
            },
        )

        return response_msg

    async def _handle_health_check_response(
        self,
        message: ProtocolMessage,
    ) -> ProtocolMessage | None:
        """Handle health check response"""
        agent_id = message.payload.get("agent_id")
        health_status = message.payload.get("health_status", {})

        if agent_id:
            # Update health status
            self.health_status[agent_id] = {
                **health_status,
                "last_check": datetime.now(UTC),
                "status": (
                    "healthy" if health_status.get("healthy", True) else "unhealthy"
                ),
            }

            logger.debug(f"Received health check response from {agent_id}")

        return None

    async def _send_health_message(
        self,
        message_bus: MessageBus,
        message: ProtocolMessage,
    ):
        """Send health monitoring message"""
        bus_message = Message(
            type=MessageType.HEALTH_CHECK,
            priority=MessagePriority.NORMAL,
            source=message.sender_id,
            target=message.receiver_id,
            data=message.payload,
            correlation_id=message.correlation_id,
        )

        await message_bus.publish("health:checks", bus_message)

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health status"""
        total_agents = len(self.health_status)
        healthy_agents = len(
            [
                status
                for status in self.health_status.values()
                if status.get("status") == "healthy"
            ],
        )

        return {
            "overall_status": (
                "healthy" if healthy_agents == total_agents else "degraded"
            ),
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "unhealthy_agents": total_agents - healthy_agents,
            "last_updated": datetime.now(UTC).isoformat(),
            "agent_status": self.health_status.copy(),
        }


# Protocol middleware functions
async def logging_middleware(message: ProtocolMessage) -> ProtocolMessage:
    """Middleware for logging protocol messages"""
    logger.debug(
        f"Protocol message: {message.sender_id} -> {message.receiver_id} ({
            message.pattern.value
        })",
    )
    return message


async def timing_middleware(message: ProtocolMessage) -> ProtocolMessage:
    """Middleware for message timing"""
    if "timing" not in message.metadata:
        message.metadata["timing"] = {
            "received_at": datetime.now(UTC).isoformat(),
        }
    return message


async def validation_middleware(message: ProtocolMessage) -> ProtocolMessage:
    """Middleware for message validation"""
    if not message.sender_id:
        raise ValueError("Message must have sender_id")

    if not message.payload:
        logger.warning("Message has empty payload")

    return message


# Protocol factory
class ProtocolFactory:
    """Factory for creating protocol handlers"""

    @staticmethod
    def create_request_response_protocol(
        config: ProtocolConfig = None,
    ) -> RequestResponseProtocol:
        """Create request-response protocol handler"""
        protocol = RequestResponseProtocol(config)
        protocol.add_middleware(logging_middleware)
        protocol.add_middleware(timing_middleware)
        protocol.add_middleware(validation_middleware)
        return protocol

    @staticmethod
    def create_pubsub_protocol(
        config: ProtocolConfig = None,
    ) -> PublishSubscribeProtocol:
        """Create publish-subscribe protocol handler"""
        protocol = PublishSubscribeProtocol(config)
        protocol.add_middleware(logging_middleware)
        protocol.add_middleware(timing_middleware)
        return protocol

    @staticmethod
    def create_task_coordination_protocol(
        config: ProtocolConfig = None,
    ) -> TaskCoordinationProtocol:
        """Create task coordination protocol handler"""
        protocol = TaskCoordinationProtocol(config)
        protocol.add_middleware(logging_middleware)
        protocol.add_middleware(timing_middleware)
        protocol.add_middleware(validation_middleware)
        return protocol

    @staticmethod
    def create_health_monitoring_protocol(
        config: ProtocolConfig = None,
    ) -> HealthMonitoringProtocol:
        """Create health monitoring protocol handler"""
        protocol = HealthMonitoringProtocol(config)
        protocol.add_middleware(logging_middleware)
        protocol.add_middleware(timing_middleware)
        return protocol


# Protocol utilities
def create_standard_config() -> ProtocolConfig:
    """Create standard protocol configuration"""
    return ProtocolConfig(
        default_timeout=30.0,
        max_retries=3,
        retry_backoff=1.5,
        enable_compression=False,
        enable_encryption=False,
        message_ordering=True,
        duplicate_detection=True,
        dead_letter_handling=True,
    )


def create_high_performance_config() -> ProtocolConfig:
    """Create high-performance protocol configuration"""
    return ProtocolConfig(
        default_timeout=10.0,
        max_retries=2,
        retry_backoff=1.2,
        enable_compression=True,
        enable_encryption=False,
        message_ordering=False,
        duplicate_detection=False,
        dead_letter_handling=True,
    )


def create_secure_config() -> ProtocolConfig:
    """Create secure protocol configuration"""
    return ProtocolConfig(
        default_timeout=45.0,
        max_retries=3,
        retry_backoff=2.0,
        enable_compression=True,
        enable_encryption=True,
        message_ordering=True,
        duplicate_detection=True,
        dead_letter_handling=True,
    )
