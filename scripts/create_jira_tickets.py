#!/usr/bin/env python3
"""Create Jira tickets for SonarQube issues.
World-Class Finish Guide - Technical debt management integration.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

import requests


@dataclass
class JiraConfig:
    """Jira configuration."""

    url: str
    username: str
    api_token: str
    project_key: str


class JiraTicketCreator:
    """Creates Jira tickets for technical debt issues."""

    def __init__(self, config: JiraConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.username, config.api_token)
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def create_technical_debt_ticket(self, issue: dict[str, Any]) -> str:
        """Create a Jira ticket for a technical debt issue."""
        ticket_data = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": f"Technical Debt: {issue.get('message', 'Unknown issue')}",
                "description": self._create_ticket_description(issue),
                "issuetype": {"name": "Technical Debt"},
                "priority": {
                    "name": self._map_priority(issue.get("severity", "MINOR"))
                },
                "labels": ["technical-debt", "sonarqube", "quality"],
                "components": [
                    {"name": self._extract_component(issue.get("component", ""))}
                ],
                "customfield_10001": self._estimate_story_points(issue),  # Story Points
            }
        }

        response = self.session.post(
            f"{self.config.url}/rest/api/3/issue", json=ticket_data
        )

        if response.status_code == 201:
            ticket_key = response.json()["key"]
            print(f"✅ Created Jira ticket: {ticket_key}")
            return ticket_key
        else:
            print(f"❌ Failed to create Jira ticket: {response.text}")
            return ""

    def _create_ticket_description(self, issue: dict[str, Any]) -> str:
        """Create ticket description from SonarQube issue."""
        description = f"""
**Technical Debt Issue**

**File:** {issue.get('component', 'Unknown')}
**Line:** {issue.get('line', 'N/A')}
**Rule:** {issue.get('rule', 'Unknown')}
**Severity:** {issue.get('severity', 'Unknown')}
**Type:** {issue.get('type', 'Unknown')}

**Description:**
{issue.get('message', 'No description available')}

**Effort:** {issue.get('effort', 'Unknown')}
**Debt:** {issue.get('debt', 'Unknown')}

**SonarQube Issue Key:** {issue.get('key', 'Unknown')}

**Acceptance Criteria:**
- [ ] Fix the identified issue
- [ ] Add appropriate tests
- [ ] Update documentation if needed
- [ ] Verify fix passes quality gates

**Definition of Done:**
- [ ] Code review completed
- [ ] Tests pass
- [ ] Quality gates pass
- [ ] SonarQube issue resolved
"""
        return description

    def _map_priority(self, severity: str) -> str:
        """Map SonarQube severity to Jira priority."""
        priority_mapping = {
            "BLOCKER": "Highest",
            "CRITICAL": "High",
            "MAJOR": "Medium",
            "MINOR": "Low",
            "INFO": "Lowest",
        }
        return priority_mapping.get(severity, "Medium")

    def _extract_component(self, component: str) -> str:
        """Extract component name from file path."""
        if not component:
            return "Unknown"

        # Extract component from path like "src/services/auth/auth_service.py"
        parts = component.split("/")
        if len(parts) >= 2:
            return parts[1]  # e.g., "services"
        return "Core"

    def _estimate_story_points(self, issue: dict[str, Any]) -> int:
        """Estimate story points based on issue complexity."""
        severity = issue.get("severity", "MINOR")
        effort = issue.get("effort", "")

        # Base points by severity
        base_points = {"BLOCKER": 8, "CRITICAL": 5, "MAJOR": 3, "MINOR": 2, "INFO": 1}

        points = base_points.get(severity, 2)

        # Adjust based on effort
        if "1d" in effort or "1 day" in effort:
            points = min(points + 2, 8)
        elif "2d" in effort or "2 days" in effort:
            points = min(points + 3, 8)
        elif "3d" in effort or "3 days" in effort:
            points = 8

        return points


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python create_jira_tickets.py <sonar-report.json>")
        sys.exit(1)

    sonar_report_path = sys.argv[1]

    # Load SonarQube report
    with open(sonar_report_path) as f:
        sonar_data = json.load(f)

    # Jira configuration (should be loaded from environment variables)
    jira_config = JiraConfig(
        url="https://your-company.atlassian.net",
        username="your-email@company.com",
        api_token="your-api-token",
        project_key="PAKE",
    )

    # Create ticket creator
    ticket_creator = JiraTicketCreator(jira_config)

    # Process issues
    issues = sonar_data.get("issues", [])
    created_tickets = []

    for issue in issues:
        if issue.get("type") in ["CODE_SMELL", "BUG", "VULNERABILITY"]:
            ticket_key = ticket_creator.create_technical_debt_ticket(issue)
            if ticket_key:
                created_tickets.append(ticket_key)

    print(f"\n✅ Created {len(created_tickets)} Jira tickets for technical debt")
    print(f"Tickets: {', '.join(created_tickets)}")


if __name__ == "__main__":
    main()
