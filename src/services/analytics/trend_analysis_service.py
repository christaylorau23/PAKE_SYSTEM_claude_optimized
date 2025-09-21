"""Trend Analysis Service

Provides comprehensive trend analysis including time series decomposition,
seasonality detection, trend forecasting, and trend comparison across metrics.
"""

import logging
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class TrendType(Enum):
    """Types of trends."""

    LINEAR_UP = "linear_up"
    LINEAR_DOWN = "linear_down"
    EXPONENTIAL_UP = "exponential_up"
    EXPONENTIAL_DOWN = "exponential_down"
    LOGARITHMIC = "logarithmic"
    POLYNOMIAL = "polynomial"
    SEASONAL = "seasonal"
    CYCLICAL = "cyclical"
    STATIONARY = "stationary"
    RANDOM_WALK = "random_walk"


class SeasonalityType(Enum):
    """Types of seasonality."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    MULTIPLE = "multiple"
    NONE = "none"


@dataclass
class TrendAnalysisResult:
    """Comprehensive trend analysis result."""

    metric_name: str
    trend_type: TrendType
    trend_strength: float  # 0.0 to 1.0
    trend_direction: str  # "up", "down", "stable"
    trend_slope: float
    trend_r_squared: float
    seasonality_type: SeasonalityType
    seasonality_strength: float
    stationarity_test: dict[str, Any]
    decomposition: dict[str, list[float]]
    confidence_interval: tuple[float, float]
    forecast_horizon: int
    forecast_values: list[float]
    forecast_confidence: list[tuple[float, float]]
    trend_breakpoints: list[int]
    trend_segments: list[dict[str, Any]]


@dataclass
class TrendComparison:
    """Comparison between multiple trends."""

    metrics: list[str]
    trend_directions: dict[str, str]
    trend_strengths: dict[str, float]
    correlation_matrix: np.ndarray
    synchronized_trends: list[tuple[str, str]]
    divergent_trends: list[tuple[str, str]]
    trend_clusters: list[list[str]]


@dataclass
class TrendBreakpoint:
    """Trend breakpoint detection result."""

    breakpoint_index: int
    breakpoint_date: datetime
    confidence: float
    change_magnitude: float
    trend_before: dict[str, Any]
    trend_after: dict[str, Any]


class TrendAnalysisService:
    """Advanced trend analysis service providing comprehensive trend detection,
    decomposition, forecasting, and comparison capabilities.
    """

    def __init__(self):
        """Initialize the trend analysis service."""
        self.trend_models_cache = {}
        self.decomposition_cache = {}

        # Configuration
        self.config = {
            "min_data_points": 10,
            "seasonality_periods": {
                "daily": 24,
                "weekly": 7,
                "monthly": 30,
                "quarterly": 90,
                "yearly": 365,
            },
            "trend_confidence_threshold": 0.7,
            "seasonality_threshold": 0.1,
            "breakpoint_min_segment_length": 5,
            "forecast_horizon_days": 30,
        }

    async def analyze_trend(
        self,
        metric_name: str,
        time_range: str = "24h",
        time_series: list[tuple[datetime, float]] | None = None,
        include_forecast: bool = True,
        detect_breakpoints: bool = True,
    ) -> TrendAnalysisResult:
        """Perform comprehensive trend analysis on a time series.

        Args:
            metric_name: Name of the metric being analyzed
            time_range: Time range for analysis (e.g., "24h", "7d")
            time_series: Optional list of (timestamp, value) tuples.
                If None, generates mock data
            include_forecast: Whether to include trend forecasting
            detect_breakpoints: Whether to detect trend breakpoints

        Returns:
            Comprehensive trend analysis result
        """
        try:
            # Generate mock data if no time series provided
            if time_series is None:
                time_series = await self._generate_mock_time_series(
                    metric_name,
                    time_range,
                )

            if len(time_series) < self.config["min_data_points"]:
                raise ValueError(
                    f"Insufficient data: {len(time_series)} < "
                    f"{self.config['min_data_points']}",
                )

            # Convert to pandas DataFrame
            df = pd.DataFrame(time_series, columns=["timestamp", "value"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

            # Handle missing values
            df["value"] = df["value"].interpolate(method="linear")

            # Perform trend analysis
            (
                trend_type,
                trend_strength,
                trend_direction,
                trend_slope,
                r_squared,
            ) = await self._detect_trend_type(df["value"])

            # Detect seasonality
            seasonality_type, seasonality_strength = await self._detect_seasonality(
                df["value"],
            )

            # Perform time series decomposition
            decomposition = await self._decompose_time_series(
                df["value"],
                seasonality_type,
            )

            # Test for stationarity
            stationarity_test = await self._test_stationarity(df["value"])

            # Detect breakpoints if requested
            trend_breakpoints = []
            trend_segments = []
            if detect_breakpoints:
                breakpoints, segments = await self._detect_trend_breakpoints(
                    df["value"],
                )
                trend_breakpoints = breakpoints
                trend_segments = segments

            # Generate forecast if requested
            forecast_values = []
            forecast_confidence = []
            if include_forecast:
                forecast_values, forecast_confidence = await self._forecast_trend(
                    df["value"],
                    trend_type,
                    self.config["forecast_horizon_days"],
                )

            # Calculate confidence interval for trend
            trend_ci = await self._calculate_trend_confidence_interval(
                df["value"],
                trend_slope,
                trend_strength,
            )

            return TrendAnalysisResult(
                metric_name=metric_name,
                trend_type=trend_type,
                trend_strength=trend_strength,
                trend_direction=trend_direction,
                trend_slope=trend_slope,
                trend_r_squared=r_squared,
                seasonality_type=seasonality_type,
                seasonality_strength=seasonality_strength,
                stationarity_test=stationarity_test,
                decomposition=decomposition,
                confidence_interval=trend_ci,
                forecast_horizon=self.config["forecast_horizon_days"],
                forecast_values=forecast_values,
                forecast_confidence=forecast_confidence,
                trend_breakpoints=trend_breakpoints,
                trend_segments=trend_segments,
            )

        except Exception as e:
            logger.error(f"Trend analysis failed for {metric_name}: {e}")
            # Return empty result on error
            return TrendAnalysisResult(
                metric_name=metric_name,
                trend_type=TrendType.STATIONARY,
                trend_strength=0.0,
                trend_direction="unknown",
                trend_slope=0.0,
                trend_r_squared=0.0,
                seasonality_type=SeasonalityType.NONE,
                seasonality_strength=0.0,
                stationarity_test={},
                decomposition={},
                confidence_interval=(0.0, 0.0),
                forecast_horizon=0,
                forecast_values=[],
                forecast_confidence=[],
                trend_breakpoints=[],
                trend_segments=[],
            )

    async def _detect_trend_type(
        self,
        series: pd.Series,
    ) -> tuple[TrendType, float, str, float, float]:
        """Detect the type of trend in the time series."""
        try:
            values = series.values
            n = len(values)

            if n < 3:
                return TrendType.STATIONARY, 0.0, "unknown", 0.0, 0.0

            # Test different trend models
            trend_models = {
                TrendType.LINEAR_UP: self._fit_linear_trend,
                TrendType.LINEAR_DOWN: self._fit_linear_trend,
                TrendType.EXPONENTIAL_UP: self._fit_exponential_trend,
                TrendType.EXPONENTIAL_DOWN: self._fit_exponential_trend,
                TrendType.LOGARITHMIC: self._fit_logarithmic_trend,
                TrendType.POLYNOMIAL: self._fit_polynomial_trend,
            }

            best_model = TrendType.STATIONARY
            best_r_squared = 0.0
            best_slope = 0.0

            for trend_type, fit_function in trend_models.items():
                try:
                    r_squared, slope = await fit_function(values)

                    if r_squared > best_r_squared:
                        best_r_squared = r_squared
                        best_slope = slope
                        best_model = trend_type

                except Exception as e:
                    logger.debug(f"Trend model {trend_type} failed: {e}")
                    continue

            # Determine trend direction and strength
            if best_r_squared > self.config["trend_confidence_threshold"]:
                if best_slope > 0:
                    trend_direction = "up"
                    if best_model == TrendType.LINEAR_UP:
                        best_model = TrendType.LINEAR_UP
                    elif best_model == TrendType.EXPONENTIAL_UP:
                        best_model = TrendType.EXPONENTIAL_UP
                else:
                    trend_direction = "down"
                    if best_model == TrendType.LINEAR_DOWN:
                        best_model = TrendType.LINEAR_DOWN
                    elif best_model == TrendType.EXPONENTIAL_DOWN:
                        best_model = TrendType.EXPONENTIAL_DOWN
            else:
                trend_direction = "stable"
                best_model = TrendType.STATIONARY

            trend_strength = min(best_r_squared, 1.0)

            return (
                best_model,
                trend_strength,
                trend_direction,
                best_slope,
                best_r_squared,
            )

        except Exception as e:
            logger.error(f"Trend type detection failed: {e}")
            return TrendType.STATIONARY, 0.0, "unknown", 0.0, 0.0

    async def _fit_linear_trend(self, values: np.ndarray) -> tuple[float, float]:
        """Fit linear trend model."""
        try:
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)

            # Calculate R-squared
            y_pred = slope * x + intercept
            ss_res = np.sum((values - y_pred) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            return max(r_squared, 0), slope

        except Exception as e:
            logger.error(f"Linear trend fitting failed: {e}")
            return 0.0, 0.0

    async def _fit_exponential_trend(self, values: np.ndarray) -> tuple[float, float]:
        """Fit exponential trend model."""
        try:
            # Ensure all values are positive for exponential fitting
            if np.any(values <= 0):
                values = values - np.min(values) + 1

            x = np.arange(len(values))
            log_values = np.log(values)

            slope, intercept = np.polyfit(x, log_values, 1)

            # Calculate R-squared
            y_pred = np.exp(intercept + slope * x)
            ss_res = np.sum((values - y_pred) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            return max(r_squared, 0), slope

        except Exception as e:
            logger.error(f"Exponential trend fitting failed: {e}")
            return 0.0, 0.0

    async def _fit_logarithmic_trend(self, values: np.ndarray) -> tuple[float, float]:
        """Fit logarithmic trend model."""
        try:
            x = np.arange(len(values))
            # Ensure x values are positive for log fitting
            x_log = x + 1

            slope, intercept = np.polyfit(np.log(x_log), values, 1)

            # Calculate R-squared
            y_pred = intercept + slope * np.log(x_log)
            ss_res = np.sum((values - y_pred) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            return max(r_squared, 0), slope

        except Exception as e:
            logger.error(f"Logarithmic trend fitting failed: {e}")
            return 0.0, 0.0

    async def _fit_polynomial_trend(self, values: np.ndarray) -> tuple[float, float]:
        """Fit polynomial trend model (degree 2)."""
        try:
            x = np.arange(len(values))

            # Fit polynomial of degree 2
            coeffs = np.polyfit(x, values, 2)

            # Calculate R-squared
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((values - y_pred) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            # Use the linear coefficient as slope
            slope = coeffs[-2] if len(coeffs) > 1 else 0

            return max(r_squared, 0), slope

        except Exception as e:
            logger.error(f"Polynomial trend fitting failed: {e}")
            return 0.0, 0.0

    async def _detect_seasonality(
        self,
        series: pd.Series,
    ) -> tuple[SeasonalityType, float]:
        """Detect seasonality in the time series."""
        try:
            values = series.values
            n = len(values)

            if n < 24:  # Need at least 24 data points for seasonality detection
                return SeasonalityType.NONE, 0.0

            seasonality_scores = {}

            # Test different seasonal periods
            for period_name, period_length in self.config[
                "seasonality_periods"
            ].items():
                if n >= period_length * 2:  # Need at least 2 full periods
                    score = await self._calculate_seasonality_score(
                        values,
                        period_length,
                    )
                    seasonality_scores[period_name] = score

            if not seasonality_scores:
                return SeasonalityType.NONE, 0.0

            # Find the strongest seasonality
            best_period = max(seasonality_scores, key=seasonality_scores.get)
            best_score = seasonality_scores[best_period]

            # Check if multiple seasonalities exist
            significant_periods = [
                period
                for period, score in seasonality_scores.items()
                if score > self.config["seasonality_threshold"]
            ]

            if len(significant_periods) > 1:
                seasonality_type = SeasonalityType.MULTIPLE
            elif best_score > self.config["seasonality_threshold"]:
                seasonality_type = SeasonalityType(best_period.upper())
            else:
                seasonality_type = SeasonalityType.NONE

            return seasonality_type, best_score

        except Exception as e:
            logger.error(f"Seasonality detection failed: {e}")
            return SeasonalityType.NONE, 0.0

    async def _calculate_seasonality_score(
        self,
        values: np.ndarray,
        period: int,
    ) -> float:
        """Calculate seasonality score for a given period."""
        try:
            n = len(values)
            if n < period * 2:
                return 0.0

            # Calculate seasonal means
            seasonal_means = []
            for i in range(period):
                seasonal_values = values[i::period]
                if len(seasonal_values) > 0:
                    seasonal_means.append(np.mean(seasonal_values))

            if len(seasonal_means) < 2:
                return 0.0

            # Calculate coefficient of variation of seasonal means
            seasonal_std = np.std(seasonal_means)
            seasonal_mean = np.mean(seasonal_means)

            if seasonal_mean == 0:
                return 0.0

            cv = seasonal_std / seasonal_mean

            # Normalize to 0-1 scale
            score = min(cv, 1.0)

            return score

        except Exception as e:
            logger.error(f"Seasonality score calculation failed: {e}")
            return 0.0

    async def _decompose_time_series(
        self,
        series: pd.Series,
        seasonality_type: SeasonalityType,
    ) -> dict[str, list[float]]:
        """Decompose time series into trend, seasonal, and residual components."""
        try:
            values = series.values
            n = len(values)

            if n < 12:  # Need sufficient data for decomposition
                return {
                    "trend": values.tolist(),
                    "seasonal": [0.0] * n,
                    "residual": [0.0] * n,
                }

            # Determine seasonal period
            seasonal_period = None
            if seasonality_type != SeasonalityType.NONE:
                period_map = {
                    SeasonalityType.DAILY: 24,
                    SeasonalityType.WEEKLY: 7,
                    SeasonalityType.MONTHLY: 30,
                    SeasonalityType.QUARTERLY: 90,
                    SeasonalityType.YEARLY: 365,
                }
                seasonal_period = period_map.get(seasonality_type, min(12, n // 2))

            # Perform decomposition
            if seasonal_period and n >= seasonal_period * 2:
                try:
                    decomposition = seasonal_decompose(
                        values,
                        model="additive",
                        period=seasonal_period,
                        extrapolate_trend="freq",
                    )

                    return {
                        "trend": decomposition.trend.fillna(0).tolist(),
                        "seasonal": decomposition.seasonal.tolist(),
                        "residual": decomposition.resid.fillna(0).tolist(),
                    }
                except Exception as e:
                    logger.warning(f"Seasonal decomposition failed: {e}")

            # Fallback: simple trend extraction
            # Use moving average for trend
            window_size = min(7, n // 3)
            trend = (
                pd.Series(values)
                .rolling(window=window_size, center=True)
                .mean()
                .fillna(method="bfill")
                .fillna(method="ffill")
            )

            # Residual is original minus trend
            residual = values - trend.values

            return {
                "trend": trend.tolist(),
                "seasonal": [0.0] * n,
                "residual": residual.tolist(),
            }

        except Exception as e:
            logger.error(f"Time series decomposition failed: {e}")
            return {
                "trend": values.tolist(),
                "seasonal": [0.0] * n,
                "residual": [0.0] * n,
            }

    async def _test_stationarity(self, series: pd.Series) -> dict[str, Any]:
        """Test for stationarity using Augmented Dickey-Fuller test."""
        try:
            values = series.values

            if len(values) < 10:
                return {"is_stationary": False, "p_value": 1.0, "test_statistic": 0.0}

            # Perform ADF test
            result = adfuller(values, autolag="AIC")

            return {
                # p-value < 0.05 indicates stationarity
                "is_stationary": result[1] < 0.05,
                "p_value": result[1],
                "test_statistic": result[0],
                "critical_values": result[4],
                "used_lag": result[2],
                "n_observations": result[3],
            }

        except Exception as e:
            logger.error(f"Stationarity test failed: {e}")
            return {"is_stationary": False, "p_value": 1.0, "test_statistic": 0.0}

    async def _detect_trend_breakpoints(
        self,
        series: pd.Series,
    ) -> tuple[list[int], list[dict[str, Any]]]:
        """Detect trend breakpoints in the time series."""
        try:
            values = series.values
            n = len(values)

            if n < self.config["breakpoint_min_segment_length"] * 2:
                return [], []

            breakpoints = []
            segments = []

            # Simple breakpoint detection using rolling regression
            window_size = self.config["breakpoint_min_segment_length"]

            slopes = []
            for i in range(window_size, n - window_size):
                # Calculate slope for segments before and after
                before_slope = np.polyfit(
                    range(window_size),
                    values[i - window_size : i],
                    1,
                )[0]
                after_slope = np.polyfit(
                    range(window_size),
                    values[i : i + window_size],
                    1,
                )[0]

                # Check for significant change in slope
                slope_change = abs(after_slope - before_slope)
                slopes.append(slope_change)

            if slopes:
                # Find points with significant slope changes
                threshold = np.mean(slopes) + 2 * np.std(slopes)

                for i, slope_change in enumerate(slopes):
                    if slope_change > threshold:
                        breakpoint_idx = i + window_size
                        breakpoints.append(breakpoint_idx)

                        # Analyze segments
                        if breakpoints:
                            start_idx = breakpoints[-2] if len(breakpoints) > 1 else 0
                            end_idx = breakpoint_idx

                            segment_values = values[start_idx:end_idx]
                            if len(segment_values) >= 3:
                                segment_slope = np.polyfit(
                                    range(len(segment_values)),
                                    segment_values,
                                    1,
                                )[0]
                                segments.append(
                                    {
                                        "start_index": start_idx,
                                        "end_index": end_idx,
                                        "slope": segment_slope,
                                        "length": len(segment_values),
                                    },
                                )

            # Add final segment
            if breakpoints:
                start_idx = breakpoints[-1]
                end_idx = n
                segment_values = values[start_idx:end_idx]
                if len(segment_values) >= 3:
                    segment_slope = np.polyfit(
                        range(len(segment_values)),
                        segment_values,
                        1,
                    )[0]
                    segments.append(
                        {
                            "start_index": start_idx,
                            "end_index": end_idx,
                            "slope": segment_slope,
                            "length": len(segment_values),
                        },
                    )

            return breakpoints, segments

        except Exception as e:
            logger.error(f"Breakpoint detection failed: {e}")
            return [], []

    async def _forecast_trend(
        self,
        series: pd.Series,
        trend_type: TrendType,
        horizon: int,
    ) -> tuple[list[float], list[tuple[float, float]]]:
        """Forecast trend into the future."""
        try:
            values = series.values
            n = len(values)

            if n < 3:
                return [], []

            forecast_values = []
            forecast_confidence = []

            # Simple linear trend forecast
            x = np.arange(n)
            slope, intercept = np.polyfit(x, values, 1)

            # Generate forecasts
            for i in range(1, horizon + 1):
                forecast_value = slope * (n + i - 1) + intercept
                forecast_values.append(forecast_value)

                # Simple confidence interval (using residual standard error)
                residuals = values - (slope * x + intercept)
                residual_std = np.std(residuals)

                # 95% confidence interval
                margin = 1.96 * residual_std
                forecast_confidence.append(
                    (forecast_value - margin, forecast_value + margin),
                )

            return forecast_values, forecast_confidence

        except Exception as e:
            logger.error(f"Trend forecasting failed: {e}")
            return [], []

    async def _calculate_trend_confidence_interval(
        self,
        series: pd.Series,
        slope: float,
        strength: float,
    ) -> tuple[float, float]:
        """Calculate confidence interval for trend slope."""
        try:
            values = series.values
            n = len(values)

            if n < 3:
                return (0.0, 0.0)

            # Calculate standard error of slope
            x = np.arange(n)
            residuals = values - (slope * x + np.mean(values))
            residual_std = np.std(residuals)

            # Standard error of slope
            x_mean = np.mean(x)
            slope_se = residual_std / np.sqrt(np.sum((x - x_mean) ** 2))

            # 95% confidence interval
            margin = 1.96 * slope_se

            return (slope - margin, slope + margin)

        except Exception as e:
            logger.error(f"Trend confidence interval calculation failed: {e}")
            return (0.0, 0.0)

    async def _generate_mock_time_series(
        self,
        metric_name: str,
        time_range: str,
    ) -> list[tuple[datetime, float]]:
        """Generate mock time series data for testing and demonstration."""
        try:
            # Parse time range
            time_range_hours = self._parse_time_range(time_range)

            # Generate timestamps
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=time_range_hours)

            # Generate data points (one per hour)
            time_series = []
            current_time = start_time

            # Base values for different metrics
            base_values = {
                "response_time": 100,
                "throughput": 1000,
                "error_rate": 0.01,
                "cache_hit_rate": 0.95,
            }

            base_value = base_values.get(metric_name, 100)

            # Generate trend and noise
            trend_slope = np.random.uniform(-0.1, 0.1)  # Small trend
            noise_level = base_value * 0.1  # 10% noise

            hour = 0
            while current_time <= end_time:
                # Add trend and noise
                value = (
                    base_value + trend_slope * hour + np.random.normal(0, noise_level)
                )

                # Ensure positive values for certain metrics
                if metric_name in ["response_time", "throughput"]:
                    value = max(value, 1)
                elif metric_name in ["error_rate", "cache_hit_rate"]:
                    value = max(0, min(1, value))

                time_series.append((current_time, value))
                current_time += timedelta(hours=1)
                hour += 1

            return time_series

        except Exception as e:
            logger.error(f"Mock time series generation failed: {e}")
            # Return minimal data
            return [(datetime.now(), 100.0)]

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours."""
        try:
            if time_range.endswith("h"):
                return int(time_range[:-1])
            if time_range.endswith("d"):
                return int(time_range[:-1]) * 24
            if time_range.endswith("w"):
                return int(time_range[:-1]) * 24 * 7
            return 24  # Default to 24 hours
        except Exception:
            return 24

    async def compare_trends(
        self,
        trend_results: list[TrendAnalysisResult],
    ) -> TrendComparison:
        """Compare trends across multiple metrics."""
        try:
            if len(trend_results) < 2:
                return TrendComparison(
                    metrics=[],
                    trend_directions={},
                    trend_strengths={},
                    correlation_matrix=np.array([]),
                    synchronized_trends=[],
                    divergent_trends=[],
                    trend_clusters=[],
                )

            metrics = [result.metric_name for result in trend_results]
            trend_directions = {
                result.metric_name: result.trend_direction for result in trend_results
            }
            trend_strengths = {
                result.metric_name: result.trend_strength for result in trend_results
            }

            # Create correlation matrix based on trend similarities
            n_metrics = len(metrics)
            correlation_matrix = np.zeros((n_metrics, n_metrics))

            for i in range(n_metrics):
                for j in range(n_metrics):
                    if i == j:
                        correlation_matrix[i, j] = 1.0
                    else:
                        # Calculate trend similarity
                        similarity = await self._calculate_trend_similarity(
                            trend_results[i],
                            trend_results[j],
                        )
                        correlation_matrix[i, j] = similarity

            # Find synchronized and divergent trends
            synchronized_trends = []
            divergent_trends = []

            for i in range(n_metrics):
                for j in range(i + 1, n_metrics):
                    metric_a = metrics[i]
                    metric_b = metrics[j]

                    if correlation_matrix[i, j] > 0.7:
                        synchronized_trends.append((metric_a, metric_b))
                    elif correlation_matrix[i, j] < -0.7:
                        divergent_trends.append((metric_a, metric_b))

            # Cluster trends
            trend_clusters = await self._cluster_trends(
                trend_results,
                correlation_matrix,
            )

            return TrendComparison(
                metrics=metrics,
                trend_directions=trend_directions,
                trend_strengths=trend_strengths,
                correlation_matrix=correlation_matrix,
                synchronized_trends=synchronized_trends,
                divergent_trends=divergent_trends,
                trend_clusters=trend_clusters,
            )

        except Exception as e:
            logger.error(f"Trend comparison failed: {e}")
            return TrendComparison(
                metrics=[],
                trend_directions={},
                trend_strengths={},
                correlation_matrix=np.array([]),
                synchronized_trends=[],
                divergent_trends=[],
                trend_clusters=[],
            )

    async def _calculate_trend_similarity(
        self,
        result_a: TrendAnalysisResult,
        result_b: TrendAnalysisResult,
    ) -> float:
        """Calculate similarity between two trend results."""
        try:
            # Direction similarity
            direction_similarity = (
                1.0 if result_a.trend_direction == result_b.trend_direction else -1.0
            )

            # Strength similarity
            strength_diff = abs(result_a.trend_strength - result_b.trend_strength)
            strength_similarity = 1.0 - strength_diff

            # Type similarity
            type_similarity = 1.0 if result_a.trend_type == result_b.trend_type else 0.5

            # Combined similarity
            similarity = (
                direction_similarity * 0.5
                + strength_similarity * 0.3
                + type_similarity * 0.2
            )

            return similarity

        except Exception as e:
            logger.error(f"Trend similarity calculation failed: {e}")
            return 0.0

    async def _cluster_trends(
        self,
        trend_results: list[TrendAnalysisResult],
        correlation_matrix: np.ndarray,
    ) -> list[list[str]]:
        """Cluster trends based on similarity."""
        try:
            if len(trend_results) < 2:
                return [[result.metric_name] for result in trend_results]

            # Use K-means clustering on trend features
            features = []
            for result in trend_results:
                # Create feature vector: [direction, strength, type]
                direction_feature = (
                    1.0
                    if result.trend_direction == "up"
                    else (-1.0 if result.trend_direction == "down" else 0.0)
                )
                features.append(
                    [
                        direction_feature,
                        result.trend_strength,
                        hash(result.trend_type.value) % 10,
                    ],
                )

            features = np.array(features)

            # Determine number of clusters
            n_clusters = min(3, len(trend_results))

            if n_clusters < 2:
                return [[result.metric_name] for result in trend_results]

            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(features)

            # Group metrics by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[label].append(trend_results[i].metric_name)

            return list(clusters.values())

        except Exception as e:
            logger.error(f"Trend clustering failed: {e}")
            return [[result.metric_name] for result in trend_results]

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the trend analysis service."""
        try:
            # Test basic functionality
            test_data = [
                (datetime.now() - timedelta(days=i), 10 + i + np.random.normal(0, 1))
                for i in range(20, 0, -1)
            ]

            result = await self.analyze_trend(
                "test_metric",
                time_series=test_data,
                include_forecast=False,
            )

            return {
                "status": "healthy",
                "trend_types_supported": len(TrendType),
                "seasonality_types_supported": len(SeasonalityType),
                "test_trend_analysis_success": result.trend_strength > 0,
                "cache_size": len(self.trend_models_cache),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "trend_types_supported": 0,
                "seasonality_types_supported": 0,
                "test_trend_analysis_success": False,
            }


# Singleton instance
_trend_service = None


def get_trend_analysis_service() -> TrendAnalysisService:
    """Get or create trend analysis service singleton."""
    global _trend_service
    if _trend_service is None:
        _trend_service = TrendAnalysisService()
    return _trend_service
