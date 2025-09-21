#!/usr/bin/env python3
"""PAKE System - Phase 16 Tenant Management Service
Enterprise-grade tenant management with automated provisioning and lifecycle management.
"""

import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import bcrypt

from src.middleware.tenant_context import (
    create_tenant_jwt,
    get_current_user_id,
)
from src.services.database.multi_tenant_schema import (
    MultiTenantPostgreSQLService,
)
from src.services.database.tenant_aware_dal import (
    TenantAwareDataAccessLayer,
)

logger = logging.getLogger(__name__)


@dataclass
class TenantCreationRequest:
    """Tenant creation request model"""

    name: str
    display_name: str
    domain: str | None = None
    plan: str = "basic"
    admin_email: str = ""
    admin_username: str = "admin"
    admin_full_name: str | None = None
    settings: dict[str, Any] | None = None
    limits: dict[str, Any] | None = None


@dataclass
class TenantUpdateRequest:
    """Tenant update request model"""

    display_name: str | None = None
    domain: str | None = None
    plan: str | None = None
    status: str | None = None
    settings: dict[str, Any] | None = None
    limits: dict[str, Any] | None = None


@dataclass
class UserCreationRequest:
    """User creation request model"""

    username: str
    email: str
    REDACTED_SECRET: str
    full_name: str | None = None
    role: str = "user"
    is_active: bool = True


@dataclass
class TenantStats:
    """Tenant statistics model"""

    tenant_id: str
    user_count: int
    search_count: int
    storage_usage_mb: float
    api_calls_today: int
    last_activity: datetime | None
    resource_utilization: dict[str, float]


class TenantPlanLimits:
    """Predefined tenant plan limits"""

    PLANS = {
        "basic": {
            "max_users": 5,
            "max_api_calls_per_day": 1000,
            "max_storage_mb": 1024,  # 1GB
            "max_concurrent_searches": 3,
            "features": ["search", "basic_analytics"],
            "support_level": "community",
        },
        "professional": {
            "max_users": 25,
            "max_api_calls_per_day": 10000,
            "max_storage_mb": 10240,  # 10GB
            "max_concurrent_searches": 10,
            "features": ["search", "advanced_analytics", "export", "api_access"],
            "support_level": "email",
        },
        "enterprise": {
            "max_users": 100,
            "max_api_calls_per_day": 100000,
            "max_storage_mb": 102400,  # 100GB
            "max_concurrent_searches": 50,
            "features": [
                "search",
                "advanced_analytics",
                "export",
                "api_access",
                "sso",
                "audit_logs",
            ],
            "support_level": "priority",
        },
    }

    @classmethod
    def get_plan_limits(cls, plan: str) -> dict[str, Any]:
        """Get limits for a specific plan"""
        return cls.PLANS.get(plan, cls.PLANS["basic"])

    @classmethod
    def validate_plan(cls, plan: str) -> bool:
        """Validate if plan exists"""
        return plan in cls.PLANS


class TenantManagementService:
    """Enterprise tenant management service.

    Features:
    - Complete tenant lifecycle management
    - User management within tenants
    - Plan-based resource limits
    - Activity tracking and analytics
    - Security and compliance features
    - Integration with Kubernetes provisioning
    """

    def __init__(self, db_service: MultiTenantPostgreSQLService):
        self.db_service = db_service
        self.dal = TenantAwareDataAccessLayer(db_service)

        # Repository access
        self.user_repo = self.dal.users
        self.activity_repo = self.dal.activity

        logger.info("Tenant Management Service initialized")

    async def create_tenant(self, request: TenantCreationRequest) -> dict[str, Any]:
        """Create new tenant with admin user.

        Process:
        1. Validate tenant name uniqueness
        2. Create tenant record
        3. Create admin user
        4. Set up default settings and limits
        5. Log tenant creation activity
        6. Return tenant details and access credentials
        """
        try:
            # Validate plan
            if not TenantPlanLimits.validate_plan(request.plan):
                raise ValueError(f"Invalid plan: {request.plan}")

            # Check tenant name uniqueness
            existing_tenant = await self.db_service.get_tenant_by_name(request.name)
            if existing_tenant:
                raise ValueError(f"Tenant name already exists: {request.name}")

            # Check domain uniqueness if provided
            if request.domain:
                existing_domain = await self.db_service.get_tenant_by_domain(
                    request.domain,
                )
                if existing_domain:
                    raise ValueError(f"Domain already exists: {request.domain}")

            # Get plan limits
            plan_limits = TenantPlanLimits.get_plan_limits(request.plan)

            # Merge custom limits with plan defaults
            final_limits = {**plan_limits, **(request.limits or {})}

            # Default settings
            default_settings = {
                "created_at": datetime.utcnow().isoformat(),
                "created_by": "system",
                "plan_features": plan_limits["features"],
                "support_level": plan_limits["support_level"],
                "onboarding_completed": False,
                "theme": "default",
                "timezone": "UTC",
                "notifications_enabled": True,
            }

            final_settings = {**default_settings, **(request.settings or {})}

            # Create tenant
            tenant = await self.db_service.create_tenant(
                name=request.name,
                display_name=request.display_name,
                domain=request.domain,
                plan=request.plan,
                settings=final_settings,
                limits=final_limits,
            )

            # Generate secure admin REDACTED_SECRET if not provided
            if not hasattr(request, "admin_REDACTED_SECRET") or not request.admin_REDACTED_SECRET:
                admin_REDACTED_SECRET = self._generate_REDACTED_SECRET()
            else:
                admin_REDACTED_SECRET = request.admin_REDACTED_SECRET

            # Hash REDACTED_SECRET
            REDACTED_SECRET_hash = bcrypt.hashpw(
                admin_REDACTED_SECRET.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

            # Create admin user
            admin_user = await self.db_service.create_user(
                tenant_id=tenant["id"],
                username=request.admin_username,
                email=request.admin_email,
                REDACTED_SECRET_hash=REDACTED_SECRET_hash,
                full_name=request.admin_full_name
                or f"{request.display_name} Administrator",
                role="admin",
            )

            # Log tenant creation
            await self.db_service.log_tenant_activity(
                tenant_id=tenant["id"],
                user_id=admin_user["id"],
                activity_type="tenant_created",
                activity_data={
                    "plan": request.plan,
                    "created_by": "system",
                    "admin_email": request.admin_email,
                },
            )

            # Generate access token for admin user
            access_token = create_tenant_jwt(
                tenant_id=tenant["id"],
                user_id=admin_user["id"],
                user_role="admin",
                permissions=["read", "write", "admin", "manage_users"],
                expires_hours=24,
            )

            logger.info(f"✅ Created tenant: {request.name} ({tenant['id']})")

            return {
                "status": "success",
                "tenant": tenant,
                "admin_user": {
                    "id": admin_user["id"],
                    "username": admin_user["username"],
                    "email": admin_user["email"],
                    "role": admin_user["role"],
                },
                "credentials": {
                    "admin_REDACTED_SECRET": admin_REDACTED_SECRET,
                    "access_token": access_token,
                },
                "next_steps": [
                    "Update admin REDACTED_SECRET",
                    "Complete tenant onboarding",
                    "Configure tenant settings",
                    "Invite additional users",
                    "Set up integrations",
                ],
            }

        except Exception as e:
            logger.error(f"Failed to create tenant: {e}")
            raise

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        """Get tenant by ID with comprehensive information"""
        try:
            tenant = await self.db_service.get_tenant_by_id(tenant_id)
            if not tenant:
                return None

            # Get tenant statistics
            stats = await self._get_tenant_stats(tenant_id)

            # Get recent activity
            recent_activity = await self.db_service.get_tenant_activity(
                tenant_id,
                limit=10,
            )

            return {
                "tenant": tenant,
                "statistics": stats,
                "recent_activity": recent_activity,
            }

        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            raise

    async def update_tenant(
        self,
        tenant_id: str,
        request: TenantUpdateRequest,
    ) -> dict[str, Any]:
        """Update tenant configuration"""
        try:
            # Get current tenant
            current_tenant = await self.db_service.get_tenant_by_id(tenant_id)
            if not current_tenant:
                raise ValueError(f"Tenant not found: {tenant_id}")

            # Validate plan if being changed
            if request.plan and not TenantPlanLimits.validate_plan(request.plan):
                raise ValueError(f"Invalid plan: {request.plan}")

            # Check domain uniqueness if being changed
            if request.domain and request.domain != current_tenant.get("domain"):
                existing_domain = await self.db_service.get_tenant_by_domain(
                    request.domain,
                )
                if existing_domain and existing_domain["id"] != tenant_id:
                    raise ValueError(f"Domain already exists: {request.domain}")

            # Prepare update data
            update_data = {}
            if request.display_name:
                update_data["display_name"] = request.display_name
            if request.domain:
                update_data["domain"] = request.domain
            if request.plan:
                update_data["plan"] = request.plan
                # Update limits based on new plan
                plan_limits = TenantPlanLimits.get_plan_limits(request.plan)
                update_data["limits"] = {
                    **current_tenant.get("limits", {}),
                    **plan_limits,
                    **(request.limits or {}),
                }
            if request.status:
                update_data["status"] = request.status
            if request.settings:
                update_data["settings"] = {
                    **current_tenant.get("settings", {}),
                    **request.settings,
                }

            # Update tenant
            updated_tenant = await self.db_service.update_tenant(
                tenant_id,
                **update_data,
            )

            # Log update activity
            await self.db_service.log_tenant_activity(
                tenant_id=tenant_id,
                user_id=get_current_user_id(),
                activity_type="tenant_updated",
                activity_data={
                    "updated_fields": list(update_data.keys()),
                    "updated_by": get_current_user_id(),
                },
            )

            logger.info(f"✅ Updated tenant: {tenant_id}")

            return {"status": "success", "tenant": updated_tenant}

        except Exception as e:
            logger.error(f"Failed to update tenant {tenant_id}: {e}")
            raise

    async def delete_tenant(
        self,
        tenant_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete tenant and all associated data"""
        try:
            # Get tenant info for logging
            tenant = await self.db_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant not found: {tenant_id}")

            # Check if tenant can be deleted
            if not force and tenant["status"] == "active":
                # First suspend the tenant
                await self.db_service.update_tenant_status(tenant_id, "suspended")

                return {
                    "status": "suspended",
                    "message": "Tenant suspended. Use force=true to permanently delete.",
                }

            # Log deletion activity
            await self.db_service.log_tenant_activity(
                tenant_id=tenant_id,
                user_id=get_current_user_id(),
                activity_type="tenant_deleted",
                activity_data={
                    "tenant_name": tenant["name"],
                    "deleted_by": get_current_user_id(),
                    "force": force,
                },
            )

            # Mark tenant as deleted
            await self.db_service.update_tenant_status(tenant_id, "deleted")

            logger.info(f"✅ Deleted tenant: {tenant_id} ({tenant['name']})")

            return {
                "status": "success",
                "message": f"Tenant {tenant['name']} has been deleted",
            }

        except Exception as e:
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise

    async def list_tenants(
        self,
        status: str | None = None,
        plan: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List tenants with filtering and pagination"""
        try:
            tenants = await self.db_service.get_all_tenants(status, plan)

            # Apply pagination
            total_count = len(tenants)
            paginated_tenants = tenants[offset : offset + limit]

            # Add statistics for each tenant
            tenant_list = []
            for tenant in paginated_tenants:
                stats = await self._get_tenant_stats(tenant["id"])
                tenant_list.append({**tenant, "statistics": stats})

            return {
                "tenants": tenant_list,
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count,
                },
            }

        except Exception as e:
            logger.error(f"Failed to list tenants: {e}")
            raise

    async def create_user(
        self,
        tenant_id: str,
        request: UserCreationRequest,
    ) -> dict[str, Any]:
        """Create new user within tenant"""
        try:
            # Validate tenant exists and is active
            tenant = await self.db_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant not found: {tenant_id}")
            if tenant["status"] != "active":
                raise ValueError(f"Tenant is not active: {tenant['status']}")

            # Check user limits
            current_user_count = await self._get_user_count(tenant_id)
            plan_limits = TenantPlanLimits.get_plan_limits(tenant["plan"])
            if current_user_count >= plan_limits["max_users"]:
                raise ValueError(
                    f"User limit reached for {tenant['plan']} plan: {plan_limits['max_users']}",
                )

            # Check username uniqueness within tenant
            existing_user = await self.db_service.get_user_by_username(
                tenant_id,
                request.username,
            )
            if existing_user:
                raise ValueError(
                    f"Username already exists in tenant: {request.username}",
                )

            # Hash REDACTED_SECRET
            REDACTED_SECRET_hash = bcrypt.hashpw(
                request.REDACTED_SECRET.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

            # Create user
            user = await self.db_service.create_user(
                tenant_id=tenant_id,
                username=request.username,
                email=request.email,
                REDACTED_SECRET_hash=REDACTED_SECRET_hash,
                full_name=request.full_name,
                role=request.role,
            )

            # Log user creation
            await self.db_service.log_tenant_activity(
                tenant_id=tenant_id,
                user_id=get_current_user_id(),
                activity_type="user_created",
                activity_data={
                    "new_user_id": user["id"],
                    "new_user_username": user["username"],
                    "new_user_role": user["role"],
                    "created_by": get_current_user_id(),
                },
            )

            logger.info(f"✅ Created user: {request.username} in tenant {tenant_id}")

            return {
                "status": "success",
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                    "is_active": user["is_active"],
                },
            }

        except Exception as e:
            logger.error(f"Failed to create user in tenant {tenant_id}: {e}")
            raise

    async def get_tenant_users(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get users within tenant"""
        try:
            users = await self.db_service.get_tenant_users(tenant_id, limit, offset)

            return {"users": users, "pagination": {"limit": limit, "offset": offset}}

        except Exception as e:
            logger.error(f"Failed to get users for tenant {tenant_id}: {e}")
            raise

    async def get_tenant_analytics(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get comprehensive tenant analytics"""
        try:
            # Get search analytics
            search_analytics = await self.db_service.get_tenant_search_analytics(
                tenant_id,
                days,
            )

            # Get user activity
            user_count = await self._get_user_count(tenant_id)
            active_users = await self._get_active_user_count(tenant_id, days)

            # Get resource usage
            # This would integrate with actual resource monitoring
            resource_usage = {
                "cpu_usage_percent": 45.2,
                "memory_usage_percent": 62.1,
                "storage_usage_mb": 1234.5,
                "network_io_mb": 567.8,
            }

            # Get plan information
            tenant = await self.db_service.get_tenant_by_id(tenant_id)
            plan_limits = TenantPlanLimits.get_plan_limits(tenant["plan"])

            return {
                "tenant_id": tenant_id,
                "period_days": days,
                "search_analytics": search_analytics,
                "user_analytics": {
                    "total_users": user_count,
                    "active_users": active_users,
                    "user_limit": plan_limits["max_users"],
                },
                "resource_usage": resource_usage,
                "plan_limits": plan_limits,
            }

        except Exception as e:
            logger.error(f"Failed to get analytics for tenant {tenant_id}: {e}")
            raise

    # Helper methods

    def _generate_REDACTED_SECRET(self, length: int = 12) -> str:
        """Generate secure random REDACTED_SECRET"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        REDACTED_SECRET = "".join(secrets.choice(alphabet) for _ in range(length))
        return REDACTED_SECRET

    async def _get_tenant_stats(self, tenant_id: str) -> TenantStats:
        """Get tenant statistics"""
        try:
            # Get user count
            user_count = await self._get_user_count(tenant_id)

            # Get search count (last 30 days)
            search_analytics = await self.db_service.get_tenant_search_analytics(
                tenant_id,
                30,
            )
            search_count = search_analytics.get("total_searches", 0)

            # Mock additional stats (would be replaced with real monitoring)
            storage_usage_mb = 125.6
            api_calls_today = 234
            last_activity = datetime.utcnow() - timedelta(minutes=15)
            resource_utilization = {
                "cpu_percent": 45.2,
                "memory_percent": 62.1,
                "storage_percent": 12.3,
            }

            return TenantStats(
                tenant_id=tenant_id,
                user_count=user_count,
                search_count=search_count,
                storage_usage_mb=storage_usage_mb,
                api_calls_today=api_calls_today,
                last_activity=last_activity,
                resource_utilization=resource_utilization,
            )

        except Exception as e:
            logger.error(f"Failed to get stats for tenant {tenant_id}: {e}")
            # Return empty stats on error
            return TenantStats(
                tenant_id=tenant_id,
                user_count=0,
                search_count=0,
                storage_usage_mb=0.0,
                api_calls_today=0,
                last_activity=None,
                resource_utilization={},
            )

    async def _get_user_count(self, tenant_id: str) -> int:
        """Get user count for tenant"""
        users = await self.db_service.get_tenant_users(tenant_id, limit=1000)
        return len(users)

    async def _get_active_user_count(self, tenant_id: str, days: int) -> int:
        """Get active user count for tenant in last N days"""
        # This would query actual activity data
        # For now, return mock data
        total_users = await self._get_user_count(tenant_id)
        return max(1, int(total_users * 0.7))  # Assume 70% activity rate

    async def health_check(self) -> dict[str, Any]:
        """Health check for tenant management service"""
        try:
            # Test database connectivity
            db_health = await self.db_service.health_check()

            # Test basic operations
            test_tenant_count = len(await self.db_service.get_all_tenants())

            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database_health": db_health,
                "tenant_count": test_tenant_count,
                "service": "tenant_management",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "service": "tenant_management",
            }


# Factory function


async def create_tenant_management_service(
    db_service: MultiTenantPostgreSQLService,
) -> TenantManagementService:
    """Create tenant management service"""
    return TenantManagementService(db_service)


if __name__ == "__main__":
    # Example usage
    print("Tenant Management Service")
    print("=" * 50)
    print("Enterprise-grade tenant lifecycle management")
    print("Features:")
    print("- Multi-tenant provisioning")
    print("- User management within tenants")
    print("- Plan-based resource limits")
    print("- Activity tracking and analytics")
    print("- Security and compliance")
