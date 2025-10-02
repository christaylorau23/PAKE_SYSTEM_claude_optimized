#!/usr/bin/env python3
"""
Type Check Validation Script
Runs MyPy and TypeScript type checking
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class TypeCheckValidator:
    """Type check validation runner"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
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

    def run_mypy_check(self) -> tuple[str, bool, str]:
        """Run MyPy type checking"""
        command = [
            "poetry",
            "run",
            "mypy",
            "src/",
            "--strict",
            "--show-error-codes",
            "--ignore-missing-imports",
        ]
        description = "Run MyPy type checking with strict mode"

        return self.run_command("mypy", command, description)

    def run_typescript_check(self) -> tuple[str, bool, str]:
        """Run TypeScript type checking"""
        command = ["npm", "run", "type-check"]
        description = "Run TypeScript type checking"

        return self.run_command("typescript", command, description)

    def run_all_checks(self) -> bool:
        """Run all type checking"""
        self.log("Starting type check validation...")

        # Run all checks
        checks = [self.run_mypy_check(), self.run_typescript_check()]

        self.results.extend(checks)

        # Print summary
        self.print_summary()

        # Return success if all checks passed
        return all(result[1] for result in checks)

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("🔍 TYPE CHECK VALIDATION SUMMARY")
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
                print(f"     Error: {output[:200]}...")

        print("=" * 60)

        if passed == total:
            print("\n🎉 All type checks passed!")
        else:
            print(f"\n❌ {total - passed} type check(s) failed!")
            print("💡 Review type errors and fix them before committing.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Type Check Validation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--tool",
        choices=["mypy", "typescript", "all"],
        default="all",
        help="Run specific type checking tool",
    )

    args = parser.parse_args()

    # Create validator
    validator = TypeCheckValidator(verbose=args.verbose)

    # Run specific tool or all
    if args.tool == "all":
        success = validator.run_all_checks()
    else:
        if args.tool == "mypy":
            result = validator.run_mypy_check()
        elif args.tool == "typescript":
            result = validator.run_typescript_check()

        validator.results.append(result)
        validator.print_summary()
        success = result[1]

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
