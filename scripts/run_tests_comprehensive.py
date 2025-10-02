#!/usr/bin/env python3
"""
Comprehensive Test Execution Script for PAKE System

This script provides a unified interface for running all types of tests
with proper configuration, coverage reporting, and result aggregation.

Usage:
    python scripts/run_tests_comprehensive.py --help
    python scripts/run_tests_comprehensive.py --unit --coverage
    python scripts/run_tests_comprehensive.py --integration --database
    python scripts/run_tests_comprehensive.py --e2e --performance
    python scripts/run_tests_comprehensive.py --all --coverage --report
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import pytest
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


class TestRunner:
    """Comprehensive test runner for PAKE System"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.test_results = {}
        self.coverage_data = {}
        
    def setup_environment(self) -> None:
        """Setup test environment variables"""
        env_vars = {
            "PAKE_ENVIRONMENT": "test",
            "PAKE_DEBUG": "true",
            "USE_VAULT": "false",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "DATABASE_URL": "postgresql://test:test@localhost/pake_test",
            "REDIS_URL": "redis://localhost:6379/1",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            
        console.print("✅ Test environment configured", style="green")
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        required_commands = ["poetry", "pytest", "coverage"]
        missing = []
        
        for cmd in required_commands:
            if not self._command_exists(cmd):
                missing.append(cmd)
        
        if missing:
            console.print(f"❌ Missing required commands: {', '.join(missing)}", style="red")
            return False
        
        console.print("✅ All dependencies available", style="green")
        return True
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run([command, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def run_unit_tests(self, categories: List[str] = None, coverage: bool = False) -> Dict:
        """Run unit tests with optional coverage"""
        console.print("\n🧪 Running Unit Tests", style="bold blue")
        
        cmd = ["poetry", "run", "pytest", "tests/unit/", "-v"]
        
        if categories:
            markers = " or ".join(categories)
            cmd.extend(["-m", markers])
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/unit",
                "--cov-report=xml:coverage-unit.xml"
            ])
        
        cmd.extend(["--junitxml=unit-test-results.xml"])
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        end_time = time.time()
        
        return {
            "type": "unit",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "output": result.stdout,
            "error": result.stderr,
            "coverage": coverage
        }
    
    def run_integration_tests(self, categories: List[str] = None, coverage: bool = False) -> Dict:
        """Run integration tests with optional coverage"""
        console.print("\n🔗 Running Integration Tests", style="bold blue")
        
        cmd = ["poetry", "run", "pytest", "tests/integration/", "-v"]
        
        if categories:
            markers = " or ".join(categories)
            cmd.extend(["-m", markers])
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/integration",
                "--cov-report=xml:coverage-integration.xml"
            ])
        
        cmd.extend(["--junitxml=integration-test-results.xml"])
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        end_time = time.time()
        
        return {
            "type": "integration",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "output": result.stdout,
            "error": result.stderr,
            "coverage": coverage
        }
    
    def run_e2e_tests(self, categories: List[str] = None, coverage: bool = False) -> Dict:
        """Run end-to-end tests with optional coverage"""
        console.print("\n🌐 Running End-to-End Tests", style="bold blue")
        
        cmd = ["poetry", "run", "pytest", "tests/e2e/", "-v"]
        
        if categories:
            markers = " or ".join(categories)
            cmd.extend(["-m", markers])
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/e2e",
                "--cov-report=xml:coverage-e2e.xml"
            ])
        
        cmd.extend(["--junitxml=e2e-test-results.xml"])
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        end_time = time.time()
        
        return {
            "type": "e2e",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "output": result.stdout,
            "error": result.stderr,
            "coverage": coverage
        }
    
    def run_security_tests(self) -> Dict:
        """Run security tests"""
        console.print("\n🛡️ Running Security Tests", style="bold blue")
        
        cmd = ["poetry", "run", "python", "scripts/security_test_suite.py"]
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        end_time = time.time()
        
        return {
            "type": "security",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "output": result.stdout,
            "error": result.stderr,
            "coverage": False
        }
    
    def combine_coverage_reports(self) -> Dict:
        """Combine coverage reports from all test types"""
        console.print("\n📊 Combining Coverage Reports", style="bold blue")
        
        cmd = [
            "poetry", "run", "coverage", "combine",
            "coverage-unit.xml",
            "coverage-integration.xml", 
            "coverage-e2e.xml"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Generate combined report
            report_cmd = [
                "poetry", "run", "coverage", "report", "--show-missing"
            ]
            report_result = subprocess.run(report_cmd, cwd=self.project_root, capture_output=True, text=True)
            
            # Generate HTML report
            html_cmd = [
                "poetry", "run", "coverage", "html", "-d", "htmlcov/combined"
            ]
            subprocess.run(html_cmd, cwd=self.project_root, capture_output=True, text=True)
            
            return {
                "success": True,
                "report": report_result.stdout,
                "error": report_result.stderr
            }
        else:
            return {
                "success": False,
                "error": result.stderr
            }
    
    def generate_test_report(self, results: Dict) -> None:
        """Generate comprehensive test report"""
        console.print("\n📋 Test Execution Report", style="bold green")
        
        table = Table(title="Test Results Summary")
        table.add_column("Test Type", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Duration", style="yellow")
        table.add_column("Coverage", style="blue")
        
        total_duration = 0
        success_count = 0
        
        for test_type, result in results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            duration = f"{result['duration']:.2f}s"
            coverage = "📊 YES" if result.get("coverage", False) else "📊 NO"
            
            table.add_row(test_type.title(), status, duration, coverage)
            
            total_duration += result["duration"]
            if result["success"]:
                success_count += 1
        
        console.print(table)
        
        # Summary
        console.print(f"\n📈 Summary:", style="bold")
        console.print(f"  • Total Tests: {len(results)}")
        console.print(f"  • Passed: {success_count}")
        console.print(f"  • Failed: {len(results) - success_count}")
        console.print(f"  • Total Duration: {total_duration:.2f}s")
        console.print(f"  • Success Rate: {(success_count/len(results)*100):.1f}%")
        
        # Save report to file
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(results),
                "passed": success_count,
                "failed": len(results) - success_count,
                "total_duration": total_duration,
                "success_rate": success_count/len(results)*100
            },
            "results": results
        }
        
        report_file = self.project_root / "test-execution-report.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)
        
        console.print(f"\n💾 Report saved to: {report_file}", style="green")
    
    def run_all_tests(self, coverage: bool = False, categories: List[str] = None) -> Dict:
        """Run all test types"""
        console.print("🚀 Running All Tests", style="bold green")
        
        results = {}
        
        # Unit tests
        results["unit"] = self.run_unit_tests(categories, coverage)
        
        # Integration tests
        results["integration"] = self.run_integration_tests(categories, coverage)
        
        # E2E tests
        results["e2e"] = self.run_e2e_tests(categories, coverage)
        
        # Security tests
        results["security"] = self.run_security_tests()
        
        # Combine coverage if requested
        if coverage:
            coverage_result = self.combine_coverage_reports()
            results["coverage"] = coverage_result
        
        return results


@click.command()
@click.option("--unit", is_flag=True, help="Run unit tests")
@click.option("--integration", is_flag=True, help="Run integration tests")
@click.option("--e2e", is_flag=True, help="Run end-to-end tests")
@click.option("--security", is_flag=True, help="Run security tests")
@click.option("--all", is_flag=True, help="Run all test types")
@click.option("--coverage", is_flag=True, help="Generate coverage reports")
@click.option("--report", is_flag=True, help="Generate detailed test report")
@click.option("--categories", help="Comma-separated list of test categories to run")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def main(unit, integration, e2e, security, all, coverage, report, categories, verbose):
    """Comprehensive Test Runner for PAKE System"""
    
    runner = TestRunner(verbose=verbose)
    
    # Setup
    runner.setup_environment()
    
    if not runner.check_dependencies():
        sys.exit(1)
    
    # Parse categories
    test_categories = None
    if categories:
        test_categories = [cat.strip() for cat in categories.split(",")]
    
    # Determine which tests to run
    if all:
        results = runner.run_all_tests(coverage=coverage, categories=test_categories)
    else:
        results = {}
        
        if unit:
            results["unit"] = runner.run_unit_tests(test_categories, coverage)
        
        if integration:
            results["integration"] = runner.run_integration_tests(test_categories, coverage)
        
        if e2e:
            results["e2e"] = runner.run_e2e_tests(test_categories, coverage)
        
        if security:
            results["security"] = runner.run_security_tests()
        
        if not results:
            console.print("❌ No test types specified. Use --help for options.", style="red")
            sys.exit(1)
    
    # Generate report
    if report or all:
        runner.generate_test_report(results)
    
    # Check for failures
    failed_tests = [test_type for test_type, result in results.items() 
                   if not result.get("success", True)]
    
    if failed_tests:
        console.print(f"\n❌ Tests failed: {', '.join(failed_tests)}", style="red")
        sys.exit(1)
    else:
        console.print("\n✅ All tests passed!", style="green")


if __name__ == "__main__":
    main()
