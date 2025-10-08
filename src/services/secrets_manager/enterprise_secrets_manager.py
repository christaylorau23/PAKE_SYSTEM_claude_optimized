#!/usr/bin/env python3
"""Enterprise Secrets Manager
PAKE System - Phase 4 Implementation.

This module provides enterprise-grade secrets management with multiple backends
including HashiCorp Vault, Azure Key Vault, and AWS Secrets Manager.
"""

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
import os
from typing import Any

from .vault_client import PAKESecretsManager, create_vault_config_from_env

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecretsBackend(Enum):
    """Supported secrets backends."""

    VAULT = "vault"
    AZURE_KEY_VAULT = "azure_key_vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    ENVIRONMENT = "environment"


@dataclass
class SecretInfo:
    """Secret information."""

    name: str
    value: str
    backend: SecretsBackend
    path: str
    version: str | None = None
    created_time: str | None = None
    updated_time: str | None = None


class SecretsBackendInterface(ABC):
    """Interface for secrets backends."""

    @abstractmethod
    async def get_secret(self, name: str) -> str | None:
        """Get secret by name."""

    @abstractmethod
    async def set_secret(self, name: str, value: str) -> bool:
        """Set secret value."""

    @abstractmethod
    async def list_secrets(self) -> list[str]:
        """List all secret names."""

    @abstractmethod
    async def delete_secret(self, name: str) -> bool:
        """Delete secret."""


class VaultSecretsBackend(SecretsBackendInterface):
    """HashiCorp Vault secrets backend."""

    def __init__(self, vault_config: dict[str, Any] | None = None) -> None:
        self.vault_config = vault_config or create_vault_config_from_env()
        self.secrets_manager: PAKESecretsManager | None = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        self.secrets_manager = PAKESecretsManager(self.vault_config)
        await self.secrets_manager.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        if self.secrets_manager:
            await self.secrets_manager.__aexit__(exc_type, exc_val, exc_tb)

    async def get_secret(self, name: str) -> str | None:
        """Get secret from Vault."""
        if not self.secrets_manager:
            msg = "Vault backend not initialized"
            raise RuntimeError(msg)

        # Map secret names to Vault paths
        vault_paths = {
            "SECRET_KEY": "pake-system/jwt-secret",
            "JWT_SECRET": "pake-system/jwt-secret",
            "DATABASE_URL": "pake-system/database-url",
            "REDIS_URL": "pake-system/redis-url",
            "API_KEY": "pake-system/api-key",
            "DB_PASSWORD": "pake-system/db-password",
            "REDIS_PASSWORD": "pake-system/redis-password",
            "ANTHROPIC_API_KEY": "pake-system/anthropic-api-key",
            "GEMINI_API_KEY": "pake-system/gemini-api-key",
            "WEBHOOK_SECRET": "pake-system/webhook-secret",
        }

        vault_path = vault_paths.get(
            name, f"pake-system/{name.lower().replace('_', '-')}"
        )
        return await self.secrets_manager.vault_client.get_secret(vault_path, "value")

    async def set_secret(self, name: str, value: str) -> bool:
        """Set secret in Vault."""
        if not self.secrets_manager:
            msg = "Vault backend not initialized"
            raise RuntimeError(msg)

        vault_path = f"pake-system/{name.lower().replace('_', '-')}"
        return await self.secrets_manager.vault_client.set_secret(
            vault_path, {"value": value}
        )

    async def list_secrets(self) -> list[str]:
        """List secrets in Vault."""
        if not self.secrets_manager:
            msg = "Vault backend not initialized"
            raise RuntimeError(msg)

        return await self.secrets_manager.vault_client.list_secrets("pake-system/")

    async def delete_secret(self, name: str) -> bool:
        """Delete secret from Vault."""
        if not self.secrets_manager:
            msg = "Vault backend not initialized"
            raise RuntimeError(msg)

        vault_path = f"pake-system/{name.lower().replace('_', '-')}"
        return await self.secrets_manager.vault_client.delete_secret(vault_path)


class AzureKeyVaultBackend(SecretsBackendInterface):
    """Azure Key Vault secrets backend."""

    def __init__(
        self, vault_url: str, client_id: str, client_secret: str, tenant_id: str
    ) -> None:
        self.vault_url = vault_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self._client = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        try:
            from azure.identity.aio import ClientSecretCredential
            from azure.keyvault.secrets.aio import SecretClient

            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            self._client = SecretClient(vault_url=self.vault_url, credential=credential)
            return self
        except ImportError:
            logger.error("Azure Key Vault SDK not installed")
            msg = "Azure Key Vault SDK not available"
            raise RuntimeError(msg)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.close()

    async def get_secret(self, name: str) -> str | None:
        """Get secret from Azure Key Vault."""
        if not self._client:
            msg = "Azure Key Vault backend not initialized"
            raise RuntimeError(msg)

        try:
            secret = await self._client.get_secret(name)
            return secret.value
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to get secret %s: %s", name, e)
            return None

    async def set_secret(self, name: str, value: str) -> bool:
        """Set secret in Azure Key Vault."""
        if not self._client:
            msg = "Azure Key Vault backend not initialized"
            raise RuntimeError(msg)

        try:
            await self._client.set_secret(name, value)
            return True
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to set secret %s: %s", name, e)
            return False

    async def list_secrets(self) -> list[str]:
        """List secrets in Azure Key Vault."""
        if not self._client:
            msg = "Azure Key Vault backend not initialized"
            raise RuntimeError(msg)

        try:
            secrets = []
            async for secret_properties in self._client.list_properties_of_secrets():
                secrets.append(secret_properties.name)
            return secrets
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to list secrets: %s", e)
            return []

    async def delete_secret(self, name: str) -> bool:
        """Delete secret from Azure Key Vault."""
        if not self._client:
            msg = "Azure Key Vault backend not initialized"
            raise RuntimeError(msg)

        try:
            await self._client.begin_delete_secret(name)
            return True
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to delete secret %s: %s", name, e)
            return False


class AWSSecretsManagerBackend(SecretsBackendInterface):
    """AWS Secrets Manager backend."""

    def __init__(self, region: str) -> None:
        self.region = region
        self._client = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            self._client = boto3.client("secretsmanager", region_name=self.region)
            return self
        except ImportError:
            logger.error("AWS SDK not installed")
            msg = "AWS SDK not available"
            raise RuntimeError(msg)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        # boto3 client doesn't need explicit cleanup

    async def get_secret(self, name: str) -> str | None:
        """Get secret from AWS Secrets Manager."""
        if not self._client:
            msg = "AWS Secrets Manager backend not initialized"
            raise RuntimeError(msg)

        try:
            response = self._client.get_secret_value(SecretId=name)
            return response["SecretString"]
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to get secret %s: %s", name, e)
            return None

    async def set_secret(self, name: str, value: str) -> bool:
        """Set secret in AWS Secrets Manager."""
        if not self._client:
            msg = "AWS Secrets Manager backend not initialized"
            raise RuntimeError(msg)

        try:
            self._client.put_secret_value(SecretId=name, SecretString=value)
            return True
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to set secret %s: %s", name, e)
            return False

    async def list_secrets(self) -> list[str]:
        """List secrets in AWS Secrets Manager."""
        if not self._client:
            msg = "AWS Secrets Manager backend not initialized"
            raise RuntimeError(msg)

        try:
            response = self._client.list_secrets()
            return [secret["Name"] for secret in response["SecretList"]]
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to list secrets: %s", e)
            return []

    async def delete_secret(self, name: str) -> bool:
        """Delete secret from AWS Secrets Manager."""
        if not self._client:
            msg = "AWS Secrets Manager backend not initialized"
            raise RuntimeError(msg)

        try:
            self._client.delete_secret(SecretId=name, ForceDeleteWithoutRecovery=True)
            return True
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to delete secret %s: %s", name, e)
            return False


class EnvironmentSecretsBackend(SecretsBackendInterface):
    """Environment variables secrets backend."""

    async def get_secret(self, name: str) -> str | None:
        """Get secret from environment variables."""
        return os.getenv(name)

    async def set_secret(self, name: str, value: str) -> bool:
        """Set secret in environment variables."""
        os.environ[name] = value
        return True

    async def list_secrets(self) -> list[str]:
        """List secrets from environment variables."""
        # Return common secret names
        common_secrets = [
            "SECRET_KEY",
            "JWT_SECRET",
            "DATABASE_URL",
            "REDIS_URL",
            "API_KEY",
            "DB_PASSWORD",
            "REDIS_PASSWORD",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "WEBHOOK_SECRET",
        ]
        return [name for name in common_secrets if os.getenv(name)]

    async def delete_secret(self, name: str) -> bool:
        """Delete secret from environment variables."""
        if name in os.environ:
            del os.environ[name]
            return True
        return False


class EnterpriseSecretsManager:
    """Enterprise secrets manager with multiple backend support."""

    def __init__(self, primary_backend: SecretsBackend) -> None:
        self.primary_backend = primary_backend
        self.backends: dict[SecretsBackend, SecretsBackendInterface] = {}
        self._current_backend: SecretsBackendInterface | None = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        await self._initialize_backend()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        if self._current_backend and hasattr(self._current_backend, "__aexit__"):
            await self._current_backend.__aexit__(exc_type, exc_val, exc_tb)

    async def _initialize_backend(self) -> None:
        """Initialize the primary backend."""
        logger.info("Initializing %s backend", self.primary_backend.value)

        if self.primary_backend == SecretsBackend.VAULT:
            self._current_backend = VaultSecretsBackend()
        elif self.primary_backend == SecretsBackend.AZURE_KEY_VAULT:
            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            client_id = os.getenv("AZURE_CLIENT_ID")
            client_secret = os.getenv("AZURE_CLIENT_SECRET")
            tenant_id = os.getenv("AZURE_TENANT_ID")

            if not all([vault_url, client_id, client_secret, tenant_id]):
                msg = "Azure Key Vault credentials not provided"
                raise RuntimeError(msg)

            self._current_backend = AzureKeyVaultBackend(
                vault_url, client_id, client_secret, tenant_id
            )
        elif self.primary_backend == SecretsBackend.AWS_SECRETS_MANAGER:
            region = os.getenv("AWS_REGION", "us-east-1")
            self._current_backend = AWSSecretsManagerBackend(region)
        elif self.primary_backend == SecretsBackend.ENVIRONMENT:
            self._current_backend = EnvironmentSecretsBackend()
        else:
            msg = f"Unsupported backend: {self.primary_backend}"
            raise ValueError(msg)

        if hasattr(self._current_backend, "__aenter__"):
            await self._current_backend.__aenter__()

    async def get_secret(
        self, name: str, backend: SecretsBackend | None = None
    ) -> str | None:
        """Get secret from specified backend or primary backend."""
        if backend and backend != self.primary_backend:
            # Use fallback backend
            fallback_backend = await self._get_fallback_backend(backend)
            if fallback_backend:
                return await fallback_backend.get_secret(name)

        if not self._current_backend:
            msg = "No backend initialized"
            raise RuntimeError(msg)

        return await self._current_backend.get_secret(name)

    async def set_secret(
        self, name: str, value: str, backend: SecretsBackend | None = None
    ) -> bool:
        """Set secret in specified backend or primary backend."""
        if backend and backend != self.primary_backend:
            # Use fallback backend
            fallback_backend = await self._get_fallback_backend(backend)
            if fallback_backend:
                return await fallback_backend.set_secret(name, value)

        if not self._current_backend:
            msg = "No backend initialized"
            raise RuntimeError(msg)

        return await self._current_backend.set_secret(name, value)

    async def list_secrets(self, backend: SecretsBackend | None = None) -> list[str]:
        """List secrets from specified backend or primary backend."""
        if backend and backend != self.primary_backend:
            # Use fallback backend
            fallback_backend = await self._get_fallback_backend(backend)
            if fallback_backend:
                return await fallback_backend.list_secrets()

        if not self._current_backend:
            msg = "No backend initialized"
            raise RuntimeError(msg)

        return await self._current_backend.list_secrets()

    async def delete_secret(
        self, name: str, backend: SecretsBackend | None = None
    ) -> bool:
        """Delete secret from specified backend or primary backend."""
        if backend and backend != self.primary_backend:
            # Use fallback backend
            fallback_backend = await self._get_fallback_backend(backend)
            if fallback_backend:
                return await fallback_backend.delete_secret(name)

        if not self._current_backend:
            msg = "No backend initialized"
            raise RuntimeError(msg)

        return await self._current_backend.delete_secret(name)

    async def _get_fallback_backend(
        self, backend: SecretsBackend
    ) -> SecretsBackendInterface | None:
        """Get fallback backend instance."""
        if backend not in self.backends:
            if backend == SecretsBackend.VAULT:
                self.backends[backend] = VaultSecretsBackend()
            elif backend == SecretsBackend.AZURE_KEY_VAULT:
                vault_url = os.getenv("AZURE_KEY_VAULT_URL")
                client_id = os.getenv("AZURE_CLIENT_ID")
                client_secret = os.getenv("AZURE_CLIENT_SECRET")
                tenant_id = os.getenv("AZURE_TENANT_ID")

                if all([vault_url, client_id, client_secret, tenant_id]):
                    self.backends[backend] = AzureKeyVaultBackend(
                        vault_url, client_id, client_secret, tenant_id
                    )
            elif backend == SecretsBackend.AWS_SECRETS_MANAGER:
                region = os.getenv("AWS_REGION", "us-east-1")
                self.backends[backend] = AWSSecretsManagerBackend(region)
            elif backend == SecretsBackend.ENVIRONMENT:
                self.backends[backend] = EnvironmentSecretsBackend()

        return self.backends.get(backend)

    async def export_all_secrets(self) -> dict[str, str]:
        """Export all secrets as environment variables."""
        logger.info("Exporting all secrets from enterprise secrets manager")

        secrets = {}
        secret_names = await self.list_secrets()

        for name in secret_names:
            value = await self.get_secret(name)
            if value:
                secrets[name] = value

        logger.info("Exported %s secrets", len(secrets))
        return secrets

    async def sync_secrets_to_environment(self) -> None:
        """Sync all secrets to environment variables."""
        secrets = await self.export_all_secrets()

        for name, value in secrets.items():
            os.environ[name] = value

        logger.info("Synced %s secrets to environment variables", len(secrets))


def create_enterprise_secrets_manager(
    backend: SecretsBackend | None = None,
) -> EnterpriseSecretsManager:
    """Create enterprise secrets manager with specified backend."""
    if backend is None:
        # Determine backend from environment
        if os.getenv("VAULT_ADDR"):
            backend = SecretsBackend.VAULT
        elif os.getenv("AZURE_KEY_VAULT_URL"):
            backend = SecretsBackend.AZURE_KEY_VAULT
        elif os.getenv("AWS_REGION"):
            backend = SecretsBackend.AWS_SECRETS_MANAGER
        else:
            backend = SecretsBackend.ENVIRONMENT

    return EnterpriseSecretsManager(backend)


async def main(self) -> None:
    """Main function for testing enterprise secrets manager."""
    logger.info("Testing Enterprise Secrets Manager...")

    try:
        async with create_enterprise_secrets_manager() as secrets_manager:
            # Test secret retrieval
            jwt_secret = await secrets_manager.get_secret("SECRET_KEY")
            if jwt_secret:
                logger.info("✅ Successfully retrieved SECRET_KEY")
            else:
                logger.warning("❌ Failed to retrieve SECRET_KEY")

            # Export all secrets
            all_secrets = await secrets_manager.export_all_secrets()
            logger.info("✅ Exported %s secrets", len(all_secrets))

            # Print secrets (without values for security)
            for key in all_secrets:
                logger.info("  - %s: [REDACTED_SECRET]", key)

    except (ValueError, RuntimeError) as e:
        logger.error("❌ Enterprise secrets manager test failed: %s", e)
        return 1

    logger.info("✅ Enterprise secrets manager test completed successfully")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
