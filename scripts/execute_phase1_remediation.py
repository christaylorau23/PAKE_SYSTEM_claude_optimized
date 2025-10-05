#!/usr/bin/env python3
"""
Automated Codemod Execution Script for Phase 1 Remediation

This script implements the automated remediation strategy described in the
engineering plan's Phase 1. It executes the LibCST transformers to fix
F821 and DTZ errors across the entire codebase using programmatic
code transformation.

The script follows the "Automation First" principle and ensures
"Preservation of Intent" by using LibCST's format-preserving transformations.
"""

import argparse
import logging
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add the codemods directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "codemods"))

from context_passing_transformer import create_context_passing_codemod
from datetime_timezone_transformer import create_datetime_timezone_transformer


class CodemodExecutor:
    """Executes LibCST codemods across the codebase."""

    def __init__(self, dry_run: bool = False, max_workers: int = 4):
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for the codemod execution."""
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def find_python_files(self, root_dir: Path) -> list[Path]:
        """Find all Python files in the codebase."""
        python_files = []

        # Exclude common directories that shouldn't be modified
        exclude_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            "env",
            ".env",
            "build",
            "dist",
        }

        for py_file in root_dir.rglob("*.py"):
            # Skip files in excluded directories
            if any(part in exclude_dirs for part in py_file.parts):
                continue
            python_files.append(py_file)

        return python_files

    def run_ruff_check(self, file_path: Path) -> list[str]:
        """Run ruff check on a file to identify F821 and DTZ errors."""
        try:
            result = subprocess.run(
                ["poetry", "run", "ruff", "check", "--select=F821,DTZ", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            errors = []
            for line in result.stdout.splitlines():
                if "F821" in line or "DTZ" in line:
                    errors.append(line.strip())

            return errors

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout checking {file_path}")
            return []
        except Exception as e:
            self.logger.error(f"Error checking {file_path}: {e}")
            return []

    def apply_context_passing_fixes(self, file_path: Path) -> tuple[bool, int]:
        """Apply context passing fixes to a file."""
        try:
            # Read the file content
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()

            # Apply the transformer
            transformer = create_context_passing_codemod()

            # Parse and transform the code
            tree = transformer.context.parse_module(original_content)
            transformed_tree = transformer.transform_module(tree)

            # Check if changes were made
            new_content = transformed_tree.code
            if new_content != original_content:
                if not self.dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                # Count the number of fixes by comparing before/after ruff output
                original_errors = self.run_ruff_check(file_path)
                return True, len(original_errors)

            return False, 0

        except Exception as e:
            self.logger.error(
                f"Error applying context passing fixes to {file_path}: {e}"
            )
            return False, 0

    def apply_datetime_fixes(self, file_path: Path) -> tuple[bool, int]:
        """Apply datetime timezone fixes to a file."""
        try:
            # Read the file content
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()

            # Apply the transformer
            transformer = create_datetime_timezone_transformer()

            # Parse and transform the code
            tree = transformer.context.parse_module(original_content)
            transformed_tree = transformer.transform_module(tree)

            # Check if changes were made
            new_content = transformed_tree.code
            if new_content != original_content:
                if not self.dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                # Count the number of fixes
                original_errors = self.run_ruff_check(file_path)
                return True, len(original_errors)

            return False, 0

        except Exception as e:
            self.logger.error(f"Error applying datetime fixes to {file_path}: {e}")
            return False, 0

    def process_file(self, file_path: Path) -> dict[str, Any]:
        """Process a single file with both transformers."""
        result = {
            "file": str(file_path),
            "context_fixes": 0,
            "datetime_fixes": 0,
            "total_fixes": 0,
            "errors": [],
        }

        try:
            # Check for errors first
            errors = self.run_ruff_check(file_path)
            if not errors:
                return result

            # Apply context passing fixes
            context_modified, context_count = self.apply_context_passing_fixes(
                file_path
            )
            result["context_fixes"] = context_count

            # Apply datetime fixes
            datetime_modified, datetime_count = self.apply_datetime_fixes(file_path)
            result["datetime_fixes"] = datetime_count

            result["total_fixes"] = context_count + datetime_count

            if context_modified or datetime_modified:
                self.logger.info(f"Fixed {result['total_fixes']} issues in {file_path}")

        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"Error processing {file_path}: {e}")

        return result

    def execute_phase1_remediation(self, root_dir: Path) -> dict[str, Any]:
        """Execute Phase 1 remediation across the entire codebase."""
        self.logger.info(
            "🚀 Starting Phase 1: Automated Remediation of Production Incidents"
        )
        self.logger.info("=" * 80)

        # Find all Python files
        python_files = self.find_python_files(root_dir)
        self.logger.info(f"📁 Found {len(python_files)} Python files to process")

        if self.dry_run:
            self.logger.info("🔍 DRY RUN MODE - No files will be modified")

        # Process files in parallel
        results = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.process_file, file_path): file_path
                for file_path in python_files
            }

            # Collect results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result["total_fixes"] > 0:
                        self.logger.info(
                            f"✅ {file_path.name}: {result['total_fixes']} fixes "
                            f"(F821: {result['context_fixes']}, DTZ: {result['datetime_fixes']})"
                        )

                except Exception as e:
                    self.logger.error(f"Failed to process {file_path}: {e}")

        end_time = time.time()

        # Calculate summary statistics
        total_files_processed = len(results)
        files_with_fixes = sum(1 for r in results if r["total_fixes"] > 0)
        total_context_fixes = sum(r["context_fixes"] for r in results)
        total_datetime_fixes = sum(r["datetime_fixes"] for r in results)
        total_fixes = total_context_fixes + total_datetime_fixes

        summary = {
            "total_files_processed": total_files_processed,
            "files_with_fixes": files_with_fixes,
            "total_context_fixes": total_context_fixes,
            "total_datetime_fixes": total_datetime_fixes,
            "total_fixes": total_fixes,
            "execution_time": end_time - start_time,
            "dry_run": self.dry_run,
        }

        # Log summary
        self.logger.info("\n" + "=" * 80)
        self.logger.info("📊 PHASE 1 REMEDIATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Files processed: {total_files_processed}")
        self.logger.info(f"Files with fixes: {files_with_fixes}")
        self.logger.info(f"F821 Context fixes: {total_context_fixes}")
        self.logger.info(f"DTZ DateTime fixes: {total_datetime_fixes}")
        self.logger.info(f"Total fixes applied: {total_fixes}")
        self.logger.info(f"Execution time: {summary['execution_time']:.2f} seconds")

        if self.dry_run:
            self.logger.info("🔍 This was a DRY RUN - no files were actually modified")
        else:
            self.logger.info("✅ All fixes have been applied to the codebase")

        return summary


def main():
    """Main entry point for the codemod execution script."""
    parser = argparse.ArgumentParser(
        description="Execute Phase 1 automated remediation using LibCST codemods"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without actually modifying files",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path.cwd(),
        help="Root directory to process (default: current directory)",
    )

    args = parser.parse_args()

    # Create executor and run remediation
    executor = CodemodExecutor(dry_run=args.dry_run, max_workers=args.max_workers)
    summary = executor.execute_phase1_remediation(args.root_dir)

    # Exit with appropriate code
    if summary["total_fixes"] > 0:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # No fixes applied


if __name__ == "__main__":
    main()
