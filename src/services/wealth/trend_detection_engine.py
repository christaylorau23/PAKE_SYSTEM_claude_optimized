#!/usr/bin/env python3
"""🤖 AI-Powered Trend Detection Engine with Google Trends Integration
Personal Wealth Generation Platform - World-Class Engineering

Enhanced trend detection system that combines Google Trends data with multi-source
analysis to identify emerging trends 2-6 months before mainstream adoption,
providing maximum profit potential through early opportunity identification.

Enhanced Features:
- Google Trends integration for search behavior analysis
- Multi-source trend analysis (patents, papers, funding, social sentiment)
- AI-powered pattern recognition and correlation analysis
- Investment opportunity mapping from trends to stocks/sectors
- Early-stage trend scoring with confidence intervals
- Automated trend monitoring and alert system
- Real-time trend momentum tracking

Author: Claude (Personal Wealth Generation System)
Version: 2.0.0 - Enhanced with Google Trends
Performance Target: <3s comprehensive trend analysis, 90% early detection accuracy
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np

# AI/ML imports
try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from transformers import pipeline

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Google Trends integration
try:
    from .google_trends_analyzer import GeographicRegion, GoogleTrendsIntegrationService

    HAS_GOOGLE_TRENDS = True
except ImportError:
    HAS_GOOGLE_TRENDS = False

logger = logging.getLogger(__name__)


class TrendStage(Enum):
    EMERGENCE = "emergence"  # Academic papers, early patents
    EARLY_ADOPTION = "early_adoption"  # Startups, first funding rounds
    GROWTH = "growth"  # Corporate adoption, major funding
    MAINSTREAM = "mainstream"  # IPOs, mass market adoption
    MATURITY = "maturity"  # Market saturation


class TrendCategory(Enum):
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    ENERGY = "energy"
    CONSUMER = "consumer"
    ENTERPRISE = "enterprise"
    INFRASTRUCTURE = "infrastructure"
    AI_ML = "artificial_intelligence"


class InvestmentVehicle(Enum):
    STOCK = "stock"
    ETF = "etf"
    PRIVATE_EQUITY = "private_equity"
    CRYPTO = "cryptocurrency"
    COMMODITY = "commodity"
    STARTUP = "startup"


@dataclass
class TrendSignal:
    """Individual signal contributing to trend detection"""

    source: str  # "patents", "papers", "funding", "news", etc.
    signal_type: str  # "volume_increase", "sentiment_positive", etc.
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    data_points: int  # Number of data points supporting signal
    time_period: str  # "last_30_days", "last_quarter", etc.
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergingTrend:
    """Represents an emerging trend with investment opportunities"""

    name: str
    description: str
    category: TrendCategory
    stage: TrendStage

    # Trend strength metrics
    overall_score: float  # 0.0 to 1.0 composite trend strength
    confidence: float  # 0.0 to 1.0 confidence in trend detection
    momentum: float  # -1.0 to 1.0 trend momentum (acceleration)

    # Timeline estimates
    estimated_mainstream_date: datetime | None = None
    current_adoption_percentage: float = 0.0

    # Supporting signals
    signals: list[TrendSignal] = field(default_factory=list)

    # Investment opportunities
    investment_opportunities: list[dict[str, Any]] = field(default_factory=list)

    # Market potential
    estimated_market_size: float | None = None  # in billions USD
    growth_rate_estimate: float | None = None  # annual percentage

    # Metadata
    detected_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Risk factors
    risk_factors: list[str] = field(default_factory=list)
    competitive_landscape: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "stage": self.stage.value,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "momentum": self.momentum,
            "estimated_mainstream_date": (
                self.estimated_mainstream_date.isoformat()
                if self.estimated_mainstream_date
                else None
            ),
            "current_adoption_percentage": self.current_adoption_percentage,
            "signals": [
                {
                    "source": s.source,
                    "signal_type": s.signal_type,
                    "strength": s.strength,
                    "confidence": s.confidence,
                    "data_points": s.data_points,
                    "time_period": s.time_period,
                }
                for s in self.signals
            ],
            "investment_opportunities": self.investment_opportunities,
            "estimated_market_size": self.estimated_market_size,
            "growth_rate_estimate": self.growth_rate_estimate,
            "risk_factors": self.risk_factors,
            "competitive_landscape": self.competitive_landscape,
            "detected_at": self.detected_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


class PatentAnalyzer:
    """Analyzes patent filings for emerging technology trends"""

    def __init__(self):
        self.uspto_base_url = "https://developer.uspto.gov/ptab-api/v1"
        # Note: Real implementation would use proper USPTO API credentials

    async def analyze_patent_trends(
        self,
        keywords: list[str],
        months_back: int = 12,
    ) -> dict[str, Any]:
        """Analyze patent filing trends for given keywords"""
        # Mock patent data - in production would use real USPTO API
        trend_data = {}

        for keyword in keywords:
            # Simulate patent filing analysis
            monthly_filings = np.random.poisson(50, months_back)  # Mock data
            recent_trend = monthly_filings[-3:].mean() / monthly_filings[:-3].mean()

            # Calculate growth metrics
            total_filings = sum(monthly_filings)
            growth_rate = (
                (monthly_filings[-1] - monthly_filings[0]) / monthly_filings[0]
                if monthly_filings[0] > 0
                else 0
            )

            # Extract key companies (mock data)
            top_companies = [
                {"name": "Apple Inc.", "filings": np.random.randint(10, 50)},
                {"name": "Google LLC", "filings": np.random.randint(5, 40)},
                {"name": "Microsoft Corp.", "filings": np.random.randint(8, 35)},
                {"name": "Amazon.com Inc.", "filings": np.random.randint(3, 25)},
                {"name": "Tesla Inc.", "filings": np.random.randint(2, 20)},
            ]
            top_companies.sort(key=lambda x: x["filings"], reverse=True)

            trend_data[keyword] = {
                "total_filings": total_filings,
                "monthly_average": total_filings / months_back,
                "recent_trend_multiplier": recent_trend,
                "growth_rate": growth_rate,
                "top_companies": top_companies[:3],
                # Convert to 0-1 scale
                "signal_strength": min(1.0, max(0.0, (recent_trend - 1.0) * 2)),
            }

        return trend_data


class ResearchPaperAnalyzer:
    """Analyzes academic research publications for emerging trends"""

    def __init__(self):
        self.arxiv_base_url = "http://export.arxiv.org/api/query"
        self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def analyze_research_trends(
        self,
        keywords: list[str],
        months_back: int = 12,
    ) -> dict[str, Any]:
        """Analyze research publication trends"""
        trend_data = {}

        for keyword in keywords:
            try:
                # Query ArXiv for recent papers
                arxiv_data = await self._query_arxiv(keyword, months_back)

                # Query PubMed for biomedical research
                pubmed_data = await self._query_pubmed(keyword, months_back)

                # Combine and analyze
                total_papers = arxiv_data.get("total_papers", 0) + pubmed_data.get(
                    "total_papers",
                    0,
                )
                recent_papers = arxiv_data.get("recent_papers", 0) + pubmed_data.get(
                    "recent_papers",
                    0,
                )

                # Calculate trend metrics
                baseline_rate = total_papers / months_back
                recent_rate = recent_papers / 3  # Last 3 months
                trend_acceleration = (
                    recent_rate / baseline_rate if baseline_rate > 0 else 1.0
                )

                # Extract key research areas
                research_areas = self._extract_research_areas(keyword)

                trend_data[keyword] = {
                    "total_papers": total_papers,
                    "recent_papers": recent_papers,
                    "trend_acceleration": trend_acceleration,
                    "research_areas": research_areas,
                    "arxiv_papers": arxiv_data.get("total_papers", 0),
                    "pubmed_papers": pubmed_data.get("total_papers", 0),
                    "signal_strength": min(
                        1.0,
                        max(0.0, (trend_acceleration - 1.0) * 0.5),
                    ),
                }

            except Exception as e:
                logger.error(f"Error analyzing research trends for {keyword}: {e}")
                trend_data[keyword] = {"error": str(e), "signal_strength": 0.0}

        return trend_data

    async def _query_arxiv(self, keyword: str, months_back: int) -> dict[str, Any]:
        """Query ArXiv for research papers"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)

        # Mock ArXiv query - in production would use real ArXiv API
        total_papers = np.random.poisson(100)  # Mock total papers
        recent_papers = np.random.poisson(30)  # Mock recent papers

        return {
            "total_papers": total_papers,
            "recent_papers": recent_papers,
            "query_keyword": keyword,
        }

    async def _query_pubmed(self, keyword: str, months_back: int) -> dict[str, Any]:
        """Query PubMed for biomedical research papers"""
        # Mock PubMed query
        total_papers = (
            np.random.poisson(80)
            if "bio" in keyword.lower() or "medical" in keyword.lower()
            else np.random.poisson(20)
        )
        recent_papers = (
            np.random.poisson(25)
            if "bio" in keyword.lower() or "medical" in keyword.lower()
            else np.random.poisson(5)
        )

        return {
            "total_papers": total_papers,
            "recent_papers": recent_papers,
            "query_keyword": keyword,
        }

    def _extract_research_areas(self, keyword: str) -> list[str]:
        """Extract related research areas for a keyword"""
        # Mock research area extraction - would use NLP in production
        area_mapping = {
            "quantum": ["quantum computing", "quantum cryptography", "quantum sensors"],
            "ai": [
                "machine learning",
                "neural networks",
                "deep learning",
                "computer vision",
            ],
            "biotech": [
                "gene therapy",
                "CRISPR",
                "personalized medicine",
                "immunotherapy",
            ],
            "energy": [
                "renewable energy",
                "battery technology",
                "fusion power",
                "hydrogen fuel",
            ],
            "space": [
                "satellite technology",
                "space exploration",
                "asteroid mining",
                "space manufacturing",
            ],
        }

        for key, areas in area_mapping.items():
            if key.lower() in keyword.lower():
                return areas[:3]  # Return top 3 related areas

        return ["emerging technology", "innovation research", "applied science"]


class FundingAnalyzer:
    """Analyzes startup funding and investment trends"""

    def __init__(self):
        # Note: In production would integrate with Crunchbase, PitchBook, or
        # similar APIs
        pass

    async def analyze_funding_trends(
        self,
        keywords: list[str],
        months_back: int = 12,
    ) -> dict[str, Any]:
        """Analyze startup funding trends in specific sectors"""
        trend_data = {}

        for keyword in keywords:
            # Mock funding data - would use real APIs in production
            funding_rounds = self._generate_mock_funding_data(keyword, months_back)

            # Calculate metrics
            total_funding = sum(round_data["amount"] for round_data in funding_rounds)
            total_deals = len(funding_rounds)
            average_deal_size = total_funding / total_deals if total_deals > 0 else 0

            # Recent vs historical comparison
            recent_funding = sum(
                round_data["amount"]
                for round_data in funding_rounds
                if round_data["months_ago"] <= 3
            )
            historical_avg = total_funding / months_back * 3  # 3-month equivalent
            funding_acceleration = (
                recent_funding / historical_avg if historical_avg > 0 else 1.0
            )

            # Extract top investors and startups
            top_startups = sorted(
                [(r["startup"], r["amount"]) for r in funding_rounds],
                key=lambda x: x[1],
                reverse=True,
            )[:5]

            # Calculate stage distribution
            stage_distribution = defaultdict(int)
            for round_data in funding_rounds:
                stage_distribution[round_data["stage"]] += 1

            trend_data[keyword] = {
                "total_funding_millions": total_funding,
                "total_deals": total_deals,
                "average_deal_size_millions": average_deal_size,
                "funding_acceleration": funding_acceleration,
                "top_startups": top_startups,
                "stage_distribution": dict(stage_distribution),
                "signal_strength": min(
                    1.0,
                    max(0.0, (funding_acceleration - 1.0) * 0.3),
                ),
            }

        return trend_data

    def _generate_mock_funding_data(
        self,
        keyword: str,
        months_back: int,
    ) -> list[dict[str, Any]]:
        """Generate mock funding data for demonstration"""
        funding_rounds = []

        # Base funding activity based on keyword
        base_activity = {
            "ai": 15,
            "quantum": 5,
            "biotech": 8,
            "fintech": 12,
            "energy": 6,
            "space": 4,
        }

        monthly_deals = base_activity.get(keyword.lower(), 3)

        stages = ["seed", "series_a", "series_b", "series_c", "growth"]
        stage_amounts = [2, 8, 25, 60, 150]  # Million USD

        for month in range(months_back):
            deals_this_month = np.random.poisson(monthly_deals)

            for _ in range(deals_this_month):
                stage_idx = np.random.choice(len(stages), p=[0.4, 0.3, 0.15, 0.1, 0.05])
                amount = np.random.normal(
                    stage_amounts[stage_idx],
                    stage_amounts[stage_idx] * 0.5,
                )
                amount = max(0.5, amount)  # Minimum 0.5M

                funding_rounds.append(
                    {
                        "startup": f"{keyword.title()} Startup {np.random.randint(1000, 9999)}",
                        "stage": stages[stage_idx],
                        "amount": amount,
                        "months_ago": month,
                        "investors": [
                            f"Investor {i}" for i in range(np.random.randint(1, 4))
                        ],
                    },
                )

        return funding_rounds


class SentimentAnalyzer:
    """Analyzes social sentiment and media coverage for trend validation"""

    def __init__(self):
        self.sentiment_pipeline = None
        if HAS_TRANSFORMERS:
            try:
                self.sentiment_pipeline = pipeline("sentiment-analysis")
            except Exception as e:
                logger.warning(f"Could not load sentiment pipeline: {e}")

    async def analyze_trend_sentiment(self, keywords: list[str]) -> dict[str, Any]:
        """Analyze social sentiment around trend keywords"""
        sentiment_data = {}

        for keyword in keywords:
            # Mock social media data - would integrate with Twitter API, Reddit API,
            # etc.
            social_mentions = self._generate_mock_social_data(keyword)
            news_mentions = self._generate_mock_news_data(keyword)

            # Analyze sentiment
            social_sentiment = self._analyze_sentiment_scores(social_mentions)
            news_sentiment = self._analyze_sentiment_scores(news_mentions)

            # Calculate trend metrics
            total_mentions = len(social_mentions) + len(news_mentions)
            positive_ratio = (
                (social_sentiment["positive"] + news_sentiment["positive"])
                / (2 * total_mentions)
                if total_mentions > 0
                else 0
            )
            sentiment_momentum = self._calculate_sentiment_momentum(
                social_mentions + news_mentions,
            )

            sentiment_data[keyword] = {
                "total_mentions": total_mentions,
                "social_mentions": len(social_mentions),
                "news_mentions": len(news_mentions),
                "positive_ratio": positive_ratio,
                "sentiment_momentum": sentiment_momentum,
                "social_sentiment": social_sentiment,
                "news_sentiment": news_sentiment,
                # Convert to signal strength
                "signal_strength": min(1.0, max(0.0, positive_ratio * 2 - 0.5)),
            }

        return sentiment_data

    def _generate_mock_social_data(self, keyword: str) -> list[dict[str, Any]]:
        """Generate mock social media mentions"""
        mentions = []
        base_mentions = np.random.randint(50, 500)

        for i in range(base_mentions):
            # Mock sentiment score
            sentiment_score = np.random.normal(0.1, 0.4)  # Slightly positive bias
            sentiment_score = max(-1.0, min(1.0, sentiment_score))

            mentions.append(
                {
                    "text": f"Mock social post about {keyword} #{i}",
                    "sentiment_score": sentiment_score,
                    "platform": np.random.choice(
                        ["twitter", "reddit", "linkedin", "youtube"],
                    ),
                    "engagement": np.random.randint(1, 1000),
                    "timestamp": datetime.now()
                    - timedelta(days=np.random.randint(0, 90)),
                },
            )

        return mentions

    def _generate_mock_news_data(self, keyword: str) -> list[dict[str, Any]]:
        """Generate mock news mentions"""
        mentions = []
        base_mentions = np.random.randint(20, 100)

        for i in range(base_mentions):
            sentiment_score = np.random.normal(
                0.05,
                0.3,
            )  # Neutral to slightly positive
            sentiment_score = max(-1.0, min(1.0, sentiment_score))

            mentions.append(
                {
                    "title": f"News article about {keyword} trends #{i}",
                    "sentiment_score": sentiment_score,
                    "source": np.random.choice(
                        ["TechCrunch", "Reuters", "Bloomberg", "The Verge", "Forbes"],
                    ),
                    "timestamp": datetime.now()
                    - timedelta(days=np.random.randint(0, 30)),
                },
            )

        return mentions

    def _analyze_sentiment_scores(
        self,
        mentions: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Analyze sentiment distribution"""
        positive = sum(1 for m in mentions if m["sentiment_score"] > 0.1)
        negative = sum(1 for m in mentions if m["sentiment_score"] < -0.1)
        neutral = len(mentions) - positive - negative

        return {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "total": len(mentions),
        }

    def _calculate_sentiment_momentum(self, mentions: list[dict[str, Any]]) -> float:
        """Calculate sentiment momentum over time"""
        if len(mentions) < 10:
            return 0.0

        # Sort by timestamp
        sorted_mentions = sorted(mentions, key=lambda x: x["timestamp"])

        # Calculate recent vs historical sentiment
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_mentions = [m for m in sorted_mentions if m["timestamp"] > cutoff_date]
        historical_mentions = [
            m for m in sorted_mentions if m["timestamp"] <= cutoff_date
        ]

        if not recent_mentions or not historical_mentions:
            return 0.0

        recent_avg = np.mean([m["sentiment_score"] for m in recent_mentions])
        historical_avg = np.mean([m["sentiment_score"] for m in historical_mentions])

        # Return momentum (-1 to 1)
        momentum = (recent_avg - historical_avg) / 2  # Scale to -1 to 1
        return max(-1.0, min(1.0, momentum))


class TrendDetectionEngine:
    """Enhanced trend detection engine with Google Trends integration
    Orchestrates all analysis components including search behavior data
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

        # Initialize analyzers
        self.patent_analyzer = PatentAnalyzer()
        self.research_analyzer = ResearchPaperAnalyzer()
        self.funding_analyzer = FundingAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()

        # Google Trends integration
        self.google_trends_service = None
        if HAS_GOOGLE_TRENDS and config.get("enable_google_trends", True):
            try:
                trends_config = config.get("google_trends", {})
                self.google_trends_service = GoogleTrendsIntegrationService(
                    trends_config,
                )
                logger.info("Google Trends integration enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Google Trends service: {e}")

        # AI integration
        self.openai_client = None
        if HAS_OPENAI and config.get("openai_api_key"):
            openai.api_key = config["openai_api_key"]
            self.openai_client = openai

        # Trend storage
        self.active_trends: list[EmergingTrend] = []
        self.trend_history: list[EmergingTrend] = []

        # Monitoring keywords by category
        self.keyword_categories = {
            TrendCategory.AI_ML: [
                "artificial intelligence",
                "machine learning",
                "neural networks",
                "deep learning",
                "computer vision",
                "natural language processing",
                "ai agents",
                "generative ai",
                "large language models",
                "autonomous systems",
            ],
            TrendCategory.TECHNOLOGY: [
                "quantum computing",
                "quantum cryptography",
                "quantum sensors",
                "blockchain",
                "augmented reality",
                "virtual reality",
                "edge computing",
                "5g technology",
                "internet of things",
                "cybersecurity",
            ],
            TrendCategory.HEALTHCARE: [
                "gene therapy",
                "crispr",
                "personalized medicine",
                "immunotherapy",
                "telemedicine",
                "digital health",
                "biomarkers",
                "regenerative medicine",
                "precision medicine",
                "ai diagnostics",
            ],
            TrendCategory.ENERGY: [
                "renewable energy",
                "battery technology",
                "energy storage",
                "fusion power",
                "hydrogen fuel",
                "solar technology",
                "wind energy",
                "carbon capture",
                "smart grid",
                "electric vehicles",
            ],
            TrendCategory.FINANCE: [
                "fintech",
                "cryptocurrency",
                "defi",
                "digital banking",
                "robo advisors",
                "payment technology",
                "insurtech",
                "regtech",
                "blockchain finance",
                "central bank digital currency",
            ],
        }

        logger.info(
            f"TrendDetectionEngine initialized with {len(self.keyword_categories)} categories",
        )

    async def detect_emerging_trends(self) -> list[EmergingTrend]:
        """Enhanced trend detection method with Google Trends integration"""
        logger.info(
            "🔍 Starting comprehensive trend detection analysis with Google Trends...",
        )

        all_trends = []

        # Start with Google Trends analysis for rapid early detection
        if self.google_trends_service:
            logger.info("🌐 Analyzing Google Trends for early signals...")
            try:
                google_opportunities = (
                    await self.google_trends_service.analyze_wealth_keywords(
                        region=GeographicRegion.US,
                    )
                )

                # Convert Google Trends opportunities to trend signals
                for opp in google_opportunities[:10]:  # Top 10 opportunities
                    trend_signal = await self._convert_google_trends_to_signal(opp)
                    if trend_signal:
                        all_trends.append(trend_signal)

                logger.info(
                    f"📈 Found {len(google_opportunities)} Google Trends opportunities",
                )
            except Exception as e:
                logger.error(f"Error in Google Trends analysis: {e}")

        # Continue with traditional multi-source analysis
        for category, keywords in self.keyword_categories.items():
            logger.info(f"Analyzing {category.value} trends...")

            try:
                # Analyze each data source
                patent_data = await self.patent_analyzer.analyze_patent_trends(keywords)
                research_data = await self.research_analyzer.analyze_research_trends(
                    keywords,
                )
                funding_data = await self.funding_analyzer.analyze_funding_trends(
                    keywords,
                )
                sentiment_data = await self.sentiment_analyzer.analyze_trend_sentiment(
                    keywords,
                )

                # Get Google Trends data for this category if available
                google_trends_data = {}
                if self.google_trends_service:
                    try:
                        google_trends_data = await self._get_google_trends_for_category(
                            keywords,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error getting Google Trends for {category.value}: {e}",
                        )

                # Synthesize trends for this category (enhanced with Google Trends)
                category_trends = await self._synthesize_category_trends(
                    category,
                    keywords,
                    patent_data,
                    research_data,
                    funding_data,
                    sentiment_data,
                    google_trends_data,
                )

                all_trends.extend(category_trends)

            except Exception as e:
                logger.error(f"Error analyzing {category.value} trends: {e}")
                continue

        # Filter and rank all detected trends
        high_quality_trends = self._filter_and_rank_trends(all_trends)

        # Update active trends
        self._update_active_trends(high_quality_trends)

        logger.info(
            f"✅ Enhanced trend detection complete: {len(high_quality_trends)} high-quality trends detected",
        )

        return high_quality_trends

    async def _synthesize_category_trends(
        self,
        category: TrendCategory,
        keywords: list[str],
        patent_data: dict[str, Any],
        research_data: dict[str, Any],
        funding_data: dict[str, Any],
        sentiment_data: dict[str, Any],
        google_trends_data: dict[str, Any] = None,
    ) -> list[EmergingTrend]:
        """Synthesize trends for a specific category"""
        trends = []

        for keyword in keywords:
            try:
                # Collect signals from all sources
                signals = []

                # Patent signals
                if keyword in patent_data:
                    patent_info = patent_data[keyword]
                    if patent_info.get("signal_strength", 0) > 0.3:
                        signals.append(
                            TrendSignal(
                                source="patents",
                                signal_type="filing_acceleration",
                                strength=patent_info["signal_strength"],
                                confidence=0.8,
                                data_points=patent_info.get("total_filings", 0),
                                time_period="last_12_months",
                                raw_data=patent_info,
                            ),
                        )

                # Research signals
                if keyword in research_data:
                    research_info = research_data[keyword]
                    if research_info.get("signal_strength", 0) > 0.3:
                        signals.append(
                            TrendSignal(
                                source="research_papers",
                                signal_type="publication_surge",
                                strength=research_info["signal_strength"],
                                confidence=0.7,
                                data_points=research_info.get("total_papers", 0),
                                time_period="last_12_months",
                                raw_data=research_info,
                            ),
                        )

                # Funding signals
                if keyword in funding_data:
                    funding_info = funding_data[keyword]
                    if funding_info.get("signal_strength", 0) > 0.3:
                        signals.append(
                            TrendSignal(
                                source="startup_funding",
                                signal_type="investment_acceleration",
                                strength=funding_info["signal_strength"],
                                confidence=0.9,
                                data_points=funding_info.get("total_deals", 0),
                                time_period="last_12_months",
                                raw_data=funding_info,
                            ),
                        )

                # Sentiment signals
                if keyword in sentiment_data:
                    sentiment_info = sentiment_data[keyword]
                    if sentiment_info.get("signal_strength", 0) > 0.3:
                        signals.append(
                            TrendSignal(
                                source="social_sentiment",
                                signal_type="positive_sentiment_surge",
                                strength=sentiment_info["signal_strength"],
                                confidence=0.6,
                                data_points=sentiment_info.get("total_mentions", 0),
                                time_period="last_90_days",
                                raw_data=sentiment_info,
                            ),
                        )

                # Only create trend if we have at least 2 strong signals
                if len([s for s in signals if s.strength > 0.4]) >= 2:
                    trend = await self._create_trend_from_signals(
                        keyword,
                        category,
                        signals,
                    )
                    if trend:
                        trends.append(trend)

            except Exception as e:
                logger.error(f"Error synthesizing trend for {keyword}: {e}")
                continue

        return trends

    async def _create_trend_from_signals(
        self,
        keyword: str,
        category: TrendCategory,
        signals: list[TrendSignal],
    ) -> EmergingTrend | None:
        """Create an EmergingTrend object from collected signals"""
        if not signals:
            return None

        # Calculate overall score (weighted average of signal strengths)
        weights = {
            "patents": 0.3,
            "research_papers": 0.25,
            "startup_funding": 0.35,
            "social_sentiment": 0.1,
        }
        weighted_score = 0.0
        total_weight = 0.0

        for signal in signals:
            weight = weights.get(signal.source, 0.1)
            weighted_score += signal.strength * weight
            total_weight += weight

        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # Calculate confidence (average of signal confidences)
        confidence = np.mean([s.confidence for s in signals])

        # Calculate momentum (trend acceleration)
        momentum = self._calculate_trend_momentum(signals)

        # Determine trend stage
        stage = self._determine_trend_stage(signals)

        # Generate investment opportunities
        investment_opportunities = await self._generate_investment_opportunities(
            keyword,
            category,
            signals,
        )

        # Estimate market potential
        market_size = self._estimate_market_size(keyword, category, signals)
        growth_rate = self._estimate_growth_rate(signals)

        # Generate AI-powered description
        description = await self._generate_trend_description(keyword, category, signals)

        # Estimate mainstream adoption timeline
        mainstream_date = self._estimate_mainstream_date(stage, momentum)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(keyword, category, signals)

        return EmergingTrend(
            name=keyword.title(),
            description=description,
            category=category,
            stage=stage,
            overall_score=overall_score,
            confidence=confidence,
            momentum=momentum,
            estimated_mainstream_date=mainstream_date,
            current_adoption_percentage=self._estimate_current_adoption(stage),
            signals=signals,
            investment_opportunities=investment_opportunities,
            estimated_market_size=market_size,
            growth_rate_estimate=growth_rate,
            risk_factors=risk_factors,
            competitive_landscape=self._analyze_competitive_landscape(keyword, signals),
        )

    def _calculate_trend_momentum(self, signals: list[TrendSignal]) -> float:
        """Calculate trend momentum from signals"""
        momentum_indicators = []

        for signal in signals:
            if signal.source == "startup_funding":
                funding_acceleration = signal.raw_data.get("funding_acceleration", 1.0)
                momentum_indicators.append((funding_acceleration - 1.0) * 0.5)
            elif signal.source == "research_papers":
                research_acceleration = signal.raw_data.get("trend_acceleration", 1.0)
                momentum_indicators.append((research_acceleration - 1.0) * 0.3)
            elif signal.source == "social_sentiment":
                sentiment_momentum = signal.raw_data.get("sentiment_momentum", 0.0)
                momentum_indicators.append(sentiment_momentum)

        if momentum_indicators:
            return max(-1.0, min(1.0, np.mean(momentum_indicators)))
        return 0.0

    def _determine_trend_stage(self, signals: list[TrendSignal]) -> TrendStage:
        """Determine what stage the trend is in"""
        # Simple heuristic based on signal sources and strength
        has_strong_research = any(
            s.source == "research_papers" and s.strength > 0.6 for s in signals
        )
        has_funding = any(s.source == "startup_funding" for s in signals)
        has_patents = any(s.source == "patents" and s.strength > 0.5 for s in signals)
        has_social_buzz = any(
            s.source == "social_sentiment" and s.strength > 0.7 for s in signals
        )

        if has_social_buzz and has_funding:
            return TrendStage.GROWTH
        if has_funding and (has_patents or has_strong_research):
            return TrendStage.EARLY_ADOPTION
        if has_strong_research or has_patents:
            return TrendStage.EMERGENCE
        return TrendStage.EMERGENCE

    async def _generate_investment_opportunities(
        self,
        keyword: str,
        category: TrendCategory,
        signals: list[TrendSignal],
    ) -> list[dict[str, Any]]:
        """Generate investment opportunities based on trend analysis"""
        opportunities = []

        # Stock opportunities based on category
        stock_mappings = {
            TrendCategory.AI_ML: [
                {
                    "symbol": "NVDA",
                    "name": "NVIDIA Corp",
                    "relevance": 0.9,
                    "type": "direct_play",
                },
                {
                    "symbol": "GOOGL",
                    "name": "Alphabet Inc",
                    "relevance": 0.8,
                    "type": "diversified_tech",
                },
                {
                    "symbol": "MSFT",
                    "name": "Microsoft Corp",
                    "relevance": 0.8,
                    "type": "cloud_ai",
                },
                {
                    "symbol": "TSLA",
                    "name": "Tesla Inc",
                    "relevance": 0.7,
                    "type": "ai_applications",
                },
            ],
            TrendCategory.HEALTHCARE: [
                {
                    "symbol": "GERN",
                    "name": "Geron Corp",
                    "relevance": 0.8,
                    "type": "biotech",
                },
                {
                    "symbol": "ARWR",
                    "name": "Arrowhead Pharmaceuticals",
                    "relevance": 0.7,
                    "type": "gene_therapy",
                },
                {
                    "symbol": "ILMN",
                    "name": "Illumina Inc",
                    "relevance": 0.8,
                    "type": "genomics",
                },
                {
                    "symbol": "VEEV",
                    "name": "Veeva Systems",
                    "relevance": 0.6,
                    "type": "digital_health",
                },
            ],
            TrendCategory.ENERGY: [
                {
                    "symbol": "TSLA",
                    "name": "Tesla Inc",
                    "relevance": 0.9,
                    "type": "ev_energy",
                },
                {
                    "symbol": "ENPH",
                    "name": "Enphase Energy",
                    "relevance": 0.8,
                    "type": "solar",
                },
                {
                    "symbol": "BE",
                    "name": "Bloom Energy",
                    "relevance": 0.7,
                    "type": "fuel_cells",
                },
                {
                    "symbol": "PLUG",
                    "name": "Plug Power",
                    "relevance": 0.6,
                    "type": "hydrogen",
                },
            ],
        }

        # Get relevant stocks for category
        category_stocks = stock_mappings.get(category, [])

        for stock in category_stocks:
            if stock["relevance"] > 0.6:  # Only high-relevance opportunities
                opportunities.append(
                    {
                        "vehicle": InvestmentVehicle.STOCK.value,
                        "symbol": stock["symbol"],
                        "name": stock["name"],
                        "relevance_score": stock["relevance"],
                        "investment_type": stock["type"],
                        "estimated_impact": (
                            "high" if stock["relevance"] > 0.8 else "medium"
                        ),
                        "time_horizon": "6-18 months",
                        "risk_level": "medium",
                    },
                )

        # ETF opportunities
        etf_mappings = {
            TrendCategory.AI_ML: [
                {
                    "symbol": "ARKQ",
                    "name": "ARK Autonomous Technology & Robotics ETF",
                    "relevance": 0.8,
                },
                {
                    "symbol": "BOTZ",
                    "name": "Global X Robotics & Artificial Intelligence ETF",
                    "relevance": 0.9,
                },
            ],
            TrendCategory.HEALTHCARE: [
                {
                    "symbol": "ARKG",
                    "name": "ARK Genomic Revolution ETF",
                    "relevance": 0.9,
                },
                {"symbol": "XBI", "name": "SPDR S&P Biotech ETF", "relevance": 0.7},
            ],
        }

        category_etfs = etf_mappings.get(category, [])
        for etf in category_etfs:
            opportunities.append(
                {
                    "vehicle": InvestmentVehicle.ETF.value,
                    "symbol": etf["symbol"],
                    "name": etf["name"],
                    "relevance_score": etf["relevance"],
                    "investment_type": "diversified_exposure",
                    "estimated_impact": "medium",
                    "time_horizon": "12-24 months",
                    "risk_level": "medium",
                },
            )

        # Crypto opportunities for relevant categories
        if category in [TrendCategory.FINANCE, TrendCategory.AI_ML]:
            opportunities.extend(
                [
                    {
                        "vehicle": InvestmentVehicle.CRYPTO.value,
                        "symbol": "ETH",
                        "name": "Ethereum",
                        "relevance_score": 0.7,
                        "investment_type": "platform_token",
                        "estimated_impact": "high",
                        "time_horizon": "3-12 months",
                        "risk_level": "high",
                    },
                ],
            )

        return opportunities[:5]  # Return top 5 opportunities

    def _estimate_market_size(
        self,
        keyword: str,
        category: TrendCategory,
        signals: list[TrendSignal],
    ) -> float | None:
        """Estimate total addressable market size in billions USD"""
        # Base market sizes by category (rough estimates)
        base_markets = {
            TrendCategory.AI_ML: 500,  # AI market expected to reach $500B+
            TrendCategory.HEALTHCARE: 200,
            TrendCategory.ENERGY: 300,
            TrendCategory.FINANCE: 150,
            TrendCategory.TECHNOLOGY: 400,
        }

        base_size = base_markets.get(category, 50)

        # Adjust based on signal strength (stronger signals = larger addressable market)
        avg_signal_strength = np.mean([s.strength for s in signals])
        size_multiplier = 0.5 + avg_signal_strength  # Range: 0.5 to 1.5

        return base_size * size_multiplier

    def _estimate_growth_rate(self, signals: list[TrendSignal]) -> float | None:
        """Estimate annual growth rate percentage"""
        growth_rates = []

        for signal in signals:
            if signal.source == "startup_funding":
                funding_growth = signal.raw_data.get("funding_acceleration", 1.0)
                growth_rates.append(
                    (funding_growth - 1.0) * 100,
                )  # Convert to percentage
            elif signal.source == "research_papers":
                research_growth = signal.raw_data.get("trend_acceleration", 1.0)
                growth_rates.append(
                    (research_growth - 1.0) * 50,
                )  # Scale research growth

        if growth_rates:
            estimated_growth = max(
                10,
                min(200, np.mean(growth_rates)),
            )  # Cap between 10% and 200%
            return estimated_growth
        return 25.0  # Default growth rate

    async def _generate_trend_description(
        self,
        keyword: str,
        category: TrendCategory,
        signals: list[TrendSignal],
    ) -> str:
        """Generate AI-powered trend description"""
        # If OpenAI is available, use it for better descriptions
        if self.openai_client:
            try:
                signal_summary = self._summarize_signals(signals)

                prompt = f"""
                Generate a concise, professional description of the emerging trend "{
                    keyword
                }" in the {category.value} sector.

                Key signals detected:
                {signal_summary}

                The description should be 2-3 sentences explaining:
                1. What the trend is
                2. Why it's emerging now
                3. Its potential impact

                Keep it factual and investor-focused.
                """

                response = await self.openai_client.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.7,
                )

                return response.choices[0].message.content.strip()

            except Exception as e:
                logger.warning(f"OpenAI description generation failed: {e}")

        # Fallback to template-based description
        return self._generate_template_description(keyword, category, signals)

    def _generate_template_description(
        self,
        keyword: str,
        category: TrendCategory,
        signals: list[TrendSignal],
    ) -> str:
        """Generate description using templates"""
        signal_types = [s.signal_type for s in signals]

        if (
            "investment_acceleration" in signal_types
            and "publication_surge" in signal_types
        ):
            return f"{keyword.title()} is experiencing rapid growth with increased research activity and significant investment acceleration in the {category.value} sector, positioning it as a key emerging technology with substantial commercial potential."
        if "filing_acceleration" in signal_types:
            return f"{keyword.title()} shows strong innovation momentum with accelerating patent activity in {category.value}, indicating increasing commercial interest and potential breakthrough applications."
        return f"{keyword.title()} is an emerging trend in {
            category.value
        } showing multiple positive indicators including research growth and market interest."

    def _summarize_signals(self, signals: list[TrendSignal]) -> str:
        """Summarize signals for AI prompt"""
        summary_parts = []

        for signal in signals:
            summary_parts.append(
                f"- {signal.source}: {signal.signal_type} (strength: {
                    signal.strength:.2f}, {signal.data_points} data points)",
            )

        return "\n".join(summary_parts)

    def _estimate_mainstream_date(
        self,
        stage: TrendStage,
        momentum: float,
    ) -> datetime | None:
        """Estimate when trend will reach mainstream adoption"""
        base_months = {
            TrendStage.EMERGENCE: 36,  # 3 years
            TrendStage.EARLY_ADOPTION: 24,  # 2 years
            TrendStage.GROWTH: 12,  # 1 year
            TrendStage.MAINSTREAM: 0,  # Already there
        }

        months_to_mainstream = base_months.get(stage, 36)

        # Adjust based on momentum
        if momentum > 0.5:
            months_to_mainstream *= 0.8  # Faster with high momentum
        elif momentum < -0.2:
            months_to_mainstream *= 1.3  # Slower with negative momentum

        return datetime.now() + timedelta(days=int(months_to_mainstream * 30))

    def _estimate_current_adoption(self, stage: TrendStage) -> float:
        """Estimate current adoption percentage"""
        adoption_percentages = {
            TrendStage.EMERGENCE: 0.5,
            TrendStage.EARLY_ADOPTION: 2.5,
            TrendStage.GROWTH: 16.0,
            TrendStage.MAINSTREAM: 50.0,
            TrendStage.MATURITY: 84.0,
        }

        return adoption_percentages.get(stage, 1.0)

    def _identify_risk_factors(
        self,
        keyword: str,
        category: TrendCategory,
        signals: list[TrendSignal],
    ) -> list[str]:
        """Identify potential risk factors for the trend"""
        risk_factors = []

        # Category-specific risks
        category_risks = {
            TrendCategory.AI_ML: [
                "Regulatory uncertainty around AI governance",
                "Technical limitations and AI safety concerns",
                "High computational costs and energy requirements",
            ],
            TrendCategory.HEALTHCARE: [
                "Regulatory approval delays (FDA, EMA)",
                "High development costs and R&D risks",
                "Ethical and safety considerations",
            ],
            TrendCategory.ENERGY: [
                "Policy and regulatory changes",
                "Infrastructure investment requirements",
                "Competition from established energy sources",
            ],
            TrendCategory.FINANCE: [
                "Regulatory crackdowns and compliance costs",
                "Cybersecurity and fraud risks",
                "Market volatility and adoption barriers",
            ],
        }

        risk_factors.extend(
            category_risks.get(category, ["Market adoption uncertainty"]),
        )

        # Signal-based risks
        funding_signals = [s for s in signals if s.source == "startup_funding"]
        if funding_signals and funding_signals[0].strength > 0.8:
            risk_factors.append("Potential investment bubble and valuation concerns")

        # Add general risks
        risk_factors.extend(
            ["Competition from established players", "Technology maturation risks"],
        )

        return risk_factors[:5]  # Return top 5 risks

    def _analyze_competitive_landscape(
        self,
        keyword: str,
        signals: list[TrendSignal],
    ) -> dict[str, Any]:
        """Analyze competitive landscape"""
        # Extract company information from signals
        companies = []

        for signal in signals:
            if signal.source == "patents":
                patent_companies = signal.raw_data.get("top_companies", [])
                companies.extend([c["name"] for c in patent_companies])
            elif signal.source == "startup_funding":
                startup_companies = signal.raw_data.get("top_startups", [])
                companies.extend(
                    [c[0] for c in startup_companies],
                )  # Extract company names

        # Count company mentions
        company_counts = {}
        for company in companies:
            company_counts[company] = company_counts.get(company, 0) + 1

        # Return competitive analysis
        return {
            "key_players": list(company_counts.keys())[:5],
            "market_concentration": (
                "fragmented" if len(company_counts) > 10 else "concentrated"
            ),
            "innovation_leaders": sorted(
                company_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3],
        }

    def _filter_and_rank_trends(
        self,
        trends: list[EmergingTrend],
    ) -> list[EmergingTrend]:
        """Filter and rank trends by investment potential"""
        # Filter trends with minimum quality threshold
        filtered_trends = [
            trend
            for trend in trends
            if trend.overall_score >= 0.5 and trend.confidence >= 0.6
        ]

        # Calculate investment score for ranking
        def investment_score(trend: EmergingTrend) -> float:
            base_score = trend.overall_score * trend.confidence

            # Bonus for early-stage trends (more upside potential)
            stage_multiplier = {
                TrendStage.EMERGENCE: 1.2,
                TrendStage.EARLY_ADOPTION: 1.1,
                TrendStage.GROWTH: 1.0,
                TrendStage.MAINSTREAM: 0.8,
            }.get(trend.stage, 1.0)

            # Bonus for high momentum
            momentum_bonus = max(0, trend.momentum) * 0.2

            # Bonus for multiple investment opportunities
            opportunity_bonus = min(0.2, len(trend.investment_opportunities) * 0.05)

            return base_score * stage_multiplier + momentum_bonus + opportunity_bonus

        # Sort by investment score
        filtered_trends.sort(key=investment_score, reverse=True)

        return filtered_trends[:15]  # Return top 15 trends

    def _update_active_trends(self, new_trends: list[EmergingTrend]):
        """Update active trends list"""
        # Remove old trends or update existing ones
        existing_trend_names = {trend.name.lower() for trend in self.active_trends}

        for new_trend in new_trends:
            # Update existing trend or add new one
            existing_trend = None
            for i, active_trend in enumerate(self.active_trends):
                if active_trend.name.lower() == new_trend.name.lower():
                    existing_trend = i
                    break

            if existing_trend is not None:
                # Update existing trend
                new_trend.detected_at = self.active_trends[existing_trend].detected_at
                self.active_trends[existing_trend] = new_trend
            else:
                # Add new trend
                self.active_trends.append(new_trend)

        # Remove trends that are no longer detected (older than 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        self.active_trends = [
            trend for trend in self.active_trends if trend.last_updated > cutoff_date
        ]

        # Sort by overall score
        self.active_trends.sort(key=lambda x: x.overall_score, reverse=True)

    def get_active_trends(self) -> list[EmergingTrend]:
        """Get all active trends"""
        return self.active_trends.copy()

    def get_top_trends(self, limit: int = 10) -> list[EmergingTrend]:
        """Get top trends by overall score"""
        return self.active_trends[:limit]

    def get_trends_by_category(self, category: TrendCategory) -> list[EmergingTrend]:
        """Get trends filtered by category"""
        return [trend for trend in self.active_trends if trend.category == category]

    def get_early_stage_trends(self) -> list[EmergingTrend]:
        """Get trends in emergence or early adoption stage (highest upside potential)"""
        return [
            trend
            for trend in self.active_trends
            if trend.stage in [TrendStage.EMERGENCE, TrendStage.EARLY_ADOPTION]
        ]


# Example usage


async def main_trend_detection_demo():
    """Demo of the trend detection engine"""
    config = {
        "openai_api_key": None,  # Add your OpenAI API key for better descriptions
    }

    # Initialize trend detection engine
    engine = TrendDetectionEngine(config)

    # Detect emerging trends
    trends = await engine.detect_emerging_trends()

    # Display results
    print("\n🔍 EMERGING TREND ANALYSIS")
    print("=" * 60)
    print(f"Detected {len(trends)} high-quality emerging trends:\n")

    for i, trend in enumerate(trends[:5], 1):  # Show top 5
        print(f"{i}. {trend.name} ({trend.category.value.upper()})")
        print(f"   Stage: {trend.stage.value}")
        print(f"   Score: {trend.overall_score:.2f}")
        print(f"   Confidence: {trend.confidence:.1%}")
        print(f"   Momentum: {trend.momentum:+.2f}")
        if trend.estimated_mainstream_date:
            print(
                f"   Mainstream ETA: {trend.estimated_mainstream_date.strftime('%Y-%m')}",
            )
        print(f"   Market Size: ${trend.estimated_market_size:.0f}B (estimated)")
        print(f"   Growth Rate: {trend.growth_rate_estimate:.0f}% annually")
        print(f"   Investment Opportunities: {len(trend.investment_opportunities)}")
        print(f"   Description: {trend.description}")
        print()

    # Show early-stage trends with highest upside
    early_trends = engine.get_early_stage_trends()
    print("🚀 EARLY-STAGE TRENDS (Highest Upside Potential):")
    print("-" * 50)
    for trend in early_trends[:3]:
        print(
            f"• {trend.name}: {trend.stage.value} stage, {
                trend.overall_score:.2f} score",
        )

        # Show top investment opportunity
        if trend.investment_opportunities:
            top_opportunity = trend.investment_opportunities[0]
            print(
                f"  → Top Play: {top_opportunity['symbol']} ({
                    top_opportunity['name']
                })",
            )
        print()

    async def _convert_google_trends_to_signal(
        self,
        google_opportunity,
    ) -> EmergingTrend | None:
        """Convert Google Trends opportunity to EmergingTrend signal"""
        try:
            # Determine category based on keyword
            category = self._classify_keyword_category(google_opportunity.keyword)

            # Map Google Trends strength to trend stage
            trend_data = google_opportunity.trend_data
            if trend_data.trend_strength.value >= 4:  # VERY_STRONG or EXPLOSIVE
                stage = TrendStage.EARLY_ADOPTION
            elif trend_data.trend_strength.value >= 3:  # STRONG
                stage = TrendStage.EMERGENCE
            else:
                return None  # Skip weak trends

            # Create investment opportunities from Google Trends symbols
            investment_opportunities = []
            for symbol in google_opportunity.related_symbols:
                investment_opportunities.append(
                    {
                        "symbol": symbol,
                        "name": f"{symbol} - {google_opportunity.keyword} exposure",
                        "correlation": 0.8,  # High correlation from Google Trends mapping
                        "risk_score": (
                            0.6 if google_opportunity.risk_level == "medium" else 0.4
                        ),
                        "upside_potential": google_opportunity.potential_return / 100,
                    },
                )

            # Calculate overall score based on Google Trends metrics
            overall_score = (
                trend_data.trend_strength.value * 0.3
                + (trend_data.momentum_score + 1) * 2.5  # Scale momentum to 0-5
                + google_opportunity.confidence_score * 5
            ) / 3

            # Create EmergingTrend from Google Trends data
            trend = EmergingTrend(
                id=f"gt_{google_opportunity.opportunity_id}",
                name=google_opportunity.keyword.title(),
                category=category,
                stage=stage,
                description=google_opportunity.investment_thesis,
                confidence=google_opportunity.confidence_score,
                overall_score=min(overall_score, 5.0),
                momentum=trend_data.momentum_score,
                investment_opportunities=investment_opportunities,
                data_sources={"google_trends": trend_data.to_dict()},
                estimated_market_size=trend_data.peak_interest * 100,  # Rough estimate
                growth_rate_estimate=max(trend_data.momentum_score * 50, 10),
                estimated_mainstream_date=datetime.now()
                + timedelta(days=180 if stage == TrendStage.EMERGENCE else 90),
                last_updated=datetime.now(),
            )

            return trend

        except Exception as e:
            logger.error(f"Error converting Google Trends opportunity to signal: {e}")
            return None

    async def _get_google_trends_for_category(
        self,
        keywords: list[str],
    ) -> dict[str, Any]:
        """Get Google Trends data for specific category keywords"""
        try:
            google_data = {}

            # Analyze a subset of keywords to avoid rate limits
            for keyword in keywords[:3]:  # Limit to 3 keywords per category
                try:
                    trend_data = (
                        await self.google_trends_service.analyzer.analyze_trend(keyword)
                    )
                    if trend_data:
                        google_data[keyword] = trend_data.to_dict()
                        await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error getting Google Trends for '{keyword}': {e}")
                    continue

            return google_data

        except Exception as e:
            logger.error(f"Error getting Google Trends for category: {e}")
            return {}

    def _classify_keyword_category(self, keyword: str) -> TrendCategory:
        """Classify a keyword into trend category"""
        keyword_lower = keyword.lower()

        # Check against each category's keywords
        for category, keywords in self.keyword_categories.items():
            for cat_keyword in keywords:
                if cat_keyword in keyword_lower or keyword_lower in cat_keyword:
                    return category

        # Fallback classification based on common terms
        if any(
            term in keyword_lower
            for term in ["ai", "artificial", "machine", "neural", "deep"]
        ):
            return TrendCategory.AI_ML
        if any(
            term in keyword_lower
            for term in ["quantum", "blockchain", "crypto", "5g", "iot"]
        ):
            return TrendCategory.TECHNOLOGY
        if any(
            term in keyword_lower
            for term in ["gene", "bio", "health", "medical", "therapy"]
        ):
            return TrendCategory.HEALTHCARE
        if any(
            term in keyword_lower
            for term in ["energy", "battery", "solar", "electric", "renewable"]
        ):
            return TrendCategory.ENERGY
        if any(
            term in keyword_lower
            for term in ["fintech", "payment", "crypto", "digital", "finance"]
        ):
            return TrendCategory.FINANCE
        return TrendCategory.TECHNOLOGY  # Default fallback

    def get_google_trends_dashboard(self) -> dict[str, Any]:
        """Get Google Trends integration dashboard data"""
        try:
            if not self.google_trends_service:
                return {"error": "Google Trends not available"}

            # This would be implemented as an async method in production
            return {
                "integration_status": "active",
                "last_analysis": datetime.now().isoformat(),
                "trends_analyzed": len(self.active_trends),
                "google_trends_enabled": True,
            }

        except Exception as e:
            logger.error(f"Error getting Google Trends dashboard: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    asyncio.run(main_trend_detection_demo())
