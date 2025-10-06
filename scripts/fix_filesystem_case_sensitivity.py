#!/usr/bin/env python3
"""
PAKE System - Filesystem Case Sensitivity Fix Script
===================================================

This script identifies and fixes case sensitivity issues that cause CI failures
on Linux runners while working fine on case-insensitive macOS/Windows systems.

Key Issues Addressed:
1. Directory names with hyphens (secrets-manager, agent-runtime, etc.)
2. Import statements referencing hyphenated directories
3. sys.path manipulation patterns
4. Hardcoded absolute paths
5. Working directory assumptions

Usage:
    python scripts/fix_filesystem_case_sensitivity.py [--dry-run] [--verbose]
"""

import argparse
import ast
import logging
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FilesystemCaseSensitivityFixer:
    """Fix case sensitivity issues in the PAKE system"""

    def __init__(self) -> None:
        self.root_path = Path(root_path or os.getcwd())
        self.dry_run = dry_run
        self.fixes_applied = []
        self.warnings = []

        # Directory mapping for hyphenated directories
        self.directory_mappings = {
            "secrets-manager": "secrets_manager",
            "agent-runtime": "agent_runtime",
            "enterprise-integrations": "enterprise_integrations",
            "social-media-automation": "social_media_automation",
            "knowledge-graph": "knowledge_graph",
            "knowledge-api": "knowledge_api",
            "vault-integration": "vault_integration",
            "voice-agents": "voice_agents",
        }

    def fix_all_issues(self) -> dict[str, Any]:
        """Main fix entry point"""
        logger.info(
            "🔧 Fixing filesystem case sensitivity issues in: %s", self.root_path
        )

        results = {
            "directory_renames": self._fix_directory_names(),
            "import_fixes": self._fix_import_statements(),
            "sys_path_fixes": self._fix_sys_path_usage(),
            "hardcoded_path_fixes": self._fix_hardcoded_paths(),
            "summary": {},
        }

        # Generate summary
        results["summary"] = self._generate_summary(results)

        return results

    def _fix_directory_names(self) -> list[dict[str, Any]]:
        """Rename directories with hyphens to use underscores"""
        logger.info("📁 Fixing directory names with hyphens...")

        fixes = []

        for hyphenated_name, underscore_name in self.directory_mappings.items():
            old_path = self.root_path / "src" / "services" / hyphenated_name
            new_path = self.root_path / "src" / "services" / underscore_name

            if old_path.exists() and not new_path.exists():
                if not self.dry_run:
                    try:
                        shutil.move(str(old_path), str(new_path))
                        logger.info("✅ Renamed: %s -> %s", old_path, new_path)
                        fixes.append(
                            {
                                "type": "directory_rename",
                                "old_path": str(old_path),
                                "new_path": str(new_path),
                                "status": "success",
                            }
                        )
                    except (ValueError, RuntimeError) as e:
                        logger.error("❌ Failed to rename %s: %s", old_path, e)
                        fixes.append(
                            {
                                "type": "directory_rename",
                                "old_path": str(old_path),
                                "new_path": str(new_path),
                                "status": "failed",
                                "error": str(e),
                            }
                        )
                else:
                    logger.info("🔍 DRY RUN: Would rename %s -> %s", old_path, new_path)
                    fixes.append(
                        {
                            "type": "directory_rename",
                            "old_path": str(old_path),
                            "new_path": str(new_path),
                            "status": "dry_run",
                        }
                    )

        return fixes

    def _fix_import_statements(self) -> list[dict[str, Any]]:
        """Fix import statements that reference hyphenated directories"""
        logger.info("📦 Fixing import statements...")

        fixes = []
        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                original_content = content

                # Fix import statements
                for hyphenated, underscore in self.directory_mappings.items():
                    # Fix from imports
                    pattern = rf"from\s+.*{re.escape(hyphenated)}.*import"
                    content = re.sub(
                        pattern,
                        lambda m: m.group(0).replace(hyphenated, underscore),
                        content,
                    )

                    # Fix relative imports
                    pattern = rf"from\s+\.\.?/{re.escape(hyphenated)}"
                    content = re.sub(
                        pattern,
                        lambda m: m.group(0).replace(hyphenated, underscore),
                        content,
                    )

                if content != original_content:
                    if not self.dry_run:
                        with open(py_file, "w", encoding="utf-8") as f:
                            f.write(content)
                        logger.info("✅ Fixed imports in: %s", py_file)
                        fixes.append(
                            {
                                "type": "import_fix",
                                "file": str(py_file),
                                "status": "success",
                            }
                        )
                    else:
                        logger.info("🔍 DRY RUN: Would fix imports in %s", py_file)
                        fixes.append(
                            {
                                "type": "import_fix",
                                "file": str(py_file),
                                "status": "dry_run",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error fixing imports in %s: %s", py_file, e)

        return fixes

    def _fix_sys_path_usage(self) -> list[dict[str, Any]]:
        """Replace sys.path manipulation with proper package structure"""
        logger.info("🐍 Fixing sys.path usage...")

        fixes = []
        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                lines = content.split("\n")
                new_lines = []

                for line in lines:
                    # Replace sys.path.append with proper imports
                    if "sys.path.append(" in line and "src" in line:
                        # Comment out the line and add a note
                        new_line = f"# {line}  # Replaced with proper package structure"
                        new_lines.append(new_line)
                        logger.info("✅ Commented out sys.path.append in: %s", py_file)
                    elif "sys.path.insert(" in line and "src" in line:
                        # Comment out the line and add a note
                        new_line = f"# {line}  # Replaced with proper package structure"
                        new_lines.append(new_line)
                        logger.info("✅ Commented out sys.path.insert in: %s", py_file)
                    else:
                        new_lines.append(line)

                new_content = "\n".join(new_lines)

                if new_content != original_content:
                    if not self.dry_run:
                        with open(py_file, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        fixes.append(
                            {
                                "type": "sys_path_fix",
                                "file": str(py_file),
                                "status": "success",
                            }
                        )
                    else:
                        logger.info(
                            "🔍 DRY RUN: Would fix sys.path usage in %s", py_file
                        )
                        fixes.append(
                            {
                                "type": "sys_path_fix",
                                "file": str(py_file),
                                "status": "dry_run",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error fixing sys.path usage in %s: %s", py_file, e)

        return fixes

    def _fix_hardcoded_paths(self) -> list[dict[str, Any]]:
        """Fix hardcoded absolute paths"""
        logger.info("🛤️ Fixing hardcoded paths...")

        fixes = []
        python_files = list(self.root_path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                original_content = content

                # Fix common hardcoded paths
                replacements = [
                    (
                        r'"/d/Projects/PAKE_SYSTEM/',
                        "str(Path(__file__).parent.parent.parent / ",
                    ),
                    (
                        r"'/d/Projects/PAKE_SYSTEM/",
                        "str(Path(__file__).parent.parent.parent / ",
                    ),
                    (
                        r'"/root/projects/PAKE_SYSTEM_claude_optimized/',
                        "str(Path(__file__).parent.parent.parent / ",
                    ),
                    (
                        r"'/root/projects/PAKE_SYSTEM_claude_optimized/",
                        "str(Path(__file__).parent.parent.parent / ",
                    ),
                ]

                for old_pattern, new_pattern in replacements:
                    content = re.sub(old_pattern, new_pattern, content)

                if content != original_content:
                    if not self.dry_run:
                        with open(py_file, "w", encoding="utf-8") as f:
                            f.write(content)
                        logger.info("✅ Fixed hardcoded paths in: %s", py_file)
                        fixes.append(
                            {
                                "type": "hardcoded_path_fix",
                                "file": str(py_file),
                                "status": "success",
                            }
                        )
                    else:
                        logger.info(
                            "🔍 DRY RUN: Would fix hardcoded paths in %s", py_file
                        )
                        fixes.append(
                            {
                                "type": "hardcoded_path_fix",
                                "file": str(py_file),
                                "status": "dry_run",
                            }
                        )

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error fixing hardcoded paths in %s: %s", py_file, e)

        return fixes

    def _generate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary of fixes applied"""
        summary = {
            "total_fixes": 0,
            "successful_fixes": 0,
            "failed_fixes": 0,
            "dry_run_fixes": 0,
            "fixes_by_type": {},
        }

        for _category, fixes in results.items():
            if isinstance(fixes, list):
                for fix in fixes:
                    summary["total_fixes"] += 1
                    fix_type = fix.get("type", "unknown")

                    if fix_type not in summary["fixes_by_type"]:
                        summary["fixes_by_type"][fix_type] = 0
                    summary["fixes_by_type"][fix_type] += 1

                    status = fix.get("status", "unknown")
                    if status == "success":
                        summary["successful_fixes"] += 1
                    elif status == "failed":
                        summary["failed_fixes"] += 1
                    elif status == "dry_run":
                        summary["dry_run_fixes"] += 1

        return summary

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a comprehensive report of fixes applied"""
        report = []
        report.append("=" * 80)
        report.append("PAKE SYSTEM - FILESYSTEM CASE SENSITIVITY FIX REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        summary = results["summary"]
        report.append("📊 SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Fixes Applied: {summary['total_fixes']}")
        report.append(f"Successful Fixes: {summary['successful_fixes']}")
        report.append(f"Failed Fixes: {summary['failed_fixes']}")
        report.append(f"Dry Run Fixes: {summary['dry_run_fixes']}")
        report.append("")

        # Fixes by type
        if summary["fixes_by_type"]:
            report.append("🔧 FIXES BY TYPE")
            report.append("-" * 40)
            for fix_type, count in summary["fixes_by_type"].items():
                report.append(f"{fix_type}: {count}")
            report.append("")

        # Detailed results
        for category, fixes in results.items():
            if isinstance(fixes, list) and fixes:
                report.append(f"📋 {category.upper().replace('_', ' ')}")
                report.append("-" * 40)
                for fix in fixes:
                    report.append(f"Type: {fix.get('type', 'unknown')}")
                    report.append(f"Status: {fix.get('status', 'unknown')}")
                    if "file" in fix:
                        report.append(f"File: {fix['file']}")
                    if "old_path" in fix:
                        report.append(f"Old: {fix['old_path']}")
                    if "new_path" in fix:
                        report.append(f"New: {fix['new_path']}")
                    if "error" in fix:
                        report.append(f"Error: {fix['error']}")
                    report.append("")

        report.append("=" * 80)
        report.append("End of Report")
        report.append("=" * 80)

        return "\n".join(report)


def main(self) -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PAKE System Filesystem Case Sensitivity Fixer"
    )
    parser.add_argument("--root", default=os.getcwd(), help="Root directory to fix")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run fixes
    fixer = FilesystemCaseSensitivityFixer(args.root, args.dry_run)
    results = fixer.fix_all_issues()

    # Generate report
    report = fixer.generate_report(results)

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        logger.info("Report saved to: %s", args.output)
    else:
        print(report)

    # Exit with appropriate code
    if results["summary"]["failed_fixes"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()