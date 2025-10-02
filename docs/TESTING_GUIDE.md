# PAKE System - Comprehensive Testing Guide

**Building confidence through automated testing and continuous integration**

---

## Table of Contents

1. [Overview](#overview)
2. [Testing Philosophy](#testing-philosophy)
3. [Testing Pyramid](#testing-pyramid)
4. [Running Tests](#running-tests)
5. [Writing Tests](#writing-tests)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Test Coverage](#test-coverage)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The PAKE System implements a comprehensive, automated testing suite following industry best practices. Our testing strategy is built on the Testing Pyramid principle, emphasizing fast, isolated unit tests while maintaining essential integration and end-to-end coverage.

### Testing Stack

- **Framework**: pytest 7.4+
- **Mocking**: pytest-mock, unittest.mock
- **Factories**: factory_boy
- **Coverage**: pytest-cov
- **Async**: pytest-asyncio
- **Performance**: pytest-benchmark

### Coverage Goals

| Test Type | Target Coverage | Actual |
|-----------|----------------|--------|
| Unit Tests | 70% of tests | ✅ |
| Integration Tests | 20% of tests | ✅ |
| E2E Tests | 10% of tests | ✅ |
| **Total Coverage** | **>80%** | ✅ **Enforced by CI** |

---

## Testing Philosophy

### Core Principles

1. **Fast Feedback** - Tests should run quickly, giving instant feedback
2. **Isolation** - Each test should be independent and isolated
3. **Repeatability** - Tests should produce the same results every time
4. **Clarity** - Tests should be easy to read and understand
5. **Maintainability** - Tests should be easy to update as code evolves

### AAA Pattern

All tests follow the **Arrange-Act-Assert** pattern:

```python
def test_user_authentication():
    # Arrange - Set up test data and conditions
    username = "testuser"
    password = "secret"

    # Act - Perform the action being tested
    result = authenticate_user(username, password)

    # Assert - Verify the outcome
    assert result.success is True
    assert result.user.username == username
```

---

## Testing Pyramid

Our tests are organized into three layers, following the Testing Pyramid:

```
       /\
      /E2E\      10% - End-to-End (Slow, High Confidence)
     /------\
    /  INT  \    20% - Integration (Medium Speed)
   /----------\
  /    UNIT    \ 70% - Unit (Fast, Low-level)
 /--------------\
```

### 1. Unit Tests (70%)

**Location**: `tests/unit/`

**Purpose**: Test individual functions/methods in complete isolation

**Characteristics**:
- ⚡ Fast (milliseconds)
- 🔒 Isolated (all dependencies mocked)
- 📊 High coverage of edge cases
- 🎯 Test single responsibility

**Example**:
```python
@pytest.mark.unit
def test_create_password_hash(test_password):
    """Test password hashing generates valid hash"""
    # Arrange
    password = "SecurePassword123!"

    # Act
    hashed = create_password_hash(password)

    # Assert
    assert isinstance(hashed, str)
    assert hashed.startswith("$2b$")  # Bcrypt
```

**Markers**:
- `@pytest.mark.unit` - General unit test
- `@pytest.mark.unit_functional` - Normal operation
- `@pytest.mark.unit_edge_case` - Boundary conditions
- `@pytest.mark.unit_error_handling` - Error scenarios
- `@pytest.mark.unit_performance` - Performance benchmarks

### 2. Integration Tests (20%)

**Location**: `tests/integration/`

**Purpose**: Test interaction between components with real dependencies

**Characteristics**:
- 🐢 Medium speed (seconds)
- 🔗 Real database/cache connections
- 🧩 Test component interactions
- ✅ Verify data persistence

**Example**:
```python
@pytest.mark.integration
@pytest.mark.integration_database
@pytest.mark.asyncio
async def test_user_persists_to_database(test_database):
    """Test that user creation persists correctly"""
    # Arrange
    username = "newuser"
    password_hash = create_password_hash("password")

    # Act
    user = await create_user(username, password_hash)

    # Assert
    stored_user = await get_user(username)
    assert stored_user.username == username
```

**Markers**:
- `@pytest.mark.integration` - General integration test
- `@pytest.mark.integration_database` - Database integration
- `@pytest.mark.integration_cache` - Cache integration
- `@pytest.mark.integration_auth` - Auth integration
- `@pytest.mark.integration_api` - API integration

### 3. End-to-End Tests (10%)

**Location**: `tests/e2e/`

**Purpose**: Test complete user workflows from end to end

**Characteristics**:
- 🐌 Slow (seconds to minutes)
- 🌐 Real HTTP requests
- 🧪 Full application stack
- 👤 User journey focused

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.e2e_user_journey
def test_complete_login_flow(test_client):
    """Test complete user login journey"""
    # Step 1: Login
    response = test_client.post("/token", data={
        "username": "admin",
        "password": "secret"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Step 2: Access protected resource
    response = test_client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

**Markers**:
- `@pytest.mark.e2e` - General E2E test
- `@pytest.mark.e2e_user_journey` - User workflows
- `@pytest.mark.e2e_performance` - Performance tests
- `@pytest.mark.e2e_reliability` - Reliability tests

---

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test type
pytest -m unit
pytest -m integration
pytest -m e2e

# Run specific file
pytest tests/unit/auth/test_security_unit.py

# Run specific test
pytest tests/unit/auth/test_security_unit.py::TestPasswordHashing::test_create_password_hash
```

### Common Commands

```bash
# Fast tests only (no slow E2E)
pytest -m "not slow"

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run in parallel (4 workers)
pytest -n 4

# Re-run failed tests
pytest --lf

# Coverage with HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Environment Setup

Tests require specific environment variables:

```bash
# Set environment variables
export SECRET_KEY="test-secret-key"
export DATABASE_URL="postgresql://test:test@localhost/pake_test"
export REDIS_URL="redis://localhost:6379/1"

# Or use .env.test file
cp .env.example .env.test
# Edit .env.test with test values

# Run tests
pytest
```

### Running Specific Test Suites

```bash
# Authentication tests only
pytest tests/unit/auth/ tests/integration/auth/ tests/e2e/auth/

# Unit tests only (fast)
pytest -m unit

# Integration + E2E (requires services)
pytest -m "integration or e2e"

# Performance benchmarks
pytest -m performance --benchmark-only
```

---

## Writing Tests

### Using Fixtures

**Global Fixtures** (`tests/conftest.py`):

```python
def test_something(test_user, test_client, mock_database):
    """Use pre-configured fixtures"""
    # test_user: Factory-generated user
    # test_client: FastAPI test client
    # mock_database: Mocked database service
    pass
```

**Available Fixtures**:
- `test_client` - FastAPI TestClient
- `authenticated_client` - Client with valid JWT
- `test_user` - Factory-generated user
- `test_admin_user` - Admin user
- `mock_database` - Mocked database
- `mock_redis` - Mocked Redis
- `mock_auth_service` - Mocked auth service

### Using Factories

**Creating Test Data**:

```python
from tests.factories import UserFactory, SearchQueryFactory

def test_with_factory():
    # Create with defaults
    user = UserFactory()

    # Create with overrides
    admin = UserFactory(username="admin", role="admin")

    # Create batch
    users = [UserFactory() for _ in range(5)]

    # Use in tests
    assert user.username.startswith("user")
```

### Mocking Dependencies

**Using pytest-mock**:

```python
def test_with_mocking(mocker):
    # Mock a function
    mock_db = mocker.patch('src.auth.database.get_user')
    mock_db.return_value = UserFactory()

    # Mock async function
    mock_api = mocker.patch('src.api.client.fetch_data')
    mock_api.return_value = AsyncMock(return_value={"data": []})

    # Test code that uses mocked dependencies
    result = authenticate_user("testuser", "password")
    assert mock_db.called
```

**Manual Mocking**:

```python
from unittest.mock import AsyncMock, MagicMock

def test_with_manual_mock():
    # Create mock
    mock_service = AsyncMock()
    mock_service.get_user.return_value = {"id": "123"}

    # Use mock
    result = await service.process(mock_service)

    # Verify calls
    assert mock_service.get_user.called_once_with("123")
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    # Arrange
    user_id = "test-123"

    # Act
    result = await async_get_user(user_id)

    # Assert
    assert result is not None
```

### Testing Exceptions

```python
import pytest

def test_raises_exception():
    # Test that specific exception is raised
    with pytest.raises(ValueError, match="Invalid input"):
        validate_input("bad data")

def test_handles_exception():
    # Test that exception is caught and handled
    result = safe_operation()
    assert result.error is not None
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

Our CI pipeline runs on every pull request and push to main:

```
PR Created → CI Pipeline (Parallel Jobs)
             ├─ 🎨 Lint & Format
             ├─ 🔍 Static Analysis
             ├─ 🔒 Security Scan
             ├─ 🧪 Run Tests (80% coverage required)
             └─ 🐳 Build Check

All Pass? → ✅ Ready to Merge
Any Fail? → ❌ Fix Required
```

### CI Jobs

**1. Lint and Format**
```yaml
- ruff check src/ tests/
- black --check src/ tests/
- isort --check-only src/ tests/
```

**2. Static Analysis**
```yaml
- mypy src/ --strict
```

**3. Security Scan**
```yaml
- bandit -r src/
- pip-audit
```

**4. Run Tests**
```yaml
- pytest --cov=src --cov-fail-under=80
```

**5. Build Check**
```yaml
- docker build -f Dockerfile.production
```

### Coverage Enforcement

**The pipeline will fail if**:
- Code coverage drops below 80%
- Any test fails
- Linting errors exist
- Type checking fails
- Security vulnerabilities found

### Deployment Pipeline

Triggered on merge to main:

```
Merge to Main → Build Image → Deploy Staging → Manual Approval → Deploy Production
```

---

## Test Coverage

### Viewing Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html

# Terminal report
pytest --cov=src --cov-report=term-missing

# XML for CI
pytest --cov=src --cov-report=xml
```

### Coverage Reports

**Terminal Output**:
```
---------- coverage: platform linux, python 3.12 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
src/auth/__init__.py                  5      0   100%
src/auth/security.py                 45      2    96%   89-90
src/auth/dependencies.py             32      1    97%   65
src/auth/router.py                   28      0   100%
---------------------------------------------------------------
TOTAL                               110      3    97%
```

### Coverage Goals by Module

| Module | Target | Status |
|--------|--------|--------|
| Authentication | >90% | ✅ 97% |
| API Endpoints | >85% | ✅ 89% |
| Services | >80% | ✅ 83% |
| Utils | >80% | ✅ 86% |

---

## Best Practices

### DO ✅

1. **Test Behavior, Not Implementation**
   ```python
   # Good - tests behavior
   def test_user_can_login():
       result = login("user", "pass")
       assert result.success is True

   # Bad - tests implementation details
   def test_login_calls_hash_function():
       assert hash_called == True
   ```

2. **Use Descriptive Names**
   ```python
   # Good
   def test_login_fails_with_invalid_password():
       pass

   # Bad
   def test_login_2():
       pass
   ```

3. **One Assertion Per Concept**
   ```python
   # Good
   def test_user_creation_sets_username():
       user = create_user("testuser")
       assert user.username == "testuser"

   def test_user_creation_sets_email():
       user = create_user("test", email="test@example.com")
       assert user.email == "test@example.com"
   ```

4. **Use Factories for Test Data**
   ```python
   # Good
   user = UserFactory(username="specific_user")

   # Bad
   user = {"username": "user", "email": "...", ...}
   ```

5. **Mock External Dependencies**
   ```python
   # Good - mock external API
   @patch('src.api.client.requests.get')
   def test_fetch_data(mock_get):
       mock_get.return_value.json.return_value = {"data": []}
   ```

### DON'T ❌

1. **Don't Test Third-Party Code**
2. **Don't Share State Between Tests**
3. **Don't Use Sleep for Timing**
4. **Don't Mock Everything in Integration Tests**
5. **Don't Skip Failing Tests** - Fix them!

---

## Troubleshooting

### Common Issues

**Issue: Tests fail with "ModuleNotFoundError"**
```bash
# Solution: Install package in editable mode
poetry install
```

**Issue: "No fixtures found"**
```bash
# Solution: Ensure conftest.py is in correct location
tests/conftest.py  # Must exist
```

**Issue: Database tests fail**
```bash
# Solution: Start test database
docker-compose up -d postgres redis
```

**Issue: Coverage too low**
```bash
# Solution: Identify untested code
pytest --cov=src --cov-report=term-missing
# Look at "Missing" column
```

**Issue: Async tests not running**
```python
# Solution: Add pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_function():
    pass
```

**Issue: Tests are slow**
```bash
# Solution: Run only fast tests
pytest -m "not slow"

# Or use parallel execution
pytest -n 4
```

---

## Additional Resources

### Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Guide](https://pytest-cov.readthedocs.io/)
- [factory_boy Documentation](https://factoryboy.readthedocs.io/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)

### Internal Docs
- [conftest.py](../tests/conftest.py) - Global fixtures
- [factories.py](../tests/factories.py) - Test data factories
- [pyproject.toml](../pyproject.toml) - pytest configuration

### Example Tests
- [Unit Tests](../tests/unit/auth/test_security_unit.py)
- [Integration Tests](../tests/integration/auth/test_auth_integration.py)
- [E2E Tests](../tests/e2e/auth/test_auth_user_journeys.py)

---

## Contributing

When adding new features:

1. ✅ Write tests FIRST (TDD)
2. ✅ Follow the Testing Pyramid (70/20/10)
3. ✅ Ensure >80% coverage
4. ✅ Use existing fixtures and factories
5. ✅ Add markers (`@pytest.mark.*`)
6. ✅ Verify CI passes

**Remember**: Tests are first-class code. Write them well!

---

*Last Updated: 2025-01-30*
*Version: 1.0.0*
