"""Curation Orchestrator
Integration layer that connects the intelligent content curation system with the existing PAKE system.
Provides unified API for content discovery, analysis, and recommendation.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, List
import uuid

import asyncpg
import psycopg2
import sqlalchemy

from ..ml.feature_extractor import FeatureExtractor
from ..ml.model_trainer import ModelTrainer
from ..ml.prediction_engine import PredictionEngine
from ..models.content_item import ContentItem
from ..models.recommendation import Recommendation
from ..models.user_interaction import UserInteraction
from ..models.user_profile import UserProfile
from ..services.content_analysis_service import ContentAnalysisService
from ..services.feedback_processing_service import FeedbackProcessingService
from ..services.recommendation_service import RecommendationService
from ..services.user_preference_service import UserPreferenceService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CurationRequest:
    """Request for content curation."""

    user_id: str
    query: str | None = None
    interests: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    max_results: int = 20
    include_explanations: bool = True
    freshness_days: int = 30
    min_quality_score: float = 0.3
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class CurationResponse:
    """Response from content curation."""

    request_id: str
    user_id: str
    recommendations: list[Recommendation]
    total_content_analyzed: int
    processing_time_ms: float
    cache_hit_rate: float
    model_confidence: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class SystemHealth:
    """System health status."""

    services_healthy: dict[str, bool]
    models_loaded: dict[str, bool]
    cache_status: dict[str, Any]
    performance_metrics: dict[str, float]
    last_updated: datetime = field(default_factory=datetime.now)


class CurationOrchestrator:
    """Main orchestrator for intelligent content curation system."""

    def __init__(self) -> None:
        # Initialize services
        self.content_analysis_service = ContentAnalysisService()
        self.recommendation_service = RecommendationService()
        self.user_preference_service = UserPreferenceService()
        self.feedback_processing_service = FeedbackProcessingService()

        # Initialize ML components
        self.feature_extractor = FeatureExtractor()
        self.model_trainer = ModelTrainer()
        self.prediction_engine = PredictionEngine()

        # System state
        self.is_initialized = False
        self.models_trained = False
        self.last_model_update = None

        logger.info("CurationOrchestrator initialized")

    async def initialize(self) -> bool:
        """Initialize the curation system."""
        logger.info("Initializing curation system")

        try:
            # Load pre-trained models
            loaded_models = await self.model_trainer.load_models()
            self.models_trained = any(loaded_models.values())

            if not self.models_trained:
                logger.warning(
                    "No pre-trained models found. System will use fallback strategies.",
                )

            # Initialize services
            await self.content_analysis_service.initialize()
            await self.recommendation_service.initialize()
            await self.user_preference_service.initialize()
            await self.feedback_processing_service.initialize()

            self.is_initialized = True
            logger.info("Curation system initialized successfully")
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Error initializing curation system: %s", e)
            return False

    async def curate_content(self, request: CurationRequest) -> CurationResponse:
        """Main curation endpoint - discover and recommend content."""
        if not self.is_initialized:
            await self.initialize()

        start_time = datetime.now(UTC)
        request_id = str(uuid.uuid4())

        logger.info(
            "Processing curation request %s for user %s",
            request_id,
            request.user_id,
        )

        try:
            # Get or create user profile
            user_profile = await self._get_user_profile(request.user_id)

            # Get user interactions for personalization
            user_interactions = await self._get_user_interactions(request.user_id)

            # Discover content based on request
            discovered_content = await self._discover_content(request)

            if not discovered_content:
                logger.warning("No content discovered for request %s", request_id)
                return CurationResponse(
                    request_id=request_id,
                    user_id=request.user_id,
                    recommendations=[],
                    total_content_analyzed=0,
                    processing_time_ms=0,
                    cache_hit_rate=0.0,
                    model_confidence=0.0,
                )

            # Analyze content quality and extract features
            analyzed_content = await self._analyze_content_batch(discovered_content)

            # Generate personalized recommendations
            recommendations = await self._generate_recommendations(
                analyzed_content,
                user_profile,
                user_interactions,
                request,
            )

            # Sort and limit results
            recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
            recommendations = recommendations[: request.max_results]

            # Calculate processing metrics
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            performance_stats = self.prediction_engine.get_performance_stats()
            cache_hit_rate = performance_stats.get("cache_hit_rate", 0.0)

            # Calculate average model confidence
            model_confidence = (
                self.np.mean([r.confidence_score for r in recommendations])
                if recommendations
                else 0.0
            )

            response = CurationResponse(
                request_id=request_id,
                user_id=request.user_id,
                recommendations=recommendations,
                total_content_analyzed=len(analyzed_content),
                processing_time_ms=processing_time,
                cache_hit_rate=cache_hit_rate,
                model_confidence=model_confidence,
            )

            logger.info(
                "Curation request %s completed: %s recommendations in %sms",
                request_id,
                len(recommendations),
                f"{processing_time:.1f}",
            )
            return response

        except (ValueError, RuntimeError) as e:
            logger.error("Error processing curation request %s: %s", request_id, e)
            # Return empty response on error
            return CurationResponse(
                request_id=request_id,
                user_id=request.user_id,
                recommendations=[],
                total_content_analyzed=0,
                processing_time_ms=0,
                cache_hit_rate=0.0,
                model_confidence=0.0,
            )

    async def _get_user_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile."""
        try:
            # Try to get existing profile
            profile = await self.user_preference_service.get_user_profile(user_id)
            if profile:
                return profile

            # Create new profile with default preferences
            logger.info("Creating new user profile for %s", user_id)
            return await self.user_preference_service.create_user_profile(
                user_id=user_id,
                interests=[],  # Will be learned over time
                preference_weights={
                    "academic": 0.3,
                    "news": 0.3,
                    "blog": 0.2,
                    "tutorial": 0.2,
                },
                learning_rate=0.1,
                exploration_factor=0.1,
            )

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Error getting user profile for %s: %s", user_id, e)
            # Return default profile
            return UserProfile(
                user_id=user_id,
                interests=[],
                preference_weights={
                    "academic": 0.3,
                    "news": 0.3,
                    "blog": 0.2,
                    "tutorial": 0.2,
                },
                learning_rate=0.1,
                exploration_factor=0.1,
            )

    async def _get_user_interactions(self, user_id: str) -> list[UserInteraction]:
        """Get user interaction history."""
        try:
            # Get interactions from the last 90 days
            since_date = datetime.now(UTC) - timedelta(days=90)
            return await self.user_preference_service.get_user_interactions(
                user_id,
                since_date=since_date,
            )

        except (ValueError, RuntimeError) as e:
            logger.error("Error getting user interactions for %s: %s", user_id, e)
            return []

    async def _discover_content(self, request: CurationRequest) -> list[ContentItem]:
        """Discover content based on request parameters."""
        discovered_content = []

        try:
            # If query provided, use search-based discovery
            if request.query:
                search_results = await self._search_content(
                    request.query,
                    request.max_results * 2,
                )
                discovered_content.extend(search_results)

            # If interests provided, use interest-based discovery
            if request.interests:
                interest_results = await self._discover_by_interests(
                    request.interests,
                    request.max_results * 2,
                )
                discovered_content.extend(interest_results)

            # If no specific criteria, use trending/popular content
            if not request.query and not request.interests:
                trending_results = await self._get_trending_content(
                    request.max_results * 2,
                )
                discovered_content.extend(trending_results)

            # Remove duplicates
            seen_ids = set()
            unique_content = []
            for content in discovered_content:
                if content.id not in seen_ids:
                    seen_ids.add(content.id)
                    unique_content.append(content)

            logger.info("Discovered %s unique content items", len(unique_content))
            return unique_content

        except (ValueError, RuntimeError) as e:
            logger.error("Error discovering content: %s", e)
            return []

    async def _search_content(self, query: str, max_results: int) -> list[ContentItem]:
        """Search for content using query."""
        # This would integrate with the existing PAKE search system
        # For now, return mock results
        logger.info("Searching content for query: %s", query)

        # INTEGRATION NEEDED: Connect with PAKE search services
        # This method should integrate with the existing Orchestrator service
        # to leverage the multi-source research capabilities for content discovery
        # from src.services.ingestion.orchestrator import Orchestrator
        # orchestrator = Orchestrator()
        # results = await orchestrator.research_topic(query)

        return []  # Placeholder

    async def _discover_by_interests(
        self,
        interests: list[str],
        max_results: int,
    ) -> list[ContentItem]:
        """Discover content based on user interests."""
        logger.info("Discovering content for interests: %s", interests)

        # INTEGRATION NEEDED: Connect with PAKE content database
        # This method should query the existing PAKE database for content
        # that matches user interests using the content categorization system
        # Implementation should leverage existing content tagging and metadata

        return []  # Placeholder

    async def _get_trending_content(self, max_results: int) -> list[ContentItem]:
        """Get trending/popular content."""
        logger.info("Getting trending content: %s items", max_results)

        # TODO: Integrate with existing PAKE system to get trending content
        # This would query the database for recently popular content

        return []  # Placeholder

    async def _analyze_content_batch(
        self,
        contents: list[ContentItem],
    ) -> list[ContentItem]:
        """Analyze content quality and extract features in batch."""
        logger.info("Analyzing %s content items", len(contents))

        analyzed_content = []

        for content in contents:
            try:
                # Analyze content quality
                analysis_result = await self.content_analysis_service.analyze_content(
                    content,
                )

                # Update content with analysis results
                updated_content = ContentItem(
                    id=content.id,
                    title=content.title,
                    content_text=content.content_text,
                    author=content.author,
                    source_url=content.source_url,
                    published_date=content.published_date,
                    content_type=content.content_type,
                    tags=content.tags,
                    quality_score=analysis_result.quality_score,
                    credibility_score=analysis_result.credibility_score,
                    topic_categories=analysis_result.topic_categories,
                    sentiment_score=analysis_result.sentiment_score,
                    readability_score=analysis_result.readability_score,
                    source_authority_score=content.source_authority_score,
                    source_reliability=content.source_reliability,
                    view_count=content.view_count,
                    share_count=content.share_count,
                    like_count=content.like_count,
                    comment_count=content.comment_count,
                    abstract=content.abstract,
                )

                analyzed_content.append(updated_content)

            except (ValueError, RuntimeError) as e:
                logger.warning("Error analyzing content %s: %s", content.id, e)
                analyzed_content.append(content)  # Use original content

        logger.info("Successfully analyzed %s content items", len(analyzed_content))
        return analyzed_content

    async def _generate_recommendations(
        self,
        contents: list[ContentItem],
        user_profile: UserProfile,
        user_interactions: list[UserInteraction],
        request: CurationRequest,
    ) -> list[Recommendation]:
        """Generate personalized recommendations."""
        logger.info("Generating recommendations for %s content items", len(contents))

        recommendations = []

        # Use batch prediction for efficiency
        prediction_results = await self.prediction_engine.predict_batch_recommendations(
            contents,
            user_profile,
            user_interactions,
            max_results=len(contents),
        )

        for i, prediction in enumerate(prediction_results):
            try:
                content = contents[i]

                # Apply filters
                if (
                    content.quality_score
                    and content.quality_score < request.min_quality_score
                ):
                    continue

                if (
                    request.content_types
                    and content.content_type not in request.content_types
                ):
                    continue

                if request.freshness_days and content.published_date:
                    age_days = (datetime.now(UTC) - content.published_date).days
                    if age_days > request.freshness_days:
                        continue

                # Generate recommendation
                recommendation = (
                    await self.recommendation_service.generate_recommendation(
                        content=content,
                        user_profile=user_profile,
                        relevance_score=prediction.score,
                        confidence_score=prediction.confidence,
                        reasoning=(
                            await self._generate_reasoning(
                                content,
                                user_profile,
                                prediction,
                            )
                            if request.include_explanations
                            else None
                        ),
                    )
                )

                recommendations.append(recommendation)

            except (ValueError, RuntimeError) as e:
                logger.warning(
                    "Error generating recommendation for content %s: %s",
                    contents[i].id,
                    e,
                )
                continue

        logger.info("Generated %s recommendations", len(recommendations))
        return recommendations

    async def _generate_reasoning(
        self,
        content: ContentItem,
        user_profile: UserProfile,
        prediction,
    ) -> str:
        """Generate explanation for recommendation."""
        reasoning_parts = []

        # Content quality reasoning
        if content.quality_score and content.quality_score > 0.7:
            reasoning_parts.append("High-quality content")

        # Interest matching reasoning
        if user_profile.interests and content.tags:
            matching_interests = set(user_profile.interests) & set(content.tags)
            if matching_interests:
                reasoning_parts.append(
                    f"Matches your interests: {', '.join(matching_interests)}",
                )

        # Source authority reasoning
        if content.source_authority_score and content.source_authority_score > 0.8:
            reasoning_parts.append("From authoritative source")

        # Recency reasoning
        if content.published_date:
            age_days = (datetime.now(UTC) - content.published_date).days
            if age_days < 7:
                reasoning_parts.append("Recently published")

        # Confidence reasoning
        if prediction.confidence > 0.8:
            reasoning_parts.append("High confidence match")

        return (
            "; ".join(reasoning_parts)
            if reasoning_parts
            else "Recommended based on your preferences"
        )

    async def process_user_feedback(
        self,
        user_id: str,
        content_id: str,
        feedback_type: str,
        feedback_data: dict[str, Any],
    ) -> bool:
        """Process user feedback for learning."""
        try:
            # Create user interaction
            interaction = UserInteraction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                content_id=content_id,
                interaction_type=feedback_type,
                timestamp=datetime.now(UTC),
                session_duration=feedback_data.get("session_duration"),
                context=feedback_data.get("context", {}),
            )

            # Process feedback
            await self.feedback_processing_service.process_feedback(interaction)

            # Update user preferences
            await self.user_preference_service.update_user_preferences(
                user_id,
                interaction,
            )

            logger.info(
                "Processed feedback for user %s, content %s", user_id, content_id
            )
            return True

        except (sqlalchemy.exc.SQLAlchemyError, psycopg2.Error, asyncpg.Error) as e:
            logger.error("Error processing feedback: %s", e)
            return False

    async def retrain_models(self, force_retrain: bool = False) -> dict[str, bool]:
        """Retrain ML models with latest data."""
        # Check if retraining is needed
        if not force_retrain and self.last_model_update:
            time_since_update = datetime.now(UTC) - self.last_model_update
            if time_since_update.days < 7:  # Retrain weekly
                logger.info("Models are up to date, skipping retraining")
                return {"retrained": False, "reason": "models_up_to_date"}

        logger.info("Retraining ML models")

        try:
            # Get training data
            contents = await self._get_training_content()
            user_profiles = await self._get_training_users()
            interactions = await self._get_training_interactions()

            # Retrain models
            results = await self.model_trainer.retrain_models(
                contents,
                user_profiles,
                interactions,
            )

            # Update system state
            self.models_trained = True
            self.last_model_update = datetime.now(UTC)

            logger.info("Model retraining completed successfully")
            return {"retrained": True, "results": results}

        except (ValueError, RuntimeError) as e:
            logger.error("Error retraining models: %s", e)
            return {"retrained": False, "error": str(e)}

    async def _get_training_content(self) -> list[ContentItem]:
        """Get content for model training."""
        # TODO: Integrate with existing PAKE database
        # This would query the database for content with sufficient interactions
        return []

    async def _get_training_users(self) -> list[UserProfile]:
        """Get users for model training."""
        # TODO: Integrate with existing PAKE database
        # This would query the database for users with sufficient interaction history
        return []

    async def _get_training_interactions(self) -> list[UserInteraction]:
        """Get interactions for model training."""
        # TODO: Integrate with existing PAKE database
        # This would query the database for user interactions
        return []

    async def get_system_health(self) -> SystemHealth:
        """Get system health status."""
        services_healthy = {
            "content_analysis": await self.content_analysis_service.is_healthy(),
            "recommendation": await self.recommendation_service.is_healthy(),
            "user_preference": await self.user_preference_service.is_healthy(),
            "feedback_processing": await self.feedback_processing_service.is_healthy(),
        }

        models_loaded = await self.model_trainer.load_models()

        cache_status = self.prediction_engine.get_performance_stats()

        performance_metrics = {
            "avg_prediction_time_ms": cache_status.get("avg_prediction_time_ms", 0),
            "cache_hit_rate": cache_status.get("cache_hit_rate", 0),
            "total_predictions": cache_status.get("total_predictions", 0),
        }

        return SystemHealth(
            services_healthy=services_healthy,
            models_loaded=models_loaded,
            cache_status=cache_status,
            performance_metrics=performance_metrics,
        )

    async def shutdown(self) -> None:
        """Shutdown the curation system."""
        logger.info("Shutting down curation system")

        try:
            # Save models
            await self.model_trainer.save_models()

            # Shutdown services
            await self.content_analysis_service.shutdown()
            await self.recommendation_service.shutdown()
            await self.user_preference_service.shutdown()
            await self.feedback_processing_service.shutdown()

            logger.info("Curation system shutdown completed")

        except (sqlalchemy.exc.SQLAlchemyError, psycopg2.Error, asyncpg.Error) as e:
            logger.error("Error during shutdown: %s", e)
