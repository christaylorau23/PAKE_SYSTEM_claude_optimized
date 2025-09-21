"""
Secure Secret Management Module for PAKE System
Supports multiple secret backends with fallback to environment variables
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SecretConfig:
    """Configuration for secret management"""
    backend: str = "env"  # env, aws, vault, azure
    region: str = "us-east-1"
    cache_ttl: int = 300  # 5 minutes
    auto_refresh: bool = True
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None

class SecretBackend(ABC):
    """Abstract base class for secret backends"""
    
    @abstractmethod
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Retrieve a secret value"""
        pass
    
    @abstractmethod
    async def get_secret_dict(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a secret as a dictionary (for JSON secrets)"""
        pass

class EnvironmentSecretBackend(SecretBackend):
    """Environment variable secret backend (development and production)"""
    
    def __init__(self, cache_ttl: int = 0):
        self.name = "Environment Variables"
        self.cache_ttl = cache_ttl
        self._cache = {} if cache_ttl > 0 else None
        self._cache_timestamps = {} if cache_ttl > 0 else None
        
        environment = os.getenv("NODE_ENV", "development").lower()
        self.is_production = environment == "production"
        
        if self.is_production:
            self._validate_production_secrets()
            
        logger.info(f"Initialized Environment Variables secret backend for {environment}")
    
    def _validate_production_secrets(self):
        """Validate that critical secrets are present in production"""
        required_secrets = [
            "DB_PASSWORD",
            "REDIS_PASSWORD",
        ]
        
        missing_secrets = []
        for secret in required_secrets:
            if not os.getenv(secret):
                missing_secrets.append(secret)
        
        if missing_secrets:
            logger.error(f"Production deployment missing critical secrets: {missing_secrets}")
            raise ValueError(f"Missing required production secrets: {', '.join(missing_secrets)}")
        
        # Validate REDACTED_SECRET strength in production
        db_REDACTED_SECRET = os.getenv("DB_PASSWORD", "")
        redis_REDACTED_SECRET = os.getenv("REDIS_PASSWORD", "")
        
        if len(db_REDACTED_SECRET) < 12:
            logger.warning("DB_PASSWORD is shorter than 12 characters - consider using a stronger REDACTED_SECRET")
        if len(redis_REDACTED_SECRET) < 12:
            logger.warning("REDIS_PASSWORD is shorter than 12 characters - consider using a stronger REDACTED_SECRET")
        
        logger.info("Production secret validation completed successfully")
    
    def _is_cache_valid(self, secret_name: str) -> bool:
        """Check if cached secret is still valid"""
        if not self._cache or secret_name not in self._cache_timestamps:
            return False
        cache_time = self._cache_timestamps[secret_name]
        return datetime.now() - cache_time < timedelta(seconds=self.cache_ttl)
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variables with optional caching"""
        # Check cache first (if enabled)
        if self._cache and self._is_cache_valid(secret_name):
            logger.debug(f"Retrieved cached secret {secret_name}")
            return self._cache[secret_name]
        
        # Get from environment
        value = os.getenv(secret_name)
        
        if value:
            # Cache the result (if caching enabled)
            if self._cache:
                self._cache[secret_name] = value
                self._cache_timestamps[secret_name] = datetime.now()
            
            # Mask sensitive values in logs
            if any(sensitive in secret_name.lower() for sensitive in ['REDACTED_SECRET', 'key', 'secret', 'token']):
                logger.debug(f"Retrieved secret {secret_name} from environment (value masked)")
            else:
                logger.debug(f"Retrieved secret {secret_name} from environment")
            return value
        
        # Log missing secrets appropriately
        if self.is_production:
            logger.error(f"Production secret {secret_name} not found in environment")
        else:
            logger.debug(f"Development secret {secret_name} not found in environment")
        return None
    
    async def get_secret_dict(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get JSON secret from environment variables"""
        value = await self.get_secret(secret_name)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON secret {secret_name}")
                return None
        return None

class AWSSecretsManagerBackend(SecretBackend):
    """AWS Secrets Manager backend (production)"""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.name = f"AWS Secrets Manager ({region})"
        self._client = None
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
        logger.info(f"Initialized AWS Secrets Manager backend in {region}")
    
    async def _get_client(self):
        """Lazy initialization of AWS client"""
        if self._client is None:
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
                
                self._client = boto3.client('secretsmanager', region_name=self.region)
                logger.info("AWS Secrets Manager client initialized")
            except ImportError:
                logger.error("boto3 not installed. Install with: pip install boto3")
                raise
            except NoCredentialsError:
                logger.error("AWS credentials not configured. Configure with AWS CLI or IAM role")
                raise
        return self._client
    
    def _is_cache_valid(self, secret_name: str) -> bool:
        """Check if cached secret is still valid"""
        if secret_name not in self._cache_timestamps:
            return False
        cache_time = self._cache_timestamps[secret_name]
        return datetime.now() - cache_time < timedelta(seconds=self._cache_ttl)
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager with caching"""
        # Check cache first
        if self._is_cache_valid(secret_name):
            logger.debug(f"Retrieved cached secret {secret_name}")
            return self._cache[secret_name]
        
        try:
            client = await self._get_client()
            response = client.get_secret_value(SecretId=secret_name)
            secret_value = response['SecretString']
            
            # Cache the result
            self._cache[secret_name] = secret_value
            self._cache_timestamps[secret_name] = datetime.now()
            
            logger.info(f"Retrieved secret {secret_name} from AWS Secrets Manager")
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name} from AWS: {e}")
            return None
    
    async def get_secret_dict(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get JSON secret from AWS Secrets Manager"""
        value = await self.get_secret(secret_name)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON secret {secret_name}")
                return None
        return None

class HashiCorpVaultBackend(SecretBackend):
    """HashiCorp Vault backend (production)"""
    
    def __init__(self, vault_url: str, vault_token: str):
        self.vault_url = vault_url.rstrip('/')
        self.vault_token = vault_token
        self.name = f"HashiCorp Vault ({vault_url})"
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300
        logger.info(f"Initialized HashiCorp Vault backend at {vault_url}")
    
    async def _make_request(self, path: str) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Vault"""
        try:
            import aiohttp
            
            headers = {
                'X-Vault-Token': self.vault_token,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.vault_url}/v1/{path}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Vault request failed with status {response.status}")
                        return None
                        
        except ImportError:
            logger.error("aiohttp not installed. Install with: pip install aiohttp")
            return None
        except Exception as e:
            logger.error(f"Vault request failed: {e}")
            return None
    
    def _is_cache_valid(self, secret_name: str) -> bool:
        """Check if cached secret is still valid"""
        if secret_name not in self._cache_timestamps:
            return False
        cache_time = self._cache_timestamps[secret_name]
        return datetime.now() - cache_time < timedelta(seconds=self._cache_ttl)
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from HashiCorp Vault with caching"""
        # Check cache first
        if self._is_cache_valid(secret_name):
            logger.debug(f"Retrieved cached secret {secret_name}")
            return self._cache[secret_name]
        
        response = await self._make_request(f"secret/data/{secret_name}")
        if response and 'data' in response and 'data' in response['data']:
            secret_value = response['data']['data'].get('value')
            if secret_value:
                # Cache the result
                self._cache[secret_name] = secret_value
                self._cache_timestamps[secret_name] = datetime.now()
                
                logger.info(f"Retrieved secret {secret_name} from Vault")
                return secret_value
        
        logger.error(f"Failed to retrieve secret {secret_name} from Vault")
        return None
    
    async def get_secret_dict(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get JSON secret from HashiCorp Vault"""
        response = await self._make_request(f"secret/data/{secret_name}")
        if response and 'data' in response and 'data' in response['data']:
            secret_data = response['data']['data']
            logger.info(f"Retrieved JSON secret {secret_name} from Vault")
            return secret_data
        return None

class SecretManager:
    """Main secret manager with multiple backend support"""
    
    def __init__(self, config: SecretConfig):
        self.config = config
        self.backend = self._initialize_backend()
        logger.info(f"SecretManager initialized with {self.backend.name}")
    
    def _initialize_backend(self) -> SecretBackend:
        """Initialize the appropriate secret backend"""
        if self.config.backend.lower() == "aws":
            return AWSSecretsManagerBackend(self.config.region)
        elif self.config.backend.lower() == "vault":
            if not self.config.vault_url or not self.config.vault_token:
                logger.warning("Vault URL/token not provided, falling back to environment")
                return EnvironmentSecretBackend(self.config.cache_ttl)
            return HashiCorpVaultBackend(self.config.vault_url, self.config.vault_token)
        else:
            return EnvironmentSecretBackend(self.config.cache_ttl)
    
    async def get_database_config(self) -> Dict[str, str]:
        """Get database configuration secrets"""
        if self.config.backend == "env":
            # Development: use environment variables
            return {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": os.getenv("DB_PORT", "5432"),
                "database": os.getenv("DB_NAME", "pake_system"),
                "user": os.getenv("DB_USER", "pake_user"),
                "REDACTED_SECRET": os.getenv("DB_PASSWORD", ""),
            }
        else:
            # Production: use secret manager
            secret_dict = await self.backend.get_secret_dict("pake-system/database")
            if secret_dict:
                return {
                    "host": secret_dict.get("host", "localhost"),
                    "port": str(secret_dict.get("port", 5432)),
                    "database": secret_dict.get("database", "pake_system"),
                    "user": secret_dict.get("user", "pake_user"),
                    "REDACTED_SECRET": secret_dict.get("REDACTED_SECRET", ""),
                }
            else:
                logger.error("Failed to retrieve database config from secret manager")
                raise Exception("Database configuration not available")
    
    async def get_redis_config(self) -> Dict[str, str]:
        """Get Redis configuration secrets"""
        if self.config.backend == "env":
            # Development: use environment variables
            return {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": os.getenv("REDIS_PORT", "6379"),
                "REDACTED_SECRET": os.getenv("REDIS_PASSWORD", ""),
            }
        else:
            # Production: use secret manager
            secret_dict = await self.backend.get_secret_dict("pake-system/redis")
            if secret_dict:
                return {
                    "host": secret_dict.get("host", "localhost"),
                    "port": str(secret_dict.get("port", 6379)),
                    "REDACTED_SECRET": secret_dict.get("REDACTED_SECRET", ""),
                }
            else:
                logger.error("Failed to retrieve Redis config from secret manager")
                raise Exception("Redis configuration not available")
    
    async def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for external service"""
        if self.config.backend == "env":
            # Development: use environment variables
            return os.getenv(f"{service.upper()}_API_KEY")
        else:
            # Production: use secret manager
            return await self.backend.get_secret(f"pake-system/api-keys/{service.lower()}")
    
    async def get_service_credentials(self, service: str) -> Optional[Dict[str, Any]]:
        """Get service credentials (username/REDACTED_SECRET pairs)"""
        if self.config.backend == "env":
            # Development: use environment variables
            username = os.getenv(f"{service.upper()}_USER")
            REDACTED_SECRET = os.getenv(f"{service.upper()}_PASSWORD")
            if username and REDACTED_SECRET:
                return {"username": username, "REDACTED_SECRET": REDACTED_SECRET}
            return None
        else:
            # Production: use secret manager
            return await self.backend.get_secret_dict(f"pake-system/services/{service.lower()}")

# Global secret manager instance
_secret_manager: Optional[SecretManager] = None

def get_secret_manager() -> SecretManager:
    """Get global secret manager instance"""
    global _secret_manager
    if _secret_manager is None:
        # Determine backend based on explicit configuration
        secret_backend = os.getenv("PAKE_SECRET_BACKEND", "env").lower()
        
        if secret_backend == "aws":
            # AWS Secrets Manager (premium option)
            if not (os.getenv("AWS_ACCESS_KEY_ID") or os.path.exists("/root/.aws/credentials")):
                logger.error("AWS backend requested but no credentials found, falling back to environment")
                secret_backend = "env"
            else:
                config = SecretConfig(
                    backend="aws",
                    region=os.getenv("AWS_REGION", "us-east-1")
                )
        elif secret_backend == "vault":
            # HashiCorp Vault (premium option)
            if not (os.getenv("VAULT_ADDR") and os.getenv("VAULT_TOKEN")):
                logger.error("Vault backend requested but configuration missing, falling back to environment")
                secret_backend = "env"
            else:
                config = SecretConfig(
                    backend="vault",
                    vault_url=os.getenv("VAULT_ADDR"),
                    vault_token=os.getenv("VAULT_TOKEN")
                )
        
        # Default to environment variables (free for all environments)
        if secret_backend == "env":
            environment = os.getenv("NODE_ENV", "development").lower()
            config = SecretConfig(
                backend="env",
                cache_ttl=300 if environment == "production" else 0  # Cache in prod for performance
            )
            logger.info(f"Using environment variables for secret management in {environment} mode")
        
        _secret_manager = SecretManager(config)
    
    return _secret_manager

async def get_database_url() -> str:
    """Get database connection URL"""
    secret_manager = get_secret_manager()
    config = await secret_manager.get_database_config()
    
    REDACTED_SECRET_part = f":{config['REDACTED_SECRET']}" if config['REDACTED_SECRET'] else ""
    return f"postgresql://{config['user']}{REDACTED_SECRET_part}@{config['host']}:{config['port']}/{config['database']}"

async def get_redis_url() -> str:
    """Get Redis connection URL"""
    secret_manager = get_secret_manager()
    config = await secret_manager.get_redis_config()
    
    REDACTED_SECRET_part = f":{config['REDACTED_SECRET']}@" if config['REDACTED_SECRET'] else ""
    return f"redis://{REDACTED_SECRET_part}{config['host']}:{config['port']}"