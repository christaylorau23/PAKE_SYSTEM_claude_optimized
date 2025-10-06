#!/usr/bin/env python3
import aiohttp
"""PAKE System - Model Serving Service
Phase 9B: Advanced AI/ML Pipeline Integration.

Provides enterprise-grade model serving infrastructure with Kubernetes integration,
load balancing, health checks, and high-performance inference capabilities.
"""

from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List

import numpy as np

from kubernetes import client, config

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""

    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    UNLOADING = "unloading"
    UNAVAILABLE = "unavailable"


class ModelFramework(Enum):
    """Supported ML frameworks."""

    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    ONNX = "onnx"
    SKLEARN = "sklearn"
    CUSTOM = "custom"


class InferenceType(Enum):
    """Types of inference requests."""

    REAL_TIME = "real_time"
    BATCH = "batch"
    STREAMING = "streaming"


@dataclass(frozen=True)
class ModelMetadata:
    """Immutable model metadata."""

    model_id: str
    model_name: str
    version: str
    framework: ModelFramework
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    model_size_mb: float
    created_at: datetime
    last_updated: datetime
    performance_metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "version": self.version,
            "framework": self.framework.value,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "model_size_mb": self.model_size_mb,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "performance_metrics": self.performance_metrics,
        }


@dataclass(frozen=True)
class InferenceRequest:
    """Immutable inference request."""

    request_id: str
    model_id: str
    input_data: Dict[str, Any]
    inference_type: InferenceType = InferenceType.REAL_TIME
    priority: int = 0  # Higher number = higher priority
    timeout_seconds: float = 30.0
    request_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "input_data": self.input_data,
            "inference_type": self.inference_type.value,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "request_timestamp": self.request_timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class InferenceResponse:
    """Immutable inference response."""

    request_id: str
    model_id: str
    predictions: Dict[str, Any]
    confidence_scores: dict[str, float] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    model_version: str = ""
    response_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "predictions": self.predictions,
            "confidence_scores": self.confidence_scores,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version,
            "response_timestamp": self.response_timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ModelHealth:
    """Immutable model health status."""

    model_id: str
    status: ModelStatus
    health_score: float  # 0.0 to 1.0
    last_inference_time: datetime | None = None
    error_count: int = 0
    success_count: int = 0
    average_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_health_check: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_id": self.model_id,
            "status": self.status.value,
            "health_score": self.health_score,
            "last_inference_time": (
                self.last_inference_time.isoformat()
                if self.last_inference_time
                else None
            ),
            "error_count": self.error_count,
            "success_count": self.success_count,
            "average_latency_ms": self.average_latency_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "last_health_check": self.last_health_check.isoformat(),
        }


@dataclass
class ModelServingConfig:
    """Configuration for model serving service."""

    # Model management
    max_models_per_node: int = 10
    model_cache_size_mb: int = 2048
    model_load_timeout_seconds: int = 300
    model_unload_timeout_seconds: int = 60

    # Inference settings
    max_concurrent_inferences: int = 100
    inference_timeout_seconds: float = 30.0
    batch_size: int = 32
    enable_batching: bool = True

    # Performance settings
    enable_model_warmup: bool = True
    warmup_requests: int = 10
    health_check_interval_seconds: int = 30
    performance_monitoring: bool = True

    # Kubernetes settings
    kubernetes_namespace: str = "pake-ml"
    kubernetes_config_path: str | None = None
    enable_auto_scaling: bool = True
    min_replicas: int = 1
    max_replicas: int = 10

    # Caching settings
    enable_prediction_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size: int = 10000


class ModelInterface(ABC):
    """Abstract interface for ML models."""

    @abstractmethod
    async def load_model(self, model_path: str) -> bool:
        """Load model from path."""

    @abstractmethod
    async def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run inference on input data."""

    @abstractmethod
    async def unload_model(self) -> bool:
        """Unload model from memory."""

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""


class TensorFlowModel(ModelInterface):
    """TensorFlow model implementation."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.model = None
        self.model_path = None
        self.loaded = False

    async def load_model(self, model_path: str) -> bool:
        """Load TensorFlow model."""
        try:
            import tensorflow as tf

            self.model_path = model_path
            self.model = tf.keras.models.load_model(model_path)
            self.loaded = True

            logger.info("Loaded TensorFlow model %s from %s", self.model_id, model_path)
            return True

        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Failed to load TensorFlow model %s: %s", self.model_id, e)
            return False

    async def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run TensorFlow inference."""
        if not self.loaded or not self.model:
            msg = f"Model {self.model_id} not loaded"
            raise RuntimeError(msg)

        try:
            # Convert input data to appropriate format
            inputs = self._prepare_inputs(input_data)

            # Run inference
            predictions = self.model.predict(inputs)

            # Convert predictions to dictionary
            return self._format_predictions(predictions)

        except (ValueError, RuntimeError) as e:
            logger.error("TensorFlow inference failed for %s: %s", self.model_id, e)
            raise

    async def unload_model(self) -> bool:
        """Unload TensorFlow model."""
        try:
            self.model = None
            self.loaded = False

            logger.info("Unloaded TensorFlow model %s", self.model_id)
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to unload TensorFlow model %s: %s", self.model_id, e)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get TensorFlow model information."""
        if not self.model:
            return {"status": "not_loaded"}

        return {
            "framework": "tensorflow",
            "input_shape": [
                layer.input_shape
                for layer in self.model.layers
                if hasattr(layer, "input_shape")
            ],
            "output_shape": [
                layer.output_shape
                for layer in self.model.layers
                if hasattr(layer, "output_shape")
            ],
            "total_params": self.model.count_params(),
            "loaded": self.loaded,
        }

    def _prepare_inputs(self, input_data: Dict[str, Any]) -> np.ndarray:
        """Prepare input data for TensorFlow model."""
        # Convert input data to numpy arrays
        # This is a simplified implementation
        if isinstance(input_data, dict):
            # Assume single input for now
            key = list(input_data.keys())[0]
            return np.array(input_data[key])
        return np.array(input_data)

    def _format_predictions(self, predictions: np.ndarray) -> Dict[str, Any]:
        """Format TensorFlow predictions."""
        return {"predictions": predictions.tolist(), "shape": predictions.shape}


class ONNXModel(ModelInterface):
    """ONNX model implementation."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.model = None
        self.model_path = None
        self.loaded = False

    async def load_model(self, model_path: str) -> bool:
        """Load ONNX model."""
        try:
            import onnxruntime as ort

            self.model_path = model_path
            self.model = ort.InferenceSession(model_path)
            self.loaded = True

            logger.info("Loaded ONNX model %s from %s", self.model_id, model_path)
            return True

        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Failed to load ONNX model %s: %s", self.model_id, e)
            return False

    async def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run ONNX inference."""
        if not self.loaded or not self.model:
            msg = f"Model {self.model_id} not loaded"
            raise RuntimeError(msg)

        try:
            # Prepare inputs for ONNX
            inputs = self._prepare_inputs(input_data)

            # Run inference
            outputs = self.model.run(None, inputs)

            # Format outputs
            return self._format_predictions(outputs)

        except (ValueError, RuntimeError) as e:
            logger.error("ONNX inference failed for %s: %s", self.model_id, e)
            raise

    async def unload_model(self) -> bool:
        """Unload ONNX model."""
        try:
            self.model = None
            self.loaded = False

            logger.info("Unloaded ONNX model %s", self.model_id)
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to unload ONNX model %s: %s", self.model_id, e)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get ONNX model information."""
        if not self.model:
            return {"status": "not_loaded"}

        input_info = dict(self.model.get_inputs())
        output_info = dict(self.model.get_outputs())

        return {
            "framework": "onnx",
            "input_info": input_info,
            "output_info": output_info,
            "loaded": self.loaded,
        }

    def _prepare_inputs(self, input_data: Dict[str, Any]) -> dict[str, np.ndarray]:
        """Prepare input data for ONNX model."""
        inputs = {}
        for name, data in input_data.items():
            inputs[name] = np.array(data)
        return inputs

    def _format_predictions(self, outputs: list[np.ndarray]) -> Dict[str, Any]:
        """Format ONNX predictions."""
        result = {}
        for i, output in enumerate(outputs):
            result[f"output_{i}"] = output.tolist()
        return result


class ModelRegistry:
    """Model registry for managing model metadata and versions."""

    def __init__(self) -> None:
        self.models: dict[str, ModelMetadata] = {}
        self.model_versions: dict[str, List[str]] = {}
        self.model_paths: dict[str, str] = {}

    def register_model(self, metadata: ModelMetadata, model_path: str) -> bool:
        """Register a new model."""
        try:
            self.models[metadata.model_id] = metadata
            self.model_paths[metadata.model_id] = model_path

            # Track versions
            if metadata.model_name not in self.model_versions:
                self.model_versions[metadata.model_name] = []
            self.model_versions[metadata.model_name].append(metadata.version)

            logger.info(
                "Registered model %s version %s",
                metadata.model_id,
                metadata.version,
            )
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to register model %s: %s", metadata.model_id, e)
            return False

    def get_model(self, model_id: str) -> ModelMetadata | None:
        """Get model metadata by ID."""
        return self.models.get(model_id)

    def get_model_path(self, model_id: str) -> str | None:
        """Get model file path by ID."""
        return self.model_paths.get(model_id)

    def list_models(self) -> list[ModelMetadata]:
        """List all registered models."""
        return list(self.models.values())

    def get_model_versions(self, model_name: str) -> List[str]:
        """Get all versions of a model."""
        return self.model_versions.get(model_name, [])

    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model."""
        try:
            if model_id in self.models:
                metadata = self.models[model_id]
                del self.models[model_id]
                del self.model_paths[model_id]

                # Remove from version tracking
                if metadata.model_name in self.model_versions:
                    versions = self.model_versions[metadata.model_name]
                    if metadata.version in versions:
                        versions.remove(metadata.version)

                logger.info("Unregistered model %s", model_id)
                return True

            return False

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to unregister model %s: %s", model_id, e)
            return False


class ModelServingService:
    """Enterprise-grade model serving service with Kubernetes integration.
    Provides high-performance inference, load balancing, and health monitoring.
    """

    def __init__(self, config: ModelServingConfig | None = None) -> None:
        self.config = config or ModelServingConfig()

        # Model management
        self.registry = ModelRegistry()
        self.loaded_models: dict[str, ModelInterface] = {}
        self.model_health: dict[str, ModelHealth] = {}

        # Inference management
        self.inference_executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_inferences,
        )
        self.prediction_cache: dict[str, InferenceResponse] = {}

        # Kubernetes integration
        self.k8s_client = None
        self.k8s_apps_client = None
        self._init_kubernetes()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "average_latency_ms": 0.0,
            "models_loaded": 0,
            "models_unloaded": 0,
        }

        # Health check task
        self.health_check_task = None

        logger.info("Initialized Model Serving Service")

    def _init_kubernetes(self) -> None:
        """Initialize Kubernetes client."""
        try:
            if self.config.kubernetes_config_path:
                config.load_kube_config(config_file=self.config.kubernetes_config_path)
            else:
                config.load_incluster_config()

            self.k8s_client = client.CoreV1Api()
            self.k8s_apps_client = client.AppsV1Api()

            logger.info("Kubernetes client initialized")

        except (ValueError, RuntimeError) as e:
            logger.warning("Kubernetes initialization failed: %s", e)
            self.k8s_client = None
            self.k8s_apps_client = None

    async def start(self) -> None:
        """Start the model serving service."""
        try:
            # Start health check task
            self.health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info("Model Serving Service started")

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to start Model Serving Service: %s", e)
            raise

    async def stop(self) -> None:
        """Stop the model serving service."""
        try:
            # Cancel health check task
            if self.health_check_task:
                self.health_check_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.health_check_task

            # Unload all models
            for model_id in list(self.loaded_models.keys()):
                await self.unload_model(model_id)

            # Shutdown executor
            self.inference_executor.shutdown(wait=True)

            logger.info("Model Serving Service stopped")

        except (ValueError, RuntimeError) as e:
            logger.error("Error stopping Model Serving Service: %s", e)

    async def register_model(
        self,
        model_path: str,
        model_name: str,
        version: str,
        framework: ModelFramework,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
    ) -> str:
        """Register a new model."""
        try:
            # Generate model ID
            model_id = f"{model_name}_{version}_{int(time.time())}"

            # Get model size
            model_size_mb = Path(model_path).stat().st_size / (1024 * 1024)

            # Create metadata
            metadata = ModelMetadata(
                model_id=model_id,
                model_name=model_name,
                version=version,
                framework=framework,
                input_schema=input_schema,
                output_schema=output_schema,
                model_size_mb=model_size_mb,
                created_at=datetime.now(UTC),
                last_updated=datetime.now(UTC),
            )

            # Register in registry
            if self.registry.register_model(metadata, model_path):
                logger.info("Registered model %s", model_id)
                return model_id
            msg = "Failed to register model in registry"
            raise RuntimeError(msg)

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to register model: %s", e)
            raise

    async def load_model(self, model_id: str) -> bool:
        """Load a model for serving."""
        try:
            if model_id in self.loaded_models:
                logger.warning("Model %s already loaded", model_id)
                return True

            # Get model metadata and path
            metadata = self.registry.get_model(model_id)
            model_path = self.registry.get_model_path(model_id)

            if not metadata or not model_path:
                msg = f"Model {model_id} not found in registry"
                raise ValueError(msg)

            # Create model instance based on framework
            if metadata.framework == ModelFramework.TENSORFLOW:
                model = TensorFlowModel(model_id)
            elif metadata.framework == ModelFramework.ONNX:
                model = ONNXModel(model_id)
            else:
                msg = f"Unsupported framework: {metadata.framework}"
                raise ValueError(msg)

            # Load model
            if await model.load_model(model_path):
                self.loaded_models[model_id] = model

                # Initialize health status
                self.model_health[model_id] = ModelHealth(
                    model_id=model_id,
                    status=ModelStatus.READY,
                    health_score=1.0,
                )

                # Model warmup if enabled
                if self.config.enable_model_warmup:
                    await self._warmup_model(model_id)

                self.stats["models_loaded"] += 1
                logger.info("Loaded model %s", model_id)
                return True
            msg = f"Failed to load model {model_id}"
            raise RuntimeError(msg)

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to load model %s: %s", model_id, e)
            return False

    async def unload_model(self, model_id: str) -> bool:
        """Unload a model from serving."""
        try:
            if model_id not in self.loaded_models:
                logger.warning("Model %s not loaded", model_id)
                return True

            model = self.loaded_models[model_id]

            # Unload model
            if await model.unload_model():
                del self.loaded_models[model_id]

                # Update health status
                if model_id in self.model_health:
                    health = self.model_health[model_id]
                    self.model_health[model_id] = ModelHealth(
                        model_id=model_id,
                        status=ModelStatus.UNAVAILABLE,
                        health_score=0.0,
                        error_count=health.error_count,
                        success_count=health.success_count,
                        average_latency_ms=health.average_latency_ms,
                        memory_usage_mb=health.memory_usage_mb,
                        cpu_usage_percent=health.cpu_usage_percent,
                    )

                self.stats["models_unloaded"] += 1
                logger.info("Unloaded model %s", model_id)
                return True
            msg = f"Failed to unload model {model_id}"
            raise RuntimeError(msg)

        except (ValueError, RuntimeError) as e:
            logger.error("Failed to unload model %s: %s", model_id, e)
            return False

    async def predict(self, request: InferenceRequest) -> InferenceResponse:
        """Run inference on a model."""
        start_time = time.time()

        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if (
                self.config.enable_prediction_caching
                and cache_key in self.prediction_cache
            ):
                cached_response = self.prediction_cache[cache_key]
                self.stats["cache_hits"] += 1
                return cached_response

            # Validate request
            if request.model_id not in self.loaded_models:
                msg = f"Model {request.model_id} not loaded"
                raise ValueError(msg)

            # Get model
            model = self.loaded_models[request.model_id]

            # Run inference
            predictions = await model.predict(request.input_data)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Create response
            response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                predictions=predictions,
                processing_time_ms=processing_time,
                model_version=self.registry.get_model(request.model_id).version,
            )

            # Cache response
            if self.config.enable_prediction_caching:
                self.prediction_cache[cache_key] = response
                # Simple cache management
                if len(self.prediction_cache) > self.config.max_cache_size:
                    oldest_keys = list(self.prediction_cache.keys())[:1000]
                    for old_key in oldest_keys:
                        del self.prediction_cache[old_key]

            # Update statistics
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1

            # Update model health
            await self._update_model_health(request.model_id, True, processing_time)

            return response

        except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
            # Update statistics
            self.stats["total_requests"] += 1
            self.stats["failed_requests"] += 1

            # Update model health
            await self._update_model_health(request.model_id, False, 0.0)

            logger.error("Inference failed for request %s: %s", request.request_id, e)
            raise

    async def _warmup_model(self, model_id: str) -> None:
        """Warm up model with sample requests."""
        try:
            metadata = self.registry.get_model(model_id)
            if not metadata:
                return

            # Create sample input based on schema
            sample_input = self._create_sample_input(metadata.input_schema)

            # Run warmup requests
            for i in range(self.config.warmup_requests):
                request = InferenceRequest(
                    request_id=f"warmup_{i}",
                    model_id=model_id,
                    input_data=sample_input,
                )

                try:
                    await self.predict(request)
                except (ValueError, RuntimeError) as e:
                    logger.warning("Warmup request %s failed: %s", i, e)

            logger.info("Warmed up model %s", model_id)

        except (ValueError, RuntimeError) as e:
            logger.error("Model warmup failed for %s: %s", model_id, e)

    def _create_sample_input(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create sample input based on schema."""
        sample_input = {}

        for field, schema in input_schema.items():
            if schema.get("type") == "array":
                shape = schema.get("shape", [1])
                sample_input[field] = np.random.random(shape).tolist()
            elif schema.get("type") == "string":
                sample_input[field] = "sample_text"
            else:
                sample_input[field] = 0.0

        return sample_input

    def _generate_cache_key(self, request: InferenceRequest) -> str:
        """Generate cache key for request."""
        request_data = {"model_id": request.model_id, "input_data": request.input_data}
        request_str = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()[:16]

    async def _update_model_health(self, model_id: str, success: bool, latency_ms: float) -> None:
        """Update model health metrics."""
        if model_id not in self.model_health:
            return

        health = self.model_health[model_id]

        if success:
            new_success_count = health.success_count + 1
            new_error_count = health.error_count
            new_latency = (
                health.average_latency_ms * health.success_count + latency_ms
            ) / new_success_count
        else:
            new_success_count = health.success_count
            new_error_count = health.error_count + 1
            new_latency = health.average_latency_ms

        # Calculate health score
        total_requests = new_success_count + new_error_count
        health_score = new_success_count / total_requests if total_requests > 0 else 0.0

        # Update health
        self.model_health[model_id] = ModelHealth(
            model_id=model_id,
            status=ModelStatus.READY if health_score > 0.8 else ModelStatus.ERROR,
            health_score=health_score,
            last_inference_time=(
                datetime.now(UTC) if success else health.last_inference_time
            ),
            error_count=new_error_count,
            success_count=new_success_count,
            average_latency_ms=new_latency,
            memory_usage_mb=health.memory_usage_mb,
            cpu_usage_percent=health.cpu_usage_percent,
        )

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except (ValueError, RuntimeError) as e:
                logger.error("Health check loop error: %s", e)

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all loaded models."""
        for model_id in list(self.loaded_models.keys()):
            try:
                # Simple health check - try a minimal prediction
                metadata = self.registry.get_model(model_id)
                if metadata:
                    sample_input = self._create_sample_input(metadata.input_schema)
                    request = InferenceRequest(
                        request_id=f"health_check_{int(time.time())}",
                        model_id=model_id,
                        input_data=sample_input,
                    )

                    await self.predict(request)

            except (ValueError, RuntimeError) as e:
                logger.warning("Health check failed for model %s: %s", model_id, e)

    def get_model_status(self, model_id: str) -> ModelHealth | None:
        """Get model health status."""
        return self.model_health.get(model_id)

    def list_loaded_models(self) -> List[str]:
        """List all loaded model IDs."""
        return list(self.loaded_models.keys())

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        stats = self.stats.copy()
        stats["loaded_models_count"] = len(self.loaded_models)
        stats["registered_models_count"] = len(self.registry.models)
        stats["cache_size"] = len(self.prediction_cache)

        if stats["total_requests"] > 0:
            stats["success_rate"] = (
                stats["successful_requests"] / stats["total_requests"]
            )
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["cache_hit_rate"] = 0.0

        return stats


# Production-ready factory functions
async def create_production_model_serving_service() -> ModelServingService:
    """Create production-ready model serving service."""
    config = ModelServingConfig(
        max_models_per_node=20,
        model_cache_size_mb=4096,
        model_load_timeout_seconds=600,
        max_concurrent_inferences=200,
        inference_timeout_seconds=60.0,
        batch_size=64,
        enable_batching=True,
        enable_model_warmup=True,
        warmup_requests=20,
        health_check_interval_seconds=15,
        performance_monitoring=True,
        kubernetes_namespace="pake-ml",
        enable_auto_scaling=True,
        min_replicas=2,
        max_replicas=20,
        enable_prediction_caching=True,
        cache_ttl_seconds=7200,
        max_cache_size=50000,
    )

    service = ModelServingService(config)
    await service.start()

    return service


if __name__ == "__main__":
    # Example usage
    async def main() -> None:
        service = ModelServingService()
        await service.start()

        try:
            # Register a model (example)
            model_id = await service.register_model(
                model_path="/path/to/model",
                model_name="test_model",
                version="1.0",
                framework=ModelFramework.TENSORFLOW,
                input_schema={"input": {"type": "array", "shape": [1, 10]}},
                output_schema={"output": {"type": "array", "shape": [1, 2]}},
            )

            # Load model
            await service.load_model(model_id)

            # Run inference
            request = InferenceRequest(
                request_id="test_request",
                model_id=model_id,
                input_data={"input": [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]},
            )

            response = await service.predict(request)
            print(f"Prediction: {response.predictions}")
            print(f"Processing time: {response.processing_time_ms}ms")

            # Get statistics
            stats = service.get_service_statistics()
            print(f"Service statistics: {stats}")

        finally:
            await service.stop()

    asyncio.run(main())