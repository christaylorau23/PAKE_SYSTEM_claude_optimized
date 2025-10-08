#!/usr/bin/env python3
"""Phase 2B: Focused LibCST Application - Targeted Approach
World-Class Finish Guide - Focused application of LibCST codemods.
"""

import ast
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

import libcst as cst
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand


class FocusedIndentationFixer(VisitorBasedCodemodCommand):
    """Focused indentation fixer for specific patterns."""

    DESCRIPTION: str = "Focused indentation fixes for specific patterns."

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.fixes_applied = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Fix function definition indentation."""
        # Fix function indentation
        if hasattr(updated_node, "indent") and updated_node.indent.value == "":
            self.fixes_applied += 1
            return updated_node.with_changes(indent=cst.SimpleWhitespace("    "))

        return updated_node


def apply_focused_fix_to_file(file_path: str) -> dict[str, Any]:
    """Apply focused fix to a specific file."""
    try:
        # Read the file
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse with LibCST
        try:
            module = cst.parse_module(content)
        except cst.ParserSyntaxError:
            return {
                "success": False,
                "error": "Cannot parse with LibCST",
                "fixes_applied": 0,
                "file": file_path,
            }

        # Apply focused fixer
        context = CodemodContext()
        fixer = FocusedIndentationFixer(context)

        try:
            fixed_module = fixer.transform_module(module)

            # Write back if changes were made
            if fixer.fixes_applied > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_module.code)

                return {
                    "success": True,
                    "fixes_applied": fixer.fixes_applied,
                    "file": file_path,
                }
            return {
                "success": True,
                "fixes_applied": 0,
                "file": file_path,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Fix application error: {e}",
                "fixes_applied": 0,
                "file": file_path,
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"File processing error: {e}",
            "fixes_applied": 0,
            "file": file_path,
        }


def get_files_with_syntax_errors(project_root: str) -> list[str]:
    """Get files that have syntax errors."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--no-fix"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        files_with_errors = set()
        lines = result.stdout.split("\n")

        for line in lines:
            if "-->" in line and ".py:" in line:
                # Extract file path
                match = re.search(r"--> ([^:]+):", line)
                if match:
                    file_path = match.group(1)
                    files_with_errors.add(file_path)

        return list(files_with_errors)

    except Exception as e:
        print(f"Error getting files with syntax errors: {e}")
        return []


def main():
    """Main execution function for focused Phase 2B."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    print("🎯 Starting Focused Phase 2B: LibCST Application...")

    # Get files with syntax errors
    files_with_errors = get_files_with_syntax_errors(project_root)

    if not files_with_errors:
        print("✅ No files with syntax errors found!")
        return

    print(f"📁 Found {len(files_with_errors)} files with syntax errors")

    # Process first 20 files
    files_to_process = files_with_errors[:20]
    results = {
        "files_processed": 0,
        "files_modified": 0,
        "total_fixes": 0,
        "errors": [],
    }

    for file_path in files_to_process:
        full_path = Path(project_root) / file_path
        if full_path.exists():
            print(f"\n🔧 Processing: {file_path}")
            results["files_processed"] += 1

            fix_result = apply_focused_fix_to_file(str(full_path))

            if fix_result["success"]:
                if fix_result["fixes_applied"] > 0:
                    results["files_modified"] += 1
                    results["total_fixes"] += fix_result["fixes_applied"]
                    print(f"    ✅ Applied {fix_result['fixes_applied']} fixes")
                else:
                    print("    ℹ️  No fixes needed")
            else:
                print(f"    ❌ Failed: {fix_result['error']}")
                results["errors"].append(fix_result)

    print("\n✅ Focused Phase 2B Complete!")
    print(f"🎯 Files Processed: {results['files_processed']}")
    print(f"📁 Files Modified: {results['files_modified']}")
    print(f"🔧 Total Fixes Applied: {results['total_fixes']}")

    # Check remaining syntax errors
    print("\n🔍 Checking remaining syntax errors...")
    try:
        result = subprocess.run(
            ["ruff", "check", "--statistics"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.split("\n"):
                if "invalid-syntax" in line:
                    match = re.search(r"(\d+)\s+invalid-syntax", line)
                    if match:
                        syntax_count = int(match.group(1))
                        print(f"🎯 Remaining syntax errors: {syntax_count}")
                        break

    except Exception as e:
        print(f"Error checking remaining syntax errors: {e}")


if __name__ == "__main__":
    main()
