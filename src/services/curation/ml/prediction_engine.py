"""Prediction Engine
Advanced prediction engine for real-time content curation and recommendation scoring.
Provides fast, cached predictions with model ensemble and fallback strategies.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from ..models.content_item import ContentItem
from ..models.user_interaction import UserInteraction
from ..models.user_profile import UserProfile
from .feature_extractor import ContentFeatures, FeatureExtractor, UserFeatures
from .model_trainer import ModelTrainer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PredictionResult:
    """Result of a prediction operation"""

    content_id: str
    user_id: str
    prediction_type: str  # 'quality', 'preference', 'recommendation'
    score: float
    confidence: float
    model_used: str
    features_used: int
    prediction_time_ms: float
    cached: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class EnsemblePrediction:
    """Ensemble prediction combining multiple models"""

    content_id: str
    user_id: str
    individual_predictions: list[PredictionResult]
    ensemble_score: float
    ensemble_confidence: float
    variance: float
    created_at: datetime = field(default_factory=datetime.now)


class PredictionEngine:
    """Advanced prediction engine for real-time content curation"""

    def __init__(self, cache_size: int = 10000, cache_ttl_hours: int = 1):
        self.cache_size = cache_size
        self.cache_ttl_hours = cache_ttl_hours
        self.prediction_cache: dict[str, PredictionResult] = {}
        self.feature_extractor = FeatureExtractor()
        self.model_trainer = ModelTrainer()

        # Performance tracking
        self.prediction_times: deque = deque(maxlen=1000)
        self.cache_hit_rate = 0.0
        self.total_predictions = 0
        self.cached_predictions = 0

        # Ensemble weights (can be learned from validation data)
        self.ensemble_weights = {
            "content_quality": {
                "RandomForest": 0.4,
                "GradientBoosting": 0.3,
                "SVR": 0.2,
                "MLP": 0.1,
            },
            "user_preference": {
                "LogisticRegression": 0.4,
                "RandomForest": 0.3,
                "MLP": 0.3,
            },
            "recommendation": {
                "RandomForest": 0.4,
                "GradientBoosting": 0.4,
                "MLP": 0.2,
            },
        }

        # Fallback strategies
        self.fallback_strategies = {
            "content_quality": self._fallback_content_quality,
            "user_preference": self._fallback_user_preference,
            "recommendation": self._fallback_recommendation,
        }

    def _get_cache_key(
        self,
        content_id: str,
        user_id: str,
        prediction_type: str,
    ) -> str:
        """Generate cache key for prediction"""
        return f"{prediction_type}:{content_id}:{user_id}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached prediction is still valid"""
        if cache_key not in self.prediction_cache:
            return False

        cached_result = self.prediction_cache[cache_key]
        age = datetime.now() - cached_result.created_at
        return age.total_seconds() < self.cache_ttl_hours * 3600

    async def predict_content_quality(
        self,
        content: ContentItem,
        use_cache: bool = True,
    ) -> PredictionResult:
        """Predict content quality score"""
        cache_key = self._get_cache_key(content.id, "system", "quality")

        if use_cache and self._is_cache_valid(cache_key):
            self.cached_predictions += 1
            cached_result = self.prediction_cache[cache_key]
            logger.debug(f"Using cached quality prediction for content {content.id}")
            return PredictionResult(
                content_id=content.id,
                user_id="system",
                prediction_type="quality",
                score=cached_result.score,
                confidence=cached_result.confidence,
                model_used=cached_result.model_used,
                features_used=cached_result.features_used,
                prediction_time_ms=0.1,  # Cache lookup time
                cached=True,
            )

        start_time = time.time()

        try:
            # Extract features
            content_features = await self.feature_extractor.extract_content_features(
                content,
            )
            feature_vector = await self.feature_extractor.get_feature_vector(
                content_features,
                UserFeatures(user_id="system"),
            )

            # Get prediction from model trainer
            score = await self.model_trainer.predict_content_quality(content)

            # Calculate confidence based on feature completeness
            confidence = self._calculate_quality_confidence(
                content_features,
                feature_vector,
            )

            prediction_time = (time.time() - start_time) * 1000

            result = PredictionResult(
                content_id=content.id,
                user_id="system",
                prediction_type="quality",
                score=score,
                confidence=confidence,
                model_used="content_quality_model",
                features_used=len(feature_vector),
                prediction_time_ms=prediction_time,
            )

            # Cache the result
            if use_cache:
                self.prediction_cache[cache_key] = result
                await self._manage_cache_size()

            self.total_predictions += 1
            self.prediction_times.append(prediction_time)

            logger.debug(
                f"Predicted quality for content {content.id}: {score:.3f} (confidence: {
                    confidence:.3f})",
            )
            return result

        except Exception as e:
            logger.error(f"Error predicting content quality for {content.id}: {e}")
            # Use fallback strategy
            return await self._fallback_content_quality(content)

    async def predict_user_preference(
        self,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
        use_cache: bool = True,
    ) -> PredictionResult:
        """Predict user preference category"""
        cache_key = self._get_cache_key("system", user_profile.user_id, "preference")

        if use_cache and self._is_cache_valid(cache_key):
            self.cached_predictions += 1
            cached_result = self.prediction_cache[cache_key]
            logger.debug(
                f"Using cached preference prediction for user {user_profile.user_id}",
            )
            return PredictionResult(
                content_id="system",
                user_id=user_profile.user_id,
                prediction_type="preference",
                score=cached_result.score,
                confidence=cached_result.confidence,
                model_used=cached_result.model_used,
                features_used=cached_result.features_used,
                prediction_time_ms=0.1,
                cached=True,
            )

        start_time = time.time()

        try:
            # Extract features
            user_features = await self.feature_extractor.extract_user_features(
                user_profile,
                interactions,
            )
            feature_vector = await self.feature_extractor.get_feature_vector(
                ContentFeatures(content_id="system"),
                user_features,
            )

            # Get prediction from model trainer
            preference_category = await self.model_trainer.predict_user_preference(
                user_profile,
                interactions,
            )

            # Convert category to score (0-1 scale)
            score = preference_category / 3.0  # Assuming 4 categories (0-3)

            # Calculate confidence based on interaction history
            confidence = self._calculate_preference_confidence(
                user_features,
                len(interactions),
            )

            prediction_time = (time.time() - start_time) * 1000

            result = PredictionResult(
                content_id="system",
                user_id=user_profile.user_id,
                prediction_type="preference",
                score=score,
                confidence=confidence,
                model_used="user_preference_model",
                features_used=len(feature_vector),
                prediction_time_ms=prediction_time,
            )

            # Cache the result
            if use_cache:
                self.prediction_cache[cache_key] = result
                await self._manage_cache_size()

            self.total_predictions += 1
            self.prediction_times.append(prediction_time)

            logger.debug(
                f"Predicted preference for user {user_profile.user_id}: {
                    preference_category
                } (confidence: {confidence:.3f})",
            )
            return result

        except Exception as e:
            logger.error(
                f"Error predicting user preference for {user_profile.user_id}: {e}",
            )
            # Use fallback strategy
            return await self._fallback_user_preference(user_profile, interactions)

    async def predict_recommendation_score(
        self,
        content: ContentItem,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
        use_cache: bool = True,
    ) -> PredictionResult:
        """Predict recommendation score for content-user pair"""
        cache_key = self._get_cache_key(
            content.id,
            user_profile.user_id,
            "recommendation",
        )

        if use_cache and self._is_cache_valid(cache_key):
            self.cached_predictions += 1
            cached_result = self.prediction_cache[cache_key]
            logger.debug(
                f"Using cached recommendation prediction for {content.id}:{
                    user_profile.user_id
                }",
            )
            return PredictionResult(
                content_id=content.id,
                user_id=user_profile.user_id,
                prediction_type="recommendation",
                score=cached_result.score,
                confidence=cached_result.confidence,
                model_used=cached_result.model_used,
                features_used=cached_result.features_used,
                prediction_time_ms=0.1,
                cached=True,
            )

        start_time = time.time()

        try:
            # Extract features
            content_features = await self.feature_extractor.extract_content_features(
                content,
            )
            user_features = await self.feature_extractor.extract_user_features(
                user_profile,
                interactions,
            )
            feature_vector = await self.feature_extractor.get_feature_vector(
                content_features,
                user_features,
            )

            # Get prediction from model trainer
            score = await self.model_trainer.predict_recommendation_score(
                content,
                user_profile,
                interactions,
            )

            # Calculate confidence based on feature quality and user history
            confidence = self._calculate_recommendation_confidence(
                content_features,
                user_features,
                len(interactions),
            )

            prediction_time = (time.time() - start_time) * 1000

            result = PredictionResult(
                content_id=content.id,
                user_id=user_profile.user_id,
                prediction_type="recommendation",
                score=score,
                confidence=confidence,
                model_used="recommendation_model",
                features_used=len(feature_vector),
                prediction_time_ms=prediction_time,
            )

            # Cache the result
            if use_cache:
                self.prediction_cache[cache_key] = result
                await self._manage_cache_size()

            self.total_predictions += 1
            self.prediction_times.append(prediction_time)

            logger.debug(
                f"Predicted recommendation for {content.id}:{user_profile.user_id}: {
                    score:.3f} (confidence: {confidence:.3f})",
            )
            return result

        except Exception as e:
            logger.error(
                f"Error predicting recommendation for {content.id}:{
                    user_profile.user_id
                }: {e}",
            )
            # Use fallback strategy
            return await self._fallback_recommendation(
                content,
                user_profile,
                interactions,
            )

    async def predict_batch_recommendations(
        self,
        contents: list[ContentItem],
        user_profile: UserProfile,
        interactions: list[UserInteraction],
        max_results: int = 100,
    ) -> list[PredictionResult]:
        """Predict recommendation scores for multiple contents efficiently"""
        logger.info(f"Batch predicting recommendations for {len(contents)} contents")

        # Process in parallel
        tasks = []
        for content in contents[:max_results]:  # Limit to avoid memory issues
            task = self.predict_recommendation_score(
                content,
                user_profile,
                interactions,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and sort by score
        valid_results = [r for r in results if isinstance(r, PredictionResult)]
        valid_results.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            f"Batch prediction completed: {len(valid_results)} valid predictions",
        )
        return valid_results

    async def ensemble_predict_recommendation(
        self,
        content: ContentItem,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> EnsemblePrediction:
        """Make ensemble prediction using multiple models"""
        logger.debug(
            f"Making ensemble prediction for {content.id}:{user_profile.user_id}",
        )

        # Get individual predictions
        individual_predictions = []

        # Content quality prediction
        quality_pred = await self.predict_content_quality(content)
        individual_predictions.append(quality_pred)

        # User preference prediction
        preference_pred = await self.predict_user_preference(user_profile, interactions)
        individual_predictions.append(preference_pred)

        # Recommendation prediction
        recommendation_pred = await self.predict_recommendation_score(
            content,
            user_profile,
            interactions,
        )
        individual_predictions.append(recommendation_pred)

        # Calculate ensemble score (weighted average)
        weights = [0.3, 0.2, 0.5]  # Quality, Preference, Recommendation
        ensemble_score = sum(
            pred.score * weight
            for pred, weight in zip(individual_predictions, weights, strict=False)
        )

        # Calculate ensemble confidence
        confidences = [pred.confidence for pred in individual_predictions]
        ensemble_confidence = np.mean(confidences)

        # Calculate variance (uncertainty measure)
        scores = [pred.score for pred in individual_predictions]
        variance = np.var(scores)

        return EnsemblePrediction(
            content_id=content.id,
            user_id=user_profile.user_id,
            individual_predictions=individual_predictions,
            ensemble_score=ensemble_score,
            ensemble_confidence=ensemble_confidence,
            variance=variance,
        )

    def _calculate_quality_confidence(
        self,
        content_features: ContentFeatures,
        feature_vector: np.ndarray,
    ) -> float:
        """Calculate confidence for quality prediction"""
        confidence = 0.5  # Base confidence

        # Increase confidence based on feature completeness
        if content_features.text_features:
            confidence += 0.2
        if content_features.metadata_features:
            confidence += 0.2
        if content_features.quality_features:
            confidence += 0.1

        # Increase confidence based on feature vector quality
        non_zero_features = np.count_nonzero(feature_vector)
        feature_completeness = non_zero_features / len(feature_vector)
        confidence += feature_completeness * 0.2

        return min(1.0, confidence)

    def _calculate_preference_confidence(
        self,
        user_features: UserFeatures,
        interaction_count: int,
    ) -> float:
        """Calculate confidence for preference prediction"""
        confidence = 0.3  # Base confidence

        # Increase confidence based on interaction history
        if interaction_count > 10:
            confidence += 0.3
        elif interaction_count > 5:
            confidence += 0.2
        elif interaction_count > 0:
            confidence += 0.1

        # Increase confidence based on feature completeness
        if user_features.preference_features:
            confidence += 0.2
        if user_features.behavioral_features:
            confidence += 0.2

        return min(1.0, confidence)

    def _calculate_recommendation_confidence(
        self,
        content_features: ContentFeatures,
        user_features: UserFeatures,
        interaction_count: int,
    ) -> float:
        """Calculate confidence for recommendation prediction"""
        confidence = 0.4  # Base confidence

        # Content feature confidence
        content_confidence = self._calculate_quality_confidence(
            content_features,
            np.array([]),
        )

        # User feature confidence
        user_confidence = self._calculate_preference_confidence(
            user_features,
            interaction_count,
        )

        # Combine confidences
        confidence = (content_confidence + user_confidence) / 2

        return min(1.0, confidence)

    async def _fallback_content_quality(self, content: ContentItem) -> PredictionResult:
        """Fallback strategy for content quality prediction"""
        logger.warning(f"Using fallback strategy for content quality: {content.id}")

        # Simple heuristic-based quality score
        score = 0.5  # Base score

        # Adjust based on available metadata
        if content.quality_score:
            score = content.quality_score
        elif content.source_authority_score:
            score = content.source_authority_score
        elif content.view_count and content.view_count > 100:
            score = min(0.8, 0.5 + (content.view_count / 1000) * 0.3)

        return PredictionResult(
            content_id=content.id,
            user_id="system",
            prediction_type="quality",
            score=score,
            confidence=0.3,  # Low confidence for fallback
            model_used="fallback_heuristic",
            features_used=0,
            prediction_time_ms=1.0,
        )

    async def _fallback_user_preference(
        self,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> PredictionResult:
        """Fallback strategy for user preference prediction"""
        logger.warning(
            f"Using fallback strategy for user preference: {user_profile.user_id}",
        )

        # Simple heuristic based on interests
        score = 0.5  # Base score

        if user_profile.interests:
            # More interests = higher engagement
            score = min(0.8, 0.5 + len(user_profile.interests) * 0.1)

        if interactions:
            # Recent interactions indicate engagement
            recent_interactions = [
                i for i in interactions if (datetime.now() - i.timestamp).days < 7
            ]
            if recent_interactions:
                score = min(0.9, score + 0.2)

        return PredictionResult(
            content_id="system",
            user_id=user_profile.user_id,
            prediction_type="preference",
            score=score,
            confidence=0.3,  # Low confidence for fallback
            model_used="fallback_heuristic",
            features_used=0,
            prediction_time_ms=1.0,
        )

    async def _fallback_recommendation(
        self,
        content: ContentItem,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> PredictionResult:
        """Fallback strategy for recommendation prediction"""
        logger.warning(
            f"Using fallback strategy for recommendation: {content.id}:{
                user_profile.user_id
            }",
        )

        # Simple heuristic combining content and user factors
        score = 0.5  # Base score

        # Content factors
        if content.quality_score:
            score += content.quality_score * 0.3
        elif content.source_authority_score:
            score += content.source_authority_score * 0.2

        # User factors
        if user_profile.interests and content.tags:
            # Check for interest overlap
            interest_overlap = len(set(user_profile.interests) & set(content.tags))
            score += interest_overlap * 0.1

        # Interaction history
        if interactions:
            recent_interactions = [
                i for i in interactions if (datetime.now() - i.timestamp).days < 30
            ]
            if recent_interactions:
                score += 0.1

        return PredictionResult(
            content_id=content.id,
            user_id=user_profile.user_id,
            prediction_type="recommendation",
            score=max(0.0, min(1.0, score)),
            confidence=0.3,  # Low confidence for fallback
            model_used="fallback_heuristic",
            features_used=0,
            prediction_time_ms=1.0,
        )

    async def _manage_cache_size(self):
        """Manage prediction cache size"""
        if len(self.prediction_cache) <= self.cache_size:
            return

        # Remove oldest entries
        sorted_items = sorted(
            self.prediction_cache.items(),
            key=lambda x: x[1].created_at,
        )

        items_to_remove = len(self.prediction_cache) - self.cache_size
        for key, _ in sorted_items[:items_to_remove]:
            del self.prediction_cache[key]

        logger.debug(f"Cleaned up {items_to_remove} cache entries")

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics"""
        if not self.prediction_times:
            return {
                "total_predictions": self.total_predictions,
                "cached_predictions": self.cached_predictions,
                "cache_hit_rate": 0.0,
                "avg_prediction_time_ms": 0.0,
                "cache_size": len(self.prediction_cache),
            }

        cache_hit_rate = self.cached_predictions / max(self.total_predictions, 1)
        avg_prediction_time = np.mean(list(self.prediction_times))

        return {
            "total_predictions": self.total_predictions,
            "cached_predictions": self.cached_predictions,
            "cache_hit_rate": cache_hit_rate,
            "avg_prediction_time_ms": avg_prediction_time,
            "cache_size": len(self.prediction_cache),
            "max_prediction_time_ms": max(self.prediction_times),
            "min_prediction_time_ms": min(self.prediction_times),
        }

    async def clear_cache(self):
        """Clear prediction cache"""
        self.prediction_cache.clear()
        logger.info("Prediction cache cleared")

    async def warm_cache(
        self,
        contents: list[ContentItem],
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ):
        """Warm up prediction cache with common predictions"""
        logger.info("Warming up prediction cache")

        # Warm up content quality predictions
        for content in contents[:100]:  # Limit to avoid memory issues
            await self.predict_content_quality(content)

        # Warm up user preference predictions
        for user_profile in user_profiles[:50]:
            user_interactions = [
                i for i in interactions if i.user_id == user_profile.user_id
            ]
            await self.predict_user_preference(user_profile, user_interactions)

        logger.info(f"Cache warmed up with {len(self.prediction_cache)} predictions")
