#!/bin/bash
# HashiCorp Vault Integration Script
# PAKE System - Phase 4 Implementation

set -euo pipefail

# Configuration
VAULT_ADDR="${VAULT_ADDR:-https://vault.pake-system.com}"
VAULT_ROLE_ID="${VAULT_ROLE_ID}"
VAULT_SECRET_ID="${VAULT_SECRET_ID}"
VAULT_PATH="secret/pake-system"

# Function to authenticate with Vault using JWT/OIDC
authenticate_vault() {
    echo "🔐 Authenticating with HashiCorp Vault..."

    # Get OIDC token from GitHub Actions
    if [ -n "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]; then
        echo "Using GitHub Actions OIDC token..."
        OIDC_TOKEN=$(curl -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN"             "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=vault" | jq -r .value)

        # Authenticate with Vault using OIDC
        VAULT_TOKEN=$(vault write -field=token auth/jwt/login             role="pake-system-role"             jwt="$OIDC_TOKEN")

        export VAULT_TOKEN
        echo "✅ Successfully authenticated with Vault"
    else
        echo "❌ No GitHub Actions OIDC token available"
        exit 1
    fi
}

# Function to retrieve secrets from Vault
get_secret() {
    local secret_name="$1"
    local secret_path="$VAULT_PATH/$secret_name"

    echo "🔑 Retrieving secret: $secret_name"

    if vault kv get -field=value "$secret_path" 2>/dev/null; then
        echo "✅ Successfully retrieved $secret_name"
    else
        echo "❌ Failed to retrieve $secret_name"
        return 1
    fi
}

# Function to export all required secrets as environment variables
export_secrets() {
    echo "📤 Exporting secrets as environment variables..."

    # Core secrets
    export SECRET_KEY=$(get_secret "jwt-secret")
    export DATABASE_URL=$(get_secret "database-url")
    export REDIS_URL=$(get_secret "redis-url")
    export API_KEY=$(get_secret "api-key")
    export DB_PASSWORD=$(get_secret "db-password")
    export REDIS_PASSWORD=$(get_secret "redis-password")

    # API Keys
    export ANTHROPIC_API_KEY=$(get_secret "anthropic-api-key")
    export GEMINI_API_KEY=$(get_secret "gemini-api-key")

    # Optional API Keys
    export DID_API_KEY=$(get_secret "did-api-key" || echo "")
    export HEYGEN_API_KEY=$(get_secret "heygen-api-key" || echo "")

    # Webhook Security
    export WEBHOOK_SECRET=$(get_secret "webhook-secret")

    echo "✅ All secrets exported successfully"
}

# Main execution
main() {
    echo "🚀 Starting HashiCorp Vault integration..."

    # Check required environment variables
    if [ -z "${VAULT_ROLE_ID:-}" ] || [ -z "${VAULT_SECRET_ID:-}" ]; then
        echo "❌ VAULT_ROLE_ID and VAULT_SECRET_ID must be set"
        exit 1
    fi

    # Authenticate with Vault
    authenticate_vault

    # Export secrets
    export_secrets

    echo "🎉 Vault integration completed successfully"
}

# Run main function
main "$@"
