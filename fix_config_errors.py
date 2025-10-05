#!/usr/bin/env python3
"""Fix undefined config/app errors in __init__ methods - CRITICAL runtime bugs."""

import re
import subprocess
from pathlib import Path


def analyze_init_method(content: str, file_path: Path) -> dict:
    """Analyze __init__ method to find undefined variables."""
    # Find all __init__ methods
    init_pattern = r"def __init__\(self(?:,\s*([^)]*))?\)\s*->\s*None:"

    issues = []
    for match in re.finditer(init_pattern, content):
        start_pos = match.start()
        params = match.group(1) or ""

        # Find the method body (next 50 lines)
        lines_after = content[start_pos:].split("\n")[:50]
        method_body = "\n".join(lines_after)

        # Check for undefined variables being used
        undefined_vars = []

        # Pattern 1: self.X = X (where X is not in params)
        assignments = re.findall(r"self\.(\w+)\s*=\s*(\w+)", method_body)
        for attr, var in assignments:
            if var not in params and var not in ["None", "True", "False", "self"]:
                # Check if it's likely a config/app variable
                if var in ["config", "app", "message_bus", "agent_id", "service_name"]:
                    undefined_vars.append((attr, var))

        # Pattern 2: super().__init__(X) where X is undefined
        super_calls = re.findall(r"super\(\).__init__\(([^)]+)\)", method_body)
        for super_args in super_calls:
            for arg in super_args.split(","):
                arg = arg.strip()
                if (
                    arg
                    and arg not in params
                    and arg not in ["self", "None", "True", "False"]
                ):
                    undefined_vars.append(("super_arg", arg))

        if undefined_vars:
            issues.append(
                {
                    "start_pos": start_pos,
                    "current_params": params,
                    "undefined_vars": undefined_vars,
                    "method_snippet": method_body[:200],
                }
            )

    return issues


def fix_file(file_path: Path) -> tuple[bool, int]:
    """Fix undefined config/app errors in a file.

    Returns:
        Tuple of (was_modified, num_fixes)
    """
    try:
        content = file_path.read_text()
        original_content = content
        fixes = 0

        # Pattern 1: Fix `def __init__(self) -> None:` with `self.config = config`
        # This is the most common pattern
        pattern1 = (
            r"(def __init__\(self)\)\s*->\s*None:\s*\n(\s+).*?self\.config\s*=\s*config"
        )
        if re.search(pattern1, content, re.DOTALL):
            # Check what other undefined vars are used
            undefined_vars = set()
            init_match = re.search(pattern1, content, re.DOTALL)
            if init_match:
                init_body = init_match.group(0)
                # Look for self.X = X patterns
                for match in re.finditer(r"self\.\w+\s*=\s*(\w+)", init_body):
                    var = match.group(1)
                    if var not in [
                        "self",
                        "None",
                        "True",
                        "False",
                        "str",
                        "int",
                        "list",
                        "dict",
                    ]:
                        undefined_vars.add(var)

                # Look for super().__init__(X)
                super_match = re.search(r"super\(\).__init__\(([^)]+)\)", init_body)
                if super_match:
                    for arg in super_match.group(1).split(","):
                        arg = arg.strip()
                        if arg and arg not in ["self", "None", "True", "False"]:
                            undefined_vars.add(arg)

            # Build new parameter list
            new_params = ", ".join(sorted(undefined_vars))
            if new_params:
                # Add type hints for common patterns
                typed_params = []
                for var in sorted(undefined_vars):
                    if var == "config" or var == "app":
                        typed_params.append(f"{var}: Any")
                    elif var.endswith("_id"):
                        typed_params.append(f"{var}: str")
                    elif var.endswith("_bus"):
                        typed_params.append(f"{var}: Any")
                    else:
                        typed_params.append(f"{var}: Any")

                new_params = ", ".join(typed_params)

                # Replace the __init__ signature
                content = re.sub(
                    r"(def __init__\(self)\)\s*->\s*None:",
                    f"\\1, {new_params}) -> None:",
                    content,
                    count=1,
                )
                fixes += 1

        if content != original_content:
            # Add Any import if needed
            if "from typing import" in content and "Any" not in content:
                content = re.sub(
                    r"(from typing import [^\n]+)",
                    lambda m: m.group(0) + ", Any"
                    if "Any" not in m.group(0)
                    else m.group(0),
                    content,
                    count=1,
                )
            elif "from typing import" not in content and "import" in content:
                # Add typing import
                first_import = re.search(r"^import ", content, re.MULTILINE)
                if first_import:
                    insert_pos = first_import.start()
                    content = (
                        content[:insert_pos]
                        + "from typing import Any\n"
                        + content[insert_pos:]
                    )

            file_path.write_text(content)
            return True, fixes

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Fix all Python files with undefined config/app errors."""
    print("🔧 Phase 2: Fixing CRITICAL undefined config/app errors...")
    print("=" * 80)

    # Get list of files with F821 config errors
    result = subprocess.run(
        ["poetry", "run", "ruff", "check", "--select=F821", "."],
        capture_output=True,
        text=True,
        timeout=120,
    )

    files_to_fix = set()
    output = result.stdout + result.stderr
    for line in output.splitlines():
        if "Undefined name `config`" in line or "Undefined name `app`" in line:
            if ":" in line and ".py:" in line:
                file_path = line.split(":")[0]
                files_to_fix.add(Path(file_path))

    print(f"📁 Found {len(files_to_fix)} files with undefined config/app errors\n")

    fixed_count = 0
    total_fixes = 0

    for file_path in sorted(files_to_fix):
        was_modified, num_fixes = fix_file(file_path)
        if was_modified:
            fixed_count += 1
            total_fixes += num_fixes
            print(f"✅ Fixed {num_fixes:2d} issues: {file_path}")

    print("\n" + "=" * 80)
    print(
        f"✅ Phase 2 Complete: Fixed {total_fixes} config/app issues in {fixed_count} files"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
