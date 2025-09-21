#!/usr/bin/env python3
"""
PAKE System - Unified Test Runner
Provides comprehensive test execution with coverage reporting and parallel execution.
Integrates with pyproject.toml pytest configuration for unified testing approach.

Usage:
    python scripts/run_tests.py --help
    python scripts/run_tests.py unit
    python scripts/run_tests.py integration
    python scripts/run_tests.py e2e
    python scripts/run_tests.py all
    python scripts/run_tests.py --coverage
    python scripts/run_tests.py --parallel
    python scripts/run_tests.py --performance
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Unified test runner for PAKE System integrating with pyproject.toml configuration"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"

        # Base pytest command that uses pyproject.toml configuration
        self.base_pytest_cmd = [
            "python", "-m", "pytest",
            "--tb=short",  # Override for consistent short traceback
        ]
        
    def run_command(self, command: List[str], description: str) -> bool:
        """Run a command and return success status"""
        print(f"\n🔄 {description}")
        print(f"Command: {' '.join(command)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            execution_time = time.time() - start_time
            
            print(f"✅ {description} completed successfully")
            print(f"⏱️  Execution time: {execution_time:.2f} seconds")
            
            if result.stdout:
                print("📋 Output:")
                print(result.stdout)
            
            return True
            
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            print(f"❌ {description} failed")
            print(f"⏱️  Execution time: {execution_time:.2f} seconds")
            print(f"🔢 Exit code: {e.returncode}")
            
            if e.stdout:
                print("📋 Output:")
                print(e.stdout)
            
            if e.stderr:
                print("🚨 Error:")
                print(e.stderr)
            
            return False
    
    def run_unit_tests(self, coverage: bool = False, performance: bool = False, parallel: bool = False) -> bool:
        """Run unit tests (Testing Pyramid base - 70% of tests)"""
        command = self.base_pytest_cmd.copy()
        command.extend([
            "tests/unit/",
            "-m", "unit"
        ])

        if parallel:
            command.extend(["-n", "auto"])

        if coverage:
            # pyproject.toml already configures coverage, but we can override for specific runs
            command.extend(["--cov=src", "--cov-report=term-missing", "--cov-report=html"])

        if performance:
            command.extend(["--durations=10"])

        return self.run_command(command, "Running Unit Tests (Testing Pyramid Base)")
    
    def run_integration_tests(self, performance: bool = False, parallel: bool = False) -> bool:
        """Run integration tests (Testing Pyramid middle - 20% of tests)"""
        command = self.base_pytest_cmd.copy()
        command.extend([
            "tests/integration/",
            "-m", "integration"
        ])

        if parallel:
            command.extend(["-n", "auto"])

        if performance:
            command.extend(["--durations=10"])

        return self.run_command(command, "Running Integration Tests (Testing Pyramid Middle)")
    
    def run_e2e_tests(self, performance: bool = False, parallel: bool = False) -> bool:
        """Run end-to-end tests (Testing Pyramid top - 10% of tests)"""
        command = self.base_pytest_cmd.copy()
        command.extend([
            "tests/e2e/",
            "-m", "e2e"
        ])

        if parallel:
            # E2E tests typically shouldn't run in parallel as they might interfere
            # but allow override if requested
            command.extend(["-n", "2"])  # Limited parallelism for E2E

        if performance:
            command.extend(["--durations=10"])

        return self.run_command(command, "Running End-to-End Tests (Testing Pyramid Top)")
    
    def run_all_tests(self, coverage: bool = False, performance: bool = False, parallel: bool = False) -> bool:
        """Run all tests following Testing Pyramid order"""
        print("🏗️  Running Complete Testing Pyramid")
        print("=" * 50)

        # Run tests in Testing Pyramid order
        success = True

        # 1. Unit Tests (70% - Base of pyramid)
        print("\n📊 Layer 1: Unit Tests (70% of tests)")
        print("-" * 30)
        if not self.run_unit_tests(coverage=coverage, performance=performance, parallel=parallel):
            success = False

        # 2. Integration Tests (20% - Middle of pyramid)
        print("\n🔗 Layer 2: Integration Tests (20% of tests)")
        print("-" * 30)
        if not self.run_integration_tests(performance=performance, parallel=parallel):
            success = False

        # 3. E2E Tests (10% - Top of pyramid)
        print("\n🎯 Layer 3: End-to-End Tests (10% of tests)")
        print("-" * 30)
        if not self.run_e2e_tests(performance=performance, parallel=parallel):
            success = False

        return success

    def run_comprehensive_tests(self, parallel: bool = True) -> bool:
        """Run comprehensive test suite using pyproject.toml configuration"""
        print("🚀 Running Comprehensive Test Suite")
        print("=" * 50)
        print("📋 Using unified pytest configuration from pyproject.toml")

        command = self.base_pytest_cmd.copy()
        command.extend([
            "tests/",  # Run all tests
            # pyproject.toml configuration will be automatically applied
        ])

        if parallel:
            command.extend(["-n", "auto"])

        return self.run_command(command, "Running Comprehensive Test Suite with Coverage")
    
    def run_specific_tests(self, test_path: str, coverage: bool = False, parallel: bool = False) -> bool:
        """Run specific test file or directory"""
        command = self.base_pytest_cmd.copy()
        command.append(test_path)

        if parallel:
            command.extend(["-n", "auto"])

        if coverage:
            command.extend(["--cov=src", "--cov-report=term-missing"])

        return self.run_command(command, f"Running Specific Tests: {test_path}")

    def run_tests_by_marker(self, marker: str, coverage: bool = False, parallel: bool = False) -> bool:
        """Run tests with specific marker"""
        command = self.base_pytest_cmd.copy()
        command.extend([
            "tests/",
            "-m", marker
        ])

        if parallel:
            command.extend(["-n", "auto"])

        if coverage:
            command.extend(["--cov=src", "--cov-report=term-missing"])

        return self.run_command(command, f"Running Tests with Marker: {marker}")
    
    def run_linting_tests(self) -> bool:
        """Run linting and code quality tests"""
        print("\n🔍 Running Code Quality Tests")
        print("=" * 30)
        
        success = True
        
        # Python linting
        if not self.run_command(
            ["python", "-m", "ruff", "check", "src/", "tests/", "scripts/"],
            "Python Linting (Ruff)"
        ):
            success = False
        
        # Python formatting check
        if not self.run_command(
            ["python", "-m", "ruff", "format", "--check", "src/", "tests/", "scripts/"],
            "Python Formatting Check (Ruff)"
        ):
            success = False
        
        # TypeScript linting
        if not self.run_command(
            ["npm", "run", "lint:typescript"],
            "TypeScript Linting (ESLint)"
        ):
            success = False
        
        return success
    
    def run_quick_tests(self) -> bool:
        """Run quick smoke tests for development"""
        command = [
            "python", "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-m", "smoke",
            "--maxfail=3"
        ]
        
        return self.run_command(command, "Running Quick Smoke Tests")
    
    def show_test_statistics(self):
        """Show test statistics and coverage information"""
        print("\n📊 Test Statistics")
        print("=" * 20)
        
        # Count tests by layer
        unit_tests = len(list((self.test_dir / "unit").rglob("test_*.py")))
        integration_tests = len(list((self.test_dir / "integration").rglob("test_*.py")))
        e2e_tests = len(list((self.test_dir / "e2e").rglob("test_*.py")))
        total_tests = unit_tests + integration_tests + e2e_tests
        
        print(f"Unit Tests: {unit_tests} files")
        print(f"Integration Tests: {integration_tests} files")
        print(f"E2E Tests: {e2e_tests} files")
        print(f"Total Test Files: {total_tests}")
        
        # Calculate Testing Pyramid distribution
        if total_tests > 0:
            unit_percentage = (unit_tests / total_tests) * 100
            integration_percentage = (integration_tests / total_tests) * 100
            e2e_percentage = (e2e_tests / total_tests) * 100
            
            print(f"\nTesting Pyramid Distribution:")
            print(f"Unit Tests: {unit_percentage:.1f}% (Target: 70%)")
            print(f"Integration Tests: {integration_percentage:.1f}% (Target: 20%)")
            print(f"E2E Tests: {e2e_percentage:.1f}% (Target: 10%)")
            
            # Check if distribution follows Testing Pyramid
            if unit_percentage >= 60 and integration_percentage <= 30 and e2e_percentage <= 20:
                print("✅ Testing Pyramid distribution is optimal")
            else:
                print("⚠️  Testing Pyramid distribution could be improved")
    
    def check_test_environment(self) -> bool:
        """Check if test environment is properly set up"""
        print("\n🔧 Checking Test Environment")
        print("=" * 25)
        
        success = True
        
        # Check Python version
        try:
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Python: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print("❌ Python not found or not working")
            success = False
        
        # Check pytest installation
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Pytest: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print("❌ Pytest not installed")
            success = False
        
        # Check test directories
        if (self.test_dir / "unit").exists():
            print("✅ Unit tests directory exists")
        else:
            print("❌ Unit tests directory missing")
            success = False
        
        if (self.test_dir / "integration").exists():
            print("✅ Integration tests directory exists")
        else:
            print("❌ Integration tests directory missing")
            success = False
        
        if (self.test_dir / "e2e").exists():
            print("✅ E2E tests directory exists")
        else:
            print("❌ E2E tests directory missing")
            success = False
        
        return success


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(
        description="PAKE System Multi-Layered Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py                  # Run comprehensive test suite (default)
  python scripts/run_tests.py --comprehensive  # Run comprehensive tests with pyproject.toml config
  python scripts/run_tests.py unit             # Run unit tests only
  python scripts/run_tests.py integration      # Run integration tests only
  python scripts/run_tests.py e2e              # Run E2E tests only
  python scripts/run_tests.py all              # Run all tests (Testing Pyramid order)
  python scripts/run_tests.py --coverage       # Run with coverage report
  python scripts/run_tests.py --parallel       # Run tests in parallel
  python scripts/run_tests.py --performance    # Run with performance metrics
  python scripts/run_tests.py --comprehensive --parallel  # Fast comprehensive testing
  python scripts/run_tests.py --quick          # Run quick smoke tests
  python scripts/run_tests.py --lint           # Run linting tests only
  python scripts/run_tests.py --stats          # Show test statistics
  python scripts/run_tests.py --check-env      # Check test environment
        """
    )
    
    parser.add_argument(
        "test_layer",
        nargs="?",
        choices=["unit", "integration", "e2e", "all"],
        help="Test layer to run (unit, integration, e2e, or all)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Show performance metrics"
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel for better performance"
    )

    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive test suite using pyproject.toml configuration"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick smoke tests"
    )
    
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting tests only"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show test statistics"
    )
    
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check test environment setup"
    )
    
    parser.add_argument(
        "--test-path",
        help="Run specific test file or directory"
    )
    
    parser.add_argument(
        "--marker",
        help="Run tests with specific marker"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Handle special commands
    if args.check_env:
        success = runner.check_test_environment()
        sys.exit(0 if success else 1)
    
    if args.stats:
        runner.show_test_statistics()
        sys.exit(0)
    
    if args.lint:
        success = runner.run_linting_tests()
        sys.exit(0 if success else 1)
    
    if args.quick:
        success = runner.run_quick_tests()
        sys.exit(0 if success else 1)

    if args.comprehensive:
        success = runner.run_comprehensive_tests(args.parallel)
        sys.exit(0 if success else 1)

    # Handle test execution
    success = True

    if args.test_path:
        success = runner.run_specific_tests(args.test_path, args.coverage, args.parallel)
    elif args.marker:
        success = runner.run_tests_by_marker(args.marker, args.coverage, args.parallel)
    elif args.test_layer == "unit":
        success = runner.run_unit_tests(args.coverage, args.performance, args.parallel)
    elif args.test_layer == "integration":
        success = runner.run_integration_tests(args.performance, args.parallel)
    elif args.test_layer == "e2e":
        success = runner.run_e2e_tests(args.performance, args.parallel)
    elif args.test_layer == "all":
        success = runner.run_all_tests(args.coverage, args.performance, args.parallel)
    else:
        # Default: run comprehensive tests with pyproject.toml configuration
        print("🚀 Running Comprehensive Test Suite (default)")
        success = runner.run_comprehensive_tests(args.parallel)
    
    # Show final results
    if success:
        print("\n🎉 All tests completed successfully!")
        print("✅ PAKE System testing pyramid validation passed")
    else:
        print("\n💥 Some tests failed!")
        print("❌ Please review the test failures above")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
