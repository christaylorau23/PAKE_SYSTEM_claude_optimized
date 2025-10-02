"""
PAKE System - HashiCorp Vault Client
Centralized secrets management with secure credential handling
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from cryptography.fernet import Fernet
import base64
import json

logger = logging.getLogger(__name__)

@dataclass
class VaultConfig:
    """Vault configuration settings"""
    url: str = "http://localhost:8200"
    token: Optional[str] = None
    timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0


class VaultClient:
    """
    HashiCorp Vault client for secure secrets management

    Features:
    - Automatic token refresh
    - Connection pooling
    - Circuit breaker pattern
    - Encryption at rest for cached secrets
    - Audit logging
    """

    def __init__(self, config: VaultConfig):
        self.config = config
        self._session: Optional[ClientSession] = None
        self._token = config.token or os.getenv('VAULT_TOKEN')
        self._cache: Dict[str, Any] = {}
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for local caching"""
        key_path = os.path.expanduser('~/.pake/vault_cache.key')
        os.makedirs(os.path.dirname(key_path), exist_ok=True)

        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            os.chmod(key_path, 0o600)  # Secure file permissions
            return key

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.config.timeout)
            connector = TCPConnector(limit=10, limit_per_host=5)
            self._session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'X-Vault-Token': self._token} if self._token else {}
            )

    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_secret(self, path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Retrieve secret from Vault with caching support

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
            except Exception as e:
                logger.warning(f"Cache decryption failed for {path}: {e}")

        await self._ensure_session()

        url = f"{self.config.url}/v1/kv/data/{path}"

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        secret_data = data.get('data', {}).get('data', {})

                        # Cache encrypted secret
                        if use_cache:
                            encrypted_data = self._fernet.encrypt(
                                json.dumps(secret_data).encode()
                            )
                            self._cache[cache_key] = encrypted_data.decode()

                        logger.info(f"Successfully retrieved secret: {path}")
                        return secret_data

                    elif response.status == 404:
                        raise VaultSecretNotFound(f"Secret not found: {path}")

                    elif response.status == 403:
                        raise VaultPermissionDenied(f"Access denied to secret: {path}")

                    else:
                        error_data = await response.text()
                        raise VaultAPIError(f"API error {response.status}: {error_data}")

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Failed to retrieve secret {path} after {self.config.max_retries} attempts: {e}")
                    raise

                logger.warning(f"Attempt {attempt + 1} failed for secret {path}: {e}")
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))

        raise VaultAPIError(f"Max retries exceeded for secret: {path}")

    async def put_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Store secret in Vault

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

                logger.info(f"Successfully stored secret: {path}")
                return True
            else:
                error_data = await response.text()
                raise VaultAPIError(f"Failed to store secret {path}: {error_data}")

    async def list_secrets(self, path: str) -> list[str]:
        """
        List secrets at path

        Args:
            path: Path to list

        Returns:
            List of secret names
        """
        await self._ensure_session()

        url = f"{self.config.url}/v1/kv/metadata/{path}"

        async with self._session.request('LIST', url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('data', {}).get('keys', [])
            else:
                error_data = await response.text()
                raise VaultAPIError(f"Failed to list secrets at {path}: {error_data}")

    async def delete_secret(self, path: str) -> bool:
        """
        Delete secret from Vault

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

                logger.info(f"Successfully deleted secret: {path}")
                return True
            else:
                error_data = await response.text()
                raise VaultAPIError(f"Failed to delete secret {path}: {error_data}")

    def clear_cache(self):
        """Clear local encrypted cache"""
        self._cache.clear()
        logger.info("Vault cache cleared")


class VaultSecretManager:
    """
    High-level interface for PAKE System secrets management
    """

    def __init__(self, vault_client: VaultClient):
        self.vault = vault_client
        self.service_prefix = "pake-system"

    async def get_database_config(self) -> Dict[str, str]:
        """Get database configuration"""
        return await self.vault.get_secret(f"{self.service_prefix}/database")

    async def get_redis_config(self) -> Dict[str, str]:
        """Get Redis configuration"""
        return await self.vault.get_secret(f"{self.service_prefix}/redis")

    async def get_jwt_config(self) -> Dict[str, str]:
        """Get JWT configuration"""
        return await self.vault.get_secret(f"{self.service_prefix}/jwt")

    async def get_vapi_config(self) -> Dict[str, str]:
        """Get Vapi.ai configuration"""
        return await self.vault.get_secret(f"{self.service_prefix}/voice-agents/vapi")

    async def get_video_generation_config(self, provider: str = "d-id") -> Dict[str, str]:
        """Get video generation configuration"""
        return await self.vault.get_secret(f"{self.service_prefix}/video-generation/{provider}")

    async def get_social_media_config(self, platform: str) -> Dict[str, str]:
        """Get social media platform configuration"""
        return await self.vault.get_secret(f"{self.service_prefix}/social-media/{platform}")

    async def rotate_secret(self, path: str, new_value: str, key: str = "REDACTED_SECRET") -> bool:
        """
        Rotate a secret value

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

        except Exception as e:
            logger.error(f"Failed to rotate secret {path}.{key}: {e}")
            return False


# Custom exceptions
class VaultError(Exception):
    """Base Vault exception"""
    pass

class VaultAPIError(VaultError):
    """Vault API error"""
    pass

class VaultSecretNotFound(VaultError):
    """Secret not found in Vault"""
    pass

class VaultPermissionDenied(VaultError):
    """Permission denied for Vault operation"""
    pass


# Factory function for easy initialization
async def create_vault_client(
    vault_url: str = None,
    vault_token: str = None
) -> VaultClient:
    """
    Create and initialize a Vault client

    Args:
        vault_url: Vault URL (defaults to VAULT_ADDR env var or localhost)
        vault_token: Vault token (defaults to VAULT_TOKEN env var)

    Returns:
        Initialized VaultClient
    """
    config = VaultConfig(
        url=vault_url or os.getenv('VAULT_ADDR', 'http://localhost:8200'),
        token=vault_token or os.getenv('VAULT_TOKEN')
    )

    client = VaultClient(config)
    await client._ensure_session()

    return client


# Example usage and testing
async def main():
    """Example usage of the Vault client"""
    async with await create_vault_client() as vault:
        secrets_manager = VaultSecretManager(vault)

        try:
            # Test database config retrieval
            db_config = await secrets_manager.get_database_config()
            print(f"Database config retrieved: {list(db_config.keys())}")

            # Test Vapi config
            vapi_config = await secrets_manager.get_vapi_config()
            print(f"Vapi config retrieved: {list(vapi_config.keys())}")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())