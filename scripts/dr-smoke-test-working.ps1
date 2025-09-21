# DR Smoke Test for PAKE System - Working PowerShell Version
# Usage: .\scripts\dr-smoke-test-working.ps1

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
    $kubectlVersion = & kubectl version --client --output=json 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-TestResult "kubectl is available and working" "Success"
    } else {
        Write-TestResult "kubectl not found or not working" "Error"
    }
} catch {
    Write-TestResult "kubectl command failed" "Error"
}

Write-TestResult "Checking DR directory structure"
if (Test-Path $DR_DIR) {
    Write-TestResult "DR directory exists at: $DR_DIR" "Success"
} else {
    Write-TestResult "DR directory not found at: $DR_DIR" "Error"
    Write-Host "Cannot continue without DR directory" -ForegroundColor Red
    exit 1
}

# YAML validation
Write-TestHeader "YAML Syntax Validation"

Write-TestResult "Scanning for YAML files in DR directory"
$yamlFiles = Get-ChildItem -Path $DR_DIR -Filter "*.yaml" -Recurse -ErrorAction SilentlyContinue

if ($yamlFiles.Count -eq 0) {
    Write-TestResult "No YAML files found in DR directory" "Warning"
} else {
    Write-TestResult "Found $($yamlFiles.Count) YAML files to validate"
    
    foreach ($file in $yamlFiles) {
        $relativePath = $file.FullName.Replace($ROOT_DIR.Path + "\", "")
        Write-TestResult "Validating: $relativePath"
        
        try {
            $null = & kubectl apply --dry-run=client -f $file.FullName 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-TestResult "Valid YAML: $relativePath" "Success"
            } else {
                Write-TestResult "Invalid YAML: $relativePath" "Error"
                if ($Verbose) {
                    $errorOutput = & kubectl apply --dry-run=client -f $file.FullName 2>&1
                    Write-Host $errorOutput -ForegroundColor Red
                }
            }
        } catch {
            Write-TestResult "Validation failed: $relativePath" "Error"
        }
    }
}

# Check key component files
Write-TestHeader "Key Component Files Check"

$keyFiles = @(
    @{Path="failover\failover-controller.yaml"; Required=$true},
    @{Path="replication\postgres-replication.yaml"; Required=$true},
    @{Path="replication\postgres-snapshot-cron.yaml"; Required=$true},
    @{Path="replication\vector-export-cron.yaml"; Required=$true},
    @{Path="replication\object-sync-deployment.yaml"; Required=$true},
    @{Path="chaos\random-pod-kill-cron.yaml"; Required=$false},
    @{Path="chaos\network-partition-job.yaml"; Required=$false},
    @{Path="validation\restore-validate-job.yaml"; Required=$false},
    @{Path="compliance\audit-config.yaml"; Required=$false},
    @{Path="runbooks.md"; Required=$true}
)

foreach ($fileInfo in $keyFiles) {
    $file = $fileInfo.Path
    $required = $fileInfo.Required
    $fullPath = Join-Path $DR_DIR $file
    
    Write-TestResult "Checking: $file"
    
    if (Test-Path $fullPath) {
        $fileItem = Get-Item $fullPath
        $sizeKB = [math]::Round($fileItem.Length / 1024, 1)
        Write-TestResult "Found $file (Size: ${sizeKB}KB)" "Success"
    } else {
        if ($required) {
            Write-TestResult "Missing required file: $file" "Error"
        } else {
            Write-TestResult "Missing optional file: $file" "Warning"
        }
    }
}

# Check monitoring files
Write-TestHeader "Monitoring Files Check"

$monitoringDir = Join-Path $ROOT_DIR "kubernetes\infrastructure\monitoring"
$monitoringFiles = @(
    "grafana-dr-dashboards.json",
    "alerting-rules-rto-rpo.yaml",
    "alerting-rules-backup-validation.yaml",
    "alerting-rules-compliance.yaml",
    "exporter-dr-metrics.yaml"
)

foreach ($file in $monitoringFiles) {
    $fullPath = Join-Path $monitoringDir $file
    Write-TestResult "Checking monitoring file: $file"
    
    if (Test-Path $fullPath) {
        Write-TestResult "Found monitoring file: $file" "Success"
    } else {
        Write-TestResult "Missing monitoring file: $file" "Warning"
    }
}

# Test cluster connectivity (optional)
Write-TestHeader "Cluster Connectivity Test"

Write-TestResult "Testing Kubernetes cluster connection"
try {
    $null = & kubectl cluster-info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-TestResult "Cluster is accessible" "Success"
        
        # Check namespace
        Write-TestResult "Checking namespace: $NAMESPACE"
        $null = & kubectl get namespace $NAMESPACE 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-TestResult "Namespace '$NAMESPACE' exists" "Success"
        } else {
            Write-TestResult "Namespace '$NAMESPACE' not found" "Warning"
            Write-Host "   💡 Create with: kubectl create namespace $NAMESPACE" -ForegroundColor Yellow
        }
        
        # Test dry-run deployment
        Write-TestResult "Testing dry-run deployment of DR components"
        $tempFile = [System.IO.Path]::GetTempFileName()
        try {
            Get-ChildItem -Path $DR_DIR -Filter "*.yaml" -Recurse | ForEach-Object {
                Get-Content $_.FullName | Out-File -Append -FilePath $tempFile
                "---" | Out-File -Append -FilePath $tempFile
            }
            
            $null = & kubectl apply --dry-run=server -f $tempFile 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-TestResult "Dry-run deployment successful" "Success"
            } else {
                Write-TestResult "Dry-run deployment has issues" "Warning"
            }
        } finally {
            Remove-Item $tempFile -ErrorAction SilentlyContinue
        }
        
    } else {
        Write-TestResult "Cluster not accessible (continuing with offline validation)" "Warning"
    }
} catch {
    Write-TestResult "Cannot test cluster connectivity" "Warning"
}

# Configuration validation
Write-TestHeader "Configuration Validation"

# Check if runbooks contain required sections
$runbooksPath = Join-Path $DR_DIR "runbooks.md"
if (Test-Path $runbooksPath) {
    $runbooksContent = Get-Content $runbooksPath -Raw
    $requiredSections = @(
        "Automated Failover",
        "Data Replication", 
        "Chaos Engineering",
        "Backup Validation",
        "Compliance",
        "Post-Mortem"
    )
    
    foreach ($section in $requiredSections) {
        if ($runbooksContent -match $section) {
            Write-TestResult "Runbooks contain '$section' section" "Success"
        } else {
            Write-TestResult "Runbooks missing '$section' section" "Warning"
        }
    }
}

# Final summary
Write-TestHeader "Test Results Summary"

$total = $successCount + $warningCount + $errorCount

Write-Host ""
Write-Host "📊 Test Results:" -ForegroundColor White
Write-Host "   ✅ Successes: $successCount" -ForegroundColor Green
Write-Host "   ⚠️  Warnings:  $warningCount" -ForegroundColor Yellow  
Write-Host "   ❌ Errors:    $errorCount" -ForegroundColor Red
Write-Host "   📈 Total:     $total" -ForegroundColor White

Write-Host ""
Write-Host "📋 Recommendations:" -ForegroundColor White

if ($errorCount -gt 0) {
    Write-Host ""
    Write-Host "❌ CRITICAL ISSUES DETECTED" -ForegroundColor Red
    Write-Host "   👉 Fix $errorCount error(s) before deploying to production" -ForegroundColor Red
    Write-Host "   👉 Review YAML syntax and missing required components" -ForegroundColor Red
}

if ($warningCount -gt 0) {
    Write-Host ""
    Write-Host "⚠️  WARNINGS DETECTED" -ForegroundColor Yellow
    Write-Host "   👉 Review $warningCount warning(s) for optional components" -ForegroundColor Yellow
    Write-Host "   👉 Consider creating missing namespaces and optional files" -ForegroundColor Yellow
}

if ($successCount -ge 10) {
    Write-Host ""
    Write-Host "✅ CORE INFRASTRUCTURE HEALTHY" -ForegroundColor Green
    Write-Host "   👉 DR infrastructure appears ready for deployment" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor White
Write-Host "   1. Address any critical errors shown above" -ForegroundColor White
Write-Host "   2. Review warnings and create missing optional components" -ForegroundColor White
Write-Host "   3. Test deployment: kubectl apply -f kubernetes/infrastructure/disaster-recovery/" -ForegroundColor White
Write-Host "   4. Verify monitoring: kubectl get pods -n disaster-recovery" -ForegroundColor White

# Set exit code based on results
Write-Host ""
if ($errorCount -gt 0) {
    Write-Host "🚫 SMOKE TEST FAILED" -ForegroundColor Red -BackgroundColor Black
    Write-Host "   Fix critical errors before proceeding" -ForegroundColor Red
    exit 1
} elseif ($warningCount -gt 5) {
    Write-Host "⚠️  SMOKE TEST PASSED WITH WARNINGS" -ForegroundColor Yellow -BackgroundColor Black
    Write-Host "   Review warnings before production deployment" -ForegroundColor Yellow
    exit 2
} else {
    Write-Host "✅ SMOKE TEST PASSED" -ForegroundColor Green -BackgroundColor Black
    Write-Host "   DR infrastructure ready for deployment" -ForegroundColor Green
    exit 0
}

