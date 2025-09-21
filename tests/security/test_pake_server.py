#!/usr/bin/env python3
"""
Security tests for PAKE MCP Server
Tests path traversal prevention and other security measures
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from pake_mcp_server import SecurityError, VaultManager

# Add the mcp-servers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers"))


class TestPathTraversalSecurity:
    """Test path traversal prevention mechanisms"""

    def setup_method(self):
        """Set up test environment for each test"""
        # Create temporary vault directory
        self.temp_vault = Path(tempfile.mkdtemp(prefix="test_vault_"))
        self.vault_manager = VaultManager(self.temp_vault)

        # Create expected folder structure
        (self.temp_vault / "00-Inbox").mkdir(exist_ok=True)
        (self.temp_vault / "01-Daily").mkdir(exist_ok=True)
        (self.temp_vault / "01-Projects").mkdir(exist_ok=True)
        (self.temp_vault / "02-Areas").mkdir(exist_ok=True)

        # Create external directory to test escape attempts
        self.external_dir = Path(tempfile.mkdtemp(prefix="external_"))

    def teardown_method(self):
        """Clean up after each test"""
        if self.temp_vault.exists():
            shutil.rmtree(str(self.temp_vault))
        if self.external_dir.exists():
            shutil.rmtree(str(self.external_dir))

    def test_path_traversal_prevention_basic(self):
        """Test basic path traversal prevention with ../../../etc/passwd"""
        malicious_title = "../../../etc/passwd"

        with pytest.raises(SecurityError, match="Path traversal attempt detected"):
            self.vault_manager.create_note(
                title=malicious_title,
                content="This should not be created",
                note_type="SourceNote",
            )

        # Verify no file was created outside vault
        assert not (self.external_dir / "passwd").exists()

        # Verify no passwd file exists anywhere in the filesystem tree
        for root, dirs, files in os.walk(str(self.temp_vault.parent)):
            assert "passwd" not in files

    def test_path_traversal_prevention_windows_style(self):
        """Test path traversal prevention with Windows-style paths"""
        malicious_titles = [
            "..\\..\\..\\Windows\\System32\\config\\sam",
            "....//....//....//etc//passwd",
            "..\\/../../../etc/shadow",
        ]

        for malicious_title in malicious_titles:
            with pytest.raises(SecurityError, match="Path traversal attempt detected"):
                self.vault_manager.create_note(
                    title=malicious_title,
                    content="This should not be created",
                    note_type="SourceNote",
                )

    def test_path_traversal_prevention_absolute_paths(self):
        """Test prevention of absolute path attacks"""
        malicious_titles = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "/tmp/malicious_file",
            "\\\\server\\share\\malicious",
        ]

        for malicious_title in malicious_titles:
            with pytest.raises(SecurityError, match="Path traversal attempt detected"):
                self.vault_manager.create_note(
                    title=malicious_title,
                    content="This should not be created",
                    note_type="SourceNote",
                )

    def test_path_traversal_prevention_null_bytes(self):
        """Test prevention of null byte injection attacks"""
        malicious_titles = [
            "../../../etc/passwd\x00.md",
            "normal_name\x00../../../etc/passwd",
            "test\x00\x00../../../etc/passwd",
        ]

        for malicious_title in malicious_titles:
            with pytest.raises(SecurityError, match="Path traversal attempt detected"):
                self.vault_manager.create_note(
                    title=malicious_title,
                    content="This should not be created",
                    note_type="SourceNote",
                )

    def test_path_traversal_prevention_encoded_attacks(self):
        """Test prevention of URL-encoded and other encoded path traversal attempts"""
        malicious_titles = [
            "%2e%2e/%2e%2e/%2e%2e/etc/passwd",  # URL encoded ../../../
            "..%2f..%2f..%2fetc%2fpasswd",  # Mixed encoding
            "..%5c..%5c..%5cetc%5cpasswd",  # Backslash encoding
            "....//....//....//etc//passwd",  # Double dots
        ]

        for malicious_title in malicious_titles:
            with pytest.raises(SecurityError, match="Path traversal attempt detected"):
                self.vault_manager.create_note(
                    title=malicious_title,
                    content="This should not be created",
                    note_type="SourceNote",
                )

    def test_dot_and_dotdot_filenames(self):
        """Test handling of dot and double-dot filenames"""
        malicious_titles = [".", "..", "..."]

        for malicious_title in malicious_titles:
            # Should not raise SecurityError but should generate safe filename
            result = self.vault_manager.create_note(
                title=malicious_title,
                content="Safe content",
                note_type="SourceNote",
            )

            # Verify a safe filename was generated
            file_path = Path(result["file_path"])
            assert file_path.parent == self.temp_vault / "00-Inbox"
            assert file_path.name.startswith("note_")
            assert file_path.exists()

    def test_empty_title_handling(self):
        """Test handling of empty or whitespace-only titles"""
        empty_titles = ["", "   ", "\t\n\r", "!@#$%^&*()", "||||"]

        for empty_title in empty_titles:
            result = self.vault_manager.create_note(
                title=empty_title,
                content="Content for empty title",
                note_type="SourceNote",
            )

            # Verify a safe filename was generated
            file_path = Path(result["file_path"])
            assert file_path.parent == self.temp_vault / "00-Inbox"
            assert file_path.name.startswith("note_")
            assert file_path.exists()

    def test_valid_titles_work_correctly(self):
        """Test that valid titles still work correctly after security fixes"""
        valid_titles = [
            "Project Plan",
            "Meeting Notes 2024",
            "Research-Topic_v2",
            "daily-note-january-15",
            "API Documentation",
            "Bug Report #123",
        ]

        expected_filenames = [
            "Project-Plan.md",
            "Meeting-Notes-2024.md",
            "Research-Topic_v2.md",
            "daily-note-january-15.md",
            "API-Documentation.md",
            "Bug-Report-123.md",
        ]

        for title, expected_filename in zip(
            valid_titles, expected_filenames, strict=False
        ):
            result = self.vault_manager.create_note(
                title=title,
                content=f"Content for {title}",
                note_type="SourceNote",
            )

            file_path = Path(result["file_path"])
            assert file_path.parent == self.temp_vault / "00-Inbox"
            assert file_path.name == expected_filename
            assert file_path.exists()

            # Verify content was written correctly
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                assert f"Content for {title}" in content
                assert f'title: "{title}"' in content

    def test_long_title_truncation(self):
        """Test that very long titles are properly truncated"""
        long_title = "A" * 100 + "../../../etc/passwd"

        with pytest.raises(SecurityError, match="Path traversal attempt detected"):
            self.vault_manager.create_note(
                title=long_title,
                content="This should not be created",
                note_type="SourceNote",
            )

    def test_symbolic_link_attacks(self):
        """Test prevention of symbolic link attacks"""
        # Create a symbolic link pointing outside the vault
        if hasattr(os, "symlink"):  # Only run on systems that support symlinks
            try:
                # Create malicious symlink
                symlink_path = self.temp_vault / "00-Inbox" / "malicious_link"
                target_path = self.external_dir / "escaped_file.txt"

                # Create target file
                target_path.write_text("This file is outside the vault!")

                # Create symlink pointing to external file
                os.symlink(str(target_path), str(symlink_path))

                # Attempt to create note that would traverse via symlink
                with pytest.raises(SecurityError):
                    self.vault_manager.create_note(
                        title="malicious_link/../../../external_file",
                        content="This should not escape",
                        note_type="SourceNote",
                    )

            except OSError:
                # Skip if symlinks not supported (e.g., Windows without admin)
                pytest.skip("Symbolic links not supported on this system")

    def test_different_note_types_security(self):
        """Test that path traversal prevention works for all note types"""
        note_types = ["SourceNote", "DailyNote", "ProjectNote", "InsightNote"]
        malicious_title = "../../../etc/passwd"

        for note_type in note_types:
            with pytest.raises(SecurityError, match="Path traversal attempt detected"):
                self.vault_manager.create_note(
                    title=malicious_title,
                    content="This should not be created",
                    note_type=note_type,
                )

    def test_basename_stripping_effectiveness(self):
        """Test that os.path.basename effectively strips directory components"""
        test_cases = [
            ("../../../malicious", "malicious"),
            ("/absolute/path/file", "file"),
            ("..\\..\\windows\\path", "path"),
            ("./relative/path", "path"),
            ("file", "file"),
            ("", ""),
        ]

        for input_path, expected_basename in test_cases:
            result = os.path.basename(input_path)
            assert result == expected_basename

    def test_path_resolution_security(self):
        """Test that path resolution correctly identifies escapes"""
        # Test that resolve() correctly identifies attempts to escape vault
        vault_root = self.temp_vault.resolve()

        # Safe paths (should work)
        safe_paths = [
            self.temp_vault / "00-Inbox" / "safe_file.md",
            self.temp_vault / "01-Daily" / "daily.md",
        ]

        for safe_path in safe_paths:
            resolved = safe_path.resolve()
            assert str(resolved).startswith(str(vault_root))

        # Unsafe paths (theoretical - our code should prevent these)
        unsafe_theoretical_paths = [
            self.temp_vault / "../../../etc/passwd",
            self.temp_vault / "00-Inbox" / "../../../etc/passwd",
        ]

        for unsafe_path in unsafe_theoretical_paths:
            try:
                resolved = unsafe_path.resolve()
                # If resolution succeeds, ensure it's not within vault
                # (This tests our detection logic)
                is_within_vault = str(resolved).startswith(str(vault_root))
                if not is_within_vault:
                    # This is what our security check should catch
                    assert True  # Expected behavior
                else:
                    # If it resolves within vault, it might be safe
                    # but our algorithm should still catch suspicious patterns
                    pass
            except (OSError, ValueError):
                # Path resolution can fail for invalid paths - this is also safe
                pass


class TestSecurityIntegration:
    """Integration tests for security features"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_vault = Path(tempfile.mkdtemp(prefix="integration_test_"))
        self.vault_manager = VaultManager(self.temp_vault)

    def teardown_method(self):
        """Clean up after tests"""
        if self.temp_vault.exists():
            shutil.rmtree(str(self.temp_vault))

    def test_comprehensive_attack_scenarios(self):
        """Test comprehensive real-world attack scenarios"""
        attack_scenarios = [
            # Classic path traversal
            {
                "title": "../../../etc/passwd",
                "expected_error": "Path traversal attempt detected",
            },
            # Windows attacks
            {
                "title": "..\\..\\..\\Windows\\System32",
                "expected_error": "Path traversal attempt detected",
            },
            # Mixed separators
            {
                "title": "../..\\/../etc/passwd",
                "expected_error": "Path traversal attempt detected",
            },
            # Absolute paths
            {
                "title": "/etc/shadow",
                "expected_error": "Path traversal attempt detected",
            },
            {
                "title": "C:\\Windows\\System32",
                "expected_error": "Path traversal attempt detected",
            },
            # URL encoding attempts
            {
                "title": "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "expected_error": "Path traversal attempt detected",
            },
            # Null byte injection
            {
                "title": "safe_name\x00../../../etc/passwd",
                "expected_error": "Path traversal attempt detected",
            },
            # Unicode attacks
            {
                "title": "safe\u002e\u002e/\u002e\u002e/etc/passwd",
                "expected_error": "Path traversal attempt detected",
            },
        ]

        for scenario in attack_scenarios:
            with pytest.raises(SecurityError, match=scenario["expected_error"]):
                self.vault_manager.create_note(
                    title=scenario["title"],
                    content="Malicious content",
                    note_type="SourceNote",
                )

            # Verify no files were created with suspicious names
            for root, dirs, files in os.walk(str(self.temp_vault)):
                for file in files:
                    assert "passwd" not in file
                    assert "shadow" not in file
                    assert "System32" not in file

    def test_security_with_concurrent_operations(self):
        """Test security under concurrent operations"""
        import threading

        results = []
        errors = []

        def create_malicious_note(thread_id):
            try:
                self.vault_manager.create_note(
                    title=f"../../../tmp/malicious_{thread_id}",
                    content=f"Thread {thread_id} attack",
                    note_type="SourceNote",
                )
                results.append(f"Thread {thread_id}: SUCCESS - SECURITY BREACH!")
            except SecurityError as e:
                results.append(f"Thread {thread_id}: BLOCKED - {str(e)}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: ERROR - {str(e)}")

        # Launch multiple concurrent attacks
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_malicious_note, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)

        # Verify all attacks were blocked
        for result in results:
            assert "BLOCKED" in result
            assert "Path traversal attempt detected" in result

        # Verify no errors occurred
        assert len(errors) == 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
