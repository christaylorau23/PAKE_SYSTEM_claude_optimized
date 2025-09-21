#!/usr/bin/env python3
"""PAKE System - Security Utilities
Provides secure credential management and security utilities
"""

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.utils.exceptions import (
    ConfigurationException,
    SecurityException,
)


class SecurityLevel(Enum):
    """Security level classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecretConfig:
    """Configuration for secret management"""

    environment: str = "development"
    require_secure_secrets: bool = True
    min_secret_length: int = 32
    secret_rotation_days: int = 90
    audit_secret_access: bool = True


class SecureCredentialManager:
    """Secure credential management utility

    Provides safe handling of secrets, API keys, and sensitive configuration
    """

    def __init__(self, config: SecretConfig | None = None):
        self.config = config or SecretConfig()
        self.logger = logging.getLogger(__name__)
        self._credentials_cache: dict[str, str] = {}

    def get_secret(
        self,
        key: str,
        default: str | None = None,
        required: bool = True,
        min_length: int | None = None,
    ) -> str | None:
        """Safely retrieve a secret from environment variables

        Args:
            key: Environment variable name
            default: Default value if not found
            required: Whether the secret is required
            min_length: Minimum required length

        Returns:
            Secret value or None if not found and not required

        Raises:
            ConfigurationException: If required secret is missing or invalid
        """
        # Check cache first
        if key in self._credentials_cache:
            return self._credentials_cache[key]

        # Get from environment
        value = os.getenv(key, default)

        if value is None and required:
            raise ConfigurationException(
                f"Required secret '{key}' not found in environment variables",
                context={"key": key, "required": required},
            )

        if value is not None:
            # Validate secret
            self._validate_secret(key, value, min_length)

            # Cache the secret
            self._credentials_cache[key] = value

            if self.config.audit_secret_access:
                self.logger.info(f"Secret accessed: {key}", extra={"secret_key": key})

        return value

    def _validate_secret(
        self,
        key: str,
        value: str,
        min_length: int | None = None,
    ) -> None:
        """Validate secret meets security requirements"""
        min_len = min_length or self.config.min_secret_length

        # Check if it's a placeholder or development key
        dangerous_patterns = [
            "change-in-production",
            "your-secret",
            "test-key",
            "dev-key",
            "development",
            "placeholder",
            "example",
            "sample",
            "default",
        ]

        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                if self.config.environment == "production":
                    raise SecurityException(
                        f"Insecure secret detected for '{key}': contains '{pattern}'",
                        context={
                            "key": key,
                            "pattern": pattern,
                            "environment": self.config.environment,
                        },
                    )
                self.logger.warning(
                    f"Development secret detected for '{key}': contains '{pattern}'",
                )

        # Check minimum length
        if len(value) < min_len:
            if self.config.require_secure_secrets:
                raise SecurityException(
                    f"Secret '{key}' is too short: {len(value)} < {min_len}",
                    context={"key": key, "length": len(value), "min_length": min_len},
                )
            self.logger.warning(
                f"Short secret detected for '{key}': {len(value)} characters",
            )

    def generate_secure_secret(self, length: int = 64, url_safe: bool = True) -> str:
        """Generate a cryptographically secure secret

        Args:
            length: Length of the secret
            url_safe: Whether to use URL-safe characters

        Returns:
            Secure random string
        """
        if url_safe:
            return secrets.token_urlsafe(length)
        return secrets.token_hex(length)

    def get_jwt_secret(self, key: str = "JWT_SECRET_KEY") -> str:
        """Get JWT secret with appropriate validation"""
        secret = self.get_secret(key, min_length=64)
        if secret is None:
            if self.config.environment == "production":
                raise SecurityException(
                    f"JWT secret '{key}' is required in production",
                    context={"key": key, "environment": self.config.environment},
                )
            # Generate a development secret
            secret = self.generate_secure_secret(64)
            self.logger.warning(
                f"Generated temporary JWT secret for development. "
                f"Set {key} environment variable for production.",
            )

        return secret

    def get_api_key(
        self,
        service_name: str,
        key: str | None = None,
        allow_test_keys: bool = None,
    ) -> str:
        """Get API key for external service

        Args:
            service_name: Name of the service
            key: Environment variable name (auto-generated if not provided)
            allow_test_keys: Whether to allow test keys (defaults to development mode)

        Returns:
            API key

        Raises:
            ConfigurationException: If API key is missing or invalid
        """
        if key is None:
            key = f"{service_name.upper()}_API_KEY"

        if allow_test_keys is None:
            allow_test_keys = self.config.environment != "production"

        api_key = self.get_secret(key, required=True)

        # Validate API key
        if not allow_test_keys:
            test_patterns = ["test", "dev", "mock", "fake", "sample"]
            if any(pattern in api_key.lower() for pattern in test_patterns):
                raise SecurityException(
                    f"Test API key detected for {service_name} in production",
                    context={
                        "service": service_name,
                        "key": key,
                        "environment": self.config.environment,
                    },
                )

        return api_key

    def get_database_credentials(self, prefix: str = "DB") -> dict[str, str]:
        """Get database credentials safely"""
        credentials = {}

        for field in ["HOST", "PORT", "NAME", "USER", "PASSWORD"]:
            env_key = f"{prefix}_{field}"
            value = self.get_secret(
                env_key,
                required=field in ["HOST", "NAME", "USER"],
                min_length=8 if field == "PASSWORD" else 1,
            )
            if value is not None:
                credentials[field.lower()] = value

        return credentials

    def mask_sensitive_data(
        self,
        data: dict[str, Any],
        sensitive_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Mask sensitive data for logging

        Args:
            data: Data dictionary
            sensitive_keys: List of keys to mask

        Returns:
            Data with sensitive values masked
        """
        if sensitive_keys is None:
            sensitive_keys = [
                "REDACTED_SECRET",
                "secret",
                "key",
                "token",
                "credential",
                "api_key",
                "auth",
                "private",
                "confidential",
            ]

        masked_data = {}

        for key, value in data.items():
            key_lower = key.lower()
            is_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)

            if is_sensitive and isinstance(value, str) and len(value) > 4:
                # Show first 4 and last 4 characters
                masked_data[key] = f"{value[:4]}...{value[-4:]}"
            elif is_sensitive:
                masked_data[key] = "***MASKED***"
            else:
                masked_data[key] = value

        return masked_data

    def clear_credentials_cache(self) -> None:
        """Clear the credentials cache"""
        self._credentials_cache.clear()
        self.logger.info("Credentials cache cleared")

    def audit_secrets_usage(self) -> dict[str, Any]:
        """Get audit information about secrets usage"""
        return {
            "cached_secrets": list(self._credentials_cache.keys()),
            "cache_size": len(self._credentials_cache),
            "config": {
                "environment": self.config.environment,
                "require_secure_secrets": self.config.require_secure_secrets,
                "min_secret_length": self.config.min_secret_length,
                "audit_enabled": self.config.audit_secret_access,
            },
        }


class PasswordHasher:
    """Secure REDACTED_SECRET hashing utility"""

    @staticmethod
    def hash_REDACTED_SECRET(REDACTED_SECRET: str, salt: str | None = None) -> str:
        """Hash REDACTED_SECRET with salt"""
        if salt is None:
            salt = secrets.token_hex(32)

        # Use PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            REDACTED_SECRET.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # iterations
        )

        return f"pbkdf2_sha256${salt}${hashed.hex()}"

    @staticmethod
    def verify_REDACTED_SECRET(REDACTED_SECRET: str, hashed: str) -> bool:
        """Verify REDACTED_SECRET against hash"""
        try:
            algorithm, salt, hash_value = hashed.split("$")
            if algorithm != "pbkdf2_sha256":
                return False

            new_hash = hashlib.pbkdf2_hmac(
                "sha256",
                REDACTED_SECRET.encode("utf-8"),
                salt.encode("utf-8"),
                100000,
            )

            return hash_value == new_hash.hex()
        except (ValueError, AttributeError):
            return False


# Global credential manager instance
_credential_manager: SecureCredentialManager | None = None


def get_credential_manager(
    config: SecretConfig | None = None,
) -> SecureCredentialManager:
    """Get the global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = SecureCredentialManager(config)
    return _credential_manager


def get_secure_secret(
    key: str,
    default: str | None = None,
    required: bool = True,
    min_length: int | None = None,
) -> str | None:
    """Convenience function to get a secure secret"""
    manager = get_credential_manager()
    return manager.get_secret(key, default, required, min_length)


def get_secure_api_key(
    service_name: str,
    key: str | None = None,
    allow_test_keys: bool = None,
) -> str:
    """Convenience function to get a secure API key"""
    manager = get_credential_manager()
    return manager.get_api_key(service_name, key, allow_test_keys)


def generate_secure_token(length: int = 64) -> str:
    """Generate a secure token"""
    manager = get_credential_manager()
    return manager.generate_secure_secret(length)


def mask_sensitive_dict(
    data: dict[str, Any],
    sensitive_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Mask sensitive data in a dictionary"""
    manager = get_credential_manager()
    return manager.mask_sensitive_data(data, sensitive_keys)


# Security validation functions
def validate_environment_security() -> list[str]:
    """Validate the security configuration of the environment

    Returns:
        List of security warnings/issues
    """
    issues = []
    manager = get_credential_manager()

    # Check for common security environment variables
    required_secrets = ["JWT_SECRET_KEY", "DATABASE_PASSWORD", "REDIS_PASSWORD"]

    for secret in required_secrets:
        try:
            manager.get_secret(secret, required=False)
        except SecurityException as e:
            issues.append(f"Security issue with {secret}: {e.message}")

    return issues


def create_security_headers() -> dict[str, str]:
    """Create security headers for HTTP responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
