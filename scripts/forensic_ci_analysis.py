#!/usr/bin/env python3
"""
Forensic CI Analysis Tool
Automates comparison between CI and local environments to identify test failures.

Usage:
    # Analyze downloaded CI artifacts
    python scripts/forensic_ci_analysis.py --artifacts-dir ./diagnostic-artifacts

    # Download and analyze latest CI run
    python scripts/forensic_ci_analysis.py --run-id 12345678

    # Compare with local environment
    python scripts/forensic_ci_analysis.py --artifacts-dir ./diagnostic-artifacts --generate-local
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class EnvironmentDiff:
    """Represents differences in environment variables."""

    only_in_ci: dict[str, str]
    only_in_local: dict[str, str]
    different_values: dict[str, tuple[str, str]]  # key -> (ci_value, local_value)


@dataclass
class DependencyDiff:
    """Represents differences in Python dependencies."""

    only_in_ci: set[str]
    only_in_local: set[str]
    version_mismatches: dict[
        str, tuple[str, str]
    ]  # package -> (ci_version, local_version)


@dataclass
class LogIssue:
    """Represents an issue found in logs."""

    type: str  # 'error', 'timeout', 'module_not_found', 'file_not_found'
    message: str
    line_number: int
    context: list[str]  # surrounding lines


class ForensicAnalyzer:
    """Main forensic analysis engine."""

    def __init__(self) -> None:
        self.artifacts_dir = artifacts_dir
        self.issues: list[LogIssue] = []

    def analyze(self) -> dict:
        """Run complete forensic analysis."""
        print("🔍 Starting Forensic CI Analysis...")

        results = {
            "environment_diff": None,
            "dependency_diff": None,
            "log_issues": [],
            "recommendations": [],
        }

        # 1. Analyze environment variables
        env_ci_path = self.artifacts_dir / "environment.log"
        if env_ci_path.exists():
            print("\n📊 Analyzing environment variables...")
            results["environment_diff"] = self.compare_environments(env_ci_path)

        # 2. Analyze dependencies
        req_ci_path = self.artifacts_dir / "requirements.ci.log"
        if req_ci_path.exists():
            print("\n📦 Analyzing Python dependencies...")
            results["dependency_diff"] = self.compare_dependencies(req_ci_path)

        # 3. Analyze logs for issues
        print("\n🔎 Analyzing logs for errors and patterns...")
        results["log_issues"] = self.analyze_logs()

        # 4. Generate recommendations
        results["recommendations"] = self.generate_recommendations(results)

        return results

    def compare_environments(self, ci_env_path: Path) -> EnvironmentDiff:
        """Compare CI environment with local environment."""
        ci_env = self._parse_env_file(ci_env_path)
        local_env = dict(os.environ)

        only_in_ci = {k: v for k, v in ci_env.items() if k not in local_env}
        only_in_local = {k: v for k, v in local_env.items() if k not in ci_env}
        different_values = {
            k: (ci_env[k], local_env[k])
            for k in ci_env.keys() & local_env.keys()
            if ci_env[k] != local_env[k]
        }

        # Filter out noise (CI-specific vars)
        ci_specific = {"CI", "GITHUB_", "RUNNER_", "ImageOS", "AGENT_"}
        only_in_ci = {
            k: v
            for k, v in only_in_ci.items()
            if not any(k.startswith(prefix) for prefix in ci_specific)
        }

        return EnvironmentDiff(
            only_in_ci=only_in_ci,
            only_in_local=only_in_local,
            different_values=different_values,
        )

    def compare_dependencies(self, ci_req_path: Path) -> DependencyDiff:
        """Compare CI dependencies with local dependencies."""
        ci_deps = self._parse_requirements(ci_req_path)

        # Get local dependencies
        try:
            result = subprocess.run(
                ["pip", "freeze"], capture_output=True, text=True, check=True
            )
            local_deps = self._parse_requirements_text(result.stdout)
        except subprocess.CalledProcessError:
            print("⚠️  Warning: Could not get local pip freeze")
            local_deps = {}

        only_in_ci = set(ci_deps.keys()) - set(local_deps.keys())
        only_in_local = set(local_deps.keys()) - set(ci_deps.keys())
        version_mismatches = {
            pkg: (ci_deps[pkg], local_deps[pkg])
            for pkg in ci_deps.keys() & local_deps.keys()
            if ci_deps[pkg] != local_deps[pkg]
        }

        return DependencyDiff(
            only_in_ci=only_in_ci,
            only_in_local=only_in_local,
            version_mismatches=version_mismatches,
        )

    def analyze_logs(self) -> list[LogIssue]:
        """Analyze log files for common issues."""
        issues = []

        # Find all log files
        log_patterns = ["*.log", "*.txt", "pytest_output.txt"]
        log_files = []
        for pattern in log_patterns:
            log_files.extend(self.artifacts_dir.rglob(pattern))

        for log_file in log_files:
            issues.extend(self._analyze_single_log(log_file))

        # Sort by line number to find first error
        issues.sort(key=lambda x: x.line_number)

        return issues

    def _analyze_single_log(self, log_path: Path) -> list[LogIssue]:
        """Analyze a single log file."""
        issues = []

        try:
            with open(log_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  Could not read {log_path}: {e}")
            return issues

        for i, line in enumerate(lines):
            # Check for errors
            if re.search(
                r"\b(ERROR|FAILED|Exception|Traceback)\b", line, re.IGNORECASE
            ):
                issues.append(
                    LogIssue(
                        type="error",
                        message=line.strip(),
                        line_number=i + 1,
                        context=self._get_context(lines, i, 5),
                    )
                )

            # Check for timeouts
            if re.search(
                r"\b(timeout|timed out|took \d+\.\d+s)\b", line, re.IGNORECASE
            ):
                issues.append(
                    LogIssue(
                        type="timeout",
                        message=line.strip(),
                        line_number=i + 1,
                        context=self._get_context(lines, i, 3),
                    )
                )

            # Check for module not found
            if "ModuleNotFoundError" in line or "No module named" in line:
                issues.append(
                    LogIssue(
                        type="module_not_found",
                        message=line.strip(),
                        line_number=i + 1,
                        context=self._get_context(lines, i, 5),
                    )
                )

            # Check for file not found
            if "FileNotFoundError" in line or "No such file or directory" in line:
                issues.append(
                    LogIssue(
                        type="file_not_found",
                        message=line.strip(),
                        line_number=i + 1,
                        context=self._get_context(lines, i, 5),
                    )
                )

        return issues

    def generate_recommendations(self, results: dict) -> list[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []

        # Environment variable recommendations
        if results["environment_diff"]:
            env_diff = results["environment_diff"]

            if env_diff.different_values:
                critical_vars = ["DATABASE_URL", "REDIS_URL", "SECRET_KEY", "API_KEY"]
                for var in critical_vars:
                    if var in env_diff.different_values:
                        ci_val, local_val = env_diff.different_values[var]
                        recommendations.append(
                            f"🔴 CRITICAL: {var} differs between CI and local\n"
                            f"   CI: {self._mask_secret(ci_val)}\n"
                            f"   Local: {self._mask_secret(local_val)}\n"
                            f"   → Ensure this variable is set correctly in both environments"
                        )

            if env_diff.only_in_ci:
                recommendations.append(
                    f"⚠️  {len(env_diff.only_in_ci)} environment variables exist only in CI\n"
                    f"   → Review if any are required locally: {', '.join(list(env_diff.only_in_ci.keys())[:5])}"
                )

        # Dependency recommendations
        if results["dependency_diff"]:
            dep_diff = results["dependency_diff"]

            if dep_diff.version_mismatches:
                recommendations.append(
                    f"📦 {len(dep_diff.version_mismatches)} dependency version mismatches detected:\n"
                    + "\n".join(
                        [
                            f"   • {pkg}: CI={ci_ver}, Local={local_ver}"
                            for pkg, (ci_ver, local_ver) in list(
                                dep_diff.version_mismatches.items()
                            )[:10]
                        ]
                    )
                    + "\n   → Run: poetry lock && poetry install"
                )

            if dep_diff.only_in_ci:
                recommendations.append(
                    f"⚠️  {len(dep_diff.only_in_ci)} packages only in CI environment\n"
                    f"   → May indicate incomplete local setup"
                )

        # Log issue recommendations
        if results["log_issues"]:
            # Group by type
            by_type = defaultdict(list)
            for issue in results["log_issues"]:
                by_type[issue.type].append(issue)

            if "module_not_found" in by_type:
                first_module_error = by_type["module_not_found"][0]
                module_match = re.search(
                    r"No module named ['\"]([^'\"]+)['\"]", first_module_error.message
                )
                if module_match:
                    module = module_match.group(1)
                    recommendations.append(
                        f"🔴 CRITICAL: Module '{module}' not found (line {first_module_error.line_number})\n"
                        f"   → Check if package is in pyproject.toml\n"
                        f"   → Run: poetry add {module.split('.')[0]}"
                    )

            if "file_not_found" in by_type:
                first_file_error = by_type["file_not_found"][0]
                recommendations.append(
                    f"🔴 File not found error at line {first_file_error.line_number}\n"
                    f"   {first_file_error.message}\n"
                    f"   → Check for case-sensitivity issues (Linux is case-sensitive)\n"
                    f"   → Verify file exists in repository"
                )

            if "timeout" in by_type:
                recommendations.append(
                    f"⏱️  {len(by_type['timeout'])} timeout/performance issues detected\n"
                    f"   → CI runners may have resource constraints\n"
                    f"   → Consider increasing timeout values or optimizing slow operations"
                )

        return recommendations

    def _parse_env_file(self, path: Path) -> dict[str, str]:
        """Parse environment log file."""
        env = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("---"):
                    key, _, value = line.partition("=")
                    env[key] = value
        return env

    def _parse_requirements(self, path: Path) -> dict[str, str]:
        """Parse requirements file."""
        with open(path) as f:
            content = f.read()
        return self._parse_requirements_text(content)

    def _parse_requirements_text(self, text: str) -> dict[str, str]:
        """Parse requirements from text."""
        deps = {}
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                if "==" in line:
                    pkg, version = line.split("==", 1)
                    deps[pkg.strip()] = version.strip()
                elif "@" in line:
                    # Handle @ syntax (e.g., package @ git+https://...)
                    pkg = line.split("@")[0].strip()
                    deps[pkg] = line.split("@")[1].strip()
        return deps

    def _get_context(
        self, lines: list[str], index: int, context_size: int
    ) -> list[str]:
        """Get surrounding lines for context."""
        start = max(0, index - context_size)
        end = min(len(lines), index + context_size + 1)
        return [l.strip() for l in lines[start:end]]

    def _mask_secret(self, value: str) -> str:
        """Mask sensitive values in output."""
        if len(value) > 20:
            return value[:8] + "..." + value[-4:]
        return "***"


def generate_local_snapshot(self) -> None:
    """Generate local environment snapshot for comparison."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("📸 Generating local environment snapshot...")

    # Environment variables
    with open(output_dir / "environment.log", "w") as f:
        f.write("--- Environment Variables ---\n")
        for key, value in sorted(os.environ.items()):
            f.write(f"{key}={value}\n")

    # Python packages
    try:
        result = subprocess.run(
            ["pip", "freeze"], capture_output=True, text=True, check=True
        )
        with open(output_dir / "requirements.ci.log", "w") as f:
            f.write("--- Python Packages (pip freeze) ---\n")
            f.write(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not run pip freeze: {e}")

    # Poetry dependency tree
    try:
        result = subprocess.run(
            ["poetry", "show", "--tree"], capture_output=True, text=True, check=True
        )
        with open(output_dir / "poetry.tree.log", "w") as f:
            f.write("--- Poetry Dependency Tree ---\n")
            f.write(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not run poetry show: {e}")

    print(f"✅ Local snapshot saved to {output_dir}")


def print_report(self) -> None:
    """Print formatted analysis report."""
    print("\n" + "=" * 80)
    print("📋 FORENSIC CI ANALYSIS REPORT")
    print("=" * 80)

    # Environment differences
    if results["environment_diff"]:
        env_diff = results["environment_diff"]
        print("\n🌍 ENVIRONMENT VARIABLE ANALYSIS:")
        print("-" * 80)

        if env_diff.different_values:
            print(
                f"\n⚠️  {len(env_diff.different_values)} variables with different values:"
            )
            for key, (ci_val, local_val) in list(env_diff.different_values.items())[
                :10
            ]:
                print(f"   • {key}")
                print(
                    f"     CI:    {ci_val[:60]}..."
                    if len(ci_val) > 60
                    else f"     CI:    {ci_val}"
                )
                print(
                    f"     Local: {local_val[:60]}..."
                    if len(local_val) > 60
                    else f"     Local: {local_val}"
                )

        if env_diff.only_in_ci:
            print(f"\n📤 {len(env_diff.only_in_ci)} variables only in CI:")
            for key in list(env_diff.only_in_ci.keys())[:10]:
                print(f"   • {key}")

        if env_diff.only_in_local:
            print(f"\n📥 {len(env_diff.only_in_local)} variables only in Local:")
            for key in list(env_diff.only_in_local.keys())[:10]:
                print(f"   • {key}")

    # Dependency differences
    if results["dependency_diff"]:
        dep_diff = results["dependency_diff"]
        print("\n\n📦 DEPENDENCY ANALYSIS:")
        print("-" * 80)

        if dep_diff.version_mismatches:
            print(f"\n⚠️  {len(dep_diff.version_mismatches)} version mismatches:")
            for pkg, (ci_ver, local_ver) in list(dep_diff.version_mismatches.items())[
                :15
            ]:
                print(f"   • {pkg}: CI={ci_ver}, Local={local_ver}")

        if dep_diff.only_in_ci:
            print(f"\n📤 {len(dep_diff.only_in_ci)} packages only in CI")

        if dep_diff.only_in_local:
            print(f"\n📥 {len(dep_diff.only_in_local)} packages only in Local")

    # Log issues
    if results["log_issues"]:
        print("\n\n🔎 LOG ANALYSIS:")
        print("-" * 80)

        # Group by type
        by_type = defaultdict(list)
        for issue in results["log_issues"]:
            by_type[issue.type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"\n{issue_type.upper().replace('_', ' ')}: {len(issues)} found")

            # Show first 3 of each type
            for issue in issues[:3]:
                print(f"\n   Line {issue.line_number}: {issue.message}")
                if issue.context:
                    print("   Context:")
                    for ctx_line in issue.context[:3]:
                        if ctx_line:
                            print(f"      {ctx_line[:100]}")

    # Recommendations
    if results["recommendations"]:
        print("\n\n💡 RECOMMENDATIONS:")
        print("=" * 80)
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"\n{i}. {rec}")

    print("\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80 + "\n")


def main(self) -> None:
    parser = argparse.ArgumentParser(
        description="Forensic CI Analysis Tool - Compare CI and local environments"
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        help="Directory containing downloaded CI artifacts",
    )
    parser.add_argument(
        "--generate-local",
        action="store_true",
        help="Generate local environment snapshot for comparison",
    )
    parser.add_argument(
        "--local-snapshot-dir",
        type=Path,
        default=Path("./local-snapshot"),
        help="Directory to save local snapshot (default: ./local-snapshot)",
    )
    parser.add_argument("--output-json", type=Path, help="Save results to JSON file")

    args = parser.parse_args()

    # Generate local snapshot if requested
    if args.generate_local:
        generate_local_snapshot(args.local_snapshot_dir)
        if not args.artifacts_dir:
            print(
                "\n✅ Local snapshot generated. Use --artifacts-dir to compare with CI."
            )
            return

    # Run analysis
    if not args.artifacts_dir:
        parser.print_help()
        sys.exit(1)

    if not args.artifacts_dir.exists():
        print(f"❌ Error: Artifacts directory not found: {args.artifacts_dir}")
        sys.exit(1)

    analyzer = ForensicAnalyzer(args.artifacts_dir)
    results = analyzer.analyze()

    # Print report
    print_report(results)

    # Save to JSON if requested
    if args.output_json:
        # Convert dataclasses to dicts for JSON serialization
        json_results = {
            "environment_diff": {
                "only_in_ci": results["environment_diff"].only_in_ci
                if results["environment_diff"]
                else {},
                "only_in_local": results["environment_diff"].only_in_local
                if results["environment_diff"]
                else {},
                "different_values": {
                    k: {"ci": v[0], "local": v[1]}
                    for k, v in (
                        results["environment_diff"].different_values.items()
                        if results["environment_diff"]
                        else {}
                    )
                },
            }
            if results["environment_diff"]
            else None,
            "dependency_diff": {
                "only_in_ci": list(results["dependency_diff"].only_in_ci)
                if results["dependency_diff"]
                else [],
                "only_in_local": list(results["dependency_diff"].only_in_local)
                if results["dependency_diff"]
                else [],
                "version_mismatches": {
                    k: {"ci": v[0], "local": v[1]}
                    for k, v in (
                        results["dependency_diff"].version_mismatches.items()
                        if results["dependency_diff"]
                        else {}
                    )
                },
            }
            if results["dependency_diff"]
            else None,
            "log_issues": [
                {
                    "type": issue.type,
                    "message": issue.message,
                    "line_number": issue.line_number,
                    "context": issue.context,
                }
                for issue in results["log_issues"]
            ],
            "recommendations": results["recommendations"],
        }

        with open(args.output_json, "w") as f:
            json.dump(json_results, f, indent=2)
        print(f"\n📄 Results saved to {args.output_json}")


if __name__ == "__main__":
    main()
