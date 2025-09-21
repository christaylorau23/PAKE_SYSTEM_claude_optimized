# Data Model: Intelligent Content Curation

**Feature**: 001-intelligent-content-curation  
**Date**: 2025-01-23  
**Status**: Complete

## Overview

This document defines the data model for the Intelligent Content Curation system, including entities, relationships, validation rules, and state transitions.

## Core Entities

### ContentItem
Represents individual pieces of content with comprehensive metadata and analysis results.

```python
@dataclass(frozen=True)
class ContentItem:
    # Core identification
    id: str                           # UUID4 primary key
    title: str                        # Content title (required)
    content_text: Optional[str]        # Full text content
    author: Optional[str]             # Content author
    source_url: Optional[str]         # Original source URL
    
    # Temporal information
    published_date: Optional[datetime] # Publication date
    ingested_at: datetime             # When added to system (auto-generated)
    updated_at: datetime              # Last update timestamp (auto-generated)
    
    # Content classification
    content_type: str                 # article, blog, paper, news, tutorial, review
    tags: List[str]                   # Content tags/keywords
    topic_categories: List[str]       # Assigned topic categories
    
    # Quality metrics (0.0-1.0 scale)
    quality_score: Optional[float]    # ML-calculated quality score
    credibility_score: Optional[float] # Source credibility assessment
    sentiment_score: Optional[float]  # Sentiment analysis result (-1.0 to 1.0)
    readability_score: Optional[float] # Readability assessment (0.0-1.0)
    
    # Source information
    source_authority_score: Optional[float] # Source authority rating
    source_reliability: Optional[float]      # Source reliability rating
    
    # Engagement metrics
    view_count: Optional[int]         # Total views
    share_count: Optional[int]        # Total shares
    like_count: Optional[int]         # Total likes
    comment_count: Optional[int]      # Total comments
    
    # Additional metadata
    abstract: Optional[str]           # Content abstract/summary
    language: str = "en"             # Content language (ISO 639-1)
    word_count: Optional[int]         # Word count
    reading_time_minutes: Optional[int] # Estimated reading time
```

**Validation Rules**:
- `id`: Must be valid UUID4 format
- `title`: Required, 1-500 characters
- `content_type`: Must be one of predefined types
- `quality_score`, `credibility_score`, `sentiment_score`, `readability_score`: Must be in range [0.0, 1.0] (except sentiment: [-1.0, 1.0])
- `tags`: Maximum 20 tags, each 1-50 characters
- `published_date`: Cannot be in the future
- `source_url`: Must be valid URL format if provided

**State Transitions**:
- `draft` → `analyzed` (after content analysis)
- `analyzed` → `published` (after quality validation)
- `published` → `archived` (after expiration or deprecation)

### UserProfile
Represents user preferences, behavior patterns, and personalization settings.

```python
@dataclass(frozen=True)
class UserProfile:
    # Core identification
    user_id: str                      # User identifier (matches PAKE system)
    
    # Preference settings
    interests: List[str]              # User interest categories
    preference_weights: Dict[str, float] # Content type preferences
    learning_rate: float = 0.1         # ML learning rate (0.0-1.0)
    exploration_factor: float = 0.1   # Exploration vs exploitation balance
    
    # Behavioral patterns
    interaction_history: List[str]    # Recent interaction IDs
    preferred_content_types: List[str] # Preferred content types
    preferred_sources: List[str]      # Preferred content sources
    preferred_topics: List[str]       # Preferred topic categories
    
    # Temporal preferences
    active_hours: List[int]           # Hours of day when user is active (0-23)
    active_days: List[int]            # Days of week when user is active (0-6)
    timezone: str = "UTC"             # User timezone
    
    # Privacy settings
    data_sharing_level: str = "standard" # standard, minimal, none
    personalization_enabled: bool = True # Enable/disable personalization
    
    # System metadata
    created_at: datetime              # Profile creation timestamp
    updated_at: datetime              # Last update timestamp
    last_active_at: datetime          # Last user activity timestamp
    total_interactions: int = 0       # Total interaction count
```

**Validation Rules**:
- `user_id`: Required, matches PAKE system user ID format
- `interests`: Maximum 50 interests, each 1-100 characters
- `preference_weights`: Values must sum to 1.0, keys must be valid content types
- `learning_rate`, `exploration_factor`: Must be in range [0.0, 1.0]
- `active_hours`: Must be integers 0-23, maximum 24 hours
- `active_days`: Must be integers 0-6, maximum 7 days
- `data_sharing_level`: Must be one of predefined levels

**State Transitions**:
- `new` → `learning` (after first interactions)
- `learning` → `stable` (after sufficient interaction history)
- `stable` → `learning` (after significant behavior change)

### UserInteraction
Tracks user engagement with content for learning and personalization.

```python
@dataclass(frozen=True)
class UserInteraction:
    # Core identification
    id: str                           # UUID4 primary key
    user_id: str                      # User identifier
    content_id: str                   # Content identifier
    
    # Interaction details
    interaction_type: InteractionType # view, like, share, save, click, dismiss
    timestamp: datetime               # Interaction timestamp
    session_duration: Optional[int]   # Session duration in seconds
    context: Dict[str, Any]          # Additional context data
    
    # Interaction metadata
    source: str                       # Where interaction occurred (web, mobile, api)
    user_agent: Optional[str]        # User agent string
    ip_address: Optional[str]        # IP address (hashed for privacy)
    referrer: Optional[str]           # Referrer URL
    
    # Content context
    content_position: Optional[int]   # Position in recommendation list
    recommendation_id: Optional[str]  # Associated recommendation ID
    recommendation_score: Optional[float] # Original recommendation score
    
    # Feedback data
    explicit_rating: Optional[int]   # Explicit user rating (1-5)
    feedback_text: Optional[str]      # User feedback text
    satisfaction_score: Optional[float] # Calculated satisfaction score
```

**Validation Rules**:
- `id`: Must be valid UUID4 format
- `user_id`, `content_id`: Required, must reference existing entities
- `interaction_type`: Must be valid InteractionType enum value
- `timestamp`: Cannot be in the future
- `session_duration`: Must be positive integer if provided
- `explicit_rating`: Must be integer 1-5 if provided
- `satisfaction_score`: Must be in range [0.0, 1.0] if provided

**State Transitions**:
- `pending` → `processed` (after feedback processing)
- `processed` → `learned` (after ML model update)

### Recommendation
Represents generated content recommendations with reasoning and feedback tracking.

```python
@dataclass(frozen=True)
class Recommendation:
    # Core identification
    id: str                           # UUID4 primary key
    content_id: str                   # Recommended content ID
    user_id: str                      # Target user ID
    
    # Recommendation metrics
    relevance_score: float            # Relevance score (0.0-1.0)
    confidence_score: float           # Confidence in recommendation (0.0-1.0)
    ranking_position: int             # Position in recommendation list
    
    # Recommendation context
    reasoning: Optional[str]          # Human-readable explanation
    algorithm_used: str               # ML algorithm that generated recommendation
    feature_weights: Dict[str, float] # Feature importance weights
    
    # User feedback
    user_feedback: Optional[str]      # User feedback on recommendation
    feedback_timestamp: Optional[datetime] # When feedback was provided
    satisfaction_score: Optional[float] # Calculated satisfaction score
    
    # System metadata
    created_at: datetime              # Recommendation creation timestamp
    expires_at: Optional[datetime]    # Recommendation expiration
    batch_id: Optional[str]           # Batch processing identifier
    request_id: Optional[str]         # Associated API request ID
```

**Validation Rules**:
- `id`: Must be valid UUID4 format
- `content_id`, `user_id`: Required, must reference existing entities
- `relevance_score`, `confidence_score`: Must be in range [0.0, 1.0]
- `ranking_position`: Must be positive integer
- `algorithm_used`: Must be valid algorithm identifier
- `expires_at`: Must be after `created_at` if provided

**State Transitions**:
- `generated` → `presented` (when shown to user)
- `presented` → `interacted` (when user interacts with recommendation)
- `interacted` → `feedback_received` (when user provides feedback)

### ContentSource
Represents external content sources with reliability and authority metrics.

```python
@dataclass(frozen=True)
class ContentSource:
    # Core identification
    id: str                           # UUID4 primary key
    name: str                         # Source name
    domain: str                       # Source domain
    
    # Source metrics
    authority_score: float            # Authority rating (0.0-1.0)
    reliability_score: float         # Reliability rating (0.0-1.0)
    quality_score: float             # Average content quality (0.0-1.0)
    
    # Source characteristics
    content_types: List[str]          # Supported content types
    update_frequency: str             # daily, weekly, monthly, irregular
    content_volume: int               # Average content volume per period
    
    # Integration details
    api_endpoint: Optional[str]       # API endpoint for content retrieval
    authentication_required: bool = False # Whether authentication is required
    rate_limit: Optional[int]         # Rate limit (requests per hour)
    
    # System metadata
    created_at: datetime              # Source registration timestamp
    updated_at: datetime              # Last update timestamp
    last_sync_at: Optional[datetime] # Last content synchronization
    is_active: bool = True            # Whether source is active
```

**Validation Rules**:
- `id`: Must be valid UUID4 format
- `name`: Required, 1-200 characters
- `domain`: Required, valid domain format
- `authority_score`, `reliability_score`, `quality_score`: Must be in range [0.0, 1.0]
- `update_frequency`: Must be one of predefined frequencies
- `content_volume`: Must be non-negative integer
- `rate_limit`: Must be positive integer if provided

**State Transitions**:
- `registered` → `active` (after validation)
- `active` → `suspended` (after reliability issues)
- `suspended` → `active` (after resolution)
- `active` → `deprecated` (after source closure)

### TopicCategory
Represents hierarchical topic categories for content organization and discovery.

```python
@dataclass(frozen=True)
class TopicCategory:
    # Core identification
    id: str                           # UUID4 primary key
    name: str                         # Category name
    slug: str                         # URL-friendly identifier
    
    # Hierarchical structure
    parent_id: Optional[str]          # Parent category ID
    level: int                        # Hierarchy level (0 = root)
    path: str                         # Full path (e.g., "technology/ai/machine-learning")
    
    # Category metadata
    description: Optional[str]        # Category description
    keywords: List[str]               # Associated keywords
    synonyms: List[str]               # Alternative names
    
    # Content statistics
    content_count: int = 0            # Number of content items in category
    subcategory_count: int = 0        # Number of subcategories
    
    # System metadata
    created_at: datetime              # Category creation timestamp
    updated_at: datetime              # Last update timestamp
    is_active: bool = True            # Whether category is active
```

**Validation Rules**:
- `id`: Must be valid UUID4 format
- `name`: Required, 1-200 characters
- `slug`: Required, URL-friendly format (lowercase, alphanumeric, hyphens)
- `parent_id`: Must reference existing category if provided
- `level`: Must be non-negative integer
- `path`: Must match hierarchy structure
- `keywords`: Maximum 100 keywords, each 1-50 characters
- `content_count`, `subcategory_count`: Must be non-negative integers

**State Transitions**:
- `draft` → `active` (after validation)
- `active` → `archived` (after deprecation)
- `archived` → `active` (after restoration)

## Relationships

### Primary Relationships
- **UserProfile** ↔ **UserInteraction**: One-to-many (user has many interactions)
- **ContentItem** ↔ **UserInteraction**: One-to-many (content has many interactions)
- **UserProfile** ↔ **Recommendation**: One-to-many (user has many recommendations)
- **ContentItem** ↔ **Recommendation**: One-to-many (content has many recommendations)
- **ContentSource** ↔ **ContentItem**: One-to-many (source has many content items)
- **TopicCategory** ↔ **ContentItem**: Many-to-many (content can belong to multiple categories)

### Derived Relationships
- **UserProfile** ↔ **ContentItem**: Many-to-many through UserInteraction
- **ContentItem** ↔ **ContentItem**: Many-to-many through topic similarity
- **UserProfile** ↔ **UserProfile**: Many-to-many through collaborative filtering

## Data Integrity Constraints

### Referential Integrity
- All foreign key references must point to existing entities
- Cascade deletes for dependent entities (e.g., delete user interactions when user is deleted)
- Soft deletes for content items (mark as deleted, don't remove)

### Business Rules
- User profiles must have at least one interest or preference weight
- Content items must have either title or content_text
- Recommendations must have relevance_score > 0.0
- User interactions must have valid interaction_type
- Topic categories cannot be their own parent

### Data Quality Rules
- No duplicate content items (based on title + source_url hash)
- No orphaned recommendations (must reference existing user and content)
- No circular topic category hierarchies
- No future timestamps in historical data

## Indexing Strategy

### Primary Indexes
- `ContentItem.id` (primary key)
- `UserProfile.user_id` (primary key)
- `UserInteraction.id` (primary key)
- `Recommendation.id` (primary key)

### Performance Indexes
- `ContentItem.published_date` (for time-based queries)
- `ContentItem.content_type` (for content type filtering)
- `UserInteraction.user_id + timestamp` (for user activity queries)
- `UserInteraction.content_id + interaction_type` (for content engagement)
- `Recommendation.user_id + created_at` (for user recommendation history)
- `TopicCategory.path` (for hierarchical queries)

### Composite Indexes
- `(user_id, content_id, timestamp)` on UserInteraction (for user-content interaction history)
- `(content_type, published_date, quality_score)` on ContentItem (for content discovery)
- `(user_id, relevance_score, created_at)` on Recommendation (for user recommendation ranking)

## Data Retention and Archival

### Retention Policies
- **UserInteractions**: Retain for 2 years, then archive
- **Recommendations**: Retain for 1 year, then archive
- **ContentItems**: Retain indefinitely (mark as archived after 5 years)
- **UserProfiles**: Retain indefinitely (respect user deletion requests)

### Archival Strategy
- Move old data to separate archival tables
- Compress archived data to reduce storage costs
- Maintain referential integrity in archived data
- Provide data export functionality for user requests

## Privacy and Security Considerations

### Data Minimization
- Collect only necessary data for recommendation generation
- Anonymize user data in analytics and ML training
- Implement data retention policies for automatic cleanup

### Access Control
- Role-based access to user data (user, admin, system)
- Audit logging for all data access and modifications
- Encryption at rest and in transit for sensitive data

### Compliance
- GDPR compliance for EU users (right to be forgotten, data portability)
- CCPA compliance for California users
- SOC 2 compliance for enterprise customers

---

*Data model completed: 2025-01-23*  
*Ready for implementation*