"""PredictionEngine - Advanced trend prediction and forecasting

Uses machine learning and statistical models for trend prediction and opportunity timing.
"""

import logging
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from ..models.trend_correlation import TrendCorrelation
from ..models.trend_signal import TrendLifecycle, TrendSignal


@dataclass
class PredictionResult:
    """Result of trend prediction"""

    trend_keyword: str
    prediction_type: str  # 'momentum', 'volume', 'lifecycle', 'peak_timing'
    predicted_value: float
    confidence: float
    time_horizon_hours: int
    prediction_timestamp: datetime
    supporting_factors: list[str]


@dataclass
class ForecastModel:
    """Simple forecasting model"""

    model_type: str
    parameters: dict[str, float]
    accuracy_score: float
    last_updated: datetime


class PredictionEngine:
    """Advanced trend prediction and forecasting engine

    Capabilities:
    - Momentum forecasting
    - Volume prediction
    - Lifecycle stage prediction
    - Peak timing estimation
    - Cross-platform correlation prediction
    - Model accuracy tracking
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.accuracy_threshold = 0.95  # For contract testing

        # Prediction models
        self.models: dict[str, ForecastModel] = {}
        self._initialize_models()

        # Historical predictions for accuracy tracking
        self.prediction_history: deque = deque(maxlen=1000)
        self.accuracy_scores: dict[str, list[float]] = defaultdict(list)

        # Feature engineering parameters
        self.feature_window = 24  # hours
        self.min_samples_for_prediction = 3

    def _initialize_models(self):
        """Initialize prediction models"""
        # Simple linear trend model
        self.models["linear_trend"] = ForecastModel(
            model_type="linear_regression",
            parameters={"slope": 0.0, "intercept": 0.0, "r_squared": 0.0},
            accuracy_score=0.7,
            last_updated=datetime.now(),
        )

        # Momentum prediction model
        self.models["momentum_forecast"] = ForecastModel(
            model_type="exponential_smoothing",
            parameters={"alpha": 0.3, "beta": 0.1, "gamma": 0.05},
            accuracy_score=0.65,
            last_updated=datetime.now(),
        )

        # Volume prediction model
        self.models["volume_forecast"] = ForecastModel(
            model_type="seasonal_decomposition",
            parameters={
                "trend_weight": 0.6,
                "seasonal_weight": 0.3,
                "noise_weight": 0.1,
            },
            accuracy_score=0.6,
            last_updated=datetime.now(),
        )

        # Lifecycle prediction model
        self.models["lifecycle_prediction"] = ForecastModel(
            model_type="state_transition",
            parameters={"transition_threshold": 0.1, "confidence_decay": 0.05},
            accuracy_score=0.75,
            last_updated=datetime.now(),
        )

    async def predict_trend_momentum(
        self,
        trend_history: list[TrendSignal],
        forecast_hours: int = 24,
    ) -> PredictionResult:
        """Predict future momentum for a trend"""
        if len(trend_history) < self.min_samples_for_prediction:
            return self._create_low_confidence_prediction(
                trend_history[0].keyword if trend_history else "unknown",
                "momentum",
                0.5,
                forecast_hours,
            )

        # Extract momentum time series
        sorted_history = sorted(trend_history, key=lambda t: t.timestamp)
        momentum_values = [t.momentum for t in sorted_history]
        timestamps = [t.timestamp for t in sorted_history]

        # Calculate time intervals (in hours)
        time_intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600
            time_intervals.append(interval)

        # Use linear trend extrapolation
        predicted_momentum, confidence = self._predict_using_linear_trend(
            momentum_values,
            time_intervals,
            forecast_hours,
        )

        # Generate supporting factors
        supporting_factors = self._analyze_momentum_factors(
            momentum_values,
            time_intervals,
        )

        return PredictionResult(
            trend_keyword=sorted_history[0].keyword,
            prediction_type="momentum",
            predicted_value=predicted_momentum,
            confidence=confidence,
            time_horizon_hours=forecast_hours,
            prediction_timestamp=datetime.now(),
            supporting_factors=supporting_factors,
        )

    async def predict_volume_growth(
        self,
        trend_history: list[TrendSignal],
        forecast_hours: int = 24,
    ) -> PredictionResult:
        """Predict future volume growth for a trend"""
        if len(trend_history) < self.min_samples_for_prediction:
            return self._create_low_confidence_prediction(
                trend_history[0].keyword if trend_history else "unknown",
                "volume",
                1000,
                forecast_hours,
            )

        # Extract volume time series
        sorted_history = sorted(trend_history, key=lambda t: t.timestamp)
        volume_values = [t.volume for t in sorted_history]

        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(volume_values)):
            if volume_values[i - 1] > 0:
                growth_rate = (volume_values[i] - volume_values[i - 1]) / volume_values[
                    i - 1
                ]
                growth_rates.append(growth_rate)

        if not growth_rates:
            return self._create_low_confidence_prediction(
                sorted_history[0].keyword,
                "volume",
                volume_values[-1] if volume_values else 1000,
                forecast_hours,
            )

        # Predict future volume using exponential smoothing
        predicted_growth_rate = self._exponential_smoothing(growth_rates, alpha=0.3)
        current_volume = volume_values[-1]
        predicted_volume = current_volume * (1 + predicted_growth_rate)

        # Calculate confidence based on growth rate stability
        growth_rate_variance = (
            statistics.variance(growth_rates) if len(growth_rates) > 1 else 1.0
        )
        confidence = max(0.1, 1.0 - min(growth_rate_variance, 1.0))

        supporting_factors = [
            f"Average growth rate: {statistics.mean(growth_rates):.1%}",
            f"Growth rate variance: {growth_rate_variance:.3f}",
            f"Data points: {len(volume_values)}",
        ]

        return PredictionResult(
            trend_keyword=sorted_history[0].keyword,
            prediction_type="volume",
            predicted_value=predicted_volume,
            confidence=confidence,
            time_horizon_hours=forecast_hours,
            prediction_timestamp=datetime.now(),
            supporting_factors=supporting_factors,
        )

    async def predict_lifecycle_transition(
        self,
        trend_history: list[TrendSignal],
    ) -> PredictionResult:
        """Predict next lifecycle stage transition"""
        if len(trend_history) < 2:
            return self._create_low_confidence_prediction(
                trend_history[0].keyword if trend_history else "unknown",
                "lifecycle",
                0.5,
                24,
            )

        sorted_history = sorted(trend_history, key=lambda t: t.timestamp)
        current_trend = sorted_history[-1]

        # Analyze lifecycle progression patterns
        stage_changes = self._analyze_lifecycle_changes(sorted_history)
        momentum_trend = self._calculate_momentum_trend(sorted_history)
        volume_trend = self._calculate_volume_trend(sorted_history)

        # Predict next stage based on current stage and trends
        next_stage, confidence, hours_to_transition = (
            self._predict_next_lifecycle_stage(
                current_trend.lifecycle_stage,
                momentum_trend,
                volume_trend,
                stage_changes,
            )
        )

        supporting_factors = [
            f"Current stage: {current_trend.lifecycle_stage.value}",
            f"Momentum trend: {momentum_trend:.2f}",
            f"Volume trend: {volume_trend:.2f}",
            f"Historical stage changes: {len(stage_changes)}",
        ]

        return PredictionResult(
            trend_keyword=current_trend.keyword,
            prediction_type="lifecycle",
            predicted_value=self._lifecycle_to_numeric(next_stage),
            confidence=confidence,
            time_horizon_hours=hours_to_transition,
            prediction_timestamp=datetime.now(),
            supporting_factors=supporting_factors,
        )

    async def predict_peak_timing(
        self,
        trend_history: list[TrendSignal],
        correlations: list[TrendCorrelation] = None,
    ) -> PredictionResult:
        """Predict when trend will reach its peak"""
        if len(trend_history) < self.min_samples_for_prediction:
            return self._create_low_confidence_prediction(
                trend_history[0].keyword if trend_history else "unknown",
                "peak_timing",
                72,  # 3 days default
                24,
            )

        sorted_history = sorted(trend_history, key=lambda t: t.timestamp)

        # Analyze momentum and volume patterns
        momentum_trajectory = [t.momentum for t in sorted_history]
        volume_trajectory = [t.volume for t in sorted_history]

        # Calculate derivatives to find inflection points
        momentum_derivative = self._calculate_derivative(momentum_trajectory)
        volume_derivative = self._calculate_derivative(volume_trajectory)

        # Predict peak based on current trajectory
        peak_hours, confidence = self._predict_peak_from_trajectories(
            momentum_trajectory,
            volume_trajectory,
            momentum_derivative,
            volume_derivative,
        )

        # Enhance prediction with correlation data
        if correlations:
            correlation_adjustment = self._adjust_peak_prediction_with_correlations(
                peak_hours,
                correlations,
            )
            peak_hours = correlation_adjustment

        supporting_factors = [
            f"Momentum trajectory slope: {momentum_derivative[-1] if momentum_derivative else 0:.3f}",
            f"Volume trajectory slope: {volume_derivative[-1] if volume_derivative else 0:.3f}",
            f"Current momentum: {sorted_history[-1].momentum:.2f}",
            f"Correlations considered: {len(correlations) if correlations else 0}",
        ]

        return PredictionResult(
            trend_keyword=sorted_history[0].keyword,
            prediction_type="peak_timing",
            predicted_value=peak_hours,
            confidence=confidence,
            time_horizon_hours=int(peak_hours),
            prediction_timestamp=datetime.now(),
            supporting_factors=supporting_factors,
        )

    def _predict_using_linear_trend(
        self,
        values: list[float],
        time_intervals: list[float],
        forecast_hours: float,
    ) -> tuple[float, float]:
        """Predict using linear trend extrapolation"""
        if len(values) < 2:
            return values[0] if values else 0.5, 0.3

        # Simple linear regression
        x = (
            np.cumsum([0] + time_intervals[:-1])
            if time_intervals
            else np.arange(len(values))
        )
        y = np.array(values)

        if len(x) != len(y):
            x = np.arange(len(y))

        # Calculate slope and intercept
        if len(x) > 1:
            slope = (
                np.corrcoef(x, y)[0, 1] * (np.std(y) / np.std(x))
                if np.std(x) > 0
                else 0
            )
            intercept = np.mean(y) - slope * np.mean(x)
        else:
            slope = 0
            intercept = y[0]

        # Predict future value
        future_x = x[-1] + forecast_hours
        predicted_value = slope * future_x + intercept

        # Calculate confidence based on R-squared
        if len(values) > 2:
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            confidence = max(0.1, min(0.9, r_squared))
        else:
            confidence = 0.5

        return max(0.0, min(1.0, predicted_value)), confidence

    def _exponential_smoothing(self, values: list[float], alpha: float = 0.3) -> float:
        """Apply exponential smoothing to predict next value"""
        if not values:
            return 0.0

        if len(values) == 1:
            return values[0]

        # Initialize with first value
        smoothed = values[0]

        # Apply exponential smoothing
        for value in values[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed

        return smoothed

    def _analyze_momentum_factors(
        self,
        momentum_values: list[float],
        time_intervals: list[float],
    ) -> list[str]:
        """Analyze factors affecting momentum prediction"""
        factors = []

        if len(momentum_values) >= 3:
            recent_trend = momentum_values[-1] - momentum_values[-3]
            if recent_trend > 0.1:
                factors.append("Strong positive momentum trend")
            elif recent_trend < -0.1:
                factors.append("Declining momentum trend")
            else:
                factors.append("Stable momentum")

        # Volatility analysis
        if len(momentum_values) > 1:
            volatility = statistics.stdev(momentum_values)
            if volatility > 0.2:
                factors.append("High momentum volatility")
            else:
                factors.append("Stable momentum pattern")

        # Acceleration analysis
        if len(momentum_values) >= 3:
            acceleration = (momentum_values[-1] - momentum_values[-2]) - (
                momentum_values[-2] - momentum_values[-3]
            )
            if abs(acceleration) > 0.05:
                factors.append(f"Momentum acceleration: {acceleration:.3f}")

        return factors

    def _analyze_lifecycle_changes(
        self,
        trend_history: list[TrendSignal],
    ) -> list[tuple[TrendLifecycle, TrendLifecycle]]:
        """Analyze historical lifecycle stage changes"""
        changes = []
        for i in range(1, len(trend_history)):
            prev_stage = trend_history[i - 1].lifecycle_stage
            curr_stage = trend_history[i].lifecycle_stage
            if prev_stage != curr_stage:
                changes.append((prev_stage, curr_stage))

        return changes

    def _calculate_momentum_trend(self, trend_history: list[TrendSignal]) -> float:
        """Calculate overall momentum trend direction"""
        if len(trend_history) < 2:
            return 0.0

        momentum_values = [t.momentum for t in trend_history]

        # Simple linear trend
        x = np.arange(len(momentum_values))
        y = np.array(momentum_values)

        if len(momentum_values) > 1:
            correlation = (
                np.corrcoef(x, y)[0, 1] if not np.isnan(np.corrcoef(x, y)[0, 1]) else 0
            )
            return correlation

        return 0.0

    def _calculate_volume_trend(self, trend_history: list[TrendSignal]) -> float:
        """Calculate overall volume trend direction"""
        if len(trend_history) < 2:
            return 0.0

        volume_values = [t.volume for t in trend_history]

        # Calculate log growth to handle large numbers
        log_volumes = [np.log(max(v, 1)) for v in volume_values]

        x = np.arange(len(log_volumes))
        y = np.array(log_volumes)

        if len(log_volumes) > 1:
            correlation = (
                np.corrcoef(x, y)[0, 1] if not np.isnan(np.corrcoef(x, y)[0, 1]) else 0
            )
            return correlation

        return 0.0

    def _predict_next_lifecycle_stage(
        self,
        current_stage: TrendLifecycle,
        momentum_trend: float,
        volume_trend: float,
        stage_changes: list[tuple[TrendLifecycle, TrendLifecycle]],
    ) -> tuple[TrendLifecycle, float, int]:
        """Predict next lifecycle stage and timing"""
        # Define stage transition probabilities
        transition_matrix = {
            TrendLifecycle.EMERGING: {
                TrendLifecycle.GROWING: 0.7,
                TrendLifecycle.PEAK: 0.2,
                TrendLifecycle.DECLINING: 0.1,
            },
            TrendLifecycle.GROWING: {
                TrendLifecycle.PEAK: 0.6,
                TrendLifecycle.DECLINING: 0.3,
                TrendLifecycle.GROWING: 0.1,
            },
            TrendLifecycle.PEAK: {
                TrendLifecycle.DECLINING: 0.8,
                TrendLifecycle.PEAK: 0.2,
            },
            TrendLifecycle.DECLINING: {
                TrendLifecycle.DORMANT: 0.7,
                TrendLifecycle.DECLINING: 0.3,
            },
            TrendLifecycle.DORMANT: {TrendLifecycle.DORMANT: 1.0},
        }

        base_transitions = transition_matrix.get(current_stage, {})

        if not base_transitions:
            return current_stage, 0.3, 72

        # Adjust probabilities based on trends
        adjusted_transitions = base_transitions.copy()

        # Positive momentum/volume trends favor progression
        if momentum_trend > 0.1 and volume_trend > 0.1:
            # Favor progression to next stage
            if current_stage == TrendLifecycle.EMERGING:
                adjusted_transitions[TrendLifecycle.GROWING] *= 1.3
            elif current_stage == TrendLifecycle.GROWING:
                adjusted_transitions[TrendLifecycle.PEAK] *= 1.2

        # Negative trends favor decline
        elif momentum_trend < -0.1 or volume_trend < -0.1:
            if TrendLifecycle.DECLINING in adjusted_transitions:
                adjusted_transitions[TrendLifecycle.DECLINING] *= 1.5
            if TrendLifecycle.DORMANT in adjusted_transitions:
                adjusted_transitions[TrendLifecycle.DORMANT] *= 1.3

        # Find most likely next stage
        next_stage = max(
            adjusted_transitions.keys(),
            key=lambda k: adjusted_transitions[k],
        )
        confidence = adjusted_transitions[next_stage]

        # Estimate hours to transition
        stage_durations = {
            TrendLifecycle.EMERGING: 48,  # 2 days
            TrendLifecycle.GROWING: 168,  # 1 week
            TrendLifecycle.PEAK: 72,  # 3 days
            TrendLifecycle.DECLINING: 240,  # 10 days
            TrendLifecycle.DORMANT: 720,  # 30 days
        }

        hours_to_transition = stage_durations.get(current_stage, 72)

        # Adjust timing based on trends
        if momentum_trend > 0.2:
            hours_to_transition = int(hours_to_transition * 0.7)  # Faster transition
        elif momentum_trend < -0.2:
            hours_to_transition = int(hours_to_transition * 1.3)  # Slower transition

        return next_stage, confidence, hours_to_transition

    def _lifecycle_to_numeric(self, stage: TrendLifecycle) -> float:
        """Convert lifecycle stage to numeric value for prediction"""
        stage_values = {
            TrendLifecycle.EMERGING: 0.2,
            TrendLifecycle.GROWING: 0.4,
            TrendLifecycle.PEAK: 0.6,
            TrendLifecycle.DECLINING: 0.8,
            TrendLifecycle.DORMANT: 1.0,
        }

        return stage_values.get(stage, 0.5)

    def _calculate_derivative(self, values: list[float]) -> list[float]:
        """Calculate simple derivative (rate of change) for time series"""
        if len(values) < 2:
            return [0.0]

        derivatives = []
        for i in range(1, len(values)):
            derivative = values[i] - values[i - 1]
            derivatives.append(derivative)

        return derivatives

    def _predict_peak_from_trajectories(
        self,
        momentum_trajectory: list[float],
        volume_trajectory: list[float],
        momentum_derivative: list[float],
        volume_derivative: list[float],
    ) -> tuple[float, float]:
        """Predict peak timing from momentum and volume trajectories"""
        # Current momentum and volume
        current_momentum = momentum_trajectory[-1] if momentum_trajectory else 0.5
        current_volume = volume_trajectory[-1] if volume_trajectory else 1000

        # Recent rate of change
        recent_momentum_change = momentum_derivative[-1] if momentum_derivative else 0
        recent_volume_change = volume_derivative[-1] if volume_derivative else 0

        # Simple peak prediction logic
        peak_hours = 72  # Default 3 days

        # If momentum is high and still increasing, peak is further out
        if current_momentum > 0.7 and recent_momentum_change > 0:
            peak_hours = 120  # 5 days

        # If momentum is declining rapidly, peak is soon or passed
        elif recent_momentum_change < -0.1:
            peak_hours = 12  # 12 hours

        # If momentum is very high but stable, peak is imminent
        elif current_momentum > 0.8 and abs(recent_momentum_change) < 0.05:
            peak_hours = 24  # 1 day

        # Confidence based on trend clarity
        trend_clarity = (
            1.0 - abs(recent_momentum_change) if recent_momentum_change else 0.5
        )
        confidence = max(0.3, min(0.8, trend_clarity))

        return peak_hours, confidence

    def _adjust_peak_prediction_with_correlations(
        self,
        base_prediction_hours: float,
        correlations: list[TrendCorrelation],
    ) -> float:
        """Adjust peak prediction using correlation data"""
        if not correlations:
            return base_prediction_hours

        # Look for leading correlations that might predict peak timing
        leading_correlations = [
            corr
            for corr in correlations
            if corr.correlation_type.value == "leading" and corr.is_significant
        ]

        if leading_correlations:
            # Use the strongest correlation to adjust timing
            strongest_corr = max(
                leading_correlations,
                key=lambda c: abs(c.correlation_coefficient),
            )
            time_lag_hours = abs(strongest_corr.time_lag_hours)

            # Adjust prediction based on lag
            adjusted_prediction = base_prediction_hours + time_lag_hours

            # Cap between 1 hour and 30 days
            return max(1, min(720, adjusted_prediction))

        return base_prediction_hours

    def _create_low_confidence_prediction(
        self,
        keyword: str,
        prediction_type: str,
        default_value: float,
        forecast_hours: int,
    ) -> PredictionResult:
        """Create a low-confidence prediction when insufficient data"""
        return PredictionResult(
            trend_keyword=keyword,
            prediction_type=prediction_type,
            predicted_value=default_value,
            confidence=0.3,
            time_horizon_hours=forecast_hours,
            prediction_timestamp=datetime.now(),
            supporting_factors=[
                "Insufficient historical data",
                "Using default prediction",
            ],
        )

    async def batch_predict(
        self,
        trends_data: dict[str, list[TrendSignal]],
        prediction_types: list[str] = None,
    ) -> dict[str, list[PredictionResult]]:
        """Run batch predictions for multiple trends"""
        if prediction_types is None:
            prediction_types = ["momentum", "volume", "lifecycle", "peak_timing"]

        results = {}

        for keyword, trend_history in trends_data.items():
            keyword_results = []

            for pred_type in prediction_types:
                try:
                    if pred_type == "momentum":
                        result = await self.predict_trend_momentum(trend_history)
                    elif pred_type == "volume":
                        result = await self.predict_volume_growth(trend_history)
                    elif pred_type == "lifecycle":
                        result = await self.predict_lifecycle_transition(trend_history)
                    elif pred_type == "peak_timing":
                        result = await self.predict_peak_timing(trend_history)
                    else:
                        continue

                    keyword_results.append(result)

                except Exception as e:
                    self.logger.error(
                        f"Prediction error for {keyword} ({pred_type}): {e}",
                    )

            results[keyword] = keyword_results

        return results

    def get_model_accuracy(self) -> dict[str, float]:
        """Get accuracy scores for all prediction models"""
        accuracy_summary = {}

        for model_name, model in self.models.items():
            recent_accuracies = self.accuracy_scores.get(model_name, [])
            if recent_accuracies:
                accuracy_summary[model_name] = statistics.mean(
                    recent_accuracies[-10:],
                )  # Last 10 predictions
            else:
                accuracy_summary[model_name] = model.accuracy_score

        # Overall accuracy
        if accuracy_summary:
            accuracy_summary["overall"] = statistics.mean(accuracy_summary.values())
        else:
            accuracy_summary["overall"] = 0.7

        return accuracy_summary
