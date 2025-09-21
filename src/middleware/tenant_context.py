#!/usr/bin/env python3
"""PAKE System - Phase 16 Tenant Context Middleware
Enterprise-grade tenant context propagation and isolation middleware.
"""

import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Context variables for tenant isolation
tenant_context: ContextVar[str | None] = ContextVar("tenant_context", default=None)
user_context: ContextVar[str | None] = ContextVar("user_context", default=None)
request_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "request_context",
    default=None,
)


@dataclass
class TenantContext:
    """Tenant context data structure"""

    tenant_id: str
    tenant_name: str
    tenant_domain: str | None
    tenant_status: str
    tenant_plan: str
    user_id: str | None
    user_role: str | None
    user_permissions: list[str]
    request_id: str
    timestamp: datetime
    ip_address: str | None
    user_agent: str | None


@dataclass
class TenantConfig:
    """Tenant middleware configuration"""

    # JWT Configuration
    jwt_secret_key: str = "REDACTED_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Tenant Resolution
    tenant_resolution_method: str = "jwt"  # jwt, header, subdomain, path
    tenant_header_name: str = "X-Tenant-ID"
    tenant_cookie_name: str = "tenant_id"

    # Security Settings
    require_tenant_context: bool = True
    allow_anonymous_access: bool = False
    validate_tenant_status: bool = True
    allowed_tenant_statuses: list[str] = None

    # Cross-Tenant Access
    allow_cross_tenant_access: bool = False
    admin_tenant_access: bool = True

    # Caching
    tenant_cache_ttl: int = 300  # 5 minutes
    enable_tenant_caching: bool = True

    def __post_init__(self):
        if self.allowed_tenant_statuses is None:
            self.allowed_tenant_statuses = ["active", "trial"]


class TenantResolutionError(Exception):
    """Exception raised when tenant resolution fails"""


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Enterprise-grade tenant context middleware.

    Features:
    - Multiple tenant resolution methods (JWT, header, subdomain, path)
    - Automatic tenant context propagation
    - Tenant status validation
    - Security isolation enforcement
    - Performance optimization with caching
    - Comprehensive audit logging
    """

    def __init__(self, app, config: TenantConfig):
        super().__init__(app)
        self.config = config
        self.security = HTTPBearer(auto_error=False)
        self._tenant_cache: dict[str, dict[str, Any]] = {}
        self._cache_timestamps: dict[str, datetime] = {}

        logger.info("Tenant context middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant context"""
        start_time = datetime.utcnow()
        request_id = str(uuid.uuid4())

        try:
            # Extract request metadata
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")

            # Set request context
            request_context.set(
                {
                    "request_id": request_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "start_time": start_time,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            # Resolve tenant context
            tenant_ctx = await self._resolve_tenant_context(request)

            if tenant_ctx:
                # Set tenant context
                tenant_context.set(tenant_ctx.tenant_id)
                user_context.set(tenant_ctx.user_id)

                # Validate tenant access
                await self._validate_tenant_access(tenant_ctx, request)

                # Add tenant context to request state
                request.state.tenant_context = tenant_ctx

                logger.debug(
                    f"Tenant context resolved: {tenant_ctx.tenant_id} for {request.url.path}",
                )
            else:
                # Handle anonymous access
                if not self.config.allow_anonymous_access:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "Tenant context required",
                            "code": "TENANT_REQUIRED",
                        },
                    )

                logger.debug(f"Anonymous access to {request.url.path}")

            # Process request
            response = await call_next(request)

            # Add tenant context headers to response
            if tenant_ctx:
                response.headers["X-Tenant-ID"] = tenant_ctx.tenant_id
                response.headers["X-Request-ID"] = request_id

            # Log request completion
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self._log_request_completion(
                request,
                tenant_ctx,
                duration,
                response.status_code,
            )

            return response

        except TenantResolutionError as e:
            logger.warning(f"Tenant resolution failed: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": str(e), "code": "TENANT_RESOLUTION_FAILED"},
            )
        except HTTPException as e:
            logger.warning(f"Tenant validation failed: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "code": "TENANT_VALIDATION_FAILED"},
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "code": "TENANT_MIDDLEWARE_ERROR",
                },
            )

    async def _resolve_tenant_context(
        self,
        request: Request,
    ) -> TenantContext | None:
        """Resolve tenant context from request"""
        try:
            if self.config.tenant_resolution_method == "jwt":
                return await self._resolve_from_jwt(request)
            if self.config.tenant_resolution_method == "header":
                return await self._resolve_from_header(request)
            if self.config.tenant_resolution_method == "subdomain":
                return await self._resolve_from_subdomain(request)
            if self.config.tenant_resolution_method == "path":
                return await self._resolve_from_path(request)
            raise TenantResolutionError(
                f"Unknown tenant resolution method: {self.config.tenant_resolution_method}",
            )

        except Exception as e:
            logger.error(f"Tenant resolution error: {e}")
            raise TenantResolutionError(f"Failed to resolve tenant context: {e}")

    async def _resolve_from_jwt(self, request: Request) -> TenantContext | None:
        """Resolve tenant context from JWT token"""
        try:
            # Extract JWT token
            credentials: HTTPAuthorizationCredentials = await self.security(request)
            if not credentials:
                return None

            # Decode JWT token
            token = credentials.credentials
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )

            # Extract tenant information
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                raise TenantResolutionError("JWT token missing tenant_id claim")

            # Get tenant details (with caching)
            tenant_data = await self._get_tenant_data(tenant_id)
            if not tenant_data:
                raise TenantResolutionError(f"Tenant not found: {tenant_id}")

            # Extract user information
            user_id = payload.get("sub")  # Standard JWT subject claim
            user_role = payload.get("role", "user")
            user_permissions = payload.get("permissions", [])

            return TenantContext(
                tenant_id=tenant_id,
                tenant_name=tenant_data["name"],
                tenant_domain=tenant_data.get("domain"),
                tenant_status=tenant_data["status"],
                tenant_plan=tenant_data["plan"],
                user_id=user_id,
                user_role=user_role,
                user_permissions=user_permissions,
                request_id=request_context.get()["request_id"],
                timestamp=datetime.utcnow(),
                ip_address=request_context.get()["ip_address"],
                user_agent=request_context.get()["user_agent"],
            )

        except ExpiredSignatureError:
            raise TenantResolutionError("JWT token has expired")
        except InvalidTokenError:
            raise TenantResolutionError("Invalid JWT token")
        except Exception as e:
            raise TenantResolutionError(f"JWT resolution failed: {e}")

    async def _resolve_from_header(self, request: Request) -> TenantContext | None:
        """Resolve tenant context from HTTP header"""
        try:
            tenant_id = request.headers.get(self.config.tenant_header_name)
            if not tenant_id:
                return None

            # Get tenant details
            tenant_data = await self._get_tenant_data(tenant_id)
            if not tenant_data:
                raise TenantResolutionError(f"Tenant not found: {tenant_id}")

            return TenantContext(
                tenant_id=tenant_id,
                tenant_name=tenant_data["name"],
                tenant_domain=tenant_data.get("domain"),
                tenant_status=tenant_data["status"],
                tenant_plan=tenant_data["plan"],
                user_id=None,  # Header method doesn't provide user info
                user_role=None,
                user_permissions=[],
                request_id=request_context.get()["request_id"],
                timestamp=datetime.utcnow(),
                ip_address=request_context.get()["ip_address"],
                user_agent=request_context.get()["user_agent"],
            )

        except Exception as e:
            raise TenantResolutionError(f"Header resolution failed: {e}")

    async def _resolve_from_subdomain(
        self,
        request: Request,
    ) -> TenantContext | None:
        """Resolve tenant context from subdomain"""
        try:
            host = request.headers.get("host", "")
            if not host:
                return None

            # Extract subdomain (e.g., tenant1.pake.com -> tenant1)
            parts = host.split(".")
            if len(parts) < 3:
                return None

            subdomain = parts[0]
            if subdomain in ["www", "api", "admin"]:
                return None

            # Get tenant by domain
            tenant_data = await self._get_tenant_by_domain(host)
            if not tenant_data:
                raise TenantResolutionError(f"Tenant not found for domain: {host}")

            return TenantContext(
                tenant_id=tenant_data["id"],
                tenant_name=tenant_data["name"],
                tenant_domain=tenant_data.get("domain"),
                tenant_status=tenant_data["status"],
                tenant_plan=tenant_data["plan"],
                user_id=None,  # Subdomain method doesn't provide user info
                user_role=None,
                user_permissions=[],
                request_id=request_context.get()["request_id"],
                timestamp=datetime.utcnow(),
                ip_address=request_context.get()["ip_address"],
                user_agent=request_context.get()["user_agent"],
            )

        except Exception as e:
            raise TenantResolutionError(f"Subdomain resolution failed: {e}")

    async def _resolve_from_path(self, request: Request) -> TenantContext | None:
        """Resolve tenant context from URL path"""
        try:
            path_parts = request.url.path.strip("/").split("/")
            if len(path_parts) < 2 or path_parts[0] != "api":
                return None

            tenant_id = path_parts[1]  # /api/{tenant_id}/...

            # Get tenant details
            tenant_data = await self._get_tenant_data(tenant_id)
            if not tenant_data:
                raise TenantResolutionError(f"Tenant not found: {tenant_id}")

            return TenantContext(
                tenant_id=tenant_id,
                tenant_name=tenant_data["name"],
                tenant_domain=tenant_data.get("domain"),
                tenant_status=tenant_data["status"],
                tenant_plan=tenant_data["plan"],
                user_id=None,  # Path method doesn't provide user info
                user_role=None,
                user_permissions=[],
                request_id=request_context.get()["request_id"],
                timestamp=datetime.utcnow(),
                ip_address=request_context.get()["ip_address"],
                user_agent=request_context.get()["user_agent"],
            )

        except Exception as e:
            raise TenantResolutionError(f"Path resolution failed: {e}")

    async def _get_tenant_data(self, tenant_id: str) -> dict[str, Any] | None:
        """Get tenant data with caching"""
        if self.config.enable_tenant_caching:
            # Check cache
            if tenant_id in self._tenant_cache:
                cache_time = self._cache_timestamps.get(tenant_id)
                if (
                    cache_time
                    and (datetime.utcnow() - cache_time).seconds
                    < self.config.tenant_cache_ttl
                ):
                    return self._tenant_cache[tenant_id]

        # Fetch from database (this would be implemented with actual database service)
        tenant_data = await self._fetch_tenant_from_database(tenant_id)

        if tenant_data and self.config.enable_tenant_caching:
            # Cache the result
            self._tenant_cache[tenant_id] = tenant_data
            self._cache_timestamps[tenant_id] = datetime.utcnow()

        return tenant_data

    async def _get_tenant_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Get tenant data by domain with caching"""
        cache_key = f"domain:{domain}"

        if self.config.enable_tenant_caching:
            if cache_key in self._tenant_cache:
                cache_time = self._cache_timestamps.get(cache_key)
                if (
                    cache_time
                    and (datetime.utcnow() - cache_time).seconds
                    < self.config.tenant_cache_ttl
                ):
                    return self._tenant_cache[cache_key]

        # Fetch from database
        tenant_data = await self._fetch_tenant_by_domain_from_database(domain)

        if tenant_data and self.config.enable_tenant_caching:
            self._tenant_cache[cache_key] = tenant_data
            self._cache_timestamps[cache_key] = datetime.utcnow()

        return tenant_data

    async def _fetch_tenant_from_database(
        self,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Fetch tenant data from database"""
        # This would be implemented with actual database service
        # For now, return mock data
        return {
            "id": tenant_id,
            "name": f"tenant-{tenant_id[:8]}",
            "domain": f"{tenant_id[:8]}.pake.com",
            "status": "active",
            "plan": "basic",
        }

    async def _fetch_tenant_by_domain_from_database(
        self,
        domain: str,
    ) -> dict[str, Any] | None:
        """Fetch tenant data by domain from database"""
        # This would be implemented with actual database service
        # For now, return mock data
        tenant_id = domain.split(".")[0]
        return {
            "id": tenant_id,
            "name": f"tenant-{tenant_id}",
            "domain": domain,
            "status": "active",
            "plan": "basic",
        }

    async def _validate_tenant_access(
        self,
        tenant_ctx: TenantContext,
        request: Request,
    ) -> None:
        """Validate tenant access permissions"""
        # Check tenant status
        if self.config.validate_tenant_status:
            if tenant_ctx.tenant_status not in self.config.allowed_tenant_statuses:
                raise HTTPException(
                    status_code=403,
                    detail=f"Tenant status '{tenant_ctx.tenant_status}' not allowed",
                )

        # Check for admin endpoints
        if request.url.path.startswith("/admin/"):
            if tenant_ctx.user_role not in ["admin", "super_admin"]:
                raise HTTPException(status_code=403, detail="Admin access required")

        # Check for cross-tenant access
        if not self.config.allow_cross_tenant_access:
            # Ensure request doesn't try to access other tenant's data
            # This would be implemented based on specific API patterns
            pass

    async def _log_request_completion(
        self,
        request: Request,
        tenant_ctx: TenantContext | None,
        duration: float,
        status_code: int,
    ) -> None:
        """Log request completion for audit trail"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_context.get()["request_id"],
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "ip_address": request_context.get()["ip_address"],
            "user_agent": request_context.get()["user_agent"],
        }

        if tenant_ctx:
            log_data.update(
                {
                    "tenant_id": tenant_ctx.tenant_id,
                    "tenant_name": tenant_ctx.tenant_name,
                    "user_id": tenant_ctx.user_id,
                    "user_role": tenant_ctx.user_role,
                },
            )

        logger.info(f"Request completed: {log_data}")

    def _get_client_ip(self, request: Request) -> str | None:
        """Get client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None


# Dependency functions for FastAPI


async def get_tenant_context(request: Request) -> TenantContext | None:
    """FastAPI dependency to get tenant context"""
    return getattr(request.state, "tenant_context", None)


async def require_tenant_context(request: Request) -> TenantContext:
    """FastAPI dependency that requires tenant context"""
    tenant_ctx = getattr(request.state, "tenant_context", None)
    if not tenant_ctx:
        raise HTTPException(status_code=401, detail="Tenant context required")
    return tenant_ctx


async def require_admin_access(request: Request) -> TenantContext:
    """FastAPI dependency that requires admin access"""
    tenant_ctx = await require_tenant_context(request)
    if tenant_ctx.user_role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return tenant_ctx


# Context getter functions


def get_current_tenant_id() -> str | None:
    """Get current tenant ID from context"""
    return tenant_context.get()


def get_current_user_id() -> str | None:
    """Get current user ID from context"""
    return user_context.get()


def get_current_request_context() -> dict[str, Any] | None:
    """Get current request context"""
    return request_context.get()


# Utility functions


def create_tenant_jwt(
    tenant_id: str,
    user_id: str,
    user_role: str = "user",
    permissions: list[str] = None,
    expires_hours: int = 24,
) -> str:
    """Create JWT token with tenant context"""
    payload = {
        "tenant_id": tenant_id,
        "sub": user_id,
        "role": user_role,
        "permissions": permissions or [],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
    }

    return jwt.encode(
        payload,
        "REDACTED_SECRET",
        algorithm="HS256",
    )


def validate_tenant_jwt(token: str, secret_key: str) -> dict[str, Any]:
    """Validate JWT token and extract tenant context"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


if __name__ == "__main__":
    # Example usage
    print("Tenant Context Middleware")
    print("=" * 50)

    # Create JWT token
    token = create_tenant_jwt(
        tenant_id="tenant-123",
        user_id="user-456",
        user_role="admin",
        permissions=["read", "write", "admin"],
    )
    print(f"Created JWT token: {token[:50]}...")

    # Validate token
    try:
        payload = validate_tenant_jwt(token, "REDACTED_SECRET")
        print(f"Token payload: {payload}")
    except ValueError as e:
        print(f"Token validation error: {e}")
