#!/bin/bash

# PAKE System - CI Resource Constraint Simulation Script
# Simulates GitHub Actions runner limitations for local testing
#
# This script helps identify timing-sensitive bugs and race conditions
# that only surface under resource-constrained CI environments.

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# GitHub Actions Runner Specifications
# Reference: https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners
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

# Parse arguments
if [[ $# -eq 0 ]] || [[ "$1" == "help" ]]; then
    RUNNER_TYPE="ubuntu-latest"
    ACTION="help"
else
    RUNNER_TYPE="${1:-ubuntu-latest}"
    ACTION="${2:-help}"
fi

# Extract CPU and memory specs (only if not help)
if [[ "$ACTION" != "help" ]]; then
    IFS=' ' read -r CPU_LIMIT MEMORY_LIMIT <<< "${RUNNER_SPECS[$RUNNER_TYPE]}"
fi

# Function to display help
show_help() {
    echo -e "${BLUE}PAKE System - CI Resource Constraint Simulation${NC}"
    echo ""
    echo "Usage: $0 [RUNNER_TYPE] [ACTION]"
    echo ""
    echo "Available Runner Types:"
    for runner in "${!RUNNER_SPECS[@]}"; do
        IFS=' ' read -r cpu mem <<< "${RUNNER_SPECS[$runner]}"
        echo "  - $runner: ${cpu} CPU cores, ${mem} RAM"
    done
    echo ""
    echo "Available Actions:"
    echo "  help          - Show this help message"
    echo "  docker-test   - Run tests in resource-constrained Docker container"
    echo "  pytest-ci     - Run pytest with CI-parallelism settings"
    echo "  docker-build  - Build Docker image with resource constraints"
    echo "  monitor       - Monitor resource usage during tests"
    echo "  validate       - Validate CI environment simulation"
    echo ""
    echo "Examples:"
    echo "  $0 ubuntu-latest docker-test"
    echo "  $0 macos-latest pytest-ci"
    echo "  $0 windows-latest monitor"
}

# Function to validate runner type
validate_runner() {
    if [[ ! ${RUNNER_SPECS[$RUNNER_TYPE]+_} ]]; then
        echo -e "${RED}Error: Invalid runner type '$RUNNER_TYPE'${NC}"
        echo "Available runners: ${!RUNNER_SPECS[*]}"
        exit 1
    fi
}

# Function to run Docker tests with resource constraints
run_docker_test() {
    echo -e "${BLUE}Running tests in resource-constrained Docker container${NC}"
    echo "Runner: $RUNNER_TYPE (${CPU_LIMIT} CPU cores, ${MEMORY_LIMIT} RAM)"

    # Create temporary Docker Compose file for CI simulation
    cat > docker-compose.ci-simulation.yml << EOF
version: '3.8'

services:
  postgres-ci:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: pake_system_test
      POSTGRES_USER: pake_test
      POSTGRES_PASSWORD: test_password
    ports:
      - '5434:5432'
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1g
        reservations:
          cpus: '0.25'
          memory: 512m
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U pake_test -d pake_system_test']
      interval: 10s
      timeout: 5s
      retries: 3

  redis-ci:
    image: redis:7-alpine
    ports:
      - '6381:6379'
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256m
        reservations:
          cpus: '0.1'
          memory: 128m
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 10s
      timeout: 5s
      retries: 3

  pake-test-ci:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://pake_test:test_password@postgres-ci:5432/pake_system_test
      REDIS_URL: redis://redis-ci:6379/0
      JWT_SECRET_KEY: test-secret-key
      ENVIRONMENT: test
      LOG_LEVEL: info
      PYTEST_WORKERS: 1
    depends_on:
      postgres-ci:
        condition: service_healthy
      redis-ci:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '${CPU_LIMIT}'
          memory: ${MEMORY_LIMIT}
        reservations:
          cpus: '1'
          memory: 2g
    command: >
      sh -c "
        echo 'Waiting for services to be ready...' &&
        sleep 10 &&
        echo 'Running tests with CI resource constraints...' &&
        python -m pytest tests/ -v
          --tb=short
          --maxfail=5
          --durations=10
          -x
          --disable-warnings
      "
EOF

    echo -e "${YELLOW}Starting CI simulation environment...${NC}"
    docker-compose -f docker-compose.ci-simulation.yml up --build --abort-on-container-exit

    echo -e "${YELLOW}Cleaning up CI simulation environment...${NC}"
    docker-compose -f docker-compose.ci-simulation.yml down -v
    rm -f docker-compose.ci-simulation.yml

    echo -e "${GREEN}CI simulation completed${NC}"
}

# Function to run pytest with CI-parallelism settings
run_pytest_ci() {
    echo -e "${BLUE}Running pytest with CI-parallelism settings${NC}"
    echo "Runner: $RUNNER_TYPE (${CPU_LIMIT} CPU cores, ${MEMORY_LIMIT} RAM)"

    # Calculate optimal worker count based on CI constraints
    # GitHub Actions runners typically use 1-2 workers max
    if [[ $CPU_LIMIT -eq 2 ]]; then
        WORKERS=1
    elif [[ $CPU_LIMIT -eq 3 ]]; then
        WORKERS=2
    else
        WORKERS=1
    fi

    echo -e "${YELLOW}Using $WORKERS worker(s) to simulate CI environment${NC}"

    # Set environment variables for CI simulation
    export CI=true
    export GITHUB_ACTIONS=true
    export PYTEST_WORKERS=$WORKERS
    export PYTEST_TIMEOUT=300  # 5 minutes timeout

    # Run pytest with CI-specific settings
    if command -v poetry &> /dev/null; then
        poetry run python -m pytest tests/ \
            --workers=$WORKERS \
            --timeout=300 \
            -v \
            --tb=short \
            --maxfail=5 \
            --durations=10 \
            --disable-warnings \
            --cov=src \
            --cov-report=xml \
            --cov-report=html \
            --cov-fail-under=80 \
            --junitxml=ci-test-results.xml
    else
        python -m pytest tests/ \
            --workers=$WORKERS \
            --timeout=300 \
            -v \
            --tb=short \
            --maxfail=5 \
            --durations=10 \
            --disable-warnings \
            --cov=src \
            --cov-report=xml \
            --cov-report=html \
            --cov-fail-under=80 \
            --junitxml=ci-test-results.xml
    fi

    echo -e "${GREEN}Pytest CI simulation completed${NC}"
}

# Function to build Docker image with resource constraints
run_docker_build() {
    echo -e "${BLUE}Building Docker image with resource constraints${NC}"
    echo "Runner: $RUNNER_TYPE (${CPU_LIMIT} CPU cores, ${MEMORY_LIMIT} RAM)"

    # Build with resource limits
    docker build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --memory=${MEMORY_LIMIT} \
        --cpus=${CPU_LIMIT} \
        -t pake-system:ci-simulation \
        -f Dockerfile .

    echo -e "${GREEN}Docker build completed${NC}"
}

# Function to monitor resource usage
monitor_resources() {
    echo -e "${BLUE}Monitoring resource usage during CI simulation${NC}"
    echo "Runner: $RUNNER_TYPE (${CPU_LIMIT} CPU cores, ${MEMORY_LIMIT} RAM)"

    # Create monitoring script
    cat > monitor-ci-resources.sh << 'EOF'
#!/bin/bash

echo "=== CI Resource Monitoring ==="
echo "Timestamp: $(date)"
echo ""

# System info
echo "=== System Information ==="
echo "CPU Cores: $(nproc)"
echo "Total Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Available Memory: $(free -h | awk '/^Mem:/ {print $7}')"
echo ""

# Docker resource usage
echo "=== Docker Resource Usage ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# Process resource usage
echo "=== Top Resource Consumers ==="
ps aux --sort=-%cpu | head -10
echo ""

# Memory usage by process
echo "=== Memory Usage by Process ==="
ps aux --sort=-%mem | head -10
EOF

    chmod +x monitor-ci-resources.sh

    echo -e "${YELLOW}Starting resource monitoring...${NC}"
    echo "Press Ctrl+C to stop monitoring"

    # Run monitoring in background
    while true; do
        ./monitor-ci-resources.sh
        sleep 30
    done
}

# Function to validate CI environment simulation
validate_simulation() {
    echo -e "${BLUE}Validating CI environment simulation${NC}"
    echo "Runner: $RUNNER_TYPE (${CPU_LIMIT} CPU cores, ${MEMORY_LIMIT} RAM)"

    # Check Docker availability
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    # Check Docker Compose availability
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi

    # Check Python/pytest availability
    if ! command -v python &> /dev/null; then
        echo -e "${RED}Error: Python is not installed${NC}"
        exit 1
    fi

    # Check if Poetry is available and use it, otherwise check system Python
    if command -v poetry &> /dev/null; then
        if ! poetry run python -c "import pytest" &> /dev/null; then
            echo -e "${RED}Error: pytest is not installed in Poetry environment${NC}"
            exit 1
        fi
    else
        if ! python -c "import pytest" &> /dev/null; then
            echo -e "${RED}Error: pytest is not installed${NC}"
            exit 1
        fi
    fi

    # Check system resources
    AVAILABLE_CPUS=$(nproc)
    AVAILABLE_MEMORY=$(free -g | awk '/^Mem:/ {print $2}')

    echo -e "${YELLOW}System Resources:${NC}"
    echo "  Available CPUs: $AVAILABLE_CPUS"
    echo "  Available Memory: ${AVAILABLE_MEMORY}GB"
    echo "  Target CI CPUs: $CPU_LIMIT"
    echo "  Target CI Memory: $MEMORY_LIMIT"

    if [[ $AVAILABLE_CPUS -lt $CPU_LIMIT ]]; then
        echo -e "${YELLOW}Warning: Available CPUs ($AVAILABLE_CPUS) is less than CI target ($CPU_LIMIT)${NC}"
    fi

    if [[ $AVAILABLE_MEMORY -lt ${MEMORY_LIMIT%g} ]]; then
        echo -e "${YELLOW}Warning: Available memory (${AVAILABLE_MEMORY}GB) is less than CI target ($MEMORY_LIMIT)${NC}"
    fi

    echo -e "${GREEN}CI environment simulation validation completed${NC}"
}

# Main execution
main() {
    validate_runner

    case $ACTION in
        help)
            show_help
            ;;
        docker-test)
            run_docker_test
            ;;
        pytest-ci)
            run_pytest_ci
            ;;
        docker-build)
            run_docker_build
            ;;
        monitor)
            monitor_resources
            ;;
        validate)
            validate_simulation
            ;;
        *)
            echo -e "${RED}Error: Invalid action '$ACTION'${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
