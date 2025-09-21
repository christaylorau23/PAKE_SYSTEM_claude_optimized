# Data Model: Phase 18 Production System Integration

**Branch**: `phase-18-production-integration` | **Date**: 2025-09-20 | **Spec**: [spec.md](spec.md)

## Overview

This document defines the comprehensive data model for Phase 18 Production System Integration, establishing the foundation for enterprise-grade service orchestration, performance optimization, and observability infrastructure.

The data model supports 50+ microservices with unified management, comprehensive monitoring, and enterprise-scale performance requirements including sub-second response times for 1000+ concurrent users.

## Core Domain Models

### Service Registry & Discovery

#### ServiceRegistry

```python
@dataclass(frozen=True)
class ServiceRegistry:
    """Central registry for all PAKE System microservices"""
    service_id: UUID
    service_name: str  # Unique identifier (e.g., "orchestrator", "api_gateway")
    service_version: str  # Semantic version (e.g., "18.1.0")
    service_type: ServiceType  # Enum: API, WORKER, SCHEDULER, GATEWAY
    environment: Environment  # Enum: DEVELOPMENT, STAGING, PRODUCTION

    # Network Configuration
    endpoints: List[ServiceEndpoint]
    base_url: str
    internal_port: int
    external_port: Optional[int] = None
    protocol: Protocol = Protocol.HTTP  # Enum: HTTP, HTTPS, GRPC

    # Health & Monitoring
    health_check_url: str
    health_check_interval_seconds: int = 30
    health_timeout_seconds: int = 5

    # Dependencies & Relationships
    dependencies: List[ServiceDependency]
    dependent_services: List[str] = field(default_factory=list)

    # Resource Requirements
    resource_requirements: ResourceSpecification
    scaling_config: AutoScalingConfiguration

    # Metadata & Configuration
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle Management
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN

    # Security & Authentication
    authentication_required: bool = True
    authorization_policies: List[AuthorizationPolicy] = field(default_factory=list)
    tls_config: Optional[TLSConfiguration] = None
```

#### ServiceEndpoint

```python
@dataclass(frozen=True)
class ServiceEndpoint:
    """Individual service endpoint definition"""
    endpoint_id: UUID
    service_id: UUID
    path: str  # API path (e.g., "/api/v1/research")
    method: HTTPMethod  # Enum: GET, POST, PUT, DELETE, PATCH

    # API Specification
    openapi_spec: Dict[str, Any]  # OpenAPI 3.1 specification
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None

    # Performance & Rate Limiting
    rate_limit: RateLimitConfig
    timeout_seconds: int = 30
    retry_policy: RetryPolicy
    circuit_breaker_config: CircuitBreakerConfig

    # Security Configuration
    authentication_required: bool = True
    authorization_required: bool = True
    allowed_roles: List[str] = field(default_factory=list)

    # Monitoring & Analytics
    monitoring_enabled: bool = True
    logging_level: LogLevel = LogLevel.INFO
    metrics_collection: MetricsConfig

    # Documentation
    description: str
    tags: List[str] = field(default_factory=list)
    deprecation_date: Optional[datetime] = None
```

#### ServiceDependency

```python
@dataclass(frozen=True)
class ServiceDependency:
    """Service dependency relationship"""
    dependency_id: UUID
    dependent_service_id: UUID  # Service that depends on another
    provider_service_id: UUID   # Service being depended upon
    dependency_type: DependencyType  # Enum: HARD, SOFT, OPTIONAL

    # Connection Configuration
    connection_config: ConnectionConfig
    fallback_strategy: FallbackStrategy = FallbackStrategy.GRACEFUL_DEGRADATION

    # Health & Monitoring
    health_check_enabled: bool = True
    dependency_timeout_seconds: int = 10
    circuit_breaker_enabled: bool = True

    # Performance Requirements
    max_response_time_ms: int = 500
    expected_availability: float = 0.999  # 99.9%

    # Metadata
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
```

### Performance & Monitoring

#### PerformanceMetrics

```python
@dataclass(frozen=True)
class PerformanceMetrics:
    """Comprehensive performance metrics collection"""
    metric_id: UUID
    service_id: UUID
    timestamp: datetime

    # Request Performance
    request_metrics: RequestMetrics

    # System Performance
    system_metrics: SystemMetrics

    # Business Metrics
    business_metrics: BusinessMetrics

    # Infrastructure Metrics
    infrastructure_metrics: InfrastructureMetrics

    # Aggregation Metadata
    aggregation_period: timedelta
    sample_count: int
    collection_method: MetricCollectionMethod  # PUSH, PULL, STREAM
```

#### RequestMetrics

```python
@dataclass(frozen=True)
class RequestMetrics:
    """HTTP request performance metrics"""
    total_requests: int
    successful_requests: int
    failed_requests: int

    # Response Time Distribution
    response_time_p50_ms: float
    response_time_p90_ms: float
    response_time_p95_ms: float
    response_time_p99_ms: float
    average_response_time_ms: float
    max_response_time_ms: float
    min_response_time_ms: float

    # Throughput Metrics
    requests_per_second: float
    requests_per_minute: float

    # Error Analysis
    error_rate_percentage: float
    errors_by_status_code: Dict[int, int]
    timeout_count: int

    # Endpoint Breakdown
    endpoint_metrics: Dict[str, EndpointMetrics]
```

#### SystemMetrics

```python
@dataclass(frozen=True)
class SystemMetrics:
    """System resource utilization metrics"""

    # CPU Metrics
    cpu_usage_percentage: float
    cpu_cores_available: int
    cpu_load_average: float

    # Memory Metrics
    memory_usage_percentage: float
    memory_used_mb: float
    memory_available_mb: float
    memory_peak_mb: float

    # Disk Metrics
    disk_usage_percentage: float
    disk_read_iops: float
    disk_write_iops: float
    disk_read_mb_per_second: float
    disk_write_mb_per_second: float

    # Network Metrics
    network_in_mb_per_second: float
    network_out_mb_per_second: float
    network_connections_active: int
    network_latency_ms: float

    # Application Metrics
    thread_count: int
    active_connections: int
    queue_depth: int
    garbage_collection_time_ms: float
```

#### CachePerformanceMetrics

```python
@dataclass(frozen=True)
class CachePerformanceMetrics:
    """Multi-level cache performance tracking"""
    cache_instance_id: UUID
    cache_type: CacheType  # Enum: L1_MEMORY, L2_REDIS, DISTRIBUTED
    timestamp: datetime

    # Hit Rate Metrics
    total_operations: int
    cache_hits: int
    cache_misses: int
    hit_rate_percentage: float

    # Performance Metrics
    average_get_latency_ms: float
    average_set_latency_ms: float
    p95_get_latency_ms: float
    p95_set_latency_ms: float

    # Memory Management
    memory_used_mb: float
    memory_available_mb: float
    memory_utilization_percentage: float
    eviction_count: int

    # Key Management
    total_keys: int
    expired_keys: int
    key_size_distribution: Dict[str, int]  # Size ranges to count

    # Cache Warming & Invalidation
    warming_operations: int
    invalidation_operations: int
    invalidation_by_tag: Dict[str, int]

    # Cluster Metrics (for distributed caches)
    cluster_nodes: int
    cluster_healthy_nodes: int
    cluster_sync_lag_ms: float
    data_replication_factor: int
```

### Service Mesh & Communication

#### ServiceMeshConfiguration

```python
@dataclass(frozen=True)
class ServiceMeshConfiguration:
    """Istio service mesh configuration"""
    mesh_id: UUID
    mesh_name: str
    version: str

    # Network Configuration
    network_config: NetworkConfiguration
    security_config: SecurityConfiguration
    traffic_config: TrafficConfiguration

    # Service Discovery
    service_discovery: ServiceDiscoveryConfig
    load_balancing: LoadBalancingConfig

    # Observability
    telemetry_config: TelemetryConfiguration
    distributed_tracing: TracingConfiguration

    # Policy Management
    security_policies: List[SecurityPolicy]
    traffic_policies: List[TrafficPolicy]
    access_policies: List[AccessPolicy]

    # Metadata
    created_at: datetime
    updated_at: datetime
    environment: Environment
```

#### CircuitBreakerConfiguration

```python
@dataclass(frozen=True)
class CircuitBreakerConfiguration:
    """Circuit breaker pattern configuration"""
    circuit_breaker_id: UUID
    service_id: UUID
    target_service_id: UUID

    # Threshold Configuration
    failure_threshold: int = 5  # Number of failures before opening
    timeout_duration_seconds: int = 60  # How long to stay open
    success_threshold: int = 3  # Successes needed to close

    # Monitoring Window
    monitoring_window_seconds: int = 300  # 5 minutes
    minimum_request_threshold: int = 10

    # Failure Detection
    failure_criteria: List[FailureCriteria]
    timeout_threshold_ms: int = 5000

    # Recovery Strategy
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
    max_retry_attempts: int = 3

    # State Management
    current_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    state_changed_at: datetime
    failure_count: int = 0
    success_count: int = 0

    # Fallback Configuration
    fallback_enabled: bool = True
    fallback_response: Optional[Dict[str, Any]] = None
    fallback_service_id: Optional[UUID] = None
```

### Database & Storage

#### DatabaseConfiguration

```python
@dataclass(frozen=True)
class DatabaseConfiguration:
    """PostgreSQL database configuration and optimization"""
    database_id: UUID
    database_name: str
    database_type: DatabaseType = DatabaseType.POSTGRESQL

    # Connection Configuration
    connection_config: DatabaseConnectionConfig
    connection_pool_config: ConnectionPoolConfiguration

    # Performance Configuration
    performance_config: DatabasePerformanceConfig
    query_optimization: QueryOptimizationConfig
    index_management: IndexManagementConfig

    # High Availability
    replication_config: ReplicationConfiguration
    backup_config: BackupConfiguration
    disaster_recovery: DisasterRecoveryConfig

    # Monitoring & Alerting
    monitoring_config: DatabaseMonitoringConfig
    slow_query_threshold_ms: int = 1000

    # Security Configuration
    security_config: DatabaseSecurityConfig
    encryption_config: EncryptionConfiguration

    # Metadata
    created_at: datetime
    updated_at: datetime
    environment: Environment
    version: str
```

#### ConnectionPoolConfiguration

```python
@dataclass(frozen=True)
class ConnectionPoolConfiguration:
    """Database connection pool optimization"""
    pool_id: UUID
    database_id: UUID

    # Pool Size Configuration
    min_connections: int = 10
    max_connections: int = 100
    initial_connections: int = 20

    # Connection Lifecycle
    max_connection_age_seconds: int = 3600  # 1 hour
    connection_timeout_seconds: int = 30
    idle_timeout_seconds: int = 600  # 10 minutes

    # Health Checking
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 60
    health_check_query: str = "SELECT 1"

    # Performance Tuning
    connection_validation_timeout_ms: int = 500
    leak_detection_threshold_ms: int = 30000

    # Scaling Configuration
    auto_scaling_enabled: bool = True
    scale_up_threshold_percentage: float = 0.8  # 80% utilization
    scale_down_threshold_percentage: float = 0.3  # 30% utilization

    # Monitoring
    metrics_collection_enabled: bool = True
    connection_usage_tracking: bool = True
```

### Authentication & Authorization

#### AuthenticationConfiguration

```python
@dataclass(frozen=True)
class AuthenticationConfiguration:
    """JWT-based authentication system configuration"""
    auth_config_id: UUID

    # JWT Configuration
    jwt_config: JWTConfiguration
    token_validation: TokenValidationConfig

    # Security Policies
    REDACTED_SECRET_policy: PasswordPolicy
    account_lockout_policy: AccountLockoutPolicy
    session_management: SessionManagementConfig

    # Multi-Factor Authentication
    mfa_config: MFAConfiguration
    mfa_required_roles: List[str] = field(default_factory=list)

    # OAuth & External Providers
    oauth_providers: List[OAuthProviderConfig] = field(default_factory=list)
    saml_config: Optional[SAMLConfiguration] = None

    # Audit & Compliance
    audit_config: AuthenticationAuditConfig
    compliance_requirements: List[ComplianceRequirement]

    # Rate Limiting
    rate_limiting: AuthenticationRateLimitConfig

    # Environment & Deployment
    environment: Environment
    created_at: datetime
    updated_at: datetime
```

#### UserSession

```python
@dataclass(frozen=True)
class UserSession:
    """Active user session tracking"""
    session_id: UUID
    user_id: UUID

    # Session Metadata
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime

    # Authentication Details
    authentication_method: AuthenticationMethod  # PASSWORD, MFA, OAUTH, SAML
    authentication_timestamp: datetime
    ip_address: str
    user_agent: str

    # Authorization Context
    roles: List[str]
    permissions: List[Permission]
    scopes: List[str] = field(default_factory=list)

    # Security Tracking
    risk_score: float = 0.0  # 0.0 = low risk, 1.0 = high risk
    security_events: List[SecurityEvent] = field(default_factory=list)

    # Session State
    status: SessionStatus = SessionStatus.ACTIVE
    device_fingerprint: Optional[str] = None
    geo_location: Optional[GeoLocation] = None
```

### Observability & Alerting

#### DistributedTrace

```python
@dataclass(frozen=True)
class DistributedTrace:
    """OpenTelemetry distributed trace representation"""
    trace_id: str  # 32-character hex string

    # Trace Metadata
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None

    # Spans Collection
    spans: List[TraceSpan]
    root_span_id: Optional[str] = None

    # Service Topology
    services_involved: List[str]
    service_dependencies: Dict[str, List[str]]  # Service -> Dependencies

    # Status & Errors
    status: TraceStatus = TraceStatus.OK
    error_count: int = 0
    error_details: List[TraceError] = field(default_factory=list)

    # Business Context
    user_id: Optional[UUID] = None
    correlation_id: Optional[str] = None
    business_transaction_id: Optional[str] = None

    # Performance Analysis
    critical_path: List[str] = field(default_factory=list)  # Span IDs
    bottleneck_spans: List[str] = field(default_factory=list)

    # Sampling & Collection
    sampling_rate: float = 1.0
    collection_agent: str
    tags: Dict[str, str] = field(default_factory=dict)
```

#### TraceSpan

```python
@dataclass(frozen=True)
class TraceSpan:
    """Individual span within a distributed trace"""
    span_id: str  # 16-character hex string
    trace_id: str  # Parent trace ID
    parent_span_id: Optional[str] = None

    # Span Timing
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None

    # Service Context
    service_name: str
    operation_name: str
    span_kind: SpanKind  # CLIENT, SERVER, PRODUCER, CONSUMER, INTERNAL

    # Status & Errors
    status: SpanStatus = SpanStatus.OK
    status_message: Optional[str] = None
    error_details: Optional[SpanError] = None

    # Attributes & Tags
    attributes: Dict[str, Any] = field(default_factory=dict)
    resource_attributes: Dict[str, str] = field(default_factory=dict)

    # Events & Logs
    events: List[SpanEvent] = field(default_factory=list)

    # Links to Other Spans
    links: List[SpanLink] = field(default_factory=list)
```

#### AlertRule

```python
@dataclass(frozen=True)
class AlertRule:
    """Comprehensive alerting rule configuration"""
    rule_id: UUID
    rule_name: str

    # Rule Definition
    metric_query: str  # PromQL expression
    condition: AlertCondition
    threshold_value: float
    comparison_operator: ComparisonOperator  # GT, LT, EQ, NE, GTE, LTE

    # Trigger Configuration
    evaluation_interval_seconds: int = 60
    for_duration_seconds: int = 300  # How long condition must be true

    # Severity & Priority
    severity: AlertSeverity  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    priority: AlertPriority = AlertPriority.NORMAL

    # Notification Configuration
    notification_channels: List[NotificationChannel]
    escalation_policy: EscalationPolicy

    # Context & Documentation
    description: str
    runbook_url: Optional[str] = None
    related_dashboards: List[str] = field(default_factory=list)

    # Labels & Routing
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # State Management
    enabled: bool = True
    last_evaluation: Optional[datetime] = None
    current_state: AlertState = AlertState.NORMAL

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str
    environment: Environment
```

## Configuration Management Models

#### SystemConfiguration

```python
@dataclass(frozen=True)
class SystemConfiguration:
    """Unified system configuration management"""
    config_id: UUID
    config_name: str
    config_version: str

    # Configuration Hierarchy
    environment: Environment
    service_configs: Dict[str, ServiceConfiguration]
    global_configs: Dict[str, Any]

    # Deployment Configuration
    kubernetes_config: KubernetesConfiguration
    deployment_strategy: DeploymentStrategy

    # Security Configuration
    security_config: SecurityConfiguration
    secrets_management: SecretsManagementConfig

    # Monitoring & Observability
    monitoring_config: MonitoringConfiguration
    logging_config: LoggingConfiguration

    # Performance & Scaling
    performance_config: PerformanceConfiguration
    auto_scaling_config: AutoScalingConfiguration

    # Validation & Compliance
    validation_rules: List[ValidationRule]
    compliance_policies: List[CompliancePolicy]

    # Change Management
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None
    rollback_config: Optional[UUID] = None  # Previous config for rollback
```

## Enum Definitions

```python
# Service Types
class ServiceType(Enum):
    API_GATEWAY = "api_gateway"
    MICROSERVICE = "microservice"
    WORKER_SERVICE = "worker_service"
    SCHEDULER_SERVICE = "scheduler_service"
    DATA_SERVICE = "data_service"

# Environment Types
class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

# Service Status
class ServiceStatus(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"

# Performance Metrics
class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

# Circuit Breaker States
class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

# Alert Severities
class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

# Trace Status
class TraceStatus(Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"

# Authentication Methods
class AuthenticationMethod(Enum):
    PASSWORD = "REDACTED_SECRET"
    MFA = "mfa"
    OAUTH = "oauth"
    SAML = "saml"
    API_KEY = "api_key"
```

## Database Schema

### Primary Tables

```sql
-- Service Registry
CREATE TABLE service_registry (
    service_id UUID PRIMARY KEY,
    service_name VARCHAR(255) UNIQUE NOT NULL,
    service_version VARCHAR(50) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    environment VARCHAR(50) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    health_check_url VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'unknown',
    configuration JSONB,
    labels JSONB,
    annotations JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    CONSTRAINT valid_service_type CHECK (service_type IN ('api_gateway', 'microservice', 'worker_service', 'scheduler_service', 'data_service')),
    CONSTRAINT valid_environment CHECK (environment IN ('development', 'staging', 'production', 'testing')),
    CONSTRAINT valid_status CHECK (status IN ('unknown', 'healthy', 'degraded', 'unhealthy', 'maintenance'))
);

-- Performance Metrics (Time-series optimized)
CREATE TABLE performance_metrics (
    metric_id UUID PRIMARY KEY,
    service_id UUID REFERENCES service_registry(service_id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit VARCHAR(50),
    labels JSONB,
    aggregation_period INTERVAL,
    sample_count INTEGER,

    -- Partitioning by time for efficient querying
    PARTITION BY RANGE (timestamp)
);

-- Distributed Traces
CREATE TABLE distributed_traces (
    trace_id VARCHAR(32) PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_ms DOUBLE PRECISION,
    services_involved TEXT[],
    status VARCHAR(20) NOT NULL DEFAULT 'ok',
    error_count INTEGER DEFAULT 0,
    user_id UUID,
    correlation_id VARCHAR(255),
    business_transaction_id VARCHAR(255),
    sampling_rate DOUBLE PRECISION DEFAULT 1.0,
    tags JSONB,

    CONSTRAINT valid_trace_status CHECK (status IN ('ok', 'error', 'timeout'))
);

-- Alert Rules
CREATE TABLE alert_rules (
    rule_id UUID PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    metric_query TEXT NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    comparison_operator VARCHAR(10) NOT NULL,
    evaluation_interval_seconds INTEGER DEFAULT 60,
    for_duration_seconds INTEGER DEFAULT 300,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    runbook_url VARCHAR(500),
    labels JSONB,
    annotations JSONB,
    enabled BOOLEAN DEFAULT true,
    current_state VARCHAR(20) DEFAULT 'normal',
    environment VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,

    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    CONSTRAINT valid_comparison CHECK (comparison_operator IN ('gt', 'lt', 'eq', 'ne', 'gte', 'lte')),
    CONSTRAINT valid_alert_state CHECK (current_state IN ('normal', 'pending', 'firing', 'resolved'))
);

-- Cache Performance Metrics
CREATE TABLE cache_performance (
    cache_metric_id UUID PRIMARY KEY,
    cache_instance_id UUID NOT NULL,
    cache_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    total_operations BIGINT NOT NULL,
    cache_hits BIGINT NOT NULL,
    cache_misses BIGINT NOT NULL,
    hit_rate_percentage DOUBLE PRECISION GENERATED ALWAYS AS (
        CASE WHEN total_operations > 0
        THEN (cache_hits::DOUBLE PRECISION / total_operations::DOUBLE PRECISION) * 100
        ELSE 0 END
    ) STORED,
    average_get_latency_ms DOUBLE PRECISION,
    average_set_latency_ms DOUBLE PRECISION,
    memory_used_mb DOUBLE PRECISION,
    memory_available_mb DOUBLE PRECISION,
    total_keys BIGINT,
    eviction_count BIGINT,

    CONSTRAINT valid_cache_type CHECK (cache_type IN ('l1_memory', 'l2_redis', 'distributed')),
    PARTITION BY RANGE (timestamp)
);
```

### Indexes for Performance

```sql
-- Service Registry Indexes
CREATE INDEX idx_service_registry_name ON service_registry(service_name);
CREATE INDEX idx_service_registry_type_env ON service_registry(service_type, environment);
CREATE INDEX idx_service_registry_status ON service_registry(status);
CREATE INDEX idx_service_registry_updated ON service_registry(updated_at);

-- Performance Metrics Indexes (for time-series queries)
CREATE INDEX idx_performance_metrics_service_time ON performance_metrics(service_id, timestamp DESC);
CREATE INDEX idx_performance_metrics_name_time ON performance_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_performance_metrics_labels ON performance_metrics USING GIN (labels);

-- Trace Indexes
CREATE INDEX idx_traces_start_time ON distributed_traces(start_time DESC);
CREATE INDEX idx_traces_duration ON distributed_traces(duration_ms);
CREATE INDEX idx_traces_services ON distributed_traces USING GIN (services_involved);
CREATE INDEX idx_traces_user ON distributed_traces(user_id);
CREATE INDEX idx_traces_correlation ON distributed_traces(correlation_id);

-- Alert Rules Indexes
CREATE INDEX idx_alert_rules_enabled ON alert_rules(enabled);
CREATE INDEX idx_alert_rules_severity ON alert_rules(severity);
CREATE INDEX idx_alert_rules_environment ON alert_rules(environment);
CREATE INDEX idx_alert_rules_state ON alert_rules(current_state);

-- Cache Performance Indexes
CREATE INDEX idx_cache_perf_instance_time ON cache_performance(cache_instance_id, timestamp DESC);
CREATE INDEX idx_cache_perf_type_time ON cache_performance(cache_type, timestamp DESC);
CREATE INDEX idx_cache_perf_hit_rate ON cache_performance(hit_rate_percentage);
```

## Data Validation Rules

### Service Registry Validation

```python
def validate_service_registry(service: ServiceRegistry) -> List[ValidationError]:
    """Comprehensive validation for service registry entries"""
    errors = []

    # Service Name Validation
    if not re.match(r'^[a-z0-9_-]+$', service.service_name):
        errors.append(ValidationError("service_name must contain only lowercase letters, numbers, underscores, and hyphens"))

    # Version Validation (Semantic Versioning)
    if not re.match(r'^\d+\.\d+\.\d+$', service.service_version):
        errors.append(ValidationError("service_version must follow semantic versioning (x.y.z)"))

    # URL Validation
    if not service.base_url.startswith(('http://', 'https://')):
        errors.append(ValidationError("base_url must be a valid HTTP/HTTPS URL"))

    # Health Check URL
    if not service.health_check_url.startswith(('http://', 'https://')):
        errors.append(ValidationError("health_check_url must be a valid HTTP/HTTPS URL"))

    # Resource Requirements
    if service.resource_requirements.cpu_request_millicores < 100:
        errors.append(ValidationError("minimum CPU request is 100 millicores"))

    if service.resource_requirements.memory_request_mb < 128:
        errors.append(ValidationError("minimum memory request is 128 MB"))

    return errors
```

### Performance Metrics Validation

```python
def validate_performance_metrics(metrics: PerformanceMetrics) -> List[ValidationError]:
    """Validate performance metrics for consistency and accuracy"""
    errors = []

    # Response Time Validation
    if metrics.request_metrics.response_time_p95_ms < metrics.request_metrics.response_time_p50_ms:
        errors.append(ValidationError("p95 response time cannot be less than p50"))

    if metrics.request_metrics.response_time_p99_ms < metrics.request_metrics.response_time_p95_ms:
        errors.append(ValidationError("p99 response time cannot be less than p95"))

    # Error Rate Validation
    if not 0 <= metrics.request_metrics.error_rate_percentage <= 100:
        errors.append(ValidationError("error_rate_percentage must be between 0 and 100"))

    # Resource Utilization Validation
    if not 0 <= metrics.system_metrics.cpu_usage_percentage <= 100:
        errors.append(ValidationError("cpu_usage_percentage must be between 0 and 100"))

    if not 0 <= metrics.system_metrics.memory_usage_percentage <= 100:
        errors.append(ValidationError("memory_usage_percentage must be between 0 and 100"))

    return errors
```

## Migration Strategy

### Phase 1: Core Service Registry (Week 1-2)
- Implement ServiceRegistry and ServiceEndpoint models
- Create database schema and indexes
- Develop service discovery mechanisms
- Set up basic health checking

### Phase 2: Performance & Monitoring (Week 3-4)
- Add PerformanceMetrics and related models
- Implement time-series data collection
- Create monitoring dashboards
- Set up basic alerting

### Phase 3: Service Mesh Integration (Week 5-6)
- Implement ServiceMeshConfiguration models
- Add circuit breaker and retry logic
- Integrate with Istio service mesh
- Set up secure inter-service communication

### Phase 4: Advanced Features (Week 7-8)
- Add distributed tracing models
- Implement comprehensive alerting
- Set up auto-scaling configurations
- Add security and authentication models

## Performance Considerations

### Database Optimization
- **Partitioning**: Time-series tables partitioned by timestamp
- **Indexing**: Strategic B-tree and GIN indexes for common query patterns
- **Connection Pooling**: Optimized pool sizes for concurrent access
- **Read Replicas**: Separate read workloads from write operations

### Cache Strategy
- **L1 Cache**: In-memory LRU cache for frequently accessed configuration
- **L2 Cache**: Redis cluster for distributed caching
- **Cache Warming**: Proactive loading of critical configuration data
- **Invalidation**: Tag-based invalidation for efficient cache management

### Data Retention
- **Metrics Retention**:
  - Raw data: 7 days
  - 1-minute aggregates: 30 days
  - 1-hour aggregates: 1 year
  - Daily aggregates: 5 years
- **Trace Retention**: 14 days for detailed traces, 90 days for summaries
- **Log Retention**: 30 days for application logs, 1 year for audit logs

---

*This data model follows PAKE System Constitution v1.0.0 principles and supports the enterprise-grade requirements defined in the Phase 18 specification.*