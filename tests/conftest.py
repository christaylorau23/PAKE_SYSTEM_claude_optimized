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
def test_data_dir(self) -> None:
    """Get test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def mock_env_vars(self) -> None:
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
async def test_database(self) -> None:
    """
    Create a test database for the module.

    This fixture sets up a clean test database before tests run
    and tears it down after all tests in the module complete.
    """
    # TODO: Implement actual database creation/teardown
    # For now, this is a placeholder
    return {
        "host": "localhost",
        "port": 5432,
        "database": "pake_test",
        "user": "test_user",
        "password": "test_password",
    }
    # Cleanup happens here


@pytest.fixture(scope="module")
async def test_redis(self) -> None:
    """
    Create a test Redis connection for the module.

    Uses a separate Redis database (typically db=1) for testing.
    """
    # TODO: Implement actual Redis connection
    return {
        "host": "localhost",
        "port": 6379,
        "db": 1,
    }
    # Cleanup happens here


# ============================================================================
# Function-Scoped Fixtures (fresh for each test)
# ============================================================================


@pytest.fixture
def test_client(self) -> None:
    """
    FastAPI test client for E2E tests.

    Creates a fresh test client for each test function.
    """
    from src.pake_system.auth.example_app import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client(self) -> None:
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


@pytest.fixture
def test_user(self) -> None:
    """Create a test user using factory."""
    return UserInDBFactory()


@pytest.fixture
def test_admin_user(self) -> None:
    """Create an admin test user using factory."""
    return UserInDBFactory(username="admin", role="admin")


@pytest.fixture
def test_disabled_user(self) -> None:
    """Create a disabled test user using factory."""
    return UserInDBFactory(disabled=True)


@pytest.fixture
def test_users(self) -> None:
    """Create multiple test users using factory."""
    return [UserInDBFactory() for _ in range(count)]


@pytest.fixture
def test_search_query(self) -> None:
    """Create a test search query using factory."""
    return SearchQueryFactory()


@pytest.fixture
def test_search_results(self) -> None:
    """Create test search results using factory."""
    return [SearchResultFactory() for _ in range(count)]


@pytest.fixture
def test_login_request(self) -> None:
    """Create a test login request using factory."""
    return LoginRequestFactory()


# ============================================================================
# Mock Fixtures (for unit tests)
# ============================================================================


@pytest.fixture
def mock_database(self) -> None:
    """Mock database service for unit tests."""
    mock_db = AsyncMock()

    # Configure common database operations
    mock_db.execute_query = AsyncMock(return_value=None)
    mock_db.fetch_one = AsyncMock(return_value=None)
    mock_db.fetch_all = AsyncMock(return_value=[])
    mock_db.health_check = AsyncMock(return_value={"status": "healthy"})

    return mock_db


@pytest.fixture
def mock_redis(self) -> None:
    """Mock Redis service for unit tests."""
    mock_redis = MagicMock()

    # Configure common Redis operations
    mock_redis.get = MagicMock(return_value=None)
    mock_redis.set = MagicMock(return_value=True)
    mock_redis.delete = MagicMock(return_value=1)
    mock_redis.exists = MagicMock(return_value=False)

    return mock_redis


@pytest.fixture
def mock_user_repository(self) -> None:
    """Mock user repository for unit tests."""
    mock_repo = AsyncMock()

    # Configure common repository operations
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.get_by_username = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(return_value={"id": "test-user-id"})
    mock_repo.update = AsyncMock(return_value=True)
    mock_repo.delete = AsyncMock(return_value=True)

    return mock_repo


@pytest.fixture
def mock_auth_service(self) -> None:
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


@pytest.fixture
def mock_external_api(self) -> None:
    """Mock external API client for unit tests."""
    mock_api = AsyncMock()

    # Configure API operations
    mock_api.get = AsyncMock(return_value={"status": "ok", "data": []})
    mock_api.post = AsyncMock(return_value={"status": "ok"})

    return mock_api


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def mock_datetime(self) -> None:
    """Mock datetime for testing time-sensitive functionality."""
    from datetime import datetime

    fixed_time = datetime(2025, 1, 30, 12, 0, 0, tzinfo=UTC)
    mock_now = mocker.patch("datetime.datetime")
    mock_now.now.return_value = fixed_time
    mock_now.utcnow.return_value = fixed_time

    return fixed_time


@pytest.fixture(autouse=True)
def reset_singletons(self) -> None:
    """
    Auto-use fixture to reset singleton instances between tests.

    Prevents test pollution when testing singleton patterns.
    """
    return
    # Reset singleton instances here if needed


@pytest.fixture
def capture_logs(self) -> None:
    """
    Enhanced log capturing with helper methods.

    Usage:
        def test_something(self) -> None:
            # Test code
            assert capture_logs.has_error("Error message")
    """

    class LogCapture:
        def __init__(self) -> None:
            self.caplog = caplog

        def has_error(self) -> None:
            return any(
                message in record.message
                for record in self.caplog.records
                if record.levelname == "ERROR"
            )

        def has_warning(self) -> None:
            return any(
                message in record.message
                for record in self.caplog.records
                if record.levelname == "WARNING"
            )

        def has_info(self) -> None:
            return any(
                message in record.message
                for record in self.caplog.records
                if record.levelname == "INFO"
            )

    return LogCapture(caplog)


@pytest.fixture
def test_logger(self) -> None:
    """
    Enhanced test logger with structured logging and context.

    Usage:
        def test_something(self) -> None:
            test_logger.info("Test started")
            # Test code
            test_logger.log_performance("operation", 0.05)
    """
    try:
        from src.services.logging.enhanced_test_logging import get_test_logging_service

        service = get_test_logging_service()
        test_name = request.node.name

        # Use test context for automatic logging
        return service.test_context(test_name, "unit")

    except ImportError:
        # Fallback to basic logging if enhanced service not available
        import logging

        return logging.getLogger(f"test.{request.node.name}")


@pytest.fixture
def structured_logger(self) -> None:
    """
    Structured logger for comprehensive test logging.

    Usage:
        def test_something(self) -> None:
            structured_logger.info("Test event", test_data="value")
            structured_logger.log_database("SELECT", "users", 0.05)
    """
    try:
        from src.services.logging.enhanced_test_logging import get_test_logging_service

        service = get_test_logging_service()
        return service.get_test_logger("structured_test")

    except ImportError:
        # Fallback to basic structured logging
        import structlog

        return structlog.get_logger("test.structured")


# ============================================================================
# Pytest Hooks
# ============================================================================


def pytest_configure(self) -> None:
    """Configure pytest with custom markers and settings."""
    # Setup enhanced test logging
    try:
        from src.services.logging.enhanced_test_logging import (
            TestLoggingConfig,
            setup_test_logging,
        )

        # Configure test logging based on pytest options
        log_config = TestLoggingConfig(
            enabled=True,
            level="DEBUG",
            format_type="structured",
            console_output=True,
            file_output=True,
            capture_application_logs=True,
            capture_performance_metrics=True,
            show_test_boundaries=True,
            integrate_with_pytest=True,
        )

        setup_test_logging(log_config)

    except ImportError:
        # Fallback if enhanced logging not available
        pass


def pytest_runtest_setup(self) -> None:
    """Setup before each test runs."""
    try:
        from src.services.logging.enhanced_test_logging import get_test_logging_service

        service = get_test_logging_service()
        test_name = item.name

        # Log test start
        logger = service.get_test_logger(test_name)
        logger.info("Setting up test: %s", test_name)

    except ImportError:
        pass


def pytest_runtest_teardown(self) -> None:
    """Teardown after each test runs."""
    try:
        from src.services.logging.enhanced_test_logging import get_test_logging_service

        service = get_test_logging_service()
        test_name = item.name

        # Log test completion
        logger = service.get_test_logger(test_name)
        logger.info("Tearing down test: %s", test_name)

    except ImportError:
        pass


def pytest_sessionfinish(self) -> None:
    """Called after whole test run finished."""
    try:
        from src.services.logging.enhanced_test_logging import get_test_logging_service

        service = get_test_logging_service()
        summary = service.get_test_summary()

        # Log test session summary
        logger = service.get_test_logger("session")
        logger.info(
            "Test session completed",
            total_tests=summary["total_tests"],
            slow_tests=len(summary["slow_tests"]),
            failed_tests=len(summary["failed_tests"]),
            exit_status=exitstatus,
        )

        # Log slow tests if any
        if summary["slow_tests"]:
            logger.warning("Slow tests detected", slow_tests=summary["slow_tests"])

    except ImportError:
        pass
    # Markers are already defined in pyproject.toml


def pytest_collection_modifyitems(self) -> None:
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests in specific directories
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
