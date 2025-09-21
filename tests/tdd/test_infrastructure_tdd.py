"""
TDD Infrastructure Tests
Test-Driven Development for Infrastructure as Code validation
"""

import pytest
import yaml
import json
import os
from pathlib import Path


class TestInfrastructureTDD:
    """Test-Driven Development for Infrastructure components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.infra_dir = self.project_root / "infra" / "terraform"
        self.k8s_dir = self.project_root / "k8s"
        
    def test_terraform_configuration_structure(self):
        """TDD: Test Terraform configuration has proper structure"""
        # Arrange
        terraform_files = [
            "main.tf",
            "variables.tf", 
            "outputs.tf",
            "terraform.tfvars.example"
        ]
        
        # Act & Assert
        for file_name in terraform_files:
            file_path = self.infra_dir / file_name
            assert file_path.exists(), f"Terraform file {file_name} should exist"
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            assert len(content) > 100, f"Terraform file {file_name} should have substantial content"
            
    def test_terraform_provider_configuration(self):
        """TDD: Test Terraform providers are properly configured"""
        # Arrange
        main_tf_path = self.infra_dir / "main.tf"
        
        # Act
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'required_providers' in content, "Should have required_providers block"
        assert 'aws' in content, "Should configure AWS provider"
        assert 'kubernetes' in content, "Should configure Kubernetes provider"
        assert 'helm' in content, "Should configure Helm provider"
        
    def test_terraform_resource_definitions(self):
        """TDD: Test Terraform resources are properly defined"""
        # Arrange
        main_tf_path = self.infra_dir / "main.tf"
        
        # Act
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        # Assert - Check for key infrastructure components
        required_resources = [
            'module "vpc"',
            'module "eks"', 
            'module "rds"',
            'aws_elasticache_replication_group',
            'aws_security_group'
        ]
        
        for resource in required_resources:
            assert resource in content, f"Should define {resource}"
            
    def test_terraform_variables_validation(self):
        """TDD: Test Terraform variables have proper validation"""
        # Arrange
        variables_tf_path = self.infra_dir / "variables.tf"
        
        # Act
        with open(variables_tf_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'variable "aws_region"' in content, "Should define aws_region variable"
        assert 'variable "environment"' in content, "Should define environment variable"
        assert 'validation' in content, "Should have validation blocks"
        assert 'variable "database_REDACTED_SECRET"' in content, "Should define database_REDACTED_SECRET variable"
        
    def test_terraform_outputs_completeness(self):
        """TDD: Test Terraform outputs provide all necessary information"""
        # Arrange
        outputs_tf_path = self.infra_dir / "outputs.tf"
        
        # Act
        with open(outputs_tf_path, 'r') as f:
            content = f.read()
        
        # Assert
        required_outputs = [
            'output "vpc_id"',
            'output "cluster_endpoint"',
            'output "rds_endpoint"',
            'output "redis_endpoint"',
            'output "database_url"'
        ]
        
        for output in required_outputs:
            assert output in content, f"Should define {output}"
            
    def test_terraform_backend_configuration(self):
        """TDD: Test Terraform backend is properly configured"""
        # Arrange
        main_tf_path = self.infra_dir / "main.tf"
        
        # Act
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'backend "s3"' in content, "Should configure S3 backend"
        assert 'terraform.tfstate' in content, "Should specify state file location"
        
    def test_terraform_environment_configuration(self):
        """TDD: Test environment-specific configurations exist"""
        # Arrange
        tfvars_example = self.infra_dir / "terraform.tfvars.example"
        
        # Act
        with open(tfvars_example, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'aws_region' in content, "Should define aws_region"
        assert 'environment' in content, "Should define environment"
        assert 'project_name' in content, "Should define project_name"
        assert 'database_REDACTED_SECRET' in content, "Should define database_REDACTED_SECRET"
        
    def test_kubernetes_manifests_structure(self):
        """TDD: Test Kubernetes manifests have proper structure"""
        # Arrange
        helm_chart_dir = self.k8s_dir / "helm" / "pake-system"
        
        # Act & Assert
        required_files = [
            "Chart.yaml",
            "values.yaml",
            "values-staging.yaml", 
            "values-production.yaml"
        ]
        
        for file_name in required_files:
            file_path = helm_chart_dir / file_name
            assert file_path.exists(), f"Helm chart file {file_name} should exist"
            
    def test_helm_chart_metadata(self):
        """TDD: Test Helm chart has proper metadata"""
        # Arrange
        chart_yaml_path = self.k8s_dir / "helm" / "pake-system" / "Chart.yaml"
        
        # Act
        with open(chart_yaml_path, 'r') as f:
            chart_data = yaml.safe_load(f)
        
        # Assert
        assert chart_data['apiVersion'] == 'v2', "Should use Chart API version 2"
        assert chart_data['name'] == 'pake-system', "Should have correct chart name"
        assert 'version' in chart_data, "Should have version"
        assert 'appVersion' in chart_data, "Should have app version"
        assert 'dependencies' in chart_data, "Should have dependencies"
        
    def test_helm_values_consistency(self):
        """TDD: Test Helm values files are consistent"""
        # Arrange
        helm_chart_dir = self.k8s_dir / "helm" / "pake-system"
        values_files = [
            "values.yaml",
            "values-staging.yaml",
            "values-production.yaml"
        ]
        
        # Act & Assert
        for values_file in values_files:
            file_path = helm_chart_dir / values_file
            
            with open(file_path, 'r') as f:
                values_data = yaml.safe_load(f)
            
            # Check for required sections
            required_sections = ['image', 'service', 'resources', 'autoscaling']
            for section in required_sections:
                assert section in values_data, f"{values_file} should have {section} section"
                
    def test_argocd_application_manifests(self):
        """TDD: Test ArgoCD application manifests are properly configured"""
        # Arrange
        argocd_dir = self.k8s_dir / "argocd" / "applications"
        
        # Act & Assert
        app_files = [
            "pake-system-staging.yaml",
            "pake-system-production.yaml"
        ]
        
        for app_file in app_files:
            file_path = argocd_dir / app_file
            assert file_path.exists(), f"ArgoCD app {app_file} should exist"
            
            with open(file_path, 'r') as f:
                app_data = yaml.safe_load(f)
            
            assert app_data['kind'] == 'Application', "Should be ArgoCD Application"
            assert 'spec' in app_data, "Should have spec section"
            assert 'source' in app_data['spec'], "Should have source configuration"
            assert 'destination' in app_data['spec'], "Should have destination configuration"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
