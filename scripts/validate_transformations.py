#!/usr/bin/env python3
"""
Validation Script for LibCST Transformations

This script validates that the LibCST transformations preserve code intent
and formatting while correctly fixing F821 and DTZ errors. It implements
comprehensive testing as required by the engineering plan's "Preservation of Intent"
principle.
"""

import ast
import difflib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

import libcst as cst
from libcst.codemod import CodemodContext

# Add the codemods directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "codemods"))

from simple_transformers import (
    create_simple_context_transformer,
    create_simple_datetime_transformer,
)


class TransformationValidator:
    """Validates LibCST transformations for correctness and format preservation."""

    def __init__(self):
        self.test_cases = self._create_test_cases()

    def _create_test_cases(self) -> list[dict]:
        """Create comprehensive test cases for validation."""
        return [
            # F821 Context Passing Test Cases
            {
                "name": "Flask Request Context",
                "type": "F821",
                "input": """
def process_user_data():
    user_id = request.json.get('user_id')
    return {"user_id": user_id}
""",
                "expected_patterns": ["def process_user_data(request: Request):"],
                "should_fix": True,
            },
            {
                "name": "Flask Session Context",
                "type": "F821",
                "input": """
def get_user_preferences():
    theme = session.get('theme', 'default')
    return {"theme": theme}
""",
                "expected_patterns": ["def get_user_preferences(session: Session):"],
                "should_fix": True,
            },
            {
                "name": "Kwargs Misuse",
                "type": "F821",
                "input": """
def configure_service(**kwargs):
    self.config = config
    self.app = app
    return True
""",
                "expected_patterns": [
                    "def configure_service(config: Any, app: Any, **kwargs):"
                ],
                "should_fix": True,
            },
            # DTZ DateTime Test Cases
            {
                "name": "datetime.utcnow() Replacement",
                "type": "DTZ",
                "input": """
import datetime

def get_current_time():
    return datetime.utcnow()
""",
                "expected_patterns": [
                    "datetime.now(timezone.utc)",
                    "from datetime import timezone",
                ],
                "should_fix": True,
            },
            {
                "name": "datetime.now() without timezone",
                "type": "DTZ",
                "input": """
import datetime

def get_timestamp():
    return datetime.now()
""",
                "expected_patterns": ["datetime.now(timezone.utc)"],
                "should_fix": True,
            },
            {
                "name": "datetime.fromtimestamp() without timezone",
                "type": "DTZ",
                "input": """
import datetime

def from_timestamp(ts):
    return datetime.fromtimestamp(ts)
""",
                "expected_patterns": ["datetime.fromtimestamp(ts, tz=timezone.utc)"],
                "should_fix": True,
            },
            # Edge Cases
            {
                "name": "Already Fixed Code",
                "type": "F821",
                "input": """
def process_request(request: Request):
    user_id = request.json.get('user_id')
    return {"user_id": user_id}
""",
                "expected_patterns": [],
                "should_fix": False,
            },
            {
                "name": "Method with Self Parameter",
                "type": "F821",
                "input": """
class Service:
    def process_data(self):
        user_id = request.json.get('user_id')
        return {"user_id": user_id}
""",
                "expected_patterns": [],
                "should_fix": False,  # Methods shouldn't be modified
            },
        ]

    def validate_syntax(self, code: str) -> bool:
        """Validate that code has valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def validate_format_preservation(
        self, original: str, transformed: str
    ) -> dict[str, any]:
        """Validate that formatting is preserved."""
        original_lines = original.splitlines()
        transformed_lines = transformed.splitlines()

        # Check for significant formatting changes
        diff = list(
            difflib.unified_diff(
                original_lines,
                transformed_lines,
                fromfile="original",
                tofile="transformed",
                lineterm="",
            )
        )

        # Count non-whitespace changes
        significant_changes = 0
        for line in diff:
            if line.startswith(("+", "-")):
                if line.strip() and not line.strip().startswith("#"):
                    significant_changes += 1

        return {
            "valid": significant_changes
            < len(original_lines) * 0.1,  # Less than 10% change
            "changes_count": significant_changes,
            "preserves_formatting": significant_changes < 5,  # Arbitrary threshold
        }

    def validate_transformation(self, test_case: dict) -> dict[str, any]:
        """Validate a single transformation test case."""
        result = {
            "name": test_case["name"],
            "type": test_case["type"],
            "passed": False,
            "errors": [],
            "details": {},
        }

        try:
            # Parse the input code
            tree = cst.parse_module(test_case["input"])

            # Apply appropriate transformer
            if test_case["type"] == "F821":
                transformer = create_simple_context_transformer()
            elif test_case["type"] == "DTZ":
                transformer = create_simple_datetime_transformer()
            else:
                result["errors"].append(f"Unknown test type: {test_case['type']}")
                return result

            # Transform the code
            transformed_tree = transformer.transform_module(tree)
            transformed_code = transformed_tree.code

            # Validate syntax
            if not self.validate_syntax(transformed_code):
                result["errors"].append("Transformed code has invalid syntax")
                return result

            # Check if transformation was applied
            transformation_applied = transformed_code != test_case["input"]

            if test_case["should_fix"]:
                if not transformation_applied:
                    result["errors"].append("Expected transformation was not applied")
                    return result

                # Check for expected patterns
                for pattern in test_case["expected_patterns"]:
                    if pattern not in transformed_code:
                        result["errors"].append(
                            f"Expected pattern not found: {pattern}"
                        )
                        return result
            else:
                if transformation_applied:
                    result["errors"].append("Unexpected transformation was applied")
                    return result

            # Validate format preservation
            format_validation = self.validate_format_preservation(
                test_case["input"], transformed_code
            )

            if not format_validation["preserves_formatting"]:
                result["errors"].append("Formatting was not preserved")
                return result

            result["passed"] = True
            result["details"] = {
                "transformation_applied": transformation_applied,
                "format_preserved": format_validation["preserves_formatting"],
                "changes_count": format_validation["changes_count"],
            }

        except (ValueError, RuntimeError) as e:
            result["errors"].append(f"Transformation failed: {str(e)}")

        return result

    def run_ruff_validation(self, code: str) -> dict[str, list[str]]:
        """Run ruff check on code to validate fixes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["poetry", "run", "ruff", "check", "--select=F821,DTZ", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            errors = []
            for line in result.stdout.splitlines():
                if "F821" in line or "DTZ" in line:
                    errors.append(line.strip())

            return {"errors": errors, "error_count": len(errors)}

        except (ValueError, RuntimeError) as e:
            return {"errors": [f"Ruff validation failed: {str(e)}"], "error_count": 1}
        finally:
            temp_file.unlink()

    def run_comprehensive_validation(self) -> dict[str, any]:
        """Run comprehensive validation of all test cases."""
        print("🔍 Starting Comprehensive Transformation Validation")
        print("=" * 80)

        results = []
        passed_count = 0

        for test_case in self.test_cases:
            print(f"\n🧪 Testing: {test_case['name']} ({test_case['type']})")

            result = self.validate_transformation(test_case)
            results.append(result)

            if result["passed"]:
                passed_count += 1
                print("✅ PASSED")
                if result["details"]:
                    print(f"   Details: {result['details']}")
            else:
                print("❌ FAILED")
                for error in result["errors"]:
                    print(f"   Error: {error}")

        # Summary
        total_tests = len(self.test_cases)
        success_rate = (passed_count / total_tests) * 100

        print("\n" + "=" * 80)
        print("📊 VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_tests - passed_count}")
        print(f"Success rate: {success_rate:.1f}%")

        if success_rate >= 90:
            print("✅ Validation PASSED - Transformations are working correctly")
        else:
            print("❌ Validation FAILED - Transformations need fixes")

        return {
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": total_tests - passed_count,
            "success_rate": success_rate,
            "results": results,
        }


def main():
    """Main entry point for validation."""
    validator = TransformationValidator()
    summary = validator.run_comprehensive_validation()

    # Exit with appropriate code
    if summary["success_rate"] >= 90:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Validation failed


if __name__ == "__main__":
    main()
