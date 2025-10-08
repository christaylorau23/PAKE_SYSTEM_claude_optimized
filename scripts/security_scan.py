#!/usr/bin/env python3
"""
Comprehensive Security Scanning Script
Following The Vanguard Protocol - Phase 6: Advanced Quality Fortification
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List


class SecurityScanner:
    """Comprehensive security scanner for the PAKE System"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = {}

    def run_ruff_security_scan(self) -> dict[str, Any]:
        """Run Ruff security checks"""
        print("🔍 Running Ruff security scan...")
        try:
            result = subprocess.run(
                ["ruff", "check", ".", "--select=S", "--output-format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            errors = json.loads(result.stdout) if result.stdout else []
            security_issues = [e for e in errors if e.get("code", "").startswith("S")]

            return {
                "tool": "ruff",
                "total_issues": len(security_issues),
                "issues": security_issues,
                "status": "success" if result.returncode == 0 else "warning",
            }
        except (ValueError, RuntimeError) as e:
            return {"tool": "ruff", "error": str(e), "status": "error"}

    def run_bandit_scan(self) -> dict[str, Any]:
        """Run Bandit security linter"""
        print("🛡️  Running Bandit security scan...")
        try:
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            bandit_results = json.loads(result.stdout) if result.stdout else {}

            return {
                "tool": "bandit",
                "total_issues": bandit_results.get("results", []),
                "high_severity": len(
                    [
                        r
                        for r in bandit_results.get("results", [])
                        if r.get("issue_severity") == "HIGH"
                    ]
                ),
                "medium_severity": len(
                    [
                        r
                        for r in bandit_results.get("results", [])
                        if r.get("issue_severity") == "MEDIUM"
                    ]
                ),
                "low_severity": len(
                    [
                        r
                        for r in bandit_results.get("results", [])
                        if r.get("issue_severity") == "LOW"
                    ]
                ),
                "status": "success" if result.returncode == 0 else "warning",
            }
        except (ValueError, RuntimeError) as e:
            return {"tool": "bandit", "error": str(e), "status": "error"}

    def run_safety_check(self) -> dict[str, Any]:
        """Run Safety dependency vulnerability check"""
        print("🔒 Running Safety vulnerability check...")
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            safety_results = json.loads(result.stdout) if result.stdout else []

            return {
                "tool": "safety",
                "vulnerabilities": safety_results,
                "total_vulnerabilities": len(safety_results),
                "status": "success" if result.returncode == 0 else "warning",
            }
        except (ValueError, RuntimeError) as e:
            return {"tool": "safety", "error": str(e), "status": "error"}

    def run_pip_audit(self) -> dict[str, Any]:
        """Run pip-audit for dependency vulnerabilities"""
        print("📦 Running pip-audit...")
        try:
            result = subprocess.run(
                ["pip-audit", "--format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            audit_results = json.loads(result.stdout) if result.stdout else {}

            return {
                "tool": "pip-audit",
                "vulnerabilities": audit_results.get("vulnerabilities", []),
                "total_vulnerabilities": len(audit_results.get("vulnerabilities", [])),
                "status": "success" if result.returncode == 0 else "warning",
            }
        except (ValueError, RuntimeError) as e:
            return {"tool": "pip-audit", "error": str(e), "status": "error"}

    def run_secret_scan(self) -> dict[str, Any]:
        """Run detect-secrets for secret scanning"""
        print("🔐 Running secret scan...")
        try:
            result = subprocess.run(
                [
                    "detect-secrets",
                    "scan",
                    "--all-files",
                    "--baseline",
                    ".secrets.baseline",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            return {
                "tool": "detect-secrets",
                "status": "success" if result.returncode == 0 else "warning",
                "output": result.stdout,
            }
        except (ValueError, RuntimeError) as e:
            return {"tool": "detect-secrets", "error": str(e), "status": "error"}

    def run_comprehensive_scan(self) -> dict[str, Any]:
        """Run comprehensive security scan"""
        print("🚀 Starting comprehensive security scan...")

        scan_results = {
            "ruff_security": self.run_ruff_security_scan(),
            "bandit": self.run_bandit_scan(),
            "safety": self.run_safety_check(),
            "pip_audit": self.run_pip_audit(),
            "secret_scan": self.run_secret_scan(),
        }

        # Calculate overall security score
        total_issues = 0
        critical_issues = 0

        for _tool, result in scan_results.items():
            if result.get("status") == "error":
                continue

            if "total_issues" in result:
                total_issues += result["total_issues"]
            if "total_vulnerabilities" in result:
                total_issues += result["total_vulnerabilities"]
            if "high_severity" in result:
                critical_issues += result["high_severity"]

        scan_results["summary"] = {
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "security_score": max(0, 100 - (total_issues * 2) - (critical_issues * 10)),
        }

        return scan_results

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate comprehensive security report"""
        report = []
        report.append("# Comprehensive Security Scan Report")
        report.append("")
        report.append(
            "**Following The Vanguard Protocol - Phase 6: Advanced Quality Fortification**"
        )
        report.append("")

        summary = results.get("summary", {})
        report.append(f"**Security Score**: {summary.get('security_score', 0)}/100")
        report.append(f"**Total Issues**: {summary.get('total_issues', 0)}")
        report.append(f"**Critical Issues**: {summary.get('critical_issues', 0)}")
        report.append("")

        for tool, result in results.items():
            if tool == "summary":
                continue

            report.append(f"## {tool.replace('_', ' ').title()}")
            report.append("")

            if result.get("status") == "error":
                report.append(f"❌ **Error**: {result.get('error', 'Unknown error')}")
            else:
                if "total_issues" in result:
                    report.append(f"**Issues Found**: {result['total_issues']}")
                if "total_vulnerabilities" in result:
                    report.append(
                        f"**Vulnerabilities**: {result['total_vulnerabilities']}"
                    )
                if "high_severity" in result:
                    report.append(f"**High Severity**: {result['high_severity']}")
                if "medium_severity" in result:
                    report.append(f"**Medium Severity**: {result['medium_severity']}")
                if "low_severity" in result:
                    report.append(f"**Low Severity**: {result['low_severity']}")

            report.append("")

        return "\n".join(report)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Comprehensive Security Scanner")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    scanner = SecurityScanner(args.project_root)
    results = scanner.run_comprehensive_scan()

    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = scanner.generate_report(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"📄 Report written to: {args.output}")
    else:
        print(output)

    # Exit with error code if critical issues found
    summary = results.get("summary", {})
    if summary.get("critical_issues", 0) > 0:
        print("🚨 Critical security issues found!")
        sys.exit(1)
    else:
        print("✅ Security scan completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
