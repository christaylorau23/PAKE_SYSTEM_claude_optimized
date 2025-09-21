"""ContentAnalysisService

Provides comprehensive content analysis including quality assessment, topic extraction,
sentiment analysis, and readability scoring. This service is ML-enabled and integrates
with the PAKE system's existing AI capabilities.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import nltk
import numpy as np
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize, word_tokenize
from sentence_transformers import SentenceTransformer
from textstat import flesch_kincaid_grade, flesch_reading_ease

from ..models.content_item import ContentEmbedding, ContentItem, ContentType

# Download required NLTK data
try:
    nltk.data.find("vader_lexicon")
except LookupError:
    nltk.download("vader_lexicon")

try:
    nltk.data.find("punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("stopwords")
except LookupError:
    nltk.download("stopwords")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QualityMetrics:
    """Comprehensive content quality metrics"""

    readability_score: float = 0.0  # 0-1 scale
    complexity_score: float = 0.0  # 0-1 scale (higher = more complex)
    coherence_score: float = 0.0  # 0-1 scale
    completeness_score: float = 0.0  # 0-1 scale
    authority_indicators: float = 0.0  # 0-1 scale
    freshness_score: float = 0.0  # 0-1 scale
    overall_quality: float = 0.0  # Weighted combination

    def to_dict(self) -> dict[str, float]:
        return {
            "readability_score": self.readability_score,
            "complexity_score": self.complexity_score,
            "coherence_score": self.coherence_score,
            "completeness_score": self.completeness_score,
            "authority_indicators": self.authority_indicators,
            "freshness_score": self.freshness_score,
            "overall_quality": self.overall_quality,
        }


@dataclass(frozen=True)
class SentimentAnalysis:
    """Sentiment analysis results"""

    compound: float = 0.0  # Overall sentiment (-1 to 1)
    positive: float = 0.0  # Positive sentiment (0-1)
    negative: float = 0.0  # Negative sentiment (0-1)
    neutral: float = 0.0  # Neutral sentiment (0-1)
    confidence: float = 0.0  # Confidence in sentiment (0-1)

    def to_dict(self) -> dict[str, float]:
        return {
            "compound": self.compound,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class TopicExtraction:
    """Extracted topics and keywords"""

    primary_topics: list[str] = field(default_factory=list)
    secondary_topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_topics": self.primary_topics,
            "secondary_topics": self.secondary_topics,
            "keywords": self.keywords,
            "entities": self.entities,
            "confidence_scores": self.confidence_scores,
        }


@dataclass(frozen=True)
class ContentAnalysisResult:
    """Complete content analysis result"""

    content_id: str
    quality_metrics: QualityMetrics
    sentiment_analysis: SentimentAnalysis
    topic_extraction: TopicExtraction
    embedding: ContentEmbedding | None = None
    processing_time_ms: float = 0.0
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_id": self.content_id,
            "quality_metrics": self.quality_metrics.to_dict(),
            "sentiment_analysis": self.sentiment_analysis.to_dict(),
            "topic_extraction": self.topic_extraction.to_dict(),
            "embedding": self.embedding.to_list() if self.embedding else None,
            "processing_time_ms": self.processing_time_ms,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


class ContentAnalysisService:
    """Advanced content analysis service with ML capabilities.

    Provides comprehensive content evaluation including quality assessment,
    topic extraction, sentiment analysis, and embedding generation.
    """

    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        enable_gpu: bool = False,
    ):
        """Initialize the content analysis service.

        Args:
            embedding_model_name: Name of the sentence transformer model
            enable_gpu: Whether to use GPU acceleration
        """
        self.embedding_model_name = embedding_model_name
        self.enable_gpu = enable_gpu

        # Initialize models
        self._embedding_model = None
        self._sentiment_analyzer = None
        self._stop_words = set(stopwords.words("english"))

        # Quality assessment weights
        self.quality_weights = {
            "readability": 0.15,
            "complexity": 0.15,
            "coherence": 0.20,
            "completeness": 0.20,
            "authority": 0.15,
            "freshness": 0.15,
        }

        logger.info(
            f"ContentAnalysisService initialized with model: {embedding_model_name}",
        )

    async def _load_models(self) -> None:
        """Lazy load ML models to avoid startup delays"""
        if self._embedding_model is None:

            def load_embedding_model():
                device = "cuda" if self.enable_gpu else "cpu"
                return SentenceTransformer(self.embedding_model_name, device=device)

            # Load in thread to avoid blocking
            loop = asyncio.get_event_loop()
            self._embedding_model = await loop.run_in_executor(
                None,
                load_embedding_model,
            )
            logger.info("Embedding model loaded successfully")

        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = SentimentIntensityAnalyzer()
            logger.info("Sentiment analyzer loaded successfully")

    async def analyze_content(self, content_item: ContentItem) -> ContentAnalysisResult:
        """Perform comprehensive content analysis.

        Args:
            content_item: Content item to analyze

        Returns:
            Complete analysis result with quality, sentiment, and topics
        """
        start_time = datetime.now()

        try:
            # Ensure models are loaded
            await self._load_models()

            # Get content text for analysis
            content_text = content_item.get_content_text()

            if not content_text.strip():
                logger.warning(f"Empty content for item {content_item.id}")
                return self._create_empty_result(str(content_item.id))

            # Run analysis components concurrently
            tasks = [
                self._analyze_quality(content_text, content_item),
                self._analyze_sentiment(content_text),
                self._extract_topics(content_text),
                self._generate_embedding(content_text),
            ]

            (
                quality_metrics,
                sentiment_analysis,
                topic_extraction,
                embedding,
            ) = await asyncio.gather(*tasks)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            result = ContentAnalysisResult(
                content_id=str(content_item.id),
                quality_metrics=quality_metrics,
                sentiment_analysis=sentiment_analysis,
                topic_extraction=topic_extraction,
                embedding=embedding,
                processing_time_ms=processing_time,
                analysis_timestamp=datetime.now(),
            )

            logger.info(
                f"Content analysis completed for {content_item.id} in {
                    processing_time:.2f}ms",
            )
            return result

        except Exception as e:
            logger.error(f"Error analyzing content {content_item.id}: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return self._create_error_result(str(content_item.id), processing_time)

    async def _analyze_quality(
        self,
        content_text: str,
        content_item: ContentItem,
    ) -> QualityMetrics:
        """Analyze content quality across multiple dimensions"""

        def analyze_quality_sync():
            try:
                # Readability analysis
                readability_score = self._calculate_readability_score(content_text)

                # Complexity analysis
                complexity_score = self._calculate_complexity_score(content_text)

                # Coherence analysis
                coherence_score = self._calculate_coherence_score(content_text)

                # Completeness analysis
                completeness_score = self._calculate_completeness_score(
                    content_text,
                    content_item,
                )

                # Authority indicators
                authority_indicators = self._calculate_authority_indicators(
                    content_text,
                    content_item,
                )

                # Freshness score
                freshness_score = self._calculate_freshness_score(content_item)

                # Overall quality (weighted combination)
                overall_quality = (
                    readability_score * self.quality_weights["readability"]
                    + complexity_score * self.quality_weights["complexity"]
                    + coherence_score * self.quality_weights["coherence"]
                    + completeness_score * self.quality_weights["completeness"]
                    + authority_indicators * self.quality_weights["authority"]
                    + freshness_score * self.quality_weights["freshness"]
                )

                return QualityMetrics(
                    readability_score=readability_score,
                    complexity_score=complexity_score,
                    coherence_score=coherence_score,
                    completeness_score=completeness_score,
                    authority_indicators=authority_indicators,
                    freshness_score=freshness_score,
                    overall_quality=overall_quality,
                )

            except Exception as e:
                logger.error(f"Error in quality analysis: {str(e)}")
                return QualityMetrics()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, analyze_quality_sync)

    def _calculate_readability_score(self, text: str) -> float:
        """Calculate readability score (0-1, higher = more readable)"""
        try:
            # Use Flesch Reading Ease (0-100 scale)
            flesch_score = flesch_reading_ease(text)
            # Convert to 0-1 scale (90-100 = 1.0, 0-30 = 0.0)
            normalized_score = max(0.0, min(1.0, (flesch_score - 30) / 70))
            return normalized_score
        except BaseException:
            return 0.5  # Default medium readability

    def _calculate_complexity_score(self, text: str) -> float:
        """Calculate content complexity (0-1, higher = more complex)"""
        try:
            # Flesch-Kincaid Grade Level
            grade_level = flesch_kincaid_grade(text)

            # Sentence length variance
            sentences = sent_tokenize(text)
            if len(sentences) > 1:
                sentence_lengths = [len(word_tokenize(sent)) for sent in sentences]
                length_variance = (
                    np.var(sentence_lengths) / np.mean(sentence_lengths)
                    if sentence_lengths
                    else 0
                )
            else:
                length_variance = 0

            # Vocabulary complexity (unique words ratio)
            words = word_tokenize(text.lower())
            unique_ratio = len(set(words)) / len(words) if words else 0

            # Combine metrics (normalize to 0-1)
            complexity = (
                min(1.0, grade_level / 20.0) * 0.5  # Grade level component
                + min(1.0, length_variance / 2.0) * 0.3  # Sentence variance
                + unique_ratio * 0.2  # Vocabulary diversity
            )

            return complexity

        except BaseException:
            return 0.5  # Default medium complexity

    def _calculate_coherence_score(self, text: str) -> float:
        """Calculate content coherence using linguistic features"""
        try:
            sentences = sent_tokenize(text)
            if len(sentences) < 2:
                return 0.8  # Short content, assume coherent

            # Lexical cohesion (word overlap between adjacent sentences)
            cohesion_scores = []
            for i in range(len(sentences) - 1):
                words1 = set(word_tokenize(sentences[i].lower())) - self._stop_words
                words2 = set(word_tokenize(sentences[i + 1].lower())) - self._stop_words

                if words1 and words2:
                    overlap = len(words1.intersection(words2))
                    union = len(words1.union(words2))
                    cohesion_scores.append(overlap / union if union > 0 else 0)

            # Average cohesion score
            avg_cohesion = np.mean(cohesion_scores) if cohesion_scores else 0

            # Sentence transition indicators
            transition_words = {
                "however",
                "therefore",
                "furthermore",
                "moreover",
                "additionally",
                "consequently",
                "similarly",
                "likewise",
                "contrast",
                "meanwhile",
            }

            transition_count = sum(
                1
                for sent in sentences
                for word in transition_words
                if word in sent.lower()
            )

            transition_score = min(1.0, transition_count / max(1, len(sentences) - 1))

            # Combine scores
            coherence_score = avg_cohesion * 0.7 + transition_score * 0.3
            return min(1.0, coherence_score)

        except BaseException:
            return 0.5  # Default medium coherence

    def _calculate_completeness_score(
        self,
        text: str,
        content_item: ContentItem,
    ) -> float:
        """Calculate content completeness based on various factors"""
        try:
            word_count = len(word_tokenize(text))

            # Length-based completeness (different thresholds by content type)
            if content_item.content_type == ContentType.PAPER:
                # Academic papers should be longer
                length_score = min(1.0, word_count / 3000)
            elif content_item.content_type == ContentType.ARTICLE:
                # Articles moderate length
                length_score = min(1.0, word_count / 800)
            else:
                # Blog posts, shorter content
                length_score = min(1.0, word_count / 500)

            # Structure indicators (headings, lists, etc.)
            structure_indicators = 0
            if content_item.title and len(content_item.title) > 10:
                structure_indicators += 0.2
            if content_item.summary and len(content_item.summary) > 50:
                structure_indicators += 0.3
            if "•" in text or "-" in text or re.search(r"\d+\.", text):
                structure_indicators += 0.2  # Lists
            if re.search(r"[A-Z][^.]*:", text):
                structure_indicators += 0.3  # Possible headings

            completeness = length_score * 0.6 + min(1.0, structure_indicators) * 0.4
            return completeness

        except BaseException:
            return 0.5

    def _calculate_authority_indicators(
        self,
        text: str,
        content_item: ContentItem,
    ) -> float:
        """Calculate authority indicators from content and metadata"""
        try:
            authority_score = 0.0

            # Author credentials
            if content_item.author:
                author_keywords = [
                    "dr.",
                    "prof.",
                    "phd",
                    "md",
                    "professor",
                    "researcher",
                ]
                if any(
                    keyword in content_item.author.lower()
                    for keyword in author_keywords
                ):
                    authority_score += 0.3

            # Citation indicators
            citation_patterns = [
                r"\([12]\d{3}\)",  # (2023)
                r"\[[0-9]+\]",  # [1]
                r"et al\.",  # et al.
                r"doi:",  # DOI references
                r"https?://[^\s]+",  # URLs
            ]

            citation_count = sum(
                len(re.findall(pattern, text, re.IGNORECASE))
                for pattern in citation_patterns
            )
            authority_score += min(0.4, citation_count / 10)  # Max 0.4 for citations

            # Source authority (if available)
            if (
                hasattr(content_item, "authority_score")
                and content_item.authority_score
            ):
                authority_score += content_item.authority_score * 0.3

            return min(1.0, authority_score)

        except BaseException:
            return 0.3  # Default low-medium authority

    def _calculate_freshness_score(self, content_item: ContentItem) -> float:
        """Calculate content freshness based on publication date"""
        try:
            if not content_item.published_date:
                return 0.5  # Unknown date, assume medium freshness

            days_old = (datetime.now() - content_item.published_date).days

            # Freshness decay function
            if days_old <= 7:
                return 1.0  # Very fresh
            if days_old <= 30:
                return 0.8  # Fresh
            if days_old <= 90:
                return 0.6  # Moderately fresh
            if days_old <= 365:
                return 0.4  # Aging
            return 0.2  # Old

        except BaseException:
            return 0.5

    async def _analyze_sentiment(self, text: str) -> SentimentAnalysis:
        """Analyze content sentiment"""

        def analyze_sentiment_sync():
            try:
                scores = self._sentiment_analyzer.polarity_scores(text)

                # Calculate confidence based on the strength of sentiment
                confidence = (
                    abs(scores["compound"])
                    if scores["compound"] != 0
                    else scores["neu"]
                )

                return SentimentAnalysis(
                    compound=scores["compound"],
                    positive=scores["pos"],
                    negative=scores["neg"],
                    neutral=scores["neu"],
                    confidence=confidence,
                )

            except Exception as e:
                logger.error(f"Error in sentiment analysis: {str(e)}")
                return SentimentAnalysis()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, analyze_sentiment_sync)

    async def _extract_topics(self, text: str) -> TopicExtraction:
        """Extract topics and keywords from content"""

        def extract_topics_sync():
            try:
                # Tokenize and clean text
                words = word_tokenize(text.lower())
                words = [
                    word
                    for word in words
                    if word.isalnum() and word not in self._stop_words
                ]

                # Simple frequency-based keyword extraction
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1

                # Get top keywords
                sorted_words = sorted(
                    word_freq.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                keywords = [word for word, freq in sorted_words[:15] if freq > 1]

                # Simple topic extraction (could be enhanced with more sophisticated NLP)
                # For now, use most frequent multi-word combinations
                bigrams = []
                for i in range(len(words) - 1):
                    bigram = f"{words[i]} {words[i + 1]}"
                    bigrams.append(bigram)

                bigram_freq = {}
                for bigram in bigrams:
                    bigram_freq[bigram] = bigram_freq.get(bigram, 0) + 1

                topics = [
                    bigram
                    for bigram, freq in sorted(
                        bigram_freq.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5]
                    if freq > 1
                ]

                # Confidence scores (simple heuristic based on frequency)
                confidence_scores = {}
                total_words = len(words)
                for keyword in keywords[:10]:
                    confidence_scores[keyword] = min(
                        1.0,
                        word_freq[keyword] / total_words * 100,
                    )

                return TopicExtraction(
                    primary_topics=topics[:3],
                    secondary_topics=topics[3:],
                    keywords=keywords,
                    entities=[],  # Would need NER model for proper entity extraction
                    confidence_scores=confidence_scores,
                )

            except Exception as e:
                logger.error(f"Error in topic extraction: {str(e)}")
                return TopicExtraction()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_topics_sync)

    async def _generate_embedding(self, text: str) -> ContentEmbedding | None:
        """Generate content embedding vector"""

        def generate_embedding_sync():
            try:
                # Generate embedding
                embedding_vector = self._embedding_model.encode(text)

                return ContentEmbedding(
                    vector=embedding_vector,
                    dimension=len(embedding_vector),
                    model_name=self.embedding_model_name,
                )

            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, generate_embedding_sync)

    async def classify_content_type(
        self,
        content_text: str,
        url: str = "",
    ) -> ContentType:
        """Classify content type based on text and URL analysis"""

        def classify_sync():
            # URL-based classification
            url_lower = url.lower()
            if "arxiv.org" in url_lower or "pubmed" in url_lower:
                return ContentType.PAPER
            if "youtube.com" in url_lower or "video" in url_lower:
                return ContentType.VIDEO
            if "podcast" in url_lower or "audio" in url_lower:
                return ContentType.PODCAST

            # Content-based classification
            word_count = len(word_tokenize(content_text))

            # Look for academic indicators
            academic_indicators = [
                "abstract",
                "methodology",
                "results",
                "conclusion",
                "references",
                "doi:",
                "et al.",
            ]
            academic_score = sum(
                1
                for indicator in academic_indicators
                if indicator in content_text.lower()
            )

            if academic_score >= 3 and word_count > 1000:
                return ContentType.PAPER
            if word_count > 500:
                return ContentType.ARTICLE
            return ContentType.BLOG

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, classify_sync)

    def _create_empty_result(self, content_id: str) -> ContentAnalysisResult:
        """Create empty analysis result for content with no text"""
        return ContentAnalysisResult(
            content_id=content_id,
            quality_metrics=QualityMetrics(),
            sentiment_analysis=SentimentAnalysis(),
            topic_extraction=TopicExtraction(),
            processing_time_ms=0.0,
        )

    def _create_error_result(
        self,
        content_id: str,
        processing_time: float,
    ) -> ContentAnalysisResult:
        """Create error analysis result"""
        return ContentAnalysisResult(
            content_id=content_id,
            quality_metrics=QualityMetrics(),
            sentiment_analysis=SentimentAnalysis(),
            topic_extraction=TopicExtraction(),
            processing_time_ms=processing_time,
        )

    async def batch_analyze(
        self,
        content_items: list[ContentItem],
        max_concurrent: int = 5,
    ) -> list[ContentAnalysisResult]:
        """Analyze multiple content items concurrently"""

        async def analyze_with_semaphore(semaphore, content_item):
            async with semaphore:
                return await self.analyze_content(content_item)

        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [analyze_with_semaphore(semaphore, item) for item in content_items]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error analyzing content {content_items[i].id}: {str(result)}",
                )
                valid_results.append(
                    self._create_error_result(str(content_items[i].id), 0.0),
                )
            else:
                valid_results.append(result)

        return valid_results
