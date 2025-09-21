"""Vector Database Service

Provides vector storage and similarity search capabilities using PostgreSQL with pgvector.
This service is designed for future integration when pgvector extension is available.
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VectorMatch:
    """Represents a vector similarity match result."""

    id: str
    vector: np.ndarray
    similarity: float
    metadata: dict[str, Any]


class VectorService:
    """Vector database service for future pgvector integration.

    Currently provides a foundation for vector operations that can be
    extended when PostgreSQL with pgvector is available.
    """

    def __init__(self, dimension: int = 384):
        """Initialize vector service.

        Args:
            dimension: Vector embedding dimension
        """
        self.dimension = dimension
        self.vectors = {}  # In-memory storage for now
        self.metadata = {}

    async def store_vector(
        self,
        id: str,
        vector: np.ndarray,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store a vector with associated metadata.

        Args:
            id: Unique identifier for the vector
            vector: Vector embedding
            metadata: Optional metadata dictionary

        Returns:
            bool: True if successful
        """
        try:
            if len(vector) != self.dimension:
                raise ValueError(
                    f"Vector dimension {len(vector)} doesn't match expected {
                        self.dimension
                    }",
                )

            self.vectors[id] = vector.copy()
            self.metadata[id] = metadata or {}

            logger.debug(f"Stored vector {id} with dimension {len(vector)}")
            return True

        except Exception as e:
            logger.error(f"Error storing vector {id}: {e}")
            return False

    async def get_vector(self, id: str) -> tuple[np.ndarray, dict[str, Any]] | None:
        """Retrieve a vector and its metadata by ID.

        Args:
            id: Vector identifier

        Returns:
            Tuple of (vector, metadata) or None if not found
        """
        if id in self.vectors:
            return self.vectors[id], self.metadata.get(id, {})
        return None

    async def similarity_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[VectorMatch]:
        """Find vectors similar to the query vector.

        Args:
            query_vector: Vector to search for
            top_k: Number of top results
            min_similarity: Minimum similarity threshold

        Returns:
            List of vector matches
        """
        try:
            if len(query_vector) != self.dimension:
                raise ValueError(
                    f"Query vector dimension {
                        len(query_vector)
                    } doesn't match expected {self.dimension}",
                )

            if not self.vectors:
                return []

            # Calculate cosine similarities
            similarities = []
            for vec_id, stored_vector in self.vectors.items():
                # Cosine similarity
                dot_product = np.dot(query_vector, stored_vector)
                norms = np.linalg.norm(query_vector) * np.linalg.norm(stored_vector)
                similarity = dot_product / norms if norms > 0 else 0.0

                if similarity >= min_similarity:
                    similarities.append((vec_id, similarity))

            # Sort by similarity and take top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_results = similarities[:top_k]

            # Create VectorMatch objects
            matches = []
            for vec_id, similarity in top_results:
                matches.append(
                    VectorMatch(
                        id=vec_id,
                        vector=self.vectors[vec_id],
                        similarity=similarity,
                        metadata=self.metadata.get(vec_id, {}),
                    ),
                )

            return matches

        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

    async def delete_vector(self, id: str) -> bool:
        """Delete a vector by ID.

        Args:
            id: Vector identifier

        Returns:
            bool: True if deleted, False if not found
        """
        if id in self.vectors:
            del self.vectors[id]
            if id in self.metadata:
                del self.metadata[id]
            logger.debug(f"Deleted vector {id}")
            return True
        return False

    async def get_statistics(self) -> dict[str, Any]:
        """Get vector database statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "memory_usage_mb": self._estimate_memory_usage(),
            "status": "in_memory",  # Will change to "pgvector" when integrated
        }

    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        if not self.vectors:
            return 0.0

        # Each vector is float64 * dimension * 8 bytes
        vector_size = self.dimension * 8
        total_bytes = len(self.vectors) * vector_size
        return total_bytes / (1024 * 1024)  # Convert to MB

    async def health_check(self) -> dict[str, Any]:
        """Check vector service health."""
        return {
            "status": "healthy",
            "type": "in_memory",
            "vectors_stored": len(self.vectors),
            "dimension": self.dimension,
            "memory_usage_mb": self._estimate_memory_usage(),
        }


# Singleton instance
_vector_service = None


def get_vector_service() -> VectorService:
    """Get or create vector service singleton."""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
