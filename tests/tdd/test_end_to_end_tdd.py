"""
TDD End-to-End Integration Tests
Test-Driven Development for complete system integration and workflows
"""

import pytest
import yaml
import json
import os
from pathlib import Path


class TestEndToEndIntegrationTDD:
    """Test-Driven Development for end-to-end system integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        
    def test_complete_workflow_integration(self):
        """TDD: Test complete workflow integration from code to production"""
        # Arrange
        workflow_files = [
            ".github/workflows/ci.yml",
            ".github/workflows/terraform.yml", 
            ".github/workflows/security-scan.yml",
            ".github/workflows/gitops.yml"
        ]
        
        # Act & Assert
        for workflow_file in workflow_files:
            workflow_path = self.project_root / workflow_file
            assert workflow_path.exists(), f"Should have {workflow_file} workflow"
            
            with open(workflow_path, 'r') as f:
                workflow_data = yaml.safe_load(f)
            
            assert 'jobs' in workflow_data, f"{workflow_file} should have jobs"
            assert len(workflow_data['jobs']) > 0, f"{workflow_file} should have at least one job"
            
    def test_infrastructure_to_application_pipeline(self):
        """TDD: Test infrastructure to application deployment pipeline"""
        # Arrange
        infra_files = [
            "infra/terraform/main.tf",
            "infra/terraform/variables.tf",
            "infra/terraform/outputs.tf"
        ]
        
        app_files = [
            "k8s/helm/pake-system/Chart.yaml",
            "k8s/helm/pake-system/values.yaml",
            "k8s/argocd/applications/pake-system-staging.yaml"
        ]
        
        # Act & Assert
        for file_group, file_list in [("Infrastructure", infra_files), ("Application", app_files)]:
            for file_path in file_list:
                full_path = self.project_root / file_path
                assert full_path.exists(), f"Should have {file_group} file {file_path}"
                
    def test_service_template_to_production_pipeline(self):
        """TDD: Test service template to production deployment pipeline"""
        # Arrange
        template_files = [
            "pkgs/service-template/pyproject.toml",
            "pkgs/service-template/Dockerfile",
            "pkgs/service-template/app/main.py"
        ]
        
        production_files = [
            "k8s/helm/pake-system/values-production.yaml",
            "k8s/argocd/applications/pake-system-production.yaml"
        ]
        
        # Act & Assert
        for file_group, file_list in [("Template", template_files), ("Production", production_files)]:
            for file_path in file_list:
                full_path = self.project_root / file_path
                assert full_path.exists(), f"Should have {file_group} file {file_path}"
                
    def test_monitoring_stack_integration(self):
        """TDD: Test monitoring stack integration"""
        # Arrange
        monitoring_files = [
            "monitoring/prometheus/prometheus.yml",
            "monitoring/prometheus/rules/pake-system.yml",
            "monitoring/grafana/dashboards/pake-system-overview.json",
            "monitoring/jaeger/jaeger-config.yaml"
        ]
        
        # Act & Assert
        for file_path in monitoring_files:
            full_path = self.project_root / file_path
            assert full_path.exists(), f"Should have monitoring file {file_path}"
            
            # Check file has substantial content
            assert full_path.stat().st_size > 500, f"{file_path} should have substantial content"
            
    def test_security_integration_completeness(self):
        """TDD: Test security integration completeness"""
        # Arrange
        security_components = [
            ".github/workflows/security-scan.yml",
            "pkgs/service-template/.pre-commit-config.yaml",
            "k8s/helm/pake-system/values-production.yaml"
        ]
        
        # Act & Assert
        for component in security_components:
            component_path = self.project_root / component
            assert component_path.exists(), f"Should have security component {component}"
            
    def test_documentation_integration(self):
        """TDD: Test documentation integration"""
        # Arrange
        doc_files = [
            "docs/WORLD_CLASS_ENGINEERING_GUIDE.md",
            "README.md",
            "adrs/001-api-gateway-selection.md",
            "adrs/002-service-mesh-selection.md",
            "adrs/003-database-selection.md",
            "adrs/004-monorepo-strategy.md"
        ]
        
        # Act & Assert
        for doc_file in doc_files:
            doc_path = self.project_root / doc_file
            assert doc_path.exists(), f"Should have documentation {doc_file}"
            
            # Check documentation is comprehensive
            with open(doc_path, 'r') as f:
                content = f.read()
            
            assert len(content) > 1000, f"{doc_file} should be comprehensive"
            
    def test_environment_configuration_consistency(self):
        """TDD: Test environment configuration consistency"""
        # Arrange
        env_configs = [
            "k8s/helm/pake-system/values-staging.yaml",
            "k8s/helm/pake-system/values-production.yaml"
        ]
        
        # Act & Assert
        for config_file in env_configs:
            config_path = self.project_root / config_file
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Check required sections exist
            required_sections = ['image', 'service', 'resources', 'autoscaling', 'monitoring']
            for section in required_sections:
                assert section in config_data, f"{config_file} should have {section} section"
                
    def test_ci_cd_pipeline_dependencies(self):
        """TDD: Test CI/CD pipeline job dependencies"""
        # Arrange
        ci_workflow_path = self.project_root / ".github/workflows/ci.yml"
        
        # Act
        with open(ci_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        jobs = workflow_data['jobs']
        
        # Check build job dependencies
        if 'build' in jobs:
            build_job = jobs['build']
            assert 'needs' in build_job, "Build job should have dependencies"
            
            needs = build_job['needs']
            assert 'test' in needs, "Build should depend on test"
            assert 'lint' in needs, "Build should depend on lint"
            assert 'security' in needs, "Build should depend on security"
            
    def test_gitops_deployment_workflow(self):
        """TDD: Test GitOps deployment workflow"""
        # Arrange
        gitops_workflow_path = self.project_root / ".github/workflows/gitops.yml"
        
        # Act
        with open(gitops_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        jobs = workflow_data['jobs']
        
        # Check GitOps workflow structure
        required_jobs = ['update-gitops', 'deploy-staging', 'deploy-production']
        for job in required_jobs:
            assert job in jobs, f"GitOps workflow should have {job} job"
            
        # Check deployment dependencies
        if 'deploy-staging' in jobs:
            staging_job = jobs['deploy-staging']
            assert 'needs' in staging_job, "Staging deployment should have dependencies"
            
    def test_monitoring_alerting_integration(self):
        """TDD: Test monitoring and alerting integration"""
        # Arrange
        prometheus_config_path = self.project_root / "monitoring/prometheus/prometheus.yml"
        rules_path = self.project_root / "monitoring/prometheus/rules/pake-system.yml"
        
        # Act
        with open(prometheus_config_path, 'r') as f:
            prometheus_content = f.read()
            
        with open(rules_path, 'r') as f:
            rules_content = f.read()
        
        # Assert
        # Check Prometheus has alerting configuration
        assert 'alerting:' in prometheus_content, "Prometheus should have alerting config"
        assert 'rule_files:' in prometheus_content, "Prometheus should have rule files"
        
        # Check alerting rules exist
        assert 'groups:' in rules_content, "Should have alerting rule groups"
        assert 'PAKESystemHighErrorRate' in rules_content, "Should have error rate alert"
        
    def test_security_scanning_integration(self):
        """TDD: Test security scanning integration"""
        # Arrange
        security_workflow_path = self.project_root / ".github/workflows/security-scan.yml"
        
        # Act
        with open(security_workflow_path, 'r') as f:
            workflow_data = yaml.safe_load(f)
        
        # Assert
        jobs = workflow_data['jobs']
        
        # Check comprehensive security scanning
        security_jobs = [
            'dependency-scan',
            'code-scan',
            'container-scan',
            'secrets-scan',
            'license-scan'
        ]
        
        for job in security_jobs:
            assert job in jobs, f"Should have {job} security job"
            
    def test_kubernetes_helm_integration(self):
        """TDD: Test Kubernetes Helm chart integration"""
        # Arrange
        helm_chart_path = self.project_root / "k8s/helm/pake-system/Chart.yaml"
        
        # Act
        with open(helm_chart_path, 'r') as f:
            chart_data = yaml.safe_load(f)
        
        # Assert
        assert chart_data['name'] == 'pake-system', "Should have correct chart name"
        assert 'dependencies' in chart_data, "Should have dependencies"
        
        # Check for monitoring dependencies
        dependencies = chart_data['dependencies']
        monitoring_deps = ['prometheus', 'grafana']
        
        for dep in monitoring_deps:
            dep_found = any(d['name'] == dep for d in dependencies)
            assert dep_found, f"Should have {dep} dependency"
            
    def test_argocd_application_integration(self):
        """TDD: Test ArgoCD application integration"""
        # Arrange
        staging_app_path = self.project_root / "k8s/argocd/applications/pake-system-staging.yaml"
        production_app_path = self.project_root / "k8s/argocd/applications/pake-system-production.yaml"
        
        # Act & Assert
        for app_path in [staging_app_path, production_app_path]:
            with open(app_path, 'r') as f:
                app_data = yaml.safe_load(f)
            
            assert app_data['kind'] == 'Application', "Should be ArgoCD Application"
            assert 'spec' in app_data, "Should have spec section"
            
            spec = app_data['spec']
            assert 'source' in spec, "Should have source configuration"
            assert 'destination' in spec, "Should have destination configuration"
            assert 'syncPolicy' in spec, "Should have sync policy"
            
    def test_complete_system_readiness(self):
        """TDD: Test complete system readiness for production"""
        # Arrange
        system_components = {
            "Infrastructure": [
                "infra/terraform/main.tf",
                "infra/terraform/variables.tf",
                "infra/terraform/outputs.tf"
            ],
            "CI/CD": [
                ".github/workflows/ci.yml",
                ".github/workflows/terraform.yml",
                ".github/workflows/security-scan.yml",
                ".github/workflows/gitops.yml"
            ],
            "Services": [
                "pkgs/service-template/pyproject.toml",
                "pkgs/service-template/Dockerfile",
                "pkgs/service-template/app/main.py"
            ],
            "Kubernetes": [
                "k8s/helm/pake-system/Chart.yaml",
                "k8s/helm/pake-system/values.yaml",
                "k8s/helm/pake-system/values-staging.yaml",
                "k8s/helm/pake-system/values-production.yaml"
            ],
            "Monitoring": [
                "monitoring/prometheus/prometheus.yml",
                "monitoring/grafana/dashboards/pake-system-overview.json",
                "monitoring/jaeger/jaeger-config.yaml"
            ],
            "Documentation": [
                "docs/WORLD_CLASS_ENGINEERING_GUIDE.md",
                "README.md",
                "adrs/001-api-gateway-selection.md"
            ]
        }
        
        # Act & Assert
        total_components = 0
        existing_components = 0
        
        for category, components in system_components.items():
            for component in components:
                total_components += 1
                component_path = self.project_root / component
                
                if component_path.exists():
                    existing_components += 1
                    # Check component has substantial content
                    if component_path.stat().st_size > 100:
                        pass  # Component is ready
                    else:
                        print(f"Warning: {component} has minimal content")
                else:
                    print(f"Missing: {component}")
        
        # Calculate readiness percentage
        readiness_percentage = (existing_components / total_components) * 100
        
        assert readiness_percentage >= 95, f"System should be 95%+ ready, currently {readiness_percentage:.1f}%"
        
    def test_workflow_integration_flow(self):
        """TDD: Test workflow integration flow"""
        # Arrange
        workflow_sequence = [
            "ci.yml",           # Code quality and testing
            "security-scan.yml", # Security validation
            "terraform.yml",    # Infrastructure validation
            "gitops.yml"        # Deployment
        ]
        
        # Act & Assert
        for workflow_file in workflow_sequence:
            workflow_path = self.project_root / ".github/workflows" / workflow_file
            
            assert workflow_path.exists(), f"Should have {workflow_file} workflow"
            
            with open(workflow_path, 'r') as f:
                workflow_data = yaml.safe_load(f)
            
            assert 'jobs' in workflow_data, f"{workflow_file} should have jobs"
            assert len(workflow_data['jobs']) > 0, f"{workflow_file} should have at least one job"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
