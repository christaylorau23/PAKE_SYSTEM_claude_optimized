# PAKE System - Engineering Best Practices Documentation

## Overview

This document synthesizes the key findings from the PAKE System remediation initiative and establishes engineering best practices to prevent the recurrence of critical bug classes. These practices are derived from the forensic analysis of F821 and DTZ errors and the implementation of automated prevention mechanisms.

## Table of Contents

1. [Context Management Best Practices](#context-management-best-practices)
2. [Timezone Handling Standards](#timezone-handling-standards)
3. [Structured Logging Standards](#structured-logging-standards)
4. [Security Best Practices](#security-best-practices)
5. [Code Quality Standards](#code-quality-standards)
6. [CI/CD Integration Guidelines](#cicd-integration-guidelines)
7. [Architectural Review Process](#architectural-review-process)

## Context Management Best Practices

### Execution Context in Web Frameworks

#### Flask Context Management

**Problem**: Flask uses "context locals" - proxies bound to specific request data on a per-thread basis. Accessing these proxies outside an active request context raises a `RuntimeError`.

**Anti-Pattern**:
```python
# ❌ WRONG - Accessing request directly in helper function
def process_user_data():
    user_id = request.json.get('user_id')  # F821 error - request not defined
    return process_data(user_id)
```

**Correct Pattern**:
```python
# ✅ CORRECT - Pass context explicitly
def process_user_data(request_data):
    user_id = request_data.get('user_id')
    return process_data(user_id)

# In route handler
@app.route('/api/process', methods=['POST'])
def api_process():
    return process_user_data(request.json)
```

#### Django Context Management

**Problem**: Django passes `HttpRequest` as the first argument to view functions. Accessing this object from utility modules without passing it down causes F821 errors.

**Anti-Pattern**:
```python
# ❌ WRONG - Accessing request from utility module
def utility_function():
    user_id = request.user.id  # F821 error - request not defined
    return process_data(user_id)
```

**Correct Pattern**:
```python
# ✅ CORRECT - Pass request explicitly
def utility_function(request):
    user_id = request.user.id
    return process_data(user_id)

# In view
def my_view(request):
    return utility_function(request)
```

#### **kwargs Handling

**Problem**: Developers sometimes assume kwargs keys are automatically unpacked as local variables.

**Anti-Pattern**:
```python
# ❌ WRONG - Assuming kwargs keys are local variables
def process_data(**kwargs):
    return f"Processing {data_type}"  # F821 error - data_type not defined
```

**Correct Pattern**:
```python
# ✅ CORRECT - Access kwargs explicitly
def process_data(**kwargs):
    data_type = kwargs.get('data_type', 'unknown')
    return f"Processing {data_type}"
```

### Context Propagation Guidelines

1. **Explicit Parameter Passing**: Always pass context objects (request, session, etc.) as explicit parameters
2. **Context Managers**: Use context managers for request-scoped operations
3. **Dependency Injection**: Consider dependency injection patterns for complex context requirements
4. **Documentation**: Document context requirements in function signatures and docstrings

## Timezone Handling Standards

### The datetime.utcnow() Anti-Pattern

**Problem**: `datetime.utcnow()` returns naive datetime objects without timezone information, causing ambiguity and incorrect calculations across timezones.

**Anti-Pattern**:
```python
# ❌ WRONG - Creates naive datetime objects
from datetime import datetime
now = datetime.utcnow()  # DTZ005 violation
timestamp = datetime.fromtimestamp(1234567890)  # DTZ004 violation
```

**Correct Pattern**:
```python
# ✅ CORRECT - Use timezone-aware datetime objects
from datetime import datetime, timezone
now = datetime.now(timezone.utc)  # Timezone-aware
timestamp = datetime.fromtimestamp(1234567890, tz=timezone.utc)  # Timezone-aware
```

### Modern Python Timezone Best Practices

#### Python 3.9+ (Recommended)
```python
from zoneinfo import ZoneInfo
from datetime import datetime

# UTC timezone
utc_now = datetime.now(ZoneInfo("UTC"))

# Local timezone
local_now = datetime.now(ZoneInfo("America/New_York"))

# Convert between timezones
utc_time = datetime.now(ZoneInfo("UTC"))
local_time = utc_time.astimezone(ZoneInfo("America/New_York"))
```

#### Python 3.8 and Earlier
```python
from datetime import datetime, timezone
import pytz

# UTC timezone
utc_now = datetime.now(timezone.utc)

# Local timezone
local_tz = pytz.timezone("America/New_York")
local_now = datetime.now(local_tz)
```

### Timezone Handling Guidelines

1. **Always Use Timezone-Aware Objects**: Never create naive datetime objects
2. **Explicit Timezone Specification**: Always specify timezone when creating datetime objects
3. **UTC for Storage**: Store all timestamps in UTC in the database
4. **Local Timezone for Display**: Convert to local timezone only for user display
5. **Consistent Timezone Handling**: Use the same timezone handling pattern throughout the application

## Structured Logging Standards

### Migration from Traditional Logging

**Anti-Pattern**:
```python
# ❌ WRONG - F-string logging (G004 violation)
import logging
logger = logging.getLogger(__name__)
logger.info(f"User {user_id} logged in")  # Inefficient and unstructured
```

**Correct Pattern**:
```python
# ✅ CORRECT - Structured logging with structlog
import structlog
logger = structlog.get_logger(__name__)
logger.info("user_logged_in", user_id=user_id)  # Structured and efficient
```

### Structured Logging Best Practices

#### 1. Event-Based Messages
```python
# Use descriptive event names instead of sentences
logger.info("user_authentication_success", user_id=user_id, method="oauth")
logger.error("database_connection_failed", host=host, port=port, error=str(e))
```

#### 2. Contextual Logging
```python
# Bind context at the beginning of processes
import structlog.contextvars

with structlog.contextvars.bound_contextvars(
    request_id="req-123",
    user_id="user-456",
    correlation_id="corr-789"
):
    logger.info("Processing request")  # Automatically includes context
    logger.info("Another log message")  # Same context included
```

#### 3. Specialized Logging Methods
```python
# Use specialized logging methods for different event types
logger.security("login_attempt", user_id=user_id, ip=ip, success=True)
logger.audit("resource_access", user_id=user_id, resource="/api/data", action="read")
logger.performance("query_executed", operation="SELECT", duration_ms=150.5)
```

#### 4. Error Logging
```python
# Include exception information
try:
    risky_operation()
except Exception as e:
    logger.error("operation_failed", operation="risky_operation", error=str(e), exc_info=True)
```

### Logging Configuration

Use the centralized structlog configuration:

```python
from src.services.logging.centralized_structlog_config import initialize_logging

# Initialize once at application startup
logger = initialize_logging(
    service_name="my-service",
    environment="production",
    log_level="INFO",
    json_format=True
)
```

## Security Best Practices

### Static Analysis Security Testing (SAST)

#### Bandit Integration
The PAKE system integrates Bandit SAST tool with proper suppression policies to avoid alert fatigue.

**S311 - Random Module Usage**:
```python
# ❌ WRONG - Using random for security purposes
import random
token = ''.join(random.choices(string.ascii_letters, k=32))  # S311 violation
```

```python
# ✅ CORRECT - Use secrets module for security
import secrets
token = secrets.token_urlsafe(32)  # Cryptographically secure
```

**S603 - Subprocess Usage**:
```python
# ❌ WRONG - Unreviewed subprocess call
import subprocess
result = subprocess.run(['ls', '-la'])  # S603 violation
```

```python
# ✅ CORRECT - Explicitly reviewed and suppressed
import subprocess
result = subprocess.run(['ls', '-la'])  # nosec B603 - Safe command, no user input
```

#### Security Suppression Policy

For any subprocess call deemed safe upon review, developers must add:
```python
# nosec B603 - Brief justification for why this is safe
```

This transforms noisy warnings into deliberate, auditable security decisions.

### Security Guidelines

1. **Never Use Random for Security**: Always use `secrets` module for tokens, passwords, keys
2. **Review All Subprocess Calls**: Add explicit suppression comments for safe subprocess usage
3. **Input Validation**: Validate all external inputs
4. **Secret Management**: Never commit secrets to version control
5. **Audit Logging**: Log all security-relevant events

## Code Quality Standards

### Ruff Configuration

The PAKE system uses a comprehensive ruff ruleset designed to prevent the specific bug classes that caused production failures:

#### Critical Bug Prevention Rules
- **F821**: UndefinedName - Prevents undefined variable usage
- **DTZ003**: CallDatetimeNowWithoutTzinfo - Prevents naive datetime objects
- **DTZ004**: CallDatetimeFromtimestampWithoutTzinfo - Prevents naive datetime objects
- **DTZ005**: CallDatetimeUTCNow - Forbids datetime.utcnow()
- **G004**: LoggingFString - Discourages f-strings in logs

#### Code Quality Rules
- **B**: flake8-bugbear - Catches common bugs
- **C4**: flake8-comprehensions - Enforces better comprehensions
- **UP**: pyupgrade - Suggests modern Python syntax
- **SIM**: flake8-simplify - Simplifies code
- **S**: flake8-bandit - Security checks

### Code Quality Guidelines

1. **Type Annotations**: Use comprehensive type hints
2. **Error Handling**: Implement proper exception handling
3. **Documentation**: Document all public APIs
4. **Testing**: Maintain high test coverage
5. **Performance**: Consider performance implications of code changes

## CI/CD Integration Guidelines

### Quality Gate Implementation

The PAKE system implements a comprehensive quality gate in the CI/CD pipeline:

#### Required Checks
1. **Linting**: Ruff check with comprehensive ruleset
2. **Formatting**: Ruff format check
3. **Security**: Bandit, Safety, and pip-audit scans
4. **Structured Logging**: Validation of logging configuration
5. **DateTime Timezone**: Validation of timezone handling
6. **Integration Tests**: End-to-end functionality tests

#### Quality Gate Policy
- **All checks must pass** for code to be merged
- **No exceptions** for critical bug prevention rules (F821, DTZ005, G004)
- **Security violations** must be explicitly reviewed and suppressed
- **Performance regressions** are flagged but don't block merges

### Pre-commit Hooks

Configure pre-commit hooks to run quality checks locally:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/]
```

## Architectural Review Process

### Context Propagation Checkpoint

All new system designs must explicitly document:

#### 1. Execution Context Management
- How request data is passed between components
- How session information is managed
- How context is propagated through service layers

#### 2. Temporal Context Management
- How timezone information is handled
- How datetime objects are created and manipulated
- How time-sensitive operations are managed

#### 3. Logging Strategy
- How structured logging is implemented
- How contextual information is captured
- How security events are logged

### Review Checklist

#### Design Phase
- [ ] Context propagation strategy documented
- [ ] Timezone handling approach specified
- [ ] Logging strategy defined
- [ ] Security considerations addressed

#### Implementation Phase
- [ ] Context passed explicitly between components
- [ ] Timezone-aware datetime objects used
- [ ] Structured logging implemented
- [ ] Security checks integrated

#### Testing Phase
- [ ] Context propagation tested
- [ ] Timezone handling validated
- [ ] Logging output verified
- [ ] Security scans passed

### Architectural Decision Records (ADRs)

Document all architectural decisions using ADRs:

```markdown
# ADR-001: Context Propagation Strategy

## Status
Accepted

## Context
The PAKE system experienced F821 errors due to improper context management.

## Decision
All context objects (request, session, etc.) must be passed explicitly as parameters.

## Consequences
- Positive: Eliminates F821 errors, improves code clarity
- Negative: More verbose function signatures
```

## Implementation Timeline

### Phase 1: Immediate Stabilization (Completed)
- [x] Automated F821 error remediation
- [x] Automated DTZ error remediation
- [x] System stability restored

### Phase 2: Systemic Hardening (In Progress)
- [x] Centralized structlog configuration
- [x] Automated log call refactoring codemod
- [ ] Seamless integration with existing logging
- [ ] Contextual logging implementation
- [ ] Bandit SAST integration

### Phase 3: Prophylactic Fortification (In Progress)
- [x] Comprehensive ruff ruleset configuration
- [x] GitHub Actions quality workflow
- [ ] Engineering best practices documentation
- [ ] Architectural review process updates

## Conclusion

These engineering best practices represent a comprehensive approach to preventing the recurrence of critical bug classes in the PAKE system. By implementing these standards and integrating them into the development workflow, we ensure that:

1. **F821 errors are prevented** through explicit context management
2. **DTZ errors are eliminated** through timezone-aware datetime handling
3. **Code quality is maintained** through comprehensive linting and formatting
4. **Security vulnerabilities are caught** through automated scanning
5. **System observability is improved** through structured logging

The key to success is the integration of these practices into the CI/CD pipeline, creating an automated quality gate that enforces best practices and prevents the introduction of similar defects in the future.
