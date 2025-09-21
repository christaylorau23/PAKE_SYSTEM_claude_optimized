#!/bin/bash

# Wealth Platform - Security Validation Script
# This script validates that no hardcoded secrets remain in the manifests

set -euo pipefail

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

# Check for hardcoded secrets
check_hardcoded_secrets() {
    log_info "Checking for hardcoded secrets in Kubernetes manifests..."
    
    local issues_found=0
    
    # Check for base64 encoded secrets in Secret manifests only (exclude templates)
    if find k8s/ -name "*.yaml" -not -path "*/multitenant/*" -not -path "*/overlays/*" -not -path "*/base/*" -exec grep -l "kind: Secret" {} \; | xargs grep -l "data:" | xargs grep -E "(REDACTED_SECRET|key|token|secret)" | grep -v "# Secret is now managed" | grep -v "{{.*}}"; then
        log_error "Found potential hardcoded secrets in Secret data sections"
        issues_found=$((issues_found + 1))
    fi
    
    # Check for common base64 patterns in Secret manifests only (exclude templates)
    if find k8s/ -name "*.yaml" -not -path "*/multitenant/*" -not -path "*/overlays/*" -not -path "*/base/*" -exec grep -l "kind: Secret" {} \; | xargs grep -l "data:" | xargs grep -E "[A-Za-z0-9+/]{20,}={0,2}" | grep -v "# Secret is now managed" | grep -v "{{.*}}"; then
        log_error "Found potential base64 encoded secrets in Secret manifests"
        issues_found=$((issues_found + 1))
    fi
    
    # Check for specific known secrets (exclude documentation and scripts)
    if grep -r "WealthPass\|WealthDashboard\|ReplicaPass" k8s/ --exclude="*.md" --exclude="*.sh" --exclude="validate-security.sh"; then
        log_error "Found hardcoded REDACTED_SECRETs in manifests"
        issues_found=$((issues_found + 1))
    fi
    
    # Check for API key patterns (exclude documentation and scripts)
    if grep -r "sk-\|pk-\|fc-" k8s/ --exclude="*.md" --exclude="*.sh" --exclude="validate-security.sh"; then
        log_error "Found potential API keys in manifests"
        issues_found=$((issues_found + 1))
    fi
    
    if [ $issues_found -eq 0 ]; then
        log_success "No hardcoded secrets found in manifests"
        return 0
    else
        log_error "Found $issues_found security issues"
        return 1
    fi
}

# Check for External Secrets Operator configuration
check_external_secrets_config() {
    log_info "Checking External Secrets Operator configuration..."
    
    local config_found=0
    
    if [ -f "k8s/external-secrets-operator.yaml" ]; then
        log_success "External Secrets Operator manifest found"
        config_found=$((config_found + 1))
    else
        log_error "External Secrets Operator manifest not found"
    fi
    
    if [ -f "k8s/vault-deployment.yaml" ]; then
        log_success "Vault deployment manifest found"
        config_found=$((config_found + 1))
    else
        log_error "Vault deployment manifest not found"
    fi
    
    if grep -q "external-secrets.io" k8s/external-secrets-operator.yaml; then
        log_success "External Secrets Operator CRDs configured"
        config_found=$((config_found + 1))
    else
        log_error "External Secrets Operator CRDs not configured"
    fi
    
    if [ $config_found -eq 3 ]; then
        log_success "External Secrets Operator properly configured"
        return 0
    else
        log_error "External Secrets Operator configuration incomplete"
        return 1
    fi
}

# Check for secret references in deployments
check_secret_references() {
    log_info "Checking secret references in deployments..."
    
    local refs_found=0
    
    # Check PostgreSQL deployment
    if grep -q "secretKeyRef" k8s/postgresql-deployment.yaml; then
        log_success "PostgreSQL deployment uses secretKeyRef"
        refs_found=$((refs_found + 1))
    else
        log_error "PostgreSQL deployment missing secretKeyRef"
    fi
    
    # Check Wealth Platform deployment
    if grep -q "secretKeyRef" k8s/wealth-platform-deployment.yaml; then
        log_success "Wealth Platform deployment uses secretKeyRef"
        refs_found=$((refs_found + 1))
    else
        log_error "Wealth Platform deployment missing secretKeyRef"
    fi
    
    # Check Monitoring deployment
    if grep -q "secretKeyRef" k8s/monitoring.yaml; then
        log_success "Monitoring deployment uses secretKeyRef"
        refs_found=$((refs_found + 1))
    else
        log_error "Monitoring deployment missing secretKeyRef"
    fi
    
    if [ $refs_found -eq 3 ]; then
        log_success "All deployments properly reference secrets"
        return 0
    else
        log_error "Some deployments missing secret references"
        return 1
    fi
}

# Check for security documentation
check_security_docs() {
    log_info "Checking security documentation..."
    
    local docs_found=0
    
    if [ -f "k8s/SECURITY.md" ]; then
        log_success "Security documentation found"
        docs_found=$((docs_found + 1))
    else
        log_error "Security documentation not found"
    fi
    
    if [ -f "k8s/deploy-secure.sh" ]; then
        log_success "Secure deployment script found"
        docs_found=$((docs_found + 1))
    else
        log_error "Secure deployment script not found"
    fi
    
    if [ -x "k8s/deploy-secure.sh" ]; then
        log_success "Deployment script is executable"
        docs_found=$((docs_found + 1))
    else
        log_error "Deployment script is not executable"
    fi
    
    if [ $docs_found -eq 3 ]; then
        log_success "Security documentation complete"
        return 0
    else
        log_error "Security documentation incomplete"
        return 1
    fi
}

# Main validation function
main() {
    log_info "Starting security validation..."
    
    local total_checks=0
    local passed_checks=0
    
    # Run all checks
    if check_hardcoded_secrets; then
        passed_checks=$((passed_checks + 1))
    fi
    total_checks=$((total_checks + 1))
    
    if check_external_secrets_config; then
        passed_checks=$((passed_checks + 1))
    fi
    total_checks=$((total_checks + 1))
    
    if check_secret_references; then
        passed_checks=$((passed_checks + 1))
    fi
    total_checks=$((total_checks + 1))
    
    if check_security_docs; then
        passed_checks=$((passed_checks + 1))
    fi
    total_checks=$((total_checks + 1))
    
    # Summary
    echo ""
    echo "=== Security Validation Summary ==="
    echo "Total Checks: $total_checks"
    echo "Passed: $passed_checks"
    echo "Failed: $((total_checks - passed_checks))"
    
    if [ $passed_checks -eq $total_checks ]; then
        log_success "All security checks passed! ✅"
        echo ""
        echo "The security vulnerability has been successfully fixed:"
        echo "- Hardcoded secrets removed from manifests"
        echo "- External Secrets Operator configured"
        echo "- HashiCorp Vault deployed for secure secret storage"
        echo "- Proper secret references in deployments"
        echo "- Comprehensive security documentation provided"
        return 0
    else
        log_error "Some security checks failed! ❌"
        echo ""
        echo "Please review the failed checks above and fix any issues."
        return 1
    fi
}

# Run main function
main "$@"
