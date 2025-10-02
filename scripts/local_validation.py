#!/usr/bin/env python3
"""
PAKE System Local Validation Script
Runs all CI/CD quality checks locally before pushing to GitHub
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ValidationResult(Enum):
    """Validation result status"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationStep:
    """Individual validation step"""

    name: str
    command: list[str]
    description: str
    timeout: int = 300
    required: bool = True
    cwd: Optional[Path] = None


@dataclass
class ValidationResult:
    """Result of validation step"""

    step: ValidationStep
    result: ValidationResult
    duration: float
    output: str
    error: Optional[str] = None
    exit_code: int = 0


class LocalValidator:
    """Local validation runner for PAKE System"""

    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.project_root = Path(__file__).parent.parent
        self.results: list[ValidationResult] = []

        # Define validation steps matching CI/CD pipeline
        self.validation_steps = [
            # Code Quality & Formatting
            ValidationStep(
                name="ruff-lint",
                command=[
                    "poetry",
                    "run",
                    "ruff",
                    "check",
                    "src/",
                    "tests/",
                    "scripts/",
                ],
                description="Run Ruff linting with comprehensive rule set",
                timeout=60,
            ),
            ValidationStep(
                name="black-format",
                command=[
                    "poetry",
                    "run",
                    "black",
                    "--check",
                    "src/",
                    "tests/",
                    "scripts/",
                ],
                description="Check Black code formatting",
                timeout=60,
            ),
            ValidationStep(
                name="isort-check",
                command=[
                    "poetry",
                    "run",
                    "isort",
                    "--check-only",
                    "src/",
                    "tests/",
                    "scripts/",
                ],
                description="Check import sorting with isort",
                timeout=60,
            ),
            ValidationStep(
                name="eslint",
                command=["npm", "run", "lint"],
                description="Run ESLint for TypeScript/JavaScript",
                timeout=120,
            ),
            ValidationStep(
                name="prettier-check",
                command=["npm", "run", "format:check"],
                description="Check Prettier formatting for frontend code",
                timeout=60,
            ),
            # Static Analysis & Type Checking
            ValidationStep(
                name="mypy",
                command=[
                    "poetry",
                    "run",
                    "mypy",
                    "src/",
                    "--strict",
                    "--show-error-codes",
                ],
                description="Run MyPy type checking with strict mode",
                timeout=180,
            ),
            ValidationStep(
                name="typescript-check",
                command=["npm", "run", "type-check"],
                description="Run TypeScript type checking",
                timeout=120,
            ),
            ValidationStep(
                name="bandit",
                command=["poetry", "run", "bandit", "-r", "src/", "-f", "json"],
                description="Run Bandit security analysis",
                timeout=120,
            ),
            # Security Scanning
            ValidationStep(
                name="pip-audit",
                command=["poetry", "run", "pip-audit", "--format=json"],
                description="Scan for vulnerable Python dependencies",
                timeout=180,
            ),
            ValidationStep(
                name="safety-check",
                command=["poetry", "run", "safety", "check", "--json"],
                description="Additional Python security checks",
                timeout=120,
            ),
            ValidationStep(
                name="detect-secrets",
                command=[
                    "poetry",
                    "run",
                    "detect-secrets",
                    "scan",
                    "--baseline",
                    ".secrets.baseline",
                ],
                description="Scan for hardcoded secrets",
                timeout=60,
            ),
            ValidationStep(
                name="gitleaks",
                command=["gitleaks", "detect", "--source", ".", "--verbose"],
                description="Scan git history for secrets",
                timeout=120,
            ),
            # Unit Tests
            ValidationStep(
                name="unit-tests",
                command=[
                    "poetry",
                    "run",
                    "pytest",
                    "tests/unit/",
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=html",
                    "--cov-fail-under=85",
                    "--junitxml=unit-test-results.xml",
                    "-v",
                ],
                description="Run unit tests with 85% coverage requirement",
                timeout=300,
            ),
            # Integration Tests
            ValidationStep(
                name="integration-tests",
                command=[
                    "poetry",
                    "run",
                    "pytest",
                    "tests/integration/",
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=html",
                    "--cov-fail-under=80",
                    "--junitxml=integration-test-results.xml",
                    "-v",
                ],
                description="Run integration tests with 80% coverage requirement",
                timeout=600,
            ),
            # End-to-End Tests
            ValidationStep(
                name="e2e-tests",
                command=[
                    "poetry",
                    "run",
                    "pytest",
                    "tests/e2e/",
                    "--cov=src",
                    "--cov-report=xml",
                    "--cov-report=html",
                    "--cov-fail-under=75",
                    "--junitxml=e2e-test-results.xml",
                    "-v",
                ],
                description="Run E2E tests with 75% coverage requirement",
                timeout=900,
            ),
            # Security Tests
            ValidationStep(
                name="security-tests",
                command=["poetry", "run", "python", "scripts/security_test_suite.py"],
                description="Run comprehensive security test suite",
                timeout=300,
            ),
            # Performance Tests
            ValidationStep(
                name="performance-tests",
                command=[
                    "poetry",
                    "run",
                    "pytest",
                    "tests/performance/",
                    "--junitxml=performance-test-results.xml",
                    "-v",
                ],
                description="Run performance tests",
                timeout=1200,
            ),
        ]

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] [{level}] {message}")

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        self.log("Checking prerequisites...")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 12):
            self.log(
                f"Python 3.12+ required, found {python_version.major}.{python_version.minor}",
                "ERROR",
            )
            return False

        # Check Poetry
        try:
            result = subprocess.run(
                ["poetry", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("Poetry not found. Please install Poetry.", "ERROR")
                return False
        except FileNotFoundError:
            self.log("Poetry not found. Please install Poetry.", "ERROR")
            return False

        # Check Node.js and npm
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("Node.js not found. Please install Node.js.", "ERROR")
                return False
        except FileNotFoundError:
            self.log("Node.js not found. Please install Node.js.", "ERROR")
            return False

        try:
            result = subprocess.run(
                ["npm", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("npm not found. Please install npm.", "ERROR")
                return False
        except FileNotFoundError:
            self.log("npm not found. Please install npm.", "ERROR")
            return False

        # Check gitleaks
        try:
            result = subprocess.run(
                ["gitleaks", "version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("gitleaks not found. Please install gitleaks.", "WARNING")
        except FileNotFoundError:
            self.log("gitleaks not found. Please install gitleaks.", "WARNING")

        # Check test directories
        test_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/e2e",
            "tests/performance",
        ]
        for test_dir in test_dirs:
            test_path = self.project_root / test_dir
            if not test_path.exists():
                self.log(f"Test directory not found: {test_path}", "WARNING")

        # Set up environment variables for testing
        os.environ.setdefault("SECRET_KEY", "test-secret-key-for-local-validation")
        os.environ.setdefault(
            "DATABASE_URL", "postgresql://test:test@localhost/pake_test"
        )
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
        os.environ.setdefault("USE_VAULT", "false")

        self.log("Prerequisites check completed", "INFO")
        return True

    def install_dependencies(self) -> bool:
        """Install dependencies"""
        self.log("Installing dependencies...")

        try:
            # Install Python dependencies
            result = subprocess.run(
                ["poetry", "install", "--no-interaction"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.log(
                    f"Failed to install Python dependencies: {result.stderr}", "ERROR"
                )
                return False

            # Install Node.js dependencies
            result = subprocess.run(
                ["npm", "ci"], cwd=self.project_root, capture_output=True, text=True
            )

            if result.returncode != 0:
                self.log(
                    f"Failed to install Node.js dependencies: {result.stderr}", "ERROR"
                )
                return False

            self.log("Dependencies installed successfully", "INFO")
            return True

        except Exception as e:
            self.log(f"Error installing dependencies: {e}", "ERROR")
            return False

    def run_validation_step(self, step: ValidationStep) -> ValidationResult:
        """Run a single validation step"""
        self.log(f"Running {step.name}: {step.description}")
        start_time = time.time()

        try:
            # Determine working directory
            cwd = step.cwd or self.project_root

            # Run the command
            result = subprocess.run(
                step.command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=step.timeout,
            )

            duration = time.time() - start_time

            # Determine result status
            if result.returncode == 0:
                status = ValidationResult.PASSED
                error = None
            else:
                status = ValidationResult.FAILED
                error = result.stderr

            validation_result = ValidationResult(
                step=step,
                result=status,
                duration=duration,
                output=result.stdout,
                error=error,
                exit_code=result.returncode,
            )

            if status == ValidationResult.PASSED:
                self.log(f"✅ {step.name} passed ({duration:.2f}s)", "INFO")
            else:
                self.log(f"❌ {step.name} failed ({duration:.2f}s)", "ERROR")
                if self.verbose and error:
                    self.log(f"Error: {error}", "ERROR")

            return validation_result

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log(f"⏰ {step.name} timed out after {step.timeout}s", "ERROR")
            return ValidationResult(
                step=step,
                result=ValidationResult.ERROR,
                duration=duration,
                output="",
                error=f"Timeout after {step.timeout}s",
                exit_code=-1,
            )
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {step.name} crashed: {e}", "ERROR")
            return ValidationResult(
                step=step,
                result=ValidationResult.ERROR,
                duration=duration,
                output="",
                error=str(e),
                exit_code=-1,
            )

    def run_validation_suite(
        self, categories: list[str] = None, skip_tests: bool = False
    ) -> list[ValidationResult]:
        """Run validation suite"""
        self.log("Starting local validation suite...")

        if not self.check_prerequisites():
            self.log("Prerequisites check failed", "ERROR")
            return []

        if not self.install_dependencies():
            self.log("Dependency installation failed", "ERROR")
            return []

        # Filter steps based on categories
        steps_to_run = self.validation_steps
        if categories:
            steps_to_run = [
                step
                for step in steps_to_run
                if any(cat in step.name for cat in categories)
            ]

        if skip_tests:
            steps_to_run = [step for step in steps_to_run if "test" not in step.name]

        results = []

        # Run validation steps
        for step in steps_to_run:
            result = self.run_validation_step(step)
            results.append(result)
            self.results.append(result)

            # Stop on first failure for required steps
            if step.required and result.result == ValidationResult.FAILED:
                self.log(
                    f"Stopping validation due to failure in required step: {step.name}",
                    "ERROR",
                )
                break

        return results

    def generate_report(self) -> dict:
        """Generate comprehensive validation report"""
        total_steps = len(self.results)
        passed_steps = len(
            [r for r in self.results if r.result == ValidationResult.PASSED]
        )
        failed_steps = len(
            [r for r in self.results if r.result == ValidationResult.FAILED]
        )
        error_steps = len(
            [r for r in self.results if r.result == ValidationResult.ERROR]
        )
        total_duration = sum(r.duration for r in self.results)

        # Calculate success rate
        success_rate = (passed_steps / total_steps * 100) if total_steps > 0 else 0

        report = {
            "summary": {
                "total_steps": total_steps,
                "passed_steps": passed_steps,
                "failed_steps": failed_steps,
                "error_steps": error_steps,
                "success_rate": round(success_rate, 2),
                "total_duration": round(total_duration, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "results": {
                r.step.name: {
                    "result": r.result.value,
                    "duration": round(r.duration, 2),
                    "exit_code": r.exit_code,
                    "error": r.error,
                    "required": r.step.required,
                }
                for r in self.results
            },
            "overall_status": "PASSED"
            if all(r.result == ValidationResult.PASSED for r in self.results)
            else "FAILED",
        }

        return report

    def print_summary(self):
        """Print validation summary"""
        report = self.generate_report()

        print("\n" + "=" * 80)
        print("🔍 PAKE SYSTEM LOCAL VALIDATION SUMMARY")
        print("=" * 80)

        summary = report["summary"]
        print(f"📊 Total Steps: {summary['total_steps']}")
        print(f"✅ Passed: {summary['passed_steps']}")
        print(f"❌ Failed: {summary['failed_steps']}")
        print(f"💥 Errors: {summary['error_steps']}")
        print(f"📈 Success Rate: {summary['success_rate']}%")
        print(f"⏱️ Total Duration: {summary['total_duration']}s")

        print(f"\n🎯 Overall Status: {report['overall_status']}")

        print("\n📋 Results by Step:")
        for step_name, result in report["results"].items():
            status_emoji = (
                "✅"
                if result["result"] == "passed"
                else "❌"
                if result["result"] == "failed"
                else "💥"
            )
            required_marker = " (REQUIRED)" if result["required"] else ""
            print(
                f"  {status_emoji} {step_name.upper()}: {result['result'].upper()} "
                f"({result['duration']}s){required_marker}"
            )

            if result["error"] and self.verbose:
                print(f"     Error: {result['error'][:100]}...")

        print("=" * 80)

        # Print recommendations
        if report["overall_status"] == "FAILED":
            print("\n🔧 RECOMMENDATIONS:")
            print("1. Fix all failed validation steps before pushing to GitHub")
            print(
                "2. Run 'poetry run ruff check --fix src/ tests/ scripts/' to auto-fix linting issues"
            )
            print("3. Run 'poetry run black src/ tests/ scripts/' to auto-format code")
            print("4. Run 'npm run format' to format frontend code")
            print("5. Check test coverage and add missing tests")
            print("6. Review security scan results and fix vulnerabilities")
        else:
            print("\n🎉 All validations passed! Ready to push to GitHub.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Local Validation")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["lint", "format", "type-check", "security", "test", "all"],
        default=["all"],
        help="Validation categories to run",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip test execution (faster validation)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--report-file", help="Save detailed report to file")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation only (lint, format, type-check)",
    )

    args = parser.parse_args()

    # Determine categories
    if args.quick:
        categories = ["lint", "format", "type-check"]
    else:
        categories = args.categories

    # Create validator
    validator = LocalValidator(verbose=args.verbose)

    # Run validation
    results = validator.run_validation_suite(
        categories=categories, skip_tests=args.skip_tests
    )

    # Generate and print report
    validator.print_summary()

    # Save report if requested
    if args.report_file:
        report = validator.generate_report()
        with open(args.report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Detailed report saved to: {args.report_file}")

    # Exit with appropriate code
    if all(r.result == ValidationResult.PASSED for r in results):
        print("\n🎉 All validations passed!")
        sys.exit(0)
    else:
        print("\n❌ Some validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
