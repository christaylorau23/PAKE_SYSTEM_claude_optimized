"""Intelligence GraphQL Service

FastAPI + GraphQL interface for unified querying across all knowledge stores
following the Personal Intelligence Engine blueprint. Provides a single,
powerful endpoint for querying:
- Obsidian vault knowledge
- Neo4j graph relationships
- PostgreSQL vector similarities
- Generated insights and analytics

Following PAKE System enterprise standards with comprehensive error handling,
async/await patterns, and production-ready performance.
"""

import asyncio
import logging
from datetime import UTC, datetime

import strawberry

# FastAPI and GraphQL
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from graphene import Mutation
from strawberry.asgi import GraphQL

from src.services.analytics.intelligence_insight_service import (
    IntelligenceInsightService,
    get_intelligence_insight_service,
)
from src.services.caching.redis_cache_service import CacheService
from src.services.database.vector_database_service import (
    VectorDatabaseService,
    get_vector_database_service,
)

# PAKE System imports
from src.services.knowledge.intelligence_core_service import (
    IntelligenceCoreService,
    KnowledgeQuery,
    KnowledgeSourceType,
    get_intelligence_core_service,
)
from src.services.nlp.intelligence_nlp_service import (
    IntelligenceNLPService,
    get_intelligence_nlp_service,
)

logger = logging.getLogger(__name__)


# GraphQL Type Definitions
@strawberry.type
class EntityType:
    """GraphQL type for extracted entities."""

    text: str
    entity_type: str
    confidence: float
    mentions: list[str]
    properties: strawberry.scalars.JSON


@strawberry.type
class RelationshipType:
    """GraphQL type for extracted relationships."""

    subject_entity: str
    relation_type: str
    object_entity: str
    confidence: float
    source_sentence: str
    context: str


@strawberry.type
class KnowledgeItemType:
    """GraphQL type for knowledge items."""

    id: str
    title: str
    content: str
    source_type: str
    source_path: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    entities: list[EntityType]
    relationships: list[RelationshipType]


@strawberry.type
class VectorSearchResultType:
    """GraphQL type for vector search results."""

    id: str
    content: str
    similarity_score: float
    metadata: strawberry.scalars.JSON
    vector_type: str
    created_at: datetime


@strawberry.type
class TopicEvolutionType:
    """GraphQL type for topic evolution."""

    topic_id: str
    topic_description: str
    keywords: list[str]
    coherence_score: float
    trend_direction: str
    growth_rate: float
    significance: str


@strawberry.type
class CorrelationInsightType:
    """GraphQL type for correlation insights."""

    metric1_name: str
    metric2_name: str
    correlation_coefficient: float
    p_value: float
    lag_periods: int
    confidence_interval: list[float]
    correlation_type: str
    temporal_pattern: str


@strawberry.type
class CommunityInsightType:
    """GraphQL type for community insights."""

    community_id: str
    community_description: str
    member_entities: list[str]
    community_size: int
    modularity_score: float
    central_entities: list[str]
    significance: str


@strawberry.type
class SynthesisInsightType:
    """GraphQL type for synthesis insights."""

    insight_id: str
    title: str
    description: str
    confidence_score: float
    significance: str
    supporting_evidence: list[str]
    actionable_recommendations: list[str]
    time_horizon: str
    categories: list[str]
    created_at: datetime


@strawberry.type
class AnalysisResultType:
    """GraphQL type for comprehensive analysis results."""

    analysis_timestamp: datetime
    topic_evolutions: list[TopicEvolutionType]
    correlations: list[CorrelationInsightType]
    communities: list[CommunityInsightType]
    synthesis_insights: list[SynthesisInsightType]
    processing_time_ms: float


@strawberry.type
class ServiceStatsType:
    """GraphQL type for service statistics."""

    intelligence_core: strawberry.scalars.JSON
    nlp_service: strawberry.scalars.JSON
    vector_database: strawberry.scalars.JSON
    insight_service: strawberry.scalars.JSON


@strawberry.type
class HealthCheckType:
    """GraphQL type for health check results."""

    status: str
    components: strawberry.scalars.JSON
    timestamp: datetime
    response_time_ms: float


# Input Types for Mutations
@strawberry.input
class KnowledgeQueryInput:
    """Input type for knowledge queries."""

    query_text: str
    query_type: str = "hybrid"  # semantic, graph, hybrid
    limit: int = 10
    similarity_threshold: float = 0.7
    include_entities: bool = True
    include_relationships: bool = True
    expand_graph: bool = False
    filters: strawberry.scalars.JSON | None = None


@strawberry.input
class AddKnowledgeItemInput:
    """Input type for adding knowledge items."""

    title: str
    content: str
    source_type: str
    source_path: str
    tags: list[str] | None = None
    frontmatter: strawberry.scalars.JSON | None = None


@strawberry.input
class AnalysisInput:
    """Input type for running comprehensive analysis."""

    documents: list[str] | None = None
    include_topics: bool = True
    include_correlations: bool = True
    include_communities: bool = True
    time_series_data: strawberry.scalars.JSON | None = None


# GraphQL Query Class
@strawberry.type
class Query:
    """GraphQL queries for the Intelligence Engine."""

    @strawberry.field
    async def knowledge_search(
        self,
        info: strawberry.Info,
        query: KnowledgeQueryInput,
    ) -> list[KnowledgeItemType]:
        """Search knowledge across all storage systems."""
        try:
            intelligence_core = info.context["intelligence_core"]

            # Convert input to query object
            knowledge_query = KnowledgeQuery(
                query_text=query.query_text,
                query_type=query.query_type,
                filters=query.filters or {},
                limit=query.limit,
                similarity_threshold=query.similarity_threshold,
                include_entities=query.include_entities,
                include_relationships=query.include_relationships,
                expand_graph=query.expand_graph,
            )

            # Execute query
            result = await intelligence_core.query_knowledge(knowledge_query)

            # Convert to GraphQL types
            items = []
            for item in result.items:
                entities = [
                    EntityType(
                        text=entity.text,
                        entity_type=entity.entity_type.value,
                        confidence=entity.confidence,
                        mentions=[mention.text for mention in entity.mentions],
                        properties=entity.properties,
                    )
                    for entity in item.entities
                ]

                relationships = [
                    RelationshipType(
                        subject_entity=rel.subject_entity,
                        relation_type=rel.relation_type.value,
                        object_entity=rel.object_entity,
                        confidence=rel.confidence,
                        source_sentence=rel.source_sentence,
                        context=rel.context,
                    )
                    for rel in item.relationships
                ]

                knowledge_item = KnowledgeItemType(
                    id=item.id,
                    title=item.title,
                    content=item.content,
                    source_type=item.source_type.value,
                    source_path=item.source_path,
                    tags=item.tags,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    entities=entities,
                    relationships=relationships,
                )
                items.append(knowledge_item)

            return items

        except Exception as e:
            logger.error(f"Error in knowledge search: {e}")
            raise Exception(f"Knowledge search failed: {str(e)}")

    @strawberry.field
    async def semantic_search(
        self,
        info: strawberry.Info,
        query_text: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        vector_type: str | None = None,
        source_filter: str | None = None,
    ) -> list[VectorSearchResultType]:
        """Perform semantic search using vector embeddings."""
        try:
            vector_db = info.context["vector_db"]
            nlp_service = info.context["nlp_service"]

            # Generate query embedding
            embeddings = await nlp_service.generate_embeddings([query_text])
            if embeddings.size == 0:
                raise Exception("Failed to generate query embedding")

            # Perform vector search
            results = await vector_db.semantic_search(
                query_embedding=embeddings[0],
                limit=limit,
                similarity_threshold=similarity_threshold,
            )

            # Convert to GraphQL types
            search_results = []
            for result in results:
                search_result = VectorSearchResultType(
                    id=result.id,
                    content=result.content,
                    similarity_score=result.similarity_score,
                    metadata=result.metadata,
                    vector_type=result.vector_type.value,
                    created_at=result.created_at,
                )
                search_results.append(search_result)

            return search_results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise Exception(f"Semantic search failed: {str(e)}")

    @strawberry.field
    async def get_insights(
        self,
        info: strawberry.Info,
        insight_type: str | None = None,
        significance_filter: str | None = None,
        limit: int = 20,
    ) -> list[SynthesisInsightType]:
        """Get generated insights."""
        try:
            insight_service = info.context["insight_service"]

            # Get insights from service
            all_insights = list(insight_service.generated_insights.values())

            # Apply filters
            filtered_insights = all_insights
            if significance_filter:
                filtered_insights = [
                    insight
                    for insight in filtered_insights
                    if insight.significance.value == significance_filter
                ]

            # Sort by creation time (newest first)
            filtered_insights.sort(key=lambda x: x.created_at, reverse=True)

            # Limit results
            filtered_insights = filtered_insights[:limit]

            # Convert to GraphQL types
            insights = []
            for insight in filtered_insights:
                synthesis_insight = SynthesisInsightType(
                    insight_id=insight.insight_id,
                    title=insight.title,
                    description=insight.description,
                    confidence_score=insight.confidence_score,
                    significance=insight.significance.value,
                    supporting_evidence=insight.supporting_evidence,
                    actionable_recommendations=insight.actionable_recommendations,
                    time_horizon=insight.time_horizon,
                    categories=insight.categories,
                    created_at=insight.created_at,
                )
                insights.append(synthesis_insight)

            return insights

        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            raise Exception(f"Failed to retrieve insights: {str(e)}")

    @strawberry.field
    async def get_topic_evolution(
        self,
        info: strawberry.Info,
        time_period: str | None = None,
        trend_filter: str | None = None,
    ) -> list[TopicEvolutionType]:
        """Get topic evolution data."""
        try:
            insight_service = info.context["insight_service"]

            # Get topic evolution history
            if time_period:
                evolutions = insight_service.topic_evolution_history.get(
                    time_period,
                    [],
                )
            else:
                evolutions = []
                for (
                    period_evolutions
                ) in insight_service.topic_evolution_history.values():
                    evolutions.extend(period_evolutions)

            # Apply trend filter
            if trend_filter:
                evolutions = [
                    evolution
                    for evolution in evolutions
                    if evolution.trend_direction == trend_filter
                ]

            # Convert to GraphQL types
            topic_evolutions = []
            for evolution in evolutions:
                keywords = [word for word, _ in evolution.topic_words[:10]]

                topic_evolution = TopicEvolutionType(
                    topic_id=evolution.topic_id,
                    topic_description=evolution.topic_description,
                    keywords=keywords,
                    coherence_score=(
                        evolution.coherence_scores[0]
                        if evolution.coherence_scores
                        else 0.0
                    ),
                    trend_direction=evolution.trend_direction,
                    growth_rate=evolution.growth_rate,
                    significance=evolution.significance.value,
                )
                topic_evolutions.append(topic_evolution)

            return topic_evolutions

        except Exception as e:
            logger.error(f"Error getting topic evolution: {e}")
            raise Exception(f"Failed to retrieve topic evolution: {str(e)}")

    @strawberry.field
    async def get_service_statistics(self, info: strawberry.Info) -> ServiceStatsType:
        """Get comprehensive service statistics."""
        try:
            intelligence_core = info.context["intelligence_core"]
            nlp_service = info.context["nlp_service"]
            vector_db = info.context["vector_db"]
            insight_service = info.context["insight_service"]

            # Gather stats from all services
            core_stats = await intelligence_core.get_service_stats()
            nlp_stats = await nlp_service.get_service_stats()
            vector_stats = await vector_db.get_database_stats()
            insight_stats = await insight_service.get_service_stats()

            return ServiceStatsType(
                intelligence_core=core_stats,
                nlp_service=nlp_stats,
                vector_database=vector_stats,
                insight_service=insight_stats,
            )

        except Exception as e:
            logger.error(f"Error getting service statistics: {e}")
            raise Exception(f"Failed to retrieve service statistics: {str(e)}")

    @strawberry.field
    async def health_check(self, info: strawberry.Info) -> HealthCheckType:
        """Perform comprehensive health check."""
        try:
            start_time = datetime.now()

            intelligence_core = info.context["intelligence_core"]
            nlp_service = info.context["nlp_service"]
            vector_db = info.context["vector_db"]
            insight_service = info.context["insight_service"]

            # Run health checks in parallel
            health_checks = await asyncio.gather(
                intelligence_core.health_check(),
                nlp_service.health_check(),
                vector_db.health_check(),
                insight_service.health_check(),
                return_exceptions=True,
            )

            # Process results
            components = {
                "intelligence_core": (
                    health_checks[0]
                    if not isinstance(health_checks[0], Exception)
                    else {"status": "error", "error": str(health_checks[0])}
                ),
                "nlp_service": (
                    health_checks[1]
                    if not isinstance(health_checks[1], Exception)
                    else {"status": "error", "error": str(health_checks[1])}
                ),
                "vector_database": (
                    health_checks[2]
                    if not isinstance(health_checks[2], Exception)
                    else {"status": "error", "error": str(health_checks[2])}
                ),
                "insight_service": (
                    health_checks[3]
                    if not isinstance(health_checks[3], Exception)
                    else {"status": "error", "error": str(health_checks[3])}
                ),
            }

            # Determine overall status
            all_healthy = all(
                component.get("status") == "healthy"
                for component in components.values()
            )

            overall_status = "healthy" if all_healthy else "degraded"

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            return HealthCheckType(
                status=overall_status,
                components=components,
                timestamp=datetime.now(UTC),
                response_time_ms=response_time,
            )

        except Exception as e:
            logger.error(f"Error in health check: {e}")
            raise Exception(f"Health check failed: {str(e)}")


# GraphQL Mutation Class
@strawberry.type
class Mutation:
    """GraphQL mutations for the Intelligence Engine."""

    @strawberry.mutation
    async def add_knowledge_item(
        self,
        info: strawberry.Info,
        input: AddKnowledgeItemInput,
    ) -> KnowledgeItemType:
        """Add a new knowledge item to the system."""
        try:
            intelligence_core = info.context["intelligence_core"]

            # Convert source type
            source_type = KnowledgeSourceType(input.source_type)

            # Add knowledge item
            knowledge_item = await intelligence_core.add_knowledge_item(
                content=input.content,
                title=input.title,
                source_type=source_type,
                source_path=input.source_path,
                tags=input.tags or [],
                frontmatter=input.frontmatter or {},
            )

            # Convert to GraphQL type
            entities = [
                EntityType(
                    text=entity.text,
                    entity_type=entity.entity_type.value,
                    confidence=entity.confidence,
                    mentions=[mention.text for mention in entity.mentions],
                    properties=entity.properties,
                )
                for entity in knowledge_item.entities
            ]

            relationships = [
                RelationshipType(
                    subject_entity=rel.subject_entity,
                    relation_type=rel.relation_type.value,
                    object_entity=rel.object_entity,
                    confidence=rel.confidence,
                    source_sentence=rel.source_sentence,
                    context=rel.context,
                )
                for rel in knowledge_item.relationships
            ]

            return KnowledgeItemType(
                id=knowledge_item.id,
                title=knowledge_item.title,
                content=knowledge_item.content,
                source_type=knowledge_item.source_type.value,
                source_path=knowledge_item.source_path,
                tags=knowledge_item.tags,
                created_at=knowledge_item.created_at,
                updated_at=knowledge_item.updated_at,
                entities=entities,
                relationships=relationships,
            )

        except Exception as e:
            logger.error(f"Error adding knowledge item: {e}")
            raise Exception(f"Failed to add knowledge item: {str(e)}")

    @strawberry.mutation
    async def run_comprehensive_analysis(
        self,
        info: strawberry.Info,
        input: AnalysisInput,
    ) -> AnalysisResultType:
        """Run comprehensive analysis across the intelligence engine."""
        try:
            insight_service = info.context["insight_service"]

            # Convert time series data if provided
            time_series_data = None
            if input.time_series_data:
                import pandas as pd

                time_series_data = {}
                for metric_name, data in input.time_series_data.items():
                    if isinstance(data, list):
                        time_series_data[metric_name] = pd.Series(data)

            # Run analysis
            results = await insight_service.run_comprehensive_analysis(
                documents=input.documents,
                time_series_data=time_series_data,
            )

            # Convert to GraphQL types
            topic_evolutions = []
            for topic in results.get("topic_evolutions", []):
                keywords = [word for word, _ in topic.topic_words[:10]]
                topic_evolutions.append(
                    TopicEvolutionType(
                        topic_id=topic.topic_id,
                        topic_description=topic.topic_description,
                        keywords=keywords,
                        coherence_score=(
                            topic.coherence_scores[0] if topic.coherence_scores else 0.0
                        ),
                        trend_direction=topic.trend_direction,
                        growth_rate=topic.growth_rate,
                        significance=topic.significance.value,
                    ),
                )

            correlations = []
            for corr in results.get("correlations", []):
                correlations.append(
                    CorrelationInsightType(
                        metric1_name=corr.metric1_name,
                        metric2_name=corr.metric2_name,
                        correlation_coefficient=corr.correlation_coefficient,
                        p_value=corr.p_value,
                        lag_periods=corr.lag_periods,
                        confidence_interval=list(corr.confidence_interval),
                        correlation_type=corr.correlation_type,
                        temporal_pattern=corr.temporal_pattern,
                    ),
                )

            communities = []
            for comm in results.get("communities", []):
                communities.append(
                    CommunityInsightType(
                        community_id=comm.community_id,
                        community_description=comm.community_description,
                        member_entities=comm.member_entities,
                        community_size=comm.community_size,
                        modularity_score=comm.modularity_score,
                        central_entities=[
                            entity for entity, _ in comm.central_entities
                        ],
                        significance=comm.significance.value,
                    ),
                )

            synthesis_insights = []
            for insight in results.get("synthesis_insights", []):
                synthesis_insights.append(
                    SynthesisInsightType(
                        insight_id=insight.insight_id,
                        title=insight.title,
                        description=insight.description,
                        confidence_score=insight.confidence_score,
                        significance=insight.significance.value,
                        supporting_evidence=insight.supporting_evidence,
                        actionable_recommendations=insight.actionable_recommendations,
                        time_horizon=insight.time_horizon,
                        categories=insight.categories,
                        created_at=insight.created_at,
                    ),
                )

            return AnalysisResultType(
                analysis_timestamp=datetime.fromisoformat(
                    results["analysis_timestamp"],
                ),
                topic_evolutions=topic_evolutions,
                correlations=correlations,
                communities=communities,
                synthesis_insights=synthesis_insights,
                processing_time_ms=results["processing_time_ms"],
            )

        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            raise Exception(f"Comprehensive analysis failed: {str(e)}")


# GraphQL Schema
schema = strawberry.Schema(query=Query, mutation=Mutation)


class IntelligenceGraphQLService:
    """FastAPI service with GraphQL interface for the Intelligence Engine.

    Provides unified access to all intelligence engine capabilities through
    a single, powerful GraphQL endpoint with comprehensive error handling
    and production-ready performance.
    """

    def __init__(
        self,
        obsidian_vault_path: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_REDACTED_SECRET: str,
        postgres_url: str,
        cache_service: CacheService | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
    ):
        """Initialize the GraphQL service.

        Args:
            obsidian_vault_path: Path to Obsidian vault
            neo4j_uri: Neo4j database URI
            neo4j_user: Neo4j username
            neo4j_REDACTED_SECRET: Neo4j REDACTED_SECRET
            postgres_url: PostgreSQL connection URL
            cache_service: Optional cache service
            host: Host to bind to
            port: Port to bind to
        """
        self.obsidian_vault_path = obsidian_vault_path
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_REDACTED_SECRET = neo4j_REDACTED_SECRET
        self.postgres_url = postgres_url
        self.cache_service = cache_service
        self.host = host
        self.port = port

        # FastAPI app
        self.app = FastAPI(
            title="PAKE Intelligence Engine API",
            description="GraphQL API for the Personal Intelligence Engine with unified knowledge access",
            version="1.0.0",
        )

        # Service instances
        self.intelligence_core: IntelligenceCoreService | None = None
        self.nlp_service: IntelligenceNLPService | None = None
        self.vector_db: VectorDatabaseService | None = None
        self.insight_service: IntelligenceInsightService | None = None

        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()

    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint with service information."""
            return {
                "service": "PAKE Intelligence Engine API",
                "version": "1.0.0",
                "endpoints": {
                    "graphql": "/graphql",
                    "health": "/health",
                    "docs": "/docs",
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                if not all(
                    [
                        self.intelligence_core,
                        self.nlp_service,
                        self.vector_db,
                        self.insight_service,
                    ],
                ):
                    return JSONResponse(
                        status_code=503,
                        content={
                            "status": "unhealthy",
                            "error": "Services not initialized",
                        },
                    )

                # Run health checks
                health_results = await asyncio.gather(
                    self.intelligence_core.health_check(),
                    self.nlp_service.health_check(),
                    self.vector_db.health_check(),
                    self.insight_service.health_check(),
                    return_exceptions=True,
                )

                all_healthy = all(
                    not isinstance(result, Exception)
                    and result.get("status") == "healthy"
                    for result in health_results
                )

                return {
                    "status": "healthy" if all_healthy else "degraded",
                    "services": {
                        "intelligence_core": (
                            health_results[0]
                            if not isinstance(health_results[0], Exception)
                            else {"status": "error"}
                        ),
                        "nlp_service": (
                            health_results[1]
                            if not isinstance(health_results[1], Exception)
                            else {"status": "error"}
                        ),
                        "vector_database": (
                            health_results[2]
                            if not isinstance(health_results[2], Exception)
                            else {"status": "error"}
                        ),
                        "insight_service": (
                            health_results[3]
                            if not isinstance(health_results[3], Exception)
                            else {"status": "error"}
                        ),
                    },
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"status": "unhealthy", "error": str(e)},
                )

    async def initialize(self) -> bool:
        """Initialize all intelligence engine services.

        Returns:
            bool: Success status
        """
        try:
            logger.info("Initializing Intelligence GraphQL Service...")

            # Initialize core services
            self.intelligence_core = await get_intelligence_core_service(
                obsidian_vault_path=self.obsidian_vault_path,
                neo4j_uri=self.neo4j_uri,
                neo4j_user=self.neo4j_user,
                neo4j_REDACTED_SECRET=self.neo4j_REDACTED_SECRET,
                postgres_url=self.postgres_url,
                cache_service=self.cache_service,
            )

            self.nlp_service = await get_intelligence_nlp_service(self.cache_service)
            self.vector_db = await get_vector_database_service(
                self.postgres_url,
                self.cache_service,
            )

            self.insight_service = await get_intelligence_insight_service(
                intelligence_core=self.intelligence_core,
                nlp_service=self.nlp_service,
                vector_db=self.vector_db,
                cache_service=self.cache_service,
            )

            # Setup GraphQL with context
            async def get_context():
                return {
                    "intelligence_core": self.intelligence_core,
                    "nlp_service": self.nlp_service,
                    "vector_db": self.vector_db,
                    "insight_service": self.insight_service,
                }

            # Add GraphQL endpoint
            graphql_app = GraphQL(schema, context_getter=get_context)
            self.app.mount("/graphql", graphql_app)

            logger.info("Intelligence GraphQL Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Intelligence GraphQL Service: {e}")
            return False

    async def start(self):
        """Start the FastAPI service."""
        import uvicorn

        if not await self.initialize():
            raise RuntimeError("Failed to initialize Intelligence GraphQL Service")

        logger.info(f"Starting Intelligence GraphQL Service on {self.host}:{self.port}")

        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )

        server = uvicorn.Server(config)
        await server.serve()

    async def close(self):
        """Close all service connections."""
        try:
            if self.intelligence_core:
                await self.intelligence_core.close()

            if self.vector_db:
                await self.vector_db.close()

            logger.info("Intelligence GraphQL Service closed")

        except Exception as e:
            logger.error(f"Error closing GraphQL service: {e}")


# Factory function for creating the service
async def create_intelligence_graphql_service(
    obsidian_vault_path: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_REDACTED_SECRET: str,
    postgres_url: str,
    cache_service: CacheService | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> IntelligenceGraphQLService:
    """Create and initialize Intelligence GraphQL Service.

    Args:
        obsidian_vault_path: Path to Obsidian vault
        neo4j_uri: Neo4j database URI
        neo4j_user: Neo4j username
        neo4j_REDACTED_SECRET: Neo4j REDACTED_SECRET
        postgres_url: PostgreSQL connection URL
        cache_service: Optional cache service
        host: Host to bind to
        port: Port to bind to

    Returns:
        IntelligenceGraphQLService: Initialized service
    """
    service = IntelligenceGraphQLService(
        obsidian_vault_path=obsidian_vault_path,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_REDACTED_SECRET=neo4j_REDACTED_SECRET,
        postgres_url=postgres_url,
        cache_service=cache_service,
        host=host,
        port=port,
    )

    if not await service.initialize():
        raise RuntimeError("Failed to initialize Intelligence GraphQL Service")

    return service


# Example usage and CLI
if __name__ == "__main__":
    import asyncio
    import os

    async def main():
        # SECURITY: Fail-fast approach - no hardcoded fallbacks
        neo4j_REDACTED_SECRET = os.getenv("NEO4J_PASSWORD")
        if not neo4j_REDACTED_SECRET:
            raise ValueError(
                "The NEO4J_PASSWORD environment variable is not set. "
                "Please configure it before running the application. "
                "This is a security requirement."
            )

        service = await create_intelligence_graphql_service(
            obsidian_vault_path=os.getenv("OBSIDIAN_VAULT_PATH", "/path/to/vault"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_REDACTED_SECRET=neo4j_REDACTED_SECRET,
            postgres_url=os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://user:REDACTED_SECRET@localhost/pake_intelligence",
            ),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8000")),
        )

        await service.start()

    asyncio.run(main())
