#!/usr/bin/env python3
"""PAKE System - Knowledge Graph Service
Phase 10A: ML Intelligence Dashboard

Generates interactive knowledge graph visualizations from search patterns
and research sessions to show relationships between topics and concepts.
"""

import asyncio
import hashlib
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """A node in the knowledge graph"""

    id: str
    label: str
    type: str  # 'topic', 'query', 'source', 'session'
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    color: str = "#3498db"
    size: int = 10


@dataclass
class GraphEdge:
    """An edge connecting two nodes in the knowledge graph"""

    source_id: str
    target_id: str
    weight: float = 1.0
    edge_type: str = "related"  # 'related', 'contains', 'searched_together'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph structure"""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                    "weight": node.weight,
                    "metadata": node.metadata,
                    "color": node.color,
                    "size": node.size,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "weight": edge.weight,
                    "type": edge.edge_type,
                    "metadata": edge.metadata,
                }
                for edge in self.edges
            ],
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
        }


class KnowledgeGraphService:
    """Service for generating interactive knowledge graphs from research data.

    Creates visual representations of topic relationships, search patterns,
    and knowledge connections to help users understand their research landscape.
    """

    def __init__(self):
        # Node type colors
        self.node_colors = {
            "topic": "#3498db",  # Blue
            "query": "#e74c3c",  # Red
            "source": "#27ae60",  # Green
            "session": "#f39c12",  # Orange
            "insight": "#9b59b6",  # Purple
        }

        # Minimum thresholds for including nodes
        self.min_topic_frequency = 2
        self.min_edge_weight = 0.1

        logger.info("Knowledge Graph Service initialized")

    async def generate_knowledge_graph(
        self,
        search_history: list[dict[str, Any]],
        research_sessions: dict[str, Any],
        knowledge_insights: list[dict[str, Any]],
        max_nodes: int = 50,
    ) -> KnowledgeGraph:
        """Generate comprehensive knowledge graph from research data.

        Args:
            search_history: List of search events
            research_sessions: Dictionary of research sessions
            knowledge_insights: List of generated insights
            max_nodes: Maximum number of nodes to include

        Returns:
            KnowledgeGraph object ready for visualization
        """
        nodes = []
        edges = []

        # Generate topic nodes from search history
        topic_nodes, topic_frequencies = await self._generate_topic_nodes(
            search_history,
        )
        nodes.extend(topic_nodes)

        # Generate query nodes from recent searches
        # Last 10 queries
        query_nodes = await self._generate_query_nodes(search_history[-10:])
        nodes.extend(query_nodes)

        # Generate session nodes
        session_nodes = await self._generate_session_nodes(research_sessions)
        nodes.extend(session_nodes)

        # Generate insight nodes
        insight_nodes = await self._generate_insight_nodes(knowledge_insights)
        nodes.extend(insight_nodes)

        # Generate edges between nodes
        topic_edges = await self._generate_topic_edges(
            search_history,
            topic_frequencies,
        )
        edges.extend(topic_edges)

        query_topic_edges = await self._generate_query_topic_edges(
            search_history,
            topic_frequencies,
        )
        edges.extend(query_topic_edges)

        session_edges = await self._generate_session_edges(
            research_sessions,
            topic_frequencies,
        )
        edges.extend(session_edges)

        # Limit nodes to max_nodes by weight/importance
        if len(nodes) > max_nodes:
            nodes.sort(key=lambda n: n.weight, reverse=True)
            kept_node_ids = set(node.id for node in nodes[:max_nodes])
            nodes = nodes[:max_nodes]

            # Filter edges to only include connections between kept nodes
            edges = [
                edge
                for edge in edges
                if edge.source_id in kept_node_ids and edge.target_id in kept_node_ids
            ]

        # Calculate graph statistics
        graph_metadata = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": Counter(node.type for node in nodes),
            "edge_types": Counter(edge.edge_type for edge in edges),
            "avg_node_weight": (
                sum(node.weight for node in nodes) / len(nodes) if nodes else 0
            ),
            "avg_edge_weight": (
                sum(edge.weight for edge in edges) / len(edges) if edges else 0
            ),
        }

        return KnowledgeGraph(nodes=nodes, edges=edges, metadata=graph_metadata)

    async def _generate_topic_nodes(
        self,
        search_history: list[dict[str, Any]],
    ) -> tuple[list[GraphNode], dict[str, int]]:
        """Generate nodes for topics based on search frequency"""
        topic_frequencies = Counter()
        topic_semantic_scores = defaultdict(list)

        # Count topic occurrences and collect semantic scores
        for event in search_history:
            semantic_analytics = event.get("semantic_analytics", {})
            topics = semantic_analytics.get("top_topics", [])
            semantic_score = semantic_analytics.get("avg_semantic_score", 0)

            for topic in topics:
                topic_frequencies[topic] += 1
                topic_semantic_scores[topic].append(semantic_score)

        # Create nodes for frequently occurring topics
        topic_nodes = []
        for topic, frequency in topic_frequencies.items():
            if frequency >= self.min_topic_frequency:
                # Calculate average semantic score for this topic
                avg_semantic_score = (
                    sum(topic_semantic_scores[topic])
                    / len(topic_semantic_scores[topic])
                    if topic_semantic_scores[topic]
                    else 0.5
                )

                # Node weight based on frequency and semantic relevance
                weight = frequency * (1 + avg_semantic_score)

                # Node size based on frequency (10-30 range)
                size = min(30, max(10, 10 + frequency * 2))

                node = GraphNode(
                    id=f"topic_{topic}",
                    label=topic.title(),
                    type="topic",
                    weight=weight,
                    size=size,
                    color=self.node_colors["topic"],
                    metadata={
                        "frequency": frequency,
                        "avg_semantic_score": avg_semantic_score,
                        "category": "topic",
                    },
                )
                topic_nodes.append(node)

        return topic_nodes, dict(topic_frequencies)

    async def _generate_query_nodes(
        self,
        recent_searches: list[dict[str, Any]],
    ) -> list[GraphNode]:
        """Generate nodes for recent queries"""
        query_nodes = []

        for i, event in enumerate(recent_searches):
            query = event.get("query", "")
            if len(query) > 3:  # Skip very short queries
                # Create unique ID for query
                query_id = hashlib.sha256(query.encode()).hexdigest()[:8]

                # Weight based on recency and results count
                recency_bonus = (len(recent_searches) - i) / len(recent_searches)
                results_count = event.get("results_count", 0)
                weight = recency_bonus * (1 + results_count * 0.1)

                node = GraphNode(
                    id=f"query_{query_id}",
                    label=query[:30] + "..." if len(query) > 30 else query,
                    type="query",
                    weight=weight,
                    size=max(8, min(20, 8 + results_count)),
                    color=self.node_colors["query"],
                    metadata={
                        "full_query": query,
                        "results_count": results_count,
                        "timestamp": event.get("timestamp", ""),
                        "execution_time_ms": event.get("execution_time_ms", 0),
                    },
                )
                query_nodes.append(node)

        return query_nodes

    async def _generate_session_nodes(
        self,
        research_sessions: dict[str, Any],
    ) -> list[GraphNode]:
        """Generate nodes for research sessions"""
        session_nodes = []

        for session_id, session_data in research_sessions.items():
            if isinstance(session_data, dict):
                query_count = len(session_data.get("queries", []))
                total_results = session_data.get("total_results", 0)
                avg_semantic_score = session_data.get("avg_semantic_score", 0)

                # Weight based on activity and quality
                weight = query_count * (1 + avg_semantic_score) * (total_results * 0.1)

                # Size based on activity
                size = min(25, max(12, 12 + query_count * 2))

                node = GraphNode(
                    id=f"session_{session_id}",
                    label=f"Session {session_id[:8]}",
                    type="session",
                    weight=weight,
                    size=size,
                    color=self.node_colors["session"],
                    metadata={
                        "session_id": session_id,
                        "query_count": query_count,
                        "total_results": total_results,
                        "avg_semantic_score": avg_semantic_score,
                        "start_time": session_data.get("start_time", ""),
                        "dominant_topics": session_data.get("dominant_topics", []),
                    },
                )
                session_nodes.append(node)

        return session_nodes

    async def _generate_insight_nodes(
        self,
        knowledge_insights: list[dict[str, Any]],
    ) -> list[GraphNode]:
        """Generate nodes for knowledge insights"""
        insight_nodes = []

        for i, insight in enumerate(knowledge_insights):
            insight_id = hashlib.sha256(
                insight.get("title", f"insight_{i}").encode(),
            ).hexdigest()[:8]

            # Weight based on confidence and priority
            confidence = insight.get("confidence", 0.5)
            priority_weights = {"high": 3, "medium": 2, "low": 1}
            priority_weight = priority_weights.get(insight.get("priority", "medium"), 2)

            weight = confidence * priority_weight

            # Size based on importance
            size = min(20, max(10, 10 + int(weight * 3)))

            # Color variation based on insight type
            insight_type = insight.get("insight_type", "general")
            color = {
                "research_gap": "#e74c3c",  # Red for gaps
                "trending_topic": "#f39c12",  # Orange for trends
                "deep_dive": "#27ae60",  # Green for opportunities
                "related_area": "#9b59b6",  # Purple for connections
            }.get(insight_type, self.node_colors["insight"])

            node = GraphNode(
                id=f"insight_{insight_id}",
                label=insight.get("title", "Insight")[:25] + "...",
                type="insight",
                weight=weight,
                size=size,
                color=color,
                metadata={
                    "insight_type": insight_type,
                    "confidence": confidence,
                    "priority": insight.get("priority", "medium"),
                    "description": insight.get("description", ""),
                    "actionable_suggestions": insight.get("actionable_suggestions", []),
                    "related_topics": insight.get("related_topics", []),
                },
            )
            insight_nodes.append(node)

        return insight_nodes

    async def _generate_topic_edges(
        self,
        search_history: list[dict[str, Any]],
        topic_frequencies: dict[str, int],
    ) -> list[GraphEdge]:
        """Generate edges between topics that appear together in searches"""
        topic_cooccurrence = defaultdict(Counter)

        # Track topic co-occurrence within individual searches
        for event in search_history:
            topics = event.get("semantic_analytics", {}).get("top_topics", [])

            # Create edges between all pairs of topics in this search
            for i, topic1 in enumerate(topics):
                for topic2 in topics[i + 1 :]:
                    if (
                        topic1 in topic_frequencies
                        and topic2 in topic_frequencies
                        and topic_frequencies[topic1] >= self.min_topic_frequency
                        and topic_frequencies[topic2] >= self.min_topic_frequency
                    ):
                        topic_cooccurrence[topic1][topic2] += 1
                        topic_cooccurrence[topic2][topic1] += 1

        # Create edges for significant co-occurrences
        edges = []
        processed_pairs = set()

        for topic1, related_topics in topic_cooccurrence.items():
            for topic2, cooccurrence_count in related_topics.items():
                pair = tuple(sorted([topic1, topic2]))
                if pair in processed_pairs:
                    continue

                # Calculate edge weight based on co-occurrence frequency
                max_possible = min(topic_frequencies[topic1], topic_frequencies[topic2])
                if max_possible > 0:
                    weight = cooccurrence_count / max_possible

                    if weight >= self.min_edge_weight:
                        edge = GraphEdge(
                            source_id=f"topic_{topic1}",
                            target_id=f"topic_{topic2}",
                            weight=weight,
                            edge_type="co_occurs",
                            metadata={
                                "cooccurrence_count": cooccurrence_count,
                                "topic1_frequency": topic_frequencies[topic1],
                                "topic2_frequency": topic_frequencies[topic2],
                            },
                        )
                        edges.append(edge)
                        processed_pairs.add(pair)

        return edges

    async def _generate_query_topic_edges(
        self,
        search_history: list[dict[str, Any]],
        topic_frequencies: dict[str, int],
    ) -> list[GraphEdge]:
        """Generate edges from queries to their related topics"""
        edges = []

        for event in search_history[-10:]:  # Recent searches only
            query = event.get("query", "")
            topics = event.get("semantic_analytics", {}).get("top_topics", [])
            semantic_score = event.get("semantic_analytics", {}).get(
                "avg_semantic_score",
                0,
            )

            if query and topics:
                query_id = hashlib.sha256(query.encode()).hexdigest()[:8]

                for topic in topics[:3]:  # Top 3 topics per query
                    if (
                        topic in topic_frequencies
                        and topic_frequencies[topic] >= self.min_topic_frequency
                    ):
                        # Edge weight based on semantic score and topic frequency
                        weight = semantic_score * (
                            topic_frequencies[topic] / max(topic_frequencies.values())
                        )

                        if weight >= self.min_edge_weight:
                            edge = GraphEdge(
                                source_id=f"query_{query_id}",
                                target_id=f"topic_{topic}",
                                weight=weight,
                                edge_type="contains_topic",
                                metadata={
                                    "query": query,
                                    "topic": topic,
                                    "semantic_score": semantic_score,
                                },
                            )
                            edges.append(edge)

        return edges

    async def _generate_session_edges(
        self,
        research_sessions: dict[str, Any],
        topic_frequencies: dict[str, int],
    ) -> list[GraphEdge]:
        """Generate edges from sessions to their dominant topics"""
        edges = []

        for session_id, session_data in research_sessions.items():
            if isinstance(session_data, dict):
                dominant_topics = session_data.get("dominant_topics", [])
                avg_semantic_score = session_data.get("avg_semantic_score", 0)

                for topic in dominant_topics[:3]:  # Top 3 topics per session
                    if (
                        topic in topic_frequencies
                        and topic_frequencies[topic] >= self.min_topic_frequency
                    ):
                        # Edge weight based on session quality and topic dominance
                        weight = (
                            avg_semantic_score * 0.8
                        )  # Sessions have slightly lower weight

                        if weight >= self.min_edge_weight:
                            edge = GraphEdge(
                                source_id=f"session_{session_id}",
                                target_id=f"topic_{topic}",
                                weight=weight,
                                edge_type="focuses_on",
                                metadata={
                                    "session_id": session_id,
                                    "topic": topic,
                                    "avg_semantic_score": avg_semantic_score,
                                },
                            )
                            edges.append(edge)

        return edges

    def get_graph_statistics(self, graph: KnowledgeGraph) -> dict[str, Any]:
        """Calculate detailed graph statistics"""
        if not graph.nodes:
            return {"message": "Empty graph"}

        node_degrees = defaultdict(int)
        for edge in graph.edges:
            node_degrees[edge.source_id] += 1
            node_degrees[edge.target_id] += 1

        # Find most connected nodes
        most_connected = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        # Calculate clustering metrics
        total_possible_edges = len(graph.nodes) * (len(graph.nodes) - 1) / 2
        edge_density = (
            len(graph.edges) / total_possible_edges if total_possible_edges > 0 else 0
        )

        return {
            "basic_stats": {
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "edge_density": round(edge_density, 3),
                "avg_degree": (
                    round(sum(node_degrees.values()) / len(graph.nodes), 2)
                    if graph.nodes
                    else 0
                ),
            },
            "node_distribution": dict(Counter(node.type for node in graph.nodes)),
            "most_connected_nodes": [
                {
                    "node_id": node_id,
                    "connections": degree,
                    "degree_centrality": round(degree / (len(graph.nodes) - 1), 3),
                }
                for node_id, degree in most_connected
            ],
            "weight_distribution": {
                "avg_node_weight": round(
                    sum(node.weight for node in graph.nodes) / len(graph.nodes),
                    3,
                ),
                "avg_edge_weight": (
                    round(
                        sum(edge.weight for edge in graph.edges) / len(graph.edges),
                        3,
                    )
                    if graph.edges
                    else 0
                ),
                "max_node_weight": max(node.weight for node in graph.nodes),
                "max_edge_weight": (
                    max(edge.weight for edge in graph.edges) if graph.edges else 0
                ),
            },
        }


# Global service instance
_knowledge_graph_service = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get or create global knowledge graph service instance"""
    global _knowledge_graph_service
    if _knowledge_graph_service is None:
        _knowledge_graph_service = KnowledgeGraphService()
    return _knowledge_graph_service


async def main():
    """Demo of knowledge graph service"""
    service = get_knowledge_graph_service()

    # Simulate search history
    sample_search_history = [
        {
            "query": "artificial intelligence applications",
            "results_count": 5,
            "semantic_analytics": {
                "avg_semantic_score": 0.85,
                "top_topics": ["artificial", "intelligence", "applications"],
            },
            "timestamp": "2025-09-14T01:00:00Z",
        },
        {
            "query": "machine learning neural networks",
            "results_count": 8,
            "semantic_analytics": {
                "avg_semantic_score": 0.78,
                "top_topics": ["machine", "learning", "neural", "networks"],
            },
            "timestamp": "2025-09-14T01:15:00Z",
        },
        {
            "query": "artificial intelligence ethics",
            "results_count": 6,
            "semantic_analytics": {
                "avg_semantic_score": 0.72,
                "top_topics": ["artificial", "intelligence", "ethics"],
            },
            "timestamp": "2025-09-14T01:30:00Z",
        },
    ]

    # Simulate research sessions
    sample_sessions = {
        "session_1": {
            "queries": [
                "artificial intelligence applications",
                "machine learning neural networks",
            ],
            "total_results": 13,
            "avg_semantic_score": 0.82,
            "dominant_topics": ["artificial", "intelligence", "machine", "learning"],
            "start_time": "2025-09-14T01:00:00Z",
        },
    }

    # Simulate insights
    sample_insights = [
        {
            "title": "Deep dive into AI applications",
            "confidence": 0.8,
            "priority": "high",
            "insight_type": "deep_dive",
            "related_topics": ["artificial", "intelligence", "applications"],
        },
    ]

    print("Generating knowledge graph...")
    graph = await service.generate_knowledge_graph(
        sample_search_history,
        sample_sessions,
        sample_insights,
    )

    print("\nKnowledge Graph Generated:")
    print(f"  Nodes: {len(graph.nodes)}")
    print(f"  Edges: {len(graph.edges)}")

    print("\nNodes by type:")
    for node in graph.nodes:
        print(f"  {node.type}: {node.label} (weight: {node.weight:.2f})")

    print("\nEdges:")
    for edge in graph.edges:
        print(
            f"  {edge.source_id} -> {edge.target_id} ({edge.edge_type}, weight: {edge.weight:.2f})",
        )

    # Get statistics
    stats = service.get_graph_statistics(graph)
    print("\nGraph Statistics:")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
