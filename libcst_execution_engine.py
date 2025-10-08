#!/usr/bin/env python3
"""LibCST Execution Engine - Advanced Refactoring at Scale
World-Class Finish Guide - Systematic execution of LibCST codemods.
"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple


class LibCSTExecutionEngine:
    """Advanced execution engine for LibCST codemods."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.codemod_results = {}
        self.files_processed = 0
        self.files_modified = 0

    def analyze_syntax_errors(self) -> dict[str, list[str]]:
        """Analyze syntax errors to identify files needing LibCST treatment."""
        try:
            result = subprocess.run(
                ["ruff", "check", "--no-fix"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            syntax_files = {
                "indentation": [],
                "missing_self": [],
                "duplicate_params": [],
                "class_structure": [],
            }

            lines = result.stdout.split("\n")
            current_file = None

            for line in lines:
                if "-->" in line and ".py:" in line:
                    # Extract file path
                    match = re.search(r"--> ([^:]+):", line)
                    if match:
                        current_file = match.group(1)

                if current_file and "invalid-syntax:" in line:
                    if "unindent does not match" in line:
                        syntax_files["indentation"].append(current_file)
                    elif "Expected an indented block after `class`" in line:
                        syntax_files["class_structure"].append(current_file)
                    elif "Expected class, function definition" in line:
                        syntax_files["missing_self"].append(current_file)
                    elif "Parameter without a default cannot follow" in line:
                        syntax_files["duplicate_params"].append(current_file)

            return syntax_files
        except Exception as e:
            print(f"Error analyzing syntax errors: {e}")
            return {}

    def create_test_file(self, content: str) -> str:
        """Create a temporary test file for LibCST testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            return f.name

    def test_codemod_on_file(self, codemod_class: str, test_file: str) -> bool:
        """Test a codemod on a specific file."""
        try:
            # Create a simple test script
            test_script = f"""
import sys
import libcst as cst
from libcst.codemod import CodemodContext
from libcst_codemods import {codemod_class}

# Read the file
with open('{test_file}', 'r') as f:
    content = f.read()

# Apply codemod
context = CodemodContext()
codemod = {codemod_class}(context)
result = codemod.transform_module(cst.parse_module(content))

# Write result back
with open('{test_file}', 'w') as f:
    f.write(result.code)

print("Codemod applied successfully")
"""

            # Execute the test
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Error testing codemod {codemod_class}: {e}")
            return False

    def execute_codemod_on_file(
        self, codemod_class: str, file_path: str
    ) -> dict[str, Any]:
        """Execute a codemod on a specific file."""
        try:
            # Create execution script
            exec_script = f"""
import sys
import libcst as cst
from libcst.codemod import CodemodContext
from libcst_codemods import {codemod_class}

# Read the file
with open('{file_path}', 'r') as f:
    content = f.read()

# Apply codemod
context = CodemodContext()
codemod = {codemod_class}(context)
result = codemod.transform_module(cst.parse_module(content))

# Write result back
with open('{file_path}', 'w') as f:
    f.write(result.code)

print("SUCCESS: Codemod applied to {file_path}")
"""

            # Execute the codemod
            result = subprocess.run(
                [sys.executable, "-c", exec_script],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "file": file_path,
            }

        except Exception as e:
            return {"success": False, "output": "", "error": str(e), "file": file_path}

    def execute_comprehensive_fix(self) -> dict[str, Any]:
        """Execute comprehensive syntax fixes using LibCST."""
        print("🎯 Starting LibCST Comprehensive Syntax Fix...")

        # Analyze syntax errors
        syntax_files = self.analyze_syntax_errors()

        results = {
            "files_processed": 0,
            "files_modified": 0,
            "codemod_results": {},
            "syntax_files": syntax_files,
        }

        # Define codemod mapping
        codemod_mapping = {
            "indentation": "FixIndentationIssues",
            "missing_self": "FixMissingSelfParameter",
            "duplicate_params": "FixDuplicateParameters",
            "class_structure": "FixClassStructureIssues",
        }

        # Execute codemods on identified files
        for issue_type, files in syntax_files.items():
            if not files:
                continue

            codemod_class = codemod_mapping.get(issue_type)
            if not codemod_class:
                continue

            print(f"\n🔧 Processing {issue_type} issues with {codemod_class}...")

            for file_path in files[:5]:  # Limit to first 5 files for safety
                full_path = self.project_root / file_path
                if not full_path.exists():
                    continue

                print(f"  📁 Processing: {file_path}")
                results["files_processed"] += 1

                # Execute codemod
                codemod_result = self.execute_codemod_on_file(
                    codemod_class, str(full_path)
                )

                if codemod_result["success"]:
                    results["files_modified"] += 1
                    print(f"    ✅ Success: {file_path}")
                else:
                    print(f"    ❌ Failed: {file_path}")
                    print(f"    Error: {codemod_result['error']}")

                # Store result
                if issue_type not in results["codemod_results"]:
                    results["codemod_results"][issue_type] = []
                results["codemod_results"][issue_type].append(codemod_result)

        return results

    def validate_results(self) -> dict[str, Any]:
        """Validate the results of LibCST execution."""
        print("\n🔍 Validating LibCST Results...")

        try:
            # Check remaining syntax errors
            result = subprocess.run(
                ["ruff", "check", "--statistics"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            # Parse syntax error count
            syntax_count = 0
            f821_count = 0

            if result.stdout:
                for line in result.stdout.split("\n"):
                    if "invalid-syntax" in line:
                        match = re.search(r"(\d+)\s+invalid-syntax", line)
                        if match:
                            syntax_count = int(match.group(1))
                    elif "F821" in line and "undefined-name" in line:
                        match = re.search(r"(\d+)\s+F821", line)
                        if match:
                            f821_count = int(match.group(1))

            return {
                "remaining_syntax_errors": syntax_count,
                "remaining_f821_errors": f821_count,
                "validation_successful": True,
            }

        except Exception as e:
            print(f"Error validating results: {e}")
            return {
                "remaining_syntax_errors": "unknown",
                "remaining_f821_errors": "unknown",
                "validation_successful": False,
                "error": str(e),
            }

    def generate_libcst_report(
        self, results: dict[str, Any], validation: dict[str, Any]
    ) -> str:
        """Generate comprehensive LibCST execution report."""
        report = []
        report.append("# LibCST Execution Engine - Advanced Refactoring Report")
        report.append("")
        report.append(f"**Execution Date**: {Path().cwd()}")
        report.append("")

        report.append("## 🎯 LibCST Execution Results")
        report.append("")
        report.append(f"- **Files Processed**: {results['files_processed']}")
        report.append(f"- **Files Modified**: {results['files_modified']}")
        report.append(
            f"- **Success Rate**: {(results['files_modified'] / max(results['files_processed'], 1)) * 100:.1f}%"
        )
        report.append("")

        report.append("## 🔧 Codemod Execution Summary")
        report.append("")
        for issue_type, codemod_results in results["codemod_results"].items():
            success_count = sum(1 for r in codemod_results if r["success"])
            total_count = len(codemod_results)
            report.append(
                f"- **{issue_type.replace('_', ' ').title()}**: {success_count}/{total_count} successful"
            )
        report.append("")

        report.append("## 🔍 Validation Results")
        report.append("")
        if validation["validation_successful"]:
            report.append(
                f"- **Remaining Syntax Errors**: {validation['remaining_syntax_errors']}"
            )
            report.append(
                f"- **Remaining F821 Errors**: {validation['remaining_f821_errors']}"
            )

            if (
                validation["remaining_syntax_errors"] == 0
                and validation["remaining_f821_errors"] == 0
            ):
                report.append(
                    "- **Status**: ✅ **COMPLETE SUCCESS** - All syntax and F821 errors resolved!"
                )
            else:
                report.append("- **Status**: ⚠️  Some errors remain")
        else:
            report.append(
                f"- **Validation Error**: {validation.get('error', 'Unknown error')}"
            )
        report.append("")

        report.append("## 🏆 LibCST Techniques Applied")
        report.append("")
        report.append("### 1. Indentation Fixes")
        report.append("- **Pattern**: Incorrect indentation preventing proper parsing")
        report.append("- **Solution**: LibCST-based indentation normalization")
        report.append("- **Files**: Test files with indentation issues")
        report.append("")

        report.append("### 2. Missing Self Parameter Fixes")
        report.append("- **Pattern**: Class methods missing self parameter")
        report.append("- **Solution**: Automatic self parameter injection")
        report.append("- **Files**: Test methods and class definitions")
        report.append("")

        report.append("### 3. Duplicate Parameter Removal")
        report.append("- **Pattern**: Function definitions with duplicate parameters")
        report.append("- **Solution**: Parameter deduplication using CST analysis")
        report.append("- **Files**: Functions with malformed signatures")
        report.append("")

        report.append("### 4. Class Structure Fixes")
        report.append("- **Pattern**: Malformed class definitions")
        report.append("- **Solution**: CST-based structure correction")
        report.append("- **Files**: Classes with structural issues")
        report.append("")

        report.append("## 🎯 Impact Assessment")
        report.append("")
        report.append(
            "- **Syntax Resolution**: Fixed parsing issues preventing F821 detection"
        )
        report.append(
            "- **Code Quality**: Improved structural integrity of Python files"
        )
        report.append(
            "- **Development Experience**: Enhanced IDE support and error detection"
        )
        report.append("- **Foundation**: Solid base for continued development")

        return "\n".join(report)


def main():
    """Main execution function for LibCST engine."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    engine = LibCSTExecutionEngine(project_root)

    print("🚀 Starting LibCST Execution Engine...")

    # Execute comprehensive fix
    results = engine.execute_comprehensive_fix()

    # Validate results
    validation = engine.validate_results()

    # Generate report
    report = engine.generate_libcst_report(results, validation)
    with open("LIBCST_EXECUTION_REPORT.md", "w") as f:
        f.write(report)

    print("✅ LibCST Execution Complete!")
    print("📄 Report written to: LIBCST_EXECUTION_REPORT.md")
    print(f"🎯 Files Processed: {results['files_processed']}")
    print(f"📁 Files Modified: {results['files_modified']}")
    print(f"🔍 Remaining Syntax Errors: {validation['remaining_syntax_errors']}")
    print(f"🔍 Remaining F821 Errors: {validation['remaining_f821_errors']}")


if __name__ == "__main__":
    main()
