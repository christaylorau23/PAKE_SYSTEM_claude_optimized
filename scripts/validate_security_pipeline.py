#!/usr/bin/env python3
"""
PAKE System Security Pipeline Validation Script
Phoenix Protocol Phase 7.2 - Security Pipeline Testing and Validation

This script validates the security pipeline implementation and tests all components.
"""

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityPipelineValidator:
    """Validator for the Phoenix Protocol Security Pipeline."""
    
    def __init__(self):
        """Initialize the security pipeline validator."""
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "validations": {},
            "summary": {
                "total_validations": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    def validate_workflow_files(self) -> Dict[str, Any]:
        """Validate GitHub Actions workflow files."""
        logger.info("Validating GitHub Actions workflow files...")
        
        workflow_dir = Path(".github/workflows")
        results = {
            "success": True,
            "workflows": [],
            "issues": []
        }
        
        if not workflow_dir.exists():
            results["success"] = False
            results["issues"].append("GitHub workflows directory not found")
            return results
        
        # Check for Phoenix Protocol security workflow
        phoenix_workflow = workflow_dir / "phoenix-protocol-security.yml"
        if phoenix_workflow.exists():
            results["workflows"].append("phoenix-protocol-security.yml")
            logger.info("✅ Phoenix Protocol security workflow found")
        else:
            results["success"] = False
            results["issues"].append("Phoenix Protocol security workflow not found")
        
        # Validate workflow syntax
        for workflow_file in workflow_dir.glob("*.yml"):
            try:
                result = subprocess.run(
                    ["yamllint", str(workflow_file)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    results["issues"].append(f"YAML syntax issues in {workflow_file.name}")
            except FileNotFoundError:
                logger.warning("yamllint not available, skipping YAML validation")
        
        return results
    
    def validate_security_tools(self) -> Dict[str, Any]:
        """Validate security tools availability."""
        logger.info("Validating security tools availability...")
        
        tools = {
            "trivy": ["trivy", "--version"],
            "bandit": ["bandit", "--version"],
            "safety": ["safety", "--version"],
            "pip-audit": ["pip-audit", "--version"],
            "ruff": ["ruff", "--version"],
            "semgrep": ["semgrep", "--version"],
            "trufflehog": ["trufflehog", "--version"],
            "gitleaks": ["gitleaks", "--version"]
        }
        
        results = {
            "success": True,
            "tools": {},
            "missing_tools": []
        }
        
        for tool_name, command in tools.items():
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results["tools"][tool_name] = {
                        "available": True,
                        "version": result.stdout.strip()
                    }
                    logger.info(f"✅ {tool_name} is available")
                else:
                    results["tools"][tool_name] = {"available": False}
                    results["missing_tools"].append(tool_name)
                    logger.warning(f"⚠️ {tool_name} not available")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                results["tools"][tool_name] = {"available": False}
                results["missing_tools"].append(tool_name)
                logger.warning(f"⚠️ {tool_name} not available")
        
        if results["missing_tools"]:
            results["success"] = False
        
        return results
    
    def validate_configuration_files(self) -> Dict[str, Any]:
        """Validate security configuration files."""
        logger.info("Validating security configuration files...")
        
        config_files = [
            ".trufflehog-ignore",
            "sonar-project.properties",
            "security-gate-config.yaml"
        ]
        
        results = {
            "success": True,
            "files": {},
            "missing_files": []
        }
        
        for config_file in config_files:
            file_path = Path(config_file)
            if file_path.exists():
                results["files"][config_file] = {
                    "exists": True,
                    "size": file_path.stat().st_size
                }
                logger.info(f"✅ {config_file} found")
            else:
                results["files"][config_file] = {"exists": False}
                results["missing_files"].append(config_file)
                logger.warning(f"⚠️ {config_file} not found")
        
        if results["missing_files"]:
            results["success"] = False
        
        return results
    
    def validate_security_scripts(self) -> Dict[str, Any]:
        """Validate security testing scripts."""
        logger.info("Validating security testing scripts...")
        
        scripts_dir = Path("scripts")
        security_scripts = [
            "security_test_suite.py"
        ]
        
        results = {
            "success": True,
            "scripts": {},
            "missing_scripts": []
        }
        
        if not scripts_dir.exists():
            results["success"] = False
            results["missing_scripts"] = security_scripts
            return results
        
        for script in security_scripts:
            script_path = scripts_dir / script
            if script_path.exists():
                # Check if script is executable
                is_executable = os.access(script_path, os.X_OK)
                results["scripts"][script] = {
                    "exists": True,
                    "executable": is_executable,
                    "size": script_path.stat().st_size
                }
                logger.info(f"✅ {script} found")
            else:
                results["scripts"][script] = {"exists": False}
                results["missing_scripts"].append(script)
                logger.warning(f"⚠️ {script} not found")
        
        if results["missing_scripts"]:
            results["success"] = False
        
        return results
    
    def validate_dependency_management(self) -> Dict[str, Any]:
        """Validate dependency management setup."""
        logger.info("Validating dependency management...")
        
        results = {
            "success": True,
            "files": {},
            "issues": []
        }
        
        # Check for Poetry configuration
        pyproject_toml = Path("pyproject.toml")
        poetry_lock = Path("poetry.lock")
        
        if pyproject_toml.exists():
            results["files"]["pyproject.toml"] = {"exists": True}
            logger.info("✅ pyproject.toml found")
        else:
            results["files"]["pyproject.toml"] = {"exists": False}
            results["issues"].append("pyproject.toml not found")
        
        if poetry_lock.exists():
            results["files"]["poetry.lock"] = {"exists": True}
            logger.info("✅ poetry.lock found")
        else:
            results["files"]["poetry.lock"] = {"exists": False}
            results["issues"].append("poetry.lock not found - required for deterministic builds")
        
        # Check for deprecated requirements.txt files
        requirements_files = list(Path(".").glob("requirements*.txt"))
        if requirements_files:
            results["issues"].append(f"Found {len(requirements_files)} requirements.txt files - should use Poetry")
        
        if results["issues"]:
            results["success"] = False
        
        return results
    
    def validate_security_gates(self) -> Dict[str, Any]:
        """Validate security gate configuration."""
        logger.info("Validating security gate configuration...")
        
        results = {
            "success": True,
            "gates": {},
            "issues": []
        }
        
        # Check security gate configuration
        config_file = Path("security-gate-config.yaml")
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Validate security gate thresholds
                gate_config = config.get("SECURITY_GATE_CONFIG", {})
                if gate_config.get("CRITICAL_VULNERABILITIES_MAX", 0) > 0:
                    results["issues"].append("Critical vulnerabilities threshold should be 0")
                
                if gate_config.get("HIGH_VULNERABILITIES_MAX", 0) > 0:
                    results["issues"].append("High vulnerabilities threshold should be 0")
                
                results["gates"]["configuration"] = {"valid": True}
                logger.info("✅ Security gate configuration validated")
                
            except (pydantic.ValidationError, ValueError) as e:
                results["issues"].append(f"Error parsing security gate config: {e}")
        else:
            results["issues"].append("Security gate configuration file not found")
        
        if results["issues"]:
            results["success"] = False
        
        return results
    
    def validate_ci_cd_integration(self) -> Dict[str, Any]:
        """Validate CI/CD integration."""
        logger.info("Validating CI/CD integration...")
        
        results = {
            "success": True,
            "integrations": {},
            "issues": []
        }
        
        # Check for GitHub Actions integration
        workflow_dir = Path(".github/workflows")
        if workflow_dir.exists():
            workflow_files = list(workflow_dir.glob("*.yml"))
            results["integrations"]["github_actions"] = {
                "enabled": True,
                "workflows": len(workflow_files)
            }
            logger.info(f"✅ GitHub Actions integration found ({len(workflow_files)} workflows)")
        else:
            results["integrations"]["github_actions"] = {"enabled": False}
            results["issues"].append("GitHub Actions not configured")
        
        # Check for pre-commit hooks
        pre_commit_config = Path(".pre-commit-config.yaml")
        if pre_commit_config.exists():
            results["integrations"]["pre_commit"] = {"enabled": True}
            logger.info("✅ Pre-commit hooks configured")
        else:
            results["integrations"]["pre_commit"] = {"enabled": False}
            results["issues"].append("Pre-commit hooks not configured")
        
        if results["issues"]:
            results["success"] = False
        
        return results
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of security pipeline."""
        logger.info("Starting comprehensive security pipeline validation...")
        
        validation_categories = [
            ("workflow_files", self.validate_workflow_files),
            ("security_tools", self.validate_security_tools),
            ("configuration_files", self.validate_configuration_files),
            ("security_scripts", self.validate_security_scripts),
            ("dependency_management", self.validate_dependency_management),
            ("security_gates", self.validate_security_gates),
            ("ci_cd_integration", self.validate_ci_cd_integration),
        ]
        
        for category_name, validation_func in validation_categories:
            logger.info(f"Running {category_name} validation...")
            try:
                self.validation_results["validations"][category_name] = validation_func()
                self.validation_results["summary"]["total_validations"] += 1
                
                validation_result = self.validation_results["validations"][category_name]
                if validation_result.get("success", False):
                    self.validation_results["summary"]["passed"] += 1
                else:
                    self.validation_results["summary"]["failed"] += 1
                    
            except (ValueError, RuntimeError) as e:
                logger.error(f"Error running {category_name} validation: {e}")
                self.validation_results["validations"][category_name] = {
                    "success": False,
                    "error": str(e)
                }
                self.validation_results["summary"]["failed"] += 1
        
        return self.validation_results
    
    def generate_validation_report(self, output_file: str = "security_pipeline_validation.json") -> None:
        """Generate validation report."""
        logger.info(f"Generating validation report: {output_file}")
        
        with open(output_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        logger.info(f"Validation report saved to {output_file}")
        
        # Print summary
        summary = self.validation_results["summary"]
        logger.info(f"Security Pipeline Validation Summary:")
        logger.info(f"  Total Validations: {summary['total_validations']}")
        logger.info(f"  Passed: {summary['passed']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Warnings: {summary['warnings']}")
        
        # Print detailed results
        for category, result in self.validation_results["validations"].items():
            status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
            logger.info(f"  {category}: {status}")
            
            if not result.get("success", False) and "issues" in result:
                for issue in result["issues"]:
                    logger.info(f"    - {issue}")


def main():
    """Main entry point for security pipeline validation."""
    parser = argparse.ArgumentParser(description="PAKE System Security Pipeline Validator")
    parser.add_argument(
        "--output",
        help="Output file for validation results",
        default="security_pipeline_validation.json"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize validator
    validator = SecurityPipelineValidator()
    
    # Run comprehensive validation
    results = validator.run_comprehensive_validation()
    
    # Generate report
    validator.generate_validation_report(output_file=args.output)
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        logger.error("Security pipeline validation failed!")
        sys.exit(1)
    else:
        logger.info("Security pipeline validation passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()