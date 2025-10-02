#!/usr/bin/env python3
"""
Test suite for weak hashing and insecure network binding remediation.

This test suite validates that:
1. No weak hashing algorithms (MD5/SHA1) are used for security purposes
2. All network bindings use secure addresses instead of 0.0.0.0
"""

import re
from pathlib import Path

import pytest


class TestHashingNetworkRemediation:
    """Test weak hashing and network binding remediation."""

    def setup_method(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.src_dir = self.project_root / "src"
        self.config_dir = self.project_root / "configs"
        self.deploy_dir = self.project_root / "deploy"

    def test_no_weak_hashing_in_source(self):
        """Test that no weak hashing algorithms are used in source code."""
        weak_hash_patterns = [
            r"hashlib\.md5\(",
            r"hashlib\.sha1\(",
            r"MD5\(",
            r"SHA1\(",
            r"md5sum",
            r"sha1sum",
        ]

        vulnerable_files = []

        # Search in src directory
        for py_file in self.src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for pattern in weak_hash_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        # Check if it's used for security purposes
                        if self._is_security_related_usage(content, pattern):
                            vulnerable_files.append(
                                str(py_file.relative_to(self.project_root))
                            )
                            break
            except Exception:
                continue

        assert (
            len(vulnerable_files) == 0
        ), f"Found weak hashing in source files: {vulnerable_files}"

    def test_secure_network_bindings(self):
        """Test that all network bindings use secure addresses."""
        insecure_bindings = []

        # Search for 0.0.0.0 bindings in production source files only
        for py_file in self.src_dir.rglob("*.py"):
            # Skip the secure network config utility as it legitimately mentions 0.0.0.0 for security checks
            if "secure_network_config.py" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                if "0.0.0.0" in content:
                    # Check if it's a network binding
                    if self._is_network_binding(content):
                        insecure_bindings.append(
                            str(py_file.relative_to(self.project_root))
                        )
            except Exception:
                continue

        # Search in specific configuration files that we fixed
        config_files = [
            "docker-compose.performance.yml",
            "deploy/docker/base/docker-compose.base.yml",
            "ai-security-config.yml",
        ]

        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text(encoding="utf-8")
                    if "0.0.0.0" in content and self._is_network_binding(content):
                        insecure_bindings.append(config_file)
                except Exception:
                    continue

        assert (
            len(insecure_bindings) == 0
        ), f"Found insecure 0.0.0.0 bindings in production code: {insecure_bindings}"

    def test_secure_hashing_algorithms_used(self):
        """Test that secure hashing algorithms are used for passwords."""
        secure_hash_files = []

        # Check for Argon2 usage
        for py_file in self.src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "argon2" in content.lower() or "Argon2" in content:
                    secure_hash_files.append(
                        str(py_file.relative_to(self.project_root))
                    )
            except Exception:
                continue

        # Check for bcrypt usage
        for py_file in self.src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "bcrypt" in content.lower() or "CryptContext" in content:
                    secure_hash_files.append(
                        str(py_file.relative_to(self.project_root))
                    )
            except Exception:
                continue

        assert (
            len(secure_hash_files) > 0
        ), "No secure hashing algorithms found in source code"

        # Verify specific files use secure hashing
        expected_secure_files = [
            "src/services/authentication/jwt_auth_service.py",
            "src/services/base/auth.py",
        ]

        for expected_file in expected_secure_files:
            file_path = self.project_root / expected_file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                assert (
                    "argon2" in content.lower() or "bcrypt" in content.lower()
                ), f"Expected secure hashing in {expected_file}"

    def test_network_binding_security(self):
        """Test that network bindings use secure local addresses."""
        secure_bindings = []

        # Check for 127.0.0.1 bindings
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "127.0.0.1" in content and self._is_network_binding(content):
                    secure_bindings.append(str(py_file.relative_to(self.project_root)))
            except Exception:
                continue

        # Check configuration files
        config_files = [
            "docker-compose.performance.yml",
            "deploy/docker/base/docker-compose.base.yml",
            "ai-security-config.yml",
        ]

        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text(encoding="utf-8")
                    if "127.0.0.1" in content and self._is_network_binding(content):
                        secure_bindings.append(config_file)
                except Exception:
                    continue

        assert len(secure_bindings) > 0, "No secure network bindings found"

        # Verify specific files use secure bindings
        expected_secure_files = [
            "src/pake_system/auth/example_app.py",
            "src/services/observability/monitoring_service.py",
            "src/services/orchestration/service_registry.py",
            "src/services/orchestration/api_gateway.py",
        ]

        for expected_file in expected_secure_files:
            file_path = self.project_root / expected_file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                assert (
                    "127.0.0.1" in content
                ), f"Expected secure binding in {expected_file}"

    def test_no_md5_sha1_in_security_context(self):
        """Test that MD5/SHA1 are not used in security contexts."""
        security_context_patterns = [
            r"password.*md5",
            r"password.*sha1",
            r"hash.*password.*md5",
            r"hash.*password.*sha1",
            r"REDACTED_SECRET.*md5",
            r"REDACTED_SECRET.*sha1",
            r"auth.*md5",
            r"auth.*sha1",
            r"token.*md5",
            r"token.*sha1",
        ]

        vulnerable_files = []

        for py_file in self.src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for pattern in security_context_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        vulnerable_files.append(
                            str(py_file.relative_to(self.project_root))
                        )
                        break
            except Exception:
                continue

        assert (
            len(vulnerable_files) == 0
        ), f"Found MD5/SHA1 in security context: {vulnerable_files}"

    def test_secure_network_configuration(self):
        """Test that network configuration uses secure defaults."""
        # Check that secure network config utility exists and is used
        secure_config_file = self.project_root / "src/utils/secure_network_config.py"
        assert (
            secure_config_file.exists()
        ), "Secure network configuration utility not found"

        content = secure_config_file.read_text(encoding="utf-8")

        # Verify it contains security checks
        assert "0.0.0.0" in content, "Secure network config should check for 0.0.0.0"
        assert "127.0.0.1" in content, "Secure network config should use 127.0.0.1"
        assert (
            "insecure" in content.lower()
        ), "Secure network config should detect insecure bindings"

    def _is_security_related_usage(self, content: str, pattern: str) -> bool:
        """Check if hash usage is security-related."""
        security_keywords = [
            "password",
            "REDACTED_SECRET",
            "auth",
            "token",
            "session",
            "credential",
            "login",
            "user",
            "security",
            "hash",
        ]

        # Get context around the pattern
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                # Check surrounding lines for security context
                context_lines = lines[max(0, i - 2) : i + 3]
                context = " ".join(context_lines).lower()

                for keyword in security_keywords:
                    if keyword in context:
                        return True

        return False

    def _is_network_binding(self, content: str) -> bool:
        """Check if 0.0.0.0 usage is a network binding."""
        binding_keywords = [
            "host",
            "bind",
            "listen",
            "address",
            "server",
            "uvicorn",
            "run",
            "port",
            "endpoint",
            "api_host",
            "uvicorn_host",
        ]

        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "0.0.0.0" in line:
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                # Check if it's in a comment within the line
                if "#" in line:
                    code_part = line.split("#")[0]
                    if "0.0.0.0" not in code_part:
                        continue

                # Check surrounding lines for binding context
                context_lines = lines[max(0, i - 2) : i + 3]
                context = " ".join(context_lines).lower()

                for keyword in binding_keywords:
                    if keyword in context:
                        return True

        return False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
