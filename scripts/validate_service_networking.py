#!/usr/bin/env python3
"""
Phase 3: Service Container Networking Validator
Validates GitHub Actions workflows for correct service container configuration.

This tool checks:
1. Networking model consistency (container vs host-based)
2. Service health check configuration
3. Port mapping correctness
4. Connection string alignment

Usage:
    python scripts/validate_service_networking.py
    python scripts/validate_service_networking.py --workflow .github/workflows/ci.yml
    python scripts/validate_service_networking.py --fix
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


class ServiceNetworkingValidator:
    """Validates GitHub Actions service container networking configuration."""

    def __init__(self) -> None:
        self.workflow_path = workflow_path
        self.issues: list[dict] = []
        self.warnings: list[dict] = []

    def validate(self) -> tuple[bool, list[dict], list[dict]]:
        """
        Validate workflow for correct service networking configuration.

        Returns:
            Tuple of (is_valid, issues, warnings)
        """
        try:
            with open(self.workflow_path) as f:
                workflow = yaml.safe_load(f)
        except Exception as e:
            self.issues.append(
                {
                    "type": "parse_error",
                    "severity": "critical",
                    "message": f"Failed to parse workflow: {e}",
                }
            )
            return False, self.issues, self.warnings

        # Validate each job
        jobs = workflow.get("jobs", {})
        for job_name, job_config in jobs.items():
            self._validate_job(job_name, job_config)

        return len(self.issues) == 0, self.issues, self.warnings

    def _validate_job(self) -> None:
        """Validate a single job's service configuration."""
        # Check if job has services
        services = job_config.get("services", {})
        if not services:
            return  # No services, nothing to validate

        # Determine networking model
        has_container = "container" in job_config
        runs_on = job_config.get("runs-on", "")

        if has_container:
            # Container-based networking model
            self._validate_container_based_job(job_name, job_config, services)
        else:
            # Host-based networking model
            self._validate_host_based_job(job_name, job_config, services)

    def _validate_container_based_job(self) -> None:
        """
        Validate container-based networking (job runs in container).

        Expected:
        - Service hostname = service label
        - No port mapping required
        - All containers on same bridge network
        """
        container_image = job_config["container"]
        if isinstance(container_image, dict):
            container_image = container_image.get("image", "unknown")

        # Check for unnecessary port mappings
        for service_name, service_config in services.items():
            ports = service_config.get("ports", [])
            if ports:
                self.warnings.append(
                    {
                        "type": "unnecessary_port_mapping",
                        "severity": "warning",
                        "job": job_name,
                        "service": service_name,
                        "message": f"Port mapping not required for container-based job. "
                        f"Service '{service_name}' can be accessed via hostname '{service_name}' "
                        f"from within container '{container_image}'.",
                    }
                )

        # Check connection strings in env
        self._validate_connection_strings_container(job_name, job_config, services)

    def _validate_host_based_job(self) -> None:
        """
        Validate host-based networking (job runs on runner host).

        Expected:
        - Service hostname = localhost
        - Port mapping required
        - Health checks recommended
        """
        for service_name, service_config in services.items():
            # Check port mapping
            ports = service_config.get("ports", [])
            if not ports:
                self.issues.append(
                    {
                        "type": "missing_port_mapping",
                        "severity": "error",
                        "job": job_name,
                        "service": service_name,
                        "message": f"Service '{service_name}' missing port mapping. "
                        f"Host-based jobs require explicit port mapping to access services.",
                        "fix": f"Add 'ports' to service '{service_name}', e.g., ports: ['5432:5432']",
                    }
                )

            # Check health check
            options = service_config.get("options", "")
            if not options or "--health-cmd" not in options:
                self.warnings.append(
                    {
                        "type": "missing_health_check",
                        "severity": "warning",
                        "job": job_name,
                        "service": service_name,
                        "message": f"Service '{service_name}' missing health check. "
                        f"This may cause race conditions where tests start before service is ready.",
                        "fix": self._suggest_health_check(service_name, service_config),
                    }
                )

        # Check connection strings in env
        self._validate_connection_strings_host(job_name, job_config, services)

    def _validate_connection_strings_container(self) -> None:
        """Validate connection strings for container-based networking."""
        # Extract env vars from steps
        env_vars = self._extract_env_vars(job_config)

        for service_name in services:
            # Check common connection string patterns
            if service_name == "postgres":
                self._check_postgres_connection(
                    job_name, env_vars, service_name, use_localhost=False
                )
            elif service_name == "redis":
                self._check_redis_connection(
                    job_name, env_vars, service_name, use_localhost=False
                )

    def _validate_connection_strings_host(self) -> None:
        """Validate connection strings for host-based networking."""
        # Extract env vars from steps
        env_vars = self._extract_env_vars(job_config)

        for service_name in services:
            # Check common connection string patterns
            if service_name == "postgres":
                self._check_postgres_connection(
                    job_name, env_vars, service_name, use_localhost=True
                )
            elif service_name == "redis":
                self._check_redis_connection(
                    job_name, env_vars, service_name, use_localhost=True
                )

    def _check_postgres_connection(self) -> None:
        """Check PostgreSQL connection string."""
        database_url = env_vars.get("DATABASE_URL", "")

        if not database_url:
            return  # No DATABASE_URL found, skip

        expected_host = "localhost" if use_localhost else service_name
        actual_host_match = re.search(r"@([^:]+):", database_url)

        if actual_host_match:
            actual_host = actual_host_match.group(1)
            if actual_host != expected_host:
                self.issues.append(
                    {
                        "type": "incorrect_hostname",
                        "severity": "error",
                        "job": job_name,
                        "service": service_name,
                        "message": f"DATABASE_URL uses '{actual_host}' but should use '{expected_host}' "
                        f"for {'host-based' if use_localhost else 'container-based'} networking.",
                        "fix": f"Change DATABASE_URL to use '@{expected_host}:'",
                    }
                )

    def _check_redis_connection(self) -> None:
        """Check Redis connection string."""
        redis_url = env_vars.get("REDIS_URL", "") or env_vars.get("REDIS_HOST", "")

        if not redis_url:
            return  # No Redis URL found, skip

        expected_host = "localhost" if use_localhost else service_name

        if "redis://" in redis_url:
            # Parse redis:// URL
            host_match = re.search(r"redis://([^:/@]+)", redis_url)
            if host_match:
                actual_host = host_match.group(1)
                if actual_host != expected_host:
                    self.issues.append(
                        {
                            "type": "incorrect_hostname",
                            "severity": "error",
                            "job": job_name,
                            "service": service_name,
                            "message": f"REDIS_URL uses '{actual_host}' but should use '{expected_host}' "
                            f"for {'host-based' if use_localhost else 'container-based'} networking.",
                            "fix": f"Change REDIS_URL to use 'redis://{expected_host}:'",
                        }
                    )
        elif expected_host not in redis_url:
            self.warnings.append(
                {
                    "type": "possible_incorrect_hostname",
                    "severity": "warning",
                    "job": job_name,
                    "service": service_name,
                    "message": f"REDIS_URL may not use correct hostname. Expected '{expected_host}'.",
                }
            )

    def _extract_env_vars(self, job_config: dict) -> dict[str, str]:
        """Extract environment variables from job configuration."""
        env_vars = {}

        # Check job-level env
        if "env" in job_config:
            env_vars.update(job_config["env"])

        # Check step-level env
        for step in job_config.get("steps", []):
            if "env" in step:
                env_vars.update(step["env"])

        return env_vars

    def _suggest_health_check(self, service_name: str, service_config: dict) -> str:
        """Suggest appropriate health check based on service image."""
        image = service_config.get("image", "")

        if "postgres" in image.lower():
            return """Add health check:
options: >-
  --health-cmd pg_isready
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5"""

        if "redis" in image.lower():
            return """Add health check:
options: >-
  --health-cmd "redis-cli ping"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5"""

        if "mysql" in image.lower() or "mariadb" in image.lower():
            return """Add health check:
options: >-
  --health-cmd "mysqladmin ping"
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5"""

        return f"Add appropriate health check for {image}"


def print_report(self) -> None:
    """Print validation report."""
    print(f"\n{'=' * 80}")
    print(f"🔍 Service Networking Validation: {workflow_path}")
    print(f"{'=' * 80}\n")

    if is_valid and not warnings:
        print("✅ All service networking configurations are correct!\n")
        print("Configuration follows Phase 3 best practices:")
        print("  ✓ Correct networking model (host-based vs container-based)")
        print("  ✓ Proper port mappings")
        print("  ✓ Health checks configured")
        print("  ✓ Connection strings use correct hostnames")
        return

    # Print errors
    if issues:
        print(f"❌ Found {len(issues)} error(s):\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. [{issue['severity'].upper()}] {issue['type']}")
            print(f"   Job: {issue.get('job', 'N/A')}")
            if "service" in issue:
                print(f"   Service: {issue['service']}")
            print(f"   Problem: {issue['message']}")
            if "fix" in issue:
                print(f"   Fix: {issue['fix']}")
            print()

    # Print warnings
    if warnings:
        print(f"⚠️  Found {len(warnings)} warning(s):\n")
        for i, warning in enumerate(warnings, 1):
            print(f"{i}. [{warning['severity'].upper()}] {warning['type']}")
            print(f"   Job: {warning.get('job', 'N/A')}")
            if "service" in warning:
                print(f"   Service: {warning['service']}")
            print(f"   Issue: {warning['message']}")
            if "fix" in warning:
                print(f"   Recommendation: {warning['fix']}")
            print()

    # Summary
    print(f"{'=' * 80}")
    if issues:
        print(f"Status: ❌ FAILED - {len(issues)} error(s) must be fixed")
    else:
        print(f"Status: ⚠️  WARNINGS - {len(warnings)} recommendation(s)")
    print(f"{'=' * 80}\n")


def main(self) -> None:
    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions service container networking configuration"
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        help="Path to workflow file (default: validate all workflows)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Suggest fixes for identified issues (not yet implemented)",
    )

    args = parser.parse_args()

    # Find workflows to validate
    if args.workflow:
        workflows = [args.workflow]
    else:
        workflows_dir = Path(".github/workflows")
        if not workflows_dir.exists():
            print(f"Error: {workflows_dir} not found")
            sys.exit(1)
        workflows = list(workflows_dir.glob("*.yml"))

    # Validate each workflow
    all_valid = True
    for workflow_path in workflows:
        validator = ServiceNetworkingValidator(workflow_path)
        is_valid, issues, warnings = validator.validate()

        print_report(workflow_path, is_valid, issues, warnings)

        if not is_valid:
            all_valid = False

    # Exit with appropriate code
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
