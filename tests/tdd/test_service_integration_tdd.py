"""
TDD Service Integration Tests
Test-Driven Development for service template and FastAPI functionality
"""

import pytest
import json
import os
import subprocess
from pathlib import Path


class TestServiceIntegrationTDD:
    """Test-Driven Development for service components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.service_template_dir = self.project_root / "pkgs" / "service-template"
        self.src_dir = self.project_root / "src"
        
    def test_service_template_structure(self):
        """TDD: Test service template has proper structure"""
        # Arrange
        required_files = [
            "pyproject.toml",
            "Dockerfile",
            ".pre-commit-config.yaml",
            "README.md"
        ]
        
        # Act & Assert
        for file_name in required_files:
            file_path = self.service_template_dir / file_name
            assert file_path.exists(), f"Service template should have {file_name}"
            
    def test_service_template_pyproject_config(self):
        """TDD: Test service template pyproject.toml configuration"""
        # Arrange
        pyproject_path = self.service_template_dir / "pyproject.toml"
        
        # Act
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert '[tool.poetry]' in content, "Should have Poetry configuration"
        assert 'fastapi' in content, "Should include FastAPI dependency"
        assert 'uvicorn' in content, "Should include Uvicorn dependency"
        assert 'pydantic' in content, "Should include Pydantic dependency"
        assert 'sqlalchemy' in content, "Should include SQLAlchemy dependency"
        assert 'redis' in content, "Should include Redis dependency"
        
        # Check dev dependencies
        assert 'pytest' in content, "Should include pytest for testing"
        assert 'black' in content, "Should include Black for formatting"
        assert 'mypy' in content, "Should include MyPy for type checking"
        assert 'bandit' in content, "Should include Bandit for security"
        
    def test_service_template_dockerfile(self):
        """TDD: Test service template Dockerfile configuration"""
        # Arrange
        dockerfile_path = self.service_template_dir / "Dockerfile"
        
        # Act
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'FROM python:3.12-slim' in content, "Should use Python 3.12 slim base"
        assert 'as builder' in content, "Should have multi-stage build"
        assert 'as production' in content, "Should have production stage"
        assert 'USER pake' in content, "Should use non-root user"
        assert 'HEALTHCHECK' in content, "Should have health check"
        
    def test_service_template_precommit_config(self):
        """TDD: Test service template pre-commit configuration"""
        # Arrange
        precommit_path = self.service_template_dir / ".pre-commit-config.yaml"
        
        # Act
        with open(precommit_path, 'r') as f:
            content = f.read()
        
        # Assert
        required_hooks = ['black', 'isort', 'ruff', 'mypy', 'bandit']
        for hook in required_hooks:
            assert hook in content, f"Should configure {hook} hook"
            
    def test_service_template_app_structure(self):
        """TDD: Test service template app structure"""
        # Arrange
        app_dir = self.service_template_dir / "app"
        
        # Act & Assert
        assert app_dir.exists(), "Should have app directory"
        
        required_files = [
            "main.py",
            "core/config.py"
        ]
        
        for file_name in required_files:
            file_path = app_dir / file_name
            assert file_path.exists(), f"Should have {file_name}"
            
    def test_service_template_main_py(self):
        """TDD: Test service template main.py configuration"""
        # Arrange
        main_py_path = self.service_template_dir / "app" / "main.py"
        
        # Act
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'from fastapi import FastAPI' in content, "Should import FastAPI"
        assert 'def create_app()' in content, "Should have create_app function"
        assert '@app.get("/health")' in content, "Should have health endpoint"
        assert '@app.get("/metrics")' in content, "Should have metrics endpoint"
        assert 'lifespan' in content, "Should have lifespan manager"
        
    def test_service_template_config_py(self):
        """TDD: Test service template config.py configuration"""
        # Arrange
        config_py_path = self.service_template_dir / "app" / "core" / "config.py"
        
        # Act
        with open(config_py_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert 'from pydantic import BaseSettings' in content, "Should use Pydantic settings"
        assert 'class Settings' in content, "Should have Settings class"
        assert 'SECRET_KEY' in content, "Should have SECRET_KEY configuration"
        assert 'DATABASE_URL' in content, "Should have DATABASE_URL configuration"
        assert 'REDIS_URL' in content, "Should have REDIS_URL configuration"
        assert '@validator' in content, "Should have validation methods"
        
    def test_service_template_readme(self):
        """TDD: Test service template README completeness"""
        # Arrange
        readme_path = self.service_template_dir / "README.md"
        
        # Act
        with open(readme_path, 'r') as f:
            content = f.read()
        
        # Assert
        assert len(content) > 5000, "README should be comprehensive"
        
        required_sections = [
            '# PAKE Service Template',
            '## Quick Start',
            '## Project Structure',
            '## Configuration',
            '## Testing Strategy',
            '## Docker Deployment'
        ]
        
        for section in required_sections:
            assert section in content, f"README should have {section} section"
            
    def test_existing_services_structure(self):
        """TDD: Test existing services have proper structure"""
        # Arrange
        services_dir = self.src_dir
        
        # Act & Assert
        assert services_dir.exists(), "Should have src directory"
        
        # Check for key service directories
        service_dirs = [d for d in services_dir.iterdir() if d.is_dir()]
        assert len(service_dirs) > 0, "Should have service directories"
        
    def test_service_template_poetry_validation(self):
        """TDD: Test service template Poetry configuration validation"""
        # Arrange
        pyproject_path = self.service_template_dir / "pyproject.toml"
        
        # Act
        try:
            # Try to validate Poetry configuration
            result = subprocess.run(
                ['python3', '-c', 'import tomllib; tomllib.load(open("pyproject.toml", "rb"))'],
                cwd=self.service_template_dir,
                capture_output=True,
                text=True
            )
            
            # Assert
            assert result.returncode == 0, f"Poetry config should be valid: {result.stderr}"
            
        except FileNotFoundError:
            # Fallback to basic file validation
            with open(pyproject_path, 'r') as f:
                content = f.read()
            
            assert '[tool.poetry]' in content, "Should have Poetry section"
            assert 'name =' in content, "Should have package name"
            assert 'version =' in content, "Should have version"
            
    def test_service_template_dockerfile_validation(self):
        """TDD: Test service template Dockerfile validation"""
        # Arrange
        dockerfile_path = self.service_template_dir / "Dockerfile"
        
        # Act
        with open(dockerfile_path, 'r') as f:
            lines = f.readlines()
        
        # Assert
        assert len(lines) > 20, "Dockerfile should have substantial content"
        
        # Check for proper structure
        has_from = any('FROM' in line for line in lines)
        assert has_from, "Should have FROM instruction"
        
        has_workdir = any('WORKDIR' in line for line in lines)
        assert has_workdir, "Should have WORKDIR instruction"
        
        has_cmd = any('CMD' in line for line in lines)
        assert has_cmd, "Should have CMD instruction"
        
    def test_service_template_integration_readiness(self):
        """TDD: Test service template is ready for integration"""
        # Arrange
        template_files = [
            "pyproject.toml",
            "Dockerfile", 
            ".pre-commit-config.yaml",
            "README.md",
            "app/main.py",
            "app/core/config.py"
        ]
        
        # Act & Assert
        for file_name in template_files:
            file_path = self.service_template_dir / file_name
            assert file_path.exists(), f"Template should have {file_name}"
            
            # Check file is not empty
            assert file_path.stat().st_size > 100, f"{file_name} should have substantial content"
            
    def test_service_template_security_features(self):
        """TDD: Test service template has security features"""
        # Arrange
        dockerfile_path = self.service_template_dir / "Dockerfile"
        precommit_path = self.service_template_dir / ".pre-commit-config.yaml"
        
        # Act
        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
            
        with open(precommit_path, 'r') as f:
            precommit_content = f.read()
        
        # Assert
        # Docker security
        assert 'USER pake' in dockerfile_content, "Should use non-root user"
        assert 'rm -rf /var/lib/apt/lists/*' in dockerfile_content, "Should clean package cache"
        
        # Pre-commit security
        assert 'bandit' in precommit_content, "Should have security linting"
        assert 'safety' in precommit_content, "Should have dependency scanning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
