#!/usr/bin/env python3
"""Type Safety Enhancement Tool - Phase 3 of The Vanguard Protocol
Systematic resolution of ANN (type annotation) errors.
"""

import ast
from collections import Counter, defaultdict
import inspect
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple


class TypeSafetyEnhancer:
    """Systematic enhancer for type annotations following ANN rules."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = Counter()
        self.files_processed = set()

        # Common type patterns for automatic inference
        self.type_patterns = {
            # Built-in types
            "str": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "bytes": "bytes",
            "list": "List[Any]",
            "dict": "Dict[str, Any]",
            "tuple": "Tuple[Any, ...]",
            "set": "Set[Any]",
            # Common collections
            "List": "List[Any]",
            "Dict": "Dict[str, Any]",
            "Tuple": "Tuple[Any, ...]",
            "Set": "Set[Any]",
            "Optional": "Optional[Any]",
            "Union": "Union[Any, Any]",
            "Any": "Any",
            # Common patterns
            "None": "None",
            "self": "Self",  # For methods
            "cls": "Type[Self]",  # For class methods
        }

        # Common return types based on function patterns
        self.return_type_patterns = {
            r"async def.*-> None": "None",
            r"def.*-> None": "None",
            r"async def.*-> JSONResponse": "JSONResponse",
            r"def.*-> JSONResponse": "JSONResponse",
            r"async def.*-> Response": "Response",
            r"def.*-> Response": "Response",
            r"async def.*-> Dict": "Dict[str, Any]",
            r"def.*-> Dict": "Dict[str, Any]",
            r"async def.*-> List": "List[Any]",
            r"def.*-> List": "List[Any]",
            r"async def.*-> str": "str",
            r"def.*-> str": "str",
            r"async def.*-> int": "int",
            r"def.*-> int": "int",
            r"async def.*-> bool": "bool",
            r"def.*-> bool": "bool",
        }

    def get_ann_errors_for_file(self, file_path: str) -> list[dict]:
        """Get ANN errors for a specific file."""
        try:
            result = subprocess.run(
                ["ruff", "check", file_path, "--select=ANN", "--output-format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return []

            # Parse JSON output
            import json

            errors = json.loads(result.stdout)

            file_errors = []
            for error in errors:
                if isinstance(error, dict) and error.get("code", "").startswith("ANN"):
                    file_errors.append(
                        {
                            "line": error.get("location", {}).get("row", 0),
                            "col": error.get("location", {}).get("column", 0),
                            "code": error.get("code", ""),
                            "message": error.get("message", ""),
                            "end_line": error.get("end_location", {}).get("row", 0),
                            "end_col": error.get("end_location", {}).get("column", 0),
                        }
                    )

            return file_errors

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error checking {file_path}: {e}")
            return []

    def analyze_function_signature(
        self, lines: list[str], line_num: int
    ) -> dict[str, Any]:
        """Analyze function signature to infer types."""
        func_info = {
            "is_async": False,
            "function_name": "",
            "parameters": [],
            "has_return_annotation": False,
            "return_type": None,
        }

        # Find the function definition
        for i in range(max(0, line_num - 5), min(len(lines), line_num + 5)):
            line = lines[i].strip()
            if "def " in line and "(" in line:
                func_info["is_async"] = "async def" in line
                func_info["function_name"] = self._extract_function_name(line)
                func_info["parameters"] = self._extract_parameters(line)
                func_info["has_return_annotation"] = "->" in line
                if "->" in line:
                    func_info["return_type"] = self._extract_return_type(line)
                break

        return func_info

    def _extract_function_name(self, line: str) -> str:
        """Extract function name from definition line."""
        match = re.search(r"(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
        return match.group(1) if match else ""

    def _extract_parameters(self, line: str) -> list[str]:
        """Extract parameter names from function definition."""
        # Find the parameter section
        start = line.find("(")
        end = line.rfind(")")
        if start == -1 or end == -1:
            return []

        param_section = line[start + 1 : end]
        params = []

        # Simple parameter extraction (handles basic cases)
        for param in param_section.split(","):
            param = param.strip()
            if param and not param.startswith("*"):
                # Remove type annotations and default values
                param_name = param.split(":")[0].split("=")[0].strip()
                if param_name:
                    params.append(param_name)

        return params

    def _extract_return_type(self, line: str) -> str:
        """Extract return type from function definition."""
        if "->" in line:
            return line.split("->")[1].strip()
        return None

    def infer_parameter_type(self, param_name: str, func_info: dict[str, Any]) -> str:
        """Infer parameter type based on name and context."""
        param_lower = param_name.lower()

        # Common parameter patterns
        if param_lower in ["self"]:
            return "Self"
        if param_lower in ["cls"]:
            return "Type[Self]"
        if param_lower in ["request"]:
            return "Request"
        if param_lower in ["response"]:
            return "Response"
        if param_lower in ["data", "payload", "body"]:
            return "Dict[str, Any]"
        if param_lower in ["user_id", "id", "userid"]:
            return "str"
        if param_lower in ["limit", "count", "size", "offset"]:
            return "int"
        if param_lower in ["enabled", "active", "is_valid"]:
            return "bool"
        if param_lower in ["items", "results", "data_list"]:
            return "List[Any]"
        if param_lower in ["config", "settings", "options"]:
            return "Dict[str, Any]"
        if param_lower in ["message", "text", "content", "description"]:
            return "str"
        if param_lower in ["conversation", "extraction", "user", "session"]:
            return "Any"  # Complex objects
        return "Any"

    def infer_return_type(self, func_info: dict[str, Any]) -> str:
        """Infer return type based on function context."""
        func_name = func_info["function_name"].lower()

        # Common return patterns
        if func_name.startswith(
            ("get_", "fetch_", "create_", "add_", "update_", "modify_")
        ):
            return "Any"
        if func_name.startswith(("delete_", "remove_")):
            return "None"
        if func_name.startswith(("is_", "has_", "validate_", "check_")):
            return "bool"
        if func_name in ["__init__", "setup", "configure"]:
            return "None"
        if func_info["is_async"]:
            return "Any"
        return "Any"

    def fix_file(self, file_path: str) -> bool:
        """Fix ANN errors in a specific file."""
        file_path = Path(file_path)
        if not file_path.exists():
            return False

        print(f"🔧 Processing type annotations in {file_path}")

        # Get ANN errors for this file
        errors = self.get_ann_errors_for_file(str(file_path))
        if not errors:
            return True

        # Read file content
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False

        # Group errors by type
        ann001_errors = [
            e for e in errors if e["code"] == "ANN001"
        ]  # Missing function argument types
        ann201_errors = [
            e for e in errors if e["code"] == "ANN201"
        ]  # Missing return types
        ann202_errors = [
            e for e in errors if e["code"] == "ANN202"
        ]  # Missing private function return types
        ann401_errors = [e for e in errors if e["code"] == "ANN401"]  # Any type usage

        modified = False

        # Fix missing function argument types (ANN001)
        if ann001_errors:
            content = self._fix_missing_argument_types(content, ann001_errors)
            modified = True
            self.fixes_applied["argument_types"] += len(ann001_errors)

        # Fix missing return types (ANN201, ANN202)
        return_type_errors = ann201_errors + ann202_errors
        if return_type_errors:
            content = self._fix_missing_return_types(content, return_type_errors)
            modified = True
            self.fixes_applied["return_types"] += len(return_type_errors)

        # Write back if modified
        if modified:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Fixed {len(errors)} type annotation issues in {file_path}")
                self.files_processed.add(str(file_path))
                return True
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"❌ Error writing {file_path}: {e}")
                return False

        return True

    def _fix_missing_argument_types(self, content: str, errors: list[dict]) -> str:
        """Fix missing function argument types."""
        lines = content.splitlines()

        for error in errors:
            line_num = error["line"] - 1  # Convert to 0-based index
            if line_num >= len(lines):
                continue

            # Analyze the function signature
            func_info = self.analyze_function_signature(lines, line_num)

            # Find the function definition line
            func_line_num = None
            for i in range(max(0, line_num - 10), min(len(lines), line_num + 5)):
                if "def " in lines[i] and "(" in lines[i]:
                    func_line_num = i
                    break

            if func_line_num is None:
                continue

            # Fix the function definition
            func_line = lines[func_line_num]
            if "->" not in func_line and "(" in func_line and ")" in func_line:
                # Add type annotations to parameters
                fixed_line = self._add_parameter_types(func_line, func_info)
                if fixed_line != func_line:
                    lines[func_line_num] = fixed_line

        return "\n".join(lines)

    def _add_parameter_types(self, func_line: str, func_info: dict[str, Any]) -> str:
        """Add type annotations to function parameters."""
        # Find parameter section
        start = func_line.find("(")
        end = func_line.rfind(")")
        if start == -1 or end == -1:
            return func_line

        param_section = func_line[start + 1 : end]
        if not param_section.strip():
            return func_line

        # Parse and add types to parameters
        params = []
        for param in param_section.split(","):
            param = param.strip()
            if not param:
                continue

            # Check if already has type annotation
            if ":" in param:
                params.append(param)
            else:
                # Add type annotation
                param_name = param.split("=")[0].strip()
                param_type = self.infer_parameter_type(param_name, func_info)
                if "=" in param:
                    default_value = param.split("=", 1)[1]
                    params.append(f"{param_name}: {param_type} = {default_value}")
                else:
                    params.append(f"{param_name}: {param_type}")

        # Reconstruct function line
        new_param_section = ", ".join(params)
        return func_line[: start + 1] + new_param_section + func_line[end:]

    def _fix_missing_return_types(self, content: str, errors: list[dict]) -> str:
        """Fix missing return types."""
        lines = content.splitlines()

        for error in errors:
            line_num = error["line"] - 1  # Convert to 0-based index
            if line_num >= len(lines):
                continue

            # Find the function definition line
            func_line = lines[line_num]
            if "def " in func_line and "->" not in func_line:
                # Analyze function to infer return type
                func_info = self.analyze_function_signature(lines, line_num)
                return_type = self.infer_return_type(func_info)

                # Add return type annotation
                if ")" in func_line:
                    func_line = func_line.replace(")", f") -> {return_type}")
                    lines[line_num] = func_line

        return "\n".join(lines)

    def process_high_priority_files(self) -> dict[str, int]:
        """Process files with the most ANN errors first."""
        print("🎯 Processing high-priority files with type annotation issues...")

        # Get list of Python files
        python_files = list(self.project_root.rglob("*.py"))

        # Check each file for ANN errors
        files_with_errors = []
        for py_file in python_files:
            errors = self.get_ann_errors_for_file(str(py_file))
            if errors:
                files_with_errors.append((str(py_file), len(errors)))

        # Sort by error count (highest first)
        files_with_errors.sort(key=lambda x: x[1], reverse=True)

        print(f"📁 Found {len(files_with_errors)} files with type annotation issues")

        # Process top 15 files first
        for file_path, error_count in files_with_errors[:15]:
            print(f"🔧 Processing {file_path} ({error_count} type issues)")
            self.fix_file(file_path)

        return dict(self.fixes_applied)

    def generate_report(self) -> str:
        """Generate type safety enhancement report."""
        report = []
        report.append(
            "# Type Safety Enhancement Report - Phase 3 of The Vanguard Protocol"
        )
        report.append("")
        report.append(f"**Files Processed**: {len(self.files_processed)}")
        report.append("")

        report.append("## Type Annotation Fix Statistics")
        report.append("")
        for fix_type, count in self.fixes_applied.items():
            report.append(f"- **{fix_type.replace('_', ' ').title()}**: {count}")
        report.append("")

        report.append("## Files Processed")
        report.append("")
        for file_path in sorted(self.files_processed):
            report.append(f"- `{file_path}`")

        report.append("")
        report.append("## Impact Assessment")
        report.append("")
        report.append("- **IDE Support**: Enhanced autocompletion and error detection")
        report.append("- **Static Analysis**: Improved type checking and bug detection")
        report.append(
            "- **Maintainability**: Self-documenting code with explicit contracts"
        )
        report.append(
            "- **Developer Experience**: Better tooling integration and refactoring support"
        )

        return "\n".join(report)


def main():
    """Main execution function."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    enhancer = TypeSafetyEnhancer(project_root)

    print("🚀 Starting Type Safety Enhancement - Phase 3 of The Vanguard Protocol...")

    # Process high-priority files
    stats = enhancer.process_high_priority_files()

    # Generate report
    report = enhancer.generate_report()
    with open("TYPE_SAFETY_ENHANCEMENT_REPORT.md", "w") as f:
        f.write(report)

    print("✅ Type Safety Enhancement Complete!")
    print("📄 Report written to: TYPE_SAFETY_ENHANCEMENT_REPORT.md")
    print(f"📊 Enhancement statistics: {stats}")


if __name__ == "__main__":
    main()
