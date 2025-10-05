"""Neo4j Database Service.

Provides core Neo4j database connectivity and operations for the PAKE System.
Handles entity creation, relationship management, and graph querying.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

logger = logging.getLogger(__name__)


class Neo4jService:
    """Core Neo4j database service for graph operations.

    Provides high-level interface for entity and relationship management,
    with async support and comprehensive error handling.
    """

    def __init__(self) -> None:
        """Initialize Neo4j service with connection parameters.

        Args:
            uri: Neo4j database URI
            user: Database username
            REDACTED_SECRET: Database REDACTED_SECRET
        """
        self.uri = uri
        self.user = user
        self.REDACTED_SECRET = REDACTED_SECRET
        self.driver = None
        self._connection_pool_size = 10

    async def connect(self) -> bool:
        """Establish connection to Neo4j database.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.REDACTED_SECRET),
                max_connection_pool_size=self._connection_pool_size,
            )

            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")

            logger.info("Connected to Neo4j at %s", self.uri)
            return True

        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to connect to Neo4j: %s", e)
            return False

    async def disconnect(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def execute_query(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            msg = "Neo4j driver not connected"
            raise RuntimeError(msg)

        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]

        except TransientError as e:
            logger.warning("Transient Neo4j error: %s", e)
            raise
        except Exception as e:
            logger.error("Neo4j query error: %s", e)
            raise

    def execute_write_transaction(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """Execute a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records
        """
        if not self.driver:
            msg = "Neo4j driver not connected"
            raise RuntimeError(msg)

        def _transaction_function(self) -> None:
            result = tx.run(query, parameters or {})
            return [record.data() for record in result]

        try:
            with self.driver.session() as session:
                return session.execute_write(_transaction_function)

        except Exception as e:
            logger.error("Neo4j write transaction error: %s", e)
            raise

    # Entity Management

    def create_entity(self, entity_type: str, properties: Dict[str, Any]) -> str:
        """Create a new entity in the graph.

        Args:
            entity_type: Type/label of the entity (e.g., 'Person', 'Organization')
            properties: Entity properties

        Returns:
            str: Created entity ID
        """
        # Add metadata
        properties = properties.copy()
        properties["created_at"] = datetime.now(UTC).isoformat()
        properties["entity_type"] = entity_type

        query = f"""
        CREATE (e:{entity_type} $props)
        RETURN id(e) as entity_id, e
        """

        result = self.execute_write_transaction(query, {"props": properties})
        if result:
            entity_id = result[0]["entity_id"]
            logger.info("Created %s entity with ID: %s", entity_type, entity_id)
            return str(entity_id)

        msg = "Failed to create entity"
        raise RuntimeError(msg)

    def update_entity(self, entity_id: str, properties: Dict[str, Any]) -> bool:
        """Update an existing entity.

        Args:
            entity_id: ID of entity to update
            properties: Properties to update

        Returns:
            bool: True if successful
        """
        # Add update timestamp
        properties = properties.copy()
        properties["updated_at"] = datetime.now(UTC).isoformat()

        query = """
        MATCH (e) WHERE id(e) = $entity_id
        SET e += $props
        RETURN e
        """

        result = self.execute_write_transaction(
            query,
            {"entity_id": int(entity_id), "props": properties},
        )

        success = len(result) > 0
        if success:
            logger.info("Updated entity %s", entity_id)

        return success

    def get_entity(self, entity_id: str) -> dict | None:
        """Retrieve entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity data or None if not found
        """
        query = """
        MATCH (e) WHERE id(e) = $entity_id
        RETURN e, labels(e) as labels
        """

        result = self.execute_query(query, {"entity_id": int(entity_id)})
        if result:
            entity_data = result[0]["e"]
            entity_data["labels"] = result[0]["labels"]
            entity_data["id"] = entity_id
            return entity_data

        return None

    def find_entities_by_type(self, entity_type: str, limit: int = 100) -> list[dict]:
        """Find entities by type/label.

        Args:
            entity_type: Entity type to search for
            limit: Maximum number of results

        Returns:
            List of matching entities
        """
        query = f"""
        MATCH (e:{entity_type})
        RETURN id(e) as id, e, labels(e) as labels
        LIMIT $limit
        """

        results = self.execute_query(query, {"limit": limit})
        entities = []

        for record in results:
            entity = record["e"]
            entity["id"] = str(record["id"])
            entity["labels"] = record["labels"]
            entities.append(entity)

        return entities

    def search_entities(
        self,
        search_term: str,
        entity_types: List[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search entities by text content.

        Args:
            search_term: Text to search for
            entity_types: Optional list of entity types to filter by
            limit: Maximum results

        Returns:
            List of matching entities
        """
        type_filter = ":" + "|".join(entity_types) if entity_types else ""

        query = f"""
        MATCH (e{type_filter})
        WHERE any(prop in keys(e) WHERE toString(e[prop]) CONTAINS $search_term)
        RETURN id(e) as id, e, labels(e) as labels
        LIMIT $limit
        """

        results = self.execute_query(
            query,
            {"search_term": search_term, "limit": limit},
        )

        entities = []
        for record in results:
            entity = record["e"]
            entity["id"] = str(record["id"])
            entity["labels"] = record["labels"]
            entities.append(entity)

        return entities

    # Relationship Management

    def create_relationship(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relationship_type: str,
        properties: dict | None = None,
    ) -> str:
        """Create a relationship between two entities.

        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional relationship properties

        Returns:
            str: Relationship ID
        """
        properties = properties or {}
        properties["created_at"] = datetime.now(UTC).isoformat()
        properties["relationship_type"] = relationship_type

        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:{relationship_type} $props]->(b)
        RETURN id(r) as rel_id
        """

        result = self.execute_write_transaction(
            query,
            {
                "from_id": int(from_entity_id),
                "to_id": int(to_entity_id),
                "props": properties,
            },
        )

        if result:
            rel_id = result[0]["rel_id"]
            logger.info(
                "Created %s relationship: %s -> %s",
                relationship_type,
                from_entity_id,
                to_entity_id,
            )
            return str(rel_id)

        msg = "Failed to create relationship"
        raise RuntimeError(msg)

    def get_entity_relationships(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> list[dict]:
        """Get all relationships for an entity.

        Args:
            entity_id: Entity ID
            direction: 'in', 'out', or 'both'

        Returns:
            List of relationships with connected entities
        """
        if direction == "out":
            pattern = "(e)-[r]->(connected)"
        elif direction == "in":
            pattern = "(connected)-[r]->(e)"
        else:  # both
            pattern = "(e)-[r]-(connected)"

        query = f"""
        MATCH {pattern}
        WHERE id(e) = $entity_id
        RETURN id(r) as rel_id, type(r) as rel_type, r as relationship,
               id(connected) as connected_id, connected, labels(connected) as connected_labels
        """

        results = self.execute_query(query, {"entity_id": int(entity_id)})

        relationships = []
        for record in results:
            rel_data = {
                "id": str(record["rel_id"]),
                "type": record["rel_type"],
                "properties": record["relationship"],
                "connected_entity": {
                    "id": str(record["connected_id"]),
                    "properties": record["connected"],
                    "labels": record["connected_labels"],
                },
            }
            relationships.append(rel_data)

        return relationships

    # Graph Analysis

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get basic graph statistics.

        Returns:
            Dictionary with graph metrics
        """
        queries = {
            "total_nodes": "MATCH (n) RETURN count(n) as count",
            "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
            "node_labels": "CALL db.labels() YIELD label RETURN collect(label) as labels",
            "relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types",
        }

        stats = {}
        for stat_name, query in queries.items():
            try:
                result = self.execute_query(query)
                if stat_name in ["node_labels", "relationship_types"]:
                    stats[stat_name] = result[0][list(result[0].keys())[0]]
                else:
                    stats[stat_name] = result[0]["count"]
            except Exception as e:
                logger.warning("Failed to get %s: %s", stat_name, e)
                stats[stat_name] = 0

        return stats

    def get_subgraph(
        self,
        center_entity_id: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> Dict[str, Any]:
        """Get a subgraph centered on a specific entity.

        Args:
            center_entity_id: Central entity ID
            depth: How many hops to traverse
            max_nodes: Maximum nodes to return

        Returns:
            Graph data with nodes and relationships
        """
        query = f"""
        MATCH path = (center)-[*1..{depth}]-(connected)
        WHERE id(center) = $center_id
        WITH center, connected, relationships(path) as rels
        WITH center, collect(DISTINCT connected)[0..{max_nodes}] as nodes,
             reduce(all_rels = [], rel in rels | all_rels + rel) as all_rels
        RETURN
            id(center) as center_id, center,
            [n in nodes | {id: id(n), properties: n, labels: labels(n)} ] as connected_nodes,
            [r in all_rels | {id: id(r), type: type(r), properties: r} ] as relationships
        """

        result = self.execute_query(query, {"center_id": int(center_entity_id)})

        if not result:
            return {"nodes": [], "relationships": []}

        data = result[0]

        # Include center node
        nodes = [
            {
                "id": str(data["center_id"]),
                "properties": data["center"],
                "labels": ["Center"],  # Add special label for center node
            },
        ]

        # Add connected nodes
        if data["connected_nodes"]:
            for node in data["connected_nodes"]:
                nodes.append(
                    {
                        "id": str(node["id"]),
                        "properties": node["properties"],
                        "labels": node["labels"],
                    },
                )

        # Format relationships
        relationships = []
        if data["relationships"]:
            for rel in data["relationships"]:
                relationships.append(
                    {
                        "id": str(rel["id"]),
                        "type": rel["type"],
                        "properties": rel["properties"],
                    },
                )

        return {
            "nodes": nodes,
            "relationships": relationships,
            "center_id": center_entity_id,
        }

    # Health and Maintenance

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Neo4j connection.

        Returns:
            Health status information
        """
        try:
            stats = self.get_graph_stats()

            return {
                "status": "healthy",
                "connection": "connected",
                "uri": self.uri,
                "stats": stats,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e),
                "uri": self.uri,
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Singleton instance
_neo4j_service = None


def get_neo4j_service() -> Neo4jService:
    """Get or create Neo4j service singleton."""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service
