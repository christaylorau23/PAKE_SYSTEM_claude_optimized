"""Curation API
REST API endpoints for the intelligent content curation system.
Provides HTTP endpoints for content discovery, recommendations, and user feedback.
"""

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..integration.curation_orchestrator import (
    CurationOrchestrator,
    CurationRequest,
)
from ..models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Pydantic models for API


class CurationRequestModel(BaseModel):
    user_id: str = Field(..., description="User ID for personalization")
    query: str | None = Field(None, description="Search query")
    interests: list[str] = Field(default_factory=list, description="User interests")
    content_types: list[str] = Field(
        default_factory=list,
        description="Preferred content types",
    )
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of results")
    include_explanations: bool = Field(
        True,
        description="Include recommendation explanations",
    )
    freshness_days: int = Field(
        30,
        ge=1,
        le=365,
        description="Maximum content age in days",
    )
    min_quality_score: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum quality score",
    )


class FeedbackRequestModel(BaseModel):
    user_id: str = Field(..., description="User ID")
    content_id: str = Field(..., description="Content ID")
    feedback_type: str = Field(
        ...,
        description="Type of feedback (like, dislike, share, save, etc.)",
    )
    feedback_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional feedback data",
    )


class RecommendationModel(BaseModel):
    id: str
    content_id: str
    user_id: str
    relevance_score: float
    confidence_score: float
    reasoning: str | None
    created_at: datetime


class CurationResponseModel(BaseModel):
    request_id: str
    user_id: str
    recommendations: list[RecommendationModel]
    total_content_analyzed: int
    processing_time_ms: float
    cache_hit_rate: float
    model_confidence: float
    created_at: datetime


class SystemHealthModel(BaseModel):
    services_healthy: dict[str, bool]
    models_loaded: dict[str, bool]
    cache_status: dict[str, Any]
    performance_metrics: dict[str, float]
    last_updated: datetime


# Global orchestrator instance
orchestrator: CurationOrchestrator | None = None


def get_orchestrator() -> CurationOrchestrator:
    """Dependency to get orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        orchestrator = CurationOrchestrator()
    return orchestrator


# FastAPI app
app = FastAPI(
    title="PAKE Intelligent Content Curation API",
    description="Advanced content curation and recommendation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize the curation system on startup"""
    global orchestrator
    logger.info("Starting PAKE Curation API")

    orchestrator = CurationOrchestrator()
    success = await orchestrator.initialize()

    if not success:
        logger.error("Failed to initialize curation system")
        raise Exception("Curation system initialization failed")

    logger.info("PAKE Curation API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the curation system"""
    global orchestrator
    if orchestrator:
        await orchestrator.shutdown()
    logger.info("PAKE Curation API shutdown")


@app.get("/health", response_model=SystemHealthModel)
async def health_check(orch: CurationOrchestrator = Depends(get_orchestrator)):
    """Get system health status"""
    try:
        health = await orch.get_system_health()
        return SystemHealthModel(**asdict(health))
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post("/curate", response_model=CurationResponseModel)
async def curate_content(
    request: CurationRequestModel,
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Get personalized content recommendations"""
    try:
        # Convert Pydantic model to dataclass
        curation_request = CurationRequest(
            user_id=request.user_id,
            query=request.query,
            interests=request.interests,
            content_types=request.content_types,
            max_results=request.max_results,
            include_explanations=request.include_explanations,
            freshness_days=request.freshness_days,
            min_quality_score=request.min_quality_score,
        )

        # Process curation request
        response = await orch.curate_content(curation_request)

        # Convert recommendations to Pydantic models
        recommendation_models = [
            RecommendationModel(
                id=rec.id,
                content_id=rec.content_id,
                user_id=rec.user_id,
                relevance_score=rec.relevance_score,
                confidence_score=rec.confidence_score,
                reasoning=rec.reasoning,
                created_at=rec.created_at,
            )
            for rec in response.recommendations
        ]

        return CurationResponseModel(
            request_id=response.request_id,
            user_id=response.user_id,
            recommendations=recommendation_models,
            total_content_analyzed=response.total_content_analyzed,
            processing_time_ms=response.processing_time_ms,
            cache_hit_rate=response.cache_hit_rate,
            model_confidence=response.model_confidence,
            created_at=response.created_at,
        )

    except Exception as e:
        logger.error(f"Error processing curation request: {e}")
        raise HTTPException(status_code=500, detail=f"Curation failed: {str(e)}")


@app.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequestModel,
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Submit user feedback for learning"""
    try:
        success = await orch.process_user_feedback(
            user_id=feedback.user_id,
            content_id=feedback.content_id,
            feedback_type=feedback.feedback_type,
            feedback_data=feedback.feedback_data,
        )

        if success:
            return {"status": "success", "message": "Feedback processed successfully"}
        raise HTTPException(status_code=400, detail="Failed to process feedback")

    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Feedback processing failed: {str(e)}",
        )


@app.get("/recommendations/{user_id}")
async def get_user_recommendations(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    content_types: str | None = Query(
        None,
        description="Comma-separated content types",
    ),
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Get recommendations for a specific user"""
    try:
        # Parse content types
        content_types_list = []
        if content_types:
            content_types_list = [ct.strip() for ct in content_types.split(",")]

        # Create curation request
        request = CurationRequest(
            user_id=user_id,
            max_results=limit,
            content_types=content_types_list,
        )

        # Get recommendations
        response = await orch.curate_content(request)

        return {
            "user_id": user_id,
            "recommendations": [
                {
                    "content_id": rec.content_id,
                    "relevance_score": rec.relevance_score,
                    "confidence_score": rec.confidence_score,
                    "reasoning": rec.reasoning,
                }
                for rec in response.recommendations
            ],
            "total_recommendations": len(response.recommendations),
            "processing_time_ms": response.processing_time_ms,
        }

    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}",
        )


@app.post("/retrain")
async def retrain_models(
    force: bool = Query(
        False,
        description="Force retraining even if models are recent",
    ),
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Retrain ML models with latest data"""
    try:
        results = await orch.retrain_models(force_retrain=force)

        if results.get("retrained"):
            return {
                "status": "success",
                "message": "Models retrained successfully",
                "results": results.get("results", {}),
            }
        return {
            "status": "skipped",
            "message": results.get("reason", "Retraining not needed"),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error retraining models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model retraining failed: {str(e)}",
        )


@app.get("/stats")
async def get_system_stats(orch: CurationOrchestrator = Depends(get_orchestrator)):
    """Get system performance statistics"""
    try:
        health = await orch.get_system_health()

        return {
            "system_health": {
                "services_healthy": health.services_healthy,
                "models_loaded": health.models_loaded,
            },
            "performance": health.performance_metrics,
            "cache": health.cache_status,
            "last_updated": health.last_updated,
        }

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/content/{content_id}/quality")
async def get_content_quality(
    content_id: str,
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Get quality score for specific content"""
    try:
        # This would typically fetch content from database
        # For now, return a placeholder response
        return {
            "content_id": content_id,
            "quality_score": 0.0,
            "message": "Content quality analysis not yet implemented",
        }

    except Exception as e:
        logger.error(f"Error getting content quality for {content_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get content quality: {str(e)}",
        )


@app.get("/user/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Get user profile and preferences"""
    try:
        # Get user profile from orchestrator
        user_profile = await orch._get_user_profile(user_id)

        return {
            "user_id": user_profile.user_id,
            "interests": user_profile.interests,
            "preference_weights": user_profile.preference_weights,
            "learning_rate": user_profile.learning_rate,
            "exploration_factor": user_profile.exploration_factor,
            "created_at": user_profile.created_at,
            "updated_at": user_profile.updated_at,
        }

    except Exception as e:
        logger.error(f"Error getting user profile for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user profile: {str(e)}",
        )


@app.put("/user/{user_id}/profile")
async def update_user_profile(
    user_id: str,
    interests: list[str] | None = Body(None),
    preference_weights: dict[str, float] | None = Body(None),
    orch: CurationOrchestrator = Depends(get_orchestrator),
):
    """Update user profile and preferences"""
    try:
        # Get current profile
        current_profile = await orch._get_user_profile(user_id)

        # Update fields
        updated_interests = (
            interests if interests is not None else current_profile.interests
        )
        updated_weights = (
            preference_weights
            if preference_weights is not None
            else current_profile.preference_weights
        )

        # Create updated profile
        updated_profile = UserProfile(
            user_id=user_id,
            interests=updated_interests,
            preference_weights=updated_weights,
            learning_rate=current_profile.learning_rate,
            exploration_factor=current_profile.exploration_factor,
            created_at=current_profile.created_at,
            updated_at=datetime.now(),
        )

        # Update in user preference service
        await orch.user_preference_service.update_user_profile(updated_profile)

        return {
            "status": "success",
            "message": "User profile updated successfully",
            "profile": {
                "user_id": updated_profile.user_id,
                "interests": updated_profile.interests,
                "preference_weights": updated_profile.preference_weights,
                "updated_at": updated_profile.updated_at,
            },
        }

    except Exception as e:
        logger.error(f"Error updating user profile for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user profile: {str(e)}",
        )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "PAKE Intelligent Content Curation API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "curate": "/curate",
            "feedback": "/feedback",
            "recommendations": "/recommendations/{user_id}",
            "retrain": "/retrain",
            "stats": "/stats",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the API server
    uvicorn.run(
        "curation_api:app",
        host="127.0.0.1",
        port=8001,  # Different port from main PAKE system
        reload=True,
        log_level="info",
    )
