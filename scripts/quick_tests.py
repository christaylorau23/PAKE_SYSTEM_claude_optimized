#!/usr/bin/env python3
"""
Quick Tests Script for Pre-commit Hooks
Runs a subset of fast unit tests for immediate feedback
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Run quick unit tests"""
    project_root = Path(__file__).parent.parent

    # Run only fast unit tests (no integration, no E2E)
    cmd = [
        "poetry",
        "run",
        "pytest",
        "tests/unit/",
        "-m",
        "not slow and not requires_db and not requires_redis and not requires_network",
        "--maxfail=3",  # Stop after 3 failures
        "--tb=short",  # Short traceback
        "-q",  # Quiet output
        "--disable-warnings",
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root, timeout=60)
        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        print("Quick tests timed out after 60 seconds")
        sys.exit(1)
    except Exception as e:
        print(f"Error running quick tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
