#!/usr/bin/env python3
"""
Test Validation Script
Runs comprehensive test suite (unit, integration, E2E, performance, security)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class TestValidator:
    """Test validation runner"""

    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.project_root = Path(__file__).parent.parent
        self.results: list[tuple[str, bool, str, dict[str, Any]]] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] [{level}] {message}")

    def run_command(
        self, name: str, command: list[str], description: str
    ) -> tuple[str, bool, str, dict[str, Any]]:
        """Run a command and return results"""
        self.log(f"Running {name}: {description}")
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
            )

            duration = time.time() - start_time

            # Parse output for test-specific information
            test_info = self._parse_test_output(name, result.stdout, result.stderr)

            if result.returncode == 0:
                self.log(f"✅ {name} passed ({duration:.2f}s)", "INFO")
                return name, True, result.stdout, test_info
            else:
                self.log(f"❌ {name} failed ({duration:.2f}s)", "ERROR")
                if self.verbose:
                    self.log(f"Error: {result.stderr}", "ERROR")
                return name, False, result.stderr, test_info

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log(f"⏰ {name} timed out after 600s", "ERROR")
            return name, False, "Timeout after 600s", {}
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {name} crashed: {e}", "ERROR")
            return name, False, str(e), {}

    def _parse_test_output(
        self, test_type: str, stdout: str, stderr: str
    ) -> dict[str, Any]:
        """Parse test output for structured information"""
        info = {"test_type": test_type, "summary": {}}

        try:
            lines = stdout.split("\n")

            # Parse pytest output
            for line in lines:
                if "failed" in line and "passed" in line:
                    # Parse line like "5 failed, 10 passed, 2 skipped in 1.23s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            if (
                                "failed" in line
                                and i > 0
                                and "failed" in parts[i - 1 : i + 2]
                            ):
                                info["summary"]["failed"] = int(part)
                            elif (
                                "passed" in line
                                and i > 0
                                and "passed" in parts[i - 1 : i + 2]
                            ):
                                info["summary"]["passed"] = int(part)
                            elif (
                                "skipped" in line
                                and i > 0
                                and "skipped" in parts[i - 1 : i + 2]
                            ):
                                info["summary"]["skipped"] = int(part)

                # Parse coverage information
                if "TOTAL" in line and "%" in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith("%"):
                            try:
                                info["summary"]["coverage"] = float(part[:-1])
                                break
                            except ValueError:
                                continue

            # Calculate totals
            if "summary" in info:
                summary = info["summary"]
                total = (
                    summary.get("passed", 0)
                    + summary.get("failed", 0)
                    + summary.get("skipped", 0)
                )
                info["summary"]["total"] = total
                info["summary"]["success_rate"] = (
                    (summary.get("passed", 0) / total * 100) if total > 0 else 0
                )

        except Exception as e:
            if self.verbose:
                self.log(f"Error parsing {test_type} output: {e}", "WARNING")

        return info

    def run_unit_tests(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run unit tests"""
        command = [
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

        if self.parallel:
            command.extend(["-n", "auto"])

        description = "Run unit tests with 85% coverage requirement"
        return self.run_command("unit-tests", command, description)

    def run_integration_tests(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run integration tests"""
        command = [
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

        if self.parallel:
            command.extend(["-n", "auto"])

        description = "Run integration tests with 80% coverage requirement"
        return self.run_command("integration-tests", command, description)

    def run_e2e_tests(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run end-to-end tests"""
        command = [
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

        if self.parallel:
            command.extend(["-n", "auto"])

        description = "Run E2E tests with 75% coverage requirement"
        return self.run_command("e2e-tests", command, description)

    def run_performance_tests(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run performance tests"""
        command = [
            "poetry",
            "run",
            "pytest",
            "tests/performance/",
            "--junitxml=performance-test-results.xml",
            "-v",
        ]

        if self.parallel:
            command.extend(["-n", "auto"])

        description = "Run performance tests"
        return self.run_command("performance-tests", command, description)

    def run_security_tests(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run security tests"""
        command = ["poetry", "run", "python", "scripts/security_test_suite.py"]
        description = "Run comprehensive security test suite"

        return self.run_command("security-tests", command, description)

    def run_all_tests(self) -> bool:
        """Run all tests"""
        self.log("Starting test validation...")

        # Run all tests
        tests = [
            self.run_unit_tests(),
            self.run_integration_tests(),
            self.run_e2e_tests(),
            self.run_performance_tests(),
            self.run_security_tests(),
        ]

        self.results.extend(tests)

        # Print summary
        self.print_summary()

        # Return success if all tests passed
        return all(result[1] for result in tests)

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("🧪 TEST VALIDATION SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, success, _, _ in self.results if success)
        total = len(self.results)

        print(f"📊 Total Test Suites: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"📈 Success Rate: {(passed/total*100):.1f}%")

        print("\n📋 Results by Test Suite:")
        for name, success, output, info in self.results:
            status_emoji = "✅" if success else "❌"
            print(
                f"  {status_emoji} {name.upper()}: {'PASSED' if success else 'FAILED'}"
            )

            # Show test-specific information
            if info.get("summary"):
                summary = info["summary"]
                if "total" in summary:
                    print(
                        f"     Tests: {summary.get('passed', 0)}/{summary['total']} passed"
                    )
                if "coverage" in summary:
                    print(f"     Coverage: {summary['coverage']:.1f}%")
                if "success_rate" in summary:
                    print(f"     Success Rate: {summary['success_rate']:.1f}%")

            if not success and self.verbose:
                print(f"     Error: {output[:200]}...")

        print("=" * 60)

        if passed == total:
            print("\n🎉 All test suites passed!")
        else:
            print(f"\n❌ {total - passed} test suite(s) failed!")
            print("💡 Review test failures and fix them before committing.")
            print("🔧 Common fixes:")
            print("   - Fix failing tests")
            print("   - Improve test coverage")
            print("   - Update test data and fixtures")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Test Validation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument(
        "--test-type",
        choices=["unit", "integration", "e2e", "performance", "security", "all"],
        default="all",
        help="Run specific test type",
    )
    parser.add_argument("--report-file", help="Save detailed test report to file")

    args = parser.parse_args()

    # Create validator
    validator = TestValidator(verbose=args.verbose, parallel=args.parallel)

    # Run specific test type or all
    if args.test_type == "all":
        success = validator.run_all_tests()
    else:
        if args.test_type == "unit":
            result = validator.run_unit_tests()
        elif args.test_type == "integration":
            result = validator.run_integration_tests()
        elif args.test_type == "e2e":
            result = validator.run_e2e_tests()
        elif args.test_type == "performance":
            result = validator.run_performance_tests()
        elif args.test_type == "security":
            result = validator.run_security_tests()

        validator.results.append(result)
        validator.print_summary()
        success = result[1]

    # Save report if requested
    if args.report_file:
        import json

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [
                {"test_type": name, "success": success, "output": output, "info": info}
                for name, success, output, info in validator.results
            ],
        }

        with open(args.report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Test report saved to: {args.report_file}")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
