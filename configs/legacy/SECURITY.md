# Wealth Platform - Security Documentation

## Overview

This document outlines the security measures implemented in the Wealth Platform, particularly focusing on secret management and secure deployment practices.

## Security Vulnerability Fixed

### Problem
The original Kubernetes manifests contained hardcoded, base64-encoded secrets directly in the YAML files:
- Database REDACTED_SECRETs (`WealthPass!2025`, `ReplicaPass!2025`)
- API keys (Firecrawl, OpenAI, Alpha Vantage)
- Grafana admin REDACTED_SECRET (`WealthDashboard!!!`)

This created a critical security vulnerability as these secrets were committed to version control.

### Solution
Implemented enterprise-grade secret management using:
1. **HashiCorp Vault** - Secure secret storage
2. **External Secrets Operator** - Kubernetes-native secret synchronization
3. **Kubernetes RBAC** - Proper access controls
4. **Encryption at rest and in transit**

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HashiCorp     │    │   External       │    │   Kubernetes    │
│   Vault         │◄───┤   Secrets        │◄───┤   Secrets       │
│   (Secret Store)│    │   Operator       │    │   (Applications)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Components

### 1. HashiCorp Vault (`vault-deployment.yaml`)
- **Purpose**: Centralized secret storage
- **Features**:
  - Encryption at rest
  - Audit logging
  - Access policies
  - Kubernetes authentication
- **Namespace**: `vault-system`

### 2. External Secrets Operator (`external-secrets-operator.yaml`)
- **Purpose**: Synchronizes secrets from Vault to Kubernetes
- **Features**:
  - Automatic secret refresh
  - Kubernetes-native integration
  - RBAC enforcement
- **Namespace**: `external-secrets-system`

### 3. Secret Management
- **PostgreSQL Secrets**: Database credentials and replication REDACTED_SECRETs
- **API Secrets**: External service API keys
- **Grafana Secrets**: Monitoring dashboard credentials

## Deployment Process

### Prerequisites
- Kubernetes cluster with RBAC enabled
- `kubectl` configured and accessible
- `openssl` for secure token generation

### Secure Deployment
```bash
# Make the deployment script executable
chmod +x deploy-secure.sh

# Run the secure deployment
./deploy-secure.sh
```

### Manual Deployment Steps
1. **Deploy Vault**:
   ```bash
   kubectl apply -f vault-deployment.yaml
   ```

2. **Deploy External Secrets Operator**:
   ```bash
   kubectl apply -f external-secrets-operator.yaml
   ```

3. **Deploy Platform Components**:
   ```bash
   kubectl apply -f namespace.yaml
   kubectl apply -f postgresql-deployment.yaml
   kubectl apply -f wealth-platform-deployment.yaml
   kubectl apply -f monitoring.yaml
   ```

## Secret Management

### Adding New Secrets
1. **Add to Vault**:
   ```bash
   kubectl exec -it deployment/vault -n vault-system -- \
     vault kv put secret/wealth-platform/new-service \
     api-key="your-secret-key"
   ```

2. **Create ExternalSecret**:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: new-service-secret
     namespace: wealth-platform
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: vault-backend
       kind: ClusterSecretStore
     target:
       name: new-service-secret
       creationPolicy: Owner
     data:
     - secretKey: api-key
       remoteRef:
         key: wealth-platform/new-service
         property: api-key
   ```

### Updating Existing Secrets
```bash
# Update secret in Vault
kubectl exec -it deployment/vault -n vault-system -- \
  vault kv put secret/wealth-platform/api \
  openai-api-key="new-api-key"

# External Secrets Operator will automatically sync
```

## Security Best Practices

### 1. Access Control
- **Principle of Least Privilege**: Services only access required secrets
- **RBAC**: Kubernetes role-based access control
- **Service Accounts**: Dedicated service accounts for each component

### 2. Secret Rotation
- **Automatic Refresh**: External Secrets Operator refreshes secrets every hour
- **Manual Rotation**: Update secrets in Vault for immediate rotation
- **Audit Trail**: All secret access is logged

### 3. Network Security
- **Internal Communication**: Vault and ESO communicate within cluster
- **TLS Encryption**: All communications are encrypted
- **Network Policies**: Restrict pod-to-pod communication

### 4. Monitoring
- **Secret Access Logs**: Monitor who accesses what secrets
- **Failed Access Attempts**: Alert on unauthorized access attempts
- **Secret Sync Status**: Monitor External Secrets Operator health

## Troubleshooting

### Common Issues

#### 1. Secrets Not Syncing
```bash
# Check External Secrets Operator status
kubectl get externalsecrets -n wealth-platform

# Check ESO logs
kubectl logs deployment/external-secrets -n external-secrets-system

# Verify Vault connectivity
kubectl exec -it deployment/vault -n vault-system -- vault status
```

#### 2. Vault Authentication Issues
```bash
# Check Vault auth methods
kubectl exec -it deployment/vault -n vault-system -- \
  vault auth list

# Verify Kubernetes auth configuration
kubectl exec -it deployment/vault -n vault-system -- \
  vault read auth/kubernetes/config
```

#### 3. Permission Denied
```bash
# Check RBAC permissions
kubectl get clusterrole external-secrets -o yaml
kubectl get clusterrolebinding external-secrets -o yaml
```

## Production Considerations

### 1. High Availability
- **Vault Clustering**: Deploy Vault in HA mode for production
- **Backup Strategy**: Regular Vault data backups
- **Disaster Recovery**: Cross-region Vault replication

### 2. Performance
- **Secret Caching**: Configure appropriate cache TTL
- **Resource Limits**: Set proper CPU/memory limits
- **Monitoring**: Monitor secret access patterns

### 3. Compliance
- **Audit Logging**: Enable comprehensive audit logs
- **Secret Classification**: Implement secret classification policies
- **Retention Policies**: Define secret retention and rotation policies

## Security Checklist

- [ ] All hardcoded secrets removed from manifests
- [ ] Vault deployed and initialized
- [ ] External Secrets Operator deployed and configured
- [ ] Secrets syncing from Vault to Kubernetes
- [ ] RBAC policies applied
- [ ] Network policies configured
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Security documentation updated
- [ ] Team training completed

## Emergency Procedures

### Secret Compromise
1. **Immediate Response**:
   ```bash
   # Revoke compromised secret
   kubectl exec -it deployment/vault -n vault-system -- \
     vault kv delete secret/wealth-platform/compromised-service
   ```

2. **Generate New Secret**:
   ```bash
   # Create new secret
   kubectl exec -it deployment/vault -n vault-system -- \
     vault kv put secret/wealth-platform/compromised-service \
     new-api-key="new-secure-key"
   ```

3. **Verify Rotation**:
   ```bash
   # Check if new secret is synced
   kubectl get secret compromised-service-secret -n wealth-platform -o yaml
   ```

### Vault Recovery
1. **Check Vault Status**:
   ```bash
   kubectl exec -it deployment/vault -n vault-system -- vault status
   ```

2. **Restore from Backup**:
   ```bash
   # Restore Vault data from backup
   kubectl exec -it deployment/vault -n vault-system -- \
     vault operator unseal <unseal-key>
   ```

## Contact Information

For security-related questions or incidents:
- **Security Team**: security@wealth-platform.com
- **Emergency Contact**: +1-XXX-XXX-XXXX
- **Incident Response**: Follow company incident response procedures

---

**Last Updated**: 2025-01-27
**Version**: 1.0
**Classification**: Internal Use Only
