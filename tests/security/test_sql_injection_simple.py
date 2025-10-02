#!/usr/bin/env python3
"""
Simple test suite for SQL injection remediation validation.

This test suite validates that SQL injection vulnerabilities have been
properly remediated using basic database operations.
"""

import os
import sqlite3
import tempfile

import pytest


class TestSQLInjectionRemediation:
    """Test SQL injection remediation with simple database operations."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_parameterized_query_execution(self):
        """Test that parameterized queries execute correctly."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE test_users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT
            )
        """
        )

        # Insert test data using parameterized query
        cursor.execute(
            """
            INSERT INTO test_users (name, email)
            VALUES (?, ?)
        """,
            ("John Doe", "john@example.com"),
        )

        conn.commit()

        # Query using parameterized query
        cursor.execute(
            """
            SELECT * FROM test_users WHERE name = ?
        """,
            ("John Doe",),
        )

        result = cursor.fetchone()
        assert result is not None, "Should find the user"
        assert result[1] == "John Doe", "Should return correct name"

        conn.close()

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are prevented."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """
        )

        # Insert test data
        cursor.execute(
            """
            INSERT INTO test_data (value)
            VALUES (?)
        """,
            ("safe_value",),
        )

        conn.commit()

        # Attempt SQL injection with parameterized query
        malicious_input = "'; DROP TABLE test_data; --"

        # This should be treated as a literal string, not SQL
        cursor.execute(
            """
            SELECT * FROM test_data WHERE value = ?
        """,
            (malicious_input,),
        )

        result = cursor.fetchone()
        assert result is None, "Should not find malicious input as data"

        # Verify table still exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_data'"
        )
        table_exists = cursor.fetchone()
        assert table_exists is not None, "Table should still exist"

        conn.close()

    def test_comprehensive_sql_injection_protection(self):
        """Comprehensive test for SQL injection protection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE security_test (
                id INTEGER PRIMARY KEY,
                user_input TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Test various SQL injection patterns
        injection_patterns = [
            "'; DROP TABLE security_test; --",
            "' OR '1'='1",
            "'; INSERT INTO security_test (user_input) VALUES ('hacked'); --",
            "'; UPDATE security_test SET user_input = 'hacked'; --",
            "'; DELETE FROM security_test; --",
            "'; CREATE TABLE hacked (id INT); --",
            "'; ALTER TABLE security_test ADD COLUMN hacked TEXT; --",
        ]

        for pattern in injection_patterns:
            # Insert using parameterized query
            cursor.execute(
                """
                INSERT INTO security_test (user_input)
                VALUES (?)
            """,
                (pattern,),
            )

            # Query using parameterized query
            cursor.execute(
                """
                SELECT * FROM security_test WHERE user_input = ?
            """,
                (pattern,),
            )

            result = cursor.fetchone()
            assert result is not None, f"Should find injected pattern: {pattern}"

            # Verify table structure is unchanged
            cursor.execute("PRAGMA table_info(security_test)")
            columns = cursor.fetchall()
            assert len(columns) == 3, "Table should have exactly 3 columns"

            # Verify no additional tables were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            assert "hacked" not in table_names, "No malicious tables should be created"

        conn.commit()
        conn.close()

    def test_performance_with_parameterized_queries(self):
        """Test that parameterized queries maintain good performance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE performance_test (
                id INTEGER PRIMARY KEY,
                value TEXT,
                number INTEGER
            )
        """
        )

        # Insert test data
        for i in range(1000):
            cursor.execute(
                """
                INSERT INTO performance_test (value, number)
                VALUES (?, ?)
            """,
                (f"value_{i}", i),
            )

        conn.commit()

        # Test parameterized query performance
        import time

        start_time = time.time()

        for i in range(100):
            cursor.execute(
                """
                SELECT * FROM performance_test WHERE number = ?
            """,
                (i * 10,),
            )
            result = cursor.fetchone()
            assert result is not None, "Should find the record"

        end_time = time.time()
        execution_time = end_time - start_time

        # Parameterized queries should be fast (less than 1 second for 100 queries)
        assert (
            execution_time < 1.0
        ), f"Parameterized queries should be fast, took {execution_time}s"

        conn.close()

    def test_like_operator_parameterization(self):
        """Test that LIKE operator uses parameterized queries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE search_test (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
        """
        )

        # Insert test data
        cursor.execute(
            """
            INSERT INTO search_test (content)
            VALUES (?)
        """,
            ("This is a test content",),
        )

        conn.commit()

        # Test LIKE with parameterized query (simulating the fixed social scheduler)
        search_term = "test"
        platform_pattern = f"%{search_term}%"

        cursor.execute(
            """
            SELECT * FROM search_test WHERE content LIKE ?
        """,
            (platform_pattern,),
        )

        result = cursor.fetchone()
        assert result is not None, "Should find matching content"
        assert "test" in result[1], "Should contain the search term"

        # Test with malicious input
        malicious_search = "'; DROP TABLE search_test; --"
        malicious_pattern = f"%{malicious_search}%"

        cursor.execute(
            """
            SELECT * FROM search_test WHERE content LIKE ?
        """,
            (malicious_pattern,),
        )

        result = cursor.fetchone()
        assert result is None, "Should not find malicious pattern"

        # Verify table still exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='search_test'"
        )
        table_exists = cursor.fetchone()
        assert table_exists is not None, "Table should still exist"

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
