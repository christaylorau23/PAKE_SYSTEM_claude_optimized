#!/bin/bash
# PAKE System - Unified Quality Dashboard Deployment Script
# This script deploys the complete monitoring stack with SonarQube integration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MONITORING_DIR="$PROJECT_ROOT/monitoring"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Check if Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi

    # Check if required environment variables are set
    if [[ -z "${SONAR_TOKEN:-}" ]]; then
        log_warning "SONAR_TOKEN environment variable is not set. SonarQube integration will be limited."
    fi

    if [[ -z "${GRAFANA_PASSWORD:-}" ]]; then
        log_warning "GRAFANA_PASSWORD environment variable is not set. Using default password."
        export GRAFANA_PASSWORD="pake_grafana_2024"
    fi

    log_success "Prerequisites check completed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."

    mkdir -p "$MONITORING_DIR/grafana/dashboards"
    mkdir -p "$MONITORING_DIR/grafana/datasources"
    mkdir -p "$MONITORING_DIR/prometheus/rules"
    mkdir -p "$MONITORING_DIR/grafana/provisioning/dashboards"
    mkdir -p "$MONITORING_DIR/grafana/provisioning/datasources"

    log_success "Directories created"
}

# Deploy Prometheus
deploy_prometheus() {
    log_info "Deploying Prometheus..."

    # Copy Prometheus configuration
    cp "$MONITORING_DIR/prometheus/sonarqube-exporter.yml" "$MONITORING_DIR/prometheus.yml"

    # Start Prometheus
    docker-compose -f "$MONITORING_DIR/docker-compose.monitoring.yml" up -d prometheus

    # Wait for Prometheus to be ready
    log_info "Waiting for Prometheus to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
            log_success "Prometheus is ready"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "Prometheus failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
}

# Deploy Grafana
deploy_grafana() {
    log_info "Deploying Grafana..."

    # Copy Grafana configuration
    cp "$MONITORING_DIR/grafana/datasources/sonarqube.yml" "$MONITORING_DIR/grafana/provisioning/datasources/"
    cp "$MONITORING_DIR/grafana/dashboards/unified-quality-dashboard.json" "$MONITORING_DIR/grafana/provisioning/dashboards/"

    # Start Grafana
    docker-compose -f "$MONITORING_DIR/docker-compose.monitoring.yml" up -d grafana

    # Wait for Grafana to be ready
    log_info "Waiting for Grafana to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3001/api/health >/dev/null 2>&1; then
            log_success "Grafana is ready"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "Grafana failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
}

# Deploy SonarQube (if not already running)
deploy_sonarqube() {
    log_info "Checking SonarQube status..."

    if docker ps --format "table {{.Names}}" | grep -q "sonarqube"; then
        log_info "SonarQube is already running"
    else
        log_info "Deploying SonarQube..."

        # Start SonarQube
        docker-compose -f "$MONITORING_DIR/docker-compose.monitoring.yml" up -d sonarqube

        # Wait for SonarQube to be ready
        log_info "Waiting for SonarQube to be ready..."
        for i in {1..60}; do
            if curl -s http://localhost:9000/api/system/status >/dev/null 2>&1; then
                log_success "SonarQube is ready"
                break
            fi
            if [[ $i -eq 60 ]]; then
                log_error "SonarQube failed to start within 60 seconds"
                exit 1
            fi
            sleep 2
        done
    fi
}

# Configure SonarQube project
configure_sonarqube() {
    log_info "Configuring SonarQube project..."

    if [[ -n "${SONAR_TOKEN:-}" ]]; then
        # Create project if it doesn't exist
        curl -s -u "$SONAR_TOKEN:" \
            -X POST \
            "http://localhost:9000/api/projects/create" \
            -d "project=pake-system" \
            -d "name=PAKE System" \
            -d "organization=pake-system-org" || true

        log_success "SonarQube project configured"
    else
        log_warning "SONAR_TOKEN not set. Please configure SonarQube project manually."
    fi
}

# Deploy monitoring stack
deploy_monitoring_stack() {
    log_info "Deploying complete monitoring stack..."

    # Start all monitoring services
    docker-compose -f "$MONITORING_DIR/docker-compose.monitoring.yml" up -d

    log_success "Monitoring stack deployed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check Prometheus
    if curl -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
        log_success "Prometheus is healthy"
    else
        log_error "Prometheus health check failed"
        return 1
    fi

    # Check Grafana
    if curl -s http://localhost:3001/api/health >/dev/null 2>&1; then
        log_success "Grafana is healthy"
    else
        log_error "Grafana health check failed"
        return 1
    fi

    # Check SonarQube
    if curl -s http://localhost:9000/api/system/status >/dev/null 2>&1; then
        log_success "SonarQube is healthy"
    else
        log_error "SonarQube health check failed"
        return 1
    fi

    log_success "All services are healthy"
}

# Display access information
display_access_info() {
    log_success "Unified Quality Dashboard deployment completed!"
    echo
    echo "Access Information:"
    echo "=================="
    echo "Grafana Dashboard: http://localhost:3001"
    echo "  Username: admin"
    echo "  Password: $GRAFANA_PASSWORD"
    echo
    echo "Prometheus: http://localhost:9090"
    echo "SonarQube: http://localhost:9000"
    echo
    echo "Dashboard Features:"
    echo "=================="
    echo "✅ Code Quality Metrics (SonarQube integration)"
    echo "✅ Security Posture Monitoring"
    echo "✅ Test Coverage Tracking"
    echo "✅ Technical Debt Monitoring"
    echo "✅ CI/CD Performance Metrics"
    echo "✅ Development Velocity Tracking"
    echo "✅ Real-time Quality Gate Alerts"
    echo
    echo "Next Steps:"
    echo "==========="
    echo "1. Access Grafana dashboard to view quality metrics"
    echo "2. Configure SonarQube project settings"
    echo "3. Set up GitHub Actions integration"
    echo "4. Configure alerting rules"
    echo "5. Train team on Boy Scout Rule implementation"
}

# Main deployment function
main() {
    log_info "Starting Unified Quality Dashboard deployment..."

    check_prerequisites
    create_directories
    deploy_prometheus
    deploy_grafana
    deploy_sonarqube
    configure_sonarqube
    deploy_monitoring_stack
    verify_deployment
    display_access_info

    log_success "Unified Quality Dashboard deployment completed successfully!"
}

# Run main function
main "$@"
