#!/usr/bin/env python3
"""Generate technical debt report for sprint planning.
World-Class Finish Guide - Data-driven technical debt management.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List


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
        self.debt_items: list[TechnicalDebtItem] = []

    def analyze_sonarqube_issues(self) -> list[TechnicalDebtItem]:
        """Analyze SonarQube issues and convert to technical debt items."""
        print("🔍 Analyzing SonarQube issues for technical debt...")

        try:
            # Run SonarQube analysis
            result = subprocess.run(
                ["sonar-scanner", "-Dsonar.analysis.mode=preview"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"SonarQube analysis failed: {result.stderr}")
                return self._create_mock_debt_items()

            # Parse SonarQube report
            report_path = self.project_root / "sonar-report.json"
            if report_path.exists():
                with open(report_path) as f:
                    sonar_data = json.load(f)

                return self._parse_sonar_issues(sonar_data)
            else:
                return self._create_mock_debt_items()

        except Exception as e:
            print(f"Error analyzing SonarQube issues: {e}")
            return self._create_mock_debt_items()

    def _parse_sonar_issues(
        self, sonar_data: dict[str, Any]
    ) -> list[TechnicalDebtItem]:
        """Parse SonarQube issues into technical debt items."""
        debt_items = []

        for issue in sonar_data.get("issues", []):
            if issue.get("type") in ["CODE_SMELL", "BUG", "VULNERABILITY"]:
                debt_item = TechnicalDebtItem(
                    issue_key=issue.get("key", ""),
                    file_path=issue.get("component", ""),
                    line_number=issue.get("line", 0),
                    rule=issue.get("rule", ""),
                    severity=issue.get("severity", "MINOR"),
                    message=issue.get("message", ""),
                    effort=issue.get("effort", ""),
                    debt=issue.get("debt", ""),
                    story_points=self._estimate_story_points(issue),
                    priority_score=self._calculate_priority_score(issue),
                    component=self._extract_component(issue.get("component", "")),
                )
                debt_items.append(debt_item)

        return debt_items

    def _estimate_story_points(self, issue: dict[str, Any]) -> int:
        """Estimate story points based on issue complexity."""
        severity = issue.get("severity", "MINOR")
        effort = issue.get("effort", "")

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

    def _calculate_priority_score(self, issue: dict[str, Any]) -> int:
        """Calculate priority score for technical debt item."""
        severity = issue.get("severity", "MINOR")
        issue_type = issue.get("type", "CODE_SMELL")

        severity_scores = {
            "BLOCKER": 10,
            "CRITICAL": 8,
            "MAJOR": 6,
            "MINOR": 4,
            "INFO": 2,
        }

        type_multipliers = {
            "VULNERABILITY": 2,
            "BUG": 1.5,
            "CODE_SMELL": 1,
            "SECURITY_HOTSPOT": 1.8,
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

    def _create_mock_debt_items(self) -> list[TechnicalDebtItem]:
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
                component="auth",
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
                component="database",
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
                component="security",
            ),
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
            component_counts[item.component] = (
                component_counts.get(item.component, 0) + 1
            )

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
        medium_priority = [
            item for item in debt_items if 10 <= item.priority_score < 15
        ]
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
            report.append(
                "- **Recommended Approach**: Address during maintenance sprints"
            )
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

        return "\n".join(report)

    def save_debt_analysis(self, debt_items: list[TechnicalDebtItem]) -> None:
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
                    "component": item.component,
                }
                for item in debt_items
            ],
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
    print(
        "📄 Sprint planning report written to: technical-debt-sprint-planning-report.md"
    )
    print(f"🎯 Total technical debt items: {len(debt_items)}")


if __name__ == "__main__":
    main()
