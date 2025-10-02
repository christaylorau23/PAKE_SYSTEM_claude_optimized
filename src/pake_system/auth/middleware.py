"""Authentication middleware for enhanced security
Implements rate limiting, security headers, and request validation
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent brute force attacks.

    Implements sliding window rate limiting with configurable limits
    for different endpoint types.
    """

    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests: dict[str, deque] = defaultdict(deque)
        self.burst_requests: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old requests (older than 1 minute)
        self._clean_old_requests(client_ip, current_time)

        # Check burst limit (requests in last 10 seconds)
        if self._check_burst_limit(client_ip, current_time):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": "10"},
            )

        # Check rate limit (requests per minute)
        if self._check_rate_limit(client_ip, current_time):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"},
            )

        # Record this request
        self.requests[client_ip].append(current_time)
        self.burst_requests[client_ip].append(current_time)

        response = await call_next(request)
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        # Check for forwarded IP (when behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, client_ip: str, current_time: float):
        """Remove requests older than 1 minute."""
        minute_ago = current_time - 60
        while self.requests[client_ip] and self.requests[client_ip][0] < minute_ago:
            self.requests[client_ip].popleft()

        # Clean burst requests older than 10 seconds
        ten_seconds_ago = current_time - 10
        while (
            self.burst_requests[client_ip]
            and self.burst_requests[client_ip][0] < ten_seconds_ago
        ):
            self.burst_requests[client_ip].popleft()

    def _check_burst_limit(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded burst limit."""
        return len(self.burst_requests[client_ip]) >= self.burst_limit

    def _check_rate_limit(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded rate limit."""
        return len(self.requests[client_ip]) >= self.requests_per_minute


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware to enhance application security.

    Adds essential security headers to all responses.
    """

    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Strict Transport Security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions Policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            ),
            # Remove server information
            "Server": "PAKE-System",
        }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers to response
        for header, value in self.security_headers.items():
            response.headers[header] = value

        return response


class AuthenticationAuditMiddleware(BaseHTTPMiddleware):
    """Authentication audit middleware for security monitoring.

    Logs authentication attempts and security events for monitoring.
    """

    def __init__(self, app):
        super().__init__(app)
        self.failed_attempts: dict[str, int] = defaultdict(int)
        self.locked_ips: dict[str, float] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Check if IP is temporarily locked
        if client_ip in self.locked_ips:
            if current_time < self.locked_ips[client_ip]:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="IP temporarily locked due to suspicious activity",
                    headers={
                        "Retry-After": str(
                            int(self.locked_ips[client_ip] - current_time)
                        )
                    },
                )
            else:
                # Lock expired, remove it
                del self.locked_ips[client_ip]
                self.failed_attempts[client_ip] = 0

        response = await call_next(request)

        # Audit authentication endpoints
        if request.url.path in ["/auth/token", "/token"]:
            self._audit_auth_request(request, response, client_ip)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _audit_auth_request(self, request: Request, response: Response, client_ip: str):
        """Audit authentication requests for security monitoring."""
        current_time = time.time()

        # Log authentication attempt
        if response.status_code == 200:
            # Successful login
            self.failed_attempts[client_ip] = 0
            # TODO: Log successful authentication to security monitoring system
        elif response.status_code == 401:
            # Failed authentication
            self.failed_attempts[client_ip] += 1

            # Lock IP after 5 failed attempts
            if self.failed_attempts[client_ip] >= 5:
                self.locked_ips[client_ip] = current_time + 900  # 15 minutes
                # TODO: Log IP lockout to security monitoring system

            # TODO: Log failed authentication attempt to security monitoring system


def setup_security_middleware(app):
    """Setup all security middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Add security middleware in order
    app.add_middleware(AuthenticationAuditMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60, burst_limit=10)

    return app
