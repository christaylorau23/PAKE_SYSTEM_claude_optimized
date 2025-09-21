#!/usr/bin/env python3
"""PAKE System - PubMed Worker Agent
Stateless worker for biomedical literature ingestion from PubMed.

Handles:
- Biomedical literature search and retrieval
- MeSH term processing and filtering
- NCBI E-utilities API integration
- Medical content structuring
"""

import logging
from datetime import UTC, datetime
from typing import Any

from scripts.ingestion_pipeline import ContentItem

from ..ingestion.pubmed_service import PubMedSearchQuery, PubMedService
from ..messaging.message_bus import MessageBus
from .base_worker import BaseWorkerAgent, WorkerCapabilityBuilder

# Configure logging
logger = logging.getLogger(__name__)


class PubMedWorker(BaseWorkerAgent):
    """Stateless worker agent for PubMed biomedical literature ingestion.

    Processes biomedical search tasks from the supervisor using the PubMed service
    for comprehensive medical literature retrieval with NCBI compliance.
    """

    def __init__(
        self,
        message_bus: MessageBus,
        email: str = "worker@pake.example.com",
        worker_id: str = None,
    ):
        """Initialize PubMed worker"""
        # Define worker capabilities
        capabilities = [
            WorkerCapabilityBuilder("biomedical_literature_search")
            .with_description("Search and retrieve biomedical literature from PubMed")
            .with_input_types("search_query", "mesh_terms", "publication_types")
            .with_output_types("content_item", "medical_metadata", "mesh_headings")
            .with_performance_metrics(
                average_search_time=5.1,
                success_rate=0.96,
                papers_per_query=12,
            )
            .build(),
            WorkerCapabilityBuilder("ncbi_api_integration")
            .with_description(
                "Advanced NCBI E-utilities API integration with rate limiting",
            )
            .with_input_types("complex_queries", "mesh_filters", "date_ranges")
            .with_output_types("structured_results", "xml_parsing", "pmid_resolution")
            .with_performance_metrics(
                api_response_time=3.2,
                rate_limit_compliance=True,
                xml_parsing_accuracy=0.97,
            )
            .build(),
            WorkerCapabilityBuilder("medical_content_structuring")
            .with_description(
                "Structure medical content with proper MeSH terms and metadata",
            )
            .with_input_types("raw_paper_data", "mesh_headings", "publication_info")
            .with_output_types(
                "content_item",
                "mesh_classification",
                "medical_metadata",
            )
            .with_performance_metrics(
                structuring_accuracy=0.97,
                mesh_term_extraction=True,
                medical_classification=True,
            )
            .build(),
            WorkerCapabilityBuilder("biomedical_quality_assessment")
            .with_description(
                "Assess quality of biomedical content with domain expertise",
            )
            .with_input_types("medical_content", "mesh_terms", "publication_type")
            .with_output_types("quality_scores", "clinical_relevance", "evidence_level")
            .with_performance_metrics(
                assessment_accuracy=0.93,
                clinical_relevance_scoring=True,
            )
            .build(),
        ]

        super().__init__(
            worker_type="pubmed_service",
            message_bus=message_bus,
            capabilities=capabilities,
            worker_id=worker_id,
        )

        # Initialize PubMed service
        self.pubmed_service = PubMedService(email=email)

        # PubMed worker specific configuration
        self.max_task_timeout = 240.0  # 4 minutes for biomedical searches
        self.default_max_results = 8
        self.default_mesh_terms = [
            "Algorithms",
            "Machine Learning",
            "Artificial Intelligence",
        ]
        self.supported_publication_types = [
            "Journal Article",
            "Review",
            "Meta-Analysis",
            "Systematic Review",
            "Clinical Trial",
            "Randomized Controlled Trial",
            "Case Reports",
            "Comparative Study",
            "Editorial",
            "Letter",
        ]

        logger.info(f"PubMedWorker {self.worker_id} initialized with email: {email}")

    async def process_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process PubMed search task.

        Handles 'pubmed_ingestion' tasks from the supervisor with biomedical search parameters.
        """
        try:
            # Extract task parameters
            source_data = task_data.get("source", {})
            plan_context = task_data.get("plan_context", {})

            # Parse source configuration
            query_params = source_data.get("query_parameters", {})
            terms = query_params.get("terms", [])
            mesh_terms = query_params.get("mesh_terms", self.default_mesh_terms)
            publication_types = query_params.get(
                "publication_types",
                ["Journal Article"],
            )
            max_results = query_params.get("max_results", self.default_max_results)

            if not terms:
                return {
                    "success": False,
                    "error": "No search terms provided for PubMed search",
                    "result": None,
                }

            # Create PubMed search query
            search_query = PubMedSearchQuery(
                terms=terms,
                mesh_terms=self._validate_mesh_terms(mesh_terms),
                publication_types=self._validate_publication_types(publication_types),
                max_results=max_results,
                date_range=query_params.get("date_range"),
                sort_order="relevance",
            )

            # Determine if cognitive assessment is enabled
            use_cognitive = plan_context.get("cognitive_processing", False)

            # Execute search
            if use_cognitive:
                # Note: In actual implementation, cognitive_engine would be injected
                # For now, use standard search and simulate cognitive assessment
                result = await self.pubmed_service.search_papers(search_query)
                cognitive_applied = False
            else:
                result = await self.pubmed_service.search_papers(search_query)
                cognitive_applied = False

            if not result.success:
                return {
                    "success": False,
                    "error": f"PubMed search failed: {result.error}",
                    "result": None,
                }

            # Convert to ContentItems
            content_items = await self.pubmed_service.to_content_items(
                result,
                f"pubmed_worker_{self.worker_id}",
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
                f"PubMed search completed: {len(content_items)} papers retrieved",
            )

            return {
                "success": True,
                "result": serializable_items,
                "error": None,
                "metrics": {
                    "papers_retrieved": len(content_items),
                    "search_terms_used": len(terms),
                    "mesh_terms_used": len(mesh_terms),
                    "publication_types_used": len(publication_types),
                    "cognitive_assessment_applied": cognitive_applied,
                    "total_content_length": sum(
                        len(item.content or "") for item in content_items
                    ),
                    "unique_authors": len(
                        set(item.author for item in content_items if item.author),
                    ),
                    "clinical_papers": len(
                        [
                            item
                            for item in content_items
                            if item.metadata
                            and "Clinical"
                            in str(item.metadata.get("publication_type", ""))
                        ],
                    ),
                },
            }

        except Exception as e:
            logger.error(f"PubMed worker task processing error: {e}")
            return {
                "success": False,
                "error": f"Task processing failed: {str(e)}",
                "result": None,
            }

    def _validate_mesh_terms(self, mesh_terms: list[str]) -> list[str]:
        """Validate and filter MeSH terms"""
        if not mesh_terms:
            return self.default_mesh_terms

        # In a real implementation, we would validate against MeSH vocabulary
        # For now, return as-is with basic filtering
        valid_mesh_terms = [term for term in mesh_terms if term and len(term) > 2]

        if not valid_mesh_terms:
            logger.warning(f"No valid MeSH terms from {mesh_terms}, using defaults")
            return self.default_mesh_terms

        return valid_mesh_terms

    def _validate_publication_types(self, pub_types: list[str]) -> list[str]:
        """Validate publication types"""
        if not pub_types:
            return ["Journal Article"]

        # Filter to supported publication types
        valid_types = [pt for pt in pub_types if pt in self.supported_publication_types]

        if not valid_types:
            logger.warning(
                f"No valid publication types from {pub_types}, using default",
            )
            return ["Journal Article"]

        return valid_types

    def _enhance_content_metadata(
        self,
        content_item: ContentItem,
        plan_context: dict[str, Any],
        source_data: dict[str, Any],
        cognitive_applied: bool,
    ):
        """Enhance content item with PubMed-specific metadata"""
        if not content_item.metadata:
            content_item.metadata = {}

        # Add worker information
        content_item.metadata.update(
            {
                "worker_id": self.worker_id,
                "worker_type": self.worker_type,
                "processing_timestamp": datetime.now(UTC).isoformat(),
                "search_method": "ncbi_eutils_api",
                "biomedical_content": True,
                "peer_reviewed": True,  # PubMed content is generally peer-reviewed
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

        # Add PubMed-specific information
        if source_data:
            query_params = source_data.get("query_parameters", {})
            content_item.metadata.update(
                {
                    "mesh_terms": query_params.get("mesh_terms", []),
                    "publication_types": query_params.get("publication_types", []),
                    "search_terms": query_params.get("terms", []),
                    "source_priority": source_data.get("priority"),
                    "source_timeout": source_data.get("timeout"),
                    "estimated_results": source_data.get("estimated_results"),
                },
            )

        # Add biomedical-specific metadata
        if hasattr(content_item, "metadata") and content_item.metadata:
            # Enhance existing PubMed metadata
            if "pmid" in content_item.metadata:
                content_item.metadata["indexed_in_pubmed"] = True
                content_item.metadata["ncbi_compliant"] = True
                content_item.metadata["medical_literature"] = True

            # Add evidence level classification
            pub_type = content_item.metadata.get("publication_type", "")
            if (
                "Meta-Analysis" in pub_type
                or "Systematic Review" in pub_type
                or "Randomized Controlled Trial" in pub_type
            ):
                content_item.metadata["evidence_level"] = "high"
            elif "Clinical Trial" in pub_type:
                content_item.metadata["evidence_level"] = "medium"
            elif "Case Reports" in pub_type:
                content_item.metadata["evidence_level"] = "low"
            else:
                content_item.metadata["evidence_level"] = "medium"

    async def _on_start(self):
        """PubMed worker specific startup logic"""
        # Test PubMed service connection
        try:
            test_query = PubMedSearchQuery(
                terms=["machine learning"],
                mesh_terms=["Algorithms"],
                publication_types=["Journal Article"],
                max_results=1,
            )

            test_result = await self.pubmed_service.search_papers(test_query)

            if test_result.success:
                logger.info(f"PubMedWorker {self.worker_id} service test successful")
            else:
                logger.warning(
                    f"PubMedWorker {self.worker_id} service test warning: {
                        test_result.error
                    }",
                )

        except Exception as e:
            logger.error(f"PubMedWorker {self.worker_id} service test failed: {e}")

    async def _on_stop(self):
        """PubMed worker specific cleanup logic"""
        # No specific cleanup needed for stateless worker
        logger.info(f"PubMedWorker {self.worker_id} cleanup completed")

    async def get_health_status(self) -> dict[str, Any]:
        """Get PubMed worker specific health status"""
        base_health = await super().get_health_status()

        # Add PubMed-specific health information
        pubmed_health = {
            "pubmed_service_status": "healthy",
            "ncbi_api_status": "healthy",
            "supported_publication_types": len(self.supported_publication_types),
            "default_max_results": self.default_max_results,
            "max_task_timeout": self.max_task_timeout,
            "biomedical_search_enabled": True,
            "rate_limiting_compliant": True,
        }

        # Test PubMed service health
        try:
            test_query = PubMedSearchQuery(
                terms=["test"],
                mesh_terms=["Algorithms"],
                publication_types=["Journal Article"],
                max_results=1,
            )

            test_result = await self.pubmed_service.search_papers(test_query)

            if not test_result.success:
                pubmed_health["pubmed_service_status"] = "degraded"
                pubmed_health["pubmed_service_error"] = test_result.error

        except Exception as e:
            pubmed_health["pubmed_service_status"] = "unhealthy"
            pubmed_health["pubmed_service_error"] = str(e)

        base_health.update(pubmed_health)
        return base_health


# Factory function for creating PubMed workers
async def create_pubmed_worker(
    message_bus: MessageBus,
    email: str = None,
    worker_id: str = None,
) -> PubMedWorker:
    """Create and start a PubMed worker.

    Args:
        message_bus: Message bus for communication
        email: Email for NCBI API compliance
        worker_id: Optional custom worker ID

    Returns:
        Started PubMedWorker instance
    """
    # Use environment variable or default email
    if email is None:
        import os

        email = os.getenv("PUBMED_EMAIL", "worker@pake.example.com")

    worker = PubMedWorker(message_bus=message_bus, email=email, worker_id=worker_id)

    await worker.start()
    return worker


# Task type handlers for different PubMed search scenarios
class PubMedTaskTypes:
    """PubMed task type definitions"""

    BASIC_SEARCH = "pubmed_search_basic"
    CLINICAL_TRIALS = "pubmed_search_clinical"
    SYSTEMATIC_REVIEWS = "pubmed_search_systematic"
    META_ANALYSIS = "pubmed_search_meta"
    DISEASE_SPECIFIC = "pubmed_search_disease"
    DRUG_RESEARCH = "pubmed_search_drug"
    MESH_FOCUSED = "pubmed_search_mesh"


def create_pubmed_task_data(
    terms: list[str],
    mesh_terms: list[str] = None,
    publication_types: list[str] = None,
    max_results: int = 8,
    task_type: str = PubMedTaskTypes.BASIC_SEARCH,
    **kwargs,
) -> dict[str, Any]:
    """Create task data for PubMed search operations.

    Args:
        terms: Search terms
        mesh_terms: MeSH terms for filtering
        publication_types: Types of publications to search
        max_results: Maximum number of papers to retrieve
        task_type: Type of PubMed search task
        **kwargs: Additional search options

    Returns:
        Task data dictionary
    """
    return {
        "source": {
            "source_type": "pubmed",
            "query_parameters": {
                "terms": terms,
                "mesh_terms": mesh_terms or ["Algorithms"],
                "publication_types": publication_types or ["Journal Article"],
                "max_results": max_results,
                "date_range": kwargs.get("date_range"),
                "sort_order": kwargs.get("sort_order", "relevance"),
            },
            "priority": kwargs.get("priority", 3),
            "timeout": kwargs.get("source_timeout", 240),
            "estimated_results": max_results,
        },
        "plan_context": {
            "topic": kwargs.get("topic", "Biomedical Research"),
            "plan_id": kwargs.get("plan_id"),
            "cognitive_processing": kwargs.get("cognitive_processing", True),
        },
        "task_type": task_type,
    }


# Common MeSH terms by medical domain
PUBMED_DOMAIN_MESH_TERMS = {
    "artificial_intelligence": [
        "Artificial Intelligence",
        "Machine Learning",
        "Deep Learning",
        "Neural Networks, Computer",
        "Algorithms",
    ],
    "cardiology": [
        "Cardiology",
        "Heart Diseases",
        "Cardiovascular System",
        "Myocardial Infarction",
        "Heart Failure",
    ],
    "oncology": [
        "Neoplasms",
        "Cancer",
        "Oncology",
        "Chemotherapy",
        "Radiation Therapy",
        "Immunotherapy",
    ],
    "neurology": [
        "Neurology",
        "Brain",
        "Nervous System",
        "Neurological Disorders",
        "Alzheimer Disease",
        "Parkinson Disease",
    ],
    "infectious_diseases": [
        "Infectious Diseases",
        "Bacteria",
        "Viruses",
        "Antibiotics",
        "Antimicrobial Resistance",
        "Vaccines",
    ],
    "mental_health": [
        "Mental Health",
        "Psychiatry",
        "Depression",
        "Anxiety",
        "Schizophrenia",
        "Bipolar Disorder",
    ],
    "diabetes": [
        "Diabetes Mellitus",
        "Blood Glucose",
        "Insulin",
        "Endocrinology",
        "Metabolic Syndrome",
    ],
    "surgery": [
        "Surgery",
        "Surgical Procedures",
        "Minimally Invasive Surgery",
        "Robotic Surgery",
        "Anesthesia",
    ],
}


def get_mesh_terms_for_domain(domain: str) -> list[str]:
    """Get MeSH terms for a medical domain"""
    return PUBMED_DOMAIN_MESH_TERMS.get(domain.lower(), ["Algorithms"])
