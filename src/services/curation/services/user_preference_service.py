"""UserPreferenceService

Advanced user preference management and learning service that tracks user interests,
learns from interactions, and maintains personalized preference profiles with
sophisticated preference evolution and interest discovery capabilities.
"""

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from ..models.content_item import ContentItem
from ..models.topic_category import TopicCategory
from ..models.user_feedback import FeedbackType, UserFeedback
from ..models.user_interaction import InteractionType, UserInteraction
from ..models.user_profile import (
    ContentEmbedding,
    InterestCategory,
    PreferencePattern,
    UserProfile,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreferenceUpdate:
    """Represents a preference update operation"""

    user_id: str
    content_id: str
    interaction_type: InteractionType
    preference_delta: dict[str, float]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class InterestEvolution:
    """Tracks how user interests evolve over time"""

    user_id: str
    interest_name: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0.0 to 1.0
    period_days: int
    confidence: float


@dataclass(frozen=True)
class PersonalizationInsight:
    """Insights about user personalization patterns"""

    user_id: str
    primary_interests: list[str]
    emerging_interests: list[str]
    declining_interests: list[str]
    preference_diversity: float  # How diverse user's interests are
    engagement_patterns: dict[str, Any]
    learning_velocity: float  # How quickly preferences change
    discovery_propensity: float  # Likelihood to explore new content


class UserPreferenceService:
    """Advanced user preference management with ML-powered learning.

    Tracks user interactions, learns preferences, discovers interest patterns,
    and provides sophisticated personalization capabilities.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        interest_decay_rate: float = 0.02,
        min_interactions_for_learning: int = 3,
    ):
        """Initialize user preference service.

        Args:
            learning_rate: Rate at which preferences adapt to new interactions
            interest_decay_rate: Rate at which old interests decay over time
            min_interactions_for_learning: Minimum interactions needed for reliable learning
        """
        self.learning_rate = learning_rate
        self.interest_decay_rate = interest_decay_rate
        self.min_interactions_for_learning = min_interactions_for_learning

        # Interaction weight configuration
        self.interaction_weights = {
            InteractionType.VIEW: 1.0,
            InteractionType.LIKE: 3.0,
            InteractionType.SAVE: 5.0,
            InteractionType.SHARE: 6.0,
            InteractionType.COMMENT: 4.0,
            InteractionType.CLICK: 2.0,
            InteractionType.DOWNLOAD: 7.0,
        }

        # Temporal decay configuration
        self.temporal_decay_halflife_days = (
            30  # How quickly old interactions lose weight
        )

        logger.info("UserPreferenceService initialized")

    async def learn_from_interaction(
        self,
        user_profile: UserProfile,
        interaction: UserInteraction,
        content_item: ContentItem,
    ) -> UserProfile:
        """Learn from a single user interaction and update preferences.

        Args:
            user_profile: Current user profile
            interaction: User interaction to learn from
            content_item: Content item that was interacted with

        Returns:
            Updated user profile with learned preferences
        """
        try:
            # Calculate interaction weight with temporal decay
            interaction_weight = self._calculate_interaction_weight(interaction)

            if interaction_weight <= 0:
                return (
                    user_profile  # No learning from very old or negative interactions
                )

            # Extract features from content
            content_features = await self._extract_content_features(content_item)

            # Update interest categories
            updated_interests = await self._update_interest_categories(
                user_profile.interests,
                content_features,
                interaction_weight,
            )

            # Update preference vector if embeddings are available
            updated_preference_vector = await self._update_preference_vector(
                user_profile.preference_vector,
                content_item,
                interaction_weight,
            )

            # Update preference patterns
            updated_patterns = await self._update_preference_patterns(
                user_profile.preference_patterns,
                content_item,
                interaction,
                interaction_weight,
            )

            # Create updated profile
            updated_profile = UserProfile(
                user_id=user_profile.user_id,
                interests=updated_interests,
                preference_vector=updated_preference_vector,
                preference_patterns=updated_patterns,
                total_interactions=user_profile.total_interactions + 1,
                last_activity=interaction.timestamp,
                learning_rate=user_profile.learning_rate,
                exploration_factor=user_profile.exploration_factor,
                created_at=user_profile.created_at,
                updated_at=datetime.now(),
            )

            logger.debug(
                f"Updated preferences for user {user_profile.user_id} from interaction {
                    interaction.id
                }",
            )
            return updated_profile

        except Exception as e:
            logger.error(f"Error learning from interaction: {str(e)}")
            return user_profile

    async def learn_from_feedback(
        self,
        user_profile: UserProfile,
        feedback: UserFeedback,
        content_item: ContentItem,
    ) -> UserProfile:
        """Learn from explicit user feedback and update preferences.

        Args:
            user_profile: Current user profile
            feedback: User feedback to learn from
            content_item: Content item that received feedback

        Returns:
            Updated user profile with learned preferences
        """
        try:
            # Convert feedback to learning signal
            feedback_weight = await self._convert_feedback_to_weight(feedback)

            if feedback_weight == 0:
                return user_profile

            # Extract content features
            content_features = await self._extract_content_features(content_item)

            # Update interests based on feedback
            updated_interests = await self._update_interest_categories(
                user_profile.interests,
                content_features,
                feedback_weight,
            )

            # Update preference vector
            updated_preference_vector = await self._update_preference_vector(
                user_profile.preference_vector,
                content_item,
                feedback_weight,
            )

            # Update preference patterns
            fake_interaction = UserInteraction(
                user_id=user_profile.user_id,
                content_id=content_item.id,
                interaction_type=(
                    InteractionType.LIKE
                    if feedback_weight > 0
                    else InteractionType.VIEW
                ),
                timestamp=feedback.timestamp,
            )

            updated_patterns = await self._update_preference_patterns(
                user_profile.preference_patterns,
                content_item,
                fake_interaction,
                feedback_weight,
            )

            # Create updated profile
            updated_profile = UserProfile(
                user_id=user_profile.user_id,
                interests=updated_interests,
                preference_vector=updated_preference_vector,
                preference_patterns=updated_patterns,
                total_interactions=user_profile.total_interactions,
                last_activity=feedback.timestamp,
                learning_rate=user_profile.learning_rate,
                exploration_factor=user_profile.exploration_factor,
                created_at=user_profile.created_at,
                updated_at=datetime.now(),
            )

            logger.debug(
                f"Updated preferences for user {user_profile.user_id} from feedback {
                    feedback.id
                }",
            )
            return updated_profile

        except Exception as e:
            logger.error(f"Error learning from feedback: {str(e)}")
            return user_profile

    async def batch_learn_from_interactions(
        self,
        user_profile: UserProfile,
        interactions: list[tuple[UserInteraction, ContentItem]],
        batch_size: int = 10,
    ) -> UserProfile:
        """Learn from multiple interactions in batch for efficiency.

        Args:
            user_profile: Current user profile
            interactions: List of (interaction, content_item) tuples
            batch_size: Number of interactions to process in each batch

        Returns:
            Updated user profile with learned preferences
        """
        try:
            updated_profile = user_profile

            # Process interactions in batches
            for i in range(0, len(interactions), batch_size):
                batch = interactions[i : i + batch_size]

                # Process each interaction in the batch
                for interaction, content_item in batch:
                    updated_profile = await self.learn_from_interaction(
                        updated_profile,
                        interaction,
                        content_item,
                    )

                # Apply batch normalization to prevent excessive drift
                updated_profile = await self._normalize_preferences(updated_profile)

            logger.info(
                f"Batch learned from {len(interactions)} interactions for user {
                    user_profile.user_id
                }",
            )
            return updated_profile

        except Exception as e:
            logger.error(f"Error in batch learning: {str(e)}")
            return user_profile

    async def analyze_interest_evolution(
        self,
        user_profile: UserProfile,
        historical_interactions: list[tuple[UserInteraction, ContentItem]],
        analysis_window_days: int = 90,
    ) -> list[InterestEvolution]:
        """Analyze how user interests have evolved over time.

        Args:
            user_profile: Current user profile
            historical_interactions: Historical interaction data
            analysis_window_days: Time window for analysis

        Returns:
            List of interest evolution patterns
        """
        try:
            # Group interactions by time periods
            cutoff_date = datetime.now() - timedelta(days=analysis_window_days)
            recent_interactions = [
                (interaction, content)
                for interaction, content in historical_interactions
                if interaction.timestamp >= cutoff_date
            ]

            if len(recent_interactions) < self.min_interactions_for_learning:
                return []

            # Analyze interest trends by time periods
            period_length = analysis_window_days // 3  # Split into 3 periods
            periods = [
                cutoff_date + timedelta(days=i * period_length)
                for i in range(4)  # 4 period boundaries for 3 periods
            ]

            interest_trends = {}

            # Calculate interest strength for each period
            for period_idx in range(3):
                period_start = periods[period_idx]
                period_end = periods[period_idx + 1]

                period_interactions = [
                    (interaction, content)
                    for interaction, content in recent_interactions
                    if period_start <= interaction.timestamp < period_end
                ]

                if not period_interactions:
                    continue

                # Calculate interest scores for this period
                period_interests = defaultdict(float)
                for interaction, content in period_interactions:
                    weight = self._calculate_interaction_weight(interaction)
                    for tag in content.topic_tags:
                        period_interests[tag] += weight

                # Normalize by number of interactions
                if period_interactions:
                    for interest in period_interests:
                        period_interests[interest] /= len(period_interactions)

                # Store period results
                for interest, score in period_interests.items():
                    if interest not in interest_trends:
                        interest_trends[interest] = []
                    interest_trends[interest].append(score)

            # Analyze trends
            evolutions = []
            for interest, scores in interest_trends.items():
                if len(scores) >= 2:
                    evolution = await self._calculate_interest_trend(
                        interest,
                        scores,
                        analysis_window_days,
                    )
                    if evolution:
                        evolutions.append(evolution)

            # Sort by trend strength
            evolutions.sort(key=lambda x: x.trend_strength, reverse=True)

            logger.debug(
                f"Analyzed {len(evolutions)} interest evolutions for user {
                    user_profile.user_id
                }",
            )
            return evolutions

        except Exception as e:
            logger.error(f"Error analyzing interest evolution: {str(e)}")
            return []

    async def generate_personalization_insights(
        self,
        user_profile: UserProfile,
        recent_interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> PersonalizationInsight:
        """Generate comprehensive personalization insights for a user.

        Args:
            user_profile: Current user profile
            recent_interactions: Recent interaction history

        Returns:
            Personalization insights and recommendations
        """
        try:
            # Analyze primary interests
            primary_interests = [
                interest.name
                for interest in user_profile.interests
                if interest.weight > 0.5
            ][:5]  # Top 5 interests

            # Analyze emerging interests (interests with positive trend)
            interest_evolutions = await self.analyze_interest_evolution(
                user_profile,
                recent_interactions,
                60,
            )

            emerging_interests = [
                evolution.interest_name
                for evolution in interest_evolutions
                if evolution.trend_direction == "increasing"
                and evolution.trend_strength > 0.3
            ][:3]

            declining_interests = [
                evolution.interest_name
                for evolution in interest_evolutions
                if evolution.trend_direction == "decreasing"
                and evolution.trend_strength > 0.3
            ][:3]

            # Calculate preference diversity
            diversity = await self._calculate_preference_diversity(user_profile)

            # Analyze engagement patterns
            engagement_patterns = await self._analyze_engagement_patterns(
                recent_interactions,
            )

            # Calculate learning velocity
            learning_velocity = await self._calculate_learning_velocity(
                user_profile,
                recent_interactions,
            )

            # Calculate discovery propensity
            discovery_propensity = await self._calculate_discovery_propensity(
                recent_interactions,
            )

            insight = PersonalizationInsight(
                user_id=str(user_profile.user_id),
                primary_interests=primary_interests,
                emerging_interests=emerging_interests,
                declining_interests=declining_interests,
                preference_diversity=diversity,
                engagement_patterns=engagement_patterns,
                learning_velocity=learning_velocity,
                discovery_propensity=discovery_propensity,
            )

            logger.debug(
                f"Generated personalization insights for user {user_profile.user_id}",
            )
            return insight

        except Exception as e:
            logger.error(f"Error generating personalization insights: {str(e)}")
            return PersonalizationInsight(
                user_id=str(user_profile.user_id),
                primary_interests=[],
                emerging_interests=[],
                declining_interests=[],
                preference_diversity=0.5,
                engagement_patterns={},
                learning_velocity=0.5,
                discovery_propensity=0.5,
            )

    async def suggest_exploration_content(
        self,
        user_profile: UserProfile,
        available_categories: list[TopicCategory],
        exploration_factor: float = 0.3,
    ) -> list[TopicCategory]:
        """Suggest content categories for user exploration based on preferences.

        Args:
            user_profile: Current user profile
            available_categories: Available topic categories
            exploration_factor: How aggressive to be with exploration suggestions

        Returns:
            List of recommended categories for exploration
        """
        try:
            # Get user's current interests
            user_interests = {
                interest.name.lower() for interest in user_profile.interests
            }

            # Score categories for exploration potential
            exploration_scores = []

            for category in available_categories:
                if not category.is_active:
                    continue

                # Skip categories user is already heavily interested in
                if category.name.lower() in user_interests:
                    continue

                # Calculate exploration score
                score = await self._calculate_exploration_score(
                    user_profile,
                    category,
                    exploration_factor,
                )

                if score > 0.1:  # Minimum threshold for suggestion
                    exploration_scores.append((category, score))

            # Sort by exploration score
            exploration_scores.sort(key=lambda x: x[1], reverse=True)

            # Return top suggestions
            suggested_categories = [
                category for category, score in exploration_scores[:5]
            ]

            logger.debug(
                f"Suggested {
                    len(suggested_categories)
                } exploration categories for user {user_profile.user_id}",
            )
            return suggested_categories

        except Exception as e:
            logger.error(f"Error suggesting exploration content: {str(e)}")
            return []

    async def optimize_learning_rate(
        self,
        user_profile: UserProfile,
        recent_interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> float:
        """Optimize learning rate based on user behavior patterns.

        Args:
            user_profile: Current user profile
            recent_interactions: Recent interaction history

        Returns:
            Optimized learning rate
        """
        try:
            if len(recent_interactions) < self.min_interactions_for_learning:
                return user_profile.learning_rate

            # Analyze interaction consistency
            consistency_score = await self._calculate_interaction_consistency(
                recent_interactions,
            )

            # Analyze preference stability
            stability_score = await self._calculate_preference_stability(
                user_profile,
                recent_interactions,
            )

            # Calculate optimal learning rate
            # High consistency + high stability = lower learning rate (don't change much)
            # Low consistency or low stability = higher learning rate (adapt quickly)
            optimal_rate = 0.1  # Base rate

            if consistency_score > 0.7 and stability_score > 0.7:
                optimal_rate = 0.05  # Slow learning for stable users
            elif consistency_score < 0.3 or stability_score < 0.3:
                optimal_rate = 0.2  # Fast learning for changing preferences
            else:
                optimal_rate = 0.1  # Medium learning rate

            # Smooth the transition
            new_rate = user_profile.learning_rate * 0.7 + optimal_rate * 0.3

            logger.debug(
                f"Optimized learning rate for user {user_profile.user_id}: {
                    user_profile.learning_rate:.3f} -> {new_rate:.3f}",
            )
            return new_rate

        except Exception as e:
            logger.error(f"Error optimizing learning rate: {str(e)}")
            return user_profile.learning_rate

    # Helper methods

    def _calculate_interaction_weight(self, interaction: UserInteraction) -> float:
        """Calculate weight for an interaction considering type and recency"""
        # Base weight from interaction type
        base_weight = self.interaction_weights.get(interaction.interaction_type, 1.0)

        # Apply temporal decay
        days_old = (datetime.now() - interaction.timestamp).days
        decay_factor = math.exp(-days_old / self.temporal_decay_halflife_days)

        return base_weight * decay_factor

    async def _extract_content_features(
        self,
        content_item: ContentItem,
    ) -> dict[str, float]:
        """Extract features from content for preference learning"""
        features = {}

        # Topic tags as features
        for tag in content_item.topic_tags:
            features[f"topic_{tag.lower()}"] = 1.0

        # Content type as feature
        features[f"type_{content_item.content_type.value}"] = 1.0

        # Quality as feature
        if content_item.quality_score:
            features["quality"] = content_item.quality_score

        # Authority as feature
        if content_item.authority_score:
            features["authority"] = content_item.authority_score

        # Domain as feature
        if content_item.domain:
            features[f"domain_{content_item.domain.lower()}"] = 1.0

        return features

    async def _update_interest_categories(
        self,
        current_interests: list[InterestCategory],
        content_features: dict[str, float],
        interaction_weight: float,
    ) -> list[InterestCategory]:
        """Update user interest categories based on interaction"""
        # Convert current interests to dict for easier manipulation
        interests_dict = {interest.name: interest for interest in current_interests}

        # Update interests based on content features
        for feature, feature_value in content_features.items():
            if feature.startswith("topic_"):
                topic_name = feature.replace("topic_", "")

                if topic_name in interests_dict:
                    # Update existing interest
                    current_interest = interests_dict[topic_name]
                    new_weight = current_interest.weight + (
                        interaction_weight * feature_value * self.learning_rate
                    )
                    new_weight = min(1.0, new_weight)  # Cap at 1.0

                    interests_dict[topic_name] = InterestCategory(
                        name=topic_name,
                        weight=new_weight,
                        confidence=min(1.0, current_interest.confidence + 0.1),
                        last_updated=datetime.now(),
                    )
                else:
                    # Add new interest
                    if interaction_weight > 0.5:  # Only add if significant interaction
                        interests_dict[topic_name] = InterestCategory(
                            name=topic_name,
                            weight=interaction_weight
                            * feature_value
                            * self.learning_rate,
                            confidence=0.3,  # Low initial confidence
                            last_updated=datetime.now(),
                        )

        # Apply decay to all interests
        for name, interest in interests_dict.items():
            days_since_update = (datetime.now() - interest.last_updated).days
            decay = math.exp(-days_since_update * self.interest_decay_rate)
            interests_dict[name] = InterestCategory(
                name=interest.name,
                weight=interest.weight * decay,
                confidence=interest.confidence,
                last_updated=interest.last_updated,
            )

        # Filter out very weak interests
        filtered_interests = [
            interest for interest in interests_dict.values() if interest.weight > 0.01
        ]

        # Limit to top interests to prevent unlimited growth
        filtered_interests.sort(key=lambda x: x.weight, reverse=True)
        return filtered_interests[:50]  # Keep top 50 interests

    async def _update_preference_vector(
        self,
        current_vector: ContentEmbedding | None,
        content_item: ContentItem,
        interaction_weight: float,
    ) -> ContentEmbedding | None:
        """Update user preference vector based on content interaction"""
        if not content_item.content_embedding:
            return current_vector

        content_vector = content_item.content_embedding.vector

        if current_vector is None:
            # Initialize with content vector
            return ContentEmbedding(
                vector=content_vector * interaction_weight * self.learning_rate,
                dimension=len(content_vector),
                model_name=content_item.content_embedding.model_name,
            )

        # Update existing vector
        current_array = current_vector.vector
        update_strength = interaction_weight * self.learning_rate

        # Weighted update
        new_vector = (
            current_array * (1 - update_strength) + content_vector * update_strength
        )

        # Normalize to prevent unbounded growth
        norm = np.linalg.norm(new_vector)
        if norm > 0:
            new_vector = new_vector / norm

        return ContentEmbedding(
            vector=new_vector,
            dimension=len(new_vector),
            model_name=current_vector.model_name,
        )

    async def _update_preference_patterns(
        self,
        current_patterns: list[PreferencePattern],
        content_item: ContentItem,
        interaction: UserInteraction,
        interaction_weight: float,
    ) -> list[PreferencePattern]:
        """Update user preference patterns based on interaction"""
        patterns_dict = {pattern.pattern_type: pattern for pattern in current_patterns}

        # Time-based patterns
        hour = interaction.timestamp.hour
        if hour < 6:
            time_pattern = "night"
        elif hour < 12:
            time_pattern = "morning"
        elif hour < 18:
            time_pattern = "afternoon"
        else:
            time_pattern = "evening"

        # Update time pattern
        time_key = f"time_{time_pattern}"
        if time_key in patterns_dict:
            current_pattern = patterns_dict[time_key]
            new_strength = current_pattern.strength + (
                interaction_weight * self.learning_rate
            )
            patterns_dict[time_key] = PreferencePattern(
                pattern_type=time_key,
                strength=min(1.0, new_strength),
                confidence=min(1.0, current_pattern.confidence + 0.05),
                last_updated=datetime.now(),
            )
        else:
            patterns_dict[time_key] = PreferencePattern(
                pattern_type=time_key,
                strength=interaction_weight * self.learning_rate,
                confidence=0.2,
                last_updated=datetime.now(),
            )

        # Content type patterns
        content_type_key = f"content_{content_item.content_type.value}"
        if content_type_key in patterns_dict:
            current_pattern = patterns_dict[content_type_key]
            new_strength = current_pattern.strength + (
                interaction_weight * self.learning_rate
            )
            patterns_dict[content_type_key] = PreferencePattern(
                pattern_type=content_type_key,
                strength=min(1.0, new_strength),
                confidence=min(1.0, current_pattern.confidence + 0.05),
                last_updated=datetime.now(),
            )
        else:
            patterns_dict[content_type_key] = PreferencePattern(
                pattern_type=content_type_key,
                strength=interaction_weight * self.learning_rate,
                confidence=0.2,
                last_updated=datetime.now(),
            )

        return list(patterns_dict.values())

    async def _convert_feedback_to_weight(self, feedback: UserFeedback) -> float:
        """Convert user feedback to learning weight"""
        if feedback.feedback_type == FeedbackType.RATING:
            # Convert 1-5 rating to -1 to 1 weight
            normalized_rating = (feedback.feedback_value - 3.0) / 2.0
            return normalized_rating * 2.0  # Amplify feedback signal

        if feedback.feedback_type == FeedbackType.THUMBS:
            return 2.0 if feedback.feedback_value > 0 else -2.0

        if feedback.feedback_type == FeedbackType.RELEVANCE:
            # Relevance feedback (0-1) converted to weight
            return (feedback.feedback_value - 0.5) * 4.0

        return 0.0

    async def _normalize_preferences(self, user_profile: UserProfile) -> UserProfile:
        """Normalize preferences to prevent excessive drift"""
        # Normalize interest weights
        total_weight = sum(interest.weight for interest in user_profile.interests)
        if total_weight > 10.0:  # If total weight is too high, normalize
            scale_factor = 10.0 / total_weight
            normalized_interests = [
                InterestCategory(
                    name=interest.name,
                    weight=interest.weight * scale_factor,
                    confidence=interest.confidence,
                    last_updated=interest.last_updated,
                )
                for interest in user_profile.interests
            ]
        else:
            normalized_interests = user_profile.interests

        # Normalize preference vector
        normalized_vector = user_profile.preference_vector
        if normalized_vector and len(normalized_vector.vector) > 0:
            norm = np.linalg.norm(normalized_vector.vector)
            if norm > 2.0:  # If vector norm is too large, normalize
                normalized_vector = ContentEmbedding(
                    vector=normalized_vector.vector / (norm / 2.0),
                    dimension=normalized_vector.dimension,
                    model_name=normalized_vector.model_name,
                )

        return UserProfile(
            user_id=user_profile.user_id,
            interests=normalized_interests,
            preference_vector=normalized_vector,
            preference_patterns=user_profile.preference_patterns,
            total_interactions=user_profile.total_interactions,
            last_activity=user_profile.last_activity,
            learning_rate=user_profile.learning_rate,
            exploration_factor=user_profile.exploration_factor,
            created_at=user_profile.created_at,
            updated_at=datetime.now(),
        )

    async def _calculate_interest_trend(
        self,
        interest: str,
        scores: list[float],
        period_days: int,
    ) -> InterestEvolution | None:
        """Calculate trend for a specific interest"""
        if len(scores) < 2:
            return None

        # Simple linear trend calculation
        n = len(scores)
        x = list(range(n))
        y = scores

        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return None

        slope = numerator / denominator

        # Determine trend direction and strength
        if slope > 0.01:
            direction = "increasing"
            strength = min(1.0, abs(slope) * 10)
        elif slope < -0.01:
            direction = "decreasing"
            strength = min(1.0, abs(slope) * 10)
        else:
            direction = "stable"
            strength = 1.0 - abs(slope) * 10

        # Calculate confidence based on data consistency
        variance = sum((score - y_mean) ** 2 for score in scores) / n
        confidence = max(0.1, 1.0 - variance)

        return InterestEvolution(
            user_id="",  # Will be set by caller
            interest_name=interest,
            trend_direction=direction,
            trend_strength=strength,
            period_days=period_days,
            confidence=confidence,
        )

    async def _calculate_preference_diversity(self, user_profile: UserProfile) -> float:
        """Calculate how diverse user's preferences are"""
        if not user_profile.interests:
            return 0.0

        # Calculate entropy of interest weights
        weights = [interest.weight for interest in user_profile.interests]
        total_weight = sum(weights)

        if total_weight == 0:
            return 0.0

        # Normalize weights
        probabilities = [w / total_weight for w in weights]

        # Calculate Shannon entropy
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)

        # Normalize by maximum possible entropy
        max_entropy = math.log2(len(probabilities))
        diversity = entropy / max_entropy if max_entropy > 0 else 0.0

        return diversity

    async def _analyze_engagement_patterns(
        self,
        interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> dict[str, Any]:
        """Analyze user engagement patterns"""
        if not interactions:
            return {}

        # Analyze interaction types
        interaction_counts = Counter(
            interaction.interaction_type for interaction, _ in interactions
        )

        # Analyze time patterns
        hours = [interaction.timestamp.hour for interaction, _ in interactions]
        hour_counts = Counter(hours)

        # Analyze content type preferences
        content_types = [content.content_type for _, content in interactions]
        content_type_counts = Counter(content_types)

        # Calculate session patterns (interactions within 1 hour)
        session_lengths = []
        current_session = []
        for interaction, _ in sorted(interactions, key=lambda x: x[0].timestamp):
            if (
                current_session
                and (
                    interaction.timestamp - current_session[-1].timestamp
                ).total_seconds()
                > 3600
            ):
                session_lengths.append(len(current_session))
                current_session = [interaction]
            else:
                current_session.append(interaction)
        if current_session:
            session_lengths.append(len(current_session))

        return {
            "interaction_types": dict(interaction_counts),
            "active_hours": dict(hour_counts),
            "content_type_preferences": dict(content_type_counts),
            "avg_session_length": (
                sum(session_lengths) / len(session_lengths) if session_lengths else 0
            ),
            "total_sessions": len(session_lengths),
            "most_active_hour": (
                max(hour_counts, key=hour_counts.get) if hour_counts else 12
            ),
        }

    async def _calculate_learning_velocity(
        self,
        user_profile: UserProfile,
        recent_interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> float:
        """Calculate how quickly user preferences change"""
        if len(recent_interactions) < 5:
            return 0.5  # Default medium velocity

        # Analyze how much interests have changed recently
        time_windows = [7, 14, 30]  # Days
        velocity_scores = []

        for window in time_windows:
            cutoff = datetime.now() - timedelta(days=window)
            window_interactions = [
                (interaction, content)
                for interaction, content in recent_interactions
                if interaction.timestamp >= cutoff
            ]

            if len(window_interactions) < 2:
                continue

            # Calculate interest distribution in this window
            interest_counts = Counter()
            for _, content in window_interactions:
                for tag in content.topic_tags:
                    interest_counts[tag] += 1

            # Compare with overall profile
            profile_interests = {
                interest.name: interest.weight for interest in user_profile.interests
            }

            # Calculate distribution difference
            overlap = 0
            total_window_interests = sum(interest_counts.values())
            for interest, count in interest_counts.items():
                window_weight = count / total_window_interests
                profile_weight = profile_interests.get(interest, 0)
                overlap += min(window_weight, profile_weight)

            # Lower overlap = higher velocity
            velocity_scores.append(1.0 - overlap)

        return sum(velocity_scores) / len(velocity_scores) if velocity_scores else 0.5

    async def _calculate_discovery_propensity(
        self,
        recent_interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> float:
        """Calculate user's propensity to discover new content"""
        if not recent_interactions:
            return 0.5

        # Analyze content diversity in recent interactions
        all_topics = set()
        content_sources = set()
        content_types = set()

        for _, content in recent_interactions:
            all_topics.update(content.topic_tags)
            content_sources.add(content.source)
            content_types.add(content.content_type)

        # Calculate diversity metrics
        topic_diversity = len(all_topics) / max(1, len(recent_interactions))
        source_diversity = len(content_sources) / max(1, len(recent_interactions))
        type_diversity = len(content_types) / max(1, len(recent_interactions))

        # Combine diversity metrics
        discovery_propensity = (
            topic_diversity + source_diversity + type_diversity
        ) / 3.0

        return min(1.0, discovery_propensity)

    async def _calculate_exploration_score(
        self,
        user_profile: UserProfile,
        category: TopicCategory,
        exploration_factor: float,
    ) -> float:
        """Calculate exploration score for a category"""
        # Base score from category popularity
        popularity_score = (
            category.metrics.popularity_score if category.metrics else 0.3
        )

        # Similarity to existing interests
        similarity_score = 0.0
        user_interests = {interest.name.lower() for interest in user_profile.interests}

        # Check keyword overlap
        category_keywords = set(category.keywords) if category.keywords else set()
        user_keywords = set()
        for interest in user_profile.interests:
            user_keywords.add(interest.name.lower())

        if category_keywords and user_keywords:
            overlap = len(category_keywords.intersection(user_keywords))
            similarity_score = overlap / len(category_keywords.union(user_keywords))

        # Exploration score balances popularity and novelty
        exploration_score = (
            popularity_score * (1 - exploration_factor)
            + (1 - similarity_score) * exploration_factor
        )

        return exploration_score

    async def _calculate_interaction_consistency(
        self,
        interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> float:
        """Calculate consistency of user interactions"""
        if len(interactions) < 3:
            return 0.5

        # Analyze interaction type consistency
        interaction_types = [
            interaction.interaction_type for interaction, _ in interactions
        ]
        type_distribution = Counter(interaction_types)

        # Calculate entropy (lower entropy = more consistent)
        total = len(interaction_types)
        entropy = -sum(
            (count / total) * math.log2(count / total)
            for count in type_distribution.values()
        )
        max_entropy = math.log2(len(type_distribution))

        # Convert to consistency score (inverse of normalized entropy)
        consistency = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0

        return consistency

    async def _calculate_preference_stability(
        self,
        user_profile: UserProfile,
        recent_interactions: list[tuple[UserInteraction, ContentItem]],
    ) -> float:
        """Calculate stability of user preferences"""
        if not recent_interactions:
            return 0.5

        # Calculate recent interest distribution
        recent_interests = Counter()
        for _, content in recent_interactions:
            for tag in content.topic_tags:
                recent_interests[tag] += 1

        # Normalize recent interests
        total_recent = sum(recent_interests.values())
        recent_distribution = {
            interest: count / total_recent
            for interest, count in recent_interests.items()
        }

        # Compare with profile interests
        profile_distribution = {}
        total_profile_weight = sum(
            interest.weight for interest in user_profile.interests
        )

        if total_profile_weight > 0:
            for interest in user_profile.interests:
                profile_distribution[interest.name] = (
                    interest.weight / total_profile_weight
                )

        # Calculate distribution similarity (stability)
        all_interests = set(recent_distribution.keys()).union(
            set(profile_distribution.keys()),
        )

        if not all_interests:
            return 0.5

        # Calculate cosine similarity between distributions
        recent_vector = [
            recent_distribution.get(interest, 0) for interest in all_interests
        ]
        profile_vector = [
            profile_distribution.get(interest, 0) for interest in all_interests
        ]

        # Cosine similarity
        dot_product = sum(
            r * p for r, p in zip(recent_vector, profile_vector, strict=False)
        )
        recent_norm = math.sqrt(sum(r * r for r in recent_vector))
        profile_norm = math.sqrt(sum(p * p for p in profile_vector))

        if recent_norm == 0 or profile_norm == 0:
            return 0.0

        stability = dot_product / (recent_norm * profile_norm)
        return max(0.0, stability)
