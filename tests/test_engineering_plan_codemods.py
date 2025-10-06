#!/usr/bin/env python3
"""Test Suite for Engineering Plan Codemods

This module provides comprehensive tests for the LibCST-based codemods
implemented according to the engineering plan. It validates that the
transformations work correctly and preserve code formatting.

Tests cover:
1. UTCNowTransformer - DTZ error remediation
2. ContextPassingTransformer - F821 error remediation
3. ComprehensiveDTZTransformer - Extended DTZ patterns
4. CodemodRunner - Execution framework
5. Integration tests with real code patterns

This ensures the engineering plan's principles are met:
- Automation First: Programmatic refactoring works correctly
- Preservation of Intent: Format and comments are preserved
- Prevention over Cure: Transformations prevent future bugs
"""

from pathlib import Path
import tempfile
from typing import List

import libcst as cst
from libcst.codemod import CodemodContext
import pytest

from .codemod_runner import (
    CodemodExecutionPlan,
    CodemodResult,
    CodemodRunner,
    create_comprehensive_remediation_plan,
    create_dtz_remediation_plan,
    create_f821_remediation_plan,
)
from .engineering_plan_codemods import (
    ComprehensiveDTZTransformer,
    ContextPassingTransformer,
    UTCNowTransformer,
)


class TestUTCNowTransformer:
    """Test cases for UTCNowTransformer."""

    def test_datetime_utcnow_replacement(self):
        """Test that datetime.utcnow() is replaced with datetime.now(timezone.utc)."""
        code = """
import datetime

def get_current_time():
    return datetime.utcnow()
"""

        transformer = UTCNowTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() == 1

        # Check that the import was added
        transformed_code = transformed_tree.code
        assert "from datetime import timezone" in transformed_code
        assert "datetime.now(timezone.utc)" in transformed_code
        assert "datetime.utcnow()" not in transformed_code

    def test_multiple_datetime_utcnow_calls(self):
        """Test transformation of multiple datetime.utcnow() calls."""
        code = """
import datetime

def get_timestamps():
    start_time = datetime.utcnow()
    end_time = datetime.utcnow()
    return start_time, end_time
"""

        transformer = UTCNowTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that both calls were transformed
        assert transformer.get_modifications_count() == 2

        transformed_code = transformed_tree.code
        assert transformed_code.count("datetime.now(timezone.utc)") == 2
        assert "datetime.utcnow()" not in transformed_code

    def test_format_preservation(self):
        """Test that code formatting and comments are preserved."""
        code = """
# This is a comment
import datetime

def get_time():
    # Another comment
    return datetime.utcnow()  # Inline comment
"""

        transformer = UTCNowTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        transformed_code = transformed_tree.code

        # Check that comments are preserved
        assert "# This is a comment" in transformed_code
        assert "# Another comment" in transformed_code
        assert "# Inline comment" in transformed_code

        # Check that formatting is preserved
        assert "def get_time():" in transformed_code
        assert "return datetime.now(timezone.utc)" in transformed_code

    def test_no_transformation_when_not_needed(self):
        """Test that no transformation occurs when datetime.utcnow() is not present."""
        code = """
import datetime

def get_time():
    return datetime.now()
"""

        transformer = UTCNowTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that no transformation occurred
        assert transformer.get_modifications_count() == 0

        # Check that code is unchanged
        assert transformed_tree.code == code


class TestContextPassingTransformer:
    """Test cases for ContextPassingTransformer."""

    def test_flask_request_context_fix(self):
        """Test fixing Flask request context F821 errors."""
        code = """
def process_user_data():
    user_id = request.json.get('user_id')
    return {"user_id": user_id}
"""

        transformer = ContextPassingTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() >= 1

        transformed_code = transformed_tree.code

        # Check that request parameter was added
        assert "def process_user_data(request: Request):" in transformed_code
        assert "from flask import Request" in transformed_code

    def test_flask_session_context_fix(self):
        """Test fixing Flask session context F821 errors."""
        code = """
def get_user_session():
    user_id = session.get('user_id')
    return user_id
"""

        transformer = ContextPassingTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() >= 1

        transformed_code = transformed_tree.code

        # Check that session parameter was added
        assert "def get_user_session(session: Session):" in transformed_code
        assert "from flask import Session" in transformed_code

    def test_multiple_context_variables(self):
        """Test fixing functions that use multiple context variables."""
        code = """
def process_request():
    user_id = request.json.get('user_id')
    session_id = session.get('session_id')
    return {"user_id": user_id, "session_id": session_id}
"""

        transformer = ContextPassingTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() >= 2

        transformed_code = transformed_tree.code

        # Check that both parameters were added
        assert (
            "def process_request(request: Request, session: Session):"
            in transformed_code
        )
        assert "from flask import Request, Session" in transformed_code

    def test_skip_methods_with_self(self):
        """Test that methods with 'self' parameter are skipped."""
        code = """
class UserService:
    def process_user_data(self):
        user_id = request.json.get('user_id')
        return {"user_id": user_id}
"""

        transformer = ContextPassingTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that no transformation occurred for methods
        assert transformer.get_modifications_count() == 0

        # Check that code is unchanged
        assert transformed_tree.code == code

    def test_kwargs_misuse_fix(self):
        """Test fixing **kwargs misuse patterns."""
        code = """
def configure_service(**kwargs):
    service_name = config  # Should be kwargs['config']
    return service_name
"""

        transformer = ContextPassingTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() >= 1

        transformed_code = transformed_tree.code

        # Check that config parameter was added
        assert "def configure_service(config: Any, **kwargs):" in transformed_code
        assert "from typing import Any" in transformed_code


class TestComprehensiveDTZTransformer:
    """Test cases for ComprehensiveDTZTransformer."""

    def test_datetime_now_without_timezone(self):
        """Test that datetime.now() without timezone gets timezone parameter."""
        code = """
import datetime

def get_time():
    return datetime.now()
"""

        transformer = ComprehensiveDTZTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() == 1

        transformed_code = transformed_tree.code
        assert "datetime.now(timezone.utc)" in transformed_code
        assert "from datetime import timezone" in transformed_code

    def test_datetime_fromtimestamp_without_timezone(self):
        """Test that datetime.fromtimestamp() gets timezone parameter."""
        code = """
import datetime

def get_time_from_timestamp(ts):
    return datetime.fromtimestamp(ts)
"""

        transformer = ComprehensiveDTZTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that transformation occurred
        assert transformer.get_modifications_count() == 1

        transformed_code = transformed_tree.code
        assert "datetime.fromtimestamp(ts, tz=timezone.utc)" in transformed_code
        assert "from datetime import timezone" in transformed_code

    def test_datetime_fromtimestamp_with_existing_tz(self):
        """Test that datetime.fromtimestamp() with existing tz parameter is not modified."""
        code = """
import datetime

def get_time_from_timestamp(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc)
"""

        transformer = ComprehensiveDTZTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        # Check that no transformation occurred
        assert transformer.get_modifications_count() == 0

        # Check that code is unchanged
        assert transformed_tree.code == code


class TestCodemodRunner:
    """Test cases for CodemodRunner."""

    def test_transform_file_success(self):
        """Test successful file transformation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
import datetime

def get_time():
    return datetime.utcnow()
"""
            )
            temp_file = Path(f.name)

        try:
            runner = CodemodRunner()
            result = runner.transform_file(temp_file, [UTCNowTransformer], dry_run=True)

            assert result.success
            assert result.modifications_made == 1
            assert result.error_message is None

        finally:
            temp_file.unlink()

    def test_transform_file_error(self):
        """Test file transformation with error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("invalid python syntax !!!")
            temp_file = Path(f.name)

        try:
            runner = CodemodRunner()
            result = runner.transform_file(temp_file, [UTCNowTransformer], dry_run=True)

            assert not result.success
            assert result.error_message is not None

        finally:
            temp_file.unlink()

    def test_execute_plan(self):
        """Test execution plan with multiple files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            file1 = temp_path / "test1.py"
            file1.write_text(
                """
import datetime

def get_time():
    return datetime.utcnow()
"""
            )

            file2 = temp_path / "test2.py"
            file2.write_text(
                """
def process_data():
    user_id = request.json.get('user_id')
    return user_id
"""
            )

            # Create execution plan
            plan = CodemodExecutionPlan(
                transformers=[UTCNowTransformer, ContextPassingTransformer],
                target_files=[file1, file2],
                dry_run=True,
            )

            # Execute plan
            runner = CodemodRunner()
            results = runner.execute_plan(plan)

            # Check results
            assert len(results) == 2
            assert all(result.success for result in results)
            assert sum(result.modifications_made for result in results) >= 2

    def test_generate_report(self):
        """Test report generation."""
        results = [
            CodemodResult(
                file_path=Path("test1.py"),
                success=True,
                modifications_made=2,
                original_size=100,
                transformed_size=110,
                execution_time=0.1,
            ),
            CodemodResult(
                file_path=Path("test2.py"),
                success=False,
                modifications_made=0,
                error_message="Syntax error",
                original_size=50,
                execution_time=0.05,
            ),
        ]

        runner = CodemodRunner()
        report = runner.generate_report(results)

        assert report["summary"]["total_files"] == 2
        assert report["summary"]["successful_files"] == 1
        assert report["summary"]["failed_files"] == 1
        assert report["summary"]["total_modifications"] == 2
        assert report["summary"]["success_rate"] == 50.0


class TestIntegration:
    """Integration tests with real code patterns."""

    def test_real_world_flask_pattern(self):
        """Test transformation of real-world Flask code patterns."""
        code = """
from flask import Flask, jsonify

app = Flask(__name__)

def process_user_request():
    user_id = request.json.get('user_id')
    session_data = session.get('user_data')

    # Process the data
    result = {
        'user_id': user_id,
        'session_data': session_data,
        'timestamp': datetime.utcnow()
    }

    return jsonify(result)
"""

        # Apply both transformers
        transformer1 = UTCNowTransformer(CodemodContext())
        transformer2 = ContextPassingTransformer(CodemodContext())

        tree = cst.parse_module(code)
        tree = transformer1.transform_module(tree)
        tree = transformer2.transform_module(tree)

        transformed_code = tree.code

        # Check that all issues were fixed
        assert (
            "def process_user_request(request: Request, session: Session):"
            in transformed_code
        )
        assert "datetime.now(timezone.utc)" in transformed_code
        assert "from flask import Request, Session" in transformed_code
        assert "from datetime import timezone" in transformed_code

    def test_real_world_django_pattern(self):
        """Test transformation of real-world Django code patterns."""
        code = """
from django.http import JsonResponse

def api_view(request):
    user_id = request.GET.get('user_id')

    # Process with timestamp
    timestamp = datetime.utcnow()

    return JsonResponse({
        'user_id': user_id,
        'timestamp': timestamp
    })
"""

        transformer = UTCNowTransformer(CodemodContext())
        tree = cst.parse_module(code)
        transformed_tree = transformer.transform_module(tree)

        transformed_code = transformed_tree.code

        # Check that datetime.utcnow() was replaced
        assert "datetime.now(timezone.utc)" in transformed_code
        assert "datetime.utcnow()" not in transformed_code
        assert "from datetime import timezone" in transformed_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
