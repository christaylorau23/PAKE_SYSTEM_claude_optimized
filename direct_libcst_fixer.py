#!/usr/bin/env python3
"""Direct LibCST Fixer - Targeted Approach
World-Class Finish Guide - Direct fix for known indentation issues.
"""

from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

import libcst as cst
from libcst.codemod import VisitorBasedCodemodCommand


class DirectIndentationFixer(VisitorBasedCodemodCommand):
    """Direct indentation fixer for specific patterns."""

    DESCRIPTION: str = "Fixes indentation issues in function definitions."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.fixes_applied = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Fix function definition indentation issues."""
        # Fix function indentation (should be at class level)
        if hasattr(updated_node, "indent") and updated_node.indent.value == "":
            self.fixes_applied += 1
            return updated_node.with_changes(indent=cst.SimpleWhitespace("    "))

        return updated_node


def fix_specific_file(file_path: str) -> dict[str, Any]:
    """Fix a specific file using direct LibCST approach."""
    try:
        # Read the file
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Try to parse with LibCST
        try:
            module = cst.parse_module(content)
        except cst.ParserSyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
                "fixes_applied": 0,
                "file": file_path,
            }

        # Apply direct fixes
        from libcst.codemod import CodemodContext

        context = CodemodContext()
        fixer = DirectIndentationFixer(context)

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
            return {"success": True, "fixes_applied": 0, "file": file_path}

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


def main():
    """Main execution function for direct LibCST fix."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    print("🎯 Starting Direct LibCST Indentation Fix...")

    # Target specific files we know have issues
    target_files = [
        "data/repositories/NoteRepository.py",
        "performance_tests/database_profiler.py",
        "tests/contract/test_api_gateway_health.py",
        "tests/data/test_vector_memory_database.py",
        "tests/e2e/auth/test_auth_comprehensive_e2e.py",
    ]

    results = {
        "files_processed": 0,
        "files_modified": 0,
        "total_fixes": 0,
        "errors": [],
    }

    for file_path in target_files:
        full_path = Path(project_root) / file_path
        if full_path.exists():
            print(f"\n🔧 Processing: {file_path}")
            results["files_processed"] += 1

            fix_result = fix_specific_file(str(full_path))

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

    print("\n✅ Direct LibCST Fix Complete!")
    print(f"🎯 Files Processed: {results['files_processed']}")
    print(f"📁 Files Modified: {results['files_modified']}")
    print(f"🔧 Total Fixes Applied: {results['total_fixes']}")

    # Validate results
    print("\n🔍 Validating results...")
    try:
        result = subprocess.run(
            ["ruff", "check", "--select=F821", "--statistics"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        f821_count = 0
        if result.stdout:
            for line in result.stdout.split("\n"):
                if "F821" in line and "undefined-name" in line:
                    match = re.search(r"(\d+)\s+F821", line)
                    if match:
                        f821_count = int(match.group(1))
                        break

        print(f"🎯 Remaining F821 errors: {f821_count}")

    except Exception as e:
        print(f"Error validating results: {e}")


if __name__ == "__main__":
    main()
