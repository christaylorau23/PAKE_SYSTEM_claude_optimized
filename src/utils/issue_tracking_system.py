#!/usr/bin/env python3
"""PAKE System - Issue Tracking System for Flaky Tests
Enterprise-grade issue tracking integration for flaky test management.

This module provides integration with issue tracking systems to ensure
mandatory documentation of flaky tests as per enterprise policy.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class IssueTrackerType(Enum):
    """Supported issue tracker types."""

    GITHUB = "github"
    JIRA = "jira"
    GITLAB = "gitlab"
    AZURE_DEVOPS = "azure_devops"
    CUSTOM_API = "custom_api"


class IssuePriority(Enum):
    """Issue priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(Enum):
    """Issue status values."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DUPLICATE = "duplicate"
    WONT_FIX = "wont_fix"


@dataclass(frozen=True)
class IssueTemplate:
    """Template for creating flaky test issues."""

    title_template: str = "Flaky Test: {test_name}"
    description_template: str = """
## Flaky Test Report

**Test Name:** {test_name}
**Test File:** {test_file}
**Failure Mode:** {failure_mode}
**Failure Rate:** {failure_rate:.1%}
**First Detected:** {first_detected}
**Total Failures:** {total_failures}
**Total Runs:** {total_runs}

### Error Details
```
{error_message}
```

### Recommended Actions
1. **Investigate Root Cause:** {investigation_steps}
2. **Apply Fix:** {fix_recommendations}
3. **Add Mocking:** {mocking_recommendations}
4. **Update Tests:** {test_updates}

### Policy Compliance
- [ ] Issue ticket created (mandatory per enterprise policy)
- [ ] Root cause analysis completed
- [ ] Fix implemented or test refactored
- [ ] Mocking added for external dependencies
- [ ] Resolution documented

### Related Files
- Test file: `{test_file}`
- Related services: {related_services}

---
*This issue was automatically created by the PAKE System Flaky Test Management System*
"""
    labels: list[str] = field(
        default_factory=lambda: ["flaky-test", "test-stability", "priority-medium"]
    )
    priority: IssuePriority = IssuePriority.MEDIUM
    assignee: str | None = None
    milestone: str | None = None


@dataclass
class IssueTrackerConfig:
    """Configuration for issue tracker integration."""

    tracker_type: IssueTrackerType
    base_url: str
    api_token: str
    project_id: str | None = None
    repository: str | None = None
    default_assignee: str | None = None
    default_labels: list[str] = field(default_factory=list)
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class IssueTrackerClient:
    """Base class for issue tracker clients."""

    def __init__(self, config: IssueTrackerConfig | None = None) -> None:
        self.config = config or IssueTrackerConfig()
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            headers=self._get_headers(),
        )
        return self

    async def __aexit__(self) -> None:
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "PAKE-System-FlakyTestManager/1.0",
        }

    async def create_issue(
        self, template: IssueTemplate, test_data: dict[str, Any]
    ) -> str:
        """Create an issue using the template and test data."""
        msg = "Subclasses must implement create_issue"
        raise NotImplementedError(msg)

    async def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update an existing issue."""
        msg = "Subclasses must implement update_issue"
        raise NotImplementedError(msg)

    async def close_issue(self, issue_id: str, resolution_notes: str = None) -> bool:
        """Close an issue with optional resolution notes."""
        msg = "Subclasses must implement close_issue"
        raise NotImplementedError(msg)

    async def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue details."""
        msg = "Subclasses must implement get_issue"
        raise NotImplementedError(msg)


class GitHubIssueTracker(IssueTrackerClient):
    """GitHub Issues integration."""

    def __init__(self, config: IssueTrackerConfig | None = None) -> None:
        super().__init__(config)
        if not config.repository:
            msg = "GitHub tracker requires repository configuration"
            raise ValueError(msg)

    def _get_headers(self) -> dict[str, str]:
        """Get GitHub-specific headers."""
        headers = super()._get_headers()
        headers["Authorization"] = f"token {self.config.api_token}"
        return headers

    async def create_issue(
        self, template: IssueTemplate, test_data: dict[str, Any]
    ) -> str:
        """Create a GitHub issue."""
        url = f"https://api.github.com/repos/{self.config.repository}/issues"

        # Format template
        title = template.title_template.format(**test_data)
        description = template.description_template.format(**test_data)

        payload = {
            "title": title,
            "body": description,
            "labels": template.labels + self.config.default_labels,
            "assignee": template.assignee or self.config.default_assignee,
        }

        if template.milestone:
            payload["milestone"] = template.milestone

        if not self.session:
            msg = "Session not initialized. Use async context manager."
            raise RuntimeError(msg)
        async with self.session.post(url, json=payload) as response:
            if response.status == 201:
                data = await response.json()
                issue_number = data["number"]
                issue_url = data["html_url"]
                logger.info("Created GitHub issue #%s: %s", issue_number, issue_url)
                return f"#{issue_number}"
            error_text = await response.text()
            logger.error(
                "Failed to create GitHub issue: %s - %s", response.status, error_text
            )
            msg = f"GitHub API error: {response.status}"
            raise Exception(msg)

    async def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update a GitHub issue."""
        # Remove # prefix if present
        issue_number = issue_id.lstrip("#")
        url = f"https://api.github.com/repos/{self.config.repository}/issues/{issue_number}"

        if not self.session:
            msg = "Session not initialized. Use async context manager."
            raise RuntimeError(msg)
        async with self.session.patch(url, json=updates) as response:
            if response.status == 200:
                logger.info("Updated GitHub issue #%s", issue_number)
                return True
            error_text = await response.text()
            logger.error(
                "Failed to update GitHub issue: %s - %s", response.status, error_text
            )
            return False

    async def close_issue(self, issue_id: str, resolution_notes: str = None) -> bool:
        """Close a GitHub issue."""
        issue_number = issue_id.lstrip("#")
        url = f"https://api.github.com/repos/{self.config.repository}/issues/{issue_number}"

        updates = {"state": "closed"}
        if resolution_notes:
            # Get current issue body and append resolution notes
            current_issue = await self.get_issue(issue_id)
            if current_issue:
                current_body = current_issue.get("body", "")
                updates["body"] = f"{current_body}\n\n## Resolution\n{resolution_notes}"

        return await self.update_issue(issue_id, updates)

    async def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get GitHub issue details."""
        issue_number = issue_id.lstrip("#")
        url = f"https://api.github.com/repos/{self.config.repository}/issues/{issue_number}"

        if not self.session:
            msg = "Session not initialized. Use async context manager."
            raise RuntimeError(msg)
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            logger.error("Failed to get GitHub issue: %s", response.status)
            return None


class JiraIssueTracker(IssueTrackerClient):
    """Jira integration."""

    def __init__(self, config: IssueTrackerConfig | None = None) -> None:
        super().__init__(config)
        if not config.project_id:
            msg = "Jira tracker requires project_id configuration"
            raise ValueError(msg)

    def _get_headers(self) -> dict[str, str]:
        """Get Jira-specific headers."""
        headers = super()._get_headers()
        headers["Authorization"] = f"Basic {self.config.api_token}"  # Base64 encoded
        return headers

    async def create_issue(
        self, template: IssueTemplate, test_data: dict[str, Any]
    ) -> str:
        """Create a Jira issue."""
        url = f"{self.config.base_url}/rest/api/2/issue"

        # Format template
        title = template.title_template.format(**test_data)
        description = template.description_template.format(**test_data)

        payload = {
            "fields": {
                "project": {"key": self.config.project_id},
                "summary": title,
                "description": description,
                "issuetype": {"name": "Bug"},
                "priority": {"name": template.priority.value.title()},
                "labels": template.labels + self.config.default_labels,
            }
        }

        if template.assignee or self.config.default_assignee:
            payload["fields"]["assignee"] = {
                "name": template.assignee or self.config.default_assignee
            }

        if not self.session:
            msg = "Session not initialized. Use async context manager."
            raise RuntimeError(msg)
        async with self.session.post(url, json=payload) as response:
            if response.status == 201:
                data = await response.json()
                issue_key = data["key"]
                issue_url = f"{self.config.base_url}/browse/{issue_key}"
                logger.info("Created Jira issue %s: %s", issue_key, issue_url)
                return issue_key
            error_text = await response.text()
            logger.error(
                "Failed to create Jira issue: %s - %s", response.status, error_text
            )
            msg = f"Jira API error: {response.status}"
            raise Exception(msg)

    async def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update a Jira issue."""
        url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}"

        # Convert updates to Jira format
        jira_updates = {"fields": {}}
        for key, value in updates.items():
            if key == "labels":
                jira_updates["fields"]["labels"] = value
            elif key == "assignee":
                jira_updates["fields"]["assignee"] = {"name": value}
            elif key == "priority":
                jira_updates["fields"]["priority"] = {"name": value}
            else:
                jira_updates["fields"][key] = value

        if not self.session:
            msg = "Session not initialized. Use async context manager."
            raise RuntimeError(msg)
        async with self.session.put(url, json=jira_updates) as response:
            if response.status == 204:
                logger.info("Updated Jira issue %s", issue_id)
                return True
            error_text = await response.text()
            logger.error(
                "Failed to update Jira issue: %s - %s", response.status, error_text
            )
            return False

    async def close_issue(self, issue_id: str, resolution_notes: str = None) -> bool:
        """Close a Jira issue."""
        # First transition to resolved
        transition_url = (
            f"{self.config.base_url}/rest/api/2/issue/{issue_id}/transitions"
        )

        # Get available transitions
        async with self.session.get(transition_url) as response:
            if response.status == 200:
                transitions_data = await response.json()
                resolved_transition = None
                for transition in transitions_data.get("transitions", []):
                    if transition["name"].lower() in [
                        "resolve",
                        "resolved",
                        "close",
                        "closed",
                    ]:
                        resolved_transition = transition
                        break

                if resolved_transition:
                    transition_payload = {
                        "transition": {"id": resolved_transition["id"]}
                    }

                    if resolution_notes:
                        transition_payload["update"] = {
                            "comment": [
                                {"add": {"body": f"Resolution: {resolution_notes}"}}
                            ]
                        }

                    async with self.session.post(
                        transition_url, json=transition_payload
                    ) as transition_response:
                        if transition_response.status == 204:
                            logger.info("Closed Jira issue %s", issue_id)
                            return True
                        logger.error(
                            "Failed to close Jira issue: %s", transition_response.status
                        )
                        return False
                else:
                    logger.error(
                        "No suitable transition found for Jira issue %s", issue_id
                    )
                    return False
            else:
                logger.error(
                    "Failed to get transitions for Jira issue: %s", response.status
                )
                return False

    async def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get Jira issue details."""
        url = f"{self.config.base_url}/rest/api/2/issue/{issue_id}"

        if not self.session:
            msg = "Session not initialized. Use async context manager."
            raise RuntimeError(msg)
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            logger.error("Failed to get Jira issue: %s", response.status)
            return None


class IssueTrackerFactory:
    """Factory for creating issue tracker clients."""

    @staticmethod
    def create_tracker(config: IssueTrackerConfig) -> IssueTrackerClient:
        """Create appropriate issue tracker client."""
        if config.tracker_type == IssueTrackerType.GITHUB:
            return GitHubIssueTracker(config)
        if config.tracker_type == IssueTrackerType.JIRA:
            return JiraIssueTracker(config)
        msg = f"Unsupported tracker type: {config.tracker_type}"
        raise ValueError(msg)


class FlakyTestIssueManager:
    """Manager for creating and tracking flaky test issues."""

    def __init__(self, config: IssueTrackerConfig | None = None, template: IssueTemplate | None = None) -> None:
        self.config = config or IssueTrackerConfig()
        self.template = template or IssueTemplate()
        self.tracker_factory = IssueTrackerFactory()
        self.created_issues: dict[str, str] = {}  # test_id -> issue_id mapping

    async def create_flaky_test_issue(self, test_data: dict[str, Any]) -> str:
        """Create an issue for a flaky test."""
        test_id = test_data.get("test_id")
        if not test_id:
            msg = "test_id is required in test_data"
            raise ValueError(msg)

        # Check if issue already exists
        if test_id in self.created_issues:
            logger.info(
                "Issue already exists for test %s: %s",
                test_id,
                self.created_issues[test_id],
            )
            return self.created_issues[test_id]

        # Enhance test data with additional context
        enhanced_data = self._enhance_test_data(test_data)

        # Create tracker client
        async with self.tracker_factory.create_tracker(self.config) as tracker:
            try:
                issue_id = await tracker.create_issue(self.template, enhanced_data)
                self.created_issues[test_id] = issue_id
                logger.info("Created issue %s for flaky test %s", issue_id, test_id)
                return issue_id
            except (ValueError, RuntimeError) as e:
                logger.error("Failed to create issue for test %s: %s", test_id, e)
                raise

    async def update_flaky_test_issue(
        self, test_id: str, updates: dict[str, Any]
    ) -> bool:
        """Update an existing flaky test issue."""
        if test_id not in self.created_issues:
            logger.warning("No issue found for test %s", test_id)
            return False

        issue_id = self.created_issues[test_id]

        async with self.tracker_factory.create_tracker(self.config) as tracker:
            try:
                success = await tracker.update_issue(issue_id, updates)
                if success:
                    logger.info("Updated issue %s for test %s", issue_id, test_id)
                return success
            except (ValueError, RuntimeError) as e:
                logger.error("Failed to update issue for test %s: %s", test_id, e)
                return False

    async def resolve_flaky_test_issue(
        self, test_id: str, resolution_notes: str
    ) -> bool:
        """Resolve a flaky test issue."""
        if test_id not in self.created_issues:
            logger.warning("No issue found for test %s", test_id)
            return False

        issue_id = self.created_issues[test_id]

        async with self.tracker_factory.create_tracker(self.config) as tracker:
            try:
                success = await tracker.close_issue(issue_id, resolution_notes)
                if success:
                    logger.info("Resolved issue %s for test %s", issue_id, test_id)
                return success
            except (ValueError, RuntimeError) as e:
                logger.error("Failed to resolve issue for test %s: %s", test_id, e)
                return False

    def _enhance_test_data(self, test_data: dict[str, Any]) -> dict[str, Any]:
        """Enhance test data with additional context and recommendations."""
        enhanced = test_data.copy()

        # Add investigation steps based on failure mode
        failure_mode = test_data.get("failure_mode", "unknown")
        enhanced["investigation_steps"] = self._get_investigation_steps(failure_mode)
        enhanced["fix_recommendations"] = self._get_fix_recommendations(failure_mode)
        enhanced["mocking_recommendations"] = self._get_mocking_recommendations(
            failure_mode
        )
        enhanced["test_updates"] = self._get_test_update_recommendations(failure_mode)

        # Add related services based on test file
        test_file = test_data.get("test_file", "")
        enhanced["related_services"] = self._get_related_services(test_file)

        # Format timestamps
        if "first_detected" in enhanced:
            enhanced["first_detected"] = enhanced["first_detected"].strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )

        return enhanced

    def _get_investigation_steps(self, failure_mode: str) -> str:
        """Get investigation steps based on failure mode."""
        steps_map = {
            "race_condition": "1. Review shared state access patterns\n2. Check for missing synchronization primitives\n3. Analyze concurrent execution paths\n4. Use race condition detection tools",
            "timing_dependent": "1. Review test timing assumptions\n2. Check for hardcoded delays\n3. Analyze system performance under load\n4. Consider using robust polling mechanisms",
            "external_api": "1. Check API rate limits and quotas\n2. Verify network connectivity\n3. Review API response times\n4. Consider implementing retry logic with exponential backoff",
            "network_timeout": "1. Check network connectivity\n2. Review timeout configurations\n3. Analyze network latency\n4. Consider increasing timeout values or implementing retry logic",
            "database_connection": "1. Check database connectivity\n2. Review connection pool settings\n3. Analyze database performance\n4. Consider connection retry logic",
            "cache_inconsistency": "1. Review cache invalidation logic\n2. Check cache synchronization\n3. Analyze cache hit/miss patterns\n4. Consider cache warming strategies",
        }
        return steps_map.get(
            failure_mode,
            "1. Analyze test failure patterns\n2. Review test implementation\n3. Check for environmental dependencies\n4. Consider test refactoring",
        )

    def _get_fix_recommendations(self, failure_mode: str) -> str:
        """Get fix recommendations based on failure mode."""
        fixes_map = {
            "race_condition": "Implement proper synchronization primitives (asyncio.Lock, threading.Lock, AsyncSafeDict)",
            "timing_dependent": "Replace fixed delays with robust polling mechanisms or event-driven approaches",
            "external_api": "Add proper mocking for external API calls in tests",
            "network_timeout": "Implement retry logic with exponential backoff and circuit breaker patterns",
            "database_connection": "Add connection retry logic and proper connection pool management",
            "cache_inconsistency": "Implement proper cache invalidation and synchronization mechanisms",
        }
        return fixes_map.get(
            failure_mode,
            "Review test implementation and consider refactoring for better reliability",
        )

    def _get_mocking_recommendations(self, failure_mode: str) -> str:
        """Get mocking recommendations based on failure mode."""
        mocking_map = {
            "external_api": "Mock external API responses using unittest.mock or pytest-mock",
            "network_timeout": "Mock network calls to avoid external dependencies",
            "database_connection": "Use in-memory database or database mocks for testing",
            "cache_inconsistency": "Mock cache operations or use test-specific cache instances",
        }
        return mocking_map.get(
            failure_mode,
            "Consider mocking external dependencies to improve test reliability",
        )

    def _get_test_update_recommendations(self, failure_mode: str) -> str:
        """Get test update recommendations based on failure mode."""
        updates_map = {
            "race_condition": "Add synchronization primitives and test concurrent scenarios",
            "timing_dependent": "Replace timing-dependent assertions with state-based checks",
            "external_api": "Add proper test data setup and teardown for external dependencies",
            "network_timeout": "Add timeout handling and retry logic to tests",
            "database_connection": "Add database setup/teardown and connection testing",
            "cache_inconsistency": "Add cache state verification and invalidation testing",
        }
        return updates_map.get(
            failure_mode,
            "Review test structure and add proper setup/teardown procedures",
        )

    def _get_related_services(self, test_file: str) -> str:
        """Get related services based on test file path."""
        if "ingestion" in test_file:
            return (
                "Ingestion services, Firecrawl service, ArXiv service, PubMed service"
            )
        if "caching" in test_file:
            return "Multi-tier cache service, Redis cache service"
        if "auth" in test_file:
            return "Authentication service, JWT service, User service"
        if "analytics" in test_file:
            return "Analytics engine, ML services, Intelligence services"
        if "cognitive" in test_file:
            return "Cognitive analysis engine, Self-critique analyzer"
        return "General services"


# Global issue manager instance
_issue_manager: FlakyTestIssueManager | None = None


def get_issue_manager() -> FlakyTestIssueManager | None:
    """Get the global issue manager."""
    return _issue_manager


def configure_issue_tracker(config: IssueTrackerConfig, template: IssueTemplate | None = None) -> None:
    """Configure the global issue tracker."""
    global _issue_manager
    _issue_manager = FlakyTestIssueManager(config, template)
    logger.info("Configured issue tracker: %s", config.tracker_type.value)


# Convenience functions for integration with flaky test management
async def create_flaky_test_issue(test_data: dict[str, Any]) -> str | None:
    """Create an issue for a flaky test using the global manager."""
    manager = get_issue_manager()
    if not manager:
        logger.warning("No issue tracker configured")
        return None

    try:
        return await manager.create_flaky_test_issue(test_data)
    except (ValueError, RuntimeError) as e:
        logger.error("Failed to create flaky test issue: %s", e)
        return None


async def update_flaky_test_issue(test_id: str, updates: dict[str, Any]) -> bool:
    """Update a flaky test issue using the global manager."""
    manager = get_issue_manager()
    if not manager:
        logger.warning("No issue tracker configured")
        return False

    return await manager.update_flaky_test_issue(test_id, updates)


async def resolve_flaky_test_issue(test_id: str, resolution_notes: str) -> bool:
    """Resolve a flaky test issue using the global manager."""
    manager = get_issue_manager()
    if not manager:
        logger.warning("No issue tracker configured")
        return False

    return await manager.resolve_flaky_test_issue(test_id, resolution_notes)


if __name__ == "__main__":
    # Example usage
    async def example_usage(self) -> None:
        print("Issue Tracking System Example")

        # Configure GitHub tracker
        config = IssueTrackerConfig(
            tracker_type=IssueTrackerType.GITHUB,
            base_url="https://api.github.com",
            api_token="your_github_token",
            repository="your_org/your_repo",
        )

        template = IssueTemplate(
            labels=["flaky-test", "test-stability"], priority=IssuePriority.HIGH
        )

        configure_issue_tracker(config, template)

        # Create issue for flaky test
        test_data = {
            "test_id": "test_example_race_condition",
            "test_name": "test_example_race_condition",
            "test_file": "tests/unit/test_example.py",
            "failure_mode": "race_condition",
            "failure_rate": 0.3,
            "first_detected": datetime.now(UTC),
            "total_failures": 3,
            "total_runs": 10,
            "error_message": "Race condition detected in shared counter",
        }

        issue_id = await create_flaky_test_issue(test_data)
        print(f"Created issue: {issue_id}")

        # Update issue
        await update_flaky_test_issue(
            "test_example_race_condition",
            {"labels": ["flaky-test", "test-stability", "in-progress"]},
        )

        # Resolve issue
        await resolve_flaky_test_issue(
            "test_example_race_condition",
            "Fixed race condition by implementing AsyncSafeCounter",
        )

        print("Issue tracking system example completed!")

    # Run example
    asyncio.run(example_usage())