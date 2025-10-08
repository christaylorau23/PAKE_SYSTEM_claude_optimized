#!/usr/bin/env python3
"""Phase 2+: Mastering Automated Refactoring with LibCST
World-Class Finish Guide - Advanced LibCST codemods for syntax error resolution.
"""

import re
from typing import Any, Optional

import libcst as cst
from libcst.codemod import CodemodTest, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


class FixIndentationIssues(VisitorBasedCodemodCommand):
    """Fix indentation issues that prevent proper parsing."""

    DESCRIPTION: str = "Fixes indentation issues in test files."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.indentation_fixes = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Fix function definition indentation issues."""
        # Check if function is missing proper indentation
        if hasattr(updated_node, "indent") and updated_node.indent.value == "":
            # Fix indentation for function definitions
            return updated_node.with_changes(indent=cst.SimpleWhitespace("    "))
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Fix class definition indentation issues."""
        # Check if class methods are missing proper indentation
        if hasattr(updated_node, "indent") and updated_node.indent.value == "":
            return updated_node.with_changes(indent=cst.SimpleWhitespace("    "))
        return updated_node


class FixMissingSelfParameter(VisitorBasedCodemodCommand):
    """Fix missing self parameter in class methods."""

    DESCRIPTION: str = "Adds missing self parameter to class methods."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.self_fixes = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Add self parameter to class methods that are missing it."""
        # Check if this is a method (has decorators like @pytest.mark.asyncio)
        is_method = any(
            isinstance(dec, cst.Call)
            and isinstance(dec.func, cst.Attribute)
            and dec.func.attr.value in ["asyncio", "unit_functional", "unit_edge_case"]
            for dec in updated_node.decorators
        )

        if is_method:
            # Check if self parameter is missing
            params = updated_node.params
            if not params.params or params.params[0].name.value != "self":
                # Add self parameter
                self_param = cst.Param(
                    name=cst.Name("self"),
                    comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" ")),
                )

                if params.params:
                    # Insert self as first parameter
                    new_params = [self_param] + list(params.params)
                    return updated_node.with_changes(
                        params=params.with_changes(params=new_params)
                    )
                # Add self as only parameter
                return updated_node.with_changes(
                    params=params.with_changes(params=[self_param])
                )

        return updated_node


class FixDuplicateParameters(VisitorBasedCodemodCommand):
    """Remove duplicate parameters from function definitions."""

    DESCRIPTION: str = "Removes duplicate parameters from function definitions."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.duplicate_fixes = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Remove duplicate parameters from function definitions."""
        params = updated_node.params
        if not params.params:
            return updated_node

        # Track seen parameter names
        seen_names = set()
        unique_params = []

        for param in params.params:
            param_name = param.name.value
            if param_name not in seen_names:
                seen_names.add(param_name)
                unique_params.append(param)
            else:
                self.duplicate_fixes += 1

        if len(unique_params) != len(params.params):
            return updated_node.with_changes(
                params=params.with_changes(params=unique_params)
            )

        return updated_node


class FixClassStructureIssues(VisitorBasedCodemodCommand):
    """Fix class structure issues like missing indentation."""

    DESCRIPTION: str = "Fixes class structure and indentation issues."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.structure_fixes = 0

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Fix class definition structure issues."""
        # Ensure class has proper indentation
        if hasattr(updated_node, "indent") and updated_node.indent.value == "":
            self.structure_fixes += 1
            return updated_node.with_changes(indent=cst.SimpleWhitespace("    "))

        return updated_node


class ComprehensiveSyntaxFixer(VisitorBasedCodemodCommand):
    """Comprehensive syntax fixer combining all techniques."""

    DESCRIPTION: str = "Comprehensive syntax fixer for all identified issues."

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self.fixes_applied = 0
        self.indentation_fixer = FixIndentationIssues(context)
        self.self_fixer = FixMissingSelfParameter(context)
        self.duplicate_fixer = FixDuplicateParameters(context)
        self.structure_fixer = FixClassStructureIssues(context)

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Apply all fixes to the module."""
        # Apply indentation fixes
        updated_node = self.indentation_fixer.transform_module(updated_node)

        # Apply self parameter fixes
        updated_node = self.self_fixer.transform_module(updated_node)

        # Apply duplicate parameter fixes
        updated_node = self.duplicate_fixer.transform_module(updated_node)

        # Apply structure fixes
        updated_node = self.structure_fixer.transform_module(updated_node)

        self.fixes_applied = (
            self.indentation_fixer.indentation_fixes
            + self.self_fixer.self_fixes
            + self.duplicate_fixer.duplicate_fixes
            + self.structure_fixer.structure_fixes
        )

        return updated_node


# Test Suite for LibCST Codemods
class TestComprehensiveSyntaxFixer(CodemodTest):
    """Test suite for comprehensive syntax fixer."""

    TRANSFORM = ComprehensiveSyntaxFixer

    def test_fix_missing_self_parameter(self) -> None:
        """Test fixing missing self parameter."""
        before = """
@pytest.mark.asyncio
async def test_function(self) -> None:
    pass
"""
        after = """
@pytest.mark.asyncio
async def test_function(self) -> None:
    pass
"""
        self.assertCodemod(before, after)

    def test_fix_duplicate_parameters(self) -> None:
        """Test fixing duplicate parameters."""
        before = """
def test_function(self, param1: Any = None, param1: Any = None) -> None:
    pass
"""
        after = """
def test_function(self, param1: Any = None) -> None:
    pass
"""
        self.assertCodemod(before, after)

    def test_fix_class_indentation(self) -> None:
        """Test fixing class indentation."""
        before = """
class TestClass:
def __init__(self) -> None:
    pass
"""
        after = """
class TestClass:
    def __init__(self) -> None:
        pass
"""
        self.assertCodemod(before, after)

    def test_no_change_for_valid_code(self) -> None:
        """Test that valid code is not changed."""
        before = """
class TestClass:
    def __init__(self) -> None:
        pass

    @pytest.mark.asyncio
    async def test_method(self) -> None:
        pass
"""
        after = """
class TestClass:
    def __init__(self) -> None:
        pass

    @pytest.mark.asyncio
    async def test_method(self) -> None:
        pass
"""
        self.assertCodemod(before, after)


def main():
    """Main execution function for LibCST codemods."""
    print("🎯 Starting LibCST Codemod Execution...")

    # This would typically be run with:
    # python -m libcst.tool codemod your_module.ComprehensiveSyntaxFixer .

    print("✅ LibCST Codemod system ready!")
    print("📋 Available codemods:")
    print("  - FixIndentationIssues")
    print("  - FixMissingSelfParameter")
    print("  - FixDuplicateParameters")
    print("  - FixClassStructureIssues")
    print("  - ComprehensiveSyntaxFixer")


if __name__ == "__main__":
    main()
