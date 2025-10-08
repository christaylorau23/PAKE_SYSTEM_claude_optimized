import logging
import random
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)


def terminate_random_api_instance() -> None:
    """Terminate a random API instance."""
    try:
        # Get list of API pods
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "pods",
                "-n",
                "pake-system",
                "-l",
                "app=pake-api",
                "--no-headers",
                "-o",
                "custom-columns=NAME:.metadata.name",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        pods = result.stdout.strip().split("\n")
        if not pods:
            raise Exception("No API pods found")

        # Select random pod
        selected_pod = random.choice(pods)

        # Delete the pod
        subprocess.run(
            ["kubectl", "delete", "pod", selected_pod, "-n", "pake-system"], check=True
        )

        logger.info(f"Terminated API instance: {selected_pod}")
    except Exception as e:
        logger.error(f"Failed to terminate API instance: {e}")
        raise


def restore_api_instance() -> None:
    """Restore API instance."""
    try:
        # Scale up API deployment
        subprocess.run(
            [
                "kubectl",
                "scale",
                "deployment",
                "pake-api",
                "--replicas=3",
                "-n",
                "pake-system",
            ],
            check=True,
        )

        # Wait for pods to be ready
        subprocess.run(
            [
                "kubectl",
                "wait",
                "--for=condition=ready",
                "pod",
                "-l",
                "app=pake-api",
                "-n",
                "pake-system",
                "--timeout=300s",
            ],
            check=True,
        )

        logger.info("API instance restored successfully")
    except Exception as e:
        logger.error(f"Failed to restore API instance: {e}")
        raise
