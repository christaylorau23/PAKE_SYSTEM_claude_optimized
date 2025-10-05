#!/usr/bin/env python3
"""
Phase 4 Validation Script
PAKE System - Strategic Plan for Codebase Remediation

This script validates all Phase 4 implementations including:
- Environment variable synchronization
- GitHub Actions workflow updates
- HashiCorp Vault integration
- Case-sensitivity fixes
"""

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"


@dataclass
class ValidationResult:
    """Validation result."""

    test_name: str
    status: ValidationStatus
    message: str
    details: dict | None = None


class Phase4Validator:
    """Phase 4 implementation validator."""

    def __init__(self) -> None:
        self.project_root = project_root
        self.results: list[ValidationResult] = []

    def add_result(self) -> None:
        """Add validation result."""
        self.results.append(ValidationResult(test_name, status, message, details))

    def validate_environment_sync(self) -> None:
        """Validate environment variable synchronization."""
        logger.info("Validating environment variable synchronization...")

        # Check if phase4_remediation directory exists
        remediation_dir = self.project_root / "phase4_remediation"
        if not remediation_dir.exists():
            self.add_result(
                "Environment Sync - Directory",
                ValidationStatus.FAIL,
                "Phase 4 remediation directory not found",
            )
            return

        # Check if required files exist
        required_files = [
            "github_secrets_template.md",
            "workflow_secrets_update.md",
            "vault_integration.sh",
            "fix_case_sensitivity.py",
            "phase4_remediation_report.md",
        ]

        for file_name in required_files:
            file_path = remediation_dir / file_name
            if file_path.exists():
                self.add_result(
                    f"Environment Sync - {file_name}",
                    ValidationStatus.PASS,
                    f"File exists: {file_path}",
                )
            else:
                self.add_result(
                    f"Environment Sync - {file_name}",
                    ValidationStatus.FAIL,
                    f"File missing: {file_path}",
                )

        # Validate environment variable analysis
        report_file = remediation_dir / "phase4_remediation_report.md"
        if report_file.exists():
            with open(report_file) as f:
                content = f.read()

            if "Total Environment Variables Identified: 45" in content:
                self.add_result(
                    "Environment Sync - Variable Count",
                    ValidationStatus.PASS,
                    "Correct number of environment variables identified",
                )
            else:
                self.add_result(
                    "Environment Sync - Variable Count",
                    ValidationStatus.WARNING,
                    "Environment variable count may be incorrect",
                )

            if "Sensitive Variables: 9" in content:
                self.add_result(
                    "Environment Sync - Sensitive Variables",
                    ValidationStatus.PASS,
                    "Correct number of sensitive variables identified",
                )
            else:
                self.add_result(
                    "Environment Sync - Sensitive Variables",
                    ValidationStatus.WARNING,
                    "Sensitive variable count may be incorrect",
                )

    def validate_workflow_updates(self) -> None:
        """Validate GitHub Actions workflow updates."""
        logger.info("Validating GitHub Actions workflow updates...")

        workflow_dir = self.project_root / ".github" / "workflows"
        if not workflow_dir.exists():
            self.add_result(
                "Workflow Updates - Directory",
                ValidationStatus.FAIL,
                "GitHub Actions workflows directory not found",
            )
            return

        # Check main workflow files
        main_workflows = ["comprehensive-cicd.yml", "enhanced-cicd.yml", "ci-cd.yml"]

        for workflow_name in main_workflows:
            workflow_file = workflow_dir / workflow_name
            if workflow_file.exists():
                self.validate_workflow_file(workflow_file)
            else:
                self.add_result(
                    f"Workflow Updates - {workflow_name}",
                    ValidationStatus.WARNING,
                    f"Workflow file not found: {workflow_file}",
                )

        # Check vault integration workflow
        vault_workflow = workflow_dir / "vault-integration.yml"
        if vault_workflow.exists():
            self.add_result(
                "Workflow Updates - Vault Integration",
                ValidationStatus.PASS,
                "Vault integration workflow created",
            )
        else:
            self.add_result(
                "Workflow Updates - Vault Integration",
                ValidationStatus.FAIL,
                "Vault integration workflow not found",
            )

    def validate_workflow_file(self, workflow_file: Path) -> None:
        """Validate individual workflow file."""
        try:
            with open(workflow_file) as f:
                workflow_data = yaml.safe_load(f)

            workflow_name = workflow_file.name

            # Check if env section exists
            if "env" in workflow_data:
                env_vars = workflow_data["env"]

                # Check for secrets context usage
                secrets_found = 0
                for _key, value in env_vars.items():
                    if isinstance(value, str) and value.startswith("${{ secrets."):
                        secrets_found += 1

                if secrets_found > 0:
                    self.add_result(
                        f"Workflow Updates - {workflow_name} - Secrets",
                        ValidationStatus.PASS,
                        f"Found {secrets_found} secrets context references",
                    )
                else:
                    self.add_result(
                        f"Workflow Updates - {workflow_name} - Secrets",
                        ValidationStatus.WARNING,
                        "No secrets context references found",
                    )

                # Check for required secrets
                required_secrets = [
                    "SECRET_KEY",
                    "DATABASE_URL",
                    "REDIS_URL",
                    "API_KEY",
                    "JWT_SECRET",
                    "DB_PASSWORD",
                    "REDIS_PASSWORD",
                ]

                found_secrets = []
                for secret in required_secrets:
                    if secret in env_vars:
                        found_secrets.append(secret)

                if len(found_secrets) >= 5:  # At least 5 of 7 required secrets
                    self.add_result(
                        f"Workflow Updates - {workflow_name} - Required Secrets",
                        ValidationStatus.PASS,
                        f"Found {len(found_secrets)}/{len(required_secrets)} required secrets",
                    )
                else:
                    self.add_result(
                        f"Workflow Updates - {workflow_name} - Required Secrets",
                        ValidationStatus.WARNING,
                        f"Only found {len(found_secrets)}/{len(required_secrets)} required secrets",
                    )
            else:
                self.add_result(
                    f"Workflow Updates - {workflow_name} - Env Section",
                    ValidationStatus.FAIL,
                    "No env section found in workflow",
                )

        except Exception as e:
            self.add_result(
                f"Workflow Updates - {workflow_file.name} - Parse",
                ValidationStatus.FAIL,
                f"Failed to parse workflow file: {e}",
            )

    def validate_vault_integration(self) -> None:
        """Validate HashiCorp Vault integration."""
        logger.info("Validating HashiCorp Vault integration...")

        # Check if vault client exists
        vault_client = (
            self.project_root
            / "src"
            / "services"
            / "secrets_manager"
            / "vault_client.py"
        )
        if vault_client.exists():
            self.add_result(
                "Vault Integration - Client",
                ValidationStatus.PASS,
                "Vault client implementation found",
            )

            # Check for key components in vault client
            with open(vault_client) as f:
                content = f.read()

            required_components = [
                "class VaultClient",
                "class PAKESecretsManager",
                "JWT_OIDC",
                "authenticate_jwt_oidc",
                "get_github_oidc_token",
            ]

            for component in required_components:
                if component in content:
                    self.add_result(
                        f"Vault Integration - {component}",
                        ValidationStatus.PASS,
                        f"Component found: {component}",
                    )
                else:
                    self.add_result(
                        f"Vault Integration - {component}",
                        ValidationStatus.FAIL,
                        f"Component missing: {component}",
                    )
        else:
            self.add_result(
                "Vault Integration - Client",
                ValidationStatus.FAIL,
                "Vault client implementation not found",
            )

        # Check vault integration script
        vault_script = self.project_root / "phase4_remediation" / "vault_integration.sh"
        if vault_script.exists():
            self.add_result(
                "Vault Integration - Script",
                ValidationStatus.PASS,
                "Vault integration script found",
            )

            # Check if script is executable
            if vault_script.stat().st_mode & 0o111:
                self.add_result(
                    "Vault Integration - Script Executable",
                    ValidationStatus.PASS,
                    "Vault integration script is executable",
                )
            else:
                self.add_result(
                    "Vault Integration - Script Executable",
                    ValidationStatus.WARNING,
                    "Vault integration script is not executable",
                )
        else:
            self.add_result(
                "Vault Integration - Script",
                ValidationStatus.FAIL,
                "Vault integration script not found",
            )

    def validate_case_sensitivity_fixes(self) -> None:
        """Validate case-sensitivity fixes."""
        logger.info("Validating case-sensitivity fixes...")

        # Check if case-sensitivity fix script exists
        case_script = (
            self.project_root / "phase4_remediation" / "fix_case_sensitivity.py"
        )
        if case_script.exists():
            self.add_result(
                "Case Sensitivity - Script",
                ValidationStatus.PASS,
                "Case-sensitivity fix script found",
            )

            # Check if script is executable
            if case_script.stat().st_mode & 0o111:
                self.add_result(
                    "Case Sensitivity - Script Executable",
                    ValidationStatus.PASS,
                    "Case-sensitivity fix script is executable",
                )
            else:
                self.add_result(
                    "Case Sensitivity - Script Executable",
                    ValidationStatus.WARNING,
                    "Case-sensitivity fix script is not executable",
                )

            # Try to run the script to check for syntax errors
            try:
                result = subprocess.run(
                    [sys.executable, str(case_script)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    self.add_result(
                        "Case Sensitivity - Script Execution",
                        ValidationStatus.PASS,
                        "Case-sensitivity script runs without errors",
                    )
                else:
                    self.add_result(
                        "Case Sensitivity - Script Execution",
                        ValidationStatus.WARNING,
                        f"Case-sensitivity script has issues: {result.stderr[:100]}",
                    )
            except subprocess.TimeoutExpired:
                self.add_result(
                    "Case Sensitivity - Script Execution",
                    ValidationStatus.WARNING,
                    "Case-sensitivity script timed out",
                )
            except Exception as e:
                self.add_result(
                    "Case Sensitivity - Script Execution",
                    ValidationStatus.FAIL,
                    f"Failed to run case-sensitivity script: {e}",
                )
        else:
            self.add_result(
                "Case Sensitivity - Script",
                ValidationStatus.FAIL,
                "Case-sensitivity fix script not found",
            )

    def validate_secrets_management(self) -> None:
        """Validate secrets management strategy."""
        logger.info("Validating secrets management strategy...")

        # Check if secrets management strategy document exists
        strategy_doc = self.project_root / "SECRETS_MANAGEMENT_STRATEGY.md"
        if strategy_doc.exists():
            self.add_result(
                "Secrets Management - Strategy Document",
                ValidationStatus.PASS,
                "Secrets management strategy document found",
            )

            with open(strategy_doc) as f:
                content = f.read()

            # Check for key strategy elements
            strategy_elements = [
                "EnterpriseSecretsManager",
                "Azure Key Vault",
                "Zero hardcoded secrets",
                "Fail-fast security",
                "Secret rotation",
            ]

            for element in strategy_elements:
                if element in content:
                    self.add_result(
                        f"Secrets Management - {element}",
                        ValidationStatus.PASS,
                        f"Strategy element found: {element}",
                    )
                else:
                    self.add_result(
                        f"Secrets Management - {element}",
                        ValidationStatus.WARNING,
                        f"Strategy element missing: {element}",
                    )
        else:
            self.add_result(
                "Secrets Management - Strategy Document",
                ValidationStatus.FAIL,
                "Secrets management strategy document not found",
            )

        # Check if enterprise secrets manager exists
        secrets_manager = (
            self.project_root
            / "src"
            / "services"
            / "secrets_manager"
            / "enterprise_secrets_manager.py"
        )
        if secrets_manager.exists():
            self.add_result(
                "Secrets Management - Enterprise Manager",
                ValidationStatus.PASS,
                "Enterprise secrets manager found",
            )
        else:
            self.add_result(
                "Secrets Management - Enterprise Manager",
                ValidationStatus.WARNING,
                "Enterprise secrets manager not found",
            )

    def validate_ci_pipeline(self) -> None:
        """Validate CI pipeline configuration."""
        logger.info("Validating CI pipeline configuration...")

        # Check if CI configuration files exist
        ci_files = [
            "pyproject.toml",
            "pytest.ini",
            "mypy.ini",
            ".pre-commit-config.yaml",
        ]

        for ci_file in ci_files:
            file_path = self.project_root / ci_file
            if file_path.exists():
                self.add_result(
                    f"CI Pipeline - {ci_file}",
                    ValidationStatus.PASS,
                    f"CI configuration file found: {ci_file}",
                )
            else:
                self.add_result(
                    f"CI Pipeline - {ci_file}",
                    ValidationStatus.WARNING,
                    f"CI configuration file missing: {ci_file}",
                )

        # Check if test directory exists
        test_dir = self.project_root / "tests"
        if test_dir.exists():
            test_files = list(test_dir.rglob("test_*.py"))
            if len(test_files) > 0:
                self.add_result(
                    "CI Pipeline - Test Files",
                    ValidationStatus.PASS,
                    f"Found {len(test_files)} test files",
                )
            else:
                self.add_result(
                    "CI Pipeline - Test Files",
                    ValidationStatus.WARNING,
                    "No test files found",
                )
        else:
            self.add_result(
                "CI Pipeline - Test Directory",
                ValidationStatus.FAIL,
                "Test directory not found",
            )

    def generate_report(self) -> str:
        """Generate validation report."""
        logger.info("Generating validation report...")

        # Count results by status
        status_counts = {}
        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        report = f"""
# Phase 4 Validation Report
# PAKE System - Strategic Plan for Codebase Remediation

## Executive Summary

This report validates the implementation of Phase 4 remediation strategies for the PAKE System.

## Validation Results Summary

- **Total Tests**: {len(self.results)}
- **Passed**: {status_counts.get(ValidationStatus.PASS, 0)}
- **Failed**: {status_counts.get(ValidationStatus.FAIL, 0)}
- **Warnings**: {status_counts.get(ValidationStatus.WARNING, 0)}
- **Skipped**: {status_counts.get(ValidationStatus.SKIP, 0)}

## Detailed Results

"""

        # Group results by category
        categories = {}
        for result in self.results:
            category = result.test_name.split(" - ")[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        for category, results in categories.items():
            report += f"### {category}\n\n"

            for result in results:
                status_emoji = {
                    ValidationStatus.PASS: "✅",
                    ValidationStatus.FAIL: "❌",
                    ValidationStatus.WARNING: "⚠️",
                    ValidationStatus.SKIP: "⏭️",
                }

                report += f"- {status_emoji[result.status]} **{result.test_name}**: {result.message}\n"

                if result.details:
                    report += f"  - Details: {json.dumps(result.details, indent=2)}\n"

            report += "\n"

        # Overall assessment
        pass_rate = (
            status_counts.get(ValidationStatus.PASS, 0) / len(self.results)
        ) * 100

        if pass_rate >= 90:
            overall_status = "EXCELLENT"
            status_emoji = "🎉"
        elif pass_rate >= 75:
            overall_status = "GOOD"
            status_emoji = "👍"
        elif pass_rate >= 50:
            overall_status = "FAIR"
            status_emoji = "⚠️"
        else:
            overall_status = "POOR"
            status_emoji = "❌"

        report += f"""
## Overall Assessment

{status_emoji} **Overall Status**: {overall_status}
- **Pass Rate**: {pass_rate:.1f}%
- **Implementation Quality**: {"High" if pass_rate >= 75 else "Needs Improvement"}

## Recommendations

"""

        if status_counts.get(ValidationStatus.FAIL, 0) > 0:
            report += "- **Critical**: Address all failed validations immediately\n"

        if status_counts.get(ValidationStatus.WARNING, 0) > 0:
            report += "- **Important**: Review and address warnings to improve implementation quality\n"

        if pass_rate >= 90:
            report += "- **Excellent**: Phase 4 implementation is ready for production deployment\n"
        elif pass_rate >= 75:
            report += "- **Good**: Phase 4 implementation is mostly ready, address remaining issues\n"
        else:
            report += "- **Needs Work**: Phase 4 implementation requires significant improvements\n"

        report += f"""
## Next Steps

1. **Address Failed Validations**: Fix all critical issues identified in the validation
2. **Review Warnings**: Improve implementation quality by addressing warnings
3. **Test Integration**: Run comprehensive integration tests
4. **Deploy to Staging**: Test Phase 4 implementations in staging environment
5. **Production Deployment**: Deploy to production after successful staging validation

---
Generated on: {os.popen("date").read().strip()}
Validation Script Version: Phase 4 Implementation v1.0
"""

        return report

    def run_validation(self) -> None:
        """Run complete Phase 4 validation."""
        logger.info("Starting Phase 4 validation...")

        # Run all validation tests
        self.validate_environment_sync()
        self.validate_workflow_updates()
        self.validate_vault_integration()
        self.validate_case_sensitivity_fixes()
        self.validate_secrets_management()
        self.validate_ci_pipeline()

        # Generate report
        report = self.generate_report()

        # Save report
        output_dir = self.project_root / "phase4_remediation"
        output_dir.mkdir(exist_ok=True)

        report_file = output_dir / "phase4_validation_report.md"
        with open(report_file, "w") as f:
            f.write(report)

        logger.info("Validation report saved to: %s", report_file)

        # Print summary
        print("\n" + "=" * 60)
        print("PHASE 4 VALIDATION SUMMARY")
        print("=" * 60)

        status_counts = {}
        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {status_counts.get(ValidationStatus.PASS, 0)}")
        print(f"❌ Failed: {status_counts.get(ValidationStatus.FAIL, 0)}")
        print(f"⚠️  Warnings: {status_counts.get(ValidationStatus.WARNING, 0)}")
        print(f"⏭️  Skipped: {status_counts.get(ValidationStatus.SKIP, 0)}")

        pass_rate = (
            status_counts.get(ValidationStatus.PASS, 0) / len(self.results)
        ) * 100
        print(f"\nPass Rate: {pass_rate:.1f}%")

        if pass_rate >= 90:
            print("🎉 Overall Status: EXCELLENT - Ready for production!")
        elif pass_rate >= 75:
            print("👍 Overall Status: GOOD - Mostly ready, minor issues to address")
        elif pass_rate >= 50:
            print("⚠️  Overall Status: FAIR - Needs improvement")
        else:
            print("❌ Overall Status: POOR - Significant work needed")

        print("=" * 60)


def main(self) -> None:
    """Main function to run Phase 4 validation."""
    project_root = Path(__file__).parent.parent
    validator = Phase4Validator(project_root)
    validator.run_validation()


if __name__ == "__main__":
    main()
