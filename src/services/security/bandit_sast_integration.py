#!/usr/bin/env python3
"""PAKE System - Bandit SAST Integration
Implements Bandit static analysis security testing (SAST) integration with proper
S603 suppression policy as specified in Phase 2 of the engineering plan.

This module addresses the challenge of "alert fatigue" by implementing a policy
that requires explicit, audited suppression for S603 violations, transforming
noisy warnings into deliberate, auditable security decisions.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class BanditSASTIntegration:
    """Bandit SAST integration with proper suppression policy.

    This class implements the security scanning strategy from the engineering plan,
    focusing on S311 (random module usage) and S603 (subprocess usage) with proper
    suppression policies to avoid alert fatigue.
    """

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.bandit_config = self._load_bandit_config()
        self.suppression_policy = self._load_suppression_policy()

    def _load_bandit_config(self) -> dict[str, Any]:
        """Load Bandit configuration from pyproject.toml."""
        config_file = self.project_root / "pyproject.toml"

        if not config_file.exists():
            return self._default_bandit_config()

        try:
            import tomllib

            with open(config_file, "rb") as f:
                data = tomllib.load(f)
                return data.get("tool", {}).get("bandit", {})
        except ImportError:
            # Fallback for Python < 3.11
            try:
                import tomli

                with open(config_file, "rb") as f:
                    data = tomli.load(f)
                    return data.get("tool", {}).get("bandit", {})
            except ImportError:
                return self._default_bandit_config()

    def _default_bandit_config(self) -> dict[str, Any]:
        """Default Bandit configuration."""
        return {
            "exclude_dirs": [
                "tests",
                "venv",
                ".venv",
                "mcp-env",
                "test_env",
                "security_backups",
                "backups",
            ],
            "skips": ["B101", "B601"],  # Skip assert and shell injection tests
        }

    def _load_suppression_policy(self) -> dict[str, Any]:
        """Load suppression policy configuration."""
        policy_file = self.project_root / "security_suppression_policy.json"

        if policy_file.exists():
            try:
                with open(policy_file) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        return self._default_suppression_policy()

    def _default_suppression_policy(self) -> dict[str, Any]:
        """Default suppression policy."""
        return {
            "s603_policy": {
                "enabled": True,
                "require_explicit_suppression": True,
                "suppression_format": "# nosec B603 - Brief justification",
                "audit_required": True,
                "max_suppressions_per_file": 10,
            },
            "s311_policy": {
                "enabled": True,
                "require_replacement": True,
                "replacement_module": "secrets",
                "audit_required": True,
            },
            "general_policy": {
                "audit_all_suppressions": True,
                "suppression_review_required": True,
                "max_suppressions_per_project": 100,
            },
        }

    def run_security_scan(self, target_path: str = None) -> dict[str, Any]:
        """Run comprehensive security scan with Bandit.

        Args:
            target_path: Path to scan (defaults to src/)

        Returns:
            Dictionary containing scan results and analysis
        """
        if target_path is None:
            target_path = str(self.project_root / "src")

        # Run Bandit scan
        bandit_results = self._run_bandit_scan(target_path)

        # Analyze results
        analysis = self._analyze_scan_results(bandit_results)

        # Check suppression policy compliance
        suppression_analysis = self._analyze_suppression_compliance(target_path)

        return {
            "scan_results": bandit_results,
            "analysis": analysis,
            "suppression_analysis": suppression_analysis,
            "recommendations": self._generate_recommendations(
                analysis, suppression_analysis
            ),
        }

    def _run_bandit_scan(self, target_path: str) -> dict[str, Any]:
        """Run Bandit scan on target path."""
        try:
            # Run Bandit with JSON output
            cmd = [
                "bandit",
                "-r",
                target_path,
                "-f",
                "json",
                "-o",
                "/tmp/bandit_report.json",
            ]

            # Add configuration options
            if "exclude_dirs" in self.bandit_config:
                for exclude_dir in self.bandit_config["exclude_dirs"]:
                    cmd.extend(["-x", exclude_dir])

            if "skips" in self.bandit_config:
                cmd.extend(["-s", ",".join(self.bandit_config["skips"])])

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # Read the JSON report
            if os.path.exists("/tmp/bandit_report.json"):
                with open("/tmp/bandit_report.json") as f:
                    return json.load(f)
            else:
                return {
                    "error": "Failed to generate Bandit report",
                    "stderr": result.stderr,
                }

        except subprocess.TimeoutExpired:
            return {"error": "Bandit scan timed out"}
        except FileNotFoundError:
            return {"error": "Bandit not installed"}
        except Exception as e:
            return {"error": f"Bandit scan failed: {str(e)}"}

    def _analyze_scan_results(self, results: dict[str, Any]) -> dict[str, Any]:
        """Analyze Bandit scan results."""
        if "error" in results:
            return {"error": results["error"]}

        findings = results.get("results", [])

        # Categorize findings
        categorized_findings = {
            "S311": [],  # random module usage
            "S603": [],  # subprocess usage
            "other": [],
            "high_severity": [],
            "medium_severity": [],
            "low_severity": [],
        }

        for finding in findings:
            test_id = finding.get("test_id", "")
            severity = finding.get("issue_severity", "UNKNOWN")

            # Categorize by test ID
            if test_id == "S311":
                categorized_findings["S311"].append(finding)
            elif test_id == "S603":
                categorized_findings["S603"].append(finding)
            else:
                categorized_findings["other"].append(finding)

            # Categorize by severity
            if severity == "HIGH":
                categorized_findings["high_severity"].append(finding)
            elif severity == "MEDIUM":
                categorized_findings["medium_severity"].append(finding)
            elif severity == "LOW":
                categorized_findings["low_severity"].append(finding)

        # Calculate statistics
        stats = {
            "total_findings": len(findings),
            "s311_count": len(categorized_findings["S311"]),
            "s603_count": len(categorized_findings["S603"]),
            "other_count": len(categorized_findings["other"]),
            "high_severity_count": len(categorized_findings["high_severity"]),
            "medium_severity_count": len(categorized_findings["medium_severity"]),
            "low_severity_count": len(categorized_findings["low_severity"]),
        }

        return {
            "categorized_findings": categorized_findings,
            "statistics": stats,
            "summary": self._generate_summary(stats),
        }

    def _analyze_suppression_compliance(self, target_path: str) -> dict[str, Any]:
        """Analyze suppression policy compliance."""
        return {
            "s603_compliance": self._check_s603_compliance(target_path),
            "s311_compliance": self._check_s311_compliance(target_path),
            "general_compliance": self._check_general_compliance(target_path),
        }

    def _check_s603_compliance(self, target_path: str) -> dict[str, Any]:
        """Check S603 suppression policy compliance."""
        if not self.suppression_policy["s603_policy"]["enabled"]:
            return {"status": "disabled"}

        # Find all Python files
        python_files = list(Path(target_path).rglob("*.py"))

        violations = []
        compliant_files = []

        for file_path in python_files:
            try:
                with open(file_path) as f:
                    content = f.read()
                    lines = content.split("\n")

                # Check for subprocess usage
                subprocess_lines = []
                for i, line in enumerate(lines):
                    if "subprocess" in line and "import" not in line:
                        subprocess_lines.append((i + 1, line.strip()))

                if subprocess_lines:
                    # Check for proper suppression comments
                    suppressions = []
                    for line_num, line in subprocess_lines:
                        # Look for nosec comment on the same line or previous line
                        if (
                            "# nosec B603" in line
                            or line_num > 1
                            and "# nosec B603" in lines[line_num - 2]
                        ):
                            suppressions.append((line_num, line))

                    if len(suppressions) != len(subprocess_lines):
                        violations.append(
                            {
                                "file": str(file_path),
                                "subprocess_lines": subprocess_lines,
                                "suppressions": suppressions,
                                "missing_suppressions": len(subprocess_lines)
                                - len(suppressions),
                            }
                        )
                    else:
                        compliant_files.append(str(file_path))

            except (OSError, UnicodeDecodeError):
                continue

        return {
            "status": "compliant" if not violations else "non_compliant",
            "violations": violations,
            "compliant_files": compliant_files,
            "violation_count": len(violations),
        }

    def _check_s311_compliance(self, target_path: str) -> dict[str, Any]:
        """Check S311 suppression policy compliance."""
        if not self.suppression_policy["s311_policy"]["enabled"]:
            return {"status": "disabled"}

        # Find all Python files
        python_files = list(Path(target_path).rglob("*.py"))

        violations = []
        compliant_files = []

        for file_path in python_files:
            try:
                with open(file_path) as f:
                    content = f.read()

                # Check for random module usage
                if "import random" in content or "from random import" in content:
                    # Check if secrets module is also imported
                    if (
                        "import secrets" not in content
                        and "from secrets import" not in content
                    ):
                        violations.append(
                            {
                                "file": str(file_path),
                                "issue": "random module used without secrets module",
                                "recommendation": "Replace random with secrets for cryptographic purposes",
                            }
                        )
                    else:
                        compliant_files.append(str(file_path))

            except (OSError, UnicodeDecodeError):
                continue

        return {
            "status": "compliant" if not violations else "non_compliant",
            "violations": violations,
            "compliant_files": compliant_files,
            "violation_count": len(violations),
        }

    def _check_general_compliance(self, target_path: str) -> dict[str, Any]:
        """Check general suppression policy compliance."""
        # Find all Python files
        python_files = list(Path(target_path).rglob("*.py"))

        total_suppressions = 0
        files_with_suppressions = []

        for file_path in python_files:
            try:
                with open(file_path) as f:
                    content = f.read()

                # Count nosec comments
                nosec_count = content.count("# nosec")
                if nosec_count > 0:
                    total_suppressions += nosec_count
                    files_with_suppressions.append(
                        {
                            "file": str(file_path),
                            "suppression_count": nosec_count,
                        }
                    )

            except (OSError, UnicodeDecodeError):
                continue

        max_suppressions = self.suppression_policy["general_policy"][
            "max_suppressions_per_project"
        ]

        return {
            "total_suppressions": total_suppressions,
            "files_with_suppressions": files_with_suppressions,
            "within_limits": total_suppressions <= max_suppressions,
            "max_allowed": max_suppressions,
        }

    def _generate_summary(self, stats: dict[str, Any]) -> str:
        """Generate summary of scan results."""
        summary_parts = []

        if stats["total_findings"] == 0:
            return "No security issues found."

        summary_parts.append(f"Total findings: {stats['total_findings']}")

        if stats["s311_count"] > 0:
            summary_parts.append(
                f"S311 (random module): {stats['s311_count']} - Replace with secrets module"
            )

        if stats["s603_count"] > 0:
            summary_parts.append(
                f"S603 (subprocess): {stats['s603_count']} - Add explicit suppression comments"
            )

        if stats["high_severity_count"] > 0:
            summary_parts.append(
                f"High severity: {stats['high_severity_count']} - Immediate attention required"
            )

        return "; ".join(summary_parts)

    def _generate_recommendations(
        self, analysis: dict[str, Any], suppression_analysis: dict[str, Any]
    ) -> list[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if "error" in analysis:
            recommendations.append(f"Fix scan error: {analysis['error']}")
            return recommendations

        stats = analysis.get("statistics", {})

        # S311 recommendations
        if stats.get("s311_count", 0) > 0:
            recommendations.append(
                "Replace random module usage with secrets module for cryptographic purposes"
            )

        # S603 recommendations
        if stats.get("s603_count", 0) > 0:
            recommendations.append(
                "Add explicit suppression comments (# nosec B603) for safe subprocess calls"
            )

        # High severity recommendations
        if stats.get("high_severity_count", 0) > 0:
            recommendations.append("Address high severity security issues immediately")

        # Suppression compliance recommendations
        s603_compliance = suppression_analysis.get("s603_compliance", {})
        if s603_compliance.get("status") == "non_compliant":
            recommendations.append(
                f"Fix S603 suppression compliance: {s603_compliance['violation_count']} violations"
            )

        s311_compliance = suppression_analysis.get("s311_compliance", {})
        if s311_compliance.get("status") == "non_compliant":
            recommendations.append(
                f"Fix S311 compliance: {s311_compliance['violation_count']} violations"
            )

        return recommendations

    def generate_security_report(self, scan_results: dict[str, Any]) -> str:
        """Generate human-readable security report."""
        report_parts = []

        report_parts.append("=" * 60)
        report_parts.append("PAKE System Security Scan Report")
        report_parts.append("=" * 60)

        # Analysis summary
        analysis = scan_results.get("analysis", {})
        if "error" in analysis:
            report_parts.append(f"ERROR: {analysis['error']}")
            return "\n".join(report_parts)

        summary = analysis.get("summary", "No summary available")
        report_parts.append(f"Summary: {summary}")
        report_parts.append("")

        # Statistics
        stats = analysis.get("statistics", {})
        report_parts.append("Statistics:")
        report_parts.append(f"  Total findings: {stats.get('total_findings', 0)}")
        report_parts.append(f"  S311 (random module): {stats.get('s311_count', 0)}")
        report_parts.append(f"  S603 (subprocess): {stats.get('s603_count', 0)}")
        report_parts.append(f"  High severity: {stats.get('high_severity_count', 0)}")
        report_parts.append(
            f"  Medium severity: {stats.get('medium_severity_count', 0)}"
        )
        report_parts.append(f"  Low severity: {stats.get('low_severity_count', 0)}")
        report_parts.append("")

        # Suppression analysis
        suppression_analysis = scan_results.get("suppression_analysis", {})
        report_parts.append("Suppression Policy Compliance:")

        s603_compliance = suppression_analysis.get("s603_compliance", {})
        report_parts.append(
            f"  S603 compliance: {s603_compliance.get('status', 'unknown')}"
        )
        if s603_compliance.get("violation_count", 0) > 0:
            report_parts.append(f"    Violations: {s603_compliance['violation_count']}")

        s311_compliance = suppression_analysis.get("s311_compliance", {})
        report_parts.append(
            f"  S311 compliance: {s311_compliance.get('status', 'unknown')}"
        )
        if s311_compliance.get("violation_count", 0) > 0:
            report_parts.append(f"    Violations: {s311_compliance['violation_count']}")

        general_compliance = suppression_analysis.get("general_compliance", {})
        report_parts.append(
            f"  Total suppressions: {general_compliance.get('total_suppressions', 0)}"
        )
        report_parts.append(
            f"  Within limits: {general_compliance.get('within_limits', False)}"
        )
        report_parts.append("")

        # Recommendations
        recommendations = scan_results.get("recommendations", [])
        if recommendations:
            report_parts.append("Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                report_parts.append(f"  {i}. {rec}")
            report_parts.append("")

        report_parts.append("=" * 60)

        return "\n".join(report_parts)


# Utility functions
def run_security_scan(project_root: str = None) -> dict[str, Any]:
    """Run security scan on the project.

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary containing scan results
    """
    integration = BanditSASTIntegration(project_root)
    return integration.run_security_scan()


def generate_security_report(project_root: str = None) -> str:
    """Generate security report for the project.

    Args:
        project_root: Root directory of the project

    Returns:
        Human-readable security report
    """
    integration = BanditSASTIntegration(project_root)
    scan_results = integration.run_security_scan()
    return integration.generate_security_report(scan_results)


# Example usage and testing
if __name__ == "__main__":
    print("Running PAKE System Security Scan...")

    # Run security scan
    results = run_security_scan()

    # Generate report
    report = generate_security_report()
    print(report)

    # Save report to file
    with open("security_scan_report.txt", "w") as f:
        f.write(report)

    print("Security scan completed. Report saved to security_scan_report.txt")
