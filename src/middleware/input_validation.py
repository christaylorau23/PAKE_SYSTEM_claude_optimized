"""Input Validation Middleware for PAKE System
Prevents injection attacks and ensures data integrity

SECURITY POLICY: All inputs must be validated and sanitized before processing
"""

import html
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""


class SecurityLevel(Enum):
    """Security validation levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of input validation"""

    is_valid: bool
    sanitized_value: Any
    error_message: str | None = None
    security_warnings: list[str] = None

    def __post_init__(self):
        if self.security_warnings is None:
            self.security_warnings = []


class InputValidator:
    """Comprehensive input validation and sanitization"""

    # Dangerous patterns that could indicate injection attempts
    DANGEROUS_PATTERNS = [
        # SQL Injection patterns
        r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"(?i)(script|javascript|vbscript|onload|onerror|onclick)",
        r"(?i)(<script|</script|javascript:|data:|vbscript:)",
        # Command injection patterns
        r"[;&|`$(){}[\]\\]",
        r"(?i)(cmd|command|shell|bash|sh|powershell)",
        # Path traversal patterns
        r"\.\./|\.\.\\|\.\.%2f|\.\.%5c",
        # XSS patterns
        r"<[^>]*>",
        r"(?i)(alert|prompt|confirm|eval|function)",
        # LDAP injection patterns
        r"[()=*!&|]",
        # NoSQL injection patterns
        r"[$]where|[$]ne|[$]gt|[$]lt|[$]regex",
    ]

    # Compiled regex patterns for performance
    _compiled_patterns = [re.compile(pattern) for pattern in DANGEROUS_PATTERNS]

    @classmethod
    def validate_string(
        self,
        value: str,
        max_length: int = 1000,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        allow_html: bool = False,
    ) -> ValidationResult:
        """Validate and sanitize string input

        Args:
            value: Input string to validate
            max_length: Maximum allowed length
            security_level: Security validation level
            allow_html: Whether to allow HTML tags
        """
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Input must be a string",
            )

        warnings = []

        # Length validation
        if len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message=f"Input exceeds maximum length of {max_length} characters",
            )

        # Security pattern detection
        for pattern in self._compiled_patterns:
            if pattern.search(value):
                if security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=None,
                        error_message="Input contains potentially dangerous content",
                    )
                warnings.append("Input contains potentially dangerous content")

        # HTML sanitization
        if not allow_html:
            sanitized_value = html.escape(value)
            if sanitized_value != value:
                warnings.append("HTML content was escaped")
        else:
            sanitized_value = value

        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized_value,
            security_warnings=warnings,
        )

    @classmethod
    def validate_email(cls, value: str) -> ValidationResult:
        """Validate email address format"""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Email must be a string",
            )

        # Basic email regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Invalid email format",
            )

        # Sanitize email
        sanitized_email = html.escape(value.strip().lower())

        return ValidationResult(is_valid=True, sanitized_value=sanitized_email)

    @classmethod
    def validate_json(
        cls,
        value: str | dict,
        max_size: int = 10000,
    ) -> ValidationResult:
        """Validate JSON input"""
        if isinstance(value, str):
            try:
                parsed_json = json.loads(value)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=None,
                    error_message=f"Invalid JSON format: {str(e)}",
                )
        elif isinstance(value, dict):
            parsed_json = value
        else:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Input must be JSON string or dictionary",
            )

        # Size validation
        json_str = json.dumps(parsed_json)
        if len(json_str) > max_size:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message=f"JSON exceeds maximum size of {max_size} characters",
            )

        return ValidationResult(is_valid=True, sanitized_value=parsed_json)

    @classmethod
    def validate_integer(
        cls,
        value: Any,
        min_val: int = None,
        max_val: int = None,
    ) -> ValidationResult:
        """Validate integer input"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Input must be a valid integer",
            )

        if min_val is not None and int_value < min_val:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message=f"Integer must be at least {min_val}",
            )

        if max_val is not None and int_value > max_val:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message=f"Integer must be at most {max_val}",
            )

        return ValidationResult(is_valid=True, sanitized_value=int_value)

    @classmethod
    def validate_uuid(cls, value: str) -> ValidationResult:
        """Validate UUID format"""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="UUID must be a string",
            )

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, value.lower()):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Invalid UUID format",
            )

        return ValidationResult(is_valid=True, sanitized_value=value.lower())

    @classmethod
    def validate_api_key(cls, value: str) -> ValidationResult:
        """Validate API key format"""
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="API key must be a string",
            )

        # API keys should be alphanumeric with some special characters
        api_key_pattern = r"^[a-zA-Z0-9_-]{20,}$"
        if not re.match(api_key_pattern, value):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="Invalid API key format",
            )

        return ValidationResult(is_valid=True, sanitized_value=value)


class RequestValidator:
    """Request-level validation middleware"""

    @classmethod
    def validate_request_data(
        cls,
        data: dict[str, Any],
        schema: dict[str, Any],
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ) -> ValidationResult:
        """Validate request data against schema

        Args:
            data: Request data to validate
            schema: Validation schema
            security_level: Security validation level
        """
        validator = InputValidator()
        errors = []
        warnings = []
        sanitized_data = {}

        for field, rules in schema.items():
            if field not in data:
                if rules.get("required", False):
                    errors.append(f"Required field '{field}' is missing")
                continue

            value = data[field]
            field_type = rules.get("type", "string")

            # Validate based on field type
            if field_type == "string":
                result = validator.validate_string(
                    value,
                    max_length=rules.get("max_length", 1000),
                    security_level=security_level,
                    allow_html=rules.get("allow_html", False),
                )
            elif field_type == "email":
                result = validator.validate_email(value)
            elif field_type == "integer":
                result = validator.validate_integer(
                    value,
                    min_val=rules.get("min"),
                    max_val=rules.get("max"),
                )
            elif field_type == "uuid":
                result = validator.validate_uuid(value)
            elif field_type == "api_key":
                result = validator.validate_api_key(value)
            elif field_type == "json":
                result = validator.validate_json(value)
            else:
                errors.append(f"Unknown field type '{field_type}' for field '{field}'")
                continue

            if not result.is_valid:
                errors.append(f"Field '{field}': {result.error_message}")
            else:
                sanitized_data[field] = result.sanitized_value
                warnings.extend(
                    [f"Field '{field}': {w}" for w in result.security_warnings],
                )

        if errors:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                error_message="; ".join(errors),
            )

        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized_data,
            security_warnings=warnings,
        )


def validate_input(value: Any, field_type: str = "string", **kwargs) -> Any:
    """Convenience function for input validation

    Args:
        value: Value to validate
        field_type: Type of validation to perform
        **kwargs: Additional validation parameters

    Returns:
        Sanitized value

    Raises:
        ValidationError: If validation fails
    """
    validator = InputValidator()

    if field_type == "string":
        result = validator.validate_string(value, **kwargs)
    elif field_type == "email":
        result = validator.validate_email(value)
    elif field_type == "integer":
        result = validator.validate_integer(value, **kwargs)
    elif field_type == "uuid":
        result = validator.validate_uuid(value)
    elif field_type == "api_key":
        result = validator.validate_api_key(value)
    elif field_type == "json":
        result = validator.validate_json(value, **kwargs)
    else:
        raise ValidationError(f"Unknown field type: {field_type}")

    if not result.is_valid:
        raise ValidationError(result.error_message)

    # Log security warnings
    for warning in result.security_warnings:
        logger.warning(f"Security warning: {warning}")

    return result.sanitized_value
