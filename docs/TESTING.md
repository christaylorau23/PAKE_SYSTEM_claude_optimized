# 🧪 PAKE System Testing Guide

**Version**: 10.1.0 | **Last Updated**: 2025-09-14

## 📋 Table of Contents

- [Testing Strategy](#testing-strategy)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Performance Testing](#performance-testing)
- [Integration Testing](#integration-testing)
- [CI/CD Testing](#cicd-testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Testing Strategy

### Test Pyramid

```
    /\
   /  \     E2E Tests (5%)
  /____\    
 /      \   Integration Tests (15%)
/________\  
            Unit Tests (80%)
```

### Testing Levels

1. **Unit Tests (80%)**: Individual components and functions
2. **Integration Tests (15%)**: API endpoints and service interactions
3. **End-to-End Tests (5%)**: Complete user workflows

### Quality Gates

- **Minimum Coverage**: 80% overall
- **Critical Services**: 95% coverage required
- **New Features**: 100% coverage required
- **Performance**: All critical paths benchmarked

## 📁 Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── services/           # Service unit tests
│   │   ├── ml/            # ML service tests
│   │   ├── ingestion/     # Ingestion service tests
│   │   └── cache/         # Cache service tests
│   ├── utils/              # Utility function tests
│   └── models/             # Data model tests
├── integration/            # Integration tests
│   ├── api/                # API endpoint tests
│   ├── database/           # Database integration tests
│   └── external/           # External API integration tests
├── e2e/                    # End-to-end tests
│   ├── workflows/          # Complete workflow tests
│   └── performance/        # Performance and load tests
├── fixtures/               # Test data and fixtures
│   ├── sample_data/        # Sample test data
│   └── mock_responses/     # Mock API responses
└── conftest.py            # Pytest configuration
```

## 🚀 Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
python -m pytest tests/e2e/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# Run specific test file
python -m pytest tests/unit/test_semantic_search.py -v

# Run specific test function
python -m pytest tests/unit/test_semantic_search.py::test_enhance_search_results -v
```

### Advanced Test Options

```bash
# Parallel execution
python -m pytest tests/ -n auto

# Stop on first failure
python -m pytest tests/ -x

# Run only failed tests from last run
python -m pytest tests/ --lf

# Run tests matching pattern
python -m pytest tests/ -k "test_search"

# Run performance tests only
python -m pytest tests/ -m performance

# Verbose output with timestamps
python -m pytest tests/ -v -s --durations=10
```

### Test Environment Setup

```bash
# Create test environment
python -m venv test-env
source test-env/bin/activate

# Install test dependencies
pip install -r requirements-test.txt

# Set test environment variables
export TESTING=true
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/pake_test
export REDIS_URL=redis://localhost:6379/1

# Run database migrations for tests
python scripts/setup_test_database.py
```

## 📊 Test Coverage

### Coverage Requirements

| Component | Minimum Coverage | Target Coverage |
|-----------|------------------|-----------------|
| **Core Services** | 95% | 98% |
| **ML Services** | 90% | 95% |
| **API Endpoints** | 85% | 90% |
| **Utilities** | 80% | 85% |
| **Overall** | 80% | 85% |

### Coverage Commands

```bash
# Generate coverage report
python -m pytest tests/ --cov=src --cov-report=html

# View coverage in terminal
python -m pytest tests/ --cov=src --cov-report=term-missing

# Coverage for specific modules
python -m pytest tests/ --cov=src.services.ml --cov-report=html

# Coverage with branch analysis
python -m pytest tests/ --cov=src --cov-branch --cov-report=html
```

### Coverage Analysis

```bash
# View coverage report
open htmlcov/index.html

# Check coverage thresholds
python -m pytest tests/ --cov=src --cov-fail-under=80

# Coverage for new code only
python -m pytest tests/ --cov=src --cov-report=term --cov-report=xml
```

## ⚡ Performance Testing

### Benchmark Tests

```bash
# Run performance benchmarks
python -m pytest tests/e2e/performance/ -v

# Benchmark specific components
python scripts/benchmark_performance.py

# Load testing
python scripts/load_test.py --users=100 --duration=300

# Memory profiling
python -m pytest tests/e2e/performance/test_memory_usage.py --profile
```

### Performance Metrics

| Metric | Target | Critical |
|--------|--------|----------|
| **Search Response** | <1s | <2s |
| **ML Processing** | <100ms | <200ms |
| **Dashboard Load** | <500ms | <1s |
| **Memory Usage** | <512MB | <1GB |
| **CPU Usage** | <50% | <80% |

### Performance Test Examples

```python
# Example performance test
@pytest.mark.performance
async def test_search_performance():
    """Test search performance under load."""
    start_time = time.time()
    
    # Execute concurrent searches
    tasks = [
        search_service.search("test query") 
        for _ in range(10)
    ]
    results = await asyncio.gather(*tasks)
    
    execution_time = time.time() - start_time
    
    assert execution_time < 2.0  # Should complete in under 2 seconds
    assert len(results) == 10     # All searches should succeed
    assert all(r.success for r in results)
```

## 🔗 Integration Testing

### API Integration Tests

```bash
# Test all API endpoints
python -m pytest tests/integration/api/ -v

# Test specific API
python -m pytest tests/integration/api/test_search_api.py -v

# Test with real external APIs
python -m pytest tests/integration/external/ -v --external-apis
```

### Database Integration Tests

```bash
# Test database operations
python -m pytest tests/integration/database/ -v

# Test with test database
python -m pytest tests/integration/database/ --database-url=postgresql://test_user:test_pass@localhost:5432/pake_test
```

### Service Integration Tests

```bash
# Test service interactions
python -m pytest tests/integration/services/ -v

# Test ML service integration
python -m pytest tests/integration/services/test_ml_integration.py -v
```

## 🔄 CI/CD Testing

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-phase7.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python -m pytest tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true
      
      - id: coverage
        name: coverage
        entry: python -m pytest tests/ --cov=src --cov-fail-under=80
        language: system
        pass_filenames: false
        always_run: true
```

## 🐛 Troubleshooting

### Common Test Issues

#### 1. Import Errors

**Problem**: Module import failures
**Solution**:
```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use pytest with proper path
python -m pytest tests/ --import-mode=importlib
```

#### 2. Database Connection Issues

**Problem**: Test database not accessible
**Solution**:
```bash
# Check database status
sudo systemctl status postgresql

# Create test database
sudo -u postgres createdb pake_test

# Grant permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pake_test TO test_user;"
```

#### 3. Redis Connection Issues

**Problem**: Redis not accessible for tests
**Solution**:
```bash
# Start Redis
sudo systemctl start redis-server

# Test connection
redis-cli ping

# Use different Redis database for tests
export REDIS_URL=redis://localhost:6379/1
```

#### 4. External API Failures

**Problem**: External API tests failing
**Solution**:
```bash
# Use mock responses
python -m pytest tests/ --mock-external-apis

# Skip external API tests
python -m pytest tests/ -m "not external"
```

### Test Debugging

```bash
# Run with debug output
python -m pytest tests/ -v -s --tb=long

# Debug specific test
python -m pytest tests/unit/test_semantic_search.py::test_enhance_search_results -v -s --pdb

# Profile test execution
python -m pytest tests/ --profile

# Show slowest tests
python -m pytest tests/ --durations=10
```

### Test Data Management

```bash
# Reset test database
python scripts/reset_test_database.py

# Load test fixtures
python scripts/load_test_fixtures.py

# Clean test cache
python -m pytest tests/ --cache-clear
```

---

## 📞 Support

- **Documentation**: [Complete testing docs](https://github.com/your-org/pake-system/blob/main/docs/)
- **Issues**: [Report test issues](https://github.com/your-org/pake-system/issues)
- **Email**: dev@pake-system.com

---

<div align="center">

**PAKE System Testing Guide** 🧪  
**Version 10.1.0** | **Last Updated**: 2025-09-14

</div>
