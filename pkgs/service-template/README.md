# PAKE Service Template

This is a production-ready template for creating new microservices in the PAKE System. It follows enterprise-grade best practices and includes comprehensive tooling for development, testing, and deployment.

## Features

- **FastAPI Framework**: Modern, fast web framework with automatic API documentation
- **Poetry Dependency Management**: Reliable dependency management with lock files
- **Docker Multi-stage Build**: Optimized containerization for production deployment
- **Comprehensive Testing**: Unit, integration, and end-to-end test configurations
- **Code Quality Tools**: Black, isort, Ruff, MyPy, and pre-commit hooks
- **Security Scanning**: Bandit, Safety, and container security scanning
- **Monitoring & Observability**: Prometheus metrics, structured logging, and health checks
- **Database Integration**: SQLAlchemy with async support and Alembic migrations
- **Caching**: Redis integration for high-performance caching
- **Authentication**: JWT-based authentication with secure token handling

## Quick Start

### 1. Create New Service

```bash
# Copy the template to create a new service
cp -r pkgs/service-template services/my-new-service
cd services/my-new-service

# Update the service name in pyproject.toml
sed -i 's/pake-service-template/my-new-service/g' pyproject.toml
```

### 2. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with dev

# Install pre-commit hooks
poetry run pre-commit install
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 4. Run the Service

```bash
# Development mode
poetry run python app/main.py

# Or with uvicorn directly
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test types
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m e2e
```

## Project Structure

```
my-new-service/
├── app/                          # Application code
│   ├── api/                      # API routes and endpoints
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── router.py         # Main API router
│   │       └── endpoints/        # Individual endpoint modules
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database connection and setup
│   │   ├── logging.py           # Structured logging setup
│   │   └── middleware.py         # Custom middleware
│   ├── models/                   # Database models
│   │   ├── __init__.py
│   │   └── base.py              # Base model classes
│   ├── schemas/                  # Pydantic schemas
│   │   ├── __init__.py
│   │   └── base.py              # Base schema classes
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   └── base.py              # Base service classes
│   └── main.py                   # FastAPI application entry point
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                     # End-to-end tests
├── alembic/                      # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── .env.example                 # Environment variables template
├── .pre-commit-config.yaml      # Pre-commit hooks configuration
├── Dockerfile                    # Multi-stage Docker build
├── docker-compose.yml           # Local development with Docker
├── pyproject.toml               # Poetry configuration and dependencies
└── README.md                    # This file
```

## Configuration

The service uses environment-based configuration with sensible defaults. Key configuration options:

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Service name | "PAKE Service" |
| `ENVIRONMENT` | Environment (dev/staging/production) | "development" |
| `DEBUG` | Enable debug mode | False |
| `SECRET_KEY` | JWT secret key | Required |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `LOG_LEVEL` | Logging level | "INFO" |

### Configuration Management

Configuration is managed through Pydantic settings with validation:

```python
from app.core.config import get_settings

settings = get_settings()
print(settings.PROJECT_NAME)
```

## API Documentation

Once the service is running, API documentation is automatically available:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Testing Strategy

The service follows a comprehensive testing strategy:

### Test Types

1. **Unit Tests (70%)**: Test individual functions and methods in isolation
2. **Integration Tests (20%)**: Test service-to-service interactions
3. **End-to-End Tests (10%)**: Test complete user workflows

### Test Markers

```bash
# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e          # End-to-end tests only
pytest -m slow         # Slow tests only
```

### Test Configuration

- **Coverage**: Minimum 80% code coverage required
- **Parallel Execution**: Tests run in parallel for faster execution
- **Fixtures**: Comprehensive test fixtures for common scenarios
- **Mocking**: External dependencies are mocked in unit tests

## Code Quality

The service enforces high code quality standards:

### Pre-commit Hooks

Automatically run on every commit:
- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Bandit**: Security linting
- **Safety**: Dependency vulnerability scanning

### Manual Quality Checks

```bash
# Format code
poetry run black app/ tests/

# Sort imports
poetry run isort app/ tests/

# Run linter
poetry run ruff check app/ tests/

# Type checking
poetry run mypy app/

# Security scan
poetry run bandit -r app/
poetry run safety check
```

## Docker Deployment

### Multi-stage Build

The Dockerfile uses a multi-stage build for optimal production images:

1. **Builder Stage**: Install dependencies and build artifacts
2. **Production Stage**: Copy only runtime dependencies and application code

### Security Features

- **Non-root User**: Runs as `pake` user for security
- **Minimal Base Image**: Uses `python:3.12-slim` for smaller attack surface
- **Health Checks**: Built-in health check endpoint
- **No Cache**: Disabled pip cache to reduce image size

### Building and Running

```bash
# Build image
docker build -t my-new-service:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e REDIS_URL="redis://host:6379" \
  -e SECRET_KEY="your-secret-key" \
  my-new-service:latest
```

## Monitoring and Observability

### Health Checks

- **Health Endpoint**: `GET /health` - Service health status
- **Metrics Endpoint**: `GET /metrics` - Prometheus metrics

### Structured Logging

Uses `structlog` for consistent, structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("User action", user_id=123, action="login")
```

### Prometheus Metrics

Built-in metrics collection:
- HTTP request count and duration
- Database connection pool metrics
- Cache hit/miss ratios
- Custom business metrics

## Database Management

### Migrations

Uses Alembic for database migrations:

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add user table"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

### Models

SQLAlchemy models with async support:

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

## Security Best Practices

### Authentication

- JWT-based authentication with secure token handling
- Password hashing with Argon2
- Rate limiting on API endpoints
- CORS configuration for cross-origin requests

### Input Validation

- Pydantic schemas for request/response validation
- SQL injection prevention with SQLAlchemy ORM
- XSS protection with proper content types

### Secrets Management

- Environment variables for sensitive configuration
- No secrets in code or configuration files
- Secure secret rotation procedures

## Performance Optimization

### Caching

- Redis integration for high-performance caching
- Cache invalidation strategies
- Cache warming for critical data

### Database Optimization

- Connection pooling with SQLAlchemy
- Query optimization with proper indexing
- Async database operations

### Monitoring

- Performance metrics collection
- Slow query detection
- Resource usage monitoring

## Deployment

### Kubernetes

The service is designed for Kubernetes deployment with:
- Health checks and readiness probes
- Resource limits and requests
- Horizontal pod autoscaling
- Service mesh integration

### CI/CD Integration

- Automated testing in CI pipeline
- Security scanning and vulnerability detection
- Container image scanning
- Automated deployment to staging/production

## Contributing

1. Follow the established code style and patterns
2. Write comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all pre-commit hooks pass
5. Follow the PR template for code reviews

## Support

For questions or issues:
- Check the [PAKE System Documentation](../docs/)
- Review existing [GitHub Issues](https://github.com/your-org/pake-system/issues)
- Contact the PAKE Team: team@pake-system.com
