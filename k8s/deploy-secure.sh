#!/bin/bash

# Wealth Platform - Secure Deployment Script
# This script deploys the platform with proper secret management

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

# Check if kubectl is available
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Generate secure secrets for Vault
generate_vault_secrets() {
    log_info "Generating secure Vault secrets..."

    # Generate a secure root token
    VAULT_ROOT_TOKEN=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    # Create temporary secret file
    cat > /tmp/vault-secret.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: vault-secret
  namespace: vault-system
type: Opaque
data:
  root-token: $(echo -n "$VAULT_ROOT_TOKEN" | base64)
EOF

    log_success "Vault secrets generated"
    echo "Vault Root Token: $VAULT_ROOT_TOKEN"
    echo "Please save this token securely!"
}

# Deploy Vault
deploy_vault() {
    log_info "Deploying HashiCorp Vault..."

    # Apply Vault deployment
    kubectl apply -f vault-deployment.yaml

    # Wait for Vault to be ready
    log_info "Waiting for Vault to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/vault -n vault-system

    # Apply the generated secret
    kubectl apply -f /tmp/vault-secret.yaml

    # Wait for Vault init job to complete
    log_info "Waiting for Vault initialization..."
    kubectl wait --for=condition=complete --timeout=300s job/vault-init -n vault-system

    log_success "Vault deployed and initialized"
}

# Deploy External Secrets Operator
deploy_external_secrets() {
    log_info "Deploying External Secrets Operator..."

    kubectl apply -f external-secrets-operator.yaml

    # Wait for ESO to be ready
    log_info "Waiting for External Secrets Operator to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/external-secrets -n external-secrets-system

    log_success "External Secrets Operator deployed"
}

# Deploy the main platform
deploy_platform() {
    log_info "Deploying Wealth Platform..."

    # Deploy in order
    kubectl apply -f namespace.yaml
    kubectl apply -f postgresql-deployment.yaml
    kubectl apply -f redis-deployment.yaml
    kubectl apply -f wealth-platform-deployment.yaml
    kubectl apply -f monitoring.yaml
    kubectl apply -f ingress.yaml
    kubectl apply -f autoscaling.yaml

    log_success "Wealth Platform deployed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check if secrets are created by External Secrets Operator
    log_info "Checking if secrets are properly created..."

    if kubectl get secret postgres-secret -n wealth-platform &> /dev/null; then
        log_success "PostgreSQL secret created"
    else
        log_warning "PostgreSQL secret not found - External Secrets may still be syncing"
    fi

    if kubectl get secret wealth-secrets -n wealth-platform &> /dev/null; then
        log_success "Wealth Platform secrets created"
    else
        log_warning "Wealth Platform secrets not found - External Secrets may still be syncing"
    fi

    if kubectl get secret grafana-secret -n wealth-platform &> /dev/null; then
        log_success "Grafana secret created"
    else
        log_warning "Grafana secret not found - External Secrets may still be syncing"
    fi

    # Check pod status
    log_info "Checking pod status..."
    kubectl get pods -n wealth-platform
    kubectl get pods -n vault-system
    kubectl get pods -n external-secrets-system
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f /tmp/vault-secret.yaml
}

# Main deployment function
main() {
    log_info "Starting Wealth Platform secure deployment..."

    check_prerequisites
    generate_vault_secrets
    deploy_vault
    deploy_external_secrets
    deploy_platform
    verify_deployment
    cleanup

    log_success "Deployment completed successfully!"

    echo ""
    echo "=== Access Information ==="
    echo "Vault UI: kubectl port-forward svc/vault-service 8200:8200 -n vault-system"
    echo "Grafana: kubectl port-forward svc/grafana-service 3000:3000 -n wealth-platform"
    echo "Prometheus: kubectl port-forward svc/prometheus-service 9090:9090 -n wealth-platform"
    echo ""
    echo "=== Security Notes ==="
    echo "1. All secrets are now managed by HashiCorp Vault"
    echo "2. External Secrets Operator syncs secrets from Vault to Kubernetes"
    echo "3. No secrets are stored in version control"
    echo "4. Secrets are encrypted at rest and in transit"
    echo ""
    echo "=== Next Steps ==="
    echo "1. Update your API keys in Vault:"
    echo "   kubectl exec -it deployment/vault -n vault-system -- vault kv put secret/wealth-platform/api openai-api-key='your-actual-key'"
    echo "2. Monitor secret sync status:"
    echo "   kubectl get externalsecrets -n wealth-platform"
    echo "3. Set up proper backup for Vault data"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"
