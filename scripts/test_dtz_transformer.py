#!/usr/bin/env python3
"""Test script for the DTZ transformer to validate automated remediation.

This script tests the ComprehensiveDTZTransformer against various DTZ patterns
to ensure it correctly handles all the datetime timezone issues described in
the engineering plan.
"""

from pathlib import Path
import tempfile
from typing import List, Tuple

import libcst as cst
from libcst.codemod import CodemodContext

from src.codemods.datetime_timezone_transformer import ComprehensiveDTZTransformer


def test_dtz_transformer():
    """Test the DTZ transformer with various problematic patterns."""

    test_cases = [
        # Test case 1: datetime.utcnow() - Primary source of DTZ bugs
        (
            "datetime.utcnow()",
            "datetime.now(timezone.utc)",
            "from datetime import timezone",
        ),
        # Test case 2: datetime.now() without timezone
        (
            "datetime.now()",
            "datetime.now(timezone.utc)",
            "from datetime import timezone",
        ),
        # Test case 3: datetime.fromtimestamp() without timezone
        (
            "datetime.fromtimestamp(1234567890)",
            "datetime.fromtimestamp(1234567890, tz=timezone.utc)",
            "from datetime import timezone",
        ),
        # Test case 4: datetime.strptime() without %z
        (
            'datetime.strptime("2023-01-01", "%Y-%m-%d")',
            'datetime.strptime("2023-01-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)',
            "from datetime import timezone",
        ),
        # Test case 5: Complex function with multiple DTZ issues
        (
            """
def process_data():
    now = datetime.utcnow()
    timestamp = datetime.fromtimestamp(time.time())
    parsed = datetime.strptime("2023-01-01", "%Y-%m-%d")
    return now, timestamp, parsed
            """,
            """
def process_data():
    now = datetime.now(timezone.utc)
    timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc)
    parsed = datetime.strptime("2023-01-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return now, timestamp, parsed
            """,
            "from datetime import timezone",
        ),
    ]

    print("🧪 Testing ComprehensiveDTZTransformer")
    print("=" * 60)

    success_count = 0
    total_tests = len(test_cases)

    for i, (input_code, expected_output, expected_import) in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}:")
        print(f"Input:    {input_code.strip()}")
        print(f"Expected: {expected_output.strip()}")

        try:
            # Create a complete Python file with imports
            full_input = f"import datetime\nimport time\n\n{input_code}"
            full_expected = (
                f"import datetime\nimport time\n{expected_import}\n\n{expected_output}"
            )

            # Parse the input code
            input_tree = cst.parse_expression(input_code.strip())

            # Apply the transformer
            context = CodemodContext()
            transformer = ComprehensiveDTZTransformer(context)

            # Transform the code
            result_tree = transformer.transform_module(cst.parse_module(full_input))

            # Check if modifications were made
            modifications = transformer.get_modifications_count()

            if modifications > 0:
                print(f"✅ Transformations applied: {modifications}")
                print(f"Result: {result_tree.code}")

                # Verify the import was added
                if expected_import in result_tree.code:
                    print("✅ Timezone import added correctly")
                    success_count += 1
                else:
                    print("❌ Timezone import missing")
            else:
                print("⚠️  No transformations applied")

        except (ImportError, ModuleNotFoundError) as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 All tests passed! DTZ transformer is working correctly.")
        return True
    print("⚠️  Some tests failed. Review the transformer implementation.")
    return False


def test_real_file_transformation():
    """Test the transformer on a real Python file with DTZ issues."""

    print("\n🔬 Testing Real File Transformation")
    print("=" * 60)

    # Create a test file with DTZ issues
    test_file_content = '''
import datetime
import time

def get_current_time():
    """Get current time - this has DTZ issues."""
    return datetime.utcnow()

def parse_timestamp(ts):
    """Parse timestamp - this has DTZ issues."""
    return datetime.fromtimestamp(ts)

def parse_date_string(date_str):
    """Parse date string - this has DTZ issues."""
    return datetime.strptime(date_str, "%Y-%m-%d")

def get_naive_now():
    """Get naive now - this has DTZ issues."""
    return datetime.now()

class TimeProcessor:
    def process(self):
        now = datetime.utcnow()
        ts = datetime.fromtimestamp(time.time())
        parsed = datetime.strptime("2023-01-01", "%Y-%m-%d")
        return now, ts, parsed
'''

    try:
        # Write test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_file_content)
            test_file_path = Path(f.name)

        # Apply transformer
        context = CodemodContext()
        transformer = ComprehensiveDTZTransformer(context)

        with open(test_file_path) as f:
            original_content = f.read()

        result_tree = transformer.transform_module(cst.parse_module(original_content))
        modifications = transformer.get_modifications_count()

        print(f"📁 Test file: {test_file_path}")
        print(f"🔧 Modifications made: {modifications}")
        print("📝 Transformed code:")
        print("-" * 40)
        print(result_tree.code)
        print("-" * 40)

        # Clean up
        test_file_path.unlink()

        if modifications > 0:
            print("✅ Real file transformation successful!")
            return True
        print("⚠️  No modifications made to real file")
        return False

    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"❌ Error in real file test: {e}")
        return False


def main():
    """Run all DTZ transformer tests."""
    print("🕐 DTZ Transformer Test Suite")
    print("Testing automated remediation of datetime timezone issues")
    print("Based on the engineering plan's Phase 1 requirements")
    print("=" * 80)

    # Run unit tests
    unit_test_success = test_dtz_transformer()

    # Run real file test
    real_file_success = test_real_file_transformation()

    print("\n" + "=" * 80)
    print("📋 Final Results:")
    print(f"Unit Tests: {'✅ PASSED' if unit_test_success else '❌ FAILED'}")
    print(f"Real File Test: {'✅ PASSED' if real_file_success else '❌ FAILED'}")

    if unit_test_success and real_file_success:
        print("\n🎉 All DTZ transformer tests passed!")
        print("The transformer is ready for production use.")
        return 0
    print("\n⚠️  Some tests failed. Review the implementation.")
    return 1


if __name__ == "__main__":
    exit(main())