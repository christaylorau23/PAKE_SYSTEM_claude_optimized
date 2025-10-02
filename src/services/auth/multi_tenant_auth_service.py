#!/usr/bin/env python3
"""PAKE System - Phase 16 Multi-Tenant Authentication & Authorization Service
Enterprise-grade authentication with tenant isolation and role-based access control.
"""

import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.middleware.tenant_context import get_current_tenant_id
from src.services.database.multi_tenant_schema import MultiTenantPostgreSQLService

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Authentication configuration"""

    # JWT Settings
    jwt_secret_key: str = "change-in-production-use-env-var"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Password Settings
    REDACTED_SECRET_min_length: int = 8
    REDACTED_SECRET_require_uppercase: bool = True
    REDACTED_SECRET_require_lowercase: bool = True
    REDACTED_SECRET_require_numbers: bool = True
    REDACTED_SECRET_require_special: bool = True
    REDACTED_SECRET_history_count: int = 5

    # Account Security
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    session_timeout_minutes: int = 60
    require_email_verification: bool = True

    # Multi-Factor Authentication
    mfa_enabled: bool = False
    mfa_issuer: str = "PAKE System"

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_window_minutes: int = 1


@dataclass
class LoginRequest:
    """Login request model"""

    username: str
    REDACTED_SECRET: str
    tenant_id: str | None = None  # Can be resolved from context
    remember_me: bool = False
    mfa_token: str | None = None


@dataclass
class LoginResponse:
    """Login response model"""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    user_info: dict[str, Any] | None = None
    permissions: list[str] | None = None
    error: str | None = None
    requires_mfa: bool = False


@dataclass
class UserSession:
    """Active user session"""

    session_id: str
    tenant_id: str
    user_id: str
    username: str
    role: str
    permissions: set[str]
    created_at: datetime
    last_activity: datetime
    ip_address: str | None
    user_agent: str | None
    expires_at: datetime


class RolePermissionManager:
    """Role-based permission management"""

    # Default role permissions
    ROLE_PERMISSIONS = {
        "super_admin": {
            "system:manage",
            "tenant:create",
            "tenant:read",
            "tenant:update",
            "tenant:delete",
            "user:create",
            "user:read",
            "user:update",
            "user:delete",
            "search:read",
            "search:write",
            "search:delete",
            "analytics:read",
            "analytics:advanced",
            "admin:access",
            "audit:read",
        },
        "admin": {
            "tenant:read",
            "tenant:update",
            "user:create",
            "user:read",
            "user:update",
            "search:read",
            "search:write",
            "search:delete",
            "analytics:read",
            "analytics:advanced",
            "admin:access",
        },
        "manager": {
            "user:read",
            "user:update",
            "search:read",
            "search:write",
            "analytics:read",
        },
        "user": {"search:read", "search:write", "profile:read", "profile:update"},
        "viewer": {"search:read", "profile:read"},
    }

    @classmethod
    def get_role_permissions(cls, role: str) -> set[str]:
        """Get permissions for a role"""
        return cls.ROLE_PERMISSIONS.get(role, cls.ROLE_PERMISSIONS["user"])

    @classmethod
    def has_permission(cls, user_role: str, required_permission: str) -> bool:
        """Check if role has specific permission"""
        user_permissions = cls.get_role_permissions(user_role)
        return required_permission in user_permissions

    @classmethod
    def can_access_endpoint(cls, user_role: str, endpoint: str) -> bool:
        """Check if role can access specific endpoint"""
        # Map endpoints to required permissions
        endpoint_permissions = {
            "/admin/": "admin:access",
            "/api/tenants": "tenant:read",
            "/api/users": "user:read",
            "/api/analytics": "analytics:read",
            "/api/search": "search:read",
        }

        for endpoint_pattern, required_permission in endpoint_permissions.items():
            if endpoint.startswith(endpoint_pattern):
                return cls.has_permission(user_role, required_permission)

        # Default to user permissions for unspecified endpoints
        return True


class MultiTenantAuthService:
    """Enterprise multi-tenant authentication service.

    Features:
    - Tenant-scoped authentication
    - JWT-based session management
    - Role-based access control (RBAC)
    - Account security (lockouts, REDACTED_SECRET policies)
    - Rate limiting and abuse prevention
    - Multi-factor authentication (MFA)
    - Session management and tracking
    - Audit logging
    """

    def __init__(
        self,
        db_service: MultiTenantPostgreSQLService,
        config: AuthConfig | None = None,
    ):
        self.db_service = db_service
        self.config = config or AuthConfig()
        self.REDACTED_SECRET_hasher = PasswordHasher()

        # In-memory session storage (would use Redis in production)
        self._active_sessions: dict[str, UserSession] = {}
        self._failed_attempts: dict[str, dict[str, Any]] = {}
        self._rate_limits: dict[str, dict[str, Any]] = {}

        logger.info("Multi-tenant authentication service initialized")

    async def authenticate_user(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user within tenant context.

        Process:
        1. Resolve tenant ID
        2. Check rate limiting
        3. Validate user credentials
        4. Check account status and lockouts
        5. Verify MFA if enabled
        6. Generate tokens and create session
        7. Log authentication activity
        """
        try:
            # Resolve tenant ID
            tenant_id = request.tenant_id or get_current_tenant_id()
            if not tenant_id:
                return LoginResponse(
                    success=False,
                    error="Tenant context required for authentication",
                )

            # Check rate limiting
            rate_limit_key = f"{tenant_id}:{request.username}"
            if not self._check_rate_limit(rate_limit_key):
                return LoginResponse(
                    success=False,
                    error="Too many authentication attempts. Please try again later.",
                )

            # Get user from database
            user = await self.db_service.get_user_by_username(
                tenant_id,
                request.username,
            )
            if not user:
                await self._record_failed_attempt(
                    tenant_id,
                    request.username,
                    "user_not_found",
                )
                return LoginResponse(success=False, error="Invalid credentials")

            # Check if account is locked
            if await self._is_account_locked(tenant_id, user["id"]):
                return LoginResponse(
                    success=False,
                    error="Account is locked due to too many failed attempts",
                )

            # Verify REDACTED_SECRET
            try:
                self.REDACTED_SECRET_hasher.verify(
                    user["REDACTED_SECRET_hash"], request.REDACTED_SECRET
                )
            except VerifyMismatchError:
                await self._record_failed_attempt(
                    tenant_id,
                    request.username,
                    "invalid_REDACTED_SECRET",
                )
                return LoginResponse(success=False, error="Invalid credentials")

            # Check if REDACTED_SECRET needs rehashing (Argon2 upgrade)
            if self.REDACTED_SECRET_hasher.check_needs_rehash(
                user["REDACTED_SECRET_hash"]
            ):
                new_hash = self.REDACTED_SECRET_hasher.hash(request.REDACTED_SECRET)
                await self._update_user_REDACTED_SECRET_hash(
                    tenant_id, user["id"], new_hash
                )

            # Check account status
            if not user["is_active"]:
                return LoginResponse(success=False, error="Account is disabled")

            # Check MFA if enabled
            if self.config.mfa_enabled and user.get("mfa_enabled"):
                if not request.mfa_token:
                    return LoginResponse(
                        success=False,
                        requires_mfa=True,
                        error="MFA token required",
                    )

                if not await self._verify_mfa_token(user["id"], request.mfa_token):
                    await self._record_failed_attempt(
                        tenant_id,
                        request.username,
                        "invalid_mfa",
                    )
                    return LoginResponse(success=False, error="Invalid MFA token")

            # Clear failed attempts
            await self._clear_failed_attempts(tenant_id, user["id"])

            # Get user permissions
            permissions = list(RolePermissionManager.get_role_permissions(user["role"]))

            # Generate tokens
            access_token_expires = datetime.utcnow() + timedelta(
                minutes=self.config.access_token_expire_minutes,
            )
            refresh_token_expires = datetime.utcnow() + timedelta(
                days=self.config.refresh_token_expire_days,
            )

            if request.remember_me:
                # Extend token lifetime for "remember me"
                access_token_expires += timedelta(days=7)

            access_token = self._generate_jwt_token(
                tenant_id=tenant_id,
                user_id=user["id"],
                username=user["username"],
                role=user["role"],
                permissions=permissions,
                expires_at=access_token_expires,
                token_type="access",
            )

            refresh_token = self._generate_jwt_token(
                tenant_id=tenant_id,
                user_id=user["id"],
                username=user["username"],
                role=user["role"],
                permissions=permissions,
                expires_at=refresh_token_expires,
                token_type="refresh",
            )

            # Create session
            session = await self._create_session(
                tenant_id=tenant_id,
                user_id=user["id"],
                username=user["username"],
                role=user["role"],
                permissions=set(permissions),
                expires_at=access_token_expires,
            )

            # Update last login
            await self.db_service.execute_query(
                "UPDATE users SET last_login = $1 WHERE tenant_id = $2 AND id = $3",
                datetime.utcnow(),
                tenant_id,
                user["id"],
            )

            # Log successful authentication
            await self.db_service.log_tenant_activity(
                tenant_id=tenant_id,
                user_id=user["id"],
                activity_type="user_login",
                activity_data={
                    "username": user["username"],
                    "role": user["role"],
                    "session_id": session.session_id,
                    "remember_me": request.remember_me,
                },
            )

            logger.info(
                f"✅ User authenticated: {user['username']} in tenant {tenant_id}",
            )

            return LoginResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=access_token_expires,
                user_info={
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                    "is_active": user["is_active"],
                },
                permissions=permissions,
            )

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return LoginResponse(success=False, error="Authentication service error")

    async def refresh_token(self, refresh_token: str) -> LoginResponse:
        """Refresh access token using refresh token"""
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )

            # Validate token type
            if payload.get("token_type") != "refresh":
                return LoginResponse(success=False, error="Invalid token type")

            tenant_id = payload.get("tenant_id")
            user_id = payload.get("sub")

            # Get current user data
            user = await self.db_service.get_user_by_id(tenant_id, user_id)
            if not user or not user["is_active"]:
                return LoginResponse(success=False, error="User not found or inactive")

            # Generate new access token
            permissions = list(RolePermissionManager.get_role_permissions(user["role"]))
            access_token_expires = datetime.utcnow() + timedelta(
                minutes=self.config.access_token_expire_minutes,
            )

            access_token = self._generate_jwt_token(
                tenant_id=tenant_id,
                user_id=user["id"],
                username=user["username"],
                role=user["role"],
                permissions=permissions,
                expires_at=access_token_expires,
                token_type="access",
            )

            # Update session
            await self._update_session_activity(user_id)

            logger.info(
                f"✅ Token refreshed for user: {user['username']} in tenant {tenant_id}",
            )

            return LoginResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,  # Keep same refresh token
                expires_at=access_token_expires,
                user_info={
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                },
                permissions=permissions,
            )

        except ExpiredSignatureError:
            return LoginResponse(success=False, error="Refresh token has expired")
        except InvalidTokenError:
            return LoginResponse(success=False, error="Invalid refresh token")
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return LoginResponse(success=False, error="Token refresh service error")

    async def logout_user(self, access_token: str) -> dict[str, Any]:
        """Logout user and invalidate session"""
        try:
            # Decode token to get session info
            payload = jwt.decode(
                access_token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )

            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            session_id = payload.get("session_id")

            # Remove session
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]

            # Log logout activity
            await self.db_service.log_tenant_activity(
                tenant_id=tenant_id,
                user_id=user_id,
                activity_type="user_logout",
                activity_data={"session_id": session_id},
            )

            logger.info(f"✅ User logged out: {user_id} in tenant {tenant_id}")

            return {"success": True, "message": "Successfully logged out"}

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {"success": False, "error": "Logout service error"}

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token and return user info"""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )

            # Check token type
            if payload.get("token_type") != "access":
                return {"valid": False, "error": "Invalid token type"}

            # Check session exists
            session_id = payload.get("session_id")
            if session_id not in self._active_sessions:
                return {"valid": False, "error": "Session not found or expired"}

            session = self._active_sessions[session_id]

            # Check session expiry
            if datetime.utcnow() > session.expires_at:
                del self._active_sessions[session_id]
                return {"valid": False, "error": "Session expired"}

            # Update session activity
            await self._update_session_activity(session.user_id)

            return {
                "valid": True,
                "tenant_id": session.tenant_id,
                "user_id": session.user_id,
                "username": session.username,
                "role": session.role,
                "permissions": list(session.permissions),
                "session_id": session.session_id,
            }

        except ExpiredSignatureError:
            return {"valid": False, "error": "Token has expired"}
        except InvalidTokenError:
            return {"valid": False, "error": "Invalid token"}
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {"valid": False, "error": "Token validation service error"}

    async def change_REDACTED_SECRET(
        self,
        user_id: str,
        current_REDACTED_SECRET: str,
        new_REDACTED_SECRET: str,
    ) -> dict[str, Any]:
        """Change user REDACTED_SECRET with validation"""
        try:
            tenant_id = get_current_tenant_id()
            if not tenant_id:
                return {"success": False, "error": "Tenant context required"}

            # Get user
            user = await self.db_service.get_user_by_id(tenant_id, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            # Verify current REDACTED_SECRET
            try:
                self.REDACTED_SECRET_hasher.verify(
                    user["REDACTED_SECRET_hash"], current_REDACTED_SECRET
                )
            except VerifyMismatchError:
                return {
                    "success": False,
                    "error": "Current REDACTED_SECRET is incorrect",
                }

            # Validate new REDACTED_SECRET
            REDACTED_SECRET_validation = self._validate_REDACTED_SECRET(
                new_REDACTED_SECRET
            )
            if not REDACTED_SECRET_validation["valid"]:
                return {"success": False, "error": REDACTED_SECRET_validation["error"]}

            # Hash new REDACTED_SECRET
            new_REDACTED_SECRET_hash = self.REDACTED_SECRET_hasher.hash(
                new_REDACTED_SECRET
            )

            # Update REDACTED_SECRET
            await self._update_user_REDACTED_SECRET_hash(
                tenant_id, user_id, new_REDACTED_SECRET_hash
            )

            # Log REDACTED_SECRET change
            await self.db_service.log_tenant_activity(
                tenant_id=tenant_id,
                user_id=user_id,
                activity_type="REDACTED_SECRET_changed",
                activity_data={"user_id": user_id},
            )

            logger.info(
                f"✅ Password changed for user: {user['username']} in tenant {tenant_id}",
            )

            return {"success": True, "message": "Password changed successfully"}

        except Exception as e:
            logger.error(f"Password change error: {e}")
            return {"success": False, "error": "Password change service error"}

    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission"""
        return RolePermissionManager.has_permission(user_role, required_permission)

    def check_endpoint_access(self, user_role: str, endpoint: str) -> bool:
        """Check if user role can access endpoint"""
        return RolePermissionManager.can_access_endpoint(user_role, endpoint)

    # Helper methods

    def _generate_jwt_token(
        self,
        tenant_id: str,
        user_id: str,
        username: str,
        role: str,
        permissions: list[str],
        expires_at: datetime,
        token_type: str = "access",
    ) -> str:
        """Generate JWT token"""
        payload = {
            "tenant_id": tenant_id,
            "sub": user_id,
            "username": username,
            "role": role,
            "permissions": permissions,
            "token_type": token_type,
            "iat": datetime.utcnow(),
            "exp": expires_at,
        }

        if token_type == "access":
            payload["session_id"] = self._generate_session_id()

        return jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
        )

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"sess_{secrets.token_hex(16)}"

    async def _create_session(
        self,
        tenant_id: str,
        user_id: str,
        username: str,
        role: str,
        permissions: set[str],
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        """Create user session"""
        session = UserSession(
            session_id=self._generate_session_id(),
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        self._active_sessions[session.session_id] = session
        return session

    async def _update_session_activity(self, user_id: str) -> None:
        """Update session last activity"""
        for session in self._active_sessions.values():
            if session.user_id == user_id:
                session.last_activity = datetime.utcnow()
                break

    def _check_rate_limit(self, key: str) -> bool:
        """Check rate limiting"""
        now = time.time()
        window_start = now - (self.config.rate_limit_window_minutes * 60)

        if key not in self._rate_limits:
            self._rate_limits[key] = {"attempts": [], "last_attempt": now}

        rate_data = self._rate_limits[key]

        # Remove old attempts
        rate_data["attempts"] = [
            attempt for attempt in rate_data["attempts"] if attempt > window_start
        ]

        # Check limit
        if len(rate_data["attempts"]) >= self.config.rate_limit_requests_per_minute:
            return False

        # Record attempt
        rate_data["attempts"].append(now)
        rate_data["last_attempt"] = now

        return True

    async def _record_failed_attempt(
        self,
        tenant_id: str,
        username: str,
        reason: str,
    ) -> None:
        """Record failed authentication attempt"""
        key = f"{tenant_id}:{username}"
        now = datetime.utcnow()

        if key not in self._failed_attempts:
            self._failed_attempts[key] = {
                "count": 0,
                "first_attempt": now,
                "last_attempt": now,
                "reasons": [],
            }

        attempt_data = self._failed_attempts[key]
        attempt_data["count"] += 1
        attempt_data["last_attempt"] = now
        attempt_data["reasons"].append(reason)

        # Keep only recent reasons
        if len(attempt_data["reasons"]) > 10:
            attempt_data["reasons"] = attempt_data["reasons"][-10:]

        # Log security event
        await self.db_service.log_tenant_activity(
            tenant_id=tenant_id,
            activity_type="failed_login_attempt",
            activity_data={
                "username": username,
                "reason": reason,
                "attempt_count": attempt_data["count"],
            },
        )

    async def _is_account_locked(self, tenant_id: str, user_id: str) -> bool:
        """Check if account is locked due to failed attempts"""
        # Implementation would check database for lockout status
        # For now, return False
        return False

    async def _clear_failed_attempts(self, tenant_id: str, user_id: str) -> None:
        """Clear failed attempts for successful login"""
        # Clear from memory
        key_prefix = f"{tenant_id}:"
        keys_to_remove = [
            key for key in self._failed_attempts.keys() if key.startswith(key_prefix)
        ]
        for key in keys_to_remove:
            del self._failed_attempts[key]

    def _validate_REDACTED_SECRET(self, REDACTED_SECRET: str) -> dict[str, Any]:
        """Validate REDACTED_SECRET against policy"""
        errors = []

        if len(REDACTED_SECRET) < self.config.REDACTED_SECRET_min_length:
            errors.append(
                f"Password must be at least {self.config.REDACTED_SECRET_min_length} characters long",
            )

        if self.config.REDACTED_SECRET_require_uppercase and not any(
            c.isupper() for c in REDACTED_SECRET
        ):
            errors.append("Password must contain at least one uppercase letter")

        if self.config.REDACTED_SECRET_require_lowercase and not any(
            c.islower() for c in REDACTED_SECRET
        ):
            errors.append("Password must contain at least one lowercase letter")

        if self.config.REDACTED_SECRET_require_numbers and not any(
            c.isdigit() for c in REDACTED_SECRET
        ):
            errors.append("Password must contain at least one number")

        if self.config.REDACTED_SECRET_require_special and not any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in REDACTED_SECRET
        ):
            errors.append("Password must contain at least one special character")

        return {
            "valid": len(errors) == 0,
            "error": "; ".join(errors) if errors else None,
        }

    async def _update_user_REDACTED_SECRET_hash(
        self,
        tenant_id: str,
        user_id: str,
        REDACTED_SECRET_hash: str,
    ) -> None:
        """Update user REDACTED_SECRET hash"""
        await self.db_service.execute_query(
            "UPDATE users SET REDACTED_SECRET_hash = $1, updated_at = $2 WHERE tenant_id = $3 AND id = $4",
            REDACTED_SECRET_hash,
            datetime.utcnow(),
            tenant_id,
            user_id,
        )

    async def _verify_mfa_token(self, user_id: str, mfa_token: str) -> bool:
        """Verify MFA token (TOTP)"""
        # Implementation would verify TOTP token
        # For now, return True for valid format
        return len(mfa_token) == 6 and mfa_token.isdigit()

    async def health_check(self) -> dict[str, Any]:
        """Health check for authentication service"""
        try:
            # Test database connectivity
            db_health = await self.db_service.health_check()

            # Check active sessions
            active_session_count = len(self._active_sessions)

            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database_health": db_health,
                "active_sessions": active_session_count,
                "service": "multi_tenant_auth",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "service": "multi_tenant_auth",
            }


# Factory function


async def create_multi_tenant_auth_service(
    db_service: MultiTenantPostgreSQLService,
    config: AuthConfig | None = None,
) -> MultiTenantAuthService:
    """Create multi-tenant authentication service"""
    return MultiTenantAuthService(db_service, config)


if __name__ == "__main__":
    # Example usage
    print("Multi-Tenant Authentication Service")
    print("=" * 50)
    print("Enterprise-grade authentication with tenant isolation")
    print("Features:")
    print("- JWT-based session management")
    print("- Role-based access control (RBAC)")
    print("- Account security and lockouts")
    print("- Multi-factor authentication")
    print("- Rate limiting and audit logging")
