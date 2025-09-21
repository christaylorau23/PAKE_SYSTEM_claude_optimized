#!/usr/bin/env python3
"""PAKE System - Supervisor Agent
Event-driven orchestration agent for hierarchical architecture.

Replaces the monolithic orchestrator with event-driven supervision of:
- Worker agents (AI services)
- Task distribution and coordination
- System-wide monitoring and health
- Cognitive processing coordination
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from scripts.ingestion_pipeline import ContentItem

from ..ingestion.orchestrator import IngestionConfig, IngestionPlan, IngestionResult
from ..messaging.message_bus import (
    Message,
    MessageBus,
    MessagePriority,
    create_response_message,
    create_system_event,
    create_task_message,
)

# Configure logging
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class WorkerType(Enum):
    """Types of worker agents"""

    WEB_SCRAPER = "web_scraper"
    ARXIV_SERVICE = "arxiv_service"
    PUBMED_SERVICE = "pubmed_service"
    COGNITIVE_ENGINE = "cognitive_engine"
    PERFORMANCE_OPTIMIZER = "performance_optimizer"


@dataclass
class Task:
    """Task representation for supervisor-worker coordination"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    data: dict[str, Any] = field(default_factory=dict)
    assigned_worker: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    assigned_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 300.0  # 5 minutes default


@dataclass
class WorkerAgent:
    """Worker agent registration and status"""

    id: str
    type: WorkerType
    status: str = "idle"
    last_heartbeat: datetime | None = None
    current_task: str | None = None
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_task_time: float = 0.0
    capabilities: list[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1


class SupervisorAgent:
    """Event-driven supervisor agent for hierarchical architecture.

    Coordinates worker agents through Redis Streams messaging:
    - Task distribution and load balancing
    - Health monitoring and recovery
    - System-wide event coordination
    - Performance optimization
    """

    def __init__(
        self,
        message_bus: MessageBus,
        config: IngestionConfig,
        agent_id: str = None,
    ):
        """Initialize supervisor agent"""
        self.agent_id = agent_id or f"supervisor_{uuid.uuid4().hex[:8]}"
        self.message_bus = message_bus
        self.config = config

        # Task management
        self.active_tasks: dict[str, Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.completed_tasks: list[Task] = []

        # Worker management
        self.registered_workers: dict[str, WorkerAgent] = {}
        self.worker_capabilities: dict[WorkerType, list[str]] = {
            WorkerType.WEB_SCRAPER: ["web_scraping", "javascript_rendering"],
            WorkerType.ARXIV_SERVICE: ["academic_search", "arxiv_api"],
            WorkerType.PUBMED_SERVICE: ["biomedical_search", "pubmed_api"],
            WorkerType.COGNITIVE_ENGINE: ["quality_assessment", "content_analysis"],
            WorkerType.PERFORMANCE_OPTIMIZER: ["caching", "performance_metrics"],
        }

        # Execution metrics
        self.metrics = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "workers_active": 0,
            "average_task_completion_time": 0.0,
            "system_uptime": time.time(),
        }

        # Running state
        self._running = False
        self._background_tasks: list[asyncio.Task] = []

        logger.info(f"SupervisorAgent {self.agent_id} initialized")

    async def start(self):
        """Start supervisor agent and initialize messaging"""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting SupervisorAgent {self.agent_id}...")

        # Subscribe to core message streams
        await self._setup_message_handlers()

        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._task_dispatcher()),
            asyncio.create_task(self._health_monitor()),
            asyncio.create_task(self._metrics_collector()),
            asyncio.create_task(self._task_timeout_monitor()),
        ]

        # Send startup event
        startup_event = create_system_event(
            source=self.agent_id,
            event_type="supervisor_started",
            event_data={
                "agent_id": self.agent_id,
                "config": {
                    "max_concurrent_sources": self.config.max_concurrent_sources,
                    "cognitive_processing": self.config.enable_cognitive_processing,
                },
            },
            priority=MessagePriority.HIGH,
        )

        await self.message_bus.publish("system:events", startup_event)
        logger.info(f"SupervisorAgent {self.agent_id} started successfully")

    async def stop(self):
        """Stop supervisor agent and cleanup resources"""
        if not self._running:
            return

        self._running = False
        logger.info(f"Stopping SupervisorAgent {self.agent_id}...")

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Send shutdown event
        shutdown_event = create_system_event(
            source=self.agent_id,
            event_type="supervisor_shutdown",
            event_data={
                "agent_id": self.agent_id,
                "final_metrics": self.metrics.copy(),
            },
            priority=MessagePriority.HIGH,
        )

        await self.message_bus.publish("system:events", shutdown_event)
        logger.info(f"SupervisorAgent {self.agent_id} stopped")

    async def execute_ingestion_plan(self, plan: IngestionPlan) -> IngestionResult:
        """Execute ingestion plan using event-driven worker coordination.

        Transforms the original orchestrator workflow into distributed tasks.
        """
        logger.info(f"Executing ingestion plan {plan.plan_id} for topic: {plan.topic}")
        start_time = time.time()

        # Create tasks for each source
        tasks = []
        for source in plan.sources:
            task = Task(
                type=f"{source.source_type}_ingestion",
                priority=(
                    MessagePriority.NORMAL
                    if source.priority > 2
                    else MessagePriority.HIGH
                ),
                data={
                    "source": source.__dict__,
                    "plan_context": {
                        "topic": plan.topic,
                        "plan_id": plan.plan_id,
                        "cognitive_processing": self.config.enable_cognitive_processing,
                    },
                },
                timeout=source.timeout,
            )
            tasks.append(task)

        # Execute tasks through event-driven coordination
        results = await self._execute_tasks_parallel(tasks)

        # Aggregate results
        all_content_items = []
        error_details = []
        sources_completed = 0
        sources_failed = 0

        for task, result in zip(tasks, results, strict=False):
            if task.status == TaskStatus.COMPLETED:
                sources_completed += 1
                if result and isinstance(result, list):
                    all_content_items.extend(result)
            else:
                sources_failed += 1
                error_details.append(
                    {
                        "task_id": task.id,
                        "source_type": task.type,
                        "error": task.error or "Unknown error",
                    },
                )

        # Apply post-processing through worker agents
        if self.config.enable_cognitive_processing:
            await self._apply_cognitive_processing(all_content_items, plan)

        if plan.enable_deduplication:
            all_content_items = await self._apply_deduplication(all_content_items)

        # Create comprehensive result
        execution_time = time.time() - start_time

        result = IngestionResult(
            success=sources_completed > 0,
            plan_id=plan.plan_id,
            content_items=all_content_items,
            total_content_items=len(all_content_items),
            sources_attempted=len(plan.sources),
            sources_completed=sources_completed,
            sources_failed=sources_failed,
            execution_time=execution_time,
            error_details=error_details,
            metrics=self._calculate_execution_metrics(
                all_content_items,
                execution_time,
            ),
        )

        # Update supervisor metrics
        self.metrics["tasks_completed"] += len(tasks)
        if sources_failed > 0:
            self.metrics["tasks_failed"] += sources_failed

        logger.info(
            f"Completed ingestion plan {plan.plan_id}: "
            f"{result.total_content_items} items from {sources_completed}/{
                len(plan.sources)
            } sources "
            f"in {execution_time:.2f}s",
        )

        return result

    async def register_worker(self, worker_agent: WorkerAgent):
        """Register worker agent with supervisor"""
        self.registered_workers[worker_agent.id] = worker_agent
        self.metrics["workers_active"] = len(self.registered_workers)

        # Send registration confirmation
        confirmation = create_system_event(
            source=self.agent_id,
            event_type="worker_registered",
            event_data={
                "worker_id": worker_agent.id,
                "worker_type": worker_agent.type.value,
                "capabilities": worker_agent.capabilities,
            },
        )

        await self.message_bus.publish("system:events", confirmation)
        logger.info(f"Registered worker {worker_agent.id} ({worker_agent.type.value})")

    async def unregister_worker(self, worker_id: str):
        """Unregister worker agent"""
        if worker_id in self.registered_workers:
            worker = self.registered_workers.pop(worker_id)
            self.metrics["workers_active"] = len(self.registered_workers)

            # Handle any active tasks from this worker
            for task in self.active_tasks.values():
                if task.assigned_worker == worker_id:
                    task.status = TaskStatus.FAILED
                    task.error = "Worker disconnected"
                    await self._reschedule_task(task)

            logger.info(f"Unregistered worker {worker_id}")

    async def get_metrics(self) -> dict[str, Any]:
        """Get supervisor agent metrics"""
        metrics = self.metrics.copy()
        metrics.update(
            {
                "active_tasks": len(self.active_tasks),
                "queued_tasks": self.task_queue.qsize(),
                "registered_workers": len(self.registered_workers),
                "worker_breakdown": {
                    worker_type.value: len(
                        [
                            w
                            for w in self.registered_workers.values()
                            if w.type == worker_type
                        ],
                    )
                    for worker_type in WorkerType
                },
                "uptime": time.time() - self.metrics["system_uptime"],
            },
        )

        return metrics

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check"""
        health = {
            "status": "healthy",
            "supervisor_id": self.agent_id,
            "running": self._running,
            "message_bus_health": await self.message_bus.health_check(),
            "metrics": await self.get_metrics(),
            "workers": {},
        }

        # Check worker health
        current_time = datetime.now(UTC)
        for worker_id, worker in self.registered_workers.items():
            worker_healthy = True
            if worker.last_heartbeat:
                time_since_heartbeat = (
                    current_time - worker.last_heartbeat
                ).total_seconds()
                worker_healthy = time_since_heartbeat < 60  # 1 minute timeout

            health["workers"][worker_id] = {
                "type": worker.type.value,
                "status": worker.status,
                "healthy": worker_healthy,
                "tasks_completed": worker.total_tasks_completed,
                "tasks_failed": worker.total_tasks_failed,
            }

        # Overall health status
        unhealthy_workers = sum(
            1 for w in health["workers"].values() if not w["healthy"]
        )
        if unhealthy_workers > 0:
            health["status"] = "degraded"
            health["unhealthy_workers"] = unhealthy_workers

        if not health["message_bus_health"]["redis_connected"]:
            health["status"] = "unhealthy"
            health["error"] = "Redis connection failed"

        return health

    async def _setup_message_handlers(self):
        """Setup message stream handlers"""
        # Task responses from workers
        await self.message_bus.subscribe(
            "supervisor:responses",
            self._handle_task_response,
            consumer_name=f"supervisor_{self.agent_id}",
        )

        # System events
        await self.message_bus.subscribe(
            "system:events",
            self._handle_system_event,
            consumer_name=f"supervisor_{self.agent_id}",
        )

        # Health check requests
        await self.message_bus.subscribe(
            "health:checks",
            self._handle_health_check,
            consumer_name=f"supervisor_{self.agent_id}",
        )

        logger.info("Message handlers setup complete")

    async def _execute_tasks_parallel(self, tasks: list[Task]) -> list[Any]:
        """Execute multiple tasks in parallel through worker coordination"""
        # Add tasks to active tracking
        for task in tasks:
            self.active_tasks[task.id] = task
            await self.task_queue.put(task)
            self.metrics["tasks_created"] += 1

        # Wait for all tasks to complete
        completion_futures = {}
        for task in tasks:
            future = asyncio.Future()
            completion_futures[task.id] = future

        # Monitor task completion
        async def completion_monitor():
            while completion_futures:
                completed_tasks = []
                for task_id, future in completion_futures.items():
                    if task_id in self.active_tasks:
                        task = self.active_tasks[task_id]
                        if task.status in [
                            TaskStatus.COMPLETED,
                            TaskStatus.FAILED,
                            TaskStatus.TIMEOUT,
                        ]:
                            future.set_result(task.result)
                            completed_tasks.append(task_id)

                for task_id in completed_tasks:
                    completion_futures.pop(task_id)

                if completion_futures:
                    await asyncio.sleep(0.1)

        # Start completion monitor
        monitor_task = asyncio.create_task(completion_monitor())

        try:
            # Wait for all tasks with timeout
            await asyncio.wait_for(
                asyncio.gather(*completion_futures.values()),
                timeout=max(task.timeout for task in tasks) + 30,
            )
        except TimeoutError:
            logger.warning("Task execution timeout reached")
        finally:
            monitor_task.cancel()

        # Collect results
        results = []
        for task in tasks:
            if task.id in self.active_tasks:
                results.append(self.active_tasks[task.id].result)
                # Move to completed tasks
                self.completed_tasks.append(self.active_tasks.pop(task.id))
            else:
                results.append(None)

        return results

    async def _task_dispatcher(self):
        """Background task dispatcher for worker coordination"""
        logger.info("Task dispatcher started")

        while self._running:
            try:
                # Get task from queue
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                # Find available worker
                worker = await self._find_available_worker(task)
                if not worker:
                    # No worker available, requeue task
                    await asyncio.sleep(0.5)
                    await self.task_queue.put(task)
                    continue

                # Assign task to worker
                await self._assign_task_to_worker(task, worker)

            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task dispatcher error: {e}")
                await asyncio.sleep(1)

        logger.info("Task dispatcher stopped")

    async def _find_available_worker(self, task: Task) -> WorkerAgent | None:
        """Find available worker for task type"""
        # Map task types to worker types
        task_worker_mapping = {
            "web_ingestion": WorkerType.WEB_SCRAPER,
            "arxiv_ingestion": WorkerType.ARXIV_SERVICE,
            "pubmed_ingestion": WorkerType.PUBMED_SERVICE,
            "cognitive_assessment": WorkerType.COGNITIVE_ENGINE,
            "performance_optimization": WorkerType.PERFORMANCE_OPTIMIZER,
        }

        required_worker_type = task_worker_mapping.get(task.type)
        if not required_worker_type:
            return None

        # Find idle workers of correct type
        available_workers = [
            worker
            for worker in self.registered_workers.values()
            if (
                worker.type == required_worker_type
                and worker.status == "idle"
                and worker.current_task is None
            )
        ]

        if not available_workers:
            return None

        # Return worker with best performance
        return min(available_workers, key=lambda w: w.total_tasks_failed)

    async def _assign_task_to_worker(self, task: Task, worker: WorkerAgent):
        """Assign task to specific worker"""
        task.assigned_worker = worker.id
        task.assigned_at = datetime.now(UTC)
        task.status = TaskStatus.ASSIGNED

        worker.current_task = task.id
        worker.status = "busy"

        # Send task message to worker
        task_message = create_task_message(
            source=self.agent_id,
            target=worker.id,
            task_type=task.type,
            task_data=task.data,
            priority=task.priority,
        )
        task_message.correlation_id = task.id

        await self.message_bus.publish("supervisor:tasks", task_message)

        logger.debug(f"Assigned task {task.id} to worker {worker.id}")

    async def _handle_task_response(self, message: Message):
        """Handle task response from worker"""
        task_id = message.correlation_id
        if not task_id or task_id not in self.active_tasks:
            return

        task = self.active_tasks[task_id]

        # Update task status
        response_data = message.data
        if response_data.get("success", False):
            task.status = TaskStatus.COMPLETED
            task.result = response_data.get("result")
        else:
            task.status = TaskStatus.FAILED
            task.error = response_data.get("error", "Unknown error")

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                await self.task_queue.put(task)
                return

        task.completed_at = datetime.now(UTC)

        # Update worker status
        if task.assigned_worker and task.assigned_worker in self.registered_workers:
            worker = self.registered_workers[task.assigned_worker]
            worker.current_task = None
            worker.status = "idle"

            if task.status == TaskStatus.COMPLETED:
                worker.total_tasks_completed += 1
            else:
                worker.total_tasks_failed += 1

        logger.debug(f"Task {task_id} completed with status {task.status}")

    async def _handle_system_event(self, message: Message):
        """Handle system-wide events"""
        event_data = message.data
        event_type = event_data.get("event_type")

        if event_type == "worker_heartbeat":
            await self._handle_worker_heartbeat(message)
        elif event_type == "worker_registration":
            await self._handle_worker_registration(message)
        elif event_type == "worker_shutdown":
            await self._handle_worker_shutdown(message)

        logger.debug(f"Processed system event: {event_type}")

    async def _handle_worker_heartbeat(self, message: Message):
        """Handle worker heartbeat"""
        worker_id = message.source
        if worker_id in self.registered_workers:
            worker = self.registered_workers[worker_id]
            worker.last_heartbeat = datetime.now(UTC)

            # Update worker status from heartbeat data
            heartbeat_data = message.data.get("event_data", {})
            if "status" in heartbeat_data:
                worker.status = heartbeat_data["status"]

    async def _handle_worker_registration(self, message: Message):
        """Handle new worker registration"""
        event_data = message.data.get("event_data", {})
        worker_type = event_data.get("worker_type")
        worker_id = message.source

        if worker_type and worker_id:
            try:
                worker_type_enum = WorkerType(worker_type)
                worker = WorkerAgent(
                    id=worker_id,
                    type=worker_type_enum,
                    capabilities=self.worker_capabilities.get(worker_type_enum, []),
                    last_heartbeat=datetime.now(UTC),
                )
                await self.register_worker(worker)
            except ValueError:
                logger.warning(f"Unknown worker type: {worker_type}")

    async def _handle_worker_shutdown(self, message: Message):
        """Handle worker shutdown"""
        worker_id = message.source
        await self.unregister_worker(worker_id)

    async def _handle_health_check(self, message: Message):
        """Handle health check request"""
        health = await self.health_check()

        response = create_response_message(
            source=self.agent_id,
            target=message.source,
            result=health,
            success=True,
        )

        await self.message_bus.send_response(
            "health:checks:responses",
            response,
            message,
        )

    async def _health_monitor(self):
        """Background health monitoring"""
        logger.info("Health monitor started")

        while self._running:
            try:
                # Check worker health
                current_time = datetime.now(UTC)

                for worker_id, worker in list(self.registered_workers.items()):
                    if worker.last_heartbeat:
                        time_since_heartbeat = (
                            current_time - worker.last_heartbeat
                        ).total_seconds()
                        if time_since_heartbeat > 120:  # 2 minute timeout
                            logger.warning(f"Worker {worker_id} health check timeout")
                            await self.unregister_worker(worker_id)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)

        logger.info("Health monitor stopped")

    async def _metrics_collector(self):
        """Background metrics collection"""
        logger.info("Metrics collector started")

        while self._running:
            try:
                # Update average task completion time
                if self.completed_tasks:
                    total_time = sum(
                        (task.completed_at - task.created_at).total_seconds()
                        for task in self.completed_tasks[-100:]  # Last 100 tasks
                        if task.completed_at and task.created_at
                    )
                    self.metrics["average_task_completion_time"] = total_time / min(
                        len(self.completed_tasks),
                        100,
                    )

                # Publish metrics
                metrics_event = create_system_event(
                    source=self.agent_id,
                    event_type="supervisor_metrics",
                    event_data=await self.get_metrics(),
                )

                await self.message_bus.publish("system:events", metrics_event)

                await asyncio.sleep(60)  # Publish every minute

            except Exception as e:
                logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(5)

        logger.info("Metrics collector stopped")

    async def _task_timeout_monitor(self):
        """Monitor and handle task timeouts"""
        logger.info("Task timeout monitor started")

        while self._running:
            try:
                current_time = datetime.now(UTC)
                timed_out_tasks = []

                for task in self.active_tasks.values():
                    if (
                        task.assigned_at
                        and (current_time - task.assigned_at).total_seconds()
                        > task.timeout
                    ):
                        timed_out_tasks.append(task)

                for task in timed_out_tasks:
                    logger.warning(f"Task {task.id} timed out")
                    task.status = TaskStatus.TIMEOUT
                    task.error = "Task execution timeout"

                    # Free up worker
                    if (
                        task.assigned_worker
                        and task.assigned_worker in self.registered_workers
                    ):
                        worker = self.registered_workers[task.assigned_worker]
                        worker.current_task = None
                        worker.status = "idle"
                        worker.total_tasks_failed += 1

                    # Retry if possible
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.status = TaskStatus.PENDING
                        task.assigned_worker = None
                        task.assigned_at = None
                        await self.task_queue.put(task)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Task timeout monitor error: {e}")
                await asyncio.sleep(5)

        logger.info("Task timeout monitor stopped")

    async def _apply_cognitive_processing(
        self,
        content_items: list[ContentItem],
        plan: IngestionPlan,
    ):
        """Apply cognitive processing through worker agents"""
        if not content_items:
            return

        # Create cognitive assessment task
        cognitive_task = Task(
            type="cognitive_assessment",
            priority=MessagePriority.NORMAL,
            data={
                "content_items": [item.__dict__ for item in content_items],
                "assessment_type": "quality_and_relevance",
                "context": {"topic": plan.topic},
            },
            timeout=120.0,
        )

        # Execute through worker coordination
        results = await self._execute_tasks_parallel([cognitive_task])

        if results and results[0]:
            # Apply assessment results to content items
            assessments = results[0]
            for i, item in enumerate(content_items):
                if i < len(assessments) and hasattr(item, "metadata"):
                    if not item.metadata:
                        item.metadata = {}
                    item.metadata.update(assessments[i])

    async def _apply_deduplication(
        self,
        content_items: list[ContentItem],
    ) -> list[ContentItem]:
        """Apply deduplication through performance optimizer worker"""
        if not content_items:
            return content_items

        # Create deduplication task
        dedup_task = Task(
            type="performance_optimization",
            data={
                "operation": "deduplication",
                "content_items": [item.__dict__ for item in content_items],
            },
            timeout=60.0,
        )

        # Execute through worker coordination
        results = await self._execute_tasks_parallel([dedup_task])

        if results and results[0]:
            # Reconstruct ContentItem objects
            deduplicated_data = results[0]
            return [ContentItem(**item_data) for item_data in deduplicated_data]

        return content_items

    async def _reschedule_task(self, task: Task):
        """Reschedule failed task for retry"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.assigned_worker = None
            task.assigned_at = None
            await self.task_queue.put(task)
            logger.info(
                f"Rescheduled task {task.id} for retry ({task.retry_count}/{
                    task.max_retries
                })",
            )

    def _calculate_execution_metrics(
        self,
        content_items: list[ContentItem],
        execution_time: float,
    ) -> dict[str, Any]:
        """Calculate execution metrics for ingestion result"""
        return {
            "supervisor_execution_time": execution_time,
            "total_content_items": len(content_items),
            "content_diversity": len(set(item.source_type for item in content_items)),
            "average_content_length": sum(
                len(item.content or "") for item in content_items
            )
            / max(len(content_items), 1),
            "unique_sources": len(set(item.source_name for item in content_items)),
        }
