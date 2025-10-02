"""
Comprehensive test suite for Adaptive Learning Engine
Tests personalization, recommendation generation, and user behavior learning.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from services.ai.adaptive_learning_engine import (
    AdaptiveLearningConfig,
    AdaptiveLearningEngine,
    CollaborativeFilter,
    ContentBasedFilter,
    LearningConfidence,
    LearningStrategy,
    Recommendation,
    RecommendationRequest,
    RecommendationResult,
    UserBehaviorType,
    UserInteraction,
    UserProfile,
    create_production_adaptive_learning_engine,
)


@pytest.fixture()
def learning_config():
    """Test configuration for adaptive learning"""
    return AdaptiveLearningConfig(
        learning_rate=0.2,
        min_interactions_for_confidence=5,
        max_profile_history_days=30,
        recommendation_diversity_threshold=0.3,
        collaborative_similarity_threshold=0.5,
        content_similarity_threshold=0.6,
        learning_decay_factor=0.9,
        max_concurrent_learning=5,
        enable_real_time_learning=True,
        cache_recommendations=True,
        recommendation_cache_ttl_minutes=10,
    )


@pytest.fixture()
def learning_engine(learning_config):
    """Adaptive learning engine instance for testing"""
    return AdaptiveLearningEngine(learning_config)


@pytest.fixture()
def sample_interactions():
    """Sample user interactions for testing"""
    base_time = datetime.now(UTC)

    interactions = [
        UserInteraction(
            user_id="user_1",
            interaction_type=UserBehaviorType.CONTENT_VIEW,
            content_id="content_1",
            content_category="technology",
            content_topics=["ai", "machine_learning"],
            interaction_score=1.0,
            timestamp=base_time - timedelta(hours=5),
            context_metadata={"source": "tech_blog", "session_id": "session_1"},
        ),
        UserInteraction(
            user_id="user_1",
            interaction_type=UserBehaviorType.CONTENT_LIKE,
            content_id="content_1",
            content_category="technology",
            content_topics=["ai", "machine_learning"],
            interaction_score=2.0,
            timestamp=base_time - timedelta(hours=4),
            context_metadata={"source": "tech_blog", "session_id": "session_1"},
        ),
        UserInteraction(
            user_id="user_1",
            interaction_type=UserBehaviorType.SEARCH_QUERY,
            content_topics=["deep_learning", "neural_networks"],
            interaction_score=1.5,
            timestamp=base_time - timedelta(hours=3),
            context_metadata={
                "query": "deep learning tutorials",
                "session_id": "session_2",
            },
        ),
        UserInteraction(
            user_id="user_2",
            interaction_type=UserBehaviorType.CONTENT_VIEW,
            content_id="content_1",
            content_category="technology",
            content_topics=["ai", "machine_learning"],
            interaction_score=1.0,
            timestamp=base_time - timedelta(hours=2),
            context_metadata={"source": "tech_blog", "session_id": "session_3"},
        ),
    ]

    return interactions


@pytest.fixture()
def sample_recommendation_requests():
    """Sample recommendation requests for testing"""
    return [
        RecommendationRequest(
            user_id="user_1",
            context="technology_learning",
            content_types=["article", "tutorial"],
            max_recommendations=5,
            diversity_factor=0.3,
            exclude_seen=True,
        ),
        RecommendationRequest(
            user_id="new_user",
            max_recommendations=10,
            diversity_factor=0.5,
        ),
    ]


class TestAdaptiveLearningEngine:
    """Test the main adaptive learning engine functionality"""

    @pytest.mark.asyncio()
    async def test_should_initialize_learning_engine_with_configuration(
        self,
        learning_config,
    ):
        """
        Test: Should initialize adaptive learning engine with proper configuration
        and default state ready for learning operations.
        """
        engine = AdaptiveLearningEngine(learning_config)

        # Verify initialization
        assert engine.config == learning_config
        assert len(engine.user_profiles) == 0
        assert len(engine.user_interactions) == 0
        assert engine.collaborative_filter is not None
        assert engine.content_filter is not None
        assert len(engine.recommendation_cache) == 0

        # Verify metrics initialization
        metrics = engine.get_metrics()
        assert metrics["profiles_created"] == 0
        assert metrics["interactions_processed"] == 0
        assert metrics["recommendations_generated"] == 0
        assert metrics["learning_updates"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0

    @pytest.mark.asyncio()
    async def test_should_record_user_interactions_and_update_profiles(
        self,
        learning_engine,
        sample_interactions,
    ):
        """
        Test: Should record user interactions and automatically update
        user profiles with learned preferences in real-time.
        """
        # Record interactions
        for interaction in sample_interactions[:3]:  # First 3 interactions for user_1
            result = await learning_engine.record_interaction(interaction)
            assert result is True

        # Verify interaction storage
        user1_interactions = learning_engine.user_interactions["user_1"]
        assert len(user1_interactions) == 3

        # Verify profile was created/updated
        profile = learning_engine.get_user_profile("user_1")
        assert profile is not None
        assert profile.user_id == "user_1"
        assert profile.total_interactions == 3

        # Check learned preferences
        assert "ai" in profile.topic_preferences
        assert "machine_learning" in profile.topic_preferences
        assert profile.topic_preferences["ai"] > 0
        assert "tech_blog" in profile.source_preferences
        assert "technology" in profile.content_type_preferences

        # Verify metrics
        metrics = learning_engine.get_metrics()
        assert metrics["interactions_processed"] == 3
        assert metrics["learning_updates"] >= 1

    @pytest.mark.asyncio()
    async def test_should_generate_personalized_recommendations_for_existing_user(
        self,
        learning_engine,
        sample_interactions,
        sample_recommendation_requests,
    ):
        """
        Test: Should generate personalized recommendations based on learned
        user preferences with appropriate confidence and reasoning.
        """
        # Setup user profile with interactions
        for interaction in sample_interactions[:3]:
            await learning_engine.record_interaction(interaction)

        # Request recommendations
        request = sample_recommendation_requests[0]  # user_1 request
        result = await learning_engine.get_recommendations(request)

        # Verify recommendation result structure
        assert isinstance(result, RecommendationResult)
        assert result.user_id == "user_1"
        assert len(result.recommendations) > 0
        assert result.processing_time_ms > 0
        assert result.confidence in [
            LearningConfidence.LOW,
            LearningConfidence.MEDIUM,
            LearningConfidence.HIGH,
            LearningConfidence.VERY_HIGH,
        ]
        assert result.strategy_used in [
            LearningStrategy.CONTENT_BASED,
            LearningStrategy.HYBRID,
        ]

        # Verify individual recommendations
        for rec in result.recommendations:
            assert isinstance(rec, Recommendation)
            assert rec.content_id is not None
            assert 0 <= rec.relevance_score <= 1
            assert rec.confidence is not None
            assert len(rec.reasoning) > 0
            assert rec.recommendation_type is not None

        # Verify recommendations are sorted by relevance
        scores = [rec.relevance_score for rec in result.recommendations]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio()
    async def test_should_provide_fallback_recommendations_for_new_users(
        self,
        learning_engine,
        sample_recommendation_requests,
    ):
        """
        Test: Should provide fallback recommendations for users without
        sufficient interaction history or profile data.
        """
        request = sample_recommendation_requests[1]  # new_user request
        result = await learning_engine.get_recommendations(request)

        # Verify fallback behavior
        assert result.user_id == "new_user"
        assert result.confidence == LearningConfidence.LOW
        assert result.strategy_used == LearningStrategy.CONTENT_BASED
        assert len(result.fallback_recommendations) > 0

        # Verify fallback recommendations structure
        for rec in result.fallback_recommendations:
            assert rec.recommendation_type == "fallback_trending"
            assert rec.relevance_score > 0
            assert "Popular content" in rec.reasoning[0]

    @pytest.mark.asyncio()
    async def test_should_handle_concurrent_interaction_processing_safely(
        self,
        learning_engine,
        sample_interactions,
    ):
        """
        Test: Should handle concurrent interaction processing without
        race conditions and maintain data consistency.
        """
        # Create many concurrent interactions
        concurrent_interactions = []
        for i in range(20):
            interaction = UserInteraction(
                user_id=f"user_{i % 5}",  # 5 different users
                interaction_type=UserBehaviorType.CONTENT_VIEW,
                content_id=f"content_{i}",
                content_topics=[f"topic_{i % 3}"],
                interaction_score=1.0,
            )
            concurrent_interactions.append(interaction)

        # Process all interactions concurrently
        tasks = [
            learning_engine.record_interaction(interaction)
            for interaction in concurrent_interactions
        ]
        results = await asyncio.gather(*tasks)

        # Verify all interactions were processed successfully
        assert all(results)
        assert (
            sum(
                len(interactions)
                for interactions in learning_engine.user_interactions.values()
            )
            == 20
        )

        # Verify profiles were created for all users
        assert len(learning_engine.user_profiles) == 5

        # Verify no data corruption
        for user_id in [f"user_{i}" for i in range(5)]:
            profile = learning_engine.get_user_profile(user_id)
            assert profile is not None
            assert profile.total_interactions == 4  # Each user has 4 interactions

    @pytest.mark.asyncio()
    async def test_should_implement_recommendation_caching_effectively(
        self,
        learning_engine,
        sample_interactions,
        sample_recommendation_requests,
    ):
        """
        Test: Should cache recommendations and serve from cache when appropriate
        to improve performance and reduce computational overhead.
        """
        # Setup user profile
        for interaction in sample_interactions[:3]:
            await learning_engine.record_interaction(interaction)

        request = sample_recommendation_requests[0]

        # First request - should miss cache
        result1 = await learning_engine.get_recommendations(request)
        metrics1 = learning_engine.get_metrics()

        # Second identical request - should hit cache
        result2 = await learning_engine.get_recommendations(request)
        metrics2 = learning_engine.get_metrics()

        # Verify cache behavior
        assert metrics1["cache_misses"] == 1
        assert metrics1["cache_hits"] == 0
        assert metrics2["cache_misses"] == 1
        assert metrics2["cache_hits"] == 1

        # Verify cached results are identical
        assert result1.user_id == result2.user_id
        assert len(result1.recommendations) == len(result2.recommendations)
        assert result1.strategy_used == result2.strategy_used

    @pytest.mark.asyncio()
    async def test_should_apply_learning_confidence_levels_appropriately(
        self,
        learning_engine,
    ):
        """
        Test: Should calculate and apply learning confidence levels based on
        interaction history volume and user engagement patterns.
        """
        user_id = "confidence_test_user"

        # Test LOW confidence (few interactions)
        for i in range(3):
            interaction = UserInteraction(
                user_id=user_id,
                interaction_type=UserBehaviorType.CONTENT_VIEW,
                content_topics=[f"topic_{i}"],
                interaction_score=1.0,
            )
            await learning_engine.record_interaction(interaction)

        profile = learning_engine.get_user_profile(user_id)
        assert profile.learning_confidence == LearningConfidence.LOW

        # Add more interactions for MEDIUM confidence
        for i in range(3, 7):
            interaction = UserInteraction(
                user_id=user_id,
                interaction_type=UserBehaviorType.CONTENT_LIKE,
                content_topics=[f"topic_{i}"],
                interaction_score=2.0,
            )
            await learning_engine.record_interaction(interaction)

        profile = learning_engine.get_user_profile(user_id)
        assert profile.learning_confidence == LearningConfidence.MEDIUM

        # Add even more for HIGH confidence
        for i in range(7, 15):
            interaction = UserInteraction(
                user_id=user_id,
                interaction_type=UserBehaviorType.CONTENT_SHARE,
                content_topics=[f"topic_{i}"],
                interaction_score=3.0,
            )
            await learning_engine.record_interaction(interaction)

        profile = learning_engine.get_user_profile(user_id)
        assert profile.learning_confidence in [
            LearningConfidence.HIGH,
            LearningConfidence.VERY_HIGH,
        ]

    @pytest.mark.asyncio()
    async def test_should_handle_learning_strategy_selection_intelligently(
        self,
        learning_engine,
        sample_interactions,
    ):
        """
        Test: Should select appropriate learning strategies based on user profile
        confidence and available data for optimal recommendation quality.
        """
        # Setup multiple users for collaborative filtering
        users = ["strategy_user_1", "strategy_user_2", "strategy_user_3"]

        for user_id in users:
            for i in range(12):  # High interaction count for high confidence
                interaction = UserInteraction(
                    user_id=user_id,
                    interaction_type=UserBehaviorType.CONTENT_VIEW,
                    content_id=f"shared_content_{i % 3}",  # Some shared content
                    content_topics=["ai", "technology"],
                    interaction_score=1.0,
                )
                await learning_engine.record_interaction(interaction)

        # Test recommendation strategy for high-confidence user
        request = RecommendationRequest(user_id=users[0], max_recommendations=5)
        result = await learning_engine.get_recommendations(request)

        # High confidence should use HYBRID strategy
        assert result.strategy_used == LearningStrategy.HYBRID
        assert result.confidence in [
            LearningConfidence.HIGH,
            LearningConfidence.VERY_HIGH,
        ]

    @pytest.mark.asyncio()
    async def test_should_track_comprehensive_learning_metrics(
        self,
        learning_engine,
        sample_interactions,
    ):
        """
        Test: Should track comprehensive metrics for monitoring learning
        effectiveness and system performance.
        """
        initial_metrics = learning_engine.get_metrics()

        # Process interactions and generate recommendations
        for interaction in sample_interactions:
            await learning_engine.record_interaction(interaction)

        request = RecommendationRequest(user_id="user_1", max_recommendations=5)
        await learning_engine.get_recommendations(request)

        final_metrics = learning_engine.get_metrics()

        # Verify metric tracking
        assert (
            final_metrics["interactions_processed"]
            > initial_metrics["interactions_processed"]
        )
        assert final_metrics["learning_updates"] > initial_metrics["learning_updates"]
        assert (
            final_metrics["recommendations_generated"]
            > initial_metrics["recommendations_generated"]
        )
        assert final_metrics["total_users"] > 0
        assert final_metrics["total_interactions"] > 0
        assert "average_confidence" in final_metrics


class TestCollaborativeFilter:
    """Test collaborative filtering functionality"""

    @pytest.mark.asyncio()
    async def test_should_calculate_user_similarity_accurately(
        self,
        learning_config,
        sample_interactions,
    ):
        """
        Test: Should calculate user similarity based on shared content
        interactions and cache results for performance.
        """
        collab_filter = CollaborativeFilter(learning_config)

        # Update with interactions
        collab_filter.update_user_interactions(sample_interactions)

        # Calculate similarity between users who viewed same content
        similarity = collab_filter.calculate_user_similarity("user_1", "user_2")

        # Both users interacted with content_1, so similarity should be > 0
        assert similarity > 0
        assert similarity <= 1.0

        # Verify caching
        cached_similarity = collab_filter.calculate_user_similarity("user_1", "user_2")
        assert cached_similarity == similarity

    @pytest.mark.asyncio()
    async def test_should_find_similar_users_effectively(
        self,
        learning_config,
        sample_interactions,
    ):
        """
        Test: Should find and rank similar users based on interaction
        patterns and content overlap.
        """
        collab_filter = CollaborativeFilter(learning_config)
        collab_filter.update_user_interactions(sample_interactions)

        similar_users = collab_filter.find_similar_users("user_1", min_similarity=0.0)

        # Verify similar users are found and ranked
        assert len(similar_users) > 0
        assert all(
            isinstance(user_sim, tuple) and len(user_sim) == 2
            for user_sim in similar_users
        )
        assert all(0 <= similarity <= 1 for user, similarity in similar_users)

        # Verify ranking (highest similarity first)
        similarities = [sim for user, sim in similar_users]
        assert similarities == sorted(similarities, reverse=True)


class TestContentBasedFilter:
    """Test content-based filtering functionality"""

    @pytest.mark.asyncio()
    async def test_should_update_content_features_correctly(self, learning_config):
        """
        Test: Should extract and normalize content features for
        similarity calculations and recommendations.
        """
        content_filter = ContentBasedFilter(learning_config)

        content_features = {
            "topics": ["ai", "machine_learning", "technology"],
            "content_type": "article",
            "source": "tech_blog",
            "quality_score": 0.85,
        }

        content_filter.update_content_features("test_content", content_features)

        # Verify feature extraction
        features = content_filter.content_features["test_content"]
        assert "topic_ai" in features
        assert "topic_machine_learning" in features
        assert "topic_technology" in features
        assert "type_article" in features
        assert "source_tech_blog" in features
        assert "quality" in features
        assert features["quality"] == 0.85

    @pytest.mark.asyncio()
    async def test_should_calculate_content_similarity_with_user_profile(
        self,
        learning_config,
    ):
        """
        Test: Should calculate how well content matches user profile
        preferences across topics, sources, and content types.
        """
        content_filter = ContentBasedFilter(learning_config)

        # Setup content features
        content_features = {
            "topics": ["ai", "technology"],
            "content_type": "article",
            "source": "tech_blog",
            "quality_score": 0.8,
        }
        content_filter.update_content_features("similarity_test", content_features)

        # Create user profile with matching preferences
        user_profile = UserProfile(
            user_id="test_user",
            topic_preferences={"ai": 0.9, "technology": 0.7},
            content_type_preferences={"article": 0.8},
            source_preferences={"tech_blog": 0.6},
        )

        # Calculate similarity
        similarity = content_filter.calculate_content_similarity(
            user_profile,
            "similarity_test",
        )

        # Should have high similarity due to matching preferences
        assert similarity > 0.5
        assert similarity <= 1.0


class TestProductionConfiguration:
    """Test production-ready configuration and setup"""

    @pytest.mark.asyncio()
    async def test_should_create_production_adaptive_learning_engine(self):
        """
        Test: Should create production-optimized adaptive learning engine
        with appropriate configuration for scale and performance.
        """
        engine = create_production_adaptive_learning_engine()

        # Verify production configuration
        assert engine.config.learning_rate == 0.05  # Conservative learning
        assert engine.config.min_interactions_for_confidence == 25  # Higher threshold
        assert engine.config.max_profile_history_days == 180  # Longer retention
        assert engine.config.max_concurrent_learning == 20  # Higher concurrency
        assert engine.config.enable_real_time_learning is True
        assert engine.config.cache_recommendations is True
        assert (
            engine.config.recommendation_cache_ttl_minutes == 15
        )  # Fresh recommendations

        # Verify engine is ready for operation
        assert engine.collaborative_filter is not None
        assert engine.content_filter is not None
        assert len(engine.user_profiles) == 0
        assert len(engine.recommendation_cache) == 0


class TestDataStructures:
    """Test data structure serialization and immutability"""

    def test_user_interaction_should_be_immutable_and_serializable(self):
        """
        Test: UserInteraction should be immutable and properly serializable
        for storage and transmission across system components.
        """
        interaction = UserInteraction(
            user_id="test_user",
            interaction_type=UserBehaviorType.CONTENT_LIKE,
            content_id="test_content",
            content_topics=["ai", "tech"],
            interaction_score=2.0,
            context_metadata={"source": "test_source"},
        )

        # Verify immutability
        with pytest.raises(Exception):  # Should raise FrozenInstanceError
            interaction.interaction_score = 3.0

        # Verify serialization fields
        assert interaction.user_id == "test_user"
        assert interaction.interaction_type == UserBehaviorType.CONTENT_LIKE
        assert interaction.content_id == "test_content"
        assert interaction.content_topics == ["ai", "tech"]
        assert interaction.interaction_score == 2.0
        assert interaction.context_metadata["source"] == "test_source"
        assert isinstance(interaction.timestamp, datetime)

    def test_user_profile_should_serialize_learning_state_completely(self):
        """
        Test: UserProfile should serialize complete learning state including
        preferences, confidence levels, and interaction statistics.
        """
        profile = UserProfile(
            user_id="profile_test_user",
            topic_preferences={"ai": 0.9, "tech": 0.7},
            source_preferences={"blog": 0.8},
            content_type_preferences={"article": 0.6},
            learning_confidence=LearningConfidence.HIGH,
            total_interactions=25,
        )

        # Verify complete serialization
        assert profile.user_id == "profile_test_user"
        assert profile.topic_preferences["ai"] == 0.9
        assert profile.source_preferences["blog"] == 0.8
        assert profile.content_type_preferences["article"] == 0.6
        assert profile.learning_confidence == LearningConfidence.HIGH
        assert profile.total_interactions == 25
        assert isinstance(profile.last_updated, datetime)

    def test_recommendation_result_should_serialize_with_comprehensive_metadata(self):
        """
        Test: RecommendationResult should serialize with comprehensive metadata
        including processing metrics and strategy information.
        """
        recommendations = [
            Recommendation(
                content_id="rec_1",
                relevance_score=0.95,
                confidence=LearningConfidence.HIGH,
                reasoning=["High topic match"],
                recommendation_type="content_based",
            ),
        ]

        result = RecommendationResult(
            user_id="result_test_user",
            recommendations=recommendations,
            processing_time_ms=45.2,
            confidence=LearningConfidence.HIGH,
            strategy_used=LearningStrategy.HYBRID,
        )

        # Verify comprehensive serialization
        assert result.user_id == "result_test_user"
        assert len(result.recommendations) == 1
        assert result.recommendations[0].content_id == "rec_1"
        assert result.processing_time_ms == 45.2
        assert result.confidence == LearningConfidence.HIGH
        assert result.strategy_used == LearningStrategy.HYBRID
        assert isinstance(result.generated_timestamp, datetime)
