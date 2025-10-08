from typing import Dict, List

#!/usr/bin/env python3
"""
PAKE+ Syntax Validation Script
Automated detection and prevention of common syntax errors
Based on learnings from monorepo recovery
"""

import logging
from pathlib import Path
import re
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SyntaxValidator:
    """Validates syntax across Python and JavaScript files"""

def __init__(self, base_path: Any = None) -> None:
        self.base_path = Path(base_path)
        self.errors: list[dict[str, Any]] = []

        # Pattern definitions based on monorepo issues we found
        self.python_patterns = {
            "malformed_env_vars": {
                "pattern": r"['\"]process\.env\.[^'\"]*\|\|[^'\"]*['\"]",
                "description": "Malformed environment variable with JavaScript-style fallback",
                "severity": "critical",
            },
            "double_quotes_in_single": {
                "pattern": r"'[^']*'[^']*'[^']*'",
                "description": "Potentially malformed string with multiple quotes",
                "severity": "warning",
            },
            "incomplete_string_concat": {
                "pattern": r'["\'][^"\']*\s+["\'][^"\']*["\']',
                "description": "Possible incomplete string concatenation",
                "severity": "warning",
            },
        }

        self.javascript_patterns = {
            "misplaced_shebang": {
                "pattern": r"^(?!#!/).*#!/usr/bin/env\s+node",
                "description": "Shebang line not at file start",
                "severity": "critical",
            },
            "malformed_env_check": {
                "pattern": r"process\.env\.NODE_ENV\s*[!=]==?\s*['\"]process\.env\.",
                "description": "Malformed environment variable comparison",
                "severity": "critical",
            },
        }

        self.typescript_patterns = {
            "malformed_interface": {
                "pattern": r"interface\s+\w+\s*{\s*[^}]*function\s+\w+\(\)\s*{\s*\[native\s+code\]\s*}",
                "description": "Malformed interface with native code reference",
                "severity": "critical",
            },
        }

    def validate_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Validate a single file for syntax issues"""
        file_errors = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Determine file type and apply appropriate patterns
            if file_path.suffix == ".py":
                patterns = self.python_patterns
            elif file_path.suffix in [".js", ".ts"]:
                patterns = self.javascript_patterns
                if file_path.suffix == ".ts":
                    patterns.update(self.typescript_patterns)
            else:
                return file_errors

            # Apply pattern matching
            for pattern_name, pattern_info in patterns.items():
                matches = re.finditer(
                    pattern_info["pattern"],
                    content,
                    re.MULTILINE | re.DOTALL,
                )

                for match in matches:
                    # Calculate line number
                    line_num = content[: match.start()].count("\n") + 1

                    error = {
                        "file": str(file_path),
                        "line": line_num,
                        "pattern": pattern_name,
                        "description": pattern_info["description"],
                        "severity": pattern_info["severity"],
                        "matched_text": match.group()[:100],  # Truncate long matches
                        "context": self._get_context(
                            content,
                            match.start(),
                            match.end(),
                        ),
                    }
                    file_errors.append(error)

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Error reading file %s: %s", file_path, e)

        return file_errors

    def _get_context(
        self,
        content: str,
        start: int,
        end: int,
        context_lines: int = 2,
    ) -> str:
        """Get context around the error location"""
        lines = content.split("\n")
        error_line = content[:start].count("\n")

        start_line = max(0, error_line - context_lines)
        end_line = min(len(lines), error_line + context_lines + 1)

        context = []
        for i in range(start_line, end_line):
            marker = " → " if i == error_line else "   "
            context.append(f"{i + 1:3d}{marker}{lines[i]}")

        return "\n".join(context)

    def validate_directory(self, extensions: list[str] = None) -> None:
        """Validate all files in directory tree"""
        if extensions is None:
            extensions = [".py", ".js", ".ts"]

        logger.info("Starting validation of %s", self.base_path)

        file_count = 0
        for ext in extensions:
            pattern = f"**/*{ext}"
            for file_path in self.base_path.rglob(pattern):
                # Skip common directories to avoid
                if any(
                    part in str(file_path)
                    for part in [
                        "node_modules",
                        ".git",
                        "__pycache__",
                        ".venv",
                        "dist",
                        ".next",
                    ]
                ):
                    continue

                file_errors = self.validate_file(file_path)
                self.errors.extend(file_errors)
                file_count += 1

        logger.info("Validated %s files", file_count)

    def report_errors(self) -> int:
        """Report all found errors and return error count"""
        if not self.errors:
            logger.info("✅ No syntax issues found!")
            return 0

        # Group errors by severity
        critical_errors = [e for e in self.errors if e["severity"] == "critical"]
        warnings = [e for e in self.errors if e["severity"] == "warning"]

        if critical_errors:
            logger.error("🚨 Found %s critical syntax errors:", len(critical_errors))
            for error in critical_errors:
                logger.error("\n  File: %s:%s", error["file"], error["line"])
                logger.error("  Issue: %s", error["description"])
                logger.error("  Pattern: %s", error["pattern"])
                logger.error("  Context:\n%s", error["context"])
                logger.error("-" * 80)

        if warnings:
            logger.warning("⚠️  Found %s warnings:", len(warnings))
            for warning in warnings:
                logger.warning("\n  File: %s:%s", warning["file"], warning["line"])
                logger.warning("  Issue: %s", warning["description"])
                logger.warning("  Context:\n%s", warning["context"])

        return len(critical_errors)

    def fix_common_issues(self, dry_run: bool = True) -> int:
        """Attempt to fix common syntax issues automatically"""
        if not self.errors:
            return 0

        fixes_applied = 0

        for error in self.errors:
            if error["severity"] != "critical":
                continue

            file_path = Path(error["file"])

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                original_content = content

                # Apply fixes based on pattern
                if error["pattern"] == "malformed_env_vars":
                    # Fix JavaScript-style env vars in Python
                    content = re.sub(
                        r"['\"]process\.env\.[^'\"]*\|\|[^'\"]*['\"]",
                        "'REDACTED_SECRET'",
                        content,
                    )
                elif error["pattern"] == "misplaced_shebang":
                    # Move shebang to start of file
                    lines = content.split("\n")
                    shebang_lines = [
                        i for i, line in enumerate(lines) if line.startswith("#!/")
                    ]
                    if shebang_lines:
                        shebang = lines.pop(shebang_lines[0])
                        lines.insert(0, shebang)
                        content = "\n".join(lines)

                if content != original_content:
                    if not dry_run:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        logger.info("🔧 Fixed %s in %s", error["pattern"], file_path)
                    else:
                        logger.info(
                            "🔍 Would fix %s in %s", error["pattern"], file_path
                        )
                    fixes_applied += 1

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error("Error fixing file %s: %s", file_path, e)

        return fixes_applied


def main(self) -> None:
    """Main validation function"""
    import argparse

    parser = argparse.ArgumentParser(description="PAKE+ Syntax Validator")
    parser.add_argument("--path", default=".", help="Path to validate")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview fixes only",
    )

    args = parser.parse_args()

    validator = SyntaxValidator(args.path)

    # Run validation
    validator.validate_directory()

    # Report errors
    critical_count = validator.report_errors()

    # Apply fixes if requested
    if args.fix:
        fixes = validator.fix_common_issues(dry_run=args.dry_run)
        if fixes:
            logger.info("Applied %s fixes", fixes)

    # Exit with error code if critical issues found
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == "__main__":
    main()
