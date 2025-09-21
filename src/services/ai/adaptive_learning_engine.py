"""Adaptive Learning Engine for PAKE System
Implements personalization and recommendation capabilities with machine learning.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LearningStrategy(Enum):
    """Learning strategies for user behavior adaptation"""

    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"
    REINFORCEMENT = "reinforcement"


class UserBehaviorType(Enum):
    """Types of user behavior to learn from"""

    CONTENT_VIEW = "content_view"
    CONTENT_LIKE = "content_like"
    CONTENT_SHARE = "content_share"
    SEARCH_QUERY = "search_query"
    TOPIC_PREFERENCE = "topic_preference"
    SOURCE_PREFERENCE = "source_preference"
    TIME_PREFERENCE = "time_preference"


class LearningConfidence(Enum):
    """Confidence levels for learned preferences"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass(frozen=True)
class UserInteraction:
    """Immutable record of user interaction"""

    user_id: str
    interaction_type: UserBehaviorType
    content_id: str | None = None
    content_category: str | None = None
    content_topics: list[str] = field(default_factory=list)
    interaction_score: float = 1.0  # Positive/negative weight
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context_metadata: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None


@dataclass(frozen=True)
class UserProfile:
    """Immutable user preference profile"""

    user_id: str
    topic_preferences: dict[str, float] = field(default_factory=dict)
    source_preferences: dict[str, float] = field(default_factory=dict)
    content_type_preferences: dict[str, float] = field(default_factory=dict)
    time_preferences: dict[str, float] = field(
        default_factory=dict,
    )  # Hour of day patterns
    interaction_patterns: dict[str, Any] = field(default_factory=dict)
    learning_confidence: LearningConfidence = LearningConfidence.LOW
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_interactions: int = 0


@dataclass(frozen=True)
class RecommendationRequest:
    """Request for personalized recommendations"""

    user_id: str
    context: str | None = None
    content_types: list[str] = field(default_factory=list)
    max_recommendations: int = 10
    diversity_factor: float = 0.3  # Balance between relevance and diversity
    exclude_seen: bool = True
    request_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class Recommendation:
    """Individual recommendation result"""

    content_id: str
    relevance_score: float
    confidence: LearningConfidence
    reasoning: list[str] = field(default_factory=list)
    recommendation_type: str = "personalized"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecommendationResult:
    """Complete recommendation response"""

    user_id: str
    recommendations: list[Recommendation] = field(default_factory=list)
    fallback_recommendations: list[Recommendation] = field(default_factory=list)
    processing_time_ms: float = 0.0
    confidence: LearningConfidence = LearningConfidence.LOW
    strategy_used: LearningStrategy = LearningStrategy.CONTENT_BASED
    generated_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass
class AdaptiveLearningConfig:
    """Configuration for adaptive learning system"""

    learning_rate: float = 0.1
    min_interactions_for_confidence: int = 10
    max_profile_history_days: int = 90
    recommendation_diversity_threshold: float = 0.3
    collaborative_similarity_threshold: float = 0.6
    content_similarity_threshold: float = 0.7
    learning_decay_factor: float = 0.95  # Older interactions have less weight
    max_concurrent_learning: int = 10
    enable_real_time_learning: bool = True
    cache_recommendations: bool = True
    recommendation_cache_ttl_minutes: int = 30


class CollaborativeFilter:
    """Collaborative filtering for user similarity and recommendations"""

    def __init__(self, config: AdaptiveLearningConfig):
        self.config = config
        self.user_similarities: dict[str, dict[str, float]] = {}
        self.content_user_matrix: dict[str, set[str]] = defaultdict(set)

    def update_user_interactions(self, interactions: list[UserInteraction]):
        """Update the collaborative filtering model with new interactions"""
        for interaction in interactions:
            if interaction.content_id:
                self.content_user_matrix[interaction.content_id].add(
                    interaction.user_id,
                )

    def calculate_user_similarity(self, user1: str, user2: str) -> float:
        """Calculate similarity between two users based on content interactions"""
        if user1 not in self.user_similarities:
            self.user_similarities[user1] = {}

        if user2 in self.user_similarities[user1]:
            return self.user_similarities[user1][user2]

        # Find common content
        user1_content = {
            content_id
            for content_id, users in self.content_user_matrix.items()
            if user1 in users
        }
        user2_content = {
            content_id
            for content_id, users in self.content_user_matrix.items()
            if user2 in users
        }

        if not user1_content or not user2_content:
            similarity = 0.0
        else:
            intersection = len(user1_content.intersection(user2_content))
            union = len(user1_content.union(user2_content))
            similarity = intersection / union if union > 0 else 0.0

        # Cache the similarity
        self.user_similarities[user1][user2] = similarity
        if user2 not in self.user_similarities:
            self.user_similarities[user2] = {}
        self.user_similarities[user2][user1] = similarity

        return similarity

    def find_similar_users(
        self,
        user_id: str,
        min_similarity: float = 0.3,
    ) -> list[tuple[str, float]]:
        """Find users similar to the given user"""
        similarities = []

        for other_user in self.content_user_matrix:
            if other_user != user_id:
                similarity = self.calculate_user_similarity(user_id, other_user)
                if similarity >= min_similarity:
                    similarities.append((other_user, similarity))

        return sorted(similarities, key=lambda x: x[1], reverse=True)


class ContentBasedFilter:
    """Content-based filtering using content features and user preferences"""

    def __init__(self, config: AdaptiveLearningConfig):
        self.config = config
        self.content_features: dict[str, dict[str, float]] = {}
        self.feature_weights: dict[str, float] = {
            "topic_match": 0.4,
            "content_type_match": 0.2,
            "source_match": 0.2,
            "quality_score": 0.2,
        }

    def update_content_features(self, content_id: str, features: dict[str, Any]):
        """Update content feature representation"""
        self.content_features[content_id] = {}

        # Extract and normalize features
        if "topics" in features:
            for topic in features["topics"]:
                self.content_features[content_id][f"topic_{topic}"] = 1.0

        if "content_type" in features:
            self.content_features[content_id][f"type_{features['content_type']}"] = 1.0

        if "source" in features:
            self.content_features[content_id][f"source_{features['source']}"] = 1.0

        if "quality_score" in features:
            self.content_features[content_id]["quality"] = features["quality_score"]

    def calculate_content_similarity(
        self,
        profile: UserProfile,
        content_id: str,
    ) -> float:
        """Calculate how well content matches user profile"""
        if content_id not in self.content_features:
            return 0.0

        content_features = self.content_features[content_id]
        similarity_score = 0.0

        # Topic similarity
        topic_score = 0.0
        for topic, preference in profile.topic_preferences.items():
            if f"topic_{topic}" in content_features:
                topic_score += preference * content_features[f"topic_{topic}"]
        similarity_score += topic_score * self.feature_weights["topic_match"]

        # Content type similarity
        type_score = 0.0
        for content_type, preference in profile.content_type_preferences.items():
            if f"type_{content_type}" in content_features:
                type_score += preference * content_features[f"type_{content_type}"]
        similarity_score += type_score * self.feature_weights["content_type_match"]

        # Source similarity
        source_score = 0.0
        for source, preference in profile.source_preferences.items():
            if f"source_{source}" in content_features:
                source_score += preference * content_features[f"source_{source}"]
        similarity_score += source_score * self.feature_weights["source_match"]

        # Quality score
        quality_score = content_features.get("quality", 0.0)
        similarity_score += quality_score * self.feature_weights["quality_score"]

        return min(similarity_score, 1.0)


class AdaptiveLearningEngine:
    """Main adaptive learning engine for personalized user experiences.
    Combines collaborative filtering, content-based filtering, and reinforcement learning.
    """

    def __init__(self, config: AdaptiveLearningConfig = None):
        self.config = config or AdaptiveLearningConfig()
        self.user_profiles: dict[str, UserProfile] = {}
        self.user_interactions: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000),
        )
        self.collaborative_filter = CollaborativeFilter(self.config)
        self.content_filter = ContentBasedFilter(self.config)
        self.recommendation_cache: dict[str, tuple[RecommendationResult, datetime]] = {}
        self.learning_semaphore = asyncio.Semaphore(self.config.max_concurrent_learning)

        # Metrics
        self.metrics = {
            "profiles_created": 0,
            "interactions_processed": 0,
            "recommendations_generated": 0,
            "learning_updates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    async def record_interaction(self, interaction: UserInteraction) -> bool:
        """Record user interaction and trigger learning update"""
        try:
            async with self.learning_semaphore:
                # Store interaction
                self.user_interactions[interaction.user_id].append(interaction)
                self.metrics["interactions_processed"] += 1

                # Update collaborative filter
                self.collaborative_filter.update_user_interactions([interaction])

                # Trigger profile update if real-time learning is enabled
                if self.config.enable_real_time_learning:
                    await self._update_user_profile(interaction.user_id)

                logger.debug(
                    f"Recorded interaction for user {interaction.user_id}: {
                        interaction.interaction_type
                    }",
                )
                return True

        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")
            return False

    async def _update_user_profile(self, user_id: str):
        """Update user profile based on recent interactions"""
        interactions = list(self.user_interactions[user_id])
        if not interactions:
            return

        # Get existing profile or create new one
        current_profile = self.user_profiles.get(user_id, UserProfile(user_id=user_id))

        # Calculate new preferences
        topic_preferences = dict(current_profile.topic_preferences)
        source_preferences = dict(current_profile.source_preferences)
        content_type_preferences = dict(current_profile.content_type_preferences)

        # Apply learning rate to update preferences
        for interaction in interactions[-100:]:  # Consider recent interactions
            weight = interaction.interaction_score * self.config.learning_rate

            # Update topic preferences
            for topic in interaction.content_topics:
                current_pref = topic_preferences.get(topic, 0.0)
                topic_preferences[topic] = min(1.0, current_pref + weight)

            # Update source preferences
            if "source" in interaction.context_metadata:
                source = interaction.context_metadata["source"]
                current_pref = source_preferences.get(source, 0.0)
                source_preferences[source] = min(1.0, current_pref + weight)

            # Update content type preferences
            if interaction.content_category:
                current_pref = content_type_preferences.get(
                    interaction.content_category,
                    0.0,
                )
                content_type_preferences[interaction.content_category] = min(
                    1.0,
                    current_pref + weight,
                )

        # Determine learning confidence
        total_interactions = len(interactions)
        if total_interactions >= self.config.min_interactions_for_confidence * 4:
            confidence = LearningConfidence.VERY_HIGH
        elif total_interactions >= self.config.min_interactions_for_confidence * 2:
            confidence = LearningConfidence.HIGH
        elif total_interactions >= self.config.min_interactions_for_confidence:
            confidence = LearningConfidence.MEDIUM
        else:
            confidence = LearningConfidence.LOW

        # Create updated profile
        updated_profile = UserProfile(
            user_id=user_id,
            topic_preferences=topic_preferences,
            source_preferences=source_preferences,
            content_type_preferences=content_type_preferences,
            learning_confidence=confidence,
            total_interactions=total_interactions,
            last_updated=datetime.now(UTC),
        )

        self.user_profiles[user_id] = updated_profile
        self.metrics["learning_updates"] += 1

        if user_id not in [p.user_id for p in self.user_profiles.values()]:
            self.metrics["profiles_created"] += 1

    async def get_recommendations(
        self,
        request: RecommendationRequest,
    ) -> RecommendationResult:
        """Generate personalized recommendations for user"""
        start_time = time.time()

        try:
            # Check cache first
            cache_key = f"{request.user_id}_{hash(str(request))}"
            if (
                self.config.cache_recommendations
                and cache_key in self.recommendation_cache
            ):
                cached_result, cached_time = self.recommendation_cache[cache_key]
                cache_age_minutes = (
                    datetime.now(UTC) - cached_time
                ).total_seconds() / 60

                if cache_age_minutes < self.config.recommendation_cache_ttl_minutes:
                    self.metrics["cache_hits"] += 1
                    return cached_result
                del self.recommendation_cache[cache_key]

            self.metrics["cache_misses"] += 1

            # Get user profile
            user_profile = self.user_profiles.get(request.user_id)
            if not user_profile:
                # Return generic recommendations for new users
                return RecommendationResult(
                    user_id=request.user_id,
                    recommendations=[],
                    fallback_recommendations=await self._get_fallback_recommendations(
                        request,
                    ),
                    processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                    confidence=LearningConfidence.LOW,
                    strategy_used=LearningStrategy.CONTENT_BASED,
                )

            # Choose learning strategy based on profile confidence and data availability
            if user_profile.learning_confidence in [
                LearningConfidence.HIGH,
                LearningConfidence.VERY_HIGH,
            ]:
                strategy = LearningStrategy.HYBRID
            else:
                strategy = LearningStrategy.CONTENT_BASED

            # Generate recommendations using chosen strategy
            recommendations = await self._generate_recommendations(
                user_profile,
                request,
                strategy,
            )

            # Apply diversity filter
            final_recommendations = self._apply_diversity_filter(
                recommendations,
                request.diversity_factor,
            )

            # Create result
            result = RecommendationResult(
                user_id=request.user_id,
                recommendations=final_recommendations[: request.max_recommendations],
                processing_time_ms=max((time.time() - start_time) * 1000, 0.1),
                confidence=user_profile.learning_confidence,
                strategy_used=strategy,
                generated_timestamp=datetime.now(UTC),
            )

            # Cache result
            if self.config.cache_recommendations:
                self.recommendation_cache[cache_key] = (
                    result,
                    datetime.now(UTC),
                )

            self.metrics["recommendations_generated"] += 1
            return result

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            processing_time = max((time.time() - start_time) * 1000, 0.1)
            return RecommendationResult(
                user_id=request.user_id,
                processing_time_ms=processing_time,
                confidence=LearningConfidence.LOW,
            )

    async def _generate_recommendations(
        self,
        profile: UserProfile,
        request: RecommendationRequest,
        strategy: LearningStrategy,
    ) -> list[Recommendation]:
        """Generate recommendations using specified strategy"""
        recommendations = []

        if strategy == LearningStrategy.CONTENT_BASED:
            recommendations = await self._content_based_recommendations(
                profile,
                request,
            )
        elif strategy == LearningStrategy.COLLABORATIVE_FILTERING:
            recommendations = await self._collaborative_recommendations(
                profile,
                request,
            )
        elif strategy == LearningStrategy.HYBRID:
            # Combine both approaches
            content_recs = await self._content_based_recommendations(profile, request)
            collab_recs = await self._collaborative_recommendations(profile, request)

            # Merge and weight recommendations
            combined_recs = {}
            for rec in content_recs:
                combined_recs[rec.content_id] = rec

            for rec in collab_recs:
                if rec.content_id in combined_recs:
                    # Average the scores
                    existing = combined_recs[rec.content_id]
                    new_score = (existing.relevance_score + rec.relevance_score) / 2
                    combined_recs[rec.content_id] = Recommendation(
                        content_id=rec.content_id,
                        relevance_score=new_score,
                        confidence=LearningConfidence.HIGH,
                        reasoning=existing.reasoning + rec.reasoning,
                        recommendation_type="hybrid",
                    )
                else:
                    combined_recs[rec.content_id] = rec

            recommendations = list(combined_recs.values())

        return recommendations

    async def _content_based_recommendations(
        self,
        profile: UserProfile,
        request: RecommendationRequest,
    ) -> list[Recommendation]:
        """Generate content-based recommendations"""
        recommendations = []

        # Mock content database - in production, this would query real content
        mock_content = [
            {
                "content_id": f"content_{i}",
                "topics": ["ai", "technology"],
                "content_type": "article",
                "source": "tech_blog",
                "quality_score": 0.8 + (i % 3) * 0.1,
            }
            for i in range(1, 21)
        ]

        for content in mock_content:
            # Update content features
            self.content_filter.update_content_features(content["content_id"], content)

            # Calculate similarity
            similarity = self.content_filter.calculate_content_similarity(
                profile,
                content["content_id"],
            )

            if similarity > 0.3:  # Threshold for relevance
                recommendations.append(
                    Recommendation(
                        content_id=content["content_id"],
                        relevance_score=similarity,
                        confidence=profile.learning_confidence,
                        reasoning=[
                            f"Matches your preferences in topics: {
                                ', '.join(content['topics'])
                            }",
                        ],
                        recommendation_type="content_based",
                    ),
                )

        return sorted(recommendations, key=lambda x: x.relevance_score, reverse=True)

    async def _collaborative_recommendations(
        self,
        profile: UserProfile,
        request: RecommendationRequest,
    ) -> list[Recommendation]:
        """Generate collaborative filtering recommendations"""
        recommendations = []

        # Find similar users
        similar_users = self.collaborative_filter.find_similar_users(
            profile.user_id,
            self.config.collaborative_similarity_threshold,
        )

        if not similar_users:
            return recommendations

        # Mock content liked by similar users
        for user_id, similarity in similar_users[:5]:  # Top 5 similar users
            user_content = [f"collab_content_{user_id}_{i}" for i in range(1, 4)]

            for content_id in user_content:
                recommendations.append(
                    Recommendation(
                        content_id=content_id,
                        relevance_score=similarity * 0.8,  # Weight by user similarity
                        confidence=profile.learning_confidence,
                        reasoning=[
                            "Recommended because users similar to you liked this content",
                        ],
                        recommendation_type="collaborative",
                    ),
                )

        return recommendations

    async def _get_fallback_recommendations(
        self,
        request: RecommendationRequest,
    ) -> list[Recommendation]:
        """Generate fallback recommendations for users without sufficient data"""
        fallback_recs = []

        # Popular/trending content
        for i in range(1, min(6, request.max_recommendations + 1)):
            fallback_recs.append(
                Recommendation(
                    content_id=f"trending_{i}",
                    relevance_score=0.6 - (i * 0.05),
                    confidence=LearningConfidence.LOW,
                    reasoning=["Popular content for new users"],
                    recommendation_type="fallback_trending",
                ),
            )

        return fallback_recs

    def _apply_diversity_filter(
        self,
        recommendations: list[Recommendation],
        diversity_factor: float,
    ) -> list[Recommendation]:
        """Apply diversity filtering to avoid too similar recommendations"""
        if not recommendations or diversity_factor <= 0:
            return recommendations

        # Simple diversity filter - in production would use more sophisticated methods
        diverse_recs = []
        seen_types = set()

        # Sort by relevance first
        sorted_recs = sorted(
            recommendations,
            key=lambda x: x.relevance_score,
            reverse=True,
        )

        for rec in sorted_recs:
            rec_type = rec.recommendation_type

            if rec_type not in seen_types or len(seen_types) < (1 / diversity_factor):
                diverse_recs.append(rec)
                seen_types.add(rec_type)

        return diverse_recs

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        """Get current user profile"""
        return self.user_profiles.get(user_id)

    def get_metrics(self) -> dict[str, Any]:
        """Get learning engine metrics"""
        return {
            **self.metrics,
            "total_users": len(self.user_profiles),
            "total_interactions": sum(
                len(interactions) for interactions in self.user_interactions.values()
            ),
            "cached_recommendations": len(self.recommendation_cache),
            "average_confidence": self._calculate_average_confidence(),
        }

    def _calculate_average_confidence(self) -> str:
        """Calculate average user confidence level"""
        if not self.user_profiles:
            return LearningConfidence.LOW.value

        confidence_values = {
            LearningConfidence.LOW: 1,
            LearningConfidence.MEDIUM: 2,
            LearningConfidence.HIGH: 3,
            LearningConfidence.VERY_HIGH: 4,
        }

        total_confidence = sum(
            confidence_values[profile.learning_confidence]
            for profile in self.user_profiles.values()
        )
        avg_confidence = total_confidence / len(self.user_profiles)

        if avg_confidence <= 1.5:
            return LearningConfidence.LOW.value
        if avg_confidence <= 2.5:
            return LearningConfidence.MEDIUM.value
        if avg_confidence <= 3.5:
            return LearningConfidence.HIGH.value
        return LearningConfidence.VERY_HIGH.value


def create_production_adaptive_learning_engine() -> AdaptiveLearningEngine:
    """Factory function to create production-optimized adaptive learning engine"""
    config = AdaptiveLearningConfig(
        learning_rate=0.05,  # Conservative learning rate
        min_interactions_for_confidence=25,  # Higher threshold for production
        max_profile_history_days=180,  # Longer history retention
        recommendation_diversity_threshold=0.4,  # More diversity
        collaborative_similarity_threshold=0.7,  # Higher similarity threshold
        content_similarity_threshold=0.75,  # Higher content similarity
        learning_decay_factor=0.98,  # Slower decay
        max_concurrent_learning=20,  # Higher concurrency
        enable_real_time_learning=True,
        cache_recommendations=True,
        recommendation_cache_ttl_minutes=15,  # Shorter cache for fresher recommendations
    )

    return AdaptiveLearningEngine(config)
