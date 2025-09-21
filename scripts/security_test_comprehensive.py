#!/usr/bin/env python3
"""
Comprehensive Security Testing Script for PAKE System
World-class security validation with TDD approach
"""

import os
import sys
import json
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


class SecuritySeverity(Enum):
    """Security issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SecurityIssue:
    """Security issue representation"""
    test_name: str
    severity: SecuritySeverity
    message: str
    file_path: str = ""
    line_number: int = 0
    details: Dict[str, Any] = None
    passed: bool = False


@dataclass
class SecurityTestResult:
    """Security test result"""
    test_name: str
    passed: bool
    severity: SecuritySeverity
    message: str
    details: Dict[str, Any] = None


class SecurityTester:
    """Comprehensive security testing framework"""

    def __init__(self):
        self.issues: List[SecurityIssue] = []
        self.results: List[SecurityTestResult] = []
        self.project_root = Path(__file__).parent.parent

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests and return comprehensive report"""
        logger.info("🔒 Starting comprehensive security testing...")

        # Run all security tests
        self.test_dependency_vulnerabilities()
        self.test_insecure_hash_algorithms()
        self.test_insecure_serialization()
        self.test_secure_serialization()
        self.test_network_security()
        self.test_file_permissions()
        self.test_hardcoded_secrets()
        self.test_input_validation()
        self.test_environment_configuration()
        self.test_ci_cd_security()

        # Generate report
        return self.generate_report()

    def test_dependency_vulnerabilities(self) -> None:
        """Test for vulnerable dependencies"""
        logger.info("📦 Testing dependencies...")
        
        try:
            # Check if safety is available
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.results.append(SecurityTestResult(
                    test_name="dependency_vulnerabilities",
                    passed=True,
                    severity=SecuritySeverity.MEDIUM,
                    message="No vulnerable dependencies found"
                ))
            else:
                vulnerabilities = json.loads(result.stdout) if result.stdout else []
                self.results.append(SecurityTestResult(
                    test_name="dependency_vulnerabilities",
                    passed=False,
                    severity=SecuritySeverity.MEDIUM,
                    message=f"Found {len(vulnerabilities)} vulnerable dependencies",
                    details={"vulnerabilities": vulnerabilities}
                ))
                
        except subprocess.TimeoutExpired:
            self.results.append(SecurityTestResult(
                test_name="dependency_vulnerabilities",
                passed=False,
                severity=SecuritySeverity.MEDIUM,
                message="Dependency check timed out"
            ))
        except FileNotFoundError:
            self.results.append(SecurityTestResult(
                test_name="dependency_vulnerabilities",
                passed=False,
                severity=SecuritySeverity.MEDIUM,
                message="Safety tool not found - install with: pip install safety"
            ))
        except Exception as e:
            self.results.append(SecurityTestResult(
                test_name="dependency_vulnerabilities",
                passed=False,
                severity=SecuritySeverity.MEDIUM,
                message=f"Dependency check failed: {str(e)}"
            ))

    def test_insecure_hash_algorithms(self) -> None:
        """Test for insecure hash algorithm usage"""
        logger.info("🔐 Testing hash algorithms...")
        
        md5_files = []
        sha1_files = []
        
        # Search for MD5 usage
        md5_patterns = [
            "hashlib.md5",
            "md5(",
            "MD5",
            "md5sum"
        ]
        
        # Search for SHA1 usage
        sha1_patterns = [
            "hashlib.sha1",
            "sha1(",
            "SHA1",
            "sha1sum"
        ]
        
        for pattern in md5_patterns:
            result = subprocess.run(
                ["grep", "-r", "-n", pattern, "src/", "scripts/"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                md5_files.extend(result.stdout.strip().split('\n'))
        
        for pattern in sha1_patterns:
            result = subprocess.run(
                ["grep", "-r", "-n", pattern, "src/", "scripts/"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                sha1_files.extend(result.stdout.strip().split('\n'))
        
        # Filter out false positives (secure_serialization.py uses SHA256)
        md5_files = [f for f in md5_files if "sha256" not in f.lower()]
        sha1_files = [f for f in sha1_files if "sha256" not in f.lower()]
        
        if md5_files:
            self.results.append(SecurityTestResult(
                test_name="insecure_hash_md5",
                passed=False,
                severity=SecuritySeverity.HIGH,
                message=f"Found MD5 usage in {len(md5_files)} files",
                details={"files": md5_files}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="insecure_hash_md5",
                passed=True,
                severity=SecuritySeverity.HIGH,
                message="No MD5 usage found"
            ))
        
        if sha1_files:
            self.results.append(SecurityTestResult(
                test_name="insecure_hash_sha1",
                passed=False,
                severity=SecuritySeverity.MEDIUM,
                message=f"Found SHA1 usage in {len(sha1_files)} files",
                details={"files": sha1_files}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="insecure_hash_sha1",
                passed=True,
                severity=SecuritySeverity.MEDIUM,
                message="No SHA1 usage found"
            ))

    def test_insecure_serialization(self) -> None:
        """Test for insecure serialization (pickle) usage"""
        logger.info("📄 Testing serialization security...")
        
        pickle_files = []
        
        # Search for pickle usage
        pickle_patterns = [
            "import pickle",
            "pickle.loads",
            "pickle.dumps",
            "pickle.load",
            "pickle.dump"
        ]
        
        for pattern in pickle_patterns:
            result = subprocess.run(
                ["grep", "-r", "-n", pattern, "src/", "scripts/"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                pickle_files.extend(result.stdout.strip().split('\n'))
        
        # Filter out migration utilities and test files
        pickle_files = [f for f in pickle_files if "migrate_from_pickle" not in f and "test_" not in f]
        
        if pickle_files:
            self.results.append(SecurityTestResult(
                test_name="insecure_serialization_pickle",
                passed=False,
                severity=SecuritySeverity.CRITICAL,
                message=f"Found pickle usage in {len(pickle_files)} files",
                details={"files": pickle_files}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="insecure_serialization_pickle",
                passed=True,
                severity=SecuritySeverity.CRITICAL,
                message="No insecure pickle usage found"
            ))

    def test_secure_serialization(self) -> None:
        """Test secure serialization functionality"""
        logger.info("🔒 Testing secure serialization...")
        
        try:
            from utils.secure_serialization import serialize, deserialize, SerializationFormat
            
            # Test basic serialization
            test_data = {"test": "data", "number": 42}
            serialized = serialize(test_data)
            deserialized = deserialize(serialized)
            
            if deserialized == test_data:
                self.results.append(SecurityTestResult(
                    test_name="secure_serialization",
                    passed=True,
                    severity=SecuritySeverity.HIGH,
                    message="Secure serialization working correctly"
                ))
            else:
                self.results.append(SecurityTestResult(
                    test_name="secure_serialization",
                    passed=False,
                    severity=SecuritySeverity.HIGH,
                    message="Secure serialization data mismatch"
                ))
                
        except Exception as e:
            self.results.append(SecurityTestResult(
                test_name="secure_serialization",
                passed=False,
                severity=SecuritySeverity.HIGH,
                message=f"Secure serialization failed: {str(e)}"
            ))

    def test_network_security(self) -> None:
        """Test network security configuration"""
        logger.info("🌐 Testing network security...")
        
        insecure_bindings = []
        
        # Search for 0.0.0.0 bindings
        result = subprocess.run(
            ["grep", "-r", "-n", "0\\.0\\.0\\.0", "src/", "scripts/"],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            insecure_bindings.extend(result.stdout.strip().split('\n'))
        
        # Filter out comments and documentation
        insecure_bindings = [f for f in insecure_bindings if not any(
            word in f.lower() for word in ["comment", "todo", "fixme", "note", "example"]
        )]
        
        if insecure_bindings:
            self.results.append(SecurityTestResult(
                test_name="insecure_network_binding",
                passed=False,
                severity=SecuritySeverity.CRITICAL,
                message=f"Found 0.0.0.0 bindings in {len(insecure_bindings)} files",
                details={"files": insecure_bindings}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="insecure_network_binding",
                passed=True,
                severity=SecuritySeverity.CRITICAL,
                message="No insecure network bindings found"
            ))

    def test_file_permissions(self) -> None:
        """Test file permissions security"""
        logger.info("📁 Testing file permissions...")
        
        insecure_files = []
        
        # Check for world-writable files
        result = subprocess.run(
            ["find", "src/", "scripts/", "-type", "f", "-perm", "-002"],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            insecure_files.extend(result.stdout.strip().split('\n'))
        
        if insecure_files:
            self.results.append(SecurityTestResult(
                test_name="insecure_file_permissions",
                passed=False,
                severity=SecuritySeverity.MEDIUM,
                message=f"Found {len(insecure_files)} files with insecure permissions",
                details={"files": insecure_files}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="insecure_file_permissions",
                passed=True,
                severity=SecuritySeverity.MEDIUM,
                message="No insecure file permissions found"
            ))

    def test_hardcoded_secrets(self) -> None:
        """Test for hardcoded secrets"""
        logger.info("🔑 Testing secrets management...")
        
        secret_patterns = [
            r'REDACTED_SECRET\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']'
        ]
        
        secrets_found = []
        
        for pattern in secret_patterns:
            result = subprocess.run(
                ["grep", "-r", "-n", "-E", pattern, "src/", "configs/", "tests/"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                secrets_found.extend(result.stdout.strip().split('\n'))
        
        # Filter out test files and environment variable examples
        secrets_found = [s for s in secrets_found if not any(
            word in s.lower() for word in ["test_", "example", "placeholder", "change-in-production"]
        )]
        
        if secrets_found:
            self.results.append(SecurityTestResult(
                test_name="hardcoded_secrets",
                passed=False,
                severity=SecuritySeverity.CRITICAL,
                message=f"Found potential hardcoded secrets in {len(secrets_found)} files",
                details={"secrets": secrets_found}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="hardcoded_secrets",
                passed=True,
                severity=SecuritySeverity.CRITICAL,
                message="No hardcoded secrets found"
            ))

    def test_input_validation(self) -> None:
        """Test for input validation issues"""
        logger.info("✅ Testing input validation...")
        
        sql_injection_patterns = [
            r'execute\s*\(\s*["\'][^"\']*%[sd][^"\']*["\']',
            r'query\s*\(\s*["\'][^"\']*\+[^"\']*["\']',
            r'cursor\.execute\s*\(\s*["\'][^"\']*%[sd][^"\']*["\']'
        ]
        
        injection_risks = []
        
        for pattern in sql_injection_patterns:
            result = subprocess.run(
                ["grep", "-r", "-n", "-E", pattern, "src/"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                injection_risks.extend(result.stdout.strip().split('\n'))
        
        if injection_risks:
            self.results.append(SecurityTestResult(
                test_name="input_validation",
                passed=False,
                severity=SecuritySeverity.HIGH,
                message=f"Found potential SQL injection risks in {len(injection_risks)} files",
                details={"files": injection_risks}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="input_validation",
                passed=True,
                severity=SecuritySeverity.HIGH,
                message="No input validation risks found"
            ))

    def test_environment_configuration(self) -> None:
        """Test environment configuration security"""
        logger.info("⚙️ Testing environment configuration...")
        
        # Check for required environment variables in production
        required_env_vars = [
            "JWT_SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.results.append(SecurityTestResult(
                test_name="environment_configuration",
                passed=False,
                severity=SecuritySeverity.HIGH,
                message=f"Missing required environment variables: {', '.join(missing_vars)}",
                details={"missing_vars": missing_vars}
            ))
        else:
            self.results.append(SecurityTestResult(
                test_name="environment_configuration",
                passed=True,
                severity=SecuritySeverity.HIGH,
                message="All required environment variables are set"
            ))

    def test_ci_cd_security(self) -> None:
        """Test CI/CD security configuration"""
        logger.info("🔄 Testing CI/CD security...")
        
        # Check GitHub Actions permissions
        workflow_file = self.project_root / ".github" / "workflows" / "ci.yml"
        
        if workflow_file.exists():
            with open(workflow_file, 'r') as f:
                content = f.read()
            
            # Check for secure permissions
            if "contents: write" in content:
                self.results.append(SecurityTestResult(
                    test_name="ci_cd_security",
                    passed=True,
                    severity=SecuritySeverity.MEDIUM,
                    message="CI/CD permissions configured correctly"
                ))
            else:
                self.results.append(SecurityTestResult(
                    test_name="ci_cd_security",
                    passed=False,
                    severity=SecuritySeverity.MEDIUM,
                    message="CI/CD permissions may be insufficient"
                ))
        else:
            self.results.append(SecurityTestResult(
                test_name="ci_cd_security",
                passed=False,
                severity=SecuritySeverity.MEDIUM,
                message="CI/CD workflow file not found"
            ))

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Count by severity
        severity_counts = {
            "critical": sum(1 for r in self.results if not r.passed and r.severity == SecuritySeverity.CRITICAL),
            "high": sum(1 for r in self.results if not r.passed and r.severity == SecuritySeverity.HIGH),
            "medium": sum(1 for r in self.results if not r.passed and r.severity == SecuritySeverity.MEDIUM),
            "low": sum(1 for r in self.results if not r.passed and r.severity == SecuritySeverity.LOW)
        }
        
        import datetime
        report = {
            "timestamp": str(datetime.datetime.now()),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0.0%"
            },
            "severity_breakdown": {
                "critical_failed": severity_counts["critical"],
                "high_failed": severity_counts["high"],
                "medium_failed": severity_counts["medium"],
                "low_failed": severity_counts["low"]
            },
            "results": [
                {
                    "test_name": result.test_name,
                    "passed": result.passed,
                    "severity": result.severity.value,
                    "message": result.message,
                    "details": result.details
                }
                for result in self.results
            ],
            "recommendations": self._generate_recommendations()
        }
        
        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on test results"""
        recommendations = []
        
        failed_tests = [r for r in self.results if not r.passed]
        
        if any(r.test_name == "dependency_vulnerabilities" for r in failed_tests):
            recommendations.append("Update vulnerable dependencies using: pip install --upgrade -r requirements.txt")
        
        if any(r.test_name == "insecure_hash_md5" for r in failed_tests):
            recommendations.append("Replace all MD5 usage with SHA-256")
        
        if any(r.test_name == "insecure_hash_sha1" for r in failed_tests):
            recommendations.append("Replace all SHA1 usage with SHA-256")
        
        if any(r.test_name == "insecure_serialization_pickle" for r in failed_tests):
            recommendations.append("Replace pickle usage with secure serialization (JSON/MessagePack)")
        
        if any(r.test_name == "insecure_network_binding" for r in failed_tests):
            recommendations.append("Replace 0.0.0.0 bindings with specific interface addresses")
        
        if any(r.test_name == "hardcoded_secrets" for r in failed_tests):
            recommendations.append("Move hardcoded secrets to environment variables")
        
        if any(r.test_name == "input_validation" for r in failed_tests):
            recommendations.append("Implement proper input validation and use parameterized queries")
        
        return recommendations

    def print_report(self, report: Dict[str, Any]) -> None:
        """Print formatted security report"""
        print("=" * 60)
        print("🔒 PAKE SYSTEM SECURITY TEST REPORT")
        print("=" * 60)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Pass Rate: {report['summary']['pass_rate']}")
        print()
        print("Severity Breakdown:")
        print(f"  Critical Issues: {report['severity_breakdown']['critical_failed']}")
        print(f"  High Issues: {report['severity_breakdown']['high_failed']}")
        print(f"  Medium Issues: {report['severity_breakdown']['medium_failed']}")
        print(f"  Low Issues: {report['severity_breakdown']['low_failed']}")
        print()
        
        failed_tests = [r for r in report['results'] if not r['passed']]
        if failed_tests:
            print("❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"[{test['severity'].upper()}] {test['test_name']}: {test['message']}")
            print()
        
        if report['recommendations']:
            print("💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"• {rec}")
            print()
        
        # Save detailed report
        report_file = self.project_root / "security_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved to: {report_file}")
        
        # Exit with error code if critical issues found
        if report['severity_breakdown']['critical_failed'] > 0:
            print("\n🚨 CRITICAL SECURITY ISSUES FOUND! Please fix before deployment.")
            sys.exit(1)
        elif report['summary']['failed'] > 0:
            print("\n⚠️  Security issues found. Please review and fix.")
            sys.exit(1)
        else:
            print("\n✅ All security tests passed!")


def main():
    """Main entry point for security testing"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run security tests
    tester = SecurityTester()
    report = tester.run_all_tests()
    
    # Print and save report
    tester.print_report(report)


if __name__ == "__main__":
    main()
