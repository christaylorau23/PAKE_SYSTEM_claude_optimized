"""Entity Management Service

Provides high-level entity management functionality for the PAKE System.
Handles different entity types, validation, and business logic for knowledge graph entities.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .neo4j_service import get_neo4j_service

logger = logging.getLogger(__name__)


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


class RelationshipType(Enum):
    """Supported relationship types."""

    WORKS_FOR = "WORKS_FOR"
    LOCATED_IN = "LOCATED_IN"
    MENTIONS = "MENTIONS"
    RELATED_TO = "RELATED_TO"
    AUTHOR_OF = "AUTHOR_OF"
    PUBLISHED_BY = "PUBLISHED_BY"
    CITES = "CITES"
    COLLABORATED_WITH = "COLLABORATED_WITH"
    PART_OF = "PART_OF"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    OCCURRED_AT = "OCCURRED_AT"
    ACQUIRED_BY = "ACQUIRED_BY"
    FOUNDED = "FOUNDED"
    DEVELOPS = "DEVELOPS"


@dataclass
class EntitySchema:
    """Schema definition for an entity type."""

    entity_type: EntityType
    required_fields: set[str]
    optional_fields: set[str]
    validation_rules: dict[str, callable]


class EntityService:
    """High-level entity management service.

    Provides entity creation, validation, relationship management,
    and business logic for knowledge graph operations.
    """

    def __init__(self):
        self.neo4j_service = get_neo4j_service()
        self._entity_schemas = self._init_schemas()

    def _init_schemas(self) -> dict[EntityType, EntitySchema]:
        """Initialize entity schemas with validation rules."""

        def validate_email(value: str) -> bool:
            """Validate email format."""
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return bool(re.match(pattern, value))

        def validate_url(value: str) -> bool:
            """Validate URL format."""
            pattern = r"^https?://[^\s/$.?#].[^\s]*$"
            return bool(re.match(pattern, value))

        def validate_non_empty(value: str) -> bool:
            """Validate non-empty string."""
            return isinstance(value, str) and len(value.strip()) > 0

        schemas = {
            EntityType.PERSON: EntitySchema(
                entity_type=EntityType.PERSON,
                required_fields={"name"},
                optional_fields={"email", "affiliation", "bio", "orcid", "linkedin"},
                validation_rules={
                    "name": validate_non_empty,
                    "email": validate_email,
                    "orcid": validate_url,
                    "linkedin": validate_url,
                },
            ),
            EntityType.ORGANIZATION: EntitySchema(
                entity_type=EntityType.ORGANIZATION,
                required_fields={"name"},
                optional_fields={
                    "website",
                    "description",
                    "location",
                    "industry",
                    "founded_year",
                },
                validation_rules={
                    "name": validate_non_empty,
                    "website": validate_url,
                    "description": validate_non_empty,
                },
            ),
            EntityType.RESEARCH_PAPER: EntitySchema(
                entity_type=EntityType.RESEARCH_PAPER,
                required_fields={"title"},
                optional_fields={
                    "abstract",
                    "authors",
                    "journal",
                    "doi",
                    "arxiv_id",
                    "pubmed_id",
                    "publication_date",
                    "keywords",
                    "url",
                },
                validation_rules={
                    "title": validate_non_empty,
                    "url": validate_url,
                    "doi": validate_non_empty,
                },
            ),
            EntityType.TECHNOLOGY: EntitySchema(
                entity_type=EntityType.TECHNOLOGY,
                required_fields={"name"},
                optional_fields={
                    "description",
                    "category",
                    "version",
                    "documentation_url",
                    "license",
                },
                validation_rules={
                    "name": validate_non_empty,
                    "documentation_url": validate_url,
                },
            ),
            EntityType.CONCEPT: EntitySchema(
                entity_type=EntityType.CONCEPT,
                required_fields={"name"},
                optional_fields={
                    "description",
                    "category",
                    "synonyms",
                    "wikipedia_url",
                },
                validation_rules={
                    "name": validate_non_empty,
                    "wikipedia_url": validate_url,
                },
            ),
            EntityType.DOCUMENT: EntitySchema(
                entity_type=EntityType.DOCUMENT,
                required_fields={"title", "source"},
                optional_fields={
                    "content",
                    "url",
                    "author",
                    "publication_date",
                    "content_type",
                    "summary",
                },
                validation_rules={
                    "title": validate_non_empty,
                    "source": validate_non_empty,
                    "url": validate_url,
                },
            ),
        }

        return schemas

    def validate_entity(
        self,
        entity_type: EntityType,
        properties: dict[str, Any],
    ) -> list[str]:
        """Validate entity properties against schema.

        Args:
            entity_type: Type of entity to validate
            properties: Entity properties to validate

        Returns:
            List of validation errors (empty if valid)
        """
        if entity_type not in self._entity_schemas:
            return [f"Unsupported entity type: {entity_type}"]

        schema = self._entity_schemas[entity_type]
        errors = []

        # Check required fields
        missing_fields = schema.required_fields - set(properties.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate field values
        for field, value in properties.items():
            if field in schema.validation_rules:
                validator = schema.validation_rules[field]
                try:
                    if not validator(value):
                        errors.append(f"Invalid value for field '{field}': {value}")
                except Exception as e:
                    errors.append(f"Validation error for field '{field}': {str(e)}")

        return errors

    async def create_entity(
        self,
        entity_type: EntityType,
        properties: dict[str, Any],
    ) -> str | None:
        """Create a new entity with validation.

        Args:
            entity_type: Type of entity to create
            properties: Entity properties

        Returns:
            Entity ID if successful, None otherwise
        """
        # Validate entity
        validation_errors = self.validate_entity(entity_type, properties)
        if validation_errors:
            logger.error(f"Entity validation failed: {validation_errors}")
            return None

        try:
            # Connect to Neo4j if not connected
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            # Add metadata
            properties = properties.copy()
            properties["entity_type"] = entity_type.value

            # Create entity
            entity_id = self.neo4j_service.create_entity(entity_type.value, properties)
            logger.info(f"Created {entity_type.value} entity: {entity_id}")

            return entity_id

        except Exception as e:
            logger.error(f"Failed to create {entity_type.value} entity: {e}")
            return None

    async def create_person(
        self,
        name: str,
        email: str | None = None,
        affiliation: str | None = None,
        **kwargs,
    ) -> str | None:
        """Create a Person entity."""
        properties = {"name": name}
        if email:
            properties["email"] = email
        if affiliation:
            properties["affiliation"] = affiliation
        properties.update(kwargs)

        return await self.create_entity(EntityType.PERSON, properties)

    async def create_organization(
        self,
        name: str,
        website: str | None = None,
        description: str | None = None,
        **kwargs,
    ) -> str | None:
        """Create an Organization entity."""
        properties = {"name": name}
        if website:
            properties["website"] = website
        if description:
            properties["description"] = description
        properties.update(kwargs)

        return await self.create_entity(EntityType.ORGANIZATION, properties)

    async def create_research_paper(
        self,
        title: str,
        abstract: str | None = None,
        authors: list[str] | None = None,
        doi: str | None = None,
        **kwargs,
    ) -> str | None:
        """Create a Research Paper entity."""
        properties = {"title": title}
        if abstract:
            properties["abstract"] = abstract
        if authors:
            properties["authors"] = authors
        if doi:
            properties["doi"] = doi
        properties.update(kwargs)

        return await self.create_entity(EntityType.RESEARCH_PAPER, properties)

    async def create_document(
        self,
        title: str,
        source: str,
        url: str | None = None,
        content: str | None = None,
        **kwargs,
    ) -> str | None:
        """Create a Document entity."""
        properties = {"title": title, "source": source}
        if url:
            properties["url"] = url
        if content:
            properties["content"] = content
        properties.update(kwargs)

        return await self.create_entity(EntityType.DOCUMENT, properties)

    async def create_relationship(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relationship_type: RelationshipType,
        properties: dict[str, Any] | None = None,
    ) -> str | None:
        """Create a relationship between entities.

        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional relationship properties

        Returns:
            Relationship ID if successful
        """
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            rel_id = self.neo4j_service.create_relationship(
                from_entity_id,
                to_entity_id,
                relationship_type.value,
                properties,
            )

            logger.info(
                f"Created {relationship_type.value} relationship: {from_entity_id} -> {
                    to_entity_id
                }",
            )
            return rel_id

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return None

    async def find_or_create_entity(
        self,
        entity_type: EntityType,
        properties: dict[str, Any],
    ) -> str:
        """Find existing entity or create new one.

        Args:
            entity_type: Entity type
            properties: Entity properties

        Returns:
            Entity ID (existing or newly created)
        """
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            # Try to find existing entity by name/title
            search_field = "title" if "title" in properties else "name"
            if search_field in properties:
                existing = self.neo4j_service.search_entities(
                    properties[search_field],
                    [entity_type.value],
                )

                if existing:
                    # Check for exact match
                    for entity in existing:
                        if (
                            entity["properties"].get(search_field)
                            == properties[search_field]
                        ):
                            logger.info(
                                f"Found existing {entity_type.value} entity: {
                                    entity['id']
                                }",
                            )
                            return entity["id"]

            # Create new entity if not found
            entity_id = await self.create_entity(entity_type, properties)
            if entity_id:
                logger.info(f"Created new {entity_type.value} entity: {entity_id}")
                return entity_id
            raise RuntimeError("Failed to create entity")

        except Exception as e:
            logger.error(f"Error in find_or_create_entity: {e}")
            raise

    async def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """Get entity by ID."""
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            return self.neo4j_service.get_entity(entity_id)

        except Exception as e:
            logger.error(f"Error getting entity {entity_id}: {e}")
            return None

    async def search_entities(
        self,
        search_term: str,
        entity_types: list[EntityType] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search entities by text."""
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            type_strings = [et.value for et in entity_types] if entity_types else None

            return self.neo4j_service.search_entities(search_term, type_strings, limit)

        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []

    async def get_entity_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all relationships for an entity."""
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            return self.neo4j_service.get_entity_relationships(entity_id)

        except Exception as e:
            logger.error(f"Error getting relationships for entity {entity_id}: {e}")
            return []

    async def get_knowledge_subgraph(
        self,
        center_entity_id: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> dict[str, Any]:
        """Get knowledge subgraph around an entity."""
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            return self.neo4j_service.get_subgraph(center_entity_id, depth, max_nodes)

        except Exception as e:
            logger.error(f"Error getting subgraph for entity {center_entity_id}: {e}")
            return {"nodes": [], "relationships": []}

    async def get_graph_statistics(self) -> dict[str, Any]:
        """Get knowledge graph statistics."""
        try:
            if not self.neo4j_service.driver:
                await self.neo4j_service.connect()

            return self.neo4j_service.get_graph_stats()

        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {}


# Singleton instance
_entity_service = None


def get_entity_service() -> EntityService:
    """Get or create entity service singleton."""
    global _entity_service
    if _entity_service is None:
        _entity_service = EntityService()
    return _entity_service
