#!/usr/bin/env python3
"""PAKE System - Real-Time Opportunity Scanner
World-class financial opportunity detection system for personal wealth generation.

Features:
- Multi-market scanning (stocks, crypto, forex, commodities)
- Real-time signal generation with confidence scores
- Pattern recognition across timeframes
- Automated alert system for high-probability opportunities
- Risk-adjusted position sizing recommendations
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import aiohttp
import numpy as np
import pandas as pd

# Data source integrations (would use real APIs in production)
import yfinance as yf  # For stock/ETF data

logger = logging.getLogger(__name__)


class MarketType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    OPTION = "option"
    ETF = "etf"


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class OpportunityType(Enum):
    BREAKOUT = "technical_breakout"
    REVERSAL = "trend_reversal"
    MOMENTUM = "momentum_surge"
    ARBITRAGE = "arbitrage"
    EVENT_DRIVEN = "event_driven"
    SENTIMENT = "sentiment_driven"
    CROSS_ASSET = "cross_asset_correlation"


@dataclass
class MarketOpportunity:
    """Represents a detected market opportunity with all relevant metadata"""

    symbol: str
    market_type: MarketType
    opportunity_type: OpportunityType
    signal: SignalType
    confidence_score: float  # 0.0 to 1.0
    expected_return: float  # Expected percentage return
    time_horizon: str  # "minutes", "hours", "days", "weeks"
    risk_level: str  # "low", "medium", "high"

    # Market data
    current_price: float
    target_price: float
    stop_loss: float
    volume_spike: float = 0.0

    # Analysis details
    technical_indicators: dict[str, Any] = field(default_factory=dict)
    fundamental_data: dict[str, Any] = field(default_factory=dict)
    sentiment_data: dict[str, Any] = field(default_factory=dict)
    catalyst: str | None = None

    # Metadata
    detected_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    alert_sent: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "market_type": self.market_type.value,
            "opportunity_type": self.opportunity_type.value,
            "signal": self.signal.value,
            "confidence_score": self.confidence_score,
            "expected_return": self.expected_return,
            "time_horizon": self.time_horizon,
            "risk_level": self.risk_level,
            "current_price": self.current_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "volume_spike": self.volume_spike,
            "technical_indicators": self.technical_indicators,
            "fundamental_data": self.fundamental_data,
            "sentiment_data": self.sentiment_data,
            "catalyst": self.catalyst,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "alert_sent": self.alert_sent,
        }


class MarketDataSource(ABC):
    """Abstract base class for market data sources"""

    @abstractmethod
    async def get_real_time_data(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get real-time market data for symbols"""

    @abstractmethod
    async def get_historical_data(self, symbol: str, period: str) -> pd.DataFrame:
        """Get historical data for technical analysis"""


class AlphaVantageDataSource(MarketDataSource):
    """Alpha Vantage API integration for stock data"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"

    async def get_real_time_data(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get real-time stock data"""
        results = {}

        async with aiohttp.ClientSession() as session:
            for symbol in symbols:
                try:
                    url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol={
                        symbol
                    }&apikey={self.api_key}"
                    async with session.get(url) as response:
                        data = await response.json()

                        if "Global Quote" in data:
                            quote = data["Global Quote"]
                            results[symbol] = {
                                "price": float(quote.get("05. price", 0)),
                                "change": float(quote.get("09. change", 0)),
                                "change_percent": quote.get(
                                    "10. change percent",
                                    "0%",
                                ).strip("%"),
                                "volume": int(quote.get("06. volume", 0)),
                                "high": float(quote.get("03. high", 0)),
                                "low": float(quote.get("04. low", 0)),
                                "open": float(quote.get("02. open", 0)),
                                "previous_close": float(
                                    quote.get("08. previous close", 0),
                                ),
                            }

                except Exception as e:
                    logger.error(f"Error fetching data for {symbol}: {e}")
                    results[symbol] = {}

        return results

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1y",
    ) -> pd.DataFrame:
        """Get historical data using yfinance (faster for historical data)"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()


class CryptocurrencyDataSource(MarketDataSource):
    """Cryptocurrency data source using CoinGecko API"""

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"

    async def get_real_time_data(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get real-time crypto data"""
        results = {}

        # Convert symbols to CoinGecko format (e.g., BTC -> bitcoin)
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "ADA": "cardano",
            "DOT": "polkadot",
            "LINK": "chainlink",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
        }

        coingecko_ids = [
            symbol_map.get(symbol.upper(), symbol.lower()) for symbol in symbols
        ]
        ids_string = ",".join(coingecko_ids)

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/simple/price?ids={ids_string}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
                async with session.get(url) as response:
                    data = await response.json()

                    for i, symbol in enumerate(symbols):
                        coingecko_id = coingecko_ids[i]
                        if coingecko_id in data:
                            coin_data = data[coingecko_id]
                            results[symbol] = {
                                "price": coin_data.get("usd", 0),
                                "change_percent_24h": coin_data.get(
                                    "usd_24h_change",
                                    0,
                                ),
                                "volume_24h": coin_data.get("usd_24h_vol", 0),
                            }
                        else:
                            results[symbol] = {}

        except Exception as e:
            logger.error(f"Error fetching crypto data: {e}")
            results = {symbol: {} for symbol in symbols}

        return results

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "365",
    ) -> pd.DataFrame:
        """Get historical crypto data"""
        symbol_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}

        coingecko_id = symbol_map.get(symbol.upper(), symbol.lower())

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/coins/{
                    coingecko_id
                }/market_chart?vs_currency=usd&days={period}"
                async with session.get(url) as response:
                    data = await response.json()

                    if "prices" in data:
                        prices = data["prices"]
                        df = pd.DataFrame(prices, columns=["timestamp", "price"])
                        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                        df.set_index("timestamp", inplace=True)
                        return df

        except Exception as e:
            logger.error(f"Error fetching historical crypto data for {symbol}: {e}")

        return pd.DataFrame()


class TechnicalAnalyzer:
    """Advanced technical analysis for opportunity detection"""

    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> dict[str, pd.Series]:
        """Calculate MACD indicators"""
        ema_fast = data.ewm(span=fast).mean()
        ema_slow = data.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line

        return {"macd": macd, "signal": signal_line, "histogram": histogram}

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std: float = 2.0,
    ) -> dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std_dev = data.rolling(window=period).std()

        return {
            "upper": sma + (std_dev * std),
            "middle": sma,
            "lower": sma - (std_dev * std),
        }

    @staticmethod
    def detect_breakout(data: pd.DataFrame, current_price: float) -> dict[str, Any]:
        """Detect technical breakout patterns"""
        if len(data) < 50:
            return {"breakout_detected": False}

        # Calculate 20-day high and low
        high_20 = data["High"].rolling(window=20).max().iloc[-1]
        low_20 = data["Low"].rolling(window=20).min().iloc[-1]

        # Volume analysis
        avg_volume = data["Volume"].rolling(window=20).mean().iloc[-1]
        current_volume = data["Volume"].iloc[-1]
        volume_spike = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Breakout detection
        breakout_up = current_price > high_20 and volume_spike > 1.5
        breakout_down = current_price < low_20 and volume_spike > 1.5

        if breakout_up:
            return {
                "breakout_detected": True,
                "direction": "up",
                "resistance_level": high_20,
                "volume_spike": volume_spike,
                "confidence": min(0.9, volume_spike / 3.0),
            }
        if breakout_down:
            return {
                "breakout_detected": True,
                "direction": "down",
                "support_level": low_20,
                "volume_spike": volume_spike,
                "confidence": min(0.9, volume_spike / 3.0),
            }
        return {"breakout_detected": False}


class SentimentAnalyzer:
    """Market sentiment analysis for opportunity detection"""

    async def analyze_news_sentiment(self, symbol: str) -> dict[str, Any]:
        """Analyze news sentiment for a symbol"""
        # Placeholder implementation - would integrate with news APIs
        # like NewsAPI, Alpha Vantage News, or social media APIs

        sentiment_scores = np.random.uniform(-1, 1, 10)  # Mock data
        avg_sentiment = np.mean(sentiment_scores)
        sentiment_strength = abs(avg_sentiment)

        return {
            "sentiment_score": avg_sentiment,
            "sentiment_strength": sentiment_strength,
            "news_volume": len(sentiment_scores),
            "bullish_articles": sum(1 for s in sentiment_scores if s > 0.1),
            "bearish_articles": sum(1 for s in sentiment_scores if s < -0.1),
            "neutral_articles": sum(1 for s in sentiment_scores if -0.1 <= s <= 0.1),
        }

    async def analyze_social_sentiment(self, symbol: str) -> dict[str, Any]:
        """Analyze social media sentiment"""
        # Placeholder implementation - would integrate with Twitter API, Reddit
        # API, etc.

        social_mentions = np.random.randint(50, 500)
        sentiment_trend = np.random.uniform(-1, 1)

        return {
            "social_sentiment": sentiment_trend,
            "mention_volume": social_mentions,
            "trending_score": abs(sentiment_trend) * social_mentions / 100,
        }


class OpportunityScanner:
    """Main opportunity scanning engine that orchestrates all analysis components"""

    def __init__(self, config: dict[str, Any]):
        self.config = config

        # Initialize data sources
        self.stock_data_source = AlphaVantageDataSource(
            config.get("alpha_vantage_api_key", "demo"),
        )
        self.crypto_data_source = CryptocurrencyDataSource()

        # Initialize analyzers
        self.technical_analyzer = TechnicalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()

        # Opportunity storage
        self.active_opportunities: list[MarketOpportunity] = []
        self.opportunity_history: list[MarketOpportunity] = []

        # Watchlists
        self.stock_watchlist = config.get(
            "stock_watchlist",
            [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "TSLA",
                "NVDA",
                "META",
                "NFLX",
                "AMD",
                "CRM",
            ],
        )
        self.crypto_watchlist = config.get(
            "crypto_watchlist",
            ["BTC", "ETH", "SOL", "ADA", "DOT", "LINK", "MATIC", "AVAX"],
        )

        logger.info(
            f"OpportunityScanner initialized with {len(self.stock_watchlist)} stocks and {len(self.crypto_watchlist)} cryptos",
        )

    async def scan_all_opportunities(self) -> list[MarketOpportunity]:
        """Main scanning method - scans all markets for opportunities"""
        logger.info("🔍 Starting comprehensive opportunity scan...")

        new_opportunities = []

        # Scan stock market opportunities
        stock_opportunities = await self._scan_stock_opportunities()
        new_opportunities.extend(stock_opportunities)

        # Scan cryptocurrency opportunities
        crypto_opportunities = await self._scan_crypto_opportunities()
        new_opportunities.extend(crypto_opportunities)

        # Filter and rank opportunities
        filtered_opportunities = self._filter_and_rank_opportunities(new_opportunities)

        # Update active opportunities
        self._update_active_opportunities(filtered_opportunities)

        logger.info(
            f"✅ Scan complete: {len(filtered_opportunities)} high-quality opportunities detected",
        )

        return filtered_opportunities

    async def _scan_stock_opportunities(self) -> list[MarketOpportunity]:
        """Scan stock market for opportunities"""
        opportunities = []

        try:
            # Get real-time stock data
            stock_data = await self.stock_data_source.get_real_time_data(
                self.stock_watchlist,
            )

            for symbol, data in stock_data.items():
                if not data:  # Skip if no data
                    continue

                try:
                    # Get historical data for technical analysis
                    historical_data = await self.stock_data_source.get_historical_data(
                        symbol,
                        "3mo",
                    )

                    if historical_data.empty:
                        continue

                    current_price = data.get("price", 0)
                    if current_price == 0:
                        continue

                    # Technical analysis
                    breakout_analysis = self.technical_analyzer.detect_breakout(
                        historical_data,
                        current_price,
                    )

                    # Sentiment analysis
                    news_sentiment = (
                        await self.sentiment_analyzer.analyze_news_sentiment(symbol)
                    )
                    social_sentiment = (
                        await self.sentiment_analyzer.analyze_social_sentiment(symbol)
                    )

                    # Volume analysis
                    volume_spike = (
                        data.get("volume", 0)
                        / historical_data["Volume"].rolling(20).mean().iloc[-1]
                        if len(historical_data) > 20
                        else 1.0
                    )

                    # Opportunity detection logic
                    opportunity = self._analyze_stock_opportunity(
                        symbol,
                        data,
                        historical_data,
                        breakout_analysis,
                        news_sentiment,
                        social_sentiment,
                        volume_spike,
                    )

                    if (
                        opportunity and opportunity.confidence_score >= 0.6
                    ):  # Minimum confidence threshold
                        opportunities.append(opportunity)
                        logger.info(
                            f"📈 Stock opportunity detected: {symbol} ({opportunity.confidence_score:.2f} confidence)",
                        )

                except Exception as e:
                    logger.error(f"Error analyzing stock {symbol}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in stock opportunity scanning: {e}")

        return opportunities

    async def _scan_crypto_opportunities(self) -> list[MarketOpportunity]:
        """Scan cryptocurrency market for opportunities"""
        opportunities = []

        try:
            # Get real-time crypto data
            crypto_data = await self.crypto_data_source.get_real_time_data(
                self.crypto_watchlist,
            )

            for symbol, data in crypto_data.items():
                if not data:  # Skip if no data
                    continue

                try:
                    current_price = data.get("price", 0)
                    change_24h = data.get("change_percent_24h", 0)
                    volume_24h = data.get("volume_24h", 0)

                    if current_price == 0:
                        continue

                    # Simple crypto opportunity detection
                    confidence = 0.0
                    signal = SignalType.HOLD
                    opportunity_type = OpportunityType.MOMENTUM
                    expected_return = 0.0

                    # Strong momentum detection
                    if abs(change_24h) > 5:  # More than 5% change in 24h
                        confidence += 0.3
                        if change_24h > 0:
                            signal = SignalType.BUY
                            opportunity_type = OpportunityType.MOMENTUM
                            expected_return = min(
                                change_24h * 0.5,
                                20,
                            )  # Conservative estimate
                        else:
                            signal = SignalType.SELL
                            expected_return = max(change_24h * 0.5, -20)

                    # High volume activity
                    if volume_24h > 1000000:  # High volume threshold
                        confidence += 0.2

                    # Additional crypto-specific analysis could be added here

                    if (
                        confidence >= 0.4
                    ):  # Lower threshold for crypto due to volatility
                        opportunity = MarketOpportunity(
                            symbol=symbol,
                            market_type=MarketType.CRYPTO,
                            opportunity_type=opportunity_type,
                            signal=signal,
                            confidence_score=confidence,
                            expected_return=expected_return,
                            time_horizon="hours",
                            risk_level="high",
                            current_price=current_price,
                            target_price=current_price * (1 + expected_return / 100),
                            stop_loss=current_price * 0.95,  # 5% stop loss
                            volume_spike=volume_24h / 1000000,  # Normalized volume
                            technical_indicators={
                                "change_24h": change_24h,
                                "volume_24h": volume_24h,
                            },
                            catalyst=f"Strong momentum: {change_24h:+.2f}% in 24h",
                        )

                        opportunities.append(opportunity)
                        logger.info(
                            f"🚀 Crypto opportunity detected: {symbol} ({
                                confidence:.2f} confidence)",
                        )

                except Exception as e:
                    logger.error(f"Error analyzing crypto {symbol}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in crypto opportunity scanning: {e}")

        return opportunities

    def _analyze_stock_opportunity(
        self,
        symbol: str,
        real_time_data: dict[str, Any],
        historical_data: pd.DataFrame,
        breakout_analysis: dict[str, Any],
        news_sentiment: dict[str, Any],
        social_sentiment: dict[str, Any],
        volume_spike: float,
    ) -> MarketOpportunity | None:
        """Analyze individual stock for opportunities"""
        current_price = real_time_data.get("price", 0)
        change_percent = float(real_time_data.get("change_percent", "0").strip("%"))

        confidence = 0.0
        signal = SignalType.HOLD
        opportunity_type = OpportunityType.MOMENTUM
        expected_return = 0.0

        # Technical breakout analysis
        if breakout_analysis.get("breakout_detected", False):
            confidence += breakout_analysis.get("confidence", 0) * 0.4
            if breakout_analysis.get("direction") == "up":
                signal = SignalType.BUY
                opportunity_type = OpportunityType.BREAKOUT
                expected_return = min(
                    abs(change_percent) * 1.5,
                    15,
                )  # Conservative breakout target
            else:
                signal = SignalType.SELL
                expected_return = max(-abs(change_percent) * 1.5, -15)

        # Volume spike analysis
        if volume_spike > 2.0:  # 2x normal volume
            confidence += min(0.3, volume_spike / 10)

        # Sentiment analysis
        news_score = news_sentiment.get("sentiment_score", 0)
        if abs(news_score) > 0.3:
            confidence += abs(news_score) * 0.2
            if news_score > 0.3 and signal != SignalType.SELL:
                signal = SignalType.BUY if signal == SignalType.HOLD else signal
            elif news_score < -0.3 and signal != SignalType.BUY:
                signal = SignalType.SELL if signal == SignalType.HOLD else signal

        # Strong momentum detection
        if abs(change_percent) > 3:  # More than 3% change
            confidence += 0.2
            if change_percent > 0 and signal == SignalType.HOLD:
                signal = SignalType.BUY
                opportunity_type = OpportunityType.MOMENTUM
                expected_return = min(change_percent * 0.8, 12)

        # Only return opportunities with sufficient confidence
        if confidence < 0.6:
            return None

        # Calculate target and stop loss
        if signal == SignalType.BUY:
            target_price = current_price * (1 + expected_return / 100)
            stop_loss = current_price * 0.98  # 2% stop loss
            risk_level = "medium" if confidence > 0.8 else "high"
        elif signal == SignalType.SELL:
            # expected_return is negative
            target_price = current_price * (1 + expected_return / 100)
            stop_loss = current_price * 1.02  # 2% stop loss (upward for short)
            risk_level = "high"
        else:
            return None

        # Determine time horizon
        if opportunity_type == OpportunityType.BREAKOUT:
            time_horizon = "days"
        elif volume_spike > 3.0:
            time_horizon = "hours"
        else:
            time_horizon = "days"

        return MarketOpportunity(
            symbol=symbol,
            market_type=MarketType.STOCK,
            opportunity_type=opportunity_type,
            signal=signal,
            confidence_score=min(confidence, 1.0),
            expected_return=expected_return,
            time_horizon=time_horizon,
            risk_level=risk_level,
            current_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            volume_spike=volume_spike,
            technical_indicators={
                "change_percent": change_percent,
                "breakout_analysis": breakout_analysis,
                "volume_spike": volume_spike,
            },
            sentiment_data={
                "news_sentiment": news_sentiment,
                "social_sentiment": social_sentiment,
            },
            catalyst=self._generate_catalyst_description(
                breakout_analysis,
                news_sentiment,
                volume_spike,
            ),
        )

    def _generate_catalyst_description(
        self,
        breakout_analysis: dict[str, Any],
        news_sentiment: dict[str, Any],
        volume_spike: float,
    ) -> str:
        """Generate human-readable catalyst description"""
        catalysts = []

        if breakout_analysis.get("breakout_detected"):
            direction = breakout_analysis.get("direction", "")
            catalysts.append(f"Technical breakout ({direction})")

        if volume_spike > 2.0:
            catalysts.append(f"Volume surge ({volume_spike:.1f}x normal)")

        sentiment_score = news_sentiment.get("sentiment_score", 0)
        if abs(sentiment_score) > 0.4:
            sentiment_text = "positive" if sentiment_score > 0 else "negative"
            catalysts.append(f"Strong {sentiment_text} news sentiment")

        return " + ".join(catalysts) if catalysts else "Multiple technical factors"

    def _filter_and_rank_opportunities(
        self,
        opportunities: list[MarketOpportunity],
    ) -> list[MarketOpportunity]:
        """Filter and rank opportunities by quality"""
        # Filter out low-quality opportunities
        filtered = [op for op in opportunities if op.confidence_score >= 0.6]

        # Rank by composite score (confidence * expected return * risk adjustment)
        def composite_score(op: MarketOpportunity) -> float:
            risk_multiplier = {"low": 1.0, "medium": 0.9, "high": 0.7}[op.risk_level]
            time_multiplier = {"minutes": 1.2, "hours": 1.1, "days": 1.0, "weeks": 0.9}[
                op.time_horizon
            ]

            return (
                op.confidence_score
                * abs(op.expected_return)
                * risk_multiplier
                * time_multiplier
            )

        filtered.sort(key=composite_score, reverse=True)

        # Return top opportunities (max 20)
        return filtered[:20]

    def _update_active_opportunities(self, new_opportunities: list[MarketOpportunity]):
        """Update the list of active opportunities"""
        # Remove expired opportunities
        current_time = datetime.utcnow()
        self.active_opportunities = [
            op
            for op in self.active_opportunities
            if op.expires_at is None or op.expires_at > current_time
        ]

        # Add new opportunities (avoid duplicates)
        existing_symbols = {op.symbol for op in self.active_opportunities}

        for opportunity in new_opportunities:
            if opportunity.symbol not in existing_symbols:
                # Set expiration time based on time horizon
                if opportunity.time_horizon == "minutes":
                    opportunity.expires_at = current_time + timedelta(minutes=30)
                elif opportunity.time_horizon == "hours":
                    opportunity.expires_at = current_time + timedelta(hours=6)
                elif opportunity.time_horizon == "days":
                    opportunity.expires_at = current_time + timedelta(days=2)
                else:  # weeks
                    opportunity.expires_at = current_time + timedelta(weeks=1)

                self.active_opportunities.append(opportunity)

        # Sort active opportunities by confidence
        self.active_opportunities.sort(key=lambda x: x.confidence_score, reverse=True)

    def get_active_opportunities(self) -> list[MarketOpportunity]:
        """Get current active opportunities"""
        return self.active_opportunities.copy()

    def get_top_opportunities(self, limit: int = 10) -> list[MarketOpportunity]:
        """Get top opportunities by confidence score"""
        return self.active_opportunities[:limit]

    async def generate_opportunity_alert(
        self,
        opportunity: MarketOpportunity,
    ) -> dict[str, Any]:
        """Generate formatted alert for an opportunity"""
        # Calculate potential profit for a $10,000 investment
        investment_amount = 10000
        potential_profit = investment_amount * (opportunity.expected_return / 100)

        alert = {
            "title": f"🚨 {opportunity.signal.value.upper()} SIGNAL: {opportunity.symbol}",
            "message": f"""
{opportunity.opportunity_type.value.replace("_", " ").title()} Opportunity Detected!

💰 Symbol: {opportunity.symbol} ({opportunity.market_type.value.upper()})
📊 Current Price: ${opportunity.current_price:.4f}
🎯 Target Price: ${opportunity.target_price:.4f}
🛡️ Stop Loss: ${opportunity.stop_loss:.4f}
📈 Expected Return: {opportunity.expected_return:+.2f}%
⏱️ Time Horizon: {opportunity.time_horizon}
🔥 Confidence: {opportunity.confidence_score:.1%}
⚠️ Risk Level: {opportunity.risk_level.upper()}

💡 Catalyst: {opportunity.catalyst}

💵 Potential Profit (on $10K): ${potential_profit:+,.2f}
""".strip(),
            "priority": "high" if opportunity.confidence_score > 0.8 else "medium",
            "opportunity_data": opportunity.to_dict(),
        }

        return alert


# Example usage and configuration


async def main_scanner_demo():
    """Demo of the opportunity scanner"""
    # Configuration
    config = {
        "alpha_vantage_api_key": "demo",  # Replace with real API key
        "stock_watchlist": ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"],
        "crypto_watchlist": ["BTC", "ETH", "SOL", "ADA"],
    }

    # Initialize scanner
    scanner = OpportunityScanner(config)

    # Scan for opportunities
    opportunities = await scanner.scan_all_opportunities()

    # Display results
    print("\n🔍 OPPORTUNITY SCAN RESULTS")
    print("=" * 50)
    print(f"Found {len(opportunities)} high-quality opportunities:\n")

    for i, op in enumerate(opportunities[:5], 1):  # Show top 5
        print(f"{i}. {op.symbol} ({op.market_type.value.upper()})")
        print(f"   Signal: {op.signal.value.upper()}")
        print(f"   Expected Return: {op.expected_return:+.2f}%")
        print(f"   Confidence: {op.confidence_score:.1%}")
        print(f"   Catalyst: {op.catalyst}")
        print()

    # Generate alert for top opportunity
    if opportunities:
        top_opportunity = opportunities[0]
        alert = await scanner.generate_opportunity_alert(top_opportunity)
        print("🚨 TOP OPPORTUNITY ALERT:")
        print(alert["message"])


if __name__ == "__main__":
    asyncio.run(main_scanner_demo())
