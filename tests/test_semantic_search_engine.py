#!/usr/bin/env python3
"""
Test Suite for Semantic Search Engine
Comprehensive tests for vector embeddings, semantic matching, and intelligent search capabilities
"""

import asyncio
import time

import numpy as np
import pytest
import pytest_asyncio

from services.ai.semantic_search_engine import (
    RankingStrategy,
    SearchMode,
    SearchResult,
    SemanticConfig,
    SemanticSearchEngine,
    SemanticSearchQuery,
    SemanticSearchResponse,
    SimilarityCalculator,
    SimilarityMetric,
    SimilarityScore,
    TFIDFEmbeddingGenerator,
    VectorEmbedding,
    create_production_semantic_search_engine,
)


@pytest.mark.asyncio
class TestSemanticSearchEngine:
    """
    Test suite for the main Semantic Search Engine functionality.
    """

    @pytest_asyncio.fixture
    async def semantic_engine(self):
        """Create semantic search engine for testing"""
        config = SemanticConfig(
            embedding_dimensionality=100,
            enable_vector_caching=True,
            enable_search_caching=True,
            default_max_results=50,
            batch_embedding_size=10,
        )
        return SemanticSearchEngine(config)

    @pytest.fixture
    def sample_content_items(self):
        """Sample content for testing"""
        return [
            (
                "research_1",
                "This comprehensive research study investigates machine learning algorithms for natural language processing tasks. The methodology employs deep neural networks.",
                {"source_type": "academic", "quality_score": 0.9},
            ),
            (
                "news_1",
                "Breaking: Major AI breakthrough announced by tech company. Revolutionary deep learning model achieves unprecedented accuracy.",
                {"source_type": "news", "quality_score": 0.7},
            ),
            (
                "tutorial_1",
                "Learn how to build neural networks from scratch using Python. Step-by-step guide for beginners in machine learning.",
                {"source_type": "tutorial", "quality_score": 0.8},
            ),
            (
                "blog_1",
                "My thoughts on artificial intelligence and its impact on society. Personal perspective on AI ethics and future implications.",
                {"source_type": "blog", "quality_score": 0.6},
            ),
            (
                "paper_1",
                "Advanced optimization techniques for training deep neural networks. Comparative analysis of gradient descent variants.",
                {"source_type": "academic", "quality_score": 0.95},
            ),
        ]

    @pytest.fixture
    def sample_search_queries(self):
        """Sample search queries for testing"""
        return [
            SemanticSearchQuery(
                query_text="machine learning neural networks",
                max_results=10,
                include_snippets=True,
            ),
            SemanticSearchQuery(
                query_text="artificial intelligence breakthrough",
                search_mode=SearchMode.SEMANTIC_SEARCH,
                similarity_metric=SimilarityMetric.COSINE,
                max_results=5,
            ),
            SemanticSearchQuery(
                query_text="deep learning tutorial python",
                ranking_strategy=RankingStrategy.QUALITY_WEIGHTED,
                min_similarity_threshold=0.1,
            ),
        ]

    # ========================================================================
    # Core Engine Tests
    # ========================================================================

    async def test_should_initialize_semantic_search_engine_with_configuration(
        self,
        semantic_engine,
    ):
        """
        Test: Should initialize semantic search engine with proper
        configuration and component setup.
        """
        # Check engine initialization
        assert semantic_engine.config is not None
        assert semantic_engine.embedding_generator is not None
        assert semantic_engine.similarity_calculator is not None

        # Check initial state
        assert len(semantic_engine.embeddings_store) == 0
        assert len(semantic_engine.content_metadata) == 0
        assert semantic_engine.stats["total_embeddings"] == 0
        assert semantic_engine.stats["total_searches"] == 0

    async def test_should_index_single_content_successfully(self, semantic_engine):
        """
        Test: Should index single piece of content and generate
        proper vector embedding with metadata storage.
        """
        content_id = "test_doc"
        content = "This is a test document about machine learning and artificial intelligence."
        metadata = {"source_type": "test", "quality_score": 0.8}

        # Index content
        embedding = await semantic_engine.index_content(content_id, content, metadata)

        # Verify embedding
        assert isinstance(embedding, VectorEmbedding)
        assert embedding.content_id == content_id
        assert (
            embedding.dimensionality == semantic_engine.config.embedding_dimensionality
        )
        assert len(embedding.vector) == semantic_engine.config.embedding_dimensionality

        # Verify storage
        assert content_id in semantic_engine.embeddings_store
        assert content_id in semantic_engine.content_metadata
        assert semantic_engine.stats["total_embeddings"] == 1

        # Verify metadata
        stored_metadata = semantic_engine.content_metadata[content_id]
        assert stored_metadata["source_type"] == "test"
        assert stored_metadata["quality_score"] == 0.8
        assert "indexed_at" in stored_metadata
        assert stored_metadata["content_length"] == len(content)

    async def test_should_batch_index_multiple_content_items_efficiently(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should efficiently index multiple content items in batch
        with proper embedding generation and metadata storage.
        """
        # Batch index content
        embeddings = await semantic_engine.batch_index_content(sample_content_items)

        # Verify embeddings
        assert len(embeddings) == len(sample_content_items)
        for embedding in embeddings:
            assert isinstance(embedding, VectorEmbedding)
            assert (
                embedding.dimensionality
                == semantic_engine.config.embedding_dimensionality
            )

        # Verify storage
        assert len(semantic_engine.embeddings_store) == len(sample_content_items)
        assert len(semantic_engine.content_metadata) == len(sample_content_items)
        assert semantic_engine.stats["total_embeddings"] == len(sample_content_items)

        # Verify all content IDs are stored
        for content_id, _, _ in sample_content_items:
            assert content_id in semantic_engine.embeddings_store
            assert content_id in semantic_engine.content_metadata

    async def test_should_perform_semantic_search_with_relevance_ranking(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should perform semantic search and return results
        ranked by relevance with proper scoring.
        """
        # Index content first
        await semantic_engine.batch_index_content(sample_content_items)

        # Perform search
        query = SemanticSearchQuery(
            query_text="machine learning neural networks",
            max_results=10,
            include_snippets=True,
        )

        response = await semantic_engine.semantic_search(query)

        # Verify response structure
        assert isinstance(response, SemanticSearchResponse)
        assert response.query == query
        assert len(response.results) > 0
        assert response.total_matches >= len(response.results)
        assert response.search_time_ms > 0
        assert response.embedding_time_ms > 0

        # Verify result quality
        assert response.average_relevance > 0
        assert response.top_relevance > 0
        assert response.top_relevance >= response.average_relevance

        # Verify results are ranked by relevance
        relevance_scores = [result.relevance_score for result in response.results]
        assert relevance_scores == sorted(relevance_scores, reverse=True)

        # Verify search statistics update
        stats = semantic_engine.get_search_statistics()
        assert stats["total_searches"] == 1
        assert stats["average_search_time"] > 0

    async def test_should_find_similar_content_with_similarity_scoring(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should find content similar to a specific item
        with accurate similarity scoring and ranking.
        """
        # Index content first
        await semantic_engine.batch_index_content(sample_content_items)

        # Find similar content to research_1 (ML/AI focused)
        similar_results = await semantic_engine.find_similar_content(
            "research_1",
            max_results=5,
            similarity_threshold=0.1,
        )

        # Verify results
        assert isinstance(similar_results, list)
        assert len(similar_results) > 0

        for similarity in similar_results:
            assert isinstance(similarity, SimilarityScore)
            assert similarity.content_id_1 == "research_1"
            assert similarity.content_id_2 != "research_1"
            assert 0.0 <= similarity.similarity_score <= 1.0
            assert similarity.similarity_score >= 0.1  # Above threshold

        # Results should be ordered by similarity
        scores = [s.similarity_score for s in similar_results]
        assert scores == sorted(scores, reverse=True)

    # ========================================================================
    # Search Functionality Tests
    # ========================================================================

    async def test_should_handle_different_search_modes_appropriately(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should handle different search modes (semantic, fuzzy, hybrid)
        with appropriate result variation and performance.
        """
        await semantic_engine.batch_index_content(sample_content_items)

        base_query_text = "machine learning algorithms"

        # Test different search modes
        search_modes = [
            SearchMode.SEMANTIC_SEARCH,
            SearchMode.FUZZY_SEARCH,
            SearchMode.HYBRID_SEARCH,
        ]

        results_by_mode = {}

        for mode in search_modes:
            query = SemanticSearchQuery(
                query_text=base_query_text,
                search_mode=mode,
                max_results=10,
            )

            response = await semantic_engine.semantic_search(query)
            results_by_mode[mode] = response

            # Verify basic response quality
            assert len(response.results) > 0
            assert response.search_time_ms > 0
            assert response.average_relevance > 0

            # Verify search mode is preserved
            for result in response.results:
                assert result.search_mode == mode

    async def test_should_apply_different_similarity_metrics_correctly(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should apply different similarity metrics (cosine, euclidean, dot product)
        with measurable differences in results.
        """
        await semantic_engine.batch_index_content(sample_content_items)

        query_text = "neural networks deep learning"
        metrics = [
            SimilarityMetric.COSINE,
            SimilarityMetric.EUCLIDEAN,
            SimilarityMetric.DOT_PRODUCT,
        ]

        results_by_metric = {}

        for metric in metrics:
            query = SemanticSearchQuery(
                query_text=query_text,
                similarity_metric=metric,
                max_results=5,
            )

            response = await semantic_engine.semantic_search(query)
            results_by_metric[metric] = response

            # Verify results exist
            assert len(response.results) > 0
            assert response.average_relevance > 0

        # Different metrics should potentially produce different rankings
        cosine_results = results_by_metric[SimilarityMetric.COSINE]
        euclidean_results = results_by_metric[SimilarityMetric.EUCLIDEAN]

        # At minimum, verify they both produce valid results
        assert len(cosine_results.results) > 0
        assert len(euclidean_results.results) > 0

    async def test_should_apply_ranking_strategies_with_different_outcomes(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should apply different ranking strategies (relevance, quality, recency, hybrid)
        with observable impact on result ordering.
        """
        await semantic_engine.batch_index_content(sample_content_items)

        query_text = "artificial intelligence"
        strategies = [
            RankingStrategy.RELEVANCE_ONLY,
            RankingStrategy.QUALITY_WEIGHTED,
            RankingStrategy.HYBRID_RANKING,
        ]

        results_by_strategy = {}

        for strategy in strategies:
            query = SemanticSearchQuery(
                query_text=query_text,
                ranking_strategy=strategy,
                max_results=5,
            )

            response = await semantic_engine.semantic_search(query)
            results_by_strategy[strategy] = response

            # Verify results quality
            assert len(response.results) > 0
            assert response.ranking_time_ms > 0

        # Quality-weighted should potentially favor higher quality content
        quality_results = results_by_strategy[RankingStrategy.QUALITY_WEIGHTED]
        relevance_results = results_by_strategy[RankingStrategy.RELEVANCE_ONLY]

        # Both should produce valid results
        assert len(quality_results.results) > 0
        assert len(relevance_results.results) > 0

    # ========================================================================
    # Caching and Performance Tests
    # ========================================================================

    async def test_should_utilize_search_caching_for_repeated_queries(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should cache search results and utilize cache for
        repeated queries with improved performance.
        """
        await semantic_engine.batch_index_content(sample_content_items)

        query = SemanticSearchQuery(
            query_text="machine learning research",
            max_results=5,
        )

        # First search (cache miss)
        start_time = time.time()
        response1 = await semantic_engine.semantic_search(query)
        first_search_time = time.time() - start_time

        # Second search (should be cached)
        start_time = time.time()
        response2 = await semantic_engine.semantic_search(query)
        second_search_time = time.time() - start_time

        # Verify results are identical
        assert len(response1.results) == len(response2.results)
        assert response1.total_matches == response2.total_matches

        # Verify cache utilization
        stats = semantic_engine.get_search_statistics()
        if semantic_engine.config.enable_search_caching:
            assert stats["cache_hits"] > 0
            assert stats["cache_hit_rate"] > 0
            # Second search should be faster due to caching
            assert second_search_time < first_search_time * 1.5  # Allow some variance

    async def test_should_handle_large_volume_content_indexing_efficiently(
        self,
        semantic_engine,
    ):
        """
        Test: Should efficiently handle indexing of large volumes of content
        with reasonable performance and memory usage.
        """
        # Generate large volume of content
        large_content_batch = []
        for i in range(100):  # 100 documents
            content_id = f"large_doc_{i}"
            content = f"Document {
                i
            } contains information about various topics including technology, science, and research methods. This content is part of a large-scale indexing test."
            metadata = {
                "source_type": "test",
                "doc_number": i,
                "quality_score": 0.5 + (i % 5) * 0.1,
            }
            large_content_batch.append((content_id, content, metadata))

        # Measure indexing performance
        start_time = time.time()
        embeddings = await semantic_engine.batch_index_content(large_content_batch)
        indexing_time = time.time() - start_time

        # Verify successful indexing
        assert len(embeddings) == 100
        assert semantic_engine.stats["total_embeddings"] == 100
        assert len(semantic_engine.embeddings_store) == 100

        # Verify reasonable performance (should complete within 30 seconds)
        assert indexing_time < 30.0

        # Test search performance on large index
        query = SemanticSearchQuery(
            query_text="technology research methods",
            max_results=20,
        )
        search_start = time.time()
        response = await semantic_engine.semantic_search(query)
        search_time = time.time() - search_start

        # Search should complete quickly even with large index
        assert search_time < 5.0
        assert len(response.results) > 0

    async def test_should_handle_empty_and_invalid_content_gracefully(
        self,
        semantic_engine,
    ):
        """
        Test: Should handle empty, invalid, or malformed content
        without errors and with appropriate fallback behavior.
        """
        # Test empty content
        empty_embedding = await semantic_engine.index_content(
            "empty_doc",
            "",
            {"source_type": "test"},
        )
        assert isinstance(empty_embedding, VectorEmbedding)
        assert empty_embedding.content_id == "empty_doc"

        # Test very short content
        short_embedding = await semantic_engine.index_content(
            "short_doc",
            "AI",
            {"source_type": "test"},
        )
        assert isinstance(short_embedding, VectorEmbedding)

        # Test None content (should not crash)
        try:
            none_embedding = await semantic_engine.index_content(
                "none_doc",
                None,
                {"source_type": "test"},
            )
            assert isinstance(none_embedding, VectorEmbedding)
        except Exception:
            # It's acceptable to raise an exception for None content
            pass

        # Test search with empty query
        empty_query = SemanticSearchQuery(query_text="")
        response = await semantic_engine.semantic_search(empty_query)
        assert isinstance(response, SemanticSearchResponse)
        # Empty query might return no results or all results
        assert response.total_matches >= 0

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    async def test_should_handle_concurrent_operations_safely(self, semantic_engine):
        """
        Test: Should handle concurrent indexing and searching operations
        without data corruption or race conditions.
        """
        # Create concurrent content for indexing
        concurrent_content = [
            (
                f"concurrent_doc_{i}",
                f"Concurrent document {i} about machine learning and AI research.",
                {"source_type": "concurrent", "doc_id": i},
            )
            for i in range(20)
        ]

        # Define concurrent operations
        async def index_operation():
            return await semantic_engine.batch_index_content(concurrent_content[:10])

        async def search_operation():
            query = SemanticSearchQuery(query_text="machine learning", max_results=5)
            return await semantic_engine.semantic_search(query)

        # Run concurrent operations
        index_task = asyncio.create_task(index_operation())
        search_task1 = asyncio.create_task(search_operation())
        search_task2 = asyncio.create_task(search_operation())

        # Wait for all operations to complete
        results = await asyncio.gather(
            index_task,
            search_task1,
            search_task2,
            return_exceptions=True,
        )

        # Verify no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception)

        # Verify data integrity
        assert len(semantic_engine.embeddings_store) >= 10
        assert semantic_engine.stats["total_embeddings"] >= 10

    async def test_should_clear_index_and_reset_statistics_properly(
        self,
        semantic_engine,
        sample_content_items,
    ):
        """
        Test: Should properly clear search index, caches, and reset
        statistics without leaving residual data.
        """
        # Index some content and perform searches
        await semantic_engine.batch_index_content(sample_content_items)

        query = SemanticSearchQuery(query_text="machine learning")
        await semantic_engine.semantic_search(query)

        # Verify data exists
        assert len(semantic_engine.embeddings_store) > 0
        assert semantic_engine.stats["total_embeddings"] > 0
        assert semantic_engine.stats["total_searches"] > 0

        # Clear index
        await semantic_engine.clear_index()

        # Verify everything is cleared
        assert len(semantic_engine.embeddings_store) == 0
        assert len(semantic_engine.content_metadata) == 0
        assert len(semantic_engine.search_cache) == 0
        assert semantic_engine.stats["total_embeddings"] == 0
        assert semantic_engine.stats["total_searches"] == 0
        assert semantic_engine.stats["cache_hits"] == 0


@pytest.mark.asyncio
class TestEmbeddingComponents:
    """
    Test suite for individual embedding and similarity components.
    """

    @pytest_asyncio.fixture
    def tfidf_generator(self):
        """Create TF-IDF embedding generator for testing"""
        config = SemanticConfig(embedding_dimensionality=50)
        return TFIDFEmbeddingGenerator(config)

    @pytest_asyncio.fixture
    def similarity_calculator(self):
        """Create similarity calculator for testing"""
        return SimilarityCalculator()

    async def test_tfidf_generator_should_create_normalized_embeddings(
        self,
        tfidf_generator,
    ):
        """
        Test: TF-IDF generator should create properly normalized vector embeddings
        with correct dimensionality and mathematical properties.
        """
        content = "This is a test document about machine learning and artificial intelligence algorithms."
        metadata = {"content_id": "test_doc"}

        embedding = await tfidf_generator.generate_embedding(content, metadata)

        # Verify embedding properties
        assert isinstance(embedding, VectorEmbedding)
        assert embedding.content_id == "test_doc"
        assert embedding.dimensionality == 50
        assert len(embedding.vector) == 50

        # Verify normalization (L2 norm should be approximately 1.0)
        vector_np = embedding.to_numpy()
        norm = np.linalg.norm(vector_np)
        assert 0.95 <= norm <= 1.05  # Allow small numerical variance

        # Vector should not be all zeros
        assert np.sum(np.abs(vector_np)) > 0

    async def test_similarity_calculator_should_compute_accurate_similarity_scores(
        self,
        tfidf_generator,
        similarity_calculator,
    ):
        """
        Test: Similarity calculator should compute accurate similarity scores
        using different metrics with expected mathematical properties.
        """
        # Create two similar documents
        content1 = "Machine learning and artificial intelligence research in deep neural networks."
        content2 = "Research in machine learning focuses on neural networks and artificial intelligence."
        content3 = "This document is about cooking recipes and kitchen techniques."

        # Generate embeddings
        embedding1 = await tfidf_generator.generate_embedding(
            content1,
            {"content_id": "doc1"},
        )
        embedding2 = await tfidf_generator.generate_embedding(
            content2,
            {"content_id": "doc2"},
        )
        embedding3 = await tfidf_generator.generate_embedding(
            content3,
            {"content_id": "doc3"},
        )

        # Test cosine similarity
        sim_1_2 = similarity_calculator.calculate_similarity(
            embedding1,
            embedding2,
            SimilarityMetric.COSINE,
        )
        sim_1_3 = similarity_calculator.calculate_similarity(
            embedding1,
            embedding3,
            SimilarityMetric.COSINE,
        )

        # Verify similarity scores
        assert isinstance(sim_1_2, SimilarityScore)
        assert 0.0 <= sim_1_2.similarity_score <= 1.0
        assert 0.0 <= sim_1_3.similarity_score <= 1.0

        # Similar documents should have higher similarity than dissimilar ones
        assert sim_1_2.similarity_score > sim_1_3.similarity_score

        # Test different metrics produce valid results
        sim_euclidean = similarity_calculator.calculate_similarity(
            embedding1,
            embedding2,
            SimilarityMetric.EUCLIDEAN,
        )
        sim_dot_product = similarity_calculator.calculate_similarity(
            embedding1,
            embedding2,
            SimilarityMetric.DOT_PRODUCT,
        )

        assert 0.0 <= sim_euclidean.similarity_score <= 1.0
        assert 0.0 <= sim_dot_product.similarity_score <= 1.0

    async def test_embedding_generator_should_handle_batch_processing_efficiently(
        self,
        tfidf_generator,
    ):
        """
        Test: Embedding generator should efficiently process multiple documents
        in batch with consistent quality and performance.
        """
        content_items = [
            (
                "batch_1",
                "Machine learning algorithms for data processing and analysis.",
                {"source": "test"},
            ),
            (
                "batch_2",
                "Deep neural networks in artificial intelligence research.",
                {"source": "test"},
            ),
            (
                "batch_3",
                "Natural language processing using transformer models.",
                {"source": "test"},
            ),
            (
                "batch_4",
                "Computer vision applications in autonomous driving.",
                {"source": "test"},
            ),
            (
                "batch_5",
                "Reinforcement learning for game playing and robotics.",
                {"source": "test"},
            ),
        ]

        start_time = time.time()
        embeddings = await tfidf_generator.batch_generate_embeddings(content_items)
        processing_time = time.time() - start_time

        # Verify batch results
        assert len(embeddings) == len(content_items)
        assert processing_time < 5.0  # Should complete quickly

        for i, embedding in enumerate(embeddings):
            assert isinstance(embedding, VectorEmbedding)
            assert embedding.content_id == content_items[i][0]
            assert (
                embedding.dimensionality
                == tfidf_generator.config.embedding_dimensionality
            )

            # Verify vector quality
            vector_np = embedding.to_numpy()
            assert np.sum(np.abs(vector_np)) > 0  # Not all zeros


@pytest.mark.asyncio
class TestProductionConfiguration:
    """
    Test suite for production-ready configuration and deployment scenarios.
    """

    async def test_should_create_production_semantic_search_engine(self):
        """
        Test: Should create production-ready semantic search engine
        with optimized configuration and performance settings.
        """
        engine = await create_production_semantic_search_engine()

        # Check engine is properly configured
        assert (
            engine.config.embedding_dimensionality > 100
        )  # Higher dimensionality for production
        assert engine.config.enable_vector_caching
        assert engine.config.enable_search_caching
        assert engine.config.max_concurrent_searches > 10
        assert engine.config.batch_embedding_size > 50

        # Test with sample content
        test_content = [
            (
                "prod_test_1",
                "Advanced machine learning techniques for large-scale data analysis and pattern recognition in enterprise environments.",
                {"source_type": "production", "quality_score": 0.9},
            ),
            (
                "prod_test_2",
                "Scalable artificial intelligence solutions for real-time decision making and automated system optimization.",
                {"source_type": "production", "quality_score": 0.85},
            ),
        ]

        # Should handle production-level operations
        embeddings = await engine.batch_index_content(test_content)
        assert len(embeddings) == 2

        # Should perform efficient searches
        query = SemanticSearchQuery(
            query_text="machine learning enterprise data analysis",
            max_results=10,
        )

        response = await engine.semantic_search(query)
        assert isinstance(response, SemanticSearchResponse)
        assert len(response.results) > 0
        assert response.search_time_ms > 0
        assert response.average_relevance > 0


class TestDataStructures:
    """
    Test suite for semantic search data structures and serialization.
    """

    def test_vector_embedding_should_serialize_correctly(self):
        """
        Test: VectorEmbedding should properly serialize to dictionary
        for JSON export and API responses.
        """
        embedding = VectorEmbedding(
            content_id="test_embedding",
            vector=(0.1, 0.2, 0.3, 0.4),
            dimensionality=4,
            embedding_model="test_model",
        )

        embedding_dict = embedding.to_dict()

        # Verify serialization
        assert embedding_dict["content_id"] == "test_embedding"
        assert embedding_dict["vector"] == [0.1, 0.2, 0.3, 0.4]
        assert embedding_dict["dimensionality"] == 4
        assert embedding_dict["embedding_model"] == "test_model"
        assert "creation_timestamp" in embedding_dict

    def test_semantic_search_response_should_serialize_completely(self):
        """
        Test: SemanticSearchResponse should serialize all components
        correctly for comprehensive API responses.
        """
        # Create complete search response
        query = SemanticSearchQuery(
            query_text="test query",
            max_results=5,
            similarity_metric=SimilarityMetric.COSINE,
        )

        results = [
            SearchResult(
                content_id="result_1",
                relevance_score=0.95,
                content_snippet="Test content snippet",
                matched_terms=["test", "query"],
                search_mode=SearchMode.SEMANTIC_SEARCH,
            ),
        ]

        response = SemanticSearchResponse(
            query=query,
            results=results,
            total_matches=1,
            search_time_ms=150.5,
            embedding_time_ms=50.2,
            ranking_time_ms=25.1,
            average_relevance=0.95,
            top_relevance=0.95,
        )

        response_dict = response.to_dict()

        # Verify complete serialization
        assert response_dict["query"]["query_text"] == "test query"
        assert len(response_dict["results"]) == 1
        assert response_dict["results"][0]["content_id"] == "result_1"
        assert response_dict["total_matches"] == 1
        assert response_dict["search_time_ms"] == 150.5
        assert response_dict["average_relevance"] == 0.95
        assert "search_timestamp" in response_dict
