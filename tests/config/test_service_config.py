#!/usr/bin/env python3
"""
Tests for Unified Configuration System
Tests hierarchical configuration loading, validation, and platform independence
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "configs"))

from configs.service_config import (
    CacheConfig,
    SearchConfig,
    ServiceConfig,
    VaultConfig,
    get_config,
)


class TestServiceConfig:
    """Test ServiceConfig class functionality"""

    def setup_method(self):
        """Set up test environment"""
        # Clear any existing global config
        from configs import service_config

        service_config._config_instance = None

    def test_default_configuration_values(self):
        """Test that default configuration values are loaded correctly"""
        config = ServiceConfig()

        # Test vault defaults
        assert config.vault.default_vault_name == "Knowledge-Vault"
        assert config.vault.max_filename_length == 50
        assert config.vault.default_file_extension == ".md"
        assert config.vault.summary_truncate_length == 200
        assert config.vault.default_confidence_score == 0.7

        # Test search defaults
        assert config.search.default_search_limit == 10
        assert config.search.max_search_limit == 100

        # Test cache defaults
        assert config.cache.default_ttl_seconds == 300
        assert config.cache.production_ttl_seconds == 300
        assert config.cache.development_ttl_seconds == 0

        # Test server defaults
        assert config.server.server_name == "pake-server"
        assert config.server.server_version == "1.0.0"
        assert config.server.mcp_server_port == 8000

    def test_config_file_loading(self):
        """Test loading configuration from JSON file"""
        config_data = {
            "vault": {"max_filename_length": 75, "default_confidence_score": 0.8},
            "search": {"default_search_limit": 15, "max_search_limit": 150},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            config = ServiceConfig(config_file=config_file)

            # Check that config file values override defaults
            assert config.vault.max_filename_length == 75
            assert config.vault.default_confidence_score == 0.8
            assert config.search.default_search_limit == 15
            assert config.search.max_search_limit == 150

            # Check that unspecified values use defaults
            assert config.vault.default_vault_name == "Knowledge-Vault"
            assert config.cache.default_ttl_seconds == 300

        finally:
            os.unlink(config_file)

    def test_environment_variable_overrides(self):
        """Test environment variable overrides"""
        env_vars = {
            "PAKE_MAX_FILENAME_LENGTH": "100",
            "PAKE_SEARCH_LIMIT": "25",
            "PAKE_CACHE_TTL": "600",
            "PAKE_LOG_LEVEL": "DEBUG",
            "PAKE_LOG_JSON": "false",
        }

        with patch.dict(os.environ, env_vars):
            config = ServiceConfig()

            assert config.vault.max_filename_length == 100
            assert config.search.default_search_limit == 25
            assert config.cache.default_ttl_seconds == 600
            assert config.logging.default_level == "DEBUG"
            assert config.logging.json_formatting == False

    def test_hierarchical_configuration_loading(self):
        """Test that configuration is loaded in correct priority order"""
        # Create config file
        config_data = {
            "vault": {"max_filename_length": 60},
            "search": {"default_search_limit": 20},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        # Environment variables should override config file
        env_vars = {
            "PAKE_MAX_FILENAME_LENGTH": "80",  # Should override config file value of 60
            "PAKE_CACHE_TTL": "450",  # Should override default value of 300
        }

        try:
            with patch.dict(os.environ, env_vars):
                config = ServiceConfig(config_file=config_file)

                # Environment should override config file
                assert config.vault.max_filename_length == 80

                # Config file should override default
                assert config.search.default_search_limit == 20

                # Environment should override default
                assert config.cache.default_ttl_seconds == 450

                # Defaults should be used when not overridden
                assert config.vault.default_vault_name == "Knowledge-Vault"

        finally:
            os.unlink(config_file)

    def test_platform_independent_vault_path(self):
        """Test that vault path is platform independent"""
        config = ServiceConfig()

        # Test default path (should be relative to user home)
        vault_path = config.get_vault_path()

        assert isinstance(vault_path, Path)
        assert vault_path.is_absolute()
        assert vault_path.name == "Knowledge-Vault"
        assert str(vault_path.home()) in str(vault_path)

        # Test explicit VAULT_PATH environment variable
        test_path = "/tmp/test-vault" if os.name != "nt" else r"C:\temp\test-vault"

        with patch.dict(os.environ, {"VAULT_PATH": test_path}):
            vault_path = config.get_vault_path()
            assert str(vault_path) == str(Path(test_path).resolve())

    def test_folder_structure_mapping(self):
        """Test note type to folder mapping"""
        config = ServiceConfig()

        assert config.get_folder_for_note_type("SourceNote") == "00-Inbox"
        assert config.get_folder_for_note_type("DailyNote") == "01-Daily"
        assert config.get_folder_for_note_type("ProjectNote") == "01-Projects"
        assert config.get_folder_for_note_type("InsightNote") == "02-Areas"

        # Test unknown note type defaults to SourceNote folder
        assert config.get_folder_for_note_type("UnknownType") == "00-Inbox"

    def test_cache_ttl_environment_dependent(self):
        """Test cache TTL varies by environment"""
        config = ServiceConfig()

        # Test production environment
        production_ttl = config.get_cache_ttl("production")
        assert production_ttl == config.cache.production_ttl_seconds

        # Test development environment
        dev_ttl = config.get_cache_ttl("development")
        assert dev_ttl == config.cache.development_ttl_seconds

        # Test default environment detection
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            auto_ttl = config.get_cache_ttl()
            assert auto_ttl == config.cache.production_ttl_seconds

    def test_configuration_validation(self):
        """Test configuration validation catches invalid values"""
        config = ServiceConfig()

        # Valid configuration should pass
        assert config.validate_configuration()

        # Test invalid search limits
        config.search.default_search_limit = 200
        config.search.max_search_limit = 100
        assert config.validate_configuration() == False

        # Reset and test invalid confidence score
        config.search.default_search_limit = 10
        config.search.max_search_limit = 100
        config.vault.default_confidence_score = 1.5
        assert config.validate_configuration() == False

        # Reset and test negative cache TTL
        config.vault.default_confidence_score = 0.7
        config.cache.default_ttl_seconds = -100
        assert config.validate_configuration() == False

    def test_config_export_to_dict(self):
        """Test configuration can be exported as dictionary"""
        config = ServiceConfig()
        config_dict = config.to_dict()

        # Check structure
        assert "vault" in config_dict
        assert "search" in config_dict
        assert "cache" in config_dict
        assert "logging" in config_dict
        assert "security" in config_dict
        assert "server" in config_dict
        assert "_metadata" in config_dict

        # Check values
        assert config_dict["vault"]["default_vault_name"] == "Knowledge-Vault"
        assert config_dict["search"]["default_search_limit"] == 10
        assert config_dict["_metadata"]["vault_path"] == str(config.get_vault_path())

    def test_invalid_config_file_handling(self):
        """Test handling of invalid or missing config files"""

        # Test missing file - use explicit non-existent path and patch to prevent
        # fallback discovery
        nonexistent_file = "/absolutely/nonexistent/path/config.json"

        with patch("service_config.ServiceConfig._find_config_file", return_value=None):
            config = ServiceConfig(config_file=nonexistent_file)
            assert config.config_file_path is None
            assert (
                config.vault.default_vault_name == "Knowledge-Vault"
            )  # Should use defaults

        # Test invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')
            invalid_config_file = f.name

        try:
            # Patch to prevent fallback to actual config files
            with patch(
                "service_config.ServiceConfig._find_config_file",
                return_value=invalid_config_file,
            ):
                config = ServiceConfig(config_file=invalid_config_file)
                assert config.config_file_path is None  # Should not load invalid file
                assert (
                    config.vault.default_vault_name == "Knowledge-Vault"
                )  # Should use defaults
        finally:
            os.unlink(invalid_config_file)

    def test_type_validation_in_config_overrides(self):
        """Test that config overrides validate types"""
        config_data = {
            "vault": {
                "max_filename_length": "not a number",  # Invalid type
                "default_confidence_score": 0.8,  # Valid type
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            with patch("logging.Logger.warning") as mock_warning:
                config = ServiceConfig(config_file=config_file)

                # Invalid type should be ignored
                assert config.vault.max_filename_length == 50  # Default value

                # Valid type should be applied
                assert config.vault.default_confidence_score == 0.8

                # Should log warning about type mismatch
                mock_warning.assert_called()

        finally:
            os.unlink(config_file)


class TestGlobalConfigSingleton:
    """Test global configuration singleton functionality"""

    def setup_method(self):
        """Clear global config before each test"""
        from configs import service_config

        service_config._config_instance = None

    def test_singleton_pattern(self):
        """Test that get_config returns same instance"""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_force_reload_option(self):
        """Test that force_reload creates new instance"""
        config1 = get_config()
        config2 = get_config(force_reload=True)

        assert config1 is not config2

    def test_config_file_parameter_in_singleton(self):
        """Test that config file parameter works with singleton"""
        config_data = {"vault": {"max_filename_length": 99}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            config = get_config(config_file=config_file)
            assert config.vault.max_filename_length == 99

            # Second call should return same configured instance
            config2 = get_config()
            assert config2.vault.max_filename_length == 99
            assert config is config2

        finally:
            os.unlink(config_file)


class TestConfigurationDataClasses:
    """Test individual configuration dataclasses"""

    def test_vault_config_defaults(self):
        """Test VaultConfig defaults"""
        vault_config = VaultConfig()

        assert vault_config.default_vault_name == "Knowledge-Vault"
        assert vault_config.max_filename_length == 50
        assert vault_config.default_file_extension == ".md"
        assert vault_config.summary_truncate_length == 200
        assert vault_config.default_confidence_score == 0.7

        # Test folder structure
        assert "SourceNote" in vault_config.folder_structure
        assert vault_config.folder_structure["SourceNote"] == "00-Inbox"

    def test_search_config_defaults(self):
        """Test SearchConfig defaults"""
        search_config = SearchConfig()

        assert search_config.default_search_limit == 10
        assert search_config.max_search_limit == 100
        assert search_config.min_confidence_threshold == 0.0
        assert search_config.max_confidence_threshold == 1.0

    def test_cache_config_defaults(self):
        """Test CacheConfig defaults"""
        cache_config = CacheConfig()

        assert cache_config.default_ttl_seconds == 300
        assert cache_config.production_ttl_seconds == 300
        assert cache_config.development_ttl_seconds == 0
        assert cache_config.max_ttl_seconds == 3600


class TestPlatformIndependence:
    """Test platform-independent functionality"""

    def test_path_handling_windows(self):
        """Test path handling on Windows-style paths"""
        config = ServiceConfig()

        # Test Windows-style environment variable
        windows_path = r"C:\Users\TestUser\Documents\MyVault"

        with patch.dict(os.environ, {"VAULT_PATH": windows_path}):
            vault_path = config.get_vault_path()

            assert isinstance(vault_path, Path)
            assert vault_path.is_absolute()
            # Should resolve to proper Path object regardless of platform
            assert str(vault_path) == str(Path(windows_path).resolve())

    def test_path_handling_unix(self):
        """Test path handling on Unix-style paths"""
        config = ServiceConfig()

        # Test Unix-style environment variable
        unix_path = "/home/testuser/documents/MyVault"

        with patch.dict(os.environ, {"VAULT_PATH": unix_path}):
            vault_path = config.get_vault_path()

            assert isinstance(vault_path, Path)
            assert vault_path.is_absolute()
            assert str(vault_path) == str(Path(unix_path).resolve())

    def test_home_directory_resolution(self):
        """Test that home directory resolution works across platforms"""
        config = ServiceConfig()

        # Mock home directory resolution to avoid environment-specific issues
        mock_home = Path("/mock/home/user")

        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.home", return_value=mock_home):
                vault_path = config.get_vault_path()

                expected_path = mock_home / "Knowledge-Vault"

                assert vault_path == expected_path.resolve()
                assert vault_path.is_absolute()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
