import logging
import os
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)


def terminate_primary_database() -> None:
    """Terminate primary database instance."""
    try:
        # Scale down primary database
        subprocess.run(
            [
                "kubectl",
                "scale",
                "statefulset",
                "pake-postgresql-primary",
                "--replicas=0",
                "-n",
                "database",
            ],
            check=True,
        )

        logger.info("Primary database terminated successfully")
    except Exception as e:
        logger.error(f"Failed to terminate primary database: {e}")
        raise


def restore_primary_database() -> None:
    """Restore primary database instance."""
    try:
        # Scale up primary database
        subprocess.run(
            [
                "kubectl",
                "scale",
                "statefulset",
                "pake-postgresql-primary",
                "--replicas=1",
                "-n",
                "database",
            ],
            check=True,
        )

        # Wait for database to be ready
        subprocess.run(
            [
                "kubectl",
                "wait",
                "--for=condition=ready",
                "pod",
                "-l",
                "app=pake-postgresql-primary",
                "-n",
                "database",
                "--timeout=300s",
            ],
            check=True,
        )

        logger.info("Primary database restored successfully")
    except Exception as e:
        logger.error(f"Failed to restore primary database: {e}")
        raise


def restore_database_from_backup() -> None:
    """Restore database from backup."""
    try:
        backup_id = os.getenv("CHAOS_BACKUP_ID")
        if not backup_id:
            raise Exception("CHAOS_BACKUP_ID environment variable not set")

        # Restore from backup
        subprocess.run(
            [
                "kubectl",
                "exec",
                "-n",
                "database",
                "pake-postgresql-restore-0",
                "--",
                "pg_restore",
                "--clean",
                "--if-exists",
                "--verbose",
                f"/backups/{backup_id}.sql",
            ],
            check=True,
        )

        logger.info(f"Database restored from backup {backup_id}")
    except Exception as e:
        logger.error(f"Failed to restore database from backup: {e}")
        raise
