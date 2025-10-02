#!/usr/bin/env bash
# ====================================================================
# Disaster Recovery Smoke Test
# Location: scripts/dr-smoke-test.sh
#
# Purpose:
#   - Run basic pre-deployment checks on DR YAMLs
#   - Validate syntax, dry-run apply, and component health
#   - Quick sanity check before merging or deploying
#
# Usage:
#   ./scripts/dr-smoke-test.sh
# ====================================================================

set -euo pipefail

NAMESPACE="disaster-recovery"
ROOT_DIR="$(git rev-parse --show-toplevel)"
DR_DIR="$ROOT_DIR/kubernetes/infrastructure/disaster-recovery"
MONITORING_DIR="$ROOT_DIR/kubernetes/infrastructure/monitoring"
SCRIPTS_DIR="$ROOT_DIR/scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}🔎 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "\n${BLUE}=================================================================${NC}"
    echo -e "${BLUE}🚀 $1${NC}"
    echo -e "${BLUE}=================================================================${NC}"
}

# Initialize counters
SUCCESS_COUNT=0
WARNING_COUNT=0
ERROR_COUNT=0

increment_success() {
    ((SUCCESS_COUNT++))
}

increment_warning() {
    ((WARNING_COUNT++))
}

increment_error() {
    ((ERROR_COUNT++))
}

log_header "Disaster Recovery Smoke Test"
echo "Namespace: $NAMESPACE"
echo "Root Dir: $ROOT_DIR"
echo "DR Dir: $DR_DIR"
echo "Timestamp: $(date)"

# -------------------------------------------------------------
# 1. Pre-flight checks
# -------------------------------------------------------------
log_header "Pre-flight Checks"

log_info "Checking kubectl availability..."
if command -v kubectl >/dev/null 2>&1; then
    log_success "kubectl is available"
    increment_success
else
    log_error "kubectl not found in PATH"
    increment_error
    exit 1
fi

log_info "Checking cluster connectivity..."
if kubectl cluster-info >/dev/null 2>&1; then
    log_success "Cluster connectivity verified"
    increment_success
else
    log_error "Cannot connect to Kubernetes cluster"
    increment_error
    exit 1
fi

log_info "Checking git repository..."
if [ -d "$ROOT_DIR/.git" ]; then
    log_success "Git repository detected"
    increment_success
else
    log_warning "Not in a git repository, using current directory"
    ROOT_DIR="$(pwd)"
    DR_DIR="$ROOT_DIR/kubernetes/infrastructure/disaster-recovery"
    increment_warning
fi

# -------------------------------------------------------------
# 2. YAML Syntax Validation
# -------------------------------------------------------------
log_header "YAML Syntax Validation"

if [ ! -d "$DR_DIR" ]; then
    log_error "DR directory not found: $DR_DIR"
    increment_error
    exit 1
fi

log_info "Validating YAML syntax for all DR files..."
yaml_files=()
while IFS= read -r -d '' file; do
    yaml_files+=("$file")
done < <(find "$DR_DIR" -type f -name "*.yaml" -print0 2>/dev/null)

if [ ${#yaml_files[@]} -eq 0 ]; then
    log_warning "No YAML files found in $DR_DIR"
    increment_warning
else
    log_info "Found ${#yaml_files[@]} YAML files to validate"

    for file in "${yaml_files[@]}"; do
        relative_file="${file#$ROOT_DIR/}"
        log_info "Validating $relative_file"

        if kubectl apply --dry-run=client -f "$file" >/dev/null 2>&1; then
            log_success "✓ $relative_file"
            increment_success
        else
            log_error "✗ $relative_file - YAML syntax error"
            increment_error
            # Show the actual error
            kubectl apply --dry-run=client -f "$file" 2>&1 | head -3
        fi
    done
fi

# Also check monitoring YAML files
if [ -d "$MONITORING_DIR" ]; then
    log_info "Validating monitoring YAML files..."
    while IFS= read -r -d '' file; do
        if [[ "$file" == *"dr"* ]] || [[ "$file" == *"disaster"* ]] || [[ "$file" == *"backup"* ]]; then
            relative_file="${file#$ROOT_DIR/}"
            log_info "Validating $relative_file"

            if kubectl apply --dry-run=client -f "$file" >/dev/null 2>&1; then
                log_success "✓ $relative_file"
                increment_success
            else
                log_error "✗ $relative_file - YAML syntax error"
                increment_error
            fi
        fi
    done < <(find "$MONITORING_DIR" -type f -name "*.yaml" -print0 2>/dev/null)
fi

# -------------------------------------------------------------
# 3. Namespace Management
# -------------------------------------------------------------
log_header "Namespace Management"

log_info "Checking if namespace '$NAMESPACE' exists..."
if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    log_success "Namespace '$NAMESPACE' exists"
    increment_success
else
    log_warning "Namespace '$NAMESPACE' does not exist"
    increment_warning

    read -p "Create namespace '$NAMESPACE'? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if kubectl create namespace "$NAMESPACE"; then
            log_success "Created namespace '$NAMESPACE'"
            increment_success
        else
            log_error "Failed to create namespace '$NAMESPACE'"
            increment_error
        fi
    else
        log_warning "Skipping namespace creation - some checks may fail"
        increment_warning
    fi
fi

# -------------------------------------------------------------
# 4. Component Presence & Status Checks
# -------------------------------------------------------------
log_header "Component Presence & Status Checks"

check_component() {
    local type=$1
    local name=$2
    local required=${3:-true}

    log_info "Checking $type/$name..."
    if kubectl get "$type" -n "$NAMESPACE" "$name" >/dev/null 2>&1; then
        # Get additional status info
        local status
        case $type in
            "deployment")
                status=$(kubectl get deployment -n "$NAMESPACE" "$name" -o jsonpath='{.status.readyReplicas}/{.status.replicas}')
                log_success "Found $type/$name (Ready: $status)"
                ;;
            "cronjob")
                status=$(kubectl get cronjob -n "$NAMESPACE" "$name" -o jsonpath='{.spec.schedule}')
                log_success "Found $type/$name (Schedule: $status)"
                ;;
            "job")
                status=$(kubectl get job -n "$NAMESPACE" "$name" -o jsonpath='{.status.conditions[0].type}')
                log_success "Found $type/$name (Status: $status)"
                ;;
            *)
                log_success "Found $type/$name"
                ;;
        esac
        increment_success
        return 0
    else
        if [ "$required" = "true" ]; then
            log_error "Missing $type/$name"
            increment_error
        else
            log_warning "Missing $type/$name (optional)"
            increment_warning
        fi
        return 1
    fi
}

# Core DR components
log_info "Checking core DR components..."
check_component deployment failover-controller
check_component configmap failover-controller-config

# Replication components
log_info "Checking replication components..."
check_component cronjob postgres-snapshot
check_component cronjob vector-export
check_component deployment object-sync

# Chaos engineering components (optional - may not be scheduled)
log_info "Checking chaos engineering components..."
check_component cronjob chaos-random-pod-kill false
check_component cronjob chaos-network-partition false
check_component cronjob chaos-resource-exhaustion false
check_component cronjob chaos-dependency-failure false
check_component cronjob chaos-region-failover-drill false

# Validation components
log_info "Checking validation components..."
check_component cronjob restore-validation-full false
check_component cronjob restore-validation-quick false

# Compliance components
log_info "Checking compliance components..."
check_component cronjob compliance-attestation-monthly false
check_component cronjob compliance-attestation-quarterly false
check_component cronjob compliance-attestation-annual false

# -------------------------------------------------------------
# 5. Monitoring Integration Checks
# -------------------------------------------------------------
log_header "Monitoring Integration Checks"

# Check for Prometheus Operator CRDs
log_info "Checking Prometheus Operator CRDs..."
if kubectl get crd prometheusrules.monitoring.coreos.com >/dev/null 2>&1; then
    log_success "PrometheusRule CRD is installed"
    increment_success

    # Check for DR-specific PrometheusRules
    log_info "Checking DR PrometheusRules..."
    dr_rules=$(kubectl get prometheusrule --all-namespaces -o name 2>/dev/null | grep -E "(dr|disaster|backup)" | wc -l)
    if [ "$dr_rules" -gt 0 ]; then
        log_success "Found $dr_rules DR-related PrometheusRule(s)"
        increment_success
    else
        log_warning "No DR-specific PrometheusRules found"
        increment_warning
    fi
else
    log_warning "PrometheusRule CRD not installed - monitoring integration unavailable"
    increment_warning
fi

# Check for ServiceMonitor CRDs
if kubectl get crd servicemonitors.monitoring.coreos.com >/dev/null 2>&1; then
    log_success "ServiceMonitor CRD is installed"
    increment_success

    # Check for DR-specific ServiceMonitors
    log_info "Checking DR ServiceMonitors..."
    dr_monitors=$(kubectl get servicemonitor --all-namespaces -o name 2>/dev/null | grep -E "(dr|disaster|backup)" | wc -l)
    if [ "$dr_monitors" -gt 0 ]; then
        log_success "Found $dr_monitors DR-related ServiceMonitor(s)"
        increment_success
    else
        log_warning "No DR-specific ServiceMonitors found"
        increment_warning
    fi
else
    log_warning "ServiceMonitor CRD not installed"
    increment_warning
fi

# -------------------------------------------------------------
# 6. Configuration Files Check
# -------------------------------------------------------------
log_header "Configuration Files Check"

# Check for Grafana dashboard
DASHBOARD_FILE="$MONITORING_DIR/grafana-dr-dashboards.json"
log_info "Checking Grafana DR dashboard..."
if [ -f "$DASHBOARD_FILE" ]; then
    # Validate JSON syntax
    if python3 -m json.tool "$DASHBOARD_FILE" >/dev/null 2>&1; then
        log_success "Grafana DR dashboard JSON exists and is valid"
        increment_success
    else
        log_error "Grafana DR dashboard JSON exists but has syntax errors"
        increment_error
    fi
else
    log_warning "Grafana DR dashboard JSON missing: $DASHBOARD_FILE"
    increment_warning
fi

# Check for runbooks
RUNBOOKS_FILE="$DR_DIR/runbooks.md"
log_info "Checking DR runbooks..."
if [ -f "$RUNBOOKS_FILE" ]; then
    lines=$(wc -l < "$RUNBOOKS_FILE")
    log_success "DR runbooks exist ($lines lines)"
    increment_success
else
    log_error "DR runbooks missing: $RUNBOOKS_FILE"
    increment_error
fi

# -------------------------------------------------------------
# 7. Advanced Checks (Optional)
# -------------------------------------------------------------
log_header "Advanced Checks"

# Check if Prometheus is accessible
log_info "Checking Prometheus accessibility..."
if kubectl get service -n monitoring prometheus-kube-prometheus-prometheus >/dev/null 2>&1; then
    log_success "Prometheus service found in monitoring namespace"
    increment_success

    # Try to port-forward and check metrics (non-blocking)
    log_info "Testing Prometheus port-forward (5 second timeout)..."
    if timeout 5s kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 >/dev/null 2>&1 &
    then
        sleep 2
        if curl -s http://localhost:9090/api/v1/query?query=up >/dev/null 2>&1; then
            log_success "Prometheus API is accessible"
            increment_success
        else
            log_warning "Prometheus API not accessible via port-forward"
            increment_warning
        fi
        # Clean up port-forward
        pkill -f "kubectl port-forward.*prometheus" 2>/dev/null || true
    else
        log_warning "Could not establish port-forward to Prometheus"
        increment_warning
    fi
else
    log_warning "Prometheus service not found - advanced checks skipped"
    increment_warning
fi

# Check for required secrets
log_info "Checking for required secrets..."
required_secrets=("postgres-credentials" "s3-credentials" "monitoring-credentials")
for secret in "${required_secrets[@]}"; do
    if kubectl get secret -n "$NAMESPACE" "$secret" >/dev/null 2>&1; then
        log_success "Secret '$secret' exists"
        increment_success
    else
        log_warning "Secret '$secret' not found (may need to be created)"
        increment_warning
    fi
done

# -------------------------------------------------------------
# 8. Deployment Simulation (Dry Run)
# -------------------------------------------------------------
log_header "Deployment Simulation"

log_info "Running dry-run deployment of all DR components..."
temp_file=$(mktemp)
find "$DR_DIR" -name "*.yaml" -exec cat {} \; > "$temp_file"

if kubectl apply --dry-run=server -f "$temp_file" >/dev/null 2>&1; then
    log_success "Dry-run deployment successful - no conflicts detected"
    increment_success
else
    log_warning "Dry-run deployment had issues (check manually):"
    kubectl apply --dry-run=server -f "$temp_file" 2>&1 | head -10
    increment_warning
fi

rm -f "$temp_file"

# -------------------------------------------------------------
# 9. Final Results Summary
# -------------------------------------------------------------
log_header "Smoke Test Results Summary"

echo "📊 Test Results:"
echo "   ✅ Successes: $SUCCESS_COUNT"
echo "   ⚠️  Warnings:  $WARNING_COUNT"
echo "   ❌ Errors:    $ERROR_COUNT"
echo "   📈 Total:     $((SUCCESS_COUNT + WARNING_COUNT + ERROR_COUNT))"

# Generate recommendations
echo ""
echo "📋 Recommendations:"

if [ $ERROR_COUNT -gt 0 ]; then
    log_error "❌ $ERROR_COUNT critical errors detected"
    echo "   👉 Fix errors before deploying to production"
    echo "   👉 Review YAML syntax and missing components"
fi

if [ $WARNING_COUNT -gt 0 ]; then
    log_warning "⚠️ $WARNING_COUNT warnings detected"
    echo "   👉 Review warnings for optional components"
    echo "   👉 Consider creating missing secrets/namespaces"
fi

if [ $SUCCESS_COUNT -gt 10 ]; then
    log_success "🎉 Core DR infrastructure looks healthy"
    echo "   👉 Ready for deployment with warnings addressed"
fi

# Exit code based on results
if [ $ERROR_COUNT -gt 0 ]; then
    echo ""
    echo "🚫 Smoke test FAILED due to critical errors"
    exit 1
elif [ $WARNING_COUNT -gt 5 ]; then
    echo ""
    echo "⚠️ Smoke test PASSED with significant warnings"
    exit 2
else
    echo ""
    echo "✅ Smoke test PASSED - DR infrastructure ready"
    exit 0
fi
