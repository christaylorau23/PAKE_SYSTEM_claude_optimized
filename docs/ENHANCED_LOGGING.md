# Enhanced Application and Test Logging - PAKE System

## Overview

The PAKE System now includes comprehensive logging capabilities that provide detailed insights into application behavior during test runs. This enhancement addresses the critical need to capture application internal log messages when tests fail, making debugging significantly more effective.

## Key Features

### 1. Pytest Logging Configuration

The `pyproject.toml` file now includes comprehensive pytest logging configuration:

```toml
[tool.pytest.ini_options]
# Enhanced logging configuration for test runs
log_cli = true
log_cli_level = "DEBUG"
log_cli_format = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)s)"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"

# Log file configuration for test runs
log_file = "logs/test_run.log"
log_file_level = "DEBUG"
log_file_format = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)s)"
log_file_date_format = "%Y-%m-%d %H:%M:%S"

# Auto-use fixtures for logging
log_auto_indent = true
log_capture = true
log_level = "DEBUG"
```

### 2. Enhanced Test Logging Service

A new `EnhancedTestLoggingService` provides:

- **Structured logging** with context and metadata
- **Performance monitoring** with automatic timing
- **Error tracking** with detailed context
- **Test boundary logging** showing test start/end
- **Integration with pytest** hooks for automatic setup

### 3. Comprehensive Log Capture

The system captures:
- Application internal logs during test execution
- Performance metrics and timing information
- Database operations and API calls
- Security events and business logic
- Error details with full context

## Usage Examples

### Basic Test Logging

```python
def test_basic_logging_with_capture(caplog):
    """Test basic logging with log capture verification"""
    logger = logging.getLogger("test_basic")

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Verify logs were captured
    assert capture_logs.has_info("Info message")
    assert capture_logs.has_warning("Warning message")
    assert capture_logs.has_error("Error message")
```

### Structured Logging

```python
def test_structured_logging(structured_logger):
    """Test structured logging with context and metadata"""
    structured_logger.info(
        "User action performed",
        user_id="12345",
        action="login",
        timestamp="2024-01-01T00:00:00Z",
        metadata={"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"}
    )

    # Log database operation
    structured_logger.log_database(
        "User query executed",
        operation="SELECT",
        table="users",
        duration=0.05,
        row_count=1
    )

    # Log API call
    structured_logger.log_api_call(
        "API request processed",
        method="POST",
        url="/api/v1/users",
        status_code=201,
        duration=0.15
    )
```

### Performance Logging

```python
def test_performance_logging(test_logger):
    """Test performance logging and timing"""
    start_time = time.time()

    # Simulate database operation
    time.sleep(0.01)  # 10ms
    test_logger.log_performance("database_query", time.time() - start_time)

    # Log memory usage (simulated)
    test_logger.info(
        "Memory usage tracked",
        memory_mb=128.5,
        operation="test_operation"
    )
```

### Error Logging with Context

```python
def test_error_logging_with_context(structured_logger):
    """Test error logging with detailed context"""
    try:
        # Simulate an error
        raise ValueError("Test error for logging demonstration")
    except ValueError as e:
        structured_logger.error(
            "Test error occurred",
            error=e,
            context="test_error_logging",
            operation="simulate_error",
            user_id="test_user"
        )
```

## Available Fixtures

### `capture_logs(caplog)`
Enhanced log capturing with helper methods:
- `has_error(message)` - Check if error message was logged
- `has_warning(message)` - Check if warning message was logged
- `has_info(message)` - Check if info message was logged

### `test_logger(request)`
Enhanced test logger with structured logging and context:
- Automatic test context management
- Performance logging capabilities
- Error tracking with context

### `structured_logger`
Structured logger for comprehensive test logging:
- JSON-structured log entries
- Database operation logging
- API call logging
- Business event logging
- Security event logging

## Log Output Format

The logging system produces output in the following format:

```
2024-01-01 12:00:00 [    INFO] test_service: Starting test operation (test_file.py:42)
2024-01-01 12:00:00 [   DEBUG] test_service: Debug information (test_file.py:45)
2024-01-01 12:00:00 [ WARNING] test_service: Warning message (test_file.py:48)
2024-01-01 12:00:00 [   ERROR] test_service: Error occurred (test_file.py:51)
```

## Configuration Options

### Environment Variables

- `LOG_LEVEL` - Set the minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_CONSOLE` - Enable/disable console output (true/false)
- `LOG_FILE` - Enable/disable file logging (true/false)
- `LOG_DIRECTORY` - Directory for log files (default: "logs")

### Pytest Options

- `--log-cli-level=DEBUG` - Set CLI log level
- `--log-cli-format` - Customize CLI log format
- `--log-file` - Specify log file path
- `--log-file-level` - Set file log level

## Benefits

### 1. Enhanced Debugging
- **Complete visibility** into application behavior during tests
- **Detailed error context** with stack traces and metadata
- **Performance insights** showing slow operations

### 2. Better Test Reliability
- **Early detection** of issues through comprehensive logging
- **Easier troubleshooting** when tests fail
- **Performance monitoring** to identify bottlenecks

### 3. Production Readiness
- **Consistent logging** across development and production
- **Structured data** for log analysis and monitoring
- **Security-aware logging** that masks sensitive information

## Integration with CI/CD

The logging configuration works seamlessly with CI/CD pipelines:

```bash
# Run tests with full logging
pytest tests/ -v --log-cli-level=DEBUG --log-file=logs/ci_test_run.log

# Generate detailed reports
pytest tests/ --html=reports/test_report.html --self-contained-html
```

## Best Practices

### 1. Use Appropriate Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about program execution
- **WARNING**: Something unexpected happened but the program continues
- **ERROR**: A serious problem occurred
- **CRITICAL**: A very serious error occurred

### 2. Include Context
Always include relevant context in log messages:
```python
logger.info("User login successful", user_id=user_id, ip=ip_address)
```

### 3. Use Structured Logging
Prefer structured logging over string formatting:
```python
# Good
logger.info("Operation completed", operation="database_query", duration=0.05)

# Avoid
logger.info(f"Database query took {duration} seconds")
```

### 4. Log Performance Metrics
Include timing and resource usage information:
```python
logger.performance("API call completed", duration=0.15, memory_mb=64.2)
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check log level configuration
2. **Missing context**: Ensure structured logging is used
3. **Performance impact**: Use appropriate log levels in production

### Debug Commands

```bash
# Test logging configuration
python scripts/test_logging_configuration.py

# Run tests with verbose logging
pytest tests/ -v -s --log-cli-level=DEBUG

# Check log files
tail -f logs/test_run.log
```

## Conclusion

The enhanced logging system provides comprehensive visibility into application behavior during test execution, making debugging significantly more effective. By capturing application internal logs, performance metrics, and detailed error context, developers can quickly identify and resolve issues when tests fail.

The system integrates seamlessly with pytest and provides both console and file output options, making it suitable for both local development and CI/CD environments.
