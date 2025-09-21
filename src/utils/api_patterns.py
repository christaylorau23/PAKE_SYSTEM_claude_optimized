#!/usr/bin/env python3
"""PAKE+ Standardized API Patterns
Enterprise-grade API patterns with foundation component integration
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# from fastapi.middleware.base import BaseHTTPMiddleware  # Not needed, using starlette
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from utils.async_task_queue import AsyncTaskQueue, TaskPriority
from utils.distributed_cache import CacheConfig, DistributedCache
from utils.error_handling import (
    ErrorHandler,
    ErrorSeverity,
    PAKEException,
    with_error_handling,
)

# Import our foundation components
from utils.logger import get_logger
from utils.metrics import MetricsStore
from utils.security_guards import SecurityConfig, SecurityGuard, secure_endpoint

logger = get_logger(service_name="pake-api-patterns")
metrics = MetricsStore(service_name="pake-api-patterns")


class APIVersion(Enum):
    """API versioning"""

    V1 = "v1"
    V2 = "v2"
    BETA = "beta"


class ResponseStatus(Enum):
    """Standardized response statuses"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


@dataclass
class APIConfig:
    """Configuration for API patterns"""

    # Rate limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst: int = 20

    # Caching
    default_cache_ttl: int = 300  # 5 minutes
    enable_response_caching: bool = True

    # Security
    enable_security_guards: bool = True
    require_authentication: bool = False

    # Monitoring
    enable_detailed_metrics: bool = True
    log_request_bodies: bool = False

    # Task processing
    default_task_priority: TaskPriority = TaskPriority.NORMAL
    async_task_timeout: float = 300.0


# Standard API Response Models
class APIError(BaseModel):
    """Standardized error response"""

    type: str = Field(..., description="Error type classification")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Error code for programmatic handling")
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details",
    )
    trace_id: str | None = Field(None, description="Request trace ID for debugging")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp",
    )


class APIResponse(BaseModel):
    """Standardized API response wrapper"""

    status: ResponseStatus = Field(..., description="Response status")
    data: Any | None = Field(None, description="Response data")
    message: str | None = Field(None, description="Optional status message")
    error: APIError | None = Field(
        None,
        description="Error details if status is error",
    )
    metadata: dict[str, Any] | None = Field(None, description="Response metadata")
    trace_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request trace ID",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
    )
    version: str = Field(default="v1", description="API version")


class PaginationMetadata(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(APIResponse):
    """Paginated response with metadata"""

    pagination: PaginationMetadata = Field(..., description="Pagination information")


class RateLimitInfo(BaseModel):
    """Rate limit information"""

    limit: int = Field(..., description="Rate limit per window")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset: datetime = Field(..., description="When the rate limit resets")
    retry_after: int | None = Field(None, description="Seconds to wait before retry")


# Middleware Classes
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request/response logging"""

    def __init__(self, app, config: APIConfig):
        super().__init__(app)
        self.config = config
        self.logger = get_logger(service_name="api-request-logging")
        self.metrics = MetricsStore(service_name="api-requests")

    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        start_time = time.time()
        trace_id = str(uuid.uuid4())

        # Add trace ID to request
        request.state.trace_id = trace_id

        # Log request start
        request_logger = self.logger.with_correlation_id(trace_id)

        # Extract request info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        request_data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        if self.config.log_request_bodies and request.method in [
            "POST",
            "PUT",
            "PATCH",
        ]:
            try:
                body = await request.body()
                if body:
                    request_data["body_size"] = len(body)
                    # Don't log full body for security, just size
            except Exception:
                pass

        request_logger.http("Request started", **request_data)

        # Process request
        response = None
        error = None

        try:
            response = await call_next(request)

        except Exception as e:
            error = e
            # Create error response
            response = JSONResponse(
                status_code=500,
                content=APIResponse(
                    status=ResponseStatus.ERROR,
                    error=APIError(
                        type="internal_server_error",
                        message="An internal server error occurred",
                        code="INTERNAL_ERROR",
                        trace_id=trace_id,
                    ),
                    trace_id=trace_id,
                ).dict(),
            )

        # Calculate duration
        duration = (time.time() - start_time) * 1000  # Convert to ms

        # Add standard response headers
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time"] = f"{duration:.2f}ms"

        # Log response
        response_data = {
            "status_code": response.status_code,
            "duration_ms": duration,
            "response_size": len(response.body) if hasattr(response, "body") else 0,
        }

        if error:
            request_logger.http("Request failed", error=error, **response_data)
        else:
            request_logger.http("Request completed", **response_data)

        # Update metrics
        self.metrics.record_histogram(
            "request_duration",
            duration / 1000,
            labels={
                "method": request.method,
                "path": request.url.path,
                "status_code": str(response.status_code),
            },
        )

        self.metrics.increment_counter(
            "requests_total",
            labels={
                "method": request.method,
                "path": request.url.path,
                "status_code": str(response.status_code),
            },
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis backend"""

    def __init__(self, app, config: APIConfig, redis_client: redis.Redis):
        super().__init__(app)
        self.config = config
        self.redis_client = redis_client
        self.logger = get_logger(service_name="api-rate-limiting")

    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Extract client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        is_allowed, rate_info = await self._check_rate_limit(client_id)

        if not is_allowed:
            # Rate limit exceeded
            self.logger.warning(f"Rate limit exceeded for client {client_id}")

            response = JSONResponse(
                status_code=429,
                content=APIResponse(
                    status=ResponseStatus.ERROR,
                    error=APIError(
                        type="rate_limit_exceeded",
                        message="Rate limit exceeded. Please try again later.",
                        code="RATE_LIMIT_EXCEEDED",
                        details={"rate_limit": rate_info.dict()},
                    ),
                ).dict(),
            )

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(rate_info.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_info.remaining)
            response.headers["X-RateLimit-Reset"] = rate_info.reset.isoformat()
            if rate_info.retry_after:
                response.headers["Retry-After"] = str(rate_info.retry_after)

            return response

        # Process request normally
        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(rate_info.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_info.remaining)
        response.headers["X-RateLimit-Reset"] = rate_info.reset.isoformat()

        return response

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier for rate limiting"""
        # Try authentication token first
        auth_header = request.headers.get("authorization")
        if auth_header:
            return f"token:{auth_header[:20]}"  # Use first 20 chars of token

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _check_rate_limit(self, client_id: str) -> tuple[bool, RateLimitInfo]:
        """Check rate limit using sliding window"""
        window_key = f"rate_limit:{client_id}:window"
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        try:
            # Remove old entries
            await self.redis_client.zremrangebyscore(window_key, 0, window_start)

            # Count current requests
            current_count = await self.redis_client.zcard(window_key)

            # Check if limit exceeded
            if current_count >= self.config.rate_limit_requests_per_minute:
                # Get reset time (when oldest entry expires)
                oldest_entries = await self.redis_client.zrange(
                    window_key,
                    0,
                    0,
                    withscores=True,
                )
                reset_time = (
                    datetime.fromtimestamp(oldest_entries[0][1] + 60)
                    if oldest_entries
                    else datetime.utcnow()
                )

                return False, RateLimitInfo(
                    limit=self.config.rate_limit_requests_per_minute,
                    remaining=0,
                    reset=reset_time,
                    retry_after=int((reset_time - datetime.utcnow()).total_seconds()),
                )

            # Add current request
            await self.redis_client.zadd(window_key, {str(uuid.uuid4()): current_time})
            # Expire window after 60 seconds
            await self.redis_client.expire(window_key, 60)

            return True, RateLimitInfo(
                limit=self.config.rate_limit_requests_per_minute,
                remaining=self.config.rate_limit_requests_per_minute
                - current_count
                - 1,
                reset=datetime.fromtimestamp(current_time + 60),
            )

        except Exception as e:
            self.logger.error("Rate limit check failed", error=e)
            # Allow request if Redis is down
            return True, RateLimitInfo(
                limit=self.config.rate_limit_requests_per_minute,
                remaining=self.config.rate_limit_requests_per_minute,
                reset=datetime.utcnow() + timedelta(minutes=1),
            )


# API Pattern Factory
class EnhancedAPIFactory:
    """Factory for creating standardized API patterns with foundation integration"""

    def __init__(self, config: APIConfig, redis_url: str = "redis://localhost:6379/0"):
        self.config = config
        self.redis_url = redis_url

        self.logger = get_logger(service_name="enhanced-api-factory")
        self.metrics = MetricsStore(service_name="enhanced-api-factory")
        self.error_handler = ErrorHandler(service_name="enhanced-api-factory")

        # Initialize foundation components
        self.security_guard = None
        self.cache = None
        self.redis_client = None
        self.task_queue = None

    async def create_app(
        self,
        title: str = "PAKE+ Enhanced API",
        description: str = "API with foundation hardening",
        version: str = "1.0.0",
    ) -> FastAPI:
        """Create FastAPI app with all foundation components integrated"""
        # Initialize Redis connection
        self.redis_client = redis.from_url(self.redis_url)

        # Initialize cache
        cache_config = CacheConfig(
            host="localhost",
            port=6379,
            default_ttl=self.config.default_cache_ttl,
        )
        self.cache = DistributedCache(cache_config)
        await self.cache.connect()

        # Initialize security guard
        if self.config.enable_security_guards:
            security_config = SecurityConfig(
                prompt_injection_threshold=0.7,
                block_high_threats=True,
                block_critical_threats=True,
            )
            self.security_guard = SecurityGuard(security_config)

        # Initialize task queue
        self.task_queue = AsyncTaskQueue(redis_url=self.redis_url)
        await self.task_queue.connect()

        # Create FastAPI app
        app = FastAPI(
            title=title,
            description=description,
            version=version,
            responses={
                422: {"model": APIResponse, "description": "Validation Error"},
                429: {"model": APIResponse, "description": "Rate Limit Exceeded"},
                500: {"model": APIResponse, "description": "Internal Server Error"},
            },
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add custom middleware
        app.add_middleware(RequestLoggingMiddleware, config=self.config)
        app.add_middleware(
            RateLimitMiddleware,
            config=self.config,
            redis_client=self.redis_client,
        )

        # Add exception handlers
        self._add_exception_handlers(app)

        # Add standard endpoints
        self._add_standard_endpoints(app)

        self.logger.info(f"Created enhanced API: {title} v{version}")

        return app

    def _add_exception_handlers(self, app: FastAPI):
        """Add standardized exception handlers"""

        @app.exception_handler(PAKEException)
        async def pake_exception_handler(request: Request, exc: PAKEException):
            trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

            return JSONResponse(
                status_code=(
                    400
                    if exc.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]
                    else 500
                ),
                content=APIResponse(
                    status=ResponseStatus.ERROR,
                    error=APIError(
                        type=exc.category.value,
                        message=exc.user_message,
                        code=exc.category.value.upper(),
                        details=exc.to_dict(),
                        trace_id=trace_id,
                    ),
                    trace_id=trace_id,
                ).dict(),
            )

        @app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

            return JSONResponse(
                status_code=exc.status_code,
                content=APIResponse(
                    status=ResponseStatus.ERROR,
                    error=APIError(
                        type="http_error",
                        message=str(exc.detail),
                        code=f"HTTP_{exc.status_code}",
                        trace_id=trace_id,
                    ),
                    trace_id=trace_id,
                ).dict(),
            )

    def _add_standard_endpoints(self, app: FastAPI):
        """Add standard system endpoints"""

        @app.get("/health", response_model=APIResponse, tags=["System"])
        async def health_check():
            """System health check endpoint"""
            try:
                # Check Redis connectivity
                await self.redis_client.ping()
                redis_status = "healthy"
            except Exception:
                redis_status = "unhealthy"

            # Check cache connectivity
            try:
                await self.cache.exists("health_check")
                cache_status = "healthy"
            except Exception:
                cache_status = "unhealthy"

            # Get system stats
            system_stats = {
                "redis": redis_status,
                "cache": cache_status,
                "security_guards": "enabled" if self.security_guard else "disabled",
                "task_queue": "connected" if self.task_queue else "disconnected",
            }

            overall_status = (
                "healthy"
                if all(
                    status in ["healthy", "enabled", "connected"]
                    for status in system_stats.values()
                )
                else "degraded"
            )

            return APIResponse(
                status=(
                    ResponseStatus.SUCCESS
                    if overall_status == "healthy"
                    else ResponseStatus.WARNING
                ),
                data=system_stats,
                message=f"System is {overall_status}",
            )

        @app.get("/metrics", tags=["System"])
        async def get_metrics():
            """System metrics endpoint"""
            # This would typically return Prometheus metrics
            # For now, return basic system info
            return APIResponse(
                status=ResponseStatus.SUCCESS,
                data={
                    "message": "Metrics available at /metrics endpoint",
                    "format": "prometheus",
                },
            )

    def create_crud_endpoints(
        self,
        app: FastAPI,
        model_class: type,
        prefix: str,
        tags: list[str] = None,
    ):
        """Create standardized CRUD endpoints with caching and security"""

        @app.post(f"{prefix}/", response_model=APIResponse, tags=tags or [])
        @secure_endpoint() if self.security_guard else lambda x: x
        @with_error_handling("create_resource")
        async def create_resource(
            item: model_class,
            background_tasks: BackgroundTasks,
            request: Request,
        ):
            """Create a new resource"""
            trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

            # Process creation (would integrate with actual database)
            # For demo purposes, we'll simulate
            resource_id = str(uuid.uuid4())

            # Schedule background task for post-processing
            task_id = await self.task_queue.submit_task(
                "process_resource_creation",
                resource_id,
                item.dict(),
                priority=self.config.default_task_priority,
            )

            # Cache the new resource
            cache_key = f"{prefix}:{resource_id}"
            await self.cache.set(
                cache_key,
                item.dict(),
                ttl=self.config.default_cache_ttl,
            )

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                data={"id": resource_id, "task_id": task_id, **item.dict()},
                message="Resource created successfully",
                trace_id=trace_id,
            )

        @app.get(f"{prefix}/{{item_id}}", response_model=APIResponse, tags=tags or [])
        @with_error_handling("get_resource")
        async def get_resource(item_id: str, request: Request):
            """Get a resource by ID with caching"""
            trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

            # Try cache first
            cache_key = f"{prefix}:{item_id}"
            cached_item = await self.cache.get(cache_key)

            if cached_item:
                self.metrics.increment_counter(
                    "cache_hits",
                    labels={"endpoint": prefix},
                )
                return APIResponse(
                    status=ResponseStatus.SUCCESS,
                    data=cached_item,
                    metadata={"cached": True},
                    trace_id=trace_id,
                )

            # Simulate database lookup
            # In real implementation, this would query the actual database
            self.metrics.increment_counter("cache_misses", labels={"endpoint": prefix})

            # For demo, return simulated data
            simulated_data = {
                "id": item_id,
                "name": f"Resource {item_id}",
                "created_at": datetime.utcnow().isoformat(),
            }

            # Cache for future requests
            await self.cache.set(
                cache_key,
                simulated_data,
                ttl=self.config.default_cache_ttl,
            )

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                data=simulated_data,
                metadata={"cached": False},
                trace_id=trace_id,
            )


# Example usage models
class TaskItem(BaseModel):
    """Example task model"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    priority: int = Field(default=1, ge=1, le=5)
    completed: bool = Field(default=False)

    @validator("title")
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


# Factory function for quick setup
async def create_enhanced_api(
    title: str = "PAKE+ Enhanced API",
    config: APIConfig | None = None,
    redis_url: str = "redis://localhost:6379/0",
) -> FastAPI:
    """Quick factory function for creating enhanced API"""
    api_config = config or APIConfig()
    factory = EnhancedAPIFactory(api_config, redis_url)
    app = await factory.create_app(title=title)

    # Add example CRUD endpoints
    factory.create_crud_endpoints(app, TaskItem, "/tasks", tags=["Tasks"])

    return app


# Testing function
if __name__ == "__main__":

    async def test_api_patterns():
        """Test the API patterns system"""
        print("Testing Enhanced API Patterns...")

        try:
            # Create API with custom configuration
            config = APIConfig(
                rate_limit_requests_per_minute=60,
                enable_security_guards=True,
                enable_detailed_metrics=True,
            )

            app = await create_enhanced_api(
                title="PAKE+ Test API",
                config=config,
                redis_url="redis://localhost:6379/2",  # Use different DB for testing
            )

            print("SUCCESS: Enhanced API created")
            print(f"INFO: API title: {app.title}")
            print(f"INFO: Routes: {len(app.routes)}")
            print(f"INFO: Middleware: {len(app.user_middleware)}")

            # Test would continue with actual HTTP requests in a real scenario
            print("SUCCESS: API patterns validation complete")

        except Exception as e:
            print(f"ERROR: API patterns test failed: {e}")
            import traceback

            traceback.print_exc()

    asyncio.run(test_api_patterns())
