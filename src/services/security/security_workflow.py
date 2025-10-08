#!/usr/bin/env python3
"""PAKE System - Security Workflow and Triage System (Phase 3 Architectural Health)
Comprehensive workflow for triaging, prioritizing, and remediating security findings.

This module provides:
1. Vulnerability triage and prioritization
2. Remediation tracking and assignment
3. Security workflow automation
4. Compliance reporting and auditing
5. Integration with development workflow
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any

import requests
import yaml

logger = logging.getLogger(__name__)


class VulnerabilityPriority(Enum):
    """Vulnerability priority levels."""

    P0_CRITICAL = "P0"  # Immediate action required
    P1_HIGH = "P1"  # Action within 24 hours
    P2_MEDIUM = "P2"  # Action within 1 week
    P3_LOW = "P3"  # Action within 1 month
    P4_INFO = "P4"  # Informational only


class RemediationStatus(Enum):
    """Remediation status."""

    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"
    DEFERRED = "deferred"


class WorkflowStage(Enum):
    """Security workflow stages."""

    DISCOVERY = "discovery"
    TRIAGE = "triage"
    ASSIGNMENT = "assignment"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"
    CLOSURE = "closure"


@dataclass
class SecurityFinding:
    """Security finding with triage information."""

    finding_id: str
    vulnerability_id: str
    title: str
    description: str
    severity: str
    priority: VulnerabilityPriority
    status: RemediationStatus
    workflow_stage: WorkflowStage
    discovered_date: datetime
    assigned_to: str | None = None
    assigned_date: datetime | None = None
    due_date: datetime | None = None
    remediation_notes: list[str] = field(default_factory=list)
    verification_notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    business_impact: str = ""
    technical_details: dict[str, Any] = field(default_factory=dict)
    remediation_effort_hours: int | None = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SecurityWorkflowRule:
    """Rule for automated security workflow."""

    rule_id: str
    name: str
    description: str
    conditions: dict[str, Any]
    actions: list[dict[str, Any]]
    enabled: bool = True
    priority: int = 0


@dataclass
class SecurityMetrics:
    """Security metrics and KPIs."""

    total_findings: int = 0
    open_findings: int = 0
    resolved_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    avg_remediation_time_hours: float = 0.0
    sla_compliance_rate: float = 0.0
    false_positive_rate: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


class SecurityTriageSystem:
    """System for triaging and managing security findings."""

    def __init__(self, config_file: str = "security_triage_config.yaml") -> None:
        self.config_file = config_file
        self.config = self._load_config()
        self.findings: list[SecurityFinding] = []
        self.workflow_rules: list[SecurityWorkflowRule] = []
        self.metrics = SecurityMetrics()
        self._load_existing_data()
        self._initialize_workflow_rules()

    def _load_config(self) -> dict[str, Any]:
        """Load triage system configuration."""
        default_config = {
            "priorities": {
                "critical": {
                    "priority": "P0",
                    "sla_hours": 4,
                    "auto_assign": True,
                    "notification_channels": ["slack", "email", "sms"],
                },
                "high": {
                    "priority": "P1",
                    "sla_hours": 24,
                    "auto_assign": True,
                    "notification_channels": ["slack", "email"],
                },
                "medium": {
                    "priority": "P2",
                    "sla_hours": 168,  # 1 week
                    "auto_assign": False,
                    "notification_channels": ["slack"],
                },
                "low": {
                    "priority": "P3",
                    "sla_hours": 720,  # 1 month
                    "auto_assign": False,
                    "notification_channels": [],
                },
                "informational": {
                    "priority": "P4",
                    "sla_hours": 0,
                    "auto_assign": False,
                    "notification_channels": [],
                },
            },
            "assignments": {
                "default_assignee": "security-team",
                "escalation_rules": {
                    "overdue_hours": 24,
                    "escalation_chain": ["security-team", "security-lead", "cto"],
                },
            },
            "notifications": {
                "slack": {
                    "enabled": True,
                    "webhook_url": None,
                    "channels": ["#security-alerts"],
                },
                "email": {"enabled": True, "smtp_server": None, "recipients": []},
            },
            "workflow": {
                "auto_triage": True,
                "auto_assignment": True,
                "escalation_enabled": True,
                "sla_tracking": True,
            },
        }

        if Path(self.config_file).exists():
            try:
                with open(self.config_file) as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Could not load config file %s: %s", self.config_file, e)

        return default_config

    def _load_existing_data(self) -> None:
        """Load existing findings and data."""
        data_file = Path("security_findings.json")
        if data_file.exists():
            try:
                with open(data_file) as f:
                    data = json.load(f)
                    for finding_data in data.get("findings", []):
                        finding = SecurityFinding(**finding_data)
                        self.findings.append(finding)
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Could not load existing findings: %s", e)

    def _save_data(self) -> None:
        """Save findings and data to file."""
        try:
            data = {
                "findings": [
                    {
                        "finding_id": f.finding_id,
                        "vulnerability_id": f.vulnerability_id,
                        "title": f.title,
                        "description": f.description,
                        "severity": f.severity,
                        "priority": f.priority.value,
                        "status": f.status.value,
                        "workflow_stage": f.workflow_stage.value,
                        "discovered_date": f.discovered_date.isoformat(),
                        "assigned_to": f.assigned_to,
                        "assigned_date": f.assigned_date.isoformat()
                        if f.assigned_date
                        else None,
                        "due_date": f.due_date.isoformat() if f.due_date else None,
                        "remediation_notes": f.remediation_notes,
                        "verification_notes": f.verification_notes,
                        "tags": f.tags,
                        "affected_components": f.affected_components,
                        "business_impact": f.business_impact,
                        "technical_details": f.technical_details,
                        "remediation_effort_hours": f.remediation_effort_hours,
                        "last_updated": f.last_updated.isoformat(),
                    }
                    for f in self.findings
                ]
            }

            with open("security_findings.json", "w") as f:
                json.dump(data, f, indent=2)

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Error saving findings data: %s", e)

    def _initialize_workflow_rules(self) -> None:
        """Initialize automated workflow rules."""
        self.workflow_rules = [
            SecurityWorkflowRule(
                rule_id="auto_triage_critical",
                name="Auto-triage Critical Vulnerabilities",
                description="Automatically assign P0 priority to critical vulnerabilities",
                conditions={"severity": "critical", "workflow_stage": "discovery"},
                actions=[
                    {"type": "set_priority", "value": "P0"},
                    {"type": "set_status", "value": "assigned"},
                    {"type": "auto_assign"},
                    {"type": "notify", "channels": ["slack", "email"]},
                ],
                priority=1,
            ),
            SecurityWorkflowRule(
                rule_id="auto_triage_high",
                name="Auto-triage High Vulnerabilities",
                description="Automatically assign P1 priority to high vulnerabilities",
                conditions={"severity": "high", "workflow_stage": "discovery"},
                actions=[
                    {"type": "set_priority", "value": "P1"},
                    {"type": "set_status", "value": "assigned"},
                    {"type": "auto_assign"},
                    {"type": "notify", "channels": ["slack"]},
                ],
                priority=2,
            ),
            SecurityWorkflowRule(
                rule_id="escalation_overdue",
                name="Escalate Overdue Findings",
                description="Escalate findings that are overdue",
                conditions={"status": ["assigned", "in_progress"], "overdue": True},
                actions=[
                    {"type": "escalate"},
                    {"type": "notify", "channels": ["slack", "email"]},
                    {"type": "update_priority", "value": "increase"},
                ],
                priority=3,
            ),
            SecurityWorkflowRule(
                rule_id="auto_close_false_positive",
                name="Auto-close False Positives",
                description="Automatically close findings marked as false positives",
                conditions={"status": "false_positive", "workflow_stage": "triage"},
                actions=[
                    {"type": "set_status", "value": "resolved"},
                    {"type": "set_workflow_stage", "value": "closure"},
                    {
                        "type": "add_note",
                        "value": "Automatically closed as false positive",
                    },
                ],
                priority=4,
            ),
        ]

    def add_finding(self, finding: SecurityFinding) -> None:
        """Add new security finding."""
        self.findings.append(finding)

        # Apply automated workflow rules
        if self.config["workflow"]["auto_triage"]:
            self._apply_workflow_rules(finding)

        self._update_metrics()
        self._save_data()

        logger.info("Added security finding: %s", finding.finding_id)

    def _apply_workflow_rules(self, finding: SecurityFinding) -> None:
        """Apply automated workflow rules to finding."""
        for rule in sorted(self.workflow_rules, key=lambda r: r.priority):
            if not rule.enabled:
                continue

            if self._rule_matches(rule, finding):
                self._execute_rule_actions(rule, finding)

    def _rule_matches(
        self, rule: SecurityWorkflowRule, finding: SecurityFinding
    ) -> bool:
        """Check if workflow rule matches finding."""
        conditions = rule.conditions

        # Check severity condition
        if "severity" in conditions:
            if finding.severity != conditions["severity"]:
                return False

        # Check workflow stage condition
        if "workflow_stage" in conditions:
            if finding.workflow_stage.value != conditions["workflow_stage"]:
                return False

        # Check status condition
        if "status" in conditions:
            if isinstance(conditions["status"], list):
                if finding.status.value not in conditions["status"]:
                    return False
            else:
                if finding.status.value != conditions["status"]:
                    return False

        # Check overdue condition
        if conditions.get("overdue", False):
            if not self._is_finding_overdue(finding):
                return False

        return True

    def _execute_rule_actions(
        self, rule: SecurityWorkflowRule, finding: SecurityFinding
    ) -> None:
        """Execute workflow rule actions."""
        for action in rule.actions:
            action_type = action["type"]

            if action_type == "set_priority":
                priority_value = action["value"]
                finding.priority = VulnerabilityPriority(priority_value)
                finding.last_updated = datetime.now(UTC)

            elif action_type == "set_status":
                status_value = action["value"]
                finding.status = RemediationStatus(status_value)
                finding.last_updated = datetime.now(UTC)

            elif action_type == "set_workflow_stage":
                stage_value = action["value"]
                finding.workflow_stage = WorkflowStage(stage_value)
                finding.last_updated = datetime.now(UTC)

            elif action_type == "auto_assign":
                self._auto_assign_finding(finding)

            elif action_type == "notify":
                channels = action.get("channels", [])
                self._send_notifications(finding, channels)

            elif action_type == "escalate":
                self._escalate_finding(finding)

            elif action_type == "add_note":
                note = action["value"]
                finding.remediation_notes.append(
                    f"{datetime.now(UTC).isoformat()}: {note}"
                )

        logger.info(
            "Applied workflow rule '%s' to finding %s", rule.name, finding.finding_id
        )

    def _auto_assign_finding(self, finding: SecurityFinding) -> None:
        """Automatically assign finding."""
        if finding.assigned_to:
            return  # Already assigned

        default_assignee = self.config["assignments"]["default_assignee"]
        finding.assigned_to = default_assignee
        finding.assigned_date = datetime.now(UTC)

        # Set due date based on priority
        priority_config = self.config["priorities"].get(finding.severity, {})
        sla_hours = priority_config.get("sla_hours", 24)
        finding.due_date = datetime.now(UTC) + timedelta(hours=sla_hours)

        logger.info(
            "Auto-assigned finding %s to %s", finding.finding_id, default_assignee
        )

    def _is_finding_overdue(self, finding: SecurityFinding) -> bool:
        """Check if finding is overdue."""
        if not finding.due_date:
            return False

        return datetime.now(UTC) > finding.due_date

    def _escalate_finding(self, finding: SecurityFinding) -> None:
        """Escalate finding."""
        escalation_chain = self.config["assignments"]["escalation_rules"][
            "escalation_chain"
        ]

        # Find current assignee in escalation chain
        current_index = 0
        if finding.assigned_to in escalation_chain:
            current_index = escalation_chain.index(finding.assigned_to)

        # Move to next level
        if current_index < len(escalation_chain) - 1:
            finding.assigned_to = escalation_chain[current_index + 1]
            finding.assigned_date = datetime.now(UTC)

            # Extend due date
            finding.due_date = datetime.now(UTC) + timedelta(hours=24)

            logger.info(
                "Escalated finding %s to %s", finding.finding_id, finding.assigned_to
            )

    def _send_notifications(
        self, finding: SecurityFinding, channels: list[str]
    ) -> None:
        """Send notifications for finding."""
        message = self._format_notification_message(finding)

        for channel in channels:
            if channel == "slack" and self.config["notifications"]["slack"]["enabled"]:
                self._send_slack_notification(message, finding)
            elif (
                channel == "email" and self.config["notifications"]["email"]["enabled"]
            ):
                self._send_email_notification(message, finding)

    def _format_notification_message(self, finding: SecurityFinding) -> str:
        """Format notification message."""
        return f"""
🔒 **Security Finding Alert**

**Finding ID:** {finding.finding_id}
**Title:** {finding.title}
**Severity:** {finding.severity.upper()}
**Priority:** {finding.priority.value}
**Status:** {finding.status.value}
**Assigned To:** {finding.assigned_to or "Unassigned"}
**Due Date:** {finding.due_date.strftime("%Y-%m-%d %H:%M") if finding.due_date else "Not set"}

**Description:**
{finding.description}

**Affected Components:**
{", ".join(finding.affected_components) if finding.affected_components else "Not specified"}

**Business Impact:**
{finding.business_impact if finding.business_impact else "Not assessed"}

---
*This is an automated notification from the PAKE System Security Workflow*
"""

    def _send_slack_notification(self, message: str, finding: SecurityFinding) -> None:
        """Send Slack notification."""
        try:
            webhook_url = self.config["notifications"]["slack"]["webhook_url"]
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return

            color = (
                "danger"
                if finding.priority
                in [VulnerabilityPriority.P0_CRITICAL, VulnerabilityPriority.P1_HIGH]
                else "warning"
            )

            payload = {
                "text": "🔒 Security Finding Alert",
                "attachments": [
                    {"color": color, "text": message, "mrkdwn_in": ["text"]}
                ],
            }

            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                logger.info(
                    "Sent Slack notification for finding %s", finding.finding_id
                )
            else:
                logger.error(
                    "Failed to send Slack notification: %s", response.status_code
                )

        except (ValueError, RuntimeError) as e:
            logger.error("Error sending Slack notification: %s", e)

    def _send_email_notification(self, message: str, finding: SecurityFinding) -> None:
        """Send email notification."""
        try:
            recipients = self.config["notifications"]["email"]["recipients"]
            if not recipients:
                logger.warning("Email recipients not configured")
                return

            # This would be implemented with actual email service
            logger.info("Email notification would be sent to: %s", recipients)
            logger.info("Subject: Security Finding Alert - %s", finding.finding_id)
            logger.info("Message: %s", message)

        except (ValueError, RuntimeError) as e:
            logger.error("Error sending email notification: %s", e)

    def _update_metrics(self) -> None:
        """Update security metrics."""
        self.metrics.total_findings = len(self.findings)
        self.metrics.open_findings = len(
            [f for f in self.findings if f.status != RemediationStatus.RESOLVED]
        )
        self.metrics.resolved_findings = len(
            [f for f in self.findings if f.status == RemediationStatus.RESOLVED]
        )

        # Count by severity
        severity_counts = {}
        for finding in self.findings:
            severity = finding.severity.lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        self.metrics.critical_findings = severity_counts.get("critical", 0)
        self.metrics.high_findings = severity_counts.get("high", 0)
        self.metrics.medium_findings = severity_counts.get("medium", 0)
        self.metrics.low_findings = severity_counts.get("low", 0)

        # Calculate SLA compliance
        total_with_sla = len([f for f in self.findings if f.due_date])
        compliant_findings = len(
            [
                f
                for f in self.findings
                if f.due_date
                and f.status == RemediationStatus.RESOLVED
                and f.last_updated <= f.due_date
            ]
        )

        if total_with_sla > 0:
            self.metrics.sla_compliance_rate = (
                compliant_findings / total_with_sla
            ) * 100

        # Calculate false positive rate
        total_resolved = len(
            [f for f in self.findings if f.status == RemediationStatus.RESOLVED]
        )
        false_positives = len(
            [f for f in self.findings if f.status == RemediationStatus.FALSE_POSITIVE]
        )

        if total_resolved > 0:
            self.metrics.false_positive_rate = (false_positives / total_resolved) * 100

        self.metrics.last_updated = datetime.now(UTC)

    def get_findings_by_status(
        self, status: RemediationStatus
    ) -> list[SecurityFinding]:
        """Get findings by status."""
        return [f for f in self.findings if f.status == status]

    def get_findings_by_priority(
        self, priority: VulnerabilityPriority
    ) -> list[SecurityFinding]:
        """Get findings by priority."""
        return [f for f in self.findings if f.priority == priority]

    def get_overdue_findings(self) -> list[SecurityFinding]:
        """Get overdue findings."""
        return [f for f in self.findings if self._is_finding_overdue(f)]

    def update_finding_status(
        self, finding_id: str, status: RemediationStatus, notes: str | None = None
    ) -> bool:
        """Update finding status."""
        finding = next((f for f in self.findings if f.finding_id == finding_id), None)

        if finding:
            finding.status = status
            finding.last_updated = datetime.now(UTC)

            if notes:
                finding.remediation_notes.append(
                    f"{datetime.now(UTC).isoformat()}: {notes}"
                )

            # Update workflow stage based on status
            if status == RemediationStatus.RESOLVED:
                finding.workflow_stage = WorkflowStage.CLOSURE
            elif status == RemediationStatus.IN_PROGRESS:
                finding.workflow_stage = WorkflowStage.REMEDIATION

            self._update_metrics()
            self._save_data()

            logger.info("Updated finding %s status to %s", finding_id, status.value)
            return True

        return False

    def generate_security_report(self) -> str:
        """Generate comprehensive security report."""
        report = f"""
# PAKE System Security Report

**Generated:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")} UTC

## Executive Summary

- **Total Findings:** {self.metrics.total_findings}
- **Open Findings:** {self.metrics.open_findings}
- **Resolved Findings:** {self.metrics.resolved_findings}
- **SLA Compliance Rate:** {self.metrics.sla_compliance_rate:.1f}%
- **False Positive Rate:** {self.metrics.false_positive_rate:.1f}%

## Vulnerability Breakdown

| Severity | Count | Percentage |
|----------|-------|------------|
| Critical | {self.metrics.critical_findings} | {(self.metrics.critical_findings / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| High | {self.metrics.high_findings} | {(self.metrics.high_findings / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| Medium | {self.metrics.medium_findings} | {(self.metrics.medium_findings / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| Low | {self.metrics.low_findings} | {(self.metrics.low_findings / max(self.metrics.total_findings, 1)) * 100:.1f}% |

## Priority Distribution

| Priority | Count | Percentage |
|----------|-------|------------|
| P0 (Critical) | {len(self.get_findings_by_priority(VulnerabilityPriority.P0_CRITICAL))} | {(len(self.get_findings_by_priority(VulnerabilityPriority.P0_CRITICAL)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| P1 (High) | {len(self.get_findings_by_priority(VulnerabilityPriority.P1_HIGH))} | {(len(self.get_findings_by_priority(VulnerabilityPriority.P1_HIGH)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| P2 (Medium) | {len(self.get_findings_by_priority(VulnerabilityPriority.P2_MEDIUM))} | {(len(self.get_findings_by_priority(VulnerabilityPriority.P2_MEDIUM)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| P3 (Low) | {len(self.get_findings_by_priority(VulnerabilityPriority.P3_LOW))} | {(len(self.get_findings_by_priority(VulnerabilityPriority.P3_LOW)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |

## Status Distribution

| Status | Count | Percentage |
|--------|-------|------------|
| New | {len(self.get_findings_by_status(RemediationStatus.NEW))} | {(len(self.get_findings_by_status(RemediationStatus.NEW)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| Assigned | {len(self.get_findings_by_status(RemediationStatus.ASSIGNED))} | {(len(self.get_findings_by_status(RemediationStatus.ASSIGNED)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| In Progress | {len(self.get_findings_by_status(RemediationStatus.IN_PROGRESS))} | {(len(self.get_findings_by_status(RemediationStatus.IN_PROGRESS)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |
| Resolved | {len(self.get_findings_by_status(RemediationStatus.RESOLVED))} | {(len(self.get_findings_by_status(RemediationStatus.RESOLVED)) / max(self.metrics.total_findings, 1)) * 100:.1f}% |

## Overdue Findings

"""

        overdue_findings = self.get_overdue_findings()
        if overdue_findings:
            report += f"**{len(overdue_findings)} findings are overdue:**\n\n"
            for finding in overdue_findings:
                report += f"- **{finding.finding_id}**: {finding.title} (Assigned to: {finding.assigned_to})\n"
        else:
            report += "✅ No overdue findings\n"

        report += """

## Recommendations

"""

        if self.metrics.critical_findings > 0:
            report += "- **URGENT**: Address critical vulnerabilities immediately\n"

        if self.metrics.high_findings > 0:
            report += "- **HIGH PRIORITY**: Address high severity vulnerabilities within 24 hours\n"

        if len(overdue_findings) > 0:
            report += "- **OVERDUE**: Review and escalate overdue findings\n"

        if self.metrics.sla_compliance_rate < 90:
            report += "- **SLA COMPLIANCE**: Improve SLA compliance rate\n"

        if self.metrics.false_positive_rate > 20:
            report += "- **FALSE POSITIVES**: Review scanning configuration to reduce false positives\n"

        report += "- Implement additional security controls\n"
        report += "- Schedule regular security reviews\n"
        report += "- Update security training for development team\n"

        return report


# Global triage system instance
triage_system: SecurityTriageSystem | None = None


def initialize_triage_system(config_file: str | None = None) -> SecurityTriageSystem:
    """Initialize the security triage system."""
    global triage_system

    if not triage_system:
        config_file = config_file or "security_triage_config.yaml"
        triage_system = SecurityTriageSystem(config_file)
        logger.info("Security triage system initialized")

    return triage_system


def create_sample_findings() -> None:
    """Create sample security findings for testing."""
    triage = initialize_triage_system()

    sample_findings = [
        SecurityFinding(
            finding_id="FIND-001",
            vulnerability_id="SQL-INJ-001",
            title="SQL Injection in User Authentication",
            description="SQL injection vulnerability found in user authentication endpoint",
            severity="critical",
            priority=VulnerabilityPriority.P0_CRITICAL,
            status=RemediationStatus.NEW,
            workflow_stage=WorkflowStage.DISCOVERY,
            discovered_date=datetime.now(UTC),
            affected_components=["auth-service", "user-api"],
            business_impact="Complete system compromise possible",
            remediation_effort_hours=8,
        ),
        SecurityFinding(
            finding_id="FIND-002",
            vulnerability_id="XSS-001",
            title="Cross-Site Scripting in Dashboard",
            description="XSS vulnerability found in user dashboard",
            severity="high",
            priority=VulnerabilityPriority.P1_HIGH,
            status=RemediationStatus.ASSIGNED,
            workflow_stage=WorkflowStage.ASSIGNMENT,
            discovered_date=datetime.now(UTC) - timedelta(hours=2),
            assigned_to="frontend-team",
            assigned_date=datetime.now(UTC) - timedelta(hours=1),
            due_date=datetime.now(UTC) + timedelta(hours=22),
            affected_components=["frontend", "dashboard"],
            business_impact="User data theft possible",
            remediation_effort_hours=4,
        ),
        SecurityFinding(
            finding_id="FIND-003",
            vulnerability_id="INFO-001",
            title="Information Disclosure in API Response",
            description="Sensitive information exposed in API response headers",
            severity="medium",
            priority=VulnerabilityPriority.P2_MEDIUM,
            status=RemediationStatus.IN_PROGRESS,
            workflow_stage=WorkflowStage.REMEDIATION,
            discovered_date=datetime.now(UTC) - timedelta(days=1),
            assigned_to="backend-team",
            assigned_date=datetime.now(UTC) - timedelta(days=1),
            due_date=datetime.now(UTC) + timedelta(days=6),
            affected_components=["api-gateway", "backend-services"],
            business_impact="Information leakage",
            remediation_effort_hours=2,
        ),
    ]

    for finding in sample_findings:
        triage.add_finding(finding)

    print("✅ Created sample security findings")


if __name__ == "__main__":
    # Example usage
    print("Initializing Security Triage System...")

    triage = initialize_triage_system()

    # Create sample findings
    create_sample_findings()

    # Generate report
    report = triage.generate_security_report()
    print(report)

    # Save report
    with open("security_report.md", "w") as f:
        f.write(report)

    print("✅ Security report saved to security_report.md")
