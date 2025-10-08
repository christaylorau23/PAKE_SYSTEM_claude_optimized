import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""Test script for coverage analysis of core modules."""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test importing core modules."""
    try:
        # Test basic imports
        import src.utils.logger

        print("✓ Logger module imported successfully")

        # Test some basic functionality
        from src.utils.logger import StructuredLogger

        logger = StructuredLogger(service_name="test")
        logger.info("Test message")
        print("✓ Logger functionality works")

    except (ImportError, ModuleNotFoundError) as e:
        print(f"✗ Import failed: {e}")
        return False

    return True


def test_basic_functionality():
    """Test basic functionality of imported modules."""
    try:
        # Test logger
        from src.utils.logger import StructuredLogger

        logger = StructuredLogger(service_name="coverage_test")
        logger.info("Coverage test message", test_param="value")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")
        print("✓ Logger methods work correctly")

    except (ValueError, RuntimeError) as e:
        print(f"✗ Functionality test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("Running coverage test...")

    success = True
    success &= test_imports()
    success &= test_basic_functionality()

    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
        sys.exit(1)
