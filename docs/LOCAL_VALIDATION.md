# PAKE System - Local Validation Guide

## Overview

This guide provides comprehensive instructions for running all CI/CD quality checks locally before pushing code to GitHub. This ensures a green build and eliminates the inefficient "push to see if it passes" development loop.

## Quick Start

### 1. Run All Checks Locally
```bash
# Run complete local validation (recommended)
python scripts/local_validation.py

# Run quick validation (lint, format, type-check only)
python scripts/local_validation.py --quick

# Run with verbose output
python scripts/local_validation.py --verbose

# Skip tests for faster validation
python scripts/local_validation.py --skip-tests
```

### 2. Simulate Full CI/CD Pipeline
```bash
# Simulate entire GitHub Actions pipeline
python scripts/simulate_cicd.py

# Run specific pipeline stages
python scripts/simulate_cicd.py --stages lint-and-format static-analysis

# Quick pipeline simulation
python scripts/simulate_cicd.py --quick
```

### 3. Pre-commit Hooks (Automatic)
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff
```

## Validation Scripts

### Individual Quality Gate Scripts

#### 1. Lint Validation (`scripts/validate_lint.py`)
Runs all linting checks: Ruff, Black, isort, ESLint, Prettier

```bash
# Run all linting checks
python scripts/validate_lint.py

# Auto-fix linting issues
python scripts/validate_lint.py --fix

# Run specific tool
python scripts/validate_lint.py --tool ruff
python scripts/validate_lint.py --tool black
python scripts/validate_lint.py --tool eslint
```

#### 2. Type Check Validation (`scripts/validate_type_check.py`)
Runs MyPy and TypeScript type checking

```bash
# Run all type checks
python scripts/validate_type_check.py

# Run specific tool
python scripts/validate_type_check.py --tool mypy
python scripts/validate_type_check.py --tool typescript
```

#### 3. Security Validation (`scripts/validate_security.py`)
Runs comprehensive security checks

```bash
# Run all security checks
python scripts/validate_security.py

# Run specific tool
python scripts/validate_security.py --tool bandit
python scripts/validate_security.py --tool pip-audit
python scripts/validate_security.py --tool gitleaks

# Save security report
python scripts/validate_security.py --report-file security-report.json
```

#### 4. Test Validation (`scripts/validate_tests.py`)
Runs comprehensive test suite

```bash
# Run all tests
python scripts/validate_tests.py

# Run specific test type
python scripts/validate_tests.py --test-type unit
python scripts/validate_tests.py --test-type integration
python scripts/validate_tests.py --test-type e2e

# Run tests in parallel
python scripts/validate_tests.py --parallel
```

## Pre-commit Hooks Configuration

### Optimized Hook Order
The pre-commit hooks are configured for optimal performance:

1. **Fast Formatting & Linting** (Run first for quick feedback)
   - General file checks (trailing whitespace, end-of-file, etc.)
   - Ruff linting and formatting
   - Black formatting (backup)
   - isort import sorting

2. **Type Checking & Static Analysis** (Medium speed)
   - MyPy type checking

3. **Security Scanning** (Slower but critical)
   - detect-secrets
   - gitleaks
   - Bandit security analysis

4. **Frontend Code Quality**
   - ESLint for TypeScript/JavaScript
   - Prettier for frontend formatting

5. **Custom Security & Validation Checks**
   - Hardcoded secrets check
   - Environment variable validation
   - Security audit
   - Dependency vulnerability check

### Hook Usage
```bash
# Install hooks
pre-commit install

# Run on staged files (default)
git commit

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff
pre-commit run mypy
pre-commit run bandit

# Skip hooks (not recommended)
git commit --no-verify
```

## CI/CD Pipeline Simulation

### Pipeline Stages
The local simulation runs the same stages as GitHub Actions:

1. **🎨 Code Quality & Formatting** (`lint-and-format`)
2. **🔍 Static Analysis & Type Checking** (`static-analysis`)
3. **🔒 Security Scanning** (`security-scan`)
4. **🧪 Unit Tests** (`unit-tests`)
5. **🔗 Integration Tests** (`integration-tests`)
6. **🌐 End-to-End Tests** (`e2e-tests`)
7. **🛡️ Security Tests** (`security-tests`)
8. **📊 Test Coverage Gate** (`test-coverage-gate`)
9. **🐳 Build & Container Scan** (`build-and-scan`)

### Usage Examples
```bash
# Run complete pipeline
python scripts/simulate_cicd.py

# Run specific stages
python scripts/simulate_cicd.py --stages lint-and-format static-analysis

# Skip tests for faster validation
python scripts/simulate_cicd.py --skip-tests

# Quick pipeline (lint and type-check only)
python scripts/simulate_cicd.py --quick

# Save detailed report
python scripts/simulate_cicd.py --report-file pipeline-report.json
```

## Prerequisites

### Required Tools
- **Python 3.12+**: Core runtime
- **Poetry**: Python dependency management
- **Node.js 18+**: Frontend development
- **npm**: Node.js package management

### Optional Tools (for full pipeline)
- **Docker**: Container building and scanning
- **Trivy**: Container vulnerability scanning
- **gitleaks**: Git history secret scanning

### Installation Commands
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Node.js (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Install Docker
# Follow instructions at https://docs.docker.com/get-docker/

# Install Trivy
# Follow instructions at https://aquasecurity.github.io/trivy/latest/getting-started/installation/

# Install gitleaks
# Follow instructions at https://github.com/gitleaks/gitleaks#installation
```

## Environment Setup

### Environment Variables
The validation scripts automatically set up test environment variables:

```bash
SECRET_KEY=test-secret-key-for-local-validation
DATABASE_URL=postgresql://test:test@localhost/pake_test
REDIS_URL=redis://localhost:6379/1
USE_VAULT=false
```

### Database Setup (for integration tests)
```bash
# Start PostgreSQL
docker run -d --name pake-postgres \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=pake_test \
  -p 5432:5432 \
  postgres:16-alpine

# Start Redis
docker run -d --name pake-redis \
  -p 6379:6379 \
  redis:7-alpine
```

## Troubleshooting

### Common Issues

#### 1. Linting Failures
```bash
# Auto-fix most issues
python scripts/validate_lint.py --fix

# Run specific tools
python scripts/validate_lint.py --tool ruff --fix
python scripts/validate_lint.py --tool black --fix
python scripts/validate_lint.py --tool isort --fix
```

#### 2. Type Check Failures
```bash
# Run with verbose output to see specific errors
python scripts/validate_type_check.py --verbose

# Check specific files
poetry run mypy src/specific_file.py --strict
```

#### 3. Security Scan Failures
```bash
# Review security issues
python scripts/validate_security.py --verbose

# Update vulnerable dependencies
poetry update
npm audit fix

# Fix hardcoded secrets
poetry run detect-secrets scan --baseline .secrets.baseline
```

#### 4. Test Failures
```bash
# Run specific test categories
python scripts/validate_tests.py --test-type unit --verbose

# Run tests in parallel for speed
python scripts/validate_tests.py --parallel

# Check test coverage
poetry run pytest tests/ --cov=src --cov-report=html
```

#### 5. Pre-commit Hook Failures
```bash
# Run hooks manually to see errors
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify

# Update hook versions
pre-commit autoupdate
```

### Performance Optimization

#### 1. Faster Validation
```bash
# Skip tests for quick feedback
python scripts/local_validation.py --skip-tests

# Run only linting and formatting
python scripts/local_validation.py --categories lint format

# Use parallel execution
python scripts/validate_tests.py --parallel
```

#### 2. Pre-commit Optimization
```bash
# Run only fast hooks
pre-commit run ruff black isort

# Skip slow hooks during development
pre-commit run --hook-stage manual
```

#### 3. CI/CD Simulation Optimization
```bash
# Run quick pipeline
python scripts/simulate_cicd.py --quick

# Skip test stages
python scripts/simulate_cicd.py --skip-tests

# Run specific stages only
python scripts/simulate_cicd.py --stages lint-and-format static-analysis
```

## Best Practices

### 1. Development Workflow
1. **Before coding**: Run `python scripts/local_validation.py --quick`
2. **During development**: Use pre-commit hooks for automatic checks
3. **Before committing**: Run `python scripts/local_validation.py`
4. **Before pushing**: Run `python scripts/simulate_cicd.py`

### 2. Pre-commit Hook Usage
- Install hooks: `pre-commit install`
- Let hooks run automatically on commit
- Fix issues immediately when hooks fail
- Use `--no-verify` only in emergencies

### 3. Validation Script Usage
- Use `--fix` flags to auto-fix issues
- Use `--verbose` for debugging
- Save reports with `--report-file` for analysis
- Run specific tools for targeted fixes

### 4. CI/CD Simulation
- Run full simulation before major changes
- Use quick simulation for daily development
- Save reports for team review
- Fix all failures before pushing

## Integration with IDE

### VS Code Configuration
Add to `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm Configuration
1. Enable Ruff as external tool
2. Configure Black as code formatter
3. Enable MyPy type checking
4. Set up pre-commit hook integration

## Monitoring and Reporting

### Report Generation
```bash
# Generate comprehensive report
python scripts/local_validation.py --report-file validation-report.json

# Generate security report
python scripts/validate_security.py --report-file security-report.json

# Generate test report
python scripts/validate_tests.py --report-file test-report.json

# Generate pipeline report
python scripts/simulate_cicd.py --report-file pipeline-report.json
```

### Report Analysis
Reports include:
- Execution summary with success rates
- Detailed results for each tool/stage
- Error messages and recommendations
- Performance metrics and timing
- Coverage information (for tests)

## Support and Maintenance

### Updating Validation Scripts
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update Python dependencies
poetry update

# Update Node.js dependencies
npm update
```

### Adding New Validation Tools
1. Add tool to appropriate validation script
2. Update pre-commit configuration
3. Update CI/CD pipeline simulation
4. Update documentation

### Troubleshooting Support
- Check script output with `--verbose` flag
- Review generated reports
- Consult individual tool documentation
- Check GitHub Actions logs for comparison

## Conclusion

Local validation ensures code quality and prevents CI/CD failures. Use the provided scripts and pre-commit hooks to maintain a green build and efficient development workflow.

For questions or issues, refer to the troubleshooting section or consult the project documentation.
