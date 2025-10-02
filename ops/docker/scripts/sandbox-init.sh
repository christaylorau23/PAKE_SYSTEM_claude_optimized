#!/bin/bash

# PAKE System - Sandbox Initialization Script
# Enforces security policies and resource limits before application startup

set -euo pipefail

# Security logging
exec 1> >(tee -a /app/logs/sandbox-init.log)
exec 2>&1

log() {
    echo "[$(date -Iseconds)] [SANDBOX-INIT] $*"
}

error() {
    echo "[$(date -Iseconds)] [SANDBOX-INIT] ERROR: $*" >&2
}

log "Starting PAKE Agent Sandbox initialization"

# ============================================================================
# SECURITY VALIDATIONS
# ============================================================================

log "Performing security validations..."

# Verify we're running as non-root
if [[ $EUID -eq 0 ]]; then
    error "Security violation: Running as root is forbidden"
    exit 1
fi

# Verify user identity
CURRENT_USER=$(whoami)
if [[ "$CURRENT_USER" != "pake" ]]; then
    error "Security violation: Must run as 'pake' user, currently: $CURRENT_USER"
    exit 1
fi

# Verify read-only filesystem marker
if [[ ! -f /app/.readonly-fs-marker ]]; then
    error "Security violation: Read-only filesystem not properly configured"
    exit 1
fi

log "User identity verified: $CURRENT_USER"

# ============================================================================
# RESOURCE LIMIT ENFORCEMENT
# ============================================================================

log "Enforcing resource limits..."

# Set process limits
ulimit -u ${PROCESS_LIMIT:-32}              # Max processes
ulimit -n ${FILE_DESCRIPTOR_LIMIT:-1024}    # Max file descriptors
ulimit -f 1048576                           # Max file size (1GB in 512-byte blocks)
ulimit -t ${EXECUTION_TIMEOUT:-60}          # Max CPU time per process

# Memory pressure monitoring
if [[ -f /sys/fs/cgroup/memory/memory.limit_in_bytes ]]; then
    MEMORY_LIMIT_BYTES=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
    log "Container memory limit: $(( MEMORY_LIMIT_BYTES / 1024 / 1024 ))MB"
else
    log "WARNING: Memory cgroup limit not detected"
fi

log "Resource limits enforced"

# ============================================================================
# SECURITY POLICY SETUP
# ============================================================================

log "Setting up security policies..."

# Create secure temporary directories
mkdir -p /app/temp/sandbox-$$
mkdir -p /app/logs/session-$$
export TMPDIR="/app/temp/sandbox-$$"
export TEMP="$TMPDIR"

# Set restrictive umask
umask 077

# Clear environment of potentially dangerous variables
unset LD_PRELOAD
unset LD_LIBRARY_PATH
unset PATH_SEPARATOR
unset SHELL
unset HOME

# Set minimal secure environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export SHELL="/bin/false"
export HOME="/app"

log "Security policies configured"

# ============================================================================
# NETWORK ISOLATION VERIFICATION
# ============================================================================

log "Verifying network isolation..."

# Check if network isolation is properly enforced
if [[ "${ALLOW_NETWORK:-false}" == "false" ]]; then
    # Test network connectivity (should fail in isolated mode)
    if timeout 2 ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        error "Security violation: Network access detected when disabled"
        exit 1
    fi
    log "Network isolation verified"
else
    log "Network access permitted by policy"
fi

# ============================================================================
# FILESYSTEM SECURITY
# ============================================================================

log "Configuring filesystem security..."

# Verify critical directories are writable for application
WRITABLE_DIRS=("/app/temp" "/app/logs")
for dir in "${WRITABLE_DIRS[@]}"; do
    if [[ ! -w "$dir" ]]; then
        error "Security violation: Required directory not writable: $dir"
        exit 1
    fi
done

# Verify system directories are read-only
READONLY_DIRS=("/etc" "/usr" "/bin" "/sbin")
for dir in "${READONLY_DIRS[@]}"; do
    if [[ -w "$dir" ]]; then
        error "Security violation: System directory is writable: $dir"
        exit 1
    fi
done

log "Filesystem security verified"

# ============================================================================
# MONITORING SETUP
# ============================================================================

log "Starting resource monitoring..."

# Start background resource monitor
/app/resource-monitor.sh &
MONITOR_PID=$!
echo $MONITOR_PID > /app/temp/.monitor.pid

# Trap signals for cleanup
cleanup() {
    log "Performing cleanup..."
    if [[ -f /app/temp/.monitor.pid ]]; then
        MONITOR_PID=$(cat /app/temp/.monitor.pid)
        kill $MONITOR_PID 2>/dev/null || true
    fi

    # Clean temporary files
    rm -rf /app/temp/sandbox-$$ 2>/dev/null || true

    log "Cleanup completed"
}

trap cleanup EXIT INT TERM

# ============================================================================
# SECURITY AUDIT LOG
# ============================================================================

log "Generating security audit log..."

cat > /app/logs/security-audit.json << EOF
{
  "timestamp": "$(date -Iseconds)",
  "sandbox_version": "1.0.0",
  "security_checks": {
    "user_identity": "passed",
    "filesystem_readonly": "passed",
    "resource_limits": "passed",
    "network_isolation": "$(if [[ "${ALLOW_NETWORK:-false}" == "false" ]]; then echo "passed"; else echo "bypassed"; fi)",
    "process_limits": "passed"
  },
  "environment": {
    "user": "$(whoami)",
    "uid": "$(id -u)",
    "gid": "$(id -g)",
    "working_directory": "$(pwd)",
    "umask": "$(umask)",
    "ulimit_processes": "$(ulimit -u)",
    "ulimit_files": "$(ulimit -n)"
  },
  "policies": {
    "sandbox_mode": "${SANDBOX_MODE:-strict}",
    "allow_network": "${ALLOW_NETWORK:-false}",
    "allow_file_write": "${ALLOW_FILE_WRITE:-false}",
    "log_all_commands": "${LOG_ALL_COMMANDS:-true}",
    "redact_secrets": "${REDACT_SECRETS:-true}"
  }
}
EOF

log "Security audit log generated"

# ============================================================================
# STARTUP VALIDATION
# ============================================================================

log "Performing final startup validation..."

# Verify Node.js environment
if ! node --version >/dev/null 2>&1; then
    error "Node.js runtime not available"
    exit 1
fi

# Check available memory
AVAILABLE_MEMORY=$(free -m | awk '/^Mem:/ {print $7}')
if [[ $AVAILABLE_MEMORY -lt 50 ]]; then
    error "Insufficient available memory: ${AVAILABLE_MEMORY}MB"
    exit 1
fi

log "Startup validation completed"
log "PAKE Agent Sandbox initialization successful"
log "Environment secured and ready for agent execution"

exit 0