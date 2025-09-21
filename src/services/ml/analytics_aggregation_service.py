#!/usr/bin/env python3
"""PAKE System - ML Analytics Aggregation Service
Phase 10A: ML Intelligence Dashboard

Advanced analytics service that aggregates and processes ML insights
from semantic search and content summarization for intelligent dashboards.
"""

import asyncio
import hashlib
import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

# Import services - handle both relative and absolute imports
try:
    from .content_summarization_service import get_content_summarization_service
    from .knowledge_graph_service import get_knowledge_graph_service
    from .semantic_search_service import get_semantic_search_service
except ImportError:
    # Fallback for direct execution
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from knowledge_graph_service import get_knowledge_graph_service

logger = logging.getLogger(__name__)


@dataclass
class SearchSession:
    """Represents a research session with multiple queries"""

    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    queries: list[str] = field(default_factory=list)
    total_results: int = 0
    avg_semantic_score: float = 0.0
    dominant_topics: list[str] = field(default_factory=list)
    content_types_explored: dict[str, int] = field(default_factory=dict)
    session_duration_minutes: float = 0.0


@dataclass
class ResearchPattern:
    """Identified research patterns and insights"""

    pattern_type: str  # 'topic_cluster', 'time_pattern', 'source_preference'
    pattern_name: str
    frequency: int
    confidence: float
    last_seen: datetime
    related_queries: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)


@dataclass
class KnowledgeInsight:
    """Knowledge insights and recommendations"""

    insight_type: str  # 'research_gap', 'trending_topic', 'deep_dive', 'related_area'
    title: str
    description: str
    confidence: float
    actionable_suggestions: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high


@dataclass
class DashboardMetrics:
    """Real-time dashboard metrics"""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Search Performance
    total_searches_today: int = 0
    avg_response_time_ms: float = 0.0
    success_rate: float = 100.0

    # Content Analysis
    total_content_analyzed: int = 0
    avg_compression_ratio: float = 0.0
    avg_confidence_score: float = 0.0

    # Research Intelligence
    active_research_sessions: int = 0
    trending_topics: list[tuple[str, int]] = field(default_factory=list)
    knowledge_gaps: list[str] = field(default_factory=list)

    # User Insights
    research_productivity_score: float = 0.0
    exploration_diversity: float = 0.0
    focus_areas: list[str] = field(default_factory=list)


class MLAnalyticsAggregationService:
    """Advanced ML analytics aggregation service for intelligent dashboard insights.

    Processes and analyzes data from semantic search and content summarization
    to provide actionable research intelligence and recommendations.
    """

    def __init__(self):
        # Core data storage
        self.search_history: list[dict[str, Any]] = []
        self.research_sessions: dict[str, SearchSession] = {}
        self.identified_patterns: list[ResearchPattern] = []
        self.knowledge_insights: list[KnowledgeInsight] = []

        # Analytics cache
        self.analytics_cache: dict[str, Any] = {}
        self.cache_expiry: dict[str, datetime] = {}

        # Configuration
        self.session_timeout_minutes = 30
        self.max_history_days = 30
        self.pattern_min_frequency = 3

        logger.info("ML Analytics Aggregation Service initialized")

    async def record_search_event(
        self,
        query: str,
        results_count: int,
        semantic_analytics: dict[str, Any] | None = None,
        summarization_analytics: dict[str, Any] | None = None,
        execution_time_ms: float = 0.0,
        sources_used: list[str] | None = None,
    ) -> str:
        """Record a search event for analytics processing.

        Returns:
            session_id: Current or new session ID
        """
        timestamp = datetime.now(UTC)

        # Create search event record
        search_event = {
            "timestamp": timestamp,
            "query": query,
            "results_count": results_count,
            "execution_time_ms": execution_time_ms,
            "sources_used": sources_used or [],
            "semantic_analytics": semantic_analytics or {},
            "summarization_analytics": summarization_analytics or {},
            "session_id": None,  # Will be set by session management
        }

        # Manage research sessions
        session_id = await self._manage_research_session(query, timestamp, search_event)
        search_event["session_id"] = session_id

        # Add to history
        self.search_history.append(search_event)

        # Trim old history
        cutoff_time = timestamp - timedelta(days=self.max_history_days)
        self.search_history = [
            event for event in self.search_history if event["timestamp"] > cutoff_time
        ]

        # Invalidate relevant caches
        self._invalidate_cache(["dashboard_metrics", "research_patterns"])

        logger.info(
            f"Recorded search event for query '{query}' in session {session_id}",
        )
        return session_id

    async def _manage_research_session(
        self,
        query: str,
        timestamp: datetime,
        search_event: dict[str, Any],
    ) -> str:
        """Manage research sessions and detect session boundaries"""
        # Find active session (within timeout window)
        active_session_id = None
        timeout_threshold = timestamp - timedelta(minutes=self.session_timeout_minutes)

        for session_id, session in self.research_sessions.items():
            if session.end_time is None and session.start_time > timeout_threshold:
                active_session_id = session_id
                break

        if active_session_id:
            # Continue existing session
            session = self.research_sessions[active_session_id]
            session.queries.append(query)
            session.total_results += search_event["results_count"]

            # Update session analytics
            if search_event["semantic_analytics"]:
                sem_score = search_event["semantic_analytics"].get(
                    "avg_semantic_score",
                    0,
                )
                current_avg = session.avg_semantic_score
                query_count = len(session.queries)
                session.avg_semantic_score = (
                    current_avg * (query_count - 1) + sem_score
                ) / query_count

                # Update dominant topics
                new_topics = search_event["semantic_analytics"].get("top_topics", [])
                all_topics = session.dominant_topics + new_topics
                topic_counts = Counter(all_topics)
                session.dominant_topics = [
                    topic for topic, _ in topic_counts.most_common(5)
                ]

            return active_session_id
        # Start new session
        session_id = hashlib.sha256(f"{timestamp}{query}".encode()).hexdigest()[:12]

        new_session = SearchSession(
            session_id=session_id,
            start_time=timestamp,
            queries=[query],
            total_results=search_event["results_count"],
        )

        # Initialize analytics
        if search_event["semantic_analytics"]:
            new_session.avg_semantic_score = search_event["semantic_analytics"].get(
                "avg_semantic_score",
                0,
            )
            new_session.dominant_topics = search_event["semantic_analytics"].get(
                "top_topics",
                [],
            )[:5]

        self.research_sessions[session_id] = new_session

        # Close old sessions
        for session in self.research_sessions.values():
            if session.end_time is None and session.start_time <= timeout_threshold:
                session.end_time = timestamp
                session.session_duration_minutes = (
                    timestamp - session.start_time
                ).total_seconds() / 60

        return session_id

    async def generate_dashboard_metrics(self) -> DashboardMetrics:
        """Generate real-time dashboard metrics"""
        cache_key = "dashboard_metrics"
        if self._is_cache_valid(cache_key):
            return DashboardMetrics(**self.analytics_cache[cache_key])

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Filter today's events
        today_events = [
            event for event in self.search_history if event["timestamp"] >= today_start
        ]

        # Calculate search performance metrics
        total_searches = len(today_events)
        avg_response_time = (
            statistics.mean([e["execution_time_ms"] for e in today_events])
            if today_events
            else 0
        )
        success_rate = 100.0  # Assuming all logged searches were successful

        # Content analysis metrics
        content_events = [e for e in today_events if e.get("summarization_analytics")]
        total_content_analyzed = sum(
            e["summarization_analytics"].get("total_documents_processed", 0)
            for e in content_events
        )

        avg_compression = (
            statistics.mean(
                [
                    e["summarization_analytics"].get("avg_compression_ratio", 0)
                    for e in content_events
                ],
            )
            if content_events
            else 0
        )

        avg_confidence = (
            statistics.mean(
                [
                    e["summarization_analytics"].get("avg_confidence_score", 0)
                    for e in content_events
                ],
            )
            if content_events
            else 0
        )

        # Research intelligence metrics
        active_sessions = len(
            [s for s in self.research_sessions.values() if s.end_time is None],
        )

        # Trending topics (from recent searches)
        recent_events = today_events[-20:] if len(today_events) > 20 else today_events
        all_topics = []
        for event in recent_events:
            if event.get("semantic_analytics", {}).get("top_topics"):
                all_topics.extend(event["semantic_analytics"]["top_topics"])

        trending_topics = Counter(all_topics).most_common(10)

        # Research productivity and focus analysis
        productivity_score = await self._calculate_productivity_score(today_events)
        exploration_diversity = await self._calculate_exploration_diversity(
            today_events,
        )
        focus_areas = await self._identify_focus_areas(today_events)

        # Knowledge gaps (topics with low confidence scores)
        knowledge_gaps = await self._identify_knowledge_gaps(recent_events)

        metrics = DashboardMetrics(
            timestamp=now,
            total_searches_today=total_searches,
            avg_response_time_ms=round(avg_response_time, 1),
            success_rate=success_rate,
            total_content_analyzed=total_content_analyzed,
            avg_compression_ratio=round(avg_compression, 3),
            avg_confidence_score=round(avg_confidence, 3),
            active_research_sessions=active_sessions,
            trending_topics=trending_topics,
            knowledge_gaps=knowledge_gaps,
            research_productivity_score=productivity_score,
            exploration_diversity=exploration_diversity,
            focus_areas=focus_areas,
        )

        # Cache results
        self.analytics_cache[cache_key] = metrics.__dict__
        self.cache_expiry[cache_key] = now + timedelta(minutes=5)  # 5-minute cache

        return metrics

    async def _calculate_productivity_score(
        self,
        events: list[dict[str, Any]],
    ) -> float:
        """Calculate research productivity score based on search patterns"""
        if not events:
            return 0.0

        factors = []

        # Search frequency (more searches = higher engagement)
        search_count = len(events)
        frequency_score = min(search_count / 10, 1.0)  # Normalize to max 10 searches
        factors.append(frequency_score)

        # Query quality (longer, more specific queries)
        avg_query_length = statistics.mean([len(e["query"].split()) for e in events])
        quality_score = min(avg_query_length / 5, 1.0)  # Normalize to max 5 words
        factors.append(quality_score)

        # Semantic relevance (higher semantic scores = better matches)
        semantic_scores = [
            e.get("semantic_analytics", {}).get("avg_semantic_score", 0) for e in events
        ]
        if semantic_scores:
            relevance_score = statistics.mean(semantic_scores)
            factors.append(relevance_score)

        # Session depth (longer sessions = more focused research)
        sessions = set(e.get("session_id") for e in events if e.get("session_id"))
        if sessions:
            avg_session_queries = len(events) / len(sessions)
            # Normalize to max 5 queries per session
            depth_score = min(avg_session_queries / 5, 1.0)
            factors.append(depth_score)

        return round(statistics.mean(factors), 3)

    async def _calculate_exploration_diversity(
        self,
        events: list[dict[str, Any]],
    ) -> float:
        """Calculate exploration diversity based on topic spread"""
        if not events:
            return 0.0

        all_topics = set()
        for event in events:
            if event.get("semantic_analytics", {}).get("top_topics"):
                all_topics.update(event["semantic_analytics"]["top_topics"])

        # Diversity based on unique topics explored
        unique_topics = len(all_topics)
        max_expected_topics = len(events) * 2  # Reasonable expectation

        diversity_score = min(unique_topics / max_expected_topics, 1.0)
        return round(diversity_score, 3)

    async def _identify_focus_areas(self, events: list[dict[str, Any]]) -> list[str]:
        """Identify main focus areas from search patterns"""
        topic_frequency = Counter()

        for event in events:
            if event.get("semantic_analytics", {}).get("top_topics"):
                for topic in event["semantic_analytics"]["top_topics"]:
                    topic_frequency[topic] += 1

        # Return topics that appear in at least 20% of searches
        min_frequency = max(1, len(events) * 0.2)
        focus_areas = [
            topic for topic, freq in topic_frequency.items() if freq >= min_frequency
        ]

        return focus_areas[:8]  # Limit to top 8 focus areas

    async def _identify_knowledge_gaps(self, events: list[dict[str, Any]]) -> list[str]:
        """Identify potential knowledge gaps based on low-confidence searches"""
        gap_indicators = []

        for event in events:
            semantic_score = event.get("semantic_analytics", {}).get(
                "avg_semantic_score",
                1.0,
            )
            confidence_score = event.get("summarization_analytics", {}).get(
                "avg_confidence_score",
                1.0,
            )

            # Consider low confidence or low semantic relevance as potential gaps
            if semantic_score < 0.4 or confidence_score < 0.6:
                query_topics = event["query"].lower().split()
                gap_indicators.extend(
                    [
                        topic
                        for topic in query_topics
                        if len(topic) > 3 and topic not in {"the", "and", "for", "with"}
                    ],
                )

        # Return most common gap indicators
        gap_frequency = Counter(gap_indicators)
        return [topic for topic, _ in gap_frequency.most_common(5)]

    async def identify_research_patterns(self) -> list[ResearchPattern]:
        """Identify recurring research patterns and insights"""
        cache_key = "research_patterns"
        if self._is_cache_valid(cache_key):
            return [ResearchPattern(**p) for p in self.analytics_cache[cache_key]]

        patterns = []

        # Topic clustering patterns
        topic_patterns = await self._identify_topic_clusters()
        patterns.extend(topic_patterns)

        # Time-based patterns
        time_patterns = await self._identify_time_patterns()
        patterns.extend(time_patterns)

        # Source preference patterns
        source_patterns = await self._identify_source_preferences()
        patterns.extend(source_patterns)

        # Cache results
        self.analytics_cache[cache_key] = [p.__dict__ for p in patterns]
        self.cache_expiry[cache_key] = datetime.now(UTC) + timedelta(hours=2)

        self.identified_patterns = patterns
        return patterns

    async def _identify_topic_clusters(self) -> list[ResearchPattern]:
        """Identify clusters of related research topics"""
        topic_co_occurrence = defaultdict(Counter)
        topic_queries = defaultdict(list)

        # Track topic co-occurrence within sessions
        for session in self.research_sessions.values():
            session_topics = session.dominant_topics
            for i, topic1 in enumerate(session_topics):
                topic_queries[topic1].extend(session.queries)
                for topic2 in session_topics[i + 1 :]:
                    topic_co_occurrence[topic1][topic2] += 1
                    topic_co_occurrence[topic2][topic1] += 1

        patterns = []
        processed_clusters = set()

        for topic, related_topics in topic_co_occurrence.items():
            if topic in processed_clusters:
                continue

            # Find significant co-occurrences
            significant_related = [
                (related, count)
                for related, count in related_topics.most_common(3)
                if count >= self.pattern_min_frequency
            ]

            if significant_related:
                cluster_topics = [topic] + [t[0] for t in significant_related]
                processed_clusters.update(cluster_topics)

                pattern = ResearchPattern(
                    pattern_type="topic_cluster",
                    pattern_name=f"Research cluster: {topic} ecosystem",
                    frequency=sum(count for _, count in significant_related),
                    # More related topics = higher confidence
                    confidence=min(1.0, len(significant_related) / 3),
                    last_seen=datetime.now(UTC),
                    related_queries=list(set(topic_queries[topic]))[:5],
                    insights=[
                        f"Frequently research {topic} alongside {', '.join([t[0] for t in significant_related])}",
                        f"This suggests a systematic approach to understanding the {topic} domain",
                    ],
                )
                patterns.append(pattern)

        return patterns

    async def _identify_time_patterns(self) -> list[ResearchPattern]:
        """Identify time-based research patterns"""
        if not self.search_history:
            return []

        # Group searches by hour of day
        hour_distribution = Counter()
        for event in self.search_history:
            hour = event["timestamp"].hour
            hour_distribution[hour] += 1

        patterns = []

        # Identify peak research hours
        if len(hour_distribution) >= 3:
            total_searches = sum(hour_distribution.values())
            avg_per_hour = total_searches / 24

            peak_hours = [
                hour
                for hour, count in hour_distribution.items()
                if count > avg_per_hour * 1.5  # 50% above average
            ]

            if peak_hours:
                pattern = ResearchPattern(
                    pattern_type="time_pattern",
                    pattern_name="Peak research hours identified",
                    frequency=sum(hour_distribution[h] for h in peak_hours),
                    confidence=0.8,
                    last_seen=datetime.now(UTC),
                    insights=[
                        f"Most active research hours: {', '.join(map(str, sorted(peak_hours)))}:00",
                        "Consider scheduling deep research during these peak productivity windows",
                    ],
                )
                patterns.append(pattern)

        return patterns

    async def _identify_source_preferences(self) -> list[ResearchPattern]:
        """Identify source usage patterns and preferences"""
        source_usage = Counter()
        source_success = defaultdict(list)

        for event in self.search_history:
            sources = event.get("sources_used", [])
            semantic_score = event.get("semantic_analytics", {}).get(
                "avg_semantic_score",
                0,
            )

            for source in sources:
                source_usage[source] += 1
                source_success[source].append(semantic_score)

        patterns = []

        if source_usage:
            # Identify preferred sources
            most_used_source = source_usage.most_common(1)[0]
            if most_used_source[1] >= self.pattern_min_frequency:
                avg_success = statistics.mean(source_success[most_used_source[0]])

                pattern = ResearchPattern(
                    pattern_type="source_preference",
                    pattern_name=f"Preferred source: {most_used_source[0]}",
                    frequency=most_used_source[1],
                    confidence=min(1.0, avg_success),
                    last_seen=datetime.now(UTC),
                    insights=[
                        f"Consistently use {most_used_source[0]} for research",
                        f"Average relevance score: {avg_success:.2f}",
                        (
                            "Consider exploring other sources for broader perspectives"
                            if avg_success < 0.6
                            else "This source provides consistently relevant results"
                        ),
                    ],
                )
                patterns.append(pattern)

        return patterns

    async def generate_knowledge_insights(self) -> list[KnowledgeInsight]:
        """Generate actionable knowledge insights and recommendations"""
        insights = []

        # Research gap insights
        gap_insights = await self._generate_research_gap_insights()
        insights.extend(gap_insights)

        # Trending topic insights
        trend_insights = await self._generate_trending_insights()
        insights.extend(trend_insights)

        # Deep dive recommendations
        deep_dive_insights = await self._generate_deep_dive_insights()
        insights.extend(deep_dive_insights)

        # Related area suggestions
        related_insights = await self._generate_related_area_insights()
        insights.extend(related_insights)

        self.knowledge_insights = insights
        return insights

    async def _generate_research_gap_insights(self) -> list[KnowledgeInsight]:
        """Generate insights about potential research gaps"""
        insights = []

        metrics = await self.generate_dashboard_metrics()
        knowledge_gaps = metrics.knowledge_gaps

        for gap in knowledge_gaps[:3]:  # Top 3 gaps
            insight = KnowledgeInsight(
                insight_type="research_gap",
                title=f"Explore {gap.title()} more deeply",
                description=f"Your searches for {gap} have shown mixed results, suggesting an opportunity for deeper exploration.",
                confidence=0.7,
                actionable_suggestions=[
                    f"Try more specific queries about {gap}",
                    f"Explore {gap} from different perspectives (academic, practical, historical)",
                    f"Look for comprehensive reviews or introductory materials on {gap}",
                ],
                related_topics=[gap],
                priority="medium",
            )
            insights.append(insight)

        return insights

    async def _generate_trending_insights(self) -> list[KnowledgeInsight]:
        """Generate insights about trending topics"""
        insights = []

        metrics = await self.generate_dashboard_metrics()
        trending = metrics.trending_topics[:2]  # Top 2 trends

        for topic, frequency in trending:
            if frequency >= 3:  # Significant trend
                insight = KnowledgeInsight(
                    insight_type="trending_topic",
                    title=f"{topic.title()} is trending in your research",
                    description=f"You've explored {topic} {frequency} times recently, indicating strong interest.",
                    confidence=0.8,
                    actionable_suggestions=[
                        f"Consider creating a knowledge map for {topic}",
                        f"Look for recent developments in {topic}",
                        f"Connect {topic} to your other research areas",
                    ],
                    related_topics=[topic],
                    priority="high",
                )
                insights.append(insight)

        return insights

    async def _generate_deep_dive_insights(self) -> list[KnowledgeInsight]:
        """Generate deep dive recommendations for established interests"""
        insights = []

        # Identify topics with consistent high-quality results
        topic_quality = defaultdict(list)

        for event in self.search_history[-20:]:  # Recent events
            semantic_score = event.get("semantic_analytics", {}).get(
                "avg_semantic_score",
                0,
            )
            topics = event.get("semantic_analytics", {}).get("top_topics", [])

            for topic in topics:
                topic_quality[topic].append(semantic_score)

        for topic, scores in topic_quality.items():
            if len(scores) >= 3 and statistics.mean(scores) > 0.6:
                insight = KnowledgeInsight(
                    insight_type="deep_dive",
                    title=f"Ready for advanced {topic.title()} exploration",
                    description=f"Your {topic} searches show consistently good results, suggesting readiness for advanced topics.",
                    confidence=0.9,
                    actionable_suggestions=[
                        f"Explore advanced concepts in {topic}",
                        f"Look for cutting-edge research in {topic}",
                        f"Consider practical applications of {topic}",
                    ],
                    related_topics=[topic],
                    priority="high",
                )
                insights.append(insight)

        return insights[:2]  # Limit to top 2

    async def _generate_related_area_insights(self) -> list[KnowledgeInsight]:
        """Generate insights about related areas to explore"""
        insights = []

        patterns = await self.identify_research_patterns()
        topic_clusters = [p for p in patterns if p.pattern_type == "topic_cluster"]

        for cluster in topic_clusters[:1]:  # Top cluster
            # Suggest exploring the intersection of clustered topics
            topics = cluster.pattern_name.split(": ")[1].split(" ecosystem")[0]

            insight = KnowledgeInsight(
                insight_type="related_area",
                title=f"Explore intersections in {topics} domain",
                description="Your research shows connected interests that could benefit from interdisciplinary exploration.",
                confidence=cluster.confidence,
                actionable_suggestions=[
                    "Look for interdisciplinary research combining your focus areas",
                    f"Explore how {topics} connects to other fields",
                    "Consider practical applications that bridge multiple topics",
                ],
                related_topics=cluster.related_queries[:3],
                priority="medium",
            )
            insights.append(insight)

        return insights

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.analytics_cache:
            return False

        expiry = self.cache_expiry.get(cache_key)
        if not expiry or datetime.now(UTC) > expiry:
            return False

        return True

    def _invalidate_cache(self, cache_keys: list[str]) -> None:
        """Invalidate specific cache entries"""
        for key in cache_keys:
            if key in self.analytics_cache:
                del self.analytics_cache[key]
            if key in self.cache_expiry:
                del self.cache_expiry[key]

    async def generate_knowledge_graph(self) -> dict[str, Any]:
        """Generate knowledge graph from research data"""
        try:
            graph_service = get_knowledge_graph_service()

            # Convert research sessions to the format expected by knowledge graph
            # service
            sessions_dict = {
                session_id: {
                    "queries": session.queries,
                    "total_results": session.total_results,
                    "avg_semantic_score": session.avg_semantic_score,
                    "dominant_topics": session.dominant_topics,
                    "start_time": (
                        session.start_time.isoformat() if session.start_time else ""
                    ),
                    "session_duration_minutes": session.session_duration_minutes,
                }
                for session_id, session in self.research_sessions.items()
            }

            # Generate insights in dict format
            insights = await self.generate_knowledge_insights()
            insights_dict = [insight.__dict__ for insight in insights]

            # Generate knowledge graph
            knowledge_graph = await graph_service.generate_knowledge_graph(
                search_history=self.search_history,
                research_sessions=sessions_dict,
                knowledge_insights=insights_dict,
                max_nodes=30,  # Limit for dashboard display
            )

            # Get graph statistics
            graph_stats = graph_service.get_graph_statistics(knowledge_graph)

            return {
                "graph_data": knowledge_graph.to_dict(),
                "graph_statistics": graph_stats,
            }

        except Exception as e:
            logger.warning(f"Failed to generate knowledge graph: {e}")
            return {
                "graph_data": {"nodes": [], "edges": [], "metadata": {}},
                "graph_statistics": {"message": "Knowledge graph generation failed"},
                "error": str(e),
            }

    async def get_realtime_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive real-time dashboard data"""
        # Generate all components
        metrics = await self.generate_dashboard_metrics()
        patterns = await self.identify_research_patterns()
        insights = await self.generate_knowledge_insights()

        # Get recent session data
        recent_sessions = [
            session
            for session in self.research_sessions.values()
            if session.start_time > datetime.now(UTC) - timedelta(hours=24)
        ]

        # Generate knowledge graph
        knowledge_graph_data = await self.generate_knowledge_graph()

        return {
            "dashboard_metrics": metrics.__dict__,
            "research_patterns": [p.__dict__ for p in patterns],
            "knowledge_insights": [i.__dict__ for i in insights],
            "recent_sessions": [s.__dict__ for s in recent_sessions],
            "knowledge_graph": knowledge_graph_data,
            "system_status": {
                "total_searches_logged": len(self.search_history),
                "active_sessions": len(
                    [s for s in self.research_sessions.values() if s.end_time is None],
                ),
                "patterns_identified": len(patterns),
                "insights_generated": len(insights),
                "cache_status": len(self.analytics_cache),
                "last_updated": datetime.now(UTC).isoformat(),
            },
        }


# Global service instance
_analytics_service = None


def get_ml_analytics_service() -> MLAnalyticsAggregationService:
    """Get or create global ML analytics service instance"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = MLAnalyticsAggregationService()
    return _analytics_service


async def main():
    """Demo of ML analytics aggregation service"""
    service = get_ml_analytics_service()

    # Simulate some search events
    print("Simulating search events...")

    await service.record_search_event(
        query="artificial intelligence applications",
        results_count=5,
        semantic_analytics={
            "avg_semantic_score": 0.85,
            "top_topics": ["artificial", "intelligence", "applications"],
        },
        summarization_analytics={
            "avg_compression_ratio": 0.3,
            "avg_confidence_score": 0.9,
        },
        execution_time_ms=150.0,
        sources_used=["arxiv", "web"],
    )

    await service.record_search_event(
        query="machine learning neural networks",
        results_count=8,
        semantic_analytics={
            "avg_semantic_score": 0.78,
            "top_topics": ["machine", "learning", "neural", "networks"],
        },
        summarization_analytics={
            "avg_compression_ratio": 0.25,
            "avg_confidence_score": 0.85,
        },
        execution_time_ms=120.0,
        sources_used=["arxiv", "pubmed"],
    )

    await service.record_search_event(
        query="deep learning optimization",
        results_count=6,
        semantic_analytics={
            "avg_semantic_score": 0.72,
            "top_topics": ["deep", "learning", "optimization"],
        },
        summarization_analytics={
            "avg_compression_ratio": 0.4,
            "avg_confidence_score": 0.75,
        },
        execution_time_ms=180.0,
        sources_used=["arxiv"],
    )

    # Generate dashboard data
    print("\nGenerating dashboard analytics...")
    dashboard_data = await service.get_realtime_dashboard_data()

    print("\nDashboard Metrics:")
    metrics = dashboard_data["dashboard_metrics"]
    print(f"  Total Searches Today: {metrics['total_searches_today']}")
    print(f"  Avg Response Time: {metrics['avg_response_time_ms']}ms")
    print(f"  Research Productivity Score: {metrics['research_productivity_score']}")
    print(f"  Exploration Diversity: {metrics['exploration_diversity']}")

    print("\nTrending Topics:")
    for topic, freq in metrics["trending_topics"]:
        print(f"  {topic}: {freq} occurrences")

    print(f"\nFocus Areas: {', '.join(metrics['focus_areas'])}")

    print("\nResearch Patterns:")
    for pattern in dashboard_data["research_patterns"]:
        print(f"  {pattern['pattern_name']} (confidence: {pattern['confidence']:.2f})")
        for insight in pattern["insights"]:
            print(f"    • {insight}")

    print("\nKnowledge Insights:")
    for insight in dashboard_data["knowledge_insights"]:
        print(f"  {insight['title']} ({insight['insight_type']})")
        print(f"    {insight['description']}")
        for suggestion in insight["actionable_suggestions"]:
            print(f"    → {suggestion}")


if __name__ == "__main__":
    asyncio.run(main())
