#!/usr/bin/env python3
"""
Lint Validation Script
Runs all linting checks (Ruff, Black, isort, ESLint, Prettier)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class LintValidator:
    """Lint validation runner"""

    def __init__(self, verbose: bool = False, fix: bool = False):
        self.verbose = verbose
        self.fix = fix
        self.project_root = Path(__file__).parent.parent
        self.results: list[tuple[str, bool, str]] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] [{level}] {message}")

    def run_command(
        self, name: str, command: list[str], description: str
    ) -> tuple[str, bool, str]:
        """Run a command and return results"""
        self.log(f"Running {name}: {description}")
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                self.log(f"✅ {name} passed ({duration:.2f}s)", "INFO")
                return name, True, result.stdout
            else:
                self.log(f"❌ {name} failed ({duration:.2f}s)", "ERROR")
                if self.verbose:
                    self.log(f"Error: {result.stderr}", "ERROR")
                return name, False, result.stderr

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log(f"⏰ {name} timed out after 300s", "ERROR")
            return name, False, "Timeout after 300s"
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {name} crashed: {e}", "ERROR")
            return name, False, str(e)

    def run_ruff_check(self) -> tuple[str, bool, str]:
        """Run Ruff linting"""
        if self.fix:
            command = [
                "poetry",
                "run",
                "ruff",
                "check",
                "--fix",
                "src/",
                "tests/",
                "scripts/",
            ]
            description = "Run Ruff linting with auto-fix"
        else:
            command = ["poetry", "run", "ruff", "check", "src/", "tests/", "scripts/"]
            description = "Run Ruff linting"

        return self.run_command("ruff", command, description)

    def run_black_check(self) -> tuple[str, bool, str]:
        """Run Black formatting check"""
        if self.fix:
            command = ["poetry", "run", "black", "src/", "tests/", "scripts/"]
            description = "Run Black formatting with auto-fix"
        else:
            command = [
                "poetry",
                "run",
                "black",
                "--check",
                "src/",
                "tests/",
                "scripts/",
            ]
            description = "Check Black formatting"

        return self.run_command("black", command, description)

    def run_isort_check(self) -> tuple[str, bool, str]:
        """Run isort import sorting check"""
        if self.fix:
            command = ["poetry", "run", "isort", "src/", "tests/", "scripts/"]
            description = "Run isort import sorting with auto-fix"
        else:
            command = [
                "poetry",
                "run",
                "isort",
                "--check-only",
                "src/",
                "tests/",
                "scripts/",
            ]
            description = "Check isort import sorting"

        return self.run_command("isort", command, description)

    def run_eslint_check(self) -> tuple[str, bool, str]:
        """Run ESLint for TypeScript/JavaScript"""
        if self.fix:
            command = ["npm", "run", "lint:fix"]
            description = "Run ESLint with auto-fix"
        else:
            command = ["npm", "run", "lint"]
            description = "Run ESLint"

        return self.run_command("eslint", command, description)

    def run_prettier_check(self) -> tuple[str, bool, str]:
        """Run Prettier formatting check"""
        if self.fix:
            command = ["npm", "run", "format"]
            description = "Run Prettier formatting with auto-fix"
        else:
            command = ["npm", "run", "format:check"]
            description = "Check Prettier formatting"

        return self.run_command("prettier", command, description)

    def run_all_checks(self) -> bool:
        """Run all linting checks"""
        self.log("Starting lint validation...")

        # Run all checks
        checks = [
            self.run_ruff_check(),
            self.run_black_check(),
            self.run_isort_check(),
            self.run_eslint_check(),
            self.run_prettier_check(),
        ]

        self.results.extend(checks)

        # Print summary
        self.print_summary()

        # Return success if all checks passed
        return all(result[1] for result in checks)

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("🎨 LINT VALIDATION SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)

        print(f"📊 Total Checks: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"📈 Success Rate: {(passed/total*100):.1f}%")

        print("\n📋 Results by Tool:")
        for name, success, output in self.results:
            status_emoji = "✅" if success else "❌"
            print(
                f"  {status_emoji} {name.upper()}: {'PASSED' if success else 'FAILED'}"
            )

            if not success and self.verbose:
                print(f"     Error: {output[:100]}...")

        print("=" * 60)

        if passed == total:
            print("\n🎉 All lint checks passed!")
        else:
            print(f"\n❌ {total - passed} lint check(s) failed!")
            if self.fix:
                print("💡 Auto-fix was applied. Please review changes and commit.")
            else:
                print("💡 Run with --fix to automatically fix issues.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Lint Validation")
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix linting issues"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--tool",
        choices=["ruff", "black", "isort", "eslint", "prettier", "all"],
        default="all",
        help="Run specific linting tool",
    )

    args = parser.parse_args()

    # Create validator
    validator = LintValidator(verbose=args.verbose, fix=args.fix)

    # Run specific tool or all
    if args.tool == "all":
        success = validator.run_all_checks()
    else:
        if args.tool == "ruff":
            result = validator.run_ruff_check()
        elif args.tool == "black":
            result = validator.run_black_check()
        elif args.tool == "isort":
            result = validator.run_isort_check()
        elif args.tool == "eslint":
            result = validator.run_eslint_check()
        elif args.tool == "prettier":
            result = validator.run_prettier_check()

        validator.results.append(result)
        validator.print_summary()
        success = result[1]

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
