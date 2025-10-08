#!/usr/bin/env python3
"""Resilient GraphQL Error Handling Template
World-Class Finish Guide - "Errors as Data" pattern implementation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ErrorType(Enum):
    """Domain-specific error types."""

    VALIDATION_ERROR = "ValidationError"
    AUTHORIZATION_ERROR = "AuthorizationError"
    NOT_FOUND_ERROR = "NotFoundError"
    CONFLICT_ERROR = "ConflictError"
    INTERNAL_ERROR = "InternalError"


@dataclass
class GraphQLError:
    """Base GraphQL error structure."""

    message: str
    code: str
    field: Optional[str] = None
    extensions: Optional[dict[str, Any]] = None


@dataclass
class ValidationError(GraphQLError):
    """Validation error with specific field information."""

    field: str
    value: Any
    constraint: str


@dataclass
class AuthorizationError(GraphQLError):
    """Authorization error with permission details."""

    required_permission: str
    user_role: str


class ResilientGraphQLHandler:
    """Resilient GraphQL error handler implementing 'Errors as Data' pattern."""

    def __init__(self):
        self.error_handlers = {
            ValueError: self._handle_validation_error,
            PermissionError: self._handle_authorization_error,
            FileNotFoundError: self._handle_not_found_error,
            Exception: self._handle_generic_error,
        }

    def handle_resolver_error(
        self, error: Exception, context: dict[str, Any]
    ) -> GraphQLError:
        """Handle resolver errors with proper error types."""
        error_type = type(error)
        handler = self.error_handlers.get(error_type, self._handle_generic_error)
        return handler(error, context)

    def _handle_validation_error(
        self, error: ValueError, context: dict[str, Any]
    ) -> ValidationError:
        """Handle validation errors with specific field information."""
        return ValidationError(
            message=str(error),
            code="VALIDATION_ERROR",
            field=context.get("field", "unknown"),
            value=context.get("value"),
            constraint=context.get("constraint", "invalid"),
        )

    def _handle_authorization_error(
        self, error: PermissionError, context: dict[str, Any]
    ) -> AuthorizationError:
        """Handle authorization errors with permission details."""
        return AuthorizationError(
            message="Insufficient permissions",
            code="AUTHORIZATION_ERROR",
            required_permission=context.get("required_permission", "unknown"),
            user_role=context.get("user_role", "guest"),
        )

    def _handle_not_found_error(
        self, error: FileNotFoundError, context: dict[str, Any]
    ) -> GraphQLError:
        """Handle not found errors."""
        return GraphQLError(
            message=f"Resource not found: {context.get('resource', 'unknown')}",
            code="NOT_FOUND_ERROR",
            field=context.get("field"),
        )

    def _handle_generic_error(
        self, error: Exception, context: dict[str, Any]
    ) -> GraphQLError:
        """Handle generic errors with sanitized messages."""
        # Log the full error server-side
        print(f"Internal error: {error}")

        # Return sanitized message to client
        return GraphQLError(message="An internal error occurred", code="INTERNAL_ERROR")


# Example usage in GraphQL resolvers
async def create_user_resolver(
    parent: Any, info: Any, input_data: dict[str, Any]
) -> Union[dict[str, Any], GraphQLError]:
    """Example resolver with resilient error handling."""
    error_handler = ResilientGraphQLHandler()

    try:
        # Validate input
        if not input_data.get("email"):
            raise ValueError("Email is required")

        # Check permissions
        if not info.context.get("user"):
            raise PermissionError("Authentication required")

        # Business logic
        user = await create_user(input_data)
        return {"user": user, "success": True}

    except Exception as e:
        return error_handler.handle_resolver_error(
            e,
            {
                "field": "email",
                "value": input_data.get("email"),
                "required_permission": "user.create",
                "user_role": info.context.get("user", {}).get("role", "guest"),
            },
        )


async def create_user(data: dict[str, Any]) -> dict[str, Any]:
    """Mock user creation function."""
    return {"id": "123", "email": data["email"], "name": data.get("name")}
