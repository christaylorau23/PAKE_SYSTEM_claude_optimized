#!/usr/bin/env python3
"""PAKE System - Training Pipeline Orchestrator
Phase 9B: Advanced AI/ML Pipeline Integration

Provides automated ML training pipelines with Kubeflow integration,
experiment tracking, model versioning, and automated retraining capabilities.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn
    import mlflow.tensorflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    # Create dummy classes for when mlflow is not available
    class mlflow:
        class pytorch: pass
        class sklearn: pass
        class tensorflow: pass
import numpy as np

# # import pickle  # SECURITY: Replaced with secure serialization  # SECURITY: Replaced with secure serialization
from kubernetes import client, config

logger = logging.getLogger(__name__)


class TrainingStatus(Enum):
    """Training job status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class ModelType(Enum):
    """Types of ML models"""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    RECOMMENDATION = "recommendation"
    TIME_SERIES = "time_series"


class TrainingTrigger(Enum):
    """Triggers for training jobs"""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    DATA_DRIFT = "data_drift"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    NEW_DATA = "new_data"
    MODEL_EXPIRY = "model_expiry"


@dataclass(frozen=True)
class TrainingJob:
    """Immutable training job specification"""

    job_id: str
    model_name: str
    model_type: ModelType
    training_data_path: str
    validation_data_path: str | None = None
    test_data_path: str | None = None
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    training_config: dict[str, Any] = field(default_factory=dict)
    trigger: TrainingTrigger = TrainingTrigger.MANUAL
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "system"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "training_data_path": self.training_data_path,
            "validation_data_path": self.validation_data_path,
            "test_data_path": self.test_data_path,
            "hyperparameters": self.hyperparameters,
            "training_config": self.training_config,
            "trigger": self.trigger.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "tags": self.tags,
        }


@dataclass(frozen=True)
class TrainingResult:
    """Immutable training result"""

    job_id: str
    model_name: str
    status: TrainingStatus
    model_path: str | None = None
    model_version: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    training_time_seconds: float = 0.0
    data_size: int = 0
    features_count: int = 0
    completed_at: datetime | None = None
    error_message: str | None = None
    mlflow_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "model_name": self.model_name,
            "status": self.status.value,
            "model_path": self.model_path,
            "model_version": self.model_version,
            "metrics": self.metrics,
            "training_time_seconds": self.training_time_seconds,
            "data_size": self.data_size,
            "features_count": self.features_count,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
            "mlflow_run_id": self.mlflow_run_id,
        }


@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable experiment configuration"""

    experiment_name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    artifact_location: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "experiment_name": experiment_name,
            "description": self.description,
            "tags": self.tags,
            "artifact_location": self.artifact_location,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TrainingPipelineConfig:
    """Configuration for training pipeline"""

    # MLflow settings
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment_name: str = "pake-ml-experiments"
    enable_mlflow_logging: bool = True

    # Kubernetes settings
    kubernetes_namespace: str = "pake-ml"
    kubernetes_config_path: str | None = None
    enable_kubeflow: bool = True

    # Training settings
    max_concurrent_jobs: int = 5
    default_training_timeout_hours: int = 24
    enable_hyperparameter_tuning: bool = True
    max_tuning_trials: int = 50

    # Model validation
    enable_model_validation: bool = True
    validation_threshold: float = 0.7
    enable_cross_validation: bool = True
    cv_folds: int = 5

    # Storage settings
    model_storage_path: str = "/models"
    data_storage_path: str = "/data"
    artifact_storage_path: str = "/artifacts"

    # Monitoring
    enable_training_monitoring: bool = True
    monitoring_interval_seconds: int = 60
    enable_alerting: bool = True


class ModelTrainer(ABC):
    """Abstract base class for model trainers"""

    @abstractmethod
    async def train_model(
        self,
        job: TrainingJob,
        data: Any,
    ) -> tuple[Any, dict[str, float]]:
        """Train a model and return model and metrics"""

    @abstractmethod
    def save_model(self, model: Any, path: str) -> bool:
        """Save model to path"""

    @abstractmethod
    def load_model(self, path: str) -> Any:
        """Load model from path"""


class SklearnTrainer(ModelTrainer):
    """Scikit-learn model trainer"""

    def __init__(self):
        self.supported_models = {
            ModelType.CLASSIFICATION: [
                "RandomForestClassifier",
                "GradientBoostingClassifier",
                "LogisticRegression",
                "SVC",
            ],
            ModelType.REGRESSION: [
                "RandomForestRegressor",
                "GradientBoostingRegressor",
                "LinearRegression",
                "SVR",
            ],
            ModelType.CLUSTERING: ["KMeans", "DBSCAN", "AgglomerativeClustering"],
        }

    async def train_model(
        self,
        job: TrainingJob,
        data: Any,
    ) -> tuple[Any, dict[str, float]]:
        """Train scikit-learn model"""
        try:
            # Get model class
            model_class = self._get_model_class(job)
            if not model_class:
                raise ValueError(f"Unsupported model type: {job.model_type}")

            # Create model instance
            model = model_class(**job.hyperparameters)

            # Prepare data
            X_train, y_train, X_val, y_val = self._prepare_data(data, job)

            # Train model
            start_time = time.time()
            model.fit(X_train, y_train)
            training_time = time.time() - start_time

            # Calculate metrics
            metrics = self._calculate_metrics(model, X_val, y_val, job.model_type)
            metrics["training_time_seconds"] = training_time

            return model, metrics

        except Exception as e:
            logger.error(f"Sklearn training failed: {e}")
            raise

    def save_model(self, model: Any, path: str) -> bool:
        """Save scikit-learn model"""
        try:
            import joblib

            Path(path).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, path)
            return True
        except Exception as e:
            logger.error(f"Failed to save sklearn model: {e}")
            return False

    def load_model(self, path: str) -> Any:
        """Load scikit-learn model"""
        try:
            import joblib

            return joblib.load(path)
        except Exception as e:
            logger.error(f"Failed to load sklearn model: {e}")
            raise

    def _get_model_class(self, job: TrainingJob):
        """Get model class based on job configuration"""
        model_name = job.training_config.get("model_name", "RandomForestClassifier")

        if job.model_type == ModelType.CLASSIFICATION:
            if model_name == "RandomForestClassifier":
                from sklearn.ensemble import RandomForestClassifier

                return RandomForestClassifier
            if model_name == "GradientBoostingClassifier":
                from sklearn.ensemble import GradientBoostingClassifier

                return GradientBoostingClassifier
            if model_name == "LogisticRegression":
                from sklearn.linear_model import LogisticRegression

                return LogisticRegression
            if model_name == "SVC":
                from sklearn.svm import SVC

                return SVC

        elif job.model_type == ModelType.REGRESSION:
            if model_name == "RandomForestRegressor":
                from sklearn.ensemble import RandomForestRegressor

                return RandomForestRegressor
            if model_name == "GradientBoostingRegressor":
                from sklearn.ensemble import GradientBoostingRegressor

                return GradientBoostingRegressor
            if model_name == "LinearRegression":
                from sklearn.linear_model import LinearRegression

                return LinearRegression
            if model_name == "SVR":
                from sklearn.svm import SVR

                return SVR

        elif job.model_type == ModelType.CLUSTERING:
            if model_name == "KMeans":
                from sklearn.cluster import KMeans

                return KMeans
            if model_name == "DBSCAN":
                from sklearn.cluster import DBSCAN

                return DBSCAN

        return None

    def _prepare_data(
        self,
        data: Any,
        job: TrainingJob,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training"""
        # This is a simplified implementation
        # In production, this would handle various data formats
        if isinstance(data, dict):
            X_train = np.array(data.get("X_train", []))
            y_train = np.array(data.get("y_train", []))
            X_val = np.array(data.get("X_val", []))
            y_val = np.array(data.get("y_val", []))
        else:
            # Assume data is a tuple/list
            X_train, y_train, X_val, y_val = data

        return X_train, y_train, X_val, y_val

    def _calculate_metrics(
        self,
        model: Any,
        X_val: np.ndarray,
        y_val: np.ndarray,
        model_type: ModelType,
    ) -> dict[str, float]:
        """Calculate model metrics"""
        metrics = {}

        try:
            if model_type in [ModelType.CLASSIFICATION]:
                y_pred = model.predict(X_val)
                metrics["accuracy"] = accuracy_score(y_val, y_pred)
                metrics["precision"] = precision_score(
                    y_val,
                    y_pred,
                    average="weighted",
                )
                metrics["recall"] = recall_score(y_val, y_pred, average="weighted")
                metrics["f1_score"] = f1_score(y_val, y_pred, average="weighted")

            elif model_type == ModelType.REGRESSION:
                y_pred = model.predict(X_val)
                from sklearn.metrics import (
                    mean_absolute_error,
                    mean_squared_error,
                    r2_score,
                )

                metrics["mse"] = mean_squared_error(y_val, y_pred)
                metrics["mae"] = mean_absolute_error(y_val, y_pred)
                metrics["r2_score"] = r2_score(y_val, y_pred)

            elif model_type == ModelType.CLUSTERING:
                y_pred = model.predict(X_val)
                from sklearn.metrics import silhouette_score

                if (
                    len(set(y_pred)) > 1
                ):  # Silhouette score requires at least 2 clusters
                    metrics["silhouette_score"] = silhouette_score(X_val, y_pred)
                else:
                    metrics["silhouette_score"] = 0.0

        except Exception as e:
            logger.warning(f"Failed to calculate some metrics: {e}")

        return metrics


class TensorFlowTrainer(ModelTrainer):
    """TensorFlow model trainer"""

    def __init__(self):
        self.supported_models = {
            ModelType.CLASSIFICATION: ["DenseClassifier", "CNNClassifier"],
            ModelType.REGRESSION: ["DenseRegressor", "CNNRegressor"],
            ModelType.NLP: ["TextClassifier", "TextRegressor"],
            ModelType.COMPUTER_VISION: ["ImageClassifier", "ObjectDetector"],
        }

    async def train_model(
        self,
        job: TrainingJob,
        data: Any,
    ) -> tuple[Any, dict[str, float]]:
        """Train TensorFlow model"""
        try:
            import tensorflow as tf

            # Create model
            model = self._create_model(job)

            # Prepare data
            train_dataset, val_dataset = self._prepare_data(data, job)

            # Configure training
            optimizer = tf.keras.optimizers.Adam(
                **job.hyperparameters.get("optimizer", {}),
            )
            model.compile(
                optimizer=optimizer,
                loss=job.training_config.get("loss", "sparse_categorical_crossentropy"),
                metrics=job.training_config.get("metrics", ["accuracy"]),
            )

            # Train model
            start_time = time.time()
            history = model.fit(
                train_dataset,
                validation_data=val_dataset,
                epochs=job.hyperparameters.get("epochs", 10),
                batch_size=job.hyperparameters.get("batch_size", 32),
                verbose=1,
            )
            training_time = time.time() - start_time

            # Calculate metrics
            metrics = self._extract_metrics(history)
            metrics["training_time_seconds"] = training_time

            return model, metrics

        except Exception as e:
            logger.error(f"TensorFlow training failed: {e}")
            raise

    def save_model(self, model: Any, path: str) -> bool:
        """Save TensorFlow model"""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            model.save(path)
            return True
        except Exception as e:
            logger.error(f"Failed to save TensorFlow model: {e}")
            return False

    def load_model(self, path: str) -> Any:
        """Load TensorFlow model"""
        try:
            import tensorflow as tf

            return tf.keras.models.load_model(path)
        except Exception as e:
            logger.error(f"Failed to load TensorFlow model: {e}")
            raise

    def _create_model(self, job: TrainingJob):
        """Create TensorFlow model based on job configuration"""
        import tensorflow as tf

        model_name = job.training_config.get("model_name", "DenseClassifier")

        if model_name == "DenseClassifier":
            model = tf.keras.Sequential(
                [
                    tf.keras.layers.Dense(
                        128,
                        activation="relu",
                        input_shape=(job.training_config.get("input_shape", [10])),
                    ),
                    tf.keras.layers.Dropout(0.2),
                    tf.keras.layers.Dense(64, activation="relu"),
                    tf.keras.layers.Dropout(0.2),
                    tf.keras.layers.Dense(
                        job.training_config.get("num_classes", 2),
                        activation="softmax",
                    ),
                ],
            )
        elif model_name == "CNNClassifier":
            model = tf.keras.Sequential(
                [
                    tf.keras.layers.Conv2D(
                        32,
                        (3, 3),
                        activation="relu",
                        input_shape=job.training_config.get("input_shape", [32, 32, 3]),
                    ),
                    tf.keras.layers.MaxPooling2D((2, 2)),
                    tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
                    tf.keras.layers.MaxPooling2D((2, 2)),
                    tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
                    tf.keras.layers.Flatten(),
                    tf.keras.layers.Dense(64, activation="relu"),
                    tf.keras.layers.Dense(
                        job.training_config.get("num_classes", 10),
                        activation="softmax",
                    ),
                ],
            )
        else:
            # Default dense classifier
            model = tf.keras.Sequential(
                [
                    tf.keras.layers.Dense(
                        128,
                        activation="relu",
                        input_shape=(job.training_config.get("input_shape", [10])),
                    ),
                    tf.keras.layers.Dense(64, activation="relu"),
                    tf.keras.layers.Dense(
                        job.training_config.get("num_classes", 2),
                        activation="softmax",
                    ),
                ],
            )

        return model

    def _prepare_data(self, data: Any, job: TrainingJob):
        """Prepare data for TensorFlow training"""
        import tensorflow as tf

        # This is a simplified implementation
        if isinstance(data, dict):
            X_train = tf.data.Dataset.from_tensor_slices(data.get("X_train", []))
            y_train = tf.data.Dataset.from_tensor_slices(data.get("y_train", []))
            train_dataset = tf.data.Dataset.zip((X_train, y_train)).batch(
                job.hyperparameters.get("batch_size", 32),
            )

            X_val = tf.data.Dataset.from_tensor_slices(data.get("X_val", []))
            y_val = tf.data.Dataset.from_tensor_slices(data.get("y_val", []))
            val_dataset = tf.data.Dataset.zip((X_val, y_val)).batch(
                job.hyperparameters.get("batch_size", 32),
            )
        else:
            # Assume data is already prepared
            train_dataset, val_dataset = data

        return train_dataset, val_dataset

    def _extract_metrics(self, history) -> dict[str, float]:
        """Extract metrics from training history"""
        metrics = {}

        try:
            # Get final epoch metrics
            if hasattr(history, "history"):
                for metric_name, values in history.history.items():
                    if values:
                        metrics[f"final_{metric_name}"] = float(values[-1])

                # Calculate improvement
                for metric_name, values in history.history.items():
                    if len(values) > 1:
                        improvement = values[-1] - values[0]
                        metrics[f"{metric_name}_improvement"] = float(improvement)

        except Exception as e:
            logger.warning(f"Failed to extract some metrics: {e}")

        return metrics


class TrainingOrchestrator:
    """Training pipeline orchestrator with MLflow integration and Kubernetes support.
    Manages training jobs, experiments, and model lifecycle.
    """

    def __init__(self, config: TrainingPipelineConfig = None):
        self.config = config or TrainingPipelineConfig()

        # Job management
        self.training_jobs: dict[str, TrainingJob] = {}
        self.training_results: dict[str, TrainingResult] = {}
        self.active_jobs: dict[str, asyncio.Task] = {}

        # Trainers
        self.trainers: dict[str, ModelTrainer] = {
            "sklearn": SklearnTrainer(),
            "tensorflow": TensorFlowTrainer(),
        }

        # MLflow integration
        self.mlflow_client = None
        self.experiment_id = None
        self._init_mlflow()

        # Kubernetes integration
        self.k8s_client = None
        self._init_kubernetes()

        # Statistics
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "active_jobs": 0,
            "average_training_time": 0.0,
        }

        logger.info("Initialized Training Orchestrator")

    def _init_mlflow(self):
        """Initialize MLflow client"""
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available, skipping MLflow initialization")
            self.mlflow_client = None
            return
            
        try:
            mlflow.set_tracking_uri(self.config.mlflow_tracking_uri)

            # Create or get experiment
            try:
                self.experiment_id = mlflow.create_experiment(
                    name=self.config.mlflow_experiment_name,
                    artifact_location=self.config.artifact_storage_path,
                )
            except mlflow.exceptions.MlflowException:
                # Experiment already exists
                experiment = mlflow.get_experiment_by_name(
                    self.config.mlflow_experiment_name,
                )
                self.experiment_id = experiment.experiment_id

            self.mlflow_client = mlflow.tracking.MlflowClient()
            logger.info(f"MLflow initialized with experiment ID: {self.experiment_id}")

        except Exception as e:
            logger.warning(f"MLflow initialization failed: {e}")
            self.mlflow_client = None

    def _init_kubernetes(self):
        """Initialize Kubernetes client"""
        try:
            if self.config.kubernetes_config_path:
                config.load_kube_config(config_file=self.config.kubernetes_config_path)
            else:
                config.load_incluster_config()

            self.k8s_client = client.CoreV1Api()
            logger.info("Kubernetes client initialized")

        except Exception as e:
            logger.warning(f"Kubernetes initialization failed: {e}")
            self.k8s_client = None

    async def submit_training_job(self, job: TrainingJob) -> str:
        """Submit a training job"""
        try:
            # Validate job
            if not self._validate_job(job):
                raise ValueError("Invalid training job")

            # Store job
            self.training_jobs[job.job_id] = job
            self.stats["total_jobs"] += 1

            # Start training task
            training_task = asyncio.create_task(self._execute_training_job(job))
            self.active_jobs[job.job_id] = training_task

            logger.info(f"Submitted training job {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Failed to submit training job: {e}")
            raise

    async def _execute_training_job(self, job: TrainingJob):
        """Execute a training job"""
        start_time = time.time()

        try:
            # Update job status
            self._update_job_status(job.job_id, TrainingStatus.RUNNING)

            # Load training data
            data = await self._load_training_data(job)

            # Select trainer
            trainer = self._select_trainer(job)

            # Start MLflow run
            mlflow_run_id = None
            if self.config.enable_mlflow_logging and self.mlflow_client and MLFLOW_AVAILABLE:
                with mlflow.start_run(experiment_id=self.experiment_id):
                    mlflow_run_id = mlflow.active_run().info.run_id

                    # Log parameters
                    mlflow.log_params(job.hyperparameters)
                    mlflow.log_params(job.training_config)
                    mlflow.set_tag("model_name", job.model_name)
                    mlflow.set_tag("model_type", job.model_type.value)
                    mlflow.set_tag("trigger", job.trigger.value)

            # Train model
            model, metrics = await trainer.train_model(job, data)

            # Save model
            model_version = f"{job.model_name}_v{int(time.time())}"
            model_path = f"{self.config.model_storage_path}/{model_version}"

            if trainer.save_model(model, model_path):
                # Create training result
                result = TrainingResult(
                    job_id=job.job_id,
                    model_name=job.model_name,
                    status=TrainingStatus.COMPLETED,
                    model_path=model_path,
                    model_version=model_version,
                    metrics=metrics,
                    training_time_seconds=time.time() - start_time,
                    data_size=len(data) if hasattr(data, "__len__") else 0,
                    features_count=job.training_config.get("features_count", 0),
                    completed_at=datetime.now(UTC),
                    mlflow_run_id=mlflow_run_id,
                )

                # Store result
                self.training_results[job.job_id] = result

                # Log to MLflow
                if self.config.enable_mlflow_logging and self.mlflow_client and MLFLOW_AVAILABLE:
                    with mlflow.start_run(run_id=mlflow_run_id):
                        mlflow.log_metrics(metrics)
                        mlflow.log_artifact(model_path)
                        mlflow.set_tag("status", "completed")

                # Update statistics
                self.stats["completed_jobs"] += 1
                self._update_average_training_time(result.training_time_seconds)

                logger.info(f"Training job {job.job_id} completed successfully")

            else:
                raise RuntimeError("Failed to save trained model")

        except Exception as e:
            # Create failed result
            result = TrainingResult(
                job_id=job.job_id,
                model_name=job.model_name,
                status=TrainingStatus.FAILED,
                training_time_seconds=time.time() - start_time,
                completed_at=datetime.now(UTC),
                error_message=str(e),
            )

            self.training_results[job.job_id] = result
            self.stats["failed_jobs"] += 1

            # Log to MLflow
            if self.config.enable_mlflow_logging and self.mlflow_client and MLFLOW_AVAILABLE:
                with mlflow.start_run(run_id=mlflow_run_id):
                    mlflow.set_tag("status", "failed")
                    mlflow.log_param("error_message", str(e))

            logger.error(f"Training job {job.job_id} failed: {e}")

        finally:
            # Clean up
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            self.stats["active_jobs"] = len(self.active_jobs)

    def _validate_job(self, job: TrainingJob) -> bool:
        """Validate training job"""
        try:
            # Check required fields
            if not job.job_id or not job.model_name or not job.training_data_path:
                return False

            # Check model type
            if job.model_type not in ModelType:
                return False

            # Check data path exists
            if not Path(job.training_data_path).exists():
                logger.warning(
                    f"Training data path does not exist: {job.training_data_path}",
                )
                # Don't fail validation for missing data path in development

            return True

        except Exception as e:
            logger.error(f"Job validation error: {e}")
            return False

    async def _load_training_data(self, job: TrainingJob) -> Any:
        """Load training data"""
        try:
            # This is a simplified implementation
            # In production, this would handle various data formats
            data_path = Path(job.training_data_path)

            if data_path.suffix == ".json":
                with open(data_path) as f:
                    return json.load(f)
            elif data_path.suffix == ".pkl":
                with open(data_path, "rb") as f:
                    return pickle.load(f)
            elif data_path.suffix == ".csv":
                import pandas as pd

                return pd.read_csv(data_path)
            else:
                # Default: assume it's a pickle file
                with open(data_path, "rb") as f:
                    return pickle.load(f)

        except Exception as e:
            logger.error(f"Failed to load training data: {e}")
            raise

    def _select_trainer(self, job: TrainingJob) -> ModelTrainer:
        """Select appropriate trainer based on job configuration"""
        framework = job.training_config.get("framework", "sklearn")

        if framework in self.trainers:
            return self.trainers[framework]
        # Default to sklearn trainer
        return self.trainers["sklearn"]

    def _update_job_status(self, job_id: str, status: TrainingStatus):
        """Update job status"""
        # This would update the job status in a database in production
        logger.info(f"Job {job_id} status: {status.value}")

    def _update_average_training_time(self, training_time: float):
        """Update average training time"""
        total_completed = self.stats["completed_jobs"]
        if total_completed > 0:
            current_avg = self.stats["average_training_time"]
            self.stats["average_training_time"] = (
                current_avg * (total_completed - 1) + training_time
            ) / total_completed

    async def cancel_training_job(self, job_id: str) -> bool:
        """Cancel a training job"""
        try:
            if job_id in self.active_jobs:
                task = self.active_jobs[job_id]
                task.cancel()

                # Create cancelled result
                result = TrainingResult(
                    job_id=job_id,
                    model_name=self.training_jobs[job_id].model_name,
                    status=TrainingStatus.CANCELLED,
                    completed_at=datetime.now(UTC),
                )

                self.training_results[job_id] = result
                self.stats["cancelled_jobs"] += 1

                logger.info(f"Cancelled training job {job_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to cancel training job {job_id}: {e}")
            return False

    def get_job_status(self, job_id: str) -> TrainingResult | None:
        """Get training job status"""
        return self.training_results.get(job_id)

    def list_jobs(
        self,
        status: TrainingStatus | None = None,
    ) -> list[TrainingResult]:
        """List training jobs"""
        results = list(self.training_results.values())

        if status:
            results = [r for r in results if r.status == status]

        return sorted(
            results,
            key=lambda x: x.completed_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )

    def get_training_statistics(self) -> dict[str, Any]:
        """Get training statistics"""
        stats = self.stats.copy()
        stats["total_jobs"] = len(self.training_jobs)
        stats["active_jobs"] = len(self.active_jobs)

        if stats["total_jobs"] > 0:
            stats["success_rate"] = stats["completed_jobs"] / stats["total_jobs"]
            stats["failure_rate"] = stats["failed_jobs"] / stats["total_jobs"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0

        return stats


# Production-ready factory functions
def create_production_training_orchestrator() -> TrainingOrchestrator:
    """Create production-ready training orchestrator"""
    config = TrainingPipelineConfig(
        mlflow_tracking_uri="http://mlflow-service:5000",
        mlflow_experiment_name="pake-production-ml",
        enable_mlflow_logging=True,
        kubernetes_namespace="pake-ml",
        enable_kubeflow=True,
        max_concurrent_jobs=10,
        default_training_timeout_hours=48,
        enable_hyperparameter_tuning=True,
        max_tuning_trials=100,
        enable_model_validation=True,
        validation_threshold=0.8,
        enable_cross_validation=True,
        cv_folds=10,
        model_storage_path="/models/production",
        data_storage_path="/data/production",
        artifact_storage_path="/artifacts/production",
        enable_training_monitoring=True,
        monitoring_interval_seconds=30,
        enable_alerting=True,
    )

    return TrainingOrchestrator(config)


if __name__ == "__main__":
    # Example usage
    async def main():
        orchestrator = TrainingOrchestrator()

        # Create training job
        job = TrainingJob(
            job_id="test_job_001",
            model_name="test_classifier",
            model_type=ModelType.CLASSIFICATION,
            training_data_path="/data/training_data.pkl",
            hyperparameters={"n_estimators": 100, "max_depth": 10},
            training_config={
                "framework": "sklearn",
                "model_name": "RandomForestClassifier",
                "num_classes": 2,
                "features_count": 10,
            },
            trigger=TrainingTrigger.MANUAL,
        )

        # Submit job
        job_id = await orchestrator.submit_training_job(job)
        print(f"Submitted training job: {job_id}")

        # Wait for completion
        while job_id in orchestrator.active_jobs:
            await asyncio.sleep(5)
            status = orchestrator.get_job_status(job_id)
            if status:
                print(f"Job status: {status.status.value}")

        # Get final result
        result = orchestrator.get_job_status(job_id)
        if result:
            print(f"Training completed: {result.status.value}")
            print(f"Metrics: {result.metrics}")
            print(f"Model path: {result.model_path}")

        # Get statistics
        stats = orchestrator.get_training_statistics()
        print(f"Training statistics: {stats}")

    asyncio.run(main())
