#!/usr/bin/env python3
"""PAKE System - Prediction Service
Phase 9B: Advanced AI/ML Pipeline Integration

Provides high-performance prediction services with model ensemble capabilities,
batch processing, streaming predictions, and comprehensive result management.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class PredictionType(Enum):
    """Types of predictions"""

    REAL_TIME = "real_time"
    BATCH = "batch"
    STREAMING = "streaming"
    SCHEDULED = "scheduled"


class PredictionStatus(Enum):
    """Prediction request status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnsembleMethod(Enum):
    """Ensemble prediction methods"""

    VOTING = "voting"
    AVERAGING = "averaging"
    WEIGHTED_AVERAGING = "weighted_averaging"
    STACKING = "stacking"
    BAGGING = "bagging"


@dataclass(frozen=True)
class PredictionRequest:
    """Immutable prediction request"""

    request_id: str
    model_ids: list[str]
    input_data: dict[str, Any]
    prediction_type: PredictionType = PredictionType.REAL_TIME
    ensemble_method: EnsembleMethod | None = None
    ensemble_weights: list[float] | None = None
    priority: int = 0
    timeout_seconds: float = 30.0
    request_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "request_id": self.request_id,
            "model_ids": self.model_ids,
            "input_data": self.input_data,
            "prediction_type": self.prediction_type.value,
            "ensemble_method": (
                self.ensemble_method.value if self.ensemble_method else None
            ),
            "ensemble_weights": self.ensemble_weights,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "request_timestamp": self.request_timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PredictionResult:
    """Immutable prediction result"""

    request_id: str
    model_ids: list[str]
    predictions: dict[str, Any]
    ensemble_prediction: dict[str, Any] | None = None
    confidence_scores: dict[str, float] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    status: PredictionStatus = PredictionStatus.COMPLETED
    error_message: str | None = None
    response_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "request_id": self.request_id,
            "model_ids": self.model_ids,
            "predictions": self.predictions,
            "ensemble_prediction": self.ensemble_prediction,
            "confidence_scores": self.confidence_scores,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status.value,
            "error_message": self.error_message,
            "response_timestamp": self.response_timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class BatchPredictionRequest:
    """Immutable batch prediction request"""

    batch_id: str
    model_ids: list[str]
    input_data_list: list[dict[str, Any]]
    ensemble_method: EnsembleMethod | None = None
    ensemble_weights: list[float] | None = None
    batch_size: int = 100
    priority: int = 0
    timeout_seconds: float = 300.0
    request_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "batch_id": self.batch_id,
            "model_ids": self.model_ids,
            "input_data_list": self.input_data_list,
            "ensemble_method": (
                self.ensemble_method.value if self.ensemble_method else None
            ),
            "ensemble_weights": self.ensemble_weights,
            "batch_size": self.batch_size,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "request_timestamp": self.request_timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class BatchPredictionResult:
    """Immutable batch prediction result"""

    batch_id: str
    model_ids: list[str]
    results: list[PredictionResult]
    total_processing_time_ms: float = 0.0
    successful_predictions: int = 0
    failed_predictions: int = 0
    status: PredictionStatus = PredictionStatus.COMPLETED
    error_message: str | None = None
    completed_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "batch_id": self.batch_id,
            "model_ids": self.model_ids,
            "results": [r.to_dict() for r in self.results],
            "total_processing_time_ms": self.total_processing_time_ms,
            "successful_predictions": self.successful_predictions,
            "failed_predictions": self.failed_predictions,
            "status": self.status.value,
            "error_message": self.error_message,
            "completed_timestamp": self.completed_timestamp.isoformat(),
            "metadata": self.metadata,
        }


class InferenceEngine(ABC):
    """Abstract base class for inference engines"""

    @abstractmethod
    async def predict(
        self,
        model_id: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run inference on a model"""

    @abstractmethod
    async def batch_predict(
        self,
        model_id: str,
        input_data_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run batch inference on a model"""

    @abstractmethod
    def get_model_info(self, model_id: str) -> dict[str, Any]:
        """Get model information"""


class ModelServingInferenceEngine(InferenceEngine):
    """Inference engine using model serving service"""

    def __init__(self, model_serving_service):
        self.model_serving_service = model_serving_service

    async def predict(
        self,
        model_id: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run inference using model serving service"""
        try:
            from .model_serving import InferenceRequest

            request = InferenceRequest(
                request_id=str(uuid.uuid4()),
                model_id=model_id,
                input_data=input_data,
            )

            response = await self.model_serving_service.predict(request)
            return response.predictions

        except Exception as e:
            logger.error(f"Inference failed for model {model_id}: {e}")
            raise

    async def batch_predict(
        self,
        model_id: str,
        input_data_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run batch inference"""
        try:
            # Process in parallel
            tasks = [
                self.predict(model_id, input_data) for input_data in input_data_list
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            predictions = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Batch prediction error: {result}")
                    predictions.append({"error": str(result)})
                else:
                    predictions.append(result)

            return predictions

        except Exception as e:
            logger.error(f"Batch inference failed for model {model_id}: {e}")
            raise

    def get_model_info(self, model_id: str) -> dict[str, Any]:
        """Get model information"""
        try:
            health = self.model_serving_service.get_model_status(model_id)
            if health:
                return {
                    "model_id": model_id,
                    "status": health.status.value,
                    "health_score": health.health_score,
                    "average_latency_ms": health.average_latency_ms,
                    "success_count": health.success_count,
                    "error_count": health.error_count,
                }
            return {"model_id": model_id, "status": "not_found"}

        except Exception as e:
            logger.error(f"Failed to get model info for {model_id}: {e}")
            return {"model_id": model_id, "status": "error", "error": str(e)}


class EnsemblePredictor:
    """Ensemble prediction coordinator"""

    def __init__(self):
        self.ensemble_methods = {
            EnsembleMethod.VOTING: self._voting_ensemble,
            EnsembleMethod.AVERAGING: self._averaging_ensemble,
            EnsembleMethod.WEIGHTED_AVERAGING: self._weighted_averaging_ensemble,
            EnsembleMethod.STACKING: self._stacking_ensemble,
        }

    async def predict_ensemble(
        self,
        predictions: dict[str, dict[str, Any]],
        method: EnsembleMethod,
        weights: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create ensemble prediction from individual model predictions"""
        try:
            if method in self.ensemble_methods:
                ensemble_func = self.ensemble_methods[method]
                return await ensemble_func(predictions, weights)
            raise ValueError(f"Unsupported ensemble method: {method}")

        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            raise

    async def _voting_ensemble(
        self,
        predictions: dict[str, dict[str, Any]],
        weights: list[float] | None = None,
    ) -> dict[str, Any]:
        """Voting ensemble method"""
        try:
            # Extract prediction values
            pred_values = []
            for model_id, pred in predictions.items():
                if "predictions" in pred:
                    pred_values.append(pred["predictions"])
                else:
                    pred_values.append(pred)

            # Convert to numpy arrays
            pred_arrays = [np.array(pv) for pv in pred_values]

            # Simple majority voting for classification
            if len(pred_arrays) > 0:
                if pred_arrays[0].ndim == 1:  # Classification
                    # Count votes for each class
                    all_predictions = np.concatenate(pred_arrays)
                    unique, counts = np.unique(all_predictions, return_counts=True)
                    ensemble_pred = unique[np.argmax(counts)]
                else:  # Regression or probabilities
                    # Average predictions
                    ensemble_pred = np.mean(pred_arrays, axis=0)
            else:
                ensemble_pred = None

            return {
                "ensemble_prediction": (
                    ensemble_pred.tolist() if ensemble_pred is not None else None
                ),
                "method": "voting",
                "model_count": len(predictions),
            }

        except Exception as e:
            logger.error(f"Voting ensemble failed: {e}")
            raise

    async def _averaging_ensemble(
        self,
        predictions: dict[str, dict[str, Any]],
        weights: list[float] | None = None,
    ) -> dict[str, Any]:
        """Averaging ensemble method"""
        try:
            # Extract prediction values
            pred_values = []
            for model_id, pred in predictions.items():
                if "predictions" in pred:
                    pred_values.append(pred["predictions"])
                else:
                    pred_values.append(pred)

            # Convert to numpy arrays
            pred_arrays = [np.array(pv) for pv in pred_values]

            # Average predictions
            if len(pred_arrays) > 0:
                ensemble_pred = np.mean(pred_arrays, axis=0)
            else:
                ensemble_pred = None

            return {
                "ensemble_prediction": (
                    ensemble_pred.tolist() if ensemble_pred is not None else None
                ),
                "method": "averaging",
                "model_count": len(predictions),
            }

        except Exception as e:
            logger.error(f"Averaging ensemble failed: {e}")
            raise

    async def _weighted_averaging_ensemble(
        self,
        predictions: dict[str, dict[str, Any]],
        weights: list[float] | None = None,
    ) -> dict[str, Any]:
        """Weighted averaging ensemble method"""
        try:
            # Extract prediction values
            pred_values = []
            for model_id, pred in predictions.items():
                if "predictions" in pred:
                    pred_values.append(pred["predictions"])
                else:
                    pred_values.append(pred)

            # Convert to numpy arrays
            pred_arrays = [np.array(pv) for pv in pred_values]

            # Apply weights
            if weights is None:
                weights = [1.0 / len(pred_arrays)] * len(pred_arrays)

            # Normalize weights
            weights = np.array(weights)
            weights = weights / np.sum(weights)

            # Weighted average
            if len(pred_arrays) > 0:
                ensemble_pred = np.average(pred_arrays, axis=0, weights=weights)
            else:
                ensemble_pred = None

            return {
                "ensemble_prediction": (
                    ensemble_pred.tolist() if ensemble_pred is not None else None
                ),
                "method": "weighted_averaging",
                "model_count": len(predictions),
                "weights": weights.tolist(),
            }

        except Exception as e:
            logger.error(f"Weighted averaging ensemble failed: {e}")
            raise

    async def _stacking_ensemble(
        self,
        predictions: dict[str, dict[str, Any]],
        weights: list[float] | None = None,
    ) -> dict[str, Any]:
        """Stacking ensemble method (simplified)"""
        try:
            # For simplicity, use weighted averaging as stacking
            # In production, this would use a meta-learner
            return await self._weighted_averaging_ensemble(predictions, weights)

        except Exception as e:
            logger.error(f"Stacking ensemble failed: {e}")
            raise


class PredictionService:
    """High-performance prediction service with ensemble capabilities.
    Provides real-time, batch, and streaming predictions with comprehensive result management.
    """

    def __init__(self, inference_engine: InferenceEngine):
        self.inference_engine = inference_engine
        self.ensemble_predictor = EnsemblePredictor()

        # Request management
        self.active_requests: dict[str, asyncio.Task] = {}
        self.prediction_results: dict[str, PredictionResult] = {}
        self.batch_results: dict[str, BatchPredictionResult] = {}

        # Processing executor
        self.executor = ThreadPoolExecutor(max_workers=20)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "ensemble_requests": 0,
            "batch_requests": 0,
            "average_processing_time_ms": 0.0,
            "total_processing_time_ms": 0.0,
        }

        logger.info("Initialized Prediction Service")

    async def predict(self, request: PredictionRequest) -> PredictionResult:
        """Process a prediction request"""
        start_time = time.time()

        try:
            # Validate request
            if not self._validate_request(request):
                raise ValueError("Invalid prediction request")

            # Update statistics
            self.stats["total_requests"] += 1

            # Run predictions for each model
            model_predictions = {}
            model_errors = {}

            for model_id in request.model_ids:
                try:
                    prediction = await self.inference_engine.predict(
                        model_id,
                        request.input_data,
                    )
                    model_predictions[model_id] = prediction
                except Exception as e:
                    model_errors[model_id] = str(e)
                    logger.error(f"Prediction failed for model {model_id}: {e}")

            # Create ensemble prediction if requested
            ensemble_prediction = None
            if request.ensemble_method and len(model_predictions) > 1:
                try:
                    ensemble_prediction = (
                        await self.ensemble_predictor.predict_ensemble(
                            model_predictions,
                            request.ensemble_method,
                            request.ensemble_weights,
                        )
                    )
                    self.stats["ensemble_requests"] += 1
                except Exception as e:
                    logger.error(f"Ensemble prediction failed: {e}")

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Create result
            result = PredictionResult(
                request_id=request.request_id,
                model_ids=request.model_ids,
                predictions=model_predictions,
                ensemble_prediction=ensemble_prediction,
                processing_time_ms=processing_time,
                status=(
                    PredictionStatus.COMPLETED
                    if model_predictions
                    else PredictionStatus.FAILED
                ),
                error_message=(
                    "; ".join(model_errors.values()) if model_errors else None
                ),
            )

            # Store result
            self.prediction_results[request.request_id] = result

            # Update statistics
            if result.status == PredictionStatus.COMPLETED:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1

            self._update_average_processing_time(processing_time)

            logger.info(f"Prediction completed for request {request.request_id}")
            return result

        except Exception as e:
            # Create failed result
            processing_time = (time.time() - start_time) * 1000
            result = PredictionResult(
                request_id=request.request_id,
                model_ids=request.model_ids,
                predictions={},
                processing_time_ms=processing_time,
                status=PredictionStatus.FAILED,
                error_message=str(e),
            )

            self.prediction_results[request.request_id] = result
            self.stats["failed_requests"] += 1

            logger.error(f"Prediction failed for request {request.request_id}: {e}")
            return result

    async def batch_predict(
        self,
        request: BatchPredictionRequest,
    ) -> BatchPredictionResult:
        """Process a batch prediction request"""
        start_time = time.time()

        try:
            # Validate request
            if not self._validate_batch_request(request):
                raise ValueError("Invalid batch prediction request")

            # Update statistics
            self.stats["batch_requests"] += 1

            # Process in batches
            results = []
            successful_predictions = 0
            failed_predictions = 0

            for i in range(0, len(request.input_data_list), request.batch_size):
                batch_data = request.input_data_list[i : i + request.batch_size]

                # Create individual requests for this batch
                batch_requests = []
                for j, input_data in enumerate(batch_data):
                    pred_request = PredictionRequest(
                        request_id=f"{request.batch_id}_{i}_{j}",
                        model_ids=request.model_ids,
                        input_data=input_data,
                        prediction_type=PredictionType.BATCH,
                        ensemble_method=request.ensemble_method,
                        ensemble_weights=request.ensemble_weights,
                    )
                    batch_requests.append(pred_request)

                # Process batch requests in parallel
                batch_results = await asyncio.gather(
                    *[self.predict(req) for req in batch_requests],
                    return_exceptions=True,
                )

                # Handle results
                for result in batch_results:
                    if isinstance(result, Exception):
                        failed_predictions += 1
                        logger.error(f"Batch prediction error: {result}")
                    else:
                        results.append(result)
                        if result.status == PredictionStatus.COMPLETED:
                            successful_predictions += 1
                        else:
                            failed_predictions += 1

            # Calculate total processing time
            total_processing_time = (time.time() - start_time) * 1000

            # Create batch result
            batch_result = BatchPredictionResult(
                batch_id=request.batch_id,
                model_ids=request.model_ids,
                results=results,
                total_processing_time_ms=total_processing_time,
                successful_predictions=successful_predictions,
                failed_predictions=failed_predictions,
                status=(
                    PredictionStatus.COMPLETED
                    if successful_predictions > 0
                    else PredictionStatus.FAILED
                ),
            )

            # Store result
            self.batch_results[request.batch_id] = batch_result

            logger.info(f"Batch prediction completed for batch {request.batch_id}")
            return batch_result

        except Exception as e:
            # Create failed batch result
            total_processing_time = (time.time() - start_time) * 1000
            batch_result = BatchPredictionResult(
                batch_id=request.batch_id,
                model_ids=request.model_ids,
                results=[],
                total_processing_time_ms=total_processing_time,
                successful_predictions=0,
                failed_predictions=len(request.input_data_list),
                status=PredictionStatus.FAILED,
                error_message=str(e),
            )

            self.batch_results[request.batch_id] = batch_result

            logger.error(f"Batch prediction failed for batch {request.batch_id}: {e}")
            return batch_result

    def _validate_request(self, request: PredictionRequest) -> bool:
        """Validate prediction request"""
        try:
            # Check required fields
            if (
                not request.request_id
                or not request.model_ids
                or not request.input_data
            ):
                return False

            # Check model IDs
            if len(request.model_ids) == 0:
                return False

            # Check ensemble configuration
            if request.ensemble_method and len(request.model_ids) < 2:
                logger.warning("Ensemble method specified but only one model provided")

            return True

        except Exception as e:
            logger.error(f"Request validation error: {e}")
            return False

    def _validate_batch_request(self, request: BatchPredictionRequest) -> bool:
        """Validate batch prediction request"""
        try:
            # Check required fields
            if (
                not request.batch_id
                or not request.model_ids
                or not request.input_data_list
            ):
                return False

            # Check data list
            if len(request.input_data_list) == 0:
                return False

            # Check batch size
            if request.batch_size <= 0:
                return False

            return True

        except Exception as e:
            logger.error(f"Batch request validation error: {e}")
            return False

    def _update_average_processing_time(self, processing_time: float):
        """Update average processing time"""
        total_requests = (
            self.stats["successful_requests"] + self.stats["failed_requests"]
        )
        if total_requests > 0:
            self.stats["total_processing_time_ms"] += processing_time
            self.stats["average_processing_time_ms"] = (
                self.stats["total_processing_time_ms"] / total_requests
            )

    def get_prediction_result(self, request_id: str) -> PredictionResult | None:
        """Get prediction result by request ID"""
        return self.prediction_results.get(request_id)

    def get_batch_result(self, batch_id: str) -> BatchPredictionResult | None:
        """Get batch prediction result by batch ID"""
        return self.batch_results.get(batch_id)

    def list_recent_predictions(self, limit: int = 100) -> list[PredictionResult]:
        """List recent predictions"""
        results = list(self.prediction_results.values())
        results.sort(key=lambda x: x.response_timestamp, reverse=True)
        return results[:limit]

    def list_recent_batches(self, limit: int = 50) -> list[BatchPredictionResult]:
        """List recent batch predictions"""
        results = list(self.batch_results.values())
        results.sort(key=lambda x: x.completed_timestamp, reverse=True)
        return results[:limit]

    def get_service_statistics(self) -> dict[str, Any]:
        """Get service statistics"""
        stats = self.stats.copy()

        if stats["total_requests"] > 0:
            stats["success_rate"] = (
                stats["successful_requests"] / stats["total_requests"]
            )
            stats["failure_rate"] = stats["failed_requests"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0

        stats["active_requests"] = len(self.active_requests)
        stats["cached_results"] = len(self.prediction_results)
        stats["cached_batches"] = len(self.batch_results)

        return stats

    async def cleanup_old_results(self, max_age_hours: int = 24):
        """Clean up old prediction results"""
        try:
            cutoff_time = datetime.now(UTC).timestamp() - (max_age_hours * 3600)

            # Clean up individual results
            old_results = [
                req_id
                for req_id, result in self.prediction_results.items()
                if result.response_timestamp.timestamp() < cutoff_time
            ]

            for req_id in old_results:
                del self.prediction_results[req_id]

            # Clean up batch results
            old_batches = [
                batch_id
                for batch_id, result in self.batch_results.items()
                if result.completed_timestamp.timestamp() < cutoff_time
            ]

            for batch_id in old_batches:
                del self.batch_results[batch_id]

            logger.info(
                f"Cleaned up {len(old_results)} old results and {len(old_batches)} old batches",
            )

        except Exception as e:
            logger.error(f"Failed to cleanup old results: {e}")


# Production-ready factory functions
def create_production_prediction_service(
    inference_engine: InferenceEngine,
) -> PredictionService:
    """Create production-ready prediction service"""
    return PredictionService(inference_engine)


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create mock inference engine
        class MockInferenceEngine(InferenceEngine):
            async def predict(
                self,
                model_id: str,
                input_data: dict[str, Any],
            ) -> dict[str, Any]:
                # Mock prediction
                return {"prediction": np.random.random(), "confidence": 0.8}

            async def batch_predict(
                self,
                model_id: str,
                input_data_list: list[dict[str, Any]],
            ) -> list[dict[str, Any]]:
                return [
                    {"prediction": np.random.random(), "confidence": 0.8}
                    for _ in input_data_list
                ]

            def get_model_info(self, model_id: str) -> dict[str, Any]:
                return {"model_id": model_id, "status": "ready"}

        # Create prediction service
        inference_engine = MockInferenceEngine()
        service = PredictionService(inference_engine)

        # Test individual prediction
        request = PredictionRequest(
            request_id="test_request_001",
            model_ids=["model_1", "model_2"],
            input_data={"feature_1": 1.0, "feature_2": 2.0},
            ensemble_method=EnsembleMethod.AVERAGING,
        )

        result = await service.predict(request)
        print(f"Prediction result: {result.predictions}")
        print(f"Ensemble prediction: {result.ensemble_prediction}")
        print(f"Processing time: {result.processing_time_ms}ms")

        # Test batch prediction
        batch_request = BatchPredictionRequest(
            batch_id="test_batch_001",
            model_ids=["model_1"],
            input_data_list=[
                {"feature_1": 1.0, "feature_2": 2.0},
                {"feature_1": 3.0, "feature_2": 4.0},
                {"feature_1": 5.0, "feature_2": 6.0},
            ],
            batch_size=2,
        )

        batch_result = await service.batch_predict(batch_request)
        print(
            f"Batch result: {batch_result.successful_predictions} successful, {batch_result.failed_predictions} failed",
        )
        print(f"Total processing time: {batch_result.total_processing_time_ms}ms")

        # Get statistics
        stats = service.get_service_statistics()
        print(f"Service statistics: {stats}")

    asyncio.run(main())
