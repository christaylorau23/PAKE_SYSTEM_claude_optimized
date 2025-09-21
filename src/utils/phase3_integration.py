#!/usr/bin/env python3
"""PAKE+ Phase 3 Frontend Integration Components
Backend services and API endpoints for Phase 3 UI/UX integration
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils.api_patterns import (
    APIConfig,
    APIResponse,
    EnhancedAPIFactory,
    ResponseStatus,
)
from utils.async_task_queue import AsyncTaskQueue, TaskPriority
from utils.distributed_cache import CacheConfig, DistributedCache
from utils.error_handling import with_error_handling

# Import Phase 1 & 2 foundation components
from utils.logger import get_logger
from utils.metrics import MetricsStore

logger = get_logger(service_name="pake-phase3-integration")
metrics = MetricsStore(service_name="pake-phase3-integration")


class UIComponentType(Enum):
    """Frontend UI component types"""

    DASHBOARD = "dashboard"
    FORM = "form"
    CHART = "chart"
    TABLE = "table"
    CARD = "card"
    MODAL = "modal"
    NOTIFICATION = "notification"


class SystemStatus(Enum):
    """System health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


@dataclass
class ComponentMetrics:
    """UI component performance metrics"""

    component_type: UIComponentType
    load_time_ms: float
    render_time_ms: float
    interaction_count: int = 0
    error_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SystemHealthData:
    """Comprehensive system health information"""

    overall_status: SystemStatus
    components: dict[str, str]
    metrics: dict[str, float]
    alerts: list[str] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.utcnow)


# Frontend API Models
class DashboardRequest(BaseModel):
    """Dashboard data request"""

    timeRange: str = Field(default="24h", description="Time range for metrics")
    components: list[str] = Field(default=[], description="Specific components to load")
    refresh: bool = Field(default=False, description="Force refresh data")


class TaskQueueStatus(BaseModel):
    """Task queue status for frontend display"""

    total_active: int
    total_pending: int
    total_completed: int
    total_failed: int
    queue_health: str
    average_completion_time: float
    recent_tasks: list[dict[str, Any]]


class MetricsData(BaseModel):
    """System metrics for frontend charts"""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: dict[str, float]
    request_count: int
    response_time_avg: float
    error_rate: float


class SecurityStatus(BaseModel):
    """Security status for frontend monitoring"""

    threats_blocked: int
    security_score: float
    recent_incidents: list[dict[str, Any]]
    prompt_injections_blocked: int
    authentication_failures: int


class Phase3IntegrationService:
    """Service class for Phase 3 frontend integration"""

    def __init__(self):
        self.logger = get_logger(service_name="phase3-integration")
        self.metrics = MetricsStore(service_name="phase3-integration")

        # Initialize Phase 2 components
        self.cache = None
        self.task_queue = None
        self.websocket_connections: list[WebSocket] = []

        # Component performance tracking
        self.component_metrics: dict[str, ComponentMetrics] = {}

    async def initialize(self):
        """Initialize all Phase 2 backend connections"""
        try:
            # Initialize distributed cache
            cache_config = CacheConfig(
                host="localhost",
                port=6379,
                REDACTED_SECRET=os.getenv("REDIS_PASSWORD", "REDACTED_SECRET"),
                default_ttl=300,
            )
            self.cache = DistributedCache(cache_config)
            await self.cache.connect()

            # Initialize task queue
            self.task_queue = AsyncTaskQueue(
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            )
            await self.task_queue.connect()

            self.logger.info("Phase 3 integration service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 3 integration: {e}")
            raise

    @with_error_handling("get_dashboard_data")
    async def get_dashboard_data(self, request: DashboardRequest) -> dict[str, Any]:
        """Get comprehensive dashboard data for frontend"""
        # Check cache first
        cache_key = f"dashboard:{request.timeRange}:{hash(str(request.components))}"
        cached_data = await self.cache.get(cache_key)

        if cached_data and not request.refresh:
            self.metrics.increment_counter("dashboard_cache_hits")
            return cached_data

        # Gather fresh data
        dashboard_data = {
            "system_health": await self._get_system_health(),
            "task_queue_status": await self._get_task_queue_status(),
            "metrics": await self._get_metrics_data(request.timeRange),
            "security_status": await self._get_security_status(),
            "component_performance": self._get_component_performance(),
            "alerts": await self._get_system_alerts(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Cache the result
        await self.cache.set(cache_key, dashboard_data, ttl=60)  # 1 minute cache

        self.metrics.increment_counter("dashboard_data_generated")
        return dashboard_data

    async def _get_system_health(self) -> SystemHealthData:
        """Get comprehensive system health status"""
        try:
            # Check Phase 2 component health
            components = {}

            # Check Redis connectivity
            try:
                await self.cache.exists("health_check")
                components["redis"] = "healthy"
            except Exception:
                components["redis"] = "unhealthy"

            # Check task queue
            try:
                queue_stats = await self.task_queue.get_queue_stats()
                components["task_queue"] = "healthy" if queue_stats else "degraded"
            except Exception:
                components["task_queue"] = "unhealthy"

            # Determine overall status
            unhealthy_components = [
                k for k, v in components.items() if v == "unhealthy"
            ]
            if len(unhealthy_components) == 0:
                overall_status = SystemStatus.HEALTHY
            elif len(unhealthy_components) < len(components) / 2:
                overall_status = SystemStatus.DEGRADED
            else:
                overall_status = SystemStatus.UNHEALTHY

            return SystemHealthData(
                overall_status=overall_status,
                components=components,
                metrics={
                    "uptime": time.time(),
                    "response_time": 150.0,  # Simulated
                    "cpu_usage": 25.5,  # Simulated
                    "memory_usage": 45.2,  # Simulated
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return SystemHealthData(
                overall_status=SystemStatus.UNHEALTHY,
                components={"error": "failed"},
                metrics={},
                alerts=["System health check failed"],
            )

    async def _get_task_queue_status(self) -> TaskQueueStatus:
        """Get task queue status for frontend display"""
        try:
            stats = await self.task_queue.get_queue_stats()

            return TaskQueueStatus(
                total_active=stats.get("total_active", 0),
                total_pending=stats.get("total_scheduled", 0)
                + stats.get("total_reserved", 0),
                total_completed=150,  # Simulated - would come from metrics
                total_failed=3,  # Simulated - would come from metrics
                queue_health="healthy",
                average_completion_time=2.5,  # seconds
                recent_tasks=[
                    {
                        "id": "task_123",
                        "name": "ai.process_document",
                        "status": "completed",
                        "duration": 2.3,
                    },
                    {
                        "id": "task_124",
                        "name": "data.sync_knowledge_vault",
                        "status": "running",
                        "duration": None,
                    },
                ],
            )

        except Exception as e:
            self.logger.error(f"Failed to get task queue status: {e}")
            return TaskQueueStatus(
                total_active=0,
                total_pending=0,
                total_completed=0,
                total_failed=0,
                queue_health="unhealthy",
                average_completion_time=0.0,
                recent_tasks=[],
            )

    async def _get_metrics_data(self, time_range: str) -> list[MetricsData]:
        """Get time-series metrics data for charts"""
        # This would typically query Prometheus or time-series database
        # For demo, return simulated data

        now = datetime.utcnow()
        data_points = []

        # Generate hourly data points for last 24 hours
        for i in range(24):
            timestamp = now - timedelta(hours=23 - i)
            data_points.append(
                MetricsData(
                    timestamp=timestamp,
                    cpu_usage=20 + (i % 5) * 5,  # Simulated pattern
                    memory_usage=40 + (i % 3) * 10,
                    disk_usage=60 + i,
                    network_io={"ingress": 100 + i * 10, "egress": 80 + i * 8},
                    request_count=1000 + i * 50,
                    response_time_avg=150 + (i % 4) * 25,
                    error_rate=0.1 + (i % 2) * 0.05,
                ),
            )

        return data_points

    async def _get_security_status(self) -> SecurityStatus:
        """Get security status from Phase 1 security guards"""
        try:
            # This would query actual security metrics
            return SecurityStatus(
                threats_blocked=42,
                security_score=98.5,
                recent_incidents=[
                    {
                        "type": "prompt_injection",
                        "timestamp": datetime.utcnow().isoformat(),
                        "threat_level": "high",
                        "blocked": True,
                    },
                ],
                prompt_injections_blocked=15,
                authentication_failures=2,
            )

        except Exception as e:
            self.logger.error(f"Failed to get security status: {e}")
            return SecurityStatus(
                threats_blocked=0,
                security_score=0.0,
                recent_incidents=[],
                prompt_injections_blocked=0,
                authentication_failures=0,
            )

    def _get_component_performance(self) -> dict[str, ComponentMetrics]:
        """Get UI component performance metrics"""
        return {
            name: {
                "component_type": metric.component_type.value,
                "load_time_ms": metric.load_time_ms,
                "render_time_ms": metric.render_time_ms,
                "interaction_count": metric.interaction_count,
                "error_count": metric.error_count,
                "last_updated": metric.last_updated.isoformat(),
            }
            for name, metric in self.component_metrics.items()
        }

    async def _get_system_alerts(self) -> list[dict[str, Any]]:
        """Get current system alerts"""
        return [
            {
                "id": "alert_1",
                "type": "info",
                "message": "System performance optimal",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]

    def track_component_performance(
        self,
        component_name: str,
        component_type: UIComponentType,
        load_time_ms: float,
        render_time_ms: float,
    ):
        """Track frontend component performance"""
        if component_name not in self.component_metrics:
            self.component_metrics[component_name] = ComponentMetrics(
                component_type=component_type,
                load_time_ms=load_time_ms,
                render_time_ms=render_time_ms,
            )
        else:
            metric = self.component_metrics[component_name]
            metric.load_time_ms = load_time_ms
            metric.render_time_ms = render_time_ms
            metric.interaction_count += 1
            metric.last_updated = datetime.utcnow()

    async def handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connections for real-time updates"""
        await websocket.accept()
        self.websocket_connections.append(websocket)

        try:
            while True:
                # Send periodic updates
                dashboard_data = await self.get_dashboard_data(
                    DashboardRequest(timeRange="1h", refresh=True),
                )

                await websocket.send_json(
                    {"type": "dashboard_update", "data": dashboard_data},
                )

                await asyncio.sleep(10)  # Update every 10 seconds

        except WebSocketDisconnect:
            self.websocket_connections.remove(websocket)
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)

    async def broadcast_update(self, message: dict[str, Any]):
        """Broadcast update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return

        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Remove disconnected clients
        for ws in disconnected:
            self.websocket_connections.remove(ws)

    async def process_frontend_task(self, task_data: dict[str, Any]) -> str:
        """Process a task requested from the frontend"""
        try:
            task_id = await self.task_queue.submit_task(
                task_data.get("task_name", "frontend.process_request"),
                task_data.get("data", {}),
                priority=TaskPriority.HIGH,
            )

            # Broadcast task start notification
            await self.broadcast_update(
                {
                    "type": "task_started",
                    "task_id": task_id,
                    "task_name": task_data.get("task_name"),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            return task_id

        except Exception as e:
            self.logger.error(f"Failed to process frontend task: {e}")
            raise


# Global service instance
phase3_service: Phase3IntegrationService | None = None


async def get_phase3_service() -> Phase3IntegrationService:
    """Get global Phase 3 integration service instance"""
    global phase3_service
    if phase3_service is None:
        phase3_service = Phase3IntegrationService()
        await phase3_service.initialize()
    return phase3_service


# FastAPI app for Phase 3 integration
async def create_phase3_integration_app() -> FastAPI:
    """Create Phase 3 integration API app"""
    # Create enhanced API with Phase 2 foundation
    config = APIConfig(
        rate_limit_requests_per_minute=120,  # Higher limit for frontend
        enable_security_guards=True,
        enable_detailed_metrics=True,
        default_cache_ttl=60,
    )

    factory = EnhancedAPIFactory(config, redis_url="redis://localhost:6379/2")
    app = await factory.create_app(
        title="PAKE+ Phase 3 Frontend Integration API",
        description="API endpoints for Phase 3 UI/UX integration",
        version="3.0.0",
    )

    # Add CORS for frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    service = await get_phase3_service()

    # Dashboard endpoints
    @app.get("/api/v3/dashboard", response_model=APIResponse, tags=["Frontend"])
    async def get_dashboard(timeRange: str = "24h", refresh: bool = False):
        """Get dashboard data for frontend"""
        request = DashboardRequest(timeRange=timeRange, refresh=refresh)
        data = await service.get_dashboard_data(request)

        return APIResponse(
            status=ResponseStatus.SUCCESS,
            data=data,
            message="Dashboard data retrieved successfully",
        )

    @app.get(
        "/api/v3/metrics/{time_range}",
        response_model=APIResponse,
        tags=["Frontend"],
    )
    async def get_metrics(time_range: str):
        """Get time-series metrics for charts"""
        metrics_data = await service._get_metrics_data(time_range)

        return APIResponse(
            status=ResponseStatus.SUCCESS,
            data=[metric.dict() for metric in metrics_data],
            message=f"Metrics for {time_range} retrieved successfully",
        )

    @app.post("/api/v3/tasks", response_model=APIResponse, tags=["Frontend"])
    async def submit_frontend_task(task_data: dict[str, Any]):
        """Submit a task from the frontend"""
        task_id = await service.process_frontend_task(task_data)

        return APIResponse(
            status=ResponseStatus.SUCCESS,
            data={"task_id": task_id},
            message="Task submitted successfully",
        )

    @app.get(
        "/api/v3/component-performance",
        response_model=APIResponse,
        tags=["Frontend"],
    )
    async def get_component_performance():
        """Get UI component performance metrics"""
        performance_data = service._get_component_performance()

        return APIResponse(
            status=ResponseStatus.SUCCESS,
            data=performance_data,
            message="Component performance data retrieved",
        )

    # WebSocket endpoint for real-time updates
    @app.websocket("/ws/dashboard")
    async def websocket_dashboard(websocket: WebSocket):
        """WebSocket endpoint for real-time dashboard updates"""
        await service.handle_websocket_connection(websocket)

    return app


# Testing function
if __name__ == "__main__":

    async def test_phase3_integration():
        """Test Phase 3 integration components"""
        print("Testing Phase 3 Frontend Integration...")

        try:
            service = Phase3IntegrationService()
            await service.initialize()

            # Test dashboard data generation
            request = DashboardRequest(timeRange="24h")
            dashboard_data = await service.get_dashboard_data(request)

            print("SUCCESS: Dashboard data generated")
            print(
                f"  - System status: {dashboard_data['system_health']['overall_status']}",
            )
            print(
                f"  - Active tasks: {dashboard_data['task_queue_status']['total_active']}",
            )
            print(f"  - Metrics points: {len(dashboard_data['metrics'])}")

            # Test component performance tracking
            service.track_component_performance(
                "dashboard-card",
                UIComponentType.CARD,
                load_time_ms=150.0,
                render_time_ms=45.0,
            )

            performance = service._get_component_performance()
            print(
                f"SUCCESS: Component performance tracked: {len(performance)} components",
            )

            print("SUCCESS: Phase 3 integration validation complete")

        except Exception as e:
            print(f"ERROR: Phase 3 integration test failed: {e}")
            import traceback

            traceback.print_exc()

    asyncio.run(test_phase3_integration())
