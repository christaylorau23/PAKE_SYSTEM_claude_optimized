#!/usr/bin/env python3
"""Strategic Linting Analysis Tool
Following The Vanguard Protocol's "Signal from the Noise" approach.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from typing import Dict, List, Tuple


def parse_ruff_log(log_file: str) -> dict[str, any]:
    """Parse ruff error log and create intelligence dashboard."""
    error_counts = Counter()
    file_counts = defaultdict(int)
    file_errors = defaultdict(list)

    # ANSI escape sequence pattern
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Remove ANSI color codes
            clean_line = ansi_escape.sub("", line)

            # Skip warning messages
            if clean_line.startswith(("warning:", "help:")):
                continue

            # Parse ruff error format: path:line:col: error_code message
            # Handle both formats: file:line:col: code message and file:line:col: code [*] message
            match = re.match(
                r"^([^:]+):(\d+):(\d+):\s+([A-Z0-9]+)(?:\s+\[[^\]]+\])?\s+(.+)$",
                clean_line,
            )
            if match:
                file_path, line_num, col_num, error_code, message = match.groups()

                error_counts[error_code] += 1
                file_counts[file_path] += 1
                file_errors[file_path].append(
                    {
                        "line": int(line_num),
                        "col": int(col_num),
                        "code": error_code,
                        "message": message,
                    }
                )

    return {
        "error_counts": dict(error_counts),
        "file_counts": dict(file_counts),
        "file_errors": dict(file_errors),
        "total_errors": sum(error_counts.values()),
        "total_files": len(file_counts),
    }


def generate_analysis_report(data: dict[str, any]) -> str:
    """Generate comprehensive Markdown analysis report."""
    report = []
    report.append("# PAKE System - Strategic Linting Analysis Report")
    report.append("")
    report.append(
        "**Following The Vanguard Protocol's 'Signal from the Noise' Approach**"
    )
    report.append("")
    report.append(f"**Total Errors**: {data['total_errors']:,}")
    report.append(f"**Total Files Affected**: {data['total_files']:,}")
    report.append("")

    # Top 10 Error Codes
    report.append("## Top 10 Most Frequent Error Codes")
    report.append("")
    report.append("| Error Code | Count | Percentage | Priority | Description |")
    report.append("|------------|-------|------------|----------|-------------|")

    error_priorities = {
        "F821": "CRITICAL - Runtime NameError risk",
        "ARG001": "HIGH - Unused function arguments",
        "Q000": "MEDIUM - Quote style consistency",
        "ARG002": "HIGH - Unused method arguments",
        "D205": "LOW - Documentation formatting",
        "SLF001": "MEDIUM - Private member access",
        "UP006": "MEDIUM - Type annotation modernization",
        "S311": "HIGH - Security: non-cryptographic random",
        "UP035": "MEDIUM - Deprecated imports",
        "B904": "HIGH - Exception handling best practices",
    }

    total_errors = data["total_errors"]
    sorted_errors = sorted(
        data["error_counts"].items(), key=lambda x: x[1], reverse=True
    )
    for i, (error_code, count) in enumerate(sorted_errors[:10], 1):
        percentage = (count / total_errors) * 100
        priority = error_priorities.get(error_code, "MEDIUM - Code quality")
        description = get_error_description(error_code)

        report.append(
            f"| {error_code} | {count:,} | {percentage:.1f}% | {priority} | {description} |"
        )

    report.append("")

    # Top 10 Files with Highest Error Density
    report.append("## Top 10 Files with Highest Error Density")
    report.append("")
    report.append("| Rank | File | Error Count | Error Density |")
    report.append("|------|------|-------------|---------------|")

    sorted_files = sorted(data["file_counts"].items(), key=lambda x: x[1], reverse=True)
    for i, (file_path, count) in enumerate(sorted_files[:10], 1):
        # Calculate error density (errors per 100 lines)
        try:
            with open(file_path) as f:
                line_count = len(f.readlines())
            density = (count / line_count) * 100 if line_count > 0 else 0
        except (FileNotFoundError, PermissionError, OSError) as e:
            density = 0

        report.append(
            f"| {i} | `{file_path}` | {count} | {density:.1f} errors/100 lines |"
        )

    report.append("")

    # Strategic Recommendations
    report.append("## Strategic Remediation Recommendations")
    report.append("")
    report.append("### Phase 1: Critical Runtime Stability (F821)")
    report.append(
        f"- **Target**: {data['error_counts'].get('F821', 0):,} F821 undefined-name errors"
    )
    report.append("- **Impact**: Eliminates potential NameError exceptions at runtime")
    report.append(
        "- **Strategy**: Systematic import resolution and circular dependency fixes"
    )
    report.append("")

    report.append("### Phase 2: Type Safety Enhancement (ANN rules)")
    ann_count = sum(
        count for code, count in data["error_counts"].items() if code.startswith("ANN")
    )
    report.append(f"- **Target**: {ann_count:,} type annotation issues")
    report.append(
        "- **Impact**: Improved IDE support, static analysis, and maintainability"
    )
    report.append(
        "- **Strategy**: Add comprehensive type hints to functions and methods"
    )
    report.append("")

    report.append("### Phase 3: Security Hardening (S rules)")
    security_count = sum(
        count for code, count in data["error_counts"].items() if code.startswith("S")
    )
    report.append(f"- **Target**: {security_count:,} security warnings")
    report.append("- **Impact**: Eliminates common security vulnerabilities")
    report.append("- **Strategy**: Replace insecure patterns with secure alternatives")
    report.append("")

    # File-by-file breakdown for top offenders
    report.append("## Detailed File Analysis (Top 5)")
    report.append("")

    for i, (file_path, count) in enumerate(sorted_files[:5], 1):
        report.append(f"### {i}. {file_path} ({count} errors)")
        report.append("")

        # Group errors by type for this file
        file_error_types = Counter()
        for error in data["file_errors"][file_path]:
            file_error_types[error["code"]] += 1

        report.append("| Error Code | Count | Lines |")
        report.append("|------------|-------|-------|")

        for error_code, error_count in file_error_types.most_common():
            lines = [
                str(e["line"])
                for e in data["file_errors"][file_path]
                if e["code"] == error_code
            ]
            report.append(
                f"| {error_code} | {error_count} | {', '.join(lines[:10])}{'...' if len(lines) > 10 else ''} |"
            )

        report.append("")

    return "\n".join(report)


def get_error_description(error_code: str) -> str:
    """Get human-readable description for error codes."""
    descriptions = {
        "F821": "Undefined name (potential NameError)",
        "ARG001": "Unused function argument",
        "Q000": "Bad quotes in inline string",
        "ARG002": "Unused method argument",
        "D205": "Missing blank line after summary",
        "SLF001": "Private member access",
        "UP006": "Non-PEP 585 annotation",
        "S311": "Suspicious non-cryptographic random usage",
        "UP035": "Deprecated import",
        "B904": "Raise without from inside except",
        "S607": "Start process with partial path",
        "G004": "Logging f-string",
        "INP001": "Implicit namespace package",
        "S603": "Subprocess without shell equals true",
        "N806": "Non-lowercase variable in function",
        "S101": "Assert statement",
        "SIM102": "Collapsible if statement",
        "D415": "Missing terminal punctuation",
        "N802": "Invalid function name",
        "B008": "Function call in default argument",
    }
    return descriptions.get(error_code, "Code quality issue")


def main():
    """Main analysis function."""
    log_file = "ruff_errors.log"

    if not Path(log_file).exists():
        print(
            f"Error: {log_file} not found. Run 'ruff check . > ruff_errors.log' first."
        )
        return

    print("🔍 Analyzing linting errors...")
    data = parse_ruff_log(log_file)

    print("📊 Generating intelligence dashboard...")
    report = generate_analysis_report(data)

    # Write report
    with open("LINTING_ANALYSIS.md", "w") as f:
        f.write(report)

    # Also create JSON data for programmatic access
    with open("linting_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print("✅ Analysis complete!")
    print("📄 Report written to: LINTING_ANALYSIS.md")
    print("📊 Data written to: linting_data.json")
    print(f"🎯 Total errors found: {data['total_errors']:,}")
    print(f"📁 Files affected: {data['total_files']:,}")


if __name__ == "__main__":
    main()
