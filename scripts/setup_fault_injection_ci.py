#!/usr/bin/env python3
"""
PAKE System - CI Pipeline Configuration for Fault Injection Testing
Ensures fault injection tests are included in CI pipeline validation
"""

import os
from pathlib import Path
import subprocess
import sys
from typing import List, Optional

import pytest


class FaultInjectionCIRunner:
    """CI runner for fault injection tests"""

def __init__(self, test_dir: Any = None) -> None:
        self.test_dir = Path(test_dir)
        self.fault_injection_tests = self.test_dir / "test_fault_injection.py"
        self.config_file = self.test_dir / "fault_injection_config.py"

    def validate_test_files_exist(self) -> bool:
        """Validate that fault injection test files exist"""
        if not self.fault_injection_tests.exists():
            print(
                f"❌ Fault injection test file not found: {self.fault_injection_tests}"
            )
            return False

        if not self.config_file.exists():
            print(f"❌ Fault injection config file not found: {self.config_file}")
            return False

        print("✅ Fault injection test files exist")
        return True

    def run_fault_injection_tests(
        self,
        markers: list[str] | None = None,
        verbose: bool = True,
        parallel: bool = False,
    ) -> bool:
        """Run fault injection tests with specified configuration"""
        if not self.validate_test_files_exist():
            return False

        # Build pytest command
        cmd = [sys.executable, "-m", "pytest"]

        if verbose:
            cmd.extend(["-vv", "--tb=short"])

        if parallel:
            cmd.extend(["-n", "auto"])

        # Add fault injection specific markers
        if markers:
            marker_expr = " or ".join(markers)
            cmd.extend(["-m", marker_expr])
        else:
            cmd.extend(["-m", "fault_injection"])

        # Add test file
        cmd.append(str(self.fault_injection_tests))

        # Add coverage for fault injection tests
        cmd.extend(
            [
                "--cov=src.services.ingestion",
                "--cov-report=term-missing",
                "--cov-report=xml:coverage-fault-injection.xml",
            ]
        )

        # Add timeout for fault injection tests
        cmd.extend(["--timeout=300"])

        print(f"Running fault injection tests: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                print("✅ Fault injection tests passed")
                print(result.stdout)
                return True
            print("❌ Fault injection tests failed")
            print(result.stdout)
            print(result.stderr)
            return False

        except subprocess.TimeoutExpired:
            print("❌ Fault injection tests timed out")
            return False
        except (ValueError, RuntimeError) as e:
            print(f"❌ Error running fault injection tests: {e}")
            return False

    def run_resilience_tests(self) -> bool:
        """Run resilience-specific tests"""
        return self.run_fault_injection_tests(
            markers=["resilience_testing", "fault_injection"], verbose=True
        )

    def run_external_api_tests(self) -> bool:
        """Run external API fault injection tests"""
        return self.run_fault_injection_tests(
            markers=["external_api_testing", "fault_injection"], verbose=True
        )

    def run_all_fault_tests(self) -> bool:
        """Run all fault injection tests"""
        return self.run_fault_injection_tests(
            markers=["fault_injection", "resilience_testing", "external_api_testing"],
            verbose=True,
            parallel=True,
        )


def create_ci_script(self) -> None:
    """Create CI script for fault injection testing"""
    script_content = """#!/bin/bash
# PAKE System - CI Script for Fault Injection Testing
# This script ensures fault injection tests are run in CI pipeline

set -e

echo "🚀 Starting Fault Injection Testing CI Pipeline"

# Check if we're in CI environment
if [ -n "$CI" ]; then
    echo "✅ Running in CI environment"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
else
    echo "⚠️  Not in CI environment - setting up local test environment"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -e ".[dev]"

# Run fault injection tests
echo "🧪 Running fault injection tests..."
python -m pytest tests/integration/test_fault_injection.py \\
    -m "fault_injection" \\
    -vv \\
    --tb=short \\
    --timeout=300 \\
    --cov=src.services.ingestion \\
    --cov-report=term-missing \\
    --cov-report=xml:coverage-fault-injection.xml \\
    --junitxml=test-results-fault-injection.xml

# Check test results
if [ $? -eq 0 ]; then
    echo "✅ Fault injection tests passed"
    exit 0
else
    echo "❌ Fault injection tests failed"
    exit 1
fi
"""

    script_path = Path("scripts/ci_fault_injection_tests.sh")
    script_path.parent.mkdir(exist_ok=True)

    with open(script_path, "w") as f:
        f.write(script_content)

    # Make script executable
    os.chmod(script_path, 0o755)

    print(f"✅ Created CI script: {script_path}")
    return script_path


def create_github_workflow(self) -> None:
    """Create GitHub Actions workflow for fault injection testing"""
    workflow_content = """name: Fault Injection Testing

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'src/services/ingestion/**'
      - 'tests/integration/test_fault_injection.py'
      - 'tests/integration/fault_injection_config.py'
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'src/services/ingestion/**'
      - 'tests/integration/test_fault_injection.py'
      - 'tests/integration/fault_injection_config.py'

jobs:
  fault-injection-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    strategy:
      matrix:
        python-version: [3.12]
        test-type: [unit, integration, resilience]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Run fault injection tests
      run: |
        python -m pytest tests/integration/test_fault_injection.py \\
          -m "fault_injection and ${{ matrix.test-type }}" \\
          -vv \\
          --tb=short \\
          --timeout=300 \\
          --cov=src.services.ingestion \\
          --cov-report=xml:coverage-fault-injection-${{ matrix.test-type }}.xml \\
          --junitxml=test-results-fault-injection-${{ matrix.test-type }}.xml

    - name: Upload coverage to Codecov
      if: matrix.test-type == 'integration'
      uses: codecov/codecov-action@v3
      with:
        file: coverage-fault-injection-integration.xml
        flags: fault-injection
        name: fault-injection-coverage

    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: fault-injection-test-results-${{ matrix.test-type }}
        path: |
          test-results-fault-injection-${{ matrix.test-type }}.xml
          coverage-fault-injection-${{ matrix.test-type }}.xml

  resilience-validation:
    runs-on: ubuntu-latest
    needs: fault-injection-tests
    timeout-minutes: 15

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v4
      with:
        python-version: 3.12

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Validate system resilience
      run: |
        python -c "
        import sys
        sys.path.append('src')
        from tests.integration.fault_injection_config import FaultInjectionCIRunner

        runner = FaultInjectionCIRunner()
        success = runner.run_resilience_tests()

        if not success:
            print('❌ Resilience validation failed')
            sys.exit(1)
        else:
            print('✅ System resilience validated')
        "
"""

    workflow_path = Path(".github/workflows/fault-injection-tests.yml")
    workflow_path.parent.mkdir(parents=True, exist_ok=True)

    with open(workflow_path, "w") as f:
        f.write(workflow_content)

    print(f"✅ Created GitHub workflow: {workflow_path}")
    return workflow_path


def create_pytest_config(self) -> None:
    """Create pytest configuration for fault injection tests"""
    pytest_ini_content = """[tool:pytest]
# Fault Injection Test Configuration

# Test markers
markers =
    fault_injection: Fault injection tests for API resilience
    resilience_testing: Tests for system resilience
    external_api_testing: Tests requiring external API access
    requires_network: Tests requiring network connectivity

# Test discovery
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Fault injection specific configuration
addopts =
    -ra
    --strict-markers
    --strict-config
    --timeout=300
    --maxfail=5
    --durations=10

# Coverage configuration for fault injection
[tool:coverage:run]
source = src
omit =
    */tests/*
    */test_*
    */__pycache__/*

[tool:coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    raise AssertionError
    raise NotImplementedError
"""

    pytest_ini_path = Path("pytest-fault-injection.ini")

    with open(pytest_ini_path, "w") as f:
        f.write(pytest_ini_content)

    print(f"✅ Created pytest configuration: {pytest_ini_path}")
    return pytest_ini_path


def main(self) -> None:
    """Main function to set up CI pipeline for fault injection testing"""
    print("🔧 Setting up CI Pipeline for Fault Injection Testing")

    # Create CI script
    ci_script = create_ci_script()

    # Create GitHub workflow
    github_workflow = create_github_workflow()

    # Create pytest configuration
    pytest_config = create_pytest_config()

    # Test the setup
    runner = FaultInjectionCIRunner()

    if runner.validate_test_files_exist():
        print("✅ CI pipeline setup complete")
        print("📝 Files created:")
        print(f"   - {ci_script}")
        print(f"   - {github_workflow}")
        print(f"   - {pytest_config}")
        print("\n🚀 To run fault injection tests:")
        print(f"   bash {ci_script}")
        print("\n🧪 To run specific test types:")
        print(
            "   python -m pytest tests/integration/test_fault_injection.py -m fault_injection"
        )
        print(
            "   python -m pytest tests/integration/test_fault_injection.py -m resilience_testing"
        )
        print(
            "   python -m pytest tests/integration/test_fault_injection.py -m external_api_testing"
        )
    else:
        print("❌ CI pipeline setup failed - test files missing")
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
