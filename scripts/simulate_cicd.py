#!/usr/bin/env python3
"""
CI/CD Pipeline Simulation Script
Simulates the entire GitHub Actions CI/CD pipeline locally
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


class PipelineStage(Enum):
    """CI/CD Pipeline stages"""

    LINT_AND_FORMAT = "lint-and-format"
    STATIC_ANALYSIS = "static-analysis"
    SECURITY_SCAN = "security-scan"
    UNIT_TESTS = "unit-tests"
    INTEGRATION_TESTS = "integration-tests"
    E2E_TESTS = "e2e-tests"
    SECURITY_TESTS = "security-tests"
    TEST_COVERAGE_GATE = "test-coverage-gate"
    BUILD_AND_SCAN = "build-and-scan"


class StageResult(Enum):
    """Stage execution result"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class StageExecution:
    """Individual stage execution"""

    stage: PipelineStage
    result: StageResult
    duration: float
    output: str
    error: Optional[str] = None
    exit_code: int = 0


class CICDSimulator:
    """CI/CD Pipeline Simulator"""

    def __init__(
        self, verbose: bool = False, parallel: bool = False, skip_tests: bool = False
    ):
        self.verbose = verbose
        self.parallel = parallel
        self.skip_tests = skip_tests
        self.project_root = Path(__file__).parent.parent
        self.results: list[StageExecution] = []

        # Pipeline configuration matching GitHub Actions
        self.pipeline_config = {
            PipelineStage.LINT_AND_FORMAT: {
                "name": "🎨 Code Quality & Formatting",
                "timeout": 600,
                "required": True,
                "commands": [
                    ["poetry", "run", "ruff", "check", "src/", "tests/", "scripts/"],
                    ["poetry", "run", "black", "--check", "src/", "tests/", "scripts/"],
                    [
                        "poetry",
                        "run",
                        "isort",
                        "--check-only",
                        "src/",
                        "tests/",
                        "scripts/",
                    ],
                    ["npm", "run", "lint"],
                    ["npm", "run", "format:check"],
                ],
            },
            PipelineStage.STATIC_ANALYSIS: {
                "name": "🔍 Static Analysis & Type Checking",
                "timeout": 900,
                "required": True,
                "commands": [
                    ["poetry", "run", "mypy", "src/", "--strict", "--show-error-codes"],
                    ["npm", "run", "type-check"],
                    [
                        "poetry",
                        "run",
                        "bandit",
                        "-r",
                        "src/",
                        "-f",
                        "json",
                        "-o",
                        "bandit-report.json",
                    ],
                ],
            },
            PipelineStage.SECURITY_SCAN: {
                "name": "🔒 Security Scanning",
                "timeout": 1200,
                "required": True,
                "commands": [
                    [
                        "poetry",
                        "run",
                        "pip-audit",
                        "--format=json",
                        "--output=pip-audit-report.json",
                    ],
                    [
                        "poetry",
                        "run",
                        "safety",
                        "check",
                        "--json",
                        "--output=safety-report.json",
                    ],
                    [
                        "poetry",
                        "run",
                        "detect-secrets",
                        "scan",
                        "--baseline",
                        ".secrets.baseline",
                    ],
                    ["gitleaks", "detect", "--source", ".", "--verbose"],
                ],
            },
            PipelineStage.UNIT_TESTS: {
                "name": "🧪 Unit Tests",
                "timeout": 1200,
                "required": True,
                "commands": [
                    [
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
                    ]
                ],
            },
            PipelineStage.INTEGRATION_TESTS: {
                "name": "🔗 Integration Tests",
                "timeout": 1800,
                "required": True,
                "commands": [
                    [
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
                    ]
                ],
            },
            PipelineStage.E2E_TESTS: {
                "name": "🌐 End-to-End Tests",
                "timeout": 2700,
                "required": True,
                "commands": [
                    [
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
                    ]
                ],
            },
            PipelineStage.SECURITY_TESTS: {
                "name": "🛡️ Security Tests",
                "timeout": 1500,
                "required": True,
                "commands": [
                    ["poetry", "run", "python", "scripts/security_test_suite.py"]
                ],
            },
            PipelineStage.TEST_COVERAGE_GATE: {
                "name": "📊 Test Coverage Gate",
                "timeout": 900,
                "required": True,
                "commands": [
                    ["poetry", "run", "coverage", "combine", "coverage.xml"],
                    [
                        "poetry",
                        "run",
                        "coverage",
                        "report",
                        "--show-missing",
                        "--fail-under=85",
                    ],
                    ["poetry", "run", "coverage", "html", "-d", "htmlcov-combined"],
                    ["poetry", "run", "coverage", "xml", "-o", "coverage-combined.xml"],
                ],
            },
            PipelineStage.BUILD_AND_SCAN: {
                "name": "🐳 Build & Container Scan",
                "timeout": 1800,
                "required": True,
                "commands": [
                    [
                        "docker",
                        "build",
                        "-f",
                        "Dockerfile.production",
                        "-t",
                        "pake-system:local",
                        ".",
                    ],
                    [
                        "trivy",
                        "image",
                        "--format",
                        "json",
                        "--output",
                        "trivy-results.json",
                        "pake-system:local",
                    ],
                ],
            },
        }

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

        # Check Docker
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("Docker not found. Please install Docker.", "WARNING")
        except FileNotFoundError:
            self.log("Docker not found. Please install Docker.", "WARNING")

        # Check Trivy
        try:
            result = subprocess.run(
                ["trivy", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("Trivy not found. Please install Trivy.", "WARNING")
        except FileNotFoundError:
            self.log("Trivy not found. Please install Trivy.", "WARNING")

        # Check gitleaks
        try:
            result = subprocess.run(
                ["gitleaks", "version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.log("gitleaks not found. Please install gitleaks.", "WARNING")
        except FileNotFoundError:
            self.log("gitleaks not found. Please install gitleaks.", "WARNING")

        # Set up environment variables
        os.environ.setdefault("SECRET_KEY", "test-secret-key-for-cicd-simulation")
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

    def run_stage(self, stage: PipelineStage) -> StageExecution:
        """Run a single pipeline stage"""
        config = self.pipeline_config[stage]
        self.log(f"Running {config['name']}...")
        start_time = time.time()

        try:
            all_outputs = []
            all_errors = []
            exit_code = 0

            # Run all commands in the stage
            for command in config["commands"]:
                self.log(f"  Executing: {' '.join(command)}")

                try:
                    result = subprocess.run(
                        command,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=config["timeout"],
                    )

                    all_outputs.append(result.stdout)
                    if result.stderr:
                        all_errors.append(result.stderr)

                    if result.returncode != 0:
                        exit_code = result.returncode
                        break

                except subprocess.TimeoutExpired:
                    all_errors.append(f"Command timed out after {config['timeout']}s")
                    exit_code = -1
                    break
                except Exception as e:
                    all_errors.append(str(e))
                    exit_code = -1
                    break

            duration = time.time() - start_time

            # Determine result status
            if exit_code == 0:
                result_status = StageResult.PASSED
                error = None
            else:
                result_status = StageResult.FAILED
                error = "\n".join(all_errors)

            execution = StageExecution(
                stage=stage,
                result=result_status,
                duration=duration,
                output="\n".join(all_outputs),
                error=error,
                exit_code=exit_code,
            )

            if result_status == StageResult.PASSED:
                self.log(f"✅ {config['name']} passed ({duration:.2f}s)", "INFO")
            else:
                self.log(f"❌ {config['name']} failed ({duration:.2f}s)", "ERROR")
                if self.verbose and error:
                    self.log(f"Error: {error}", "ERROR")

            return execution

        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {config['name']} crashed: {e}", "ERROR")
            return StageExecution(
                stage=stage,
                result=StageResult.ERROR,
                duration=duration,
                output="",
                error=str(e),
                exit_code=-1,
            )

    def run_pipeline(self, stages: list[PipelineStage] = None) -> list[StageExecution]:
        """Run the CI/CD pipeline"""
        self.log("Starting CI/CD pipeline simulation...")

        if not self.check_prerequisites():
            self.log("Prerequisites check failed", "ERROR")
            return []

        if not self.install_dependencies():
            self.log("Dependency installation failed", "ERROR")
            return []

        # Determine stages to run
        if stages is None:
            stages = list(PipelineStage)
            if self.skip_tests:
                stages = [s for s in stages if "test" not in s.value]

        results = []

        # Run stages sequentially (matching GitHub Actions)
        for stage in stages:
            result = self.run_stage(stage)
            results.append(result)
            self.results.append(result)

            # Stop on first failure for required stages
            config = self.pipeline_config[stage]
            if config["required"] and result.result == StageResult.FAILED:
                self.log(
                    f"Stopping pipeline due to failure in required stage: {config['name']}",
                    "ERROR",
                )
                break

        return results

    def generate_report(self) -> dict:
        """Generate comprehensive pipeline report"""
        total_stages = len(self.results)
        passed_stages = len([r for r in self.results if r.result == StageResult.PASSED])
        failed_stages = len([r for r in self.results if r.result == StageResult.FAILED])
        error_stages = len([r for r in self.results if r.result == StageResult.ERROR])
        total_duration = sum(r.duration for r in self.results)

        # Calculate success rate
        success_rate = (passed_stages / total_stages * 100) if total_stages > 0 else 0

        report = {
            "summary": {
                "total_stages": total_stages,
                "passed_stages": passed_stages,
                "failed_stages": failed_stages,
                "error_stages": error_stages,
                "success_rate": round(success_rate, 2),
                "total_duration": round(total_duration, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "stages": {
                r.stage.value: {
                    "name": self.pipeline_config[r.stage]["name"],
                    "result": r.result.value,
                    "duration": round(r.duration, 2),
                    "exit_code": r.exit_code,
                    "error": r.error,
                    "required": self.pipeline_config[r.stage]["required"],
                }
                for r in self.results
            },
            "overall_status": "PASSED"
            if all(r.result == StageResult.PASSED for r in self.results)
            else "FAILED",
        }

        return report

    def print_summary(self):
        """Print pipeline summary"""
        report = self.generate_report()

        print("\n" + "=" * 80)
        print("🚀 CI/CD PIPELINE SIMULATION SUMMARY")
        print("=" * 80)

        summary = report["summary"]
        print(f"📊 Total Stages: {summary['total_stages']}")
        print(f"✅ Passed: {summary['passed_stages']}")
        print(f"❌ Failed: {summary['failed_stages']}")
        print(f"💥 Errors: {summary['error_stages']}")
        print(f"📈 Success Rate: {summary['success_rate']}%")
        print(f"⏱️ Total Duration: {summary['total_duration']}s")

        print(f"\n🎯 Overall Status: {report['overall_status']}")

        print("\n📋 Results by Stage:")
        for stage_key, stage_info in report["stages"].items():
            status_emoji = (
                "✅"
                if stage_info["result"] == "passed"
                else "❌"
                if stage_info["result"] == "failed"
                else "💥"
            )
            required_marker = " (REQUIRED)" if stage_info["required"] else ""
            print(
                f"  {status_emoji} {stage_info['name']}: {stage_info['result'].upper()} "
                f"({stage_info['duration']}s){required_marker}"
            )

            if stage_info["error"] and self.verbose:
                print(f"     Error: {stage_info['error'][:100]}...")

        print("=" * 80)

        # Print recommendations
        if report["overall_status"] == "FAILED":
            print("\n🔧 RECOMMENDATIONS:")
            print("1. Fix all failed pipeline stages before pushing to GitHub")
            print("2. Run individual validation scripts to debug specific issues:")
            print("   - python scripts/validate_lint.py --fix")
            print("   - python scripts/validate_type_check.py")
            print("   - python scripts/validate_security.py")
            print("   - python scripts/validate_tests.py")
            print("3. Check test coverage and add missing tests")
            print("4. Review security scan results and fix vulnerabilities")
            print("5. Ensure all dependencies are up to date")
        else:
            print("\n🎉 All pipeline stages passed! Ready to push to GitHub.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PAKE System CI/CD Pipeline Simulation"
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=[stage.value for stage in PipelineStage],
        help="Specific stages to run",
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip test execution stages"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--report-file", help="Save detailed pipeline report to file")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick pipeline (lint, format, type-check only)",
    )

    args = parser.parse_args()

    # Determine stages to run
    if args.quick:
        stages = [PipelineStage.LINT_AND_FORMAT, PipelineStage.STATIC_ANALYSIS]
    elif args.stages:
        stages = [PipelineStage(stage) for stage in args.stages]
    else:
        stages = None

    # Create simulator
    simulator = CICDSimulator(verbose=args.verbose, skip_tests=args.skip_tests)

    # Run pipeline
    results = simulator.run_pipeline(stages=stages)

    # Generate and print report
    simulator.print_summary()

    # Save report if requested
    if args.report_file:
        report = simulator.generate_report()
        with open(args.report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Pipeline report saved to: {args.report_file}")

    # Exit with appropriate code
    if all(r.result == StageResult.PASSED for r in results):
        print("\n🎉 All pipeline stages passed!")
        sys.exit(0)
    else:
        print("\n❌ Some pipeline stages failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
