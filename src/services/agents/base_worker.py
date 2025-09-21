#!/usr/bin/env python3
"""PAKE System - Base Worker Agent
Foundation class for stateless worker agents in hierarchical architecture.

Provides common functionality for:
- Message-based communication with Supervisor
- Health monitoring and heartbeat
- Task execution patterns
- Error handling and recovery
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ..messaging.message_bus import (
    Message,
    MessageBus,
    MessagePriority,
    create_response_message,
    create_system_event,
)

# Configure logging
logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    """Worker agent status"""

    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class WorkerCapability:
    """Capability definition for worker agent"""

    name: str
    description: str
    input_types: list[str]
    output_types: list[str]
    performance_metrics: dict[str, Any]


class BaseWorkerAgent(ABC):
    """Abstract base class for stateless worker agents.

    Implements common patterns for:
    - Event-driven communication
    - Health monitoring
    - Task lifecycle management
    - Performance tracking
    """

    def __init__(
        self,
        worker_type: str,
        message_bus: MessageBus,
        capabilities: list[WorkerCapability] = None,
        worker_id: str = None,
    ):
        """Initialize base worker agent"""
        self.worker_id = worker_id or f"{worker_type}_{uuid.uuid4().hex[:8]}"
        self.worker_type = worker_type
        self.message_bus = message_bus
        self.capabilities = capabilities or []

        # Worker state
        self.status = WorkerStatus.INITIALIZING
        self.current_task_id: str | None = None
        self.last_heartbeat = datetime.now(UTC)

        # Performance metrics
        self.metrics = {
            "tasks_processed": 0,
            "tasks_successful": 0,
            "tasks_failed": 0,
            "average_task_time": 0.0,
            "total_processing_time": 0.0,
            "uptime": time.time(),
            "error_rate": 0.0,
        }

        # Configuration
        self.heartbeat_interval = 30.0  # seconds
        self.max_task_timeout = 300.0  # 5 minutes

        # Running state
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None

        logger.info(f"BaseWorkerAgent {self.worker_id} ({worker_type}) initialized")

    async def start(self):
        """Start worker agent"""
        if self._running:
            return

        self._running = True
        self.status = WorkerStatus.IDLE

        logger.info(f"Starting worker {self.worker_id}...")

        # Subscribe to task messages
        await self.message_bus.subscribe(
            "supervisor:tasks",
            self._handle_task_message,
            consumer_name=self.worker_id,
        )

        # Subscribe to system events
        await self.message_bus.subscribe(
            "system:events",
            self._handle_system_event,
            consumer_name=self.worker_id,
        )

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Send registration event
        await self._send_registration()

        # Call subclass initialization
        await self._on_start()

        logger.info(f"Worker {self.worker_id} started successfully")

    async def stop(self):
        """Stop worker agent"""
        if not self._running:
            return

        self._running = False
        self.status = WorkerStatus.SHUTTING_DOWN

        logger.info(f"Stopping worker {self.worker_id}...")

        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Send shutdown event
        shutdown_event = create_system_event(
            source=self.worker_id,
            event_type="worker_shutdown",
            event_data={
                "worker_type": self.worker_type,
                "final_metrics": self.metrics.copy(),
            },
            priority=MessagePriority.HIGH,
        )

        await self.message_bus.publish("system:events", shutdown_event)

        # Call subclass cleanup
        await self._on_stop()

        logger.info(f"Worker {self.worker_id} stopped")

    async def get_health_status(self) -> dict[str, Any]:
        """Get worker health status"""
        return {
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "status": self.status.value,
            "current_task": self.current_task_id,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "uptime": time.time() - self.metrics["uptime"],
            "capabilities": [cap.name for cap in self.capabilities],
            "metrics": self.metrics.copy(),
            "healthy": self.status
            not in [WorkerStatus.ERROR, WorkerStatus.SHUTTING_DOWN],
        }

    @abstractmethod
    async def process_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process task data and return result.

        Must be implemented by subclasses to handle specific task types.

        Args:
            task_data: Task data from supervisor

        Returns:
            Dict containing:
                - success: bool
                - result: Any (task result)
                - error: str (error message if failed)
                - metrics: Dict (performance metrics)
        """

    async def _on_start(self):
        """Override in subclasses for custom startup logic"""

    async def _on_stop(self):
        """Override in subclasses for custom shutdown logic"""

    async def _handle_task_message(self, message: Message):
        """Handle task message from supervisor"""
        if message.target != self.worker_id:
            return  # Not for this worker

        if self.status != WorkerStatus.IDLE:
            # Worker is busy, send busy response
            busy_response = create_response_message(
                source=self.worker_id,
                target=message.source,
                result=None,
                success=False,
                error="Worker is busy",
            )
            busy_response.correlation_id = message.correlation_id

            await self.message_bus.publish("supervisor:responses", busy_response)
            return

        # Process task
        await self._execute_task(message)

    async def _execute_task(self, message: Message):
        """Execute task with error handling and metrics"""
        task_id = message.correlation_id
        self.current_task_id = task_id
        self.status = WorkerStatus.BUSY

        start_time = time.time()

        try:
            logger.info(f"Worker {self.worker_id} executing task {task_id}")

            # Process task through subclass implementation
            result = await asyncio.wait_for(
                self.process_task(message.data),
                timeout=self.max_task_timeout,
            )

            # Send success response
            response = create_response_message(
                source=self.worker_id,
                target=message.source,
                result=result.get("result"),
                success=result.get("success", True),
                error=result.get("error"),
            )
            response.correlation_id = task_id

            await self.message_bus.publish("supervisor:responses", response)

            # Update metrics
            execution_time = time.time() - start_time
            self._update_success_metrics(execution_time)

            logger.info(
                f"Worker {self.worker_id} completed task {task_id} in {
                    execution_time:.2f}s",
            )

        except TimeoutError:
            # Task timeout
            error_msg = f"Task {task_id} timed out after {self.max_task_timeout}s"
            logger.error(error_msg)

            response = create_response_message(
                source=self.worker_id,
                target=message.source,
                result=None,
                success=False,
                error=error_msg,
            )
            response.correlation_id = task_id

            await self.message_bus.publish("supervisor:responses", response)
            self._update_failure_metrics(time.time() - start_time, "timeout")

        except Exception as e:
            # Task execution error
            error_msg = f"Task execution failed: {str(e)}"
            logger.error(f"Worker {self.worker_id} task {task_id} failed: {e}")

            response = create_response_message(
                source=self.worker_id,
                target=message.source,
                result=None,
                success=False,
                error=error_msg,
            )
            response.correlation_id = task_id

            await self.message_bus.publish("supervisor:responses", response)
            self._update_failure_metrics(time.time() - start_time, "error")

        finally:
            # Reset worker state
            self.current_task_id = None
            self.status = WorkerStatus.IDLE

    async def _handle_system_event(self, message: Message):
        """Handle system events"""
        event_data = message.data
        event_type = event_data.get("event_type")

        if event_type == "health_check_request":
            await self._handle_health_check_request(message)
        elif event_type == "shutdown_request":
            await self.stop()

    async def _handle_health_check_request(self, message: Message):
        """Handle health check request"""
        health_status = await self.get_health_status()

        response = create_response_message(
            source=self.worker_id,
            target=message.source,
            result=health_status,
            success=True,
        )

        await self.message_bus.publish("health:checks:responses", response)

    async def _send_registration(self):
        """Send worker registration event"""
        registration_event = create_system_event(
            source=self.worker_id,
            event_type="worker_registration",
            event_data={
                "worker_type": self.worker_type,
                "capabilities": [cap.name for cap in self.capabilities],
                "max_concurrent_tasks": 1,  # Stateless workers process one task at a time
                "performance_profile": {
                    "average_task_time": self.metrics["average_task_time"],
                    "error_rate": self.metrics["error_rate"],
                },
            },
            priority=MessagePriority.HIGH,
        )

        await self.message_bus.publish("system:events", registration_event)

    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        logger.info(f"Worker {self.worker_id} heartbeat started")

        while self._running:
            try:
                self.last_heartbeat = datetime.now(UTC)

                heartbeat_event = create_system_event(
                    source=self.worker_id,
                    event_type="worker_heartbeat",
                    event_data={
                        "status": self.status.value,
                        "current_task": self.current_task_id,
                        "metrics": self.metrics.copy(),
                        "timestamp": self.last_heartbeat.isoformat(),
                    },
                )

                await self.message_bus.publish("system:events", heartbeat_event)

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error for worker {self.worker_id}: {e}")
                await asyncio.sleep(5)

        logger.info(f"Worker {self.worker_id} heartbeat stopped")

    def _update_success_metrics(self, execution_time: float):
        """Update metrics for successful task"""
        self.metrics["tasks_processed"] += 1
        self.metrics["tasks_successful"] += 1
        self.metrics["total_processing_time"] += execution_time

        # Update average task time
        self.metrics["average_task_time"] = (
            self.metrics["total_processing_time"] / self.metrics["tasks_processed"]
        )

        # Update error rate
        self.metrics["error_rate"] = (
            self.metrics["tasks_failed"] / self.metrics["tasks_processed"]
        )

    def _update_failure_metrics(self, execution_time: float, failure_type: str):
        """Update metrics for failed task"""
        self.metrics["tasks_processed"] += 1
        self.metrics["tasks_failed"] += 1
        self.metrics["total_processing_time"] += execution_time

        # Update average task time
        self.metrics["average_task_time"] = (
            self.metrics["total_processing_time"] / self.metrics["tasks_processed"]
        )

        # Update error rate
        self.metrics["error_rate"] = (
            self.metrics["tasks_failed"] / self.metrics["tasks_processed"]
        )

        # Log failure type
        if "failure_types" not in self.metrics:
            self.metrics["failure_types"] = {}

        if failure_type not in self.metrics["failure_types"]:
            self.metrics["failure_types"][failure_type] = 0

        self.metrics["failure_types"][failure_type] += 1


class WorkerCapabilityBuilder:
    """Builder for creating worker capabilities"""

    def __init__(self, name: str):
        self.name = name
        self.description = ""
        self.input_types = []
        self.output_types = []
        self.performance_metrics = {}

    def with_description(self, description: str):
        """Add capability description"""
        self.description = description
        return self

    def with_input_types(self, *input_types: str):
        """Add input types"""
        self.input_types.extend(input_types)
        return self

    def with_output_types(self, *output_types: str):
        """Add output types"""
        self.output_types.extend(output_types)
        return self

    def with_performance_metrics(self, **metrics):
        """Add performance metrics"""
        self.performance_metrics.update(metrics)
        return self

    def build(self) -> WorkerCapability:
        """Build capability"""
        return WorkerCapability(
            name=self.name,
            description=self.description,
            input_types=self.input_types,
            output_types=self.output_types,
            performance_metrics=self.performance_metrics,
        )
