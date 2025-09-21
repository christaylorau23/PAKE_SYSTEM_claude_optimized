"""
TDD Kubernetes Deployment Tests
Test-Driven Development for Helm charts and deployment workflows
"""

import pytest
import yaml
import json
import os
from pathlib import Path


class TestKubernetesDeploymentTDD:
    """Test-Driven Development for Kubernetes components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.k8s_dir = self.project_root / "k8s"
        self.helm_dir = self.k8s_dir / "helm" / "pake-system"
        self.argocd_dir = self.k8s_dir / "argocd" / "applications"
        
    def test_helm_chart_structure(self):
        """TDD: Test Helm chart has proper structure"""
        # Arrange
        required_files = [
            "Chart.yaml",
            "values.yaml",
            "values-staging.yaml",
            "values-production.yaml"
        ]
        
        # Act & Assert
        for file_name in required_files:
            file_path = self.helm_dir / file_name
            assert file_path.exists(), f"Helm chart should have {file_name}"
            
    def test_helm_chart_metadata(self):
        """TDD: Test Helm chart metadata is complete"""
        # Arrange
        chart_yaml_path = self.helm_dir / "Chart.yaml"
        
        # Act
        with open(chart_yaml_path, 'r') as f:
            chart_data = yaml.safe_load(f)
        
        # Assert
        assert chart_data['apiVersion'] == 'v2', "Should use Chart API version 2"
        assert chart_data['name'] == 'pake-system', "Should have correct chart name"
        assert 'version' in chart_data, "Should have version"
        assert 'appVersion' in chart_data, "Should have app version"
        assert 'description' in chart_data, "Should have description"
        assert 'dependencies' in chart_data, "Should have dependencies"
        
    def test_helm_chart_dependencies(self):
        """TDD: Test Helm chart dependencies are properly configured"""
        # Arrange
        chart_yaml_path = self.helm_dir / "Chart.yaml"
        
        # Act
        with open(chart_yaml_path, 'r') as f:
            chart_data = yaml.safe_load(f)
        
        # Assert
        dependencies = chart_data['dependencies']
        
        required_deps = ['postgresql', 'redis', 'prometheus', 'grafana']
        for dep in required_deps:
            dep_found = any(d['name'] == dep for d in dependencies)
            assert dep_found, f"Should have {dep} dependency"
            
    def test_helm_values_structure(self):
        """TDD: Test Helm values files have proper structure"""
        # Arrange
        values_files = [
            "values.yaml",
            "values-staging.yaml", 
            "values-production.yaml"
        ]
        
        # Act & Assert
        for values_file in values_files:
            file_path = self.helm_dir / values_file
            
            with open(file_path, 'r') as f:
                values_data = yaml.safe_load(f)
            
            # Check required sections
            required_sections = [
                'image', 'service', 'resources', 'autoscaling',
                'postgresql', 'redis', 'monitoring'
            ]
            
            for section in required_sections:
                assert section in values_data, f"{values_file} should have {section} section"
                
    def test_helm_values_environment_specific(self):
        """TDD: Test Helm values are environment-specific"""
        # Arrange
        staging_values_path = self.helm_dir / "values-staging.yaml"
        production_values_path = self.helm_dir / "values-production.yaml"
        
        # Act
        with open(staging_values_path, 'r') as f:
            staging_data = yaml.safe_load(f)
            
        with open(production_values_path, 'r') as f:
            production_data = yaml.safe_load(f)
        
        # Assert
        # Staging should have debug enabled
        staging_env = staging_data.get('env', [])
        staging_debug = any(env.get('name') == 'DEBUG' and env.get('value') == 'true' 
                           for env in staging_env)
        assert staging_debug, "Staging should have DEBUG enabled"
        
        # Production should have debug disabled
        production_env = production_data.get('env', [])
        production_debug = any(env.get('name') == 'DEBUG' and env.get('value') == 'false' 
                              for env in production_env)
        assert production_debug, "Production should have DEBUG disabled"
        
        # Production should have higher resource limits
        staging_resources = staging_data.get('resources', {})
        production_resources = production_data.get('resources', {})
        
        assert production_resources.get('limits', {}).get('cpu') > staging_resources.get('limits', {}).get('cpu'), \
            "Production should have higher CPU limits"
            
    def test_helm_templates_structure(self):
        """TDD: Test Helm templates have proper structure"""
        # Arrange
        templates_dir = self.helm_dir / "templates"
        
        # Act & Assert
        assert templates_dir.exists(), "Should have templates directory"
        
        required_templates = [
            "deployment.yaml",
            "service.yaml",
            "configmap.yaml",
            "_helpers.tpl"
        ]
        
        for template in required_templates:
            template_path = templates_dir / template
            assert template_path.exists(), f"Should have {template} template"
            
    def test_helm_deployment_template(self):
        """TDD: Test Helm deployment template configuration"""
        # Arrange
        deployment_template_path = self.helm_dir / "templates" / "deployment.yaml"
        
        # Act
        with open(deployment_template_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'apiVersion: apps/v1' in content, "Should use apps/v1 API"
        assert 'kind: Deployment' in content, "Should be Deployment resource"
        assert '{{ include "pake-system.fullname" . }}' in content, "Should use helper function"
        assert 'securityContext' in content, "Should have security context"
        assert 'livenessProbe' in content, "Should have liveness probe"
        assert 'readinessProbe' in content, "Should have readiness probe"
        
    def test_helm_service_template(self):
        """TDD: Test Helm service template configuration"""
        # Arrange
        service_template_path = self.helm_dir / "templates" / "service.yaml"
        
        # Act
        with open(service_template_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'apiVersion: v1' in content, "Should use v1 API"
        assert 'kind: Service' in content, "Should be Service resource"
        assert 'type: {{ .Values.service.type }}' in content, "Should use service type from values"
        assert 'port: {{ .Values.service.port }}' in content, "Should use service port from values"
        
    def test_helm_helpers_template(self):
        """TDD: Test Helm helpers template configuration"""
        # Arrange
        helpers_template_path = self.helm_dir / "templates" / "_helpers.tpl"
        
        # Act
        with open(helpers_template_path, 'r') as f:
            content = f.read()
        
        # Assert
        required_helpers = [
            'pake-system.name',
            'pake-system.fullname',
            'pake-system.labels',
            'pake-system.selectorLabels'
        ]
        
        for helper in required_helpers:
            assert f'define "{helper}"' in content, f"Should define {helper} helper"
            
    def test_argocd_applications_structure(self):
        """TDD: Test ArgoCD applications have proper structure"""
        # Arrange
        required_apps = [
            "pake-system-staging.yaml",
            "pake-system-production.yaml"
        ]
        
        # Act & Assert
        for app_file in required_apps:
            app_path = self.argocd_dir / app_file
            assert app_path.exists(), f"Should have {app_file} ArgoCD application"
            
    def test_argocd_application_configuration(self):
        """TDD: Test ArgoCD application configuration"""
        # Arrange
        staging_app_path = self.argocd_dir / "pake-system-staging.yaml"
        
        # Act
        with open(staging_app_path, 'r') as f:
            app_data = yaml.safe_load(f)
        
        # Assert
        assert app_data['kind'] == 'Application', "Should be ArgoCD Application"
        assert app_data['metadata']['name'] == 'pake-system-staging', "Should have correct name"
        
        spec = app_data['spec']
        assert 'source' in spec, "Should have source configuration"
        assert 'destination' in spec, "Should have destination configuration"
        assert 'syncPolicy' in spec, "Should have sync policy"
        
        # Check source configuration
        source = spec['source']
        assert source['repoURL'] == 'https://github.com/your-org/pake-system', "Should have correct repo URL"
        assert source['targetRevision'] == 'develop', "Should target develop branch"
        assert source['path'] == 'k8s/helm/pake-system', "Should point to Helm chart"
        
    def test_argocd_sync_policy(self):
        """TDD: Test ArgoCD sync policy configuration"""
        # Arrange
        staging_app_path = self.argocd_dir / "pake-system-staging.yaml"
        
        # Act
        with open(staging_app_path, 'r') as f:
            app_data = yaml.safe_load(f)
        
        # Assert
        sync_policy = app_data['spec']['syncPolicy']
        
        assert 'automated' in sync_policy, "Should have automated sync"
        assert sync_policy['automated']['prune'] == True, "Should enable pruning"
        assert sync_policy['automated']['selfHeal'] == True, "Should enable self-healing"
        
        assert 'syncOptions' in sync_policy, "Should have sync options"
        assert 'CreateNamespace=true' in sync_policy['syncOptions'], "Should create namespace"
        
    def test_kubernetes_security_configuration(self):
        """TDD: Test Kubernetes security configuration"""
        # Arrange
        production_values_path = self.helm_dir / "values-production.yaml"
        
        # Act
        with open(production_values_path, 'r') as f:
            values_data = yaml.safe_load(f)
        
        # Assert
        assert 'podSecurityContext' in values_data, "Should have pod security context"
        assert 'securityContext' in values_data, "Should have container security context"
        assert 'networkPolicy' in values_data, "Should have network policies"
        
        # Check security context values
        pod_security = values_data['podSecurityContext']
        assert pod_security['runAsNonRoot'] == True, "Should run as non-root"
        assert pod_security['runAsUser'] == 1000, "Should run as user 1000"
        
        security_context = values_data['securityContext']
        assert security_context['allowPrivilegeEscalation'] == False, "Should not allow privilege escalation"
        assert security_context['readOnlyRootFilesystem'] == True, "Should have read-only root filesystem"
        
    def test_kubernetes_monitoring_integration(self):
        """TDD: Test Kubernetes monitoring integration"""
        # Arrange
        production_values_path = self.helm_dir / "values-production.yaml"
        
        # Act
        with open(production_values_path, 'r') as f:
            values_data = yaml.safe_load(f)
        
        # Assert
        monitoring = values_data.get('monitoring', {})
        assert monitoring.get('enabled') == True, "Should enable monitoring"
        
        prometheus = monitoring.get('prometheus', {})
        assert prometheus.get('enabled') == True, "Should enable Prometheus"
        
        grafana = monitoring.get('grafana', {})
        assert grafana.get('enabled') == True, "Should enable Grafana"
        
    def test_kubernetes_autoscaling_configuration(self):
        """TDD: Test Kubernetes autoscaling configuration"""
        # Arrange
        production_values_path = self.helm_dir / "values-production.yaml"
        
        # Act
        with open(production_values_path, 'r') as f:
            values_data = yaml.safe_load(f)
        
        # Assert
        autoscaling = values_data.get('autoscaling', {})
        assert autoscaling.get('enabled') == True, "Should enable autoscaling"
        assert autoscaling.get('minReplicas') == 3, "Should have minimum 3 replicas"
        assert autoscaling.get('maxReplicas') == 20, "Should have maximum 20 replicas"
        
    def test_kubernetes_health_checks(self):
        """TDD: Test Kubernetes health checks configuration"""
        # Arrange
        production_values_path = self.helm_dir / "values-production.yaml"
        
        # Act
        with open(production_values_path, 'r') as f:
            values_data = yaml.safe_load(f)
        
        # Assert
        assert 'livenessProbe' in values_data, "Should have liveness probe"
        assert 'readinessProbe' in values_data, "Should have readiness probe"
        
        liveness = values_data['livenessProbe']
        assert liveness.get('enabled') == True, "Should enable liveness probe"
        assert liveness.get('initialDelaySeconds') == 60, "Should have appropriate initial delay"
        
        readiness = values_data['readinessProbe']
        assert readiness.get('enabled') == True, "Should enable readiness probe"
        assert readiness.get('initialDelaySeconds') == 10, "Should have appropriate initial delay"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
