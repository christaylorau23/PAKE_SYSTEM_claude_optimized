#!/usr/bin/env python3
"""Simple, targeted syntax fixes for remaining errors."""

import subprocess
from pathlib import Path


def get_parse_errors():
    """Get all parse errors."""
    result = subprocess.run(
        ["poetry", "run", "ruff", "check", ".", "2>&1"],
        capture_output=True,
        text=True,
        shell=True,
    )
    errors = []
    for line in result.stderr.split("\n"):
        if line.startswith("error:"):
            errors.append(line)
    return errors


def fix_bare_except_pass(file_path: Path, line_num: int) -> bool:
    """Fix bare except clauses missing pass."""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        if line_num >= len(lines):
            return False

        # Look for pattern: except ...: \n return/other statement
        for i in range(max(0, line_num - 5), min(line_num + 5, len(lines))):
            line = lines[i].strip()
            if line.startswith("except") and line.endswith(":"):
                # Check if next non-empty line is not indented properly
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1

                if next_idx < len(lines):
                    next_line = lines[next_idx]
                    # If next line doesn't start with proper indentation for except body
                    except_indent = len(lines[i]) - len(lines[i].lstrip())
                    next_indent = len(next_line) - len(next_line.lstrip())

                    # If next line is at same or lower indentation, add pass
                    if next_indent <= except_indent and next_line.strip():
                        # Insert pass at correct indentation
                        pass_line = " " * (except_indent + 4) + "pass\n"
                        lines.insert(i + 1, pass_line)

                        with open(file_path, "w", encoding="utf-8") as f:
                            f.writelines(lines)
                        return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}:{line_num} - {e}")
        return False


def main():
    """Fix simple syntax errors."""
    errors = get_parse_errors()
    print(f"Found {len(errors)} parse errors")

    fixed = 0
    for error in errors:
        if "Expected 'Indent'" in error or "unindent does not match" in error:
            # Extract file and line
            try:
                parts = error.split("Failed to parse ", 1)[1]
                file_line = parts.split(": ", 1)[0]
                file_parts = file_line.split(":")
                file_path = ":".join(file_parts[:-2])
                line_num = int(file_parts[-2])

                path = Path(file_path)
                if path.exists():
                    if fix_bare_except_pass(path, line_num):
                        fixed += 1
                        print(f"✓ Fixed {file_path}:{line_num}")
            except Exception as e:
                print(f"Failed to parse error line: {error[:100]} - {e}")

    print(f"\n✅ Fixed {fixed} errors")

    # Recheck
    remaining = get_parse_errors()
    print(f"Remaining: {len(remaining)} parse errors")


if __name__ == "__main__":
    main()
