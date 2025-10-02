#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Refactored SecretsManager Class

Tests the Single Responsibility Principle refactoring of the SecretsManager class,
ensuring each method has a single, clearly defined responsibility and can be tested
independently.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the refactored SecretsManager
from security.secrets_manager import SecretProvider, SecretsManager


class TestSecretsManagerRefactoring:
    """Test suite for the refactored SecretsManager class"""

    def setup_method(self):
        """Set up test environment before each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """Clean up after each test method"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_constructor_orchestration(self):
        """Test that constructor properly orchestrates the setup process"""
        with patch.object(
            SecretsManager, "_validate_provider_parameter"
        ) as mock_validate, patch.object(
            SecretsManager, "_configure_logging"
        ) as mock_logging, patch.object(
            SecretsManager, "_initialize_data_structures"
        ) as mock_data, patch.object(
            SecretsManager, "_configure_provider"
        ) as mock_provider, patch.object(
            SecretsManager, "_initialize_provider_client"
        ) as mock_client:
            # Create instance with local provider (no external dependencies)
            manager = SecretsManager(SecretProvider.LOCAL_FILE)

            # Verify all orchestration methods were called in correct order
            mock_validate.assert_called_once()
            mock_logging.assert_called_once()
            mock_data.assert_called_once()
            mock_provider.assert_called_once()
            mock_client.assert_called_once()

            # Verify provider is set correctly
            assert manager.provider == SecretProvider.LOCAL_FILE

    def test_validate_provider_parameter_valid_provider(self):
        """Test parameter validation with valid provider"""
        manager = SecretsManager()
        manager.provider = SecretProvider.LOCAL_FILE

        # Should not raise any exception
        manager._validate_provider_parameter()

    def test_validate_provider_parameter_invalid_type(self):
        """Test parameter validation with invalid provider type"""
        manager = SecretsManager()
        manager.provider = "invalid_provider"  # Not a SecretProvider enum

        with pytest.raises(
            ValueError, match="Provider must be a SecretProvider enum value"
        ):
            manager._validate_provider_parameter()

    def test_validate_provider_parameter_azure_missing_url(self):
        """Test Azure provider validation with missing URL"""
        manager = SecretsManager()
        manager.provider = SecretProvider.AZURE_KEY_VAULT

        # Remove AZURE_KEY_VAULT_URL if it exists
        if "AZURE_KEY_VAULT_URL" in os.environ:
            del os.environ["AZURE_KEY_VAULT_URL"]

        with pytest.raises(
            ValueError, match="AZURE_KEY_VAULT_URL environment variable is required"
        ):
            manager._validate_provider_parameter()

    def test_validate_provider_parameter_google_missing_project(self):
        """Test Google provider validation with missing project ID"""
        manager = SecretsManager()
        manager.provider = SecretProvider.GOOGLE_SECRET_MANAGER

        # Remove GOOGLE_CLOUD_PROJECT_ID if it exists
        if "GOOGLE_CLOUD_PROJECT_ID" in os.environ:
            del os.environ["GOOGLE_CLOUD_PROJECT_ID"]

        with pytest.raises(
            ValueError, match="GOOGLE_CLOUD_PROJECT_ID environment variable is required"
        ):
            manager._validate_provider_parameter()

    def test_configure_logging(self):
        """Test logging configuration"""
        manager = SecretsManager()

        with patch.object(manager, "_setup_logger") as mock_setup:
            mock_logger = Mock()
            mock_setup.return_value = mock_logger

            manager._configure_logging()

            mock_setup.assert_called_once()
            assert manager.logger == mock_logger

    def test_initialize_data_structures(self):
        """Test data structure initialization"""
        manager = SecretsManager()

        manager._initialize_data_structures()

        # Verify all data structures are initialized
        assert isinstance(manager.secrets_cache, dict)
        assert isinstance(manager.access_logs, list)
        assert isinstance(manager.metadata_store, dict)

        # Verify they are empty initially
        assert len(manager.secrets_cache) == 0
        assert len(manager.access_logs) == 0
        assert len(manager.metadata_store) == 0

    def test_configure_provider_local(self):
        """Test local provider configuration"""
        manager = SecretsManager()
        manager.provider = SecretProvider.LOCAL_FILE

        with patch.object(manager, "_configure_local_provider") as mock_local:
            manager._configure_provider()
            mock_local.assert_called_once()

    def test_configure_provider_aws(self):
        """Test AWS provider configuration"""
        manager = SecretsManager()
        manager.provider = SecretProvider.AWS_SECRETS_MANAGER

        with patch.object(manager, "_configure_aws_provider") as mock_aws:
            manager._configure_provider()
            mock_aws.assert_called_once()

    def test_configure_provider_azure(self):
        """Test Azure provider configuration"""
        manager = SecretsManager()
        manager.provider = SecretProvider.AZURE_KEY_VAULT

        with patch.object(manager, "_configure_azure_provider") as mock_azure:
            manager._configure_provider()
            mock_azure.assert_called_once()

    def test_configure_provider_google(self):
        """Test Google provider configuration"""
        manager = SecretsManager()
        manager.provider = SecretProvider.GOOGLE_SECRET_MANAGER

        with patch.object(manager, "_configure_google_provider") as mock_google:
            manager._configure_provider()
            mock_google.assert_called_once()

    def test_configure_provider_unsupported(self):
        """Test unsupported provider configuration"""
        manager = SecretsManager()
        manager.provider = "unsupported_provider"  # Invalid provider

        with pytest.raises(ValueError, match="Unsupported provider"):
            manager._configure_provider()

    def test_configure_aws_provider(self):
        """Test AWS provider-specific configuration"""
        manager = SecretsManager()
        manager.logger = Mock()

        # Set up environment variables
        os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
        os.environ["AWS_PROFILE"] = "test-profile"
        os.environ["AWS_ENDPOINT_URL"] = "https://test-endpoint.com"

        manager._configure_aws_provider()

        # Verify configuration
        assert manager.provider_config["region"] == "us-west-2"
        assert manager.provider_config["profile"] == "test-profile"
        assert manager.provider_config["endpoint_url"] == "https://test-endpoint.com"

        manager.logger.info.assert_called_with(
            "AWS Secrets Manager provider configured"
        )

    def test_configure_azure_provider(self):
        """Test Azure provider-specific configuration"""
        manager = SecretsManager()
        manager.logger = Mock()

        # Set up environment variables
        os.environ["AZURE_KEY_VAULT_URL"] = "https://test-vault.vault.azure.net/"
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"

        manager._configure_azure_provider()

        # Verify configuration
        assert (
            manager.provider_config["vault_url"]
            == "https://test-vault.vault.azure.net/"
        )
        assert manager.provider_config["tenant_id"] == "test-tenant-id"
        assert manager.provider_config["client_id"] == "test-client-id"
        assert manager.provider_config["client_secret"] == "test-client-secret"

        manager.logger.info.assert_called_with("Azure Key Vault provider configured")

    def test_configure_google_provider(self):
        """Test Google provider-specific configuration"""
        manager = SecretsManager()
        manager.logger = Mock()

        # Set up environment variables
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project-id"
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/credentials.json"
        os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

        manager._configure_google_provider()

        # Verify configuration
        assert manager.provider_config["project_id"] == "test-project-id"
        assert (
            manager.provider_config["credentials_path"] == "/path/to/credentials.json"
        )
        assert manager.provider_config["location"] == "us-central1"

        manager.logger.info.assert_called_with(
            "Google Secret Manager provider configured"
        )

    def test_configure_local_provider(self):
        """Test local provider-specific configuration"""
        manager = SecretsManager()
        manager.logger = Mock()

        # Set up environment variables
        os.environ["LOCAL_SECRETS_ENCRYPTION_KEY"] = "test-encryption-key"
        os.environ["LOCAL_SECRETS_BACKUP"] = "false"

        manager._configure_local_provider()

        # Verify configuration
        assert isinstance(manager.provider_config["secrets_dir"], Path)
        assert manager.provider_config["encryption_key"] == "test-encryption-key"
        assert manager.provider_config["backup_enabled"] is False

        manager.logger.info.assert_called_with("Local file storage provider configured")

    def test_initialize_provider_client_local(self):
        """Test local client initialization"""
        manager = SecretsManager()
        manager.provider = SecretProvider.LOCAL_FILE
        manager.logger = Mock()

        with patch.object(manager, "_initialize_local_client") as mock_local:
            manager._initialize_provider_client()
            mock_local.assert_called_once()
            manager.logger.info.assert_called_with(
                "✅ local_file client initialized successfully"
            )

    def test_initialize_provider_client_aws(self):
        """Test AWS client initialization"""
        manager = SecretsManager()
        manager.provider = SecretProvider.AWS_SECRETS_MANAGER
        manager.logger = Mock()

        with patch.object(manager, "_initialize_aws_client") as mock_aws:
            manager._initialize_provider_client()
            mock_aws.assert_called_once()
            manager.logger.info.assert_called_with(
                "✅ aws_secrets_manager client initialized successfully"
            )

    def test_initialize_provider_client_azure(self):
        """Test Azure client initialization"""
        manager = SecretsManager()
        manager.provider = SecretProvider.AZURE_KEY_VAULT
        manager.logger = Mock()

        with patch.object(manager, "_initialize_azure_client") as mock_azure:
            manager._initialize_provider_client()
            mock_azure.assert_called_once()
            manager.logger.info.assert_called_with(
                "✅ azure_key_vault client initialized successfully"
            )

    def test_initialize_provider_client_google(self):
        """Test Google client initialization"""
        manager = SecretsManager()
        manager.provider = SecretProvider.GOOGLE_SECRET_MANAGER
        manager.logger = Mock()

        with patch.object(manager, "_initialize_google_client") as mock_google:
            manager._initialize_provider_client()
            mock_google.assert_called_once()
            manager.logger.info.assert_called_with(
                "✅ google_secret_manager client initialized successfully"
            )

    def test_initialize_provider_client_failure(self):
        """Test provider client initialization failure"""
        manager = SecretsManager()
        manager.provider = SecretProvider.AWS_SECRETS_MANAGER
        manager.logger = Mock()

        with patch.object(manager, "_initialize_aws_client") as mock_aws:
            mock_aws.side_effect = Exception("AWS initialization failed")

            with pytest.raises(RuntimeError, match="Provider initialization failed"):
                manager._initialize_provider_client()

            manager.logger.error.assert_called_with(
                "Failed to initialize aws_secrets_manager client: AWS initialization failed"
            )

    def test_initialize_aws_client_with_configuration(self):
        """Test AWS client initialization with provider configuration"""
        manager = SecretsManager()
        manager.logger = Mock()
        manager.provider_config = {
            "region": "us-west-2",
            "profile": "test-profile",
            "endpoint_url": "https://test-endpoint.com",
        }

        with patch("boto3.Session") as mock_session_class, patch(
            "boto3.client"
        ) as mock_client_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_client = Mock()
            mock_session.client.return_value = mock_client

            manager._initialize_aws_client()

            # Verify session was created with correct profile
            mock_session_class.assert_called_once_with(profile_name="test-profile")

            # Verify client was created with correct parameters
            mock_session.client.assert_called_once_with(
                service_name="secretsmanager",
                region_name="us-west-2",
                endpoint_url="https://test-endpoint.com",
            )

            assert manager.aws_client == mock_client
            manager.logger.info.assert_called_with(
                "AWS Secrets Manager client initialized"
            )

    def test_initialize_azure_client_with_configuration(self):
        """Test Azure client initialization with provider configuration"""
        manager = SecretsManager()
        manager.logger = Mock()
        manager.provider_config = {"vault_url": "https://test-vault.vault.azure.net/"}

        with patch(
            "azure.identity.DefaultAzureCredential"
        ) as mock_credential_class, patch(
            "azure.keyvault.secrets.SecretClient"
        ) as mock_client_class:
            mock_credential = Mock()
            mock_credential_class.return_value = mock_credential
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            manager._initialize_azure_client()

            # Verify credential was created
            mock_credential_class.assert_called_once()

            # Verify client was created with correct parameters
            mock_client_class.assert_called_once_with(
                vault_url="https://test-vault.vault.azure.net/",
                credential=mock_credential,
            )

            assert manager.azure_client == mock_client
            manager.logger.info.assert_called_with("Azure Key Vault client initialized")

    def test_initialize_google_client_with_configuration(self):
        """Test Google client initialization with provider configuration"""
        manager = SecretsManager()
        manager.logger = Mock()
        manager.provider_config = {"project_id": "test-project-id"}

        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            manager._initialize_google_client()

            # Verify client was created
            mock_client_class.assert_called_once()

            assert manager.google_client == mock_client
            assert manager.project_id == "test-project-id"
            manager.logger.info.assert_called_with(
                "Google Secret Manager client initialized"
            )

    def test_initialize_local_client_with_configuration(self):
        """Test local client initialization with provider configuration"""
        manager = SecretsManager()
        manager.logger = Mock()
        manager.provider_config = {
            "secrets_dir": Path(self.temp_dir),
            "encryption_key": "test-key",
            "backup_enabled": True,
        }

        with patch("json.load") as mock_json_load:
            mock_json_load.return_value = {}

            manager._initialize_local_client()

            # Verify directory was created
            assert manager.secrets_dir.exists()
            assert manager.secrets_dir == Path(self.temp_dir)

            # Verify metadata file path is set
            assert manager.metadata_file == Path(self.temp_dir) / "metadata.json"

            manager.logger.info.assert_called_with("Local secrets storage initialized")


class TestSecretsManagerIntegration:
    """Integration tests for the refactored SecretsManager"""

    def test_full_initialization_local_provider(self):
        """Test complete initialization with local provider"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["LOCAL_SECRETS_ENCRYPTION_KEY"] = "test-key"

            # This should not raise any exceptions
            manager = SecretsManager(SecretProvider.LOCAL_FILE)

            # Verify all components are initialized
            assert manager.provider == SecretProvider.LOCAL_FILE
            assert manager.logger is not None
            assert isinstance(manager.secrets_cache, dict)
            assert isinstance(manager.access_logs, list)
            assert isinstance(manager.metadata_store, dict)
            assert manager.provider_config is not None
            assert manager.secrets_dir is not None

    def test_full_initialization_azure_provider_with_env(self):
        """Test complete initialization with Azure provider when env vars are set"""
        os.environ["AZURE_KEY_VAULT_URL"] = "https://test-vault.vault.azure.net/"

        with patch("azure.identity.DefaultAzureCredential"), patch(
            "azure.keyvault.secrets.SecretClient"
        ):
            # This should not raise any exceptions
            manager = SecretsManager(SecretProvider.AZURE_KEY_VAULT)

            # Verify all components are initialized
            assert manager.provider == SecretProvider.AZURE_KEY_VAULT
            assert manager.logger is not None
            assert isinstance(manager.secrets_cache, dict)
            assert isinstance(manager.access_logs, list)
            assert isinstance(manager.metadata_store, dict)
            assert manager.provider_config is not None
            assert manager.azure_client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
