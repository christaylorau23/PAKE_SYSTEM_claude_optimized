"""Integration Bridge for AI Security Monitor and Anomaly-to-Action Workflows.

This module bridges the existing ai-security-monitor.py with the new
proactive anomaly-to-action workflow system.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
from typing import Any, Dict, TYPE_CHECKING

from .anomaly_to_action import AnomalyToActionEngine
from .task_management import TaskManagementSystem

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class SecurityAlertAdapter:
    """Adapter to convert SecurityAlert from ai-security-monitor.py to our workflow format."""

    def __init__(self, security_alert) -> None:
        """Initialize with SecurityAlert from ai-security-monitor.py."""
        self.id = security_alert.id
        self.timestamp = security_alert.timestamp
        self.severity = security_alert.severity
        self.pattern_type = (
            security_alert.pattern_type.value
            if hasattr(security_alert.pattern_type, "value")
            else security_alert.pattern_type
        )
        self.source_ip = security_alert.source_ip
        self.user_agent = security_alert.user_agent
        self.endpoint = security_alert.endpoint
        self.message = security_alert.message
        self.ai_confidence = security_alert.ai_confidence
        self.risk_score = security_alert.risk_score
        self.recommended_actions = security_alert.recommended_actions
        self.context = getattr(security_alert, "context", {})

        # Store original alert for reference
        self._original_alert = security_alert


class ProactiveSecurityMonitor:
    """Enhanced security monitor with proactive workflow integration."""

    def __init__(self) -> None:
        self.task_management_system = TaskManagementSystem()
        self.anomaly_to_action_engine = AnomalyToActionEngine(
            self.task_management_system,
        )
        self.alert_processors: list[Callable] = []
        self.notification_handlers: list[Callable] = []

        # Statistics tracking
        self.processed_alerts = 0
        self.tasks_created = 0
        self.incidents_created = 0

        # Setup default notification handlers
        self._setup_default_notifications()

    def _setup_default_notifications(self) -> None:
        """Setup default notification handlers for task creation."""

        async def log_task_creation(task, action) -> None:
            """Log task creation events."""
            if action == "created":
                logger.info(
                    "Proactive workflow created task: %s (Priority: %s)",
                    task.title,
                    task.priority.value,
                )

        async def alert_on_critical_tasks(task, action) -> None:
            """Send alerts for critical security tasks."""
            if action == "created" and task.priority.value in ["critical", "high"]:
                logger.warning("CRITICAL SECURITY TASK CREATED: %s", task.title)
                # In production, would send to alerting systems (Slack, email, etc.)

        self.task_management_system.add_notification_handler(log_task_creation)
        self.task_management_system.add_notification_handler(alert_on_critical_tasks)

    async def process_security_alert(self, security_alert) -> Dict[str, Any]:
        """Process security alert through proactive workflow system."""
        # Convert to our format
        adapted_alert = SecurityAlertAdapter(security_alert)

        # Process through anomaly-to-action engine
        result = await self.anomaly_to_action_engine.process_security_alert(
            adapted_alert,
        )

        # Update statistics
        self.processed_alerts += 1
        if result.task_created:
            self.tasks_created += 1
        if result.incident_id:
            self.incidents_created += 1

        # Call additional processors
        for processor in self.alert_processors:
            try:
                await processor(adapted_alert, result)
            except (ValueError, RuntimeError) as e:
                logger.error("Alert processor failed: %s", e)

        # Return comprehensive result
        return {
            "alert_id": adapted_alert.id,
            "workflow_result": result,
            "task_created": result.task_created,
            "task_id": result.task_id,
            "incident_id": result.incident_id,
            "assignee": result.assignee,
            "priority": result.priority.value if result.priority else None,
            "estimated_resolution": result.estimated_resolution_time,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def add_alert_processor(self, processor: Callable) -> None:
        """Add custom alert processor."""
        self.alert_processors.append(processor)

    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow processing statistics."""
        task_stats = self.task_management_system.get_task_manager().get_statistics()

        return {
            "proactive_workflows": {
                "alerts_processed": self.processed_alerts,
                "tasks_created": self.tasks_created,
                "incidents_created": self.incidents_created,
                "success_rate": self.tasks_created / max(self.processed_alerts, 1),
            },
            "task_management": task_stats,
            "active_incidents": len(self.anomaly_to_action_engine.active_incidents),
        }


# Global instance for integration with existing ai-security-monitor.py
proactive_monitor = ProactiveSecurityMonitor()


async def process_alert_with_workflows(security_alert) -> Dict[str, Any]:
    """Main integration function to be called from ai-security-monitor.py.

    This function should be called whenever a new SecurityAlert is created
    to automatically trigger the proactive workflow system.
    """
    return await proactive_monitor.process_security_alert(security_alert)


def get_workflow_dashboard() -> Dict[str, Any]:
    """Get workflow dashboard data for integration with existing security dashboard."""
    return proactive_monitor.get_workflow_statistics()


def integrate_with_security_monitor() -> None:
    """Integration function to patch the existing ai-security-monitor.py.

    This would modify the existing security monitor to call our workflow system
    whenever new alerts are created.
    """
    # This is a conceptual integration - in practice would require
    # modifying the ai-security-monitor.py to call our workflow system

    integration_code = '''
# Add this to ai-security-monitor.py after security alerts are created:

from services.workflows.security_monitor_integration import process_alert_with_workflows

# In the alert creation section, add:
async def create_security_alert_with_workflows(self) -> None:
    """Create security alert and trigger proactive workflows"""

    # Create the standard SecurityAlert
    alert = SecurityAlert(...)  # existing alert creation code

    # Add to global alerts storage (existing code)
    security_alerts.append(alert)

    # NEW: Trigger proactive workflows
    try:
        workflow_result = await process_alert_with_workflows(alert)
        logger.info("Proactive workflow triggered for alert %s: %s", alert.id, workflow_result)
    except (ValueError, RuntimeError) as e:
        logger.error("Proactive workflow failed for alert %s: %s", alert.id, e)

    return alert

# Modify the dashboard endpoint to include workflow data:
@app.get("/dashboard/enhanced")
async def get_enhanced_security_dashboard(self) -> None:
    """Enhanced dashboard with workflow data"""

    # Get existing dashboard data
    standard_dashboard = await get_security_dashboard()

    # Add workflow statistics
    workflow_stats = get_workflow_dashboard()

    return {
        **standard_dashboard,
        "proactive_workflows": workflow_stats
    }
'''

    logger.info(
        "Integration code template generated. See integration_code variable for implementation details.",
    )
    return integration_code


# Example usage and demonstration


async def demonstrate_integration() -> None:
    """Demonstrate the integration with sample alerts."""
    logger.info("Demonstrating Proactive Anomaly-to-Action Workflow Integration")

    # Create sample alerts that would come from ai-security-monitor.py
    class MockSecurityAlert:
        def __init__(self, id: str, severity: str, pattern_type: str, message: str) -> None:
            self.id = id
            self.timestamp = datetime.now(UTC)
            self.severity = severity
            self.pattern_type = pattern_type
            self.message = message
            self.source_ip = "192.168.1.100"
            self.user_agent = "Mozilla/5.0"
            self.endpoint = "/api/login"
            self.ai_confidence = 0.85
            self.risk_score = 75
            self.recommended_actions = ["Block IP", "Review logs"]

    # Simulate various security alerts
    alerts = [
        MockSecurityAlert(
            "alert-001",
            "HIGH",
            "failed_login",
            "Multiple failed login attempts",
        ),
        MockSecurityAlert(
            "alert-002",
            "CRITICAL",
            "sql_injection",
            "SQL injection detected",
        ),
        MockSecurityAlert(
            "alert-003",
            "MEDIUM",
            "suspicious_access",
            "Unusual access pattern",
        ),
    ]

    results = []
    for alert in alerts:
        logger.info(
            "Processing alert: %s - %s - %s",
            alert.id,
            alert.severity,
            alert.pattern_type,
        )
        result = await process_alert_with_workflows(alert)
        results.append(result)
        logger.info(
            "Result: Task created: %s, Incident: %s",
            result["task_created"],
            result["incident_id"],
        )

    # Show final statistics
    stats = get_workflow_dashboard()
    logger.info("Final statistics: %s", json.dumps(stats, indent=2))

    return results


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demonstrate_integration())