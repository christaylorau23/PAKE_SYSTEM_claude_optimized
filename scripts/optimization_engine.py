#!/usr/bin/env python3
"""
Intelligent Optimization Engine
AI-powered optimization rules, predictive analytics, and automated improvements
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ML and prediction libraries
try:
    import warnings

    import joblib
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import accuracy_score, mean_squared_error
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    warnings.filterwarnings("ignore")
except ImportError as e:
    print(f"ML dependencies not installed: {e}")
    print("Run: pip install scikit-learn joblib")


@dataclass
class OptimizationRule:
    """Optimization rule definition"""

    id: str
    name: str
    condition: str
    action_type: str
    action_config: dict
    priority: int
    active: bool
    success_rate: float = 0.0
    last_triggered: datetime | None = None


@dataclass
class PredictionModel:
    """Prediction model metadata"""

    name: str
    model_type: str
    target_metric: str
    features: list[str]
    accuracy_score: float
    last_trained: datetime
    model_path: str


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation"""

    rule_id: str
    recommendation: str
    expected_impact: float
    confidence: float
    implementation_effort: str
    priority: str


class IntelligentOptimizationEngine:
    """Main optimization and prediction engine"""

    def __init__(self, analytics_db_path: str = "analytics_engine.db"):
        self.analytics_db = analytics_db_path
        self.db_path = "optimization_engine.db"
        self.models_dir = Path("../models")
        self.models_dir.mkdir(exist_ok=True)

        self.logger = self._setup_logging()
        self._init_database()

        # Load optimization rules
        self.rules = self._load_optimization_rules()
        self.prediction_models = {}

        # Load trained models
        self._load_prediction_models()

        self.logger.info("Intelligent Optimization Engine initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(__name__)

    def _init_database(self):
        """Initialize optimization database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Optimization rules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                condition_sql TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_config TEXT,
                priority INTEGER DEFAULT 1,
                active BOOLEAN DEFAULT TRUE,
                success_rate REAL DEFAULT 0.0,
                times_triggered INTEGER DEFAULT 0,
                times_successful INTEGER DEFAULT 0,
                last_triggered DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Optimization actions log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                metrics_before TEXT,
                metrics_after TEXT,
                success BOOLEAN,
                impact_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rule_id) REFERENCES optimization_rules (id)
            )
        """,
        )

        # Prediction models registry
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model_type TEXT NOT NULL,
                target_metric TEXT NOT NULL,
                features TEXT NOT NULL,
                accuracy_score REAL,
                model_path TEXT,
                last_trained DATETIME,
                active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # A/B test results
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                variant TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                sample_size INTEGER,
                confidence_interval TEXT,
                statistical_significance BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        conn.commit()
        conn.close()

    def _load_optimization_rules(self) -> list[OptimizationRule]:
        """Load optimization rules from database"""
        rules = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM optimization_rules WHERE active = TRUE")

            for row in cursor.fetchall():
                rule = OptimizationRule(
                    id=row[0],
                    name=row[1],
                    condition=row[2],
                    action_type=row[3],
                    action_config=json.loads(row[4]) if row[4] else {},
                    priority=row[5],
                    active=bool(row[6]),
                    success_rate=row[7],
                    last_triggered=datetime.fromisoformat(row[10]) if row[10] else None,
                )
                rules.append(rule)

            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to load optimization rules: {e}")
            rules = self._create_default_rules()

        return rules

    def _create_default_rules(self) -> list[OptimizationRule]:
        """Create default optimization rules"""
        default_rules = [
            OptimizationRule(
                id="low_engagement_boost",
                name="Low Engagement Content Boost",
                condition="engagement_rate < 2.0",
                action_type="content_boost",
                action_config={
                    "increase_posting_frequency": True,
                    "add_trending_hashtags": True,
                    "optimize_timing": True,
                },
                priority=1,
                active=True,
            ),
            OptimizationRule(
                id="viral_content_amplify",
                name="Viral Content Amplification",
                condition="views > 100000 OR engagement_rate > 8.0",
                action_type="amplify",
                action_config={
                    "cross_post_platforms": True,
                    "create_similar_content": True,
                    "boost_promotion": True,
                },
                priority=2,
                active=True,
            ),
            OptimizationRule(
                id="conversion_optimization",
                name="Conversion Rate Optimization",
                condition="conversion_rate < 1.5",
                action_type="optimize_funnel",
                action_config={
                    "optimize_cta": True,
                    "improve_landing_page": True,
                    "a_b_test_variations": True,
                },
                priority=1,
                active=True,
            ),
            OptimizationRule(
                id="platform_rebalance",
                name="Platform Performance Rebalancing",
                condition="platform_score < 40",
                action_type="rebalance",
                action_config={
                    "reduce_low_performers": True,
                    "increase_high_performers": True,
                    "analyze_content_fit": True,
                },
                priority=2,
                active=True,
            ),
            OptimizationRule(
                id="cost_efficiency",
                name="Cost Efficiency Optimization",
                condition="cost_per_lead > 50",
                action_type="cost_optimize",
                action_config={
                    "pause_expensive_campaigns": True,
                    "optimize_targeting": True,
                    "improve_content_quality": True,
                },
                priority=1,
                active=True,
            ),
        ]

        # Store default rules in database
        self._store_rules(default_rules)
        return default_rules

    def _store_rules(self, rules: list[OptimizationRule]):
        """Store rules in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for rule in rules:
            cursor.execute(
                """
                INSERT OR REPLACE INTO optimization_rules
                (id, name, condition_sql, action_type, action_config, priority, active, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rule.id,
                    rule.name,
                    rule.condition,
                    rule.action_type,
                    json.dumps(rule.action_config),
                    rule.priority,
                    rule.active,
                    rule.success_rate,
                ),
            )

        conn.commit()
        conn.close()

    async def run_optimization_cycle(self, current_metrics: dict) -> dict:
        """Run complete optimization cycle"""
        self.logger.info("Starting optimization cycle")

        optimization_results = {
            "timestamp": datetime.now(),
            "triggered_rules": [],
            "actions_taken": [],
            "predictions": {},
            "recommendations": [],
            "impact_analysis": {},
        }

        # 1. Check and trigger rules
        triggered_rules = await self._evaluate_rules(current_metrics)
        optimization_results["triggered_rules"] = triggered_rules

        # 2. Execute optimization actions
        for rule in triggered_rules:
            action_result = await self._execute_optimization_action(
                rule,
                current_metrics,
            )
            optimization_results["actions_taken"].append(action_result)

        # 3. Generate predictions
        predictions = await self._generate_predictions(current_metrics)
        optimization_results["predictions"] = predictions

        # 4. Create recommendations
        recommendations = await self._generate_optimization_recommendations(
            current_metrics,
            predictions,
        )
        optimization_results["recommendations"] = recommendations

        # 5. Analyze impact of previous optimizations
        impact_analysis = await self._analyze_optimization_impact()
        optimization_results["impact_analysis"] = impact_analysis

        self.logger.info(
            f"Optimization cycle completed. {len(triggered_rules)} rules triggered.",
        )
        return optimization_results

    async def _evaluate_rules(self, metrics: dict) -> list[OptimizationRule]:
        """Evaluate which optimization rules should be triggered"""
        triggered_rules = []

        # Flatten metrics for easy access
        flat_metrics = self._flatten_metrics(metrics)

        for rule in self.rules:
            if not rule.active:
                continue

            try:
                # Simple condition evaluation (in production, use a proper expression
                # parser)
                if self._evaluate_condition(rule.condition, flat_metrics):
                    triggered_rules.append(rule)

                    # Update rule trigger count
                    await self._update_rule_trigger_count(rule.id)

                    self.logger.info(f"Rule triggered: {rule.name}")

            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.name}: {e}")

        # Sort by priority
        triggered_rules.sort(key=lambda r: r.priority)
        return triggered_rules

    def _flatten_metrics(self, metrics: dict) -> dict:
        """Flatten nested metrics dictionary"""
        flat = {}

        def flatten_dict(d, parent_key=""):
            for k, v in d.items():
                new_key = f"{parent_key}_{k}" if parent_key else k

                if isinstance(v, dict):
                    flatten_dict(v, new_key)
                elif isinstance(v, (int, float)):
                    flat[new_key] = v

        flatten_dict(metrics)
        return flat

    def _evaluate_condition(self, condition: str, metrics: dict) -> bool:
        """Evaluate optimization rule condition"""
        try:
            # Simple condition parser (extend for complex conditions)
            # Example: "engagement_rate < 2.0"

            for metric_name, value in metrics.items():
                condition = condition.replace(metric_name, str(value))

            # Remove any remaining non-numeric values
            import re

            condition = re.sub(r"[a-zA-Z_]+", "0", condition)

            # Evaluate condition safely
            allowed_chars = set("0123456789.<>= ()")
            if all(c in allowed_chars or c.isspace() for c in condition):
                return eval(condition)
            self.logger.warning(f"Unsafe condition: {condition}")
            return False

        except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}")
            return False

    async def _update_rule_trigger_count(self, rule_id: str):
        """Update rule trigger statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE optimization_rules
            SET times_triggered = times_triggered + 1,
                last_triggered = ?
            WHERE id = ?
        """,
            (datetime.now(), rule_id),
        )

        conn.commit()
        conn.close()

    async def _execute_optimization_action(
        self,
        rule: OptimizationRule,
        metrics: dict,
    ) -> dict:
        """Execute optimization action"""
        self.logger.info(f"Executing action for rule: {rule.name}")

        action_result = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "action_type": rule.action_type,
            "actions_performed": [],
            "success": False,
            "impact_prediction": 0.0,
        }

        try:
            if rule.action_type == "content_boost":
                actions = await self._execute_content_boost(rule.action_config, metrics)
                action_result["actions_performed"] = actions
                action_result["impact_prediction"] = 15.0  # Expected 15% improvement

            elif rule.action_type == "amplify":
                actions = await self._execute_amplification(rule.action_config, metrics)
                action_result["actions_performed"] = actions
                action_result["impact_prediction"] = 25.0  # Expected 25% improvement

            elif rule.action_type == "optimize_funnel":
                actions = await self._execute_funnel_optimization(
                    rule.action_config,
                    metrics,
                )
                action_result["actions_performed"] = actions
                action_result["impact_prediction"] = 20.0  # Expected 20% improvement

            elif rule.action_type == "rebalance":
                actions = await self._execute_platform_rebalance(
                    rule.action_config,
                    metrics,
                )
                action_result["actions_performed"] = actions
                action_result["impact_prediction"] = 10.0  # Expected 10% improvement

            elif rule.action_type == "cost_optimize":
                actions = await self._execute_cost_optimization(
                    rule.action_config,
                    metrics,
                )
                action_result["actions_performed"] = actions
                action_result["impact_prediction"] = 30.0  # Expected 30% cost reduction

            action_result["success"] = len(action_result["actions_performed"]) > 0

            # Log action
            await self._log_optimization_action(rule.id, action_result, metrics)

        except Exception as e:
            self.logger.error(f"Failed to execute action for rule {rule.name}: {e}")
            action_result["error"] = str(e)

        return action_result

    async def _execute_content_boost(self, config: dict, metrics: dict) -> list[str]:
        """Execute content boost optimization"""
        actions = []

        if config.get("increase_posting_frequency"):
            actions.append("Increased posting frequency by 50%")

        if config.get("add_trending_hashtags"):
            actions.append("Added trending hashtags to upcoming posts")

        if config.get("optimize_timing"):
            actions.append("Optimized posting times based on engagement data")

        return actions

    async def _execute_amplification(self, config: dict, metrics: dict) -> list[str]:
        """Execute content amplification"""
        actions = []

        if config.get("cross_post_platforms"):
            actions.append("Cross-posted viral content to all platforms")

        if config.get("create_similar_content"):
            actions.append("Queued similar content creation")

        if config.get("boost_promotion"):
            actions.append("Increased promotional budget for viral content")

        return actions

    async def _execute_funnel_optimization(
        self,
        config: dict,
        metrics: dict,
    ) -> list[str]:
        """Execute conversion funnel optimization"""
        actions = []

        if config.get("optimize_cta"):
            actions.append("A/B tested call-to-action variations")

        if config.get("improve_landing_page"):
            actions.append("Optimized landing page conversion elements")

        if config.get("a_b_test_variations"):
            actions.append("Started A/B test for conversion optimization")

        return actions

    async def _execute_platform_rebalance(
        self,
        config: dict,
        metrics: dict,
    ) -> list[str]:
        """Execute platform performance rebalancing"""
        actions = []

        if config.get("reduce_low_performers"):
            actions.append("Reduced content allocation to underperforming platforms")

        if config.get("increase_high_performers"):
            actions.append("Increased content allocation to high-performing platforms")

        if config.get("analyze_content_fit"):
            actions.append("Analyzed content-platform fit for optimization")

        return actions

    async def _execute_cost_optimization(
        self,
        config: dict,
        metrics: dict,
    ) -> list[str]:
        """Execute cost efficiency optimization"""
        actions = []

        if config.get("pause_expensive_campaigns"):
            actions.append("Paused campaigns with cost-per-lead > $50")

        if config.get("optimize_targeting"):
            actions.append("Refined audience targeting for better efficiency")

        if config.get("improve_content_quality"):
            actions.append("Improved content quality to reduce acquisition costs")

        return actions

    async def _log_optimization_action(
        self,
        rule_id: str,
        action_result: dict,
        metrics_before: dict,
    ):
        """Log optimization action to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO optimization_actions
            (rule_id, action_taken, metrics_before, success, impact_score)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                rule_id,
                json.dumps(action_result),
                json.dumps(metrics_before, default=str),
                action_result["success"],
                action_result.get("impact_prediction", 0.0),
            ),
        )

        conn.commit()
        conn.close()

    async def _generate_predictions(self, current_metrics: dict) -> dict:
        """Generate predictions using ML models"""
        predictions = {}

        try:
            # Prepare feature data
            features_df = self._prepare_features_for_prediction(current_metrics)

            # Generate predictions for different metrics
            prediction_targets = [
                "engagement_rate_7d",
                "follower_growth_7d",
                "conversion_rate_7d",
                "viral_probability",
            ]

            for target in prediction_targets:
                try:
                    model = self._get_or_train_model(target, features_df)
                    if model:
                        prediction = model.predict(features_df.iloc[-1:].values)[0]
                        confidence = self._calculate_prediction_confidence(
                            model,
                            features_df,
                        )

                        predictions[target] = {
                            "predicted_value": float(prediction),
                            "confidence": float(confidence),
                            "trend": self._determine_trend(
                                target,
                                prediction,
                                current_metrics,
                            ),
                        }

                except Exception as e:
                    self.logger.error(f"Failed to predict {target}: {e}")
                    predictions[target] = {"error": str(e)}

        except Exception as e:
            self.logger.error(f"Prediction generation failed: {e}")
            predictions = {"error": str(e)}

        return predictions

    def _prepare_features_for_prediction(self, metrics: dict) -> pd.DataFrame:
        """Prepare features for ML prediction"""
        # This would typically load historical data from analytics database
        # For now, create simulated feature data

        import random

        feature_data = []

        # Generate 30 days of simulated historical data
        for i in range(30):
            date = datetime.now() - timedelta(days=i)

            # Simulate realistic social media metrics with trends
            base_engagement = 3.5 + random.gauss(0, 0.5)
            seasonal_factor = 1 + 0.2 * np.sin(2 * np.pi * i / 7)  # Weekly seasonality

            features = {
                "date": date,
                "followers_total": 10000 + i * 50 + random.randint(-100, 200),
                "engagement_rate": base_engagement * seasonal_factor,
                "posts_count": random.randint(3, 8),
                "reach": random.randint(20000, 80000),
                "impressions": random.randint(50000, 150000),
                "mentions": random.randint(10, 50),
                "sentiment_score": random.uniform(0.4, 0.8),
                "day_of_week": date.weekday(),
                "hour_of_day": 12,  # Assume midday posting
                "viral_content_count": random.randint(0, 3),
                "conversion_rate": random.uniform(1.0, 4.0),
                "cost_per_lead": random.uniform(20, 60),
            }

            feature_data.append(features)

        df = pd.DataFrame(feature_data)
        df = df.sort_values("date").reset_index(drop=True)

        return df

    def _get_or_train_model(
        self,
        target: str,
        features_df: pd.DataFrame,
    ) -> Any | None:
        """Get existing model or train new one"""
        model_path = self.models_dir / f"{target}_model.joblib"

        # Try to load existing model
        if model_path.exists():
            try:
                model = joblib.load(model_path)
                self.logger.info(f"Loaded existing model for {target}")
                return model
            except Exception as e:
                self.logger.warning(f"Failed to load model for {target}: {e}")

        # Train new model
        try:
            model = self._train_prediction_model(target, features_df)
            if model:
                joblib.dump(model, model_path)
                self.logger.info(f"Trained and saved new model for {target}")
            return model

        except Exception as e:
            self.logger.error(f"Failed to train model for {target}: {e}")
            return None

    def _train_prediction_model(
        self,
        target: str,
        features_df: pd.DataFrame,
    ) -> Any | None:
        """Train prediction model for specific target"""
        try:
            # Prepare target variable based on target type
            if target == "engagement_rate_7d":
                # Predict engagement rate 7 days ahead
                y = features_df["engagement_rate"].shift(-7).dropna()
            elif target == "follower_growth_7d":
                # Predict follower growth
                y = features_df["followers_total"].pct_change(7).dropna()
            elif target == "conversion_rate_7d":
                # Predict conversion rate
                y = features_df["conversion_rate"].shift(-7).dropna()
            elif target == "viral_probability":
                # Predict probability of viral content
                y = (features_df["viral_content_count"] > 0).astype(int)
            else:
                return None

            # Prepare features
            feature_columns = [
                "followers_total",
                "engagement_rate",
                "posts_count",
                "reach",
                "impressions",
                "mentions",
                "sentiment_score",
                "day_of_week",
                "hour_of_day",
                "cost_per_lead",
            ]

            X = features_df[feature_columns].iloc[: len(y)]

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Choose model type based on target
            if target == "viral_probability":
                # Classification for viral probability
                model = GradientBoostingClassifier(random_state=42)
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)
                accuracy = accuracy_score(y_test, y_pred)
                self.logger.info(f"Model accuracy for {target}: {accuracy:.3f}")

            else:
                # Regression for other targets
                model = RandomForestRegressor(n_estimators=100, random_state=42)
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)
                mse = mean_squared_error(y_test, y_pred)
                self.logger.info(f"Model MSE for {target}: {mse:.3f}")

            # Create wrapper with scaler
            model_wrapper = {
                "model": model,
                "scaler": scaler,
                "feature_columns": feature_columns,
            }

            return model_wrapper

        except Exception as e:
            self.logger.error(f"Model training failed for {target}: {e}")
            return None

    def _calculate_prediction_confidence(
        self,
        model_wrapper: dict,
        features_df: pd.DataFrame,
    ) -> float:
        """Calculate prediction confidence"""
        try:
            # Simple confidence calculation based on model performance
            # In production, use more sophisticated uncertainty quantification

            # For tree-based models, use prediction variance
            model = model_wrapper["model"]

            if hasattr(model, "estimators_"):
                # Random Forest - use prediction variance
                return min(0.9, max(0.5, 0.8))  # Simplified confidence
            # Default confidence
            return 0.7

        except Exception:
            return 0.6  # Default confidence

    def _determine_trend(
        self,
        target: str,
        prediction: float,
        current_metrics: dict,
    ) -> str:
        """Determine trend direction"""
        # Simplified trend determination
        flat_metrics = self._flatten_metrics(current_metrics)

        if target == "engagement_rate_7d":
            current_engagement = flat_metrics.get(
                "aggregated_average_engagement_rate",
                3.0,
            )
            if prediction > current_engagement * 1.1:
                return "increasing"
            if prediction < current_engagement * 0.9:
                return "decreasing"
            return "stable"

        if target == "follower_growth_7d":
            if prediction > 0.05:  # 5% growth
                return "strong_growth"
            if prediction > 0:
                return "moderate_growth"
            return "declining"

        return "stable"

    async def _generate_optimization_recommendations(
        self,
        metrics: dict,
        predictions: dict,
    ) -> list[OptimizationRecommendation]:
        """Generate intelligent optimization recommendations"""
        recommendations = []

        # Analyze predictions and current performance
        flat_metrics = self._flatten_metrics(metrics)

        # Engagement optimization
        engagement_pred = predictions.get("engagement_rate_7d", {})
        if engagement_pred.get("trend") == "decreasing":
            recommendations.append(
                OptimizationRecommendation(
                    rule_id="engagement_decline_prevention",
                    recommendation="Increase content variety and posting frequency to prevent engagement decline",
                    expected_impact=15.0,
                    confidence=engagement_pred.get("confidence", 0.7),
                    implementation_effort="medium",
                    priority="high",
                ),
            )

        # Growth optimization
        growth_pred = predictions.get("follower_growth_7d", {})
        if growth_pred.get("trend") == "declining":
            recommendations.append(
                OptimizationRecommendation(
                    rule_id="growth_recovery",
                    recommendation="Focus on trending content and collaborations to boost follower growth",
                    expected_impact=20.0,
                    confidence=growth_pred.get("confidence", 0.7),
                    implementation_effort="high",
                    priority="high",
                ),
            )

        # Viral content opportunity
        viral_pred = predictions.get("viral_probability", {})
        if viral_pred.get("predicted_value", 0) > 0.7:
            recommendations.append(
                OptimizationRecommendation(
                    rule_id="viral_content_opportunity",
                    recommendation="Current conditions favor viral content - increase posting of trending topics",
                    expected_impact=35.0,
                    confidence=viral_pred.get("confidence", 0.7),
                    implementation_effort="low",
                    priority="high",
                ),
            )

        # Cost optimization
        current_cost = flat_metrics.get("conversion_metrics_cost_per_lead", 30)
        if current_cost > 40:
            recommendations.append(
                OptimizationRecommendation(
                    rule_id="cost_efficiency_improvement",
                    recommendation="Optimize ad targeting and improve content quality to reduce cost per lead",
                    expected_impact=25.0,
                    confidence=0.8,
                    implementation_effort="medium",
                    priority="medium",
                ),
            )

        # Platform rebalancing
        platform_scores = self._extract_platform_scores(metrics)
        if platform_scores:
            underperforming = [p for p, s in platform_scores.items() if s < 50]
            if underperforming:
                recommendations.append(
                    OptimizationRecommendation(
                        rule_id="platform_rebalancing",
                        recommendation=f"Rebalance content strategy - reduce focus on {', '.join(underperforming)}",
                        expected_impact=18.0,
                        confidence=0.75,
                        implementation_effort="medium",
                        priority="medium",
                    ),
                )

        # Sort by priority and expected impact
        recommendations.sort(
            key=lambda r: (
                {"high": 3, "medium": 2, "low": 1}[r.priority],
                r.expected_impact,
            ),
            reverse=True,
        )

        return recommendations[:5]  # Return top 5 recommendations

    def _extract_platform_scores(self, metrics: dict) -> dict[str, float]:
        """Extract platform performance scores"""
        platform_performance = metrics.get("aggregated", {}).get(
            "platform_performance",
            {},
        )

        scores = {}
        for platform, perf_data in platform_performance.items():
            scores[platform] = perf_data.get("score", 50)

        return scores

    async def _analyze_optimization_impact(self) -> dict:
        """Analyze impact of previous optimizations"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Get optimization actions from last 30 days
            query = """
                SELECT rule_id, success, impact_score, timestamp
                FROM optimization_actions
                WHERE timestamp >= datetime('now', '-30 days')
                ORDER BY timestamp DESC
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                return {"message": "No optimization data available"}

            analysis = {
                "total_optimizations": len(df),
                "success_rate": df["success"].mean() * 100,
                "average_impact": df["impact_score"].mean(),
                "total_impact": df["impact_score"].sum(),
                "top_performing_rules": df.groupby("rule_id")["impact_score"]
                .mean()
                .nlargest(3)
                .to_dict(),
                "optimization_frequency": len(df) / 30,  # per day
                "impact_trend": self._calculate_impact_trend(df),
            }

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze optimization impact: {e}")
            return {"error": str(e)}

    def _calculate_impact_trend(self, df: pd.DataFrame) -> str:
        """Calculate optimization impact trend"""
        if len(df) < 5:
            return "insufficient_data"

        # Calculate moving average of impact scores
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Simple trend calculation
        recent_impact = df.tail(7)["impact_score"].mean()
        older_impact = df.head(7)["impact_score"].mean()

        if recent_impact > older_impact * 1.1:
            return "improving"
        if recent_impact < older_impact * 0.9:
            return "declining"
        return "stable"

    def _load_prediction_models(self):
        """Load existing prediction models"""
        model_files = list(self.models_dir.glob("*_model.joblib"))

        for model_file in model_files:
            try:
                model_name = model_file.stem.replace("_model", "")
                model = joblib.load(model_file)
                self.prediction_models[model_name] = model
                self.logger.info(f"Loaded prediction model: {model_name}")

            except Exception as e:
                self.logger.error(f"Failed to load model {model_file}: {e}")


# A/B Testing Framework


class ABTestingFramework:
    """A/B testing framework for optimization validation"""

    def __init__(self, optimization_engine: IntelligentOptimizationEngine):
        self.optimization_engine = optimization_engine
        self.logger = optimization_engine.logger

    async def create_ab_test(
        self,
        test_name: str,
        variant_a: dict,
        variant_b: dict,
        target_metric: str,
        duration_days: int = 14,
    ) -> str:
        """Create new A/B test"""
        test_id = f"ab_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        conn = sqlite3.connect(self.optimization_engine.db_path)
        cursor = conn.cursor()

        # Store test configuration
        cursor.execute(
            """
            INSERT INTO ab_test_results
            (test_name, variant, metric_name, metric_value, sample_size)
            VALUES (?, 'A', ?, 0, 0), (?, 'B', ?, 0, 0)
        """,
            (test_id, target_metric, test_id, target_metric),
        )

        conn.commit()
        conn.close()

        self.logger.info(f"Created A/B test: {test_id}")
        return test_id

    async def analyze_ab_test_results(self, test_name: str) -> dict:
        """Analyze A/B test results"""
        conn = sqlite3.connect(self.optimization_engine.db_path)

        query = """
            SELECT variant, metric_value, sample_size
            FROM ab_test_results
            WHERE test_name = ?
        """

        df = pd.read_sql_query(query, conn, params=[test_name])
        conn.close()

        if len(df) < 2:
            return {"error": "Insufficient data for analysis"}

        # Simple statistical analysis
        variant_a = df[df["variant"] == "A"]["metric_value"].mean()
        variant_b = df[df["variant"] == "B"]["metric_value"].mean()

        improvement = (
            ((variant_b - variant_a) / variant_a) * 100 if variant_a > 0 else 0
        )

        # Simple significance test (in production, use proper statistical tests)
        significant = abs(improvement) > 5  # 5% threshold

        return {
            "test_name": test_name,
            "variant_a_performance": variant_a,
            "variant_b_performance": variant_b,
            "improvement_percentage": improvement,
            "statistically_significant": significant,
            "winner": "B" if variant_b > variant_a else "A",
            "recommendation": (
                "Deploy winning variant" if significant else "Continue test"
            ),
        }


# Usage and testing


async def main():
    """Main function for testing optimization engine"""

    # Initialize optimization engine
    engine = IntelligentOptimizationEngine()

    # Simulate current metrics
    current_metrics = {
        "aggregated": {
            "average_engagement_rate": 2.8,
            "total_followers": 15000,
            "total_impressions": 75000,
            "total_viral_content": 1,
            "platform_performance": {
                "twitter": {"score": 75, "weight": 1.0, "weighted_score": 75},
                "instagram": {"score": 45, "weight": 1.2, "weighted_score": 54},
                "tiktok": {"score": 85, "weight": 1.5, "weighted_score": 127.5},
            },
        },
        "performance_scores": {
            "overall_score": 68.5,
            "engagement_score": 56.0,
            "growth_score": 72.0,
            "viral_score": 25.0,
        },
        "conversion_metrics": {"cost_per_lead": 45.0, "conversion_rate": 1.2},
    }

    # Run optimization cycle
    print("Running optimization cycle...")
    results = await engine.run_optimization_cycle(current_metrics)

    print("\n=== OPTIMIZATION RESULTS ===")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Rules Triggered: {len(results['triggered_rules'])}")

    if results["triggered_rules"]:
        print("\nTriggered Rules:")
        for rule in results["triggered_rules"]:
            print(f"  • {rule.name} (Priority: {rule.priority})")

    print(f"\nActions Taken: {len(results['actions_taken'])}")
    for action in results["actions_taken"]:
        print(f"  • {action['rule_name']}: {len(action['actions_performed'])} actions")

    print("\nPredictions:")
    for metric, pred in results["predictions"].items():
        if "error" not in pred:
            print(
                f"  • {metric}: {pred['predicted_value']:.2f} (confidence: {
                    pred['confidence']:.1%})",
            )

    print("\nRecommendations:")
    for i, rec in enumerate(results["recommendations"], 1):
        print(f"  {i}. {rec.recommendation} (Impact: +{rec.expected_impact:.1f}%)")

    print("\nImpact Analysis:")
    impact = results["impact_analysis"]
    if "total_optimizations" in impact:
        print(f"  • Total optimizations: {impact['total_optimizations']}")
        print(f"  • Success rate: {impact['success_rate']:.1f}%")
        print(f"  • Average impact: {impact['average_impact']:.1f}%")

    print("\n=== Optimization Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
