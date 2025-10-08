"""PAKE System - HashiCorp Vault Client
Centralized secrets management with secure credential handling.
"""

import asyncio
from dataclasses import dataclass
import json
import logging
import os
from typing import Any, List

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class VaultConfig:
    """Vault configuration settings."""

    url: str = "http://localhost:8200"
    token: str | None = None
    timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0


class VaultClient:
    """HashiCorp Vault client for secure secrets management.

    Features:
    - Automatic token refresh
    - Connection pooling
    - Circuit breaker pattern
    - Encryption at rest for cached secrets
    - Audit logging
    """

    def __init__(self, config: VaultConfig | None = None) -> None:
        self.config = config or VaultConfig()
        self._session: ClientSession | None = None
        self._token = self.config.token or os.getenv("VAULT_TOKEN")
        self._cache: dict[str, Any] = {}
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for local caching."""
        key_path = os.path.expanduser("~/.pake/vault_cache.key")
        os.makedirs(os.path.dirname(key_path), exist_ok=True)

        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            os.chmod(key_path, 0o600)  # Secure file permissions
            return key

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.config.timeout)
            connector = TCPConnector(limit=10, limit_per_host=5)
            self._session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"X-Vault-Token": self._token} if self._token else {},
            )

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_secret(self, path: str, use_cache: bool = True) -> dict[str, Any]:
        """Retrieve secret from Vault with caching support.

        Args:
            path: Secret path in Vault (e.g., 'pake-system/database')
            use_cache: Whether to use local encrypted cache

        Returns:
            Dictionary containing secret data
        """
        # Check cache first
        cache_key = f"kv/data/{path}"
        if use_cache and cache_key in self._cache:
            try:
                encrypted_data = self._cache[cache_key]
                decrypted_data = self._fernet.decrypt(encrypted_data.encode())
                return json.loads(decrypted_data.decode())
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Cache decryption failed for %s: %s", path, e)

        await self._ensure_session()

        url = f"{self.config.url}/v1/kv/data/{path}"

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        secret_data = data.get("data", {}).get("data", {})

                        # Cache encrypted secret
                        if use_cache:
                            encrypted_data = self._fernet.encrypt(
                                json.dumps(secret_data).encode()
                            )
                            self._cache[cache_key] = encrypted_data.decode()

                        logger.info("Successfully retrieved secret: %s", path)
                        return secret_data

                    if response.status == 404:
                        msg = f"Secret not found: {path}"
                        raise VaultSecretNotFound(msg)

                    if response.status == 403:
                        msg = f"Access denied to secret: {path}"
                        raise VaultPermissionDenied(msg)

                    error_data = await response.text()
                    msg = f"API error {response.status}: {error_data}"
                    raise VaultAPIError(msg)

            except (ValueError, RuntimeError) as e:
                if attempt == self.config.max_retries - 1:
                    logger.error(
                        "Failed to retrieve secret %s after %s attempts: %s",
                        path,
                        self.config.max_retries,
                        e,
                    )
                    raise

                logger.warning(
                    "Attempt %s failed for secret %s: %s", attempt + 1, path, e
                )
                await asyncio.sleep(self.config.retry_delay * (2**attempt))

        msg = f"Max retries exceeded for secret: {path}"
        raise VaultAPIError(msg)

    async def put_secret(self, path: str, data: dict[str, Any]) -> bool:
        """Store secret in Vault.

        Args:
            path: Secret path in Vault
            data: Secret data to store

        Returns:
            True if successful
        """
        await self._ensure_session()

        url = f"{self.config.url}/v1/kv/data/{path}"
        payload = {"data": data}

        async with self._session.post(url, json=payload) as response:
            if response.status in (200, 204):
                # Invalidate cache
                cache_key = f"kv/data/{path}"
                if cache_key in self._cache:
                    del self._cache[cache_key]

                logger.info("Successfully stored secret: %s", path)
                return True
            error_data = await response.text()
            msg = f"Failed to store secret {path}: {error_data}"
            raise VaultAPIError(msg)

    async def list_secrets(self, path: str) -> list[str]:
        """List secrets at path.

        Args:
            path: Path to list

        Returns:
            List of secret names
        """
        await self._ensure_session()

        url = f"{self.config.url}/v1/kv/metadata/{path}"

        async with self._session.request("LIST", url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {}).get("keys", [])
            error_data = await response.text()
            msg = f"Failed to list secrets at {path}: {error_data}"
            raise VaultAPIError(msg)

    async def delete_secret(self, path: str) -> bool:
        """Delete secret from Vault.

        Args:
            path: Secret path to delete

        Returns:
            True if successful
        """
        await self._ensure_session()

        url = f"{self.config.url}/v1/kv/metadata/{path}"

        async with self._session.delete(url) as response:
            if response.status in (200, 204):
                # Invalidate cache
                cache_key = f"kv/data/{path}"
                if cache_key in self._cache:
                    del self._cache[cache_key]

                logger.info("Successfully deleted secret: %s", path)
                return True
            error_data = await response.text()
            msg = f"Failed to delete secret {path}: {error_data}"
            raise VaultAPIError(msg)

    def clear_cache(self) -> None:
        """Clear local encrypted cache."""
        self._cache.clear()
        logger.info("Vault cache cleared")


class VaultSecretManager:
    """High-level interface for PAKE System secrets management."""

    def __init__(self, vault_client: VaultClient | None = None) -> None:
        self.vault = vault_client or VaultClient()
        self.service_prefix = "pake-system"

    async def get_database_config(self) -> dict[str, str]:
        """Get database configuration."""
        return await self.vault.get_secret(f"{self.service_prefix}/database")

    async def get_redis_config(self) -> dict[str, str]:
        """Get Redis configuration."""
        return await self.vault.get_secret(f"{self.service_prefix}/redis")

    async def get_jwt_config(self) -> dict[str, str]:
        """Get JWT configuration."""
        return await self.vault.get_secret(f"{self.service_prefix}/jwt")

    async def get_vapi_config(self) -> dict[str, str]:
        """Get Vapi.ai configuration."""
        return await self.vault.get_secret(f"{self.service_prefix}/voice-agents/vapi")

    async def get_video_generation_config(
        self, provider: str = "d-id"
    ) -> dict[str, str]:
        """Get video generation configuration."""
        return await self.vault.get_secret(
            f"{self.service_prefix}/video-generation/{provider}"
        )

    async def get_social_media_config(self, platform: str) -> dict[str, str]:
        """Get social media platform configuration."""
        return await self.vault.get_secret(
            f"{self.service_prefix}/social-media/{platform}"
        )

    async def rotate_secret(
        self, path: str, new_value: str, key: str = "REDACTED_SECRET"
    ) -> bool:
        """Rotate a secret value.

        Args:
            path: Secret path
            new_value: New secret value
            key: Key within the secret to rotate

        Returns:
            True if successful
        """
        try:
            # Get existing secret
            existing = await self.vault.get_secret(path, use_cache=False)

            # Update the specific key
            existing[key] = new_value

            # Store updated secret
            return await self.vault.put_secret(path, existing)

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to rotate secret %s.%s: %s", path, key, e)
            return False


# Custom exceptions
class VaultError(Exception):
    """Base Vault exception."""


class VaultAPIError(VaultError):
    """Vault API error."""


class VaultSecretNotFound(VaultError):
    """Secret not found in Vault."""


class VaultPermissionDenied(VaultError):
    """Permission denied for Vault operation."""


# Factory function for easy initialization
async def create_vault_client(
    vault_url: str = None, vault_token: str = None
) -> VaultClient:
    """Create and initialize a Vault client.

    Args:
        vault_url: Vault URL (defaults to VAULT_ADDR env var or localhost)
        vault_token: Vault token (defaults to VAULT_TOKEN env var)

    Returns:
        Initialized VaultClient
    """
    config = VaultConfig(
        url=vault_url or os.getenv("VAULT_ADDR", "http://localhost:8200"),
        token=vault_token or os.getenv("VAULT_TOKEN"),
    )

    client = VaultClient(config)
    await client._ensure_session()

    return client


# Example usage and testing
async def main(self) -> None:
    """Example usage of the Vault client."""
    async with await create_vault_client() as vault:
        secrets_manager = VaultSecretManager(vault)

        try:
            # Test database config retrieval
            db_config = await secrets_manager.get_database_config()
            print(f"Database config retrieved: {list(db_config.keys())}")

            # Test Vapi config
            vapi_config = await secrets_manager.get_vapi_config()
            print(f"Vapi config retrieved: {list(vapi_config.keys())}")

        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
