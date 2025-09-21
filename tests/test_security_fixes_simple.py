#!/usr/bin/env python3
"""
Simple Security Tests for PAKE System
Tests that don't require external dependencies
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSecureSerialization:
    """Test secure serialization functionality"""

    def test_serializer_import(self):
        """Test secure serializer can be imported"""
        try:
            from utils.secure_serialization import (
                SecureSerializer,
                SerializationFormat,
                SerializationConfig,
                serialize,
                deserialize,
            )
            assert True  # Import successful
        except ImportError as e:
            pytest.fail(f"Failed to import secure serialization: {e}")

    def test_json_serialization(self):
        """Test JSON serialization works correctly"""
        try:
            from utils.secure_serialization import serialize, deserialize, SerializationFormat
            
            test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
            
            serialized = serialize(test_data, SerializationFormat.JSON)
            deserialized = deserialize(serialized)
            
            assert deserialized == test_data
            assert isinstance(serialized, bytes)
            assert serialized.startswith(b"FORMAT:json:")
        except ImportError:
            pytest.skip("Secure serialization not available")

    def test_serialization_formats(self):
        """Test serialization format enum"""
        try:
            from utils.secure_serialization import SerializationFormat
            
            assert SerializationFormat.JSON.value == "json"
            assert SerializationFormat.MSGPACK.value == "msgpack"
            assert SerializationFormat.CBOR.value == "cbor"
        except ImportError:
            pytest.skip("Secure serialization not available")


class TestSecureNetworkConfig:
    """Test secure network configuration"""

    def test_network_config_import(self):
        """Test network config can be imported"""
        try:
            from utils.secure_network_config import (
                SecureNetworkConfig,
                Environment,
                NetworkSecurityConfig,
                get_network_config,
                validate_network_security,
            )
            assert True  # Import successful
        except ImportError as e:
            pytest.fail(f"Failed to import network config: {e}")

    def test_environment_enum(self):
        """Test environment enum values"""
        try:
            from utils.secure_network_config import Environment
            
            assert Environment.DEVELOPMENT.value == "development"
            assert Environment.STAGING.value == "staging"
            assert Environment.PRODUCTION.value == "production"
        except ImportError:
            pytest.skip("Network config not available")

    def test_development_config_secure(self):
        """Test development config uses secure bindings"""
        try:
            from utils.secure_network_config import SecureNetworkConfig, Environment
            
            config = SecureNetworkConfig(Environment.DEVELOPMENT)
            
            assert config.config.bind_address == "127.0.0.1"
            assert config.config.bind_address != "0.0.0.0"
            assert "localhost" in config.config.allowed_hosts
            assert "127.0.0.1" in config.config.allowed_hosts
        except ImportError:
            pytest.skip("Network config not available")


class TestServiceConfigSecurity:
    """Test service configuration security"""

    def test_service_config_import(self):
        """Test service config can be imported"""
        try:
            from configs.service_config import (
                ServiceConfig,
                SecurityConfig,
                Environment as ConfigEnvironment,
            )
            assert True  # Import successful
        except ImportError as e:
            pytest.fail(f"Failed to import service config: {e}")

    def test_security_config_validation(self):
        """Test security config validation"""
        try:
            from configs.service_config import SecurityConfig
            
            config = SecurityConfig()
            
            # Test valid configuration
            config.jwt_expire_minutes = 30
            config.__post_init__()  # Should not raise
            
            # Test invalid configuration
            config.jwt_expire_minutes = 0
            with pytest.raises(ValueError, match="JWT expire minutes must be at least 1"):
                config.__post_init__()
        except ImportError:
            pytest.skip("Service config not available")


class TestDependencyFixes:
    """Test dependency-related fixes"""

    def test_pyproject_toml_exists(self):
        """Test pyproject.toml exists and has correct pycountry version"""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists()
        
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        # Check that pycountry version is updated
        assert "pycountry = \"^24.6.1\"" in content
        assert "pycountry = \"^22.3.13\"" not in content

    def test_node_lock_files_exist(self):
        """Test Node.js lock files exist"""
        project_root = Path(__file__).parent.parent
        
        # Check that package-lock.json exists
        assert (project_root / "package-lock.json").exists()
        
        # Check that yarn.lock exists
        assert (project_root / "yarn.lock").exists()

    def test_ci_cache_configuration(self):
        """Test CI cache configuration is correct"""
        ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists()
        
        with open(ci_path, 'r') as f:
            ci_content = f.read()
        
        # Should have cache-dependency-path configured
        assert "cache-dependency-path" in ci_content
        assert "package-lock.json" in ci_content

    def test_gitops_permissions(self):
        """Test GitOps workflow has correct permissions"""
        gitops_path = Path(__file__).parent.parent / ".github" / "workflows" / "gitops.yml"
        assert gitops_path.exists()
        
        with open(gitops_path, 'r') as f:
            gitops_content = f.read()
        
        # Should have write permissions
        assert "contents: write" in gitops_content


class TestSecurityFiles:
    """Test security-related files exist and are properly configured"""

    def test_security_test_script_exists(self):
        """Test comprehensive security test script exists"""
        script_path = Path(__file__).parent.parent / "scripts" / "security_test_comprehensive.py"
        assert script_path.exists()

    def test_security_tests_exist(self):
        """Test security test files exist"""
        test_path = Path(__file__).parent / "test_security_fixes.py"
        assert test_path.exists()

    def test_secure_serialization_file_exists(self):
        """Test secure serialization file exists"""
        serialization_path = Path(__file__).parent.parent / "src" / "utils" / "secure_serialization.py"
        assert serialization_path.exists()

    def test_secure_network_config_exists(self):
        """Test secure network config file exists"""
        network_path = Path(__file__).parent.parent / "src" / "utils" / "secure_network_config.py"
        assert network_path.exists()


class TestSecurityIntegration:
    """Integration tests for security fixes"""

    def test_end_to_end_secure_serialization(self):
        """Test end-to-end secure serialization workflow"""
        try:
            from utils.secure_serialization import serialize, deserialize
            
            # Create test data
            test_data = {
                "user_id": 12345,
                "data": {"sensitive": "information"},
                "metadata": ["list", "of", "items"]
            }
            
            # Serialize securely
            serialized = serialize(test_data)
            
            # Verify format
            assert serialized.startswith(b"FORMAT:")
            
            # Deserialize
            deserialized = deserialize(serialized)
            
            # Verify data integrity
            assert deserialized == test_data
        except ImportError:
            pytest.skip("Secure serialization not available")

    def test_network_config_integration(self):
        """Test network configuration integrates properly"""
        try:
            from utils.secure_network_config import SecureNetworkConfig, Environment
            
            config = SecureNetworkConfig(Environment.DEVELOPMENT)
            
            # Get complete server config
            from utils.secure_network_config import get_secure_server_config
            server_config = get_secure_server_config()
            
            # Verify all components are present
            assert "uvicorn" in server_config
            assert "fastapi" in server_config
            assert "cors" in server_config
            assert "security" in server_config
            
            # Verify security settings
            assert server_config["security"]["enable_ssl"] is False  # OK for dev
            assert server_config["uvicorn"]["host"] == "127.0.0.1"
        except ImportError:
            pytest.skip("Network config not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
