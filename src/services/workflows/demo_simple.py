"""Simple demonstration of Proactive Anomaly-to-Action Workflows"""

import asyncio
import logging
from datetime import datetime

from .security_monitor_integration import ProactiveSecurityMonitor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def simple_demonstration():
    """Simple demonstration of the workflow system"""
    print("PROACTIVE ANOMALY-TO-ACTION WORKFLOWS DEMONSTRATION")
    print("=" * 60)

    # Initialize the system
    monitor = ProactiveSecurityMonitor()
    print("System initialized successfully")

    # Create a mock security alert
    class MockAlert:
        def __init__(self):
            self.id = "alert-001"
            self.timestamp = datetime.now()
            self.severity = "HIGH"
            self.pattern_type = "failed_login"
            self.message = "Multiple failed login attempts detected"
            self.source_ip = "192.168.1.100"
            self.user_agent = "Mozilla/5.0"
            self.endpoint = "/api/login"
            self.ai_confidence = 0.85
            self.risk_score = 75
            self.recommended_actions = ["Block IP", "Review logs"]

    # Process the alert
    alert = MockAlert()
    print(f"\nProcessing security alert: {alert.id}")
    print(f"Severity: {alert.severity}")
    print(f"Pattern: {alert.pattern_type}")

    # Run through workflow system
    result = await monitor.process_security_alert(alert)

    # Display results
    print("\nWorkflow Results:")
    print(f"- Task Created: {result['task_created']}")
    print(f"- Task ID: {result['task_id']}")
    print(f"- Incident ID: {result['incident_id']}")
    print(f"- Assignee: {result['assignee']}")
    print(f"- Priority: {result['priority']}")
    print(f"- Estimated Resolution: {result['estimated_resolution']}")

    # Get statistics
    stats = monitor.get_workflow_statistics()
    print("\nSystem Statistics:")
    print(f"- Alerts Processed: {stats['proactive_workflows']['alerts_processed']}")
    print(f"- Tasks Created: {stats['proactive_workflows']['tasks_created']}")
    print(f"- Success Rate: {stats['proactive_workflows']['success_rate']:.1%}")

    print("\nDemonstration Complete!")
    print("The system successfully converted a security alert into an actionable task.")

    return result


if __name__ == "__main__":
    result = asyncio.run(simple_demonstration())
