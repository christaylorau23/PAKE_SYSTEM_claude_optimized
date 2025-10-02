#!/usr/bin/env python3
"""PAKE System - Ingestion Plan Builder
Single Responsibility: Building and validating ingestion plans
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..interfaces import (
    IngestionSource,
    IngestionPlan,
    SourceType,
    IngestionStatus,
    IngestionPlanBuilderInterface,
)
from ..shared_utils import (
    extract_search_terms,
    calculate_duration_estimate,
    validate_source_config,
)


@dataclass
class PlanBuilderConfig:
    """Configuration for plan builder"""
    max_sources_per_plan: int = 10
    default_timeout: int = 300
    default_priority: int = 5
    enable_validation: bool = True


class IngestionPlanBuilder(IngestionPlanBuilderInterface):
    """Single Responsibility: Building and validating ingestion plans"""
    
    def __init__(self, config: PlanBuilderConfig | None = None):
        self.config = config or PlanBuilderConfig()
    
    def build_plan(
        self,
        topic: str,
        source_configs: list[dict[str, Any]],
        user_preferences: dict[str, Any] | None = None,
    ) -> IngestionPlan:
        """Build a comprehensive ingestion plan from source configurations"""
        
        # Validate inputs
        if not topic or not source_configs:
            raise ValueError("Topic and source configurations are required")
        
        if len(source_configs) > self.config.max_sources_per_plan:
            raise ValueError(f"Too many sources (max: {self.config.max_sources_per_plan})")
        
        # Build sources
        sources = []
        total_estimated_results = 0
        
        for config in source_configs:
            source = self._build_source(config)
            sources.append(source)
            total_estimated_results += source.estimated_results
        
        # Calculate estimated duration
        estimated_duration = self._calculate_duration(sources)
        
        # Create plan
        plan = IngestionPlan(
            topic=topic,
            sources=sources,
            total_sources=len(sources),
            estimated_total_results=total_estimated_results,
            estimated_duration=estimated_duration,
            plan_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
        )
        
        # Validate plan if enabled
        if self.config.enable_validation:
            self._validate_plan(plan)
        
        return plan
    
    def _build_source(self, config: dict[str, Any]) -> IngestionSource:
        """Build a single ingestion source from configuration"""
        
        # Extract required fields
        source_type = config.get("source_type", "web")
        query_parameters = config.get("query_parameters", {})
        estimated_results = config.get("estimated_results", 10)
        
        # Extract optional fields with defaults
        priority = config.get("priority", self.config.default_priority)
        timeout = config.get("timeout", self.config.default_timeout)
        
        # Validate source type
        try:
            SourceType(source_type)
        except ValueError:
            raise ValueError(f"Invalid source type: {source_type}")
        
        return IngestionSource(
            source_type=source_type,
            priority=priority,
            query_parameters=query_parameters,
            estimated_results=estimated_results,
            timeout=timeout,
            source_id=str(uuid.uuid4()),
            status=IngestionStatus.PENDING,
        )
    
    def _calculate_duration(self, sources: list[IngestionSource]) -> int:
        """Calculate estimated total duration for all sources"""
        
        # Base duration per source type (seconds)
        duration_map = {
            "web": 30,
            "arxiv": 45,
            "pubmed": 60,
            "rss": 20,
            "email": 15,
            "social": 25,
        }
        
        total_duration = 0
        for source in sources:
            base_duration = duration_map.get(source.source_type, 30)
            # Adjust based on estimated results
            adjusted_duration = base_duration + (source.estimated_results * 2)
            total_duration += adjusted_duration
        
        return total_duration
    
    def _validate_plan(self, plan: IngestionPlan) -> None:
        """Validate the ingestion plan"""
        
        # Check plan constraints
        if plan.total_sources == 0:
            raise ValueError("Plan must have at least one source")
        
        if plan.estimated_total_results == 0:
            raise ValueError("Plan must have estimated results > 0")
        
        if plan.estimated_duration <= 0:
            raise ValueError("Plan must have positive estimated duration")
        
        # Check source constraints
        for source in plan.sources:
            if not source.query_parameters:
                raise ValueError(f"Source {source.source_id} must have query parameters")
            
            if source.estimated_results <= 0:
                raise ValueError(f"Source {source.source_id} must have estimated results > 0")
            
            if source.timeout <= 0:
                raise ValueError(f"Source {source.source_id} must have positive timeout")
    
    def optimize_plan(self, plan: IngestionPlan) -> IngestionPlan:
        """Optimize the ingestion plan for better performance"""
        
        # Sort sources by priority (higher priority first)
        sorted_sources = sorted(
            plan.sources,
            key=lambda s: s.priority,
            reverse=True
        )
        
        # Create optimized plan
        optimized_plan = IngestionPlan(
            topic=plan.topic,
            sources=sorted_sources,
            total_sources=plan.total_sources,
            estimated_total_results=plan.estimated_total_results,
            estimated_duration=plan.estimated_duration,
            plan_id=plan.plan_id,
            created_at=plan.created_at,
        )
        
        return optimized_plan
