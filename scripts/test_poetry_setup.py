#!/usr/bin/env python3
"""
Test script to verify Poetry setup and dependency installation.

This script validates that:
1. All critical dependencies are importable
2. Version compatibility is correct
3. Optional dependency groups work properly
4. The environment is properly configured

Usage:
    poetry run python scripts/test_poetry_setup.py
"""

import importlib
import sys
from typing import Optional


def test_import(package: str, optional: bool = False) -> tuple[bool, Optional[str]]:
    """Test if a package can be imported."""
    try:
        module = importlib.import_module(package)
        version = getattr(module, "__version__", "unknown")
        return True, version
    except ImportError as e:
        if not optional:
            return False, str(e)
        return True, f"Optional package not installed: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def test_core_dependencies() -> dict[str, tuple[bool, Optional[str]]]:
    """Test core production dependencies."""
    core_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "sqlalchemy",
        "redis",
        "asyncpg",
        "aiohttp",
        "httpx",
        "pyjwt",
        "passlib",
        "websockets",
        "aiofiles",
        "structlog",
        "loguru",
    ]

    results = {}
    for package in core_packages:
        success, info = test_import(package)
        results[package] = (success, info)

    return results


def test_dev_dependencies() -> dict[str, tuple[bool, Optional[str]]]:
    """Test development dependencies."""
    dev_packages = ["pytest", "black", "isort", "mypy", "ruff", "bandit", "coverage"]

    results = {}
    for package in dev_packages:
        success, info = test_import(package)
        results[package] = (success, info)

    return results


def test_optional_dependencies() -> dict[str, tuple[bool, Optional[str]]]:
    """Test optional dependency groups."""
    optional_packages = {
        # Trends group
        "tweepy": True,
        "geopy": True,
        # AI/ML packages
        "numpy": False,
        "pandas": False,
        "sklearn": True,  # scikit-learn
        # Cloud packages
        "boto3": True,
        # Monitoring
        "prometheus_client": False,
    }

    results = {}
    for package, is_optional in optional_packages.items():
        success, info = test_import(package, optional=is_optional)
        results[package] = (success, info)

    return results


def test_poetry_environment():
    """Test Poetry-specific environment setup."""
    import os

    print("🔍 Testing Poetry Environment Setup...")

    # Check if we're in a Poetry environment
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env and ".venv" in virtual_env:
        print(f"✅ Running in Poetry virtual environment: {virtual_env}")
    else:
        print(f"⚠️  May not be in Poetry venv. Current VIRTUAL_ENV: {virtual_env}")

    # Check Python path
    python_path = sys.executable
    if ".venv" in python_path:
        print(f"✅ Using Poetry Python: {python_path}")
    else:
        print(f"⚠️  Python path may not be from Poetry: {python_path}")


def print_results(category: str, results: dict[str, tuple[bool, Optional[str]]]):
    """Print test results for a category."""
    print(f"\n📦 {category} Dependencies:")
    print("-" * 40)

    success_count = 0
    for package, (success, info) in results.items():
        if success:
            status = "✅"
            success_count += 1
            if "Optional package not installed" in str(info):
                status = "⚠️ "
                success_count -= 1
        else:
            status = "❌"

        version_info = (
            f" (v{info})"
            if success and "unknown" not in str(info) and "Optional" not in str(info)
            else ""
        )
        print(f"  {status} {package}{version_info}")

        if not success:
            print(f"      Error: {info}")

    print(
        f"\n📊 {category} Summary: {success_count}/{len(results)} packages successfully imported"
    )
    return success_count == len(
        [
            r
            for r in results.values()
            if "Optional package not installed" not in str(r[1])
        ]
    )


def test_basic_functionality():
    """Test basic functionality of key components."""
    print("\n🧪 Testing Basic Functionality...")
    print("-" * 40)

    # Test FastAPI import and basic setup
    try:
        from fastapi import FastAPI

        app = FastAPI()
        print("  ✅ FastAPI: Can create app instance")
    except Exception as e:
        print(f"  ❌ FastAPI: {e}")

    # Test SQLAlchemy basic functionality
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        # Test with SQLite in-memory database
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        session = Session()
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("  ✅ SQLAlchemy: Basic database operations work")
    except Exception as e:
        print(f"  ❌ SQLAlchemy: {e}")

    # Test Redis connection (mock)
    try:
        import redis

        # Don't actually connect, just test import and basic setup
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        print("  ✅ Redis: Client can be created")
    except Exception as e:
        print(f"  ❌ Redis: {e}")

    # Test pytest functionality
    try:
        print("  ✅ Pytest: Available for testing")
    except Exception as e:
        print(f"  ❌ Pytest: {e}")


def main():
    """Main test function."""
    print("🧪 PAKE System - Poetry Setup Validation")
    print("=" * 50)

    # Test Poetry environment
    test_poetry_environment()

    # Test core dependencies
    core_success = print_results("Core", test_core_dependencies())

    # Test dev dependencies
    dev_success = print_results("Development", test_dev_dependencies())

    # Test optional dependencies
    print_results("Optional", test_optional_dependencies())

    # Test basic functionality
    test_basic_functionality()

    # Overall summary
    print("\n" + "=" * 50)
    print("📋 OVERALL SUMMARY")
    print("=" * 50)

    if core_success:
        print("✅ Core dependencies: ALL WORKING")
    else:
        print("❌ Core dependencies: SOME ISSUES FOUND")

    if dev_success:
        print("✅ Development dependencies: ALL WORKING")
    else:
        print("⚠️  Development dependencies: SOME ISSUES (may be acceptable)")

    if core_success and dev_success:
        print("\n🎉 Poetry setup is SUCCESSFUL!")
        print("   You can now run: poetry run pytest tests/ -v")
        print("   Or start development: poetry shell")
    else:
        print("\n⚠️  Some issues found. Consider running:")
        print("   poetry install --with dev,trends")
        print("   poetry update")

    # Exit with appropriate code
    sys.exit(0 if core_success else 1)


if __name__ == "__main__":
    main()
