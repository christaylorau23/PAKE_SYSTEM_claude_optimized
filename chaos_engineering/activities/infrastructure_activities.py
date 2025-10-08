import logging
import os
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)


def identify_latest_backup() -> None:
    """Identify the latest backup for restoration."""
    try:
        # Find the most recent backup
        result = subprocess.run(
            [
                "kubectl",
                "exec",
                "-n",
                "backup-system",
                "backup-service-0",
                "--",
                "ls",
                "-t",
                "/backups",
                "|",
                "head",
                "-1",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        backup_id = result.stdout.strip()
        os.environ["CHAOS_BACKUP_ID"] = backup_id

        logger.info(f"Identified latest backup: {backup_id}")
    except Exception as e:
        logger.error(f"Failed to identify latest backup: {e}")
        raise


def provision_restore_environment() -> None:
    """Provision a new environment for restore testing."""
    try:
        # Create restore namespace
        subprocess.run(["kubectl", "create", "namespace", "restore-system"], check=True)

        # Deploy restore database
        subprocess.run(
            [
                "kubectl",
                "apply",
                "-f",
                "k8s/restore/postgresql-restore.yaml",
                "-n",
                "restore-system",
            ],
            check=True,
        )

        # Wait for restore database to be ready
        subprocess.run(
            [
                "kubectl",
                "wait",
                "--for=condition=ready",
                "pod",
                "-l",
                "app=restore-database",
                "-n",
                "restore-system",
                "--timeout=600s",
            ],
            check=True,
        )

        logger.info("Restore environment provisioned successfully")
    except Exception as e:
        logger.error(f"Failed to provision restore environment: {e}")
        raise


def cleanup_restore_environment() -> None:
    """Clean up restore environment after testing."""
    try:
        # Delete restore namespace
        subprocess.run(["kubectl", "delete", "namespace", "restore-system"], check=True)

        logger.info("Restore environment cleaned up successfully")
    except Exception as e:
        logger.error(f"Failed to cleanup restore environment: {e}")
        raise
