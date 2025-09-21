"""TrendAnalyzer - Advanced trend analysis and lifecycle prediction

Analyzes trend patterns, predicts lifecycle stages, and generates investment insights.
"""

import asyncio
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from ..models.trend_signal import Platform, TrendLifecycle, TrendSignal


@dataclass
class TrendAnalysisResult:
    """Result of comprehensive trend analysis"""

    trend_signal: TrendSignal
    predicted_lifecycle_stage: TrendLifecycle
    lifecycle_confidence: float
    momentum_trajectory: list[float]  # Historical momentum values
    volume_growth_rate: float
    peak_prediction_days: int | None
    investment_score: float  # 0.0 to 1.0
    risk_assessment: dict[str, float]
    supporting_evidence: list[str]


class TrendAnalyzer:
    """Advanced trend analysis engine

    Capabilities:
    - Trend lifecycle prediction
    - Momentum trajectory analysis
    - Volume growth calculation
    - Peak timing prediction
    - Investment scoring
    - Risk assessment
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.accuracy_threshold = 0.95  # For contract testing

        # Historical data cache for analysis
        self.trend_history: dict[str, list[TrendSignal]] = defaultdict(list)
        self.analysis_cache: dict[str, TrendAnalysisResult] = {}

        # Analysis parameters
        self.min_data_points = 5
        self.momentum_window_hours = 24
        self.volume_growth_threshold = 0.1  # 10% growth

    async def analyze_trends(
        self,
        trends: list[TrendSignal],
    ) -> list[TrendAnalysisResult]:
        """Analyze multiple trends and return comprehensive analysis results

        Args:
            trends: List of trend signals to analyze

        Returns:
            List of analysis results with predictions and insights
        """
        start_time = datetime.now()

        results = []

        # Process trends in parallel for performance
        analysis_tasks = [self._analyze_single_trend(trend) for trend in trends]
        analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        for i, result in enumerate(analysis_results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Error analyzing trend {trends[i].keyword}: {result}",
                )
                continue
            results.append(result)

        # Log performance
        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Analyzed {len(trends)} trends in {elapsed:.3f}s")

        return results

    async def _analyze_single_trend(self, trend: TrendSignal) -> TrendAnalysisResult:
        """Analyze a single trend signal"""
        # Add to historical data
        self.trend_history[trend.keyword].append(trend)

        # Get historical context
        history = self.trend_history[trend.keyword]

        # Predict lifecycle stage
        predicted_stage, lifecycle_confidence = self._predict_lifecycle_stage(
            trend,
            history,
        )

        # Calculate momentum trajectory
        momentum_trajectory = self._calculate_momentum_trajectory(history)

        # Calculate volume growth rate
        volume_growth_rate = self._calculate_volume_growth_rate(history)

        # Predict peak timing
        peak_prediction_days = self._predict_peak_timing(trend, history)

        # Calculate investment score
        investment_score = self._calculate_investment_score(
            trend,
            predicted_stage,
            volume_growth_rate,
            momentum_trajectory,
        )

        # Assess risks
        risk_assessment = self._assess_risks(trend, history)

        # Generate supporting evidence
        supporting_evidence = self._generate_supporting_evidence(
            trend,
            predicted_stage,
            volume_growth_rate,
            momentum_trajectory,
        )

        return TrendAnalysisResult(
            trend_signal=trend,
            predicted_lifecycle_stage=predicted_stage,
            lifecycle_confidence=lifecycle_confidence,
            momentum_trajectory=momentum_trajectory,
            volume_growth_rate=volume_growth_rate,
            peak_prediction_days=peak_prediction_days,
            investment_score=investment_score,
            risk_assessment=risk_assessment,
            supporting_evidence=supporting_evidence,
        )

    def _predict_lifecycle_stage(
        self,
        trend: TrendSignal,
        history: list[TrendSignal],
    ) -> tuple[TrendLifecycle, float]:
        """Predict the lifecycle stage with confidence"""
        if len(history) < 2:
            # Not enough data, use current stage with low confidence
            return trend.lifecycle_stage, 0.5

        # Calculate trend age
        first_seen = min(t.timestamp for t in history)
        age_hours = (trend.timestamp - first_seen).total_seconds() / 3600

        # Analyze momentum and volume trends
        recent_momentum = [t.momentum for t in history[-5:]]  # Last 5 data points
        recent_volumes = [t.volume for t in history[-5:]]

        momentum_trend = self._calculate_trend_direction(recent_momentum)
        volume_trend = self._calculate_trend_direction(recent_volumes)

        # Lifecycle prediction logic
        confidence = 0.8

        if age_hours < 24:
            # Very new trend
            if momentum_trend > 0.1 and volume_trend > 0.1:
                return TrendLifecycle.EMERGING, confidence
            return TrendLifecycle.EMERGING, 0.6

        if age_hours < 168:  # Less than a week
            if momentum_trend > 0.05:
                return TrendLifecycle.GROWING, confidence
            if momentum_trend < -0.05:
                return TrendLifecycle.DECLINING, confidence - 0.1
            return TrendLifecycle.PEAK, confidence - 0.2

        if age_hours < 720:  # Less than a month
            if momentum_trend > 0:
                return TrendLifecycle.PEAK, confidence
            return TrendLifecycle.DECLINING, confidence

        # Old trend
        if trend.momentum < 0.3:
            return TrendLifecycle.DORMANT, confidence
        return TrendLifecycle.DECLINING, confidence - 0.1

    def _calculate_trend_direction(self, values: list[float]) -> float:
        """Calculate trend direction (-1 to 1) using linear regression"""
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values))
        y = np.array(values)

        # Simple linear regression
        slope = (
            np.corrcoef(x, y)[0, 1] if len(values) > 2 else (y[-1] - y[0]) / len(values)
        )

        # Normalize slope to -1 to 1 range
        return max(-1.0, min(1.0, slope))

    def _calculate_momentum_trajectory(self, history: list[TrendSignal]) -> list[float]:
        """Calculate momentum trajectory over time"""
        if len(history) < 2:
            return [history[0].momentum] if history else [0.0]

        # Sort by timestamp
        sorted_history = sorted(history, key=lambda t: t.timestamp)

        # Extract momentum values
        momentum_values = [t.momentum for t in sorted_history]

        # Apply smoothing if we have enough data points
        if len(momentum_values) >= 5:
            smoothed = []
            for i in range(len(momentum_values)):
                start_idx = max(0, i - 2)
                end_idx = min(len(momentum_values), i + 3)
                window = momentum_values[start_idx:end_idx]
                smoothed.append(statistics.mean(window))
            return smoothed

        return momentum_values

    def _calculate_volume_growth_rate(self, history: list[TrendSignal]) -> float:
        """Calculate volume growth rate"""
        if len(history) < 2:
            return 0.0

        sorted_history = sorted(history, key=lambda t: t.timestamp)

        # Calculate growth rate over the full history
        initial_volume = sorted_history[0].volume
        final_volume = sorted_history[-1].volume

        if initial_volume == 0:
            return 1.0 if final_volume > 0 else 0.0

        growth_rate = (final_volume - initial_volume) / initial_volume

        # Normalize to reasonable range
        return max(-1.0, min(5.0, growth_rate))

    def _predict_peak_timing(
        self,
        trend: TrendSignal,
        history: list[TrendSignal],
    ) -> int | None:
        """Predict when trend will peak (days from now)"""
        if len(history) < 3:
            return None

        # Analyze momentum trajectory
        momentum_trajectory = self._calculate_momentum_trajectory(history)

        if len(momentum_trajectory) < 3:
            return None

        # If momentum is declining, peak may have passed or be imminent
        recent_momentum_trend = self._calculate_trend_direction(
            momentum_trajectory[-3:],
        )

        if recent_momentum_trend < -0.1:
            # Declining momentum - peak soon or already passed
            if trend.momentum > 0.7:
                return 1  # Peak within 1 day
            return 0  # Peak already passed

        if recent_momentum_trend > 0.1:
            # Growing momentum - peak further out
            if trend.momentum < 0.5:
                return 7  # Peak in about a week
            return 3  # Peak in a few days

        # Stable momentum - near peak
        return 2

    def _calculate_investment_score(
        self,
        trend: TrendSignal,
        predicted_stage: TrendLifecycle,
        volume_growth_rate: float,
        momentum_trajectory: list[float],
    ) -> float:
        """Calculate investment score (0.0 to 1.0)"""
        # Base score from trend strength
        base_score = trend.trend_strength

        # Lifecycle stage multiplier
        stage_multipliers = {
            TrendLifecycle.EMERGING: 1.0,
            TrendLifecycle.GROWING: 0.9,
            TrendLifecycle.PEAK: 0.6,
            TrendLifecycle.DECLINING: 0.3,
            TrendLifecycle.DORMANT: 0.1,
        }

        stage_score = base_score * stage_multipliers.get(predicted_stage, 0.5)

        # Volume growth bonus
        volume_score = min(0.2, max(0.0, volume_growth_rate * 0.1))

        # Momentum trajectory bonus
        if len(momentum_trajectory) >= 3:
            momentum_trend = self._calculate_trend_direction(momentum_trajectory[-3:])
            momentum_score = max(0.0, momentum_trend * 0.1)
        else:
            momentum_score = 0.0

        # Platform bonus (some platforms are more investable)
        platform_multipliers = {
            Platform.GOOGLE_TRENDS: 1.0,
            Platform.YOUTUBE: 0.9,
            Platform.TWITTER: 0.8,
            Platform.TIKTOK: 0.7,
        }

        platform_multiplier = platform_multipliers.get(trend.platform, 0.8)

        # Calculate final score
        final_score = (
            stage_score + volume_score + momentum_score
        ) * platform_multiplier

        return max(0.0, min(1.0, final_score))

    def _assess_risks(
        self,
        trend: TrendSignal,
        history: list[TrendSignal],
    ) -> dict[str, float]:
        """Assess various risk factors"""
        risks = {
            "volatility_risk": 0.0,
            "decline_risk": 0.0,
            "timing_risk": 0.0,
            "platform_risk": 0.0,
            "overall_risk": 0.0,
        }

        # Volatility risk - based on momentum variance
        if len(history) >= 3:
            momentum_values = [t.momentum for t in history]
            momentum_variance = statistics.variance(momentum_values)
            risks["volatility_risk"] = min(1.0, momentum_variance * 2)

        # Decline risk - based on recent trend direction
        if len(history) >= 3:
            recent_momentum = [t.momentum for t in history[-3:]]
            decline_trend = -self._calculate_trend_direction(recent_momentum)
            risks["decline_risk"] = max(0.0, decline_trend)

        # Timing risk - based on lifecycle stage
        stage_risks = {
            TrendLifecycle.EMERGING: 0.3,
            TrendLifecycle.GROWING: 0.2,
            TrendLifecycle.PEAK: 0.7,
            TrendLifecycle.DECLINING: 0.9,
            TrendLifecycle.DORMANT: 1.0,
        }
        risks["timing_risk"] = stage_risks.get(trend.lifecycle_stage, 0.5)

        # Platform risk - some platforms are more volatile
        platform_risks = {
            Platform.GOOGLE_TRENDS: 0.2,
            Platform.YOUTUBE: 0.3,
            Platform.TWITTER: 0.4,
            Platform.TIKTOK: 0.5,
        }
        risks["platform_risk"] = platform_risks.get(trend.platform, 0.4)

        # Overall risk (weighted average)
        risks["overall_risk"] = (
            risks["volatility_risk"] * 0.3
            + risks["decline_risk"] * 0.3
            + risks["timing_risk"] * 0.25
            + risks["platform_risk"] * 0.15
        )

        return risks

    def _generate_supporting_evidence(
        self,
        trend: TrendSignal,
        predicted_stage: TrendLifecycle,
        volume_growth_rate: float,
        momentum_trajectory: list[float],
    ) -> list[str]:
        """Generate supporting evidence for analysis"""
        evidence = []

        # Trend strength evidence
        if trend.trend_strength > 0.8:
            evidence.append(
                f"Strong trend signal with {trend.trend_strength:.1%} strength",
            )

        # Lifecycle evidence
        evidence.append(f"Predicted to be in {predicted_stage.value} stage")

        # Volume growth evidence
        if volume_growth_rate > 0.2:
            evidence.append(f"High volume growth rate of {volume_growth_rate:.1%}")
        elif volume_growth_rate < -0.1:
            evidence.append(f"Declining volume with {volume_growth_rate:.1%} growth")

        # Momentum evidence
        if len(momentum_trajectory) >= 3:
            momentum_trend = self._calculate_trend_direction(momentum_trajectory[-3:])
            if momentum_trend > 0.1:
                evidence.append("Momentum is increasing")
            elif momentum_trend < -0.1:
                evidence.append("Momentum is decreasing")
            else:
                evidence.append("Momentum is stable")

        # Platform evidence
        evidence.append(f"Detected on {trend.platform.value} platform")

        # Geographic evidence
        if trend.geographic_scope:
            evidence.append(
                f"Active in {len(trend.geographic_scope)} regions: {', '.join(trend.geographic_scope[:3])}",
            )

        return evidence

    async def get_trend_predictions(
        self,
        keyword: str,
    ) -> TrendAnalysisResult | None:
        """Get latest analysis for a specific trend keyword"""
        return self.analysis_cache.get(keyword)

    async def clear_cache(self, older_than_hours: int = 24):
        """Clear old cached analysis results"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        cleared_count = 0
        for keyword in list(self.analysis_cache.keys()):
            analysis = self.analysis_cache[keyword]
            if analysis.trend_signal.timestamp < cutoff_time:
                del self.analysis_cache[keyword]
                cleared_count += 1

        self.logger.info(f"Cleared {cleared_count} cached analysis results")

    def get_analysis_statistics(self) -> dict[str, Any]:
        """Get statistics about analysis performance"""
        total_trends = sum(len(history) for history in self.trend_history.values())

        return {
            "total_trends_analyzed": total_trends,
            "unique_keywords": len(self.trend_history),
            "cached_analyses": len(self.analysis_cache),
            "accuracy_threshold": self.accuracy_threshold,
            "average_history_length": (
                total_trends / len(self.trend_history) if self.trend_history else 0
            ),
        }
