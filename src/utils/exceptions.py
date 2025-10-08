#!/usr/bin/env python3
"""PAKE System - Centralized Exception Hierarchy
Provides consistent error handling patterns across the entire system.
"""

from datetime import UTC, datetime
from enum import Enum
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization."""

    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"
    SERVICE = "service"
    EXTERNAL_API = "external_api"
    PROCESSING = "processing"
    FILESYSTEM = "filesystem"
    IMPORT = "import"
    UNKNOWN = "unknown"


class PAKEException(Exception):
    """Base exception class for all PAKE system errors.

    Provides structured error information for consistent handling
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory | None = None,
        context: dict[str, Any] | None = None,
        error_code: str | None = None,
        severity: ErrorSeverity | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now(UTC)

    def _generate_error_code(self) -> str:
        """Generate a unique error code based on class name."""
        class_name = self.__class__.__name__
        timestamp = self.timestamp.strftime("%Y%m%d%H%M%S")
        return f"{class_name}_{timestamp}"

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "type": self.__class__.__name__,
            "original_exception": (
                str(self.original_exception) if self.original_exception else None
            ),
        }

    def log_error(self) -> None:
        """Log the error with appropriate level based on severity."""
        error_dict = self.to_dict()

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                "Critical error [%s]: %s",
                self.error_code,
                self.message,
                extra=error_dict,
            )
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(
                "High severity error [%s]: %s",
                self.error_code,
                self.message,
                extra=error_dict,
            )
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                "Medium severity error [%s]: %s",
                self.error_code,
                self.message,
                extra=error_dict,
            )
        else:
            logger.info(
                "Low severity error [%s]: %s",
                self.error_code,
                self.message,
                extra=error_dict,
            )


# Configuration Exceptions
class ConfigurationException(PAKEException):
    """Configuration-related errors."""

    def __init__(
        self,
        config_key: Any = None,
        expected: Any = None,
        kwargs: Any = None,
        message: Any = None,
        value: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class MissingConfigurationException(ConfigurationException):
    """Missing required configuration."""

    def __init__(
        self,
        config_key: Any = None,
        expected: Any = None,
        kwargs: Any = None,
        message: Any = None,
        value: Any = None,
    ) -> None:
        message = f"Missing required configuration: {config_key}"
        super().__init__(message, context={"config_key": config_key}, **kwargs)


class InvalidConfigurationException(ConfigurationException):
    """Invalid configuration value."""

    def __init__(
        self,
        config_key: Any = None,
        expected: Any = None,
        kwargs: Any = None,
        message: Any = None,
        value: Any = None,
    ) -> None:
        message = f"Invalid configuration value for {config_key}: {value} (expected {expected})"
        super().__init__(
            message,
            context={"config_key": config_key, "value": value, "expected": expected},
            **kwargs,
        )


# Authentication & Authorization Exceptions
class AuthenticationException(PAKEException):
    """Authentication-related errors."""

    def __init__(self, kwargs: Any = None, message: Any = None) -> None:
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class AuthorizationException(PAKEException):
    """Authorization-related errors."""

    def __init__(
        self, field: Any = None, kwargs: Any = None, message: Any = None
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class InvalidCredentialsException(AuthenticationException):
    """Invalid authentication credentials."""


class TokenExpiredException(AuthenticationException):
    """Authentication token has expired."""


class InsufficientPermissionsException(AuthorizationException):
    """User lacks required permissions."""


class SecurityException(PAKEException):
    """Security-related errors."""

    def __init__(
        self,
        expected_format: Any = None,
        field: Any = None,
        kwargs: Any = None,
        message: Any = None,
        value: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


# Validation Exceptions
class ValidationException(PAKEException):
    """Data validation errors."""

    def __init__(
        self,
        expected_format: Any = None,
        field: Any = None,
        kwargs: Any = None,
        message: Any = None,
        value: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context={"field": field} if field else None,
            **kwargs,
        )


class RequiredFieldException(ValidationException):
    """Required field is missing."""

    def __init__(
        self,
        api_name: Any = None,
        expected_format: Any = None,
        field: Any = None,
        kwargs: Any = None,
        message: Any = None,
        retry_after: Any = None,
        status_code: Any = None,
        value: Any = None,
    ) -> None:
        message = f"Required field is missing: {field}"
        super().__init__(message, field=field, **kwargs)


class InvalidFormatException(ValidationException):
    """Invalid data format."""

    def __init__(
        self,
        api_name: Any = None,
        expected_format: Any = None,
        field: Any = None,
        kwargs: Any = None,
        message: Any = None,
        retry_after: Any = None,
        status_code: Any = None,
        value: Any = None,
    ) -> None:
        message = f"Invalid format for {field}: {value} (expected {expected_format})"
        super().__init__(
            message,
            field=field,
            context={"value": value, "expected_format": expected_format},
            **kwargs,
        )


# Network & External API Exceptions
class NetworkException(PAKEException):
    """Network-related errors."""

    def __init__(
        self,
        api_name: Any = None,
        kwargs: Any = None,
        message: Any = None,
        retry_after: Any = None,
        status_code: Any = None,
        timeout: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class ExternalAPIException(PAKEException):
    """External API errors."""

    def __init__(
        self,
        api_name: Any = None,
        kwargs: Any = None,
        message: Any = None,
        retry_after: Any = None,
        status_code: Any = None,
        timeout: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.MEDIUM,
            context={"api_name": api_name, "status_code": status_code},
            **kwargs,
        )


class APIRateLimitException(ExternalAPIException):
    """API rate limit exceeded."""

    def __init__(
        self,
        api_name: Any = None,
        database: Any = None,
        error: Any = None,
        kwargs: Any = None,
        message: Any = None,
        retry_after: Any = None,
        timeout: Any = None,
    ) -> None:
        message = f"Rate limit exceeded for {api_name}"
        if retry_after:
            message += f" (retry after {retry_after} seconds)"
        super().__init__(
            message,
            api_name=api_name,
            context={"retry_after": retry_after},
            **kwargs,
        )


class APITimeoutException(ExternalAPIException):
    """API request timeout."""

    def __init__(
        self,
        api_name: Any = None,
        database: Any = None,
        error: Any = None,
        kwargs: Any = None,
        message: Any = None,
        query: Any = None,
        timeout: Any = None,
    ) -> None:
        message = f"Timeout after {timeout}s calling {api_name}"
        super().__init__(
            message,
            api_name=api_name,
            context={"timeout": timeout},
            **kwargs,
        )


# Database Exceptions
class DatabaseException(PAKEException):
    """Database-related errors."""

    def __init__(
        self,
        database: Any = None,
        error: Any = None,
        kwargs: Any = None,
        message: Any = None,
        query: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class DatabaseConnectionException(DatabaseException):
    """Database connection error."""

    def __init__(
        self,
        database: Any = None,
        error: Any = None,
        kwargs: Any = None,
        message: Any = None,
        query: Any = None,
        service_name: Any = None,
    ) -> None:
        message = f"Failed to connect to database: {database}"
        super().__init__(message, context={"database": database}, **kwargs)


class DatabaseQueryException(DatabaseException):
    """Database query error."""

    def __init__(
        self,
        error: Any = None,
        kwargs: Any = None,
        message: Any = None,
        query: Any = None,
        service_name: Any = None,
    ) -> None:
        message = f"Database query failed: {error}"
        super().__init__(message, context={"query": query, "error": error}, **kwargs)


# Cache Exceptions
class CacheException(PAKEException):
    """Cache-related errors."""

    def __init__(
        self,
        kwargs: Any = None,
        message: Any = None,
        reason: Any = None,
        service_name: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class CacheConnectionException(CacheException):
    """Cache connection error."""


class CacheKeyException(CacheException):
    """Invalid cache key."""


# Service Exceptions
class ServiceException(PAKEException):
    """Service-related errors."""

    def __init__(
        self,
        kwargs: Any = None,
        message: Any = None,
        reason: Any = None,
        service_name: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context={"service_name": service_name} if service_name else None,
            **kwargs,
        )


class ServiceUnavailableException(ServiceException):
    """Service is temporarily unavailable."""

    def __init__(
        self,
        file_path: Any = None,
        kwargs: Any = None,
        message: Any = None,
        reason: Any = None,
        service_name: Any = None,
    ) -> None:
        message = f"Service unavailable: {service_name}"
        super().__init__(message, service_name=service_name, **kwargs)


class ServiceInitializationException(ServiceException):
    """Service initialization failed."""

    def __init__(
        self,
        file_path: Any = None,
        kwargs: Any = None,
        message: Any = None,
        reason: Any = None,
        service_name: Any = None,
    ) -> None:
        message = f"Failed to initialize service {service_name}: {reason}"
        super().__init__(
            message,
            service_name=service_name,
            context={"reason": reason},
            **kwargs,
        )


# Processing Exceptions
class ProcessingException(PAKEException):
    """Data processing errors."""

    def __init__(
        self,
        file_path: Any = None,
        kwargs: Any = None,
        message: Any = None,
        operation: bool = False,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class DataProcessingException(ProcessingException):
    """Data processing failed."""


class ModelProcessingException(ProcessingException):
    """ML model processing failed."""


# Filesystem Exceptions
class FilesystemException(PAKEException):
    """Filesystem-related errors."""

    def __init__(
        self,
        file_path: Any = None,
        kwargs: Any = None,
        message: Any = None,
        module_name: Any = None,
        operation: bool = False,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.FILESYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context={"file_path": file_path} if file_path else None,
            **kwargs,
        )


class FileNotFoundException(FilesystemException):
    """File not found."""

    def __init__(
        self,
        dependency: Any = None,
        file_path: Any = None,
        install_command: Any = None,
        kwargs: Any = None,
        message: Any = None,
        module_name: Any = None,
        operation: bool = False,
    ) -> None:
        message = f"File not found: {file_path}"
        super().__init__(message, file_path=file_path, **kwargs)


class FilePermissionException(FilesystemException):
    """File permission denied."""

    def __init__(
        self,
        Dict: Any = None,
        dependency: Any = None,
        file_path: Any = None,
        install_command: Any = None,
        kwargs: Any = None,
        message: Any = None,
        module_name: Any = None,
        operation: bool = False,
    ) -> None:
        message = f"Permission denied for {operation} on {file_path}"
        super().__init__(
            message,
            file_path=file_path,
            context={"operation": operation},
            **kwargs,
        )


# Import Exceptions
class ImportException(PAKEException):
    """Import-related errors."""

    def __init__(
        self,
        Dict: Any = None,
        dependency: Any = None,
        install_command: Any = None,
        kwargs: Any = None,
        message: Any = None,
        module_name: Any = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.IMPORT,
            severity=ErrorSeverity.HIGH,
            context={"module_name": module_name} if module_name else None,
            **kwargs,
        )


class ModuleNotFoundError(ImportException):
    """Module could not be imported."""

    def __init__(
        self,
        Dict: Any = None,
        dependency: Any = None,
        install_command: Any = None,
        kwargs: Any = None,
        module_name: Any = None,
    ) -> None:
        message = f"Module not found: {module_name}"
        super().__init__(message, module_name=module_name, **kwargs)


class DependencyException(ImportException):
    """Missing dependency."""

    def __init__(
        self,
        Dict: Any = None,
        dependency: Any = None,
        install_command: Any = None,
        kwargs: Any = None,
    ) -> None:
        message = f"Missing dependency: {dependency}"
        if install_command:
            message += f" (install with: {install_command})"
        super().__init__(
            message,
            context={"dependency": dependency, "install_command": install_command},
            **kwargs,
        )


# Utility functions for error handling
def handle_exception(
    exception: Exception,
    logger: logging.Logger,
    context: dict[str, Any] | None = None,
    reraise: bool = True,
) -> PAKEException | None:
    """Handle any exception by converting it to a PAKEException if needed.

    This function provides centralized exception handling for the PAKE system. It
    converts standard Python exceptions to PAKEException subclasses, logs the error
    with appropriate context, and optionally re-raises the converted exception.

    Args:
        exception: The exception to handle. Can be any Python exception or
            already a PAKEException.
        logger: Logger instance for error logging and tracking.
        context: Optional additional context information for error tracking.
        reraise: Whether to re-raise the exception after handling. If False,
            returns the PAKEException instead of raising it.

    Returns:
        PAKEException | None: If reraise is False, returns the converted PAKEException.
            If reraise is True, returns None (exception is raised instead).

    Raises:
        PAKEException: If reraise is True, raises the converted PAKEException.

    Example:
        >>> try:
        ...     risky_operation()
        ... except (ValueError, RuntimeError) as e:
        ...     handle_exception(e, logger, context={"operation": "risky_operation"})
        ...     # Exception is logged and re-raised as PAKEException
    """
    if isinstance(exception, PAKEException):
        pake_exception = exception
    else:
        # Convert standard exceptions to PAKEException
        pake_exception = convert_standard_exception(exception, context)

    # Log the error
    pake_exception.log_error(logger)

    if reraise:
        raise pake_exception

    return pake_exception


def convert_standard_exception(
    exception: Exception,
    context: dict[str, Any] | None = None,
) -> PAKEException:
    """Convert standard Python exceptions to appropriate PAKEException subclasses.

    This function maps standard Python exceptions to their corresponding PAKEException
    subclasses, providing consistent error handling across the PAKE system. It preserves
    the original exception context while wrapping it in the PAKE exception hierarchy.

    Args:
        exception: The standard Python exception to convert.
        context: Optional additional context information for error tracking.

    Returns:
        PAKEException: The appropriate PAKEException subclass that corresponds to the
            input exception type. If no specific mapping exists, returns a generic
            PAKEException with UNKNOWN category and MEDIUM severity.

    Example:
        >>> try:
        ...     open("nonexistent.txt")
        ... except FileNotFoundError as e:
        ...     pake_error = convert_standard_exception(e)
        ...     # pake_error is now a FileNotFoundException
    """
    message = str(exception)

    if isinstance(exception, ImportError):
        return ImportException(message, original_exception=exception, context=context)
    if isinstance(exception, FileNotFoundError):
        return FileNotFoundException(
            exception.filename or "unknown",
            original_exception=exception,
            context=context,
        )
    if isinstance(exception, PermissionError):
        return FilePermissionException(
            exception.filename or "unknown",
            "access",
            original_exception=exception,
            context=context,
        )
    if isinstance(exception, ConnectionError):
        return NetworkException(message, original_exception=exception, context=context)
    if isinstance(exception, TimeoutError):
        return NetworkException(
            f"Timeout: {message}",
            original_exception=exception,
            context=context,
        )
    if isinstance(exception, ValueError):
        return ValidationException(
            message,
            original_exception=exception,
            context=context,
        )
    if isinstance(exception, KeyError):
        return ValidationException(
            f"Missing required key: {message}",
            original_exception=exception,
            context=context,
        )
    # Generic PAKE exception for unknown types
    return PAKEException(
        message,
        category=ErrorCategory.UNKNOWN,
        severity=ErrorSeverity.MEDIUM,
        original_exception=exception,
        context=context,
    )


def create_error_response(
    exception: PAKEException,
    include_details: bool = False,
) -> dict[str, Any]:
    """Create a standardized error response dictionary.

    Args:
        exception: PAKEException instance
        include_details: Whether to include detailed error information

    Returns:
        Error response dictionary
    """
    response = {
        "error": True,
        "error_code": exception.error_code,
        "message": exception.message,
        "category": exception.category.value,
        "severity": exception.severity.value,
        "timestamp": exception.timestamp.isoformat(),
    }

    if include_details:
        response.update(
            {"context": exception.context, "type": exception.__class__.__name__},
        )

    return response
