#!/usr/bin/env python3
# PAKE System - GitHub Actions Metrics Exporter
# This service exposes GitHub Actions metrics via HTTP for Prometheus scraping
# Implements the CI/CD metrics collection specified in the engineering guide

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
class GitHubConfig:
    """GitHub configuration for metrics collection"""

    token: str
    org: str
    repo: str
    api_url: str = "https://api.github.com"


@dataclass
class WorkflowRun:
    """GitHub Actions workflow run data"""

    id: int
    name: str
    status: str
    conclusion: str
    created_at: datetime
    updated_at: datetime
    duration: int
    success: bool


class GitHubActionsMetricsCollector:
    """Collects metrics from GitHub Actions API for the Unified Quality Dashboard"""

    def __init__(self, config: GitHubConfig):
        self.config = config
        self.session: aiohttp.ClientSession | None = None

        # Prometheus metrics
        self.registry = CollectorRegistry()

        # Build metrics
        self.build_duration = Histogram(
            "github_actions_build_duration_seconds",
            "GitHub Actions build duration in seconds",
            ["workflow", "status", "conclusion"],
            registry=self.registry,
        )

        self.builds_total = Counter(
            "github_actions_builds_total",
            "Total GitHub Actions builds",
            ["workflow", "status", "conclusion"],
            registry=self.registry,
        )

        self.build_success_rate = Gauge(
            "github_actions_build_success_rate",
            "GitHub Actions build success rate",
            ["workflow"],
            registry=self.registry,
        )

        self.build_failure_rate = Gauge(
            "github_actions_build_failure_rate",
            "GitHub Actions build failure rate",
            ["workflow"],
            registry=self.registry,
        )

        self.avg_build_time = Gauge(
            "github_actions_avg_build_time_seconds",
            "Average GitHub Actions build time",
            ["workflow"],
            registry=self.registry,
        )

        self.pr_build_time = Histogram(
            "github_actions_pr_build_duration_seconds",
            "GitHub Actions PR build duration",
            ["workflow"],
            registry=self.registry,
        )

        self.workflow_runs_total = Counter(
            "github_actions_workflow_runs_total",
            "Total GitHub Actions workflow runs",
            ["workflow", "event_type"],
            registry=self.registry,
        )

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"token {self.config.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "PAKE-System-Metrics-Collector",
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
        """Make authenticated request to GitHub API"""
        url = f"{self.config.api_url}/repos/{self.config.org}/{self.config.repo}/{endpoint}"

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 404:
                    logger.warning(f"GitHub API endpoint not found: {endpoint}")
                    return {}
                logger.error(
                    f"GitHub API request failed: {response.status} - {await response.text()}"
                )
                return {}
        except Exception as e:
            logger.error(f"Error making GitHub API request: {e}")
            return {}

    async def get_workflow_runs(
        self, workflow_id: str = None, per_page: int = 100
    ) -> list[WorkflowRun]:
        """Get workflow runs from GitHub Actions"""
        endpoint = "actions/runs"
        params = {"per_page": per_page, "page": 1}

        if workflow_id:
            params["workflow_id"] = workflow_id

        response = await self._make_request(endpoint, params)
        runs_data = response.get("workflow_runs", [])

        runs = []
        for run_data in runs_data:
            try:
                created_at = datetime.fromisoformat(
                    run_data["created_at"].replace("Z", "+00:00")
                )
                updated_at = datetime.fromisoformat(
                    run_data["updated_at"].replace("Z", "+00:00")
                )

                # Calculate duration
                duration = 0
                if run_data["conclusion"] and run_data["conclusion"] != "cancelled":
                    duration = (updated_at - created_at).total_seconds()

                run = WorkflowRun(
                    id=run_data["id"],
                    name=run_data["name"],
                    status=run_data["status"],
                    conclusion=run_data["conclusion"] or "unknown",
                    created_at=created_at,
                    updated_at=updated_at,
                    duration=duration,
                    success=run_data["conclusion"] == "success",
                )
                runs.append(run)

            except Exception as e:
                logger.error(f"Error parsing workflow run data: {e}")
                continue

        return runs

    async def get_workflows(self) -> list[dict[str, Any]]:
        """Get all workflows for the repository"""
        endpoint = "actions/workflows"
        response = await self._make_request(endpoint)
        return response.get("workflows", [])

    async def get_pr_workflow_runs(self, days: int = 7) -> list[WorkflowRun]:
        """Get workflow runs triggered by pull requests"""
        since = datetime.now() - timedelta(days=days)

        endpoint = "actions/runs"
        params = {"per_page": 100, "page": 1, "created": since.isoformat()}

        response = await self._make_request(endpoint, params)
        runs_data = response.get("workflow_runs", [])

        # Filter for PR-triggered runs
        pr_runs = []
        for run_data in runs_data:
            if run_data.get("event") == "pull_request":
                try:
                    created_at = datetime.fromisoformat(
                        run_data["created_at"].replace("Z", "+00:00")
                    )
                    updated_at = datetime.fromisoformat(
                        run_data["updated_at"].replace("Z", "+00:00")
                    )

                    duration = 0
                    if run_data["conclusion"] and run_data["conclusion"] != "cancelled":
                        duration = (updated_at - created_at).total_seconds()

                    run = WorkflowRun(
                        id=run_data["id"],
                        name=run_data["name"],
                        status=run_data["status"],
                        conclusion=run_data["conclusion"] or "unknown",
                        created_at=created_at,
                        updated_at=updated_at,
                        duration=duration,
                        success=run_data["conclusion"] == "success",
                    )
                    pr_runs.append(run)

                except Exception as e:
                    logger.error(f"Error parsing PR workflow run data: {e}")
                    continue

        return pr_runs

    async def collect_metrics(self) -> None:
        """Collect all metrics and update Prometheus metrics"""
        logger.info("Starting GitHub Actions metrics collection")

        try:
            # Get all workflows
            workflows = await self.get_workflows()

            for workflow in workflows:
                workflow_id = str(workflow["id"])
                workflow_name = workflow["name"]

                # Get workflow runs
                runs = await self.get_workflow_runs(workflow_id, per_page=50)

                # Calculate metrics for this workflow
                total_runs = len(runs)
                successful_runs = sum(1 for run in runs if run.success)
                failed_runs = sum(1 for run in runs if run.conclusion == "failure")

                success_rate = (
                    (successful_runs / total_runs * 100) if total_runs > 0 else 0
                )
                failure_rate = (failed_runs / total_runs * 100) if total_runs > 0 else 0

                # Calculate average build time
                completed_runs = [run for run in runs if run.duration > 0]
                avg_build_time = (
                    sum(run.duration for run in completed_runs) / len(completed_runs)
                    if completed_runs
                    else 0
                )

                # Update Prometheus metrics
                self.build_success_rate.labels(workflow=workflow_name).set(success_rate)
                self.build_failure_rate.labels(workflow=workflow_name).set(failure_rate)
                self.avg_build_time.labels(workflow=workflow_name).set(avg_build_time)

                # Record individual run metrics
                for run in runs:
                    self.build_duration.labels(
                        workflow=workflow_name,
                        status=run.status,
                        conclusion=run.conclusion,
                    ).observe(run.duration)

                    self.builds_total.labels(
                        workflow=workflow_name,
                        status=run.status,
                        conclusion=run.conclusion,
                    ).inc()

                    self.workflow_runs_total.labels(
                        workflow=workflow_name,
                        event_type="push",  # Simplified for now
                    ).inc()

            # Get PR-specific metrics
            pr_runs = await self.get_pr_workflow_runs(days=7)

            for run in pr_runs:
                self.pr_build_time.labels(workflow=run.name).observe(run.duration)

            logger.info("GitHub Actions metrics collection completed successfully")

        except Exception as e:
            logger.error(f"Error collecting GitHub Actions metrics: {e}")

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest(self.registry).decode("utf-8")


class GitHubActionsMetricsExporter:
    """HTTP server that exposes GitHub Actions metrics for Prometheus scraping"""

    def __init__(self, config: GitHubConfig):
        self.config = config
        self.collector = GitHubActionsMetricsCollector(config)
        self.app = web.Application()
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_get("/health", self.health_handler)
        self.app.router.add_get("/ready", self.ready_handler)

        # Collection interval (seconds)
        self.collection_interval = int(
            os.getenv("GITHUB_COLLECTION_INTERVAL", "300")
        )  # 5 minutes
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
            text='{"status": "healthy", "service": "github-actions-metrics-exporter"}',
            content_type="application/json",
        )

    async def ready_handler(self, request):
        """Handle /ready endpoint for readiness checks"""
        try:
            # Test GitHub connectivity
            async with self.collector as collector:
                # Simple API call to test connectivity
                await collector._make_request("actions/workflows")

            return web.Response(
                text='{"status": "ready", "service": "github-actions-metrics-exporter"}',
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
                logger.info("GitHub Actions metrics collected successfully")
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")

            await asyncio.sleep(self.collection_interval)

    async def start_server(self, host="0.0.0.0", port=9100):
        """Start the HTTP server"""
        logger.info(f"Starting GitHub Actions metrics exporter on {host}:{port}")

        # Start collection loop
        self.collection_task = asyncio.create_task(self.start_collection_loop())

        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(
            f"GitHub Actions metrics exporter started successfully on {host}:{port}"
        )

        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down GitHub Actions metrics exporter")
        finally:
            await runner.cleanup()
            if self.collection_task:
                self.collection_task.cancel()


def create_config_from_env() -> GitHubConfig:
    """Create GitHub configuration from environment variables"""
    return GitHubConfig(
        token=os.getenv("GITHUB_TOKEN", ""),
        org=os.getenv("GITHUB_ORG", "pake-system-org"),
        repo=os.getenv("GITHUB_REPO", "pake-system"),
        api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
    )


async def main():
    """Main entry point"""
    logger.info("Starting PAKE System GitHub Actions Metrics Exporter")

    # Create configuration
    config = create_config_from_env()

    # Validate configuration
    if not config.token:
        logger.error(
            "Missing required GitHub configuration. Please set GITHUB_TOKEN environment variable."
        )
        sys.exit(1)

    # Create and start exporter
    exporter = GitHubActionsMetricsExporter(config)

    # Get server configuration
    host = os.getenv("EXPORTER_HOST", "0.0.0.0")
    port = int(os.getenv("EXPORTER_PORT", "9100"))

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
