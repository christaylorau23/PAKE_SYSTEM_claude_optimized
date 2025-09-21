#!/usr/bin/env python3
"""PAKE+ Async Task Queue System
High-performance async task processing with Celery, Redis, and foundation integration
"""

import asyncio
import functools
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis
from celery import Celery
from celery.result import AsyncResult
from kombu import Exchange, Queue

from utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    with_circuit_breaker,
)
from utils.distributed_cache import CacheConfig, DistributedCache
from utils.error_handling import (
    ErrorCategory,
    ErrorHandler,
    PAKEException,
    with_error_handling,
)
from utils.logger import get_logger
from utils.metrics import MetricsStore

logger = get_logger(service_name="pake-async-tasks")
metrics = MetricsStore(service_name="pake-async-tasks")


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class TaskConfig:
    """Task configuration with retry and timeout settings"""

    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: bool = True
    retry_jitter: bool = True
    timeout: float = 300.0  # 5 minutes
    soft_timeout: float = 240.0  # 4 minutes
    priority: TaskPriority = TaskPriority.NORMAL
    rate_limit: str | None = None  # e.g., "10/m" for 10 per minute
    queue_name: str = "default"


@dataclass
class TaskResult:
    """Task execution result with metadata"""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: float | None = None
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskQueueError(PAKEException):
    """Task queue-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SYSTEM, **kwargs)


class AsyncTaskQueue:
    """High-performance async task queue with Redis backend and Celery integration
    Includes circuit breaker protection, retry mechanisms, and comprehensive monitoring
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        broker_url: str | None = None,
        result_backend: str | None = None,
        app_name: str = "pake_tasks",
    ):
        self.redis_url = redis_url
        self.broker_url = broker_url or redis_url
        self.result_backend = result_backend or redis_url
        self.app_name = app_name

        self.logger = get_logger(service_name="async-task-queue")
        self.metrics = MetricsStore(service_name="async-task-queue")
        self.error_handler = ErrorHandler(service_name="async-task-queue")

        # Initialize Celery app
        self.celery_app = self._create_celery_app()

        # Initialize Redis connection for direct operations
        self.redis_client: redis.Redis | None = None

        # Task registry for tracking
        self.task_registry: dict[str, Callable] = {}

        # Circuit breakers for different operations

        task_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            enable_metrics=True,
        )
        self.task_breaker = CircuitBreaker("task_execution", task_config)

        redis_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            enable_metrics=True,
        )
        self.redis_breaker = CircuitBreaker("redis_connection", redis_config)

        # Cache for task results
        cache_config = CacheConfig(
            host="localhost",
            port=6379,
            REDACTED_SECRET=None,  # Will be updated from Redis URL
            default_ttl=3600,
        )
        self.cache = DistributedCache(cache_config)

    def _create_celery_app(self) -> Celery:
        """Create and configure Celery application"""
        app = Celery(self.app_name)

        app.conf.update(
            # Broker and backend configuration
            broker_url=self.broker_url,
            result_backend=self.result_backend,
            # Serialization
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            # Task execution
            task_always_eager=False,
            task_eager_propagates=True,
            task_ignore_result=False,
            task_track_started=True,
            # Worker configuration
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
            worker_disable_rate_limits=False,
            # Result configuration
            result_expires=3600,  # 1 hour
            result_cache_max=10000,
            # Routing
            task_default_queue="default",
            task_default_exchange="tasks",
            task_default_exchange_type="direct",
            task_default_routing_key="default",
            # Queue configuration
            task_queues=(
                Queue("default", Exchange("tasks"), routing_key="default"),
                Queue("high_priority", Exchange("tasks"), routing_key="high_priority"),
                Queue("low_priority", Exchange("tasks"), routing_key="low_priority"),
                Queue("ai_processing", Exchange("tasks"), routing_key="ai_processing"),
                Queue(
                    "data_processing",
                    Exchange("tasks"),
                    routing_key="data_processing",
                ),
            ),
            # Monitoring
            worker_send_task_events=True,
            task_send_sent_event=True,
            # Error handling
            task_reject_on_worker_lost=True,
            task_acks_late=True,
            # Security
            worker_hijack_root_logger=False,
            worker_log_color=False,
        )

        return app

    @with_circuit_breaker("redis_connection")
    async def connect(self) -> None:
        """Initialize Redis connection and cache"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            await self.cache.connect()

            self.logger.info("Connected to Redis and initialized task queue")
            self.metrics.increment_counter(
                "task_queue_connections",
                labels={"status": "success"},
            )

        except Exception as e:
            self.metrics.increment_counter(
                "task_queue_connections",
                labels={"status": "error"},
            )
            raise TaskQueueError(
                f"Failed to connect to Redis: {str(e)}",
                original_exception=e,
            )

    async def disconnect(self) -> None:
        """Close Redis connections"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            await self.cache.disconnect()
            self.logger.info("Disconnected from task queue")
        except Exception as e:
            self.logger.error("Error disconnecting from task queue", error=e)

    def task(self, config: TaskConfig | None = None, name: str | None = None):
        """Decorator to register async functions as Celery tasks"""

        def decorator(func: Callable) -> Callable:
            task_config = config or TaskConfig()
            task_name = name or f"{func.__module__}.{func.__name__}"

            # Create Celery task
            celery_task = self.celery_app.task(
                bind=True,
                name=task_name,
                max_retries=task_config.max_retries,
                default_retry_delay=task_config.retry_delay,
                time_limit=task_config.timeout,
                soft_time_limit=task_config.soft_timeout,
                rate_limit=task_config.rate_limit,
                queue=task_config.queue_name,
            )(self._create_task_wrapper(func, task_config))

            # Register task
            self.task_registry[task_name] = celery_task

            return celery_task

        return decorator

    def _create_task_wrapper(self, func: Callable, config: TaskConfig) -> Callable:
        """Create a wrapper for async functions to work with Celery"""

        @functools.wraps(func)
        @with_error_handling(f"task_{func.__name__}")
        async def async_wrapper(celery_self, *args, **kwargs):
            task_id = celery_self.request.id
            start_time = time.time()

            try:
                # Update task status
                celery_self.update_state(state="STARTED", meta={"progress": 0})

                # Execute the actual function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Calculate duration and update metrics
                duration = time.time() - start_time
                self.metrics.record_histogram(
                    "task_duration",
                    duration,
                    labels={"task_name": func.__name__, "status": "success"},
                )

                # Cache result if needed
                await self._cache_task_result(task_id, result, duration)

                self.logger.info(
                    f"Task {task_id} completed successfully in {duration:.2f}s",
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_histogram(
                    "task_duration",
                    duration,
                    labels={"task_name": func.__name__, "status": "error"},
                )

                self.logger.error(
                    f"Task {task_id} failed after {duration:.2f}s",
                    error=e,
                )
                raise

        def sync_wrapper(celery_self, *args, **kwargs):
            """Sync wrapper that runs async function in event loop"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    async_wrapper(celery_self, *args, **kwargs),
                )
            finally:
                loop.close()

        return sync_wrapper

    @with_circuit_breaker("task_execution")
    async def submit_task(
        self,
        task_name: str,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        eta: datetime | None = None,
        countdown: int | None = None,
        **kwargs,
    ) -> str:
        """Submit a task for execution"""
        try:
            if task_name not in self.task_registry:
                raise TaskQueueError(f"Task '{task_name}' not registered")

            task = self.task_registry[task_name]

            # Determine queue based on priority
            queue_name = self._get_queue_for_priority(priority)

            # Submit task
            result = task.apply_async(
                args=args,
                kwargs=kwargs,
                queue=queue_name,
                eta=eta,
                countdown=countdown,
                priority=priority.value,
            )

            task_id = result.id

            # Track task submission
            await self._track_task_submission(task_id, task_name, priority)

            self.logger.info(
                f"Submitted task {task_id} ({task_name}) to queue {queue_name}",
            )
            self.metrics.increment_counter(
                "tasks_submitted",
                labels={
                    "task_name": task_name,
                    "priority": priority.name,
                    "queue": queue_name,
                },
            )

            return task_id

        except Exception as e:
            self.metrics.increment_counter(
                "task_submission_errors",
                labels={"task_name": task_name},
            )
            raise TaskQueueError(
                f"Failed to submit task: {str(e)}",
                original_exception=e,
            )

    async def get_task_result(self, task_id: str, timeout: float = 10.0) -> TaskResult:
        """Get task result with caching"""
        try:
            # Try cache first
            cached_result = await self.cache.get(f"task_result:{task_id}")
            if cached_result:
                return TaskResult(**cached_result)

            # Get from Celery
            result = AsyncResult(task_id, app=self.celery_app)

            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus(result.status),
                result=result.result if result.successful() else None,
                error=str(result.result) if result.failed() else None,
                retries=getattr(result.info, "retries", 0) if result.info else 0,
                metadata=result.info if isinstance(result.info, dict) else {},
            )

            # Cache completed results
            if task_result.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE]:
                await self.cache.set(
                    f"task_result:{task_id}",
                    task_result.__dict__,
                    ttl=3600,
                )

            return task_result

        except Exception as e:
            raise TaskQueueError(
                f"Failed to get task result: {str(e)}",
                original_exception=e,
            )

    async def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """Cancel a running task"""
        try:
            self.celery_app.control.revoke(task_id, terminate=terminate)

            self.logger.info(f"Cancelled task {task_id} (terminate={terminate})")
            self.metrics.increment_counter(
                "tasks_cancelled",
                labels={"terminate": str(terminate)},
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id}", error=e)
            return False

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get comprehensive queue statistics"""
        try:
            active_tasks = self.celery_app.control.inspect().active()
            scheduled_tasks = self.celery_app.control.inspect().scheduled()
            reserved_tasks = self.celery_app.control.inspect().reserved()

            stats = {
                "active_tasks": active_tasks or {},
                "scheduled_tasks": scheduled_tasks or {},
                "reserved_tasks": reserved_tasks or {},
                "total_active": sum(
                    len(tasks) for tasks in (active_tasks or {}).values()
                ),
                "total_scheduled": sum(
                    len(tasks) for tasks in (scheduled_tasks or {}).values()
                ),
                "total_reserved": sum(
                    len(tasks) for tasks in (reserved_tasks or {}).values()
                ),
            }

            return stats

        except Exception as e:
            self.logger.error("Failed to get queue stats", error=e)
            return {"error": str(e)}

    def _get_queue_for_priority(self, priority: TaskPriority) -> str:
        """Map priority to queue name"""
        priority_queues = {
            TaskPriority.LOW: "low_priority",
            TaskPriority.NORMAL: "default",
            TaskPriority.HIGH: "high_priority",
            TaskPriority.CRITICAL: "high_priority",
        }
        return priority_queues.get(priority, "default")

    async def _track_task_submission(
        self,
        task_id: str,
        task_name: str,
        priority: TaskPriority,
    ) -> None:
        """Track task submission in cache for monitoring"""
        submission_data = {
            "task_id": task_id,
            "task_name": task_name,
            "priority": priority.name,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "submitted",
        }

        # 2 hours
        await self.cache.set(f"task_tracking:{task_id}", submission_data, ttl=7200)

    async def _cache_task_result(
        self,
        task_id: str,
        result: Any,
        duration: float,
    ) -> None:
        """Cache task result with metadata"""
        result_data = {
            "task_id": task_id,
            "status": "success",
            "result": result,
            "duration": duration,
            "completed_at": datetime.utcnow().isoformat(),
        }

        await self.cache.set(f"task_result:{task_id}", result_data, ttl=3600)


# Global task queue instance
task_queue: AsyncTaskQueue | None = None


def get_task_queue() -> AsyncTaskQueue:
    """Get global task queue instance"""
    global task_queue
    if task_queue is None:
        task_queue = AsyncTaskQueue()
    return task_queue


# Convenience decorators
def async_task(config: TaskConfig | None = None, name: str | None = None):
    """Convenience decorator for registering async tasks"""
    queue = get_task_queue()
    return queue.task(config=config, name=name)


@asynccontextmanager
async def task_queue_context():
    """Context manager for task queue operations"""
    queue = get_task_queue()
    try:
        await queue.connect()
        yield queue
    finally:
        await queue.disconnect()


# Example usage and predefined tasks
@async_task(
    config=TaskConfig(
        max_retries=5,
        timeout=600.0,
        priority=TaskPriority.HIGH,
        queue_name="ai_processing",
    ),
    name="ai.process_document",
)
async def process_document_task(
    document_id: str,
    options: dict[str, Any] = None,
) -> dict[str, Any]:
    """Example AI processing task"""
    logger.info(f"Processing document {document_id} with options {options}")

    # Simulate AI processing
    await asyncio.sleep(2)

    return {
        "document_id": document_id,
        "status": "processed",
        "tokens": 1500,
        "processing_time": 2.0,
        "options": options or {},
    }


@async_task(
    config=TaskConfig(
        max_retries=3,
        timeout=300.0,
        priority=TaskPriority.NORMAL,
        queue_name="data_processing",
    ),
    name="data.sync_knowledge_vault",
)
async def sync_knowledge_vault_task(
    vault_path: str,
    sync_options: dict[str, Any] = None,
) -> dict[str, Any]:
    """Example data synchronization task"""
    logger.info(f"Syncing knowledge vault at {vault_path}")

    # Simulate sync operation
    await asyncio.sleep(5)

    return {
        "vault_path": vault_path,
        "files_synced": 42,
        "sync_time": 5.0,
        "status": "completed",
    }


# Testing function
if __name__ == "__main__":

    async def test_task_queue():
        """Test the async task queue system"""
        async with task_queue_context() as queue:
            print("Testing async task queue...")

            # Submit test tasks
            doc_task_id = await queue.submit_task(
                "ai.process_document",
                "doc_123",
                options={"extract_entities": True},
            )
            print(f"Submitted document processing task: {doc_task_id}")

            sync_task_id = await queue.submit_task(
                "data.sync_knowledge_vault",
                "/path/to/vault",
                sync_options={"incremental": True},
            )
            print(f"Submitted vault sync task: {sync_task_id}")

            # Check queue stats
            stats = await queue.get_queue_stats()
            print(f"Queue stats: {stats}")

            print("Task queue test completed")

    asyncio.run(test_task_queue())
