# ====================================================================
# Disaster Recovery Smoke Test (PowerShell Version)
# Location: scripts/dr-smoke-test.ps1
#
# Purpose:
#   - Run basic pre-deployment checks on DR YAMLs
#   - Validate syntax, dry-run apply, and component health
#   - Quick sanity check before merging or deploying
#
# Usage:
#   .\scripts\dr-smoke-test.ps1
# ====================================================================

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Continue"
$NAMESPACE = "disaster-recovery"
$ROOT_DIR = Get-Location
$DR_DIR = Join-Path $ROOT_DIR "kubernetes\infrastructure\disaster-recovery"
$MONITORING_DIR = Join-Path $ROOT_DIR "kubernetes\infrastructure\monitoring"

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"

# Counters
$Script:SUCCESS_COUNT = 0
$Script:WARNING_COUNT = 0
$Script:ERROR_COUNT = 0

function Write-Info {
    param([string]$Message)
    Write-Host "🔎 $Message" -ForegroundColor $BLUE
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $GREEN
    $Script:SUCCESS_COUNT++
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor $YELLOW
    $Script:WARNING_COUNT++
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $RED
    $Script:ERROR_COUNT++
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor $BLUE
    Write-Host "🚀 $Message" -ForegroundColor $BLUE
    Write-Host "=================================================================" -ForegroundColor $BLUE
}

# Start smoke test
Write-Header "Disaster Recovery Smoke Test"
Write-Host "Namespace: $NAMESPACE"
Write-Host "Root Dir: $ROOT_DIR"
Write-Host "DR Dir: $DR_DIR"
Write-Host "Timestamp: $(Get-Date)"

# -------------------------------------------------------------
# 1. Pre-flight checks
# -------------------------------------------------------------
Write-Header "Pre-flight Checks"

Write-Info "Checking kubectl availability..."
try {
    $null = kubectl version --client 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "kubectl is available"
    } else {
        Write-Error-Custom "kubectl not found in PATH"
        exit 1
    }
} catch {
    Write-Error-Custom "kubectl not found in PATH"
    exit 1
}

Write-Info "Checking cluster connectivity..."
try {
    $null = kubectl cluster-info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Cluster connectivity verified"
    } else {
        Write-Warning "Cannot connect to Kubernetes cluster (continuing with offline checks)"
    }
} catch {
    Write-Warning "Cannot connect to Kubernetes cluster (continuing with offline checks)"
}

Write-Info "Checking DR directory structure..."
if (Test-Path $DR_DIR) {
    Write-Success "DR directory exists: $DR_DIR"
} else {
    Write-Error-Custom "DR directory not found: $DR_DIR"
    exit 1
}

# -------------------------------------------------------------
# 2. YAML Syntax Validation
# -------------------------------------------------------------
Write-Header "YAML Syntax Validation"

Write-Info "Finding YAML files in DR directory..."
$yamlFiles = Get-ChildItem -Path $DR_DIR -Filter "*.yaml" -Recurse
Write-Info "Found $($yamlFiles.Count) YAML files to validate"

foreach ($file in $yamlFiles) {
    $relativePath = $file.FullName.Replace($ROOT_DIR, "").TrimStart('\')
    Write-Info "Validating $relativePath"

    try {
        $result = kubectl apply --dry-run=client -f $file.FullName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ $relativePath"
        } else {
            Write-Error-Custom "✗ $relativePath - YAML syntax error"
            if ($Verbose) {
                Write-Host $result -ForegroundColor Red
            }
        }
    } catch {
        Write-Error-Custom "✗ $relativePath - Validation failed"
    }
}

# Check monitoring files
if (Test-Path $MONITORING_DIR) {
    Write-Info "Checking monitoring YAML files..."
    $monitoringFiles = Get-ChildItem -Path $MONITORING_DIR -Filter "*.yaml" -Recurse | Where-Object {
        $_.Name -match "(dr|disaster|backup)"
    }

    foreach ($file in $monitoringFiles) {
        $relativePath = $file.FullName.Replace($ROOT_DIR, "").TrimStart('\')
        Write-Info "Validating $relativePath"

        try {
            $result = kubectl apply --dry-run=client -f $file.FullName 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "✓ $relativePath"
            } else {
                Write-Error-Custom "✗ $relativePath"
            }
        } catch {
            Write-Error-Custom "✗ $relativePath - Validation failed"
        }
    }
}

# -------------------------------------------------------------
# 3. Component Presence Checks (if cluster accessible)
# -------------------------------------------------------------
Write-Header "Component Presence Checks"

function Test-Component {
    param(
        [string]$Type,
        [string]$Name,
        [bool]$Required = $true
    )

    Write-Info "Checking $Type/$Name..."
    try {
        $result = kubectl get $Type -n $NAMESPACE $Name 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Found $Type/$Name"
            return $true
        } else {
            if ($Required) {
                Write-Error-Custom "Missing $Type/$Name"
            } else {
                Write-Warning "Missing $Type/$Name (optional)"
            }
            return $false
        }
    } catch {
        if ($Required) {
            Write-Error-Custom "Cannot check $Type/$Name"
        } else {
            Write-Warning "Cannot check $Type/$Name (optional)"
        }
        return $false
    }
}

# Check namespace
Write-Info "Checking namespace '$NAMESPACE'..."
try {
    $null = kubectl get namespace $NAMESPACE 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Namespace '$NAMESPACE' exists"
    } else {
        Write-Warning "Namespace '$NAMESPACE' does not exist"
    }
} catch {
    Write-Warning "Cannot check namespace (cluster not accessible)"
}

# Core components (only if cluster is accessible)
try {
    $null = kubectl cluster-info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Checking core DR components..."
        Test-Component "deployment" "failover-controller"
        Test-Component "configmap" "failover-controller-config"

        Write-Info "Checking replication components..."
        Test-Component "cronjob" "postgres-snapshot"
        Test-Component "cronjob" "vector-export"
        Test-Component "deployment" "object-sync"

        Write-Info "Checking chaos components (optional)..."
        Test-Component "cronjob" "chaos-random-pod-kill" $false
        Test-Component "cronjob" "chaos-network-partition" $false

        Write-Info "Checking validation components (optional)..."
        Test-Component "cronjob" "restore-validation-full" $false
        Test-Component "cronjob" "restore-validation-quick" $false

        Write-Info "Checking compliance components (optional)..."
        Test-Component "cronjob" "compliance-attestation-monthly" $false
    }
} catch {
    Write-Warning "Skipping component checks - cluster not accessible"
}

# -------------------------------------------------------------
# 4. Configuration Files Check
# -------------------------------------------------------------
Write-Header "Configuration Files Check"

# Check Grafana dashboard
$dashboardFile = Join-Path $MONITORING_DIR "grafana-dr-dashboards.json"
Write-Info "Checking Grafana DR dashboard..."
if (Test-Path $dashboardFile) {
    try {
        $content = Get-Content $dashboardFile -Raw | ConvertFrom-Json
        Write-Success "Grafana DR dashboard JSON exists and is valid"
    } catch {
        Write-Error-Custom "Grafana DR dashboard JSON has syntax errors"
    }
} else {
    Write-Warning "Grafana DR dashboard JSON missing"
}

# Check runbooks
$runbooksFile = Join-Path $DR_DIR "runbooks.md"
Write-Info "Checking DR runbooks..."
if (Test-Path $runbooksFile) {
    $lines = (Get-Content $runbooksFile).Count
    Write-Success "DR runbooks exist ($lines lines)"
} else {
    Write-Error-Custom "DR runbooks missing"
}

# Check key YAML files exist
$keyFiles = @(
    "failover\failover-controller.yaml",
    "replication\postgres-replication.yaml",
    "replication\postgres-snapshot-cron.yaml",
    "replication\vector-export-cron.yaml",
    "replication\object-sync-deployment.yaml",
    "chaos\random-pod-kill-cron.yaml",
    "validation\restore-validate-job.yaml",
    "compliance\audit-config.yaml"
)

Write-Info "Checking key DR component files..."
foreach ($file in $keyFiles) {
    $fullPath = Join-Path $DR_DIR $file
    if (Test-Path $fullPath) {
        Write-Success "✓ $file"
    } else {
        Write-Warning "✗ $file (missing)"
    }
}

# -------------------------------------------------------------
# 5. Final Results
# -------------------------------------------------------------
Write-Header "Smoke Test Results Summary"

Write-Host "📊 Test Results:"
Write-Host "   ✅ Successes: $SUCCESS_COUNT" -ForegroundColor $GREEN
Write-Host "   ⚠️  Warnings:  $WARNING_COUNT" -ForegroundColor $YELLOW
Write-Host "   ❌ Errors:    $ERROR_COUNT" -ForegroundColor $RED
Write-Host "   📈 Total:     $($SUCCESS_COUNT + $WARNING_COUNT + $ERROR_COUNT)"

Write-Host ""
Write-Host "📋 Recommendations:"

if ($ERROR_COUNT -gt 0) {
    Write-Host "❌ $ERROR_COUNT critical errors detected" -ForegroundColor $RED
    Write-Host "   👉 Fix errors before deploying to production"
    Write-Host "   👉 Review YAML syntax and missing components"
}

if ($WARNING_COUNT -gt 0) {
    Write-Host "⚠️ $WARNING_COUNT warnings detected" -ForegroundColor $YELLOW
    Write-Host "   👉 Review warnings for optional components"
    Write-Host "   👉 Consider creating missing secrets/namespaces"
}

if ($SUCCESS_COUNT -gt 10) {
    Write-Host "🎉 Core DR infrastructure looks healthy" -ForegroundColor $GREEN
    Write-Host "   👉 Ready for deployment with warnings addressed"
}

# Exit with appropriate code
if ($ERROR_COUNT -gt 0) {
    Write-Host ""
    Write-Host "🚫 Smoke test FAILED due to critical errors" -ForegroundColor $RED
    exit 1
} elseif ($WARNING_COUNT -gt 5) {
    Write-Host ""
    Write-Host "⚠️ Smoke test PASSED with significant warnings" -ForegroundColor $YELLOW
    exit 2
} else {
    Write-Host ""
    Write-Host "✅ Smoke test PASSED - DR infrastructure ready" -ForegroundColor $GREEN
    exit 0
}
