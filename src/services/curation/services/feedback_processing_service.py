"""FeedbackProcessingService

Advanced feedback processing system that handles both explicit and implicit user feedback,
processes it for machine learning, and provides insights for system improvement.
Supports real-time feedback processing, batch analytics, and automated quality assessment.
"""

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler

from ..models.content_item import ContentItem
from ..models.user_feedback import FeedbackType, LearningSignal, UserFeedback
from ..models.user_interaction import InteractionType, UserInteraction
from ..models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class FeedbackQuality(str, Enum):
    """Quality assessment for feedback"""

    HIGH = "high"  # Reliable, consistent feedback
    MEDIUM = "medium"  # Generally reliable
    LOW = "low"  # Potentially unreliable
    SUSPICIOUS = "suspicious"  # Potentially fraudulent or spam


@dataclass(frozen=True)
class FeedbackPattern:
    """Pattern detected in user feedback"""

    user_id: str
    pattern_type: str  # e.g., "consistent_rater", "harsh_critic", "easy_pleaser"
    confidence: float  # 0.0 to 1.0
    evidence: dict[str, Any]  # Supporting evidence for the pattern
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class FeedbackInsight:
    """Insights derived from feedback analysis"""

    content_id: str
    avg_rating: float
    rating_variance: float
    feedback_count: int
    quality_indicators: dict[str, float]
    user_sentiment: str  # "positive", "negative", "mixed", "neutral"
    confidence: float
    recommendations: list[str]  # Actionable recommendations


@dataclass(frozen=True)
class SystemFeedbackMetrics:
    """System-wide feedback metrics"""

    total_feedback_count: int
    avg_rating: float
    rating_distribution: dict[str, int]
    feedback_velocity: float  # Feedback per day
    quality_score: float  # Overall feedback quality
    user_engagement: float  # User feedback participation rate
    content_coverage: float  # Percentage of content with feedback
    trending_sentiment: str  # Overall trend in sentiment


class FeedbackProcessingService:
    """Advanced feedback processing service with ML-powered analysis.

    Processes both explicit and implicit feedback, detects patterns,
    provides quality assessment, and generates actionable insights.
    """

    def __init__(
        self,
        feedback_quality_threshold: float = 0.5,
        batch_processing_size: int = 100,
        anomaly_detection_enabled: bool = True,
    ):
        """Initialize feedback processing service.

        Args:
            feedback_quality_threshold: Minimum quality score for reliable feedback
            batch_processing_size: Size of batches for bulk processing
            anomaly_detection_enabled: Whether to detect anomalous feedback patterns
        """
        self.feedback_quality_threshold = feedback_quality_threshold
        self.batch_processing_size = batch_processing_size
        self.anomaly_detection_enabled = anomaly_detection_enabled

        # ML models for anomaly detection
        self._anomaly_detector = None
        self._feedback_scaler = StandardScaler()

        # Feedback quality weights
        self.quality_weights = {
            "consistency": 0.3,  # How consistent user is across feedback
            "engagement": 0.2,  # Level of user engagement
            "variance": 0.2,  # Variance in ratings (too consistent = suspicious)
            "timing": 0.15,  # Timing patterns
            "content_awareness": 0.15,  # Appears to understand content
        }

        # Pattern detection thresholds
        self.pattern_thresholds = {
            "consistent_rater": 0.8,  # Low variance in ratings
            "harsh_critic": 0.7,  # Consistently low ratings
            "easy_pleaser": 0.7,  # Consistently high ratings
            "rapid_feedback": 0.6,  # Very fast feedback patterns
            "detailed_reviewer": 0.5,  # Provides detailed feedback
        }

        logger.info("FeedbackProcessingService initialized")

    async def process_feedback(
        self,
        feedback: UserFeedback,
        content_item: ContentItem,
        user_profile: UserProfile | None = None,
    ) -> LearningSignal:
        """Process individual feedback and generate learning signal.

        Args:
            feedback: User feedback to process
            content_item: Content item that received feedback
            user_profile: Optional user profile for context

        Returns:
            Learning signal derived from feedback
        """
        try:
            # Assess feedback quality
            quality_score = await self._assess_feedback_quality(
                feedback,
                content_item,
                user_profile,
            )

            # Convert feedback to learning signal
            learning_signal = await self._convert_to_learning_signal(
                feedback,
                content_item,
                quality_score,
            )

            # Detect any suspicious patterns
            if self.anomaly_detection_enabled and user_profile:
                is_anomalous = await self._detect_anomalous_feedback(
                    feedback,
                    user_profile,
                )
                if is_anomalous:
                    learning_signal.confidence *= (
                        0.5  # Reduce confidence for suspicious feedback
                    )

            logger.debug(
                f"Processed feedback {feedback.id} with quality {quality_score:.2f}",
            )
            return learning_signal

        except Exception as e:
            logger.error(f"Error processing feedback {feedback.id}: {str(e)}")
            # Return neutral learning signal
            return LearningSignal(
                user_id=feedback.user_id,
                content_id=feedback.content_id,
                signal_strength=0.0,
                signal_type="neutral",
                confidence=0.0,
                metadata={"error": str(e)},
            )

    async def process_implicit_feedback(
        self,
        interaction: UserInteraction,
        content_item: ContentItem,
        context: dict[str, Any] = None,
    ) -> LearningSignal:
        """Process implicit feedback from user interactions.

        Args:
            interaction: User interaction to analyze
            content_item: Content that was interacted with
            context: Additional context (e.g., session data, previous interactions)

        Returns:
            Learning signal derived from implicit feedback
        """
        try:
            # Convert interaction to implicit feedback signal
            signal_strength = await self._calculate_implicit_signal_strength(
                interaction,
                content_item,
                context or {},
            )

            # Determine signal type based on interaction
            signal_type = await self._determine_implicit_signal_type(
                interaction,
                content_item,
                context or {},
            )

            # Calculate confidence based on interaction patterns
            confidence = await self._calculate_implicit_confidence(
                interaction,
                context or {},
            )

            learning_signal = LearningSignal(
                user_id=interaction.user_id,
                content_id=interaction.content_id,
                signal_strength=signal_strength,
                signal_type=signal_type,
                confidence=confidence,
                source="implicit",
                metadata={
                    "interaction_type": interaction.interaction_type.value,
                    "duration": context.get("duration_seconds", 0) if context else 0,
                    "session_context": (
                        context.get("session_context", {}) if context else {}
                    ),
                },
            )

            logger.debug(
                f"Generated implicit learning signal from {interaction.interaction_type.value}",
            )
            return learning_signal

        except Exception as e:
            logger.error(f"Error processing implicit feedback: {str(e)}")
            return LearningSignal(
                user_id=interaction.user_id,
                content_id=interaction.content_id,
                signal_strength=0.0,
                signal_type="neutral",
                confidence=0.0,
                source="implicit",
                metadata={"error": str(e)},
            )

    async def batch_process_feedback(
        self,
        feedback_batch: list[tuple[UserFeedback, ContentItem]],
        user_profiles: dict[str, UserProfile] | None = None,
    ) -> list[LearningSignal]:
        """Process multiple feedback items in batch for efficiency.

        Args:
            feedback_batch: List of (feedback, content_item) tuples
            user_profiles: Optional mapping of user_id to UserProfile

        Returns:
            List of learning signals
        """
        try:
            # Process in smaller batches to avoid memory issues
            all_signals = []

            for i in range(0, len(feedback_batch), self.batch_processing_size):
                batch = feedback_batch[i : i + self.batch_processing_size]

                # Process batch concurrently
                tasks = []
                for feedback, content_item in batch:
                    user_profile = (
                        user_profiles.get(str(feedback.user_id))
                        if user_profiles
                        else None
                    )
                    tasks.append(
                        self.process_feedback(feedback, content_item, user_profile),
                    )

                batch_signals = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle any exceptions
                for signal in batch_signals:
                    if isinstance(signal, Exception):
                        logger.error(f"Error in batch processing: {str(signal)}")
                    else:
                        all_signals.append(signal)

            logger.info(f"Batch processed {len(feedback_batch)} feedback items")
            return all_signals

        except Exception as e:
            logger.error(f"Error in batch feedback processing: {str(e)}")
            return []

    async def analyze_user_feedback_patterns(
        self,
        user_id: str,
        user_feedback_history: list[UserFeedback],
        lookback_days: int = 30,
    ) -> list[FeedbackPattern]:
        """Analyze user's feedback patterns to detect behavioral signatures.

        Args:
            user_id: User to analyze
            user_feedback_history: User's feedback history
            lookback_days: Number of days to analyze

        Returns:
            List of detected feedback patterns
        """
        try:
            # Filter recent feedback
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            recent_feedback = [
                fb for fb in user_feedback_history if fb.timestamp >= cutoff_date
            ]

            if len(recent_feedback) < 3:
                return []  # Need minimum feedback for pattern detection

            patterns = []

            # Detect consistency pattern
            consistency_pattern = await self._detect_consistency_pattern(
                user_id,
                recent_feedback,
            )
            if consistency_pattern:
                patterns.append(consistency_pattern)

            # Detect rating bias patterns
            bias_patterns = await self._detect_rating_bias_patterns(
                user_id,
                recent_feedback,
            )
            patterns.extend(bias_patterns)

            # Detect timing patterns
            timing_pattern = await self._detect_timing_patterns(
                user_id,
                recent_feedback,
            )
            if timing_pattern:
                patterns.append(timing_pattern)

            # Detect engagement patterns
            engagement_pattern = await self._detect_engagement_patterns(
                user_id,
                recent_feedback,
            )
            if engagement_pattern:
                patterns.append(engagement_pattern)

            logger.debug(
                f"Detected {len(patterns)} feedback patterns for user {user_id}",
            )
            return patterns

        except Exception as e:
            logger.error(
                f"Error analyzing feedback patterns for user {user_id}: {str(e)}",
            )
            return []

    async def generate_content_feedback_insights(
        self,
        content_id: str,
        content_feedback: list[UserFeedback],
        content_item: ContentItem,
    ) -> FeedbackInsight:
        """Generate insights about content based on feedback received.

        Args:
            content_id: Content to analyze
            content_feedback: All feedback for this content
            content_item: The content item itself

        Returns:
            Comprehensive feedback insights
        """
        try:
            if not content_feedback:
                return self._create_empty_insight(content_id)

            # Calculate basic statistics
            ratings = [
                fb.feedback_value
                for fb in content_feedback
                if fb.feedback_type == FeedbackType.RATING
            ]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            rating_variance = np.var(ratings) if len(ratings) > 1 else 0.0

            # Analyze quality indicators
            quality_indicators = await self._analyze_content_quality_indicators(
                content_feedback,
                content_item,
            )

            # Determine user sentiment
            user_sentiment = await self._determine_content_sentiment(content_feedback)

            # Calculate confidence based on sample size and consistency
            confidence = await self._calculate_insight_confidence(
                content_feedback,
                rating_variance,
            )

            # Generate actionable recommendations
            recommendations = await self._generate_content_recommendations(
                content_feedback,
                content_item,
                quality_indicators,
            )

            insight = FeedbackInsight(
                content_id=content_id,
                avg_rating=avg_rating,
                rating_variance=rating_variance,
                feedback_count=len(content_feedback),
                quality_indicators=quality_indicators,
                user_sentiment=user_sentiment,
                confidence=confidence,
                recommendations=recommendations,
            )

            logger.debug(f"Generated insights for content {content_id}")
            return insight

        except Exception as e:
            logger.error(
                f"Error generating insights for content {content_id}: {str(e)}",
            )
            return self._create_empty_insight(content_id)

    async def generate_system_feedback_metrics(
        self,
        all_feedback: list[UserFeedback],
        all_content: list[ContentItem],
        active_users: int,
    ) -> SystemFeedbackMetrics:
        """Generate system-wide feedback metrics and health indicators.

        Args:
            all_feedback: All feedback in the system
            all_content: All content items
            active_users: Number of active users

        Returns:
            System-wide feedback metrics
        """
        try:
            if not all_feedback:
                return self._create_empty_system_metrics()

            # Basic metrics
            total_feedback = len(all_feedback)
            ratings = [
                fb.feedback_value
                for fb in all_feedback
                if fb.feedback_type == FeedbackType.RATING
            ]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

            # Rating distribution
            rating_distribution = Counter()
            for rating in ratings:
                rating_bucket = f"{int(rating)}-{int(rating) + 1}"
                rating_distribution[rating_bucket] += 1

            # Calculate feedback velocity (feedback per day)
            if all_feedback:
                date_range = (
                    max(fb.timestamp for fb in all_feedback)
                    - min(fb.timestamp for fb in all_feedback)
                ).days
                feedback_velocity = total_feedback / max(1, date_range)
            else:
                feedback_velocity = 0.0

            # Quality score (average of feedback quality assessments)
            quality_scores = []
            for feedback in all_feedback[-100:]:  # Sample recent feedback
                # Simplified quality assessment for system metrics
                quality_score = 0.8 if not feedback.is_implicit else 0.6
                quality_scores.append(quality_score)

            avg_quality = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
            )

            # User engagement (percentage of users providing feedback)
            unique_feedback_users = len(set(str(fb.user_id) for fb in all_feedback))
            user_engagement = unique_feedback_users / max(1, active_users)

            # Content coverage (percentage of content with feedback)
            content_with_feedback = len(set(str(fb.content_id) for fb in all_feedback))
            content_coverage = content_with_feedback / max(1, len(all_content))

            # Trending sentiment analysis
            recent_feedback = [
                fb
                for fb in all_feedback
                if fb.timestamp >= datetime.now() - timedelta(days=7)
            ]
            trending_sentiment = await self._analyze_trending_sentiment(recent_feedback)

            metrics = SystemFeedbackMetrics(
                total_feedback_count=total_feedback,
                avg_rating=avg_rating,
                rating_distribution=dict(rating_distribution),
                feedback_velocity=feedback_velocity,
                quality_score=avg_quality,
                user_engagement=user_engagement,
                content_coverage=content_coverage,
                trending_sentiment=trending_sentiment,
            )

            logger.info(
                f"Generated system feedback metrics: {total_feedback} feedback items",
            )
            return metrics

        except Exception as e:
            logger.error(f"Error generating system feedback metrics: {str(e)}")
            return self._create_empty_system_metrics()

    async def detect_feedback_anomalies(
        self,
        recent_feedback: list[UserFeedback],
        historical_baseline: SystemFeedbackMetrics | None = None,
    ) -> list[str]:
        """Detect anomalies in feedback patterns that might indicate issues.

        Args:
            recent_feedback: Recent feedback to analyze
            historical_baseline: Historical metrics for comparison

        Returns:
            List of anomaly descriptions
        """
        try:
            anomalies = []

            if not recent_feedback:
                return anomalies

            # Detect sudden rating drops
            recent_ratings = [
                fb.feedback_value
                for fb in recent_feedback
                if fb.feedback_type == FeedbackType.RATING
            ]

            if recent_ratings and historical_baseline:
                recent_avg = sum(recent_ratings) / len(recent_ratings)
                if recent_avg < historical_baseline.avg_rating - 0.5:
                    anomalies.append(
                        f"Significant rating drop detected: {recent_avg:.2f} vs {
                            historical_baseline.avg_rating:.2f}",
                    )

            # Detect unusual feedback patterns
            user_feedback_counts = Counter(str(fb.user_id) for fb in recent_feedback)
            max_feedback_per_user = (
                max(user_feedback_counts.values()) if user_feedback_counts else 0
            )

            if max_feedback_per_user > 20:  # User providing excessive feedback
                anomalies.append(
                    f"User providing excessive feedback: {max_feedback_per_user} items",
                )

            # Detect rating inflation/deflation
            extreme_ratings = sum(
                1 for rating in recent_ratings if rating <= 1 or rating >= 5
            )
            if recent_ratings and extreme_ratings / len(recent_ratings) > 0.8:
                anomalies.append("High proportion of extreme ratings detected")

            # Detect temporal anomalies
            if len(recent_feedback) > 10:
                timestamps = [fb.timestamp for fb in recent_feedback]
                time_gaps = [
                    (timestamps[i + 1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps) - 1)
                ]
                avg_gap = sum(time_gaps) / len(time_gaps)

                # Check for suspiciously regular patterns
                if len(set(int(gap) for gap in time_gaps)) == 1:
                    anomalies.append("Suspiciously regular feedback timing pattern")

            logger.debug(f"Detected {len(anomalies)} feedback anomalies")
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting feedback anomalies: {str(e)}")
            return []

    # Helper methods

    async def _assess_feedback_quality(
        self,
        feedback: UserFeedback,
        content_item: ContentItem,
        user_profile: UserProfile | None,
    ) -> float:
        """Assess the quality/reliability of feedback"""
        quality_score = 0.5  # Base score

        # Explicit feedback generally higher quality than implicit
        if not feedback.is_implicit:
            quality_score += 0.2

        # Feedback with text comments generally higher quality
        if feedback.metadata and feedback.metadata.get("comment"):
            quality_score += 0.15

        # User profile context
        if user_profile:
            # Users with more interactions generally provide better feedback
            interaction_factor = min(0.15, user_profile.total_interactions / 100)
            quality_score += interaction_factor

        # Timing context (too fast = suspicious)
        if feedback.metadata and "response_time_seconds" in feedback.metadata:
            response_time = feedback.metadata["response_time_seconds"]
            if response_time < 5:  # Too fast to properly evaluate
                quality_score -= 0.2
            elif response_time > 300:  # Very considered response
                quality_score += 0.1

        # Content context
        if (
            content_item.content_type.value in ["paper", "article"]
            and feedback.feedback_value != 3
        ):
            # Non-neutral feedback on substantial content suggests engagement
            quality_score += 0.1

        return max(0.0, min(1.0, quality_score))

    async def _convert_to_learning_signal(
        self,
        feedback: UserFeedback,
        content_item: ContentItem,
        quality_score: float,
    ) -> LearningSignal:
        """Convert feedback to learning signal"""
        # Convert feedback value to signal strength
        if feedback.feedback_type == FeedbackType.RATING:
            # Convert 1-5 rating to -1 to 1 signal
            signal_strength = (feedback.feedback_value - 3.0) / 2.0
        elif feedback.feedback_type == FeedbackType.THUMBS:
            signal_strength = 1.0 if feedback.feedback_value > 0 else -1.0
        elif feedback.feedback_type == FeedbackType.RELEVANCE:
            signal_strength = (feedback.feedback_value - 0.5) * 2.0
        else:
            signal_strength = 0.0

        # Determine signal type
        if signal_strength > 0.3:
            signal_type = "positive"
        elif signal_strength < -0.3:
            signal_type = "negative"
        else:
            signal_type = "neutral"

        # Confidence based on quality and feedback strength
        confidence = quality_score * (0.5 + 0.5 * abs(signal_strength))

        return LearningSignal(
            user_id=feedback.user_id,
            content_id=feedback.content_id,
            signal_strength=signal_strength,
            signal_type=signal_type,
            confidence=confidence,
            source="explicit",
            metadata={
                "feedback_type": feedback.feedback_type.value,
                "quality_score": quality_score,
                "original_value": feedback.feedback_value,
            },
        )

    async def _calculate_implicit_signal_strength(
        self,
        interaction: UserInteraction,
        content_item: ContentItem,
        context: dict[str, Any],
    ) -> float:
        """Calculate signal strength from implicit interaction"""
        base_strength = {
            InteractionType.VIEW: 0.1,
            InteractionType.CLICK: 0.2,
            InteractionType.LIKE: 0.6,
            InteractionType.SAVE: 0.8,
            InteractionType.SHARE: 0.9,
            InteractionType.COMMENT: 0.7,
            InteractionType.DOWNLOAD: 0.9,
        }.get(interaction.interaction_type, 0.1)

        # Adjust based on context
        duration = context.get("duration_seconds", 0)
        if duration > 0:
            # Longer engagement = stronger signal
            if duration > 300:  # 5 minutes
                base_strength *= 1.5
            elif duration > 60:  # 1 minute
                base_strength *= 1.2
            elif duration < 10:  # Very short
                base_strength *= 0.5

        # Content type context
        if content_item.content_type.value in ["paper", "article"] and duration > 120:
            base_strength *= 1.3  # Reading substantial content

        return min(1.0, base_strength)

    async def _determine_implicit_signal_type(
        self,
        interaction: UserInteraction,
        content_item: ContentItem,
        context: dict[str, Any],
    ) -> str:
        """Determine signal type from implicit interaction"""
        positive_interactions = {
            InteractionType.LIKE,
            InteractionType.SAVE,
            InteractionType.SHARE,
            InteractionType.DOWNLOAD,
        }

        if interaction.interaction_type in positive_interactions:
            return "positive"
        if interaction.interaction_type == InteractionType.VIEW:
            # Views are neutral unless there's context suggesting otherwise
            duration = context.get("duration_seconds", 0)
            if duration > 180:  # Long view suggests interest
                return "positive"
            if duration < 5:  # Very short view suggests disinterest
                return "negative"
            return "neutral"
        return "neutral"

    async def _calculate_implicit_confidence(
        self,
        interaction: UserInteraction,
        context: dict[str, Any],
    ) -> float:
        """Calculate confidence for implicit feedback signal"""
        base_confidence = {
            InteractionType.VIEW: 0.2,
            InteractionType.CLICK: 0.3,
            InteractionType.LIKE: 0.8,
            InteractionType.SAVE: 0.9,
            InteractionType.SHARE: 0.95,
            InteractionType.COMMENT: 0.85,
            InteractionType.DOWNLOAD: 0.9,
        }.get(interaction.interaction_type, 0.2)

        # Adjust based on context
        if context.get("duration_seconds", 0) > 120:
            base_confidence *= 1.2

        # Session context can increase confidence
        session_interactions = context.get("session_context", {}).get(
            "interaction_count",
            1,
        )
        if session_interactions > 3:
            base_confidence *= 1.1

        return min(1.0, base_confidence)

    async def _detect_anomalous_feedback(
        self,
        feedback: UserFeedback,
        user_profile: UserProfile,
    ) -> bool:
        """Detect if feedback appears anomalous/suspicious"""
        # Simple heuristics for anomaly detection

        # Too fast response time
        if feedback.metadata and feedback.metadata.get("response_time_seconds", 10) < 2:
            return True

        # Extreme ratings without engagement history
        if (
            feedback.feedback_type == FeedbackType.RATING
            and (feedback.feedback_value <= 1 or feedback.feedback_value >= 5)
            and user_profile.total_interactions < 5
        ):
            return True

        # More sophisticated ML-based detection would go here
        return False

    async def _detect_consistency_pattern(
        self,
        user_id: str,
        feedback_history: list[UserFeedback],
    ) -> FeedbackPattern | None:
        """Detect if user has consistent rating patterns"""
        ratings = [
            fb.feedback_value
            for fb in feedback_history
            if fb.feedback_type == FeedbackType.RATING
        ]

        if len(ratings) < 3:
            return None

        variance = np.var(ratings)
        mean_rating = np.mean(ratings)

        # Low variance indicates consistent rating
        if variance < 0.25:  # Very consistent
            confidence = 1.0 - variance
            return FeedbackPattern(
                user_id=user_id,
                pattern_type="consistent_rater",
                confidence=confidence,
                evidence={
                    "rating_variance": variance,
                    "mean_rating": mean_rating,
                    "sample_size": len(ratings),
                },
            )

        return None

    async def _detect_rating_bias_patterns(
        self,
        user_id: str,
        feedback_history: list[UserFeedback],
    ) -> list[FeedbackPattern]:
        """Detect rating bias patterns (harsh critic, easy pleaser)"""
        patterns = []
        ratings = [
            fb.feedback_value
            for fb in feedback_history
            if fb.feedback_type == FeedbackType.RATING
        ]

        if len(ratings) < 5:
            return patterns

        mean_rating = np.mean(ratings)

        # Harsh critic pattern
        if mean_rating < 2.5:
            harsh_confidence = (2.5 - mean_rating) / 1.5
            patterns.append(
                FeedbackPattern(
                    user_id=user_id,
                    pattern_type="harsh_critic",
                    confidence=harsh_confidence,
                    evidence={
                        "mean_rating": mean_rating,
                        "low_ratings_percentage": sum(1 for r in ratings if r <= 2)
                        / len(ratings),
                    },
                ),
            )

        # Easy pleaser pattern
        elif mean_rating > 4.0:
            pleaser_confidence = (mean_rating - 4.0) / 1.0
            patterns.append(
                FeedbackPattern(
                    user_id=user_id,
                    pattern_type="easy_pleaser",
                    confidence=pleaser_confidence,
                    evidence={
                        "mean_rating": mean_rating,
                        "high_ratings_percentage": sum(1 for r in ratings if r >= 4)
                        / len(ratings),
                    },
                ),
            )

        return patterns

    async def _detect_timing_patterns(
        self,
        user_id: str,
        feedback_history: list[UserFeedback],
    ) -> FeedbackPattern | None:
        """Detect unusual timing patterns in feedback"""
        if len(feedback_history) < 5:
            return None

        # Calculate time intervals between feedback
        sorted_feedback = sorted(feedback_history, key=lambda x: x.timestamp)
        intervals = []
        for i in range(1, len(sorted_feedback)):
            interval = (
                sorted_feedback[i].timestamp - sorted_feedback[i - 1].timestamp
            ).total_seconds()
            intervals.append(interval)

        # Detect rapid feedback pattern
        rapid_count = sum(
            1 for interval in intervals if interval < 30
        )  # Less than 30 seconds
        if rapid_count / len(intervals) > 0.6:
            return FeedbackPattern(
                user_id=user_id,
                pattern_type="rapid_feedback",
                confidence=rapid_count / len(intervals),
                evidence={
                    "rapid_feedback_percentage": rapid_count / len(intervals),
                    "avg_interval_seconds": np.mean(intervals),
                    "min_interval_seconds": min(intervals),
                },
            )

        return None

    async def _detect_engagement_patterns(
        self,
        user_id: str,
        feedback_history: list[UserFeedback],
    ) -> FeedbackPattern | None:
        """Detect user engagement patterns"""
        detailed_feedback = [
            fb for fb in feedback_history if fb.metadata and fb.metadata.get("comment")
        ]

        if len(detailed_feedback) / len(feedback_history) > 0.7:
            return FeedbackPattern(
                user_id=user_id,
                pattern_type="detailed_reviewer",
                confidence=len(detailed_feedback) / len(feedback_history),
                evidence={
                    "detailed_feedback_percentage": len(detailed_feedback)
                    / len(feedback_history),
                    "avg_comment_length": np.mean(
                        [
                            len(fb.metadata.get("comment", ""))
                            for fb in detailed_feedback
                        ],
                    ),
                },
            )

        return None

    async def _analyze_content_quality_indicators(
        self,
        feedback_list: list[UserFeedback],
        content_item: ContentItem,
    ) -> dict[str, float]:
        """Analyze quality indicators from feedback"""
        indicators = {}

        # Rating-based indicators
        ratings = [
            fb.feedback_value
            for fb in feedback_list
            if fb.feedback_type == FeedbackType.RATING
        ]

        if ratings:
            indicators["avg_rating"] = np.mean(ratings)
            indicators["rating_consistency"] = (
                1.0 - np.std(ratings) / 5.0
            )  # Normalized std dev
            indicators["positive_sentiment"] = sum(1 for r in ratings if r >= 4) / len(
                ratings,
            )

        # Engagement indicators
        engagement_feedback = [fb for fb in feedback_list if not fb.is_implicit]
        indicators["engagement_rate"] = len(engagement_feedback) / max(
            1,
            len(feedback_list),
        )

        # Quality feedback indicators
        detailed_feedback = [
            fb for fb in feedback_list if fb.metadata and fb.metadata.get("comment")
        ]
        indicators["detailed_feedback_rate"] = len(detailed_feedback) / max(
            1,
            len(feedback_list),
        )

        return indicators

    async def _determine_content_sentiment(
        self,
        feedback_list: list[UserFeedback],
    ) -> str:
        """Determine overall sentiment from feedback"""
        if not feedback_list:
            return "neutral"

        ratings = [
            fb.feedback_value
            for fb in feedback_list
            if fb.feedback_type == FeedbackType.RATING
        ]

        if not ratings:
            return "neutral"

        avg_rating = np.mean(ratings)
        rating_spread = max(ratings) - min(ratings)

        if avg_rating >= 4.0:
            return "positive"
        if avg_rating <= 2.0:
            return "negative"
        if rating_spread > 3.0:
            return "mixed"
        return "neutral"

    async def _calculate_insight_confidence(
        self,
        feedback_list: list[UserFeedback],
        rating_variance: float,
    ) -> float:
        """Calculate confidence in content insights"""
        sample_size_factor = min(
            1.0,
            len(feedback_list) / 10,
        )  # More feedback = higher confidence
        # Lower variance = higher confidence
        consistency_factor = max(0.2, 1.0 - rating_variance / 2.0)

        confidence = (sample_size_factor + consistency_factor) / 2.0
        return confidence

    async def _generate_content_recommendations(
        self,
        feedback_list: list[UserFeedback],
        content_item: ContentItem,
        quality_indicators: dict[str, float],
    ) -> list[str]:
        """Generate actionable recommendations for content"""
        recommendations = []

        avg_rating = quality_indicators.get("avg_rating", 3.0)
        engagement_rate = quality_indicators.get("engagement_rate", 0.5)

        if avg_rating < 3.0:
            recommendations.append("Consider reviewing content quality and relevance")

        if engagement_rate < 0.3:
            recommendations.append(
                "Low engagement - consider improving content presentation",
            )

        if quality_indicators.get("detailed_feedback_rate", 0) < 0.2:
            recommendations.append("Encourage more detailed user feedback")

        if len(feedback_list) < 5:
            recommendations.append("Gather more user feedback for better insights")

        return recommendations

    async def _analyze_trending_sentiment(
        self,
        recent_feedback: list[UserFeedback],
    ) -> str:
        """Analyze trending sentiment from recent feedback"""
        if not recent_feedback:
            return "neutral"

        ratings = [
            fb.feedback_value
            for fb in recent_feedback
            if fb.feedback_type == FeedbackType.RATING
        ]

        if not ratings:
            return "neutral"

        avg_recent = np.mean(ratings)

        if avg_recent >= 3.8:
            return "positive"
        if avg_recent <= 2.2:
            return "negative"
        return "neutral"

    def _create_empty_insight(self, content_id: str) -> FeedbackInsight:
        """Create empty insight for content with no feedback"""
        return FeedbackInsight(
            content_id=content_id,
            avg_rating=0.0,
            rating_variance=0.0,
            feedback_count=0,
            quality_indicators={},
            user_sentiment="neutral",
            confidence=0.0,
            recommendations=["Gather initial user feedback"],
        )

    def _create_empty_system_metrics(self) -> SystemFeedbackMetrics:
        """Create empty system metrics"""
        return SystemFeedbackMetrics(
            total_feedback_count=0,
            avg_rating=0.0,
            rating_distribution={},
            feedback_velocity=0.0,
            quality_score=0.0,
            user_engagement=0.0,
            content_coverage=0.0,
            trending_sentiment="neutral",
        )
