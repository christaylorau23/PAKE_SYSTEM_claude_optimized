#!/bin/bash
# Configuration Validation Script for PAKE System
# Validates Kustomize configurations and Docker Compose files

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
PROJECT_ROOT="$(dirname "$DEPLOY_DIR")"

# Logging function
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

# Check required tools
check_tools() {
    log "Checking required tools..."

    local tools=("kubectl" "kustomize" "docker" "docker-compose")
    local missing_tools=()

    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        else
            success "$tool is installed"
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
}

# Validate Kubernetes configurations
validate_k8s() {
    log "Validating Kubernetes configurations..."

    local environments=("development" "staging" "production")
    local validation_errors=0

    for env in "${environments[@]}"; do
        log "Validating $env environment..."

        local overlay_dir="$DEPLOY_DIR/k8s/overlays/$env"
        if [ ! -d "$overlay_dir" ]; then
            error "Environment directory not found: $overlay_dir"
            ((validation_errors++))
            continue
        fi

        # Test kustomize build
        if kustomize build "$overlay_dir" > /dev/null 2>&1; then
            success "Kustomize build successful for $env"
        else
            error "Kustomize build failed for $env"
            ((validation_errors++))
            continue
        fi

        # Validate with kubectl (dry-run)
        if kubectl apply --dry-run=client -k "$overlay_dir" > /dev/null 2>&1; then
            success "kubectl validation successful for $env"
        else
            warning "kubectl validation failed for $env (cluster may not be available)"
        fi

        # Check for required files
        local required_files=("kustomization.yaml")
        for file in "${required_files[@]}"; do
            if [ -f "$overlay_dir/$file" ]; then
                success "$env has required file: $file"
            else
                error "$env missing required file: $file"
                ((validation_errors++))
            fi
        done
    done

    return $validation_errors
}

# Validate Docker configurations
validate_docker() {
    log "Validating Docker configurations..."

    local validation_errors=0

    # Check base configuration
    local base_compose="$DEPLOY_DIR/docker/base/docker-compose.base.yml"
    if [ -f "$base_compose" ]; then
        if docker-compose -f "$base_compose" config > /dev/null 2>&1; then
            success "Base Docker Compose configuration is valid"
        else
            error "Base Docker Compose configuration is invalid"
            ((validation_errors++))
        fi
    else
        error "Base Docker Compose file not found: $base_compose"
        ((validation_errors++))
    fi

    # Check environment overrides
    local environments=("development" "staging" "production")
    for env in "${environments[@]}"; do
        local overlay_compose="$DEPLOY_DIR/docker/overlays/$env/docker-compose.override.yml"
        if [ -f "$overlay_compose" ]; then
            if docker-compose -f "$base_compose" -f "$overlay_compose" config > /dev/null 2>&1; then
                success "Docker Compose configuration is valid for $env"
            else
                error "Docker Compose configuration is invalid for $env"
                ((validation_errors++))
            fi
        else
            warning "Docker Compose override not found for $env: $overlay_compose"
        fi
    done

    return $validation_errors
}

# Validate configuration consistency
validate_consistency() {
    log "Validating configuration consistency..."

    local validation_errors=0

    # Check if service names match between Docker and K8s
    log "Checking service name consistency..."

    # Extract service names from base Docker Compose
    local docker_services
    docker_services=$(docker-compose -f "$DEPLOY_DIR/docker/base/docker-compose.base.yml" config --services 2>/dev/null || echo "")

    if [ -n "$docker_services" ]; then
        success "Found Docker services: $docker_services"
    else
        warning "Could not extract Docker services"
    fi

    # Check for common configuration issues
    log "Checking for common configuration issues..."

    # Check for hardcoded REDACTED_SECRETs in non-development configs
    if grep -r "changeme\|REDACTED_SECRET123\|secret123" "$DEPLOY_DIR/k8s/overlays/production" "$DEPLOY_DIR/k8s/overlays/staging" 2>/dev/null; then
        error "Found hardcoded REDACTED_SECRETs in production/staging configurations"
        ((validation_errors++))
    else
        success "No hardcoded REDACTED_SECRETs found in production/staging"
    fi

    # Check for missing environment variables
    local required_env_vars=("DATABASE_PASSWORD" "REDIS_PASSWORD" "JWT_SECRET_KEY")
    for env_var in "${required_env_vars[@]}"; do
        if grep -r "$env_var" "$DEPLOY_DIR/k8s/base" > /dev/null 2>&1; then
            success "Environment variable $env_var is referenced in configuration"
        else
            warning "Environment variable $env_var not found in base configuration"
        fi
    done

    return $validation_errors
}

# Generate validation report
generate_report() {
    local k8s_errors=$1
    local docker_errors=$2
    local consistency_errors=$3
    local total_errors=$((k8s_errors + docker_errors + consistency_errors))

    log "Generating validation report..."

    echo ""
    echo "=================================="
    echo "   CONFIGURATION VALIDATION REPORT"
    echo "=================================="
    echo ""
    echo "Kubernetes Configurations:"
    if [ $k8s_errors -eq 0 ]; then
        success "All Kubernetes configurations are valid"
    else
        error "$k8s_errors Kubernetes validation errors found"
    fi

    echo ""
    echo "Docker Configurations:"
    if [ $docker_errors -eq 0 ]; then
        success "All Docker configurations are valid"
    else
        error "$docker_errors Docker validation errors found"
    fi

    echo ""
    echo "Configuration Consistency:"
    if [ $consistency_errors -eq 0 ]; then
        success "Configuration consistency checks passed"
    else
        error "$consistency_errors consistency errors found"
    fi

    echo ""
    echo "=================================="
    if [ $total_errors -eq 0 ]; then
        success "ALL VALIDATIONS PASSED ✅"
        echo "Your configurations are ready for deployment!"
    else
        error "VALIDATION FAILED ❌"
        echo "Found $total_errors total errors. Please fix them before deployment."
    fi
    echo "=================================="

    return $total_errors
}

# Main execution
main() {
    log "Starting PAKE System configuration validation..."

    # Check tools
    check_tools

    # Run validations
    local k8s_errors=0
    local docker_errors=0
    local consistency_errors=0

    validate_k8s || k8s_errors=$?
    validate_docker || docker_errors=$?
    validate_consistency || consistency_errors=$?

    # Generate report
    generate_report $k8s_errors $docker_errors $consistency_errors

    # Exit with appropriate code
    local total_errors=$((k8s_errors + docker_errors + consistency_errors))
    exit $total_errors
}

# Run main function
main "$@"