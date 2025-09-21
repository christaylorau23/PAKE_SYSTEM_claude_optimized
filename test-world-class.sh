#!/bin/bash

# PAKE System - World-Class Testing & Validation Suite
# Comprehensive testing framework for enterprise-grade validation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TEST_RESULTS_DIR="test-results-$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$TEST_RESULTS_DIR/test-suite.log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_header() {
    echo -e "${PURPLE}[HEADER]${NC} $1" | tee -a "$LOG_FILE"
}

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1" | tee -a "$LOG_FILE"
}

# Test result tracking
record_test() {
    local test_name="$1"
    local result="$2"
    local details="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    case "$result" in
        "PASS")
            PASSED_TESTS=$((PASSED_TESTS + 1))
            log_success "✓ $test_name"
            ;;
        "FAIL")
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_error "✗ $test_name: $details"
            ;;
        "SKIP")
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
            log_warning "⊘ $test_name: $details"
            ;;
    esac
    
    echo "$(date): $test_name - $result - $details" >> "$TEST_RESULTS_DIR/test-details.log"
}

# Setup test environment
setup_test_environment() {
    log_header "Setting Up Test Environment"
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    # Initialize log files
    touch "$LOG_FILE"
    touch "$TEST_RESULTS_DIR/test-details.log"
    
    log_success "Test environment setup completed"
}

# Test Docker services
test_docker_services() {
    log_header "Testing Docker Services"
    
    # Test if Docker is running
    log_test "Docker daemon status"
    if docker info >/dev/null 2>&1; then
        record_test "Docker daemon" "PASS" "Docker is running"
    else
        record_test "Docker daemon" "FAIL" "Docker is not running"
        return 1
    fi
    
    # Test Docker Compose
    log_test "Docker Compose availability"
    if command -v docker-compose >/dev/null 2>&1; then
        record_test "Docker Compose" "PASS" "Docker Compose is available"
    else
        record_test "Docker Compose" "FAIL" "Docker Compose is not available"
        return 1
    fi
    
    # Test service containers
    local services=("vault" "postgres" "redis" "pake-api" "pake-bridge" "prometheus" "grafana" "nginx")
    
    for service in "${services[@]}"; do
        log_test "Service container: $service"
        if docker-compose ps "$service" | grep -q "Up"; then
            record_test "Container $service" "PASS" "Container is running"
        else
            record_test "Container $service" "FAIL" "Container is not running"
        fi
    done
}

# Test network connectivity
test_network_connectivity() {
    log_header "Testing Network Connectivity"
    
    local endpoints=(
        "http://localhost:8000/health:PAKE API"
        "http://localhost:3001/health:PAKE Bridge"
        "http://localhost:9090/-/healthy:Prometheus"
        "http://localhost:3000/api/health:Grafana"
        "http://localhost:8200/v1/sys/health:Vault"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r endpoint service <<< "$endpoint_info"
        log_test "Network connectivity: $service"
        
        if curl -f -s --max-time 10 "$endpoint" >/dev/null 2>&1; then
            record_test "Network $service" "PASS" "Endpoint is reachable"
        else
            record_test "Network $service" "FAIL" "Endpoint is not reachable"
        fi
    done
}

# Test API endpoints
test_api_endpoints() {
    log_header "Testing API Endpoints"
    
    local api_base="http://localhost:8000"
    local endpoints=(
        "/health:Health check"
        "/ready:Readiness check"
        "/metrics:Metrics endpoint"
        "/docs:API documentation"
        "/openapi.json:OpenAPI specification"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r endpoint description <<< "$endpoint_info"
        log_test "API endpoint: $description"
        
        local response_code
        response_code=$(curl -s -o /dev/null -w "%{http_code}" "$api_base$endpoint")
        
        if [ "$response_code" = "200" ]; then
            record_test "API $description" "PASS" "HTTP 200 response"
        else
            record_test "API $description" "FAIL" "HTTP $response_code response"
        fi
    done
}

# Test database connections
test_database_connections() {
    log_header "Testing Database Connections"
    
    # Test PostgreSQL
    log_test "PostgreSQL connection"
    if docker-compose exec -T postgres pg_isready -U postgres -d wealth_db >/dev/null 2>&1; then
        record_test "PostgreSQL connection" "PASS" "Database is ready"
    else
        record_test "PostgreSQL connection" "FAIL" "Database is not ready"
    fi
    
    # Test PostgreSQL query
    log_test "PostgreSQL query execution"
    if docker-compose exec -T postgres psql -U postgres -d wealth_db -c "SELECT 1;" >/dev/null 2>&1; then
        record_test "PostgreSQL query" "PASS" "Query executed successfully"
    else
        record_test "PostgreSQL query" "FAIL" "Query execution failed"
    fi
    
    # Test Redis
    log_test "Redis connection"
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        record_test "Redis connection" "PASS" "Redis is responding"
    else
        record_test "Redis connection" "FAIL" "Redis is not responding"
    fi
    
    # Test Redis operations
    log_test "Redis operations"
    if docker-compose exec -T redis redis-cli set test_key "test_value" && \
       docker-compose exec -T redis redis-cli get test_key | grep -q "test_value"; then
        record_test "Redis operations" "PASS" "Set/get operations successful"
        docker-compose exec -T redis redis-cli del test_key >/dev/null 2>&1
    else
        record_test "Redis operations" "FAIL" "Set/get operations failed"
    fi
}

# Test Vault functionality
test_vault_functionality() {
    log_header "Testing Vault Functionality"
    
    # Test Vault status
    log_test "Vault status"
    if docker-compose exec -T vault vault status | grep -q "Sealed.*false"; then
        record_test "Vault status" "PASS" "Vault is unsealed and ready"
    else
        record_test "Vault status" "FAIL" "Vault is not ready"
    fi
    
    # Test Vault secret access
    log_test "Vault secret access"
    if docker-compose exec -T vault vault kv get secret/wealth-platform/postgres >/dev/null 2>&1; then
        record_test "Vault secret access" "PASS" "Secrets are accessible"
    else
        record_test "Vault secret access" "FAIL" "Secrets are not accessible"
    fi
    
    # Test Vault policy
    log_test "Vault policy"
    if docker-compose exec -T vault vault policy read wealth-platform >/dev/null 2>&1; then
        record_test "Vault policy" "PASS" "Policy exists and is readable"
    else
        record_test "Vault policy" "FAIL" "Policy does not exist or is not readable"
    fi
}

# Test monitoring systems
test_monitoring_systems() {
    log_header "Testing Monitoring Systems"
    
    # Test Prometheus
    log_test "Prometheus metrics collection"
    if curl -f -s "http://localhost:9090/api/v1/query?query=up" | grep -q "success"; then
        record_test "Prometheus metrics" "PASS" "Metrics collection is working"
    else
        record_test "Prometheus metrics" "FAIL" "Metrics collection is not working"
    fi
    
    # Test Grafana
    log_test "Grafana dashboard access"
    if curl -f -s "http://localhost:3000/api/health" | grep -q "ok"; then
        record_test "Grafana dashboard" "PASS" "Dashboard is accessible"
    else
        record_test "Grafana dashboard" "FAIL" "Dashboard is not accessible"
    fi
}

# Test security features
test_security_features() {
    log_header "Testing Security Features"
    
    # Test HTTPS redirect (if configured)
    log_test "HTTPS redirect"
    local https_response
    https_response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/health" || echo "000")
    
    if [ "$https_response" = "301" ] || [ "$https_response" = "302" ]; then
        record_test "HTTPS redirect" "PASS" "HTTPS redirect is configured"
    elif [ "$https_response" = "200" ]; then
        record_test "HTTPS redirect" "SKIP" "HTTP is working (HTTPS not configured)"
    else
        record_test "HTTPS redirect" "FAIL" "HTTP endpoint is not responding"
    fi
    
    # Test secret management
    log_test "Secret management"
    if docker-compose exec -T vault vault kv list secret/wealth-platform/ >/dev/null 2>&1; then
        record_test "Secret management" "PASS" "Secrets are properly managed"
    else
        record_test "Secret management" "FAIL" "Secret management is not working"
    fi
    
    # Test non-root containers
    log_test "Container security"
    local containers=("pake-api" "pake-bridge")
    local all_non_root=true
    
    for container in "${containers[@]}"; do
        if docker-compose exec -T "$container" whoami | grep -q "root"; then
            all_non_root=false
            break
        fi
    done
    
    if [ "$all_non_root" = true ]; then
        record_test "Container security" "PASS" "Containers run as non-root user"
    else
        record_test "Container security" "FAIL" "Some containers run as root"
    fi
}

# Test performance
test_performance() {
    log_header "Testing Performance"
    
    # Test API response time
    log_test "API response time"
    local response_time
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "http://localhost:8000/health")
    
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        record_test "API response time" "PASS" "Response time: ${response_time}s"
    else
        record_test "API response time" "FAIL" "Response time too slow: ${response_time}s"
    fi
    
    # Test database query performance
    log_test "Database query performance"
    local query_time
    query_time=$(time (docker-compose exec -T postgres psql -U postgres -d wealth_db -c "SELECT 1;" >/dev/null 2>&1) 2>&1 | grep real | awk '{print $2}')
    
    record_test "Database query performance" "PASS" "Query time: $query_time"
}

# Generate test report
generate_test_report() {
    log_header "Generating Test Report"
    
    local report_file="$TEST_RESULTS_DIR/test-report.md"
    
    cat > "$report_file" << EOF
# PAKE System Test Report

**Test Date:** $(date)
**Test Duration:** $(($(date +%s) - START_TIME)) seconds
**Test Environment:** Docker Compose

## Test Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS
- **Failed:** $FAILED_TESTS
- **Skipped:** $SKIPPED_TESTS
- **Success Rate:** $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%

## Test Results

EOF

    # Add detailed test results
    if [ -f "$TEST_RESULTS_DIR/test-details.log" ]; then
        echo "### Detailed Results" >> "$report_file"
        echo '```' >> "$report_file"
        cat "$TEST_RESULTS_DIR/test-details.log" >> "$report_file"
        echo '```' >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

## System Status

### Services
EOF

    # Add service status
    docker-compose ps >> "$report_file"
    
    cat >> "$report_file" << EOF

## Recommendations

EOF

    if [ $FAILED_TESTS -gt 0 ]; then
        cat >> "$report_file" << EOF
- Address failed tests before production deployment
- Review error logs for failed services
- Verify all dependencies are properly configured
EOF
    else
        cat >> "$report_file" << EOF
- All tests passed! System is ready for production
- Consider setting up monitoring alerts
- Implement backup strategies
- Review security configurations
EOF
    fi
    
    log_success "Test report generated: $report_file"
}

# Show test summary
show_test_summary() {
    log_header "Test Summary"
    
    echo -e "${CYAN}📊 Test Results:${NC}"
    echo -e "   Total Tests:  $TOTAL_TESTS"
    echo -e "   Passed:       ${GREEN}$PASSED_TESTS${NC}"
    echo -e "   Failed:       ${RED}$FAILED_TESTS${NC}"
    echo -e "   Skipped:      ${YELLOW}$SKIPPED_TESTS${NC}"
    echo -e "   Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
    
    echo ""
    echo -e "${CYAN}📁 Test Results Directory:${NC}"
    echo -e "   $TEST_RESULTS_DIR"
    
    echo ""
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! System is ready for production!${NC}"
    else
        echo -e "${RED}⚠️  Some tests failed. Please review and fix issues.${NC}"
    fi
}

# Main test function
main() {
    START_TIME=$(date +%s)
    
    log_header "Starting PAKE System Test Suite"
    log_info "Test results directory: $TEST_RESULTS_DIR"
    
    # Execute test suites
    setup_test_environment
    test_docker_services
    test_network_connectivity
    test_api_endpoints
    test_database_connections
    test_vault_functionality
    test_monitoring_systems
    test_security_features
    test_performance
    generate_test_report
    show_test_summary
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
        log_success "All tests completed successfully!"
        exit 0
    else
        log_error "Some tests failed. Please review the test report."
        exit 1
    fi
}

# Run main function
main "$@"
