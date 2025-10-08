#!/bin/bash
# PAKE System - Complete Unified Quality Dashboard Deployment Script
# Implements the full technology stack from the engineering guide

set -e

echo "🚀 Starting PAKE System Unified Quality Dashboard Deployment..."
echo "================================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Check environment variables
if [ -z "$SONAR_TOKEN" ]; then
    print_warning "SONAR_TOKEN environment variable is not set. SonarQube integration will be limited."
    print_warning "Set SONAR_TOKEN to enable full SonarQube integration."
fi

if [ -z "$GRAFANA_PASSWORD" ]; then
    print_warning "GRAFANA_PASSWORD environment variable is not set. Using default password."
    print_warning "Set GRAFANA_PASSWORD to use a custom password."
fi

print_success "Prerequisites check completed"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/prometheus/rules
print_success "Directories created"

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose -f monitoring/docker-compose.simple.yml down 2>/dev/null || true
docker-compose -f monitoring/docker-compose.complete.yml down 2>/dev/null || true
print_success "Existing containers stopped"

# Build the monitoring services
print_status "Building monitoring services..."
cd monitoring

# Build SonarQube exporter
print_status "Building SonarQube metrics exporter..."
docker build -f ../src/services/monitoring/Dockerfile.sonarqube-exporter -t pake-sonarqube-exporter ../src/services/monitoring/

# Build GitHub Actions exporter
print_status "Building GitHub Actions metrics exporter..."
docker build -f ../src/services/monitoring/Dockerfile.github-actions-exporter -t pake-github-actions-exporter ../src/services/monitoring/

# Build Jira exporter
print_status "Building Jira metrics exporter..."
docker build -f ../src/services/monitoring/Dockerfile.jira-exporter -t pake-jira-exporter ../src/services/monitoring/

print_success "Monitoring services built"

# Deploy the monitoring stack
print_status "Deploying complete monitoring stack..."
docker-compose -f docker-compose.complete.yml up -d

print_success "Monitoring stack deployed"

# Wait for services to be ready
print_status "Waiting for services to be ready..."

# Wait for Prometheus
print_status "Waiting for Prometheus..."
for i in {1..30}; do
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        print_success "Prometheus is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Prometheus failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Wait for Grafana
print_status "Waiting for Grafana..."
for i in {1..30}; do
    if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
        print_success "Grafana is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Grafana failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Wait for SonarQube exporter
print_status "Waiting for SonarQube exporter..."
for i in {1..30}; do
    if curl -s http://localhost:9300/health > /dev/null 2>&1; then
        print_success "SonarQube exporter is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "SonarQube exporter may not be ready (this is normal if SONAR_TOKEN is not set)"
        break
    fi
    sleep 1
done

# Wait for GitHub Actions exporter
print_status "Waiting for GitHub Actions exporter..."
for i in {1..30}; do
    if curl -s http://localhost:9100/health > /dev/null 2>&1; then
        print_success "GitHub Actions exporter is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "GitHub Actions exporter may not be ready (this is normal if GITHUB_TOKEN is not set)"
        break
    fi
    sleep 1
done

# Wait for Jira exporter
print_status "Waiting for Jira exporter..."
for i in {1..30}; do
    if curl -s http://localhost:9200/health > /dev/null 2>&1; then
        print_success "Jira exporter is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "Jira exporter may not be ready (this is normal if Jira credentials are not set)"
        break
    fi
    sleep 1
done

# Display access information
echo ""
echo "🎉 PAKE System Unified Quality Dashboard Deployment Complete!"
echo "================================================================"
echo ""
echo "📊 Dashboard Access:"
echo "   Grafana Dashboard: http://localhost:3001"
echo "   Username: admin"
echo "   Password: ${GRAFANA_PASSWORD:-pake_grafana_2024}"
echo ""
echo "🔧 Service Endpoints:"
echo "   Prometheus: http://localhost:9090"
echo "   SonarQube Exporter: http://localhost:9300"
echo "   GitHub Actions Exporter: http://localhost:9100"
echo "   Jira Exporter: http://localhost:9200"
echo ""
echo "📈 Dashboard Features:"
echo "   ✅ Complete metrics matrix from engineering guide Table 1.1"
echo "   ✅ Code Quality metrics (smells, duplication, complexity)"
echo "   ✅ Security metrics (vulnerabilities, hotspots)"
echo "   ✅ Test Coverage metrics (new code, overall)"
echo "   ✅ Technical Debt metrics (F821 errors, security violations)"
echo "   ✅ CI/CD Health metrics (build time, success rate)"
echo "   ✅ Development Velocity metrics (story points, bug ratio)"
echo ""
echo "🚀 Next Steps:"
echo "   1. Open http://localhost:3001 in your browser"
echo "   2. Login with admin / ${GRAFANA_PASSWORD:-pake_grafana_2024}"
echo "   3. View the 'PAKE System - Unified Quality Dashboard'"
echo "   4. Set up SonarQube Cloud integration (if not already done)"
echo "   5. Configure GitHub Actions and Jira integration (optional)"
echo ""
echo "🔍 Troubleshooting:"
echo "   - Check container status: docker ps"
echo "   - View logs: docker logs <container_name>"
echo "   - Restart services: docker-compose -f monitoring/docker-compose.complete.yml restart"
echo ""
print_success "Deployment completed successfully!"
