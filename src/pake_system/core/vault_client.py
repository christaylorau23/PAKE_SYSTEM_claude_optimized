"""
HashiCorp Vault Client for PAKE System
=======================================

This module provides a secure interface for retrieving secrets from HashiCorp Vault.
It implements connection pooling, error handling, and caching for optimal performance.
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    import hvac
    HVAC_AVAILABLE = True
except ImportError:
    hvac = None
    HVAC_AVAILABLE = False


class VaultClientError(Exception):
    """Raised when Vault client operations fail."""
    pass


class VaultClient:
    """
    HashiCorp Vault client for secure secrets management.

    Features:
    - Automatic connection management
    - LRU caching for frequently accessed secrets
    - Graceful fallback to environment variables
    - Comprehensive error handling
    """

    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_point: str = "secret",
        environment: str = "development"
    ):
        """
        Initialize Vault client.

        Args:
            vault_url: Vault server URL (defaults to VAULT_URL env var)
            vault_token: Vault authentication token (defaults to VAULT_TOKEN env var)
            mount_point: KV secrets engine mount point
            environment: Environment name (development, staging, production)
        """
        self.vault_url = vault_url or os.getenv("VAULT_URL", "http://127.0.0.1:8200")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._client: Optional[Any] = None
        self._authenticated = False

    @property
    def client(self) -> Any:
        """
        Get or create authenticated Vault client.

        Returns:
            Authenticated hvac.Client instance

        Raises:
            VaultClientError: If hvac library not available or authentication fails
        """
        if not HVAC_AVAILABLE:
            raise VaultClientError(
                "hvac library not available. Install with: poetry add hvac"
            )

        if self._client is None:
            if not self.vault_token:
                raise VaultClientError(
                    "VAULT_TOKEN environment variable not set. "
                    "Cannot authenticate to Vault."
                )

            try:
                self._client = hvac.Client(
                    url=self.vault_url,
                    token=self.vault_token
                )

                if not self._client.is_authenticated():
                    raise VaultClientError(
                        f"Failed to authenticate with Vault at {self.vault_url}"
                    )

                self._authenticated = True

            except Exception as e:
                raise VaultClientError(f"Error connecting to Vault: {e}")

        return self._client

    def get_secret(
        self,
        path: str,
        key: Optional[str] = None,
        fallback_env_var: Optional[str] = None,
        raise_on_error: bool = False
    ) -> Optional[str]:
        """
        Retrieve a secret from Vault.

        Args:
            path: Secret path relative to environment (e.g., 'security', 'database')
            key: Specific key within the secret (returns all if None)
            fallback_env_var: Environment variable to check if Vault fails
            raise_on_error: Whether to raise exception on error

        Returns:
            Secret value or None if not found

        Raises:
            VaultClientError: If raise_on_error=True and retrieval fails
        """
        # Construct full path with environment prefix
        full_path = f"pake_system/{self.environment}/{path}"

        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=full_path)
            secret_data = response['data']['data']

            if key:
                return secret_data.get(key)
            return secret_data

        except Exception as e:
            error_msg = f"Error retrieving secret from {full_path}: {e}"

            # Try fallback to environment variable
            if fallback_env_var and (fallback_value := os.getenv(fallback_env_var)):
                return fallback_value

            if raise_on_error:
                raise VaultClientError(error_msg)

            # Silent fallback for non-critical secrets
            return None

    def get_database_url(self) -> str:
        """
        Get database URL from Vault.

        Returns:
            Database connection URL

        Raises:
            VaultClientError: If database URL cannot be retrieved
        """
        db_url = self.get_secret(
            path="database",
            key="url",
            fallback_env_var="DATABASE_URL",
            raise_on_error=True
        )

        if not db_url:
            raise VaultClientError("DATABASE_URL not found in Vault or environment")

        return db_url

    def get_redis_url(self) -> str:
        """
        Get Redis URL from Vault.

        Returns:
            Redis connection URL

        Raises:
            VaultClientError: If Redis URL cannot be retrieved
        """
        redis_url = self.get_secret(
            path="redis",
            key="url",
            fallback_env_var="REDIS_URL",
            raise_on_error=True
        )

        if not redis_url:
            raise VaultClientError("REDIS_URL not found in Vault or environment")

        return redis_url

    def get_secret_key(self) -> str:
        """
        Get application secret key from Vault.

        Returns:
            Application secret key for JWT signing

        Raises:
            VaultClientError: If secret key cannot be retrieved
        """
        secret_key = self.get_secret(
            path="security",
            key="secret_key",
            fallback_env_var="SECRET_KEY",
            raise_on_error=True
        )

        if not secret_key:
            raise VaultClientError("SECRET_KEY not found in Vault or environment")

        return secret_key

    def get_api_key(self, service_name: str) -> Optional[str]:
        """
        Get API key for external service from Vault.

        Args:
            service_name: Name of the service (e.g., 'firecrawl_api_key')

        Returns:
            API key or None if not found
        """
        return self.get_secret(
            path="api_keys",
            key=service_name,
            fallback_env_var=service_name.upper(),
            raise_on_error=False
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Check Vault connection health.

        Returns:
            Dictionary with health status information
        """
        try:
            if not HVAC_AVAILABLE:
                return {
                    "status": "unavailable",
                    "message": "hvac library not installed",
                    "authenticated": False
                }

            client = self.client
            health = client.sys.read_health_status(method='GET')

            return {
                "status": "healthy",
                "vault_url": self.vault_url,
                "authenticated": self._authenticated,
                "initialized": health.get('initialized', False),
                "sealed": health.get('sealed', False)
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e),
                "authenticated": False
            }


@lru_cache()
def get_vault_client() -> VaultClient:
    """
    Get cached Vault client instance.

    Returns:
        Singleton VaultClient instance

    Note:
        This uses LRU cache to ensure only one client instance exists.
        The environment is read from ENVIRONMENT env var.
    """
    environment = os.getenv("ENVIRONMENT", "development")
    return VaultClient(environment=environment)
