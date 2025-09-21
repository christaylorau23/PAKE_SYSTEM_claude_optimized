#!/usr/bin/env python3
"""PAKE System - Content Summarization Service
Phase 9B: Practical AI/ML Integration

Provides intelligent content summarization and analysis for research results
using lightweight NLP techniques without heavy ML dependencies.
"""

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryResult:
    """Result from content summarization"""

    original_content: str
    extractive_summary: str
    key_points: list[str]
    abstract_summary: str
    content_type: str
    word_count_original: int
    word_count_summary: int
    compression_ratio: float
    confidence_score: float
    processing_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "extractive_summary": self.extractive_summary,
            "key_points": self.key_points,
            "abstract_summary": self.abstract_summary,
            "metadata": {
                "content_type": self.content_type,
                "word_count_original": self.word_count_original,
                "word_count_summary": self.word_count_summary,
                "compression_ratio": self.compression_ratio,
                "confidence_score": self.confidence_score,
                "processing_time_ms": self.processing_time_ms,
                "generated_by": "PAKE Content Summarizer v1.0",
            },
        }


@dataclass
class SummarizationMetrics:
    """Metrics for summarization performance"""

    total_documents: int
    avg_compression_ratio: float
    avg_confidence_score: float
    avg_processing_time_ms: float
    content_types_processed: dict[str, int]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ContentSummarizationService:
    """Advanced content summarization service using lightweight NLP techniques.

    Provides multiple summarization approaches:
    - Extractive summarization (sentence selection)
    - Abstract summarization (key point extraction)
    - Structured summarization for academic papers
    """

    def __init__(self):
        self.processing_history: list[SummarizationMetrics] = []

        # Advanced stop words and transition words
        self.stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
            "my",
            "your",
            "his",
            "its",
            "our",
            "their",
            "from",
            "as",
            "can",
            "may",
            "might",
            "must",
            "also",
            "however",
            "therefore",
            "thus",
            "hence",
            "moreover",
            "furthermore",
        }

        # Important academic and technical keywords
        self.important_terms = {
            "research",
            "study",
            "analysis",
            "method",
            "result",
            "conclusion",
            "finding",
            "evidence",
            "data",
            "experiment",
            "hypothesis",
            "theory",
            "model",
            "algorithm",
            "technique",
            "approach",
            "framework",
            "system",
            "application",
            "implementation",
            "evaluation",
            "performance",
            "accuracy",
            "artificial",
            "intelligence",
            "machine",
            "learning",
            "neural",
            "network",
            "deep",
            "optimization",
            "prediction",
            "classification",
            "regression",
        }

    async def summarize_content(
        self,
        content: str,
        content_type: str = "general",
        target_sentences: int = 3,
        include_key_points: bool = True,
    ) -> SummaryResult:
        """Summarize content using multiple techniques.

        Args:
            content: Text content to summarize
            content_type: Type of content (academic, web, news, etc.)
            target_sentences: Number of sentences for extractive summary
            include_key_points: Whether to extract key points

        Returns:
            SummaryResult with multiple summarization approaches
        """
        start_time = datetime.now()

        if not content or len(content.strip()) < 50:
            return self._create_empty_summary(content, content_type, 0.0)

        # Extract sentences and analyze
        sentences = self._extract_sentences(content)
        if not sentences:
            return self._create_empty_summary(content, content_type, 0.0)

        # Generate extractive summary
        extractive_summary = self._generate_extractive_summary(
            sentences,
            target_sentences,
            content_type,
        )

        # Extract key points if requested
        key_points = []
        if include_key_points:
            key_points = self._extract_key_points(content, sentences)

        # Generate abstract summary
        abstract_summary = self._generate_abstract_summary(
            content,
            sentences,
            key_points,
        )

        # Calculate metrics
        word_count_original = len(content.split())
        word_count_summary = len(extractive_summary.split())
        compression_ratio = (
            word_count_summary / word_count_original if word_count_original > 0 else 0
        )
        confidence_score = self._calculate_confidence_score(
            content,
            extractive_summary,
            sentences,
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return SummaryResult(
            original_content=content,
            extractive_summary=extractive_summary,
            key_points=key_points,
            abstract_summary=abstract_summary,
            content_type=content_type,
            word_count_original=word_count_original,
            word_count_summary=word_count_summary,
            compression_ratio=compression_ratio,
            confidence_score=confidence_score,
            processing_time_ms=processing_time,
        )

    async def summarize_research_results(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Summarize multiple research results with content-aware processing.

        Args:
            results: List of search results to summarize

        Returns:
            Results enhanced with summarization data
        """
        if not results:
            return []

        enhanced_results = []
        processing_metrics = []

        for result in results:
            # Determine content type from source
            content_type = self._determine_content_type(result)

            # Extract content for summarization
            content = self._extract_content_for_summarization(result)

            if content:
                summary_result = await self.summarize_content(
                    content=content,
                    content_type=content_type,
                    target_sentences=2,  # Shorter for result lists
                    include_key_points=True,
                )

                # Add summary to result
                enhanced_result = result.copy()
                enhanced_result["content_summary"] = summary_result.to_dict()
                enhanced_results.append(enhanced_result)

                processing_metrics.append(
                    {
                        "content_type": content_type,
                        "processing_time_ms": summary_result.processing_time_ms,
                        "compression_ratio": summary_result.compression_ratio,
                        "confidence_score": summary_result.confidence_score,
                    },
                )
            else:
                enhanced_results.append(result)

        # Store metrics for analytics
        if processing_metrics:
            self._store_processing_metrics(processing_metrics)

        logger.info(f"Summarized {len(processing_metrics)} research results")
        return enhanced_results

    def _extract_sentences(self, content: str) -> list[str]:
        """Extract and clean sentences from content"""
        # Improved sentence splitting with academic text handling
        sentence_endings = r"[.!?]+(?:\s|$)"
        sentences = re.split(sentence_endings, content)

        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip very short sentences and common patterns
            if (
                len(sentence) > 20
                and not sentence.startswith("http")
                and not sentence.startswith("doi:")
                and sentence.count(" ") > 3
            ):
                clean_sentences.append(sentence)

        return clean_sentences

    def _generate_extractive_summary(
        self,
        sentences: list[str],
        target_sentences: int,
        content_type: str,
    ) -> str:
        """Generate extractive summary by selecting best sentences"""
        if len(sentences) <= target_sentences:
            return ". ".join(sentences) + "."

        # Score sentences based on multiple factors
        sentence_scores = []
        for sentence in sentences:
            score = self._score_sentence(sentence, content_type)
            sentence_scores.append((sentence, score))

        # Sort by score and select top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:target_sentences]]

        # Maintain original order where possible
        ordered_summary = self._maintain_sentence_order(sentences, top_sentences)

        return ". ".join(ordered_summary) + "."

    def _score_sentence(self, sentence: str, content_type: str) -> float:
        """Score sentence for importance using multiple factors"""
        score = 0.0
        words = sentence.lower().split()

        # Length factor (prefer medium-length sentences)
        word_count = len(words)
        if 10 <= word_count <= 25:
            score += 0.2
        elif word_count < 5 or word_count > 40:
            score -= 0.1

        # Important term presence
        important_word_count = sum(1 for word in words if word in self.important_terms)
        score += important_word_count * 0.15

        # Position factor (first and last sentences often important)
        # This would be handled by the calling function

        # Numerical data presence (often important in academic content)
        if re.search(
            r"\d+\.?\d*%|\d+\.?\d*\s*(seconds?|ms|hours?|days?|years?)",
            sentence,
        ):
            score += 0.1

        # Capital words (proper nouns, acronyms)
        capital_words = sum(1 for word in words if word.isupper() and len(word) > 1)
        score += min(capital_words * 0.05, 0.15)

        # Content-type specific scoring
        if content_type == "academic":
            # Academic papers - look for methodology and results
            if any(
                term in sentence.lower()
                for term in ["method", "result", "conclusion", "finding"]
            ):
                score += 0.2
        elif content_type == "web":
            # Web content - look for key information
            if any(
                term in sentence.lower()
                for term in ["key", "important", "main", "primary"]
            ):
                score += 0.15

        return score

    def _maintain_sentence_order(
        self,
        original_sentences: list[str],
        selected_sentences: list[str],
    ) -> list[str]:
        """Maintain original sentence order in summary"""
        ordered_summary = []
        original_indices = {
            sentence: i for i, sentence in enumerate(original_sentences)
        }

        # Sort selected sentences by their original position
        selected_with_indices = [
            (sentence, original_indices.get(sentence, 999))
            for sentence in selected_sentences
        ]
        selected_with_indices.sort(key=lambda x: x[1])

        return [sentence for sentence, _ in selected_with_indices]

    def _extract_key_points(self, content: str, sentences: list[str]) -> list[str]:
        """Extract key points from content"""
        key_points = []

        # Look for bullet points or numbered lists
        bullet_pattern = r"(?:^|\n)\s*[•·\-\*\d+\.]\s+(.+?)(?=\n|$)"
        bullets = re.findall(bullet_pattern, content, re.MULTILINE)
        key_points.extend(
            [bullet.strip() for bullet in bullets if len(bullet.strip()) > 10],
        )

        # Extract sentences with key indicators
        key_indicators = [
            "key",
            "main",
            "important",
            "significant",
            "primary",
            "major",
            "critical",
        ]
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in key_indicators):
                key_points.append(sentence.strip())

        # Remove duplicates while preserving order
        seen = set()
        unique_points = []
        for point in key_points:
            point_hash = hashlib.sha256(point.lower().encode()).hexdigest()
            if point_hash not in seen:
                seen.add(point_hash)
                unique_points.append(point)

        return unique_points[:5]  # Limit to 5 key points

    def _generate_abstract_summary(
        self,
        content: str,
        sentences: list[str],
        key_points: list[str],
    ) -> str:
        """Generate abstract summary combining multiple signals"""
        # Start with the most important information
        summary_parts = []

        # Add topic identification
        main_topics = self._identify_main_topics(content)
        if main_topics:
            topic_text = f"This content focuses on {', '.join(main_topics[:3])}"
            summary_parts.append(topic_text)

        # Add key finding or main point
        if key_points:
            # Use first key point as main finding
            main_finding = key_points[0]
            if len(main_finding) > 100:
                main_finding = main_finding[:100] + "..."
            summary_parts.append(f"Key finding: {main_finding}")
        elif sentences:
            # Use highest scored sentence
            best_sentence = max(
                sentences,
                key=lambda s: self._score_sentence(s, "general"),
            )
            if len(best_sentence) > 100:
                best_sentence = best_sentence[:100] + "..."
            summary_parts.append(best_sentence)

        return ". ".join(summary_parts) + "."

    def _identify_main_topics(self, content: str) -> list[str]:
        """Identify main topics in content using keyword frequency"""
        words = re.findall(r"\b[a-zA-Z]+\b", content.lower())

        # Filter meaningful words
        meaningful_words = [
            word
            for word in words
            if (len(word) >= 4 and word not in self.stop_words and not word.isdigit())
        ]

        # Count frequencies
        word_counts = Counter(meaningful_words)

        # Boost important terms
        for word in meaningful_words:
            if word in self.important_terms:
                word_counts[word] = word_counts.get(word, 0) * 2

        # Return top topics
        return [word for word, _ in word_counts.most_common(8)]

    def _determine_content_type(self, result: dict[str, Any]) -> str:
        """Determine content type from result metadata"""
        source_type = result.get("source_type", "").lower()

        if "arxiv" in source_type:
            return "academic"
        if "pubmed" in source_type:
            return "medical"
        if "firecrawl" in source_type or "web" in source_type:
            return "web"
        return "general"

    def _extract_content_for_summarization(self, result: dict[str, Any]) -> str:
        """Extract the best content for summarization from result"""
        content_parts = []

        # Add title if available
        if result.get("title"):
            content_parts.append(result["title"])

        # Add main content
        for field in ["content", "abstract", "description", "summary"]:
            if field in result and result[field]:
                content_parts.append(str(result[field]))

        return " ".join(content_parts).strip()

    def _calculate_confidence_score(
        self,
        original: str,
        summary: str,
        sentences: list[str],
    ) -> float:
        """Calculate confidence score for the summary"""
        if not summary or not original:
            return 0.0

        score = 0.5  # Base score

        # Check coverage of important terms
        original_words = set(original.lower().split())
        summary_words = set(summary.lower().split())

        important_original = original_words.intersection(self.important_terms)
        important_summary = summary_words.intersection(self.important_terms)

        if important_original:
            coverage = len(important_summary) / len(important_original)
            score += coverage * 0.3

        # Check sentence quality
        summary_sentences = self._extract_sentences(summary)
        if summary_sentences:
            avg_sentence_quality = sum(
                self._score_sentence(s, "general") for s in summary_sentences
            ) / len(summary_sentences)
            score += min(avg_sentence_quality, 0.2)

        return min(1.0, score)

    def _create_empty_summary(
        self,
        content: str,
        content_type: str,
        processing_time_ms: float,
    ) -> SummaryResult:
        """Create empty summary result for invalid content"""
        return SummaryResult(
            original_content=content,
            extractive_summary="Content too short or empty for summarization.",
            key_points=[],
            abstract_summary="No meaningful content found for analysis.",
            content_type=content_type,
            word_count_original=len(content.split()) if content else 0,
            word_count_summary=0,
            compression_ratio=0.0,
            confidence_score=0.0,
            processing_time_ms=processing_time_ms,
        )

    def _store_processing_metrics(self, metrics: list[dict[str, Any]]) -> None:
        """Store processing metrics for analytics"""
        if not metrics:
            return

        content_types = Counter(m["content_type"] for m in metrics)
        avg_compression = sum(m["compression_ratio"] for m in metrics) / len(metrics)
        avg_confidence = sum(m["confidence_score"] for m in metrics) / len(metrics)
        avg_processing_time = sum(m["processing_time_ms"] for m in metrics) / len(
            metrics,
        )

        summary_metrics = SummarizationMetrics(
            total_documents=len(metrics),
            avg_compression_ratio=avg_compression,
            avg_confidence_score=avg_confidence,
            avg_processing_time_ms=avg_processing_time,
            content_types_processed=dict(content_types),
        )

        self.processing_history.append(summary_metrics)
        if len(self.processing_history) > 50:  # Keep last 50 metrics
            self.processing_history = self.processing_history[-50:]

    def get_summarization_analytics(self) -> dict[str, Any]:
        """Get analytics from summarization history"""
        if not self.processing_history:
            return {"message": "No summarization history available"}

        recent_metrics = self.processing_history[-10:]  # Last 10 batches

        total_docs = sum(m.total_documents for m in recent_metrics)
        avg_compression = (
            sum(m.avg_compression_ratio * m.total_documents for m in recent_metrics)
            / total_docs
            if total_docs > 0
            else 0
        )
        avg_confidence = (
            sum(m.avg_confidence_score * m.total_documents for m in recent_metrics)
            / total_docs
            if total_docs > 0
            else 0
        )
        avg_processing_time = (
            sum(m.avg_processing_time_ms * m.total_documents for m in recent_metrics)
            / total_docs
            if total_docs > 0
            else 0
        )

        # Aggregate content types
        all_content_types = Counter()
        for m in recent_metrics:
            all_content_types.update(m.content_types_processed)

        return {
            "summarization_statistics": {
                "total_documents_processed": total_docs,
                "avg_compression_ratio": round(avg_compression, 3),
                "avg_confidence_score": round(avg_confidence, 3),
                "avg_processing_time_ms": round(avg_processing_time, 1),
            },
            "content_types_distribution": dict(all_content_types.most_common()),
            "processing_history_batches": len(self.processing_history),
        }


# Global instance for reuse
_summarization_service = None


def get_content_summarization_service() -> ContentSummarizationService:
    """Get or create global content summarization service instance"""
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = ContentSummarizationService()
    return _summarization_service


async def main():
    """Demo of content summarization service"""
    service = get_content_summarization_service()

    # Test with sample academic content
    academic_content = """
    Artificial Intelligence in Medical Diagnosis: A Comprehensive Review

    This paper presents a systematic review of artificial intelligence applications in medical diagnosis,
    focusing on machine learning and deep learning approaches. We analyzed 150 studies published between
    2020-2023 to evaluate the effectiveness of AI-driven diagnostic systems.

    Our methodology involved a comprehensive literature search across PubMed, IEEE Xplore, and ACM Digital
    Library. Studies were selected based on specific inclusion criteria including peer-review status,
    clinical validation, and statistical significance of results.

    Key findings indicate that AI systems achieved an average accuracy of 87.3% across different medical
    specialties. Radiology applications showed the highest performance with 92.1% accuracy, followed by
    pathology at 89.4% and dermatology at 85.7%. The study also identified significant challenges including
    data privacy concerns, regulatory approval processes, and integration with existing clinical workflows.

    Our results demonstrate that AI has substantial potential to improve diagnostic accuracy and efficiency
    in healthcare settings. However, successful implementation requires careful consideration of ethical
    implications, regulatory compliance, and healthcare provider training. Future research should focus on
    developing explainable AI systems and addressing bias in medical datasets.

    The implications of this research suggest that healthcare institutions should begin strategic planning
    for AI integration while maintaining focus on patient safety and care quality. Collaboration between
    technologists, clinicians, and policymakers will be essential for realizing the full potential of AI
    in medical diagnosis.
    """

    print("Testing Content Summarization Service")
    print("=" * 50)

    summary_result = await service.summarize_content(
        content=academic_content,
        content_type="academic",
        target_sentences=3,
        include_key_points=True,
    )

    print(f"Original length: {summary_result.word_count_original} words")
    print(f"Summary length: {summary_result.word_count_summary} words")
    print(f"Compression ratio: {summary_result.compression_ratio:.2f}")
    print(f"Confidence score: {summary_result.confidence_score:.2f}")
    print(f"Processing time: {summary_result.processing_time_ms:.1f}ms")
    print()

    print("Extractive Summary:")
    print(summary_result.extractive_summary)
    print()

    print("Key Points:")
    for i, point in enumerate(summary_result.key_points, 1):
        print(f"{i}. {point}")
    print()

    print("Abstract Summary:")
    print(summary_result.abstract_summary)
    print()

    # Test with multiple results
    sample_results = [
        {
            "title": "Deep Learning for Image Classification",
            "content": "This study explores convolutional neural networks for image classification tasks. The research demonstrates significant improvements in accuracy through advanced architectural designs and training methodologies.",
            "source_type": "arxiv_enhanced",
        },
        {
            "title": "Web Development Best Practices",
            "content": "A comprehensive guide to modern web development covering frontend frameworks, backend architectures, and deployment strategies. The article provides practical examples and performance optimization techniques.",
            "source_type": "firecrawl_web",
        },
    ]

    print("\nTesting Research Results Summarization:")
    print("=" * 50)

    enhanced_results = await service.summarize_research_results(sample_results)

    for i, result in enumerate(enhanced_results, 1):
        print(f"\nResult {i}: {result['title']}")
        if "content_summary" in result:
            summary = result["content_summary"]
            print(f"Summary: {summary['extractive_summary']}")
            print(f"Compression: {summary['metadata']['compression_ratio']:.2f}")
            print(f"Confidence: {summary['metadata']['confidence_score']:.2f}")

    # Show analytics
    analytics = service.get_summarization_analytics()
    print("\nSummarization Analytics:")
    print(json.dumps(analytics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
