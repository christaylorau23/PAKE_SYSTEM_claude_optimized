"""
Comprehensive Test Configuration for PAKE System

This file contains all test configuration, markers, and settings
for the comprehensive testing suite.
"""

import pytest
from pathlib import Path

# Test configuration
pytest_plugins = [
    "pytest_asyncio",
    "pytest_cov",
    "pytest_mock",
    "pytest_html",
    "pytest_json_report",
]

# Test discovery
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Test markers following Testing Pyramid: Unit (70%) -> Integration (20%) -> E2E (10%)
markers = [
    # Unit Tests (70% of tests) - Fast, isolated, comprehensive
    "unit: Unit tests - test individual functions/methods in isolation",
    "unit_functional: Unit tests for normal operation paths",
    "unit_edge_case: Unit tests for boundary conditions and edge cases",
    "unit_error_handling: Unit tests for error scenarios and exception handling",
    "unit_performance: Unit tests for algorithm efficiency and performance",
    "unit_security: Unit tests for security-related functionality",

    # Integration Tests (20% of tests) - Service interactions, real dependencies
    "integration: Integration tests - test service-to-service interactions",
    "integration_database: Integration tests with database dependencies",
    "integration_cache: Integration tests with cache system",
    "integration_message_bus: Integration tests with message queue",
    "integration_api: Integration tests with external APIs",
    "integration_auth: Integration tests with authentication system",

    # End-to-End Tests (10% of tests) - Complete workflows, user journeys
    "e2e: End-to-end tests - complete user workflows",
    "e2e_user_journey: E2E tests for complete user journeys",
    "e2e_performance: E2E tests for performance under load",
    "e2e_reliability: E2E tests for system reliability",
    "e2e_user_experience: E2E tests for user experience validation",
    "e2e_security: E2E tests for security validation",

    # Test Categories
    "slow: Slow running tests (> 5 seconds)",
    "requires_db: Tests requiring database connection",
    "requires_redis: Tests requiring Redis connection",
    "requires_network: Tests requiring network access",
    "requires_external_api: Tests requiring external API access",

    # Test Types
    "smoke: Smoke tests - basic functionality verification",
    "regression: Regression tests - prevent regression of fixed bugs",
    "security: Security tests - authentication, authorization, data protection",
    "performance: Performance tests - response time, throughput, resource usage",
    "load: Load tests - system behavior under high load",
    "stress: Stress tests - system behavior under extreme conditions",
]

# Async configuration
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

# Test timeout configuration
timeout = 300  # 5 minutes default timeout
timeout_method = "thread"

# Test filtering and warnings
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
    "ignore::UserWarning:sklearn.*",
    "ignore::UserWarning:pandas.*",
    "ignore::UserWarning:matplotlib.*",
    "ignore::RuntimeWarning:asyncio.*",
    "ignore::pytest.PytestUnraisableExceptionWarning",
]

# Test discovery configuration
norecursedirs = [
    "venv", ".venv", "mcp-env", "test_env", "black_env",
    "node_modules", "dist", "build", ".git", "__pycache__",
    "security_backups", "backups", ".pytest_cache"
]

# Coverage configuration
coverage_source = ["src"]
coverage_omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
    "*/mcp-env/*",
    "*/test_env/*",
]

coverage_exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]

# Test data configuration
test_data_dir = Path(__file__).parent / "tests" / "data"
test_fixtures_dir = Path(__file__).parent / "tests" / "fixtures"

# Database configuration for tests
test_database_config = {
    "host": "localhost",
    "port": 5432,
    "database": "pake_test",
    "user": "test_user",
    "password": "test_password",
}

# Redis configuration for tests
test_redis_config = {
    "host": "localhost",
    "port": 6379,
    "db": 1,
}

# Test environment variables
test_env_vars = {
    "PAKE_ENVIRONMENT": "test",
    "PAKE_DEBUG": "true",
    "USE_VAULT": "false",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "DATABASE_URL": "postgresql://test_user:test_password@localhost:5432/pake_test",
    "REDIS_URL": "redis://localhost:6379/1",
}

# Performance test thresholds
performance_thresholds = {
    "unit_test_max_duration": 1.0,  # seconds
    "integration_test_max_duration": 5.0,  # seconds
    "e2e_test_max_duration": 30.0,  # seconds
    "api_response_max_duration": 2.0,  # seconds
    "database_query_max_duration": 1.0,  # seconds
}

# Coverage thresholds
coverage_thresholds = {
    "unit_tests": 85,  # percentage
    "integration_tests": 80,  # percentage
    "e2e_tests": 75,  # percentage
    "overall": 85,  # percentage
}

# Test categories and their expected distribution
test_distribution = {
    "unit_tests": 70,  # percentage of total tests
    "integration_tests": 20,  # percentage of total tests
    "e2e_tests": 10,  # percentage of total tests
}

# Test execution configuration
test_execution_config = {
    "parallel_workers": 4,
    "max_failures": 5,
    "retry_count": 2,
    "retry_delay": 1.0,  # seconds
    "shuffle_tests": True,
    "stop_on_first_failure": False,
}

# Test reporting configuration
test_reporting_config = {
    "html_report": True,
    "json_report": True,
    "junit_report": True,
    "coverage_report": True,
    "performance_report": True,
    "security_report": True,
}

# Test data generation configuration
test_data_config = {
    "use_factory_boy": True,
    "use_faker": True,
    "seed_data": True,
    "cleanup_after_tests": True,
    "generate_realistic_data": True,
}

# Mock configuration
mock_config = {
    "mock_external_apis": True,
    "mock_database": False,  # Use real database for integration tests
    "mock_redis": False,  # Use real Redis for integration tests
    "mock_file_system": True,
    "mock_network_calls": True,
}

# Test fixtures configuration
fixtures_config = {
    "session_scope": [
        "test_database",
        "test_redis",
        "test_environment",
    ],
    "module_scope": [
        "test_client",
        "test_data",
    ],
    "function_scope": [
        "mock_services",
        "test_user",
        "test_data",
    ],
}

# Test validation configuration
validation_config = {
    "validate_test_coverage": True,
    "validate_test_performance": True,
    "validate_test_security": True,
    "validate_test_data": True,
    "validate_test_cleanup": True,
}

# Test debugging configuration
debug_config = {
    "enable_debug_logging": True,
    "capture_logs": True,
    "save_failed_test_output": True,
    "generate_debug_reports": True,
    "enable_profiling": False,  # Enable only when needed
}

# Test maintenance configuration
maintenance_config = {
    "cleanup_old_reports": True,
    "cleanup_old_coverage": True,
    "cleanup_test_data": True,
    "archive_failed_tests": True,
    "generate_test_metrics": True,
}

# Export configuration for use in tests
__all__ = [
    "testpaths",
    "python_files",
    "python_classes",
    "python_functions",
    "markers",
    "asyncio_mode",
    "asyncio_default_fixture_loop_scope",
    "timeout",
    "timeout_method",
    "filterwarnings",
    "norecursedirs",
    "coverage_source",
    "coverage_omit",
    "coverage_exclude_lines",
    "test_data_dir",
    "test_fixtures_dir",
    "test_database_config",
    "test_redis_config",
    "test_env_vars",
    "performance_thresholds",
    "coverage_thresholds",
    "test_distribution",
    "test_execution_config",
    "test_reporting_config",
    "test_data_config",
    "mock_config",
    "fixtures_config",
    "validation_config",
    "debug_config",
    "maintenance_config",
]
