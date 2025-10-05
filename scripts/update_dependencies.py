#!/usr/bin/env python3
"""
PAKE System Dependency Update Script
Addresses security vulnerabilities and updates deprecated packages
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DependencyUpdater:
    def __init__(self) -> None:
        self.project_root = project_root
        self.security_updates = []
        self.deprecated_updates = []

    def run_command(self, command: str, cwd: Path = None) -> tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                command.split(),
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error("Command failed: %s", command)
            logger.error("Error: %s", e.stderr)
            return False, e.stderr

    def update_python_dependencies(self) -> bool:
        """Update Python dependencies using Poetry"""
        logger.info("Updating Python dependencies...")

        # Update specific vulnerable packages
        vulnerable_packages = {
            "black": "^24.3.0",  # Fix PYSEC-2024-48
            "django": "^5.2.7",  # Fix GHSA vulnerabilities
            "gunicorn": "^22.0.0",  # Fix GHSA vulnerabilities
            "starlette": "^0.47.2",  # Fix GHSA vulnerabilities
            "strawberry-graphql": "^0.257.0",  # Fix PYSEC-2024-171
            "urllib3": "^2.5.0",  # Fix GHSA-pq67-6m6q-mj2v
        }

        for package, version in vulnerable_packages.items():
            logger.info("Updating %s to %s", package, version)
            success, output = self.run_command(f"poetry add {package}@{version}")
            if not success:
                logger.warning("Failed to update %s: %s", package, output)

        # Update all dependencies
        success, output = self.run_command("poetry update")
        if success:
            logger.info("Python dependencies updated successfully")
            return True
        logger.error("Failed to update Python dependencies: %s", output)
        return False

    def update_node_dependencies(self) -> bool:
        """Update Node.js dependencies using Yarn"""
        logger.info("Updating Node.js dependencies...")

        # Update specific vulnerable packages
        vulnerable_packages = {
            "ws": "^8.17.1",  # Fix DoS vulnerability
            "semver": "^5.7.2",  # Fix ReDoS vulnerability
            "tar-fs": "^2.1.4",  # Fix path traversal vulnerabilities
            "xlsx": "^0.18.5",  # Fix prototype pollution and ReDoS
        }

        for package, version in vulnerable_packages.items():
            logger.info("Updating %s to %s", package, version)
            success, output = self.run_command(f"yarn add {package}@{version}")
            if not success:
                logger.warning("Failed to update %s: %s", package, output)

        # Update deprecated packages
        deprecated_updates = {
            "eslint": "^9.36.0",  # Update from 8.x
            "supertest": "^7.1.3",  # Update from 6.x
            "rimraf": "^5.0.5",  # Update from 3.x
            "glob": "^10.3.10",  # Update from 7.x
            "multer": "^2.0.0",  # Update from 1.x
            "puppeteer": "^24.15.0",  # Update from 22.x
        }

        for package, version in deprecated_updates.items():
            logger.info("Updating deprecated %s to %s", package, version)
            success, output = self.run_command(f"yarn add {package}@{version}")
            if not success:
                logger.warning("Failed to update %s: %s", package, output)

        # Update all dependencies
        success, output = self.run_command("yarn upgrade")
        if success:
            logger.info("Node.js dependencies updated successfully")
            return True
        logger.error("Failed to update Node.js dependencies: %s", output)
        return False

    def run_security_audits(self) -> dict[str, list[str]]:
        """Run security audits and return vulnerabilities"""
        vulnerabilities = {"python": [], "node": []}

        # Python security audit
        logger.info("Running Python security audit...")
        success, output = self.run_command("poetry run pip-audit --format=json")
        if success:
            try:
                audit_data = json.loads(output)
                for vuln in audit_data.get("vulnerabilities", []):
                    vulnerabilities["python"].append(
                        f"{vuln['name']} {vuln['version']}: {vuln['id']}"
                    )
            except json.JSONDecodeError:
                logger.warning("Could not parse pip-audit JSON output")
        else:
            logger.warning("Python security audit failed: %s", output)

        # Node.js security audit
        logger.info("Running Node.js security audit...")
        success, output = self.run_command("yarn audit --json")
        if success:
            try:
                for line in output.strip().split("\n"):
                    if line:
                        audit_data = json.loads(line)
                        if audit_data.get("type") == "auditAdvisory":
                            advisory = audit_data.get("data", {}).get("advisory", {})
                            vulnerabilities["node"].append(
                                f"{advisory.get('module_name')}: {advisory.get('title')}"
                            )
            except json.JSONDecodeError:
                logger.warning("Could not parse yarn audit JSON output")
        else:
            logger.warning("Node.js security audit failed: %s", output)

        return vulnerabilities

    def generate_update_report(self, vulnerabilities: dict[str, list[str]]) -> str:
        """Generate a comprehensive update report"""
        report = []
        report.append("# PAKE System Dependency Update Report")
        report.append("=" * 50)
        report.append("")

        # Security vulnerabilities
        report.append("## Security Vulnerabilities Found")
        report.append("")

        if vulnerabilities["python"]:
            report.append("### Python Vulnerabilities")
            for vuln in vulnerabilities["python"]:
                report.append(f"- {vuln}")
            report.append("")

        if vulnerabilities["node"]:
            report.append("### Node.js Vulnerabilities")
            for vuln in vulnerabilities["node"]:
                report.append(f"- {vuln}")
            report.append("")

        # Update recommendations
        report.append("## Update Recommendations")
        report.append("")
        report.append("### High Priority (Security)")
        report.append("- Update all packages with known security vulnerabilities")
        report.append("- Run security audits after each update")
        report.append("- Configure Dependabot for automated security updates")
        report.append("")

        report.append("### Medium Priority (Deprecated)")
        report.append("- Update ESLint from 8.x to 9.x")
        report.append("- Update supertest from 6.x to 7.x")
        report.append("- Update rimraf from 3.x to 5.x")
        report.append("- Update glob from 7.x to 10.x")
        report.append("- Update multer from 1.x to 2.x")
        report.append("- Update puppeteer from 22.x to 24.x")
        report.append("")

        report.append("### Low Priority (Maintenance)")
        report.append("- Regular dependency updates via Dependabot")
        report.append("- Monitor for new security advisories")
        report.append("- Update development dependencies quarterly")
        report.append("")

        return "\n".join(report)

    def run_full_update(self) -> bool:
        """Run complete dependency update process"""
        logger.info("Starting PAKE System dependency update process...")

        # Run security audits first
        vulnerabilities = self.run_security_audits()

        # Update Python dependencies
        python_success = self.update_python_dependencies()

        # Update Node.js dependencies
        node_success = self.update_node_dependencies()

        # Generate report
        report = self.generate_update_report(vulnerabilities)

        # Save report
        report_path = self.project_root / "DEPENDENCY_UPDATE_REPORT.md"
        with open(report_path, "w") as f:
            f.write(report)

        logger.info("Update report saved to %s", report_path)

        # Run final security audit
        logger.info("Running final security audit...")
        final_vulnerabilities = self.run_security_audits()

        # Check if vulnerabilities were resolved
        python_resolved = len(final_vulnerabilities["python"]) < len(
            vulnerabilities["python"]
        )
        node_resolved = len(final_vulnerabilities["node"]) < len(
            vulnerabilities["node"]
        )

        if python_resolved and node_resolved:
            logger.info("✅ Security vulnerabilities successfully resolved!")
        else:
            logger.warning("⚠️ Some security vulnerabilities may still exist")

        return python_success and node_success


def main(self) -> None:
    """Main entry point"""
    project_root = Path(__file__).parent
    updater = DependencyUpdater(project_root)

    try:
        success = updater.run_full_update()
        if success:
            logger.info("🎉 Dependency update process completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Dependency update process failed!")
            sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
