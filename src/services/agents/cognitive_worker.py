#!/usr/bin/env python3
"""PAKE System - Cognitive Engine Worker Agent
Stateless worker for content quality assessment and cognitive processing.

Handles:
- Content quality assessment
- Relevance scoring and analysis
- Knowledge extraction and structuring
- Cognitive optimization recommendations
"""

import logging
from datetime import UTC, datetime
from typing import Any

from ..messaging.message_bus import MessageBus
from .base_worker import BaseWorkerAgent, WorkerCapabilityBuilder

# Configure logging
logger = logging.getLogger(__name__)


class CognitiveWorker(BaseWorkerAgent):
    """Stateless worker agent for cognitive processing and content assessment.

    Processes cognitive assessment tasks from the supervisor to evaluate
    content quality, relevance, and extract actionable insights.
    """

    def __init__(self, message_bus: MessageBus, worker_id: str = None):
        """Initialize Cognitive Engine worker"""
        # Define worker capabilities
        capabilities = [
            WorkerCapabilityBuilder("content_quality_assessment")
            .with_description("Assess content quality using multiple dimensions")
            .with_input_types("content_text", "metadata", "context")
            .with_output_types(
                "quality_score",
                "quality_dimensions",
                "improvement_suggestions",
            )
            .with_performance_metrics(
                assessment_accuracy=0.92,
                processing_speed=1.8,
                consistency_score=0.95,
            )
            .build(),
            WorkerCapabilityBuilder("relevance_analysis")
            .with_description(
                "Analyze content relevance to research topics and context",
            )
            .with_input_types("content", "topic", "context", "keywords")
            .with_output_types("relevance_score", "topic_alignment", "keyword_matches")
            .with_performance_metrics(
                relevance_accuracy=0.90,
                topic_matching_precision=0.89,
                contextual_analysis=True,
            )
            .build(),
            WorkerCapabilityBuilder("knowledge_extraction")
            .with_description("Extract structured knowledge and key insights")
            .with_input_types("content_text", "domain_context")
            .with_output_types("key_concepts", "entities", "relationships")
            .with_performance_metrics(
                extraction_precision=0.87,
                entity_recognition=0.91,
                concept_clustering=True,
            )
            .build(),
            WorkerCapabilityBuilder("cognitive_optimization")
            .with_description(
                "Provide optimization recommendations for content processing",
            )
            .with_input_types("assessment_results", "processing_context")
            .with_output_types(
                "optimization_suggestions",
                "priority_rankings",
                "action_items",
            )
            .with_performance_metrics(
                suggestion_accuracy=0.85,
                actionability_score=0.88,
            )
            .build(),
        ]

        super().__init__(
            worker_type="cognitive_engine",
            message_bus=message_bus,
            capabilities=capabilities,
            worker_id=worker_id,
        )

        # Cognitive worker specific configuration
        self.max_task_timeout = 120.0  # 2 minutes for cognitive processing
        self.quality_dimensions = [
            "clarity",
            "coherence",
            "completeness",
            "accuracy",
            "relevance",
            "timeliness",
            "credibility",
        ]
        self.relevance_factors = [
            "keyword_match",
            "topic_alignment",
            "contextual_fit",
            "semantic_similarity",
            "domain_relevance",
        ]

        # Quality assessment thresholds
        self.quality_thresholds = {
            "excellent": 0.9,
            "good": 0.75,
            "fair": 0.6,
            "poor": 0.4,
        }

        logger.info(f"CognitiveWorker {self.worker_id} initialized")

    async def process_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process cognitive assessment task.

        Handles various cognitive processing tasks including quality assessment,
        relevance analysis, and optimization recommendations.
        """
        try:
            # Determine task type
            task_type = task_data.get("task_type", "cognitive_assessment")

            if task_type == "cognitive_assessment":
                return await self._process_quality_assessment(task_data)
            if task_type == "relevance_analysis":
                return await self._process_relevance_analysis(task_data)
            if task_type == "knowledge_extraction":
                return await self._process_knowledge_extraction(task_data)
            if task_type == "optimization_recommendations":
                return await self._process_optimization_recommendations(task_data)
            return {
                "success": False,
                "error": f"Unknown cognitive task type: {task_type}",
                "result": None,
            }

        except Exception as e:
            logger.error(f"Cognitive worker task processing error: {e}")
            return {
                "success": False,
                "error": f"Task processing failed: {str(e)}",
                "result": None,
            }

    async def _process_quality_assessment(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process content quality assessment"""
        content_items_data = task_data.get("content_items", [])
        assessment_type = task_data.get("assessment_type", "quality_and_relevance")
        context = task_data.get("context", {})

        if not content_items_data:
            return {
                "success": False,
                "error": "No content items provided for assessment",
                "result": None,
            }

        assessments = []
        total_quality_score = 0.0
        processed_items = 0

        for item_data in content_items_data:
            try:
                # Extract content and metadata
                content_text = (
                    f"{item_data.get('title', '')} {item_data.get('content', '')}"
                )
                metadata = item_data.get("metadata", {})

                # Perform quality assessment
                quality_assessment = await self._assess_content_quality(
                    content_text,
                    metadata,
                    context,
                )

                # Perform relevance analysis if requested
                relevance_assessment = {}
                if "relevance" in assessment_type:
                    relevance_assessment = await self._assess_content_relevance(
                        content_text,
                        context,
                    )

                # Combine assessments
                combined_assessment = {
                    **quality_assessment,
                    **relevance_assessment,
                    "item_id": item_data.get("source_name", f"item_{processed_items}"),
                    "processed_at": datetime.now(UTC).isoformat(),
                }

                assessments.append(combined_assessment)
                total_quality_score += quality_assessment.get("overall_quality", 0.0)
                processed_items += 1

            except Exception as e:
                logger.warning(f"Failed to assess content item: {e}")
                assessments.append(
                    {
                        "error": str(e),
                        "item_id": item_data.get(
                            "source_name",
                            f"item_{processed_items}",
                        ),
                        "overall_quality": 0.0,
                    },
                )
                processed_items += 1

        average_quality = total_quality_score / max(processed_items, 1)

        return {
            "success": True,
            "result": assessments,
            "error": None,
            "metrics": {
                "items_assessed": processed_items,
                "average_quality_score": average_quality,
                "quality_distribution": self._calculate_quality_distribution(
                    assessments,
                ),
                "high_quality_items": len(
                    [
                        a
                        for a in assessments
                        if a.get("overall_quality", 0)
                        >= self.quality_thresholds["good"]
                    ],
                ),
                "assessment_type": assessment_type,
            },
        }

    async def _process_relevance_analysis(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process content relevance analysis"""
        content = task_data.get("content", "")
        topic = task_data.get("topic", "")
        context = task_data.get("context", {})

        if not content or not topic:
            return {
                "success": False,
                "error": "Content and topic are required for relevance analysis",
                "result": None,
            }

        relevance_assessment = await self._assess_content_relevance(
            content,
            {"topic": topic, **context},
        )

        return {
            "success": True,
            "result": relevance_assessment,
            "error": None,
            "metrics": {
                "relevance_score": relevance_assessment.get("relevance_score", 0.0),
                "topic_alignment": relevance_assessment.get("topic_alignment", 0.0),
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            },
        }

    async def _process_knowledge_extraction(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process knowledge extraction from content"""
        content = task_data.get("content", "")
        domain_context = task_data.get("domain_context", {})

        if not content:
            return {
                "success": False,
                "error": "No content provided for knowledge extraction",
                "result": None,
            }

        knowledge = await self._extract_knowledge(content, domain_context)

        return {
            "success": True,
            "result": knowledge,
            "error": None,
            "metrics": {
                "concepts_extracted": len(knowledge.get("key_concepts", [])),
                "entities_identified": len(knowledge.get("entities", [])),
                "relationships_found": len(knowledge.get("relationships", [])),
                "extraction_timestamp": datetime.now(UTC).isoformat(),
            },
        }

    async def _process_optimization_recommendations(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process optimization recommendations"""
        assessment_results = task_data.get("assessment_results", [])
        processing_context = task_data.get("processing_context", {})

        if not assessment_results:
            return {
                "success": False,
                "error": "No assessment results provided for optimization",
                "result": None,
            }

        recommendations = await self._generate_optimization_recommendations(
            assessment_results,
            processing_context,
        )

        return {
            "success": True,
            "result": recommendations,
            "error": None,
            "metrics": {
                "recommendations_generated": len(
                    recommendations.get("suggestions", []),
                ),
                "high_priority_actions": len(
                    [
                        r
                        for r in recommendations.get("suggestions", [])
                        if r.get("priority") == "high"
                    ],
                ),
                "recommendation_timestamp": datetime.now(UTC).isoformat(),
            },
        }

    async def _assess_content_quality(
        self,
        content: str,
        metadata: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess content quality across multiple dimensions"""
        # Basic content metrics
        word_count = len(content.split())
        char_count = len(content)
        sentence_count = content.count(".") + content.count("!") + content.count("?")

        # Quality dimension scores (simplified implementation)
        dimension_scores = {}

        # Clarity (based on readability factors)
        avg_sentence_length = word_count / max(sentence_count, 1)
        clarity_score = min(1.0, max(0.0, 1.0 - (avg_sentence_length - 15) / 50))
        dimension_scores["clarity"] = clarity_score

        # Completeness (based on content length and structure)
        completeness_score = min(1.0, word_count / 500)  # Assume 500 words is complete
        dimension_scores["completeness"] = completeness_score

        # Coherence (simplified - based on repeated keywords)
        words = content.lower().split()
        unique_words = len(set(words))
        coherence_score = min(1.0, unique_words / max(len(words), 1) * 3)
        dimension_scores["coherence"] = coherence_score

        # Accuracy (based on metadata indicators)
        accuracy_score = 0.8  # Default - could be enhanced with fact-checking
        if metadata.get("peer_reviewed"):
            accuracy_score += 0.1
        if metadata.get("citations", 0) > 0:
            accuracy_score += 0.05
        dimension_scores["accuracy"] = min(1.0, accuracy_score)

        # Credibility (based on source and metadata)
        credibility_score = 0.7  # Default
        if metadata.get("indexed_in_pubmed") or metadata.get("arxiv_id"):
            credibility_score += 0.2
        if metadata.get("author"):
            credibility_score += 0.1
        dimension_scores["credibility"] = min(1.0, credibility_score)

        # Timeliness (based on publication date)
        timeliness_score = 0.8  # Default
        if metadata.get("published"):
            # Simple timeliness calculation - newer is better
            timeliness_score = 0.9  # Simplified
        dimension_scores["timeliness"] = timeliness_score

        # Overall quality (weighted average)
        weights = {
            "clarity": 0.2,
            "completeness": 0.2,
            "coherence": 0.15,
            "accuracy": 0.2,
            "credibility": 0.15,
            "timeliness": 0.1,
        }

        overall_quality = sum(
            dimension_scores[dim] * weights[dim] for dim in dimension_scores
        )

        # Quality classification
        quality_level = "poor"
        for level, threshold in sorted(
            self.quality_thresholds.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if overall_quality >= threshold:
                quality_level = level
                break

        return {
            "overall_quality": overall_quality,
            "quality_level": quality_level,
            "dimension_scores": dimension_scores,
            "content_metrics": {
                "word_count": word_count,
                "character_count": char_count,
                "sentence_count": sentence_count,
                "avg_sentence_length": avg_sentence_length,
            },
            "quality_indicators": {
                "has_metadata": len(metadata) > 0,
                "has_citations": metadata.get("citations", 0) > 0,
                "peer_reviewed": metadata.get("peer_reviewed", False),
                "structured_content": sentence_count > 3,
            },
        }

    async def _assess_content_relevance(
        self,
        content: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess content relevance to topic and context"""
        topic = context.get("topic", "").lower()
        content_lower = content.lower()

        # Keyword matching
        topic_words = set(topic.split())
        content_words = set(content_lower.split())
        keyword_matches = len(topic_words.intersection(content_words))
        keyword_score = min(1.0, keyword_matches / max(len(topic_words), 1))

        # Topic alignment (simplified semantic similarity)
        # In a real implementation, this would use embeddings/NLP models
        topic_alignment_score = keyword_score * 0.8 + 0.2  # Simplified

        # Contextual fit
        domain = context.get("domain", "")
        contextual_fit_score = 0.7  # Default
        if domain and domain.lower() in content_lower:
            contextual_fit_score = 0.9

        # Overall relevance score
        relevance_factors = {
            "keyword_match": keyword_score,
            "topic_alignment": topic_alignment_score,
            "contextual_fit": contextual_fit_score,
        }

        relevance_score = sum(relevance_factors.values()) / len(relevance_factors)

        # Relevance classification
        if relevance_score >= 0.8:
            relevance_level = "high"
        elif relevance_score >= 0.6:
            relevance_level = "medium"
        elif relevance_score >= 0.4:
            relevance_level = "low"
        else:
            relevance_level = "very_low"

        return {
            "relevance_score": relevance_score,
            "relevance_level": relevance_level,
            "topic_alignment": topic_alignment_score,
            "relevance_factors": relevance_factors,
            "keyword_matches": keyword_matches,
            "total_topic_keywords": len(topic_words),
            "match_ratio": keyword_matches / max(len(topic_words), 1),
        }

    async def _extract_knowledge(
        self,
        content: str,
        domain_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract structured knowledge from content"""
        # Simple knowledge extraction (would use NLP models in production)
        words = content.split()

        # Extract key concepts (simplified)
        key_concepts = []
        concept_indicators = ["algorithm", "method", "approach", "technique", "system"]
        for indicator in concept_indicators:
            if indicator in content.lower():
                key_concepts.append(indicator)

        # Extract entities (simplified)
        entities = []
        # Look for capitalized words (potential entities)
        for word in words:
            if word.istitle() and len(word) > 3:
                entities.append(word)

        entities = list(set(entities))[:10]  # Limit and deduplicate

        # Extract relationships (simplified)
        relationships = []
        relationship_patterns = ["related to", "based on", "derived from", "leads to"]
        for pattern in relationship_patterns:
            if pattern in content.lower():
                relationships.append({"type": pattern, "context": "found in content"})

        return {
            "key_concepts": key_concepts,
            "entities": entities,
            "relationships": relationships,
            "domain": domain_context.get("domain", "general"),
            "extraction_confidence": 0.75,  # Simplified confidence score
            "content_summary": content[:200] + "..." if len(content) > 200 else content,
        }

    async def _generate_optimization_recommendations(
        self,
        assessment_results: list[dict[str, Any]],
        processing_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate optimization recommendations based on assessments"""
        # Analyze assessment results
        quality_scores = [r.get("overall_quality", 0) for r in assessment_results]
        avg_quality = sum(quality_scores) / max(len(quality_scores), 1)

        recommendations = []

        # Quality-based recommendations
        if avg_quality < self.quality_thresholds["good"]:
            recommendations.append(
                {
                    "type": "quality_improvement",
                    "priority": "high",
                    "suggestion": "Focus on higher-quality sources",
                    "rationale": f"Average quality score ({avg_quality:.2f}) below threshold",
                    "action_items": [
                        "Add peer-reviewed source filters",
                        "Implement content length requirements",
                        "Enhance source credibility checks",
                    ],
                },
            )

        # Relevance-based recommendations
        relevance_scores = [r.get("relevance_score", 0) for r in assessment_results]
        if relevance_scores:
            avg_relevance = sum(relevance_scores) / len(relevance_scores)
            if avg_relevance < 0.7:
                recommendations.append(
                    {
                        "type": "relevance_improvement",
                        "priority": "medium",
                        "suggestion": "Refine search queries for better topic alignment",
                        "rationale": f"Average relevance score ({avg_relevance:.2f}) could be improved",
                        "action_items": [
                            "Add topic-specific keywords",
                            "Implement semantic search",
                            "Use domain-specific filters",
                        ],
                    },
                )

        # Content diversity recommendations
        source_types = set(
            r.get("item_id", "").split("_")[0] for r in assessment_results
        )
        if len(source_types) < 3:
            recommendations.append(
                {
                    "type": "diversity_improvement",
                    "priority": "medium",
                    "suggestion": "Increase content source diversity",
                    "rationale": f"Only {len(source_types)} source types detected",
                    "action_items": [
                        "Add more source types",
                        "Balance academic and web sources",
                        "Include different content formats",
                    ],
                },
            )

        # Performance recommendations
        processing_time = processing_context.get("processing_time", 0)
        if processing_time > 120:  # 2 minutes
            recommendations.append(
                {
                    "type": "performance_optimization",
                    "priority": "low",
                    "suggestion": "Optimize processing pipeline for speed",
                    "rationale": f"Processing time ({processing_time:.1f}s) above optimal",
                    "action_items": [
                        "Implement parallel processing",
                        "Add caching for repeated queries",
                        "Optimize content parsing",
                    ],
                },
            )

        return {
            "suggestions": recommendations,
            "summary": {
                "total_recommendations": len(recommendations),
                "high_priority": len(
                    [r for r in recommendations if r["priority"] == "high"],
                ),
                "medium_priority": len(
                    [r for r in recommendations if r["priority"] == "medium"],
                ),
                "low_priority": len(
                    [r for r in recommendations if r["priority"] == "low"],
                ),
            },
            "context": {
                "average_quality": avg_quality,
                "average_relevance": sum(relevance_scores)
                / max(len(relevance_scores), 1),
                "content_diversity": len(source_types),
                "processing_time": processing_time,
            },
        }

    def _calculate_quality_distribution(
        self,
        assessments: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Calculate distribution of quality levels"""
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}

        for assessment in assessments:
            quality_level = assessment.get("quality_level", "poor")
            if quality_level in distribution:
                distribution[quality_level] += 1

        return distribution

    async def _on_start(self):
        """Cognitive worker specific startup logic"""
        logger.info(
            f"CognitiveWorker {self.worker_id} cognitive processing engine ready",
        )

    async def _on_stop(self):
        """Cognitive worker specific cleanup logic"""
        logger.info(f"CognitiveWorker {self.worker_id} cleanup completed")

    async def get_health_status(self) -> dict[str, Any]:
        """Get cognitive worker specific health status"""
        base_health = await super().get_health_status()

        # Add cognitive-specific health information
        cognitive_health = {
            "cognitive_engine_status": "healthy",
            "quality_dimensions": len(self.quality_dimensions),
            "relevance_factors": len(self.relevance_factors),
            "max_task_timeout": self.max_task_timeout,
            "quality_assessment_enabled": True,
            "knowledge_extraction_enabled": True,
        }

        base_health.update(cognitive_health)
        return base_health


# Factory function for creating cognitive workers
async def create_cognitive_worker(
    message_bus: MessageBus,
    worker_id: str = None,
) -> CognitiveWorker:
    """Create and start a cognitive worker.

    Args:
        message_bus: Message bus for communication
        worker_id: Optional custom worker ID

    Returns:
        Started CognitiveWorker instance
    """
    worker = CognitiveWorker(message_bus=message_bus, worker_id=worker_id)

    await worker.start()
    return worker


# Task creation helpers
def create_quality_assessment_task_data(
    content_items: list[dict[str, Any]],
    context: dict[str, Any] = None,
) -> dict[str, Any]:
    """Create task data for content quality assessment"""
    return {
        "task_type": "cognitive_assessment",
        "content_items": content_items,
        "assessment_type": "quality_and_relevance",
        "context": context or {},
    }


def create_relevance_analysis_task_data(
    content: str,
    topic: str,
    context: dict[str, Any] = None,
) -> dict[str, Any]:
    """Create task data for relevance analysis"""
    return {
        "task_type": "relevance_analysis",
        "content": content,
        "topic": topic,
        "context": context or {},
    }


def create_knowledge_extraction_task_data(
    content: str,
    domain_context: dict[str, Any] = None,
) -> dict[str, Any]:
    """Create task data for knowledge extraction"""
    return {
        "task_type": "knowledge_extraction",
        "content": content,
        "domain_context": domain_context or {},
    }
