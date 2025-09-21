#!/bin/bash

# PAKE System - Resource Monitor
# Continuous monitoring of sandbox resource usage with automatic enforcement

set -euo pipefail

# Monitoring configuration
MONITOR_INTERVAL=${MONITOR_INTERVAL:-5}     # Check every 5 seconds
LOG_FILE="/app/logs/resource-monitor.log"
METRICS_FILE="/app/logs/resource-metrics.jsonl"

# Resource thresholds (configurable via environment)
MEMORY_THRESHOLD_MB=${MEMORY_THRESHOLD_MB:-400}    # 400MB of 512MB limit
CPU_THRESHOLD_PERCENT=${CPU_THRESHOLD_PERCENT:-80} # 80% CPU usage
DISK_THRESHOLD_MB=${DISK_THRESHOLD_MB:-800}        # 800MB of 1GB limit
PROCESS_THRESHOLD=${PROCESS_THRESHOLD:-25}         # 25 of 32 process limit

# Alert counters
MEMORY_VIOLATIONS=0
CPU_VIOLATIONS=0
DISK_VIOLATIONS=0
PROCESS_VIOLATIONS=0

log() {
    echo "[$(date -Iseconds)] [RESOURCE-MONITOR] $*" | tee -a "$LOG_FILE"
}

alert() {
    echo "[$(date -Iseconds)] [RESOURCE-MONITOR] ALERT: $*" | tee -a "$LOG_FILE" >&2
}

fatal() {
    echo "[$(date -Iseconds)] [RESOURCE-MONITOR] FATAL: $*" | tee -a "$LOG_FILE" >&2
    exit 1
}

# Get memory usage in MB
get_memory_usage() {
    if [[ -f /sys/fs/cgroup/memory/memory.usage_in_bytes ]]; then
        local usage_bytes=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
        echo $((usage_bytes / 1024 / 1024))
    else
        # Fallback to /proc/meminfo
        awk '/^MemAvailable:/ {print int(($2/1024))}' /proc/meminfo 2>/dev/null || echo "0"
    fi
}

# Get CPU usage percentage
get_cpu_usage() {
    # Use top to get current process CPU usage
    top -bn1 | grep "CPU:" | awk '{print $2}' | sed 's/%us,//' | sed 's/\..*//' 2>/dev/null || echo "0"
}

# Get disk usage in MB for /app
get_disk_usage() {
    df /app 2>/dev/null | awk 'NR==2 {print int($3/1024)}' || echo "0"
}

# Get process count for current user
get_process_count() {
    pgrep -cu "$(whoami)" 2>/dev/null || echo "0"
}

# Emit resource metrics in JSON Lines format
emit_metrics() {
    local memory_mb=$1
    local cpu_percent=$2
    local disk_mb=$3
    local process_count=$4
    
    cat >> "$METRICS_FILE" << EOF
{"timestamp":"$(date -Iseconds)","memory_mb":$memory_mb,"cpu_percent":$cpu_percent,"disk_mb":$disk_mb,"process_count":$process_count,"memory_threshold":$MEMORY_THRESHOLD_MB,"cpu_threshold":$CPU_THRESHOLD_PERCENT,"disk_threshold":$DISK_THRESHOLD_MB,"process_threshold":$PROCESS_THRESHOLD}
EOF
}

# Check for resource violations and take action
check_violations() {
    local memory_mb=$1
    local cpu_percent=$2
    local disk_mb=$3
    local process_count=$4
    
    local violations=0
    
    # Memory violation check
    if [[ $memory_mb -gt $MEMORY_THRESHOLD_MB ]]; then
        ((MEMORY_VIOLATIONS++))
        alert "Memory usage exceeded: ${memory_mb}MB > ${MEMORY_THRESHOLD_MB}MB (violation #$MEMORY_VIOLATIONS)"
        ((violations++))
        
        # Kill memory-intensive processes after 3 violations
        if [[ $MEMORY_VIOLATIONS -ge 3 ]]; then
            alert "Memory violation limit reached. Terminating high-memory processes"
            # Kill processes consuming most memory (except self)
            ps -eo pid,pmem,cmd --sort=-pmem | head -5 | grep -v resource-monitor | awk '{print $1}' | xargs -r kill -TERM 2>/dev/null || true
        fi
    else
        MEMORY_VIOLATIONS=0
    fi
    
    # CPU violation check
    if [[ $cpu_percent -gt $CPU_THRESHOLD_PERCENT ]]; then
        ((CPU_VIOLATIONS++))
        alert "CPU usage exceeded: ${cpu_percent}% > ${CPU_THRESHOLD_PERCENT}% (violation #$CPU_VIOLATIONS)"
        ((violations++))
        
        # Throttle CPU after violations
        if [[ $CPU_VIOLATIONS -ge 5 ]]; then
            alert "CPU violation limit reached. Applying CPU throttling"
            # Send SIGSTOP to high CPU processes briefly
            ps -eo pid,pcpu,cmd --sort=-pcpu | head -3 | grep -v resource-monitor | awk '{print $1}' | while read pid; do
                kill -STOP $pid 2>/dev/null && sleep 1 && kill -CONT $pid 2>/dev/null || true
            done
        fi
    else
        CPU_VIOLATIONS=0
    fi
    
    # Disk violation check
    if [[ $disk_mb -gt $DISK_THRESHOLD_MB ]]; then
        ((DISK_VIOLATIONS++))
        alert "Disk usage exceeded: ${disk_mb}MB > ${DISK_THRESHOLD_MB}MB (violation #$DISK_VIOLATIONS)"
        ((violations++))
        
        # Clean temporary files after violations
        if [[ $DISK_VIOLATIONS -ge 2 ]]; then
            alert "Disk violation limit reached. Cleaning temporary files"
            find /app/temp -type f -mmin +5 -delete 2>/dev/null || true
            find /app/logs -name "*.log" -mtime +1 -delete 2>/dev/null || true
        fi
    else
        DISK_VIOLATIONS=0
    fi
    
    # Process count violation check
    if [[ $process_count -gt $PROCESS_THRESHOLD ]]; then
        ((PROCESS_VIOLATIONS++))
        alert "Process count exceeded: $process_count > $PROCESS_THRESHOLD (violation #$PROCESS_VIOLATIONS)"
        ((violations++))
        
        # Kill excess processes after violations
        if [[ $PROCESS_VIOLATIONS -ge 2 ]]; then
            alert "Process violation limit reached. Terminating excess processes"
            # Kill oldest processes (except essential ones)
            ps -eo pid,etime,cmd --sort=etime | tail -n +$((PROCESS_THRESHOLD + 1)) | \
                grep -v -E "(resource-monitor|sandbox-init|node)" | \
                awk '{print $1}' | xargs -r kill -TERM 2>/dev/null || true
        fi
    else
        PROCESS_VIOLATIONS=0
    fi
    
    # Fatal violation check - shutdown if all systems are over limits
    if [[ $violations -ge 3 ]]; then
        fatal "Multiple critical resource violations detected. Initiating sandbox shutdown"
    fi
}

# Main monitoring loop
main() {
    log "Resource monitor starting (interval: ${MONITOR_INTERVAL}s)"
    log "Thresholds: Memory=${MEMORY_THRESHOLD_MB}MB, CPU=${CPU_THRESHOLD_PERCENT}%, Disk=${DISK_THRESHOLD_MB}MB, Processes=${PROCESS_THRESHOLD}"
    
    # Initialize metrics file
    echo '{"type":"resource_monitor_start","timestamp":"'"$(date -Iseconds)"'"}' > "$METRICS_FILE"
    
    # Monitoring loop
    while true; do
        # Collect current metrics
        local memory_mb=$(get_memory_usage)
        local cpu_percent=$(get_cpu_usage)
        local disk_mb=$(get_disk_usage)  
        local process_count=$(get_process_count)
        
        # Emit metrics for observability
        emit_metrics "$memory_mb" "$cpu_percent" "$disk_mb" "$process_count"
        
        # Check for violations and enforce limits
        check_violations "$memory_mb" "$cpu_percent" "$disk_mb" "$process_count"
        
        # Log periodic status (every 12 cycles = 1 minute)
        if (( $(date +%s) % 60 < MONITOR_INTERVAL )); then
            log "Status: Memory=${memory_mb}MB, CPU=${cpu_percent}%, Disk=${disk_mb}MB, Processes=${process_count}"
        fi
        
        sleep "$MONITOR_INTERVAL"
    done
}

# Signal handlers for graceful shutdown
cleanup() {
    log "Resource monitor shutting down"
    echo '{"type":"resource_monitor_stop","timestamp":"'"$(date -Iseconds)"'"}' >> "$METRICS_FILE"
    exit 0
}

trap cleanup EXIT INT TERM

# Handle specific monitoring commands
case "${1:-monitor}" in
    "monitor")
        main
        ;;
    "status")
        echo "Memory: $(get_memory_usage)MB, CPU: $(get_cpu_usage)%, Disk: $(get_disk_usage)MB, Processes: $(get_process_count)"
        ;;
    "metrics")
        if [[ -f "$METRICS_FILE" ]]; then
            tail -n 10 "$METRICS_FILE"
        else
            echo "No metrics available"
        fi
        ;;
    *)
        echo "Usage: $0 [monitor|status|metrics]"
        exit 1
        ;;
esac