"""Centralized Secrets Validation Utility for Python Services
Implements fail-fast pattern for missing secrets - NO FALLBACKS ALLOWED

SECURITY POLICY: Application must crash if required secrets are missing
This prevents weak REDACTED_SECRET fallbacks and ensures proper secret management
"""

import os
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecretValidationResult:
    """Result of secret validation"""

    is_valid: bool
    secret_name: str
    error_message: str | None = None


class SecretsValidator:
    """Centralized secrets validation for Python services"""

    # Required secrets for the PAKE system
    REQUIRED_SECRETS = [
        "JWT_SECRET",
        "DB_PASSWORD",
        "REDIS_PASSWORD",
        "PAKE_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "DID_API_KEY",
        "HEYGEN_API_KEY",
        "WEBHOOK_SECRET",
    ]

    # Known weak patterns that should never be used
    WEAK_PATTERNS = [
        "SECURE_WEAK_PASSWORD_REQUIRED",
        "SECURE_DB_PASSWORD_REQUIRED",
        "SECURE_API_KEY_REQUIRED",
        "SECURE_JWT_SECRET_REQUIRED",
        "SECURE_SECRET_KEY_REQUIRED",
        "your-super-secret-jwt-key-change-in-production",
        "default",
        "REDACTED_SECRET",
        "secret",
        "key",
        "test",
        "dev",
        "development",
    ]

    @classmethod
    def validate_all_secrets(cls) -> None:
        """Validate all required secrets at application startup
        FAILS FAST if any required secret is missing or weak
        """
        missing_secrets: list[str] = []
        weak_secrets: list[str] = []

        for secret_name in cls.REQUIRED_SECRETS:
            value = os.getenv(secret_name)

            if not value:
                missing_secrets.append(secret_name)
            elif cls._is_weak_secret(value):
                weak_secrets.append(secret_name)

        if missing_secrets:
            error_msg = (
                f"CRITICAL SECURITY ERROR: Missing required secrets: {', '.join(missing_secrets)}. "
                f"Application cannot start without proper secret configuration. "
                f"Please set these environment variables with strong values."
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        if weak_secrets:
            error_msg = (
                f"CRITICAL SECURITY ERROR: Weak secrets detected: {', '.join(weak_secrets)}. "
                f"All secrets must be properly configured with strong values. "
                f"Never use default or weak REDACTED_SECRETs in production."
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        print("✅ All secrets validated successfully")

    @classmethod
    def get_required_secret(cls, secret_name: str) -> str:
        """Get a required secret with validation
        FAILS FAST if secret is missing or weak
        """
        value = os.getenv(secret_name)

        if not value:
            error_msg = (
                f"CRITICAL SECURITY ERROR: Required secret '{secret_name}' is not configured. "
                f"Application cannot continue without this secret. "
                f"Please set the {secret_name} environment variable."
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        if cls._is_weak_secret(value):
            error_msg = (
                f"CRITICAL SECURITY ERROR: Secret '{secret_name}' has a weak value. "
                f"All secrets must be properly configured with strong values. "
                f"Never use default or weak REDACTED_SECRETs."
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        return value

    @classmethod
    def get_optional_secret(cls, secret_name: str) -> str | None:
        """Get an optional secret (returns None if not set, but validates if set)"""
        value = os.getenv(secret_name)

        if not value:
            return None

        if cls._is_weak_secret(value):
            error_msg = (
                f"CRITICAL SECURITY ERROR: Optional secret '{secret_name}' has a weak value. "
                f"If configured, secrets must have strong values."
            )
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        return value

    @classmethod
    def validate_secret_strength(
        cls,
        secret_name: str,
        value: str,
    ) -> SecretValidationResult:
        """Validate secret strength (minimum requirements)"""
        if len(value) < 16:
            return SecretValidationResult(
                is_valid=False,
                secret_name=secret_name,
                error_message=f"Secret '{secret_name}' is too short (minimum 16 characters)",
            )

        if cls._is_weak_secret(value):
            return SecretValidationResult(
                is_valid=False,
                secret_name=secret_name,
                error_message=f"Secret '{secret_name}' matches weak pattern",
            )

        return SecretValidationResult(is_valid=True, secret_name=secret_name)

    @classmethod
    def get_configured_secrets(cls) -> dict[str, bool]:
        """Get all configured secrets (for debugging - never log actual values)"""
        result: dict[str, bool] = {}

        for secret_name in cls.REQUIRED_SECRETS:
            result[secret_name] = bool(os.getenv(secret_name))

        return result

    @classmethod
    def _is_weak_secret(cls, value: str) -> bool:
        """Check if a secret value is weak (matches known weak patterns)"""
        lower_value = value.lower()
        return any(pattern.lower() in lower_value for pattern in cls.WEAK_PATTERNS)

    @classmethod
    def get_database_config(cls) -> dict[str, Any]:
        """Get validated database configuration"""
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "pake_system"),
            "user": os.getenv("DB_USER", "pake_user"),
            "REDACTED_SECRET": cls.get_required_secret("DB_PASSWORD"),
        }

    @classmethod
    def get_redis_config(cls) -> dict[str, Any]:
        """Get validated Redis configuration"""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "db": int(os.getenv("REDIS_DB", "0")),
            "REDACTED_SECRET": cls.get_required_secret("REDIS_PASSWORD"),
        }


# Initialize secrets validation on module import
# This ensures the application fails fast if secrets are not properly configured
if __name__ != "__main__":
    SecretsValidator.validate_all_secrets()
