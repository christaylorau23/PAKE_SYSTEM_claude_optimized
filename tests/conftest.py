import asyncio
import os
from pathlib import Path

import pytest

# Set test environment
os.environ["PAKE_ENVIRONMENT"] = "test"
os.environ["PAKE_DEBUG"] = "true"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir():
    """Get test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    return {
        "PAKE_DB_HOST": "localhost",
        "PAKE_DB_PORT": "5432",
        "PAKE_DB_NAME": "pake_test",
        "PAKE_DB_USER": "test_user",
        "PAKE_DB_PASSWORD": "test_REDACTED_SECRET",
        "PAKE_REDIS_URL": "redis://localhost:6379/1",
        "PAKE_JWT_SECRET": "test-secret-key",
        "PAKE_HOST": "127.0.0.1",
        "PAKE_PORT": "8000",
    }
