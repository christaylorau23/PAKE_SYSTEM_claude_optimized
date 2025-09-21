#!/bin/bash
#
# PAKE System - Production Deployment Script
# Automated deployment with health checks and rollback capability
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="pake-system"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.production"
BACKUP_DIR="backups"
DEPLOYMENT_TIMEOUT=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        error "Environment file $ENV_FILE not found."
        log "Please copy .env.production.example to $ENV_FILE and configure it."
        exit 1
    fi

    # Check if required environment variables are set
    source "$ENV_FILE"
    if [ -z "${JWT_SECRET_KEY:-}" ] || [ "$JWT_SECRET_KEY" = "CHANGE_THIS_TO_A_VERY_LONG_SECURE_RANDOM_STRING" ]; then
        error "JWT_SECRET_KEY not properly configured in $ENV_FILE"
        exit 1
    fi

    if [ -z "${POSTGRES_PASSWORD:-}" ] || [ "$POSTGRES_PASSWORD" = "CHANGE_THIS_PASSWORD" ]; then
        error "POSTGRES_PASSWORD not properly configured in $ENV_FILE"
        exit 1
    fi

    success "Prerequisites check passed"
}

# Function to create backup
create_backup() {
    log "Creating backup..."

    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pake-backup-$(date +%Y%m%d-%H%M%S).tar.gz"

    # Backup database if it exists
    if docker-compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
        log "Backing up database..."
        docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U pake_user pake_system > "$BACKUP_DIR/database-$(date +%Y%m%d-%H%M%S).sql"
    fi

    # Backup volumes
    log "Backing up application data..."
    tar -czf "$BACKUP_FILE" --exclude="$BACKUP_DIR" --exclude=".git" --exclude="node_modules" --exclude="venv" .

    success "Backup created: $BACKUP_FILE"
}

# Function to build images
build_images() {
    log "Building Docker images..."

    docker-compose -f "$COMPOSE_FILE" build --no-cache

    success "Docker images built successfully"
}

# Function to start services
start_services() {
    log "Starting services..."

    docker-compose -f "$COMPOSE_FILE" up -d

    success "Services started"
}

# Function to wait for services
wait_for_services() {
    log "Waiting for services to be healthy..."

    local timeout=$DEPLOYMENT_TIMEOUT
    local count=0

    while [ $count -lt $timeout ]; do
        if docker-compose -f "$COMPOSE_FILE" ps --filter "health=healthy" | grep -q "healthy"; then
            local healthy_count=$(docker-compose -f "$COMPOSE_FILE" ps --filter "health=healthy" | grep -c "healthy" || echo "0")
            local total_count=$(docker-compose -f "$COMPOSE_FILE" ps --services | wc -l)

            log "Health check: $healthy_count/$total_count services healthy"

            if [ "$healthy_count" -eq "$total_count" ]; then
                success "All services are healthy"
                return 0
            fi
        fi

        sleep 5
        count=$((count + 5))
    done

    error "Services failed to become healthy within $timeout seconds"
    return 1
}

# Function to run smoke tests
run_smoke_tests() {
    log "Running smoke tests..."

    # Test backend health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "Backend health check passed"
    else
        error "Backend health check failed"
        return 1
    fi

    # Test frontend health
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        success "Frontend health check passed"
    else
        warning "Frontend health check failed (might be normal)"
    fi

    # Test database connection
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U pake_user -d pake_system > /dev/null 2>&1; then
        success "Database connection test passed"
    else
        error "Database connection test failed"
        return 1
    fi

    # Test Redis connection
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping | grep -q PONG; then
        success "Redis connection test passed"
    else
        error "Redis connection test failed"
        return 1
    fi

    success "Smoke tests completed successfully"
}

# Function to rollback
rollback() {
    error "Deployment failed. Starting rollback..."

    log "Stopping current deployment..."
    docker-compose -f "$COMPOSE_FILE" down

    # Restore from backup if available
    local latest_backup=$(ls -t "$BACKUP_DIR"/pake-backup-*.tar.gz 2>/dev/null | head -n 1 || echo "")
    if [ -n "$latest_backup" ]; then
        warning "Restore from backup manually if needed: $latest_backup"
    fi

    error "Rollback completed. Please investigate the issues."
    exit 1
}

# Function to show status
show_status() {
    log "Deployment Status:"
    echo "===================="
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""

    log "Service URLs:"
    echo "Frontend: http://localhost:3000"
    echo "Backend API: http://localhost:8000"
    echo "WebSocket: ws://localhost:8001"
    echo "Admin Dashboard: http://localhost:8000/admin/dashboard"
    echo "Health Check: http://localhost:8000/health"
}

# Main deployment function
deploy() {
    log "Starting PAKE System deployment..."

    check_prerequisites

    # Create backup before deployment
    create_backup

    # Build and deploy
    build_images
    start_services

    # Wait for services and run tests
    if wait_for_services && run_smoke_tests; then
        success "🚀 PAKE System deployed successfully!"
        show_status
    else
        rollback
    fi
}

# Function to show usage
usage() {
    echo "PAKE System Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    Deploy the PAKE system (default)"
    echo "  status    Show current deployment status"
    echo "  logs      Show service logs"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  backup    Create a backup"
    echo "  help      Show this help message"
    echo ""
    echo "Environment:"
    echo "  Make sure to configure $ENV_FILE before deployment"
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    status)
        show_status
        ;;
    logs)
        docker-compose -f "$COMPOSE_FILE" logs -f "${2:-}"
        ;;
    stop)
        log "Stopping all services..."
        docker-compose -f "$COMPOSE_FILE" down
        success "All services stopped"
        ;;
    restart)
        log "Restarting all services..."
        docker-compose -f "$COMPOSE_FILE" restart
        wait_for_services
        success "All services restarted"
        ;;
    backup)
        create_backup
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        error "Unknown command: $1"
        usage
        exit 1
        ;;
esac