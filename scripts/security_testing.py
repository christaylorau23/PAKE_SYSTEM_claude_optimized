#!/usr/bin/env python3
"""
Security Testing Suite for PAKE System
Comprehensive security validation and testing
"""

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.secure_network_config import Environment, SecureNetworkConfig
from utils.secure_serialization import SecureSerializer

logger = logging.getLogger(__name__)


@dataclass
class SecurityTestResult:
    """Result of a security test"""

    test_name: str
    passed: bool
    severity: str  # "critical", "high", "medium", "low"
    message: str
    details: dict[str, Any] | None = None


class SecurityTester:
    """Comprehensive security testing suite"""

    def __init__(self):
        self.results: list[SecurityTestResult] = []
        self.project_root = Path(__file__).parent.parent

    def run_all_tests(self) -> dict[str, Any]:
        """Run all security tests"""
        logger.info("🔒 Starting comprehensive security testing...")

        # Test categories
        self._test_dependencies()
        self._test_hash_algorithms()
        self._test_serialization_security()
        self._test_network_security()
        self._test_file_permissions()
        self._test_secrets_management()
        self._test_input_validation()

        return self._generate_report()

    def _test_dependencies(self):
        """Test for vulnerable dependencies"""
        logger.info("📦 Testing dependencies...")

        try:
            # Check if safety is available
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                self.results.append(
                    SecurityTestResult(
                        test_name="dependency_vulnerabilities",
                        passed=True,
                        severity="high",
                        message="No known vulnerabilities found in dependencies",
                    ),
                )
            else:
                vulnerabilities = json.loads(result.stdout) if result.stdout else []
                self.results.append(
                    SecurityTestResult(
                        test_name="dependency_vulnerabilities",
                        passed=False,
                        severity="high",
                        message=f"Found {len(vulnerabilities)} vulnerabilities in dependencies",
                        details={"vulnerabilities": vulnerabilities},
                    ),
                )

        except Exception as e:
            self.results.append(
                SecurityTestResult(
                    test_name="dependency_vulnerabilities",
                    passed=False,
                    severity="medium",
                    message=f"Could not check dependencies: {e}",
                ),
            )

    def _test_hash_algorithms(self):
        """Test for insecure hash algorithms"""
        logger.info("🔐 Testing hash algorithms...")

        md5_usage = []
        sha1_usage = []

        # Search for MD5 usage
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "hashlib.md5" in content:
                    md5_usage.append(str(py_file.relative_to(self.project_root)))
            except Exception:
                continue

        # Search for SHA1 usage
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "hashlib.sha1" in content:
                    sha1_usage.append(str(py_file.relative_to(self.project_root)))
            except Exception:
                continue

        if md5_usage:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_hash_md5",
                    passed=False,
                    severity="high",
                    message=f"Found MD5 usage in {len(md5_usage)} files",
                    details={"files": md5_usage},
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_hash_md5",
                    passed=True,
                    severity="high",
                    message="No MD5 usage found",
                ),
            )

        if sha1_usage:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_hash_sha1",
                    passed=False,
                    severity="medium",
                    message=f"Found SHA1 usage in {len(sha1_usage)} files",
                    details={"files": sha1_usage},
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_hash_sha1",
                    passed=True,
                    severity="medium",
                    message="No SHA1 usage found",
                ),
            )

    def _test_serialization_security(self):
        """Test for insecure serialization"""
        logger.info("📄 Testing serialization security...")

        pickle_usage = []

        # Search for pickle usage
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "pickle." in content and "import pickle" in content:
                    pickle_usage.append(str(py_file.relative_to(self.project_root)))
            except Exception:
                continue

        if pickle_usage:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_serialization_pickle",
                    passed=False,
                    severity="critical",
                    message=f"Found pickle usage in {len(pickle_usage)} files",
                    details={"files": pickle_usage},
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_serialization_pickle",
                    passed=True,
                    severity="critical",
                    message="No pickle usage found",
                ),
            )

        # Test secure serialization
        try:
            serializer = SecureSerializer()
            test_data = {"test": "data", "number": 42}

            # Test serialization
            serialized = serializer.serialize(test_data)
            deserialized = serializer.deserialize(serialized)

            if deserialized == test_data:
                self.results.append(
                    SecurityTestResult(
                        test_name="secure_serialization",
                        passed=True,
                        severity="high",
                        message="Secure serialization working correctly",
                    ),
                )
            else:
                self.results.append(
                    SecurityTestResult(
                        test_name="secure_serialization",
                        passed=False,
                        severity="high",
                        message="Secure serialization not working correctly",
                    ),
                )

        except Exception as e:
            self.results.append(
                SecurityTestResult(
                    test_name="secure_serialization",
                    passed=False,
                    severity="high",
                    message=f"Secure serialization failed: {e}",
                ),
            )

    def _test_network_security(self):
        """Test network security configuration"""
        logger.info("🌐 Testing network security...")

        insecure_bindings = []

        # Search for 0.0.0.0 bindings
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if '"0.0.0.0"' in content or "'0.0.0.0'" in content:
                    insecure_bindings.append(
                        str(py_file.relative_to(self.project_root)),
                    )
            except Exception:
                continue

        if insecure_bindings:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_network_binding",
                    passed=False,
                    severity="critical",
                    message=f"Found 0.0.0.0 bindings in {len(insecure_bindings)} files",
                    details={"files": insecure_bindings},
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_network_binding",
                    passed=True,
                    severity="critical",
                    message="No insecure network bindings found",
                ),
            )

        # Test secure network configuration
        try:
            config = SecureNetworkConfig(Environment.PRODUCTION)
            warnings = config.validate_configuration()

            if warnings:
                self.results.append(
                    SecurityTestResult(
                        test_name="network_configuration",
                        passed=False,
                        severity="high",
                        message=f"Network configuration has {len(warnings)} warnings",
                        details={"warnings": warnings},
                    ),
                )
            else:
                self.results.append(
                    SecurityTestResult(
                        test_name="network_configuration",
                        passed=True,
                        severity="high",
                        message="Network configuration is secure",
                    ),
                )

        except Exception as e:
            self.results.append(
                SecurityTestResult(
                    test_name="network_configuration",
                    passed=False,
                    severity="high",
                    message=f"Network configuration test failed: {e}",
                ),
            )

    def _test_file_permissions(self):
        """Test file permissions"""
        logger.info("📁 Testing file permissions...")

        insecure_files = []

        # Check for world-writable files
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    # Check if file is world-writable
                    if stat.st_mode & 0o002:
                        insecure_files.append(
                            str(file_path.relative_to(self.project_root)),
                        )
                except Exception:
                    continue

        if insecure_files:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_file_permissions",
                    passed=False,
                    severity="medium",
                    message=f"Found {len(insecure_files)} world-writable files",
                    details={"files": insecure_files[:10]},  # Limit output
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="insecure_file_permissions",
                    passed=True,
                    severity="medium",
                    message="No insecure file permissions found",
                ),
            )

    def _test_secrets_management(self):
        """Test secrets management"""
        logger.info("🔑 Testing secrets management...")

        hardcoded_secrets = []

        # Common secret patterns
        secret_patterns = [
            r'REDACTED_SECRET\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][^"\']{20,}["\']',  # Long keys
        ]

        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        hardcoded_secrets.append(
                            {
                                "file": str(py_file.relative_to(self.project_root)),
                                "matches": matches,
                            },
                        )
            except Exception:
                continue

        if hardcoded_secrets:
            self.results.append(
                SecurityTestResult(
                    test_name="hardcoded_secrets",
                    passed=False,
                    severity="critical",
                    message=f"Found potential hardcoded secrets in {len(hardcoded_secrets)} files",
                    details={"secrets": hardcoded_secrets[:5]},  # Limit output
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="hardcoded_secrets",
                    passed=True,
                    severity="critical",
                    message="No hardcoded secrets found",
                ),
            )

    def _test_input_validation(self):
        """Test input validation"""
        logger.info("✅ Testing input validation...")

        # This is a basic test - in a real scenario, you'd want more comprehensive testing
        validation_issues = []

        # Look for potential SQL injection patterns
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if 'f"SELECT' in content or "f'SELECT" in content:
                    validation_issues.append(
                        str(py_file.relative_to(self.project_root)),
                    )
            except Exception:
                continue

        if validation_issues:
            self.results.append(
                SecurityTestResult(
                    test_name="input_validation",
                    passed=False,
                    severity="high",
                    message=f"Found potential SQL injection risks in {len(validation_issues)} files",
                    details={"files": validation_issues},
                ),
            )
        else:
            self.results.append(
                SecurityTestResult(
                    test_name="input_validation",
                    passed=True,
                    severity="high",
                    message="No obvious input validation issues found",
                ),
            )

    def _generate_report(self) -> dict[str, Any]:
        """Generate comprehensive security report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        # Categorize by severity
        critical_failed = [
            r for r in self.results if not r.passed and r.severity == "critical"
        ]
        high_failed = [r for r in self.results if not r.passed and r.severity == "high"]
        medium_failed = [
            r for r in self.results if not r.passed and r.severity == "medium"
        ]
        low_failed = [r for r in self.results if not r.passed and r.severity == "low"]

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": f"{(passed_tests / total_tests * 100):.1f}%",
            },
            "severity_breakdown": {
                "critical_failed": len(critical_failed),
                "high_failed": len(high_failed),
                "medium_failed": len(medium_failed),
                "low_failed": len(low_failed),
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> list[str]:
        """Generate security recommendations"""
        recommendations = []

        failed_tests = [r for r in self.results if not r.passed]

        if any(r.test_name == "dependency_vulnerabilities" for r in failed_tests):
            recommendations.append(
                "Update vulnerable dependencies using: pip install --upgrade -r requirements.txt",
            )

        if any(r.test_name == "insecure_hash_md5" for r in failed_tests):
            recommendations.append("Replace all MD5 usage with SHA-256")

        if any(r.test_name == "insecure_serialization_pickle" for r in failed_tests):
            recommendations.append(
                "Replace pickle usage with secure serialization (JSON/MessagePack)",
            )

        if any(r.test_name == "insecure_network_binding" for r in failed_tests):
            recommendations.append(
                "Replace 0.0.0.0 bindings with specific interface addresses",
            )

        if any(r.test_name == "hardcoded_secrets" for r in failed_tests):
            recommendations.append("Move hardcoded secrets to environment variables")

        return recommendations


def main():
    """Main entry point for security testing"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    tester = SecurityTester()
    report = tester.run_all_tests()

    # Print summary
    print("\n" + "=" * 60)
    print("🔒 PAKE SYSTEM SECURITY TEST REPORT")
    print("=" * 60)

    summary = report["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']}")

    severity = report["severity_breakdown"]
    print("\nSeverity Breakdown:")
    print(f"  Critical Issues: {severity['critical_failed']}")
    print(f"  High Issues: {severity['high_failed']}")
    print(f"  Medium Issues: {severity['medium_failed']}")
    print(f"  Low Issues: {severity['low_failed']}")

    # Print failed tests
    failed_tests = [r for r in report["results"] if not r["passed"]]
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(
                f"  [{test['severity'].upper()}] {test['test_name']}: {test['message']}",
            )

    # Print recommendations
    if report["recommendations"]:
        print("\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")

    # Save detailed report
    report_file = Path(__file__).parent.parent / "security_test_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: {report_file}")

    # Exit with error code if critical issues found
    if severity["critical_failed"] > 0:
        print("\n🚨 CRITICAL SECURITY ISSUES FOUND! Please fix before deployment.")
        sys.exit(1)
    elif severity["high_failed"] > 0:
        print(
            "\n⚠️  HIGH PRIORITY SECURITY ISSUES FOUND! Consider fixing before deployment.",
        )
        sys.exit(1)
    else:
        print("\n✅ Security tests completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
