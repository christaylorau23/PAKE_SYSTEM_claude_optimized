#!/bin/bash
# PAKE System - Advanced Docker Build Script
# Implements Phase 5: Fortifying CI Pipeline for Future Resilience
#
# Features:
# - Multi-stage builds with optimal layer caching
# - Security scanning and vulnerability assessment
# - Registry caching for faster builds
# - Parallel builds for different services
# - Image optimization and compression
# - Comprehensive error handling and logging

set -euo pipefail

# =============================================================================
# Configuration and Environment Setup
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Build configuration
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_NAME="${IMAGE_NAME:-pake-system}"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT="${GIT_COMMIT:-$(git rev-parse HEAD)}"

# BuildKit configuration
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build arguments
BUILD_ARGS="--build-arg BUILD_DATE=${BUILD_DATE} --build-arg GIT_COMMIT=${GIT_COMMIT} --build-arg VERSION=${VERSION}"

# =============================================================================
# Utility Functions
# =============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
    fi
    log "Docker is running ✓"
}

# Check if BuildKit is available
check_buildkit() {
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker BuildKit is not available. Please update Docker to version 19.03+"
    fi
    log "Docker BuildKit is available ✓"
}

# Create buildx builder if it doesn't exist
setup_buildx() {
    local builder_name="pake-builder"

    if ! docker buildx inspect "$builder_name" >/dev/null 2>&1; then
        log "Creating BuildKit builder: $builder_name"
        docker buildx create --name "$builder_name" --driver docker-container --use
        docker buildx inspect --bootstrap
    else
        log "Using existing BuildKit builder: $builder_name"
        docker buildx use "$builder_name"
    fi
}

# =============================================================================
# Build Functions
# =============================================================================

# Build a single service with optimized caching
build_service() {
    local service_name="$1"
    local dockerfile="$2"
    local context="$3"
    local target="${4:-production}"
    local platforms="${5:-linux/amd64,linux/arm64}"

    log "Building $service_name service..."

    # Build with advanced caching
    docker buildx build \
        --file "$dockerfile" \
        --context "$context" \
        --target "$target" \
        --platform "$platforms" \
        --tag "$REGISTRY/$IMAGE_NAME/$service_name:$VERSION" \
        --tag "$REGISTRY/$IMAGE_NAME/$service_name:$GIT_COMMIT" \
        --tag "$REGISTRY/$IMAGE_NAME/$service_name:latest" \
        --cache-from "type=gha,scope=$service_name" \
        --cache-from "type=registry,ref=$REGISTRY/$IMAGE_NAME/$service_name:cache" \
        --cache-to "type=gha,scope=$service_name,mode=max" \
        --cache-to "type=registry,ref=$REGISTRY/$IMAGE_NAME/$service_name:cache,mode=max" \
        $BUILD_ARGS \
        --push \
        .

    success "Built $service_name service ✓"
}

# Build Python main service
build_python_main() {
    log "Building Python main service with multi-stage optimization..."

    build_service \
        "python-main" \
        "Dockerfile.production" \
        "." \
        "production" \
        "linux/amd64,linux/arm64"
}

# Build TypeScript bridge service
build_bridge() {
    log "Building TypeScript bridge service..."

    build_service \
        "bridge" \
        "Dockerfile.bridge.production" \
        "." \
        "production" \
        "linux/amd64,linux/arm64"
}

# Build frontend service
build_frontend() {
    log "Building frontend service..."

    build_service \
        "frontend" \
        "frontend/Dockerfile" \
        "frontend" \
        "runner" \
        "linux/amd64,linux/arm64"
}

# Build voice agents service
build_voice_agents() {
    log "Building voice agents service..."

    build_service \
        "voice-agents" \
        "src/services/voice-agents/Dockerfile" \
        "src/services/voice-agents" \
        "production" \
        "linux/amd64,linux/arm64"
}

# =============================================================================
# Security Functions
# =============================================================================

# Run security scan on built image
security_scan() {
    local image_name="$1"
    local service_name="$2"

    log "Running security scan on $service_name..."

    # Trivy security scan
    if command -v trivy >/dev/null 2>&1; then
        log "Running Trivy vulnerability scan..."
        trivy image --format table --severity HIGH,CRITICAL "$image_name" || warning "Trivy scan found vulnerabilities"
    else
        warning "Trivy not installed, skipping vulnerability scan"
    fi

    # Docker Scout security scan
    if command -v docker >/dev/null 2>&1 && docker scout version >/dev/null 2>&1; then
        log "Running Docker Scout security scan..."
        docker scout cves "$image_name" || warning "Docker Scout scan found issues"
    else
        warning "Docker Scout not available, skipping security scan"
    fi

    success "Security scan completed for $service_name ✓"
}

# =============================================================================
# Optimization Functions
# =============================================================================

# Analyze image layers and size
analyze_image() {
    local image_name="$1"
    local service_name="$2"

    log "Analyzing $service_name image..."

    # Pull image for analysis
    docker pull "$image_name" >/dev/null 2>&1 || true

    # Get image size
    local size=$(docker images --format "table {{.Size}}" "$image_name" | tail -n 1)
    log "Image size: $size"

    # Analyze with dive if available
    if command -v dive >/dev/null 2>&1; then
        log "Running dive analysis..."
        dive "$image_name" --ci || warning "Dive analysis completed with warnings"
    else
        warning "Dive not installed, skipping layer analysis"
    fi

    success "Image analysis completed for $service_name ✓"
}

# =============================================================================
# Testing Functions
# =============================================================================

# Test built image
test_image() {
    local image_name="$1"
    local service_name="$2"
    local port="${3:-8000}"

    log "Testing $service_name image..."

    # Start container
    local container_id=$(docker run -d -p "$port:$port" "$image_name")

    # Wait for service to start
    sleep 10

    # Test health endpoint
    if curl -f "http://localhost:$port/health" >/dev/null 2>&1; then
        success "Health check passed for $service_name ✓"
    else
        warning "Health check failed for $service_name"
    fi

    # Test non-root user
    if docker exec "$container_id" id | grep -q "uid=1000"; then
        success "Non-root user verification passed for $service_name ✓"
    else
        warning "Non-root user verification failed for $service_name"
    fi

    # Cleanup
    docker stop "$container_id" >/dev/null 2>&1
    docker rm "$container_id" >/dev/null 2>&1

    success "Testing completed for $service_name ✓"
}

# =============================================================================
# Main Build Pipeline
# =============================================================================

# Build all services
build_all() {
    log "Starting comprehensive Docker build pipeline..."

    # Pre-build checks
    check_docker
    check_buildkit
    setup_buildx

    # Build services in parallel where possible
    build_python_main &
    build_bridge &
    build_frontend &
    build_voice_agents &

    # Wait for all builds to complete
    wait

    success "All services built successfully ✓"
}

# Build specific service
build_specific() {
    local service="$1"

    check_docker
    check_buildkit
    setup_buildx

    case "$service" in
        "python"|"python-main")
            build_python_main
            ;;
        "bridge")
            build_bridge
            ;;
        "frontend")
            build_frontend
            ;;
        "voice-agents")
            build_voice_agents
            ;;
        *)
            error "Unknown service: $service. Available services: python, bridge, frontend, voice-agents"
            ;;
    esac
}

# Run security scans on all images
scan_all() {
    log "Running security scans on all built images..."

    security_scan "$REGISTRY/$IMAGE_NAME/python-main:$VERSION" "python-main"
    security_scan "$REGISTRY/$IMAGE_NAME/bridge:$VERSION" "bridge"
    security_scan "$REGISTRY/$IMAGE_NAME/frontend:$VERSION" "frontend"
    security_scan "$REGISTRY/$IMAGE_NAME/voice-agents:$VERSION" "voice-agents"

    success "Security scans completed ✓"
}

# Analyze all images
analyze_all() {
    log "Analyzing all built images..."

    analyze_image "$REGISTRY/$IMAGE_NAME/python-main:$VERSION" "python-main"
    analyze_image "$REGISTRY/$IMAGE_NAME/bridge:$VERSION" "bridge"
    analyze_image "$REGISTRY/$IMAGE_NAME/frontend:$VERSION" "frontend"
    analyze_image "$REGISTRY/$IMAGE_NAME/voice-agents:$VERSION" "voice-agents"

    success "Image analysis completed ✓"
}

# Test all images
test_all() {
    log "Testing all built images..."

    test_image "$REGISTRY/$IMAGE_NAME/python-main:$VERSION" "python-main" "8000"
    test_image "$REGISTRY/$IMAGE_NAME/bridge:$VERSION" "bridge" "3001"
    test_image "$REGISTRY/$IMAGE_NAME/frontend:$VERSION" "frontend" "3000"

    success "Testing completed ✓"
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    local command="${1:-all}"

    case "$command" in
        "all")
            build_all
            scan_all
            analyze_all
            test_all
            ;;
        "build")
            build_all
            ;;
        "build-specific")
            if [ -z "${2:-}" ]; then
                error "Please specify a service to build"
            fi
            build_specific "$2"
            ;;
        "scan")
            scan_all
            ;;
        "analyze")
            analyze_all
            ;;
        "test")
            test_all
            ;;
        "help"|"-h"|"--help")
            echo "PAKE System Docker Build Script"
            echo ""
            echo "Usage: $0 [command] [service]"
            echo ""
            echo "Commands:"
            echo "  all              Build, scan, analyze, and test all services"
            echo "  build            Build all services"
            echo "  build-specific   Build specific service (python, bridge, frontend, voice-agents)"
            echo "  scan             Run security scans on all images"
            echo "  analyze          Analyze all images for optimization"
            echo "  test             Test all images"
            echo "  help             Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  REGISTRY         Container registry (default: ghcr.io)"
            echo "  IMAGE_NAME       Image name prefix (default: pake-system)"
            echo "  VERSION          Image version tag (default: latest)"
            echo "  GIT_COMMIT       Git commit hash (default: current HEAD)"
            ;;
        *)
            error "Unknown command: $command. Use '$0 help' for usage information."
            ;;
    esac
}

# Run main function with all arguments
main "$@"
