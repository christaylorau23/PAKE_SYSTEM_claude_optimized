#!/usr/bin/env python3
"""Apply DTZ fixes across the entire codebase using LibCST transformer.

This script implements Phase 1 of the engineering plan by automatically
remediating all DTZ (DateTime-Timezone) errors using the ComprehensiveDTZTransformer.
It addresses the systemic mishandling of time-aware datetimes that causes
production failures when data crosses timezone boundaries.

Based on the engineering plan's requirements for automated remediation
of production incidents.
"""

from pathlib import Path
import subprocess
import sys
from typing import List, Tuple

import libcst as cst
from libcst.codemod import CodemodContext

from src.codemods.datetime_timezone_transformer import ComprehensiveDTZTransformer


def find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in the directory."""
    python_files = []
    for file_path in directory.rglob("*.py"):
        # Skip certain directories
        if any(
            skip_dir in str(file_path)
            for skip_dir in [
                "__pycache__",
                ".git",
                ".venv",
                "venv",
                "mcp-env",
                "test_env",
                "security_backups",
                "backups",
                ".pytest_cache",
                "node_modules",
            ]
        ):
            continue
        python_files.append(file_path)
    return python_files


def apply_dtz_transformer(file_path: Path) -> tuple[bool, int, str]:
    """Apply DTZ transformer to a single file.

    Returns:
        Tuple of (was_modified, num_modifications, error_message)
    """
    try:
        # Read the original file
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        # Skip files that don't use datetime
        if "datetime" not in original_content:
            return False, 0, ""

        # Parse the file
        try:
            original_tree = cst.parse_module(original_content)
        except cst.ParserSyntaxError as e:
            return False, 0, f"Parse error: {e}"

        # Apply the transformer
        context = CodemodContext()
        transformer = ComprehensiveDTZTransformer(context)
        transformed_tree = transformer.transform_module(original_tree)

        # Check if modifications were made
        modifications = transformer.get_modifications_count()

        if modifications > 0:
            # Write the transformed content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(transformed_tree.code)
            return True, modifications, ""
        return False, 0, ""

    except (FileNotFoundError, PermissionError, OSError) as e:
        return False, 0, f"Error: {e}"


def get_dtz_issues() -> list[str]:
    """Get list of files with DTZ issues using ruff."""
    try:
        result = subprocess.run(
            ["poetry", "run", "ruff", "check", "--select=DTZ", "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        files_with_issues = set()
        output = result.stdout + result.stderr

        for line in output.splitlines():
            if ":" in line and (".py:" in line):
                # Skip error lines
                if line.startswith("error:"):
                    continue
                file_path = line.split(":")[0]
                files_with_issues.add(file_path)

        return list(files_with_issues)

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Warning: Could not get DTZ issues from ruff: {e}")
        return []


def main():
    """Apply DTZ fixes across the entire codebase."""
    print("🕐 Phase 1: Automated DTZ Remediation")
    print("Addressing systemic mishandling of time-aware datetimes")
    print("Based on the engineering plan's requirements")
    print("=" * 80)

    # Get the project root
    project_root = Path(__file__).parent.parent

    # First, try to get files with DTZ issues from ruff
    print("🔍 Scanning for DTZ issues...")
    files_with_dtz_issues = get_dtz_issues()

    if files_with_dtz_issues:
        print(f"📋 Found {len(files_with_dtz_issues)} files with DTZ issues")
        target_files = [Path(f) for f in files_with_dtz_issues if Path(f).exists()]
    else:
        print("📁 Scanning all Python files for datetime usage...")
        target_files = find_python_files(project_root)

    print(f"🎯 Processing {len(target_files)} files...")
    print()

    # Track results
    modified_files = 0
    total_modifications = 0
    errors = []

    # Process each file
    for i, file_path in enumerate(target_files, 1):
        print(
            f"[{i:3d}/{len(target_files)}] {file_path.relative_to(project_root)}",
            end=" ",
        )

        was_modified, modifications, error = apply_dtz_transformer(file_path)

        if error:
            print(f"❌ {error}")
            errors.append(f"{file_path}: {error}")
        elif was_modified:
            print(f"✅ {modifications} fixes")
            modified_files += 1
            total_modifications += modifications
        else:
            print("⏭️  no changes needed")

    # Summary
    print("\n" + "=" * 80)
    print("📊 DTZ Remediation Summary:")
    print(f"   Files processed: {len(target_files)}")
    print(f"   Files modified:  {modified_files}")
    print(f"   Total fixes:      {total_modifications}")
    print(f"   Errors:          {len(errors)}")

    if errors:
        print("\n❌ Errors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"   {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")

    if total_modifications > 0:
        print(f"\n✅ Successfully applied {total_modifications} DTZ fixes!")
        print("🎉 Phase 1 DTZ remediation completed!")

        # Verify fixes with ruff
        print("\n🔍 Verifying fixes with ruff...")
        try:
            result = subprocess.run(
                ["poetry", "run", "ruff", "check", "--select=DTZ", "--statistics"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print("✅ No DTZ issues remaining!")
            else:
                print("⚠️  Some DTZ issues may remain:")
                print(result.stdout)

        except (ValueError, RuntimeError) as e:
            print(f"⚠️  Could not verify with ruff: {e}")

        return 0
    print("\n⚠️  No DTZ fixes were applied.")
    print("This could mean:")
    print("   - No DTZ issues were found")
    print("   - Files have parsing errors")
    print("   - Transformer needs adjustment")
    return 1


if __name__ == "__main__":
    exit(main())
