#!/usr/bin/env python3
"""
Pre-commit hook to validate secrets manager usage
Ensures proper use of enterprise secrets manager instead of hardcoded fallbacks
"""

import re
import sys
from pathlib import Path


def validate_secrets_manager_usage():
    """Validate that secrets manager is used instead of hardcoded fallbacks"""

    # Patterns that indicate improper secret handling
    IMPROPER_PATTERNS = [
        # os.getenv with hardcoded fallbacks
        (
            r'os\.getenv\s*\(\s*["\'][^"\']+["\']\s*,\s*["\'][^"\']+["\']\s*\)',
            "os.getenv with hardcoded fallback",
        ),
        # os.environ.get with hardcoded fallbacks
        (
            r'os\.environ\.get\s*\(\s*["\'][^"\']+["\']\s*,\s*["\'][^"\']+["\']\s*\)',
            "os.environ.get with hardcoded fallback",
        ),
        # Direct environment variable access with fallbacks
        (
            r'os\.environ\[["\'][^"\']+["\']\]\s*or\s*["\'][^"\']+["\']',
            "Direct environment access with fallback",
        ),
    ]

    # Get staged Python files
    staged_files = get_staged_python_files()

    violations = []

    for file_path in staged_files:
        if not file_path.exists():
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    for pattern, description in IMPROPER_PATTERNS:
                        if re.search(pattern, line):
                            # Skip if it's clearly a test or example
                            if any(
                                word in line.lower()
                                for word in [
                                    "test",
                                    "example",
                                    "placeholder",
                                    "mock",
                                    "fake",
                                ]
                            ):
                                continue

                            violations.append(
                                {
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.strip(),
                                    "description": description,
                                    "pattern": pattern,
                                }
                            )

        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            continue

    if violations:
        print("🚨 IMPROPER SECRET HANDLING DETECTED!", file=sys.stderr)
        print("", file=sys.stderr)

        for violation in violations:
            print(f"❌ {violation['description']}", file=sys.stderr)
            print(f"   File: {violation['file']}:{violation['line']}", file=sys.stderr)
            print(f"   Content: {violation['content']}", file=sys.stderr)
            print("", file=sys.stderr)

        print("🔧 REMEDIATION:", file=sys.stderr)
        print(
            "Replace hardcoded fallbacks with enterprise secrets manager:",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print("❌ BAD:", file=sys.stderr)
        print("   api_key = os.getenv('API_KEY', 'default-api-key')", file=sys.stderr)
        print("", file=sys.stderr)
        print("✅ GOOD:", file=sys.stderr)
        print(
            "   from src.services.secrets_manager.enterprise_secrets_manager import get_api_key",
            file=sys.stderr,
        )
        print("   api_key = await get_api_key()", file=sys.stderr)
        print("", file=sys.stderr)
        print("Or use fail-fast approach:", file=sys.stderr)
        print("   api_key = os.getenv('API_KEY')", file=sys.stderr)
        print("   if not api_key:", file=sys.stderr)
        print(
            "       raise ValueError('API_KEY environment variable is required')",
            file=sys.stderr,
        )
        print("", file=sys.stderr)

        return False

    print("✅ Proper secrets management detected")
    return True


def get_staged_python_files():
    """Get list of staged Python files"""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", "*.py"],
            capture_output=True,
            text=True,
            check=True,
        )

        staged_files = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                staged_files.append(Path(line.strip()))

        return staged_files

    except subprocess.CalledProcessError as e:
        print(f"Error getting staged Python files: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    success = validate_secrets_manager_usage()
    sys.exit(0 if success else 1)
