"""Enterprise Data Models
Task T025-T034 - Phase 18 Production System Integration

Production-grade data models with comprehensive type annotations,
relationships, and enterprise patterns.
"""

from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ServiceRegistry(Base):
    """Service registry for microservice discovery and management"""

    __tablename__ = "service_registry"

    # Primary key
    service_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Core service information
    service_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    service_version: Mapped[str] = mapped_column(String(50), nullable=False)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)

    # Network configuration
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    health_check_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Health monitoring configuration
    health_check_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    health_timeout_seconds: Mapped[int] = mapped_column(Integer, default=5)

    # Resource requirements
    resource_requirements: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    # Service metadata
    endpoints: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON)
    dependencies: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON)
    labels: Mapped[Optional[dict[str, str]]] = mapped_column(JSON)

    # Status and timestamps
    status: Mapped[str] = mapped_column(String(50), default="HEALTHY")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    health_checks = relationship(
        "ServiceHealthCheck", back_populates="service", cascade="all, delete-orphan"
    )
    metrics = relationship(
        "ServiceMetrics", back_populates="service", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_service_registry_name", "service_name"),
        Index("ix_service_registry_env_type", "environment", "service_type"),
        Index("ix_service_registry_status", "status"),
        Index("ix_service_registry_created_at", "created_at"),
    )


class ServiceHealthCheck(Base):
    """Service health check history and status"""

    __tablename__ = "service_health_checks"

    # Primary key
    health_check_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign key to service
    service_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("service_registry.service_id"),
        nullable=False,
    )

    # Health check results
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Check metadata
    check_type: Mapped[str] = mapped_column(String(50), default="HTTP")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    service = relationship("ServiceRegistry", back_populates="health_checks")

    # Indexes for performance
    __table_args__ = (
        Index("ix_health_checks_service_timestamp", "service_id", "timestamp"),
        Index("ix_health_checks_status", "status"),
        Index("ix_health_checks_timestamp", "timestamp"),
    )


class ServiceMetrics(Base):
    """Service performance metrics"""

    __tablename__ = "service_metrics"

    # Primary key
    metric_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign key to service
    service_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("service_registry.service_id"),
        nullable=False,
    )

    # Metric data
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_labels: Mapped[Optional[dict[str, str]]] = mapped_column(JSON)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    service = relationship("ServiceRegistry", back_populates="metrics")

    # Indexes for performance
    __table_args__ = (
        Index(
            "ix_metrics_service_name_timestamp",
            "service_id",
            "metric_name",
            "timestamp",
        ),
        Index("ix_metrics_timestamp", "timestamp"),
        Index("ix_metrics_name", "metric_name"),
    )


class APIGatewayRoute(Base):
    """API Gateway routing configuration"""

    __tablename__ = "api_gateway_routes"

    # Primary key
    route_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Route configuration
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    target_service: Mapped[str] = mapped_column(String(255), nullable=False)
    target_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Route metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    authentication_required: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    # Status and timestamps
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_routes_path_method", "path", "method"),
        Index("ix_routes_target_service", "target_service"),
        Index("ix_routes_active", "is_active"),
        UniqueConstraint("path", "method", name="uq_routes_path_method"),
    )


class SystemAlert(Base):
    """System alerts and notifications"""

    __tablename__ = "system_alerts"

    # Primary key
    alert_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Alert information
    alert_name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")

    # Alert details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    service_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Alert metadata
    labels: Mapped[Optional[dict[str, str]]] = mapped_column(JSON)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255))
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Indexes for performance
    __table_args__ = (
        Index("ix_alerts_severity_status", "severity", "status"),
        Index("ix_alerts_service", "service_name"),
        Index("ix_alerts_created_at", "created_at"),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low', 'info')",
            name="ck_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved')", name="ck_alerts_status"
        ),
    )
