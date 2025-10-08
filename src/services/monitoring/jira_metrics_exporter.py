#!/usr/bin/env python3
# PAKE System - Jira Metrics Exporter
# This service exposes Jira metrics via HTTP for Prometheus scraping
# Implements the Jira integration specified in the engineering guide

import asyncio
import logging
import os
import signal
import sys

import aiohttp
from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.services.monitoring.jira_metrics_collector import (
    JiraConfig,
    JiraMetricsCollector,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JiraMetricsExporter:
    """HTTP server that exposes Jira metrics for Prometheus scraping"""

    def __init__(self, config: JiraConfig):
        self.config = config
        self.collector = JiraMetricsCollector(config)
        self.app = web.Application()
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_get("/health", self.health_handler)
        self.app.router.add_get("/ready", self.ready_handler)

        # Collection interval (seconds)
        self.collection_interval = int(os.getenv("JIRA_COLLECTION_INTERVAL", "60"))
        self.collection_task = None

    async def metrics_handler(self, request):
        """Handle /metrics endpoint for Prometheus scraping"""
        try:
            # Collect fresh metrics
            await self.collector.collect_metrics()

            # Return metrics in Prometheus format
            metrics_data = self.collector.get_metrics()
            return web.Response(text=metrics_data, content_type=CONTENT_TYPE_LATEST)
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return web.Response(
                text=f"# Error generating metrics: {e}\n",
                content_type=CONTENT_TYPE_LATEST,
                status=500,
            )

    async def health_handler(self, request):
        """Handle /health endpoint for health checks"""
        return web.Response(
            text='{"status": "healthy", "service": "jira-metrics-exporter"}',
            content_type="application/json",
        )

    async def ready_handler(self, request):
        """Handle /ready endpoint for readiness checks"""
        try:
            # Test Jira connectivity
            async with self.collector as collector:
                # Simple API call to test connectivity
                await collector._make_request("myself")

            return web.Response(
                text='{"status": "ready", "service": "jira-metrics-exporter"}',
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
                logger.info("Jira metrics collected successfully")
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")

            await asyncio.sleep(self.collection_interval)

    async def start_server(self, host="0.0.0.0", port=9200):
        """Start the HTTP server"""
        logger.info(f"Starting Jira metrics exporter on {host}:{port}")

        # Start collection loop
        self.collection_task = asyncio.create_task(self.start_collection_loop())

        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(f"Jira metrics exporter started successfully on {host}:{port}")

        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down Jira metrics exporter")
        finally:
            await runner.cleanup()
            if self.collection_task:
                self.collection_task.cancel()


def create_config_from_env() -> JiraConfig:
    """Create Jira configuration from environment variables"""
    return JiraConfig(
        url=os.getenv("JIRA_URL", "https://your-org.atlassian.net"),
        username=os.getenv("JIRA_USERNAME", ""),
        token=os.getenv("JIRA_TOKEN", ""),
        project_key=os.getenv("JIRA_PROJECT_KEY", "PAKE"),
        api_version=os.getenv("JIRA_API_VERSION", "3"),
    )


async def main():
    """Main entry point"""
    logger.info("Starting PAKE System Jira Metrics Exporter")

    # Create configuration
    config = create_config_from_env()

    # Validate configuration
    if not config.url or not config.username or not config.token:
        logger.error(
            "Missing required Jira configuration. Please set JIRA_URL, JIRA_USERNAME, and JIRA_TOKEN environment variables."
        )
        sys.exit(1)

    # Create and start exporter
    exporter = JiraMetricsExporter(config)

    # Get server configuration
    host = os.getenv("EXPORTER_HOST", "0.0.0.0")
    port = int(os.getenv("EXPORTER_PORT", "9200"))

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
