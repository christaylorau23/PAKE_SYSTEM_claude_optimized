# Migration Guide: Legacy to Standardized Configuration

This guide helps you migrate from the legacy configuration system to the new Kustomize-based standardized configuration management.

## 🔄 Migration Overview

### **What Changed**

| Legacy System | New Standardized System |
|---------------|-------------------------|
| 11+ scattered requirements.txt files | Single `pyproject.toml` with Poetry |
| Duplicate K8s YAML files in root | Unified `deploy/k8s/base/` + overlays |
| Multiple docker-compose files | Base + environment overlays |
| Hardcoded environment values | ConfigMaps + external secrets |
| Manual deployment procedures | Automated deployment scripts |

### **Migration Benefits**

- ✅ **Zero Duplication**: Single source of truth for all configurations
- ✅ **Drift Prevention**: Consistent deployments across environments
- ✅ **Security**: External secret management integration
- ✅ **Validation**: Automated configuration validation
- ✅ **Simplicity**: One-command deployments

## 📦 Step-by-Step Migration

### **Phase 1: Backup and Preparation**

1. **Backup existing configurations**:
   ```bash
   # Already done during implementation
   ls configs/legacy/
   # Contains: k8s/, docker-compose*.yml, requirements*.txt
   ```

2. **Verify new structure**:
   ```bash
   # New standardized structure
   tree deploy/
   ```

3. **Install required tools**:
   ```bash
   # For Kubernetes deployments
   curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash

   # For Poetry (Python dependencies)
   curl -sSL https://install.python-poetry.org | python3 -
   ```

### **Phase 2: Environment Migration**

#### **Development Environment**

1. **Stop legacy services**:
   ```bash
   # Stop old Docker Compose setup
   docker-compose down

   # Or stop old Kubernetes deployment
   kubectl delete namespace pake-system 2>/dev/null || true
   ```

2. **Deploy with new system**:
   ```bash
   # Validate new configuration
   deploy/scripts/validate-config.sh

   # Deploy development environment
   deploy/scripts/deploy.sh -e development
   ```

3. **Verify deployment**:
   ```bash
   # Check pods/services
   kubectl get pods -n pake-system

   # Or for Docker
   docker-compose ps
   ```

#### **Staging Environment**

1. **Coordinate with team**:
   ```bash
   # Announce maintenance window
   echo "Staging environment will be updated to new configuration system"
   ```

2. **Backup staging data** (if needed):
   ```bash
   # PostgreSQL backup
   kubectl exec -n pake-system postgres-0 -- pg_dump -U pake_user pake_system > staging-backup.sql
   ```

3. **Deploy new staging**:
   ```bash
   deploy/scripts/deploy.sh -e staging
   ```

4. **Run integration tests**:
   ```bash
   # Run your existing integration test suite
   poetry run pytest tests/integration/ -v
   ```

#### **Production Environment**

⚠️ **Production migration requires careful planning and coordination**

1. **Pre-migration checklist**:
   - [ ] Team approval for maintenance window
   - [ ] Complete backup of production data
   - [ ] Test migration procedure in staging
   - [ ] Rollback plan prepared
   - [ ] External secrets configured (Vault/ESO)

2. **Production migration**:
   ```bash
   # Validate production configuration
   deploy/scripts/deploy.sh -e production -v

   # Dry run to see changes
   deploy/scripts/deploy.sh -e production -d

   # Deploy production (requires confirmation)
   deploy/scripts/deploy.sh -e production
   ```

3. **Post-migration verification**:
   ```bash
   # Health checks
   kubectl get pods -n pake-system
   curl https://api.pake.yourdomain.com/health

   # Monitor metrics
   kubectl port-forward -n pake-system svc/pake-backend-service 9090:9090
   ```

### **Phase 3: Team Onboarding**

#### **Update Development Workflows**

1. **Poetry for Python dependencies**:
   ```bash
   # Old way
   pip install -r requirements.txt

   # New way
   poetry install --with dev,trends
   poetry shell
   ```

2. **New deployment commands**:
   ```bash
   # Old way
   kubectl apply -f k8s/
   docker-compose up -d

   # New way
   deploy/scripts/deploy.sh -e development
   deploy/scripts/deploy.sh -e development -p docker
   ```

3. **Configuration validation**:
   ```bash
   # Always validate before deployment
   deploy/scripts/validate-config.sh
   ```

#### **Update CI/CD Pipelines**

1. **GitHub Actions / GitLab CI**:
   ```yaml
   # .github/workflows/deploy.yml
   - name: Validate Configuration
     run: deploy/scripts/validate-config.sh

   - name: Deploy to Staging
     run: deploy/scripts/deploy.sh -e staging -f
   ```

2. **Jenkins Pipeline**:
   ```groovy
   stage('Validate') {
       steps {
           sh 'deploy/scripts/validate-config.sh'
       }
   }

   stage('Deploy') {
       steps {
           sh 'deploy/scripts/deploy.sh -e ${ENVIRONMENT} -f'
       }
   }
   ```

## 🔧 Configuration Updates

### **Adding New Services**

#### **Legacy Way** (Don't do this anymore)
```bash
# Multiple files to update
echo "service: ..." >> k8s/service.yaml
echo "service: ..." >> docker-compose.yml
echo "service: ..." >> docker-compose.production.yml
# Risk of inconsistency
```

#### **New Standardized Way**
```bash
# 1. Add to base configuration
cat > deploy/k8s/base/new-service.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: new-service
# ... service definition
EOF

# 2. Update base kustomization
echo "  - new-service.yaml" >> deploy/k8s/base/kustomization.yaml

# 3. Add environment-specific patches if needed
# deploy/k8s/overlays/production/production-patches.yaml

# 4. Validate and deploy
deploy/scripts/validate-config.sh
deploy/scripts/deploy.sh -e development
```

### **Managing Secrets**

#### **Legacy Way** (Insecure)
```yaml
# Hardcoded in YAML files
env:
  - name: DATABASE_PASSWORD
    value: "hardcoded-REDACTED_SECRET"  # ❌ Security risk
```

#### **New Standardized Way**
```yaml
# Development (placeholder)
env:
  - name: DATABASE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: pake-secrets
        key: DATABASE_PASSWORD

# Production (External Secrets Operator)
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

### **Environment Configuration**

#### **Legacy Way** (Error-prone)
```bash
# Manual environment variables
export DATABASE_HOST=localhost
export REDIS_HOST=localhost
# Risk of forgetting variables
```

#### **New Standardized Way**
```yaml
# Centralized ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: pake-config
data:
  DATABASE_HOST: "postgres-service"
  REDIS_HOST: "redis-service"
  LOG_LEVEL: "info"

# Environment-specific overlays
configMapGenerator:
  - name: pake-config
    behavior: merge
    literals:
      - LOG_LEVEL=debug  # Development override
```

## 🚨 Troubleshooting Migration Issues

### **Common Problems and Solutions**

#### **1. "Kustomize build failed"**
```bash
# Problem: YAML syntax errors
kustomize build deploy/k8s/overlays/production

# Solution: Validate YAML syntax
yamllint deploy/k8s/base/*.yaml
```

#### **2. "Secret not found"**
```bash
# Problem: Missing secrets in new environment
kubectl get secrets -n pake-system

# Solution: Check secret generation/external secrets
kubectl describe externalsecret pake-secrets -n pake-system
```

#### **3. "Service unavailable after migration"**
```bash
# Problem: Service not starting
kubectl logs -n pake-system deployment/pake-backend

# Solution: Check environment variables and config
kubectl describe pod -n pake-system -l app.kubernetes.io/name=pake-backend
```

#### **4. "Docker Compose configuration invalid"**
```bash
# Problem: Override file conflicts
docker-compose -f deploy/docker/base/docker-compose.base.yml \
               -f deploy/docker/overlays/production/docker-compose.override.yml \
               config

# Solution: Check YAML formatting and service names
```

### **Rollback Procedure**

If migration fails and you need to rollback:

1. **Restore legacy configurations**:
   ```bash
   # Copy back legacy files
   cp configs/legacy/docker-compose.yml .
   cp -r configs/legacy/k8s/ .
   ```

2. **Deploy legacy system**:
   ```bash
   # Kubernetes
   kubectl apply -f k8s/

   # Docker
   docker-compose up -d
   ```

3. **Investigate and fix issues**:
   ```bash
   # Check logs from migration attempt
   kubectl logs -n pake-system --previous deployment/pake-backend
   ```

## 📋 Migration Checklist

### **Pre-Migration**
- [ ] Backup all existing configurations
- [ ] Install required tools (kubectl, kustomize, poetry)
- [ ] Test new configuration in development
- [ ] Update CI/CD pipelines
- [ ] Train team on new workflows
- [ ] Prepare rollback plan

### **During Migration**
- [ ] Stop legacy services
- [ ] Validate new configurations
- [ ] Deploy new system
- [ ] Verify service health
- [ ] Test critical functionality
- [ ] Monitor for errors

### **Post-Migration**
- [ ] Update documentation
- [ ] Remove legacy configuration files (after verification)
- [ ] Update team workflows
- [ ] Monitor for 24-48 hours
- [ ] Collect team feedback

## 🎯 Success Criteria

Migration is considered successful when:

- ✅ All services deploy and run correctly
- ✅ Configuration validation passes
- ✅ No configuration duplication exists
- ✅ Team can deploy using new commands
- ✅ CI/CD pipelines work with new system
- ✅ Production stability maintained
- ✅ Security posture improved (external secrets)

## 📞 Getting Help

If you encounter issues during migration:

1. **Check documentation**: Review `deploy/README.md`
2. **Validate configuration**: Run `deploy/scripts/validate-config.sh`
3. **Review logs**: Check application and deployment logs
4. **Test in development**: Always test changes in dev first
5. **Rollback if needed**: Use the rollback procedure above

---

**🎉 Welcome to standardized configuration management! This migration eliminates configuration drift and provides a robust foundation for PAKE System deployments.**