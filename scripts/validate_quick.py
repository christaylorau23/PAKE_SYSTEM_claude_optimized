#!/usr/bin/env python3
"""
Quick Validation Reference Script
Provides easy access to common validation commands
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n🔧 {description}")
    print(f"Running: {' '.join(command)}")

    try:
        result = subprocess.run(command, cwd=Path(__file__).parent.parent)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Quick Validation")
    parser.add_argument(
        "command",
        choices=[
            "all",
            "quick",
            "lint",
            "format",
            "type-check",
            "security",
            "tests",
            "pre-commit",
            "install-hooks",
            "fix-lint",
            "fix-format",
        ],
        help="Validation command to run",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Define commands
    commands = {
        "all": {
            "command": ["python", "scripts/local_validation.py"],
            "description": "Run complete local validation",
        },
        "quick": {
            "command": ["python", "scripts/local_validation.py", "--quick"],
            "description": "Run quick validation (lint, format, type-check)",
        },
        "lint": {
            "command": ["python", "scripts/validate_lint.py"],
            "description": "Run linting checks",
        },
        "format": {
            "command": ["python", "scripts/validate_lint.py", "--tool", "black"],
            "description": "Check code formatting",
        },
        "type-check": {
            "command": ["python", "scripts/validate_type_check.py"],
            "description": "Run type checking",
        },
        "security": {
            "command": ["python", "scripts/validate_security.py"],
            "description": "Run security checks",
        },
        "tests": {
            "command": ["python", "scripts/validate_tests.py"],
            "description": "Run test suite",
        },
        "pre-commit": {
            "command": ["pre-commit", "run", "--all-files"],
            "description": "Run pre-commit hooks on all files",
        },
        "install-hooks": {
            "command": ["pre-commit", "install"],
            "description": "Install pre-commit hooks",
        },
        "fix-lint": {
            "command": ["python", "scripts/validate_lint.py", "--fix"],
            "description": "Auto-fix linting issues",
        },
        "fix-format": {
            "command": [
                "python",
                "scripts/validate_lint.py",
                "--tool",
                "black",
                "--fix",
            ],
            "description": "Auto-fix formatting issues",
        },
    }

    # Add verbose flag if requested
    if args.verbose and args.command in [
        "all",
        "quick",
        "lint",
        "type-check",
        "security",
        "tests",
    ]:
        commands[args.command]["command"].append("--verbose")

    # Run the command
    if args.command in commands:
        cmd_info = commands[args.command]
        success = run_command(cmd_info["command"], cmd_info["description"])

        if success:
            print(f"\n✅ {args.command} completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ {args.command} failed!")
            sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
