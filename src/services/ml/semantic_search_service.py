#!/usr/bin/env python3
"""PAKE System - Semantic Search Enhancement Service
Phase 9B: Practical AI/ML Integration

Enhances search results with semantic similarity, content summarization,
and intelligent ranking without heavy ML dependencies.
"""

import asyncio
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchEnhancement:
    """Enhanced search result with ML insights"""

    original_result: dict[str, Any]
    semantic_score: float
    content_summary: str
    key_topics: list[str]
    similarity_explanation: str
    relevance_score: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            **self.original_result,
            "ml_enhancements": {
                "semantic_score": self.semantic_score,
                "content_summary": self.content_summary,
                "key_topics": self.key_topics,
                "similarity_explanation": self.similarity_explanation,
                "relevance_score": self.relevance_score,
                "enhanced_by": "PAKE Semantic Search v1.0",
            },
        }


@dataclass
class SearchAnalytics:
    """Analytics and insights from search patterns"""

    query: str
    total_results: int
    avg_semantic_score: float
    top_topics: list[str]
    search_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    processing_time_ms: float = 0.0


class SemanticSearchService:
    """Practical semantic search enhancement without heavy ML dependencies.
    Focuses on text analysis, keyword extraction, and intelligent ranking.
    """

    def __init__(self):
        self.search_history: list[SearchAnalytics] = []

        # Common stop words for better keyword extraction
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
        }

    async def enhance_search_results(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> tuple[list[SearchEnhancement], SearchAnalytics]:
        """Enhance search results with semantic analysis and ranking.

        Args:
            query: Original search query
            results: Search results from the orchestrator

        Returns:
            Tuple of enhanced results and analytics
        """
        start_time = datetime.now()

        if not results:
            analytics = SearchAnalytics(
                query=query,
                total_results=0,
                avg_semantic_score=0.0,
                top_topics=[],
                processing_time_ms=0.0,
            )
            return [], analytics

        # Extract query keywords for semantic matching
        query_keywords = self._extract_keywords(query)

        enhanced_results = []
        semantic_scores = []
        all_topics = []

        for result in results:
            enhancement = await self._enhance_single_result(
                result,
                query,
                query_keywords,
            )
            enhanced_results.append(enhancement)
            semantic_scores.append(enhancement.semantic_score)
            all_topics.extend(enhancement.key_topics)

        # Sort by relevance score (combination of semantic and other factors)
        enhanced_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Generate analytics
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        topic_counter = Counter(all_topics)

        analytics = SearchAnalytics(
            query=query,
            total_results=len(enhanced_results),
            avg_semantic_score=(
                sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0
            ),
            top_topics=[topic for topic, _ in topic_counter.most_common(10)],
            processing_time_ms=processing_time,
        )

        # Store analytics for insights
        self.search_history.append(analytics)
        if len(self.search_history) > 100:  # Keep last 100 searches
            self.search_history = self.search_history[-100:]

        logger.info(
            f"Enhanced {len(enhanced_results)} search results for query '{query}' in {processing_time:.1f}ms",
        )

        return enhanced_results, analytics

    async def _enhance_single_result(
        self,
        result: dict[str, Any],
        query: str,
        query_keywords: list[str],
    ) -> SearchEnhancement:
        """Enhance a single search result with ML insights"""
        # Extract content for analysis
        content = self._extract_content_text(result)
        title = result.get("title", "")

        # Calculate semantic similarity (simplified TF-IDF approach)
        semantic_score = self._calculate_semantic_similarity(
            query_keywords,
            content + " " + title,
        )

        # Generate content summary
        summary = self._generate_summary(content, max_sentences=2)

        # Extract key topics
        key_topics = self._extract_topics(content + " " + title)

        # Generate similarity explanation
        similarity_explanation = self._generate_similarity_explanation(
            query_keywords,
            content,
            semantic_score,
        )

        # Calculate final relevance score (combines multiple factors)
        relevance_score = self._calculate_relevance_score(
            result,
            semantic_score,
            query_keywords,
            content,
            title,
        )

        return SearchEnhancement(
            original_result=result,
            semantic_score=semantic_score,
            content_summary=summary,
            key_topics=key_topics,
            similarity_explanation=similarity_explanation,
            relevance_score=relevance_score,
        )

    def _extract_content_text(self, result: dict[str, Any]) -> str:
        """Extract text content from search result"""
        content_parts = []

        # Common content fields
        for field in ["content", "abstract", "description", "summary", "text"]:
            if field in result and result[field]:
                content_parts.append(str(result[field]))

        return " ".join(content_parts).strip()

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return []

        # Convert to lowercase and extract words
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

        # Filter out stop words and short words
        keywords = [
            word for word in words if len(word) >= 3 and word not in self.stop_words
        ]

        # Return unique keywords, keeping order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)

        return unique_keywords[:20]  # Limit to top 20 keywords

    def _calculate_semantic_similarity(
        self,
        query_keywords: list[str],
        content: str,
    ) -> float:
        """Calculate semantic similarity using simplified TF-IDF approach"""
        if not query_keywords or not content:
            return 0.0

        content_words = self._extract_keywords(content)
        content_word_count = Counter(content_words)
        total_content_words = len(content_words)

        if total_content_words == 0:
            return 0.0

        # Calculate TF-IDF style score
        similarity_score = 0.0
        matched_keywords = 0

        for keyword in query_keywords:
            if keyword in content_word_count:
                matched_keywords += 1
                tf = content_word_count[keyword] / total_content_words
                # Simplified IDF (inverse document frequency)
                idf = math.log(1 + total_content_words / content_word_count[keyword])
                similarity_score += tf * idf

        # Normalize by query length and add bonus for keyword coverage
        normalized_score = similarity_score / len(query_keywords)
        coverage_bonus = matched_keywords / len(query_keywords) * 0.5

        return min(1.0, normalized_score + coverage_bonus)

    def _generate_summary(self, content: str, max_sentences: int = 2) -> str:
        """Generate a simple extractive summary"""
        if not content:
            return "No content available for summary."

        # Split into sentences
        sentences = re.split(r"[.!?]+", content.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if not sentences:
            return "Content too short for summary."

        if len(sentences) <= max_sentences:
            return ". ".join(sentences) + "."

        # Simple ranking: prefer longer sentences with more keywords
        sentence_scores = []
        for sentence in sentences:
            keywords = self._extract_keywords(sentence)
            score = len(keywords) * len(sentence)  # Simple scoring
            sentence_scores.append((sentence, score))

        # Sort by score and take top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:max_sentences]]

        return ". ".join(top_sentences) + "."

    def _extract_topics(self, text: str) -> list[str]:
        """Extract key topics from text"""
        keywords = self._extract_keywords(text)
        keyword_counts = Counter(keywords)

        # Return top keywords as topics, with minimum frequency
        topics = [
            keyword
            for keyword, count in keyword_counts.most_common(10)
            if count >= 2
            or keyword
            in [
                "artificial",
                "intelligence",
                "machine",
                "learning",
                "research",
                "analysis",
                "system",
                "data",
                "technology",
            ]
        ]

        return topics[:8]  # Limit to 8 topics

    def _generate_similarity_explanation(
        self,
        query_keywords: list[str],
        content: str,
        similarity_score: float,
    ) -> str:
        """Generate human-readable explanation of similarity"""
        content_keywords = self._extract_keywords(content)
        matched = [kw for kw in query_keywords if kw in content_keywords]

        if not matched:
            return "No direct keyword matches found in content."

        match_pct = (len(matched) / len(query_keywords)) * 100

        if similarity_score > 0.7:
            level = "High"
        elif similarity_score > 0.4:
            level = "Moderate"
        else:
            level = "Low"

        return (
            f"{level} relevance ({match_pct:.0f}% keyword match). "
            f"Matched terms: {', '.join(matched[:5])}"
        )

    def _calculate_relevance_score(
        self,
        result: dict[str, Any],
        semantic_score: float,
        query_keywords: list[str],
        content: str,
        title: str,
    ) -> float:
        """Calculate final relevance score combining multiple factors"""
        # Base semantic score
        relevance = semantic_score * 0.6

        # Title relevance bonus
        title_keywords = self._extract_keywords(title)
        title_matches = len([kw for kw in query_keywords if kw in title_keywords])
        if title_matches > 0:
            relevance += (title_matches / len(query_keywords)) * 0.2

        # Content length factor (prefer substantial content)
        content_length = len(content.split())
        if content_length > 100:
            relevance += 0.1
        elif content_length < 20:
            relevance -= 0.1

        # Source credibility (based on source type)
        source_type = result.get("source_type", "").lower()
        if "arxiv" in source_type:
            relevance += 0.05  # Academic bonus
        elif "pubmed" in source_type:
            relevance += 0.05  # Medical research bonus

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, relevance))

    def get_search_insights(self) -> dict[str, Any]:
        """Get insights from recent search history"""
        if not self.search_history:
            return {"message": "No search history available"}

        recent_searches = self.search_history[-20:]  # Last 20 searches

        # Aggregate statistics
        avg_results = sum(s.total_results for s in recent_searches) / len(
            recent_searches,
        )
        avg_semantic_score = sum(s.avg_semantic_score for s in recent_searches) / len(
            recent_searches,
        )
        avg_processing_time = sum(s.processing_time_ms for s in recent_searches) / len(
            recent_searches,
        )

        # Top topics across all searches
        all_topics = []
        for search in recent_searches:
            all_topics.extend(search.top_topics)
        top_topics = [topic for topic, _ in Counter(all_topics).most_common(10)]

        # Recent queries
        recent_queries = [s.query for s in recent_searches[-5:]]

        return {
            "search_statistics": {
                "total_searches": len(self.search_history),
                "recent_searches": len(recent_searches),
                "avg_results_per_search": round(avg_results, 1),
                "avg_semantic_score": round(avg_semantic_score, 3),
                "avg_processing_time_ms": round(avg_processing_time, 1),
            },
            "trending_topics": top_topics,
            "recent_queries": recent_queries,
        }


# Create global instance for reuse
_semantic_service = None


def get_semantic_search_service() -> SemanticSearchService:
    """Get or create global semantic search service instance"""
    global _semantic_service
    if _semantic_service is None:
        _semantic_service = SemanticSearchService()
    return _semantic_service


async def main():
    """Demo of semantic search enhancement"""
    service = get_semantic_search_service()

    # Sample search results (simulating orchestrator output)
    sample_results = [
        {
            "title": "Machine Learning Applications in Healthcare",
            "content": "This paper explores the use of artificial intelligence and machine learning techniques in medical diagnosis and treatment optimization.",
            "source_type": "arxiv_enhanced",
            "url": "https://arxiv.org/abs/example1",
        },
        {
            "title": "Database Systems and Performance",
            "content": "A study of relational database performance optimization techniques and indexing strategies.",
            "source_type": "web_scraping",
            "url": "https://example.com/databases",
        },
        {
            "title": "AI in Medical Imaging",
            "content": "Advanced machine learning algorithms for medical image analysis and diagnostic assistance using deep neural networks.",
            "source_type": "pubmed_research",
            "url": "https://pubmed.ncbi.nlm.nih.gov/example",
        },
    ]

    query = "machine learning healthcare applications"

    enhanced_results, analytics = await service.enhance_search_results(
        query,
        sample_results,
    )

    print(f"Enhanced Search Results for: '{query}'")
    print("=" * 60)

    for i, result in enumerate(enhanced_results, 1):
        print(f"\n{i}. {result.original_result['title']}")
        print(f"   Relevance Score: {result.relevance_score:.3f}")
        print(f"   Semantic Score: {result.semantic_score:.3f}")
        print(f"   Summary: {result.content_summary}")
        print(f"   Key Topics: {', '.join(result.key_topics)}")
        print(f"   Similarity: {result.similarity_explanation}")

    print("\nSearch Analytics:")
    print(f"Total Results: {analytics.total_results}")
    print(f"Avg Semantic Score: {analytics.avg_semantic_score:.3f}")
    print(f"Processing Time: {analytics.processing_time_ms:.1f}ms")
    print(f"Top Topics: {', '.join(analytics.top_topics)}")

    # Show insights after multiple searches
    insights = service.get_search_insights()
    print("\nSearch Insights:")
    print(json.dumps(insights, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
