#!/usr/bin/env python3
"""
Working Demonstration of LibCST Transformations

This script demonstrates the working LibCST transformers for F821 and DTZ
error remediation as described in the engineering plan. It shows the
transformations in action with real examples.
"""

from pathlib import Path
import sys

import libcst as cst
from libcst.codemod import CodemodContext

# Add the codemods directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "codemods"))

from simple_transformers import (
    create_simple_context_transformer,
    create_simple_datetime_transformer,
)


def demonstrate_context_transformer():
    """Demonstrate the context passing transformer."""
    print("🔧 Context Passing Transformer Demo")
    print("=" * 50)

    # Test case 1: Flask request context
    code1 = """
def process_user_data():
    user_id = request.json.get('user_id')
    return {"user_id": user_id}
"""

    print("Input:")
    print(code1)

    tree = cst.parse_module(code1)
    transformer = create_simple_context_transformer()
    transformed_tree = transformer.transform_module(tree)

    print("Output:")
    print(transformed_tree.code)
    print()

    # Test case 2: Flask session context
    code2 = """
def get_user_preferences():
    theme = session.get('theme', 'default')
    return {"theme": theme}
"""

    print("Input:")
    print(code2)

    tree = cst.parse_module(code2)
    transformer = create_simple_context_transformer()
    transformed_tree = transformer.transform_module(tree)

    print("Output:")
    print(transformed_tree.code)
    print()


def demonstrate_datetime_transformer():
    """Demonstrate the datetime transformer."""
    print("🕒 DateTime Transformer Demo")
    print("=" * 50)

    # Test case 1: datetime.utcnow()
    code1 = """
import datetime

def get_current_time():
    return datetime.utcnow()
"""

    print("Input:")
    print(code1)

    tree = cst.parse_module(code1)
    transformer = create_simple_datetime_transformer()
    transformed_tree = transformer.transform_module(tree)

    print("Output:")
    print(transformed_tree.code)
    print()

    # Test case 2: Multiple datetime.utcnow() calls
    code2 = """
import datetime

def create_timestamps():
    start_time = datetime.utcnow()
    end_time = datetime.utcnow()
    return start_time, end_time
"""

    print("Input:")
    print(code2)

    tree = cst.parse_module(code2)
    transformer = create_simple_datetime_transformer()
    transformed_tree = transformer.transform_module(tree)

    print("Output:")
    print(transformed_tree.code)
    print()


def demonstrate_real_world_example():
    """Demonstrate with a more realistic example."""
    print("🌍 Real-World Example Demo")
    print("=" * 50)

    code = """
from flask import Flask
import datetime

app = Flask(__name__)

def process_request():
    user_id = request.json.get('user_id')
    timestamp = datetime.utcnow()
    theme = session.get('theme', 'default')

    return {
        "user_id": user_id,
        "timestamp": timestamp,
        "theme": theme
    }

def get_user_data():
    data = request.json
    created_at = datetime.utcnow()
    return {"data": data, "created_at": created_at}
"""

    print("Input:")
    print(code)

    # Apply both transformers
    tree = cst.parse_module(code)

    # First apply context transformer
    context_transformer = create_simple_context_transformer()
    tree = context_transformer.transform_module(tree)

    # Then apply datetime transformer
    datetime_transformer = create_simple_datetime_transformer()
    tree = datetime_transformer.transform_module(tree)

    print("Output:")
    print(tree.code)
    print()


def main():
    """Run all demonstrations."""
    print("🚀 LibCST Transformation Demonstrations")
    print("Based on the Engineering Plan for PAKE System Remediation")
    print("=" * 80)
    print()

    demonstrate_context_transformer()
    demonstrate_datetime_transformer()
    demonstrate_real_world_example()

    print("✅ All transformations completed successfully!")
    print()
    print("Key Benefits:")
    print("- Format preservation: Comments, whitespace, and style maintained")
    print("- Automated fixes: No manual intervention required")
    print("- Scalable: Can process entire codebases")
    print("- Safe: Only modifies specific patterns")


if __name__ == "__main__":
    main()
