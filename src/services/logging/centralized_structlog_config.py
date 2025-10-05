#!/usr/bin/env python3
"""PAKE System - Centralized Structured Logging Configuration
Implements the production processor chain as specified in the engineering plan.
This module provides a single, standardized structlog configuration for all services.
"""

import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

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


class ContextVarsProcessor:
    """Merges context bound via bind_contextvars into the log entry."""

    def __call__(
        self, logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Process context variables."""
        # Import here to avoid circular imports
        try:
            import structlog.contextvars

            context_vars = structlog.contextvars.get_context()
            if context_vars:
                event_dict.update(context_vars)
        except ImportError:
            # Fallback if contextvars not available
            pass
        return event_dict


class StackInfoRenderer:
    """Renders stack trace information for exceptions."""

    def __call__(
        self, logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Add stack info to log entry."""
        if "exc_info" in event_dict and event_dict["exc_info"]:
            import traceback

            event_dict["stack_info"] = traceback.format_stack()
        return event_dict


class FormatExcInfo:
    """Formats exception tuples into a readable string."""

    def __call__(
        self, logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Format exception info."""
        if "exc_info" in event_dict and event_dict["exc_info"]:
            import traceback

            event_dict["exception"] = "".join(
                traceback.format_exception(*event_dict["exc_info"])
            )
            del event_dict["exc_info"]
        return event_dict


def configure_structlog_production(
    service_name: str = "pake-system",
    environment: str = None,
    log_level: str = "INFO",
    json_format: bool = True,
    file_logging: bool = True,
    log_directory: str = "logs",
) -> structlog.BoundLogger:
    """Configure structlog with the production processor chain.

    This implements the exact processor chain specified in Table 3.1 of the engineering plan:
    1. structlog.contextvars.merge_contextvars
    2. structlog.stdlib.filter_by_level
    3. structlog.stdlib.add_logger_name
    4. structlog.stdlib.add_log_level
    5. structlog.processors.TimeStamper(fmt="iso")
    6. structlog.processors.StackInfoRenderer()
    7. structlog.processors.format_exc_info
    8. structlog.processors.JSONRenderer()

    Args:
        service_name: Name of the service
        environment: Environment (development, staging, production)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
        file_logging: Whether to enable file logging
        log_directory: Directory for log files

    Returns:
        Configured structlog logger
    """
    # Set defaults
    environment = environment or os.getenv("ENVIRONMENT", "development")

    # Create log directory if file logging is enabled
    if file_logging:
        log_path = Path(log_directory)
        log_path.mkdir(exist_ok=True)

    # Configure the production processor chain as specified in the engineering plan
    processors = [
        # 1. Merge context bound via bind_contextvars into the log entry
        ContextVarsProcessor(),
        # 2. Filter logs based on the standard library's configured log level
        filter_by_level,
        # 3. Add the name of the logger that emitted the message
        add_logger_name,
        # 4. Add the log level (e.g., "info", "error") to the event dictionary
        add_log_level,
        # 5. Add a standardized ISO 8601 formatted timestamp
        TimeStamper(fmt="iso"),
        # 6. Render stack trace information for exceptions
        StackInfoRenderer(),
        # 7. Format exception tuples into a readable string
        FormatExcInfo(),
    ]

    # 8. Serialize the final, enriched event dictionary into a JSON string for output
    if json_format:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[],
    )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logging.getLogger().addHandler(console_handler)

    # Add file handler if enabled
    if file_logging:
        try:
            from logging.handlers import RotatingFileHandler

            log_file = Path(log_directory) / f"{service_name}.log"
            max_bytes = 10 * 1024 * 1024  # 10MB

            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=5, encoding="utf-8"
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            logging.getLogger().addHandler(file_handler)

        except Exception as e:
            print(f"Failed to setup file logging: {e}", file=sys.stderr)

    # Return configured logger
    return structlog.get_logger(service_name)


def setup_contextual_logging() -> None:
    """Setup contextual logging with bind_contextvars.

    This implements the contextual logging standard from the engineering plan,
    using structlog.contextvars.bind_contextvars to attach high-level context
    at the beginning of a process (e.g., an HTTP request).
    """
    try:
        import structlog.contextvars

        # This will be used by services to bind context at the start of processes
        # Example usage:
        # structlog.contextvars.bind_contextvars(
        #     request_id="req-123",
        #     user_id="user-456",
        #     correlation_id="corr-789"
        # )

        # The context will automatically be included in every subsequent log message
        # generated within that process

    except ImportError:
        print("Warning: structlog.contextvars not available", file=sys.stderr)


def get_configured_logger(service_name: str = "pake-system") -> structlog.BoundLogger:
    """Get a configured structlog logger for a service.

    Args:
        service_name: Name of the service

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(service_name)


# Global configuration function
def initialize_logging(
    service_name: str = "pake-system",
    environment: str = None,
    log_level: str = None,
    json_format: bool = None,
    file_logging: bool = None,
) -> structlog.BoundLogger:
    """Initialize logging for the PAKE system.

    This function should be called once at application startup to configure
    the entire logging infrastructure according to the engineering plan.

    Args:
        service_name: Name of the service
        environment: Environment (development, staging, production)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
        file_logging: Whether to enable file logging

    Returns:
        Configured structlog logger
    """
    # Use environment variables for configuration
    environment = environment or os.getenv("ENVIRONMENT", "development")
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    json_format = (
        json_format
        if json_format is not None
        else os.getenv("JSON_LOGGING", "true").lower() == "true"
    )
    file_logging = (
        file_logging
        if file_logging is not None
        else os.getenv("FILE_LOGGING", "true").lower() == "true"
    )

    # Configure structlog with production processor chain
    logger = configure_structlog_production(
        service_name=service_name,
        environment=environment,
        log_level=log_level,
        json_format=json_format,
        file_logging=file_logging,
    )

    # Setup contextual logging
    setup_contextual_logging()

    # Log initialization
    logger.info(
        "Logging initialized",
        service_name=service_name,
        environment=environment,
        log_level=log_level,
        json_format=json_format,
        file_logging=file_logging,
    )

    return logger


# Example usage and testing
if __name__ == "__main__":
    # Initialize logging
    logger = initialize_logging("test-service")

    # Test basic logging
    logger.info("Service started", version="1.0.0")
    logger.debug("Debug message", extra_data={"key": "value"})

    # Test contextual logging
    try:
        import structlog.contextvars

        with structlog.contextvars.bound_contextvars(
            request_id="req-123", user_id="user-456", correlation_id="corr-789"
        ):
            logger.info("Processing request with context")
            logger.info("Another log message with same context")

    except ImportError:
        logger.info("Contextual logging not available")

    # Test error logging
    try:
        msg = "Test error"
        raise ValueError(msg)
    except Exception as e:
        logger.error("An error occurred", error=str(e), exc_info=True)

    # Test structured logging
    logger.info(
        "User action completed",
        user_id="user-123",
        action="login",
        success=True,
        duration_ms=150.5,
    )
