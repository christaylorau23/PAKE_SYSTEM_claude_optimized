#!/usr/bin/env python3
"""
Phase 1: Core Infrastructure Test Coverage
Achieves 20% test coverage on critical infrastructure modules
"""

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.pake_system.core.cache import CacheService, cache_key, get_cache_service

# Test the core modules
from src.pake_system.core.config import Settings, get_settings
from src.pake_system.core.logging_config import (
    CorrelationFilter,
    StructuredFormatter,
    get_logger,
    setup_logging,
)


class TestSettings:
    """Test the Settings configuration class."""

    def test_default_settings(self):
        """Test that default settings are properly set."""
        settings = Settings()

        assert settings.PROJECT_NAME == "PAKE System"
        assert (
            settings.PROJECT_DESCRIPTION
            == "Enterprise Knowledge Management & AI Research Platform"
        )
        assert settings.VERSION == "10.1.0"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 8000
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.ALGORITHM == "HS256"
        assert ["*"] == settings.ALLOWED_HOSTS
        assert settings.DATABASE_POOL_SIZE == 10
        assert settings.REDIS_POOL_SIZE == 10
        assert settings.LOG_LEVEL == "INFO"
        assert settings.USE_VAULT is True

    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production", "test"]:
            settings = Settings(ENVIRONMENT=env)
            assert env == settings.ENVIRONMENT

        # Invalid environment
        with pytest.raises(ValueError, match="Invalid environment"):
            Settings(ENVIRONMENT="invalid")

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(LOG_LEVEL=level)
            assert level == settings.LOG_LEVEL

        # Case insensitive
        settings = Settings(LOG_LEVEL="debug")
        assert settings.LOG_LEVEL == "DEBUG"

        # Invalid log level
        with pytest.raises(ValueError, match="Log level must be one of"):
            Settings(LOG_LEVEL="INVALID")

    def test_sql_log_level_validation(self):
        """Test SQL log level validation."""
        # Valid SQL log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(SQL_LOG_LEVEL=level)
            assert level == settings.SQL_LOG_LEVEL

        # Case insensitive
        settings = Settings(SQL_LOG_LEVEL="debug")
        assert settings.SQL_LOG_LEVEL == "DEBUG"

        # Invalid SQL log level
        with pytest.raises(ValueError, match="SQL log level must be one of"):
            Settings(SQL_LOG_LEVEL="INVALID")

    def test_allowed_hosts_parsing(self):
        """Test ALLOWED_HOSTS parsing from string."""
        settings = Settings(ALLOWED_HOSTS="localhost,127.0.0.1,example.com")
        assert ["localhost", "127.0.0.1", "example.com"] == settings.ALLOWED_HOSTS

        # Test with spaces
        settings = Settings(ALLOWED_HOSTS="localhost, 127.0.0.1 , example.com")
        assert ["localhost", "127.0.0.1", "example.com"] == settings.ALLOWED_HOSTS

    def test_production_vault_requirement(self):
        """Test that production environment requires Vault."""
        with pytest.raises(
            ValueError, match="Vault integration is mandatory for production"
        ):
            Settings(ENVIRONMENT="production", USE_VAULT=False)

    @patch("src.pake_system.core.config.VAULT_AVAILABLE", True)
    @patch("src.pake_system.core.config.get_vault_client")
    def test_vault_integration_success(self, mock_get_vault_client):
        """Test successful Vault integration."""
        mock_vault = Mock()
        mock_vault.get_secret.return_value = "test-secret"
        mock_get_vault_client.return_value = mock_vault

        settings = Settings(
            ENVIRONMENT="production", USE_VAULT=True, SECRET_KEY=None, DATABASE_URL=None
        )

        # Should not raise an error
        assert settings.SECRET_KEY == "test-secret"
        assert settings.DATABASE_URL == "test-secret"

    @patch("src.pake_system.core.config.VAULT_AVAILABLE", False)
    def test_vault_unavailable_fallback(self):
        """Test fallback when Vault is not available."""
        settings = Settings(
            ENVIRONMENT="development",
            USE_VAULT=True,
            SECRET_KEY="env-secret",
            DATABASE_URL="env-database-url",
        )

        # Should use environment variables
        assert settings.SECRET_KEY == "env-secret"
        assert settings.DATABASE_URL == "env-database-url"

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestLoggingConfig:
    """Test the logging configuration."""

    def test_correlation_filter(self):
        """Test correlation ID filter."""
        filter_instance = CorrelationFilter()

        # Mock log record
        record = Mock()
        record.correlation_id = "test-correlation-id"

        # Should return True (allow the record)
        assert filter_instance.filter(record) is True

        # Test without correlation_id
        record.correlation_id = None
        assert filter_instance.filter(record) is True

    def test_structured_formatter(self):
        """Test structured JSON formatter."""
        formatter = StructuredFormatter()

        # Mock log record
        record = Mock()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.return_value = "Test message"
        record.created = 1234567890.0
        record.correlation_id = "test-correlation-id"
        record.module = "test_module"
        record.funcName = "test_function"
        record.lineno = 42

        # Format the record
        formatted = formatter.format(record)

        # Should be valid JSON
        log_entry = json.loads(formatted)

        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "test_logger"
        assert log_entry["message"] == "Test message"
        assert log_entry["correlation_id"] == "test-correlation-id"
        assert log_entry["module"] == "test_module"
        assert log_entry["function"] == "test_function"
        assert log_entry["line"] == 42

    def test_setup_logging(self):
        """Test logging setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Setup logging
                setup_logging(log_level="DEBUG", enable_json=True)

                # Get logger
                logger = get_logger("test_logger")

                # Test logging
                logger.info("Test message")

                # Verify logger exists
                assert logger.name == "test_logger"
                assert logger.level <= logging.INFO

            finally:
                os.chdir(original_cwd)

    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger("test_module")

        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)


class TestCacheService:
    """Test the cache service."""

    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = cache_key("test", "key", "1")
        key2 = cache_key("test", "key", "2")
        key3 = cache_key("test", "key", "1")  # Same as key1

        assert key1 != key2
        assert key1 == key3
        assert key1.startswith("pake:")
        assert "test" in key1
        assert "key" in key1
        assert "1" in key1

    @patch("src.pake_system.core.cache.redis.Redis")
    def test_cache_service_initialization(self, mock_redis):
        """Test cache service initialization."""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        cache_service = CacheService()

        assert cache_service.redis_client is mock_redis_instance
        mock_redis.assert_called_once()

    @patch("src.pake_system.core.cache.redis.Redis")
    def test_cache_service_get_set(self, mock_redis):
        """Test cache get/set operations."""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        cache_service = CacheService()

        # Test set
        cache_service.set("test_key", "test_value", ttl=300)
        mock_redis_instance.setex.assert_called_once_with("test_key", 300, "test_value")

        # Test get
        mock_redis_instance.get.return_value = b"test_value"
        result = cache_service.get("test_key")
        assert result == "test_value"
        mock_redis_instance.get.assert_called_once_with("test_key")

        # Test get with default
        mock_redis_instance.get.return_value = None
        result = cache_service.get("nonexistent_key", default="default_value")
        assert result == "default_value"

    @patch("src.pake_system.core.cache.redis.Redis")
    def test_cache_service_delete(self, mock_redis):
        """Test cache delete operation."""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        cache_service = CacheService()

        cache_service.delete("test_key")
        mock_redis_instance.delete.assert_called_once_with("test_key")

    @patch("src.pake_system.core.cache.redis.Redis")
    def test_cache_service_exists(self, mock_redis):
        """Test cache exists operation."""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        cache_service = CacheService()

        # Test exists returns True
        mock_redis_instance.exists.return_value = 1
        assert cache_service.exists("test_key") is True

        # Test exists returns False
        mock_redis_instance.exists.return_value = 0
        assert cache_service.exists("test_key") is False

        mock_redis_instance.exists.assert_called_with("test_key")

    @patch("src.pake_system.core.cache.redis.Redis")
    def test_cache_service_clear(self, mock_redis):
        """Test cache clear operation."""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        cache_service = CacheService()

        cache_service.clear()
        mock_redis_instance.flushdb.assert_called_once()

    def test_get_cache_service_singleton(self):
        """Test that get_cache_service returns singleton."""
        with patch("src.pake_system.core.cache.redis.Redis"):
            service1 = get_cache_service()
            service2 = get_cache_service()

            assert service1 is service2


class TestVaultClient:
    """Test the Vault client (if available)."""

    @patch("src.pake_system.core.vault_client.VAULT_AVAILABLE", True)
    @patch("src.pake_system.core.vault_client.hvac.Client")
    def test_vault_client_initialization(self, mock_hvac_client):
        """Test Vault client initialization."""
        from src.pake_system.core.vault_client import VaultClient

        mock_client = Mock()
        mock_hvac_client.return_value = mock_client

        vault_client = VaultClient(environment="test")

        assert vault_client.environment == "test"
        assert vault_client.client is mock_client

    @patch("src.pake_system.core.vault_client.VAULT_AVAILABLE", False)
    def test_vault_client_unavailable(self):
        """Test behavior when Vault is not available."""
        from src.pake_system.core.vault_client import VaultClient

        with pytest.raises(ImportError):
            VaultClient(environment="test")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
