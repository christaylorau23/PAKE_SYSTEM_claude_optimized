#!/usr/bin/env python3
"""
Deployment script for the Intelligent Content Curation System.
Handles model training, system initialization, and production deployment.
"""

import argparse
import asyncio
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys

import uvicorn

from services.curation.api.curation_api import app
from services.curation.integration.curation_orchestrator import CurationOrchestrator

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


logger = logging.getLogger(__name__)


class CurationDeployment:
    """Handles deployment of the curation system"""

def __init__(self, config_path: Any = None) -> None:
        self.config_path = config_path
        self.config = self._load_config()
        self.orchestrator = None

    def _load_config(self) -> dict:
        """Load deployment configuration"""
        default_config = {
            "models_dir": "models",
            "cache_size": 10000,
            "cache_ttl_hours": 1,
            "api_host": "127.0.0.1",
            "api_port": 8001,
            "max_batch_size": 100,
            "prediction_timeout": 5.0,
            "feature_cache_size": 5000,
            "retrain_interval_days": 7,
            "min_training_samples": 100,
        }

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Error loading config file: %s", e)

        return default_config

    async def initialize_system(self) -> bool:
        """Initialize the curation system"""
        logger.info("Initializing curation system...")

        try:
            self.orchestrator = CurationOrchestrator()
            success = await self.orchestrator.initialize()

            if success:
                logger.info("✅ Curation system initialized successfully")
                return True
            logger.error("❌ Failed to initialize curation system")
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Error initializing system: %s", e)
            return False

    async def train_models(self, force_retrain: bool = False) -> bool:
        """Train or retrain ML models"""
        logger.info("Training ML models...")

        try:
            if not self.orchestrator:
                await self.initialize_system()

            # Check if retraining is needed
            if not force_retrain and self.orchestrator.last_model_update:
                days_since_update = (
                    datetime.now(UTC) - self.orchestrator.last_model_update
                ).days
                if days_since_update < self.config["retrain_interval_days"]:
                    logger.info(
                        "Models are up to date (updated %s days ago)",
                        days_since_update,
                    )
                    return True

            # Get training data
            contents = await self._get_training_content()
            user_profiles = await self._get_training_users()
            interactions = await self._get_training_interactions()

            # Check if we have enough data
            if len(contents) < self.config["min_training_samples"]:
                logger.warning(
                    "Insufficient training data: %s samples (minimum: %s)",
                    len(contents),
                    self.config["min_training_samples"],
                )
                return False

            # Train models
            results = await self.orchestrator.retrain_models(force_retrain=True)

            if results.get("retrained"):
                logger.info("✅ Models trained successfully")
                return True
            logger.error(
                "❌ Model training failed: %s",
                results.get("error", "Unknown error"),
            )
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Error training models: %s", e)
            return False

    async def _get_training_content(self) -> None:
        """Get content for model training"""
        # TODO: Integrate with existing PAKE database
        # For now, return empty list - models will use fallback strategies
        logger.info("Getting training content from PAKE database...")
        return []

    async def _get_training_users(self) -> None:
        """Get users for model training"""
        # TODO: Integrate with existing PAKE database
        logger.info("Getting training users from PAKE database...")
        return []

    async def _get_training_interactions(self) -> None:
        """Get interactions for model training"""
        # TODO: Integrate with existing PAKE database
        logger.info("Getting training interactions from PAKE database...")
        return []

    async def run_health_check(self) -> bool:
        """Run system health check"""
        logger.info("Running health check...")

        try:
            if not self.orchestrator:
                await self.initialize_system()

            health = await self.orchestrator.get_system_health()

            # Check service health
            unhealthy_services = [
                name for name, healthy in health.services_healthy.items() if not healthy
            ]
            if unhealthy_services:
                logger.warning("Unhealthy services: %s", unhealthy_services)

            # Check model status
            loaded_models = sum(health.models_loaded.values())
            total_models = len(health.models_loaded)
            logger.info("Models loaded: %s/%s", loaded_models, total_models)

            # Check performance metrics
            avg_prediction_time = health.performance_metrics.get(
                "avg_prediction_time_ms",
                0,
            )
            cache_hit_rate = health.cache_status.get("cache_hit_rate", 0)

            logger.info("Average prediction time: %.2f%%ms", avg_prediction_time)
            logger.info("Cache hit rate: %s", f"{cache_hit_rate:.2%}")

            # Overall health assessment
            all_services_healthy = all(health.services_healthy.values())
            models_loaded = loaded_models > 0

            if all_services_healthy and models_loaded:
                logger.info("✅ System health check passed")
                return True
            logger.warning("⚠️ System health check failed")
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Health check failed: %s", e)
            return False

    async def run_performance_test(self) -> bool:
        """Run performance tests"""
        logger.info("Running performance tests...")

        try:
            if not self.orchestrator:
                await self.initialize_system()

            # Create test request
            from services.curation.integration.curation_orchestrator import (
                CurationRequest,
            )

            test_request = CurationRequest(
                user_id="test-user",
                query="machine learning",
                interests=["AI", "ML"],
                max_results=10,
            )

            # Measure response time
            start_time = datetime.now(UTC)
            response = await self.orchestrator.curate_content(test_request)
            end_time = datetime.now(UTC)

            response_time = (end_time - start_time).total_seconds() * 1000

            logger.info("Test response time: %.2f%%ms", response_time)
            logger.info("Recommendations generated: %s", len(response.recommendations))
            logger.info("Content analyzed: %s", response.total_content_analyzed)
            logger.info("Cache hit rate: %s", f"{response.cache_hit_rate:.2%}")

            # Performance criteria
            if response_time < 1000:  # Sub-second response
                logger.info("✅ Performance test passed")
                return True
            logger.warning(
                "⚠️ Performance test failed: %sms > 1000ms",
                response_time,
            )
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("❌ Performance test failed: %s", e)
            return False

    def start_api_server(self) -> None:
        """Start the API server"""
        logger.info(
            "Starting API server on %s:%s",
            self.config["api_host"],
            self.config["api_port"],
        )

        uvicorn.run(
            app,
            host=self.config["api_host"],
            port=self.config["api_port"],
            log_level="info",
            access_log=True,
        )

    async def shutdown(self) -> None:
        """Shutdown the system"""
        if self.orchestrator:
            await self.orchestrator.shutdown()
        logger.info("System shutdown completed")


async def main(self) -> None:
    """Main deployment function"""
    parser = argparse.ArgumentParser(
        description="Deploy Intelligent Content Curation System",
    )
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument(
        "--init-only",
        action="store_true",
        help="Only initialize system",
    )
    parser.add_argument("--train-models", action="store_true", help="Train models")
    parser.add_argument(
        "--force-retrain",
        action="store_true",
        help="Force model retraining",
    )
    parser.add_argument("--health-check", action="store_true", help="Run health check")
    parser.add_argument(
        "--performance-test",
        action="store_true",
        help="Run performance test",
    )
    parser.add_argument("--start-api", action="store_true", help="Start API server")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    deployment = CurationDeployment(args.config)

    try:
        # Initialize system
        if not await deployment.initialize_system():
            logger.error("Failed to initialize system")
            return 1

        if args.init_only:
            logger.info("System initialization completed")
            return 0

        # Train models
        if args.train_models:
            if not await deployment.train_models(args.force_retrain):
                logger.error("Model training failed")
                return 1

        # Health check
        if args.health_check and not await deployment.run_health_check():
            logger.warning("Health check failed")
            return 1

        # Performance test
        if args.performance_test:
            if not await deployment.run_performance_test():
                logger.warning("Performance test failed")
                return 1

        # Start API server
        if args.start_api:
            deployment.start_api_server()

        # If no specific action, run full deployment
        if not any(
            [
                args.train_models,
                args.health_check,
                args.performance_test,
                args.start_api,
            ],
        ):
            logger.info("Running full deployment...")

            # Train models
            await deployment.train_models()

            # Health check
            await deployment.run_health_check()

            # Performance test
            await deployment.run_performance_test()

            logger.info("✅ Deployment completed successfully")

        return 0

    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        return 0
    except (ValueError, RuntimeError) as e:
        logger.error("Deployment failed: %s", e)
        return 1
    finally:
        await deployment.shutdown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
