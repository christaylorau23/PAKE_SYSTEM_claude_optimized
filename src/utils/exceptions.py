#!/usr/bin/env python3
"""PAKE System - Centralized Exception Hierarchy
Provides consistent error handling patterns across the entire system
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels for classification"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization"""

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
    """Base exception class for all PAKE system errors

    Provides structured error information for consistent handling
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()

    def _generate_error_code(self) -> str:
        """Generate a unique error code based on class name"""
        class_name = self.__class__.__name__
        timestamp = self.timestamp.strftime("%Y%m%d%H%M%S")
        return f"{class_name}_{timestamp}"

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
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

    def log_error(self, logger: logging.Logger):
        """Log the error with appropriate level based on severity"""
        error_dict = self.to_dict()

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                f"Critical error [{self.error_code}]: {self.message}",
                extra=error_dict,
            )
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(
                f"High severity error [{self.error_code}]: {self.message}",
                extra=error_dict,
            )
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                f"Medium severity error [{self.error_code}]: {self.message}",
                extra=error_dict,
            )
        else:
            logger.info(
                f"Low severity error [{self.error_code}]: {self.message}",
                extra=error_dict,
            )


# Configuration Exceptions
class ConfigurationException(PAKEException):
    """Configuration-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class MissingConfigurationException(ConfigurationException):
    """Missing required configuration"""

    def __init__(self, config_key: str, **kwargs):
        message = f"Missing required configuration: {config_key}"
        super().__init__(message, context={"config_key": config_key}, **kwargs)


class InvalidConfigurationException(ConfigurationException):
    """Invalid configuration value"""

    def __init__(self, config_key: str, value: Any, expected: str, **kwargs):
        message = f"Invalid configuration value for {config_key}: {value} (expected {expected})"
        super().__init__(
            message,
            context={"config_key": config_key, "value": value, "expected": expected},
            **kwargs,
        )


# Authentication & Authorization Exceptions
class AuthenticationException(PAKEException):
    """Authentication-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class AuthorizationException(PAKEException):
    """Authorization-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class InvalidCredentialsException(AuthenticationException):
    """Invalid authentication credentials"""


class TokenExpiredException(AuthenticationException):
    """Authentication token has expired"""


class InsufficientPermissionsException(AuthorizationException):
    """User lacks required permissions"""


# Validation Exceptions
class ValidationException(PAKEException):
    """Data validation errors"""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context={"field": field} if field else None,
            **kwargs,
        )


class RequiredFieldException(ValidationException):
    """Required field is missing"""

    def __init__(self, field: str, **kwargs):
        message = f"Required field is missing: {field}"
        super().__init__(message, field=field, **kwargs)


class InvalidFormatException(ValidationException):
    """Invalid data format"""

    def __init__(self, field: str, value: Any, expected_format: str, **kwargs):
        message = f"Invalid format for {field}: {value} (expected {expected_format})"
        super().__init__(
            message,
            field=field,
            context={"value": value, "expected_format": expected_format},
            **kwargs,
        )


# Network & External API Exceptions
class NetworkException(PAKEException):
    """Network-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class ExternalAPIException(PAKEException):
    """External API errors"""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: int | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.MEDIUM,
            context={"api_name": api_name, "status_code": status_code},
            **kwargs,
        )


class APIRateLimitException(ExternalAPIException):
    """API rate limit exceeded"""

    def __init__(self, api_name: str, retry_after: int | None = None, **kwargs):
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
    """API request timeout"""

    def __init__(self, api_name: str, timeout: float, **kwargs):
        message = f"Timeout after {timeout}s calling {api_name}"
        super().__init__(
            message,
            api_name=api_name,
            context={"timeout": timeout},
            **kwargs,
        )


# Database Exceptions
class DatabaseException(PAKEException):
    """Database-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class DatabaseConnectionException(DatabaseException):
    """Database connection error"""

    def __init__(self, database: str, **kwargs):
        message = f"Failed to connect to database: {database}"
        super().__init__(message, context={"database": database}, **kwargs)


class DatabaseQueryException(DatabaseException):
    """Database query error"""

    def __init__(self, query: str, error: str, **kwargs):
        message = f"Database query failed: {error}"
        super().__init__(message, context={"query": query, "error": error}, **kwargs)


# Cache Exceptions
class CacheException(PAKEException):
    """Cache-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class CacheConnectionException(CacheException):
    """Cache connection error"""


class CacheKeyException(CacheException):
    """Invalid cache key"""


# Service Exceptions
class ServiceException(PAKEException):
    """Service-related errors"""

    def __init__(self, message: str, service_name: str | None = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context={"service_name": service_name} if service_name else None,
            **kwargs,
        )


class ServiceUnavailableException(ServiceException):
    """Service is temporarily unavailable"""

    def __init__(self, service_name: str, **kwargs):
        message = f"Service unavailable: {service_name}"
        super().__init__(message, service_name=service_name, **kwargs)


class ServiceInitializationException(ServiceException):
    """Service initialization failed"""

    def __init__(self, service_name: str, reason: str, **kwargs):
        message = f"Failed to initialize service {service_name}: {reason}"
        super().__init__(
            message,
            service_name=service_name,
            context={"reason": reason},
            **kwargs,
        )


# Processing Exceptions
class ProcessingException(PAKEException):
    """Data processing errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class DataProcessingException(ProcessingException):
    """Data processing failed"""


class ModelProcessingException(ProcessingException):
    """ML model processing failed"""


# Filesystem Exceptions
class FilesystemException(PAKEException):
    """Filesystem-related errors"""

    def __init__(self, message: str, file_path: str | None = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.FILESYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context={"file_path": file_path} if file_path else None,
            **kwargs,
        )


class FileNotFoundException(FilesystemException):
    """File not found"""

    def __init__(self, file_path: str, **kwargs):
        message = f"File not found: {file_path}"
        super().__init__(message, file_path=file_path, **kwargs)


class FilePermissionException(FilesystemException):
    """File permission denied"""

    def __init__(self, file_path: str, operation: str, **kwargs):
        message = f"Permission denied for {operation} on {file_path}"
        super().__init__(
            message,
            file_path=file_path,
            context={"operation": operation},
            **kwargs,
        )


# Import Exceptions
class ImportException(PAKEException):
    """Import-related errors"""

    def __init__(self, message: str, module_name: str | None = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.IMPORT,
            severity=ErrorSeverity.HIGH,
            context={"module_name": module_name} if module_name else None,
            **kwargs,
        )


class ModuleNotFoundError(ImportException):
    """Module could not be imported"""

    def __init__(self, module_name: str, **kwargs):
        message = f"Module not found: {module_name}"
        super().__init__(message, module_name=module_name, **kwargs)


class DependencyException(ImportException):
    """Missing dependency"""

    def __init__(
        self,
        dependency: str,
        install_command: str | None = None,
        **kwargs,
    ):
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
    """Handle any exception by converting it to a PAKEException if needed

    Args:
        exception: The exception to handle
        logger: Logger instance for logging
        context: Additional context information
        reraise: Whether to re-raise the exception

    Returns:
        PAKEException instance (if not reraising)
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
    """Convert standard Python exceptions to appropriate PAKEException subclasses

    Args:
        exception: Standard exception to convert
        context: Additional context information

    Returns:
        Appropriate PAKEException subclass
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
    """Create a standardized error response dictionary

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
