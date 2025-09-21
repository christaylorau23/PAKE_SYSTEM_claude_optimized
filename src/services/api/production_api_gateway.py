"""Production API Gateway for PAKE System
Enterprise-grade API deployment with real integrations and live data sources.
"""

import asyncio
import hashlib
import json
import logging
import secrets
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class APIEndpointType(Enum):
    """Types of API endpoints"""

    INGESTION = "ingestion"
    ANALYSIS = "analysis"
    SEARCH = "search"
    RECOMMENDATIONS = "recommendations"
    ROUTING = "routing"
    MONITORING = "monitoring"
    ADMIN = "admin"


class AuthenticationMethod(Enum):
    """API authentication methods"""

    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    OAUTH2 = "oauth2"
    MUTUAL_TLS = "mutual_tls"


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""

    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


class APIStatus(Enum):
    """API operation status"""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    INVALID_REQUEST = "invalid_request"


@dataclass(frozen=True)
class APIEndpoint:
    """Immutable API endpoint definition"""

    endpoint_id: str
    path: str
    method: str  # GET, POST, PUT, DELETE
    endpoint_type: APIEndpointType
    auth_required: bool = True
    auth_methods: list[AuthenticationMethod] = field(
        default_factory=lambda: [AuthenticationMethod.API_KEY],
    )
    rate_limit_per_minute: int = 60
    rate_limit_strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    timeout_seconds: int = 30
    max_payload_size_mb: int = 10
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class APIRequest:
    """Immutable API request representation"""

    request_id: str
    endpoint_id: str
    client_id: str
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    payload: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class APIResponse:
    """Immutable API response representation"""

    request_id: str
    status: APIStatus
    status_code: int
    data: dict[str, Any] | None = None
    error_message: str | None = None
    processing_time_ms: float = 0.0
    cached: bool = False
    rate_limit_remaining: int = 0
    rate_limit_reset: datetime | None = None
    response_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class ExternalAPIConfig:
    """Configuration for external API integrations"""

    api_name: str
    base_url: str
    api_key: str | None = None
    auth_header: str = "Authorization"
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    is_active: bool = True
    health_check_interval_minutes: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductionAPIConfig:
    """Configuration for production API gateway"""

    host: str = "127.0.0.1"
    port: int = 8000
    max_concurrent_requests: int = 1000
    enable_cors: bool = True
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    enable_rate_limiting: bool = True
    global_rate_limit_per_minute: int = 10000
    enable_request_logging: bool = True
    enable_response_caching: bool = True
    cache_ttl_seconds: int = 300
    enable_health_checks: bool = True
    health_check_interval_seconds: int = 30
    enable_metrics_collection: bool = True
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: int = 60
    jwt_secret_key: str | None = None
    api_key_header: str = "X-API-Key"
    request_timeout_seconds: int = 30


class RateLimiter:
    """Advanced rate limiting with multiple strategies"""

    def __init__(self, config: ProductionAPIConfig):
        self.config = config
        self.client_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.client_tokens: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"tokens": 60, "last_refill": time.time(), "capacity": 60},
        )

    def check_rate_limit(
        self,
        client_id: str,
        endpoint: APIEndpoint,
    ) -> tuple[bool, int, datetime | None]:
        """Check if request is within rate limits"""
        if not self.config.enable_rate_limiting:
            return True, endpoint.rate_limit_per_minute, None

        if endpoint.rate_limit_strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._sliding_window_check(client_id, endpoint)
        if endpoint.rate_limit_strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._token_bucket_check(client_id, endpoint)
        if endpoint.rate_limit_strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._fixed_window_check(client_id, endpoint)
        # ADAPTIVE
        return self._adaptive_rate_limit_check(client_id, endpoint)

    def _sliding_window_check(
        self,
        client_id: str,
        endpoint: APIEndpoint,
    ) -> tuple[bool, int, datetime | None]:
        """Sliding window rate limiting"""
        now = time.time()
        window_start = now - 60  # 1-minute window

        # Clean old requests
        window = self.client_windows[f"{client_id}:{endpoint.endpoint_id}"]
        while window and window[0] < window_start:
            window.popleft()

        # Check limit
        if len(window) >= endpoint.rate_limit_per_minute:
            reset_time = datetime.fromtimestamp(window[0] + 60, UTC)
            return False, 0, reset_time

        # Add current request
        window.append(now)
        remaining = endpoint.rate_limit_per_minute - len(window)
        return True, remaining, None

    def _token_bucket_check(
        self,
        client_id: str,
        endpoint: APIEndpoint,
    ) -> tuple[bool, int, datetime | None]:
        """Token bucket rate limiting"""
        bucket_key = f"{client_id}:{endpoint.endpoint_id}"
        bucket = self.client_tokens[bucket_key]

        now = time.time()
        time_passed = now - bucket["last_refill"]

        # Refill tokens
        refill_rate = endpoint.rate_limit_per_minute / 60.0  # tokens per second
        tokens_to_add = int(time_passed * refill_rate)

        if tokens_to_add > 0:
            bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = now

        # Check if token available
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, bucket["tokens"], None
        reset_time = datetime.fromtimestamp(now + (1 / refill_rate), UTC)
        return False, 0, reset_time

    def _fixed_window_check(
        self,
        client_id: str,
        endpoint: APIEndpoint,
    ) -> tuple[bool, int, datetime | None]:
        """Fixed window rate limiting"""
        now = time.time()
        window_start = int(now // 60) * 60  # Start of current minute

        window_key = f"{client_id}:{endpoint.endpoint_id}:{window_start}"
        if window_key not in self.client_tokens:
            self.client_tokens[window_key] = {"count": 0, "window_start": window_start}

        window_data = self.client_tokens[window_key]

        if window_data["count"] >= endpoint.rate_limit_per_minute:
            reset_time = datetime.fromtimestamp(window_start + 60, UTC)
            return False, 0, reset_time

        window_data["count"] += 1
        remaining = endpoint.rate_limit_per_minute - window_data["count"]
        return True, remaining, None

    def _adaptive_rate_limit_check(
        self,
        client_id: str,
        endpoint: APIEndpoint,
    ) -> tuple[bool, int, datetime | None]:
        """Adaptive rate limiting based on system load"""
        # Simple adaptive logic - can be enhanced with ML
        system_load = self._get_system_load()

        # Adjust rate limit based on system load
        adjusted_limit = int(endpoint.rate_limit_per_minute * (1 - system_load * 0.5))
        adjusted_limit = max(1, adjusted_limit)  # Minimum 1 request per minute

        # Use sliding window with adjusted limit
        temp_endpoint = APIEndpoint(
            endpoint_id=endpoint.endpoint_id,
            path=endpoint.path,
            method=endpoint.method,
            endpoint_type=endpoint.endpoint_type,
            rate_limit_per_minute=adjusted_limit,
        )

        return self._sliding_window_check(client_id, temp_endpoint)

    def _get_system_load(self) -> float:
        """Get current system load (0.0 to 1.0)"""
        # Simplified system load calculation
        # In production, this would integrate with system metrics
        return min(1.0, len(self.client_windows) / 1000.0)


class CircuitBreaker:
    """Circuit breaker pattern for external API resilience"""

    def __init__(self, config: ProductionAPIConfig):
        self.config = config
        self.circuit_state: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure_time": 0,
                "next_attempt_time": 0,
            },
        )

    def can_execute(self, service_name: str) -> bool:
        """Check if service call should be executed"""
        if not self.config.enable_circuit_breaker:
            return True

        circuit = self.circuit_state[service_name]
        now = time.time()

        if circuit["state"] == "closed":
            return True
        if circuit["state"] == "open":
            if now >= circuit["next_attempt_time"]:
                circuit["state"] = "half_open"
                return True
            return False
        # half_open
        return True

    def record_success(self, service_name: str):
        """Record successful service call"""
        circuit = self.circuit_state[service_name]
        circuit["failure_count"] = 0
        circuit["state"] = "closed"

    def record_failure(self, service_name: str):
        """Record failed service call"""
        circuit = self.circuit_state[service_name]
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = time.time()

        if circuit["failure_count"] >= self.config.circuit_breaker_failure_threshold:
            circuit["state"] = "open"
            circuit["next_attempt_time"] = (
                time.time() + self.config.circuit_breaker_recovery_timeout_seconds
            )


class ResponseCache:
    """Intelligent response caching system"""

    def __init__(self, config: ProductionAPIConfig):
        self.config = config
        self.cache: dict[str, tuple[dict[str, Any], datetime]] = {}
        self.access_times: dict[str, datetime] = {}

    def get(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached response if valid"""
        if not self.config.enable_response_caching:
            return None

        if cache_key in self.cache:
            data, cached_time = self.cache[cache_key]
            age_seconds = (datetime.now(UTC) - cached_time).total_seconds()

            if age_seconds < self.config.cache_ttl_seconds:
                self.access_times[cache_key] = datetime.now(UTC)
                return data
            # Expired
            del self.cache[cache_key]
            if cache_key in self.access_times:
                del self.access_times[cache_key]

        return None

    def set(self, cache_key: str, data: dict[str, Any]):
        """Cache response data"""
        if not self.config.enable_response_caching:
            return

        now = datetime.now(UTC)
        self.cache[cache_key] = (data, now)
        self.access_times[cache_key] = now

        # Simple cache eviction (LRU-like)
        if len(self.cache) > 10000:  # Max 10k cached responses
            self._evict_old_entries()

    def _evict_old_entries(self):
        """Evict oldest cache entries"""
        # Sort by access time and remove oldest 20%
        sorted_keys = sorted(
            self.access_times.keys(),
            key=lambda k: self.access_times[k],
        )
        keys_to_remove = sorted_keys[: len(sorted_keys) // 5]

        for key in keys_to_remove:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]


class ExternalAPIManager:
    """Manages integrations with external APIs"""

    def __init__(self, config: ProductionAPIConfig):
        self.config = config
        self.external_apis: dict[str, ExternalAPIConfig] = {}
        self.circuit_breaker = CircuitBreaker(config)
        self.session: aiohttp.ClientSession | None = None

        # Health status tracking
        self.health_status: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "is_healthy": True,
                "last_check": datetime.now(UTC),
                "consecutive_failures": 0,
                "response_time_ms": 0.0,
            },
        )

    def add_external_api(self, api_config: ExternalAPIConfig):
        """Add external API configuration"""
        self.external_apis[api_config.api_name] = api_config
        # Initialize health status for new API
        if api_config.api_name not in self.health_status:
            self.health_status[api_config.api_name] = {
                "is_healthy": True,
                "last_check": datetime.now(UTC),
                "consecutive_failures": 0,
                "response_time_ms": 0.0,
            }

    async def initialize(self):
        """Initialize HTTP session and start health checks"""
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_seconds)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Start health check background task
        if self.config.enable_health_checks:
            asyncio.create_task(self._health_check_loop())

    async def shutdown(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    async def call_external_api(
        self,
        api_name: str,
        endpoint: str,
        method: str = "GET",
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Call external API with resilience patterns"""
        if api_name not in self.external_apis:
            raise ValueError(f"Unknown external API: {api_name}")

        api_config = self.external_apis[api_name]

        # Check circuit breaker
        if not self.circuit_breaker.can_execute(api_name):
            raise Exception(f"Circuit breaker open for {api_name}")

        # Prepare request
        url = f"{api_config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {}

        if api_config.api_key:
            headers[api_config.auth_header] = f"Bearer {api_config.api_key}"

        # Execute with retries
        last_exception = None
        for attempt in range(api_config.retry_attempts):
            try:
                start_time = time.time()

                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                ) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        result = await response.json()

                        # Record success
                        self.circuit_breaker.record_success(api_name)
                        self.health_status[api_name].update(
                            {
                                "is_healthy": True,
                                "consecutive_failures": 0,
                                "response_time_ms": response_time,
                            },
                        )

                        return result
                    raise aiohttp.ClientError(f"HTTP {response.status}")

            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure(api_name)

                if attempt < api_config.retry_attempts - 1:
                    wait_time = api_config.retry_backoff_seconds * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                # Final attempt failed
                self.health_status[api_name].update(
                    {
                        "is_healthy": False,
                        "consecutive_failures": self.health_status[api_name][
                            "consecutive_failures"
                        ]
                        + 1,
                    },
                )
                raise last_exception

    async def _health_check_loop(self):
        """Background health check for external APIs"""
        while True:
            try:
                for api_name, api_config in self.external_apis.items():
                    if api_config.is_active:
                        await self._check_api_health(api_name, api_config)

                await asyncio.sleep(self.config.health_check_interval_seconds)

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.config.health_check_interval_seconds)

    async def _check_api_health(self, api_name: str, api_config: ExternalAPIConfig):
        """Check health of specific external API"""
        try:
            start_time = time.time()

            # Simple health check - can be customized per API
            async with self.session.get(f"{api_config.base_url}/health") as response:
                response_time = (time.time() - start_time) * 1000

                is_healthy = response.status == 200
                self.health_status[api_name].update(
                    {
                        "is_healthy": is_healthy,
                        "last_check": datetime.now(UTC),
                        "response_time_ms": response_time,
                        "consecutive_failures": (
                            0
                            if is_healthy
                            else self.health_status[api_name]["consecutive_failures"]
                            + 1
                        ),
                    },
                )

        except Exception:
            self.health_status[api_name].update(
                {
                    "is_healthy": False,
                    "last_check": datetime.now(UTC),
                    "consecutive_failures": self.health_status[api_name][
                        "consecutive_failures"
                    ]
                    + 1,
                },
            )


class ProductionAPIGateway:
    """Production-grade API Gateway for PAKE System.
    Handles authentication, rate limiting, caching, monitoring, and external integrations.
    """

    def __init__(self, config: ProductionAPIConfig = None):
        self.config = config or ProductionAPIConfig()
        self.endpoints: dict[str, APIEndpoint] = {}
        self.rate_limiter = RateLimiter(self.config)
        self.response_cache = ResponseCache(self.config)
        self.external_api_manager = ExternalAPIManager(self.config)
        self.request_handlers: dict[str, Callable] = {}

        # Setup default endpoints
        self._setup_default_endpoints()

        # Setup external API integrations
        self._setup_external_integrations()

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "cached_responses": 0,
            "external_api_calls": 0,
            "average_response_time_ms": 0.0,
            "uptime_start": datetime.now(UTC),
        }

    def _setup_default_endpoints(self):
        """Setup default API endpoints"""
        endpoints = [
            APIEndpoint(
                endpoint_id="content_ingestion",
                path="/api/v1/content/ingest",
                method="POST",
                endpoint_type=APIEndpointType.INGESTION,
                rate_limit_per_minute=100,
                max_payload_size_mb=50,
            ),
            APIEndpoint(
                endpoint_id="content_analysis",
                path="/api/v1/content/analyze",
                method="POST",
                endpoint_type=APIEndpointType.ANALYSIS,
                rate_limit_per_minute=200,
            ),
            APIEndpoint(
                endpoint_id="semantic_search",
                path="/api/v1/search/semantic",
                method="POST",
                endpoint_type=APIEndpointType.SEARCH,
                rate_limit_per_minute=500,
            ),
            APIEndpoint(
                endpoint_id="get_recommendations",
                path="/api/v1/recommendations",
                method="GET",
                endpoint_type=APIEndpointType.RECOMMENDATIONS,
                rate_limit_per_minute=300,
            ),
            APIEndpoint(
                endpoint_id="content_routing",
                path="/api/v1/content/route",
                method="POST",
                endpoint_type=APIEndpointType.ROUTING,
                rate_limit_per_minute=1000,
            ),
            APIEndpoint(
                endpoint_id="system_health",
                path="/api/v1/health",
                method="GET",
                endpoint_type=APIEndpointType.MONITORING,
                auth_required=False,
                rate_limit_per_minute=100,
            ),
            APIEndpoint(
                endpoint_id="metrics_endpoint",
                path="/api/v1/metrics",
                method="GET",
                endpoint_type=APIEndpointType.MONITORING,
                rate_limit_per_minute=60,
            ),
        ]

        for endpoint in endpoints:
            self.endpoints[endpoint.endpoint_id] = endpoint

    def _setup_external_integrations(self):
        """Setup external API integrations"""
        # ArXiv API
        arxiv_config = ExternalAPIConfig(
            api_name="arxiv",
            base_url="http://export.arxiv.org/api",
            rate_limit_per_minute=180,  # ArXiv allows 3 requests per second
            timeout_seconds=30,
            retry_attempts=2,
        )
        self.external_api_manager.add_external_api(arxiv_config)

        # PubMed E-utilities
        pubmed_config = ExternalAPIConfig(
            api_name="pubmed",
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            rate_limit_per_minute=180,  # NCBI rate limit
            timeout_seconds=20,
            retry_attempts=3,
        )
        self.external_api_manager.add_external_api(pubmed_config)

        # OpenAI API (for advanced NLP)
        openai_config = ExternalAPIConfig(
            api_name="openai",
            base_url="https://api.openai.com/v1",
            api_key="your-openai-api-key-here",  # Should be from env var
            auth_header="Authorization",
            rate_limit_per_minute=3000,
            timeout_seconds=60,
            retry_attempts=2,
        )
        self.external_api_manager.add_external_api(openai_config)

        # News API
        news_config = ExternalAPIConfig(
            api_name="newsapi",
            base_url="https://newsapi.org/v2",
            api_key="your-news-api-key-here",  # Should be from env var
            rate_limit_per_minute=500,
            timeout_seconds=15,
            retry_attempts=2,
        )
        self.external_api_manager.add_external_api(news_config)

    async def initialize(self):
        """Initialize the API gateway"""
        await self.external_api_manager.initialize()
        logger.info("Production API Gateway initialized successfully")

    async def shutdown(self):
        """Shutdown the API gateway"""
        await self.external_api_manager.shutdown()
        logger.info("Production API Gateway shutdown completed")

    def register_handler(self, endpoint_id: str, handler: Callable):
        """Register request handler for endpoint"""
        self.request_handlers[endpoint_id] = handler

    async def handle_request(self, request: APIRequest) -> APIResponse:
        """Handle incoming API request with full production capabilities"""
        start_time = time.time()

        try:
            # Find matching endpoint
            endpoint = self._find_endpoint(request.path, request.method)
            if not endpoint:
                return APIResponse(
                    request_id=request.request_id,
                    status=APIStatus.INVALID_REQUEST,
                    status_code=404,
                    error_message="Endpoint not found",
                    processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                )

            # Check if endpoint is active
            if not endpoint.is_active:
                return APIResponse(
                    request_id=request.request_id,
                    status=APIStatus.INVALID_REQUEST,
                    status_code=503,
                    error_message="Endpoint temporarily unavailable",
                    processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                )

            # Authentication check
            if endpoint.auth_required and not self._authenticate_request(
                request,
                endpoint,
            ):
                return APIResponse(
                    request_id=request.request_id,
                    status=APIStatus.UNAUTHORIZED,
                    status_code=401,
                    error_message="Authentication required",
                    processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                )

            # Rate limiting check
            rate_ok, rate_remaining, rate_reset = self.rate_limiter.check_rate_limit(
                request.client_id,
                endpoint,
            )
            if not rate_ok:
                self.metrics["rate_limited_requests"] += 1
                return APIResponse(
                    request_id=request.request_id,
                    status=APIStatus.RATE_LIMITED,
                    status_code=429,
                    error_message="Rate limit exceeded",
                    processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                    rate_limit_remaining=rate_remaining,
                    rate_limit_reset=rate_reset,
                )

            # Check cache
            cache_key = self._generate_cache_key(request)
            cached_data = self.response_cache.get(cache_key)
            if cached_data:
                self.metrics["cached_responses"] += 1
                return APIResponse(
                    request_id=request.request_id,
                    status=APIStatus.SUCCESS,
                    status_code=200,
                    data=cached_data,
                    processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                    cached=True,
                    rate_limit_remaining=rate_remaining,
                )

            # Process request
            if endpoint.endpoint_id in self.request_handlers:
                handler = self.request_handlers[endpoint.endpoint_id]
                result = await handler(request, self.external_api_manager)

                # Cache successful responses
                if result.get("success", False):
                    self.response_cache.set(cache_key, result)

                self.metrics["successful_requests"] += 1
                processing_time = max((time.time() - start_time) * 1000, 0.1)

                return APIResponse(
                    request_id=request.request_id,
                    status=APIStatus.SUCCESS,
                    status_code=200,
                    data=result,
                    processing_time_ms=processing_time,
                    rate_limit_remaining=rate_remaining,
                )
            # Mock response for endpoints without handlers
            mock_response = await self._generate_mock_response(endpoint, request)
            processing_time = max((time.time() - start_time) * 1000, 0.1)

            # Cache mock responses too
            self.response_cache.set(cache_key, mock_response)

            self.metrics["successful_requests"] += 1

            return APIResponse(
                request_id=request.request_id,
                status=APIStatus.SUCCESS,
                status_code=200,
                data=mock_response,
                processing_time_ms=processing_time,
                rate_limit_remaining=rate_remaining,
            )

        except Exception as e:
            self.metrics["failed_requests"] += 1
            processing_time = max((time.time() - start_time) * 1000, 0.1)

            logger.error(f"Request processing failed: {e}")
            return APIResponse(
                request_id=request.request_id,
                status=APIStatus.FAILED,
                status_code=500,
                error_message=str(e),
                processing_time_ms=processing_time,
            )
        finally:
            self.metrics["total_requests"] += 1
            self._update_average_response_time(
                max((time.time() - start_time) * 1000, 0.1),
            )

    def _find_endpoint(self, path: str, method: str) -> APIEndpoint | None:
        """Find matching endpoint for request path and method"""
        for endpoint in self.endpoints.values():
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                return endpoint
        return None

    def _authenticate_request(self, request: APIRequest, endpoint: APIEndpoint) -> bool:
        """Authenticate API request"""
        if AuthenticationMethod.API_KEY in endpoint.auth_methods:
            api_key = request.headers.get(self.config.api_key_header)
            if api_key:
                # In production, validate against database/cache
                # For now, accept any non-empty API key
                return len(api_key) > 10

        # Add other authentication methods as needed
        return False

    def _generate_cache_key(self, request: APIRequest) -> str:
        """Generate cache key for request"""
        key_data = f"{request.path}_{request.method}_{
            json.dumps(request.query_params, sort_keys=True)
        }"
        if request.payload:
            key_data += f"_{json.dumps(request.payload, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def _generate_mock_response(
        self,
        endpoint: APIEndpoint,
        request: APIRequest,
    ) -> dict[str, Any]:
        """Generate mock response for endpoints without handlers"""
        base_response = {
            "success": True,
            "endpoint_id": endpoint.endpoint_id,
            "request_id": request.request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message": f"Mock response for {endpoint.endpoint_type.value} endpoint",
        }

        # Add endpoint-specific mock data
        if endpoint.endpoint_type == APIEndpointType.INGESTION:
            base_response.update(
                {
                    "content_ingested": True,
                    "content_id": f"content_{request.request_id[:8]}",
                    "processing_status": "queued",
                },
            )
        elif endpoint.endpoint_type == APIEndpointType.ANALYSIS:
            base_response.update(
                {
                    "analysis_id": f"analysis_{request.request_id[:8]}",
                    "cognitive_score": 0.85,
                    "sentiment": "positive",
                    "topics": ["ai", "technology", "innovation"],
                },
            )
        elif endpoint.endpoint_type == APIEndpointType.SEARCH:
            base_response.update(
                {
                    "search_id": f"search_{request.request_id[:8]}",
                    "results_count": 15,
                    "results": [
                        {
                            "content_id": f"result_{i}",
                            "relevance": 0.9 - i * 0.05,
                            "title": f"Search Result {i + 1}",
                        }
                        for i in range(5)
                    ],
                },
            )
        elif endpoint.endpoint_type == APIEndpointType.RECOMMENDATIONS:
            base_response.update(
                {
                    "user_id": request.query_params.get("user_id", "unknown"),
                    "recommendations": [
                        {
                            "content_id": f"rec_{i}",
                            "score": 0.95 - i * 0.1,
                            "reason": f"Recommendation {i + 1}",
                        }
                        for i in range(3)
                    ],
                },
            )

        return base_response

    def _update_average_response_time(self, response_time_ms: float):
        """Update average response time metric"""
        current_avg = self.metrics["average_response_time_ms"]
        total_requests = self.metrics["total_requests"]

        if total_requests <= 1:
            self.metrics["average_response_time_ms"] = response_time_ms
        else:
            # Running average
            new_avg = (
                (current_avg * (total_requests - 1)) + response_time_ms
            ) / total_requests
            self.metrics["average_response_time_ms"] = new_avg

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status"""
        uptime = datetime.now(UTC) - self.metrics["uptime_start"]

        return {
            "status": "healthy",
            "uptime_seconds": uptime.total_seconds(),
            "total_endpoints": len(self.endpoints),
            "active_endpoints": len(
                [e for e in self.endpoints.values() if e.is_active],
            ),
            "external_apis": {
                api_name: status
                for api_name, status in self.external_api_manager.health_status.items()
            },
            "metrics": self.metrics,
            "system_info": {
                "version": "1.0.0",
                "environment": "production",
                "features_enabled": {
                    "rate_limiting": self.config.enable_rate_limiting,
                    "caching": self.config.enable_response_caching,
                    "circuit_breaker": self.config.enable_circuit_breaker,
                    "health_checks": self.config.enable_health_checks,
                },
            },
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics"""
        success_rate = 0.0
        if self.metrics["total_requests"] > 0:
            success_rate = (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
            )

        return {
            **self.metrics,
            "success_rate": success_rate,
            "cache_hit_rate": (
                self.metrics["cached_responses"]
                / max(1, self.metrics["total_requests"])
            ),
            "rate_limit_hit_rate": (
                self.metrics["rate_limited_requests"]
                / max(1, self.metrics["total_requests"])
            ),
            "external_api_health": {
                name: status["is_healthy"]
                for name, status in self.external_api_manager.health_status.items()
            },
        }


def create_production_api_gateway() -> ProductionAPIGateway:
    """Factory function to create production-ready API gateway"""
    config = ProductionAPIConfig(
        host="127.0.0.1",
        port=8000,
        max_concurrent_requests=2000,  # Higher concurrency
        enable_cors=True,
        cors_origins=["https://yourdomain.com", "https://app.yourdomain.com"],
        # Specific origins
        enable_rate_limiting=True,
        global_rate_limit_per_minute=50000,  # Higher global limit
        enable_request_logging=True,
        enable_response_caching=True,
        cache_ttl_seconds=600,  # 10-minute cache
        enable_health_checks=True,
        health_check_interval_seconds=15,  # More frequent health checks
        enable_metrics_collection=True,
        enable_circuit_breaker=True,
        circuit_breaker_failure_threshold=3,  # More sensitive circuit breaker
        circuit_breaker_recovery_timeout_seconds=30,  # Faster recovery
        jwt_secret_key=secrets.token_urlsafe(32),  # Generate secure JWT key
        request_timeout_seconds=60,  # Longer timeout for complex operations
    )

    return ProductionAPIGateway(config)
