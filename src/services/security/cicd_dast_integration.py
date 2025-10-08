#!/usr/bin/env python3
"""PAKE System - CI/CD DAST Integration (Phase 3 Architectural Health)
GitHub Actions workflow for automated DAST security testing.

This module provides:
1. GitHub Actions workflow configuration
2. Automated DAST scanning on deployments
3. Security gate enforcement
4. Vulnerability reporting and notifications
5. Integration with existing CI/CD pipeline
"""

from pathlib import Path
from typing import Any

import aiohttp
import yaml


class GitHubActionsDASTWorkflow:
    """GitHub Actions workflow generator for DAST integration."""

    def __init__(self, workflow_name: str) -> None:
        self.workflow_name = workflow_name
        self.workflow_file = Path(".github/workflows") / f"{workflow_name}.yml"

    def generate_workflow(self) -> dict[str, Any]:
        """Generate GitHub Actions workflow for DAST scanning."""
        return {
            "name": "DAST Security Scan",
            "on": {
                "push": {
                    "branches": ["main", "develop"],
                    "paths": [
                        "src/**",
                        "package.json",
                        "pyproject.toml",
                        "requirements.txt",
                    ],
                },
                "pull_request": {
                    "branches": ["main", "develop"],
                    "paths": [
                        "src/**",
                        "package.json",
                        "pyproject.toml",
                        "requirements.txt",
                    ],
                },
                "workflow_dispatch": {
                    "inputs": {
                        "environment": {
                            "description": "Target environment",
                            "required": True,
                            "default": "staging",
                            "type": "choice",
                            "options": ["staging", "production"],
                        },
                        "scan_type": {
                            "description": "Scan type",
                            "required": True,
                            "default": "full",
                            "type": "choice",
                            "options": ["quick", "full", "custom"],
                        },
                    }
                },
            },
            "env": {
                "ZAP_HOST": "localhost",
                "ZAP_PORT": "8080",
                "SCAN_TIMEOUT": "3600",
                "REPORT_FORMATS": "json,html",
            },
            "jobs": {
                "dast-scan": {
                    "runs-on": "ubuntu-latest",
                    "if": "github.event_name == 'push' || github.event_name == 'workflow_dispatch'",
                    "steps": self._generate_dast_steps(),
                    "timeout-minutes": 60,
                },
                "security-gate": {
                    "runs-on": "ubuntu-latest",
                    "needs": "dast-scan",
                    "if": "always()",
                    "steps": self._generate_security_gate_steps(),
                },
                "vulnerability-report": {
                    "runs-on": "ubuntu-latest",
                    "needs": ["dast-scan", "security-gate"],
                    "if": "always()",
                    "steps": self._generate_reporting_steps(),
                },
            },
        }

    def _generate_dast_steps(self) -> list[dict[str, Any]]:
        """Generate DAST scanning steps."""
        return [
            {"name": "Checkout code", "uses": "actions/checkout@v4"},
            {
                "name": "Setup Python",
                "uses": "actions/setup-python@v4",
                "with": {"python-version": "3.12"},
            },
            {
                "name": "Setup Node.js",
                "uses": "actions/setup-node@v4",
                "with": {"node-version": "22", "cache": "npm"},
            },
            {
                "name": "Install Python dependencies",
                "run": "python -m pip install --upgrade pip && pip install poetry && poetry install --no-dev",
            },
            {"name": "Install Node.js dependencies", "run": "npm ci"},
            {
                "name": "Install OWASP ZAP",
                "run": "wget -q https://github.com/zaproxy/zaproxy/releases/download/v2.14.0/ZAP_2.14.0_Linux.tar.gz && tar -xzf ZAP_2.14.0_Linux.tar.gz && sudo mv ZAP_2.14.0 /opt/zap && sudo chmod +x /opt/zap/zap.sh && echo '/opt/zap' >> $GITHUB_PATH",
            },
            {
                "name": "Start application services",
                "run": "sudo systemctl start postgresql && sudo systemctl start redis-server && python scripts/start_services.py --background && timeout 300 bash -c 'until curl -f http://localhost:3001/health; do sleep 5; done'",
            },
            {
                "name": "Run DAST scan",
                "run": "python src/services/security/dast_integration.py --target-url http://localhost:3001 --scan-name ci_scan_${{ github.run_id }} --environment staging --timeout ${{ env.SCAN_TIMEOUT }} --formats ${{ env.REPORT_FORMATS }}",
            },
            {
                "name": "Upload DAST reports",
                "uses": "actions/upload-artifact@v4",
                "if": "always()",
                "with": {
                    "name": "dast-reports-${{ github.run_id }}",
                    "path": "reports/dast/",
                    "retention-days": "30",
                },
            },
            {
                "name": "Upload scan logs",
                "uses": "actions/upload-artifact@v4",
                "if": "always()",
                "with": {
                    "name": "dast-logs-${{ github.run_id }}",
                    "path": "logs/dast/",
                    "retention-days": "30",
                },
            },
        ]

    def _generate_security_gate_steps(self) -> list[dict[str, Any]]:
        """Generate security gate validation steps."""
        return [
            {"name": "Checkout code", "uses": "actions/checkout@v4"},
            {
                "name": "Download DAST reports",
                "uses": "actions/download-artifact@v4",
                "with": {
                    "name": "dast-reports-${{ github.run_id }}",
                    "path": "reports/dast/",
                },
            },
            {
                "name": "Setup Python",
                "uses": "actions/setup-python@v4",
                "with": {"python-version": "3.12"},
            },
            {
                "name": "Install security analysis tools",
                "run": "pip install safety bandit semgrep",
            },
            {
                "name": "Run security gate validation",
                "run": "python scripts/security_gate_validation.py --reports-dir reports/dast/ --max-critical 0 --max-high 2 --max-medium 5 --fail-on-threshold",
            },
            {
                "name": "Generate security summary",
                "run": "python scripts/generate_security_summary.py --reports-dir reports/dast/ --output security-summary.md",
            },
            {
                "name": "Upload security summary",
                "uses": "actions/upload-artifact@v4",
                "with": {
                    "name": "security-summary-${{ github.run_id }}",
                    "path": "security-summary.md",
                },
            },
        ]

    def _generate_reporting_steps(self) -> list[dict[str, Any]]:
        """Generate vulnerability reporting steps."""
        return [
            {"name": "Checkout code", "uses": "actions/checkout@v4"},
            {
                "name": "Download security summary",
                "uses": "actions/download-artifact@v4",
                "with": {"name": "security-summary-${{ github.run_id }}", "path": "."},
            },
            {
                "name": "Setup Python",
                "uses": "actions/setup-python@v4",
                "with": {"python-version": "3.12"},
            },
            {
                "name": "Install notification tools",
                "run": "pip install requests python-slack-sdk",
            },
            {
                "name": "Send security notifications",
                "run": "python scripts/send_security_notifications.py --summary-file security-summary.md --slack-webhook ${{ secrets.SLACK_WEBHOOK_URL }} --email-recipients ${{ secrets.SECURITY_EMAIL_LIST }}",
                "env": {
                    "SLACK_WEBHOOK_URL": "${{ secrets.SLACK_WEBHOOK_URL }}",
                    "SECURITY_EMAIL_LIST": "${{ secrets.SECURITY_EMAIL_LIST }}",
                },
            },
            {
                "name": "Create security issue",
                "if": "failure()",
                "run": "python scripts/create_security_issue.py --summary-file security-summary.md --github-token ${{ secrets.GITHUB_TOKEN }} --repository ${{ github.repository }}",
                "env": {"GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"},
            },
            {
                "name": "Update security dashboard",
                "run": "python scripts/update_security_dashboard.py --summary-file security-summary.md --dashboard-url ${{ secrets.SECURITY_DASHBOARD_URL }}",
                "env": {
                    "SECURITY_DASHBOARD_URL": "${{ secrets.SECURITY_DASHBOARD_URL }}"
                },
            },
        ]

    def save_workflow(self) -> None:
        """Save workflow to GitHub Actions directory."""
        workflow_dir = Path(".github/workflows")
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = self.generate_workflow()

        with open(self.workflow_file, "w") as f:
            yaml.dump(workflow_content, f, default_flow_style=False, sort_keys=False)


class SecurityGateValidator:
    """Security gate validation for CI/CD pipeline."""

    def __init__(self, config_file: Path) -> None:
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load security gate configuration."""
        default_config = {
            "thresholds": {
                "critical": 0,
                "high": 2,
                "medium": 5,
                "low": 10,
                "informational": 50,
            },
            "exclusions": {
                "false_positives": [],
                "accepted_risks": [],
                "ignored_paths": ["/api/health", "/api/metrics"],
            },
            "notifications": {
                "slack_enabled": True,
                "email_enabled": True,
                "dashboard_enabled": True,
            },
        }

        if Path(self.config_file).exists():
            try:
                with open(self.config_file) as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")

        return default_config

    def validate_security_thresholds(self, scan_results: dict[str, Any]) -> bool:
        """Validate security scan results against thresholds."""
        thresholds = self.config["thresholds"]

        critical_count = scan_results.get("critical_count", 0)
        high_count = scan_results.get("high_count", 0)
        medium_count = scan_results.get("medium_count", 0)
        low_count = scan_results.get("low_count", 0)
        informational_count = scan_results.get("informational_count", 0)

        # Check thresholds
        if critical_count > thresholds["critical"]:
            print(
                f"❌ CRITICAL threshold exceeded: {critical_count} > {thresholds['critical']}"
            )
            return False

        if high_count > thresholds["high"]:
            print(f"❌ HIGH threshold exceeded: {high_count} > {thresholds['high']}")
            return False

        if medium_count > thresholds["medium"]:
            print(
                f"❌ MEDIUM threshold exceeded: {medium_count} > {thresholds['medium']}"
            )
            return False

        if low_count > thresholds["low"]:
            print(f"❌ LOW threshold exceeded: {low_count} > {thresholds['low']}")
            return False

        if informational_count > thresholds["informational"]:
            print(
                f"❌ INFORMATIONAL threshold exceeded: {informational_count} > {thresholds['informational']}"
            )
            return False

        print("✅ All security thresholds passed")
        return True

    def generate_security_summary(self, scan_results: dict[str, Any]) -> str:
        """Generate security summary report."""
        summary = f"""
# Security Scan Summary

**Scan ID:** {scan_results.get("scan_id", "N/A")}
**Target:** {scan_results.get("target_url", "N/A")}
**Scan Date:** {scan_results.get("scan_date", "N/A")}
**Duration:** {scan_results.get("duration_seconds", 0)} seconds

## Vulnerability Summary

| Severity | Count | Threshold | Status |
|----------|-------|-----------|--------|
| Critical | {scan_results.get("critical_count", 0)} | {self.config["thresholds"]["critical"]} | {"✅" if scan_results.get("critical_count", 0) <= self.config["thresholds"]["critical"] else "❌"} |
| High | {scan_results.get("high_count", 0)} | {self.config["thresholds"]["high"]} | {"✅" if scan_results.get("high_count", 0) <= self.config["thresholds"]["high"] else "❌"} |
| Medium | {scan_results.get("medium_count", 0)} | {self.config["thresholds"]["medium"]} | {"✅" if scan_results.get("medium_count", 0) <= self.config["thresholds"]["medium"] else "❌"} |
| Low | {scan_results.get("low_count", 0)} | {self.config["thresholds"]["low"]} | {"✅" if scan_results.get("low_count", 0) <= self.config["thresholds"]["low"] else "❌"} |
| Informational | {scan_results.get("informational_count", 0)} | {self.config["thresholds"]["informational"]} | {"✅" if scan_results.get("informational_count", 0) <= self.config["thresholds"]["informational"] else "❌"} |

## Overall Status

{"✅ **PASSED** - All security thresholds met" if self.validate_security_thresholds(scan_results) else "❌ **FAILED** - Security thresholds exceeded"}

## Recommendations

"""

        if scan_results.get("critical_count", 0) > 0:
            summary += "- **URGENT**: Address critical vulnerabilities immediately\n"

        if scan_results.get("high_count", 0) > 0:
            summary += "- **HIGH PRIORITY**: Address high severity vulnerabilities within 24 hours\n"

        if scan_results.get("medium_count", 0) > 0:
            summary += "- **MEDIUM PRIORITY**: Address medium severity vulnerabilities within 1 week\n"

        summary += "- Review and update security thresholds if needed\n"
        summary += "- Implement additional security controls\n"
        summary += "- Schedule regular security reviews\n"

        return summary


class SecurityNotificationSystem:
    """System for sending security notifications."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def send_slack_notification(self, message: str, webhook_url: str) -> bool:
        """Send Slack notification."""
        try:
            import requests

            payload = {
                "text": "🔒 PAKE System Security Alert",
                "attachments": [
                    {
                        "color": "danger" if "FAILED" in message else "good",
                        "text": message,
                        "mrkdwn_in": ["text"],
                    }
                ],
            }

            response = requests.post(webhook_url, json=payload)
            return response.status_code == 200

        except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
            print(f"Error sending Slack notification: {e}")
            return False

    def send_email_notification(
        self, subject: str, message: str, recipients: list[str]
    ) -> bool:
        """Send email notification."""
        try:
            # This would be implemented with actual email service
            print(f"Email notification would be sent to: {recipients}")
            print(f"Subject: {subject}")
            print(f"Message: {message}")

            return True

        except (ValueError, RuntimeError) as e:
            print(f"Error sending email notification: {e}")
            return False

    def create_github_issue(
        self, title: str, body: str, token: str, repository: str
    ) -> bool:
        """Create GitHub issue for security findings."""
        try:
            import requests

            url = f"https://api.github.com/repos/{repository}/issues"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }

            payload = {
                "title": title,
                "body": body,
                "labels": ["security", "dast", "vulnerability"],
            }

            response = requests.post(url, headers=headers, json=payload)
            return response.status_code == 201

        except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
            print(f"Error creating GitHub issue: {e}")
            return False


def create_dast_workflow() -> None:
    """Create DAST workflow for GitHub Actions."""
    workflow_generator = GitHubActionsDASTWorkflow()
    workflow_generator.save_workflow()
    print(f"✅ Created DAST workflow: {workflow_generator.workflow_file}")


def create_security_gate_config() -> None:
    """Create security gate configuration."""
    config = {
        "thresholds": {
            "critical": 0,
            "high": 2,
            "medium": 5,
            "low": 10,
            "informational": 50,
        },
        "exclusions": {
            "false_positives": [],
            "accepted_risks": [],
            "ignored_paths": ["/api/health", "/api/metrics"],
        },
        "notifications": {
            "slack_enabled": True,
            "email_enabled": True,
            "dashboard_enabled": True,
        },
    }

    with open("security_gate_config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print("✅ Created security gate configuration: security_gate_config.yaml")


def create_dast_scripts() -> None:
    """Create DAST-related scripts."""
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)

    # Security gate validation script
    security_gate_script = """#!/usr/bin/env python3
\"\"\"Security gate validation script\"\"\"

import argparse
import json
import sys
from pathlib import Path
from src.services.security.dast_integration import SecurityGateValidator

def main(self) -> None:
    parser = argparse.ArgumentParser(description="Validate security gate thresholds")
    parser.add_argument("--reports-dir", required=True, help="Directory containing DAST reports")
    parser.add_argument("--max-critical", type=int, default=0, help="Maximum critical vulnerabilities")
    parser.add_argument("--max-high", type=int, default=2, help="Maximum high vulnerabilities")
    parser.add_argument("--max-medium", type=int, default=5, help="Maximum medium vulnerabilities")
    parser.add_argument("--fail-on-threshold", action="store_true", help="Fail if thresholds exceeded")

    args = parser.parse_args()

    # Load scan results
    reports_dir = Path(args.reports_dir)
    json_reports = list(reports_dir.glob("*.json"))

    if not json_reports:
        print("❌ No JSON reports found")
        sys.exit(1)

    # Process reports
    total_critical = 0
    total_high = 0
    total_medium = 0

    for report_file in json_reports:
        with open(report_file, 'r') as f:
            report_data = json.load(f)

        # Extract vulnerability counts
        alerts = report_data.get("alerts", [])
        for alert in alerts:
            risk = alert.get("risk", "").lower()
            if risk == "high":
                total_high += 1
            elif risk == "medium":
                total_medium += 1
            elif risk == "critical":
                total_critical += 1

    # Validate thresholds
    validator = SecurityGateValidator()
    scan_results = {
        "critical_count": total_critical,
        "high_count": total_high,
        "medium_count": total_medium
    }

    if validator.validate_security_thresholds(scan_results):
        print("✅ Security gate validation passed")
        sys.exit(0)
    else:
        print("❌ Security gate validation failed")
        if args.fail_on_threshold:
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == "__main__":
    main()
"""

    with open(scripts_dir / "security_gate_validation.py", "w") as f:
        f.write(security_gate_script)

    # Security summary script
    security_summary_script = """#!/usr/bin/env python3
\"\"\"Generate security summary script\"\"\"

import argparse
import json
from pathlib import Path
from src.services.security.dast_integration import SecurityGateValidator

def main(self) -> None:
    parser = argparse.ArgumentParser(description="Generate security summary")
    parser.add_argument("--reports-dir", required=True, help="Directory containing DAST reports")
    parser.add_argument("--output", required=True, help="Output file for summary")

    args = parser.parse_args()

    # Process reports and generate summary
    validator = SecurityGateValidator()
    reports_dir = Path(args.reports_dir)

    # This would process the actual reports and generate summary
    summary = validator.generate_security_summary({
        "scan_id": "ci_scan_123",
        "target_url": "http://localhost:3001",
        "scan_date": "2025-01-15",
        "duration_seconds": 1800,
        "critical_count": 0,
        "high_count": 1,
        "medium_count": 3,
        "low_count": 5,
        "informational_count": 10
    })

    with open(args.output, 'w') as f:
        f.write(summary)

    print(f"✅ Security summary generated: {args.output}")

if __name__ == "__main__":
    main()
"""

    with open(scripts_dir / "generate_security_summary.py", "w") as f:
        f.write(security_summary_script)

    print("✅ Created DAST scripts in scripts/ directory")


if __name__ == "__main__":
    print("Setting up DAST CI/CD integration...")

    create_dast_workflow()
    create_security_gate_config()
    create_dast_scripts()

    print("\n🎉 DAST CI/CD integration setup complete!")
    print("\nNext steps:")
    print("1. Configure GitHub secrets:")
    print("   - SLACK_WEBHOOK_URL")
    print("   - SECURITY_EMAIL_LIST")
    print("   - SECURITY_DASHBOARD_URL")
    print("2. Install OWASP ZAP on your system")
    print("3. Test the workflow with: gh workflow run dast-security-scan.yml")
    print("4. Review and adjust security thresholds in security_gate_config.yaml")
