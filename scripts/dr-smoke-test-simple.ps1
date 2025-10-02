# Simple DR Smoke Test for PAKE System
# PowerShell version for Windows compatibility

param(
    [switch]$Verbose = $false
)

$NAMESPACE = "disaster-recovery"
$ROOT_DIR = Get-Location
$DR_DIR = Join-Path $ROOT_DIR "kubernetes\infrastructure\disaster-recovery"

# Counters
$successCount = 0
$warningCount = 0
$errorCount = 0

function Write-TestResult {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )

    switch ($Type) {
        "Success" {
            Write-Host "✅ $Message" -ForegroundColor Green
            $script:successCount++
        }
        "Warning" {
            Write-Host "⚠️ $Message" -ForegroundColor Yellow
            $script:warningCount++
        }
        "Error" {
            Write-Host "❌ $Message" -ForegroundColor Red
            $script:errorCount++
        }
        default {
            Write-Host "🔎 $Message" -ForegroundColor Cyan
        }
    }
}

function Write-TestHeader {
    param([string]$Message)
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Blue
    Write-Host "🚀 $Message" -ForegroundColor Blue
    Write-Host "=================================================================" -ForegroundColor Blue
}

# Start test
Write-TestHeader "DR Smoke Test - PAKE System"
Write-Host "Timestamp: $(Get-Date)"
Write-Host "Namespace: $NAMESPACE"
Write-Host "DR Directory: $DR_DIR"

# Check prerequisites
Write-TestHeader "Prerequisites Check"

Write-TestResult "Checking kubectl availability"
try {
    $null = & kubectl version --client 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-TestResult "kubectl is available" "Success"
    } else {
        Write-TestResult "kubectl not found or not working" "Error"
    }
} catch {
    Write-TestResult "kubectl command failed" "Error"
}

Write-TestResult "Checking DR directory structure"
if (Test-Path $DR_DIR) {
    Write-TestResult "DR directory exists: $DR_DIR" "Success"
} else {
    Write-TestResult "DR directory not found: $DR_DIR" "Error"
    exit 1
}

# YAML validation
Write-TestHeader "YAML Validation"

Write-TestResult "Finding YAML files in DR directory"
$yamlFiles = Get-ChildItem -Path $DR_DIR -Filter "*.yaml" -Recurse -ErrorAction SilentlyContinue

if ($yamlFiles.Count -eq 0) {
    Write-TestResult "No YAML files found in DR directory" "Warning"
} else {
    Write-TestResult "Found $($yamlFiles.Count) YAML files to validate"

    foreach ($file in $yamlFiles) {
        $relativePath = $file.FullName.Replace("$ROOT_DIR\", "")
        Write-TestResult "Validating: $relativePath"

        try {
            $output = & kubectl apply --dry-run=client -f $file.FullName 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-TestResult "✓ $relativePath syntax OK" "Success"
            } else {
                Write-TestResult "✗ $relativePath has YAML errors" "Error"
                if ($Verbose) {
                    Write-Host $output -ForegroundColor Red
                }
            }
        } catch {
            Write-TestResult "✗ $relativePath validation failed" "Error"
        }
    }
}

# Check key component files
Write-TestHeader "Key Component Files Check"

$keyFiles = @(
    "failover\failover-controller.yaml",
    "replication\postgres-replication.yaml",
    "replication\postgres-snapshot-cron.yaml",
    "replication\vector-export-cron.yaml",
    "replication\object-sync-deployment.yaml",
    "chaos\random-pod-kill-cron.yaml",
    "chaos\network-partition-job.yaml",
    "validation\restore-validate-job.yaml",
    "compliance\audit-config.yaml",
    "runbooks.md"
)

foreach ($file in $keyFiles) {
    $fullPath = Join-Path $DR_DIR $file
    Write-TestResult "Checking: $file"

    if (Test-Path $fullPath) {
        $fileInfo = Get-Item $fullPath
        $sizeKB = [math]::Round($fileInfo.Length / 1KB, 1)
        Write-TestResult "✓ $file exists (${sizeKB}KB)" "Success"
    } else {
        Write-TestResult "✗ $file missing" "Warning"
    }
}

# Check cluster connectivity (if possible)
Write-TestHeader "Cluster Connectivity (Optional)"

Write-TestResult "Testing cluster connection"
try {
    $clusterInfo = & kubectl cluster-info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-TestResult "Cluster is accessible" "Success"

        # Check namespace
        Write-TestResult "Checking namespace: $NAMESPACE"
        $nsCheck = & kubectl get namespace $NAMESPACE 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-TestResult "Namespace '$NAMESPACE' exists" "Success"
        } else {
            Write-TestResult "Namespace '$NAMESPACE' not found" "Warning"
        }
    } else {
        Write-TestResult "Cluster not accessible (offline validation only)" "Warning"
    }
} catch {
    Write-TestResult "Cannot test cluster connectivity" "Warning"
}

# Final summary
Write-TestHeader "Test Results Summary"

$total = $successCount + $warningCount + $errorCount

Write-Host "📊 Results:" -ForegroundColor White
Write-Host "   ✅ Successes: $successCount" -ForegroundColor Green
Write-Host "   ⚠️  Warnings:  $warningCount" -ForegroundColor Yellow
Write-Host "   ❌ Errors:    $errorCount" -ForegroundColor Red
Write-Host "   📈 Total:     $total" -ForegroundColor White

Write-Host ""
Write-Host "📋 Status:" -ForegroundColor White

if ($errorCount -gt 0) {
    Write-Host "🚫 FAILED - Fix critical errors before proceeding" -ForegroundColor Red
    exit 1
} elseif ($warningCount -gt 3) {
    Write-Host "⚠️ PASSED with warnings - Review issues before deployment" -ForegroundColor Yellow
    exit 2
} else {
    Write-Host "✅ PASSED - DR infrastructure ready for deployment" -ForegroundColor Green
    exit 0
}
