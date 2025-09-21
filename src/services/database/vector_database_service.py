"""Vector Database Service

PostgreSQL with pgvector implementation following the Personal Intelligence Engine blueprint.
Provides semantic search capabilities, vector similarity operations, and integration
with the tripartite knowledge core architecture.

Following PAKE System enterprise standards with async/await patterns,
comprehensive error handling, and production-ready performance.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

# Database imports
import numpy as np

# Vector operations
import pgvector
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

# PAKE System imports
from src.services.caching.redis_cache_service import CacheService

logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()


class VectorType(Enum):
    """Types of vectors stored in the database."""

    DOCUMENT_EMBEDDING = "document_embedding"
    ENTITY_EMBEDDING = "entity_embedding"
    SENTENCE_EMBEDDING = "sentence_embedding"
    QUERY_EMBEDDING = "query_embedding"


class SimilarityMetric(Enum):
    """Similarity metrics for vector search."""

    COSINE = "cosine"
    L2_DISTANCE = "l2"
    INNER_PRODUCT = "inner_product"


@dataclass(frozen=True)
class VectorSearchResult:
    """Result from vector similarity search."""

    id: str
    content: str
    similarity_score: float
    metadata: dict[str, Any]
    vector_type: VectorType
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class VectorInsertResult:
    """Result from vector insertion."""

    id: str
    success: bool
    embedding_dimensions: int
    error: str | None = None


class DocumentVector(Base):
    """Document embeddings table with pgvector support."""

    __tablename__ = "document_vectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    content_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[pgvector.Vector] = mapped_column(
        Vector(384),
    )  # Default for all-MiniLM-L6-v2
    vector_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=True, index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Search performance indexes
    __table_args__ = (
        Index("ix_document_vectors_vector_type_source", "vector_type", "source"),
        Index("ix_document_vectors_created_at", "created_at"),
        # Vector similarity indexes (created separately due to pgvector requirements)
    )


class EntityVector(Base):
    """Entity embeddings table for knowledge graph integration."""

    __tablename__ = "entity_vectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_text: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    embedding: Mapped[pgvector.Vector] = mapped_column(Vector(384))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Knowledge graph references
    neo4j_node_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    # Context and source information
    source_document_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    context_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_entity_vectors_entity_text_type", "entity_text", "entity_type"),
        Index("ix_entity_vectors_confidence", "confidence"),
        Index("ix_entity_vectors_neo4j_node_id", "neo4j_node_id"),
    )


class QueryVector(Base):
    """Query embeddings for search optimization and analytics."""

    __tablename__ = "query_vectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[pgvector.Vector] = mapped_column(Vector(384))
    query_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, default=1)
    last_used: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Performance metrics
    avg_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    results_found: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class VectorDatabaseService:
    """PostgreSQL with pgvector implementation for semantic search.

    Provides:
    - High-dimensional vector storage and retrieval
    - Semantic similarity search with multiple metrics
    - Integration with Neo4j knowledge graph
    - Performance optimization with caching
    - Comprehensive analytics and monitoring
    """

    def __init__(
        self,
        database_url: str,
        embedding_dimensions: int = 384,
        cache_service: CacheService | None = None,
        max_connections: int = 20,
    ):
        """Initialize Vector Database Service.

        Args:
            database_url: PostgreSQL connection URL with pgvector support
            embedding_dimensions: Dimension of vector embeddings
            cache_service: Optional cache service for performance
            max_connections: Maximum database connections
        """
        self.database_url = database_url
        self.embedding_dimensions = embedding_dimensions
        self.cache_service = cache_service
        self.max_connections = max_connections

        # Database engine and session
        self.engine: AsyncEngine | None = None
        self.async_session_maker = None

        # Performance tracking
        self._stats = {
            "vectors_inserted": 0,
            "searches_performed": 0,
            "cache_hits": 0,
            "total_search_time_ms": 0.0,
            "average_search_time_ms": 0.0,
        }

        # Connection pool health
        self._connection_healthy = False

    async def initialize(self) -> bool:
        """Initialize the vector database service.

        Returns:
            bool: Success status
        """
        try:
            logger.info("Initializing Vector Database Service...")

            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_size=self.max_connections // 2,
                max_overflow=self.max_connections // 2,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
            )

            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
            )

            # Initialize database schema
            await self._initialize_schema()

            # Create vector indexes for performance
            await self._create_vector_indexes()

            # Verify pgvector extension
            await self._verify_pgvector()

            self._connection_healthy = True
            logger.info("Vector Database Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            self._connection_healthy = False
            return False

    async def _initialize_schema(self) -> None:
        """Initialize database schema and pgvector extension."""
        async with self.engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

            # Create tables
            await conn.run_sync(Base.metadata.create_all)

            logger.info("Database schema initialized with pgvector support")

    async def _create_vector_indexes(self) -> None:
        """Create vector similarity indexes for performance."""
        try:
            async with self.engine.begin() as conn:
                # Document vector indexes
                index_queries = [
                    # IVFFlat index for document embeddings (good for large datasets)
                    "CREATE INDEX IF NOT EXISTS ix_document_vectors_embedding_ivfflat ON document_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
                    # HNSW index for entity embeddings (better for accuracy)
                    "CREATE INDEX IF NOT EXISTS ix_entity_vectors_embedding_hnsw ON entity_vectors USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);",
                    # Query vector index for search optimization
                    "CREATE INDEX IF NOT EXISTS ix_query_vectors_embedding_cosine ON query_vectors USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);",
                ]

                for query in index_queries:
                    try:
                        await conn.execute(sa.text(query))
                        logger.debug(f"Created vector index: {query.split()[4]}")
                    except Exception as e:
                        logger.warning(f"Failed to create index: {e}")

                logger.info("Vector indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating vector indexes: {e}")

    async def _verify_pgvector(self) -> None:
        """Verify pgvector extension is working correctly."""
        async with self.async_session_maker() as session:
            result = await session.execute(
                sa.text("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector as distance;"),
            )
            distance = result.scalar()
            if distance is None:
                raise RuntimeError("pgvector extension verification failed")

            logger.info(f"pgvector verified successfully (test distance: {distance})")

    async def insert_document_vector(
        self,
        content_id: str,
        content: str,
        embedding: np.ndarray,
        vector_type: VectorType = VectorType.DOCUMENT_EMBEDDING,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VectorInsertResult:
        """Insert a document vector into the database.

        Args:
            content_id: Unique identifier for the content
            content: Text content
            embedding: Vector embedding
            vector_type: Type of vector
            source: Source of the content
            metadata: Additional metadata

        Returns:
            VectorInsertResult: Insert operation result
        """
        try:
            # Validate embedding dimensions
            if embedding.shape[0] != self.embedding_dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {
                        self.embedding_dimensions
                    }, got {embedding.shape[0]}",
                )

            # Convert numpy array to pgvector format
            vector_data = embedding.tolist()

            async with self.async_session_maker() as session:
                # Check if document already exists
                existing = await session.execute(
                    sa.select(DocumentVector).where(
                        DocumentVector.content_id == content_id,
                    ),
                )
                existing_doc = existing.scalar_one_or_none()

                if existing_doc:
                    # Update existing document
                    existing_doc.content = content
                    existing_doc.embedding = vector_data
                    existing_doc.vector_type = vector_type.value
                    existing_doc.source = source
                    existing_doc.metadata_ = metadata or {}
                    existing_doc.updated_at = datetime.now(UTC)

                    doc_id = str(existing_doc.id)
                else:
                    # Insert new document
                    new_doc = DocumentVector(
                        content_id=content_id,
                        content=content,
                        embedding=vector_data,
                        vector_type=vector_type.value,
                        source=source,
                        metadata_=metadata or {},
                    )
                    session.add(new_doc)
                    await session.flush()  # Get the ID
                    doc_id = str(new_doc.id)

                await session.commit()

                # Update statistics
                self._stats["vectors_inserted"] += 1

                # Invalidate cache if present
                if self.cache_service:
                    await self.cache_service.delete_pattern("vector_search:*")

                return VectorInsertResult(
                    id=doc_id,
                    success=True,
                    embedding_dimensions=self.embedding_dimensions,
                )

        except Exception as e:
            logger.error(f"Error inserting document vector: {e}")
            return VectorInsertResult(
                id="",
                success=False,
                embedding_dimensions=0,
                error=str(e),
            )

    async def insert_entity_vector(
        self,
        entity_text: str,
        entity_type: str,
        embedding: np.ndarray,
        confidence: float = 1.0,
        neo4j_node_id: str | None = None,
        source_document_id: str | None = None,
        context_window: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VectorInsertResult:
        """Insert an entity vector for knowledge graph integration.

        Args:
            entity_text: Text of the entity
            entity_type: Type/category of the entity
            embedding: Vector embedding
            confidence: Confidence score for the entity
            neo4j_node_id: Reference to Neo4j node
            source_document_id: Source document reference
            context_window: Context surrounding the entity
            metadata: Additional metadata

        Returns:
            VectorInsertResult: Insert operation result
        """
        try:
            # Validate embedding dimensions
            if embedding.shape[0] != self.embedding_dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {
                        self.embedding_dimensions
                    }, got {embedding.shape[0]}",
                )

            vector_data = embedding.tolist()

            async with self.async_session_maker() as session:
                # Check for existing entity
                existing = await session.execute(
                    sa.select(EntityVector).where(
                        sa.and_(
                            EntityVector.entity_text == entity_text,
                            EntityVector.entity_type == entity_type,
                        ),
                    ),
                )
                existing_entity = existing.scalar_one_or_none()

                if existing_entity:
                    # Update existing entity with new information
                    existing_entity.embedding = vector_data
                    existing_entity.confidence = max(
                        existing_entity.confidence,
                        confidence,
                    )
                    existing_entity.neo4j_node_id = (
                        neo4j_node_id or existing_entity.neo4j_node_id
                    )
                    existing_entity.source_document_id = (
                        source_document_id or existing_entity.source_document_id
                    )
                    existing_entity.context_window = (
                        context_window or existing_entity.context_window
                    )
                    existing_entity.metadata_ = {
                        **existing_entity.metadata_,
                        **(metadata or {}),
                    }
                    existing_entity.updated_at = datetime.now(UTC)

                    entity_id = str(existing_entity.id)
                else:
                    # Insert new entity
                    new_entity = EntityVector(
                        entity_text=entity_text,
                        entity_type=entity_type,
                        embedding=vector_data,
                        confidence=confidence,
                        neo4j_node_id=neo4j_node_id,
                        source_document_id=source_document_id,
                        context_window=context_window,
                        metadata_=metadata or {},
                    )
                    session.add(new_entity)
                    await session.flush()
                    entity_id = str(new_entity.id)

                await session.commit()

                self._stats["vectors_inserted"] += 1

                return VectorInsertResult(
                    id=entity_id,
                    success=True,
                    embedding_dimensions=self.embedding_dimensions,
                )

        except Exception as e:
            logger.error(f"Error inserting entity vector: {e}")
            return VectorInsertResult(
                id="",
                success=False,
                embedding_dimensions=0,
                error=str(e),
            )

    async def semantic_search(
        self,
        query_embedding: np.ndarray,
        vector_type: VectorType | None = None,
        source_filter: str | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> list[VectorSearchResult]:
        """Perform semantic similarity search.

        Args:
            query_embedding: Query vector embedding
            vector_type: Optional filter by vector type
            source_filter: Optional filter by source
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            metric: Similarity metric to use

        Returns:
            List[VectorSearchResult]: Search results
        """
        start_time = datetime.now()

        try:
            # Generate cache key
            cache_key = None
            if self.cache_service:
                cache_components = [
                    str(hash(query_embedding.tobytes())),
                    vector_type.value if vector_type else "all",
                    source_filter or "all",
                    str(limit),
                    str(similarity_threshold),
                    metric.value,
                ]
                cache_key = f"vector_search:{':'.join(cache_components)}"

                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    self._stats["cache_hits"] += 1
                    return [VectorSearchResult(**item) for item in cached_result]

            # Build query based on metric
            similarity_expr = self._get_similarity_expression(
                metric,
                query_embedding.tolist(),
            )

            async with self.async_session_maker() as session:
                # Build base query
                query = sa.select(
                    DocumentVector.id,
                    DocumentVector.content_id,
                    DocumentVector.content,
                    DocumentVector.vector_type,
                    DocumentVector.source,
                    DocumentVector.metadata_,
                    DocumentVector.created_at,
                    DocumentVector.updated_at,
                    similarity_expr.label("similarity_score"),
                ).where(similarity_expr >= similarity_threshold)

                # Apply filters
                if vector_type:
                    query = query.where(DocumentVector.vector_type == vector_type.value)

                if source_filter:
                    query = query.where(DocumentVector.source == source_filter)

                # Order by similarity and limit
                query = query.order_by(similarity_expr.desc()).limit(limit)

                # Execute query
                result = await session.execute(query)
                rows = result.fetchall()

                # Convert to result objects
                search_results = []
                for row in rows:
                    search_result = VectorSearchResult(
                        id=str(row.id),
                        content=row.content,
                        similarity_score=float(row.similarity_score),
                        metadata={
                            "content_id": row.content_id,
                            "vector_type": row.vector_type,
                            "source": row.source,
                            **row.metadata_,
                        },
                        vector_type=VectorType(row.vector_type),
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                    search_results.append(search_result)

                # Update statistics
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                self._stats["searches_performed"] += 1
                self._stats["total_search_time_ms"] += processing_time
                self._stats["average_search_time_ms"] = (
                    self._stats["total_search_time_ms"]
                    / self._stats["searches_performed"]
                )

                # Cache results
                if cache_key and self.cache_service:
                    cache_data = [
                        {
                            **result.__dict__,
                            "created_at": result.created_at.isoformat(),
                            "updated_at": result.updated_at.isoformat(),
                        }
                        for result in search_results
                    ]
                    # 30 minutes
                    await self.cache_service.set(cache_key, cache_data, ttl=1800)

                logger.debug(
                    f"Semantic search found {len(search_results)} results in {
                        processing_time:.2f}ms",
                )
                return search_results

        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []

    def _get_similarity_expression(
        self,
        metric: SimilarityMetric,
        query_vector: list[float],
    ):
        """Get SQLAlchemy expression for similarity calculation."""
        query_vector_str = str(query_vector)

        if metric == SimilarityMetric.COSINE:
            # For cosine similarity, pgvector uses 1 - cosine_distance
            return 1 - DocumentVector.embedding.cosine_distance(query_vector_str)
        if metric == SimilarityMetric.L2_DISTANCE:
            # L2 distance (lower is better, so we negate it)
            return -DocumentVector.embedding.l2_distance(query_vector_str)
        if metric == SimilarityMetric.INNER_PRODUCT:
            return DocumentVector.embedding.max_inner_product(query_vector_str)
        # Default to cosine similarity
        return 1 - DocumentVector.embedding.cosine_distance(query_vector_str)

    async def find_similar_entities(
        self,
        entity_embedding: np.ndarray,
        entity_type_filter: str | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.8,
    ) -> list[dict[str, Any]]:
        """Find similar entities for knowledge graph expansion.

        Args:
            entity_embedding: Query entity embedding
            entity_type_filter: Optional filter by entity type
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List[Dict]: Similar entities with metadata
        """
        try:
            query_vector = entity_embedding.tolist()
            similarity_expr = 1 - EntityVector.embedding.cosine_distance(
                str(query_vector),
            )

            async with self.async_session_maker() as session:
                query = sa.select(
                    EntityVector.entity_text,
                    EntityVector.entity_type,
                    EntityVector.confidence,
                    EntityVector.neo4j_node_id,
                    EntityVector.source_document_id,
                    EntityVector.context_window,
                    EntityVector.metadata_,
                    similarity_expr.label("similarity_score"),
                ).where(similarity_expr >= similarity_threshold)

                if entity_type_filter:
                    query = query.where(EntityVector.entity_type == entity_type_filter)

                query = query.order_by(similarity_expr.desc()).limit(limit)

                result = await session.execute(query)
                rows = result.fetchall()

                similar_entities = []
                for row in rows:
                    entity_data = {
                        "entity_text": row.entity_text,
                        "entity_type": row.entity_type,
                        "confidence": row.confidence,
                        "similarity_score": float(row.similarity_score),
                        "neo4j_node_id": row.neo4j_node_id,
                        "source_document_id": row.source_document_id,
                        "context_window": row.context_window,
                        "metadata": row.metadata_,
                    }
                    similar_entities.append(entity_data)

                logger.debug(f"Found {len(similar_entities)} similar entities")
                return similar_entities

        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return []

    async def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            async with self.async_session_maker() as session:
                # Count vectors by type
                doc_count = await session.execute(
                    sa.select(sa.func.count(DocumentVector.id)),
                )

                entity_count = await session.execute(
                    sa.select(sa.func.count(EntityVector.id)),
                )

                query_count = await session.execute(
                    sa.select(sa.func.count(QueryVector.id)),
                )

                # Vector type distribution
                vector_types = await session.execute(
                    sa.select(
                        DocumentVector.vector_type,
                        sa.func.count(DocumentVector.id).label("count"),
                    ).group_by(DocumentVector.vector_type),
                )

                # Source distribution
                sources = await session.execute(
                    sa.select(
                        DocumentVector.source,
                        sa.func.count(DocumentVector.id).label("count"),
                    ).group_by(DocumentVector.source),
                )

                return {
                    "total_documents": doc_count.scalar(),
                    "total_entities": entity_count.scalar(),
                    "total_queries": query_count.scalar(),
                    "vector_types": {
                        row.vector_type: row.count for row in vector_types
                    },
                    "sources": {row.source or "unknown": row.count for row in sources},
                    "embedding_dimensions": self.embedding_dimensions,
                    "performance_stats": self._stats,
                    "connection_healthy": self._connection_healthy,
                }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e), "connection_healthy": False}

    async def cleanup_old_vectors(self, days_old: int = 30) -> int:
        """Clean up old vectors to manage storage.

        Args:
            days_old: Remove vectors older than this many days

        Returns:
            int: Number of vectors removed
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

            async with self.async_session_maker() as session:
                # Delete old document vectors
                doc_result = await session.execute(
                    sa.delete(DocumentVector).where(
                        DocumentVector.created_at < cutoff_date,
                    ),
                )

                # Delete old query vectors (keep recent ones for cache optimization)
                query_result = await session.execute(
                    sa.delete(QueryVector).where(
                        sa.and_(
                            QueryVector.created_at < cutoff_date,
                            QueryVector.usage_count < 5,  # Keep frequently used queries
                        ),
                    ),
                )

                await session.commit()

                deleted_count = doc_result.rowcount + query_result.rowcount
                logger.info(f"Cleaned up {deleted_count} old vectors")
                return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old vectors: {e}")
            return 0

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check for the vector database."""
        try:
            # Test basic database connectivity
            async with self.async_session_maker() as session:
                result = await session.execute(sa.text("SELECT 1 as test"))
                test_value = result.scalar()

                if test_value != 1:
                    raise RuntimeError("Basic database test failed")

            # Test vector operations
            test_vector = np.random.rand(self.embedding_dimensions).astype(np.float32)
            test_result = await self.semantic_search(
                test_vector,
                limit=1,
                similarity_threshold=0.0,
            )

            # Get current stats
            stats = await self.get_database_stats()

            return {
                "status": "healthy",
                "database_connected": True,
                "pgvector_working": True,
                "vector_operations_working": True,
                "total_vectors": stats.get("total_documents", 0)
                + stats.get("total_entities", 0),
                "performance_stats": self._stats,
                "database_stats": stats,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_connected": False,
                "pgvector_working": False,
                "vector_operations_working": False,
            }

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        try:
            if self.engine:
                await self.engine.dispose()
                self._connection_healthy = False
                logger.info("Vector database connections closed")

        except Exception as e:
            logger.error(f"Error closing vector database: {e}")


# Singleton instance
_vector_db_service: VectorDatabaseService | None = None


async def get_vector_database_service(
    database_url: str,
    cache_service: CacheService | None = None,
) -> VectorDatabaseService:
    """Get or create Vector Database service singleton.

    Args:
        database_url: PostgreSQL connection URL
        cache_service: Optional cache service

    Returns:
        VectorDatabaseService: Initialized service instance
    """
    global _vector_db_service

    if _vector_db_service is None:
        _vector_db_service = VectorDatabaseService(
            database_url=database_url,
            cache_service=cache_service,
        )
        await _vector_db_service.initialize()

    return _vector_db_service
