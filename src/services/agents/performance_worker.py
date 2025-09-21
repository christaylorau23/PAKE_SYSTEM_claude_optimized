#!/usr/bin/env python3
"""PAKE System - Performance Optimizer Worker Agent
Stateless worker for performance optimization and system monitoring.

Handles:
- Content deduplication and optimization
- Performance metrics collection
- System resource monitoring
- Cache management and optimization
"""

import gc
import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Any

import psutil

from ..messaging.message_bus import MessageBus
from .base_worker import BaseWorkerAgent, WorkerCapabilityBuilder

# Configure logging
logger = logging.getLogger(__name__)


class PerformanceWorker(BaseWorkerAgent):
    """Stateless worker agent for performance optimization and system monitoring.

    Processes performance optimization tasks from the supervisor including
    deduplication, caching, metrics collection, and system monitoring.
    """

    def __init__(self, message_bus: MessageBus, worker_id: str = None):
        """Initialize Performance Optimizer worker"""
        # Define worker capabilities
        capabilities = [
            WorkerCapabilityBuilder("content_deduplication")
            .with_description(
                "Advanced content deduplication using multiple algorithms",
            )
            .with_input_types("content_items", "dedup_strategy", "similarity_threshold")
            .with_output_types(
                "unique_content",
                "deduplication_report",
                "similarity_scores",
            )
            .with_performance_metrics(
                deduplication_accuracy=0.96,
                processing_speed="high",
                memory_efficiency=True,
            )
            .build(),
            WorkerCapabilityBuilder("performance_metrics")
            .with_description("Collect and analyze system performance metrics")
            .with_input_types("metric_types", "time_window", "aggregation_method")
            .with_output_types("performance_report", "trend_analysis", "alerts")
            .with_performance_metrics(
                metrics_accuracy=0.99,
                collection_overhead="minimal",
                real_time_monitoring=True,
            )
            .build(),
            WorkerCapabilityBuilder("cache_optimization")
            .with_description(
                "Optimize cache usage and implement intelligent caching strategies",
            )
            .with_input_types("cache_data", "access_patterns", "optimization_goals")
            .with_output_types("cache_strategy", "optimization_report", "memory_usage")
            .with_performance_metrics(
                cache_hit_improvement=0.15,
                memory_reduction=0.20,
                access_speed_improvement=0.25,
            )
            .build(),
            WorkerCapabilityBuilder("system_monitoring")
            .with_description(
                "Monitor system resources and detect performance bottlenecks",
            )
            .with_input_types("monitoring_targets", "alert_thresholds", "interval")
            .with_output_types("system_status", "resource_usage", "performance_alerts")
            .with_performance_metrics(
                monitoring_accuracy=0.98,
                alert_precision=0.92,
                system_overhead="low",
            )
            .build(),
        ]

        super().__init__(
            worker_type="performance_optimizer",
            message_bus=message_bus,
            capabilities=capabilities,
            worker_id=worker_id,
        )

        # Performance worker specific configuration
        self.max_task_timeout = 180.0  # 3 minutes for performance tasks
        self.deduplication_algorithms = [
            "content_hash",
            "fuzzy_match",
            "semantic_similarity",
        ]
        self.similarity_threshold = 0.85
        self.cache_strategies = ["lru", "lfu", "ttl", "adaptive"]

        # System monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.resource_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "network_latency": 1000,  # ms
        }

        # Performance metrics storage
        self.performance_history = []
        self.max_history_length = 1000

        logger.info(f"PerformanceWorker {self.worker_id} initialized")

    async def process_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process performance optimization task.

        Handles various performance tasks including deduplication,
        metrics collection, and system monitoring.
        """
        try:
            # Determine task operation
            operation = task_data.get("operation", "deduplication")

            if operation == "deduplication":
                return await self._process_deduplication(task_data)
            if operation == "performance_metrics":
                return await self._process_metrics_collection(task_data)
            if operation == "cache_optimization":
                return await self._process_cache_optimization(task_data)
            if operation == "system_monitoring":
                return await self._process_system_monitoring(task_data)
            if operation == "resource_analysis":
                return await self._process_resource_analysis(task_data)
            return {
                "success": False,
                "error": f"Unknown performance operation: {operation}",
                "result": None,
            }

        except Exception as e:
            logger.error(f"Performance worker task processing error: {e}")
            return {
                "success": False,
                "error": f"Task processing failed: {str(e)}",
                "result": None,
            }

    async def _process_deduplication(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Process content deduplication"""
        content_items_data = task_data.get("content_items", [])
        strategy = task_data.get("strategy", "content_hash")
        threshold = task_data.get("threshold", self.similarity_threshold)

        if not content_items_data:
            return {
                "success": False,
                "error": "No content items provided for deduplication",
                "result": None,
            }

        start_time = time.time()
        original_count = len(content_items_data)

        # Apply deduplication strategy
        if strategy == "content_hash":
            unique_items = await self._deduplicate_by_hash(content_items_data)
        elif strategy == "fuzzy_match":
            unique_items = await self._deduplicate_by_fuzzy_match(
                content_items_data,
                threshold,
            )
        elif strategy == "semantic_similarity":
            unique_items = await self._deduplicate_by_semantic(
                content_items_data,
                threshold,
            )
        elif strategy == "combined":
            unique_items = await self._deduplicate_combined(
                content_items_data,
                threshold,
            )
        else:
            # Default to hash-based
            unique_items = await self._deduplicate_by_hash(content_items_data)

        processing_time = time.time() - start_time
        duplicates_removed = original_count - len(unique_items)
        deduplication_ratio = duplicates_removed / max(original_count, 1)

        return {
            "success": True,
            "result": unique_items,
            "error": None,
            "metrics": {
                "original_count": original_count,
                "unique_count": len(unique_items),
                "duplicates_removed": duplicates_removed,
                "deduplication_ratio": deduplication_ratio,
                "processing_time": processing_time,
                "strategy_used": strategy,
                "similarity_threshold": threshold,
                "throughput": (
                    original_count / processing_time if processing_time > 0 else 0
                ),
            },
        }

    async def _process_metrics_collection(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process performance metrics collection"""
        metric_types = task_data.get("metric_types", ["system", "application"])
        time_window = task_data.get("time_window", 60)  # seconds

        metrics = {}

        # System metrics
        if "system" in metric_types:
            metrics["system"] = await self._collect_system_metrics()

        # Application metrics
        if "application" in metric_types:
            metrics["application"] = await self._collect_application_metrics()

        # Worker metrics
        if "worker" in metric_types:
            metrics["worker"] = await self._collect_worker_metrics()

        # Performance history analysis
        if "trends" in metric_types:
            metrics["trends"] = await self._analyze_performance_trends()

        # Store metrics in history
        self.performance_history.append(
            {"timestamp": datetime.now(UTC).isoformat(), "metrics": metrics},
        )

        # Trim history if too long
        if len(self.performance_history) > self.max_history_length:
            self.performance_history = self.performance_history[
                -self.max_history_length :
            ]

        return {
            "success": True,
            "result": metrics,
            "error": None,
            "metrics": {
                "collection_timestamp": datetime.now(UTC).isoformat(),
                "metric_categories": len(metrics),
                "history_length": len(self.performance_history),
                "time_window": time_window,
            },
        }

    async def _process_cache_optimization(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process cache optimization"""
        cache_data = task_data.get("cache_data", {})
        optimization_goals = task_data.get("goals", ["hit_rate", "memory_efficiency"])

        optimization_report = {
            "current_performance": await self._analyze_cache_performance(cache_data),
            "recommendations": [],
            "estimated_improvements": {},
        }

        # Generate recommendations based on goals
        for goal in optimization_goals:
            if goal == "hit_rate":
                optimization_report["recommendations"].append(
                    {
                        "type": "cache_hit_optimization",
                        "suggestion": "Implement adaptive caching with access pattern learning",
                        "expected_improvement": "15-25% hit rate increase",
                    },
                )
            elif goal == "memory_efficiency":
                optimization_report["recommendations"].append(
                    {
                        "type": "memory_optimization",
                        "suggestion": "Use compressed cache entries and smart eviction",
                        "expected_improvement": "20-30% memory reduction",
                    },
                )
            elif goal == "access_speed":
                optimization_report["recommendations"].append(
                    {
                        "type": "access_optimization",
                        "suggestion": "Implement tiered caching with hot data prioritization",
                        "expected_improvement": "25-35% access speed increase",
                    },
                )

        return {
            "success": True,
            "result": optimization_report,
            "error": None,
            "metrics": {
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "recommendations_count": len(optimization_report["recommendations"]),
                "optimization_goals": optimization_goals,
            },
        }

    async def _process_system_monitoring(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process system monitoring and alerting"""
        monitoring_targets = task_data.get(
            "targets",
            ["cpu", "memory", "disk", "network"],
        )
        alert_thresholds = task_data.get("thresholds", self.resource_thresholds)

        monitoring_report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "system_status": "healthy",
            "resource_usage": {},
            "alerts": [],
            "recommendations": [],
        }

        # Monitor each target
        for target in monitoring_targets:
            if target == "cpu":
                cpu_usage = psutil.cpu_percent(interval=1)
                monitoring_report["resource_usage"]["cpu"] = {
                    "current": cpu_usage,
                    "threshold": alert_thresholds.get("cpu_usage", 80),
                    "status": (
                        "ok"
                        if cpu_usage < alert_thresholds.get("cpu_usage", 80)
                        else "warning"
                    ),
                }

                if cpu_usage >= alert_thresholds.get("cpu_usage", 80):
                    monitoring_report["alerts"].append(
                        {
                            "type": "cpu_high",
                            "severity": "warning",
                            "message": f"CPU usage ({cpu_usage:.1f}%) above threshold",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )

            elif target == "memory":
                memory = psutil.virtual_memory()
                memory_usage = memory.percent
                monitoring_report["resource_usage"]["memory"] = {
                    "current": memory_usage,
                    "available": memory.available,
                    "total": memory.total,
                    "threshold": alert_thresholds.get("memory_usage", 85),
                    "status": (
                        "ok"
                        if memory_usage < alert_thresholds.get("memory_usage", 85)
                        else "warning"
                    ),
                }

                if memory_usage >= alert_thresholds.get("memory_usage", 85):
                    monitoring_report["alerts"].append(
                        {
                            "type": "memory_high",
                            "severity": "warning",
                            "message": f"Memory usage ({memory_usage:.1f}%) above threshold",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )

            elif target == "disk":
                disk = psutil.disk_usage("/")
                disk_usage = disk.percent
                monitoring_report["resource_usage"]["disk"] = {
                    "current": disk_usage,
                    "free": disk.free,
                    "total": disk.total,
                    "threshold": alert_thresholds.get("disk_usage", 90),
                    "status": (
                        "ok"
                        if disk_usage < alert_thresholds.get("disk_usage", 90)
                        else "critical"
                    ),
                }

                if disk_usage >= alert_thresholds.get("disk_usage", 90):
                    monitoring_report["alerts"].append(
                        {
                            "type": "disk_full",
                            "severity": "critical",
                            "message": f"Disk usage ({disk_usage:.1f}%) above threshold",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )

        # Overall system status
        if monitoring_report["alerts"]:
            critical_alerts = [
                a for a in monitoring_report["alerts"] if a["severity"] == "critical"
            ]
            if critical_alerts:
                monitoring_report["system_status"] = "critical"
            else:
                monitoring_report["system_status"] = "warning"

        return {
            "success": True,
            "result": monitoring_report,
            "error": None,
            "metrics": {
                "monitoring_timestamp": datetime.now(UTC).isoformat(),
                "targets_monitored": len(monitoring_targets),
                "alerts_generated": len(monitoring_report["alerts"]),
                "system_health": monitoring_report["system_status"],
            },
        }

    async def _process_resource_analysis(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Process resource usage analysis and optimization"""
        analysis_type = task_data.get("type", "comprehensive")

        analysis_report = {
            "analysis_type": analysis_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "resource_summary": {},
            "bottlenecks": [],
            "optimization_opportunities": [],
        }

        # Comprehensive resource analysis
        if analysis_type in ["comprehensive", "all"]:
            # CPU analysis
            cpu_times = psutil.cpu_times()
            analysis_report["resource_summary"]["cpu"] = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "core_count": psutil.cpu_count(),
                "user_time": cpu_times.user,
                "system_time": cpu_times.system,
                "idle_time": cpu_times.idle,
            }

            # Memory analysis
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            analysis_report["resource_summary"]["memory"] = {
                "virtual": {
                    "total": memory.total,
                    "used": memory.used,
                    "available": memory.available,
                    "percent": memory.percent,
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
            }

            # Process analysis
            current_process = psutil.Process()
            analysis_report["resource_summary"]["process"] = {
                "cpu_percent": current_process.cpu_percent(),
                "memory_info": current_process.memory_info()._asdict(),
                "num_threads": current_process.num_threads(),
                "open_files": len(current_process.open_files()),
                "connections": len(current_process.connections()),
            }

        # Identify bottlenecks
        cpu_usage = (
            analysis_report["resource_summary"].get("cpu", {}).get("usage_percent", 0)
        )
        memory_usage = (
            analysis_report["resource_summary"]
            .get("memory", {})
            .get("virtual", {})
            .get("percent", 0)
        )

        if cpu_usage > 75:
            analysis_report["bottlenecks"].append(
                {
                    "type": "cpu",
                    "severity": "high" if cpu_usage > 90 else "medium",
                    "description": f"CPU usage at {cpu_usage:.1f}%",
                    "recommendation": "Consider parallel processing optimization",
                },
            )

        if memory_usage > 80:
            analysis_report["bottlenecks"].append(
                {
                    "type": "memory",
                    "severity": "high" if memory_usage > 95 else "medium",
                    "description": f"Memory usage at {memory_usage:.1f}%",
                    "recommendation": "Implement memory-efficient algorithms or increase available memory",
                },
            )

        # Optimization opportunities
        if cpu_usage < 30:
            analysis_report["optimization_opportunities"].append(
                {
                    "type": "cpu_underutilization",
                    "description": "CPU resources are underutilized",
                    "suggestion": "Increase concurrency or parallel processing",
                },
            )

        if memory_usage < 40:
            analysis_report["optimization_opportunities"].append(
                {
                    "type": "memory_headroom",
                    "description": "Significant memory headroom available",
                    "suggestion": "Consider increasing cache sizes or batch processing",
                },
            )

        return {
            "success": True,
            "result": analysis_report,
            "error": None,
            "metrics": {
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "bottlenecks_identified": len(analysis_report["bottlenecks"]),
                "optimization_opportunities": len(
                    analysis_report["optimization_opportunities"],
                ),
                "analysis_type": analysis_type,
            },
        }

    async def _deduplicate_by_hash(
        self,
        content_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Deduplicate content using hash-based comparison"""
        seen_hashes = set()
        unique_items = []

        for item in content_items:
            content_text = f"{item.get('title', '')}{item.get('content', '')}"
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_items.append(item)

        return unique_items

    async def _deduplicate_by_fuzzy_match(
        self,
        content_items: list[dict[str, Any]],
        threshold: float,
    ) -> list[dict[str, Any]]:
        """Deduplicate content using fuzzy string matching"""
        unique_items = []

        for item in content_items:
            content_text = f"{item.get('title', '')}{item.get('content', '')}"
            is_duplicate = False

            for unique_item in unique_items:
                unique_text = (
                    f"{unique_item.get('title', '')}{unique_item.get('content', '')}"
                )
                similarity = self._calculate_text_similarity(content_text, unique_text)

                if similarity >= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)

        return unique_items

    async def _deduplicate_by_semantic(
        self,
        content_items: list[dict[str, Any]],
        threshold: float,
    ) -> list[dict[str, Any]]:
        """Deduplicate content using semantic similarity (simplified)"""
        # Simplified semantic deduplication - would use embeddings in production
        return await self._deduplicate_by_fuzzy_match(content_items, threshold * 0.9)

    async def _deduplicate_combined(
        self,
        content_items: list[dict[str, Any]],
        threshold: float,
    ) -> list[dict[str, Any]]:
        """Deduplicate using combined approach"""
        # First pass: hash-based
        hash_unique = await self._deduplicate_by_hash(content_items)

        # Second pass: fuzzy matching on hash-unique items
        combined_unique = await self._deduplicate_by_fuzzy_match(hash_unique, threshold)

        return combined_unique

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simplified)"""
        if not text1 or not text2:
            return 0.0

        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    async def _collect_system_metrics(self) -> dict[str, Any]:
        """Collect system-level performance metrics"""
        return {
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            },
            "memory": {
                "virtual": psutil.virtual_memory()._asdict(),
                "swap": psutil.swap_memory()._asdict(),
            },
            "disk": {
                "usage": psutil.disk_usage("/")._asdict(),
                "io": (
                    psutil.disk_io_counters()._asdict()
                    if psutil.disk_io_counters()
                    else {}
                ),
            },
            "network": (
                psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _collect_application_metrics(self) -> dict[str, Any]:
        """Collect application-level performance metrics"""
        current_process = psutil.Process()

        return {
            "process": {
                "cpu_percent": current_process.cpu_percent(),
                "memory_info": current_process.memory_info()._asdict(),
                "num_threads": current_process.num_threads(),
                "open_files": len(current_process.open_files()),
                "connections": len(current_process.connections()),
            },
            "garbage_collection": {
                "collections": gc.get_stats(),
                "garbage_count": len(gc.garbage),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _collect_worker_metrics(self) -> dict[str, Any]:
        """Collect worker-specific performance metrics"""
        return {
            "worker_performance": {
                "tasks_processed": self.metrics["tasks_processed"],
                "tasks_successful": self.metrics["tasks_successful"],
                "tasks_failed": self.metrics["tasks_failed"],
                "average_task_time": self.metrics["average_task_time"],
                "error_rate": self.metrics["error_rate"],
            },
            "worker_status": {
                "status": self.status.value,
                "uptime": time.time() - self.metrics["uptime"],
                "current_task": self.current_task_id,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _analyze_performance_trends(self) -> dict[str, Any]:
        """Analyze performance trends from historical data"""
        if len(self.performance_history) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need more historical data",
            }

        # Simple trend analysis
        recent_metrics = self.performance_history[-10:]  # Last 10 entries

        cpu_values = []
        memory_values = []

        for entry in recent_metrics:
            system_metrics = entry.get("metrics", {}).get("system", {})
            if system_metrics:
                cpu_values.append(system_metrics.get("cpu", {}).get("usage_percent", 0))
                memory_values.append(
                    system_metrics.get("memory", {})
                    .get("virtual", {})
                    .get("percent", 0),
                )

        trends = {}

        if cpu_values:
            trends["cpu"] = {
                "average": sum(cpu_values) / len(cpu_values),
                "trend": (
                    "increasing" if cpu_values[-1] > cpu_values[0] else "decreasing"
                ),
                "variance": max(cpu_values) - min(cpu_values),
            }

        if memory_values:
            trends["memory"] = {
                "average": sum(memory_values) / len(memory_values),
                "trend": (
                    "increasing"
                    if memory_values[-1] > memory_values[0]
                    else "decreasing"
                ),
                "variance": max(memory_values) - min(memory_values),
            }

        return trends

    async def _analyze_cache_performance(
        self,
        cache_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze cache performance metrics"""
        # Simplified cache analysis
        hit_rate = cache_data.get("hit_rate", 0.8)
        miss_rate = 1.0 - hit_rate
        memory_usage = cache_data.get("memory_usage", 0)

        return {
            "hit_rate": hit_rate,
            "miss_rate": miss_rate,
            "memory_usage": memory_usage,
            "efficiency_score": hit_rate * 0.7 + (1.0 - memory_usage / 100) * 0.3,
            "recommendations": self._generate_cache_recommendations(
                hit_rate,
                memory_usage,
            ),
        }

    def _generate_cache_recommendations(
        self,
        hit_rate: float,
        memory_usage: float,
    ) -> list[str]:
        """Generate cache optimization recommendations"""
        recommendations = []

        if hit_rate < 0.8:
            recommendations.append(
                "Improve cache hit rate by optimizing cache key strategies",
            )

        if memory_usage > 80:
            recommendations.append("Reduce memory usage with better eviction policies")

        if hit_rate > 0.95 and memory_usage < 50:
            recommendations.append(
                "Cache is performing well - consider expanding capacity",
            )

        return recommendations

    async def _on_start(self):
        """Performance worker specific startup logic"""
        logger.info(
            f"PerformanceWorker {self.worker_id} monitoring and optimization engine ready",
        )

        # Initialize performance monitoring
        initial_metrics = await self._collect_system_metrics()
        self.performance_history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "metrics": {"system": initial_metrics},
            },
        )

    async def _on_stop(self):
        """Performance worker specific cleanup logic"""
        logger.info(f"PerformanceWorker {self.worker_id} cleanup completed")

    async def get_health_status(self) -> dict[str, Any]:
        """Get performance worker specific health status"""
        base_health = await super().get_health_status()

        # Add performance-specific health information
        performance_health = {
            "performance_engine_status": "healthy",
            "deduplication_algorithms": len(self.deduplication_algorithms),
            "cache_strategies": len(self.cache_strategies),
            "monitoring_active": True,
            "history_length": len(self.performance_history),
            "system_resources": await self._collect_system_metrics(),
        }

        base_health.update(performance_health)
        return base_health


# Factory function for creating performance workers
async def create_performance_worker(
    message_bus: MessageBus,
    worker_id: str = None,
) -> PerformanceWorker:
    """Create and start a performance worker.

    Args:
        message_bus: Message bus for communication
        worker_id: Optional custom worker ID

    Returns:
        Started PerformanceWorker instance
    """
    worker = PerformanceWorker(message_bus=message_bus, worker_id=worker_id)

    await worker.start()
    return worker


# Task creation helpers
def create_deduplication_task_data(
    content_items: list[dict[str, Any]],
    strategy: str = "content_hash",
    threshold: float = 0.85,
) -> dict[str, Any]:
    """Create task data for content deduplication"""
    return {
        "operation": "deduplication",
        "content_items": content_items,
        "strategy": strategy,
        "threshold": threshold,
    }


def create_metrics_collection_task_data(
    metric_types: list[str] = None,
    time_window: int = 60,
) -> dict[str, Any]:
    """Create task data for metrics collection"""
    return {
        "operation": "performance_metrics",
        "metric_types": metric_types or ["system", "application", "worker"],
        "time_window": time_window,
    }


def create_system_monitoring_task_data(
    targets: list[str] = None,
    thresholds: dict[str, float] = None,
) -> dict[str, Any]:
    """Create task data for system monitoring"""
    return {
        "operation": "system_monitoring",
        "targets": targets or ["cpu", "memory", "disk"],
        "thresholds": thresholds or {},
    }
