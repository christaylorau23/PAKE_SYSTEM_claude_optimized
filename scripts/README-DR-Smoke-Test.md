# DR Smoke Test Utility

## 🎯 Purpose

The `dr-smoke-test.sh` script provides a lightweight, cluster-safe validation utility for the PAKE System's Disaster Recovery infrastructure. It's designed to be run frequently during development to catch issues early.

## 🚀 Quick Start

```bash
# Make executable (first time only)
chmod +x scripts/dr-smoke-test.sh

# Run the smoke test
./scripts/dr-smoke-test.sh
```

## 📋 What It Checks

### 1. **Pre-flight Validation**
- ✅ kubectl availability and cluster connectivity
- ✅ Git repository detection
- ✅ Directory structure validation

### 2. **YAML Syntax Validation**
- ✅ All `.yaml` files in `disaster-recovery/` directory
- ✅ DR-related monitoring files
- ✅ Kubernetes dry-run validation

### 3. **Namespace Management**
- ✅ `disaster-recovery` namespace existence
- ✅ Auto-creation option if missing

### 4. **Component Health Checks**
- ✅ **Failover Controller**: Deployment and ConfigMap
- ✅ **Replication**: CronJobs for snapshots, exports, sync deployment
- ✅ **Chaos Engineering**: Pod kill, network partition, resource exhaustion
- ✅ **Validation**: Restore testing CronJobs
- ✅ **Compliance**: Attestation and audit CronJobs

### 5. **Monitoring Integration**
- ✅ Prometheus Operator CRD detection
- ✅ PrometheusRule and ServiceMonitor validation
- ✅ Prometheus API accessibility test

### 6. **Configuration Validation**
- ✅ Grafana dashboard JSON syntax
- ✅ DR runbooks existence and completeness
- ✅ Required secrets availability

### 7. **Deployment Simulation**
- ✅ Server-side dry-run of all DR components
- ✅ Conflict detection and validation

## 📊 Output Format

The script provides color-coded output with clear status indicators:

- 🔎 **Blue**: Information/progress messages
- ✅ **Green**: Successful checks
- ⚠️ **Yellow**: Warnings (non-critical issues)
- ❌ **Red**: Errors (critical issues requiring attention)

## 🎯 Exit Codes

| Exit Code | Meaning | Action Required |
|-----------|---------|------------------|
| `0` | All checks passed | ✅ Safe to deploy |
| `1` | Critical errors detected | ❌ Fix errors before deployment |
| `2` | Passed with significant warnings | ⚠️ Review warnings |

## 🔧 Usage Scenarios

### **After Code Changes**
```bash
# Quick validation after editing DR YAML files
./scripts/dr-smoke-test.sh
```

### **Pre-Deployment**
```bash
# Comprehensive check before merging/deploying
./scripts/dr-smoke-test.sh

# Check exit code
echo "Exit code: $?"
```

### **CI/CD Integration**
```yaml
# Add to your CI pipeline
steps:
  - name: DR Smoke Test
    run: |
      chmod +x scripts/dr-smoke-test.sh
      ./scripts/dr-smoke-test.sh
```

### **Development Workflow**
```bash
# Typical development cycle
git checkout -b feature/dr-enhancement
# ... make changes to DR YAML files ...
./scripts/dr-smoke-test.sh  # Validate changes
git add . && git commit -m "DR: Enhanced failover controller"
./scripts/dr-smoke-test.sh  # Final validation before push
git push origin feature/dr-enhancement
```

## 🛠️ Advanced Features

### **Component Status Details**
The script provides detailed status for each component:
- **Deployments**: Ready replicas ratio
- **CronJobs**: Schedule information
- **Jobs**: Execution status
- **Secrets**: Existence validation

### **Prometheus Integration**
- Port-forward testing to Prometheus
- Metrics endpoint validation
- Alert rule detection

### **Error Recovery**
- Graceful handling of missing components
- Automatic namespace creation option
- Non-blocking advanced checks

## 🐛 Troubleshooting

### **Common Issues**

#### **"kubectl not found"**
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

#### **"Cannot connect to cluster"**
```bash
# Check cluster context
kubectl config current-context
kubectl cluster-info
```

#### **"Namespace does not exist"**
The script will offer to create the `disaster-recovery` namespace automatically.

#### **"YAML syntax errors"**
Review the specific file mentioned in the error output:
```bash
kubectl apply --dry-run=client -f path/to/problematic-file.yaml
```

#### **"PrometheusRule CRD not installed"**
Install the Prometheus Operator:
```bash
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
```

### **Debug Mode**
For verbose output, run with debug flag:
```bash
bash -x scripts/dr-smoke-test.sh
```

## 🔄 Integration with Development Workflow

### **Git Hooks**
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
./scripts/dr-smoke-test.sh
if [ $? -ne 0 ]; then
    echo "DR smoke test failed. Commit aborted."
    exit 1
fi
```

### **IDE Integration**
Configure your IDE to run the smoke test:
- **VS Code**: Add to tasks.json
- **IntelliJ**: Add as External Tool
- **Vim**: Add as make target

### **Automation**
Create aliases for frequent use:
```bash
# Add to .bashrc or .zshrc
alias dr-test='./scripts/dr-smoke-test.sh'
alias dr-quick='./scripts/dr-smoke-test.sh | grep -E "(✅|❌|⚠️|🎉)"'
```

## 📈 Future Enhancements

The script can be extended with:

1. **Metrics Validation**: Query Prometheus for specific DR metrics
2. **Performance Testing**: Basic load testing of DR components
3. **Log Analysis**: Check component logs for errors
4. **Integration Testing**: End-to-end DR scenario testing
5. **Report Generation**: Export results to JSON/HTML format

## 🤝 Contributing

To enhance the smoke test:

1. Add new check functions following the existing pattern
2. Update success/warning/error counters appropriately
3. Include clear logging with appropriate color coding
4. Test thoroughly in different cluster environments
5. Update this README with new features

## 📞 Support

If you encounter issues with the smoke test:

1. Check the troubleshooting section above
2. Review component logs: `kubectl logs -n disaster-recovery <component-name>`
3. Validate YAML manually: `kubectl apply --dry-run=client -f <file>`
4. Test cluster connectivity: `kubectl cluster-info`

## 🔗 Related Documentation

- [DR Runbooks](../kubernetes/infrastructure/disaster-recovery/runbooks.md)
- [Chaos Engineering Guide](../kubernetes/infrastructure/disaster-recovery/chaos/README.md)
- [Compliance Documentation](../kubernetes/infrastructure/disaster-recovery/compliance/README.md)
- [Monitoring Setup](../kubernetes/infrastructure/monitoring/README.md)
