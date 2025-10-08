#!/usr/bin/env python3
"""
PAKE System - Filesystem Diagnostics Script
===========================================

This script performs comprehensive filesystem analysis to identify potential
case sensitivity issues, path resolution problems, and permission discrepancies
that could cause CI failures.

Key Areas Investigated:
1. Case sensitivity in import statements vs actual file/directory names
2. Working directory assumptions and relative path usage
3. File permission patterns
4. Path resolution inconsistencies
5. sys.path manipulation patterns

Usage:
    python scripts/filesystem_diagnostics.py [--verbose] [--fix]
"""

import argparse
import ast
from collections import defaultdict
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FilesystemDiagnostics:
    """Comprehensive filesystem analysis for CI compatibility"""

def __init__(self, root_path: Any = None) -> None:
        self.root_path = Path(root_path or os.getcwd())
        self.issues = []
        self.warnings = []
        self.fixes_applied = []

        # Track case-sensitive patterns
        self.import_patterns = defaultdict(list)
        self.file_structure = {}
        self.case_mismatches = []

    def analyze_filesystem(self) -> dict[str, Any]:
        """Main analysis entry point"""
        logger.info("🔍 Analyzing filesystem at: %s", self.root_path)

        results = {
            "case_sensitivity_issues": self._analyze_case_sensitivity(),
            "path_resolution_issues": self._analyze_path_resolution(),
            "permission_issues": self._analyze_permissions(),
            "working_directory_issues": self._analyze_working_directory(),
            "sys_path_issues": self._analyze_sys_path_usage(),
            "summary": {},
        }

        # Generate summary
        results["summary"] = self._generate_summary(results)

        return results

    def _analyze_case_sensitivity(self) -> dict[str, Any]:
        """Analyze case sensitivity issues in imports and file paths"""
        logger.info("📁 Analyzing case sensitivity issues...")

        issues = {
            "import_case_mismatches": [],
            "directory_case_mismatches": [],
            "file_case_mismatches": [],
            "recommendations": [],
        }

        # Get all Python files
        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Parse AST to find imports
                tree = ast.parse(content)
                imports = self._extract_imports(tree)

                for import_stmt in imports:
                    # Check if import path matches actual filesystem
                    mismatch = self._check_import_case_mismatch(py_file, import_stmt)
                    if mismatch:
                        issues["import_case_mismatches"].append(mismatch)

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error analyzing %s: %s", py_file, e)

        # Check directory structure for case issues
        issues["directory_case_mismatches"] = self._check_directory_case_issues()

        return issues

    def _extract_imports(self, tree: ast.AST) -> list[dict[str, Any]]:
        """Extract all import statements from AST"""
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
    ) -> dict[str, Any]:
        """Check if import statement has case sensitivity issues"""
        module_path = import_stmt["module"]

        # Skip external packages
        if not module_path.startswith("src.") and not module_path.startswith("."):
            return None

        # Convert import path to filesystem path
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

        # Check if path exists with exact case
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

    def _check_directory_case_issues(self) -> list[dict[str, Any]]:
        """Check for directory case sensitivity issues"""
        issues = []

        # Check for common problematic patterns
        problematic_dirs = [
            "src/services/secrets-manager",  # hyphen vs underscore
            "src/services/agent-runtime",  # hyphen vs underscore
            "src/services/enterprise-integrations",  # hyphen vs underscore
            "src/services/social-media-automation",  # hyphen vs underscore
        ]

        for dir_path in problematic_dirs:
            full_path = self.root_path / dir_path
            if full_path.exists():
                # Check if there are any imports that might conflict
                issues.append(
                    {
                        "directory": str(full_path),
                        "issue": "hyphen_in_directory_name",
                        "recommendation": "Consider using underscores for Python compatibility",
                    }
                )

        return issues

    def _analyze_path_resolution(self) -> dict[str, Any]:
        """Analyze path resolution patterns"""
        logger.info("🛤️ Analyzing path resolution issues...")

        issues = {
            "relative_path_usage": [],
            "hardcoded_paths": [],
            "working_directory_assumptions": [],
            "recommendations": [],
        }

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Look for problematic patterns
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    # Hardcoded paths - fixed regex
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

                    # Relative path usage - fixed regex
                    if re.search(r'["\'][^"\']*\.\./', line):
                        issues["relative_path_usage"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "relative_path_usage",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error analyzing %s: %s", py_file, e)

        return issues

    def _analyze_permissions(self) -> dict[str, Any]:
        """Analyze file permission patterns"""
        logger.info("🔐 Analyzing permission issues...")

        issues = {
            "executable_files": [],
            "permission_mismatches": [],
            "recommendations": [],
        }

        # Check Python files for executable permissions
        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                stat = py_file.stat()
                if stat.st_mode & 0o111:  # Executable bit set
                    issues["executable_files"].append(
                        {
                            "file": str(py_file),
                            "permissions": oct(stat.st_mode)[-3:],
                            "issue": "executable_python_file",
                        }
                    )
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error checking permissions for %s: %s", py_file, e)

        return issues

    def _analyze_working_directory(self) -> dict[str, Any]:
        """Analyze working directory assumptions"""
        logger.info("📂 Analyzing working directory issues...")

        issues = {
            "cwd_assumptions": [],
            "chdir_usage": [],
            "relative_imports": [],
            "recommendations": [],
        }

        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    # os.getcwd() usage
                    if "os.getcwd()" in line:
                        issues["cwd_assumptions"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "cwd_assumption",
                            }
                        )

                    # os.chdir() usage
                    if "os.chdir(" in line:
                        issues["chdir_usage"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "chdir_usage",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error analyzing %s: %s", py_file, e)

        return issues

    def _analyze_sys_path_usage(self) -> dict[str, Any]:
        """Analyze sys.path manipulation patterns"""
        logger.info("🐍 Analyzing sys.path usage...")

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
                    # sys.path.append usage
                    if "sys.path.append(" in line:
                        issues["sys_path_append"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "sys_path_append",
                            }
                        )

                    # sys.path.insert usage
                    if "sys.path.insert(" in line:
                        issues["sys_path_insert"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "sys_path_insert",
                            }
                        )

                    # Other sys.path manipulation
                    if "sys.path[" in line and "=" in line:
                        issues["sys_path_manipulation"].append(
                            {
                                "file": str(py_file),
                                "line": i,
                                "content": line.strip(),
                                "issue": "sys_path_manipulation",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error analyzing %s: %s", py_file, e)

        return issues

    def _generate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary of all issues found"""
        summary = {
            "total_issues": 0,
            "critical_issues": 0,
            "warnings": 0,
            "recommendations": [],
            "ci_risk_level": "LOW",
        }

        # Count issues
        for _category, data in results.items():
            if isinstance(data, dict):
                for _issue_type, issues in data.items():
                    if isinstance(issues, list):
                        summary["total_issues"] += len(issues)

                        # Categorize by severity
                        for issue in issues:
                            if issue.get("issue") in [
                                "case_mismatch",
                                "hardcoded_absolute_path",
                            ]:
                                summary["critical_issues"] += 1
                            else:
                                summary["warnings"] += 1

        # Determine CI risk level
        if summary["critical_issues"] > 10:
            summary["ci_risk_level"] = "HIGH"
        elif summary["critical_issues"] > 5:
            summary["ci_risk_level"] = "MEDIUM"

        # Generate recommendations
        if summary["critical_issues"] > 0:
            summary["recommendations"].append(
                "Fix case sensitivity issues in import statements"
            )
        if results["path_resolution_issues"]["hardcoded_paths"]:
            summary["recommendations"].append(
                "Replace hardcoded paths with relative or configurable paths"
            )
        if results["sys_path_issues"]["sys_path_append"]:
            summary["recommendations"].append(
                "Replace sys.path manipulation with proper package structure"
            )

        return summary

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a comprehensive report"""
        report = []
        report.append("=" * 80)
        report.append("PAKE SYSTEM - FILESYSTEM DIAGNOSTICS REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        summary = results["summary"]
        report.append("📊 SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Issues Found: {summary['total_issues']}")
        report.append(f"Critical Issues: {summary['critical_issues']}")
        report.append(f"Warnings: {summary['warnings']}")
        report.append(f"CI Risk Level: {summary['ci_risk_level']}")
        report.append("")

        # Case sensitivity issues
        case_issues = results["case_sensitivity_issues"]
        if case_issues["import_case_mismatches"]:
            report.append("🚨 CASE SENSITIVITY ISSUES")
            report.append("-" * 40)
            for issue in case_issues["import_case_mismatches"]:
                report.append(f"File: {issue['file']}")
                report.append(f"Line: {issue['line']}")
                report.append(f"Import: {issue['import']}")
                report.append(f"Expected: {issue['expected_path']}")
                report.append(f"Actual: {issue['actual_path']}")
                report.append("")

        # Path resolution issues
        path_issues = results["path_resolution_issues"]
        if path_issues["hardcoded_paths"]:
            report.append("🛤️ PATH RESOLUTION ISSUES")
            report.append("-" * 40)
            for issue in path_issues["hardcoded_paths"]:
                report.append(f"File: {issue['file']}")
                report.append(f"Line: {issue['line']}")
                report.append(f"Content: {issue['content']}")
                report.append("")

        # Sys.path issues
        sys_path_issues = results["sys_path_issues"]
        if sys_path_issues["sys_path_append"]:
            report.append("🐍 SYS.PATH MANIPULATION ISSUES")
            report.append("-" * 40)
            for issue in sys_path_issues["sys_path_append"]:
                report.append(f"File: {issue['file']}")
                report.append(f"Line: {issue['line']}")
                report.append(f"Content: {issue['content']}")
                report.append("")

        # Recommendations
        if summary["recommendations"]:
            report.append("💡 RECOMMENDATIONS")
            report.append("-" * 40)
            for i, rec in enumerate(summary["recommendations"], 1):
                report.append(f"{i}. {rec}")
            report.append("")

        report.append("=" * 80)
        report.append("End of Report")
        report.append("=" * 80)

        return "\n".join(report)


def main(self) -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Filesystem Diagnostics")
    parser.add_argument("--root", default=os.getcwd(), help="Root directory to analyze")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run diagnostics
    diagnostics = FilesystemDiagnostics(args.root)
    results = diagnostics.analyze_filesystem()

    # Generate report
    report = diagnostics.generate_report(results)

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        logger.info("Report saved to: %s", args.output)
    else:
        print(report)

    # Exit with appropriate code
    if results["summary"]["critical_issues"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
