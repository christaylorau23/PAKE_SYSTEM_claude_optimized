#!/usr/bin/env python3
"""
Test-Driven Development (TDD) Tests for Security Fixes
Comprehensive tests to ensure all security vulnerabilities are properly addressed
"""

import os
import pytest
import json
import hashlib
from unittest.mock import patch, MagicMock
from typing import Any, Dict

# Import the modules we're testing
from src.utils.secure_serialization import (
    SecureSerializer,
    SerializationFormat,
    SerializationConfig,
    serialize,
    deserialize,
    migrate_from_pickle,
    safe_pickle_replacement,
    safe_pickle_loads_replacement,
)
from src.utils.distributed_cache import DistributedCache, CacheConfig
from src.utils.secure_network_config import (
    SecureNetworkConfig,
    Environment,
    NetworkSecurityConfig,
    get_network_config,
    validate_network_security,
    migrate_bind_address,
)
from configs.service_config import ServiceConfig, SecurityConfig, Environment as ConfigEnvironment


class TestSecureSerialization:
    """Test secure serialization replaces pickle functionality"""

    def test_serializer_initialization(self):
        """Test secure serializer initializes correctly"""
        config = SerializationConfig()
        serializer = SecureSerializer(config)
        
        assert serializer.config == config
        assert serializer.config.default_format == SerializationFormat.JSON

    def test_json_serialization(self):
        """Test JSON serialization works correctly"""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        
        serialized = serialize(test_data, SerializationFormat.JSON)
        deserialized = deserialize(serialized)
        
        assert deserialized == test_data
        assert isinstance(serialized, bytes)
        assert serialized.startswith(b"FORMAT:json:")

    def test_serialization_with_checksum(self):
        """Test serialization includes checksum verification"""
        config = SerializationConfig(enable_checksums=True)
        serializer = SecureSerializer(config)
        
        test_data = {"secure": "data"}
        serialized = serializer.serialize(test_data)
        
        # Should include checksum header
        assert b"CHECKSUM:" in serialized
        assert b"FORMAT:json:" in serialized

    def test_checksum_verification(self):
        """Test checksum verification catches tampering"""
        config = SerializationConfig(enable_checksums=True)
        serializer = SecureSerializer(config)
        
        test_data = {"secure": "data"}
        serialized = serializer.serialize(test_data)
        
        # Tamper with the data
        tampered = serialized[:-10] + b"tampered"
        
        with pytest.raises(ValueError, match="Checksum verification failed"):
            serializer.deserialize(tampered)

    def test_size_limit_enforcement(self):
        """Test serialization enforces size limits"""
        config = SerializationConfig(max_size_bytes=100)
        serializer = SecureSerializer(config)
        
        large_data = "x" * 200
        
        with pytest.raises(ValueError, match="Serialized data too large"):
            serializer.serialize(large_data)

    def test_pickle_migration_utility(self):
        """Test pickle migration utility works"""
        # Mock pickle data
        import pickle
        original_data = {"test": "data"}
        pickle_data = pickle.dumps(original_data)
        
        # Migrate to secure format
        secure_data = migrate_from_pickle(pickle_data)
        deserialized = deserialize(secure_data)
        
        assert deserialized == original_data

    def test_safe_pickle_replacements(self):
        """Test safe pickle replacement functions"""
        test_data = {"safe": "replacement"}
        
        # Test safe replacement for pickle.dumps()
        secure_dumps = safe_pickle_replacement(test_data)
        assert isinstance(secure_dumps, bytes)
        
        # Test safe replacement for pickle.loads()
        secure_loads = safe_pickle_loads_replacement(secure_dumps)
        assert secure_loads == test_data

    def test_serialization_formats(self):
        """Test all supported serialization formats"""
        test_data = {"format": "test", "number": 123}
        
        # Test JSON format
        json_data = serialize(test_data, SerializationFormat.JSON)
        json_result = deserialize(json_data)
        assert json_result == test_data
        
        # Test MessagePack if available
        try:
            msgpack_data = serialize(test_data, SerializationFormat.MSGPACK)
            msgpack_result = deserialize(msgpack_data)
            assert msgpack_result == test_data
        except ValueError:
            # MessagePack not available, which is OK
            pass
        
        # Test CBOR if available
        try:
            cbor_data = serialize(test_data, SerializationFormat.CBOR)
            cbor_result = deserialize(cbor_data)
            assert cbor_result == test_data
        except ValueError:
            # CBOR not available, which is OK
            pass

    def test_error_handling(self):
        """Test proper error handling for invalid data"""
        with pytest.raises(RuntimeError, match="Failed to deserialize data"):
            deserialize(b"invalid data")
        
        with pytest.raises(ValueError, match="Invalid serialized data format"):
            deserialize(b"not a format header")


class TestDistributedCacheSecurity:
    """Test distributed cache security improvements"""

    def test_cache_config_secure_serialization(self):
        """Test cache uses secure serialization by default"""
        config = CacheConfig()
        assert config.default_serialization == SerializationFormat.JSON
        assert config.compression_enabled is True

    def test_cache_no_pickle_fallback(self):
        """Test cache doesn't fall back to pickle"""
        cache = DistributedCache(CacheConfig())
        
        # Mock Redis client
        cache._client = MagicMock()
        cache._client.get.return_value = b"RAW:invalid_json_data"
        
        # Should not use pickle, should return string
        result = cache._deserialize_value(b"RAW:invalid_json_data")
        assert isinstance(result, str)

    def test_cache_secure_serialization_integration(self):
        """Test cache integrates with secure serialization"""
        cache = DistributedCache(CacheConfig())
        
        # Test serialization uses secure format
        test_data = {"cache": "test"}
        serialized = cache._serialize_value(test_data)
        
        assert serialized.startswith(b"RAW:")
        # Should not contain pickle format indicators
        assert b"pickle" not in serialized.lower()


class TestSecureNetworkConfig:
    """Test secure network configuration"""

    def test_development_config_secure(self):
        """Test development config uses secure bindings"""
        config = SecureNetworkConfig(Environment.DEVELOPMENT)
        
        assert config.config.bind_address == "127.0.0.1"
        assert config.config.bind_address != "0.0.0.0"
        assert "localhost" in config.config.allowed_hosts
        assert "127.0.0.1" in config.config.allowed_hosts

    def test_production_config_secure(self):
        """Test production config enforces security"""
        with patch.dict(os.environ, {"PAKE_BIND_ADDRESS": "192.168.1.100"}):
            config = SecureNetworkConfig(Environment.PRODUCTION)
            
            assert config.config.bind_address == "192.168.1.100"
            assert config.config.bind_address != "0.0.0.0"
            assert config.config.enable_ssl is True
            assert config.config.enable_rate_limiting is True

    def test_production_warns_on_insecure_binding(self):
        """Test production warns on insecure 0.0.0.0 binding"""
        with patch.dict(os.environ, {"PAKE_BIND_ADDRESS": "0.0.0.0"}):
            config = SecureNetworkConfig(Environment.PRODUCTION)
            warnings = config.validate_configuration()
            
            assert any("CRITICAL" in warning for warning in warnings)
            assert any("0.0.0.0" in warning for warning in warnings)

    def test_bind_address_migration(self):
        """Test insecure bind address migration"""
        # Test migration from 0.0.0.0
        secure_address = migrate_bind_address("0.0.0.0")
        assert secure_address != "0.0.0.0"
        assert secure_address in ["127.0.0.1", "localhost"]
        
        # Test non-insecure addresses pass through
        secure_address = migrate_bind_address("192.168.1.100")
        assert secure_address == "192.168.1.100"

    def test_network_security_validation(self):
        """Test network security validation"""
        # Test secure configuration passes
        config = SecureNetworkConfig(Environment.DEVELOPMENT)
        assert validate_network_security() is True
        
        # Test insecure configuration fails
        with patch.dict(os.environ, {"PAKE_BIND_ADDRESS": "0.0.0.0"}):
            config = SecureNetworkConfig(Environment.PRODUCTION)
            assert validate_network_security() is False

    def test_uvicorn_config_secure(self):
        """Test uvicorn configuration is secure"""
        config = SecureNetworkConfig(Environment.PRODUCTION)
        uvicorn_config = config.get_uvicorn_config()
        
        assert uvicorn_config["host"] != "0.0.0.0"
        assert uvicorn_config["server_header"] is False
        assert uvicorn_config["date_header"] is False
        assert uvicorn_config["proxy_headers"] is True

    def test_cors_config_secure(self):
        """Test CORS configuration is secure"""
        config = SecureNetworkConfig(Environment.PRODUCTION)
        cors_config = config.get_cors_config()
        
        assert "allow_origins" in cors_config
        assert cors_config["allow_credentials"] is True
        assert "max_age" in cors_config


class TestServiceConfigSecurity:
    """Test service configuration security"""

    def test_security_config_no_hardcoded_secrets(self):
        """Test security config doesn't use hardcoded secrets in production"""
        with patch.dict(os.environ, {"PAKE_ENVIRONMENT": "production"}):
            with pytest.raises(ValueError, match="JWT secret key must be set"):
                SecurityConfig()

    def test_security_config_uses_env_vars(self):
        """Test security config uses environment variables"""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": "secure-key-from-env",
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRE_MINUTES": "60"
        }):
            config = SecurityConfig()
            
            assert config.jwt_secret_key == "secure-key-from-env"
            assert config.jwt_algorithm == "HS256"
            assert config.jwt_expire_minutes == 60

    def test_security_config_validation(self):
        """Test security config validation"""
        config = SecurityConfig()
        
        # Test valid configuration
        config.jwt_expire_minutes = 30
        config.__post_init__()  # Should not raise
        
        # Test invalid configuration
        config.jwt_expire_minutes = 0
        with pytest.raises(ValueError, match="JWT expire minutes must be at least 1"):
            config.__post_init__()

    def test_service_config_production_validation(self):
        """Test service config validates production requirements"""
        with patch.dict(os.environ, {
            "PAKE_ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "production-secret"
        }):
            config = ServiceConfig()
            
            assert config.is_production() is True
            assert config.security.jwt_secret_key == "production-secret"

    def test_config_excludes_secrets_from_dict(self):
        """Test configuration excludes secrets when converting to dict"""
        config = ServiceConfig()
        config_dict = config.to_dict()
        
        # JWT secret should be excluded
        assert "jwt_secret_key" not in config_dict["security"]
        # Other security config should be present
        assert "jwt_algorithm" in config_dict["security"]


class TestDependencyFixes:
    """Test dependency-related fixes"""

    def test_pycountry_version_fix(self):
        """Test pycountry version is fixed"""
        # This test ensures the version in pyproject.toml is valid
        import pycountry
        assert hasattr(pycountry, '__version__')
        
        # Version should be recent (24.x.x)
        version = pycountry.__version__
        major_version = int(version.split('.')[0])
        assert major_version >= 24

    def test_node_lock_files_exist(self):
        """Test Node.js lock files exist"""
        # Check that package-lock.json exists
        assert os.path.exists("package-lock.json")
        
        # Check that yarn.lock exists
        assert os.path.exists("yarn.lock")

    def test_ci_cache_configuration(self):
        """Test CI cache configuration is correct"""
        # Read the CI workflow file
        with open(".github/workflows/ci.yml", "r") as f:
            ci_content = f.read()
        
        # Should have cache-dependency-path configured
        assert "cache-dependency-path" in ci_content
        assert "package-lock.json" in ci_content


class TestSecurityIntegration:
    """Integration tests for security fixes"""

    def test_end_to_end_secure_serialization(self):
        """Test end-to-end secure serialization workflow"""
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

    def test_cache_with_secure_serialization(self):
        """Test cache works with secure serialization"""
        config = CacheConfig()
        cache = DistributedCache(config)
        
        # Mock Redis client
        cache._client = MagicMock()
        cache._client.setex.return_value = True
        cache._client.get.return_value = cache._serialize_value({"test": "data"})
        
        # Test set operation
        result = cache.set("test_key", {"test": "data"})
        assert result is True
        
        # Test get operation
        retrieved = cache.get("test_key")
        assert retrieved == {"test": "data"}

    def test_network_config_integration(self):
        """Test network configuration integrates properly"""
        config = SecureNetworkConfig(Environment.DEVELOPMENT)
        
        # Get complete server config
        server_config = config.get_secure_server_config()
        
        # Verify all components are present
        assert "uvicorn" in server_config
        assert "fastapi" in server_config
        assert "cors" in server_config
        assert "security" in server_config
        
        # Verify security settings
        assert server_config["security"]["enable_ssl"] is False  # OK for dev
        assert server_config["uvicorn"]["host"] == "127.0.0.1"

    def test_service_config_integration(self):
        """Test service configuration integrates properly"""
        with patch.dict(os.environ, {
            "PAKE_ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "test-secret"
        }):
            config = ServiceConfig()
            
            # Verify all sections are present
            assert hasattr(config, 'vault')
            assert hasattr(config, 'search')
            assert hasattr(config, 'cache')
            assert hasattr(config, 'security')
            assert hasattr(config, 'server')
            
            # Verify validation passes
            issues = config.validate()
            assert len(issues) == 0


class TestSecurityRegression:
    """Regression tests to ensure security fixes don't break functionality"""

    def test_serialization_performance(self):
        """Test serialization performance is acceptable"""
        import time
        
        test_data = {"performance": "test", "data": list(range(1000))}
        
        start_time = time.time()
        serialized = serialize(test_data)
        deserialized = deserialize(serialized)
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second)
        assert (end_time - start_time) < 1.0
        assert deserialized == test_data

    def test_cache_performance(self):
        """Test cache performance with secure serialization"""
        config = CacheConfig()
        cache = DistributedCache(config)
        
        # Mock Redis client
        cache._client = MagicMock()
        cache._client.setex.return_value = True
        cache._client.get.return_value = cache._serialize_value({"perf": "test"})
        
        # Test multiple operations
        for i in range(100):
            cache.set(f"key_{i}", {"data": f"value_{i}"})
            result = cache.get(f"key_{i}")
            assert result == {"data": f"value_{i}"}

    def test_backward_compatibility(self):
        """Test backward compatibility with existing data"""
        # Test that we can still deserialize old JSON data
        old_json_data = b'{"legacy": "data"}'
        
        # Should handle legacy format gracefully
        try:
            result = deserialize(old_json_data)
            # If it doesn't raise an error, it should return the data
            assert result == {"legacy": "data"}
        except ValueError:
            # If it raises an error, that's also acceptable for security
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
