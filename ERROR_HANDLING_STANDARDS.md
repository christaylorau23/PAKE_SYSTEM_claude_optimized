# PAKE System Error Handling Standards

## Overview

This document establishes standardized error handling patterns for the PAKE System, ensuring consistent, maintainable, and debuggable error handling across all modules.

## Core Principles

### 1. Specific Exception Handling
**Never use broad `except Exception:` blocks**
- Use specific exception types whenever possible
- Handle different error types with appropriate responses
- Preserve error context and stack traces

**Good Examples:**
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise NetworkException(f"Failed to connect to {url}") from e
except requests.Timeout as e:
    logger.error(f"Request timeout: {e}")
    raise TimeoutException(f"Request to {url} timed out") from e
except requests.HTTPError as e:
    logger.error(f"HTTP error {e.response.status_code}: {e}")
    raise APIException(f"API returned {e.response.status_code}") from e
```

**Bad Examples:**
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except Exception as e:  # Too broad!
    logger.error(f"Error: {e}")
    raise
```

### 2. Proper Error Context
**Always provide meaningful error context**
- Include operation details in error messages
- Preserve original exception with `from e`
- Add relevant context information

```python
try:
    data = json.loads(response_text)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON response: {e}")
    raise DataProcessingException(
        f"Invalid JSON in API response: {e}",
        context={"response_length": len(response_text)},
        original_exception=e
    ) from e
```

### 3. Graceful Degradation
**Handle errors gracefully when possible**
- Provide fallback mechanisms
- Log errors for monitoring
- Continue operation when safe

```python
try:
    cached_data = cache.get(key)
except CacheException as e:
    logger.warning(f"Cache miss, falling back to database: {e}")
    cached_data = None

if cached_data is None:
    cached_data = database.fetch(key)
```

### 4. Never Silent Failures
**Avoid try-except-pass blocks**
- Always log exceptions
- Provide meaningful error handling
- Document why exceptions are ignored

**Good:**
```python
try:
    optional_operation()
except OptionalOperationException as e:
    logger.debug(f"Optional operation failed (expected): {e}")
    # Continue gracefully - this operation is optional
```

**Bad:**
```python
try:
    optional_operation()
except Exception:
    pass  # Silent failure - never do this!
```

## Exception Hierarchy

### PAKE System Exceptions
Use the established PAKE exception hierarchy:

```python
from src.utils.exceptions import (
    PAKEException,
    NetworkException,
    DataProcessingException,
    ConfigurationException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    FileNotFoundException,
    ImportException
)
```

### Exception Categories
- **NetworkException**: Connection, timeout, HTTP errors
- **DataProcessingException**: JSON, parsing, data validation errors
- **ConfigurationException**: Settings, environment, configuration errors
- **AuthenticationException**: Login, token, credential errors
- **AuthorizationException**: Permission, access control errors
- **ValidationException**: Input validation, schema validation errors
- **FileNotFoundException**: File system, path resolution errors
- **ImportException**: Module import, dependency errors

## Error Handling Patterns

### 1. API Error Handling
```python
async def api_call(self, endpoint: str, data: dict) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=data) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientConnectionError as e:
        logger.error(f"Connection failed to {endpoint}: {e}")
        raise NetworkException(f"Failed to connect to {endpoint}") from e
    except aiohttp.ClientTimeout as e:
        logger.error(f"Timeout calling {endpoint}: {e}")
        raise TimeoutException(f"Request to {endpoint} timed out") from e
    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP {e.status} error calling {endpoint}: {e}")
        raise APIException(f"API returned {e.status}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from {endpoint}: {e}")
        raise DataProcessingException(f"Invalid response format from {endpoint}") from e
```

### 2. File Operation Error Handling
```python
def load_config_file(self, file_path: Path) -> dict:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Config file not found: {file_path}")
        raise FileNotFoundException(str(file_path)) from e
    except PermissionError as e:
        logger.error(f"Permission denied reading {file_path}: {e}")
        raise FilePermissionException(str(file_path), "read") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise DataProcessingException(f"Invalid JSON in {file_path}") from e
```

### 3. Database Error Handling
```python
async def save_user(self, user: User) -> User:
    try:
        async with self.db_session() as session:
            session.add(user)
            await session.commit()
            return user
    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"User already exists: {user.email}")
        raise ValidationException(f"User {user.email} already exists") from e
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.error(f"Database error saving user: {e}")
        raise DataProcessingException("Failed to save user") from e
```

## Logging Standards

### Error Log Levels
- **ERROR**: System errors, failed operations, exceptions
- **WARNING**: Recoverable issues, fallback operations
- **INFO**: Normal operations, important state changes
- **DEBUG**: Detailed debugging information, exception details

### Log Message Format
```python
logger.error(f"Operation failed: {operation_name} - {error_details}")
logger.warning(f"Fallback activated: {fallback_reason}")
logger.info(f"Operation completed: {operation_name} - {result_summary}")
logger.debug(f"Exception details: {exception_type} - {exception_message}")
```

## Testing Error Handling

### Unit Tests for Error Cases
```python
def test_api_call_connection_error():
    with pytest.raises(NetworkException) as exc_info:
        api_client.api_call("http://invalid-url")
    
    assert "Failed to connect" in str(exc_info.value)
    assert exc_info.value.original_exception is not None

def test_config_file_not_found():
    with pytest.raises(FileNotFoundException):
        config_loader.load_config_file(Path("nonexistent.json"))
```

## Monitoring and Alerting

### Error Metrics
- Track exception rates by type and module
- Monitor error patterns and trends
- Alert on critical error thresholds

### Error Context
- Include correlation IDs in error logs
- Add request/operation context to exceptions
- Preserve stack traces for debugging

## Migration Checklist

When updating existing error handling:

- [ ] Replace broad `except Exception:` with specific exceptions
- [ ] Add proper error context and logging
- [ ] Use PAKE exception hierarchy
- [ ] Preserve original exceptions with `from e`
- [ ] Add unit tests for error cases
- [ ] Update documentation
- [ ] Verify error monitoring works correctly
