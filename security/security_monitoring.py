#!/usr/bin/env python3
"""
PAKE System - Security Monitoring & Alerting System
Comprehensive security monitoring, threat detection, and incident response.

This module provides:
- Real-time security monitoring
- Threat detection and analysis
- Automated incident response
- Security alerting and notifications
- Compliance monitoring
- Security metrics and reporting
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable

import aiohttp
from pydantic import BaseModel, Field


class ThreatLevel(Enum):
    """Threat levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Incident status"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


class SecurityEvent(BaseModel):
    """Security event model"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of security event")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_id: Optional[str] = Field(None, description="User identifier")
    resource: Optional[str] = Field(None, description="Affected resource")
    description: str = Field(..., description="Event description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    false_positive: bool = Field(default=False, description="Whether this is a false positive")


class SecurityIncident(BaseModel):
    """Security incident model"""
    incident_id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Incident description")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    status: IncidentStatus = Field(default=IncidentStatus.OPEN, description="Incident status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    assigned_to: Optional[str] = Field(None, description="Assigned analyst")
    events: List[SecurityEvent] = Field(default_factory=list, description="Related events")
    tags: List[str] = Field(default_factory=list, description="Incident tags")
    notes: List[str] = Field(default_factory=list, description="Investigation notes")
    remediation_steps: List[str] = Field(default_factory=list, description="Remediation steps")


class SecurityRule(BaseModel):
    """Security detection rule"""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    pattern: str = Field(..., description="Detection pattern")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    tags: List[str] = Field(default_factory=list, description="Rule tags")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SecurityAlert(BaseModel):
    """Security alert model"""
    alert_id: str = Field(..., description="Unique alert identifier")
    incident_id: Optional[str] = Field(None, description="Related incident ID")
    event_id: str = Field(..., description="Related event ID")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    channels: List[AlertChannel] = Field(..., description="Alert channels")
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    acknowledged: bool = Field(default=False, description="Whether alert is acknowledged")
    acknowledged_by: Optional[str] = Field(None, description="Who acknowledged the alert")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment timestamp")


class SecurityMonitoringSystem:
    """
    Enterprise Security Monitoring & Alerting System

    Provides comprehensive security monitoring, threat detection,
    and automated incident response capabilities.
    """

    def __init__(self):
        self.logger = self._setup_logger()
        self.security_events: List[SecurityEvent] = []
        self.incidents: List[SecurityIncident] = []
        self.alerts: List[SecurityAlert] = []
        self.detection_rules: List[SecurityRule] = []
        self.threat_indicators: Dict[str, List[datetime]] = {}

        # Initialize detection rules
        self._initialize_default_rules()

        # Alert handlers
        self.alert_handlers: Dict[AlertChannel, Callable] = {}
        self._setup_alert_handlers()

        # Monitoring state
        self.monitoring_active = False
        self.last_scan_time = datetime.now(UTC)

    def _setup_logger(self) -> logging.Logger:
        """Set up security monitoring logger"""
        logger = logging.getLogger("pake_security_monitoring")
        logger.setLevel(logging.INFO)

        # Create security log file
        log_dir = Path("logs/security")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "security_monitoring.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _initialize_default_rules(self):
        """Initialize default security detection rules"""
        default_rules = [
            SecurityRule(
                rule_id="brute_force_attack",
                name="Brute Force Attack Detection",
                description="Detects multiple failed login attempts from same IP",
                pattern="failed_login_attempts",
                threat_level=ThreatLevel.HIGH,
                tags=["authentication", "brute_force"]
            ),
            SecurityRule(
                rule_id="sql_injection_attempt",
                name="SQL Injection Attempt",
                description="Detects potential SQL injection patterns",
                pattern="sql_injection",
                threat_level=ThreatLevel.HIGH,
                tags=["injection", "database"]
            ),
            SecurityRule(
                rule_id="xss_attempt",
                name="XSS Attack Attempt",
                description="Detects potential XSS attack patterns",
                pattern="xss_attack",
                threat_level=ThreatLevel.MEDIUM,
                tags=["xss", "injection"]
            ),
            SecurityRule(
                rule_id="suspicious_file_access",
                name="Suspicious File Access",
                description="Detects unauthorized file access attempts",
                pattern="unauthorized_file_access",
                threat_level=ThreatLevel.MEDIUM,
                tags=["file_access", "authorization"]
            ),
            SecurityRule(
                rule_id="privilege_escalation",
                name="Privilege Escalation Attempt",
                description="Detects privilege escalation attempts",
                pattern="privilege_escalation",
                threat_level=ThreatLevel.CRITICAL,
                tags=["privilege", "escalation"]
            ),
            SecurityRule(
                rule_id="data_exfiltration",
                name="Data Exfiltration Attempt",
                description="Detects potential data exfiltration",
                pattern="data_exfiltration",
                threat_level=ThreatLevel.CRITICAL,
                tags=["data", "exfiltration"]
            ),
            SecurityRule(
                rule_id="anomalous_traffic",
                name="Anomalous Network Traffic",
                description="Detects unusual network traffic patterns",
                pattern="anomalous_traffic",
                threat_level=ThreatLevel.MEDIUM,
                tags=["network", "anomaly"]
            ),
            SecurityRule(
                rule_id="malware_signature",
                name="Malware Signature Detection",
                description="Detects known malware signatures",
                pattern="malware_signature",
                threat_level=ThreatLevel.HIGH,
                tags=["malware", "signature"]
            )
        ]

        self.detection_rules.extend(default_rules)
        self.logger.info(f"Initialized {len(default_rules)} default security rules")

    def _setup_alert_handlers(self):
        """Setup alert notification handlers"""
        self.alert_handlers[AlertChannel.EMAIL] = self._send_email_alert
        self.alert_handlers[AlertChannel.SLACK] = self._send_slack_alert
        self.alert_handlers[AlertChannel.WEBHOOK] = self._send_webhook_alert
        self.alert_handlers[AlertChannel.SMS] = self._send_sms_alert
        self.alert_handlers[AlertChannel.PAGERDUTY] = self._send_pagerduty_alert

    # ========================================================================
    # Event Processing and Detection
    # ========================================================================

    async def process_security_event(
        self,
        event_type: str,
        description: str,
        source_ip: str = None,
        user_id: str = None,
        resource: str = None,
        metadata: Dict[str, Any] = None
    ) -> SecurityEvent:
        """
        Process a security event and run detection rules

        Args:
            event_type: Type of security event
            description: Event description
            source_ip: Source IP address
            user_id: User identifier
            resource: Affected resource
            metadata: Additional metadata

        Returns:
            SecurityEvent object
        """
        # Create security event
        event = SecurityEvent(
            event_id=f"sec_{int(time.time())}_{secrets.token_hex(4)}",
            event_type=event_type,
            threat_level=ThreatLevel.LOW,  # Default, will be updated by rules
            source_ip=source_ip,
            user_id=user_id,
            resource=resource,
            description=description,
            metadata=metadata or {}
        )

        # Run detection rules
        await self._run_detection_rules(event)

        # Store event
        self.security_events.append(event)

        # Update threat indicators
        await self._update_threat_indicators(event)

        # Check for incident creation
        await self._check_incident_creation(event)

        self.logger.info(f"Processed security event: {event.event_id} - {event_type}")

        return event

    async def _run_detection_rules(self, event: SecurityEvent):
        """Run detection rules against security event"""
        for rule in self.detection_rules:
            if not rule.enabled:
                continue

            # Check if event matches rule pattern
            if await self._matches_rule_pattern(event, rule):
                # Update threat level if rule threat level is higher
                if self._get_threat_level_value(rule.threat_level) > self._get_threat_level_value(event.threat_level):
                    event.threat_level = rule.threat_level

                # Add rule metadata
                event.metadata[f"matched_rule_{rule.rule_id}"] = {
                    "rule_name": rule.name,
                    "rule_description": rule.description,
                    "matched_at": datetime.now(UTC).isoformat()
                }

                self.logger.warning(f"Event {event.event_id} matched rule {rule.rule_id}: {rule.name}")

    async def _matches_rule_pattern(self, event: SecurityEvent, rule: SecurityRule) -> bool:
        """Check if event matches rule pattern"""
        # Simple pattern matching - in production, use more sophisticated detection
        event_text = f"{event.event_type} {event.description} {event.resource or ''}"

        if rule.pattern == "failed_login_attempts":
            return await self._detect_brute_force(event)
        elif rule.pattern == "sql_injection":
            return await self._detect_sql_injection(event)
        elif rule.pattern == "xss_attack":
            return await self._detect_xss(event)
        elif rule.pattern == "unauthorized_file_access":
            return await self._detect_unauthorized_access(event)
        elif rule.pattern == "privilege_escalation":
            return await self._detect_privilege_escalation(event)
        elif rule.pattern == "data_exfiltration":
            return await self._detect_data_exfiltration(event)
        elif rule.pattern == "anomalous_traffic":
            return await self._detect_anomalous_traffic(event)
        elif rule.pattern == "malware_signature":
            return await self._detect_malware_signature(event)

        return False

    async def _detect_brute_force(self, event: SecurityEvent) -> bool:
        """Detect brute force attack patterns"""
        if event.event_type != "failed_login":
            return False

        # Check for multiple failed attempts from same IP
        if event.source_ip:
            recent_events = [
                e for e in self.security_events[-100:]  # Last 100 events
                if e.event_type == "failed_login"
                and e.source_ip == event.source_ip
                and (datetime.now(UTC) - e.timestamp).total_seconds() < 300  # 5 minutes
            ]

            if len(recent_events) >= 5:  # 5 or more failed attempts
                event.threat_level = ThreatLevel.HIGH
                event.metadata["brute_force_detected"] = {
                    "failed_attempts": len(recent_events),
                    "time_window": "5 minutes"
                }
                return True

        return False

    async def _detect_sql_injection(self, event: SecurityEvent) -> bool:
        """Detect SQL injection patterns"""
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|\#|\/\*|\*\/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"].*['\"]\s*=\s*['\"].*['\"])",
            r"(UNION\s+SELECT)",
            r"(DROP\s+TABLE)",
            r"(INSERT\s+INTO)",
            r"(UPDATE\s+SET)",
            r"(DELETE\s+FROM)"
        ]

        event_text = f"{event.description} {event.resource or ''}"

        for pattern in sql_patterns:
            if re.search(pattern, event_text, re.IGNORECASE):
                event.metadata["sql_injection_detected"] = {
                    "matched_pattern": pattern,
                    "event_text": event_text
                }
                return True

        return False

    async def _detect_xss(self, event: SecurityEvent) -> bool:
        """Detect XSS attack patterns"""
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
            r"eval\s*\(",
            r"document\.cookie",
            r"document\.write",
            r"innerHTML\s*="
        ]

        event_text = f"{event.description} {event.resource or ''}"

        for pattern in xss_patterns:
            if re.search(pattern, event_text, re.IGNORECASE):
                event.metadata["xss_detected"] = {
                    "matched_pattern": pattern,
                    "event_text": event_text
                }
                return True

        return False

    async def _detect_unauthorized_access(self, event: SecurityEvent) -> bool:
        """Detect unauthorized file access"""
        if event.event_type == "file_access":
            # Check if access was denied or unauthorized
            if "unauthorized" in event.description.lower() or "denied" in event.description.lower():
                event.metadata["unauthorized_access_detected"] = {
                    "access_type": "file_access",
                    "resource": event.resource
                }
                return True

        return False

    async def _detect_privilege_escalation(self, event: SecurityEvent) -> bool:
        """Detect privilege escalation attempts"""
        escalation_patterns = [
            r"sudo\s+su",
            r"su\s+-",
            r"chmod\s+777",
            r"chown\s+root",
            r"privilege\s+escalation",
            r"elevate\s+privileges"
        ]

        event_text = f"{event.description} {event.resource or ''}"

        for pattern in escalation_patterns:
            if re.search(pattern, event_text, re.IGNORECASE):
                event.metadata["privilege_escalation_detected"] = {
                    "matched_pattern": pattern,
                    "event_text": event_text
                }
                return True

        return False

    async def _detect_data_exfiltration(self, event: SecurityEvent) -> bool:
        """Detect data exfiltration attempts"""
        exfiltration_indicators = [
            "large_data_transfer",
            "unusual_data_access",
            "bulk_download",
            "data_export",
            "file_copy_outbound"
        ]

        event_text = f"{event.description} {event.resource or ''}"

        for indicator in exfiltration_indicators:
            if indicator in event_text.lower():
                event.metadata["data_exfiltration_detected"] = {
                    "indicator": indicator,
                    "event_text": event_text
                }
                return True

        return False

    async def _detect_anomalous_traffic(self, event: SecurityEvent) -> bool:
        """Detect anomalous network traffic"""
        if event.event_type == "network_traffic":
            # Check for unusual patterns (simplified)
            metadata = event.metadata

            # High bandwidth usage
            if metadata.get("bandwidth_mbps", 0) > 1000:  # 1 Gbps
                event.metadata["anomalous_traffic_detected"] = {
                    "reason": "high_bandwidth",
                    "bandwidth_mbps": metadata.get("bandwidth_mbps")
                }
                return True

            # Unusual destination
            if metadata.get("destination_country") not in ["US", "CA", "GB"]:
                event.metadata["anomalous_traffic_detected"] = {
                    "reason": "unusual_destination",
                    "destination_country": metadata.get("destination_country")
                }
                return True

        return False

    async def _detect_malware_signature(self, event: SecurityEvent) -> bool:
        """Detect malware signatures"""
        malware_signatures = [
            "trojan",
            "virus",
            "malware",
            "ransomware",
            "backdoor",
            "rootkit",
            "keylogger",
            "botnet"
        ]

        event_text = f"{event.description} {event.resource or ''}"

        for signature in malware_signatures:
            if signature in event_text.lower():
                event.metadata["malware_signature_detected"] = {
                    "signature": signature,
                    "event_text": event_text
                }
                return True

        return False

    # ========================================================================
    # Threat Intelligence and Correlation
    # ========================================================================

    async def _update_threat_indicators(self, event: SecurityEvent):
        """Update threat indicators for correlation"""
        if event.source_ip:
            if event.source_ip not in self.threat_indicators:
                self.threat_indicators[event.source_ip] = []

            self.threat_indicators[event.source_ip].append(event.timestamp)

            # Keep only recent indicators (last 24 hours)
            cutoff_time = datetime.now(UTC) - timedelta(hours=24)
            self.threat_indicators[event.source_ip] = [
                ts for ts in self.threat_indicators[event.source_ip]
                if ts > cutoff_time
            ]

    async def _check_incident_creation(self, event: SecurityEvent):
        """Check if event should trigger incident creation"""
        # Create incident for high/critical threat events
        if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            # Check if there's already an open incident for this threat
            existing_incident = await self._find_related_incident(event)

            if not existing_incident:
                # Create new incident
                incident = await self._create_incident(event)
                await self._send_incident_alerts(incident)
            else:
                # Add event to existing incident
                existing_incident.events.append(event)
                existing_incident.updated_at = datetime.now(UTC)

                # Update incident threat level if needed
                if self._get_threat_level_value(event.threat_level) > self._get_threat_level_value(existing_incident.threat_level):
                    existing_incident.threat_level = event.threat_level
                    await self._send_incident_update_alerts(existing_incident)

    async def _find_related_incident(self, event: SecurityEvent) -> Optional[SecurityIncident]:
        """Find related incident for event"""
        for incident in self.incidents:
            if incident.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]:
                # Check if event is related (same IP, user, or resource)
                for incident_event in incident.events:
                    if (event.source_ip and incident_event.source_ip == event.source_ip) or \
                       (event.user_id and incident_event.user_id == event.user_id) or \
                       (event.resource and incident_event.resource == event.resource):
                        return incident

        return None

    async def _create_incident(self, event: SecurityEvent) -> SecurityIncident:
        """Create new security incident"""
        incident = SecurityIncident(
            incident_id=f"inc_{int(time.time())}_{secrets.token_hex(4)}",
            title=f"Security Incident: {event.event_type}",
            description=f"Security incident triggered by {event.event_type} event",
            threat_level=event.threat_level,
            events=[event],
            tags=[event.event_type]
        )

        self.incidents.append(incident)
        self.logger.warning(f"Created security incident: {incident.incident_id}")

        return incident

    # ========================================================================
    # Alerting and Notifications
    # ========================================================================

    async def _send_incident_alerts(self, incident: SecurityIncident):
        """Send alerts for new incident"""
        alert_channels = self._get_alert_channels_for_threat_level(incident.threat_level)

        alert = SecurityAlert(
            alert_id=f"alert_{int(time.time())}_{secrets.token_hex(4)}",
            incident_id=incident.incident_id,
            event_id=incident.events[0].event_id,
            title=f"Security Incident Alert: {incident.title}",
            message=f"New security incident detected: {incident.description}",
            threat_level=incident.threat_level,
            channels=alert_channels
        )

        self.alerts.append(alert)

        # Send alerts to all channels
        for channel in alert_channels:
            try:
                await self.alert_handlers[channel](alert)
            except Exception as e:
                self.logger.error(f"Failed to send alert to {channel}: {str(e)}")

    async def _send_incident_update_alerts(self, incident: SecurityIncident):
        """Send alerts for incident updates"""
        alert_channels = self._get_alert_channels_for_threat_level(incident.threat_level)

        alert = SecurityAlert(
            alert_id=f"alert_{int(time.time())}_{secrets.token_hex(4)}",
            incident_id=incident.incident_id,
            event_id=incident.events[-1].event_id,
            title=f"Security Incident Update: {incident.title}",
            message=f"Security incident updated: {incident.description}",
            threat_level=incident.threat_level,
            channels=alert_channels
        )

        self.alerts.append(alert)

        # Send alerts to all channels
        for channel in alert_channels:
            try:
                await self.alert_handlers[channel](alert)
            except Exception as e:
                self.logger.error(f"Failed to send alert to {channel}: {str(e)}")

    def _get_alert_channels_for_threat_level(self, threat_level: ThreatLevel) -> List[AlertChannel]:
        """Get alert channels based on threat level"""
        if threat_level == ThreatLevel.CRITICAL:
            return [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.PAGERDUTY]
        elif threat_level == ThreatLevel.HIGH:
            return [AlertChannel.EMAIL, AlertChannel.SLACK]
        elif threat_level == ThreatLevel.MEDIUM:
            return [AlertChannel.EMAIL]
        else:
            return [AlertChannel.EMAIL]

    async def _send_email_alert(self, alert: SecurityAlert):
        """Send email alert"""
        # In production, integrate with email service (SendGrid, SES, etc.)
        self.logger.info(f"Email alert sent: {alert.title}")

    async def _send_slack_alert(self, alert: SecurityAlert):
        """Send Slack alert"""
        # In production, integrate with Slack API
        self.logger.info(f"Slack alert sent: {alert.title}")

    async def _send_webhook_alert(self, alert: SecurityAlert):
        """Send webhook alert"""
        # In production, send to configured webhook URL
        self.logger.info(f"Webhook alert sent: {alert.title}")

    async def _send_sms_alert(self, alert: SecurityAlert):
        """Send SMS alert"""
        # In production, integrate with SMS service (Twilio, etc.)
        self.logger.info(f"SMS alert sent: {alert.title}")

    async def _send_pagerduty_alert(self, alert: SecurityAlert):
        """Send PagerDuty alert"""
        # In production, integrate with PagerDuty API
        self.logger.info(f"PagerDuty alert sent: {alert.title}")

    # ========================================================================
    # Incident Management
    # ========================================================================

    async def update_incident_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        assigned_to: str = None,
        notes: str = None
    ) -> bool:
        """Update incident status"""
        incident = await self._get_incident_by_id(incident_id)
        if not incident:
            return False

        incident.status = status
        incident.updated_at = datetime.now(UTC)

        if assigned_to:
            incident.assigned_to = assigned_to

        if notes:
            incident.notes.append(f"{datetime.now(UTC).isoformat()}: {notes}")

        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now(UTC)

        self.logger.info(f"Updated incident {incident_id} status to {status.value}")
        return True

    async def _get_incident_by_id(self, incident_id: str) -> Optional[SecurityIncident]:
        """Get incident by ID"""
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                return incident
        return None

    async def get_open_incidents(self) -> List[SecurityIncident]:
        """Get all open incidents"""
        return [
            incident for incident in self.incidents
            if incident.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]
        ]

    async def get_incident_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get incident metrics"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Filter incidents by date range
        recent_incidents = [
            incident for incident in self.incidents
            if start_date <= incident.created_at <= end_date
        ]

        # Calculate metrics
        total_incidents = len(recent_incidents)
        resolved_incidents = len([i for i in recent_incidents if i.status == IncidentStatus.RESOLVED])
        open_incidents = len([i for i in recent_incidents if i.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]])

        # Threat level breakdown
        threat_level_counts = {}
        for incident in recent_incidents:
            level = incident.threat_level.value
            threat_level_counts[level] = threat_level_counts.get(level, 0) + 1

        # Average resolution time
        resolved_with_time = [i for i in recent_incidents if i.resolved_at]
        avg_resolution_time = None
        if resolved_with_time:
            resolution_times = [
                (i.resolved_at - i.created_at).total_seconds() / 3600  # hours
                for i in resolved_with_time
            ]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_incidents": total_incidents,
                "resolved_incidents": resolved_incidents,
                "open_incidents": open_incidents,
                "resolution_rate": resolved_incidents / total_incidents if total_incidents > 0 else 0,
                "avg_resolution_time_hours": avg_resolution_time
            },
            "threat_level_breakdown": threat_level_counts,
            "top_event_types": self._get_top_event_types(recent_incidents),
            "top_source_ips": self._get_top_source_ips(recent_incidents)
        }

    def _get_top_event_types(self, incidents: List[SecurityIncident]) -> Dict[str, int]:
        """Get top event types from incidents"""
        event_type_counts = {}
        for incident in incidents:
            for event in incident.events:
                event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1

        return dict(sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    def _get_top_source_ips(self, incidents: List[SecurityIncident]) -> Dict[str, int]:
        """Get top source IPs from incidents"""
        ip_counts = {}
        for incident in incidents:
            for event in incident.events:
                if event.source_ip:
                    ip_counts[event.source_ip] = ip_counts.get(event.source_ip, 0) + 1

        return dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _get_threat_level_value(self, threat_level: ThreatLevel) -> int:
        """Get numeric value for threat level comparison"""
        threat_values = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4
        }
        return threat_values[threat_level]

    async def generate_security_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Filter events by date range
        recent_events = [
            event for event in self.security_events
            if start_date <= event.timestamp <= end_date
        ]

        # Filter incidents by date range
        recent_incidents = [
            incident for incident in self.incidents
            if start_date <= incident.created_at <= end_date
        ]

        # Calculate statistics
        total_events = len(recent_events)
        critical_events = len([e for e in recent_events if e.threat_level == ThreatLevel.CRITICAL])
        high_events = len([e for e in recent_events if e.threat_level == ThreatLevel.HIGH])

        # Get incident metrics
        incident_metrics = await self.get_incident_metrics(days)

        report = {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_security_events": total_events,
                "critical_events": critical_events,
                "high_events": high_events,
                "total_incidents": len(recent_incidents),
                "open_incidents": len([i for i in recent_incidents if i.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]])
            },
            "incident_metrics": incident_metrics,
            "top_threats": self._get_top_event_types(recent_incidents),
            "recommendations": await self._generate_security_recommendations(recent_events, recent_incidents)
        }

        return report

    async def _generate_security_recommendations(
        self,
        events: List[SecurityEvent],
        incidents: List[SecurityIncident]
    ) -> List[str]:
        """Generate security recommendations"""
        recommendations = []

        # Check for high number of critical events
        critical_events = [e for e in events if e.threat_level == ThreatLevel.CRITICAL]
        if len(critical_events) > 5:
            recommendations.append("High number of critical security events detected - review security controls")

        # Check for unresolved incidents
        open_incidents = [i for i in incidents if i.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]]
        if len(open_incidents) > 3:
            recommendations.append("Multiple unresolved security incidents - prioritize incident response")

        # Check for repeated source IPs
        source_ips = [e.source_ip for e in events if e.source_ip]
        if source_ips:
            ip_counts = {}
            for ip in source_ips:
                ip_counts[ip] = ip_counts.get(ip, 0) + 1

            suspicious_ips = [ip for ip, count in ip_counts.items() if count > 10]
            if suspicious_ips:
                recommendations.append(f"Consider blocking suspicious IP addresses: {suspicious_ips}")

        return recommendations


if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize security monitoring system
        security_monitor = SecurityMonitoringSystem()

        # Process some security events
        await security_monitor.process_security_event(
            event_type="failed_login",
            description="Failed login attempt for user admin",
            source_ip="192.168.1.100",
            user_id="admin"
        )

        # Generate security report
        report = await security_monitor.generate_security_report()
        print(f"Security report: {report['summary']}")

    asyncio.run(main())
