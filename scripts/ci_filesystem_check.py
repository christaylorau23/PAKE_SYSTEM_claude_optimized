#!/usr/bin/env python3
"""
PAKE System - Comprehensive CI Filesystem Diagnostics
====================================================

This script provides comprehensive filesystem analysis specifically designed
for CI environments to identify case sensitivity, path resolution, and
permission issues that cause "works on my machine" problems.

Key Features:
1. Case sensitivity analysis (Linux vs macOS/Windows)
2. Import statement validation
3. Path resolution testing
4. Permission pattern analysis
5. Working directory assumption detection
6. sys.path manipulation audit

Usage:
    python scripts/ci_filesystem_check.py [--verbose] [--fix] [--output FILE]
"""

import argparse
import ast
from collections import defaultdict
import json
import logging
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CIFilesystemDiagnostics:
    """Comprehensive CI filesystem diagnostics"""

    def __init__(self, root_path: str | None = None, verbose: bool = False) -> None:
        self.root_path = Path(root_path or os.getcwd())
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.fixes_applied = []

        # Track patterns
        self.import_patterns = defaultdict(list)
        self.case_mismatches = []
        self.sys_path_issues = []
        self.permission_issues = []
        self.path_resolution_issues = []

    def run_comprehensive_analysis(self) -> dict[str, Any]:
        """Run comprehensive filesystem analysis"""
        logger.info(
            "🔍 Running comprehensive CI filesystem analysis at: %s", self.root_path
        )

        results = {
            "filesystem_info": self._analyze_filesystem_info(),
            "case_sensitivity": self._analyze_case_sensitivity(),
            "import_validation": self._validate_imports(),
            "path_resolution": self._analyze_path_resolution(),
            "permissions": self._analyze_permissions(),
            "working_directory": self._analyze_working_directory(),
            "sys_path_audit": self._audit_sys_path(),
            "ci_compatibility": self._assess_ci_compatibility(),
            "summary": {},
        }

        # Generate summary
        results["summary"] = self._generate_summary(results)

        return results

    def _analyze_filesystem_info(self) -> dict[str, Any]:
        """Analyze basic filesystem information"""
        logger.info("📊 Analyzing filesystem information...")

        return {
            "root_path": str(self.root_path),
            "current_working_directory": os.getcwd(),
            "python_version": sys.version,
            "python_path": sys.path[:5],  # First 5 entries
            "case_sensitivity": self._test_case_sensitivity(),
            "directory_structure": self._analyze_directory_structure(),
            "file_counts": self._count_files_by_type(),
        }

    def _test_case_sensitivity(self) -> dict[str, Any]:
        """Test filesystem case sensitivity"""
        test_file = self.root_path / "ci_test_case.txt"
        test_file_upper = self.root_path / "CI_TEST_CASE.txt"

        try:
            # Create test files
            test_file.write_text("test")
            test_file_upper.write_text("TEST")

            # Test if both files exist (case-sensitive) or only one (case-insensitive)
            both_exist = test_file.exists() and test_file_upper.exists()

            # Clean up
            test_file.unlink(missing_ok=True)
            test_file_upper.unlink(missing_ok=True)

            return {
                "is_case_sensitive": both_exist,
                "filesystem_type": "Case-sensitive (Linux)"
                if both_exist
                else "Case-insensitive (macOS/Windows)",
                "ci_compatible": both_exist,  # Linux CI is case-sensitive
            }
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning("Error testing case sensitivity: %s", e)
            return {
                "is_case_sensitive": True,  # Assume case-sensitive for safety
                "filesystem_type": "Unknown",
                "ci_compatible": True,
            }

    def _analyze_directory_structure(self) -> dict[str, Any]:
        """Analyze directory structure for issues"""
        structure = {
            "required_dirs": [],
            "hyphenated_dirs": [],
            "problematic_patterns": [],
        }

        # Check required directories
        required = ["src", "tests", "scripts"]
        for req_dir in required:
            path = self.root_path / req_dir
            if path.exists():
                structure["required_dirs"].append({"name": req_dir, "exists": True})
            else:
                structure["required_dirs"].append({"name": req_dir, "exists": False})
                self.issues.append(f"Missing required directory: {req_dir}")

        # Find hyphenated directories
        hyphenated = list(self.root_path.rglob("*-*"))
        for hyp_dir in hyphenated:
            if hyp_dir.is_dir() and "node_modules" not in str(hyp_dir):
                structure["hyphenated_dirs"].append(
                    {
                        "path": str(hyp_dir),
                        "issue": "hyphenated_directory_name",
                        "recommendation": "Rename to use underscores for Python compatibility",
                    }
                )
                self.issues.append(f"Hyphenated directory: {hyp_dir}")

        return structure

    def _count_files_by_type(self) -> dict[str, int]:
        """Count files by type"""
        counts = defaultdict(int)

        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                counts[suffix] += 1

        return dict(counts)

    def _analyze_case_sensitivity(self) -> dict[str, Any]:
        """Analyze case sensitivity issues"""
        logger.info("📁 Analyzing case sensitivity issues...")

        issues = {
            "import_case_mismatches": [],
            "file_case_mismatches": [],
            "directory_case_mismatches": [],
            "recommendations": [],
        }

        # Check Python files for case issues
        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Parse imports
                tree = ast.parse(content)
                imports = self._extract_imports(tree)

                for import_stmt in imports:
                    mismatch = self._check_import_case_mismatch(py_file, import_stmt)
                    if mismatch:
                        issues["import_case_mismatches"].append(mismatch)

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error analyzing %s: %s", py_file, e)

        # Check for hyphenated directory imports
        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Look for imports with hyphens
                hyphen_pattern = r"from\s+.*services\..*-.*import"
                matches = re.findall(hyphen_pattern, content)

                for match in matches:
                    issues["import_case_mismatches"].append(
                        {
                            "file": str(py_file),
                            "import": match,
                            "issue": "hyphenated_module_import",
                            "recommendation": "Replace hyphens with underscores in import statements",
                        }
                    )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning(
                    "Error checking hyphenated imports in %s: %s", py_file, e
                )

        return issues

    def _extract_imports(self, tree: ast.AST) -> list[dict[str, Any]]:
        """Extract import statements from AST"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(
                        {
                            "type": "from_import",
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )

        return imports

    def _check_import_case_mismatch(
        self, file_path: Path, import_stmt: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Check if import has case sensitivity issues"""
        module_path = import_stmt["module"]

        # Skip external packages
        if not module_path.startswith("src.") and not module_path.startswith("."):
            return None

        # Convert to filesystem path
        if module_path.startswith("src."):
            fs_path = self.root_path / module_path.replace(".", "/")
        elif module_path.startswith("."):
            # Relative import
            relative_depth = len(module_path.split(".")) - 1
            fs_path = file_path.parent
            for _ in range(relative_depth):
                fs_path = fs_path.parent
            if module_path != ".":
                fs_path = fs_path / module_path.lstrip(".")

        # Check if path exists
        if not fs_path.exists():
            # Try case-insensitive search
            parent = fs_path.parent
            if parent.exists():
                for item in parent.iterdir():
                    if item.name.lower() == fs_path.name.lower():
                        return {
                            "file": str(file_path),
                            "line": import_stmt["line"],
                            "import": import_stmt,
                            "expected_path": str(fs_path),
                            "actual_path": str(item),
                            "issue": "case_mismatch",
                        }

        return None

    def _validate_imports(self) -> dict[str, Any]:
        """Validate import statements"""
        logger.info("📦 Validating import statements...")

        validation = {
            "valid_imports": [],
            "invalid_imports": [],
            "external_imports": [],
            "internal_imports": [],
        }

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                imports = self._extract_imports(tree)

                for import_stmt in imports:
                    module = import_stmt["module"]

                    if module.startswith(("src.", ".")):
                        validation["internal_imports"].append(
                            {
                                "file": str(py_file),
                                "import": import_stmt,
                                "status": "internal",
                            }
                        )
                    else:
                        validation["external_imports"].append(
                            {
                                "file": str(py_file),
                                "import": import_stmt,
                                "status": "external",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error validating imports in %s: %s", py_file, e)

        return validation

    def _analyze_path_resolution(self) -> dict[str, Any]:
        """Analyze path resolution patterns"""
        logger.info("🛤️ Analyzing path resolution...")

        issues = {
            "hardcoded_paths": [],
            "relative_paths": [],
            "working_directory_assumptions": [],
            "path_manipulation": [],
        }

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    # Hardcoded absolute paths
                    if re.search(r'["\']/[a-zA-Z]', line):
                        issues["hardcoded_paths"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "hardcoded_absolute_path",
                            }
                        )

                    # Working directory assumptions
                    if "os.getcwd()" in line or "os.chdir(" in line:
                        issues["working_directory_assumptions"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "working_directory_assumption",
                            }
                        )

                    # Relative path usage
                    if re.search(r'["\'][^"\']*\.\./', line):
                        issues["relative_paths"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "relative_path_usage",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error analyzing path resolution in %s: %s", py_file, e)

        return issues

    def _analyze_permissions(self) -> dict[str, Any]:
        """Analyze file permissions"""
        logger.info("🔐 Analyzing file permissions...")

        issues = {
            "executable_python_files": [],
            "permission_mismatches": [],
            "recommendations": [],
        }

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                stat_info = py_file.stat()
                mode = stat_info.st_mode

                # Check if executable
                if mode & stat.S_IEXEC:
                    issues["executable_python_files"].append(
                        {
                            "file": str(py_file),
                            "permissions": oct(mode)[-3:],
                            "issue": "executable_python_file",
                        }
                    )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error checking permissions for %s: %s", py_file, e)

        return issues

    def _analyze_working_directory(self) -> dict[str, Any]:
        """Analyze working directory assumptions"""
        logger.info("📂 Analyzing working directory assumptions...")

        issues = {"cwd_usage": [], "chdir_usage": [], "relative_imports": []}

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if "os.getcwd()" in line:
                        issues["cwd_usage"].append(
                            {"file": str(py_file), "line": i, "content": line.strip()}
                        )

                    if "os.chdir(" in line:
                        issues["chdir_usage"].append(
                            {"file": str(py_file), "line": i, "content": line.strip()}
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning(
                    "Error analyzing working directory in %s: %s", py_file, e
                )

        return issues

    def _audit_sys_path(self) -> dict[str, Any]:
        """Audit sys.path manipulation"""
        logger.info("🐍 Auditing sys.path manipulation...")

        issues = {
            "sys_path_append": [],
            "sys_path_insert": [],
            "sys_path_manipulation": [],
            "recommendations": [],
        }

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if "sys.path.append(" in line:
                        issues["sys_path_append"].append(
                            {"file": str(py_file), "line": i, "content": line.strip()}
                        )

                    if "sys.path.insert(" in line:
                        issues["sys_path_insert"].append(
                            {"file": str(py_file), "line": i, "content": line.strip()}
                        )

                    if "sys.path[" in line and "=" in line:
                        issues["sys_path_manipulation"].append(
                            {"file": str(py_file), "line": i, "content": line.strip()}
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error auditing sys.path in %s: %s", py_file, e)

        return issues

    def _assess_ci_compatibility(self) -> dict[str, Any]:
        """Assess overall CI compatibility"""
        logger.info("🚀 Assessing CI compatibility...")

        compatibility = {
            "overall_score": 0,
            "critical_issues": 0,
            "warnings": 0,
            "recommendations": [],
            "ci_ready": False,
        }

        # Count issues
        total_issues = len(self.issues)
        compatibility["critical_issues"] = total_issues
        compatibility["warnings"] = len(self.warnings)

        # Calculate score (100 - issues * 10)
        compatibility["overall_score"] = max(0, 100 - (total_issues * 10))

        # Determine CI readiness
        compatibility["ci_ready"] = total_issues == 0

        # Generate recommendations
        if total_issues > 0:
            compatibility["recommendations"].extend(
                [
                    "Fix case sensitivity issues in directory names",
                    "Replace sys.path manipulation with proper package structure",
                    "Use relative paths instead of hardcoded absolute paths",
                    "Implement centralized import utilities",
                ]
            )

        return compatibility

    def _generate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive summary"""
        summary = {
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings),
            "critical_issues": 0,
            "ci_compatibility_score": 0,
            "recommendations": [],
            "next_steps": [],
        }

        # Count critical issues
        for issue in self.issues:
            if any(
                keyword in issue.lower()
                for keyword in ["case", "hyphenated", "hardcoded"]
            ):
                summary["critical_issues"] += 1

        # Get CI compatibility score
        if "ci_compatibility" in results:
            summary["ci_compatibility_score"] = results["ci_compatibility"][
                "overall_score"
            ]

        # Generate recommendations
        if summary["critical_issues"] > 0:
            summary["recommendations"].append(
                "Address critical filesystem issues before CI deployment"
            )

        if results["sys_path_audit"]["sys_path_append"]:
            summary["recommendations"].append(
                "Replace sys.path manipulation with proper imports"
            )

        # Generate next steps
        if summary["critical_issues"] > 0:
            summary["next_steps"].append(
                "Run fix_filesystem_case_sensitivity.py script"
            )
            summary["next_steps"].append(
                "Update import statements to use correct directory names"
            )
            summary["next_steps"].append("Test changes in CI environment")

        return summary

    def generate_report(self, results: dict[str, Any], output_file: str = None) -> str:
        """Generate comprehensive report"""
        report = []
        report.append("=" * 80)
        report.append("PAKE SYSTEM - CI FILESYSTEM DIAGNOSTICS REPORT")
        report.append("=" * 80)
        report.append("")

        # Filesystem info
        fs_info = results["filesystem_info"]
        report.append("📊 FILESYSTEM INFORMATION")
        report.append("-" * 40)
        report.append(f"Root Path: {fs_info['root_path']}")
        report.append(f"Working Directory: {fs_info['current_working_directory']}")
        report.append(f"Python Version: {fs_info['python_version'].split()[0]}")
        report.append(
            f"Case Sensitivity: {fs_info['case_sensitivity']['filesystem_type']}"
        )
        report.append(
            f"CI Compatible: {'✅ Yes' if fs_info['case_sensitivity']['ci_compatible'] else '❌ No'}"
        )
        report.append("")

        # Summary
        summary = results["summary"]
        report.append("📋 SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Issues: {summary['total_issues']}")
        report.append(f"Critical Issues: {summary['critical_issues']}")
        report.append(
            f"CI Compatibility Score: {summary['ci_compatibility_score']}/100"
        )
        report.append(
            f"CI Ready: {'✅ Yes' if summary['ci_compatibility_score'] >= 80 else '❌ No'}"
        )
        report.append("")

        # Critical issues
        if self.issues:
            report.append("🚨 CRITICAL ISSUES")
            report.append("-" * 40)
            for i, issue in enumerate(self.issues, 1):
                report.append(f"{i}. {issue}")
            report.append("")

        # Recommendations
        if summary["recommendations"]:
            report.append("💡 RECOMMENDATIONS")
            report.append("-" * 40)
            for i, rec in enumerate(summary["recommendations"], 1):
                report.append(f"{i}. {rec}")
            report.append("")

        # Next steps
        if summary["next_steps"]:
            report.append("🎯 NEXT STEPS")
            report.append("-" * 40)
            for i, step in enumerate(summary["next_steps"], 1):
                report.append(f"{i}. {step}")
            report.append("")

        report.append("=" * 80)
        report.append("End of Report")
        report.append("=" * 80)

        report_text = "\n".join(report)

        # Save to file if specified
        if output_file:
            with open(output_file, "w") as f:
                f.write(report_text)
            logger.info("Report saved to: %s", output_file)

        return report_text


def main(self) -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PAKE System CI Filesystem Diagnostics"
    )
    parser.add_argument("--root", default=os.getcwd(), help="Root directory to analyze")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run diagnostics
    diagnostics = CIFilesystemDiagnostics(args.root, args.verbose)
    results = diagnostics.run_comprehensive_analysis()

    # Generate report
    if args.json:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
        else:
            print(json.dumps(results, indent=2, default=str))
    else:
        report = diagnostics.generate_report(results, args.output)
        if not args.output:
            print(report)

    # Exit with appropriate code
    if results["summary"]["critical_issues"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
