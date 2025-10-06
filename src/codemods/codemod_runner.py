#!/usr/bin/env python3
"""Automated Codemod Execution Framework.

This module implements the automated codemod execution framework described in the
engineering plan. It provides the infrastructure for running LibCST-based transformations
at scale across the entire PAKE system codebase.

The framework implements the engineering plan's principles:
- Automation First: Programmatic refactoring for thousands of errors
- Preservation of Intent: Lossless transformations preserving formatting and comments
- Prevention over Cure: Building automated defenses against future bugs

This supports Phase 1 of the engineering plan for immediate stabilization through
automated remediation of production incidents.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import libcst as cst
from libcst.codemod import CodemodContext

from .engineering_plan_codemods import (
    ComprehensiveDTZTransformer,
    ContextPassingTransformer,
    UTCNowTransformer,
)

logger = logging.getLogger(__name__)


@dataclass
class CodemodResult:
    """Result of a codemod transformation."""

    file_path: Path
    success: bool
    modifications_made: int
    error_message: str | None = None
    original_size: int = 0
    transformed_size: int = 0
    execution_time: float = 0.0


@dataclass
class CodemodExecutionPlan:
    """Execution plan for running codemods across the codebase."""

    transformers: list[Any]  # List of transformer classes
    target_files: list[Path]
    backup_enabled: bool = True
    dry_run: bool = False
    parallel_execution: bool = True
    max_workers: int = 4


class CodemodRunner:
    """Automated codemod execution framework.

    This implements the engineering plan's automation-first approach for
    programmatic refactoring at scale. It provides:
    - Parallel execution for speed
    - Backup creation for safety
    - Dry-run mode for validation
    - Comprehensive reporting
    - Error handling and recovery
    """

    def __init__(self, backup_dir: Path | None = None, log_level: str = "INFO"):
        """Initialize the codemod runner.

        Args:
            backup_dir: Directory to store backups (defaults to ./backups)
            log_level: Logging level for the runner
        """
        self.backup_dir = backup_dir or Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of the file before transformation.

        Args:
            file_path: Path to the file to backup

        Returns:
            Path to the backup file
        """
        timestamp = int(time.time())
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name

        # Copy file content to backup
        backup_path.write_text(file_path.read_text())
        self.logger.debug(f"Created backup: {backup_path}")

        return backup_path

    def transform_file(
        self, file_path: Path, transformers: list[Any], dry_run: bool = False
    ) -> CodemodResult:
        """Transform a single file using the specified transformers.

        Args:
            file_path: Path to the file to transform
            transformers: List of transformer classes to apply
            dry_run: If True, don't write changes to disk

        Returns:
            CodemodResult with transformation details
        """
        start_time = time.time()
        original_size = file_path.stat().st_size if file_path.exists() else 0

        try:
            # Read the file content
            if not file_path.exists():
                return CodemodResult(
                    file_path=file_path,
                    success=False,
                    modifications_made=0,
                    error_message="File does not exist",
                    original_size=original_size,
                )

            content = file_path.read_text()

            # Parse the code as a module
            tree = cst.parse_module(content)

            # Apply transformers sequentially
            context = CodemodContext()
            total_modifications = 0

            for transformer_class in transformers:
                transformer = transformer_class(context)
                tree = transformer.transform_module(tree)
                total_modifications += transformer.get_modifications_count()

            # Generate transformed code
            transformed_code = tree.code

            # Write changes if not dry run
            if not dry_run and total_modifications > 0:
                file_path.write_text(transformed_code)

            transformed_size = len(transformed_code.encode("utf-8"))
            execution_time = time.time() - start_time

            return CodemodResult(
                file_path=file_path,
                success=True,
                modifications_made=total_modifications,
                original_size=original_size,
                transformed_size=transformed_size,
                execution_time=execution_time,
            )

        except (FileNotFoundError, PermissionError, OSError) as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error transforming {file_path}: {e}")

            return CodemodResult(
                file_path=file_path,
                success=False,
                modifications_made=0,
                error_message=str(e),
                original_size=original_size,
                execution_time=execution_time,
            )

    def execute_plan(self, plan: CodemodExecutionPlan) -> list[CodemodResult]:
        """Execute a codemod plan across multiple files.

        Args:
            plan: The execution plan to run

        Returns:
            List of CodemodResult objects for each file
        """
        self.logger.info(
            f"Starting codemod execution plan with {len(plan.target_files)} files"
        )
        self.logger.info(f"Transformers: {[t.DESCRIPTION for t in plan.transformers]}")
        self.logger.info(f"Dry run: {plan.dry_run}")
        self.logger.info(f"Parallel execution: {plan.parallel_execution}")

        results = []

        if plan.parallel_execution and len(plan.target_files) > 1:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=plan.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        self.transform_file, file_path, plan.transformers, plan.dry_run
                    ): file_path
                    for file_path in plan.target_files
                }

                # Collect results as they complete
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)

                        if result.success:
                            self.logger.info(
                                f"✓ {file_path.name}: {result.modifications_made} modifications"
                            )
                        else:
                            self.logger.error(
                                f"✗ {file_path.name}: {result.error_message}"
                            )

                    except (FileNotFoundError, PermissionError, OSError) as e:
                        self.logger.error(f"✗ {file_path.name}: Unexpected error: {e}")
                        results.append(
                            CodemodResult(
                                file_path=file_path,
                                success=False,
                                modifications_made=0,
                                error_message=f"Unexpected error: {e}",
                            )
                        )
        else:
            # Sequential execution
            for file_path in plan.target_files:
                result = self.transform_file(file_path, plan.transformers, plan.dry_run)
                results.append(result)

                if result.success:
                    self.logger.info(
                        f"✓ {file_path.name}: {result.modifications_made} modifications"
                    )
                else:
                    self.logger.error(f"✗ {file_path.name}: {result.error_message}")

        return results

    def generate_report(self, results: list[CodemodResult]) -> dict[str, Any]:
        """Generate a comprehensive report of codemod execution results.

        Args:
            results: List of CodemodResult objects

        Returns:
            Dictionary containing report data
        """
        total_files = len(results)
        successful_files = sum(1 for r in results if r.success)
        failed_files = total_files - successful_files
        total_modifications = sum(r.modifications_made for r in results)
        total_execution_time = sum(r.execution_time for r in results)

        # Calculate size changes
        total_original_size = sum(r.original_size for r in results)
        total_transformed_size = sum(r.transformed_size for r in results)
        size_change = total_transformed_size - total_original_size

        # Group by error types
        error_summary = {}
        for result in results:
            if not result.success and result.error_message:
                error_type = type(result.error_message).__name__
                error_summary[error_type] = error_summary.get(error_type, 0) + 1

        return {
            "summary": {
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "success_rate": (successful_files / total_files * 100)
                if total_files > 0
                else 0,
                "total_modifications": total_modifications,
                "total_execution_time": total_execution_time,
                "average_time_per_file": total_execution_time / total_files
                if total_files > 0
                else 0,
            },
            "size_analysis": {
                "total_original_size": total_original_size,
                "total_transformed_size": total_transformed_size,
                "size_change": size_change,
                "size_change_percent": (size_change / total_original_size * 100)
                if total_original_size > 0
                else 0,
            },
            "error_summary": error_summary,
            "detailed_results": [
                {
                    "file_path": str(r.file_path),
                    "success": r.success,
                    "modifications_made": r.modifications_made,
                    "error_message": r.error_message,
                    "execution_time": r.execution_time,
                }
                for r in results
            ],
        }

    def print_report(self, report: dict[str, Any]) -> None:
        """Print a formatted report to the console."""
        print("\n" + "=" * 80)
        print("CODEMOD EXECUTION REPORT")
        print("=" * 80)

        summary = report["summary"]
        print("\nSUMMARY:")
        print(f"  Total files processed: {summary['total_files']}")
        print(f"  Successful: {summary['successful_files']}")
        print(f"  Failed: {summary['failed_files']}")
        print(f"  Success rate: {summary['success_rate']:.1f}%")
        print(f"  Total modifications: {summary['total_modifications']}")
        print(f"  Total execution time: {summary['total_execution_time']:.2f}s")
        print(f"  Average time per file: {summary['average_time_per_file']:.3f}s")

        size_analysis = report["size_analysis"]
        print("\nSIZE ANALYSIS:")
        print(f"  Original size: {size_analysis['total_original_size']:,} bytes")
        print(f"  Transformed size: {size_analysis['total_transformed_size']:,} bytes")
        print(
            f"  Size change: {size_analysis['size_change']:+,} bytes ({size_analysis['size_change_percent']:+.2f}%)"
        )

        if report["error_summary"]:
            print("\nERROR SUMMARY:")
            for error_type, count in report["error_summary"].items():
                print(f"  {error_type}: {count}")

        print("\n" + "=" * 80)


def discover_python_files(
    root_dir: Path, exclude_dirs: set[str] | None = None
) -> list[Path]:
    """Discover Python files in the given directory tree.

    Args:
        root_dir: Root directory to search
        exclude_dirs: Set of directory names to exclude

    Returns:
        List of Path objects for Python files
    """
    if exclude_dirs is None:
        exclude_dirs = {
            "__pycache__",
            ".git",
            ".pytest_cache",
            "venv",
            ".venv",
            "mcp-env",
            "test_env",
            "node_modules",
            "dist",
            "build",
            "security_backups",
            "backups",
            ".ruff_cache",
        }

    python_files = []

    for file_path in root_dir.rglob("*.py"):
        # Skip files in excluded directories
        if any(part in exclude_dirs for part in file_path.parts):
            continue
        python_files.append(file_path)

    return sorted(python_files)


def create_dtz_remediation_plan(
    root_dir: Path, dry_run: bool = False
) -> CodemodExecutionPlan:
    """Create an execution plan for DTZ error remediation.

    Args:
        root_dir: Root directory of the codebase
        dry_run: If True, don't write changes to disk

    Returns:
        CodemodExecutionPlan for DTZ remediation
    """
    python_files = discover_python_files(root_dir)

    return CodemodExecutionPlan(
        transformers=[ComprehensiveDTZTransformer],
        target_files=python_files,
        backup_enabled=True,
        dry_run=dry_run,
        parallel_execution=True,
        max_workers=4,
    )


def create_f821_remediation_plan(
    root_dir: Path, dry_run: bool = False
) -> CodemodExecutionPlan:
    """Create an execution plan for F821 error remediation.

    Args:
        root_dir: Root directory of the codebase
        dry_run: If True, don't write changes to disk

    Returns:
        CodemodExecutionPlan for F821 remediation
    """
    python_files = discover_python_files(root_dir)

    return CodemodExecutionPlan(
        transformers=[ContextPassingTransformer],
        target_files=python_files,
        backup_enabled=True,
        dry_run=dry_run,
        parallel_execution=True,
        max_workers=4,
    )


def create_comprehensive_remediation_plan(
    root_dir: Path, dry_run: bool = False
) -> CodemodExecutionPlan:
    """Create an execution plan for comprehensive remediation of both DTZ and F821 errors.

    Args:
        root_dir: Root directory of the codebase
        dry_run: If True, don't write changes to disk

    Returns:
        CodemodExecutionPlan for comprehensive remediation
    """
    python_files = discover_python_files(root_dir)

    return CodemodExecutionPlan(
        transformers=[ComprehensiveDTZTransformer, ContextPassingTransformer],
        target_files=python_files,
        backup_enabled=True,
        dry_run=dry_run,
        parallel_execution=True,
        max_workers=4,
    )


def main():
    """Main entry point for the codemod runner."""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE System Codemod Runner")
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path("."),
        help="Root directory of the codebase",
    )
    parser.add_argument(
        "--mode",
        choices=["dtz", "f821", "comprehensive"],
        default="comprehensive",
        help="Remediation mode",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't write changes to disk"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--max-workers", type=int, default=4, help="Maximum number of parallel workers"
    )

    args = parser.parse_args()

    # Create runner
    runner = CodemodRunner(log_level=args.log_level)

    # Create execution plan
    if args.mode == "dtz":
        plan = create_dtz_remediation_plan(args.root_dir, args.dry_run)
    elif args.mode == "f821":
        plan = create_f821_remediation_plan(args.root_dir, args.dry_run)
    else:
        plan = create_comprehensive_remediation_plan(args.root_dir, args.dry_run)

    plan.max_workers = args.max_workers

    # Execute plan
    results = runner.execute_plan(plan)

    # Generate and print report
    report = runner.generate_report(results)
    runner.print_report(report)

    # Exit with appropriate code
    failed_files = report["summary"]["failed_files"]
    sys.exit(1 if failed_files > 0 else 0)


if __name__ == "__main__":
    main()