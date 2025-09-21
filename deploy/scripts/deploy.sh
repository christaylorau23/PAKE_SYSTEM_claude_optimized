#!/bin/bash
# Deployment Script for PAKE System
# Supports deployment to different environments using Kustomize

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
ENVIRONMENT=""
PLATFORM="kubernetes"
DRY_RUN=false
VALIDATE_ONLY=false
FORCE=false
TIMEOUT=600

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy PAKE System to different environments using Kustomize.

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production)
    -p, --platform PLATFORM Deployment platform (kubernetes|docker) [default: kubernetes]
    -d, --dry-run           Perform a dry run without making changes
    -v, --validate-only     Only validate configurations without deploying
    -f, --force            Force deployment without confirmation
    -t, --timeout SECONDS  Deployment timeout in seconds [default: 600]
    -h, --help             Show this help message

EXAMPLES:
    $0 -e development                    # Deploy to development environment
    $0 -e production -d                  # Dry run deployment to production
    $0 -e staging -p docker              # Deploy to staging using Docker Compose
    $0 -e production -v                  # Validate production configuration only

EOF
}

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$ENVIRONMENT" ]; then
        error "Environment is required. Use -e or --environment."
        usage
        exit 1
    fi

    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
        error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: development, staging, production"
        exit 1
    fi

    # Validate platform
    if [[ ! "$PLATFORM" =~ ^(kubernetes|docker)$ ]]; then
        error "Invalid platform: $PLATFORM"
        echo "Valid platforms: kubernetes, docker"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for $PLATFORM deployment..."

    if [ "$PLATFORM" = "kubernetes" ]; then
        # Check kubectl
        if ! command -v kubectl &> /dev/null; then
            error "kubectl is required for Kubernetes deployments"
            exit 1
        fi

        # Check kustomize
        if ! command -v kustomize &> /dev/null; then
            error "kustomize is required for Kubernetes deployments"
            exit 1
        fi

        # Check cluster connectivity
        if ! kubectl cluster-info &> /dev/null; then
            error "Cannot connect to Kubernetes cluster"
            exit 1
        fi

        success "Kubernetes prerequisites satisfied"

    elif [ "$PLATFORM" = "docker" ]; then
        # Check docker
        if ! command -v docker &> /dev/null; then
            error "docker is required for Docker deployments"
            exit 1
        fi

        # Check docker-compose
        if ! command -v docker-compose &> /dev/null; then
            error "docker-compose is required for Docker deployments"
            exit 1
        fi

        # Check Docker daemon
        if ! docker info &> /dev/null; then
            error "Cannot connect to Docker daemon"
            exit 1
        fi

        success "Docker prerequisites satisfied"
    fi
}

# Validate configurations
validate_configurations() {
    log "Validating configurations..."

    if [ -x "$SCRIPT_DIR/validate-config.sh" ]; then
        "$SCRIPT_DIR/validate-config.sh"
    else
        warning "Configuration validation script not found or not executable"
    fi
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log "Deploying to Kubernetes environment: $ENVIRONMENT"

    local overlay_dir="$DEPLOY_DIR/k8s/overlays/$ENVIRONMENT"

    if [ ! -d "$overlay_dir" ]; then
        error "Kubernetes overlay directory not found: $overlay_dir"
        exit 1
    fi

    # Build and validate
    log "Building Kustomize configuration..."
    local manifest_file="/tmp/pake-${ENVIRONMENT}-manifest.yaml"

    if ! kustomize build "$overlay_dir" > "$manifest_file"; then
        error "Failed to build Kustomize configuration"
        exit 1
    fi

    success "Kustomize build successful"

    # Show what will be deployed
    log "Resources to be deployed:"
    kubectl apply --dry-run=client -f "$manifest_file" | grep -E "^(deployment|service|configmap|secret|ingress|statefulset|pvc)"

    # Deployment confirmation
    if [ "$DRY_RUN" = true ]; then
        success "Dry run completed successfully"
        rm -f "$manifest_file"
        return 0
    fi

    if [ "$FORCE" = false ]; then
        echo ""
        read -p "Do you want to proceed with the deployment? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Deployment cancelled by user"
            rm -f "$manifest_file"
            exit 0
        fi
    fi

    # Apply the configuration
    log "Applying Kubernetes manifests..."
    if kubectl apply -f "$manifest_file" --timeout="${TIMEOUT}s"; then
        success "Kubernetes deployment completed"
    else
        error "Kubernetes deployment failed"
        rm -f "$manifest_file"
        exit 1
    fi

    # Wait for rollout
    log "Waiting for rollout to complete..."
    local deployments
    deployments=$(kubectl get deployments -n pake-system -o name 2>/dev/null || echo "")

    if [ -n "$deployments" ]; then
        for deployment in $deployments; do
            log "Waiting for $deployment..."
            if kubectl rollout status "$deployment" -n pake-system --timeout="${TIMEOUT}s"; then
                success "$deployment rollout completed"
            else
                warning "$deployment rollout did not complete within timeout"
            fi
        done
    fi

    # Cleanup
    rm -f "$manifest_file"

    # Show deployment status
    show_deployment_status
}

# Deploy with Docker Compose
deploy_docker() {
    log "Deploying with Docker Compose environment: $ENVIRONMENT"

    local base_compose="$DEPLOY_DIR/docker/base/docker-compose.base.yml"
    local override_compose="$DEPLOY_DIR/docker/overlays/$ENVIRONMENT/docker-compose.override.yml"

    if [ ! -f "$base_compose" ]; then
        error "Base Docker Compose file not found: $base_compose"
        exit 1
    fi

    local compose_files=("-f" "$base_compose")

    if [ -f "$override_compose" ]; then
        compose_files+=("-f" "$override_compose")
        log "Using override file: $override_compose"
    else
        warning "Override file not found, using base configuration only"
    fi

    # Change to deployment directory
    cd "$DEPLOY_DIR/docker/overlays/$ENVIRONMENT"

    # Show what will be deployed
    log "Services to be deployed:"
    docker-compose "${compose_files[@]}" config --services

    # Deployment confirmation
    if [ "$DRY_RUN" = true ]; then
        log "Docker Compose configuration:"
        docker-compose "${compose_files[@]}" config
        success "Dry run completed successfully"
        return 0
    fi

    if [ "$FORCE" = false ]; then
        echo ""
        read -p "Do you want to proceed with the deployment? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Deployment cancelled by user"
            exit 0
        fi
    fi

    # Deploy with Docker Compose
    log "Starting Docker Compose deployment..."
    if docker-compose "${compose_files[@]}" up -d --build; then
        success "Docker Compose deployment completed"
    else
        error "Docker Compose deployment failed"
        exit 1
    fi

    # Show deployment status
    docker-compose "${compose_files[@]}" ps
}

# Show deployment status
show_deployment_status() {
    log "Checking deployment status..."

    if [ "$PLATFORM" = "kubernetes" ]; then
        echo ""
        echo "===== PODS ====="
        kubectl get pods -n pake-system

        echo ""
        echo "===== SERVICES ====="
        kubectl get services -n pake-system

        echo ""
        echo "===== INGRESS ====="
        kubectl get ingress -n pake-system 2>/dev/null || echo "No ingress found"

        # Health check
        log "Performing health checks..."
        local backend_service
        backend_service=$(kubectl get service -n pake-system -l app.kubernetes.io/name=pake-backend -o name 2>/dev/null | head -1)

        if [ -n "$backend_service" ]; then
            log "Checking backend health..."
            if kubectl port-forward -n pake-system "$backend_service" 8080:8000 &> /dev/null &
            then
                local port_forward_pid=$!
                sleep 2
                if curl -s http://localhost:8080/health &> /dev/null; then
                    success "Backend health check passed"
                else
                    warning "Backend health check failed"
                fi
                kill $port_forward_pid 2>/dev/null || true
            fi
        fi

    elif [ "$PLATFORM" = "docker" ]; then
        echo ""
        log "Container status:"
        docker-compose ps

        # Health check
        log "Performing health checks..."
        local backend_container
        backend_container=$(docker-compose ps -q pake-backend 2>/dev/null)

        if [ -n "$backend_container" ]; then
            if docker exec "$backend_container" curl -s http://localhost:8000/health &> /dev/null; then
                success "Backend health check passed"
            else
                warning "Backend health check failed"
            fi
        fi
    fi
}

# Main deployment function
main() {
    log "Starting PAKE System deployment..."
    log "Environment: $ENVIRONMENT"
    log "Platform: $PLATFORM"
    log "Dry run: $DRY_RUN"
    log "Validate only: $VALIDATE_ONLY"

    # Check prerequisites
    check_prerequisites

    # Validate configurations
    validate_configurations

    # Exit if validation only
    if [ "$VALIDATE_ONLY" = true ]; then
        success "Configuration validation completed"
        exit 0
    fi

    # Deploy based on platform
    case $PLATFORM in
        kubernetes)
            deploy_kubernetes
            ;;
        docker)
            deploy_docker
            ;;
        *)
            error "Unsupported platform: $PLATFORM"
            exit 1
            ;;
    esac

    success "Deployment completed successfully!"
}

# Parse arguments and run main function
parse_args "$@"
main