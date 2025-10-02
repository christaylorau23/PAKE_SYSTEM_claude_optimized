#!/usr/bin/env python3
"""
Comprehensive script to fix all unterminated f-strings in Python files.
This script handles various patterns of malformed f-strings.
"""

import re
import os
import sys
from pathlib import Path

def fix_fstrings_in_file(file_path):
    """Fix f-string issues in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: f"text {variable} more text" - single line
        pattern1 = r'f"([^"]*)\{\s*([^}]+)\s*\}([^"]*)"'

        def fix_match1(match):
            prefix = match.group(1)
            variable = match.group(2).strip()
            suffix = match.group(3)
            return f'f"{prefix}{{{variable}}}{suffix}"'

        content = re.sub(pattern1, fix_match1, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 2: Multi-line f-strings with variables
        # f"text {
        #     variable} more text"
        pattern2 = r'f"([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'

        def fix_match2(match):
            prefix = match.group(1)
            variable = match.group(2).strip()
            suffix = match.group(3)
            return f'f"{prefix}{{{variable}}}{suffix}"'

        content = re.sub(pattern2, fix_match2, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 3: f"text {
        #     variable} more {
        #     variable2} text"
        pattern3 = r'f"([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'

        def fix_match3(match):
            prefix = match.group(1)
            var1 = match.group(2).strip()
            middle = match.group(3)
            var2 = match.group(4).strip()
            suffix = match.group(5)
            return f'f"{prefix}{{{var1}}}{middle}{{{var2}}}{suffix}"'

        content = re.sub(pattern3, fix_match3, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 4: Simple cases like f"{
        #     variable}"
        pattern4 = r'f"\{\s*\n\s*([^}]+)\s*\n\s*\}"'

        def fix_match4(match):
            variable = match.group(1).strip()
            return f'f"{{{variable}}}"'

        content = re.sub(pattern4, fix_match4, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 5: Cases where the f-string starts with a variable
        pattern5 = r'f"\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'

        def fix_match5(match):
            variable = match.group(1).strip()
            suffix = match.group(2)
            return f'f"{{{variable}}}{suffix}"'

        content = re.sub(pattern5, fix_match5, content, flags=re.MULTILINE | re.DOTALL)

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed f-strings in: {file_path}")
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix f-strings in all Python files."""
    src_dir = Path("/home/chris/projects/PAKE_SYSTEM_claude_optimized/src")

    if not src_dir.exists():
        print(f"Source directory {src_dir} does not exist")
        return

    fixed_count = 0
    total_count = 0

    # Find all Python files
    for py_file in src_dir.rglob("*.py"):
        total_count += 1
        if fix_fstrings_in_file(py_file):
            fixed_count += 1

    print(f"Processed {total_count} Python files")
    print(f"Fixed f-strings in {fixed_count} files")

if __name__ == "__main__":
    main()
