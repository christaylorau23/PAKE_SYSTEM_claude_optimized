#!/usr/bin/env python3
"""Phase 3: Hardening the Application and API Layers
World-Class Finish Guide - OWASP-based security vulnerability triage and GraphQL hardening.
"""

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests


class OWASPCategory(Enum):
    """OWASP Top 10 2021 categories."""

    BROKEN_ACCESS_CONTROL = "A01:2021-Broken Access Control"
    CRYPTOGRAPHIC_FAILURES = "A02:2021-Cryptographic Failures"
    INJECTION = "A03:2021-Injection"
    INSECURE_DESIGN = "A04:2021-Insecure Design"
    SECURITY_MISCONFIGURATION = "A05:2021-Security Misconfiguration"
    VULNERABLE_COMPONENTS = "A06:2021-Vulnerable and Outdated Components"
    IDENTIFICATION_FAILURES = "A07:2021-Identification and Authentication Failures"
    SOFTWARE_DATA_INTEGRITY = "A08:2021-Software and Data Integrity Failures"
    LOGGING_MONITORING_FAILURES = "A09:2021-Security Logging and Monitoring Failures"
    SERVER_SIDE_REQUEST_FORGERY = "A10:2021-Server-Side Request Forgery (SSRF)"


@dataclass
class SecurityVulnerability:
    """Represents a security vulnerability."""

    id: str
    category: OWASPCategory
    severity: str
    description: str
    file_path: str
    line_number: int
    remediation_pattern: str
    business_impact: int  # 1-5 scale
    remediation_effort: str  # S, M, L, XL


class SecurityTriageFramework:
    """OWASP-based security vulnerability triage framework."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.vulnerabilities: list[SecurityVulnerability] = []
        self.remediation_patterns = self._load_remediation_patterns()

    def _load_remediation_patterns(self) -> dict[str, str]:
        """Load standard remediation patterns."""
        return {
            "information_leakage": "Implement global exception handler with sanitized error messages",
            "security_misconfiguration": "Harden server configurations and disable unnecessary headers",
            "vulnerable_components": "Implement automated dependency scanning and update policy",
            "poor_logging": "Configure loggers to filter sensitive fields and implement security event logging",
            "weak_crypto": "Replace weak random generators with cryptographically secure alternatives",
            "injection_risks": "Implement strict input validation and parameterized queries",
            "access_control": "Implement proper authentication and authorization mechanisms",
        }

    def analyze_security_vulnerabilities(self) -> list[SecurityVulnerability]:
        """Analyze security vulnerabilities using multiple tools."""
        print("🔍 Analyzing security vulnerabilities...")

        vulnerabilities = []

        # Analyze with ruff security rules
        vulnerabilities.extend(self._analyze_ruff_security())

        # Analyze with bandit if available
        vulnerabilities.extend(self._analyze_bandit_security())

        # Analyze dependency vulnerabilities
        vulnerabilities.extend(self._analyze_dependency_vulnerabilities())

        self.vulnerabilities = vulnerabilities
        return vulnerabilities

    def _analyze_ruff_security(self) -> list[SecurityVulnerability]:
        """Analyze security issues using ruff security rules."""
        vulnerabilities = []

        try:
            result = subprocess.run(
                ["ruff", "check", "--select=S", "--no-fix"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            lines = result.stdout.split("\n")
            current_file = None

            for line in lines:
                if "-->" in line and ".py:" in line:
                    match = re.search(r"--> ([^:]+):(\d+)", line)
                    if match:
                        current_file = match.group(1)
                        line_number = int(match.group(2))

                if current_file and "S" in line:
                    # Parse security rule
                    if "S311" in line:  # Suspicious non-cryptographic random usage
                        vulnerabilities.append(
                            SecurityVulnerability(
                                id=f"S311_{current_file}_{line_number}",
                                category=OWASPCategory.CRYPTOGRAPHIC_FAILURES,
                                severity="Medium",
                                description="Use of weak random number generator",
                                file_path=current_file,
                                line_number=line_number,
                                remediation_pattern=self.remediation_patterns[
                                    "weak_crypto"
                                ],
                                business_impact=3,
                                remediation_effort="S",
                            )
                        )
                    elif "S607" in line:  # Start process with partial path
                        vulnerabilities.append(
                            SecurityVulnerability(
                                id=f"S607_{current_file}_{line_number}",
                                category=OWASPCategory.INJECTION,
                                severity="High",
                                description="Process execution with partial path",
                                file_path=current_file,
                                line_number=line_number,
                                remediation_pattern=self.remediation_patterns[
                                    "injection_risks"
                                ],
                                business_impact=4,
                                remediation_effort="M",
                            )
                        )
                    elif "S603" in line:  # Subprocess without shell equals true
                        vulnerabilities.append(
                            SecurityVulnerability(
                                id=f"S603_{current_file}_{line_number}",
                                category=OWASPCategory.INJECTION,
                                severity="Medium",
                                description="Subprocess call without shell security",
                                file_path=current_file,
                                line_number=line_number,
                                remediation_pattern=self.remediation_patterns[
                                    "injection_risks"
                                ],
                                business_impact=3,
                                remediation_effort="S",
                            )
                        )
                    elif "S101" in line:  # Use of assert
                        vulnerabilities.append(
                            SecurityVulnerability(
                                id=f"S101_{current_file}_{line_number}",
                                category=OWASPCategory.SECURITY_MISCONFIGURATION,
                                severity="Low",
                                description="Use of assert statement",
                                file_path=current_file,
                                line_number=line_number,
                                remediation_pattern="Replace assert with proper error handling",
                                business_impact=2,
                                remediation_effort="S",
                            )
                        )

        except Exception as e:
            print(f"Error analyzing ruff security: {e}")

        return vulnerabilities

    def _analyze_bandit_security(self) -> list[SecurityVulnerability]:
        """Analyze security issues using bandit."""
        vulnerabilities = []

        try:
            result = subprocess.run(
                ["bandit", "-r", "src/", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout:
                bandit_data = json.loads(result.stdout)

                for issue in bandit_data.get("results", []):
                    vulnerabilities.append(
                        SecurityVulnerability(
                            id=f"BANDIT_{issue['test_id']}_{issue['filename']}_{issue['line_number']}",
                            category=self._map_bandit_to_owasp(issue["test_id"]),
                            severity=issue["issue_severity"].title(),
                            description=issue["issue_text"],
                            file_path=issue["filename"],
                            line_number=issue["line_number"],
                            remediation_pattern=self._get_bandit_remediation(
                                issue["test_id"]
                            ),
                            business_impact=self._calculate_business_impact(
                                issue["issue_severity"]
                            ),
                            remediation_effort=self._estimate_effort(
                                issue["issue_severity"]
                            ),
                        )
                    )

        except Exception as e:
            print(f"Error analyzing bandit security: {e}")

        return vulnerabilities

    def _analyze_dependency_vulnerabilities(self) -> list[SecurityVulnerability]:
        """Analyze dependency vulnerabilities."""
        vulnerabilities = []

        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0 and result.stdout:
                safety_data = json.loads(result.stdout)

                for vuln in safety_data:
                    vulnerabilities.append(
                        SecurityVulnerability(
                            id=f"SAFETY_{vuln['package']}_{vuln['installed_version']}",
                            category=OWASPCategory.VULNERABLE_COMPONENTS,
                            severity=vuln["severity"].title(),
                            description=f"Vulnerable dependency: {vuln['package']} {vuln['installed_version']}",
                            file_path="requirements.txt",
                            line_number=0,
                            remediation_pattern=self.remediation_patterns[
                                "vulnerable_components"
                            ],
                            business_impact=self._calculate_business_impact(
                                vuln["severity"]
                            ),
                            remediation_effort="M",
                        )
                    )

        except Exception as e:
            print(f"Error analyzing dependency vulnerabilities: {e}")

        return vulnerabilities

    def _map_bandit_to_owasp(self, test_id: str) -> OWASPCategory:
        """Map bandit test ID to OWASP category."""
        mapping = {
            "B101": OWASPCategory.SECURITY_MISCONFIGURATION,  # assert_used
            "B102": OWASPCategory.INJECTION,  # exec_used
            "B103": OWASPCategory.INJECTION,  # set_bad_file_permissions
            "B104": OWASPCategory.SECURITY_MISCONFIGURATION,  # hardcoded_bind_all_interfaces
            "B105": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # hardcoded_password_string
            "B106": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # hardcoded_password_funcarg
            "B107": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # hardcoded_password_default
            "B108": OWASPCategory.SECURITY_MISCONFIGURATION,  # hardcoded_tmp_directory
            "B110": OWASPCategory.INJECTION,  # try_except_pass
            "B112": OWASPCategory.SECURITY_MISCONFIGURATION,  # try_except_continue
            "B201": OWASPCategory.INJECTION,  # flask_debug_true
            "B301": OWASPCategory.INJECTION,  # pickle
            "B302": OWASPCategory.INJECTION,  # marshal
            "B303": OWASPCategory.INJECTION,  # md5
            "B304": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # cipher
            "B305": OWASPCategory.INJECTION,  # cipher_mode
            "B306": OWASPCategory.INJECTION,  # mktemp_q
            "B307": OWASPCategory.INJECTION,  # eval
            "B308": OWASPCategory.INJECTION,  # mark_safe
            "B309": OWASPCategory.INJECTION,  # httpsconnection
            "B310": OWASPCategory.INJECTION,  # urllib_urlopen
            "B311": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # random
            "B312": OWASPCategory.INJECTION,  # telnetlib
            "B313": OWASPCategory.INJECTION,  # xml_bad_cElementTree
            "B314": OWASPCategory.INJECTION,  # xml_bad_ElementTree
            "B315": OWASPCategory.INJECTION,  # xml_bad_expatreader
            "B316": OWASPCategory.INJECTION,  # xml_bad_expatbuilder
            "B317": OWASPCategory.INJECTION,  # xml_bad_sax
            "B318": OWASPCategory.INJECTION,  # xml_bad_minidom
            "B319": OWASPCategory.INJECTION,  # xml_bad_pulldom
            "B320": OWASPCategory.INJECTION,  # xml_bad_etree
            "B321": OWASPCategory.INJECTION,  # ftplib
            "B322": OWASPCategory.INJECTION,  # input
            "B323": OWASPCategory.INJECTION,  # unverified_context
            "B324": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # hashlib_new_insecure_functions
            "B325": OWASPCategory.CRYPTOGRAPHIC_FAILURES,  # tempnam
            "B501": OWASPCategory.INJECTION,  # request_with_no_cert_validation
            "B502": OWASPCategory.INJECTION,  # ssl_with_bad_version
            "B503": OWASPCategory.INJECTION,  # ssl_with_bad_defaults
            "B504": OWASPCategory.INJECTION,  # ssl_with_no_version
            "B505": OWASPCategory.INJECTION,  # weak_cryptographic_key
            "B506": OWASPCategory.INJECTION,  # yaml_load
            "B507": OWASPCategory.INJECTION,  # ssh_no_host_key_verification
            "B601": OWASPCategory.INJECTION,  # paramiko_calls
            "B602": OWASPCategory.INJECTION,  # subprocess_popen_with_shell_equals_true
            "B603": OWASPCategory.INJECTION,  # subprocess_without_shell_equals_true
            "B604": OWASPCategory.INJECTION,  # any_other_function_with_shell_equals_true
            "B605": OWASPCategory.INJECTION,  # start_process_with_a_shell
            "B606": OWASPCategory.INJECTION,  # start_process_with_no_shell
            "B607": OWASPCategory.INJECTION,  # start_process_with_partial_path
            "B608": OWASPCategory.INJECTION,  # hardcoded_sql_expressions
            "B609": OWASPCategory.INJECTION,  # linux_commands_wildcard_injection
            "B610": OWASPCategory.INJECTION,  # django_extra_used
            "B611": OWASPCategory.INJECTION,  # django_rawsql_used
            "B612": OWASPCategory.INJECTION,  # logging_injection
            "B613": OWASPCategory.INJECTION,  # python_jwt_used
            "B614": OWASPCategory.INJECTION,  # django_mark_safe
            "B615": OWASPCategory.INJECTION,  # django_extra_used
            "B616": OWASPCategory.INJECTION,  # django_rawsql_used
            "B617": OWASPCategory.INJECTION,  # django_extra_used
            "B618": OWASPCategory.INJECTION,  # django_rawsql_used
            "B619": OWASPCategory.INJECTION,  # django_extra_used
            "B620": OWASPCategory.INJECTION,  # django_rawsql_used
        }

        return mapping.get(test_id, OWASPCategory.SECURITY_MISCONFIGURATION)

    def _get_bandit_remediation(self, test_id: str) -> str:
        """Get remediation pattern for bandit test ID."""
        remediation_map = {
            "B101": "Replace assert with proper error handling",
            "B102": "Avoid using exec() with user input",
            "B105": "Use environment variables or secure configuration for passwords",
            "B311": "Use cryptographically secure random number generators",
            "B602": "Avoid shell=True in subprocess calls",
            "B603": "Use shell=False and proper argument lists",
            "B607": "Use absolute paths for process execution",
        }

        return remediation_map.get(
            test_id, "Review and implement secure coding practices"
        )

    def _calculate_business_impact(self, severity: str) -> int:
        """Calculate business impact score (1-5)."""
        impact_map = {
            "HIGH": 5,
            "MEDIUM": 3,
            "LOW": 2,
            "CRITICAL": 5,
        }

        return impact_map.get(severity.upper(), 2)

    def _estimate_effort(self, severity: str) -> str:
        """Estimate remediation effort."""
        effort_map = {
            "HIGH": "L",
            "MEDIUM": "M",
            "LOW": "S",
            "CRITICAL": "XL",
        }

        return effort_map.get(severity.upper(), "M")

    def prioritize_vulnerabilities(self) -> list[SecurityVulnerability]:
        """Prioritize vulnerabilities using OWASP framework."""

        def priority_score(vuln: SecurityVulnerability) -> int:
            # Priority = Business Impact + Severity Score
            severity_scores = {"Critical": 5, "High": 4, "Medium": 3, "Low": 2}
            severity_score = severity_scores.get(vuln.severity, 2)
            return vuln.business_impact + severity_score

        return sorted(self.vulnerabilities, key=priority_score, reverse=True)

    def generate_security_report(self) -> str:
        """Generate comprehensive security report."""
        report = []
        report.append("# Phase 3: Security Vulnerability Triage Report")
        report.append("")
        report.append(f"**Analysis Date**: {Path().cwd()}")
        report.append("")

        # Summary
        report.append("## 🎯 Security Analysis Summary")
        report.append("")
        report.append(f"- **Total Vulnerabilities**: {len(self.vulnerabilities)}")

        # Group by severity
        severity_counts = {}
        for vuln in self.vulnerabilities:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1

        for severity, count in severity_counts.items():
            report.append(f"- **{severity}**: {count}")
        report.append("")

        # OWASP Categories
        report.append("## 🛡️ OWASP Top 10 2021 Analysis")
        report.append("")
        category_counts = {}
        for vuln in self.vulnerabilities:
            category_counts[vuln.category] = category_counts.get(vuln.category, 0) + 1

        for category, count in category_counts.items():
            report.append(f"- **{category.value}**: {count}")
        report.append("")

        # Top Priority Vulnerabilities
        prioritized = self.prioritize_vulnerabilities()
        report.append("## 🚨 Top Priority Vulnerabilities")
        report.append("")

        for i, vuln in enumerate(prioritized[:10], 1):
            report.append(f"### {i}. {vuln.id}")
            report.append(f"- **Category**: {vuln.category.value}")
            report.append(f"- **Severity**: {vuln.severity}")
            report.append(f"- **File**: {vuln.file_path}:{vuln.line_number}")
            report.append(f"- **Description**: {vuln.description}")
            report.append(f"- **Remediation**: {vuln.remediation_pattern}")
            report.append(f"- **Business Impact**: {vuln.business_impact}/5")
            report.append(f"- **Effort**: {vuln.remediation_effort}")
            report.append("")

        # Remediation Recommendations
        report.append("## 🔧 Remediation Recommendations")
        report.append("")
        report.append("### Immediate Actions (High Priority)")
        report.append("1. **Implement Global Exception Handler**")
        report.append("   - Prevent information leakage through error messages")
        report.append("   - Log full stack traces server-side only")
        report.append("")
        report.append("2. **Replace Weak Random Generators**")
        report.append("   - Use `secrets` module for cryptographic operations")
        report.append("   - Replace `random` with `secrets` where security is critical")
        report.append("")
        report.append("3. **Secure Subprocess Calls**")
        report.append("   - Use `shell=False` and proper argument lists")
        report.append("   - Validate and sanitize all input parameters")
        report.append("")
        report.append("### Medium-term Actions")
        report.append("1. **Implement Dependency Scanning**")
        report.append("   - Integrate Dependabot or Snyk into CI/CD pipeline")
        report.append("   - Establish regular dependency update policy")
        report.append("")
        report.append("2. **Enhance Logging Security**")
        report.append("   - Filter sensitive fields from logs")
        report.append("   - Implement security event monitoring")
        report.append("")

        return "\n".join(report)


def main():
    """Main execution function for Phase 3 security analysis."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    print("🚀 Starting Phase 3: Security Vulnerability Triage...")

    # Initialize security framework
    security_framework = SecurityTriageFramework(project_root)

    # Analyze vulnerabilities
    vulnerabilities = security_framework.analyze_security_vulnerabilities()

    # Generate report
    report = security_framework.generate_security_report()
    with open("PHASE_3_SECURITY_TRIAGE_REPORT.md", "w") as f:
        f.write(report)

    print("✅ Phase 3 Security Analysis Complete!")
    print("📄 Report written to: PHASE_3_SECURITY_TRIAGE_REPORT.md")
    print(f"🎯 Total Vulnerabilities Found: {len(vulnerabilities)}")

    # Show top 5 vulnerabilities
    prioritized = security_framework.prioritize_vulnerabilities()
    print("\n🚨 Top 5 Priority Vulnerabilities:")
    for i, vuln in enumerate(prioritized[:5], 1):
        print(f"{i}. {vuln.severity} - {vuln.description} ({vuln.file_path})")


if __name__ == "__main__":
    main()
