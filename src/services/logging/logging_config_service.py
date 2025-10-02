#!/usr/bin/env python3
"""PAKE System - Centralized Logging Configuration Service
Centralized configuration management for enterprise logging and monitoring.

This service provides:
- Environment-based configuration
- Dynamic configuration updates
- Configuration validation
- Hot-reloading of logging settings
- Integration with external configuration sources
"""

import json
import os

# Add project root to path for imports
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.services.logging.enterprise_logging_service import (
        LogCategory,
        LoggingConfig,
        LogLevel,
        SecurityLevel,
    )
    from src.services.monitoring.enterprise_monitoring_service import (
        AlertSeverity,
        HealthStatus,
        MetricType,
        MonitoringConfig,
    )
except ImportError:
    # Fallback imports
    LoggingConfig = None
    LogLevel = None
    SecurityLevel = None
    LogCategory = None
    MonitoringConfig = None
    MetricType = None
    HealthStatus = None
    AlertSeverity = None


class Environment(Enum):
    """Environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigSource(Enum):
    """Configuration source types"""

    ENVIRONMENT = "environment"
    FILE = "file"
    DATABASE = "database"
    CONSUL = "consul"
    ETCD = "etcd"
    VAULT = "vault"


@dataclass
class LoggingServiceConfig:
    """Configuration for logging service"""

    # Basic settings
    service_name: str = "pake-system"
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    version: str = field(default_factory=lambda: os.getenv("SERVICE_VERSION", "1.0.0"))

    # Logging settings
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    json_format: bool = field(
        default_factory=lambda: os.getenv("LOG_JSON", "true").lower() == "true"
    )
    console_enabled: bool = field(
        default_factory=lambda: os.getenv("LOG_CONSOLE", "true").lower() == "true"
    )
    file_enabled: bool = field(
        default_factory=lambda: os.getenv("LOG_FILE", "true").lower() == "true"
    )

    # File settings
    log_directory: str = field(
        default_factory=lambda: os.getenv("LOG_DIRECTORY", "logs")
    )
    max_file_size_mb: int = field(
        default_factory=lambda: int(os.getenv("LOG_MAX_FILE_SIZE_MB", "100"))
    )
    backup_count: int = field(
        default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "10"))
    )

    # Security settings
    mask_sensitive_data: bool = field(
        default_factory=lambda: os.getenv("LOG_MASK_SENSITIVE", "true").lower()
        == "true"
    )
    security_level: str = field(
        default_factory=lambda: os.getenv("LOG_SECURITY_LEVEL", "internal")
    )

    # Performance settings
    async_logging: bool = field(
        default_factory=lambda: os.getenv("LOG_ASYNC", "true").lower() == "true"
    )
    buffer_size: int = field(
        default_factory=lambda: int(os.getenv("LOG_BUFFER_SIZE", "1000"))
    )
    flush_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("LOG_FLUSH_INTERVAL", "5"))
    )

    # External services
    syslog_enabled: bool = field(
        default_factory=lambda: os.getenv("LOG_SYSLOG", "false").lower() == "true"
    )
    syslog_host: str = field(
        default_factory=lambda: os.getenv("SYSLOG_HOST", "localhost")
    )
    syslog_port: int = field(
        default_factory=lambda: int(os.getenv("SYSLOG_PORT", "514"))
    )

    # Monitoring integration
    metrics_enabled: bool = field(
        default_factory=lambda: os.getenv("LOG_METRICS", "true").lower() == "true"
    )
    tracing_enabled: bool = field(
        default_factory=lambda: os.getenv("LOG_TRACING", "true").lower() == "true"
    )

    def __post_init__(self):
        """Validate configuration"""
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log level: {self.log_level}. Must be one of {valid_levels}"
            )

        # Validate security level
        valid_security_levels = ["public", "internal", "confidential", "restricted"]
        if self.security_level.lower() not in valid_security_levels:
            raise ValueError(
                f"Invalid security level: {self.security_level}. Must be one of {valid_security_levels}"
            )

        # Validate numeric values
        if self.max_file_size_mb <= 0:
            raise ValueError("Max file size must be positive")

        if self.backup_count < 0:
            raise ValueError("Backup count cannot be negative")

        if self.buffer_size <= 0:
            raise ValueError("Buffer size must be positive")

        if self.flush_interval_seconds <= 0:
            raise ValueError("Flush interval must be positive")


@dataclass
class MonitoringServiceConfig:
    """Configuration for monitoring service"""

    # Basic settings
    service_name: str = "pake-system"
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

    # Collection settings
    collection_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("MONITORING_COLLECTION_INTERVAL", "30"))
    )
    metrics_retention_days: int = field(
        default_factory=lambda: int(os.getenv("MONITORING_RETENTION_DAYS", "30"))
    )
    health_check_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("MONITORING_HEALTH_CHECK_INTERVAL", "60"))
    )

    # Thresholds
    cpu_threshold_percent: float = field(
        default_factory=lambda: float(os.getenv("MONITORING_CPU_THRESHOLD", "80.0"))
    )
    memory_threshold_percent: float = field(
        default_factory=lambda: float(os.getenv("MONITORING_MEMORY_THRESHOLD", "85.0"))
    )
    disk_threshold_percent: float = field(
        default_factory=lambda: float(os.getenv("MONITORING_DISK_THRESHOLD", "90.0"))
    )
    response_time_threshold_ms: float = field(
        default_factory=lambda: float(
            os.getenv("MONITORING_RESPONSE_TIME_THRESHOLD", "5000.0")
        )
    )

    # Alerting
    alerting_enabled: bool = field(
        default_factory=lambda: os.getenv("MONITORING_ALERTING", "true").lower()
        == "true"
    )
    alert_cooldown_minutes: int = field(
        default_factory=lambda: int(os.getenv("MONITORING_ALERT_COOLDOWN", "15"))
    )
    max_alerts_per_hour: int = field(
        default_factory=lambda: int(os.getenv("MONITORING_MAX_ALERTS_PER_HOUR", "10"))
    )

    # External services
    prometheus_enabled: bool = field(
        default_factory=lambda: os.getenv("MONITORING_PROMETHEUS", "false").lower()
        == "true"
    )
    prometheus_port: int = field(
        default_factory=lambda: int(os.getenv("PROMETHEUS_PORT", "9090"))
    )

    datadog_enabled: bool = field(
        default_factory=lambda: os.getenv("MONITORING_DATADOG", "false").lower()
        == "true"
    )
    datadog_api_key: str = field(
        default_factory=lambda: os.getenv("DATADOG_API_KEY", "")
    )
    datadog_app_key: str = field(
        default_factory=lambda: os.getenv("DATADOG_APP_KEY", "")
    )

    grafana_enabled: bool = field(
        default_factory=lambda: os.getenv("MONITORING_GRAFANA", "false").lower()
        == "true"
    )
    grafana_url: str = field(
        default_factory=lambda: os.getenv("GRAFANA_URL", "http://localhost:3000")
    )

    def __post_init__(self):
        """Validate configuration"""
        if self.collection_interval_seconds <= 0:
            raise ValueError("Collection interval must be positive")

        if self.health_check_interval_seconds <= 0:
            raise ValueError("Health check interval must be positive")

        if not (0 <= self.cpu_threshold_percent <= 100):
            raise ValueError("CPU threshold must be between 0 and 100")

        if not (0 <= self.memory_threshold_percent <= 100):
            raise ValueError("Memory threshold must be between 0 and 100")

        if not (0 <= self.disk_threshold_percent <= 100):
            raise ValueError("Disk threshold must be between 0 and 100")


class LoggingConfigService:
    """Centralized logging configuration service that manages:
    - Environment-based configuration
    - Dynamic configuration updates
    - Configuration validation
    - Hot-reloading of logging settings
    - Integration with external configuration sources
    """

    def __init__(self, config_file: str = None):
        self.config_file = config_file or "logging_config.yaml"
        self.logging_config: Optional[LoggingServiceConfig] = None
        self.monitoring_config: Optional[MonitoringServiceConfig] = None
        self.config_sources: list[ConfigSource] = [
            ConfigSource.ENVIRONMENT,
            ConfigSource.FILE,
        ]
        self.last_modified: Optional[datetime] = None

        # Load initial configuration
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from all sources"""
        try:
            # Load from environment variables first
            self.logging_config = LoggingServiceConfig()
            self.monitoring_config = MonitoringServiceConfig()

            # Load from file if it exists
            if Path(self.config_file).exists():
                self._load_from_file()

            # Validate configurations
            self._validate_configurations()

        except Exception as e:
            print(f"Failed to load configuration: {e}")
            # Use default configurations
            self.logging_config = LoggingServiceConfig()
            self.monitoring_config = MonitoringServiceConfig()

    def _load_from_file(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_file) as f:
                config_data = yaml.safe_load(f)

            if config_data:
                # Update logging config
                if "logging" in config_data:
                    logging_data = config_data["logging"]
                    for key, value in logging_data.items():
                        if hasattr(self.logging_config, key):
                            setattr(self.logging_config, key, value)

                # Update monitoring config
                if "monitoring" in config_data:
                    monitoring_data = config_data["monitoring"]
                    for key, value in monitoring_data.items():
                        if hasattr(self.monitoring_config, key):
                            setattr(self.monitoring_config, key, value)

            # Update last modified time
            self.last_modified = datetime.fromtimestamp(
                Path(self.config_file).stat().st_mtime, tz=UTC
            )

        except Exception as e:
            print(f"Failed to load configuration from file: {e}")

    def _validate_configurations(self):
        """Validate both configurations"""
        if self.logging_config:
            # Re-run post_init validation
            self.logging_config.__post_init__()

        if self.monitoring_config:
            # Re-run post_init validation
            self.monitoring_config.__post_init__()

    def get_logging_config(self) -> LoggingServiceConfig:
        """Get current logging configuration"""
        if self.logging_config is None:
            self.logging_config = LoggingServiceConfig()
        return self.logging_config

    def get_monitoring_config(self) -> MonitoringServiceConfig:
        """Get current monitoring configuration"""
        if self.monitoring_config is None:
            self.monitoring_config = MonitoringServiceConfig()
        return self.monitoring_config

    def update_logging_config(self, **kwargs):
        """Update logging configuration dynamically"""
        if self.logging_config is None:
            self.logging_config = LoggingServiceConfig()

        for key, value in kwargs.items():
            if hasattr(self.logging_config, key):
                setattr(self.logging_config, key, value)

        # Validate updated configuration
        self._validate_configurations()

    def update_monitoring_config(self, **kwargs):
        """Update monitoring configuration dynamically"""
        if self.monitoring_config is None:
            self.monitoring_config = MonitoringServiceConfig()

        for key, value in kwargs.items():
            if hasattr(self.monitoring_config, key):
                setattr(self.monitoring_config, key, value)

        # Validate updated configuration
        self._validate_configurations()

    def reload_configuration(self):
        """Reload configuration from all sources"""
        self._load_configuration()

    def check_configuration_changes(self) -> bool:
        """Check if configuration file has changed"""
        if not Path(self.config_file).exists():
            return False

        current_modified = datetime.fromtimestamp(
            Path(self.config_file).stat().st_mtime, tz=UTC
        )

        if self.last_modified is None or current_modified > self.last_modified:
            self.reload_configuration()
            return True

        return False

    def save_configuration(self, file_path: str = None):
        """Save current configuration to file"""
        save_path = file_path or self.config_file

        config_data = {
            "logging": {
                "service_name": self.logging_config.service_name,
                "environment": self.logging_config.environment,
                "version": self.logging_config.version,
                "log_level": self.logging_config.log_level,
                "json_format": self.logging_config.json_format,
                "console_enabled": self.logging_config.console_enabled,
                "file_enabled": self.logging_config.file_enabled,
                "log_directory": self.logging_config.log_directory,
                "max_file_size_mb": self.logging_config.max_file_size_mb,
                "backup_count": self.logging_config.backup_count,
                "mask_sensitive_data": self.logging_config.mask_sensitive_data,
                "security_level": self.logging_config.security_level,
                "async_logging": self.logging_config.async_logging,
                "buffer_size": self.logging_config.buffer_size,
                "flush_interval_seconds": self.logging_config.flush_interval_seconds,
                "syslog_enabled": self.logging_config.syslog_enabled,
                "syslog_host": self.logging_config.syslog_host,
                "syslog_port": self.logging_config.syslog_port,
                "metrics_enabled": self.logging_config.metrics_enabled,
                "tracing_enabled": self.logging_config.tracing_enabled,
            },
            "monitoring": {
                "service_name": self.monitoring_config.service_name,
                "environment": self.monitoring_config.environment,
                "collection_interval_seconds": self.monitoring_config.collection_interval_seconds,
                "metrics_retention_days": self.monitoring_config.metrics_retention_days,
                "health_check_interval_seconds": self.monitoring_config.health_check_interval_seconds,
                "cpu_threshold_percent": self.monitoring_config.cpu_threshold_percent,
                "memory_threshold_percent": self.monitoring_config.memory_threshold_percent,
                "disk_threshold_percent": self.monitoring_config.disk_threshold_percent,
                "response_time_threshold_ms": self.monitoring_config.response_time_threshold_ms,
                "alerting_enabled": self.monitoring_config.alerting_enabled,
                "alert_cooldown_minutes": self.monitoring_config.alert_cooldown_minutes,
                "max_alerts_per_hour": self.monitoring_config.max_alerts_per_hour,
                "prometheus_enabled": self.monitoring_config.prometheus_enabled,
                "prometheus_port": self.monitoring_config.prometheus_port,
                "datadog_enabled": self.monitoring_config.datadog_enabled,
                "datadog_api_key": self.monitoring_config.datadog_api_key,
                "datadog_app_key": self.monitoring_config.datadog_app_key,
                "grafana_enabled": self.monitoring_config.grafana_enabled,
                "grafana_url": self.monitoring_config.grafana_url,
            },
        }

        try:
            with open(save_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

            # Update last modified time
            self.last_modified = datetime.fromtimestamp(
                Path(save_path).stat().st_mtime, tz=UTC
            )

        except Exception as e:
            print(f"Failed to save configuration: {e}")

    def get_configuration_summary(self) -> dict[str, Any]:
        """Get configuration summary"""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "config_file": self.config_file,
            "last_modified": self.last_modified.isoformat()
            if self.last_modified
            else None,
            "config_sources": [source.value for source in self.config_sources],
            "logging": {
                "service_name": self.logging_config.service_name,
                "environment": self.logging_config.environment,
                "log_level": self.logging_config.log_level,
                "json_format": self.logging_config.json_format,
                "console_enabled": self.logging_config.console_enabled,
                "file_enabled": self.logging_config.file_enabled,
                "log_directory": self.logging_config.log_directory,
                "security_level": self.logging_config.security_level,
                "mask_sensitive_data": self.logging_config.mask_sensitive_data,
                "async_logging": self.logging_config.async_logging,
                "metrics_enabled": self.logging_config.metrics_enabled,
                "tracing_enabled": self.logging_config.tracing_enabled,
            },
            "monitoring": {
                "service_name": self.monitoring_config.service_name,
                "environment": self.monitoring_config.environment,
                "collection_interval_seconds": self.monitoring_config.collection_interval_seconds,
                "health_check_interval_seconds": self.monitoring_config.health_check_interval_seconds,
                "cpu_threshold_percent": self.monitoring_config.cpu_threshold_percent,
                "memory_threshold_percent": self.monitoring_config.memory_threshold_percent,
                "disk_threshold_percent": self.monitoring_config.disk_threshold_percent,
                "alerting_enabled": self.monitoring_config.alerting_enabled,
                "prometheus_enabled": self.monitoring_config.prometheus_enabled,
                "datadog_enabled": self.monitoring_config.datadog_enabled,
                "grafana_enabled": self.monitoring_config.grafana_enabled,
            },
        }

    def validate_environment(self) -> dict[str, Any]:
        """Validate current environment configuration"""
        validation_results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": self.logging_config.environment
            if self.logging_config
            else "unknown",
            "validations": [],
            "warnings": [],
            "errors": [],
        }

        # Check log directory
        if self.logging_config and self.logging_config.file_enabled:
            log_dir = Path(self.logging_config.log_directory)
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    validation_results["validations"].append(
                        "Log directory created successfully"
                    )
                except Exception as e:
                    validation_results["errors"].append(
                        f"Failed to create log directory: {e}"
                    )
            else:
                validation_results["validations"].append(
                    "Log directory exists and is accessible"
                )

        # Check external service configurations
        if self.monitoring_config:
            if self.monitoring_config.datadog_enabled:
                if not self.monitoring_config.datadog_api_key:
                    validation_results["warnings"].append(
                        "Datadog enabled but API key not configured"
                    )
                else:
                    validation_results["validations"].append(
                        "Datadog configuration appears valid"
                    )

            if self.monitoring_config.prometheus_enabled:
                validation_results["validations"].append(
                    "Prometheus monitoring enabled"
                )

            if self.monitoring_config.grafana_enabled:
                validation_results["validations"].append("Grafana integration enabled")

        # Check security settings
        if self.logging_config:
            if not self.logging_config.mask_sensitive_data:
                validation_results["warnings"].append(
                    "Sensitive data masking is disabled"
                )

            if self.logging_config.security_level.lower() == "public":
                validation_results["warnings"].append(
                    "Security level is set to public - consider using internal or higher"
                )

        return validation_results


# ========================================================================
# Global Configuration Instance
# ========================================================================

# Create global configuration instance
_global_config: Optional[LoggingConfigService] = None


def get_config_service(config_file: str = None) -> LoggingConfigService:
    """Get or create global configuration service instance"""
    global _global_config
    if _global_config is None:
        _global_config = LoggingConfigService(config_file)
    return _global_config


# Convenience functions for quick access
def get_logging_config() -> LoggingServiceConfig:
    """Get current logging configuration"""
    return get_config_service().get_logging_config()


def get_monitoring_config() -> MonitoringServiceConfig:
    """Get current monitoring configuration"""
    return get_config_service().get_monitoring_config()


def reload_configuration():
    """Reload configuration from all sources"""
    get_config_service().reload_configuration()


# ========================================================================
# Example Usage
# ========================================================================

if __name__ == "__main__":
    # Example usage
    config_service = get_config_service()

    # Get configurations
    logging_config = config_service.get_logging_config()
    monitoring_config = config_service.get_monitoring_config()

    print(f"Service: {logging_config.service_name}")
    print(f"Environment: {logging_config.environment}")
    print(f"Log Level: {logging_config.log_level}")
    print(f"JSON Format: {logging_config.json_format}")

    # Update configuration dynamically
    config_service.update_logging_config(log_level="DEBUG")

    # Save configuration to file
    config_service.save_configuration("example_logging_config.yaml")

    # Get configuration summary
    summary = config_service.get_configuration_summary()
    print(f"Configuration summary: {json.dumps(summary, indent=2)}")

    # Validate environment
    validation = config_service.validate_environment()
    print(f"Environment validation: {json.dumps(validation, indent=2)}")
