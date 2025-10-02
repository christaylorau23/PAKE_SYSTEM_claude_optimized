#!/usr/bin/env python3
"""Secure Network Configuration for PAKE System
Replaces insecure 0.0.0.0 bindings with secure alternatives
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment types for network configuration"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class NetworkSecurityConfig:
    """Secure network configuration"""

    environment: Environment
    allowed_hosts: list[str]
    bind_address: str
    port: int
    enable_ssl: bool = True
    enable_cors: bool = True
    cors_origins: Optional[list[str]] = None
    enable_rate_limiting: bool = True
    max_connections: int = 1000
    timeout_seconds: int = 30


class SecureNetworkConfig:
    """Secure network configuration manager
    Provides environment-appropriate network settings
    """

    def __init__(self, environment: Environment | None = None):
        self.environment = environment or self._detect_environment()
        self.config = self._get_secure_config()

    def _detect_environment(self) -> Environment:
        """Detect environment from environment variables"""
        env_str = os.getenv("PAKE_ENVIRONMENT", "development").lower()

        if env_str in ["prod", "production"]:
            return Environment.PRODUCTION
        if env_str in ["staging", "stage"]:
            return Environment.STAGING
        return Environment.DEVELOPMENT

    def _get_secure_config(self) -> NetworkSecurityConfig:
        """Get secure network configuration based on environment"""
        if self.environment == Environment.PRODUCTION:
            return NetworkSecurityConfig(
                environment=self.environment,
                allowed_hosts=self._get_production_hosts(),
                bind_address=self._get_production_bind_address(),
                port=int(os.getenv("PAKE_PORT", "8000")),
                enable_ssl=True,
                enable_cors=True,
                cors_origins=self._get_production_cors_origins(),
                enable_rate_limiting=True,
                max_connections=2000,
                timeout_seconds=30,
            )

        if self.environment == Environment.STAGING:
            return NetworkSecurityConfig(
                environment=self.environment,
                allowed_hosts=self._get_staging_hosts(),
                bind_address=self._get_staging_bind_address(),
                port=int(os.getenv("PAKE_PORT", "8000")),
                enable_ssl=True,
                enable_cors=True,
                cors_origins=self._get_staging_cors_origins(),
                enable_rate_limiting=True,
                max_connections=1000,
                timeout_seconds=30,
            )

        # DEVELOPMENT
        return NetworkSecurityConfig(
            environment=self.environment,
            allowed_hosts=["localhost", "127.0.0.1"],
            bind_address="127.0.0.1",  # Secure: only localhost
            port=int(os.getenv("PAKE_PORT", "8000")),
            enable_ssl=False,  # OK for development
            enable_cors=True,
            cors_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            enable_rate_limiting=False,  # OK for development
            max_connections=100,
            timeout_seconds=60,
        )

    def _get_production_hosts(self) -> list[str]:
        """Get production allowed hosts"""
        hosts_str = os.getenv("PAKE_ALLOWED_HOSTS", "")
        if hosts_str:
            return [host.strip() for host in hosts_str.split(",") if host.strip()]

        # Default production hosts - should be configured via environment
        return ["api.pake.example.com", "pake.example.com", "*.pake.example.com"]

    def _get_staging_hosts(self) -> list[str]:
        """Get staging allowed hosts"""
        hosts_str = os.getenv("PAKE_STAGING_HOSTS", "")
        if hosts_str:
            return [host.strip() for host in hosts_str.split(",") if host.strip()]

        return ["staging-api.pake.example.com", "staging.pake.example.com"]

    def _get_production_bind_address(self) -> str:
        """Get production bind address"""
        bind_addr = os.getenv("PAKE_BIND_ADDRESS")
        if bind_addr:
            return bind_addr

        # Production should bind to specific interface, not 0.0.0.0
        # This should be configured via environment variable
        logger.warning("PAKE_BIND_ADDRESS not set for production! Using localhost")
        return "127.0.0.1"

    def _get_staging_bind_address(self) -> str:
        """Get staging bind address"""
        bind_addr = os.getenv("PAKE_STAGING_BIND_ADDRESS")
        if bind_addr:
            return bind_addr

        return "127.0.0.1"

    def _get_production_cors_origins(self) -> list[str]:
        """Get production CORS origins"""
        cors_str = os.getenv("PAKE_CORS_ORIGINS", "")
        if cors_str:
            return [origin.strip() for origin in cors_str.split(",") if origin.strip()]

        return ["https://pake.example.com", "https://app.pake.example.com"]

    def _get_staging_cors_origins(self) -> list[str]:
        """Get staging CORS origins"""
        cors_str = os.getenv("PAKE_STAGING_CORS_ORIGINS", "")
        if cors_str:
            return [origin.strip() for origin in cors_str.split(",") if origin.strip()]

        return [
            "https://staging.pake.example.com",
            "https://staging-app.pake.example.com",
        ]

    def get_uvicorn_config(self) -> dict[str, Any]:
        """Get secure uvicorn configuration"""
        config = {
            "host": self.config.bind_address,
            "port": self.config.port,
            "log_level": (
                "info" if self.environment == Environment.PRODUCTION else "debug"
            ),
            "access_log": True,
            "server_header": False,  # Security: Don't expose server info
            "date_header": False,  # Security: Don't expose date
            "proxy_headers": True,  # Handle proxy headers for IP detection
        }

        # Add workers for production
        if self.environment == Environment.PRODUCTION:
            workers = int(os.getenv("PAKE_WORKERS", "4"))
            if workers > 1:
                config["workers"] = workers

        # Add timeout settings
        config["timeout_keep_alive"] = self.config.timeout_seconds

        return config

    def get_fastapi_config(self) -> dict[str, Any]:
        """Get secure FastAPI configuration"""
        return {
            "title": "PAKE System API",
            "version": "1.0.0",
            "docs_url": "/docs" if self.environment != Environment.PRODUCTION else None,
            "redoc_url": (
                "/redoc" if self.environment != Environment.PRODUCTION else None
            ),
            "openapi_url": (
                "/openapi.json" if self.environment != Environment.PRODUCTION else None
            ),
        }

    def get_cors_config(self) -> dict[str, Any]:
        """Get secure CORS configuration"""
        if not self.config.enable_cors:
            return {}

        return {
            "allow_origins": self.config.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
            "max_age": 3600,
        }

    def validate_configuration(self) -> list[str]:
        """Validate network configuration and return warnings"""
        warnings = []

        if self.environment == Environment.PRODUCTION:
            if self.config.bind_address == "0.0.0.0":
                warnings.append(
                    "CRITICAL: Production server binding to 0.0.0.0 is insecure!",
                )

            if not self.config.enable_ssl:
                warnings.append("WARNING: SSL not enabled in production!")

            if not self.config.enable_rate_limiting:
                warnings.append("WARNING: Rate limiting not enabled in production!")

            if len(self.config.allowed_hosts) == 0:
                warnings.append("WARNING: No allowed hosts configured for production!")

        return warnings


# Global configuration instance
_network_config: SecureNetworkConfig | None = None


def get_network_config() -> SecureNetworkConfig:
    """Get global network configuration instance"""
    global _network_config
    if _network_config is None:
        _network_config = SecureNetworkConfig()
    return _network_config


def get_secure_host() -> str:
    """Get secure host binding address"""
    return get_network_config().config.bind_address


def get_secure_port() -> int:
    """Get secure port"""
    return get_network_config().config.port


def validate_network_security() -> bool:
    """Validate network security configuration"""
    config = get_network_config()
    warnings = config.validate_configuration()

    if warnings:
        logger.warning("Network security warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")

        # Return False if there are critical warnings
        critical_warnings = [w for w in warnings if "CRITICAL" in w]
        return len(critical_warnings) == 0

    return True


# Migration utilities for replacing 0.0.0.0 bindings
def migrate_bind_address(old_address: str) -> str:
    """Migrate insecure bind address to secure alternative"""
    if old_address == "0.0.0.0":
        config = get_network_config()
        return config.config.bind_address

    return old_address


def get_secure_server_config() -> dict[str, Any]:
    """Get complete secure server configuration"""
    config = get_network_config()

    return {
        "uvicorn": config.get_uvicorn_config(),
        "fastapi": config.get_fastapi_config(),
        "cors": config.get_cors_config(),
        "security": {
            "allowed_hosts": config.config.allowed_hosts,
            "enable_ssl": config.config.enable_ssl,
            "enable_rate_limiting": config.config.enable_rate_limiting,
            "max_connections": config.config.max_connections,
            "timeout_seconds": config.config.timeout_seconds,
        },
    }
