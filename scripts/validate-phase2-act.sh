#!/bin/bash
# PAKE System - Phase 2 Validation Script
# This script validates the act setup and tests local GitHub Actions simulation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"

    log_info "Running test: $test_name"

    if eval "$test_command"; then
        log_success "✓ $test_name passed"
        ((TESTS_PASSED++))
    else
        log_error "✗ $test_name failed"
        ((TESTS_FAILED++))
    fi
    echo
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    run_test "Docker installation" "command -v docker"
    run_test "Docker running" "docker info > /dev/null 2>&1"

    # Check act
    run_test "act installation" "command -v act"
    run_test "act version" "act --version > /dev/null 2>&1"

    # Check configuration files
    run_test ".actrc exists" "test -f .actrc"
    run_test ".secrets exists" "test -f .secrets"
    run_test ".vars exists" "test -f .vars"

    # Check file permissions
    run_test ".secrets permissions" "test -r .secrets"
    run_test ".vars permissions" "test -r .vars"
}

# Test workflow discovery
test_workflow_discovery() {
    log_info "Testing workflow discovery..."

    # Check if workflows exist
    run_test "Workflows directory exists" "test -d .github/workflows"

    # Count workflows
    local workflow_count=$(find .github/workflows -name "*.yml" -o -name "*.yaml" | wc -l)
    run_test "Workflows found ($workflow_count)" "test $workflow_count -gt 0"

    # Test act list command
    run_test "act list command" "act -l > /dev/null 2>&1"
}

# Test individual jobs
test_individual_jobs() {
    log_info "Testing individual job execution..."

    # Test lint job (should be fast and reliable)
    run_test "Lint job execution" "act -j lint-and-format --dry-run > /dev/null 2>&1"

    # Test static analysis job
    run_test "Static analysis job" "act -j static-analysis --dry-run > /dev/null 2>&1"

    # Test security scan job
    run_test "Security scan job" "act -j security-scan --dry-run > /dev/null 2>&1"
}

# Test with services
test_service_jobs() {
    log_info "Testing jobs with services..."

    # Start test services
    log_info "Starting test services..."

    # Start PostgreSQL
    if ! docker ps | grep -q postgres-test; then
        docker run -d --name postgres-test \
            -e POSTGRES_USER=test_user \
            -e POSTGRES_PASSWORD=test_password \
            -e POSTGRES_DB=pake_test \
            -p 5432:5432 \
            postgres:16-alpine > /dev/null 2>&1

        # Wait for PostgreSQL to be ready
        sleep 5
        log_success "PostgreSQL test service started"
    fi

    # Start Redis
    if ! docker ps | grep -q redis-test; then
        docker run -d --name redis-test \
            -p 6379:6379 \
            redis:7-alpine > /dev/null 2>&1

        # Wait for Redis to be ready
        sleep 2
        log_success "Redis test service started"
    fi

    # Test service connectivity
    run_test "PostgreSQL connectivity" "docker exec postgres-test pg_isready > /dev/null 2>&1"
    run_test "Redis connectivity" "docker exec redis-test redis-cli ping > /dev/null 2>&1"

    # Test integration job with services
    run_test "Integration tests job" "act -j integration-tests --dry-run > /dev/null 2>&1"
}

# Test secrets and variables
test_secrets_variables() {
    log_info "Testing secrets and variables..."

    # Check if secrets file has required values
    run_test "GITHUB_TOKEN in secrets" "grep -q 'GITHUB_TOKEN=' .secrets"
    run_test "DATABASE_URL in secrets" "grep -q 'DATABASE_URL=' .secrets"
    run_test "SECRET_KEY in secrets" "grep -q 'SECRET_KEY=' .secrets"

    # Check if vars file has required values
    run_test "ENVIRONMENT in vars" "grep -q 'ENVIRONMENT=' .vars"
    run_test "DEBUG in vars" "grep -q 'DEBUG=' .vars"
    run_test "API_BASE_URL in vars" "grep -q 'API_BASE_URL=' .vars"
}

# Test runner images
test_runner_images() {
    log_info "Testing runner images..."

    # Check if runner images are available
    run_test "Ubuntu 22.04 runner" "docker image inspect catthehacker/ubuntu:full-22.04 > /dev/null 2>&1"
    run_test "Ubuntu 20.04 runner" "docker image inspect catthehacker/ubuntu:full-20.04 > /dev/null 2>&1"
}

# Test act configuration
test_act_configuration() {
    log_info "Testing act configuration..."

    # Test .actrc configuration
    run_test ".actrc has runner images" "grep -q 'catthehacker/ubuntu:full-22.04' .actrc"
    run_test ".actrc has secret file" "grep -q '--secret-file .secrets' .actrc"
    run_test ".actrc has var file" "grep -q '--var-file .vars' .actrc"
    run_test ".actrc has verbose flag" "grep -q '--verbose' .actrc"
}

# Performance test
test_performance() {
    log_info "Testing performance..."

    # Test act startup time
    local start_time=$(date +%s)
    act --version > /dev/null 2>&1
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $duration -lt 5 ]; then
        log_success "✓ act startup time acceptable ($duration seconds)"
        ((TESTS_PASSED++))
    else
        log_warning "⚠ act startup time slow ($duration seconds)"
        ((TESTS_FAILED++))
    fi
    echo
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test resources..."

    # Stop and remove test containers
    docker stop postgres-test redis-test 2>/dev/null || true
    docker rm postgres-test redis-test 2>/dev/null || true

    log_success "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting Phase 2 Validation Tests"
    echo "=================================="

    # Set up cleanup trap
    trap cleanup EXIT

    # Run all tests
    check_prerequisites
    test_workflow_discovery
    test_act_configuration
    test_secrets_variables
    test_runner_images
    test_individual_jobs
    test_service_jobs
    test_performance

    # Print results
    echo "=================================="
    log_info "Test Results Summary:"
    log_success "Passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Failed: $TESTS_FAILED"
    else
        log_success "Failed: $TESTS_FAILED"
    fi

    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "🎉 All tests passed! Phase 2 setup is working correctly."
        log_info "You can now use act to simulate GitHub Actions locally."
        log_info "Try running: act -l (to list jobs) or act -j lint-and-format (to test a job)"
    else
        log_error "❌ Some tests failed. Please check the errors above and fix them."
        log_info "Refer to the debugging guide: docs/PHASE_2_ENVIRONMENTAL_PARITY_GUIDE.md"
        exit 1
    fi
}

# Run main function
main "$@"
