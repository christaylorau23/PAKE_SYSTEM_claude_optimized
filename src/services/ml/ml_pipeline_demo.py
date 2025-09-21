#!/usr/bin/env python3
"""PAKE System - ML Pipeline Integration Demo
Phase 9B: Advanced AI/ML Pipeline Integration

Demonstrates the complete ML pipeline integration including model serving,
training orchestration, feature engineering, prediction services, and monitoring.
"""

import asyncio
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .feature_engineering import (
    create_production_feature_engineer,
)
from .ml_monitoring import (
    MetricType,
    create_production_ml_monitor,
)

# Import ML services
from .model_serving import (
    InferenceRequest,
    ModelFramework,
    create_production_model_serving_service,
)
from .prediction_service import (
    BatchPredictionRequest,
    ModelServingInferenceEngine,
    PredictionRequest,
    PredictionType,
    create_production_prediction_service,
)
from .training_pipeline import (
    ModelType,
    TrainingJob,
    TrainingTrigger,
    create_production_training_orchestrator,
)

# # import pickle  # SECURITY: Replaced with secure serialization  # SECURITY: Replaced with secure serialization


logger = logging.getLogger(__name__)


class MLPipelineDemo:
    """Comprehensive ML pipeline demonstration.
    Shows integration of all ML services in a production-like scenario.
    """

    def __init__(self):
        # Initialize services
        self.model_serving = None
        self.training_orchestrator = None
        self.feature_engineer = None
        self.prediction_service = None
        self.ml_monitor = None

        # Demo data
        self.demo_data = None
        self.demo_models = {}

        logger.info("Initialized ML Pipeline Demo")

    async def setup_services(self):
        """Setup all ML services"""
        try:
            logger.info("Setting up ML services...")

            # Initialize model serving
            self.model_serving = await create_production_model_serving_service()

            # Initialize training orchestrator
            self.training_orchestrator = create_production_training_orchestrator()

            # Initialize feature engineer
            self.feature_engineer = create_production_feature_engineer()

            # Initialize prediction service
            inference_engine = ModelServingInferenceEngine(self.model_serving)
            self.prediction_service = create_production_prediction_service(
                inference_engine,
            )

            # Initialize ML monitor
            self.ml_monitor = create_production_ml_monitor()

            logger.info("All ML services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup ML services: {e}")
            raise

    async def generate_demo_data(self):
        """Generate demo data for training and testing"""
        try:
            logger.info("Generating demo data...")

            # Generate synthetic classification data
            np.random.seed(42)
            n_samples = 1000

            # Features
            X = np.random.randn(n_samples, 10)
            X[:, 0] = X[:, 0] * 2 + 1  # Make first feature more important
            X[:, 1] = X[:, 1] * 1.5 + 0.5

            # Add some categorical features
            categorical_features = np.random.choice(["A", "B", "C"], n_samples)
            categorical_encoded = pd.get_dummies(categorical_features)

            # Combine features
            X_df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(10)])
            X_df = pd.concat([X_df, categorical_encoded], axis=1)

            # Generate target (binary classification)
            y = (X[:, 0] + X[:, 1] + np.random.randn(n_samples) * 0.5 > 0).astype(int)

            # Split data
            train_size = int(0.7 * n_samples)
            val_size = int(0.15 * n_samples)

            X_train = X_df[:train_size]
            y_train = y[:train_size]
            X_val = X_df[train_size : train_size + val_size]
            y_val = y[train_size : train_size + val_size]
            X_test = X_df[train_size + val_size :]
            y_test = y[train_size + val_size :]

            # Create demo data structure
            self.demo_data = {
                "X_train": X_train,
                "y_train": y_train,
                "X_val": X_val,
                "y_val": y_val,
                "X_test": X_test,
                "y_test": y_test,
                "feature_names": X_df.columns.tolist(),
                "target_name": "target",
            }

            # Save demo data
            demo_data_path = Path("/tmp/pake_demo_data.pkl")
            with open(demo_data_path, "wb") as f:
                pickle.dump(self.demo_data, f)

            logger.info(
                f"Generated demo data with {n_samples} samples, {len(X_df.columns)} features",
            )
            logger.info(f"Demo data saved to {demo_data_path}")

        except Exception as e:
            logger.error(f"Failed to generate demo data: {e}")
            raise

    async def demonstrate_feature_engineering(self):
        """Demonstrate feature engineering capabilities"""
        try:
            logger.info("Demonstrating feature engineering...")

            # Create automated feature pipeline
            pipeline_id = await self.feature_engineer.create_automated_pipeline(
                self.demo_data["X_train"],
                self.demo_data["y_train"],
                "demo_classification_pipeline",
            )

            logger.info(f"Created feature pipeline: {pipeline_id}")

            # Process features
            processed_data, result = await self.feature_engineer.process_features(
                self.demo_data["X_train"],
                pipeline_id,
                self.demo_data["y_train"],
            )

            logger.info("Feature processing completed:")
            logger.info(f"  Original shape: {self.demo_data['X_train'].shape}")
            logger.info(f"  Processed shape: {processed_data.shape}")
            logger.info(f"  Processing time: {result.processing_time_ms:.2f}ms")
            logger.info(f"  Features created: {result.features_created}")
            logger.info(f"  Features dropped: {result.features_dropped}")

            # Get statistics
            stats = self.feature_engineer.get_processing_statistics()
            logger.info(f"Feature engineering statistics: {stats}")

            return processed_data

        except Exception as e:
            logger.error(f"Feature engineering demonstration failed: {e}")
            raise

    async def demonstrate_model_training(self, processed_data: pd.DataFrame):
        """Demonstrate model training capabilities"""
        try:
            logger.info("Demonstrating model training...")

            # Prepare training data
            training_data = {
                "X_train": processed_data.values.tolist(),
                "y_train": self.demo_data["y_train"].tolist(),
                # Use subset for validation
                "X_val": processed_data.values.tolist()[:100],
                "y_val": self.demo_data["y_train"].tolist()[:100],
            }

            # Save training data
            training_data_path = Path("/tmp/pake_training_data.pkl")
            with open(training_data_path, "wb") as f:
                pickle.dump(training_data, f)

            # Create training job
            job = TrainingJob(
                job_id=f"demo_training_{int(time.time())}",
                model_name="demo_classifier",
                model_type=ModelType.CLASSIFICATION,
                training_data_path=str(training_data_path),
                hyperparameters={
                    "n_estimators": 100,
                    "max_depth": 10,
                    "random_state": 42,
                },
                training_config={
                    "framework": "sklearn",
                    "model_name": "RandomForestClassifier",
                    "num_classes": 2,
                    "features_count": processed_data.shape[1],
                },
                trigger=TrainingTrigger.MANUAL,
            )

            # Submit training job
            job_id = await self.training_orchestrator.submit_training_job(job)
            logger.info(f"Submitted training job: {job_id}")

            # Wait for completion
            while job_id in self.training_orchestrator.active_jobs:
                await asyncio.sleep(2)
                status = self.training_orchestrator.get_job_status(job_id)
                if status:
                    logger.info(f"Training status: {status.status.value}")

            # Get final result
            result = self.training_orchestrator.get_job_status(job_id)
            if result and result.status.value == "completed":
                logger.info("Training completed successfully:")
                logger.info(f"  Model path: {result.model_path}")
                logger.info(f"  Model version: {result.model_version}")
                logger.info(f"  Training time: {result.training_time_seconds:.2f}s")
                logger.info(f"  Metrics: {result.metrics}")

                # Store model info for serving
                self.demo_models[job_id] = {
                    "model_path": result.model_path,
                    "model_version": result.model_version,
                    "metrics": result.metrics,
                }

                return result.model_path
            logger.error(
                f"Training failed: {result.error_message if result else 'Unknown error'}",
            )
            return None

        except Exception as e:
            logger.error(f"Model training demonstration failed: {e}")
            raise

    async def demonstrate_model_serving(self, model_path: str):
        """Demonstrate model serving capabilities"""
        try:
            logger.info("Demonstrating model serving...")

            # Register model
            model_id = await self.model_serving.register_model(
                model_path=model_path,
                model_name="demo_classifier",
                version="1.0",
                framework=ModelFramework.SKLEARN,
                input_schema={"features": {"type": "array", "shape": [10]}},
                output_schema={"prediction": {"type": "array", "shape": [2]}},
            )

            logger.info(f"Registered model: {model_id}")

            # Load model
            await self.model_serving.load_model(model_id)
            logger.info(f"Loaded model: {model_id}")

            # Test inference
            test_input = {
                "features": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]],
            }

            request = InferenceRequest(
                request_id=f"demo_request_{int(time.time())}",
                model_id=model_id,
                input_data=test_input,
            )

            response = await self.model_serving.predict(request)

            logger.info("Model serving test successful:")
            logger.info(f"  Request ID: {response.request_id}")
            logger.info(f"  Predictions: {response.predictions}")
            logger.info(f"  Processing time: {response.processing_time_ms:.2f}ms")

            # Get model status
            status = self.model_serving.get_model_status(model_id)
            logger.info(f"Model status: {status.to_dict()}")

            return model_id

        except Exception as e:
            logger.error(f"Model serving demonstration failed: {e}")
            raise

    async def demonstrate_prediction_service(self, model_id: str):
        """Demonstrate prediction service capabilities"""
        try:
            logger.info("Demonstrating prediction service...")

            # Test individual prediction
            request = PredictionRequest(
                request_id=f"demo_pred_{int(time.time())}",
                model_ids=[model_id],
                input_data={
                    "features": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]],
                },
                prediction_type=PredictionType.REAL_TIME,
            )

            result = await self.prediction_service.predict(request)

            logger.info("Individual prediction completed:")
            logger.info(f"  Request ID: {result.request_id}")
            logger.info(f"  Predictions: {result.predictions}")
            logger.info(f"  Processing time: {result.processing_time_ms:.2f}ms")
            logger.info(f"  Status: {result.status.value}")

            # Test batch prediction
            batch_request = BatchPredictionRequest(
                batch_id=f"demo_batch_{int(time.time())}",
                model_ids=[model_id],
                input_data_list=[
                    {"features": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]]},
                    {
                        "features": [
                            [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
                        ],
                    },
                    {
                        "features": [
                            [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
                        ],
                    },
                ],
                batch_size=2,
            )

            batch_result = await self.prediction_service.batch_predict(batch_request)

            logger.info("Batch prediction completed:")
            logger.info(f"  Batch ID: {batch_result.batch_id}")
            logger.info(
                f"  Successful predictions: {batch_result.successful_predictions}",
            )
            logger.info(f"  Failed predictions: {batch_result.failed_predictions}")
            logger.info(
                f"  Total processing time: {batch_result.total_processing_time_ms:.2f}ms",
            )

            # Get service statistics
            stats = self.prediction_service.get_service_statistics()
            logger.info(f"Prediction service statistics: {stats}")

        except Exception as e:
            logger.error(f"Prediction service demonstration failed: {e}")
            raise

    async def demonstrate_ml_monitoring(self, model_id: str):
        """Demonstrate ML monitoring capabilities"""
        try:
            logger.info("Demonstrating ML monitoring...")

            # Start monitoring
            await self.ml_monitor.start_monitoring(model_id)

            # Simulate some metrics collection
            for i in range(10):
                await self.ml_monitor._collect_model_metrics(model_id)
                await asyncio.sleep(1)

            # Get metrics
            metrics = self.ml_monitor.get_model_metrics(model_id, limit=5)
            logger.info(f"Collected {len(metrics)} metrics for model {model_id}")

            # Start A/B test
            await self.ml_monitor.start_ab_test(
                f"demo_ab_{int(time.time())}",
                model_id,
                f"{model_id}_variant",
                MetricType.ACCURACY,
                traffic_split=0.5,
            )

            logger.info("Started A/B test")

            # Simulate A/B test metrics
            for i in range(50):
                await self.ml_monitor.record_ab_test_metric(
                    f"demo_ab_{int(time.time())}",
                    model_id,
                    0.85 + np.random.normal(0, 0.02),
                )
                await self.ml_monitor.record_ab_test_metric(
                    f"demo_ab_{int(time.time())}",
                    f"{model_id}_variant",
                    0.87 + np.random.normal(0, 0.02),
                )

            # Get monitoring statistics
            stats = self.ml_monitor.get_monitoring_statistics()
            logger.info(f"ML monitoring statistics: {stats}")

            # Stop monitoring
            await self.ml_monitor.stop_monitoring(model_id)

        except Exception as e:
            logger.error(f"ML monitoring demonstration failed: {e}")
            raise

    async def run_complete_demo(self):
        """Run the complete ML pipeline demonstration"""
        try:
            logger.info("Starting complete ML pipeline demonstration...")

            # Setup services
            await self.setup_services()

            # Generate demo data
            await self.generate_demo_data()

            # Demonstrate feature engineering
            processed_data = await self.demonstrate_feature_engineering()

            # Demonstrate model training
            model_path = await self.demonstrate_model_training(processed_data)

            if model_path:
                # Demonstrate model serving
                model_id = await self.demonstrate_model_serving(model_path)

                # Demonstrate prediction service
                await self.demonstrate_prediction_service(model_id)

                # Demonstrate ML monitoring
                await self.demonstrate_ml_monitoring(model_id)

            logger.info("Complete ML pipeline demonstration finished successfully!")

            # Print summary
            await self.print_demo_summary()

        except Exception as e:
            logger.error(f"Complete demo failed: {e}")
            raise

    async def print_demo_summary(self):
        """Print demonstration summary"""
        try:
            logger.info("=" * 60)
            logger.info("ML PIPELINE DEMONSTRATION SUMMARY")
            logger.info("=" * 60)

            # Model serving summary
            if self.model_serving:
                serving_stats = self.model_serving.get_service_statistics()
                logger.info("Model Serving:")
                logger.info(f"  Loaded models: {serving_stats['loaded_models_count']}")
                logger.info(f"  Total requests: {serving_stats['total_requests']}")
                logger.info(f"  Success rate: {serving_stats['success_rate']:.2%}")
                logger.info(
                    f"  Average latency: {serving_stats['average_latency_ms']:.2f}ms",
                )

            # Training summary
            if self.training_orchestrator:
                training_stats = self.training_orchestrator.get_training_statistics()
                logger.info("Training Orchestrator:")
                logger.info(f"  Total jobs: {training_stats['total_jobs']}")
                logger.info(f"  Completed jobs: {training_stats['completed_jobs']}")
                logger.info(f"  Success rate: {training_stats['success_rate']:.2%}")
                logger.info(
                    f"  Average training time: {training_stats['average_training_time']:.2f}s",
                )

            # Feature engineering summary
            if self.feature_engineer:
                feature_stats = self.feature_engineer.get_processing_statistics()
                logger.info("Feature Engineering:")
                logger.info(
                    f"  Pipelines executed: {feature_stats['pipelines_executed']}",
                )
                logger.info(f"  Features created: {feature_stats['features_created']}")
                logger.info(f"  Cache hit rate: {feature_stats['cache_hit_rate']:.2%}")
                logger.info(
                    f"  Average processing time: {feature_stats['average_processing_time_ms']:.2f}ms",
                )

            # Prediction service summary
            if self.prediction_service:
                prediction_stats = self.prediction_service.get_service_statistics()
                logger.info("Prediction Service:")
                logger.info(f"  Total requests: {prediction_stats['total_requests']}")
                logger.info(
                    f"  Ensemble requests: {prediction_stats['ensemble_requests']}",
                )
                logger.info(f"  Batch requests: {prediction_stats['batch_requests']}")
                logger.info(f"  Success rate: {prediction_stats['success_rate']:.2%}")

            # ML monitoring summary
            if self.ml_monitor:
                monitoring_stats = self.ml_monitor.get_monitoring_statistics()
                logger.info("ML Monitoring:")
                logger.info(
                    f"  Monitored models: {monitoring_stats['monitored_models']}",
                )
                logger.info(
                    f"  Metrics collected: {monitoring_stats['total_metrics_collected']}",
                )
                logger.info(
                    f"  Alerts generated: {monitoring_stats['total_alerts_generated']}",
                )
                logger.info(
                    f"  Active A/B tests: {monitoring_stats['active_ab_tests']}",
                )

            logger.info("=" * 60)
            logger.info("DEMONSTRATION COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Failed to print demo summary: {e}")


async def main():
    """Main function to run the ML pipeline demonstration"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run demo
    demo = MLPipelineDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())
