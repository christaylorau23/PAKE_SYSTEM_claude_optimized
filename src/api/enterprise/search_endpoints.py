#!/usr/bin/env python3
"""PAKE System - Phase 17 Enterprise Multi-Tenant Search Endpoints
World-class search endpoints with tenant isolation, ML enhancement, and comprehensive analytics.
"""

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List

import aiohttp
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field

from src.api.enterprise.multi_tenant_server import SearchRequest, get_current_user
from src.middleware.tenant_context import get_current_tenant_id, get_current_user_id
from src.security.tenant_isolation_enforcer import enforce_tenant_isolation

logger = logging.getLogger(__name__)


# Mock dependencies for TDD (will be injected from main server)
def get_dal() -> Any:
    """Get data access layer instance."""
    return None  # Will be injected from main server


def get_tenant_orchestrator(tenant_id: str) -> Any:
    """Get tenant orchestrator instance."""
    return None  # Will be injected from main server


def get_semantic_search_service() -> Any:
    """Get semantic search service instance."""
    return None  # Will be injected from main server


def get_content_summarization_service() -> Any:
    """Get content summarization service instance."""
    return None  # Will be injected from main server


def get_security_enforcer() -> Any:
    """Get security enforcer instance."""
    return None  # Will be injected from main server


# Mock metrics for TDD (will be replaced with real metrics)
class MockMetrics:
    def labels(self, **kwargs):
        return self

    def inc(self):
        pass

    def observe(self, value):
        pass


SEARCH_OPERATIONS = MockMetrics()
SEARCH_DURATION = MockMetrics()

# Create search router
search_router = APIRouter(prefix="/search", tags=["search"])


@search_router.post("/")
@enforce_tenant_isolation("search", "multi_source")
async def perform_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    security_enforcer: Any = Depends(get_security_enforcer),
    get_tenant_orchestrator: Any = Depends(get_tenant_orchestrator),
    get_semantic_search_service: Any = Depends(get_semantic_search_service),
    get_content_summarization_service: Any = Depends(get_content_summarization_service),
    current_user: dict = Depends(get_current_user),
):
    """Perform comprehensive multi-source search with tenant isolation.

    Features:
    - Multi-source search (web, academic, biomedical)
    - ML-powered enhancement and ranking
    - Real-time content summarization
    - Search history tracking
    - Usage analytics
    - Security enforcement
    """
    tenant_id = get_current_tenant_id()
    user_id = get_current_user_id()

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        start_time = datetime.now(UTC)

        # Validate input parameters
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            raise HTTPException(status_code=400, detail="Invalid input detected")

        # Get tenant orchestrator
        orchestrator = await get_tenant_orchestrator(tenant_id)

        # Create and execute search plan
        plan = await orchestrator.create_ingestion_plan(
            topic=request.query,
            context={
                "sources": request.sources,
                "max_results_per_source": request.max_results,
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )

        result = await orchestrator.execute_ingestion_plan(plan)
        execution_time_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        # Process results
        processed_results = await process_search_results(
            result,
            request,
            tenant_id,
            user_id,
        )

        # ML enhancement if enabled
        if request.enable_ml_enhancement and processed_results:
            try:
                semantic_service = get_semantic_search_service()
                if semantic_service:
                    enhanced_results = await semantic_service.enhance_search_results(
                        query=request.query,
                        results=processed_results,
                        tenant_id=tenant_id,
                    )
                    processed_results = enhanced_results
            except (ValueError, RuntimeError) as e:
                logger.warning("ML enhancement failed: %s", e)

        # Content summarization if enabled
        if request.enable_summarization and processed_results:
            try:
                summarization_service = get_content_summarization_service()
                if summarization_service:
                    for result_item in processed_results:
                        if result_item.get("content"):
                            summary = await summarization_service.summarize_content(
                                content=result_item["content"],
                                tenant_id=tenant_id,
                            )
                            result_item["summary"] = summary
            except (ValueError, RuntimeError) as e:
                logger.warning("Content summarization failed: %s", e)

        # Save search history (background task)
        background_tasks.add_task(
            save_search_history,
            tenant_id,
            user_id,
            request.query,
            request.sources,
            len(processed_results),
            execution_time_ms,
            processed_results,
        )

        # Scan response for security issues
        scan_result = await security_enforcer.scan_response_data(
            processed_results,
            tenant_id,
        )

        if not scan_result["clean"]:
            logger.warning(
                "Security scan warning for tenant %s: %s",
                tenant_id,
                scan_result,
            )

        # Record search metrics
        SEARCH_OPERATIONS.labels(
            tenant_id=tenant_id,
            sources=",".join(request.sources),
            ml_enhanced=request.enable_ml_enhancement,
        ).inc()

        SEARCH_DURATION.labels(
            tenant_id=tenant_id,
            sources=",".join(request.sources),
        ).observe(execution_time_ms / 1000)

        return {
            "success": True,
            "query": request.query,
            "sources": request.sources,
            "results": processed_results,
            "total_results": len(processed_results),
            "execution_time_ms": execution_time_ms,
            "ml_enhanced": request.enable_ml_enhancement,
            "summarized": request.enable_summarization,
            "metadata": {
                "tenant_id": tenant_id,
                "timestamp": start_time.isoformat(),
                "plan_id": plan.plan_id if hasattr(plan, "plan_id") else None,
            },
        }

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Search error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Search service error")


@search_router.get("/history")
@enforce_tenant_isolation("read", "search_history")
async def get_search_history(
    dal: Any = Depends(get_dal),
    limit: int = 50,
    offset: int = 0,
    user_filter: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Get search history for current tenant."""
    tenant_id = get_current_tenant_id()
    user_id = get_current_user_id()

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    if not dal:
        raise HTTPException(status_code=503, detail="Data access layer not available")

    try:
        # Check permissions for user filtering
        if user_filter and user_filter != user_id:
            if current_user["role"] not in ["admin", "manager"]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Get search history
        if user_filter:
            search_history = await dal.search_history.get_by_user(
                user_filter,
                tenant_id,
                limit,
                offset,
            )
        else:
            search_history = await dal.search_history.get_all(tenant_id, limit, offset)

        # Convert to serializable format
        history_data = []
        for search in search_history:
            history_data.append(
                {
                    "id": search.id,
                    "query": search.query,
                    "sources": search.sources,
                    "results_count": search.results_count,
                    "execution_time_ms": search.execution_time_ms,
                    "cache_hit": search.cache_hit,
                    "quality_score": search.quality_score,
                    "created_at": search.created_at.isoformat(),
                    "user_id": search.user_id,
                },
            )

        return {
            "success": True,
            "search_history": history_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(history_data),
            },
        }

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Search history error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Search history service error")


@search_router.get("/analytics")
@enforce_tenant_isolation("read", "search_analytics")
async def get_search_analytics(
    days: int = 30,
    dal: Any = Depends(get_dal),
    current_user: dict = Depends(get_current_user),
):
    """Get search analytics for current tenant."""
    tenant_id = get_current_tenant_id()

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    if not dal:
        raise HTTPException(status_code=503, detail="Data access layer not available")

    try:
        analytics = await dal.search_history.get_search_analytics(tenant_id, days)

        return {"success": True, "analytics": analytics}

    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Search analytics error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Search analytics service error")


@search_router.get("/popular")
@enforce_tenant_isolation("read", "popular_searches")
async def get_popular_searches(
    limit: int = 10,
    days: int = 7,
    dal: Any = Depends(get_dal),
    current_user: dict = Depends(get_current_user),
):
    """Get popular searches within tenant."""
    tenant_id = get_current_tenant_id()

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    if not dal:
        raise HTTPException(status_code=503, detail="Data access layer not available")

    try:
        popular_searches = await dal.search_history.get_popular_searches(
            tenant_id,
            limit,
            days,
        )

        return {
            "success": True,
            "popular_searches": popular_searches,
            "period_days": days,
        }

    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Popular searches error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Popular searches service error")


@search_router.post("/saved")
@enforce_tenant_isolation("create", "saved_search")
async def save_search(
    request: SearchRequest,
    dal: Any = Depends(get_dal),
    security_enforcer: Any = Depends(get_security_enforcer),
    current_user: dict = Depends(get_current_user),
):
    """Save search query for later use."""
    tenant_id = get_current_tenant_id()
    user_id = get_current_user_id()

    if not tenant_id or not user_id:
        raise HTTPException(status_code=400, detail="Tenant and user context required")

    if not dal:
        raise HTTPException(status_code=503, detail="Data access layer not available")

    try:
        # Validate input
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            raise HTTPException(status_code=400, detail="Invalid input detected")

        saved_search = await dal.saved_searches.create(
            tenant_id=tenant_id,
            user_id=user_id,
            name=request.name,
            query=request.query,
            sources=request.sources,
            filters=request.filters,
            is_public=request.is_public,
            tags=request.tags,
        )

        return {
            "success": True,
            "saved_search": {
                "id": saved_search.id,
                "name": saved_search.name,
                "query": saved_search.query,
                "sources": saved_search.sources,
                "is_public": saved_search.is_public,
                "created_at": saved_search.created_at.isoformat(),
            },
            "message": "Search saved successfully",
        }

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Save search error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Save search service error")


@search_router.get("/saved")
@enforce_tenant_isolation("read", "saved_searches")
async def get_saved_searches(
    user_filter: str | None = None,
    public_only: bool = False,
    dal: Any = Depends(get_dal),
    current_user: dict = Depends(get_current_user),
):
    """Get saved searches for current tenant."""
    tenant_id = get_current_tenant_id()
    user_id = get_current_user_id()

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    if not dal:
        raise HTTPException(status_code=503, detail="Data access layer not available")

    try:
        if public_only:
            # Get public saved searches
            saved_searches = await dal.saved_searches.get_public_searches(tenant_id)
        elif user_filter:
            # Check permissions for user filtering
            if user_filter != user_id and current_user["role"] not in [
                "admin",
                "manager",
            ]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            saved_searches = await dal.saved_searches.get_by_user(
                user_filter,
                tenant_id,
            )
        else:
            # Get user's own saved searches
            saved_searches = await dal.saved_searches.get_by_user(user_id, tenant_id)

        # Convert to serializable format
        searches_data = []
        for search in saved_searches:
            searches_data.append(
                {
                    "id": search.id,
                    "name": search.name,
                    "query": search.query,
                    "sources": search.sources,
                    "filters": search.filters,
                    "is_public": search.is_public,
                    "tags": search.tags,
                    "created_at": search.created_at.isoformat(),
                    "updated_at": search.updated_at.isoformat(),
                    "user_id": search.user_id,
                },
            )

        return {
            "success": True,
            "saved_searches": searches_data,
            "total": len(searches_data),
        }

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Get saved searches error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Saved searches service error")


# Quick search endpoint for simplified queries


@search_router.post("/quick")
@enforce_tenant_isolation("search", "quick")
async def quick_search(
    request: SearchRequest,
    security_enforcer: Any = Depends(get_security_enforcer),
    current_user: dict = Depends(get_current_user),
):
    """Perform quick search with intelligent source selection.

    This endpoint automatically selects the best sources based on query analysis.
    """
    tenant_id = get_current_tenant_id()
    user_id = get_current_user_id()

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        start_time = datetime.now(UTC)

        # Validate input
        validation = await security_enforcer.validate_input_parameters(request.dict())
        if not validation["safe"]:
            raise HTTPException(status_code=400, detail="Invalid input detected")

        # Intelligent source selection based on query
        sources = await select_optimal_sources(request.query, tenant_id)

        # Create full search request
        full_request = SearchRequest(
            query=request.query,
            sources=sources,
            max_results=10,
            enable_ml_enhancement=request.enable_ml_enhancement,
            enable_summarization=request.enable_content_summarization,
        )

        # Get tenant orchestrator
        orchestrator = await get_tenant_orchestrator(tenant_id)

        # Execute search
        plan = await orchestrator.create_ingestion_plan(
            topic=full_request.query,
            context={
                "sources": full_request.sources,
                "max_results_per_source": full_request.max_results,
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )

        result = await orchestrator.execute_ingestion_plan(plan)
        execution_time_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        # Process results
        processed_results = await process_search_results(
            result,
            full_request,
            tenant_id,
            user_id,
        )

        return {
            "success": True,
            "query": request.query,
            "selected_sources": sources,
            "results": processed_results,
            "total_results": len(processed_results),
            "execution_time_ms": execution_time_ms,
            "metadata": {
                "tenant_id": tenant_id,
                "timestamp": start_time.isoformat(),
                "search_type": "quick",
            },
        }

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
        logger.error("Quick search error for tenant %s: %s", tenant_id, e)
        raise HTTPException(status_code=500, detail="Quick search service error")


# Helper functions


async def process_search_results(
    result,
    request,
    tenant_id: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Process raw search results into standardized format."""
    processed_results = []

    try:
        if hasattr(result, "content_items") and result.content_items:
            for item in result.content_items:
                if hasattr(item, "__dict__"):
                    item_dict = {
                        "title": getattr(item, "title", "Untitled"),
                        "content": getattr(item, "content", ""),
                        "url": getattr(item, "url", ""),
                        "source": getattr(item, "source", "unknown"),
                        "timestamp": getattr(
                            item,
                            "timestamp",
                            datetime.now(UTC),
                        ).isoformat(),
                        "relevance_score": getattr(item, "relevance_score", 0.0),
                        "metadata": getattr(item, "metadata", {}),
                    }

                    # Add tenant context to metadata
                    item_dict["metadata"]["tenant_id"] = tenant_id
                    item_dict["metadata"]["user_id"] = user_id

                    processed_results.append(item_dict)
                else:
                    # Handle dict-like results
                    processed_results.append(dict(item))

        return processed_results

    except (ValueError, RuntimeError) as e:
        logger.error("Error processing search results: %s", e)
        return []


async def save_search_history(
    tenant_id: str,
    user_id: str,
    query: str,
    sources: list[str],
    results_count: int,
    execution_time_ms: float,
    results: list[dict[str, Any]],
    dal: Any = Depends(get_dal),
) -> None:
    """Background task to save search history."""
    try:
        if not dal:
            return

        # Calculate quality score based on results
        quality_score = calculate_quality_score(results, execution_time_ms)

        # Save to database
        await dal.search_history.create(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            sources=sources,
            results_count=results_count,
            execution_time_ms=execution_time_ms,
            cache_hit=False,  # TODO: Implement cache hit detection
            quality_score=quality_score,
            query_metadata={
                "ml_enhanced": True,
                "result_sample": results[:3] if results else [],
            },
        )

        logger.debug("Search history saved for tenant %s", tenant_id)

    except (ValueError, RuntimeError) as e:
        logger.error("Error saving search history: %s", e)


def calculate_quality_score(
    results: list[dict[str, Any]],
    execution_time_ms: float,
) -> float:
    """Calculate search quality score based on results and performance."""
    try:
        if not results:
            return 0.0

        # Base score from result count (max 40 points)
        result_score = min(len(results) / 10 * 40, 40)

        # Performance score (max 30 points) - faster is better
        performance_score = max(0, 30 - (execution_time_ms / 1000) * 10)

        # Content quality score (max 30 points) - based on content length and relevance
        content_score = 0
        for result in results:
            if result.get("content") and len(result["content"]) > 100:
                content_score += 5
            if result.get("relevance_score", 0) > 0.7:
                content_score += 5

        content_score = min(content_score, 30)

        total_score = (result_score + performance_score + content_score) / 100
        return round(total_score, 2)

    except (ValueError, RuntimeError) as e:
        logger.error("Error calculating quality score: %s", e)
        return 0.5


async def select_optimal_sources(query: str, tenant_id: str) -> list[str]:
    """Intelligently select optimal sources based on query analysis."""
    try:
        # Default sources
        sources = ["web"]

        # Academic keywords
        academic_keywords = [
            "research",
            "study",
            "paper",
            "journal",
            "academic",
            "scientific",
            "analysis",
            "methodology",
            "experiment",
            "hypothesis",
            "theory",
        ]

        # Medical keywords
        medical_keywords = [
            "medical",
            "health",
            "disease",
            "treatment",
            "medicine",
            "clinical",
            "patient",
            "diagnosis",
            "therapy",
            "pharmaceutical",
            "drug",
        ]

        query_lower = query.lower()

        # Add academic sources for academic queries
        if any(keyword in query_lower for keyword in academic_keywords):
            sources.append("arxiv")

        # Add medical sources for medical queries
        if any(keyword in query_lower for keyword in medical_keywords):
            sources.append("pubmed")

        # Tech-related queries might benefit from additional sources
        tech_keywords = ["software", "programming", "code", "algorithm", "api"]
        if any(keyword in query_lower for keyword in tech_keywords):
            # Could add GitHub, Stack Overflow, etc.
            pass

        return sources

    except (ValueError, RuntimeError) as e:
        logger.error("Error selecting optimal sources: %s", e)
        return ["web"]  # Fallback to web only


# Additional request models


class QuickSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    enable_ml_enhancement: bool = Field(default=True)
    enable_content_summarization: bool = Field(default=False)


class SavedSearchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=1, max_length=500)
    sources: list[str] = Field(default=["web"])
    filters: dict[str, Any] | None = Field(default=None)
    is_public: bool = Field(default=False)
    tags: list[str] | None = Field(default=None)


# Search metrics

SEARCH_OPERATIONS = Counter(
    "pake_search_operations_total",
    "Total search operations",
    ["tenant_id", "sources", "ml_enhanced"],
)

SEARCH_DURATION = Histogram(
    "pake_search_duration_seconds",
    "Search operation duration",
    ["tenant_id", "sources"],
)
