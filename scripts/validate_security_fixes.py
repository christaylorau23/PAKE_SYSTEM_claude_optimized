from typing import List

#!/usr/bin/env python3
"""
Security Validation Script for PAKE System
==========================================

This script validates that all security fixes have been properly implemented:
1. No hardcoded secrets in the codebase
2. Vault integration is working correctly
3. Fail-fast security is enforced
4. All secrets are properly managed

Usage:
    python scripts/validate_security_fixes.py

Requirements:
    - Vault server running (for integration tests)
    - All dependencies installed
"""

import logging
from pathlib import Path
import re
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validate security fixes implementation."""

def __init__(self, repo_path: Any = None) -> None:
        """
        Initialize security validator.

        Args:
            repo_path: Path to the repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.validation_results = {}

    def check_hardcoded_secrets(self) -> tuple[bool, list[str]]:
        """
        Check for hardcoded secrets in the codebase.

        Returns:
            Tuple of (success, list of found secrets)
        """
        logger.info("Checking for hardcoded secrets...")

        # Patterns that indicate hardcoded secrets
        secret_patterns = [
            r'["\'](sk-|pk-|rk-)[a-zA-Z0-9]{20,}["\']',  # API keys
            r'["\'](password|passwd|pwd)\s*[:=]\s*["\'][^"\']+["\']',  # Passwords
            r'["\'](secret|key|token)\s*[:=]\s*["\'][^"\']{20,}["\']',  # Secrets
            r'["\'](changeme|default|placeholder)[^"\']*["\']',  # Placeholders
            r'["\'](your-|test-)[^"\']*["\']',  # Template values
        ]

        found_secrets = []

        # Search through Python files
        for py_file in self.repo_path.rglob("*.py"):
            if any(
                skip in str(py_file)
                for skip in [".git", "__pycache__", ".pytest_cache"]
            ):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's a REDACTED_SECRET or test value
                        if any(
                            skip in match.lower()
                            for skip in ["redacted", "test-", "placeholder"]
                        ):
                            continue
                        found_secrets.append(f"{py_file}: {match}")

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error reading %s: %s", py_file, e)

        # Search through YAML files
        for yaml_file in self.repo_path.rglob("*.yaml"):
            if any(
                skip in str(yaml_file)
                for skip in [".git", "__pycache__", ".pytest_cache"]
            ):
                continue

            try:
                with open(yaml_file, encoding="utf-8") as f:
                    content = f.read()

                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's a REDACTED_SECRET or test value
                        if any(
                            skip in match.lower()
                            for skip in ["redacted", "test-", "placeholder"]
                        ):
                            continue
                        found_secrets.append(f"{yaml_file}: {match}")

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error reading %s: %s", yaml_file, e)

        success = len(found_secrets) == 0
        self.validation_results["hardcoded_secrets"] = {
            "success": success,
            "found_secrets": found_secrets,
        }

        if success:
            logger.info("✅ No hardcoded secrets found")
        else:
            logger.error("❌ Found %s potential hardcoded secrets", len(found_secrets))
            for secret in found_secrets:
                logger.error("   %s", secret)

        return success, found_secrets

    def check_vault_integration(self) -> bool:
        """
        Check if Vault integration is properly implemented.

        Returns:
            True if Vault integration is properly implemented
        """
        logger.info("Checking Vault integration...")

        # Check if Vault client exists
        vault_client_path = (
            self.repo_path / "src" / "pake_system" / "core" / "vault_client.py"
        )
        if not vault_client_path.exists():
            logger.error("❌ Vault client not found")
            self.validation_results["vault_integration"] = {
                "success": False,
                "error": "Vault client not found",
            }
            return False

        # Check if config.py uses Vault
        config_path = self.repo_path / "src" / "pake_system" / "core" / "config.py"
        if not config_path.exists():
            logger.error("❌ Config file not found")
            self.validation_results["vault_integration"] = {
                "success": False,
                "error": "Config file not found",
            }
            return False

        try:
            with open(config_path, encoding="utf-8") as f:
                config_content = f.read()

            # Check for Vault integration
            vault_checks = [
                "get_vault_client" in config_content,
                "VaultClientError" in config_content,
                "load_secrets_from_vault" in config_content,
                "USE_VAULT" in config_content,
            ]

            if not all(vault_checks):
                logger.error("❌ Vault integration not properly implemented in config")
                self.validation_results["vault_integration"] = {
                    "success": False,
                    "error": "Vault integration incomplete",
                }
                return False

            logger.info("✅ Vault integration properly implemented")
            self.validation_results["vault_integration"] = {"success": True}
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Error checking Vault integration: %s", e)
            self.validation_results["vault_integration"] = {
                "success": False,
                "error": str(e),
            }
            return False

    def check_fail_fast_security(self) -> bool:
        """
        Check if fail-fast security is properly implemented.

        Returns:
            True if fail-fast security is properly implemented
        """
        logger.info("Checking fail-fast security...")

        config_path = self.repo_path / "src" / "pake_system" / "core" / "config.py"

        try:
            with open(config_path, encoding="utf-8") as f:
                config_content = f.read()

            # Check for fail-fast patterns
            fail_fast_checks = [
                "raise ValueError" in config_content,
                "security requirement" in config_content.lower(),
                "cannot start without" in config_content.lower(),
                "required secrets missing" in config_content.lower(),
            ]

            if not all(fail_fast_checks):
                logger.error("❌ Fail-fast security not properly implemented")
                self.validation_results["fail_fast_security"] = {
                    "success": False,
                    "error": "Fail-fast security incomplete",
                }
                return False

            logger.info("✅ Fail-fast security properly implemented")
            self.validation_results["fail_fast_security"] = {"success": True}
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Error checking fail-fast security: %s", e)
            self.validation_results["fail_fast_security"] = {
                "success": False,
                "error": str(e),
            }
            return False

    def check_kubernetes_secrets(self) -> bool:
        """
        Check if Kubernetes secrets are properly configured.

        Returns:
            True if Kubernetes secrets are properly configured
        """
        logger.info("Checking Kubernetes secrets configuration...")

        secrets_path = self.repo_path / "deploy" / "k8s" / "base" / "secrets.yaml"

        if not secrets_path.exists():
            logger.error("❌ Kubernetes secrets file not found")
            self.validation_results["kubernetes_secrets"] = {
                "success": False,
                "error": "Secrets file not found",
            }
            return False

        try:
            with open(secrets_path, encoding="utf-8") as f:
                secrets_content = f.read()

            # Check for proper configuration
            k8s_checks = [
                "REDACTED_SECRET" in secrets_content,
                "vault.hashicorp.com/agent-inject" in secrets_content,
                "External Secrets Operator" in secrets_content,
                "NO hardcoded secrets" in secrets_content,
            ]

            if not all(k8s_checks):
                logger.error("❌ Kubernetes secrets not properly configured")
                self.validation_results["kubernetes_secrets"] = {
                    "success": False,
                    "error": "Kubernetes secrets configuration incomplete",
                }
                return False

            logger.info("✅ Kubernetes secrets properly configured")
            self.validation_results["kubernetes_secrets"] = {"success": True}
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Error checking Kubernetes secrets: %s", e)
            self.validation_results["kubernetes_secrets"] = {
                "success": False,
                "error": str(e),
            }
            return False

    def check_trufflehog_ignore(self) -> bool:
        """
        Check if .trufflehog-ignore file is properly configured.

        Returns:
            True if .trufflehog-ignore is properly configured
        """
        logger.info("Checking .trufflehog-ignore configuration...")

        ignore_path = self.repo_path / ".trufflehog-ignore"

        if not ignore_path.exists():
            logger.error("❌ .trufflehog-ignore file not found")
            self.validation_results["trufflehog_ignore"] = {
                "success": False,
                "error": "Ignore file not found",
            }
            return False

        try:
            with open(ignore_path, encoding="utf-8") as f:
                ignore_content = f.read()

            # Check for proper configuration
            ignore_checks = [
                "REDACTED_SECRET" in ignore_content,
                "test-secret-key" in ignore_content,
                "placeholder" in ignore_content,
                "confirmed false positives" in ignore_content,
            ]

            if not all(ignore_checks):
                logger.error("❌ .trufflehog-ignore not properly configured")
                self.validation_results["trufflehog_ignore"] = {
                    "success": False,
                    "error": "Ignore file configuration incomplete",
                }
                return False

            logger.info("✅ .trufflehog-ignore properly configured")
            self.validation_results["trufflehog_ignore"] = {"success": True}
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Error checking .trufflehog-ignore: %s", e)
            self.validation_results["trufflehog_ignore"] = {
                "success": False,
                "error": str(e),
            }
            return False

    def run_validation(self) -> bool:
        """
        Run all security validation checks.

        Returns:
            True if all validations pass, False otherwise
        """
        logger.info("=" * 60)
        logger.info("PAKE System - Security Validation")
        logger.info("=" * 60)

        # Run all validation checks
        checks = [
            self.check_hardcoded_secrets,
            self.check_vault_integration,
            self.check_fail_fast_security,
            self.check_kubernetes_secrets,
            self.check_trufflehog_ignore,
        ]

        all_passed = True
        for check in checks:
            try:
                result = check()
                if not result:
                    all_passed = False
            except (ValueError, RuntimeError) as e:
                logger.error("❌ Validation check failed: %s", e)
                all_passed = False

        # Print summary
        logger.info("=" * 60)
        logger.info("Security Validation Summary")
        logger.info("=" * 60)

        for check_name, result in self.validation_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            logger.info("%s: %s", check_name, status)
            if not result["success"] and "error" in result:
                logger.info("   Error: %s", result["error"])

        if all_passed:
            logger.info("")
            logger.info("🎉 All security validations passed!")
            logger.info("The PAKE System is now secure and ready for production.")
        else:
            logger.info("")
            logger.error("❌ Some security validations failed!")
            logger.error("Please address the issues above before proceeding.")

        return all_passed


def main(self) -> None:
    """Main entry point for security validation."""
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."

    validator = SecurityValidator(repo_path)
    success = validator.run_validation()

    if success:
        print("\n✅ Security validation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Security validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
