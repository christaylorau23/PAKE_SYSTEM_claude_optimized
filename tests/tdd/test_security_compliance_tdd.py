"""
TDD Security Compliance Tests
Test-Driven Development for security scanning and compliance workflows
"""

import pytest
import yaml
import json
import os
from pathlib import Path


class TestSecurityComplianceTDD:
    """Test-Driven Development for security components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.github_dir = self.project_root / ".github" / "workflows"
        self.service_template_dir = self.project_root / "pkgs" / "service-template"
        self.k8s_dir = self.project_root / "k8s"
        
    def test_security_scan_workflow_structure(self):
        """TDD: Test security scan workflow has proper structure"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert workflow_data['name'] == 'Security Scanning', "Should have correct workflow name"
        assert 'jobs' in workflow_data, "Should have jobs section"
        
        required_jobs = [
            'dependency-scan',
            'code-scan',
            'container-scan', 
            'secrets-scan',
            'license-scan',
            'security-summary'
        ]
        
        for job in required_jobs:
            assert job in workflow_data['jobs'], f"Should have {job} job"
            
    def test_security_scan_triggers(self):
        """TDD: Test security scan workflow triggers"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert 'on' in workflow_data, "Should have trigger configuration"
        triggers = workflow_data['on']
        
        assert 'push' in triggers, "Should trigger on push"
        assert 'pull_request' in triggers, "Should trigger on pull request"
        assert 'schedule' in triggers, "Should have scheduled runs"
        
        # Check schedule configuration
        schedule = triggers['schedule']
        assert len(schedule) > 0, "Should have scheduled runs"
        assert 'cron:' in str(schedule), "Should use cron schedule"
        
    def test_dependency_scan_job(self):
        """TDD: Test dependency scan job configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        dep_scan_job = workflow_data['jobs']['dependency-scan']
        
        assert dep_scan_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for Poetry installation
        steps = dep_scan_job['steps']
        poetry_steps = [step for step in steps if 'Install Poetry' in step.get('name', '')]
        assert len(poetry_steps) > 0, "Should install Poetry"
        
        # Check for Safety tool
        safety_steps = [step for step in steps if 'Safety' in step.get('name', '')]
        assert len(safety_steps) > 0, "Should run Safety check"
        
    def test_code_scan_job(self):
        """TDD: Test code scan job configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        code_scan_job = workflow_data['jobs']['code-scan']
        
        assert code_scan_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for security tools
        steps = code_scan_job['steps']
        security_tools = ['Bandit', 'Semgrep']
        
        for tool in security_tools:
            tool_steps = [step for step in steps if tool in step.get('name', '')]
            assert len(tool_steps) > 0, f"Should run {tool} scanner"
            
    def test_container_scan_job(self):
        """TDD: Test container scan job configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        container_scan_job = workflow_data['jobs']['container-scan']
        
        assert container_scan_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for Docker setup
        steps = container_scan_job['steps']
        docker_steps = [step for step in steps if 'Docker' in step.get('name', '')]
        assert len(docker_steps) > 0, "Should setup Docker"
        
        # Check for Trivy scanner
        trivy_steps = [step for step in steps if 'Trivy' in step.get('name', '')]
        assert len(trivy_steps) > 0, "Should run Trivy scanner"
        
    def test_secrets_scan_job(self):
        """TDD: Test secrets scan job configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        secrets_scan_job = workflow_data['jobs']['secrets-scan']
        
        assert secrets_scan_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for secrets detection tools
        steps = secrets_scan_job['steps']
        secrets_tools = ['TruffleHog', 'GitLeaks']
        
        for tool in secrets_tools:
            tool_steps = [step for step in steps if tool in step.get('name', '')]
            assert len(tool_steps) > 0, f"Should run {tool} scanner"
            
    def test_license_scan_job(self):
        """TDD: Test license scan job configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        license_scan_job = workflow_data['jobs']['license-scan']
        
        assert license_scan_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        
        # Check for license scanning
        steps = license_scan_job['steps']
        license_steps = [step for step in steps if 'license' in step.get('name', '').lower()]
        assert len(license_steps) > 0, "Should run license scan"
        
    def test_security_summary_job(self):
        """TDD: Test security summary job configuration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        summary_job = workflow_data['jobs']['security-summary']
        
        assert summary_job['runs-on'] == 'ubuntu-latest', "Should run on Ubuntu"
        assert 'needs' in summary_job, "Should depend on other security jobs"
        assert 'if: always()' in str(summary_job), "Should run even if other jobs fail"
        
    def test_precommit_security_hooks(self):
        """TDD: Test pre-commit security hooks"""
        # Arrange
        precommit_path = self.service_template_dir / ".pre-commit-config.yaml"
        
        # Act
        with open(precommit_path, 'r') as f:
            content = f.read()
        
        # Assert
        security_hooks = ['bandit', 'safety']
        
        for hook in security_hooks:
            assert hook in content, f"Should configure {hook} security hook"
            
    def test_dockerfile_security_features(self):
        """TDD: Test Dockerfile security features"""
        # Arrange
        dockerfile_path = self.service_template_dir / "Dockerfile"
        
        # Act
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Assert
        security_features = [
            'USER pake',
            'rm -rf /var/lib/apt/lists/*',
            'readOnlyRootFilesystem',
            'runAsNonRoot'
        ]
        
        for feature in security_features:
            assert feature in content, f"Dockerfile should have {feature} security feature"
            
    def test_kubernetes_security_context(self):
        """TDD: Test Kubernetes security context"""
        # Arrange
        production_values_path = self.k8s_dir / "helm" / "pake-system" / "values-production.yaml"
        
        # Act
        with open(production_values_path, 'r') as f:
            values_data = yaml.safe_load(f)
        
        # Assert
        assert 'podSecurityContext' in values_data, "Should have pod security context"
        assert 'securityContext' in values_data, "Should have container security context"
        
        pod_security = values_data['podSecurityContext']
        assert pod_security['runAsNonRoot'] == True, "Should run as non-root"
        assert pod_security['runAsUser'] == 1000, "Should run as user 1000"
        
        security_context = values_data['securityContext']
        assert security_context['allowPrivilegeEscalation'] == False, "Should not allow privilege escalation"
        assert security_context['readOnlyRootFilesystem'] == True, "Should have read-only root filesystem"
        
    def test_kubernetes_network_policies(self):
        """TDD: Test Kubernetes network policies"""
        # Arrange
        production_values_path = self.k8s_dir / "helm" / "pake-system" / "values-production.yaml"
        
        # Act
        with open(production_values_path, 'r') as f:
            values_data = yaml.safe_load(f)
        
        # Assert
        assert 'networkPolicy' in values_data, "Should have network policies"
        
        network_policy = values_data['networkPolicy']
        assert network_policy['enabled'] == True, "Should enable network policies"
        assert 'ingress' in network_policy, "Should have ingress rules"
        
    def test_security_workflow_permissions(self):
        """TDD: Test security workflow permissions"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        assert 'permissions' in workflow_data, "Should define permissions"
        
        permissions = workflow_data['permissions']
        assert permissions['contents'] == 'read', "Should have read access to contents"
        assert permissions['security-events'] == 'write', "Should have write access to security events"
        
    def test_security_artifact_handling(self):
        """TDD: Test security artifact handling"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        # Check for artifact upload steps
        for job_name, job_config in workflow_data['jobs'].items():
            if job_name != 'security-summary':
                steps = job_config['steps']
                upload_steps = [step for step in steps if 'upload' in step.get('name', '').lower()]
                assert len(upload_steps) > 0, f"{job_name} should upload artifacts"
                
    def test_security_scan_comprehensive_coverage(self):
        """TDD: Test security scan comprehensive coverage"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            content = f.read()
        
        # Assert
        # Check for comprehensive security scanning
        security_areas = [
            'dependency-scan',
            'code-scan',
            'container-scan',
            'secrets-scan',
            'license-scan'
        ]
        
        for area in security_areas:
            assert area in content, f"Should cover {area} security area"
            
    def test_security_compliance_standards(self):
        """TDD: Test security compliance standards"""
        # Arrange
        security_files = [
            self.github_dir / "security-scan.yml",
            self.service_template_dir / ".pre-commit-config.yaml",
            self.service_template_dir / "Dockerfile",
            self.k8s_dir / "helm" / "pake-system" / "values-production.yaml"
        ]
        
        # Act & Assert
        for security_file in security_files:
            assert security_file.exists(), f"Should have {security_file.name} for security compliance"
            
            with open(security_file, 'r') as f:
                content = f.read()
            
            # Check for security best practices
            if 'Dockerfile' in str(security_file):
                assert 'USER pake' in content, "Should use non-root user"
                assert 'rm -rf /var/lib/apt/lists/*' in content, "Should clean package cache"
            elif 'pre-commit' in str(security_file):
                assert 'bandit' in content, "Should have security linting"
            elif 'values-production' in str(security_file):
                assert 'securityContext' in content, "Should have security context"
                
    def test_security_monitoring_integration(self):
        """TDD: Test security monitoring integration"""
        # Arrange
        security_workflow_path = self.github_dir / "security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            content = f.read()
        
        # Assert
        # Check for security monitoring features
        monitoring_features = [
            'security-summary',
            'Upload security reports',
            'Generate security summary'
        ]
        
        for feature in monitoring_features:
            assert feature in content, f"Should have {feature} for security monitoring"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
