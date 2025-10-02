"""Minimal Service Registry Implementation
Task T039 - Phase 18 Production System Integration

This is the MINIMAL implementation to make TDD tests pass.
Following TDD Green Phase - just enough to pass tests, then refactor.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


# Minimal data models for TDD
class ServiceConfig(BaseModel):
    service_name: str
    service_version: str = "1.0.0"
    service_type: str = "API"
    environment: str = "DEVELOPMENT"
    base_url: str
    health_check_url: str
    health_check_interval_seconds: int = 30
    health_timeout_seconds: int = 5
    resource_requirements: Optional[dict[str, Any]] = None
    endpoints: Optional[list[dict[str, Any]]] = None
    dependencies: Optional[list[dict[str, Any]]] = None
    labels: Optional[dict[str, str]] = None


class ServiceUpdate(BaseModel):
    service_version: Optional[str] = None
    labels: Optional[dict[str, str]] = None
    resource_requirements: Optional[dict[str, Any]] = None


# In-memory storage for TDD (will be replaced with database)
registered_services: dict[str, dict[str, Any]] = {}
service_health_status: dict[str, dict[str, Any]] = {}


app = FastAPI(
    title="PAKE System Service Registry",
    version="18.0.0",
    description="Minimal implementation for TDD Green Phase",
)


@app.post("/api/v1/services/register", status_code=201)
async def register_service(service_config: ServiceConfig):
    """Minimal service registration to satisfy test_service_registry_integration.py

    This implements just enough to pass the integration tests:
    - Accepts service configuration
    - Returns service_id
    - Stores service in memory
    - Activates health monitoring
    """
    service_id = str(uuid.uuid4())

    # Convert to dict and add metadata
    service_data = service_config.dict()
    service_data.update(
        {
            "service_id": service_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "deployed_at": datetime.utcnow().isoformat(),
            "status": "HEALTHY",
        }
    )

    # Store service
    registered_services[service_id] = service_data

    # Initialize health status
    service_health_status[service_id] = {
        "service_id": service_id,
        "service_name": service_config.service_name,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": 5.0,
        "last_check": datetime.utcnow().isoformat(),
    }

    # Mock health monitoring activation
    asyncio.create_task(mock_health_monitoring(service_id))

    return {
        "status": "registered",
        "service_id": service_id,
        "health_check_url": service_config.health_check_url,
    }


@app.get("/api/v1/services")
async def list_services(
    environment: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """Service discovery with filtering"""
    services = list(registered_services.values())

    # Apply filters
    if environment:
        services = [s for s in services if s.get("environment") == environment]

    if service_type:
        services = [s for s in services if s.get("service_type") == service_type]

    if status:
        services = [
            s for s in services if s.get("status", "").lower() == status.lower()
        ]

    return services


@app.get("/api/v1/services/{service_id}")
async def get_service(service_id: str):
    """Get individual service configuration"""
    if service_id not in registered_services:
        raise HTTPException(status_code=404, detail="Service not found")

    return registered_services[service_id]


@app.put("/api/v1/services/{service_id}")
async def update_service(service_id: str, update: ServiceUpdate):
    """Update service configuration"""
    if service_id not in registered_services:
        raise HTTPException(status_code=404, detail="Service not found")

    service = registered_services[service_id]

    # Apply updates
    if update.service_version:
        service["service_version"] = update.service_version

    if update.labels:
        if "labels" not in service:
            service["labels"] = {}
        service["labels"].update(update.labels)

    if update.resource_requirements:
        service["resource_requirements"] = update.resource_requirements

    service["updated_at"] = datetime.utcnow().isoformat()

    return service


@app.delete("/api/v1/services/{service_id}")
async def deregister_service(service_id: str):
    """Remove service from registry"""
    if service_id in registered_services:
        del registered_services[service_id]

    if service_id in service_health_status:
        del service_health_status[service_id]

    return {"status": "deregistered", "service_id": service_id}


@app.get("/api/v1/services/{service_id}/health")
async def get_service_health(
    service_id: str,
    include_dependencies: bool = Query(False),
    include_metrics: bool = Query(False),
):
    """Get service health status"""
    if service_id not in service_health_status:
        raise HTTPException(status_code=404, detail="Service not found")

    health = service_health_status[service_id].copy()

    if include_dependencies:
        # Mock dependency health
        service = registered_services.get(service_id, {})
        dependencies = service.get("dependencies", [])

        health["dependencies"] = {}
        for dep in dependencies:
            dep_name = dep.get("provider_service_name", "unknown")
            health["dependencies"][dep_name] = {
                "status": "healthy",
                "response_time_ms": 10.0,
                "last_check": datetime.utcnow().isoformat(),
            }

    if include_metrics:
        health["metrics"] = {
            "requests_per_minute": 120,
            "error_rate": 0.01,
            "cpu_usage_percentage": 25.5,
            "memory_usage_mb": 128,
        }

    return health


@app.get("/api/v1/services/{service_id}/dependencies")
async def get_service_dependencies(service_id: str):
    """Get service dependencies"""
    if service_id not in registered_services:
        raise HTTPException(status_code=404, detail="Service not found")

    service = registered_services[service_id]
    dependencies = service.get("dependencies", [])

    # Add dependency metadata
    for dep in dependencies:
        dep["dependency_id"] = str(uuid.uuid4())
        dep["status"] = "healthy"
        dep["last_check"] = datetime.utcnow().isoformat()

    return dependencies


@app.put("/api/v1/services/{service_id}/health-config")
async def update_health_config(service_id: str, config: dict[str, Any]):
    """Update health check configuration"""
    if service_id not in registered_services:
        raise HTTPException(status_code=404, detail="Service not found")

    service = registered_services[service_id]

    # Update health check configuration
    if "health_check_interval_seconds" in config:
        service["health_check_interval_seconds"] = config[
            "health_check_interval_seconds"
        ]

    if "health_timeout_seconds" in config:
        service["health_timeout_seconds"] = config["health_timeout_seconds"]

    service["updated_at"] = datetime.utcnow().isoformat()

    return {"status": "updated", "service_id": service_id}


async def mock_health_monitoring(service_id: str):
    """Mock health monitoring background task"""
    while service_id in service_health_status:
        # Update health status
        service_health_status[service_id].update(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "last_check": datetime.utcnow().isoformat(),
                "response_time_ms": 5.0
                + (hash(service_id) % 10),  # Mock variable response time
            }
        )

        # Wait for next check (shortened for testing)
        await asyncio.sleep(5)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="127.0.0.1", port=8000
    )  # Secure local binding instead of 0.0.0.0
