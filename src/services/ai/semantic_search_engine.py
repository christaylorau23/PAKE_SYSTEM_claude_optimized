#!/usr/bin/env python3
"""PAKE System - Semantic Search and Similarity Engine
Phase 3 Sprint 5: Advanced AI integration with vector embeddings and semantic matching

Provides intelligent semantic search, content similarity analysis, vector embeddings,
and context-aware search capabilities for enhanced content discovery.
"""

import asyncio
import hashlib
import json
import logging
import math
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SimilarityMetric(Enum):
    """Similarity calculation methods"""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    JACCARD = "jaccard"
    SEMANTIC_HYBRID = "semantic_hybrid"


class SearchMode(Enum):
    """Search operation modes"""

    EXACT_MATCH = "exact_match"
    FUZZY_SEARCH = "fuzzy_search"
    SEMANTIC_SEARCH = "semantic_search"
    HYBRID_SEARCH = "hybrid_search"
    CONTEXTUAL_SEARCH = "contextual_search"


class RankingStrategy(Enum):
    """Result ranking strategies"""

    RELEVANCE_ONLY = "relevance_only"
    RECENCY_WEIGHTED = "recency_weighted"
    QUALITY_WEIGHTED = "quality_weighted"
    HYBRID_RANKING = "hybrid_ranking"
    PERSONALIZED = "personalized"


@dataclass(frozen=True)
class VectorEmbedding:
    """Immutable vector embedding representation"""

    content_id: str
    vector: tuple[float, ...] = field(default_factory=tuple)
    dimensionality: int = 0
    embedding_model: str = "tf_idf"
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array for calculations"""
        return np.array(self.vector)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "content_id": self.content_id,
            "vector": list(self.vector),
            "dimensionality": self.dimensionality,
            "embedding_model": self.embedding_model,
            "creation_timestamp": self.creation_timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SimilarityScore:
    """Immutable similarity score result"""

    content_id_1: str
    content_id_2: str
    similarity_score: float  # 0.0 to 1.0
    metric_used: SimilarityMetric
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "content_id_1": self.content_id_1,
            "content_id_2": self.content_id_2,
            "similarity_score": self.similarity_score,
            "metric_used": self.metric_used.value,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SearchResult:
    """Immutable search result with relevance scoring"""

    content_id: str
    relevance_score: float  # 0.0 to 1.0
    content_snippet: str = ""
    matched_terms: list[str] = field(default_factory=list)
    search_mode: SearchMode = SearchMode.SEMANTIC_SEARCH
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "content_id": self.content_id,
            "relevance_score": self.relevance_score,
            "content_snippet": self.content_snippet,
            "matched_terms": self.matched_terms,
            "search_mode": self.search_mode.value,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class SemanticSearchQuery:
    """Immutable semantic search query specification"""

    query_text: str
    search_mode: SearchMode = SearchMode.SEMANTIC_SEARCH
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    ranking_strategy: RankingStrategy = RankingStrategy.HYBRID_RANKING
    max_results: int = 50
    min_similarity_threshold: float = 0.1
    include_snippets: bool = True
    context_filters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "query_text": self.query_text,
            "search_mode": self.search_mode.value,
            "similarity_metric": self.similarity_metric.value,
            "ranking_strategy": self.ranking_strategy.value,
            "max_results": self.max_results,
            "min_similarity_threshold": self.min_similarity_threshold,
            "include_snippets": self.include_snippets,
            "context_filters": self.context_filters,
        }


@dataclass(frozen=True)
class SemanticSearchResponse:
    """Immutable comprehensive search response"""

    query: SemanticSearchQuery
    results: list[SearchResult]
    total_matches: int
    search_time_ms: float
    embedding_time_ms: float
    ranking_time_ms: float

    # Statistics
    average_relevance: float
    top_relevance: float
    search_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "query": self.query.to_dict(),
            "results": [result.to_dict() for result in self.results],
            "total_matches": self.total_matches,
            "search_time_ms": self.search_time_ms,
            "embedding_time_ms": self.embedding_time_ms,
            "ranking_time_ms": self.ranking_time_ms,
            "average_relevance": self.average_relevance,
            "top_relevance": self.top_relevance,
            "search_timestamp": self.search_timestamp.isoformat(),
        }


@dataclass
class SemanticConfig:
    """Configuration for semantic search engine"""

    # Embedding settings
    embedding_dimensionality: int = 300
    embedding_model: str = "tf_idf_enhanced"
    enable_vector_caching: bool = True
    vector_cache_ttl: int = 7200  # 2 hours

    # Search settings
    default_max_results: int = 50
    default_similarity_threshold: float = 0.1
    enable_fuzzy_matching: bool = True
    fuzzy_threshold: float = 0.8

    # Performance settings
    max_concurrent_searches: int = 10
    batch_embedding_size: int = 100
    enable_search_caching: bool = True
    search_cache_ttl: int = 1800  # 30 minutes

    # Quality settings
    snippet_length: int = 200
    max_matched_terms: int = 10
    enable_query_expansion: bool = True

    # Advanced features
    enable_contextual_boosting: bool = True
    enable_recency_decay: bool = True
    recency_decay_factor: float = 0.1
    quality_boost_factor: float = 0.2


class EmbeddingGenerator(ABC):
    """Abstract base for embedding generation implementations"""

    @abstractmethod
    async def generate_embedding(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> VectorEmbedding:
        """Generate vector embedding for content"""

    @abstractmethod
    async def batch_generate_embeddings(
        self,
        content_items: list[tuple[str, str, dict[str, Any]]],
    ) -> list[VectorEmbedding]:
        """Generate embeddings for multiple content items"""


class TFIDFEmbeddingGenerator(EmbeddingGenerator):
    """TF-IDF based embedding generator with enhancements"""

    def __init__(self, config: SemanticConfig):
        self.config = config
        self.vocabulary: dict[str, int] = {}
        self.idf_scores: dict[str, float] = {}
        self.document_frequencies: dict[str, int] = defaultdict(int)
        self.total_documents = 0

        # Enhanced vocabulary with semantic understanding
        self._initialize_enhanced_vocabulary()

    def _initialize_enhanced_vocabulary(self):
        """Initialize vocabulary with semantic word relationships"""
        # Core semantic categories
        self.semantic_categories = {
            "technology": {
                "ai",
                "artificial",
                "intelligence",
                "machine",
                "learning",
                "deep",
                "neural",
                "network",
                "algorithm",
                "data",
                "science",
                "programming",
            },
            "research": {
                "study",
                "research",
                "analysis",
                "methodology",
                "results",
                "conclusion",
                "experiment",
                "hypothesis",
                "findings",
                "statistical",
                "academic",
            },
            "business": {
                "business",
                "company",
                "market",
                "strategy",
                "revenue",
                "profit",
                "growth",
                "management",
                "corporate",
                "enterprise",
                "investment",
            },
            "health": {
                "health",
                "medical",
                "healthcare",
                "treatment",
                "patient",
                "clinical",
                "medicine",
                "therapy",
                "diagnosis",
                "disease",
                "wellness",
            },
        }

        # Build initial vocabulary from semantic categories
        for category, terms in self.semantic_categories.items():
            for term in terms:
                if term not in self.vocabulary:
                    self.vocabulary[term] = len(self.vocabulary)

    def _preprocess_text(self, content: str) -> list[str]:
        """Preprocess text for embedding generation"""
        # Convert to lowercase and extract words
        normalized = content.lower()
        words = re.findall(r"\b[a-zA-Z]{2,}\b", normalized)

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }

        return [word for word in words if word not in stop_words and len(word) > 2]

    def _update_vocabulary_and_idf(self, processed_words: list[str]):
        """Update vocabulary and IDF scores"""
        # Add new words to vocabulary
        unique_words = set(processed_words)
        for word in unique_words:
            if word not in self.vocabulary:
                self.vocabulary[word] = len(self.vocabulary)
            self.document_frequencies[word] += 1

        self.total_documents += 1

        # Recalculate IDF scores
        for word in self.vocabulary:
            doc_freq = self.document_frequencies.get(word, 1)
            # Add smoothing to avoid zero IDF and ensure positive values
            self.idf_scores[word] = (
                math.log((self.total_documents + 1) / (doc_freq + 1)) + 1
            )

    def _calculate_tf_idf_vector(self, processed_words: list[str]) -> list[float]:
        """Calculate TF-IDF vector for processed words"""
        # Initialize vector with configured dimensionality
        vector = [0.0] * self.config.embedding_dimensionality

        # Calculate term frequencies
        term_counts = defaultdict(int)
        for word in processed_words:
            term_counts[word] += 1

        total_terms = len(processed_words)
        if total_terms == 0:
            return vector

        # Calculate TF-IDF scores
        for word, count in term_counts.items():
            if word in self.vocabulary:
                vocab_index = self.vocabulary[word]
                # Map vocabulary index to vector dimensions
                vector_index = vocab_index % self.config.embedding_dimensionality

                tf = count / total_terms
                idf = self.idf_scores.get(word, 1.0)
                # Use += to handle multiple words mapping to same index
                vector[vector_index] += tf * idf

        # Normalize vector (L2 normalization)
        vector_magnitude = math.sqrt(sum(x * x for x in vector))
        if vector_magnitude > 0:
            vector = [x / vector_magnitude for x in vector]

        return vector

    async def generate_embedding(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> VectorEmbedding:
        """Generate TF-IDF embedding for content"""
        if not content or len(content.strip()) < 10:
            # Return zero vector for empty content
            zero_vector = [0.0] * self.config.embedding_dimensionality
            return VectorEmbedding(
                content_id=(
                    metadata.get("content_id", "unknown") if metadata else "unknown"
                ),
                vector=tuple(zero_vector),
                dimensionality=self.config.embedding_dimensionality,
                embedding_model=self.config.embedding_model,
            )

        # Preprocess content
        processed_words = self._preprocess_text(content)

        # Update vocabulary and IDF (for training)
        self._update_vocabulary_and_idf(processed_words)

        # Generate TF-IDF vector
        vector = self._calculate_tf_idf_vector(processed_words)

        # Ensure vector matches configured dimensionality
        if len(vector) != self.config.embedding_dimensionality:
            if len(vector) > self.config.embedding_dimensionality:
                vector = vector[: self.config.embedding_dimensionality]
            else:
                vector.extend(
                    [0.0] * (self.config.embedding_dimensionality - len(vector)),
                )

        return VectorEmbedding(
            content_id=metadata.get("content_id", "unknown") if metadata else "unknown",
            vector=tuple(vector),
            dimensionality=self.config.embedding_dimensionality,
            embedding_model=self.config.embedding_model,
        )

    async def batch_generate_embeddings(
        self,
        content_items: list[tuple[str, str, dict[str, Any]]],
    ) -> list[VectorEmbedding]:
        """Generate embeddings for multiple content items"""
        results = []

        for content_id, content, metadata in content_items:
            embedding_metadata = {**(metadata or {}), "content_id": content_id}
            embedding = await self.generate_embedding(content, embedding_metadata)
            results.append(embedding)

        return results


class SimilarityCalculator:
    """Advanced similarity calculation with multiple metrics"""

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        magnitude1 = np.linalg.norm(vec1)
        magnitude2 = np.linalg.norm(vec2)

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return max(0.0, min(1.0, dot_product / (magnitude1 * magnitude2)))

    @staticmethod
    def euclidean_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate euclidean distance-based similarity"""
        if len(vec1) != len(vec2):
            return 0.0

        distance = np.linalg.norm(vec1 - vec2)
        # Convert distance to similarity (0 to 1)
        max_distance = math.sqrt(2)  # Maximum possible distance for normalized vectors
        similarity = 1.0 - min(distance / max_distance, 1.0)
        return max(0.0, similarity)

    @staticmethod
    def dot_product_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate dot product similarity"""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        # Normalize to 0-1 range (assuming vectors are normalized)
        return max(0.0, min(1.0, (dot_product + 1) / 2))

    @staticmethod
    def jaccard_similarity(terms1: set[str], terms2: set[str]) -> float:
        """Calculate Jaccard similarity for term sets"""
        if not terms1 and not terms2:
            return 1.0
        if not terms1 or not terms2:
            return 0.0

        intersection = len(terms1.intersection(terms2))
        union = len(terms1.union(terms2))

        return intersection / union if union > 0 else 0.0

    @classmethod
    def calculate_similarity(
        cls,
        embedding1: VectorEmbedding,
        embedding2: VectorEmbedding,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> SimilarityScore:
        """Calculate similarity between two embeddings"""
        vec1 = embedding1.to_numpy()
        vec2 = embedding2.to_numpy()

        if metric == SimilarityMetric.COSINE:
            score = cls.cosine_similarity(vec1, vec2)
        elif metric == SimilarityMetric.EUCLIDEAN:
            score = cls.euclidean_similarity(vec1, vec2)
        elif metric == SimilarityMetric.DOT_PRODUCT:
            score = cls.dot_product_similarity(vec1, vec2)
        else:
            # Default to cosine similarity
            score = cls.cosine_similarity(vec1, vec2)

        # Calculate confidence based on vector magnitudes
        mag1 = np.linalg.norm(vec1)
        mag2 = np.linalg.norm(vec2)
        confidence = min(mag1, mag2) / max(max(mag1, mag2), 1e-8)

        return SimilarityScore(
            content_id_1=embedding1.content_id,
            content_id_2=embedding2.content_id,
            similarity_score=score,
            metric_used=metric,
            confidence=confidence,
        )


class SemanticSearchEngine:
    """Advanced semantic search engine with vector embeddings and similarity matching.
    Provides intelligent content discovery and contextual search capabilities.
    """

    def __init__(self, config: SemanticConfig = None):
        self.config = config or SemanticConfig()

        # Initialize components
        self.embedding_generator = TFIDFEmbeddingGenerator(self.config)
        self.similarity_calculator = SimilarityCalculator()

        # Storage
        self.embeddings_store: dict[str, VectorEmbedding] = {}
        self.content_metadata: dict[str, dict[str, Any]] = {}

        # Caching
        self.search_cache: dict[str, SemanticSearchResponse] = {}

        # Statistics
        self.stats = {
            "total_embeddings": 0,
            "total_searches": 0,
            "cache_hits": 0,
            "average_search_time": 0.0,
            "total_search_time": 0.0,
        }

        logger.info("Initialized Semantic Search Engine")

    async def index_content(
        self,
        content_id: str,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> VectorEmbedding:
        """Index content by generating and storing its vector embedding."""
        start_time = time.time()

        try:
            # Generate embedding
            embedding_metadata = {**(metadata or {}), "content_id": content_id}
            embedding = await self.embedding_generator.generate_embedding(
                content,
                embedding_metadata,
            )

            # Store embedding and metadata
            self.embeddings_store[content_id] = embedding
            self.content_metadata[content_id] = {
                **(metadata or {}),
                "content_length": len(content),
                "indexed_at": datetime.now(UTC).isoformat(),
            }

            # Update statistics
            self.stats["total_embeddings"] += 1

            logger.debug(
                f"Indexed content {content_id} in {(time.time() - start_time) * 1000:.1f}ms",
            )
            return embedding

        except Exception as e:
            logger.error(f"Failed to index content {content_id}: {e}")
            raise

    async def batch_index_content(
        self,
        content_items: list[tuple[str, str, dict[str, Any]]],
    ) -> list[VectorEmbedding]:
        """Index multiple content items in batch for efficiency."""
        start_time = time.time()

        try:
            # Generate embeddings in batch
            embeddings = await self.embedding_generator.batch_generate_embeddings(
                content_items,
            )

            # Store embeddings and metadata
            for i, (content_id, content, metadata) in enumerate(content_items):
                if i < len(embeddings):
                    self.embeddings_store[content_id] = embeddings[i]
                    self.content_metadata[content_id] = {
                        **(metadata or {}),
                        "content_length": len(content),
                        "indexed_at": datetime.now(UTC).isoformat(),
                    }

            # Update statistics
            self.stats["total_embeddings"] += len(embeddings)

            logger.info(
                f"Batch indexed {len(embeddings)} items in {(time.time() - start_time) * 1000:.1f}ms",
            )
            return embeddings

        except Exception as e:
            logger.error(f"Failed to batch index content: {e}")
            raise

    async def semantic_search(
        self,
        query: SemanticSearchQuery,
    ) -> SemanticSearchResponse:
        """Perform semantic search using vector similarity matching."""
        start_time = time.time()

        try:
            # Check search cache
            cache_key = self._generate_search_cache_key(query)
            if self.config.enable_search_caching and cache_key in self.search_cache:
                self.stats["cache_hits"] += 1
                return self.search_cache[cache_key]

            # Generate query embedding
            embedding_start = time.time()
            query_embedding = await self.embedding_generator.generate_embedding(
                query.query_text,
                {"content_id": "query"},
            )
            embedding_time = max(
                0.1,
                (time.time() - embedding_start) * 1000,
            )  # Ensure minimum time

            # Calculate similarities with all indexed content
            similarity_scores = []
            for content_id, content_embedding in self.embeddings_store.items():
                similarity = self.similarity_calculator.calculate_similarity(
                    query_embedding,
                    content_embedding,
                    query.similarity_metric,
                )

                if similarity.similarity_score >= query.min_similarity_threshold:
                    similarity_scores.append((content_id, similarity))

            # Rank and format results
            ranking_start = time.time()
            search_results = self._rank_and_format_results(query, similarity_scores)
            ranking_time = max(
                0.1,
                (time.time() - ranking_start) * 1000,
            )  # Ensure minimum time

            # Calculate statistics
            total_search_time = max(
                0.1,
                (time.time() - start_time) * 1000,
            )  # Ensure minimum time
            avg_relevance = sum(r.relevance_score for r in search_results) / max(
                len(search_results),
                1,
            )
            top_relevance = max(
                (r.relevance_score for r in search_results),
                default=0.0,
            )

            response = SemanticSearchResponse(
                query=query,
                results=search_results[: query.max_results],
                total_matches=len(similarity_scores),
                search_time_ms=total_search_time,
                embedding_time_ms=embedding_time,
                ranking_time_ms=ranking_time,
                average_relevance=avg_relevance,
                top_relevance=top_relevance,
            )

            # Cache response
            if self.config.enable_search_caching:
                self.search_cache[cache_key] = response
                # Simple cache management
                if len(self.search_cache) > 1000:
                    oldest_keys = list(self.search_cache.keys())[:100]
                    for old_key in oldest_keys:
                        del self.search_cache[old_key]

            # Update statistics
            self.stats["total_searches"] += 1
            self.stats["total_search_time"] += total_search_time
            self.stats["average_search_time"] = (
                self.stats["total_search_time"] / self.stats["total_searches"]
            )

            return response

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    def _rank_and_format_results(
        self,
        query: SemanticSearchQuery,
        similarity_scores: list[tuple[str, SimilarityScore]],
    ) -> list[SearchResult]:
        """Rank and format search results"""
        results = []

        for content_id, similarity in similarity_scores:
            metadata = self.content_metadata.get(content_id, {})

            # Calculate final relevance score
            relevance_score = similarity.similarity_score

            # Apply ranking strategy adjustments
            if query.ranking_strategy == RankingStrategy.QUALITY_WEIGHTED:
                quality_score = metadata.get("quality_score", 0.5)
                relevance_score = (relevance_score * 0.7) + (quality_score * 0.3)
            elif query.ranking_strategy == RankingStrategy.RECENCY_WEIGHTED:
                recency_boost = self._calculate_recency_boost(metadata)
                relevance_score = relevance_score + (
                    recency_boost * self.config.recency_decay_factor
                )
            elif query.ranking_strategy == RankingStrategy.HYBRID_RANKING:
                quality_score = metadata.get("quality_score", 0.5)
                recency_boost = self._calculate_recency_boost(metadata)
                relevance_score = (
                    relevance_score * 0.6 + quality_score * 0.25 + recency_boost * 0.15
                )

            # Generate snippet if requested
            snippet = ""
            if query.include_snippets:
                snippet = self._generate_snippet(content_id, query.query_text)

            # Extract matched terms
            matched_terms = self._extract_matched_terms(query.query_text, content_id)

            result = SearchResult(
                content_id=content_id,
                relevance_score=min(1.0, max(0.0, relevance_score)),
                content_snippet=snippet,
                matched_terms=matched_terms,
                search_mode=query.search_mode,
                metadata=metadata,
            )

            results.append(result)

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results

    def _calculate_recency_boost(self, metadata: dict[str, Any]) -> float:
        """Calculate recency boost factor"""
        indexed_at_str = metadata.get("indexed_at")
        if not indexed_at_str:
            return 0.0

        try:
            indexed_at = datetime.fromisoformat(indexed_at_str.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            days_old = (now - indexed_at).days

            # Exponential decay based on age
            recency_boost = math.exp(-days_old * self.config.recency_decay_factor)
            return min(1.0, recency_boost)

        except Exception:
            return 0.0

    def _generate_snippet(self, content_id: str, query_text: str) -> str:
        """Generate content snippet highlighting query relevance"""
        # In a real implementation, this would extract relevant content segments
        # For now, return a placeholder snippet
        return f"Content snippet for {content_id} related to: {query_text[:100]}..."

    def _extract_matched_terms(self, query_text: str, content_id: str) -> list[str]:
        """Extract terms that matched between query and content"""
        query_terms = set(re.findall(r"\b[a-zA-Z]{2,}\b", query_text.lower()))

        # In a real implementation, this would analyze the actual content
        # For now, return a subset of query terms
        return list(query_terms)[: self.config.max_matched_terms]

    def _generate_search_cache_key(self, query: SemanticSearchQuery) -> str:
        """Generate cache key for search query"""
        query_data = {
            "query_text": query.query_text,
            "search_mode": query.search_mode.value,
            "similarity_metric": query.similarity_metric.value,
            "max_results": query.max_results,
            "min_similarity_threshold": query.min_similarity_threshold,
        }

        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()[:16]

    def get_search_statistics(self) -> dict[str, Any]:
        """Get semantic search engine statistics"""
        stats = self.stats.copy()
        stats["indexed_content_count"] = len(self.embeddings_store)
        stats["cache_hit_rate"] = self.stats["cache_hits"] / max(
            self.stats["total_searches"],
            1,
        )
        stats["cached_searches"] = len(self.search_cache)

        return stats

    async def find_similar_content(
        self,
        content_id: str,
        max_results: int = 10,
        similarity_threshold: float = 0.3,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> list[SimilarityScore]:
        """Find content similar to a specific piece of content."""
        if content_id not in self.embeddings_store:
            return []

        target_embedding = self.embeddings_store[content_id]
        similarities = []

        for other_id, other_embedding in self.embeddings_store.items():
            if other_id != content_id:
                similarity = self.similarity_calculator.calculate_similarity(
                    target_embedding,
                    other_embedding,
                    metric,
                )

                if similarity.similarity_score >= similarity_threshold:
                    similarities.append(similarity)

        # Sort by similarity score
        similarities.sort(key=lambda x: x.similarity_score, reverse=True)

        return similarities[:max_results]

    async def clear_index(self):
        """Clear all indexed content and caches"""
        self.embeddings_store.clear()
        self.content_metadata.clear()
        self.search_cache.clear()

        # Reset statistics
        self.stats = {
            "total_embeddings": 0,
            "total_searches": 0,
            "cache_hits": 0,
            "average_search_time": 0.0,
            "total_search_time": 0.0,
        }

        logger.info("Cleared semantic search index and cache")


# Production-ready factory functions
async def create_production_semantic_search_engine() -> SemanticSearchEngine:
    """Create production-ready semantic search engine"""
    config = SemanticConfig(
        embedding_dimensionality=500,
        embedding_model="tf_idf_enhanced_production",
        enable_vector_caching=True,
        vector_cache_ttl=14400,  # 4 hours
        default_max_results=100,
        default_similarity_threshold=0.05,
        enable_fuzzy_matching=True,
        max_concurrent_searches=20,
        batch_embedding_size=200,
        enable_search_caching=True,
        search_cache_ttl=3600,  # 1 hour
        enable_contextual_boosting=True,
        enable_recency_decay=True,
        recency_decay_factor=0.05,
        quality_boost_factor=0.3,
    )

    return SemanticSearchEngine(config)


if __name__ == "__main__":
    # Example usage
    async def main():
        engine = SemanticSearchEngine()

        # Index some test content
        content_items = [
            (
                "doc1",
                "This is a comprehensive study on machine learning algorithms and their applications in natural language processing.",
                {"source_type": "academic", "quality_score": 0.9},
            ),
            (
                "doc2",
                "Latest breakthroughs in artificial intelligence research show promising results for deep learning models.",
                {"source_type": "news", "quality_score": 0.7},
            ),
            (
                "doc3",
                "Tutorial: How to implement neural networks using Python and TensorFlow framework for beginners.",
                {"source_type": "tutorial", "quality_score": 0.8},
            ),
        ]

        await engine.batch_index_content(content_items)

        # Perform semantic search
        query = SemanticSearchQuery(
            query_text="machine learning neural networks",
            max_results=10,
            include_snippets=True,
        )

        response = await engine.semantic_search(query)

        print(f"Search Results: {len(response.results)}")
        print(f"Search Time: {response.search_time_ms:.1f}ms")
        print(f"Average Relevance: {response.average_relevance:.3f}")

        for result in response.results:
            print(f"  - {result.content_id}: {result.relevance_score:.3f}")

        # Find similar content
        similar = await engine.find_similar_content("doc1", max_results=5)
        print(f"Similar to doc1: {len(similar)} matches")

        stats = engine.get_search_statistics()
        print(f"Engine Statistics: {stats}")

    asyncio.run(main())
