#!/usr/bin/env python3
"""PAKE System - Phase 17 Enterprise Tenant API Endpoints
World-class tenant management endpoints with comprehensive validation and security.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.enterprise.multi_tenant_server import (
    TenantCreateRequest,
    UserCreateRequest,
    get_current_user,
)
from src.middleware.tenant_context import (
    get_current_tenant_id,
    require_admin_access,
)
from src.security.tenant_isolation_enforcer import enforce_tenant_isolation

# Import models and services (will be injected from main server)
from src.services.tenant.tenant_management_service import (
    TenantCreationRequest,
    TenantUpdateRequest,
    UserCreationRequest,
)

logger = logging.getLogger(__name__)

# Create tenant management router
tenant_router = APIRouter(prefix="/tenants", tags=["tenants"])


@tenant_router.post("/", status_code=201)
@enforce_tenant_isolation("create", "tenant")
async def create_tenant(
    request: TenantCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_access),
):
    """Create new tenant with complete provisioning"""
    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        # Validate request with security enforcer
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            raise HTTPException(status_code=400, detail="Invalid input detected")

        # Create tenant
        tenant_request = TenantCreationRequest(
            name=request.name,
            display_name=request.display_name,
            domain=request.domain,
            plan=request.plan,
            admin_email=request.admin_email,
            admin_username=request.admin_username,
            admin_full_name=request.admin_full_name,
        )

        result = await tenant_service.create_tenant(tenant_request)

        # Background task for complete provisioning
        background_tasks.add_task(provision_tenant_resources, result["tenant"]["id"])

        # Record metrics
        TENANT_OPERATIONS.labels(
            operation="create",
            tenant_id=result["tenant"]["id"],
        ).inc()

        logger.info(f"✅ Tenant created: {request.name}")

        return {
            "success": True,
            "tenant": result["tenant"],
            "admin_user": result["admin_user"],
            "message": "Tenant created successfully. Provisioning resources in background.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Tenant creation error: {e}")
        raise HTTPException(status_code=500, detail="Tenant creation service error")


@tenant_router.get("/")
@enforce_tenant_isolation("read", "tenants")
async def list_tenants(
    status_filter: str | None = None,
    plan_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_admin_access),
):
    """List tenants with filtering and pagination"""
    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        result = await tenant_service.list_tenants(
            status=status_filter,
            plan=plan_filter,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "tenants": result["tenants"],
            "pagination": result["pagination"],
        }

    except Exception as e:
        logger.error(f"Tenant listing error: {e}")
        raise HTTPException(status_code=500, detail="Tenant listing service error")


@tenant_router.get("/{tenant_id}")
@enforce_tenant_isolation("read", "tenant")
async def get_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Get tenant details with statistics"""
    # Validate tenant access
    current_tenant = get_current_tenant_id()
    if current_tenant != tenant_id and current_user["role"] not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied to tenant data")

    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        result = await tenant_service.get_tenant(tenant_id)
        if not result:
            raise HTTPException(status_code=404, detail="Tenant not found")

        return {"success": True, "tenant": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Tenant retrieval service error")


@tenant_router.put("/{tenant_id}")
@enforce_tenant_isolation("update", "tenant")
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
    current_user: dict = Depends(require_admin_access),
):
    """Update tenant configuration"""
    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        # Validate input
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            raise HTTPException(status_code=400, detail="Invalid input detected")

        result = await tenant_service.update_tenant(tenant_id, request)

        # Record metrics
        TENANT_OPERATIONS.labels(operation="update", tenant_id=tenant_id).inc()

        return {
            "success": True,
            "tenant": result["tenant"],
            "message": "Tenant updated successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Tenant update error: {e}")
        raise HTTPException(status_code=500, detail="Tenant update service error")


@tenant_router.delete("/{tenant_id}")
@enforce_tenant_isolation("delete", "tenant")
async def delete_tenant(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: dict = Depends(require_admin_access),
):
    """Delete tenant and all associated resources"""
    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        result = await tenant_service.delete_tenant(tenant_id, force)

        # Background cleanup
        if result["status"] == "success":
            background_tasks.add_task(cleanup_tenant_resources, tenant_id)

        # Record metrics
        TENANT_OPERATIONS.labels(operation="delete", tenant_id=tenant_id).inc()

        return {
            "success": True,
            "message": result["message"],
            "status": result["status"],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Tenant deletion error: {e}")
        raise HTTPException(status_code=500, detail="Tenant deletion service error")


@tenant_router.get("/{tenant_id}/analytics")
@enforce_tenant_isolation("read", "tenant_analytics")
async def get_tenant_analytics(
    tenant_id: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
):
    """Get comprehensive tenant analytics"""
    # Validate tenant access
    current_tenant = get_current_tenant_id()
    if current_tenant != tenant_id and current_user["role"] not in [
        "admin",
        "super_admin",
    ]:
        raise HTTPException(status_code=403, detail="Access denied to tenant analytics")

    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        analytics = await tenant_service.get_tenant_analytics(tenant_id, days)

        return {"success": True, "analytics": analytics}

    except Exception as e:
        logger.error(f"Tenant analytics error: {e}")
        raise HTTPException(status_code=500, detail="Tenant analytics service error")


# User management endpoints within tenants
user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.post("/", status_code=201)
@enforce_tenant_isolation("create", "user")
async def create_user(
    request: UserCreateRequest,
    current_user: dict = Depends(require_admin_access),
):
    """Create new user within current tenant"""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        # Validate input
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            raise HTTPException(status_code=400, detail="Invalid input detected")

        user_request = UserCreationRequest(
            username=request.username,
            email=request.email,
            REDACTED_SECRET=request.REDACTED_SECRET,
            full_name=request.full_name,
            role=request.role,
        )

        result = await tenant_service.create_user(tenant_id, user_request)

        return {
            "success": True,
            "user": result["user"],
            "message": "User created successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(status_code=500, detail="User creation service error")


@user_router.get("/")
@enforce_tenant_isolation("read", "users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """List users within current tenant"""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Check permissions
    if current_user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not tenant_service:
        raise HTTPException(status_code=503, detail="Tenant service not available")

    try:
        result = await tenant_service.get_tenant_users(tenant_id, limit, offset)

        return {
            "success": True,
            "users": result["users"],
            "pagination": result["pagination"],
        }

    except Exception as e:
        logger.error(f"User listing error: {e}")
        raise HTTPException(status_code=500, detail="User listing service error")


# Background task functions


async def provision_tenant_resources(tenant_id: str):
    """Background task to provision tenant resources"""
    try:
        logger.info(f"🔄 Provisioning resources for tenant {tenant_id}")

        # Run tenant provisioning script
        from scripts.provision_tenant import (
            MultiTenantDatabaseConfig,
            TenantProvisioner,
        )

        db_config = MultiTenantDatabaseConfig()
        provisioner = TenantProvisioner(db_config)

        await provisioner.initialize()

        # Get tenant data
        tenant_data = await tenant_service.get_tenant(tenant_id)
        if not tenant_data:
            logger.error(f"Tenant not found for provisioning: {tenant_id}")
            return

        tenant = tenant_data["tenant"]

        # Provision Kubernetes resources
        k8s_success = await provisioner.create_k8s_namespace(
            {"tenant": tenant},
            provisioner._generate_credentials(),
        )

        if k8s_success:
            logger.info(f"✅ Successfully provisioned resources for tenant {tenant_id}")
        else:
            logger.warning(f"⚠️ Partial provisioning for tenant {tenant_id}")

        await provisioner.close()

    except Exception as e:
        logger.error(f"❌ Resource provisioning failed for tenant {tenant_id}: {e}")


async def cleanup_tenant_resources(tenant_id: str):
    """Background task to cleanup tenant resources"""
    try:
        logger.info(f"🧹 Cleaning up resources for tenant {tenant_id}")

        # Cleanup Kubernetes resources
        # Cleanup cached orchestrators
        if tenant_id in tenant_orchestrators:
            del tenant_orchestrators[tenant_id]

        # Additional cleanup tasks would go here

        logger.info(f"✅ Successfully cleaned up resources for tenant {tenant_id}")

    except Exception as e:
        logger.error(f"❌ Resource cleanup failed for tenant {tenant_id}: {e}")
