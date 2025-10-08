#!/usr/bin/env python3
"""PAKE System - Chaos Engineering Integration Test
Section 3.2: Implementing Proactive Resilience

This script validates the complete chaos engineering implementation.
"""

import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChaosIntegrationValidator:
    """Validates the complete chaos engineering implementation."""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.errors = []
        self.warnings = []

    def validate_file_structure(self) -> bool:
        """Validate the chaos engineering file structure."""
        logger.info("🔍 Validating file structure...")

        required_files = [
            "requirements.txt",
            "chaos_config.yaml",
            "README.md",
            "test_runner.py",
            "deploy.sh",
        ]

        required_dirs = ["experiments", "probes", "activities"]

        required_experiments = [
            "experiments/database_failover_test.json",
            "experiments/api_instance_failure_test.json",
            "experiments/backup_restore_validation.json",
        ]

        required_probes = [
            "probes/database_probe.py",
            "probes/application_probe.py",
            "probes/system_health_probe.py",
        ]

        required_activities = [
            "activities/database_activities.py",
            "activities/application_activities.py",
            "activities/infrastructure_activities.py",
        ]

        all_required = (
            required_files
            + required_dirs
            + required_experiments
            + required_probes
            + required_activities
        )

        for item in all_required:
            path = self.base_dir / item
            if not path.exists():
                self.errors.append(f"Missing required file/directory: {item}")
            else:
                logger.info(f"✅ Found: {item}")

        return len(self.errors) == 0

    def validate_experiment_schemas(self) -> bool:
        """Validate chaos experiment JSON schemas."""
        logger.info("🔍 Validating experiment schemas...")

        experiments = [
            "experiments/database_failover_test.json",
            "experiments/api_instance_failure_test.json",
            "experiments/backup_restore_validation.json",
        ]

        required_fields = [
            "version",
            "title",
            "description",
            "tags",
            "steady-state-hypothesis",
            "method",
            "rollbacks",
        ]

        for exp_file in experiments:
            path = self.base_dir / exp_file
            try:
                with open(path) as f:
                    experiment = json.load(f)

                for field in required_fields:
                    if field not in experiment:
                        self.errors.append(f"Missing field '{field}' in {exp_file}")
                    else:
                        logger.info(f"✅ {exp_file} has field '{field}'")

                # Validate steady-state-hypothesis structure
                if "steady-state-hypothesis" in experiment:
                    ssh = experiment["steady-state-hypothesis"]
                    if "probes" not in ssh:
                        self.errors.append(
                            f"Missing 'probes' in steady-state-hypothesis in {exp_file}"
                        )

                # Validate method structure
                if "method" in experiment:
                    method = experiment["method"]
                    if not isinstance(method, list):
                        self.errors.append(f"'method' should be a list in {exp_file}")

            except json.JSONDecodeError as e:
                self.errors.append(f"Invalid JSON in {exp_file}: {e}")
            except Exception as e:
                self.errors.append(f"Error reading {exp_file}: {e}")

        return len(self.errors) == 0

    def validate_python_modules(self) -> bool:
        """Validate Python module syntax and imports."""
        logger.info("🔍 Validating Python modules...")

        python_files = [
            "probes/database_probe.py",
            "probes/application_probe.py",
            "probes/system_health_probe.py",
            "activities/database_activities.py",
            "activities/application_activities.py",
            "activities/infrastructure_activities.py",
            "test_runner.py",
        ]

        for py_file in python_files:
            path = self.base_dir / py_file
            try:
                # Try to compile the Python file
                with open(path) as f:
                    compile(f.read(), str(path), "exec")
                logger.info(f"✅ {py_file} compiles successfully")

                # Check for required imports
                with open(path) as f:
                    content = f.read()

                if "import logging" not in content:
                    self.warnings.append(f"Missing logging import in {py_file}")

                if "logger = logging.getLogger(__name__)" not in content:
                    self.warnings.append(f"Missing logger setup in {py_file}")

            except SyntaxError as e:
                self.errors.append(f"Syntax error in {py_file}: {e}")
            except Exception as e:
                self.errors.append(f"Error validating {py_file}: {e}")

        return len(self.errors) == 0

    def validate_configuration(self) -> bool:
        """Validate chaos configuration file."""
        logger.info("🔍 Validating configuration...")

        config_file = self.base_dir / "chaos_config.yaml"
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)

            required_sections = [
                "version",
                "title",
                "environments",
                "experiments",
                "thresholds",
            ]
            for section in required_sections:
                if section not in config:
                    self.errors.append(
                        f"Missing section '{section}' in chaos_config.yaml"
                    )
                else:
                    logger.info(f"✅ Configuration has section '{section}'")

            # Validate thresholds
            if "thresholds" in config:
                thresholds = config["thresholds"]
                required_thresholds = [
                    "rto",
                    "rpo",
                    "max_error_rate",
                    "max_latency_ms",
                    "max_restore_time",
                ]
                for threshold in required_thresholds:
                    if threshold not in thresholds:
                        self.errors.append(
                            f"Missing threshold '{threshold}' in chaos_config.yaml"
                        )
                    else:
                        logger.info(f"✅ Threshold '{threshold}' is configured")

        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in chaos_config.yaml: {e}")
        except Exception as e:
            self.errors.append(f"Error reading chaos_config.yaml: {e}")

        return len(self.errors) == 0

    def validate_dependencies(self) -> bool:
        """Validate Python dependencies."""
        logger.info("🔍 Validating dependencies...")

        requirements_file = self.base_dir / "requirements.txt"
        try:
            with open(requirements_file) as f:
                requirements = f.read()

            required_packages = [
                "chaostoolkit",
                "chaostoolkit-kubernetes",
                "chaostoolkit-prometheus",
                "psycopg2-binary",
                "redis",
                "requests",
                "prometheus-client",
                "kubernetes",
                "pyyaml",
                "python-dotenv",
            ]

            for package in required_packages:
                if package in requirements:
                    logger.info(f"✅ Required package '{package}' found")
                else:
                    self.warnings.append(
                        f"Package '{package}' not found in requirements.txt"
                    )

        except Exception as e:
            self.errors.append(f"Error reading requirements.txt: {e}")

        return len(self.errors) == 0

    def validate_engineering_guide_compliance(self) -> bool:
        """Validate compliance with Section 3.2 of the Engineering Guide."""
        logger.info("🔍 Validating Engineering Guide compliance...")

        # Check for Chaos Toolkit framework
        if (self.base_dir / "requirements.txt").exists():
            with open(self.base_dir / "requirements.txt") as f:
                content = f.read()
            if "chaostoolkit" in content:
                logger.info("✅ Chaos Toolkit framework implemented")
            else:
                self.errors.append("Chaos Toolkit framework not found")

        # Check for three critical recovery tests
        critical_tests = [
            "database_failover_test.json",
            "api_instance_failure_test.json",
            "backup_restore_validation.json",
        ]

        for test in critical_tests:
            test_path = self.base_dir / "experiments" / test
            if test_path.exists():
                logger.info(f"✅ Critical test '{test}' implemented")
            else:
                self.errors.append(f"Critical test '{test}' not implemented")

        # Check for scientific method implementation
        for test in critical_tests:
            test_path = self.base_dir / "experiments" / test
            if test_path.exists():
                with open(test_path) as f:
                    experiment = json.load(f)

                if "steady-state-hypothesis" in experiment and "method" in experiment:
                    logger.info(f"✅ Scientific method implemented in '{test}'")
                else:
                    self.errors.append(
                        f"Scientific method not properly implemented in '{test}'"
                    )

        # Check for staging environment setup
        staging_config = self.base_dir.parent / "k8s" / "chaos-staging.yaml"
        if staging_config.exists():
            logger.info("✅ Staging environment configuration found")
        else:
            self.warnings.append("Staging environment configuration not found")

        return len(self.errors) == 0

    def run_comprehensive_validation(self) -> dict[str, Any]:
        """Run comprehensive validation of the chaos engineering implementation."""
        logger.info("🚀 Starting comprehensive chaos engineering validation...")

        validation_results = {
            "file_structure": self.validate_file_structure(),
            "experiment_schemas": self.validate_experiment_schemas(),
            "python_modules": self.validate_python_modules(),
            "configuration": self.validate_configuration(),
            "dependencies": self.validate_dependencies(),
            "engineering_guide_compliance": self.validate_engineering_guide_compliance(),
        }

        # Generate summary
        total_checks = len(validation_results)
        passed_checks = sum(1 for result in validation_results.values() if result)

        summary = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "success_rate": (passed_checks / total_checks) * 100,
            "errors": self.errors,
            "warnings": self.warnings,
            "validation_results": validation_results,
        }

        return summary

    def print_validation_report(self, summary: dict[str, Any]):
        """Print a comprehensive validation report."""
        print("\n" + "=" * 60)
        print("PAKE SYSTEM - CHAOS ENGINEERING VALIDATION REPORT")
        print("=" * 60)

        print("\n📊 SUMMARY:")
        print(f"   Total Checks: {summary['total_checks']}")
        print(f"   Passed: {summary['passed_checks']}")
        print(f"   Failed: {summary['failed_checks']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")

        print("\n✅ VALIDATION RESULTS:")
        for check, result in summary["validation_results"].items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {check.replace('_', ' ').title()}: {status}")

        if summary["errors"]:
            print(f"\n❌ ERRORS ({len(summary['errors'])}):")
            for error in summary["errors"]:
                print(f"   • {error}")

        if summary["warnings"]:
            print(f"\n⚠️  WARNINGS ({len(summary['warnings'])}):")
            for warning in summary["warnings"]:
                print(f"   • {warning}")

        print("\n🎯 CONCLUSION:")
        if summary["success_rate"] == 100:
            print(
                "   🎉 All validations passed! Chaos engineering implementation is complete."
            )
        elif summary["success_rate"] >= 80:
            print("   ✅ Most validations passed. Minor issues need attention.")
        else:
            print(
                "   ⚠️  Multiple validation failures. Implementation needs significant work."
            )

        print("=" * 60)


def main():
    """Main entry point."""
    validator = ChaosIntegrationValidator()
    summary = validator.run_comprehensive_validation()
    validator.print_validation_report(summary)

    # Exit with appropriate code
    if summary["success_rate"] == 100:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()
