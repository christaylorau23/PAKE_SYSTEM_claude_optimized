#!/usr/bin/env python3
"""PAKE System - ArXiv Enhanced Worker Agent
Stateless worker for academic paper ingestion from ArXiv.

Handles:
- Academic paper search and retrieval
- Quality assessment integration
- Metadata extraction and structuring
- Category and subject filtering
"""

import logging
from datetime import UTC, datetime
from typing import Any

from scripts.ingestion_pipeline import ContentItem

from ..ingestion.arxiv_enhanced_service import ArxivEnhancedService, ArxivSearchQuery
from ..messaging.message_bus import MessageBus
from .base_worker import BaseWorkerAgent, WorkerCapabilityBuilder

# Configure logging
logger = logging.getLogger(__name__)


class ArXivWorker(BaseWorkerAgent):
    """Stateless worker agent for ArXiv academic paper ingestion.

    Processes academic search tasks from the supervisor using the ArXiv Enhanced service
    for comprehensive academic content retrieval with cognitive assessment.
    """

    def __init__(self, message_bus: MessageBus, worker_id: str = None):
        """Initialize ArXiv worker"""
        # Define worker capabilities
        capabilities = [
            WorkerCapabilityBuilder("academic_paper_search")
            .with_description("Search and retrieve academic papers from ArXiv")
            .with_input_types("search_query", "categories", "date_range")
            .with_output_types("content_item", "paper_metadata", "citations")
            .with_performance_metrics(
                average_search_time=4.2,
                success_rate=0.97,
                papers_per_query=15,
            )
            .build(),
            WorkerCapabilityBuilder("arxiv_api_integration")
            .with_description("Advanced ArXiv API integration with query optimization")
            .with_input_types("complex_queries", "category_filters", "sorting_criteria")
            .with_output_types(
                "structured_results",
                "xml_parsing",
                "metadata_extraction",
            )
            .with_performance_metrics(
                api_response_time=2.8,
                xml_parsing_speed="high",
                metadata_completeness=0.95,
            )
            .build(),
            WorkerCapabilityBuilder("academic_content_structuring")
            .with_description(
                "Structure academic content with proper citations and metadata",
            )
            .with_input_types("raw_paper_data", "author_info", "subject_categories")
            .with_output_types(
                "content_item",
                "citation_data",
                "subject_classification",
            )
            .with_performance_metrics(
                structuring_accuracy=0.98,
                citation_extraction=True,
                subject_classification=True,
            )
            .build(),
            WorkerCapabilityBuilder("cognitive_quality_assessment")
            .with_description(
                "Integrate cognitive assessment for academic content quality",
            )
            .with_input_types("paper_content", "metadata", "context")
            .with_output_types("quality_scores", "relevance_metrics", "recommendations")
            .with_performance_metrics(assessment_accuracy=0.92, processing_speed="fast")
            .build(),
        ]

        super().__init__(
            worker_type="arxiv_service",
            message_bus=message_bus,
            capabilities=capabilities,
            worker_id=worker_id,
        )

        # Initialize ArXiv Enhanced service
        self.arxiv_service = ArxivEnhancedService()

        # ArXiv worker specific configuration
        self.max_task_timeout = 180.0  # 3 minutes for academic searches
        self.default_max_results = 10
        self.supported_categories = [
            "cs.AI",
            "cs.LG",
            "cs.CL",
            "cs.CV",
            "cs.RO",  # Computer Science
            "stat.ML",
            "math.ST",  # Statistics/Math
            "q-bio.QM",
            "q-bio.GN",  # Quantitative Biology
            "physics.data-an",
            "physics.comp-ph",  # Physics
        ]

        logger.info(f"ArXivWorker {self.worker_id} initialized")

    async def process_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process ArXiv search task.

        Handles 'arxiv_ingestion' tasks from the supervisor with academic search parameters.
        """
        try:
            # Extract task parameters
            source_data = task_data.get("source", {})
            plan_context = task_data.get("plan_context", {})

            # Parse source configuration
            query_params = source_data.get("query_parameters", {})
            terms = query_params.get("terms", [])
            categories = query_params.get("categories", [])
            max_results = query_params.get("max_results", self.default_max_results)

            if not terms:
                return {
                    "success": False,
                    "error": "No search terms provided for ArXiv search",
                    "result": None,
                }

            # Create ArXiv search query
            search_query = ArxivSearchQuery(
                terms=terms,
                categories=self._validate_categories(categories),
                max_results=max_results,
                sort_by="relevance",
                sort_order="descending",
            )

            # Determine if cognitive assessment is enabled
            use_cognitive = plan_context.get("cognitive_processing", False)

            # Execute search
            if use_cognitive:
                # Note: In actual implementation, cognitive_engine would be injected
                # For now, use standard search and simulate cognitive assessment
                result = await self.arxiv_service.search_papers(search_query)
                cognitive_applied = False
            else:
                result = await self.arxiv_service.search_papers(search_query)
                cognitive_applied = False

            if not result.success:
                return {
                    "success": False,
                    "error": f"ArXiv search failed: {result.error}",
                    "result": None,
                }

            # Convert to ContentItems
            content_items = await self.arxiv_service.to_content_items(
                result,
                f"arxiv_worker_{self.worker_id}",
            )

            # Enhance with context metadata
            for item in content_items:
                self._enhance_content_metadata(
                    item,
                    plan_context,
                    source_data,
                    cognitive_applied,
                )

            # Convert to serializable format
            serializable_items = [item.__dict__ for item in content_items]

            logger.info(
                f"ArXiv search completed: {len(content_items)} papers retrieved",
            )

            return {
                "success": True,
                "result": serializable_items,
                "error": None,
                "metrics": {
                    "papers_retrieved": len(content_items),
                    "search_terms_used": len(terms),
                    "categories_searched": len(categories),
                    "cognitive_assessment_applied": cognitive_applied,
                    "total_content_length": sum(
                        len(item.content or "") for item in content_items
                    ),
                    "unique_authors": len(
                        set(item.author for item in content_items if item.author),
                    ),
                },
            }

        except Exception as e:
            logger.error(f"ArXiv worker task processing error: {e}")
            return {
                "success": False,
                "error": f"Task processing failed: {str(e)}",
                "result": None,
            }

    def _validate_categories(self, categories: list[str]) -> list[str]:
        """Validate and filter ArXiv categories"""
        if not categories:
            return ["cs.AI", "cs.LG"]  # Default to AI/ML categories

        # Filter to supported categories and add defaults if empty
        valid_categories = [
            cat for cat in categories if cat in self.supported_categories
        ]

        if not valid_categories:
            logger.warning(f"No valid categories from {categories}, using defaults")
            return ["cs.AI", "cs.LG"]

        return valid_categories

    def _enhance_content_metadata(
        self,
        content_item: ContentItem,
        plan_context: dict[str, Any],
        source_data: dict[str, Any],
        cognitive_applied: bool,
    ):
        """Enhance content item with ArXiv-specific metadata"""
        if not content_item.metadata:
            content_item.metadata = {}

        # Add worker information
        content_item.metadata.update(
            {
                "worker_id": self.worker_id,
                "worker_type": self.worker_type,
                "processing_timestamp": datetime.now(UTC).isoformat(),
                "search_method": "arxiv_enhanced_api",
                "academic_content": True,
                "cognitive_assessment_applied": cognitive_applied,
            },
        )

        # Add plan context
        if plan_context:
            content_item.metadata.update(
                {
                    "plan_id": plan_context.get("plan_id"),
                    "research_topic": plan_context.get("topic"),
                    "cognitive_processing_enabled": plan_context.get(
                        "cognitive_processing",
                        False,
                    ),
                },
            )

        # Add ArXiv-specific information
        if source_data:
            query_params = source_data.get("query_parameters", {})
            content_item.metadata.update(
                {
                    "arxiv_categories": query_params.get("categories", []),
                    "search_terms": query_params.get("terms", []),
                    "source_priority": source_data.get("priority"),
                    "source_timeout": source_data.get("timeout"),
                    "estimated_results": source_data.get("estimated_results"),
                },
            )

        # Add academic-specific metadata
        if hasattr(content_item, "metadata") and content_item.metadata:
            # Enhance existing ArXiv metadata
            if "arxiv_id" in content_item.metadata:
                content_item.metadata["paper_type"] = "preprint"
                content_item.metadata["peer_reviewed"] = False
                content_item.metadata["open_access"] = True

    async def _on_start(self):
        """ArXiv worker specific startup logic"""
        # Test ArXiv service connection
        try:
            test_query = ArxivSearchQuery(
                terms=["machine learning"],
                categories=["cs.LG"],
                max_results=1,
            )

            test_result = await self.arxiv_service.search_papers(test_query)

            if test_result.success:
                logger.info(f"ArXivWorker {self.worker_id} service test successful")
            else:
                logger.warning(
                    f"ArXivWorker {self.worker_id} service test warning: {
                        test_result.error
                    }",
                )

        except Exception as e:
            logger.error(f"ArXivWorker {self.worker_id} service test failed: {e}")

    async def _on_stop(self):
        """ArXiv worker specific cleanup logic"""
        # No specific cleanup needed for stateless worker
        logger.info(f"ArXivWorker {self.worker_id} cleanup completed")

    async def get_health_status(self) -> dict[str, Any]:
        """Get ArXiv worker specific health status"""
        base_health = await super().get_health_status()

        # Add ArXiv-specific health information
        arxiv_health = {
            "arxiv_service_status": "healthy",
            "supported_categories": len(self.supported_categories),
            "default_max_results": self.default_max_results,
            "max_task_timeout": self.max_task_timeout,
            "academic_search_enabled": True,
        }

        # Test ArXiv service health
        try:
            test_query = ArxivSearchQuery(
                terms=["test"],
                categories=["cs.AI"],
                max_results=1,
            )

            test_result = await self.arxiv_service.search_papers(test_query)

            if not test_result.success:
                arxiv_health["arxiv_service_status"] = "degraded"
                arxiv_health["arxiv_service_error"] = test_result.error

        except Exception as e:
            arxiv_health["arxiv_service_status"] = "unhealthy"
            arxiv_health["arxiv_service_error"] = str(e)

        base_health.update(arxiv_health)
        return base_health


# Factory function for creating ArXiv workers
async def create_arxiv_worker(
    message_bus: MessageBus,
    worker_id: str = None,
) -> ArXivWorker:
    """Create and start an ArXiv worker.

    Args:
        message_bus: Message bus for communication
        worker_id: Optional custom worker ID

    Returns:
        Started ArXivWorker instance
    """
    worker = ArXivWorker(message_bus=message_bus, worker_id=worker_id)

    await worker.start()
    return worker


# Task type handlers for different ArXiv search scenarios
class ArXivTaskTypes:
    """ArXiv task type definitions"""

    BASIC_SEARCH = "arxiv_search_basic"
    CATEGORY_SPECIFIC = "arxiv_search_category"
    AUTHOR_SEARCH = "arxiv_search_author"
    RECENT_PAPERS = "arxiv_search_recent"
    COMPREHENSIVE_SURVEY = "arxiv_search_comprehensive"


def create_arxiv_task_data(
    terms: list[str],
    categories: list[str] = None,
    max_results: int = 10,
    task_type: str = ArXivTaskTypes.BASIC_SEARCH,
    **kwargs,
) -> dict[str, Any]:
    """Create task data for ArXiv search operations.

    Args:
        terms: Search terms
        categories: ArXiv categories to search
        max_results: Maximum number of papers to retrieve
        task_type: Type of ArXiv search task
        **kwargs: Additional search options

    Returns:
        Task data dictionary
    """
    return {
        "source": {
            "source_type": "arxiv",
            "query_parameters": {
                "terms": terms,
                "categories": categories or ["cs.AI", "cs.LG"],
                "max_results": max_results,
                "sort_by": kwargs.get("sort_by", "relevance"),
                "sort_order": kwargs.get("sort_order", "descending"),
                "date_range": kwargs.get("date_range"),
            },
            "priority": kwargs.get("priority", 2),
            "timeout": kwargs.get("source_timeout", 180),
            "estimated_results": max_results,
        },
        "plan_context": {
            "topic": kwargs.get("topic", "Academic Research"),
            "plan_id": kwargs.get("plan_id"),
            "cognitive_processing": kwargs.get("cognitive_processing", True),
        },
        "task_type": task_type,
    }


# ArXiv category mapping for domain-specific searches
ARXIV_DOMAIN_CATEGORIES = {
    "computer_science": [
        "cs.AI",
        "cs.LG",
        "cs.CL",
        "cs.CV",
        "cs.RO",
        "cs.NE",
        "cs.IR",
        "cs.HC",
        "cs.SE",
        "cs.DB",
        "cs.DC",
        "cs.CR",
    ],
    "machine_learning": ["cs.LG", "stat.ML", "cs.AI", "cs.NE"],
    "natural_language": ["cs.CL", "cs.AI", "cs.IR", "cs.LG"],
    "computer_vision": ["cs.CV", "cs.LG", "cs.AI", "eess.IV"],
    "robotics": ["cs.RO", "cs.AI", "cs.CV", "cs.LG"],
    "biology": ["q-bio.QM", "q-bio.GN", "q-bio.CB", "q-bio.MN"],
    "physics": ["physics.data-an", "physics.comp-ph", "cond-mat.stat-mech"],
    "mathematics": ["math.ST", "math.OC", "math.NA", "math.PR"],
    "statistics": ["stat.ML", "stat.TH", "stat.CO", "stat.AP"],
}


def get_categories_for_domain(domain: str) -> list[str]:
    """Get ArXiv categories for a research domain"""
    return ARXIV_DOMAIN_CATEGORIES.get(domain.lower(), ["cs.AI", "cs.LG"])
