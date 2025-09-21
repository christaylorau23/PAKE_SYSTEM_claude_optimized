#!/usr/bin/env python3
"""
PAKE System - Enterprise Secrets Management
Secure secrets management following enterprise best practices.

This module provides:
- Secure secrets storage and retrieval
- Environment-based configuration
- Secrets rotation and lifecycle management
- Audit logging for secrets access
- Integration with cloud secrets managers
"""

import asyncio
import base64
import json
import logging
import os
import secrets
from datetime import datetime, UTC, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import aiofiles
import boto3
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from google.cloud import secretmanager
from pydantic import BaseModel, Field, validator


class SecretType(Enum):
    """Types of secrets"""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_REDACTED_SECRET"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"
    SSL_CERTIFICATE = "ssl_certificate"
    SSH_KEY = "ssh_key"
    OAUTH_TOKEN = "oauth_token"
    WEBHOOK_SECRET = "webhook_secret"


class SecretProvider(Enum):
    """Secret storage providers"""
    LOCAL_FILE = "local_file"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    GOOGLE_SECRET_MANAGER = "google_secret_manager"
    HASHICORP_VAULT = "hashicorp_vault"


class SecretMetadata(BaseModel):
    """Secret metadata model"""
    secret_id: str = Field(..., description="Unique secret identifier")
    secret_type: SecretType = Field(..., description="Type of secret")
    provider: SecretProvider = Field(..., description="Storage provider")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: Optional[datetime] = Field(None, description="Secret expiration")
    rotation_schedule: Optional[str] = Field(None, description="Rotation schedule")
    tags: Dict[str, str] = Field(default_factory=dict, description="Secret tags")
    description: Optional[str] = Field(None, description="Secret description")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    access_count: int = Field(default=0, description="Access count")


class SecretAccessLog(BaseModel):
    """Secret access log entry"""
    log_id: str = Field(..., description="Unique log identifier")
    secret_id: str = Field(..., description="Secret identifier")
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    accessed_by: str = Field(..., description="User or service that accessed secret")
    access_type: str = Field(..., description="Type of access (read, write, delete)")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    success: bool = Field(..., description="Whether access was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SecretsManager:
    """
    Enterprise Secrets Management System
    
    Provides secure storage, retrieval, and lifecycle management of secrets
    with support for multiple cloud providers and local storage.
    """
    
    def __init__(self, provider: SecretProvider = SecretProvider.LOCAL_FILE):
        self.provider = provider
        self.logger = self._setup_logger()
        self.secrets_cache: Dict[str, str] = {}
        self.access_logs: List[SecretAccessLog] = []
        self.metadata_store: Dict[str, SecretMetadata] = {}
        
        # Initialize provider-specific client
        self._initialize_provider()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up secrets management logger"""
        logger = logging.getLogger("pake_secrets")
        logger.setLevel(logging.INFO)
        
        # Create secrets log file
        log_dir = Path("logs/secrets")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "secrets.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_provider(self):
        """Initialize provider-specific client"""
        try:
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                self._init_aws_client()
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                self._init_azure_client()
            elif self.provider == SecretProvider.GOOGLE_SECRET_MANAGER:
                self._init_google_client()
            elif self.provider == SecretProvider.LOCAL_FILE:
                self._init_local_storage()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize secrets provider: {str(e)}")
            raise
    
    def _init_aws_client(self):
        """Initialize AWS Secrets Manager client"""
        try:
            self.aws_client = boto3.client('secretsmanager')
            self.logger.info("AWS Secrets Manager client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS client: {str(e)}")
            raise
    
    def _init_azure_client(self):
        """Initialize Azure Key Vault client"""
        try:
            credential = DefaultAzureCredential()
            vault_url = os.getenv('AZURE_KEY_VAULT_URL')
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL environment variable not set")
            
            self.azure_client = SecretClient(vault_url=vault_url, credential=credential)
            self.logger.info("Azure Key Vault client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure client: {str(e)}")
            raise
    
    def _init_google_client(self):
        """Initialize Google Secret Manager client"""
        try:
            self.google_client = secretmanager.SecretManagerServiceClient()
            self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            if not self.project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT_ID environment variable not set")
            
            self.logger.info("Google Secret Manager client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google client: {str(e)}")
            raise
    
    def _init_local_storage(self):
        """Initialize local file storage"""
        try:
            self.secrets_dir = Path("secrets")
            self.secrets_dir.mkdir(exist_ok=True)
            
            # Create metadata file
            self.metadata_file = self.secrets_dir / "metadata.json"
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self.metadata_store = {
                        k: SecretMetadata(**v) for k, v in json.load(f).items()
                    }
            
            self.logger.info("Local secrets storage initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize local storage: {str(e)}")
            raise
    
    # ========================================================================
    # Secret Operations
    # ========================================================================
    
    async def store_secret(
        self,
        secret_id: str,
        secret_value: str,
        secret_type: SecretType,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        rotation_schedule: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Store a secret securely
        
        Args:
            secret_id: Unique identifier for the secret
            secret_value: The secret value to store
            secret_type: Type of secret
            description: Optional description
            expires_at: Optional expiration date
            rotation_schedule: Optional rotation schedule
            tags: Optional tags for the secret
            
        Returns:
            True if secret was stored successfully
        """
        try:
            # Encrypt secret value
            encrypted_value = await self._encrypt_secret(secret_value)
            
            # Store secret based on provider
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                await self._store_aws_secret(secret_id, encrypted_value)
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                await self._store_azure_secret(secret_id, encrypted_value)
            elif self.provider == SecretProvider.GOOGLE_SECRET_MANAGER:
                await self._store_google_secret(secret_id, encrypted_value)
            elif self.provider == SecretProvider.LOCAL_FILE:
                await self._store_local_secret(secret_id, encrypted_value)
            
            # Create metadata
            metadata = SecretMetadata(
                secret_id=secret_id,
                secret_type=secret_type,
                provider=self.provider,
                expires_at=expires_at,
                rotation_schedule=rotation_schedule,
                tags=tags or {},
                description=description
            )
            
            self.metadata_store[secret_id] = metadata
            await self._save_metadata()
            
            # Log access
            await self._log_access(secret_id, "write", "system", success=True)
            
            self.logger.info(f"Secret stored successfully: {secret_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store secret {secret_id}: {str(e)}")
            await self._log_access(secret_id, "write", "system", success=False, error_message=str(e))
            return False
    
    async def retrieve_secret(
        self,
        secret_id: str,
        accessed_by: str = "system",
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieve a secret securely
        
        Args:
            secret_id: Secret identifier
            accessed_by: User or service accessing the secret
            source_ip: Source IP address
            user_agent: User agent string
            
        Returns:
            Secret value if found, None otherwise
        """
        try:
            # Check if secret exists in metadata
            if secret_id not in self.metadata_store:
                await self._log_access(secret_id, "read", accessed_by, source_ip, user_agent, success=False, error_message="Secret not found")
                return None
            
            metadata = self.metadata_store[secret_id]
            
            # Check expiration
            if metadata.expires_at and metadata.expires_at < datetime.now(UTC):
                await self._log_access(secret_id, "read", accessed_by, source_ip, user_agent, success=False, error_message="Secret expired")
                return None
            
            # Retrieve encrypted secret
            encrypted_value = None
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                encrypted_value = await self._retrieve_aws_secret(secret_id)
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                encrypted_value = await self._retrieve_azure_secret(secret_id)
            elif self.provider == SecretProvider.GOOGLE_SECRET_MANAGER:
                encrypted_value = await self._retrieve_google_secret(secret_id)
            elif self.provider == SecretProvider.LOCAL_FILE:
                encrypted_value = await self._retrieve_local_secret(secret_id)
            
            if not encrypted_value:
                await self._log_access(secret_id, "read", accessed_by, source_ip, user_agent, success=False, error_message="Failed to retrieve encrypted secret")
                return None
            
            # Decrypt secret
            secret_value = await self._decrypt_secret(encrypted_value)
            
            # Update metadata
            metadata.last_accessed = datetime.now(UTC)
            metadata.access_count += 1
            await self._save_metadata()
            
            # Log successful access
            await self._log_access(secret_id, "read", accessed_by, source_ip, user_agent, success=True)
            
            self.logger.info(f"Secret retrieved successfully: {secret_id}")
            return secret_value
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {secret_id}: {str(e)}")
            await self._log_access(secret_id, "read", accessed_by, source_ip, user_agent, success=False, error_message=str(e))
            return None
    
    async def delete_secret(
        self,
        secret_id: str,
        deleted_by: str = "system"
    ) -> bool:
        """
        Delete a secret
        
        Args:
            secret_id: Secret identifier
            deleted_by: User or service deleting the secret
            
        Returns:
            True if secret was deleted successfully
        """
        try:
            # Delete from provider
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                await self._delete_aws_secret(secret_id)
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                await self._delete_azure_secret(secret_id)
            elif self.provider == SecretProvider.GOOGLE_SECRET_MANAGER:
                await self._delete_google_secret(secret_id)
            elif self.provider == SecretProvider.LOCAL_FILE:
                await self._delete_local_secret(secret_id)
            
            # Remove from metadata
            if secret_id in self.metadata_store:
                del self.metadata_store[secret_id]
                await self._save_metadata()
            
            # Log deletion
            await self._log_access(secret_id, "delete", deleted_by, success=True)
            
            self.logger.info(f"Secret deleted successfully: {secret_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete secret {secret_id}: {str(e)}")
            await self._log_access(secret_id, "delete", deleted_by, success=False, error_message=str(e))
            return False
    
    # ========================================================================
    # Provider-Specific Implementations
    # ========================================================================
    
    async def _store_aws_secret(self, secret_id: str, encrypted_value: str):
        """Store secret in AWS Secrets Manager"""
        try:
            self.aws_client.create_secret(
                Name=secret_id,
                SecretString=encrypted_value,
                Description=f"PAKE System secret: {secret_id}"
            )
        except self.aws_client.exceptions.ResourceExistsException:
            # Update existing secret
            self.aws_client.update_secret(
                SecretId=secret_id,
                SecretString=encrypted_value
            )
    
    async def _retrieve_aws_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from AWS Secrets Manager"""
        try:
            response = self.aws_client.get_secret_value(SecretId=secret_id)
            return response['SecretString']
        except self.aws_client.exceptions.ResourceNotFoundException:
            return None
    
    async def _delete_aws_secret(self, secret_id: str):
        """Delete secret from AWS Secrets Manager"""
        self.aws_client.delete_secret(
            SecretId=secret_id,
            ForceDeleteWithoutRecovery=True
        )
    
    async def _store_azure_secret(self, secret_id: str, encrypted_value: str):
        """Store secret in Azure Key Vault"""
        self.azure_client.set_secret(secret_id, encrypted_value)
    
    async def _retrieve_azure_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from Azure Key Vault"""
        try:
            secret = self.azure_client.get_secret(secret_id)
            return secret.value
        except Exception:
            return None
    
    async def _delete_azure_secret(self, secret_id: str):
        """Delete secret from Azure Key Vault"""
        self.azure_client.begin_delete_secret(secret_id)
    
    async def _store_google_secret(self, secret_id: str, encrypted_value: str):
        """Store secret in Google Secret Manager"""
        parent = f"projects/{self.project_id}"
        
        # Create secret
        secret = self.google_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        
        # Add secret version
        self.google_client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": encrypted_value.encode()},
            }
        )
    
    async def _retrieve_google_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from Google Secret Manager"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
            response = self.google_client.access_secret_version(request={"name": name})
            return response.payload.data.decode()
        except Exception:
            return None
    
    async def _delete_google_secret(self, secret_id: str):
        """Delete secret from Google Secret Manager"""
        name = f"projects/{self.project_id}/secrets/{secret_id}"
        self.google_client.delete_secret(request={"name": name})
    
    async def _store_local_secret(self, secret_id: str, encrypted_value: str):
        """Store secret in local file"""
        secret_file = self.secrets_dir / f"{secret_id}.secret"
        async with aiofiles.open(secret_file, 'w') as f:
            await f.write(encrypted_value)
    
    async def _retrieve_local_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from local file"""
        secret_file = self.secrets_dir / f"{secret_id}.secret"
        if secret_file.exists():
            async with aiofiles.open(secret_file, 'r') as f:
                return await f.read()
        return None
    
    async def _delete_local_secret(self, secret_id: str):
        """Delete secret from local file"""
        secret_file = self.secrets_dir / f"{secret_id}.secret"
        if secret_file.exists():
            secret_file.unlink()
    
    # ========================================================================
    # Encryption/Decryption
    # ========================================================================
    
    async def _encrypt_secret(self, secret_value: str) -> str:
        """Encrypt secret value"""
        try:
            # Generate encryption key from environment variable
            master_key = os.getenv('PAKE_MASTER_KEY', 'default-master-key-for-development-only')
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'pake_secrets_salt',  # In production, use random salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            
            # Encrypt using Fernet
            f = Fernet(key)
            encrypted_data = f.encrypt(secret_value.encode())
            
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt secret: {str(e)}")
            raise
    
    async def _decrypt_secret(self, encrypted_value: str) -> str:
        """Decrypt secret value"""
        try:
            # Generate encryption key from environment variable
            master_key = os.getenv('PAKE_MASTER_KEY', 'default-master-key-for-development-only')
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'pake_secrets_salt',  # In production, use random salt
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            
            # Decrypt using Fernet
            f = Fernet(key)
            decrypted_data = f.decrypt(base64.urlsafe_b64decode(encrypted_value))
            
            return decrypted_data.decode()
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt secret: {str(e)}")
            raise
    
    # ========================================================================
    # Metadata and Logging
    # ========================================================================
    
    async def _save_metadata(self):
        """Save metadata to storage"""
        try:
            if self.provider == SecretProvider.LOCAL_FILE:
                metadata_dict = {
                    k: v.dict() for k, v in self.metadata_store.items()
                }
                async with aiofiles.open(self.metadata_file, 'w') as f:
                    await f.write(json.dumps(metadata_dict, indent=2, default=str))
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {str(e)}")
    
    async def _log_access(
        self,
        secret_id: str,
        access_type: str,
        accessed_by: str,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log secret access"""
        log_entry = SecretAccessLog(
            log_id=f"log_{int(datetime.now(UTC).timestamp())}_{secrets.token_hex(4)}",
            secret_id=secret_id,
            accessed_by=accessed_by,
            access_type=access_type,
            source_ip=source_ip,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        self.access_logs.append(log_entry)
        
        # Log to file
        if success:
            self.logger.info(f"Secret access: {access_type} {secret_id} by {accessed_by}")
        else:
            self.logger.warning(f"Failed secret access: {access_type} {secret_id} by {accessed_by} - {error_message}")
    
    # ========================================================================
    # Secret Management Operations
    # ========================================================================
    
    async def list_secrets(self) -> List[SecretMetadata]:
        """List all secrets metadata"""
        return list(self.metadata_store.values())
    
    async def get_secret_metadata(self, secret_id: str) -> Optional[SecretMetadata]:
        """Get metadata for a specific secret"""
        return self.metadata_store.get(secret_id)
    
    async def rotate_secret(
        self,
        secret_id: str,
        new_value: str,
        rotated_by: str = "system"
    ) -> bool:
        """
        Rotate a secret value
        
        Args:
            secret_id: Secret identifier
            new_value: New secret value
            rotated_by: User or service performing rotation
            
        Returns:
            True if rotation was successful
        """
        try:
            # Store new value
            success = await self.store_secret(secret_id, new_value, SecretType.API_KEY)
            
            if success:
                # Update metadata
                if secret_id in self.metadata_store:
                    metadata = self.metadata_store[secret_id]
                    metadata.updated_at = datetime.now(UTC)
                    await self._save_metadata()
                
                # Log rotation
                await self._log_access(secret_id, "rotate", rotated_by, success=True)
                
                self.logger.info(f"Secret rotated successfully: {secret_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to rotate secret {secret_id}: {str(e)}")
            await self._log_access(secret_id, "rotate", rotated_by, success=False, error_message=str(e))
            return False
    
    async def get_access_logs(
        self,
        secret_id: Optional[str] = None,
        days: int = 30
    ) -> List[SecretAccessLog]:
        """Get access logs for secrets"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)
        
        filtered_logs = [
            log for log in self.access_logs
            if start_date <= log.accessed_at <= end_date
            and (secret_id is None or log.secret_id == secret_id)
        ]
        
        return sorted(filtered_logs, key=lambda x: x.accessed_at, reverse=True)
    
    async def check_expiring_secrets(self, days_ahead: int = 7) -> List[SecretMetadata]:
        """Check for secrets expiring soon"""
        check_date = datetime.now(UTC) + timedelta(days=days_ahead)
        
        expiring_secrets = [
            metadata for metadata in self.metadata_store.values()
            if metadata.expires_at and metadata.expires_at <= check_date
        ]
        
        return expiring_secrets
    
    async def generate_security_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate secrets security report"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)
        
        # Filter logs by date range
        recent_logs = [
            log for log in self.access_logs
            if start_date <= log.accessed_at <= end_date
        ]
        
        # Calculate statistics
        total_secrets = len(self.metadata_store)
        total_accesses = len(recent_logs)
        failed_accesses = len([log for log in recent_logs if not log.success])
        
        # Most accessed secrets
        access_counts = {}
        for log in recent_logs:
            access_counts[log.secret_id] = access_counts.get(log.secret_id, 0) + 1
        
        most_accessed = sorted(access_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Expiring secrets
        expiring_secrets = await self.check_expiring_secrets()
        
        report = {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_secrets": total_secrets,
                "total_accesses": total_accesses,
                "failed_accesses": failed_accesses,
                "success_rate": (total_accesses - failed_accesses) / total_accesses if total_accesses > 0 else 1.0,
                "expiring_secrets": len(expiring_secrets)
            },
            "most_accessed_secrets": most_accessed,
            "expiring_secrets": [
                {
                    "secret_id": secret.secret_id,
                    "expires_at": secret.expires_at.isoformat(),
                    "secret_type": secret.secret_type.value
                }
                for secret in expiring_secrets
            ],
            "recommendations": await self._generate_recommendations(recent_logs, expiring_secrets)
        }
        
        return report
    
    async def _generate_recommendations(
        self,
        recent_logs: List[SecretAccessLog],
        expiring_secrets: List[SecretMetadata]
    ) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # Check for failed accesses
        failed_logs = [log for log in recent_logs if not log.success]
        if len(failed_logs) > 10:
            recommendations.append("High number of failed secret accesses detected - review access patterns")
        
        # Check for expiring secrets
        if expiring_secrets:
            recommendations.append(f"{len(expiring_secrets)} secrets are expiring soon - schedule rotation")
        
        # Check for secrets that haven't been accessed recently
        all_secret_ids = set(self.metadata_store.keys())
        accessed_secret_ids = set(log.secret_id for log in recent_logs)
        unused_secrets = all_secret_ids - accessed_secret_ids
        
        if unused_secrets:
            recommendations.append(f"{len(unused_secrets)} secrets haven't been accessed recently - consider cleanup")
        
        return recommendations


# ========================================================================
# Environment Configuration Helper
# ========================================================================

class EnvironmentConfig:
    """Helper class for environment-based configuration"""
    
    @staticmethod
    def load_secrets_from_env() -> Dict[str, str]:
        """Load secrets from environment variables"""
        secrets = {}
        
        # Common secret environment variables
        secret_vars = [
            'PAKE_JWT_SECRET',
            'PAKE_DB_PASSWORD',
            'PAKE_REDIS_PASSWORD',
            'PAKE_ENCRYPTION_KEY',
            'FIRECRAWL_API_KEY',
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY'
        ]
        
        for var in secret_vars:
            value = os.getenv(var)
            if value:
                secrets[var] = value
        
        return secrets
    
    @staticmethod
    def validate_required_secrets(required_secrets: List[str]) -> List[str]:
        """Validate that required secrets are present in environment"""
        missing_secrets = []
        
        for secret in required_secrets:
            if not os.getenv(secret):
                missing_secrets.append(secret)
        
        return missing_secrets


if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize secrets manager
        secrets_manager = SecretsManager(provider=SecretProvider.LOCAL_FILE)
        
        # Store a secret
        await secrets_manager.store_secret(
            secret_id="test_api_key",
            secret_value="sk-test-123456789",
            secret_type=SecretType.API_KEY,
            description="Test API key for development"
        )
        
        # Retrieve the secret
        retrieved_secret = await secrets_manager.retrieve_secret("test_api_key")
        print(f"Retrieved secret: {retrieved_secret}")
        
        # Generate security report
        report = await secrets_manager.generate_security_report()
        print(f"Security report: {report['summary']}")
    
    asyncio.run(main())
