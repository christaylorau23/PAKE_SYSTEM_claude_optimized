#!/usr/bin/env python3
"""AI-Assisted Security Monitoring System
=====================================

This service integrates with ELK stack to consume JSON logs and uses AI/LLM
capabilities to analyze patterns for security anomalies and threats.

Features:
- Real-time log analysis from Elasticsearch
- AI-powered anomaly detection
- Integration with existing MCP system
- RESTful API for security alerts
- Support for multiple security patterns (failed logins, SQL injection, etc.)
"""

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import uvicorn

# FastAPI and async dependencies
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

# Elasticsearch integration
try:
    from elasticsearch import AsyncElasticsearch

    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    print(
        "⚠️ Elasticsearch client not available. Install with: pip install elasticsearch",
    )

# MCP integration (using existing system)
import sys

sys.path.append("/d/Projects/PAKE_SYSTEM/mcp-servers")
try:
    from pake_mcp_server import SecurityLogger, VaultManager

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ MCP system not available. Some features will be limited.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("ai-security-monitor.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ============================================================================
# AI/LLM MOCK SYSTEM
# ============================================================================


class SecurityPatternType(Enum):
    FAILED_LOGIN = "failed_login"
    SQL_INJECTION = "sql_injection"
    SLOW_QUERY = "slow_query"
    SUSPICIOUS_ACCESS = "suspicious_access"
    RATE_LIMITING = "rate_limiting"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    UNKNOWN_ANOMALY = "unknown_anomaly"


@dataclass
class SecurityAlert:
    """Security alert data structure"""

    id: str
    timestamp: datetime
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    pattern_type: SecurityPatternType
    source_ip: str | None
    user_agent: str | None
    endpoint: str | None
    message: str
    ai_confidence: float
    raw_logs: list[dict[str, Any]]
    recommended_actions: list[str]
    risk_score: int  # 1-100


class MockLLMAnalyzer:
    """Mock LLM system for analyzing security patterns
    In production, this would connect to OpenAI API, Claude, or local LLM
    """

    def __init__(self):
        self.security_patterns = {
            "failed_login": [
                r"failed.*login",
                r"authentication.*failed",
                r"invalid.*credentials",
                r"unauthorized.*access",
                r"401.*unauthorized",
            ],
            "sql_injection": [
                r"(union|select|insert|update|delete).*(\-\-|\/\*)",
                r"or.*1=1",
                r"drop.*table",
                r"exec.*sp_",
                r"information_schema",
            ],
            "slow_query": [
                r"slow.*query",
                r"execution.*time.*\d{3,}",  # >100ms
                r"timeout.*exceeded",
                r"query.*duration.*\d+\.?\d*s",
            ],
            "xss_attempt": [
                r"<script.*?>",
                r"javascript:",
                r"onerror.*=",
                r"alert\(",
                r"document\.cookie",
            ],
            "path_traversal": [
                r"\.\.\/\.\.\/",
                r"\.\.\\\.\.\\",
                r"\/etc\/passwd",
                r"\/windows\/system32",
                r"\.\..*\/.*\.\.",
            ],
        }

        self.ip_reputation_cache = {}
        self.user_behavior_baseline = {}

    async def analyze_log_batch(
        self,
        logs: list[dict[str, Any]],
    ) -> list[SecurityAlert]:
        """Analyze a batch of logs for security patterns
        Mock implementation using pattern matching and heuristics
        """
        alerts = []

        for log_entry in logs:
            try:
                # Extract common fields
                timestamp = self._parse_timestamp(log_entry.get("timestamp", ""))
                message = log_entry.get("message", "")
                source_ip = log_entry.get("source_ip", log_entry.get("client_ip", ""))
                user_agent = log_entry.get("user_agent", "")
                endpoint = log_entry.get("endpoint", log_entry.get("path", ""))
                status_code = log_entry.get("status_code", 0)

                # Run pattern detection
                detected_patterns = self._detect_security_patterns(message, log_entry)

                for pattern_type, confidence in detected_patterns:
                    alert = self._create_security_alert(
                        pattern_type=pattern_type,
                        confidence=confidence,
                        timestamp=timestamp,
                        source_ip=source_ip,
                        user_agent=user_agent,
                        endpoint=endpoint,
                        message=message,
                        raw_log=log_entry,
                    )
                    alerts.append(alert)

                # Additional behavioral analysis
                behavioral_alerts = await self._analyze_user_behavior(log_entry)
                alerts.extend(behavioral_alerts)

            except Exception as e:
                logger.error(f"Error analyzing log entry: {e}")
                continue

        # Post-process alerts for correlation
        correlated_alerts = self._correlate_alerts(alerts)

        return correlated_alerts

    def _detect_security_patterns(
        self,
        message: str,
        log_entry: dict[str, Any],
    ) -> list[tuple[SecurityPatternType, float]]:
        """Detect security patterns in log messages"""
        detected = []

        message_lower = message.lower()

        for pattern_name, regex_patterns in self.security_patterns.items():
            confidence = 0.0
            matches = 0

            for pattern in regex_patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    matches += 1
                    confidence += 0.3

            if matches > 0:
                # Adjust confidence based on context
                if pattern_name == "failed_login":
                    if log_entry.get("status_code") == 401:
                        confidence += 0.4
                    if "REDACTED_SECRET" in message_lower or "username" in message_lower:
                        confidence += 0.2

                elif pattern_name == "sql_injection":
                    if log_entry.get("endpoint", "").endswith(("/api/", "/query")):
                        confidence += 0.3
                    if log_entry.get("method") == "POST":
                        confidence += 0.2

                elif pattern_name == "slow_query":
                    # Extract execution time if available
                    time_match = re.search(
                        r"(\d+\.?\d*)\s*(?:ms|seconds?)",
                        message_lower,
                    )
                    if time_match:
                        exec_time = float(time_match.group(1))
                        if exec_time > 1000:  # >1 second
                            confidence += 0.5
                        elif exec_time > 500:  # >500ms
                            confidence += 0.3

                # Cap confidence at 1.0
                confidence = min(confidence, 1.0)

                if confidence > 0.3:  # Threshold for alert generation
                    try:
                        pattern_type = SecurityPatternType(pattern_name)
                        detected.append((pattern_type, confidence))
                    except ValueError:
                        continue

        return detected

    async def _analyze_user_behavior(
        self,
        log_entry: dict[str, Any],
    ) -> list[SecurityAlert]:
        """Analyze user behavior patterns for anomalies"""
        alerts = []

        source_ip = log_entry.get("source_ip", log_entry.get("client_ip", ""))
        if not source_ip:
            return alerts

        # Track request frequency (simple rate limiting detection)
        current_time = time.time()
        if source_ip not in self.user_behavior_baseline:
            self.user_behavior_baseline[source_ip] = {
                "request_times": [],
                "endpoints": set(),
                "user_agents": set(),
            }

        baseline = self.user_behavior_baseline[source_ip]
        baseline["request_times"].append(current_time)

        # Keep only recent requests (last 5 minutes)
        cutoff_time = current_time - 300
        baseline["request_times"] = [
            t for t in baseline["request_times"] if t > cutoff_time
        ]

        # Check for rate limiting violations
        if len(baseline["request_times"]) > 100:  # >100 requests in 5 minutes
            alert = SecurityAlert(
                id=self._generate_alert_id(),
                timestamp=datetime.now(),
                severity="HIGH",
                pattern_type=SecurityPatternType.RATE_LIMITING,
                source_ip=source_ip,
                user_agent=log_entry.get("user_agent", ""),
                endpoint=log_entry.get("endpoint", ""),
                message=f"Excessive requests detected: {len(baseline['request_times'])} requests in 5 minutes",
                ai_confidence=0.9,
                raw_logs=[log_entry],
                recommended_actions=[
                    "Block or rate limit source IP",
                    "Investigate for potential DDoS attack",
                    "Review application rate limiting policies",
                ],
                risk_score=85,
            )
            alerts.append(alert)

        return alerts

    def _create_security_alert(
        self,
        pattern_type: SecurityPatternType,
        confidence: float,
        timestamp: datetime,
        source_ip: str,
        user_agent: str,
        endpoint: str,
        message: str,
        raw_log: dict[str, Any],
    ) -> SecurityAlert:
        """Create a security alert from detected pattern"""
        # Determine severity based on pattern type and confidence
        severity = self._calculate_severity(pattern_type, confidence)
        risk_score = self._calculate_risk_score(pattern_type, confidence, raw_log)

        # Generate recommended actions
        recommended_actions = self._get_recommended_actions(pattern_type, raw_log)

        alert = SecurityAlert(
            id=self._generate_alert_id(),
            timestamp=timestamp,
            severity=severity,
            pattern_type=pattern_type,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            message=self._generate_alert_message(pattern_type, message, raw_log),
            ai_confidence=confidence,
            raw_logs=[raw_log],
            recommended_actions=recommended_actions,
            risk_score=risk_score,
        )

        return alert

    def _calculate_severity(
        self,
        pattern_type: SecurityPatternType,
        confidence: float,
    ) -> str:
        """Calculate alert severity"""
        base_severity = {
            SecurityPatternType.SQL_INJECTION: "CRITICAL",
            SecurityPatternType.PATH_TRAVERSAL: "CRITICAL",
            SecurityPatternType.PRIVILEGE_ESCALATION: "CRITICAL",
            SecurityPatternType.DATA_EXFILTRATION: "CRITICAL",
            SecurityPatternType.XSS_ATTEMPT: "HIGH",
            SecurityPatternType.FAILED_LOGIN: "MEDIUM",
            SecurityPatternType.SLOW_QUERY: "LOW",
            SecurityPatternType.SUSPICIOUS_ACCESS: "MEDIUM",
            SecurityPatternType.RATE_LIMITING: "HIGH",
            SecurityPatternType.UNKNOWN_ANOMALY: "MEDIUM",
        }.get(pattern_type, "LOW")

        # Adjust severity based on confidence
        if confidence < 0.5:
            severity_map = {
                "CRITICAL": "HIGH",
                "HIGH": "MEDIUM",
                "MEDIUM": "LOW",
                "LOW": "LOW",
            }
            return severity_map.get(base_severity, base_severity)

        return base_severity

    def _calculate_risk_score(
        self,
        pattern_type: SecurityPatternType,
        confidence: float,
        raw_log: dict[str, Any],
    ) -> int:
        """Calculate risk score (1-100)"""
        base_scores = {
            SecurityPatternType.SQL_INJECTION: 95,
            SecurityPatternType.PATH_TRAVERSAL: 90,
            SecurityPatternType.PRIVILEGE_ESCALATION: 95,
            SecurityPatternType.DATA_EXFILTRATION: 100,
            SecurityPatternType.XSS_ATTEMPT: 75,
            SecurityPatternType.FAILED_LOGIN: 40,
            SecurityPatternType.SLOW_QUERY: 25,
            SecurityPatternType.SUSPICIOUS_ACCESS: 60,
            SecurityPatternType.RATE_LIMITING: 70,
            SecurityPatternType.UNKNOWN_ANOMALY: 50,
        }.get(pattern_type, 30)

        # Adjust based on confidence
        adjusted_score = int(base_scores * confidence)

        # Additional adjustments based on context
        if raw_log.get("status_code") == 200:
            adjusted_score += 10  # Successful requests are more concerning

        if raw_log.get("source_ip", "").startswith("10.") or raw_log.get(
            "source_ip",
            "",
        ).startswith("192.168."):
            adjusted_score -= 20  # Internal IPs are less risky

        return max(1, min(100, adjusted_score))

    def _get_recommended_actions(
        self,
        pattern_type: SecurityPatternType,
        raw_log: dict[str, Any],
    ) -> list[str]:
        """Generate recommended actions for each pattern type"""
        actions_map = {
            SecurityPatternType.SQL_INJECTION: [
                "Block source IP immediately",
                "Review and sanitize database query inputs",
                "Enable SQL injection protection in WAF",
                "Audit database access logs",
                "Implement parameterized queries",
            ],
            SecurityPatternType.PATH_TRAVERSAL: [
                "Block source IP immediately",
                "Review file access controls",
                "Implement path sanitization",
                "Audit file system access logs",
                "Enable file upload restrictions",
            ],
            SecurityPatternType.XSS_ATTEMPT: [
                "Block malicious requests",
                "Review input validation",
                "Implement Content Security Policy",
                "Enable XSS protection headers",
                "Sanitize user inputs",
            ],
            SecurityPatternType.FAILED_LOGIN: [
                "Monitor for brute force patterns",
                "Implement account lockout policies",
                "Enable multi-factor authentication",
                "Review user access logs",
                "Consider IP-based blocking",
            ],
            SecurityPatternType.SLOW_QUERY: [
                "Optimize database queries",
                "Review database indexing",
                "Monitor query performance",
                "Implement query timeout limits",
                "Consider database scaling",
            ],
            SecurityPatternType.RATE_LIMITING: [
                "Implement rate limiting rules",
                "Block or throttle source IP",
                "Review DDoS protection",
                "Monitor traffic patterns",
                "Scale infrastructure if needed",
            ],
        }

        return actions_map.get(
            pattern_type,
            [
                "Investigate the anomaly further",
                "Review application logs",
                "Monitor for similar patterns",
                "Consider implementing additional security controls",
            ],
        )

    def _generate_alert_message(
        self,
        pattern_type: SecurityPatternType,
        original_message: str,
        raw_log: dict[str, Any],
    ) -> str:
        """Generate human-readable alert message"""
        source_ip = raw_log.get("source_ip", raw_log.get("client_ip", "Unknown"))
        endpoint = raw_log.get("endpoint", raw_log.get("path", "Unknown"))

        templates = {
            SecurityPatternType.SQL_INJECTION: f"SQL injection attempt detected from {source_ip} on endpoint {endpoint}",
            SecurityPatternType.PATH_TRAVERSAL: f"Path traversal attempt detected from {source_ip} targeting {endpoint}",
            SecurityPatternType.XSS_ATTEMPT: f"Cross-site scripting attempt from {source_ip} on {endpoint}",
            SecurityPatternType.FAILED_LOGIN: f"Failed login attempt from {source_ip}",
            SecurityPatternType.SLOW_QUERY: f"Slow database query detected (source: {source_ip})",
            SecurityPatternType.RATE_LIMITING: f"Rate limiting violation from {source_ip}",
            SecurityPatternType.SUSPICIOUS_ACCESS: f"Suspicious access pattern from {source_ip}",
        }

        return templates.get(
            pattern_type,
            f"Security anomaly detected: {original_message[:100]}",
        )

    def _correlate_alerts(self, alerts: list[SecurityAlert]) -> list[SecurityAlert]:
        """Correlate related alerts to reduce noise"""
        if len(alerts) <= 1:
            return alerts

        # Group alerts by source IP and pattern type
        alert_groups = {}
        for alert in alerts:
            key = (alert.source_ip, alert.pattern_type.value)
            if key not in alert_groups:
                alert_groups[key] = []
            alert_groups[key].append(alert)

        # Merge related alerts
        correlated_alerts = []
        for group_alerts in alert_groups.values():
            if len(group_alerts) == 1:
                correlated_alerts.extend(group_alerts)
            else:
                # Create a single consolidated alert
                merged_alert = self._merge_alerts(group_alerts)
                correlated_alerts.append(merged_alert)

        return correlated_alerts

    def _merge_alerts(self, alerts: list[SecurityAlert]) -> SecurityAlert:
        """Merge multiple related alerts into one"""
        if not alerts:
            return None

        first_alert = alerts[0]

        # Merge raw logs
        all_raw_logs = []
        for alert in alerts:
            all_raw_logs.extend(alert.raw_logs)

        # Calculate average confidence
        avg_confidence = sum(alert.ai_confidence for alert in alerts) / len(alerts)

        # Use highest risk score
        max_risk_score = max(alert.risk_score for alert in alerts)

        # Update message to reflect multiple occurrences
        merged_message = (
            f"{first_alert.message} (+ {len(alerts) - 1} similar occurrences)"
        )

        return SecurityAlert(
            id=self._generate_alert_id(),
            timestamp=first_alert.timestamp,
            severity=first_alert.severity,
            pattern_type=first_alert.pattern_type,
            source_ip=first_alert.source_ip,
            user_agent=first_alert.user_agent,
            endpoint=first_alert.endpoint,
            message=merged_message,
            ai_confidence=avg_confidence,
            raw_logs=all_raw_logs,
            recommended_actions=first_alert.recommended_actions,
            risk_score=max_risk_score,
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from various formats"""
        if not timestamp_str:
            return datetime.now()

        # Common timestamp formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with microseconds
            "%Y-%m-%dT%H:%M:%SZ",  # ISO format
            "%Y-%m-%d %H:%M:%S",  # Standard format
            "%d/%b/%Y:%H:%M:%S %z",  # Apache log format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # If all parsing fails, return current time
        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return datetime.now()

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        timestamp = str(int(time.time() * 1000000))
        random_data = os.urandom(8).hex()
        return f"ai-sec-{timestamp}-{random_data[:8]}"


# ============================================================================
# ELASTICSEARCH INTEGRATION
# ============================================================================


class ElasticsearchLogConsumer:
    """Consumes logs from Elasticsearch for analysis"""

    def __init__(
        self,
        elasticsearch_host: str = "localhost",
        elasticsearch_port: int = 9200,
    ):
        self.host = elasticsearch_host
        self.port = elasticsearch_port
        self.client = None
        self.last_query_time = datetime.now() - timedelta(minutes=5)

        if ELASTICSEARCH_AVAILABLE:
            try:
                self.client = AsyncElasticsearch(
                    [f"http://{elasticsearch_host}:{elasticsearch_port}"],
                )
                logger.info(
                    f"Connected to Elasticsearch at {elasticsearch_host}:{
                        elasticsearch_port
                    }",
                )
            except Exception as e:
                logger.error(f"Failed to connect to Elasticsearch: {e}")
                self.client = None
        else:
            logger.warning("Elasticsearch client not available")

    async def fetch_recent_logs(
        self,
        index_pattern: str = "logs-*",
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch recent logs from Elasticsearch"""
        if not self.client:
            return self._generate_mock_logs(limit)

        try:
            # Query for logs since last fetch
            query = {
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": self.last_query_time.isoformat(),
                            "lte": datetime.now().isoformat(),
                        },
                    },
                },
                "sort": [{"@timestamp": {"order": "desc"}}],
                "size": limit,
            }

            response = await self.client.search(index=index_pattern, body=query)
            logs = []

            for hit in response["hits"]["hits"]:
                log_entry = hit["_source"]
                log_entry["_id"] = hit["_id"]
                log_entry["_index"] = hit["_index"]
                logs.append(log_entry)

            self.last_query_time = datetime.now()
            logger.info(f"Fetched {len(logs)} logs from Elasticsearch")
            return logs

        except Exception as e:
            logger.error(f"Error fetching logs from Elasticsearch: {e}")
            return self._generate_mock_logs(limit)

    def _generate_mock_logs(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate mock logs for testing when Elasticsearch is not available"""
        mock_logs = []

        # Mock log patterns
        patterns = [
            # Normal logs
            {
                "timestamp": datetime.now().isoformat(),
                "message": "User logged in successfully",
                "source_ip": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "endpoint": "/api/auth/login",
                "status_code": 200,
                "method": "POST",
                "user_id": "user123",
            },
            # Failed login
            {
                "timestamp": datetime.now().isostring(),
                "message": "Authentication failed for user admin",
                "source_ip": "203.0.113.45",
                "user_agent": "Python/3.9 requests/2.25.1",
                "endpoint": "/api/auth/login",
                "status_code": 401,
                "method": "POST",
                "attempted_username": "REDACTED_SECRET",
            },
            # SQL injection attempt
            {
                "timestamp": datetime.now().isoformat(),
                "message": "Database query: SELECT * FROM users WHERE id = 1 OR 1=1--",
                "source_ip": "198.51.100.42",
                "user_agent": "curl/7.68.0",
                "endpoint": "/api/users/search",
                "status_code": 500,
                "method": "GET",
                "query_duration": "1250ms",
            },
            # Slow query
            {
                "timestamp": datetime.now().isoformat(),
                "message": "Slow query detected: execution time 3.5 seconds",
                "source_ip": "192.168.1.50",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "endpoint": "/api/reports/generate",
                "status_code": 200,
                "method": "POST",
                "query_duration": "3500ms",
            },
            # XSS attempt
            {
                "timestamp": datetime.now().isoformat(),
                "message": "Suspicious input detected: <script>alert('XSS')</script>",
                "source_ip": "203.0.113.100",
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64)",
                "endpoint": "/api/comments/create",
                "status_code": 400,
                "method": "POST",
                "payload": "<script>alert('XSS')</script>",
            },
        ]

        import random

        for i in range(min(count, len(patterns) * 3)):
            pattern = random.choice(patterns)
            mock_log = pattern.copy()
            # Vary timestamp slightly
            base_time = datetime.now() - timedelta(minutes=random.randint(0, 30))
            mock_log["timestamp"] = base_time.isoformat()
            mock_logs.append(mock_log)

        logger.info(f"Generated {len(mock_logs)} mock logs for testing")
        return mock_logs

    async def close(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()


# ============================================================================
# MCP INTEGRATION
# ============================================================================


class MCPSecurityIntegration:
    """Integration with existing MCP system for enhanced analysis"""

    def __init__(self):
        self.vault_manager = None
        self.security_logger = None

        if MCP_AVAILABLE:
            try:
                self.vault_manager = VaultManager()
                self.security_logger = SecurityLogger()
                logger.info("MCP integration initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MCP integration: {e}")
        else:
            logger.warning("MCP system not available")

    async def enrich_alert_context(self, alert: SecurityAlert) -> SecurityAlert:
        """Enrich security alert with additional context from MCP system"""
        if not self.vault_manager:
            return alert

        try:
            # Add threat intelligence context
            if alert.source_ip:
                ip_context = await self._get_ip_context(alert.source_ip)
                if ip_context:
                    alert.message += f" (IP Context: {ip_context})"

            # Add historical context
            similar_alerts = await self._get_similar_historical_alerts(alert)
            if similar_alerts:
                alert.recommended_actions.append(
                    f"Similar incidents occurred {len(similar_alerts)} times in the past 30 days",
                )

            # Log to MCP security system
            if self.security_logger:
                await self.security_logger.log_security_event(
                    {
                        "alert_id": alert.id,
                        "pattern_type": alert.pattern_type.value,
                        "severity": alert.severity,
                        "source_ip": alert.source_ip,
                        "confidence": alert.ai_confidence,
                        "risk_score": alert.risk_score,
                    },
                )

        except Exception as e:
            logger.error(f"Error enriching alert context: {e}")

        return alert

    async def _get_ip_context(self, ip_address: str) -> str | None:
        """Get additional context for IP address"""
        # Mock implementation - in reality this would query threat intelligence
        suspicious_ips = ["203.0.113.45", "198.51.100.42", "203.0.113.100"]

        if ip_address in suspicious_ips:
            return "Known malicious IP"
        if ip_address.startswith(("10.", "192.168.", "172.")):
            return "Internal network"
        return "External IP"

    async def _get_similar_historical_alerts(
        self,
        alert: SecurityAlert,
    ) -> list[dict[str, Any]]:
        """Get similar alerts from historical data"""
        # Mock implementation - in reality this would query the MCP vault
        return []


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================


app = FastAPI(
    title="AI Security Monitor",
    description="AI-powered security monitoring system with ELK integration",
    version="1.0.0",
)

# Global components
llm_analyzer = MockLLMAnalyzer()
elk_consumer = ElasticsearchLogConsumer()
mcp_integration = MCPSecurityIntegration()

# In-memory storage for alerts (in production, use database)
security_alerts: list[SecurityAlert] = []
alert_history: dict[str, list[SecurityAlert]] = {}

# ============================================================================
# API MODELS
# ============================================================================


class SecurityAlertResponse(BaseModel):
    id: str
    timestamp: str
    severity: str
    pattern_type: str
    source_ip: str | None
    user_agent: str | None
    endpoint: str | None
    message: str
    ai_confidence: float
    risk_score: int
    recommended_actions: list[str]


class SecurityDashboard(BaseModel):
    total_alerts: int
    alerts_by_severity: dict[str, int]
    alerts_by_pattern: dict[str, int]
    recent_alerts: list[SecurityAlertResponse]
    system_status: str
    last_analysis_time: str


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "service": "AI Security Monitor",
        "version": "1.0.0",
        "status": "active",
        "features": {
            "elasticsearch_integration": ELASTICSEARCH_AVAILABLE,
            "mcp_integration": MCP_AVAILABLE,
            "ai_analysis": True,
        },
        "endpoints": {
            "alerts": "/alerts",
            "dashboard": "/dashboard",
            "analyze": "/analyze",
            "health": "/health",
        },
    }


@app.get("/alerts", response_model=list[SecurityAlertResponse])
async def get_security_alerts(
    severity: str | None = None,
    pattern_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Get security alerts with optional filtering"""
    global security_alerts

    # Filter alerts
    filtered_alerts = security_alerts.copy()

    if severity:
        filtered_alerts = [
            a for a in filtered_alerts if a.severity.lower() == severity.lower()
        ]

    if pattern_type:
        filtered_alerts = [
            a for a in filtered_alerts if a.pattern_type.value == pattern_type
        ]

    # Sort by timestamp (newest first)
    filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)

    # Pagination
    paginated_alerts = filtered_alerts[offset : offset + limit]

    # Convert to response model
    response_alerts = []
    for alert in paginated_alerts:
        response_alerts.append(
            SecurityAlertResponse(
                id=alert.id,
                timestamp=alert.timestamp.isoformat(),
                severity=alert.severity,
                pattern_type=alert.pattern_type.value,
                source_ip=alert.source_ip,
                user_agent=alert.user_agent,
                endpoint=alert.endpoint,
                message=alert.message,
                ai_confidence=alert.ai_confidence,
                risk_score=alert.risk_score,
                recommended_actions=alert.recommended_actions,
            ),
        )

    return response_alerts


@app.get("/dashboard", response_model=SecurityDashboard)
async def get_security_dashboard():
    """Get security monitoring dashboard"""
    global security_alerts

    # Calculate statistics
    total_alerts = len(security_alerts)

    alerts_by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    alerts_by_pattern = {}

    for alert in security_alerts:
        alerts_by_severity[alert.severity] += 1
        pattern_key = alert.pattern_type.value
        alerts_by_pattern[pattern_key] = alerts_by_pattern.get(pattern_key, 0) + 1

    # Get recent alerts (last 10)
    recent_alerts_data = sorted(
        security_alerts,
        key=lambda x: x.timestamp,
        reverse=True,
    )[:10]
    recent_alerts = []

    for alert in recent_alerts_data:
        recent_alerts.append(
            SecurityAlertResponse(
                id=alert.id,
                timestamp=alert.timestamp.isoformat(),
                severity=alert.severity,
                pattern_type=alert.pattern_type.value,
                source_ip=alert.source_ip,
                user_agent=alert.user_agent,
                endpoint=alert.endpoint,
                message=alert.message,
                ai_confidence=alert.ai_confidence,
                risk_score=alert.risk_score,
                recommended_actions=alert.recommended_actions,
            ),
        )

    return SecurityDashboard(
        total_alerts=total_alerts,
        alerts_by_severity=alerts_by_severity,
        alerts_by_pattern=alerts_by_pattern,
        recent_alerts=recent_alerts,
        system_status="active",
        last_analysis_time=datetime.now().isoformat(),
    )


@app.post("/analyze")
async def trigger_log_analysis(background_tasks: BackgroundTasks):
    """Manually trigger log analysis"""
    background_tasks.add_task(analyze_logs_task)
    return {"message": "Log analysis triggered", "status": "processing"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "ai_analyzer": "active",
            "elasticsearch": (
                "active"
                if ELASTICSEARCH_AVAILABLE and elk_consumer.client
                else "inactive"
            ),
            "mcp_integration": "active" if MCP_AVAILABLE else "inactive",
        },
        "metrics": {
            "total_alerts": len(security_alerts),
            "alert_rate": f"{len(security_alerts)} alerts/hour",  # Simplified metric
        },
    }


# ============================================================================
# BACKGROUND TASKS
# ============================================================================


async def analyze_logs_task():
    """Background task to analyze logs from ELK stack"""
    global security_alerts

    try:
        logger.info("Starting log analysis task...")

        # Fetch recent logs from Elasticsearch
        logs = await elk_consumer.fetch_recent_logs(limit=1000)

        if not logs:
            logger.info("No new logs to analyze")
            return

        # Analyze logs with AI/LLM
        new_alerts = await llm_analyzer.analyze_log_batch(logs)

        if new_alerts:
            # Enrich alerts with MCP context
            enriched_alerts = []
            for alert in new_alerts:
                enriched_alert = await mcp_integration.enrich_alert_context(alert)
                enriched_alerts.append(enriched_alert)

            # Add to global alerts storage
            security_alerts.extend(enriched_alerts)

            # Keep only recent alerts (last 7 days)
            cutoff_time = datetime.now() - timedelta(days=7)
            security_alerts = [a for a in security_alerts if a.timestamp > cutoff_time]

            # Log summary
            severity_counts = {}
            for alert in enriched_alerts:
                severity_counts[alert.severity] = (
                    severity_counts.get(alert.severity, 0) + 1
                )

            logger.info(
                f"Generated {len(enriched_alerts)} new alerts: {severity_counts}",
            )

        else:
            logger.info("No security alerts generated from recent logs")

    except Exception as e:
        logger.error(f"Error in log analysis task: {e}")


# ============================================================================
# STARTUP AND SHUTDOWN
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("🤖 AI Security Monitor starting up...")

    # Start background analysis task
    asyncio.create_task(periodic_analysis())

    logger.info("✅ AI Security Monitor ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("🔄 AI Security Monitor shutting down...")

    # Close Elasticsearch connection
    if elk_consumer:
        await elk_consumer.close()

    logger.info("✅ AI Security Monitor shutdown complete")


async def periodic_analysis():
    """Periodic task to analyze logs"""
    while True:
        try:
            await analyze_logs_task()
            # Run analysis every 5 minutes
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Error in periodic analysis: {e}")
            # Wait 1 minute before retrying on error
            await asyncio.sleep(60)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Security Monitor")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--elk-host", default="localhost", help="Elasticsearch host")
    parser.add_argument("--elk-port", type=int, default=9200, help="Elasticsearch port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # Initialize ELK consumer with custom host/port
    elk_consumer = ElasticsearchLogConsumer(args.elk_host, args.elk_port)

    logger.info(f"🚀 Starting AI Security Monitor on {args.host}:{args.port}")
    logger.info(f"📊 Elasticsearch: {args.elk_host}:{args.elk_port}")
    logger.info(f"🔍 MCP Integration: {'Enabled' if MCP_AVAILABLE else 'Disabled'}")

    # Run the FastAPI application
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())
