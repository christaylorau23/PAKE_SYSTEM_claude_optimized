"""Feature Extractor
Advanced feature extraction pipeline for content analysis and recommendation systems.
Supports text, metadata, and behavioral feature extraction with caching and optimization.
"""

import asyncio
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import nltk
import numpy as np
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

from ..models.content_item import ContentItem
from ..models.user_interaction import UserInteraction
from ..models.user_profile import UserProfile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContentFeatures:
    """Extracted features from content"""

    content_id: str
    text_features: dict[str, float] = field(default_factory=dict)
    metadata_features: dict[str, float] = field(default_factory=dict)
    semantic_features: dict[str, float] = field(default_factory=dict)
    quality_features: dict[str, float] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class UserFeatures:
    """Extracted features from user behavior"""

    user_id: str
    preference_features: dict[str, float] = field(default_factory=dict)
    behavioral_features: dict[str, float] = field(default_factory=dict)
    temporal_features: dict[str, float] = field(default_factory=dict)
    social_features: dict[str, float] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.now)


class FeatureExtractor:
    """Advanced feature extraction pipeline for content and user analysis"""

    def __init__(self, cache_size: int = 10000):
        self.cache_size = cache_size
        self.feature_cache: dict[str, Any] = {}
        self.text_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.95,
        )
        self.lda_model = LatentDirichletAllocation(
            n_components=20,
            random_state=42,
            max_iter=100,
        )
        self.scaler = StandardScaler()
        self.lemmatizer = WordNetLemmatizer()

        # Initialize NLTK components
        try:
            nltk.data.find("tokenizers/punkt")
            nltk.data.find("corpora/stopwords")
            nltk.data.find("corpora/wordnet")
        except LookupError:
            logger.warning("NLTK data not found, downloading required components")
            nltk.download("punkt", quiet=True)
            nltk.download("stopwords", quiet=True)
            nltk.download("wordnet", quiet=True)

    def _get_cache_key(self, content_id: str, feature_type: str) -> str:
        """Generate cache key for features"""
        return f"{feature_type}:{content_id}"

    def _is_cache_valid(self, cache_key: str, max_age_hours: int = 24) -> bool:
        """Check if cached features are still valid"""
        if cache_key not in self.feature_cache:
            return False

        cached_data = self.feature_cache[cache_key]
        age = datetime.now() - cached_data.get("extracted_at", datetime.min)
        return age.total_seconds() < max_age_hours * 3600

    async def extract_content_features(self, content: ContentItem) -> ContentFeatures:
        """Extract comprehensive features from content"""
        cache_key = self._get_cache_key(content.id, "content")

        if self._is_cache_valid(cache_key):
            logger.debug(f"Using cached features for content {content.id}")
            return self.feature_cache[cache_key]["features"]

        try:
            # Text features
            text_features = await self._extract_text_features(content)

            # Metadata features
            metadata_features = await self._extract_metadata_features(content)

            # Semantic features
            semantic_features = await self._extract_semantic_features(content)

            # Quality features
            quality_features = await self._extract_quality_features(content)

            features = ContentFeatures(
                content_id=content.id,
                text_features=text_features,
                metadata_features=metadata_features,
                semantic_features=semantic_features,
                quality_features=quality_features,
            )

            # Cache the features
            self.feature_cache[cache_key] = {
                "features": features,
                "extracted_at": datetime.now(),
            }

            # Manage cache size
            if len(self.feature_cache) > self.cache_size:
                await self._cleanup_cache()

            logger.info(f"Extracted features for content {content.id}")
            return features

        except Exception as e:
            logger.error(f"Error extracting features for content {content.id}: {e}")
            raise

    async def extract_user_features(
        self,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> UserFeatures:
        """Extract comprehensive features from user behavior"""
        cache_key = self._get_cache_key(user_profile.user_id, "user")

        if self._is_cache_valid(cache_key):
            logger.debug(f"Using cached features for user {user_profile.user_id}")
            return self.feature_cache[cache_key]["features"]

        try:
            # Preference features
            preference_features = await self._extract_preference_features(user_profile)

            # Behavioral features
            behavioral_features = await self._extract_behavioral_features(interactions)

            # Temporal features
            temporal_features = await self._extract_temporal_features(interactions)

            # Social features
            social_features = await self._extract_social_features(
                user_profile,
                interactions,
            )

            features = UserFeatures(
                user_id=user_profile.user_id,
                preference_features=preference_features,
                behavioral_features=behavioral_features,
                temporal_features=temporal_features,
                social_features=social_features,
            )

            # Cache the features
            self.feature_cache[cache_key] = {
                "features": features,
                "extracted_at": datetime.now(),
            }

            logger.info(f"Extracted features for user {user_profile.user_id}")
            return features

        except Exception as e:
            logger.error(
                f"Error extracting features for user {user_profile.user_id}: {e}",
            )
            raise

    async def _extract_text_features(self, content: ContentItem) -> dict[str, float]:
        """Extract text-based features"""
        features = {}

        if not content.content_text:
            return features

        text = content.content_text

        # Basic text statistics
        features["text_length"] = len(text)
        features["word_count"] = len(text.split())
        features["sentence_count"] = len(re.findall(r"[.!?]+", text))
        features["avg_word_length"] = (
            np.mean([len(word) for word in text.split()]) if text.split() else 0
        )
        features["avg_sentence_length"] = (
            features["word_count"] / features["sentence_count"]
            if features["sentence_count"] > 0
            else 0
        )

        # Readability features
        features["flesch_reading_ease"] = self._calculate_flesch_score(text)
        features["flesch_kincaid_grade"] = self._calculate_fk_grade(text)

        # Vocabulary features
        words = word_tokenize(text.lower())
        unique_words = set(words)
        features["vocabulary_richness"] = len(unique_words) / len(words) if words else 0
        features["unique_word_ratio"] = (
            len(unique_words) / features["word_count"]
            if features["word_count"] > 0
            else 0
        )

        # Sentiment indicators
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
        ]
        negative_words = [
            "bad",
            "terrible",
            "awful",
            "horrible",
            "disappointing",
            "poor",
        ]

        features["positive_sentiment_ratio"] = (
            sum(1 for word in words if word in positive_words) / len(words)
            if words
            else 0
        )
        features["negative_sentiment_ratio"] = (
            sum(1 for word in words if word in negative_words) / len(words)
            if words
            else 0
        )

        # Topic indicators
        features["has_numbers"] = 1.0 if re.search(r"\d+", text) else 0.0
        features["has_urls"] = 1.0 if re.search(r"http[s]?://", text) else 0.0
        features["has_emails"] = (
            1.0
            if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
            else 0.0
        )

        return features

    async def _extract_metadata_features(
        self,
        content: ContentItem,
    ) -> dict[str, float]:
        """Extract metadata-based features"""
        features = {}

        # Source features
        features["source_authority_score"] = content.source_authority_score or 0.0
        features["source_reliability"] = content.source_reliability or 0.0

        # Temporal features
        if content.published_date:
            now = datetime.now()
            age_days = (now - content.published_date).days
            features["content_age_days"] = age_days
            features["is_recent"] = 1.0 if age_days < 7 else 0.0
            features["is_fresh"] = 1.0 if age_days < 30 else 0.0

        # Engagement features
        features["view_count"] = content.view_count or 0
        features["share_count"] = content.share_count or 0
        features["like_count"] = content.like_count or 0
        features["comment_count"] = content.comment_count or 0

        # Quality indicators
        features["has_abstract"] = 1.0 if content.abstract else 0.0
        features["has_tags"] = 1.0 if content.tags else 0.0
        features["tag_count"] = len(content.tags) if content.tags else 0

        # Content type features
        content_types = ["article", "blog", "paper", "news", "tutorial", "review"]
        for content_type in content_types:
            features[f"is_{content_type}"] = (
                1.0 if content.content_type == content_type else 0.0
            )

        return features

    async def _extract_semantic_features(
        self,
        content: ContentItem,
    ) -> dict[str, float]:
        """Extract semantic features using topic modeling"""
        features = {}

        if not content.content_text:
            return features

        # Topic modeling features
        text = content.content_text
        words = word_tokenize(text.lower())

        # Remove stopwords and lemmatize
        stop_words = set(stopwords.words("english"))
        filtered_words = [
            self.lemmatizer.lemmatize(word)
            for word in words
            if word not in stop_words and word.isalpha()
        ]

        if len(filtered_words) < 10:  # Need minimum words for topic modeling
            return features

        # TF-IDF features
        try:
            tfidf_matrix = self.text_vectorizer.fit_transform(
                [" ".join(filtered_words)],
            )
            tfidf_features = tfidf_matrix.toarray()[0]

            # Top TF-IDF scores
            top_indices = np.argsort(tfidf_features)[-10:]  # Top 10 features
            for i, idx in enumerate(top_indices):
                features[f"tfidf_top_{i}"] = tfidf_features[idx]

        except Exception as e:
            logger.warning(f"Error in TF-IDF extraction: {e}")

        # Topic distribution (if LDA model is trained)
        try:
            if hasattr(self.lda_model, "components_"):
                topic_probs = self.lda_model.transform(tfidf_matrix)
                for i, prob in enumerate(topic_probs[0]):
                    features[f"topic_{i}_probability"] = prob
        except Exception as e:
            logger.warning(f"Error in topic modeling: {e}")

        return features

    async def _extract_quality_features(self, content: ContentItem) -> dict[str, float]:
        """Extract content quality indicators"""
        features = {}

        # Completeness features
        features["has_title"] = 1.0 if content.title else 0.0
        features["has_content"] = 1.0 if content.content_text else 0.0
        features["has_author"] = 1.0 if content.author else 0.0
        features["has_source"] = 1.0 if content.source_url else 0.0

        # Quality scores
        features["quality_score"] = content.quality_score or 0.0
        features["credibility_score"] = content.credibility_score or 0.0

        # Content structure
        if content.content_text:
            text = content.content_text
            features["has_paragraphs"] = 1.0 if "\n\n" in text else 0.0
            features["has_lists"] = (
                1.0 if re.search(r"^\s*[-*+]\s", text, re.MULTILINE) else 0.0
            )
            features["has_headings"] = (
                1.0 if re.search(r"^#{1,6}\s", text, re.MULTILINE) else 0.0
            )

        return features

    async def _extract_preference_features(
        self,
        user_profile: UserProfile,
    ) -> dict[str, float]:
        """Extract user preference features"""
        features = {}

        # Interest categories
        if user_profile.interests:
            for interest in user_profile.interests:
                features[f"interest_{interest}"] = 1.0

        # Preference weights
        features["preference_weight_academic"] = user_profile.preference_weights.get(
            "academic",
            0.0,
        )
        features["preference_weight_news"] = user_profile.preference_weights.get(
            "news",
            0.0,
        )
        features["preference_weight_blog"] = user_profile.preference_weights.get(
            "blog",
            0.0,
        )
        features["preference_weight_tutorial"] = user_profile.preference_weights.get(
            "tutorial",
            0.0,
        )

        # Learning preferences
        features["learning_rate"] = user_profile.learning_rate or 0.1
        features["exploration_factor"] = user_profile.exploration_factor or 0.1

        return features

    async def _extract_behavioral_features(
        self,
        interactions: list[UserInteraction],
    ) -> dict[str, float]:
        """Extract behavioral features from user interactions"""
        features = {}

        if not interactions:
            return features

        # Interaction counts by type
        interaction_counts = Counter(
            interaction.interaction_type for interaction in interactions
        )
        total_interactions = len(interactions)

        for interaction_type in ["view", "like", "share", "save", "click", "dismiss"]:
            count = interaction_counts.get(interaction_type, 0)
            features[f"{interaction_type}_count"] = count
            features[f"{interaction_type}_ratio"] = (
                count / total_interactions if total_interactions > 0 else 0
            )

        # Engagement patterns
        features["avg_session_duration"] = np.mean(
            [i.session_duration or 0 for i in interactions],
        )
        features["total_time_spent"] = sum(
            i.session_duration or 0 for i in interactions
        )

        # Interaction frequency
        if interactions:
            first_interaction = min(interactions, key=lambda x: x.timestamp)
            last_interaction = max(interactions, key=lambda x: x.timestamp)
            time_span = (last_interaction.timestamp - first_interaction.timestamp).days
            features["interaction_frequency"] = total_interactions / max(time_span, 1)

        return features

    async def _extract_temporal_features(
        self,
        interactions: list[UserInteraction],
    ) -> dict[str, float]:
        """Extract temporal patterns from interactions"""
        features = {}

        if not interactions:
            return features

        # Time-based patterns
        hours = [i.timestamp.hour for i in interactions]
        days = [i.timestamp.weekday() for i in interactions]

        features["avg_hour_of_day"] = np.mean(hours)
        features["avg_day_of_week"] = np.mean(days)

        # Activity patterns
        features["is_morning_user"] = 1.0 if np.mean(hours) < 12 else 0.0
        features["is_evening_user"] = 1.0 if np.mean(hours) > 18 else 0.0
        features["is_weekend_user"] = 1.0 if np.mean(days) >= 5 else 0.0

        # Recency
        now = datetime.now()
        recent_interactions = [i for i in interactions if (now - i.timestamp).days < 7]
        features["recent_activity_ratio"] = len(recent_interactions) / len(interactions)

        return features

    async def _extract_social_features(
        self,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> dict[str, float]:
        """Extract social and collaborative features"""
        features = {}

        # Social indicators
        features["has_social_profile"] = 1.0 if user_profile.social_links else 0.0
        features["social_link_count"] = (
            len(user_profile.social_links) if user_profile.social_links else 0
        )

        # Sharing behavior
        share_interactions = [i for i in interactions if i.interaction_type == "share"]
        features["sharing_frequency"] = (
            len(share_interactions) / len(interactions) if interactions else 0
        )

        return features

    def _calculate_flesch_score(self, text: str) -> float:
        """Calculate Flesch Reading Ease score"""
        try:
            sentences = re.findall(r"[.!?]+", text)
            words = text.split()
            syllables = sum(self._count_syllables(word) for word in words)

            if sentences and words:
                avg_sentence_length = len(words) / len(sentences)
                avg_syllables_per_word = syllables / len(words)
                score = (
                    206.835
                    - (1.015 * avg_sentence_length)
                    - (84.6 * avg_syllables_per_word)
                )
                return max(0, min(100, score))
        except BaseException:
            pass
        return 50.0  # Default middle score

    def _calculate_fk_grade(self, text: str) -> float:
        """Calculate Flesch-Kincaid Grade Level"""
        try:
            sentences = re.findall(r"[.!?]+", text)
            words = text.split()
            syllables = sum(self._count_syllables(word) for word in words)

            if sentences and words:
                avg_sentence_length = len(words) / len(sentences)
                avg_syllables_per_word = syllables / len(words)
                grade = (
                    (0.39 * avg_sentence_length)
                    + (11.8 * avg_syllables_per_word)
                    - 15.59
                )
                return max(0, grade)
        except BaseException:
            pass
        return 8.0  # Default grade level

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word"""
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel

        # Handle silent 'e'
        if word.endswith("e") and syllable_count > 1:
            syllable_count -= 1

        return max(1, syllable_count)

    async def _cleanup_cache(self):
        """Clean up old cache entries"""
        if len(self.feature_cache) <= self.cache_size:
            return

        # Remove oldest entries
        sorted_items = sorted(
            self.feature_cache.items(),
            key=lambda x: x[1].get("extracted_at", datetime.min),
        )

        items_to_remove = len(self.feature_cache) - self.cache_size
        for key, _ in sorted_items[:items_to_remove]:
            del self.feature_cache[key]

        logger.info(f"Cleaned up {items_to_remove} cache entries")

    async def get_feature_vector(
        self,
        content_features: ContentFeatures,
        user_features: UserFeatures,
    ) -> np.ndarray:
        """Combine content and user features into a single feature vector"""
        all_features = {}

        # Combine all feature dictionaries
        all_features.update(content_features.text_features)
        all_features.update(content_features.metadata_features)
        all_features.update(content_features.semantic_features)
        all_features.update(content_features.quality_features)
        all_features.update(user_features.preference_features)
        all_features.update(user_features.behavioral_features)
        all_features.update(user_features.temporal_features)
        all_features.update(user_features.social_features)

        # Convert to numpy array
        feature_vector = np.array(list(all_features.values()))

        # Handle NaN values
        feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=1.0, neginf=-1.0)

        return feature_vector

    async def batch_extract_features(
        self,
        contents: list[ContentItem],
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ) -> tuple[list[ContentFeatures], list[UserFeatures]]:
        """Extract features for multiple contents and users in batch"""
        logger.info(
            f"Batch extracting features for {len(contents)} contents and {
                len(user_profiles)
            } users",
        )

        # Extract content features
        content_tasks = [self.extract_content_features(content) for content in contents]
        content_features = await asyncio.gather(*content_tasks, return_exceptions=True)

        # Extract user features
        user_tasks = []
        for user_profile in user_profiles:
            user_interactions = [
                i for i in interactions if i.user_id == user_profile.user_id
            ]
            user_tasks.append(
                self.extract_user_features(user_profile, user_interactions),
            )

        user_features = await asyncio.gather(*user_tasks, return_exceptions=True)

        # Filter out exceptions
        content_features = [f for f in content_features if not isinstance(f, Exception)]
        user_features = [f for f in user_features if not isinstance(f, Exception)]

        logger.info(
            f"Successfully extracted features for {len(content_features)} contents and {
                len(user_features)
            } users",
        )
        return content_features, user_features
