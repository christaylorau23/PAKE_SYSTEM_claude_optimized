#!/usr/bin/env python3
"""Ruff Error Analysis Script.
=========================

This script parses the ruff_errors.log file and generates a comprehensive
analysis report of linting violations, categorizing them by error code and
file location for strategic remediation planning.

Part of The Phoenix Protocol - Phase 5.1: Triage and Intelligence Gathering
"""

from collections import Counter, defaultdict
from pathlib import Path
import re
import sys
from typing import DefaultDict, Dict, List, Tuple


def parse_ruff_log(
    log_file_path: str,
) -> tuple[dict[str, int], dict[str, int], list[tuple[str, int]]]:
    """Parse the ruff error log file and extract error statistics.

    Args:
        log_file_path: Path to the ruff_errors.log file

    Returns:
        Tuple containing:
        - error_code_counts: Dict mapping error codes to their frequency
        - file_error_counts: Dict mapping file paths to error counts
        - file_error_list: List of tuples (file_path, error_count) sorted by count
    """
    error_code_counts: defaultdict[str, int] = defaultdict(int)
    file_error_counts: defaultdict[str, int] = defaultdict(int)

    print(f"Parsing ruff error log: {log_file_path}")

    try:
        with open(log_file_path, encoding="utf-8") as f:
            line_count = 0
            error_count = 0

            for line in f:
                line_count += 1
                line_stripped = line.strip()

                if not line_stripped:
                    continue

                # Look for error codes - they appear as ANSI escape sequences
                # Pattern: \x1b[1m\x1b[91mS607 \x1b[0m\x1b[1mStarting a process...
                if "\x1b" in line:
                    # Use regex to find error codes embedded in ANSI sequences
                    # Look for pattern like \x1b[1m\x1b[91mS607
                    error_code_match = re.search(
                        r"\x1b\[1m\x1b\[91m([A-Z][A-Z0-9]{2,5})\s", line
                    )
                    if error_code_match:
                        error_code = error_code_match.group(1)
                        if len(error_code) >= 3:
                            error_code_counts[error_code] += 1
                            error_count += 1

                # Look for file paths in lines with --> pattern
                if "-->" in line:
                    # Pattern: \x1b[ANSI_CODES]-->\x1b[ANSI_CODES] file_path:line:column
                    if ":" in line:
                        # Extract file path by finding the part after --> and before the first :
                        after_arrow = line.split("-->", 1)
                        if len(after_arrow) > 1:
                            file_part = after_arrow[1]
                            # Remove ANSI codes and extract file path
                            file_part_clean = re.sub(r"\x1b\[[^\]]*\]", "", file_part)
                            if ":" in file_part_clean:
                                file_path = file_part_clean.split(":")[0].strip()
                                # Clean up any remaining ANSI artifacts
                                file_path = re.sub(
                                    r"^[^\w/]*", "", file_path
                                )  # Remove leading non-word chars
                                if (
                                    file_path and "." in file_path
                                ):  # Basic validation that it's a file path
                                    file_error_counts[file_path] += 1

                # Progress indicator for large files
                if line_count % 10000 == 0:
                    print(
                        f"Processed {line_count:,} lines, found {error_count:,} errors..."
                    )

    except FileNotFoundError:
        print(f"Error: Could not find log file {log_file_path}")
        sys.exit(1)
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error reading log file: {e}")
        sys.exit(1)

    # Convert to regular dicts and sort
    error_code_counts = dict(error_code_counts)
    file_error_counts = dict(file_error_counts)

    # Sort files by error count (descending)
    file_error_list = sorted(
        file_error_counts.items(), key=lambda x: x[1], reverse=True
    )

    print("Parsing complete!")
    print(f"Total lines processed: {line_count:,}")
    print(f"Total errors found: {error_count:,}")
    print(f"Unique error codes: {len(error_code_counts)}")
    print(f"Files with errors: {len(file_error_counts)}")

    return error_code_counts, file_error_counts, file_error_list


def generate_markdown_report(
    error_code_counts: dict[str, int],
    file_error_list: list[tuple[str, int]],
    output_file: str,
) -> None:
    """Generate a comprehensive Markdown report of the linting analysis.

    Args:
        error_code_counts: Dict mapping error codes to their frequency
        file_error_list: List of tuples (file_path, error_count) sorted by count
        output_file: Path to the output Markdown file
    """
    # Get top 10 error codes
    top_error_codes = Counter(error_code_counts).most_common(10)

    # Get top 10 files with most errors
    top_files = file_error_list[:10]

    # Calculate total errors
    total_errors = sum(error_code_counts.values())

    # Safety check for empty results
    if total_errors == 0:
        print("Warning: No errors found in the log file. Check the ruff output format.")
        return

    # Calculate F821 percentage
    f821_count = error_code_counts.get("F821", 0)
    f821_percentage = (f821_count / total_errors * 100) if total_errors > 0 else 0

    # Generate the report
    report_content = f"""# Linting Analysis Report
## The Phoenix Protocol - Phase 5.1: Triage and Intelligence Gathering

**Generated:** {Path().cwd()}
**Total Errors Analyzed:** {total_errors:,}
**Unique Error Codes:** {len(error_code_counts)}
**Files with Errors:** {len(file_error_list)}

## Executive Summary

This analysis reveals the scope and nature of linting violations across the PAKE System codebase. The data-driven approach enables strategic remediation by identifying:

- **Critical Error Patterns:** The most frequent error types that pose the highest risk
- **Hotspot Files:** Files with concentrated error density requiring immediate attention
- **Systemic Issues:** Patterns that indicate root causes rather than isolated problems

### Key Findings

- **F821 (undefined-name) violations:** {f821_count:,} ({f821_percentage:.1f}% of total errors)
- **Top error category:** {top_error_codes[0][0]} with {top_error_codes[0][1]:,} violations
- **Most problematic file:** {top_files[0][0]} with {top_files[0][1]:,} errors

## Top 10 Most Frequent Error Codes

| Rank | Error Code | Count | Percentage | Description |
|------|------------|-------|------------|-------------|
"""

    # Add error code table rows
    for i, (error_code, count) in enumerate(top_error_codes, 1):
        percentage = (count / total_errors * 100) if total_errors > 0 else 0
        description = get_error_description(error_code)
        report_content += f"| {i} | `{error_code}` | {count:,} | {percentage:.1f}% | {description} |\n"

    report_content += """
## Top 10 Files with Highest Error Density

| Rank | File Path | Error Count | Percentage | Priority Level |
|------|-----------|-------------|------------|----------------|
"""

    # Add file table rows
    for i, (file_path, count) in enumerate(top_files, 1):
        percentage = (count / total_errors * 100) if total_errors > 0 else 0

        # Determine priority level based on error count
        if count >= 1000:
            priority = "🔴 CRITICAL"
        elif count >= 500:
            priority = "🟠 HIGH"
        elif count >= 100:
            priority = "🟡 MEDIUM"
        else:
            priority = "🟢 LOW"

        report_content += (
            f"| {i} | `{file_path}` | {count:,} | {percentage:.1f}% | {priority} |\n"
        )

    report_content += f"""
## Strategic Remediation Recommendations

### Phase 5.2: The Great Import Sweep (F821 Focus)
- **Target:** {f821_count:,} F821 violations ({f821_percentage:.1f}% of total)
- **Strategy:** Systematic import resolution and circular dependency refactoring
- **Expected Impact:** Elimination of NameError runtime exceptions

### Priority File Remediation
Focus remediation efforts on the top 10 files identified above, as they contain:
- **{sum(count for _, count in top_files[:5]):,} errors** in the top 5 files alone
- **Concentrated complexity** that can be addressed efficiently
- **High-impact fixes** that will dramatically reduce total error count

### Error Pattern Analysis
The error distribution reveals:
- **Systemic import issues** (F821 dominance)
- **Type annotation gaps** (ANN rules)
- **Security considerations** (S rules)
- **Code quality patterns** (other rule categories)

## Next Steps

1. **Execute Phase 5.2:** Focus exclusively on F821 undefined-name violations
2. **File-by-file remediation:** Address hotspot files in priority order
3. **Pattern-based fixes:** Apply systematic solutions for common error types
4. **Validation:** Re-run analysis after each remediation phase

---
*This report was generated as part of The Phoenix Protocol for systematic codebase modernization and architectural integrity.*
"""

    # Write the report
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Report generated successfully: {output_file}")
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error writing report: {e}")
        sys.exit(1)


def get_error_description(error_code: str) -> str:
    """Get a human-readable description for common ruff error codes.

    Args:
        error_code: The ruff error code (e.g., 'F821', 'ANN001')

    Returns:
        Human-readable description of the error
    """
    descriptions = {
        "F821": "undefined-name - Variable/function/class name not defined",
        "ANN001": "missing-type-annotation - Function argument missing type annotation",
        "ANN201": "missing-return-type-annotation - Function missing return type annotation",
        "ANN202": "missing-return-type-annotation - Private function missing return type annotation",
        "ANN101": "missing-type-annotation - Missing type annotation for self in method",
        "S101": "assert-used - Use of assert detected (removed in production)",
        "S102": "exec-used - Use of exec detected (security risk)",
        "S103": "subprocess-popen-preexec-fn - Use of subprocess with shell=True",
        "E501": "line-too-long - Line exceeds maximum length",
        "E302": "expected-2-blank-lines - Expected 2 blank lines before class definition",
        "E303": "too-many-blank-lines - Too many blank lines",
        "W293": "blank-line-contains-whitespace - Blank line contains whitespace",
        "F401": "unused-import - Imported but unused",
        "F841": "unused-variable - Local variable assigned but never used",
        "B006": "mutable-argument - Do not use mutable data structures for argument defaults",
        "B008": "do-not-perform-direct-calls - Do not perform function calls in argument defaults",
    }

    return descriptions.get(error_code, f"Unknown error code: {error_code}")


def main():
    """Main execution function."""
    log_file = "ruff_errors.log"
    output_file = "LINTING_ANALYSIS.md"

    print("=" * 60)
    print("RUFF ERROR ANALYSIS SCRIPT")
    print("The Phoenix Protocol - Phase 5.1")
    print("=" * 60)

    # Parse the log file
    error_code_counts, file_error_counts, file_error_list = parse_ruff_log(log_file)

    # Generate the markdown report
    generate_markdown_report(error_code_counts, file_error_list, output_file)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"📊 Total errors analyzed: {sum(error_code_counts.values()):,}")
    print(f"📁 Files with errors: {len(file_error_counts)}")
    print(f"🔍 Unique error types: {len(error_code_counts)}")
    print(f"📄 Report generated: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
