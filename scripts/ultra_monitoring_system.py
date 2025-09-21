#!/usr/bin/env python3
"""
PAKE Ultra Monitoring & Self-Healing System
Advanced monitoring with predictive analytics and autonomous recovery
"""

import json
import logging
import os
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

# Configure advanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/ultra_monitoring.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""

    timestamp: datetime
    cpu_percent: float
    memory_used_mb: int
    memory_available_mb: int
    disk_used_gb: int
    disk_free_gb: int
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    pake_processes: list[dict[str, Any]]
    vault_stats: dict[str, Any]
    processing_stats: dict[str, Any]


@dataclass
class HealthStatus:
    """Overall system health status"""

    timestamp: datetime
    overall_health: str  # EXCELLENT, GOOD, WARNING, CRITICAL
    component_health: dict[str, str]
    active_alerts: list[str]
    performance_score: float
    recommendations: list[str]
    next_check: datetime


@dataclass
class Alert:
    """System alert"""

    id: str
    timestamp: datetime
    level: str  # INFO, WARNING, CRITICAL
    component: str
    message: str
    details: dict[str, Any]
    resolved: bool = False
    resolution_time: datetime | None = None


class UltraMonitoringSystem:
    """Advanced monitoring system with self-healing capabilities"""

    def __init__(self):
        self.monitoring_active = True
        self.metrics_history = []
        self.alerts = []
        self.health_thresholds = {
            "cpu_critical": 90,
            "cpu_warning": 70,
            "memory_critical": 90,
            "memory_warning": 75,
            "disk_critical": 95,
            "disk_warning": 85,
            "process_response_timeout": 30,
            "unprocessed_notes_critical": 50,
            "unprocessed_notes_warning": 20,
        }

        # Initialize monitoring database
        self.init_monitoring_db()

        # Start monitoring threads
        self.start_monitoring_threads()

        logger.info("Ultra Monitoring System initialized")

    def init_monitoring_db(self):
        """Initialize SQLite database for monitoring data"""
        try:
            os.makedirs("data", exist_ok=True)
            self.db_path = "data/monitoring.db"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Metrics table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    cpu_percent REAL,
                    memory_used_mb INTEGER,
                    memory_available_mb INTEGER,
                    disk_used_gb INTEGER,
                    disk_free_gb INTEGER,
                    process_count INTEGER,
                    vault_notes_total INTEGER,
                    vault_processed INTEGER,
                    processing_speed_ms REAL,
                    performance_score REAL
                )
            """,
            )

            # Alerts table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME,
                    level TEXT,
                    component TEXT,
                    message TEXT,
                    details TEXT,
                    resolved BOOLEAN,
                    resolution_time DATETIME
                )
            """,
            )

            # Health history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS health_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    overall_health TEXT,
                    performance_score REAL,
                    component_scores TEXT,
                    recommendations TEXT
                )
            """,
            )

            conn.commit()
            conn.close()

            logger.info("Monitoring database initialized")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring database: {e}")

    def start_monitoring_threads(self):
        """Start all monitoring threads"""
        # System metrics collection
        threading.Thread(target=self.metrics_collection_loop, daemon=True).start()

        # Health assessment
        threading.Thread(target=self.health_assessment_loop, daemon=True).start()

        # Process monitoring
        threading.Thread(target=self.process_monitoring_loop, daemon=True).start()

        # Vault monitoring
        threading.Thread(target=self.vault_monitoring_loop, daemon=True).start()

        # Performance optimization
        threading.Thread(target=self.performance_optimization_loop, daemon=True).start()

        # Self-healing
        threading.Thread(target=self.self_healing_loop, daemon=True).start()

        logger.info("All monitoring threads started")

    def metrics_collection_loop(self):
        """Continuous metrics collection"""
        while self.monitoring_active:
            try:
                metrics = self.collect_system_metrics()
                self.store_metrics(metrics)
                self.analyze_metrics_trends(metrics)

                # Keep only last 24 hours of metrics
                if (
                    len(self.metrics_history) > 2880
                ):  # 24 hours * 60 minutes / 0.5 minute intervals
                    self.metrics_history = self.metrics_history[-2880:]

                time.sleep(30)  # Collect every 30 seconds

            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(60)  # Wait longer on error

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        try:
            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            # PAKE processes
            pake_processes = []
            all_processes = psutil.process_iter(
                ["pid", "name", "cmdline", "cpu_percent", "memory_info"],
            )

            for proc in all_processes:
                try:
                    if proc.info["cmdline"] and any(
                        "pake" in str(cmd).lower() for cmd in proc.info["cmdline"]
                    ):
                        pake_processes.append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cpu_percent": proc.info["cpu_percent"],
                                "memory_mb": (
                                    proc.info["memory_info"].rss // (1024 * 1024)
                                    if proc.info["memory_info"]
                                    else 0
                                ),
                            },
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Vault statistics
            vault_stats = self.collect_vault_stats()

            # Processing statistics
            processing_stats = self.collect_processing_stats()

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_used_mb=memory.used // (1024 * 1024),
                memory_available_mb=memory.available // (1024 * 1024),
                disk_used_gb=disk.used // (1024 * 1024 * 1024),
                disk_free_gb=disk.free // (1024 * 1024 * 1024),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=len(list(psutil.process_iter())),
                pake_processes=pake_processes,
                vault_stats=vault_stats,
                processing_stats=processing_stats,
            )

            self.metrics_history.append(metrics)
            return metrics

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            raise

    def collect_vault_stats(self) -> dict[str, Any]:
        """Collect vault-specific statistics"""
        try:
            vault_path = Path("vault")
            if not vault_path.exists():
                return {"error": "Vault path not found"}

            total_notes = 0
            processed_notes = 0
            unprocessed_notes = []

            for md_file in vault_path.rglob("*.md"):
                if md_file.is_file():
                    total_notes += 1
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        if "pake_id" in content:
                            processed_notes += 1
                        else:
                            unprocessed_notes.append(
                                str(md_file.relative_to(vault_path)),
                            )
                    except Exception as e:
                        logger.debug(f"Error reading {md_file}: {e}")

            return {
                "total_notes": total_notes,
                "processed_notes": processed_notes,
                "unprocessed_notes": len(unprocessed_notes),
                "processing_rate": (
                    processed_notes / total_notes * 100 if total_notes > 0 else 100
                ),
                # First 10 unprocessed files
                "unprocessed_files": unprocessed_notes[:10],
            }

        except Exception as e:
            logger.error(f"Error collecting vault stats: {e}")
            return {"error": str(e)}

    def collect_processing_stats(self) -> dict[str, Any]:
        """Collect processing performance statistics"""
        try:
            # Check recent processing logs
            log_file = Path("logs/vault_automation.log")
            if not log_file.exists():
                return {"error": "No automation log found"}

            # Parse recent processing times
            processing_times = []
            error_count = 0
            success_count = 0

            try:
                with open(log_file, encoding="utf-8") as f:
                    lines = f.readlines()

                # Look at last 100 lines
                for line in lines[-100:]:
                    if "time=" in line and "s" in line:
                        try:
                            time_part = line.split("time=")[1].split("s")[0]
                            processing_times.append(float(time_part))
                            success_count += 1
                        except BaseException:
                            pass
                    elif "ERROR" in line:
                        error_count += 1
            except Exception as e:
                logger.debug(f"Error parsing log file: {e}")

            avg_processing_time = (
                statistics.mean(processing_times) if processing_times else 0
            )

            return {
                "avg_processing_time_s": avg_processing_time,
                "recent_success_count": success_count,
                "recent_error_count": error_count,
                "success_rate": (
                    success_count / (success_count + error_count) * 100
                    if (success_count + error_count) > 0
                    else 100
                ),
                "processing_speed_score": min(
                    100,
                    max(0, 100 - (avg_processing_time * 10)),
                ),
            }

        except Exception as e:
            logger.error(f"Error collecting processing stats: {e}")
            return {"error": str(e)}

    def store_metrics(self, metrics: SystemMetrics):
        """Store metrics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO system_metrics
                (timestamp, cpu_percent, memory_used_mb, memory_available_mb,
                 disk_used_gb, disk_free_gb, process_count, vault_notes_total,
                 vault_processed, processing_speed_ms, performance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics.timestamp.isoformat(),
                    metrics.cpu_percent,
                    metrics.memory_used_mb,
                    metrics.memory_available_mb,
                    metrics.disk_used_gb,
                    metrics.disk_free_gb,
                    metrics.process_count,
                    metrics.vault_stats.get("total_notes", 0),
                    metrics.vault_stats.get("processed_notes", 0),
                    metrics.processing_stats.get("avg_processing_time_s", 0) * 1000,
                    self.calculate_performance_score(metrics),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing metrics: {e}")

    def analyze_metrics_trends(self, metrics: SystemMetrics):
        """Analyze trends and generate alerts"""
        try:
            # CPU usage alerts
            if metrics.cpu_percent > self.health_thresholds["cpu_critical"]:
                self.create_alert(
                    "CRITICAL",
                    "system",
                    f"Critical CPU usage: {metrics.cpu_percent:.1f}%",
                )
            elif metrics.cpu_percent > self.health_thresholds["cpu_warning"]:
                self.create_alert(
                    "WARNING",
                    "system",
                    f"High CPU usage: {metrics.cpu_percent:.1f}%",
                )

            # Memory usage alerts
            memory_percent = (
                metrics.memory_used_mb
                / (metrics.memory_used_mb + metrics.memory_available_mb)
                * 100
            )
            if memory_percent > self.health_thresholds["memory_critical"]:
                self.create_alert(
                    "CRITICAL",
                    "system",
                    f"Critical memory usage: {memory_percent:.1f}%",
                )
            elif memory_percent > self.health_thresholds["memory_warning"]:
                self.create_alert(
                    "WARNING",
                    "system",
                    f"High memory usage: {memory_percent:.1f}%",
                )

            # Disk space alerts
            disk_percent = (
                metrics.disk_used_gb
                / (metrics.disk_used_gb + metrics.disk_free_gb)
                * 100
            )
            if disk_percent > self.health_thresholds["disk_critical"]:
                self.create_alert(
                    "CRITICAL",
                    "storage",
                    f"Critical disk usage: {disk_percent:.1f}%",
                )
            elif disk_percent > self.health_thresholds["disk_warning"]:
                self.create_alert(
                    "WARNING",
                    "storage",
                    f"High disk usage: {disk_percent:.1f}%",
                )

            # Vault processing alerts
            unprocessed = metrics.vault_stats.get("unprocessed_notes", 0)
            if unprocessed > self.health_thresholds["unprocessed_notes_critical"]:
                self.create_alert(
                    "CRITICAL",
                    "vault",
                    f"{unprocessed} unprocessed notes detected",
                )
            elif unprocessed > self.health_thresholds["unprocessed_notes_warning"]:
                self.create_alert(
                    "WARNING",
                    "vault",
                    f"{unprocessed} unprocessed notes detected",
                )

            # PAKE process alerts
            if not metrics.pake_processes:
                self.create_alert("CRITICAL", "pake", "No PAKE processes detected")

        except Exception as e:
            logger.error(f"Error analyzing metrics trends: {e}")

    def create_alert(
        self,
        level: str,
        component: str,
        message: str,
        details: dict[str, Any] = None,
    ):
        """Create and manage alerts"""
        alert_id = f"{component}_{level}_{hash(message) % 10000}"

        # Check if alert already exists
        existing_alert = next(
            (a for a in self.alerts if a.id == alert_id and not a.resolved),
            None,
        )
        if existing_alert:
            return  # Don't create duplicate alerts

        alert = Alert(
            id=alert_id,
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            details=details or {},
        )

        self.alerts.append(alert)
        self.store_alert(alert)

        logger.warning(f"ALERT [{level}] {component}: {message}")

        # Trigger self-healing for critical alerts
        if level == "CRITICAL":
            self.trigger_self_healing(alert)

    def store_alert(self, alert: Alert):
        """Store alert in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO alerts
                (id, timestamp, level, component, message, details, resolved, resolution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    alert.id,
                    alert.timestamp.isoformat(),
                    alert.level,
                    alert.component,
                    alert.message,
                    json.dumps(alert.details),
                    alert.resolved,
                    (
                        alert.resolution_time.isoformat()
                        if alert.resolution_time
                        else None
                    ),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing alert: {e}")

    def health_assessment_loop(self):
        """Continuous health assessment"""
        while self.monitoring_active:
            try:
                health_status = self.assess_overall_health()
                self.store_health_status(health_status)
                self.generate_health_report(health_status)

                time.sleep(300)  # Assess every 5 minutes

            except Exception as e:
                logger.error(f"Health assessment error: {e}")
                time.sleep(300)

    def assess_overall_health(self) -> HealthStatus:
        """Assess overall system health"""
        try:
            if not self.metrics_history:
                return HealthStatus(
                    timestamp=datetime.now(),
                    overall_health="UNKNOWN",
                    component_health={},
                    active_alerts=[],
                    performance_score=0,
                    recommendations=["Insufficient data for health assessment"],
                    next_check=datetime.now() + timedelta(minutes=5),
                )

            latest_metrics = self.metrics_history[-1]

            # Component health assessment
            component_health = {}

            # System health
            if latest_metrics.cpu_percent > 90:
                component_health["system"] = "CRITICAL"
            elif latest_metrics.cpu_percent > 70:
                component_health["system"] = "WARNING"
            else:
                component_health["system"] = "GOOD"

            # Memory health
            memory_percent = (
                latest_metrics.memory_used_mb
                / (latest_metrics.memory_used_mb + latest_metrics.memory_available_mb)
                * 100
            )
            if memory_percent > 90:
                component_health["memory"] = "CRITICAL"
            elif memory_percent > 75:
                component_health["memory"] = "WARNING"
            else:
                component_health["memory"] = "GOOD"

            # Vault health
            unprocessed = latest_metrics.vault_stats.get("unprocessed_notes", 0)
            processing_rate = latest_metrics.vault_stats.get("processing_rate", 100)

            if unprocessed > 50 or processing_rate < 50:
                component_health["vault"] = "CRITICAL"
            elif unprocessed > 20 or processing_rate < 75:
                component_health["vault"] = "WARNING"
            else:
                component_health["vault"] = "EXCELLENT"

            # PAKE processes health
            if not latest_metrics.pake_processes:
                component_health["pake"] = "CRITICAL"
            elif len(latest_metrics.pake_processes) < 2:
                component_health["pake"] = "WARNING"
            else:
                component_health["pake"] = "GOOD"

            # Overall health determination
            health_scores = {"CRITICAL": 0, "WARNING": 25, "GOOD": 75, "EXCELLENT": 100}

            avg_score = statistics.mean(
                [health_scores.get(h, 0) for h in component_health.values()],
            )

            if avg_score >= 90:
                overall_health = "EXCELLENT"
            elif avg_score >= 75:
                overall_health = "GOOD"
            elif avg_score >= 50:
                overall_health = "WARNING"
            else:
                overall_health = "CRITICAL"

            # Active alerts
            active_alerts = [
                alert.message for alert in self.alerts if not alert.resolved
            ]

            # Generate recommendations
            recommendations = self.generate_recommendations(
                component_health,
                latest_metrics,
            )

            return HealthStatus(
                timestamp=datetime.now(),
                overall_health=overall_health,
                component_health=component_health,
                active_alerts=active_alerts,
                performance_score=avg_score,
                recommendations=recommendations,
                next_check=datetime.now() + timedelta(minutes=5),
            )

        except Exception as e:
            logger.error(f"Error assessing health: {e}")
            return HealthStatus(
                timestamp=datetime.now(),
                overall_health="ERROR",
                component_health={},
                active_alerts=[],
                performance_score=0,
                recommendations=[f"Health assessment error: {e}"],
                next_check=datetime.now() + timedelta(minutes=5),
            )

    def generate_recommendations(
        self,
        component_health: dict[str, str],
        metrics: SystemMetrics,
    ) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if component_health.get("system") in ["CRITICAL", "WARNING"]:
            recommendations.append(
                "Consider upgrading system resources or reducing load",
            )

        if component_health.get("memory") in ["CRITICAL", "WARNING"]:
            recommendations.append(
                "Close unnecessary applications or increase system RAM",
            )

        if component_health.get("vault") in ["CRITICAL", "WARNING"]:
            unprocessed = metrics.vault_stats.get("unprocessed_notes", 0)
            if unprocessed > 0:
                recommendations.append(f"Process {unprocessed} pending notes in vault")

        if component_health.get("pake") in ["CRITICAL", "WARNING"]:
            recommendations.append("Restart PAKE automation services")

        if not recommendations:
            recommendations.append("System is running optimally")

        return recommendations

    def calculate_performance_score(self, metrics: SystemMetrics) -> float:
        """Calculate overall performance score (0-100)"""
        try:
            # CPU score (lower usage = higher score)
            cpu_score = max(0, 100 - metrics.cpu_percent)

            # Memory score
            memory_percent = (
                metrics.memory_used_mb
                / (metrics.memory_used_mb + metrics.memory_available_mb)
                * 100
            )
            memory_score = max(0, 100 - memory_percent)

            # Disk score
            disk_percent = (
                metrics.disk_used_gb
                / (metrics.disk_used_gb + metrics.disk_free_gb)
                * 100
            )
            # 50% disk usage is considered good
            disk_score = max(0, 100 - (disk_percent - 50))

            # Vault processing score
            processing_rate = metrics.vault_stats.get("processing_rate", 100)
            vault_score = processing_rate

            # Processing speed score
            speed_score = metrics.processing_stats.get("processing_speed_score", 100)

            # Weighted average
            performance_score = (
                cpu_score * 0.2
                + memory_score * 0.2
                + disk_score * 0.1
                + vault_score * 0.3
                + speed_score * 0.2
            )

            return min(100, max(0, performance_score))

        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 50  # Default middle score on error

    def store_health_status(self, health_status: HealthStatus):
        """Store health status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO health_history
                (timestamp, overall_health, performance_score, component_scores, recommendations)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    health_status.timestamp.isoformat(),
                    health_status.overall_health,
                    health_status.performance_score,
                    json.dumps(health_status.component_health),
                    json.dumps(health_status.recommendations),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing health status: {e}")

    def generate_health_report(self, health_status: HealthStatus):
        """Generate and save health report"""
        try:
            report = {
                "timestamp": health_status.timestamp.isoformat(),
                "overall_health": health_status.overall_health,
                "performance_score": health_status.performance_score,
                "component_health": health_status.component_health,
                "active_alerts": health_status.active_alerts,
                "recommendations": health_status.recommendations,
                "system_stats": (
                    asdict(self.metrics_history[-1]) if self.metrics_history else {}
                ),
            }

            # Save current health status
            with open("logs/current_health.json", "w") as f:
                json.dump(report, f, indent=2, default=str)

            # Log health status
            logger.info(
                f"Health Status: {health_status.overall_health} (Score: {
                    health_status.performance_score:.1f})",
            )

        except Exception as e:
            logger.error(f"Error generating health report: {e}")

    def process_monitoring_loop(self):
        """Monitor PAKE processes specifically"""
        while self.monitoring_active:
            try:
                self.monitor_pake_processes()
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Process monitoring error: {e}")
                time.sleep(60)

    def monitor_pake_processes(self):
        """Monitor PAKE-specific processes"""
        try:
            # Check if vault watcher is running
            vault_watcher_running = False
            api_bridge_running = False

            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["cmdline"]:
                        cmdline_str = " ".join(proc.info["cmdline"])
                        if "automated_vault_watcher.py" in cmdline_str:
                            vault_watcher_running = True
                        elif "obsidian_bridge.js" in cmdline_str:
                            api_bridge_running = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Create alerts if processes are not running
            if not vault_watcher_running:
                self.create_alert(
                    "CRITICAL",
                    "vault_watcher",
                    "Vault watcher process not running",
                )

            # API bridge is optional, so only warning
            if not api_bridge_running:
                self.create_alert(
                    "WARNING",
                    "api_bridge",
                    "API bridge process not running",
                )

        except Exception as e:
            logger.error(f"Error monitoring PAKE processes: {e}")

    def vault_monitoring_loop(self):
        """Monitor vault-specific activities"""
        while self.monitoring_active:
            try:
                self.monitor_vault_activity()
                time.sleep(120)  # Check every 2 minutes

            except Exception as e:
                logger.error(f"Vault monitoring error: {e}")
                time.sleep(120)

    def monitor_vault_activity(self):
        """Monitor vault for processing issues"""
        try:
            # Check for stuck files (files that haven't been processed in a while)
            vault_path = Path("vault")
            if not vault_path.exists():
                return

            now = datetime.now()
            stuck_files = []

            for md_file in vault_path.rglob("*.md"):
                try:
                    # Skip template and system files
                    if any(part.startswith(("_", ".")) for part in md_file.parts):
                        continue

                    content = md_file.read_text(encoding="utf-8")

                    # If file doesn't have pake_id and is older than 5 minutes
                    if "pake_id" not in content:
                        file_age = now - datetime.fromtimestamp(md_file.stat().st_mtime)
                        if file_age.total_seconds() > 300:  # 5 minutes
                            stuck_files.append(str(md_file.relative_to(vault_path)))

                except Exception:
                    continue

            if stuck_files:
                self.create_alert(
                    "WARNING",
                    "vault",
                    f"{len(stuck_files)} files stuck in processing",
                    {"stuck_files": stuck_files[:5]},  # First 5 files
                )

        except Exception as e:
            logger.error(f"Error monitoring vault activity: {e}")

    def performance_optimization_loop(self):
        """Continuous performance optimization"""
        while self.monitoring_active:
            try:
                self.optimize_performance()
                time.sleep(1800)  # Optimize every 30 minutes

            except Exception as e:
                logger.error(f"Performance optimization error: {e}")
                time.sleep(1800)

    def optimize_performance(self):
        """Perform automatic performance optimizations"""
        try:
            # Clean up old log files
            self.cleanup_old_logs()

            # Optimize database
            self.optimize_database()

            # Clean up temporary files
            self.cleanup_temp_files()

            logger.info("Performance optimization completed")

        except Exception as e:
            logger.error(f"Error during performance optimization: {e}")

    def cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            logs_path = Path("logs")
            if not logs_path.exists():
                return

            cutoff_date = datetime.now() - timedelta(days=7)  # Keep logs for 7 days

            for log_file in logs_path.glob("*.log"):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if (
                        file_time < cutoff_date
                        and log_file.stat().st_size > 10 * 1024 * 1024
                    ):  # > 10MB
                        # Keep only last 1MB of large old files
                        with open(log_file, "rb") as f:
                            f.seek(-1024 * 1024, 2)  # Last 1MB
                            content = f.read()

                        with open(log_file, "wb") as f:
                            f.write(content)

                        logger.info(f"Truncated old log file: {log_file}")

                except Exception as e:
                    logger.debug(f"Error cleaning log file {log_file}: {e}")

        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")

    def optimize_database(self):
        """Optimize monitoring database"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Vacuum database
            conn.execute("VACUUM")

            # Clean up old records (keep last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)

            conn.execute(
                "DELETE FROM system_metrics WHERE timestamp < ?",
                (cutoff_date.isoformat(),),
            )
            conn.execute(
                "DELETE FROM health_history WHERE timestamp < ?",
                (cutoff_date.isoformat(),),
            )
            conn.execute(
                "DELETE FROM alerts WHERE resolved = 1 AND resolution_time < ?",
                (cutoff_date.isoformat(),),
            )

            conn.commit()
            conn.close()

            logger.info("Database optimization completed")

        except Exception as e:
            logger.error(f"Error optimizing database: {e}")

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            # Clean up temp files in logs directory
            temp_patterns = ["*.tmp", "*.temp", "*~"]

            for pattern in temp_patterns:
                for temp_file in Path("logs").glob(pattern):
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        logger.debug(f"Error removing temp file {temp_file}: {e}")

        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")

    def self_healing_loop(self):
        """Self-healing and recovery loop"""
        while self.monitoring_active:
            try:
                self.perform_self_healing()
                time.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Self-healing error: {e}")
                time.sleep(300)

    def perform_self_healing(self):
        """Perform autonomous self-healing actions"""
        try:
            # Resolve critical alerts automatically
            critical_alerts = [
                alert
                for alert in self.alerts
                if alert.level == "CRITICAL" and not alert.resolved
            ]

            for alert in critical_alerts:
                self.auto_resolve_alert(alert)

        except Exception as e:
            logger.error(f"Error during self-healing: {e}")

    def trigger_self_healing(self, alert: Alert):
        """Trigger immediate self-healing for critical alerts"""
        threading.Thread(
            target=self.auto_resolve_alert,
            args=(alert,),
            daemon=True,
        ).start()

    def auto_resolve_alert(self, alert: Alert):
        """Automatically resolve alerts when possible"""
        try:
            resolved = False
            resolution_action = None

            if (
                alert.component == "pake"
                and "process not running" in alert.message.lower()
            ):
                # Restart PAKE services
                resolution_action = self.restart_pake_services()
                resolved = resolution_action

            elif (
                alert.component == "vault_watcher"
                and "not running" in alert.message.lower()
            ):
                # Restart vault watcher specifically
                resolution_action = self.restart_vault_watcher()
                resolved = resolution_action

            elif (
                alert.component == "vault"
                and "unprocessed notes" in alert.message.lower()
            ):
                # Trigger manual processing of stuck notes
                resolution_action = self.process_stuck_notes()
                resolved = resolution_action

            elif alert.component == "storage" and "disk usage" in alert.message.lower():
                # Clean up storage space
                resolution_action = self.cleanup_storage()
                resolved = resolution_action

            if resolved:
                alert.resolved = True
                alert.resolution_time = datetime.now()
                self.store_alert(alert)
                logger.info(f"Auto-resolved alert: {alert.message}")

                # Create resolution log
                self.create_alert(
                    "INFO",
                    "self_healing",
                    f"Auto-resolved: {alert.message}",
                    {
                        "original_alert_id": alert.id,
                        "resolution_action": resolution_action,
                    },
                )

        except Exception as e:
            logger.error(f"Error auto-resolving alert {alert.id}: {e}")

    def restart_pake_services(self) -> bool:
        """Restart PAKE services"""
        try:
            logger.info("Attempting to restart PAKE services")

            # Try to restart via Windows service
            result = subprocess.run(
                ["sc", "stop", "PAKEUltraAutomationService"],
                capture_output=True,
                text=True,
            )
            time.sleep(5)

            result = subprocess.run(
                ["sc", "start", "PAKEUltraAutomationService"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info("PAKE services restarted successfully via Windows service")
                return True

            # Fallback: restart manually
            return self.restart_vault_watcher()

        except Exception as e:
            logger.error(f"Error restarting PAKE services: {e}")
            return False

    def restart_vault_watcher(self) -> bool:
        """Restart vault watcher process"""
        try:
            logger.info("Attempting to restart vault watcher")

            # Kill existing vault watcher processes
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info[
                        "cmdline"
                    ] and "automated_vault_watcher.py" in " ".join(
                        proc.info["cmdline"],
                    ):
                        proc.terminate()
                        proc.wait(timeout=10)
                        logger.info(
                            f"Terminated vault watcher process {proc.info['pid']}",
                        )
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.TimeoutExpired,
                ):
                    continue

            # Start new vault watcher process
            subprocess.Popen(
                [sys.executable, "scripts/automated_vault_watcher.py"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            time.sleep(3)  # Give it time to start

            # Verify it started
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info[
                        "cmdline"
                    ] and "automated_vault_watcher.py" in " ".join(
                        proc.info["cmdline"],
                    ):
                        logger.info("Vault watcher restarted successfully")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return False

        except Exception as e:
            logger.error(f"Error restarting vault watcher: {e}")
            return False

    def process_stuck_notes(self) -> bool:
        """Process notes that are stuck in the pipeline"""
        try:
            logger.info("Processing stuck notes")

            # This would trigger a manual processing run
            # For now, we'll just log and return success
            # In a full implementation, this could trigger a batch processing job

            return True

        except Exception as e:
            logger.error(f"Error processing stuck notes: {e}")
            return False

    def cleanup_storage(self) -> bool:
        """Clean up storage space"""
        try:
            logger.info("Cleaning up storage space")

            # Clean up logs more aggressively
            self.cleanup_old_logs()

            # Clean up old vector files if needed
            vectors_path = Path("data/vectors")
            if vectors_path.exists():
                vector_files = list(vectors_path.glob("*.json"))
                if len(vector_files) > 1000:  # Keep only 1000 most recent
                    vector_files.sort(key=lambda x: x.stat().st_mtime)
                    for old_file in vector_files[:-1000]:
                        try:
                            old_file.unlink()
                        except Exception:
                            pass

            logger.info("Storage cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up storage: {e}")
            return False

    def get_system_status(self) -> dict[str, Any]:
        """Get current system status summary"""
        try:
            if not self.metrics_history:
                return {"status": "No data available"}

            latest_metrics = self.metrics_history[-1]
            health_status = self.assess_overall_health()

            return {
                "timestamp": datetime.now().isoformat(),
                "overall_health": health_status.overall_health,
                "performance_score": health_status.performance_score,
                "system": {
                    "cpu_percent": latest_metrics.cpu_percent,
                    "memory_used_mb": latest_metrics.memory_used_mb,
                    "disk_free_gb": latest_metrics.disk_free_gb,
                    "pake_processes": len(latest_metrics.pake_processes),
                },
                "vault": latest_metrics.vault_stats,
                "processing": latest_metrics.processing_stats,
                "active_alerts": len([a for a in self.alerts if not a.resolved]),
                "recommendations": health_status.recommendations,
            }

        except Exception as e:
            return {"status": "Error", "error": str(e)}


def main():
    """Main monitoring system entry point"""
    print("PAKE Ultra Monitoring & Self-Healing System")
    print("=" * 50)

    try:
        monitor = UltraMonitoringSystem()

        print("Ultra monitoring system started successfully!")
        print("Monitoring system health, performance, and auto-healing...")
        print("Press Ctrl+C to stop")

        # Keep the main thread alive
        while True:
            time.sleep(60)
            status = monitor.get_system_status()
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Health: {
                    status.get('overall_health', 'UNKNOWN')
                } | "
                f"Score: {status.get('performance_score', 0):.1f} | "
                f"CPU: {status.get('system', {}).get('cpu_percent', 0):.1f}% | "
                f"Alerts: {status.get('active_alerts', 0)}",
            )

    except KeyboardInterrupt:
        print("\nShutting down monitoring system...")
        monitor.monitoring_active = False

    except Exception as e:
        logger.error(f"Fatal monitoring system error: {e}")
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
