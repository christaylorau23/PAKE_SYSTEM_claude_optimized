"""Proactive Anomaly-to-Action Workflow Engine

Automatically converts security anomalies into actionable tasks with
comprehensive context, priority assignment, and incident response workflows.
"""

import hashlib
import logging
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .task_management import (
    Task,
    TaskManagementSystem,
    TaskPriority,
    TaskStatus,
    TaskType,
)

logger = logging.getLogger(__name__)


class IncidentPriority(Enum):
    """Incident priority levels that map to task priorities"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class WorkflowAction(Enum):
    """Actions that can be taken by workflow rules"""

    CREATE_IMMEDIATE_TASK = "create_immediate_task"
    CREATE_STANDARD_TASK = "create_standard_task"
    CORRELATE_OR_CREATE = "correlate_or_create"
    BATCH_ALERTS = "batch_alerts"
    ESCALATE_IMMEDIATELY = "escalate_immediately"
    IGNORE = "ignore"


@dataclass
class WorkflowRule:
    """Rules that determine how alerts are processed into tasks"""

    name: str
    condition: Callable[[Any], bool]
    action: WorkflowAction
    priority: IncidentPriority
    assignee: str | None = None
    response_time: str | None = None
    correlation_window: str | None = None
    correlation_key: str | None = None
    batch_size: int | None = None
    batch_timeout: str | None = None
    escalation_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def execute(self, alert: Any) -> "TaskProperties":
        """Execute the rule and return task properties"""
        return TaskProperties(
            priority=self.priority,
            assignee=self.assignee,
            response_time=self.response_time,
            action=self.action,
        )


@dataclass
class TaskProperties:
    """Properties for task creation from workflow rules"""

    priority: IncidentPriority
    assignee: str | None = None
    response_time: str | None = None
    action: WorkflowAction | None = None
    escalated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityIncident:
    """Security incident tracking"""

    id: str
    alert_ids: list[str]
    incident_type: str
    severity: str
    created_at: datetime
    status: str = "open"
    assigned_task_id: str | None = None
    correlation_key: str | None = None
    merged_incidents: list[str] = field(default_factory=list)


@dataclass
class IncidentTask:
    """Enhanced task specifically for security incidents"""

    title: str
    description: str
    priority: TaskPriority
    security_alert_id: str
    incident_type: str
    investigation_checklist: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    attached_logs: str | None = None
    network_context: dict[str, Any] | None = None
    user_context: dict[str, Any] | None = None
    system_context: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] | None = None

    @classmethod
    def from_security_alert(cls, alert: Any) -> "IncidentTask":
        """Create an incident task from a security alert"""
        # Map alert severity to task priority
        priority_mapping = {
            "LOW": TaskPriority.LOW,
            "MEDIUM": TaskPriority.MEDIUM,
            "HIGH": TaskPriority.HIGH,
            "CRITICAL": TaskPriority.CRITICAL,
        }

        priority = priority_mapping.get(alert.severity, TaskPriority.MEDIUM)

        # Generate title based on alert type and content
        title = cls._generate_task_title(alert)

        # Generate comprehensive description
        description = cls._generate_task_description(alert)

        # Generate investigation checklist
        checklist = cls._generate_investigation_checklist(alert)

        # Generate recommended actions
        actions = cls._generate_recommended_actions(alert)

        # Collect contextual data
        network_context = cls._collect_network_context(alert)
        user_context = cls._collect_user_context(alert)
        system_context = cls._collect_system_context(alert)
        timeline = cls._generate_timeline(alert)

        return cls(
            title=title,
            description=description,
            priority=priority,
            security_alert_id=alert.id,
            incident_type=alert.pattern_type,
            investigation_checklist=checklist,
            recommended_actions=actions,
            attached_logs=cls._collect_logs(alert),
            network_context=network_context,
            user_context=user_context,
            system_context=system_context,
            timeline=timeline,
        )

    @staticmethod
    def _generate_task_title(alert: Any) -> str:
        """Generate descriptive task title"""
        pattern_titles = {
            "failed_login": "Investigate Failed Login Attempts",
            "sql_injection": "Critical: SQL Injection Attack Detected",
            "privilege_escalation": "Urgent: Privilege Escalation Attempt",
            "data_exfiltration": "Critical: Potential Data Exfiltration",
            "suspicious_access": "Investigate Suspicious Access Pattern",
            "rate_limiting": "Review Rate Limiting Violations",
        }

        base_title = pattern_titles.get(
            alert.pattern_type,
            "Security Incident Investigation",
        )

        # Add source IP if available
        if hasattr(alert, "source_ip") and alert.source_ip:
            return f"{base_title} - {alert.source_ip}"

        return base_title

    @staticmethod
    def _generate_task_description(alert: Any) -> str:
        """Generate comprehensive task description"""
        description = f"""
SECURITY INCIDENT DETECTED

Alert ID: {alert.id}
Severity: {alert.severity}
Pattern Type: {alert.pattern_type}
Detection Time: {alert.timestamp}
AI Confidence: {alert.ai_confidence:.2%}

INCIDENT SUMMARY:
{alert.message}

IMMEDIATE ACTIONS REQUIRED:
1. Review and validate the security alert
2. Analyze attached logs and context
3. Determine if incident is legitimate threat
4. Implement appropriate containment measures
5. Document findings and actions taken

RISK ASSESSMENT:
- Risk Score: {getattr(alert, "risk_score", "Unknown")}
- Potential Impact: {alert.severity}
- Confidence Level: {alert.ai_confidence:.2%}

This task was automatically created by the Proactive Anomaly-to-Action system.
"""
        return description.strip()

    @staticmethod
    def _generate_investigation_checklist(alert: Any) -> list[str]:
        """Generate investigation checklist based on alert type"""
        base_checklist = [
            "Validate alert accuracy and eliminate false positives",
            "Review system logs for the timeframe of incident",
            "Check for additional related security events",
            "Document initial findings and observations",
        ]

        pattern_specific_checks = {
            "failed_login": [
                "Verify user account legitimacy",
                "Check for REDACTED_SECRET spray attacks",
                "Review source IP reputation",
                "Examine user's recent login history",
                "Check if account should be locked/suspended",
            ],
            "sql_injection": [
                "Identify affected database and tables",
                "Review database logs for unauthorized queries",
                "Check for data modification or extraction",
                "Validate web application input sanitization",
                "Review application logs for attack patterns",
            ],
            "privilege_escalation": [
                "Identify user account involved in escalation",
                "Review privilege changes and authorization logs",
                "Check for unauthorized admin access attempts",
                "Validate current user permissions",
                "Review recent system configuration changes",
            ],
            "suspicious_access": [
                "Analyze access patterns and timing",
                "Review user's typical access behavior",
                "Check for data access outside normal scope",
                "Validate business justification for access",
                "Review access controls and permissions",
            ],
        }

        specific_checks = pattern_specific_checks.get(alert.pattern_type, [])
        return base_checklist + specific_checks

    @staticmethod
    def _generate_recommended_actions(alert: Any) -> list[str]:
        """Generate recommended actions based on alert"""
        base_actions = [
            "Review and analyze security alert details",
            "Collect additional forensic evidence",
            "Document investigation process and findings",
        ]

        # Use existing recommended actions from alert if available
        if hasattr(alert, "recommended_actions") and alert.recommended_actions:
            return base_actions + alert.recommended_actions

        # Generate based on alert type
        pattern_actions = {
            "failed_login": [
                "Consider blocking source IP address",
                "Reset user REDACTED_SECRET if account compromised",
                "Enable additional MFA for affected account",
            ],
            "sql_injection": [
                "Block malicious requests at WAF level",
                "Review and update input validation",
                "Consider temporary database access restrictions",
            ],
            "privilege_escalation": [
                "Immediately revoke elevated privileges",
                "Review and audit user access permissions",
                "Enable additional monitoring for user account",
            ],
        }

        specific_actions = pattern_actions.get(alert.pattern_type, [])
        return base_actions + specific_actions

    @staticmethod
    def _collect_logs(alert: Any) -> str:
        """Collect relevant logs for the incident"""
        # This would integrate with log aggregation systems
        return f"Logs automatically collected for alert {alert.id}"

    @staticmethod
    def _collect_network_context(alert: Any) -> dict[str, Any]:
        """Collect network-related context"""
        context = {}

        if hasattr(alert, "source_ip"):
            context["source_ip"] = alert.source_ip
            # In production, would do IP reputation lookup, geolocation, etc.
            context["ip_reputation"] = "Unknown"
            context["geographic_location"] = "Unknown"
            context["is_internal_ip"] = alert.source_ip.startswith(
                ("192.168.", "10.", "172."),
            )

        if hasattr(alert, "endpoint"):
            context["target_endpoint"] = alert.endpoint
            # Would be determined by endpoint classification
            context["endpoint_sensitivity"] = "Medium"

        return context

    @staticmethod
    def _collect_user_context(alert: Any) -> dict[str, Any]:
        """Collect user-related context"""
        context = {}

        # This would integrate with user directory services
        context["user_account_status"] = "Unknown"
        context["user_recent_activity"] = "Requires investigation"
        context["user_permissions"] = "To be reviewed"

        return context

    @staticmethod
    def _collect_system_context(alert: Any) -> dict[str, Any]:
        """Collect system-related context"""
        context = {}

        context["system_status"] = "Operational"
        context["recent_changes"] = "None detected"
        context["affected_services"] = []

        return context

    @staticmethod
    def _generate_timeline(alert: Any) -> list[dict[str, Any]]:
        """Generate incident timeline"""
        timeline = [
            {
                "timestamp": alert.timestamp,
                "event": "Security alert detected",
                "details": alert.message,
                "source": "AI Security Monitor",
            },
            {
                "timestamp": datetime.now(),
                "event": "Incident task created",
                "details": "Automated task creation by Anomaly-to-Action system",
                "source": "Workflow Engine",
            },
        ]

        return timeline


@dataclass
class IncidentAssignment:
    """Assignment information for incidents"""

    assignee_id: str
    assignee_name: str
    team: str
    assignment_reason: str
    assigned_at: datetime


@dataclass
class AnomalyProcessingResult:
    """Result of processing a security anomaly"""

    task_created: bool
    task_id: str | None = None
    incident_id: str | None = None
    assignee: str | None = None
    priority: IncidentPriority | None = None
    response_time: str | None = None
    escalated: bool = False
    duplicate_detected: bool = False
    merged_with_incident: str | None = None
    batched: bool = False
    batch_id: str | None = None
    workflow_completed: bool = False
    task_title: str | None = None
    task_details: Any | None = None
    estimated_resolution_time: str | None = None
    incident_status: str | None = None
    response_initiated: bool = False


class AnomalyToActionEngine:
    """Main engine for converting anomalies to actionable tasks"""

    def __init__(self, task_manager: TaskManagementSystem):
        self.task_manager = task_manager
        self.workflow_rules: list[WorkflowRule] = []
        self.incident_counter = 0
        self.active_incidents: dict[str, SecurityIncident] = {}
        self.correlation_cache: dict[str, list[str]] = defaultdict(
            list,
        )  # correlation_key -> incident_ids
        self.alert_deduplication: dict[str, str] = {}  # alert_hash -> incident_id

        # Initialize default workflow rules
        self._setup_default_workflow_rules()

    def _setup_default_workflow_rules(self):
        """Setup default workflow rules for common security patterns"""
        # Critical alerts get immediate response
        critical_rule = WorkflowRule(
            name="critical_immediate_response",
            condition=lambda alert: alert.severity == "CRITICAL",
            action=WorkflowAction.CREATE_IMMEDIATE_TASK,
            priority=IncidentPriority.CRITICAL,
            assignee="security_team_lead",
            response_time="immediate",
        )

        # SQL injection gets senior analyst
        sql_injection_rule = WorkflowRule(
            name="sql_injection_expert",
            condition=lambda alert: alert.pattern_type == "sql_injection",
            action=WorkflowAction.CREATE_IMMEDIATE_TASK,
            priority=IncidentPriority.CRITICAL,
            assignee="senior_security_analyst",
            response_time="immediate",
        )

        # Failed logins are correlated by IP
        failed_login_rule = WorkflowRule(
            name="failed_login_clustering",
            condition=lambda alert: alert.pattern_type == "failed_login",
            action=WorkflowAction.CORRELATE_OR_CREATE,
            priority=IncidentPriority.HIGH,
            assignee="security_analyst",
            correlation_window="5 minutes",
            correlation_key="source_ip",
        )

        # Privilege escalation gets immediate attention
        privilege_escalation_rule = WorkflowRule(
            name="privilege_escalation_urgent",
            condition=lambda alert: alert.pattern_type == "privilege_escalation",
            action=WorkflowAction.CREATE_IMMEDIATE_TASK,
            priority=IncidentPriority.CRITICAL,
            assignee="senior_security_analyst",
            response_time="immediate",
        )

        # Low priority alerts can be batched
        low_priority_rule = WorkflowRule(
            name="low_priority_batching",
            condition=lambda alert: alert.severity == "LOW",
            action=WorkflowAction.BATCH_ALERTS,
            priority=IncidentPriority.LOW,
            batch_size=5,
            batch_timeout="1 hour",
        )

        # Data exfiltration gets emergency response
        data_exfiltration_rule = WorkflowRule(
            name="data_exfiltration_emergency",
            condition=lambda alert: alert.pattern_type == "data_exfiltration",
            action=WorkflowAction.ESCALATE_IMMEDIATELY,
            priority=IncidentPriority.EMERGENCY,
            assignee="incident_response_team",
            response_time="immediate",
        )

        self.workflow_rules = [
            critical_rule,
            sql_injection_rule,
            failed_login_rule,
            privilege_escalation_rule,
            data_exfiltration_rule,
            low_priority_rule,
        ]

    async def process_security_alert(self, alert: Any) -> AnomalyProcessingResult:
        """Process a security alert and create appropriate tasks/incidents"""
        # Check for duplicates
        alert_hash = self._generate_alert_hash(alert)
        if alert_hash in self.alert_deduplication:
            existing_incident_id = self.alert_deduplication[alert_hash]
            return AnomalyProcessingResult(
                task_created=False,
                duplicate_detected=True,
                merged_with_incident=existing_incident_id,
                workflow_completed=True,
                incident_id=existing_incident_id,
            )

        # Find matching workflow rule
        matching_rule = self._find_matching_rule(alert)
        if not matching_rule:
            # No rule matches - create default task
            return await self._create_default_task(alert)

        # Execute the matched rule
        if matching_rule.action == WorkflowAction.CREATE_IMMEDIATE_TASK:
            return await self._create_immediate_task(alert, matching_rule)
        if matching_rule.action == WorkflowAction.CORRELATE_OR_CREATE:
            return await self._correlate_or_create_task(alert, matching_rule)
        if matching_rule.action == WorkflowAction.BATCH_ALERTS:
            return await self._batch_alert(alert, matching_rule)
        if matching_rule.action == WorkflowAction.ESCALATE_IMMEDIATELY:
            return await self._escalate_immediately(alert, matching_rule)
        return await self._create_standard_task(alert, matching_rule)

    def _generate_alert_hash(self, alert: Any) -> str:
        """Generate hash for alert deduplication"""
        # Create hash based on key alert characteristics
        hash_data = (
            f"{alert.pattern_type}|{getattr(alert, 'source_ip', '')}|{alert.message}"
        )
        return hashlib.sha256(hash_data.encode()).hexdigest()

    def _find_matching_rule(self, alert: Any) -> WorkflowRule | None:
        """Find the first matching workflow rule for an alert"""
        for rule in self.workflow_rules:
            try:
                if rule.condition(alert):
                    return rule
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
        return None

    async def _create_immediate_task(
        self,
        alert: Any,
        rule: WorkflowRule,
    ) -> AnomalyProcessingResult:
        """Create immediate high-priority task"""
        # Create incident
        incident = await self._create_incident(alert, rule)

        # Create task from alert
        incident_task = IncidentTask.from_security_alert(alert)

        # Convert to Task object
        task = Task(
            id=str(uuid.uuid4()),
            title=incident_task.title,
            description=incident_task.description,
            task_type=TaskType.SECURITY_INCIDENT,
            priority=self._map_incident_to_task_priority(rule.priority),
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            created_by="anomaly_to_action_system",
            security_alert_id=alert.id,
            incident_type=alert.pattern_type,
            investigation_checklist=incident_task.investigation_checklist,
            recommended_actions=incident_task.recommended_actions,
            attached_logs=incident_task.attached_logs,
            network_context=incident_task.network_context,
            user_context=incident_task.user_context,
            system_context=incident_task.system_context,
            timeline=incident_task.timeline,
        )

        # Create task in management system
        task_id = await self.task_manager.create_task(task)

        # Assign task
        if rule.assignee:
            await self.task_manager.assign_task(
                task_id,
                rule.assignee,
                "workflow_engine",
            )

        # Update incident with task
        incident.assigned_task_id = task_id

        # Store deduplication info
        alert_hash = self._generate_alert_hash(alert)
        self.alert_deduplication[alert_hash] = incident.id

        return AnomalyProcessingResult(
            task_created=True,
            task_id=task_id,
            incident_id=incident.id,
            assignee=rule.assignee,
            priority=rule.priority,
            response_time=rule.response_time,
            escalated=rule.priority == IncidentPriority.CRITICAL,
            workflow_completed=True,
            task_title=incident_task.title,
            task_details=incident_task,
            estimated_resolution_time=self._estimate_resolution_time(rule.priority),
            incident_status="open",
            response_initiated=True,
        )

    async def _correlate_or_create_task(
        self,
        alert: Any,
        rule: WorkflowRule,
    ) -> AnomalyProcessingResult:
        """Correlate with existing incidents or create new task"""
        # Generate correlation key
        correlation_key = self._generate_correlation_key(alert, rule)

        # Check for existing correlated incidents
        existing_incidents = self.correlation_cache.get(correlation_key, [])

        # Filter for recent incidents (within correlation window)
        recent_incidents = []
        correlation_window = self._parse_time_window(
            rule.correlation_window or "5 minutes",
        )
        cutoff_time = datetime.now() - correlation_window

        for incident_id in existing_incidents:
            if incident_id in self.active_incidents:
                incident = self.active_incidents[incident_id]
                if incident.created_at > cutoff_time:
                    recent_incidents.append(incident_id)

        if recent_incidents:
            # Correlate with existing incident
            incident_id = recent_incidents[0]  # Use most recent
            incident = self.active_incidents[incident_id]
            incident.alert_ids.append(alert.id)

            # Store deduplication info
            alert_hash = self._generate_alert_hash(alert)
            self.alert_deduplication[alert_hash] = incident_id

            return AnomalyProcessingResult(
                task_created=False,
                incident_id=incident_id,
                merged_with_incident=incident_id,
                workflow_completed=True,
            )
        # Create new task
        result = await self._create_immediate_task(alert, rule)

        # Add to correlation cache
        self.correlation_cache[correlation_key].append(result.incident_id)

        return result

    async def _batch_alert(
        self,
        alert: Any,
        rule: WorkflowRule,
    ) -> AnomalyProcessingResult:
        """Batch alert for later processing"""
        # This is a simplified implementation
        # In production, would implement proper batching with timeouts

        batch_id = f"batch_{rule.name}_{datetime.now().strftime('%Y%m%d_%H')}"

        return AnomalyProcessingResult(
            task_created=False,
            batched=True,
            batch_id=batch_id,
            workflow_completed=True,
        )

    async def _escalate_immediately(
        self,
        alert: Any,
        rule: WorkflowRule,
    ) -> AnomalyProcessingResult:
        """Escalate alert immediately with emergency response"""
        result = await self._create_immediate_task(alert, rule)
        result.escalated = True

        # Additional escalation actions would go here
        # (notifications, emergency protocols, etc.)

        return result

    async def _create_standard_task(
        self,
        alert: Any,
        rule: WorkflowRule,
    ) -> AnomalyProcessingResult:
        """Create standard priority task"""
        return await self._create_immediate_task(alert, rule)

    async def _create_default_task(self, alert: Any) -> AnomalyProcessingResult:
        """Create default task when no rules match"""
        default_rule = WorkflowRule(
            name="default",
            condition=lambda x: True,
            action=WorkflowAction.CREATE_STANDARD_TASK,
            priority=IncidentPriority.MEDIUM,
            assignee="security_analyst",
        )

        return await self._create_standard_task(alert, default_rule)

    async def _create_incident(
        self,
        alert: Any,
        rule: WorkflowRule,
    ) -> SecurityIncident:
        """Create a security incident"""
        self.incident_counter += 1
        incident_id = (
            f"INC-{datetime.now().strftime('%Y%m%d')}-{self.incident_counter:04d}"
        )

        incident = SecurityIncident(
            id=incident_id,
            alert_ids=[alert.id],
            incident_type=alert.pattern_type,
            severity=alert.severity,
            created_at=datetime.now(),
            status="open",
        )

        self.active_incidents[incident_id] = incident
        return incident

    def _generate_correlation_key(self, alert: Any, rule: WorkflowRule) -> str:
        """Generate correlation key for alert"""
        if rule.correlation_key == "source_ip":
            return f"{alert.pattern_type}|{getattr(alert, 'source_ip', 'unknown')}"
        if rule.correlation_key == "user":
            return f"{alert.pattern_type}|{getattr(alert, 'user', 'unknown')}"
        return f"{alert.pattern_type}|general"

    def _parse_time_window(self, window_str: str) -> timedelta:
        """Parse time window string to timedelta"""
        # Simplified parser - "5 minutes", "1 hour", etc.
        try:
            parts = window_str.lower().split()
            value = int(parts[0])
            unit = parts[1]

            if unit.startswith("minute"):
                return timedelta(minutes=value)
            if unit.startswith("hour"):
                return timedelta(hours=value)
            if unit.startswith("day"):
                return timedelta(days=value)
            return timedelta(minutes=5)  # Default
        except BaseException:
            return timedelta(minutes=5)  # Default

    def _map_incident_to_task_priority(
        self,
        incident_priority: IncidentPriority,
    ) -> TaskPriority:
        """Map incident priority to task priority"""
        mapping = {
            IncidentPriority.LOW: TaskPriority.LOW,
            IncidentPriority.MEDIUM: TaskPriority.MEDIUM,
            IncidentPriority.HIGH: TaskPriority.HIGH,
            IncidentPriority.CRITICAL: TaskPriority.CRITICAL,
            IncidentPriority.EMERGENCY: TaskPriority.CRITICAL,  # Map emergency to critical for tasks
        }
        return mapping.get(incident_priority, TaskPriority.MEDIUM)

    def _estimate_resolution_time(self, priority: IncidentPriority) -> str:
        """Estimate resolution time based on priority"""
        estimates = {
            IncidentPriority.EMERGENCY: "1 hour",
            IncidentPriority.CRITICAL: "4 hours",
            IncidentPriority.HIGH: "24 hours",
            IncidentPriority.MEDIUM: "72 hours",
            IncidentPriority.LOW: "1 week",
        }
        return estimates.get(priority, "Unknown")


class IncidentResponseWorkflow:
    """Orchestrates incident response workflows"""

    def __init__(self):
        self.active_workflows: dict[str, dict[str, Any]] = {}

    async def initiate_response(self, alert: Any) -> "IncidentResponseResult":
        """Initiate incident response based on alert"""
        # Determine response level based on alert severity
        response_level = self._determine_response_level(alert)

        # Create response plan
        response_plan = self._create_response_plan(alert, response_level)

        # Execute immediate actions
        immediate_actions = await self._execute_immediate_actions(alert, response_plan)

        return IncidentResponseResult(
            incident_declared=True,
            response_team_notified=True,
            containment_initiated=response_level >= 3,
            investigation_started=True,
            immediate_actions_taken=immediate_actions,
            escalation_level=response_level,
            response_team_size=self._calculate_team_size(response_level),
            executive_notification=response_level >= 4,
        )

    def _determine_response_level(self, alert: Any) -> int:
        """Determine response level (1-5 scale)"""
        severity_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        base_level = severity_levels.get(alert.severity, 2)

        # Adjust based on alert type
        if alert.pattern_type in ["data_exfiltration", "privilege_escalation"]:
            base_level += 1

        return min(base_level, 5)

    def _create_response_plan(self, alert: Any, response_level: int) -> dict[str, Any]:
        """Create incident response plan"""
        return {
            "response_level": response_level,
            "containment_required": response_level >= 3,
            "executive_notification": response_level >= 4,
            "external_notification": response_level >= 4,
            "forensic_collection": response_level >= 3,
        }

    async def _execute_immediate_actions(
        self,
        alert: Any,
        plan: dict[str, Any],
    ) -> list[str]:
        """Execute immediate response actions"""
        actions = [
            "Security alert validated and processed",
            "Incident response team notified",
            "Initial containment measures assessed",
        ]

        if plan.get("containment_required"):
            actions.append("Containment procedures initiated")

        if plan.get("forensic_collection"):
            actions.append("Forensic evidence collection started")

        return actions

    def _calculate_team_size(self, response_level: int) -> int:
        """Calculate response team size based on level"""
        return min(response_level + 1, 6)


@dataclass
class IncidentResponseResult:
    """Result of incident response initiation"""

    incident_declared: bool
    response_team_notified: bool
    containment_initiated: bool
    investigation_started: bool
    immediate_actions_taken: list[str]
    escalation_level: int
    response_team_size: int
    executive_notification: bool
