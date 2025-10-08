#!/usr/bin/env python3
"""PAKE System - Chaos Engineering Test Runner
Section 3.2: Implementing Proactive Resilience

This script provides a comprehensive test runner for all chaos engineering experiments.
"""

from datetime import datetime
import json
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChaosTestRunner:
    """Comprehensive test runner for chaos engineering experiments."""

    def __init__(self):
        self.experiments_dir = "experiments"
        self.results_dir = "results"
        self.config_file = "chaos_config.yaml"

        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)

        # Load configuration
        self.config = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Load chaos engineering configuration."""
        try:
            import yaml

            with open(self.config_file) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        logger.info("Checking prerequisites...")

        # Check if chaos toolkit is installed
        try:
            subprocess.run(["chaos", "--version"], capture_output=True, check=True)
            logger.info("✅ Chaos Toolkit is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ Chaos Toolkit not found. Please install it first.")
            return False

        # Check environment variables
        required_env_vars = [
            "CHAOS_STAGING_URL",
            "CHAOS_DATABASE_URL",
            "CHAOS_KUBECONFIG",
        ]

        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return False

        logger.info("✅ All prerequisites met")
        return True

    def run_experiment(self, experiment_file: str) -> dict[str, Any]:
        """Run a single chaos experiment."""
        logger.info(f"Running experiment: {experiment_file}")

        start_time = time.time()
        result = {
            "experiment": experiment_file,
            "start_time": datetime.now().isoformat(),
            "status": "unknown",
            "duration": 0,
            "output": "",
            "error": None,
        }

        try:
            # Run chaos experiment
            process = subprocess.run(
                ["chaos", "run", experiment_file],
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            result["duration"] = time.time() - start_time
            result["output"] = process.stdout
            result["status"] = "success" if process.returncode == 0 else "failed"

            if process.stderr:
                result["error"] = process.stderr

            logger.info(
                f"✅ Experiment {experiment_file} completed in {result['duration']:.2f}s"
            )

        except subprocess.TimeoutExpired:
            result["duration"] = time.time() - start_time
            result["status"] = "timeout"
            result["error"] = "Experiment timed out after 1 hour"
            logger.error(f"❌ Experiment {experiment_file} timed out")

        except Exception as e:
            result["duration"] = time.time() - start_time
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"❌ Experiment {experiment_file} failed: {e}")

        return result

    def run_all_experiments(self) -> list[dict[str, Any]]:
        """Run all chaos experiments."""
        logger.info("Starting comprehensive chaos engineering test suite")

        if not self.check_prerequisites():
            logger.error("Prerequisites check failed. Aborting.")
            return []

        experiments = [
            "database_failover_test.json",
            "api_instance_failure_test.json",
            "backup_restore_validation.json",
        ]

        results = []
        for experiment in experiments:
            experiment_path = os.path.join(self.experiments_dir, experiment)
            if os.path.exists(experiment_path):
                result = self.run_experiment(experiment_path)
                results.append(result)
            else:
                logger.warning(f"Experiment file not found: {experiment_path}")

        return results

    def generate_report(self, results: list[dict[str, Any]]) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append("# PAKE System - Chaos Engineering Test Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Summary
        total_experiments = len(results)
        successful_experiments = len([r for r in results if r["status"] == "success"])
        failed_experiments = len([r for r in results if r["status"] == "failed"])

        report.append("## Summary")
        report.append(f"- Total Experiments: {total_experiments}")
        report.append(f"- Successful: {successful_experiments}")
        report.append(f"- Failed: {failed_experiments}")
        report.append(
            f"- Success Rate: {(successful_experiments / total_experiments * 100):.1f}%"
            if total_experiments > 0
            else "- Success Rate: 0%"
        )
        report.append("")

        # Detailed Results
        report.append("## Detailed Results")
        for result in results:
            report.append(f"### {result['experiment']}")
            report.append(f"- Status: {result['status']}")
            report.append(f"- Duration: {result['duration']:.2f}s")
            report.append(f"- Start Time: {result['start_time']}")

            if result["error"]:
                report.append(f"- Error: {result['error']}")

            report.append("")

        # Recommendations
        report.append("## Recommendations")
        if failed_experiments > 0:
            report.append("- Review failed experiments and address underlying issues")
            report.append(
                "- Consider adjusting thresholds or improving system resilience"
            )
        else:
            report.append("- All experiments passed successfully")
            report.append("- System demonstrates strong resilience characteristics")

        report.append("- Continue regular chaos engineering testing")
        report.append("- Monitor system metrics during experiments")
        report.append("- Document lessons learned and system improvements")

        return "\n".join(report)

    def save_results(self, results: list[dict[str, Any]], report: str):
        """Save test results and report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        results_file = os.path.join(self.results_dir, f"chaos_results_{timestamp}.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        # Save report
        report_file = os.path.join(self.results_dir, f"chaos_report_{timestamp}.md")
        with open(report_file, "w") as f:
            f.write(report)

        logger.info(f"Results saved to: {results_file}")
        logger.info(f"Report saved to: {report_file}")

    def run_comprehensive_test(self):
        """Run comprehensive chaos engineering test suite."""
        logger.info("🚀 Starting PAKE System Chaos Engineering Test Suite")

        # Run all experiments
        results = self.run_all_experiments()

        if not results:
            logger.error(
                "No experiments were run. Check prerequisites and configuration."
            )
            return

        # Generate and save report
        report = self.generate_report(results)
        self.save_results(results, report)

        # Print summary
        successful = len([r for r in results if r["status"] == "success"])
        total = len(results)

        logger.info(f"🎯 Test Suite Complete: {successful}/{total} experiments passed")

        if successful == total:
            logger.info(
                "🎉 All chaos engineering tests passed! System resilience validated."
            )
        else:
            logger.warning(
                f"⚠️ {total - successful} experiments failed. Review results for details."
            )


def main():
    """Main entry point."""
    runner = ChaosTestRunner()
    runner.run_comprehensive_test()


if __name__ == "__main__":
    main()
