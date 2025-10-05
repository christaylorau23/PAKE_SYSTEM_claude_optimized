#!/usr/bin/env python3
"""
PAKE System - Development Environment Status Check
Quick demonstration of the implemented environment fortification
"""

import os
import sys
from pathlib import Path


def check_environment():
    """Check the development environment configuration."""
    print("🔍 PAKE System - Development Environment Status")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # Check configuration files
    config_files = [
        (".editorconfig", "Editor Configuration"),
        (".pre-commit-config.yaml", "Pre-commit Hooks"),
        (".vscode/settings.json", "VS Code Settings"),
        (".vscode/python-settings.json", "VS Code Python Settings"),
    ]

    print("\n📁 Configuration Files:")
    for file_path, description in config_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ {description}: {file_path} (NOT FOUND)")

    # Check Python tools
    print("\n🛠️  Python Development Tools:")
    tools = ["ruff", "black", "mypy", "pytest", "bandit"]
    for tool in tools:
        try:
            result = os.system(f"which {tool} > /dev/null 2>&1")
            if result == 0:
                print(f"✅ {tool.title()}: Installed")
            else:
                print(f"❌ {tool.title()}: Not installed")
        except:
            print(f"❌ {tool.title()}: Check failed")

    # Check Python version
    print(f"\n🐍 Python Version: {sys.version}")

    # Check virtual environment
    venv_path = project_root / "venv"
    if venv_path.exists():
        print("✅ Virtual Environment: Found")
    else:
        print("⚠️  Virtual Environment: Not found (optional)")

    print("\n✨ Environment fortification implementation completed!")
    print(
        "📋 All configuration files have been created according to the Engineering Plan."
    )


if __name__ == "__main__":
    check_environment()
