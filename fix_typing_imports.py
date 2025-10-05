#!/usr/bin/env python3
"""Fix undefined Dict, List, Optional errors by updating to Python 3.9+ style."""

import re
import subprocess
from pathlib import Path


def fix_file(file_path: Path) -> bool:
    """Fix typing issues in a single file."""
    try:
        content = file_path.read_text()
        original_content = content

        # Check if file uses Dict, List, Optional, Tuple, Set
        has_typing_usage = bool(
            re.search(r"\b(Dict|List|Optional|Tuple|Set)\[", content)
        )

        if not has_typing_usage:
            return False

        # Remove old typing imports
        content = re.sub(
            r"^from typing import .*?(Dict|List|Optional|Tuple|Set).*?\n",
            "",
            content,
            flags=re.MULTILINE,
        )

        # Replace Dict with dict
        content = re.sub(r"\bDict\[", "dict[", content)

        # Replace List with list
        content = re.sub(r"\bList\[", "list[", content)

        # Replace Set with set
        content = re.sub(r"\bSet\[", "set[", content)

        # Replace Tuple with tuple
        content = re.sub(r"\bTuple\[", "tuple[", content)

        # Replace Optional[X] with X | None
        def replace_optional(match):
            inner = match.group(1)
            return f"{inner} | None"

        content = re.sub(r"Optional\[([^\]]+)\]", replace_optional, content)

        if content != original_content:
            file_path.write_text(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Fix all Python files with typing issues."""
    # Get list of files with F821 errors
    result = subprocess.run(
        [
            "poetry",
            "run",
            "ruff",
            "check",
            "--select=F821",
            "--output-format=concise",
            ".",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    files_to_fix = set()
    for line in result.stdout.splitlines():
        if "Undefined name" in line and ":" in line:
            file_path = line.split(":")[0]
            files_to_fix.add(Path(file_path))

    print(f"Found {len(files_to_fix)} files with undefined typing names")

    fixed_count = 0
    for file_path in sorted(files_to_fix):
        if fix_file(file_path):
            fixed_count += 1
            print(f"Fixed: {file_path}")

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
