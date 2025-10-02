#!/usr/bin/env python3
"""
Security Validation Script
Runs comprehensive security checks (Bandit, pip-audit, Safety, detect-secrets, gitleaks)
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class SecurityValidator:
    """Security validation runner"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.results: list[tuple[str, bool, str, dict[str, Any]]] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] [{level}] {message}")

    def run_command(
        self, name: str, command: list[str], description: str
    ) -> tuple[str, bool, str, dict[str, Any]]:
        """Run a command and return results"""
        self.log(f"Running {name}: {description}")
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            duration = time.time() - start_time

            # Parse output for security-specific information
            security_info = self._parse_security_output(
                name, result.stdout, result.stderr
            )

            if result.returncode == 0:
                self.log(f"✅ {name} passed ({duration:.2f}s)", "INFO")
                return name, True, result.stdout, security_info
            else:
                self.log(f"❌ {name} failed ({duration:.2f}s)", "ERROR")
                if self.verbose:
                    self.log(f"Error: {result.stderr}", "ERROR")
                return name, False, result.stderr, security_info

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log(f"⏰ {name} timed out after 300s", "ERROR")
            return name, False, "Timeout after 300s", {}
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {name} crashed: {e}", "ERROR")
            return name, False, str(e), {}

    def _parse_security_output(
        self, tool: str, stdout: str, stderr: str
    ) -> dict[str, Any]:
        """Parse security tool output for structured information"""
        info = {"tool": tool, "issues": [], "summary": {}}

        try:
            if tool == "bandit" and stdout:
                # Parse Bandit JSON output
                try:
                    bandit_data = json.loads(stdout)
                    info["summary"] = {
                        "high_severity": bandit_data.get("results", []).count(
                            lambda x: x.get("issue_severity") == "HIGH"
                        ),
                        "medium_severity": bandit_data.get("results", []).count(
                            lambda x: x.get("issue_severity") == "MEDIUM"
                        ),
                        "low_severity": bandit_data.get("results", []).count(
                            lambda x: x.get("issue_severity") == "LOW"
                        ),
                        "total_issues": len(bandit_data.get("results", [])),
                    }
                except json.JSONDecodeError:
                    pass

            elif tool == "pip-audit" and stdout:
                # Parse pip-audit JSON output
                try:
                    audit_data = json.loads(stdout)
                    info["summary"] = {
                        "vulnerabilities": len(audit_data.get("vulnerabilities", [])),
                        "packages_scanned": len(audit_data.get("dependencies", [])),
                    }
                except json.JSONDecodeError:
                    pass

            elif tool == "safety" and stdout:
                # Parse Safety JSON output
                try:
                    safety_data = json.loads(stdout)
                    info["summary"] = {
                        "vulnerabilities": len(safety_data),
                        "packages_affected": len(
                            set(vuln.get("package") for vuln in safety_data)
                        ),
                    }
                except json.JSONDecodeError:
                    pass

            elif tool == "detect-secrets" and stdout:
                # Parse detect-secrets output
                lines = stdout.split("\n")
                info["summary"] = {
                    "secrets_found": len(
                        [line for line in lines if "Potential secrets" in line]
                    ),
                    "files_scanned": len(
                        [line for line in lines if "Scanning" in line]
                    ),
                }

            elif tool == "gitleaks" and stdout:
                # Parse gitleaks output
                lines = stdout.split("\n")
                info["summary"] = {
                    "leaks_found": len(
                        [line for line in lines if "leak" in line.lower()]
                    ),
                    "files_scanned": len(
                        [line for line in lines if "scanning" in line.lower()]
                    ),
                }

        except Exception as e:
            if self.verbose:
                self.log(f"Error parsing {tool} output: {e}", "WARNING")

        return info

    def run_bandit_check(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run Bandit security analysis"""
        command = [
            "poetry",
            "run",
            "bandit",
            "-r",
            "src/",
            "-f",
            "json",
            "-o",
            "bandit-report.json",
        ]
        description = "Run Bandit security analysis"

        return self.run_command("bandit", command, description)

    def run_pip_audit_check(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run pip-audit for vulnerable dependencies"""
        command = ["poetry", "run", "pip-audit", "--format=json"]
        description = "Scan for vulnerable Python dependencies"

        return self.run_command("pip-audit", command, description)

    def run_safety_check(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run Safety check"""
        command = ["poetry", "run", "safety", "check", "--json"]
        description = "Additional Python security checks"

        return self.run_command("safety", command, description)

    def run_detect_secrets_check(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run detect-secrets scan"""
        command = [
            "poetry",
            "run",
            "detect-secrets",
            "scan",
            "--baseline",
            ".secrets.baseline",
        ]
        description = "Scan for hardcoded secrets"

        return self.run_command("detect-secrets", command, description)

    def run_gitleaks_check(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run gitleaks scan"""
        command = ["gitleaks", "detect", "--source", ".", "--verbose"]
        description = "Scan git history for secrets"

        return self.run_command("gitleaks", command, description)

    def run_custom_security_tests(self) -> tuple[str, bool, str, dict[str, Any]]:
        """Run custom security test suite"""
        command = ["poetry", "run", "python", "scripts/security_test_suite.py"]
        description = "Run comprehensive security test suite"

        return self.run_command("security-tests", command, description)

    def run_all_checks(self) -> bool:
        """Run all security checks"""
        self.log("Starting security validation...")

        # Run all checks
        checks = [
            self.run_bandit_check(),
            self.run_pip_audit_check(),
            self.run_safety_check(),
            self.run_detect_secrets_check(),
            self.run_gitleaks_check(),
            self.run_custom_security_tests(),
        ]

        self.results.extend(checks)

        # Print summary
        self.print_summary()

        # Return success if all checks passed
        return all(result[1] for result in checks)

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("🔒 SECURITY VALIDATION SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, success, _, _ in self.results if success)
        total = len(self.results)

        print(f"📊 Total Checks: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"📈 Success Rate: {(passed/total*100):.1f}%")

        print("\n📋 Results by Tool:")
        for name, success, output, info in self.results:
            status_emoji = "✅" if success else "❌"
            print(
                f"  {status_emoji} {name.upper()}: {'PASSED' if success else 'FAILED'}"
            )

            # Show security-specific information
            if info.get("summary"):
                summary = info["summary"]
                if "vulnerabilities" in summary:
                    print(f"     Vulnerabilities: {summary['vulnerabilities']}")
                if "high_severity" in summary:
                    print(f"     High Severity: {summary['high_severity']}")
                if "secrets_found" in summary:
                    print(f"     Secrets Found: {summary['secrets_found']}")
                if "leaks_found" in summary:
                    print(f"     Leaks Found: {summary['leaks_found']}")

            if not success and self.verbose:
                print(f"     Error: {output[:200]}...")

        print("=" * 60)

        if passed == total:
            print("\n🎉 All security checks passed!")
        else:
            print(f"\n❌ {total - passed} security check(s) failed!")
            print("💡 Review security issues and fix them before committing.")
            print("🔧 Common fixes:")
            print("   - Update vulnerable dependencies")
            print("   - Remove hardcoded secrets")
            print("   - Fix security vulnerabilities in code")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Security Validation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--tool",
        choices=[
            "bandit",
            "pip-audit",
            "safety",
            "detect-secrets",
            "gitleaks",
            "security-tests",
            "all",
        ],
        default="all",
        help="Run specific security tool",
    )
    parser.add_argument("--report-file", help="Save detailed security report to file")

    args = parser.parse_args()

    # Create validator
    validator = SecurityValidator(verbose=args.verbose)

    # Run specific tool or all
    if args.tool == "all":
        success = validator.run_all_checks()
    else:
        if args.tool == "bandit":
            result = validator.run_bandit_check()
        elif args.tool == "pip-audit":
            result = validator.run_pip_audit_check()
        elif args.tool == "safety":
            result = validator.run_safety_check()
        elif args.tool == "detect-secrets":
            result = validator.run_detect_secrets_check()
        elif args.tool == "gitleaks":
            result = validator.run_gitleaks_check()
        elif args.tool == "security-tests":
            result = validator.run_custom_security_tests()

        validator.results.append(result)
        validator.print_summary()
        success = result[1]

    # Save report if requested
    if args.report_file:
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [
                {"tool": name, "success": success, "output": output, "info": info}
                for name, success, output, info in validator.results
            ],
        }

        with open(args.report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Security report saved to: {args.report_file}")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
