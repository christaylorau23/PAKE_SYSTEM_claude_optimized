"""Knowledge Graph Service

Provides high-level knowledge graph operations for the PAKE System.
Handles entity extraction from text, relationship inference, and graph visualization.
"""

import logging
from datetime import datetime
from typing import Any

from .entity_service import (
    EntityType,
    RelationshipType,
    get_entity_service,
)
from .neo4j_service import get_neo4j_service

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """High-level knowledge graph service.

    Provides intelligent knowledge graph operations including entity extraction,
    relationship inference, and graph analytics for research intelligence.
    """

    def __init__(self):
        self.entity_service = get_entity_service()
        self.neo4j_service = get_neo4j_service()

    async def process_document_entities(
        self,
        document_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a document and extract entities to knowledge graph.

        Args:
            document_data: Document with title, content, source, etc.

        Returns:
            Processing results with entities and relationships created
        """
        try:
            # Create document entity
            document_id = await self.entity_service.create_document(
                title=document_data["title"],
                source=document_data.get("source", "unknown"),
                url=document_data.get("url"),
                content=document_data.get("content"),
                publication_date=document_data.get("publication_date"),
                content_type=document_data.get("content_type", "text"),
            )

            if not document_id:
                logger.error("Failed to create document entity")
                return {"success": False, "error": "Failed to create document entity"}

            results = {
                "success": True,
                "document_id": document_id,
                "entities_created": [],
                "relationships_created": [],
                "processing_time_ms": 0,
            }

            start_time = datetime.utcnow()

            # Extract entities from content if available
            if document_data.get("content"):
                extraction_results = await self._extract_entities_from_text(
                    document_data["content"],
                    document_id,
                )
                results.update(extraction_results)

            # Process authors if this is a research paper
            if document_data.get("authors"):
                author_results = await self._process_authors(
                    document_data["authors"],
                    document_id,
                )
                results["entities_created"].extend(author_results["entities_created"])
                results["relationships_created"].extend(
                    author_results["relationships_created"],
                )

            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            results["processing_time_ms"] = round(processing_time, 2)

            logger.info(
                f"Processed document {document_id}: "
                f"{len(results['entities_created'])} entities, "
                f"{len(results['relationships_created'])} relationships",
            )

            return results

        except Exception as e:
            logger.error(f"Error processing document entities: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_entities_from_text(
        self,
        text: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Extract entities from text content using simple pattern matching.

        Note: This is a basic implementation. In production, you would use
        advanced NLP models like spaCy or transformers for entity recognition.
        """
        entities_created = []
        relationships_created = []

        try:
            # Simple pattern-based entity extraction
            # In a real implementation, use spaCy NER or similar

            # Extract potential organization names (capitalized words/phrases)
            import re

            # Pattern for organizations (often have Corp, Inc, Ltd, etc.)
            org_patterns = [
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Corp|Corporation|Inc|Incorporated|Ltd|Limited|LLC|Company|Co\.)\b",
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:University|Institute|School|College)\b",
            ]

            organizations = set()
            for pattern in org_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    organizations.add(match.strip())

            # Create organization entities
            for org_name in organizations:
                org_id = await self.entity_service.find_or_create_entity(
                    EntityType.ORGANIZATION,
                    {"name": org_name},
                )
                entities_created.append(
                    {
                        "id": org_id,
                        "type": EntityType.ORGANIZATION.value,
                        "name": org_name,
                    },
                )

                # Create MENTIONS relationship
                rel_id = await self.entity_service.create_relationship(
                    document_id,
                    org_id,
                    RelationshipType.MENTIONS,
                    {"confidence": 0.8, "extraction_method": "pattern_matching"},
                )
                if rel_id:
                    relationships_created.append(
                        {
                            "id": rel_id,
                            "type": RelationshipType.MENTIONS.value,
                            "from": document_id,
                            "to": org_id,
                        },
                    )

            # Extract potential technology/concept names
            tech_keywords = [
                "machine learning",
                "artificial intelligence",
                "neural network",
                "deep learning",
                "natural language processing",
                "computer vision",
                "blockchain",
                "cryptocurrency",
                "cloud computing",
                "kubernetes",
                "docker",
                "microservices",
                "api",
                "database",
                "postgresql",
                "mongodb",
                "redis",
                "elasticsearch",
                "python",
                "javascript",
                "react",
                "fastapi",
                "flask",
                "django",
                "tensorflow",
                "pytorch",
            ]

            concepts_found = set()
            text_lower = text.lower()
            for keyword in tech_keywords:
                if keyword in text_lower:
                    concepts_found.add(keyword.title())

            # Create concept entities
            for concept_name in concepts_found:
                concept_id = await self.entity_service.find_or_create_entity(
                    EntityType.CONCEPT,
                    {"name": concept_name, "category": "technology"},
                )
                entities_created.append(
                    {
                        "id": concept_id,
                        "type": EntityType.CONCEPT.value,
                        "name": concept_name,
                    },
                )

                # Create MENTIONS relationship
                rel_id = await self.entity_service.create_relationship(
                    document_id,
                    concept_id,
                    RelationshipType.MENTIONS,
                    {"confidence": 0.7, "extraction_method": "keyword_matching"},
                )
                if rel_id:
                    relationships_created.append(
                        {
                            "id": rel_id,
                            "type": RelationshipType.MENTIONS.value,
                            "from": document_id,
                            "to": concept_id,
                        },
                    )

            return {
                "entities_created": entities_created,
                "relationships_created": relationships_created,
            }

        except Exception as e:
            logger.error(f"Error extracting entities from text: {e}")
            return {"entities_created": [], "relationships_created": []}

    async def _process_authors(
        self,
        authors: list[str],
        document_id: str,
    ) -> dict[str, Any]:
        """Process author information and create entities/relationships."""
        entities_created = []
        relationships_created = []

        try:
            for author_name in authors:
                # Create or find author entity
                author_id = await self.entity_service.find_or_create_entity(
                    EntityType.PERSON,
                    {"name": author_name.strip()},
                )
                entities_created.append(
                    {
                        "id": author_id,
                        "type": EntityType.PERSON.value,
                        "name": author_name.strip(),
                    },
                )

                # Create AUTHOR_OF relationship
                rel_id = await self.entity_service.create_relationship(
                    author_id,
                    document_id,
                    RelationshipType.AUTHOR_OF,
                )
                if rel_id:
                    relationships_created.append(
                        {
                            "id": rel_id,
                            "type": RelationshipType.AUTHOR_OF.value,
                            "from": author_id,
                            "to": document_id,
                        },
                    )

            return {
                "entities_created": entities_created,
                "relationships_created": relationships_created,
            }

        except Exception as e:
            logger.error(f"Error processing authors: {e}")
            return {"entities_created": [], "relationships_created": []}

    async def get_knowledge_graph_visualization(
        self,
        center_entity_id: str | None = None,
        entity_types: list[str] | None = None,
        max_nodes: int = 50,
    ) -> dict[str, Any]:
        """Get knowledge graph data for visualization.

        Args:
            center_entity_id: Optional central entity for subgraph
            entity_types: Optional filter by entity types
            max_nodes: Maximum nodes to return

        Returns:
            Graph visualization data
        """
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            if center_entity_id:
                # Get subgraph around specific entity
                graph_data = await self.entity_service.get_knowledge_subgraph(
                    center_entity_id,
                    depth=2,
                    max_nodes=max_nodes,
                )
            else:
                # Get general graph sample
                graph_data = await self._get_sample_graph(entity_types, max_nodes)

            # Format for visualization
            visualization_data = self._format_for_visualization(graph_data)

            return {
                "success": True,
                "graph_data": visualization_data,
                "metadata": {
                    "node_count": len(visualization_data["nodes"]),
                    "edge_count": len(visualization_data["edges"]),
                    "center_entity": center_entity_id,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error getting knowledge graph visualization: {e}")
            return {
                "success": False,
                "error": str(e),
                "graph_data": {"nodes": [], "edges": []},
            }

    async def _get_sample_graph(
        self,
        entity_types: list[str] | None = None,
        max_nodes: int = 50,
    ) -> dict[str, Any]:
        """Get a sample of the knowledge graph."""
        try:
            # Build query to get sample nodes and their relationships
            if entity_types:
                type_filter = ":" + "|".join(entity_types)
            else:
                type_filter = ""

            query = f"""
            MATCH (n{type_filter})
            WITH n
            LIMIT {max_nodes}
            OPTIONAL MATCH (n)-[r]-(connected)
            WHERE connected IS NOT NULL
            RETURN
                collect(DISTINCT {{
                    id: id(n),
                    properties: n,
                    labels: labels(n)
                }}) as nodes,
                collect(DISTINCT {{
                    id: id(r),
                    type: type(r),
                    properties: r,
                    source: id(startNode(r)),
                    target: id(endNode(r))
                }}) as relationships
            """

            result = self.neo4j_service.execute_query(query)

            if result and result[0]:
                data = result[0]
                return {
                    "nodes": data["nodes"] or [],
                    "relationships": data["relationships"] or [],
                }

            return {"nodes": [], "relationships": []}

        except Exception as e:
            logger.error(f"Error getting sample graph: {e}")
            return {"nodes": [], "relationships": []}

    def _format_for_visualization(self, graph_data: dict[str, Any]) -> dict[str, Any]:
        """Format graph data for frontend visualization."""
        try:
            nodes = []
            edges = []

            # Process nodes
            for node in graph_data.get("nodes", []):
                node_id = str(node["id"])
                properties = node.get("properties", {})
                labels = node.get("labels", [])

                # Determine node type and display name
                node_type = labels[0] if labels else "Unknown"
                display_name = (
                    properties.get("name")
                    or properties.get("title")
                    or f"{node_type} {node_id}"
                )

                # Color coding by type
                color_map = {
                    "Person": "#FF6B6B",
                    "Organization": "#4ECDC4",
                    "Concept": "#45B7D1",
                    "Document": "#96CEB4",
                    "Technology": "#FFEAA7",
                    "ResearchPaper": "#DDA0DD",
                    "Location": "#98D8C8",
                }

                formatted_node = {
                    "id": node_id,
                    "label": display_name,
                    "type": node_type,
                    "properties": properties,
                    "color": color_map.get(node_type, "#BDC3C7"),
                    "size": min(max(len(display_name) * 2, 20), 50),
                    "metadata": {
                        "labels": labels,
                        "created_at": properties.get("created_at"),
                        "entity_type": properties.get("entity_type"),
                    },
                }
                nodes.append(formatted_node)

            # Process edges/relationships
            processed_relationships = set()
            for relationship in graph_data.get("relationships", []):
                rel_id = str(relationship["id"])
                rel_type = relationship.get("type", "RELATED_TO")
                properties = relationship.get("properties", {})

                # Get source and target from properties if available
                source = str(relationship.get("source", ""))
                target = str(relationship.get("target", ""))

                # Skip if we can't determine source/target
                if not source or not target:
                    continue

                # Avoid duplicate relationships
                rel_key = f"{source}-{rel_type}-{target}"
                if rel_key in processed_relationships:
                    continue
                processed_relationships.add(rel_key)

                formatted_edge = {
                    "id": rel_id,
                    "source": source,
                    "target": target,
                    "label": rel_type.replace("_", " "),
                    "type": rel_type,
                    "properties": properties,
                    "weight": properties.get("confidence", 1.0),
                    "metadata": {
                        "created_at": properties.get("created_at"),
                        "relationship_type": properties.get("relationship_type"),
                    },
                }
                edges.append(formatted_edge)

            return {"nodes": nodes, "edges": edges}

        except Exception as e:
            logger.error(f"Error formatting graph data for visualization: {e}")
            return {"nodes": [], "edges": []}

    async def get_entity_insights(self, entity_id: str) -> dict[str, Any]:
        """Get insights about a specific entity.

        Args:
            entity_id: Entity ID to analyze

        Returns:
            Entity insights and analytics
        """
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            # Get entity details
            entity = await self.entity_service.get_entity_by_id(entity_id)
            if not entity:
                return {"success": False, "error": "Entity not found"}

            # Get relationships
            relationships = await self.entity_service.get_entity_relationships(
                entity_id,
            )

            # Analyze relationships
            relationship_analysis = self._analyze_relationships(relationships)

            # Get network metrics
            network_metrics = await self._get_entity_network_metrics(entity_id)

            return {
                "success": True,
                "entity": entity,
                "relationship_count": len(relationships),
                "relationship_analysis": relationship_analysis,
                "network_metrics": network_metrics,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting entity insights for {entity_id}: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_relationships(self, relationships: list[dict]) -> dict[str, Any]:
        """Analyze entity relationships for insights."""
        if not relationships:
            return {"total": 0, "by_type": {}, "most_common_type": None}

        by_type = {}
        for rel in relationships:
            rel_type = rel.get("type", "UNKNOWN")
            by_type[rel_type] = by_type.get(rel_type, 0) + 1

        most_common_type = max(by_type.items(), key=lambda x: x[1]) if by_type else None

        return {
            "total": len(relationships),
            "by_type": by_type,
            "most_common_type": most_common_type[0] if most_common_type else None,
            "unique_types": len(by_type),
        }

    async def _get_entity_network_metrics(self, entity_id: str) -> dict[str, Any]:
        """Calculate network metrics for an entity."""
        try:
            # Simple network metrics
            query = """
            MATCH (center)-[r]-(connected)
            WHERE id(center) = $entity_id
            WITH center, count(DISTINCT connected) as degree,
                 count(DISTINCT r) as relationship_count
            RETURN degree, relationship_count
            """

            result = self.neo4j_service.execute_query(
                query,
                {"entity_id": int(entity_id)},
            )

            if result:
                return {
                    "degree": result[0].get("degree", 0),
                    "relationship_count": result[0].get("relationship_count", 0),
                }

            return {"degree": 0, "relationship_count": 0}

        except Exception as e:
            logger.error(f"Error calculating network metrics: {e}")
            return {"degree": 0, "relationship_count": 0}

    async def get_graph_statistics(self) -> dict[str, Any]:
        """Get comprehensive knowledge graph statistics."""
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            stats = await self.entity_service.get_graph_statistics()

            # Add additional analytics
            entity_distribution = await self._get_entity_type_distribution()
            relationship_distribution = await self._get_relationship_type_distribution()

            return {
                "success": True,
                "basic_stats": stats,
                "entity_distribution": entity_distribution,
                "relationship_distribution": relationship_distribution,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {"success": False, "error": str(e)}

    async def _get_entity_type_distribution(self) -> dict[str, int]:
        """Get distribution of entity types."""
        try:
            query = """
            MATCH (n)
            RETURN labels(n) as labels, count(n) as count
            ORDER BY count DESC
            """

            result = self.neo4j_service.execute_query(query)
            distribution = {}

            for record in result:
                labels = record["labels"]
                count = record["count"]
                # Use first label as primary type
                if labels:
                    primary_label = labels[0]
                    distribution[primary_label] = (
                        distribution.get(primary_label, 0) + count
                    )

            return distribution

        except Exception as e:
            logger.error(f"Error getting entity type distribution: {e}")
            return {}

    async def _get_relationship_type_distribution(self) -> dict[str, int]:
        """Get distribution of relationship types."""
        try:
            query = """
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(r) as count
            ORDER BY count DESC
            """

            result = self.neo4j_service.execute_query(query)
            distribution = {}

            for record in result:
                rel_type = record["rel_type"]
                count = record["count"]
                distribution[rel_type] = count

            return distribution

        except Exception as e:
            logger.error(f"Error getting relationship type distribution: {e}")
            return {}


# Singleton instance
_knowledge_graph_service = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get or create knowledge graph service singleton."""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service
