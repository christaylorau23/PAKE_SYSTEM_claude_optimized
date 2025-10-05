#!/usr/bin/env python3
"""Simplified LibCST Transformers for F821 and DTZ Error Remediation.

This module provides simplified, working implementations of the transformers
described in the engineering plan. These transformers focus on the most
common patterns and ensure format preservation.
"""

from typing import Set

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


class SimpleContextPassingTransformer(VisitorBasedCodemodCommand):
    """Simplified transformer that fixes F821 errors by adding context parameters.

    This focuses on the most common patterns:
    1. Functions using 'request' without it as a parameter
    2. Functions using 'session' without it as a parameter
    """

    DESCRIPTION = "Fix F821 undefined name errors by adding context parameters"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.context_vars = {"request", "session"}
        self.functions_to_modify = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Analyze function definitions for context variable usage."""
        # Skip methods (functions with 'self' parameter)
        has_self = any(param.name.value == "self" for param in node.params.params)

        if has_self:
            return False

        # Check for context variables in function body
        context_vars_used = self._find_context_vars_in_function(node)

        if context_vars_used:
            self.functions_to_modify[node.name.value] = {
                "node": node,
                "context_vars": context_vars_used,
                "current_params": [p.name.value for p in node.params.params],
            }

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

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Modify function definitions to accept context parameters."""
        if original_node.name.value not in self.functions_to_modify:
            return updated_node

        mod_info = self.functions_to_modify[original_node.name.value]
        current_params = mod_info["current_params"]
        new_params = []

        # Add context variables as parameters
        for var in sorted(mod_info["context_vars"]):
            if var not in current_params:
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

        if new_params:
            # Create new parameter list
            existing_params = list(updated_node.params.params)
            new_param_list = existing_params + new_params

            # Update the function definition
            updated_node = updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_param_list)
            )

            # Add necessary imports
            if "request" in mod_info["context_vars"]:
                AddImportsVisitor.add_needed_import(self.context, "flask", "Request")
            if "session" in mod_info["context_vars"]:
                AddImportsVisitor.add_needed_import(self.context, "flask", "Session")

        return updated_node


class SimpleDateTimeTransformer(VisitorBasedCodemodCommand):
    """Simplified transformer that fixes DTZ errors by replacing datetime.utcnow().

    This focuses on the most common pattern: datetime.utcnow() -> datetime.now(timezone.utc)
    """

    DESCRIPTION = "Replace datetime.utcnow() with datetime.now(timezone.utc)"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.timezone_import_added = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Replace datetime.utcnow() calls with datetime.now(timezone.utc)."""
        # Match datetime.utcnow() pattern
        if m.matches(
            updated_node,
            m.Call(func=m.Attribute(value=m.Name("datetime"), attr=m.Name("utcnow"))),
        ):
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

            return replacement

        return updated_node


def create_simple_context_transformer() -> SimpleContextPassingTransformer:
    """Factory function to create the simplified context transformer."""
    return SimpleContextPassingTransformer(CodemodContext())


def create_simple_datetime_transformer() -> SimpleDateTimeTransformer:
    """Factory function to create the simplified datetime transformer."""
    return SimpleDateTimeTransformer(CodemodContext())
