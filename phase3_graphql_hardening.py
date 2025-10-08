#!/usr/bin/env python3
"""Phase 3: GraphQL API Hardening Implementation
World-Class Finish Guide - Resilient GraphQL API with "Errors as Data" pattern.
"""

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Union


class GraphQLSeverity(Enum):
    """GraphQL error severity levels."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class GraphQLErrorType(Enum):
    """GraphQL error types based on OWASP patterns."""

    INFORMATION_LEAKAGE = "Information Leakage"
    VALIDATION_ERROR = "Validation Error"
    AUTHORIZATION_ERROR = "Authorization Error"
    RESOLVER_ERROR = "Resolver Error"
    SCHEMA_ERROR = "Schema Error"
    NULLABILITY_ERROR = "Nullability Error"


@dataclass
class GraphQLIssue:
    """Represents a GraphQL API issue."""

    id: str
    error_type: GraphQLErrorType
    severity: GraphQLSeverity
    description: str
    file_path: str
    line_number: int
    remediation_pattern: str
    security_impact: int  # 1-5 scale
    remediation_effort: str  # S, M, L, XL
    priority_score: int


class GraphQLHardeningFramework:
    """Comprehensive GraphQL API hardening framework."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.graphql_issues: list[GraphQLIssue] = []
        self.remediation_patterns = self._load_remediation_patterns()
        self.error_type_mappings = self._load_error_type_mappings()

    def _load_remediation_patterns(self) -> dict[str, str]:
        """Load GraphQL-specific remediation patterns."""
        return {
            "information_leakage": "Implement global exception handler with sanitized error messages",
            "validation_error": "Add comprehensive input validation with detailed error types",
            "authorization_error": "Implement proper authentication and authorization checks",
            "resolver_error": "Add error handling in resolvers with proper error types",
            "schema_error": "Fix schema definition issues and add proper nullability",
            "nullability_error": "Use non-null modifiers (!) appropriately for reliable API contracts",
            "union_types": "Implement union types for error handling instead of nullable fields",
            "error_types": "Create specific error types for each domain error scenario",
        }

    def _load_error_type_mappings(
        self,
    ) -> dict[str, tuple[GraphQLErrorType, GraphQLSeverity, int]]:
        """Load error type mappings to severity and security impact."""
        return {
            "stack_trace_exposure": (
                GraphQLErrorType.INFORMATION_LEAKAGE,
                GraphQLSeverity.CRITICAL,
                5,
            ),
            "unhandled_exception": (
                GraphQLErrorType.INFORMATION_LEAKAGE,
                GraphQLSeverity.HIGH,
                4,
            ),
            "validation_failure": (
                GraphQLErrorType.VALIDATION_ERROR,
                GraphQLSeverity.MEDIUM,
                3,
            ),
            "auth_failure": (
                GraphQLErrorType.AUTHORIZATION_ERROR,
                GraphQLSeverity.HIGH,
                4,
            ),
            "resolver_error": (
                GraphQLErrorType.RESOLVER_ERROR,
                GraphQLSeverity.MEDIUM,
                3,
            ),
            "schema_issue": (GraphQLErrorType.SCHEMA_ERROR, GraphQLSeverity.MEDIUM, 3),
            "nullability_issue": (
                GraphQLErrorType.NULLABILITY_ERROR,
                GraphQLSeverity.LOW,
                2,
            ),
            "missing_error_handling": (
                GraphQLErrorType.RESOLVER_ERROR,
                GraphQLSeverity.HIGH,
                4,
            ),
        }

    def analyze_graphql_issues(self) -> list[GraphQLIssue]:
        """Analyze GraphQL-related issues in the codebase."""
        print("🔍 Analyzing GraphQL API issues...")

        issues = []

        # Analyze GraphQL schema files
        issues.extend(self._analyze_graphql_schemas())

        # Analyze GraphQL resolvers
        issues.extend(self._analyze_graphql_resolvers())

        # Analyze error handling patterns
        issues.extend(self._analyze_error_handling())

        # Analyze API security patterns
        issues.extend(self._analyze_api_security())

        self.graphql_issues = issues
        return issues

    def _analyze_graphql_schemas(self) -> list[GraphQLIssue]:
        """Analyze GraphQL schema files for issues."""
        issues = []

        try:
            # Find GraphQL schema files
            schema_files = list(self.project_root.rglob("*.graphql"))
            schema_files.extend(list(self.project_root.rglob("schema.py")))
            schema_files.extend(list(self.project_root.rglob("*schema*.py")))

            for schema_file in schema_files:
                try:
                    with open(schema_file, encoding="utf-8") as f:
                        content = f.read()

                    # Check for common GraphQL schema issues
                    issues.extend(
                        self._check_schema_patterns(content, str(schema_file))
                    )

                except Exception as e:
                    print(f"Error analyzing schema file {schema_file}: {e}")

        except Exception as e:
            print(f"Error finding GraphQL schema files: {e}")

        return issues

    def _check_schema_patterns(
        self, content: str, file_path: str
    ) -> list[GraphQLIssue]:
        """Check for problematic GraphQL schema patterns."""
        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for nullable fields that should be non-null
            if re.search(r"user:\s*User\s*$", line.strip()):
                issues.append(
                    GraphQLIssue(
                        id=f"nullable_user_field_{file_path}_{i}",
                        error_type=GraphQLErrorType.NULLABILITY_ERROR,
                        severity=GraphQLSeverity.MEDIUM,
                        description="User field should be non-null for reliable API contract",
                        file_path=file_path,
                        line_number=i,
                        remediation_pattern=self.remediation_patterns[
                            "nullability_error"
                        ],
                        security_impact=3,
                        remediation_effort="S",
                        priority_score=6,
                    )
                )

            # Check for error arrays instead of union types
            if re.search(r"errors:\s*\[.*Error.*\]", line.strip()):
                issues.append(
                    GraphQLIssue(
                        id=f"error_array_pattern_{file_path}_{i}",
                        error_type=GraphQLErrorType.SCHEMA_ERROR,
                        severity=GraphQLSeverity.MEDIUM,
                        description="Use union types instead of error arrays for better type safety",
                        file_path=file_path,
                        line_number=i,
                        remediation_pattern=self.remediation_patterns["union_types"],
                        security_impact=3,
                        remediation_effort="M",
                        priority_score=6,
                    )
                )

            # Check for missing non-null modifiers on critical fields
            if re.search(r"(id|email|username):\s*[A-Z]", line.strip()):
                if "!" not in line:
                    issues.append(
                        GraphQLIssue(
                            id=f"missing_non_null_{file_path}_{i}",
                            error_type=GraphQLErrorType.NULLABILITY_ERROR,
                            severity=GraphQLSeverity.MEDIUM,
                            description="Critical fields should be non-null",
                            file_path=file_path,
                            line_number=i,
                            remediation_pattern=self.remediation_patterns[
                                "nullability_error"
                            ],
                            security_impact=3,
                            remediation_effort="S",
                            priority_score=6,
                        )
                    )

        return issues

    def _analyze_graphql_resolvers(self) -> list[GraphQLIssue]:
        """Analyze GraphQL resolver files for issues."""
        issues = []

        try:
            # Find resolver files
            resolver_files = list(self.project_root.rglob("*resolver*.py"))
            resolver_files.extend(list(self.project_root.rglob("*query*.py")))
            resolver_files.extend(list(self.project_root.rglob("*mutation*.py")))

            for resolver_file in resolver_files:
                try:
                    with open(resolver_file, encoding="utf-8") as f:
                        content = f.read()

                    issues.extend(
                        self._check_resolver_patterns(content, str(resolver_file))
                    )

                except Exception as e:
                    print(f"Error analyzing resolver file {resolver_file}: {e}")

        except Exception as e:
            print(f"Error finding GraphQL resolver files: {e}")

        return issues

    def _check_resolver_patterns(
        self, content: str, file_path: str
    ) -> list[GraphQLIssue]:
        """Check for problematic GraphQL resolver patterns."""
        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for bare except clauses
            if re.search(r"except\s*:", line.strip()):
                issues.append(
                    GraphQLIssue(
                        id=f"bare_except_{file_path}_{i}",
                        error_type=GraphQLErrorType.INFORMATION_LEAKAGE,
                        severity=GraphQLSeverity.CRITICAL,
                        description="Bare except clauses can leak sensitive information",
                        file_path=file_path,
                        line_number=i,
                        remediation_pattern=self.remediation_patterns[
                            "information_leakage"
                        ],
                        security_impact=5,
                        remediation_effort="M",
                        priority_score=10,
                    )
                )

            # Check for print statements in resolvers
            if re.search(r"print\s*\(", line.strip()):
                issues.append(
                    GraphQLIssue(
                        id=f"print_statement_{file_path}_{i}",
                        error_type=GraphQLErrorType.INFORMATION_LEAKAGE,
                        severity=GraphQLSeverity.MEDIUM,
                        description="Print statements can leak sensitive information",
                        file_path=file_path,
                        line_number=i,
                        remediation_pattern=self.remediation_patterns[
                            "information_leakage"
                        ],
                        security_impact=3,
                        remediation_effort="S",
                        priority_score=6,
                    )
                )

            # Check for missing error handling in async resolvers
            if re.search(r"async def.*resolver", line.strip()):
                # Look for try/except in the next few lines
                has_error_handling = False
                for j in range(i, min(i + 10, len(lines))):
                    if "try:" in lines[j] or "except" in lines[j]:
                        has_error_handling = True
                        break

                if not has_error_handling:
                    issues.append(
                        GraphQLIssue(
                            id=f"missing_error_handling_{file_path}_{i}",
                            error_type=GraphQLErrorType.RESOLVER_ERROR,
                            severity=GraphQLSeverity.HIGH,
                            description="Async resolver missing error handling",
                            file_path=file_path,
                            line_number=i,
                            remediation_pattern=self.remediation_patterns[
                                "resolver_error"
                            ],
                            security_impact=4,
                            remediation_effort="M",
                            priority_score=8,
                        )
                    )

        return issues

    def _analyze_error_handling(self) -> list[GraphQLIssue]:
        """Analyze error handling patterns across the codebase."""
        issues = []

        try:
            # Find API-related files
            api_files = list(self.project_root.rglob("*api*.py"))
            api_files.extend(list(self.project_root.rglob("*endpoint*.py")))

            for api_file in api_files:
                try:
                    with open(api_file, encoding="utf-8") as f:
                        content = f.read()

                    issues.extend(
                        self._check_error_handling_patterns(content, str(api_file))
                    )

                except Exception as e:
                    print(f"Error analyzing API file {api_file}: {e}")

        except Exception as e:
            print(f"Error finding API files: {e}")

        return issues

    def _check_error_handling_patterns(
        self, content: str, file_path: str
    ) -> list[GraphQLIssue]:
        """Check for problematic error handling patterns."""
        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for stack trace exposure
            if re.search(r"traceback|stack.*trace", line.strip(), re.IGNORECASE):
                issues.append(
                    GraphQLIssue(
                        id=f"stack_trace_exposure_{file_path}_{i}",
                        error_type=GraphQLErrorType.INFORMATION_LEAKAGE,
                        severity=GraphQLSeverity.CRITICAL,
                        description="Stack trace exposure can leak sensitive system information",
                        file_path=file_path,
                        line_number=i,
                        remediation_pattern=self.remediation_patterns[
                            "information_leakage"
                        ],
                        security_impact=5,
                        remediation_effort="M",
                        priority_score=10,
                    )
                )

            # Check for generic error messages
            if re.search(r"raise.*Exception\(", line.strip()):
                issues.append(
                    GraphQLIssue(
                        id=f"generic_exception_{file_path}_{i}",
                        error_type=GraphQLErrorType.RESOLVER_ERROR,
                        severity=GraphQLSeverity.MEDIUM,
                        description="Generic exceptions provide poor error context",
                        file_path=file_path,
                        line_number=i,
                        remediation_pattern=self.remediation_patterns["error_types"],
                        security_impact=3,
                        remediation_effort="M",
                        priority_score=6,
                    )
                )

        return issues

    def _analyze_api_security(self) -> list[GraphQLIssue]:
        """Analyze API security patterns."""
        issues = []

        try:
            # Find authentication/authorization files
            auth_files = list(self.project_root.rglob("*auth*.py"))
            auth_files.extend(list(self.project_root.rglob("*permission*.py")))

            for auth_file in auth_files:
                try:
                    with open(auth_file, encoding="utf-8") as f:
                        content = f.read()

                    issues.extend(self._check_auth_patterns(content, str(auth_file)))

                except Exception as e:
                    print(f"Error analyzing auth file {auth_file}: {e}")

        except Exception as e:
            print(f"Error finding auth files: {e}")

        return issues

    def _check_auth_patterns(self, content: str, file_path: str) -> list[GraphQLIssue]:
        """Check for authentication/authorization issues."""
        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for missing authentication checks
            if re.search(r"def.*resolver", line.strip()) and "async def" not in line:
                # Look for auth checks in the function
                has_auth_check = False
                for j in range(i, min(i + 20, len(lines))):
                    if (
                        "authenticate" in lines[j]
                        or "authorize" in lines[j]
                        or "permission" in lines[j]
                    ):
                        has_auth_check = True
                        break

                if not has_auth_check:
                    issues.append(
                        GraphQLIssue(
                            id=f"missing_auth_check_{file_path}_{i}",
                            error_type=GraphQLErrorType.AUTHORIZATION_ERROR,
                            severity=GraphQLSeverity.HIGH,
                            description="Resolver missing authentication/authorization checks",
                            file_path=file_path,
                            line_number=i,
                            remediation_pattern=self.remediation_patterns[
                                "authorization_error"
                            ],
                            security_impact=4,
                            remediation_effort="M",
                            priority_score=8,
                        )
                    )

        return issues

    def prioritize_issues(self) -> list[GraphQLIssue]:
        """Prioritize GraphQL issues by priority score."""
        return sorted(self.graphql_issues, key=lambda x: x.priority_score, reverse=True)

    def generate_graphql_hardening_plan(self) -> str:
        """Generate comprehensive GraphQL hardening plan."""
        plan = []
        plan.append("# Phase 3: GraphQL API Hardening Plan")
        plan.append("")
        plan.append(f"**Analysis Date**: {Path().cwd()}")
        plan.append("")

        # Executive Summary
        plan.append("## 🎯 Executive Summary")
        plan.append("")
        plan.append(f"- **Total GraphQL Issues**: {len(self.graphql_issues)}")

        # Severity breakdown
        severity_counts = {}
        for issue in self.graphql_issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        plan.append("- **Severity Breakdown**:")
        for severity, count in severity_counts.items():
            plan.append(f"  - {severity.value}: {count}")
        plan.append("")

        # Error Type Analysis
        plan.append("## 🛡️ GraphQL Error Type Analysis")
        plan.append("")
        error_type_counts = {}
        for issue in self.graphql_issues:
            error_type_counts[issue.error_type] = (
                error_type_counts.get(issue.error_type, 0) + 1
            )

        for error_type, count in error_type_counts.items():
            plan.append(f"- **{error_type.value}**: {count} issues")
        plan.append("")

        # Critical Issues
        critical_issues = [
            i for i in self.graphql_issues if i.severity == GraphQLSeverity.CRITICAL
        ]
        if critical_issues:
            plan.append("## 🚨 CRITICAL ISSUES (Priority 1)")
            plan.append("")
            for i, issue in enumerate(critical_issues[:5], 1):
                plan.append(f"### {i}. {issue.id}")
                plan.append(f"- **Type**: {issue.error_type.value}")
                plan.append(f"- **File**: {issue.file_path}:{issue.line_number}")
                plan.append(f"- **Description**: {issue.description}")
                plan.append(f"- **Remediation**: {issue.remediation_pattern}")
                plan.append(f"- **Security Impact**: {issue.security_impact}/5")
                plan.append("")

        # High Priority Issues
        high_issues = [
            i for i in self.graphql_issues if i.severity == GraphQLSeverity.HIGH
        ]
        if high_issues:
            plan.append("## ⚠️ HIGH PRIORITY ISSUES (Priority 2)")
            plan.append("")
            for i, issue in enumerate(high_issues[:10], 1):
                plan.append(f"### {i}. {issue.id}")
                plan.append(f"- **Type**: {issue.error_type.value}")
                plan.append(f"- **File**: {issue.file_path}:{issue.line_number}")
                plan.append(f"- **Description**: {issue.description}")
                plan.append(f"- **Remediation**: {issue.remediation_pattern}")
                plan.append("")

        # GraphQL Hardening Strategy
        plan.append("## 🔧 GraphQL Hardening Strategy")
        plan.append("")
        plan.append("### Phase 3A: Error Handling Hardening (Week 1)")
        plan.append("1. **Implement Global Exception Handler**")
        plan.append("   - Catch all unhandled exceptions")
        plan.append("   - Return sanitized error messages")
        plan.append("   - Log full stack traces server-side only")
        plan.append("")
        plan.append("2. **Replace Generic Errors with Specific Types**")
        plan.append("   - Create domain-specific error types")
        plan.append("   - Implement union types for error handling")
        plan.append("   - Provide rich error context to clients")
        plan.append("")
        plan.append("### Phase 3B: Schema Hardening (Week 2)")
        plan.append("1. **Implement Union Types for Error Handling**")
        plan.append("   ```graphql")
        plan.append("   # Before (Fragile)")
        plan.append("   type CreateUserPayload {")
        plan.append("     user: User")
        plan.append("     errors: [Error!]")
        plan.append("   }")
        plan.append("")
        plan.append("   # After (Resilient)")
        plan.append(
            "   union CreateUserResult = UserCreated | UsernameTakenError | InvalidEmailError"
        )
        plan.append("   ```")
        plan.append("")
        plan.append("2. **Enforce Proper Nullability**")
        plan.append("   - Use non-null modifiers (!) for guaranteed fields")
        plan.append("   - Prevent cascading null failures")
        plan.append("   - Create predictable API contracts")
        plan.append("")
        plan.append("### Phase 3C: Security Hardening (Week 3)")
        plan.append("1. **Authentication and Authorization**")
        plan.append("   - Implement proper auth checks in all resolvers")
        plan.append("   - Add role-based access control")
        plan.append("   - Validate permissions for sensitive operations")
        plan.append("")
        plan.append("2. **Input Validation and Sanitization**")
        plan.append("   - Validate all input parameters")
        plan.append("   - Sanitize user-provided data")
        plan.append("   - Implement rate limiting")
        plan.append("")

        # Implementation Guidelines
        plan.append("## 📋 GraphQL Best Practices")
        plan.append("")
        plan.append("### Error Handling Patterns")
        plan.append("1. **Errors as Data** - Model errors as part of the schema")
        plan.append("2. **Union Types** - Use unions instead of nullable error arrays")
        plan.append("3. **Specific Error Types** - Create domain-specific error types")
        plan.append(
            "4. **Non-null Guarantees** - Use ! for fields that must be present"
        )
        plan.append("")
        plan.append("### Security Patterns")
        plan.append("1. **No Information Leakage** - Never expose stack traces")
        plan.append("2. **Proper Authentication** - Check auth in all resolvers")
        plan.append("3. **Input Validation** - Validate all user inputs")
        plan.append("4. **Error Sanitization** - Sanitize error messages")
        plan.append("")

        return "\n".join(plan)

    def create_graphql_hardening_templates(self) -> None:
        """Create GraphQL hardening templates and examples."""
        templates_dir = Path(self.project_root) / "graphql_hardening"
        templates_dir.mkdir(exist_ok=True)

        # Template 1: Resilient Error Handling
        error_template = templates_dir / "resilient_error_handling.py"
        with open(error_template, "w") as f:
            f.write(
                '''#!/usr/bin/env python3
"""Resilient GraphQL Error Handling Template
World-Class Finish Guide - "Errors as Data" pattern implementation.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


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
    extensions: Optional[Dict[str, Any]] = None


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

    def handle_resolver_error(self, error: Exception, context: Dict[str, Any]) -> GraphQLError:
        """Handle resolver errors with proper error types."""
        error_type = type(error)
        handler = self.error_handlers.get(error_type, self._handle_generic_error)
        return handler(error, context)

    def _handle_validation_error(self, error: ValueError, context: Dict[str, Any]) -> ValidationError:
        """Handle validation errors with specific field information."""
        return ValidationError(
            message=str(error),
            code="VALIDATION_ERROR",
            field=context.get("field", "unknown"),
            value=context.get("value"),
            constraint=context.get("constraint", "invalid")
        )

    def _handle_authorization_error(self, error: PermissionError, context: Dict[str, Any]) -> AuthorizationError:
        """Handle authorization errors with permission details."""
        return AuthorizationError(
            message="Insufficient permissions",
            code="AUTHORIZATION_ERROR",
            required_permission=context.get("required_permission", "unknown"),
            user_role=context.get("user_role", "guest")
        )

    def _handle_not_found_error(self, error: FileNotFoundError, context: Dict[str, Any]) -> GraphQLError:
        """Handle not found errors."""
        return GraphQLError(
            message=f"Resource not found: {context.get('resource', 'unknown')}",
            code="NOT_FOUND_ERROR",
            field=context.get("field")
        )

    def _handle_generic_error(self, error: Exception, context: Dict[str, Any]) -> GraphQLError:
        """Handle generic errors with sanitized messages."""
        # Log the full error server-side
        print(f"Internal error: {error}")

        # Return sanitized message to client
        return GraphQLError(
            message="An internal error occurred",
            code="INTERNAL_ERROR"
        )


# Example usage in GraphQL resolvers
async def create_user_resolver(parent: Any, info: Any, input_data: Dict[str, Any]) -> Union[Dict[str, Any], GraphQLError]:
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
        return error_handler.handle_resolver_error(e, {
            "field": "email",
            "value": input_data.get("email"),
            "required_permission": "user.create",
            "user_role": info.context.get("user", {}).get("role", "guest")
        })


async def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mock user creation function."""
    return {"id": "123", "email": data["email"], "name": data.get("name")}
'''
            )

        # Template 2: Union Type Schema
        schema_template = templates_dir / "resilient_schema.graphql"
        with open(schema_template, "w") as f:
            f.write(
                """# Resilient GraphQL Schema Template
# World-Class Finish Guide - "Errors as Data" pattern

type Query {
  user(id: ID!): UserResult!
  users(filter: UserFilter): UsersResult!
}

type Mutation {
  createUser(input: CreateUserInput!): CreateUserResult!
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserResult!
  deleteUser(id: ID!): DeleteUserResult!
}

# Input Types
input CreateUserInput {
  email: String!
  name: String!
  password: String!
}

input UpdateUserInput {
  email: String
  name: String
}

input UserFilter {
  email: String
  name: String
}

# Success Types
type User {
  id: ID!
  email: String!
  name: String!
  createdAt: String!
  updatedAt: String!
}

type UserCreated {
  user: User!
  message: String!
}

type UserUpdated {
  user: User!
  message: String!
}

type UserDeleted {
  id: ID!
  message: String!
}

type UsersFound {
  users: [User!]!
  totalCount: Int!
}

# Error Types
type ValidationError {
  message: String!
  field: String!
  code: String!
}

type AuthorizationError {
  message: String!
  requiredPermission: String!
  userRole: String!
}

type NotFoundError {
  message: String!
  resource: String!
}

type ConflictError {
  message: String!
  conflictingField: String!
  suggestedValue: String
}

type InternalError {
  message: String!
  code: String!
}

# Union Types for Resilient Error Handling
union UserResult = User | NotFoundError | AuthorizationError | InternalError
union UsersResult = UsersFound | AuthorizationError | InternalError
union CreateUserResult = UserCreated | ValidationError | ConflictError | AuthorizationError | InternalError
union UpdateUserResult = UserUpdated | ValidationError | NotFoundError | AuthorizationError | InternalError
union DeleteUserResult = UserDeleted | NotFoundError | AuthorizationError | InternalError
"""
            )

        # Template 3: Security Middleware
        security_template = templates_dir / "graphql_security_middleware.py"
        with open(security_template, "w") as f:
            f.write(
                '''#!/usr/bin/env python3
"""GraphQL Security Middleware Template
World-Class Finish Guide - Security hardening for GraphQL APIs.
"""

import time
from typing import Any, Dict, List, Optional
from functools import wraps
from dataclasses import dataclass


@dataclass
class SecurityContext:
    """Security context for GraphQL operations."""
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    permissions: List[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: float = 0.0


class GraphQLSecurityMiddleware:
    """Security middleware for GraphQL operations."""

    def __init__(self):
        self.rate_limits = {}  # In production, use Redis
        self.permission_map = {
            "user.create": ["admin", "user_manager"],
            "user.read": ["admin", "user_manager", "user"],
            "user.update": ["admin", "user_manager"],
            "user.delete": ["admin"],
        }

    def authenticate(self, token: Optional[str]) -> Optional[SecurityContext]:
        """Authenticate user and return security context."""
        if not token:
            return None

        # In production, validate JWT token
        # For now, mock authentication
        if token == "admin_token":
            return SecurityContext(
                user_id="admin_123",
                user_role="admin",
                permissions=["admin"],
                timestamp=time.time()
            )
        elif token == "user_token":
            return SecurityContext(
                user_id="user_123",
                user_role="user",
                permissions=["user"],
                timestamp=time.time()
            )

        return None

    def authorize(self, context: SecurityContext, required_permission: str) -> bool:
        """Check if user has required permission."""
        if not context:
            return False

        allowed_roles = self.permission_map.get(required_permission, [])
        return context.user_role in allowed_roles

    def check_rate_limit(self, ip_address: str, operation: str) -> bool:
        """Check rate limiting for operations."""
        key = f"{ip_address}:{operation}"
        now = time.time()

        if key not in self.rate_limits:
            self.rate_limits[key] = []

        # Clean old entries (older than 1 minute)
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if now - timestamp < 60
        ]

        # Check if under rate limit (10 requests per minute)
        if len(self.rate_limits[key]) >= 10:
            return False

        self.rate_limits[key].append(now)
        return True

    def sanitize_error(self, error: Exception) -> str:
        """Sanitize error messages to prevent information leakage."""
        # Log the full error server-side
        print(f"Internal error: {error}")

        # Return generic message to client
        return "An internal error occurred"

    def log_security_event(self, event_type: str, context: SecurityContext, details: Dict[str, Any]):
        """Log security events for monitoring."""
        print(f"Security Event: {event_type}")
        print(f"User: {context.user_id}")
        print(f"Role: {context.user_role}")
        print(f"Details: {details}")


def require_auth(required_permission: str):
    """Decorator to require authentication and authorization."""
    def decorator(func):
        @wraps(func)
        async def wrapper(parent: Any, info: Any, *args, **kwargs):
            security_middleware = GraphQLSecurityMiddleware()

            # Extract security context
            token = info.context.get("authorization")
            context = security_middleware.authenticate(token)

            if not context:
                raise PermissionError("Authentication required")

            # Check authorization
            if not security_middleware.authorize(context, required_permission):
                security_middleware.log_security_event(
                    "authorization_failed",
                    context,
                    {"required_permission": required_permission}
                )
                raise PermissionError("Insufficient permissions")

            # Check rate limiting
            ip_address = info.context.get("ip_address", "unknown")
            if not security_middleware.check_rate_limit(ip_address, func.__name__):
                raise PermissionError("Rate limit exceeded")

            # Add security context to info
            info.context["security"] = context

            return await func(parent, info, *args, **kwargs)

        return wrapper
    return decorator


# Example usage
@require_auth("user.create")
async def create_user_resolver(parent: Any, info: Any, input_data: Dict[str, Any]):
    """Example resolver with security middleware."""
    try:
        # Business logic here
        user = await create_user(input_data)
        return {"user": user, "success": True}
    except Exception as e:
        security_middleware = GraphQLSecurityMiddleware()
        error_message = security_middleware.sanitize_error(e)
        raise Exception(error_message)


async def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mock user creation function."""
    return {"id": "123", "email": data["email"], "name": data.get("name")}
'''
            )

        print(f"✅ GraphQL hardening templates created in {templates_dir}")


def main():
    """Main execution function for GraphQL hardening."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    print("🚀 Starting Phase 3: GraphQL API Hardening...")

    # Initialize GraphQL hardening framework
    graphql_framework = GraphQLHardeningFramework(project_root)

    # Analyze GraphQL issues
    issues = graphql_framework.analyze_graphql_issues()

    # Generate hardening plan
    hardening_plan = graphql_framework.generate_graphql_hardening_plan()
    with open("PHASE_3_GRAPHQL_HARDENING_PLAN.md", "w") as f:
        f.write(hardening_plan)

    # Create hardening templates
    graphql_framework.create_graphql_hardening_templates()

    print("✅ Phase 3 GraphQL Hardening Complete!")
    print("📄 Hardening plan written to: PHASE_3_GRAPHQL_HARDENING_PLAN.md")
    print(f"🎯 Total GraphQL Issues Found: {len(issues)}")

    # Show critical issues
    critical_issues = [i for i in issues if i.severity == GraphQLSeverity.CRITICAL]
    high_issues = [i for i in issues if i.severity == GraphQLSeverity.HIGH]

    print(f"🚨 Critical Issues: {len(critical_issues)}")
    print(f"⚠️  High Priority Issues: {len(high_issues)}")

    if critical_issues:
        print("\n🚨 Top Critical GraphQL Issues:")
        for i, issue in enumerate(critical_issues[:3], 1):
            print(
                f"{i}. {issue.error_type.value} - {issue.description} ({issue.file_path})"
            )


if __name__ == "__main__":
    main()
