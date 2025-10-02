#!/usr/bin/env python3
"""
Vault Integration Test Script
==============================

Tests the PAKE System configuration with Vault integration.
This script verifies that secrets can be loaded from both Vault
and environment variables.

Usage:
    poetry run python scripts/test_vault_integration.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_vault_integration():
    """Test configuration loading from Vault."""
    print("\n" + "=" * 60)
    print("Test 1: Loading Configuration from Vault")
    print("=" * 60 + "\n")

    # Set environment for Vault integration
    os.environ["ENVIRONMENT"] = "test"
    os.environ["USE_VAULT"] = "true"
    os.environ["VAULT_URL"] = "http://127.0.0.1:8200"
    os.environ["VAULT_TOKEN"] = "dev-only-token"

    # Clear any existing secrets to force Vault loading
    os.environ.pop("SECRET_KEY", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("REDIS_URL", None)

    try:
        from pake_system.core.config import get_settings

        settings = get_settings()

        # Verify secrets were loaded
        assert settings.SECRET_KEY, "SECRET_KEY should be loaded from Vault"
        assert settings.DATABASE_URL, "DATABASE_URL should be loaded from Vault"
        assert settings.REDIS_URL, "REDIS_URL should be loaded from Vault"

        print("✅ Successfully loaded secrets from Vault:")
        print(f"   - SECRET_KEY: {'*' * 20} (hidden)")
        print(f"   - DATABASE_URL: {settings.DATABASE_URL}")
        print(f"   - REDIS_URL: {settings.REDIS_URL}")
        print(f"   - Environment: {settings.ENVIRONMENT}")

        return True

    except Exception as e:
        print(f"❌ Failed to load configuration from Vault: {e}")
        return False


def test_environment_fallback():
    """Test configuration loading from environment variables."""
    print("\n" + "=" * 60)
    print("Test 2: Loading Configuration from Environment Variables")
    print("=" * 60 + "\n")

    # Clear cache to force reload
    from pake_system.core.config import get_settings

    get_settings.cache_clear()

    # Disable Vault and set environment variables
    os.environ["USE_VAULT"] = "false"
    os.environ["SECRET_KEY"] = "test-env-secret-key"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test_db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"

    try:
        settings = get_settings()

        # Verify secrets were loaded from environment
        assert (
            settings.SECRET_KEY == "test-env-secret-key"
        ), "SECRET_KEY should match environment"
        assert (
            settings.DATABASE_URL == "postgresql://test:test@localhost/test_db"
        ), "DATABASE_URL should match environment"
        assert (
            settings.REDIS_URL == "redis://localhost:6379/1"
        ), "REDIS_URL should match environment"

        print("✅ Successfully loaded secrets from environment variables:")
        print(f"   - SECRET_KEY: {settings.SECRET_KEY}")
        print(f"   - DATABASE_URL: {settings.DATABASE_URL}")
        print(f"   - REDIS_URL: {settings.REDIS_URL}")

        return True

    except Exception as e:
        print(f"❌ Failed to load configuration from environment: {e}")
        return False


def test_vault_priority():
    """Test that environment variables override Vault values."""
    print("\n" + "=" * 60)
    print("Test 3: Environment Variable Override (Priority Test)")
    print("=" * 60 + "\n")

    # Clear cache
    from pake_system.core.config import get_settings

    get_settings.cache_clear()

    # Enable Vault but also set environment variables
    os.environ["USE_VAULT"] = "true"
    os.environ["VAULT_URL"] = "http://127.0.0.1:8200"
    os.environ["VAULT_TOKEN"] = "dev-only-token"
    os.environ["SECRET_KEY"] = "env-override-secret"
    os.environ["DATABASE_URL"] = "postgresql://override:override@localhost/override_db"

    try:
        settings = get_settings()

        # Environment variables should take precedence
        assert (
            settings.SECRET_KEY == "env-override-secret"
        ), "Env var should override Vault"
        assert (
            settings.DATABASE_URL and "override" in settings.DATABASE_URL
        ), "Env var should override Vault"

        print("✅ Environment variables correctly override Vault values:")
        print(f"   - SECRET_KEY: {settings.SECRET_KEY}")
        print(f"   - DATABASE_URL: {settings.DATABASE_URL}")

        return True

    except Exception as e:
        print(f"❌ Priority test failed: {e}")
        return False


def test_vault_client_health():
    """Test Vault client health check."""
    print("\n" + "=" * 60)
    print("Test 4: Vault Client Health Check")
    print("=" * 60 + "\n")

    try:
        from pake_system.core.vault_client import get_vault_client

        vault_client = get_vault_client()
        health = vault_client.health_check()

        print("✅ Vault Health Status:")
        for key, value in health.items():
            print(f"   - {key}: {value}")

        return health.get("status") == "healthy"

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("PAKE System - Vault Integration Test Suite")
    print("=" * 70)

    results = []

    # Test 1: Vault integration
    results.append(("Vault Integration", test_vault_integration()))

    # Test 2: Environment fallback
    results.append(("Environment Fallback", test_environment_fallback()))

    # Test 3: Priority test
    results.append(("Priority Override", test_vault_priority()))

    # Test 4: Health check
    results.append(("Vault Health Check", test_vault_client_health()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70 + "\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")
    print("=" * 70 + "\n")

    if passed == total:
        print("🎉 All tests passed! Vault integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
