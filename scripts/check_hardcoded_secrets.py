#!/usr/bin/env python3
"""
Pre-commit hook to check for hardcoded secrets
Prevents hardcoded secrets from being committed to the repository
"""

import re
import sys
from pathlib import Path


def check_hardcoded_secrets():
    """Check for hardcoded secrets in staged files"""

    # Patterns that indicate hardcoded secrets
    FORBIDDEN_PATTERNS = [
        # API keys with hardcoded values
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
        (r'api[_-]?key\s*=\s*["\'][^"\']*api[_-]?key[^"\']*["\']', "Hardcoded API key"),
        # Secrets with hardcoded values
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
        (r'secret\s*=\s*["\'][^"\']*secret[^"\']*["\']', "Hardcoded secret"),
        # Passwords with hardcoded values
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'password\s*=\s*["\'][^"\']*password[^"\']*["\']', "Hardcoded password"),
        # Tokens with hardcoded values
        (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
        (r'token\s*=\s*["\'][^"\']*token[^"\']*["\']', "Hardcoded token"),
        # Keys with hardcoded values
        (r'key\s*=\s*["\'][^"\']+["\']', "Hardcoded key"),
        (r'key\s*=\s*["\'][^"\']*key[^"\']*["\']', "Hardcoded key"),
        # Specific dangerous patterns
        (r'["\']default[_-]?api[_-]?key["\']', "Dangerous default API key"),
        (r'["\']your[_-]?secret[_-]?key["\']', "Dangerous placeholder secret"),
        (r'["\']secure[_-]?default[_-]?value["\']', "Dangerous default value"),
        (r'["\']password["\']', "Dangerous default password"),
    ]

    # Get staged files
    staged_files = get_staged_files()

    violations = []

    for file_path in staged_files:
        if not file_path.exists():
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    for pattern, description in FORBIDDEN_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
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
        print("🚨 HARDCODED SECRETS DETECTED!", file=sys.stderr)
        print("", file=sys.stderr)

        for violation in violations:
            print(f"❌ {violation['description']}", file=sys.stderr)
            print(f"   File: {violation['file']}:{violation['line']}", file=sys.stderr)
            print(f"   Content: {violation['content']}", file=sys.stderr)
            print("", file=sys.stderr)

        print("🔧 REMEDIATION:", file=sys.stderr)
        print("1. Remove hardcoded values", file=sys.stderr)
        print("2. Use environment variables or Azure Key Vault", file=sys.stderr)
        print("3. Use the enterprise secrets manager:", file=sys.stderr)
        print(
            "   from src.services.secrets_manager.enterprise_secrets_manager import get_api_key",
            file=sys.stderr,
        )
        print("", file=sys.stderr)

        return False

    print("✅ No hardcoded secrets detected")
    return True


def get_staged_files():
    """Get list of staged files"""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
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
        print(f"Error getting staged files: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    success = check_hardcoded_secrets()
    sys.exit(0 if success else 1)
