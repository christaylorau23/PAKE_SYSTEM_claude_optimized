#!/usr/bin/env python3
"""PAKE System - Domain Interfaces (Phase 2 Architectural Refactoring)
Abstract interfaces for dependency inversion and breaking circular dependencies.

This module defines the core abstractions that enable:
1. Dependency Inversion Principle implementation
2. Breaking circular dependencies
3. Repository Pattern implementation
4. Service layer decoupling
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

# Generic type for domain entities
T = TypeVar('T')


class ServiceStatus(Enum):
    """Service operation status"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    """Immutable service operation result"""
    status: ServiceStatus
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())


# ============================================================================
# Repository Pattern Interfaces
# ============================================================================

class AbstractRepository(ABC, Generic[T]):
    """Abstract base repository interface following Repository Pattern"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List entities with pagination"""
        pass


class AbstractUserRepository(AbstractRepository[T]):
    """Abstract user repository interface"""
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[T]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def get_by_tenant(self, tenant_id: str) -> list[T]:
        """Get users by tenant"""
        pass


class AbstractContentRepository(AbstractRepository[T]):
    """Abstract content repository interface"""
    
    @abstractmethod
    async def search(self, query: str, limit: int = 50) -> list[T]:
        """Search content by query"""
        pass
    
    @abstractmethod
    async def get_by_source(self, source: str) -> list[T]:
        """Get content by source"""
        pass


# ============================================================================
# Service Layer Interfaces
# ============================================================================

class AbstractNotificationService(ABC):
    """Abstract notification service interface"""
    
    @abstractmethod
    async def send_welcome_email(self, email: str, user_data: dict[str, Any]) -> ServiceResult[bool]:
        """Send welcome email to new user"""
        pass
    
    @abstractmethod
    async def send_notification(self, user_id: str, message: str, notification_type: str) -> ServiceResult[bool]:
        """Send notification to user"""
        pass


class AbstractAuthenticationService(ABC):
    """Abstract authentication service interface"""
    
    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> ServiceResult[dict[str, Any]]:
        """Authenticate user credentials"""
        pass
    
    @abstractmethod
    async def create_user(self, user_data: dict[str, Any]) -> ServiceResult[dict[str, Any]]:
        """Create new user account"""
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> ServiceResult[dict[str, Any]]:
        """Validate JWT token"""
        pass


class AbstractCacheService(ABC):
    """Abstract cache service interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        pass


class AbstractIngestionService(ABC):
    """Abstract ingestion service interface"""
    
    @abstractmethod
    async def ingest_content(self, source: str, content_data: dict[str, Any]) -> ServiceResult[str]:
        """Ingest content from external source"""
        pass
    
    @abstractmethod
    async def process_batch(self, batch_data: list[dict[str, Any]]) -> ServiceResult[list[str]]:
        """Process batch of content items"""
        pass


# ============================================================================
# Data Access Layer Interfaces
# ============================================================================

class AbstractDatabaseService(ABC):
    """Abstract database service interface"""
    
    @abstractmethod
    async def execute_query(self, query: str, params: dict[str, Any] = None) -> ServiceResult[list[dict[str, Any]]]:
        """Execute raw SQL query"""
        pass
    
    @abstractmethod
    async def health_check(self) -> ServiceResult[dict[str, Any]]:
        """Check database health"""
        pass
    
    @abstractmethod
    async def get_connection(self):
        """Get database connection"""
        pass


class AbstractVectorDatabaseService(ABC):
    """Abstract vector database service interface"""
    
    @abstractmethod
    async def store_embedding(self, content_id: str, embedding: list[float], metadata: dict[str, Any]) -> ServiceResult[str]:
        """Store vector embedding"""
        pass
    
    @abstractmethod
    async def search_similar(self, query_embedding: list[float], limit: int = 10) -> ServiceResult[list[dict[str, Any]]]:
        """Search for similar vectors"""
        pass


# ============================================================================
# External API Interfaces
# ============================================================================

class AbstractExternalAPIService(ABC):
    """Abstract external API service interface"""
    
    @abstractmethod
    async def make_request(self, endpoint: str, method: str, data: dict[str, Any] = None) -> ServiceResult[dict[str, Any]]:
        """Make HTTP request to external API"""
        pass
    
    @abstractmethod
    async def health_check(self) -> ServiceResult[dict[str, Any]]:
        """Check external API health"""
        pass


class AbstractFirecrawlService(AbstractExternalAPIService):
    """Abstract Firecrawl service interface"""
    
    @abstractmethod
    async def scrape_url(self, url: str, options: dict[str, Any] = None) -> ServiceResult[dict[str, Any]]:
        """Scrape URL content"""
        pass


class AbstractArXivService(AbstractExternalAPIService):
    """Abstract ArXiv service interface"""
    
    @abstractmethod
    async def search_papers(self, query: str, max_results: int = 10) -> ServiceResult[list[dict[str, Any]]]:
        """Search ArXiv papers"""
        pass


# ============================================================================
# Configuration Interfaces
# ============================================================================

class AbstractConfigService(ABC):
    """Abstract configuration service interface"""
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration"""
        pass
    
    @abstractmethod
    def get_redis_config(self) -> dict[str, Any]:
        """Get Redis configuration"""
        pass


# ============================================================================
# Monitoring and Logging Interfaces
# ============================================================================

class AbstractLoggingService(ABC):
    """Abstract logging service interface"""
    
    @abstractmethod
    def log_info(self, message: str, metadata: Optional[dict[str, Any]] = None):
        """Log info message"""
        pass
    
    @abstractmethod
    def log_error(self, message: str, error: Optional[Exception] = None, metadata: Optional[dict[str, Any]] = None):
        """Log error message"""
        pass
    
    @abstractmethod
    def log_performance(self, operation: str, duration_ms: float, metadata: Optional[dict[str, Any]] = None):
        """Log performance metrics"""
        pass


class AbstractMetricsService(ABC):
    """Abstract metrics service interface"""
    
    @abstractmethod
    async def record_counter(self, metric_name: str, value: int = 1, tags: Optional[dict[str, str]] = None):
        """Record counter metric"""
        pass
    
    @abstractmethod
    async def record_timer(self, metric_name: str, duration_ms: float, tags: Optional[dict[str, str]] = None):
        """Record timer metric"""
        pass
    
    @abstractmethod
    async def record_gauge(self, metric_name: str, value: float, tags: Optional[dict[str, str]] = None):
        """Record gauge metric"""
        pass


# ============================================================================
# Factory Interfaces
# ============================================================================

class AbstractServiceFactory(ABC):
    """Abstract service factory interface"""
    
    @abstractmethod
    def create_user_service(self) -> 'AbstractUserService':
        """Create user service instance"""
        pass
    
    @abstractmethod
    def create_auth_service(self) -> AbstractAuthenticationService:
        """Create authentication service instance"""
        pass
    
    @abstractmethod
    def create_notification_service(self) -> AbstractNotificationService:
        """Create notification service instance"""
        pass


class AbstractUserService(ABC):
    """Abstract user service interface"""
    
    def __init__(self, 
                 user_repo: AbstractUserRepository,
                 auth_service: AbstractAuthenticationService,
                 notification_service: AbstractNotificationService):
        self.user_repo = user_repo
        self.auth_service = auth_service
        self.notification_service = notification_service
    
    @abstractmethod
    async def create_user(self, email: str, password: str, user_data: dict[str, Any]) -> ServiceResult[dict[str, Any]]:
        """Create new user with authentication and notification"""
        pass
    
    @abstractmethod
    async def get_user_profile(self, user_id: str) -> ServiceResult[dict[str, Any]]:
        """Get user profile information"""
        pass
