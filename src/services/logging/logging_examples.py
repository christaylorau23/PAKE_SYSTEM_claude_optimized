#!/usr/bin/env python3
"""
PAKE System - Logging and Monitoring Examples
Comprehensive examples demonstrating enterprise logging and monitoring best practices.

This module provides:
- Basic logging examples
- Advanced structured logging
- Security-aware logging
- Performance monitoring
- Audit logging
- Error handling and alerting
"""

import asyncio
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, Any

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.services.logging.enterprise_logging_service import (
        EnterpriseLoggingService,
        LoggingConfig,
        LogLevel,
        LogCategory,
        SecurityLevel,
        get_logger
    )
    from src.services.monitoring.enterprise_monitoring_service import (
        EnterpriseMonitoringService,
        MonitoringConfig,
        MetricType,
        HealthStatus,
        AlertSeverity,
        get_monitor
    )
    from src.services.logging.logging_config_service import (
        LoggingConfigService,
        get_config_service
    )
except ImportError:
    print("Warning: Could not import enterprise logging services. Using fallback examples.")
    EnterpriseLoggingService = None
    LoggingConfig = None
    LogLevel = None
    LogCategory = None
    SecurityLevel = None
    get_logger = None
    EnterpriseMonitoringService = None
    MonitoringConfig = None
    MetricType = None
    HealthStatus = None
    AlertSeverity = None
    get_monitor = None
    LoggingConfigService = None
    get_config_service = None


class LoggingExamples:
    """Comprehensive examples of enterprise logging and monitoring"""
    
    def __init__(self):
        self.logger = get_logger() if get_logger else None
        self.monitor = get_monitor() if get_monitor else None
        self.config_service = get_config_service() if get_config_service else None
    
    # ========================================================================
    # Basic Logging Examples
    # ========================================================================
    
    def example_basic_logging(self):
        """Example of basic logging with different levels"""
        if not self.logger:
            print("Logger not available - skipping basic logging example")
            return
        
        print("=== Basic Logging Examples ===")
        
        # Basic log levels
        self.logger.debug("This is a debug message", extra_data={"debug_info": "detailed debugging info"})
        self.logger.info("Service started successfully", version="1.0.0", port=8080)
        self.logger.warning("High memory usage detected", memory_percent=85.5)
        self.logger.error("Database connection failed", error_code="DB_CONN_001")
        self.logger.critical("System is shutting down", reason="critical_error")
        
        print("Basic logging examples completed")
    
    def example_structured_logging(self):
        """Example of structured logging with context"""
        if not self.logger:
            print("Logger not available - skipping structured logging example")
            return
        
        print("=== Structured Logging Examples ===")
        
        # Context-based logging
        with self.logger.with_correlation_id("req-12345"):
            self.logger.info("Request processing started")
            
            with self.logger.with_user("user123", "john_doe"):
                self.logger.info("User action performed", action="login", ip="192.168.1.100")
            
            with self.logger.with_request(
                request_id="req-12345",
                method="POST",
                path="/api/v1/users",
                ip="192.168.1.100",
                user_agent="Mozilla/5.0..."
            ):
                self.logger.info("API request received")
        
        print("Structured logging examples completed")
    
    def example_security_logging(self):
        """Example of security-aware logging"""
        if not self.logger:
            print("Logger not available - skipping security logging example")
            return
        
        print("=== Security Logging Examples ===")
        
        # Security events
        self.logger.security(
            "User login attempt",
            event="login",
            user_id="user123",
            ip="192.168.1.100",
            user_agent="Mozilla/5.0...",
            success=True,
            reason="valid_credentials"
        )
        
        self.logger.security(
            "Failed login attempt",
            event="login",
            user_id="user123",
            ip="192.168.1.100",
            success=False,
            reason="invalid_REDACTED_SECRET"
        )
        
        # Audit logging
        self.logger.audit(
            "User accessed sensitive resource",
            event_type="resource_access",
            action="read",
            result="success",
            user_id="user123",
            resource="/api/documents/confidential/123"
        )
        
        # Sensitive data masking example
        sensitive_data = {
            "username": "john_doe",
            "REDACTED_SECRET": "secret123",
            "api_key": "sk-1234567890abcdef",
            "credit_card": "4111-1111-1111-1111",
            "email": "john@example.com"
        }
        
        self.logger.info(
            "Processing user data",
            user_data=sensitive_data  # This will be automatically masked
        )
        
        print("Security logging examples completed")
    
    def example_performance_logging(self):
        """Example of performance monitoring and logging"""
        if not self.logger:
            print("Logger not available - skipping performance logging example")
            return
        
        print("=== Performance Logging Examples ===")
        
        # Performance metrics
        self.logger.performance(
            "Database query completed",
            operation="SELECT",
            duration_ms=150.5,
            memory_mb=25.3,
            cpu_percent=12.5
        )
        
        # API performance
        self.logger.api(
            "API request processed",
            method="GET",
            path="/api/v1/users",
            status_code=200,
            duration_ms=250.0,
            user_id="user123"
        )
        
        # Database operations
        self.logger.database(
            "Query executed",
            operation="INSERT",
            table="users",
            duration_ms=45.2,
            row_count=1
        )
        
        # Timer context manager
        async def example_async_operation():
            async with self.logger.timer("expensive_operation"):
                await asyncio.sleep(0.1)  # Simulate work
                return "operation completed"
        
        # Decorator usage
        @self.logger.trace_operation("data_processing")
        def process_data():
            time.sleep(0.05)  # Simulate work
            return "processed"
        
        print("Performance logging examples completed")
    
    def example_business_logging(self):
        """Example of business event logging"""
        if not self.logger:
            print("Logger not available - skipping business logging example")
            return
        
        print("=== Business Logging Examples ===")
        
        # Business events
        self.logger.business(
            "User created new document",
            event="document_created",
            user_id="user123",
            entity_type="document",
            entity_id="doc-456",
            action="create",
            metadata={
                "document_type": "contract",
                "file_size": "2.5MB",
                "template_used": "standard_contract"
            }
        )
        
        self.logger.business(
            "Payment processed",
            event="payment_processed",
            user_id="user123",
            entity_type="payment",
            entity_id="pay-789",
            action="process",
            metadata={
                "amount": 99.99,
                "currency": "USD",
                "payment_method": "credit_card",
                "transaction_id": "txn-abc123"
            }
        )
        
        print("Business logging examples completed")
    
    # ========================================================================
    # Monitoring Examples
    # ========================================================================
    
    def example_monitoring_metrics(self):
        """Example of monitoring metrics collection"""
        if not self.monitor:
            print("Monitor not available - skipping monitoring examples")
            return
        
        print("=== Monitoring Examples ===")
        
        # Custom metrics
        self.monitor.increment_counter("requests.total")
        self.monitor.increment_counter("requests.success", tags={"endpoint": "/api/v1/users"})
        self.monitor.increment_counter("requests.error", tags={"error_type": "validation_error"})
        
        self.monitor.set_gauge("active_connections", 25)
        self.monitor.set_gauge("queue_size", 150)
        
        self.monitor.record_timing("database.query", 150.5, tags={"table": "users"})
        self.monitor.record_timing("api.response", 250.0, tags={"endpoint": "/api/v1/users"})
        
        # Error tracking
        self.monitor.record_error("database_connection_error")
        self.monitor.record_error("validation_error", tags={"field": "email"})
        
        print("Monitoring examples completed")
    
    def example_health_checks(self):
        """Example of health check registration"""
        if not self.monitor:
            print("Monitor not available - skipping health check examples")
            return
        
        print("=== Health Check Examples ===")
        
        # Register health checks
        self.monitor.register_health_check("database")
        self.monitor.register_health_check("redis")
        self.monitor.register_health_check("api")
        
        # Custom health check function
        def custom_health_check():
            # Simulate health check logic
            return {
                "status": "healthy",
                "message": "Custom service is running",
                "details": {"uptime": "24h", "version": "1.0.0"}
            }
        
        self.monitor.register_health_check("custom_service", custom_health_check)
        
        print("Health check examples completed")
    
    def example_alerting(self):
        """Example of alert creation and management"""
        if not self.monitor:
            print("Monitor not available - skipping alerting examples")
            return
        
        print("=== Alerting Examples ===")
        
        # Create alerts
        alert_id = self.monitor.create_alert(
            title="High CPU Usage",
            message="CPU usage is above 90%",
            severity=AlertSeverity.HIGH,
            tags={"metric": "cpu_percent", "threshold": "90%"}
        )
        
        self.monitor.create_alert(
            title="Database Connection Failed",
            message="Unable to connect to primary database",
            severity=AlertSeverity.CRITICAL,
            tags={"service": "database", "instance": "primary"}
        )
        
        # Resolve alert
        asyncio.create_task(self.monitor.resolve_alert(
            alert_id,
            "CPU usage returned to normal levels"
        ))
        
        print("Alerting examples completed")
    
    # ========================================================================
    # Configuration Examples
    # ========================================================================
    
    def example_configuration_management(self):
        """Example of configuration management"""
        if not self.config_service:
            print("Config service not available - skipping configuration examples")
            return
        
        print("=== Configuration Examples ===")
        
        # Get current configuration
        logging_config = self.config_service.get_logging_config()
        monitoring_config = self.config_service.get_monitoring_config()
        
        print(f"Current log level: {logging_config.log_level}")
        print(f"Current environment: {logging_config.environment}")
        print(f"CPU threshold: {monitoring_config.cpu_threshold_percent}%")
        
        # Update configuration dynamically
        self.config_service.update_logging_config(log_level="DEBUG")
        self.config_service.update_monitoring_config(cpu_threshold_percent=75.0)
        
        # Get configuration summary
        summary = self.config_service.get_configuration_summary()
        print(f"Configuration summary: {summary['logging']['log_level']}")
        
        # Validate environment
        validation = self.config_service.validate_environment()
        print(f"Environment validation: {len(validation['validations'])} validations passed")
        
        print("Configuration examples completed")
    
    # ========================================================================
    # Real-world Integration Examples
    # ========================================================================
    
    def example_web_application_logging(self):
        """Example of logging in a web application context"""
        if not self.logger:
            print("Logger not available - skipping web application example")
            return
        
        print("=== Web Application Logging Example ===")
        
        # Simulate web request processing
        request_id = str(uuid.uuid4())
        user_id = "user123"
        
        with self.logger.with_correlation_id(request_id):
            # Request received
            self.logger.info(
                "HTTP request received",
                category=LogCategory.API,
                method="POST",
                path="/api/v1/users",
                user_id=user_id,
                ip="192.168.1.100"
            )
            
            # Authentication
            self.logger.security(
                "User authentication",
                event="auth",
                user_id=user_id,
                success=True,
                ip="192.168.1.100"
            )
            
            # Business logic
            self.logger.business(
                "User creation initiated",
                event="user_creation",
                user_id=user_id,
                entity_type="user",
                action="create"
            )
            
            # Database operation
            self.logger.database(
                "User record created",
                operation="INSERT",
                table="users",
                duration_ms=45.2,
                row_count=1
            )
            
            # Response
            self.logger.api(
                "HTTP response sent",
                method="POST",
                path="/api/v1/users",
                status_code=201,
                duration_ms=250.0,
                user_id=user_id
            )
        
        print("Web application logging example completed")
    
    def example_error_handling_and_recovery(self):
        """Example of comprehensive error handling and recovery"""
        if not self.logger or not self.monitor:
            print("Services not available - skipping error handling example")
            return
        
        print("=== Error Handling and Recovery Example ===")
        
        try:
            # Simulate an operation that might fail
            result = self._simulate_risky_operation()
            
            self.logger.info(
                "Operation completed successfully",
                result=result,
                category=LogCategory.APPLICATION
            )
            
        except ValueError as e:
            # Log the error
            self.logger.error(
                "Validation error occurred",
                category=LogCategory.APPLICATION,
                error=e,
                error_code="VALIDATION_ERROR"
            )
            
            # Record error metric
            self.monitor.record_error("validation_error", {"field": "email"})
            
            # Create alert if needed
            self.monitor.create_alert(
                title="Validation Error Spike",
                message="Multiple validation errors detected",
                severity=AlertSeverity.MEDIUM,
                tags={"error_type": "validation_error"}
            )
            
        except ConnectionError as e:
            # Log connection error
            self.logger.error(
                "Database connection failed",
                category=LogCategory.DATABASE,
                error=e,
                error_code="DB_CONN_ERROR"
            )
            
            # Record error metric
            self.monitor.record_error("database_connection_error")
            
            # Create critical alert
            self.monitor.create_alert(
                title="Database Connection Failure",
                message="Unable to connect to database",
                severity=AlertSeverity.CRITICAL,
                tags={"service": "database"}
            )
            
        except Exception as e:
            # Log unexpected error
            self.logger.critical(
                "Unexpected error occurred",
                category=LogCategory.APPLICATION,
                error=e,
                error_code="UNEXPECTED_ERROR"
            )
            
            # Record error metric
            self.monitor.record_error("unexpected_error", {"error_type": type(e).__name__})
            
            # Create critical alert
            self.monitor.create_alert(
                title="Unexpected System Error",
                message=f"Unexpected error: {str(e)}",
                severity=AlertSeverity.CRITICAL,
                tags={"error_type": type(e).__name__}
            )
        
        print("Error handling and recovery example completed")
    
    def _simulate_risky_operation(self):
        """Simulate an operation that might fail"""
        import random
        
        # Randomly fail with different error types
        failure_type = random.choice(["none", "validation", "connection", "unexpected"])
        
        if failure_type == "validation":
            raise ValueError("Invalid email format")
        elif failure_type == "connection":
            raise ConnectionError("Database connection timeout")
        elif failure_type == "unexpected":
            raise RuntimeError("Unexpected system error")
        
        return "Operation successful"
    
    # ========================================================================
    # Reporting Examples
    # ========================================================================
    
    def example_reporting(self):
        """Example of generating reports from logs and metrics"""
        if not self.logger or not self.monitor:
            print("Services not available - skipping reporting example")
            return
        
        print("=== Reporting Examples ===")
        
        # Generate compliance report
        compliance_report = self.logger.generate_compliance_report(days=7)
        print(f"Compliance report: {compliance_report['summary']['total_audit_events']} audit events")
        
        # Generate monitoring report
        monitoring_report = self.monitor.generate_monitoring_report()
        print(f"Monitoring report: {monitoring_report['system_metrics']['cpu']['current']}% CPU usage")
        
        # Get performance summary
        performance_summary = self.monitor.get_performance_summary()
        print(f"Performance summary: {len(performance_summary)} operations tracked")
        
        # Get health summary
        health_summary = self.monitor.get_health_summary()
        print(f"Health summary: {health_summary['health_percentage']}% healthy")
        
        print("Reporting examples completed")
    
    # ========================================================================
    # Run All Examples
    # ========================================================================
    
    async def run_all_examples(self):
        """Run all logging and monitoring examples"""
        print("Starting PAKE System Logging and Monitoring Examples")
        print("=" * 60)
        
        # Basic examples
        self.example_basic_logging()
        print()
        
        self.example_structured_logging()
        print()
        
        self.example_security_logging()
        print()
        
        self.example_performance_logging()
        print()
        
        self.example_business_logging()
        print()
        
        # Monitoring examples
        self.example_monitoring_metrics()
        print()
        
        self.example_health_checks()
        print()
        
        self.example_alerting()
        print()
        
        # Configuration examples
        self.example_configuration_management()
        print()
        
        # Real-world examples
        self.example_web_application_logging()
        print()
        
        self.example_error_handling_and_recovery()
        print()
        
        # Reporting examples
        self.example_reporting()
        print()
        
        print("=" * 60)
        print("All examples completed successfully!")
        
        # Cleanup
        if self.monitor:
            await self.monitor.stop_monitoring()


# ========================================================================
# Main Execution
# ========================================================================

async def main():
    """Main function to run examples"""
    examples = LoggingExamples()
    await examples.run_all_examples()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
