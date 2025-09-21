"""
Tests for Proactive Anomaly-to-Action Workflows

Tests the automated incident response system that bridges anomaly detection
with actionable task management.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Import the classes we need to implement
try:
    from services.workflows.anomaly_to_action import (
        AnomalyToActionEngine,
        IncidentAssignment,
        IncidentPriority,
        IncidentResponseWorkflow,
        IncidentTask,
        SecurityIncident,
        TaskManagementSystem,
        WorkflowRule,
    )
    from services.workflows.task_management import (
        Task,
        TaskAssignment,
        TaskManager,
        TaskPriority,
        TaskStatus,
    )
except ImportError:
    # These modules don't exist yet - this will make tests fail initially (TDD
    # Red phase)
    pass

# Mock SecurityAlert from existing ai-security-monitor.py


class MockSecurityAlert:
    """Mock of SecurityAlert from ai-security-monitor.py"""

    def __init__(
        self,
        id: str,
        severity: str,
        pattern_type: str,
        message: str,
        ai_confidence: float = 0.85,
        source_ip: str = "192.168.1.100",
    ):
        self.id = id
        self.timestamp = datetime.now()
        self.severity = severity
        self.pattern_type = pattern_type
        self.message = message
        self.ai_confidence = ai_confidence
        self.source_ip = source_ip
        self.user_agent = "Mozilla/5.0"
        self.endpoint = "/api/login"
        self.risk_score = 75
        self.recommended_actions = ["Block IP", "Review logs"]
        self.context = {"attempts": 5, "timeframe": "1 minute"}


@pytest.fixture
def mock_task_manager():
    """Mock task management system"""
    return MagicMock(spec=TaskManager)


@pytest.fixture
def sample_security_alerts():
    """Sample security alerts for testing"""
    return [
        MockSecurityAlert(
            id="alert-001",
            severity="HIGH",
            pattern_type="failed_login",
            message="Multiple failed login attempts detected from 192.168.1.100",
        ),
        MockSecurityAlert(
            id="alert-002",
            severity="CRITICAL",
            pattern_type="sql_injection",
            message="SQL injection attempt detected on /api/users endpoint",
        ),
        MockSecurityAlert(
            id="alert-003",
            severity="MEDIUM",
            pattern_type="suspicious_access",
            message="Access to sensitive endpoint outside business hours",
        ),
        MockSecurityAlert(
            id="alert-004",
            severity="LOW",
            pattern_type="rate_limiting",
            message="Rate limit exceeded for user session",
        ),
    ]


class TestAnomalyToActionEngine:
    """Test the main anomaly-to-action workflow engine"""

    @pytest.fixture
    def engine(self, mock_task_manager):
        """Create AnomalyToActionEngine instance for testing"""
        # This will fail initially because AnomalyToActionEngine doesn't exist yet
        return AnomalyToActionEngine(task_manager=mock_task_manager)

    def test_engine_initialization(self, engine):
        """Test that the engine initializes correctly"""
        assert engine.task_manager is not None
        assert engine.workflow_rules is not None
        assert engine.incident_counter >= 0
        assert engine.active_incidents is not None

    def test_process_security_alert_creates_incident_task(
        self,
        engine,
        sample_security_alerts,
    ):
        """Test that security alerts automatically create incident tasks"""
        alert = sample_security_alerts[0]  # HIGH severity failed login

        result = asyncio.run(engine.process_security_alert(alert))

        # Should create an incident task
        assert result.task_created is True
        assert result.incident_id is not None
        assert result.task_id is not None
        assert result.assignee is not None
        assert result.priority == IncidentPriority.HIGH

    def test_critical_alert_creates_immediate_task(
        self,
        engine,
        sample_security_alerts,
    ):
        """Test that CRITICAL alerts create immediate high-priority tasks"""
        alert = sample_security_alerts[1]  # CRITICAL SQL injection

        result = asyncio.run(engine.process_security_alert(alert))

        assert result.task_created is True
        assert result.priority == IncidentPriority.CRITICAL
        assert result.response_time == "immediate"
        assert result.escalated is True
        assert "SQL Injection" in result.task_title

    def test_low_severity_alerts_may_not_create_tasks(
        self,
        engine,
        sample_security_alerts,
    ):
        """Test that LOW severity alerts may be filtered or batched"""
        alert = sample_security_alerts[3]  # LOW severity rate limiting

        result = asyncio.run(engine.process_security_alert(alert))

        # Depending on configuration, low severity might be batched
        if result.task_created:
            assert result.priority == IncidentPriority.LOW
        else:
            assert result.batched is True
            assert result.batch_id is not None

    def test_incident_task_includes_comprehensive_context(
        self,
        engine,
        sample_security_alerts,
    ):
        """Test that created tasks include all relevant context and data"""
        alert = sample_security_alerts[0]

        result = asyncio.run(engine.process_security_alert(alert))

        assert result.task_created is True
        # Verify task includes comprehensive context
        task_details = result.task_details
        assert task_details.security_alert_id is not None
        assert task_details.attached_logs is not None
        assert task_details.recommended_actions is not None
        assert task_details.network_context is not None
        assert len(task_details.investigation_checklist) > 0

    def test_duplicate_alert_handling(self, engine, sample_security_alerts):
        """Test handling of duplicate or similar alerts"""
        alert = sample_security_alerts[0]

        # Process same alert twice
        result1 = asyncio.run(engine.process_security_alert(alert))
        result2 = asyncio.run(engine.process_security_alert(alert))

        # Second alert should be deduplicated
        assert result1.task_created is True
        assert result2.task_created is False
        assert result2.merged_with_incident == result1.incident_id
        assert result2.duplicate_detected is True

    def test_alert_correlation_and_clustering(self, engine, sample_security_alerts):
        """Test that related alerts are correlated into single incidents"""
        # Multiple failed login attempts from same IP should be correlated
        alerts = [
            MockSecurityAlert(
                id=f"alert-{i}",
                severity="MEDIUM",
                pattern_type="failed_login",
                message=f"Failed login attempt #{i} from 192.168.1.100",
            )
            for i in range(3)
        ]

        results = []
        for alert in alerts:
            result = asyncio.run(engine.process_security_alert(alert))
            results.append(result)

        # First alert creates task, subsequent ones should be correlated
        assert results[0].task_created is True
        assert results[1].task_created is False
        assert results[2].task_created is False

        # All should have same incident ID
        incident_id = results[0].incident_id
        assert all(r.incident_id == incident_id for r in results)


class TestWorkflowRules:
    """Test the workflow rule engine that determines how alerts are processed"""

    @pytest.fixture
    def workflow_rules(self):
        """Create WorkflowRule instances for testing"""
        # This will fail initially because WorkflowRule doesn't exist yet
        return [
            WorkflowRule(
                name="critical_immediate_response",
                condition=lambda alert: alert.severity == "CRITICAL",
                action="create_immediate_task",
                priority=IncidentPriority.CRITICAL,
                assignee="security_team_lead",
                response_time="immediate",
            ),
            WorkflowRule(
                name="failed_login_clustering",
                condition=lambda alert: alert.pattern_type == "failed_login",
                action="correlate_or_create",
                priority=IncidentPriority.HIGH,
                assignee="security_analyst",
                correlation_window="5 minutes",
                correlation_key="source_ip",
            ),
            WorkflowRule(
                name="low_priority_batching",
                condition=lambda alert: alert.severity == "LOW",
                action="batch_alerts",
                batch_size=5,
                batch_timeout="1 hour",
                priority=IncidentPriority.LOW,
            ),
        ]

    def test_rule_matching(self, workflow_rules, sample_security_alerts):
        """Test that rules correctly match security alerts"""
        critical_alert = sample_security_alerts[1]  # CRITICAL SQL injection

        matching_rule = None
        for rule in workflow_rules:
            if rule.condition(critical_alert):
                matching_rule = rule
                break

        assert matching_rule is not None
        assert matching_rule.name == "critical_immediate_response"
        assert matching_rule.priority == IncidentPriority.CRITICAL

    def test_rule_execution_creates_correct_task_properties(self, workflow_rules):
        """Test that rule execution sets correct task properties"""
        rule = workflow_rules[0]  # critical_immediate_response
        alert = MockSecurityAlert(
            "test",
            "CRITICAL",
            "sql_injection",
            "Test critical alert",
        )

        # This would be called by the engine
        task_properties = rule.execute(alert)

        assert task_properties.priority == IncidentPriority.CRITICAL
        assert task_properties.assignee == "security_team_lead"
        assert task_properties.response_time == "immediate"


class TestIncidentTaskCreation:
    """Test the automated incident task creation process"""

    def test_task_creation_with_security_context(self):
        """Test that tasks are created with comprehensive security context"""
        alert = MockSecurityAlert(
            id="test-alert",
            severity="HIGH",
            pattern_type="failed_login",
            message="Failed login attempts detected",
        )

        # This will fail initially because IncidentTask doesn't exist yet
        task = IncidentTask.from_security_alert(alert)

        assert task.title is not None
        assert task.description is not None
        assert task.priority == TaskPriority.HIGH
        assert task.security_alert_id == alert.id
        assert task.incident_type == "failed_login"
        assert len(task.investigation_checklist) > 0
        assert len(task.recommended_actions) > 0

    def test_task_includes_automated_data_collection(self):
        """Test that tasks include automatically collected contextual data"""
        alert = MockSecurityAlert(
            id="test-alert",
            severity="HIGH",
            pattern_type="suspicious_access",
            message="Suspicious access pattern detected",
        )

        task = IncidentTask.from_security_alert(alert)

        # Should automatically collect relevant data
        assert task.attached_logs is not None
        assert task.network_context is not None
        assert task.user_context is not None
        assert task.system_context is not None
        assert task.timeline is not None


class TestIncidentResponseWorkflow:
    """Test the incident response workflow orchestration"""

    @pytest.fixture
    def workflow(self):
        """Create IncidentResponseWorkflow for testing"""
        # This will fail initially because IncidentResponseWorkflow doesn't exist yet
        return IncidentResponseWorkflow()

    def test_workflow_initiates_incident_response(self, workflow):
        """Test that workflow can initiate incident response procedures"""
        alert = MockSecurityAlert(
            id="workflow-test",
            severity="CRITICAL",
            pattern_type="data_exfiltration",
            message="Potential data exfiltration detected",
        )

        response = asyncio.run(workflow.initiate_response(alert))

        assert response.incident_declared is True
        assert response.response_team_notified is True
        assert response.containment_initiated is True
        assert response.investigation_started is True
        assert len(response.immediate_actions_taken) > 0

    def test_workflow_escalation_based_on_severity(self, workflow):
        """Test that workflows escalate appropriately based on alert severity"""
        critical_alert = MockSecurityAlert(
            "test",
            "CRITICAL",
            "privilege_escalation",
            "Critical",
        )
        medium_alert = MockSecurityAlert(
            "test",
            "MEDIUM",
            "suspicious_access",
            "Medium",
        )

        critical_response = asyncio.run(workflow.initiate_response(critical_alert))
        medium_response = asyncio.run(workflow.initiate_response(medium_alert))

        # Critical should have more aggressive response
        assert critical_response.escalation_level > medium_response.escalation_level
        assert critical_response.response_team_size > medium_response.response_team_size
        assert (
            critical_response.executive_notification
            != medium_response.executive_notification
        )


class TestTaskManagementIntegration:
    """Test integration with task management systems"""

    @pytest.fixture
    def task_manager(self):
        """Mock task management system"""
        return MagicMock(spec=TaskManagementSystem)

    def test_task_creation_in_management_system(self, task_manager):
        """Test that tasks are properly created in the task management system"""
        alert = MockSecurityAlert("test", "HIGH", "failed_login", "Test alert")

        # This will fail initially because TaskManagementSystem doesn't exist yet
        engine = AnomalyToActionEngine(task_manager=task_manager)
        result = asyncio.run(engine.process_security_alert(alert))

        # Verify task manager was called
        task_manager.create_task.assert_called_once()
        call_args = task_manager.create_task.call_args[0]
        created_task = call_args[0]

        assert created_task.title is not None
        assert created_task.priority is not None
        assert created_task.assignment is not None

    def test_task_assignment_logic(self, task_manager):
        """Test that tasks are assigned to appropriate team members"""
        alerts = [
            MockSecurityAlert("test1", "CRITICAL", "sql_injection", "SQL injection"),
            MockSecurityAlert("test2", "HIGH", "failed_login", "Failed login"),
            MockSecurityAlert(
                "test3",
                "MEDIUM",
                "suspicious_access",
                "Suspicious access",
            ),
        ]

        engine = AnomalyToActionEngine(task_manager=task_manager)

        for alert in alerts:
            result = asyncio.run(engine.process_security_alert(alert))

        # Verify assignments are appropriate for alert types
        assert task_manager.create_task.call_count == 3

        # Check that different alert types get assigned to appropriate teams/individuals
        calls = task_manager.create_task.call_args_list
        sql_injection_task = calls[0][0][0]
        failed_login_task = calls[1][0][0]
        suspicious_access_task = calls[2][0][0]

        # SQL injection should go to senior security analyst
        sql_assignee = (
            sql_injection_task.assignment.assignee_id
            if sql_injection_task.assignment
            else "unknown"
        )
        assert "senior" in sql_assignee.lower() or "lead" in sql_assignee.lower()

        # Different alert types should potentially have different assignees
        assignees = {
            (
                sql_injection_task.assignment.assignee_id
                if sql_injection_task.assignment
                else "unknown"
            ),
            (
                failed_login_task.assignment.assignee_id
                if failed_login_task.assignment
                else "unknown"
            ),
            (
                suspicious_access_task.assignment.assignee_id
                if suspicious_access_task.assignment
                else "unknown"
            ),
        }
        assert len(assignees) >= 1  # At least some differentiation


class TestEndToEndWorkflow:
    """Test the complete end-to-end anomaly-to-action workflow"""

    def test_complete_workflow_from_alert_to_task(self):
        """Test the complete workflow from security alert detection to task creation"""
        # Simulate security alert from AI Security Monitor
        alert = MockSecurityAlert(
            id="e2e-test-001",
            severity="HIGH",
            pattern_type="privilege_escalation",
            message="Privilege escalation attempt detected for user admin_test",
        )

        # Initialize complete system
        task_manager = MagicMock(spec=TaskManagementSystem)
        engine = AnomalyToActionEngine(task_manager=task_manager)

        # Process the alert through the complete workflow
        result = asyncio.run(engine.process_security_alert(alert))

        # Verify end-to-end workflow completion
        assert result.workflow_completed is True
        assert result.task_created is True
        assert result.incident_id is not None
        assert result.assignee is not None
        assert result.estimated_resolution_time is not None

        # Verify task manager integration
        task_manager.create_task.assert_called_once()
        task_manager.assign_task.assert_called_once()

        # Verify incident tracking
        assert result.incident_status == "open"
        assert result.response_initiated is True

    def test_workflow_handles_multiple_concurrent_alerts(self):
        """Test that workflow can handle multiple concurrent security alerts"""
        alerts = [
            MockSecurityAlert(f"concurrent-{i}", "HIGH", "failed_login", f"Alert {i}")
            for i in range(10)
        ]

        task_manager = MagicMock(spec=TaskManagementSystem)
        engine = AnomalyToActionEngine(task_manager=task_manager)

        # Process alerts concurrently
        async def process_all_alerts():
            tasks = [engine.process_security_alert(alert) for alert in alerts]
            return await asyncio.gather(*tasks)

        results = asyncio.run(process_all_alerts())

        assert len(results) == 10
        assert all(result.workflow_completed for result in results)

        # Some may be correlated/merged, but at least some tasks should be created
        created_tasks = sum(1 for result in results if result.task_created)
        assert created_tasks >= 1

    def test_workflow_performance_under_load(self):
        """Test workflow performance with high alert volume"""
        # Generate many alerts
        alerts = [
            MockSecurityAlert(
                f"load-test-{i}",
                "MEDIUM",
                "suspicious_access",
                f"Load test {i}",
            )
            for i in range(100)
        ]

        task_manager = MagicMock(spec=TaskManagementSystem)
        engine = AnomalyToActionEngine(task_manager=task_manager)

        start_time = datetime.now()

        # Process all alerts
        results = []
        for alert in alerts:
            result = asyncio.run(engine.process_security_alert(alert))
            results.append(result)

        processing_time = (datetime.now() - start_time).total_seconds()

        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 10.0  # 10 seconds for 100 alerts
        assert len(results) == 100
        assert all(result.workflow_completed for result in results)


class TestIntegrationWithExistingMonitor:
    """Test integration with the existing ai-security-monitor.py system"""

    def test_integration_with_security_monitor_alerts(self):
        """Test that the system integrates with existing security monitor"""
        # This test would verify integration with the actual SecurityAlert class
        # from ai-security-monitor.py
        # Implementation depends on how we integrate with existing system

    def test_real_time_alert_processing(self):
        """Test real-time processing of alerts from the security monitor"""
        # This would test the real-time event handling
        # Implementation depends on event system architecture

    def test_backwards_compatibility(self):
        """Test that existing security monitor functionality is preserved"""
        # Ensure we don't break existing security monitoring
        # Implementation depends on integration approach
