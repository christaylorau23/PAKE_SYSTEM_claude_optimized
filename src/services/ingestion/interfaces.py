#!/usr/bin/env python3
"""PAKE System - Ingestion Service Interfaces
Dependency Inversion Principle implementation to break circular dependencies.

This module defines abstract interfaces that high-level modules depend on,
rather than depending on concrete implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid


class SourceType(Enum):
    """Supported ingestion source types"""
    WEB = "web"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    RSS = "rss"
    EMAIL = "email"
    SOCIAL = "social"


class IngestionStatus(Enum):
    """Ingestion execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass(frozen=True)
class IngestionSource:
    """Configuration for a single ingestion source"""
    source_type: str
    priority: int
    query_parameters: dict[str, Any]
    estimated_results: int
    timeout: int
    source_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    retry_count: int = 0
    last_attempt: datetime | None = None
    status: IngestionStatus = IngestionStatus.PENDING


@dataclass(frozen=True)
class IngestionPlan:
    """Comprehensive ingestion plan for multi-source content retrieval"""
    topic: str
    sources: list[IngestionSource]
    total_sources: int
    estimated_total_results: int
    estimated_duration: int
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = field(default_factory=dict)
    enable_cross_source_workflows: bool = False
    enable_deduplication: bool = True


@dataclass(frozen=True)
class ContentItem:
    """Standard content item structure"""
    title: str
    content: str
    url: str
    source_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = ""
    published: datetime | None = None
    author: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class IngestionResult:
    """Comprehensive results from ingestion plan execution"""
    success: bool
    plan_id: str
    content_items: list[ContentItem] = field(default_factory=list)
    total_content_items: int = 0
    sources_attempted: int = 0
    sources_completed: int = 0
    sources_failed: int = 0
    execution_time: float = 0.0
    execution_time_ms: float = 0.0
    error_details: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    # Additional fields for compatibility
    total_sources: int = 0
    successful_sources: int = 0
    failed_sources: int = 0
    total_items_retrieved: int = 0


class IngestionPlanBuilderInterface(ABC):
    """Abstract interface for ingestion plan builders"""
    
    @abstractmethod
    def build_plan(
        self,
        topic: str,
        source_configs: list[dict[str, Any]],
        user_preferences: dict[str, Any] | None = None,
    ) -> IngestionPlan:
        """Build a comprehensive ingestion plan from source configurations"""
        pass
    
    @abstractmethod
    def optimize_plan(self, plan: IngestionPlan) -> IngestionPlan:
        """Optimize the ingestion plan for better performance"""
        pass


class SourceExecutorInterface(ABC):
    """Abstract interface for source executors"""
    
    @abstractmethod
    async def execute_source(
        self,
        source: IngestionSource,
        plan: IngestionPlan,
    ) -> tuple[list[ContentItem], dict[str, Any]]:
        """Execute ingestion for a single source"""
        pass
    
    @abstractmethod
    def get_source_cache_key(self, source: IngestionSource) -> str:
        """Generate cache key for source execution"""
        pass


class IngestionOrchestratorInterface(ABC):
    """Abstract interface for ingestion orchestrators"""
    
    @abstractmethod
    async def create_ingestion_plan(
        self,
        topic: str,
        context: dict[str, Any] | None = None,
    ) -> IngestionPlan:
        """Create comprehensive ingestion plan based on research topic and context"""
        pass
    
    @abstractmethod
    async def execute_ingestion_plan(
        self,
        plan: IngestionPlan,
        user_id: str | None = None,
    ) -> IngestionResult:
        """Execute comprehensive ingestion plan with full orchestration"""
        pass
    
    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive orchestrator health check"""
        pass


class NotificationServiceInterface(ABC):
    """Abstract interface for notification services"""
    
    @abstractmethod
    async def send_notification(
        self,
        message: str,
        recipient: str,
        notification_type: str = "info",
    ) -> bool:
        """Send a notification to a recipient"""
        pass


class CacheServiceInterface(ABC):
    """Abstract interface for cache services"""
    
    @abstractmethod
    async def get(self, namespace: str, key: str) -> Any:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache"""
        pass


class MetricsCollectorInterface(ABC):
    """Abstract interface for metrics collection"""
    
    @abstractmethod
    def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a metric value"""
        pass
    
    @abstractmethod
    def increment_counter(
        self,
        counter_name: str,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics"""
        pass
