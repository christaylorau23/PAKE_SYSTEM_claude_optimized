"""
Pytest configuration for authentication tests
Provides fixtures and test configuration
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    # Disable Vault for tests to keep them simple and fast
    os.environ["USE_VAULT"] = "false"

    # Set test secrets via environment variables
    # SECURITY: No hardcoded secrets - use environment variables or Vault
    os.environ["SECRET_KEY"] = os.getenv(
        "TEST_SECRET_KEY",
        "test-secret-key-for-testing-only-never-use-in-production-12345678",
    )
    os.environ["DATABASE_URL"] = os.getenv(
        "TEST_DATABASE_URL", "postgresql://test:test@localhost/test_db"
    )
    os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379")
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
    os.environ["ALGORITHM"] = "HS256"

    return

    # Cleanup after tests
