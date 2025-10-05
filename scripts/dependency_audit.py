#!/usr/bin/env python3
"""
PAKE System - Dependency Audit Integration Script
Integrates dependency auditing with Poetry lock file verification
"""

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp


class DependencyAuditor:
    """Comprehensive dependency auditing with Poetry integration."""

    def __init__(self) -> None:
        self.project_root = project_root
        self.lock_file = project_root / "poetry.lock"
        self.pyproject_file = project_root / "pyproject.toml"
        self.audit_results = {}

    def audit_poetry_lock_file(self) -> tuple[bool, dict]:
        """Audit Poetry lock file for vulnerabilities."""
        try:
            # Run pip-audit on the lock file
            result = subprocess.run(
                ["poetry", "run", "pip-audit", "--format=json", "--output=-"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                # No vulnerabilities found
                return True, {
                    "vulnerabilities": [],
                    "summary": "No vulnerabilities found",
                }
            # Parse vulnerabilities
            try:
                vulnerabilities = json.loads(result.stdout)
                return False, vulnerabilities
            except json.JSONDecodeError:
                return False, {
                    "error": "Failed to parse pip-audit output",
                    "raw_output": result.stdout,
                }

        except subprocess.TimeoutExpired:
            return False, {"error": "pip-audit timed out"}
        except Exception as e:
            return False, {"error": f"Error running pip-audit: {e}"}

    def audit_with_safety(self) -> tuple[bool, dict]:
        """Audit dependencies using Safety."""
        try:
            result = subprocess.run(
                ["poetry", "run", "safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return True, {
                    "vulnerabilities": [],
                    "summary": "No vulnerabilities found",
                }
            try:
                vulnerabilities = json.loads(result.stdout)
                return False, vulnerabilities
            except json.JSONDecodeError:
                return False, {
                    "error": "Failed to parse safety output",
                    "raw_output": result.stdout,
                }

        except subprocess.TimeoutExpired:
            return False, {"error": "safety check timed out"}
        except Exception as e:
            return False, {"error": f"Error running safety: {e}"}

    def audit_with_bandit(self) -> tuple[bool, dict]:
        """Audit code for security issues using Bandit."""
        try:
            result = subprocess.run(
                ["poetry", "run", "bandit", "-r", "src/", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Bandit returns 0 for no issues, 1 for issues found
            issues = []
            if result.returncode == 1:
                try:
                    issues = json.loads(result.stdout)
                except json.JSONDecodeError:
                    issues = [
                        {
                            "error": "Failed to parse bandit output",
                            "raw_output": result.stdout,
                        }
                    ]

            return len(issues) == 0, {
                "issues": issues,
                "summary": f"{len(issues)} security issues found",
            }

        except subprocess.TimeoutExpired:
            return False, {"error": "bandit scan timed out"}
        except Exception as e:
            return False, {"error": f"Error running bandit: {e}"}

    async def audit_dependency_licenses(self) -> tuple[bool, dict]:
        """Audit dependency licenses for compliance."""
        try:
            # Get installed packages
            result = subprocess.run(
                ["poetry", "show", "--only=main"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return False, {"error": "Failed to get installed packages"}

            packages = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    package_name = line.split()[0]
                    packages.append(package_name)

            # Check licenses (simplified approach)
            license_issues = []
            for package in packages:
                # This is a simplified check - in production, you'd use a proper license checker
                if any(
                    restricted in package.lower()
                    for restricted in ["gpl", "agpl", "copyleft"]
                ):
                    license_issues.append(
                        {
                            "package": package,
                            "issue": "Potentially restrictive license detected",
                            "severity": "medium",
                        }
                    )

            return len(license_issues) == 0, {
                "license_issues": license_issues,
                "packages_checked": len(packages),
                "summary": f"{len(license_issues)} license issues found",
            }

        except Exception as e:
            return False, {"error": f"Error checking licenses: {e}"}

    def audit_dependency_freshness(self) -> tuple[bool, dict]:
        """Audit dependency freshness and outdated packages."""
        try:
            # Check for outdated packages
            result = subprocess.run(
                ["poetry", "show", "--outdated"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            outdated_packages = []
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            outdated_packages.append(
                                {
                                    "package": parts[0],
                                    "current": parts[1],
                                    "latest": parts[2],
                                }
                            )

            # Determine severity based on age and criticality
            critical_outdated = []
            for pkg in outdated_packages:
                # This is a simplified check - in production, you'd use proper version comparison
                if any(
                    critical in pkg["package"].lower()
                    for critical in ["django", "flask", "fastapi", "requests"]
                ):
                    critical_outdated.append(pkg)

            return len(critical_outdated) == 0, {
                "outdated_packages": outdated_packages,
                "critical_outdated": critical_outdated,
                "summary": f"{len(outdated_packages)} outdated packages, {len(critical_outdated)} critical",
            }

        except subprocess.TimeoutExpired:
            return False, {"error": "Dependency freshness check timed out"}
        except Exception as e:
            return False, {"error": f"Error checking dependency freshness: {e}"}

    def validate_poetry_lock_consistency(self) -> tuple[bool, dict]:
        """Validate Poetry lock file consistency."""
        try:
            # Run poetry check
            result = subprocess.run(
                ["poetry", "check"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, {"summary": "Poetry lock file is consistent"}
            return False, {
                "error": "Poetry lock file inconsistency",
                "details": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return False, {"error": "Poetry consistency check timed out"}
        except Exception as e:
            return False, {"error": f"Error checking Poetry consistency: {e}"}

    async def run_comprehensive_audit(self) -> dict:
        """Run comprehensive dependency audit."""
        print("🔍 Running comprehensive dependency audit...")

        audit_results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "project_root": str(self.project_root),
            "audits": {},
        }

        # Run all audits
        audits = [
            ("poetry_lock_vulnerabilities", self.audit_poetry_lock_file()),
            ("safety_check", self.audit_with_safety()),
            ("bandit_security", self.audit_with_bandit()),
            ("dependency_licenses", await self.audit_dependency_licenses()),
            ("dependency_freshness", self.audit_dependency_freshness()),
            ("poetry_consistency", self.validate_poetry_lock_consistency()),
        ]

        overall_success = True

        for audit_name, (success, result) in audits:
            audit_results["audits"][audit_name] = {"success": success, "result": result}

            if not success:
                overall_success = False

            status = "✅" if success else "❌"
            print(f"{status} {audit_name.replace('_', ' ').title()}")

        audit_results["overall_success"] = overall_success

        return audit_results

    def generate_audit_report(self, audit_results: dict) -> str:
        """Generate human-readable audit report."""
        report = []
        report.append("🔍 PAKE System Dependency Audit Report")
        report.append("=" * 50)
        report.append(f"Timestamp: {audit_results['timestamp']}")
        report.append(f"Project Root: {audit_results['project_root']}")
        report.append("")

        for audit_name, audit_data in audit_results["audits"].items():
            success = audit_data["success"]
            result = audit_data["result"]

            status = "✅" if success else "❌"
            report.append(f"{status} {audit_name.replace('_', ' ').title()}")

            if "summary" in result:
                report.append(f"   Summary: {result['summary']}")

            if not success and "error" in result:
                report.append(f"   Error: {result['error']}")

            if not success and "vulnerabilities" in result:
                vulnerabilities = result["vulnerabilities"]
                if vulnerabilities:
                    report.append(f"   Vulnerabilities: {len(vulnerabilities)} found")
                    for vuln in vulnerabilities[:3]:  # Show first 3
                        if isinstance(vuln, dict):
                            report.append(
                                f"     - {vuln.get('package', 'Unknown')}: {vuln.get('vulnerability', 'Unknown issue')}"
                            )

            report.append("")

        report.append("=" * 50)
        if audit_results["overall_success"]:
            report.append("🎉 All audits passed! Dependencies are secure.")
        else:
            report.append("⚠️  Some audits failed. Please address the issues above.")

        return "\n".join(report)


async def main(self) -> None:
    """Main entry point for the dependency audit script."""
    parser = argparse.ArgumentParser(
        description="Comprehensive dependency audit with Poetry integration"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results in JSON format"
    )
    parser.add_argument("--output-file", type=Path, help="Save results to file")
    parser.add_argument(
        "--exit-on-failure",
        action="store_true",
        help="Exit with non-zero code on audit failure",
    )

    args = parser.parse_args()

    auditor = DependencyAuditor(args.project_root)
    audit_results = await auditor.run_comprehensive_audit()

    if args.json_output:
        # JSON output for CI integration
        output = json.dumps(audit_results, indent=2)
    else:
        # Human-readable output
        output = auditor.generate_audit_report(audit_results)

    print(output)

    # Save to file if requested
    if args.output_file:
        args.output_file.write_text(output)
        print(f"\nResults saved to: {args.output_file}")

    # Exit with appropriate code
    if args.exit_on_failure and not audit_results["overall_success"]:
        sys.exit(1)
    elif audit_results["overall_success"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
