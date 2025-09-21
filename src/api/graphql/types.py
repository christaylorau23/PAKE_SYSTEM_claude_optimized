"""GraphQL Types

Defines the GraphQL schema types for the PAKE System including entities,
relationships, search results, and analytics data.
"""

from datetime import datetime
from enum import Enum

import strawberry


@strawberry.enum
class EntityType(Enum):
    """Supported entity types in the knowledge graph."""

    PERSON = "Person"
    ORGANIZATION = "Organization"
    LOCATION = "Location"
    CONCEPT = "Concept"
    DOCUMENT = "Document"
    TOPIC = "Topic"
    TECHNOLOGY = "Technology"
    EVENT = "Event"
    PRODUCT = "Product"
    RESEARCH_PAPER = "ResearchPaper"


@strawberry.enum
class RelationshipType(Enum):
    """Supported relationship types between entities."""

    MENTIONS = "MENTIONS"
    AUTHOR_OF = "AUTHOR_OF"
    WORKS_FOR = "WORKS_FOR"
    LOCATED_IN = "LOCATED_IN"
    RELATED_TO = "RELATED_TO"
    PART_OF = "PART_OF"
    CREATED_BY = "CREATED_BY"
    PUBLISHED_BY = "PUBLISHED_BY"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    FUNDED_BY = "FUNDED_BY"
    RESEARCHES = "RESEARCHES"
    USES = "USES"
    DEVELOPS = "DEVELOPS"
    INFLUENCES = "INFLUENCES"


@strawberry.type
class EntityProperties:
    """Dynamic properties for entities."""

    name: str | None = None
    description: str | None = None
    url: str | None = None
    email: str | None = None
    created_at: datetime | None = None
    additional_data: str | None = None  # JSON string for flexible data


@strawberry.type
class Entity:
    """Knowledge graph entity representation."""

    id: str
    type: EntityType
    label: str
    properties: EntityProperties
    created_at: datetime
    confidence_score: float | None = None


@strawberry.type
class RelationshipProperties:
    """Properties for relationships."""

    data: str | None = None  # JSON string for flexible data


@strawberry.type
class Relationship:
    """Knowledge graph relationship representation."""

    id: str
    from_entity_id: str
    to_entity_id: str
    type: RelationshipType
    properties: RelationshipProperties | None = None
    weight: float | None = None
    created_at: datetime


@strawberry.type
class EntityWithRelationships:
    """Entity with its connected relationships and entities."""

    entity: Entity
    relationships: list[Relationship]
    connected_entities: list[Entity]
    relationship_count: int


@strawberry.type
class SemanticMatch:
    """Semantic search result."""

    text: str
    score: float
    metadata: str | None = None  # JSON string
    entity_id: str | None = None
    highlighted_text: str | None = None


@strawberry.type
class SearchResult:
    """Comprehensive search result combining multiple sources."""

    query: str
    semantic_matches: list[SemanticMatch]
    related_entities: list[Entity]
    graph_connections: list[Relationship]
    total_results: int
    processing_time_ms: float


@strawberry.type
class AnalyticsMetric:
    """Analytics metric with time series data."""

    name: str
    value: float
    timestamp: datetime
    metadata: str | None = None  # JSON string


@strawberry.type
class TrendAnalysis:
    """Trend analysis result."""

    metric_name: str
    trend_direction: str  # "up", "down", "stable"
    trend_strength: float  # 0.0 to 1.0
    confidence: float
    prediction_horizon: int  # days
    historical_data: list[AnalyticsMetric]
    predicted_values: list[AnalyticsMetric]


@strawberry.type
class CorrelationAnalysis:
    """Correlation analysis between metrics."""

    metric_a: str
    metric_b: str
    correlation_coefficient: float
    p_value: float
    significance_level: str
    relationship_type: str  # "positive", "negative", "none"


@strawberry.type
class InsightRecommendation:
    """AI-generated insight and recommendation."""

    title: str
    description: str
    confidence: float
    category: str
    priority: str  # "high", "medium", "low"
    supporting_data: list[str]
    action_suggestions: list[str]
    created_at: datetime


@strawberry.type
class GraphVisualization:
    """Graph visualization data."""

    nodes: list[Entity]
    edges: list[Relationship]
    layout_data: str | None = None  # JSON string
    filters_applied: list[str] | None = None
    node_count: int
    edge_count: int


@strawberry.type
class SystemHealth:
    """System health and status information."""

    status: str
    version: str
    timestamp: datetime
    components: str | None = None  # JSON string
    performance_metrics: list[AnalyticsMetric]
    capabilities: list[str]


@strawberry.input
class EntityInput:
    """Input type for creating/updating entities."""

    type: EntityType
    label: str
    properties: str | None = None  # JSON string


@strawberry.input
class RelationshipInput:
    """Input type for creating relationships."""

    from_entity_id: str
    to_entity_id: str
    type: RelationshipType
    properties: str | None = None  # JSON string
    weight: float | None = None


@strawberry.input
class SearchInput:
    """Input type for complex search operations."""

    query: str
    entity_types: list[EntityType] | None = None
    relationship_types: list[RelationshipType] | None = None
    max_results: int | None = 50
    include_semantic: bool | None = True
    include_graph: bool | None = True
    min_confidence: float | None = 0.1


@strawberry.input
class AnalyticsInput:
    """Input type for analytics operations."""

    metrics: list[str]
    start_date: datetime | None = None
    end_date: datetime | None = None
    aggregation: str | None = "daily"  # "hourly", "daily", "weekly", "monthly"
    include_predictions: bool | None = False


@strawberry.input
class VisualizationInput:
    """Input type for graph visualization."""

    center_entity_id: str | None = None
    max_nodes: int | None = 50
    max_depth: int | None = 2
    entity_types: list[EntityType] | None = None
    relationship_types: list[RelationshipType] | None = None
    layout_algorithm: str | None = "force_directed"
