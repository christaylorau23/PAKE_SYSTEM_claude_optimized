
# Updated GitHub Actions Workflow with Proper Secrets Management

# Add this to your workflow files in the env section:
env:
  # Non-sensitive configuration
  PYTHON_VERSION: '3.12'
  NODE_VERSION: '22.18.0'
  REGISTRY_URL: 'ghcr.io'
  IMAGE_NAME: 'pake-system'

  # Sensitive secrets (from GitHub repository secrets)
  SECRET_KEY: ${{ secrets.SECRET_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  REDIS_URL: ${{ secrets.REDIS_URL }}
  API_KEY: ${{ secrets.API_KEY }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}

  # API Keys
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

  # Optional API Keys
  DID_API_KEY: ${{ secrets.DID_API_KEY }}
  HEYGEN_API_KEY: ${{ secrets.HEYGEN_API_KEY }}

  # Webhook Security
  WEBHOOK_SECRET: ${{ secrets.WEBHOOK_SECRET }}

  # HashiCorp Vault Configuration
  VAULT_ADDR: ${{ secrets.VAULT_ADDR }}
  VAULT_ROLE_ID: ${{ secrets.VAULT_ROLE_ID }}
  VAULT_SECRET_ID: ${{ secrets.VAULT_SECRET_ID }}
