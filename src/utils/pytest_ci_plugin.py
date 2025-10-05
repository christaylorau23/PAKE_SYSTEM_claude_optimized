"""PAKE System - CI-Specific pytest Plugin
Provides CI environment simulation and resource constraint testing.
"""

import os
import time
from dataclasses import dataclass
from typing import Any

import psutil
import pytest


@dataclass
class CIResourceLimits:
    """CI resource limits configuration."""

    max_cpu_cores: int = 2
    max_memory_gb: int = 7
    max_workers: int = 1
    timeout_seconds: int = 300
    max_failures: int = 3


class CIResourceMonitor:
    """Monitor resource usage during test execution."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.start_cpu_percent = psutil.cpu_percent()
        self.start_memory = psutil.virtual_memory()
        self.peak_memory_usage = 0
        self.peak_cpu_usage = 0

    def update_peaks(self) -> None:
        """Update peak resource usage."""
        current_memory = psutil.virtual_memory()
        current_cpu = psutil.cpu_percent()

        memory_usage_gb = current_memory.used / (1024**3)
        if memory_usage_gb > self.peak_memory_usage:
            self.peak_memory_usage = memory_usage_gb

        if current_cpu > self.peak_cpu_usage:
            self.peak_cpu_usage = current_cpu

    def get_summary(self) -> dict[str, Any]:
        """Get resource usage summary."""
        current_time = time.time()
        duration = current_time - self.start_time

        return {
            "duration_seconds": duration,
            "peak_memory_gb": round(self.peak_memory_usage, 2),
            "peak_cpu_percent": round(self.peak_cpu_usage, 2),
            "current_memory_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "current_cpu_percent": psutil.cpu_percent(),
            "available_memory_gb": round(
                psutil.virtual_memory().available / (1024**3), 2
            ),
        }


class CIEnvironmentPlugin:
    """pytest plugin for CI environment simulation."""

    def __init__(self) -> None:
        self.config = config
        self.resource_monitor = None
        self.ci_limits = CIResourceLimits()
        self.is_ci_env = self._detect_ci_environment()

    def _detect_ci_environment(self) -> bool:
        """Detect if running in CI environment."""
        ci_indicators = [
            "CI",
            "GITHUB_ACTIONS",
            "TRAVIS",
            "JENKINS",
            "CIRCLECI",
            "BUILDKITE",
            "GITLAB_CI",
        ]
        return any(os.getenv(indicator) for indicator in ci_indicators)

    def _apply_ci_constraints(self) -> None:
        """Apply CI resource constraints."""
        if not self.is_ci_env:
            return

        # Set environment variables for CI simulation
        os.environ["CI"] = "true"
        os.environ["GITHUB_ACTIONS"] = "true"
        os.environ["PYTEST_WORKERS"] = str(self.ci_limits.max_workers)
        os.environ["PYTEST_TIMEOUT"] = str(self.ci_limits.timeout_seconds)

        # Log CI constraints
        print("\n🔧 CI Environment Detected")
        print(f"   CPU Cores: {self.ci_limits.max_cpu_cores}")
        print(f"   Memory: {self.ci_limits.max_memory_gb}GB")
        print(f"   Workers: {self.ci_limits.max_workers}")
        print(f"   Timeout: {self.ci_limits.timeout_seconds}s")

    def pytest_configure(self) -> None:
        """Configure pytest with CI-specific settings."""
        self._apply_ci_constraints()

        # Add CI-specific markers
        config.addinivalue_line(
            "markers", "ci-sensitive: Tests sensitive to CI environment conditions"
        )
        config.addinivalue_line(
            "markers", "ci-only: Tests that should only run in CI environment"
        )
        config.addinivalue_line(
            "markers", "local-only: Tests that should only run locally"
        )
        config.addinivalue_line(
            "markers", "resource-intensive: Tests that consume significant resources"
        )

    def pytest_sessionstart(self) -> None:
        """Start resource monitoring at session start."""
        self.resource_monitor = CIResourceMonitor()
        print("\n🚀 Starting CI Resource Monitoring")

    def pytest_sessionfinish(self) -> None:
        """Finish resource monitoring and report results."""
        if self.resource_monitor:
            summary = self.resource_monitor.get_summary()
            print("\n📊 CI Resource Usage Summary:")
            print(f"   Duration: {summary['duration_seconds']:.1f}s")
            print(f"   Peak Memory: {summary['peak_memory_gb']}GB")
            print(f"   Peak CPU: {summary['peak_cpu_percent']}%")
            print(f"   Current Memory: {summary['current_memory_gb']}GB")
            print(f"   Available Memory: {summary['available_memory_gb']}GB")

            # Check against CI limits
            if summary["peak_memory_gb"] > self.ci_limits.max_memory_gb:
                print(
                    f"⚠️  WARNING: Peak memory usage ({summary['peak_memory_gb']}GB) exceeds CI limit ({self.ci_limits.max_memory_gb}GB)"
                )

    def pytest_runtest_setup(self) -> None:
        """Setup before each test."""
        if self.resource_monitor:
            self.resource_monitor.update_peaks()

    def pytest_runtest_teardown(self) -> None:
        """Teardown after each test."""
        if self.resource_monitor:
            self.resource_monitor.update_peaks()

    def pytest_collection_modifyitems(self) -> None:
        """Modify test collection based on CI environment."""
        if self.is_ci_env:
            # Skip local-only tests in CI
            for item in items:
                if item.get_closest_marker("local-only"):
                    item.add_marker(
                        pytest.mark.skip(
                            reason="Skipping local-only test in CI environment"
                        )
                    )
        else:
            # Skip CI-only tests locally (unless explicitly requested)
            ci_only_requested = config.getoption("--ci-only", default=False)
            if not ci_only_requested:
                for item in items:
                    if item.get_closest_marker("ci-only"):
                        item.add_marker(
                            pytest.mark.skip(
                                reason="Skipping CI-only test in local environment"
                            )
                        )


def pytest_addoption(self) -> None:
    """Add CI-specific command line options."""
    parser.addoption(
        "--ci-only",
        action="store_true",
        default=False,
        help="Run CI-only tests even in local environment",
    )
    parser.addoption(
        "--ci-simulation",
        action="store_true",
        default=False,
        help="Simulate CI environment constraints locally",
    )
    parser.addoption(
        "--ci-workers",
        type=int,
        default=1,
        help="Number of workers for CI simulation (default: 1)",
    )
    parser.addoption(
        "--ci-timeout",
        type=int,
        default=300,
        help="Timeout for CI simulation in seconds (default: 300)",
    )


def pytest_configure(self) -> None:
    """Configure pytest with CI plugin."""
    if config.getoption("--ci-simulation") or os.getenv("CI"):
        config.pluginmanager.register(CIEnvironmentPlugin(config))


# Utility functions for test authors
def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))


def skip_if_not_ci(self) -> None:
    """Skip test if not running in CI environment."""
    return pytest.mark.skipif(not is_ci_environment(), reason=reason)


def skip_if_ci(self) -> None:
    """Skip test if running in CI environment."""
    return pytest.mark.skipif(is_ci_environment(), reason=reason)


def ci_sensitive(self) -> None:
    """Mark test as CI-sensitive."""
    return pytest.mark.ci_sensitive(reason=reason)


def resource_intensive(self) -> None:
    """Mark test as resource-intensive."""
    return pytest.mark.resource_intensive(reason=reason)
