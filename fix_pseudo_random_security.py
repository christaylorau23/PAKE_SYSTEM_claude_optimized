#!/usr/bin/env python3
"""Pseudo-Random Generator Security Fix Script
Replaces insecure random generators with cryptographically secure alternatives.
"""

import logging
import os
from pathlib import Path
import re
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_random_usage() -> list[tuple[str, int, str]]:
    """Find all insecure random usage patterns."""
    violations = []

    # Search for random module usage
    for py_file in Path(".").rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Check for insecure random patterns
                if (
                    re.search(
                        r"\brandom\.(random|uniform|randint|choice|shuffle)\b", line
                    )
                    or re.search(r"\bfrom random import", line)
                    or re.search(r"\bimport random\b", line)
                ):
                    violations.append((str(py_file), line_num, line.strip()))

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error(f"Error reading {py_file}: {e}")

    return violations


def fix_random_imports(file_path: str) -> bool:
    """Fix random imports in a file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Replace random imports
        content = re.sub(r"import random", "import secrets", content)

        content = re.sub(r"from random import", "from secrets import", content)

        # Replace specific random functions
        replacements = [
            (r"\brandom\.random\(\)", "secrets.randbelow(2**32) / (2**32)"),
            (
                r"\brandom\.uniform\(([^)]+)\)",
                r"secrets.randbelow(int((\1[1] - \1[0]) * 1000)) / 1000 + \1[0]",
            ),
            (
                r"\brandom\.randint\(([^,]+),\s*([^)]+)\)",
                r"secrets.randbelow(\2 - \1 + 1) + \1",
            ),
            (r"\brandom\.choice\(([^)]+)\)", r"secrets.choice(\1)"),
            (r"\brandom\.shuffle\(([^)]+)\)", r"secrets.shuffle(\1)"),
        ]

        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.error(f"Error fixing {file_path}: {e}")

    return False


def create_secure_random_utils():
    """Create a secure random utilities module."""
    utils_content = '''"""
Secure Random Utilities
Provides cryptographically secure random number generation
"""

import secrets
import string
from typing import List, Any


def secure_random_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Generate a cryptographically secure random float."""
    if min_val >= max_val:
        raise ValueError("min_val must be less than max_val")

    range_size = max_val - min_val
    # Use a large range for better precision
    random_int = secrets.randbelow(2**32)
    return (random_int / (2**32)) * range_size + min_val


def secure_random_int(min_val: int, max_val: int) -> int:
    """Generate a cryptographically secure random integer."""
    if min_val >= max_val:
        raise ValueError("min_val must be less than max_val")

    return secrets.randbelow(max_val - min_val + 1) + min_val


def secure_random_string(length: int = 32, alphabet: str = None) -> str:
    """Generate a cryptographically secure random string."""
    if alphabet is None:
        alphabet = string.ascii_letters + string.digits

    return ''.join(secrets.choice(alphabet) for _ in range(length))


def secure_shuffle(items: List[Any]) -> List[Any]:
    """Shuffle a list in place using cryptographically secure random."""
    # Create a copy to avoid modifying the original
    shuffled = items.copy()
    secrets.shuffle(shuffled)
    return shuffled


def secure_choice(items: List[Any]) -> Any:
    """Choose a random item from a list using cryptographically secure random."""
    return secrets.choice(items)
'''

    utils_path = Path("src/utils/secure_random.py")
    utils_path.parent.mkdir(parents=True, exist_ok=True)

    with open(utils_path, "w", encoding="utf-8") as f:
        f.write(utils_content)

    logger.info(f"Created secure random utilities at {utils_path}")


def main():
    """Main function to fix pseudo-random generator issues."""
    logger.info("Starting pseudo-random generator security fixes...")

    # Create secure random utilities
    create_secure_random_utils()

    # Find all random usage
    violations = find_random_usage()
    logger.info(f"Found {len(violations)} insecure random usage patterns")

    # Fix files
    fixed_files = set()
    for file_path, _line_num, _line_content in violations:
        if file_path not in fixed_files and fix_random_imports(file_path):
            fixed_files.add(file_path)
            logger.info(f"Fixed random usage in {file_path}")

    logger.info(f"Fixed random usage in {len(fixed_files)} files")
    logger.info("Pseudo-random generator security fixes completed!")


if __name__ == "__main__":
    main()
