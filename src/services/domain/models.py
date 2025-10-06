#!/usr/bin/env python3
"""PAKE System - Domain Models (Phase 2 Architectural Refactoring)
Pure domain models without ORM dependencies.

These models represent the core business entities as Plain Old Python Objects (POPOs)
that are completely decoupled from any persistence mechanism.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List
from uuid import uuid4


class UserRole(Enum):
    """User roles in the system."""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MODERATOR = "moderator"


class UserStatus(Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class ContentType(Enum):
    """Content types."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    WEB_PAGE = "web_page"
    ACADEMIC_PAPER = "academic_paper"


class ContentSource(Enum):
    """Content sources."""

    FIRECRAWL = "firecrawl"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    RSS_FEED = "rss_feed"
    EMAIL = "email"
    MANUAL_UPLOAD = "manual_upload"


class ProcessingStatus(Enum):
    """Content processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class User:
    """Pure domain model for User entity."""

    id: str
    email: str
    hashed_password: str
    tenant_id: str

    # Profile information
    first_name: str | None = None
    last_name: str | None = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: datetime | None = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not self.email or "@" not in self.email:
            msg = "Invalid email address"
            raise ValueError(msg)
        if not self.hashed_password:
            msg = "Password hash is required"
            raise ValueError(msg)
        if not self.tenant_id:
            msg = "Tenant ID is required"
            raise ValueError(msg)

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split("@")[0]

    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE

    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if user can access specific tenant."""
        return self.tenant_id == tenant_id


@dataclass(frozen=True)
class ContentItem:
    """Pure domain model for Content entity."""

    id: str
    title: str
    content: str
    content_type: ContentType
    source: ContentSource
    tenant_id: str

    # Processing information
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None

    # Content metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # External references
    source_url: str | None = None
    source_id: str | None = None

    def __post_init__(self) -> None:
        """Validate content data after initialization."""
        if not self.title.strip():
            msg = "Title cannot be empty"
            raise ValueError(msg)
        if not self.content.strip():
            msg = "Content cannot be empty"
            raise ValueError(msg)
        if not self.tenant_id:
            msg = "Tenant ID is required"
            raise ValueError(msg)

    @property
    def is_processed(self) -> bool:
        """Check if content is fully processed."""
        return self.processing_status == ProcessingStatus.COMPLETED

    @property
    def content_length(self) -> int:
        """Get content length in characters."""
        return len(self.content)

    def add_tag(self, tag: str) -> "ContentItem":
        """Add tag to content (returns new instance)."""
        new_tags = self.tags + [tag] if tag not in self.tags else self.tags
        return ContentItem(
            id=self.id,
            title=self.title,
            content=self.content,
            content_type=self.content_type,
            source=self.source,
            tenant_id=self.tenant_id,
            processing_status=self.processing_status,
            processing_metadata=self.processing_metadata,
            created_at=self.created_at,
            updated_at=self.updated_at,
            processed_at=self.processed_at,
            tags=new_tags,
            metadata=self.metadata,
            source_url=self.source_url,
            source_id=self.source_id,
        )


@dataclass(frozen=True)
class SearchHistory:
    """Pure domain model for Search History entity."""

    id: str
    user_id: str
    tenant_id: str
    query: str

    # Search metadata
    results_count: int = 0
    search_filters: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Performance metrics
    response_time_ms: float | None = None

    def __post_init__(self) -> None:
        """Validate search history data."""
        if not self.query.strip():
            msg = "Search query cannot be empty"
            raise ValueError(msg)
        if not self.user_id:
            msg = "User ID is required"
            raise ValueError(msg)
        if not self.tenant_id:
            msg = "Tenant ID is required"
            raise ValueError(msg)


@dataclass(frozen=True)
class SavedSearch:
    """Pure domain model for Saved Search entity."""

    id: str
    user_id: str
    tenant_id: str
    name: str
    query: str

    # Search configuration
    search_filters: Dict[str, Any] = field(default_factory=dict)
    is_public: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_run_at: datetime | None = None

    # Usage statistics
    run_count: int = 0

    def __post_init__(self) -> None:
        """Validate saved search data."""
        if not self.name.strip():
            msg = "Search name cannot be empty"
            raise ValueError(msg)
        if not self.query.strip():
            msg = "Search query cannot be empty"
            raise ValueError(msg)
        if not self.user_id:
            msg = "User ID is required"
            raise ValueError(msg)
        if not self.tenant_id:
            msg = "Tenant ID is required"
            raise ValueError(msg)


@dataclass(frozen=True)
class Tenant:
    """Pure domain model for Tenant entity."""

    id: str
    name: str
    domain: str

    # Tenant configuration
    plan: str = "basic"
    is_active: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Limits and quotas
    max_users: int = 10
    max_content_items: int = 1000
    max_storage_mb: int = 1000

    # Metadata
    settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate tenant data."""
        if not self.name.strip():
            msg = "Tenant name cannot be empty"
            raise ValueError(msg)
        if not self.domain.strip():
            msg = "Tenant domain cannot be empty"
            raise ValueError(msg)

    @property
    def is_within_limits(self) -> bool:
        """Check if tenant is within resource limits."""
        # This would be checked against actual usage
        return True


@dataclass(frozen=True)
class SystemMetrics:
    """Pure domain model for System Metrics entity."""

    id: str
    metric_name: str
    metric_value: float
    tenant_id: str | None = None

    # Metric metadata
    metric_type: str = "counter"  # counter, gauge, timer
    tags: dict[str, str] = field(default_factory=dict)

    # Timestamps
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate metrics data."""
        if not self.metric_name.strip():
            msg = "Metric name cannot be empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class TenantActivity:
    """Pure domain model for Tenant Activity entity."""

    id: str
    tenant_id: str
    activity_type: str
    activity_description: str
    user_id: str | None = None

    # Activity metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate activity data."""
        if not self.tenant_id:
            msg = "Tenant ID is required"
            raise ValueError(msg)
        if not self.activity_type.strip():
            msg = "Activity type cannot be empty"
            raise ValueError(msg)
        if not self.activity_description.strip():
            msg = "Activity description cannot be empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class TenantResourceUsage:
    """Pure domain model for Tenant Resource Usage entity."""

    id: str
    tenant_id: str

    # Resource usage metrics
    users_count: int = 0
    content_items_count: int = 0
    storage_used_mb: float = 0.0
    api_calls_count: int = 0

    # Timestamps
    recorded_at: datetime = field(default_factory=datetime.utcnow)
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate resource usage data."""
        if not self.tenant_id:
            msg = "Tenant ID is required"
            raise ValueError(msg)
        if self.users_count < 0:
            msg = "Users count cannot be negative"
            raise ValueError(msg)
        if self.content_items_count < 0:
            msg = "Content items count cannot be negative"
            raise ValueError(msg)
        if self.storage_used_mb < 0:
            msg = "Storage used cannot be negative"
            raise ValueError(msg)
        if self.api_calls_count < 0:
            msg = "API calls count cannot be negative"
            raise ValueError(msg)


# ============================================================================
# Factory Functions
# ============================================================================


def create_user(email: str, hashed_password: str, tenant_id: str, **kwargs) -> User:
    """Factory function to create User domain model."""
    return User(
        id=str(uuid4()),
        email=email,
        hashed_password=hashed_password,
        tenant_id=tenant_id,
        **kwargs,
    )


def create_content_item(
    title: str,
    content: str,
    content_type: ContentType,
    source: ContentSource,
    tenant_id: str,
    **kwargs,
) -> ContentItem:
    """Factory function to create ContentItem domain model."""
    return ContentItem(
        id=str(uuid4()),
        title=title,
        content=content,
        content_type=content_type,
        source=source,
        tenant_id=tenant_id,
        **kwargs,
    )


def create_search_history(
    user_id: str, tenant_id: str, query: str, **kwargs
) -> SearchHistory:
    """Factory function to create SearchHistory domain model."""
    return SearchHistory(
        id=str(uuid4()), user_id=user_id, tenant_id=tenant_id, query=query, **kwargs
    )


def create_saved_search(
    user_id: str, tenant_id: str, name: str, query: str, **kwargs
) -> SavedSearch:
    """Factory function to create SavedSearch domain model."""
    return SavedSearch(
        id=str(uuid4()),
        user_id=user_id,
        tenant_id=tenant_id,
        name=name,
        query=query,
        **kwargs,
    )


def create_tenant(name: str, domain: str, **kwargs) -> Tenant:
    """Factory function to create Tenant domain model."""
    return Tenant(id=str(uuid4()), name=name, domain=domain, **kwargs)
