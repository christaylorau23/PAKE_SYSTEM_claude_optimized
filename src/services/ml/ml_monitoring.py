#!/usr/bin/env python3
"""PAKE System - ML Monitoring Service
Phase 9B: Advanced AI/ML Pipeline Integration

Provides comprehensive ML model monitoring, drift detection, performance tracking,
A/B testing, and alerting capabilities for production ML systems.
"""

import asyncio
import logging
import statistics
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DriftType(Enum):
    """Types of data drift"""

    CONCEPT_DRIFT = "concept_drift"
    DATA_DRIFT = "data_drift"
    LABEL_DRIFT = "label_drift"
    FEATURE_DRIFT = "feature_drift"
    PERFORMANCE_DRIFT = "performance_drift"


class MetricType(Enum):
    """Types of monitoring metrics"""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    AUC = "auc"
    MAE = "mae"
    MSE = "mse"
    R2_SCORE = "r2_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"


@dataclass(frozen=True)
class ModelMetric:
    """Immutable model metric"""

    model_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "model_id": self.model_id,
            "metric_type": metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DriftAlert:
    """Immutable drift detection alert"""

    alert_id: str
    model_id: str
    drift_type: DriftType
    severity: AlertLevel
    drift_score: float
    threshold: float
    affected_features: list[str] = field(default_factory=list)
    detection_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    description: str = ""
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "alert_id": self.alert_id,
            "model_id": self.model_id,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "drift_score": self.drift_score,
            "threshold": self.threshold,
            "affected_features": self.affected_features,
            "detection_timestamp": self.detection_timestamp.isoformat(),
            "description": self.description,
            "recommendations": self.recommendations,
        }


@dataclass(frozen=True)
class PerformanceAlert:
    """Immutable performance alert"""

    alert_id: str
    model_id: str
    metric_type: MetricType
    severity: AlertLevel
    current_value: float
    threshold_value: float
    trend: str  # "improving", "degrading", "stable"
    detection_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    description: str = ""
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "alert_id": self.alert_id,
            "model_id": self.model_id,
            "metric_type": self.metric_type.value,
            "severity": self.severity.value,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "trend": self.trend,
            "detection_timestamp": self.detection_timestamp.isoformat(),
            "description": self.description,
            "recommendations": self.recommendations,
        }


@dataclass(frozen=True)
class ABTestResult:
    """Immutable A/B test result"""

    test_id: str
    model_a_id: str
    model_b_id: str
    metric_type: MetricType
    model_a_metric: float
    model_b_metric: float
    statistical_significance: float
    confidence_interval: tuple[float, float]
    p_value: float
    test_duration_hours: float
    sample_size: int
    conclusion: str  # "model_a_better", "model_b_better", "no_significant_difference"
    completed_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "test_id": self.test_id,
            "model_a_id": self.model_a_id,
            "model_b_id": self.model_b_id,
            "metric_type": self.metric_type.value,
            "model_a_metric": self.model_a_metric,
            "model_b_metric": self.model_b_metric,
            "statistical_significance": self.statistical_significance,
            "confidence_interval": self.confidence_interval,
            "p_value": self.p_value,
            "test_duration_hours": self.test_duration_hours,
            "sample_size": self.sample_size,
            "conclusion": self.conclusion,
            "completed_timestamp": self.completed_timestamp.isoformat(),
        }


@dataclass
class MLMonitoringConfig:
    """Configuration for ML monitoring service"""

    # Monitoring intervals
    metric_collection_interval_seconds: int = 60
    drift_detection_interval_hours: int = 24
    performance_check_interval_hours: int = 6

    # Drift detection thresholds
    concept_drift_threshold: float = 0.1
    data_drift_threshold: float = 0.15
    performance_drift_threshold: float = 0.05

    # Performance thresholds
    accuracy_threshold: float = 0.8
    latency_threshold_ms: float = 1000.0
    error_rate_threshold: float = 0.05

    # Alerting
    enable_alerting: bool = True
    alert_cooldown_minutes: int = 30
    max_alerts_per_hour: int = 10

    # A/B testing
    enable_ab_testing: bool = True
    min_sample_size: int = 1000
    significance_level: float = 0.05
    max_test_duration_hours: int = 168  # 1 week

    # Storage
    metrics_retention_days: int = 90
    alerts_retention_days: int = 30
    enable_metrics_compression: bool = True


class DriftDetector(ABC):
    """Abstract base class for drift detectors"""

    @abstractmethod
    async def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        model_id: str,
    ) -> tuple[bool, float, list[str]]:
        """Detect drift between reference and current data"""


class StatisticalDriftDetector(DriftDetector):
    """Statistical drift detector using KS test and other statistical tests"""

    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold

    async def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        model_id: str,
    ) -> tuple[bool, float, list[str]]:
        """Detect drift using statistical tests"""
        try:
            from scipy import stats

            drift_detected = False
            max_drift_score = 0.0
            affected_features = []

            # Get numerical columns
            numerical_cols = reference_data.select_dtypes(include=[np.number]).columns

            for col in numerical_cols:
                if col in current_data.columns:
                    ref_values = reference_data[col].dropna()
                    curr_values = current_data[col].dropna()

                    if len(ref_values) > 0 and len(curr_values) > 0:
                        # Kolmogorov-Smirnov test
                        ks_statistic, ks_p_value = stats.ks_2samp(
                            ref_values,
                            curr_values,
                        )

                        # Mann-Whitney U test
                        mw_statistic, mw_p_value = stats.mannwhitneyu(
                            ref_values,
                            curr_values,
                            alternative="two-sided",
                        )

                        # Use the more conservative p-value
                        drift_score = min(ks_p_value, mw_p_value)

                        if drift_score < self.threshold:
                            drift_detected = True
                            affected_features.append(col)
                            max_drift_score = max(max_drift_score, 1.0 - drift_score)

            return drift_detected, max_drift_score, affected_features

        except Exception as e:
            logger.error(f"Statistical drift detection failed: {e}")
            return False, 0.0, []


class PerformanceDriftDetector(DriftDetector):
    """Performance-based drift detector"""

    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold

    async def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        model_id: str,
    ) -> tuple[bool, float, list[str]]:
        """Detect performance drift"""
        try:
            # This is a simplified implementation
            # In production, this would compare model performance metrics

            # Calculate basic statistics
            ref_mean = reference_data.mean().mean()
            curr_mean = current_data.mean().mean()

            # Calculate drift score
            drift_score = abs(ref_mean - curr_mean) / max(abs(ref_mean), 1e-8)

            drift_detected = drift_score > self.threshold
            affected_features = list(reference_data.columns) if drift_detected else []

            return drift_detected, drift_score, affected_features

        except Exception as e:
            logger.error(f"Performance drift detection failed: {e}")
            return False, 0.0, []


class ModelDriftDetector:
    """Comprehensive model drift detector"""

    def __init__(self, config: MLMonitoringConfig):
        self.config = config
        self.drift_detectors = {
            DriftType.DATA_DRIFT: StatisticalDriftDetector(config.data_drift_threshold),
            DriftType.PERFORMANCE_DRIFT: PerformanceDriftDetector(
                config.performance_drift_threshold,
            ),
        }

        # Reference data storage
        self.reference_data: dict[str, pd.DataFrame] = {}
        self.reference_timestamps: dict[str, datetime] = {}

    async def set_reference_data(self, model_id: str, reference_data: pd.DataFrame):
        """Set reference data for drift detection"""
        try:
            self.reference_data[model_id] = reference_data.copy()
            self.reference_timestamps[model_id] = datetime.now(UTC)
            logger.info(f"Set reference data for model {model_id}")
        except Exception as e:
            logger.error(f"Failed to set reference data for model {model_id}: {e}")

    async def detect_drift(
        self,
        model_id: str,
        current_data: pd.DataFrame,
    ) -> list[DriftAlert]:
        """Detect drift for a model"""
        alerts = []

        try:
            if model_id not in self.reference_data:
                logger.warning(f"No reference data found for model {model_id}")
                return alerts

            reference_data = self.reference_data[model_id]

            for drift_type, detector in self.drift_detectors.items():
                (
                    drift_detected,
                    drift_score,
                    affected_features,
                ) = await detector.detect_drift(reference_data, current_data, model_id)

                if drift_detected:
                    # Determine severity
                    if drift_score > 0.3:
                        severity = AlertLevel.CRITICAL
                    elif drift_score > 0.2:
                        severity = AlertLevel.ERROR
                    elif drift_score > 0.1:
                        severity = AlertLevel.WARNING
                    else:
                        severity = AlertLevel.INFO

                    # Create alert
                    alert = DriftAlert(
                        alert_id=f"drift_{model_id}_{int(time.time())}",
                        model_id=model_id,
                        drift_type=drift_type,
                        severity=severity,
                        drift_score=drift_score,
                        threshold=self._get_threshold_for_drift_type(drift_type),
                        affected_features=affected_features,
                        description=f"{drift_type.value} detected with score {drift_score:.3f}",
                        recommendations=self._get_drift_recommendations(
                            drift_type,
                            drift_score,
                        ),
                    )

                    alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Drift detection failed for model {model_id}: {e}")
            return alerts

    def _get_threshold_for_drift_type(self, drift_type: DriftType) -> float:
        """Get threshold for drift type"""
        thresholds = {
            DriftType.CONCEPT_DRIFT: self.config.concept_drift_threshold,
            DriftType.DATA_DRIFT: self.config.data_drift_threshold,
            DriftType.PERFORMANCE_DRIFT: self.config.performance_drift_threshold,
        }
        return thresholds.get(drift_type, 0.1)

    def _get_drift_recommendations(
        self,
        drift_type: DriftType,
        drift_score: float,
    ) -> list[str]:
        """Get recommendations for drift type"""
        recommendations = []

        if drift_type == DriftType.DATA_DRIFT:
            recommendations.extend(
                [
                    "Review data preprocessing pipeline",
                    "Check for changes in data sources",
                    "Consider retraining the model",
                ],
            )
        elif drift_type == DriftType.PERFORMANCE_DRIFT:
            recommendations.extend(
                [
                    "Monitor model performance metrics",
                    "Check for concept drift",
                    "Consider model retraining or fine-tuning",
                ],
            )

        if drift_score > 0.2:
            recommendations.append("Immediate investigation required")

        return recommendations


class MLMonitor:
    """Comprehensive ML monitoring service.
    Provides model monitoring, drift detection, performance tracking, and alerting.
    """

    def __init__(self, config: MLMonitoringConfig = None):
        self.config = config or MLMonitoringConfig()

        # Monitoring components
        self.drift_detector = ModelDriftDetector(self.config)

        # Data storage
        self.model_metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.active_alerts: dict[
            str, list[DriftAlert | PerformanceAlert]
        ] = defaultdict(list)
        self.ab_tests: dict[str, dict[str, Any]] = {}
        self.ab_test_results: dict[str, ABTestResult] = {}

        # Monitoring tasks
        self.monitoring_tasks: dict[str, asyncio.Task] = {}

        # Statistics
        self.stats = {
            "total_metrics_collected": 0,
            "total_alerts_generated": 0,
            "total_drift_detections": 0,
            "active_ab_tests": 0,
            "completed_ab_tests": 0,
        }

        logger.info("Initialized ML Monitor")

    async def start_monitoring(self, model_id: str):
        """Start monitoring for a model"""
        try:
            if model_id in self.monitoring_tasks:
                logger.warning(f"Monitoring already active for model {model_id}")
                return

            # Start monitoring tasks
            self.monitoring_tasks[model_id] = asyncio.create_task(
                self._monitoring_loop(model_id),
            )

            logger.info(f"Started monitoring for model {model_id}")

        except Exception as e:
            logger.error(f"Failed to start monitoring for model {model_id}: {e}")

    async def stop_monitoring(self, model_id: str):
        """Stop monitoring for a model"""
        try:
            if model_id in self.monitoring_tasks:
                task = self.monitoring_tasks[model_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                del self.monitoring_tasks[model_id]
                logger.info(f"Stopped monitoring for model {model_id}")

        except Exception as e:
            logger.error(f"Failed to stop monitoring for model {model_id}: {e}")

    async def _monitoring_loop(self, model_id: str):
        """Main monitoring loop for a model"""
        while True:
            try:
                await asyncio.sleep(self.config.metric_collection_interval_seconds)

                # Collect metrics (simplified)
                await self._collect_model_metrics(model_id)

                # Check for performance issues
                await self._check_performance_alerts(model_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error for model {model_id}: {e}")

    async def _collect_model_metrics(self, model_id: str):
        """Collect metrics for a model"""
        try:
            # This is a simplified implementation
            # In production, this would collect real metrics from the model serving
            # service

            # Mock metrics collection
            metrics = [
                ModelMetric(
                    model_id,
                    MetricType.ACCURACY,
                    0.85 + np.random.normal(0, 0.02),
                ),
                ModelMetric(model_id, MetricType.LATENCY, 50 + np.random.normal(0, 10)),
                ModelMetric(
                    model_id,
                    MetricType.ERROR_RATE,
                    0.02 + np.random.normal(0, 0.005),
                ),
            ]

            for metric in metrics:
                self.model_metrics[model_id].append(metric)
                self.stats["total_metrics_collected"] += 1

        except Exception as e:
            logger.error(f"Failed to collect metrics for model {model_id}: {e}")

    async def _check_performance_alerts(self, model_id: str):
        """Check for performance alerts"""
        try:
            if model_id not in self.model_metrics:
                return

            metrics = list(self.model_metrics[model_id])
            if len(metrics) < 10:  # Need sufficient data
                return

            # Check recent metrics
            recent_metrics = metrics[-10:]

            for metric_type in [
                MetricType.ACCURACY,
                MetricType.LATENCY,
                MetricType.ERROR_RATE,
            ]:
                values = [
                    m.value for m in recent_metrics if m.metric_type == metric_type
                ]
                if not values:
                    continue

                current_value = values[-1]
                threshold = self._get_threshold_for_metric(metric_type)

                # Check if threshold is exceeded
                if self._is_threshold_exceeded(metric_type, current_value, threshold):
                    # Determine severity
                    severity = self._determine_severity(
                        metric_type,
                        current_value,
                        threshold,
                    )

                    # Calculate trend
                    trend = self._calculate_trend(values)

                    # Create alert
                    alert = PerformanceAlert(
                        alert_id=f"perf_{model_id}_{int(time.time())}",
                        model_id=model_id,
                        metric_type=metric_type,
                        severity=severity,
                        current_value=current_value,
                        threshold_value=threshold,
                        trend=trend,
                        description=f"{metric_type.value} threshold exceeded: {current_value:.3f} > {threshold:.3f}",
                        recommendations=self._get_performance_recommendations(
                            metric_type,
                            current_value,
                            threshold,
                        ),
                    )

                    await self._process_alert(alert)

        except Exception as e:
            logger.error(f"Performance alert check failed for model {model_id}: {e}")

    def _get_threshold_for_metric(self, metric_type: MetricType) -> float:
        """Get threshold for metric type"""
        thresholds = {
            MetricType.ACCURACY: self.config.accuracy_threshold,
            MetricType.LATENCY: self.config.latency_threshold_ms,
            MetricType.ERROR_RATE: self.config.error_rate_threshold,
        }
        return thresholds.get(metric_type, 0.0)

    def _is_threshold_exceeded(
        self,
        metric_type: MetricType,
        value: float,
        threshold: float,
    ) -> bool:
        """Check if threshold is exceeded"""
        if metric_type in [MetricType.ACCURACY]:
            return value < threshold  # Lower is worse
        return value > threshold  # Higher is worse

    def _determine_severity(
        self,
        metric_type: MetricType,
        value: float,
        threshold: float,
    ) -> AlertLevel:
        """Determine alert severity"""
        if metric_type == MetricType.ACCURACY:
            if value < threshold * 0.7:
                return AlertLevel.CRITICAL
            if value < threshold * 0.8:
                return AlertLevel.ERROR
            if value < threshold * 0.9:
                return AlertLevel.WARNING
            return AlertLevel.INFO
        if value > threshold * 2.0:
            return AlertLevel.CRITICAL
        if value > threshold * 1.5:
            return AlertLevel.ERROR
        if value > threshold * 1.2:
            return AlertLevel.WARNING
        return AlertLevel.INFO

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate trend from values"""
        if len(values) < 3:
            return "stable"

        # Simple trend calculation
        recent_avg = statistics.mean(values[-3:])
        older_avg = statistics.mean(values[:-3]) if len(values) > 3 else recent_avg

        if recent_avg > older_avg * 1.05:
            return "degrading"
        if recent_avg < older_avg * 0.95:
            return "improving"
        return "stable"

    def _get_performance_recommendations(
        self,
        metric_type: MetricType,
        value: float,
        threshold: float,
    ) -> list[str]:
        """Get performance recommendations"""
        recommendations = []

        if metric_type == MetricType.ACCURACY:
            recommendations.extend(
                [
                    "Review model performance on recent data",
                    "Check for data quality issues",
                    "Consider model retraining",
                ],
            )
        elif metric_type == MetricType.LATENCY:
            recommendations.extend(
                [
                    "Optimize model inference",
                    "Check system resources",
                    "Consider model optimization",
                ],
            )
        elif metric_type == MetricType.ERROR_RATE:
            recommendations.extend(
                [
                    "Investigate error patterns",
                    "Check input data validation",
                    "Review error handling",
                ],
            )

        return recommendations

    async def _process_alert(self, alert: DriftAlert | PerformanceAlert):
        """Process and store alert"""
        try:
            # Store alert
            self.active_alerts[alert.model_id].append(alert)
            self.stats["total_alerts_generated"] += 1

            # Send alert (simplified)
            logger.warning(
                f"ALERT [{alert.severity.value.upper()}] {alert.model_id}: {alert.description}",
            )

            # Clean up old alerts
            await self._cleanup_old_alerts(alert.model_id)

        except Exception as e:
            logger.error(f"Failed to process alert: {e}")

    async def _cleanup_old_alerts(self, model_id: str):
        """Clean up old alerts"""
        try:
            cutoff_time = datetime.now(UTC) - timedelta(
                days=self.config.alerts_retention_days,
            )

            alerts = self.active_alerts[model_id]
            self.active_alerts[model_id] = [
                alert for alert in alerts if alert.detection_timestamp > cutoff_time
            ]

        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")

    async def start_ab_test(
        self,
        test_id: str,
        model_a_id: str,
        model_b_id: str,
        metric_type: MetricType,
        traffic_split: float = 0.5,
    ) -> bool:
        """Start A/B test between two models"""
        try:
            if test_id in self.ab_tests:
                logger.warning(f"A/B test {test_id} already exists")
                return False

            # Create A/B test
            ab_test = {
                "test_id": test_id,
                "model_a_id": model_a_id,
                "model_b_id": model_b_id,
                "metric_type": metric_type,
                "traffic_split": traffic_split,
                "start_time": datetime.now(UTC),
                "model_a_metrics": [],
                "model_b_metrics": [],
                "status": "active",
            }

            self.ab_tests[test_id] = ab_test
            self.stats["active_ab_tests"] += 1

            logger.info(f"Started A/B test {test_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start A/B test {test_id}: {e}")
            return False

    async def record_ab_test_metric(
        self,
        test_id: str,
        model_id: str,
        metric_value: float,
    ):
        """Record metric for A/B test"""
        try:
            if test_id not in self.ab_tests:
                logger.warning(f"A/B test {test_id} not found")
                return

            ab_test = self.ab_tests[test_id]

            if model_id == ab_test["model_a_id"]:
                ab_test["model_a_metrics"].append(metric_value)
            elif model_id == ab_test["model_b_id"]:
                ab_test["model_b_metrics"].append(metric_value)

            # Check if test should be completed
            await self._check_ab_test_completion(test_id)

        except Exception as e:
            logger.error(f"Failed to record A/B test metric: {e}")

    async def _check_ab_test_completion(self, test_id: str):
        """Check if A/B test should be completed"""
        try:
            ab_test = self.ab_tests[test_id]

            # Check sample size
            total_samples = len(ab_test["model_a_metrics"]) + len(
                ab_test["model_b_metrics"],
            )
            if total_samples < self.config.min_sample_size:
                return

            # Check duration
            duration = datetime.now(UTC) - ab_test["start_time"]
            if duration.total_seconds() / 3600 > self.config.max_test_duration_hours:
                await self._complete_ab_test(test_id)

        except Exception as e:
            logger.error(f"Failed to check A/B test completion: {e}")

    async def _complete_ab_test(self, test_id: str):
        """Complete A/B test and generate results"""
        try:
            ab_test = self.ab_tests[test_id]

            model_a_metrics = ab_test["model_a_metrics"]
            model_b_metrics = ab_test["model_b_metrics"]

            if len(model_a_metrics) == 0 or len(model_b_metrics) == 0:
                logger.warning(f"Insufficient data for A/B test {test_id}")
                return

            # Calculate statistics
            model_a_mean = statistics.mean(model_a_metrics)
            model_b_mean = statistics.mean(model_b_metrics)

            # Simple statistical test (t-test)
            from scipy import stats

            t_stat, p_value = stats.ttest_ind(model_a_metrics, model_b_metrics)

            # Calculate confidence interval
            se_diff = np.sqrt(
                np.var(model_a_metrics) / len(model_a_metrics)
                + np.var(model_b_metrics) / len(model_b_metrics),
            )
            ci_lower = (model_a_mean - model_b_mean) - 1.96 * se_diff
            ci_upper = (model_a_mean - model_b_mean) + 1.96 * se_diff

            # Determine conclusion
            if p_value < self.config.significance_level:
                if model_a_mean > model_b_mean:
                    conclusion = "model_a_better"
                else:
                    conclusion = "model_b_better"
            else:
                conclusion = "no_significant_difference"

            # Create result
            duration_hours = (
                datetime.now(UTC) - ab_test["start_time"]
            ).total_seconds() / 3600

            result = ABTestResult(
                test_id=test_id,
                model_a_id=ab_test["model_a_id"],
                model_b_id=ab_test["model_b_id"],
                metric_type=ab_test["metric_type"],
                model_a_metric=model_a_mean,
                model_b_metric=model_b_mean,
                statistical_significance=1.0 - p_value,
                confidence_interval=(ci_lower, ci_upper),
                p_value=p_value,
                test_duration_hours=duration_hours,
                sample_size=len(model_a_metrics) + len(model_b_metrics),
                conclusion=conclusion,
            )

            # Store result
            self.ab_test_results[test_id] = result
            ab_test["status"] = "completed"

            # Update statistics
            self.stats["active_ab_tests"] -= 1
            self.stats["completed_ab_tests"] += 1

            logger.info(f"Completed A/B test {test_id}: {conclusion}")

        except Exception as e:
            logger.error(f"Failed to complete A/B test {test_id}: {e}")

    def get_model_metrics(self, model_id: str, limit: int = 100) -> list[ModelMetric]:
        """Get recent metrics for a model"""
        if model_id not in self.model_metrics:
            return []

        metrics = list(self.model_metrics[model_id])
        return metrics[-limit:] if limit > 0 else metrics

    def get_active_alerts(
        self,
        model_id: str,
    ) -> list[DriftAlert | PerformanceAlert]:
        """Get active alerts for a model"""
        return self.active_alerts.get(model_id, [])

    def get_ab_test_result(self, test_id: str) -> ABTestResult | None:
        """Get A/B test result"""
        return self.ab_test_results.get(test_id)

    def get_monitoring_statistics(self) -> dict[str, Any]:
        """Get monitoring statistics"""
        stats = self.stats.copy()
        stats["monitored_models"] = len(self.monitoring_tasks)
        stats["active_alerts_total"] = sum(
            len(alerts) for alerts in self.active_alerts.values()
        )
        stats["active_ab_tests"] = len(
            [t for t in self.ab_tests.values() if t["status"] == "active"],
        )

        return stats


# Production-ready factory functions
def create_production_ml_monitor() -> MLMonitor:
    """Create production-ready ML monitor"""
    config = MLMonitoringConfig(
        metric_collection_interval_seconds=30,
        drift_detection_interval_hours=12,
        performance_check_interval_hours=3,
        concept_drift_threshold=0.05,
        data_drift_threshold=0.1,
        performance_drift_threshold=0.03,
        accuracy_threshold=0.85,
        latency_threshold_ms=500.0,
        error_rate_threshold=0.02,
        enable_alerting=True,
        alert_cooldown_minutes=15,
        max_alerts_per_hour=20,
        enable_ab_testing=True,
        min_sample_size=2000,
        significance_level=0.01,
        max_test_duration_hours=336,  # 2 weeks
        metrics_retention_days=180,
        alerts_retention_days=60,
        enable_metrics_compression=True,
    )

    return MLMonitor(config)


if __name__ == "__main__":
    # Example usage
    async def main():
        monitor = MLMonitor()

        # Start monitoring a model
        await monitor.start_monitoring("test_model_1")

        # Simulate some metrics
        for i in range(20):
            await monitor._collect_model_metrics("test_model_1")
            await asyncio.sleep(1)

        # Start A/B test
        await monitor.start_ab_test(
            "test_ab_001",
            "model_a",
            "model_b",
            MetricType.ACCURACY,
            traffic_split=0.5,
        )

        # Record some A/B test metrics
        for i in range(100):
            await monitor.record_ab_test_metric(
                "test_ab_001",
                "model_a",
                0.85 + np.random.normal(0, 0.02),
            )
            await monitor.record_ab_test_metric(
                "test_ab_001",
                "model_b",
                0.87 + np.random.normal(0, 0.02),
            )

        # Get metrics
        metrics = monitor.get_model_metrics("test_model_1", limit=10)
        print(f"Recent metrics: {len(metrics)}")

        # Get alerts
        alerts = monitor.get_active_alerts("test_model_1")
        print(f"Active alerts: {len(alerts)}")

        # Get A/B test result
        ab_result = monitor.get_ab_test_result("test_ab_001")
        if ab_result:
            print(f"A/B test result: {ab_result.conclusion}")

        # Get statistics
        stats = monitor.get_monitoring_statistics()
        print(f"Monitoring statistics: {stats}")

        # Stop monitoring
        await monitor.stop_monitoring("test_model_1")

    asyncio.run(main())
