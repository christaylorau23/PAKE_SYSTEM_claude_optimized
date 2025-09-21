"""GraphQL Resolvers

Implements the business logic for GraphQL queries and mutations,
connecting the GraphQL schema to the underlying services.
"""

import logging
from datetime import datetime, timedelta

import strawberry

from .types import (
    AnalyticsMetric,
    CorrelationAnalysis,
    Entity,
    EntityInput,
    EntityProperties,
    EntityType,
    EntityWithRelationships,
    GraphVisualization,
    InsightRecommendation,
    Relationship,
    RelationshipInput,
    RelationshipType,
    SearchInput,
    SearchResult,
    SemanticMatch,
    SystemHealth,
    TrendAnalysis,
    VisualizationInput,
)

logger = logging.getLogger(__name__)


@strawberry.type
class Query:
    """GraphQL Query root type."""

    @strawberry.field
    async def entity(self, id: str) -> Entity | None:
        """Get a single entity by ID."""
        try:
            from src.services.graph.entity_service import get_entity_service

            entity_service = get_entity_service()
            entity_data = await entity_service.get_entity(id)

            if not entity_data:
                return None

            return Entity(
                id=entity_data["id"],
                type=EntityType(entity_data["type"]),
                label=entity_data["label"],
                properties=EntityProperties(
                    name=entity_data.get("properties", {}).get("name"),
                    description=entity_data.get("properties", {}).get("description"),
                    url=entity_data.get("properties", {}).get("url"),
                    email=entity_data.get("properties", {}).get("email"),
                    created_at=entity_data.get("created_at"),
                    additional_data=str(entity_data.get("properties", {})),
                ),
                created_at=entity_data.get("created_at", datetime.utcnow()),
                confidence_score=entity_data.get("confidence_score", 1.0),
            )

        except Exception as e:
            logger.error(f"Error fetching entity {id}: {e}")
            return None

    @strawberry.field
    async def entities(
        self,
        entity_types: list[EntityType] | None = None,
        limit: int | None = 50,
        offset: int | None = 0,
    ) -> list[Entity]:
        """Get multiple entities with optional filtering."""
        try:
            from src.services.graph.entity_service import get_entity_service

            entity_service = get_entity_service()

            # Convert enum types to strings if provided
            type_filters = [t.value for t in entity_types] if entity_types else None

            entities_data = await entity_service.get_entities(
                entity_types=type_filters,
                limit=limit,
                offset=offset,
            )

            entities = []
            for entity_data in entities_data:
                entities.append(
                    Entity(
                        id=entity_data["id"],
                        type=EntityType(entity_data["type"]),
                        label=entity_data["label"],
                        properties=EntityProperties(
                            name=entity_data.get("properties", {}).get("name"),
                            description=entity_data.get("properties", {}).get(
                                "description",
                            ),
                            url=entity_data.get("properties", {}).get("url"),
                            email=entity_data.get("properties", {}).get("email"),
                            created_at=entity_data.get("created_at"),
                            additional_data=str(entity_data.get("properties", {})),
                        ),
                        created_at=entity_data.get("created_at", datetime.utcnow()),
                        confidence_score=entity_data.get("confidence_score", 1.0),
                    ),
                )

            return entities

        except Exception as e:
            logger.error(f"Error fetching entities: {e}")
            return []

    @strawberry.field
    async def entity_with_relationships(
        self,
        id: str,
        max_depth: int | None = 1,
    ) -> EntityWithRelationships | None:
        """Get an entity with its relationships and connected entities."""
        try:
            from src.services.graph.knowledge_graph_service import (
                get_knowledge_graph_service,
            )

            kg_service = get_knowledge_graph_service()
            subgraph = await kg_service.get_entity_subgraph(id, max_depth or 1)

            if not subgraph or "center_entity" not in subgraph:
                return None

            # Convert center entity
            center_data = subgraph["center_entity"]
            center_entity = Entity(
                id=center_data["id"],
                type=EntityType(center_data["type"]),
                label=center_data["label"],
                properties=EntityProperties(
                    name=center_data.get("properties", {}).get("name"),
                    description=center_data.get("properties", {}).get("description"),
                    url=center_data.get("properties", {}).get("url"),
                    email=center_data.get("properties", {}).get("email"),
                    created_at=center_data.get("created_at"),
                    additional_data=str(center_data.get("properties", {})),
                ),
                created_at=center_data.get("created_at", datetime.utcnow()),
                confidence_score=center_data.get("confidence_score", 1.0),
            )

            # Convert relationships
            relationships = []
            for rel_data in subgraph.get("relationships", []):
                relationships.append(
                    Relationship(
                        id=rel_data["id"],
                        from_entity_id=rel_data["from_entity_id"],
                        to_entity_id=rel_data["to_entity_id"],
                        type=RelationshipType(rel_data["type"]),
                        properties=rel_data.get("properties", {}),
                        weight=rel_data.get("weight", 1.0),
                        created_at=rel_data.get("created_at", datetime.utcnow()),
                    ),
                )

            # Convert connected entities
            connected_entities = []
            for entity_data in subgraph.get("connected_entities", []):
                connected_entities.append(
                    Entity(
                        id=entity_data["id"],
                        type=EntityType(entity_data["type"]),
                        label=entity_data["label"],
                        properties=EntityProperties(
                            name=entity_data.get("properties", {}).get("name"),
                            description=entity_data.get("properties", {}).get(
                                "description",
                            ),
                            url=entity_data.get("properties", {}).get("url"),
                            email=entity_data.get("properties", {}).get("email"),
                            created_at=entity_data.get("created_at"),
                            additional_data=str(entity_data.get("properties", {})),
                        ),
                        created_at=entity_data.get("created_at", datetime.utcnow()),
                        confidence_score=entity_data.get("confidence_score", 1.0),
                    ),
                )

            return EntityWithRelationships(
                entity=center_entity,
                relationships=relationships,
                connected_entities=connected_entities,
                relationship_count=len(relationships),
            )

        except Exception as e:
            logger.error(f"Error fetching entity with relationships {id}: {e}")
            return None

    @strawberry.field
    async def comprehensive_search(self, search_input: SearchInput) -> SearchResult:
        """Perform comprehensive search across semantic and graph data."""
        try:
            start_time = datetime.utcnow()

            # Semantic search
            semantic_matches = []
            if search_input.include_semantic:
                from src.services.semantic.lightweight_semantic_service import (
                    get_semantic_service,
                )

                semantic_service = get_semantic_service()

                matches = await semantic_service.semantic_search(
                    search_input.query,
                    top_k=search_input.max_results or 50,
                    min_score=search_input.min_confidence or 0.1,
                )

                for match in matches:
                    semantic_matches.append(
                        SemanticMatch(
                            text=match.text,
                            score=match.score,
                            metadata=match.metadata,
                            entity_id=match.id,
                        ),
                    )

            # Graph search
            related_entities = []
            graph_connections = []
            if search_input.include_graph:
                from src.services.graph.knowledge_graph_service import (
                    get_knowledge_graph_service,
                )

                kg_service = get_knowledge_graph_service()

                # Search for entities matching the query
                search_results = await kg_service.search_entities(
                    search_input.query,
                    entity_types=(
                        [t.value for t in search_input.entity_types]
                        if search_input.entity_types
                        else None
                    ),
                    limit=search_input.max_results or 50,
                )

                for entity_data in search_results.get("entities", []):
                    related_entities.append(
                        Entity(
                            id=entity_data["id"],
                            type=EntityType(entity_data["type"]),
                            label=entity_data["label"],
                            properties=EntityProperties(
                                name=entity_data.get("properties", {}).get("name"),
                                description=entity_data.get("properties", {}).get(
                                    "description",
                                ),
                                url=entity_data.get("properties", {}).get("url"),
                                email=entity_data.get("properties", {}).get("email"),
                                created_at=entity_data.get("created_at"),
                                additional_data=str(entity_data.get("properties", {})),
                            ),
                            created_at=entity_data.get("created_at", datetime.utcnow()),
                            confidence_score=entity_data.get("confidence_score", 1.0),
                        ),
                    )

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return SearchResult(
                query=search_input.query,
                semantic_matches=semantic_matches,
                related_entities=related_entities,
                graph_connections=graph_connections,
                total_results=len(semantic_matches) + len(related_entities),
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Error in comprehensive search: {e}")
            return SearchResult(
                query=search_input.query,
                semantic_matches=[],
                related_entities=[],
                graph_connections=[],
                total_results=0,
                processing_time_ms=0.0,
            )

    @strawberry.field
    async def system_health(self) -> SystemHealth:
        """Get comprehensive system health information."""
        try:
            from src.services.graph.neo4j_service import get_neo4j_service
            from src.services.semantic.lightweight_semantic_service import (
                get_semantic_service,
            )

            # Check service health
            neo4j_service = get_neo4j_service()
            semantic_service = get_semantic_service()

            neo4j_health = await neo4j_service.health_check()
            semantic_health = await semantic_service.health_check()

            components = {
                "neo4j_graph_db": neo4j_health.get("status", "unknown"),
                "semantic_search": semantic_health.get("status", "unknown"),
                "api_server": "healthy",
                "graphql_api": "healthy",
            }

            # Create performance metrics
            performance_metrics = [
                AnalyticsMetric(
                    name="neo4j_nodes",
                    value=float(neo4j_health.get("total_nodes", 0)),
                    timestamp=datetime.utcnow(),
                ),
                AnalyticsMetric(
                    name="semantic_documents",
                    value=float(semantic_health.get("documents_indexed", 0)),
                    timestamp=datetime.utcnow(),
                ),
            ]

            return SystemHealth(
                status=(
                    "healthy"
                    if all(status == "healthy" for status in components.values())
                    else "degraded"
                ),
                version="10.2.0",
                timestamp=datetime.utcnow(),
                components=components,
                performance_metrics=performance_metrics,
                capabilities=[
                    "Knowledge Graph Management",
                    "Semantic Search",
                    "Entity Recognition",
                    "Graph Visualization",
                    "GraphQL API",
                    "Advanced Analytics",
                ],
            )

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return SystemHealth(
                status="error",
                version="10.2.0",
                timestamp=datetime.utcnow(),
                components={"system": "error"},
                performance_metrics=[],
                capabilities=[],
            )

    @strawberry.field
    async def graph_visualization(
        self,
        visualization_input: VisualizationInput,
    ) -> GraphVisualization:
        """Get graph visualization data."""
        try:
            from src.services.graph.knowledge_graph_service import (
                get_knowledge_graph_service,
            )

            kg_service = get_knowledge_graph_service()

            if visualization_input.center_entity_id:
                # Get subgraph around specific entity
                subgraph = await kg_service.get_entity_subgraph(
                    visualization_input.center_entity_id,
                    visualization_input.max_depth or 2,
                )
                nodes_data = [subgraph.get("center_entity", {})] + subgraph.get(
                    "connected_entities",
                    [],
                )
                edges_data = subgraph.get("relationships", [])
            else:
                # Get general graph visualization
                viz_data = await kg_service.get_graph_visualization(
                    max_nodes=visualization_input.max_nodes or 50,
                )
                nodes_data = viz_data.get("nodes", [])
                edges_data = viz_data.get("edges", [])

            # Convert to GraphQL types
            nodes = []
            for node_data in nodes_data:
                if node_data:  # Skip empty nodes
                    nodes.append(
                        Entity(
                            id=node_data["id"],
                            type=EntityType(node_data["type"]),
                            label=node_data["label"],
                            properties=EntityProperties(
                                name=node_data.get("properties", {}).get("name"),
                                description=node_data.get("properties", {}).get(
                                    "description",
                                ),
                                url=node_data.get("properties", {}).get("url"),
                                email=node_data.get("properties", {}).get("email"),
                                created_at=node_data.get("created_at"),
                                additional_data=str(node_data.get("properties", {})),
                            ),
                            created_at=node_data.get("created_at", datetime.utcnow()),
                            confidence_score=node_data.get("confidence_score", 1.0),
                        ),
                    )

            edges = []
            for edge_data in edges_data:
                edges.append(
                    Relationship(
                        id=edge_data["id"],
                        from_entity_id=edge_data["from_entity_id"],
                        to_entity_id=edge_data["to_entity_id"],
                        type=RelationshipType(edge_data["type"]),
                        properties=edge_data.get("properties", {}),
                        weight=edge_data.get("weight", 1.0),
                        created_at=edge_data.get("created_at", datetime.utcnow()),
                    ),
                )

            return GraphVisualization(
                nodes=nodes,
                edges=edges,
                layout_data={
                    "algorithm": visualization_input.layout_algorithm
                    or "force_directed",
                },
                filters_applied=[],
                node_count=len(nodes),
                edge_count=len(edges),
            )

        except Exception as e:
            logger.error(f"Error getting graph visualization: {e}")
            return GraphVisualization(
                nodes=[],
                edges=[],
                layout_data={},
                filters_applied=[],
                node_count=0,
                edge_count=0,
            )

    @strawberry.field
    async def analytics_insights(
        self,
        metrics: list[str],
        days_back: int | None = 30,
    ) -> list[InsightRecommendation]:
        """Generate AI-powered insights from analytics data."""
        try:
            from src.services.analytics.insight_generation_service import (
                get_insight_generation_service,
            )

            insight_service = get_insight_generation_service()

            # Generate sample time series data for the requested metrics
            time_series_data = {}
            for metric in metrics:
                # Create sample data (in production, this would come from actual data
                # sources)
                sample_data = []
                base_date = datetime.now() - timedelta(days=days_back)

                for i in range(days_back):
                    # Generate realistic sample data with trends
                    # Upward trend with noise
                    value = 100 + i * 0.5 + np.random.normal(0, 5)
                    sample_data.append((base_date + timedelta(days=i), value))

                time_series_data[metric] = sample_data

            # Generate insights
            insights = await insight_service.generate_comprehensive_insights(
                time_series_data,
            )

            # Convert to GraphQL types
            graphql_insights = []
            for insight in insights:
                graphql_insights.append(
                    InsightRecommendation(
                        id=insight.id,
                        title=insight.title,
                        description=insight.description,
                        confidence=insight.confidence,
                        category=insight.category.value,
                        priority=insight.priority.value,
                        supporting_data=insight.supporting_data,
                        action_suggestions=insight.action_suggestions,
                        created_at=insight.created_at,
                    ),
                )

            return graphql_insights

        except Exception as e:
            logger.error(f"Analytics insights generation failed: {e}")
            return []

    @strawberry.field
    async def correlation_analysis(
        self,
        metric_a: str,
        metric_b: str,
        days_back: int | None = 30,
    ) -> CorrelationAnalysis:
        """Perform correlation analysis between two metrics."""
        try:
            from src.services.analytics.correlation_engine import (
                CorrelationMethod,
                get_correlation_engine,
            )

            correlation_engine = get_correlation_engine()

            # Generate sample data for demonstration
            sample_data_a = [
                100 + i * 0.5 + np.random.normal(0, 3) for i in range(days_back)
            ]
            sample_data_b = [
                50 + i * 0.3 + np.random.normal(0, 2) for i in range(days_back)
            ]

            # Perform correlation analysis
            result = await correlation_engine.analyze_correlation(
                sample_data_a,
                sample_data_b,
                metric_a,
                metric_b,
                CorrelationMethod.PEARSON,
            )

            return CorrelationAnalysis(
                metric_a=result.metric_a,
                metric_b=result.metric_b,
                correlation_coefficient=result.correlation_coefficient,
                p_value=result.p_value,
                significance_level=result.significance_level,
                relationship_type=result.relationship_type,
            )

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return CorrelationAnalysis(
                metric_a=metric_a,
                metric_b=metric_b,
                correlation_coefficient=0.0,
                p_value=1.0,
                significance_level="error",
                relationship_type="none",
            )

    @strawberry.field
    async def trend_analysis(
        self,
        metric_name: str,
        days_back: int | None = 30,
    ) -> TrendAnalysis:
        """Perform comprehensive trend analysis on a metric."""
        try:
            from src.services.analytics.trend_analysis_service import (
                get_trend_analysis_service,
            )

            trend_service = get_trend_analysis_service()

            # Generate sample time series data
            sample_data = []
            base_date = datetime.now() - timedelta(days=days_back)

            for i in range(days_back):
                # Generate data with a clear upward trend
                value = 100 + i * 1.2 + np.random.normal(0, 3)
                sample_data.append((base_date + timedelta(days=i), value))

            # Perform trend analysis
            result = await trend_service.analyze_trend(
                sample_data,
                metric_name,
                include_forecast=True,
            )

            # Convert to GraphQL type
            return TrendAnalysis(
                metric_name=result.metric_name,
                trend_direction=result.trend_direction,
                trend_strength=result.trend_strength,
                confidence=result.trend_strength,
                prediction_horizon=result.forecast_horizon,
                historical_data=[
                    AnalyticsMetric(
                        name=metric_name,
                        value=sample_data[i][1],
                        timestamp=sample_data[i][0],
                    )
                    for i in range(len(sample_data))
                ],
                predicted_values=[
                    AnalyticsMetric(
                        name=f"{metric_name}_forecast",
                        value=result.forecast_values[i],
                        timestamp=datetime.now() + timedelta(days=i + 1),
                    )
                    for i in range(len(result.forecast_values))
                ],
            )

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return TrendAnalysis(
                metric_name=metric_name,
                trend_direction="unknown",
                trend_strength=0.0,
                confidence=0.0,
                prediction_horizon=0,
                historical_data=[],
                predicted_values=[],
            )


@strawberry.type
class Mutation:
    """GraphQL Mutation root type."""

    @strawberry.mutation
    async def create_entity(self, entity_input: EntityInput) -> Entity:
        """Create a new entity in the knowledge graph."""
        try:
            from src.services.graph.entity_service import get_entity_service

            entity_service = get_entity_service()

            entity_data = await entity_service.create_entity(
                entity_type=entity_input.type.value,
                properties={
                    "label": entity_input.label,
                    **(entity_input.properties or {}),
                },
            )

            return Entity(
                id=entity_data["id"],
                type=EntityType(entity_data["type"]),
                label=entity_data["label"],
                properties=EntityProperties(
                    name=entity_data.get("properties", {}).get("name"),
                    description=entity_data.get("properties", {}).get("description"),
                    url=entity_data.get("properties", {}).get("url"),
                    email=entity_data.get("properties", {}).get("email"),
                    created_at=entity_data.get("created_at"),
                    additional_data=str(entity_data.get("properties", {})),
                ),
                created_at=entity_data.get("created_at", datetime.utcnow()),
                confidence_score=entity_data.get("confidence_score", 1.0),
            )

        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            raise Exception(f"Failed to create entity: {str(e)}")

    @strawberry.mutation
    async def create_relationship(
        self,
        relationship_input: RelationshipInput,
    ) -> Relationship:
        """Create a new relationship between entities."""
        try:
            from src.services.graph.entity_service import get_entity_service

            entity_service = get_entity_service()

            relationship_data = await entity_service.create_relationship(
                from_entity_id=relationship_input.from_entity_id,
                to_entity_id=relationship_input.to_entity_id,
                relationship_type=relationship_input.type.value,
                properties=relationship_input.properties or {},
                weight=relationship_input.weight or 1.0,
            )

            return Relationship(
                id=relationship_data["id"],
                from_entity_id=relationship_data["from_entity_id"],
                to_entity_id=relationship_data["to_entity_id"],
                type=RelationshipType(relationship_data["type"]),
                properties=relationship_data.get("properties", {}),
                weight=relationship_data.get("weight", 1.0),
                created_at=relationship_data.get("created_at", datetime.utcnow()),
            )

        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            raise Exception(f"Failed to create relationship: {str(e)}")

    @strawberry.mutation
    async def process_document_for_entities(
        self,
        title: str,
        content: str,
        source: str | None = None,
    ) -> list[Entity]:
        """Process a document and extract entities for the knowledge graph."""
        try:
            from src.services.graph.knowledge_graph_service import (
                get_knowledge_graph_service,
            )

            kg_service = get_knowledge_graph_service()

            result = await kg_service.process_document(
                {
                    "title": title,
                    "content": content,
                    "source": source or "manual_upload",
                    "url": None,
                },
            )

            entities = []
            for entity_data in result.get("entities_created", []):
                entities.append(
                    Entity(
                        id=entity_data["id"],
                        type=EntityType(entity_data["type"]),
                        label=entity_data["label"],
                        properties=EntityProperties(
                            name=entity_data.get("properties", {}).get("name"),
                            description=entity_data.get("properties", {}).get(
                                "description",
                            ),
                            url=entity_data.get("properties", {}).get("url"),
                            email=entity_data.get("properties", {}).get("email"),
                            created_at=entity_data.get("created_at"),
                            additional_data=str(entity_data.get("properties", {})),
                        ),
                        created_at=entity_data.get("created_at", datetime.utcnow()),
                        confidence_score=entity_data.get("confidence_score", 1.0),
                    ),
                )

            return entities

        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise Exception(f"Failed to process document: {str(e)}")
