# PAKE Authentication Service

Enterprise-grade authentication and authorization service for the PAKE System, providing comprehensive security features including JWT tokens, multi-factor authentication, role-based access control, and session management.

## 🔐 Features

### Core Authentication

- **JWT Token Management**: Secure access and refresh tokens with configurable expiration
- **Multi-Factor Authentication (MFA)**: TOTP and WebAuthn support
- **Session Management**: Redis-backed sessions with device tracking and limits
- **Password Security**: Argon2 hashing with comprehensive policy enforcement
- **OAuth2/OIDC**: Support for Google, GitHub, and Microsoft providers

### Authorization & Access Control

- **Role-Based Access Control (RBAC)**: Granular permission system with Casbin
- **Permission Management**: Resource-action based permissions
- **Session Limits**: Configurable maximum sessions per user
- **Rate Limiting**: Protect against brute force attacks

### Security Features

- **Password Policies**: Configurable complexity, history, and expiration
- **Account Lockout**: Automatic lockout after failed attempts
- **Device Tracking**: Monitor and manage user devices
- **Audit Logging**: Comprehensive security event logging
- **Email Notifications**: Security alerts and verification emails

### Integration

- **FastAPI Middleware**: Python service integration
- **Express.js Service**: Node.js/TypeScript implementation
- **Redis Integration**: Session and cache management
- **Database Support**: PostgreSQL with user management

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Redis 6+
- PostgreSQL 12+ (optional)
- Python 3.9+ (for middleware)

### Installation

```bash
# Install dependencies
npm install

# Install Python middleware dependencies
pip install -r ../auth-middleware/requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit configuration
nano .env
```

### Environment Variables

```env
# JWT Configuration
JWT_SECRET=your-super-secure-jwt-secret-key-change-this-in-production
JWT_ISSUER=pake-system
JWT_AUDIENCE=pake-users
JWT_ACCESS_EXPIRY=15m
JWT_REFRESH_EXPIRY=7d

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_KEY_PREFIX=pake:auth:

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-REDACTED_SECRET
EMAIL_FROM=noreply@pake-system.com

# OAuth Providers (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Security Configuration
PASSWORD_MIN_LENGTH=12
LOCKOUT_MAX_ATTEMPTS=5
LOCKOUT_DURATION=30
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX_REQUESTS=100

# Application
PORT=3001
NODE_ENV=production
FRONTEND_URL=http://localhost:3000
```

### Running the Service

```bash
# Development mode
npm run dev

# Production mode
npm run build
npm start

# With Docker
docker-compose up -d
```

## 📚 API Documentation

### Authentication Endpoints

#### POST /api/auth/register

Register a new user account.

```json
{
  "email": "user@example.com",
  "username": "testuser",
  "REDACTED_SECRET": "SecurePassword123!@#",
  "firstName": "John",
  "lastName": "Doe"
}
```

**Response:**

```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "testuser",
    "firstName": "John",
    "lastName": "Doe",
    "status": "pending_verification"
  },
  "message": "User created successfully. Please check your email for verification."
}
```

#### POST /api/auth/login

Authenticate user with email and REDACTED_SECRET.

```json
{
  "email": "user@example.com",
  "REDACTED_SECRET": "SecurePassword123!@#"
}
```

**Response:**

```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "testuser",
    "firstName": "John",
    "lastName": "Doe",
    "roles": ["user"],
    "emailVerified": true
  },
  "tokens": {
    "accessToken": "jwt-access-token",
    "refreshToken": "jwt-refresh-token",
    "tokenType": "Bearer",
    "expiresIn": 900
  }
}
```

#### POST /api/auth/login/mfa

Complete MFA authentication.

```json
{
  "sessionCode": "mfa-session-code",
  "mfaToken": "secure_mfa_token"
}
```

#### POST /api/auth/refresh

Refresh access token.

```json
{
  "refreshToken": "jwt-refresh-token"
}
```

#### POST /api/auth/logout

Logout and invalidate session.

**Headers:**

```
Authorization: Bearer jwt-access-token
```

### User Management Endpoints

#### GET /api/users/me

Get current user profile.

#### PUT /api/users/me

Update user profile.

```json
{
  "firstName": "John",
  "lastName": "Smith",
  "avatar": "https://example.com/avatar.jpg"
}
```

#### POST /api/users/me/change-REDACTED_SECRET

Change user REDACTED_SECRET.

```json
{
  "currentPassword": "CurrentPassword123!@#",
  "newPassword": "NewPassword123!@#"
}
```

#### GET /api/users/me/sessions

Get user's active sessions.

#### DELETE /api/users/me/sessions/:sessionId

Delete specific session.

### MFA Endpoints

#### POST /api/auth/mfa/setup

Setup TOTP MFA.

**Response:**

```json
{
  "success": true,
  "secret": "base32-secret",
  "qrCode": "data:image/png;base64,...",
  "backupCodes": ["12345678", "87654321", ...]
}
```

#### POST /api/auth/mfa/verify-setup

Verify MFA setup.

```json
{
  "token": "secure_jwt_token"
}
```

#### GET /api/auth/mfa/status

Get MFA status.

#### DELETE /api/auth/mfa

Disable MFA.

### Admin Endpoints

#### GET /api/admin/users

List users (admin only).

#### GET /api/admin/users/:userId

Get user details (admin only).

#### PUT /api/admin/users/:userId/status

Update user status (admin only).

```json
{
  "status": "suspended"
}
```

#### GET /api/admin/roles

List roles (admin only).

#### POST /api/admin/roles

Create role (admin only).

```json
{
  "name": "editor",
  "description": "Content editor role",
  "permissions": ["content.read", "content.write"]
}
```

## 🐍 Python Integration

### FastAPI Middleware

```python
from auth_middleware import setup_auth_middleware, get_current_user, require_roles

app = FastAPI()
setup_auth_middleware(app)

@app.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user_id": current_user.id}

@app.get("/admin-only")
async def admin_route(current_user = Depends(require_roles(["admin"]))):
    return {"message": "Admin access granted"}
```

### Manual Integration

```python
from auth_middleware import AuthService, AuthConfig

config = AuthConfig()
auth_service = AuthService(config)
await auth_service.initialize()

# Verify token
payload = await auth_service.verify_token(token)
if payload:
    user_id = payload.sub
    permissions = payload.permissions
```

## 🔧 Configuration

### Password Policy

```typescript
const REDACTED_SECRETPolicy = {
  minLength: 12,
  maxLength: 128,
  requireUppercase: true,
  requireLowercase: true,
  requireNumbers: true,
  requireSymbols: true,
  preventCommonPasswords: true,
  preventReuse: 12,
  maxAge: 90, // days
};
```

### Session Configuration

```typescript
const sessionConfig = {
  maxSessions: 5,
  maxAge: 86400, // 24 hours
  extendOnActivity: true,
};
```

### Rate Limiting

```typescript
const rateLimiting = {
  windowMs: 900000, // 15 minutes
  maxRequests: 100,
  lockoutPolicy: {
    maxAttempts: 5,
    lockoutDuration: 30, // minutes
    resetAfter: 60, // minutes
  },
};
```

## 🧪 Testing

### Run Tests

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# Coverage report
npm run test:coverage

# Watch mode
npm run test:watch
```

### Test Categories

- **Unit Tests**: Service-level testing with mocked dependencies
- **Integration Tests**: End-to-end API testing
- **Security Tests**: Authentication flow and security validation
- **Performance Tests**: Load testing and response time validation

## 🚀 Deployment

### Docker Deployment

```bash
# Build image
docker build -t pake-auth .

# Run with docker-compose
docker-compose up -d
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pake-auth
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pake-auth
  template:
    metadata:
      labels:
        app: pake-auth
    spec:
      containers:
        - name: pake-auth
          image: pake-auth:latest
          ports:
            - containerPort: 3001
          env:
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: pake-secrets
                  key: jwt-secret
```

### Environment-Specific Configuration

#### Development

```env
NODE_ENV=development
LOG_LEVEL=debug
JWT_SECRET=dev-secret-change-in-production
```

#### Production

```env
NODE_ENV=production
LOG_LEVEL=info
JWT_SECRET=production-secret-from-vault
REDIS_PASSWORD=secure-redis-REDACTED_SECRET
```

## 📊 Monitoring

### Health Endpoints

- `GET /health` - Service health status
- `GET /metrics` - Application metrics

### Logging

The service uses structured JSON logging with the following levels:

- `error` - Error events
- `warn` - Warning events
- `info` - Informational events
- `debug` - Debug events

### Metrics

Key metrics tracked:

- Authentication attempts (success/failure)
- Token generation/validation
- Session creation/destruction
- MFA usage
- Rate limiting events

## 🔒 Security Considerations

### Production Checklist

- [ ] Change default JWT secret
- [ ] Enable HTTPS/TLS everywhere
- [ ] Configure secure Redis REDACTED_SECRET
- [ ] Set up proper firewall rules
- [ ] Enable audit logging
- [ ] Configure email notifications
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Backup and disaster recovery

### Security Best Practices

1. **JWT Tokens**
   - Short-lived access tokens (15 minutes)
   - Secure refresh token storage
   - Token rotation on refresh

2. **Password Security**
   - Argon2 hashing algorithm
   - Comprehensive REDACTED_SECRET policies
   - Password history tracking

3. **Session Management**
   - Redis-based session storage
   - Session invalidation on security events
   - Device tracking and limits

4. **Rate Limiting**
   - Per-IP and per-user limits
   - Progressive delays
   - Account lockout mechanisms

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Standards

- TypeScript with strict mode
- ESLint and Prettier configuration
- 85% test coverage minimum
- Comprehensive error handling
- Security-first approach

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the test cases for examples

## 🗺️ Roadmap

### Phase 1 ✅ (Completed)

- [x] JWT token management
- [x] User registration/login
- [x] Password policies
- [x] Session management
- [x] RBAC implementation
- [x] MFA support
- [x] FastAPI middleware

### Phase 2 (In Progress)

- [ ] WebAuthn implementation
- [ ] OAuth2 provider integration
- [ ] Advanced audit logging
- [ ] Real-time session monitoring

### Phase 3 (Planned)

- [ ] SSO integration
- [ ] Advanced fraud detection
- [ ] Multi-tenant support
- [ ] Mobile app support
