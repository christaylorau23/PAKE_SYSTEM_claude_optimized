#!/usr/bin/env python3
"""Fix remaining syntax errors after initial pass removal."""

from pathlib import Path
import re
import subprocess
from typing import Tuple


def get_parse_errors() -> list[str]:
    """Get all current parse errors from ruff."""
    result = subprocess.run(
        ["poetry", "run", "ruff", "check", ".", "2>&1"],
        capture_output=True,
        text=True,
    )
    errors = []
    for line in result.stderr.split("\n"):
        if line.startswith("error:"):
            errors.append(line)
    return errors


def parse_error_line(error: str) -> tuple[str, int, int, str] | None:
    """Parse ruff error line into components."""
    try:
        # Format: "error: Failed to parse <file>:<line>:<col>: <error_type>"
        if "Failed to parse" not in error:
            return None

        after_parse = error.split("Failed to parse ", 1)[1]
        parts = after_parse.split(": ", 1)
        file_line_col = parts[0]
        error_type = parts[1]

        file_parts = file_line_col.split(":")
        file_path = ":".join(file_parts[:-2])
        line_num = int(file_parts[-2])
        col_num = int(file_parts[-1])

        return (file_path, line_num, col_num, error_type)
    except Exception:
        return None


def fix_fstring_format_specs(file_path: Path, line_num: int) -> bool:
    """Fix f-string format specs mixed with % formatting.

    Pattern: "text %s", variable:.1f  -> "text %.1f", variable
    """
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    if line_num > len(lines):
        return False

    # Look for pattern like: variable:.1f, or variable:.2f,
    line = lines[line_num - 1]

    # Pattern: word followed by :.<digits>f
    pattern = r"(\w+):(\.[\d]+f)"
    if re.search(pattern, line):
        # We need to look at the full logger call context
        # Find the start of the logger call
        start_line = line_num - 1
        while start_line > 0:
            if "logger." in lines[start_line]:
                break
            start_line -= 1

        # Find the end of the logger call
        end_line = line_num - 1
        paren_count = 0
        found_start = False
        for i in range(start_line, min(end_line + 10, len(lines))):
            paren_count += lines[i].count("(") - lines[i].count(")")
            if "(" in lines[i]:
                found_start = True
            if found_start and paren_count == 0:
                end_line = i
                break

        # Extract the logger call
        logger_lines = lines[start_line : end_line + 1]
        logger_call = "".join(logger_lines)

        # Fix the format specs
        # Find all variables with format specs
        format_spec_matches = list(re.finditer(r"(\w+):(\.[\d]+f)", logger_call))

        if format_spec_matches:
            # Also need to update the format string
            # Find the format string (first string argument)
            format_str_match = re.search(r'["\'](.*?)["\']', logger_call)
            if format_str_match:
                format_str = format_str_match.group(1)

                # For each variable with format spec, add corresponding % format
                for match in format_spec_matches:
                    var_name = match.group(1)
                    format_spec = match.group(2)

                    # Replace in logger call: var:.1f -> var
                    logger_call = logger_call.replace(
                        f"{var_name}:{format_spec}", var_name
                    )

                    # Update format string: %s -> %format_spec
                    # Find the corresponding %s in order
                    format_str = format_str.replace("%s", f"%{format_spec}", 1)

                # Update the format string in the logger call
                logger_call = re.sub(
                    r'(["\']).*?\1', f'"{format_str}"', logger_call, count=1
                )

                # Write back
                new_lines = logger_call.split("\n")
                lines[start_line : end_line + 1] = [
                    line + "\n" for line in new_lines[:-1]
                ] + [new_lines[-1] + "\n" if new_lines[-1] else ""]

                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                return True

    return False


def fix_pass_before_comment(file_path: Path, line_num: int) -> bool:
    """Fix stray pass statements before comments."""
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    if line_num > len(lines):
        return False

    # Check if this is a "Try statement must have at least one except" error
    # This happens when we have try: pass # comment

    # Look backwards for try:
    for i in range(line_num - 1, max(0, line_num - 20), -1):
        if lines[i].strip().endswith("try:"):
            # Found try block, check for pass followed by comment or code
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip() == "pass":
                    # Check if next non-empty line is a comment or code
                    for k in range(j + 1, min(j + 5, len(lines))):
                        next_line = lines[k].strip()
                        if next_line and not next_line.startswith("#"):
                            # Next line is code, remove pass
                            lines[j] = ""
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)
                            return True
                        if next_line.startswith("#"):
                            # Next line is comment, remove pass
                            lines[j] = ""
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)
                            return True
                    break
            break

    return False


def fix_init_missing_params(file_path: Path, line_num: int) -> bool:
    """Fix __init__ methods that reference config/kwargs but don't have them as params."""
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    if line_num > len(lines):
        return False

    # Look for __init__ without config parameter
    for i in range(max(0, line_num - 10), min(line_num + 5, len(lines))):
        if "def __init__" in lines[i]:
            # Check if line references config or kwargs
            if "config" in lines[line_num - 1] or "kwargs" in lines[line_num - 1]:
                # Check if config is in the signature
                if "config" not in lines[i]:
                    # Add config and **kwargs to signature
                    lines[i] = lines[i].replace("self)", "self, config=None, **kwargs)")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                    return True
            break

    return False


def main():
    """Fix all remaining syntax errors."""
    print("Getting current parse errors...")
    errors = get_parse_errors()
    print(f"Found {len(errors)} parse errors")

    if not errors:
        print("No parse errors found!")
        return

    fixed_count = 0
    error_details = []

    for error in errors:
        parsed = parse_error_line(error)
        if not parsed:
            continue

        file_path, line_num, col_num, error_type = parsed
        path = Path(file_path)

        if not path.exists():
            continue

        error_details.append((path, line_num, error_type))

    print(f"\nProcessing {len(error_details)} errors...")

    # Group by error type
    fstring_errors = [
        e
        for e in error_details
        if "Unexpected token" in e[2] and (":" in e[2] or "FString" in e[2])
    ]
    try_errors = [
        e
        for e in error_details
        if "unindent" in e[2].lower() or "Try statement" in e[2]
    ]

    print(f"\nF-string format spec errors: {len(fstring_errors)}")
    print(f"Try/indent errors: {len(try_errors)}")

    # Fix f-string format spec errors
    for path, line_num, error_type in fstring_errors:
        if fix_fstring_format_specs(path, line_num):
            fixed_count += 1
            print(f"✓ Fixed f-string format spec in {path}:{line_num}")

    # Fix try/pass errors
    for path, line_num, error_type in try_errors:
        if fix_pass_before_comment(path, line_num):
            fixed_count += 1
            print(f"✓ Fixed try/pass issue in {path}:{line_num}")

    # Fix __init__ parameter errors in cached_orchestrator.py
    cached_orch = Path("src/services/ingestion/cached_orchestrator.py")
    if cached_orch.exists():
        with open(cached_orch, encoding="utf-8") as f:
            lines = f.readlines()

        # Line 56 has super().__init__(config, **kwargs) but __init__ is at line 54
        # Need to add config and **kwargs parameters
        for i, line in enumerate(lines):
            if i == 53 and "def __init__" in line:  # Line 54 (0-indexed = 53)
                if "config" not in line:
                    lines[i] = (
                        "    def __init__(self, config=None, **kwargs) -> None:\n"
                    )
                    with open(cached_orch, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                    fixed_count += 1
                    print(f"✓ Fixed __init__ signature in {cached_orch}:54")
                    break

    print(f"\n✅ Fixed {fixed_count} errors")

    # Check remaining errors
    remaining = get_parse_errors()
    print(f"Remaining parse errors: {len(remaining)}")


if __name__ == "__main__":
    main()
