#!/usr/bin/env python3
"""Engineering Plan Codemod Implementation.

This module implements the LibCST-based codemod strategy outlined in the
"Engineering Plan for the Remediation, Hardening, and Prophylactic Fortification
of the PAKE System". It provides the two primary transformers described in the plan:

1. UTCNowTransformer: Addresses DTZ errors by replacing datetime.utcnow() calls
2. ContextPassingTransformer: Addresses F821 errors by implementing proper context passing

The implementation follows the engineering plan's principles:
- Automation First: Programmatic refactoring for thousands of errors
- Preservation of Intent: Lossless transformations preserving formatting and comments
- Prevention over Cure: Building automated defenses against future bugs

Based on Phase 1 requirements for immediate stabilization through automated remediation.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

logger = logging.getLogger(__name__)


class UTCNowTransformer(VisitorBasedCodemodCommand):
    """Transformer that addresses DTZ errors by replacing datetime.utcnow() calls.

    This implements the engineering plan's UTCNowTransformer specification:
    - Traverses CST to identify Attribute nodes for datetime.utcnow calls
    - Replaces with Call nodes representing datetime.now(timezone.utc)
    - Uses AddImportsVisitor to ensure timezone import is present

    This addresses the systemic mishandling of time-aware datetimes that causes
    production failures when data crosses timezone boundaries.
    """

    DESCRIPTION = (
        "Replace datetime.utcnow() with datetime.now(timezone.utc) to fix DTZ errors"
    )

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.timezone_import_added = False
        self.modifications_made = 0

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Transform datetime.utcnow() calls to datetime.now(timezone.utc).

        This implements the engineering plan's specification for identifying
        attribute access nodes (Attribute) that correspond to datetime.utcnow
        calls and replacing them with new Call nodes.
        """
        # Match datetime.utcnow() pattern as specified in the engineering plan
        if m.matches(
            updated_node,
            m.Call(func=m.Attribute(value=m.Name("datetime"), attr=m.Name("utcnow"))),
        ):
            self.modifications_made += 1
            logger.debug("Transforming datetime.utcnow() call")

            # Create the replacement: datetime.now(timezone.utc)
            replacement = cst.Call(
                func=cst.Attribute(value=cst.Name("datetime"), attr=cst.Name("now")),
                args=[
                    cst.Arg(
                        value=cst.Attribute(
                            value=cst.Name("timezone"), attr=cst.Name("utc")
                        )
                    )
                ],
            )

            # Add timezone import if not already added
            if not self.timezone_import_added:
                AddImportsVisitor.add_needed_import(
                    self.context, "datetime", "timezone"
                )
                self.timezone_import_added = True
                logger.debug("Added timezone import to file")

            return replacement

        return updated_node

    def get_modifications_count(self) -> int:
        """Return the number of modifications made by this transformer."""
        return self.modifications_made


class ContextPassingTransformer(VisitorBasedCodemodCommand):
    """Transformer that addresses F821 errors by implementing proper context passing.

    This implements the engineering plan's ContextPassingTransformer specification:
    - Multi-pass tool for complex F821 error remediation
    - Identifies functions using context-local variables without proper parameters
    - Modifies FunctionDef nodes to add required parameters
    - Updates Call nodes to pass context variables down the call stack

    This addresses the three main F821 root causes:
    1. Flask context-local variables (request, session, g, current_app)
    2. Django HttpRequest objects accessed outside view context
    3. **kwargs misuse where keys are accessed as local variables
    """

    DESCRIPTION = "Fix F821 undefined name errors by implementing context passing"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        # Context-local variables as specified in the engineering plan
        self.context_vars: set[str] = {"request", "session", "g", "current_app"}
        self.django_request_vars: set[str] = {"request", "HttpRequest"}

        # Track modifications for multi-pass processing
        self.function_modifications: dict[str, dict[str, Any]] = {}
        self.call_sites: list[tuple[str, cst.Call]] = []
        self.modifications_made = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Analyze function definitions for context-local variable usage.

        This implements the first pass of the multi-pass tool described
        in the engineering plan.
        """
        # Skip methods (functions with 'self' parameter)
        has_self = any(param.name.value == "self" for param in node.params.params)

        if has_self:
            return False

        # Check for context-local variables in function body
        context_vars_used = self._find_context_vars_in_function(node)
        kwargs_vars_used = self._find_kwargs_misuse_in_function(node)

        if context_vars_used or kwargs_vars_used:
            # Store modification info for later processing
            self.function_modifications[node.name.value] = {
                "node": node,
                "context_vars": context_vars_used,
                "kwargs_vars": kwargs_vars_used,
                "current_params": [p.name.value for p in node.params.params],
            }
            logger.debug(
                f"Function {node.name.value} uses context vars: {context_vars_used}, kwargs vars: {kwargs_vars_used}"
            )

        return False

    def visit_Call(self, node: cst.Call) -> bool:
        """Track function calls to update them with context parameters.

        This implements the call site tracking for the multi-pass tool.
        """
        if isinstance(node.func, cst.Name):
            func_name = node.func.value
            if func_name in self.function_modifications:
                self.call_sites.append((func_name, node))
        return False

    def _find_context_vars_in_function(self, func_node: cst.FunctionDef) -> set[str]:
        """Find context-local variables used in function body.

        This implements the context variable detection logic specified
        in the engineering plan for Flask and Django frameworks.
        """
        context_vars_found = set()

        class ContextVarFinder(cst.CSTVisitor):
            def __init__(self, context_vars: set[str]):
                self.context_vars = context_vars
                self.found_vars = set()

            def visit_Name(self, node: cst.Name) -> bool:
                if node.value in self.context_vars:
                    self.found_vars.add(node.value)
                return False

        finder = ContextVarFinder(self.context_vars)
        func_node.visit(finder)
        return finder.found_vars

    def _find_kwargs_misuse_in_function(self, func_node: cst.FunctionDef) -> set[str]:
        """Find variables accessed directly that should be kwargs['var'].

        This addresses the **kwargs misuse pattern described in the
        engineering plan where developers assume keys are automatically
        unpacked as local variables.
        """
        kwargs_vars_found = set()

        # Look for **kwargs parameter
        has_kwargs = func_node.params.star_kwarg is not None

        if not has_kwargs:
            return kwargs_vars_found

        class KwargsMisuseFinder(cst.CSTVisitor):
            def __init__(self):
                self.found_vars = set()
                # Common kwargs keys that are often misused in the PAKE system
                self.kwargs_names = {
                    "config",
                    "app",
                    "user_id",
                    "tenant_id",
                    "service_name",
                    "agent_id",
                    "message_bus",
                    "cache_ttl",
                    "region",
                    "vault_url",
                    "vault_token",
                    "environment",
                    "config_file",
                    "config_data",
                    "environment_prefix",
                    "api_key",
                    "secret_key",
                    "database_url",
                    "redis_url",
                    "log_level",
                    "debug_mode",
                }

            def visit_Name(self, node: cst.Name) -> bool:
                if node.value in self.kwargs_names:
                    self.found_vars.add(node.value)
                return False

        finder = KwargsMisuseFinder()
        func_node.visit(finder)
        return finder.found_vars

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Modify function definitions to accept context parameters.

        This implements the FunctionDef node modification specified in
        the engineering plan's multi-pass tool.
        """
        if original_node.name.value not in self.function_modifications:
            return updated_node

        mod_info = self.function_modifications[original_node.name.value]
        current_params = mod_info["current_params"]
        new_params = []

        # Add context variables as parameters with proper type hints
        for var in sorted(mod_info["context_vars"]):
            if var not in current_params:
                self.modifications_made += 1

                # Add type hints for common context variables as specified in the plan
                if var == "request":
                    new_params.append(
                        cst.Param(
                            name=cst.Name(var),
                            annotation=cst.Annotation(cst.Name("Request")),
                        )
                    )
                elif var == "session":
                    new_params.append(
                        cst.Param(
                            name=cst.Name(var),
                            annotation=cst.Annotation(cst.Name("Session")),
                        )
                    )
                elif var == "g":
                    new_params.append(
                        cst.Param(
                            name=cst.Name(var),
                            annotation=cst.Annotation(cst.Name("_AppCtxGlobals")),
                        )
                    )
                elif var == "current_app":
                    new_params.append(
                        cst.Param(
                            name=cst.Name(var),
                            annotation=cst.Annotation(cst.Name("Flask")),
                        )
                    )
                else:
                    new_params.append(cst.Param(name=cst.Name(var)))

        # Add kwargs variables as parameters
        for var in sorted(mod_info["kwargs_vars"]):
            if var not in current_params:
                self.modifications_made += 1
                new_params.append(
                    cst.Param(
                        name=cst.Name(var), annotation=cst.Annotation(cst.Name("Any"))
                    )
                )

        if new_params:
            # Create new parameter list
            existing_params = list(updated_node.params.params)
            new_param_list = existing_params + new_params

            # Update the function definition
            updated_node = updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_param_list)
            )

            # Add necessary imports as specified in the engineering plan
            if any(
                var in mod_info["context_vars"]
                for var in ["request", "session", "g", "current_app"]
            ):
                AddImportsVisitor.add_needed_import(self.context, "flask", "Request")
                AddImportsVisitor.add_needed_import(self.context, "flask", "Session")
                AddImportsVisitor.add_needed_import(
                    self.context, "flask", "_AppCtxGlobals"
                )
                AddImportsVisitor.add_needed_import(self.context, "flask", "Flask")

            if mod_info["kwargs_vars"]:
                AddImportsVisitor.add_needed_import(self.context, "typing", "Any")

            logger.debug(
                f"Modified function {original_node.name.value} to accept context parameters: {[p.name.value for p in new_params]}"
            )

        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Update function calls to pass context parameters.

        This implements the Call node updating specified in the engineering
        plan's multi-pass tool for plumbing context dependencies.
        """
        if not isinstance(original_node.func, cst.Name):
            return updated_node

        func_name = original_node.func.value
        if func_name not in self.function_modifications:
            return updated_node

        mod_info = self.function_modifications[func_name]

        # Build new arguments list
        existing_args = list(updated_node.args)
        new_args = []

        # Add context variables as keyword arguments
        for var in sorted(mod_info["context_vars"]):
            if var == "request":
                new_args.append(
                    cst.Arg(keyword=cst.Name(var), value=cst.Name("request"))
                )
            elif var == "session":
                new_args.append(
                    cst.Arg(keyword=cst.Name(var), value=cst.Name("session"))
                )
            elif var == "g":
                new_args.append(cst.Arg(keyword=cst.Name(var), value=cst.Name("g")))
            elif var == "current_app":
                new_args.append(
                    cst.Arg(keyword=cst.Name(var), value=cst.Name("current_app"))
                )
            else:
                new_args.append(cst.Arg(keyword=cst.Name(var), value=cst.Name(var)))

        # Add kwargs variables as keyword arguments
        for var in sorted(mod_info["kwargs_vars"]):
            new_args.append(
                cst.Arg(
                    keyword=cst.Name(var),
                    value=cst.Subscript(
                        value=cst.Name("kwargs"),
                        slice=[cst.Index(cst.SimpleString(f'"{var}"'))],
                    ),
                )
            )

        if new_args:
            self.modifications_made += 1
            updated_node = updated_node.with_changes(args=existing_args + new_args)
            logger.debug(f"Updated call to {func_name} to pass context parameters")

        return updated_node

    def get_modifications_count(self) -> int:
        """Return the number of modifications made by this transformer."""
        return self.modifications_made


class ComprehensiveDTZTransformer(VisitorBasedCodemodCommand):
    """Comprehensive transformer for all DTZ-related issues.

    This extends the UTCNowTransformer to handle additional DTZ patterns
    beyond just datetime.utcnow(), implementing a more complete solution
    for timezone-aware datetime handling.
    """

    DESCRIPTION = "Fix all DTZ errors by ensuring timezone-aware datetime objects"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.timezone_import_added = False
        self.modifications_made = 0

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Transform various datetime calls to be timezone-aware."""
        # Pattern 1: datetime.utcnow() - Primary source of DTZ bugs
        if m.matches(
            updated_node,
            m.Call(func=m.Attribute(value=m.Name("datetime"), attr=m.Name("utcnow"))),
        ):
            self.modifications_made += 1
            return self._create_timezone_aware_now()

        # Pattern 2: datetime.now() without timezone
        if m.matches(
            updated_node,
            m.Call(
                func=m.Attribute(value=m.Name("datetime"), attr=m.Name("now")), args=[]
            ),
        ):
            self.modifications_made += 1
            return self._create_timezone_aware_now()

        # Pattern 3: datetime.fromtimestamp() without timezone
        if m.matches(
            updated_node,
            m.Call(
                func=m.Attribute(value=m.Name("datetime"), attr=m.Name("fromtimestamp"))
            ),
        ):
            # Check if tz parameter is already present
            has_tz_param = any(
                arg.keyword and arg.keyword.value == "tz" for arg in updated_node.args
            )

            if not has_tz_param:
                self.modifications_made += 1
                # Add tz=timezone.utc parameter
                new_args = list(updated_node.args) + [
                    cst.Arg(
                        keyword=cst.Name("tz"),
                        value=cst.Attribute(
                            value=cst.Name("timezone"), attr=cst.Name("utc")
                        ),
                    )
                ]

                self._ensure_timezone_import()
                return updated_node.with_changes(args=new_args)

        return updated_node

    def _create_timezone_aware_now(self) -> cst.Call:
        """Create datetime.now(timezone.utc) call."""
        self._ensure_timezone_import()
        return cst.Call(
            func=cst.Attribute(value=cst.Name("datetime"), attr=cst.Name("now")),
            args=[
                cst.Arg(
                    value=cst.Attribute(
                        value=cst.Name("timezone"), attr=cst.Name("utc")
                    )
                )
            ],
        )

    def _ensure_timezone_import(self) -> None:
        """Ensure timezone is imported from datetime."""
        if not self.timezone_import_added:
            AddImportsVisitor.add_needed_import(self.context, "datetime", "timezone")
            self.timezone_import_added = True

    def get_modifications_count(self) -> int:
        """Return the number of modifications made by this transformer."""
        return self.modifications_made


# Factory functions for creating transformers
def create_utcnow_transformer() -> UTCNowTransformer:
    """Factory function to create the UTCNow transformer."""
    return UTCNowTransformer(CodemodContext())


def create_context_passing_transformer() -> ContextPassingTransformer:
    """Factory function to create the context passing transformer."""
    return ContextPassingTransformer(CodemodContext())


def create_comprehensive_dtz_transformer() -> ComprehensiveDTZTransformer:
    """Factory function to create the comprehensive DTZ transformer."""
    return ComprehensiveDTZTransformer(CodemodContext())
