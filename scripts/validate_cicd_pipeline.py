#!/usr/bin/env python3
"""
PAKE System - CI/CD Pipeline Validation Script
Validates that all CI/CD pipeline components are properly configured
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any


class CICDPipelineValidator:
    """Validates CI/CD pipeline configuration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            "validation_results": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }
    
    def validate_check(self, check_name: str, check_func) -> bool:
        """Run a single validation check"""
        print(f"🔍 Validating: {check_name}")
        
        try:
            result = check_func()
            self.results["validation_results"].append({
                "name": check_name,
                "status": "passed" if result else "failed",
                "details": f"{check_name} validation {'passed' if result else 'failed'}"
            })
            
            if result:
                self.results["summary"]["passed"] += 1
                print(f"✅ {check_name}: PASSED")
            else:
                self.results["summary"]["failed"] += 1
                print(f"❌ {check_name}: FAILED")
            
        except Exception as e:
            self.results["validation_results"].append({
                "name": check_name,
                "status": "error",
                "details": str(e)
            })
            self.results["summary"]["failed"] += 1
            print(f"💥 {check_name}: ERROR - {str(e)}")
        
        self.results["summary"]["total"] += 1
        return result
    
    def check_workflow_files(self) -> bool:
        """Check that workflow files exist and are valid"""
        workflow_dir = self.project_root / ".github" / "workflows"
        
        required_files = [
            "ci.yml",
            "deploy.yml"
        ]
        
        for file_name in required_files:
            file_path = workflow_dir / file_name
            if not file_path.exists():
                print(f"Missing workflow file: {file_path}")
                return False
            
            # Basic YAML validation
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if "name:" not in content or "on:" not in content:
                        print(f"Invalid workflow file: {file_path}")
                        return False
            except Exception as e:
                print(f"Error reading workflow file {file_path}: {e}")
                return False
        
        return True
    
    def check_scripts_directory(self) -> bool:
        """Check that required scripts exist"""
        scripts_dir = self.project_root / "scripts"
        
        required_scripts = [
            "security_test_suite.py",
            "performance_test_suite.py",
            "validate_production_health.py",
            "generate_deployment_report.py"
        ]
        
        for script_name in required_scripts:
            script_path = scripts_dir / script_name
            if not script_path.exists():
                print(f"Missing script: {script_path}")
                return False
            
            # Check if script is executable
            if not os.access(script_path, os.R_OK):
                print(f"Script not readable: {script_path}")
                return False
        
        return True
    
    def check_pyproject_configuration(self) -> bool:
        """Check pyproject.toml configuration"""
        pyproject_path = self.project_root / "pyproject.toml"
        
        if not pyproject_path.exists():
            print("Missing pyproject.toml")
            return False
        
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read()
                
                # Check for required dependencies
                required_deps = [
                    "pytest-cov",
                    "safety",
                    "bandit",
                    "pip-audit",
                    "httpx"
                ]
                
                for dep in required_deps:
                    if dep not in content:
                        print(f"Missing dependency in pyproject.toml: {dep}")
                        return False
                
                # Check for pytest configuration
                if "[tool.pytest.ini_options]" not in content:
                    print("Missing pytest configuration in pyproject.toml")
                    return False
                
                # Check for coverage configuration
                if "[tool.coverage.run]" not in content:
                    print("Missing coverage configuration in pyproject.toml")
                    return False
        
        except Exception as e:
            print(f"Error reading pyproject.toml: {e}")
            return False
        
        return True
    
    def check_dockerfile_exists(self) -> bool:
        """Check that production Dockerfile exists"""
        dockerfile_path = self.project_root / "Dockerfile.production"
        
        if not dockerfile_path.exists():
            print("Missing Dockerfile.production")
            return False
        
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                if "FROM" not in content:
                    print("Invalid Dockerfile.production")
                    return False
        except Exception as e:
            print(f"Error reading Dockerfile.production: {e}")
            return False
        
        return True
    
    def check_documentation_exists(self) -> bool:
        """Check that CI/CD documentation exists"""
        docs_dir = self.project_root / "docs"
        cicd_doc = docs_dir / "CICD_PIPELINE.md"
        
        if not cicd_doc.exists():
            print("Missing CI/CD documentation")
            return False
        
        return True
    
    def check_environment_example(self) -> bool:
        """Check that environment example file exists"""
        env_example = self.project_root / "env.example"
        
        if not env_example.exists():
            print("Missing env.example file")
            return False
        
        return True
    
    def validate_script_syntax(self) -> bool:
        """Validate Python script syntax"""
        scripts_dir = self.project_root / "scripts"
        
        python_scripts = [
            "security_test_suite.py",
            "performance_test_suite.py",
            "validate_production_health.py",
            "generate_deployment_report.py"
        ]
        
        for script_name in python_scripts:
            script_path = scripts_dir / script_name
            try:
                # Basic syntax check
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(script_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Syntax error in {script_name}: {result.stderr}")
                    return False
            except Exception as e:
                print(f"Error validating {script_name}: {e}")
                return False
        
        return True
    
    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        print("🔍 Starting PAKE System CI/CD Pipeline Validation")
        print("=" * 60)
        
        validations = [
            ("Workflow Files", self.check_workflow_files),
            ("Scripts Directory", self.check_scripts_directory),
            ("PyProject Configuration", self.check_pyproject_configuration),
            ("Production Dockerfile", self.check_dockerfile_exists),
            ("CI/CD Documentation", self.check_documentation_exists),
            ("Environment Example", self.check_environment_example),
            ("Script Syntax", self.validate_script_syntax),
        ]
        
        all_passed = True
        for validation_name, validation_func in validations:
            result = self.validate_check(validation_name, validation_func)
            if not result:
                all_passed = False
        
        # Generate summary
        print("\n" + "=" * 60)
        print("🔍 CI/CD Pipeline Validation Summary")
        print(f"Total Validations: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        
        if all_passed:
            print("✅ All CI/CD pipeline validations passed!")
        else:
            print("❌ Some CI/CD pipeline validations failed!")
        
        return all_passed
    
    def save_report(self, filename: str = "cicd_validation_report.json"):
        """Save validation results to file"""
        report_path = self.project_root / filename
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Validation report saved to {report_path}")


def main():
    """Main entry point"""
    validator = CICDPipelineValidator()
    success = validator.run_all_validations()
    validator.save_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
