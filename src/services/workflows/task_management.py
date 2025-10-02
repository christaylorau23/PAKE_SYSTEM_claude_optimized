"""Task Management System for Security Incident Response

Provides task creation, assignment, and tracking capabilities for
automated incident response workflows.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""

    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_INFO = "waiting_for_info"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TaskType(Enum):
    """Task type categories"""

    SECURITY_INCIDENT = "security_incident"
    INVESTIGATION = "investigation"
    REMEDIATION = "remediation"
    MONITORING = "monitoring"
    COMPLIANCE = "compliance"
    MAINTENANCE = "maintenance"


@dataclass
class TaskAssignment:
    """Task assignment information"""

    assignee_id: str
    assignee_name: str
    assigned_at: datetime
    assigned_by: str
    team: str | None = None
    role: str | None = None
    notification_sent: bool = False


@dataclass
class TaskContext:
    """Contextual information attached to tasks"""

    security_alert_id: str | None = None
    incident_id: str | None = None
    affected_systems: list[str] = field(default_factory=list)
    affected_users: list[str] = field(default_factory=list)
    threat_indicators: dict[str, Any] = field(default_factory=dict)
    attached_logs: list[str] = field(default_factory=list)
    network_context: dict[str, Any] = field(default_factory=dict)
    user_context: dict[str, Any] = field(default_factory=dict)
    system_context: dict[str, Any] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Task:
    """Core task representation"""

    id: str
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    created_by: str
    assignment: TaskAssignment | None = None
    context: TaskContext | None = None
    due_date: datetime | None = None
    estimated_duration: timedelta | None = None
    tags: list[str] = field(default_factory=list)
    checklist: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    parent_task_id: str | None = None
    subtasks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Security-specific fields
    security_alert_id: str | None = None
    incident_type: str | None = None
    investigation_checklist: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    attached_logs: str | None = None
    network_context: dict[str, Any] | None = None
    user_context: dict[str, Any] | None = None
    system_context: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] | None = None


class TaskManager:
    """Task management system for incident response"""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.assignments: dict[str, list[str]] = {}  # assignee_id -> task_ids
        self.task_history: list[dict[str, Any]] = []
        self.assignment_rules: list[Callable[[Task], str | None]] = []

        # Initialize default assignment rules
        self._setup_default_assignment_rules()

    def _setup_default_assignment_rules(self):
        """Setup default task assignment rules"""

        def critical_security_rule(task: Task) -> str | None:
            """Critical security incidents go to security team lead"""
            if task.task_type == TaskType.SECURITY_INCIDENT and task.priority in [
                TaskPriority.CRITICAL,
                TaskPriority.EMERGENCY,
            ]:
                return "security_team_lead"
            return None

        def sql_injection_rule(task: Task) -> str | None:
            """SQL injection incidents go to senior security analyst"""
            if (
                task.incident_type == "sql_injection"
                or "sql injection" in task.title.lower()
            ):
                return "senior_security_analyst"
            return None

        def failed_login_rule(task: Task) -> str | None:
            """Failed login incidents go to security analyst"""
            if (
                task.incident_type == "failed_login"
                or "failed login" in task.title.lower()
            ):
                return "security_analyst"
            return None

        def privilege_escalation_rule(task: Task) -> str | None:
            """Privilege escalation goes to senior analyst"""
            if (
                task.incident_type == "privilege_escalation"
                or "privilege escalation" in task.title.lower()
            ):
                return "senior_security_analyst"
            return None

        def default_assignment_rule(task: Task) -> str | None:
            """Default assignment based on priority"""
            if task.priority == TaskPriority.CRITICAL:
                return "security_team_lead"
            if task.priority == TaskPriority.HIGH:
                return "senior_security_analyst"
            if task.priority == TaskPriority.MEDIUM:
                return "security_analyst"
            return "junior_security_analyst"

        self.assignment_rules = [
            critical_security_rule,
            sql_injection_rule,
            failed_login_rule,
            privilege_escalation_rule,
            default_assignment_rule,
        ]

    async def create_task(self, task: Task) -> str:
        """Create a new task"""
        if not task.id:
            task.id = str(uuid.uuid4())

        # Set creation timestamp if not set
        if not task.created_at:
            task.created_at = datetime.now()

        # Auto-assign if not already assigned
        if not task.assignment:
            assignee = self._determine_assignee(task)
            if assignee:
                await self.assign_task(task.id, assignee, "system_auto_assignment")

        # Store task
        self.tasks[task.id] = task

        # Add to history
        self.task_history.append(
            {
                "action": "created",
                "task_id": task.id,
                "timestamp": datetime.now(),
                "details": {"title": task.title, "priority": task.priority.value},
            },
        )

        logger.info(f"Created task {task.id}: {task.title}")
        return task.id

    async def assign_task(
        self,
        task_id: str,
        assignee_id: str,
        assigned_by: str,
    ) -> bool:
        """Assign a task to a user"""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return False

        task = self.tasks[task_id]

        # Create assignment
        assignment = TaskAssignment(
            assignee_id=assignee_id,
            assignee_name=self._get_assignee_name(assignee_id),
            assigned_at=datetime.now(),
            assigned_by=assigned_by,
            team=self._get_assignee_team(assignee_id),
            role=self._get_assignee_role(assignee_id),
        )

        task.assignment = assignment
        task.status = TaskStatus.ASSIGNED

        # Track assignments
        if assignee_id not in self.assignments:
            self.assignments[assignee_id] = []
        self.assignments[assignee_id].append(task_id)

        # Add to history
        self.task_history.append(
            {
                "action": "assigned",
                "task_id": task_id,
                "timestamp": datetime.now(),
                "details": {"assignee_id": assignee_id, "assigned_by": assigned_by},
            },
        )

        logger.info(f"Assigned task {task_id} to {assignee_id}")
        return True

    def _determine_assignee(self, task: Task) -> str | None:
        """Determine appropriate assignee for a task"""
        for rule in self.assignment_rules:
            assignee = rule(task)
            if assignee:
                return assignee
        return None

    def _get_assignee_name(self, assignee_id: str) -> str:
        """Get display name for assignee"""
        # In production, this would lookup from user directory
        name_mapping = {
            "security_team_lead": "Security Team Lead",
            "senior_security_analyst": "Senior Security Analyst",
            "security_analyst": "Security Analyst",
            "junior_security_analyst": "Junior Security Analyst",
            "incident_response_team": "Incident Response Team",
        }
        return name_mapping.get(assignee_id, assignee_id.replace("_", " ").title())

    def _get_assignee_team(self, assignee_id: str) -> str:
        """Get team for assignee"""
        if "security" in assignee_id:
            return "Security Team"
        if "incident" in assignee_id:
            return "Incident Response Team"
        return "IT Operations"

    def _get_assignee_role(self, assignee_id: str) -> str:
        """Get role for assignee"""
        if "lead" in assignee_id:
            return "Team Lead"
        if "senior" in assignee_id:
            return "Senior Analyst"
        if "junior" in assignee_id:
            return "Junior Analyst"
        return "Analyst"

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        updated_by: str,
    ) -> bool:
        """Update task status"""
        if task_id not in self.tasks:
            return False

        old_status = self.tasks[task_id].status
        self.tasks[task_id].status = status

        self.task_history.append(
            {
                "action": "status_changed",
                "task_id": task_id,
                "timestamp": datetime.now(),
                "details": {
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "updated_by": updated_by,
                },
            },
        )

        logger.info(
            f"Updated task {task_id} status: {old_status.value} -> {status.value}",
        )
        return True

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def get_tasks_by_assignee(self, assignee_id: str) -> list[Task]:
        """Get all tasks assigned to a user"""
        task_ids = self.assignments.get(assignee_id, [])
        return [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get tasks by status"""
        return [task for task in self.tasks.values() if task.status == status]

    def get_tasks_by_priority(self, priority: TaskPriority) -> list[Task]:
        """Get tasks by priority"""
        return [task for task in self.tasks.values() if task.priority == priority]

    def get_security_incident_tasks(self) -> list[Task]:
        """Get all security incident tasks"""
        return [
            task
            for task in self.tasks.values()
            if task.task_type == TaskType.SECURITY_INCIDENT
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get task management statistics"""
        total_tasks = len(self.tasks)

        status_counts: Dict[str, int] = {}
        priority_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for task in self.tasks.values():
            status_counts[task.status.value] = (
                status_counts.get(task.status.value, 0) + 1
            )
            priority_counts[task.priority.value] = (
                priority_counts.get(task.priority.value, 0) + 1
            )
            type_counts[task.task_type.value] = (
                type_counts.get(task.task_type.value, 0) + 1
            )

        return {
            "total_tasks": total_tasks,
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "type_breakdown": type_counts,
            "total_assignments": sum(len(tasks) for tasks in self.assignments.values()),
            "active_assignees": len(self.assignments),
        }


class TaskManagementSystem:
    """High-level task management system interface"""

    def __init__(self):
        self.task_manager = TaskManager()
        self.workflows: dict[str, Any] = {}
        self.notification_handlers: list[Callable] = []

    async def create_task(self, task: Task) -> str:
        """Create a task in the system"""
        task_id = await self.task_manager.create_task(task)

        # Send notifications
        await self._send_notifications(task, "created")

        return task_id

    async def assign_task(
        self,
        task_id: str,
        assignee_id: str,
        assigned_by: str = "system",
    ) -> bool:
        """Assign a task to a user"""
        success = await self.task_manager.assign_task(task_id, assignee_id, assigned_by)

        if success:
            task = self.task_manager.get_task(task_id)
            if task:
                await self._send_notifications(task, "assigned")

        return success

    async def _send_notifications(self, task: Task, action: str):
        """Send notifications for task events"""
        for handler in self.notification_handlers:
            try:
                await handler(task, action)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")

    def add_notification_handler(self, handler: Callable):
        """Add a notification handler"""
        self.notification_handlers.append(handler)

    def get_task_manager(self) -> TaskManager:
        """Get the underlying task manager"""
        return self.task_manager
