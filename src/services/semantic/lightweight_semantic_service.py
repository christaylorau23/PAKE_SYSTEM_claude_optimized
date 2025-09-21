"""Lightweight Semantic Search Service

Provides efficient semantic search using TF-IDF vectorization and cosine similarity.
This implementation avoids heavy ML dependencies while providing robust semantic capabilities.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class SemanticMatch:
    """Represents a semantic match result."""

    text: str
    score: float
    metadata: dict[str, Any]
    id: str | None = None


@dataclass
class SemanticAnalytics:
    """Analytics for semantic search operations."""

    total_documents: int
    processing_time_ms: float
    top_keywords: list[str]
    semantic_clusters: int
    average_similarity: float


class LightweightSemanticService:
    """Lightweight semantic search service using TF-IDF and LSA.

    Provides semantic search capabilities without heavy transformer dependencies,
    making it fast and resource-efficient for production use.
    """

    def __init__(self, cache_dir: str = "./cache/semantic"):
        """Initialize the semantic search service.

        Args:
            cache_dir: Directory for caching models and data
        """
        self.cache_dir = cache_dir
        self.vectorizer = None
        self.lsa_model = None
        self.document_vectors = None
        self.documents = []
        self.document_metadata = []

        # Configuration
        self.max_features = 5000  # TF-IDF vocabulary size
        self.lsa_components = 100  # LSA dimensions
        self.min_similarity = 0.1  # Minimum similarity threshold

        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)

        # Try to load existing model
        self._load_model()

    def _load_model(self) -> bool:
        """Load existing vectorizer and LSA model from cache using secure serialization."""
        try:
            model_path = os.path.join(self.cache_dir, "semantic_model.secure")
            if os.path.exists(model_path):
                data = deserialize_from_file(model_path)
                self.vectorizer = data.get("vectorizer")
                self.lsa_model = data.get("lsa_model")
                self.document_vectors = data.get("document_vectors")
                self.documents = data.get("documents", [])
                self.document_metadata = data.get("metadata", [])

                logger.info(
                    f"Loaded semantic model with {len(self.documents)} documents",
                )
                return True
        except Exception as e:
            logger.warning(f"Could not load semantic model: {e}")

        return False

    def _save_model(self):
        """Save vectorizer and LSA model to cache using secure serialization."""
        try:
            model_path = os.path.join(self.cache_dir, "semantic_model.secure")
            data = {
                "vectorizer": self.vectorizer,
                "lsa_model": self.lsa_model,
                "document_vectors": self.document_vectors,
                "documents": self.documents,
                "metadata": self.document_metadata,
            }

            serialize_to_file(data, model_path)

            logger.info(f"Saved semantic model with {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Could not save semantic model: {e}")

    async def add_documents(self, documents: list[dict[str, Any]]) -> bool:
        """Add documents to the semantic index.

        Args:
            documents: List of documents with 'text' and optional metadata

        Returns:
            bool: True if successful
        """
        try:
            start_time = datetime.utcnow()

            # Extract text and metadata
            texts = []
            metadata = []

            for doc in documents:
                if isinstance(doc, dict):
                    text = doc.get("text", "") or doc.get("content", "")
                    if text.strip():
                        texts.append(text.strip())
                        metadata.append(
                            {
                                "id": doc.get("id"),
                                "title": doc.get("title"),
                                "source": doc.get("source"),
                                "url": doc.get("url"),
                                **{
                                    k: v
                                    for k, v in doc.items()
                                    if k not in ["text", "content"]
                                },
                            },
                        )
                elif isinstance(doc, str):
                    if doc.strip():
                        texts.append(doc.strip())
                        metadata.append({})

            if not texts:
                logger.warning("No valid text content found in documents")
                return False

            # Add to existing documents
            self.documents.extend(texts)
            self.document_metadata.extend(metadata)

            # Rebuild the semantic model
            await self._rebuild_model()

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"Added {len(texts)} documents to semantic index in {
                    processing_time:.2f}ms",
            )

            return True

        except Exception as e:
            logger.error(f"Error adding documents to semantic index: {e}")
            return False

    async def _rebuild_model(self):
        """Rebuild the TF-IDF and LSA models."""
        try:
            if not self.documents:
                return

            # Initialize TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                stop_words="english",
                ngram_range=(1, 2),  # Include bigrams
                min_df=1,
                max_df=0.95,
                lowercase=True,
                strip_accents="unicode",
            )

            # Fit and transform documents
            tfidf_matrix = self.vectorizer.fit_transform(self.documents)

            # Apply LSA for dimensionality reduction and semantic understanding
            self.lsa_model = TruncatedSVD(
                n_components=min(
                    self.lsa_components,
                    len(self.documents) - 1,
                    tfidf_matrix.shape[1] - 1,
                ),
                random_state=42,
            )

            # Create semantic vectors
            self.document_vectors = self.lsa_model.fit_transform(tfidf_matrix)

            # Save the model
            self._save_model()

            logger.info(
                f"Rebuilt semantic model: {len(self.documents)} docs, "
                f"{self.document_vectors.shape[1]} dimensions",
            )

        except Exception as e:
            logger.error(f"Error rebuilding semantic model: {e}")
            raise

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float | None = None,
    ) -> list[SemanticMatch]:
        """Perform semantic search against indexed documents.

        Args:
            query: Search query text
            top_k: Number of top results to return
            min_score: Minimum similarity score threshold

        Returns:
            List of semantic matches
        """
        try:
            if (
                not self.vectorizer
                or not self.lsa_model
                or self.document_vectors is None
            ):
                logger.warning("Semantic model not initialized")
                return []

            if not query.strip():
                return []

            min_score = min_score or self.min_similarity

            # Transform query using the fitted vectorizer
            query_tfidf = self.vectorizer.transform([query.strip()])
            query_vector = self.lsa_model.transform(query_tfidf)

            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, self.document_vectors)[0]

            # Get top results
            top_indices = np.argsort(similarities)[::-1][:top_k]

            matches = []
            for idx in top_indices:
                score = similarities[idx]
                if score >= min_score:
                    matches.append(
                        SemanticMatch(
                            text=self.documents[idx],
                            score=float(score),
                            metadata=self.document_metadata[idx],
                            id=self.document_metadata[idx].get("id"),
                        ),
                    )

            logger.info(f"Semantic search for '{query}': {len(matches)} matches found")
            return matches

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def find_similar_documents(
        self,
        document_text: str,
        top_k: int = 5,
    ) -> list[SemanticMatch]:
        """Find documents similar to the given document text.

        Args:
            document_text: Text to find similar documents for
            top_k: Number of similar documents to return

        Returns:
            List of similar documents
        """
        return await self.semantic_search(document_text, top_k=top_k, min_score=0.2)

    async def get_document_keywords(
        self,
        document_text: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Extract keywords from document using TF-IDF scores.

        Args:
            document_text: Text to extract keywords from
            top_k: Number of top keywords to return

        Returns:
            List of (keyword, score) tuples
        """
        try:
            if not self.vectorizer:
                return []

            # Transform document
            doc_tfidf = self.vectorizer.transform([document_text])

            # Get feature names and scores
            feature_names = self.vectorizer.get_feature_names_out()
            scores = doc_tfidf.toarray()[0]

            # Get top keywords
            top_indices = np.argsort(scores)[::-1][:top_k]
            keywords = [
                (feature_names[idx], float(scores[idx]))
                for idx in top_indices
                if scores[idx] > 0
            ]

            return keywords

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []

    async def cluster_documents(self, num_clusters: int = 5) -> dict[str, Any]:
        """Cluster documents using K-means on semantic vectors.

        Args:
            num_clusters: Number of clusters to create

        Returns:
            Clustering results with cluster assignments and centroids
        """
        try:
            if self.document_vectors is None or len(self.documents) < num_clusters:
                return {"clusters": [], "assignments": []}

            from sklearn.cluster import KMeans

            # Perform clustering
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            cluster_assignments = kmeans.fit_predict(self.document_vectors)

            # Organize results
            clusters = {}
            for idx, cluster_id in enumerate(cluster_assignments):
                if cluster_id not in clusters:
                    clusters[cluster_id] = []

                clusters[cluster_id].append(
                    {
                        "text": self.documents[idx],
                        "metadata": self.document_metadata[idx],
                        "index": idx,
                    },
                )

            # Get cluster keywords
            cluster_keywords = {}
            for cluster_id in clusters:
                cluster_docs = [doc["text"] for doc in clusters[cluster_id]]
                combined_text = " ".join(cluster_docs)
                keywords = await self.get_document_keywords(combined_text, top_k=5)
                cluster_keywords[cluster_id] = keywords

            return {
                "clusters": [
                    {
                        "id": cluster_id,
                        "documents": clusters[cluster_id],
                        "keywords": cluster_keywords[cluster_id],
                        "size": len(clusters[cluster_id]),
                    }
                    for cluster_id in sorted(clusters.keys())
                ],
                "assignments": cluster_assignments.tolist(),
                "num_clusters": num_clusters,
            }

        except Exception as e:
            logger.error(f"Error clustering documents: {e}")
            return {"clusters": [], "assignments": []}

    async def get_analytics(self) -> SemanticAnalytics:
        """Get analytics about the semantic search index.

        Returns:
            Analytics object with index statistics
        """
        try:
            start_time = datetime.utcnow()

            total_docs = len(self.documents)

            # Get top keywords across all documents
            top_keywords = []
            if self.vectorizer:
                feature_names = self.vectorizer.get_feature_names_out()
                # Get average TF-IDF scores
                if self.document_vectors is not None and len(self.documents) > 0:
                    # Transform all documents to get TF-IDF matrix
                    tfidf_matrix = self.vectorizer.transform(self.documents)
                    avg_scores = np.mean(tfidf_matrix.toarray(), axis=0)
                    top_indices = np.argsort(avg_scores)[::-1][:10]
                    top_keywords = [
                        feature_names[idx] for idx in top_indices if avg_scores[idx] > 0
                    ]

            # Calculate average similarity (sample-based for performance)
            avg_similarity = 0.0
            if self.document_vectors is not None and len(self.documents) > 1:
                # Sample a few documents for average similarity calculation
                sample_size = min(10, len(self.documents))
                sample_indices = np.random.choice(
                    len(self.documents),
                    sample_size,
                    replace=False,
                )
                similarities = []

                for i in range(sample_size):
                    for j in range(i + 1, sample_size):
                        sim = cosine_similarity(
                            self.document_vectors[sample_indices[i]].reshape(1, -1),
                            self.document_vectors[sample_indices[j]].reshape(1, -1),
                        )[0][0]
                        similarities.append(sim)

                avg_similarity = float(np.mean(similarities)) if similarities else 0.0

            # Estimate semantic clusters
            semantic_clusters = (
                min(max(total_docs // 10, 1), 20) if total_docs > 0 else 0
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return SemanticAnalytics(
                total_documents=total_docs,
                processing_time_ms=processing_time,
                top_keywords=top_keywords,
                semantic_clusters=semantic_clusters,
                average_similarity=avg_similarity,
            )

        except Exception as e:
            logger.error(f"Error getting semantic analytics: {e}")
            return SemanticAnalytics(
                total_documents=len(self.documents),
                processing_time_ms=0.0,
                top_keywords=[],
                semantic_clusters=0,
                average_similarity=0.0,
            )

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the semantic search service."""
        try:
            is_healthy = (
                self.vectorizer is not None
                and self.lsa_model is not None
                and len(self.documents) > 0
            )

            return {
                "status": "healthy" if is_healthy else "not_ready",
                "documents_indexed": len(self.documents),
                "model_loaded": self.vectorizer is not None,
                "lsa_dimensions": (
                    self.document_vectors.shape[1]
                    if self.document_vectors is not None
                    else 0
                ),
                "cache_dir": self.cache_dir,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "documents_indexed": 0,
                "model_loaded": False,
            }


# Singleton instance
_semantic_service = None


def get_semantic_service() -> LightweightSemanticService:
    """Get or create semantic service singleton."""
    global _semantic_service
    if _semantic_service is None:
        _semantic_service = LightweightSemanticService()
    return _semantic_service
