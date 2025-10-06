#!/usr/bin/env python3
"""Comprehensive script to fix all unterminated f-strings in Python files.
This script handles various patterns of malformed f-strings.
"""

from pathlib import Path
import re


def fix_fstrings_in_file(self) -> None:
    """Fix f-string issues in a single file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Pattern 1: f"text {variable} more text" - single line
        pattern1 = r'f"([^"]*)\{\s*([^}]+)\s*\}([^"]*)"'

        def fix_match1(self) -> None:
            prefix = self.match.group(1)
            variable = self.match.group(2).strip()
            suffix = self.match.group(3)
            return f'f"{prefix}{{{variable}}}{suffix}"'

        content = re.sub(pattern1, fix_match1, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 2: Multi-line f-strings with variables
        # f"text {
        #     variable} more text"
        pattern2 = r'f"([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'

        def fix_match2(self) -> None:
            prefix = self.match.group(1)
            variable = self.match.group(2).strip()
            suffix = self.match.group(3)
            return f'f"{prefix}{{{variable}}}{suffix}"'

        content = re.sub(pattern2, fix_match2, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 3: f"text {
        #     variable} more {
        #     variable2} text"
        pattern3 = r'f"([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'

        def fix_match3(self) -> None:
            prefix = self.match.group(1)
            var1 = self.match.group(2).strip()
            middle = self.match.group(3)
            var2 = self.match.group(4).strip()
            suffix = self.match.group(5)
            return f'f"{prefix}{{{var1}}}{middle}{{{var2}}}{suffix}"'

        content = re.sub(pattern3, fix_match3, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 4: Simple cases like f"{
        #     variable}"
        pattern4 = r'f"\{\s*\n\s*([^}]+)\s*\n\s*\}"'

        def fix_match4(self) -> None:
            variable = self.match.group(1).strip()
            return f'f"{{{variable}}}"'

        content = re.sub(pattern4, fix_match4, content, flags=re.MULTILINE | re.DOTALL)

        # Pattern 5: Cases where the f-string starts with a variable
        pattern5 = r'f"\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'

        def fix_match5(self) -> None:
            variable = self.match.group(1).strip()
            suffix = self.match.group(2)
            return f'f"{{{variable}}}{suffix}"'

        content = re.sub(pattern5, fix_match5, content, flags=re.MULTILINE | re.DOTALL)

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed f-strings in: {file_path}")
            return True
        return False

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main(self) -> None:
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