#!/usr/bin/env python3
"""PAKE System - Test Execution Script"""

import argparse
import sys
from pathlib import Path

import pytest


def main():
    parser = argparse.ArgumentParser(description="PAKE System Test Executor")
    parser.add_argument(
        "--level", choices=["unit", "integration", "e2e", "all"], default="all"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Enable coverage reporting"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    # Prepare pytest arguments
    pytest_args = ["-v", "--tb=short", "--maxfail=5"]

    if args.level == "all":
        pytest_args.append(str(tests_dir))
    else:
        test_dir = tests_dir / args.level
        if not test_dir.exists():
            print(f"Test directory not found: {test_dir}")
            sys.exit(1)
        pytest_args.append(str(test_dir))

    # Add coverage if requested
    if args.coverage:
        pytest_args.extend(
            [
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
                "--cov-fail-under=80",
            ]
        )

    # Run tests
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
