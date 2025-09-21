# PAKE System - Continuous Integration Pipeline Guide

## Overview

The PAKE System implements a foundational CI pipeline that acts as a quality gate for all pull requests targeting the main branch. This ensures that no code is merged unless it builds successfully and passes all automated checks.

## Pipeline Configuration

The CI pipeline is defined in `.github/workflows/ci.yml` and follows these core principles:

### 1. **Quality Gate Approach**
- Runs on every pull request to `main` branch
- Prevents merging of broken code
- Ensures consistency across the development team

### 2. **Comprehensive Testing**
- **Python Tests**: Full test suite with pytest
- **TypeScript/JavaScript Tests**: Node.js workspace tests
- **Database Integration**: PostgreSQL and Redis services
- **Environment Setup**: Automated test environment configuration

### 3. **Code Quality Enforcement**
- **Python Linting**: Ruff (modern, fast linter)
- **TypeScript Linting**: ESLint with TypeScript support
- **Code Formatting**: Automated formatting checks
- **Type Checking**: Comprehensive type validation

## Pipeline Steps

### Environment Setup
```yaml
- Checkout repository code
- Setup Python 3.12 environment
- Setup Node.js 22 environment
- Cache dependencies for faster builds
```

### Service Dependencies
- **PostgreSQL 15**: Test database with health checks
- **Redis 7**: Caching service with health checks
- **Automatic Health Monitoring**: Ensures services are ready before tests

### Quality Checks
1. **Dependency Installation**
   - Python: `pip install -r requirements.txt`
   - Node.js: `npm ci` (uses lockfile for consistency)

2. **Linting**
   - Python: `ruff check` and `ruff format --check`
   - TypeScript: `npm run lint:typescript`

3. **Testing**
   - Python: `pytest tests/ -v --tb=short`
   - TypeScript: `npm run test:typescript`

4. **Test Results**
   - Coverage reports uploaded as artifacts
   - Test results available for review

## Key Benefits

### 1. **Consistency**
- Same commands run locally and in CI
- Lockfile ensures identical dependency versions
- Standardized environment across all developers

### 2. **Speed**
- Dependency caching reduces build times
- Parallel service health checks
- Modern tooling (Ruff) for faster linting

### 3. **Reliability**
- Health checks ensure services are ready
- Comprehensive error reporting
- Artifact upload for debugging failed builds

### 4. **Quality Assurance**
- Prevents broken code from reaching main branch
- Enforces coding standards automatically
- Maintains test coverage requirements

## Local Development Alignment

The CI pipeline mirrors local development commands:

```bash
# Local development workflow
npm ci                    # Install dependencies
npm run lint             # Run linting
npm run test             # Run tests
npm run format:check     # Check formatting
```

```yaml
# CI pipeline workflow
- npm ci                  # Install dependencies
- npm run lint:typescript # Run linting
- npm run test:typescript # Run tests
- ruff format --check     # Check formatting
```

## Configuration Files

### Python Configuration
- `pyproject.toml`: Ruff, Black, MyPy, and pytest configuration
- `pytest.ini`: Test discovery and execution settings
- `requirements.txt`: Production dependencies including Ruff

### TypeScript Configuration
- `eslint.config.mjs`: ESLint rules and TypeScript support
- `package.json`: Scripts and workspace configuration
- `tsconfig.json`: TypeScript compiler options

## Troubleshooting

### Common Issues

1. **Service Health Check Failures**
   - Ensure PostgreSQL and Redis are properly configured
   - Check service startup time in logs

2. **Linting Failures**
   - Run `ruff check` locally to identify issues
   - Use `ruff format` to auto-fix formatting issues

3. **Test Failures**
   - Run `pytest tests/ -v` locally
   - Check test database setup and environment variables

### Debug Commands

```bash
# Check local environment
npm run doctor

# Run specific test categories
python -m pytest tests/ -m unit
python -m pytest tests/ -m integration

# Check linting locally
npm run lint:python
npm run lint:typescript

# Format code locally
npm run format:python
npm run format
```

## Best Practices

### 1. **Pre-commit Hooks**
Consider adding pre-commit hooks to catch issues before CI:

```bash
pip install pre-commit
pre-commit install
```

### 2. **Branch Protection**
Configure GitHub branch protection rules:
- Require status checks to pass
- Require up-to-date branches
- Require review from code owners

### 3. **Regular Maintenance**
- Update dependencies regularly
- Monitor CI performance metrics
- Review and update linting rules

## Integration with Development Workflow

The CI pipeline integrates seamlessly with the PAKE System's development workflow:

1. **Feature Development**: Create feature branch
2. **Local Testing**: Run `npm run doctor` to validate locally
3. **Pull Request**: CI automatically runs on PR creation
4. **Quality Gate**: CI must pass before merge approval
5. **Main Branch**: Only tested, linted code reaches main

This ensures that the main branch always contains production-ready code that builds successfully and passes all quality checks.

## Performance Optimization

The pipeline is optimized for speed:

- **Dependency Caching**: Reduces installation time
- **Modern Tooling**: Ruff is significantly faster than flake8/black
- **Parallel Services**: Database and Redis start concurrently
- **Efficient Test Discovery**: pytest automatically finds and runs tests

## Security Considerations

- No secrets in CI configuration
- Environment variables for sensitive data
- Dependency scanning through safety checks
- Secure service communication within GitHub Actions

## Monitoring and Metrics

- Build success/failure rates
- Average build duration
- Test coverage trends
- Linting error frequency

The CI pipeline provides comprehensive visibility into code quality and helps maintain the high standards required for the PAKE System's enterprise-grade knowledge management platform.
