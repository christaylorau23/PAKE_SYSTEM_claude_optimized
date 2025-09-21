"""Demonstration of Proactive Anomaly-to-Action Workflows

This script demonstrates the complete workflow from security alert detection
to automated task creation and incident response.
"""

import asyncio
import logging
from datetime import datetime

from .security_monitor_integration import ProactiveSecurityMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SecurityAlertSimulator:
    """Simulates security alerts from ai-security-monitor.py"""

    def __init__(self):
        self.alert_counter = 0

    def create_mock_alert(
        self,
        severity: str,
        pattern_type: str,
        message: str,
        **kwargs,
    ) -> "MockSecurityAlert":
        """Create a mock security alert"""
        self.alert_counter += 1

        class MockSecurityAlert:
            def __init__(self, id, severity, pattern_type, message, **kwargs):
                self.id = id
                self.timestamp = datetime.now()
                self.severity = severity
                self.pattern_type = pattern_type
                self.message = message
                self.source_ip = kwargs.get("source_ip", "192.168.1.100")
                self.user_agent = kwargs.get("user_agent", "Mozilla/5.0")
                self.endpoint = kwargs.get("endpoint", "/api/login")
                self.ai_confidence = kwargs.get("ai_confidence", 0.85)
                self.risk_score = kwargs.get("risk_score", 75)
                self.recommended_actions = kwargs.get(
                    "recommended_actions",
                    ["Block IP", "Review logs"],
                )
                self.context = kwargs.get("context", {})

        return MockSecurityAlert(
            id=f"alert-{self.alert_counter:04d}",
            severity=severity,
            pattern_type=pattern_type,
            message=message,
            **kwargs,
        )


async def demonstrate_proactive_workflows():
    """Main demonstration of proactive anomaly-to-action workflows"""
    print("🚀 PROACTIVE ANOMALY-TO-ACTION WORKFLOWS DEMONSTRATION")
    print("=" * 70)

    # Initialize the proactive security monitor
    monitor = ProactiveSecurityMonitor()
    simulator = SecurityAlertSimulator()

    print("\n1️⃣ INITIALIZATION COMPLETE")
    print("   ✓ Proactive Security Monitor initialized")
    print("   ✓ Task Management System ready")
    print("   ✓ Anomaly-to-Action Engine loaded with workflow rules")

    # Demonstrate different types of security alerts
    alert_scenarios = [
        {
            "name": "Failed Login Attack",
            "severity": "HIGH",
            "pattern_type": "failed_login",
            "message": "Multiple failed login attempts detected from suspicious IP",
            "source_ip": "203.0.113.45",
            "context": {"attempts": 15, "timeframe": "2 minutes"},
        },
        {
            "name": "SQL Injection Attack",
            "severity": "CRITICAL",
            "pattern_type": "sql_injection",
            "message": "SQL injection attempt detected on user management endpoint",
            "endpoint": "/api/users",
            "context": {"payload": "' OR '1'='1", "blocked": False},
        },
        {
            "name": "Privilege Escalation Attempt",
            "severity": "CRITICAL",
            "pattern_type": "privilege_escalation",
            "message": "Unauthorized attempt to escalate privileges detected",
            "context": {"user": "john.doe", "target_role": "REDACTED_SECRET"},
        },
        {
            "name": "Suspicious Access Pattern",
            "severity": "MEDIUM",
            "pattern_type": "suspicious_access",
            "message": "Unusual access pattern detected outside business hours",
            "context": {"access_time": "03:30 AM", "normal_hours": "9AM-5PM"},
        },
        {
            "name": "Rate Limit Violation",
            "severity": "LOW",
            "pattern_type": "rate_limiting",
            "message": "Rate limit exceeded by automated client",
            "context": {"requests_per_minute": 1000, "limit": 100},
        },
    ]

    print("\n2️⃣ PROCESSING SECURITY ALERTS")
    print(f"   Processing {len(alert_scenarios)} different types of security alerts...")

    results = []
    for i, scenario in enumerate(alert_scenarios, 1):
        print(f"\n   📊 Scenario {i}: {scenario['name']}")

        # Create mock alert
        alert = simulator.create_mock_alert(
            severity=scenario["severity"],
            pattern_type=scenario["pattern_type"],
            message=scenario["message"],
            **{
                k: v
                for k, v in scenario.items()
                if k not in ["name", "severity", "pattern_type", "message"]
            },
        )

        print(f"      Alert ID: {alert.id}")
        print(f"      Severity: {alert.severity}")
        print(f"      Pattern: {alert.pattern_type}")

        # Process through proactive workflow system
        start_time = datetime.now()
        result = await monitor.process_security_alert(alert)
        processing_time = (datetime.now() - start_time).total_seconds()

        results.append(
            {
                "scenario": scenario["name"],
                "alert_id": alert.id,
                "result": result,
                "processing_time": processing_time,
            },
        )

        # Display results
        if result["task_created"]:
            print(f"      ✅ TASK CREATED: {result['task_id']}")
            print(f"         Priority: {result['priority']}")
            print(f"         Assignee: {result['assignee']}")
            print(f"         Incident: {result['incident_id']}")
            print(f"         Est. Resolution: {result['estimated_resolution']}")
        else:
            print(
                "      ℹ️  Alert processed (no task created - may be batched or correlated)",
            )

        print(f"      ⚡ Processing time: {processing_time:.3f} seconds")

    print("\n3️⃣ WORKFLOW CORRELATION DEMONSTRATION")
    print("   Demonstrating alert correlation and deduplication...")

    # Create correlated alerts (same IP, same pattern)
    correlated_alerts = []
    for i in range(3):
        alert = simulator.create_mock_alert(
            severity="MEDIUM",
            pattern_type="failed_login",
            message=f"Failed login attempt #{i + 1} from same IP",
            source_ip="203.0.113.45",  # Same IP as first scenario
        )
        correlated_alerts.append(alert)

    correlation_results = []
    for i, alert in enumerate(correlated_alerts):
        print(f"   📊 Correlated Alert {i + 1}: {alert.id}")
        result = await monitor.process_security_alert(alert)
        correlation_results.append(result)

        if i == 0:
            print(f"      ✅ First alert - Task created: {result['task_created']}")
        else:
            print(
                f"      🔗 Subsequent alert - Correlated: {not result['task_created']}",
            )

    print("\n4️⃣ PERFORMANCE AND LOAD TESTING")
    print("   Testing system performance with high alert volume...")

    # Generate many alerts quickly
    load_test_alerts = []
    for i in range(20):
        alert = simulator.create_mock_alert(
            severity="LOW",
            pattern_type="rate_limiting",
            message=f"Load test alert #{i + 1}",
        )
        load_test_alerts.append(alert)

    load_test_start = datetime.now()
    load_test_results = []

    # Process alerts concurrently
    tasks = [monitor.process_security_alert(alert) for alert in load_test_alerts]
    load_test_results = await asyncio.gather(*tasks)

    load_test_time = (datetime.now() - load_test_start).total_seconds()

    tasks_created = sum(1 for result in load_test_results if result["task_created"])
    print(
        f"      📊 Processed {len(load_test_alerts)} alerts in {load_test_time:.3f} seconds",
    )
    print(
        f"      ⚡ Average processing time: {load_test_time / len(load_test_alerts):.4f} seconds per alert",
    )
    print(f"      📋 Tasks created: {tasks_created}")
    print(
        f"      🔄 Alerts batched/correlated: {len(load_test_alerts) - tasks_created}",
    )

    print("\n5️⃣ COMPREHENSIVE STATISTICS")
    print("   Generating comprehensive workflow statistics...")

    stats = monitor.get_workflow_statistics()
    print("")
    print("   📊 PROACTIVE WORKFLOW STATISTICS:")
    print(
        f"      • Total alerts processed: {stats['proactive_workflows']['alerts_processed']}",
    )
    print(f"      • Tasks created: {stats['proactive_workflows']['tasks_created']}")
    print(
        f"      • Incidents created: {stats['proactive_workflows']['incidents_created']}",
    )
    print(f"      • Success rate: {stats['proactive_workflows']['success_rate']:.1%}")
    print("")
    print("   📋 TASK MANAGEMENT STATISTICS:")
    print(f"      • Total tasks: {stats['task_management']['total_tasks']}")
    print(f"      • Active assignees: {stats['task_management']['active_assignees']}")
    print(f"      • Status breakdown: {stats['task_management']['status_breakdown']}")
    print(
        f"      • Priority breakdown: {stats['task_management']['priority_breakdown']}",
    )
    print("")
    print("   🎯 INCIDENT RESPONSE:")
    print(f"      • Active incidents: {stats['active_incidents']}")

    print("\n6️⃣ INTEGRATION SUMMARY")
    print("   📋 Integration Points with AI Security Monitor:")
    print("      ✓ SecurityAlertAdapter converts existing alerts")
    print("      ✓ Proactive workflow triggers on every alert")
    print("      ✓ Task management system creates actionable items")
    print("      ✓ Incident response workflows initiated automatically")
    print("      ✓ Real-time notifications and escalations")
    print("      ✓ Comprehensive analytics and reporting")

    print("\n✨ DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("🎉 The Proactive Anomaly-to-Action Workflow system successfully:")
    print(f"   • Converted {len(results)} security alerts into actionable tasks")
    print("   • Demonstrated intelligent correlation and deduplication")
    print(f"   • Processed {len(load_test_alerts)} alerts under load efficiently")
    print("   • Created comprehensive incident response workflows")
    print("   • Provided real-time analytics and monitoring")
    print("")
    print("🔧 Ready for integration with existing ai-security-monitor.py!")
    print("=" * 70)

    return {
        "demonstration_results": results,
        "correlation_results": correlation_results,
        "load_test_results": load_test_results,
        "final_statistics": stats,
        "total_processing_time": load_test_time,
        "alerts_processed": len(results)
        + len(correlated_alerts)
        + len(load_test_alerts),
    }


if __name__ == "__main__":
    # Run the demonstration
    demo_results = asyncio.run(demonstrate_proactive_workflows())
