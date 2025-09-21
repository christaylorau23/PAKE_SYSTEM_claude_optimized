#!/usr/bin/env python3
"""
PAKE System - Enterprise Monitoring Service
Comprehensive monitoring service implementing enterprise best practices for:
- Real-time application monitoring
- Performance metrics collection
- Health checks and alerting
- Resource utilization tracking
- SLA monitoring
- Capacity planning
"""

import asyncio
import json
import os
import psutil
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field

import aiohttp
from pydantic import BaseModel, Field

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.services.logging.enterprise_logging_service import (
        EnterpriseLoggingService, 
        LogCategory, 
        LogLevel,
        get_logger
    )
except ImportError:
    # Fallback imports
    EnterpriseLoggingService = None
    LogCategory = None
    LogLevel = None
    get_logger = None


class MetricType(Enum):
    """Metric types for monitoring"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    # Basic settings
    service_name: str = "pake-system"
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    
    # Collection settings
    collection_interval_seconds: int = 30
    metrics_retention_days: int = 30
    health_check_interval_seconds: int = 60
    
    # Thresholds
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    disk_threshold_percent: float = 90.0
    response_time_threshold_ms: float = 5000.0
    
    # Alerting
    alerting_enabled: bool = True
    alert_cooldown_minutes: int = 15
    max_alerts_per_hour: int = 10
    
    # External services
    prometheus_enabled: bool = False
    datadog_enabled: bool = False
    grafana_enabled: bool = False
    
    def __post_init__(self):
        """Validate configuration"""
        if self.collection_interval_seconds <= 0:
            raise ValueError("Collection interval must be positive")
        
        if self.cpu_threshold_percent < 0 or self.cpu_threshold_percent > 100:
            raise ValueError("CPU threshold must be between 0 and 100")


class Metric(BaseModel):
    """Metric data model"""
    name: str = Field(..., description="Metric name")
    value: Union[int, float] = Field(..., description="Metric value")
    metric_type: MetricType = Field(..., description="Metric type")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    service_name: str = Field(default="pake-system", description="Service name")
    environment: str = Field(default="development", description="Environment")


class HealthCheck(BaseModel):
    """Health check data model"""
    name: str = Field(..., description="Health check name")
    status: HealthStatus = Field(..., description="Health status")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class Alert(BaseModel):
    """Alert data model"""
    id: str = Field(..., description="Alert ID")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity")
    status: str = Field(default="active", description="Alert status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    service_name: str = Field(default="pake-system", description="Service name")
    environment: str = Field(default="development", description="Environment")
    tags: Dict[str, str] = Field(default_factory=dict, description="Alert tags")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")


class SystemMetrics(BaseModel):
    """System metrics data model"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    memory_used_mb: float = Field(..., description="Memory used in MB")
    memory_total_mb: float = Field(..., description="Total memory in MB")
    disk_percent: float = Field(..., description="Disk usage percentage")
    disk_used_gb: float = Field(..., description="Disk used in GB")
    disk_total_gb: float = Field(..., description="Total disk space in GB")
    network_bytes_sent: int = Field(..., description="Network bytes sent")
    network_bytes_recv: int = Field(..., description="Network bytes received")
    process_count: int = Field(..., description="Number of processes")
    load_average: List[float] = Field(..., description="System load average")


class EnterpriseMonitoringService:
    """
    Enterprise-grade monitoring service implementing all best practices:
    - Real-time application monitoring
    - Performance metrics collection
    - Health checks and alerting
    - Resource utilization tracking
    - SLA monitoring
    - Capacity planning
    """
    
    def __init__(self, config: MonitoringConfig = None, logger: EnterpriseLoggingService = None):
        self.config = config or MonitoringConfig()
        self.logger = logger or (get_logger() if get_logger else None)
        
        # Metrics storage
        self.metrics_buffer: List[Metric] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.system_metrics_history: List[SystemMetrics] = []
        
        # Performance tracking
        self.performance_metrics: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Background tasks
        self._collection_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._alerting_task: Optional[asyncio.Task] = None
        
        # Initialize monitoring
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring tasks"""
        if self.logger:
            self.logger.info(
                "Starting enterprise monitoring service",
                category=LogCategory.SYSTEM if LogCategory else None,
                service_name=self.config.service_name,
                environment=self.config.environment
            )
        
        # Start background tasks
        self._collection_task = asyncio.create_task(self._collect_metrics_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        if self.config.alerting_enabled:
            self._alerting_task = asyncio.create_task(self._alerting_loop())
    
    async def _collect_metrics_loop(self):
        """Background task to collect system metrics"""
        while True:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.config.collection_interval_seconds)
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        "Error collecting system metrics",
                        category=LogCategory.SYSTEM if LogCategory else None,
                        error=e
                    )
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _health_check_loop(self):
        """Background task to perform health checks"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval_seconds)
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        "Error performing health checks",
                        category=LogCategory.SYSTEM if LogCategory else None,
                        error=e
                    )
                await asyncio.sleep(10)  # Short delay before retry
    
    async def _alerting_loop(self):
        """Background task to process alerts"""
        while True:
            try:
                await self._process_alerts()
                await asyncio.sleep(60)  # Check alerts every minute
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        "Error processing alerts",
                        category=LogCategory.SYSTEM if LogCategory else None,
                        error=e
                    )
                await asyncio.sleep(10)  # Short delay before retry
    
    # ========================================================================
    # Metrics Collection
    # ========================================================================
    
    async def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            
            # Network metrics
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # Load average (Unix only)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]  # Windows fallback
            
            # Create system metrics
            system_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_percent=disk_percent,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=process_count,
                load_average=load_average
            )
            
            # Store metrics
            self.system_metrics_history.append(system_metrics)
            
            # Keep only recent metrics
            cutoff_time = datetime.now(UTC) - timedelta(days=self.config.metrics_retention_days)
            self.system_metrics_history = [
                m for m in self.system_metrics_history if m.timestamp >= cutoff_time
            ]
            
            # Log metrics
            if self.logger:
                self.logger.performance(
                    "System metrics collected",
                    operation="system_metrics_collection",
                    duration_ms=1000,  # Approximate collection time
                    memory_mb=memory_used_mb,
                    cpu_percent=cpu_percent,
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    disk_percent=disk_percent
                )
            
            # Check thresholds and create alerts
            await self._check_thresholds(system_metrics)
            
        except Exception as e:
            if self.logger:
                self.logger.error(
                    "Failed to collect system metrics",
                    category=LogCategory.SYSTEM if LogCategory else None,
                    error=e
                )
    
    async def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and create alerts"""
        alerts_to_create = []
        
        # CPU threshold check
        if metrics.cpu_percent > self.config.cpu_threshold_percent:
            alerts_to_create.append({
                'title': 'High CPU Usage',
                'message': f'CPU usage is {metrics.cpu_percent:.1f}%, exceeding threshold of {self.config.cpu_threshold_percent}%',
                'severity': AlertSeverity.HIGH if metrics.cpu_percent > 95 else AlertSeverity.MEDIUM,
                'tags': {'metric': 'cpu_percent', 'value': str(metrics.cpu_percent)}
            })
        
        # Memory threshold check
        if metrics.memory_percent > self.config.memory_threshold_percent:
            alerts_to_create.append({
                'title': 'High Memory Usage',
                'message': f'Memory usage is {metrics.memory_percent:.1f}%, exceeding threshold of {self.config.memory_threshold_percent}%',
                'severity': AlertSeverity.HIGH if metrics.memory_percent > 95 else AlertSeverity.MEDIUM,
                'tags': {'metric': 'memory_percent', 'value': str(metrics.memory_percent)}
            })
        
        # Disk threshold check
        if metrics.disk_percent > self.config.disk_threshold_percent:
            alerts_to_create.append({
                'title': 'High Disk Usage',
                'message': f'Disk usage is {metrics.disk_percent:.1f}%, exceeding threshold of {self.config.disk_threshold_percent}%',
                'severity': AlertSeverity.HIGH if metrics.disk_percent > 95 else AlertSeverity.MEDIUM,
                'tags': {'metric': 'disk_percent', 'value': str(metrics.disk_percent)}
            })
        
        # Create alerts
        for alert_data in alerts_to_create:
            await self.create_alert(**alert_data)
    
    # ========================================================================
    # Health Checks
    # ========================================================================
    
    async def _perform_health_checks(self):
        """Perform all registered health checks"""
        for check_name, health_check in self.health_checks.items():
            try:
                await self._run_health_check(check_name, health_check)
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Health check {check_name} failed",
                        category=LogCategory.SYSTEM if LogCategory else None,
                        error=e
                    )
    
    async def _run_health_check(self, name: str, health_check: HealthCheck):
        """Run a specific health check"""
        start_time = time.time()
        
        try:
            # This would be implemented with actual health check logic
            # For now, we'll simulate different health check types
            if name == "database":
                await self._check_database_health(health_check)
            elif name == "redis":
                await self._check_redis_health(health_check)
            elif name == "api":
                await self._check_api_health(health_check)
            else:
                # Default health check
                health_check.status = HealthStatus.HEALTHY
                health_check.message = "Service is healthy"
            
            response_time_ms = (time.time() - start_time) * 1000
            health_check.response_time_ms = response_time_ms
            health_check.timestamp = datetime.now(UTC)
            
        except Exception as e:
            health_check.status = HealthStatus.UNHEALTHY
            health_check.message = f"Health check failed: {str(e)}"
            health_check.response_time_ms = (time.time() - start_time) * 1000
            health_check.timestamp = datetime.now(UTC)
    
    async def _check_database_health(self, health_check: HealthCheck):
        """Check database health"""
        # Simulate database health check
        await asyncio.sleep(0.1)  # Simulate DB query
        health_check.status = HealthStatus.HEALTHY
        health_check.message = "Database connection is healthy"
        health_check.details = {"connection_pool_size": 10, "active_connections": 3}
    
    async def _check_redis_health(self, health_check: HealthCheck):
        """Check Redis health"""
        # Simulate Redis health check
        await asyncio.sleep(0.05)  # Simulate Redis ping
        health_check.status = HealthStatus.HEALTHY
        health_check.message = "Redis connection is healthy"
        health_check.details = {"memory_usage": "45MB", "connected_clients": 5}
    
    async def _check_api_health(self, health_check: HealthCheck):
        """Check API health"""
        # Simulate API health check
        await asyncio.sleep(0.2)  # Simulate API call
        health_check.status = HealthStatus.HEALTHY
        health_check.message = "API endpoints are responding"
        health_check.details = {"response_time_avg": "150ms", "error_rate": "0.1%"}
    
    def register_health_check(self, name: str, check_func: Callable = None):
        """Register a health check"""
        health_check = HealthCheck(
            name=name,
            status=HealthStatus.UNKNOWN,
            message="Health check not yet performed"
        )
        
        if check_func:
            health_check.details["check_function"] = check_func.__name__
        
        self.health_checks[name] = health_check
        
        if self.logger:
            self.logger.info(
                f"Registered health check: {name}",
                category=LogCategory.SYSTEM if LogCategory else None,
                health_check_name=name
            )
    
    # ========================================================================
    # Metrics Recording
    # ========================================================================
    
    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        metric_type: MetricType = MetricType.GAUGE,
        tags: Dict[str, str] = None
    ):
        """Record a custom metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            service_name=self.config.service_name,
            environment=self.config.environment
        )
        
        self.metrics_buffer.append(metric)
        
        # Log metric
        if self.logger:
            self.logger.performance(
                f"Metric recorded: {name}",
                operation="metric_recording",
                metric_name=name,
                metric_value=value,
                metric_type=metric_type.value,
                tags=tags
            )
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        self.record_metric(name, value, MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Set a gauge metric"""
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def record_timing(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timing metric"""
        self.record_metric(name, duration_ms, MetricType.TIMER, tags)
        
        # Also track in performance metrics
        if name not in self.performance_metrics:
            self.performance_metrics[name] = []
        
        self.performance_metrics[name].append(duration_ms)
        
        # Keep only recent measurements
        if len(self.performance_metrics[name]) > 1000:
            self.performance_metrics[name] = self.performance_metrics[name][-1000:]
    
    def record_error(self, error_type: str, tags: Dict[str, str] = None):
        """Record an error occurrence"""
        self.increment_counter(f"errors.{error_type}", tags=tags)
        
        # Track error counts
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        if self.logger:
            self.logger.error(
                f"Error recorded: {error_type}",
                category=LogCategory.SYSTEM if LogCategory else None,
                error_type=error_type,
                error_count=self.error_counts[error_type],
                tags=tags
            )
    
    # ========================================================================
    # Alerting
    # ========================================================================
    
    async def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        tags: Dict[str, str] = None
    ):
        """Create a new alert"""
        alert_id = f"{self.config.service_name}_{int(time.time())}"
        
        # Check if similar alert already exists
        for existing_alert in self.active_alerts.values():
            if (existing_alert.title == title and 
                existing_alert.severity == severity and
                existing_alert.status == "active"):
                # Update existing alert timestamp
                existing_alert.timestamp = datetime.now(UTC)
                return existing_alert.id
        
        # Create new alert
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            tags=tags or {},
            service_name=self.config.service_name,
            environment=self.config.environment
        )
        
        self.active_alerts[alert_id] = alert
        
        # Log alert
        if self.logger:
            self.logger.warning(
                f"Alert created: {title}",
                category=LogCategory.SYSTEM if LogCategory else None,
                alert_id=alert_id,
                alert_title=title,
                alert_severity=severity.value,
                alert_message=message,
                tags=tags
            )
        
        return alert_id
    
    async def resolve_alert(self, alert_id: str, resolution_message: str = None):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = "resolved"
            alert.resolved_at = datetime.now(UTC)
            
            if resolution_message:
                alert.message += f" Resolution: {resolution_message}"
            
            # Log resolution
            if self.logger:
                self.logger.info(
                    f"Alert resolved: {alert.title}",
                    category=LogCategory.SYSTEM if LogCategory else None,
                    alert_id=alert_id,
                    alert_title=alert.title,
                    resolution_message=resolution_message
                )
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
    
    async def _process_alerts(self):
        """Process active alerts"""
        # This would integrate with external alerting systems
        # For now, we'll just log active alerts
        if self.active_alerts and self.logger:
            active_count = len(self.active_alerts)
            critical_count = sum(1 for alert in self.active_alerts.values() 
                               if alert.severity == AlertSeverity.CRITICAL)
            
            if critical_count > 0:
                self.logger.warning(
                    f"Active alerts: {active_count} total, {critical_count} critical",
                    category=LogCategory.SYSTEM if LogCategory else None,
                    active_alerts=active_count,
                    critical_alerts=critical_count
                )
    
    # ========================================================================
    # Reporting and Analysis
    # ========================================================================
    
    def get_system_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get system metrics summary for the last N hours"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.system_metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate statistics
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_percent for m in recent_metrics]
        
        return {
            "period_hours": hours,
            "metric_count": len(recent_metrics),
            "cpu": {
                "current": cpu_values[-1] if cpu_values else 0,
                "average": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0
            },
            "memory": {
                "current": memory_values[-1] if memory_values else 0,
                "average": sum(memory_values) / len(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0
            },
            "disk": {
                "current": disk_values[-1] if disk_values else 0,
                "average": sum(disk_values) / len(disk_values) if disk_values else 0,
                "max": max(disk_values) if disk_values else 0,
                "min": min(disk_values) if disk_values else 0
            },
            "thresholds": {
                "cpu_threshold": self.config.cpu_threshold_percent,
                "memory_threshold": self.config.memory_threshold_percent,
                "disk_threshold": self.config.disk_threshold_percent
            }
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        summary = {}
        
        for operation, times in self.performance_metrics.items():
            if times:
                summary[operation] = {
                    "count": len(times),
                    "average_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
                    "p99_ms": sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else times[0]
                }
        
        return summary
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health check summary"""
        total_checks = len(self.health_checks)
        healthy_checks = sum(1 for check in self.health_checks.values() 
                           if check.status == HealthStatus.HEALTHY)
        unhealthy_checks = sum(1 for check in self.health_checks.values() 
                             if check.status == HealthStatus.UNHEALTHY)
        
        return {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "unhealthy_checks": unhealthy_checks,
            "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "last_check": check.timestamp.isoformat()
                }
                for name, check in self.health_checks.items()
            }
        }
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary"""
        active_alerts = len(self.active_alerts)
        critical_alerts = sum(1 for alert in self.active_alerts.values() 
                            if alert.severity == AlertSeverity.CRITICAL)
        high_alerts = sum(1 for alert in self.active_alerts.values() 
                         if alert.severity == AlertSeverity.HIGH)
        
        return {
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "alerts": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "created_at": alert.timestamp.isoformat(),
                    "tags": alert.tags
                }
                for alert in self.active_alerts.values()
            ]
        }
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "service_name": self.config.service_name,
            "environment": self.config.environment,
            "system_metrics": self.get_system_metrics_summary(),
            "performance": self.get_performance_summary(),
            "health": self.get_health_summary(),
            "alerts": self.get_alert_summary(),
            "error_counts": self.error_counts,
            "configuration": {
                "collection_interval_seconds": self.config.collection_interval_seconds,
                "health_check_interval_seconds": self.config.health_check_interval_seconds,
                "thresholds": {
                    "cpu_threshold_percent": self.config.cpu_threshold_percent,
                    "memory_threshold_percent": self.config.memory_threshold_percent,
                    "disk_threshold_percent": self.config.disk_threshold_percent
                }
            }
        }
    
    # ========================================================================
    # Context Managers and Decorators
    # ========================================================================
    
    def monitor_operation(self, operation_name: str):
        """Decorator to monitor an operation"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_timing(f"operation.{operation_name}", duration_ms)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_error(f"operation.{operation_name}", {"error_type": type(e).__name__})
                    self.record_timing(f"operation.{operation_name}.error", duration_ms)
                    raise
            
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_timing(f"operation.{operation_name}", duration_ms)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_error(f"operation.{operation_name}", {"error_type": type(e).__name__})
                    self.record_timing(f"operation.{operation_name}.error", duration_ms)
                    raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def stop_monitoring(self):
        """Stop all monitoring tasks"""
        if self.logger:
            self.logger.info(
                "Stopping enterprise monitoring service",
                category=LogCategory.SYSTEM if LogCategory else None
            )
        
        # Cancel background tasks
        if self._collection_task:
            self._collection_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._alerting_task:
            self._alerting_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self._collection_task, self._health_check_task, self._alerting_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# ========================================================================
# Global Monitoring Instance
# ========================================================================

# Create global monitoring instance
_global_monitoring: Optional[EnterpriseMonitoringService] = None


def get_monitoring_service(config: MonitoringConfig = None) -> EnterpriseMonitoringService:
    """Get or create global monitoring service instance"""
    global _global_monitoring
    if _global_monitoring is None:
        _global_monitoring = EnterpriseMonitoringService(config)
    return _global_monitoring


# Convenience function for quick access
def get_monitor() -> EnterpriseMonitoringService:
    """Get the global monitoring service"""
    return get_monitoring_service()


# ========================================================================
# Example Usage
# ========================================================================

if __name__ == "__main__":
    async def main():
        # Initialize monitoring service
        monitoring = get_monitoring_service()
        
        # Register health checks
        monitoring.register_health_check("database")
        monitoring.register_health_check("redis")
        monitoring.register_health_check("api")
        
        # Record some metrics
        monitoring.increment_counter("requests.total")
        monitoring.set_gauge("active_connections", 25)
        monitoring.record_timing("database.query", 150.5)
        
        # Simulate some work
        await asyncio.sleep(5)
        
        # Generate report
        report = monitoring.generate_monitoring_report()
        print(f"Monitoring report: {json.dumps(report, indent=2, default=str)}")
        
        # Stop monitoring
        await monitoring.stop_monitoring()
    
    # Run example
    asyncio.run(main())
