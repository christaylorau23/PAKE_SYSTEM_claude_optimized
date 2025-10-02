"""
Audit Integration for Python/FastAPI Services
Provides audit logging integration with the PAKE Audit System
"""

import json
import time
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import httpx
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class ActorType(str, Enum):
    USER = "user"
    SERVICE = "service"
    SYSTEM = "system"
    API_KEY = "api_key"
    ANONYMOUS = "anonymous"


class ActionType(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    EXPORT = "export"
    IMPORT = "import"
    CONFIGURE = "configure"
    BACKUP = "backup"
    RESTORE = "restore"


class ActionResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    DENIED = "denied"
    ERROR = "error"


@dataclass
class AuditActor:
    id: str
    type: ActorType
    ip: Optional[str] = None
    session: Optional[str] = None
    user_agent: Optional[str] = None
    service: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuditAction:
    type: ActionType
    resource: str
    resource_id: Optional[str] = None
    result: ActionResult = ActionResult.SUCCESS
    details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    duration: Optional[int] = None
    error: Optional[str] = None


@dataclass
class AuditContext:
    request_id: Optional[str] = None
    parent_id: Optional[str] = None
    trace_id: Optional[str] = None
    environment: str = "development"
    application: str = "pake-service"
    version: str = "1.0.0"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuditEvent:
    id: str
    timestamp: str
    actor: AuditActor
    action: AuditAction
    context: AuditContext
    version: str = "1.0.0"
    signature: Optional[str] = None


class AuditLogger:
    """Audit logger for Python services"""

    def __init__(self, audit_service_url: str = "http://localhost:3002",
                 service_name: str = "python-service"):
        self.audit_service_url = audit_service_url.rstrip('/')
        self.service_name = service_name
        self.client = httpx.AsyncClient()

    async def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event to the audit service"""
        try:
            event_dict = self._event_to_dict(event)

            response = await self.client.post(
                f"{self.audit_service_url}/api/audit/events",
                json=event_dict,
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )

            if response.status_code == 201:
                return True
            else:
                print(f"Audit logging failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"Audit logging error: {str(e)}")
            return False

    def log_event_sync(self, event: AuditEvent) -> bool:
        """Synchronously log an audit event"""
        return asyncio.run(self.log_event(event))

    async def log_user_action(self, user_id: str, action_type: ActionType,
                            resource: str, resource_id: Optional[str] = None,
                            result: ActionResult = ActionResult.SUCCESS,
                            request: Optional[Request] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Log a user action"""

        actor = AuditActor(
            id=user_id,
            type=ActorType.USER,
            ip=self._get_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            metadata=metadata
        )

        action = AuditAction(
            type=action_type,
            resource=resource,
            resource_id=resource_id,
            result=result
        )

        context = AuditContext(
            request_id=request.headers.get("x-request-id") if request else None,
            trace_id=request.headers.get("x-trace-id") if request else None,
            environment=self._get_environment(),
            application=self.service_name,
            version=self._get_version()
        )

        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + 'Z',
            actor=actor,
            action=action,
            context=context
        )

        return await self.log_event(event)

    async def log_system_action(self, action_type: ActionType, resource: str,
                              result: ActionResult = ActionResult.SUCCESS,
                              details: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Log a system action"""

        actor = AuditActor(
            id="system",
            type=ActorType.SYSTEM,
            service=self.service_name
        )

        action = AuditAction(
            type=action_type,
            resource=resource,
            result=result,
            details=details,
            metadata=metadata
        )

        context = AuditContext(
            environment=self._get_environment(),
            application=self.service_name,
            version=self._get_version()
        )

        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + 'Z',
            actor=actor,
            action=action,
            context=context
        )

        return await self.log_event(event)

    def _event_to_dict(self, event: AuditEvent) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        return {
            "id": event.id,
            "timestamp": event.timestamp,
            "actor": {
                "id": event.actor.id,
                "type": event.actor.type.value,
                "ip": event.actor.ip,
                "session": event.actor.session,
                "userAgent": event.actor.user_agent,
                "service": event.actor.service,
                "metadata": event.actor.metadata or {}
            },
            "action": {
                "type": event.action.type.value,
                "resource": event.action.resource,
                "resourceId": event.action.resource_id,
                "result": event.action.result.value,
                "details": event.action.details,
                "metadata": event.action.metadata or {},
                "duration": event.action.duration,
                "error": event.action.error
            },
            "context": {
                "requestId": event.context.request_id,
                "parentId": event.context.parent_id,
                "traceId": event.context.trace_id,
                "environment": event.context.environment,
                "application": event.context.application,
                "version": event.context.version,
                "metadata": event.context.metadata or {}
            },
            "version": event.version
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _get_environment(self) -> str:
        """Get current environment"""
        import os
        return os.getenv("ENVIRONMENT", "development")

    def _get_version(self) -> str:
        """Get application version"""
        import os
        return os.getenv("APP_VERSION", "1.0.0")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class AuditMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic audit logging"""

    def __init__(self, app, audit_logger: AuditLogger,
                 exclude_paths: Optional[List[str]] = None,
                 include_request_body: bool = False,
                 include_response_body: bool = False,
                 sensitive_fields: Optional[List[str]] = None):
        super().__init__(app)
        self.audit_logger = audit_logger
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.sensitive_fields = sensitive_fields or ["REDACTED_SECRET", "token", "secret", "key"]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log audit event"""

        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Generate request ID
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Capture request details
        start_time = time.time()
        method = request.method.upper()
        path = request.url.path

        # Process request body if needed
        request_body = None
        if self.include_request_body and method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await self._get_request_body(request)
            except Exception:
                request_body = None

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration = int((time.time() - start_time) * 1000)  # milliseconds

        # Create audit event asynchronously (don't block response)
        asyncio.create_task(self._create_and_log_audit_event(
            request, response, request_id, duration, request_body
        ))

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    async def _create_and_log_audit_event(self, request: Request, response: Response,
                                        request_id: str, duration: int,
                                        request_body: Optional[Dict[str, Any]]):
        """Create and log audit event"""
        try:
            # Extract user info (implement based on your auth system)
            user_info = self._extract_user_info(request)

            # Create actor
            if user_info:
                actor = AuditActor(
                    id=user_info.get("id", "unknown"),
                    type=ActorType.USER,
                    ip=self._get_client_ip(request),
                    session=user_info.get("session_id"),
                    user_agent=request.headers.get("user-agent"),
                    metadata={
                        "username": user_info.get("username"),
                        "email": user_info.get("email"),
                        "roles": user_info.get("roles", [])
                    }
                )
            else:
                actor = AuditActor(
                    id="anonymous",
                    type=ActorType.ANONYMOUS,
                    ip=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent")
                )

            # Map HTTP method to action type
            action_type_map = {
                "GET": ActionType.READ,
                "POST": ActionType.CREATE,
                "PUT": ActionType.UPDATE,
                "PATCH": ActionType.UPDATE,
                "DELETE": ActionType.DELETE,
                "HEAD": ActionType.READ,
                "OPTIONS": ActionType.READ
            }

            action_type = action_type_map.get(request.method, ActionType.EXECUTE)
            resource = self._extract_resource(request.url.path)
            resource_id = self._extract_resource_id(request)
            result = self._determine_result(response.status_code)

            # Create action
            action_metadata = {
                "httpMethod": request.method,
                "httpPath": request.url.path,
                "statusCode": response.status_code,
                "userAgent": request.headers.get("user-agent")
            }

            if request_body:
                action_metadata["requestBody"] = self._sanitize_data(request_body)

            action = AuditAction(
                type=action_type,
                resource=resource,
                resource_id=resource_id,
                result=result,
                duration=duration,
                metadata=action_metadata,
                error=f"HTTP {response.status_code}" if response.status_code >= 400 else None
            )

            # Create context
            context = AuditContext(
                request_id=request_id,
                trace_id=request.headers.get("x-trace-id"),
                environment=self.audit_logger._get_environment(),
                application=self.audit_logger.service_name,
                version=self.audit_logger._get_version(),
                metadata={
                    "host": request.headers.get("host"),
                    "referer": request.headers.get("referer")
                }
            )

            # Create and log event
            event = AuditEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + 'Z',
                actor=actor,
                action=action,
                context=context
            )

            await self.audit_logger.log_event(event)

        except Exception as e:
            # Log error but don't fail the request
            print(f"Audit middleware error: {str(e)}")

    def _extract_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user information from request (implement based on your auth)"""
        # This is a placeholder - implement based on your authentication system
        # For example, if you store user info in request state:
        return getattr(request.state, 'user', None)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _extract_resource(self, path: str) -> str:
        """Extract resource name from path"""
        segments = path.strip("/").split("/")
        return segments[0] if segments and segments[0] else "root"

    def _extract_resource_id(self, request: Request) -> Optional[str]:
        """Extract resource ID from request"""
        # Check path parameters
        path_segments = request.url.path.strip("/").split("/")
        for segment in path_segments:
            # UUID pattern
            if len(segment) == 36 and segment.count("-") == 4:
                return segment
            # Numeric ID
            if segment.isdigit():
                return segment

        # Check query parameters
        if "id" in request.query_params:
            return request.query_params["id"]

        return None

    def _determine_result(self, status_code: int) -> ActionResult:
        """Determine action result from status code"""
        if 200 <= status_code < 300:
            return ActionResult.SUCCESS
        elif status_code == 403:
            return ActionResult.DENIED
        elif 400 <= status_code < 500:
            return ActionResult.FAILURE
        elif status_code >= 500:
            return ActionResult.ERROR
        else:
            return ActionResult.SUCCESS

    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get request body as dictionary"""
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.body()
                if body:
                    return json.loads(body.decode())
        except Exception:
            pass
        return None

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(field.lower() in key.lower() for field in self.sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data


# Utility functions for manual audit logging
async def log_user_login(audit_logger: AuditLogger, user_id: str,
                        success: bool, request: Optional[Request] = None,
                        metadata: Optional[Dict[str, Any]] = None):
    """Log user login attempt"""
    await audit_logger.log_user_action(
        user_id=user_id,
        action_type=ActionType.LOGIN,
        resource="authentication",
        result=ActionResult.SUCCESS if success else ActionResult.FAILURE,
        request=request,
        metadata=metadata
    )


async def log_user_logout(audit_logger: AuditLogger, user_id: str,
                         request: Optional[Request] = None):
    """Log user logout"""
    await audit_logger.log_user_action(
        user_id=user_id,
        action_type=ActionType.LOGOUT,
        resource="authentication",
        result=ActionResult.SUCCESS,
        request=request
    )


async def log_data_export(audit_logger: AuditLogger, user_id: str,
                         resource: str, resource_id: Optional[str] = None,
                         export_format: Optional[str] = None,
                         record_count: Optional[int] = None):
    """Log data export"""
    metadata = {}
    if export_format:
        metadata["exportFormat"] = export_format
    if record_count:
        metadata["recordCount"] = record_count

    await audit_logger.log_user_action(
        user_id=user_id,
        action_type=ActionType.EXPORT,
        resource=resource,
        resource_id=resource_id,
        result=ActionResult.SUCCESS,
        metadata=metadata
    )


async def log_permission_change(audit_logger: AuditLogger, user_id: str,
                              target_user_id: str, permissions_added: List[str],
                              permissions_removed: List[str]):
    """Log permission changes"""
    await audit_logger.log_user_action(
        user_id=user_id,
        action_type=ActionType.CONFIGURE,
        resource="user_permissions",
        resource_id=target_user_id,
        result=ActionResult.SUCCESS,
        metadata={
            "permissionsAdded": permissions_added,
            "permissionsRemoved": permissions_removed
        }
    )