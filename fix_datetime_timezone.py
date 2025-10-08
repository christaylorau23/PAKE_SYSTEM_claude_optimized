#!/usr/bin/env python3
"""Fix datetime timezone issues - make all datetime operations timezone-aware."""

from pathlib import Path
import re
import subprocess


def fix_file(file_path: Path) -> tuple[bool, int]:
    """Fix datetime timezone issues in a single file.

    Returns:
        Tuple of (was_modified, num_fixes)
    """
    try:
        content = file_path.read_text()
        original_content = content
        fixes = 0

        # Check if file uses datetime
        if "datetime" not in content:
            return False, 0

        # Ensure UTC/timezone imports
        has_datetime_import = bool(
            re.search(r"^from datetime import.*datetime", content, re.MULTILINE)
        )
        has_timezone_import = bool(
            re.search(r"from datetime import.*timezone", content, re.MULTILINE)
            or re.search(r"from datetime import.*UTC", content, re.MULTILINE)
        )

        if has_datetime_import and not has_timezone_import:
            # Add timezone/UTC to existing datetime import
            content = re.sub(
                r"^from datetime import (.*?)$",
                lambda m: f"from datetime import {m.group(1)}, UTC"
                if "UTC" not in m.group(1)
                else m.group(0),
                content,
                flags=re.MULTILINE,
            )
            if content != original_content:
                fixes += 1
                original_content = content

        # Fix datetime.datetime.utcnow() → datetime.now(UTC)
        pattern1 = r"\bdatetime\.datetime\.utcnow\(\)"
        replacement1 = "datetime.now(UTC)"
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            fixes += re.findall(pattern1, original_content).__len__()
            original_content = content

        # Fix datetime.utcnow() → datetime.now(UTC)
        pattern2 = r"\bdatetime\.utcnow\(\)"
        replacement2 = "datetime.now(UTC)"
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            fixes += re.findall(pattern2, original_content).__len__()
            original_content = content

        # Fix datetime.datetime.now() without tz → datetime.now(UTC)
        # Match datetime.datetime.now() that doesn't already have (UTC)
        pattern3 = r"\bdatetime\.datetime\.now\(\)(?!\s*\(UTC\))"
        if re.search(pattern3, content):
            content = re.sub(pattern3, "datetime.now(UTC)", content)
            fixes += len(re.findall(pattern3, original_content))
            original_content = content

        # Fix datetime.now() without tz → datetime.now(UTC)
        # Match datetime.now() that doesn't already have (UTC)
        pattern4 = r"\bdatetime\.now\(\)(?!\s*\(UTC\))"
        if re.search(pattern4, content):
            content = re.sub(pattern4, "datetime.now(UTC)", content)
            fixes += len(re.findall(pattern4, original_content))
            original_content = content

        # Fix datetime.datetime.fromtimestamp() → datetime.fromtimestamp(..., tz=UTC)
        # Only match if it doesn't already have tz= in the arguments
        pattern5 = r"datetime\.datetime\.fromtimestamp\(([^)]*(?<!tz=)[^)]*)\)(?!\s*\.)"
        pattern5_matches = re.findall(pattern5, content)
        for match in pattern5_matches:
            if "tz=" not in match:  # Double-check the arguments
                old = f"datetime.datetime.fromtimestamp({match})"
                new = f"datetime.fromtimestamp({match}, tz=UTC)"
                content = content.replace(old, new, 1)
                fixes += 1
        original_content = content

        # Fix datetime.fromtimestamp() → datetime.fromtimestamp(..., tz=UTC)
        # Only match if it doesn't already have tz= in the arguments
        pattern6 = r"(?<!\.)\bdatetime\.fromtimestamp\(([^)]*)\)"
        pattern6_matches = re.findall(pattern6, content)
        for match in pattern6_matches:
            if "tz=" not in match:  # Only fix if no tz parameter
                old = f"datetime.fromtimestamp({match})"
                new = f"datetime.fromtimestamp({match}, tz=UTC)"
                content = content.replace(old, new, 1)
                fixes += 1

        if content != file_path.read_text():
            file_path.write_text(content)
            return True, fixes

        return False, 0

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Fix all Python files with datetime timezone issues."""
    print("🕐 Phase 1: Fixing datetime timezone issues...")
    print("=" * 80)

    # Get list of files with DTZ errors
    result = subprocess.run(
        ["poetry", "run", "ruff", "check", "--select=DTZ003,DTZ005,DTZ006", "."],
        capture_output=True,
        text=True,
        timeout=120,
    )

    files_to_fix = set()
    # Combine stdout and stderr since ruff may output to either
    output = result.stdout + result.stderr
    for line in output.splitlines():
        if ":" in line and (".py:" in line):
            # Skip error lines
            if line.startswith("error:"):
                continue
            file_path = line.split(":")[0]
            files_to_fix.add(Path(file_path))

    print(f"📁 Found {len(files_to_fix)} files with datetime timezone issues\n")

    fixed_count = 0
    total_fixes = 0

    for file_path in sorted(files_to_fix):
        was_modified, num_fixes = fix_file(file_path)
        if was_modified:
            fixed_count += 1
            total_fixes += num_fixes
            print(f"✅ Fixed {num_fixes:2d} issues: {file_path}")

    print("\n" + "=" * 80)
    print(
        f"✅ Phase 1 Complete: Fixed {total_fixes} datetime issues in {fixed_count} files"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
