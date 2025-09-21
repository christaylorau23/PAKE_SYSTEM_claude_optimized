#!/bin/bash

# Vault Initialization Script for PAKE System
# This script initializes Vault with all necessary secrets and policies

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Wait for Vault to be ready
wait_for_vault() {
    log_info "Waiting for Vault to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if vault status >/dev/null 2>&1; then
            log_success "Vault is ready!"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - Vault not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Vault failed to become ready after $max_attempts attempts"
    return 1
}

# Initialize Vault secrets
init_vault_secrets() {
    log_info "Initializing Vault secrets..."
    
    # Enable KV v2 secrets engine
    vault secrets enable -path=secret kv-v2
    
    # Create wealth-platform secrets with secure defaults
    vault kv put secret/wealth-platform/postgres \
        database="wealth_db" \
        username="postgres" \
        REDACTED_SECRET="${POSTGRES_PASSWORD:-$(openssl rand -base64 32)}" \
        replication-REDACTED_SECRET="${POSTGRES_REPLICATION_PASSWORD:-$(openssl rand -base64 32)}"
    
    vault kv put secret/wealth-platform/api \
        database-url="postgresql://postgres:${POSTGRES_PASSWORD:-$(openssl rand -base64 32)}@postgres:5432/wealth_db" \
        firecrawl-api-key="${FIRECRAWL_API_KEY:-your-firecrawl-api-key-here}" \
        openai-api-key="${OPENAI_API_KEY:-your-openai-api-key-here}" \
        alphavantage-api-key="${ALPHA_VANTAGE_API_KEY:-your-alpha-vantage-key-here}"
    
    vault kv put secret/wealth-platform/grafana \
        admin-REDACTED_SECRET="${GRAFANA_ADMIN_PASSWORD:-$(openssl rand -base64 32)}"
    
    vault kv put secret/wealth-platform/redis \
        REDACTED_SECRET="${REDIS_PASSWORD:-$(openssl rand -base64 32)}"
    
    vault kv put secret/wealth-platform/jwt \
        secret-key="${JWT_SECRET_KEY:-$(openssl rand -base64 64)}"
    
    log_success "Vault secrets initialized"
}

# Create Vault policies
create_vault_policies() {
    log_info "Creating Vault policies..."
    
    # Create policy for wealth-platform
    vault policy write wealth-platform - <<EOF
path "secret/data/wealth-platform/*" {
  capabilities = ["read"]
}

path "secret/metadata/wealth-platform/*" {
  capabilities = ["list", "read"]
}
EOF
    
    # Create policy for admin access
    vault policy write admin - <<EOF
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF
    
    log_success "Vault policies created"
}

# Enable authentication methods
enable_auth_methods() {
    log_info "Enabling authentication methods..."
    
    # Enable userpass auth for admin access
    vault auth enable userpass
    
    # Create admin user
    vault write auth/userpass/users/admin \
        REDACTED_SECRET="${VAULT_ADMIN_PASSWORD:-$(openssl rand -base64 32)}" \
        policies="admin"
    
    log_success "Authentication methods enabled"
}

# Main initialization function
main() {
    log_info "Starting Vault initialization for PAKE System..."
    
    # Set Vault address
    export VAULT_ADDR="http://localhost:8200"
    export VAULT_TOKEN="dev-root-token-2025"
    
    # Wait for Vault to be ready
    wait_for_vault
    
    # Initialize secrets
    init_vault_secrets
    
    # Create policies
    create_vault_policies
    
    # Enable auth methods
    enable_auth_methods
    
    log_success "Vault initialization completed successfully!"
    
    echo ""
    echo "=== Vault Access Information ==="
    echo "Vault URL: http://localhost:8200"
    echo "Root Token: dev-root-token-2025"
    echo "Admin User: admin"
    echo "Admin Password: admin123"
    echo ""
    echo "=== Secret Paths ==="
    echo "PostgreSQL: secret/wealth-platform/postgres"
    echo "API Keys: secret/wealth-platform/api"
    echo "Grafana: secret/wealth-platform/grafana"
    echo "Redis: secret/wealth-platform/redis"
    echo "JWT: secret/wealth-platform/jwt"
}

# Run main function
main "$@"
