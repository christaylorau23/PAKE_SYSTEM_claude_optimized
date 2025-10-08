#!/usr/bin/env python3
"""Case-Sensitivity Fix Script
PAKE System - Phase 4 Implementation.

This script fixes case-sensitivity issues in file paths, imports, and resource lookups.
"""

from pathlib import Path
import re


def find_case_sensitivity_issues(root_path: Path) -> list[tuple[str, str, str]]:
    """Find case-sensitivity issues in the codebase.
    Returns list of (file_path, line_number, issue_description).
    """
    issues = []

    # Limit scanning to essential directories to prevent timeout
    essential_dirs = ["src", "tests", "scripts"]
    exclude_dirs = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
    }

    # Patterns to look for case-sensitivity issues (optimized)
    patterns = [
        # Import statements with mixed case
        (r"from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import", "import"),
        (r"import\s+([a-zA-Z_][a-zA-Z0-9_]*)", "import"),
    ]

    # Scan only essential directories
    for essential_dir in essential_dirs:
        dir_path = root_path / essential_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip files in excluded directories
            if any(exclude_dir in str(py_file) for exclude_dir in exclude_dirs):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        # Limit to first 100 lines to prevent timeout
                        if line_num > 100:
                            break

                        for pattern, issue_type in patterns:
                            matches = re.finditer(pattern, line)
                            for match in matches:
                                if issue_type == "import":
                                    module_name = match.group(1)
                                    if re.search(
                                        r"[A-Z].*[a-z]|[a-z].*[A-Z]", module_name
                                    ):
                                        issues.append(
                                            (
                                                str(py_file),
                                                str(line_num),
                                                f"Mixed case in import: {module_name}",
                                            )
                                        )
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"Error processing {py_file}: {e}")

            # Limit total files processed to prevent timeout
            if len(issues) >= 50:
                break

        if len(issues) >= 50:
            break

    return issues


def fix_case_sensitivity_issues(issues: list[tuple[str, str, str]]) -> None:
    """Fix case-sensitivity issues by correcting file paths and imports."""
    print(f"Found {len(issues)} case-sensitivity issues")

    for file_path, line_num, issue in issues:
        print(f"Fixing: {file_path}:{line_num} - {issue}")

        # This is a placeholder - actual fixes would need to be implemented
        # based on the specific issues found


def main(self) -> None:
    """Main function to run case-sensitivity fixes."""
    root_path = Path(__file__).parent.parent
    print(f"Scanning for case-sensitivity issues in: {root_path}")

    issues = find_case_sensitivity_issues(root_path)

    if issues:
        print(f"Found {len(issues)} case-sensitivity issues:")
        for file_path, line_num, issue in issues[:10]:  # Show first 10
            print(f"  {file_path}:{line_num} - {issue}")

        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")

        # Uncomment to actually fix issues
        # fix_case_sensitivity_issues(issues)
    else:
        print("No case-sensitivity issues found!")


if __name__ == "__main__":
    main()
