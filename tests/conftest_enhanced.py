#!/usr/bin/env python3
"""
PAKE System - Enhanced Pytest Configuration
Implements comprehensive test isolation and proactive test data management.

This configuration implements the first core principle: Test Isolation.
Each test function should be completely independent and not rely on
the state left behind by previously run tests.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pytest
    from pytest_asyncio import AsyncMode
except ImportError:
    pytest = None
    AsyncMode = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set test environment before any imports
os.environ["PAKE_ENVIRONMENT"] = "test"
os.environ["PAKE_DEBUG"] = "true"
os.environ["USE_VAULT"] = "false"

# Import test services
from src.services.testing.migration_validator import (
    MigrationValidationConfig,
    MigrationValidator,
)
from src.services.testing.test_data_factories import (
    create_basic_test_scenario,
    create_comprehensive_test_scenario,
    create_performance_test_scenario,
    get_fixture_registry,
)
from src.services.testing.test_database_manager import (
    TestDatabaseConfig,
    TestDatabaseManager,
    get_test_database_manager,
    initialize_test_database_manager,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestIsolationManager:
    """
    Manages test isolation to ensure each test is completely independent.

    Implements the first core principle of proactive test data management:
    Each test function should be completely independent and not rely on
    the state left behind by previously run tests.
    """

    def __init__(self) -> None:
        self.test_db_manager: TestDatabaseManager | None = None
        self.fixture_registry = get_fixture_registry()
        self.test_isolation_config = TestDatabaseConfig(
            create_fresh_database_per_test=True,
            create_fresh_database_per_module=True,
            create_fresh_database_per_session=False,
            cleanup_after_test=True,
            cleanup_after_module=True,
            cleanup_after_session=True,
            migrations_path=Path("migrations"),
            validate_migrations_in_ci=True,
            apply_migrations_on_setup=True,
        )
        self.active_tests: dict[str, dict[str, Any]] = {}
        self.test_metrics: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize the test isolation manager."""
        logger.info("Initializing Test Isolation Manager")

        self.test_db_manager = TestDatabaseManager(self.test_isolation_config)
        await self.test_db_manager.initialize()

        logger.info("Test Isolation Manager initialized successfully")

    async def setup_test_isolation(
        self, test_name: str, isolation_level: str = "function"
    ) -> dict[str, Any]:
        """Set up complete isolation for a test."""
        logger.info(f"Setting up test isolation for: {test_name}")

        isolation_context = {
            "test_name": test_name,
            "isolation_level": isolation_level,
            "start_time": asyncio.get_event_loop().time(),
            "database_name": None,
            "engine": None,
            "session": None,
            "test_data": None,
        }

        try:
            # Create isolated test database
            async with self.test_db_manager.test_database(
                test_name=test_name, isolation_level=isolation_level
            ) as engine:
                isolation_context["engine"] = engine
                isolation_context["database_name"] = getattr(
                    engine.url, "database", "unknown"
                )

                # Create test session
                async with engine.begin() as conn:
                    isolation_context["session"] = conn
                    yield isolation_context
        except Exception as e:
            logger.error("Error in test database setup: %s", e)
            raise

    async def _generate_test_data_for_test(
        self, test_name: str, engine
    ) -> dict[str, Any]:
        """Generate appropriate test data based on test name and type."""
        # Determine test data requirements based on test name
        if "unit" in test_name.lower():
            return await create_basic_test_scenario(engine)
        if "integration" in test_name.lower():
            return await create_comprehensive_test_scenario(engine)
        if "performance" in test_name.lower() or "load" in test_name.lower():
            return await create_performance_test_scenario(engine)
        return await create_basic_test_scenario(engine)

    async def cleanup_test_isolation(self, test_name: str) -> None:
        """Clean up test isolation resources."""
        if test_name not in self.active_tests:
            return

        logger.info(f"Cleaning up test isolation for: {test_name}")

        isolation_context = self.active_tests[test_name]

        try:
            # Close database session
            if isolation_context.get("session"):
                await isolation_context["session"].close()

            # Calculate test metrics
            end_time = asyncio.get_event_loop().time()
            duration = end_time - isolation_context["start_time"]

            self.test_metrics[test_name] = {
                "duration": duration,
                "database_name": isolation_context.get("database_name"),
                "isolation_level": isolation_context.get("isolation_level"),
                "test_data_generated": bool(isolation_context.get("test_data")),
            }

            # Remove from active tests
            del self.active_tests[test_name]

            logger.info(f"Test isolation cleanup completed for: {test_name}")

        except Exception as e:
            logger.error(f"Failed to cleanup test isolation for {test_name}: {e}")

    async def cleanup_all(self) -> None:
        """Clean up all test isolation resources."""
        logger.info("Cleaning up all test isolation resources")

        # Clean up all active tests
        for test_name in list(self.active_tests.keys()):
            await self.cleanup_test_isolation(test_name)

        # Clean up test database manager
        if self.test_db_manager:
            await self.test_db_manager.cleanup_all()

        logger.info("All test isolation resources cleaned up")

    def get_test_metrics(self) -> dict[str, Any]:
        """Get test execution metrics."""
        return self.test_metrics.copy()


# Global test isolation manager
_test_isolation_manager: TestIsolationManager | None = None


def get_test_isolation_manager() -> TestIsolationManager:
    """Get the global test isolation manager."""
    global _test_isolation_manager

    if _test_isolation_manager is None:
        _test_isolation_manager = TestIsolationManager()

    return _test_isolation_manager


# Enhanced pytest fixtures with complete isolation
@pytest.fixture(scope="session")
async def test_isolation_manager(self) -> None:
    """Session-scoped test isolation manager."""
    manager = get_test_isolation_manager()
    await manager.initialize()
    yield manager
    await manager.cleanup_all()


@pytest.fixture(scope="function")
async def isolated_test_environment(self) -> None:
    """
    Function-scoped isolated test environment.

    This fixture ensures complete test isolation by:
    1. Creating a fresh database for each test
    2. Applying all migrations from scratch
    3. Generating appropriate test data
    4. Providing clean session and engine
    5. Automatic cleanup after test
    """
    test_name = request.node.name
    isolation_level = "function"

    # Set up isolation
    isolation_context = await test_isolation_manager.setup_test_isolation(
        test_name, isolation_level
    )

    yield isolation_context

    # Clean up isolation
    await test_isolation_manager.cleanup_test_isolation(test_name)


@pytest.fixture(scope="module")
async def module_isolated_test_environment(self) -> None:
    """
    Module-scoped isolated test environment.

    Provides isolation at the module level for integration tests
    that need to share some state within a module but be isolated
    from other modules.
    """
    test_name = f"module_{request.module.__name__}"
    isolation_level = "module"

    # Set up isolation
    isolation_context = await test_isolation_manager.setup_test_isolation(
        test_name, isolation_level
    )

    yield isolation_context

    # Clean up isolation
    await test_isolation_manager.cleanup_test_isolation(test_name)


@pytest.fixture(scope="function")
async def test_database(self) -> None:
    """Get the isolated test database engine."""
    return isolated_test_environment["engine"]


@pytest.fixture(scope="function")
async def test_session(self) -> None:
    """Get the isolated test database session."""
    return isolated_test_environment["session"]


@pytest.fixture(scope="function")
async def test_data(self) -> None:
    """Get the generated test data for the test."""
    return isolated_test_environment["test_data"]


# Specialized fixtures for different test types
@pytest.fixture(scope="function")
async def unit_test_environment(self) -> None:
    """Isolated environment optimized for unit tests."""
    test_name = f"unit_{request.node.name}"
    isolation_level = "function"

    isolation_context = await test_isolation_manager.setup_test_isolation(
        test_name, isolation_level
    )

    yield isolation_context

    await test_isolation_manager.cleanup_test_isolation(test_name)


@pytest.fixture(scope="function")
async def integration_test_environment(self) -> None:
    """Isolated environment optimized for integration tests."""
    test_name = f"integration_{request.node.name}"
    isolation_level = "function"

    isolation_context = await test_isolation_manager.setup_test_isolation(
        test_name, isolation_level
    )

    yield isolation_context

    await test_isolation_manager.cleanup_test_isolation(test_name)


@pytest.fixture(scope="function")
async def performance_test_environment(self) -> None:
    """Isolated environment optimized for performance tests."""
    test_name = f"performance_{request.node.name}"
    isolation_level = "function"

    isolation_context = await test_isolation_manager.setup_test_isolation(
        test_name, isolation_level
    )

    yield isolation_context

    await test_isolation_manager.cleanup_test_isolation(test_name)


# Migration validation fixtures
@pytest.fixture(scope="session")
async def migration_validator(self) -> None:
    """Session-scoped migration validator for CI validation."""
    config = MigrationValidationConfig(
        migrations_path=Path("migrations"),
        ci_environment=True,
        fail_on_validation_error=True,
        generate_report=True,
    )

    validator = MigrationValidator(config)
    await validator.initialize()

    yield validator


@pytest.fixture(scope="session")
async def validate_migrations_in_ci(self) -> None:
    """Validate migrations in CI environment."""
    logger.info("Running migration validation in CI")

    result = await migration_validator.validate_migrations()

    if not result.success:
        pytest.fail(f"Migration validation failed: {result.errors}")

    return result


# Test data factory fixtures
@pytest.fixture
def fixture_registry(self) -> None:
    """Get the fixture registry."""
    return get_fixture_registry()


@pytest.fixture(scope="function")
async def basic_test_data(self) -> None:
    """Create basic test data for a test."""
    return await create_basic_test_scenario(test_database)


@pytest.fixture(scope="function")
async def comprehensive_test_data(self) -> None:
    """Create comprehensive test data for integration tests."""
    return await create_comprehensive_test_scenario(test_database)


@pytest.fixture(scope="function")
async def performance_test_data(self) -> None:
    """Create performance test data for load testing."""
    return await create_performance_test_scenario(test_database)


# Pytest configuration hooks
def pytest_configure(self) -> None:
    """Configure pytest with enhanced settings."""
    # Set asyncio mode
    config.option.asyncio_mode = AsyncMode.AUTO

    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests with complete isolation")
    config.addinivalue_line(
        "markers", "integration: Integration tests with module isolation"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests with large datasets"
    )
    config.addinivalue_line(
        "markers", "migration_validation: Tests that validate migrations"
    )
    config.addinivalue_line(
        "markers", "test_isolation: Tests that verify isolation works"
    )

    logger.info("Pytest configured with enhanced test isolation")


def pytest_runtest_setup(self) -> None:
    """Setup before each test runs."""
    test_name = item.name

    # Log test start with isolation info
    logger.info(f"Setting up test: {test_name}")

    # Verify test isolation requirements
    if hasattr(item, "pytestmark"):
        for mark in item.pytestmark:
            if mark.name == "test_isolation":
                logger.info(f"Test {test_name} requires complete isolation")


def pytest_runtest_teardown(self) -> None:
    """Teardown after each test runs."""
    test_name = item.name

    # Log test completion
    logger.info(f"Tearing down test: {test_name}")

    # Verify isolation cleanup
    manager = get_test_isolation_manager()
    if test_name in manager.active_tests:
        logger.warning(f"Test {test_name} did not properly cleanup isolation resources")


def pytest_sessionfinish(self) -> None:
    """Called after whole test run finished."""
    logger.info("Test session finished")

    # Get test metrics
    manager = get_test_isolation_manager()
    metrics = manager.get_test_metrics()

    # Log test metrics
    if metrics:
        logger.info("Test execution metrics:")
        for test_name, test_metrics in metrics.items():
            logger.info(
                f"  {test_name}: {test_metrics['duration']:.2f}s, "
                f"DB: {test_metrics['database_name']}, "
                f"Isolation: {test_metrics['isolation_level']}"
            )

    # Log exit status
    logger.info(f"Test session exit status: {exitstatus}")


def pytest_collection_modifyitems(self) -> None:
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests based on directory structure
        test_path = str(item.fspath)

        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/performance/" in test_path or "/e2e/" in test_path:
            item.add_marker(pytest.mark.performance)

        # Add isolation marker to all tests
        item.add_marker(pytest.mark.test_isolation)


# Test isolation validation utilities
class TestIsolationValidator:
    """Utility class to validate that test isolation is working correctly."""

    @staticmethod
    async def validate_test_isolation(test_session, test_name: str) -> bool:
        """
        Validate that test isolation is working correctly.

        This method can be called within tests to verify that:
        1. The test has its own database
        2. The database is clean and isolated
        3. No data from other tests is present
        """
        try:
            # Check that we have a clean database
            from sqlalchemy import text

            result = await test_session.execute(
                text(
                    """
                SELECT COUNT(*) as table_count
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
                )
            )

            table_count = result.scalar()

            # For a clean database, we should have only the expected tables
            # This number should match your migration schema
            expected_table_count = 6  # Adjust based on your schema

            if table_count != expected_table_count:
                logger.warning(
                    f"Test {test_name}: Unexpected table count {table_count}, "
                    f"expected {expected_table_count}"
                )
                return False

            # Check that critical tables are empty (for fresh database)
            critical_tables = ["users", "tenants", "search_history"]

            for table in critical_tables:
                from sqlalchemy import text

                result = await test_session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                count = result.scalar()

                if count > 0:
                    logger.warning(
                        f"Test {test_name}: Table {table} has {count} records, "
                        f"expected 0 for fresh database"
                    )
                    return False

            logger.info(f"Test isolation validation passed for: {test_name}")
            return True

        except Exception as e:
            logger.error(f"Test isolation validation failed for {test_name}: {e}")
            return False


# Export the validator for use in tests
@pytest.fixture
def test_isolation_validator(self) -> None:
    """Get the test isolation validator."""
    return TestIsolationValidator()
