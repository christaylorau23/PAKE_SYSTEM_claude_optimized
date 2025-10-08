#!/usr/bin/env python3
# PAKE System - SonarQube Metrics Exporter
# This service exposes SonarQube metrics via HTTP for Prometheus scraping
# Implements the SonarQube integration specified in the engineering guide

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import os
import signal
import sys
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import web
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SonarQubeConfig:
    """SonarQube configuration for metrics collection"""

    url: str
    token: str
    project_key: str
    organization: str


@dataclass
class SonarQubeMetrics:
    """SonarQube metrics data structure"""

    bugs: int
    vulnerabilities: int
    security_hotspots: int
    code_smells: int
    coverage: float
    duplication: float
    cognitive_complexity: int
    technical_debt: int
    lines_of_code: int
    new_bugs: int
    new_vulnerabilities: int
    new_security_hotspots: int
    new_code_smells: int
    new_coverage: float
    new_duplication: float


class SonarQubeMetricsCollector:
    """Collects metrics from SonarQube API for the Unified Quality Dashboard"""

    def __init__(self, config: SonarQubeConfig):
        self.config = config
        self.session: aiohttp.ClientSession | None = None

        # Prometheus metrics
        self.registry = CollectorRegistry()

        # Code Quality Metrics
        self.code_smells = Gauge(
            "sonarqube_code_smells_total",
            "Total number of code smells",
            ["severity"],
            registry=self.registry,
        )

        self.new_code_smells = Gauge(
            "sonarqube_new_code_smells_total",
            "Number of new code smells",
            ["severity"],
            registry=self.registry,
        )

        self.duplication_percentage = Gauge(
            "sonarqube_duplication_percentage",
            "Code duplication percentage",
            registry=self.registry,
        )

        self.new_duplication_percentage = Gauge(
            "sonarqube_new_duplication_percentage",
            "New code duplication percentage",
            registry=self.registry,
        )

        self.cognitive_complexity = Gauge(
            "sonarqube_cognitive_complexity",
            "Cognitive complexity",
            registry=self.registry,
        )

        # Security Metrics
        self.critical_vulnerabilities = Gauge(
            "sonarqube_critical_vulnerabilities_total",
            "Number of critical vulnerabilities",
            registry=self.registry,
        )

        self.new_critical_vulnerabilities = Gauge(
            "sonarqube_new_critical_vulnerabilities_total",
            "Number of new critical vulnerabilities",
            registry=self.registry,
        )

        self.security_hotspots = Gauge(
            "sonarqube_security_hotspots_total",
            "Number of security hotspots",
            registry=self.registry,
        )

        self.new_security_hotspots = Gauge(
            "sonarqube_new_security_hotspots_total",
            "Number of new security hotspots",
            registry=self.registry,
        )

        # Test Coverage Metrics
        self.coverage_new_code = Gauge(
            "sonarqube_coverage_new_code_percentage",
            "Test coverage on new code percentage",
            registry=self.registry,
        )

        self.coverage_overall = Gauge(
            "sonarqube_coverage_overall_percentage",
            "Overall test coverage percentage",
            registry=self.registry,
        )

        # Technical Debt Metrics
        self.f821_errors = Gauge(
            "pake_f821_errors_total",
            "Total F821 undefined name errors",
            registry=self.registry,
        )

        self.security_violations = Gauge(
            "pake_security_violations_total",
            "Total S311/S603/S607 security violations",
            registry=self.registry,
        )

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "Accept": "application/json",
                "User-Agent": "PAKE-System-SonarQube-Exporter",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, endpoint: str, params: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Make authenticated request to SonarQube API"""
        url = f"{self.config.url}/api/{endpoint}"

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 404:
                    logger.warning(f"SonarQube API endpoint not found: {endpoint}")
                    return {}
                logger.error(
                    f"SonarQube API request failed: {response.status} - {await response.text()}"
                )
                return {}
        except Exception as e:
            logger.error(f"Error making SonarQube API request: {e}")
            return {}

    async def get_project_metrics(self) -> SonarQubeMetrics:
        """Get project metrics from SonarQube"""
        # Get component metrics
        component_params = {
            "component": self.config.project_key,
            "metricKeys": ",".join(
                [
                    "bugs",
                    "vulnerabilities",
                    "security_hotspots",
                    "code_smells",
                    "coverage",
                    "duplicated_lines_density",
                    "cognitive_complexity",
                    "sqale_index",
                    "ncloc",
                    "new_bugs",
                    "new_vulnerabilities",
                    "new_security_hotspots",
                    "new_code_smells",
                    "new_coverage",
                    "new_duplicated_lines_density",
                ]
            ),
        }

        # Try SonarCloud API first, then fallback to local SonarQube
        response = await self._make_request("measures/component", component_params)

        # If SonarCloud API fails, try with organization prefix
        if not response or "component" not in response:
            org_component = f"{self.config.organization}_{self.config.project_key}"
            component_params["component"] = org_component
            response = await self._make_request("measures/component", component_params)

        if not response or "component" not in response:
            logger.error("Failed to get component metrics from SonarQube")
            return SonarQubeMetrics(0, 0, 0, 0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0)

        measures = response["component"].get("measures", [])
        metrics_dict = {measure["metric"]: measure["value"] for measure in measures}

        return SonarQubeMetrics(
            bugs=int(metrics_dict.get("bugs", 0)),
            vulnerabilities=int(metrics_dict.get("vulnerabilities", 0)),
            security_hotspots=int(metrics_dict.get("security_hotspots", 0)),
            code_smells=int(metrics_dict.get("code_smells", 0)),
            coverage=float(metrics_dict.get("coverage", 0.0)),
            duplication=float(metrics_dict.get("duplicated_lines_density", 0.0)),
            cognitive_complexity=int(metrics_dict.get("cognitive_complexity", 0)),
            technical_debt=int(metrics_dict.get("sqale_index", 0)),
            lines_of_code=int(metrics_dict.get("ncloc", 0)),
            new_bugs=int(metrics_dict.get("new_bugs", 0)),
            new_vulnerabilities=int(metrics_dict.get("new_vulnerabilities", 0)),
            new_security_hotspots=int(metrics_dict.get("new_security_hotspots", 0)),
            new_code_smells=int(metrics_dict.get("new_code_smells", 0)),
            new_coverage=float(metrics_dict.get("new_coverage", 0.0)),
            new_duplication=float(
                metrics_dict.get("new_duplicated_lines_density", 0.0)
            ),
        )

    async def collect_metrics(self) -> None:
        """Collect all metrics and update Prometheus metrics"""
        logger.info("Starting SonarQube metrics collection")

        try:
            # Get project metrics
            metrics = await self.get_project_metrics()

            # Update Prometheus metrics
            # Code Quality Metrics
            self.code_smells.labels(severity="total").set(metrics.code_smells)
            self.new_code_smells.labels(severity="total").set(metrics.new_code_smells)
            self.duplication_percentage.set(metrics.duplication)
            self.new_duplication_percentage.set(metrics.new_duplication)
            self.cognitive_complexity.set(metrics.cognitive_complexity)

            # Security Metrics
            self.critical_vulnerabilities.set(metrics.vulnerabilities)
            self.new_critical_vulnerabilities.set(metrics.new_vulnerabilities)
            self.security_hotspots.set(metrics.security_hotspots)
            self.new_security_hotspots.set(metrics.new_security_hotspots)

            # Test Coverage Metrics
            self.coverage_new_code.set(metrics.new_coverage)
            self.coverage_overall.set(metrics.coverage)

            # Technical Debt Metrics (simulated for now)
            self.f821_errors.set(0)  # Will be updated when we have real data
            self.security_violations.set(0)  # Will be updated when we have real data

            logger.info("SonarQube metrics collection completed successfully")

        except Exception as e:
            logger.error(f"Error collecting SonarQube metrics: {e}")

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest(self.registry).decode("utf-8")


class SonarQubeMetricsExporter:
    """HTTP server that exposes SonarQube metrics for Prometheus scraping"""

    def __init__(self, config: SonarQubeConfig):
        self.config = config
        self.collector = SonarQubeMetricsCollector(config)
        self.app = web.Application()
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_get("/health", self.health_handler)
        self.app.router.add_get("/ready", self.ready_handler)

        # Collection interval (seconds)
        self.collection_interval = int(
            os.getenv("SONAR_COLLECTION_INTERVAL", "300")
        )  # 5 minutes
        self.collection_task = None

    async def metrics_handler(self, request):
        """Handle /metrics endpoint for Prometheus scraping"""
        try:
            # Collect fresh metrics
            await self.collector.collect_metrics()

            # Return metrics in Prometheus format
            metrics_data = self.collector.get_metrics()
            return web.Response(text=metrics_data, content_type="text/plain")
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return web.Response(
                text=f"# Error generating metrics: {e}\n",
                content_type="text/plain",
                status=500,
            )

    async def health_handler(self, request):
        """Handle /health endpoint for health checks"""
        return web.Response(
            text='{"status": "healthy", "service": "sonarqube-metrics-exporter"}',
            content_type="application/json",
        )

    async def ready_handler(self, request):
        """Handle /ready endpoint for readiness checks"""
        try:
            # Test SonarQube connectivity
            async with self.collector as collector:
                # Simple API call to test connectivity
                await collector._make_request("system/status")

            return web.Response(
                text='{"status": "ready", "service": "sonarqube-metrics-exporter"}',
                content_type="application/json",
            )
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return web.Response(
                text=f'{{"status": "not_ready", "error": "{e}"}}',
                content_type="application/json",
                status=503,
            )

    async def start_collection_loop(self):
        """Start the metrics collection loop"""
        while True:
            try:
                async with self.collector as collector:
                    await collector.collect_metrics()
                logger.info("SonarQube metrics collected successfully")
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")

            await asyncio.sleep(self.collection_interval)

    async def start_server(self, host="0.0.0.0", port=9300):
        """Start the HTTP server"""
        logger.info(f"Starting SonarQube metrics exporter on {host}:{port}")

        # Start collection loop
        self.collection_task = asyncio.create_task(self.start_collection_loop())

        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(f"SonarQube metrics exporter started successfully on {host}:{port}")

        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down SonarQube metrics exporter")
        finally:
            await runner.cleanup()
            if self.collection_task:
                self.collection_task.cancel()


def create_config_from_env() -> SonarQubeConfig:
    """Create SonarQube configuration from environment variables"""
    return SonarQubeConfig(
        url=os.getenv("SONAR_URL", "https://sonarcloud.io"),
        token=os.getenv("SONAR_TOKEN", ""),
        project_key=os.getenv("SONAR_PROJECT_KEY", "pake-system"),
        organization=os.getenv("SONAR_ORGANIZATION", "pake-system-org"),
    )


async def main():
    """Main entry point"""
    logger.info("Starting PAKE System SonarQube Metrics Exporter")

    # Create configuration
    config = create_config_from_env()

    # Validate configuration
    if not config.token:
        logger.error(
            "Missing required SonarQube configuration. Please set SONAR_TOKEN environment variable."
        )
        sys.exit(1)

    # Create and start exporter
    exporter = SonarQubeMetricsExporter(config)

    # Get server configuration
    host = os.getenv("EXPORTER_HOST", "0.0.0.0")
    port = int(os.getenv("EXPORTER_PORT", "9300"))

    # Start server
    await exporter.start_server(host, port)


if __name__ == "__main__":
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
