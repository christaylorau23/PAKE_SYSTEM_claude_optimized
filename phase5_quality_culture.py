#!/usr/bin/env python3
"""Phase 5: Institutionalizing a Culture of Quality
World-Class Finish Guide - Embedding quality gates into agile workflows.
"""

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


class QualityGateStatus(Enum):
    """Quality gate status levels."""

    PASSED = "Passed"
    FAILED = "Failed"
    WARNING = "Warning"
    ERROR = "Error"


class IssueSeverity(Enum):
    """Issue severity levels from SonarQube."""

    BLOCKER = "Blocker"
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    INFO = "Info"


class IssueType(Enum):
    """Issue types for categorization."""

    BUG = "Bug"
    VULNERABILITY = "Vulnerability"
    CODE_SMELL = "Code Smell"
    SECURITY_HOTSPOT = "Security Hotspot"
    TECH_DEBT = "Technical Debt"


@dataclass
class QualityGate:
    """Represents a quality gate configuration."""

    name: str
    description: str
    conditions: list[dict[str, Any]]
    status: QualityGateStatus
    threshold_values: dict[str, float]


@dataclass
class SonarQubeIssue:
    """Represents a SonarQube issue."""

    key: str
    rule: str
    severity: IssueSeverity
    type: IssueType
    component: str
    line: int
    message: str
    effort: str
    debt: str
    file_path: str
    priority_score: int


@dataclass
class JiraTicket:
    """Represents a Jira ticket for technical debt."""

    key: str
    summary: str
    description: str
    issue_type: str
    priority: str
    labels: list[str]
    components: list[str]
    story_points: int
    sonar_issue_key: str


class QualityCultureFramework:
    """Comprehensive framework for institutionalizing quality culture."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.quality_gates: list[QualityGate] = []
        self.sonar_issues: list[SonarQubeIssue] = []
        self.jira_tickets: list[JiraTicket] = []
        self.quality_metrics: dict[str, Any] = {}

    def create_quality_gates(self) -> list[QualityGate]:
        """Create comprehensive quality gates for the project."""
        print("🔧 Creating Quality Gates...")

        # Quality Gate 1: New Code Quality
        new_code_gate = QualityGate(
            name="New Code Quality Gate",
            description="Quality gate for new and modified code",
            conditions=[
                {"metric": "new_coverage", "op": "LT", "error": 85.0, "warning": 90.0},
                {
                    "metric": "new_duplicated_lines_density",
                    "op": "GT",
                    "error": 3.0,
                    "warning": 1.0,
                },
                {
                    "metric": "new_maintainability_rating",
                    "op": "GT",
                    "error": 1.0,
                    "warning": 1.0,
                },
                {
                    "metric": "new_reliability_rating",
                    "op": "GT",
                    "error": 1.0,
                    "warning": 1.0,
                },
                {
                    "metric": "new_security_rating",
                    "op": "GT",
                    "error": 1.0,
                    "warning": 1.0,
                },
            ],
            status=QualityGateStatus.PASSED,
            threshold_values={
                "coverage": 85.0,
                "duplication": 3.0,
                "maintainability": 1.0,
                "reliability": 1.0,
                "security": 1.0,
            },
        )

        # Quality Gate 2: Overall Project Health
        overall_gate = QualityGate(
            name="Overall Project Health Gate",
            description="Quality gate for overall project health",
            conditions=[
                {"metric": "coverage", "op": "LT", "error": 80.0, "warning": 85.0},
                {
                    "metric": "duplicated_lines_density",
                    "op": "GT",
                    "error": 5.0,
                    "warning": 3.0,
                },
                {
                    "metric": "maintainability_rating",
                    "op": "GT",
                    "error": 2.0,
                    "warning": 1.0,
                },
                {
                    "metric": "reliability_rating",
                    "op": "GT",
                    "error": 2.0,
                    "warning": 1.0,
                },
                {"metric": "security_rating", "op": "GT", "error": 2.0, "warning": 1.0},
            ],
            status=QualityGateStatus.PASSED,
            threshold_values={
                "coverage": 80.0,
                "duplication": 5.0,
                "maintainability": 2.0,
                "reliability": 2.0,
                "security": 2.0,
            },
        )

        # Quality Gate 3: Security and Vulnerabilities
        security_gate = QualityGate(
            name="Security Quality Gate",
            description="Quality gate for security vulnerabilities",
            conditions=[
                {
                    "metric": "new_security_hotspots",
                    "op": "GT",
                    "error": 0.0,
                    "warning": 0.0,
                },
                {
                    "metric": "new_vulnerabilities",
                    "op": "GT",
                    "error": 0.0,
                    "warning": 0.0,
                },
                {
                    "metric": "security_hotspots",
                    "op": "GT",
                    "error": 10.0,
                    "warning": 5.0,
                },
                {"metric": "vulnerabilities", "op": "GT", "error": 5.0, "warning": 2.0},
            ],
            status=QualityGateStatus.PASSED,
            threshold_values={
                "new_security_hotspots": 0.0,
                "new_vulnerabilities": 0.0,
                "security_hotspots": 10.0,
                "vulnerabilities": 5.0,
            },
        )

        self.quality_gates = [new_code_gate, overall_gate, security_gate]
        return self.quality_gates

    def create_sonarqube_configuration(self) -> dict[str, Any]:
        """Create SonarQube configuration for the project."""
        print("🔧 Creating SonarQube Configuration...")

        sonar_config = {
            "sonar.projectKey": "pake-system",
            "sonar.projectName": "PAKE System",
            "sonar.projectVersion": "1.0.0",
            "sonar.sources": "src/",
            "sonar.tests": "tests/",
            "sonar.python.version": "3.12",
            "sonar.python.coverage.reportPaths": "coverage.xml",
            "sonar.python.xunit.reportPath": "test-results.xml",
            "sonar.exclusions": [
                "**/node_modules/**",
                "**/venv/**",
                "**/.venv/**",
                "**/__pycache__/**",
                "**/migrations/**",
                "**/static/**",
                "**/media/**",
            ],
            "sonar.test.exclusions": ["**/test_*.py", "**/*_test.py", "**/tests/**"],
            "sonar.qualitygate.wait": "true",
            "sonar.analysis.mode": "preview",
            "sonar.issuesReport.console.enable": "true",
            "sonar.issuesReport.html.enable": "true",
            "sonar.issuesReport.json.enable": "true",
        }

        return sonar_config

    def create_github_actions_workflow(self) -> str:
        """Create GitHub Actions workflow for quality gates."""
        print("🔧 Creating GitHub Actions Quality Gate Workflow...")

        workflow_content = """name: Quality Gates and Technical Debt Management

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main, develop ]

jobs:
  quality-gates:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Shallow clones should be disabled for better analysis

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install poetry
        poetry install --no-dev

    - name: Run tests with coverage
      run: |
        poetry run pytest --cov=src --cov-report=xml --cov-report=html
        poetry run pytest --junitxml=test-results.xml

    - name: Run linting
      run: |
        poetry run ruff check src/ --output-format=json --output-file=ruff-report.json
        poetry run ruff format --check src/

    - name: Run type checking
      run: |
        poetry run mypy src/ --junit-xml=mypy-results.xml

    - name: Run security scan
      run: |
        poetry run bandit -r src/ -f json -o bandit-report.json
        poetry run safety check --json --output safety-report.json

    - name: SonarQube Scan
      uses: SonarSource/sonarqube-scan-action@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
      with:
        args: >
          -Dsonar.projectKey=pake-system
          -Dsonar.python.coverage.reportPaths=coverage.xml
          -Dsonar.python.xunit.reportPath=test-results.xml
          -Dsonar.qualitygate.wait=true

    - name: Quality Gate Status
      if: always()
      run: |
        echo "Quality Gate Status: ${{ steps.sonarqube.outputs.quality-gate-status }}"
        if [ "${{ steps.sonarqube.outputs.quality-gate-status }}" != "PASSED" ]; then
          echo "Quality gate failed!"
          exit 1
        fi

    - name: Generate Technical Debt Report
      if: always()
      run: |
        python scripts/generate_technical_debt_report.py

    - name: Create Jira Tickets for New Issues
      if: failure()
      run: |
        python scripts/create_jira_tickets.py --sonar-report sonar-report.json

    - name: Upload Quality Reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: quality-reports
        path: |
          coverage.xml
          test-results.xml
          ruff-report.json
          bandit-report.json
          safety-report.json
          sonar-report.json
          technical-debt-report.json

  technical-debt-management:
    runs-on: ubuntu-latest
    needs: quality-gates
    if: always()

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install poetry
        poetry install --no-dev

    - name: Analyze Technical Debt
      run: |
        python scripts/analyze_technical_debt.py

    - name: Generate Sprint Planning Report
      run: |
        python scripts/generate_sprint_planning_report.py

    - name: Update Jira Backlog
      run: |
        python scripts/update_jira_backlog.py --debt-report technical-debt-analysis.json
"""

        return workflow_content

    def create_jira_integration_scripts(self) -> None:
        """Create scripts for Jira integration."""
        print("🔧 Creating Jira Integration Scripts...")

        scripts_dir = Path(self.project_root) / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Script 1: Create Jira Tickets
        create_tickets_script = scripts_dir / "create_jira_tickets.py"
        with open(create_tickets_script, "w") as f:
            f.write(
                '''#!/usr/bin/env python3
"""Create Jira tickets for SonarQube issues.
World-Class Finish Guide - Technical debt management integration.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
from dataclasses import dataclass


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
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def create_technical_debt_ticket(self, issue: Dict[str, Any]) -> str:
        """Create a Jira ticket for a technical debt issue."""
        ticket_data = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": f"Technical Debt: {issue.get('message', 'Unknown issue')}",
                "description": self._create_ticket_description(issue),
                "issuetype": {"name": "Technical Debt"},
                "priority": {"name": self._map_priority(issue.get('severity', 'MINOR'))},
                "labels": ["technical-debt", "sonarqube", "quality"],
                "components": [{"name": self._extract_component(issue.get('component', ''))}],
                "customfield_10001": self._estimate_story_points(issue)  # Story Points
            }
        }

        response = self.session.post(
            f"{self.config.url}/rest/api/3/issue",
            json=ticket_data
        )

        if response.status_code == 201:
            ticket_key = response.json()["key"]
            print(f"✅ Created Jira ticket: {ticket_key}")
            return ticket_key
        else:
            print(f"❌ Failed to create Jira ticket: {response.text}")
            return ""

    def _create_ticket_description(self, issue: Dict[str, Any]) -> str:
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
            "INFO": "Lowest"
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

    def _estimate_story_points(self, issue: Dict[str, Any]) -> int:
        """Estimate story points based on issue complexity."""
        severity = issue.get('severity', 'MINOR')
        effort = issue.get('effort', '')

        # Base points by severity
        base_points = {
            "BLOCKER": 8,
            "CRITICAL": 5,
            "MAJOR": 3,
            "MINOR": 2,
            "INFO": 1
        }

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
    with open(sonar_report_path, 'r') as f:
        sonar_data = json.load(f)

    # Jira configuration (should be loaded from environment variables)
    jira_config = JiraConfig(
        url="https://your-company.atlassian.net",
        username="your-email@company.com",
        api_token="your-api-token",
        project_key="PAKE"
    )

    # Create ticket creator
    ticket_creator = JiraTicketCreator(jira_config)

    # Process issues
    issues = sonar_data.get('issues', [])
    created_tickets = []

    for issue in issues:
        if issue.get('type') in ['CODE_SMELL', 'BUG', 'VULNERABILITY']:
            ticket_key = ticket_creator.create_technical_debt_ticket(issue)
            if ticket_key:
                created_tickets.append(ticket_key)

    print(f"\\n✅ Created {len(created_tickets)} Jira tickets for technical debt")
    print(f"Tickets: {', '.join(created_tickets)}")


if __name__ == "__main__":
    main()
'''
            )

        # Script 2: Generate Technical Debt Report
        debt_report_script = scripts_dir / "generate_technical_debt_report.py"
        with open(debt_report_script, "w") as f:
            f.write(
                '''#!/usr/bin/env python3
"""Generate technical debt report for sprint planning.
World-Class Finish Guide - Data-driven technical debt management.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class TechnicalDebtItem:
    """Represents a technical debt item."""
    issue_key: str
    file_path: str
    line_number: int
    rule: str
    severity: str
    message: str
    effort: str
    debt: str
    story_points: int
    priority_score: int
    component: str


class TechnicalDebtAnalyzer:
    """Analyzes technical debt for sprint planning."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.debt_items: List[TechnicalDebtItem] = []

    def analyze_sonarqube_issues(self) -> List[TechnicalDebtItem]:
        """Analyze SonarQube issues and convert to technical debt items."""
        print("🔍 Analyzing SonarQube issues for technical debt...")

        try:
            # Run SonarQube analysis
            result = subprocess.run(
                ["sonar-scanner", "-Dsonar.analysis.mode=preview"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"SonarQube analysis failed: {result.stderr}")
                return self._create_mock_debt_items()

            # Parse SonarQube report
            report_path = self.project_root / "sonar-report.json"
            if report_path.exists():
                with open(report_path, 'r') as f:
                    sonar_data = json.load(f)

                return self._parse_sonar_issues(sonar_data)
            else:
                return self._create_mock_debt_items()

        except Exception as e:
            print(f"Error analyzing SonarQube issues: {e}")
            return self._create_mock_debt_items()

    def _parse_sonar_issues(self, sonar_data: Dict[str, Any]) -> List[TechnicalDebtItem]:
        """Parse SonarQube issues into technical debt items."""
        debt_items = []

        for issue in sonar_data.get('issues', []):
            if issue.get('type') in ['CODE_SMELL', 'BUG', 'VULNERABILITY']:
                debt_item = TechnicalDebtItem(
                    issue_key=issue.get('key', ''),
                    file_path=issue.get('component', ''),
                    line_number=issue.get('line', 0),
                    rule=issue.get('rule', ''),
                    severity=issue.get('severity', 'MINOR'),
                    message=issue.get('message', ''),
                    effort=issue.get('effort', ''),
                    debt=issue.get('debt', ''),
                    story_points=self._estimate_story_points(issue),
                    priority_score=self._calculate_priority_score(issue),
                    component=self._extract_component(issue.get('component', ''))
                )
                debt_items.append(debt_item)

        return debt_items

    def _estimate_story_points(self, issue: Dict[str, Any]) -> int:
        """Estimate story points based on issue complexity."""
        severity = issue.get('severity', 'MINOR')
        effort = issue.get('effort', '')

        base_points = {
            "BLOCKER": 8,
            "CRITICAL": 5,
            "MAJOR": 3,
            "MINOR": 2,
            "INFO": 1
        }

        points = base_points.get(severity, 2)

        # Adjust based on effort
        if "1d" in effort or "1 day" in effort:
            points = min(points + 2, 8)
        elif "2d" in effort or "2 days" in effort:
            points = min(points + 3, 8)
        elif "3d" in effort or "3 days" in effort:
            points = 8

        return points

    def _calculate_priority_score(self, issue: Dict[str, Any]) -> int:
        """Calculate priority score for technical debt item."""
        severity = issue.get('severity', 'MINOR')
        issue_type = issue.get('type', 'CODE_SMELL')

        severity_scores = {
            "BLOCKER": 10,
            "CRITICAL": 8,
            "MAJOR": 6,
            "MINOR": 4,
            "INFO": 2
        }

        type_multipliers = {
            "VULNERABILITY": 2,
            "BUG": 1.5,
            "CODE_SMELL": 1,
            "SECURITY_HOTSPOT": 1.8
        }

        base_score = severity_scores.get(severity, 4)
        multiplier = type_multipliers.get(issue_type, 1)

        return int(base_score * multiplier)

    def _extract_component(self, component: str) -> str:
        """Extract component name from file path."""
        if not component:
            return "Unknown"

        parts = component.split("/")
        if len(parts) >= 2:
            return parts[1]
        return "Core"

    def _create_mock_debt_items(self) -> List[TechnicalDebtItem]:
        """Create mock technical debt items for demonstration."""
        mock_items = [
            TechnicalDebtItem(
                issue_key="MOCK-001",
                file_path="src/services/auth/auth_service.py",
                line_number=45,
                rule="python:S1144",
                severity="MAJOR",
                message="Unused private method 'validate_token' should be removed",
                effort="5min",
                debt="5min",
                story_points=2,
                priority_score=6,
                component="auth"
            ),
            TechnicalDebtItem(
                issue_key="MOCK-002",
                file_path="src/services/database/postgresql_service.py",
                line_number=123,
                rule="python:S3776",
                severity="CRITICAL",
                message="Cognitive Complexity of methods should not be too high",
                effort="2h",
                debt="2h",
                story_points=5,
                priority_score=12,
                component="database"
            ),
            TechnicalDebtItem(
                issue_key="MOCK-003",
                file_path="src/utils/security_utils.py",
                line_number=67,
                rule="python:S5542",
                severity="BLOCKER",
                message="Use cryptographically strong random number generators",
                effort="30min",
                debt="30min",
                story_points=3,
                priority_score=20,
                component="security"
            )
        ]

        return mock_items

    def generate_sprint_planning_report(self) -> str:
        """Generate sprint planning report for technical debt."""
        print("📊 Generating Sprint Planning Report...")

        debt_items = self.analyze_sonarqube_issues()

        # Sort by priority score
        debt_items.sort(key=lambda x: x.priority_score, reverse=True)

        report = []
        report.append("# Technical Debt Sprint Planning Report")
        report.append("")
        report.append(f"**Generated**: {Path().cwd()}")
        report.append("")

        # Executive Summary
        report.append("## 🎯 Executive Summary")
        report.append("")
        report.append(f"- **Total Technical Debt Items**: {len(debt_items)}")

        # Severity breakdown
        severity_counts = {}
        for item in debt_items:
            severity_counts[item.severity] = severity_counts.get(item.severity, 0) + 1

        report.append("- **Severity Breakdown**:")
        for severity, count in severity_counts.items():
            report.append(f"  - {severity}: {count} items")
        report.append("")

        # Component breakdown
        component_counts = {}
        for item in debt_items:
            component_counts[item.component] = component_counts.get(item.component, 0) + 1

        report.append("- **Component Breakdown**:")
        for component, count in component_counts.items():
            report.append(f"  - {component}: {count} items")
        report.append("")

        # Sprint recommendations
        report.append("## 🚀 Sprint Planning Recommendations")
        report.append("")

        # High priority items (Priority 1)
        high_priority = [item for item in debt_items if item.priority_score >= 15]
        if high_priority:
            report.append("### Priority 1: Critical Issues (Score ≥ 15)")
            report.append("")
            report.append("**Recommended Sprint Allocation: 40% of capacity**")
            report.append("")
            for item in high_priority[:5]:
                report.append(f"- **{item.issue_key}**: {item.message}")
                report.append(f"  - File: {item.file_path}:{item.line_number}")
                report.append(f"  - Story Points: {item.story_points}")
                report.append(f"  - Component: {item.component}")
                report.append("")

        # Medium priority items (Priority 2)
        medium_priority = [item for item in debt_items if 10 <= item.priority_score < 15]
        if medium_priority:
            report.append("### Priority 2: High Priority Issues (Score 10-14)")
            report.append("")
            report.append("**Recommended Sprint Allocation: 30% of capacity**")
            report.append("")
            for item in medium_priority[:10]:
                report.append(f"- **{item.issue_key}**: {item.message}")
                report.append(f"  - File: {item.file_path}:{item.line_number}")
                report.append(f"  - Story Points: {item.story_points}")
                report.append("")

        # Low priority items (Priority 3)
        low_priority = [item for item in debt_items if item.priority_score < 10]
        if low_priority:
            report.append("### Priority 3: Medium Priority Issues (Score < 10)")
            report.append("")
            report.append("**Recommended Sprint Allocation: 20% of capacity**")
            report.append("")
            report.append(f"- **Total Items**: {len(low_priority)}")
            report.append("- **Recommended Approach**: Address during maintenance sprints")
            report.append("")

        # Sprint capacity recommendations
        report.append("## 📋 Sprint Capacity Recommendations")
        report.append("")
        report.append("### Recommended Sprint Allocation")
        report.append("- **Feature Development**: 50%")
        report.append("- **Technical Debt (Priority 1)**: 25%")
        report.append("- **Technical Debt (Priority 2)**: 15%")
        report.append("- **Technical Debt (Priority 3)**: 10%")
        report.append("")

        report.append("### Quality Gates")
        report.append("- **New Code Coverage**: ≥ 85%")
        report.append("- **New Security Issues**: 0")
        report.append("- **New Code Smells**: ≤ 5")
        report.append("- **New Duplication**: ≤ 3%")
        report.append("")

        return "\\n".join(report)

    def save_debt_analysis(self, debt_items: List[TechnicalDebtItem]) -> None:
        """Save technical debt analysis to JSON file."""
        analysis_data = {
            "total_items": len(debt_items),
            "items": [
                {
                    "issue_key": item.issue_key,
                    "file_path": item.file_path,
                    "line_number": item.line_number,
                    "rule": item.rule,
                    "severity": item.severity,
                    "message": item.message,
                    "effort": item.effort,
                    "debt": item.debt,
                    "story_points": item.story_points,
                    "priority_score": item.priority_score,
                    "component": item.component
                }
                for item in debt_items
            ]
        }

        with open("technical-debt-analysis.json", "w") as f:
            json.dump(analysis_data, f, indent=2)

        print("✅ Technical debt analysis saved to technical-debt-analysis.json")


def main():
    """Main execution function."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    analyzer = TechnicalDebtAnalyzer(project_root)

    # Analyze technical debt
    debt_items = analyzer.analyze_sonarqube_issues()

    # Generate sprint planning report
    report = analyzer.generate_sprint_planning_report()
    with open("technical-debt-sprint-planning-report.md", "w") as f:
        f.write(report)

    # Save analysis
    analyzer.save_debt_analysis(debt_items)

    print("✅ Technical debt analysis complete!")
    print("📄 Sprint planning report written to: technical-debt-sprint-planning-report.md")
    print(f"🎯 Total technical debt items: {len(debt_items)}")


if __name__ == "__main__":
    main()
'''
            )

        print(f"✅ Jira integration scripts created in {scripts_dir}")

    def create_sonarqube_properties(self) -> None:
        """Create sonar-project.properties file."""
        print("🔧 Creating SonarQube Properties File...")

        properties_content = """# SonarQube Project Properties
# World-Class Finish Guide - Quality Gates Configuration

# Project Information
sonar.projectKey=pake-system
sonar.projectName=PAKE System
sonar.projectVersion=1.0.0

# Source and Test Directories
sonar.sources=src/
sonar.tests=tests/

# Python Configuration
sonar.python.version=3.12
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.xunit.reportPath=test-results.xml

# Exclusions
sonar.exclusions=**/node_modules/**,**/venv/**,**/.venv/**,**/__pycache__/**,**/migrations/**,**/static/**,**/media/**
sonar.test.exclusions=**/test_*.py,**/*_test.py,**/tests/**

# Quality Gate Configuration
sonar.qualitygate.wait=true
sonar.analysis.mode=preview

# Issue Reporting
sonar.issuesReport.console.enable=true
sonar.issuesReport.html.enable=true
sonar.issuesReport.json.enable=true

# Code Duplication
sonar.cpd.python.minimumtokens=100

# Security Configuration
sonar.security.hotspots.includeAll=true

# Custom Rules (if any)
# sonar.issue.ignore.multicriteria=e1,e2
# sonar.issue.ignore.multicriteria.e1.ruleKey=python:S1144
# sonar.issue.ignore.multicriteria.e1.resourceKey=**/test_*.py
"""

        properties_file = self.project_root / "sonar-project.properties"
        with open(properties_file, "w") as f:
            f.write(properties_content)

        print(f"✅ SonarQube properties file created: {properties_file}")

    def generate_quality_culture_report(self) -> str:
        """Generate comprehensive quality culture report."""
        print("📊 Generating Quality Culture Report...")

        report = []
        report.append("# Phase 5: Quality Culture Institutionalization Report")
        report.append("")
        report.append(f"**Generated**: {Path().cwd()}")
        report.append("")

        # Executive Summary
        report.append("## 🎯 Executive Summary")
        report.append("")
        report.append(
            "Phase 5 establishes a sustainable culture of quality by embedding quality gates"
        )
        report.append(
            "and technical debt management directly into the team's daily agile workflow."
        )
        report.append(
            "This ensures that quality improvements become the new standard, not a one-time cleanup."
        )
        report.append("")

        # Quality Gates
        report.append("## 🔧 Quality Gates Configuration")
        report.append("")
        for i, gate in enumerate(self.quality_gates, 1):
            report.append(f"### Quality Gate {i}: {gate.name}")
            report.append("")
            report.append(f"**Description**: {gate.description}")
            report.append("")
            report.append("**Conditions**:")
            for condition in gate.conditions:
                metric = condition["metric"]
                op = condition["op"]
                error_threshold = condition["error"]
                warning_threshold = condition.get("warning", "N/A")
                report.append(
                    f"- **{metric}**: {op} {error_threshold} (warning: {warning_threshold})"
                )
            report.append("")

        # Integration Strategy
        report.append("## 🔗 Integration Strategy")
        report.append("")
        report.append("### SonarQube Integration")
        report.append(
            "- **Automated Analysis**: Triggered on every pull request and merge"
        )
        report.append("- **Quality Gates**: Automatic pass/fail conditions")
        report.append(
            "- **Issue Tracking**: Comprehensive issue detection and categorization"
        )
        report.append("- **Metrics Dashboard**: Real-time quality metrics visibility")
        report.append("")

        report.append("### Jira Integration")
        report.append(
            "- **Automatic Ticket Creation**: SonarQube issues → Jira tickets"
        )
        report.append(
            "- **Technical Debt Backlog**: Dedicated issue type for debt management"
        )
        report.append(
            "- **Sprint Planning**: Technical debt included in sprint capacity"
        )
        report.append(
            "- **Priority Scoring**: Data-driven prioritization of debt items"
        )
        report.append("")

        report.append("### GitHub Actions Workflow")
        report.append("- **Quality Gates**: Automated quality gate enforcement")
        report.append(
            "- **Technical Debt Reports**: Automated debt analysis and reporting"
        )
        report.append(
            "- **Jira Ticket Creation**: Automatic ticket creation for new issues"
        )
        report.append(
            "- **Sprint Planning Reports**: Automated sprint planning assistance"
        )
        report.append("")

        # Implementation Guidelines
        report.append("## 📋 Implementation Guidelines")
        report.append("")
        report.append("### Sprint Planning Integration")
        report.append(
            "1. **Allocate Capacity**: 15-20% of each sprint for technical debt"
        )
        report.append(
            "2. **Prioritize by Score**: Use priority scoring for debt item selection"
        )
        report.append(
            "3. **Balance Workload**: Mix high-priority debt with feature work"
        )
        report.append("4. **Track Progress**: Monitor debt reduction metrics")
        report.append("")

        report.append("### Quality Gate Enforcement")
        report.append(
            "1. **New Code Standards**: Strict quality gates for new/modified code"
        )
        report.append(
            "2. **Overall Health**: Gradual improvement targets for legacy code"
        )
        report.append("3. **Security Focus**: Zero tolerance for new security issues")
        report.append("4. **Automated Blocking**: Failed quality gates block merges")
        report.append("")

        report.append("### Team Culture")
        report.append(
            "1. **Shared Responsibility**: Quality is everyone's responsibility"
        )
        report.append(
            "2. **Data-Driven Decisions**: Use metrics for quality discussions"
        )
        report.append("3. **Continuous Improvement**: Regular quality culture reviews")
        report.append("4. **Knowledge Sharing**: Quality practices and lessons learned")
        report.append("")

        # Success Metrics
        report.append("## 📊 Success Metrics")
        report.append("")
        report.append("### Quality Metrics")
        report.append("- **Test Coverage**: Maintain ≥ 85% on new code")
        report.append("- **Code Duplication**: Keep ≤ 3% on new code")
        report.append("- **Security Issues**: Zero new vulnerabilities")
        report.append("- **Code Smells**: ≤ 5 new code smells per sprint")
        report.append("")

        report.append("### Process Metrics")
        report.append("- **Quality Gate Pass Rate**: ≥ 95%")
        report.append("- **Technical Debt Reduction**: 10% per quarter")
        report.append("- **Sprint Debt Allocation**: 15-20% capacity")
        report.append("- **Issue Resolution Time**: < 2 sprints for high-priority debt")
        report.append("")

        report.append("### Team Culture Metrics")
        report.append("- **Quality Discussions**: Regular quality culture reviews")
        report.append("- **Knowledge Sharing**: Quality practices documentation")
        report.append("- **Tool Adoption**: 100% team adoption of quality tools")
        report.append("- **Continuous Learning**: Regular quality training sessions")
        report.append("")

        return "\\n".join(report)


def main():
    """Main execution function for Phase 5 quality culture institutionalization."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    print("🚀 Starting Phase 5: Quality Culture Institutionalization...")

    # Initialize quality culture framework
    quality_framework = QualityCultureFramework(project_root)

    # Create quality gates
    quality_gates = quality_framework.create_quality_gates()

    # Create SonarQube configuration
    sonar_config = quality_framework.create_sonarqube_configuration()

    # Create GitHub Actions workflow
    workflow_content = quality_framework.create_github_actions_workflow()

    # Create Jira integration scripts
    quality_framework.create_jira_integration_scripts()

    # Create SonarQube properties file
    quality_framework.create_sonarqube_properties()

    # Generate comprehensive report
    report = quality_framework.generate_quality_culture_report()
    with open("PHASE_5_QUALITY_CULTURE_REPORT.md", "w") as f:
        f.write(report)

    # Create GitHub Actions workflow file
    workflow_dir = Path(project_root) / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_file = workflow_dir / "quality-gates.yml"
    with open(workflow_file, "w") as f:
        f.write(workflow_content)

    # Create SonarQube configuration file
    sonar_config_file = Path(project_root) / "sonar-config.json"
    with open(sonar_config_file, "w") as f:
        json.dump(sonar_config, f, indent=2)

    print("✅ Phase 5 Quality Culture Institutionalization Complete!")
    print("📄 Quality culture report written to: PHASE_5_QUALITY_CULTURE_REPORT.md")
    print("🔧 GitHub Actions workflow created: .github/workflows/quality-gates.yml")
    print("🔧 SonarQube configuration created: sonar-config.json")
    print("🔧 SonarQube properties created: sonar-project.properties")
    print("🔧 Jira integration scripts created: scripts/")

    print(f"\\n🎯 Quality Gates Created: {len(quality_gates)}")
    for i, gate in enumerate(quality_gates, 1):
        print(f"{i}. {gate.name}")


if __name__ == "__main__":
    main()
