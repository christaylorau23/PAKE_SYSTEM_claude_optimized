#!/usr/bin/env python3
"""PAKE System - Enterprise Test Data Factories
Code-based fixtures for realistic test data generation.

Replaces static SQL dumps with programmatic data generation that:
- Creates realistic, varied test data
- Supports complex relationships and dependencies
- Provides consistent, reproducible test scenarios
- Enables easy maintenance and updates
"""

import random
import uuid
from datetime import UTC, datetime
from typing import Any

try:
    import factory
except ImportError:
    factory = None

try:
    from faker import Faker
except ImportError:
    Faker = None

try:
    from sqlalchemy.ext.asyncio import AsyncEngine
    from sqlalchemy.orm import Session
except ImportError:
    AsyncEngine = None
    Session = None

from src.services.database.multi_tenant_schema import (
    SavedSearch,
    SearchHistory,
    SystemMetrics,
    Tenant,
    User,
)
from src.services.testing.test_database_manager import TestDataFixture

# Initialize Faker for realistic data generation
if Faker:
    fake = Faker()
    Faker.seed(42)  # Ensure reproducible data
else:
    fake = None


if factory:

    class BaseFactory(factory.Factory):
        """Base factory with common patterns for PAKE System entities."""

        class Meta:
            abstract = True

        @classmethod
        def _create(cls) -> None:
            """Create instance with proper async handling."""
            # Remove factory-specific kwargs
            factory_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_")}
            return model_class(**factory_kwargs)

        @classmethod
        async def create_async(cls) -> None:
            """Async version of factory creation."""
            return cls.build(**kwargs)

else:

    class BaseFactory:
        """Fallback base factory when factory-boy is not available."""


if factory and fake:

    class TenantFactory(BaseFactory):
        """Factory for creating realistic tenant data."""

        class Meta:
            model = Tenant

        id = factory.LazyFunction(lambda: str(uuid.uuid4()))
        name = factory.LazyFunction(lambda: fake.slug())
        display_name = factory.LazyFunction(lambda: fake.company())
        domain = factory.LazyFunction(lambda: fake.domain_name())
        plan = factory.Iterator(["basic", "professional", "enterprise"])
        status = factory.Iterator(["active", "suspended", "trial"])
        created_at = factory.LazyFunction(
            lambda: fake.date_time_between(start_date="-1y", end_date="now", tzinfo=UTC)
        )
        updated_at = factory.LazyFunction(
            lambda: fake.date_time_between(start_date="-6m", end_date="now", tzinfo=UTC)
        )

        # Realistic tenant configurations
        settings = factory.LazyFunction(
            lambda: {
                "max_users": random.choice([10, 50, 100, 500, 1000]),
                "max_storage_gb": random.choice([10, 100, 500, 1000]),
                "features": random.sample(
                    [
                        "advanced_analytics",
                        "api_access",
                        "custom_branding",
                        "sso",
                        "audit_logs",
                        "priority_support",
                    ],
                    k=random.randint(2, 6),
                ),
            }
        )

else:

    class TenantFactory(BaseFactory):
        """Fallback tenant factory when factory-boy is not available."""

        @classmethod
        def build(cls) -> None:
            """Build a tenant instance with default values."""
            return Tenant(
                id=str(uuid.uuid4()),
                name=kwargs.get("name", "test-tenant"),
                display_name=kwargs.get("display_name", "Test Tenant"),
                domain=kwargs.get("domain", "test.example.com"),
                plan=kwargs.get("plan", "basic"),
                status=kwargs.get("status", "active"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                settings=kwargs.get("settings", {}),
            )


class UserFactory(BaseFactory):
    """Factory for creating realistic user data."""

    class Meta:
        model = User

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.LazyFunction(lambda: fake.user_name())
    email = factory.LazyFunction(lambda: fake.email())
    full_name = factory.LazyFunction(lambda: fake.name())
    role = factory.Iterator(["user", "admin", "moderator", "viewer"])
    status = factory.Iterator(["active", "inactive", "pending"])
    tenant_id = factory.SubFactory(TenantFactory)
    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-1y", end_date="now", tzinfo=UTC)
    )
    last_login = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-30d", end_date="now", tzinfo=UTC)
    )

    # User preferences and settings
    preferences = factory.LazyFunction(
        lambda: {
            "theme": random.choice(["light", "dark", "auto"]),
            "language": random.choice(["en", "es", "fr", "de"]),
            "notifications": {
                "email": random.choice([True, False]),
                "push": random.choice([True, False]),
                "frequency": random.choice(["immediate", "daily", "weekly"]),
            },
        }
    )


class SearchHistoryFactory(BaseFactory):
    """Factory for creating realistic search history data."""

    class Meta:
        model = SearchHistory

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.SubFactory(UserFactory)
    tenant_id = factory.SubFactory(TenantFactory)
    query = factory.LazyFunction(lambda: fake.sentence(nb_words=random.randint(2, 8)))
    query_type = factory.Iterator(["web", "arxiv", "pubmed", "email", "rss"])
    results_count = factory.LazyFunction(lambda: random.randint(0, 100))
    execution_time_ms = factory.LazyFunction(lambda: random.randint(50, 5000))
    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-30d", end_date="now", tzinfo=UTC)
    )

    # Search context and metadata
    context = factory.LazyFunction(
        lambda: {
            "sources": random.sample(
                ["web", "arxiv", "pubmed", "email"], k=random.randint(1, 4)
            ),
            "filters": {
                "date_range": random.choice(
                    ["last_week", "last_month", "last_year", "all_time"]
                ),
                "content_type": random.choice(["all", "papers", "news", "blogs"]),
            },
            "user_agent": fake.user_agent(),
            "ip_address": fake.ipv4(),
        }
    )


class SavedSearchFactory(BaseFactory):
    """Factory for creating realistic saved search data."""

    class Meta:
        model = SavedSearch

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.SubFactory(UserFactory)
    tenant_id = factory.SubFactory(TenantFactory)
    name = factory.LazyFunction(lambda: fake.catch_phrase())
    query = factory.LazyFunction(lambda: fake.sentence(nb_words=random.randint(3, 10)))
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    is_public = factory.LazyFunction(lambda: random.choice([True, False]))
    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-6m", end_date="now", tzinfo=UTC)
    )
    last_run = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-7d", end_date="now", tzinfo=UTC)
    )

    # Search configuration
    configuration = factory.LazyFunction(
        lambda: {
            "sources": random.sample(
                ["web", "arxiv", "pubmed", "email"], k=random.randint(1, 4)
            ),
            "schedule": random.choice(["manual", "daily", "weekly", "monthly"]),
            "notifications": random.choice([True, False]),
            "auto_tagging": random.choice([True, False]),
        }
    )


class SystemMetricsFactory(BaseFactory):
    """Factory for creating realistic system metrics data."""

    class Meta:
        model = SystemMetrics

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    tenant_id = factory.SubFactory(TenantFactory)
    metric_name = factory.Iterator(
        [
            "api_requests_per_minute",
            "search_queries_per_hour",
            "user_active_count",
            "cache_hit_rate",
            "database_query_time",
            "memory_usage",
            "cpu_usage",
        ]
    )
    metric_value = factory.LazyFunction(lambda: round(random.uniform(0, 100), 2))
    metric_unit = factory.Iterator(
        ["count", "percentage", "milliseconds", "bytes", "requests"]
    )
    timestamp = factory.LazyFunction(
        lambda: fake.date_time_between(start_date="-7d", end_date="now", tzinfo=UTC)
    )

    # Additional metric metadata
    metadata = factory.LazyFunction(
        lambda: {
            "source": random.choice(["api", "database", "cache", "system"]),
            "environment": random.choice(["production", "staging", "development"]),
            "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        }
    )


class TestDataFixtureRegistry:
    """Registry for managing test data fixtures.

    Provides a centralized way to register, manage, and execute
    test data fixtures with proper dependency resolution.
    """

    def __init__(self) -> None:
        self._fixtures: dict[str, TestDataFixture] = {}
        self._execution_order: list[str] = []

    def register_fixture(self, fixture: TestDataFixture) -> None:
        """Register a test data fixture."""
        self._fixtures[fixture.name] = fixture
        self._update_execution_order()

    def _update_execution_order(self) -> None:
        """Update the execution order based on dependencies."""
        # Simple topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        order = []

        def visit(self) -> None:
            if name in temp_visited:
                msg = f"Circular dependency detected involving {name}"
                raise ValueError(msg)
            if name in visited:
                return

            temp_visited.add(name)

            if name in self._fixtures:
                for dep in self._fixtures[name].dependencies:
                    visit(dep)

            temp_visited.remove(name)
            visited.add(name)
            order.append(name)

        for fixture_name in self._fixtures:
            visit(fixture_name)

        self._execution_order = order

    async def execute_fixture(
        self, fixture_name: str, engine: AsyncEngine, **kwargs
    ) -> Any:
        """Execute a specific fixture."""
        if fixture_name not in self._fixtures:
            msg = f"Fixture '{fixture_name}' not found"
            raise ValueError(msg)

        fixture = self._fixtures[fixture_name]

        # Execute dependencies first
        dependency_data = {}
        for dep in fixture.dependencies:
            dependency_data[dep] = await self.execute_fixture(dep, engine, **kwargs)

        # Execute the fixture
        if fixture.data_generator:
            return await fixture.data_generator(engine, dependency_data, **kwargs)

        return None

    async def execute_all_fixtures(
        self, engine: AsyncEngine, **kwargs
    ) -> dict[str, Any]:
        """Execute all fixtures in dependency order."""
        results = {}

        for fixture_name in self._execution_order:
            results[fixture_name] = await self.execute_fixture(
                fixture_name, engine, **kwargs
            )

        return results


# Global fixture registry
_fixture_registry = TestDataFixtureRegistry()


def get_fixture_registry() -> TestDataFixtureRegistry:
    """Get the global fixture registry."""
    return _fixture_registry


# Predefined fixture generators
async def create_tenant_fixture(
    engine: AsyncEngine, dependencies: dict[str, Any], **kwargs
) -> dict[str, Any]:
    """Create a tenant with realistic data."""
    tenant_count = kwargs.get("count", 1)
    tenants = []

    for _ in range(tenant_count):
        tenant_data = TenantFactory.build()
        # In a real implementation, this would save to the database
        tenants.append(tenant_data)

    return {"tenants": tenants}


async def create_user_fixture(
    engine: AsyncEngine, dependencies: dict[str, Any], **kwargs
) -> dict[str, Any]:
    """Create users with realistic data."""
    tenant_data = dependencies.get("tenant_fixture", {})
    tenants = tenant_data.get("tenants", [])

    if not tenants:
        msg = "User fixture requires tenant fixture"
        raise ValueError(msg)

    user_count = kwargs.get("count", 5)
    users = []

    for _ in range(user_count):
        user_data = UserFactory.build(tenant_id=random.choice(tenants).id)
        users.append(user_data)

    return {"users": users}


async def create_search_history_fixture(
    engine: AsyncEngine, dependencies: dict[str, Any], **kwargs
) -> dict[str, Any]:
    """Create search history with realistic patterns."""
    user_data = dependencies.get("user_fixture", {})
    users = user_data.get("users", [])

    if not users:
        msg = "Search history fixture requires user fixture"
        raise ValueError(msg)

    search_count = kwargs.get("count", 20)
    searches = []

    for _ in range(search_count):
        user = random.choice(users)
        search_data = SearchHistoryFactory.build(
            user_id=user.id, tenant_id=user.tenant_id
        )
        searches.append(search_data)

    return {"searches": searches}


async def create_saved_searches_fixture(
    engine: AsyncEngine, dependencies: dict[str, Any], **kwargs
) -> dict[str, Any]:
    """Create saved searches with realistic data."""
    user_data = dependencies.get("user_fixture", {})
    users = user_data.get("users", [])

    if not users:
        msg = "Saved searches fixture requires user fixture"
        raise ValueError(msg)

    saved_count = kwargs.get("count", 10)
    saved_searches = []

    for _ in range(saved_count):
        user = random.choice(users)
        saved_search_data = SavedSearchFactory.build(
            user_id=user.id, tenant_id=user.tenant_id
        )
        saved_searches.append(saved_search_data)

    return {"saved_searches": saved_searches}


async def create_system_metrics_fixture(
    engine: AsyncEngine, dependencies: dict[str, Any], **kwargs
) -> dict[str, Any]:
    """Create system metrics with realistic patterns."""
    tenant_data = dependencies.get("tenant_fixture", {})
    tenants = tenant_data.get("tenants", [])

    if not tenants:
        msg = "System metrics fixture requires tenant fixture"
        raise ValueError(msg)

    metrics_count = kwargs.get("count", 100)
    metrics = []

    for _ in range(metrics_count):
        tenant = random.choice(tenants)
        metric_data = SystemMetricsFactory.build(tenant_id=tenant.id)
        metrics.append(metric_data)

    return {"metrics": metrics}


# Register predefined fixtures
def register_default_fixtures(self) -> None:
    """Register all default fixtures."""
    registry = get_fixture_registry()

    # Register fixtures with proper dependencies
    registry.register_fixture(
        TestDataFixture(
            name="tenant_fixture",
            description="Creates realistic tenant data",
            dependencies=[],
            data_generator=create_tenant_fixture,
        )
    )

    registry.register_fixture(
        TestDataFixture(
            name="user_fixture",
            description="Creates realistic user data",
            dependencies=["tenant_fixture"],
            data_generator=create_user_fixture,
        )
    )

    registry.register_fixture(
        TestDataFixture(
            name="search_history_fixture",
            description="Creates realistic search history",
            dependencies=["user_fixture"],
            data_generator=create_search_history_fixture,
        )
    )

    registry.register_fixture(
        TestDataFixture(
            name="saved_searches_fixture",
            description="Creates realistic saved searches",
            dependencies=["user_fixture"],
            data_generator=create_saved_searches_fixture,
        )
    )

    registry.register_fixture(
        TestDataFixture(
            name="system_metrics_fixture",
            description="Creates realistic system metrics",
            dependencies=["tenant_fixture"],
            data_generator=create_system_metrics_fixture,
        )
    )


# Initialize default fixtures
register_default_fixtures()


# Convenience functions for common test scenarios
async def create_basic_test_scenario(engine: AsyncEngine) -> dict[str, Any]:
    """Create a basic test scenario with minimal data."""
    registry = get_fixture_registry()

    return await registry.execute_all_fixtures(engine, count=1)


async def create_comprehensive_test_scenario(engine: AsyncEngine) -> dict[str, Any]:
    """Create a comprehensive test scenario with full data."""
    registry = get_fixture_registry()

    return await registry.execute_all_fixtures(engine, count=10)


async def create_performance_test_scenario(engine: AsyncEngine) -> dict[str, Any]:
    """Create a performance test scenario with large datasets."""
    registry = get_fixture_registry()

    return await registry.execute_all_fixtures(engine, count=100)


# Pytest fixtures for easy integration (only if pytest is available)
if pytest:

    @pytest.fixture
    def fixture_registry(self) -> None:
        """Get the fixture registry."""
        return get_fixture_registry()

    @pytest.fixture
    async def basic_test_data(self) -> None:
        """Create basic test data for a test."""
        return await create_basic_test_scenario(isolated_test_database)

    @pytest.fixture
    async def comprehensive_test_data(self) -> None:
        """Create comprehensive test data for integration tests."""
        return await create_comprehensive_test_scenario(isolated_test_database)

    @pytest.fixture
    async def performance_test_data(self) -> None:
        """Create performance test data for load testing."""
        return await create_performance_test_scenario(isolated_test_database)
