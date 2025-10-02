# HashiCorp Vault Integration

## Overview

The PAKE System now integrates with HashiCorp Vault for secure secrets management, eliminating hardcoded credentials from the codebase and providing enterprise-grade security for sensitive configuration values.

## Architecture

### Security Model
- **Defense in Depth**: Secrets are stored externally in Vault, not in code or environment files
- **Graceful Degradation**: System falls back to environment variables if Vault is unavailable
- **Environment Priority**: Environment variables override Vault values when both are present
- **Zero Hardcoded Secrets**: All sensitive data is externalized from the application

### Components

1. **Vault Client** (`src/pake_system/core/vault_client.py`)
   - Secure connection to HashiCorp Vault
   - Connection pooling and error handling
   - Caching for performance optimization

2. **Configuration Integration** (`src/pake_system/core/config.py`)
   - Automatic secrets loading from Vault
   - Environment variable fallback
   - Validation and error handling

3. **Migration Script** (`scripts/migrate_secrets_to_vault.py`)
   - Automated migration of existing secrets
   - Structured secret hierarchy by environment

## Setup Instructions

### 1. Start Vault Server

For development, use the Vault dev server:

```bash
# Start Vault dev server
docker run --cap-add=IPC_LOCK -d -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=dev-only-token' \
  --name vault-dev hashicorp/vault

# Verify Vault is running
curl http://127.0.0.1:8200/v1/sys/health
```

### 2. Migrate Secrets

Run the migration script to populate Vault with secrets:

```bash
poetry run python scripts/migrate_secrets_to_vault.py
```

### 3. Configure Application

Set environment variables for Vault connection:

```bash
export USE_VAULT=true
export VAULT_URL=http://127.0.0.1:8200
export VAULT_TOKEN=dev-only-token
```

## Secret Hierarchy

Secrets are organized in Vault with the following structure:

```
pake_system/
├── development/
│   ├── database/
│   │   └── url
│   ├── redis/
│   │   └── url
│   ├── security/
│   │   └── secret_key
│   └── api_keys/
│       └── firecrawl_api_key
├── staging/
│   └── [same structure]
└── production/
    └── [same structure]
```

## Configuration Behavior

### Priority Order
1. **Environment Variables** (highest priority)
2. **Vault Secrets** (if Vault is enabled and available)
3. **Default Values** (for non-sensitive configuration)

### Fallback Strategy
- If `USE_VAULT=false`: Use environment variables only
- If Vault is unavailable: Fall back to environment variables
- If neither available: Raise configuration error

## Testing

### Integration Tests

Run the Vault integration test suite:

```bash
poetry run python scripts/test_vault_integration.py
```

### Manual Testing

Test with Vault disabled:
```bash
export USE_VAULT=false
export SECRET_KEY=test-secret-key
export DATABASE_URL=postgresql://test:test@localhost/test
export REDIS_URL=redis://localhost:6379/1

poetry run python -c "from src.pake_system.core.config import get_settings; print(get_settings().SECRET_KEY)"
```

Test with Vault enabled:
```bash
export USE_VAULT=true
export VAULT_URL=http://127.0.0.1:8200
export VAULT_TOKEN=dev-only-token

poetry run python -c "from src.pake_system.core.config import get_settings; print(get_settings().SECRET_KEY)"
```

## Production Deployment

### Environment Variables Required

```bash
# Vault Configuration
USE_VAULT=true
VAULT_URL=https://vault.company.com
VAULT_TOKEN=<production-token>

# Optional: Override specific secrets
SECRET_KEY=<override-value>
DATABASE_URL=<override-value>
REDIS_URL=<override-value>
```

### Security Considerations

1. **Token Management**: Use short-lived tokens with appropriate policies
2. **Network Security**: Ensure Vault communication is encrypted (HTTPS)
3. **Access Control**: Implement proper Vault policies for secret access
4. **Monitoring**: Monitor Vault access logs for security auditing
5. **Backup**: Regular backup of Vault data and policies

## Troubleshooting

### Common Issues

1. **Vault Connection Failed**
   - Check `VAULT_URL` and `VAULT_TOKEN` environment variables
   - Verify Vault server is running and accessible
   - Check network connectivity

2. **Secret Not Found**
   - Verify secret path in Vault matches expected structure
   - Check Vault token has read permissions for the secret path
   - Run migration script to ensure secrets are populated

3. **Environment Variable Override Not Working**
   - Check environment variable names match configuration field names
   - Verify environment variables are set before application startup
   - Check for typos in variable names

### Debug Mode

Enable debug logging to troubleshoot Vault integration:

```bash
export PAKE_DEBUG=true
export USE_VAULT=true
```

## Migration from Environment Variables

If migrating from environment variable-based secrets:

1. **Audit Current Secrets**: Identify all hardcoded secrets in codebase
2. **Run Migration Script**: Populate Vault with existing secrets
3. **Update Configuration**: Set `USE_VAULT=true` in production
4. **Test Thoroughly**: Verify all functionality works with Vault
5. **Deploy Gradually**: Use feature flags to control rollout

## Benefits

- **Enhanced Security**: No secrets in code or version control
- **Centralized Management**: Single point of control for all secrets
- **Audit Trail**: Complete logging of secret access
- **Easy Rotation**: Update secrets without code changes
- **Environment Isolation**: Separate secrets per environment
- **Compliance**: Meets enterprise security requirements
