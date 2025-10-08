from typing import List

#!/usr/bin/env python3
"""
Setup and Validation Script for Code Formatters
Configures and validates Black, Prettier, Ruff, and isort across the PAKE System codebase.
"""

from pathlib import Path
import subprocess
import sys


class FormatterSetup:
    """Setup and validation for code formatters"""

    def __init__(self) -> None:
        self.project_root = Path(__file__).parent.parent
        self.python_dirs = ["src", "tests", "scripts"]
        self.js_ts_patterns = ["**/*.js", "**/*.ts", "**/*.tsx", "**/*.json"]

    def run_command(
        self, command: list[str], description: str, check: bool = True
    ) -> tuple[bool, str]:
        """Run a command and return success status and output"""
        print(f"\n🔄 {description}")
        print(f"Command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=check,
            )
            print(f"✅ {description} completed successfully")
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed")
            print(f"Exit code: {e.returncode}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            return False, e.stderr or e.stdout

    def check_tools_available(self) -> bool:
        """Check if all required formatting tools are available"""
        print("🔧 Checking formatter tool availability...")

        tools = [
            (["python", "-m", "black", "--version"], "Black"),
            (["python", "-m", "ruff", "--version"], "Ruff"),
            (["python", "-m", "isort", "--version"], "isort"),
            (["npx", "prettier", "--version"], "Prettier"),
        ]

        all_available = True
        for command, name in tools:
            success, output = self.run_command(command, f"Checking {name}")
            if success:
                print(f"  ✅ {name}: {output.strip()}")
            else:
                print(f"  ❌ {name}: Not available")
                all_available = False

        return all_available

    def validate_python_formatting(self, fix: bool = False) -> bool:
        """Validate Python code formatting with Black and Ruff"""
        print("\n🐍 Python Code Formatting Validation")

        # Black formatting check/fix
        black_command = ["python", "-m", "black"]
        if not fix:
            black_command.append("--check")
        black_command.extend(self.python_dirs)

        success, output = self.run_command(
            black_command,
            f"{'Applying' if fix else 'Checking'} Black formatting",
            check=False,
        )

        if not success and not fix:
            print("  ⚠️  Python files need Black formatting")
        elif fix:
            print("  ✅ Python files formatted with Black")

        # Ruff linting and formatting
        ruff_check_command = ["python", "-m", "ruff", "check"]
        if fix:
            ruff_check_command.append("--fix")
        ruff_check_command.extend(self.python_dirs)

        ruff_success, ruff_output = self.run_command(
            ruff_check_command,
            f"{'Fixing' if fix else 'Checking'} Ruff linting",
            check=False,
        )

        # Ruff formatting
        ruff_format_command = ["python", "-m", "ruff", "format"]
        if not fix:
            ruff_format_command.append("--check")
        ruff_format_command.extend(self.python_dirs)

        ruff_format_success, _ = self.run_command(
            ruff_format_command,
            f"{'Applying' if fix else 'Checking'} Ruff formatting",
            check=False,
        )

        # isort import sorting
        isort_command = ["python", "-m", "isort"]
        if not fix:
            isort_command.append("--check-only")
        isort_command.extend(self.python_dirs)

        isort_success, _ = self.run_command(
            isort_command,
            f"{'Applying' if fix else 'Checking'} isort import sorting",
            check=False,
        )

        return success and ruff_success and ruff_format_success and isort_success

    def validate_js_ts_formatting(self, fix: bool = False) -> bool:
        """Validate JavaScript/TypeScript code formatting with Prettier"""
        print("\n🔧 JavaScript/TypeScript Code Formatting Validation")

        prettier_command = ["npx", "prettier"]
        if fix:
            prettier_command.extend(["--write", "."])
        else:
            prettier_command.extend(["--check", "."])

        success, output = self.run_command(
            prettier_command,
            f"{'Applying' if fix else 'Checking'} Prettier formatting",
            check=False,
        )

        if not success and not fix:
            print("  ⚠️  JavaScript/TypeScript files need Prettier formatting")
        elif fix:
            print("  ✅ JavaScript/TypeScript files formatted with Prettier")

        return success

    def create_format_script(self) -> None:
        """Create a comprehensive format script in package.json"""
        print("\n📝 Format scripts are already configured in package.json")
        print("Available commands:")
        print("  npm run format           # Format all files (Python + JS/TS)")
        print("  npm run format:check     # Check all files without changes")
        print("  npm run format:python    # Format Python files only")
        print("  npm run format:python:check # Check Python files only")
        print("  npm run lint             # Lint all files")
        print("  npm run lint:fix         # Fix linting issues")

    def validate_configuration_files(self) -> bool:
        """Validate that all configuration files are present and correct"""
        print("\n📋 Configuration File Validation")

        config_files = [
            (".prettierrc.json", "Prettier configuration"),
            (".prettierignore", "Prettier ignore file"),
            ("pyproject.toml", "Python project configuration"),
        ]

        all_present = True
        for file_path, description in config_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"  ✅ {description}: {file_path}")
            else:
                print(f"  ❌ {description}: {file_path} (missing)")
                all_present = False

        # Check specific configurations in pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            required_sections = ["[tool.black]", "[tool.ruff]", "[tool.isort]"]
            for section in required_sections:
                if section in content:
                    print(f"  ✅ Configuration section: {section}")
                else:
                    print(f"  ❌ Missing configuration: {section}")
                    all_present = False

        return all_present

    def generate_pre_commit_hook(self) -> None:
        """Generate a pre-commit hook for automatic formatting"""
        hook_content = """#!/bin/sh
# Pre-commit hook for PAKE System
# Runs formatters and linters before commit

echo "🔄 Running pre-commit formatters and linters..."

# Run Python formatting and linting
echo "🐍 Formatting Python code..."
python -m black src/ tests/ scripts/ --exclude=black_env || exit 1
python -m ruff check --fix src/ tests/ scripts/ || exit 1
python -m ruff format src/ tests/ scripts/ || exit 1
python -m isort src/ tests/ scripts/ || exit 1

# Run JavaScript/TypeScript formatting
echo "🔧 Formatting JavaScript/TypeScript code..."
npx prettier --write . || exit 1

echo "✅ Pre-commit formatting completed successfully!"
"""

        hooks_dir = self.project_root / ".git" / "hooks"
        hook_file = hooks_dir / "pre-commit"

        if hooks_dir.exists():
            hook_file.write_text(hook_content)
            hook_file.chmod(0o755)
            print(f"✅ Pre-commit hook created: {hook_file}")
        else:
            print("⚠️  Git hooks directory not found, skipping pre-commit hook creation")

    def run_comprehensive_check(self, fix: bool = False) -> bool:
        """Run comprehensive formatting validation"""
        print("🚀 Running Comprehensive Code Formatting Validation")
        print("=" * 60)

        # Check tool availability
        if not self.check_tools_available():
            print("❌ Some required tools are missing")
            return False

        # Validate configuration files
        if not self.validate_configuration_files():
            print("❌ Some configuration files are missing or incomplete")
            return False

        # Validate Python formatting
        python_success = self.validate_python_formatting(fix)

        # Validate JS/TS formatting
        js_ts_success = self.validate_js_ts_formatting(fix)

        # Create format scripts info
        self.create_format_script()

        # Generate pre-commit hook
        if fix:
            self.generate_pre_commit_hook()

        # Summary
        print("\n" + "=" * 60)
        if python_success and js_ts_success:
            if fix:
                print("🎉 All code has been formatted successfully!")
            else:
                print("✅ All code is properly formatted!")
            print("📝 Use 'npm run format' to format all files")
            print("🔍 Use 'npm run format:check' to check formatting")
            return True
        if not fix:
            print("⚠️  Some files need formatting. Run with --fix to apply changes.")
            print("🔧 Quick fix: npm run format")
        else:
            print("❌ Some formatting issues could not be automatically fixed")
        return False


def main(self) -> None:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Setup and validate code formatters")
    parser.add_argument("--fix", action="store_true", help="Apply formatting fixes")
    parser.add_argument(
        "--check-only", action="store_true", help="Only check formatting, don't fix"
    )

    args = parser.parse_args()

    formatter = FormatterSetup()

    if args.check_only:
        success = formatter.run_comprehensive_check(fix=False)
    else:
        success = formatter.run_comprehensive_check(fix=args.fix)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
