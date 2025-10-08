#!/usr/bin/env python3
"""Test Template for Simple Functions
World-Class Finish Guide - Data-driven testing for simple functions.
"""

from typing import Any, Dict

import pytest


class TestSimpleFunction:
    """Test suite for simple functions (complexity ≤ 10)."""

    def test_primary_functionality(self):
        """Test primary functionality."""
        # Test main purpose of the function
        # Test expected inputs and outputs
        # Test normal operation

    def test_edge_cases(self):
        """Test edge cases."""
        # Test boundary values
        # Test empty inputs
        # Test None inputs

    def test_error_handling(self):
        """Test error handling."""
        # Test invalid inputs
        # Test exception cases


# Example test for a simple function
def simple_utility_function(data: str) -> str:
    """Example simple function."""
    if not data:
        return ""

    return data.strip().lower()


class TestSimpleUtilityFunction:
    """Test suite for simple_utility_function."""

    def test_normal_input(self):
        """Test normal input processing."""
        result = simple_utility_function("  Hello World  ")
        assert result == "hello world"

    def test_empty_string(self):
        """Test empty string handling."""
        result = simple_utility_function("")
        assert result == ""

    def test_none_input(self):
        """Test None input handling."""
        result = simple_utility_function(None)
        assert result == ""

    def test_already_clean_input(self):
        """Test already clean input."""
        result = simple_utility_function("hello world")
        assert result == "hello world"

    def test_whitespace_only(self):
        """Test whitespace-only input."""
        result = simple_utility_function("   ")
        assert result == ""

    def test_mixed_case(self):
        """Test mixed case input."""
        result = simple_utility_function("  HeLLo WoRLd  ")
        assert result == "hello world"
