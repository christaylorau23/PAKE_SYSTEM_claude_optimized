"""
Comprehensive test suite for the intelligent content curation system.
Tests all components including models, services, ML pipeline, and API endpoints.
"""

from datetime import datetime, timedelta

import numpy as np
import pytest

from src.services.curation.integration.curation_orchestrator import (
    CurationOrchestrator,
    CurationRequest,
)
from src.services.curation.ml.feature_extractor import (
    FeatureExtractor,
)
from src.services.curation.ml.model_trainer import ModelTrainer
from src.services.curation.ml.prediction_engine import PredictionEngine
from src.services.curation.models.content_item import ContentItem
from src.services.curation.models.user_interaction import (
    InteractionType,
    UserInteraction,
)
from src.services.curation.models.user_profile import UserProfile
from src.services.curation.services.content_analysis_service import (
    ContentAnalysisService,
)
from src.services.curation.services.recommendation_service import RecommendationService
from src.services.curation.services.user_preference_service import UserPreferenceService


class TestContentItem:
    """Test ContentItem model"""

    def test_content_item_creation(self):
        """Test basic content item creation"""
        content = ContentItem(
            id="test-1",
            title="Test Article",
            content_text="This is a test article with some content.",
            author="Test Author",
            source_url="https://example.com/article",
            published_date=datetime.now(),
            content_type="article",
            tags=["test", "example"],
            quality_score=0.8,
            credibility_score=0.7,
        )

        assert content.id == "test-1"
        assert content.title == "Test Article"
        assert content.content_text == "This is a test article with some content."
        assert content.author == "Test Author"
        assert content.quality_score == 0.8
        assert content.credibility_score == 0.7
        assert "test" in content.tags
        assert "example" in content.tags

    def test_content_item_validation(self):
        """Test content item validation"""
        # Test with minimal required fields
        content = ContentItem(
            id="test-2",
            title="Minimal Article",
            content_text="Minimal content",
        )

        assert content.id == "test-2"
        assert content.title == "Minimal Article"
        assert content.content_text == "Minimal content"
        assert content.quality_score is None
        assert content.tags is None


class TestUserProfile:
    """Test UserProfile model"""

    def test_user_profile_creation(self):
        """Test basic user profile creation"""
        profile = UserProfile(
            user_id="user-1",
            interests=["AI", "Machine Learning", "Data Science"],
            preference_weights={
                "academic": 0.4,
                "news": 0.3,
                "blog": 0.2,
                "tutorial": 0.1,
            },
            learning_rate=0.1,
            exploration_factor=0.15,
        )

        assert profile.user_id == "user-1"
        assert "AI" in profile.interests
        assert "Machine Learning" in profile.interests
        assert profile.preference_weights["academic"] == 0.4
        assert profile.learning_rate == 0.1
        assert profile.exploration_factor == 0.15

    def test_user_profile_defaults(self):
        """Test user profile with default values"""
        profile = UserProfile(user_id="user-2")

        assert profile.user_id == "user-2"
        assert profile.interests == []
        assert profile.preference_weights == {}
        assert profile.learning_rate == 0.1
        assert profile.exploration_factor == 0.1


class TestUserInteraction:
    """Test UserInteraction model"""

    def test_user_interaction_creation(self):
        """Test basic user interaction creation"""
        interaction = UserInteraction(
            id="interaction-1",
            user_id="user-1",
            content_id="content-1",
            interaction_type=InteractionType.LIKE,
            timestamp=datetime.now(),
            session_duration=120,
            context={"page": "home", "source": "recommendation"},
        )

        assert interaction.id == "interaction-1"
        assert interaction.user_id == "user-1"
        assert interaction.content_id == "content-1"
        assert interaction.interaction_type == InteractionType.LIKE
        assert interaction.session_duration == 120
        assert interaction.context["page"] == "home"


class TestContentAnalysisService:
    """Test ContentAnalysisService"""

    @pytest.fixture
    async def analysis_service(self):
        """Create analysis service instance"""
        service = ContentAnalysisService()
        await service.initialize()
        return service

    @pytest.fixture
    def sample_content(self):
        """Create sample content for testing"""
        return ContentItem(
            id="test-content",
            title="Machine Learning in Healthcare",
            content_text="Machine learning is revolutionizing healthcare by enabling early disease detection, personalized treatment plans, and improved patient outcomes. Recent advances in deep learning have shown remarkable success in medical imaging analysis, drug discovery, and clinical decision support systems.",
            author="Dr. Jane Smith",
            source_url="https://example.com/ml-healthcare",
            published_date=datetime.now() - timedelta(days=5),
            content_type="article",
            tags=["machine learning", "healthcare", "AI", "medical"],
            source_authority_score=0.9,
            source_reliability=0.8,
        )

    @pytest.mark.asyncio
    async def test_content_analysis(self, analysis_service, sample_content):
        """Test content analysis functionality"""
        result = await analysis_service.analyze_content(sample_content)

        assert result is not None
        assert result.quality_score is not None
        assert 0.0 <= result.quality_score <= 1.0
        assert result.credibility_score is not None
        assert 0.0 <= result.credibility_score <= 1.0
        assert result.sentiment_score is not None
        assert -1.0 <= result.sentiment_score <= 1.0
        assert result.readability_score is not None
        assert 0.0 <= result.readability_score <= 1.0
        assert result.topic_categories is not None
        assert len(result.topic_categories) > 0

    @pytest.mark.asyncio
    async def test_batch_content_analysis(self, analysis_service):
        """Test batch content analysis"""
        contents = [
            ContentItem(
                id=f"test-{i}",
                title=f"Test Article {i}",
                content_text=f"This is test content {i} with some sample text for analysis.",
                author=f"Author {i}",
            )
            for i in range(5)
        ]

        results = await analysis_service.analyze_content_batch(contents)

        assert len(results) == 5
        for result in results:
            assert result.quality_score is not None
            assert result.credibility_score is not None


class TestRecommendationService:
    """Test RecommendationService"""

    @pytest.fixture
    async def recommendation_service(self):
        """Create recommendation service instance"""
        service = RecommendationService()
        await service.initialize()
        return service

    @pytest.fixture
    def sample_user_profile(self):
        """Create sample user profile"""
        return UserProfile(
            user_id="test-user",
            interests=["AI", "Machine Learning", "Data Science"],
            preference_weights={
                "academic": 0.4,
                "news": 0.3,
                "blog": 0.2,
                "tutorial": 0.1,
            },
        )

    @pytest.fixture
    def sample_content(self):
        """Create sample content"""
        return ContentItem(
            id="test-content",
            title="Advanced Machine Learning Techniques",
            content_text="This article covers advanced machine learning techniques including deep learning, reinforcement learning, and transfer learning.",
            tags=["machine learning", "AI", "deep learning"],
            quality_score=0.8,
            credibility_score=0.7,
        )

    @pytest.mark.asyncio
    async def test_generate_recommendation(
        self,
        recommendation_service,
        sample_user_profile,
        sample_content,
    ):
        """Test recommendation generation"""
        recommendation = await recommendation_service.generate_recommendation(
            content=sample_content,
            user_profile=sample_user_profile,
            relevance_score=0.85,
            confidence_score=0.9,
            reasoning="Matches user interests in AI and Machine Learning",
        )

        assert recommendation is not None
        assert recommendation.content_id == sample_content.id
        assert recommendation.user_id == sample_user_profile.user_id
        assert recommendation.relevance_score == 0.85
        assert recommendation.confidence_score == 0.9
        assert (
            recommendation.reasoning
            == "Matches user interests in AI and Machine Learning"
        )

    @pytest.mark.asyncio
    async def test_batch_recommendations(
        self,
        recommendation_service,
        sample_user_profile,
    ):
        """Test batch recommendation generation"""
        contents = [
            ContentItem(
                id=f"content-{i}",
                title=f"Article {i}",
                content_text=f"Content {i}",
                tags=["AI", "ML"] if i % 2 == 0 else ["Data", "Science"],
                quality_score=0.7 + (i * 0.05),
            )
            for i in range(5)
        ]

        recommendations = await recommendation_service.generate_batch_recommendations(
            contents=contents,
            user_profile=sample_user_profile,
            max_recommendations=3,
        )

        assert len(recommendations) <= 3
        for rec in recommendations:
            assert rec.user_id == sample_user_profile.user_id
            assert rec.relevance_score is not None
            assert rec.confidence_score is not None


class TestUserPreferenceService:
    """Test UserPreferenceService"""

    @pytest.fixture
    async def preference_service(self):
        """Create preference service instance"""
        service = UserPreferenceService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_create_user_profile(self, preference_service):
        """Test user profile creation"""
        profile = await preference_service.create_user_profile(
            user_id="test-user",
            interests=["AI", "ML"],
            preference_weights={"academic": 0.5, "news": 0.5},
            learning_rate=0.1,
            exploration_factor=0.1,
        )

        assert profile is not None
        assert profile.user_id == "test-user"
        assert "AI" in profile.interests
        assert profile.preference_weights["academic"] == 0.5

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, preference_service):
        """Test user preference updates"""
        # Create initial profile
        profile = await preference_service.create_user_profile(
            user_id="test-user-2",
            interests=["AI"],
            preference_weights={"academic": 0.5},
        )

        # Create interaction
        interaction = UserInteraction(
            id="interaction-1",
            user_id="test-user-2",
            content_id="content-1",
            interaction_type=InteractionType.LIKE,
            timestamp=datetime.now(),
        )

        # Update preferences
        updated_profile = await preference_service.update_user_preferences(
            "test-user-2",
            interaction,
        )

        assert updated_profile is not None
        assert updated_profile.user_id == "test-user-2"


class TestFeatureExtractor:
    """Test FeatureExtractor"""

    @pytest.fixture
    def feature_extractor(self):
        """Create feature extractor instance"""
        return FeatureExtractor()

    @pytest.fixture
    def sample_content(self):
        """Create sample content"""
        return ContentItem(
            id="test-content",
            title="Machine Learning Fundamentals",
            content_text="Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models. It enables computers to learn and make decisions from data without being explicitly programmed.",
            author="Dr. John Doe",
            source_url="https://example.com/ml-fundamentals",
            published_date=datetime.now() - timedelta(days=10),
            content_type="article",
            tags=["machine learning", "AI", "algorithms"],
            quality_score=0.8,
            credibility_score=0.7,
            view_count=1500,
            like_count=45,
            share_count=12,
        )

    @pytest.fixture
    def sample_user_profile(self):
        """Create sample user profile"""
        return UserProfile(
            user_id="test-user",
            interests=["AI", "Machine Learning", "Data Science"],
            preference_weights={
                "academic": 0.4,
                "news": 0.3,
                "blog": 0.2,
                "tutorial": 0.1,
            },
            learning_rate=0.1,
            exploration_factor=0.15,
        )

    @pytest.fixture
    def sample_interactions(self):
        """Create sample interactions"""
        return [
            UserInteraction(
                id="interaction-1",
                user_id="test-user",
                content_id="content-1",
                interaction_type=InteractionType.LIKE,
                timestamp=datetime.now() - timedelta(days=1),
                session_duration=180,
            ),
            UserInteraction(
                id="interaction-2",
                user_id="test-user",
                content_id="content-2",
                interaction_type=InteractionType.SHARE,
                timestamp=datetime.now() - timedelta(days=3),
                session_duration=240,
            ),
        ]

    @pytest.mark.asyncio
    async def test_extract_content_features(self, feature_extractor, sample_content):
        """Test content feature extraction"""
        features = await feature_extractor.extract_content_features(sample_content)

        assert features is not None
        assert features.content_id == sample_content.id
        assert features.text_features is not None
        assert features.metadata_features is not None
        assert features.semantic_features is not None
        assert features.quality_features is not None

        # Check specific features
        assert "text_length" in features.text_features
        assert "word_count" in features.text_features
        assert "source_authority_score" in features.metadata_features
        assert "content_age_days" in features.metadata_features
        assert "quality_score" in features.quality_features

    @pytest.mark.asyncio
    async def test_extract_user_features(
        self,
        feature_extractor,
        sample_user_profile,
        sample_interactions,
    ):
        """Test user feature extraction"""
        features = await feature_extractor.extract_user_features(
            sample_user_profile,
            sample_interactions,
        )

        assert features is not None
        assert features.user_id == sample_user_profile.user_id
        assert features.preference_features is not None
        assert features.behavioral_features is not None
        assert features.temporal_features is not None
        assert features.social_features is not None

        # Check specific features
        assert "learning_rate" in features.preference_features
        assert "like_count" in features.behavioral_features
        assert "share_count" in features.behavioral_features
        assert "avg_hour_of_day" in features.temporal_features

    @pytest.mark.asyncio
    async def test_get_feature_vector(
        self,
        feature_extractor,
        sample_content,
        sample_user_profile,
        sample_interactions,
    ):
        """Test feature vector generation"""
        content_features = await feature_extractor.extract_content_features(
            sample_content,
        )
        user_features = await feature_extractor.extract_user_features(
            sample_user_profile,
            sample_interactions,
        )

        feature_vector = await feature_extractor.get_feature_vector(
            content_features,
            user_features,
        )

        assert feature_vector is not None
        assert isinstance(feature_vector, np.ndarray)
        assert len(feature_vector) > 0
        assert not np.any(np.isnan(feature_vector))  # No NaN values


class TestModelTrainer:
    """Test ModelTrainer"""

    @pytest.fixture
    def model_trainer(self):
        """Create model trainer instance"""
        return ModelTrainer(models_dir="test_models")

    @pytest.fixture
    def sample_contents(self):
        """Create sample contents"""
        return [
            ContentItem(
                id=f"content-{i}",
                title=f"Article {i}",
                content_text=f"This is sample content {i} for testing machine learning models.",
                author=f"Author {i}",
                quality_score=0.5 + (i * 0.1),
                credibility_score=0.6 + (i * 0.05),
                tags=["AI", "ML"] if i % 2 == 0 else ["Data", "Science"],
            )
            for i in range(10)
        ]

    @pytest.fixture
    def sample_users(self):
        """Create sample users"""
        return [
            UserProfile(
                user_id=f"user-{i}",
                interests=["AI", "ML"] if i % 2 == 0 else ["Data", "Science"],
                preference_weights={
                    "academic": 0.4,
                    "news": 0.3,
                    "blog": 0.2,
                    "tutorial": 0.1,
                },
            )
            for i in range(5)
        ]

    @pytest.fixture
    def sample_interactions(self):
        """Create sample interactions"""
        interactions = []
        for i in range(20):
            interactions.append(
                UserInteraction(
                    id=f"interaction-{i}",
                    user_id=f"user-{i % 5}",
                    content_id=f"content-{i % 10}",
                    interaction_type=(
                        InteractionType.LIKE if i % 3 == 0 else InteractionType.VIEW
                    ),
                    timestamp=datetime.now() - timedelta(days=i),
                    session_duration=100 + (i * 10),
                ),
            )
        return interactions

    @pytest.mark.asyncio
    async def test_train_content_quality_model(
        self,
        model_trainer,
        sample_contents,
        sample_interactions,
    ):
        """Test content quality model training"""
        metrics = await model_trainer.train_content_quality_model(
            sample_contents,
            sample_interactions,
        )

        assert metrics is not None
        assert metrics.model_name == "content_quality"
        assert metrics.task_type == "regression"
        assert metrics.training_time > 0

    @pytest.mark.asyncio
    async def test_train_user_preference_model(
        self,
        model_trainer,
        sample_users,
        sample_interactions,
    ):
        """Test user preference model training"""
        metrics = await model_trainer.train_user_preference_model(
            sample_users,
            sample_interactions,
        )

        assert metrics is not None
        assert metrics.model_name == "user_preference"
        assert metrics.task_type == "classification"
        assert metrics.training_time > 0

    @pytest.mark.asyncio
    async def test_predict_content_quality(self, model_trainer, sample_contents):
        """Test content quality prediction"""
        # Train model first
        await model_trainer.train_content_quality_model(sample_contents, [])

        # Test prediction
        content = sample_contents[0]
        prediction = await model_trainer.predict_content_quality(content)

        assert prediction is not None
        assert 0.0 <= prediction <= 1.0


class TestPredictionEngine:
    """Test PredictionEngine"""

    @pytest.fixture
    def prediction_engine(self):
        """Create prediction engine instance"""
        return PredictionEngine(cache_size=100, cache_ttl_hours=1)

    @pytest.fixture
    def sample_content(self):
        """Create sample content"""
        return ContentItem(
            id="test-content",
            title="AI and Machine Learning",
            content_text="Artificial intelligence and machine learning are transforming industries worldwide.",
            author="Dr. Smith",
            quality_score=0.8,
            credibility_score=0.7,
            tags=["AI", "ML"],
        )

    @pytest.fixture
    def sample_user_profile(self):
        """Create sample user profile"""
        return UserProfile(
            user_id="test-user",
            interests=["AI", "ML"],
            preference_weights={"academic": 0.5, "news": 0.5},
        )

    @pytest.fixture
    def sample_interactions(self):
        """Create sample interactions"""
        return [
            UserInteraction(
                id="interaction-1",
                user_id="test-user",
                content_id="content-1",
                interaction_type=InteractionType.LIKE,
                timestamp=datetime.now() - timedelta(days=1),
            ),
        ]

    @pytest.mark.asyncio
    async def test_predict_content_quality(self, prediction_engine, sample_content):
        """Test content quality prediction"""
        result = await prediction_engine.predict_content_quality(sample_content)

        assert result is not None
        assert result.content_id == sample_content.id
        assert result.prediction_type == "quality"
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.prediction_time_ms > 0

    @pytest.mark.asyncio
    async def test_predict_user_preference(
        self,
        prediction_engine,
        sample_user_profile,
        sample_interactions,
    ):
        """Test user preference prediction"""
        result = await prediction_engine.predict_user_preference(
            sample_user_profile,
            sample_interactions,
        )

        assert result is not None
        assert result.user_id == sample_user_profile.user_id
        assert result.prediction_type == "preference"
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_predict_recommendation_score(
        self,
        prediction_engine,
        sample_content,
        sample_user_profile,
        sample_interactions,
    ):
        """Test recommendation score prediction"""
        result = await prediction_engine.predict_recommendation_score(
            sample_content,
            sample_user_profile,
            sample_interactions,
        )

        assert result is not None
        assert result.content_id == sample_content.id
        assert result.user_id == sample_user_profile.user_id
        assert result.prediction_type == "recommendation"
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_prediction_caching(self, prediction_engine, sample_content):
        """Test prediction caching functionality"""
        # First prediction (not cached)
        result1 = await prediction_engine.predict_content_quality(sample_content)
        assert not result1.cached

        # Second prediction (should be cached)
        result2 = await prediction_engine.predict_content_quality(sample_content)
        assert result2.cached
        assert result2.score == result1.score

    def test_performance_stats(self, prediction_engine):
        """Test performance statistics"""
        stats = prediction_engine.get_performance_stats()

        assert "total_predictions" in stats
        assert "cached_predictions" in stats
        assert "cache_hit_rate" in stats
        assert "avg_prediction_time_ms" in stats
        assert "cache_size" in stats


class TestCurationOrchestrator:
    """Test CurationOrchestrator"""

    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator instance"""
        orch = CurationOrchestrator()
        await orch.initialize()
        return orch

    @pytest.fixture
    def sample_request(self):
        """Create sample curation request"""
        return CurationRequest(
            user_id="test-user",
            query="machine learning",
            interests=["AI", "ML"],
            max_results=10,
            include_explanations=True,
        )

    @pytest.mark.asyncio
    async def test_curation_request(self, orchestrator, sample_request):
        """Test curation request processing"""
        response = await orchestrator.curate_content(sample_request)

        assert response is not None
        assert response.request_id is not None
        assert response.user_id == sample_request.user_id
        assert response.recommendations is not None
        assert response.processing_time_ms >= 0
        assert response.cache_hit_rate >= 0
        assert response.model_confidence >= 0

    @pytest.mark.asyncio
    async def test_process_user_feedback(self, orchestrator):
        """Test user feedback processing"""
        success = await orchestrator.process_user_feedback(
            user_id="test-user",
            content_id="test-content",
            feedback_type="like",
            feedback_data={"session_duration": 120},
        )

        assert success is not None

    @pytest.mark.asyncio
    async def test_system_health(self, orchestrator):
        """Test system health check"""
        health = await orchestrator.get_system_health()

        assert health is not None
        assert "services_healthy" in health.__dict__
        assert "models_loaded" in health.__dict__
        assert "cache_status" in health.__dict__
        assert "performance_metrics" in health.__dict__


# Integration tests


class TestCurationSystemIntegration:
    """Integration tests for the complete curation system"""

    @pytest.mark.asyncio
    async def test_end_to_end_curation_flow(self):
        """Test complete end-to-end curation flow"""
        # Initialize orchestrator
        orchestrator = CurationOrchestrator()
        await orchestrator.initialize()

        # Create test data
        contents = [
            ContentItem(
                id=f"content-{i}",
                title=f"AI Article {i}",
                content_text=f"This is article {i} about artificial intelligence and machine learning.",
                author=f"Author {i}",
                tags=["AI", "ML"],
                quality_score=0.7 + (i * 0.05),
            )
            for i in range(5)
        ]

        user_profile = UserProfile(
            user_id="integration-test-user",
            interests=["AI", "ML"],
            preference_weights={"academic": 0.5, "news": 0.5},
        )

        interactions = [
            UserInteraction(
                id=f"interaction-{i}",
                user_id="integration-test-user",
                content_id=f"content-{i}",
                interaction_type=InteractionType.LIKE,
                timestamp=datetime.now() - timedelta(days=i),
            )
            for i in range(3)
        ]

        # Test content analysis
        analysis_service = ContentAnalysisService()
        await analysis_service.initialize()

        analyzed_contents = await analysis_service.analyze_content_batch(contents)
        assert len(analyzed_contents) == 5

        # Test recommendation generation
        recommendation_service = RecommendationService()
        await recommendation_service.initialize()

        recommendations = []
        for content in analyzed_contents:
            rec = await recommendation_service.generate_recommendation(
                content=content,
                user_profile=user_profile,
                relevance_score=0.8,
                confidence_score=0.9,
            )
            recommendations.append(rec)

        assert len(recommendations) == 5

        # Test feature extraction
        feature_extractor = FeatureExtractor()

        content_features = await feature_extractor.extract_content_features(contents[0])
        user_features = await feature_extractor.extract_user_features(
            user_profile,
            interactions,
        )

        assert content_features is not None
        assert user_features is not None

        # Test prediction engine
        prediction_engine = PredictionEngine()

        prediction = await prediction_engine.predict_recommendation_score(
            contents[0],
            user_profile,
            interactions,
        )

        assert prediction is not None
        assert 0.0 <= prediction.score <= 1.0

        # Cleanup
        await orchestrator.shutdown()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
