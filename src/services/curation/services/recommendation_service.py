"""RecommendationService

Advanced ML-powered recommendation system that provides personalized content recommendations
based on user preferences, interaction history, content analysis, and collaborative filtering.
Supports multiple recommendation strategies and real-time personalization.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..models.content_item import ContentEmbedding, ContentItem
from ..models.recommendation import (
    FeatureWeights,
    Recommendation,
    RecommendationExplanation,
)
from ..models.user_interaction import InteractionType, UserInteraction
from ..models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class RecommendationStrategy(str, Enum):
    """Different recommendation strategies"""

    CONTENT_BASED = "content_based"  # Based on content similarity
    COLLABORATIVE = "collaborative"  # Based on user similarity
    HYBRID = "hybrid"  # Combination of multiple strategies
    TRENDING = "trending"  # Popular/trending content
    DIVERSITY = "diversity"  # Diverse content exploration
    SERENDIPITY = "serendipity"  # Unexpected discoveries


@dataclass(frozen=True)
class RecommendationRequest:
    """Request for content recommendations"""

    user_profile: UserProfile
    num_recommendations: int = 10
    strategy: RecommendationStrategy = RecommendationStrategy.HYBRID
    exclude_seen: bool = True
    include_explanation: bool = True
    diversity_factor: float = 0.2  # 0.0 = pure relevance, 1.0 = maximum diversity
    recency_bias: float = 0.1  # How much to favor recent content
    categories: list[str] | None = None  # Specific categories to focus on


@dataclass(frozen=True)
class ScoredContent:
    """Content item with recommendation score and explanation"""

    content_item: ContentItem
    relevance_score: float
    diversity_score: float
    final_score: float
    feature_contributions: dict[str, float]
    explanation: str


@dataclass(frozen=True)
class RecommendationResult:
    """Complete recommendation result"""

    user_id: str
    recommendations: list[Recommendation]
    strategy_used: RecommendationStrategy
    total_candidates: int
    processing_time_ms: float
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)


class RecommendationService:
    """Advanced recommendation service with multiple ML strategies.

    Provides personalized content recommendations using content-based filtering,
    collaborative filtering, and hybrid approaches with real-time learning.
    """

    def __init__(
        self,
        enable_collaborative: bool = True,
        enable_diversity: bool = True,
        min_interactions_for_cf: int = 5,
    ):
        """Initialize recommendation service.

        Args:
            enable_collaborative: Whether to use collaborative filtering
            enable_diversity: Whether to apply diversity algorithms
            min_interactions_for_cf: Minimum interactions needed for collaborative filtering
        """
        self.enable_collaborative = enable_collaborative
        self.enable_diversity = enable_diversity
        self.min_interactions_for_cf = min_interactions_for_cf

        # ML models and data
        self._content_vectors = {}  # content_id -> embedding vector
        self._user_content_matrix = None  # For collaborative filtering
        self._content_features = {}  # content_id -> feature vector
        self._category_embeddings = {}  # category -> embedding

        # TF-IDF vectorizer for content features
        self._tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words="english",
            ngram_range=(1, 2),
        )

        # Recommendation weights for hybrid approach
        self.strategy_weights = {
            RecommendationStrategy.CONTENT_BASED: 0.4,
            RecommendationStrategy.COLLABORATIVE: 0.3,
            RecommendationStrategy.TRENDING: 0.2,
            RecommendationStrategy.DIVERSITY: 0.1,
        }

        logger.info("RecommendationService initialized")

    async def get_recommendations(
        self,
        request: RecommendationRequest,
        available_content: list[ContentItem],
        user_interactions: list[UserInteraction],
        all_user_interactions: list[UserInteraction] | None = None,
    ) -> RecommendationResult:
        """Generate personalized content recommendations.

        Args:
            request: Recommendation request with parameters
            available_content: Pool of content to recommend from
            user_interactions: Current user's interaction history
            all_user_interactions: All users' interactions for collaborative filtering

        Returns:
            Complete recommendation result with explanations
        """
        start_time = datetime.now()

        try:
            # Filter content based on request parameters
            candidates = await self._filter_candidates(
                available_content,
                request,
                user_interactions,
            )

            if not candidates:
                return self._create_empty_result(request, 0.0)

            # Generate recommendations based on strategy
            if request.strategy == RecommendationStrategy.CONTENT_BASED:
                scored_content = await self._content_based_recommendations(
                    request,
                    candidates,
                    user_interactions,
                )
            elif request.strategy == RecommendationStrategy.COLLABORATIVE:
                scored_content = await self._collaborative_recommendations(
                    request,
                    candidates,
                    user_interactions,
                    all_user_interactions,
                )
            elif request.strategy == RecommendationStrategy.TRENDING:
                scored_content = await self._trending_recommendations(
                    request,
                    candidates,
                )
            elif request.strategy == RecommendationStrategy.DIVERSITY:
                scored_content = await self._diversity_recommendations(
                    request,
                    candidates,
                    user_interactions,
                )
            else:  # HYBRID or SERENDIPITY
                scored_content = await self._hybrid_recommendations(
                    request,
                    candidates,
                    user_interactions,
                    all_user_interactions,
                )

            # Apply diversity if enabled
            if self.enable_diversity and request.diversity_factor > 0:
                scored_content = await self._apply_diversity_reranking(
                    scored_content,
                    request.diversity_factor,
                )

            # Convert to recommendations
            recommendations = await self._create_recommendations(
                scored_content[: request.num_recommendations],
                request.include_explanation,
            )

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            result = RecommendationResult(
                user_id=str(request.user_profile.user_id),
                recommendations=recommendations,
                strategy_used=request.strategy,
                total_candidates=len(candidates),
                processing_time_ms=processing_time,
                explanation=self._generate_result_explanation(
                    request,
                    len(candidates),
                    len(recommendations),
                ),
                metadata={
                    "diversity_factor": request.diversity_factor,
                    "recency_bias": request.recency_bias,
                    "categories_requested": request.categories,
                },
            )

            logger.info(
                f"Generated {len(recommendations)} recommendations for user {
                    request.user_profile.user_id
                }",
            )
            return result

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return self._create_error_result(request, processing_time)

    async def _filter_candidates(
        self,
        content: list[ContentItem],
        request: RecommendationRequest,
        user_interactions: list[UserInteraction],
    ) -> list[ContentItem]:
        """Filter content to create candidate pool"""
        # Get content IDs the user has already interacted with
        seen_content_ids = set()
        if request.exclude_seen:
            seen_content_ids = {
                interaction.content_id
                for interaction in user_interactions
                if interaction.interaction_type
                in [InteractionType.VIEW, InteractionType.SAVE, InteractionType.SHARE]
            }

        candidates = []
        for item in content:
            # Skip seen content if requested
            if request.exclude_seen and item.id in seen_content_ids:
                continue

            # Filter by categories if specified
            if request.categories:
                item_categories = [tag.lower() for tag in item.topic_tags]
                requested_categories = [cat.lower() for cat in request.categories]
                if not any(cat in item_categories for cat in requested_categories):
                    continue

            # Only include active content
            if not item.is_active:
                continue

            candidates.append(item)

        return candidates

    async def _content_based_recommendations(
        self,
        request: RecommendationRequest,
        candidates: list[ContentItem],
        user_interactions: list[UserInteraction],
    ) -> list[ScoredContent]:
        """Generate content-based recommendations using similarity"""
        # Build user preference profile from interactions
        user_preference_vector = await self._build_user_preference_vector(
            request.user_profile,
            user_interactions,
            candidates,
        )

        if user_preference_vector is None:
            # Fallback to trending if no preference data
            return await self._trending_recommendations(request, candidates)

        scored_items = []

        for content in candidates:
            # Get content embedding
            content_embedding = await self._get_content_embedding(content)

            if content_embedding is None:
                continue

            # Calculate similarity to user preferences
            similarity_score = self._calculate_cosine_similarity(
                user_preference_vector,
                content_embedding.vector,
            )

            # Apply recency bias
            recency_score = self._calculate_recency_score(content, request.recency_bias)
            final_score = (
                similarity_score * (1 - request.recency_bias)
                + recency_score * request.recency_bias
            )

            # Feature contributions for explanation
            feature_contributions = {
                "content_similarity": similarity_score,
                "recency": recency_score,
                "quality": content.quality_score or 0.5,
            }

            explanation = (
                f"Similar to your interests (similarity: {similarity_score:.2f})"
            )

            scored_items.append(
                ScoredContent(
                    content_item=content,
                    relevance_score=similarity_score,
                    diversity_score=0.0,  # Will be calculated later if needed
                    final_score=final_score,
                    feature_contributions=feature_contributions,
                    explanation=explanation,
                ),
            )

        # Sort by final score
        scored_items.sort(key=lambda x: x.final_score, reverse=True)
        return scored_items

    async def _collaborative_recommendations(
        self,
        request: RecommendationRequest,
        candidates: list[ContentItem],
        user_interactions: list[UserInteraction],
        all_user_interactions: list[UserInteraction] | None,
    ) -> list[ScoredContent]:
        """Generate collaborative filtering recommendations"""
        if (
            not all_user_interactions
            or len(user_interactions) < self.min_interactions_for_cf
        ):
            # Fall back to content-based if insufficient data
            return await self._content_based_recommendations(
                request,
                candidates,
                user_interactions,
            )

        # Build user-item interaction matrix
        user_item_matrix = await self._build_user_item_matrix(
            all_user_interactions,
            candidates,
        )

        if user_item_matrix is None:
            return await self._content_based_recommendations(
                request,
                candidates,
                user_interactions,
            )

        user_id = str(request.user_profile.user_id)
        user_similarities = await self._find_similar_users(user_id, user_item_matrix)

        scored_items = []
        for content in candidates:
            content_id = str(content.id)

            # Calculate collaborative score based on similar users
            collaborative_score = 0.0
            total_weight = 0.0

            for similar_user_id, similarity in user_similarities:
                if similar_user_id != user_id and content_id in user_item_matrix.get(
                    similar_user_id,
                    {},
                ):
                    user_rating = user_item_matrix[similar_user_id][content_id]
                    collaborative_score += similarity * user_rating
                    total_weight += similarity

            if total_weight > 0:
                collaborative_score /= total_weight
            else:
                collaborative_score = (
                    0.5  # Neutral score if no similar users interacted
                )

            # Apply recency bias
            recency_score = self._calculate_recency_score(content, request.recency_bias)
            final_score = (
                collaborative_score * (1 - request.recency_bias)
                + recency_score * request.recency_bias
            )

            feature_contributions = {
                "collaborative_filtering": collaborative_score,
                "recency": recency_score,
                "quality": content.quality_score or 0.5,
            }

            explanation = f"Recommended by users similar to you (score: {collaborative_score:.2f})"

            scored_items.append(
                ScoredContent(
                    content_item=content,
                    relevance_score=collaborative_score,
                    diversity_score=0.0,
                    final_score=final_score,
                    feature_contributions=feature_contributions,
                    explanation=explanation,
                ),
            )

        scored_items.sort(key=lambda x: x.final_score, reverse=True)
        return scored_items

    async def _trending_recommendations(
        self,
        request: RecommendationRequest,
        candidates: list[ContentItem],
    ) -> list[ScoredContent]:
        """Generate trending/popular content recommendations"""
        scored_items = []

        for content in candidates:
            # Calculate trending score based on various factors
            trending_score = 0.0

            # Engagement metrics weight
            if content.engagement_metrics:
                views = content.engagement_metrics.get("views", 0)
                shares = content.engagement_metrics.get("shares", 0)
                saves = content.engagement_metrics.get("saves", 0)

                # Normalize engagement (assuming these are reasonable maximums)
                engagement_score = min(
                    1.0,
                    (views / 1000 + shares * 5 + saves * 10) / 100,
                )
                trending_score += engagement_score * 0.4

            # Quality score weight
            if content.quality_score:
                trending_score += content.quality_score * 0.3

            # Recency weight (more recent = more trending)
            recency_score = self._calculate_recency_score(
                content,
                0.3,
            )  # Higher recency bias for trending
            trending_score += recency_score * 0.3

            feature_contributions = {
                "engagement": (
                    content.engagement_metrics.get("total_engagement", 0)
                    if content.engagement_metrics
                    else 0
                ),
                "quality": content.quality_score or 0.5,
                "recency": recency_score,
            }

            explanation = "Trending content with high engagement and quality"

            scored_items.append(
                ScoredContent(
                    content_item=content,
                    relevance_score=trending_score,
                    diversity_score=0.0,
                    final_score=trending_score,
                    feature_contributions=feature_contributions,
                    explanation=explanation,
                ),
            )

        scored_items.sort(key=lambda x: x.final_score, reverse=True)
        return scored_items

    async def _diversity_recommendations(
        self,
        request: RecommendationRequest,
        candidates: list[ContentItem],
        user_interactions: list[UserInteraction],
    ) -> list[ScoredContent]:
        """Generate diverse content recommendations to encourage exploration"""
        # First get content-based recommendations as baseline
        content_based = await self._content_based_recommendations(
            request,
            candidates,
            user_interactions,
        )

        # Apply diversity algorithm
        diverse_items = []
        selected_embeddings = []

        for scored_content in content_based:
            content_embedding = await self._get_content_embedding(
                scored_content.content_item,
            )

            if content_embedding is None:
                continue

            # Calculate diversity score (how different from already selected items)
            diversity_score = 1.0  # Maximum diversity for first item

            if selected_embeddings:
                # Calculate minimum similarity to selected items
                similarities = [
                    self._calculate_cosine_similarity(
                        content_embedding.vector,
                        selected_emb,
                    )
                    for selected_emb in selected_embeddings
                ]
                # Lower similarity = higher diversity
                diversity_score = 1.0 - max(similarities)

            # Combine relevance and diversity
            final_score = scored_content.relevance_score * 0.6 + diversity_score * 0.4

            feature_contributions = scored_content.feature_contributions.copy()
            feature_contributions["diversity"] = diversity_score

            explanation = (
                f"Diverse content recommendation (diversity: {diversity_score:.2f})"
            )

            diverse_item = ScoredContent(
                content_item=scored_content.content_item,
                relevance_score=scored_content.relevance_score,
                diversity_score=diversity_score,
                final_score=final_score,
                feature_contributions=feature_contributions,
                explanation=explanation,
            )

            diverse_items.append(diverse_item)
            selected_embeddings.append(content_embedding.vector)

            # Limit selection to avoid too much computation
            if len(diverse_items) >= request.num_recommendations * 2:
                break

        diverse_items.sort(key=lambda x: x.final_score, reverse=True)
        return diverse_items

    async def _hybrid_recommendations(
        self,
        request: RecommendationRequest,
        candidates: list[ContentItem],
        user_interactions: list[UserInteraction],
        all_user_interactions: list[UserInteraction] | None,
    ) -> list[ScoredContent]:
        """Generate hybrid recommendations combining multiple strategies"""
        # Get recommendations from different strategies
        strategies_results = await asyncio.gather(
            self._content_based_recommendations(request, candidates, user_interactions),
            self._collaborative_recommendations(
                request,
                candidates,
                user_interactions,
                all_user_interactions,
            ),
            self._trending_recommendations(request, candidates),
            return_exceptions=True,
        )

        content_based, collaborative, trending = strategies_results

        # Handle any exceptions
        if isinstance(content_based, Exception):
            content_based = []
        if isinstance(collaborative, Exception):
            collaborative = []
        if isinstance(trending, Exception):
            trending = []

        # Combine scores from different strategies
        content_scores = {}

        # Add content-based scores
        for scored_content in content_based:
            content_id = str(scored_content.content_item.id)
            content_scores[content_id] = {
                "item": scored_content.content_item,
                "content_based": scored_content.final_score,
                "collaborative": 0.0,
                "trending": 0.0,
                "features": scored_content.feature_contributions,
            }

        # Add collaborative scores
        for scored_content in collaborative:
            content_id = str(scored_content.content_item.id)
            if content_id in content_scores:
                content_scores[content_id]["collaborative"] = scored_content.final_score
            else:
                content_scores[content_id] = {
                    "item": scored_content.content_item,
                    "content_based": 0.0,
                    "collaborative": scored_content.final_score,
                    "trending": 0.0,
                    "features": scored_content.feature_contributions,
                }

        # Add trending scores
        for scored_content in trending:
            content_id = str(scored_content.content_item.id)
            if content_id in content_scores:
                content_scores[content_id]["trending"] = scored_content.final_score
            else:
                content_scores[content_id] = {
                    "item": scored_content.content_item,
                    "content_based": 0.0,
                    "collaborative": 0.0,
                    "trending": scored_content.final_score,
                    "features": scored_content.feature_contributions,
                }

        # Calculate weighted hybrid scores
        hybrid_items = []
        for content_id, scores in content_scores.items():
            hybrid_score = (
                scores["content_based"]
                * self.strategy_weights[RecommendationStrategy.CONTENT_BASED]
                + scores["collaborative"]
                * self.strategy_weights[RecommendationStrategy.COLLABORATIVE]
                + scores["trending"]
                * self.strategy_weights[RecommendationStrategy.TRENDING]
            )

            # Apply recency bias
            recency_score = self._calculate_recency_score(
                scores["item"],
                request.recency_bias,
            )
            final_score = (
                hybrid_score * (1 - request.recency_bias)
                + recency_score * request.recency_bias
            )

            feature_contributions = scores["features"].copy()
            feature_contributions.update(
                {
                    "content_based_score": scores["content_based"],
                    "collaborative_score": scores["collaborative"],
                    "trending_score": scores["trending"],
                    "hybrid_score": hybrid_score,
                    "recency": recency_score,
                },
            )

            explanation = f"Hybrid recommendation combining multiple strategies (score: {hybrid_score:.2f})"

            hybrid_items.append(
                ScoredContent(
                    content_item=scores["item"],
                    relevance_score=hybrid_score,
                    diversity_score=0.0,
                    final_score=final_score,
                    feature_contributions=feature_contributions,
                    explanation=explanation,
                ),
            )

        hybrid_items.sort(key=lambda x: x.final_score, reverse=True)
        return hybrid_items

    async def _apply_diversity_reranking(
        self,
        scored_content: list[ScoredContent],
        diversity_factor: float,
    ) -> list[ScoredContent]:
        """Apply diversity re-ranking to recommendations"""
        if not scored_content or diversity_factor <= 0:
            return scored_content

        reranked = []
        remaining = scored_content.copy()
        selected_embeddings = []

        while remaining and len(reranked) < len(scored_content):
            best_item = None
            best_score = -1.0

            for item in remaining:
                content_embedding = await self._get_content_embedding(item.content_item)

                if content_embedding is None:
                    continue

                # Calculate diversity score
                diversity_score = 1.0
                if selected_embeddings:
                    similarities = [
                        self._calculate_cosine_similarity(
                            content_embedding.vector,
                            selected_emb,
                        )
                        for selected_emb in selected_embeddings
                    ]
                    diversity_score = 1.0 - max(similarities)

                # Combine relevance and diversity
                combined_score = (
                    item.relevance_score * (1 - diversity_factor)
                    + diversity_score * diversity_factor
                )

                if combined_score > best_score:
                    best_score = combined_score
                    best_item = item

            if best_item:
                # Update diversity score and final score
                content_embedding = await self._get_content_embedding(
                    best_item.content_item,
                )
                diversity_score = 1.0
                if selected_embeddings:
                    similarities = [
                        self._calculate_cosine_similarity(
                            content_embedding.vector,
                            selected_emb,
                        )
                        for selected_emb in selected_embeddings
                    ]
                    diversity_score = 1.0 - max(similarities)

                updated_item = ScoredContent(
                    content_item=best_item.content_item,
                    relevance_score=best_item.relevance_score,
                    diversity_score=diversity_score,
                    final_score=best_score,
                    feature_contributions=best_item.feature_contributions,
                    explanation=best_item.explanation,
                )

                reranked.append(updated_item)
                remaining.remove(best_item)
                if content_embedding:
                    selected_embeddings.append(content_embedding.vector)

        return reranked

    async def _build_user_preference_vector(
        self,
        user_profile: UserProfile,
        user_interactions: list[UserInteraction],
        available_content: list[ContentItem],
    ) -> np.ndarray | None:
        """Build user preference vector from profile and interactions"""
        # Start with profile preference vector if available
        if (
            user_profile.preference_vector
            and len(user_profile.preference_vector.vector) > 0
        ):
            preference_vector = user_profile.preference_vector.vector.copy()
        else:
            preference_vector = None

        # Weight interactions by type and recency
        weighted_embeddings = []
        weights = []

        for interaction in user_interactions:
            # Find the content item
            content_item = None
            for content in available_content:
                if content.id == interaction.content_id:
                    content_item = content
                    break

            if content_item and content_item.content_embedding:
                # Calculate interaction weight
                interaction_weight = interaction.get_weighted_value()

                # Apply recency decay (interactions lose weight over time)
                days_old = (datetime.now() - interaction.timestamp).days
                recency_weight = math.exp(-days_old / 30.0)  # 30-day half-life

                final_weight = interaction_weight * recency_weight
                weighted_embeddings.append(content_item.content_embedding.vector)
                weights.append(final_weight)

        if weighted_embeddings:
            # Calculate weighted average of embeddings
            weighted_embeddings = np.array(weighted_embeddings)
            weights = np.array(weights)

            if preference_vector is not None:
                # Combine with existing preference vector
                interaction_vector = np.average(
                    weighted_embeddings,
                    axis=0,
                    weights=weights,
                )
                # Weight profile vector higher if it exists
                preference_vector = preference_vector * 0.7 + interaction_vector * 0.3
            else:
                preference_vector = np.average(
                    weighted_embeddings,
                    axis=0,
                    weights=weights,
                )

        return preference_vector

    async def _build_user_item_matrix(
        self,
        all_interactions: list[UserInteraction],
        available_content: list[ContentItem],
    ) -> dict[str, dict[str, float]] | None:
        """Build user-item interaction matrix for collaborative filtering"""
        if not all_interactions:
            return None

        user_item_matrix = {}
        content_ids = {str(content.id) for content in available_content}

        for interaction in all_interactions:
            user_id = str(interaction.user_id)
            content_id = str(interaction.content_id)

            # Only include interactions with available content
            if content_id not in content_ids:
                continue

            if user_id not in user_item_matrix:
                user_item_matrix[user_id] = {}

            # Calculate rating based on interaction type and recency
            rating = interaction.get_weighted_value()
            days_old = (datetime.now() - interaction.timestamp).days
            # 60-day half-life for collaborative
            recency_weight = math.exp(-days_old / 60.0)

            final_rating = rating * recency_weight

            # If user has multiple interactions with same content, take maximum
            if content_id in user_item_matrix[user_id]:
                user_item_matrix[user_id][content_id] = max(
                    user_item_matrix[user_id][content_id],
                    final_rating,
                )
            else:
                user_item_matrix[user_id][content_id] = final_rating

        return user_item_matrix if user_item_matrix else None

    async def _find_similar_users(
        self,
        user_id: str,
        user_item_matrix: dict[str, dict[str, float]],
    ) -> list[tuple[str, float]]:
        """Find users similar to the target user"""
        if user_id not in user_item_matrix:
            return []

        target_user_items = user_item_matrix[user_id]
        similarities = []

        for other_user_id, other_user_items in user_item_matrix.items():
            if other_user_id == user_id:
                continue

            # Find common items
            common_items = set(target_user_items.keys()).intersection(
                set(other_user_items.keys()),
            )

            if len(common_items) < 2:  # Need at least 2 items in common
                continue

            # Calculate cosine similarity
            target_ratings = [target_user_items[item] for item in common_items]
            other_ratings = [other_user_items[item] for item in common_items]

            similarity = self._calculate_cosine_similarity(
                np.array(target_ratings),
                np.array(other_ratings),
            )

            if similarity > 0.1:  # Only consider reasonably similar users
                similarities.append((other_user_id, similarity))

        # Sort by similarity and return top users
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:10]  # Top 10 similar users

    async def _get_content_embedding(
        self,
        content_item: ContentItem,
    ) -> ContentEmbedding | None:
        """Get or generate content embedding"""
        if (
            content_item.content_embedding
            and len(content_item.content_embedding.vector) > 0
        ):
            return content_item.content_embedding

        # If no embedding, this would need to be generated by ContentAnalysisService
        # For now, return None - in real implementation, we'd call the analysis service
        return None

    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except BaseException:
            return 0.0

    def _calculate_recency_score(
        self,
        content_item: ContentItem,
        recency_bias: float,
    ) -> float:
        """Calculate recency score for content"""
        if not content_item.published_date:
            return 0.5  # Neutral score for unknown date

        days_old = (datetime.now() - content_item.published_date).days

        # Exponential decay for recency
        recency_score = math.exp(-days_old / 30.0)  # 30-day half-life
        return min(1.0, recency_score)

    async def _create_recommendations(
        self,
        scored_content: list[ScoredContent],
        include_explanation: bool,
    ) -> list[Recommendation]:
        """Convert scored content to Recommendation objects"""
        recommendations = []

        for i, scored in enumerate(scored_content):
            # Create explanation if requested
            explanation = None
            if include_explanation:
                explanation = RecommendationExplanation(
                    primary_reason=scored.explanation,
                    secondary_reasons=[],
                    confidence_score=min(1.0, scored.final_score),
                    feature_contributions=scored.feature_contributions,
                )

            # Create feature weights
            feature_weights = FeatureWeights(
                content_similarity=scored.feature_contributions.get(
                    "content_similarity",
                    0.0,
                ),
                user_preference_match=scored.feature_contributions.get(
                    "user_preference_match",
                    0.0,
                ),
                collaborative_score=scored.feature_contributions.get(
                    "collaborative_filtering",
                    0.0,
                ),
                trending_score=scored.feature_contributions.get("trending", 0.0),
                quality_score=scored.feature_contributions.get("quality", 0.0),
                recency_score=scored.feature_contributions.get("recency", 0.0),
                diversity_score=scored.diversity_score,
            )

            recommendation = Recommendation(
                id=f"rec_{scored.content_item.id}_{datetime.now().timestamp()}",
                user_id=None,  # Will be set by caller
                content_id=scored.content_item.id,
                relevance_score=scored.final_score,
                explanation=explanation,
                feature_weights=feature_weights,
                rank=i + 1,
                created_at=datetime.now(),
            )

            recommendations.append(recommendation)

        return recommendations

    def _generate_result_explanation(
        self,
        request: RecommendationRequest,
        total_candidates: int,
        num_recommendations: int,
    ) -> str:
        """Generate explanation for the recommendation result"""
        strategy_name = {
            RecommendationStrategy.CONTENT_BASED: "content similarity",
            RecommendationStrategy.COLLABORATIVE: "user similarity",
            RecommendationStrategy.HYBRID: "multiple algorithms",
            RecommendationStrategy.TRENDING: "popularity and engagement",
            RecommendationStrategy.DIVERSITY: "diverse exploration",
        }.get(request.strategy, "advanced algorithms")

        explanation = f"Generated {num_recommendations} recommendations from {
            total_candidates
        } candidates using {strategy_name}"

        if request.diversity_factor > 0:
            explanation += f" with {request.diversity_factor:.1%} diversity boost"

        if request.categories:
            explanation += f" focused on categories: {', '.join(request.categories)}"

        return explanation

    def _create_empty_result(
        self,
        request: RecommendationRequest,
        processing_time: float,
    ) -> RecommendationResult:
        """Create empty result when no recommendations can be generated"""
        return RecommendationResult(
            user_id=str(request.user_profile.user_id),
            recommendations=[],
            strategy_used=request.strategy,
            total_candidates=0,
            processing_time_ms=processing_time,
            explanation="No recommendations available with current criteria",
        )

    def _create_error_result(
        self,
        request: RecommendationRequest,
        processing_time: float,
    ) -> RecommendationResult:
        """Create error result when recommendation generation fails"""
        return RecommendationResult(
            user_id=str(request.user_profile.user_id),
            recommendations=[],
            strategy_used=request.strategy,
            total_candidates=0,
            processing_time_ms=processing_time,
            explanation="Error occurred during recommendation generation",
        )

    async def update_strategy_weights(
        self,
        performance_metrics: dict[RecommendationStrategy, float],
    ) -> None:
        """Update strategy weights based on performance feedback"""
        total_performance = sum(performance_metrics.values())

        if total_performance > 0:
            # Normalize and update weights
            for strategy, performance in performance_metrics.items():
                if strategy in self.strategy_weights:
                    # Smooth update to avoid drastic changes
                    new_weight = performance / total_performance
                    self.strategy_weights[strategy] = (
                        self.strategy_weights[strategy] * 0.8 + new_weight * 0.2
                    )

            logger.info(f"Updated strategy weights: {self.strategy_weights}")

    async def explain_recommendation(
        self,
        recommendation: Recommendation,
        content_item: ContentItem,
    ) -> str:
        """Generate detailed explanation for a specific recommendation"""
        if not recommendation.explanation:
            return "Recommended based on your preferences"

        explanation_parts = [recommendation.explanation.primary_reason]

        # Add feature contribution details
        if recommendation.feature_weights:
            fw = recommendation.feature_weights
            if fw.content_similarity > 0.5:
                explanation_parts.append(
                    f"High content similarity ({fw.content_similarity:.2f})",
                )
            if fw.collaborative_score > 0.5:
                explanation_parts.append(
                    f"Liked by similar users ({fw.collaborative_score:.2f})",
                )
            if fw.trending_score > 0.7:
                explanation_parts.append("Currently trending")
            if fw.quality_score > 0.8:
                explanation_parts.append("High quality content")

        return ". ".join(explanation_parts)
