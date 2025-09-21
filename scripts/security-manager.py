#!/usr/bin/env python3
"""
PAKE System Security Manager
Automated security maintenance and vulnerability remediation
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Comprehensive security management for the PAKE System
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "nodejs_services": {},
            "python_services": {},
            "docker_images": {},
            "summary": {
                "total_vulnerabilities": 0,
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 0,
                "services_affected": 0,
            },
        }

    async def audit_nodejs_service(self, service_path: Path) -> dict[str, Any]:
        """Audit a Node.js service for vulnerabilities"""
        service_name = service_path.name
        logger.info(f"Auditing Node.js service: {service_name}")

        if not (service_path / "package.json").exists():
            logger.warning(f"No package.json found in {service_path}")
            return {"error": "No package.json found"}

        try:
            # Install dependencies if needed
            if not (service_path / "node_modules").exists():
                logger.info(f"Installing dependencies for {service_name}")
                subprocess.run(
                    ["npm", "ci", "--audit=false"],
                    cwd=service_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            # Run npm audit
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=service_path,
                capture_output=True,
                text=True,
            )

            if result.stdout:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get("metadata", {}).get(
                    "vulnerabilities",
                    {},
                )

                return {
                    "service": service_name,
                    "path": str(service_path),
                    "vulnerabilities": vulnerabilities,
                    "total": vulnerabilities.get("total", 0),
                    "critical": vulnerabilities.get("critical", 0),
                    "high": vulnerabilities.get("high", 0),
                    "moderate": vulnerabilities.get("moderate", 0),
                    "low": vulnerabilities.get("low", 0),
                    "status": "success",
                }
            return {
                "service": service_name,
                "path": str(service_path),
                "vulnerabilities": {},
                "total": 0,
                "status": "success",
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"npm audit failed for {service_name}: {e}")
            return {
                "service": service_name,
                "path": str(service_path),
                "error": str(e),
                "status": "error",
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse npm audit output for {service_name}: {e}")
            return {
                "service": service_name,
                "path": str(service_path),
                "error": f"JSON parse error: {e}",
                "status": "error",
            }

    async def audit_python_service(self, service_path: Path) -> dict[str, Any]:
        """Audit a Python service for vulnerabilities"""
        service_name = service_path.name
        logger.info(f"Auditing Python service: {service_name}")

        requirements_file = service_path / "requirements.txt"
        if not requirements_file.exists():
            logger.warning(f"No requirements.txt found in {service_path}")
            return {"error": "No requirements.txt found"}

        try:
            # Run safety check
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "safety",
                    "check",
                    "-r",
                    str(requirements_file),
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            vulnerabilities = []
            if result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    vulnerabilities = (
                        safety_data if isinstance(safety_data, list) else []
                    )
                except json.JSONDecodeError:
                    # Safety might output text instead of JSON in some cases
                    vulnerabilities = []

            return {
                "service": service_name,
                "path": str(service_path),
                "vulnerabilities": vulnerabilities,
                "total": len(vulnerabilities),
                "status": "success",
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Safety check timed out for {service_name}")
            return {
                "service": service_name,
                "path": str(service_path),
                "error": "Timeout",
                "status": "error",
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Safety check failed for {service_name}: {e}")
            return {
                "service": service_name,
                "path": str(service_path),
                "error": str(e),
                "status": "error",
            }

    async def scan_docker_images(self) -> dict[str, Any]:
        """Scan Docker images for vulnerabilities"""
        logger.info("Scanning Docker images")

        dockerfile_paths = [
            self.project_root / "services" / "voice-agents" / "Dockerfile",
            self.project_root / "mcp-servers" / "Dockerfile",
            self.project_root / "services" / "video-generation" / "Dockerfile",
        ]

        results = {}
        for dockerfile_path in dockerfile_paths:
            if dockerfile_path.exists():
                service_name = dockerfile_path.parent.name
                logger.info(f"Analyzing Dockerfile for {service_name}")

                try:
                    # Run hadolint for Dockerfile best practices
                    result = subprocess.run(
                        ["docker", "run", "--rm", "-i", "hadolint/hadolint"],
                        input=dockerfile_path.read_text(),
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    results[service_name] = {
                        "dockerfile_path": str(dockerfile_path),
                        "hadolint_output": result.stdout,
                        "hadolint_errors": result.stderr,
                        "status": (
                            "success" if result.returncode == 0 else "issues_found"
                        ),
                    }

                except subprocess.TimeoutExpired:
                    results[service_name] = {
                        "dockerfile_path": str(dockerfile_path),
                        "error": "Hadolint scan timed out",
                        "status": "error",
                    }
                except Exception as e:
                    results[service_name] = {
                        "dockerfile_path": str(dockerfile_path),
                        "error": str(e),
                        "status": "error",
                    }

        return results

    async def fix_nodejs_vulnerabilities(self, service_path: Path) -> bool:
        """Attempt to fix Node.js vulnerabilities automatically"""
        service_name = service_path.name
        logger.info(f"Attempting to fix vulnerabilities in {service_name}")

        try:
            # Try npm audit fix
            result = subprocess.run(
                ["npm", "audit", "fix", "--audit-level=moderate"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                logger.info(f"Successfully fixed vulnerabilities in {service_name}")
                return True
            logger.warning(
                f"Some vulnerabilities could not be auto-fixed in {service_name}",
            )
            return False

        except subprocess.TimeoutExpired:
            logger.error(f"npm audit fix timed out for {service_name}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"npm audit fix failed for {service_name}: {e}")
            return False

    async def generate_security_report(self) -> str:
        """Generate a comprehensive security report"""
        report = []
        report.append("# PAKE System Security Report")
        report.append(f"**Generated:** {self.results['timestamp']}")
        report.append("")

        # Summary
        summary = self.results["summary"]
        report.append("## Executive Summary")
        report.append(
            f"- **Total Vulnerabilities:** {summary['total_vulnerabilities']}",
        )
        report.append(f"- **Critical:** {summary['critical_vulnerabilities']}")
        report.append(f"- **High:** {summary['high_vulnerabilities']}")
        report.append(f"- **Services Affected:** {summary['services_affected']}")
        report.append("")

        # Node.js services
        if self.results["nodejs_services"]:
            report.append("## Node.js Services")
            for service, data in self.results["nodejs_services"].items():
                if "vulnerabilities" in data:
                    vuln = data["vulnerabilities"]
                    total = vuln.get("total", 0)
                    status = "✅ Clean" if total == 0 else f"🔴 {total} vulnerabilities"
                    report.append(f"- **{service}:** {status}")

        # Python services
        if self.results["python_services"]:
            report.append("")
            report.append("## Python Services")
            for service, data in self.results["python_services"].items():
                total = data.get("total", 0)
                status = "✅ Clean" if total == 0 else f"🔴 {total} vulnerabilities"
                report.append(f"- **{service}:** {status}")

        # Docker analysis
        if self.results["docker_images"]:
            report.append("")
            report.append("## Docker Images")
            for service, data in self.results["docker_images"].items():
                status = "✅ Clean" if data["status"] == "success" else "⚠️ Issues found"
                report.append(f"- **{service}:** {status}")

        # Recommendations
        report.append("")
        report.append("## Recommendations")
        if summary["total_vulnerabilities"] > 0:
            report.append(
                "1. **Immediate Action Required:** Address critical and high severity vulnerabilities",
            )
            report.append("2. Update dependencies to latest secure versions")
            report.append("3. Run `npm audit fix` for Node.js services")
            report.append("4. Update Python packages in requirements.txt files")
        else:
            report.append("1. Continue regular security monitoring")
            report.append("2. Keep dependencies updated")
            report.append("3. Monitor for new vulnerabilities daily")

        report.append("")
        report.append("---")
        report.append(
            "*This report was generated automatically by the PAKE Security Manager*",
        )

        return "\\n".join(report)

    async def run_full_audit(self, fix_issues: bool = False) -> dict[str, Any]:
        """Run a comprehensive security audit"""
        logger.info("Starting comprehensive security audit")

        # Find Node.js services
        nodejs_services = []
        for service_dir in [
            "frontend",
            "services/voice-agents",
            "services/video-generation",
            "services/social-media-automation",
        ]:
            service_path = self.project_root / service_dir
            if service_path.exists() and (service_path / "package.json").exists():
                nodejs_services.append(service_path)

        # Find Python services
        python_services = []
        for service_dir in ["mcp-servers", "configs", "auth-middleware"]:
            service_path = self.project_root / service_dir
            if service_path.exists() and (service_path / "requirements.txt").exists():
                python_services.append(service_path)

        # Audit Node.js services
        for service_path in nodejs_services:
            if fix_issues:
                await self.fix_nodejs_vulnerabilities(service_path)

            audit_result = await self.audit_nodejs_service(service_path)
            self.results["nodejs_services"][service_path.name] = audit_result

            if "vulnerabilities" in audit_result:
                vulns = audit_result["vulnerabilities"]
                self.results["summary"]["total_vulnerabilities"] += vulns.get(
                    "total",
                    0,
                )
                self.results["summary"]["critical_vulnerabilities"] += vulns.get(
                    "critical",
                    0,
                )
                self.results["summary"]["high_vulnerabilities"] += vulns.get("high", 0)

                if vulns.get("total", 0) > 0:
                    self.results["summary"]["services_affected"] += 1

        # Audit Python services
        for service_path in python_services:
            audit_result = await self.audit_python_service(service_path)
            self.results["python_services"][service_path.name] = audit_result

            total_vulns = audit_result.get("total", 0)
            self.results["summary"]["total_vulnerabilities"] += total_vulns

            if total_vulns > 0:
                self.results["summary"]["services_affected"] += 1

        # Scan Docker images
        self.results["docker_images"] = await self.scan_docker_images()

        # Generate report
        report = await self.generate_security_report()

        # Save results
        results_file = self.project_root / "security-audit-results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        report_file = self.project_root / "SECURITY_REPORT.md"
        with open(report_file, "w") as f:
            f.write(report)

        logger.info(f"Security audit complete. Results saved to {results_file}")
        logger.info(f"Security report saved to {report_file}")

        return self.results


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Security Manager")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix vulnerabilities",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Path to PAKE System project root",
    )

    args = parser.parse_args()

    # Verify project root
    if (
        not (args.project_root / "package.json").exists()
        and not (args.project_root / "frontend").exists()
    ):
        logger.error(f"Invalid project root: {args.project_root}")
        sys.exit(1)

    # Run security audit
    security_manager = SecurityManager(args.project_root)
    results = await security_manager.run_full_audit(fix_issues=args.fix)

    # Print summary
    print("\\n" + "=" * 50)
    print("SECURITY AUDIT SUMMARY")
    print("=" * 50)
    print(f"Total Vulnerabilities: {results['summary']['total_vulnerabilities']}")
    print(f"Critical: {results['summary']['critical_vulnerabilities']}")
    print(f"High: {results['summary']['high_vulnerabilities']}")
    print(f"Services Affected: {results['summary']['services_affected']}")
    print("=" * 50)

    # Exit with error code if vulnerabilities found
    if results["summary"]["total_vulnerabilities"] > 0:
        sys.exit(1)
    else:
        print("✅ No vulnerabilities found!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
