#!/usr/bin/env python3
"""PAKE System - Seamless Logging Integration
Implements seamless integration with existing logging library as specified in Phase 2
of the engineering plan. This module wraps existing logging configuration with structlog
to ensure logs from third-party dependencies are captured and processed through the
new structured pipeline.
"""

import logging
import logging.config
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import (
    LoggerFactory,
    add_log_level,
    add_logger_name,
    filter_by_level,
)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class SeamlessLoggingIntegration:
    """Seamless integration between structlog and standard logging library.

    This class implements the seamless integration strategy from the engineering plan,
    ensuring that logs from third-party dependencies using the standard library are
    captured and processed through the new structured pipeline.
    """

    def __init__(self, service_name: str = "pake-system"):
        self.service_name = service_name
        self.original_config = None
        self.integration_complete = False

    def integrate_with_existing_logging(
        self, existing_config: dict[str, Any] | None = None
    ) -> None:
        """Integrate structlog with existing logging configuration.

        Args:
            existing_config: Existing logging configuration dict
        """
        if self.integration_complete:
            return

        # Store original configuration
        if existing_config:
            self.original_config = existing_config.copy()

        # Configure structlog to wrap standard logging
        self._configure_structlog_wrapper()

        # Integrate with existing configuration
        if existing_config:
            self._integrate_with_config(existing_config)
        else:
            self._integrate_with_current_config()

        self.integration_complete = True

    def _configure_structlog_wrapper(self) -> None:
        """Configure structlog to wrap standard logging."""
        # Configure structlog processors
        processors = [
            # Merge context variables
            structlog.contextvars.merge_contextvars,
            # Filter by level
            filter_by_level,
            # Add logger name and level
            add_logger_name,
            add_log_level,
            # Add timestamp
            TimeStamper(fmt="iso"),
            # Add stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # JSON renderer for structured output
            JSONRenderer(),
        ]

        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _integrate_with_config(self, config: dict[str, Any]) -> None:
        """Integrate with provided logging configuration."""
        # Modify formatters to use structlog
        if "formatters" in config:
            for formatter_name, formatter_config in config["formatters"].items():
                if isinstance(formatter_config, dict):
                    # Replace formatter with structlog-compatible one
                    config["formatters"][formatter_name] = {
                        "()": "structlog.stdlib.ProcessorFormatter",
                        "processor": JSONRenderer(),
                    }

        # Apply the modified configuration
        logging.config.dictConfig(config)

    def _integrate_with_current_config(self) -> None:
        """Integrate with current logging configuration."""
        # Get current configuration
        current_config = logging.getLogger().handlers

        # Replace handlers with structlog-compatible ones
        root_logger = logging.getLogger()

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add structlog-compatible handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=JSONRenderer(),
                foreign_pre_chain=[
                    structlog.contextvars.merge_contextvars,
                    filter_by_level,
                    add_logger_name,
                    add_log_level,
                    TimeStamper(fmt="iso"),
                ],
            )
        )

        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)


class DjangoStructlogIntegration:
    """Integration with Django applications using django-structlog.

    This class provides automatic binding of request-specific context
    (e.g., request_id, user_id) to all logs generated during a request.
    """

    def __init__(self):
        self.middleware_configured = False

    def setup_django_middleware(self) -> None:
        """Setup Django middleware for automatic context binding."""
        try:
            import django
            from django.conf import settings

            # Add django-structlog to INSTALLED_APPS if not already present
            if "django_structlog" not in settings.INSTALLED_APPS:
                settings.INSTALLED_APPS.append("django_structlog")

            # Add middleware to MIDDLEWARE if not already present
            middleware_class = "django_structlog.middlewares.RequestMiddleware"
            if middleware_class not in settings.MIDDLEWARE:
                settings.MIDDLEWARE.insert(0, middleware_class)

            self.middleware_configured = True

        except ImportError:
            print("Django not available - skipping Django integration")

    def configure_django_structlog(self) -> None:
        """Configure django-structlog settings."""
        try:
            import django
            from django.conf import settings

            # Configure django-structlog
            settings.STRUCTLOG = {
                "PROCESSORS": [
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.JSONRenderer(),
                ],
                "WRAPPER_CLASS": structlog.stdlib.BoundLogger,
                "LOGGER_FACTORY": structlog.stdlib.LoggerFactory(),
                "CACHE_LOGGER_ON_FIRST_USE": True,
            }

        except ImportError:
            print("Django not available - skipping Django configuration")


class ContextualLoggingManager:
    """Manager for contextual logging using bind_contextvars.

    This class implements the contextual logging standard from the engineering plan,
    using structlog.contextvars.bind_contextvars to attach high-level context at the
    beginning of a process (e.g., an HTTP request).
    """

    def __init__(self):
        self.context_stack = []

    def bind_context(self, **context) -> "ContextualLoggingManager":
        """Bind context variables for the current process.

        Args:
            **context: Context variables to bind

        Returns:
            Context manager for the bound context
        """
        return ContextBindingManager(context)

    def bind_request_context(
        self,
        request_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        **additional_context,
    ) -> "ContextualLoggingManager":
        """Bind request-specific context.

        Args:
            request_id: Unique request identifier
            user_id: User identifier
            session_id: Session identifier
            correlation_id: Correlation identifier for tracing
            **additional_context: Additional context variables

        Returns:
            Context manager for the bound context
        """
        context = {}

        if request_id:
            context["request_id"] = request_id
        if user_id:
            context["user_id"] = user_id
        if session_id:
            context["session_id"] = session_id
        if correlation_id:
            context["correlation_id"] = correlation_id

        context.update(additional_context)

        return self.bind_context(**context)

    def bind_user_context(
        self,
        user_id: str,
        username: str | None = None,
        role: str | None = None,
        **additional_context,
    ) -> "ContextualLoggingManager":
        """Bind user-specific context.

        Args:
            user_id: User identifier
            username: Username
            role: User role
            **additional_context: Additional context variables

        Returns:
            Context manager for the bound context
        """
        context = {"user_id": user_id}

        if username:
            context["username"] = username
        if role:
            context["role"] = role

        context.update(additional_context)

        return self.bind_context(**context)

    def bind_operation_context(
        self, operation: str, operation_id: str | None = None, **additional_context
    ) -> "ContextualLoggingManager":
        """Bind operation-specific context.

        Args:
            operation: Operation name
            operation_id: Unique operation identifier
            **additional_context: Additional context variables

        Returns:
            Context manager for the bound context
        """
        context = {"operation": operation}

        if operation_id:
            context["operation_id"] = operation_id

        context.update(additional_context)

        return self.bind_context(**context)


class ContextBindingManager:
    """Context manager for binding context variables."""

    def __init__(self, context: dict[str, Any]):
        self.context = context
        self.previous_context = {}

    def __enter__(self) -> None:
        """Enter context and bind variables."""
        try:
            import structlog.contextvars

            # Store previous context
            self.previous_context = structlog.contextvars.get_context()

            # Bind new context
            structlog.contextvars.bind_contextvars(**self.context)

        except ImportError:
            print("structlog.contextvars not available - using fallback")

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore previous context."""
        try:
            import structlog.contextvars

            # Restore previous context
            structlog.contextvars.clear_contextvars()
            if self.previous_context:
                structlog.contextvars.bind_contextvars(**self.previous_context)

        except ImportError:
            pass


# Global instances
_seamless_integration = None
_contextual_manager = None


def get_seamless_integration(
    service_name: str = "pake-system",
) -> SeamlessLoggingIntegration:
    """Get or create global seamless integration instance."""
    global _seamless_integration
    if _seamless_integration is None:
        _seamless_integration = SeamlessLoggingIntegration(service_name)
    return _seamless_integration


def get_contextual_manager() -> ContextualLoggingManager:
    """Get or create global contextual logging manager."""
    global _contextual_manager
    if _contextual_manager is None:
        _contextual_manager = ContextualLoggingManager()
    return _contextual_manager


def initialize_seamless_logging(
    service_name: str = "pake-system",
    existing_config: dict[str, Any] | None = None,
    django_integration: bool = False,
) -> None:
    """Initialize seamless logging integration.

    Args:
        service_name: Name of the service
        existing_config: Existing logging configuration
        django_integration: Whether to setup Django integration
    """
    # Get seamless integration instance
    integration = get_seamless_integration(service_name)

    # Integrate with existing logging
    integration.integrate_with_existing_logging(existing_config)

    # Setup Django integration if requested
    if django_integration:
        django_integration = DjangoStructlogIntegration()
        django_integration.setup_django_middleware()
        django_integration.configure_django_structlog()

    # Get contextual manager
    contextual_manager = get_contextual_manager()

    # Log initialization
    logger = structlog.get_logger(service_name)
    logger.info(
        "Seamless logging integration initialized",
        service_name=service_name,
        django_integration=django_integration,
        existing_config_integrated=existing_config is not None,
    )


# Convenience functions for common use cases
def with_request_context(
    request_id: str | None = None, user_id: str | None = None, **context
) -> ContextBindingManager:
    """Convenience function for request context binding."""
    manager = get_contextual_manager()
    return manager.bind_request_context(
        request_id=request_id, user_id=user_id, **context
    )


def with_user_context(
    user_id: str, username: str | None = None, **context
) -> ContextBindingManager:
    """Convenience function for user context binding."""
    manager = get_contextual_manager()
    return manager.bind_user_context(user_id=user_id, username=username, **context)


def with_operation_context(
    operation: str, operation_id: str | None = None, **context
) -> ContextBindingManager:
    """Convenience function for operation context binding."""
    manager = get_contextual_manager()
    return manager.bind_operation_context(
        operation=operation, operation_id=operation_id, **context
    )


# Example usage and testing
if __name__ == "__main__":
    # Test seamless integration
    print("Testing seamless logging integration...")

    # Initialize seamless logging
    initialize_seamless_logging("test-service")

    # Test basic logging
    logger = structlog.get_logger("test-service")
    logger.info("Service started", version="1.0.0")

    # Test contextual logging
    print("Testing contextual logging...")

    with with_request_context(
        request_id="req-123", user_id="user-456", correlation_id="corr-789"
    ):
        logger.info("Processing request with context")

        with with_user_context("user-456", username="john_doe"):
            logger.info("User action", action="login")

        logger.info("Another log message with same request context")

    # Test operation context
    with with_operation_context("data_processing", operation_id="op-001"):
        logger.info("Starting data processing")
        logger.info("Processing completed")

    print("✓ Seamless logging integration test completed")
