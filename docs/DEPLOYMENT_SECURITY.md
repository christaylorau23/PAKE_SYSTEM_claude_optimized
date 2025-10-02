# PAKE System - Deployment Security Guide

**Hardened containerization and deployment following defense-in-depth principles**

---

## Table of Contents

1. [Overview](#overview)
2. [Security Architecture](#security-architecture)
3. [Docker Security](#docker-security)
4. [Kubernetes Security](#kubernetes-security)
5. [Network Security](#network-security)
6. [Secrets Management](#secrets-management)
7. [Deployment Workflows](#deployment-workflows)
8. [Security Checklist](#security-checklist)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide documents the security-hardened deployment strategy for the PAKE System, implementing:

- **Multi-stage Docker builds** for minimal attack surface
- **Non-root container execution** (principle of least privilege)
- **Read-only root filesystems** where applicable
- **Kubernetes Security Contexts** with comprehensive restrictions
- **Network Policies** for zero-trust networking
- **Resource limits** to prevent DoS attacks
- **Security scanning** integration points

### Security Principles

1. **Least Privilege** - Run as non-root, drop all capabilities
2. **Defense in Depth** - Multiple security layers
3. **Zero Trust** - Default deny network policies
4. **Immutability** - Read-only filesystems
5. **Isolation** - Network and process separation

---

## Security Architecture

### Threat Model

**Protected Against:**
- Container escape attempts
- Privilege escalation
- Lateral movement
- Resource exhaustion attacks
- Network-based attacks
- Credential theft
- Supply chain attacks

**Defense Layers:**
1. **Image Layer** - Multi-stage builds, minimal base images
2. **Container Layer** - Non-root user, dropped capabilities
3. **Pod Layer** - Security contexts, resource limits
4. **Network Layer** - Network policies, service mesh
5. **Cluster Layer** - RBAC, admission controllers

---

## Docker Security

### Multi-Stage Builds

Our Dockerfiles use multi-stage builds to minimize the attack surface:

```dockerfile
# Stage 1: Builder (includes build tools)
FROM python:3.12-slim AS builder
RUN apt-get install build-essential
COPY . .
RUN poetry install

# Stage 2: Production (minimal runtime)
FROM python:3.12-slim AS production
COPY --from=builder /app/.venv /app/.venv
USER 1000:1000  # Non-root user
```

**Benefits:**
- Build tools not present in final image
- Smaller image size (50-70% reduction)
- Fewer vulnerabilities to scan
- Faster deployment times

### Non-Root User Execution

**All containers run as UID 1000 (non-root):**

```dockerfile
# Create non-root user
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -m -d /app -s /sbin/nologin appuser

# Switch to non-root
USER appuser
```

**Security Impact:**
- Prevents privilege escalation exploits
- Limits damage from container escape
- Complies with PCI-DSS, SOC 2, HIPAA requirements

### Read-Only Root Filesystem

Where possible, containers use read-only root filesystems:

```dockerfile
# In Dockerfile
RUN chmod -R 555 /app/src

# In Kubernetes
securityContext:
  readOnlyRootFilesystem: true
```

**Writable Directories:**
- `/app/logs` - Application logs
- `/app/cache` - Temporary cache
- `/tmp` - Temporary files

### Image Scanning

**Automated scanning in CI/CD:**

```bash
# Build image
docker build -f Dockerfile.production -t pake-system:latest .

# Scan for vulnerabilities
trivy image pake-system:latest --severity HIGH,CRITICAL

# Sign image (optional)
cosign sign pake-system:latest
```

**Recommended Tools:**
- **Trivy** - Comprehensive vulnerability scanner
- **Snyk** - Developer-first security
- **Grype** - Open-source scanner
- **Docker Scout** - Official Docker scanning

---

## Kubernetes Security

### Security Context

**Pod-level security:**

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
```

**Container-level security:**

```yaml
securityContext:
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

### Pod Security Standards

Apply the **Restricted** Pod Security Standard:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pake-system
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Service Accounts

**Minimal RBAC permissions:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pake-backend-sa
automountServiceAccountToken: false  # Disable unless needed
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pake-backend-role
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
  # Only grant what's absolutely necessary
```

### Resource Limits

**Prevent resource exhaustion attacks:**

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
    ephemeral-storage: "1Gi"
  limits:
    memory: "2Gi"
    cpu: "1000m"
    ephemeral-storage: "2Gi"
```

**QoS Classes:**
- **Guaranteed** (requests == limits) - Critical services
- **Burstable** (requests < limits) - Standard services
- **BestEffort** (no limits) - Non-critical only

---

## Network Security

### Network Policies

**Zero-trust networking with default deny:**

```yaml
# 1. Default deny all traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

# 2. Explicitly allow required traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8000
```

### Service Mesh (Optional)

For advanced security, consider a service mesh:

**Istio/Linkerd benefits:**
- mTLS between services
- Fine-grained authorization
- Traffic encryption
- Observability

```yaml
# Example: Istio mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

### Ingress Security

**TLS termination and security headers:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pake-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.2 TLSv1.3"
    nginx.ingress.kubernetes.io/ssl-ciphers: "HIGH:!aNULL:!MD5"
spec:
  tls:
    - hosts:
        - api.pake-system.com
      secretName: pake-tls
```

---

## Secrets Management

### Never Hardcode Secrets

❌ **Bad:**
```yaml
env:
  - name: DB_PASSWORD
    value: "mypassword123"
```

✅ **Good:**
```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: database-credentials
        key: password
```

### External Secrets Operator

**Sync secrets from external vaults:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: pake-secrets
spec:
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: pake-secrets
  data:
    - secretKey: database-password
      remoteRef:
        key: pake/prod/database
        property: password
```

**Supported backends:**
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager
- 1Password

### Secret Rotation

**Automate secret rotation:**

```bash
# Example: Rotate database password
kubectl create secret generic database-credentials \
  --from-literal=password=$(openssl rand -base64 32) \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new secret
kubectl rollout restart deployment/pake-backend
```

---

## Deployment Workflows

### Local Development

```bash
# 1. Build images
docker-compose -f docker-compose.secure.yml build

# 2. Start services
docker-compose -f docker-compose.secure.yml up -d

# 3. Check health
docker-compose ps
docker-compose logs -f backend

# 4. Cleanup
docker-compose -f docker-compose.secure.yml down -v
```

### CI/CD Pipeline

**GitHub Actions example:**

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          docker build -f Dockerfile.production \
            --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
            --build-arg GIT_COMMIT=${{ github.sha }} \
            -t pake-system:${{ github.sha }} .

      - name: Scan for vulnerabilities
        run: |
          docker run --rm \
            aquasec/trivy:latest image \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            pake-system:${{ github.sha }}

      - name: Push to registry
        run: |
          docker tag pake-system:${{ github.sha }} \
            registry.example.com/pake-system:${{ github.sha }}
          docker push registry.example.com/pake-system:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/pake-backend \
            pake-backend=registry.example.com/pake-system:${{ github.sha }} \
            -n pake-system
```

### Kubernetes Deployment

```bash
# 1. Apply namespace and base resources
kubectl apply -f k8s/security/namespace.yaml

# 2. Create secrets (from vault/external source)
kubectl apply -f k8s/security/secrets.yaml

# 3. Apply network policies (before deployments!)
kubectl apply -f k8s/security/network-policies.yaml

# 4. Deploy applications
kubectl apply -f k8s/security/backend-hardened.yaml

# 5. Verify deployment
kubectl get pods -n pake-system
kubectl describe pod <pod-name> -n pake-system

# 6. Check security context
kubectl get pod <pod-name> -n pake-system -o jsonpath='{.spec.securityContext}'
```

### Blue-Green Deployment

```bash
# Deploy new version alongside old
kubectl apply -f k8s/backend-v2.yaml

# Test new version
kubectl port-forward svc/backend-v2 8080:8000

# Switch traffic
kubectl patch service backend -p '{"spec":{"selector":{"version":"v2"}}}'

# Monitor for issues
kubectl logs -f -l app=backend,version=v2

# Rollback if needed
kubectl patch service backend -p '{"spec":{"selector":{"version":"v1"}}}'
```

---

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in vault/external secrets manager
- [ ] No hardcoded credentials in code or configs
- [ ] Docker images scanned for vulnerabilities (0 CRITICAL)
- [ ] Images signed with cosign or similar
- [ ] Multi-stage Dockerfiles used
- [ ] Non-root users configured
- [ ] .dockerignore comprehensive
- [ ] Resource limits defined
- [ ] Health checks configured
- [ ] Logging configured

### Kubernetes Security

- [ ] Pod Security Standards enforced (restricted)
- [ ] Network Policies applied (default deny)
- [ ] RBAC roles with least privilege
- [ ] Service accounts with automountServiceAccountToken: false
- [ ] Security contexts with runAsNonRoot: true
- [ ] readOnlyRootFilesystem: true where possible
- [ ] All capabilities dropped
- [ ] seccomp profile applied
- [ ] Pod Disruption Budgets configured
- [ ] Admission controllers enabled (OPA/Gatekeeper)

### Runtime Security

- [ ] Runtime monitoring (Falco/Sysdig)
- [ ] Log aggregation (ELK/Loki)
- [ ] Metrics and alerting (Prometheus/Grafana)
- [ ] Audit logging enabled
- [ ] Intrusion detection configured
- [ ] Backup and disaster recovery tested
- [ ] Incident response plan documented

### Compliance

- [ ] OWASP Top 10 mitigations in place
- [ ] CIS Benchmarks followed
- [ ] PCI-DSS requirements met (if applicable)
- [ ] HIPAA requirements met (if applicable)
- [ ] GDPR compliance verified (if applicable)
- [ ] SOC 2 controls implemented (if applicable)

---

## Troubleshooting

### Container Won't Start

**Error: "Permission denied"**

```bash
# Check user/group IDs
kubectl exec -it <pod> -- id
# Should show: uid=1000 gid=1000

# Check file permissions
kubectl exec -it <pod> -- ls -la /app

# Solution: Ensure Dockerfile creates user correctly
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser ...
```

**Error: "Read-only file system"**

```bash
# Check security context
kubectl get pod <pod> -o yaml | grep readOnlyRootFilesystem

# Solution: Mount writable volume for required directories
volumeMounts:
  - name: tmp
    mountPath: /tmp
  - name: logs
    mountPath: /app/logs
```

### Network Policy Issues

**Pods can't communicate:**

```bash
# Check network policies
kubectl get networkpolicies -n pake-system

# Describe specific policy
kubectl describe networkpolicy backend-allow -n pake-system

# Test connectivity
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- \
  curl http://backend:8000/health

# Solution: Add explicit allow rule
```

### Security Context Violations

**Error: "container has runAsNonRoot and image will run as root"**

```bash
# Check what user the image runs as
docker inspect pake-system:latest | grep User

# Solution: Add USER directive to Dockerfile
USER 1000:1000
```

### Resource Limits

**Pods being OOM killed:**

```bash
# Check resource usage
kubectl top pods -n pake-system

# Check events
kubectl get events -n pake-system --sort-by='.lastTimestamp'

# Solution: Increase memory limits
resources:
  limits:
    memory: "4Gi"  # Increased from 2Gi
```

---

## Additional Resources

### Documentation
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

### Tools
- **Trivy** - Vulnerability scanner
- **Falco** - Runtime security
- **OPA/Gatekeeper** - Policy enforcement
- **Kyverno** - Kubernetes native policy
- **Kubescape** - Security posture scanning

### Training
- [CKSS (Certified Kubernetes Security Specialist)](https://www.cncf.io/certification/cks/)
- [Docker Security course](https://training.docker.com/security)
- [OWASP Kubernetes Security Testing Guide](https://owasp.org/www-project-kubernetes-top-ten/)

---

## Support

For security issues or questions:
1. Review this documentation
2. Check the troubleshooting section
3. Search existing issues on GitHub
4. Open a security advisory (for vulnerabilities)
5. Contact the security team

**Security Disclosure:** security@pake-system.com

---

*Last Updated: 2025-01-30*
*Document Version: 1.0.0*
