#!/bin/bash

# PAKE System - Comprehensive CI Environment Testing Script
# Provides comprehensive testing capabilities for CI environment simulation
#
# This script offers multiple testing modes:
# - Unit tests with CI constraints
# - Integration tests with resource limits
# - Performance tests under CI conditions
# - Flaky test detection
# - Resource usage monitoring

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
REPORTS_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Default configuration
RUNNER_TYPE="${1:-ubuntu-latest}"
TEST_MODE="${2:-all}"
VERBOSE="${3:-false}"
PARALLEL_WORKERS="${4:-1}"

# GitHub Actions Runner Specifications
declare -A RUNNER_SPECS=(
    ["ubuntu-latest"]="2 7g"
    ["ubuntu-22.04"]="2 7g"
    ["ubuntu-20.04"]="2 7g"
    ["windows-latest"]="2 7g"
    ["windows-2022"]="2 7g"
    ["macos-latest"]="3 14g"
    ["macos-13"]="3 14g"
    ["macos-12"]="3 14g"
)

# Extract CPU and memory specs
IFS=' ' read -r CPU_LIMIT MEMORY_LIMIT <<< "${RUNNER_SPECS[$RUNNER_TYPE]}"

# Function to display help
show_help() {
    echo -e "${BLUE}PAKE System - Comprehensive CI Environment Testing${NC}"
    echo ""
    echo "Usage: $0 [RUNNER_TYPE] [TEST_MODE] [VERBOSE] [PARALLEL_WORKERS]"
    echo ""
    echo "Available Runner Types:"
    for runner in "${!RUNNER_SPECS[@]}"; do
        IFS=' ' read -r cpu mem <<< "${RUNNER_SPECS[$runner]}"
        echo "  - $runner: ${cpu} CPU cores, ${mem} RAM"
    done
    echo ""
    echo "Available Test Modes:"
    echo "  all              - Run all test suites (default)"
    echo "  unit             - Run unit tests only"
    echo "  integration      - Run integration tests only"
    echo "  e2e              - Run end-to-end tests only"
    echo "  performance      - Run performance tests only"
    echo "  security         - Run security tests only"
    echo "  flaky            - Run flaky test detection"
    echo "  smoke            - Run smoke tests only"
    echo "  ci-sensitive     - Run CI-sensitive tests only"
    echo "  resource-intensive - Run resource-intensive tests only"
    echo ""
    echo "Options:"
    echo "  VERBOSE          - Enable verbose output (true/false, default: false)"
    echo "  PARALLEL_WORKERS - Number of parallel workers (default: 1)"
    echo ""
    echo "Examples:"
    echo "  $0 ubuntu-latest all false 1"
    echo "  $0 macos-latest unit true 2"
    echo "  $0 windows-latest performance false 1"
}

# Function to create directories
setup_directories() {
    echo -e "${BLUE}Setting up directories...${NC}"
    mkdir -p "$LOG_DIR"
    mkdir -p "$REPORTS_DIR"
    mkdir -p "$REPORTS_DIR/ci-simulation-$TIMESTAMP"
}

# Function to validate environment
validate_environment() {
    echo -e "${BLUE}Validating environment...${NC}"

    # Check required tools
    local required_tools=("python" "pytest" "docker" "docker-compose")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            echo -e "${RED}Error: $tool is not installed${NC}"
            exit 1
        fi
    done

    # Check Python packages
    if ! python -c "import pytest, psutil, pytest_cov" &> /dev/null; then
        echo -e "${RED}Error: Required Python packages not installed${NC}"
        echo "Please install: pytest, psutil, pytest-cov"
        exit 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        exit 1
    fi

    echo -e "${GREEN}Environment validation passed${NC}"
}

# Function to set CI environment variables
set_ci_environment() {
    echo -e "${BLUE}Setting CI environment variables...${NC}"

    export CI=true
    export GITHUB_ACTIONS=true
    export PYTEST_WORKERS=$PARALLEL_WORKERS
    export PYTEST_TIMEOUT=300
    export PYTEST_MAX_FAILURES=3
    export LOG_LEVEL=info
    export ENVIRONMENT=ci-simulation

    # Runner-specific environment variables
    case $RUNNER_TYPE in
        ubuntu-*)
            export OS=ubuntu
            export PLATFORM=linux
            ;;
        windows-*)
            export OS=windows
            export PLATFORM=win32
            ;;
        macos-*)
            export OS=macos
            export PLATFORM=darwin
            ;;
    esac

    echo "  CI: $CI"
    echo "  GITHUB_ACTIONS: $GITHUB_ACTIONS"
    echo "  PYTEST_WORKERS: $PYTEST_WORKERS"
    echo "  OS: $OS"
    echo "  PLATFORM: $PLATFORM"
}

# Function to run unit tests
run_unit_tests() {
    echo -e "${BLUE}Running unit tests with CI constraints...${NC}"

    local test_args=(
        "tests/unit/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/unit-test-results.xml"
        "--cov=src"
        "--cov-report=xml:$REPORTS_DIR/ci-simulation-$TIMESTAMP/unit-coverage.xml"
        "--cov-report=html:$REPORTS_DIR/ci-simulation-$TIMESTAMP/unit-htmlcov"
        "--cov-fail-under=80"
        "-m" "unit"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    if [[ $PARALLEL_WORKERS -gt 1 ]]; then
        test_args+=("-n" "$PARALLEL_WORKERS")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to run integration tests
run_integration_tests() {
    echo -e "${BLUE}Running integration tests with CI constraints...${NC}"

    local test_args=(
        "tests/integration/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/integration-test-results.xml"
        "--cov=src"
        "--cov-report=xml:$REPORTS_DIR/ci-simulation-$TIMESTAMP/integration-coverage.xml"
        "--cov-report=html:$REPORTS_DIR/ci-simulation-$TIMESTAMP/integration-htmlcov"
        "--cov-fail-under=80"
        "-m" "integration"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    if [[ $PARALLEL_WORKERS -gt 1 ]]; then
        test_args+=("-n" "$PARALLEL_WORKERS")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to run end-to-end tests
run_e2e_tests() {
    echo -e "${BLUE}Running end-to-end tests with CI constraints...${NC}"

    local test_args=(
        "tests/e2e/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/e2e-test-results.xml"
        "--cov=src"
        "--cov-report=xml:$REPORTS_DIR/ci-simulation-$TIMESTAMP/e2e-coverage.xml"
        "--cov-report=html:$REPORTS_DIR/ci-simulation-$TIMESTAMP/e2e-htmlcov"
        "--cov-fail-under=80"
        "-m" "e2e"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    # E2E tests typically run with single worker
    python -m pytest "${test_args[@]}"
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running performance tests with CI constraints...${NC}"

    local test_args=(
        "tests/performance/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/performance-test-results.xml"
        "-m" "performance"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    # Performance tests typically run with single worker
    python -m pytest "${test_args[@]}"
}

# Function to run security tests
run_security_tests() {
    echo -e "${BLUE}Running security tests with CI constraints...${NC}"

    local test_args=(
        "tests/security/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/security-test-results.xml"
        "-m" "security"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to run flaky test detection
run_flaky_test_detection() {
    echo -e "${BLUE}Running flaky test detection...${NC}"

    # Install pytest-rerunfailures if not available
    if ! python -c "import pytest_rerunfailures" &> /dev/null; then
        echo "Installing pytest-rerunfailures..."
        pip install pytest-rerunfailures
    fi

    local test_args=(
        "tests/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "--reruns=3"
        "--reruns-delay=1"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/flaky-test-results.xml"
        "-m" "flaky"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to run smoke tests
run_smoke_tests() {
    echo -e "${BLUE}Running smoke tests with CI constraints...${NC}"

    local test_args=(
        "tests/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/smoke-test-results.xml"
        "-m" "smoke"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to run CI-sensitive tests
run_ci_sensitive_tests() {
    echo -e "${BLUE}Running CI-sensitive tests...${NC}"

    local test_args=(
        "tests/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/ci-sensitive-test-results.xml"
        "-m" "ci-sensitive"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to run resource-intensive tests
run_resource_intensive_tests() {
    echo -e "${BLUE}Running resource-intensive tests with CI constraints...${NC}"

    local test_args=(
        "tests/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/resource-intensive-test-results.xml"
        "-m" "resource-intensive"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    # Resource-intensive tests typically run with single worker
    python -m pytest "${test_args[@]}"
}

# Function to run all tests
run_all_tests() {
    echo -e "${BLUE}Running all test suites with CI constraints...${NC}"

    local test_args=(
        "tests/"
        "-v"
        "--tb=short"
        "--maxfail=3"
        "--durations=5"
        "--disable-warnings"
        "--timeout=300"
        "--timeout-method=thread"
        "-x"
        "--junitxml=$REPORTS_DIR/ci-simulation-$TIMESTAMP/all-test-results.xml"
        "--cov=src"
        "--cov-report=xml:$REPORTS_DIR/ci-simulation-$TIMESTAMP/all-coverage.xml"
        "--cov-report=html:$REPORTS_DIR/ci-simulation-$TIMESTAMP/all-htmlcov"
        "--cov-fail-under=80"
    )

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=("--showlocals" "--tb=long")
    fi

    if [[ $PARALLEL_WORKERS -gt 1 ]]; then
        test_args+=("-n" "$PARALLEL_WORKERS")
    fi

    python -m pytest "${test_args[@]}"
}

# Function to generate test report
generate_test_report() {
    echo -e "${BLUE}Generating test report...${NC}"

    local report_file="$REPORTS_DIR/ci-simulation-$TIMESTAMP/test-report.md"

    cat > "$report_file" << EOF
# PAKE System - CI Simulation Test Report

## Test Configuration
- **Runner Type**: $RUNNER_TYPE
- **CPU Cores**: $CPU_LIMIT
- **Memory**: $MEMORY_LIMIT
- **Test Mode**: $TEST_MODE
- **Parallel Workers**: $PARALLEL_WORKERS
- **Timestamp**: $TIMESTAMP

## Test Results
EOF

    # Add test results from XML files
    if [[ -f "$REPORTS_DIR/ci-simulation-$TIMESTAMP/all-test-results.xml" ]]; then
        echo "### All Tests" >> "$report_file"
        echo "Results available in: all-test-results.xml" >> "$report_file"
    fi

    if [[ -f "$REPORTS_DIR/ci-simulation-$TIMESTAMP/unit-test-results.xml" ]]; then
        echo "### Unit Tests" >> "$report_file"
        echo "Results available in: unit-test-results.xml" >> "$report_file"
    fi

    if [[ -f "$REPORTS_DIR/ci-simulation-$TIMESTAMP/integration-test-results.xml" ]]; then
        echo "### Integration Tests" >> "$report_file"
        echo "Results available in: integration-test-results.xml" >> "$report_file"
    fi

    if [[ -f "$REPORTS_DIR/ci-simulation-$TIMESTAMP/e2e-test-results.xml" ]]; then
        echo "### End-to-End Tests" >> "$report_file"
        echo "Results available in: e2e-test-results.xml" >> "$report_file"
    fi

    echo "" >> "$report_file"
    echo "## Coverage Reports" >> "$report_file"
    echo "Coverage reports available in: htmlcov/" >> "$report_file"

    echo -e "${GREEN}Test report generated: $report_file${NC}"
}

# Function to cleanup
cleanup() {
    echo -e "${BLUE}Cleaning up...${NC}"

    # Remove temporary files
    rm -f pytest.ini.tmp

    # Stop any running containers
    docker-compose -f docker-compose.ci-simulation.yml down -v 2>/dev/null || true
    docker-compose -f docker-compose.macos-ci.yml down -v 2>/dev/null || true
    docker-compose -f docker-compose.windows-ci.yml down -v 2>/dev/null || true

    echo -e "${GREEN}Cleanup completed${NC}"
}

# Function to validate runner type
validate_runner() {
    if [[ ! ${RUNNER_SPECS[$RUNNER_TYPE]+_} ]]; then
        echo -e "${RED}Error: Invalid runner type '$RUNNER_TYPE'${NC}"
        echo "Available runners: ${!RUNNER_SPECS[*]}"
        exit 1
    fi
}

# Main execution function
main() {
    echo -e "${PURPLE}PAKE System - Comprehensive CI Environment Testing${NC}"
    echo -e "${PURPLE}=================================================${NC}"
    echo ""

    validate_runner
    setup_directories
    validate_environment
    set_ci_environment

    echo -e "${CYAN}Test Configuration:${NC}"
    echo "  Runner Type: $RUNNER_TYPE"
    echo "  CPU Cores: $CPU_LIMIT"
    echo "  Memory: $MEMORY_LIMIT"
    echo "  Test Mode: $TEST_MODE"
    echo "  Parallel Workers: $PARALLEL_WORKERS"
    echo "  Verbose: $VERBOSE"
    echo ""

    # Run tests based on mode
    case $TEST_MODE in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        e2e)
            run_e2e_tests
            ;;
        performance)
            run_performance_tests
            ;;
        security)
            run_security_tests
            ;;
        flaky)
            run_flaky_test_detection
            ;;
        smoke)
            run_smoke_tests
            ;;
        ci-sensitive)
            run_ci_sensitive_tests
            ;;
        resource-intensive)
            run_resource_intensive_tests
            ;;
        all)
            run_all_tests
            ;;
        *)
            echo -e "${RED}Error: Invalid test mode '$TEST_MODE'${NC}"
            show_help
            exit 1
            ;;
    esac

    generate_test_report
    cleanup

    echo -e "${GREEN}CI environment testing completed successfully${NC}"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"
