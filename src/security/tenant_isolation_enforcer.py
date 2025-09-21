#!/usr/bin/env python3
"""PAKE System - Phase 16 Tenant Isolation Security Enforcer
Enterprise-grade security enforcement for multi-tenant isolation.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.middleware.tenant_context import (
    get_current_request_context,
    get_current_tenant_id,
    get_current_user_id,
)

logger = logging.getLogger(__name__)


@dataclass
class SecurityViolation:
    """Security violation record"""

    violation_id: str
    violation_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    tenant_id: str | None
    user_id: str | None
    details: dict[str, Any]
    timestamp: datetime
    ip_address: str | None
    user_agent: str | None
    blocked: bool


@dataclass
class SecurityPolicy:
    """Security policy configuration"""

    name: str
    enabled: bool
    severity: str
    action: str  # block, log, alert
    parameters: dict[str, Any]


class SecurityMetrics:
    """Security metrics tracking"""

    def __init__(self):
        self.violations_by_type: dict[str, int] = {}
        self.violations_by_tenant: dict[str, int] = {}
        self.violations_by_severity: dict[str, int] = {}
        self.blocked_requests: int = 0
        self.total_requests: int = 0
        self.last_reset: datetime = datetime.utcnow()

    def record_violation(self, violation: SecurityViolation) -> None:
        """Record security violation in metrics"""
        self.violations_by_type[violation.violation_type] = (
            self.violations_by_type.get(violation.violation_type, 0) + 1
        )

        if violation.tenant_id:
            self.violations_by_tenant[violation.tenant_id] = (
                self.violations_by_tenant.get(violation.tenant_id, 0) + 1
            )

        self.violations_by_severity[violation.severity] = (
            self.violations_by_severity.get(violation.severity, 0) + 1
        )

        if violation.blocked:
            self.blocked_requests += 1

    def record_request(self) -> None:
        """Record total request"""
        self.total_requests += 1

    def get_security_score(self) -> float:
        """Calculate security score (0-100)"""
        if self.total_requests == 0:
            return 100.0

        # Calculate score based on violation severity
        critical_weight = self.violations_by_severity.get("CRITICAL", 0) * 10
        high_weight = self.violations_by_severity.get("HIGH", 0) * 5
        medium_weight = self.violations_by_severity.get("MEDIUM", 0) * 2
        low_weight = self.violations_by_severity.get("LOW", 0) * 1

        total_weighted_violations = (
            critical_weight + high_weight + medium_weight + low_weight
        )

        # Score decreases with violations
        score = max(0, 100 - (total_weighted_violations / self.total_requests * 100))
        return round(score, 2)

    def reset_metrics(self) -> None:
        """Reset metrics"""
        self.violations_by_type.clear()
        self.violations_by_tenant.clear()
        self.violations_by_severity.clear()
        self.blocked_requests = 0
        self.total_requests = 0
        self.last_reset = datetime.utcnow()


class TenantIsolationEnforcer:
    """Enterprise tenant isolation security enforcer.

    Features:
    - Real-time security monitoring
    - Automatic threat detection
    - Tenant boundary enforcement
    - Data leakage prevention
    - Anomaly detection
    - Security policy enforcement
    - Audit trail maintenance
    - Automated incident response
    """

    def __init__(self):
        self.security_policies: dict[str, SecurityPolicy] = {}
        self.security_metrics = SecurityMetrics()
        self.violation_log: list[SecurityViolation] = []
        self.blocked_ips: set[str] = set()
        self.suspicious_patterns: dict[str, list[str]] = {}

        # Rate limiting
        self.rate_limits: dict[str, dict[str, Any]] = {}

        # Initialize default policies
        self._initialize_security_policies()

        logger.info("Tenant Isolation Security Enforcer initialized")

    def _initialize_security_policies(self) -> None:
        """Initialize default security policies"""
        # Cross-tenant access prevention
        self.security_policies["cross_tenant_access"] = SecurityPolicy(
            name="Cross-Tenant Access Prevention",
            enabled=True,
            severity="CRITICAL",
            action="block",
            parameters={
                "check_tenant_boundaries": True,
                "block_cross_tenant_queries": True,
                "alert_on_attempts": True,
            },
        )

        # Data leakage prevention
        self.security_policies["data_leakage_prevention"] = SecurityPolicy(
            name="Data Leakage Prevention",
            enabled=True,
            severity="HIGH",
            action="block",
            parameters={
                "scan_response_data": True,
                "check_tenant_ids_in_response": True,
                "max_allowed_records": 1000,
            },
        )

        # SQL injection protection
        self.security_policies["sql_injection_protection"] = SecurityPolicy(
            name="SQL Injection Protection",
            enabled=True,
            severity="HIGH",
            action="block",
            parameters={
                "scan_input_parameters": True,
                "block_sql_keywords": True,
                "check_query_patterns": True,
            },
        )

        # Authentication anomaly detection
        self.security_policies["auth_anomaly_detection"] = SecurityPolicy(
            name="Authentication Anomaly Detection",
            enabled=True,
            severity="MEDIUM",
            action="alert",
            parameters={
                "failed_attempts_threshold": 5,
                "unusual_location_detection": True,
                "time_based_anomalies": True,
            },
        )

        # Rate limiting enforcement
        self.security_policies["rate_limiting"] = SecurityPolicy(
            name="Rate Limiting Enforcement",
            enabled=True,
            severity="MEDIUM",
            action="block",
            parameters={
                "requests_per_minute": 100,
                "burst_threshold": 20,
                "block_duration_minutes": 15,
            },
        )

    async def validate_tenant_access(
        self,
        requested_tenant_id: str,
        operation: str,
        resource: str,
    ) -> dict[str, Any]:
        """Validate tenant access permissions.

        This is the core security function that ensures tenant isolation.
        """
        try:
            self.security_metrics.record_request()

            current_tenant = get_current_tenant_id()
            current_user = get_current_user_id()
            request_context = get_current_request_context()

            # Check 1: Tenant context exists
            if not current_tenant:
                violation = await self._create_security_violation(
                    violation_type="missing_tenant_context",
                    severity="CRITICAL",
                    details={
                        "operation": operation,
                        "resource": resource,
                        "requested_tenant": requested_tenant_id,
                    },
                )
                return await self._handle_security_violation(violation)

            # Check 2: Tenant boundary enforcement
            if requested_tenant_id != current_tenant:
                violation = await self._create_security_violation(
                    violation_type="cross_tenant_access_attempt",
                    severity="CRITICAL",
                    details={
                        "current_tenant": current_tenant,
                        "requested_tenant": requested_tenant_id,
                        "operation": operation,
                        "resource": resource,
                        "user_id": current_user,
                    },
                )
                return await self._handle_security_violation(violation)

            # Check 3: Rate limiting
            rate_limit_result = await self._check_rate_limit(
                current_tenant,
                current_user,
            )
            if not rate_limit_result["allowed"]:
                violation = await self._create_security_violation(
                    violation_type="rate_limit_exceeded",
                    severity="MEDIUM",
                    details={
                        "tenant_id": current_tenant,
                        "user_id": current_user,
                        "operation": operation,
                        "rate_limit_info": rate_limit_result,
                    },
                )
                return await self._handle_security_violation(violation)

            # Check 4: Suspicious pattern detection
            if await self._detect_suspicious_patterns(operation, resource):
                violation = await self._create_security_violation(
                    violation_type="suspicious_pattern_detected",
                    severity="HIGH",
                    details={
                        "tenant_id": current_tenant,
                        "operation": operation,
                        "resource": resource,
                        "patterns": "multiple_rapid_requests",
                    },
                )
                return await self._handle_security_violation(violation)

            # All checks passed
            return {
                "allowed": True,
                "tenant_id": current_tenant,
                "message": "Access granted",
            }

        except Exception as e:
            logger.error(f"Security validation error: {e}")
            violation = await self._create_security_violation(
                violation_type="security_validation_error",
                severity="HIGH",
                details={"error": str(e), "operation": operation, "resource": resource},
            )
            return await self._handle_security_violation(violation)

    async def scan_response_data(self, data: Any, tenant_id: str) -> dict[str, Any]:
        """Scan response data for potential leakage.

        Ensures response data doesn't contain information from other tenants.
        """
        try:
            if not self.security_policies["data_leakage_prevention"].enabled:
                return {"clean": True, "message": "Data leakage scanning disabled"}

            # Convert data to string for scanning
            data_str = (
                json.dumps(data, default=str) if not isinstance(data, str) else data
            )

            # Check 1: Look for other tenant IDs in response
            other_tenant_ids = await self._extract_tenant_ids_from_data(data_str)
            if other_tenant_ids and len(other_tenant_ids) > 1:
                # Multiple tenant IDs found - potential leakage
                violation = await self._create_security_violation(
                    violation_type="data_leakage_detected",
                    severity="CRITICAL",
                    details={
                        "expected_tenant": tenant_id,
                        "found_tenant_ids": list(other_tenant_ids),
                        "data_sample": (
                            data_str[:500] + "..." if len(data_str) > 500 else data_str
                        ),
                    },
                )
                return await self._handle_security_violation(violation)

            # Check 2: Response size anomaly detection
            if isinstance(data, list) and len(data) > 1000:
                violation = await self._create_security_violation(
                    violation_type="unusual_response_size",
                    severity="MEDIUM",
                    details={
                        "tenant_id": tenant_id,
                        "response_size": len(data),
                        "threshold": 1000,
                    },
                )
                # Log but don't block for size anomalies
                await self._handle_security_violation(violation, block=False)

            # Check 3: Sensitive data patterns
            sensitive_patterns = [
                r'REDACTED_SECRET["\s]*:',
                r'secret["\s]*:',
                r'api[_-]?key["\s]*:',
                r'token["\s]*:',
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email patterns
            ]

            for pattern in sensitive_patterns:
                if re.search(pattern, data_str, re.IGNORECASE):
                    violation = await self._create_security_violation(
                        violation_type="sensitive_data_in_response",
                        severity="HIGH",
                        details={
                            "tenant_id": tenant_id,
                            "pattern_matched": pattern,
                            "data_sample": data_str[:200] + "...",
                        },
                    )
                    # Log but don't block - might be legitimate
                    await self._handle_security_violation(violation, block=False)

            return {"clean": True, "message": "Response data validated"}

        except Exception as e:
            logger.error(f"Response data scanning error: {e}")
            return {"clean": False, "error": str(e)}

    async def validate_input_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate input parameters for security threats.

        Protects against injection attacks and malicious input.
        """
        try:
            if not self.security_policies["sql_injection_protection"].enabled:
                return {"safe": True, "message": "Input validation disabled"}

            # SQL injection patterns
            sql_patterns = [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b)",
                r"(\b(UNION|JOIN)\b.*\b(SELECT)\b)",
                r"(--|\#|\/\*|\*\/)",
                r"(\b(OR|AND)\b.*[\"'].*[\"'].*=.*[\"'].*[\"'])",
                r"(\b(OR|AND)\b.*\d+.*=.*\d+)",
                r"([\"'][^\"']*[\"'])\s*=\s*\1",
                r"(\b(DROP|DELETE)\b.*\b(TABLE|DATABASE)\b)",
            ]

            # XSS patterns
            xss_patterns = [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"vbscript:",
                r"onload\s*=",
                r"onerror\s*=",
                r"onclick\s*=",
            ]

            # Path traversal patterns
            traversal_patterns = [
                r"\.\./",
                r"\.\.\\",
                r"/etc/passwd",
                r"/windows/system32",
            ]

            violations = []

            for key, value in params.items():
                if not isinstance(value, str):
                    continue

                value_lower = value.lower()

                # Check SQL injection
                for pattern in sql_patterns:
                    if re.search(pattern, value_lower, re.IGNORECASE):
                        violations.append(
                            {
                                "type": "sql_injection_attempt",
                                "parameter": key,
                                "pattern": pattern,
                                "value_sample": (
                                    value[:100] + "..." if len(value) > 100 else value
                                ),
                            },
                        )

                # Check XSS
                for pattern in xss_patterns:
                    if re.search(pattern, value_lower, re.IGNORECASE):
                        violations.append(
                            {
                                "type": "xss_attempt",
                                "parameter": key,
                                "pattern": pattern,
                                "value_sample": (
                                    value[:100] + "..." if len(value) > 100 else value
                                ),
                            },
                        )

                # Check path traversal
                for pattern in traversal_patterns:
                    if re.search(pattern, value_lower, re.IGNORECASE):
                        violations.append(
                            {
                                "type": "path_traversal_attempt",
                                "parameter": key,
                                "pattern": pattern,
                                "value_sample": (
                                    value[:100] + "..." if len(value) > 100 else value
                                ),
                            },
                        )

            if violations:
                violation = await self._create_security_violation(
                    violation_type="malicious_input_detected",
                    severity="HIGH",
                    details={
                        "tenant_id": get_current_tenant_id(),
                        "violations": violations,
                        "parameter_count": len(params),
                    },
                )
                return await self._handle_security_violation(violation)

            return {"safe": True, "message": "Input parameters validated"}

        except Exception as e:
            logger.error(f"Input validation error: {e}")
            return {"safe": False, "error": str(e)}

    async def monitor_authentication_patterns(
        self,
        tenant_id: str,
        user_id: str,
        success: bool,
        metadata: dict[str, Any],
    ) -> None:
        """Monitor authentication patterns for anomalies"""
        try:
            current_time = datetime.utcnow()
            key = f"{tenant_id}:{user_id}"

            # Initialize tracking for this user if not exists
            if key not in self.suspicious_patterns:
                self.suspicious_patterns[key] = []

            # Record authentication event
            event = {
                "timestamp": current_time.isoformat(),
                "success": success,
                "ip_address": metadata.get("ip_address"),
                "user_agent": metadata.get("user_agent"),
            }

            self.suspicious_patterns[key].append(event)

            # Keep only recent events (last 24 hours)
            cutoff_time = current_time - timedelta(hours=24)
            self.suspicious_patterns[key] = [
                e
                for e in self.suspicious_patterns[key]
                if datetime.fromisoformat(e["timestamp"]) > cutoff_time
            ]

            events = self.suspicious_patterns[key]

            # Analyze patterns
            failed_attempts = [e for e in events if not e["success"]]

            # Check for excessive failed attempts
            if len(failed_attempts) >= 5:
                recent_failures = [
                    e
                    for e in failed_attempts
                    if datetime.fromisoformat(e["timestamp"])
                    > current_time - timedelta(minutes=30)
                ]

                if len(recent_failures) >= 3:
                    violation = await self._create_security_violation(
                        violation_type="excessive_failed_logins",
                        severity="HIGH",
                        details={
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "failed_attempts": len(recent_failures),
                            "time_window": "30 minutes",
                            "ip_addresses": list(
                                set(
                                    e.get("ip_address")
                                    for e in recent_failures
                                    if e.get("ip_address")
                                ),
                            ),
                        },
                    )
                    await self._handle_security_violation(violation, block=False)

            # Check for unusual locations (different IP addresses)
            ip_addresses = list(
                set(e.get("ip_address") for e in events if e.get("ip_address")),
            )
            if len(ip_addresses) > 3:  # Multiple IPs in 24 hours might be suspicious
                violation = await self._create_security_violation(
                    violation_type="multiple_ip_authentication",
                    severity="MEDIUM",
                    details={
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "ip_count": len(ip_addresses),
                        "ip_addresses": ip_addresses[:5],  # Limit for privacy
                    },
                )
                await self._handle_security_violation(violation, block=False)

        except Exception as e:
            logger.error(f"Authentication pattern monitoring error: {e}")

    # Helper methods

    async def _create_security_violation(
        self,
        violation_type: str,
        severity: str,
        details: dict[str, Any],
    ) -> SecurityViolation:
        """Create security violation record"""
        request_context = get_current_request_context()

        return SecurityViolation(
            violation_id=str(uuid.uuid4()),
            violation_type=violation_type,
            severity=severity,
            tenant_id=get_current_tenant_id(),
            user_id=get_current_user_id(),
            details=details,
            timestamp=datetime.utcnow(),
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None,
            blocked=False,  # Will be set by handler
        )

    async def _handle_security_violation(
        self,
        violation: SecurityViolation,
        block: bool = True,
    ) -> dict[str, Any]:
        """Handle security violation based on policy"""
        try:
            # Determine action based on severity and policy
            policy = self.security_policies.get(
                violation.violation_type.replace("_", "_"),
                self.security_policies.get("cross_tenant_access"),
            )

            should_block = block and (
                policy.action == "block" and violation.severity in ["CRITICAL", "HIGH"]
            )

            violation.blocked = should_block

            # Record violation
            self.violation_log.append(violation)
            self.security_metrics.record_violation(violation)

            # Log violation
            logger.warning(
                f"Security violation detected: {violation.violation_type} "
                f"[{violation.severity}] - {violation.details}",
            )

            # Block if necessary
            if should_block:
                if violation.ip_address:
                    self.blocked_ips.add(violation.ip_address)

                return {
                    "allowed": False,
                    "blocked": True,
                    "violation_id": violation.violation_id,
                    "violation_type": violation.violation_type,
                    "severity": violation.severity,
                    "message": f"Request blocked due to security policy violation: {violation.violation_type}",
                }

            # Log only
            return {
                "allowed": True,
                "blocked": False,
                "violation_id": violation.violation_id,
                "warning": f"Security concern logged: {violation.violation_type}",
            }

        except Exception as e:
            logger.error(f"Error handling security violation: {e}")
            return {"allowed": False, "blocked": True, "error": "Security system error"}

    async def _check_rate_limit(
        self,
        tenant_id: str,
        user_id: str | None,
    ) -> dict[str, Any]:
        """Check rate limiting for tenant/user"""
        current_time = time.time()
        rate_limit_key = f"{tenant_id}:{user_id or 'anonymous'}"

        if rate_limit_key not in self.rate_limits:
            self.rate_limits[rate_limit_key] = {"requests": [], "blocked_until": 0}

        rate_data = self.rate_limits[rate_limit_key]

        # Check if currently blocked
        if current_time < rate_data["blocked_until"]:
            return {
                "allowed": False,
                "reason": "rate_limit_blocked",
                "blocked_until": rate_data["blocked_until"],
            }

        # Clean old requests (last minute)
        minute_ago = current_time - 60
        rate_data["requests"] = [
            req for req in rate_data["requests"] if req > minute_ago
        ]

        # Check rate limit
        policy = self.security_policies["rate_limiting"]
        requests_per_minute = policy.parameters.get("requests_per_minute", 100)

        if len(rate_data["requests"]) >= requests_per_minute:
            # Block for configured duration
            block_duration = policy.parameters.get("block_duration_minutes", 15) * 60
            rate_data["blocked_until"] = current_time + block_duration

            return {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "requests_in_minute": len(rate_data["requests"]),
                "limit": requests_per_minute,
                "blocked_until": rate_data["blocked_until"],
            }

        # Record request
        rate_data["requests"].append(current_time)

        return {
            "allowed": True,
            "requests_in_minute": len(rate_data["requests"]),
            "limit": requests_per_minute,
        }

    async def _detect_suspicious_patterns(self, operation: str, resource: str) -> bool:
        """Detect suspicious access patterns"""
        # Simple pattern detection - could be enhanced with ML

        # Check for rapid repeated requests
        current_time = time.time()
        tenant_id = get_current_tenant_id()

        if not tenant_id:
            return False

        pattern_key = f"{tenant_id}:{operation}:{resource}"

        if pattern_key not in self.suspicious_patterns:
            self.suspicious_patterns[pattern_key] = []

        # Clean old requests (last 5 minutes)
        five_minutes_ago = current_time - 300
        self.suspicious_patterns[pattern_key] = [
            req
            for req in self.suspicious_patterns[pattern_key]
            if req > five_minutes_ago
        ]

        # Record current request
        self.suspicious_patterns[pattern_key].append(current_time)

        # Check for suspicious frequency (more than 20 requests in 5 minutes)
        return len(self.suspicious_patterns[pattern_key]) > 20

    async def _extract_tenant_ids_from_data(self, data_str: str) -> set[str]:
        """Extract potential tenant IDs from data string"""
        # Look for UUID patterns that might be tenant IDs
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        tenant_id_pattern = r'tenant[-_]?id["\s]*[:=]["\s]*([0-9a-f-]+)'

        tenant_ids = set()

        # Extract from tenant_id fields
        tenant_matches = re.findall(tenant_id_pattern, data_str, re.IGNORECASE)
        tenant_ids.update(tenant_matches)

        # Extract UUIDs that might be tenant IDs
        uuid_matches = re.findall(uuid_pattern, data_str, re.IGNORECASE)

        # Filter UUIDs that appear in tenant-like contexts
        for uuid_match in uuid_matches:
            context = data_str[
                max(0, data_str.find(uuid_match) - 50) : data_str.find(uuid_match)
                + len(uuid_match)
                + 50
            ]
            if re.search(r"tenant", context, re.IGNORECASE):
                tenant_ids.add(uuid_match)

        return tenant_ids

    # Public API methods

    def get_security_metrics(self) -> dict[str, Any]:
        """Get current security metrics"""
        return {
            "security_score": self.security_metrics.get_security_score(),
            "total_requests": self.security_metrics.total_requests,
            "violations_by_type": dict(self.security_metrics.violations_by_type),
            "violations_by_severity": dict(
                self.security_metrics.violations_by_severity,
            ),
            "blocked_requests": self.security_metrics.blocked_requests,
            "blocked_ips_count": len(self.blocked_ips),
            "last_reset": self.security_metrics.last_reset.isoformat(),
            "active_policies": len(
                [p for p in self.security_policies.values() if p.enabled],
            ),
        }

    def get_recent_violations(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent security violations"""
        recent_violations = sorted(
            self.violation_log[-limit:],
            key=lambda x: x.timestamp,
            reverse=True,
        )

        return [
            {
                "violation_id": v.violation_id,
                "violation_type": v.violation_type,
                "severity": v.severity,
                "tenant_id": v.tenant_id,
                "user_id": v.user_id,
                "timestamp": v.timestamp.isoformat(),
                "blocked": v.blocked,
                "details": v.details,
            }
            for v in recent_violations
        ]

    def update_security_policy(self, policy_name: str, policy: SecurityPolicy) -> bool:
        """Update security policy"""
        try:
            self.security_policies[policy_name] = policy
            logger.info(f"Security policy updated: {policy_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update security policy {policy_name}: {e}")
            return False

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        return ip_address in self.blocked_ips

    def unblock_ip(self, ip_address: str) -> bool:
        """Unblock IP address"""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            logger.info(f"IP address unblocked: {ip_address}")
            return True
        return False

    async def health_check(self) -> dict[str, Any]:
        """Security system health check"""
        try:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "active_policies": len(
                    [p for p in self.security_policies.values() if p.enabled],
                ),
                "security_score": self.security_metrics.get_security_score(),
                "recent_violations": len(
                    [
                        v
                        for v in self.violation_log
                        if v.timestamp > datetime.utcnow() - timedelta(hours=1)
                    ],
                ),
                "blocked_ips": len(self.blocked_ips),
                "service": "tenant_isolation_enforcer",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "service": "tenant_isolation_enforcer",
            }


# Global instance
_security_enforcer: TenantIsolationEnforcer | None = None


def get_security_enforcer() -> TenantIsolationEnforcer:
    """Get global security enforcer instance"""
    global _security_enforcer
    if _security_enforcer is None:
        _security_enforcer = TenantIsolationEnforcer()
    return _security_enforcer


# Decorator for automatic security enforcement


def enforce_tenant_isolation(operation: str, resource: str):
    """Decorator to enforce tenant isolation on functions"""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            enforcer = get_security_enforcer()

            # Extract tenant ID from kwargs or context
            tenant_id = kwargs.get("tenant_id") or get_current_tenant_id()

            if tenant_id:
                # Validate access
                validation = await enforcer.validate_tenant_access(
                    tenant_id,
                    operation,
                    resource,
                )

                if not validation.get("allowed"):
                    raise PermissionError(f"Access denied: {validation.get('message')}")

            # Execute original function
            result = await func(*args, **kwargs)

            # Scan response for data leakage
            if tenant_id and result is not None:
                scan_result = await enforcer.scan_response_data(result, tenant_id)
                if not scan_result.get("clean"):
                    logger.warning(f"Data leakage concern in {operation}:{resource}")

            return result

        return wrapper

    return decorator


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        enforcer = TenantIsolationEnforcer()

        print("Tenant Isolation Security Enforcer")
        print("=" * 50)

        # Test security metrics
        metrics = enforcer.get_security_metrics()
        print(f"Security Score: {metrics['security_score']}%")
        print(f"Active Policies: {metrics['active_policies']}")

        # Test health check
        health = await enforcer.health_check()
        print(f"Status: {health['status']}")

        print("\nSecurity enforcer ready for multi-tenant protection!")

    asyncio.run(main())
