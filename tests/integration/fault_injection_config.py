config
#!/usr/bin/env python3
"""
PAKE System - Fault Injection Test Configuration
Configuration and utilities for comprehensive fault injection testing
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aioresponses import aioresponses
import pytest

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of faults to inject during testing"""

    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    MALFORMED_RESPONSE = "malformed_response"
    EMPTY_RESPONSE = "empty_response"
    CONNECTION_ERROR = "connection_error"
    PARTIAL_FAILURE = "partial_failure"


@dataclass
class FaultInjectionConfig:
    """Configuration for fault injection testing"""

    fault_types: list[FaultType]
    failure_rate: float = 0.5  # 50% failure rate
    retry_attempts: int = 3
    timeout_seconds: int = 30
    rate_limit_delay: int = 300  # 5 minutes


class FaultInjector:
    """Utility class for injecting faults into API responses"""

    def __init__(self) -> None:
        self.config = config
        self.fault_count = 0
        self.total_requests = 0

    def should_inject_fault(self) -> bool:
        """Determine if a fault should be injected based on failure rate"""
        self.total_requests += 1
        return (self.fault_count / self.total_requests) < self.config.failure_rate

    def inject_fault(self, fault_type: FaultType) -> dict[str, Any]:
        """Generate fault response based on fault type"""
        self.fault_count += 1

        fault_responses = {
            FaultType.SERVICE_UNAVAILABLE: {
                "status": 503,
                "body": "Service temporarily unavailable",
                "headers": {"Retry-After": "60"},
            },
            FaultType.RATE_LIMIT: {
                "status": 429,
                "body": "Rate limit exceeded",
                "headers": {"Retry-After": str(self.config.rate_limit_delay)},
            },
            FaultType.TIMEOUT: {"exception": TimeoutError("Request timeout")},
            FaultType.MALFORMED_RESPONSE: {
                "status": 200,
                "body": "Invalid JSON response {broken",
            },
            FaultType.EMPTY_RESPONSE: {"status": 200, "body": ""},
            FaultType.CONNECTION_ERROR: {
                "exception": aiohttp.ClientConnectorError(
                    None, OSError("Connection refused")
                )
            },
        }

        return fault_responses.get(fault_type, {})


class FaultInjectionTestMixin:
    """Mixin class providing common fault injection test utilities"""

    @staticmethod
    async def test_service_resilience(self) -> None:
        """Generic test for service resilience against various fault types"""
        fault_injector = FaultInjector(FaultInjectionConfig(fault_types=fault_types))

        for fault_type in fault_types:
            with aioresponses() as m:
                fault_response = fault_injector.inject_fault(fault_type)

                # Apply fault to appropriate endpoints
                if "firecrawl" in str(service_method):
                    m.post("https://api.firecrawl.dev/v0/scrape", **fault_response)
                elif "arxiv" in str(service_method):
                    m.get("http://export.arxiv.org/api/query", **fault_response)
                elif "pubmed" in str(service_method):
                    m.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                        **fault_response,
                    )

                # Execute service method
                result = await service_method(*args, **kwargs)

                # Assert graceful error handling
                assert not result.success
                assert result.error is not None
                assert result.error.error_code in expected_error_codes

                logger.info("Successfully tested %s fault injection", fault_type.value)


class FaultInjectionMetrics:
    """Metrics collection for fault injection testing"""

    def __init__(self) -> None:
        self.fault_injections = {}
        self.successful_recoveries = {}
        self.failed_recoveries = {}
        self.response_times = {}

    def record_fault_injection(self) -> None:
        """Record a fault injection event"""
        key = f"{service}_{fault_type.value}"
        self.fault_injections[key] = self.fault_injections.get(key, 0) + 1

    def record_recovery(self) -> None:
        """Record a recovery attempt"""
        key = f"{service}_{fault_type.value}"
        if successful:
            self.successful_recoveries[key] = self.successful_recoveries.get(key, 0) + 1
        else:
            self.failed_recoveries[key] = self.failed_recoveries.get(key, 0) + 1

    def record_response_time(self) -> None:
        """Record response time for a service call"""
        if service not in self.response_times:
            self.response_times[service] = []
        self.response_times[service].append(response_time_ms)

    def get_summary(self) -> dict[str, Any]:
        """Get summary of fault injection metrics"""
        return {
            "fault_injections": self.fault_injections,
            "successful_recoveries": self.successful_recoveries,
            "failed_recoveries": self.failed_recoveries,
            "average_response_times": {
                service: sum(times) / len(times)
                for service, times in self.response_times.items()
            },
        }


# Pytest fixtures for fault injection testing
@pytest.fixture
def fault_injection_config(self) -> None:
    """Fixture providing fault injection configuration"""
    return FaultInjectionConfig(
        fault_types=[
            FaultType.SERVICE_UNAVAILABLE,
            FaultType.RATE_LIMIT,
            FaultType.TIMEOUT,
            FaultType.MALFORMED_RESPONSE,
            FaultType.CONNECTION_ERROR,
        ],
        failure_rate=0.3,
        retry_attempts=2,
        timeout_seconds=15,
    )


@pytest.fixture
def fault_injector(self) -> None:
    """Fixture providing fault injector instance"""
    return FaultInjector(fault_injection_config)


@pytest.fixture
def fault_injection_metrics(self) -> None:
    """Fixture providing metrics collection for fault injection"""
    return FaultInjectionMetrics()


# Test markers for fault injection
fault_injection_marker = pytest.mark.fault_injection
resilience_marker = pytest.mark.resilience_testing
external_api_marker = pytest.mark.external_api_testing
network_required_marker = pytest.mark.requires_network


def pytest_configure(self) -> None:
    """Configure pytest for fault injection testing"""
    config.addinivalue_line(
        "markers", "fault_injection: Fault injection tests for API resilience"
    )
    config.addinivalue_line(
        "markers", "resilience_testing: Tests for system resilience"
    )
    config.addinivalue_line(
        "markers", "external_api_testing: Tests requiring external API access"
    )


# Utility functions for fault injection testing
async def simulate_network_partition(self) -> None:
    """Simulate network partition for specified service URLs"""
    logger.info(
        "Simulating network partition for %s for %ss", service_urls, duration_seconds
    )

    with aioresponses() as m:
        for url in service_urls:
            m.get(
                url,
                exception=aiohttp.ClientConnectorError(
                    None, OSError("Network unreachable")
                ),
            )
            m.post(
                url,
                exception=aiohttp.ClientConnectorError(
                    None, OSError("Network unreachable")
                ),
            )

        # Wait for partition duration
        await asyncio.sleep(duration_seconds)


async def simulate_cascading_failures(self) -> None:
    """Simulate cascading failures across multiple services"""
    logger.info(
        "Simulating cascading failures for %s with pattern: %s",
        services,
        failure_pattern,
    )

    fault_responses = {
        "linear": [503, 503, 503],  # All services fail
        "exponential": [503, 429, 200],  # Escalating failures
        "random": [503, 200, 429],  # Random failure pattern
    }

    responses = fault_responses.get(failure_pattern, [503])

    with aioresponses() as m:
        for i, service in enumerate(services):
            status = responses[i % len(responses)]
            if "firecrawl" in service:
                m.post("https://api.firecrawl.dev/v0/scrape", status=status)
            elif "arxiv" in service:
                m.get("http://export.arxiv.org/api/query", status=status)
            elif "pubmed" in service:
                m.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    status=status,
                )


def validate_error_handling(self) -> None:
    """Validate that error handling meets resilience requirements"""
    assert result is not None, f"{service_name} should return a result even on failure"

    if hasattr(result, "success"):
        assert not result.success, f"{service_name} should indicate failure"

        if hasattr(result, "error") and result.error:
            assert (
                result.error.error_code in expected_error_codes
            ), f"{service_name} should return appropriate error code"

            if hasattr(result.error, "is_retryable"):
                assert isinstance(
                    result.error.is_retryable, bool
                ), f"{service_name} error should indicate retryability"

    logger.info("✓ %s error handling validated", service_name)


def validate_graceful_degradation(self) -> None:
    """Validate that system gracefully degrades under failures"""
    total_results = len(results)
    successful_results = sum(1 for r in results if hasattr(r, "success") and r.success)

    success_rate = (
        (successful_results / total_results) * 100 if total_results > 0 else 0
    )

    assert (
        success_rate >= min_success_rate
    ), f"System should maintain at least {min_success_rate}% success rate, got {success_rate}%"

    logger.info("✓ Graceful degradation validated: %s% success rate", success_rate)


# Performance testing utilities for fault injection
class FaultInjectionPerformanceTest:
    """Performance testing utilities for fault injection scenarios"""

    @staticmethod
    async def measure_recovery_time(self) -> None:
        """Measure time to recover from a specific fault type"""
        start_time = asyncio.get_event_loop().time()

        fault_injector = FaultInjector(FaultInjectionConfig(fault_types=[fault_type]))

        with aioresponses() as m:
            fault_response = fault_injector.inject_fault(fault_type)

            # Apply fault
            if "firecrawl" in str(service_method):
                m.post("https://api.firecrawl.dev/v0/scrape", **fault_response)
            elif "arxiv" in str(service_method):
                m.get("http://export.arxiv.org/api/query", **fault_response)
            elif "pubmed" in str(service_method):
                m.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    **fault_response,
                )

            # Execute and measure
            result = await service_method(*args, **kwargs)

            end_time = asyncio.get_event_loop().time()
            recovery_time = (end_time - start_time) * 1000  # Convert to milliseconds

            return result, recovery_time

    @staticmethod
    async def stress_test_with_faults(self) -> None:
        """Stress test service under fault injection conditions"""

        async def single_request(self) -> None:
            fault_type = fault_types[hash(asyncio.current_task()) % len(fault_types)]
            return await FaultInjectionPerformanceTest.measure_recovery_time(
                service_method, fault_type, *args, **kwargs
            )

        # Execute concurrent requests
        tasks = [single_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_recoveries = 0
        total_recovery_time = 0

        for result in results:
            if isinstance(result, Exception):
                continue

            if isinstance(result, tuple) and len(result) == 2:
                service_result, recovery_time = result
                if hasattr(service_result, "success") and service_result.success:
                    successful_recoveries += 1
                total_recovery_time += recovery_time

        return {
            "success_rate": (successful_recoveries / concurrent_requests) * 100,
            "average_recovery_time": total_recovery_time / concurrent_requests,
            "total_requests": concurrent_requests,
        }