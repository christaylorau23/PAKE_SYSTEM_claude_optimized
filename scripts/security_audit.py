#!/usr/bin/env python3
"""
PAKE System - Comprehensive Security Audit and Hardening Suite
Enterprise-grade security assessment and vulnerability analysis
"""

import asyncio
import json
import logging
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import aiohttp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


@dataclass
class SecurityIssue:
    """Individual security issue"""

    severity: str  # critical, high, medium, low
    category: str  # authentication, authorization, data_protection, etc.
    title: str
    description: str
    recommendation: str
    file_path: str | None = None
    line_number: int | None = None
    cwe_id: str | None = None
    cvss_score: float | None = None


@dataclass
class SecurityAuditResult:
    """Complete security audit result"""

    audit_timestamp: str
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    issues: list[SecurityIssue]
    security_score: float
    recommendations: list[str]


class SecurityAuditor:
    """Comprehensive security audit suite"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.issues: list[SecurityIssue] = []
        self.project_root = Path(__file__).parent.parent

    def add_issue(self, issue: SecurityIssue):
        """Add security issue to audit results"""
        self.issues.append(issue)
        logger.warning(f"Security Issue [{issue.severity.upper()}]: {issue.title}")

    def check_environment_security(self):
        """Check environment variables and configuration security"""
        logger.info("Checking environment security...")

        # Check for hardcoded secrets
        env_files = [".env", ".env.production", ".env.local", ".env.development"]
        for env_file in env_files:
            env_path = self.project_root / env_file
            if env_path.exists():
                try:
                    with open(env_path) as f:
                        content = f.read()

                    # Check for common secret patterns
                    secret_patterns = [
                        (r'REDACTED_SECRET\s*=\s*["\']?[^"\'\s]+["\']?', "Hardcoded REDACTED_SECRET"),
                        (r'api_key\s*=\s*["\']?[^"\'\s]+["\']?', "Hardcoded API key"),
                        (r'secret\s*=\s*["\']?[^"\'\s]+["\']?', "Hardcoded secret"),
                        (r'token\s*=\s*["\']?[^"\'\s]+["\']?', "Hardcoded token"),
                    ]

                    for pattern, description in secret_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            self.add_issue(
                                SecurityIssue(
                                    severity="high",
                                    category="data_protection",
                                    title=f"Hardcoded Secret in {env_file}",
                                    description=f"{description} found in {env_file}",
                                    recommendation="Use environment variables or secure secret management",
                                    file_path=str(env_path),
                                ),
                            )

                except Exception as e:
                    logger.warning(f"Could not read {env_file}: {e}")

        # Check for .env files in git
        try:
            result = subprocess.run(
                ["git", "ls-files", "*.env*"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                self.add_issue(
                    SecurityIssue(
                        severity="critical",
                        category="data_protection",
                        title="Environment files tracked in Git",
                        description="Environment files containing secrets are tracked in version control",
                        recommendation="Add .env* to .gitignore and remove from git history",
                    ),
                )
        except Exception:
            pass  # Git not available or not a git repo

    def check_dependency_security(self):
        """Check for vulnerable dependencies"""
        logger.info("Checking dependency security...")

        requirements_files = [
            "requirements.txt",
            "requirements-phase7.txt",
            "src/bridge/package.json",
        ]

        for req_file in requirements_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                try:
                    with open(req_path) as f:
                        content = f.read()

                    # Check for known vulnerable packages
                    vulnerable_packages = [
                        (
                            "requests<2.20.0",
                            "Requests library with known vulnerabilities",
                        ),
                        ("urllib3<1.24.0", "urllib3 with security issues"),
                        ("pyyaml<5.1", "PyYAML with code execution vulnerability"),
                        (
                            "jinja2<2.10.1",
                            "Jinja2 with template injection vulnerability",
                        ),
                    ]

                    for package, description in vulnerable_packages:
                        if package.split("<")[0] in content.lower():
                            self.add_issue(
                                SecurityIssue(
                                    severity="high",
                                    category="dependencies",
                                    title=f"Vulnerable Package: {
                                        package.split('<')[0]
                                    }",
                                    description=f"{description}",
                                    recommendation=f"Upgrade to {
                                        package.split('<')[1]
                                    } or later",
                                    file_path=str(req_path),
                                ),
                            )

                except Exception as e:
                    logger.warning(f"Could not read {req_file}: {e}")

    def check_code_security(self):
        """Check source code for security vulnerabilities"""
        logger.info("Checking source code security...")

        # Check Python files
        python_files = list(self.project_root.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Check for dangerous patterns
                dangerous_patterns = [
                    (r"eval\s*\(", "Use of eval() function", "critical"),
                    (r"exec\s*\(", "Use of exec() function", "critical"),
                    (r"os\.system\s*\(", "Use of os.system()", "high"),
                    (r"subprocess\.call\s*\(", "Use of subprocess.call()", "high"),
                    (r"pickle\.loads?\s*\(", "Use of pickle.loads()", "high"),
                    (r"yaml\.load\s*\(", "Use of yaml.load()", "high"),
                    (r"shell=True", "Shell injection vulnerability", "high"),
                    (r'REDACTED_SECRET\s*=\s*["\'][^"\']+["\']', "Hardcoded REDACTED_SECRET", "high"),
                    (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key", "high"),
                    (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret", "high"),
                    (r"DEBUG\s*=\s*True", "Debug mode enabled", "medium"),
                    (r'CORS\s*=\s*["\']\*["\']', "Overly permissive CORS", "medium"),
                ]

                for pattern, description, severity in dangerous_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_number = content[: match.start()].count("\n") + 1
                        self.add_issue(
                            SecurityIssue(
                                severity=severity,
                                category="code_security",
                                title=description,
                                description=f"{description} found in {py_file.name}",
                                recommendation="Review and secure the identified code pattern",
                                file_path=str(py_file),
                                line_number=line_number,
                            ),
                        )

            except Exception as e:
                logger.warning(f"Could not read {py_file}: {e}")

        # Check JavaScript/TypeScript files
        js_files = list(self.project_root.rglob("*.js")) + list(
            self.project_root.rglob("*.ts"),
        )
        for js_file in js_files:
            try:
                with open(js_file, encoding="utf-8") as f:
                    content = f.read()

                # Check for dangerous patterns in JS/TS
                js_dangerous_patterns = [
                    (r"eval\s*\(", "Use of eval() function", "critical"),
                    (r"innerHTML\s*=", "Potential XSS vulnerability", "high"),
                    (r"document\.write\s*\(", "Use of document.write()", "medium"),
                    (r"console\.log\s*\([^)]*REDACTED_SECRET", "Password logging", "medium"),
                ]

                for pattern, description, severity in js_dangerous_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_number = content[: match.start()].count("\n") + 1
                        self.add_issue(
                            SecurityIssue(
                                severity=severity,
                                category="code_security",
                                title=description,
                                description=f"{description} found in {js_file.name}",
                                recommendation="Review and secure the identified code pattern",
                                file_path=str(js_file),
                                line_number=line_number,
                            ),
                        )

            except Exception as e:
                logger.warning(f"Could not read {js_file}: {e}")

    def check_authentication_security(self):
        """Check authentication and authorization security"""
        logger.info("Checking authentication security...")

        # Check for JWT implementation
        jwt_files = list(self.project_root.rglob("*.py"))
        jwt_implemented = False

        for py_file in jwt_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                if "jwt" in content.lower() or "pyjwt" in content.lower():
                    jwt_implemented = True

                    # Check for JWT security issues
                    jwt_issues = [
                        (
                            r'algorithm\s*=\s*["\']none["\']',
                            "JWT algorithm set to 'none'",
                            "critical",
                        ),
                        (r"verify\s*=\s*False", "JWT verification disabled", "high"),
                        (r"exp\s*=\s*None", "JWT expiration not set", "medium"),
                    ]

                    for pattern, description, severity in jwt_issues:
                        if re.search(pattern, content, re.IGNORECASE):
                            self.add_issue(
                                SecurityIssue(
                                    severity=severity,
                                    category="authentication",
                                    title=description,
                                    description=f"{description} in JWT implementation",
                                    recommendation="Implement proper JWT security practices",
                                    file_path=str(py_file),
                                ),
                            )
                    break

            except Exception:
                continue

        if not jwt_implemented:
            self.add_issue(
                SecurityIssue(
                    severity="medium",
                    category="authentication",
                    title="No JWT Authentication Found",
                    description="JWT authentication not implemented",
                    recommendation="Implement JWT-based authentication for API security",
                ),
            )

    def check_input_validation(self):
        """Check for input validation security"""
        logger.info("Checking input validation...")

        # Check FastAPI endpoints for input validation
        server_file = self.project_root / "mcp_server_standalone.py"
        if server_file.exists():
            try:
                with open(server_file, encoding="utf-8") as f:
                    content = f.read()

                # Check for endpoints without proper validation
                endpoints_without_validation = re.findall(
                    r'@app\.(get|post|put|delete)\s*\(\s*["\'][^"\']+["\']\s*\)\s*\n\s*async def \w+\([^)]*\):',
                    content,
                    re.MULTILINE,
                )

                if endpoints_without_validation:
                    self.add_issue(
                        SecurityIssue(
                            severity="medium",
                            category="input_validation",
                            title="Endpoints Without Input Validation",
                            description=f"Found {
                                len(endpoints_without_validation)
                            } endpoints without proper input validation",
                            recommendation="Implement Pydantic models for request validation",
                            file_path=str(server_file),
                        ),
                    )

            except Exception as e:
                logger.warning(f"Could not read server file: {e}")

    def check_ssl_tls_security(self):
        """Check SSL/TLS configuration"""
        logger.info("Checking SSL/TLS security...")

        # Check if HTTPS is configured
        if self.base_url.startswith("http://"):
            self.add_issue(
                SecurityIssue(
                    severity="high",
                    category="transport_security",
                    title="HTTP Instead of HTTPS",
                    description="API is running over HTTP instead of HTTPS",
                    recommendation="Configure HTTPS with proper SSL certificates",
                ),
            )

        # Check for SSL context configuration
        ssl_files = list(self.project_root.rglob("*.py"))
        ssl_configured = False

        for py_file in ssl_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                if "ssl" in content.lower() or "tls" in content.lower():
                    ssl_configured = True

                    # Check for insecure SSL configurations
                    ssl_issues = [
                        (r"verify=False", "SSL verification disabled", "critical"),
                        (
                            r"check_hostname=False",
                            "Hostname verification disabled",
                            "high",
                        ),
                        (
                            r"PROTOCOL_SSLv2|PROTOCOL_SSLv3",
                            "Insecure SSL protocol",
                            "high",
                        ),
                    ]

                    for pattern, description, severity in ssl_issues:
                        if re.search(pattern, content, re.IGNORECASE):
                            self.add_issue(
                                SecurityIssue(
                                    severity=severity,
                                    category="transport_security",
                                    title=description,
                                    description=f"{description} in SSL configuration",
                                    recommendation="Use secure SSL/TLS configuration",
                                    file_path=str(py_file),
                                ),
                            )
                    break

            except Exception:
                continue

    def check_file_permissions(self):
        """Check file permissions and access controls"""
        logger.info("Checking file permissions...")

        # Check for overly permissive files
        sensitive_files = [
            ".env*",
            "*.key",
            "*.pem",
            "*.p12",
            "*.pfx",
            "config.json",
            "secrets.json",
        ]

        for pattern in sensitive_files:
            files = list(self.project_root.rglob(pattern))
            for file_path in files:
                try:
                    stat_info = file_path.stat()
                    mode = oct(stat_info.st_mode)[-3:]

                    # Check if file is readable by others
                    if int(mode[2]) > 4:  # Others have read permission
                        self.add_issue(
                            SecurityIssue(
                                severity="medium",
                                category="file_permissions",
                                title="Overly Permissive File Permissions",
                                description=f"File {
                                    file_path.name
                                } is readable by others (mode: {mode})",
                                recommendation="Restrict file permissions to owner only",
                                file_path=str(file_path),
                            ),
                        )

                except Exception as e:
                    logger.warning(f"Could not check permissions for {file_path}: {e}")

    async def check_api_security(self):
        """Check API security endpoints"""
        logger.info("Checking API security...")

        try:
            async with aiohttp.ClientSession() as session:
                # Test for common security headers
                async with session.get(f"{self.base_url}/health") as response:
                    headers = response.headers

                    # Check for security headers
                    security_headers = {
                        "X-Content-Type-Options": "nosniff",
                        "X-Frame-Options": "DENY",
                        "X-XSS-Protection": "1; mode=block",
                        "Strict-Transport-Security": "max-age=31536000",
                        "Content-Security-Policy": "default-src 'self'",
                    }

                    for header, expected_value in security_headers.items():
                        if header not in headers:
                            self.add_issue(
                                SecurityIssue(
                                    severity="medium",
                                    category="http_security",
                                    title=f"Missing Security Header: {header}",
                                    description=f"Security header {header} is not present",
                                    recommendation=f"Add {header}: {expected_value} header",
                                ),
                            )

                # Test for CORS configuration
                async with session.options(
                    f"{self.base_url}/health",
                    headers={"Origin": "https://malicious-site.com"},
                ) as response:
                    cors_headers = response.headers.get("Access-Control-Allow-Origin")
                    if cors_headers == "*":
                        self.add_issue(
                            SecurityIssue(
                                severity="medium",
                                category="http_security",
                                title="Overly Permissive CORS",
                                description="CORS is configured to allow all origins (*)",
                                recommendation="Restrict CORS to specific trusted domains",
                            ),
                        )

        except Exception as e:
            logger.warning(f"Could not test API security: {e}")

    def calculate_security_score(self) -> float:
        """Calculate overall security score"""
        if not self.issues:
            return 100.0

        # Weight issues by severity
        weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}

        total_weight = sum(weights[issue.severity] for issue in self.issues)
        max_possible_weight = len(self.issues) * 10  # Assume all critical

        score = max(0, 100 - (total_weight / max_possible_weight) * 100)
        return round(score, 1)

    def generate_recommendations(self) -> list[str]:
        """Generate security recommendations"""
        recommendations = []

        # Analyze issues and generate recommendations
        issue_categories = {}
        for issue in self.issues:
            if issue.category not in issue_categories:
                issue_categories[issue.category] = []
            issue_categories[issue.category].append(issue)

        # Category-specific recommendations
        if "data_protection" in issue_categories:
            recommendations.append(
                "Implement secure secret management using environment variables or dedicated secret management services",
            )

        if "authentication" in issue_categories:
            recommendations.append(
                "Implement robust JWT authentication with proper expiration and verification",
            )

        if "code_security" in issue_categories:
            recommendations.append(
                "Review and secure dangerous code patterns, especially eval() and exec() usage",
            )

        if "dependencies" in issue_categories:
            recommendations.append(
                "Update all dependencies to latest secure versions and implement dependency scanning",
            )

        if "transport_security" in issue_categories:
            recommendations.append(
                "Configure HTTPS with proper SSL certificates and secure TLS configuration",
            )

        if "http_security" in issue_categories:
            recommendations.append(
                "Implement comprehensive security headers and restrict CORS policies",
            )

        # General recommendations
        recommendations.extend(
            [
                "Implement regular security audits and vulnerability scanning",
                "Set up automated security testing in CI/CD pipeline",
                "Implement rate limiting and DDoS protection",
                "Regular security training for development team",
                "Implement logging and monitoring for security events",
            ],
        )

        return recommendations

    async def run_comprehensive_audit(self) -> SecurityAuditResult:
        """Run comprehensive security audit"""
        logger.info("Starting comprehensive security audit...")

        # Run all security checks
        self.check_environment_security()
        self.check_dependency_security()
        self.check_code_security()
        self.check_authentication_security()
        self.check_input_validation()
        self.check_ssl_tls_security()
        self.check_file_permissions()
        await self.check_api_security()

        # Calculate metrics
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in self.issues:
            severity_counts[issue.severity] += 1

        security_score = self.calculate_security_score()
        recommendations = self.generate_recommendations()

        return SecurityAuditResult(
            audit_timestamp=datetime.now().isoformat(),
            total_issues=len(self.issues),
            critical_issues=severity_counts["critical"],
            high_issues=severity_counts["high"],
            medium_issues=severity_counts["medium"],
            low_issues=severity_counts["low"],
            issues=self.issues,
            security_score=security_score,
            recommendations=recommendations,
        )

    def generate_report(self, result: SecurityAuditResult) -> str:
        """Generate comprehensive security audit report"""
        report = []
        report.append("# PAKE System Security Audit Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        report.append(f"**Security Score**: {result.security_score}/100")
        report.append(f"**Total Issues**: {result.total_issues}")
        report.append(f"- Critical: {result.critical_issues}")
        report.append(f"- High: {result.high_issues}")
        report.append(f"- Medium: {result.medium_issues}")
        report.append(f"- Low: {result.low_issues}")
        report.append("")

        # Security Score Interpretation
        if result.security_score >= 90:
            report.append("🟢 **Security Status**: EXCELLENT - System is highly secure")
        elif result.security_score >= 75:
            report.append(
                "🟡 **Security Status**: GOOD - Minor security improvements needed",
            )
        elif result.security_score >= 50:
            report.append(
                "🟠 **Security Status**: FAIR - Significant security improvements needed",
            )
        else:
            report.append(
                "🔴 **Security Status**: POOR - Critical security issues require immediate attention",
            )

        report.append("")

        # Critical Issues
        if result.critical_issues > 0:
            report.append("## 🚨 Critical Issues (Immediate Action Required)")
            report.append("")
            critical_issues = [
                issue for issue in result.issues if issue.severity == "critical"
            ]
            for issue in critical_issues:
                report.append(f"### {issue.title}")
                report.append(f"**Category**: {issue.category}")
                report.append(f"**Description**: {issue.description}")
                report.append(f"**Recommendation**: {issue.recommendation}")
                if issue.file_path:
                    report.append(f"**File**: {issue.file_path}")
                if issue.line_number:
                    report.append(f"**Line**: {issue.line_number}")
                report.append("")

        # High Priority Issues
        if result.high_issues > 0:
            report.append("## ⚠️ High Priority Issues")
            report.append("")
            high_issues = [issue for issue in result.issues if issue.severity == "high"]
            for issue in high_issues:
                report.append(f"### {issue.title}")
                report.append(f"**Category**: {issue.category}")
                report.append(f"**Description**: {issue.description}")
                report.append(f"**Recommendation**: {issue.recommendation}")
                if issue.file_path:
                    report.append(f"**File**: {issue.file_path}")
                report.append("")

        # Medium and Low Issues Summary
        if result.medium_issues > 0 or result.low_issues > 0:
            report.append("## 📋 Medium and Low Priority Issues")
            report.append("")
            other_issues = [
                issue for issue in result.issues if issue.severity in ["medium", "low"]
            ]

            # Group by category
            categories = {}
            for issue in other_issues:
                if issue.category not in categories:
                    categories[issue.category] = []
                categories[issue.category].append(issue)

            for category, issues in categories.items():
                report.append(f"### {category.replace('_', ' ').title()}")
                for issue in issues:
                    report.append(f"- **{issue.title}**: {issue.description}")
                report.append("")

        # Recommendations
        report.append("## 🎯 Security Recommendations")
        report.append("")
        for i, recommendation in enumerate(result.recommendations, 1):
            report.append(f"{i}. {recommendation}")
        report.append("")

        # Security Best Practices
        report.append("## 📚 Security Best Practices")
        report.append("")
        report.append("### Development")
        report.append("- Use environment variables for all secrets")
        report.append("- Implement input validation and sanitization")
        report.append("- Use parameterized queries to prevent SQL injection")
        report.append(
            "- Implement proper error handling without information disclosure",
        )
        report.append("")

        report.append("### Deployment")
        report.append("- Use HTTPS with proper SSL certificates")
        report.append("- Implement security headers")
        report.append("- Configure proper CORS policies")
        report.append("- Set up monitoring and logging")
        report.append("")

        report.append("### Maintenance")
        report.append("- Regular dependency updates")
        report.append("- Security audits and penetration testing")
        report.append("- Security training for development team")
        report.append("- Incident response planning")

        return "\n".join(report)


async def main():
    """Main security audit execution"""
    logger.info("Starting PAKE System Security Audit")

    auditor = SecurityAuditor()
    result = await auditor.run_comprehensive_audit()

    # Generate report
    report = auditor.generate_report(result)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON results
    results_file = f"security_audit_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(asdict(result), f, indent=2)
    logger.info(f"Security audit results saved to {results_file}")

    # Save markdown report
    report_file = f"security_report_{timestamp}.md"
    with open(report_file, "w") as f:
        f.write(report)
    logger.info(f"Security report saved to {report_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("SECURITY AUDIT SUMMARY")
    print("=" * 60)
    print(f"Security Score: {result.security_score}/100")
    print(f"Total Issues: {result.total_issues}")
    print(f"Critical: {result.critical_issues}, High: {result.high_issues}")
    print(f"Medium: {result.medium_issues}, Low: {result.low_issues}")
    print("=" * 60)

    if result.critical_issues > 0:
        print("🚨 CRITICAL ISSUES FOUND - IMMEDIATE ACTION REQUIRED")
        critical_issues = [
            issue for issue in result.issues if issue.severity == "critical"
        ]
        for issue in critical_issues:
            print(f"- {issue.title}")
    elif result.high_issues > 0:
        print("⚠️ HIGH PRIORITY ISSUES FOUND - ACTION REQUIRED")
    else:
        print("✅ No critical or high priority security issues found")


if __name__ == "__main__":
    asyncio.run(main())
