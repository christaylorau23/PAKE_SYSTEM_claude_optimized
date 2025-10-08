#!/usr/bin/env python3
"""F821 Error Analysis Script for The Phoenix Protocol Phase 5.2
Analyzes ruff_errors.log to categorize and prioritize F821 undefined-name errors.
"""

from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Dict, List, Tuple


def parse_ruff_errors(log_file: str) -> dict[str, list[tuple[str, int, str]]]:
    """Parse ruff errors log and categorize by error code."""
    errors_by_code = defaultdict(list)

    with open(log_file) as f:
        content = f.read()

    # Pattern to match ruff error format: file:line:col: code message
    pattern = r"([^:]+):(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)"

    for match in re.finditer(pattern, content):
        file_path = match.group(1)
        line_num = int(match.group(2))
        col_num = int(match.group(3))
        error_code = match.group(4)
        message = match.group(5)

        errors_by_code[error_code].append((file_path, line_num, message))

    return dict(errors_by_code)


def analyze_f821_errors(
    f821_errors: list[tuple[str, int, str]],
) -> dict[str, list[tuple[str, int, str]]]:
    """Categorize F821 errors by type."""
    categories = {
        "missing_typing_imports": [],
        "missing_standard_library": [],
        "missing_third_party": [],
        "circular_dependencies": [],
        "forward_references": [],
        "undefined_variables": [],
        "other": [],
    }

    # Common typing imports that are often missing
    typing_imports = {
        "List",
        "Dict",
        "Tuple",
        "Set",
        "Optional",
        "Union",
        "Any",
        "Callable",
        "Type",
        "TypeVar",
        "Generic",
        "Protocol",
        "Literal",
        "Final",
        "ClassVar",
        "TYPE_CHECKING",
    }

    # Common standard library modules
    stdlib_modules = {
        "os",
        "sys",
        "pathlib",
        "json",
        "datetime",
        "time",
        "logging",
        "collections",
        "itertools",
        "functools",
        "operator",
        "re",
        "urllib",
        "http",
        "socket",
        "threading",
        "asyncio",
        "typing",
    }

    for file_path, line_num, message in f821_errors:
        # Extract the undefined name from the message
        # Format: "F821 Undefined name `name`"
        name_match = re.search(r"Undefined name `([^`]+)`", message)
        if not name_match:
            categories["other"].append((file_path, line_num, message))
            continue

        undefined_name = name_match.group(1)

        # Categorize based on the undefined name
        if undefined_name in typing_imports:
            categories["missing_typing_imports"].append((file_path, line_num, message))
        elif undefined_name in stdlib_modules:
            categories["missing_standard_library"].append(
                (file_path, line_num, message)
            )
        elif "." in undefined_name and not undefined_name.startswith("."):
            # Likely a third-party import (e.g., 'requests.get', 'numpy.array')
            categories["missing_third_party"].append((file_path, line_num, message))
        elif undefined_name.startswith('"') and undefined_name.endswith('"'):
            # Forward reference (string type hint)
            categories["forward_references"].append((file_path, line_num, message))
        else:
            # Could be circular dependency or undefined variable
            categories["undefined_variables"].append((file_path, line_num, message))

    return categories


def generate_analysis_report(
    errors_by_code: dict[str, list], f821_categories: dict[str, list]
) -> str:
    """Generate comprehensive analysis report."""
    report = []
    report.append("# F821 Error Analysis Report - The Phoenix Protocol Phase 5.2")
    report.append("")
    report.append("## Executive Summary")
    report.append("")

    total_errors = sum(len(errors) for errors in errors_by_code.values())
    f821_count = len(errors_by_code.get("F821", []))

    report.append(f"- **Total linting errors**: {total_errors:,}")
    report.append(f"- **F821 undefined-name errors**: {f821_count:,}")
    report.append(
        f"- **F821 percentage of total**: {f821_count / total_errors * 100:.1f}%"
    )
    report.append("")

    report.append("## Top 10 Most Frequent Error Codes")
    report.append("")
    report.append("| Error Code | Count | Percentage | Description |")
    report.append("|------------|-------|-------------|-------------|")

    sorted_codes = sorted(errors_by_code.items(), key=lambda x: len(x[1]), reverse=True)
    for code, errors in sorted_codes[:10]:
        count = len(errors)
        percentage = count / total_errors * 100
        description = get_error_description(code)
        report.append(f"| {code} | {count:,} | {percentage:.1f}% | {description} |")

    report.append("")
    report.append("## F821 Error Categorization")
    report.append("")

    for category, errors in f821_categories.items():
        if errors:
            count = len(errors)
            percentage = count / f821_count * 100 if f821_count > 0 else 0
            report.append(f"### {category.replace('_', ' ').title()}")
            report.append(f"- **Count**: {count:,} ({percentage:.1f}% of F821 errors)")
            report.append(f"- **Priority**: {get_category_priority(category)}")
            report.append("")

            # Show top files for this category
            file_counts = Counter(error[0] for error in errors)
            report.append("**Top files:**")
            for file_path, file_count in file_counts.most_common(5):
                report.append(f"- `{file_path}`: {file_count} errors")
            report.append("")

    report.append("## Recommended Action Plan")
    report.append("")
    report.append("1. **Missing Typing Imports** (Highest Priority)")
    report.append("   - Add missing imports from `typing` module")
    report.append("   - Focus on `List`, `Dict`, `Optional`, `Union`")
    report.append("")
    report.append("2. **Missing Standard Library** (High Priority)")
    report.append("   - Add missing standard library imports")
    report.append("   - Common modules: `os`, `sys`, `pathlib`, `json`")
    report.append("")
    report.append("3. **Circular Dependencies** (Medium Priority)")
    report.append("   - Refactor using `TYPE_CHECKING` pattern")
    report.append("   - Move imports inside `if TYPE_CHECKING:` blocks")
    report.append("")
    report.append("4. **Forward References** (Review Required)")
    report.append("   - Validate if string type hints are intentional")
    report.append("   - Preserve valid forward references")
    report.append("")

    return "\n".join(report)


def get_error_description(code: str) -> str:
    """Get human-readable description for error codes."""
    descriptions = {
        "F821": "Undefined name (NameError precursor)",
        "ANN001": "Missing type annotation for function argument",
        "ANN201": "Missing return type annotation",
        "ANN202": "Missing return type annotation for private function",
        "ANN101": "Missing type annotation for method",
        "S101": "Use of assert detected",
        "S311": "Standard pseudo-random generators are not suitable for cryptographic purposes",
        "E501": "Line too long",
        "F401": "Imported but unused",
        "F841": "Local variable assigned but never used",
    }
    return descriptions.get(code, "Unknown error")


def get_category_priority(category: str) -> str:
    """Get priority level for error category."""
    priorities = {
        "missing_typing_imports": "HIGHEST",
        "missing_standard_library": "HIGH",
        "missing_third_party": "HIGH",
        "circular_dependencies": "MEDIUM",
        "forward_references": "REVIEW",
        "undefined_variables": "MEDIUM",
        "other": "LOW",
    }
    return priorities.get(category, "UNKNOWN")


def main():
    """Main analysis function."""
    log_file = "ruff_errors.log"

    if not Path(log_file).exists():
        print(
            f"Error: {log_file} not found. Please run 'ruff check . > ruff_errors.log' first."
        )
        return

    print("Analyzing ruff errors...")
    errors_by_code = parse_ruff_errors(log_file)

    print("Categorizing F821 errors...")
    f821_errors = errors_by_code.get("F821", [])
    f821_categories = analyze_f821_errors(f821_errors)

    print("Generating analysis report...")
    report = generate_analysis_report(errors_by_code, f821_categories)

    # Write report to file
    with open("LINTING_ANALYSIS.md", "w") as f:
        f.write(report)

    print("Analysis complete!")
    print(f"- Total errors: {sum(len(errors) for errors in errors_by_code.values()):,}")
    print(f"- F821 errors: {len(f821_errors):,}")
    print("- Report saved to: LINTING_ANALYSIS.md")


if __name__ == "__main__":
    main()
