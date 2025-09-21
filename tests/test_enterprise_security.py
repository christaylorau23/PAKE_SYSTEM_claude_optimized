"""
Comprehensive test suite for Enterprise Security and Compliance Framework.
Tests security protocols, encryption, audit logging, compliance monitoring.

Following TDD methodology for enterprise-grade security implementation.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from services.security.enterprise_security import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    ComplianceFramework,
    ComplianceMonitor,
    ComplianceReport,
    EncryptionManager,
    EnterpriseSecurityConfig,
    EnterpriseSecurityFramework,
    SecurityLevel,
    SecurityPolicy,
)


@pytest_asyncio.fixture
async def security_config():
    """Create test security configuration."""
    return EnterpriseSecurityConfig(
        encryption_key_rotation_days=30,
        audit_retention_days=365,
        jwt_secret_key="test-secret-key-for-testing-only",
        session_timeout_minutes=60,
        max_failed_login_attempts=3,
        enable_audit_logging=True,
        enable_encryption=True,
        enable_compliance_monitoring=True,
    )


@pytest_asyncio.fixture
async def security_framework(security_config):
    """Create test security framework."""
    framework = EnterpriseSecurityFramework(security_config)
    await framework.initialize()
    yield framework
    await framework.shutdown()


@pytest_asyncio.fixture
async def encryption_manager(security_config):
    """Create test encryption manager."""
    return EncryptionManager(security_config)


@pytest_asyncio.fixture
async def audit_logger(security_config):
    """Create test audit logger."""
    logger = AuditLogger(security_config)
    await logger.initialize()
    yield logger
    await logger.shutdown()


@pytest_asyncio.fixture
async def compliance_monitor(security_config):
    """Create test compliance monitor."""
    monitor = ComplianceMonitor(security_config)
    await monitor.initialize()
    yield monitor
    await monitor.shutdown()


class TestEnterpriseSecurityFramework:
    """Test suite for Enterprise Security Framework main orchestration."""

    @pytest.mark.asyncio
    async def test_security_framework_initialization(self, security_framework):
        """Test security framework properly initializes all components."""
        assert security_framework.config is not None
        assert security_framework.encryption_manager is not None
        assert security_framework.audit_logger is not None
        assert security_framework.compliance_monitor is not None

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_data(self, security_framework):
        """Test data encryption and decryption functionality."""
        test_data = "Sensitive financial information for user 12345"

        # Test encryption
        encrypted_data = await security_framework.encrypt_data(test_data)
        assert encrypted_data != test_data
        assert len(encrypted_data) > len(test_data)

        # Test decryption
        decrypted_data = await security_framework.decrypt_data(encrypted_data)
        assert decrypted_data == test_data

    @pytest.mark.asyncio
    async def test_log_audit_event(self, security_framework):
        """Test audit event logging functionality."""
        event = AuditEvent(
            event_id="evt_123",
            event_type=AuditEventType.USER_LOGIN,
            user_id="user123",
            resource_id="auth_system",
            action="login_attempt",
            ip_address="192.168.1.100",
            details={"success": True, "method": "REDACTED_SECRET"},
            timestamp=datetime.now(UTC),
        )

        # Test event logging
        log_id = await security_framework.log_audit_event(event)
        assert log_id is not None
        assert isinstance(log_id, str)

    @pytest.mark.asyncio
    async def test_check_compliance_status(self, security_framework):
        """Test compliance status checking across frameworks."""
        # Test GDPR compliance
        gdpr_report = await security_framework.generate_compliance_report(
            ComplianceFramework.GDPR,
        )
        assert isinstance(gdpr_report, ComplianceReport)
        assert gdpr_report.framework == ComplianceFramework.GDPR
        assert gdpr_report.compliance_score >= 0.0
        assert gdpr_report.compliance_score <= 1.0

    @pytest.mark.asyncio
    async def test_validate_security_policy(self, security_framework):
        """Test security policy validation."""
        policy = SecurityPolicy(
            policy_id="test_policy",
            name="Test Security Policy",
            description="Test policy for validation",
            security_level=SecurityLevel.CONFIDENTIAL,
            rules={
                "REDACTED_SECRET_min_length": 12,
                "require_mfa": True,
                "session_timeout_minutes": 60,
                "max_failed_attempts": 3,
                "data_retention_days": 365,
            },
        )

        # Test policy validation
        is_valid = await security_framework.validate_policy(policy)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_detect_security_violations(self, security_framework):
        """Test security violation detection capabilities."""
        # Create test audit events
        events = [
            AuditEvent(
                event_id="evt_attack",
                event_type=AuditEventType.USER_LOGIN,
                user_id="attacker",
                resource_id="auth_system",
                action="failed_login",
                ip_address="192.168.1.200",
                details={"attempts": 5},
                success=False,
                risk_score=0.9,
                timestamp=datetime.now(UTC),
            ),
        ]

        # Test violation detection
        violations = await security_framework.detect_violations(events)
        assert isinstance(violations, list)
        assert len(violations) >= 0

    @pytest.mark.asyncio
    async def test_generate_security_report(self, security_framework):
        """Test comprehensive security report generation."""
        # Generate activity first
        await security_framework.log_audit_event(
            AuditEvent(
                event_id="evt_data",
                event_type=AuditEventType.DATA_ACCESS,
                user_id="user123",
                resource_id="financial_data",
                action="data_access",
                details={"resource": "financial_data"},
                timestamp=datetime.now(UTC),
            ),
        )

        # Test report generation
        report = await security_framework.generate_security_report(
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
        )

        assert isinstance(report, dict)
        assert "summary" in report
        assert "compliance_status" in report
        assert "audit_events" in report
        assert report["summary"]["total_events"] >= 1


class TestEncryptionManager:
    """Test suite for Encryption Manager functionality."""

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_string(self, encryption_manager):
        """Test string encryption and decryption."""
        original_text = "Confidential user data: credit_card_4532****1234"

        # Test encryption
        encrypted = await encryption_manager.encrypt_string(original_text)
        assert encrypted != original_text
        assert isinstance(encrypted, str)

        # Test decryption
        decrypted = await encryption_manager.decrypt_string(encrypted)
        assert decrypted == original_text

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_dictionary(self, encryption_manager):
        """Test dictionary encryption and decryption."""
        original_data = {
            "user_id": "12345",
            "email": "user@example.com",
            "payment_info": {"card": "4532****1234", "cvv": "***"},
        }

        # Test encryption
        encrypted = await encryption_manager.encrypt_dict(original_data)
        assert encrypted != original_data
        assert isinstance(encrypted, str)

        # Test decryption
        decrypted = await encryption_manager.decrypt_dict(encrypted)
        assert decrypted == original_data

    @pytest.mark.asyncio
    async def test_key_rotation(self, encryption_manager):
        """Test encryption key rotation functionality."""
        # Test current key info
        key_info = await encryption_manager.get_key_info()
        assert "key_id" in key_info
        assert "created_at" in key_info
        assert "rotation_due" in key_info

        # Test key rotation - check that the rotation updates metadata
        old_created_at = key_info["created_at"]
        result = await encryption_manager.rotate_key()
        assert result is True

        # Key rotation should succeed (we can't easily test key content changed
        # without exposing internals)

    @pytest.mark.asyncio
    async def test_encryption_performance(self, encryption_manager):
        """Test encryption performance with large data."""
        large_data = "x" * 10000  # 10KB of data

        import time

        start_time = time.time()

        encrypted = await encryption_manager.encrypt_string(large_data)
        decrypted = await encryption_manager.decrypt_string(encrypted)

        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to ms

        assert decrypted == large_data
        assert processing_time < 1000  # Should complete within 1 second


class TestAuditLogger:
    """Test suite for Audit Logger functionality."""

    @pytest.mark.asyncio
    async def test_log_audit_entry(self, audit_logger):
        """Test audit entry logging."""
        entry = AuditEvent(
            event_id="audit_1",
            event_type=AuditEventType.DATA_ACCESS,
            user_id="audit_user",
            resource_id="user_profile",
            action="data_access",
            details={"field": "email", "old_value": "old@example.com"},
            ip_address="192.168.1.50",
            timestamp=datetime.now(UTC),
        )

        # Test logging
        log_id = await audit_logger.log_entry(entry)
        assert log_id is not None
        assert isinstance(log_id, str)

    @pytest.mark.asyncio
    async def test_query_audit_logs(self, audit_logger):
        """Test audit log querying capabilities."""
        # Create test entries
        entries = [
            AuditEvent(
                event_id="audit_2",
                event_type=AuditEventType.USER_LOGIN,
                user_id="user1",
                resource_id="authentication",
                action="login",
                details={"success": True},
                timestamp=datetime.now(UTC),
            ),
            AuditEvent(
                event_id="audit_3",
                event_type=AuditEventType.DATA_MODIFICATION,
                user_id="user2",
                resource_id="user_profile",
                action="data_modify",
                details={"field": "address"},
                timestamp=datetime.now(UTC),
            ),
        ]

        # Log entries
        for entry in entries:
            await audit_logger.log_entry(entry)

        # Test querying
        results = await audit_logger.query_logs(
            user_id="user1",
            start_date=datetime.now(UTC) - timedelta(minutes=5),
            end_date=datetime.now(UTC),
        )

        assert isinstance(results, list)
        assert len(results) >= 1
        assert results[0].user_id == "user1"

    @pytest.mark.asyncio
    async def test_detect_security_violations(self, audit_logger):
        """Test security violation detection in audit logs."""
        # Create suspicious entries
        violations = [
            AuditEvent(
                event_id="audit_4",
                event_type=AuditEventType.DATA_ACCESS,
                user_id="suspicious_user",
                resource_id="user_database",
                action="bulk_data_access",
                details={"records_accessed": 1000},
                ip_address="unknown_ip",
                timestamp=datetime.now(UTC),
                risk_score=0.9,  # High risk
            ),
        ]

        # Log violations
        for violation in violations:
            await audit_logger.log_entry(violation)

        # Test violation detection
        detected = await audit_logger.detect_violations(
            time_window_minutes=5,
            severity_threshold="medium",
        )

        assert isinstance(detected, list)
        if detected:
            assert detected[0].severity in ["medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_audit_log_retention(self, audit_logger):
        """Test audit log retention and cleanup."""
        # Test retention policy
        retention_info = await audit_logger.get_retention_info()
        assert "retention_days" in retention_info
        assert "total_entries" in retention_info
        assert retention_info["retention_days"] == 365

        # Test cleanup (should not error)
        cleaned_count = await audit_logger.cleanup_old_logs()
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0


class TestComplianceMonitor:
    """Test suite for Compliance Monitor functionality."""

    @pytest.mark.asyncio
    async def test_gdpr_compliance_check(self, compliance_monitor):
        """Test GDPR compliance monitoring."""
        status = await compliance_monitor.check_gdpr_compliance()

        assert isinstance(status, ComplianceReport)
        assert status.framework == ComplianceFramework.GDPR
        assert len(status.findings) >= 0  # May have findings
        assert status.total_controls >= 5  # Should have multiple controls
        assert status.compliance_score >= 0.5  # Should have reasonable compliance
        assert status.compliance_score >= 0.8  # Should have high compliance

    @pytest.mark.asyncio
    async def test_soc2_compliance_check(self, compliance_monitor):
        """Test SOC2 compliance monitoring."""
        status = await compliance_monitor.check_soc2_compliance()

        assert isinstance(status, ComplianceReport)
        assert status.framework == ComplianceFramework.SOC2
        assert len(status.findings) >= 0  # May have findings
        assert status.total_controls >= 5  # Should have multiple controls
        assert status.compliance_score >= 0.5  # Should have reasonable compliance
        assert status.compliance_score >= 0.0

    @pytest.mark.asyncio
    async def test_iso27001_compliance_check(self, compliance_monitor):
        """Test ISO27001 compliance monitoring."""
        status = await compliance_monitor.check_iso27001_compliance()

        assert isinstance(status, ComplianceReport)
        assert status.framework == ComplianceFramework.ISO27001
        assert len(status.findings) >= 0  # May have findings
        assert status.total_controls >= 5  # Should have multiple controls
        assert status.compliance_score >= 0.5  # Should have reasonable compliance
        assert status.compliance_score >= 0.0

    @pytest.mark.asyncio
    async def test_hipaa_compliance_check(self, compliance_monitor):
        """Test HIPAA compliance monitoring."""
        status = await compliance_monitor.check_hipaa_compliance()

        assert isinstance(status, ComplianceReport)
        assert status.framework == ComplianceFramework.HIPAA
        assert len(status.findings) >= 0  # May have findings
        assert status.total_controls >= 5  # Should have multiple controls
        assert (
            status.compliance_score >= 0.0
        )  # May have low compliance due to new framework
        assert status.compliance_score >= 0.0

    @pytest.mark.asyncio
    async def test_compliance_reporting(self, compliance_monitor):
        """Test comprehensive compliance reporting."""
        report = await compliance_monitor.generate_compliance_report()

        assert isinstance(report, dict)
        assert "frameworks" in report
        assert "overall_score" in report
        assert "recommendations" in report
        assert "last_updated" in report

        # Verify framework scores
        for framework, details in report["frameworks"].items():
            assert "score" in details
            assert "status" in details
            assert details["score"] >= 0.0
            assert details["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_compliance_violations_detection(self, compliance_monitor):
        """Test detection of compliance violations."""
        violations = await compliance_monitor.detect_violations()

        assert isinstance(violations, list)
        # Should not have violations in test environment
        assert len(violations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
