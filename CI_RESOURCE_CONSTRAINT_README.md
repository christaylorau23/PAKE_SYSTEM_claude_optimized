# PAKE System - CI Resource Constraint Replication

## Overview

This directory contains comprehensive tools and configurations for replicating GitHub Actions runner resource constraints locally. This system helps identify timing-sensitive bugs, race conditions, and performance issues that only surface under the slower, more resource-constrained conditions of CI environments.

## Quick Start

### 1. Setup Environment
```bash
# Install required dependencies
make -f Makefile.ci ci-setup

# Validate setup
make -f Makefile.ci ci-validate
```

### 2. Run Basic CI Simulation
```bash
# Simulate ubuntu-latest runner (2 CPU cores, 7GB RAM)
make -f Makefile.ci ci-simulate

# Simulate macos-latest runner (3 CPU cores, 14GB RAM)
make -f Makefile.ci ci-macos

# Simulate windows-latest runner (2 CPU cores, 7GB RAM)
make -f Makefile.ci ci-windows
```

### 3. Run Comprehensive Testing
```bash
# Run all tests with CI constraints
make -f Makefile.ci ci-test

# Run specific test suites
make -f Makefile.ci ci-unit
make -f Makefile.ci ci-integration
make -f Makefile.ci ci-performance
```

## Available Tools

### 1. CI Resource Simulation Script
**File**: `scripts/ci-resource-simulation.sh`

Main script for simulating GitHub Actions runner limitations.

```bash
# Basic usage
./scripts/ci-resource-simulation.sh [RUNNER_TYPE] [ACTION]

# Examples
./scripts/ci-resource-simulation.sh ubuntu-latest docker-test
./scripts/ci-resource-simulation.sh macos-latest pytest-ci
./scripts/ci-resource-simulation.sh windows-latest monitor
```

**Available Actions**:
- `docker-test` - Run tests in resource-constrained Docker container
- `pytest-ci` - Run pytest with CI-parallelism settings
- `docker-build` - Build Docker image with resource constraints
- `monitor` - Monitor resource usage during tests
- `validate` - Validate CI environment simulation

### 2. Comprehensive Testing Script
**File**: `scripts/ci-comprehensive-testing.sh`

Advanced testing script with multiple test modes and comprehensive reporting.

```bash
# Basic usage
./scripts/ci-comprehensive-testing.sh [RUNNER_TYPE] [TEST_MODE] [VERBOSE] [PARALLEL_WORKERS]

# Examples
./scripts/ci-comprehensive-testing.sh ubuntu-latest all false 1
./scripts/ci-comprehensive-testing.sh macos-latest unit true 2
./scripts/ci-comprehensive-testing.sh windows-latest performance false 1
```

**Available Test Modes**:
- `all` - Run all test suites
- `unit` - Run unit tests only
- `integration` - Run integration tests only
- `e2e` - Run end-to-end tests only
- `performance` - Run performance tests only
- `security` - Run security tests only
- `flaky` - Run flaky test detection
- `smoke` - Run smoke tests only
- `ci-sensitive` - Run CI-sensitive tests only
- `resource-intensive` - Run resource-intensive tests only

### 3. Docker Compose Configurations

#### Ubuntu Runner Simulation
**File**: `docker-compose.ci-simulation.yml`

Simulates ubuntu-latest runner (2 CPU cores, 7GB RAM).

```bash
docker-compose -f docker-compose.ci-simulation.yml up --build --abort-on-container-exit
```

#### macOS Runner Simulation
**File**: `docker-compose.macos-ci.yml`

Simulates macos-latest runner (3 CPU cores, 14GB RAM).

```bash
docker-compose -f docker-compose.macos-ci.yml up --build --abort-on-container-exit
```

#### Windows Runner Simulation
**File**: `docker-compose.windows-ci.yml`

Simulates windows-latest runner (2 CPU cores, 7GB RAM).

```bash
docker-compose -f docker-compose.windows-ci.yml up --build --abort-on-container-exit
```

### 4. pytest Configurations

#### Main Configuration
**File**: `pytest.ini`

Enhanced with CI-specific markers and settings.

#### CI-Specific Configuration
**File**: `pytest-ci.ini`

Optimized for CI environment simulation.

#### CI Plugin
**File**: `src/utils/pytest_ci_plugin.py`

Custom pytest plugin for CI environment detection and resource monitoring.

### 5. Makefile Commands
**File**: `Makefile.ci`

Easy-to-use commands for CI simulation.

```bash
# Basic commands
make -f Makefile.ci help                    # Show help
make -f Makefile.ci ci-simulate            # Run basic simulation
make -f Makefile.ci ci-test                 # Run comprehensive testing
make -f Makefile.ci ci-monitor              # Monitor resources
make -f Makefile.ci ci-validate             # Validate setup
make -f Makefile.ci ci-clean                # Clean up resources

# Runner-specific shortcuts
make -f Makefile.ci ci-ubuntu               # ubuntu-latest simulation
make -f Makefile.ci ci-macos                # macos-latest simulation
make -f Makefile.ci ci-windows              # windows-latest simulation
make -f Makefile.ci ci-all-runners          # All runners

# Test-specific shortcuts
make -f Makefile.ci ci-unit                 # Unit tests
make -f Makefile.ci ci-integration           # Integration tests
make -f Makefile.ci ci-e2e                   # End-to-end tests
make -f Makefile.ci ci-performance           # Performance tests
make -f Makefile.ci ci-security              # Security tests
make -f Makefile.ci ci-flaky                 # Flaky test detection
make -f Makefile.ci ci-smoke                 # Smoke tests
```

## GitHub Actions Runner Specifications

### Standard Runner Types

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

### Comprehensive Testing
```bash
# Run all tests with CI constraints
make -f Makefile.ci ci-test RUNNER_TYPE=ubuntu-latest TEST_MODE=all

# Run specific test suites
make -f Makefile.ci ci-unit RUNNER_TYPE=macos-latest
make -f Makefile.ci ci-performance RUNNER_TYPE=windows-latest
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

## File Structure

```
PAKE_SYSTEM_claude_optimized/
├── scripts/
│   ├── ci-resource-simulation.sh          # Main CI simulation script
│   └── ci-comprehensive-testing.sh         # Comprehensive testing script
├── docker-compose.ci-simulation.yml       # Ubuntu runner simulation
├── docker-compose.macos-ci.yml            # macOS runner simulation
├── docker-compose.windows-ci.yml          # Windows runner simulation
├── pytest.ini                             # Enhanced pytest configuration
├── pytest-ci.ini                          # CI-specific pytest configuration
├── src/utils/
│   └── pytest_ci_plugin.py               # CI-specific pytest plugin
├── Makefile.ci                            # Easy-to-use CI commands
└── docs/
    └── CI_RESOURCE_CONSTRAINT_GUIDE.md    # Comprehensive documentation
```

## Dependencies

### Required Tools
- **Docker**: Container runtime
- **Docker Compose**: Container orchestration
- **Python 3.12+**: Runtime environment
- **pytest**: Testing framework
- **psutil**: System resource monitoring

### Required Python Packages
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel test execution
- `pytest-timeout` - Test timeout handling
- `psutil` - System resource monitoring
- `pytest-rerunfailures` - Flaky test detection (optional)

## Contributing

When contributing to the CI resource constraint replication system:

1. **Follow Existing Patterns**: Use established patterns and conventions
2. **Add Tests**: Include tests for new functionality
3. **Update Documentation**: Keep documentation current
4. **Test Across Runners**: Verify functionality across different runner types
5. **Monitor Performance**: Ensure changes don't impact performance

## Support

For issues or questions related to CI resource constraint replication:

1. **Check Documentation**: Review `docs/CI_RESOURCE_CONSTRAINT_GUIDE.md`
2. **Run Validation**: Use `make -f Makefile.ci ci-validate`
3. **Check Logs**: Review logs in `logs/` directory
4. **Monitor Resources**: Use `make -f Makefile.ci ci-monitor`

## License

This CI resource constraint replication system is part of the PAKE System and follows the same licensing terms.
