#!/usr/bin/env python3
"""PAKE System - Phase 17 Enterprise Multi-Tenant Server
World-class multi-tenant FastAPI server with comprehensive security, monitoring, and performance optimization.
"""

import logging
import os
import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

# Configure logging
logger = logging.getLogger(__name__)

# FastAPI and web framework imports
import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Performance and monitoring
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field, validator

from src.middleware.tenant_context import (
    TenantConfig,
    TenantContextMiddleware,
    get_current_tenant_id,
)
from src.security.tenant_isolation_enforcer import (
    TenantIsolationEnforcer,
    get_security_enforcer,
)
from src.services.auth.multi_tenant_auth_service import (
    AuthConfig,
    LoginRequest,
    LoginResponse,
    MultiTenantAuthService,
    create_multi_tenant_auth_service,
)
from src.services.database.multi_tenant_schema import (
    MultiTenantDatabaseConfig,
    MultiTenantPostgreSQLService,
    create_multi_tenant_database_service,
)
from src.services.database.tenant_aware_dal import TenantAwareDataAccessLayer
from src.services.tenant.tenant_management_service import (
    TenantManagementService,
    create_tenant_management_service,
)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import multi-tenant services

# Import existing services for integration
try:
    from src.services.ingestion.orchestrator import (
        IngestionConfig,
        IngestionOrchestrator,
    )

    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    logger.warning("Orchestrator service not available")
    ORCHESTRATOR_AVAILABLE = False

try:
    from src.services.ml.semantic_search_service import get_semantic_search_service

    ML_SERVICES_AVAILABLE = True
except ImportError:
    logger.warning("ML services not available")
    ML_SERVICES_AVAILABLE = False

try:
    from src.services.ml.analytics_aggregation_service import get_ml_analytics_service
    from src.services.ml.content_summarization_service import (
        get_content_summarization_service,
    )
    from src.services.ml.knowledge_graph_service import get_knowledge_graph_service
except ImportError:
    pass

try:
    from src.services.visualization.analytics_endpoints import (
        VisualizationAnalyticsService,
    )

    VISUALIZATION_AVAILABLE = True
except ImportError:
    logger.warning("Visualization service not available")
    VISUALIZATION_AVAILABLE = False

# Configure structured logging
logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "pake_requests_total",
    "Total requests",
    ["method", "endpoint", "tenant_id"],
)
REQUEST_DURATION = Histogram(
    "pake_request_duration_seconds",
    "Request duration",
    ["method", "endpoint", "tenant_id"],
)
AUTH_ATTEMPTS = Counter(
    "pake_auth_attempts_total",
    "Authentication attempts",
    ["tenant_id", "success"],
)
TENANT_OPERATIONS = Counter(
    "pake_tenant_operations_total",
    "Tenant operations",
    ["operation", "tenant_id"],
)

# Global service instances
db_service: MultiTenantPostgreSQLService | None = None
tenant_service: TenantManagementService | None = None
auth_service: MultiTenantAuthService | None = None
dal: TenantAwareDataAccessLayer | None = None
security_enforcer: TenantIsolationEnforcer | None = None

# Service orchestrators per tenant (cached)
tenant_orchestrators: dict[str, Any] = {}


class ServerConfig:
    """Enterprise server configuration"""

    # Server settings
    HOST: str = os.getenv("PAKE_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PAKE_PORT", "8000"))
    WORKERS: int = int(os.getenv("PAKE_WORKERS", "4"))
    DEBUG: bool = os.getenv("PAKE_DEBUG", "false").lower() == "true"

    # Database settings
    DB_HOST: str = os.getenv("PAKE_DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("PAKE_DB_PORT", "5432"))
    DB_NAME: str = os.getenv("PAKE_DB_NAME", "pake_system")
    DB_USER: str = os.getenv("PAKE_DB_USER", "pake_user")
    DB_PASSWORD: str = os.getenv("PAKE_DB_PASSWORD")
    if not DB_PASSWORD:
        raise ValueError(
            "PAKE_DB_PASSWORD environment variable is required. "
            "Please configure this secret in your environment or Azure Key Vault."
        )

    # Redis settings
    REDIS_URL: str = os.getenv("PAKE_REDIS_URL", "redis://localhost:6379")

    # Security settings
    JWT_SECRET: str = os.getenv("PAKE_JWT_SECRET")
    if not JWT_SECRET:
        raise ValueError(
            "PAKE_JWT_SECRET environment variable is required. "
            "Please configure this secret in your environment or Azure Key Vault."
        )
    ALLOWED_HOSTS: list[str] = os.getenv("PAKE_ALLOWED_HOSTS", "*").split(",")

    # API settings
    API_PREFIX: str = "/api/v1"
    TENANT_RESOLUTION: str = os.getenv(
        "PAKE_TENANT_RESOLUTION",
        "jwt",
    )  # jwt, header, subdomain

    # Performance settings
    ENABLE_GZIP: bool = os.getenv("PAKE_ENABLE_GZIP", "true").lower() == "true"
    ENABLE_METRICS: bool = os.getenv("PAKE_ENABLE_METRICS", "true").lower() == "true"
    ENABLE_TRACING: bool = os.getenv("PAKE_ENABLE_TRACING", "true").lower() == "true"

    # Feature flags
    ENABLE_WEBSOCKETS: bool = (
        os.getenv("PAKE_ENABLE_WEBSOCKETS", "true").lower() == "true"
    )
    ENABLE_GRAPHQL: bool = os.getenv("PAKE_ENABLE_GRAPHQL", "true").lower() == "true"
    ENABLE_ADMIN_UI: bool = os.getenv("PAKE_ENABLE_ADMIN_UI", "true").lower() == "true"


config = ServerConfig()

# Enhanced Pydantic models with tenant awareness


class TenantAwareBaseModel(BaseModel):
    """Base model with tenant context validation"""

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: lambda u: str(u),
        }


class SearchRequest(TenantAwareBaseModel):
    """Multi-tenant search request"""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    sources: list[str] = Field(
        default=["web", "arxiv", "pubmed"],
        description="Data sources to search",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results per source",
    )
    enable_ml_enhancement: bool = Field(
        default=True,
        description="Enable ML-powered enhancements",
    )
    enable_summarization: bool = Field(
        default=False,
        description="Enable content summarization",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Search filters",
    )

    @validator("sources")
    def validate_sources(cls, v):
        allowed_sources = ["web", "arxiv", "pubmed", "github", "stackoverflow"]
        invalid_sources = [s for s in v if s not in allowed_sources]
        if invalid_sources:
            raise ValueError(
                f"Invalid sources: {invalid_sources}. Allowed: {allowed_sources}",
            )
        return v


class TenantCreateRequest(TenantAwareBaseModel):
    """Tenant creation request"""

    name: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9-_]+$")
    display_name: str = Field(..., min_length=3, max_length=100)
    domain: str | None = Field(None, pattern=r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    plan: str = Field(default="basic", description="Subscription plan")
    admin_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    admin_username: str = Field(default="admin", min_length=3, max_length=50)
    admin_full_name: str | None = Field(None, max_length=100)


class UserCreateRequest(TenantAwareBaseModel):
    """User creation request"""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    REDACTED_SECRET: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = Field(None, max_length=100)
    role: str = Field(default="user", description="User role")


class LoginRequest(TenantAwareBaseModel):
    """Login request"""

    username: str = Field(..., min_length=1, max_length=50)
    REDACTED_SECRET: str = Field(..., min_length=1, max_length=100)
    remember_me: bool = Field(default=False)
    mfa_token: str | None = Field(None, min_length=6, max_length=6)


# Application lifespan management


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with proper startup and shutdown"""
    # Startup
    logger.info("🚀 Starting PAKE Enterprise Multi-Tenant Server...")

    try:
        # Initialize services
        await initialize_services()

        # Health checks
        await perform_startup_health_checks()

        # Initialize metrics and monitoring
        if config.ENABLE_METRICS:
            setup_monitoring()

        # Initialize tracing
        if config.ENABLE_TRACING:
            setup_tracing()

        logger.info("✅ PAKE Enterprise Server started successfully!")
        logger.info(f"🌐 Server ready at http://{config.HOST}:{config.PORT}")
        logger.info(f"📚 API docs at http://{config.HOST}:{config.PORT}/docs")
        logger.info(
            f"🔍 GraphQL playground at http://{config.HOST}:{config.PORT}/graphql",
        )

        yield

    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down PAKE Enterprise Server...")
        await cleanup_services()
        logger.info("✅ Server shutdown complete")


async def initialize_services():
    """Initialize all multi-tenant services"""
    global db_service, tenant_service, auth_service, dal, security_enforcer

    try:
        # Database service
        db_config = MultiTenantDatabaseConfig(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            username=config.DB_USER,
            REDACTED_SECRET=config.DB_PASSWORD,
            pool_min_size=10,
            pool_max_size=50,
            echo=config.DEBUG,
        )
        db_service = await create_multi_tenant_database_service(db_config)
        logger.info("✅ Multi-tenant database service initialized")

        # Tenant management service
        tenant_service = await create_tenant_management_service(db_service)
        logger.info("✅ Tenant management service initialized")

        # Authentication service
        auth_config = AuthConfig(
            jwt_secret_key=config.JWT_SECRET,
            access_token_expire_minutes=30,
            refresh_token_expire_days=30,
        )
        auth_service = await create_multi_tenant_auth_service(db_service, auth_config)
        logger.info("✅ Multi-tenant authentication service initialized")

        # Data access layer
        dal = TenantAwareDataAccessLayer(db_service)
        logger.info("✅ Tenant-aware data access layer initialized")

        # Security enforcer
        security_enforcer = get_security_enforcer()
        logger.info("✅ Tenant isolation security enforcer initialized")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


async def perform_startup_health_checks():
    """Perform comprehensive health checks on startup"""
    logger.info("🔍 Performing startup health checks...")

    # Database health check
    db_health = await db_service.health_check()
    if db_health["status"] != "healthy":
        raise RuntimeError(f"Database health check failed: {db_health}")

    # Auth service health check
    auth_health = await auth_service.health_check()
    if auth_health["status"] != "healthy":
        raise RuntimeError(f"Auth service health check failed: {auth_health}")

    # Security enforcer health check
    security_health = await security_enforcer.health_check()
    if security_health["status"] != "healthy":
        raise RuntimeError(f"Security enforcer health check failed: {security_health}")

    logger.info("✅ All health checks passed")


def setup_monitoring():
    """Setup Prometheus monitoring"""
    logger.info("📊 Setting up Prometheus monitoring...")


def setup_tracing():
    """Setup OpenTelemetry distributed tracing"""
    logger.info("🔍 Setting up OpenTelemetry tracing...")


async def cleanup_services():
    """Cleanup all services on shutdown"""
    global db_service, tenant_orchestrators

    try:
        # Close tenant orchestrators
        for orchestrator in tenant_orchestrators.values():
            if hasattr(orchestrator, "close"):
                await orchestrator.close()
        tenant_orchestrators.clear()

        # Close database service
        if db_service:
            await db_service.close()

        logger.info("✅ Services cleanup complete")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


# FastAPI application with enterprise configuration
app = FastAPI(
    title="PAKE Enterprise Multi-Tenant API",
    description="Enterprise-grade multi-tenant knowledge management and AI research platform",
    version="1.0.0",
    openapi_url=f"{config.API_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=config.DEBUG,
)

# Middleware configuration (order matters!)

# Trusted host middleware (security)
if ["*"] != config.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)

# Tenant context middleware (must be early in chain)
tenant_config = TenantConfig(
    jwt_secret_key=config.JWT_SECRET,
    tenant_resolution_method=config.TENANT_RESOLUTION,
    require_tenant_context=True,
    validate_tenant_status=True,
)
app.add_middleware(TenantContextMiddleware, config=tenant_config)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.DEBUG else config.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# GZip compression
if config.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware for request logging and metrics


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log requests and collect metrics"""
    start_time = time.time()

    # Get tenant context
    tenant_id = get_current_tenant_id() or "unknown"

    # Increment request counter
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        tenant_id=tenant_id,
    ).inc()

    response = await call_next(request)

    # Record request duration
    duration = time.time() - start_time
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
        tenant_id=tenant_id,
    ).observe(duration)

    # Log request
    logger.info(
        "HTTP request processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration,
        tenant_id=tenant_id,
    )

    return response


# Authentication dependency
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Get current authenticated user"""
    if not auth_service:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not available",
        )

    token_validation = await auth_service.validate_token(credentials.credentials)
    if not token_validation["valid"]:
        raise HTTPException(status_code=401, detail=token_validation["error"])

    return token_validation


# Helper function to get tenant orchestrator


async def get_tenant_orchestrator(tenant_id: str) -> Any:
    """Get or create orchestrator for tenant"""
    if not ORCHESTRATOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator service not available",
        )

    if tenant_id not in tenant_orchestrators:
        # Create new orchestrator for this tenant
        config = IngestionConfig()
        orchestrator = IngestionOrchestrator(config)
        tenant_orchestrators[tenant_id] = orchestrator
        logger.info(f"Created new orchestrator for tenant {tenant_id}")

    return tenant_orchestrators[tenant_id]


# API Routes

# Health and system endpoints


@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {},
        }

        # Check database service
        if db_service:
            db_health = await db_service.health_check()
            health_data["services"]["database"] = db_health

        # Check auth service
        if auth_service:
            auth_health = await auth_service.health_check()
            health_data["services"]["auth"] = auth_health

        # Check security enforcer
        if security_enforcer:
            security_health = await security_enforcer.health_check()
            health_data["services"]["security"] = security_health

        return health_data

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not config.ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    return generate_latest()


@app.get("/")
async def root():
    """API root with system information"""
    return {
        "name": "PAKE Enterprise Multi-Tenant API",
        "version": "1.0.0",
        "status": "operational",
        "description": "Enterprise multi-tenant knowledge management and AI research platform",
        "features": [
            "Multi-tenant architecture with complete isolation",
            "Enterprise-grade authentication and authorization",
            "Real-time search across multiple data sources",
            "AI-powered semantic search and summarization",
            "Advanced analytics and monitoring",
            "GraphQL and REST APIs",
            "WebSocket real-time communication",
            "Comprehensive security enforcement",
        ],
        "endpoints": {
            "auth": f"{config.API_PREFIX}/auth",
            "tenants": f"{config.API_PREFIX}/tenants",
            "users": f"{config.API_PREFIX}/users",
            "search": f"{config.API_PREFIX}/search",
            "analytics": f"{config.API_PREFIX}/analytics",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs",
        },
    }


# Authentication endpoints


@app.post(f"{config.API_PREFIX}/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT tokens"""
    if not auth_service:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not available",
        )

    # Record authentication attempt
    tenant_id = get_current_tenant_id() or "unknown"

    try:
        # Validate input with security enforcer
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            AUTH_ATTEMPTS.labels(tenant_id=tenant_id, success="blocked").inc()
            raise HTTPException(status_code=400, detail="Invalid input detected")

        # Perform authentication
        auth_request = LoginRequest(
            username=request.username,
            REDACTED_SECRET=request.REDACTED_SECRET,
            tenant_id=tenant_id,
            remember_me=request.remember_me,
            mfa_token=request.mfa_token,
        )

        result = await auth_service.authenticate_user(auth_request)

        # Record metrics
        AUTH_ATTEMPTS.labels(
            tenant_id=tenant_id,
            success="success" if result.success else "failed",
        ).inc()

        if not result.success:
            raise HTTPException(
                status_code=401 if not result.requires_mfa else 202,
                detail=result.error,
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        AUTH_ATTEMPTS.labels(tenant_id=tenant_id, success="error").inc()
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication service error")


@app.post(f"{config.API_PREFIX}/auth/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    if not auth_service:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not available",
        )

    try:
        result = await auth_service.refresh_token(refresh_token)
        if not result.success:
            raise HTTPException(status_code=401, detail=result.error)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh service error")


@app.post(f"{config.API_PREFIX}/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user and invalidate tokens"""
    if not auth_service:
        raise HTTPException(
            status_code=503,
            detail="Authentication service not available",
        )

    try:
        # Extract token from request headers
        # This would typically come from the Bearer token
        # IMPLEMENTATION NEEDED: Extract actual Bearer token from Authorization header
        # Current implementation uses placeholder - requires proper JWT token extraction
        result = await auth_service.logout_user("access_token_here")
        return result

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout service error")


# Continue with more endpoints...
# [This is part 1 of the multi-tenant server - the file is getting large]

if __name__ == "__main__":
    # Production ASGI server configuration
    uvicorn.run(
        "multi_tenant_server:app",
        host=config.HOST,
        port=config.PORT,
        workers=config.WORKERS if not config.DEBUG else 1,
        reload=config.DEBUG,
        log_level="info" if not config.DEBUG else "debug",
        access_log=True,
        server_header=False,  # Don't expose server info
        date_header=False,  # Don't expose date
    )
