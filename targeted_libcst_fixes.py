#!/usr/bin/env python3
"""Targeted LibCST Fixes - Focused on Specific Syntax Issues
World-Class Finish Guide - Surgical fixes for remaining syntax errors.
"""

from pathlib import Path
import re
from typing import Any, Optional

import libcst as cst
from libcst.codemod import VisitorBasedCodemodCommand


class TargetedSyntaxFixer(VisitorBasedCodemodCommand):
    """Targeted syntax fixer for specific issues identified in the codebase."""

    DESCRIPTION: str = "Fixes specific syntax issues preventing F821 detection."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.fixes_applied = 0

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Fix class definition issues."""
        # Ensure class has proper body indentation
        if updated_node.body and hasattr(updated_node.body, "indent"):
            if updated_node.body.indent.value == "":
                self.fixes_applied += 1
                return updated_node.with_changes(
                    body=updated_node.body.with_changes(
                        indent=cst.SimpleWhitespace("    ")
                    )
                )
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Fix function definition issues."""
        # Fix indentation for function definitions
        if hasattr(updated_node, "indent") and updated_node.indent.value == "":
            self.fixes_applied += 1
            return updated_node.with_changes(indent=cst.SimpleWhitespace("    "))

        # Fix function body indentation
        if updated_node.body and hasattr(updated_node.body, "indent"):
            if updated_node.body.indent.value == "":
                self.fixes_applied += 1
                return updated_node.with_changes(
                    body=updated_node.body.with_changes(
                        indent=cst.SimpleWhitespace("        ")
                    )
                )

        return updated_node


def fix_file_with_libcst(file_path: str) -> bool:
    """Fix a specific file using LibCST."""
    try:
        # Read the file
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Try to parse with LibCST
        try:
            module = cst.parse_module(content)
        except cst.ParserSyntaxError as e:
            print(f"  ⚠️  Syntax error in {file_path}: {e}")
            return False

        # Apply fixes
        from libcst.codemod import CodemodContext

        context = CodemodContext()
        fixer = TargetedSyntaxFixer(context)

        try:
            fixed_module = fixer.transform_module(module)

            # Write back if changes were made
            if fixer.fixes_applied > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_module.code)
                print(f"  ✅ Fixed {fixer.fixes_applied} issues in {file_path}")
                return True
            print(f"  ℹ️  No fixes needed for {file_path}")
            return True

        except Exception as e:
            print(f"  ❌ Error applying fixes to {file_path}: {e}")
            return False

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def identify_problematic_files(project_root: str) -> list:
    """Identify files with syntax issues."""
    import subprocess

    try:
        result = subprocess.run(
            ["ruff", "check", "--no-fix"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        problematic_files = set()
        lines = result.stdout.split("\n")

        for line in lines:
            if "-->" in line and ".py:" in line:
                match = re.search(r"--> ([^:]+):", line)
                if match:
                    file_path = match.group(1)
                    # Only include files with syntax errors
                    if "invalid-syntax:" in result.stdout:
                        problematic_files.add(file_path)

        return list(problematic_files)

    except Exception as e:
        print(f"Error identifying problematic files: {e}")
        return []


def main():
    """Main execution function for targeted LibCST fixes."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    print("🎯 Starting Targeted LibCST Syntax Fixes...")

    # Identify problematic files
    problematic_files = identify_problematic_files(project_root)

    if not problematic_files:
        print("✅ No problematic files found!")
        return

    print(f"📁 Found {len(problematic_files)} files with syntax issues")

    # Process files
    fixed_count = 0
    total_count = len(problematic_files)

    for file_path in problematic_files[:10]:  # Limit to first 10 for safety
        full_path = Path(project_root) / file_path
        if full_path.exists():
            print(f"\n🔧 Processing: {file_path}")
            if fix_file_with_libcst(str(full_path)):
                fixed_count += 1

    print("\n✅ Processing complete!")
    print(f"📊 Files processed: {min(total_count, 10)}")
    print(f"🔧 Files fixed: {fixed_count}")

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
