"""
Pytest Configuration and Global Fixtures

This file contains shared fixtures used across all test modules.
Organized by scope and dependency:
- Session-scoped: Event loop, database setup
- Module-scoped: Database connection, Redis connection
- Function-scoped: Test client, mocked services, test data
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set test environment before any imports
os.environ["PAKE_ENVIRONMENT"] = "test"
os.environ["PAKE_DEBUG"] = "true"

# Disable Vault for tests to keep them simple and fast
# Tests should not depend on external Vault service
os.environ["USE_VAULT"] = "false"

# Set test secrets via environment variables
# SECURITY: No hardcoded secrets - use environment variables or Vault
os.environ["SECRET_KEY"] = os.getenv(
    "TEST_SECRET_KEY", "test-secret-key-for-testing-only-never-use-in-production"
)
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://test:test@localhost/pake_test"
)
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

# Import after environment is set
from datetime import UTC

from tests.factories import (
    LoginRequestFactory,
    SearchQueryFactory,
    SearchResultFactory,
    UserInDBFactory,
)

# ============================================================================
# Session-Scoped Fixtures (shared across entire test session)
# ============================================================================

# Note: event_loop fixture is no longer needed with pytest-asyncio>=0.21.0
# The asyncio_mode = auto configuration in pytest.ini handles this automatically

@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def mock_env_vars():
    """Mock environment variables for testing."""
    return {
        "PAKE_DB_HOST": "localhost",
        "PAKE_DB_PORT": "5432",
        "PAKE_DB_NAME": "pake_test",
        "PAKE_DB_USER": "test_user",
        "PAKE_DB_PASSWORD": "test_password",
        "PAKE_REDIS_URL": "redis://localhost:6379/1",
        "PAKE_JWT_SECRET": "test-secret-key",
        "PAKE_HOST": "127.0.0.1",
        "PAKE_PORT": "8000",
    }


# ============================================================================
# Module-Scoped Fixtures (shared within a test module)
# ============================================================================


@pytest.fixture(scope="module")
async def test_database():
    """
    Create a test database for the module.

    This fixture sets up a clean test database before tests run
    and tears it down after all tests in the module complete.
    """
    # TODO: Implement actual database creation/teardown
    # For now, this is a placeholder
    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "pake_test",
        "user": "test_user",
        "password": "test_password",
    }
    return db_config
    # Cleanup happens here


@pytest.fixture(scope="module")
async def test_redis():
    """
    Create a test Redis connection for the module.

    Uses a separate Redis database (typically db=1) for testing.
    """
    # TODO: Implement actual Redis connection
    redis_config = {
        "host": "localhost",
        "port": 6379,
        "db": 1,
    }
    return redis_config
    # Cleanup happens here


# ============================================================================
# Function-Scoped Fixtures (fresh for each test)
# ============================================================================


@pytest.fixture()
def test_client():
    """
    FastAPI test client for E2E tests.

    Creates a fresh test client for each test function.
    """
    from src.pake_system.auth.example_app import app

    with TestClient(app) as client:
        yield client


@pytest.fixture()
def authenticated_client(test_client, test_user):
    """
    Authenticated FastAPI test client.

    Returns a test client with a valid JWT token in headers.
    """
    # Login to get token
    response = test_client.post(
        "/token", data={"username": test_user["username"], "password": "password123"}
    )
    token = response.json()["access_token"]

    # Add token to headers
    test_client.headers = {**test_client.headers, "Authorization": f"Bearer {token}"}

    return test_client


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture()
def test_user():
    """Create a test user using factory."""
    return UserInDBFactory()


@pytest.fixture()
def test_admin_user():
    """Create an admin test user using factory."""
    return UserInDBFactory(username="admin", role="admin")


@pytest.fixture()
def test_disabled_user():
    """Create a disabled test user using factory."""
    return UserInDBFactory(disabled=True)


@pytest.fixture()
def test_users(count=5):
    """Create multiple test users using factory."""
    return [UserInDBFactory() for _ in range(count)]


@pytest.fixture()
def test_search_query():
    """Create a test search query using factory."""
    return SearchQueryFactory()


@pytest.fixture()
def test_search_results(count=10):
    """Create test search results using factory."""
    return [SearchResultFactory() for _ in range(count)]


@pytest.fixture()
def test_login_request():
    """Create a test login request using factory."""
    return LoginRequestFactory()


# ============================================================================
# Mock Fixtures (for unit tests)
# ============================================================================


@pytest.fixture()
def mock_database():
    """Mock database service for unit tests."""
    mock_db = AsyncMock()

    # Configure common database operations
    mock_db.execute_query = AsyncMock(return_value=None)
    mock_db.fetch_one = AsyncMock(return_value=None)
    mock_db.fetch_all = AsyncMock(return_value=[])
    mock_db.health_check = AsyncMock(return_value={"status": "healthy"})

    return mock_db


@pytest.fixture()
def mock_redis():
    """Mock Redis service for unit tests."""
    mock_redis = MagicMock()

    # Configure common Redis operations
    mock_redis.get = MagicMock(return_value=None)
    mock_redis.set = MagicMock(return_value=True)
    mock_redis.delete = MagicMock(return_value=1)
    mock_redis.exists = MagicMock(return_value=False)

    return mock_redis


@pytest.fixture()
def mock_user_repository():
    """Mock user repository for unit tests."""
    mock_repo = AsyncMock()

    # Configure common repository operations
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.get_by_username = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(return_value={"id": "test-user-id"})
    mock_repo.update = AsyncMock(return_value=True)
    mock_repo.delete = AsyncMock(return_value=True)

    return mock_repo


@pytest.fixture()
def mock_auth_service():
    """Mock authentication service for unit tests."""
    mock_auth = AsyncMock()

    # Configure authentication operations
    mock_auth.authenticate_user = AsyncMock(
        return_value={
            "success": True,
            "access_token": "test_token",
            "token_type": "bearer",
        }
    )
    mock_auth.validate_token = AsyncMock(
        return_value={"valid": True, "user_id": "test-user-id"}
    )
    mock_auth.refresh_token = AsyncMock(
        return_value={"success": True, "access_token": "new_test_token"}
    )

    return mock_auth


@pytest.fixture()
def mock_external_api():
    """Mock external API client for unit tests."""
    mock_api = AsyncMock()

    # Configure API operations
    mock_api.get = AsyncMock(return_value={"status": "ok", "data": []})
    mock_api.post = AsyncMock(return_value={"status": "ok"})

    return mock_api


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture()
def mock_datetime(mocker):
    """Mock datetime for testing time-sensitive functionality."""
    from datetime import datetime

    fixed_time = datetime(2025, 1, 30, 12, 0, 0, tzinfo=UTC)
    mock_now = mocker.patch("datetime.datetime")
    mock_now.now.return_value = fixed_time
    mock_now.utcnow.return_value = fixed_time

    return fixed_time


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Auto-use fixture to reset singleton instances between tests.

    Prevents test pollution when testing singleton patterns.
    """
    return
    # Reset singleton instances here if needed


@pytest.fixture()
def capture_logs(caplog):
    """
    Enhanced log capturing with helper methods.

    Usage:
        def test_something(capture_logs):
            # Test code
            assert capture_logs.has_error("Error message")
    """

    class LogCapture:
        def __init__(self, caplog):
            self.caplog = caplog

        def has_error(self, message):
            return any(
                message in record.message
                for record in self.caplog.records
                if record.levelname == "ERROR"
            )

        def has_warning(self, message):
            return any(
                message in record.message
                for record in self.caplog.records
                if record.levelname == "WARNING"
            )

        def has_info(self, message):
            return any(
                message in record.message
                for record in self.caplog.records
                if record.levelname == "INFO"
            )

    return LogCapture(caplog)


# ============================================================================
# Pytest Hooks
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Markers are already defined in pyproject.toml


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests in specific directories
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
