#!/bin/bash

# PAKE System - Security Audit Script
# Continuous security monitoring and compliance verification

set -euo pipefail

AUDIT_LOG="/app/logs/security-audit.log"
VIOLATIONS_LOG="/app/logs/security-violations.log"

log() {
    echo "[$(date -Iseconds)] [SECURITY-AUDIT] $*" | tee -a "$AUDIT_LOG"
}

violation() {
    echo "[$(date -Iseconds)] [SECURITY-AUDIT] VIOLATION: $*" | tee -a "$AUDIT_LOG" | tee -a "$VIOLATIONS_LOG" >&2
}

# Health check for container orchestration
health_check() {
    local status="healthy"
    local errors=0
    
    # Check critical processes
    if ! pgrep -f "node.*sandbox-entrypoint" >/dev/null 2>&1; then
        status="unhealthy"
        ((errors++))
    fi
    
    # Check filesystem integrity
    if [[ ! -f /app/.readonly-fs-marker ]]; then
        status="unhealthy"
        ((errors++))
    fi
    
    # Check resource monitor
    if [[ -f /app/temp/.monitor.pid ]]; then
        local monitor_pid=$(cat /app/temp/.monitor.pid)
        if ! kill -0 "$monitor_pid" 2>/dev/null; then
            status="unhealthy"
            ((errors++))
        fi
    fi
    
    echo "{\"status\":\"$status\",\"timestamp\":\"$(date -Iseconds)\",\"errors\":$errors}"
    
    if [[ "$status" == "healthy" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Audit user privileges
audit_user_privileges() {
    log "Auditing user privileges..."
    
    # Check effective user ID
    if [[ $(id -u) -eq 0 ]]; then
        violation "Process running as root (UID 0)"
        return 1
    fi
    
    # Check for setuid/setgid binaries
    local setuid_files=$(find /app -perm /4000 2>/dev/null || true)
    if [[ -n "$setuid_files" ]]; then
        violation "Setuid binaries found: $setuid_files"
        return 1
    fi
    
    log "User privilege audit passed"
    return 0
}

# Audit filesystem permissions
audit_filesystem() {
    log "Auditing filesystem permissions..."
    
    # Check for world-writable files
    local world_writable=$(find /app -type f -perm -002 2>/dev/null | head -5)
    if [[ -n "$world_writable" ]]; then
        violation "World-writable files found: $world_writable"
    fi
    
    # Check for suspicious file modifications
    local recent_mods=$(find /app -type f -mmin -5 -not -path "*/logs/*" -not -path "*/temp/*" 2>/dev/null)
    if [[ -n "$recent_mods" ]]; then
        violation "Unexpected file modifications: $recent_mods"
    fi
    
    # Verify critical security files
    local security_files=("/app/security/seccomp-profile.json" "/app/.readonly-fs-marker")
    for file in "${security_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            violation "Critical security file missing: $file"
        fi
    done
    
    log "Filesystem audit completed"
}

# Audit network connections
audit_network() {
    log "Auditing network connections..."
    
    # Check for unexpected network connections (when network is disabled)
    if [[ "${ALLOW_NETWORK:-false}" == "false" ]]; then
        local connections=$(netstat -tn 2>/dev/null | grep ESTABLISHED || true)
        if [[ -n "$connections" ]]; then
            violation "Unexpected network connections detected: $connections"
        fi
    fi
    
    # Check for listening ports (except allowed ones)
    local listening=$(netstat -tln 2>/dev/null | grep LISTEN | grep -v ":8080" || true)
    if [[ -n "$listening" ]]; then
        violation "Unexpected listening ports: $listening"
    fi
    
    log "Network audit completed"
}

# Audit process activities
audit_processes() {
    log "Auditing process activities..."
    
    # Check for suspicious processes
    local suspicious_procs=$(ps -eo pid,cmd | grep -E "(bash|sh|curl|wget|nc|telnet)" | grep -v "resource-monitor\|security-audit" || true)
    if [[ -n "$suspicious_procs" ]]; then
        violation "Suspicious processes detected: $suspicious_procs"
    fi
    
    # Check process count against limits
    local proc_count=$(pgrep -cu "$(whoami)")
    local proc_limit=${PROCESS_LIMIT:-32}
    if [[ $proc_count -gt $proc_limit ]]; then
        violation "Process count exceeded limit: $proc_count > $proc_limit"
    fi
    
    log "Process audit completed"
}

# Audit environment variables for secrets
audit_environment() {
    log "Auditing environment variables..."
    
    # Check for potential secrets in environment
    local env_vars=$(env | grep -E "(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)" | cut -d= -f1 || true)
    if [[ -n "$env_vars" ]]; then
        log "WARNING: Potential secrets in environment: $env_vars"
    fi
    
    # Verify security environment variables are set
    local required_vars=("SANDBOX_MODE" "REDACT_SECRETS")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            violation "Required security environment variable missing: $var"
        fi
    done
    
    log "Environment audit completed"
}

# Comprehensive security scan
full_audit() {
    log "Starting comprehensive security audit..."
    
    local audit_start=$(date +%s)
    local violations=0
    
    # Run all audit checks
    audit_user_privileges || ((violations++))
    audit_filesystem || ((violations++))
    audit_network || ((violations++))
    audit_processes || ((violations++))
    audit_environment || ((violations++))
    
    local audit_duration=$(($(date +%s) - audit_start))
    
    # Generate audit summary
    cat >> "$AUDIT_LOG" << EOF

=== Security Audit Summary ===
Timestamp: $(date -Iseconds)
Duration: ${audit_duration}s
Violations: $violations
Status: $(if [[ $violations -eq 0 ]]; then echo "SECURE"; else echo "VIOLATIONS_DETECTED"; fi)
User: $(whoami) ($(id -u):$(id -g))
Working Directory: $(pwd)
Process Count: $(pgrep -cu "$(whoami)")
Memory Usage: $(get_memory_usage 2>/dev/null || echo "unknown")MB

EOF
    
    if [[ $violations -gt 0 ]]; then
        violation "Security audit completed with $violations violations"
        return 1
    else
        log "Security audit completed successfully - system secure"
        return 0
    fi
}

# Get memory usage helper
get_memory_usage() {
    if [[ -f /sys/fs/cgroup/memory/memory.usage_in_bytes ]]; then
        local usage_bytes=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
        echo $((usage_bytes / 1024 / 1024))
    else
        echo "0"
    fi
}

# Generate security report in JSON format
generate_report() {
    local violations_count=0
    if [[ -f "$VIOLATIONS_LOG" ]]; then
        violations_count=$(wc -l < "$VIOLATIONS_LOG")
    fi
    
    cat << EOF
{
  "timestamp": "$(date -Iseconds)",
  "audit_version": "1.0.0",
  "container_id": "${HOSTNAME}",
  "security_status": "$(if [[ $violations_count -eq 0 ]]; then echo "secure"; else echo "violations_detected"; fi)",
  "total_violations": $violations_count,
  "system_info": {
    "user": "$(whoami)",
    "uid": $(id -u),
    "gid": $(id -g),
    "process_count": $(pgrep -cu "$(whoami)"),
    "memory_usage_mb": $(get_memory_usage),
    "uptime_seconds": $(awk '{print int($1)}' /proc/uptime)
  },
  "security_features": {
    "sandbox_mode": "${SANDBOX_MODE:-unknown}",
    "network_isolation": $(if [[ "${ALLOW_NETWORK:-false}" == "false" ]]; then echo "true"; else echo "false"; fi),
    "filesystem_readonly": $(if [[ -f /app/.readonly-fs-marker ]]; then echo "true"; else echo "false"; fi),
    "secret_redaction": "${REDACT_SECRETS:-unknown}"
  }
}
EOF
}

# Handle different audit operations
case "${1:-health}" in
    "health")
        health_check
        ;;
    "audit")
        full_audit
        ;;
    "report")
        generate_report
        ;;
    "continuous")
        log "Starting continuous security monitoring..."
        while true; do
            full_audit
            sleep 60  # Audit every minute
        done
        ;;
    *)
        echo "Usage: $0 [health|audit|report|continuous]"
        exit 1
        ;;
esac