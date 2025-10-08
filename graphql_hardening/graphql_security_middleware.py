#!/usr/bin/env python3
"""GraphQL Security Middleware Template
World-Class Finish Guide - Security hardening for GraphQL APIs.
"""

from dataclasses import dataclass
from functools import wraps
import time
from typing import Any, Dict, List, Optional


@dataclass
class SecurityContext:
    """Security context for GraphQL operations."""

    user_id: Optional[str] = None
    user_role: Optional[str] = None
    permissions: list[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: float = 0.0


class GraphQLSecurityMiddleware:
    """Security middleware for GraphQL operations."""

    def __init__(self):
        self.rate_limits = {}  # In production, use Redis
        self.permission_map = {
            "user.create": ["admin", "user_manager"],
            "user.read": ["admin", "user_manager", "user"],
            "user.update": ["admin", "user_manager"],
            "user.delete": ["admin"],
        }

    def authenticate(self, token: Optional[str]) -> Optional[SecurityContext]:
        """Authenticate user and return security context."""
        if not token:
            return None

        # In production, validate JWT token
        # For now, mock authentication
        if token == "admin_token":
            return SecurityContext(
                user_id="admin_123",
                user_role="admin",
                permissions=["admin"],
                timestamp=time.time(),
            )
        elif token == "user_token":
            return SecurityContext(
                user_id="user_123",
                user_role="user",
                permissions=["user"],
                timestamp=time.time(),
            )

        return None

    def authorize(self, context: SecurityContext, required_permission: str) -> bool:
        """Check if user has required permission."""
        if not context:
            return False

        allowed_roles = self.permission_map.get(required_permission, [])
        return context.user_role in allowed_roles

    def check_rate_limit(self, ip_address: str, operation: str) -> bool:
        """Check rate limiting for operations."""
        key = f"{ip_address}:{operation}"
        now = time.time()

        if key not in self.rate_limits:
            self.rate_limits[key] = []

        # Clean old entries (older than 1 minute)
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key] if now - timestamp < 60
        ]

        # Check if under rate limit (10 requests per minute)
        if len(self.rate_limits[key]) >= 10:
            return False

        self.rate_limits[key].append(now)
        return True

    def sanitize_error(self, error: Exception) -> str:
        """Sanitize error messages to prevent information leakage."""
        # Log the full error server-side
        print(f"Internal error: {error}")

        # Return generic message to client
        return "An internal error occurred"

    def log_security_event(
        self, event_type: str, context: SecurityContext, details: dict[str, Any]
    ):
        """Log security events for monitoring."""
        print(f"Security Event: {event_type}")
        print(f"User: {context.user_id}")
        print(f"Role: {context.user_role}")
        print(f"Details: {details}")


def require_auth(required_permission: str):
    """Decorator to require authentication and authorization."""

    def decorator(func):
        @wraps(func)
        async def wrapper(parent: Any, info: Any, *args, **kwargs):
            security_middleware = GraphQLSecurityMiddleware()

            # Extract security context
            token = info.context.get("authorization")
            context = security_middleware.authenticate(token)

            if not context:
                raise PermissionError("Authentication required")

            # Check authorization
            if not security_middleware.authorize(context, required_permission):
                security_middleware.log_security_event(
                    "authorization_failed",
                    context,
                    {"required_permission": required_permission},
                )
                raise PermissionError("Insufficient permissions")

            # Check rate limiting
            ip_address = info.context.get("ip_address", "unknown")
            if not security_middleware.check_rate_limit(ip_address, func.__name__):
                raise PermissionError("Rate limit exceeded")

            # Add security context to info
            info.context["security"] = context

            return await func(parent, info, *args, **kwargs)

        return wrapper

    return decorator


# Example usage
@require_auth("user.create")
async def create_user_resolver(parent: Any, info: Any, input_data: dict[str, Any]):
    """Example resolver with security middleware."""
    try:
        # Business logic here
        user = await create_user(input_data)
        return {"user": user, "success": True}
    except Exception as e:
        security_middleware = GraphQLSecurityMiddleware()
        error_message = security_middleware.sanitize_error(e)
        raise Exception(error_message)


async def create_user(data: dict[str, Any]) -> dict[str, Any]:
    """Mock user creation function."""
    return {"id": "123", "email": data["email"], "name": data.get("name")}
