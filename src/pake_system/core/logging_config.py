"""Enterprise logging configuration for PAKE System
Structured logging with correlation IDs and comprehensive monitoring
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any


class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        # Add correlation ID if not present
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "no-correlation-id"
        return True


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for enterprise logging."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "no-correlation-id"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", enable_json: bool = True) -> None:
    """Setup enterprise logging configuration."""
    # Base configuration
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation": {
                "()": CorrelationFilter,
            }
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
            },
            "json": {
                "()": StructuredFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if enable_json else "detailed",
                "filters": ["correlation"],
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "json" if enable_json else "detailed",
                "filters": ["correlation"],
                "filename": "logs/pake_system.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "pake_system": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "fastapi": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }

    # Apply configuration
    logging.config.dictConfig(config)

    # Create logs directory if it doesn't exist
    import os

    os.makedirs("logs", exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with correlation ID support."""
    return logging.getLogger(f"pake_system.{name}")


# Initialize logging
setup_logging()
