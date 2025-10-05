#!/usr/bin/env python3
"""LibCST ContextPassingTransformer for F821 Error Remediation.

This transformer addresses the F821 "undefined name" errors by implementing
the context-passing pattern described in the engineering plan. It identifies
functions that use context-local variables (like Flask's request, session)
without receiving them as parameters and modifies them to accept these
variables explicitly.

Based on the engineering plan's Phase 1 requirements for automated remediation
of production incidents.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


class ContextPassingTransformer(VisitorBasedCodemodCommand):
    """Transformer that fixes F821 errors by implementing proper context passing.

    This addresses the three main F821 root causes:
    1. Flask context-local variables (request, session, g)
    2. Django HttpRequest objects accessed outside view context
    3. **kwargs misuse where keys are accessed as local variables
    """

    DESCRIPTION = "Fix F821 undefined name errors by implementing context passing"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.context_vars: set[str] = {"request", "session", "g", "current_app"}
        self.django_request_vars: set[str] = {"request", "HttpRequest"}
        self.kwargs_patterns: list[str] = []
        self.function_modifications: dict[str, dict] = {}
        self.call_sites: list[tuple[str, cst.Call]] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Analyze function definitions for context-local variable usage."""
        # Skip if this is a method (has self parameter)
        if any(param.name.value == "self" for param in node.params.params):
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

        return False

    def visit_Call(self, node: cst.Call) -> bool:
        """Track function calls to update them with context parameters."""
        if isinstance(node.func, cst.Name):
            func_name = node.func.value
            if func_name in self.function_modifications:
                self.call_sites.append((func_name, node))
        return False

    def _find_context_vars_in_function(self, func_node: cst.FunctionDef) -> set[str]:
        """Find context-local variables used in function body."""
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
        """Find variables accessed directly that should be kwargs['var']."""
        kwargs_vars_found = set()

        # Look for **kwargs parameter
        has_kwargs = func_node.params.star_kwarg is not None

        if not has_kwargs:
            return kwargs_vars_found

        class KwargsMisuseFinder(cst.CSTVisitor):
            def __init__(self):
                self.found_vars = set()
                self.kwargs_names = set()

            def visit_Name(self, node: cst.Name) -> bool:
                # Common kwargs keys that are often misused
                common_kwargs_keys = {
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
                }

                if node.value in common_kwargs_keys:
                    self.found_vars.add(node.value)
                return False

        finder = KwargsMisuseFinder()
        func_node.visit(finder)
        return finder.found_vars

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Modify function definitions to accept context parameters."""
        if original_node.name.value not in self.function_modifications:
            return updated_node

        mod_info = self.function_modifications[original_node.name.value]
        current_params = mod_info["current_params"]
        new_params = []

        # Add context variables as parameters
        for var in sorted(mod_info["context_vars"]):
            if var not in current_params:
                # Add type hints for common context variables
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
                else:
                    new_params.append(cst.Param(name=cst.Name(var)))

        # Add kwargs variables as parameters
        for var in sorted(mod_info["kwargs_vars"]):
            if var not in current_params:
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

            # Add necessary imports
            if any(var in mod_info["context_vars"] for var in ["request", "session"]):
                AddImportsVisitor.add_needed_import(
                    self.context, "flask", "Request", "Session"
                )

            if mod_info["kwargs_vars"]:
                AddImportsVisitor.add_needed_import(self.context, "typing", "Any")

        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Update function calls to pass context parameters."""
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
            updated_node = updated_node.with_changes(args=existing_args + new_args)

        return updated_node


class KwargsMisuseTransformer(VisitorBasedCodemodCommand):
    """Specialized transformer for fixing **kwargs misuse patterns.

    Converts direct variable access to proper kwargs['key'] access.
    """

    DESCRIPTION = "Fix **kwargs misuse by converting direct access to kwargs['key']"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.kwargs_vars = {
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
        }

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        """Convert direct variable access to kwargs access where appropriate."""
        if updated_node.value in self.kwargs_vars:
            # Check if we're in a function with **kwargs parameter
            # This is a simplified check - in practice, you'd want more sophisticated
            # scope analysis to determine if kwargs is available
            return cst.Subscript(
                value=cst.Name("kwargs"),
                slice=[cst.Index(cst.SimpleString(f'"{updated_node.value}"'))],
            )

        return updated_node


def create_context_passing_codemod() -> ContextPassingTransformer:
    """Factory function to create the context passing transformer."""
    return ContextPassingTransformer(CodemodContext())


def create_kwargs_misuse_codemod() -> KwargsMisuseTransformer:
    """Factory function to create the kwargs misuse transformer."""
    return KwargsMisuseTransformer(CodemodContext())
