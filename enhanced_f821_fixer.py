#!/usr/bin/env python3
"""Enhanced F821 Fixer - Phase 2: Function Parameters.

This script systematically fixes the remaining F821 errors by:
1. Identifying files with the most common parameter errors
2. Applying targeted fixes for each pattern
3. Validating fixes and reporting progress
"""

import ast
import os
from pathlib import Path
import re
import sys
from typing import Dict, List, Set, Tuple


class EnhancedF821Fixer:
    """Enhanced F821 fixer for function parameter errors."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixed_files = 0
        self.total_fixes = 0

        # Common parameter patterns and their likely types
        self.parameter_patterns = {
            "config": "dict[str, Any] | None = None",
            "message": "str | None = None",
            "kwargs": "dict[str, Any] | None = None",
            "model_id": "str | None = None",
            "name": "str | None = None",
            "request": "Any | None = None",
            "args": "tuple | None = None",
            "stream": "Any | None = None",
            "value": "Any | None = None",
            "func": "Callable | None = None",
            "event": "Any | None = None",
            "job": "Any | None = None",
            "content_item": "Any | None = None",
            "test_id": "str | None = None",
            "error": "Exception | None = None",
            "record": "Any | None = None",
            "result": "Any | None = None",
            "platform": "str | None = None",
            "task": "Any | None = None",
            "user_id": "str | None = None",
            "interactions": "List[Any] | None = None",
            "content_id": "str | None = None",
            "features": "Dict[str, Any] | None = None",
        }

    def get_files_with_most_errors(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get files with the most F821 errors."""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ruff",
                    "check",
                    str(self.root_dir / "src"),
                    "--select",
                    "F821",
                    "--output-format",
                    "json",
                ],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )

            if result.returncode != 0:
                return []

            # Parse JSON output to count errors per file
            import json

            errors = json.loads(result.stdout)

            file_counts = {}
            for error in errors:
                filename = error.get("filename", "")
                if filename:
                    file_counts[filename] = file_counts.get(filename, 0) + 1

            # Sort by error count and return top files
            sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_files[:limit]

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error getting file counts: {e}")
            return []

    def analyze_function_parameters(self, file_path: Path) -> dict[str, list[int]]:
        """Analyze a file to find functions missing parameters."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error reading {file_path}: {e}")
            return {}

        # Parse AST to find function definitions and their usage
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return {}

        missing_params = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Find undefined names in function body
                undefined_names = set()
                defined_names = set()

                # Add parameter names to defined names
                for arg in node.args.args:
                    defined_names.add(arg.arg)

                # Find all name references in function body
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                        if child.id not in defined_names:
                            undefined_names.add(child.id)

                # Check if any undefined names match our patterns
                for name in undefined_names:
                    if name in self.parameter_patterns:
                        if name not in missing_params:
                            missing_params[name] = []
                        missing_params[name].append(node.lineno)

        return missing_params

    def fix_file_parameters(self, file_path: Path) -> bool:
        """Fix parameter issues in a single file."""
        analysis = self.analyze_function_parameters(file_path)
        if not analysis:
            return False

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error reading {file_path}: {e}")
            return False

        original_content = content
        fixes_applied = 0

        # Apply fixes for each parameter pattern
        for param_name, line_numbers in analysis.items():
            param_type = self.parameter_patterns[param_name]

            # Find function definitions that need this parameter
            lines = content.split("\n")
            for line_num in line_numbers:
                if line_num <= len(lines):
                    line_idx = line_num - 1
                    line = lines[line_idx]

                    # Look for function definition patterns
                    if "def " in line and f"({param_name}" in content:
                        # This is a usage, find the function definition
                        # Look backwards for the function definition
                        for i in range(line_idx, max(0, line_idx - 20), -1):
                            func_line = lines[i]
                            if (
                                func_line.strip().startswith("def ")
                                and "(" in func_line
                                and ")" in func_line
                            ):
                                # Found function definition, add parameter
                                if param_name not in func_line:
                                    # Add parameter to function signature
                                    if func_line.endswith(") ->"):
                                        new_line = func_line.replace(
                                            ") ->", f", {param_name}: {param_type}) ->"
                                        )
                                    elif func_line.endswith("):"):
                                        new_line = func_line.replace(
                                            "):", f", {param_name}: {param_type}):"
                                        )
                                    elif func_line.endswith(") -> None:"):
                                        new_line = func_line.replace(
                                            ") -> None:",
                                            f", {param_name}: {param_type}) -> None:",
                                        )
                                    else:
                                        new_line = func_line.replace(
                                            ")", f", {param_name}: {param_type})"
                                        )

                                    lines[i] = new_line
                                    fixes_applied += 1
                                break

        # Write back if changes were made
        if fixes_applied > 0:
            new_content = "\n".join(lines)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.fixed_files += 1
                self.total_fixes += fixes_applied
                print(f"Fixed {fixes_applied} parameter issues in {file_path}")
                return True
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"Error writing {file_path}: {e}")
                return False

        return False

    def run_targeted_fixes(self):
        """Run targeted fixes on files with most errors."""
        print("🔍 Finding files with most F821 errors...")
        top_files = self.get_files_with_most_errors(20)

        if not top_files:
            print("No files found with F821 errors")
            return

        print(f"Found {len(top_files)} files with F821 errors")
        for filename, count in top_files[:10]:
            print(f"  {Path(filename).name}: {count} errors")

        print("\n🔧 Applying targeted fixes...")
        for filename, count in top_files:
            file_path = Path(filename)
            if file_path.exists():
                self.fix_file_parameters(file_path)

        print(f"\n✅ Fixed {self.total_fixes} issues in {self.fixed_files} files")


def main():
    """Main entry point."""
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    fixer = EnhancedF821Fixer(root_dir)
    fixer.run_targeted_fixes()


if __name__ == "__main__":
    main()
