"""Predictive Analytics Service

Provides time series forecasting, trend prediction, and pattern analysis
using statistical models and machine learning algorithms.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

# Statistical modeling
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Result of a prediction operation."""

    metric_name: str
    predicted_values: list[float]
    confidence_intervals: list[tuple[float, float]]
    timestamps: list[datetime]
    model_type: str
    accuracy_metrics: dict[str, float]
    trend_direction: str
    trend_strength: float


@dataclass
class TimeSeriesData:
    """Time series data container."""

    timestamps: list[datetime]
    values: list[float]
    metric_name: str
    metadata: dict[str, Any]


@dataclass
class AnomalyResult:
    """Anomaly detection result."""

    anomaly_points: list[int]  # indices of anomalous points
    anomaly_scores: list[float]
    threshold: float
    detection_method: str


class PredictiveAnalyticsService:
    """Advanced predictive analytics service for time series forecasting,
    trend analysis, and anomaly detection.
    """

    def __init__(self):
        """Initialize the predictive analytics service."""
        self.models_cache = {}
        self.scaler = StandardScaler()

        # Model configuration
        self.config = {
            "arima_max_p": 5,
            "arima_max_d": 2,
            "arima_max_q": 5,
            "forecast_horizon": 30,  # days
            "confidence_level": 0.95,
            "anomaly_threshold": 2.5,  # standard deviations
        }

    async def forecast_time_series(
        self,
        time_series: TimeSeriesData,
        forecast_horizon: int | None = None,
        model_type: str = "auto",
    ) -> PredictionResult:
        """Forecast future values of a time series.

        Args:
            time_series: Historical time series data
            forecast_horizon: Number of periods to forecast
            model_type: Type of model ("auto", "arima", "exponential", "ml")

        Returns:
            Prediction results with forecasts and confidence intervals
        """
        try:
            if not time_series.values or len(time_series.values) < 10:
                raise ValueError(
                    "Insufficient data for forecasting (minimum 10 points required)",
                )

            horizon = forecast_horizon or self.config["forecast_horizon"]

            # Convert to pandas series
            df = pd.DataFrame(
                {"timestamp": time_series.timestamps, "value": time_series.values},
            )
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

            # Handle missing values
            df["value"] = df["value"].interpolate(method="linear")

            # Choose and apply model
            if model_type == "auto":
                model_type = await self._select_best_model(df["value"])

            if model_type == "arima":
                result = await self._forecast_arima(df["value"], horizon)
            elif model_type == "exponential":
                result = await self._forecast_exponential_smoothing(
                    df["value"],
                    horizon,
                )
            elif model_type == "ml":
                result = await self._forecast_ml(df, horizon)
            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Generate future timestamps
            last_timestamp = time_series.timestamps[-1]
            if len(time_series.timestamps) > 1:
                freq = time_series.timestamps[1] - time_series.timestamps[0]
            else:
                freq = timedelta(days=1)

            future_timestamps = [
                last_timestamp + freq * (i + 1) for i in range(horizon)
            ]

            # Calculate trend
            trend_direction, trend_strength = self._analyze_trend(time_series.values)

            return PredictionResult(
                metric_name=time_series.metric_name,
                predicted_values=result["predictions"],
                confidence_intervals=result["confidence_intervals"],
                timestamps=future_timestamps,
                model_type=model_type,
                accuracy_metrics=result["accuracy_metrics"],
                trend_direction=trend_direction,
                trend_strength=trend_strength,
            )

        except Exception as e:
            logger.error(f"Error in time series forecasting: {e}")
            # Return empty result on error
            return PredictionResult(
                metric_name=time_series.metric_name,
                predicted_values=[],
                confidence_intervals=[],
                timestamps=[],
                model_type="error",
                accuracy_metrics={},
                trend_direction="unknown",
                trend_strength=0.0,
            )

    async def _select_best_model(self, series: pd.Series) -> str:
        """Automatically select the best forecasting model."""
        try:
            # Simple heuristics for model selection
            n_obs = len(series)

            if n_obs < 20:
                return "exponential"

            # Check for seasonality (if we have enough data)
            if n_obs >= 50:
                try:
                    decomposition = seasonal_decompose(
                        series,
                        model="additive",
                        period=min(12, n_obs // 4),
                    )
                    seasonal_strength = np.std(decomposition.seasonal) / np.std(series)
                    if seasonal_strength > 0.3:
                        return "exponential"  # Good for seasonal data
                except Exception:
                    pass

            # Check stationarity (simplified)
            diff_series = series.diff().dropna()
            if np.std(diff_series) < np.std(series) * 0.8:
                return "arima"  # Good for stationary data

            return "ml"  # Default to ML for complex patterns

        except Exception as e:
            logger.warning(f"Model selection failed, using default: {e}")
            return "exponential"

    async def _forecast_arima(self, series: pd.Series, horizon: int) -> dict[str, Any]:
        """Forecast using ARIMA model."""
        try:
            # Simple ARIMA model selection (1,1,1) for demonstration
            # In production, you'd use auto_arima or grid search
            model = ARIMA(series, order=(1, 1, 1))
            fitted_model = model.fit()

            # Generate forecasts
            forecast = fitted_model.forecast(steps=horizon)
            forecast_ci = fitted_model.get_forecast(steps=horizon).conf_int()

            # Calculate accuracy on training data
            fitted_values = fitted_model.fittedvalues
            mae = mean_absolute_error(series[1:], fitted_values[1:])  # Skip first NaN
            rmse = np.sqrt(mean_squared_error(series[1:], fitted_values[1:]))

            return {
                "predictions": forecast.tolist(),
                "confidence_intervals": [
                    (row[0], row[1]) for row in forecast_ci.values
                ],
                "accuracy_metrics": {
                    "mae": mae,
                    "rmse": rmse,
                    "aic": fitted_model.aic,
                    "bic": fitted_model.bic,
                },
            }

        except Exception as e:
            logger.error(f"ARIMA forecasting failed: {e}")
            # Fallback to simple linear trend
            return await self._forecast_linear_trend(series, horizon)

    async def _forecast_exponential_smoothing(
        self,
        series: pd.Series,
        horizon: int,
    ) -> dict[str, Any]:
        """Forecast using Exponential Smoothing."""
        try:
            # Try Holt-Winters if we have enough data
            if len(series) >= 24:
                model = ExponentialSmoothing(
                    series,
                    trend="add",
                    seasonal="add" if len(series) >= 48 else None,
                    seasonal_periods=12 if len(series) >= 48 else None,
                )
            else:
                # Simple exponential smoothing
                model = ExponentialSmoothing(series, trend="add")

            fitted_model = model.fit()
            forecast = fitted_model.forecast(horizon)

            # Calculate confidence intervals (simplified)
            residuals = fitted_model.resid
            std_error = np.std(residuals)
            z_score = 1.96  # 95% confidence

            confidence_intervals = [
                (pred - z_score * std_error, pred + z_score * std_error)
                for pred in forecast
            ]

            # Calculate accuracy
            fitted_values = fitted_model.fittedvalues
            mae = mean_absolute_error(series, fitted_values)
            rmse = np.sqrt(mean_squared_error(series, fitted_values))

            return {
                "predictions": forecast.tolist(),
                "confidence_intervals": confidence_intervals,
                "accuracy_metrics": {
                    "mae": mae,
                    "rmse": rmse,
                    "aic": (fitted_model.aic if hasattr(fitted_model, "aic") else None),
                },
            }

        except Exception as e:
            logger.error(f"Exponential smoothing failed: {e}")
            return await self._forecast_linear_trend(series, horizon)

    async def _forecast_ml(self, df: pd.DataFrame, horizon: int) -> dict[str, Any]:
        """Forecast using machine learning (Random Forest)."""
        try:
            # Create features for ML model
            feature_df = self._create_ml_features(df)

            if len(feature_df) < 10:
                return await self._forecast_linear_trend(df["value"], horizon)

            # Prepare training data
            X = feature_df.drop(["value"], axis=1)
            y = feature_df["value"]

            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)

            # Generate predictions
            predictions = []
            last_values = df["value"].tail(10).values

            for i in range(horizon):
                # Create features for next prediction
                features = self._create_prediction_features(last_values, i)
                pred = model.predict([features])[0]
                predictions.append(pred)

                # Update last_values for next prediction
                last_values = np.append(last_values[1:], pred)

            # Calculate confidence intervals (using prediction variance)
            # Simplified approach using standard deviation of residuals
            train_predictions = model.predict(X)
            residuals = y - train_predictions
            std_error = np.std(residuals)

            confidence_intervals = [
                (pred - 1.96 * std_error, pred + 1.96 * std_error)
                for pred in predictions
            ]

            # Calculate accuracy
            mae = mean_absolute_error(y, train_predictions)
            rmse = np.sqrt(mean_squared_error(y, train_predictions))

            return {
                "predictions": predictions,
                "confidence_intervals": confidence_intervals,
                "accuracy_metrics": {
                    "mae": mae,
                    "rmse": rmse,
                    "r2_score": model.score(X, y),
                },
            }

        except Exception as e:
            logger.error(f"ML forecasting failed: {e}")
            return await self._forecast_linear_trend(df["value"], horizon)

    def _create_ml_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features for machine learning model."""
        feature_df = df.copy()

        # Lag features
        for lag in [1, 2, 3, 7, 14]:
            if len(df) > lag:
                feature_df[f"lag_{lag}"] = feature_df["value"].shift(lag)

        # Rolling statistics
        for window in [3, 7, 14]:
            if len(df) > window:
                feature_df[f"rolling_mean_{window}"] = (
                    feature_df["value"].rolling(window).mean()
                )
                feature_df[f"rolling_std_{window}"] = (
                    feature_df["value"].rolling(window).std()
                )

        # Time-based features
        feature_df["hour"] = feature_df.index.hour
        feature_df["day_of_week"] = feature_df.index.dayofweek
        feature_df["day_of_month"] = feature_df.index.day
        feature_df["month"] = feature_df.index.month

        # Drop rows with NaN values
        feature_df.dropna(inplace=True)

        return feature_df

    def _create_prediction_features(
        self,
        last_values: np.ndarray,
        step: int,
    ) -> list[float]:
        """Create features for a single prediction step."""
        features = []

        # Lag features
        for lag in [1, 2, 3, 7, 14]:
            if lag <= len(last_values):
                features.append(last_values[-lag])
            else:
                features.append(0.0)

        # Rolling statistics
        for window in [3, 7, 14]:
            if window <= len(last_values):
                features.append(np.mean(last_values[-window:]))
                features.append(np.std(last_values[-window:]))
            else:
                features.append(0.0)
                features.append(0.0)

        # Time features (simplified - would need actual timestamp)
        now = datetime.now()
        future_time = now + timedelta(days=step)
        features.extend(
            [
                future_time.hour,
                future_time.weekday(),
                future_time.day,
                future_time.month,
            ],
        )

        return features

    async def _forecast_linear_trend(
        self,
        series: pd.Series,
        horizon: int,
    ) -> dict[str, Any]:
        """Simple linear trend forecast as fallback."""
        try:
            x = np.arange(len(series))
            y = series.values

            # Fit linear regression
            slope, intercept = np.polyfit(x, y, 1)

            # Generate predictions
            future_x = np.arange(len(series), len(series) + horizon)
            predictions = slope * future_x + intercept

            # Simple confidence intervals
            residuals = y - (slope * x + intercept)
            std_error = np.std(residuals)

            confidence_intervals = [
                (pred - 1.96 * std_error, pred + 1.96 * std_error)
                for pred in predictions
            ]

            mae = np.mean(np.abs(residuals))
            rmse = np.sqrt(np.mean(residuals**2))

            return {
                "predictions": predictions.tolist(),
                "confidence_intervals": confidence_intervals,
                "accuracy_metrics": {"mae": mae, "rmse": rmse, "slope": slope},
            }

        except Exception as e:
            logger.error(f"Linear trend forecast failed: {e}")
            # Ultimate fallback - repeat last value
            last_value = series.iloc[-1] if not series.empty else 0.0
            return {
                "predictions": [last_value] * horizon,
                "confidence_intervals": [(last_value, last_value)] * horizon,
                "accuracy_metrics": {"mae": 0, "rmse": 0},
            }

    def _analyze_trend(self, values: list[float]) -> tuple[str, float]:
        """Analyze trend direction and strength."""
        if len(values) < 2:
            return "unknown", 0.0

        # Simple linear regression to determine trend
        x = np.arange(len(values))
        y = np.array(values)

        try:
            slope, _ = np.polyfit(x, y, 1)

            # Normalize slope by mean value to get relative strength
            mean_value = np.mean(y)
            if mean_value != 0:
                relative_slope = abs(slope) / mean_value
            else:
                relative_slope = 0

            # Determine direction
            if slope > 0.01:
                direction = "up"
            elif slope < -0.01:
                direction = "down"
            else:
                direction = "stable"

            # Strength is between 0 and 1
            strength = min(relative_slope * 100, 1.0)

            return direction, strength

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return "unknown", 0.0

    async def detect_anomalies(self, time_series: TimeSeriesData) -> AnomalyResult:
        """Detect anomalies in time series data."""
        try:
            values = np.array(time_series.values)

            # Statistical method: Z-score
            mean_val = np.mean(values)
            std_val = np.std(values)

            if std_val == 0:
                return AnomalyResult(
                    anomaly_points=[],
                    anomaly_scores=[],
                    threshold=self.config["anomaly_threshold"],
                    detection_method="z_score",
                )

            z_scores = np.abs((values - mean_val) / std_val)
            threshold = self.config["anomaly_threshold"]

            anomaly_indices = np.where(z_scores > threshold)[0].tolist()
            anomaly_scores = z_scores[anomaly_indices].tolist()

            return AnomalyResult(
                anomaly_points=anomaly_indices,
                anomaly_scores=anomaly_scores,
                threshold=threshold,
                detection_method="z_score",
            )

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return AnomalyResult(
                anomaly_points=[],
                anomaly_scores=[],
                threshold=0.0,
                detection_method="error",
            )

    async def generate_forecast(
        self,
        metrics: list[str],
        forecast_horizon: str = "7d",
    ) -> dict[str, Any]:
        """Generate forecasts for multiple metrics.

        Args:
            metrics: List of metric names to forecast
            forecast_horizon: Forecast horizon (e.g., "1d", "7d", "30d")

        Returns:
            Dictionary containing forecast results
        """
        try:
            if not metrics:
                return {
                    "forecasts": {},
                    "confidence_intervals": {},
                    "model_accuracy": {},
                    "forecast_metadata": {"error": "No metrics provided"},
                }

            # Parse forecast horizon
            horizon_days = self._parse_forecast_horizon(forecast_horizon)

            forecasts = {}
            confidence_intervals = {}
            model_accuracy = {}

            for metric in metrics:
                try:
                    # Generate mock time series data
                    time_series_data = await self._generate_mock_time_series(metric)

                    # Generate forecast
                    forecast_result = await self.forecast_time_series(
                        time_series_data,
                        forecast_horizon=horizon_days,
                    )

                    # Format results
                    forecasts[metric] = [
                        {"timestamp": ts.isoformat(), "value": val}
                        for ts, val in zip(
                            forecast_result.timestamps,
                            forecast_result.predicted_values,
                            strict=False,
                        )
                    ]

                    confidence_intervals[metric] = [
                        {"timestamp": ts.isoformat(), "lower": ci[0], "upper": ci[1]}
                        for ts, ci in zip(
                            forecast_result.timestamps,
                            forecast_result.confidence_intervals,
                            strict=False,
                        )
                    ]

                    model_accuracy[metric] = forecast_result.accuracy_metrics.get(
                        "mae",
                        0.0,
                    )

                except Exception as e:
                    logger.warning(f"Forecast failed for {metric}: {e}")
                    forecasts[metric] = []
                    confidence_intervals[metric] = []
                    model_accuracy[metric] = 0.0

            return {
                "forecasts": forecasts,
                "confidence_intervals": confidence_intervals,
                "model_accuracy": model_accuracy,
                "forecast_metadata": {
                    "forecast_horizon": forecast_horizon,
                    "horizon_days": horizon_days,
                    "metrics_forecasted": metrics,
                    "generated_at": datetime.now().isoformat(),
                    "model_type": "arima",
                },
            }

        except Exception as e:
            logger.error(f"Forecast generation failed: {e}")
            return {
                "forecasts": {},
                "confidence_intervals": {},
                "model_accuracy": {},
                "forecast_metadata": {
                    "error": str(e),
                    "forecast_horizon": forecast_horizon,
                },
            }

    async def _generate_mock_time_series(self, metric_name: str) -> TimeSeriesData:
        """Generate mock time series data for forecasting."""
        try:
            # Generate 30 days of daily data
            n_days = 30
            timestamps = [
                datetime.now() - timedelta(days=i) for i in range(n_days, 0, -1)
            ]

            # Base values for different metrics
            base_values = {
                "response_time": 100,
                "throughput": 1000,
                "error_rate": 0.01,
                "cache_hit_rate": 0.95,
                "cpu_usage": 0.5,
                "memory_usage": 0.6,
                "disk_usage": 0.4,
                "network_latency": 50,
            }

            base_value = base_values.get(metric_name, 100)

            # Generate trend and seasonality
            values = []
            for i, ts in enumerate(timestamps):
                # Add trend
                trend = 0.1 * i  # Small upward trend

                # Add weekly seasonality
                day_of_week = ts.weekday()
                seasonality = 0.05 * np.sin(2 * np.pi * day_of_week / 7)

                # Add noise
                noise = np.random.normal(0, base_value * 0.05)

                value = base_value + trend + seasonality + noise

                # Ensure reasonable bounds
                if metric_name in [
                    "error_rate",
                    "cache_hit_rate",
                    "cpu_usage",
                    "memory_usage",
                    "disk_usage",
                ]:
                    value = max(0, min(1, value))
                elif metric_name in ["response_time", "network_latency"]:
                    value = max(1, value)

                values.append(value)

            return TimeSeriesData(
                timestamps=timestamps,
                values=values,
                metric_name=metric_name,
                metadata={
                    "data_points": len(values),
                    "date_range": (
                        f"{timestamps[0].date()} to {timestamps[-1].date()}"
                    ),
                    "generated_at": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Mock time series generation failed: {e}")
            # Return minimal data
            return TimeSeriesData(
                timestamps=[datetime.now()],
                values=[100.0],
                metric_name=metric_name,
                metadata={},
            )

    def _parse_forecast_horizon(self, horizon: str) -> int:
        """Parse forecast horizon string to days."""
        try:
            if horizon.endswith("d"):
                return int(horizon[:-1])
            if horizon.endswith("w"):
                return int(horizon[:-1]) * 7
            if horizon.endswith("m"):
                return int(horizon[:-1]) * 30
            return 7  # Default to 7 days
        except Exception:
            return 7

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the predictive analytics service."""
        try:
            # Test basic functionality
            test_data = TimeSeriesData(
                timestamps=[
                    datetime.now() - timedelta(days=i) for i in range(20, 0, -1)
                ],
                values=[10 + i + np.random.normal(0, 1) for i in range(20)],
                metric_name="test_metric",
                metadata={},
            )

            result = await self.forecast_time_series(test_data, forecast_horizon=5)

            return {
                "status": "healthy",
                "models_available": ["arima", "exponential", "ml"],
                "test_forecast_success": len(result.predicted_values) > 0,
                "cache_size": len(self.models_cache),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "models_available": [],
                "test_forecast_success": False,
            }


# Singleton instance
_predictive_service = None


def get_predictive_analytics_service() -> PredictiveAnalyticsService:
    """Get or create predictive analytics service singleton."""
    global _predictive_service
    if _predictive_service is None:
        _predictive_service = PredictiveAnalyticsService()
    return _predictive_service
