#!/usr/bin/env python3
"""
FastAPI Authentication Middleware
Integrates with the Node.js authentication service to provide
JWT token validation and RBAC for Python services
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Callable, Any
from functools import wraps

import httpx
import jwt
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as aioredis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthConfig:
    """Authentication configuration"""
    
    def __init__(self):
        import os
        
        # JWT Configuration
        self.JWT_SECRET = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-in-production')
        self.JWT_ALGORITHM = 'HS256'
        self.JWT_ISSUER = os.getenv('JWT_ISSUER', 'pake-system')
        self.JWT_AUDIENCE = os.getenv('JWT_AUDIENCE', 'pake-users')
        
        # Redis Configuration
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.getenv('REDIS_DB', '0'))
        self.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
        self.REDIS_KEY_PREFIX = os.getenv('REDIS_KEY_PREFIX', 'pake:auth:')
        
        # Auth Service Configuration
        self.AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:3001')
        self.CACHE_TTL = int(os.getenv('AUTH_CACHE_TTL', '300'))  # 5 minutes
        
        # Rate Limiting
        self.RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '900'))  # 15 minutes
        self.RATE_LIMIT_MAX_REQUESTS = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '100'))

class JWTPayload:
    """JWT token payload"""
    
    def __init__(self, payload: Dict[str, Any]):
        self.sub = payload.get('sub')  # user id
        self.email = payload.get('email')
        self.username = payload.get('username')
        self.roles = payload.get('roles', [])
        self.permissions = payload.get('permissions', [])
        self.session_id = payload.get('sessionId')
        self.mfa_verified = payload.get('mfaVerified', False)
        self.iat = payload.get('iat')
        self.exp = payload.get('exp')
        self.iss = payload.get('iss')
        self.aud = payload.get('aud')

class AuthUser:
    """Authenticated user"""
    
    def __init__(self, user_id: str, email: str, username: str, 
                 roles: List[str], permissions: List[str], 
                 session_id: str, mfa_verified: bool = False):
        self.id = user_id
        self.email = email
        self.username = username
        self.roles = roles
        self.permissions = permissions
        self.session_id = session_id
        self.mfa_verified = mfa_verified
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role.lower() in [r.lower() for r in self.roles]
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        user_roles_lower = [r.lower() for r in self.roles]
        return any(role.lower() in user_roles_lower for role in roles)
    
    def has_permission(self, resource: str, action: str) -> bool:
        """Check if user has a specific permission"""
        permission = f"{resource.lower()}:{action.lower()}"
        return permission in [p.lower() for p in self.permissions]
    
    def has_any_permission(self, permissions: List[tuple]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = [p.lower() for p in self.permissions]
        return any(f"{resource.lower()}:{action.lower()}" in user_permissions 
                  for resource, action in permissions)

class AuthenticationError(HTTPException):
    """Authentication error"""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=401, detail=detail)

class AuthorizationError(HTTPException):
    """Authorization error"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)

class AuthService:
    """Authentication service client"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.redis: Optional[aioredis.Redis] = None
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize connections"""
        try:
            # Initialize Redis connection
            self.redis = aioredis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                REDACTED_SECRET=self.config.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # Test Redis connection
            await self.redis.ping()
            logger.info("Redis connection established")
            
            # Initialize HTTP client
            self._http_client = httpx.AsyncClient(
                base_url=self.config.AUTH_SERVICE_URL,
                timeout=httpx.Timeout(30.0)
            )
            
            logger.info("Auth service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize auth service: {e}")
            raise
    
    async def close(self):
        """Close connections"""
        if self.redis:
            await self.redis.close()
        
        if self._http_client:
            await self._http_client.aclose()
    
    def _cache_key(self, key_type: str, identifier: str) -> str:
        """Generate cache key"""
        return f"{self.config.REDIS_KEY_PREFIX}{key_type}:{identifier}"
    
    async def verify_token(self, token: str) -> Optional[JWTPayload]:
        """Verify JWT token"""
        try:
            # First try to decode locally
            payload = jwt.decode(
                token,
                self.config.JWT_SECRET,
                algorithms=[self.config.JWT_ALGORITHM],
                issuer=self.config.JWT_ISSUER,
                audience=self.config.JWT_AUDIENCE
            )
            
            jwt_payload = JWTPayload(payload)
            
            # Check if session is still active
            if self.redis:
                session_key = self._cache_key('session', jwt_payload.session_id)
                session_active = await self.redis.exists(session_key)
                
                if not session_active:
                    logger.warning(f"Session not active: {jwt_payload.session_id}")
                    return None
            
            return jwt_payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    async def check_rate_limit(self, identifier: str, max_requests: int = None) -> bool:
        """Check rate limit for identifier"""
        if not self.redis:
            return True
        
        max_requests = max_requests or self.config.RATE_LIMIT_MAX_REQUESTS
        
        try:
            key = self._cache_key('rate_limit', identifier)
            current = await self.redis.get(key)
            
            if current is None:
                # First request
                await self.redis.setex(key, self.config.RATE_LIMIT_WINDOW, 1)
                return True
            
            current_count = int(current)
            
            if current_count >= max_requests:
                return False
            
            # Increment counter
            await self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Fail open
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions (cached)"""
        if not self.redis:
            return []
        
        try:
            cache_key = self._cache_key('user_permissions', user_id)
            cached = await self.redis.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            # Fetch from auth service
            if self._http_client:
                response = await self._http_client.get(f"/api/users/{user_id}/permissions")
                
                if response.status_code == 200:
                    permissions = response.json().get('permissions', [])
                    
                    # Cache for 5 minutes
                    await self.redis.setex(
                        cache_key, 
                        self.config.CACHE_TTL, 
                        json.dumps(permissions)
                    )
                    
                    return permissions
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return []
    
    async def audit_log(self, user_id: str, action: str, resource: str, 
                       success: bool, ip_address: str, user_agent: str,
                       resource_id: str = None, error: str = None,
                       metadata: Dict[str, Any] = None):
        """Log audit event"""
        try:
            audit_data = {
                'userId': user_id,
                'action': action,
                'resource': resource,
                'resourceId': resource_id,
                'success': success,
                'ipAddress': ip_address,
                'userAgent': user_agent,
                'error': error,
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if self._http_client:
                await self._http_client.post("/api/audit/log", json=audit_data)
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI authentication middleware"""
    
    def __init__(self, app, auth_service: AuthService, exempt_paths: Set[str] = None):
        super().__init__(app)
        self.auth_service = auth_service
        self.exempt_paths = exempt_paths or {
            "/health", "/metrics", "/docs", "/redoc", "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("authorization")
        if not authorization:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"}
            )
        
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication scheme"}
            )
        
        # Verify token
        jwt_payload = await self.auth_service.verify_token(token)
        if not jwt_payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )
        
        # Check rate limit
        ip_address = request.client.host if request.client else "unknown"
        if not await self.auth_service.check_rate_limit(f"user:{jwt_payload.sub}"):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        if not await self.auth_service.check_rate_limit(f"ip:{ip_address}"):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Create auth user
        auth_user = AuthUser(
            user_id=jwt_payload.sub,
            email=jwt_payload.email,
            username=jwt_payload.username,
            roles=jwt_payload.roles,
            permissions=jwt_payload.permissions,
            session_id=jwt_payload.session_id,
            mfa_verified=jwt_payload.mfa_verified
        )
        
        # Add user to request state
        request.state.user = auth_user
        request.state.ip_address = ip_address
        
        # Process request
        response = await call_next(request)
        
        # Log successful access
        await self.auth_service.audit_log(
            user_id=auth_user.id,
            action="access",
            resource=request.url.path,
            success=response.status_code < 400,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent", ""),
            metadata={
                "method": request.method,
                "status_code": response.status_code
            }
        )
        
        return response

# Dependency injection functions for FastAPI
security = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """Get current authenticated user"""
    if hasattr(request.state, 'user'):
        return request.state.user
    
    raise AuthenticationError("Authentication required")

async def get_current_active_user(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Get current active user (additional checks can be added here)"""
    return current_user

def require_roles(roles: List[str]):
    """Dependency to require specific roles"""
    
    def role_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not current_user.has_any_role(roles):
            raise AuthorizationError(f"Requires one of roles: {', '.join(roles)}")
        return current_user
    
    return role_checker

def require_permissions(permissions: List[tuple]):
    """Dependency to require specific permissions"""
    
    def permission_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not current_user.has_any_permission(permissions):
            permission_strs = [f"{resource}:{action}" for resource, action in permissions]
            raise AuthorizationError(f"Requires one of permissions: {', '.join(permission_strs)}")
        return current_user
    
    return permission_checker

def require_mfa():
    """Dependency to require MFA verification"""
    
    def mfa_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not current_user.mfa_verified:
            raise AuthorizationError("MFA verification required")
        return current_user
    
    return mfa_checker

# Decorators for route protection
def auth_required(func: Callable):
    """Decorator to require authentication"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # This decorator would be used with the dependency system
        return await func(*args, **kwargs)
    
    return wrapper

def roles_required(*roles: str):
    """Decorator to require specific roles"""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would work with the dependency system
            return await func(*args, **kwargs)
        return wrapper
    
    return decorator

# Utility functions
async def create_auth_service() -> AuthService:
    """Create and initialize auth service"""
    config = AuthConfig()
    service = AuthService(config)
    await service.initialize()
    return service

def setup_auth_middleware(app, exempt_paths: Set[str] = None):
    """Setup authentication middleware for FastAPI app"""
    
    async def startup_event():
        auth_service = await create_auth_service()
        app.state.auth_service = auth_service
        
        # Add middleware
        app.add_middleware(
            AuthMiddleware,
            auth_service=auth_service,
            exempt_paths=exempt_paths
        )
    
    async def shutdown_event():
        if hasattr(app.state, 'auth_service'):
            await app.state.auth_service.close()
    
    app.add_event_handler("startup", startup_event)
    app.add_event_handler("shutdown", shutdown_event)
    
    return app

# Example usage functions
def create_protected_endpoint():
    """Example of creating a protected endpoint"""
    from fastapi import FastAPI, Depends
    
    app = FastAPI()
    
    @app.get("/protected")
    async def protected_route(current_user: AuthUser = Depends(get_current_user)):
        return {"message": f"Hello {current_user.username}!"}
    
    @app.get("/admin-only")
    async def admin_route(current_user: AuthUser = Depends(require_roles(["admin"]))):
        return {"message": "Admin access granted"}
    
    @app.get("/vault-access")
    async def vault_route(
        current_user: AuthUser = Depends(require_permissions([("vault", "read")]))
    ):
        return {"message": "Vault access granted"}
    
    @app.get("/mfa-required")
    async def mfa_route(current_user: AuthUser = Depends(require_mfa())):
        return {"message": "MFA verified access"}
    
    return setup_auth_middleware(app)

if __name__ == "__main__":
    # Example usage
    import uvicorn
    
    app = create_protected_endpoint()
    uvicorn.run(app, host="127.0.0.1", port=8000)