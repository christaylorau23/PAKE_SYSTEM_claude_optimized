#!/usr/bin/env python3
"""
Migration script to help developers transition from requirements.txt files to Poetry.

This script:
1. Backs up existing requirements files
2. Installs Poetry if not available
3. Sets up the new Poetry environment
4. Validates the installation
5. Provides guidance for next steps

Usage:
    python scripts/migrate_to_poetry.py
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import List, Optional
import platform


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def check_poetry_installed() -> bool:
    """Check if Poetry is installed."""
    try:
        result = run_command(["poetry", "--version"], check=False)
        if result.returncode == 0:
            print(f"✅ Poetry is already installed: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("❌ Poetry is not installed")
    return False


def install_poetry() -> bool:
    """Install Poetry using the official installer."""
    print("🔧 Installing Poetry...")

    # Use the official Poetry installer
    if platform.system() == "Windows":
        installer_cmd = [
            "powershell",
            "-Command",
            "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"
        ]
    else:
        installer_cmd = [
            "curl", "-sSL", "https://install.python-poetry.org", "|", "python3", "-"
        ]
        # For Unix systems, we need to use shell=True
        try:
            subprocess.run(
                "curl -sSL https://install.python-poetry.org | python3 -",
                shell=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Poetry: {e}")
            return False

    # Add Poetry to PATH (for current session)
    home_dir = Path.home()
    poetry_bin = home_dir / ".local" / "bin"
    if poetry_bin.exists():
        os.environ["PATH"] = f"{poetry_bin}:{os.environ.get('PATH', '')}"

    # Verify installation
    return check_poetry_installed()


def backup_requirements_files() -> List[Path]:
    """Backup existing requirements files."""
    print("📦 Backing up existing requirements files...")

    backup_dir = Path("backups/requirements_backup")
    backup_dir.mkdir(parents=True, exist_ok=True)

    requirements_patterns = [
        "requirements*.txt",
        "*/requirements*.txt",
        "**/requirements*.txt"
    ]

    backed_up_files = []

    for pattern in requirements_patterns:
        for req_file in Path(".").glob(pattern):
            if req_file.is_file() and "venv" not in str(req_file):
                backup_path = backup_dir / req_file.name
                shutil.copy2(req_file, backup_path)
                backed_up_files.append(req_file)
                print(f"  📄 Backed up: {req_file} -> {backup_path}")

    print(f"✅ Backed up {len(backed_up_files)} requirements files to {backup_dir}")
    return backed_up_files


def setup_poetry_environment() -> bool:
    """Set up the Poetry environment."""
    print("🏗️  Setting up Poetry environment...")

    try:
        # Configure Poetry to create venv in project directory
        run_command(["poetry", "config", "virtualenvs.in-project", "true"])

        # Install dependencies
        print("📦 Installing dependencies (this may take a few minutes)...")
        run_command(["poetry", "install", "--with", "dev,trends"])

        print("✅ Poetry environment setup complete!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to setup Poetry environment: {e}")
        return False


def validate_installation() -> bool:
    """Validate the Poetry installation."""
    print("🔍 Validating Poetry installation...")

    try:
        # Check if we can run basic commands
        result = run_command(["poetry", "show"])
        if result.returncode == 0:
            print("✅ Poetry can list dependencies")

        # Try to run a simple test
        result = run_command(["poetry", "run", "python", "--version"])
        if result.returncode == 0:
            print(f"✅ Poetry environment Python: {result.stdout.strip()}")

        # Check if we can import key packages
        test_imports = [
            "import fastapi",
            "import sqlalchemy",
            "import redis",
            "import pytest"
        ]

        for test_import in test_imports:
            result = run_command(
                ["poetry", "run", "python", "-c", test_import],
                check=False
            )
            if result.returncode == 0:
                package = test_import.split()[1]
                print(f"✅ Can import {package}")
            else:
                print(f"⚠️  Warning: Cannot import {test_import.split()[1]}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Validation failed: {e}")
        return False


def print_next_steps():
    """Print guidance for next steps."""
    print("\n" + "="*60)
    print("🎉 MIGRATION TO POETRY COMPLETE!")
    print("="*60)

    print("\n📋 NEXT STEPS:")
    print("1. Activate Poetry environment:")
    print("   poetry shell")

    print("\n2. Run tests to verify everything works:")
    print("   poetry run pytest tests/ -v")

    print("\n3. Test the production pipeline:")
    print("   poetry run python scripts/test_production_pipeline.py")

    print("\n4. Update your IDE/editor to use Poetry's virtual environment:")
    print("   - VS Code: Select interpreter from .venv/bin/python")
    print("   - PyCharm: Add Poetry interpreter in settings")

    print("\n5. Team migration commands:")
    print("   # For new team members:")
    print("   git clone <repo>")
    print("   poetry install --with dev,trends")
    print("   poetry shell")

    print("\n📚 POETRY CHEAT SHEET:")
    print("   poetry install                    # Install all dependencies")
    print("   poetry install --only main        # Production only")
    print("   poetry install --with dev,trends  # Include optional groups")
    print("   poetry add package-name           # Add new dependency")
    print("   poetry add --group dev package    # Add to dev group")
    print("   poetry show --tree                # Show dependency tree")
    print("   poetry update                     # Update all dependencies")
    print("   poetry export -f requirements.txt # Export to requirements.txt")

    print("\n🗂️  DEPENDENCY GROUPS AVAILABLE:")
    print("   main: Core production dependencies")
    print("   dev: Development and testing tools")
    print("   trends: Live trend data feed system")
    print("   docs: Documentation generation")
    print("   cloud: Cloud deployment tools")
    print("   monitoring: Advanced monitoring")
    print("   messaging: Message queue systems")
    print("   search: Search engine integration")

    print("\n💡 TIP: Old requirements.txt files are backed up in backups/requirements_backup/")
    print("    You can safely remove them after confirming Poetry works correctly.")


def main():
    """Main migration function."""
    print("🚀 PAKE System - Poetry Migration Script")
    print("="*50)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run this script from the project root.")
        sys.exit(1)

    # Backup existing requirements files
    backed_up_files = backup_requirements_files()

    # Check if Poetry is installed
    if not check_poetry_installed():
        if not install_poetry():
            print("❌ Failed to install Poetry. Please install manually: https://python-poetry.org/docs/#installation")
            sys.exit(1)

    # Setup Poetry environment
    if not setup_poetry_environment():
        print("❌ Failed to setup Poetry environment")
        sys.exit(1)

    # Validate installation
    if not validate_installation():
        print("⚠️  Some validation checks failed, but basic setup is complete")

    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main()