#!/usr/bin/env python3
"""PAKE+ Circuit Breaker Implementation
Advanced circuit breaker patterns for MCP servers and external service calls
"""

import asyncio
import functools
import json
import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from utils.error_handling import ErrorCategory, PAKEException
from utils.logger import get_logger
from utils.metrics import MetricsStore

logger = get_logger(service_name="pake-circuit-breaker")
metrics = MetricsStore(service_name="pake-circuit-breaker")


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class FailureType(Enum):
    """Types of failures that can trigger circuit breaker"""

    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    HTTP_ERROR = "http_error"
    SLOW_RESPONSE = "slow_response"
    RATE_LIMIT = "rate_limit"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""

    # Failure thresholds
    failure_threshold: int = 5  # Number of failures to open circuit
    success_threshold: int = 3  # Number of successes to close circuit
    timeout_threshold: float = 10.0  # Timeout in seconds
    slow_response_threshold: float = 5.0  # Slow response threshold

    # Time windows
    recovery_timeout: float = 60.0  # Time to wait before half-open
    rolling_window_size: int = 100  # Number of recent calls to track
    minimum_requests: int = 10  # Minimum requests before considering statistics

    # Rate limiting
    max_requests_per_second: float = 100.0
    burst_capacity: int = 200

    # Monitoring
    enable_metrics: bool = True
    log_state_changes: bool = True
    alert_on_open: bool = True

    # Fallback behavior
    fail_fast: bool = True
    fallback_response: Any = None


@dataclass
class CallResult:
    """Result of a circuit-protected call"""

    success: bool
    duration: float
    timestamp: float
    failure_type: FailureType | None = None
    exception: Exception | None = None
    response_data: Any = None


class CircuitBreakerError(PAKEException):
    """Circuit breaker specific errors"""

    def __init__(self, message: str, state: CircuitState, **kwargs):
        super().__init__(message, category=ErrorCategory.SYSTEM, **kwargs)
        self.circuit_state = state


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity  # maximum tokens
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens"""
        with self._lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens"""
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.rate


class CircuitBreaker:
    """Advanced circuit breaker with comprehensive failure detection"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.logger = get_logger(service_name=f"circuit-breaker-{name}")
        self.metrics = (
            MetricsStore(service_name=f"circuit-breaker-{name}")
            if config.enable_metrics
            else None
        )

        # Circuit state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._last_state_change = time.time()

        # Call tracking
        self._recent_calls: list[CallResult] = []
        self._lock = asyncio.Lock()

        # Rate limiting
        self._rate_limiter = RateLimiter(
            config.max_requests_per_second,
            config.burst_capacity,
        )

        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate"""
        if len(self._recent_calls) < self.config.minimum_requests:
            return 0.0

        failures = sum(1 for call in self._recent_calls if not call.success)
        return failures / len(self._recent_calls)

    @property
    def average_response_time(self) -> float:
        """Calculate average response time"""
        if not self._recent_calls:
            return 0.0
        return statistics.mean(call.duration for call in self._recent_calls)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self._state != CircuitState.OPEN:
            return False

        time_since_failure = time.time() - self._last_failure_time
        return time_since_failure >= self.config.recovery_timeout

    def _record_call(self, result: CallResult) -> None:
        """Record call result for statistics"""
        self._recent_calls.append(result)

        # Keep only recent calls within rolling window
        if len(self._recent_calls) > self.config.rolling_window_size:
            self._recent_calls = self._recent_calls[-self.config.rolling_window_size :]

        # Update counters
        self._total_calls += 1
        if result.success:
            self._total_successes += 1
        else:
            self._total_failures += 1

    def _transition_to_state(self, new_state: CircuitState, reason: str = "") -> None:
        """Transition circuit to new state"""
        if new_state == self._state:
            return

        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if self.config.log_state_changes:
            self.logger.info(
                f"Circuit breaker '{self.name}' transitioned from {old_state.value} to {
                    new_state.value
                }",
                extra={"reason": reason, "failure_count": self._failure_count},
            )

        if self.metrics:
            self.metrics.increment_counter(
                "circuit_breaker_state_changes",
                labels={
                    "name": self.name,
                    "from_state": old_state.value,
                    "to_state": new_state.value,
                },
            )

        # Alert on circuit opening
        if new_state == CircuitState.OPEN and self.config.alert_on_open:
            self.logger.error(
                f"ALERT: Circuit breaker '{self.name}' opened due to failures",
                extra={
                    "failure_count": self._failure_count,
                    "failure_rate": self.failure_rate,
                    "recent_calls": len(self._recent_calls),
                },
            )

    def _handle_success(self, result: CallResult) -> None:
        """Handle successful call"""
        self._record_call(result)

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._failure_count = 0
                self._success_count = 0
                self._transition_to_state(
                    CircuitState.CLOSED,
                    "Success threshold reached",
                )
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            if self._failure_count > 0:
                self._failure_count = max(0, self._failure_count - 1)

    def _handle_failure(self, result: CallResult) -> None:
        """Handle failed call"""
        self._record_call(result)
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Go back to open on any failure in half-open state
            self._failure_count += 1
            self._success_count = 0
            self._transition_to_state(
                CircuitState.OPEN,
                f"Failure in half-open: {result.failure_type}",
            )
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1

            # Check if should open circuit
            should_open = self._failure_count >= self.config.failure_threshold or (
                len(self._recent_calls) >= self.config.minimum_requests
                and self.failure_rate >= 0.5
            )  # 50% failure rate

            if should_open:
                self._transition_to_state(
                    CircuitState.OPEN,
                    f"Failure threshold reached: {self._failure_count} failures",
                )

    async def _execute_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout"""
        try:
            return await asyncio.wait_for(
                (
                    func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                ),
                timeout=self.config.timeout_threshold,
            )
        except TimeoutError as e:
            raise CircuitBreakerError(
                f"Operation timed out after {self.config.timeout_threshold}s",
                state=self._state,
                original_exception=e,
            )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            # Check rate limiting
            if not self._rate_limiter.acquire():
                wait_time = self._rate_limiter.wait_time()
                if wait_time > 0:
                    if self.config.fail_fast:
                        raise CircuitBreakerError(
                            f"Rate limit exceeded. Wait {wait_time:.2f}s",
                            state=self._state,
                        )
                    await asyncio.sleep(wait_time)

            # Check circuit state
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_state(
                        CircuitState.HALF_OPEN,
                        "Recovery timeout reached",
                    )
                else:
                    if self.config.fail_fast:
                        if self.config.fallback_response is not None:
                            return self.config.fallback_response
                        raise CircuitBreakerError(
                            f"Circuit breaker '{self.name}' is OPEN",
                            state=self._state,
                        )

        # Execute the call
        start_time = time.time()
        result = CallResult(success=False, duration=0.0, timestamp=start_time)

        try:
            response = await self._execute_with_timeout(func, *args, **kwargs)

            # Check for slow response
            duration = time.time() - start_time
            result.duration = duration
            result.timestamp = start_time
            result.response_data = response

            if duration > self.config.slow_response_threshold:
                result.success = False
                result.failure_type = FailureType.SLOW_RESPONSE
                self._handle_failure(result)

                if self.metrics:
                    self.metrics.record_histogram(
                        "circuit_breaker_slow_calls",
                        duration,
                        labels={"name": self.name},
                    )

                # Still return the response for slow calls
                return response
            result.success = True
            self._handle_success(result)

            if self.metrics:
                self.metrics.record_histogram(
                    "circuit_breaker_success_duration",
                    duration,
                    labels={"name": self.name},
                )

            return response

        except TimeoutError:
            result.duration = time.time() - start_time
            result.failure_type = FailureType.TIMEOUT
            result.timestamp = start_time
            self._handle_failure(result)

            if self.metrics:
                self.metrics.increment_counter(
                    "circuit_breaker_timeouts",
                    labels={"name": self.name},
                )

            raise

        except Exception as e:
            result.duration = time.time() - start_time
            result.failure_type = FailureType.EXCEPTION
            result.exception = e
            result.timestamp = start_time
            self._handle_failure(result)

            if self.metrics:
                self.metrics.increment_counter(
                    "circuit_breaker_exceptions",
                    labels={"name": self.name, "exception_type": type(e).__name__},
                )

            raise

    def get_statistics(self) -> dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_rate": self.failure_rate,
            "average_response_time": self.average_response_time,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
            "recent_calls": len(self._recent_calls),
            "rate_limiter": {
                "tokens_available": self._rate_limiter.tokens,
                "rate": self._rate_limiter.rate,
                "capacity": self._rate_limiter.capacity,
            },
        }

    async def reset(self) -> None:
        """Manually reset circuit breaker"""
        async with self._lock:
            self._failure_count = 0
            self._success_count = 0
            self._recent_calls.clear()
            self._transition_to_state(CircuitState.CLOSED, "Manual reset")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self.logger = get_logger(service_name="circuit-breaker-registry")

    def create_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create and register a new circuit breaker"""
        if name in self._breakers:
            raise ValueError(f"Circuit breaker '{name}' already exists")

        breaker = CircuitBreaker(name, config)
        self._breakers[name] = breaker

        self.logger.info(f"Created circuit breaker: {name}")
        return breaker

    def get_breaker(self, name: str) -> CircuitBreaker:
        """Get circuit breaker by name"""
        if name not in self._breakers:
            raise ValueError(f"Circuit breaker '{name}' not found")
        return self._breakers[name]

    def list_breakers(self) -> list[str]:
        """List all circuit breaker names"""
        return list(self._breakers.keys())

    def get_all_statistics(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_statistics() for name, breaker in self._breakers.items()
        }

    async def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()
        self.logger.info("Reset all circuit breakers")


# Global registry instance
circuit_registry = CircuitBreakerRegistry()


# Decorators for easy circuit breaker integration
def with_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
    registry: CircuitBreakerRegistry = circuit_registry,
):
    """Decorator to add circuit breaker protection to functions"""

    def decorator(func: Callable) -> Callable:
        # Create circuit breaker if it doesn't exist
        try:
            breaker = registry.get_breaker(name)
        except ValueError:
            breaker_config = config or CircuitBreakerConfig()
            breaker = registry.create_breaker(name, breaker_config)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(breaker.call(func, *args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Specialized circuit breakers for PAKE system components
def create_mcp_server_breaker() -> CircuitBreakerConfig:
    """Create circuit breaker config optimized for MCP servers"""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_threshold=30.0,
        slow_response_threshold=10.0,
        recovery_timeout=60.0,
        rolling_window_size=50,
        minimum_requests=5,
        max_requests_per_second=50.0,
        burst_capacity=100,
        enable_metrics=True,
        log_state_changes=True,
        alert_on_open=True,
        fail_fast=True,
    )


def create_database_breaker() -> CircuitBreakerConfig:
    """Create circuit breaker config optimized for database calls"""
    return CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout_threshold=15.0,
        slow_response_threshold=5.0,
        recovery_timeout=30.0,
        rolling_window_size=100,
        minimum_requests=10,
        max_requests_per_second=200.0,
        burst_capacity=400,
        enable_metrics=True,
        log_state_changes=True,
        alert_on_open=True,
        fail_fast=False,  # Don't fail fast for database, allow retries
    )


def create_external_api_breaker() -> CircuitBreakerConfig:
    """Create circuit breaker config optimized for external API calls"""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_threshold=20.0,
        slow_response_threshold=10.0,
        recovery_timeout=120.0,  # Longer recovery for external services
        rolling_window_size=30,
        minimum_requests=5,
        max_requests_per_second=10.0,  # Conservative for external APIs
        burst_capacity=20,
        enable_metrics=True,
        log_state_changes=True,
        alert_on_open=True,
        fail_fast=True,
        fallback_response={"error": "Service temporarily unavailable"},
    )


# Health check integration
async def circuit_breaker_health_check() -> dict[str, Any]:
    """Health check for all circuit breakers"""
    stats = circuit_registry.get_all_statistics()

    healthy_breakers = sum(1 for stat in stats.values() if stat["state"] == "closed")
    total_breakers = len(stats)

    health_status = {
        "overall_health": (
            "healthy" if healthy_breakers == total_breakers else "degraded"
        ),
        "healthy_breakers": healthy_breakers,
        "total_breakers": total_breakers,
        "breakers": stats,
    }

    return health_status


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import random

    async def unreliable_service():
        """Simulate an unreliable service"""
        await asyncio.sleep(random.uniform(0.1, 2.0))
        if random.random() < 0.3:  # 30% failure rate
            raise Exception("Service failure")
        return {"status": "success", "data": "response"}

    async def slow_service():
        """Simulate a slow service"""
        await asyncio.sleep(random.uniform(8, 12))  # Slower than threshold
        return {"status": "slow_success"}

    @with_circuit_breaker("test_service", create_external_api_breaker())
    async def protected_service_call():
        """Example protected service call"""
        return await unreliable_service()

    async def main():
        print("Testing Circuit Breaker Implementation")

        # Test multiple calls
        for i in range(20):
            try:
                result = await protected_service_call()
                print(f"Call {i + 1}: Success - {result}")
            except CircuitBreakerError as e:
                print(f"Call {i + 1}: Circuit breaker blocked - {e.message}")
            except Exception as e:
                print(f"Call {i + 1}: Failed - {str(e)}")

            await asyncio.sleep(0.5)

        # Print statistics
        stats = circuit_registry.get_all_statistics()
        print("\nCircuit Breaker Statistics:")
        print(json.dumps(stats, indent=2))

        # Health check
        health = await circuit_breaker_health_check()
        print("\nHealth Check:")
        print(json.dumps(health, indent=2))

    asyncio.run(main())
