"""
TDD CI/CD Pipeline Tests
Test-Driven Development for CI/CD workflow validation
"""

import pytest
import yaml
import json
import os
from pathlib import Path


class TestCICDPipelineTDD:
    """Test-Driven Development for CI/CD components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.github_dir = self.project_root / ".github" / "workflows"
        
    def test_ci_workflow_structure(self):
        """TDD: Test CI workflow has proper structure"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert workflow_data['name'] == 'CI/CD Pipeline', "Should have correct workflow name"
        assert 'jobs' in workflow_data, "Should have jobs section"
        
        required_jobs = ['test', 'lint', 'security', 'build']
        for job in required_jobs:
            assert job in workflow_data['jobs'], f"Should have {job} job"
            
    def test_ci_workflow_triggers(self):
        """TDD: Test CI workflow triggers are properly configured"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert 'on' in workflow_data, "Should have trigger configuration"
        triggers = workflow_data['on']
        
        assert 'push' in triggers, "Should trigger on push"
        assert 'pull_request' in triggers, "Should trigger on pull request"
        
    def test_ci_workflow_environment(self):
        """TDD: Test CI workflow environment variables"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert 'env' in workflow_data, "Should have environment variables"
        env_vars = workflow_data['env']
        
        assert 'PYTHON_VERSION' in env_vars, "Should define Python version"
        assert 'NODE_VERSION' in env_vars, "Should define Node version"
        assert env_vars['PYTHON_VERSION'] == '3.12', "Should use Python 3.12"
        
    def test_ci_workflow_permissions(self):
        """TDD: Test CI workflow has proper permissions"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert 'permissions' in workflow_data, "Should define permissions"
        permissions = workflow_data['permissions']
        
        required_permissions = ['contents', 'security-events', 'issues', 'pull-requests']
        for permission in required_permissions:
            assert permission in permissions, f"Should have {permission} permission"
            
    def test_ci_workflow_test_job(self):
        """TDD: Test CI workflow test job configuration"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        test_job = workflow_data['jobs']['test']
        
        assert test_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        assert 'services' in test_job, "Should have services configuration"
        assert 'postgres' in test_job['services'], "Should have PostgreSQL service"
        assert 'redis' in test_job['services'], "Should have Redis service"
        
        # Check for Poetry installation
        steps = test_job['steps']
        poetry_steps = [step for step in steps if 'Install Poetry' in step.get('name', '')]
        assert len(poetry_steps) > 0, "Should install Poetry"
        
    def test_ci_workflow_lint_job(self):
        """TDD: Test CI workflow lint job configuration"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        lint_job = workflow_data['jobs']['lint']
        
        assert lint_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for linting tools
        steps = lint_job['steps']
        lint_tools = ['Black', 'isort', 'Ruff', 'MyPy']
        
        for tool in lint_tools:
            tool_steps = [step for step in steps if tool in step.get('name', '')]
            assert len(tool_steps) > 0, f"Should run {tool} linter"
            
    def test_ci_workflow_security_job(self):
        """TDD: Test CI workflow security job configuration"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        security_job = workflow_data['jobs']['security']
        
        assert security_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for security tools
        steps = security_job['steps']
        security_tools = ['Bandit', 'Safety']
        
        for tool in security_tools:
            tool_steps = [step for step in steps if tool in step.get('name', '')]
            assert len(tool_steps) > 0, f"Should run {tool} security scanner"
            
    def test_terraform_workflow(self):
        """TDD: Test Terraform workflow configuration"""
        # Arrange
        terraform_workflow_path = self.github_dir / "terraform.yml"
        
        # Act
        with open(terraform_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert workflow_data['name'] == 'Terraform Infrastructure', "Should have correct name"
        
        required_jobs = ['terraform-validate', 'terraform-plan', 'terraform-apply']
        for job in required_jobs:
            assert job in workflow_data['jobs'], f"Should have {job} job"
            
    def test_security_scan_workflow(self):
        """TDD: Test security scan workflow configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert workflow_data['name'] == 'Security Scanning', "Should have correct name"
        
        required_jobs = [
            'dependency-scan',
            'code-scan', 
            'container-scan',
            'secrets-scan',
            'license-scan'
        ]
        
        for job in required_jobs:
            assert job in workflow_data['jobs'], f"Should have {job} job"
            
    def test_gitops_workflow(self):
        """TDD: Test GitOps workflow configuration"""
        # Arrange
        gitops_workflow_path = self.github_dir / "gitops.yml"
        
        # Act
        with open(gitops_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert workflow_data['name'] == 'GitOps Deployment', "Should have correct name"
        
        required_jobs = ['update-gitops', 'deploy-staging', 'deploy-production']
        for job in required_jobs:
            assert job in workflow_data['jobs'], f"Should have {job} job"
            
    def test_workflow_dependencies(self):
        """TDD: Test workflow job dependencies"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        build_job = workflow_data['jobs']['build']
        assert 'needs' in build_job, "Build job should have dependencies"
        
        needs = build_job['needs']
        assert 'test' in needs, "Build should depend on test"
        assert 'lint' in needs, "Build should depend on lint"
        assert 'security' in needs, "Build should depend on security"
        
    def test_workflow_artifacts(self):
        """TDD: Test workflow artifact handling"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        test_job = workflow_data['jobs']['test']
        steps = test_job['steps']
        
        # Check for artifact upload steps
        upload_steps = [step for step in steps if 'upload' in step.get('name', '').lower()]
        assert len(upload_steps) > 0, "Should have artifact upload steps"
        
    def test_workflow_environment_specific_deployment(self):
        """TDD: Test environment-specific deployment workflows"""
        # Arrange
        ci_workflow_path = self.github_dir / "ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        deploy_staging = workflow_data['jobs']['deploy-staging']
        deploy_production = workflow_data['jobs']['deploy-production']
        
        # Check conditional deployment
        assert 'if' in deploy_staging, "Staging deployment should be conditional"
        assert 'if' in deploy_production, "Production deployment should be conditional"
        
    def test_workflow_error_handling(self):
        """TDD: Test workflow error handling and recovery"""
        # Arrange
        gitops_workflow_path = self.github_dir / "gitops.yml"
        
        # Act
        with open(gitops_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert 'rollback' in workflow_data['jobs'], "Should have rollback job"
        
        rollback_job = workflow_data['jobs']['rollback']
        assert 'if' in rollback_job, "Rollback should be conditional on failure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
