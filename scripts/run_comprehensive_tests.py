#!/usr/bin/env python3
"""
PAKE System Comprehensive Test Execution Script
Enforces testing pyramid and coverage requirements
"""

import json
import logging
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestExecutor:
    def __init__(self) -> None:
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.results = {
            "unit": {"passed": 0, "failed": 0, "time": 0, "coverage": 0},
            "integration": {"passed": 0, "failed": 0, "time": 0, "coverage": 0},
            "e2e": {"passed": 0, "failed": 0, "time": 0, "coverage": 0},
            "total": {"passed": 0, "failed": 0, "time": 0, "coverage": 0},
        }

    def run_command(self, command: str, cwd: Path = None) -> tuple[bool, str, float]:
        """Run a shell command and return success status, output, and execution time"""
        start_time = time.time()
        try:
            result = subprocess.run(
                command.split(),
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            execution_time = time.time() - start_time
            return True, result.stdout, execution_time
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            logger.error("Command failed: %s", command)
            logger.error("Error: %s", e.stderr)
            return False, e.stderr, execution_time

    def run_unit_tests(self) -> bool:
        """Run unit tests with coverage"""
        logger.info("Running unit tests...")

        command = (
            "poetry run pytest tests/unit/ "
            "-v --cov=src --cov-report=term-missing --cov-report=xml "
            "--cov-fail-under=80 --maxfail=5 --tb=short "
            "-m 'unit' --durations=10"
        )

        success, output, execution_time = self.run_command(command)

        if success:
            # Parse results
            self.parse_pytest_output(output, "unit", execution_time)
            logger.info("✅ Unit tests passed in %.2f%%s", execution_time)
            return True
        logger.error("❌ Unit tests failed: %s", output)
        return False

    def run_integration_tests(self) -> bool:
        """Run integration tests with coverage"""
        logger.info("Running integration tests...")

        command = (
            "poetry run pytest tests/integration/ "
            "-v --cov=src --cov-report=term-missing --cov-report=xml "
            "--cov-fail-under=70 --maxfail=3 --tb=short "
            "-m 'integration' --durations=10"
        )

        success, output, execution_time = self.run_command(command)

        if success:
            # Parse results
            self.parse_pytest_output(output, "integration", execution_time)
            logger.info("✅ Integration tests passed in %.2f%%s", execution_time)
            return True
        logger.error("❌ Integration tests failed: %s", output)
        return False

    def run_e2e_tests(self) -> bool:
        """Run end-to-end tests with coverage"""
        logger.info("Running E2E tests...")

        command = (
            "poetry run pytest tests/e2e/ "
            "-v --cov=src --cov-report=term-missing --cov-report=xml "
            "--cov-fail-under=60 --maxfail=2 --tb=short "
            "-m 'e2e' --durations=10"
        )

        success, output, execution_time = self.run_command(command)

        if success:
            # Parse results
            self.parse_pytest_output(output, "e2e", execution_time)
            logger.info("✅ E2E tests passed in %.2f%%s", execution_time)
            return True
        logger.error("❌ E2E tests failed: %s", output)
        return False

    def parse_pytest_output(self) -> None:
        """Parse pytest output to extract test results"""
        lines = self.output.split("\n")

        # Find test results
        for line in lines:
            if "passed" in line and "failed" in line:
                # Extract numbers from line like "5 passed, 2 failed in 10.5s"
                import re

                match = re.search(r"(\d+) passed", line)
                if match:
                    self.results[test_type]["passed"] = int(match.group(1))

                match = re.search(r"(\d+) failed", line)
                if match:
                    self.results[test_type]["failed"] = int(match.group(1))

        self.results[test_type]["time"] = execution_time

        # Extract coverage percentage
        for line in lines:
            if "TOTAL" in line and "%" in line:
                import re

                match = re.search(r"(\d+)%", line)
                if match:
                    self.results[test_type]["coverage"] = int(match.group(1))

    def run_security_tests(self) -> bool:
        """Run security-specific tests"""
        logger.info("Running security tests...")

        command = (
            "poetry run pytest tests/security/ "
            "-v --cov=src --cov-report=term-missing "
            "-m 'security' --durations=10"
        )

        success, output, execution_time = self.run_command(command)

        if success:
            logger.info("✅ Security tests passed in %.2f%%s", execution_time)
            return True
        logger.error("❌ Security tests failed: %s", output)
        return False

    def run_performance_tests(self) -> bool:
        """Run performance tests"""
        logger.info("Running performance tests...")

        command = (
            "poetry run pytest tests/performance/ "
            "-v --benchmark-only --benchmark-sort=mean "
            "-m 'performance'"
        )

        success, output, execution_time = self.run_command(command)

        if success:
            logger.info("✅ Performance tests passed in %.2f%%s", execution_time)
            return True
        logger.warning("⚠️ Performance tests failed: %s", output)
        return False

    def validate_testing_pyramid(self) -> bool:
        """Validate that the testing pyramid is properly balanced"""
        logger.info("Validating testing pyramid...")

        # Calculate test distribution
        total_tests = sum(
            self.results[test_type]["passed"] + self.results[test_type]["failed"]
            for test_type in ["unit", "integration", "e2e"]
        )

        if total_tests == 0:
            logger.error("No tests found!")
            return False

        unit_percentage = (
            (self.results["unit"]["passed"] + self.results["unit"]["failed"])
            / total_tests
            * 100
        )
        integration_percentage = (
            (
                self.results["integration"]["passed"]
                + self.results["integration"]["failed"]
            )
            / total_tests
            * 100
        )
        e2e_percentage = (
            (self.results["e2e"]["passed"] + self.results["e2e"]["failed"])
            / total_tests
            * 100
        )

        logger.info("Testing Pyramid Distribution:")
        logger.info("  Unit Tests: %.1f%%% (target: 70%)", unit_percentage)
        logger.info(
            "  Integration Tests: %.1f%%% (target: 20%)", integration_percentage
        )
        logger.info("  E2E Tests: %.1f%%% (target: 10%)", e2e_percentage)

        # Validate pyramid structure
        pyramid_valid = (
            60 <= unit_percentage <= 80  # Allow some flexibility
            and 15 <= integration_percentage <= 25
            and 5 <= e2e_percentage <= 15
        )

        if pyramid_valid:
            logger.info("✅ Testing pyramid is properly balanced")
        else:
            logger.warning("⚠️ Testing pyramid needs adjustment")

        return pyramid_valid

    def validate_coverage_requirements(self) -> bool:
        """Validate that coverage requirements are met"""
        logger.info("Validating coverage requirements...")

        coverage_valid = True

        # Check unit test coverage
        if self.results["unit"]["coverage"] < 80:
            logger.error(
                "❌ Unit test coverage %s% < 80%", self.results["unit"]["coverage"]
            )
            coverage_valid = False
        else:
            logger.info("✅ Unit test coverage: %s%", self.results["unit"]["coverage"])

        # Check integration test coverage
        if self.results["integration"]["coverage"] < 70:
            logger.error(
                "❌ Integration test coverage %s% < 70%",
                self.results["integration"]["coverage"],
            )
            coverage_valid = False
        else:
            logger.info(
                "✅ Integration test coverage: %s%",
                self.results["integration"]["coverage"],
            )

        # Check E2E test coverage
        if self.results["e2e"]["coverage"] < 60:
            logger.error(
                "❌ E2E test coverage %s% < 60%", self.results["e2e"]["coverage"]
            )
            coverage_valid = False
        else:
            logger.info("✅ E2E test coverage: %s%", self.results["e2e"]["coverage"])

        return coverage_valid

    def validate_performance_requirements(self) -> bool:
        """Validate that performance requirements are met"""
        logger.info("Validating performance requirements...")

        performance_valid = True

        # Check unit test performance
        if self.results["unit"]["time"] > 60:  # 1 minute limit
            logger.error(
                "❌ Unit tests took %ss > 60s", f"{self.results['unit']['time']:.2f}"
            )
            performance_valid = False
        else:
            logger.info(
                "✅ Unit tests completed in %ss", f"{self.results['unit']['time']:.2f}"
            )

        # Check integration test performance
        if self.results["integration"]["time"] > 300:  # 5 minute limit
            logger.error(
                "❌ Integration tests took %ss > 300s",
                f"{self.results['integration']['time']:.2f}",
            )
            performance_valid = False
        else:
            logger.info(
                "✅ Integration tests completed in %ss",
                f"{self.results['integration']['time']:.2f}",
            )

        # Check E2E test performance
        if self.results["e2e"]["time"] > 600:  # 10 minute limit
            logger.error(
                "❌ E2E tests took %.2f%%s > 600s", self.results["e2e"]["time"]
            )
            performance_valid = False
        else:
            logger.info(
                "✅ E2E tests completed in %.2f%%s", self.results["e2e"]["time"]
            )

        return performance_valid

    def generate_test_report(self) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("# PAKE System Test Execution Report")
        report.append("=" * 50)
        report.append("")

        # Test Results Summary
        report.append("## Test Results Summary")
        report.append("")
        report.append("| Test Type | Passed | Failed | Time | Coverage |")
        report.append("|-----------|--------|--------|------|----------|")

        for test_type in ["unit", "integration", "e2e"]:
            results = self.results[test_type]
            report.append(
                f"| {test_type.title()} | {results['passed']} | {results['failed']} | "
                f"{results['time']:.2f}s | {results['coverage']}% |"
            )

        report.append("")

        # Testing Pyramid Validation
        report.append("## Testing Pyramid Validation")
        report.append("")
        total_tests = sum(
            self.results[test_type]["passed"] + self.results[test_type]["failed"]
            for test_type in ["unit", "integration", "e2e"]
        )

        if total_tests > 0:
            unit_percentage = (
                (self.results["unit"]["passed"] + self.results["unit"]["failed"])
                / total_tests
                * 100
            )
            integration_percentage = (
                (
                    self.results["integration"]["passed"]
                    + self.results["integration"]["failed"]
                )
                / total_tests
                * 100
            )
            e2e_percentage = (
                (self.results["e2e"]["passed"] + self.results["e2e"]["failed"])
                / total_tests
                * 100
            )

            report.append(f"- Unit Tests: {unit_percentage:.1f}% (target: 70%)")
            report.append(
                f"- Integration Tests: {integration_percentage:.1f}% (target: 20%)"
            )
            report.append(f"- E2E Tests: {e2e_percentage:.1f}% (target: 10%)")
            report.append("")

        # Coverage Requirements
        report.append("## Coverage Requirements")
        report.append("")
        report.append(
            f"- Unit Test Coverage: {self.results['unit']['coverage']}% (required: 80%)"
        )
        report.append(
            f"- Integration Test Coverage: {self.results['integration']['coverage']}% (required: 70%)"
        )
        report.append(
            f"- E2E Test Coverage: {self.results['e2e']['coverage']}% (required: 60%)"
        )
        report.append("")

        # Performance Requirements
        report.append("## Performance Requirements")
        report.append("")
        report.append(
            f"- Unit Test Time: {self.results['unit']['time']:.2f}s (limit: 60s)"
        )
        report.append(
            f"- Integration Test Time: {self.results['integration']['time']:.2f}s (limit: 300s)"
        )
        report.append(
            f"- E2E Test Time: {self.results['e2e']['time']:.2f}s (limit: 600s)"
        )
        report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        if self.results["unit"]["coverage"] < 80:
            report.append("- Increase unit test coverage to meet 80% requirement")

        if self.results["integration"]["coverage"] < 70:
            report.append(
                "- Increase integration test coverage to meet 70% requirement"
            )

        if self.results["e2e"]["coverage"] < 60:
            report.append("- Increase E2E test coverage to meet 60% requirement")

        if self.results["unit"]["time"] > 60:
            report.append("- Optimize unit tests to reduce execution time")

        if self.results["integration"]["time"] > 300:
            report.append("- Optimize integration tests to reduce execution time")

        if self.results["e2e"]["time"] > 600:
            report.append("- Optimize E2E tests to reduce execution time")

        report.append("")

        return "\n".join(report)

    def run_comprehensive_tests(self) -> bool:
        """Run comprehensive test suite with validation"""
        logger.info("Starting comprehensive test execution...")

        start_time = time.time()

        # Run all test types
        unit_success = self.run_unit_tests()
        integration_success = self.run_integration_tests()
        e2e_success = self.run_e2e_tests()
        security_success = self.run_security_tests()
        performance_success = self.run_performance_tests()

        # Validate requirements
        pyramid_valid = self.validate_testing_pyramid()
        coverage_valid = self.validate_coverage_requirements()
        performance_valid = self.validate_performance_requirements()

        total_time = time.time() - start_time

        # Generate report
        report = self.generate_test_report()

        # Save report
        report_path = self.project_root / "TEST_EXECUTION_REPORT.md"
        with open(report_path, "w") as f:
            f.write(report)

        logger.info("Test execution report saved to %s", report_path)

        # Determine overall success
        overall_success = (
            unit_success
            and integration_success
            and e2e_success
            and security_success
            and pyramid_valid
            and coverage_valid
            and performance_valid
        )

        if overall_success:
            logger.info("🎉 All tests passed in %.2f%%s!", total_time)
        else:
            logger.error("❌ Some tests failed or requirements not met!")

        return overall_success


def main(self) -> None:
    """Main entry point"""
    project_root = Path(__file__).parent.parent
    test_executor = TestExecutor(project_root)

    try:
        success = test_executor.run_comprehensive_tests()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except (ValueError, RuntimeError) as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()