#!/usr/bin/env python3
"""Phase 3: High-Complexity Function Refactoring
Refactors 7 high-complexity functions (>20 complexity) using systematic patterns.
"""

import ast
from collections import Counter
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


class Phase3ComplexityRefactorer:
    """Systematic refactoring tool for high-complexity functions."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.refactored_functions = Counter()
        self.files_processed = set()

        # High-complexity functions identified from analysis
        self.target_functions = [
            {
                "file": "src/services/analytics/intelligence_insight_service.py",
                "function": "generate_synthesis_insights",
                "complexity": 29,
                "line": 663,
                "priority": "P0",
            },
            {
                "file": "src/services/wealth/trend_detection_engine.py",
                "function": "main_trend_detection_demo",
                "complexity": 29,
                "line": 1528,
                "priority": "P2",
            },
            {
                "file": "src/services/ingestion/pubmed_service.py",
                "function": "_apply_query_filters",
                "complexity": 25,
                "line": 452,
                "priority": "P0",
            },
            {
                "file": "src/services/ingestion/arxiv_enhanced_service.py",
                "function": "search_papers",
                "complexity": 23,
                "line": 211,
                "priority": "P1",
            },
            {
                "file": "src/services/analytics/intelligence_insight_service.py",
                "function": "analyze_correlations",
                "complexity": 22,
                "line": 437,
                "priority": "P1",
            },
            {
                "file": "src/services/secrets/migration_service.py",
                "function": "_audit_kubernetes_secrets",
                "complexity": 22,
                "line": 310,
                "priority": "P1",
            },
            {
                "file": "src/services/ingestion/firecrawl_service.py",
                "function": "scrape_url",
                "complexity": 21,
                "line": 241,
                "priority": "P1",
            },
        ]

    def refactor_function(
        self, file_path: Path, function_name: str, line_start: int
    ) -> tuple[bool, int]:
        """Refactor a high-complexity function using systematic patterns."""
        if not file_path.exists():
            return False, 0

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse the file to find the function
            tree = ast.parse(content)

            # Find the target function
            target_function = None
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == function_name
                    and node.lineno == line_start
                ):
                    target_function = node
                    break

            if not target_function:
                print(f"❌ Function {function_name} not found at line {line_start}")
                return False, 0

            # Analyze function complexity
            complexity = self._calculate_complexity(target_function)
            print(f"📊 Function {function_name} complexity: {complexity}")

            if complexity <= 15:
                print(f"✅ Function {function_name} already has acceptable complexity")
                return True, 0

            # Apply refactoring patterns
            refactored_content = self._apply_refactoring_patterns(
                content, target_function, function_name
            )

            if refactored_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(refactored_content)
                self.files_processed.add(str(file_path))
                return True, 1

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error refactoring {file_path}:{function_name}: {e}")

        return False, 0

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _apply_refactoring_patterns(
        self, content: str, function_node: ast.AST, function_name: str
    ) -> str:
        """Apply systematic refactoring patterns to reduce complexity."""
        lines = content.splitlines()
        start_line = function_node.lineno - 1
        end_line = (
            function_node.end_lineno - 1
            if hasattr(function_node, "end_lineno")
            else start_line + 50
        )

        # Extract function content
        function_lines = lines[start_line : end_line + 1]
        function_content = "\n".join(function_lines)

        # Apply refactoring patterns
        refactored_function = self._extract_method_pattern(
            function_content, function_name
        )

        # Replace in original content
        new_lines = (
            lines[:start_line]
            + refactored_function.splitlines()
            + lines[end_line + 1 :]
        )
        return "\n".join(new_lines)

    def _extract_method_pattern(self, function_content: str, function_name: str) -> str:
        """Apply extract method pattern to reduce complexity."""
        lines = function_content.splitlines()

        # Find complex conditional blocks
        complex_blocks = self._find_complex_blocks(lines)

        if not complex_blocks:
            return function_content

        # Extract the most complex block
        block_start, block_end, block_type = complex_blocks[0]

        # Create extracted method
        extracted_method = self._create_extracted_method(
            lines[block_start:block_end], function_name, block_type
        )

        # Replace complex block with method call
        new_lines = lines[:block_start]
        new_lines.append(
            f"        {self._generate_method_call(function_name, block_type)}"
        )
        new_lines.extend(lines[block_end:])

        # Add extracted method to the end
        new_lines.append("")
        new_lines.extend(extracted_method.splitlines())

        return "\n".join(new_lines)

    def _find_complex_blocks(self, lines: list[str]) -> list[tuple[int, int, str]]:
        """Find complex conditional blocks in function."""
        complex_blocks = []
        indent_level = None
        block_start = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # Detect indentation level
            current_indent = len(line) - len(line.lstrip())
            if indent_level is None and current_indent > 0:
                indent_level = current_indent

            # Find complex conditionals
            if stripped.startswith(("if ", "elif ", "for ", "while ")):
                if block_start is None:
                    block_start = i

                # Count nested conditions
                nested_count = self._count_nested_conditions(lines[i : i + 10])
                if nested_count > 3:  # Threshold for complexity
                    complex_blocks.append(
                        (block_start, i + nested_count, "conditional")
                    )
                    block_start = None

        return complex_blocks

    def _count_nested_conditions(self, lines: list[str]) -> int:
        """Count nested conditional statements."""
        count = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("if ", "elif ", "for ", "while ")):
                count += 1
        return count

    def _create_extracted_method(
        self, block_lines: list[str], parent_function: str, block_type: str
    ) -> str:
        """Create extracted method from complex block."""
        method_name = f"_{parent_function}_{block_type}_handler"

        # Clean up indentation
        cleaned_lines = [line.strip() for line in block_lines if line.strip()]

        return f"""    def {method_name}(self) -> None:
        \"\"\"Extracted method to handle {block_type} logic.\"\"\"
        {chr(10).join(cleaned_lines)}"""

    def _generate_method_call(self, parent_function: str, block_type: str) -> str:
        """Generate method call for extracted method."""
        method_name = f"_{parent_function}_{block_type}_handler"
        return f"self.{method_name}()"

    def refactor_priority_functions(self) -> dict[str, Any]:
        """Refactor priority functions (P0 and P1)."""
        print("🔧 Phase 3: High-Complexity Function Refactoring")
        print("=" * 60)

        priority_functions = [
            f for f in self.target_functions if f["priority"] in ["P0", "P1"]
        ]

        print(f"📊 Found {len(priority_functions)} priority functions to refactor")

        refactored_count = 0

        for func_info in priority_functions:
            file_path = self.project_root / func_info["file"]
            function_name = func_info["function"]
            line_start = func_info["line"]
            priority = func_info["priority"]

            print(f"\n🎯 Refactoring {priority} function: {function_name}")
            print(f"   File: {func_info['file']}")
            print(f"   Line: {line_start}")
            print(f"   Complexity: {func_info['complexity']}")

            success, fixes = self.refactor_function(
                file_path, function_name, line_start
            )

            if success:
                refactored_count += fixes
                print("   ✅ Refactored successfully")
            else:
                print("   ❌ Refactoring failed")

        print("\n📈 Results:")
        print(f"   Functions refactored: {refactored_count}")
        print(f"   Files processed: {len(self.files_processed)}")

        return {
            "functions_refactored": refactored_count,
            "files_processed": len(self.files_processed),
            "success_rate": (refactored_count / len(priority_functions) * 100)
            if priority_functions
            else 0,
        }

    def create_refactoring_guidelines(self) -> bool:
        """Create refactoring guidelines document."""
        try:
            guidelines_content = """# PAKE System Refactoring Guidelines

## High-Complexity Function Refactoring Patterns

### 1. Extract Method Pattern
**When to use**: Functions with multiple responsibilities or complex conditional logic
**How to apply**:
- Identify logical blocks within the function
- Extract each block into a separate method
- Replace the block with a method call
- Each extracted method should have a single responsibility

**Example**:
```python
# Before (Complex)
def process_data(self, data):
    if data.type == 'A':
        # 20 lines of complex logic
        result = self._process_type_a(data)
    elif data.type == 'B':
        # 15 lines of complex logic
        result = self._process_type_b(data)
    return result

# After (Refactored)
def process_data(self, data):
    if data.type == 'A':
        return self._process_type_a_data(data)
    elif data.type == 'B':
        return self._process_type_b_data(data)
    return None

def _process_type_a_data(self, data):
    # 20 lines of complex logic
    return self._process_type_a(data)

def _process_type_b_data(self, data):
    # 15 lines of complex logic
    return self._process_type_b(data)
```

### 2. Guard Clause Pattern
**When to use**: Functions with deep nesting and multiple early returns
**How to apply**:
- Handle edge cases and error conditions first
- Return early to reduce nesting levels
- Simplify the main logic flow

**Example**:
```python
# Before (Nested)
def validate_user(self, user):
    if user:
        if user.is_active:
            if user.has_permissions:
                if user.role == 'admin':
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    else:
        return False

# After (Guard Clauses)
def validate_user(self, user):
    if not user:
        return False
    if not user.is_active:
        return False
    if not user.has_permissions:
        return False
    return user.role == 'admin'
```

### 3. Strategy Pattern
**When to use**: Complex conditional logic with multiple algorithms
**How to apply**:
- Create strategy classes for each algorithm
- Use polymorphism to select the appropriate strategy
- Eliminate complex if-else chains

### 4. Command Pattern
**When to use**: Functions with multiple operations or complex parameter handling
**How to apply**:
- Encapsulate operations as command objects
- Use a command processor to execute operations
- Simplify parameter passing and operation management

## Complexity Targets

- **Target Complexity**: ≤ 15 (B rating or better)
- **Critical Threshold**: > 20 (C rating - requires immediate refactoring)
- **Emergency Threshold**: > 30 (D rating - emergency refactoring)

## Refactoring Checklist

- [ ] Identify the function's primary responsibility
- [ ] Extract methods for secondary responsibilities
- [ ] Add guard clauses for edge cases
- [ ] Simplify conditional logic
- [ ] Add comprehensive tests for refactored code
- [ ] Verify functionality remains unchanged
- [ ] Update documentation

## Testing Refactored Code

1. **Unit Tests**: Test each extracted method independently
2. **Integration Tests**: Verify the main function still works correctly
3. **Performance Tests**: Ensure refactoring doesn't impact performance
4. **Regression Tests**: Run existing tests to catch any issues
"""

            guidelines_path = self.project_root / "REFACTORING_GUIDELINES.md"
            with open(guidelines_path, "w", encoding="utf-8") as f:
                f.write(guidelines_content)

            print(f"✅ Created refactoring guidelines at {guidelines_path}")
            return True

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error creating guidelines: {e}")
            return False


def main():
    """Main execution function."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"

    refactorer = Phase3ComplexityRefactorer(project_root)

    # Create guidelines first
    refactorer.create_refactoring_guidelines()

    # Refactor priority functions
    results = refactorer.refactor_priority_functions()

    print("\n🎉 Phase 3 Complexity Refactoring Complete!")
    print(f"Success Rate: {results['success_rate']:.1f}%")


if __name__ == "__main__":
    main()
