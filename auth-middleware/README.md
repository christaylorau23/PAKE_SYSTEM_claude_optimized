# PAKE Authentication Middleware for Python/FastAPI

FastAPI middleware for integrating with the PAKE Authentication Service. Provides JWT token validation, session management, and role-based access control for Python services.

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from fastapi import FastAPI, Depends
from auth_middleware import (
    setup_auth_middleware,
    get_current_user,
    require_roles,
    require_permissions,
    AuthUser
)

app = FastAPI()

# Setup authentication middleware
setup_auth_middleware(app)

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
```

## 🔧 Configuration

### Environment Variables

```env
# JWT Configuration
JWT_SECRET=your-jwt-secret
JWT_ISSUER=pake-system
JWT_AUDIENCE=pake-users

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_KEY_PREFIX=pake:auth:

# Auth Service Configuration
AUTH_SERVICE_URL=http://localhost:3001
AUTH_CACHE_TTL=300

# Rate Limiting
RATE_LIMIT_WINDOW=900
RATE_LIMIT_MAX_REQUESTS=100
```

## 📚 API Reference

### AuthUser Class

```python
class AuthUser:
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

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if user has a specific permission"""

    def has_any_permission(self, permissions: List[tuple]) -> bool:
        """Check if user has any of the specified permissions"""
```

### Dependencies

#### get_current_user()

Extract authenticated user from JWT token.

```python
@app.get("/profile")
async def get_profile(current_user: AuthUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }
```

#### require_roles(roles: List[str])

Require user to have one of the specified roles.

```python
@app.get("/admin/users")
async def list_users(current_user: AuthUser = Depends(require_roles(["admin", "moderator"]))):
    return {"users": []}
```

#### require_permissions(permissions: List[tuple])

Require user to have one of the specified permissions.

```python
@app.get("/vault/notes")
async def get_notes(
    current_user: AuthUser = Depends(require_permissions([
        ("vault", "read"),
        ("notes", "read")
    ]))
):
    return {"notes": []}
```

#### require_mfa()

Require MFA verification.

```python
@app.get("/sensitive-data")
async def get_sensitive_data(current_user: AuthUser = Depends(require_mfa())):
    return {"data": "sensitive information"}
```

### Manual Token Verification

```python
from auth_middleware import AuthService, AuthConfig

async def verify_token_manually():
    config = AuthConfig()
    auth_service = AuthService(config)
    await auth_service.initialize()

    token = "jwt-token"
    payload = await auth_service.verify_token(token)

    if payload:
        print(f"User ID: {payload.sub}")
        print(f"Roles: {payload.roles}")
        print(f"Permissions: {payload.permissions}")

    await auth_service.close()
```

## 🔐 Security Features

### Rate Limiting

Built-in rate limiting per user and IP address.

```python
# Customize rate limits
app = setup_auth_middleware(
    app,
    rate_limit_config={
        "windowMs": 600000,  # 10 minutes
        "maxRequests": 50    # 50 requests per window
    }
)
```

### Session Validation

Automatic session validation with Redis.

```python
# Sessions are automatically validated
# Invalid sessions result in 401 Unauthorized
```

### Audit Logging

Automatic audit logging for all authenticated requests.

```python
# Logs include:
# - User ID
# - Action performed
# - Resource accessed
# - IP address
# - Timestamp
# - Success/failure status
```

## 🎯 Advanced Usage

### Custom Authentication Logic

```python
from auth_middleware import AuthMiddleware, AuthService

class CustomAuthMiddleware(AuthMiddleware):
    async def authenticate_user(self, token: str) -> AuthUser:
        # Custom authentication logic
        payload = await self.auth_service.verify_token(token)

        if not payload:
            return None

        # Add custom user data
        user = AuthUser(
            user_id=payload.sub,
            email=payload.email,
            username=payload.username,
            roles=payload.roles,
            permissions=payload.permissions,
            session_id=payload.session_id,
            mfa_verified=payload.mfa_verified
        )

        # Custom role/permission logic
        if user.has_role("premium"):
            user.permissions.extend(["premium:feature1", "premium:feature2"])

        return user

# Use custom middleware
app.add_middleware(CustomAuthMiddleware, auth_service=auth_service)
```

### Conditional Authentication

```python
from auth_middleware import get_current_user
from fastapi import HTTPException

async def optional_auth(
    current_user: AuthUser = Depends(get_current_user)
) -> Optional[AuthUser]:
    """Optional authentication - returns None if not authenticated"""
    try:
        return current_user
    except HTTPException:
        return None

@app.get("/public-or-private")
async def flexible_endpoint(user: Optional[AuthUser] = Depends(optional_auth)):
    if user:
        return {"message": f"Hello {user.username}!", "private_data": True}
    else:
        return {"message": "Hello anonymous user!", "private_data": False}
```

### Custom Permission Logic

```python
from auth_middleware import AuthUser
from fastapi import Depends, HTTPException

async def require_resource_ownership(
    resource_id: str,
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Require user to own the resource or be an admin"""

    if current_user.has_role("admin"):
        return current_user

    # Check resource ownership (implement your logic)
    if not user_owns_resource(current_user.id, resource_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return current_user

@app.get("/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    current_user: AuthUser = Depends(require_resource_ownership)
):
    return {"resource": resource_id, "owner": current_user.username}
```

## 🧪 Testing

### Test Setup

```python
import pytest
from fastapi.testclient import TestClient
from auth_middleware import create_test_token

@pytest.fixture
def authenticated_client():
    app = create_test_app()
    client = TestClient(app)

    # Create test token
    token = create_test_token(
        user_id="test-user",
        roles=["user"],
        permissions=["vault:read"]
    )

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

def test_protected_endpoint(authenticated_client):
    response = authenticated_client.get("/protected")
    assert response.status_code == 200
    assert "Hello" in response.json()["message"]
```

### Mock Authentication

```python
from auth_middleware import AuthUser
from unittest.mock import Mock

# Mock authenticated user
def override_get_current_user():
    return AuthUser(
        user_id="test-user",
        email="test@example.com",
        username="testuser",
        roles=["admin"],
        permissions=["vault:read", "vault:write"],
        session_id="test-session",
        mfa_verified=True
    )

# Override dependency
app.dependency_overrides[get_current_user] = override_get_current_user

# Test with mock user
response = client.get("/admin-only")
assert response.status_code == 200
```

## 🔧 Troubleshooting

### Common Issues

#### 401 Unauthorized

- Check JWT token is valid and not expired
- Verify JWT_SECRET matches auth service
- Ensure session is still active in Redis

#### 403 Forbidden

- Verify user has required roles/permissions
- Check RBAC configuration in auth service
- Confirm user status is active

#### 429 Rate Limited

- Reduce request frequency
- Check rate limiting configuration
- Consider implementing request queuing

#### Connection Errors

- Verify Redis connection settings
- Check auth service availability
- Validate network connectivity

### Debug Mode

```python
import logging
from auth_middleware import setup_auth_middleware

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
setup_auth_middleware(app, debug=True)
```

### Health Checks

```python
@app.get("/auth-health")
async def check_auth_health(request: Request):
    auth_service = request.app.state.auth_service

    return {
        "redis": auth_service.redis.is_healthy() if auth_service.redis else False,
        "auth_service": await auth_service.ping() if auth_service else False
    }
```

## 📊 Performance

### Caching

User permissions are cached in Redis for 5 minutes by default.

```python
# Customize cache TTL
AUTH_CACHE_TTL=600  # 10 minutes
```

### Connection Pooling

Redis connections are pooled for optimal performance.

```python
# Customize Redis pool
REDIS_POOL_MIN=2
REDIS_POOL_MAX=10
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details.
