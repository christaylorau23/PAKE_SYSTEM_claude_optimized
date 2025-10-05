#!/usr/bin/env python3
"""
Phase 4: Environment Variable Synchronization Script
PAKE System - Strategic Plan for Codebase Remediation

This script synchronizes environment variables between local and CI environments,
ensuring consistency and proper secrets management.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnvironmentType(Enum):
    LOCAL = "local"
    CI = "ci"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class EnvironmentVariable:
    name: str
    value: str | None
    required: bool
    sensitive: bool
    description: str
    environments: set[EnvironmentType]


class EnvironmentSynchronizer:
    """Synchronizes environment variables across different environments."""

    def __init__(self) -> None:
        self.project_root = project_root
        self.env_vars: dict[str, EnvironmentVariable] = {}
        self.workflow_files: list[Path] = []
        self.config_files: list[Path] = []

    def discover_files(self) -> None:
        """Discover all relevant configuration files."""
        logger.info("Discovering configuration files...")

        # Find GitHub Actions workflow files
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            self.workflow_files = list(workflows_dir.glob("*.yml")) + list(
                workflows_dir.glob("*.yaml")
            )

        # Find configuration files
        config_patterns = [
            "**/.env*",
            "**/config*.yml",
            "**/config*.yaml",
            "**/config*.json",
            "**/docker-compose*.yml",
            "**/Dockerfile*",
            "**/pyproject.toml",
            "**/package.json",
        ]

        for pattern in config_patterns:
            self.config_files.extend(self.project_root.glob(pattern))

        logger.info(
            "Found %s workflow files and %s config files",
            len(self.workflow_files),
            len(self.config_files),
        )

    def load_environment_template(self) -> None:
        """Load environment variables from template files."""
        logger.info("Loading environment variable definitions...")

        # Load from env.example
        env_example = self.project_root / "env.example"
        if env_example.exists():
            self._parse_env_file(env_example)

        # Load from pyproject.toml
        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            self._parse_pyproject_toml(pyproject_file)

        # Load from package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            self._parse_package_json(package_json)

    def _parse_env_file(self, env_file: Path) -> None:
        """Parse environment file and extract variable definitions."""
        logger.info("Parsing environment file: %s", env_file)

        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    name, value = line.split("=", 1)
                    name = name.strip()
                    value = value.strip()

                    # Determine if sensitive based on name patterns
                    sensitive_patterns = [
                        "password",
                        "secret",
                        "key",
                        "token",
                        "credential",
                        "auth",
                        "api_key",
                        "jwt",
                        "private",
                    ]
                    sensitive = any(
                        pattern in name.lower() for pattern in sensitive_patterns
                    )

                    # Determine required based on value patterns
                    required = value not in [
                        "",
                        "your-secret-here",
                        "change-this",
                        "optional",
                    ]

                    # Determine environments based on comments and context
                    environments = {EnvironmentType.LOCAL, EnvironmentType.CI}
                    if "production" in value.lower() or "prod" in value.lower():
                        environments.add(EnvironmentType.PRODUCTION)
                    if "staging" in value.lower() or "stage" in value.lower():
                        environments.add(EnvironmentType.STAGING)

                    self.env_vars[name] = EnvironmentVariable(
                        name=name,
                        value=value if not sensitive else None,
                        required=required,
                        sensitive=sensitive,
                        description=f"From {env_file.name}:{line_num}",
                        environments=environments,
                    )

    def _parse_pyproject_toml(self, pyproject_file: Path) -> None:
        """Parse pyproject.toml for environment variable references."""
        logger.info("Parsing pyproject.toml: %s", pyproject_file)

        try:
            import tomllib

            with open(pyproject_file, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            # Fallback for older Python versions
            import tomli

            with open(pyproject_file, "rb") as f:
                data = tomli.load(f)

        # Look for environment variable references in scripts and tool configurations
        self._extract_env_refs_from_dict(data, pyproject_file)

    def _parse_package_json(self, package_json: Path) -> None:
        """Parse package.json for environment variable references."""
        logger.info("Parsing package.json: %s", package_json)

        with open(package_json) as f:
            data = json.load(f)

        self._extract_env_refs_from_dict(data, package_json)

    def _extract_env_refs_from_dict(self, data: dict, source_file: Path) -> None:
        """Extract environment variable references from dictionary data."""

        def find_env_refs(self) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    find_env_refs(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_env_refs(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                # Look for environment variable patterns
                import re

                env_pattern = r"\$\{?([A-Z_][A-Z0-9_]*)\}?"
                matches = re.findall(env_pattern, obj)
                for match in matches:
                    if match not in self.env_vars:
                        self.env_vars[match] = EnvironmentVariable(
                            name=match,
                            value=None,
                            required=True,
                            sensitive=True,
                            description=f"Referenced in {source_file.name}:{path}",
                            environments={EnvironmentType.LOCAL, EnvironmentType.CI},
                        )

        find_env_refs(data)

    def analyze_workflow_files(self) -> None:
        """Analyze GitHub Actions workflow files for environment variable usage."""
        logger.info("Analyzing GitHub Actions workflow files...")

        for workflow_file in self.workflow_files:
            logger.info("Analyzing workflow: %s", workflow_file)

            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                self._extract_workflow_env_vars(workflow_data, workflow_file)

            except Exception as e:
                logger.error("Error analyzing %s: %s", workflow_file, e)

    def _extract_workflow_env_vars(
        self, workflow_data: dict, workflow_file: Path
    ) -> None:
        """Extract environment variables from workflow data."""

        def find_env_vars(self) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "env" and isinstance(value, dict):
                        for env_name, env_value in value.items():
                            if env_name not in self.env_vars:
                                self.env_vars[env_name] = EnvironmentVariable(
                                    name=env_name,
                                    value=str(env_value)
                                    if not env_name.startswith("${{")
                                    else None,
                                    required=True,
                                    sensitive=env_name.startswith("${{ secrets."),
                                    description=f"From {workflow_file.name}:{path}",
                                    environments={EnvironmentType.CI},
                                )
                    else:
                        find_env_vars(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_env_vars(item, f"{path}[{i}]")

        find_env_vars(workflow_data)

    def generate_github_secrets_template(self) -> str:
        """Generate a template for GitHub repository secrets."""
        logger.info("Generating GitHub secrets template...")

        template = "# GitHub Repository Secrets Configuration\n\n"
        template += "# Add these secrets to your GitHub repository:\n"
        template += "# Settings > Secrets and variables > Actions > Secrets\n\n"

        sensitive_vars = [var for var in self.env_vars.values() if var.sensitive]

        for var in sorted(sensitive_vars, key=lambda x: x.name):
            template += f"# {var.description}\n"
            template += f"# {var.name}={var.value or '[REDACTED_SECRET]'}\n\n"

        return template

    def generate_workflow_secrets_update(self) -> str:
        """Generate updated workflow files with proper secrets context."""
        logger.info("Generating workflow secrets update...")

        return """
# Updated GitHub Actions Workflow with Proper Secrets Management

# Add this to your workflow files in the env section:
env:
  # Non-sensitive configuration
  PYTHON_VERSION: '3.12'
  NODE_VERSION: '22.18.0'
  REGISTRY_URL: 'ghcr.io'
  IMAGE_NAME: 'pake-system'

  # Sensitive secrets (from GitHub repository secrets)
  SECRET_KEY: ${{ secrets.SECRET_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  REDIS_URL: ${{ secrets.REDIS_URL }}
  API_KEY: ${{ secrets.API_KEY }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}

  # API Keys
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

  # Optional API Keys
  DID_API_KEY: ${{ secrets.DID_API_KEY }}
  HEYGEN_API_KEY: ${{ secrets.HEYGEN_API_KEY }}

  # Webhook Security
  WEBHOOK_SECRET: ${{ secrets.WEBHOOK_SECRET }}

  # HashiCorp Vault Configuration
  VAULT_ADDR: ${{ secrets.VAULT_ADDR }}
  VAULT_ROLE_ID: ${{ secrets.VAULT_ROLE_ID }}
  VAULT_SECRET_ID: ${{ secrets.VAULT_SECRET_ID }}
"""

    def generate_vault_integration_script(self) -> str:
        """Generate HashiCorp Vault integration script."""
        logger.info("Generating HashiCorp Vault integration script...")

        return """#!/bin/bash
# HashiCorp Vault Integration Script
# PAKE System - Phase 4 Implementation

set -euo pipefail

# Configuration
VAULT_ADDR="${VAULT_ADDR:-https://vault.pake-system.com}"
VAULT_ROLE_ID="${VAULT_ROLE_ID}"
VAULT_SECRET_ID="${VAULT_SECRET_ID}"
VAULT_PATH="secret/pake-system"

# Function to authenticate with Vault using JWT/OIDC
authenticate_vault() {
    echo "🔐 Authenticating with HashiCorp Vault..."

    # Get OIDC token from GitHub Actions
    if [ -n "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]; then
        echo "Using GitHub Actions OIDC token..."
        OIDC_TOKEN=$(curl -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=vault" | jq -r .value)

        # Authenticate with Vault using OIDC
        VAULT_TOKEN=$(vault write -field=token auth/jwt/login \
            role="pake-system-role" \
            jwt="$OIDC_TOKEN")

        export VAULT_TOKEN
        echo "✅ Successfully authenticated with Vault"
    else
        echo "❌ No GitHub Actions OIDC token available"
        exit 1
    fi
}

# Function to retrieve secrets from Vault
get_secret() {
    local secret_name="$1"
    local secret_path="$VAULT_PATH/$secret_name"

    echo "🔑 Retrieving secret: $secret_name"

    if vault kv get -field=value "$secret_path" 2>/dev/null; then
        echo "✅ Successfully retrieved $secret_name"
    else
        echo "❌ Failed to retrieve $secret_name"
        return 1
    fi
}

# Function to export all required secrets as environment variables
export_secrets() {
    echo "📤 Exporting secrets as environment variables..."

    # Core secrets
    export SECRET_KEY=$(get_secret "jwt-secret")
    export DATABASE_URL=$(get_secret "database-url")
    export REDIS_URL=$(get_secret "redis-url")
    export API_KEY=$(get_secret "api-key")
    export DB_PASSWORD=$(get_secret "db-password")
    export REDIS_PASSWORD=$(get_secret "redis-password")

    # API Keys
    export ANTHROPIC_API_KEY=$(get_secret "anthropic-api-key")
    export GEMINI_API_KEY=$(get_secret "gemini-api-key")

    # Optional API Keys
    export DID_API_KEY=$(get_secret "did-api-key" || echo "")
    export HEYGEN_API_KEY=$(get_secret "heygen-api-key" || echo "")

    # Webhook Security
    export WEBHOOK_SECRET=$(get_secret "webhook-secret")

    echo "✅ All secrets exported successfully"
}

# Main execution
main() {
    echo "🚀 Starting HashiCorp Vault integration..."

    # Check required environment variables
    if [ -z "${VAULT_ROLE_ID:-}" ] || [ -z "${VAULT_SECRET_ID:-}" ]; then
        echo "❌ VAULT_ROLE_ID and VAULT_SECRET_ID must be set"
        exit 1
    fi

    # Authenticate with Vault
    authenticate_vault

    # Export secrets
    export_secrets

    echo "🎉 Vault integration completed successfully"
}

# Run main function
main "$@"
"""

    def generate_case_sensitivity_fix_script(self) -> str:
        """Generate script to fix case-sensitivity issues."""
        logger.info("Generating case-sensitivity fix script...")

        return '''#!/usr/bin/env python3
"""
Case-Sensitivity Fix Script
PAKE System - Phase 4 Implementation

This script fixes case-sensitivity issues in file paths, imports, and resource lookups.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def find_case_sensitivity_issues(root_path: Path) -> List[Tuple[str, str, str]]:
    """
    Find case-sensitivity issues in the codebase.
    Returns list of (file_path, line_number, issue_description)
    """
    issues = []

    # Patterns to look for case-sensitivity issues
    patterns = [
        # Import statements with mixed case
        (r'from\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s+import', 'import'),
        (r'import\\s+([a-zA-Z_][a-zA-Z0-9_]*)', 'import'),
        # File paths with mixed case
        (r'["\']([^"\']*[A-Z][^"\']*[a-z][^"\']*|[^"\']*[a-z][^"\']*[A-Z][^"\']*)["\']', 'file_path'),
        # Resource lookups with mixed case
        (r'open\\(["\']([^"\']*[A-Z][^"\']*[a-z][^"\']*|[^"\']*[a-z][^"\']*[A-Z][^"\']*)["\']', 'file_open'),
    ]

    for py_file in root_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern, issue_type in patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            if issue_type == 'import':
                                module_name = match.group(1)
                                if re.search(r'[A-Z].*[a-z]|[a-z].*[A-Z]', module_name):
                                    issues.append((
                                        str(py_file),
                                        str(line_num),
                                        f"Mixed case in import: {module_name}"
                                    ))
                            elif issue_type in ['file_path', 'file_open']:
                                file_path = match.group(1)
                                if re.search(r'[A-Z].*[a-z]|[a-z].*[A-Z]', file_path):
                                    issues.append((
                                        str(py_file),
                                        str(line_num),
                                        f"Mixed case in file path: {file_path}"
                                    ))
        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    return issues

def fix_case_sensitivity_issues(issues: List[Tuple[str, str, str]]) -> None:
    """Fix case-sensitivity issues by correcting file paths and imports."""
    print(f"Found {len(issues)} case-sensitivity issues")

    for file_path, line_num, issue in issues:
        print(f"Fixing: {file_path}:{line_num} - {issue}")

        # This is a placeholder - actual fixes would need to be implemented
        # based on the specific issues found
        pass

def main(self) -> None:
    """Main function to run case-sensitivity fixes."""
    root_path = Path(__file__).parent.parent
    print(f"Scanning for case-sensitivity issues in: {root_path}")

    issues = find_case_sensitivity_issues(root_path)

    if issues:
        print(f"Found {len(issues)} case-sensitivity issues:")
        for file_path, line_num, issue in issues[:10]:  # Show first 10
            print(f"  {file_path}:{line_num} - {issue}")

        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")

        # Uncomment to actually fix issues
        # fix_case_sensitivity_issues(issues)
    else:
        print("No case-sensitivity issues found!")

if __name__ == "__main__":
    main()
'''

    def generate_comprehensive_report(self) -> str:
        """Generate a comprehensive remediation report."""
        logger.info("Generating comprehensive remediation report...")

        report = f"""
# Phase 4: Codebase Remediation Report
# PAKE System - Strategic Plan Implementation

## Executive Summary

This report documents the implementation of Phase 4 remediation strategies for the PAKE System,
focusing on environment-specific configuration errors and secrets management.

## Environment Variable Analysis

### Total Environment Variables Identified: {len(self.env_vars)}

### Required Variables: {len([v for v in self.env_vars.values() if v.required])}
### Sensitive Variables: {len([v for v in self.env_vars.values() if v.sensitive])}

### Variable Breakdown by Environment:
"""

        for env_type in EnvironmentType:
            env_vars = [v for v in self.env_vars.values() if env_type in v.environments]
            report += f"- **{env_type.value.title()}**: {len(env_vars)} variables\n"

        report += f"""
## Files Analyzed

### Workflow Files: {len(self.workflow_files)}
"""
        for workflow in self.workflow_files:
            report += f"- {workflow.relative_to(self.project_root)}\n"

        report += f"""
### Configuration Files: {len(self.config_files)}
"""
        for config in self.config_files[:10]:  # Show first 10
            report += f"- {config.relative_to(self.project_root)}\n"

        if len(self.config_files) > 10:
            report += f"- ... and {len(self.config_files) - 10} more files\n"

        report += f"""
## Recommendations

### 1. Immediate Actions Required
- [ ] Add all sensitive variables to GitHub repository secrets
- [ ] Update workflow files to use proper secrets context
- [ ] Implement HashiCorp Vault integration
- [ ] Fix case-sensitivity issues in file paths

### 2. Security Improvements
- [ ] Implement JWT/OIDC authentication for Vault
- [ ] Add secret rotation policies
- [ ] Implement audit logging for secret access
- [ ] Add secret expiration monitoring

### 3. Long-term Enhancements
- [ ] Implement multi-region secret replication
- [ ] Add secret versioning
- [ ] Implement automated secret rotation
- [ ] Add comprehensive monitoring and alerting

## Next Steps

1. **Execute Environment Synchronization**: Run the generated scripts to sync environment variables
2. **Update GitHub Secrets**: Add all sensitive variables to repository secrets
3. **Deploy Vault Integration**: Implement HashiCorp Vault with JWT/OIDC authentication
4. **Validate Fixes**: Run comprehensive testing to ensure all issues are resolved

---
Generated on: {os.popen("date").read().strip()}
Script Version: Phase 4 Implementation v1.0
"""

        return report

    def run_analysis(self) -> None:
        """Run the complete environment synchronization analysis."""
        logger.info("Starting Phase 4 environment synchronization analysis...")

        # Discover files
        self.discover_files()

        # Load environment template
        self.load_environment_template()

        # Analyze workflow files
        self.analyze_workflow_files()

        # Generate outputs
        logger.info("Generating remediation outputs...")

        # Create output directory
        output_dir = self.project_root / "phase4_remediation"
        output_dir.mkdir(exist_ok=True)

        # Generate GitHub secrets template
        secrets_template = self.generate_github_secrets_template()
        with open(output_dir / "github_secrets_template.md", "w") as f:
            f.write(secrets_template)

        # Generate workflow secrets update
        workflow_update = self.generate_workflow_secrets_update()
        with open(output_dir / "workflow_secrets_update.md", "w") as f:
            f.write(workflow_update)

        # Generate Vault integration script
        vault_script = self.generate_vault_integration_script()
        with open(output_dir / "vault_integration.sh", "w") as f:
            f.write(vault_script)
        os.chmod(output_dir / "vault_integration.sh", 0o755)

        # Generate case-sensitivity fix script
        case_fix_script = self.generate_case_sensitivity_fix_script()
        with open(output_dir / "fix_case_sensitivity.py", "w") as f:
            f.write(case_fix_script)
        os.chmod(output_dir / "fix_case_sensitivity.py", 0o755)

        # Generate comprehensive report
        report = self.generate_comprehensive_report()
        with open(output_dir / "phase4_remediation_report.md", "w") as f:
            f.write(report)

        logger.info("Phase 4 remediation outputs generated in: %s", output_dir)
        logger.info("Analysis complete!")


def main(self) -> None:
    """Main function to run the environment synchronization analysis."""
    project_root = Path(__file__).parent.parent
    synchronizer = EnvironmentSynchronizer(project_root)
    synchronizer.run_analysis()


if __name__ == "__main__":
    main()
