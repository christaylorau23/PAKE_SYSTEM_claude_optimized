#!/usr/bin/env python3
"""
Production Environment Validation Script
Validates that all required environment variables are set with appropriate values
"""

import logging
import os
import re
import sys
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_REDACTED_SECRET_strength(
    REDACTED_SECRET: str, min_length: int = 12
) -> dict[str, Any]:
    """Validate REDACTED_SECRET meets security requirements"""
    issues = []

    if len(REDACTED_SECRET) < min_length:
        issues.append(f"Password too short (minimum {min_length} characters)")

    if not re.search(r"[A-Z]", REDACTED_SECRET):
        issues.append("Missing uppercase letter")

    if not re.search(r"[a-z]", REDACTED_SECRET):
        issues.append("Missing lowercase letter")

    if not re.search(r"\d", REDACTED_SECRET):
        issues.append("Missing number")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', REDACTED_SECRET):
        issues.append("Missing special character")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "strength": "Strong" if len(issues) == 0 else "Weak",
    }


def validate_api_key(api_key: str, service: str) -> dict[str, Any]:
    """Validate API key format"""
    patterns = {
        "openai": r"^sk-[A-Za-z0-9]{48}$",
        "anthropic": r"^sk-ant-[A-Za-z0-9\-_]{32,}$",
        "elevenlabs": r"^[A-Za-z0-9]{32}$",
    }

    if service not in patterns:
        return {"valid": True, "message": f"Unknown API key format for {service}"}

    if re.match(patterns[service], api_key):
        return {"valid": True, "message": f"Valid {service} API key format"}
    return {"valid": False, "message": f"Invalid {service} API key format"}


def validate_production_environment() -> bool:
    """Validate complete production environment"""
    logger.info("🔍 Validating production environment configuration...")

    # Check NODE_ENV
    node_env = os.getenv("NODE_ENV", "").lower()
    if node_env != "production":
        logger.warning(f"NODE_ENV is '{node_env}', expected 'production'")

    # Required environment variables
    required_vars = {
        "DB_HOST": {"default": "localhost", "validator": None},
        "DB_PORT": {
            "default": "5432",
            "validator": lambda x: x.isdigit() and 1 <= int(x) <= 65535,
        },
        "DB_NAME": {"default": "pake_system", "validator": None},
        "DB_USER": {"default": "pake_user", "validator": None},
        "DB_PASSWORD": {
            "default": None,
            "validator": lambda x: validate_REDACTED_SECRET_strength(x)["valid"],
        },
        "REDIS_HOST": {"default": "localhost", "validator": None},
        "REDIS_PORT": {
            "default": "6379",
            "validator": lambda x: x.isdigit() and 1 <= int(x) <= 65535,
        },
        "REDIS_PASSWORD": {
            "default": None,
            "validator": lambda x: validate_REDACTED_SECRET_strength(x, 8)["valid"],
        },
    }

    # Optional but recommended variables
    optional_vars = {
        "OPENAI_API_KEY": {
            "validator": lambda x: validate_api_key(x, "openai")["valid"],
        },
        "ANTHROPIC_API_KEY": {
            "validator": lambda x: validate_api_key(x, "anthropic")["valid"],
        },
        "ELEVENLABS_API_KEY": {
            "validator": lambda x: validate_api_key(x, "elevenlabs")["valid"],
        },
    }

    all_valid = True

    # Validate required variables
    logger.info("\n📋 Required Environment Variables:")
    for var_name, config in required_vars.items():
        value = os.getenv(var_name, config["default"])

        if not value:
            logger.error(f"❌ {var_name}: Missing (required)")
            all_valid = False
            continue

        if config["validator"] and not config["validator"](value):
            if "PASSWORD" in var_name:
                # Detailed REDACTED_SECRET validation
                result = validate_REDACTED_SECRET_strength(value)
                logger.error(
                    f"❌ {var_name}: Weak REDACTED_SECRET - {', '.join(result['issues'])}",
                )
            else:
                logger.error(f"❌ {var_name}: Invalid format")
            all_valid = False
        else:
            # Mask sensitive values
            if "PASSWORD" in var_name or "KEY" in var_name or "SECRET" in var_name:
                display_value = (
                    f"{value[:4]}...{value[-4:]}" if len(value) >= 8 else "***"
                )
            else:
                display_value = value
            logger.info(f"✅ {var_name}: {display_value}")

    # Validate optional variables
    logger.info("\n🔑 Optional API Keys:")
    for var_name, config in optional_vars.items():
        value = os.getenv(var_name)

        if not value:
            logger.info(f"⚠️  {var_name}: Not set (optional)")
            continue

        if config["validator"] and not config["validator"](value):
            result = validate_api_key(value, var_name.lower().replace("_api_key", ""))
            logger.warning(f"⚠️  {var_name}: {result['message']}")
        else:
            logger.info(f"✅ {var_name}: Valid format")

    # Final result
    if all_valid:
        logger.info("\n✅ Environment validation completed successfully!")
        logger.info("🚀 Ready for production deployment")
        return True
    logger.error("\n❌ Environment validation failed!")
    logger.error("🔧 Please fix the issues above before deploying")
    return False


if __name__ == "__main__":
    success = validate_production_environment()
    if not success:
        sys.exit(1)
    print("\n🎉 Production environment validation complete!")
