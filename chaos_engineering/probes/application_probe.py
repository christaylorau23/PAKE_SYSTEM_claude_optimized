import logging
import os
import time
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


def check_application_health() -> bool:
    """Check if application is healthy."""
    try:
        response = requests.get(f"{os.getenv('CHAOS_STAGING_URL')}/health", timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Application health check failed: {e}")
        return False


def check_api_instances_health() -> bool:
    """Check if all API instances are healthy."""
    try:
        response = requests.get(
            f"{os.getenv('CHAOS_STAGING_URL')}/api/v1/instances/health", timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("healthy_instances", 0) > 0
        return False
    except Exception as e:
        logger.error(f"API instances health check failed: {e}")
        return False


def check_load_balancer_health() -> bool:
    """Check if load balancer is healthy."""
    try:
        response = requests.get(
            f"{os.getenv('CHAOS_STAGING_URL')}/api/v1/loadbalancer/health", timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Load balancer health check failed: {e}")
        return False


def measure_error_rate_during_failure() -> float:
    """Measure error rate during instance failure."""
    error_count = 0
    total_requests = 100

    for _ in range(total_requests):
        try:
            response = requests.get(
                f"{os.getenv('CHAOS_STAGING_URL')}/api/v1/health", timeout=5
            )
            if response.status_code >= 500:
                error_count += 1
        except Exception:
            error_count += 1

        time.sleep(0.1)

    return error_count / total_requests


def measure_latency_during_failure() -> float:
    """Measure latency during instance failure."""
    latencies = []

    for _ in range(50):
        start_time = time.time()
        try:
            response = requests.get(
                f"{os.getenv('CHAOS_STAGING_URL')}/api/v1/health", timeout=10
            )
            if response.status_code == 200:
                latencies.append((time.time() - start_time) * 1000)  # Convert to ms
        except Exception:
            latencies.append(10000)  # 10 second timeout

        time.sleep(0.1)

    return sum(latencies) / len(latencies) if latencies else 10000


def verify_load_balancer_redirect() -> bool:
    """Verify load balancer redirects traffic to healthy instances."""
    try:
        # Make multiple requests and verify they're distributed
        responses = []
        for _ in range(10):
            response = requests.get(
                f"{os.getenv('CHAOS_STAGING_URL')}/api/v1/health", timeout=5
            )
            responses.append(response.status_code == 200)

        # At least 80% of requests should succeed
        success_rate = sum(responses) / len(responses)
        return success_rate >= 0.8
    except Exception as e:
        logger.error(f"Load balancer redirect verification failed: {e}")
        return False


def check_application_recovery() -> bool:
    """Check if application has recovered after database failover."""
    try:
        response = requests.get(f"{os.getenv('CHAOS_STAGING_URL')}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
        return False
    except Exception as e:
        logger.error(f"Application recovery check failed: {e}")
        return False


def test_application_functionality() -> bool:
    """Test application functionality after restore."""
    try:
        # Test basic API endpoints
        endpoints = [
            "/api/v1/health",
            "/api/v1/users/me",
            "/api/v1/documents",
            "/api/v1/research/sessions",
        ]

        for endpoint in endpoints:
            response = requests.get(
                f"{os.getenv('CHAOS_RESTORE_URL')}{endpoint}", timeout=10
            )
            if response.status_code not in [200, 401, 403]:  # Allow auth errors
                logger.error(f"Endpoint {endpoint} returned {response.status_code}")
                return False

        return True
    except Exception as e:
        logger.error(f"Application functionality test failed: {e}")
        return False
