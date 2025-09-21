#!/usr/bin/env python3
"""🧠 Vector Intelligence Database for Pattern Recognition
Personal Wealth Generation Platform - World-Class Engineering

This module implements an advanced vector intelligence database that stores and analyzes
historical patterns to improve trend detection and opportunity identification over time.
Optimized for single-user maximum performance and wealth generation.

Key Features:
- Multi-dimensional vector embeddings for market data, trends, and outcomes
- Pattern learning from historical success/failure rates
- Real-time similarity search for pattern matching
- Predictive modeling based on historical patterns
- Performance optimization for sub-second queries

Author: Claude (Personal Wealth Generation System)
Version: 1.0.0
Performance Target: <100ms query response, >90% pattern accuracy
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import aiofiles
import numpy as np
from scipy.spatial.distance import cosine
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorType(Enum):
    """Types of vectors stored in the intelligence database"""

    MARKET_PATTERN = "market_pattern"
    TREND_SIGNAL = "trend_signal"
    OPPORTUNITY_OUTCOME = "opportunity_outcome"
    SENTIMENT_PATTERN = "sentiment_pattern"
    NEWS_IMPACT = "news_impact"
    TECHNICAL_INDICATOR = "technical_indicator"
    CORRELATION_PATTERN = "correlation_pattern"


class PatternCategory(Enum):
    """Categories for pattern classification"""

    BULLISH_REVERSAL = "bullish_reversal"
    BEARISH_REVERSAL = "bearish_reversal"
    TREND_CONTINUATION = "trend_continuation"
    BREAKOUT_PATTERN = "breakout_pattern"
    CONSOLIDATION = "consolidation"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_SHIFT = "correlation_shift"
    SENTIMENT_EXTREME = "sentiment_extreme"


@dataclass
class VectorIntelligence:
    """Core data structure for vector intelligence entries"""

    vector_id: str
    vector_type: VectorType
    category: PatternCategory
    symbol: str
    timestamp: datetime
    embedding: list[float]  # High-dimensional vector representation
    metadata: dict[str, Any]
    outcome_data: dict[str, Any] | None = None
    success_rate: float | None = None
    confidence_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "vector_id": self.vector_id,
            "vector_type": self.vector_type.value,
            "category": self.category.value,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "embedding": self.embedding,
            "metadata": self.metadata,
            "outcome_data": self.outcome_data,
            "success_rate": self.success_rate,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorIntelligence":
        """Create from dictionary"""
        return cls(
            vector_id=data["vector_id"],
            vector_type=VectorType(data["vector_type"]),
            category=PatternCategory(data["category"]),
            symbol=data["symbol"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            embedding=data["embedding"],
            metadata=data["metadata"],
            outcome_data=data.get("outcome_data"),
            success_rate=data.get("success_rate"),
            confidence_score=data.get("confidence_score", 0.0),
        )


@dataclass
class PatternMatch:
    """Represents a pattern match result"""

    matched_vector: VectorIntelligence
    similarity_score: float
    confidence_adjustment: float
    predicted_outcome: dict[str, Any]
    risk_assessment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "vector_id": self.matched_vector.vector_id,
            "similarity_score": self.similarity_score,
            "confidence_adjustment": self.confidence_adjustment,
            "predicted_outcome": self.predicted_outcome,
            "risk_assessment": self.risk_assessment,
            "historical_success_rate": self.matched_vector.success_rate,
        }


class VectorEmbeddingGenerator:
    """Generates high-quality vector embeddings for different data types"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=128)  # Optimized dimensionality
        self._is_fitted = False

    async def generate_market_embedding(
        self,
        market_data: dict[str, Any],
    ) -> list[float]:
        """Generate embedding for market data patterns"""
        try:
            # Extract numerical features from market data
            features = []

            # Price-based features
            if "price_data" in market_data:
                price_data = market_data["price_data"]
                features.extend(
                    [
                        price_data.get("open", 0),
                        price_data.get("high", 0),
                        price_data.get("low", 0),
                        price_data.get("close", 0),
                        price_data.get("volume", 0),
                        price_data.get("price_change_pct", 0),
                        price_data.get("volatility", 0),
                    ],
                )

            # Technical indicators
            if "technical_indicators" in market_data:
                indicators = market_data["technical_indicators"]
                features.extend(
                    [
                        indicators.get("rsi", 50),
                        indicators.get("macd", 0),
                        indicators.get("bb_upper", 0),
                        indicators.get("bb_lower", 0),
                        indicators.get("sma_20", 0),
                        indicators.get("sma_50", 0),
                        indicators.get("ema_12", 0),
                        indicators.get("ema_26", 0),
                    ],
                )

            # Market context features
            if "market_context" in market_data:
                context = market_data["market_context"]
                features.extend(
                    [
                        context.get("market_sentiment", 0),
                        context.get("vix_level", 0),
                        context.get("sector_performance", 0),
                        context.get("news_sentiment", 0),
                    ],
                )

            # Ensure we have exactly 128 features (pad or truncate)
            while len(features) < 128:
                features.append(0.0)
            features = features[:128]

            # Normalize to prevent overflow
            features = np.array(features, dtype=np.float32)
            features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)

            return features.tolist()

        except Exception as e:
            logger.error(f"Error generating market embedding: {e}")
            return [0.0] * 128  # Return zero vector as fallback

    async def generate_trend_embedding(self, trend_data: dict[str, Any]) -> list[float]:
        """Generate embedding for trend patterns"""
        try:
            features = []

            # Trend strength indicators
            if "trend_metrics" in trend_data:
                metrics = trend_data["trend_metrics"]
                features.extend(
                    [
                        metrics.get("momentum_score", 0),
                        metrics.get("adoption_rate", 0),
                        metrics.get("social_mentions", 0),
                        metrics.get("search_volume", 0),
                        metrics.get("funding_amount", 0),
                        metrics.get("patent_count", 0),
                        metrics.get("research_papers", 0),
                    ],
                )

            # Sentiment indicators
            if "sentiment_data" in trend_data:
                sentiment = trend_data["sentiment_data"]
                features.extend(
                    [
                        sentiment.get("overall_sentiment", 0),
                        sentiment.get("expert_sentiment", 0),
                        sentiment.get("media_sentiment", 0),
                        sentiment.get("social_sentiment", 0),
                    ],
                )

            # Time-based features
            if "temporal_data" in trend_data:
                temporal = trend_data["temporal_data"]
                features.extend(
                    [
                        temporal.get("trend_age_days", 0),
                        temporal.get("growth_rate", 0),
                        temporal.get("acceleration", 0),
                        temporal.get("seasonality", 0),
                    ],
                )

            # Pad to 128 dimensions
            while len(features) < 128:
                features.append(0.0)
            features = features[:128]

            features = np.array(features, dtype=np.float32)
            features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)

            return features.tolist()

        except Exception as e:
            logger.error(f"Error generating trend embedding: {e}")
            return [0.0] * 128

    async def generate_outcome_embedding(
        self,
        outcome_data: dict[str, Any],
    ) -> list[float]:
        """Generate embedding for outcome patterns"""
        try:
            features = []

            # Performance metrics
            if "performance" in outcome_data:
                perf = outcome_data["performance"]
                features.extend(
                    [
                        perf.get("return_pct", 0),
                        perf.get("sharpe_ratio", 0),
                        perf.get("max_drawdown", 0),
                        perf.get("volatility", 0),
                        perf.get("win_rate", 0),
                        perf.get("profit_factor", 0),
                    ],
                )

            # Risk metrics
            if "risk_metrics" in outcome_data:
                risk = outcome_data["risk_metrics"]
                features.extend(
                    [
                        risk.get("var_95", 0),
                        risk.get("expected_shortfall", 0),
                        risk.get("beta", 0),
                        risk.get("correlation", 0),
                    ],
                )

            # Timing metrics
            if "timing" in outcome_data:
                timing = outcome_data["timing"]
                features.extend(
                    [
                        timing.get("entry_timing_score", 0),
                        timing.get("exit_timing_score", 0),
                        timing.get("hold_duration_days", 0),
                    ],
                )

            # Pad to 128 dimensions
            while len(features) < 128:
                features.append(0.0)
            features = features[:128]

            features = np.array(features, dtype=np.float32)
            features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)

            return features.tolist()

        except Exception as e:
            logger.error(f"Error generating outcome embedding: {e}")
            return [0.0] * 128


class VectorIntelligenceDatabase:
    """High-performance vector intelligence database for pattern recognition"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.data_path = config.get("data_path", "data/vector_intelligence/")
        self.vectors: dict[str, VectorIntelligence] = {}
        self.embedding_generator = VectorEmbeddingGenerator()
        self.pattern_clusters: dict[PatternCategory, list[str]] = {}
        self.success_metrics: dict[str, float] = {}

        # Performance optimization
        self.cache_size = config.get("cache_size", 10000)
        self.similarity_threshold = config.get("similarity_threshold", 0.85)
        self.min_pattern_count = config.get("min_pattern_count", 5)

        # Create data directory
        import os

        os.makedirs(self.data_path, exist_ok=True)

        logger.info(
            f"Vector Intelligence Database initialized with cache size: {self.cache_size}",
        )

    async def store_vector(self, vector: VectorIntelligence) -> bool:
        """Store a vector intelligence entry"""
        try:
            # Store in memory cache
            self.vectors[vector.vector_id] = vector

            # Update pattern clusters
            if vector.category not in self.pattern_clusters:
                self.pattern_clusters[vector.category] = []
            self.pattern_clusters[vector.category].append(vector.vector_id)

            # Persist to disk asynchronously
            await self._persist_vector(vector)

            logger.info(f"Stored vector: {vector.vector_id} ({vector.category.value})")
            return True

        except Exception as e:
            logger.error(f"Error storing vector {vector.vector_id}: {e}")
            return False

    async def find_similar_patterns(
        self,
        query_embedding: list[float],
        vector_type: VectorType,
        category: PatternCategory | None = None,
        limit: int = 10,
    ) -> list[PatternMatch]:
        """Find similar patterns using vector similarity search"""
        try:
            start_time = datetime.now()
            matches = []

            # Filter vectors by type and category
            candidate_vectors = []
            for vector_id, vector in self.vectors.items():
                if vector.vector_type == vector_type:
                    if category is None or vector.category == category:
                        candidate_vectors.append(vector)

            # Calculate similarity scores
            for vector in candidate_vectors:
                similarity = await self._calculate_similarity(
                    query_embedding,
                    vector.embedding,
                )

                if similarity >= self.similarity_threshold:
                    # Generate prediction based on historical outcome
                    predicted_outcome = await self._predict_outcome(vector)

                    # Calculate confidence adjustment based on historical success
                    confidence_adj = self._calculate_confidence_adjustment(vector)

                    # Assess risk based on historical patterns
                    risk_assessment = self._assess_risk(vector, similarity)

                    match = PatternMatch(
                        matched_vector=vector,
                        similarity_score=similarity,
                        confidence_adjustment=confidence_adj,
                        predicted_outcome=predicted_outcome,
                        risk_assessment=risk_assessment,
                    )

                    matches.append(match)

            # Sort by similarity and return top matches
            matches.sort(key=lambda x: x.similarity_score, reverse=True)

            # Performance logging
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Pattern search completed in {duration:.1f}ms, found {
                    len(matches)
                } matches",
            )

            return matches[:limit]

        except Exception as e:
            logger.error(f"Error finding similar patterns: {e}")
            return []

    async def learn_from_outcome(
        self,
        vector_id: str,
        actual_outcome: dict[str, Any],
    ) -> bool:
        """Learn from actual outcomes to improve future predictions"""
        try:
            if vector_id not in self.vectors:
                logger.warning(f"Vector {vector_id} not found for outcome learning")
                return False

            vector = self.vectors[vector_id]

            # Update outcome data
            vector.outcome_data = actual_outcome

            # Calculate success rate based on expected vs actual
            success_rate = await self._calculate_success_rate(vector, actual_outcome)
            vector.success_rate = success_rate

            # Update global success metrics
            pattern_key = f"{vector.category.value}_{vector.symbol}"
            if pattern_key not in self.success_metrics:
                self.success_metrics[pattern_key] = []

            # Store as list to maintain history
            if not isinstance(self.success_metrics[pattern_key], list):
                self.success_metrics[pattern_key] = [self.success_metrics[pattern_key]]

            self.success_metrics[pattern_key].append(success_rate)

            # Keep only recent history (last 100 outcomes)
            if len(self.success_metrics[pattern_key]) > 100:
                self.success_metrics[pattern_key] = self.success_metrics[pattern_key][
                    -100:
                ]

            # Persist updated vector
            await self._persist_vector(vector)

            logger.info(
                f"Learned from outcome for {vector_id}: {success_rate:.2f} success rate",
            )
            return True

        except Exception as e:
            logger.error(f"Error learning from outcome for {vector_id}: {e}")
            return False

    async def get_pattern_statistics(self, category: PatternCategory) -> dict[str, Any]:
        """Get comprehensive statistics for a pattern category"""
        try:
            if category not in self.pattern_clusters:
                return {"error": "Category not found"}

            vector_ids = self.pattern_clusters[category]
            vectors = [self.vectors[vid] for vid in vector_ids if vid in self.vectors]

            if not vectors:
                return {"error": "No vectors found for category"}

            # Calculate statistics
            success_rates = [
                v.success_rate for v in vectors if v.success_rate is not None
            ]
            confidence_scores = [v.confidence_score for v in vectors]

            stats = {
                "category": category.value,
                "total_patterns": len(vectors),
                "with_outcomes": len(success_rates),
                "avg_success_rate": np.mean(success_rates) if success_rates else 0.0,
                "success_rate_std": np.std(success_rates) if success_rates else 0.0,
                "avg_confidence": (
                    np.mean(confidence_scores) if confidence_scores else 0.0
                ),
                "min_success_rate": min(success_rates) if success_rates else 0.0,
                "max_success_rate": max(success_rates) if success_rates else 0.0,
                "patterns_by_symbol": {},
                "recent_performance": [],
            }

            # Group by symbol
            for vector in vectors:
                if vector.symbol not in stats["patterns_by_symbol"]:
                    stats["patterns_by_symbol"][vector.symbol] = 0
                stats["patterns_by_symbol"][vector.symbol] += 1

            # Recent performance (last 30 days)
            recent_cutoff = datetime.now() - timedelta(days=30)
            recent_vectors = [
                v
                for v in vectors
                if v.timestamp >= recent_cutoff and v.success_rate is not None
            ]

            if recent_vectors:
                stats["recent_performance"] = [
                    {
                        "symbol": v.symbol,
                        "success_rate": v.success_rate,
                        "timestamp": v.timestamp.isoformat(),
                    }
                    for v in sorted(
                        recent_vectors,
                        key=lambda x: x.timestamp,
                        reverse=True,
                    )[:10]
                ]

            return stats

        except Exception as e:
            logger.error(f"Error getting pattern statistics for {category}: {e}")
            return {"error": str(e)}

    async def _calculate_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)

            # Handle zero vectors
            if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
                return 0.0

            # Calculate cosine similarity (1 - cosine distance)
            similarity = 1 - cosine(vec1, vec2)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    async def _predict_outcome(self, vector: VectorIntelligence) -> dict[str, Any]:
        """Predict outcome based on historical vector data"""
        try:
            if not vector.outcome_data:
                return {"predicted_return": 0.0, "confidence": "low"}

            # Use historical outcome as baseline prediction
            outcome = vector.outcome_data.copy()

            # Adjust prediction based on pattern success rate
            if vector.success_rate is not None:
                confidence_level = (
                    "high"
                    if vector.success_rate > 0.7
                    else "medium"
                    if vector.success_rate > 0.4
                    else "low"
                )

                return {
                    "predicted_return": outcome.get("return_pct", 0.0)
                    * vector.success_rate,
                    "confidence": confidence_level,
                    "historical_success_rate": vector.success_rate,
                    "risk_adjusted_return": outcome.get("return_pct", 0.0)
                    * vector.success_rate
                    * 0.8,
                    "expected_hold_days": outcome.get("hold_duration_days", 5),
                }
            return {
                # Conservative estimate
                "predicted_return": outcome.get("return_pct", 0.0) * 0.5,
                "confidence": "low",
                "historical_success_rate": None,
            }

        except Exception as e:
            logger.error(f"Error predicting outcome: {e}")
            return {"predicted_return": 0.0, "confidence": "low", "error": str(e)}

    def _calculate_confidence_adjustment(self, vector: VectorIntelligence) -> float:
        """Calculate confidence adjustment based on historical success"""
        try:
            if vector.success_rate is None:
                return 0.0

            # Higher success rate increases confidence
            base_adjustment = (vector.success_rate - 0.5) * 2  # Scale to [-1, 1]

            # Factor in number of historical patterns
            pattern_key = f"{vector.category.value}_{vector.symbol}"
            pattern_count = len(self.success_metrics.get(pattern_key, []))

            # More data points increase confidence in the adjustment
            # Full confidence at 20+ patterns
            data_confidence = min(1.0, pattern_count / 20.0)

            return base_adjustment * data_confidence

        except Exception as e:
            logger.error(f"Error calculating confidence adjustment: {e}")
            return 0.0

    def _assess_risk(self, vector: VectorIntelligence, similarity: float) -> str:
        """Assess risk level based on vector pattern and similarity"""
        try:
            # Base risk assessment
            risk_score = 0.0

            # Factor in success rate
            if vector.success_rate is not None:
                risk_score += (
                    1.0 - vector.success_rate
                ) * 0.4  # Poor success = higher risk
            else:
                risk_score += 0.3  # Unknown success = moderate risk

            # Factor in similarity (lower similarity = higher risk)
            risk_score += (1.0 - similarity) * 0.3

            # Factor in pattern category
            high_risk_categories = [
                PatternCategory.VOLATILITY_SPIKE,
                PatternCategory.SENTIMENT_EXTREME,
            ]
            if vector.category in high_risk_categories:
                risk_score += 0.2

            # Factor in confidence score
            risk_score += (1.0 - vector.confidence_score) * 0.1

            # Classify risk level
            if risk_score <= 0.3:
                return "low"
            if risk_score <= 0.6:
                return "medium"
            return "high"

        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return "medium"

    async def _calculate_success_rate(
        self,
        vector: VectorIntelligence,
        actual_outcome: dict[str, Any],
    ) -> float:
        """Calculate success rate based on predicted vs actual outcome"""
        try:
            if not vector.outcome_data:
                return 0.5  # Neutral if no prediction

            predicted_return = vector.outcome_data.get("return_pct", 0.0)
            actual_return = actual_outcome.get("return_pct", 0.0)

            # Success metrics
            success_factors = []

            # Return direction accuracy
            if (predicted_return > 0 and actual_return > 0) or (
                predicted_return < 0 and actual_return < 0
            ):
                success_factors.append(1.0)  # Correct direction
            elif predicted_return == 0 and abs(actual_return) < 0.02:
                success_factors.append(1.0)  # Correct neutral prediction
            else:
                success_factors.append(0.0)  # Wrong direction

            # Return magnitude accuracy (within 50% is considered good)
            if predicted_return != 0:
                magnitude_accuracy = 1.0 - min(
                    1.0,
                    abs(actual_return - predicted_return) / abs(predicted_return),
                )
                success_factors.append(max(0.0, magnitude_accuracy))

            # Risk assessment accuracy
            predicted_risk = vector.metadata.get("expected_risk", "medium")
            actual_volatility = actual_outcome.get("volatility", 0.1)

            risk_mapping = {"low": 0.05, "medium": 0.15, "high": 0.3}
            expected_vol = risk_mapping.get(predicted_risk, 0.15)

            vol_accuracy = 1.0 - min(
                1.0,
                abs(actual_volatility - expected_vol) / expected_vol,
            )
            success_factors.append(max(0.0, vol_accuracy))

            # Overall success rate
            return np.mean(success_factors)

        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0.5

    async def _persist_vector(self, vector: VectorIntelligence):
        """Persist vector to disk for permanent storage"""
        try:
            filename = f"{self.data_path}/{vector.vector_id}.json"

            async with aiofiles.open(filename, "w") as f:
                await f.write(json.dumps(vector.to_dict(), indent=2))

        except Exception as e:
            logger.error(f"Error persisting vector {vector.vector_id}: {e}")

    async def load_from_disk(self):
        """Load existing vectors from disk storage"""
        try:
            import os

            if not os.path.exists(self.data_path):
                return

            vector_files = [
                f for f in os.listdir(self.data_path) if f.endswith(".json")
            ]

            for filename in vector_files:
                try:
                    filepath = os.path.join(self.data_path, filename)
                    async with aiofiles.open(filepath) as f:
                        data = json.loads(await f.read())
                        vector = VectorIntelligence.from_dict(data)

                        self.vectors[vector.vector_id] = vector

                        # Update clusters
                        if vector.category not in self.pattern_clusters:
                            self.pattern_clusters[vector.category] = []
                        if (
                            vector.vector_id
                            not in self.pattern_clusters[vector.category]
                        ):
                            self.pattern_clusters[vector.category].append(
                                vector.vector_id,
                            )

                except Exception as e:
                    logger.error(f"Error loading vector from {filename}: {e}")

            logger.info(f"Loaded {len(self.vectors)} vectors from disk")

        except Exception as e:
            logger.error(f"Error loading vectors from disk: {e}")


# Demo usage and testing
async def demo_vector_intelligence():
    """Demonstrate the vector intelligence database capabilities"""
    print("🧠 Vector Intelligence Database Demo - Personal Wealth Generation")
    print("=" * 80)

    # Initialize database
    config = {
        "data_path": "data/vector_intelligence/",
        "cache_size": 10000,
        "similarity_threshold": 0.75,
        "min_pattern_count": 3,
    }

    db = VectorIntelligenceDatabase(config)

    # Load existing data
    await db.load_from_disk()
    print(f"📊 Loaded {len(db.vectors)} existing vectors")

    # Generate sample vectors for demonstration
    embedding_gen = VectorEmbeddingGenerator()

    # Sample market pattern
    market_data = {
        "price_data": {
            "open": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 154.0,
            "volume": 1000000,
            "price_change_pct": 2.67,
            "volatility": 0.15,
        },
        "technical_indicators": {
            "rsi": 65.0,
            "macd": 1.2,
            "bb_upper": 157.0,
            "bb_lower": 147.0,
            "sma_20": 152.0,
            "sma_50": 148.0,
            "ema_12": 153.0,
            "ema_26": 150.0,
        },
        "market_context": {
            "market_sentiment": 0.6,
            "vix_level": 18.5,
            "sector_performance": 0.03,
            "news_sentiment": 0.4,
        },
    }

    market_embedding = await embedding_gen.generate_market_embedding(market_data)

    # Create sample vector
    sample_vector = VectorIntelligence(
        vector_id=f"market_pattern_{int(datetime.now().timestamp())}",
        vector_type=VectorType.MARKET_PATTERN,
        category=PatternCategory.BULLISH_REVERSAL,
        symbol="TSLA",
        timestamp=datetime.now(),
        embedding=market_embedding,
        metadata={
            "pattern_strength": 0.85,
            "expected_risk": "medium",
            "time_horizon": "5-10 days",
            "market_conditions": "bullish",
        },
        outcome_data={
            "return_pct": 8.5,
            "hold_duration_days": 7,
            "max_drawdown": -2.1,
            "sharpe_ratio": 1.8,
        },
        success_rate=0.75,
        confidence_score=0.85,
    )

    # Store the vector
    success = await db.store_vector(sample_vector)
    print(f"✅ Stored sample vector: {success}")

    # Find similar patterns
    similar_patterns = await db.find_similar_patterns(
        query_embedding=market_embedding,
        vector_type=VectorType.MARKET_PATTERN,
        category=PatternCategory.BULLISH_REVERSAL,
        limit=5,
    )

    print(f"\n🔍 Found {len(similar_patterns)} similar patterns:")
    for i, match in enumerate(similar_patterns[:3]):
        print(f"  {i + 1}. Similarity: {match.similarity_score:.3f}")
        print(
            f"     Predicted Return: {
                match.predicted_outcome.get('predicted_return', 0):.2f}%",
        )
        print(f"     Risk Level: {match.risk_assessment}")
        print(f"     Confidence Adj: {match.confidence_adjustment:.3f}")

    # Simulate learning from outcome
    actual_outcome = {
        "return_pct": 9.2,
        "hold_duration_days": 6,
        "max_drawdown": -1.8,
        "volatility": 0.12,
    }

    learned = await db.learn_from_outcome(sample_vector.vector_id, actual_outcome)
    print(f"\n📚 Learned from outcome: {learned}")

    # Get pattern statistics
    stats = await db.get_pattern_statistics(PatternCategory.BULLISH_REVERSAL)
    print("\n📈 Pattern Statistics for BULLISH_REVERSAL:")
    print(f"  Total Patterns: {stats.get('total_patterns', 0)}")
    print(f"  Average Success Rate: {stats.get('avg_success_rate', 0):.3f}")
    print(f"  Average Confidence: {stats.get('avg_confidence', 0):.3f}")

    print("\n🎯 Vector Intelligence Database ready for wealth generation!")


if __name__ == "__main__":
    asyncio.run(demo_vector_intelligence())
