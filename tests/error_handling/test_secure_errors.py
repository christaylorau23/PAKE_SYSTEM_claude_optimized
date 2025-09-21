#!/usr/bin/env python3
"""
Secure Error Handling Tests for PAKE MCP Server
Tests specific exception handling and information disclosure prevention
"""

import json
import logging
import shutil
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Add the mcp-servers directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers"))

from pake_mcp_server import JsonFormatter, SecurityError, VaultManager


class TestSpecificExceptionHandling:
    """Test that specific exceptions are caught instead of generic Exception"""

    def setup_method(self):
        """Set up test environment for each test"""
        self.temp_vault = Path(tempfile.mkdtemp(prefix="test_error_vault_"))
        self.vault_manager = VaultManager(self.temp_vault)

        # Create expected folder structure
        (self.temp_vault / "00-Inbox").mkdir(exist_ok=True)
        (self.temp_vault / "01-Daily").mkdir(exist_ok=True)
        (self.temp_vault / "01-Projects").mkdir(exist_ok=True)
        (self.temp_vault / "02-Areas").mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up after each test"""
        if self.temp_vault.exists():
            shutil.rmtree(str(self.temp_vault))

    def test_file_not_found_specific_handling(self):
        """Test that FileNotFoundError is caught specifically"""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = self.vault_manager.parse_frontmatter(Path("/nonexistent/file.md"))

            # Should return empty metadata instead of crashing
            assert result == {"metadata": {}, "content": "", "has_frontmatter": False}

    def test_permission_error_specific_handling(self):
        """Test that PermissionError is caught specifically"""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = self.vault_manager.parse_frontmatter(Path("/restricted/file.md"))

            # Should return empty metadata instead of crashing
            assert result == {"metadata": {}, "content": "", "has_frontmatter": False}

    def test_unicode_decode_error_specific_handling(self):
        """Test that UnicodeDecodeError is caught specifically"""
        with patch(
            "builtins.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte"),
        ):
            result = self.vault_manager.parse_frontmatter(Path("/binary/file.md"))

            # Should return empty metadata instead of crashing
            assert result == {"metadata": {}, "content": "", "has_frontmatter": False}

    def test_create_note_file_access_errors(self):
        """Test create_note handles file access errors specifically"""
        # Test FileNotFoundError
        with patch(
            "pathlib.Path.mkdir",
            side_effect=FileNotFoundError("Directory not found"),
        ):
            with pytest.raises(OSError) as exc_info:
                self.vault_manager.create_note("Test Note", "Content", "SourceNote")
            assert "insufficient permissions or path not found" in str(exc_info.value)

        # Test PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(OSError) as exc_info:
                self.vault_manager.create_note("Test Note", "Content", "SourceNote")
            assert "insufficient permissions or path not found" in str(exc_info.value)

    def test_create_note_unicode_error_handling(self):
        """Test create_note handles Unicode encoding errors"""
        with patch("builtins.open", mock_open()) as mock_file:
            # Mock the write operation to raise UnicodeEncodeError
            mock_file.return_value.write.side_effect = UnicodeEncodeError(
                "utf-8",
                "\udcff",
                0,
                1,
                "surrogates not allowed",
            )

            with pytest.raises(ValueError) as exc_info:
                self.vault_manager.create_note(
                    "Test Note",
                    "Invalid content: \udcff",
                    "SourceNote",
                )
            assert "invalid characters in content" in str(exc_info.value)

    def test_create_note_invalid_parameters(self):
        """Test create_note handles invalid parameter types"""
        with pytest.raises(ValueError) as exc_info:
            self.vault_manager.create_note(
                123,
                "Content",
                "SourceNote",
            )  # Invalid title type
        assert "invalid parameters" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            self.vault_manager.create_note(
                "Title",
                None,
                "SourceNote",
            )  # Invalid content type
        assert "invalid parameters" in str(exc_info.value)

    def test_search_notes_error_handling(self):
        """Test search_notes handles various errors gracefully"""
        # Create a file that will cause issues during processing
        problem_file = self.temp_vault / "00-Inbox" / "problem.md"
        problem_file.write_text("---\ninvalid: yaml: content\n---\n")

        # Mock parse_frontmatter to raise specific errors
        with patch.object(self.vault_manager, "parse_frontmatter") as mock_parse:
            mock_parse.side_effect = [
                FileNotFoundError("File disappeared"),
                UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
                ValueError("Invalid YAML"),
            ]

            # Should not crash, should return empty results
            results = self.vault_manager.search_notes(
                {"pake_type": "SourceNote"},
                limit=5,
            )
            assert results == []

    def test_get_note_by_id_error_handling(self):
        """Test get_note_by_id handles errors without exposing details"""
        # Test with invalid pake_id parameter type
        with patch("pathlib.Path.rglob", side_effect=TypeError("Invalid argument")):
            result = self.vault_manager.get_note_by_id("test-id")
            assert result is None

        # Test with file system error
        with patch("pathlib.Path.rglob", side_effect=OSError("File system error")):
            result = self.vault_manager.get_note_by_id("test-id")
            assert result is None


class TestSecurityErrorHandling:
    """Test security-specific error scenarios"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_vault = Path(tempfile.mkdtemp(prefix="test_security_vault_"))
        self.vault_manager = VaultManager(self.temp_vault)

        # Create expected folder structure
        (self.temp_vault / "00-Inbox").mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up after tests"""
        if self.temp_vault.exists():
            shutil.rmtree(str(self.temp_vault))

    def test_security_error_not_wrapped(self):
        """Test that SecurityError is re-raised without wrapping"""
        with pytest.raises(SecurityError) as exc_info:
            self.vault_manager.create_note(
                "../../../etc/passwd",
                "malicious",
                "SourceNote",
            )

        # Should be original SecurityError, not wrapped in generic Exception
        assert isinstance(exc_info.value, SecurityError)
        assert "Path traversal attempt detected" in str(exc_info.value)

    def test_security_error_logged_appropriately(self):
        """Test that security errors are logged without exposing sensitive details"""
        with patch("pake_mcp_server.logger") as mock_logger:
            with pytest.raises(SecurityError):
                self.vault_manager.create_note(
                    "../../../etc/passwd",
                    "malicious",
                    "SourceNote",
                )

            # Logger should not be called for security errors (they're handled at
            # higher level)
            mock_logger.error.assert_not_called()


class TestMCPToolErrorHandling:
    """Test MCP tool error handling and client response sanitization"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_vault = Path(tempfile.mkdtemp(prefix="test_mcp_vault_"))
        # Import after setting up path
        global vault_manager
        from pake_mcp_server import vault_manager

        # Replace with test vault
        vault_manager.vault_path = self.temp_vault
        (self.temp_vault / "00-Inbox").mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up after tests"""
        if self.temp_vault.exists():
            shutil.rmtree(str(self.temp_vault))

    def test_tool_security_error_sanitized(self):
        """Test that tool execution sanitizes security errors for client"""
        import asyncio

        from pake_mcp_server import handle_call_tool

        # Mock arguments that would trigger SecurityError
        arguments = {
            "title": "../../../etc/passwd",
            "content": "malicious content",
            "type": "SourceNote",
        }

        async def test_security_error():
            result = await handle_call_tool("notes_from_schema", arguments)
            response_text = result[0].text
            response_data = json.loads(response_text)

            # Should return sanitized error message
            assert "error" in response_data
            assert response_data["error"] == "Security violation detected"
            assert response_data["tool"] == "notes_from_schema"

            # Should not expose path traversal details
            assert "etc/passwd" not in response_text
            assert "Path traversal" not in response_text

        asyncio.run(test_security_error())

    def test_tool_invalid_parameters_sanitized(self):
        """Test that tool execution sanitizes parameter validation errors"""
        import asyncio

        from pake_mcp_server import handle_call_tool

        # Missing required parameters
        arguments = {
            "title": "",  # Invalid empty title
            "content": "",  # Invalid empty content
        }

        async def test_validation_error():
            result = await handle_call_tool("notes_from_schema", arguments)
            response_text = result[0].text
            response_data = json.loads(response_text)

            # Should return sanitized error message
            assert "error" in response_data
            assert response_data["error"] == "Invalid parameters provided"
            assert response_data["tool"] == "notes_from_schema"

        asyncio.run(test_validation_error())

    def test_tool_file_system_error_sanitized(self):
        """Test that tool execution sanitizes file system errors"""
        import asyncio

        from pake_mcp_server import handle_call_tool

        # Mock file system error during note creation
        with patch.object(
            vault_manager,
            "create_note",
            side_effect=OSError("Permission denied"),
        ):
            arguments = {
                "title": "Test Note",
                "content": "Test content",
                "type": "SourceNote",
            }

            async def test_fs_error():
                result = await handle_call_tool("notes_from_schema", arguments)
                response_text = result[0].text
                response_data = json.loads(response_text)

                # Should return sanitized error message
                assert "error" in response_data
                assert response_data["error"] == "File system operation failed"
                assert response_data["tool"] == "notes_from_schema"

                # Should not expose file paths or system details
                assert "Permission denied" not in response_text

        asyncio.run(test_fs_error())


class TestStructuredJSONLogging:
    """Test JSON structured logging functionality"""

    def test_json_formatter_basic_structure(self):
        """Test that JSON formatter produces correct structure"""
        formatter = JsonFormatter()

        # Create a log record
        logger = logging.getLogger("test")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test_path",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify required fields
        assert "timestamp" in log_data
        assert log_data["level"] == "ERROR"
        assert log_data["logger"] == "test_path"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42

    def test_json_formatter_with_exception(self):
        """Test JSON formatter includes exception information"""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        logger = logging.getLogger("test")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test_path",
            lineno=42,
            msg="Error with exception",
            args=(),
            exc_info=exc_info,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should include exception info
        assert "exception" in log_data
        assert "ValueError: Test exception" in log_data["exception"]
        assert "Traceback" in log_data["exception"]

    def test_json_formatter_extra_fields(self):
        """Test JSON formatter includes extra fields from log record"""
        formatter = JsonFormatter()

        logger = logging.getLogger("test")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test_path",
            lineno=42,
            msg="Test with extra",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.user_id = "user123"
        record.request_id = "req456"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should include extra fields
        assert log_data["user_id"] == "user123"
        assert log_data["request_id"] == "req456"

    def test_logger_configuration(self):
        """Test that logger is properly configured with JSON formatter"""
        # Import to trigger logger configuration
        from pake_mcp_server import logger

        # Verify logger has JSON handler
        assert len(logger.handlers) > 0

        # Test that logging produces JSON output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("test_json")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        test_logger.info("Test JSON log message")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert log_data["message"] == "Test JSON log message"
        assert log_data["level"] == "INFO"


class TestErrorInformationDisclosurePrevention:
    """Test that sensitive information is not disclosed in error responses"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_vault = Path(tempfile.mkdtemp(prefix="test_disclosure_vault_"))
        self.vault_manager = VaultManager(self.temp_vault)

    def teardown_method(self):
        """Clean up after tests"""
        if self.temp_vault.exists():
            shutil.rmtree(str(self.temp_vault))

    def test_no_file_path_disclosure(self):
        """Test that file paths are not disclosed in error messages"""
        sensitive_path = "/sensitive/system/path/file.md"

        with patch(
            "builtins.open",
            side_effect=FileNotFoundError(f"No such file: {sensitive_path}"),
        ):
            result = self.vault_manager.parse_frontmatter(Path(sensitive_path))

            # Should not contain the sensitive path
            assert result == {"metadata": {}, "content": "", "has_frontmatter": False}

    def test_no_stack_trace_in_responses(self):
        """Test that stack traces are not included in client responses"""
        import asyncio

        from pake_mcp_server import handle_call_tool

        # Cause an error that would normally include stack trace
        with patch.object(
            self.vault_manager,
            "create_note",
            side_effect=Exception("Internal error with stack"),
        ):
            arguments = {"title": "Test Note", "content": "Test content"}

            async def test_no_stack():
                result = await handle_call_tool("notes_from_schema", arguments)
                response_text = result[0].text

                # Should not contain stack trace information
                assert "Traceback" not in response_text
                assert 'File "/' not in response_text
                assert "line " not in response_text

        asyncio.run(test_no_stack())

    def test_sanitized_error_messages(self):
        """Test that error messages are sanitized for client consumption"""
        import asyncio

        from pake_mcp_server import handle_call_tool

        # Test various error types produce sanitized messages
        test_cases = [
            (
                SecurityError("Path traversal: ../../../etc/passwd"),
                "Security violation detected",
            ),
            (
                FileNotFoundError("File not found: /secret/path"),
                "File system operation failed",
            ),
            (
                PermissionError("Permission denied: /etc/shadow"),
                "File system operation failed",
            ),
            (ValueError("Invalid value: secret_data"), "Invalid parameters provided"),
        ]

        for error, expected_message in test_cases:
            with patch.object(self.vault_manager, "create_note", side_effect=error):
                arguments = {"title": "Test Note", "content": "Test content"}

                async def test_sanitized():
                    result = await handle_call_tool("notes_from_schema", arguments)
                    response_text = result[0].text
                    response_data = json.loads(response_text)

                    assert response_data["error"] == expected_message
                    # Should not contain original error details
                    assert "etc/passwd" not in response_text
                    assert "/secret/path" not in response_text
                    assert "/etc/shadow" not in response_text
                    assert "secret_data" not in response_text

                asyncio.run(test_sanitized())


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
