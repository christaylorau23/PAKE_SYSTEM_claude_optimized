#!/usr/bin/env python3
"""HashiCorp Vault Integration with JWT/OIDC Authentication
PAKE System - Phase 4 Implementation.

This module provides enterprise-grade secrets management using HashiCorp Vault
with JWT/OIDC authentication for GitHub Actions integration.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VaultAuthMethod(Enum):
    """Vault authentication methods."""

    JWT_OIDC = "jwt"
    TOKEN = "token"
    APPROLE = "approle"


@dataclass
class VaultConfig:
    """Vault configuration."""

    vault_addr: str
    vault_role_id: str | None = None
    vault_secret_id: str | None = None
    vault_token: str | None = None
    jwt_token: str | None = None
    auth_method: VaultAuthMethod = VaultAuthMethod.JWT_OIDC
    mount_path: str = "secret"
    namespace: str | None = None


@dataclass
class SecretMetadata:
    """Secret metadata."""

    name: str
    path: str
    version: int | None = None
    created_time: str | None = None
    updated_time: str | None = None


class VaultClient:
    """HashiCorp Vault client with JWT/OIDC authentication."""

    def __init__(self) -> None:
        self.config = config
        self.session: aiohttp.ClientSession | None = None
        self.token: str | None = None
        self.token_expiry: float | None = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self

    async def __aexit__(self) -> None:
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def authenticate(self) -> None:
        """Authenticate with Vault using the configured method."""
        logger.info(
            "Authenticating with Vault using %s method", self.config.auth_method.value
        )

        if self.config.auth_method == VaultAuthMethod.JWT_OIDC:
            await self._authenticate_jwt_oidc()
        elif self.config.auth_method == VaultAuthMethod.APPROLE:
            await self._authenticate_approle()
        elif self.config.auth_method == VaultAuthMethod.TOKEN:
            self.token = self.config.vault_token
        else:
            msg = f"Unsupported authentication method: {self.config.auth_method}"
            raise ValueError(msg)

        if not self.token:
            msg = "Failed to obtain Vault token"
            raise RuntimeError(msg)

        logger.info("Successfully authenticated with Vault")

    async def _authenticate_jwt_oidc(self) -> None:
        """Authenticate using JWT/OIDC method."""
        if not self.config.jwt_token:
            # Try to get JWT token from GitHub Actions
            self.config.jwt_token = await self._get_github_oidc_token()

        if not self.config.jwt_token:
            msg = "No JWT token available for authentication"
            raise RuntimeError(msg)

        auth_data = {"role": "pake-system-role", "jwt": self.config.jwt_token}

        response = await self._make_request(
            "POST", "/v1/auth/jwt/login", json=auth_data
        )

        if response and "auth" in response:
            self.token = response["auth"]["client_token"]
            if "lease_duration" in response["auth"]:
                self.token_expiry = time.time() + response["auth"]["lease_duration"]
        else:
            msg = "Failed to authenticate with JWT/OIDC"
            raise RuntimeError(msg)

    async def _authenticate_approle(self) -> None:
        """Authenticate using AppRole method."""
        if not self.config.vault_role_id or not self.config.vault_secret_id:
            msg = "AppRole credentials not provided"
            raise RuntimeError(msg)

        auth_data = {
            "role_id": self.config.vault_role_id,
            "secret_id": self.config.vault_secret_id,
        }

        response = await self._make_request(
            "POST", "/v1/auth/approle/login", json=auth_data
        )

        if response and "auth" in response:
            self.token = response["auth"]["client_token"]
            if "lease_duration" in response["auth"]:
                self.token_expiry = time.time() + response["auth"]["lease_duration"]
        else:
            msg = "Failed to authenticate with AppRole"
            raise RuntimeError(msg)

    async def _get_github_oidc_token(self) -> str | None:
        """Get OIDC token from GitHub Actions."""
        if not os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
            logger.warning("No GitHub Actions OIDC token available")
            return None

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"bearer {os.getenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN')}"
                }

                url = f"{os.getenv('ACTIONS_ID_TOKEN_REQUEST_URL')}&audience=vault"

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("value")
                    logger.error("Failed to get OIDC token: %s", response.status)
                    return None
        except Exception as e:
            logger.error("Error getting OIDC token: %s", e)
            return None

    async def _make_request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict | None:
        """Make authenticated request to Vault."""
        if not self.session:
            msg = "Vault client not initialized"
            raise RuntimeError(msg)

        # Check token expiry
        if self.token_expiry and time.time() >= self.token_expiry:
            logger.info("Vault token expired, re-authenticating...")
            await self.authenticate()

        url = f"{self.config.vault_addr.rstrip('/')}{path}"
        headers = {"X-Vault-Token": self.token, "Content-Type": "application/json"}

        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace

        try:
            async with self.session.request(
                method, url, headers=headers, json=json_data, params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 404:
                    logger.warning("Resource not found: %s", path)
                    return None
                error_text = await response.text()
                logger.error(
                    "Vault request failed: %s - %s", response.status, error_text
                )
                return None
        except Exception as e:
            logger.error("Error making Vault request: %s", e)
            return None

    async def get_secret(self, path: str, key: str | None = None) -> Any | None:
        """Get secret from Vault."""
        logger.info("Retrieving secret: %s", path)

        response = await self._make_request(
            "GET", f"/v1/{self.config.mount_path}/data/{path}"
        )

        if response and "data" in response:
            data = response["data"]["data"]
            if key:
                return data.get(key)
            return data
        logger.warning("Secret not found: %s", path)
        return None

    async def set_secret(self, path: str, data: dict[str, Any]) -> bool:
        """Set secret in Vault."""
        logger.info("Setting secret: %s", path)

        payload = {"data": data}
        response = await self._make_request(
            "POST", f"/v1/{self.config.mount_path}/data/{path}", json=payload
        )

        return response is not None

    async def list_secrets(self, path: str = "") -> list[str]:
        """List secrets in Vault."""
        logger.info("Listing secrets: %s", path)

        response = await self._make_request(
            "LIST", f"/v1/{self.config.mount_path}/metadata/{path}"
        )

        if response and "data" in response:
            return response["data"].get("keys", [])
        return []

    async def delete_secret(self, path: str) -> bool:
        """Delete secret from Vault."""
        logger.info("Deleting secret: %s", path)

        response = await self._make_request(
            "DELETE", f"/v1/{self.config.mount_path}/metadata/{path}"
        )

        return response is not None

    async def get_secret_metadata(self, path: str) -> SecretMetadata | None:
        """Get secret metadata."""
        response = await self._make_request(
            "GET", f"/v1/{self.config.mount_path}/metadata/{path}"
        )

        if response and "data" in response:
            data = response["data"]
            return SecretMetadata(
                name=path.split("/")[-1],
                path=path,
                version=data.get("current_version"),
                created_time=data.get("created_time"),
                updated_time=data.get("updated_time"),
            )
        return None


class PAKESecretsManager:
    """PAKE System secrets manager using HashiCorp Vault."""

    def __init__(self) -> None:
        self.vault_config = vault_config
        self.vault_client: VaultClient | None = None

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        self.vault_client = VaultClient(self.vault_config)
        await self.vault_client.__aenter__()
        return self

    async def __aexit__(self) -> None:
        """Async context manager exit."""
        if self.vault_client:
            await self.vault_client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_jwt_secret(self) -> str | None:
        """Get JWT secret."""
        return await self.vault_client.get_secret("pake-system/jwt-secret", "value")

    async def get_database_url(self) -> str | None:
        """Get database URL."""
        return await self.vault_client.get_secret("pake-system/database-url", "value")

    async def get_redis_url(self) -> str | None:
        """Get Redis URL."""
        return await self.vault_client.get_secret("pake-system/redis-url", "value")

    async def get_api_key(self) -> str | None:
        """Get API key."""
        return await self.vault_client.get_secret("pake-system/api-key", "value")

    async def get_db_password(self) -> str | None:
        """Get database password."""
        return await self.vault_client.get_secret("pake-system/db-password", "value")

    async def get_redis_password(self) -> str | None:
        """Get Redis password."""
        return await self.vault_client.get_secret("pake-system/redis-password", "value")

    async def get_anthropic_api_key(self) -> str | None:
        """Get Anthropic API key."""
        return await self.vault_client.get_secret(
            "pake-system/anthropic-api-key", "value"
        )

    async def get_gemini_api_key(self) -> str | None:
        """Get Gemini API key."""
        return await self.vault_client.get_secret("pake-system/gemini-api-key", "value")

    async def get_webhook_secret(self) -> str | None:
        """Get webhook secret."""
        return await self.vault_client.get_secret("pake-system/webhook-secret", "value")

    async def export_all_secrets(self) -> dict[str, str]:
        """Export all secrets as environment variables."""
        logger.info("Exporting all secrets from Vault")

        secrets = {}

        # Core secrets
        if jwt_secret := await self.get_jwt_secret():
            secrets["SECRET_KEY"] = jwt_secret
            secrets["JWT_SECRET"] = jwt_secret

        if db_url := await self.get_database_url():
            secrets["DATABASE_URL"] = db_url

        if redis_url := await self.get_redis_url():
            secrets["REDIS_URL"] = redis_url

        if api_key := await self.get_api_key():
            secrets["API_KEY"] = api_key

        if db_password := await self.get_db_password():
            secrets["DB_PASSWORD"] = db_password

        if redis_password := await self.get_redis_password():
            secrets["REDIS_PASSWORD"] = redis_password

        # API Keys
        if anthropic_key := await self.get_anthropic_api_key():
            secrets["ANTHROPIC_API_KEY"] = anthropic_key

        if gemini_key := await self.get_gemini_api_key():
            secrets["GEMINI_API_KEY"] = gemini_key

        # Webhook Security
        if webhook_secret := await self.get_webhook_secret():
            secrets["WEBHOOK_SECRET"] = webhook_secret

        logger.info("Exported %s secrets", len(secrets))
        return secrets


def create_vault_config_from_env() -> VaultConfig:
    """Create Vault configuration from environment variables."""
    vault_addr = os.getenv("VAULT_ADDR", "https://vault.pake-system.com")
    vault_role_id = os.getenv("VAULT_ROLE_ID")
    vault_secret_id = os.getenv("VAULT_SECRET_ID")
    vault_token = os.getenv("VAULT_TOKEN")

    # Determine authentication method
    if vault_token:
        auth_method = VaultAuthMethod.TOKEN
    elif vault_role_id and vault_secret_id:
        auth_method = VaultAuthMethod.APPROLE
    else:
        auth_method = VaultAuthMethod.JWT_OIDC

    return VaultConfig(
        vault_addr=vault_addr,
        vault_role_id=vault_role_id,
        vault_secret_id=vault_secret_id,
        vault_token=vault_token,
        auth_method=auth_method,
        mount_path=os.getenv("VAULT_MOUNT_PATH", "secret"),
        namespace=os.getenv("VAULT_NAMESPACE"),
    )


async def main(self) -> None:
    """Main function for testing Vault integration."""
    logger.info("Testing HashiCorp Vault integration...")

    try:
        config = create_vault_config_from_env()

        async with PAKESecretsManager(config) as secrets_manager:
            # Test secret retrieval
            jwt_secret = await secrets_manager.get_jwt_secret()
            if jwt_secret:
                logger.info("✅ Successfully retrieved JWT secret")
            else:
                logger.warning("❌ Failed to retrieve JWT secret")

            # Export all secrets
            all_secrets = await secrets_manager.export_all_secrets()
            logger.info("✅ Exported %s secrets", len(all_secrets))

            # Print secrets (without values for security)
            for key in all_secrets:
                logger.info("  - %s: [REDACTED_SECRET]", key)

    except Exception as e:
        logger.error("❌ Vault integration test failed: %s", e)
        return 1

    logger.info("✅ Vault integration test completed successfully")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
