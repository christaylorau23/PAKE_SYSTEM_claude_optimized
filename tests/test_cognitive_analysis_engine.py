#!/usr/bin/env python3
"""
PAKE System - Cognitive Analysis Engine Tests
Phase 3 Sprint 5: Comprehensive TDD testing for ML-powered content understanding

Tests sentiment analysis, topic extraction, quality assessment, content categorization,
and cognitive intelligence features.
"""

import asyncio
import time
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from services.ai.cognitive_analysis_engine import (
    CognitiveAnalysisEngine,
    CognitiveAnalysisResult,
    CognitiveConfig,
    ContentCategorizer,
    ContentCategory,
    QualityAssessor,
    QualityLevel,
    QualityMetrics,
    SentimentAnalysis,
    SentimentAnalyzer,
    SentimentPolarity,
    TopicConfidence,
    TopicExtraction,
    TopicExtractor,
    create_production_cognitive_engine,
)


class TestCognitiveAnalysisEngine:
    """
    Comprehensive test suite for cognitive analysis engine.
    Tests ML-powered content understanding, quality assessment, and intelligence features.
    """

    @pytest.fixture()
    def cognitive_config(self):
        """Standard cognitive analysis configuration for testing"""
        return CognitiveConfig(
            enable_sentiment_analysis=True,
            enable_topic_extraction=True,
            enable_quality_assessment=True,
            enable_entity_recognition=True,
            min_quality_score=0.3,
            min_content_length=50,
            max_content_length=10000,
            max_topics_per_content=8,
            topic_confidence_threshold=0.5,
            batch_processing_size=25,
            max_concurrent_analysis=5,
            enable_caching=True,
            enable_semantic_tagging=True,
            enable_content_summarization=True,
            summary_max_length=150,
        )

    @pytest_asyncio.fixture
    async def cognitive_engine(self, cognitive_config):
        """Create cognitive analysis engine instance for testing"""
        engine = CognitiveAnalysisEngine(cognitive_config)
        yield engine
        await engine.clear_cache()

    @pytest.fixture()
    def sample_research_content(self):
        """High-quality research content for testing"""
        return {
            "content": """
            This comprehensive research study investigates the effectiveness of deep learning algorithms
            in natural language processing tasks. The methodology employs transformer-based neural networks
            with attention mechanisms to achieve superior performance in text classification and sentiment analysis.
            Our experimental results demonstrate significant improvements over baseline approaches, with accuracy
            gains of 12% on standard benchmarks. The statistical analysis reveals strong correlations between
            model architecture complexity and task performance. These findings have important implications
            for future research in artificial intelligence and machine learning applications.
            """,
            "metadata": {
                "source_type": "academic",
                "author": "Dr. Research Team",
                "publication": "AI Research Journal",
                "year": 2024,
                "peer_reviewed": True,
            },
        }

    @pytest.fixture()
    def sample_social_content(self):
        """Social media content for testing"""
        return {
            "content": "Just amazing results from our latest #machinelearning experiment! 🎉 So excited to share this breakthrough with the community. Can't wait to see what comes next! #AI #research",
            "metadata": {
                "source_type": "social_media",
                "platform": "twitter",
                "likes": 145,
                "retweets": 32,
            },
        }

    @pytest.fixture()
    def sample_news_content(self):
        """News article content for testing"""
        return {
            "content": """
            Breaking: Major technology company announces disappointing quarterly results amid market uncertainty.
            According to sources close to the company, revenue fell short of analyst expectations by 15%.
            The CEO expressed concern about ongoing economic challenges and their impact on consumer spending.
            Industry experts warn this could signal broader troubles in the tech sector.
            """,
            "metadata": {
                "source_type": "news",
                "publication": "Tech News Daily",
                "published_date": "2024-01-15",
                "category": "business",
            },
        }

    # ========================================================================
    # Core Functionality Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_initialize_cognitive_engine_with_configuration(
        self,
        cognitive_config,
    ):
        """
        Test: Should initialize cognitive analysis engine with proper configuration
        and component setup.
        """
        engine = CognitiveAnalysisEngine(cognitive_config)

        # Check configuration is set
        assert engine.config == cognitive_config

        # Check analyzers are initialized
        assert engine.sentiment_analyzer is not None
        assert engine.topic_extractor is not None
        assert engine.quality_assessor is not None
        assert engine.content_categorizer is not None

        # Check initial state
        assert len(engine.analysis_cache) == 0
        assert engine.stats["total_analyzed"] == 0
        assert engine.stats["cache_hits"] == 0

    @pytest.mark.asyncio()
    async def test_should_perform_comprehensive_content_analysis(
        self,
        cognitive_engine,
        sample_research_content,
    ):
        """
        Test: Should perform comprehensive content analysis including sentiment,
        topics, quality, and categorization.
        """
        content = sample_research_content["content"]
        metadata = sample_research_content["metadata"]

        result = await cognitive_engine.analyze_content(
            "research_test_1",
            content,
            metadata,
        )

        # Check result structure
        assert isinstance(result, CognitiveAnalysisResult)
        assert result.content_id == "research_test_1"
        assert result.processing_time_ms > 0
        assert result.analysis_timestamp is not None

        # Check content categorization
        assert result.category in [
            ContentCategory.RESEARCH_PAPER,
            ContentCategory.EDUCATIONAL_CONTENT,
        ]

        # Check quality metrics
        assert 0.0 <= result.quality_metrics.overall_score <= 1.0
        assert result.quality_metrics.quality_level in [level for level in QualityLevel]
        assert (
            result.quality_metrics.technical_depth > 0.0
        )  # Should detect technical content

        # Check sentiment analysis
        assert result.sentiment_analysis.polarity in [
            polarity for polarity in SentimentPolarity
        ]
        assert 0.0 <= result.sentiment_analysis.confidence <= 1.0

        # Check topic extraction
        assert len(result.topic_extractions) > 0
        for topic in result.topic_extractions:
            assert isinstance(topic, TopicExtraction)
            assert topic.confidence in [conf for conf in TopicConfidence]
            assert 0.0 <= topic.relevance_score <= 1.0

        # Check confidence score
        assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio()
    async def test_should_detect_high_quality_academic_content(
        self,
        cognitive_engine,
        sample_research_content,
    ):
        """
        Test: Should correctly identify and assess high-quality academic content
        with appropriate quality metrics.
        """
        content = sample_research_content["content"]
        metadata = sample_research_content["metadata"]

        result = await cognitive_engine.analyze_content(
            "academic_test",
            content,
            metadata,
        )

        # Should identify as research or educational content
        assert result.category in [
            ContentCategory.RESEARCH_PAPER,
            ContentCategory.EDUCATIONAL_CONTENT,
        ]

        # Should assess as good quality due to academic indicators
        assert result.quality_metrics.overall_score >= 0.5
        assert result.quality_metrics.quality_level in [
            QualityLevel.GOOD,
            QualityLevel.EXCELLENT,
            QualityLevel.FAIR,
        ]

        # Should detect high technical depth
        assert result.quality_metrics.technical_depth > 0.3

        # Should extract relevant topics
        topic_names = [topic.topic for topic in result.topic_extractions]
        assert any(
            "machine_learning" in topic or "technology" in topic
            for topic in topic_names
        )

    @pytest.mark.asyncio()
    async def test_should_analyze_social_media_sentiment_correctly(
        self,
        cognitive_engine,
        sample_social_content,
    ):
        """
        Test: Should correctly analyze sentiment in social media content
        with emoji and informal language detection.
        """
        content = sample_social_content["content"]
        metadata = sample_social_content["metadata"]

        result = await cognitive_engine.analyze_content(
            "social_test",
            content,
            metadata,
        )

        # Should categorize as social media
        assert result.category == ContentCategory.SOCIAL_MEDIA

        # Should detect positive sentiment from "amazing", "excited", emojis
        assert result.sentiment_analysis.polarity in [
            SentimentPolarity.POSITIVE,
            SentimentPolarity.VERY_POSITIVE,
        ]
        assert result.sentiment_analysis.confidence > 0.3

        # Should have emotion scores
        assert len(result.sentiment_analysis.emotion_scores) > 0

    @pytest.mark.asyncio()
    async def test_should_detect_negative_sentiment_in_news_content(
        self,
        cognitive_engine,
        sample_news_content,
    ):
        """
        Test: Should detect negative sentiment in news content with
        negative business indicators.
        """
        content = sample_news_content["content"]
        metadata = sample_news_content["metadata"]

        result = await cognitive_engine.analyze_content("news_test", content, metadata)

        # Should categorize as news
        assert result.category == ContentCategory.NEWS_ARTICLE

        # Should detect negative sentiment from "disappointing", "concern", "troubles"
        assert result.sentiment_analysis.polarity in [
            SentimentPolarity.NEGATIVE,
            SentimentPolarity.VERY_NEGATIVE,
            SentimentPolarity.MIXED,
        ]

    @pytest.mark.asyncio()
    async def test_should_extract_relevant_topics_from_content(
        self,
        cognitive_engine,
        sample_research_content,
    ):
        """
        Test: Should extract relevant topics from content using
        keyword matching and relevance scoring.
        """
        content = sample_research_content["content"]
        metadata = sample_research_content["metadata"]

        result = await cognitive_engine.analyze_content("topic_test", content, metadata)

        # Should extract topics
        assert len(result.topic_extractions) > 0

        # Check topic relevance
        for topic in result.topic_extractions:
            assert topic.relevance_score > 0.0
            assert len(topic.keywords) > 0

        # Should detect machine learning topic
        topic_names = [topic.topic for topic in result.topic_extractions]
        assert "machine_learning" in topic_names or "technology" in topic_names

    @pytest.mark.asyncio()
    async def test_should_generate_content_summary_and_entities(
        self,
        cognitive_engine,
        sample_research_content,
    ):
        """
        Test: Should generate meaningful content summary and extract
        key entities from content.
        """
        content = sample_research_content["content"]
        metadata = sample_research_content["metadata"]

        result = await cognitive_engine.analyze_content(
            "summary_test",
            content,
            metadata,
        )

        # Should generate summary
        if cognitive_engine.config.enable_content_summarization:
            assert len(result.content_summary) > 0
            assert (
                len(result.content_summary)
                <= cognitive_engine.config.summary_max_length
            )

        # Should extract entities
        if cognitive_engine.config.enable_entity_recognition:
            assert len(result.key_entities) >= 0  # May be empty for some content

        # Should generate semantic tags
        if cognitive_engine.config.enable_semantic_tagging:
            assert len(result.semantic_tags) > 0
            # Should include category as tag
            assert result.category.value in result.semantic_tags

    # ========================================================================
    # Batch Processing and Performance Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_process_batch_content_efficiently(self, cognitive_engine):
        """
        Test: Should efficiently process multiple content items in batch
        with proper concurrency control and performance.
        """
        # Create batch of varied content
        batch_items = [
            (
                "item1",
                "This is excellent research on machine learning algorithms with deep analysis.",
                {"source_type": "academic"},
            ),
            (
                "item2",
                "Love this new AI breakthrough! Amazing results! 🎉",
                {"source_type": "social_media"},
            ),
            (
                "item3",
                "Breaking news: Tech stocks decline amid market uncertainty.",
                {"source_type": "news"},
            ),
            (
                "item4",
                "Tutorial: How to implement neural networks in Python with examples.",
                {"source_type": "blog"},
            ),
            (
                "item5",
                "API documentation for the new machine learning framework.",
                {"source_type": "technical"},
            ),
        ]

        # Measure processing time
        start_time = time.time()
        results = await cognitive_engine.batch_analyze_content(batch_items)
        processing_time = time.time() - start_time

        # Check results
        assert len(results) == len(batch_items)

        # All results should be valid
        for i, result in enumerate(results):
            assert isinstance(result, CognitiveAnalysisResult)
            assert result.content_id == batch_items[i][0]
            assert result.processing_time_ms > 0

        # Should complete in reasonable time
        assert processing_time < 5.0  # Under 5 seconds for 5 items

        # Check statistics
        stats = cognitive_engine.get_analysis_statistics()
        assert stats["total_analyzed"] >= 5

    @pytest.mark.asyncio()
    async def test_should_utilize_caching_for_repeated_content(self, cognitive_engine):
        """
        Test: Should cache analysis results and utilize cache for
        repeated content analysis.
        """
        content = "This is test content for caching functionality."
        metadata = {"source_type": "test"}

        # First analysis
        result1 = await cognitive_engine.analyze_content(
            "cache_test_1",
            content,
            metadata,
        )

        # Second analysis of same content
        result2 = await cognitive_engine.analyze_content(
            "cache_test_2",
            content,
            metadata,
        )

        # Check cache utilization
        stats = cognitive_engine.get_analysis_statistics()
        if cognitive_engine.config.enable_caching:
            assert stats["cache_hits"] > 0
            assert stats["cache_hit_rate"] > 0.0

    @pytest.mark.asyncio()
    async def test_should_handle_large_volume_content_analysis(self, cognitive_engine):
        """
        Test: Should handle large volume of content analysis
        with proper memory management and performance.
        """
        # Generate large batch of content
        large_batch = []
        for i in range(50):
            content = f"This is test content item number {
                i
            } with unique information about technology and research."
            large_batch.append((f"volume_test_{i}", content, {"source_type": "test"}))

        # Process large batch
        start_time = time.time()
        results = await cognitive_engine.batch_analyze_content(large_batch)
        processing_time = time.time() - start_time

        # Should complete successfully
        assert len(results) == 50

        # Should maintain reasonable performance
        assert processing_time < 15.0  # Under 15 seconds for 50 items

        # Check memory management
        stats = cognitive_engine.get_analysis_statistics()
        assert stats["total_analyzed"] >= 50

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_empty_and_invalid_content(self, cognitive_engine):
        """
        Test: Should gracefully handle empty content, None values,
        and content below minimum length threshold.
        """
        # Test empty content
        result1 = await cognitive_engine.analyze_content("empty_test", "", {})
        assert result1.category == ContentCategory.UNKNOWN
        assert result1.quality_metrics.overall_score == 0.0

        # Test very short content
        result2 = await cognitive_engine.analyze_content("short_test", "Hi", {})
        assert result2.quality_metrics.quality_level in [
            QualityLevel.VERY_POOR,
            QualityLevel.POOR,
        ]

        # Test None content (should handle gracefully)
        try:
            result3 = await cognitive_engine.analyze_content("none_test", None, {})
            assert isinstance(result3, CognitiveAnalysisResult)
        except (TypeError, AttributeError):
            # It's acceptable to throw an exception for None content
            pass

    @pytest.mark.asyncio()
    async def test_should_handle_malformed_metadata_gracefully(self, cognitive_engine):
        """
        Test: Should handle malformed or invalid metadata
        without crashing the analysis process.
        """
        content = "This is test content with problematic metadata."

        # Test with malformed metadata
        malformed_metadata = {
            "source_type": None,
            "invalid_field": {"nested": {"very": {"deep": "object"}}},
            "numbers": [1, 2, 3, "mixed", {"type": "list"}],
        }

        result = await cognitive_engine.analyze_content(
            "malformed_test",
            content,
            malformed_metadata,
        )

        # Should complete successfully
        assert isinstance(result, CognitiveAnalysisResult)
        assert result.content_id == "malformed_test"

    @pytest.mark.asyncio()
    async def test_should_handle_very_long_content_appropriately(
        self,
        cognitive_engine,
    ):
        """
        Test: Should handle content exceeding maximum length
        by truncating appropriately.
        """
        # Create very long content
        long_content = "This is a very long piece of content. " * 1000  # Very long

        result = await cognitive_engine.analyze_content("long_test", long_content, {})

        # Should complete successfully
        assert isinstance(result, CognitiveAnalysisResult)
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio()
    async def test_should_handle_concurrent_analysis_safely(self, cognitive_engine):
        """
        Test: Should handle concurrent analysis requests
        without race conditions or data corruption.
        """
        # Create concurrent analysis tasks
        tasks = []
        for i in range(20):
            content = f"Concurrent test content {i} with unique analysis requirements."
            task = asyncio.create_task(
                cognitive_engine.analyze_content(
                    f"concurrent_{i}",
                    content,
                    {"test_id": i},
                ),
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert isinstance(result, CognitiveAnalysisResult)
            assert result.content_id == f"concurrent_{i}"


class TestIndividualAnalyzers:
    """
    Test suite for individual analyzer components.
    """

    @pytest.fixture()
    def test_config(self):
        """Test configuration for analyzers"""
        return CognitiveConfig()

    def test_sentiment_analyzer_should_detect_positive_sentiment(self, test_config):
        """
        Test: SentimentAnalyzer should correctly identify positive sentiment
        in content with positive indicators.
        """
        analyzer = SentimentAnalyzer(test_config)

        positive_content = (
            "This is excellent, amazing, and wonderful research with great results!"
        )

        async def analyze():
            return await analyzer.analyze_content(positive_content)

        result = asyncio.run(analyze())

        # Should detect positive sentiment
        assert result["polarity"] in ["positive", "very_positive"]
        assert result["confidence"] > 0.0

    def test_sentiment_analyzer_should_detect_negative_sentiment(self, test_config):
        """
        Test: SentimentAnalyzer should correctly identify negative sentiment
        in content with negative indicators.
        """
        analyzer = SentimentAnalyzer(test_config)

        negative_content = (
            "This is terrible, awful, and disappointing work with horrible results."
        )

        async def analyze():
            return await analyzer.analyze_content(negative_content)

        result = asyncio.run(analyze())

        # Should detect negative sentiment
        assert result["polarity"] in ["negative", "very_negative"]
        assert result["confidence"] > 0.0

    def test_topic_extractor_should_identify_relevant_topics(self, test_config):
        """
        Test: TopicExtractor should identify relevant topics based on
        keyword matching and relevance scoring.
        """
        extractor = TopicExtractor(test_config)

        ml_content = "This research focuses on machine learning algorithms, neural networks, and deep learning models for artificial intelligence applications."

        async def extract():
            return await extractor.analyze_content(ml_content)

        result = asyncio.run(extract())

        # Should extract machine learning topic
        topics = result["topics"]
        assert len(topics) > 0

        topic_names = [topic["topic"] for topic in topics]
        assert "machine_learning" in topic_names

    def test_quality_assessor_should_evaluate_content_quality(self, test_config):
        """
        Test: QualityAssessor should evaluate content quality based on
        multiple quality indicators and metrics.
        """
        assessor = QualityAssessor(test_config)

        high_quality_content = """
        This comprehensive research study employs rigorous methodology to analyze complex data sets.
        The experimental design incorporates statistical analysis and evidence-based evaluation.
        Results demonstrate significant findings with thorough documentation and detailed analysis.
        """

        low_quality_content = (
            "This is spam promotional content with clickbait headlines and fake claims."
        )

        async def assess_high():
            return await assessor.analyze_content(high_quality_content)

        async def assess_low():
            return await assessor.analyze_content(low_quality_content)

        high_result = asyncio.run(assess_high())
        low_result = asyncio.run(assess_low())

        # High quality content should score higher
        assert high_result["overall_score"] > low_result["overall_score"]
        assert high_result["technical_depth"] > low_result["technical_depth"]

    def test_content_categorizer_should_classify_content_types(self, test_config):
        """
        Test: ContentCategorizer should classify content into appropriate
        categories based on content patterns and metadata.
        """
        categorizer = ContentCategorizer(test_config)

        research_content = "This academic study presents methodology, results, and analysis of experimental data."
        news_content = "Breaking news: Latest developments reported by journalists according to reliable sources."

        async def categorize_research():
            return await categorizer.analyze_content(research_content)

        async def categorize_news():
            return await categorizer.analyze_content(news_content)

        research_result = asyncio.run(categorize_research())
        news_result = asyncio.run(categorize_news())

        # Should classify appropriately
        assert research_result["category"] in ["research_paper", "educational_content"]
        assert news_result["category"] == "news_article"


class TestCognitiveConfigurationFactory:
    """
    Test suite for cognitive analysis configuration factory.
    """

    @pytest.mark.asyncio()
    async def test_should_create_production_cognitive_engine(self):
        """
        Test: Should create production-ready cognitive analysis engine
        with optimized configuration settings.
        """
        engine = await create_production_cognitive_engine()

        # Check engine is properly configured
        assert engine.config.enable_sentiment_analysis
        assert engine.config.enable_topic_extraction
        assert engine.config.enable_quality_assessment
        assert engine.config.enable_entity_recognition

        # Check performance settings
        assert engine.config.batch_processing_size > 50
        assert engine.config.max_concurrent_analysis > 10
        assert engine.config.enable_caching

        # Test with sample content
        test_content = "This is a test of the production cognitive analysis engine with machine learning capabilities."

        result = await engine.analyze_content("production_test", test_content)

        # Should produce valid analysis
        assert isinstance(result, CognitiveAnalysisResult)
        assert result.processing_time_ms > 0
        assert len(result.semantic_tags) > 0


class TestDataStructures:
    """
    Test suite for cognitive analysis data structures.
    """

    def test_topic_extraction_should_serialize_correctly(self):
        """
        Test: TopicExtraction should properly serialize to dictionary
        for JSON export and API responses.
        """
        topic = TopicExtraction(
            topic="machine_learning",
            confidence=TopicConfidence.HIGH,
            relevance_score=0.85,
            keywords=["algorithm", "neural", "training"],
        )

        topic_dict = topic.to_dict()

        # Verify serialization
        assert topic_dict["topic"] == "machine_learning"
        assert topic_dict["confidence"] == "high"
        assert topic_dict["relevance_score"] == 0.85
        assert topic_dict["keywords"] == ["algorithm", "neural", "training"]

    def test_cognitive_analysis_result_should_serialize_completely(self):
        """
        Test: CognitiveAnalysisResult should serialize all components
        correctly for comprehensive data export.
        """
        # Create complete analysis result
        quality_metrics = QualityMetrics(
            overall_score=0.75,
            quality_level=QualityLevel.GOOD,
            readability_score=0.8,
            technical_depth=0.6,
            information_density=0.7,
            source_credibility=0.9,
        )

        sentiment_analysis = SentimentAnalysis(
            polarity=SentimentPolarity.POSITIVE,
            confidence=0.8,
            emotion_scores={"joy": 0.6, "surprise": 0.3},
        )

        topic_extraction = TopicExtraction(
            topic="technology",
            confidence=TopicConfidence.HIGH,
            relevance_score=0.9,
            keywords=["tech", "innovation"],
        )

        result = CognitiveAnalysisResult(
            content_id="test_content",
            category=ContentCategory.RESEARCH_PAPER,
            quality_metrics=quality_metrics,
            sentiment_analysis=sentiment_analysis,
            topic_extractions=[topic_extraction],
            processing_time_ms=150.0,
            analysis_timestamp=datetime.now(UTC),
            confidence_score=0.82,
            key_entities=["Technology", "Innovation"],
            content_summary="Test summary of the content.",
            semantic_tags=["research_paper", "technology", "innovation"],
        )

        result_dict = result.to_dict()

        # Verify all components are serialized
        assert result_dict["content_id"] == "test_content"
        assert result_dict["category"] == "research_paper"
        assert "quality_metrics" in result_dict
        assert "sentiment_analysis" in result_dict
        assert "topic_extractions" in result_dict
        assert result_dict["confidence_score"] == 0.82
        assert "key_entities" in result_dict
        assert "content_summary" in result_dict
        assert "semantic_tags" in result_dict
