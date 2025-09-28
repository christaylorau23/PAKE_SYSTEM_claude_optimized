#!/usr/bin/env python3
"""
PAKE System Enterprise Secrets Manager
Production-grade secrets management with Azure Key Vault integration
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import json

logger = logging.getLogger(__name__)


class SecretType(Enum):
    """Types of secrets managed by the system"""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    JWT_SECRET = "jwt_secret"
    REDIS_PASSWORD = "redis_password"
    ENCRYPTION_KEY = "encryption_key"
    WEBHOOK_SECRET = "webhook_secret"


@dataclass
class SecretConfig:
    """Configuration for secret management"""
    vault_url: str
    secret_name: str
    secret_type: SecretType
    rotation_interval_days: int = 90
    fallback_env_var: Optional[str] = None
    required: bool = True


class EnterpriseSecretsManager:
    """Enterprise-grade secrets management with Azure Key Vault"""
    
    def __init__(self, vault_url: Optional[str] = None):
        """
        Initialize secrets manager
        
        Args:
            vault_url: Azure Key Vault URL. If None, will use environment variable
        """
        self.vault_url = vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        self.client: Optional[SecretClient] = None
        self._secrets_cache: Dict[str, str] = {}
        
        if not self.vault_url:
            logger.warning("AZURE_KEY_VAULT_URL not set. Using environment variables only.")
        else:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Azure Key Vault client"""
        try:
            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)
            logger.info(f"Connected to Azure Key Vault: {self.vault_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault client: {e}")
            self.client = None
    
    async def get_secret(self, config: SecretConfig) -> str:
        """
        Retrieve a secret with fail-fast security
        
        Args:
            config: Secret configuration
            
        Returns:
            Secret value
            
        Raises:
            ValueError: If secret is not found and required=True
        """
        # Try Azure Key Vault first
        if self.client:
            try:
                secret_value = await self._get_from_vault(config.secret_name)
                if secret_value:
                    self._secrets_cache[config.secret_name] = secret_value
                    logger.debug(f"Retrieved secret '{config.secret_name}' from Azure Key Vault")
                    return secret_value
            except Exception as e:
                logger.warning(f"Failed to retrieve secret from vault: {e}")
        
        # Try environment variable fallback
        if config.fallback_env_var:
            env_value = os.getenv(config.fallback_env_var)
            if env_value:
                logger.debug(f"Retrieved secret '{config.secret_name}' from environment variable")
                return env_value
        
        # Fail-fast if required
        if config.required:
            error_msg = (
                f"Required secret '{config.secret_name}' not found. "
                f"Please configure it in Azure Key Vault or set environment variable "
                f"'{config.fallback_env_var or config.secret_name}'. "
                f"This is a security requirement."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        return ""
    
    async def _get_from_vault(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}' from vault: {e}")
            return None
    
    async def rotate_secret(self, config: SecretConfig, new_value: str) -> bool:
        """
        Rotate a secret in Azure Key Vault
        
        Args:
            config: Secret configuration
            new_value: New secret value
            
        Returns:
            True if rotation successful
        """
        if not self.client:
            logger.error("Azure Key Vault client not initialized")
            return False
        
        try:
            # Store new secret version
            self.client.set_secret(config.secret_name, new_value)
            
            # Update cache
            self._secrets_cache[config.secret_name] = new_value
            
            logger.info(f"Successfully rotated secret '{config.secret_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to rotate secret '{config.secret_name}': {e}")
            return False
    
    async def validate_all_secrets(self, configs: Dict[str, SecretConfig]) -> Dict[str, bool]:
        """
        Validate all required secrets are available
        
        Args:
            configs: Dictionary of secret configurations
            
        Returns:
            Dictionary mapping secret names to validation results
        """
        results = {}
        
        for name, config in configs.items():
            try:
                await self.get_secret(config)
                results[name] = True
                logger.debug(f"Secret '{name}' validation: PASSED")
            except ValueError:
                results[name] = False
                logger.error(f"Secret '{name}' validation: FAILED")
        
        return results


# Predefined secret configurations for PAKE System
PAKE_SECRET_CONFIGS = {
    "api_key": SecretConfig(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        secret_name="pake-system-api-key",
        secret_type=SecretType.API_KEY,
        fallback_env_var="API_KEY",
        required=True
    ),
    "jwt_secret": SecretConfig(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        secret_name="pake-system-jwt-secret",
        secret_type=SecretType.JWT_SECRET,
        fallback_env_var="SECRET_KEY",
        required=True
    ),
    "database_password": SecretConfig(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        secret_name="pake-system-db-password",
        secret_type=SecretType.DATABASE_PASSWORD,
        fallback_env_var="DB_PASSWORD",
        required=True
    ),
    "redis_password": SecretConfig(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        secret_name="pake-system-redis-password",
        secret_type=SecretType.REDIS_PASSWORD,
        fallback_env_var="REDIS_PASSWORD",
        required=True
    ),
    "n8n_password": SecretConfig(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        secret_name="pake-system-n8n-password",
        secret_type=SecretType.API_KEY,
        fallback_env_var="N8N_PASSWORD",
        required=True
    ),
    "neo4j_password": SecretConfig(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        secret_name="pake-system-neo4j-password",
        secret_type=SecretType.DATABASE_PASSWORD,
        fallback_env_var="NEO4J_PASSWORD",
        required=True
    )
}


async def initialize_secrets_manager() -> EnterpriseSecretsManager:
    """Initialize and validate secrets manager"""
    manager = EnterpriseSecretsManager()
    
    # Validate all required secrets
    validation_results = await manager.validate_all_secrets(PAKE_SECRET_CONFIGS)
    
    failed_secrets = [name for name, passed in validation_results.items() if not passed]
    if failed_secrets:
        raise ValueError(
            f"Failed to validate required secrets: {', '.join(failed_secrets)}. "
            f"Please configure them in Azure Key Vault or environment variables."
        )
    
    logger.info("All required secrets validated successfully")
    return manager


# Convenience functions for common secrets
async def get_api_key() -> str:
    """Get API key with fail-fast security"""
    manager = EnterpriseSecretsManager()
    return await manager.get_secret(PAKE_SECRET_CONFIGS["api_key"])


async def get_jwt_secret() -> str:
    """Get JWT secret with fail-fast security"""
    manager = EnterpriseSecretsManager()
    return await manager.get_secret(PAKE_SECRET_CONFIGS["jwt_secret"])


async def get_database_password() -> str:
    """Get database password with fail-fast security"""
    manager = EnterpriseSecretsManager()
    return await manager.get_secret(PAKE_SECRET_CONFIGS["database_password"])


if __name__ == "__main__":
    async def main():
        """Test secrets manager"""
        try:
            manager = await initialize_secrets_manager()
            print("✅ Secrets manager initialized successfully")
            
            # Test secret retrieval
            api_key = await get_api_key()
            print(f"✅ API key retrieved: {api_key[:8]}...")
            
        except Exception as e:
            print(f"❌ Secrets manager initialization failed: {e}")
    
    asyncio.run(main())
