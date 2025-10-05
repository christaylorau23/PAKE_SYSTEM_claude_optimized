#!/usr/bin/env python3
"""Quick script to analyze linting issues by directory."""

import subprocess
from collections import defaultdict
from pathlib import Path


def main():
    # Run ruff and capture output
    result = subprocess.run(
        ["poetry", "run", "ruff", "check", ".", "--output-format=concise"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Parse output
    dir_counts = defaultdict(int)
    for line in result.stdout.splitlines():
        if ":" in line:
            file_path = line.split(":")[0]
            # Get the parent directory
            parent = str(Path(file_path).parent)
            dir_counts[parent] += 1

    # Sort and display top 20
    sorted_dirs = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)

    print("Top 20 Directories by Issue Count:")
    print("=" * 80)
    for dir_name, count in sorted_dirs[:20]:
        print(f"{count:6d}  {dir_name}")


if __name__ == "__main__":
    main()
