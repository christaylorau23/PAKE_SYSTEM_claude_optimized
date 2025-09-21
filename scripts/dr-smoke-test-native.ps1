<#
.SYNOPSIS
  Disaster Recovery Smoke Test (PowerShell version)

.DESCRIPTION
  - Validates YAML syntax (dry-run)
  - Ensures DR namespace exists
  - Verifies key DR components (failover, replication, chaos, validation, compliance)
  - Confirms Prometheus rules and Grafana dashboard presence
  Lightweight cluster-safe pre-deployment check.

.USAGE
  .\scripts\dr-smoke-test-native.ps1
#>

# Fail on errors
$ErrorActionPreference = "Stop"

$Namespace = "disaster-recovery"
$RootDir   = (git rev-parse --show-toplevel).Trim()
$DRDir     = Join-Path $RootDir "kubernetes\infrastructure\disaster-recovery"

Write-Host "=> Running DR smoke tests..."
Write-Host "Namespace: $Namespace"
Write-Host "Root Dir: $RootDir"

# -------------------------------------------------------------
# 1. YAML validation
# -------------------------------------------------------------
Write-Host "[INFO] Validating YAML syntax..."
Get-ChildItem -Path $DRDir -Recurse -Filter *.yaml | ForEach-Object {
    Write-Host " - Checking $($_.FullName)"
    kubectl apply --dry-run=client -f $_.FullName | Out-Null
}
Write-Host "[SUCCESS] YAML syntax valid."

# -------------------------------------------------------------
# 2. Ensure namespace exists (if cluster accessible)
# -------------------------------------------------------------
Write-Host "[INFO] Checking cluster connectivity..."
try {
    $clusterInfo = kubectl cluster-info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Cluster accessible."
        $nsExists = kubectl get ns $Namespace 2>$null
        if (-not $nsExists) {
            Write-Host "[WARNING] Namespace $Namespace does not exist. Creating..."
            kubectl create ns $Namespace | Out-Null
        } else {
            Write-Host "[SUCCESS] Namespace $Namespace exists."
        }
    } else {
        Write-Host "[WARNING] Cluster not accessible - skipping namespace and component checks."
        $nsExists = $false
    }
} catch {
    Write-Host "[WARNING] Cluster not accessible - skipping namespace and component checks."
    $nsExists = $false
}

# -------------------------------------------------------------
# 3. Component presence & status checks
# -------------------------------------------------------------
function Check-Component($Type, $Name) {
    Write-Host "[INFO] Checking $Type/$Name..."
    $exists = kubectl get $Type -n $Namespace $Name 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [SUCCESS] Found $Type/$Name"
    } else {
        Write-Host "   [ERROR] Missing $Type/$Name"
    }
}

if ($nsExists -ne $false) {
    # Failover
    Check-Component "deployment" "failover-controller"

    # Replication
    Check-Component "cronjob" "postgres-snapshot"
    Check-Component "cronjob" "vector-export"
    Check-Component "deployment" "object-sync"

    # Chaos
    Check-Component "cronjob" "chaos-random-pod-kill"

    # Validation
    Check-Component "job" "restore-validation"

    # Compliance
    Check-Component "cronjob" "compliance-attestation"
} else {
    Write-Host "[INFO] Skipping component checks - cluster not accessible."
}

Write-Host ""

# -------------------------------------------------------------
# 4. Prometheus rules (if monitoring stack present)
# -------------------------------------------------------------
Write-Host "[INFO] Checking PrometheusRule CRDs (if available)..."
$crdExists = kubectl get crd prometheusrules.monitoring.coreos.com 2>$null
if ($LASTEXITCODE -eq 0) {
    $rules = kubectl get prometheusrule -n $Namespace 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] PrometheusRule objects detected."
    } else {
        Write-Host "[WARNING] No PrometheusRule objects in $Namespace."
    }
} else {
    Write-Host "[WARNING] PrometheusRule CRD not installed, skipping check."
}
Write-Host ""

# -------------------------------------------------------------
# 5. Grafana dashboards placeholder check
# -------------------------------------------------------------
$DashboardFile = Join-Path $DRDir "monitoring\grafana-dr-dashboards.json"
if (Test-Path $DashboardFile) {
    Write-Host "[SUCCESS] Grafana DR dashboard JSON exists."
} else {
    Write-Host "[ERROR] Grafana DR dashboard JSON missing."
}
Write-Host ""

# -------------------------------------------------------------
# Final result
# -------------------------------------------------------------
Write-Host "[COMPLETE] DR smoke tests completed."
Write-Host "Review [ERROR] warnings before proceeding with deployment."
