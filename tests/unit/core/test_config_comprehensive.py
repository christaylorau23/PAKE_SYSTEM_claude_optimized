#!/usr/bin/env python3
"""Unit tests for PAKE System Configuration Module.

This module provides comprehensive test coverage for the core configuration
management system, ensuring robust handling of environment variables, Vault
integration, and validation logic.

Test Categories:
- Environment variable handling
- Vault client integration
- Configuration validation
- Error handling and edge cases
- Security scenarios
"""

import os
from pathlib import Path

# Import the module under test
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.pake_system.core.config import Settings, get_settings


class TestSettingsConfiguration:
    """Test suite for Settings class configuration management."""
    
    def test_settings_initialization_defaults(self):
        """Test Settings initialization with default values."""
        # Test that Settings can be initialized with default values
        settings = Settings()
        
        # Verify critical default values
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DATABASE_URL is not None
        assert isinstance(settings.ALLOWED_HOSTS, list)
        assert "*" in settings.ALLOWED_HOSTS
    
    def test_settings_environment_variable_override(self):
        """Test that environment variables override default settings."""
        # Set test environment variables
        test_env = {
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "sqlite:///test.db",
            "ALLOWED_HOSTS": "localhost,127.0.0.1"
        }
        
        with patch.dict(os.environ, test_env):
            settings = Settings()
            
            assert settings.DEBUG is True
            assert settings.LOG_LEVEL == "DEBUG"
            assert settings.DATABASE_URL == "sqlite:///test.db"
            assert "localhost" in settings.ALLOWED_HOSTS
            assert "127.0.0.1" in settings.ALLOWED_HOSTS
    
    def test_settings_vault_integration_disabled(self):
        """Test Settings behavior when Vault is not available."""
        # Mock Vault client to simulate unavailability
        with patch('src.pake_system.core.config.get_vault_client', side_effect=ImportError):
            settings = Settings()
            
            # Should still initialize successfully
            assert settings is not None
            assert hasattr(settings, 'DATABASE_URL')
    
    def test_settings_vault_integration_enabled(self):
        """Test Settings behavior when Vault is available."""
        # Mock Vault client
        mock_vault = Mock()
        mock_vault.get_secret.return_value = "vault_secret_value"
        
        with patch('src.pake_system.core.config.get_vault_client', return_value=mock_vault):
            settings = Settings()
            
            # Verify Vault client was called
            mock_vault.get_secret.assert_called()
    
    def test_settings_validation_rules(self):
        """Test configuration validation rules."""
        # Test invalid LOG_LEVEL
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"}):
            with pytest.raises(ValueError):
                Settings()
        
        # Test invalid DEBUG value
        with patch.dict(os.environ, {"DEBUG": "invalid"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_settings_security_configuration(self):
        """Test security-related configuration settings."""
        settings = Settings()
        
        # Verify security defaults
        assert hasattr(settings, 'SECRET_KEY')
        assert hasattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES')
        assert hasattr(settings, 'ALGORITHM')
        
        # Verify token expiration is reasonable
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES < 1440  # Less than 24 hours
    
    def test_settings_database_configuration(self):
        """Test database configuration settings."""
        settings = Settings()
        
        # Verify database settings exist
        assert hasattr(settings, 'DATABASE_URL')
        assert hasattr(settings, 'DATABASE_POOL_SIZE')
        assert hasattr(settings, 'DATABASE_MAX_OVERFLOW')
        
        # Verify reasonable defaults
        assert settings.DATABASE_POOL_SIZE > 0
        assert settings.DATABASE_MAX_OVERFLOW >= 0


class TestGetSettingsFunction:
    """Test suite for get_settings function."""
    
    def test_get_settings_caching(self):
        """Test that get_settings uses caching."""
        # First call should create settings
        settings1 = get_settings()
        assert settings1 is not None
        
        # Second call should return cached instance
        settings2 = get_settings()
        assert settings1 is settings2  # Same instance
    
    def test_get_settings_consistency(self):
        """Test that get_settings returns consistent settings."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Verify settings are identical
        assert settings1.DEBUG == settings2.DEBUG
        assert settings1.LOG_LEVEL == settings2.LOG_LEVEL
        assert settings1.DATABASE_URL == settings2.DATABASE_URL


class TestConfigurationEdgeCases:
    """Test suite for edge cases and error scenarios."""
    
    def test_empty_environment_variables(self):
        """Test behavior with empty environment variables."""
        # Clear all relevant environment variables
        env_vars_to_clear = [
            "DEBUG", "LOG_LEVEL", "DATABASE_URL", "ALLOWED_HOSTS",
            "SECRET_KEY", "ACCESS_TOKEN_EXPIRE_MINUTES"
        ]
        
        with patch.dict(os.environ, {var: "" for var in env_vars_to_clear}, clear=True):
            settings = Settings()
            
            # Should still initialize with defaults
            assert settings is not None
            assert settings.DEBUG is False  # Default value
    
    def test_malformed_environment_variables(self):
        """Test behavior with malformed environment variables."""
        # Test malformed boolean
        with patch.dict(os.environ, {"DEBUG": "maybe"}):
            with pytest.raises(ValueError):
                Settings()
        
        # Test malformed list
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "invalid,list,format"}):
            # Should handle gracefully or raise appropriate error
            try:
                settings = Settings()
                # If it doesn't raise an error, verify it handles the input
                assert isinstance(settings.ALLOWED_HOSTS, list)
            except ValueError:
                # This is also acceptable behavior
                pass
    
    def test_vault_client_error_handling(self):
        """Test error handling when Vault client fails."""
        # Mock Vault client to raise an exception
        mock_vault = Mock()
        mock_vault.get_secret.side_effect = Exception("Vault connection failed")
        
        with patch('src.pake_system.core.config.get_vault_client', return_value=mock_vault):
            # Should handle Vault errors gracefully
            try:
                settings = Settings()
                assert settings is not None
            except (ValueError, RuntimeError) as e:
                # If it raises an exception, it should be handled appropriately
                assert "Vault" in str(e) or "connection" in str(e).lower()


class TestConfigurationSecurity:
    """Test suite for security-related configuration scenarios."""
    
    def test_secret_key_generation(self):
        """Test that secret keys are properly generated."""
        settings = Settings()
        
        # Verify secret key exists and is not empty
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0
        
        # Verify secret key is different between instances
        settings2 = Settings()
        assert settings.SECRET_KEY != settings2.SECRET_KEY
    
    def test_token_expiration_security(self):
        """Test token expiration security settings."""
        settings = Settings()
        
        # Verify token expiration is not too long (security risk)
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 60  # Max 1 hour
        
        # Verify token expiration is not too short (usability issue)
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES >= 15  # Min 15 minutes
    
    def test_allowed_hosts_security(self):
        """Test allowed hosts security configuration."""
        settings = Settings()
        
        # Verify allowed hosts is a list
        assert isinstance(settings.ALLOWED_HOSTS, list)
        
        # Verify it's not empty
        assert len(settings.ALLOWED_HOSTS) > 0
        
        # Verify it contains at least one valid host
        assert any(host for host in settings.ALLOWED_HOSTS if host)


class TestConfigurationPerformance:
    """Test suite for configuration performance scenarios."""
    
    def test_settings_initialization_performance(self):
        """Test that settings initialization is reasonably fast."""
        import time
        
        start_time = time.time()
        settings = Settings()
        end_time = time.time()
        
        # Should initialize in less than 1 second
        assert (end_time - start_time) < 1.0
        assert settings is not None
    
    def test_get_settings_performance(self):
        """Test that get_settings is fast due to caching."""
        import time
        
        # First call (creates settings)
        start_time = time.time()
        settings1 = get_settings()
        first_call_time = time.time() - start_time
        
        # Second call (uses cache)
        start_time = time.time()
        settings2 = get_settings()
        second_call_time = time.time() - start_time
        
        # Second call should be significantly faster
        assert second_call_time < first_call_time
        assert settings1 is settings2


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])