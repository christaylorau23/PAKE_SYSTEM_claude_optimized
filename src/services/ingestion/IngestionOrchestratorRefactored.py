#!/usr/bin/env python3
"""PAKE System - Refactored Ingestion Orchestrator (SRP Compliant)
Single Responsibility: Orchestrating multi-source content ingestion workflow

This orchestrator now follows SRP by delegating specific responsibilities to focused managers:
- Plan Building: IngestionPlanBuilder
- Source Execution: SourceExecutor
- Caching: IngestionCacheManager (to be implemented)
- Error Handling: IngestionErrorHandler (to be implemented)
- Metrics Collection: IngestionMetricsCollector (to be implemented)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .interfaces import (
    IngestionPlan,
    IngestionResult,
    IngestionStatus,
    IngestionPlanBuilderInterface,
    SourceExecutorInterface,
)
from .shared_utils import (
    format_execution_metrics,
    create_error_detail,
    merge_content_items,
)
from .managers.IngestionPlanBuilder import IngestionPlanBuilder, PlanBuilderConfig
from .managers.SourceExecutor import SourceExecutor

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for ingestion orchestrator"""
    max_concurrent_sources: int = 5
    timeout_per_source: int = 300
    enable_retry: bool = True
    max_retries: int = 2
    enable_caching: bool = True
    cache_ttl_hours: int = 24


class IngestionOrchestratorRefactored:
    """Refactored orchestrator following Single Responsibility Principle"""
    
    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        plan_builder: IngestionPlanBuilderInterface | None = None,
        source_executor: SourceExecutorInterface | None = None,
    ):
        self.config = config or OrchestratorConfig()
        
        # Use dependency injection for managers
        self.plan_builder = plan_builder or IngestionPlanBuilder(
            PlanBuilderConfig(
                max_sources_per_plan=self.config.max_concurrent_sources,
                default_timeout=self.config.timeout_per_source,
            )
        )
        self.source_executor = source_executor or SourceExecutor()
        
        # Performance tracking
        self._stats = {
            "plans_executed": 0,
            "sources_processed": 0,
            "total_items_retrieved": 0,
            "successful_sources": 0,
            "failed_sources": 0,
            "average_execution_time_ms": 0.0,
            "last_execution": None,
        }
    
    async def execute_ingestion_plan(
        self,
        plan: IngestionPlan,
        user_id: str | None = None,
    ) -> IngestionResult:
        """Execute ingestion plan using decomposed managers"""
        
        start_time = time.time()
        logger.info(f"Starting ingestion plan execution", {
            "plan_id": plan.plan_id,
            "topic": plan.topic,
            "total_sources": plan.total_sources,
        })
        
        # Initialize result
        result = IngestionResult(
            plan_id=plan.plan_id,
            success=False,
            total_sources=plan.total_sources,
            sources_attempted=plan.total_sources,
            successful_sources=0,
            failed_sources=0,
            total_items_retrieved=0,
            execution_time_ms=0,
            created_at=datetime.now(UTC),
        )
        
        try:
            # Execute sources concurrently
            source_results = await self._execute_sources_concurrently(plan)
            
            # Process results
            self._process_source_results(source_results, result)
            
            # Update statistics
            self._update_statistics(result, start_time)
            
            result.success = result.failed_sources == 0 or result.successful_sources > 0
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Ingestion plan completed", {
                "plan_id": plan.plan_id,
                "success": result.success,
                "successful_sources": result.successful_sources,
                "failed_sources": result.failed_sources,
                "total_items": result.total_items_retrieved,
                "execution_time_ms": result.execution_time_ms,
            })
            
        except Exception as e:
            result.success = False
            result.execution_time_ms = (time.time() - start_time) * 1000
            result.error = str(e)
            
            logger.error(f"Ingestion plan failed", {
                "plan_id": plan.plan_id,
                "error": str(e),
            })
        
        return result
    
    async def _execute_sources_concurrently(
        self,
        plan: IngestionPlan,
    ) -> list[tuple[list[Any], dict[str, Any]]]:
        """Execute all sources concurrently using asyncio"""
        
        # Create tasks for concurrent execution
        tasks = []
        for source in plan.sources:
            task = asyncio.create_task(
                self.source_executor.execute_source(source, plan)
            )
            tasks.append(task)
        
        # Execute with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout_per_source * len(plan.sources),
            )
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Source execution failed", {
                        "source_id": plan.sources[i].source_id,
                        "error": str(result),
                    })
                    processed_results.append(([], {
                        "source_id": plan.sources[i].source_id,
                        "success": False,
                        "error": str(result),
                    }))
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error("Ingestion plan timed out")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise
    
    def _process_source_results(
        self,
        source_results: list[tuple[list[Any], dict[str, Any]]],
        result: IngestionResult,
    ) -> None:
        """Process results from source executions"""
        
        for content_items, metrics in source_results:
            if metrics.get("success", False):
                result.successful_sources += 1
                result.total_items_retrieved += len(content_items)
                result.content_items.extend(content_items)
            else:
                result.failed_sources += 1
                if metrics.get("error"):
                    result.errors.append(metrics["error"])
    
    def _update_statistics(
        self,
        result: IngestionResult,
        start_time: float,
    ) -> None:
        """Update orchestrator statistics"""
        
        self._stats["plans_executed"] += 1
        self._stats["sources_processed"] += result.total_sources
        self._stats["total_items_retrieved"] += result.total_items_retrieved
        self._stats["successful_sources"] += result.successful_sources
        self._stats["failed_sources"] += result.failed_sources
        self._stats["last_execution"] = datetime.now(UTC)
        
        # Update average execution time
        if self._stats["plans_executed"] > 0:
            total_time = self._stats.get("total_execution_time_ms", 0) + result.execution_time_ms
            self._stats["total_execution_time_ms"] = total_time
            self._stats["average_execution_time_ms"] = total_time / self._stats["plans_executed"]
    
    def get_statistics(self) -> dict[str, Any]:
        """Get orchestrator statistics"""
        return self._stats.copy()
    
    def create_plan_from_config(
        self,
        topic: str,
        source_configs: list[dict[str, Any]],
        user_preferences: dict[str, Any] | None = None,
    ) -> IngestionPlan:
        """Create an ingestion plan using the plan builder"""
        
        return self.plan_builder.build_plan(
            topic=topic,
            source_configs=source_configs,
            user_preferences=user_preferences,
        )
    
    def optimize_plan(self, plan: IngestionPlan) -> IngestionPlan:
        """Optimize an ingestion plan using the plan builder"""
        
        return self.plan_builder.optimize_plan(plan)
    
    async def health_check(self) -> dict[str, Any]:
        """Perform health check on orchestrator and its components"""
        
        health_status = {
            "orchestrator": "healthy",
            "plan_builder": "healthy",
            "source_executor": "healthy",
            "statistics": self._stats,
            "config": {
                "max_concurrent_sources": self.config.max_concurrent_sources,
                "timeout_per_source": self.config.timeout_per_source,
                "enable_retry": self.config.enable_retry,
                "max_retries": self.config.max_retries,
            },
        }
        
        return health_status
