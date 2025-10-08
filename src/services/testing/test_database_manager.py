#!/usr/bin/env python3
"""PAKE System - Enterprise Test Database Management Service
Proactive test data management strategy for integration tests.

This service implements the three core principles:
1. Test Isolation: Each test function is completely independent
2. Migration Validation: CI starts from empty state with full migration chain
3. Fixture-Based Seeding: Code-based fixtures instead of static SQL dumps
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from pathlib import Path
from typing import Any

import pydantic

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import pytest
except ImportError:
    pytest = None

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:
    text = None
    AsyncEngine = None
    AsyncSession = None
    create_async_engine = None
    sessionmaker = None


logger = logging.getLogger(__name__)


@dataclass
class TestDatabaseConfig:
    """Configuration for test database management."""

    # Database connection settings
    host: str = "localhost"
    port: int = 5432
    user: str = "test_user"
    password: str = "test_password"
    database_prefix: str = "pake_test"

    # Test isolation settings
    create_fresh_database_per_test: bool = False
    create_fresh_database_per_module: bool = True
    create_fresh_database_per_session: bool = False

    # Migration settings
    migrations_path: Path | None = None
    validate_migrations_in_ci: bool = True
    apply_migrations_on_setup: bool = True

    # Cleanup settings
    cleanup_after_test: bool = True
    cleanup_after_module: bool = True
    cleanup_after_session: bool = True

    # Performance settings
    connection_pool_size: int = 5
    connection_timeout: int = 30

    # Debug settings
    echo_sql: bool = False
    log_queries: bool = False

    # Generated fields
    created_databases: set[str] = field(default_factory=set)
    active_connections: dict[str, AsyncEngine] = field(default_factory=dict)


@dataclass
class TestDataFixture:
    """Represents a test data fixture with metadata."""

    name: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    data_generator: Callable | None = None
    cleanup_required: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate fixture configuration."""
        if not self.data_generator:
            msg = f"Fixture '{self.name}' must have a data_generator"
            raise ValueError(msg)


class TestDatabaseManager:
    """Enterprise-grade test database management service.

    Implements proactive test data management strategy with:
    - Complete test isolation
    - Migration validation in CI
    - Fixture-based data seeding
    - Automatic cleanup and resource management
    """

    def __init__(self, config: TestDatabaseConfig | None = None) -> None:
        self.config = config or TestDatabaseConfig()
        self._fixtures: dict[str, TestDataFixture] = {}
        self._active_sessions: dict[str, AsyncSession] = {}
        self._migration_history: list[str] = []

        # Set up logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self) -> None:
        """Initialize the test database manager."""
        self.logger.info("Initializing Test Database Manager")

        # Validate configuration
        await self._validate_config()

        # Set up migration tracking
        if self.config.migrations_path:
            await self._setup_migration_tracking()

        self.logger.info("Test Database Manager initialized successfully")

    async def _validate_config(self) -> None:
        """Validate the test database configuration."""
        if not self.config.database_prefix:
            msg = "database_prefix is required"
            raise ValueError(msg)

        if self.config.migrations_path and not self.config.migrations_path.exists():
            msg = f"Migrations path does not exist: {self.config.migrations_path}"
            raise ValueError(msg)

    async def _setup_migration_tracking(self) -> None:
        """Set up migration tracking for CI validation."""
        self.logger.info("Setting up migration tracking")

        # This would integrate with Alembic or custom migration system
        # For now, we'll track migrations manually
        if self.config.migrations_path:
            migration_files = sorted(self.config.migrations_path.glob("*.sql"))
            self._migration_history = [f.name for f in migration_files]
            self.logger.info("Found %s migration files", len(self._migration_history))

    @asynccontextmanager
    async def test_database(
        self, test_name: str | None = None, isolation_level: str = "module"
    ) -> AsyncGenerator[AsyncEngine, None]:
        """Context manager for test database with automatic cleanup.

        Args:
            test_name: Name of the test (used for database naming)
            isolation_level: Level of isolation (function, module, session)
        """
        database_name = await self._generate_database_name(test_name, isolation_level)

        try:
            # Create fresh database
            engine = await self._create_test_database(database_name)

            # Apply migrations if configured
            if self.config.apply_migrations_on_setup:
                await self._apply_migrations(engine)

            self.logger.info("Created test database: %s", database_name)
            yield engine

        finally:
            # Cleanup based on isolation level
            await self._cleanup_database(database_name, isolation_level)

    async def _generate_database_name(
        self, test_name: str | None, isolation_level: str
    ) -> str:
        """Generate a unique database name for the test."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        test_id = test_name or "test"

        # Create unique identifier
        unique_id = f"{timestamp}_{test_id}_{isolation_level}"

        return f"{self.config.database_prefix}_{unique_id}"

    async def _create_test_database(self, database_name: str) -> "AsyncEngine":
        """Create a fresh test database."""
        self.logger.info("Creating test database: %s", database_name)

        # Create database using asyncpg
        conn = await asyncpg.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database="postgres",  # Connect to default database to create new one
        )

        try:
            # Drop database if it exists (for clean state)
            await conn.execute(f"DROP DATABASE IF EXISTS {database_name}")

            # Create new database
            await conn.execute(f"CREATE DATABASE {database_name}")

            # Track created database
            self.config.created_databases.add(database_name)

        finally:
            await conn.close()

        # Create SQLAlchemy engine for the new database
        database_url = (
            f"postgresql+asyncpg://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{database_name}"
        )

        engine = create_async_engine(
            database_url,
            echo=self.config.echo_sql,
            pool_size=self.config.connection_pool_size,
            pool_timeout=self.config.connection_timeout,
        )

        self.config.active_connections[database_name] = engine
        return engine

    async def _apply_migrations(self, engine: AsyncEngine) -> None:
        """Apply all migrations to the test database."""
        if not self.config.migrations_path:
            self.logger.warning(
                "No migrations path configured, skipping migration application"
            )
            return

        self.logger.info("Applying migrations to test database")

        async with engine.begin() as conn:
            # Apply each migration in order
            for migration_file in sorted(self.config.migrations_path.glob("*.sql")):
                self.logger.info("Applying migration: %s", migration_file.name)

                with open(migration_file) as f:
                    sql_content = f.read()

                # Execute migration SQL
                await conn.execute(text(sql_content))

                # Track applied migration
                self._migration_history.append(migration_file.name)

        self.logger.info("Applied %s migrations", len(self._migration_history))

    async def _cleanup_database(self, database_name: str, isolation_level: str) -> None:
        """Clean up test database based on isolation level."""
        should_cleanup = False

        if (
            isolation_level == "function"
            and self.config.cleanup_after_test
            or isolation_level == "module"
            and self.config.cleanup_after_module
            or isolation_level == "session"
            and self.config.cleanup_after_session
        ):
            should_cleanup = True

        if should_cleanup:
            await self._drop_database(database_name)

    async def _drop_database(self, database_name: str) -> None:
        """Drop a test database."""
        self.logger.info("Dropping test database: %s", database_name)

        # Close any active connections
        if database_name in self.config.active_connections:
            engine = self.config.active_connections[database_name]
            await engine.dispose()
            del self.config.active_connections[database_name]

        # Drop database
        conn = await asyncpg.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database="postgres",
        )

        try:
            # Terminate any remaining connections
            await conn.execute(
                f"SELECT pg_terminate_backend(pid) "
                f"FROM pg_stat_activity WHERE datname = '{database_name}'"
            )

            # Drop database
            await conn.execute(f"DROP DATABASE IF EXISTS {database_name}")

            # Remove from tracking
            self.config.created_databases.discard(database_name)

        finally:
            await conn.close()

    def register_fixture(self, fixture: TestDataFixture) -> None:
        """Register a test data fixture."""
        self._fixtures[fixture.name] = fixture
        self.logger.info("Registered fixture: %s", fixture.name)

    async def create_fixture_data(
        self, fixture_name: str, engine: AsyncEngine, **kwargs
    ) -> Any:
        """Create data using a registered fixture."""
        if fixture_name not in self._fixtures:
            msg = f"Fixture '{fixture_name}' not found"
            raise ValueError(msg)

        fixture = self._fixtures[fixture_name]

        # Check dependencies
        for dep in fixture.dependencies:
            if dep not in self._fixtures:
                msg = f"Fixture dependency '{dep}' not found"
                raise ValueError(msg)

        # Create dependency data first
        dependency_data = {}
        for dep in fixture.dependencies:
            dependency_data[dep] = await self.create_fixture_data(dep, engine, **kwargs)

        # Create fixture data
        self.logger.info("Creating fixture data: %s", fixture_name)

        if fixture.data_generator:
            return await fixture.data_generator(engine, dependency_data, **kwargs)

        return None

    async def cleanup_fixture_data(
        self, fixture_name: str, engine: AsyncEngine
    ) -> None:
        """Clean up data created by a fixture."""
        if fixture_name not in self._fixtures:
            return

        fixture = self._fixtures[fixture_name]

        if fixture.cleanup_required:
            self.logger.info("Cleaning up fixture data: %s", fixture_name)
            # Implement cleanup logic based on fixture type
            # This would typically involve deleting created records

    async def validate_migrations_in_ci(self) -> bool:
        """Validate migrations in CI by starting from empty state.

        This implements the second core principle: CI should start from
        completely empty state and apply all migrations from the beginning.
        """
        if not self.config.validate_migrations_in_ci:
            return True

        self.logger.info("Validating migrations in CI environment")

        # Create a temporary database for migration validation
        temp_db_name = f"{self.config.database_prefix}_migration_validation"

        try:
            # Create fresh database
            engine = await self._create_test_database(temp_db_name)

            # Apply all migrations from scratch
            await self._apply_migrations(engine)

            # Validate schema was created correctly
            validation_passed = await self._validate_schema(engine)

            if validation_passed:
                self.logger.info("✅ Migration validation passed")
            else:
                self.logger.error("❌ Migration validation failed")

            return validation_passed

        finally:
            # Always cleanup validation database
            await self._drop_database(temp_db_name)

    async def _validate_schema(self, engine: AsyncEngine) -> bool:
        """Validate that the schema was created correctly."""
        try:
            async with engine.begin() as conn:
                # Check that essential tables exist
                result = await conn.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
                    )
                )

                tables = [row[0] for row in result.fetchall()]

                # Define expected tables (this would be configurable)
                expected_tables = [
                    "users",
                    "tenants",
                    "search_history",
                    "saved_searches",
                    "system_metrics",
                ]

                missing_tables = set(expected_tables) - set(tables)

                if missing_tables:
                    self.logger.error("Missing tables: %s", missing_tables)
                    return False

                self.logger.info("Schema validation passed. Found tables: %s", tables)
                return True

        except (pydantic.ValidationError, ValueError) as e:
            self.logger.error("Schema validation error: %s", e)
            return False

    async def get_test_session(self, engine: AsyncEngine) -> AsyncSession:
        """Get a test database session."""
        session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        return session_factory()

    async def cleanup_all(self) -> None:
        """Clean up all test databases and resources."""
        self.logger.info("Cleaning up all test resources")

        # Close all active connections
        for database_name, engine in list(self.config.active_connections.items()):
            await engine.dispose()
            del self.config.active_connections[database_name]

        # Drop all created databases
        for database_name in list(self.config.created_databases):
            await self._drop_database(database_name)

        self.logger.info("Test resource cleanup completed")


# Global test database manager instance
_test_db_manager: TestDatabaseManager | None = None


def get_test_database_manager() -> TestDatabaseManager:
    """Get the global test database manager instance."""
    global _test_db_manager

    if _test_db_manager is None:
        config = TestDatabaseConfig()
        _test_db_manager = TestDatabaseManager(config)

    return _test_db_manager


async def initialize_test_database_manager() -> TestDatabaseManager:
    """Initialize and return the test database manager."""
    manager = get_test_database_manager()
    await manager.initialize()
    return manager


# Pytest fixtures for easy integration
@pytest.fixture(scope="session")
async def test_database_manager(self) -> None:
    """Session-scoped test database manager fixture."""
    manager = await initialize_test_database_manager()
    yield manager
    await manager.cleanup_all()


@pytest.fixture(scope="module")
async def test_database(self) -> None:
    """Module-scoped test database fixture."""
    async with test_database_manager.test_database(isolation_level="module") as engine:
        yield engine


@pytest.fixture(scope="function")
async def isolated_test_database(self) -> None:
    """Function-scoped isolated test database fixture."""
    async with test_database_manager.test_database(
        isolation_level="function"
    ) as engine:
        yield engine


@pytest.fixture(scope="function")
async def test_session(self) -> None:
    """Function-scoped test database session fixture."""
    manager = get_test_database_manager()
    session = await manager.get_test_session(isolated_test_database)
    yield session
    await session.close()
