#!/usr/bin/env python3
"""
PAKE System - DAL Integration Test Execution Script
Executes comprehensive Data Access Layer integration tests with proper async configuration.
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_dal_tests(self) -> None:
    """Run DAL integration tests with proper async configuration."""
    logger.info("Starting DAL integration test execution")

    # Set test environment
    os.environ["PAKE_ENVIRONMENT"] = "test"
    os.environ["PAKE_DEBUG"] = "true"
    os.environ["USE_VAULT"] = "false"

    # Test commands to run
    test_commands = [
        {
            "name": "DAL Integration Tests",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_dal_integration.py",
                "-v",
                "--tb=short",
                "--cov=src/services/database",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml",
                "--cov-fail-under=90",
                "-m",
                "integration_database",
                "--asyncio-mode=auto",
            ],
        },
        {
            "name": "Existing DAL Tests",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_dal.py",
                "tests/test_dal_simple.py",
                "-v",
                "--tb=short",
                "--asyncio-mode=auto",
            ],
        },
        {
            "name": "Async Debugging Tests",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit/utils/test_async_debugging.py",
                "-v",
                "--tb=short",
                "--asyncio-mode=auto",
            ],
        },
    ]

    results = {}

    for test_config in test_commands:
        logger.info("Running %s...", test_config["name"])

        try:
            result = subprocess.run(
                test_config["cmd"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info("✅ %s PASSED", test_config["name"])
                results[test_config["name"]] = {
                    "status": "PASSED",
                    "output": result.stdout,
                }
            else:
                logger.error("❌ %s FAILED", test_config["name"])
                logger.error("Error: %s", result.stderr)
                results[test_config["name"]] = {
                    "status": "FAILED",
                    "output": result.stdout,
                    "error": result.stderr,
                }

        except subprocess.TimeoutExpired:
            logger.error("⏰ %s TIMEOUT", test_config["name"])
            results[test_config["name"]] = {
                "status": "TIMEOUT",
                "error": "Test execution timed out",
            }
        except Exception as e:
            logger.error("💥 %s ERROR: %s", test_config["name"], e)
            results[test_config["name"]] = {"status": "ERROR", "error": str(e)}

    # Generate summary
    logger.info("\n" + "=" * 60)
    logger.info("DAL INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)

    passed_count = sum(1 for r in results.values() if r["status"] == "PASSED")
    total_count = len(results)

    for test_name, result in results.items():
        status_emoji = {
            "PASSED": "✅",
            "FAILED": "❌",
            "TIMEOUT": "⏰",
            "ERROR": "💥",
        }.get(result["status"], "❓")

        logger.info("%s %s: %s", status_emoji, test_name, result["status"])

    logger.info("\nOverall Result: %s/%s tests passed", passed_count, total_count)

    if passed_count == total_count:
        logger.info("🎉 All DAL integration tests PASSED!")
        return True
    logger.error("💥 Some DAL integration tests FAILED!")
    return False


async def main(self) -> None:
    """Main execution function."""
    try:
        success = await run_dal_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        return 130
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
