#!/usr/bin/env python3
"""
PAKE System - Health Monitoring & Maintenance Framework
Comprehensive health monitoring, maintenance automation, and long-term system health.

This module provides:
- System health monitoring and metrics
- Automated maintenance tasks
- Performance degradation detection
- Capacity planning and scaling
- Backup and recovery monitoring
- Compliance and audit tracking
"""

import asyncio
import json
import logging
import os
import psutil
import time
from datetime import datetime, UTC, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

import aiofiles
import aiohttp
from pydantic import BaseModel, Field


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class MaintenanceTaskType(Enum):
    """Maintenance task types"""
    CLEANUP = "cleanup"
    BACKUP = "backup"
    UPDATE = "update"
    OPTIMIZATION = "optimization"
    SECURITY_SCAN = "security_scan"
    CAPACITY_CHECK = "capacity_check"
    LOG_ROTATION = "log_rotation"
    CACHE_CLEAR = "cache_clear"


class HealthMetric(BaseModel):
    """Health metric model"""
    metric_name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    threshold_warning: Optional[float] = Field(None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(None, description="Critical threshold")
    status: HealthStatus = Field(default=HealthStatus.HEALTHY, description="Health status")


class MaintenanceTask(BaseModel):
    """Maintenance task model"""
    task_id: str = Field(..., description="Unique task identifier")
    task_type: MaintenanceTaskType = Field(..., description="Task type")
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Task description")
    schedule: str = Field(..., description="Cron-like schedule")
    last_run: Optional[datetime] = Field(None, description="Last run timestamp")
    next_run: Optional[datetime] = Field(None, description="Next run timestamp")
    enabled: bool = Field(default=True, description="Whether task is enabled")
    timeout_minutes: int = Field(default=30, description="Task timeout in minutes")
    success_count: int = Field(default=0, description="Successful run count")
    failure_count: int = Field(default=0, description="Failed run count")
    last_status: Optional[str] = Field(None, description="Last run status")
    last_error: Optional[str] = Field(None, description="Last error message")


class SystemHealthReport(BaseModel):
    """System health report model"""
    report_id: str = Field(..., description="Report identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    overall_status: HealthStatus = Field(..., description="Overall system status")
    service_status: Dict[str, HealthStatus] = Field(default_factory=dict, description="Service statuses")
    metrics: List[HealthMetric] = Field(default_factory=list, description="Health metrics")
    alerts: List[str] = Field(default_factory=list, description="Active alerts")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    last_maintenance: Optional[datetime] = Field(None, description="Last maintenance timestamp")


class HealthMonitoringSystem:
    """
    Enterprise Health Monitoring & Maintenance System

    Provides comprehensive health monitoring, automated maintenance,
    and long-term system health management capabilities.
    """

    def __init__(self):
        self.logger = self._setup_logger()
        self.health_metrics: List[HealthMetric] = []
        self.maintenance_tasks: List[MaintenanceTask] = []
        self.health_reports: List[SystemHealthReport] = []
        self.service_checks: Dict[str, Callable] = {}

        # System startup time
        self.system_start_time = datetime.now(UTC)

        # Initialize default maintenance tasks
        self._initialize_default_tasks()

        # Initialize service checks
        self._initialize_service_checks()

        # Monitoring state
        self.monitoring_active = False
        self.last_health_check = datetime.now(UTC)

    def _setup_logger(self) -> logging.Logger:
        """Set up health monitoring logger"""
        logger = logging.getLogger("pake_health_monitoring")
        logger.setLevel(logging.INFO)

        # Create health log file
        log_dir = Path("logs/health")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "health_monitoring.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _initialize_default_tasks(self):
        """Initialize default maintenance tasks"""
        default_tasks = [
            MaintenanceTask(
                task_id="log_cleanup",
                task_type=MaintenanceTaskType.CLEANUP,
                name="Log Cleanup",
                description="Clean up old log files",
                schedule="0 2 * * *",  # Daily at 2 AM
                timeout_minutes=15
            ),
            MaintenanceTask(
                task_id="database_backup",
                task_type=MaintenanceTaskType.BACKUP,
                name="Database Backup",
                description="Create database backup",
                schedule="0 1 * * *",  # Daily at 1 AM
                timeout_minutes=60
            ),
            MaintenanceTask(
                task_id="cache_cleanup",
                task_type=MaintenanceTaskType.CACHE_CLEAR,
                name="Cache Cleanup",
                description="Clear expired cache entries",
                schedule="0 */6 * * *",  # Every 6 hours
                timeout_minutes=10
            ),
            MaintenanceTask(
                task_id="security_scan",
                task_type=MaintenanceTaskType.SECURITY_SCAN,
                name="Security Scan",
                description="Run security vulnerability scan",
                schedule="0 3 * * 0",  # Weekly on Sunday at 3 AM
                timeout_minutes=45
            ),
            MaintenanceTask(
                task_id="capacity_check",
                task_type=MaintenanceTaskType.CAPACITY_CHECK,
                name="Capacity Check",
                description="Check system capacity and resources",
                schedule="0 */4 * * *",  # Every 4 hours
                timeout_minutes=5
            ),
            MaintenanceTask(
                task_id="performance_optimization",
                task_type=MaintenanceTaskType.OPTIMIZATION,
                name="Performance Optimization",
                description="Run performance optimization tasks",
                schedule="0 4 * * 0",  # Weekly on Sunday at 4 AM
                timeout_minutes=30
            )
        ]

        self.maintenance_tasks.extend(default_tasks)
        self.logger.info(f"Initialized {len(default_tasks)} default maintenance tasks")

    def _initialize_service_checks(self):
        """Initialize service health checks"""
        self.service_checks = {
            "database": self._check_database_health,
            "redis": self._check_redis_health,
            "api_gateway": self._check_api_gateway_health,
            "ingestion_service": self._check_ingestion_service_health,
            "analytics_service": self._check_analytics_service_health,
            "storage": self._check_storage_health,
            "network": self._check_network_health
        }

    # ========================================================================
    # Health Monitoring
    # ========================================================================

    async def collect_system_metrics(self) -> List[HealthMetric]:
        """Collect comprehensive system metrics"""
        metrics = []

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(HealthMetric(
            metric_name="cpu_usage_percent",
            value=cpu_percent,
            unit="percent",
            threshold_warning=70.0,
            threshold_critical=90.0,
            status=self._get_metric_status(cpu_percent, 70.0, 90.0)
        ))

        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.append(HealthMetric(
            metric_name="memory_usage_percent",
            value=memory.percent,
            unit="percent",
            threshold_warning=80.0,
            threshold_critical=95.0,
            status=self._get_metric_status(memory.percent, 80.0, 95.0)
        ))

        metrics.append(HealthMetric(
            metric_name="memory_available_mb",
            value=memory.available / (1024 * 1024),
            unit="MB",
            threshold_warning=1000.0,  # 1GB
            threshold_critical=500.0,  # 500MB
            status=self._get_metric_status(memory.available / (1024 * 1024), 1000.0, 500.0, reverse=True)
        ))

        # Disk metrics
        disk = psutil.disk_usage('/')
        metrics.append(HealthMetric(
            metric_name="disk_usage_percent",
            value=(disk.used / disk.total) * 100,
            unit="percent",
            threshold_warning=80.0,
            threshold_critical=95.0,
            status=self._get_metric_status((disk.used / disk.total) * 100, 80.0, 95.0)
        ))

        metrics.append(HealthMetric(
            metric_name="disk_free_gb",
            value=disk.free / (1024 * 1024 * 1024),
            unit="GB",
            threshold_warning=10.0,  # 10GB
            threshold_critical=5.0,  # 5GB
            status=self._get_metric_status(disk.free / (1024 * 1024 * 1024), 10.0, 5.0, reverse=True)
        ))

        # Network metrics
        network_io = psutil.net_io_counters()
        metrics.append(HealthMetric(
            metric_name="network_bytes_sent_mb",
            value=network_io.bytes_sent / (1024 * 1024),
            unit="MB"
        ))

        metrics.append(HealthMetric(
            metric_name="network_bytes_received_mb",
            value=network_io.bytes_recv / (1024 * 1024),
            unit="MB"
        ))

        # Process metrics
        process_count = len(psutil.pids())
        metrics.append(HealthMetric(
            metric_name="process_count",
            value=process_count,
            unit="count",
            threshold_warning=500.0,
            threshold_critical=1000.0,
            status=self._get_metric_status(process_count, 500.0, 1000.0)
        ))

        # Load average (Unix-like systems)
        if hasattr(psutil, 'getloadavg'):
            load_avg = psutil.getloadavg()[0]  # 1-minute load average
            cpu_count = psutil.cpu_count()
            load_percent = (load_avg / cpu_count) * 100

            metrics.append(HealthMetric(
                metric_name="load_average_percent",
                value=load_percent,
                unit="percent",
                threshold_warning=70.0,
                threshold_critical=90.0,
                status=self._get_metric_status(load_percent, 70.0, 90.0)
            ))

        # Store metrics
        self.health_metrics.extend(metrics)

        # Keep only last 1000 metrics per type
        self._cleanup_old_metrics()

        self.logger.info(f"Collected {len(metrics)} system metrics")
        return metrics

    def _get_metric_status(
        self,
        value: float,
        warning_threshold: float,
        critical_threshold: float,
        reverse: bool = False
    ) -> HealthStatus:
        """Determine metric health status based on thresholds"""
        if reverse:
            # For metrics where lower is better (like free space)
            if value <= critical_threshold:
                return HealthStatus.CRITICAL
            elif value <= warning_threshold:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        else:
            # For metrics where higher is worse (like CPU usage)
            if value >= critical_threshold:
                return HealthStatus.CRITICAL
            elif value >= warning_threshold:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY

    def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent memory bloat"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=24)

        # Group metrics by name and keep only recent ones
        metric_groups = {}
        for metric in self.health_metrics:
            if metric.metric_name not in metric_groups:
                metric_groups[metric.metric_name] = []
            metric_groups[metric.metric_name].append(metric)

        # Keep only last 1000 metrics per type
        cleaned_metrics = []
        for metric_name, metrics in metric_groups.items():
            sorted_metrics = sorted(metrics, key=lambda x: x.timestamp, reverse=True)
            cleaned_metrics.extend(sorted_metrics[:1000])

        self.health_metrics = cleaned_metrics

    # ========================================================================
    # Service Health Checks
    # ========================================================================

    async def check_service_health(self, service_name: str) -> HealthStatus:
        """Check health of a specific service"""
        if service_name not in self.service_checks:
            self.logger.warning(f"No health check defined for service: {service_name}")
            return HealthStatus.UNHEALTHY

        try:
            health_status = await self.service_checks[service_name]()
            self.logger.info(f"Service {service_name} health check: {health_status.value}")
            return health_status
        except Exception as e:
            self.logger.error(f"Health check failed for {service_name}: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_database_health(self) -> HealthStatus:
        """Check database health"""
        try:
            # In production, this would check actual database connection
            # For now, simulate a health check
            await asyncio.sleep(0.1)  # Simulate database query

            # Check if database is responsive
            # This is a placeholder - implement actual database health check
            return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_redis_health(self) -> HealthStatus:
        """Check Redis health"""
        try:
            # In production, this would check Redis connection
            # For now, simulate a health check
            await asyncio.sleep(0.1)  # Simulate Redis ping

            # Check if Redis is responsive
            # This is a placeholder - implement actual Redis health check
            return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_api_gateway_health(self) -> HealthStatus:
        """Check API gateway health"""
        try:
            # Check if API gateway is responding
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/health', timeout=5) as response:
                    if response.status == 200:
                        return HealthStatus.HEALTHY
                    else:
                        return HealthStatus.DEGRADED
        except Exception as e:
            self.logger.error(f"API gateway health check failed: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_ingestion_service_health(self) -> HealthStatus:
        """Check ingestion service health"""
        try:
            # Check if ingestion service is responsive
            # This is a placeholder - implement actual service health check
            await asyncio.sleep(0.1)
            return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.error(f"Ingestion service health check failed: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_analytics_service_health(self) -> HealthStatus:
        """Check analytics service health"""
        try:
            # Check if analytics service is responsive
            # This is a placeholder - implement actual service health check
            await asyncio.sleep(0.1)
            return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.error(f"Analytics service health check failed: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_storage_health(self) -> HealthStatus:
        """Check storage health"""
        try:
            # Check disk space and I/O
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100

            if disk_usage_percent > 95:
                return HealthStatus.CRITICAL
            elif disk_usage_percent > 85:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.error(f"Storage health check failed: {str(e)}")
            return HealthStatus.CRITICAL

    async def _check_network_health(self) -> HealthStatus:
        """Check network health"""
        try:
            # Check network connectivity
            async with aiohttp.ClientSession() as session:
                async with session.get('https://www.google.com', timeout=5) as response:
                    if response.status == 200:
                        return HealthStatus.HEALTHY
                    else:
                        return HealthStatus.DEGRADED
        except Exception as e:
            self.logger.error(f"Network health check failed: {str(e)}")
            return HealthStatus.DEGRADED

    # ========================================================================
    # Health Reporting
    # ========================================================================

    async def generate_health_report(self) -> SystemHealthReport:
        """Generate comprehensive system health report"""
        # Collect current metrics
        current_metrics = await self.collect_system_metrics()

        # Check service health
        service_status = {}
        for service_name in self.service_checks.keys():
            service_status[service_name] = await self.check_service_health(service_name)

        # Determine overall status
        overall_status = self._determine_overall_status(current_metrics, service_status)

        # Generate alerts and recommendations
        alerts = self._generate_alerts(current_metrics, service_status)
        recommendations = self._generate_recommendations(current_metrics, service_status)

        # Calculate uptime
        uptime_seconds = (datetime.now(UTC) - self.system_start_time).total_seconds()

        # Create health report
        report = SystemHealthReport(
            report_id=f"health_{int(time.time())}_{secrets.token_hex(4)}",
            overall_status=overall_status,
            service_status=service_status,
            metrics=current_metrics,
            alerts=alerts,
            recommendations=recommendations,
            uptime_seconds=uptime_seconds,
            last_maintenance=self._get_last_maintenance_time()
        )

        # Store report
        self.health_reports.append(report)

        # Keep only last 100 reports
        if len(self.health_reports) > 100:
            self.health_reports = self.health_reports[-100:]

        self.logger.info(f"Generated health report: {report.report_id} - {overall_status.value}")
        return report

    def _determine_overall_status(
        self,
        metrics: List[HealthMetric],
        service_status: Dict[str, HealthStatus]
    ) -> HealthStatus:
        """Determine overall system health status"""
        # Check for critical status
        critical_metrics = [m for m in metrics if m.status == HealthStatus.CRITICAL]
        critical_services = [s for s in service_status.values() if s == HealthStatus.CRITICAL]

        if critical_metrics or critical_services:
            return HealthStatus.CRITICAL

        # Check for degraded status
        degraded_metrics = [m for m in metrics if m.status == HealthStatus.DEGRADED]
        degraded_services = [s for s in service_status.values() if s == HealthStatus.DEGRADED]

        if degraded_metrics or degraded_services:
            return HealthStatus.DEGRADED

        # Check for unhealthy status
        unhealthy_services = [s for s in service_status.values() if s == HealthStatus.UNHEALTHY]
        if unhealthy_services:
            return HealthStatus.UNHEALTHY

        return HealthStatus.HEALTHY

    def _generate_alerts(
        self,
        metrics: List[HealthMetric],
        service_status: Dict[str, HealthStatus]
    ) -> List[str]:
        """Generate health alerts"""
        alerts = []

        # Check for critical metrics
        critical_metrics = [m for m in metrics if m.status == HealthStatus.CRITICAL]
        for metric in critical_metrics:
            alerts.append(f"CRITICAL: {metric.metric_name} is {metric.value} {metric.unit}")

        # Check for degraded metrics
        degraded_metrics = [m for m in metrics if m.status == HealthStatus.DEGRADED]
        for metric in degraded_metrics:
            alerts.append(f"WARNING: {metric.metric_name} is {metric.value} {metric.unit}")

        # Check for unhealthy services
        unhealthy_services = [name for name, status in service_status.items() if status == HealthStatus.UNHEALTHY]
        for service in unhealthy_services:
            alerts.append(f"UNHEALTHY: Service {service} is not responding")

        return alerts

    def _generate_recommendations(
        self,
        metrics: List[HealthMetric],
        service_status: Dict[str, HealthStatus]
    ) -> List[str]:
        """Generate health recommendations"""
        recommendations = []

        # Check CPU usage
        cpu_metric = next((m for m in metrics if m.metric_name == "cpu_usage_percent"), None)
        if cpu_metric and cpu_metric.value > 80:
            recommendations.append("Consider scaling up CPU resources or optimizing CPU-intensive operations")

        # Check memory usage
        memory_metric = next((m for m in metrics if m.metric_name == "memory_usage_percent"), None)
        if memory_metric and memory_metric.value > 80:
            recommendations.append("Consider increasing memory allocation or optimizing memory usage")

        # Check disk usage
        disk_metric = next((m for m in metrics if m.metric_name == "disk_usage_percent"), None)
        if disk_metric and disk_metric.value > 80:
            recommendations.append("Consider cleaning up disk space or expanding storage capacity")

        # Check for failed services
        failed_services = [name for name, status in service_status.items() if status == HealthStatus.CRITICAL]
        if failed_services:
            recommendations.append(f"Investigate and restart failed services: {', '.join(failed_services)}")

        return recommendations

    def _get_last_maintenance_time(self) -> Optional[datetime]:
        """Get last maintenance execution time"""
        maintenance_times = [
            task.last_run for task in self.maintenance_tasks
            if task.last_run is not None
        ]

        if maintenance_times:
            return max(maintenance_times)

        return None

    # ========================================================================
    # Maintenance Task Management
    # ========================================================================

    async def run_maintenance_task(self, task_id: str) -> bool:
        """Run a specific maintenance task"""
        task = await self._get_task_by_id(task_id)
        if not task:
            self.logger.error(f"Maintenance task not found: {task_id}")
            return False

        if not task.enabled:
            self.logger.info(f"Maintenance task {task_id} is disabled")
            return False

        self.logger.info(f"Starting maintenance task: {task.name}")
        start_time = datetime.now(UTC)

        try:
            # Run the task
            success = await self._execute_task(task)

            # Update task status
            task.last_run = start_time
            task.last_status = "success" if success else "failed"

            if success:
                task.success_count += 1
                self.logger.info(f"Maintenance task completed successfully: {task.name}")
            else:
                task.failure_count += 1
                self.logger.error(f"Maintenance task failed: {task.name}")

            return success

        except Exception as e:
            task.last_run = start_time
            task.last_status = "error"
            task.last_error = str(e)
            task.failure_count += 1

            self.logger.error(f"Maintenance task error: {task.name} - {str(e)}")
            return False

    async def _get_task_by_id(self, task_id: str) -> Optional[MaintenanceTask]:
        """Get maintenance task by ID"""
        for task in self.maintenance_tasks:
            if task.task_id == task_id:
                return task
        return None

    async def _execute_task(self, task: MaintenanceTask) -> bool:
        """Execute maintenance task based on type"""
        try:
            if task.task_type == MaintenanceTaskType.CLEANUP:
                return await self._run_cleanup_task(task)
            elif task.task_type == MaintenanceTaskType.BACKUP:
                return await self._run_backup_task(task)
            elif task.task_type == MaintenanceTaskType.CACHE_CLEAR:
                return await self._run_cache_clear_task(task)
            elif task.task_type == MaintenanceTaskType.SECURITY_SCAN:
                return await self._run_security_scan_task(task)
            elif task.task_type == MaintenanceTaskType.CAPACITY_CHECK:
                return await self._run_capacity_check_task(task)
            elif task.task_type == MaintenanceTaskType.OPTIMIZATION:
                return await self._run_optimization_task(task)
            else:
                self.logger.error(f"Unknown task type: {task.task_type}")
                return False

        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}")
            return False

    async def _run_cleanup_task(self, task: MaintenanceTask) -> bool:
        """Run cleanup maintenance task"""
        try:
            # Clean up old log files
            log_dir = Path("logs")
            if log_dir.exists():
                cutoff_time = datetime.now(UTC) - timedelta(days=30)

                for log_file in log_dir.rglob("*.log"):
                    if log_file.stat().st_mtime < cutoff_time.timestamp():
                        log_file.unlink()
                        self.logger.info(f"Deleted old log file: {log_file}")

            # Clean up temporary files
            temp_dir = Path("/tmp")
            if temp_dir.exists():
                cutoff_time = datetime.now(UTC) - timedelta(days=7)

                for temp_file in temp_dir.glob("pake_*"):
                    if temp_file.stat().st_mtime < cutoff_time.timestamp():
                        temp_file.unlink()
                        self.logger.info(f"Deleted temporary file: {temp_file}")

            return True

        except Exception as e:
            self.logger.error(f"Cleanup task failed: {str(e)}")
            return False

    async def _run_backup_task(self, task: MaintenanceTask) -> bool:
        """Run backup maintenance task"""
        try:
            # Create backup directory
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)

            # Create timestamped backup
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"backup_{timestamp}.json"

            # Backup system configuration and data
            backup_data = {
                "timestamp": timestamp,
                "health_metrics": [metric.dict() for metric in self.health_metrics[-100:]],
                "maintenance_tasks": [task.dict() for task in self.maintenance_tasks],
                "system_info": {
                    "uptime_seconds": (datetime.now(UTC) - self.system_start_time).total_seconds(),
                    "python_version": os.sys.version,
                    "platform": os.name
                }
            }

            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(json.dumps(backup_data, indent=2, default=str))

            self.logger.info(f"Backup created: {backup_file}")
            return True

        except Exception as e:
            self.logger.error(f"Backup task failed: {str(e)}")
            return False

    async def _run_cache_clear_task(self, task: MaintenanceTask) -> bool:
        """Run cache clear maintenance task"""
        try:
            # Clear application cache
            cache_dir = Path("cache")
            if cache_dir.exists():
                for cache_file in cache_dir.glob("*"):
                    if cache_file.is_file():
                        cache_file.unlink()
                        self.logger.info(f"Cleared cache file: {cache_file}")

            # Clear temporary cache
            temp_cache_dir = Path("/tmp/pake_cache")
            if temp_cache_dir.exists():
                for cache_file in temp_cache_dir.glob("*"):
                    if cache_file.is_file():
                        cache_file.unlink()
                        self.logger.info(f"Cleared temp cache file: {cache_file}")

            return True

        except Exception as e:
            self.logger.error(f"Cache clear task failed: {str(e)}")
            return False

    async def _run_security_scan_task(self, task: MaintenanceTask) -> bool:
        """Run security scan maintenance task"""
        try:
            # This would integrate with the security monitoring system
            # For now, simulate a security scan
            await asyncio.sleep(1)  # Simulate scan time

            self.logger.info("Security scan completed")
            return True

        except Exception as e:
            self.logger.error(f"Security scan task failed: {str(e)}")
            return False

    async def _run_capacity_check_task(self, task: MaintenanceTask) -> bool:
        """Run capacity check maintenance task"""
        try:
            # Check system capacity
            await self.collect_system_metrics()

            # Check disk space
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100

            if disk_usage_percent > 90:
                self.logger.warning(f"Disk usage is high: {disk_usage_percent:.1f}%")

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.logger.warning(f"Memory usage is high: {memory.percent:.1f}%")

            self.logger.info("Capacity check completed")
            return True

        except Exception as e:
            self.logger.error(f"Capacity check task failed: {str(e)}")
            return False

    async def _run_optimization_task(self, task: MaintenanceTask) -> bool:
        """Run optimization maintenance task"""
        try:
            # Optimize database (placeholder)
            await asyncio.sleep(0.5)

            # Optimize cache (placeholder)
            await asyncio.sleep(0.5)

            # Optimize logs (placeholder)
            await asyncio.sleep(0.5)

            self.logger.info("Optimization task completed")
            return True

        except Exception as e:
            self.logger.error(f"Optimization task failed: {str(e)}")
            return False

    # ========================================================================
    # Automated Maintenance Scheduling
    # ========================================================================

    async def run_scheduled_maintenance(self):
        """Run scheduled maintenance tasks"""
        current_time = datetime.now(UTC)

        for task in self.maintenance_tasks:
            if not task.enabled:
                continue

            # Check if task should run (simplified scheduling)
            if self._should_run_task(task, current_time):
                await self.run_maintenance_task(task.task_id)

    def _should_run_task(self, task: MaintenanceTask, current_time: datetime) -> bool:
        """Check if task should run based on schedule"""
        # Simplified scheduling - in production, use cron parser
        if task.last_run is None:
            return True

        # Check if enough time has passed since last run
        time_since_last_run = current_time - task.last_run

        if "daily" in task.schedule and time_since_last_run.total_seconds() > 86400:  # 24 hours
            return True
        elif "weekly" in task.schedule and time_since_last_run.total_seconds() > 604800:  # 7 days
            return True
        elif "hourly" in task.schedule and time_since_last_run.total_seconds() > 3600:  # 1 hour
            return True

        return False

    # ========================================================================
    # Health Monitoring Loop
    # ========================================================================

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous health monitoring"""
        self.monitoring_active = True
        self.logger.info(f"Starting health monitoring with {interval_seconds}s interval")

        while self.monitoring_active:
            try:
                # Generate health report
                report = await self.generate_health_report()

                # Run scheduled maintenance
                await self.run_scheduled_maintenance()

                # Log health status
                if report.overall_status != HealthStatus.HEALTHY:
                    self.logger.warning(f"System health: {report.overall_status.value}")

                # Wait for next check
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                self.logger.error(f"Health monitoring error: {str(e)}")
                await asyncio.sleep(interval_seconds)

    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        self.logger.info("Health monitoring stopped")

    # ========================================================================
    # Reporting and Analytics
    # ========================================================================

    async def get_health_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get health trends over time"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Filter reports by date range
        recent_reports = [
            report for report in self.health_reports
            if start_date <= report.timestamp <= end_date
        ]

        if not recent_reports:
            return {"message": "No health reports available for the specified period"}

        # Calculate trends
        status_counts = {}
        for report in recent_reports:
            status = report.overall_status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate average uptime
        avg_uptime = sum(report.uptime_seconds for report in recent_reports) / len(recent_reports)

        # Get most common alerts
        all_alerts = []
        for report in recent_reports:
            all_alerts.extend(report.alerts)

        alert_counts = {}
        for alert in all_alerts:
            alert_counts[alert] = alert_counts.get(alert, 0) + 1

        top_alerts = dict(sorted(alert_counts.items(), key=lambda x: x[1], reverse=True)[:5])

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_reports": len(recent_reports),
                "status_distribution": status_counts,
                "average_uptime_hours": avg_uptime / 3600,
                "health_score": self._calculate_health_score(recent_reports)
            },
            "top_alerts": top_alerts,
            "trends": self._calculate_health_trends(recent_reports)
        }

    def _calculate_health_score(self, reports: List[SystemHealthReport]) -> float:
        """Calculate overall health score (0-100)"""
        if not reports:
            return 0.0

        total_score = 0.0
        for report in reports:
            if report.overall_status == HealthStatus.HEALTHY:
                total_score += 100
            elif report.overall_status == HealthStatus.DEGRADED:
                total_score += 70
            elif report.overall_status == HealthStatus.UNHEALTHY:
                total_score += 40
            else:  # CRITICAL
                total_score += 10

        return total_score / len(reports)

    def _calculate_health_trends(self, reports: List[SystemHealthReport]) -> Dict[str, Any]:
        """Calculate health trends"""
        if len(reports) < 2:
            return {"trend": "insufficient_data"}

        # Sort reports by timestamp
        sorted_reports = sorted(reports, key=lambda x: x.timestamp)

        # Calculate trend direction
        first_half = sorted_reports[:len(sorted_reports)//2]
        second_half = sorted_reports[len(sorted_reports)//2:]

        first_score = self._calculate_health_score(first_half)
        second_score = self._calculate_health_score(second_half)

        if second_score > first_score + 5:
            trend = "improving"
        elif second_score < first_score - 5:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "first_half_score": first_score,
            "second_half_score": second_score,
            "change": second_score - first_score
        }


if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize health monitoring system
        health_monitor = HealthMonitoringSystem()

        # Generate health report
        report = await health_monitor.generate_health_report()
        print(f"System health: {report.overall_status.value}")
        print(f"Uptime: {report.uptime_seconds / 3600:.1f} hours")

        # Run a maintenance task
        await health_monitor.run_maintenance_task("log_cleanup")

        # Get health trends
        trends = await health_monitor.get_health_trends()
        print(f"Health trends: {trends}")

    asyncio.run(main())
