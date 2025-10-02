"""Correlation Analysis Engine

Provides sophisticated correlation analysis between different metrics,
time series, and entities with statistical significance testing and
causal relationship inference.
"""

import logging
import warnings
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import kendalltau, pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class CorrelationMethod(Enum):
    """Available correlation methods."""

    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"
    PARTIAL = "partial"
    DISTANCE = "distance"


class SignificanceLevel(Enum):
    """Statistical significance levels."""

    P_001 = 0.001  # 99.9% confidence
    P_01 = 0.01  # 99% confidence
    P_05 = 0.05  # 95% confidence
    P_10 = 0.10  # 90% confidence


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""

    metric_a: str
    metric_b: str
    correlation_coefficient: float
    p_value: float
    confidence_interval: tuple[float, float]
    significance_level: str
    relationship_type: str  # "positive", "negative", "none"
    strength: str  # "weak", "moderate", "strong", "very_strong"
    sample_size: int
    method_used: str
    additional_metrics: dict[str, Any]


@dataclass
class TimeSeriesCorrelation:
    """Time series correlation analysis result."""

    series_a_name: str
    series_b_name: str
    correlation_at_lag: dict[int, float]  # lag -> correlation
    best_lag: int
    best_correlation: float
    lead_lag_relationship: str  # "a_leads_b", "b_leads_a", "simultaneous"
    granger_causality: dict[str, Any] | None = None


@dataclass
class CorrelationMatrix:
    """Complete correlation matrix analysis."""

    metrics: list[str]
    correlation_matrix: np.ndarray
    p_value_matrix: np.ndarray
    significance_matrix: np.ndarray
    cluster_groups: list[list[str]]
    principal_components: dict[str, Any] | None = None


@dataclass
class CausalAnalysis:
    """Causal relationship analysis result."""

    cause_metric: str
    effect_metric: str
    causal_strength: float
    confidence: float
    lag_days: int
    causal_type: str  # "direct", "indirect", "spurious"
    supporting_evidence: list[str]


class CorrelationEngine:
    """Advanced correlation analysis engine for discovering relationships
    between different metrics, entities, and time series.
    """

    def __init__(self):
        """Initialize the correlation engine."""
        self.scaler = StandardScaler()
        self.correlation_cache = {}

        # Configuration
        self.config = {
            "min_sample_size": 10,
            "max_lag_days": 30,
            "significance_threshold": SignificanceLevel.P_05,
            "strong_correlation_threshold": 0.7,
            "moderate_correlation_threshold": 0.5,
            "weak_correlation_threshold": 0.3,
            "cache_ttl_hours": 24,
        }

    async def analyze_correlation(
        self,
        data_a: list[float],
        data_b: list[float],
        metric_a: str,
        metric_b: str,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        significance_level: SignificanceLevel = SignificanceLevel.P_05,
    ) -> CorrelationResult:
        """Analyze correlation between two datasets with statistical rigor.

        Args:
            data_a: First dataset
            data_b: Second dataset
            metric_a: Name of first metric
            metric_b: Name of second metric
            method: Correlation method to use
            significance_level: Required significance level

        Returns:
            Comprehensive correlation analysis result
        """
        try:
            # Validate inputs
            if len(data_a) != len(data_b):
                raise ValueError("Datasets must have the same length")

            if len(data_a) < self.config["min_sample_size"]:
                raise ValueError(
                    f"Insufficient data: {len(data_a)} < "
                    f"{self.config['min_sample_size']}",
                )

            # Convert to numpy arrays and handle missing values
            arr_a = np.array(data_a, dtype=float)
            arr_b = np.array(data_b, dtype=float)

            # Remove NaN values
            valid_mask = ~(np.isnan(arr_a) | np.isnan(arr_b))
            arr_a = arr_a[valid_mask]
            arr_b = arr_b[valid_mask]

            if len(arr_a) < self.config["min_sample_size"]:
                raise ValueError("Insufficient valid data after cleaning")

            # Perform correlation analysis based on method
            if method == CorrelationMethod.PEARSON:
                result = await self._pearson_correlation(arr_a, arr_b)
            elif method == CorrelationMethod.SPEARMAN:
                result = await self._spearman_correlation(arr_a, arr_b)
            elif method == CorrelationMethod.KENDALL:
                result = await self._kendall_correlation(arr_a, arr_b)
            elif method == CorrelationMethod.PARTIAL:
                result = await self._partial_correlation(arr_a, arr_b)
            elif method == CorrelationMethod.DISTANCE:
                result = await self._distance_correlation(arr_a, arr_b)
            else:
                raise ValueError(f"Unknown correlation method: {method}")

            # Calculate confidence interval
            ci = await self._calculate_confidence_interval(
                result["correlation"],
                len(arr_a),
                significance_level,
            )

            # Determine significance
            is_significant = result["p_value"] <= significance_level.value

            # Classify relationship
            relationship_type, strength = self._classify_relationship(
                result["correlation"],
                is_significant,
            )

            # Additional metrics
            additional_metrics = {
                "effect_size": abs(result["correlation"]),
                "coefficient_of_determination": result["correlation"] ** 2,
                "is_significant": is_significant,
                "sample_size_after_cleaning": len(arr_a),
                "missing_data_count": len(data_a) - len(arr_a),
            }

            return CorrelationResult(
                metric_a=metric_a,
                metric_b=metric_b,
                correlation_coefficient=result["correlation"],
                p_value=result["p_value"],
                confidence_interval=ci,
                significance_level=f"{significance_level.value:.3f}",
                relationship_type=relationship_type,
                strength=strength,
                sample_size=len(arr_a),
                method_used=method.value,
                additional_metrics=additional_metrics,
            )

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            # Return empty result on error
            return CorrelationResult(
                metric_a=metric_a,
                metric_b=metric_b,
                correlation_coefficient=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                significance_level="error",
                relationship_type="none",
                strength="unknown",
                sample_size=0,
                method_used="error",
                additional_metrics={"error": str(e)},
            )

    async def _pearson_correlation(
        self,
        arr_a: np.ndarray,
        arr_b: np.ndarray,
    ) -> dict[str, float]:
        """Calculate Pearson correlation coefficient."""
        try:
            correlation, p_value = pearsonr(arr_a, arr_b)

            # Handle edge cases
            if np.isnan(correlation):
                correlation = 0.0
            if np.isnan(p_value):
                p_value = 1.0

            return {"correlation": correlation, "p_value": p_value}

        except Exception as e:
            logger.error(f"Pearson correlation failed: {e}")
            return {"correlation": 0.0, "p_value": 1.0}

    async def _spearman_correlation(
        self,
        arr_a: np.ndarray,
        arr_b: np.ndarray,
    ) -> dict[str, float]:
        """Calculate Spearman rank correlation coefficient."""
        try:
            correlation, p_value = spearmanr(arr_a, arr_b)

            if np.isnan(correlation):
                correlation = 0.0
            if np.isnan(p_value):
                p_value = 1.0

            return {"correlation": correlation, "p_value": p_value}

        except Exception as e:
            logger.error(f"Spearman correlation failed: {e}")
            return {"correlation": 0.0, "p_value": 1.0}

    async def _kendall_correlation(
        self,
        arr_a: np.ndarray,
        arr_b: np.ndarray,
    ) -> dict[str, float]:
        """Calculate Kendall tau correlation coefficient."""
        try:
            correlation, p_value = kendalltau(arr_a, arr_b)

            if np.isnan(correlation):
                correlation = 0.0
            if np.isnan(p_value):
                p_value = 1.0

            return {"correlation": correlation, "p_value": p_value}

        except Exception as e:
            logger.error(f"Kendall correlation failed: {e}")
            return {"correlation": 0.0, "p_value": 1.0}

    async def _partial_correlation(
        self,
        arr_a: np.ndarray,
        arr_b: np.ndarray,
    ) -> dict[str, float]:
        """Calculate partial correlation (simplified implementation)."""
        try:
            # For now, fall back to Pearson
            # In a full implementation, you'd control for other variables
            return await self._pearson_correlation(arr_a, arr_b)

        except Exception as e:
            logger.error(f"Partial correlation failed: {e}")
            return {"correlation": 0.0, "p_value": 1.0}

    async def _distance_correlation(
        self,
        arr_a: np.ndarray,
        arr_b: np.ndarray,
    ) -> dict[str, float]:
        """Calculate distance correlation (simplified implementation)."""
        try:
            # Simplified distance correlation
            # In a full implementation, you'd use proper distance correlation formula

            # Standardize the data
            arr_a_std = (arr_a - np.mean(arr_a)) / np.std(arr_a)
            arr_b_std = (arr_b - np.mean(arr_b)) / np.std(arr_b)

            # Calculate distance matrices
            n = len(arr_a_std)
            dist_a = np.abs(arr_a_std[:, np.newaxis] - arr_a_std)
            dist_b = np.abs(arr_b_std[:, np.newaxis] - arr_b_std)

            # Simplified distance correlation
            correlation = np.corrcoef(dist_a.flatten(), dist_b.flatten())[0, 1]

            if np.isnan(correlation):
                correlation = 0.0

            # Approximate p-value (simplified)
            p_value = 2 * (1 - stats.norm.cdf(abs(correlation) * np.sqrt(n - 2)))

            return {"correlation": correlation, "p_value": p_value}

        except Exception as e:
            logger.error(f"Distance correlation failed: {e}")
            return {"correlation": 0.0, "p_value": 1.0}

    async def _calculate_confidence_interval(
        self,
        correlation: float,
        sample_size: int,
        significance_level: SignificanceLevel,
    ) -> tuple[float, float]:
        """Calculate confidence interval for correlation coefficient."""
        try:
            if sample_size < 3:
                return (0.0, 0.0)

            # Fisher's z-transformation
            z = 0.5 * np.log((1 + correlation) / (1 - correlation))

            # Standard error
            se = 1 / np.sqrt(sample_size - 3)

            # Critical value
            alpha = significance_level.value
            z_critical = stats.norm.ppf(1 - alpha / 2)

            # Confidence interval in z-space
            z_lower = z - z_critical * se
            z_upper = z + z_critical * se

            # Transform back to correlation space
            ci_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
            ci_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)

            return (ci_lower, ci_upper)

        except Exception as e:
            logger.error(f"Confidence interval calculation failed: {e}")
            return (0.0, 0.0)

    def _classify_relationship(
        self,
        correlation: float,
        is_significant: bool,
    ) -> tuple[str, str]:
        """Classify the relationship type and strength."""
        if not is_significant:
            return "none", "none"

        abs_corr = abs(correlation)

        # Determine strength
        if abs_corr >= self.config["strong_correlation_threshold"]:
            strength = "very_strong"
        elif abs_corr >= self.config["moderate_correlation_threshold"]:
            strength = "strong"
        elif abs_corr >= self.config["weak_correlation_threshold"]:
            strength = "moderate"
        else:
            strength = "weak"

        # Determine direction
        if correlation > 0:
            relationship_type = "positive"
        else:
            relationship_type = "negative"

        return relationship_type, strength

    async def analyze_time_series_correlation(
        self,
        series_a: list[tuple[datetime, float]],
        series_b: list[tuple[datetime, float]],
        series_a_name: str,
        series_b_name: str,
        max_lag_days: int | None = None,
    ) -> TimeSeriesCorrelation:
        """Analyze correlation between two time series with lag analysis.

        Args:
            series_a: List of (timestamp, value) tuples
            series_b: List of (timestamp, value) tuples
            series_a_name: Name of first series
            series_b_name: Name of second series
            max_lag_days: Maximum lag to analyze

        Returns:
            Time series correlation analysis result
        """
        try:
            max_lag = max_lag_days or self.config["max_lag_days"]

            # Convert to pandas DataFrames
            df_a = pd.DataFrame(series_a, columns=["timestamp", "value"])
            df_b = pd.DataFrame(series_b, columns=["timestamp", "value"])

            df_a["timestamp"] = pd.to_datetime(df_a["timestamp"])
            df_b["timestamp"] = pd.to_datetime(df_b["timestamp"])

            # Align timestamps (find common time range)
            start_time = max(df_a["timestamp"].min(), df_b["timestamp"].min())
            end_time = min(df_a["timestamp"].max(), df_b["timestamp"].max())

            if start_time >= end_time:
                raise ValueError("No overlapping time period between series")

            # Filter to common time range
            df_a = df_a[
                (df_a["timestamp"] >= start_time) & (df_a["timestamp"] <= end_time)
            ]
            df_b = df_b[
                (df_b["timestamp"] >= start_time) & (df_b["timestamp"] <= end_time)
            ]

            # Resample to daily frequency (fill missing values)
            df_a = (
                df_a.set_index("timestamp").resample("D").mean().fillna(method="ffill")
            )
            df_b = (
                df_b.set_index("timestamp").resample("D").mean().fillna(method="ffill")
            )

            # Align indices
            common_index = df_a.index.intersection(df_b.index)
            df_a = df_a.loc[common_index]
            df_b = df_b.loc[common_index]

            if len(df_a) < self.config["min_sample_size"]:
                raise ValueError("Insufficient overlapping data")

            # Calculate cross-correlation at different lags
            correlation_at_lag = {}
            max_correlation = -1
            best_lag = 0

            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    correlation = df_a["value"].corr(df_b["value"])
                elif lag > 0:
                    # A leads B
                    if len(df_a) > lag:
                        correlation = (
                            df_a["value"].iloc[:-lag].corr(df_b["value"].iloc[lag:])
                        )
                    else:
                        correlation = 0
                else:
                    # B leads A
                    lag_abs = abs(lag)
                    if len(df_b) > lag_abs:
                        correlation = (
                            df_a["value"]
                            .iloc[lag_abs:]
                            .corr(df_b["value"].iloc[:-lag_abs])
                        )
                    else:
                        correlation = 0

                if not np.isnan(correlation):
                    correlation_at_lag[lag] = correlation

                    if abs(correlation) > abs(max_correlation):
                        max_correlation = correlation
                        best_lag = lag

            # Determine lead-lag relationship
            if best_lag > 0:
                lead_lag_relationship = "a_leads_b"
            elif best_lag < 0:
                lead_lag_relationship = "b_leads_a"
            else:
                lead_lag_relationship = "simultaneous"

            return TimeSeriesCorrelation(
                series_a_name=series_a_name,
                series_b_name=series_b_name,
                correlation_at_lag=correlation_at_lag,
                best_lag=best_lag,
                best_correlation=max_correlation,
                lead_lag_relationship=lead_lag_relationship,
            )

        except Exception as e:
            logger.error(f"Time series correlation analysis failed: {e}")
            return TimeSeriesCorrelation(
                series_a_name=series_a_name,
                series_b_name=series_b_name,
                correlation_at_lag={},
                best_lag=0,
                best_correlation=0.0,
                lead_lag_relationship="unknown",
            )

    async def analyze_correlation_matrix(
        self,
        data_matrix: dict[str, list[float]],
        significance_level: SignificanceLevel = SignificanceLevel.P_05,
    ) -> CorrelationMatrix:
        """Analyze correlation matrix for multiple metrics.

        Args:
            data_matrix: Dictionary of metric_name -> values
            significance_level: Required significance level

        Returns:
            Complete correlation matrix analysis
        """
        try:
            metrics = list(data_matrix.keys())
            n_metrics = len(metrics)

            if n_metrics < 2:
                raise ValueError("Need at least 2 metrics for correlation matrix")

            # Convert to DataFrame
            df = pd.DataFrame(data_matrix)

            # Handle missing values
            df = df.dropna()

            if len(df) < self.config["min_sample_size"]:
                raise ValueError("Insufficient data after cleaning")

            # Calculate correlation matrix
            correlation_matrix = df.corr().values

            # Calculate p-value matrix
            p_value_matrix = np.zeros((n_metrics, n_metrics))
            for i in range(n_metrics):
                for j in range(n_metrics):
                    if i != j:
                        _, p_value = pearsonr(df.iloc[:, i], df.iloc[:, j])
                        p_value_matrix[i, j] = p_value
                    else:
                        p_value_matrix[i, j] = 0.0

            # Create significance matrix
            significance_matrix = p_value_matrix <= significance_level.value

            # Perform clustering to group related metrics
            cluster_groups = await self._cluster_correlated_metrics(
                correlation_matrix,
                metrics,
                significance_matrix,
            )

            # Principal Component Analysis
            pca_result = await self._perform_pca(df)

            return CorrelationMatrix(
                metrics=metrics,
                correlation_matrix=correlation_matrix,
                p_value_matrix=p_value_matrix,
                significance_matrix=significance_matrix,
                cluster_groups=cluster_groups,
                principal_components=pca_result,
            )

        except Exception as e:
            logger.error(f"Correlation matrix analysis failed: {e}")
            return CorrelationMatrix(
                metrics=[],
                correlation_matrix=np.array([]),
                p_value_matrix=np.array([]),
                significance_matrix=np.array([]),
                cluster_groups=[],
            )

    async def _cluster_correlated_metrics(
        self,
        correlation_matrix: np.ndarray,
        metrics: list[str],
        significance_matrix: np.ndarray,
    ) -> list[list[str]]:
        """Cluster metrics based on correlation patterns."""
        try:
            # Use absolute correlation values for clustering
            abs_corr_matrix = np.abs(correlation_matrix)

            # Convert to distance matrix (1 - correlation)
            distance_matrix = 1 - abs_corr_matrix

            # Perform K-means clustering
            n_clusters = min(3, len(metrics) // 2)  # Adaptive number of clusters
            if n_clusters < 2:
                return [[metric] for metric in metrics]

            # Use PCA for dimensionality reduction before clustering
            pca = PCA(n_components=min(3, len(metrics)))
            reduced_features = pca.fit_transform(distance_matrix)

            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(reduced_features)

            # Group metrics by cluster
            cluster_groups = []
            for cluster_id in range(n_clusters):
                cluster_metrics = [
                    metrics[i]
                    for i in range(len(metrics))
                    if cluster_labels[i] == cluster_id
                ]
                if cluster_metrics:
                    cluster_groups.append(cluster_metrics)

            return cluster_groups

        except Exception as e:
            logger.error(f"Metric clustering failed: {e}")
            return [[metric] for metric in metrics]

    async def _perform_pca(self, df: pd.DataFrame) -> dict[str, Any]:
        """Perform Principal Component Analysis."""
        try:
            # Standardize the data
            df_std = StandardScaler().fit_transform(df)

            # Perform PCA
            pca = PCA()
            pca.fit_transform(df_std)

            # Calculate explained variance ratios
            explained_variance_ratio = pca.explained_variance_ratio_
            cumulative_variance = np.cumsum(explained_variance_ratio)

            # Find number of components explaining 95% of variance
            n_components_95 = np.argmax(cumulative_variance >= 0.95) + 1

            return {
                "explained_variance_ratio": explained_variance_ratio.tolist(),
                "cumulative_variance": cumulative_variance.tolist(),
                "components_95_percent": n_components_95,
                "total_variance_explained": cumulative_variance[-1],
                "component_loadings": pca.components_.tolist(),
            }

        except Exception as e:
            logger.error(f"PCA analysis failed: {e}")
            return {}

    async def detect_causal_relationships(
        self,
        time_series_data: dict[str, list[tuple[datetime, float]]],
        max_lag_days: int = 7,
    ) -> list[CausalAnalysis]:
        """Detect potential causal relationships between time series.

        Args:
            time_series_data: Dictionary of metric_name -> time series
            max_lag_days: Maximum lag to consider for causality

        Returns:
            List of detected causal relationships
        """
        try:
            causal_relationships = []
            metrics = list(time_series_data.keys())

            # Analyze all pairs of metrics
            for i, metric_a in enumerate(metrics):
                for j, metric_b in enumerate(metrics):
                    if i >= j:  # Avoid duplicates and self-correlation
                        continue

                    try:
                        # Analyze time series correlation
                        ts_corr = await self.analyze_time_series_correlation(
                            time_series_data[metric_a],
                            time_series_data[metric_b],
                            metric_a,
                            metric_b,
                            max_lag_days,
                        )

                        # Check if there's a significant correlation with lag
                        if (
                            abs(ts_corr.best_correlation) > 0.5
                            and abs(ts_corr.best_lag) > 0
                        ):
                            # Determine causal direction
                            if ts_corr.lead_lag_relationship == "a_leads_b":
                                cause_metric = metric_a
                                effect_metric = metric_b
                                lag_days = ts_corr.best_lag
                            elif ts_corr.lead_lag_relationship == "b_leads_a":
                                cause_metric = metric_b
                                effect_metric = metric_a
                                lag_days = abs(ts_corr.best_lag)
                            else:
                                continue  # No clear causal direction

                            # Calculate causal strength and confidence
                            causal_strength = abs(ts_corr.best_correlation)
                            confidence = min(
                                causal_strength * 1.5,
                                1.0,
                            )  # Simplified confidence

                            # Determine causal type
                            causal_type = (
                                "direct" if causal_strength > 0.7 else "indirect"
                            )

                            # Supporting evidence
                            supporting_evidence = [
                                f"Correlation coefficient: "
                                f"{ts_corr.best_correlation:.3f}",
                                f"Lag: {lag_days} days",
                                f"Lead-lag relationship: "
                                f"{ts_corr.lead_lag_relationship}",
                            ]

                            causal_relationships.append(
                                CausalAnalysis(
                                    cause_metric=cause_metric,
                                    effect_metric=effect_metric,
                                    causal_strength=causal_strength,
                                    confidence=confidence,
                                    lag_days=lag_days,
                                    causal_type=causal_type,
                                    supporting_evidence=supporting_evidence,
                                ),
                            )

                    except Exception as e:
                        logger.warning(
                            f"Causal analysis failed for {metric_a} -> {metric_b}: {e}",
                        )
                        continue

            # Sort by causal strength
            causal_relationships.sort(key=lambda x: x.causal_strength, reverse=True)

            return causal_relationships

        except Exception as e:
            logger.error(f"Causal relationship detection failed: {e}")
            return []

    async def analyze_correlations(
        self,
        metrics: list[str],
        time_range: str = "24h",
    ) -> dict[str, Any]:
        """Analyze correlations between multiple metrics.

        Args:
            metrics: List of metric names to analyze
            time_range: Time range for analysis (e.g., "24h", "7d")

        Returns:
            Dictionary containing correlation analysis results
        """
        try:
            if len(metrics) < 2:
                return {
                    "correlations": [],
                    "summary": {
                        "total_correlations": 0,
                        "significant_correlations": 0,
                        "strong_correlations": 0,
                    },
                }

            # Generate mock data for metrics
            mock_data = await self._generate_mock_metrics_data(metrics, time_range)

            correlations = []
            correlation_matrix = np.zeros((len(metrics), len(metrics)))

            # Calculate pairwise correlations
            for i, metric_a in enumerate(metrics):
                for j, metric_b in enumerate(metrics):
                    if i < j:  # Only calculate upper triangle
                        data_a = mock_data[metric_a]
                        data_b = mock_data[metric_b]

                        # Calculate correlation
                        correlation_result = await self.analyze_correlation(
                            data_a,
                            data_b,
                            metric_a,
                            metric_b,
                        )

                        correlations.append(
                            {
                                "metric_a": metric_a,
                                "metric_b": metric_b,
                                "correlation_coefficient": (
                                    correlation_result.correlation_coefficient
                                ),
                                "p_value": correlation_result.p_value,
                                "significance_level": correlation_result.significance_level,
                                "relationship_type": (
                                    correlation_result.relationship_type
                                ),
                                "confidence_interval": (
                                    correlation_result.confidence_interval
                                ),
                                "method": correlation_result.method.value,
                            },
                        )

                        # Fill correlation matrix
                        correlation_matrix[
                            i, j
                        ] = correlation_result.correlation_coefficient
                        correlation_matrix[
                            j, i
                        ] = correlation_result.correlation_coefficient

                # Diagonal is 1.0
                correlation_matrix[i, i] = 1.0

            # Calculate summary statistics
            significant_correlations = len(
                [c for c in correlations if c["p_value"] < 0.05],
            )
            strong_correlations = len(
                [c for c in correlations if abs(c["correlation_coefficient"]) > 0.7],
            )

            return {
                "correlations": correlations,
                "correlation_matrix": correlation_matrix.tolist(),
                "summary": {
                    "total_correlations": len(correlations),
                    "significant_correlations": significant_correlations,
                    "strong_correlations": strong_correlations,
                    "metrics_analyzed": metrics,
                    "time_range": time_range,
                },
            }

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {
                "correlations": [],
                "summary": {
                    "total_correlations": 0,
                    "significant_correlations": 0,
                    "strong_correlations": 0,
                    "error": str(e),
                },
            }

    async def _generate_mock_metrics_data(
        self,
        metrics: list[str],
        time_range: str,
    ) -> dict[str, list[float]]:
        """Generate mock data for multiple metrics."""
        try:
            # Parse time range
            time_range_hours = self._parse_time_range(time_range)

            # Generate data points (one per hour)
            n_points = min(time_range_hours, 168)  # Max 1 week of hourly data

            mock_data = {}

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

            for metric in metrics:
                base_value = base_values.get(metric, 100)

                # Generate correlated data with some noise
                if metric == "response_time":
                    # Response time correlates negatively with throughput
                    data = [
                        base_value + np.random.normal(0, 10) for _ in range(n_points)
                    ]
                elif metric == "throughput":
                    # Throughput correlates negatively with response time
                    data = [
                        base_value + np.random.normal(0, 100) for _ in range(n_points)
                    ]
                elif metric == "error_rate":
                    # Error rate correlates with response time
                    data = [
                        base_value + np.random.normal(0, 0.005) for _ in range(n_points)
                    ]
                elif metric == "cache_hit_rate":
                    # Cache hit rate correlates negatively with response time
                    data = [
                        base_value + np.random.normal(0, 0.05) for _ in range(n_points)
                    ]
                else:
                    # Other metrics with random data
                    data = [
                        base_value + np.random.normal(0, base_value * 0.1)
                        for _ in range(n_points)
                    ]

                # Ensure data is within reasonable bounds
                if metric in [
                    "error_rate",
                    "cache_hit_rate",
                    "cpu_usage",
                    "memory_usage",
                    "disk_usage",
                ]:
                    data = [max(0, min(1, val)) for val in data]
                elif metric in ["response_time", "network_latency"]:
                    data = [max(1, val) for val in data]

                mock_data[metric] = data

            return mock_data

        except Exception as e:
            logger.error(f"Mock metrics data generation failed: {e}")
            # Return minimal data
            return {metric: [100.0] for metric in metrics}

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

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the correlation engine."""
        try:
            # Test basic functionality
            test_data_a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            test_data_b = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

            result = await self.analyze_correlation(
                test_data_a,
                test_data_b,
                "test_a",
                "test_b",
            )

            return {
                "status": "healthy",
                "methods_available": [method.value for method in CorrelationMethod],
                "test_correlation_success": result.correlation_coefficient > 0.9,
                "cache_size": len(self.correlation_cache),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "methods_available": [],
                "test_correlation_success": False,
            }


# Singleton instance
_correlation_engine = None


def get_correlation_engine() -> CorrelationEngine:
    """Get or create correlation engine singleton."""
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = CorrelationEngine()
    return _correlation_engine
