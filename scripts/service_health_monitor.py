#!/usr/bin/env python3
"""
PAKE+ Service Health Monitoring System
Comprehensive monitoring, recovery, and alerting for all system components
"""

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
import psutil


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ServiceConfig:
    name: str
    type: str  # docker, process, http, database
    host: str = "localhost"
    port: int = None
    health_endpoint: str = None
    process_name: str = None
    container_name: str = None
    dependencies: list[str] = None
    critical: bool = True
    restart_command: str = None
    max_restart_attempts: int = 3
    check_interval: int = 30
    timeout: int = 10


@dataclass
class HealthResult:
    service_name: str
    status: HealthStatus
    response_time_ms: float
    error_message: str = None
    details: dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PAKEServiceMonitor:
    """Comprehensive PAKE+ service monitoring system"""

    def __init__(self, config_file: str = None):
        self.base_dir = Path(__file__).parent.parent
        self.logs_dir = self.base_dir / "logs"
        self.data_dir = self.base_dir / "data"
        self.db_path = self.data_dir / "health_monitoring.db"

        # Ensure directories exist
        for directory in [self.logs_dir, self.data_dir]:
            directory.mkdir(exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Load configuration
        self.services = self.load_service_configs(config_file)

        # Monitoring state
        self.health_history = {}
        self.restart_attempts = {}
        self.alerts_sent = {}
        self.monitoring_active = False

        # Initialize database
        self.init_database()

        self.logger.info("PAKE Service Monitor initialized")

    def setup_logging(self):
        """Setup comprehensive logging"""
        log_file = (
            self.logs_dir / f"health_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        self.logger = logging.getLogger("PAKEHealthMonitor")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def load_service_configs(self, config_file: str = None) -> dict[str, ServiceConfig]:
        """Load service configurations"""
        # Default service configurations
        default_services = {
            "postgres": ServiceConfig(
                name="PostgreSQL Database",
                type="database",
                host="localhost",
                port=5432,
                container_name="pake_postgres",
                critical=True,
                restart_command="docker restart pake_postgres",
            ),
            "redis": ServiceConfig(
                name="Redis Cache",
                type="database",
                host="localhost",
                port=6379,
                container_name="pake_redis",
                critical=True,
                restart_command="docker restart pake_redis",
            ),
            "mcp_server": ServiceConfig(
                name="MCP Server",
                type="http",
                host="localhost",
                port=8000,
                health_endpoint="http://localhost:8000/health",
                container_name="pake_mcp_server",
                dependencies=["postgres", "redis"],
                critical=True,
                restart_command="docker restart pake_mcp_server",
            ),
            "n8n": ServiceConfig(
                name="n8n Automation",
                type="http",
                host="localhost",
                port=5678,
                health_endpoint="http://localhost:5678",
                container_name="pake_n8n",
                dependencies=["postgres"],
                critical=False,
                restart_command="docker restart pake_n8n",
            ),
            "api_bridge": ServiceConfig(
                name="API Bridge",
                type="http",
                host="localhost",
                port=3000,
                health_endpoint="http://localhost:3000/health",
                process_name="node",
                dependencies=["mcp_server"],
                critical=True,
                restart_command="systemctl restart pake-api-bridge",
            ),
            "nginx": ServiceConfig(
                name="Nginx Proxy",
                type="http",
                host="localhost",
                port=80,
                health_endpoint="http://localhost/health",
                container_name="pake_nginx",
                dependencies=["mcp_server"],
                critical=False,
                restart_command="docker restart pake_nginx",
            ),
            "frontend": ServiceConfig(
                name="Frontend Application",
                type="http",
                host="localhost",
                port=3001,
                health_endpoint="http://localhost:3001",
                process_name="next-server",
                dependencies=[],
                critical=False,
                restart_command="systemctl restart pake-frontend",
            ),
        }

        # Load custom config if provided
        if config_file and Path(config_file).exists():
            try:
                with open(config_file) as f:
                    custom_config = json.load(f)

                for service_name, config_data in custom_config.items():
                    if service_name in default_services:
                        # Update existing service config
                        service = default_services[service_name]
                        for key, value in config_data.items():
                            if hasattr(service, key):
                                setattr(service, key, value)
                    else:
                        # Add new service
                        default_services[service_name] = ServiceConfig(**config_data)

            except Exception as e:
                self.logger.warning(f"Failed to load custom config: {e}")

        return default_services

    def init_database(self):
        """Initialize SQLite database for health history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time_ms REAL,
                error_message TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(service_name),
                INDEX(timestamp),
                INDEX(status)
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                INDEX(service_name),
                INDEX(alert_level),
                INDEX(resolved)
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS restart_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                command TEXT,
                success BOOLEAN,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(service_name),
                INDEX(timestamp)
            )
        """,
        )

        conn.commit()
        conn.close()

    async def check_service_health(self, service_name: str) -> HealthResult:
        """Check health of a specific service"""
        service = self.services.get(service_name)
        if not service:
            return HealthResult(
                service_name,
                HealthStatus.UNKNOWN,
                0.0,
                "Service configuration not found",
            )

        start_time = time.time()

        try:
            if service.type == "http":
                result = await self._check_http_health(service)
            elif service.type == "database":
                result = await self._check_database_health(service)
            elif service.type == "process":
                result = await self._check_process_health(service)
            elif service.type == "docker":
                result = await self._check_docker_health(service)
            else:
                result = HealthResult(
                    service_name,
                    HealthStatus.UNKNOWN,
                    0.0,
                    f"Unknown service type: {service.type}",
                )

        except Exception as e:
            result = HealthResult(
                service_name,
                HealthStatus.CRITICAL,
                0.0,
                f"Health check failed: {str(e)}",
            )

        # Calculate response time
        result.response_time_ms = (time.time() - start_time) * 1000

        # Store in database
        self._store_health_result(result)

        return result

    async def _check_http_health(self, service: ServiceConfig) -> HealthResult:
        """Check HTTP service health"""
        url = service.health_endpoint or f"http://{service.host}:{service.port}"

        try:
            timeout = aiohttp.ClientTimeout(total=service.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status < 400:
                        return HealthResult(
                            service.name,
                            HealthStatus.HEALTHY,
                            0.0,
                            details={"status_code": response.status, "url": url},
                        )
                    return HealthResult(
                        service.name,
                        HealthStatus.UNHEALTHY,
                        0.0,
                        f"HTTP {response.status}",
                        details={"status_code": response.status, "url": url},
                    )

        except TimeoutError:
            return HealthResult(
                service.name,
                HealthStatus.UNHEALTHY,
                0.0,
                "Connection timeout",
                details={"url": url, "timeout": service.timeout},
            )
        except Exception as e:
            return HealthResult(
                service.name,
                HealthStatus.CRITICAL,
                0.0,
                str(e),
                details={"url": url},
            )

    async def _check_database_health(self, service: ServiceConfig) -> HealthResult:
        """Check database service health"""
        try:
            # Try to establish connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(service.host, service.port),
                timeout=service.timeout,
            )

            writer.close()
            await writer.wait_closed()

            return HealthResult(
                service.name,
                HealthStatus.HEALTHY,
                0.0,
                details={"host": service.host, "port": service.port},
            )

        except TimeoutError:
            return HealthResult(
                service.name,
                HealthStatus.UNHEALTHY,
                0.0,
                "Connection timeout",
            )
        except Exception as e:
            return HealthResult(service.name, HealthStatus.CRITICAL, 0.0, str(e))

    async def _check_process_health(self, service: ServiceConfig) -> HealthResult:
        """Check process health"""
        try:
            # Find process by name
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                if service.process_name in proc.info["name"] or any(
                    service.process_name in cmd for cmd in (proc.info["cmdline"] or [])
                ):
                    processes.append(proc)

            if not processes:
                return HealthResult(
                    service.name,
                    HealthStatus.CRITICAL,
                    0.0,
                    f"Process '{service.process_name}' not found",
                )

            # Check if processes are responsive
            healthy_processes = 0
            total_processes = len(processes)

            for proc in processes:
                try:
                    # Check if process is running and responsive
                    if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                        healthy_processes += 1
                except BaseException:
                    pass

            if healthy_processes == 0:
                return HealthResult(
                    service.name,
                    HealthStatus.CRITICAL,
                    0.0,
                    "All processes unresponsive",
                )
            if healthy_processes < total_processes:
                return HealthResult(
                    service.name,
                    HealthStatus.DEGRADED,
                    0.0,
                    f"{healthy_processes}/{total_processes} processes healthy",
                )
            return HealthResult(
                service.name,
                HealthStatus.HEALTHY,
                0.0,
                details={"process_count": total_processes},
            )

        except Exception as e:
            return HealthResult(service.name, HealthStatus.UNKNOWN, 0.0, str(e))

    async def _check_docker_health(self, service: ServiceConfig) -> HealthResult:
        """Check Docker container health"""
        try:
            cmd = ["docker", "inspect", service.container_name]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return HealthResult(
                    service.name,
                    HealthStatus.CRITICAL,
                    0.0,
                    f"Container not found: {service.container_name}",
                )

            # Parse Docker inspect output
            container_info = json.loads(stdout.decode())[0]
            state = container_info.get("State", {})

            if not state.get("Running", False):
                return HealthResult(
                    service.name,
                    HealthStatus.CRITICAL,
                    0.0,
                    f"Container not running: {state.get('Status', 'unknown')}",
                )

            # Check health status if available
            health = state.get("Health", {})
            if health:
                health_status = health.get("Status", "")
                if health_status == "healthy":
                    return HealthResult(service.name, HealthStatus.HEALTHY, 0.0)
                if health_status == "unhealthy":
                    return HealthResult(
                        service.name,
                        HealthStatus.UNHEALTHY,
                        0.0,
                        "Container health check failed",
                    )

            # Container is running but no health check defined
            return HealthResult(
                service.name,
                HealthStatus.HEALTHY,
                0.0,
                details={"container_id": container_info.get("Id", "")[:12]},
            )

        except Exception as e:
            return HealthResult(service.name, HealthStatus.UNKNOWN, 0.0, str(e))

    def _store_health_result(self, result: HealthResult):
        """Store health check result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO health_checks
                (service_name, status, response_time_ms, error_message, details)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    result.service_name,
                    result.status.value,
                    result.response_time_ms,
                    result.error_message,
                    json.dumps(result.details) if result.details else None,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store health result: {e}")

    async def check_all_services(self) -> dict[str, HealthResult]:
        """Check health of all services"""
        self.logger.info("Checking health of all services...")

        results = {}

        # Create tasks for all health checks
        tasks = []
        for service_name in self.services:
            task = asyncio.create_task(
                self.check_service_health(service_name),
                name=f"health_check_{service_name}",
            )
            tasks.append((service_name, task))

        # Wait for all health checks to complete
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result

                status_icon = self._get_status_icon(result.status)
                self.logger.info(
                    f"{status_icon} {service_name}: {result.status.value} "
                    f"({result.response_time_ms:.1f}ms)",
                )

                if result.error_message:
                    self.logger.warning(f"  Error: {result.error_message}")

            except Exception as e:
                self.logger.error(f"Health check failed for {service_name}: {e}")
                results[service_name] = HealthResult(
                    service_name,
                    HealthStatus.UNKNOWN,
                    0.0,
                    str(e),
                )

        # Process results and handle alerts/recovery
        await self._process_health_results(results)

        return results

    def _get_status_icon(self, status: HealthStatus) -> str:
        """Get emoji icon for health status"""
        icons = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.CRITICAL: "🔥",
            HealthStatus.UNKNOWN: "❓",
        }
        return icons.get(status, "❓")

    async def _process_health_results(self, results: dict[str, HealthResult]):
        """Process health results and trigger recovery actions"""
        for service_name, result in results.items():
            service = self.services[service_name]

            # Check if service health changed
            previous_status = self.health_history.get(
                service_name,
                HealthStatus.UNKNOWN,
            )
            self.health_history[service_name] = result.status

            # Handle critical services that are unhealthy
            if service.critical and result.status in [
                HealthStatus.UNHEALTHY,
                HealthStatus.CRITICAL,
            ]:
                await self._handle_service_failure(service_name, service, result)

            # Generate alerts for status changes
            if previous_status != result.status:
                await self._generate_alert(service_name, result, previous_status)

    async def _handle_service_failure(
        self,
        service_name: str,
        service: ServiceConfig,
        result: HealthResult,
    ):
        """Handle service failure with recovery attempts"""
        restart_count = self.restart_attempts.get(service_name, 0)

        if restart_count >= service.max_restart_attempts:
            self.logger.critical(
                f"Service {service_name} exceeded max restart attempts ({restart_count})",
            )
            await self._generate_alert(
                service_name,
                result,
                None,
                AlertLevel.CRITICAL,
                f"Service failed after {restart_count} restart attempts",
            )
            return

        # Check dependencies before restarting
        if service.dependencies:
            for dep in service.dependencies:
                dep_status = self.health_history.get(dep, HealthStatus.UNKNOWN)
                if dep_status != HealthStatus.HEALTHY:
                    self.logger.warning(
                        f"Cannot restart {service_name}: dependency {dep} is {
                            dep_status.value
                        }",
                    )
                    return

        # Attempt to restart service
        if service.restart_command:
            self.logger.info(
                f"Attempting to restart {service_name} (attempt {restart_count + 1})",
            )

            success = await self._restart_service(service_name, service.restart_command)

            self.restart_attempts[service_name] = restart_count + 1

            if success:
                self.logger.info(f"Successfully restarted {service_name}")
                # Wait a bit before next health check
                await asyncio.sleep(10)
            else:
                self.logger.error(f"Failed to restart {service_name}")

    async def _restart_service(self, service_name: str, command: str) -> bool:
        """Restart a service using the provided command"""
        try:
            self.logger.info(f"Executing restart command for {service_name}: {command}")

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60,  # 1 minute timeout for restart
            )

            success = process.returncode == 0

            # Log restart attempt
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO restart_attempts
                (service_name, command, success, error_message)
                VALUES (?, ?, ?, ?)
            """,
                (service_name, command, success, stderr.decode() if stderr else None),
            )

            conn.commit()
            conn.close()

            if not success:
                self.logger.error(f"Restart command failed: {stderr.decode()}")

            return success

        except TimeoutError:
            self.logger.error(f"Restart command timed out for {service_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error executing restart command: {e}")
            return False

    async def _generate_alert(
        self,
        service_name: str,
        result: HealthResult,
        previous_status: HealthStatus = None,
        level: AlertLevel = None,
        custom_message: str = None,
    ):
        """Generate and send alerts for service status changes"""
        if level is None:
            level = self._determine_alert_level(result.status)

        if custom_message:
            message = custom_message
        else:
            if previous_status:
                message = f"Service {service_name} status changed from {
                    previous_status.value
                } to {result.status.value}"
            else:
                message = f"Service {service_name} is {result.status.value}"

        if result.error_message:
            message += f" - {result.error_message}"

        # Store alert in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO alerts (service_name, alert_level, message)
            VALUES (?, ?, ?)
        """,
            (service_name, level.value, message),
        )

        conn.commit()
        conn.close()

        # Log alert
        log_method = {
            AlertLevel.INFO: self.logger.info,
            AlertLevel.WARNING: self.logger.warning,
            AlertLevel.ERROR: self.logger.error,
            AlertLevel.CRITICAL: self.logger.critical,
        }.get(level, self.logger.info)

        log_method(f"ALERT [{level.value.upper()}] {message}")

    def _determine_alert_level(self, status: HealthStatus) -> AlertLevel:
        """Determine alert level based on health status"""
        mapping = {
            HealthStatus.HEALTHY: AlertLevel.INFO,
            HealthStatus.DEGRADED: AlertLevel.WARNING,
            HealthStatus.UNHEALTHY: AlertLevel.ERROR,
            HealthStatus.CRITICAL: AlertLevel.CRITICAL,
            HealthStatus.UNKNOWN: AlertLevel.WARNING,
        }
        return mapping.get(status, AlertLevel.WARNING)

    async def start_monitoring(self, check_interval: int = 30):
        """Start continuous monitoring loop"""
        self.monitoring_active = True
        self.logger.info(
            f"Starting continuous monitoring (interval: {check_interval}s)",
        )

        while self.monitoring_active:
            try:
                await self.check_all_services()
                await asyncio.sleep(check_interval)
            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(check_interval)

        self.logger.info("Monitoring stopped")

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall system health summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get latest status for each service
        cursor.execute(
            """
            SELECT service_name, status, error_message, timestamp
            FROM health_checks h1
            WHERE timestamp = (
                SELECT MAX(timestamp)
                FROM health_checks h2
                WHERE h2.service_name = h1.service_name
            )
            ORDER BY service_name
        """,
        )

        services_status = {}
        overall_healthy = True
        critical_services_down = 0

        for row in cursor.fetchall():
            service_name, status, error, timestamp = row
            services_status[service_name] = {
                "status": status,
                "error_message": error,
                "last_check": timestamp,
                "critical": self.services.get(
                    service_name,
                    ServiceConfig("", ""),
                ).critical,
            }

            if status in ["unhealthy", "critical"]:
                overall_healthy = False
                if services_status[service_name]["critical"]:
                    critical_services_down += 1

        # Get recent alerts
        cursor.execute(
            """
            SELECT alert_level, COUNT(*) as count
            FROM alerts
            WHERE timestamp > datetime('now', '-1 hour')
            AND resolved = FALSE
            GROUP BY alert_level
        """,
        )

        recent_alerts = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "critical_services_down": critical_services_down,
            "services": services_status,
            "recent_alerts": recent_alerts,
            "timestamp": datetime.now().isoformat(),
        }

    def generate_health_report(self, hours: int = 24) -> str:
        """Generate detailed health report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        report = f"""
# PAKE+ System Health Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Report Period: Last {hours} hours

## System Overview
"""

        summary = self.get_health_summary()

        report += f"""
- **Overall Status**: {summary["overall_status"].upper()}
- **Critical Services Down**: {summary["critical_services_down"]}
- **Total Services Monitored**: {len(summary["services"])}

## Service Status
"""

        for service_name, info in summary["services"].items():
            status_icon = self._get_status_icon(HealthStatus(info["status"]))
            criticality = "🔥 CRITICAL" if info["critical"] else "ℹ️  Optional"

            report += f"- **{service_name}** ({criticality}): {status_icon} {
                info['status'].upper()
            }\n"
            if info["error_message"]:
                report += f"  - Error: {info['error_message']}\n"
            report += f"  - Last Check: {info['last_check']}\n\n"

        # Recent alerts
        if summary["recent_alerts"]:
            report += "## Recent Alerts (Last Hour)\n"
            for level, count in summary["recent_alerts"].items():
                report += f"- **{level.upper()}**: {count}\n"
            report += "\n"

        # Health check history
        cursor.execute(
            f"""
            SELECT service_name, status, COUNT(*) as count,
                   AVG(response_time_ms) as avg_response_time
            FROM health_checks
            WHERE timestamp > datetime('now', '-{hours} hours')
            GROUP BY service_name, status
            ORDER BY service_name, status
        """,
        )

        report += "## Health Check Statistics\n"
        service_stats = {}

        for row in cursor.fetchall():
            service_name, status, count, avg_time = row
            if service_name not in service_stats:
                service_stats[service_name] = {}
            service_stats[service_name][status] = {
                "count": count,
                "avg_response_time": avg_time or 0,
            }

        for service_name, stats in service_stats.items():
            report += f"\n### {service_name}\n"
            for status, data in stats.items():
                report += f"- **{status}**: {data['count']} checks (avg: {
                    data['avg_response_time']:.1f}ms)\n"

        # Recent restart attempts
        cursor.execute(
            f"""
            SELECT service_name, COUNT(*) as attempts,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
            FROM restart_attempts
            WHERE timestamp > datetime('now', '-{hours} hours')
            GROUP BY service_name
        """,
        )

        restart_stats = cursor.fetchall()
        if restart_stats:
            report += "\n## Restart Attempts\n"
            for service_name, attempts, successful in restart_stats:
                report += f"- **{service_name}**: {successful}/{attempts} successful\n"

        conn.close()

        report += f"\n---\n*Generated by PAKE+ Service Monitor at {datetime.now()}*\n"

        return report


async def main():
    """Main entry point for health monitoring"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE+ Service Health Monitor")
    parser.add_argument(
        "command",
        choices=["check", "monitor", "report", "status"],
        help="Command to execute",
    )
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Monitoring interval in seconds",
    )
    parser.add_argument("--service", help="Specific service to check")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours of history for reports",
    )
    parser.add_argument("--output", help="Output file for reports")

    args = parser.parse_args()

    monitor = PAKEServiceMonitor(args.config)

    if args.command == "check":
        if args.service:
            result = await monitor.check_service_health(args.service)
            print(f"{args.service}: {result.status.value}")
            if result.error_message:
                print(f"Error: {result.error_message}")
        else:
            results = await monitor.check_all_services()
            for service_name, result in results.items():
                status_icon = monitor._get_status_icon(result.status)
                print(f"{status_icon} {service_name}: {result.status.value}")

    elif args.command == "monitor":
        await monitor.start_monitoring(args.interval)

    elif args.command == "status":
        summary = monitor.get_health_summary()
        print(json.dumps(summary, indent=2))

    elif args.command == "report":
        report = monitor.generate_health_report(args.hours)

        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"Report saved to {args.output}")
        else:
            print(report)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback

        traceback.print_exc()
