#!/usr/bin/env python3
"""
PAKE System Comprehensive Test Runner
Enterprise-grade test execution with multiple modes and comprehensive reporting
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class TestMode(Enum):
    """Test execution modes"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ALL = "all"
    QUICK = "quick"


class TestResult(Enum):
    """Test result status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestExecutionResult:
    """Result of test execution"""
    mode: TestMode
    result: TestResult
    duration: float
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    coverage_percentage: Optional[float] = None
    error_message: Optional[str] = None


class PAKETestRunner:
    """Comprehensive test runner for PAKE System"""
    
    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.project_root = Path(__file__).parent.parent
        self.results: List[TestExecutionResult] = []
        
        # Test configuration
        self.test_config = {
            "unit": {
                "path": "tests/unit/",
                "coverage_threshold": 85,
                "timeout": 300,
                "markers": ["unit"]
            },
            "integration": {
                "path": "tests/integration/",
                "coverage_threshold": 80,
                "timeout": 600,
                "markers": ["integration"]
            },
            "e2e": {
                "path": "tests/e2e/",
                "coverage_threshold": 75,
                "timeout": 900,
                "markers": ["e2e"]
            },
            "security": {
                "path": "scripts/security_test_suite.py",
                "coverage_threshold": None,
                "timeout": 300,
                "markers": ["security"]
            },
            "performance": {
                "path": "tests/performance/",
                "coverage_threshold": None,
                "timeout": 1200,
                "markers": ["performance"]
            }
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
            self.log(f"Python 3.12+ required, found {python_version.major}.{python_version.minor}", "ERROR")
            return False
        
        # Check Poetry
        try:
            result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                self.log("Poetry not found. Please install Poetry.", "ERROR")
                return False
        except FileNotFoundError:
            self.log("Poetry not found. Please install Poetry.", "ERROR")
            return False
        
        # Check test directories
        for test_type, config in self.test_config.items():
            if test_type == "security":
                continue  # Security tests are a script
            test_path = self.project_root / config["path"]
            if not test_path.exists():
                self.log(f"Test directory not found: {test_path}", "WARNING")
        
        # Check environment variables
        required_env_vars = ["SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.log(f"Missing environment variables: {', '.join(missing_vars)}", "WARNING")
            self.log("Setting default test values...", "INFO")
            os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
            os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/pake_test")
            os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
            os.environ.setdefault("USE_VAULT", "false")
        
        self.log("Prerequisites check completed", "INFO")
        return True
    
    def install_dependencies(self) -> bool:
        """Install test dependencies"""
        self.log("Installing dependencies...")
        
        try:
            # Install Python dependencies
            result = subprocess.run(
                ["poetry", "install", "--no-interaction"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log(f"Failed to install dependencies: {result.stderr}", "ERROR")
                return False
            
            self.log("Dependencies installed successfully", "INFO")
            return True
            
        except Exception as e:
            self.log(f"Error installing dependencies: {e}", "ERROR")
            return False
    
    def run_unit_tests(self) -> TestExecutionResult:
        """Run unit tests"""
        self.log("Running unit tests...")
        start_time = time.time()
        
        try:
            cmd = [
                "poetry", "run", "pytest",
                self.test_config["unit"]["path"],
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
                f"--cov-fail-under={self.test_config['unit']['coverage_threshold']}",
                "--junitxml=unit-test-results.xml",
                "-v",
                "--tb=short"
            ]
            
            if self.parallel:
                cmd.extend(["-n", "auto"])
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_config["unit"]["timeout"]
            )
            
            duration = time.time() - start_time
            
            # Parse results
            tests_run, tests_passed, tests_failed, tests_skipped = self._parse_pytest_output(result.stdout)
            coverage = self._extract_coverage_percentage(result.stdout)
            
            if result.returncode == 0:
                test_result = TestResult.PASSED
                error_message = None
            else:
                test_result = TestResult.FAILED
                error_message = result.stderr
            
            return TestExecutionResult(
                mode=TestMode.UNIT,
                result=test_result,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                coverage_percentage=coverage,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.UNIT,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message="Unit tests timed out"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.UNIT,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message=str(e)
            )
    
    def run_integration_tests(self) -> TestExecutionResult:
        """Run integration tests"""
        self.log("Running integration tests...")
        start_time = time.time()
        
        try:
            cmd = [
                "poetry", "run", "pytest",
                self.test_config["integration"]["path"],
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
                f"--cov-fail-under={self.test_config['integration']['coverage_threshold']}",
                "--junitxml=integration-test-results.xml",
                "-v",
                "--tb=short"
            ]
            
            if self.parallel:
                cmd.extend(["-n", "auto"])
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_config["integration"]["timeout"]
            )
            
            duration = time.time() - start_time
            
            # Parse results
            tests_run, tests_passed, tests_failed, tests_skipped = self._parse_pytest_output(result.stdout)
            coverage = self._extract_coverage_percentage(result.stdout)
            
            if result.returncode == 0:
                test_result = TestResult.PASSED
                error_message = None
            else:
                test_result = TestResult.FAILED
                error_message = result.stderr
            
            return TestExecutionResult(
                mode=TestMode.INTEGRATION,
                result=test_result,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                coverage_percentage=coverage,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.INTEGRATION,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message="Integration tests timed out"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.INTEGRATION,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message=str(e)
            )
    
    def run_e2e_tests(self) -> TestExecutionResult:
        """Run end-to-end tests"""
        self.log("Running E2E tests...")
        start_time = time.time()
        
        try:
            cmd = [
                "poetry", "run", "pytest",
                self.test_config["e2e"]["path"],
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
                f"--cov-fail-under={self.test_config['e2e']['coverage_threshold']}",
                "--junitxml=e2e-test-results.xml",
                "-v",
                "--tb=short"
            ]
            
            if self.parallel:
                cmd.extend(["-n", "auto"])
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_config["e2e"]["timeout"]
            )
            
            duration = time.time() - start_time
            
            # Parse results
            tests_run, tests_passed, tests_failed, tests_skipped = self._parse_pytest_output(result.stdout)
            coverage = self._extract_coverage_percentage(result.stdout)
            
            if result.returncode == 0:
                test_result = TestResult.PASSED
                error_message = None
            else:
                test_result = TestResult.FAILED
                error_message = result.stderr
            
            return TestExecutionResult(
                mode=TestMode.E2E,
                result=test_result,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                coverage_percentage=coverage,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.E2E,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message="E2E tests timed out"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.E2E,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_skipped=0,
                error_message=str(e)
            )
    
    def run_security_tests(self) -> TestExecutionResult:
        """Run security tests"""
        self.log("Running security tests...")
        start_time = time.time()
        
        try:
            cmd = [
                "poetry", "run", "python",
                self.test_config["security"]["path"]
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_config["security"]["timeout"]
            )
            
            duration = time.time() - start_time
            
            # Parse security test results
            if result.returncode == 0:
                test_result = TestResult.PASSED
                tests_run = 1
                tests_passed = 1
                tests_failed = 0
                tests_skipped = 0
                error_message = None
            elif result.returncode == 1:
                test_result = TestResult.FAILED
                tests_run = 1
                tests_passed = 0
                tests_failed = 1
                tests_skipped = 0
                error_message = result.stderr
            else:
                test_result = TestResult.ERROR
                tests_run = 1
                tests_passed = 0
                tests_failed = 0
                tests_skipped = 0
                error_message = result.stderr
            
            return TestExecutionResult(
                mode=TestMode.SECURITY,
                result=test_result,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.SECURITY,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message="Security tests timed out"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.SECURITY,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message=str(e)
            )
    
    def run_performance_tests(self) -> TestExecutionResult:
        """Run performance tests"""
        self.log("Running performance tests...")
        start_time = time.time()
        
        try:
            cmd = [
                "poetry", "run", "pytest",
                self.test_config["performance"]["path"],
                "--junitxml=performance-test-results.xml",
                "-v",
                "--tb=short"
            ]
            
            if self.parallel:
                cmd.extend(["-n", "auto"])
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.test_config["performance"]["timeout"]
            )
            
            duration = time.time() - start_time
            
            # Parse results
            tests_run, tests_passed, tests_failed, tests_skipped = self._parse_pytest_output(result.stdout)
            
            if result.returncode == 0:
                test_result = TestResult.PASSED
                error_message = None
            else:
                test_result = TestResult.FAILED
                error_message = result.stderr
            
            return TestExecutionResult(
                mode=TestMode.PERFORMANCE,
                result=test_result,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.PERFORMANCE,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message="Performance tests timed out"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestExecutionResult(
                mode=TestMode.PERFORMANCE,
                result=TestResult.ERROR,
                duration=duration,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_message=str(e)
            )
    
    def _parse_pytest_output(self, output: str) -> Tuple[int, int, int, int]:
        """Parse pytest output to extract test counts"""
        lines = output.split('\n')
        tests_run = tests_passed = tests_failed = tests_skipped = 0
        
        for line in lines:
            if "failed" in line and "passed" in line:
                # Parse line like "5 failed, 10 passed, 2 skipped in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        if "failed" in line and i > 0 and "failed" in parts[i-1:i+2]:
                            tests_failed = int(part)
                        elif "passed" in line and i > 0 and "passed" in parts[i-1:i+2]:
                            tests_passed = int(part)
                        elif "skipped" in line and i > 0 and "skipped" in parts[i-1:i+2]:
                            tests_skipped = int(part)
        
        tests_run = tests_passed + tests_failed + tests_skipped
        return tests_run, tests_passed, tests_failed, tests_skipped
    
    def _extract_coverage_percentage(self, output: str) -> Optional[float]:
        """Extract coverage percentage from pytest output"""
        lines = output.split('\n')
        for line in lines:
            if "TOTAL" in line and "%" in line:
                # Parse line like "TOTAL                   1000    150    85%"
                parts = line.split()
                for part in parts:
                    if part.endswith('%'):
                        try:
                            return float(part[:-1])
                        except ValueError:
                            continue
        return None
    
    def run_tests(self, mode: TestMode) -> List[TestExecutionResult]:
        """Run tests based on mode"""
        self.log(f"Starting test execution in {mode.value} mode...")
        
        if not self.check_prerequisites():
            self.log("Prerequisites check failed", "ERROR")
            return []
        
        if not self.install_dependencies():
            self.log("Dependency installation failed", "ERROR")
            return []
        
        results = []
        
        if mode == TestMode.UNIT:
            results.append(self.run_unit_tests())
        elif mode == TestMode.INTEGRATION:
            results.append(self.run_integration_tests())
        elif mode == TestMode.E2E:
            results.append(self.run_e2e_tests())
        elif mode == TestMode.SECURITY:
            results.append(self.run_security_tests())
        elif mode == TestMode.PERFORMANCE:
            results.append(self.run_performance_tests())
        elif mode == TestMode.ALL:
            # Run all test types
            results.extend([
                self.run_unit_tests(),
                self.run_integration_tests(),
                self.run_e2e_tests(),
                self.run_security_tests(),
                self.run_performance_tests()
            ])
        elif mode == TestMode.QUICK:
            # Run only unit tests for quick feedback
            results.append(self.run_unit_tests())
        
        self.results.extend(results)
        return results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_tests = sum(r.tests_run for r in self.results)
        total_passed = sum(r.tests_passed for r in self.results)
        total_failed = sum(r.tests_failed for r in self.results)
        total_skipped = sum(r.tests_skipped for r in self.results)
        total_duration = sum(r.duration for r in self.results)
        
        # Calculate overall success rate
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate average coverage
        coverage_results = [r.coverage_percentage for r in self.results if r.coverage_percentage is not None]
        avg_coverage = sum(coverage_results) / len(coverage_results) if coverage_results else None
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "tests_passed": total_passed,
                "tests_failed": total_failed,
                "tests_skipped": total_skipped,
                "success_rate": round(success_rate, 2),
                "total_duration": round(total_duration, 2),
                "average_coverage": round(avg_coverage, 2) if avg_coverage else None,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "results_by_mode": {
                r.mode.value: {
                    "result": r.result.value,
                    "duration": round(r.duration, 2),
                    "tests_run": r.tests_run,
                    "tests_passed": r.tests_passed,
                    "tests_failed": r.tests_failed,
                    "tests_skipped": r.tests_skipped,
                    "coverage_percentage": r.coverage_percentage,
                    "error_message": r.error_message
                }
                for r in self.results
            },
            "overall_status": "PASSED" if all(r.result == TestResult.PASSED for r in self.results) else "FAILED"
        }
        
        return report
    
    def print_summary(self):
        """Print test execution summary"""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("🧪 PAKE SYSTEM TEST EXECUTION SUMMARY")
        print("="*80)
        
        summary = report["summary"]
        print(f"📊 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['tests_passed']}")
        print(f"❌ Failed: {summary['tests_failed']}")
        print(f"⏭️ Skipped: {summary['tests_skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']}%")
        print(f"⏱️ Total Duration: {summary['total_duration']}s")
        
        if summary['average_coverage']:
            print(f"📊 Average Coverage: {summary['average_coverage']}%")
        
        print(f"\n🎯 Overall Status: {report['overall_status']}")
        
        print("\n📋 Results by Test Mode:")
        for mode, result in report["results_by_mode"].items():
            status_emoji = "✅" if result["result"] == "passed" else "❌" if result["result"] == "failed" else "⚠️"
            print(f"  {status_emoji} {mode.upper()}: {result['result'].upper()} "
                  f"({result['tests_passed']}/{result['tests_run']} tests, "
                  f"{result['duration']}s)")
            
            if result["coverage_percentage"]:
                print(f"     Coverage: {result['coverage_percentage']}%")
            
            if result["error_message"]:
                print(f"     Error: {result['error_message'][:100]}...")
        
        print("="*80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Comprehensive Test Runner")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in TestMode],
        default="all",
        help="Test execution mode"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--report-file",
        help="Save detailed report to file"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (unit tests)"
    )
    
    args = parser.parse_args()
    
    # Determine test mode
    if args.quick:
        mode = TestMode.QUICK
    else:
        mode = TestMode(args.mode)
    
    # Create test runner
    runner = PAKETestRunner(verbose=args.verbose, parallel=args.parallel)
    
    # Run tests
    results = runner.run_tests(mode)
    
    # Generate and print report
    runner.print_summary()
    
    # Save report if requested
    if args.report_file:
        report = runner.generate_report()
        with open(args.report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Detailed report saved to: {args.report_file}")
    
    # Exit with appropriate code
    if all(r.result == TestResult.PASSED for r in results):
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
