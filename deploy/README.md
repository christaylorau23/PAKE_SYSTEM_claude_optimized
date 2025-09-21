# PAKE System - Standardized Configuration Management

This directory contains the unified configuration management system for the PAKE System, implementing Kustomize-based deployment patterns that eliminate configuration duplication and prevent deployment drift.

## 🏗️ Architecture Overview

### **Problem Solved**

- ❌ **Before**: 11+ scattered requirements files, duplicate Kubernetes manifests, inconsistent Docker Compose configurations
- ✅ **After**: Single source of truth with environment-specific overlays

### **Solution Benefits**

- **🎯 Zero Duplication**: Base configurations with environment overlays
- **🔒 Drift Prevention**: Consistent transformations via Kustomize
- **🛡️ Security**: External secret management integration
- **⚡ Simple Deployment**: One command deploys any environment
- **📊 Validation**: Automated consistency checks

## 📁 Directory Structure

```
deploy/
├── k8s/                          # Kubernetes configurations
│   ├── base/                     # Base configurations (shared)
│   │   ├── kustomization.yaml    # Base Kustomize config
│   │   ├── namespace.yaml        # Namespace and resource quotas
│   │   ├── configmap.yaml        # Application configuration
│   │   ├── secrets.yaml          # Secret templates (dev only)
│   │   ├── postgres.yaml         # PostgreSQL StatefulSet
│   │   ├── redis.yaml            # Redis StatefulSet
│   │   ├── backend.yaml          # PAKE Backend Deployment
│   │   ├── frontend.yaml         # PAKE Frontend Deployment
│   │   └── ingress.yaml          # Ingress and NetworkPolicy
│   └── overlays/                 # Environment-specific configurations
│       ├── development/          # Local development
│       │   ├── kustomization.yaml
│       │   ├── dev-config-patch.yaml
│       │   ├── dev-resources-patch.yaml
│       │   └── dev-security-patch.yaml
│       ├── staging/              # Pre-production testing
│       │   ├── kustomization.yaml
│       │   ├── staging-resources.yaml
│       │   └── staging-monitoring.yaml
│       └── production/           # Enterprise production
│           ├── kustomization.yaml
│           ├── production-resources.yaml
│           ├── production-security.yaml
│           ├── hpa.yaml          # Horizontal Pod Autoscaler
│           ├── vpa.yaml          # Vertical Pod Autoscaler
│           ├── monitoring.yaml   # Prometheus & Grafana
│           ├── backup.yaml       # Backup configurations
│           └── external-secrets.yaml # Vault integration
├── docker/                       # Docker Compose configurations
│   ├── base/
│   │   └── docker-compose.base.yml  # Base services definition
│   └── overlays/
│       ├── development/
│       │   └── docker-compose.override.yml
│       ├── staging/
│       │   └── docker-compose.override.yml
│       └── production/
│           └── docker-compose.override.yml
└── scripts/                      # Deployment automation
    ├── deploy.sh                 # Unified deployment script
    ├── validate-config.sh        # Configuration validation
    └── README.md                 # This file
```

## 🚀 Quick Start

### **Prerequisites**

For Kubernetes deployments:

```bash
# Install required tools
kubectl version --client
kustomize version
```

For Docker deployments:

```bash
# Verify Docker setup
docker --version
docker-compose --version
```

### **Basic Deployment**

```bash
# Development environment (Kubernetes)
./scripts/deploy.sh -e development

# Production environment (with confirmation)
./scripts/deploy.sh -e production

# Docker Compose deployment
./scripts/deploy.sh -e development -p docker

# Dry run (see what would be deployed)
./scripts/deploy.sh -e production -d

# Validation only
./scripts/deploy.sh -e production -v
```

## 🔧 Configuration Management

### **Environment Configurations**

| Environment     | Purpose               | Scale       | Security        | Secrets     |
| --------------- | --------------------- | ----------- | --------------- | ----------- |
| **Development** | Local development     | 1 replica   | Relaxed         | Placeholder |
| **Staging**     | Integration testing   | 2 replicas  | Production-like | External    |
| **Production**  | Enterprise deployment | 3+ replicas | Hardened        | Vault/ESO   |

### **Adding New Services**

1. **Create base configuration**:

   ```bash
   # Add service definition to k8s/base/
   echo "apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: new-service" > k8s/base/new-service.yaml
   ```

2. **Update base kustomization**:

   ```yaml
   # Add to k8s/base/kustomization.yaml
   resources:
     - new-service.yaml
   ```

3. **Add environment-specific patches**:

   ```yaml
   # k8s/overlays/production/production-patches.yaml
   - target:
       kind: Deployment
       name: new-service
     patch: |-
       - op: replace
         path: /spec/replicas
         value: 3
   ```

4. **Validate and deploy**:
   ```bash
   ./scripts/validate-config.sh
   ./scripts/deploy.sh -e development
   ```

### **Secret Management**

#### **Development (Placeholder Secrets)**

```yaml
# k8s/base/secrets.yaml
stringData:
  DATABASE_PASSWORD: 'dev-REDACTED_SECRET'
  JWT_SECRET_KEY: 'dev-jwt-secret'
```

#### **Production (External Secrets Operator)**

```yaml
# k8s/overlays/production/external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: pake-secrets
spec:
  secretStoreRef:
    name: vault-backend
  data:
    - secretKey: DATABASE_PASSWORD
      remoteRef:
        key: pake-system/database
        property: REDACTED_SECRET
```

## 📊 Deployment Scripts

### **Deploy Script Usage**

```bash
Usage: ./scripts/deploy.sh [OPTIONS]

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production)
    -p, --platform PLATFORM Deployment platform (kubernetes|docker) [default: kubernetes]
    -d, --dry-run           Perform a dry run without making changes
    -v, --validate-only     Only validate configurations without deploying
    -f, --force            Force deployment without confirmation
    -t, --timeout SECONDS  Deployment timeout in seconds [default: 600]
    -h, --help             Show this help message

EXAMPLES:
    ./scripts/deploy.sh -e development                    # Deploy to development
    ./scripts/deploy.sh -e production -d                  # Dry run production
    ./scripts/deploy.sh -e staging -p docker              # Deploy staging with Docker
    ./scripts/deploy.sh -e production -v                  # Validate production only
```

### **Validation Script**

```bash
# Validate all configurations
./scripts/validate-config.sh

# Output includes:
# ✅ Kustomize build validation
# ✅ Docker Compose validation
# ✅ Configuration consistency checks
# ✅ Security configuration validation
```

## 🔍 Advanced Usage

### **Kustomize Commands**

```bash
# Build specific environment
kustomize build k8s/overlays/production

# View differences between environments
diff <(kustomize build k8s/overlays/staging) \
     <(kustomize build k8s/overlays/production)

# Apply with kubectl
kubectl apply -k k8s/overlays/production
```

### **Docker Compose Commands**

```bash
# Build configuration
docker-compose -f docker/base/docker-compose.base.yml \
               -f docker/overlays/production/docker-compose.override.yml \
               config

# Deploy specific environment
cd docker/overlays/production
docker-compose -f ../../base/docker-compose.base.yml \
               -f docker-compose.override.yml \
               up -d
```

### **Monitoring Deployments**

```bash
# Kubernetes
kubectl get pods -n pake-system -w
kubectl logs -n pake-system deployment/pake-backend -f

# Docker Compose
docker-compose ps
docker-compose logs -f pake-backend
```

## 🛡️ Security Best Practices

### **Secret Management**

- ✅ Never commit secrets to version control
- ✅ Use External Secrets Operator in production
- ✅ Rotate secrets regularly
- ✅ Use least-privilege access

### **Network Security**

- ✅ NetworkPolicies restrict pod-to-pod communication
- ✅ Ingress with TLS termination
- ✅ Service mesh for production (optional)

### **Resource Security**

- ✅ Pod Security Standards
- ✅ Resource quotas and limits
- ✅ Non-root containers
- ✅ Read-only filesystems where possible

## 🔧 Troubleshooting

### **Common Issues**

#### **Kustomize Build Fails**

```bash
# Check syntax
kustomize build k8s/overlays/production --enable-helm

# Validate YAML
kubectl apply --dry-run=client -k k8s/overlays/production
```

#### **Docker Compose Fails**

```bash
# Check configuration
docker-compose config

# Check service dependencies
docker-compose ps
docker-compose logs service-name
```

#### **Secret Not Found**

```bash
# Check secret creation
kubectl get secrets -n pake-system

# Check External Secrets Operator
kubectl get externalsecrets -n pake-system
```

### **Getting Help**

1. **Validate configuration**: `./scripts/validate-config.sh`
2. **Check logs**: `kubectl logs -n pake-system deployment/pake-backend`
3. **Review documentation**: See main `CLAUDE.md` for detailed workflows
4. **Test locally**: Use development environment first

## 📚 Additional Resources

- **Main Documentation**: `../CLAUDE.md`
- **Legacy Configurations**: `../configs/legacy/`
- **Poetry Dependencies**: `../pyproject.toml`
- **Project README**: `../README.md`

---

**🎯 This standardized configuration management eliminates deployment drift and provides a single source of truth for all PAKE System deployments across development, staging, and production environments.**
