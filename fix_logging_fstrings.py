import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""Fix logging f-string issues - migrate to structured logging."""

from pathlib import Path
import re
import subprocess


def fix_file(file_path: Path) -> tuple[bool, int]:
    """Fix logging f-strings in a single file.

    Returns:
        Tuple of (was_modified, num_fixes)
    """
    try:
        content = file_path.read_text()
        original_content = content
        fixes = 0

        # Pattern: logger.METHOD(f"text {var}")
        # This is a complex pattern that needs careful handling

        # Simple cases first: logger.info(f"text {var}")
        # For now, convert to: logger.info("text", var=var)

        # Find all logging calls with f-strings
        logging_methods = ["debug", "info", "warning", "error", "critical", "exception"]

        for method in logging_methods:
            # Pattern: logger.METHOD(f"...{var}...")
            # We'll use a simple approach: convert to % formatting first
            # Example: logger.info(f"Processing {item}") → logger.info("Processing %s", item)

            pattern = rf'(\b(?:logger|self\.logger|logging)\s*\.\s*{method}\s*\(\s*)f"([^"]*?)"'

            def replacer(match):
                nonlocal fixes
                prefix = match.group(1)  # logger.info(
                fstring_content = match.group(2)  # Processing {item}

                # Extract variables from {var} patterns
                var_pattern = r"\{([^}]+)\}"
                variables = re.findall(var_pattern, fstring_content)

                # Simple case: no variables
                if not variables:
                    fixes += 1
                    return f'{prefix}"{fstring_content}"'

                # Replace {var} with %s for % formatting
                log_message = re.sub(var_pattern, "%s", fstring_content)
                vars_str = ", ".join(variables)

                fixes += 1
                return f'{prefix}"{log_message}", {vars_str}'

            content = re.sub(pattern, replacer, content)

        # Also handle f'...' (single quotes)
        for method in logging_methods:
            pattern = rf"(\b(?:logger|self\.logger|logging)\s*\.\s*{method}\s*\(\s*)f'([^']*?)'"

            def replacer_single(match):
                nonlocal fixes
                prefix = match.group(1)
                fstring_content = match.group(2)

                var_pattern = r"\{([^}]+)\}"
                variables = re.findall(var_pattern, fstring_content)

                if not variables:
                    fixes += 1
                    return f'{prefix}"{fstring_content}"'

                log_message = re.sub(var_pattern, "%s", fstring_content)
                vars_str = ", ".join(variables)

                fixes += 1
                return f'{prefix}"{log_message}", {vars_str}'

            content = re.sub(pattern, replacer_single, content)

        if content != original_content:
            file_path.write_text(content)
            return True, fixes

        return False, 0

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Fix all Python files with logging f-string issues."""
    print("🔧 Phase 3: Fixing logging f-string issues...")
    print("=" * 80)

    # Get list of files with G004 errors
    result = subprocess.run(
        ["poetry", "run", "ruff", "check", "--select=G004", "."],
        capture_output=True,
        text=True,
        timeout=120,
    )

    files_to_fix = set()
    output = result.stdout + result.stderr
    for line in output.splitlines():
        if ": G004" in line and ".py:" in line:
            if not line.startswith("error:"):
                file_path = line.split(":")[0]
                files_to_fix.add(Path(file_path))

    print(f"📁 Found {len(files_to_fix)} files with logging f-string issues\n")

    fixed_count = 0
    total_fixes = 0

    for file_path in sorted(files_to_fix):
        was_modified, num_fixes = fix_file(file_path)
        if was_modified:
            fixed_count += 1
            total_fixes += num_fixes
            print(f"✅ Fixed {num_fixes:3d} issues: {file_path}")

    print("\n" + "=" * 80)
    print(
        f"✅ Phase 3 Complete: Fixed {total_fixes} logging f-strings in {fixed_count} files"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
