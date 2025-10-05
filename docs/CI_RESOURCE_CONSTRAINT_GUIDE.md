# PAKE System - CI Resource Constraint Replication Guide

## Overview

This guide provides comprehensive documentation and tools for replicating GitHub Actions runner resource constraints locally. This is essential for identifying timing-sensitive bugs, race conditions, and performance issues that only surface under the slower, more resource-constrained conditions of CI environments.

## GitHub Actions Runner Specifications

### Standard Runner Types and Resources

| Runner Type | CPU Cores | RAM | Storage | Network | Notes |
|-------------|-----------|-----|---------|---------|-------|
| `ubuntu-latest` | 2 | 7 GB | 14 GB SSD | 1 Gbps | Most common for Linux |
| `ubuntu-22.04` | 2 | 7 GB | 14 GB SSD | 1 Gbps | Ubuntu 22.04 LTS |
| `ubuntu-20.04` | 2 | 7 GB | 14 GB SSD | 1 Gbps | Ubuntu 20.04 LTS |
| `windows-latest` | 2 | 7 GB | 14 GB SSD | 1 Gbps | Windows Server 2022 |
| `windows-2022` | 2 | 7 GB | 14 GB SSD | 1 Gbps | Windows Server 2022 |
| `macos-latest` | 3 | 14 GB | 14 GB SSD | 1 Gbps | macOS 13 |
| `macos-13` | 3 | 14 GB | 14 GB SSD | 1 Gbps | macOS 13 |
| `macos-12` | 3 | 14 GB | 14 GB SSD | 1 Gbps | macOS 12 |

### Private Repository Runners

Private repositories have access to the same runner specifications as public repositories, but with additional considerations:

- **Concurrent Jobs**: Limited by your GitHub plan
- **Job Timeout**: 6 hours maximum
- **Queue Time**: May experience longer wait times during peak usage

### Performance Characteristics

#### CPU Performance
- **Clock Speed**: Variable, typically 2.1-2.6 GHz
- **Architecture**: x64 (AMD64)
- **Load Average**: Can spike during concurrent jobs
- **Context Switching**: Higher overhead in virtualized environment

#### Memory Performance
- **Available RAM**: ~6.5 GB usable (after OS overhead)
- **Swap**: Limited swap space
- **Memory Pressure**: Can cause performance degradation
- **Garbage Collection**: More frequent GC cycles under memory pressure

#### I/O Performance
- **Storage**: SSD with ~500 MB/s sequential read/write
- **Network**: 1 Gbps bandwidth with variable latency
- **File System**: Can become fragmented during long-running jobs

## Common CI-Specific Issues

### 1. Race Conditions
**Problem**: Tests pass locally but fail in CI due to timing differences.

**Symptoms**:
- Intermittent test failures
- Tests that depend on execution order
- Async operations completing out of expected order

**Solutions**:
- Use proper synchronization primitives
- Implement retry mechanisms with exponential backoff
- Add explicit waits for async operations

### 2. Memory Pressure
**Problem**: Tests fail due to insufficient memory or memory leaks.

**Symptoms**:
- OutOfMemoryError exceptions
- Slow test execution
- Tests timing out

**Solutions**:
- Optimize memory usage in tests
- Use memory profiling tools
- Implement proper cleanup in test teardown

### 3. Resource Contention
**Problem**: Tests fail due to resource conflicts between parallel processes.

**Symptoms**:
- Port conflicts
- File locking issues
- Database connection limits

**Solutions**:
- Use unique ports for each test
- Implement proper resource cleanup
- Use test-specific databases

### 4. Timing Sensitivity
**Problem**: Tests fail due to slower execution in CI environment.

**Symptoms**:
- Timeout errors
- Tests that depend on specific timing
- Network request timeouts

**Solutions**:
- Increase timeout values for CI
- Use adaptive timeouts based on environment
- Implement proper retry logic

## Local Simulation Strategies

### 1. Docker Resource Constraints

#### CPU Limiting
```bash
# Limit to 2 CPU cores (ubuntu-latest equivalent)
docker run --cpus="2" your-image

# Limit to specific CPU cores
docker run --cpuset-cpus="0,1" your-image
```

#### Memory Limiting
```bash
# Limit to 7GB RAM (ubuntu-latest equivalent)
docker run --memory="7g" your-image

# Set memory reservation
docker run --memory="7g" --memory-reservation="5g" your-image
```

#### Combined Constraints
```bash
# Full ubuntu-latest simulation
docker run --cpus="2" --memory="7g" your-image
```

### 2. Test Parallelism Simulation

#### pytest-xdist Configuration
```ini
# pytest.ini
[tool:pytest]
addopts = -n auto  # Use all available cores locally
```

#### CI-Specific Configuration
```bash
# Simulate CI parallelism (1-2 workers max)
pytest -n 1  # Single worker (most restrictive)
pytest -n 2  # Two workers (ubuntu-latest equivalent)
```

#### Jest Configuration
```bash
# Simulate CI worker limitations
jest --maxWorkers=1  # Single worker
jest --maxWorkers=2  # Two workers
```

### 3. System Resource Simulation

#### CPU Throttling
```bash
# Use cpulimit to throttle CPU usage
cpulimit -l 50 -p $(pgrep python)  # Limit to 50% CPU
```

#### Memory Pressure
```bash
# Create memory pressure
stress-ng --vm 1 --vm-bytes 2G --timeout 60s
```

## Implementation in PAKE System

### 1. CI Resource Simulation Script

The main simulation script (`scripts/ci-resource-simulation.sh`) provides:

- **Runner Type Selection**: Choose specific GitHub Actions runner
- **Resource Constraint Application**: Apply CPU and memory limits
- **Test Execution**: Run tests under CI-like conditions
- **Monitoring**: Track resource usage during execution

### 2. Docker Compose CI Simulation

```yaml
# docker-compose.ci-simulation.yml
version: '3.8'
services:
  postgres-ci:
    image: postgres:15-alpine
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1g
  redis-ci:
    image: redis:7-alpine
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256m
  pake-test-ci:
    build: .
    deploy:
      resources:
        limits:
          cpus: '2'      # ubuntu-latest equivalent
          memory: 7g      # ubuntu-latest equivalent
```

### 3. pytest CI Configuration

```ini
# pytest-ci.ini
[tool:pytest]
minversion = 7.0
addopts = -vv -rA --showlocals --tb=native --strict-markers --maxfail=5 --durations=10
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests that test individual components in isolation
    integration: Integration tests that test interactions between components
    e2e: End-to-end tests that test the entire system
    slow: Tests that take a long time to run
    ci-sensitive: Tests that are sensitive to CI environment conditions
```

## Usage Examples

### Basic CI Simulation
```bash
# Simulate ubuntu-latest runner
./scripts/ci-resource-simulation.sh ubuntu-latest docker-test

# Simulate macos-latest runner
./scripts/ci-resource-simulation.sh macos-latest pytest-ci
```

### Advanced Testing
```bash
# Run with resource monitoring
./scripts/ci-resource-simulation.sh ubuntu-latest monitor

# Validate simulation setup
./scripts/ci-resource-simulation.sh ubuntu-latest validate
```

### Custom Resource Constraints
```bash
# Custom CPU and memory limits
docker run --cpus="1.5" --memory="5g" -e PYTEST_WORKERS=1 your-test-image
```

## Best Practices

### 1. Test Design
- **Avoid Timing Dependencies**: Don't rely on specific execution timing
- **Use Proper Synchronization**: Implement proper async/await patterns
- **Clean Up Resources**: Ensure proper cleanup in test teardown
- **Handle Failures Gracefully**: Implement retry mechanisms

### 2. Resource Management
- **Monitor Resource Usage**: Track CPU, memory, and I/O usage
- **Optimize Test Performance**: Minimize resource consumption
- **Use Appropriate Timeouts**: Set realistic timeout values
- **Implement Circuit Breakers**: Handle resource exhaustion gracefully

### 3. CI-Specific Considerations
- **Environment Variables**: Use CI-specific environment variables
- **Logging**: Implement comprehensive logging for debugging
- **Artifacts**: Save test results and logs as artifacts
- **Notifications**: Set up proper failure notifications

## Troubleshooting

### Common Issues

#### Tests Pass Locally but Fail in CI
1. **Check Resource Constraints**: Ensure local simulation matches CI
2. **Review Timing**: Look for timing-dependent code
3. **Check Dependencies**: Verify all dependencies are available
4. **Review Logs**: Check CI logs for specific error messages

#### Performance Degradation
1. **Monitor Resources**: Track CPU, memory, and I/O usage
2. **Optimize Code**: Look for performance bottlenecks
3. **Review Dependencies**: Check for inefficient dependencies
4. **Profile Tests**: Use profiling tools to identify issues

#### Intermittent Failures
1. **Check Race Conditions**: Look for concurrent access issues
2. **Review Async Code**: Ensure proper async/await usage
3. **Check Resource Cleanup**: Verify proper cleanup
4. **Implement Retries**: Add retry mechanisms for flaky tests

## Monitoring and Metrics

### Key Metrics to Track
- **Test Execution Time**: Compare local vs CI execution times
- **Resource Usage**: Monitor CPU, memory, and I/O usage
- **Failure Rate**: Track test failure rates in different environments
- **Flaky Test Detection**: Identify tests that fail intermittently

### Tools and Techniques
- **Docker Stats**: Monitor container resource usage
- **pytest-benchmark**: Benchmark test performance
- **Memory Profiling**: Use memory profiling tools
- **CI Analytics**: Analyze CI performance metrics

## Conclusion

Replicating CI resource constraints locally is essential for maintaining test reliability and identifying environment-specific issues. The PAKE System provides comprehensive tools and documentation for simulating GitHub Actions runner limitations, enabling developers to catch issues before they reach CI.

By following the strategies outlined in this guide, teams can:
- Identify timing-sensitive bugs early
- Optimize test performance
- Reduce CI failure rates
- Improve overall system reliability

Remember: The goal is not to make tests slower, but to ensure they work reliably across all environments, including resource-constrained CI systems.
