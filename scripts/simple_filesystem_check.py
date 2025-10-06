#!/usr/bin/env python3
"""
PAKE System - Simple Filesystem Issue Detection
==============================================

Quick detection of common filesystem issues that cause CI failures.
"""

import os
from pathlib import Path
import re
import sys


def check_case_sensitivity_issues(self) -> None:
    """Check for case sensitivity issues in imports"""
    print("🔍 Checking for case sensitivity issues...")

    issues = []
    root = Path.cwd()

    # Check for problematic directory names with hyphens
    problematic_dirs = [
        "src/services/secrets-manager",
        "src/services/agent-runtime",
        "src/services/enterprise-integrations",
        "src/services/social-media-automation",
        "src/services/video-generation",
        "src/services/voice-agents",
    ]

    for dir_path in problematic_dirs:
        full_path = root / dir_path
        if full_path.exists():
            print(f"⚠️  Found directory with hyphens: {dir_path}")
            issues.append(f"Directory with hyphens: {dir_path}")

    return issues


def check_hardcoded_paths(self) -> None:
    """Check for hardcoded absolute paths"""
    print("🛤️ Checking for hardcoded paths...")

    issues = []
    root = Path.cwd()

    # Look for hardcoded paths in Python files
    for py_file in root.rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Check for hardcoded Windows paths
                if "/d/Projects/" in line or "/c/" in line.lower():
                    issues.append(f"Hardcoded path in {py_file}:{i} - {line.strip()}")
                    print(f"⚠️  Hardcoded path: {py_file}:{i}")

                # Check for sys.path.append with hardcoded paths
                if "sys.path.append(" in line and ("/d/" in line or "/c/" in line):
                    issues.append(
                        f"sys.path.append with hardcoded path in {py_file}:{i} - {line.strip()}"
                    )
                    print(f"⚠️  sys.path.append with hardcoded path: {py_file}:{i}")

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error reading {py_file}: {e}")

    return issues


def check_import_patterns(self) -> None:
    """Check for problematic import patterns"""
    print("📦 Checking import patterns...")

    issues = []
    root = Path.cwd()

    # Check for imports that might fail on case-sensitive filesystems
    for py_file in root.rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Check for imports from directories with hyphens
                if "from src.services.secrets-manager" in line:
                    issues.append(f"Import from hyphenated directory in {py_file}:{i}")
                    print(f"⚠️  Import from hyphenated directory: {py_file}:{i}")

                if "from src.services.agent-runtime" in line:
                    issues.append(f"Import from hyphenated directory in {py_file}:{i}")
                    print(f"⚠️  Import from hyphenated directory: {py_file}:{i}")

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error reading {py_file}: {e}")

    return issues


def main(self) -> None:
    """Main function"""
    print("=" * 60)
    print("PAKE SYSTEM - FILESYSTEM ISSUE DETECTION")
    print("=" * 60)

    all_issues = []

    # Run checks
    all_issues.extend(check_case_sensitivity_issues())
    all_issues.extend(check_hardcoded_paths())
    all_issues.extend(check_import_patterns())

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all_issues:
        print(f"Found {len(all_issues)} potential issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")

        print("\n💡 RECOMMENDATIONS:")
        print("1. Replace hyphens with underscores in directory names")
        print("2. Remove hardcoded absolute paths")
        print("3. Use relative imports instead of sys.path manipulation")
        print("4. Test imports on case-sensitive filesystem")

        return 1
    print("✅ No obvious filesystem issues found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())