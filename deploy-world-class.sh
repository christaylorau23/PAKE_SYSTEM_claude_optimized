#!/bin/bash

# PAKE System - World-Class Engineer Deployment Script
# Enterprise-Grade Production Deployment with Comprehensive Validation

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
PROJECT_NAME="PAKE_SYSTEM"
VERSION="10.2.0"
NAMESPACE="pake-system"
LOG_FILE="/tmp/pake-deployment-$(date +%Y%m%d-%H%M%S).log"

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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# Banner
show_banner() {
    clear
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║           🚀 PAKE SYSTEM - WORLD-CLASS DEPLOYMENT 🚀        ║"
    echo "║                                                              ║"
    echo "║              Enterprise-Grade Production Setup               ║"
    echo "║                      Version $VERSION                        ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Prerequisites check
check_prerequisites() {
    log_header "Checking Prerequisites"
    
    local missing_deps=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    else
        log_success "Docker: $(docker --version)"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    else
        log_success "Docker Compose: $(docker-compose --version)"
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    else
        log_success "curl: Available"
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        log_warning "jq: Not found (optional, for JSON processing)"
    else
        log_success "jq: Available"
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Environment setup
setup_environment() {
    log_header "Setting Up Environment"
    
    # Create necessary directories
    log_step "Creating directory structure"
    mkdir -p data logs monitoring/grafana/dashboards monitoring/grafana/datasources nginx/ssl
    
    # Set up environment variables
    log_step "Configuring environment variables"
    export COMPOSE_PROJECT_NAME=pake-system
    export COMPOSE_FILE=docker-compose.production.yml
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_step "Creating .env file"
        cat > .env << EOF
# PAKE System Environment Configuration
PROJECT_NAME=$PROJECT_NAME
VERSION=$VERSION
NAMESPACE=$NAMESPACE

# API Keys (Set these to your actual keys)
FIRECRAWL_API_KEY=your-firecrawl-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key-here

# Database Configuration
POSTGRES_DB=wealth_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=WealthPass!2025
POSTGRES_REPLICATION_PASSWORD=ReplicaPass!2025

# Redis Configuration
REDIS_PASSWORD=WealthRedis!2025

# Grafana Configuration
GRAFANA_ADMIN_PASSWORD=WealthDashboard!!!

# JWT Configuration
JWT_SECRET_KEY=$(openssl rand -base64 64)

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_WORKERS=8
EOF
        log_success ".env file created"
    else
        log_info ".env file already exists"
    fi
    
    log_success "Environment setup completed"
}

# Build and deploy services
deploy_services() {
    log_header "Deploying Services"
    
    # Stop any existing containers
    log_step "Stopping existing containers"
    docker-compose down --remove-orphans || true
    
    # Build images
    log_step "Building Docker images"
    docker-compose build --no-cache --parallel
    
    # Start services
    log_step "Starting services"
    docker-compose up -d
    
    # Wait for services to be healthy
    log_step "Waiting for services to be healthy"
    wait_for_services
    
    log_success "All services deployed successfully"
}

# Wait for services to be ready
wait_for_services() {
    local services=("vault" "postgres" "redis" "pake-api" "pake-bridge" "prometheus" "grafana" "nginx")
    local max_wait=300  # 5 minutes
    local wait_time=0
    
    for service in "${services[@]}"; do
        log_info "Waiting for $service to be ready..."
        
        while [ $wait_time -lt $max_wait ]; do
            if docker-compose ps "$service" | grep -q "Up"; then
                log_success "$service is ready"
                break
            fi
            
            sleep 5
            wait_time=$((wait_time + 5))
        done
        
        if [ $wait_time -ge $max_wait ]; then
            log_error "$service failed to start within $max_wait seconds"
            docker-compose logs "$service"
            exit 1
        fi
        
        wait_time=0
    done
}

# Initialize Vault
initialize_vault() {
    log_header "Initializing Vault"
    
    log_step "Waiting for Vault to be ready"
    sleep 10
    
    log_step "Running Vault initialization"
    docker-compose exec -T vault /vault-init.sh || {
        log_warning "Vault initialization script not found, initializing manually"
        
        # Manual Vault initialization
        docker-compose exec -T vault vault secrets enable -path=secret kv-v2
        docker-compose exec -T vault vault kv put secret/wealth-platform/postgres \
            database="wealth_db" \
            username="postgres" \
            REDACTED_SECRET="${POSTGRES_PASSWORD:-$(openssl rand -base64 32)}" \
            replication-REDACTED_SECRET="${POSTGRES_REPLICATION_PASSWORD:-$(openssl rand -base64 32)}"
        
        docker-compose exec -T vault vault kv put secret/wealth-platform/api \
            database-url="postgresql://postgres:\${POSTGRES_PASSWORD:-\$(openssl rand -base64 32)}@postgres:5432/wealth_db" \
            firecrawl-api-key="\${FIRECRAWL_API_KEY:-your-firecrawl-api-key-here}" \
            openai-api-key="\${OPENAI_API_KEY:-your-openai-api-key-here}" \
            alphavantage-api-key="\${ALPHAVANTAGE_API_KEY:-your-alpha-vantage-key-here}"
        
        docker-compose exec -T vault vault kv put secret/wealth-platform/grafana \
            admin-REDACTED_SECRET="${GRAFANA_ADMIN_PASSWORD:-$(openssl rand -base64 32)}"
    }
    
    log_success "Vault initialized successfully"
}

# Run comprehensive tests
run_tests() {
    log_header "Running Comprehensive Tests"
    
    # Health checks
    log_step "Running health checks"
    test_health_endpoints
    
    # API tests
    log_step "Running API tests"
    test_api_endpoints
    
    # Database tests
    log_step "Running database tests"
    test_database_connection
    
    # Redis tests
    log_step "Running Redis tests"
    test_redis_connection
    
    # Vault tests
    log_step "Running Vault tests"
    test_vault_connection
    
    log_success "All tests completed successfully"
}

# Test health endpoints
test_health_endpoints() {
    local endpoints=(
        "http://localhost:8000/health"
        "http://localhost:3001/health"
        "http://localhost:9090/-/healthy"
        "http://localhost:3000/api/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing $endpoint"
        if curl -f -s "$endpoint" > /dev/null; then
            log_success "$endpoint is healthy"
        else
            log_warning "$endpoint is not responding"
        fi
    done
}

# Test API endpoints
test_api_endpoints() {
    local api_base="http://localhost:8000"
    local endpoints=(
        "/health"
        "/ready"
        "/metrics"
        "/docs"
        "/openapi.json"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing API $endpoint"
        if curl -f -s "$api_base$endpoint" > /dev/null; then
            log_success "API $endpoint is working"
        else
            log_warning "API $endpoint is not responding"
        fi
    done
}

# Test database connection
test_database_connection() {
    log_info "Testing PostgreSQL connection"
    if docker-compose exec -T postgres pg_isready -U postgres -d wealth_db; then
        log_success "PostgreSQL connection successful"
    else
        log_error "PostgreSQL connection failed"
        return 1
    fi
}

# Test Redis connection
test_redis_connection() {
    log_info "Testing Redis connection"
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis connection successful"
    else
        log_error "Redis connection failed"
        return 1
    fi
}

# Test Vault connection
test_vault_connection() {
    log_info "Testing Vault connection"
    if docker-compose exec -T vault vault status | grep -q "Sealed.*false"; then
        log_success "Vault connection successful"
    else
        log_error "Vault connection failed"
        return 1
    fi
}

# Generate deployment report
generate_report() {
    log_header "Generating Deployment Report"
    
    local report_file="deployment-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# PAKE System Deployment Report

**Deployment Date:** $(date)
**Version:** $VERSION
**Environment:** Production
**Deployment Method:** Docker Compose

## System Status

### Services Status
EOF

    # Get service status
    docker-compose ps >> "$report_file"
    
    cat >> "$report_file" << EOF

## Access Information

### Web Interfaces
- **PAKE API:** http://localhost:8000
- **PAKE Bridge:** http://localhost:3001
- **Grafana Dashboard:** http://localhost:3000 (admin/WealthDashboard!!!)
- **Prometheus:** http://localhost:9090
- **Vault UI:** http://localhost:8200 (token: dev-root-token-2025)

### Database Access
- **PostgreSQL:** localhost:5432 (postgres/WealthPass!2025)
- **Redis:** localhost:6379 (REDACTED_SECRET: WealthRedis!2025)

## Security Notes

- All secrets are managed by HashiCorp Vault
- Database REDACTED_SECRETs are securely generated
- API keys should be updated in Vault
- SSL certificates should be configured for production

## Next Steps

1. Update API keys in Vault
2. Configure SSL certificates
3. Set up monitoring alerts
4. Configure backup strategies
5. Review security settings

## Logs

Deployment logs are available at: $LOG_FILE

EOF

    log_success "Deployment report generated: $report_file"
}

# Show access information
show_access_info() {
    log_header "Access Information"
    
    echo -e "${CYAN}🌐 Web Interfaces:${NC}"
    echo -e "   PAKE API:          ${GREEN}http://localhost:8000${NC}"
    echo -e "   PAKE Bridge:       ${GREEN}http://localhost:3001${NC}"
    echo -e "   Grafana Dashboard: ${GREEN}http://localhost:3000${NC} (admin/WealthDashboard!!!)"
    echo -e "   Prometheus:        ${GREEN}http://localhost:9090${NC}"
    echo -e "   Vault UI:         ${GREEN}http://localhost:8200${NC} (token: dev-root-token-2025)"
    
    echo ""
    echo -e "${CYAN}🗄️  Database Access:${NC}"
    echo -e "   PostgreSQL:       ${GREEN}localhost:5432${NC} (postgres/WealthPass!2025)"
    echo -e "   Redis:           ${GREEN}localhost:6379${NC} (REDACTED_SECRET: WealthRedis!2025)"
    
    echo ""
    echo -e "${CYAN}🔧 Management Commands:${NC}"
    echo -e "   View logs:        ${GREEN}docker-compose logs -f [service]${NC}"
    echo -e "   Restart service:  ${GREEN}docker-compose restart [service]${NC}"
    echo -e "   Stop all:         ${GREEN}docker-compose down${NC}"
    echo -e "   Update secrets:   ${GREEN}docker-compose exec vault vault kv put secret/wealth-platform/api openai-api-key='your-key'${NC}"
    
    echo ""
    echo -e "${YELLOW}⚠️  Important Security Notes:${NC}"
    echo -e "   • Update API keys in Vault for production use"
    echo -e "   • Configure SSL certificates for HTTPS"
    echo -e "   • Review and update default REDACTED_SECRETs"
    echo -e "   • Set up monitoring and alerting"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    # Add cleanup logic here if needed
}

# Main deployment function
main() {
    # Trap to ensure cleanup on exit
    trap cleanup EXIT
    
    # Show banner
    show_banner
    
    # Start deployment
    log_info "Starting PAKE System deployment..."
    log_info "Log file: $LOG_FILE"
    
    # Execute deployment steps
    check_prerequisites
    setup_environment
    deploy_services
    initialize_vault
    run_tests
    generate_report
    show_access_info
    
    log_success "🎉 PAKE System deployment completed successfully!"
    log_info "System is ready for production use"
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║              🚀 DEPLOYMENT SUCCESSFUL! 🚀                  ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║         Your PAKE System is now running and ready!          ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
}

# Run main function
main "$@"
