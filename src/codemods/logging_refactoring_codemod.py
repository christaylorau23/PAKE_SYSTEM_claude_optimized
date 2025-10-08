#!/usr/bin/env python3
"""PAKE System - Automated Log Call Refactoring Codemod
LibCST transformer to automatically convert existing log statements from f-string format
to structured format as specified in the engineering plan.

This codemod transforms calls like:
    logging.info(f"User {user_id} logged in")
into:
    logger.info("user_logged_in", user_id=user_id)

This change also resolves the G004 linting rule, which correctly identifies that using
f-strings for logging is inefficient because the string is formatted even if the log
level is disabled and the message is never emitted.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

import libcst as cst
from libcst import AddImportsVisitor, Call, Name, SimpleString
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


class LogCallRefactoringTransformer(VisitorBasedCodemodCommand):
    """Transform f-string log calls to structured log calls.

    This transformer implements the automated refactoring of log calls as specified
    in the engineering plan Phase 2. It converts f-string based logging to structured
    key-value logging using structlog.
    """

    DESCRIPTION = "Transform f-string log calls to structured log calls"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.logger_imports: set[str] = set()
        self.transformations: list[tuple[str, str]] = []

    def visit_Call(self, node: Call) -> bool:
        """Visit function calls to identify logging statements."""
        # Check if this is a logging call
        if self._is_logging_call(node):
            self._transform_logging_call(node)
        return False

    def _is_logging_call(self, node: Call) -> bool:
        """Check if a call node is a logging statement."""
        if not isinstance(node.func, cst.Attribute):
            return False

        # Check for logging.info, logging.debug, etc.
        if isinstance(node.func.value, cst.Name) and node.func.value.value == "logging":
            return True

        # Check for logger.info, logger.debug, etc.
        return bool(
            isinstance(node.func.value, cst.Name) and node.func.value.value == "logger"
        )

    def _transform_logging_call(self, node: Call) -> None:
        """Transform a logging call from f-string to structured format."""
        if not node.args:
            return

        # Get the first argument (the message)
        first_arg = node.args[0]

        # Check if it's an f-string
        if isinstance(first_arg.value, cst.FormattedString):
            self._transform_fstring_log_call(node, first_arg.value)
        elif isinstance(first_arg.value, cst.SimpleString):
            # Check if it's a regular string with placeholders
            self._transform_string_log_call(node, first_arg.value)

    def _transform_fstring_log_call(
        self, node: Call, fstring: cst.FormattedString
    ) -> None:
        """Transform an f-string log call to structured format."""
        # Extract the message and variables from the f-string
        message_parts = []
        variables = {}

        for part in fstring.parts:
            if isinstance(part, cst.FormattedStringText):
                message_parts.append(part.value)
            elif isinstance(part, cst.FormattedStringExpression):
                # Extract variable name and value
                var_name = self._extract_variable_name(part.expression)
                if var_name:
                    variables[var_name] = part.expression
                    message_parts.append(f"{{{var_name}}}")

        # Create the new message (replace variables with descriptive names)
        new_message = "".join(message_parts)
        new_message = self._create_structured_message(new_message, variables)

        # Create new arguments
        new_args = [cst.Arg(value=SimpleString(f'"{new_message}"'))]

        # Add variable arguments
        for var_name, var_expr in variables.items():
            new_args.append(
                cst.Arg(
                    keyword=cst.Name(var_name), value=var_expr, equal=cst.AssignEqual()
                )
            )

        # Add remaining arguments
        new_args.extend(node.args[1:])

        # Create new call node
        new_node = Call(func=node.func, args=new_args, lpar=node.lpar, rpar=node.rpar)

        # Replace the node
        self.context.replace(node, new_node)

        # Track transformation
        old_call = self._node_to_string(node)
        new_call = self._node_to_string(new_node)
        self.transformations.append((old_call, new_call))

    def _transform_string_log_call(self, node: Call, string: cst.SimpleString) -> None:
        """Transform a string log call with placeholders to structured format."""
        # Check if string contains % formatting or .format() calls
        string_value = string.value.strip("\"'")

        # Look for % formatting patterns
        if "%" in string_value and any(
            char in string_value for char in ["%s", "%d", "%f", "%r"]
        ):
            self._transform_percent_format_call(node, string_value)
        # Look for .format() patterns
        elif "{" in string_value and "}" in string_value:
            self._transform_format_call(node, string_value)

    def _transform_percent_format_call(self, node: Call, string_value: str) -> None:
        """Transform % formatting to structured format."""
        # Extract format specifiers
        format_specs = re.findall(r"%[sdfor]", string_value)

        if len(format_specs) != len(node.args) - 1:
            return  # Skip if argument count doesn't match

        # Create new message
        new_message = string_value
        variables = {}

        for i, spec in enumerate(format_specs):
            var_name = f"arg_{i}"
            variables[var_name] = node.args[i + 1].value
            new_message = new_message.replace(spec, f"{{{var_name}}}", 1)

        # Create structured message
        structured_message = self._create_structured_message(new_message, variables)

        # Create new arguments
        new_args = [cst.Arg(value=SimpleString(f'"{structured_message}"'))]

        for var_name, var_expr in variables.items():
            new_args.append(
                cst.Arg(
                    keyword=cst.Name(var_name), value=var_expr, equal=cst.AssignEqual()
                )
            )

        # Create new call node
        new_node = Call(func=node.func, args=new_args, lpar=node.lpar, rpar=node.rpar)

        self.context.replace(node, new_node)

    def _transform_format_call(self, node: Call, string_value: str) -> None:
        """Transform .format() calls to structured format."""
        # Extract format placeholders
        placeholders = re.findall(r"\{([^}]+)\}", string_value)

        if not placeholders:
            return

        # Create new message
        new_message = string_value
        variables = {}

        for i, placeholder in enumerate(placeholders):
            var_name = f"arg_{i}"
            variables[var_name] = node.args[i + 1].value
            new_message = new_message.replace(
                f"{{{placeholder}}}", f"{{{var_name}}}", 1
            )

        # Create structured message
        structured_message = self._create_structured_message(new_message, variables)

        # Create new arguments
        new_args = [cst.Arg(value=SimpleString(f'"{structured_message}"'))]

        for var_name, var_expr in variables.items():
            new_args.append(
                cst.Arg(
                    keyword=cst.Name(var_name), value=var_expr, equal=cst.AssignEqual()
                )
            )

        # Create new call node
        new_node = Call(func=node.func, args=new_args, lpar=node.lpar, rpar=node.rpar)

        self.context.replace(node, new_node)

    def _extract_variable_name(self, expr: cst.BaseExpression) -> str | None:
        """Extract variable name from expression."""
        if isinstance(expr, cst.Name):
            return expr.value
        if isinstance(expr, cst.Attribute):
            # For expressions like user.id, use the full path
            return self._attribute_to_string(expr)
        if isinstance(expr, cst.Call):
            # For function calls, use a descriptive name
            if isinstance(expr.func, cst.Name):
                return f"{expr.func.value}_result"
            if isinstance(expr.func, cst.Attribute):
                return f"{expr.func.attr.value}_result"
        return None

    def _attribute_to_string(self, attr: cst.Attribute) -> str:
        """Convert attribute expression to string."""
        if isinstance(attr.value, cst.Name):
            return f"{attr.value.value}_{attr.attr.value}"
        if isinstance(attr.value, cst.Attribute):
            return f"{self._attribute_to_string(attr.value)}_{attr.attr.value}"
        return attr.attr.value

    def _create_structured_message(
        self, message: str, variables: dict[str, Any]
    ) -> str:
        """Create a structured message from template and variables."""
        # Convert message to a more structured format
        # Replace common patterns with event names

        # Remove variable placeholders
        structured_message = message
        for var_name in variables:
            structured_message = structured_message.replace(f"{{{var_name}}}", "")

        # Clean up the message
        structured_message = structured_message.strip()

        # Convert to event-style naming
        structured_message = structured_message.lower()
        structured_message = re.sub(r"[^a-z0-9\s]", "", structured_message)
        structured_message = re.sub(r"\s+", "_", structured_message)

        # Ensure it's not empty
        if not structured_message:
            structured_message = "log_event"

        return structured_message

    def _node_to_string(self, node: cst.CSTNode) -> str:
        """Convert a CST node to string representation."""
        try:
            return cst.parse_expression(self.context.module.code_for_node(node))
        except Exception:
            return str(node)

    def transform_module_impl(self, tree: cst.Module) -> cst.Module:
        """Transform the module."""
        # First pass: transform logging calls
        tree = self.visit_and_update(tree)

        # Second pass: add structlog imports if needed
        if self.transformations:
            tree = self._add_structlog_imports(tree)

        return tree

    def _add_structlog_imports(self, tree: cst.Module) -> cst.Module:
        """Add structlog imports if transformations were made."""
        # Check if structlog is already imported
        has_structlog = False
        for stmt in tree.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for expr in stmt.body:
                    if isinstance(expr, cst.ImportFrom):
                        if expr.module and expr.module.value == "structlog":
                            has_structlog = True
                            break
                    elif isinstance(expr, cst.Import):
                        for name in expr.names:
                            if (
                                isinstance(name.name, cst.Name)
                                and name.name.value == "structlog"
                            ):
                                has_structlog = True
                                break

        if not has_structlog:
            # Add structlog import
            import_stmt = cst.SimpleStatementLine(
                body=[
                    cst.ImportFrom(
                        module=cst.Name("structlog"),
                        names=[cst.ImportAlias(name=cst.Name("get_logger"))],
                        lpar=cst.LeftParen(),
                        rpar=cst.RightParen(),
                    )
                ]
            )

            # Insert at the beginning
            new_body = [import_stmt] + list(tree.body)
            tree = tree.with_changes(body=new_body)

        return tree


class LoggingFStringTransformer(VisitorBasedCodemodCommand):
    """Specialized transformer for G004 logging f-string violations.

    This transformer specifically targets the G004 linting rule violations
    by converting f-string logging to structured logging.
    """

    DESCRIPTION = "Fix G004 logging f-string violations"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.fixes_applied = 0

    def visit_Call(self, node: Call) -> bool:
        """Visit function calls to identify f-string logging violations."""
        if self._is_fstring_logging_violation(node):
            self._fix_fstring_logging_violation(node)
        return False

    def _is_fstring_logging_violation(self, node: Call) -> bool:
        """Check if this is a G004 violation (f-string in logging)."""
        if not isinstance(node.func, cst.Attribute):
            return False

        # Check for logging methods
        if node.func.attr.value not in [
            "debug",
            "info",
            "warning",
            "error",
            "critical",
            "exception",
        ]:
            return False

        # Check if first argument is an f-string
        if not node.args:
            return False

        first_arg = node.args[0]
        return isinstance(first_arg.value, cst.FormattedString)

    def _fix_fstring_logging_violation(self, node: Call) -> None:
        """Fix f-string logging violation."""
        first_arg = node.args[0]
        fstring = first_arg.value

        # Extract message and variables
        message_parts = []
        variables = {}

        for part in fstring.parts:
            if isinstance(part, cst.FormattedStringText):
                message_parts.append(part.value)
            elif isinstance(part, cst.FormattedStringExpression):
                var_name = self._extract_simple_variable_name(part.expression)
                if var_name:
                    variables[var_name] = part.expression
                    message_parts.append(f"{{{var_name}}}")

        # Create structured message
        new_message = "".join(message_parts)
        new_message = self._create_event_message(new_message)

        # Create new arguments
        new_args = [cst.Arg(value=SimpleString(f'"{new_message}"'))]

        for var_name, var_expr in variables.items():
            new_args.append(
                cst.Arg(
                    keyword=cst.Name(var_name), value=var_expr, equal=cst.AssignEqual()
                )
            )

        # Add remaining arguments
        new_args.extend(node.args[1:])

        # Create new call node
        new_node = Call(func=node.func, args=new_args, lpar=node.lpar, rpar=node.rpar)

        # Replace the node
        self.context.replace(node, new_node)
        self.fixes_applied += 1

    def _extract_simple_variable_name(self, expr: cst.BaseExpression) -> str | None:
        """Extract simple variable name from expression."""
        if isinstance(expr, cst.Name):
            return expr.value
        if isinstance(expr, cst.Attribute) and isinstance(expr.value, cst.Name):
            return f"{expr.value.value}_{expr.attr.value}"
        return None

    def _create_event_message(self, message: str) -> str:
        """Create event-style message from template."""
        # Convert to event naming convention
        event_message = message.lower()
        event_message = re.sub(r"[^a-z0-9\s]", "", event_message)
        event_message = re.sub(r"\s+", "_", event_message)

        if not event_message:
            event_message = "log_event"

        return event_message


# Utility functions for running the codemods
def transform_logging_calls(source_code: str) -> tuple[str, list[tuple[str, str]]]:
    """Transform logging calls in source code.

    Args:
        source_code: Python source code as string

    Returns:
        Tuple of (transformed_code, list_of_transformations)
    """
    try:
        tree = cst.parse_module(source_code)
        context = CodemodContext()
        transformer = LogCallRefactoringTransformer(context)
        transformed_tree = transformer.transform_module(tree)

        return transformed_tree.code, transformer.transformations

    except (ValueError, RuntimeError) as e:
        print(f"Error transforming code: {e}")
        return source_code, []


def fix_g004_violations(source_code: str) -> tuple[str, int]:
    """Fix G004 logging f-string violations.

    Args:
        source_code: Python source code as string

    Returns:
        Tuple of (fixed_code, number_of_fixes_applied)
    """
    try:
        tree = cst.parse_module(source_code)
        context = CodemodContext()
        transformer = LoggingFStringTransformer(context)
        transformed_tree = transformer.transform_module(tree)

        return transformed_tree.code, transformer.fixes_applied

    except (ValueError, RuntimeError) as e:
        print(f"Error fixing G004 violations: {e}")
        return source_code, 0


# Example usage and testing
if __name__ == "__main__":
    # Test code with f-string logging
    test_code = """
import logging

logger = logging.getLogger(__name__)

def example_function(user_id: str, action: str):
    # This will be transformed
    logging.info(f"User {user_id} performed {action}")
    logger.debug(f"Processing user {user_id}")

    # This will also be transformed
    logging.error(f"Failed to process user {user_id}: {action}")

    # Regular string logging (no transformation)
    logging.info("Simple message")
"""

    print("Original code:")
    print(test_code)
    print("\n" + "=" * 50 + "\n")

    # Transform the code
    transformed_code, transformations = transform_logging_calls(test_code)

    print("Transformed code:")
    print(transformed_code)
    print("\n" + "=" * 50 + "\n")

    print("Transformations applied:")
    for old, new in transformations:
        print(f"OLD: {old}")
        print(f"NEW: {new}")
        print()

    # Test G004 specific fixes
    print("Testing G004 fixes:")
    fixed_code, fixes = fix_g004_violations(test_code)
    print(f"Applied {fixes} fixes")
    print("Fixed code:")
    print(fixed_code)
