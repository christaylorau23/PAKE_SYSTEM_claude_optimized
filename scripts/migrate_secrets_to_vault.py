#!/usr/bin/env python3
"""
Secrets Migration Script for PAKE System
=========================================

This script migrates all secrets from the codebase to HashiCorp Vault.
It creates a structured secret hierarchy organized by environment.

Usage:
    poetry run python scripts/migrate_secrets_to_vault.py

Requirements:
    - Vault server running at http://127.0.0.1:8200
    - VAULT_TOKEN environment variable set (or defaults to 'dev-only-token')
"""

import os
import sys
from typing import Dict, Any

try:
    import hvac
except ImportError:
    print("Error: hvac library not installed. Run: poetry add hvac")
    sys.exit(1)


class VaultSecretsManager:
    """Manages migration of secrets to HashiCorp Vault."""

    def __init__(self, vault_url: str = "http://127.0.0.1:8200", vault_token: str = None):
        """
        Initialize Vault client.

        Args:
            vault_url: Vault server URL
            vault_token: Vault authentication token
        """
        self.vault_url = vault_url
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN", "dev-only-token")
        self.client = None

    def connect(self) -> bool:
        """
        Connect to Vault server and verify authentication.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = hvac.Client(url=self.vault_url, token=self.vault_token)

            if not self.client.is_authenticated():
                print(f"❌ Failed to authenticate with Vault at {self.vault_url}")
                return False

            print(f"✅ Successfully connected to Vault at {self.vault_url}")
            return True

        except Exception as e:
            print(f"❌ Error connecting to Vault: {e}")
            return False

    def create_secret(self, path: str, secret_data: Dict[str, Any]) -> bool:
        """
        Create or update a secret in Vault.

        Args:
            path: Secret path (e.g., 'pake_system/test/database')
            secret_data: Dictionary of secret key-value pairs

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret_data
            )
            print(f"✅ Created secret at: {path}")
            return True

        except Exception as e:
            print(f"❌ Error creating secret at {path}: {e}")
            return False

    def migrate_all_secrets(self):
        """Migrate all secrets from codebase to Vault."""
        print("\n" + "="*60)
        print("PAKE System - Secrets Migration to Vault")
        print("="*60 + "\n")

        # Define all secrets organized by environment
        secrets_structure = {
            # Test environment secrets (from conftest.py and conftest_auth.py)
            "pake_system/test/security": {
                "secret_key": "test-secret-key-for-testing-only-never-use-in-production-12345678",
                "algorithm": "HS256",
                "access_token_expire_minutes": "30",
            },
            "pake_system/test/database": {
                "url": "postgresql://test:test@localhost/test_db",
                "pool_size": "10",
                "max_overflow": "20",
            },
            "pake_system/test/redis": {
                "url": "redis://localhost:6379",
                "pool_size": "10",
            },

            # Development environment secrets
            "pake_system/development/security": {
                "secret_key": "dev-secret-key-change-in-production-" + os.urandom(16).hex(),
                "algorithm": "HS256",
                "access_token_expire_minutes": "30",
                "refresh_token_expire_days": "7",
            },
            "pake_system/development/database": {
                "url": "postgresql://pake_dev:dev_password@localhost:5432/pake_dev",
                "pool_size": "10",
                "max_overflow": "20",
            },
            "pake_system/development/redis": {
                "url": "redis://localhost:6379/0",
                "pool_size": "10",
            },
            "pake_system/development/api_keys": {
                "firecrawl_api_key": "",  # Placeholder - set manually if needed
            },

            # Staging environment secrets (templates - should be replaced)
            "pake_system/staging/security": {
                "secret_key": "staging-secret-key-replace-me-" + os.urandom(16).hex(),
                "algorithm": "HS256",
                "access_token_expire_minutes": "30",
                "refresh_token_expire_days": "7",
            },
            "pake_system/staging/database": {
                "url": "postgresql://pake_staging:staging_password@db-staging:5432/pake_staging",
                "pool_size": "20",
                "max_overflow": "40",
            },
            "pake_system/staging/redis": {
                "url": "redis://redis-staging:6379/0",
                "pool_size": "20",
            },

            # Production environment secrets (templates - MUST be replaced)
            "pake_system/production/security": {
                "secret_key": "REPLACE-WITH-SECURE-PRODUCTION-KEY-" + os.urandom(32).hex(),
                "algorithm": "HS256",
                "access_token_expire_minutes": "15",
                "refresh_token_expire_days": "7",
            },
            "pake_system/production/database": {
                "url": "postgresql://pake_prod:REPLACE_WITH_SECURE_PASSWORD@db-prod:5432/pake_prod",
                "pool_size": "50",
                "max_overflow": "100",
            },
            "pake_system/production/redis": {
                "url": "redis://redis-prod:6379/0",
                "pool_size": "50",
            },
            "pake_system/production/api_keys": {
                "firecrawl_api_key": "REPLACE_WITH_PRODUCTION_API_KEY",
            },
        }

        # Migrate each secret
        success_count = 0
        total_count = len(secrets_structure)

        for path, secret_data in secrets_structure.items():
            if self.create_secret(path, secret_data):
                success_count += 1

        # Summary
        print("\n" + "="*60)
        print(f"Migration Complete: {success_count}/{total_count} secrets migrated")
        print("="*60 + "\n")

        if success_count == total_count:
            print("✅ All secrets successfully migrated to Vault!")
            print("\n⚠️  IMPORTANT NEXT STEPS:")
            print("1. Update production secrets in Vault with actual values")
            print("2. Remove hardcoded secrets from test files")
            print("3. Update config.py to fetch secrets from Vault")
            print("4. Set VAULT_URL and VAULT_TOKEN environment variables")
            return True
        else:
            print(f"⚠️  Warning: Only {success_count} out of {total_count} secrets migrated")
            return False

    def verify_secrets(self):
        """Verify that secrets can be read from Vault."""
        print("\n" + "="*60)
        print("Verifying Secrets in Vault")
        print("="*60 + "\n")

        test_paths = [
            "pake_system/test/security",
            "pake_system/test/database",
            "pake_system/development/security",
        ]

        for path in test_paths:
            try:
                response = self.client.secrets.kv.v2.read_secret_version(path=path)
                secret_data = response['data']['data']
                print(f"✅ Successfully read secret from: {path}")
                print(f"   Keys: {', '.join(secret_data.keys())}")
            except Exception as e:
                print(f"❌ Error reading secret from {path}: {e}")

        print("\n" + "="*60 + "\n")


def main():
    """Main entry point for secrets migration."""
    # Initialize Vault manager
    vault_manager = VaultSecretsManager()

    # Connect to Vault
    if not vault_manager.connect():
        print("\n❌ Migration aborted: Could not connect to Vault")
        print("   Make sure Vault server is running:")
        print("   docker run --cap-add=IPC_LOCK -d -p 8200:8200 -e 'VAULT_DEV_ROOT_TOKEN_ID=dev-only-token' --name vault-dev hashicorp/vault")
        sys.exit(1)

    # Migrate all secrets
    if vault_manager.migrate_all_secrets():
        # Verify secrets were written correctly
        vault_manager.verify_secrets()
        print("✅ Secrets migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Secrets migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
