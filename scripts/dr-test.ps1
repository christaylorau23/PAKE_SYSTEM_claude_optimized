# Simple DR Smoke Test for PAKE System
# Usage: .\scripts\dr-test.ps1

$NAMESPACE = "disaster-recovery"
$DR_DIR = "kubernetes\infrastructure\disaster-recovery"

$success = 0
$warnings = 0
$errors = 0

function Test-Result {
    param($msg, $type)
    switch ($type) {
        "OK" { Write-Host "✅ $msg" -ForegroundColor Green; $script:success++ }
        "WARN" { Write-Host "⚠️ $msg" -ForegroundColor Yellow; $script:warnings++ }
        "ERROR" { Write-Host "❌ $msg" -ForegroundColor Red; $script:errors++ }
        default { Write-Host "🔎 $msg" -ForegroundColor Cyan }
    }
}

function Test-Header {
    param($msg)
    Write-Host "`n=================================================================" -ForegroundColor Blue
    Write-Host "🚀 $msg" -ForegroundColor Blue
    Write-Host "=================================================================" -ForegroundColor Blue
}

# Main test
Test-Header "DR Smoke Test - PAKE System"
Write-Host "Timestamp: $(Get-Date)"
Write-Host "Testing DR infrastructure..."

# Check kubectl
Test-Result "Checking kubectl availability"
try {
    $null = kubectl version --client 2>$null
    if ($LASTEXITCODE -eq 0) {
        Test-Result "kubectl is available" "OK"
    } else {
        Test-Result "kubectl not found" "ERROR"
    }
} catch {
    Test-Result "kubectl command failed" "ERROR"
}

# Check directories
Test-Result "Checking DR directory structure"
if (Test-Path $DR_DIR) {
    Test-Result "DR directory exists: $DR_DIR" "OK"
} else {
    Test-Result "DR directory missing: $DR_DIR" "ERROR"
    exit 1
}

# Check YAML files
Test-Header "YAML Validation"
$yamlFiles = Get-ChildItem -Path $DR_DIR -Filter "*.yaml" -Recurse
Test-Result "Found $($yamlFiles.Count) YAML files"

foreach ($file in $yamlFiles) {
    $name = $file.Name
    Test-Result "Validating: $name"
    
    try {
        $null = kubectl apply --dry-run=client -f $file.FullName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Test-Result "Valid: $name" "OK"
        } else {
            Test-Result "Invalid: $name" "ERROR"
        }
    } catch {
        Test-Result "Failed: $name" "ERROR"
    }
}

# Check key files
Test-Header "Key Component Files"
$keyFiles = @(
    "failover\failover-controller.yaml",
    "replication\postgres-replication.yaml",
    "replication\postgres-snapshot-cron.yaml", 
    "replication\vector-export-cron.yaml",
    "replication\object-sync-deployment.yaml",
    "chaos\random-pod-kill-cron.yaml",
    "validation\restore-validate-job.yaml",
    "compliance\audit-config.yaml",
    "runbooks.md"
)

foreach ($file in $keyFiles) {
    $path = Join-Path $DR_DIR $file
    if (Test-Path $path) {
        Test-Result "Found: $file" "OK"
    } else {
        Test-Result "Missing: $file" "WARN"
    }
}

# Check cluster (optional)
Test-Header "Cluster Connectivity"
try {
    $null = kubectl cluster-info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Test-Result "Cluster accessible" "OK"
        
        $null = kubectl get namespace $NAMESPACE 2>&1
        if ($LASTEXITCODE -eq 0) {
            Test-Result "Namespace '$NAMESPACE' exists" "OK"
        } else {
            Test-Result "Namespace '$NAMESPACE' missing" "WARN"
        }
    } else {
        Test-Result "Cluster not accessible" "WARN"
    }
} catch {
    Test-Result "Cannot test cluster" "WARN"
}

# Summary
Test-Header "Results Summary"
$total = $success + $warnings + $errors

Write-Host "📊 Results:"
Write-Host "   ✅ Success: $success" -ForegroundColor Green
Write-Host "   ⚠️  Warnings: $warnings" -ForegroundColor Yellow
Write-Host "   ❌ Errors: $errors" -ForegroundColor Red
Write-Host "   📈 Total: $total"

Write-Host "`n📋 Status:"
if ($errors -gt 0) {
    Write-Host "🚫 FAILED - Fix $errors critical error(s)" -ForegroundColor Red
    exit 1
} elseif ($warnings -gt 3) {
    Write-Host "⚠️ PASSED with warnings - Review $warnings warning(s)" -ForegroundColor Yellow
    exit 2
} else {
    Write-Host "✅ PASSED - DR infrastructure ready" -ForegroundColor Green
    exit 0
}

