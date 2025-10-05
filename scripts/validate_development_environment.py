#!/usr/bin/env python3
"""
PAKE System - Development Environment Validation Script
Enterprise-Grade Environment Fortification Validation
Implements Phase 1.2 of the Engineering Plan for Systematic Codebase Stabilization

This script validates that the development environment is properly configured
to prevent Python syntax errors, particularly IndentationError issues.
"""

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ValidationStatus(Enum):
    """Validation status enumeration."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class ValidationResult:
    """Validation result data structure."""

    name: str
    status: ValidationStatus
    message: str
    details: str | None = None
    fix_command: str | None = None


class DevelopmentEnvironmentValidator:
    """Validates development environment configuration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: list[ValidationResult] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 PAKE System - Development Environment Validation")
        print("=" * 60)

        # Core environment checks
        self._validate_python_version()
        self._validate_virtual_environment()
        self._validate_editor_config()
        self._validate_vscode_config()
        self._validate_pre_commit_config()
        self._validate_python_tools()
        self._validate_indentation_settings()
        self._validate_file_permissions()

        # Display results
        self._display_results()

        # Return overall status
        failed_checks = [r for r in self.results if r.status == ValidationStatus.FAIL]
        return len(failed_checks) == 0

    def _validate_python_version(self) -> None:
        """Validate Python version compatibility."""
        try:
            version = sys.version_info
            if version.major == 3 and version.minor >= 12:
                self.results.append(
                    ValidationResult(
                        name="Python Version",
                        status=ValidationStatus.PASS,
                        message=f"Python {version.major}.{version.minor}.{version.micro} is compatible",
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        name="Python Version",
                        status=ValidationStatus.FAIL,
                        message=f"Python {version.major}.{version.minor}.{version.micro} is not compatible",
                        details="PAKE System requires Python 3.12 or higher",
                        fix_command="Install Python 3.12+ or update your Python installation",
                    )
                )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="Python Version",
                    status=ValidationStatus.FAIL,
                    message=f"Failed to check Python version: {e}",
                )
            )

    def _validate_virtual_environment(self) -> None:
        """Validate virtual environment setup."""
        venv_path = self.project_root / "venv"
        if venv_path.exists():
            self.results.append(
                ValidationResult(
                    name="Virtual Environment",
                    status=ValidationStatus.PASS,
                    message="Virtual environment exists",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    name="Virtual Environment",
                    status=ValidationStatus.WARN,
                    message="Virtual environment not found",
                    details="Consider creating a virtual environment for isolation",
                    fix_command="python -m venv venv && source venv/bin/activate",
                )
            )

    def _validate_editor_config(self) -> None:
        """Validate .editorconfig file."""
        editorconfig_path = self.project_root / ".editorconfig"
        if editorconfig_path.exists():
            try:
                content = editorconfig_path.read_text()
                if "indent_style = space" in content and "indent_size = 4" in content:
                    self.results.append(
                        ValidationResult(
                            name="EditorConfig",
                            status=ValidationStatus.PASS,
                            message="EditorConfig properly configured for Python",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            name="EditorConfig",
                            status=ValidationStatus.WARN,
                            message="EditorConfig exists but may not be optimally configured",
                            details="Check that Python files use spaces and 4-space indentation",
                        )
                    )
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        name="EditorConfig",
                        status=ValidationStatus.FAIL,
                        message=f"Failed to read EditorConfig: {e}",
                    )
                )
        else:
            self.results.append(
                ValidationResult(
                    name="EditorConfig",
                    status=ValidationStatus.FAIL,
                    message="EditorConfig file not found",
                    details="This file ensures consistent editor behavior across IDEs",
                    fix_command="Create .editorconfig file with Python-specific settings",
                )
            )

    def _validate_vscode_config(self) -> None:
        """Validate VS Code configuration."""
        vscode_dir = self.project_root / ".vscode"
        if vscode_dir.exists():
            settings_path = vscode_dir / "settings.json"
            if settings_path.exists():
                try:
                    with open(settings_path) as f:
                        settings = json.load(f)

                    # Check critical Python settings
                    python_settings = settings.get("[python]", {})
                    if (
                        python_settings.get("editor.insertSpaces") == True
                        and python_settings.get("editor.tabSize") == 4
                    ):
                        self.results.append(
                            ValidationResult(
                                name="VS Code Python Settings",
                                status=ValidationStatus.PASS,
                                message="VS Code properly configured for Python development",
                            )
                        )
                    else:
                        self.results.append(
                            ValidationResult(
                                name="VS Code Python Settings",
                                status=ValidationStatus.WARN,
                                message="VS Code settings may not be optimally configured",
                                details="Ensure Python files use spaces and 4-space indentation",
                            )
                        )
                except Exception as e:
                    self.results.append(
                        ValidationResult(
                            name="VS Code Python Settings",
                            status=ValidationStatus.FAIL,
                            message=f"Failed to read VS Code settings: {e}",
                        )
                    )
            else:
                self.results.append(
                    ValidationResult(
                        name="VS Code Python Settings",
                        status=ValidationStatus.WARN,
                        message="VS Code settings.json not found",
                        details="Consider creating workspace-specific settings",
                    )
                )
        else:
            self.results.append(
                ValidationResult(
                    name="VS Code Configuration",
                    status=ValidationStatus.WARN,
                    message="VS Code configuration directory not found",
                    details="This is optional but recommended for consistent development",
                )
            )

    def _validate_pre_commit_config(self) -> None:
        """Validate pre-commit configuration."""
        precommit_path = self.project_root / ".pre-commit-config.yaml"
        if precommit_path.exists():
            try:
                content = precommit_path.read_text()
                if "ruff" in content and "black" in content:
                    self.results.append(
                        ValidationResult(
                            name="Pre-commit Configuration",
                            status=ValidationStatus.PASS,
                            message="Pre-commit hooks properly configured",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            name="Pre-commit Configuration",
                            status=ValidationStatus.WARN,
                            message="Pre-commit config exists but may be missing key tools",
                            details="Ensure ruff and black are configured",
                        )
                    )
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        name="Pre-commit Configuration",
                        status=ValidationStatus.FAIL,
                        message=f"Failed to read pre-commit config: {e}",
                    )
                )
        else:
            self.results.append(
                ValidationResult(
                    name="Pre-commit Configuration",
                    status=ValidationStatus.WARN,
                    message="Pre-commit configuration not found",
                    details="This provides automated quality gates",
                    fix_command="Create .pre-commit-config.yaml file",
                )
            )

    def _validate_python_tools(self) -> None:
        """Validate Python development tools."""
        tools = [
            ("ruff", "Ruff linter and formatter"),
            ("black", "Black code formatter"),
            ("mypy", "MyPy type checker"),
            ("pytest", "Pytest testing framework"),
            ("bandit", "Bandit security scanner"),
        ]

        for tool, description in tools:
            try:
                result = subprocess.run(
                    [tool, "--version"], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    self.results.append(
                        ValidationResult(
                            name=f"{tool.title()} Tool",
                            status=ValidationStatus.PASS,
                            message=f"{description} is installed and working",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            name=f"{tool.title()} Tool",
                            status=ValidationStatus.FAIL,
                            message=f"{description} is not working properly",
                            details=f"Exit code: {result.returncode}",
                            fix_command=f"pip install {tool}",
                        )
                    )
            except FileNotFoundError:
                self.results.append(
                    ValidationResult(
                        name=f"{tool.title()} Tool",
                        status=ValidationStatus.FAIL,
                        message=f"{description} is not installed",
                        fix_command=f"pip install {tool}",
                    )
                )
            except subprocess.TimeoutExpired:
                self.results.append(
                    ValidationResult(
                        name=f"{tool.title()} Tool",
                        status=ValidationStatus.WARN,
                        message=f"{description} check timed out",
                        details="Tool may be installed but slow to respond",
                    )
                )
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        name=f"{tool.title()} Tool",
                        status=ValidationStatus.FAIL,
                        message=f"Failed to check {description}: {e}",
                    )
                )

    def _validate_indentation_settings(self) -> None:
        """Validate indentation settings in Python files."""
        python_files = list(self.project_root.glob("src/**/*.py"))
        if not python_files:
            self.results.append(
                ValidationResult(
                    name="Python File Indentation",
                    status=ValidationStatus.SKIP,
                    message="No Python files found in src/ directory",
                )
            )
            return

        # Check a sample of Python files for indentation issues
        sample_files = python_files[:5]  # Check first 5 files
        indentation_issues = 0

        for file_path in sample_files:
            try:
                content = file_path.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # Check for mixed tabs and spaces
                    if "\t" in line and "    " in line:
                        indentation_issues += 1
                        break

                    # Check for incorrect indentation levels
                    if line.strip() and line.startswith(" "):
                        # Count leading spaces
                        leading_spaces = len(line) - len(line.lstrip())
                        if leading_spaces % 4 != 0:
                            indentation_issues += 1
                            break

            except Exception as e:
                self.results.append(
                    ValidationResult(
                        name="Python File Indentation",
                        status=ValidationStatus.WARN,
                        message=f"Could not check {file_path.name}: {e}",
                    )
                )
                continue

        if indentation_issues == 0:
            self.results.append(
                ValidationResult(
                    name="Python File Indentation",
                    status=ValidationStatus.PASS,
                    message="No indentation issues detected in sample files",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    name="Python File Indentation",
                    status=ValidationStatus.WARN,
                    message=f"Potential indentation issues detected in {indentation_issues} files",
                    details="Check for mixed tabs/spaces or incorrect indentation levels",
                    fix_command="Run 'ruff format' to fix formatting issues",
                )
            )

    def _validate_file_permissions(self) -> None:
        """Validate file permissions and ownership."""
        try:
            # Check if we can write to the project directory
            test_file = self.project_root / ".env_validation_test"
            test_file.write_text("test")
            test_file.unlink()

            self.results.append(
                ValidationResult(
                    name="File Permissions",
                    status=ValidationStatus.PASS,
                    message="Project directory is writable",
                )
            )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="File Permissions",
                    status=ValidationStatus.FAIL,
                    message=f"Cannot write to project directory: {e}",
                    fix_command="Check directory permissions and ownership",
                )
            )

    def _display_results(self) -> None:
        """Display validation results."""
        print("\n📊 Validation Results:")
        print("-" * 40)

        for result in self.results:
            status_icon = {
                ValidationStatus.PASS: "✅",
                ValidationStatus.FAIL: "❌",
                ValidationStatus.WARN: "⚠️",
                ValidationStatus.SKIP: "⏭️",
            }[result.status]

            print(f"{status_icon} {result.name}: {result.message}")

            if result.details:
                print(f"   📝 {result.details}")

            if result.fix_command:
                print(f"   🔧 Fix: {result.fix_command}")

        # Summary
        passed = len([r for r in self.results if r.status == ValidationStatus.PASS])
        failed = len([r for r in self.results if r.status == ValidationStatus.FAIL])
        warned = len([r for r in self.results if r.status == ValidationStatus.WARN])
        skipped = len([r for r in self.results if r.status == ValidationStatus.SKIP])

        print(
            f"\n📈 Summary: {passed} passed, {failed} failed, {warned} warnings, {skipped} skipped"
        )

        if failed > 0:
            print(
                "\n🚨 Critical issues found! Please address the failed checks before proceeding."
            )
        elif warned > 0:
            print(
                "\n⚠️  Warnings found. Consider addressing these for optimal development experience."
            )
        else:
            print(
                "\n🎉 All critical checks passed! Your development environment is properly configured."
            )


def main():
    """Main entry point."""
    project_root = Path(__file__).parent
    validator = DevelopmentEnvironmentValidator(project_root)

    success = validator.validate_all()

    if not success:
        print("\n💡 Next Steps:")
        print("1. Address all FAILED checks")
        print("2. Consider addressing WARNINGS for better development experience")
        print("3. Re-run this script to verify fixes")
        sys.exit(1)
    else:
        print("\n✨ Development environment validation completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
