# PAKE System Authentication Module

**Production-grade authentication system implementing OAuth2 with JWT Bearer tokens for FastAPI applications.**

## Overview

This authentication module provides a complete, secure, and FastAPI-compliant authentication system following industry best practices. It implements the OAuth2 "Password" flow with JWT (JSON Web Tokens) for stateless authentication.

## Architecture

### Components

1. **`security.py`** - Core security functions
   - Password hashing with Bcrypt
   - JWT token generation and validation
   - Cryptographic operations

2. **`models.py`** - Pydantic data models
   - `User` - Public user model
   - `UserInDB` - User model with password hash
   - `Token` - OAuth2 token response
   - `TokenData` - Decoded token payload

3. **`database.py`** - User data access
   - User lookup and authentication
   - In-memory storage (replace with real DB in production)

4. **`dependencies.py`** - FastAPI dependencies
   - `get_current_user` - Extract and validate user from JWT
   - `get_current_active_user` - Verify user is active

5. **`router.py`** - API endpoints
   - `POST /token` - OAuth2 login endpoint
   - `GET /auth/me` - Get current user info
   - `POST /auth/logout` - Logout (optional)

6. **`example_app.py`** - Complete working example
   - Demonstrates integration
   - Includes protected routes

## Security Features

### Password Security
- ✅ **Bcrypt hashing** - Industry standard with automatic salting
- ✅ **One-way encryption** - Passwords cannot be recovered
- ✅ **Constant-time comparison** - Prevents timing attacks

### Token Security
- ✅ **JWT with HS256** - Signed tokens prevent tampering
- ✅ **Expiration claims** - Tokens automatically expire
- ✅ **Stateless authentication** - No server-side session storage
- ✅ **Bearer token scheme** - Standard HTTP authentication

### Implementation Security
- ✅ **Zero-tolerance for secrets** - No hardcoded credentials
- ✅ **Environment-based config** - Settings from .env
- ✅ **HTTPS enforcement** - Production requirement
- ✅ **Rate limiting ready** - Can integrate with slowapi

## Quick Start

### 1. Configuration

Create a `.env` file:

```bash
# Required
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=postgresql://user:pass@localhost/pake
REDIS_URL=redis://localhost:6379

# Optional (with defaults)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256
```

⚠️ **IMPORTANT**: Generate a secure SECRET_KEY:
```bash
openssl rand -hex 32
```

### 2. Basic Integration

```python
from fastapi import FastAPI, Depends
from src.pake_system.auth import get_current_active_user
from src.pake_system.auth.router import router as auth_router
from src.pake_system.auth.models import User

app = FastAPI()

# Include authentication routes
app.include_router(auth_router)

# Protect any endpoint with the dependency
@app.get("/protected")
async def protected_route(user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {user.username}"}
```

### 3. Run the Example

```bash
# Start the example application
uvicorn src.pake_system.auth.example_app:app --reload

# Access interactive docs
open http://localhost:8000/docs
```

## Usage Examples

### Authentication Flow

#### 1. Login to Get Token

```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 2. Access Protected Endpoints

```bash
curl "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <your_token_here>"
```

Response:
```json
{
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "disabled": false
}
```

### Using in Python Code

```python
from src.pake_system.auth.security import create_password_hash, verify_password

# Hash a password (during registration)
hashed = create_password_hash("SecurePassword123!")

# Verify password (during login)
is_valid = verify_password("SecurePassword123!", hashed)
```

### Creating Protected Endpoints

```python
from typing import Annotated
from fastapi import Depends
from src.pake_system.auth import get_current_active_user, User

# Simple protection
@app.get("/users/me")
async def read_current_user(user: User = Depends(get_current_active_user)):
    return user

# With role-based access control
@app.get("/admin/dashboard")
async def admin_dashboard(user: Annotated[User, Depends(get_current_active_user)]):
    # Check user role (implement your own logic)
    if not hasattr(user, 'role') or user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"admin": "data"}
```

## Testing

The module includes comprehensive tests covering:
- Unit tests for password hashing
- Unit tests for JWT tokens
- Integration tests for authentication flow
- End-to-end API tests
- Performance benchmarks

### Run Tests

```bash
# Run all auth tests
pytest tests/test_auth_system.py -v

# Run with coverage
pytest tests/test_auth_system.py --cov=src/pake_system/auth --cov-report=html

# Run specific test categories
pytest tests/test_auth_system.py -v -m unit
pytest tests/test_auth_system.py -v -m integration_auth
pytest tests/test_auth_system.py -v -m e2e
```

## Production Deployment

### Prerequisites

1. **HTTPS Only** - Never use HTTP in production
2. **Secure SECRET_KEY** - Use a cryptographically random key
3. **Database Backend** - Replace in-memory storage with PostgreSQL
4. **Rate Limiting** - Add rate limiting to prevent brute force
5. **Token Refresh** - Implement refresh tokens for better UX
6. **Logging** - Add authentication event logging
7. **Monitoring** - Track failed login attempts

### Production Checklist

- [ ] Generate secure SECRET_KEY with `openssl rand -hex 32`
- [ ] Store secrets in environment variables or vault
- [ ] Configure HTTPS/TLS certificates
- [ ] Implement rate limiting on /token endpoint
- [ ] Add refresh token support
- [ ] Replace in-memory database with PostgreSQL
- [ ] Add password complexity requirements
- [ ] Implement account lockout after failed attempts
- [ ] Set up authentication logging
- [ ] Configure token expiration appropriately
- [ ] Add CORS configuration for frontend
- [ ] Implement token revocation (blacklist)
- [ ] Add MFA (Multi-Factor Authentication) support

## Database Integration

Replace the in-memory `fake_users_db` with real database queries:

```python
# database.py - Production version
from sqlalchemy.orm import Session
from .models import UserInDB

async def get_user(username: str, db: Session) -> Optional[UserInDB]:
    """Fetch user from PostgreSQL"""
    result = await db.execute(
        "SELECT * FROM users WHERE username = :username",
        {"username": username}
    )
    user_data = result.fetchone()
    if user_data:
        return UserInDB(**user_data)
    return None
```

## Advanced Features

### Token Refresh

Implement refresh tokens for better security:

```python
@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str = Body(...)):
    # Verify refresh token
    # Generate new access token
    # Return new token pair
    pass
```

### Role-Based Access Control

Add role checking dependency:

```python
from typing import List

def require_roles(allowed_roles: List[str]):
    async def role_checker(user: User = Depends(get_current_active_user)):
        if user.role not in allowed_roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return role_checker

# Usage
@app.get("/admin")
async def admin_route(user: User = Depends(require_roles(["admin"]))):
    return {"admin": "content"}
```

### Token Revocation

Implement token blacklist with Redis:

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379)

async def revoke_token(token: str):
    """Add token to blacklist"""
    decoded = decode_token(token)
    expiration = decoded['exp'] - time.time()
    redis_client.setex(f"revoked:{token}", int(expiration), "1")

async def is_token_revoked(token: str) -> bool:
    """Check if token is revoked"""
    return redis_client.exists(f"revoked:{token}")
```

## Troubleshooting

### Common Issues

**Issue**: `401 Unauthorized` when accessing protected endpoints

**Solution**: Ensure Authorization header is correctly formatted:
```
Authorization: Bearer <token>
```

---

**Issue**: Token decoding fails with signature error

**Solution**: SECRET_KEY must be the same between token creation and validation

---

**Issue**: `422 Unprocessable Entity` at /token endpoint

**Solution**: Use `application/x-www-form-urlencoded` content type, not JSON

---

**Issue**: Password verification always fails

**Solution**: Ensure you're comparing the plaintext password with the hashed version, not the other way around

## API Reference

### Endpoints

#### `POST /token`
OAuth2 compatible token endpoint for user login.

**Request** (form data):
- `username`: string (required)
- `password`: string (required)

**Response**:
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

---

#### `GET /auth/me`
Get current authenticated user information.

**Headers**:
- `Authorization: Bearer <token>`

**Response**:
```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false
}
```

## Contributing

When extending this authentication system:

1. **Maintain test coverage** - Add tests for new features
2. **Follow security best practices** - Never store plaintext passwords
3. **Document changes** - Update this README
4. **Use type hints** - All functions should be typed
5. **Add docstrings** - Follow Google style guide

## License

Part of the PAKE System. See main project LICENSE.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the example application
3. Check the comprehensive tests
4. Open an issue on GitHub
