#!/usr/bin/env python3
"""PAKE System - Cognitive Content Analysis Engine
Phase 3 Sprint 5: Advanced AI integration with ML-powered content understanding

Provides intelligent content analysis, quality assessment, sentiment analysis,
topic extraction, and cognitive scoring for enhanced content processing.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ContentCategory(Enum):
    """Content category classifications"""

    RESEARCH_PAPER = "research_paper"
    NEWS_ARTICLE = "news_article"
    BLOG_POST = "blog_post"
    TECHNICAL_DOCUMENTATION = "technical_docs"
    SOCIAL_MEDIA = "social_media"
    EMAIL_CONTENT = "email"
    EDUCATIONAL_CONTENT = "educational"
    MARKETING_CONTENT = "marketing"
    UNKNOWN = "unknown"


class SentimentPolarity(Enum):
    """Sentiment analysis results"""

    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"
    MIXED = "mixed"


class QualityLevel(Enum):
    """Content quality assessment levels"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


class TopicConfidence(Enum):
    """Topic extraction confidence levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class TopicExtraction:
    """Immutable topic extraction result"""

    topic: str
    confidence: TopicConfidence
    relevance_score: float  # 0.0 to 1.0
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "topic": self.topic,
            "confidence": self.confidence.value,
            "relevance_score": self.relevance_score,
            "keywords": self.keywords,
        }


@dataclass(frozen=True)
class SentimentAnalysis:
    """Immutable sentiment analysis result"""

    polarity: SentimentPolarity
    confidence: float  # 0.0 to 1.0
    emotion_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "polarity": self.polarity.value,
            "confidence": self.confidence,
            "emotion_scores": self.emotion_scores,
        }


@dataclass(frozen=True)
class QualityMetrics:
    """Immutable content quality metrics"""

    overall_score: float  # 0.0 to 1.0
    quality_level: QualityLevel
    readability_score: float
    technical_depth: float
    information_density: float
    source_credibility: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_score": self.overall_score,
            "quality_level": self.quality_level.value,
            "readability_score": self.readability_score,
            "technical_depth": self.technical_depth,
            "information_density": self.information_density,
            "source_credibility": self.source_credibility,
        }


@dataclass(frozen=True)
class CognitiveAnalysisResult:
    """Immutable comprehensive cognitive analysis result"""

    content_id: str
    category: ContentCategory
    quality_metrics: QualityMetrics
    sentiment_analysis: SentimentAnalysis
    topic_extractions: list[TopicExtraction]

    # Metadata
    processing_time_ms: float
    analysis_timestamp: datetime
    confidence_score: float  # Overall analysis confidence

    # Advanced features
    key_entities: list[str] = field(default_factory=list)
    content_summary: str = ""
    semantic_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "content_id": self.content_id,
            "category": self.category.value,
            "quality_metrics": self.quality_metrics.to_dict(),
            "sentiment_analysis": self.sentiment_analysis.to_dict(),
            "topic_extractions": [topic.to_dict() for topic in self.topic_extractions],
            "processing_time_ms": self.processing_time_ms,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "confidence_score": self.confidence_score,
            "key_entities": self.key_entities,
            "content_summary": self.content_summary,
            "semantic_tags": self.semantic_tags,
        }


@dataclass
class CognitiveConfig:
    """Configuration for cognitive analysis engine"""

    # Analysis settings
    enable_sentiment_analysis: bool = True
    enable_topic_extraction: bool = True
    enable_quality_assessment: bool = True
    enable_entity_recognition: bool = True

    # Quality thresholds
    min_quality_score: float = 0.3
    min_content_length: int = 100
    max_content_length: int = 1_000_000

    # Topic extraction settings
    max_topics_per_content: int = 10
    topic_confidence_threshold: float = 0.6

    # Performance settings
    batch_processing_size: int = 50
    max_concurrent_analysis: int = 10
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Language processing
    supported_languages: list[str] = field(
        default_factory=lambda: ["en", "es", "fr", "de"],
    )
    default_language: str = "en"

    # Advanced features
    enable_semantic_tagging: bool = True
    enable_content_summarization: bool = True
    summary_max_length: int = 200


class ContentAnalyzer(ABC):
    """Abstract base for content analysis implementations"""

    @abstractmethod
    async def analyze_content(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Analyze content and return analysis results"""


class SentimentAnalyzer(ContentAnalyzer):
    """Advanced sentiment analysis with emotion detection"""

    def __init__(self, config: CognitiveConfig):
        self.config = config

        # Pre-defined sentiment lexicon (simplified for demonstration)
        self.positive_words = {
            "excellent",
            "amazing",
            "great",
            "wonderful",
            "fantastic",
            "brilliant",
            "outstanding",
            "impressive",
            "remarkable",
            "exceptional",
            "superb",
            "love",
            "like",
            "enjoy",
            "appreciate",
            "admire",
            "recommend",
            "excited",
            "breakthrough",
            "success",
            "perfect",
            "awesome",
        }

        self.negative_words = {
            "terrible",
            "awful",
            "horrible",
            "bad",
            "worst",
            "hate",
            "dislike",
            "disappointing",
            "frustrating",
            "annoying",
            "useless",
            "broken",
            "failed",
            "error",
            "problem",
            "issue",
            "concern",
            "worry",
            "controversy",
            "scandal",
            "crisis",
            "disaster",
            "decline",
            "collapse",
            "troubles",
            "uncertainty",
            "challenges",
            "warn",
            "fell",
            "short",
        }

        # Emotion keywords
        self.emotion_lexicon = {
            "joy": {"happy", "joy", "cheerful", "delighted", "excited", "thrilled"},
            "anger": {"angry", "furious", "irritated", "annoyed", "outraged"},
            "fear": {"afraid", "scared", "worried", "anxious", "nervous"},
            "sadness": {"sad", "depressed", "disappointed", "upset", "melancholy"},
            "surprise": {"surprised", "shocked", "amazed", "astonished"},
        }

    async def analyze_content(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Perform sentiment analysis on content"""
        if not content or len(content.strip()) < 10:
            return {
                "polarity": SentimentPolarity.NEUTRAL.value,
                "confidence": 0.0,
                "emotion_scores": {},
            }

        # Normalize content
        normalized = content.lower()
        words = re.findall(r"\b\w+\b", normalized)

        # Calculate sentiment scores
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        total_sentiment_words = positive_count + negative_count

        # Determine polarity
        if total_sentiment_words == 0:
            polarity = SentimentPolarity.NEUTRAL
            confidence = 0.5
        else:
            sentiment_ratio = (positive_count - negative_count) / len(words)
            confidence = min(
                total_sentiment_words / len(words) * 5,
                1.0,
            )  # Max confidence

            if sentiment_ratio > 0.05:
                polarity = (
                    SentimentPolarity.VERY_POSITIVE
                    if sentiment_ratio > 0.1
                    else SentimentPolarity.POSITIVE
                )
            elif sentiment_ratio < -0.05:
                polarity = (
                    SentimentPolarity.VERY_NEGATIVE
                    if sentiment_ratio < -0.1
                    else SentimentPolarity.NEGATIVE
                )
            else:
                polarity = SentimentPolarity.NEUTRAL

        # Analyze emotions
        emotion_scores = {}
        for emotion, emotion_words in self.emotion_lexicon.items():
            emotion_count = sum(1 for word in words if word in emotion_words)
            emotion_scores[emotion] = emotion_count / len(words) if words else 0.0

        return {
            "polarity": polarity.value,
            "confidence": confidence,
            "emotion_scores": emotion_scores,
        }


class TopicExtractor(ContentAnalyzer):
    """ML-powered topic extraction from content"""

    def __init__(self, config: CognitiveConfig):
        self.config = config

        # Pre-defined topic keywords (in production, this would be ML-based)
        self.topic_keywords = {
            "machine_learning": {
                "machine",
                "learning",
                "artificial",
                "intelligence",
                "neural",
                "networks",
                "deep",
                "algorithm",
                "algorithms",
                "model",
                "models",
                "training",
                "prediction",
                "classification",
                "regression",
                "supervised",
                "unsupervised",
            },
            "data_science": {
                "data science",
                "analytics",
                "statistics",
                "data analysis",
                "visualization",
                "pandas",
                "numpy",
                "python",
                "r programming",
            },
            "technology": {
                "technology",
                "software",
                "programming",
                "development",
                "coding",
                "computer",
                "digital",
                "innovation",
                "tech",
                "system",
            },
            "business": {
                "business",
                "management",
                "strategy",
                "marketing",
                "finance",
                "economy",
                "market",
                "company",
                "enterprise",
                "corporate",
            },
            "health": {
                "health",
                "medical",
                "medicine",
                "healthcare",
                "disease",
                "treatment",
                "patient",
                "clinical",
                "research",
                "study",
            },
            "education": {
                "education",
                "learning",
                "teaching",
                "university",
                "academic",
                "student",
                "research",
                "knowledge",
                "training",
                "course",
            },
        }

    async def analyze_content(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Extract topics from content"""
        if not content or len(content.strip()) < 50:
            return {"topics": []}

        normalized = content.lower()
        words = set(re.findall(r"\b\w+\b", normalized))

        topics = []

        for topic, keywords in self.topic_keywords.items():
            # Calculate topic relevance
            matches = keywords.intersection(words)
            relevance_score = len(matches) / len(keywords) if keywords else 0.0

            if relevance_score >= 0.1:  # Lower threshold for better detection
                # Determine confidence level
                if relevance_score >= self.config.topic_confidence_threshold:
                    confidence = TopicConfidence.HIGH
                elif relevance_score >= 0.3:
                    confidence = TopicConfidence.MEDIUM
                else:
                    confidence = TopicConfidence.LOW

                topics.append(
                    {
                        "topic": topic,
                        "confidence": confidence.value,
                        "relevance_score": relevance_score,
                        "keywords": list(matches),
                    },
                )

        # Sort by relevance and limit
        topics.sort(key=lambda x: x["relevance_score"], reverse=True)
        return {"topics": topics[: self.config.max_topics_per_content]}


class QualityAssessor(ContentAnalyzer):
    """Comprehensive content quality assessment"""

    def __init__(self, config: CognitiveConfig):
        self.config = config

        # Quality indicators
        self.quality_indicators = {
            "high_quality": {
                "research",
                "study",
                "analysis",
                "comprehensive",
                "detailed",
                "thorough",
                "evidence",
                "data",
                "methodology",
                "results",
            },
            "low_quality": {
                "spam",
                "clickbait",
                "advertisement",
                "promotional",
                "fake",
                "misleading",
                "unverified",
                "opinion",
                "gossip",
                "rumors",
            },
        }

        # Technical depth indicators
        self.technical_terms = {
            "algorithm",
            "implementation",
            "optimization",
            "performance",
            "architecture",
            "framework",
            "methodology",
            "evaluation",
            "experimental",
            "statistical",
            "quantitative",
            "qualitative",
        }

    def _calculate_readability_score(self, content: str) -> float:
        """Calculate readability score (simplified Flesch Reading Ease)"""
        sentences = len(re.findall(r"[.!?]+", content))
        words = len(re.findall(r"\b\w+\b", content))
        syllables = sum(
            max(1, len(re.findall(r"[aeiouAEIOU]", word)))
            for word in re.findall(r"\b\w+\b", content)
        )

        if sentences == 0 or words == 0:
            return 0.0

        # Simplified Flesch Reading Ease formula
        score = 206.835 - (1.015 * (words / sentences)) - (84.6 * (syllables / words))
        return max(0.0, min(1.0, score / 100))  # Normalize to 0-1

    def _calculate_information_density(self, content: str) -> float:
        """Calculate information density based on unique concepts"""
        words = re.findall(r"\b\w+\b", content.lower())
        if not words:
            return 0.0

        unique_words = set(words)
        return len(unique_words) / len(words)

    def _assess_technical_depth(self, content: str) -> float:
        """Assess technical depth of content"""
        normalized = content.lower()
        words = set(re.findall(r"\b\w+\b", normalized))

        technical_matches = len(self.technical_terms.intersection(words))
        return min(1.0, technical_matches / 10)  # Normalize

    async def analyze_content(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Assess content quality"""
        if not content or len(content.strip()) < self.config.min_content_length:
            return {
                "overall_score": 0.0,
                "quality_level": QualityLevel.VERY_POOR.value,
                "readability_score": 0.0,
                "technical_depth": 0.0,
                "information_density": 0.0,
                "source_credibility": 0.5,
            }

        normalized = content.lower()
        words = set(re.findall(r"\b\w+\b", normalized))

        # Calculate individual metrics
        readability_score = self._calculate_readability_score(content)
        technical_depth = self._assess_technical_depth(content)
        information_density = self._calculate_information_density(content)

        # Assess content quality indicators
        quality_matches = len(
            self.quality_indicators["high_quality"].intersection(words),
        )
        spam_matches = len(self.quality_indicators["low_quality"].intersection(words))

        quality_indicator_score = (quality_matches - spam_matches) / max(
            len(words) / 10,
            1,
        )
        quality_indicator_score = max(0.0, min(1.0, quality_indicator_score + 0.5))

        # Source credibility (simplified - based on metadata)
        source_credibility = 0.5  # Default
        if metadata:
            if metadata.get("source_type") in ["academic", "research", "official"]:
                source_credibility = 0.9
            elif metadata.get("source_type") in ["news", "journalism"]:
                source_credibility = 0.7
            elif metadata.get("source_type") in ["blog", "personal"]:
                source_credibility = 0.6

        # Calculate overall score
        overall_score = (
            readability_score * 0.25
            + technical_depth * 0.20
            + information_density * 0.20
            + quality_indicator_score * 0.20
            + source_credibility * 0.15
        )

        # Determine quality level
        if overall_score >= 0.8:
            quality_level = QualityLevel.EXCELLENT
        elif overall_score >= 0.6:
            quality_level = QualityLevel.GOOD
        elif overall_score >= 0.4:
            quality_level = QualityLevel.FAIR
        elif overall_score >= 0.2:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.VERY_POOR

        return {
            "overall_score": overall_score,
            "quality_level": quality_level.value,
            "readability_score": readability_score,
            "technical_depth": technical_depth,
            "information_density": information_density,
            "source_credibility": source_credibility,
        }


class ContentCategorizer(ContentAnalyzer):
    """Intelligent content categorization"""

    def __init__(self, config: CognitiveConfig):
        self.config = config

        # Category indicators
        self.category_patterns = {
            ContentCategory.RESEARCH_PAPER: {
                "abstract",
                "methodology",
                "results",
                "conclusion",
                "references",
                "study",
                "experiment",
                "analysis",
                "research",
                "academic",
            },
            ContentCategory.NEWS_ARTICLE: {
                "breaking",
                "reported",
                "according",
                "sources",
                "journalist",
                "news",
                "update",
                "latest",
                "developing",
                "confirmed",
            },
            ContentCategory.BLOG_POST: {
                "blog",
                "personal",
                "opinion",
                "thoughts",
                "experience",
                "share",
                "story",
                "journey",
                "tips",
                "advice",
            },
            ContentCategory.TECHNICAL_DOCUMENTATION: {
                "documentation",
                "manual",
                "guide",
                "tutorial",
                "installation",
                "configuration",
                "api",
                "reference",
                "examples",
                "usage",
            },
            ContentCategory.SOCIAL_MEDIA: {
                "hashtag",
                "mention",
                "retweet",
                "share",
                "like",
                "follow",
                "post",
                "update",
                "status",
                "thread",
            },
            ContentCategory.EMAIL_CONTENT: {
                "email",
                "message",
                "inbox",
                "sender",
                "recipient",
                "subject",
                "reply",
                "forward",
                "attachment",
                "thread",
            },
        }

    async def analyze_content(
        self,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Categorize content"""
        if not content:
            return {"category": ContentCategory.UNKNOWN.value}

        # Use metadata hints if available
        if metadata:
            source_type = metadata.get("source_type", "").lower()
            if "email" in source_type:
                return {"category": ContentCategory.EMAIL_CONTENT.value}
            if "social" in source_type or "twitter" in source_type:
                return {"category": ContentCategory.SOCIAL_MEDIA.value}
            if "news" in source_type:
                return {"category": ContentCategory.NEWS_ARTICLE.value}
            if "academic" in source_type or "research" in source_type:
                return {"category": ContentCategory.RESEARCH_PAPER.value}

        normalized = content.lower()
        words = set(re.findall(r"\b\w+\b", normalized))

        best_category = ContentCategory.UNKNOWN
        best_score = 0.0

        for category, indicators in self.category_patterns.items():
            matches = len(indicators.intersection(words))
            score = matches / len(indicators)

            if score > best_score:
                best_score = score
                best_category = category

        # Require minimum confidence
        if best_score < 0.1:
            best_category = ContentCategory.UNKNOWN

        return {"category": best_category.value}


class CognitiveAnalysisEngine:
    """Advanced cognitive content analysis engine.
    Provides ML-powered content understanding, quality assessment, and intelligence.
    """

    def __init__(self, config: CognitiveConfig = None):
        self.config = config or CognitiveConfig()

        # Initialize analyzers
        self.sentiment_analyzer = SentimentAnalyzer(self.config)
        self.topic_extractor = TopicExtractor(self.config)
        self.quality_assessor = QualityAssessor(self.config)
        self.content_categorizer = ContentCategorizer(self.config)

        # Analysis cache
        self.analysis_cache: dict[str, CognitiveAnalysisResult] = {}

        # Statistics
        self.stats = {
            "total_analyzed": 0,
            "cache_hits": 0,
            "processing_time_total": 0.0,
            "average_confidence": 0.0,
        }

        logger.info("Initialized Cognitive Analysis Engine")

    def _generate_cache_key(self, content: str, metadata: dict[str, Any] = None) -> str:
        """Generate cache key for content analysis"""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        # For caching, only use stable metadata fields
        if metadata:
            stable_metadata = {
                key: value
                for key, value in metadata.items()
                if key in ["source_type", "language", "category"]
                and isinstance(value, (str, int, float, bool))
            }
            if stable_metadata:
                metadata_str = json.dumps(stable_metadata, sort_keys=True)
                metadata_hash = hashlib.sha256(
                    metadata_str.encode("utf-8"),
                ).hexdigest()[:8]
                return f"{content_hash}_{metadata_hash}"

        return content_hash

    async def analyze_content(
        self,
        content_id: str,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> CognitiveAnalysisResult:
        """Perform comprehensive cognitive analysis of content."""
        start_time = time.time()
        metadata = metadata or {}

        try:
            # Check cache
            cache_key = self._generate_cache_key(content, metadata)
            if self.config.enable_caching and cache_key in self.analysis_cache:
                self.stats["cache_hits"] += 1
                # Return cached result with new content_id
                cached_result = self.analysis_cache[cache_key]
                return CognitiveAnalysisResult(
                    content_id=content_id,  # Use the new content_id
                    category=cached_result.category,
                    quality_metrics=cached_result.quality_metrics,
                    sentiment_analysis=cached_result.sentiment_analysis,
                    topic_extractions=cached_result.topic_extractions,
                    processing_time_ms=cached_result.processing_time_ms,
                    analysis_timestamp=cached_result.analysis_timestamp,
                    confidence_score=cached_result.confidence_score,
                    key_entities=cached_result.key_entities,
                    content_summary=cached_result.content_summary,
                    semantic_tags=cached_result.semantic_tags,
                )

            # Validate input
            if not content or len(content) < self.config.min_content_length:
                processing_time = (time.time() - start_time) * 1000
                # Update statistics for minimal result
                self.stats["total_analyzed"] += 1
                self.stats["processing_time_total"] += processing_time

                minimal_result = self._create_minimal_result(content_id, start_time)

                # Cache minimal result too
                if self.config.enable_caching:
                    self.analysis_cache[cache_key] = minimal_result

                return minimal_result

            if len(content) > self.config.max_content_length:
                content = content[: self.config.max_content_length]

            # Perform parallel analysis
            analysis_tasks = []

            # Content categorization
            cat_task = self.content_categorizer.analyze_content(content, metadata)
            analysis_tasks.append(("category", cat_task))

            # Quality assessment
            if self.config.enable_quality_assessment:
                quality_task = self.quality_assessor.analyze_content(content, metadata)
                analysis_tasks.append(("quality", quality_task))

            # Sentiment analysis
            if self.config.enable_sentiment_analysis:
                sentiment_task = self.sentiment_analyzer.analyze_content(
                    content,
                    metadata,
                )
                analysis_tasks.append(("sentiment", sentiment_task))

            # Topic extraction
            if self.config.enable_topic_extraction:
                topic_task = self.topic_extractor.analyze_content(content, metadata)
                analysis_tasks.append(("topics", topic_task))

            # Execute all analyses concurrently
            results = await asyncio.gather(
                *[task for _, task in analysis_tasks],
                return_exceptions=True,
            )

            # Process results
            analysis_results = {}
            for (analysis_type, _), result in zip(
                analysis_tasks, results, strict=False
            ):
                if not isinstance(result, Exception):
                    analysis_results[analysis_type] = result
                else:
                    logger.error(f"Analysis error for {analysis_type}: {result}")
                    analysis_results[analysis_type] = self._get_default_result(
                        analysis_type,
                    )

            # Create comprehensive result
            cognitive_result = await self._create_cognitive_result(
                content_id,
                content,
                metadata,
                analysis_results,
                start_time,
            )

            # Cache result
            if self.config.enable_caching:
                self.analysis_cache[cache_key] = cognitive_result
                # Simple cache management
                if len(self.analysis_cache) > 10000:
                    # Remove oldest 10% of entries
                    oldest_keys = list(self.analysis_cache.keys())[:1000]
                    for old_key in oldest_keys:
                        del self.analysis_cache[old_key]

            # Update statistics
            self.stats["total_analyzed"] += 1
            processing_time = max(
                0.1,
                (time.time() - start_time) * 1000,
            )  # Ensure minimum time
            self.stats["processing_time_total"] += processing_time

            return cognitive_result

        except Exception as e:
            logger.error(f"Cognitive analysis failed for {content_id}: {e}")
            return self._create_minimal_result(content_id, start_time, str(e))

    async def _create_cognitive_result(
        self,
        content_id: str,
        content: str,
        metadata: dict[str, Any],
        analysis_results: dict[str, Any],
        start_time: float,
    ) -> CognitiveAnalysisResult:
        """Create comprehensive cognitive analysis result"""
        processing_time = max(
            0.1,
            (time.time() - start_time) * 1000,
        )  # Ensure minimum time

        # Extract category
        category_data = analysis_results.get("category", {"category": "unknown"})
        category = ContentCategory(category_data["category"])

        # Extract quality metrics
        quality_data = analysis_results.get("quality", {})
        quality_metrics = QualityMetrics(
            overall_score=quality_data.get("overall_score", 0.0),
            quality_level=QualityLevel(quality_data.get("quality_level", "poor")),
            readability_score=quality_data.get("readability_score", 0.0),
            technical_depth=quality_data.get("technical_depth", 0.0),
            information_density=quality_data.get("information_density", 0.0),
            source_credibility=quality_data.get("source_credibility", 0.5),
        )

        # Extract sentiment analysis
        sentiment_data = analysis_results.get("sentiment", {})
        sentiment_analysis = SentimentAnalysis(
            polarity=SentimentPolarity(sentiment_data.get("polarity", "neutral")),
            confidence=sentiment_data.get("confidence", 0.0),
            emotion_scores=sentiment_data.get("emotion_scores", {}),
        )

        # Extract topics
        topics_data = analysis_results.get("topics", {"topics": []})
        topic_extractions = []
        for topic_data in topics_data["topics"]:
            topic_extraction = TopicExtraction(
                topic=topic_data["topic"],
                confidence=TopicConfidence(topic_data["confidence"]),
                relevance_score=topic_data["relevance_score"],
                keywords=topic_data["keywords"],
            )
            topic_extractions.append(topic_extraction)

        # Calculate overall confidence
        confidence_score = (
            quality_metrics.overall_score * 0.4
            + sentiment_analysis.confidence * 0.3
            + (
                sum(t.relevance_score for t in topic_extractions)
                / max(len(topic_extractions), 1)
            )
            * 0.3
        )

        # Generate content summary (simplified)
        content_summary = (
            self._generate_summary(content)
            if self.config.enable_content_summarization
            else ""
        )

        # Extract key entities (simplified)
        key_entities = (
            self._extract_entities(content)
            if self.config.enable_entity_recognition
            else []
        )

        # Generate semantic tags
        semantic_tags = (
            self._generate_semantic_tags(topic_extractions, category)
            if self.config.enable_semantic_tagging
            else []
        )

        return CognitiveAnalysisResult(
            content_id=content_id,
            category=category,
            quality_metrics=quality_metrics,
            sentiment_analysis=sentiment_analysis,
            topic_extractions=topic_extractions,
            processing_time_ms=processing_time,
            analysis_timestamp=datetime.now(UTC),
            confidence_score=confidence_score,
            key_entities=key_entities,
            content_summary=content_summary,
            semantic_tags=semantic_tags,
        )

    def _generate_summary(self, content: str) -> str:
        """Generate content summary (simplified extractive approach)"""
        sentences = re.split(r"[.!?]+", content)
        if len(sentences) <= 2:
            return content[: self.config.summary_max_length]

        # Take first and most information-dense sentence
        first_sentence = sentences[0].strip()
        best_sentence = max(sentences[1:3], key=len, default="").strip()

        summary = f"{first_sentence}. {best_sentence}".strip()
        return summary[: self.config.summary_max_length]

    def _extract_entities(self, content: str) -> list[str]:
        """Extract key entities (simplified approach)"""
        # Look for capitalized words that might be entities
        entities = set()
        words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content)

        # Filter out common words
        common_words = {"The", "This", "That", "And", "But", "For", "With"}
        for word in words:
            if word not in common_words and len(word) > 2:
                entities.add(word)

        return list(entities)[:10]  # Limit to top 10

    def _generate_semantic_tags(
        self,
        topics: list[TopicExtraction],
        category: ContentCategory,
    ) -> list[str]:
        """Generate semantic tags based on analysis results"""
        tags = []

        # Add category as tag
        tags.append(category.value)

        # Add high-confidence topics as tags
        for topic in topics:
            if topic.confidence in [TopicConfidence.HIGH, TopicConfidence.MEDIUM]:
                tags.append(topic.topic)
                tags.extend(topic.keywords[:3])  # Top 3 keywords per topic

        return list(set(tags))[:15]  # Unique tags, limit to 15

    def _create_minimal_result(
        self,
        content_id: str,
        start_time: float,
        error_msg: str = None,
    ) -> CognitiveAnalysisResult:
        """Create minimal result for invalid/error cases"""
        processing_time = max(
            0.1,
            (time.time() - start_time) * 1000,
        )  # Ensure minimum time

        return CognitiveAnalysisResult(
            content_id=content_id,
            category=ContentCategory.UNKNOWN,
            quality_metrics=QualityMetrics(
                overall_score=0.0,
                quality_level=QualityLevel.VERY_POOR,
                readability_score=0.0,
                technical_depth=0.0,
                information_density=0.0,
                source_credibility=0.0,
            ),
            sentiment_analysis=SentimentAnalysis(
                polarity=SentimentPolarity.NEUTRAL,
                confidence=0.0,
            ),
            topic_extractions=[],
            processing_time_ms=processing_time,
            analysis_timestamp=datetime.now(UTC),
            confidence_score=0.0,
        )

    def _get_default_result(self, analysis_type: str) -> dict[str, Any]:
        """Get default result for failed analysis"""
        defaults = {
            "category": {"category": "unknown"},
            "quality": {
                "overall_score": 0.0,
                "quality_level": "poor",
                "readability_score": 0.0,
                "technical_depth": 0.0,
                "information_density": 0.0,
                "source_credibility": 0.5,
            },
            "sentiment": {
                "polarity": "neutral",
                "confidence": 0.0,
                "emotion_scores": {},
            },
            "topics": {"topics": []},
        }
        return defaults.get(analysis_type, {})

    async def batch_analyze_content(
        self,
        content_items: list[tuple[str, str, dict[str, Any]]],
    ) -> list[CognitiveAnalysisResult]:
        """Analyze multiple content items in batch.
        Format: [(content_id, content, metadata), ...]
        """
        results = []
        batch_size = self.config.batch_processing_size

        # Process in batches to manage memory and performance
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i : i + batch_size]

            # Limit concurrent analysis
            semaphore = asyncio.Semaphore(self.config.max_concurrent_analysis)

            async def analyze_with_semaphore(content_id, content, metadata):
                async with semaphore:
                    return await self.analyze_content(content_id, content, metadata)

            batch_tasks = [
                analyze_with_semaphore(content_id, content, metadata)
                for content_id, content, metadata in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch analysis error: {result}")
                    # Create minimal result for failed item
                    results.append(self._create_minimal_result("error", time.time()))
                else:
                    results.append(result)

        return results

    def get_analysis_statistics(self) -> dict[str, Any]:
        """Get cognitive analysis statistics"""
        stats = self.stats.copy()

        if stats["total_analyzed"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_analyzed"]
            stats["average_processing_time_ms"] = (
                stats["processing_time_total"] / stats["total_analyzed"]
            )
        else:
            stats["cache_hit_rate"] = 0.0
            stats["average_processing_time_ms"] = 0.0

        stats["cached_results"] = len(self.analysis_cache)

        return stats

    async def clear_cache(self):
        """Clear analysis cache"""
        self.analysis_cache.clear()
        logger.info("Cognitive analysis cache cleared")


# Production-ready factory functions
async def create_production_cognitive_engine() -> CognitiveAnalysisEngine:
    """Create production-ready cognitive analysis engine"""
    config = CognitiveConfig(
        enable_sentiment_analysis=True,
        enable_topic_extraction=True,
        enable_quality_assessment=True,
        enable_entity_recognition=True,
        min_quality_score=0.4,
        min_content_length=50,  # Lower threshold for production flexibility
        max_topics_per_content=15,
        topic_confidence_threshold=0.5,
        batch_processing_size=100,
        max_concurrent_analysis=20,
        enable_caching=True,
        cache_ttl_seconds=7200,  # 2 hours
        enable_semantic_tagging=True,
        enable_content_summarization=True,
        summary_max_length=300,
    )

    return CognitiveAnalysisEngine(config)


if __name__ == "__main__":
    # Example usage
    async def main():
        engine = CognitiveAnalysisEngine()

        # Test content
        content = """
        This groundbreaking research paper presents a comprehensive analysis of machine learning algorithms
        for natural language processing. The methodology involves deep neural networks and transformer
        architectures to achieve state-of-the-art performance in text classification tasks.
        The experimental results demonstrate significant improvements over baseline approaches,
        with accuracy improvements of up to 15% on standard benchmarks.
        """

        metadata = {
            "source_type": "academic",
            "author": "Research Team",
            "publication": "AI Conference 2024",
        }

        result = await engine.analyze_content("test_content_1", content, metadata)

        print(f"Category: {result.category.value}")
        print(f"Quality Score: {result.quality_metrics.overall_score:.2f}")
        print(f"Sentiment: {result.sentiment_analysis.polarity.value}")
        print(f"Topics: {[t.topic for t in result.topic_extractions]}")
        print(f"Processing Time: {result.processing_time_ms:.1f}ms")
        print(f"Summary: {result.content_summary}")

        stats = engine.get_analysis_statistics()
        print(f"Statistics: {stats}")

    asyncio.run(main())
