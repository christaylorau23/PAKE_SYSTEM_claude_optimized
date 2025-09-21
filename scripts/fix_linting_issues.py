#!/usr/bin/env python3
"""
Comprehensive Python Linting Fixer for PAKE System

This script systematically fixes common linting issues in Python files:
- Unused imports (F401)
- Line length violations (E501)
- Blank line issues (E302, W391, W293)
- Indentation issues (E128)
- Import order issues (E402)
- Bare except clauses (E722)
- Comment spacing (E261)
- Other common linting issues

Usage:
    python scripts/fix_linting_issues.py --dry-run  # Preview changes
    python scripts/fix_linting_issues.py  # Apply fixes
    python scripts/fix_linting_issues.py --target src/services/ingestion/  # Fix specific directory
"""

import argparse
import ast
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("linting_fixes.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class PythonLintingFixer:
    """Comprehensive Python linting issue fixer"""

    def __init__(self, dry_run: bool = False, backup: bool = True):
        self.dry_run = dry_run
        self.backup = backup
        self.processed_files = 0
        self.fixed_files = 0
        self.errors = []
        self.backup_dir = None

        if self.backup and not self.dry_run:
            self.backup_dir = self._create_backup_dir()

    def _create_backup_dir(self) -> str:
        """Create backup directory with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/linting_fixes_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        logger.info(f"Created backup directory: {backup_dir}")
        return backup_dir

    def find_python_files(self, directories: list[str]) -> list[str]:
        """Find all Python files in specified directories"""
        python_files = []

        for directory in directories:
            if not os.path.exists(directory):
                logger.warning(f"Directory not found: {directory}")
                continue

            for root, dirs, files in os.walk(directory):
                # Skip certain directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["__pycache__", "node_modules"]
                ]

                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

        logger.info(f"Found {len(python_files)} Python files to process")
        return python_files

    def backup_file(self, file_path: str) -> None:
        """Create backup of file before modification"""
        if not self.backup_dir:
            return

        rel_path = os.path.relpath(file_path)
        backup_path = os.path.join(self.backup_dir, rel_path)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(file_path, backup_path)

    def read_file_safely(self, file_path: str) -> str | None:
        """Safely read file content with encoding detection"""
        encodings = ["utf-8", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                return None

        logger.error(f"Could not decode {file_path} with any encoding")
        return None

    def write_file_safely(self, file_path: str, content: str) -> bool:
        """Safely write file content"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            return False

    def get_used_names_from_ast(self, content: str) -> set[str]:
        """Get all used names from AST to identify unused imports"""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(
                f"Syntax error in file, skipping unused import detection: {e}",
            )
            return set()

        used_names = set()

        class NameVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                used_names.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node):
                # Handle module.attribute usage
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
                self.generic_visit(node)

            def visit_Call(self, node):
                # Handle function calls
                if isinstance(node.func, ast.Name):
                    used_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute) and isinstance(
                    node.func.value,
                    ast.Name,
                ):
                    used_names.add(node.func.value.id)
                self.generic_visit(node)

        visitor = NameVisitor()
        visitor.visit(tree)
        return used_names

    def fix_unused_imports(self, content: str) -> str:
        """Remove unused imports"""
        lines = content.split("\n")
        used_names = self.get_used_names_from_ast(content)

        # Add common names that might be used dynamically
        used_names.update(["logger", "logging", "sys", "os", "typing", "__version__"])

        new_lines = []
        import_section = True

        for line in lines:
            stripped = line.strip()

            # Check if we're still in import section
            if (
                stripped
                and not stripped.startswith(("  #", "import ", "from "))
                and import_section
            ):
                import_section = False

            # Handle import lines
            if import_section and (
                stripped.startswith("import ") or stripped.startswith("from ")
            ):
                if self._should_keep_import(stripped, used_names):
                    new_lines.append(line)
                else:
                    logger.debug(f"Removing unused import: {stripped}")
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    def _should_keep_import(self, import_line: str, used_names: set[str]) -> bool:
        """Determine if an import should be kept"""
        # Always keep certain imports
        keep_patterns = [
            "from __future__ import",
            "import sys",
            "import os",
            "import logging",
            "from typing import",
            "from dataclasses import",
            "from abc import",
            "from pathlib import",
        ]

        for pattern in keep_patterns:
            if pattern in import_line:
                return True

        # Extract imported names
        if import_line.startswith("import "):
            # Handle: import module, import module as alias
            parts = import_line[7:].split(",")
            for part in parts:
                name = part.strip().split(" as ")[0].strip()
                if name.split(".")[0] in used_names:
                    return True

        elif import_line.startswith("from "):
            # Handle: from module import name, from module import name as alias
            try:
                parts = import_line.split(" import ")
                if len(parts) == 2:
                    imports = parts[1].split(",")
                    for imp in imports:
                        name = imp.strip().split(" as ")[-1].strip()
                        if name in used_names or name == "*":
                            return True
            except Exception:
                # If parsing fails, keep the import to be safe
                return True

        return False

    def fix_line_length(self, content: str, max_length: int = 88) -> str:
        """Fix line length violations"""
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            if len(line) <= max_length:
                new_lines.append(line)
                continue

            # Try to break long lines intelligently
            fixed_line = self._break_long_line(line, max_length)
            if isinstance(fixed_line, list):
                new_lines.extend(fixed_line)
            else:
                new_lines.append(fixed_line)

        return "\n".join(new_lines)

    def _break_long_line(self, line: str, max_length: int) -> str:
        """Break a long line into multiple lines"""
        stripped = line.strip()
        indent = line[: len(line) - len(line.lstrip())]

        # Don't break comments or strings unless absolutely necessary
        if stripped.startswith("  #") or '"""' in stripped or "'''" in stripped:
            return line

        # Break function calls with multiple arguments
        if "(" in stripped and ")" in stripped:
            return self._break_function_call(line, max_length, indent)

        # Break list/dict literals
        if any(char in stripped for char in "[{"):
            return self._break_collection(line, max_length, indent)

        # Break import statements
        if stripped.startswith(("import ", "from ")):
            return self._break_import(line, max_length, indent)

        return line

    def _break_function_call(self, line: str, max_length: int, indent: str) -> str:
        """Break function calls with long argument lists"""
        stripped = line.strip()

        # Find function call pattern
        paren_pos = stripped.find("(")
        if paren_pos == -1:
            return line

        func_part = stripped[: paren_pos + 1]
        args_part = stripped[paren_pos + 1 :]

        if args_part.endswith(")"):
            args_part = args_part[:-1]

        # Split arguments
        args = self._split_arguments(args_part)

        if len(args) <= 1:
            return line

        # Reconstruct with line breaks
        lines = [indent + func_part]
        for i, arg in enumerate(args):
            comma = "," if i < len(args) - 1 else ""
            lines.append(indent + "    " + arg.strip() + comma)
        lines.append(indent + ")")

        return lines

    def _split_arguments(self, args_str: str) -> list[str]:
        """Split function arguments respecting nested structures"""
        args = []
        current_arg = ""
        paren_level = 0
        bracket_level = 0
        brace_level = 0
        in_string = False
        string_char = None

        for char in args_str:
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char == "(":
                    paren_level += 1
                elif char == ")":
                    paren_level -= 1
                elif char == "[":
                    bracket_level += 1
                elif char == "]":
                    bracket_level -= 1
                elif char == "{":
                    brace_level += 1
                elif char == "}":
                    brace_level -= 1
                elif (
                    char == ","
                    and paren_level == 0
                    and bracket_level == 0
                    and brace_level == 0
                ):
                    args.append(current_arg)
                    current_arg = ""
                    continue

            current_arg += char

        if current_arg.strip():
            args.append(current_arg)

        return args

    def _break_collection(self, line: str, max_length: int, indent: str) -> str:
        """Break long list/dict literals"""
        # Simple approach for now
        return line

    def _break_import(self, line: str, max_length: int, indent: str) -> str:
        """Break long import statements"""
        stripped = line.strip()

        if stripped.startswith("from ") and " import " in stripped:
            parts = stripped.split(" import ")
            if len(parts) == 2:
                from_part = parts[0]
                import_part = parts[1]

                imports = [imp.strip() for imp in import_part.split(",")]
                if len(imports) > 1:
                    lines = [indent + from_part + " import ("]
                    for i, imp in enumerate(imports):
                        comma = "," if i < len(imports) - 1 else ""
                        lines.append(indent + "    " + imp + comma)
                    lines.append(indent + ")")
                    return lines

        return line

    def fix_blank_lines(self, content: str) -> str:
        """Fix blank line issues"""
        lines = content.split("\n")
        new_lines = []

        # Remove trailing whitespace from all lines
        lines = [line.rstrip() for line in lines]

        # Remove blank lines at the end
        while lines and not lines[-1].strip():
            lines.pop()

        # Add proper blank lines around classes and functions
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Add blank lines before class/function definitions
            if (
                stripped.startswith(("def ", "class ", "@"))
                and i > 0
                and lines[i - 1].strip()
                and not lines[i - 1].strip().startswith(("@", "def ", "class "))
            ):
                # Check if we need to add blank lines
                blank_lines_before = 0
                for j in range(i - 1, -1, -1):
                    if not lines[j].strip():
                        blank_lines_before += 1
                    else:
                        break

                # Add appropriate number of blank lines
                if stripped.startswith("class "):
                    needed_blank_lines = 2
                elif stripped.startswith("def "):
                    needed_blank_lines = (
                        2
                        if i == 0
                        or any(
                            lines[k].strip().startswith("class ")
                            for k in range(max(0, i - 5), i)
                        )
                        else 1
                    )
                else:
                    needed_blank_lines = 1

                for _ in range(needed_blank_lines - blank_lines_before):
                    new_lines.append("")

            new_lines.append(line)

        # Ensure file ends with exactly one newline
        if new_lines and new_lines[-1]:
            new_lines.append("")

        return "\n".join(new_lines)

    def fix_indentation(self, content: str) -> str:
        """Fix basic indentation issues"""
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            if not line.strip():
                new_lines.append("")
                continue

            # Convert tabs to spaces
            line = line.expandtabs(4)

            # Fix basic indentation alignment
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            # Ensure indentation is multiple of 4
            if current_indent % 4 != 0:
                new_indent = (current_indent // 4 + 1) * 4
                line = " " * new_indent + stripped

            new_lines.append(line)

        return "\n".join(new_lines)

    def fix_import_order(self, content: str) -> str:
        """Fix import order issues"""
        lines = content.split("\n")

        # Find import section
        import_start = -1
        import_end = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and import_start == -1:
                import_start = i
            elif (
                import_start != -1
                and stripped
                and not stripped.startswith(("import ", "from ", "  #"))
            ):
                import_end = i
                break

        if import_start == -1:
            return content

        if import_end == -1:
            import_end = len(lines)

        # Extract imports
        imports = lines[import_start:import_end]
        other_lines = lines[:import_start] + lines[import_end:]

        # Sort imports (basic sorting)
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for imp in imports:
            stripped = imp.strip()
            if not stripped or stripped.startswith("  #"):
                continue

            if any(
                stdlib in stripped
                for stdlib in ["os", "sys", "json", "datetime", "pathlib", "typing"]
            ):
                stdlib_imports.append(imp)
            elif stripped.startswith("from .") or stripped.startswith("from src"):
                local_imports.append(imp)
            else:
                third_party_imports.append(imp)

        # Reconstruct
        sorted_imports = []
        if stdlib_imports:
            sorted_imports.extend(sorted(stdlib_imports))
            sorted_imports.append("")
        if third_party_imports:
            sorted_imports.extend(sorted(third_party_imports))
            sorted_imports.append("")
        if local_imports:
            sorted_imports.extend(sorted(local_imports))
            sorted_imports.append("")

        # Remove extra blank line at the end
        if sorted_imports and not sorted_imports[-1].strip():
            sorted_imports.pop()

        # Reconstruct file
        result_lines = (
            other_lines[:import_start] + sorted_imports + other_lines[import_start:]
        )
        return "\n".join(result_lines)

    def fix_bare_except(self, content: str) -> str:
        """Fix bare except clauses"""
        # Simple regex replacement for common patterns
        content = re.sub(r"except\s*:", "except Exception:", content)
        return content

    def fix_comment_spacing(self, content: str) -> str:
        """Fix comment spacing issues"""
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            # Fix inline comments
            if "#" in line and not line.strip().startswith("#"):
                parts = line.split("#", 1)
                if len(parts) == 2:
                    code_part = parts[0].rstrip()
                    comment_part = parts[1]

                    # Ensure at least two spaces before comment
                    if code_part and not code_part.endswith("  "):
                        line = code_part + "  #" + comment_part
                    else:
                        line = code_part + "  #" + comment_part

            new_lines.append(line)

        return "\n".join(new_lines)

    def run_autopep8(self, file_path: str) -> bool:
        """Run autopep8 to fix formatting issues"""
        try:
            # Check if autopep8 is available
            subprocess.run(["autopep8", "--version"], capture_output=True, check=True)

            cmd = [
                "autopep8",
                "--in-place",
                "--aggressive",
                "--aggressive",
                "--max-line-length=88",
                file_path,
            ]

            if self.dry_run:
                cmd.remove("--in-place")
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0

        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.debug("autopep8 not available, using manual fixes")
            return False

    def fix_file(self, file_path: str) -> bool:
        """Fix all linting issues in a single file"""
        logger.info(f"Processing: {file_path}")

        try:
            # Read original content
            original_content = self.read_file_safely(file_path)
            if original_content is None:
                return False

            # Backup original file
            if not self.dry_run:
                self.backup_file(file_path)

            # Try autopep8 first
            content = original_content
            autopep8_success = False

            if not self.dry_run:
                autopep8_success = self.run_autopep8(file_path)
                if autopep8_success:
                    # Read the autopep8 result
                    content = self.read_file_safely(file_path)
                    if content is None:
                        content = original_content

            # Apply manual fixes
            if not autopep8_success:
                content = self.fix_unused_imports(content)
                content = self.fix_line_length(content)
                content = self.fix_blank_lines(content)
                content = self.fix_indentation(content)
                content = self.fix_import_order(content)
                content = self.fix_bare_except(content)
                content = self.fix_comment_spacing(content)

            # Check if content changed
            if content != original_content:
                if self.dry_run:
                    logger.info(f"Would fix: {file_path}")
                    # Show a preview of changes
                    self._show_diff_preview(original_content, content, file_path)
                else:
                    if self.write_file_safely(file_path, content):
                        logger.info(f"Fixed: {file_path}")
                        self.fixed_files += 1
                    else:
                        logger.error(f"Failed to write: {file_path}")
                        return False
            else:
                logger.debug(f"No changes needed: {file_path}")

            self.processed_files += 1
            return True

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.errors.append(f"{file_path}: {e}")
            return False

    def _show_diff_preview(self, original: str, fixed: str, file_path: str) -> None:
        """Show a brief preview of changes"""
        original_lines = original.split("\n")
        fixed_lines = fixed.split("\n")

        changes = 0
        for i, (orig, fix) in enumerate(zip(original_lines, fixed_lines, strict=False)):
            if orig != fix:
                changes += 1
                if changes <= 3:  # Show first 3 changes
                    logger.info(f"  Line {i + 1}: '{orig.strip()}' -> '{fix.strip()}'")

        if len(fixed_lines) != len(original_lines):
            logger.info(f"  Line count: {len(original_lines)} -> {len(fixed_lines)}")

        if changes > 3:
            logger.info(f"  ... and {changes - 3} more changes")

    def process_files(self, file_paths: list[str]) -> None:
        """Process multiple files with progress reporting"""
        total_files = len(file_paths)
        logger.info(f"Starting to process {total_files} files")

        for i, file_path in enumerate(file_paths, 1):
            if i % 10 == 0 or i == total_files:
                logger.info(f"Progress: {i}/{total_files} files processed")

            self.fix_file(file_path)

        # Summary
        logger.info("\nProcessing complete!")
        logger.info(f"Files processed: {self.processed_files}")
        logger.info(f"Files fixed: {self.fixed_files}")
        if self.errors:
            logger.info(f"Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                logger.error(f"  {error}")
            if len(self.errors) > 5:
                logger.error(f"  ... and {len(self.errors) - 5} more errors")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Fix Python linting issues in PAKE codebase",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backups",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target specific directory (e.g., src/services/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine target directories
    if args.target:
        if os.path.exists(args.target):
            directories = [args.target]
        else:
            logger.error(f"Target directory not found: {args.target}")
            return 1
    else:
        # Default directories to process
        directories = ["src", "tests", "scripts"]
        # Filter to existing directories
        directories = [d for d in directories if os.path.exists(d)]

    if not directories:
        logger.error("No valid directories found to process")
        return 1

    # Initialize fixer
    fixer = PythonLintingFixer(dry_run=args.dry_run, backup=not args.no_backup)

    # Find Python files
    python_files = fixer.find_python_files(directories)

    if not python_files:
        logger.info("No Python files found to process")
        return 0

    # Process files
    try:
        fixer.process_files(python_files)

        if args.dry_run:
            logger.info("\nDry run complete. Use without --dry-run to apply fixes.")
        else:
            logger.info(
                f"\nLinting fixes complete. Backup created in: {fixer.backup_dir}",
            )

        return 0

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
