#!/usr/bin/env python3
"""
PAKE System Security Test Suite
Phoenix Protocol Phase 7.2 - Comprehensive Security Testing

This script provides comprehensive security testing capabilities for the PAKE System,
integrating with the security-first CI/CD pipeline.
"""

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecurityTestSuite:
    """Comprehensive security testing suite for PAKE System."""

    def __init__(self, config_path: str | None = None):
        """Initialize the security test suite."""
        self.config_path = config_path or "security-gate-config.yaml"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {"total_tests": 0, "passed": 0, "failed": 0, "warnings": 0},
        }

    def load_config(self) -> dict[str, Any]:
        """Load security configuration."""
        try:
            import yaml

            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(
                f"Configuration file {self.config_path} not found, using defaults"
            )
            return self._get_default_config()
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error(f"Error loading configuration: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default security configuration."""
        return {
            "SECURITY_GATE_CONFIG": {
                "CRITICAL_VULNERABILITIES_MAX": 0,
                "HIGH_VULNERABILITIES_MAX": 0,
                "MEDIUM_VULNERABILITIES_MAX": 10,
                "LOW_VULNERABILITIES_MAX": 50,
            },
            "DEPENDENCY_SCANNING": {
                "TRIVY_ENABLED": True,
                "PIP_AUDIT_ENABLED": True,
                "SAFETY_ENABLED": True,
            },
            "SECRET_SCANNING": {
                "TRUFFLEHOG_ENABLED": True,
                "GITLEAKS_ENABLED": True,
                "VERIFY_SECRETS": True,
            },
            "SAST_SCANNING": {
                "SEMGREP_ENABLED": True,
                "BANDIT_ENABLED": True,
                "RUFF_SECURITY_ENABLED": True,
            },
        }

    def run_command(self, command: list[str], description: str) -> dict[str, Any]:
        """Run a command and return results."""
        logger.info(f"Running: {description}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            return {
                "command": " ".join(command),
                "description": description,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {description}")
            return {
                "command": " ".join(command),
                "description": description,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "success": False,
            }
        except (ValueError, RuntimeError) as e:
            logger.error(f"Error running command {description}: {e}")
            return {
                "command": " ".join(command),
                "description": description,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
            }

    def test_dependency_security(self) -> dict[str, Any]:
        """Test dependency security using multiple tools."""
        logger.info("Testing dependency security...")
        config = self.load_config()
        results = {}

        # Run pip-audit
        if config.get("DEPENDENCY_SCANNING", {}).get("PIP_AUDIT_ENABLED", True):
            results["pip_audit"] = self.run_command(
                ["pip-audit", "--format=json", "--desc"],
                "pip-audit dependency vulnerability scan",
            )

        # Run safety check
        if config.get("DEPENDENCY_SCANNING", {}).get("SAFETY_ENABLED", True):
            results["safety"] = self.run_command(
                ["safety", "check", "--json"], "safety dependency vulnerability check"
            )

        # Run poetry audit if available
        try:
            results["poetry_audit"] = self.run_command(
                ["poetry", "audit"], "poetry dependency audit"
            )
        except FileNotFoundError:
            logger.info("Poetry not available, skipping poetry audit")

        return results

    def test_secret_detection(self) -> dict[str, Any]:
        """Test secret detection capabilities."""
        logger.info("Testing secret detection...")
        config = self.load_config()
        results = {}

        # Check for hardcoded secrets in source code
        results["hardcoded_secrets"] = self._check_hardcoded_secrets()

        # Validate environment variable usage
        results["env_var_validation"] = self._validate_environment_variables()

        return results

    def _check_hardcoded_secrets(self) -> dict[str, Any]:
        """Check for hardcoded secrets in source code."""
        logger.info("Checking for hardcoded secrets...")

        patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r"REDACTED_SECRET",  # Should not exist
        ]

        issues = []
        src_path = Path("src")

        if not src_path.exists():
            return {
                "success": True,
                "issues": [],
                "message": "src/ directory not found",
            }

        for py_file in src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()
                    for i, line in enumerate(content.split("\n"), 1):
                        for pattern in patterns:
                            import re

                            if re.search(pattern, line, re.IGNORECASE):
                                issues.append(
                                    {
                                        "file": str(py_file),
                                        "line": i,
                                        "pattern": pattern,
                                        "content": line.strip(),
                                    }
                                )
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning(f"Could not check {py_file}: {e}")

                return {
                    "success": len(issues) == 0,
                    "issues": issues,
                    "count": len(issues),
                }
        return None

    def _validate_environment_variables(self) -> dict[str, Any]:
        """Validate proper environment variable usage."""
        logger.info("Validating environment variable usage...")

        # Check that critical secrets use environment variables
        critical_env_vars = [
            "PAKE_MASTER_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET",
            "API_KEY",
        ]

        results = {}
        for var in critical_env_vars:
            value = os.getenv(var)
            results[var] = {
                "set": value is not None,
                "length": len(value) if value else 0,
                "secure": len(value) >= 32 if value else False,
            }

        return {
            "success": all(
                result["set"] and result["secure"] for result in results.values()
            ),
            "variables": results,
        }

    def test_static_analysis(self) -> dict[str, Any]:
        """Test static analysis security tools."""
        logger.info("Testing static analysis security...")
        config = self.load_config()
        results = {}

        # Run Bandit
        if config.get("SAST_SCANNING", {}).get("BANDIT_ENABLED", True):
            results["bandit"] = self.run_command(
                ["bandit", "-r", "src/", "-f", "json"], "Bandit security linter"
            )

        # Run Ruff security rules
        if config.get("SAST_SCANNING", {}).get("RUFF_SECURITY_ENABLED", True):
            results["ruff_security"] = self.run_command(
                ["ruff", "check", "src/", "--select", "S", "--output-format=json"],
                "Ruff security rules",
            )

        return results

    def test_authentication_security(self) -> dict[str, Any]:
        """Test authentication and authorization security."""
        logger.info("Testing authentication security...")

        # Check for secure password hashing
        results = self._check_password_security()

        # Check JWT configuration
        results["jwt_security"] = self._check_jwt_security()

        return results

    def _check_password_security(self) -> dict[str, Any]:
        """Check password security implementation."""
        logger.info("Checking password security...")

        # Look for password hashing implementations
        src_path = Path("src")
        password_issues = []

        if src_path.exists():
            for py_file in src_path.rglob("*.py"):
                try:
                    with open(py_file, encoding="utf-8") as f:
                        content = f.read()

                        # Check for insecure password handling
                        if "password" in content.lower():
                            if (
                                "bcrypt" not in content
                                and "argon2" not in content
                                and "scrypt" not in content
                            ):
                                if (
                                    "hashlib.md5" in content
                                    or "hashlib.sha1" in content
                                ):
                                    password_issues.append(
                                        {
                                            "file": str(py_file),
                                            "issue": "Insecure password hashing detected",
                                            "severity": "HIGH",
                                        }
                                    )
                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.warning(f"Could not check {py_file}: {e}")

            return {
                "success": len(password_issues) == 0,
                "issues": password_issues,
                "count": len(password_issues),
            }
        return None

    def _check_jwt_security(self) -> dict[str, Any]:
        """Check JWT security implementation."""
        logger.info("Checking JWT security...")

        # Check JWT secret strength
        jwt_secret = os.getenv("JWT_SECRET")

        return {
            "success": jwt_secret is not None and len(jwt_secret) >= 32,
            "secret_length": len(jwt_secret) if jwt_secret else 0,
            "secret_set": jwt_secret is not None,
        }

    def test_data_protection(self) -> dict[str, Any]:
        """Test data protection and privacy measures."""
        logger.info("Testing data protection...")

        # Check for data encryption
        results = self._check_data_encryption()

        # Check for sensitive data handling
        results["sensitive_data"] = self._check_sensitive_data_handling()

        return results

    def _check_data_encryption(self) -> dict[str, Any]:
        """Check data encryption implementation."""
        logger.info("Checking data encryption...")

        encryption_issues = []
        src_path = Path("src")

        if src_path.exists():
            for py_file in src_path.rglob("*.py"):
                try:
                    with open(py_file, encoding="utf-8") as f:
                        content = f.read()

                        # Check for encryption usage
                        if "encrypt" in content.lower() or "decrypt" in content.lower():
                            if (
                                "cryptography" not in content
                                and "pycryptodome" not in content
                            ):
                                encryption_issues.append(
                                    {
                                        "file": str(py_file),
                                        "issue": "Potential insecure encryption implementation",
                                        "severity": "MEDIUM",
                                    }
                                )
                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.warning(f"Could not check {py_file}: {e}")

                return {
                    "success": len(encryption_issues) == 0,
                    "issues": encryption_issues,
                    "count": len(encryption_issues),
                }
        return None

    def _check_sensitive_data_handling(self) -> dict[str, Any]:
        """Check sensitive data handling."""
        logger.info("Checking sensitive data handling...")

        sensitive_patterns = [
            "credit_card",
            "ssn",
            "social_security",
            "personal_id",
            "phone_number",
            "email_address",
        ]

        issues = []
        src_path = Path("src")

        if src_path.exists():
            for py_file in src_path.rglob("*.py"):
                try:
                    with open(py_file, encoding="utf-8") as f:
                        content = f.read()
                        for pattern in sensitive_patterns:
                            if pattern in content.lower():
                                issues.append(
                                    {
                                        "file": str(py_file),
                                        "pattern": pattern,
                                        "severity": "MEDIUM",
                                    }
                                )
                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.warning(f"Could not check {py_file}: {e}")

            return {"success": len(issues) == 0, "issues": issues, "count": len(issues)}
        return None

    def run_comprehensive_test(self) -> dict[str, Any]:
        """Run comprehensive security test suite."""
        logger.info("Starting comprehensive security test suite...")

        # Run all test categories
        test_categories = [
            ("dependency_security", self.test_dependency_security),
            ("secret_detection", self.test_secret_detection),
            ("static_analysis", self.test_static_analysis),
            ("authentication_security", self.test_authentication_security),
            ("data_protection", self.test_data_protection),
        ]

        for category_name, test_func in test_categories:
            logger.info(f"Running {category_name} tests...")
            try:
                self.results["tests"][category_name] = test_func()
                self.results["summary"]["total_tests"] += 1

                # Determine if test passed/failed
                test_result = self.results["tests"][category_name]
                if isinstance(test_result, dict):
                    if test_result.get("success", False):
                        self.results["summary"]["passed"] += 1
                    else:
                        self.results["summary"]["failed"] += 1
                else:
                    # Handle multiple results
                    for subtest in test_result.values():
                        if isinstance(subtest, dict) and subtest.get("success", False):
                            self.results["summary"]["passed"] += 1
                        else:
                            self.results["summary"]["failed"] += 1

            except (ValueError, RuntimeError) as e:
                logger.error(f"Error running {category_name} tests: {e}")
                self.results["tests"][category_name] = {
                    "success": False,
                    "error": str(e),
                }
                self.results["summary"]["failed"] += 1

        return self.results

    def generate_report(self, output_file: str = "security_test_report.json") -> None:
        """Generate security test report."""
        logger.info(f"Generating security test report: {output_file}")

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Security test report saved to {output_file}")

        # Print summary
        summary = self.results["summary"]
        logger.info("Security Test Summary:")
        logger.info(f"  Total Tests: {summary['total_tests']}")
        logger.info(f"  Passed: {summary['passed']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Warnings: {summary['warnings']}")


def main():
    """Main entry point for security test suite."""
    parser = argparse.ArgumentParser(description="PAKE System Security Test Suite")
    parser.add_argument(
        "--config",
        help="Path to security configuration file",
        default="security-gate-config.yaml",
    )
    parser.add_argument(
        "--output",
        help="Output file for test results",
        default="security_test_report.json",
    )
    parser.add_argument(
        "--base-url", help="Base URL for testing (for production tests)", default=None
    )

    args = parser.parse_args()

    # Initialize security test suite
    suite = SecurityTestSuite(config_path=args.config)

    # Run comprehensive tests
    results = suite.run_comprehensive_test()

    # Generate report
    suite.generate_report(output_file=args.output)

    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        logger.error("Security tests failed!")
        sys.exit(1)
    else:
        logger.info("All security tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
