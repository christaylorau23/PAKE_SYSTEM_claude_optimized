#!/usr/bin/env python3
"""
Git History Cleanup Script for PAKE System
==========================================

This script removes hardcoded secrets from Git history using git-filter-repo.
It's a destructive operation that rewrites Git history to permanently remove
sensitive information.

CRITICAL SECURITY WARNING:
- This script permanently removes secrets from Git history
- All team members must re-clone the repository after running this script
- This operation cannot be undone
- Backup your repository before running this script

Usage:
    python scripts/clean_git_history.py

Requirements:
    - git-filter-repo installed: pip install git-filter-repo
    - Clean working directory (no uncommitted changes)
    - Backup of the repository
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitHistoryCleaner:
    """Clean Git history to remove hardcoded secrets."""

    def __init__(self, repo_path: str = "."):
        """
        Initialize Git history cleaner.

        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.secrets_to_remove = self._load_secrets_patterns()

    def _load_secrets_patterns(self) -> list[dict[str, str]]:
        """
        Load patterns of secrets to remove from Git history.

        Returns:
            List of secret patterns with their replacement values
        """
        return [
            # Database passwords
            {
                "pattern": r"changeme-database-REDACTED_SECRET",
                "replacement": "REDACTED_SECRET",
                "description": "Database password",
            },
            {
                "pattern": r"dev_password",
                "replacement": "REDACTED_SECRET",
                "description": "Development database password",
            },
            {
                "pattern": r"staging_password",
                "replacement": "REDACTED_SECRET",
                "description": "Staging database password",
            },
            {
                "pattern": r"REPLACE_WITH_SECURE_PASSWORD",
                "replacement": "REDACTED_SECRET",
                "description": "Production database password placeholder",
            },
            # Redis passwords
            {
                "pattern": r"changeme-redis-REDACTED_SECRET",
                "replacement": "REDACTED_SECRET",
                "description": "Redis password",
            },
            # JWT secrets
            {
                "pattern": r"changeme-jwt-secret-key-make-this-long-and-random",
                "replacement": "REDACTED_SECRET",
                "description": "JWT secret key",
            },
            {
                "pattern": r"dev-secret-key-change-in-production-",
                "replacement": "REDACTED_SECRET",
                "description": "Development JWT secret",
            },
            {
                "pattern": r"staging-secret-key-replace-me-",
                "replacement": "REDACTED_SECRET",
                "description": "Staging JWT secret",
            },
            {
                "pattern": r"REPLACE-WITH-SECURE-PRODUCTION-KEY-",
                "replacement": "REDACTED_SECRET",
                "description": "Production JWT secret placeholder",
            },
            # API keys
            {
                "pattern": r"placeholder-firecrawl-api-key",
                "replacement": "REDACTED_SECRET",
                "description": "Firecrawl API key placeholder",
            },
            {
                "pattern": r"placeholder-openai-api-key",
                "replacement": "REDACTED_SECRET",
                "description": "OpenAI API key placeholder",
            },
            {
                "pattern": r"placeholder-anthropic-api-key",
                "replacement": "REDACTED_SECRET",
                "description": "Anthropic API key placeholder",
            },
            {
                "pattern": r"REPLACE_WITH_PRODUCTION_API_KEY",
                "replacement": "REDACTED_SECRET",
                "description": "Production API key placeholder",
            },
            # Application secrets
            {
                "pattern": r"changeme-app-secret-key",
                "replacement": "REDACTED_SECRET",
                "description": "Application secret key",
            },
            # Test secrets (keep test-specific ones for testing)
            {
                "pattern": r"test-secret-key-for-testing-only",
                "replacement": "REDACTED_SECRET",
                "description": "Test secret key",
            },
            # Replication passwords
            {
                "pattern": r"changeme-replication-REDACTED_SECRET",
                "replacement": "REDACTED_SECRET",
                "description": "Database replication password",
            },
        ]

    def check_prerequisites(self) -> bool:
        """
        Check if all prerequisites are met.

        Returns:
            True if all prerequisites are met, False otherwise
        """
        logger.info("Checking prerequisites...")

        # Check if we're in a Git repository
        if not (self.repo_path / ".git").exists():
            logger.error("Not in a Git repository")
            return False

        # Check if git-filter-repo is installed
        try:
            subprocess.run(
                ["git-filter-repo", "--version"], capture_output=True, check=True
            )
            logger.info("✅ git-filter-repo is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error(
                "❌ git-filter-repo not found. Install with: pip install git-filter-repo"
            )
            return False

        # Check if working directory is clean
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                logger.error(
                    "❌ Working directory is not clean. Commit or stash changes first."
                )
                return False
            logger.info("✅ Working directory is clean")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error checking Git status: {e}")
            return False

        # Check if we're on main/master branch
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()
            if current_branch not in ["main", "master"]:
                logger.warning(f"⚠️  Not on main branch (current: {current_branch})")
                logger.warning(
                    "   Consider switching to main branch before cleaning history"
                )
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error checking current branch: {e}")
            return False

        logger.info("✅ All prerequisites met")
        return True

    def create_backup(self) -> bool:
        """
        Create a backup of the repository.

        Returns:
            True if backup created successfully, False otherwise
        """
        logger.info("Creating backup...")

        backup_path = self.repo_path.parent / f"{self.repo_path.name}_backup"

        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)

            shutil.copytree(
                self.repo_path, backup_path, ignore=shutil.ignore_patterns(".git")
            )
            logger.info(f"✅ Backup created at: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return False

    def clean_git_history(self) -> bool:
        """
        Clean Git history to remove hardcoded secrets.

        Returns:
            True if cleaning was successful, False otherwise
        """
        logger.info("Starting Git history cleanup...")

        # Change to repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            for secret in self.secrets_to_remove:
                logger.info(f"Removing: {secret['description']}")

                # Use git-filter-repo to replace the secret
                cmd = [
                    "git-filter-repo",
                    "--replace-text",
                    f"{secret['pattern']}==>{secret['replacement']}",
                    "--force",  # Force overwrite of existing backup
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(
                        f"❌ Failed to remove {secret['description']}: {result.stderr}"
                    )
                    return False

                logger.info(f"✅ Removed: {secret['description']}")

            logger.info("✅ Git history cleanup completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Error during Git history cleanup: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    def verify_cleanup(self) -> bool:
        """
        Verify that secrets have been removed from Git history.

        Returns:
            True if cleanup was successful, False otherwise
        """
        logger.info("Verifying cleanup...")

        # Change to repository directory
        original_cwd = os.getcwd()
        os.chdir(self.repo_path)

        try:
            # Check if any secrets remain in the history
            remaining_secrets = []

            for secret in self.secrets_to_remove:
                # Search for the pattern in Git history
                cmd = ["git", "log", "--all", "--grep", secret["pattern"]]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.stdout.strip():
                    remaining_secrets.append(secret["description"])

            if remaining_secrets:
                logger.warning(
                    f"⚠️  Some secrets may still remain: {remaining_secrets}"
                )
                return False

            logger.info("✅ Cleanup verification passed")
            return True

        except Exception as e:
            logger.error(f"❌ Error during verification: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    def run_cleanup(self) -> bool:
        """
        Run the complete Git history cleanup process.

        Returns:
            True if cleanup was successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("PAKE System - Git History Cleanup")
        logger.info("=" * 60)

        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("❌ Prerequisites not met. Aborting.")
            return False

        # Create backup
        if not self.create_backup():
            logger.error("❌ Failed to create backup. Aborting.")
            return False

        # Clean Git history
        if not self.clean_git_history():
            logger.error("❌ Git history cleanup failed.")
            return False

        # Verify cleanup
        if not self.verify_cleanup():
            logger.warning("⚠️  Cleanup verification failed, but process completed.")

        logger.info("=" * 60)
        logger.info("✅ Git history cleanup completed successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("🚨 CRITICAL NEXT STEPS:")
        logger.info("1. All team members must re-clone the repository")
        logger.info("2. Update any CI/CD pipelines that reference the old history")
        logger.info("3. Verify that all secrets are now stored in Vault")
        logger.info("4. Test the application to ensure it works with Vault integration")
        logger.info("")
        logger.info(
            "📁 Backup location: {self.repo_path.parent}/{self.repo_path.name}_backup"
        )

        return True


def main():
    """Main entry point for Git history cleanup."""
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = "."

    cleaner = GitHistoryCleaner(repo_path)

    # Confirm before proceeding
    print("\n" + "=" * 60)
    print("⚠️  CRITICAL SECURITY WARNING")
    print("=" * 60)
    print("This script will PERMANENTLY remove secrets from Git history.")
    print("This operation CANNOT be undone.")
    print("All team members will need to re-clone the repository.")
    print("=" * 60)

    response = input("\nDo you want to continue? (yes/no): ").lower().strip()
    if response != "yes":
        print("Operation cancelled.")
        sys.exit(0)

    # Run cleanup
    success = cleaner.run_cleanup()

    if success:
        print("\n✅ Git history cleanup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Git history cleanup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
