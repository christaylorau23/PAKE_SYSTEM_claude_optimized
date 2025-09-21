# PowerShell DR Smoke Test Usage Guide

## 🎯 Purpose

The `dr-smoke-test-native.ps1` script provides a native Windows PowerShell version of the disaster recovery smoke test, allowing you to validate DR components without needing WSL or Git Bash.

## 🚀 Quick Start

### Windows PowerShell
```powershell
# Navigate to project directory
cd D:\Projects\PAKE_SYSTEM

# Set execution policy for current session (if needed)
Set-ExecutionPolicy -Scope Process Bypass

# Run the smoke test
.\scripts\dr-smoke-test-native.ps1
```

### Alternative Execution
```powershell
# Run with explicit execution policy bypass
powershell -ExecutionPolicy Bypass -File .\scripts\dr-smoke-test-native.ps1
```

## 📋 What It Validates

### 1. **YAML Syntax Validation**
- ✅ All `.yaml` files in disaster-recovery directory
- ✅ Kubernetes dry-run validation with `kubectl apply --dry-run=client`

### 2. **Cluster Connectivity**
- ✅ Checks if kubectl can connect to cluster
- ✅ Gracefully handles offline scenarios

### 3. **Namespace Management**
- ✅ Verifies `disaster-recovery` namespace exists
- ✅ Creates namespace if missing (when cluster accessible)

### 4. **Core Components**
- ✅ **Failover**: deployment/failover-controller
- ✅ **Replication**: cronjob/postgres-snapshot, cronjob/vector-export, deployment/object-sync
- ✅ **Chaos**: cronjob/chaos-random-pod-kill
- ✅ **Validation**: job/restore-validation
- ✅ **Compliance**: cronjob/compliance-attestation

### 5. **Monitoring Integration**
- ✅ PrometheusRule CRD detection
- ✅ PrometheusRule objects validation

### 6. **Configuration Files**
- ✅ Grafana dashboard JSON existence check

## 📊 Output Format

The script provides clear status indicators:

- `[INFO]` - Information/progress messages
- `[SUCCESS]` - Successful checks
- `[WARNING]` - Non-critical issues
- `[ERROR]` - Critical issues requiring attention
- `[COMPLETE]` - Final status

## 🔧 Integration Examples

### Pre-Commit Hook
Add to your Git pre-commit hook:
```bash
#!/bin/bash
# For Windows environments
powershell -ExecutionPolicy Bypass -File ./scripts/dr-smoke-test-native.ps1
if [ $? -ne 0 ]; then
    echo "DR smoke test failed. Commit aborted."
    exit 1
fi
```

### CI/CD Pipeline
```yaml
# GitHub Actions example
steps:
  - name: DR Smoke Test (Windows)
    shell: powershell
    run: |
      Set-ExecutionPolicy -Scope Process Bypass
      .\scripts\dr-smoke-test-native.ps1
```

### Development Workflow
```powershell
# Quick validation after changes
.\scripts\dr-smoke-test-native.ps1

# Before pushing changes
git add .
.\scripts\dr-smoke-test-native.ps1
if ($LASTEXITCODE -eq 0) {
    git commit -m "DR: Updated configuration"
    git push
}
```

## 🛠️ Troubleshooting

### Common Issues

#### **Execution Policy Restricted**
```powershell
# Solution 1: Set for current process
Set-ExecutionPolicy -Scope Process Bypass

# Solution 2: Run with explicit bypass
powershell -ExecutionPolicy Bypass -File .\scripts\dr-smoke-test-native.ps1
```

#### **kubectl Not Found**
```powershell
# Verify kubectl installation
kubectl version --client

# Install kubectl if missing
# Download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
```

#### **Cluster Connection Errors**
```powershell
# Check cluster context
kubectl config current-context
kubectl cluster-info

# The script handles offline scenarios gracefully
```

## 🔄 Automation Ideas

### Scheduled Task
Create a Windows scheduled task to run periodic DR validation:
```powershell
# Register a scheduled task for weekly DR checks
Register-ScheduledTask -TaskName "DR-SmokeTest" -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am) -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File D:\Projects\PAKE_SYSTEM\scripts\dr-smoke-test-native.ps1")
```

### Batch File Wrapper
Create `dr-test.bat` for easy execution:
```batch
@echo off
cd /d D:\Projects\PAKE_SYSTEM
powershell -ExecutionPolicy Bypass -File .\scripts\dr-smoke-test-native.ps1
pause
```

## 📈 Next Steps

After running the smoke test successfully:

1. **Fix any [ERROR] items** before deploying to production
2. **Review [WARNING] items** and create missing optional components
3. **Set up monitoring** if PrometheusRule CRDs are missing
4. **Create Grafana dashboards** if the JSON file is missing
5. **Integrate into CI/CD pipeline** for automated validation

## 🤝 Contributing

To enhance the PowerShell smoke test:

1. Follow PowerShell best practices
2. Maintain consistent output formatting
3. Handle errors gracefully
4. Test in different Windows environments
5. Update this documentation for new features

## 📞 Support

For issues with the PowerShell smoke test:

1. Check execution policy settings
2. Verify kubectl installation and configuration
3. Review cluster connectivity
4. Validate YAML files manually with `kubectl apply --dry-run=client`
