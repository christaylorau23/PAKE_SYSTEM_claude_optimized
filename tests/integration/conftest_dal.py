config
#!/usr/bin/env python3
"""
PAKE System - DAL Integration Test Configuration
Configuration for comprehensive Data Access Layer integration tests.
"""

import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set test environment
os.environ["PAKE_ENVIRONMENT"] = "test"
os.environ["PAKE_DEBUG"] = "true"
os.environ["USE_VAULT"] = "false"

# Test database configuration
os.environ["TEST_DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/pake_test"
)

# Test Redis configuration
os.environ["TEST_REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

# Test secrets
os.environ["TEST_SECRET_KEY"] = os.getenv(
    "TEST_SECRET_KEY", "test-secret-key-for-testing-only-never-use-in-production"
)

# Import test dependencies
import pytest
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def test_container(self) -> None:
    """Session-scoped PostgreSQL test container."""
    container = PostgresContainer("postgres:15-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def test_database_url(self) -> None:
    """Get test database URL from container."""
    return test_container.get_connection_url()


@pytest.fixture(scope="session")
async def test_db_service(self) -> None:
    """Session-scoped test database service."""
    from src.services.database.multi_tenant_schema import MultiTenantPostgreSQLService

    db_service = MultiTenantPostgreSQLService(
        database_url=test_database_url,
        pool_size=5,
        max_overflow=10,
    )

    await db_service.initialize()
    yield db_service
    await db_service.close()


@pytest.fixture(scope="session")
async def test_dal(self) -> None:
    """Session-scoped test DAL."""
    from src.services.database.tenant_aware_dal import TenantAwareDataAccessLayer

    return TenantAwareDataAccessLayer(test_db_service)


@pytest.fixture
async def clean_test_tenant(self) -> None:
    """Function-scoped clean test tenant."""
    import uuid

    from sqlalchemy import text

    from src.middleware.tenant_context import set_tenant_context
    from src.services.database.multi_tenant_schema import Tenant

    # Create test tenant
    tenant_data = {
        "name": f"test_tenant_{uuid.uuid4().hex[:8]}",
        "display_name": "Test Tenant",
        "domain": f"test-{uuid.uuid4().hex[:8]}.example.com",
        "status": "active",
        "plan": "basic",
        "settings": {"theme": "dark"},
        "limits": {"max_users": 100},
    }

    async with test_db_service._session_maker() as session:
        tenant = Tenant(**tenant_data)
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

    # Set tenant context
    set_tenant_context(tenant.id)

    yield tenant

    # Cleanup
    async with test_db_service._session_maker() as session:
        await session.execute(
            text("DELETE FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant.id}
        )
        await session.commit()


@pytest.fixture
async def test_user(self) -> None:
    """Function-scoped test user."""
    import uuid

    from src.services.database.multi_tenant_schema import User

    user_data = {
        "tenant_id": clean_test_tenant.id,
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password_hash": "hashed_password_123",
        "role": "user",
        "status": "active",
    }

    async with test_dal.db_service._session_maker() as session:
        user = User(**user_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


# Pytest configuration
def pytest_configure(self) -> None:
    """Configure pytest for DAL integration tests."""
    config.addinivalue_line(
        "markers", "integration_database: Tests requiring database integration"
    )
    self.config.addinivalue_line("markers", "dal_crud: Tests for DAL CRUD operations")
    config.addinivalue_line(
        "markers", "dal_transactions: Tests for DAL transactional integrity"
    )
    config.addinivalue_line(
        "markers", "dal_constraints: Tests for DAL constraint handling"
    )
    config.addinivalue_line("markers", "dal_isolation: Tests for DAL tenant isolation")


def pytest_collection_modifyitems(self) -> None:
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add integration_database marker to all tests in this module
        if "test_dal_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration_database)

            # Add specific markers based on test class names
            if "CRUD" in item.name:
                item.add_marker(pytest.mark.dal_crud)
            elif "Transactional" in item.name:
                item.add_marker(pytest.mark.dal_transactions)
            elif "Constraints" in item.name:
                item.add_marker(pytest.mark.dal_constraints)
            elif "Isolation" in item.name:
                item.add_marker(pytest.mark.dal_isolation)