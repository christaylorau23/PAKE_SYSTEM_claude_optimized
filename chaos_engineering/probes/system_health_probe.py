import logging
import os
import subprocess
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


def check_backup_system_health() -> bool:
    """Check if backup system is healthy."""
    try:
        # Check if backup service is running
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "pods",
                "-n",
                "backup-system",
                "-l",
                "app=backup-service",
                "--no-headers",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return len(result.stdout.strip()) > 0
    except Exception as e:
        logger.error(f"Backup system health check failed: {e}")
        return False


def check_recent_backup_available() -> bool:
    """Check if recent backup is available."""
    try:
        # Check for backups created in last 24 hours
        result = subprocess.run(
            [
                "kubectl",
                "exec",
                "-n",
                "backup-system",
                "backup-service-0",
                "--",
                "find",
                "/backups",
                "-name",
                "*.sql",
                "-mtime",
                "-1",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return len(result.stdout.strip()) > 0
    except Exception as e:
        logger.error(f"Recent backup check failed: {e}")
        return False


def measure_restore_time() -> float:
    """Measure time taken for restore operation."""
    start_time = time.time()

    # Wait for restore to complete
    while True:
        try:
            # Check if restore environment is ready
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    "restore-system",
                    "-l",
                    "app=restore-database",
                    "--no-headers",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            if "Running" in result.stdout:
                break
        except Exception:
            pass

        time.sleep(10)
        if time.time() - start_time > 18000:  # 5 hour timeout
            raise Exception("Restore timeout exceeded")

    return time.time() - start_time
