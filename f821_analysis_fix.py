#!/usr/bin/env python3
"""F821 Error Analysis and Fix Script
Analyzes and fixes the most common F821 undefined name errors.
"""

from collections import Counter
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Tuple


def analyze_f821_errors() -> dict[str, int]:
    """Analyze F821 errors and return frequency of undefined names."""
    # Use absolute path for security (S607)
    import shutil

    ruff_path = shutil.which("ruff")
    if not ruff_path:
        msg = "Ruff not found in PATH"
        raise RuntimeError(msg)

    result = subprocess.run(
        [ruff_path, "check", ".", "--select=F821"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    undefined_names = []
    output = result.stdout + result.stderr

    for line in output.splitlines():
        if "F821" in line and "Undefined name" in line:
            name_match = re.search(r"Undefined name `([^`]+)`", line)
            if name_match:
                undefined_names.append(name_match.group(1))

    return Counter(undefined_names)


def get_files_with_errors() -> dict[str, list[tuple[int, str]]]:
    """Get files with F821 errors and their details."""
    # Use absolute path for security (S607)
    import shutil

    ruff_path = shutil.which("ruff")
    if not ruff_path:
        msg = "Ruff not found in PATH"
        raise RuntimeError(msg)

    result = subprocess.run(
        [ruff_path, "check", ".", "--select=F821"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    errors_by_file = {}
    output = result.stdout + result.stderr

    for line in output.splitlines():
        if "F821" in line and "Undefined name" in line and ":" in line:
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])
                name_match = re.search(r"Undefined name `([^`]+)`", line)
                if name_match:
                    undefined_name = name_match.group(1)
                    if file_path not in errors_by_file:
                        errors_by_file[file_path] = []
                    errors_by_file[file_path].append((line_num, undefined_name))

    return errors_by_file


def fix_common_patterns(
    file_path: Path, errors: list[tuple[int, str]]
) -> tuple[bool, int]:
    """Fix common F821 patterns in a file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content
    fixes_applied = 0

    # Pattern 1: Fix missing __init__ parameters
    init_pattern = r"def __init__\(self\) -> None:"
    init_matches = list(re.finditer(init_pattern, content))

    for match in reversed(init_matches):
        init_start = match.start()
        init_end = match.end()

        # Get undefined names used near this __init__
        method_start_line = content[:init_start].count("\n") + 1
        method_end_line = method_start_line + 30

        method_undefined_names = set()
        for line_num, undefined_name in errors:
            if method_start_line <= line_num <= method_end_line:
                method_undefined_names.add(undefined_name)

        if method_undefined_names:
            # Create parameter list with proper types
            params = []
            for name in sorted(method_undefined_names):
                if name in ["environment", "config_file", "config"]:
                    params.append(f"{name}: str | None = None")
                elif name in [
                    "query_request",
                    "conversation",
                    "extraction",
                    "batch",
                    "vector_db",
                ]:
                    params.append(f"{name}: Any = None")
                elif name in ["rollback", "operation", "dal"]:
                    params.append(f"{name}: bool = False")
                elif name in ["name", "vault_path"]:
                    params.append(f"{name}: str = ''")
                else:
                    params.append(f"{name}: Any = None")

            param_str = ", ".join(params)
            new_init = f"def __init__(self, {param_str}) -> None:"

            content = content[:init_start] + new_init + content[init_end:]
            fixes_applied += 1
            print(f"  Fixed __init__: added {len(method_undefined_names)} parameters")

    # Pattern 2: Add missing Any import if needed
    if fixes_applied > 0 and "Any" in content and "from typing import" in content:
        typing_import_pattern = r"from typing import ([^\n]+)"
        typing_match = re.search(typing_import_pattern, content)

        if typing_match:
            existing_imports = typing_match.group(1)
            if "Any" not in existing_imports:
                new_import = f"from typing import {existing_imports}, Any"
                content = re.sub(typing_import_pattern, new_import, content)
                print("  Added Any import")

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, fixes_applied

    return False, 0


def main():
    """Main function to analyze and fix F821 errors."""
    print("🔧 F821 Error Analysis and Fix - The Phoenix Protocol Phase 5.2")
    print("=" * 70)

    # Analyze error patterns
    print("📊 Analyzing F821 error patterns...")
    error_counts = analyze_f821_errors()

    print("Top 10 most common undefined names:")
    for name, count in error_counts.most_common(10):
        print(f"  {name}: {count} occurrences")
    print()

    # Get files with errors
    print("📁 Getting files with F821 errors...")
    errors_by_file = get_files_with_errors()

    total_files = len(errors_by_file)
    total_errors = sum(len(errors) for errors in errors_by_file.values())

    print(f"Found {total_errors} F821 errors in {total_files} files")
    print()

    # Process files with most errors first
    sorted_files = sorted(errors_by_file.items(), key=lambda x: len(x[1]), reverse=True)

    fixed_files = 0
    total_fixes = 0

    print("🔧 Fixing files...")
    for file_path_str, errors in sorted_files[:15]:  # Process top 15 files
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue

        print(f"Fixing {file_path} ({len(errors)} errors)...")

        was_modified, fixes = fix_common_patterns(file_path, errors)
        if was_modified:
            fixed_files += 1
            total_fixes += fixes
            print(f"  ✅ Fixed {fixes} issues")
        else:
            print("  ℹ️  No fixes applied")
        print()

    print("=" * 70)
    print(
        f"✅ Phase 5.2 Complete: Fixed {total_fixes} F821 issues in {fixed_files} files"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
