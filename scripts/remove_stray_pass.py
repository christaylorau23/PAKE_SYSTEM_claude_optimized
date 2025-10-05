#!/usr/bin/env python3
"""
Remove stray 'pass' statements that are causing syntax errors.
"""

import sys
from pathlib import Path


def remove_stray_pass_statements(file_path: Path) -> int:
    """Remove stray pass statements from a Python file."""
    with open(file_path) as f:
        lines = f.readlines()

    modified = False
    removed_count = 0
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        current_stripped = line.strip()

        # Check if current line is just 'pass'
        if current_stripped == "pass":
            # Check if this is a stray pass (not part of valid control flow)
            # Look at next line - if it's actual code (not except/finally), this pass is stray
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # If next line is code (not empty, not comment, not except/finally/else/elif)
                if (
                    next_line
                    and not next_line.startswith("#")
                    and not next_line.startswith(("except", "finally", "else:", "elif"))
                ):
                    # This pass is stray - skip it
                    print(f"{file_path}:{i+1} - Removing stray 'pass'")
                    removed_count += 1
                    modified = True
                    i += 1
                    continue

        new_lines.append(line)
        i += 1

    if modified:
        with open(file_path, "w") as f:
            f.writelines(new_lines)

    return removed_count


def main():
    """Main function to remove stray pass statements from all Python files."""
    project_root = Path("/home/chris/PAKE_SYSTEM_claude_optimized")

    # Find all Python files
    python_files = list(project_root.rglob("*.py"))

    # Exclude certain directories
    excluded_dirs = {
        ".venv",
        "venv",
        "mcp-env",
        "test_env",
        "node_modules",
        ".git",
        "__pycache__",
    }

    python_files = [
        f
        for f in python_files
        if not any(excluded in f.parts for excluded in excluded_dirs)
    ]

    print(f"Scanning {len(python_files)} Python files for stray 'pass' statements...")

    total_removed = 0
    files_modified = 0

    for py_file in python_files:
        removed = remove_stray_pass_statements(py_file)
        if removed > 0:
            total_removed += removed
            files_modified += 1

    print(f"\n{'='*60}")
    print(
        f"Removed {total_removed} stray 'pass' statements from {files_modified} files"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
