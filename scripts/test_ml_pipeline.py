#!/usr/bin/env python3
"""
PAKE System - ML Pipeline Test Script
Phase 9B: Advanced AI/ML Pipeline Integration

Comprehensive test script for validating ML pipeline functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from services.ml.ml_monitoring import MetricType
from services.ml.ml_pipeline_demo import MLPipelineDemo
from services.ml.model_serving import ModelFramework
from services.ml.prediction_service import (
    BatchPredictionRequest,
    PredictionRequest,
)
from services.ml.training_pipeline import ModelType, TrainingJob

# Add src to path for imports (fallback for local development)
if str(Path(__file__).parent.parent / "src") not in sys.path:
    sys.path.append(str(Path(__file__).parent.parent / "src"))


logger = logging.getLogger(__name__)


class MLPipelineTester:
    """Comprehensive ML pipeline tester"""

    def __init__(self):
        self.test_results = {}
        self.demo = None

    async def run_all_tests(self):
        """Run all ML pipeline tests"""
        try:
            logger.info("Starting ML Pipeline Tests...")

            # Initialize demo
            self.demo = MLPipelineDemo()
            await self.demo.setup_services()

            # Run individual component tests
            await self.test_model_serving()
            await self.test_training_pipeline()
            await self.test_feature_engineering()
            await self.test_prediction_service()
            await self.test_ml_monitoring()

            # Run integration tests
            await self.test_integration_workflow()

            # Print test summary
            self.print_test_summary()

        except Exception as e:
            logger.error(f"ML pipeline tests failed: {e}")
            raise

    async def test_model_serving(self):
        """Test model serving functionality"""
        try:
            logger.info("Testing Model Serving...")

            # Test service initialization
            assert self.demo.model_serving is not None
            self.test_results["model_serving_init"] = "PASS"

            # Test model registration
            model_id = await self.demo.model_serving.register_model(
                model_path="/tmp/test_model.pkl",
                model_name="test_model",
                version="1.0",
                framework=ModelFramework.SKLEARN,
                input_schema={"features": {"type": "array", "shape": [5]}},
                output_schema={"prediction": {"type": "array", "shape": [2]}},
            )

            assert model_id is not None
            self.test_results["model_registration"] = "PASS"

            # Test model loading (mock)
            # Note: In real test, would need actual model file
            self.test_results["model_loading"] = "SKIP"

            # Test service statistics
            stats = self.demo.model_serving.get_service_statistics()
            assert isinstance(stats, dict)
            self.test_results["model_serving_stats"] = "PASS"

            logger.info("Model Serving tests completed")

        except Exception as e:
            logger.error(f"Model serving test failed: {e}")
            self.test_results["model_serving"] = f"FAIL: {e}"

    async def test_training_pipeline(self):
        """Test training pipeline functionality"""
        try:
            logger.info("Testing Training Pipeline...")

            # Test orchestrator initialization
            assert self.demo.training_orchestrator is not None
            self.test_results["training_orchestrator_init"] = "PASS"

            # Test job creation
            job = TrainingJob(
                job_id="test_job_001",
                model_name="test_classifier",
                model_type=ModelType.CLASSIFICATION,
                training_data_path="/tmp/test_data.pkl",
                hyperparameters={"n_estimators": 10},
                training_config={
                    "framework": "sklearn",
                    "model_name": "RandomForestClassifier",
                },
            )

            assert job.job_id == "test_job_001"
            self.test_results["job_creation"] = "PASS"

            # Test job validation
            is_valid = self.demo.training_orchestrator._validate_job(job)
            assert is_valid
            self.test_results["job_validation"] = "PASS"

            # Test statistics
            stats = self.demo.training_orchestrator.get_training_statistics()
            assert isinstance(stats, dict)
            self.test_results["training_stats"] = "PASS"

            logger.info("Training Pipeline tests completed")

        except Exception as e:
            logger.error(f"Training pipeline test failed: {e}")
            self.test_results["training_pipeline"] = f"FAIL: {e}"

    async def test_feature_engineering(self):
        """Test feature engineering functionality"""
        try:
            logger.info("Testing Feature Engineering...")

            # Test engineer initialization
            assert self.demo.feature_engineer is not None
            self.test_results["feature_engineer_init"] = "PASS"

            # Create test data
            test_data = pd.DataFrame(
                {
                    "numerical_1": np.random.normal(0, 1, 100),
                    "numerical_2": np.random.normal(5, 2, 100),
                    "categorical_1": np.random.choice(["A", "B", "C"], 100),
                    "text_1": ["sample text " + str(i) for i in range(100)],
                },
            )

            # Test automated pipeline creation
            pipeline_id = await self.demo.feature_engineer.create_automated_pipeline(
                test_data,
                None,
                "test_pipeline",
            )

            assert pipeline_id is not None
            self.test_results["pipeline_creation"] = "PASS"

            # Test feature processing
            processed_data, result = await self.demo.feature_engineer.process_features(
                test_data,
                pipeline_id,
            )

            assert isinstance(processed_data, pd.DataFrame)
            assert isinstance(result.processing_time_ms, float)
            self.test_results["feature_processing"] = "PASS"

            # Test statistics
            stats = self.demo.feature_engineer.get_processing_statistics()
            assert isinstance(stats, dict)
            self.test_results["feature_stats"] = "PASS"

            logger.info("Feature Engineering tests completed")

        except Exception as e:
            logger.error(f"Feature engineering test failed: {e}")
            self.test_results["feature_engineering"] = f"FAIL: {e}"

    async def test_prediction_service(self):
        """Test prediction service functionality"""
        try:
            logger.info("Testing Prediction Service...")

            # Test service initialization
            assert self.demo.prediction_service is not None
            self.test_results["prediction_service_init"] = "PASS"

            # Test request validation
            request = PredictionRequest(
                request_id="test_request",
                model_ids=["model_1"],
                input_data={"features": [[1, 2, 3, 4, 5]]},
            )

            is_valid = self.demo.prediction_service._validate_request(request)
            assert is_valid
            self.test_results["request_validation"] = "PASS"

            # Test batch request validation
            batch_request = BatchPredictionRequest(
                batch_id="test_batch",
                model_ids=["model_1"],
                input_data_list=[
                    {"features": [[1, 2, 3, 4, 5]]},
                    {"features": [[2, 3, 4, 5, 6]]},
                ],
            )

            is_valid = self.demo.prediction_service._validate_batch_request(
                batch_request,
            )
            assert is_valid
            self.test_results["batch_request_validation"] = "PASS"

            # Test statistics
            stats = self.demo.prediction_service.get_service_statistics()
            assert isinstance(stats, dict)
            self.test_results["prediction_stats"] = "PASS"

            logger.info("Prediction Service tests completed")

        except Exception as e:
            logger.error(f"Prediction service test failed: {e}")
            self.test_results["prediction_service"] = f"FAIL: {e}"

    async def test_ml_monitoring(self):
        """Test ML monitoring functionality"""
        try:
            logger.info("Testing ML Monitoring...")

            # Test monitor initialization
            assert self.demo.ml_monitor is not None
            self.test_results["ml_monitor_init"] = "PASS"

            # Test A/B test creation
            await self.demo.ml_monitor.start_ab_test(
                "test_ab_001",
                "model_a",
                "model_b",
                MetricType.ACCURACY,
                traffic_split=0.5,
            )

            self.test_results["ab_test_creation"] = "PASS"

            # Test metric recording
            await self.demo.ml_monitor.record_ab_test_metric(
                "test_ab_001",
                "model_a",
                0.85,
            )
            await self.demo.ml_monitor.record_ab_test_metric(
                "test_ab_001",
                "model_b",
                0.87,
            )

            self.test_results["metric_recording"] = "PASS"

            # Test statistics
            stats = self.demo.ml_monitor.get_monitoring_statistics()
            assert isinstance(stats, dict)
            self.test_results["monitoring_stats"] = "PASS"

            logger.info("ML Monitoring tests completed")

        except Exception as e:
            logger.error(f"ML monitoring test failed: {e}")
            self.test_results["ml_monitoring"] = f"FAIL: {e}"

    async def test_integration_workflow(self):
        """Test integrated ML workflow"""
        try:
            logger.info("Testing Integration Workflow...")

            # Test data generation
            await self.demo.generate_demo_data()
            assert self.demo.demo_data is not None
            self.test_results["data_generation"] = "PASS"

            # Test feature engineering integration
            processed_data = await self.demo.demonstrate_feature_engineering()
            assert isinstance(processed_data, pd.DataFrame)
            self.test_results["feature_integration"] = "PASS"

            # Test service coordination
            services = [
                self.demo.model_serving,
                self.demo.training_orchestrator,
                self.demo.feature_engineer,
                self.demo.prediction_service,
                self.demo.ml_monitor,
            ]

            all_initialized = all(service is not None for service in services)
            assert all_initialized
            self.test_results["service_coordination"] = "PASS"

            logger.info("Integration Workflow tests completed")

        except Exception as e:
            logger.error(f"Integration workflow test failed: {e}")
            self.test_results["integration_workflow"] = f"FAIL: {e}"

    def print_test_summary(self):
        """Print test results summary"""
        try:
            logger.info("=" * 60)
            logger.info("ML PIPELINE TEST SUMMARY")
            logger.info("=" * 60)

            total_tests = len(self.test_results)
            passed_tests = len([r for r in self.test_results.values() if r == "PASS"])
            skipped_tests = len([r for r in self.test_results.values() if r == "SKIP"])
            failed_tests = len(
                [r for r in self.test_results.values() if r.startswith("FAIL")],
            )

            logger.info(f"Total Tests: {total_tests}")
            logger.info(f"Passed: {passed_tests}")
            logger.info(f"Skipped: {skipped_tests}")
            logger.info(f"Failed: {failed_tests}")
            logger.info(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")

            logger.info("\nDetailed Results:")
            for test_name, result in self.test_results.items():
                status_icon = (
                    "✅" if result == "PASS" else "⏭️" if result == "SKIP" else "❌"
                )
                logger.info(f"  {status_icon} {test_name}: {result}")

            if failed_tests == 0:
                logger.info(
                    "\n🎉 ALL TESTS PASSED! ML Pipeline is ready for production.",
                )
            else:
                logger.info(
                    f"\n⚠️  {failed_tests} tests failed. Please review and fix issues.",
                )

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Failed to print test summary: {e}")


async def main():
    """Main function to run ML pipeline tests"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run tests
    tester = MLPipelineTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
