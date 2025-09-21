#!/usr/bin/env python3
"""
Comprehensive linting script for PAKE System
"""

import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_command(cmd, description):
    """Run a command and log results."""
    logger.info(f"Running {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ {description} passed")
            return True
        logger.error(f"❌ {description} failed:")
        logger.error(result.stderr)
        return False
    except Exception as e:
        logger.error(f"❌ {description} failed with exception: {e}")
        return False


def main():
    """Run all linting checks."""
    project_root = Path(__file__).parent.parent

    checks = [
        ("black --check src/ scripts/", "Black formatting check"),
        ("isort --check-only src/ scripts/", "Import sorting check"),
        ("flake8 src/ scripts/", "Flake8 linting"),
        ("mypy src/", "Type checking"),
        ("bandit -r src/", "Security linting"),
    ]

    passed = 0
    total = len(checks)

    for cmd, description in checks:
        if run_command(cmd, description):
            passed += 1

    logger.info(f"\nLinting Summary: {passed}/{total} checks passed")

    if passed < total:
        sys.exit(1)
    else:
        logger.info("🎉 All linting checks passed!")


if __name__ == "__main__":
    main()
