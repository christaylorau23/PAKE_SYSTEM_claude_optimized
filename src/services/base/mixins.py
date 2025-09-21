#!/usr/bin/env python3
"""PAKE System - Service Mixins
Provides reusable functionality components for services
"""

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from src.utils.exceptions import ValidationException


class LoggingMixin:
    """Mixin for standardized logging functionality"""

    def setup_logging(
        self,
        logger_name: str,
        level: str = "INFO",
        format_string: str | None = None,
    ) -> logging.Logger:
        """Setup standardized logging"""
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        if not logger.handlers:
            handler = logging.StreamHandler()
            if format_string is None:
                format_string = (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "%(funcName)s:%(lineno)d - %(message)s"
                )
            formatter = logging.Formatter(format_string)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def log_operation(
        self,
        logger: logging.Logger,
        operation: str,
        level: str = "INFO",
        **context,
    ) -> None:
        """Log an operation with context"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        message = f"Operation: {operation}"

        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            message += f" | Context: {context_str}"

        logger.log(log_level, message)

    def log_error_with_context(
        self,
        logger: logging.Logger,
        error: Exception,
        operation: str,
        **context,
    ) -> None:
        """Log error with detailed context"""
        error_info = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context,
        }

        logger.error(f"Error in {operation}: {error}", extra=error_info)


class CacheMixin:
    """Mixin for caching functionality"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl: dict[str, datetime] = {}

    def _generate_cache_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments"""
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def cache_get(self, key: str) -> Any | None:
        """Get value from cache"""
        if key not in self._cache:
            return None

        # Check TTL
        if key in self._cache_ttl:
            if datetime.now() > self._cache_ttl[key]:
                self.cache_delete(key)
                return None

        return self._cache[key].get("value")

    def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set value in cache"""
        self._cache[key] = {"value": value, "timestamp": datetime.now()}

        if ttl_seconds:
            self._cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def cache_delete(self, key: str) -> bool:
        """Delete value from cache"""
        deleted = key in self._cache
        self._cache.pop(key, None)
        self._cache_ttl.pop(key, None)
        return deleted

    def cache_clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._cache_ttl.clear()

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        expired_keys = [key for key, ttl in self._cache_ttl.items() if now > ttl]

        return {
            "total_entries": len(self._cache),
            "expired_entries": len(expired_keys),
            "active_entries": len(self._cache) - len(expired_keys),
            "memory_usage_estimate": sum(
                len(str(data)) for data in self._cache.values()
            ),
        }

    def cached(
        self,
        ttl_seconds: int | None = None,
        key_func: Callable | None = None,
    ):
        """Decorator for caching function results"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = (
                        f"{func.__name__}_{self._generate_cache_key(*args, **kwargs)}"
                    )

                # Try to get from cache
                cached_value = self.cache_get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.cache_set(cache_key, result, ttl_seconds)
                return result

            return wrapper

        return decorator


class MetricsMixin:
    """Mixin for metrics collection"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metrics: dict[str, dict[str, Any]] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: str = "gauge",
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a metric value"""
        if name not in self._metrics:
            self._metrics[name] = {
                "type": metric_type,
                "values": [],
                "tags": tags or {},
                "last_updated": datetime.now(),
            }

        self._metrics[name]["values"].append(
            {"value": value, "timestamp": datetime.now()},
        )
        self._metrics[name]["last_updated"] = datetime.now()

        # Keep only last 1000 values
        if len(self._metrics[name]["values"]) > 1000:
            self._metrics[name]["values"] = self._metrics[name]["values"][-1000:]

    def increment_counter(
        self,
        name: str,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric"""
        current = self.get_metric_value(name, default=0)
        self.record_metric(name, current + 1, "counter", tags)

    def record_timing(
        self,
        name: str,
        duration: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a timing metric"""
        self.record_metric(name, duration, "timing", tags)

    def get_metric_value(self, name: str, default: Any = None) -> Any:
        """Get the latest value of a metric"""
        if name not in self._metrics or not self._metrics[name]["values"]:
            return default

        return self._metrics[name]["values"][-1]["value"]

    def get_metric_stats(self, name: str) -> dict[str, Any] | None:
        """Get statistical summary of a metric"""
        if name not in self._metrics or not self._metrics[name]["values"]:
            return None

        values = [v["value"] for v in self._metrics[name]["values"]]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "last": values[-1],
            "type": self._metrics[name]["type"],
            "tags": self._metrics[name]["tags"],
        }

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get all metrics with statistics"""
        return {name: self.get_metric_stats(name) for name in self._metrics}

    def timed(self, metric_name: str, tags: dict[str, str] | None = None):
        """Decorator for timing function execution"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.time() - start_time
                    self.record_timing(metric_name, duration, tags)

            return wrapper

        return decorator


class RetryMixin:
    """Mixin for retry functionality"""

    def retry(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        """Decorator for retrying function execution"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                last_exception = None

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            break

                        wait_time = delay * (backoff_factor**attempt)
                        time.sleep(wait_time)

                raise last_exception

            return wrapper

        return decorator

    async def async_retry(
        self,
        func: Callable,
        *args,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        **kwargs,
    ) -> Any:
        """Async retry with exponential backoff"""
        last_exception = None

        for attempt in range(max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt == max_attempts - 1:
                    break

                wait_time = delay * (backoff_factor**attempt)
                await asyncio.sleep(wait_time)

        raise last_exception


class ValidationMixin:
    """Mixin for data validation functionality"""

    def validate_required_fields(
        self,
        data: dict[str, Any],
        required_fields: list[str],
        field_name: str = "data",
    ) -> None:
        """Validate that required fields are present"""
        missing_fields = [
            field
            for field in required_fields
            if field not in data or data[field] is None
        ]

        if missing_fields:
            raise ValidationException(
                f"Missing required fields in {field_name}: {', '.join(missing_fields)}",
                context={"missing_fields": missing_fields, "field_name": field_name},
            )

    def validate_field_types(
        self,
        data: dict[str, Any],
        field_types: dict[str, type],
        field_name: str = "data",
    ) -> None:
        """Validate field types"""
        type_errors = []

        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    type_errors.append(
                        f"{field} must be {expected_type.__name__}, got {type(data[field]).__name__}",
                    )

        if type_errors:
            raise ValidationException(
                f"Type validation failed for {field_name}: {'; '.join(type_errors)}",
                context={"type_errors": type_errors, "field_name": field_name},
            )

    def validate_field_values(
        self,
        data: dict[str, Any],
        field_validators: dict[str, Callable[[Any], bool]],
        field_name: str = "data",
    ) -> None:
        """Validate field values using custom validators"""
        validation_errors = []

        for field, validator in field_validators.items():
            if field in data and data[field] is not None:
                try:
                    if not validator(data[field]):
                        validation_errors.append(f"{field} failed validation")
                except Exception as e:
                    validation_errors.append(f"{field} validation error: {str(e)}")

        if validation_errors:
            raise ValidationException(
                f"Value validation failed for {field_name}: {'; '.join(validation_errors)}",
                context={
                    "validation_errors": validation_errors,
                    "field_name": field_name,
                },
            )

    def validate_data(
        self,
        data: dict[str, Any],
        schema: dict[str, Any],
        field_name: str = "data",
    ) -> None:
        """Validate data against a schema"""
        # Validate required fields
        if "required" in schema:
            self.validate_required_fields(data, schema["required"], field_name)

        # Validate field types
        if "types" in schema:
            self.validate_field_types(data, schema["types"], field_name)

        # Validate field values
        if "validators" in schema:
            self.validate_field_values(data, schema["validators"], field_name)


# Combined mixin for common service functionality
class ServiceMixin(LoggingMixin, CacheMixin, MetricsMixin, RetryMixin, ValidationMixin):
    """Combined mixin providing all common service functionality"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_service_info(self) -> dict[str, Any]:
        """Get comprehensive service information"""
        return {
            "cache_stats": self.cache_stats(),
            "metrics": self.get_all_metrics(),
            "timestamp": datetime.now().isoformat(),
        }
