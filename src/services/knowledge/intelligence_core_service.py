"""Intelligence Core Service

Central service implementing the tripartite knowledge core architecture from the
Personal Intelligence Engine blueprint. Coordinates between:
1. Obsidian vault (file-based knowledge)
2. Neo4j graph database (explicit relationships)
3. PostgreSQL vector database (semantic similarity)

Following PAKE System enterprise standards with comprehensive error handling,
async/await patterns, and production-ready performance.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import frontmatter

# Obsidian vault processing
# Neo4j integration
from neo4j import AsyncDriver, AsyncGraphDatabase
from obsidiantools.api import Vault

# PAKE System imports
from src.services.caching.redis_cache_service import CacheService

# Vector database and NLP
from src.services.database.vector_database_service import (
    VectorDatabaseService,
    VectorType,
    get_vector_database_service,
)
from src.services.nlp.intelligence_nlp_service import (
    DocumentAnalysis,
    ExtractedEntity,
    ExtractedRelationship,
    IntelligenceNLPService,
    get_intelligence_nlp_service,
)

logger = logging.getLogger(__name__)


class KnowledgeSourceType(Enum):
    """Types of knowledge sources in the system."""

    OBSIDIAN_NOTE = "obsidian_note"
    EXTERNAL_DOCUMENT = "external_document"
    WEB_CONTENT = "web_content"
    ACADEMIC_PAPER = "academic_paper"
    SOCIAL_MEDIA = "social_media"
    EMAIL_CONTENT = "email_content"


class SyncStatus(Enum):
    """Synchronization status for knowledge items."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class KnowledgeItem:
    """Unified knowledge item across all storage systems."""

    id: str
    title: str
    content: str
    source_type: KnowledgeSourceType
    source_path: str

    # Metadata
    tags: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Processing results
    entities: list[ExtractedEntity] = field(default_factory=list)
    relationships: list[ExtractedRelationship] = field(default_factory=list)
    semantic_embedding: bytes | None = None

    # Cross-system references
    neo4j_node_ids: list[str] = field(default_factory=list)
    vector_db_ids: list[str] = field(default_factory=list)
    linked_items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class KnowledgeQuery:
    """Query specification for knowledge retrieval."""

    query_text: str
    query_type: str = "semantic"  # semantic, graph, hybrid
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 10
    similarity_threshold: float = 0.7
    include_entities: bool = True
    include_relationships: bool = True
    expand_graph: bool = False


@dataclass(frozen=True)
class KnowledgeQueryResult:
    """Result from knowledge query."""

    items: list[KnowledgeItem]
    total_found: int
    query_time_ms: float
    sources_searched: list[str]
    related_entities: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    suggested_queries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncResult:
    """Result from knowledge synchronization."""

    items_processed: int
    items_synced: int
    items_failed: int
    sync_time_ms: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IntelligenceCoreService:
    """Central intelligence core service implementing the tripartite knowledge architecture.

    Provides:
    - Unified knowledge management across Obsidian, Neo4j, and PostgreSQL
    - Semantic search with graph traversal
    - Automated knowledge graph construction
    - Real-time synchronization and conflict resolution
    - Cross-system relationship discovery
    """

    def __init__(
        self,
        obsidian_vault_path: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_REDACTED_SECRET: str,
        vector_db_service: VectorDatabaseService,
        nlp_service: IntelligenceNLPService,
        cache_service: CacheService | None = None,
    ):
        """Initialize the Intelligence Core Service.

        Args:
            obsidian_vault_path: Path to Obsidian vault
            neo4j_uri: Neo4j database URI
            neo4j_user: Neo4j username
            neo4j_REDACTED_SECRET: Neo4j REDACTED_SECRET
            vector_db_service: Vector database service instance
            nlp_service: NLP service instance
            cache_service: Optional cache service
        """
        self.obsidian_vault_path = Path(obsidian_vault_path)
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_REDACTED_SECRET = neo4j_REDACTED_SECRET

        # Service dependencies
        self.vector_db = vector_db_service
        self.nlp_service = nlp_service
        self.cache_service = cache_service

        # Database connections
        self.neo4j_driver: AsyncDriver | None = None
        self.vault: Vault | None = None

        # Processing state
        self._sync_in_progress = False
        self._last_sync_time: datetime | None = None

        # Performance tracking
        self._stats = {
            "knowledge_items": 0,
            "entities_extracted": 0,
            "relationships_created": 0,
            "queries_processed": 0,
            "sync_operations": 0,
            "cache_hits": 0,
            "processing_time_total_ms": 0.0,
        }

        # File watchers and sync tracking
        self._file_watchers: dict[str, datetime] = {}
        self._sync_queue: set[str] = set()

    async def initialize(self) -> bool:
        """Initialize all knowledge core components.

        Returns:
            bool: Success status
        """
        try:
            logger.info("Initializing Intelligence Core Service...")

            # Initialize Obsidian vault
            await self._initialize_obsidian_vault()

            # Initialize Neo4j connection
            await self._initialize_neo4j()

            # Verify vector database connection
            if not await self._verify_vector_database():
                raise RuntimeError("Vector database verification failed")

            # Verify NLP service
            if not await self._verify_nlp_service():
                raise RuntimeError("NLP service verification failed")

            # Setup knowledge graph schema
            await self._setup_knowledge_graph_schema()

            # Perform initial synchronization
            await self._initial_knowledge_sync()

            logger.info("Intelligence Core Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Intelligence Core Service: {e}")
            return False

    async def _initialize_obsidian_vault(self) -> None:
        """Initialize connection to Obsidian vault."""
        try:
            if not self.obsidian_vault_path.exists():
                raise FileNotFoundError(
                    f"Obsidian vault not found: {self.obsidian_vault_path}",
                )

            # Initialize vault using obsidiantools
            self.vault = Vault(str(self.obsidian_vault_path))

            # Verify vault structure
            notes = list(self.vault.md_notes)
            logger.info(f"Connected to Obsidian vault with {len(notes)} notes")

        except Exception as e:
            logger.error(f"Failed to initialize Obsidian vault: {e}")
            raise

    async def _initialize_neo4j(self) -> None:
        """Initialize Neo4j database connection."""
        try:
            self.neo4j_driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_REDACTED_SECRET),
                encrypted=False,  # Set to True for production with SSL
            )

            # Test connection
            async with self.neo4j_driver.session() as session:
                result = await session.run("RETURN 1 as test")
                test_value = await result.single()
                if test_value["test"] != 1:
                    raise RuntimeError("Neo4j connection test failed")

            logger.info("Connected to Neo4j successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Neo4j: {e}")
            raise

    async def _verify_vector_database(self) -> bool:
        """Verify vector database is operational."""
        try:
            health = await self.vector_db.health_check()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Vector database verification failed: {e}")
            return False

    async def _verify_nlp_service(self) -> bool:
        """Verify NLP service is operational."""
        try:
            health = await self.nlp_service.health_check()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.error(f"NLP service verification failed: {e}")
            return False

    async def _setup_knowledge_graph_schema(self) -> None:
        """Setup Neo4j schema for knowledge graph."""
        try:
            async with self.neo4j_driver.session() as session:
                # Create constraints and indexes
                schema_queries = [
                    # Node constraints
                    "CREATE CONSTRAINT knowledge_item_id IF NOT EXISTS FOR (k:KnowledgeItem) REQUIRE k.id IS UNIQUE",
                    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                    "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
                    # Indexes for performance
                    "CREATE INDEX knowledge_item_source IF NOT EXISTS FOR (k:KnowledgeItem) ON (k.source_type)",
                    "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
                    "CREATE INDEX entity_confidence IF NOT EXISTS FOR (e:Entity) ON (e.confidence)",
                    "CREATE INDEX concept_category IF NOT EXISTS FOR (c:Concept) ON (c.category)",
                    # Full-text search indexes
                    "CREATE FULLTEXT INDEX knowledge_content IF NOT EXISTS FOR (k:KnowledgeItem) ON EACH [k.title, k.content]",
                    "CREATE FULLTEXT INDEX entity_text IF NOT EXISTS FOR (e:Entity) ON EACH [e.text, e.context]",
                ]

                for query in schema_queries:
                    try:
                        await session.run(query)
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Schema setup warning: {e}")

                logger.info("Knowledge graph schema setup complete")

        except Exception as e:
            logger.error(f"Error setting up knowledge graph schema: {e}")
            raise

    async def _initial_knowledge_sync(self) -> None:
        """Perform initial synchronization of knowledge sources."""
        try:
            logger.info("Starting initial knowledge synchronization...")

            # Sync Obsidian vault
            await self._sync_obsidian_vault()

            # Update statistics
            self._last_sync_time = datetime.now(UTC)
            self._stats["sync_operations"] += 1

            logger.info("Initial knowledge synchronization complete")

        except Exception as e:
            logger.error(f"Error during initial sync: {e}")
            raise

    async def add_knowledge_item(
        self,
        content: str,
        title: str,
        source_type: KnowledgeSourceType,
        source_path: str,
        tags: list[str] | None = None,
        frontmatter: dict[str, Any] | None = None,
    ) -> KnowledgeItem:
        """Add a new knowledge item to the core.

        Args:
            content: Text content
            title: Item title
            source_type: Type of knowledge source
            source_path: Source file/URL path
            tags: Optional tags
            frontmatter: Optional metadata

        Returns:
            KnowledgeItem: Processed knowledge item
        """
        try:
            start_time = datetime.now()

            # Generate unique ID
            item_id = str(uuid.uuid4())

            # Process content with NLP
            analysis = await self.nlp_service.analyze_document(
                content,
                include_embeddings=True,
                include_topics=True,
                cache_key=f"analysis:{hashlib.sha256(content.encode()).hexdigest()}",
            )

            # Create knowledge item
            knowledge_item = KnowledgeItem(
                id=item_id,
                title=title,
                content=content,
                source_type=source_type,
                source_path=source_path,
                tags=tags or [],
                frontmatter=frontmatter or {},
                entities=analysis.entities,
                relationships=analysis.relationships,
                semantic_embedding=(
                    analysis.semantic_embedding.tobytes()
                    if analysis.semantic_embedding.size > 0
                    else None
                ),
            )

            # Store in all systems
            await self._store_knowledge_item(knowledge_item, analysis)

            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._stats["knowledge_items"] += 1
            self._stats["entities_extracted"] += len(analysis.entities)
            self._stats["relationships_created"] += len(analysis.relationships)
            self._stats["processing_time_total_ms"] += processing_time

            logger.info(
                f"Added knowledge item '{title}' with {len(analysis.entities)} entities and {len(analysis.relationships)} relationships",
            )
            return knowledge_item

        except Exception as e:
            logger.error(f"Error adding knowledge item: {e}")
            raise

    async def _store_knowledge_item(
        self,
        item: KnowledgeItem,
        analysis: DocumentAnalysis,
    ) -> None:
        """Store knowledge item across all storage systems."""
        try:
            # Store in vector database
            if analysis.semantic_embedding.size > 0:
                vector_result = await self.vector_db.insert_document_vector(
                    content_id=item.id,
                    content=item.content,
                    embedding=analysis.semantic_embedding,
                    vector_type=VectorType.DOCUMENT_EMBEDDING,
                    source=item.source_type.value,
                    metadata={
                        "title": item.title,
                        "source_path": item.source_path,
                        "tags": item.tags,
                        "frontmatter": item.frontmatter,
                    },
                )

                if not vector_result.success:
                    logger.warning(
                        f"Failed to store vector for item {item.id}: {
                            vector_result.error
                        }",
                    )

            # Store entities in vector database
            for entity in analysis.entities:
                if entity.semantic_embedding is not None:
                    await self.vector_db.insert_entity_vector(
                        entity_text=entity.text,
                        entity_type=entity.entity_type.value,
                        embedding=entity.semantic_embedding,
                        confidence=entity.confidence,
                        source_document_id=item.id,
                        context_window=(
                            entity.mentions[0].context_window
                            if entity.mentions
                            else None
                        ),
                        metadata={
                            "source_path": item.source_path,
                            "properties": entity.properties,
                        },
                    )

            # Store in Neo4j knowledge graph
            await self._store_in_knowledge_graph(item, analysis)

        except Exception as e:
            logger.error(f"Error storing knowledge item: {e}")
            raise

    async def _store_in_knowledge_graph(
        self,
        item: KnowledgeItem,
        analysis: DocumentAnalysis,
    ) -> None:
        """Store knowledge item and relationships in Neo4j."""
        try:
            async with self.neo4j_driver.session() as session:
                # Create knowledge item node
                await session.run(
                    """
                    MERGE (k:KnowledgeItem {id: $id})
                    SET k.title = $title,
                        k.content = $content,
                        k.source_type = $source_type,
                        k.source_path = $source_path,
                        k.tags = $tags,
                        k.created_at = $created_at,
                        k.updated_at = $updated_at
                """,
                    {
                        "id": item.id,
                        "title": item.title,
                        "content": item.content,
                        "source_type": item.source_type.value,
                        "source_path": item.source_path,
                        "tags": item.tags,
                        "created_at": item.created_at.isoformat(),
                        "updated_at": item.updated_at.isoformat(),
                    },
                )

                # Create entity nodes and relationships
                for entity in analysis.entities:
                    entity_id = f"entity_{
                        hashlib.sha256(
                            f'{entity.text}_{entity.entity_type.value}'.encode()
                        ).hexdigest()
                    }"

                    # Create entity node
                    await session.run(
                        """
                        MERGE (e:Entity {id: $entity_id})
                        SET e.text = $text,
                            e.entity_type = $entity_type,
                            e.confidence = $confidence,
                            e.properties = $properties
                    """,
                        {
                            "entity_id": entity_id,
                            "text": entity.text,
                            "entity_type": entity.entity_type.value,
                            "confidence": entity.confidence,
                            "properties": json.dumps(entity.properties),
                        },
                    )

                    # Connect entity to knowledge item
                    await session.run(
                        """
                        MATCH (k:KnowledgeItem {id: $item_id})
                        MATCH (e:Entity {id: $entity_id})
                        MERGE (k)-[:CONTAINS_ENTITY]->(e)
                    """,
                        {"item_id": item.id, "entity_id": entity_id},
                    )

                # Create relationship edges
                for rel in analysis.relationships:
                    await session.run(
                        """
                        MATCH (e1:Entity {text: $subject})
                        MATCH (e2:Entity {text: $object})
                        MERGE (e1)-[r:RELATED_TO {type: $relation_type}]->(e2)
                        SET r.confidence = $confidence,
                            r.source_sentence = $source_sentence,
                            r.context = $context
                    """,
                        {
                            "subject": rel.subject_entity,
                            "object": rel.object_entity,
                            "relation_type": rel.relation_type.value,
                            "confidence": rel.confidence,
                            "source_sentence": rel.source_sentence,
                            "context": rel.context,
                        },
                    )

                logger.debug(
                    f"Stored knowledge item {item.id} in Neo4j with {len(analysis.entities)} entities",
                )

        except Exception as e:
            logger.error(f"Error storing in knowledge graph: {e}")
            raise

    async def query_knowledge(self, query: KnowledgeQuery) -> KnowledgeQueryResult:
        """Query knowledge across all storage systems.

        Args:
            query: Knowledge query specification

        Returns:
            KnowledgeQueryResult: Query results
        """
        start_time = datetime.now()

        try:
            # Check cache first
            if self.cache_service:
                cache_key = f"knowledge_query:{
                    hashlib.sha256(
                        json.dumps(query.__dict__, sort_keys=True).encode()
                    ).hexdigest()
                }"
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    self._stats["cache_hits"] += 1
                    return KnowledgeQueryResult(**cached_result)

            # Generate query embedding
            query_embeddings = await self.nlp_service.generate_embeddings(
                [query.query_text],
            )
            if query_embeddings.size == 0:
                raise ValueError("Failed to generate query embedding")

            query_embedding = query_embeddings[0]

            # Perform searches based on query type
            if query.query_type == "semantic":
                results = await self._semantic_search(query, query_embedding)
            elif query.query_type == "graph":
                results = await self._graph_search(query)
            elif query.query_type == "hybrid":
                results = await self._hybrid_search(query, query_embedding)
            else:
                raise ValueError(f"Unknown query type: {query.query_type}")

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Create result
            query_result = KnowledgeQueryResult(
                items=results,
                total_found=len(results),
                query_time_ms=processing_time,
                sources_searched=["vector_db", "neo4j", "obsidian"],
            )

            # Cache result
            if self.cache_service and cache_key:
                cache_data = {
                    **query_result.__dict__,
                    "items": [self._serialize_knowledge_item(item) for item in results],
                }
                await self.cache_service.set(cache_key, cache_data, ttl=1800)

            # Update statistics
            self._stats["queries_processed"] += 1
            self._stats["processing_time_total_ms"] += processing_time

            logger.debug(
                f"Knowledge query returned {len(results)} results in {
                    processing_time:.2f}ms",
            )
            return query_result

        except Exception as e:
            logger.error(f"Error querying knowledge: {e}")
            raise

    async def _semantic_search(
        self,
        query: KnowledgeQuery,
        query_embedding,
    ) -> list[KnowledgeItem]:
        """Perform semantic search using vector database."""
        try:
            # Search documents
            vector_results = await self.vector_db.semantic_search(
                query_embedding=query_embedding,
                limit=query.limit,
                similarity_threshold=query.similarity_threshold,
            )

            # Convert to knowledge items
            items = []
            for result in vector_results:
                item = await self._load_knowledge_item_by_id(
                    result.metadata.get("content_id"),
                )
                if item:
                    items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def _graph_search(self, query: KnowledgeQuery) -> list[KnowledgeItem]:
        """Perform graph-based search using Neo4j."""
        try:
            async with self.neo4j_driver.session() as session:
                # Full-text search on knowledge items
                result = await session.run(
                    """
                    CALL db.index.fulltext.queryNodes('knowledge_content', $query_text)
                    YIELD node, score
                    RETURN node.id as id, score
                    ORDER BY score DESC
                    LIMIT $limit
                """,
                    {"query_text": query.query_text, "limit": query.limit},
                )

                # Load knowledge items
                items = []
                async for record in result:
                    item = await self._load_knowledge_item_by_id(record["id"])
                    if item:
                        items.append(item)

                return items

        except Exception as e:
            logger.error(f"Error in graph search: {e}")
            return []

    async def _hybrid_search(
        self,
        query: KnowledgeQuery,
        query_embedding,
    ) -> list[KnowledgeItem]:
        """Perform hybrid search combining semantic and graph approaches."""
        try:
            # Run both searches in parallel
            semantic_task = self._semantic_search(query, query_embedding)
            graph_task = self._graph_search(query)

            semantic_results, graph_results = await asyncio.gather(
                semantic_task,
                graph_task,
                return_exceptions=True,
            )

            # Handle exceptions
            if isinstance(semantic_results, Exception):
                semantic_results = []
            if isinstance(graph_results, Exception):
                graph_results = []

            # Merge and deduplicate results
            seen_ids = set()
            merged_results = []

            # Prioritize semantic results (typically more relevant)
            for item in semantic_results:
                if item.id not in seen_ids:
                    merged_results.append(item)
                    seen_ids.add(item.id)

            # Add graph results
            for item in graph_results:
                if item.id not in seen_ids and len(merged_results) < query.limit:
                    merged_results.append(item)
                    seen_ids.add(item.id)

            return merged_results[: query.limit]

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    async def _load_knowledge_item_by_id(self, item_id: str) -> KnowledgeItem | None:
        """Load a knowledge item by ID from Neo4j."""
        try:
            async with self.neo4j_driver.session() as session:
                result = await session.run(
                    """
                    MATCH (k:KnowledgeItem {id: $id})
                    RETURN k
                """,
                    {"id": item_id},
                )

                record = await result.single()
                if not record:
                    return None

                node = record["k"]

                # Create knowledge item (simplified - would need to load
                # entities/relationships)
                return KnowledgeItem(
                    id=node["id"],
                    title=node["title"],
                    content=node["content"],
                    source_type=KnowledgeSourceType(node["source_type"]),
                    source_path=node["source_path"],
                    tags=node.get("tags", []),
                    frontmatter={},  # Would need to load from metadata
                    created_at=(
                        datetime.fromisoformat(node["created_at"])
                        if node.get("created_at")
                        else datetime.now(UTC)
                    ),
                    updated_at=(
                        datetime.fromisoformat(node["updated_at"])
                        if node.get("updated_at")
                        else datetime.now(UTC)
                    ),
                )

        except Exception as e:
            logger.error(f"Error loading knowledge item {item_id}: {e}")
            return None

    async def _sync_obsidian_vault(self) -> SyncResult:
        """Synchronize Obsidian vault with knowledge core."""
        start_time = datetime.now()
        sync_stats = {"processed": 0, "synced": 0, "failed": 0, "errors": []}

        try:
            if not self.vault:
                raise ValueError("Obsidian vault not initialized")

            # Get all markdown notes
            notes = list(self.vault.md_notes)

            for note in notes:
                try:
                    sync_stats["processed"] += 1

                    # Parse note content and frontmatter
                    note_path = Path(note.path)
                    with open(note_path, encoding="utf-8") as f:
                        post = frontmatter.load(f)

                    # Create knowledge item
                    await self.add_knowledge_item(
                        content=post.content,
                        title=post.metadata.get("title", note_path.stem),
                        source_type=KnowledgeSourceType.OBSIDIAN_NOTE,
                        source_path=str(note_path),
                        tags=post.metadata.get("tags", []),
                        frontmatter=post.metadata,
                    )

                    sync_stats["synced"] += 1

                except Exception as e:
                    sync_stats["failed"] += 1
                    sync_stats["errors"].append(f"Error processing {note.path}: {e}")
                    logger.warning(f"Failed to sync note {note.path}: {e}")

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return SyncResult(
                items_processed=sync_stats["processed"],
                items_synced=sync_stats["synced"],
                items_failed=sync_stats["failed"],
                sync_time_ms=processing_time,
                errors=sync_stats["errors"],
            )

        except Exception as e:
            logger.error(f"Error syncing Obsidian vault: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return SyncResult(
                items_processed=0,
                items_synced=0,
                items_failed=1,
                sync_time_ms=processing_time,
                errors=[str(e)],
            )

    def _serialize_knowledge_item(self, item: KnowledgeItem) -> dict[str, Any]:
        """Serialize knowledge item for caching."""
        return {
            **item.__dict__,
            "source_type": item.source_type.value,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "entities": [self._serialize_entity(e) for e in item.entities],
            "relationships": [
                self._serialize_relationship(r) for r in item.relationships
            ],
            "semantic_embedding": (
                item.semantic_embedding.hex() if item.semantic_embedding else None
            ),
        }

    def _serialize_entity(self, entity: ExtractedEntity) -> dict[str, Any]:
        """Serialize entity for caching."""
        return {
            **entity.__dict__,
            "entity_type": entity.entity_type.value,
            "semantic_embedding": (
                entity.semantic_embedding.tolist()
                if entity.semantic_embedding is not None
                else None
            ),
        }

    def _serialize_relationship(self, rel: ExtractedRelationship) -> dict[str, Any]:
        """Serialize relationship for caching."""
        return {**rel.__dict__, "relation_type": rel.relation_type.value}

    async def get_service_stats(self) -> dict[str, Any]:
        """Get comprehensive service statistics."""
        try:
            # Get stats from dependent services
            vector_stats = await self.vector_db.get_database_stats()
            nlp_stats = await self.nlp_service.get_service_stats()

            # Get Neo4j stats
            neo4j_stats = {}
            try:
                async with self.neo4j_driver.session() as session:
                    result = await session.run(
                        """
                        MATCH (k:KnowledgeItem) RETURN count(k) as knowledge_items
                    """,
                    )
                    record = await result.single()
                    neo4j_stats["knowledge_items"] = (
                        record["knowledge_items"] if record else 0
                    )

                    result = await session.run(
                        """
                        MATCH (e:Entity) RETURN count(e) as entities
                    """,
                    )
                    record = await result.single()
                    neo4j_stats["entities"] = record["entities"] if record else 0

                    result = await session.run(
                        """
                        MATCH ()-[r:RELATED_TO]->() RETURN count(r) as relationships
                    """,
                    )
                    record = await result.single()
                    neo4j_stats["relationships"] = (
                        record["relationships"] if record else 0
                    )
            except Exception as e:
                neo4j_stats = {"error": str(e)}

            return {
                "intelligence_core": self._stats,
                "last_sync": (
                    self._last_sync_time.isoformat() if self._last_sync_time else None
                ),
                "sync_in_progress": self._sync_in_progress,
                "obsidian_vault_path": str(self.obsidian_vault_path),
                "vector_database": vector_stats,
                "nlp_service": nlp_stats,
                "knowledge_graph": neo4j_stats,
            }

        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check for the intelligence core."""
        try:
            # Check all components
            checks = {
                "obsidian_vault": self.vault is not None,
                "neo4j_connection": False,
                "vector_database": False,
                "nlp_service": False,
            }

            # Test Neo4j
            try:
                async with self.neo4j_driver.session() as session:
                    result = await session.run("RETURN 1 as test")
                    test_record = await result.single()
                    checks["neo4j_connection"] = test_record["test"] == 1
            except Exception:
                pass

            # Test vector database
            vector_health = await self.vector_db.health_check()
            checks["vector_database"] = vector_health.get("status") == "healthy"

            # Test NLP service
            nlp_health = await self.nlp_service.health_check()
            checks["nlp_service"] = nlp_health.get("status") == "healthy"

            # Overall status
            all_healthy = all(checks.values())

            return {
                "status": "healthy" if all_healthy else "degraded",
                "components": checks,
                "performance_stats": self._stats,
                "vault_notes": len(list(self.vault.md_notes)) if self.vault else 0,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "components": {
                    "obsidian_vault": False,
                    "neo4j_connection": False,
                    "vector_database": False,
                    "nlp_service": False,
                },
            }

    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        try:
            if self.neo4j_driver:
                await self.neo4j_driver.close()
                logger.info("Neo4j driver closed")

            if self.vector_db:
                await self.vector_db.close()
                logger.info("Vector database connection closed")

        except Exception as e:
            logger.error(f"Error closing intelligence core: {e}")


# Singleton instance
_intelligence_core_service: IntelligenceCoreService | None = None


async def get_intelligence_core_service(
    obsidian_vault_path: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_REDACTED_SECRET: str,
    postgres_url: str,
    cache_service: CacheService | None = None,
) -> IntelligenceCoreService:
    """Get or create Intelligence Core service singleton.

    Args:
        obsidian_vault_path: Path to Obsidian vault
        neo4j_uri: Neo4j database URI
        neo4j_user: Neo4j username
        neo4j_REDACTED_SECRET: Neo4j REDACTED_SECRET
        postgres_url: PostgreSQL connection URL
        cache_service: Optional cache service

    Returns:
        IntelligenceCoreService: Initialized service instance
    """
    global _intelligence_core_service

    if _intelligence_core_service is None:
        # Initialize dependencies
        vector_db = await get_vector_database_service(postgres_url, cache_service)
        nlp_service = await get_intelligence_nlp_service(cache_service)

        # Create core service
        _intelligence_core_service = IntelligenceCoreService(
            obsidian_vault_path=obsidian_vault_path,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_REDACTED_SECRET=neo4j_REDACTED_SECRET,
            vector_db_service=vector_db,
            nlp_service=nlp_service,
            cache_service=cache_service,
        )

        await _intelligence_core_service.initialize()

    return _intelligence_core_service
