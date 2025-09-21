# PAKE System - Agent Sandbox Container
# Security-hardened container for isolated CLI provider execution
# Resource-constrained environment with comprehensive monitoring

FROM node:18-alpine AS base

# Security Labels
LABEL maintainer="PAKE System Security Team"
LABEL security.scan="required"
LABEL security.isolation="maximum"
LABEL version="1.0.0"

# ============================================================================
# STAGE 1: Security Hardening Base
# ============================================================================

# Install security tools and minimal dependencies
RUN apk add --no-cache \
    dumb-init \
    su-exec \
    shadow \
    curl \
    jq \
    bash \
    && rm -rf /var/cache/apk/*

# Create non-root user with minimal privileges
RUN addgroup -g 1001 -S pake \
    && adduser -u 1001 -S pake -G pake -h /home/pake -s /bin/bash

# Create secure directory structure
RUN mkdir -p /app/sandbox \
    && mkdir -p /app/logs \
    && mkdir -p /app/temp \
    && mkdir -p /app/policies \
    && chown -R pake:pake /app

# ============================================================================
# STAGE 2: Runtime Environment Setup
# ============================================================================

FROM base AS runtime

# Set security-focused environment variables
ENV NODE_ENV=sandbox \
    NODE_OPTIONS="--max-old-space-size=256 --max-semi-space-size=32" \
    UV_THREADPOOL_SIZE=2 \
    FORCE_COLOR=0 \
    NO_UPDATE_NOTIFIER=1 \
    DISABLE_TELEMETRY=1

# Resource limits via environment (enforced by container runtime)
ENV MEMORY_LIMIT=512m \
    CPU_LIMIT=0.5 \
    DISK_LIMIT=1g \
    PROCESS_LIMIT=32 \
    FILE_DESCRIPTOR_LIMIT=1024 \
    NETWORK_TIMEOUT=30 \
    EXECUTION_TIMEOUT=60

# Security policies
ENV SANDBOX_MODE=strict \
    ALLOW_NETWORK=false \
    ALLOW_FILE_WRITE=false \
    ALLOW_SYSTEM_CALLS=false \
    LOG_ALL_COMMANDS=true \
    REDACT_SECRETS=true

# Copy sandbox enforcement scripts
COPY --chown=pake:pake ops/docker/scripts/sandbox-init.sh /app/sandbox-init.sh
COPY --chown=pake:pake ops/docker/scripts/resource-monitor.sh /app/resource-monitor.sh
COPY --chown=pake:pake ops/docker/scripts/security-audit.sh /app/security-audit.sh

# Make scripts executable
RUN chmod +x /app/sandbox-init.sh \
    && chmod +x /app/resource-monitor.sh \
    && chmod +x /app/security-audit.sh

# ============================================================================
# STAGE 3: Security Hardening
# ============================================================================

# Remove unnecessary packages and clean up
RUN apk del --purge shadow \
    && rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

# Set up seccomp profile directory
RUN mkdir -p /app/security

# Copy security profiles
COPY --chown=pake:pake ops/docker/security/seccomp-profile.json /app/security/
COPY --chown=pake:pake ops/docker/security/apparmor-profile /app/security/

# Create read-only filesystem marker
RUN touch /app/.readonly-fs-marker

# ============================================================================
# STAGE 4: Application Layer
# ============================================================================

FROM runtime AS application

# Install only essential npm packages with exact versions
COPY package.json package-lock.json /app/
RUN cd /app && npm ci --only=production --no-audit --no-fund \
    && npm cache clean --force \
    && rm -rf ~/.npm /tmp/*

# Copy application source with proper ownership
COPY --chown=pake:pake services/agent-runtime/src /app/src/
COPY --chown=pake:pake services/policy /app/policy/
COPY --chown=pake:pake ops/docker/sandbox-entrypoint.js /app/

# ============================================================================
# STAGE 5: Final Hardening
# ============================================================================

FROM application AS final

# Switch to non-root user
USER pake

# Set working directory
WORKDIR /app

# Health check with security validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/app/security-audit.sh", "health"]

# Resource constraints (enforced at container level)
# Memory: 512MB, CPU: 0.5 cores, PIDs: 32, Files: 1024

# Security labels for runtime
LABEL security.no-new-privileges="true"
LABEL security.read-only-root-filesystem="true"
LABEL security.user="pake:pake"

# Expose minimal required port
EXPOSE 8080

# Volume mounts for logs and temporary data (read-only by default)
VOLUME ["/app/logs", "/app/temp"]

# Entry point with dumb-init for proper signal handling
ENTRYPOINT ["/usr/bin/dumb-init", "--", "node", "/app/sandbox-entrypoint.js"]

# ============================================================================
# RUNTIME SECURITY CONFIGURATION
# ============================================================================

# Instructions for container runtime:
#
# docker run \
#   --security-opt=no-new-privileges:true \
#   --security-opt=seccomp:/app/security/seccomp-profile.json \
#   --security-opt=apparmor:pake-agent-sandbox \
#   --read-only \
#   --tmpfs /app/temp:noexec,nosuid,size=100m \
#   --tmpfs /app/logs:noexec,nosuid,size=50m \
#   --memory=512m \
#   --memory-swap=512m \
#   --cpus=0.5 \
#   --pids-limit=32 \
#   --ulimit=nofile=1024:1024 \
#   --ulimit=nproc=32:32 \
#   --network=none \
#   --cap-drop=ALL \
#   --user=pake:pake \
#   --init \
#   pake-agent-sandbox:latest

# Additional Kubernetes security context:
#
# securityContext:
#   runAsUser: 1001
#   runAsGroup: 1001
#   runAsNonRoot: true
#   readOnlyRootFilesystem: true
#   allowPrivilegeEscalation: false
#   capabilities:
#     drop: ["ALL"]
#   seccompProfile:
#     type: Localhost
#     localhostProfile: pake-seccomp.json