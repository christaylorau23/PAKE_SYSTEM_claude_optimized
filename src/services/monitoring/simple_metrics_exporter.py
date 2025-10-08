#!/usr/bin/env python3
# PAKE System - Simple Metrics Exporter
# Provides basic metrics for the Unified Quality Dashboard

import asyncio
import logging
import os
import signal
import sys

from aiohttp import web
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    generate_latest,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleMetricsExporter:
    """Simple metrics exporter for the Unified Quality Dashboard"""

    def __init__(self):
        self.registry = CollectorRegistry()

        # Code Quality Metrics
        self.code_smells = Gauge(
            "sonarqube_new_code_smells_total",
            "Number of new code smells",
            registry=self.registry,
        )

        self.duplication_percentage = Gauge(
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
            "sonarqube_new_critical_vulnerabilities_total",
            "Number of new critical vulnerabilities",
            registry=self.registry,
        )

        self.security_hotspots = Gauge(
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

        # CI/CD Health Metrics
        self.build_duration = Gauge(
            "github_actions_build_duration_seconds",
            "GitHub Actions build duration in seconds",
            registry=self.registry,
        )

        self.build_success_rate = Gauge(
            "github_actions_build_success_rate",
            "GitHub Actions build success rate",
            registry=self.registry,
        )

        # Development Velocity Metrics
        self.story_points = Gauge(
            "jira_story_points_completed_total",
            "Story points completed",
            registry=self.registry,
        )

        self.bug_ratio = Gauge(
            "jira_bug_to_feature_ratio", "Bug to feature ratio", registry=self.registry
        )

        # Set some sample values
        self._set_sample_values()

        self.app = web.Application()
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_get("/health", self.health_handler)
        self.app.router.add_get("/ready", self.ready_handler)

    def _set_sample_values(self):
        """Set sample values for demonstration"""
        # Code Quality - Good values
        self.code_smells.set(2)  # <5 per PR ✅
        self.duplication_percentage.set(1.5)  # <3% ✅
        self.cognitive_complexity.set(8)  # No increase ✅

        # Security - Good values
        self.critical_vulnerabilities.set(0)  # 0 ✅
        self.security_hotspots.set(1)  # Review Required ✅

        # Test Coverage - Good values
        self.coverage_new_code.set(85)  # >80% ✅
        self.coverage_overall.set(72)  # Increasing trend ✅

        # Technical Debt - Good values
        self.f821_errors.set(0)  # <500 ✅
        self.security_violations.set(3)  # <10 ✅

        # CI/CD Health - Good values
        self.build_duration.set(480)  # <10 mins ✅
        self.build_success_rate.set(98.5)  # >98% ✅

        # Development Velocity - Good values
        self.story_points.set(25)  # Stable/Increasing ✅
        self.bug_ratio.set(0.2)  # Decreasing trend ✅

    async def metrics_handler(self, request):
        """Handle /metrics endpoint for Prometheus scraping"""
        try:
            metrics_data = generate_latest(self.registry).decode("utf-8")
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
            text='{"status": "healthy", "service": "unified-quality-dashboard-exporter"}',
            content_type="application/json",
        )

    async def ready_handler(self, request):
        """Handle /ready endpoint for readiness checks"""
        return web.Response(
            text='{"status": "ready", "service": "unified-quality-dashboard-exporter"}',
            content_type="application/json",
        )

    async def start_server(self, host="0.0.0.0", port=9300):
        """Start the HTTP server"""
        logger.info(
            f"Starting Unified Quality Dashboard metrics exporter on {host}:{port}"
        )

        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(
            f"Unified Quality Dashboard metrics exporter started successfully on {host}:{port}"
        )

        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down Unified Quality Dashboard metrics exporter")
        finally:
            await runner.cleanup()


async def main():
    """Main entry point"""
    logger.info("Starting PAKE System Unified Quality Dashboard Metrics Exporter")

    exporter = SimpleMetricsExporter()

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
