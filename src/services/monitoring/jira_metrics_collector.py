# PAKE System - Jira Metrics Collection Service
# This service implements the Jira integration specified in the engineering guide
# for comprehensive engineering effectiveness metrics

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


@dataclass
class JiraConfig:
    """Jira configuration for metrics collection"""

    url: str
    username: str
    token: str
    project_key: str
    api_version: str = "3"


@dataclass
class SprintMetrics:
    """Sprint-level metrics from Jira"""

    sprint_id: str
    sprint_name: str
    story_points_completed: int
    story_points_committed: int
    bugs_completed: int
    features_completed: int
    velocity: float
    bug_to_feature_ratio: float


@dataclass
class ProjectMetrics:
    """Project-level metrics from Jira"""

    total_story_points: int
    completed_story_points: int
    total_bugs: int
    completed_bugs: int
    total_features: int
    completed_features: int
    average_cycle_time: float
    average_lead_time: float


class JiraMetricsCollector:
    """Collects metrics from Jira API for the Unified Quality Dashboard"""

    def __init__(self, config: JiraConfig):
        self.config = config
        self.session: aiohttp.ClientSession | None = None

        # Prometheus metrics
        self.registry = CollectorRegistry()

        # Story points metrics
        self.story_points_completed = Counter(
            "jira_story_points_completed_total",
            "Total story points completed",
            ["sprint", "project"],
            registry=self.registry,
        )

        self.story_points_velocity = Gauge(
            "jira_story_points_velocity",
            "Story points velocity per sprint",
            ["sprint", "project"],
            registry=self.registry,
        )

        # Bug and feature metrics
        self.bugs_completed = Counter(
            "jira_bugs_completed_total",
            "Total bugs completed",
            ["sprint", "project"],
            registry=self.registry,
        )

        self.features_completed = Counter(
            "jira_features_completed_total",
            "Total features completed",
            ["sprint", "project"],
            registry=self.registry,
        )

        # Bug to feature ratio
        self.bug_to_feature_ratio = Gauge(
            "jira_bug_to_feature_ratio",
            "Ratio of bugs to features",
            ["project"],
            registry=self.registry,
        )

        # Cycle time metrics
        self.cycle_time = Histogram(
            "jira_cycle_time_seconds",
            "Issue cycle time in seconds",
            ["issue_type", "project"],
            registry=self.registry,
        )

        # Lead time metrics
        self.lead_time = Histogram(
            "jira_lead_time_seconds",
            "Issue lead time in seconds",
            ["issue_type", "project"],
            registry=self.registry,
        )

        # Sprint metrics
        self.sprint_completion_rate = Gauge(
            "jira_sprint_completion_rate",
            "Sprint completion rate percentage",
            ["sprint", "project"],
            registry=self.registry,
        )

        # Team velocity metrics
        self.team_velocity = Gauge(
            "jira_team_velocity",
            "Team velocity over time",
            ["team", "project"],
            registry=self.registry,
        )

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.config.username, self.config.token),
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, endpoint: str, params: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Make authenticated request to Jira API"""
        url = f"{self.config.url}/rest/api/{self.config.api_version}/{endpoint}"

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(
                    f"Jira API request failed: {response.status} - {await response.text()}"
                )
                return {}
        except Exception as e:
            logger.error(f"Error making Jira API request: {e}")
            return {}

    async def get_active_sprints(self) -> list[dict[str, Any]]:
        """Get active sprints for the project"""
        endpoint = f"board/{self.config.project_key}/sprint"
        params = {"state": "active"}

        response = await self._make_request(endpoint, params)
        return response.get("values", [])

    async def get_sprint_issues(self, sprint_id: str) -> list[dict[str, Any]]:
        """Get all issues for a specific sprint"""
        endpoint = "search"
        params = {
            "jql": f"project = {self.config.project_key} AND sprint = {sprint_id}",
            "fields": "summary,issuetype,status,storyPoints,created,resolutiondate,assignee",
            "maxResults": 1000,
        }

        response = await self._make_request(endpoint, params)
        return response.get("issues", [])

    async def get_project_metrics(self) -> ProjectMetrics:
        """Get project-level metrics"""
        endpoint = "search"
        params = {
            "jql": f"project = {self.config.project_key}",
            "fields": "summary,issuetype,status,storyPoints,created,resolutiondate",
            "maxResults": 1000,
        }

        response = await self._make_request(endpoint, params)
        issues = response.get("issues", [])

        total_story_points = 0
        completed_story_points = 0
        total_bugs = 0
        completed_bugs = 0
        total_features = 0
        completed_features = 0
        cycle_times = []
        lead_times = []

        for issue in issues:
            issue_type = issue["fields"]["issuetype"]["name"]
            status = issue["fields"]["status"]["name"]
            story_points = issue["fields"].get("storyPoints", 0) or 0

            # Count by type
            if issue_type.lower() == "bug":
                total_bugs += 1
                if status.lower() in ["done", "closed", "resolved"]:
                    completed_bugs += 1
            elif issue_type.lower() in ["story", "feature", "epic"]:
                total_features += 1
                if status.lower() in ["done", "closed", "resolved"]:
                    completed_features += 1

            # Story points
            total_story_points += story_points
            if status.lower() in ["done", "closed", "resolved"]:
                completed_story_points += story_points

            # Calculate cycle and lead times
            created = issue["fields"].get("created")
            resolved = issue["fields"].get("resolutiondate")

            if created and resolved:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                resolved_dt = datetime.fromisoformat(resolved.replace("Z", "+00:00"))

                lead_time = (resolved_dt - created_dt).total_seconds()
                lead_times.append(lead_time)

                # Cycle time (time from in progress to done)
                # This is simplified - in practice, you'd track status transitions
                cycle_times.append(lead_time)

        return ProjectMetrics(
            total_story_points=total_story_points,
            completed_story_points=completed_story_points,
            total_bugs=total_bugs,
            completed_bugs=completed_bugs,
            total_features=total_features,
            completed_features=completed_features,
            average_cycle_time=sum(cycle_times) / len(cycle_times)
            if cycle_times
            else 0,
            average_lead_time=sum(lead_times) / len(lead_times) if lead_times else 0,
        )

    async def get_sprint_metrics(self, sprint_id: str) -> SprintMetrics:
        """Get sprint-level metrics"""
        issues = await self.get_sprint_issues(sprint_id)

        story_points_completed = 0
        story_points_committed = 0
        bugs_completed = 0
        features_completed = 0

        for issue in issues:
            issue_type = issue["fields"]["issuetype"]["name"]
            status = issue["fields"]["status"]["name"]
            story_points = issue["fields"].get("storyPoints", 0) or 0

            story_points_committed += story_points

            if status.lower() in ["done", "closed", "resolved"]:
                story_points_completed += story_points

                if issue_type.lower() == "bug":
                    bugs_completed += 1
                elif issue_type.lower() in ["story", "feature", "epic"]:
                    features_completed += 1

        velocity = story_points_completed
        bug_to_feature_ratio = (
            bugs_completed / features_completed if features_completed > 0 else 0
        )

        return SprintMetrics(
            sprint_id=sprint_id,
            sprint_name=f"Sprint {sprint_id}",
            story_points_completed=story_points_completed,
            story_points_committed=story_points_committed,
            bugs_completed=bugs_completed,
            features_completed=features_completed,
            velocity=velocity,
            bug_to_feature_ratio=bug_to_feature_ratio,
        )

    async def collect_metrics(self) -> None:
        """Collect all metrics and update Prometheus metrics"""
        logger.info("Starting Jira metrics collection")

        try:
            # Get project metrics
            project_metrics = await self.get_project_metrics()

            # Update project-level metrics
            self.bug_to_feature_ratio.labels(project=self.config.project_key).set(
                project_metrics.completed_bugs / project_metrics.completed_features
                if project_metrics.completed_features > 0
                else 0
            )

            # Get active sprints
            active_sprints = await self.get_active_sprints()

            for sprint in active_sprints:
                sprint_id = sprint["id"]
                sprint_name = sprint["name"]

                # Get sprint metrics
                sprint_metrics = await self.get_sprint_metrics(sprint_id)

                # Update Prometheus metrics
                self.story_points_completed.labels(
                    sprint=sprint_name, project=self.config.project_key
                ).inc(sprint_metrics.story_points_completed)

                self.story_points_velocity.labels(
                    sprint=sprint_name, project=self.config.project_key
                ).set(sprint_metrics.velocity)

                self.bugs_completed.labels(
                    sprint=sprint_name, project=self.config.project_key
                ).inc(sprint_metrics.bugs_completed)

                self.features_completed.labels(
                    sprint=sprint_name, project=self.config.project_key
                ).inc(sprint_metrics.features_completed)

                completion_rate = (
                    sprint_metrics.story_points_completed
                    / sprint_metrics.story_points_committed
                    * 100
                    if sprint_metrics.story_points_committed > 0
                    else 0
                )

                self.sprint_completion_rate.labels(
                    sprint=sprint_name, project=self.config.project_key
                ).set(completion_rate)

            logger.info("Jira metrics collection completed successfully")

        except Exception as e:
            logger.error(f"Error collecting Jira metrics: {e}")

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        from prometheus_client import generate_latest

        return generate_latest(self.registry).decode("utf-8")


# Example usage and configuration
async def main():
    """Example usage of Jira metrics collector"""
    # Configuration
    config = JiraConfig(
        url="https://your-org.atlassian.net",
        username="your-email@company.com",
        token="your-api-token",
        project_key="PAKE",
    )

    # Collect metrics
    async with JiraMetricsCollector(config) as collector:
        await collector.collect_metrics()

        # Print metrics
        print(collector.get_metrics())


if __name__ == "__main__":
    asyncio.run(main())
