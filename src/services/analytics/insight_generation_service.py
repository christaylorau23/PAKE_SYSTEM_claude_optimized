"""Insight Generation Service

Provides AI-powered insight generation, recommendation systems,
and intelligent analysis of patterns and trends in the data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class InsightCategory(Enum):
    """Categories of insights."""

    TREND_ANALYSIS = "trend_analysis"
    CORRELATION_DISCOVERY = "correlation_discovery"
    ANOMALY_DETECTION = "anomaly_detection"
    PATTERN_RECOGNITION = "pattern_recognition"
    PREDICTIVE_INSIGHT = "predictive_insight"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"
    RISK_ASSESSMENT = "risk_assessment"
    OPPORTUNITY_IDENTIFICATION = "opportunity_identification"


class InsightPriority(Enum):
    """Priority levels for insights."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InsightConfidence(Enum):
    """Confidence levels for insights."""

    VERY_HIGH = "very_high"  # 90-100%
    HIGH = "high"  # 70-89%
    MEDIUM = "medium"  # 50-69%
    LOW = "low"  # 30-49%
    VERY_LOW = "very_low"  # 0-29%


@dataclass
class InsightRecommendation:
    """AI-generated insight and recommendation."""

    id: str
    title: str
    description: str
    category: InsightCategory
    priority: InsightPriority
    confidence: InsightConfidence
    confidence_score: float  # 0.0 to 1.0
    supporting_data: list[str]
    action_suggestions: list[str]
    impact_assessment: str
    timeframe: str
    created_at: datetime
    metadata: dict[str, Any]


@dataclass
class PatternInsight:
    """Pattern recognition insight."""

    pattern_type: str
    pattern_description: str
    frequency: int
    confidence: float
    examples: list[str]
    implications: list[str]


@dataclass
class TrendInsight:
    """Trend analysis insight."""

    trend_direction: str
    trend_strength: float
    trend_duration: str
    key_drivers: list[str]
    future_projection: str
    confidence: float


@dataclass
class AnomalyInsight:
    """Anomaly detection insight."""

    anomaly_type: str
    severity: str
    affected_metrics: list[str]
    anomaly_description: str
    potential_causes: list[str]
    recommended_actions: list[str]


class InsightGenerationService:
    """Advanced insight generation service that combines statistical analysis,
    pattern recognition, and AI-powered reasoning to generate actionable insights.
    """

    def __init__(self):
        """Initialize the insight generation service."""
        self.insight_templates = self._load_insight_templates()
        self.pattern_library = self._initialize_pattern_library()
        self.insight_cache = {}

        # Configuration
        self.config = {
            "min_confidence_threshold": 0.3,
            "max_insights_per_analysis": 20,
            "cache_ttl_hours": 6,
            "trend_analysis_window_days": 30,
            "pattern_min_frequency": 3,
        }

    def _load_insight_templates(self) -> dict[str, dict[str, Any]]:
        """Load insight generation templates."""
        return {
            "trend_up": {
                "title_template": "Rising Trend Detected in {metric}",
                "description_template": "The {metric} has shown a consistent upward trend over the past {duration}, with a {strength} increase of {magnitude}.",
                "action_suggestions": [
                    "Monitor this trend closely for sustainability",
                    "Investigate the underlying causes",
                    "Consider capitalizing on this positive momentum",
                ],
                "priority": InsightPriority.HIGH,
            },
            "trend_down": {
                "title_template": "Declining Trend Detected in {metric}",
                "description_template": "The {metric} has shown a concerning downward trend over the past {duration}, with a {strength} decrease of {magnitude}.",
                "action_suggestions": [
                    "Investigate the root causes immediately",
                    "Implement corrective measures",
                    "Monitor closely for further deterioration",
                ],
                "priority": InsightPriority.HIGH,
            },
            "correlation_strong": {
                "title_template": "Strong Correlation Found Between {metric_a} and {metric_b}",
                "description_template": "A {strength} {direction} correlation ({correlation:.3f}) has been identified between {metric_a} and {metric_b}.",
                "action_suggestions": [
                    "Investigate the causal relationship",
                    "Use this correlation for predictive modeling",
                    "Consider leveraging this relationship for optimization",
                ],
                "priority": InsightPriority.MEDIUM,
            },
            "anomaly_detected": {
                "title_template": "Anomaly Detected in {metric}",
                "description_template": "An unusual pattern has been detected in {metric} on {date}, with a deviation of {magnitude} from expected values.",
                "action_suggestions": [
                    "Investigate the cause of this anomaly",
                    "Check for data quality issues",
                    "Monitor for similar patterns",
                ],
                "priority": InsightPriority.HIGH,
            },
            "pattern_emerging": {
                "title_template": "Emerging Pattern Identified",
                "description_template": "A new pattern has been identified: {pattern_description}. This pattern has occurred {frequency} times recently.",
                "action_suggestions": [
                    "Validate this pattern with additional data",
                    "Investigate the underlying mechanism",
                    "Consider incorporating into predictive models",
                ],
                "priority": InsightPriority.MEDIUM,
            },
            "optimization_opportunity": {
                "title_template": "Optimization Opportunity Identified",
                "description_template": "Analysis suggests potential for optimization in {area}. Current performance shows {current_state}, with potential for {improvement}.",
                "action_suggestions": [
                    "Develop optimization strategy",
                    "Test proposed improvements",
                    "Implement changes gradually",
                ],
                "priority": InsightPriority.MEDIUM,
            },
        }

    def _initialize_pattern_library(self) -> dict[str, dict[str, Any]]:
        """Initialize pattern recognition library."""
        return {
            "seasonal_patterns": {
                "detector": self._detect_seasonal_patterns,
                "description": "Recurring patterns based on time periods",
            },
            "cyclical_patterns": {
                "detector": self._detect_cyclical_patterns,
                "description": "Regular cycles in data",
            },
            "threshold_patterns": {
                "detector": self._detect_threshold_patterns,
                "description": "Patterns around specific thresholds",
            },
            "spike_patterns": {
                "detector": self._detect_spike_patterns,
                "description": "Sudden increases or decreases",
            },
            "trend_patterns": {
                "detector": self._detect_trend_patterns,
                "description": "Long-term directional changes",
            },
        }

    async def generate_comprehensive_insights(
        self,
        time_series_data: dict[str, list[tuple[datetime, float]]],
        correlation_results: list[Any] | None = None,
        anomaly_results: list[Any] | None = None,
    ) -> list[InsightRecommendation]:
        """Generate comprehensive insights from multiple data sources.

        Args:
            time_series_data: Dictionary of metric_name -> time series
            correlation_results: Results from correlation analysis
            anomaly_results: Results from anomaly detection

        Returns:
            List of generated insights
        """
        try:
            insights = []

            # Generate trend insights
            trend_insights = await self._generate_trend_insights(time_series_data)
            insights.extend(trend_insights)

            # Generate correlation insights
            if correlation_results:
                correlation_insights = await self._generate_correlation_insights(
                    correlation_results,
                )
                insights.extend(correlation_insights)

            # Generate anomaly insights
            if anomaly_results:
                anomaly_insights = await self._generate_anomaly_insights(
                    anomaly_results,
                )
                insights.extend(anomaly_insights)

            # Generate pattern insights
            pattern_insights = await self._generate_pattern_insights(time_series_data)
            insights.extend(pattern_insights)

            # Generate optimization insights
            optimization_insights = await self._generate_optimization_insights(
                time_series_data,
            )
            insights.extend(optimization_insights)

            # Rank and filter insights
            ranked_insights = await self._rank_insights(insights)

            # Limit number of insights
            max_insights = self.config["max_insights_per_analysis"]
            return ranked_insights[:max_insights]

        except Exception as e:
            logger.error(f"Comprehensive insight generation failed: {e}")
            return []

    async def _generate_trend_insights(
        self,
        time_series_data: dict[str, list[tuple[datetime, float]]],
    ) -> list[InsightRecommendation]:
        """Generate insights from trend analysis."""
        insights = []

        try:
            for metric_name, time_series in time_series_data.items():
                if len(time_series) < 10:
                    continue

                # Analyze trend
                trend_analysis = await self._analyze_trend(time_series)

                if trend_analysis["trend_strength"] > 0.3:  # Significant trend
                    template_key = f"trend_{trend_analysis['direction']}"

                    if template_key in self.insight_templates:
                        template = self.insight_templates[template_key]

                        # Calculate magnitude
                        values = [point[1] for point in time_series]
                        magnitude = self._calculate_trend_magnitude(
                            values,
                            trend_analysis["direction"],
                        )

                        # Generate insight
                        insight = InsightRecommendation(
                            id=f"trend_{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            title=template["title_template"].format(metric=metric_name),
                            description=template["description_template"].format(
                                metric=metric_name,
                                duration=f"{len(time_series)} days",
                                strength=self._strength_to_text(
                                    trend_analysis["trend_strength"],
                                ),
                                magnitude=magnitude,
                            ),
                            category=InsightCategory.TREND_ANALYSIS,
                            priority=template["priority"],
                            confidence=self._calculate_trend_confidence(trend_analysis),
                            confidence_score=trend_analysis["trend_strength"],
                            supporting_data=[
                                f"Trend direction: {trend_analysis['direction']}",
                                f"Trend strength: {trend_analysis['trend_strength']:.3f}",
                                f"Data points: {len(time_series)}",
                                f"Magnitude: {magnitude}",
                            ],
                            action_suggestions=template["action_suggestions"],
                            impact_assessment=self._assess_trend_impact(trend_analysis),
                            timeframe=f"{len(time_series)} days",
                            created_at=datetime.now(),
                            metadata={
                                "trend_direction": trend_analysis["direction"],
                                "trend_strength": trend_analysis["trend_strength"],
                                "metric_name": metric_name,
                            },
                        )

                        insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"Trend insight generation failed: {e}")
            return []

    async def _generate_correlation_insights(
        self,
        correlation_results: list[Any],
    ) -> list[InsightRecommendation]:
        """Generate insights from correlation analysis."""
        insights = []

        try:
            for result in correlation_results:
                if (
                    hasattr(result, "correlation_coefficient")
                    and abs(result.correlation_coefficient) > 0.5
                ):
                    template = self.insight_templates["correlation_strong"]

                    # Determine strength and direction
                    strength = self._correlation_strength_to_text(
                        abs(result.correlation_coefficient),
                    )
                    direction = (
                        "positive" if result.correlation_coefficient > 0 else "negative"
                    )

                    insight = InsightRecommendation(
                        id=f"correlation_{result.metric_a}_{result.metric_b}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        title=template["title_template"].format(
                            metric_a=result.metric_a,
                            metric_b=result.metric_b,
                        ),
                        description=template["description_template"].format(
                            strength=strength,
                            direction=direction,
                            correlation=result.correlation_coefficient,
                            metric_a=result.metric_a,
                            metric_b=result.metric_b,
                        ),
                        category=InsightCategory.CORRELATION_DISCOVERY,
                        priority=template["priority"],
                        confidence=self._correlation_to_confidence(
                            result.correlation_coefficient,
                        ),
                        confidence_score=abs(result.correlation_coefficient),
                        supporting_data=[
                            f"Correlation coefficient: {result.correlation_coefficient:.3f}",
                            f"P-value: {result.p_value:.3f}",
                            f"Sample size: {result.sample_size}",
                            f"Significance: {result.significance_level}",
                        ],
                        action_suggestions=template["action_suggestions"],
                        impact_assessment=self._assess_correlation_impact(result),
                        timeframe="Analysis period",
                        created_at=datetime.now(),
                        metadata={
                            "correlation_coefficient": result.correlation_coefficient,
                            "p_value": result.p_value,
                            "metric_a": result.metric_a,
                            "metric_b": result.metric_b,
                        },
                    )

                    insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"Correlation insight generation failed: {e}")
            return []

    async def _generate_anomaly_insights(
        self,
        anomaly_results: list[Any],
    ) -> list[InsightRecommendation]:
        """Generate insights from anomaly detection."""
        insights = []

        try:
            for result in anomaly_results:
                if hasattr(result, "anomaly_points") and result.anomaly_points:
                    template = self.insight_templates["anomaly_detected"]

                    # Get the most significant anomaly
                    max_score_idx = result.anomaly_scores.index(
                        max(result.anomaly_scores),
                    )
                    anomaly_idx = result.anomaly_points[max_score_idx]
                    anomaly_score = result.anomaly_scores[max_score_idx]

                    insight = InsightRecommendation(
                        id=f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        title=template["title_template"].format(metric="Data"),
                        description=template["description_template"].format(
                            metric="Data",
                            date=f"point {anomaly_idx}",
                            magnitude=f"{anomaly_score:.2f} standard deviations",
                        ),
                        category=InsightCategory.ANOMALY_DETECTION,
                        priority=InsightPriority.HIGH,
                        confidence=self._anomaly_to_confidence(anomaly_score),
                        confidence_score=min(
                            anomaly_score / 3.0,
                            1.0,
                        ),  # Normalize to 0-1
                        supporting_data=[
                            f"Anomaly score: {anomaly_score:.3f}",
                            f"Detection method: {result.detection_method}",
                            f"Threshold: {result.threshold}",
                            f"Total anomalies: {len(result.anomaly_points)}",
                        ],
                        action_suggestions=template["action_suggestions"],
                        impact_assessment=self._assess_anomaly_impact(anomaly_score),
                        timeframe="Recent data",
                        created_at=datetime.now(),
                        metadata={
                            "anomaly_score": anomaly_score,
                            "anomaly_count": len(result.anomaly_points),
                            "detection_method": result.detection_method,
                        },
                    )

                    insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"Anomaly insight generation failed: {e}")
            return []

    async def _generate_pattern_insights(
        self,
        time_series_data: dict[str, list[tuple[datetime, float]]],
    ) -> list[InsightRecommendation]:
        """Generate insights from pattern recognition."""
        insights = []

        try:
            for metric_name, time_series in time_series_data.items():
                if len(time_series) < 20:
                    continue

                # Detect patterns
                patterns = await self._detect_all_patterns(time_series)

                for pattern_type, pattern_data in patterns.items():
                    if pattern_data["confidence"] > 0.5:
                        template = self.insight_templates["pattern_emerging"]

                        insight = InsightRecommendation(
                            id=f"pattern_{metric_name}_{pattern_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            title=f"Pattern Detected in {metric_name}",
                            description=template["description_template"].format(
                                pattern_description=pattern_data["description"],
                                frequency=f"{pattern_data['frequency']} times",
                            ),
                            category=InsightCategory.PATTERN_RECOGNITION,
                            priority=InsightPriority.MEDIUM,
                            confidence=self._pattern_to_confidence(
                                pattern_data["confidence"],
                            ),
                            confidence_score=pattern_data["confidence"],
                            supporting_data=[
                                f"Pattern type: {pattern_type}",
                                f"Frequency: {pattern_data['frequency']}",
                                f"Confidence: {pattern_data['confidence']:.3f}",
                            ],
                            action_suggestions=template["action_suggestions"],
                            impact_assessment=self._assess_pattern_impact(pattern_data),
                            timeframe=f"{len(time_series)} data points",
                            created_at=datetime.now(),
                            metadata={
                                "pattern_type": pattern_type,
                                "pattern_data": pattern_data,
                                "metric_name": metric_name,
                            },
                        )

                        insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"Pattern insight generation failed: {e}")
            return []

    async def _generate_optimization_insights(
        self,
        time_series_data: dict[str, list[tuple[datetime, float]]],
    ) -> list[InsightRecommendation]:
        """Generate optimization insights."""
        insights = []

        try:
            for metric_name, time_series in time_series_data.items():
                if len(time_series) < 10:
                    continue

                # Analyze for optimization opportunities
                optimization_analysis = await self._analyze_optimization_opportunities(
                    time_series,
                )

                if optimization_analysis["opportunity_score"] > 0.3:
                    template = self.insight_templates["optimization_opportunity"]

                    insight = InsightRecommendation(
                        id=f"optimization_{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        title=template["title_template"],
                        description=template["description_template"].format(
                            area=metric_name,
                            current_state=optimization_analysis["current_state"],
                            improvement=optimization_analysis["improvement"],
                        ),
                        category=InsightCategory.OPTIMIZATION_SUGGESTION,
                        priority=InsightPriority.MEDIUM,
                        confidence=self._optimization_to_confidence(
                            optimization_analysis["opportunity_score"],
                        ),
                        confidence_score=optimization_analysis["opportunity_score"],
                        supporting_data=[
                            f"Opportunity score: {optimization_analysis['opportunity_score']:.3f}",
                            f"Current performance: {optimization_analysis['current_state']}",
                            f"Potential improvement: {optimization_analysis['improvement']}",
                        ],
                        action_suggestions=template["action_suggestions"],
                        impact_assessment=self._assess_optimization_impact(
                            optimization_analysis,
                        ),
                        timeframe="Ongoing",
                        created_at=datetime.now(),
                        metadata={
                            "optimization_analysis": optimization_analysis,
                            "metric_name": metric_name,
                        },
                    )

                    insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"Optimization insight generation failed: {e}")
            return []

    async def _analyze_trend(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any]:
        """Analyze trend in time series data."""
        try:
            values = [point[1] for point in time_series]

            if len(values) < 2:
                return {"direction": "unknown", "trend_strength": 0.0}

            # Simple linear regression
            x = np.arange(len(values))
            slope, _ = np.polyfit(x, values, 1)

            # Normalize slope by mean value
            mean_value = np.mean(values)
            if mean_value != 0:
                relative_slope = slope / mean_value
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
            strength = min(abs(relative_slope) * 100, 1.0)

            return {
                "direction": direction,
                "trend_strength": strength,
                "slope": slope,
                "relative_slope": relative_slope,
            }

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {"direction": "unknown", "trend_strength": 0.0}

    def _calculate_trend_magnitude(self, values: list[float], direction: str) -> str:
        """Calculate trend magnitude as percentage."""
        try:
            if len(values) < 2:
                return "unknown"

            start_value = values[0]
            end_value = values[-1]

            if start_value == 0:
                return "unknown"

            percentage_change = ((end_value - start_value) / start_value) * 100

            if abs(percentage_change) < 5:
                return "minimal"
            if abs(percentage_change) < 15:
                return "moderate"
            if abs(percentage_change) < 50:
                return "significant"
            return "dramatic"

        except Exception as e:
            logger.error(f"Trend magnitude calculation failed: {e}")
            return "unknown"

    def _strength_to_text(self, strength: float) -> str:
        """Convert numeric strength to text."""
        if strength < 0.3:
            return "weak"
        if strength < 0.6:
            return "moderate"
        if strength < 0.8:
            return "strong"
        return "very strong"

    def _correlation_strength_to_text(self, correlation: float) -> str:
        """Convert correlation coefficient to strength text."""
        if correlation < 0.3:
            return "weak"
        if correlation < 0.5:
            return "moderate"
        if correlation < 0.7:
            return "strong"
        return "very strong"

    def _calculate_trend_confidence(
        self,
        trend_analysis: dict[str, Any],
    ) -> InsightConfidence:
        """Calculate confidence level for trend analysis."""
        strength = trend_analysis["trend_strength"]

        if strength >= 0.8:
            return InsightConfidence.VERY_HIGH
        if strength >= 0.6:
            return InsightConfidence.HIGH
        if strength >= 0.4:
            return InsightConfidence.MEDIUM
        if strength >= 0.2:
            return InsightConfidence.LOW
        return InsightConfidence.VERY_LOW

    def _correlation_to_confidence(self, correlation: float) -> InsightConfidence:
        """Convert correlation to confidence level."""
        abs_corr = abs(correlation)

        if abs_corr >= 0.8:
            return InsightConfidence.VERY_HIGH
        if abs_corr >= 0.6:
            return InsightConfidence.HIGH
        if abs_corr >= 0.4:
            return InsightConfidence.MEDIUM
        if abs_corr >= 0.2:
            return InsightConfidence.LOW
        return InsightConfidence.VERY_LOW

    def _anomaly_to_confidence(self, anomaly_score: float) -> InsightConfidence:
        """Convert anomaly score to confidence level."""
        if anomaly_score >= 3.0:
            return InsightConfidence.VERY_HIGH
        if anomaly_score >= 2.5:
            return InsightConfidence.HIGH
        if anomaly_score >= 2.0:
            return InsightConfidence.MEDIUM
        if anomaly_score >= 1.5:
            return InsightConfidence.LOW
        return InsightConfidence.VERY_LOW

    def _pattern_to_confidence(self, pattern_confidence: float) -> InsightConfidence:
        """Convert pattern confidence to insight confidence."""
        if pattern_confidence >= 0.8:
            return InsightConfidence.VERY_HIGH
        if pattern_confidence >= 0.6:
            return InsightConfidence.HIGH
        if pattern_confidence >= 0.4:
            return InsightConfidence.MEDIUM
        if pattern_confidence >= 0.2:
            return InsightConfidence.LOW
        return InsightConfidence.VERY_LOW

    def _optimization_to_confidence(
        self,
        opportunity_score: float,
    ) -> InsightConfidence:
        """Convert optimization opportunity score to confidence."""
        if opportunity_score >= 0.8:
            return InsightConfidence.VERY_HIGH
        if opportunity_score >= 0.6:
            return InsightConfidence.HIGH
        if opportunity_score >= 0.4:
            return InsightConfidence.MEDIUM
        if opportunity_score >= 0.2:
            return InsightConfidence.LOW
        return InsightConfidence.VERY_LOW

    def _assess_trend_impact(self, trend_analysis: dict[str, Any]) -> str:
        """Assess the impact of a trend."""
        direction = trend_analysis["direction"]
        strength = trend_analysis["trend_strength"]

        if direction == "up" and strength > 0.7:
            return "High positive impact - strong upward momentum"
        if direction == "down" and strength > 0.7:
            return "High negative impact - concerning decline"
        if direction == "up" and strength > 0.4:
            return "Moderate positive impact - steady growth"
        if direction == "down" and strength > 0.4:
            return "Moderate negative impact - gradual decline"
        return "Low impact - minimal change"

    def _assess_correlation_impact(self, correlation_result: Any) -> str:
        """Assess the impact of a correlation."""
        abs_corr = abs(correlation_result.correlation_coefficient)

        if abs_corr > 0.7:
            return "High impact - strong relationship that can be leveraged"
        if abs_corr > 0.5:
            return "Moderate impact - useful relationship for analysis"
        if abs_corr > 0.3:
            return "Low impact - weak but potentially useful relationship"
        return "Minimal impact - very weak relationship"

    def _assess_anomaly_impact(self, anomaly_score: float) -> str:
        """Assess the impact of an anomaly."""
        if anomaly_score >= 3.0:
            return "Critical impact - major deviation requiring immediate attention"
        if anomaly_score >= 2.5:
            return "High impact - significant deviation that needs investigation"
        if anomaly_score >= 2.0:
            return "Moderate impact - notable deviation worth monitoring"
        return "Low impact - minor deviation"

    def _assess_pattern_impact(self, pattern_data: dict[str, Any]) -> str:
        """Assess the impact of a pattern."""
        confidence = pattern_data["confidence"]
        frequency = pattern_data["frequency"]

        if confidence > 0.8 and frequency > 5:
            return "High impact - reliable pattern with high frequency"
        if confidence > 0.6 and frequency > 3:
            return "Moderate impact - consistent pattern"
        if confidence > 0.4:
            return "Low impact - emerging pattern"
        return "Minimal impact - weak pattern"

    def _assess_optimization_impact(self, optimization_analysis: dict[str, Any]) -> str:
        """Assess the impact of optimization opportunities."""
        score = optimization_analysis["opportunity_score"]

        if score > 0.7:
            return "High impact - significant optimization potential"
        if score > 0.5:
            return "Moderate impact - good optimization opportunity"
        if score > 0.3:
            return "Low impact - minor optimization potential"
        return "Minimal impact - limited optimization opportunity"

    async def _detect_all_patterns(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, dict[str, Any]]:
        """Detect all types of patterns in time series."""
        patterns = {}

        try:
            for pattern_type, pattern_info in self.pattern_library.items():
                detector = pattern_info["detector"]
                pattern_result = await detector(time_series)

                if pattern_result:
                    patterns[pattern_type] = pattern_result

            return patterns

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return {}

    async def _detect_seasonal_patterns(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any] | None:
        """Detect seasonal patterns."""
        try:
            if len(time_series) < 24:  # Need at least 24 data points
                return None

            values = [point[1] for point in time_series]

            # Simple seasonal detection (weekly patterns)
            if len(values) >= 7:
                weekly_patterns = []
                for i in range(7):
                    weekly_values = values[i::7]
                    if len(weekly_values) >= 2:
                        weekly_patterns.append(np.mean(weekly_values))

                if len(weekly_patterns) == 7:
                    # Check for significant variation
                    variation = np.std(weekly_patterns) / np.mean(weekly_patterns)
                    if variation > 0.1:  # 10% variation threshold
                        return {
                            "description": f"Weekly seasonal pattern with {variation:.1%} variation",
                            "frequency": len(values) // 7,
                            "confidence": min(variation * 2, 1.0),
                            "pattern_data": weekly_patterns,
                        }

            return None

        except Exception as e:
            logger.error(f"Seasonal pattern detection failed: {e}")
            return None

    async def _detect_cyclical_patterns(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any] | None:
        """Detect cyclical patterns."""
        try:
            if len(time_series) < 10:
                return None

            values = [point[1] for point in time_series]

            # Simple cyclical detection using autocorrelation
            autocorr = np.correlate(values, values, mode="full")
            autocorr = autocorr[autocorr.size // 2 :]

            # Find peaks in autocorrelation (excluding lag 0)
            if len(autocorr) > 3:
                peaks = []
                for i in range(1, len(autocorr) - 1):
                    if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1]:
                        peaks.append((i, autocorr[i]))

                if peaks:
                    # Find the strongest peak
                    strongest_peak = max(peaks, key=lambda x: x[1])
                    lag, strength = strongest_peak

                    if strength > np.mean(autocorr) * 1.2:  # 20% above mean
                        return {
                            "description": f"Cyclical pattern with period of {lag} data points",
                            "frequency": len(values) // lag,
                            "confidence": min(strength / np.max(autocorr), 1.0),
                            "pattern_data": {"lag": lag, "strength": strength},
                        }

            return None

        except Exception as e:
            logger.error(f"Cyclical pattern detection failed: {e}")
            return None

    async def _detect_threshold_patterns(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any] | None:
        """Detect patterns around thresholds."""
        try:
            if len(time_series) < 10:
                return None

            values = [point[1] for point in time_series]
            mean_val = np.mean(values)
            std_val = np.std(values)

            # Define thresholds
            high_threshold = mean_val + std_val
            low_threshold = mean_val - std_val

            # Count crossings
            high_crossings = 0
            low_crossings = 0

            for i in range(1, len(values)):
                if (
                    values[i - 1] <= high_threshold < values[i]
                    or values[i - 1] >= high_threshold > values[i]
                ):
                    high_crossings += 1

                if (
                    values[i - 1] >= low_threshold > values[i]
                    or values[i - 1] <= low_threshold < values[i]
                ):
                    low_crossings += 1

            total_crossings = high_crossings + low_crossings

            if total_crossings >= 3:  # At least 3 threshold crossings
                return {
                    "description": f"Threshold pattern with {total_crossings} crossings",
                    "frequency": total_crossings,
                    "confidence": min(total_crossings / len(values), 1.0),
                    "pattern_data": {
                        "high_crossings": high_crossings,
                        "low_crossings": low_crossings,
                        "high_threshold": high_threshold,
                        "low_threshold": low_threshold,
                    },
                }

            return None

        except Exception as e:
            logger.error(f"Threshold pattern detection failed: {e}")
            return None

    async def _detect_spike_patterns(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any] | None:
        """Detect spike patterns."""
        try:
            if len(time_series) < 5:
                return None

            values = [point[1] for point in time_series]
            mean_val = np.mean(values)
            std_val = np.std(values)

            # Detect spikes (values > 2 standard deviations from mean)
            spikes = []
            for i, value in enumerate(values):
                if abs(value - mean_val) > 2 * std_val:
                    spikes.append((i, value))

            if len(spikes) >= 2:  # At least 2 spikes
                return {
                    "description": f"Spike pattern with {len(spikes)} significant spikes",
                    "frequency": len(spikes),
                    "confidence": min(len(spikes) / len(values), 1.0),
                    "pattern_data": {"spikes": spikes, "threshold": 2 * std_val},
                }

            return None

        except Exception as e:
            logger.error(f"Spike pattern detection failed: {e}")
            return None

    async def _detect_trend_patterns(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any] | None:
        """Detect trend patterns."""
        try:
            if len(time_series) < 5:
                return None

            trend_analysis = await self._analyze_trend(time_series)

            if trend_analysis["trend_strength"] > 0.3:
                return {
                    "description": f"{trend_analysis['direction']} trend pattern",
                    "frequency": 1,
                    "confidence": trend_analysis["trend_strength"],
                    "pattern_data": trend_analysis,
                }

            return None

        except Exception as e:
            logger.error(f"Trend pattern detection failed: {e}")
            return None

    async def _analyze_optimization_opportunities(
        self,
        time_series: list[tuple[datetime, float]],
    ) -> dict[str, Any]:
        """Analyze optimization opportunities."""
        try:
            if len(time_series) < 5:
                return {
                    "opportunity_score": 0.0,
                    "current_state": "unknown",
                    "improvement": "unknown",
                }

            values = [point[1] for point in time_series]

            # Calculate variance as optimization opportunity
            variance = np.var(values)
            mean_val = np.mean(values)
            coefficient_of_variation = (
                np.sqrt(variance) / mean_val if mean_val != 0 else 0
            )

            # Higher variance suggests more optimization potential
            opportunity_score = min(coefficient_of_variation, 1.0)

            # Determine current state
            if coefficient_of_variation < 0.1:
                current_state = "very stable"
                improvement = "limited optimization potential"
            elif coefficient_of_variation < 0.3:
                current_state = "stable"
                improvement = "moderate optimization potential"
            else:
                current_state = "variable"
                improvement = "high optimization potential"

            return {
                "opportunity_score": opportunity_score,
                "current_state": current_state,
                "improvement": improvement,
                "coefficient_of_variation": coefficient_of_variation,
            }

        except Exception as e:
            logger.error(f"Optimization analysis failed: {e}")
            return {
                "opportunity_score": 0.0,
                "current_state": "unknown",
                "improvement": "unknown",
            }

    async def _rank_insights(
        self,
        insights: list[InsightRecommendation],
    ) -> list[InsightRecommendation]:
        """Rank insights by priority and confidence."""
        try:
            # Define priority weights
            priority_weights = {
                InsightPriority.CRITICAL: 4,
                InsightPriority.HIGH: 3,
                InsightPriority.MEDIUM: 2,
                InsightPriority.LOW: 1,
            }

            # Define confidence weights
            confidence_weights = {
                InsightConfidence.VERY_HIGH: 5,
                InsightConfidence.HIGH: 4,
                InsightConfidence.MEDIUM: 3,
                InsightConfidence.LOW: 2,
                InsightConfidence.VERY_LOW: 1,
            }

            # Calculate ranking scores
            for insight in insights:
                priority_score = priority_weights.get(insight.priority, 1)
                confidence_score = confidence_weights.get(insight.confidence, 1)

                # Combined score
                insight.metadata["ranking_score"] = (
                    priority_score * confidence_score * insight.confidence_score
                )

            # Sort by ranking score (descending)
            insights.sort(
                key=lambda x: x.metadata.get("ranking_score", 0),
                reverse=True,
            )

            return insights

        except Exception as e:
            logger.error(f"Insight ranking failed: {e}")
            return insights

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the insight generation service."""
        try:
            # Test basic functionality
            test_data = {
                "test_metric": [
                    (
                        datetime.now() - timedelta(days=i),
                        10 + i + np.random.normal(0, 1),
                    )
                    for i in range(20, 0, -1)
                ],
            }

            insights = await self.generate_comprehensive_insights(test_data)

            return {
                "status": "healthy",
                "templates_loaded": len(self.insight_templates),
                "pattern_detectors": len(self.pattern_library),
                "test_insights_generated": len(insights),
                "cache_size": len(self.insight_cache),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "templates_loaded": 0,
                "pattern_detectors": 0,
                "test_insights_generated": 0,
            }


# Singleton instance
_insight_service = None


def get_insight_generation_service() -> InsightGenerationService:
    """Get or create insight generation service singleton."""
    global _insight_service
    if _insight_service is None:
        _insight_service = InsightGenerationService()
    return _insight_service
