#!/usr/bin/env python3
"""
Environment Consistency Validation Script
Validates that local development environment matches CI/CD requirements
"""

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class EnvironmentValidator:
    """Validates environment consistency between local and CI environments."""

    def __init__(self) -> None:
        self.required_python_version = "3.12.8"
        self.required_poetry_version = "1.8.3"
        self.required_node_version = "22.18.0"
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_python_version(self) -> bool:
        """Validate Python version matches CI requirements."""
        try:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

            if python_version != self.required_python_version:
                self.errors.append(
                    f"Python version mismatch: Expected {self.required_python_version}, "
                    f"found {python_version}"
                )
                return False

            print(f"✅ Python version: {python_version}")
            return True

        except Exception as e:
            self.errors.append(f"Failed to check Python version: {e}")
            return False

    def validate_poetry_version(self) -> bool:
        """Validate Poetry version matches CI requirements."""
        try:
            result = subprocess.run(
                ["poetry", "--version"], capture_output=True, text=True, check=True
            )

            # Extract version from output like "Poetry (version 1.8.3)"
            version_line = result.stdout.strip()
            if self.required_poetry_version in version_line:
                print(f"✅ Poetry version: {version_line}")
                return True
            self.errors.append(
                f"Poetry version mismatch: Expected {self.required_poetry_version}, "
                f"found {version_line}"
            )
            return False

        except subprocess.CalledProcessError:
            self.errors.append("Poetry not found or not working properly")
            return False
        except FileNotFoundError:
            self.errors.append("Poetry not installed")
            return False

    def validate_node_version(self) -> bool:
        """Validate Node.js version matches CI requirements."""
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, check=True
            )

            node_version = result.stdout.strip().lstrip("v")

            if node_version.startswith(self.required_node_version.split(".")[0]):
                print(f"✅ Node.js version: v{node_version}")
                return True
            self.warnings.append(
                f"Node.js version mismatch: Expected {self.required_node_version}, "
                f"found {node_version}"
            )
            return False

        except subprocess.CalledProcessError:
            self.warnings.append("Node.js not found or not working properly")
            return False
        except FileNotFoundError:
            self.warnings.append("Node.js not installed")
            return False

    def validate_poetry_lock_exists(self) -> bool:
        """Validate poetry.lock file exists and is up to date."""
        lock_file = Path("poetry.lock")

        if not lock_file.exists():
            self.errors.append("poetry.lock file not found")
            return False

        # Check if lock file is newer than pyproject.toml
        pyproject_file = Path("pyproject.toml")
        if pyproject_file.exists():
            if lock_file.stat().st_mtime < pyproject_file.stat().st_mtime:
                self.warnings.append(
                    "poetry.lock is older than pyproject.toml - run 'poetry lock' to update"
                )

        print("✅ poetry.lock file exists")
        return True

    def validate_dependencies_installed(self) -> bool:
        """Validate that dependencies are properly installed."""
        try:
            result = subprocess.run(
                ["poetry", "check"], capture_output=True, text=True, check=True
            )
            print("✅ Poetry dependencies validated")
            return True

        except subprocess.CalledProcessError as e:
            self.errors.append(f"Poetry dependency check failed: {e.stderr}")
            return False
        except FileNotFoundError:
            self.errors.append("Poetry not available for dependency check")
            return False

    def validate_docker_consistency(self) -> bool:
        """Validate Docker configuration consistency."""
        dockerfile_prod = Path("Dockerfile.production")
        dockerfile_bridge = Path("Dockerfile.bridge.production")

        if not dockerfile_prod.exists():
            self.errors.append("Dockerfile.production not found")
            return False

        if not dockerfile_bridge.exists():
            self.warnings.append("Dockerfile.bridge.production not found")

        # Check Python version in Dockerfile
        try:
            with open(dockerfile_prod) as f:
                content = f.read()
                if f"python:{self.required_python_version}" not in content:
                    self.errors.append(
                        f"Dockerfile.production doesn't use Python {self.required_python_version}"
                    )
                    return False
        except Exception as e:
            self.errors.append(f"Failed to read Dockerfile.production: {e}")
            return False

        print("✅ Docker configuration validated")
        return True

    def validate_ci_workflow(self) -> bool:
        """Validate CI workflow configuration."""
        ci_file = Path(".github/workflows/ci.yml")

        if not ci_file.exists():
            self.errors.append("CI workflow file not found")
            return False

        try:
            with open(ci_file) as f:
                content = f.read()
                if (
                    f"python-version: '{self.required_python_version.split('.')[0]}.{self.required_python_version.split('.')[1]}'"
                    not in content
                ):
                    self.errors.append(
                        f"CI workflow doesn't specify Python {self.required_python_version.split('.')[0]}.{self.required_python_version.split('.')[1]}"
                    )
                    return False
        except Exception as e:
            self.errors.append(f"Failed to read CI workflow: {e}")
            return False

        print("✅ CI workflow validated")
        return True

    def generate_report(self) -> dict:
        """Generate validation report."""
        return {
            "python_version": self.required_python_version,
            "poetry_version": self.required_poetry_version,
            "node_version": self.required_node_version,
            "platform": platform.platform(),
            "errors": self.errors,
            "warnings": self.warnings,
            "success": len(self.errors) == 0,
        }

    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating environment consistency...")
        print("=" * 50)

        checks = [
            self.validate_python_version,
            self.validate_poetry_version,
            self.validate_node_version,
            self.validate_poetry_lock_exists,
            self.validate_dependencies_installed,
            self.validate_docker_consistency,
            self.validate_ci_workflow,
        ]

        all_passed = True
        for check in checks:
            if not check():
                all_passed = False

        print("=" * 50)

        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")

        if all_passed and not self.errors:
            print("✅ All validations passed! Environment is consistent with CI.")
        else:
            print("❌ Environment validation failed.")

        return all_passed


def main(self) -> None:
    """Main entry point."""
    validator = EnvironmentValidator()
    success = validator.run_validation()

    # Generate JSON report
    report = validator.generate_report()
    with open("environment_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📄 Report saved to: environment_validation_report.json")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
